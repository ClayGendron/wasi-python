# Limit arguments at the edges: each is checked before any work (no guest runs for a refusal).
import json, math, fractions, decimal
import wasi_python
from wasi_python import Session

class IntSub(int):
    def __index__(self): return -1
class BadFloat(float):
    def __float__(self): return float("inf")

vals = [None, 0, 1, -1, True, 2**63 - 1, 2**63, 1.5, "5", IntSub(5)]
secs = [None, 0, -0.0, 1e-300, float("nan"), float("inf"), True, 4.7e16, 4.5e16,
        fractions.Fraction(1, 10**400), decimal.Decimal("0.5"), BadFloat(1.0), "1"]
out = {}
def probe(kind, name, v, fn):
    try:
        fn()
        out.setdefault(kind, []).append([name, repr(v), "accepted"])
    except Exception as e:
        out.setdefault(kind, []).append([name, repr(v), type(e).__name__])

for name in ("fuel", "memory_bytes", "output_bytes", "max_open_files", "max_file_calls"):
    for v in vals:
        probe("run_int", name, v, lambda: wasi_python._runner._checked(
            [], None, None, *( (v, 1.0, None, None) if name=="fuel" else
                              (None, 1.0, v, None) if name=="memory_bytes" else
                              (None, 1.0, None, v) if name=="output_bytes" else
                              (None, 1.0, None, None)), None,
            **({"max_open_files": v} if name=="max_open_files" else {}),
            **({"max_file_calls": v} if name=="max_file_calls" else {})))
for v in secs:
    probe("run_deadline", "deadline_s", v, lambda: wasi_python._runner._checked([], None, None, None, v, None, None, None))
from wasi_python import _limits
for v in secs:
    probe("session_secs", "idle_s", v, lambda: _limits._seconds_limit("idle_s", v))
    probe("session_secs", "shutdown_s", v, lambda: _limits._shutdown_limit("shutdown_s", v))
# What a BadFloat deadline is stored as after the check:
print(json.dumps(out, indent=1))
