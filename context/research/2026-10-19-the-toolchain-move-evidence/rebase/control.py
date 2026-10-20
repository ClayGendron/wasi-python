"""Spec 086's layout control: fuel of numpy's import and of twenty bool-list conversions, per set.
usage: control.py NAME=SETDIR ... (snapshot binary)"""
import os, sys
C = "/Users/claygendron/Git/Repos/wasi_python-086/context/research/2026-10-19-the-toolchain-move-evidence/control"
progs = {n: open(f"{C}/{n}.py").read() for n in ("ids", "npimport", "boolconv")}
for arg in sys.argv[1:]:
    name, d = arg.split("=", 1)
    os.environ["WASI_PYTHON_ARTIFACTS"] = d
    import importlib, wasi_python
    importlib.reload(wasi_python)
    f = {}
    for n, code in progs.items():
        r = wasi_python.run(["-c", code], snapshot=True, fuel=10**13)
        f[n] = r.fuel_used
        out = r.stdout.decode().strip()
    print(name, "npimport", f["npimport"], "boolconv", f["boolconv"], "net", f["boolconv"] - f["npimport"], out)
