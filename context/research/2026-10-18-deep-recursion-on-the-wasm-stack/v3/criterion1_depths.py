"""Spec 071 criterion 1's depths on the built set's snapshot (no package pre-imported since 069)."""
import re, sys
from pathlib import Path
src = Path("tests/checks/test_v1_2_hostile_guest.py").read_text()
ns = {}
exec(src[src.index("COUNTED = "):src.index("RECURSION_CASES = ")], ns)
import wasi_python
for name, (body, kind, pat, floor, plain) in ns["RECURSIONS"].items():
    r = wasi_python.run(["-c", ns["COUNTED"].format(body=body)], fuel=10**11)
    out = r.stdout.decode().strip().splitlines()[-1] if r.stdout else str(r.trapped)
    k, d, m = (out.split(" ", 2) + ["", ""])[:3]
    print(f"{name:22} {k:15} depth {d:>4} floor {floor:>4} | {m[:40]}")
