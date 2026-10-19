"""Every fuel row's value in each run record, as one TSV: accepted, then each record named.
Usage: table.py <accepted.json> <label=latest.json>... > fuels.tsv"""
import json
import sys

acc = {n: v["metrics"]["darwin-arm64"]["fuel"] for n, v in json.load(open(sys.argv[1]))["checks"].items()
       if "fuel" in v["metrics"].get("darwin-arm64", {})}
cols = [a.split("=", 1) for a in sys.argv[2:]]
runs = [{n: v["metrics"]["fuel"] for n, v in json.load(open(p))["checks"].items()
         if "fuel" in (v.get("metrics") or {})} for _, p in cols]
print("\t".join(["row", "accepted", *(c for c, _ in cols)]))
for n in sorted(acc):
    print("\t".join([n, str(acc[n]), *(str(r.get(n, "")) for r in runs)]))
