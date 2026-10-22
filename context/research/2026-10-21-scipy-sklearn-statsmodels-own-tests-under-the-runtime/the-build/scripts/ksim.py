"""Simulate pytest's -k over a split file's known tests: which tests each split group actually
takes (`e_i and not (e_1 or ... e_{i-1})`, substring matching on the node's names, as pytest's
KeywordMatcher does, case-insensitive), against the polls' test lists.

    uv run python ksim.py [file ...]      prints, per split, each group's actual count and fuel
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

from _pytest.mark.expression import Expression

SP = Path(__file__).parent
W = Path("/Users/claygendron/Git/Repos/wasi_python/.claude/worktrees/agent-aab0b516adb4e5c06")
POLLS = sorted((W / "build/095").glob("poll-*.tsv"))


def names(node: str) -> list[str]:
    path, *rest = node.split("::")
    parts = path.split("/")
    return [*parts, *rest]


def matcher(node: str):
    ns = [n.lower() for n in names(node)]

    def m(sub: str, **_kw) -> bool:
        s = sub.lower()
        return any(s in n for n in ns)

    return m


def known_tests() -> dict[str, list[str]]:
    seen: dict[str, dict[str, None]] = defaultdict(dict)
    for p in POLLS:
        for line in p.read_text(errors="replace").splitlines():
            parts = line.split("\t", 2)
            if len(parts) == 3 and parts[2].startswith("S "):
                node = parts[2][2:]
                seen[node.split("::")[0]][node] = None
    return {f: list(v) for f, v in seen.items()}


def assign(tests: list[str], groups: list[str], keywords: list[str]) -> dict[str, list[str]]:
    exprs = [Expression.compile(k) for k in keywords]
    out: dict[str, list[str]] = {g: [] for g in groups}
    for t in tests:
        m = matcher(t)
        for g, e in zip(groups, exprs):
            if e.evaluate(m):
                out[g].append(t)
                break
        else:
            out[groups[-1]].append(t)
    return out


def main() -> None:
    splits = json.loads((SP / "splits.json").read_text())
    tests = known_tests()
    est = {}
    ff = json.loads((SP / "filefuel.json").read_text())
    for v in ff.values():
        for ts in v["tests"].values():
            for n, g in ts:
                est[n] = g
    only = set(sys.argv[1:])
    for fam, ss in splits.items():
        for s in ss:
            if only and s["file"] not in only:
                continue
            ts = tests.get(s["file"], [])
            a = assign(ts, s["groups"], s["keywords"])
            print(f"== {s['file']}: {len(ts)} known tests")
            for g in s["groups"]:
                print(f"   {g}: {len(a[g])} tests, {sum(est.get(t, 0) for t in a[g]):.0f} G est")


if __name__ == "__main__":
    main()
