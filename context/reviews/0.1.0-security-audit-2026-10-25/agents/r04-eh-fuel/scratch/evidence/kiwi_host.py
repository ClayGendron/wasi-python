# Host: run (deadline_s=None, so fuel is the only bound) the guest under wasi_python.run with a fuel cap and report fuel_used per case.
import json, sys
sys.path.insert(0, "./src")
import wasi_python
code = open(sys.argv[1]).read()
cases = [tuple(c.split(":")) for c in sys.argv[2:]]
rows = []
for c in cases:
    n, k, mode = c[:3]
    fuel = int(c[3]) if len(c) > 3 else 10**13
    r = wasi_python.run(["-c", code, n, k, mode], fuel=fuel, deadline_s=None)
    rows.append({"N": int(n), "K": int(k), "mode": mode, "fuel_cap": fuel, "exit": r.exit_code, "trapped": r.trapped,
                 "fuel_used": r.fuel_used, "stdout": r.stdout.decode().strip(), "stderr": r.stderr.decode()[-300:]})
    print(json.dumps(rows[-1]), flush=True)
