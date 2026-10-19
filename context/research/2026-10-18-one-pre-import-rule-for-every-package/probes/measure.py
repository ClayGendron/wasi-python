"""Measure one binary with the judge's guest driver. Usage: measure.py <label> <wasm> <out.json>
Fuel is wasmtime's instruction count through tests/harness/guest.py (read-only import from the main
tree); memory is the module's exported memory minimum (the pages an instance starts with)."""
import json, pathlib, shutil, sys, time, zlib
HERE = pathlib.Path("/Users/claygendron/Git/Repos/wasi_python")
sys.path.insert(0, str(HERE / "tests/harness"))
import wasmtime as wt  # noqa: E402
import guest  # noqa: E402
S = pathlib.Path(__file__).resolve().parent.parent
label, wasm, out = sys.argv[1], pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
ZIP = HERE / "build/sets/s-4eb5418a2b1bb553/python-stdlib.zip"
JOBS = S / "probes/jobs"
work = S / "runs" / label
shutil.rmtree(work, ignore_errors=True); work.mkdir(parents=True)
kept = work / "kept-mpl"; kept.mkdir()
res = {"label": label, "wasm": str(wasm), "bytes": wasm.stat().st_size}
data = wasm.read_bytes()
c = zlib.compressobj(6, zlib.DEFLATED, -15); res["deflated_level6"] = len(c.compress(data)) + len(c.flush())
# wasm sections: data section size and the memory's minimum
i = 8; sections = {}
while i < len(data):
    sid = data[i]; i += 1; n = 0; shift = 0
    while True:
        b = data[i]; i += 1; n |= (b & 0x7f) << shift; shift += 7
        if not b & 0x80: break
    sections[sid] = sections.get(sid, 0) + n; i += n
res["data_section_bytes"] = sections.get(11, 0); res["code_section_bytes"] = sections.get(10, 0)
mod = guest.module(wasm)
for e in mod.exports:
    if isinstance(e.type, wt.MemoryType):
        res["memory_min_pages"] = e.type.limits.min
res["memory_min_mib"] = round(res["memory_min_pages"] * 65536 / 2**20, 2)
sales = (JOBS / "sales.csv").read_bytes()
def go(name, argv, **kw):
    t = time.perf_counter()
    r = guest.run(wasm, argv, workdir=work, python_version="3.15", stdlib=ZIP, fuel=10**12, **kw)
    dt = time.perf_counter() - t
    ok = r.exit_code == 0 and not r.trapped
    res.setdefault("jobs", {})[name] = {"fuel": r.fuel, "ok": ok, "wall_s": round(dt, 3), "tail": r.describe() if not ok else r.text.strip().splitlines()[-1][:80] if r.text.strip() else ""}
    print(f"{label:6} {name:22} fuel {r.fuel:>14,} {'ok' if ok else r.describe()}  ({dt:.2f}s)", flush=True)
go("pass", ["-c", "pass"])
go("hard_exit", ["-c", "import os; os._exit(0)"])
go("pure", ["/job.py"], files={"/job.py": (JOBS / "pure.py").read_text()})
go("numpy", ["/job.py"], files={"/job.py": (JOBS / "numpy_small.py").read_text()})
go("pandas", ["/job.py", "/data/sales.csv"], files={"/job.py": (JOBS / "pandas_small.py").read_text(), "/data/sales.csv": sales})
plot = (HERE / "tests/jobs/plot_line.py").read_text()
go("plot_fresh_cache", ["/job.py", "/data", "/out", "/out/plot.png"], files={"/job.py": plot, "/data/.keep": "", "/out/.keep": "", "/tmp/mpl/.keep": ""}, env={"MPLCONFIGDIR": "/tmp/mpl"}, mpl_data=True)
go("plot_kept_cache_warmup", ["/job.py", "/data", "/out", "/out/plot.png"], files={"/job.py": plot, "/data/.keep": "", "/out/.keep": ""}, env={"MPLCONFIGDIR": "/tmp/mpl"}, mpl_data=True, preopens=[("/tmp/mpl", kept, True)])
go("plot_kept_cache", ["/job.py", "/data", "/out", "/out/plot.png"], files={"/job.py": plot, "/data/.keep": "", "/out/.keep": ""}, env={"MPLCONFIGDIR": "/tmp/mpl"}, mpl_data=True, preopens=[("/tmp/mpl", kept, True)])
out.write_text(json.dumps(res, indent=1))
print(json.dumps({k: v for k, v in res.items() if k != "jobs"}))
