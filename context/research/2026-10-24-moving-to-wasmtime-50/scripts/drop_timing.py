"""Load the runner's cached snapshot module and time its drop, on the installed wasmtime-py,
with native unwind information on (the runner's engine today) and off."""
import gc, glob, importlib.metadata as md, json, sys, time
import wasmtime as wt
ver = md.version("wasmtime")
rows = {"wasmtime_py": ver}
cache = "/Users/claygendron/Git/Repos/wasi_python/build/scratch-wt50/cache"
for unwind in (True, False):
    cfg = wt.Config(); cfg.consume_fuel = True; cfg.epoch_interruption = True
    cfg.native_unwind_info = unwind
    engine = wt.Engine(cfg)
    snapshot = "/Users/claygendron/Git/Repos/wasi_python/build/artifacts/python-snapshot.wasm"
    t = time.perf_counter()
    m = wt.Module.from_file(engine, snapshot)  # compile: the cached file was made with unwind on
    compile_ms = (time.perf_counter() - t) * 1e3
    t = time.perf_counter(); del m; gc.collect(); drop_ms = (time.perf_counter() - t) * 1e3
    rows[f"unwind={unwind}"] = {"compile_ms": round(compile_ms), "drop_ms": round(drop_ms, 1)}
    print(json.dumps(rows), file=sys.stderr)
print(json.dumps(rows, indent=1))
