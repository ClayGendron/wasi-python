"""Per fuel row: the spread (max - min) over the run records given; rows with a spread, and the
largest. Usage: spread.py <latest.json> ..."""
import json
import sys


def fuel(p):
    return {n: v["metrics"]["fuel"] for n, v in json.load(open(p))["checks"].items()
            if "fuel" in (v.get("metrics") or {})}


runs = [fuel(p) for p in sys.argv[1:]]
rows = sorted(set.intersection(*(set(r) for r in runs)))
worst, moved = 0, 0
for n in rows:
    vals = [r[n] for r in runs]
    s = max(vals) - min(vals)
    worst = max(worst, s)
    if s:
        moved += 1
        print(f"{s:5} {n.split('::')[-1]:70} {[v - min(vals) for v in vals]}")
print(f"rows {len(rows)}; rows with a spread {moved}; largest spread {worst}")
