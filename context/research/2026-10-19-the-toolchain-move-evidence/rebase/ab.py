"""Spec 086's A/B: compare the fuel and bytes of two or more judge records made by the same judge
commit on one machine, each against the first (the base).

usage: ab.py NAME=BASE.json NAME=B.json [NAME=C.json ...] [--rows N] [--steps]
  --steps: compare each record with the one before it, not with the base.
Prints, per pair and per kind (fuel, bytes): rows compared, up and down by more than 0.01%, the
median, minimum and maximum, the sum; then the N largest moves.
"""

import json
import statistics
import sys

args = [a for a in sys.argv[1:] if not a.startswith("--")]
rows_n = 15
if "--rows" in sys.argv:
    rows_n = int(sys.argv[sys.argv.index("--rows") + 1])
    args = [a for a in args if a != str(rows_n)]
steps = "--steps" in sys.argv


def load(path):
    out = {}
    for node, rec in json.load(open(path))["checks"].items():
        if rec.get("status") != "pass":
            continue
        for kind, val in (rec.get("metrics") or {}).items():
            if kind in ("fuel", "bytes") and isinstance(val, (int, float)) and val:
                out[(kind, node)] = val
    return out


named = [(a.split("=", 1)[0], load(a.split("=", 1)[1])) for a in args]
for i in range(1, len(named)):
    (an, a), (bn, b) = (named[i - 1] if steps else named[0]), named[i]
    print(f"== {an} -> {bn}")
    for kind in ("fuel", "bytes"):
        keys = sorted(k for k in a if k in b and k[0] == kind)
        if not keys:
            continue
        pct = [(b[k] - a[k]) / a[k] * 100 for k in keys]
        up = sum(p > 0.01 for p in pct)
        down = sum(p < -0.01 for p in pct)
        sa, sb = sum(a[k] for k in keys), sum(b[k] for k in keys)
        print(
            f"{kind}: {len(keys)} rows, {up} up and {down} down by >0.01%, "
            f"median {statistics.median(pct):+.3f}%, min {min(pct):+.3f}%, max {max(pct):+.3f}%, "
            f"sum {sa:,} -> {sb:,} ({(sb - sa) / sa * 100:+.3f}%)"
        )
        order = sorted(zip(pct, keys), key=lambda t: -abs(t[0]))[:rows_n]
        for p, k in order:
            print(f"  {p:+.3f}%  {a[k]:,} -> {b[k]:,}  {k[1]}")
