"""Per-file seconds of a pytest step in a GitHub job log: the time up to each progress line goes to its file."""
import re, sys
from datetime import datetime
def perfile(path, step):
    prev = cur = None; acc = {}
    for l in open(path, errors="replace"):
        if f"\t{step}" not in l: continue
        m = re.search(r"\t(?:\ufeff)?(\d{4}-\d\d-\d\dT[\d:.]+)Z (.*)$", l.rstrip("\n"))
        if not m: continue
        ts = datetime.fromisoformat(m[1][:26]); txt = m[2]
        if txt.startswith("collected"): prev = ts; continue
        if prev is None: continue
        mm = re.match(r"(tests/\S+\.py) ", txt)
        if mm: cur = mm[1]
        if "%]" in txt and cur:
            acc[cur] = acc.get(cur, 0) + (ts - prev).total_seconds(); prev = ts
    return acc
if __name__ == "__main__":
    step = sys.argv[1]
    cols = [perfile(p, step) for p in sys.argv[2:]]
    files = sorted(set().union(*cols), key=lambda f: -max(c.get(f, 0) for c in cols))
    print("file".ljust(48), *[p.rsplit("-",1)[-1][:10].rjust(10) for p in sys.argv[2:]])
    for f in files: print(f.ljust(48), *[f"{c.get(f,0):10.1f}" for c in cols])
    print("total".ljust(48), *[f"{sum(c.values()):10.1f}" for c in cols])
