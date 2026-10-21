"""Deal the release groups into N serial lanes by estimated fuel (longest first), one node-id file
per lane, for N judge processes side by side.

    uv run python lanes.py <N> <out prefix> [group ...]   (default: every release group)
"""

import json
import sys
import tomllib
from pathlib import Path

SP = Path(__file__).parent
W = Path("/Users/claygendron/Git/Repos/wasi_python/.claude/worktrees/agent-aab0b516adb4e5c06")
n, prefix, only = int(sys.argv[1]), sys.argv[2], set(sys.argv[3:])
groups = json.loads((SP / "groups.json").read_text())
est = {g["name"]: g.get("est", 300) for gs in groups.values() for g in gs}
est |= {"scipy-special": 14000, "scipy-stats": 14000, "scipy-smoke-slow": 600}
measured = json.loads((SP / "measured.json").read_text())
names = []
for fam in ("scipy", "scikit-learn", "statsmodels"):
    cfg = tomllib.loads((W / f"tests/upstream/{fam}.toml").read_text())
    for name, g in cfg["groups"].items():
        if g.get("tier") == "release" and (not only or name in only):
            names.append(name)
cost = {g: measured.get(g, est.get(g, 300e9) * 1e9) / 1e9 if g in measured else est.get(g, 300) for g in names}
lanes = [[] for _ in range(n)]
load = [0.0] * n
for g in sorted(names, key=lambda g: -cost[g]):
    i = load.index(min(load))
    lanes[i].append(g)
    load[i] += cost[g]
for i, lane in enumerate(lanes):
    p = Path(f"{prefix}{i + 1}.txt")
    p.write_text(
        "".join(f"tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[{g}]\n" for g in lane)
    )
    print(p, len(lane), round(load[i]), "G")
