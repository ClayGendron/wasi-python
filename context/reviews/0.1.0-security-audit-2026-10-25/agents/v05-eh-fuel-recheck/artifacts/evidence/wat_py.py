# Fuel used by the WAT's two exports on the installed wasmtime-py, consume_fuel on, defaults otherwise.
import json, sys, wasmtime as wt
from importlib.metadata import version
cfg = wt.Config(); cfg.consume_fuel = True
eng = wt.Engine(cfg); mod = wt.Module(eng, open(sys.argv[1]).read())
for name in ("returned", "thrown"):
    for r, n in ((1, 100000), (100, 100000)):
        st = wt.Store(eng); st.set_fuel(10**12)
        inst = wt.Instance(st, mod, []); st.set_fuel(10**12)
        inst.exports(st)[name](st, r, n)
        print(json.dumps({"wasmtime_py": version("wasmtime"), "func": name, "r": r, "n": n, "fuel_used": 10**12 - st.get_fuel()}))
