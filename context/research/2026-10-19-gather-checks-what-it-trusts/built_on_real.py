# Records: gh run download <run> -p 'record-*' -D <records dir>. Data only: parsed as JSON, never run.
"""Spec 085, criteria 2 and 3 at build: the built gather on real records.

    uv run python <this> <records dir> <accepted commit> <out dir>

The honest records give a baseline of red lines (their collection, judge and set_sums predate this
branch, so G2, G3 and G7 lines are expected there). Criterion 3: the baseline holds no line of the
new G4 and G5 rules and no G2 wasmtime line. Then each forgery is applied and re-hashed, and the
lines it adds to the baseline are printed: each must be its own rule's, and nothing else."""

import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "tests")
from harness import gather, paths, plugin, shards  # noqa: E402

src, commit, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])


def show(path):
    return subprocess.run(["git", "show", f"{commit}:{path}"], capture_output=True, text=True,
                          check=True).stdout


originals = {}
for f in sorted(src.glob("record-*/latest.json")):
    name = f.parent.name.removeprefix("record-")
    system, shard = ("build", "build") if name == "build-build" else name.split("-", 1)
    originals[(system, shard)] = json.loads(f.read_text())
accepted = json.loads(show("context/progress/accepted.json"))
vols = subprocess.run(["git", "ls-tree", "--name-only", commit, "context/progress/"],
                      capture_output=True, text=True, check=True).stdout.split()
history_lines = [x for v in sorted(v for v in vols if "/history" in v)
                 for x in show(v).splitlines() if x.strip()]
goal, units, may_block = gather.collect()
gaps, _ = plugin.load_gaps(paths.KNOWN_GAPS)
meta = originals[("build", "build")]["meta"]


def run(edit, name):
    records = copy.deepcopy(originals)
    edit(records)
    d = out / name
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
        plan=shards.load(), records_dir=d, handed=handed, wasm_sha256=meta["artifact"],
        set_sums_sha256="5" * 64, wasmtime=gather.locked_version("wasmtime"), may_block=may_block,
        goal_nodes=goal, unit_nodes=units, groups=shards.group_of(), accepted=accepted,
        history_lines=history_lines, gaps=set(gaps), judge_hash=meta["judge"]["hash"],
        head=meta["commit"], tag=False))
    return set(v.red)


def block_everywhere(node, need):
    def edit(records):
        for r in records.values():
            c = r["checks"][node]
            if c["status"] != "deselected":
                c.update(status="blocked", need=need, reason=f"needs: {need}", metrics={})
    return edit


def fuel_check(records):
    r = records[("windows", "own-guest")]
    return next(n for n, c in sorted(r["checks"].items())
                if c["status"] == "pass" and "fuel" in c.get("metrics", {})
                and "fuel" in accepted["checks"].get(n, {}).get("metrics", {}).get("darwin-arm64", {}))


def drop_fuel(records):
    del records[("windows", "own-guest")]["checks"][fuel_check(records)]["metrics"]["fuel"]


def fuel_x10_other_wasmtime(records):
    r = records[("macos", "own-guest")]
    for c in r["checks"].values():
        if "fuel" in c.get("metrics", {}):
            c["metrics"]["fuel"] *= 10
    r["meta"]["wasmtime"] = "48.0.0"


def fuel_nan(records):  # the build review's B1
    for c in records[("macos", "own-guest")]["checks"].values():
        if "fuel" in c.get("metrics", {}):
            c["metrics"]["fuel"] = float("nan")


def suite(key, value):
    def edit(records):
        records[key]["suite"] = value
    return edit


NEW = ("which its check does not call", "which does not block on", ": suite ", "records no ",
       "is not a number", "is not uv.lock's", "is not a mapping")
base = run(lambda r: None, "honest")
print(f"honest records: {len(base)} red lines; by rule:",
      {k: sum(x.startswith(k) for x in base) for k in ("G1", "G2", "G3", "G4", "G5", "G6", "G7")})
print("  of them, lines of the new rules:", sorted(x for x in base if any(n in x for n in NEW)) or "none")
SANDBOX = "tests/checks/test_v1_2_hostile_guest.py::test_mount_descriptors_are_bounded[plain]"
for name, edit in [
    ("no-network check blocked by 'oracle' everywhere",
     block_everywhere("tests/checks/test_v1_2_portable_and_sealed.py::test_guest_has_no_network", "oracle")),
    ("numpy-core suite blocked by 'three systems' everywhere",
     block_everywhere("tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[numpy-core]",
                      "three systems")),
    ("descriptor check blocked on macOS and Linux too", block_everywhere(SANDBOX, "descriptor limit")),
    ("linux/own-runner suite {}", suite(("linux", "own-runner"), {})),
    ("windows/own-runner suite zeros", suite(("windows", "own-runner"), {"passed": 0, "skipped": 0, "total": 0})),
    ("windows/own-guest drops one check's fuel", drop_fuel),
    ("macos/own-guest fuel x10 under wasmtime 48.0.0", fuel_x10_other_wasmtime),
    ("macos/own-guest every fuel NaN", fuel_nan),
]:
    added = sorted(run(edit, name.replace(" ", "_").replace("'", "")[:40]) - base)
    print(f"- {name}: adds {len(added)}")
    for x in added[:6]:
        print("    ", x[:200])
