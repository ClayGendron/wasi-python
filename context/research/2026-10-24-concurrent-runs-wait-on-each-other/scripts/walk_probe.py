"""The grants walk alone: its os calls by name, where they come from, and what a per-call memo of
ancestor identities (the same path read once per call) would save. Prototype only."""
import os, sys, time, statistics, threading, json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
REPO = Path("/Users/claygendron/Git/Repos/wasi_python")
os.environ["WASI_PYTHON_ARTIFACTS"] = str(REPO / "build/artifacts")
sys.path.insert(0, str(REPO / "build/concurrency-probe"))
import wasi_python
from wasi_python import _artifacts, _places, _engines, _platform
from wasi_python._process import process
import driver
CACHE = REPO / "build/rust-spike-perf/work/cwasm-py"
wasi_python.run(["-c", "pass"], fuel=10**12, cache_dir=CACHE)
found, checked = _artifacts._found_and_checked(True)
cache = _engines._cache_dir(CACHE)
others = _engines._caches(cache)
print("runtime folders judged per call:", 1 + 1 + len({found.manifest.parent, found.snapshot.parent, found.plain.parent, found.stdlib_zip.parent}) + 1 + len(others) + 2, "others:", [str(p) for _, p in others])
walk = lambda: _places._walk_grants(None, (), found, cache, (), (), others=others)
print("ops per walk:", json.dumps(driver.count_ops(walk, 8)))
# where: count calls of _chain / _cache_chain / identity_of / realpath
calls = {"_chain": 0, "_cache_chain": 0, "identity_of": 0, "realpath": 0}
o_chain, o_cc, o_id, o_rp = _places._chain, _places._cache_chain, _platform.PLATFORM.identity_of, os.path.realpath
def c1(p): calls["_chain"] += 1; return o_chain(p)
def c2(p): calls["_cache_chain"] += 1; return o_cc(p)
def c3(p): calls["identity_of"] += 1; return o_id(p)
def c4(p, **k): calls["realpath"] += 1; return o_rp(p, **k)
_places._chain, _places._cache_chain, os.path.realpath = c1, c2, c4
_platform.PLATFORM.identity_of = c3
walk(); print("helper calls per walk:", calls)
_places._chain, _places._cache_chain, os.path.realpath = o_chain, o_cc, o_rp
_platform.PLATFORM.identity_of = o_id
# distinct paths identity_of sees per walk
seen = []
def c5(p): seen.append(str(p)); return o_id(p)
_platform.PLATFORM.identity_of = c5
walk(); print("identity_of: %d calls, %d distinct paths" % (len(seen), len(set(seen))))
_platform.PLATFORM.identity_of = o_id
# the memo prototype: one identity per distinct path per walk, on this thread
local = threading.local()
def memo_identity(p):
    m = getattr(local, "memo", None)
    if m is None: return o_id(p)
    k = str(p)
    if k not in m: m[k] = o_id(p)
    return m[k]
def walk_memo():
    local.memo = {}
    try: return walk()
    finally: local.memo = None
def batch(fn, n, workers):
    t = time.perf_counter()
    if workers == 1:
        for _ in range(n): fn()
    else:
        with ThreadPoolExecutor(workers) as ex: list(ex.map(lambda _: fn(), range(n)))
    return (time.perf_counter() - t) * 1e3
out = {}
for label, fn, patch in (("walk as is", walk, False), ("walk with the identity memo", walk_memo, True)):
    _platform.PLATFORM.identity_of = memo_identity if patch else o_id
    seq = [batch(fn, 8, 1) for _ in range(7)]; par = [batch(fn, 8, 8) for _ in range(7)]
    ops = driver.count_ops(fn, 8)
    out[label] = dict(per_call_ms=round(statistics.median(seq) / 8, 3), par8_ms=round(statistics.median(par), 2), ops_per_call=ops["total_per_call"], lstat=ops["by_name"].get("lstat"), stat=ops["by_name"].get("stat"))
    print(label, out[label])
_platform.PLATFORM.identity_of = o_id
(REPO / "build/concurrency-probe/results/walk.json").write_text(json.dumps(out, indent=1))
sys.stdout.flush(); process().remove_zips(); os._exit(0)
