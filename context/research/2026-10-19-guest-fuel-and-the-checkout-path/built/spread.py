"""Per row: fuel over two runs at each of two paths; the spread within a path and over all four."""
import json
import sys

def fuel(p):
    return {n: v["metrics"]["fuel"] for n, v in json.load(open(p))["checks"].items()
            if "fuel" in (v.get("metrics") or {})}

s1, s2, l1, l2 = (fuel(p) for p in sys.argv[1:5])
worst_all = worst_within = 0
for n in sorted(s1):
    vals = [s1[n], s2[n], l1[n], l2[n]]
    allr = max(vals) - min(vals)
    within = max(abs(s1[n] - s2[n]), abs(l1[n] - l2[n]))
    worst_all, worst_within = max(worst_all, allr), max(worst_within, within)
    if allr:
        print(f"{allr:5} within {within:5} {n} {vals}")
print(f"largest spread over all four runs {worst_all}; largest within one path {worst_within}; rows {len(s1)}")
