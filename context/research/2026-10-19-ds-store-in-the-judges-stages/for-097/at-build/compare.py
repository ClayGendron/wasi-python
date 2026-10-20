"""Spec 097, criterion 3: each row's fuel and status across the four legs' records.
usage: compare.py DIR  (reads DIR/{base-1,build-1,base-2,build-2}.json)"""

import json
import sys
from pathlib import Path

LEGS = ("base-1", "base-2", "build-1", "build-2")


def rows(record: dict) -> dict:
    checks = record.get("checks", record)
    out = {}
    for node, c in checks.items():
        if not isinstance(c, dict):
            continue
        fuel = None
        m = c.get("metrics") or {}
        if "fuel" in m:
            fuel = m["fuel"]
        else:
            for v in m.values():
                if isinstance(v, dict) and "fuel" in v:
                    fuel = v["fuel"]
        out[node] = (c.get("status"), fuel)
    return out


d = Path(sys.argv[1])
got = {leg: rows(json.loads((d / f"{leg}.json").read_text())) for leg in LEGS}
nodes = sorted(set().union(*(set(g) for g in got.values())))
same = differ = 0
for node in nodes:
    vals = [got[leg].get(node, ("absent", None)) for leg in LEGS]
    fuels = {v[1] for v in vals}
    stats = {v[0] for v in vals}
    ok = len(fuels) == 1 and None not in fuels and stats == {"pass"}
    same += ok
    differ += not ok
    tag = "same" if ok else "DIFFER"
    print(f"{tag} {node.split('::')[-1]}: " + ", ".join(f"{leg} {s} {f}" for leg, (s, f) in zip(LEGS, vals)))
print(f"{same} rows one value and pass on all four legs; {differ} not")
