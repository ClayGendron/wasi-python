# Fuel consumed by the same calls under the installed wasmtime-py (49.0.0), metered, Cranelift.
import json, sys, wasmtime as wt
wat = open(sys.argv[1]).read()
cfg = wt.Config(); cfg.consume_fuel = True
eng = wt.Engine(cfg)
mod = wt.Module(eng, wat)
out = {"wasmtime_py": wt.__version__ if hasattr(wt, "__version__") else "?", "rows": []}
try:
    from importlib.metadata import version; out["wasmtime_py"] = version("wasmtime")
except Exception as e: out["ver_err"] = str(e)
for name in ("returned", "thrown"):
    for r, n in ((1, 0), (1, 1000), (1, 100000), (10, 100000), (100, 100000)):
        st = wt.Store(eng); st.set_fuel(10**12)
        inst = wt.Instance(st, mod, [])
        st.set_fuel(10**12)
        inst.exports(st)[name](st, r, max(n, 1))
        out["rows"].append({"func": name, "r": r, "n": max(n, 1), "fuel_used": 10**12 - st.get_fuel()})
print(json.dumps(out, indent=1))
