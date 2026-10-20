"""Spec 086's hash-flag cost: fuel per str hash, net of building the strings, per set (snapshot).
usage: hashcost.py NAME=SETDIR ..."""
import os, sys
BUILD = "s = ['k%07d' % i for i in range(200000)]\n"
HASH = BUILD + "for x in s: hash(x)\n"
for arg in sys.argv[1:]:
    name, d = arg.split("=", 1)
    os.environ["WASI_PYTHON_ARTIFACTS"] = d
    import importlib, wasi_python
    importlib.reload(wasi_python)
    f = [wasi_python.run(["-c", c], snapshot=True, fuel=10**12).fuel_used for c in (BUILD, HASH)]
    print(name, "build", f[0], "build+hash", f[1], "per 8-char hash", round((f[1] - f[0]) / 200000, 1))
