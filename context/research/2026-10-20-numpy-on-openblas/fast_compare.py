"""Spec 100's claim list: two fast-tier records (build/progress/latest.json) compared row by row,
099's own record of its built set (the base) against this branch's of its set. Prints status
changes, new and missing rows, and every metric that moved, sorted by percentage.
Usage: fast_compare.py <base latest.json> <new latest.json>"""

import json
import sys

base = json.load(open(sys.argv[1]))["checks"]
new = json.load(open(sys.argv[2]))["checks"]
print(f"rows: base {len(base)}, new {len(new)}")
for k in sorted(set(new) - set(base)):
    print(f"NEW {new[k]['status']} {k}")
for k in sorted(set(base) - set(new)):
    print(f"MISSING (was {base[k]['status']}) {k}")
for k in sorted(set(base) & set(new)):
    if base[k]["status"] != new[k]["status"]:
        print(f"STATUS {base[k]['status']} -> {new[k]['status']} {k}")
moved = []
for k in sorted(set(base) & set(new)):
    for m, v in (new[k].get("metrics") or {}).items():
        b = (base[k].get("metrics") or {}).get(m)
        if isinstance(v, (int, float)) and isinstance(b, (int, float)) and b and v != b:
            moved.append(((v - b) / b * 100, k, m, b, v))
grew = [x for x in moved if x[0] > 0]
fell = [x for x in moved if x[0] < 0]
print(f"metrics moved: {len(moved)} ({len(grew)} grew, {len(fell)} fell)")
for pct, k, m, b, v in sorted(moved, reverse=True):
    print(f"{pct:+9.3f}%  {m} {b} -> {v}  {k}")
