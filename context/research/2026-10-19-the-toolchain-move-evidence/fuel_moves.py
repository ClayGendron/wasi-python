"""Compare a judge run's fuel and bytes with the accepted record: per-metric ratio, distribution.

usage: fuel_moves.py ACCEPTED.json LATEST.json [PLATFORM]
"""

import json
import statistics
import sys

acc = json.load(open(sys.argv[1]))["checks"]
new = json.load(open(sys.argv[2]))["checks"]
plat = sys.argv[3] if len(sys.argv) > 3 else "darwin-arm64"
rows = []
for node, rec in new.items():
    old = acc.get(node)
    if not old:
        continue
    for name, val in (rec.get("metrics") or {}).items():
        if name not in ("fuel", "bytes"):
            continue
        v = val
        o = (old.get("metrics") or {}).get(plat, {}).get(name)
        if isinstance(o, dict):
            o = o.get("value")
        if v is None or o is None or not o:
            continue
        rows.append((name, node, o, v, (v - o) / o))
for kind in ("fuel", "bytes"):
    rs = [r for r in rows if r[0] == kind]
    if not rs:
        continue
    pct = [r[4] * 100 for r in rs]
    up = sum(1 for p in pct if p > 0.01)
    down = sum(1 for p in pct if p < -0.01)
    print(f"{kind}: {len(rs)} compared, {up} up >0.01%, {down} down >0.01%, "
          f"median {statistics.median(pct):+.3f}%, min {min(pct):+.3f}%, max {max(pct):+.3f}%, "
          f"sum {sum(r[2] for r in rs):,} -> {sum(r[3] for r in rs):,}")
    for r in sorted(rs, key=lambda r: -abs(r[4]))[:12]:
        print(f"  {r[4] * 100:+.3f}%  {r[2]:,} -> {r[3]:,}  {r[1]}")
