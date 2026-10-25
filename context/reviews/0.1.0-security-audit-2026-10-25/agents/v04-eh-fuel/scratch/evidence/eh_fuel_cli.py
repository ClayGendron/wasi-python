# Smallest -W fuel=N under which the pinned wasmtime CLI 49.0.3 completes each call (bisection).
import json, subprocess, sys
W, wat = sys.argv[1], sys.argv[2]
def ok(name, r, n, fuel):
    p = subprocess.run([W, "run", "-C", "cache=n", "-W", f"fuel={fuel},exceptions=y", "--invoke", name, wat, str(r), str(n)],
                       capture_output=True, text=True, timeout=60)
    return p.returncode == 0, p.stderr.strip().splitlines()[-1:] if p.returncode else []
out = {"cli": subprocess.run([W, "--version"], capture_output=True, text=True).stdout.strip(), "rows": []}
for name, r, n in (("returned", 1, 100000), ("thrown", 1, 1), ("thrown", 1, 1000), ("thrown", 1, 100000), ("thrown", 10, 100000), ("thrown", 100, 100000)):
    lo, hi = 0, 10**9
    if not ok(name, r, n, hi)[0]:
        out["rows"].append({"func": name, "r": r, "n": n, "error": ok(name, r, n, hi)[1]}); continue
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if ok(name, r, n, mid)[0]: hi = mid
        else: lo = mid
    out["rows"].append({"func": name, "r": r, "n": n, "min_fuel_to_complete": hi, "trap_at_one_less": ok(name, r, n, lo)[1]})
print(json.dumps(out, indent=1))
