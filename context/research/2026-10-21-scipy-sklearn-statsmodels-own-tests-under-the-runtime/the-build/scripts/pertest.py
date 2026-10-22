"""Per-test fuel estimates for each measured session, attributing sessions to groups by order:
the measurement plugin's lines are in execution order, and so are the guest folder's runs that
collect anything. Writes/merges filefuel.json in pass2.py's format:
{group: {"fuel": G, "start": G, "files": {file: G}, "tests": {file: [[node, G], ...]}}}.

    uv run python pertest.py <poll.tsv> <fuel jsonl dir> <guest dir name> <lane node-id file>
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

SP = Path(__file__).parent
poll, fueldir, gdir, lane = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4])
lane_set = {ln.split("[", 1)[1][:-1] for ln in lane.read_text().split()}
order = []
fuel = {}
for f in fueldir.glob("*.jsonl"):
    for line in f.read_text().splitlines():
        d = json.loads(line)
        if "test_upstream_suite[" in d["node"] and "fuel" in d["metrics"]:
            name = d["node"].split("[", 1)[1][:-1]
            if name in lane_set:
                order.append(name)
                fuel[name] = d["metrics"]["fuel"] / 1e9
sessions = defaultdict(list)
for line in poll.read_text().splitlines():
    t, run, text = line.split("\t", 2)
    r, g = run.split("/")
    if g == gdir:
        sessions[int(r.removeprefix("run-"))].append((float(t), text))
out = json.loads((SP / "filefuel.json").read_text()) if (SP / "filefuel.json").exists() else {}
test_runs = [n for n in sorted(sessions) if any(x.startswith(("S ", "C ")) for _, x in sessions[n])]
print(len(test_runs), "sessions with collection;", len(order), "groups with fuel")
for n, g in zip(test_runs, order):
    rows = sessions[n]
    starts = [(t, x[2:]) for t, x in rows if x.startswith("S ")]
    ends = [t for t, x in rows if x.startswith("E ")]
    if not starts or g not in fuel:
        print("skip", n, g, "no tests" if not starts else "no fuel")
        continue
    nxt_first = sessions[n + 1][0][0] if n + 1 in sessions else None
    end = ends[0] if ends else (nxt_first or rows[-1][0] + 1.0)
    t0 = rows[0][0]
    total = end - t0
    scale = fuel[g] / total if total > 0 else 0.0
    per_file = defaultdict(float)
    per_test = defaultdict(list)
    for (t, node), nx in zip(starts, starts[1:] + [(end, None)]):
        dt = (nx[0] - t) * scale
        f = node.split("::")[0]
        per_file[f] += dt
        per_test[f].append([node, dt])
    out[g] = {
        "fuel": fuel[g],
        "start": (starts[0][0] - t0) * scale,
        "files": dict(per_file),
        "tests": dict(per_test),
        "ended": bool(ends),
        "first": starts[0][1],
    }
    if not re.match(r"[\w/]+", starts[0][1]):
        print("odd", g)
(SP / "filefuel.json").write_text(json.dumps(out, indent=1))
print(len(sessions), "sessions,", len(order), "groups")
