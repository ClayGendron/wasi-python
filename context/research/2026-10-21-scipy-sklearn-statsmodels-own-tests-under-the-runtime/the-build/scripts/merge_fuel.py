"""Merge measured fuel from the measurement plugin's jsonl files into measured.json, for groups
the TOMLs still hold (a later file wins), and list the release groups still unmeasured.

    uv run python merge_fuel.py <jsonl dir> ... [--lanes N prefix]
"""

import json
import sys
import tomllib
from pathlib import Path

SP = Path(__file__).parent
W = Path("/Users/claygendron/Git/Repos/wasi_python/.claude/worktrees/agent-aab0b516adb4e5c06")
args = sys.argv[1:]
lanes = None
if "--lanes" in args:
    i = args.index("--lanes")
    lanes = (int(args[i + 1]), args[i + 2])
    args = args[:i]
groups = {}
for fam in ("scipy", "scikit-learn", "statsmodels"):
    cfg = tomllib.loads((W / f"tests/upstream/{fam}.toml").read_text())
    groups |= cfg["groups"]
measured = json.loads((SP / "measured.json").read_text())
facts = json.loads((SP / "facts.json").read_text()) if (SP / "facts.json").exists() else {}
for d in args:
    for f in sorted(Path(d).glob("*.jsonl")):
        for line in f.read_text().splitlines():
            r = json.loads(line)
            if "test_upstream_suite[" not in r["node"]:
                continue
            g = r["node"].split("[", 1)[1][:-1]
            fuel = r["metrics"].get("fuel")
            if g in groups and fuel and fuel < groups[g]["fuel"]:  # finished under its cap
                measured[g] = int(fuel)
                facts[g] = r["facts"]
(SP / "measured.json").write_text(json.dumps(measured, indent=1, sort_keys=True))
(SP / "facts.json").write_text(json.dumps(facts, indent=1, sort_keys=True))
todo = [g for g, v in groups.items() if v.get("tier") == "release" and g not in measured]
print(len(todo), "release groups unmeasured")
if lanes:
    n, prefix = lanes
    est = {g: groups[g]["fuel"] / 3 for g in todo}
    buckets = [[] for _ in range(n)]
    load = [0.0] * n
    for g in sorted(todo, key=lambda g: -est[g]):
        i = load.index(min(load))
        buckets[i].append(g)
        load[i] += est[g]
    for i, b in enumerate(buckets):
        Path(f"{prefix}{i + 1}.txt").write_text(
            "".join(f"tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[{g}]\n" for g in b)
        )
        print(f"{prefix}{i + 1}.txt", len(b), round(load[i] / 1e9), "G cap/3")
