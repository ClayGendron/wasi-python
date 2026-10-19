"""Spec 073's build: every fuel row that moved, the full judge's record (build/progress/latest.json)
against context/progress/accepted.json, darwin-arm64; grouped by binary and direction.

    uv run python <this file> <latest.json>
"""

import json
import sys

acc = json.load(open("context/progress/accepted.json"))["checks"]
lat = json.load(open(sys.argv[1]))["checks"]
rows = []
for node, rec in lat.items():
    if not isinstance(rec, dict):
        continue
    new = (rec.get("metrics") or {}).get("fuel")
    old = ((acc.get(node) or {}).get("metrics") or {}).get("darwin-arm64", {}).get("fuel")
    if new is None or old is None or new == old:
        continue
    rows.append((new - old, (new - old) / old, node, old, new))
up = [r for r in rows if r[0] > 0]
down = [r for r in rows if r[0] < 0]
print(f"rows moved: {len(rows)} ({len(up)} up, {len(down)} down)")
for label, pick in (("snapshot", "[snapshot"), ("plain", "[plain")):
    sel = [r for r in rows if pick in r[2]]
    if sel:
        print(f"{label}: {len(sel)} rows; rise from {min(r[0] for r in sel):+,} to {max(r[0] for r in sel):+,}")
other = [r for r in rows if "[snapshot" not in r[2] and "[plain" not in r[2]]
print(f"unparametrised: {len(other)} rows")
print("largest rises:")
for r in sorted(up, reverse=True)[:8]:
    print(f"  {r[0]:+,} ({r[1]:+.2%}) {r[2]}  {r[3]:,} -> {r[4]:,}")
print("largest rises in percent:")
for r in sorted(up, key=lambda r: -r[1])[:5]:
    print(f"  {r[1]:+.2%} ({r[0]:+,}) {r[2]}")
print("falls:")
for r in sorted(down)[:12]:
    print(f"  {r[0]:+,} ({r[1]:+.2%}) {r[2]}")
