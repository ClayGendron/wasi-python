# Host: run the guest through wasi_python.run on the checkout's artifact set; fuel given, deadline_s=None.
import json, sys, time
import wasi_python
guest = open(sys.argv[1]).read()
for case in sys.argv[2:]:
    parts = case.split(":")
    n, k, mode = parts[:3]
    fuel = int(parts[3]) if len(parts) > 3 else 10**13
    t = time.perf_counter()
    r = wasi_python.run(["-c", guest, n, k, mode], fuel=fuel, deadline_s=None)
    print(json.dumps({"case": case, "exit": r.exit_code, "trapped": r.trapped, "fuel_used": r.fuel_used,
                      "host_s": round(time.perf_counter() - t, 3), "stdout": r.stdout.decode().strip(),
                      "stderr": r.stderr.decode()[-200:]}), flush=True)
