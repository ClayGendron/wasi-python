# Records: gh run download 39255794160 -p 'record-*' -D <records dir> (the a7 tag run; 39265738300 for
# spec 065's dry run). Data only: parsed as JSON, never run. Spec 085's research, 2026-10-19.
"""Spec 085: forgeries on the a7 tag run's own 19 records (run 39255794160), each re-hashed after
the edit as a compromised job would hand on its hash, against today's gather.gather. The gather's
collection is this worktree's (main a6dfc17: the tag 2737b29 plus a version bump and documents, no
test changed); accepted.json and the history are the tag's; HEAD and the judge hash are taken from
the records (the tag run's gather computed the same). Run from the worktree:
    uv run python <this> <records dir> <scratch dir>"""

import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "tests")
from harness import gather, paths, plugin, shards  # noqa: E402

src, out = Path(sys.argv[1]), Path(sys.argv[2])
TAG = "2737b29"


def show(path):
    return subprocess.run(["git", "show", f"{TAG}:{path}"], capture_output=True, text=True,
                          check=True).stdout


originals = {}
for f in sorted(src.glob("record-*/latest.json")):
    name = f.parent.name.removeprefix("record-")
    system, shard = ("build", "build") if name == "build-build" else name.split("-", 1)
    originals[(system, shard)] = json.loads(f.read_text())
accepted = json.loads(show("context/progress/accepted.json"))
history_lines = [x for v in ("history.jsonl", "history-00060.jsonl")
                 for x in show(f"context/progress/{v}").splitlines() if x.strip()]
goal, units = gather.collect()
gaps, _ = plugin.load_gaps(paths.KNOWN_GAPS)
plan, groups = shards.load(), shards.group_of()
meta = originals[("build", "build")]["meta"]


def run(name, edit):
    records = copy.deepcopy(originals)
    edit(records)
    d = out / name.replace(" ", "_").replace("'", "")[:50]
    shutil.rmtree(d, ignore_errors=True)
    handed = {}
    for (system, shard), r in records.items():
        folder = d / gather.JOB[system]
        if system != "build":
            folder = folder / f"record-{system}-{shard}"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "latest.json").write_text(json.dumps(r, sort_keys=True, indent=1) + "\n")
        handed[(system, shard)] = paths.sha256_file(folder / "latest.json")
    v = gather.gather(gather.Inputs(
        plan=plan, records_dir=d, handed=handed, wasm_sha256=meta["artifact"], goal_nodes=goal,
        unit_nodes=units, groups=groups, accepted=accepted, history_lines=history_lines,
        gaps=set(gaps), judge_hash=meta["judge"]["hash"], head=meta["commit"], tag=False))
    print(f"{'RED  ' if v.red else 'GREEN'} {name}" + (f": {v.red[:3]}" if v.red else ""))


GUEST = [(s, "own-guest") for s in ("macos", "linux", "windows")]
PROBE_FUEL = "tests/checks/test_v1_2_hostile_guest.py::test_recursion_raises_recursionerror"


def block_everywhere(node, need):
    def edit(records):
        for k, r in records.items():
            c = r["checks"][node]
            if c["status"] != "deselected":
                c.update(status="blocked", need=need, reason=f"needs: {need}", metrics={})
    return edit


def first_fuel_check(records):
    r = records[("windows", "own-guest")]
    return next(n for n, c in sorted(r["checks"].items())
                if c["status"] == "pass" and "fuel" in c.get("metrics", {})
                and "fuel" in accepted["checks"].get(n, {}).get("metrics", {}).get("darwin-arm64", {}))


def drop_fuel_windows(records):
    node = first_fuel_check(records)
    print("   (the check:", node, ")")
    del records[("windows", "own-guest")]["checks"][node]["metrics"]["fuel"]


def empty_suite(records):
    records[("linux", "own-runner")]["suite"] = {}


def zero_suite(records):
    records[("windows", "own-runner")]["suite"] = {"passed": 0, "skipped": 0, "total": 0}


SANDBOX = "tests/checks/test_v1_2_hostile_guest.py::test_mount_descriptors_are_bounded[plain]"
run("the tag run's records as they are", lambda r: None)
run("test_v1_2_portable_and_sealed's sealed check blocked by 'oracle' on all three systems",
    block_everywhere("tests/checks/test_v1_2_portable_and_sealed.py::test_guest_has_no_network", "oracle"))
run("the numpy-core suite blocked by 'three systems' in every record",
    block_everywhere("tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[numpy-core]",
                     "three systems"))
run("the descriptor-limit check blocked on macOS and Linux too", block_everywhere(SANDBOX, "descriptor limit"))
run("linux/own-runner's suite is {} (538 unit tests in its share)", empty_suite)
run("windows/own-runner's suite is all zeros (538 unit tests in its share)", zero_suite)
run("a windows/own-guest record drops one check's fuel", drop_fuel_windows)
