"""Spec 100's growth against its base, from two release runs' shard records (gh run download -p
'record-*'): per system, every shard's checks merged, then each row's status and metrics compared
between 099's run and this branch's. Usage: ci_compare.py <099 records dir> <100 records dir>"""

import json
import sys
from pathlib import Path


def merged(root: Path, system: str) -> dict:
    checks = {}
    for d in sorted(root.glob(f"record-{system}-*")):
        for k, v in json.loads((d / "latest.json").read_text())["checks"].items():
            if v.get("status") != "deselected":
                checks[k] = v
    return checks


base_root, new_root = Path(sys.argv[1]), Path(sys.argv[2])
for system in ("macos", "linux", "windows"):
    base, new = merged(base_root, system), merged(new_root, system)
    print(f"== {system}: rows base {len(base)}, new {len(new)}")
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
    pcts = sorted(p for p, *_ in moved)
    if pcts:
        print(f"metrics moved: {len(moved)}; median {pcts[len(pcts) // 2]:+.3f}%")
    for pct, k, m, b, v in sorted(moved, reverse=True):
        if abs(pct) >= 0.1 or "upstream" in k or "job" in k:
            print(f"{pct:+9.3f}%  {m} {b} -> {v}  {k}")
