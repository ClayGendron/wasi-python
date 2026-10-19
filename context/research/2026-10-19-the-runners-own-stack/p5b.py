import sys
sys.argv = sys.argv
from p5_threadsize import trial
w = int(sys.argv[1]); shape = sys.argv[2]; lo, hi, step = int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
def ok(t):
    code, res = trial(w, t, shape)
    good = code == 0 and (res.get("trapped") == "stack overflow" or res.get("stdout", "").strip().endswith("freed"))
    print(f"  T={t}: exit {code} trapped={res.get('trapped')} out={res.get('stdout','').strip()!r}", flush=True)
    return good
assert ok(hi)
while hi - lo > step:
    mid = (lo + hi) // 2 // step * step
    if ok(mid): hi = mid
    else: lo = mid
print(f"RESULT W={w} {shape}: smallest surviving T = {hi} ({(hi - w) / 1024:+.0f} KiB over W)")
