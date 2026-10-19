"""The release's gather: one verdict from every shard's hashed record (spec 063, Decision 9).

    uv run python tests/harness/gather.py --records records [--out release-record]

reads `WASM_SHA256` (the build job's `wasm-sha256`), one `RECORD_<SYSTEM>_<SHARD>` per shard (the
SHA-256 its job handed on; `-` as `_`, upper case), and `GITHUB_EVENT_NAME` and `GITHUB_REF_TYPE` as
the runner sets them (a step cannot override a `GITHUB_*` variable). It collects the judge once at
this commit and is red, one line per reason, unless G1 to G7 hold. It prints the merged
scoreboard, writes the merged record, and writes nothing under `context/progress/`: only the lane
accepts. It is spec 052's controller merge, across machines.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

if __package__ in (None, ""):  # run as a script: the harness package lives one folder up
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness import history, paths, scoreboard, shards  # noqa: E402

HEX64 = re.compile(r"[0-9a-f]{64}")
# The needs that may block a check in CI: local tooling (the oracle, the prior-art clones), the
# claim G6 proves instead, and a host capability one system lacks by nature (Windows has no
# RLIMIT_NOFILE). Not "wasmtime cli": its check runs in the build shard, on the host that has it.
CI_NEEDS = frozenset({"oracle", "prior-art clones", "three systems", "descriptor limit"})

# The worst status first; `deselected` last, so a check run anywhere is never shown deselected.
ORDER = ("fail", "unrun", "blocked", "gap", "pass", "deselected")
UPSTREAM_SUITE = re.compile(re.escape(shards.UPSTREAM_FILE) + r"::test_upstream_suite\[(.+)\]$")
JOB = {"build": "build", "macos": "judge-macos", "linux": "judge-linux", "windows": "judge-windows"}


def env_name(system: str, shard: str) -> str:
    return f"RECORD_{system}_{shard}".upper().replace("-", "_")


def expected_keys(plan: dict[str, shards.Shard]) -> list[tuple[str, str]]:
    """(system, shard) for every record the release hands on: each system's shards, and build."""
    keys = [("build", "build")] if "build" in plan else []
    return keys + [(s, name) for s in shards.OWN_SYSTEMS for name in shards.on(plan, s)]


@dataclass
class Inputs:
    plan: dict[str, shards.Shard]
    records_dir: Path
    handed: dict[tuple[str, str], str]  # (system, shard) -> the SHA-256 its job handed on
    wasm_sha256: str
    goal_nodes: list[str]  # the gather's own collection, goal checks
    unit_nodes: list[str]  # and unit tests
    groups: dict[str, str]  # upstream check -> group (shards.group_of)
    accepted: dict
    history_lines: list[str]
    gaps: set[str]
    judge_hash: str
    head: str
    tag: bool
    repo: Path = paths.REPO


@dataclass
class Verdict:
    red: list[str] = field(default_factory=list)
    records: dict[tuple[str, str], dict] = field(default_factory=dict)
    merged: dict = field(default_factory=dict)
    lines: list[str] = field(default_factory=list)


def _files(folder: Path) -> list[Path]:
    return sorted(p for p in folder.rglob("*") if p.is_file()) if folder.is_dir() else []


def gather(i: Inputs) -> Verdict:
    v = Verdict()
    red = v.red
    keys = expected_keys(i.plan)
    # G1: every record, and only those, one to one, each under its own job's folder.
    handed = {k: i.handed.get(k, "") for k in keys}
    for (system, shard), sha in handed.items():
        if not HEX64.fullmatch(sha):
            red.append(f"G1 {system}/{shard}: no SHA-256 handed on ({env_name(system, shard)})")
    shas = [s for s in handed.values() if s]
    if len(set(shas)) != len(shas):
        red.append("G1 one SHA-256 is handed on for two shards")
    if not HEX64.fullmatch(i.wasm_sha256):
        red.append("G1 the build job handed on no wasm-sha256")
    found: dict[str, list[Path]] = {}
    for f in _files(i.records_dir):
        found.setdefault(paths.sha256_file(f), []).append(f)
    wanted = set(shas)
    for sha, fs in sorted(found.items()):
        if sha not in wanted:
            red += [
                f"G1 {f.relative_to(i.records_dir).as_posix()}: a file no job handed on" for f in fs
            ]
    for (system, shard), sha in handed.items():
        fs = found.get(sha, []) if sha else []
        folder = i.records_dir / JOB[system]
        if len(fs) != 1:
            red.append(f"G1 {system}/{shard}: {len(fs)} files carry its SHA-256, not one")
            continue
        if not fs[0].is_relative_to(folder):
            red.append(f"G1 {system}/{shard}: its record is not under {JOB[system]}/")
            continue
        try:
            v.records[(system, shard)] = json.loads(fs[0].read_text())
        except (OSError, ValueError) as e:
            red.append(f"G1 {system}/{shard}: not a run record ({e})")
    # G2: each record says what it is.
    for (system, shard), r in v.records.items():
        meta = r.get("meta", {})
        where = f"G2 {system}/{shard}"
        wants = [
            (meta.get("shard") == shard, f"meta.shard is {meta.get('shard')!r}"),
            (
                str(meta.get("platform", "")).startswith(shards.PLATFORM[system] + "-"),
                f"platform {meta.get('platform')!r} is not {shards.PLATFORM[system]}",
            ),
            (meta.get("commit") == i.head, f"commit {str(meta.get('commit'))[:12]} is not HEAD"),
            (meta.get("artifact") == i.wasm_sha256, "artifact is not the build's python.wasm"),
            (
                meta.get("judge", {}).get("hash") == i.judge_hash,
                "judge hash is not this commit's",
            ),
            (meta.get("dirty") is False, "dirty"),
            (not meta.get("foreign"), f"steered from outside: {meta.get('foreign')}"),
            (not meta.get("partial"), "partial"),
            (meta.get("workers") == 0, f"workers {meta.get('workers')}"),
            (
                len(meta.get("overrides", [])) == 1
                and str(meta["overrides"][0]).startswith("--progress-latest "),
                f"overrides {meta.get('overrides')}",
            ),
        ]
        red += [f"{where}: {why}" for ok, why in wants if not ok]
    # G3: each shard ran exactly its share, and the shares are the whole judge.
    goal_share = shards.select(i.goal_nodes, i.plan, i.groups)
    unit_share = shards.select(i.unit_nodes, i.plan, i.groups)
    collected = set(i.goal_nodes)
    for name in i.plan:
        if not goal_share[name] and not unit_share[name]:
            red.append(f"G3 {name}: the plan selects nothing for it")
    run_somewhere: set[str] = set()
    for (system, shard), r in v.records.items():
        where = f"G3 {system}/{shard}"
        checks = r.get("checks", {})
        if set(checks) != collected:
            red.append(f"{where}: its collection is not the gather's ({len(checks)} goal checks)")
        ran = {n for n, c in checks.items() if c.get("status") != "deselected"}
        run_somewhere |= ran
        want = set(goal_share.get(shard, []))
        if ran != want:
            extra, missing = sorted(ran - want), sorted(want - ran)
            red.append(f"{where}: ran other goal checks (+{len(extra)} -{len(missing)})")
        units = r.get("meta", {}).get("units") or {}
        mine = unit_share.get(shard, [])
        if units.get("count") != len(mine) or units.get("digest") != shards.units_digest(mine):
            red.append(f"{where}: ran other unit tests ({units.get('count')} against {len(mine)})")
        if not ran and not units.get("count"):
            red.append(f"{where}: selected nothing")
    for node in sorted(collected - run_somewhere):
        red.append(f"G3 {node}: collected, run in no record")
    shared_units = {n for name in i.plan for n in unit_share[name]}
    for node in sorted(set(i.unit_nodes) - shared_units):
        red.append(f"G3 {node}: a unit test in no shard's share")
    # G4: nothing failed, the unit tests included (the build review, F6).
    for (system, shard), r in v.records.items():
        suite = r.get("suite", {})
        failed = suite.get("total", 0) - suite.get("passed", 0) - suite.get("skipped", 0)
        if failed:
            red.append(f"G4 {system}/{shard}: {failed} unit test(s) failed")
        for node, c in sorted(r.get("checks", {}).items()):
            status = c.get("status")
            where = f"G4 {system}/{shard} {node}"
            if status in ("fail", "unrun"):
                red.append(f"{where}: {status} {str(c.get('reason', ''))[:120]}")
            elif status == "gap" and node not in i.gaps:
                red.append(f"{where}: a gap tests/known_gaps.toml does not hold")
            elif status == "blocked" and c.get("need") not in CI_NEEDS:
                red.append(f"{where}: blocked by {c.get('need')!r}")
    # G5: the lane's acceptance holds.
    for (system, shard), r in v.records.items():
        try:
            rt = scoreboard.compare(r, i.accepted, i.repo)
        except (KeyError, TypeError) as e:
            red.append(f"G5 {system}/{shard}: not comparable with accepted.json ({e})")
            continue
        for what, nodes in (
            ("lost", rt.lost),
            ("absent", rt.absent),
            ("fewer", rt.fewer),
            ("grew", rt.growth),
            ("blocked, protected", rt.unrun),
        ):
            red += [f"G5 {system}/{shard}: {what} {n}" for n in nodes[:5]]
    for node, acc in sorted(i.accepted.get("checks", {}).items()):
        if acc.get("status") not in ("pass", "gap"):
            continue
        states = [r.get("checks", {}).get(node, {}) for r in v.records.values()]
        if any(c.get("status") in ("pass", "gap") for c in states):
            continue
        if any(c.get("status") == "blocked" and c.get("need") in CI_NEEDS for c in states):
            continue
        red.append(f"G5 {node}: accepted {acc.get('status')}, ran in no record")
    for node in sorted(collected):
        m = UPSTREAM_SUITE.match(node)
        if not m:
            continue
        runs = [
            (k, r["checks"][node])
            for k, r in v.records.items()
            if r.get("checks", {}).get(node, {}).get("status") == "pass"
        ]
        passes = {c.get("metrics", {}).get("passes") for _, c in runs}
        digests = {c.get("facts", {}).get("passed_digest") for _, c in runs}
        if len(passes) > 1 or len(digests) > 1:
            red.append(f"G5 {m[1]}: passes or passed_digest differ between systems")
        acc = i.accepted.get("checks", {}).get(node, {}).get("metrics", {}).get("darwin-arm64", {})
        if runs and "passes" in acc and passes != {acc["passes"]}:
            red.append(
                f"G5 {m[1]}: passes {sorted(passes, key=str)} is not accepted {acc['passes']}"
            )
    # G6: three systems.
    systems = {
        str(r.get("meta", {}).get("platform", "")).split("-")[0]
        for r in v.records.values()
        if r.get("checks", {}).get(history.PROBE, {}).get("status") == "pass"
    }
    if not {"darwin", "linux", "win32"} <= systems:
        red.append(f"G6 the probe passed on {sorted(systems)}, not darwin, linux and win32")
    # G7: python.wasm is the lane's accepted artifact; on a tag, the judge is the accepted one.
    newest = json.loads(i.history_lines[-1]) if i.history_lines else {}
    if newest.get("artifact") != i.wasm_sha256:
        red.append("G7 the newest acceptance is not on the release's python.wasm")
    if newest.get("dirty") is not False:
        red.append("G7 the newest acceptance was not made on a clean tree")
    if newest.get("partial_reason"):
        red.append("G7 the newest acceptance is partial")
    if i.tag and i.accepted.get("judge", {}).get("hash") != i.judge_hash:
        red.append("G7 a tag, and this commit's judge is not the accepted one")
    v.merged = merge(v.records, i)
    providers = {}
    shown = dict(v.merged)
    shown["suite"] = {
        k: sum(s.get(k, 0) for s in v.merged["suite"].values())
        for k in ("passed", "skipped", "total")
    }
    v.lines = scoreboard.render(shown, None, providers, red)
    if not red:
        at = next(
            (n for n, line in enumerate(v.lines) if line.startswith("not machine-checked")), -1
        )
        v.lines.insert(at, f"three systems: darwin linux win32 on {i.wasm_sha256}")
    return v


def merge(records: dict[tuple[str, str], dict], i: Inputs) -> dict:
    """One record of the release (Decision 9): each goal check's worst status across the records
    that ran it; the darwin record's metrics, else the linux record's, else any; `suite` per
    system."""
    checks: dict[str, dict] = {}
    pref = {"darwin": 0, "linux": 1, "win32": 2}
    for node in sorted(i.goal_nodes):
        found = []
        for (_, _), r in records.items():
            c = r.get("checks", {}).get(node)
            if c is not None:
                platform = str(r.get("meta", {}).get("platform", "")).split("-")[0]
                found.append((platform, c))
        if not found:
            continue
        worst = min(found, key=lambda pc: ORDER.index(pc[1].get("status", "fail")))[1]
        ran = [(p, c) for p, c in found if c.get("status") != "deselected"]
        source = min(ran, key=lambda pc: pref.get(pc[0], 9))[1] if ran else worst
        checks[node] = {**worst, "metrics": source.get("metrics", {})}
    suite: dict[str, dict] = {}
    for (system, _), r in records.items():
        s = suite.setdefault(shards.PLATFORM[system] if system != "build" else "build", {})
        for k, n in r.get("suite", {}).items():
            s[k] = s.get(k, 0) + n
    return {
        "meta": {
            "commit": i.head,
            "artifact": i.wasm_sha256,
            "judge": {"hash": i.judge_hash},
            "records": sorted(f"{s}/{n}" for s, n in records),
            "tag": i.tag,
        },
        "checks": checks,
        "suite": suite,
    }


# ---------------------------------------------------------------------------------------------
# The command line


class _Collector:
    """Each collected item's node id and `goal` marker, read as the plugin reads it."""

    def __init__(self) -> None:
        self.items: list[tuple[str, str | None]] = []

    def pytest_collection_finish(self, session) -> None:
        from harness import plugin

        self.items = [(item.nodeid, plugin.area_of(item)) for item in session.items]


def collect(repo: Path = paths.REPO) -> tuple[list[str], list[str]]:
    """The judge's collection at this commit: (goal checks, unit tests). No artifacts needed."""
    import contextlib
    import io

    import pytest

    c = _Collector()
    here = Path.cwd()
    os.chdir(repo)
    try:
        with contextlib.redirect_stdout(io.StringIO()):  # the per-file counts, not the verdict
            code = pytest.main(["--collect-only", "-qq", "-p", "no:cacheprovider"], plugins=[c])
    finally:
        os.chdir(here)
    if code != 0:
        raise SystemExit(f"the collection failed (pytest exit {code})")
    goal = [n for n, area in c.items if area is not None]
    return goal, [n for n, area in c.items if area is None]


def is_tag(environ) -> bool:
    """A pushed tag, as the runner names it: only then must the judge be the accepted one (G7)."""
    return environ.get("GITHUB_EVENT_NAME") == "push" and environ.get("GITHUB_REF_TYPE") == "tag"


def main(argv: list[str]) -> int:
    import argparse

    from harness import plugin

    ap = argparse.ArgumentParser(prog="gather.py")
    ap.add_argument("--records", required=True, type=Path)
    ap.add_argument("--out", default="release-record", type=Path)
    a = ap.parse_args(argv)
    plan = shards.load()
    handed = {k: os.environ.get(env_name(*k), "") for k in expected_keys(plan)}
    goal, units = collect()
    gaps, _ = plugin.load_gaps(paths.KNOWN_GAPS)
    head = subprocess.run(
        ["git", "-C", str(paths.REPO), "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    tag = is_tag(os.environ)
    v = gather(
        Inputs(
            plan=plan,
            records_dir=a.records,
            handed=handed,
            wasm_sha256=os.environ.get("WASM_SHA256", ""),
            goal_nodes=goal,
            unit_nodes=units,
            groups=shards.group_of(),
            accepted=json.loads(paths.ACCEPTED.read_text()),
            history_lines=history.lines(paths.PROGRESS),
            gaps=set(gaps),
            judge_hash=paths.judge_hash(paths.judge_files()),
            head=head,
            tag=tag,
        )
    )
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "record.json").write_text(scoreboard.dumps(v.merged))
    text = "\n".join(v.lines) + "\n"
    (a.out / "scoreboard.txt").write_text(text)
    for line in v.red:
        print(line)
    print(text, end="")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("```\n" + text + "```\n")
    return 1 if v.red else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
