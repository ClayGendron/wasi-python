"""The moves of every fuel row against accepted, in aggregate: total, mean and median relative
change. Usage: aggregate.py <accepted.json> <latest.json>"""
import json, statistics, sys
acc = {n: v["metrics"]["darwin-arm64"]["fuel"] for n, v in json.load(open(sys.argv[1]))["checks"].items()
       if "fuel" in v["metrics"].get("darwin-arm64", {})}
run = {n: v["metrics"]["fuel"] for n, v in json.load(open(sys.argv[2]))["checks"].items() if "fuel" in (v.get("metrics") or {})}
rows = [n for n in run if n in acc and "stylesheets_and_entities" not in n]
rel = [(run[n] - acc[n]) / acc[n] for n in rows]
print(f"rows {len(rows)} (the two lxml grant rows left out: their fuel follows the checkout's path, spec 081)")
print(f"total {sum(run[n] for n in rows) - sum(acc[n] for n in rows):+,} of {sum(acc[n] for n in rows):,} ({(sum(run[n] for n in rows) / sum(acc[n] for n in rows) - 1) * 100:+.5f}%)")
print(f"mean {statistics.mean(rel) * 100:+.5f}%  median {statistics.median(rel) * 100:+.5f}%  largest rise {max(rel) * 100:+.4f}%  largest fall {min(rel) * 100:+.4f}%")
