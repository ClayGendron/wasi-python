"""From the poller's log and the judge's measured fuel, each folder session's time per test file
(and per test, for the largest files), as a share of the session's fuel: a packing estimate.

    uv run python split_plan.py <poll.tsv> <fuel jsonl dir> [group ...]

Prints, for each group past 480 G, its files with their estimated fuel, and writes
filefuel.json: {group: {"start": G, "files": {file: G}, "tests": {file: [[node, G], ...]}}}.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

SP = Path(__file__).parent
poll, fueldir, only = Path(sys.argv[1]), Path(sys.argv[2]), set(sys.argv[3:])
fuel = {}
for f in fueldir.glob("*.jsonl"):
    for line in f.read_text().splitlines():
        d = json.loads(line)
        if "test_upstream_suite[" in d["node"] and "fuel" in d["metrics"]:
            fuel[d["node"].split("[", 1)[1][:-1]] = d["metrics"]["fuel"]

# sessions: (run key) -> list of (t, line)
sessions = defaultdict(list)
for line in poll.read_text().splitlines():
    t, run, text = line.split("\t", 2)
    sessions[run].append((float(t), text))

out = json.loads((SP / "filefuel.json").read_text()) if (SP / "filefuel.json").exists() else {}
groups = json.loads((SP / "groups.json").read_text())
paths_of = {g["name"]: g["paths"] for gs in groups.values() for g in gs}
import tomllib  # noqa: E402

_plan = tomllib.loads((SP / "smoke.toml").read_text())
paths_of["scipy-smoke-slow"] = [p for g in _plan["scipy"]["smoke"].values() for p in g["paths"]]

# a session is a group's when its collected files lie under the group's paths and it ended
for run, rows in sessions.items():
    ended = any(t.startswith("E ") for _, t in rows)
    starts = [(t, x[2:]) for t, x in rows if x.startswith("S ")]
    if not starts:
        continue
    files_seen = {n.split("::")[0] for _, n in starts}

    def covered(ps: list[str]) -> int:
        return sum(any(f == p or f.startswith(p.rstrip("/") + "/") for p in ps) for f in files_seen)

    best = max(paths_of, key=lambda c: (covered(paths_of[c]), -len(paths_of[c])))
    if covered(paths_of[best]) < len(files_seen):
        continue
    g = best
    if only and g not in only or g not in fuel:
        continue
    if not ended and fuel[g] < 19.9e12:
        continue  # an unfinished session that was not capped: not this group's measured one
    t0 = rows[0][0]
    later = [r[0][0] for k, r in sessions.items() if k.split("/")[1] == run.split("/")[1] and r[0][0] > rows[-1][0]]
    end = next((t for t, x in rows if x.startswith("E ")), min(later) if later else rows[-1][0] + 1.0)
    total = end - t0
    per_file = defaultdict(float)
    per_test = defaultdict(list)
    for (t, node), nxt in zip(starts, starts[1:] + [(end, None)]):
        dt = nxt[0] - t
        per_file[node.split("::")[0]] += dt
        per_test[node.split("::")[0]].append((node, dt))
    collect = starts[0][0] - t0
    G = fuel[g] / 1e9
    scale = G / total if total else 0
    out[g] = {
        "fuel": G,
        "start": collect * scale,
        "files": {f: s * scale for f, s in per_file.items()},
        "tests": {f: [[n, s * scale] for n, s in v] for f, v in per_test.items() if per_file[f] * scale > 150},
    }
    if G > 480:
        print(f"== {g}: {G:.1f} G, {total:.0f} s, collection {collect * scale:.1f} G")
        for f, s in sorted(per_file.items()):
            print(f"   {s * scale:8.1f}  {f}")
(SP / "filefuel.json").write_text(json.dumps(out, indent=1))
