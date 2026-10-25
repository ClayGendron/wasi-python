"""The runner's host-side checks alone, no guest: 8 in sequence against 8 on 8 threads. If the
parallel wall equals the sequential, the GIL serializes them; if it is longer, contention costs more
than serialization (GIL hand-offs around every syscall, the kernel)."""
import os, sys, time, statistics, threading, json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
REPO = Path("/Users/claygendron/Git/Repos/wasi_python")
os.environ["WASI_PYTHON_ARTIFACTS"] = str(REPO / "build/artifacts")
sys.path.insert(0, str(REPO / "build/concurrency-probe"))
import wasi_python
from wasi_python import _zip, _artifacts, _places, _engines, _private_dirs
from wasi_python._process import process
import driver  # the fixes' alternative functions
CACHE = REPO / "build/rust-spike-perf/work/cwasm-py"
wasi_python.run(["-c", "pass"], fuel=10**12, cache_dir=CACHE)
found, checked = _artifacts._found_and_checked(True)
entry = process().zips[checked.zip]
data = entry[0].path / "mpl-data"
record = entry[2]
cache = _engines._cache_dir(CACHE)

def batch(fn, n, workers):
    t = time.perf_counter()
    if workers == 1:
        for _ in range(n): fn()
    else:
        with ThreadPoolExecutor(workers) as ex: list(ex.map(lambda _: fn(), range(n)))
    return (time.perf_counter() - t) * 1e3

def private():
    p = _private_dirs._Private("wasi-python-probe-"); p.remove()

jobs = {
    "data_intact (os.walk+pathlib, under zip_lock in the product)": lambda: _zip._data_intact(data, record),
    "data_intact by scandir": lambda: driver._data_intact_scandir(data, record),
    "zip_folder (the lock + the check)": lambda: _zip._zip_folder(found, checked.zip),
    "walk_grants": lambda: _places._walk_grants(None, (), found, cache, (), (), others=_engines._caches(cache)),
    "found_and_checked": lambda: _artifacts._found_and_checked(True),
    "Private make+remove": private,
}
out = {}
for interval in (0.005, 0.0001):
    sys.setswitchinterval(interval)
    for name, fn in jobs.items():
        seq, par = [], []
        for _ in range(5):
            seq.append(batch(fn, 8, 1)); par.append(batch(fn, 8, 8))
        row = dict(seq8_ms=round(statistics.median(seq), 2), par8_ms=round(statistics.median(par), 2),
                   per_call_ms=round(statistics.median(seq) / 8, 3), ratio_par_over_seq=round(statistics.median(par) / statistics.median(seq), 2))
        out[f"{name} @switch={interval}"] = row
        print(f"switch={interval:<6} {name:62s} seq8={row['seq8_ms']:7.2f} par8={row['par8_ms']:7.2f} per-call={row['per_call_ms']:.3f} par/seq={row['ratio_par_over_seq']}")
sys.setswitchinterval(0.005)
# an all-Python loop of the same length, for scale: pure bytecode, no syscalls
def pure():
    s = 0
    for i in range(60000): s += i
seq = [batch(pure, 8, 1) for _ in range(5)]; par = [batch(pure, 8, 8) for _ in range(5)]
print(f"pure bytecode loop: seq8={statistics.median(seq):.2f} par8={statistics.median(par):.2f} par/seq={statistics.median(par)/statistics.median(seq):.2f}")
out["pure bytecode"] = dict(seq8_ms=round(statistics.median(seq), 2), par8_ms=round(statistics.median(par), 2))
out["load_1m"] = os.getloadavg()[0]
Path(REPO / "build/concurrency-probe/results/hostonly.json").write_text(json.dumps(out, indent=1))
sys.stdout.flush(); process().remove_zips(); os._exit(0)
