"""Per fuel row: accepted (darwin-arm64) against the given run records' values (one value expected);
the change and its relative size, largest first. Usage: moved.py <accepted.json> <latest.json>..."""
import json
import sys

acc = {n: v["metrics"]["darwin-arm64"]["fuel"] for n, v in json.load(open(sys.argv[1]))["checks"].items()
       if "fuel" in v["metrics"].get("darwin-arm64", {})}
runs = [{n: v["metrics"]["fuel"] for n, v in json.load(open(p))["checks"].items()
         if "fuel" in (v.get("metrics") or {})} for p in sys.argv[2:]]
rows = []
for n in sorted(set.intersection(*(set(r) for r in runs))):
    vals = sorted({r[n] for r in runs})
    d = vals[-1] - acc[n]
    rows.append((d / acc[n], d, n, acc[n], vals))
up = [r for r in rows if r[1] > 0]
down = [r for r in rows if r[1] < 0]
over = [r for r in rows if r[0] > 1e-4]
print(f"rows {len(rows)}; rise {len(up)}; fall {len(down)}; same {len(rows) - len(up) - len(down)}; rise past 1e-4: {len(over)}")
for rel, d, n, a, vals in sorted(rows, key=lambda r: -abs(r[0])):
    if d:
        print(f"{rel * 100:+.4f}% {d:+11,} {n.split('::')[-1]:66} {a:>14,} -> {', '.join(f'{v:,}' for v in vals)}")
