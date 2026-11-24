import sys, time, json, resource, statistics, tempfile, os
import wasi_python as wp
mode = sys.argv[1]
cache = sys.argv[2] if len(sys.argv) > 2 else None
def t(fn):
    a = time.perf_counter(); r = fn(); return (time.perf_counter() - a) * 1000, r
def rss(): return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
out = {}
cd = None
if mode == "first":
    ms, r = t(lambda: wp.run(["-c", "pass"], cache_dir=cd)); out["first_call_ms"] = ms; out["exit"] = r.exit_code
    ms, r = t(lambda: wp.run(["-c", "pass"], cache_dir=cd)); out["second_call_ms"] = ms
elif mode == "warm":
    wp.run(["-c", "pass"], cache_dir=cd)
    xs = [t(lambda: wp.run(["-c", "pass"], cache_dir=cd))[0] for _ in range(20)]
    out["pass_snapshot_median_ms"] = statistics.median(xs)
    xs = [t(lambda: wp.run(["-c", "pass"], snapshot=False, cache_dir=cd))[0] for _ in range(10)]
    out["pass_plain_median_ms"] = statistics.median(xs)
    for name, code in [("numpy", "import numpy"), ("pandas", "import pandas"), ("pandas_groupby", "import pandas as pd; pd.DataFrame({'a':[1,2,2],'b':[1,2,3]}).groupby('a').b.sum()"), ("sklearn", "import sklearn.linear_model")]:
        xs = []
        for _ in range(3):
            ms, r = t(lambda: wp.run(["-c", code], cache_dir=cd, deadline_s=120)); xs.append(ms)
        out[f"{name}_on_snapshot_median_ms"] = statistics.median(xs); out[f"{name}_fuel"] = r.fuel_used; out[f"{name}_exit"]=r.exit_code
    out["rss_mib"] = rss()
elif mode == "pkgsnap":
    wp.run(["-c", "pass"], cache_dir=cd)
    ms, snap = t(lambda: wp.make_package_snapshot(["pandas"], cache_dir=cd)); out["make_pandas_snapshot_ms"] = ms
    p = tempfile.mktemp(suffix=".snap"); snap.save(p); out["pandas_snapshot_file_bytes"] = os.path.getsize(p)
    code = "import pandas as pd; pd.DataFrame({'a':[1,2,2],'b':[1,2,3]}).groupby('a').b.sum()"
    xs = []
    for _ in range(10):
        ms, r = t(lambda: wp.run(["-c", code], snapshot=snap, cache_dir=cd)); xs.append(ms)
    out["pandas_groupby_from_pkg_snapshot_median_ms"] = statistics.median(xs); out["fuel"] = r.fuel_used; out["exit"] = r.exit_code
    xs = [t(lambda: wp.run(["-c", "pass"], snapshot=snap, cache_dir=cd))[0] for _ in range(10)]
    out["pass_from_pkg_snapshot_median_ms"] = statistics.median(xs)
    ms, snap2 = t(lambda: wp.make_package_snapshot(None, cache_dir=cd)); out["make_all_snapshot_ms"] = ms
    snap2.save(p); out["all_snapshot_file_bytes"] = os.path.getsize(p)
    xs = [t(lambda: wp.run(["-c", code], snapshot=snap2, cache_dir=cd))[0] for _ in range(10)]
    out["pandas_groupby_from_all_snapshot_median_ms"] = statistics.median(xs)
    out["rss_mib"] = rss()
print(json.dumps(out))
