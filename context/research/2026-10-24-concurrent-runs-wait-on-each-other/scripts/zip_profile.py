import os, sys, time, cProfile, pstats
from pathlib import Path
REPO = Path("/Users/claygendron/Git/Repos/wasi_python")
os.environ["WASI_PYTHON_ARTIFACTS"] = str(REPO / "build/artifacts")
import wasi_python
from wasi_python import _zip, _artifacts, _places, _engines
from wasi_python._process import process
CACHE = REPO / "build/rust-spike-perf/work/cwasm-py"
wasi_python.run(["-c", "pass"], fuel=10**12, cache_dir=CACHE)
found, checked = _artifacts._found_and_checked(True)
entry = process().zips[checked.zip]
print("record is None:", entry[2] is None, "zip folder:", entry[0].path)
t = time.perf_counter()
for _ in range(100):
    _zip._zip_folder(found, checked.zip)
print("zip_folder x100: %.2f ms each" % ((time.perf_counter() - t) * 10))
pr = cProfile.Profile(); pr.enable()
for _ in range(100):
    _zip._zip_folder(found, checked.zip)
pr.disable(); pstats.Stats(pr).sort_stats("cumulative").print_stats(12)
cache = _engines._cache_dir(CACHE)
t = time.perf_counter()
for _ in range(100):
    r = _places._walk_grants(None, (), found, cache, (), (), others=_engines._caches(cache))
print("walk_grants x100: %.2f ms each" % ((time.perf_counter() - t) * 10))
pr = cProfile.Profile(); pr.enable()
for _ in range(100):
    _places._walk_grants(None, (), found, cache, (), (), others=_engines._caches(cache))
pr.disable(); pstats.Stats(pr).sort_stats("tottime").print_stats(15)
sys.stdout.flush(); process().release_at_exit(); os._exit(0)
