"""How deep the guest's plain recursion goes before wasmtime's stack-overflow trap, and how fast."""
import json, sys, time
from wasi_python import run
code = ("import sys\nsys.setrecursionlimit(10**8)\n"
        "def f(n):\n    if n % 20000 == 0: sys.stderr.write(str(n) + '\\n')\n    return f(n + 1)\nf(0)")
t = time.monotonic()
done = run(["-c", code], deadline_s=60)
last = done.stderr.decode().split()[-1:]
print(json.dumps({"trapped": done.trapped, "last_depth_printed": last,
                  "seconds": round(time.monotonic() - t, 2)}))
