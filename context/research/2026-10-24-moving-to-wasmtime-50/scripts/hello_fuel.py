"""Run hello and a numpy sum through the runner on the installed wasmtime-py; print fuel."""
import importlib.metadata as md, json, os, sys, time
os.environ["WASI_PYTHON_ARTIFACTS"] = "/Users/claygendron/Git/Repos/wasi_python/build/artifacts"
sys.path.insert(0, "/Users/claygendron/Git/Repos/wasi_python/src")
import wasi_python
cache = "/Users/claygendron/Git/Repos/wasi_python/build/scratch-wt50/cache"
rows = {"wasmtime_py": md.version("wasmtime")}
for name, code, snap in [("hello-snapshot", "print(1)", True), ("hello-plain", "print(1)", False),
                         ("numpy-sum", "import numpy as np; print(np.arange(10**6).sum())", True),
                         ("files-grant-stat", "import os\nfor i in range(1000): os.stat('/usr/local/lib')\nprint('ok')", True)]:
    t = time.perf_counter()
    c = wasi_python.run(["-c", code], fuel=10**12, snapshot=snap, cache_dir=cache)
    ms = (time.perf_counter() - t) * 1e3
    rows[name] = {"exit": c.exit_code, "trapped": c.trapped, "stdout": c.stdout.decode().strip(), "fuel_used": c.fuel_used, "wall_ms": round(ms)}
print(json.dumps(rows, indent=1))
