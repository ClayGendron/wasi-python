"""The release's gather: one verdict from every shard's hashed record (spec 063, Decision 9).

    uv run python tests/harness/gather.py --records records [--out release-record]

reads `WASM_SHA256` (the build job's `wasm-sha256`), `SET_SUMS_SHA256` (its `set-sums-sha256`, the
set's own `SHA256SUMS`; spec 085), one `RECORD_<SYSTEM>_<SHARD>` per shard (the SHA-256 its job
handed on; `-` as `_`, upper case), and `GITHUB_EVENT_NAME` and `GITHUB_REF_TYPE` as the runner
sets them (a step cannot override a `GITHUB_*` variable). It collects the judge once at this
commit and is red, one line per reason, unless G1 to G7 hold. It prints the merged
scoreboard, writes the merged record, and writes nothing under `context/progress/`: only the lane
accepts. It is spec 052's controller merge, across machines.
"""

from __future__ import annotations

import ast
import inspect
import json
import math
import os
import re
import subprocess
import sys
import textwrap
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

if __package__ in (None, ""):  # run as a script: the harness package lives one folder up
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness import history, paths, scoreboard, shards  # noqa: E402

HEX64 = re.compile(r"[0-9a-f]{64}")
# The needs that may block a check in CI, each with the systems (as `expected_keys` names them)
# that lack it: local tooling (the oracle, the prior-art clones) and the claim G6 proves instead,
# everywhere; a host capability one system lacks by nature (Windows has no RLIMIT_NOFILE, and a
# Windows guest deletes a read-only file itself, spec 094), there alone. Not "wasmtime cli": its
# check runs in the build shard, on the host that has it. A check may be blocked only by a need its
# own body names (spec 085, Decision 1).
EVERYWHERE = frozenset({"build", "macos", "linux", "windows"})
CI_NEEDS: dict[str, frozenset[str]] = {
    "oracle": EVERYWHERE,
    "prior-art clones": EVERYWHERE,
    "three systems": EVERYWHERE,
    "descriptor limit": frozenset({"windows"}),
    "read-only files": frozenset({"windows"}),
}

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
    set_sums_sha256: str  # the build's set's own SHA256SUMS (spec 085, Decision 4)
    wasmtime: str  # the version uv.lock names (spec 085, the pre-build review's F1)
    may_block: dict[str, frozenset[str]]  # goal check -> the CI needs its body names
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


def allowed(node: str, need, system: str, may_block: dict[str, frozenset[str]]) -> bool:
    """May this check be reported blocked by this need in this system's record (Decision 1)?"""
    if not isinstance(need, str):  # a list cannot be looked up (the build review, B3)
        return False
    return need in may_block.get(node, ()) and system in CI_NEEDS.get(need, ())


def _whole(x) -> bool:
    return type(x) is int and x >= 0


def _number(x) -> bool:
    """A metric value: an int, or a finite float. json reads NaN and Infinity, and the ratchet's
    `>` is false for NaN (the build review, B1)."""
    return type(x) is int or (type(x) is float and math.isfinite(x))


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
    if not HEX64.fullmatch(i.set_sums_sha256):
        red.append("G1 the build job handed on no set-sums-sha256")
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
                meta.get("set_sums") == i.set_sums_sha256,
                "set_sums is not the build's SHA256SUMS",
            ),
            (
                meta.get("wasmtime") == i.wasmtime,
                f"wasmtime {meta.get('wasmtime')!r} is not uv.lock's {i.wasmtime}",
            ),
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
    # G4: nothing failed, the unit tests included (the build review, F6); the tally is the share
    # (spec 085, Decision 2).
    for (system, shard), r in v.records.items():
        suite = r.get("suite", {})
        count = (r.get("meta", {}).get("units") or {}).get("count")
        tally = (
            [suite.get(k) for k in ("passed", "skipped", "total")]
            if isinstance(suite, dict)
            else []
        )
        if len(tally) != 3 or not all(map(_whole, tally)) or tally[2] != count:
            red.append(f"G4 {system}/{shard}: suite {suite} is not its {count} unit tests")
        elif tally[2] - tally[0] - tally[1]:
            red.append(f"G4 {system}/{shard}: {tally[2] - tally[0] - tally[1]} unit test(s) failed")
        for node, c in sorted(r.get("checks", {}).items()):
            status = c.get("status")
            where = f"G4 {system}/{shard} {node}"
            if status in ("fail", "unrun"):
                red.append(f"{where}: {status} {str(c.get('reason', ''))[:120]}")
            elif status == "gap" and node not in i.gaps:
                red.append(f"{where}: a gap tests/known_gaps.toml does not hold")
            elif status == "blocked" and (
                not isinstance(c.get("need"), str) or c.get("need") not in CI_NEEDS
            ):
                red.append(f"{where}: blocked by {c.get('need')!r}")
            elif status == "blocked" and c.get("need") not in i.may_block.get(node, ()):
                red.append(f"{where}: blocked by {c.get('need')!r}, which its check does not call")
            elif status == "blocked" and not allowed(node, c.get("need"), system, i.may_block):
                red.append(
                    f"{where}: blocked by {c.get('need')!r}, which does not block on {system}"
                )
    # G5: the lane's acceptance holds. First, every metric the lane accepted for a passing check,
    # on every system, each a finite number (spec 085, Decision 3; the build review, B1 and B3).
    # Values off darwin are not compared (Decision 9).
    for (system, shard), r in v.records.items():
        for node, c in sorted(r.get("checks", {}).items()):
            if c.get("status") != "pass":
                continue
            have = c.get("metrics", {})
            if not isinstance(have, dict):
                red.append(f"G5 {system}/{shard}: {node} metrics is not a mapping")
                continue
            acc = i.accepted.get("checks", {}).get(node, {}).get("metrics", {})
            want = set(acc.get("darwin-arm64", {})) - {"wasmtime"}
            for name in sorted(want - set(have)):
                red.append(f"G5 {system}/{shard}: {node} records no {name} (accepted.json has it)")
            for name, value in sorted(have.items()):
                if not _number(value):
                    red.append(f"G5 {system}/{shard}: {node} metric {name} is not a number")
    for (system, shard), r in v.records.items():
        try:
            rt = scoreboard.compare(r, i.accepted, i.repo)
        except (KeyError, TypeError, AttributeError) as e:
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
        states = [(s, r.get("checks", {}).get(node, {})) for (s, _), r in v.records.items()]
        if any(c.get("status") in ("pass", "gap") for _, c in states):
            continue
        if any(
            c.get("status") == "blocked" and allowed(node, c.get("need"), s, i.may_block)
            for s, c in states
        ):
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
    if newest.get("set_sums") != i.set_sums_sha256:  # a line from before spec 085 has none
        red.append("G7 the newest acceptance is not on the release's set (SHA256SUMS)")
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
        v.lines.insert(
            at, f"three systems: darwin linux win32 on {i.wasm_sha256} · set {i.set_sums_sha256}"
        )
    quiet = no_trap_anywhere(v.records)
    if quiet:  # never red: a fixed trap asks the change that closes it to go ahead (spec 065, C4)
        at = next(
            (n for n, line in enumerate(v.lines) if line.startswith("not machine-checked")), -1
        )
        v.lines.insert(at, "trap entries with no trap on any system: " + " · ".join(quiet))
    return v


def no_trap_anywhere(records: dict[tuple[str, str], dict]) -> list[str]:
    """The open trap entries (spec 065, Decision 1) that ran in at least one record and recorded
    "no trap on this host" in every record that ran them."""
    seen: dict[str, set[str]] = {}
    for r in records.values():
        for node, c in r.get("checks", {}).items():
            if "::test_upstream_trap[" in node and c.get("status") not in ("deselected", None):
                seen.setdefault(node, set()).add((c.get("facts") or {}).get("trap", ""))
    return [
        node.rsplit("[", 1)[1].rstrip("]")
        for node, facts in sorted(seen.items())
        if facts == {"no trap on this host"}
    ]


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
        need = checks[node].get("need")
        if need is not None and not isinstance(need, str):  # already red at G4 (B3)
            checks[node]["need"] = repr(need)
    suite: dict[str, dict] = {}
    for (system, _), r in records.items():
        s = suite.setdefault(shards.PLATFORM[system] if system != "build" else "build", {})
        tally = r.get("suite", {})
        for k, n in (tally if isinstance(tally, dict) else {}).items():
            if _whole(n):  # anything else is already red at G4 (spec 085, Decision 2)
                s[k] = s.get(k, 0) + n
    return {
        "meta": {
            "commit": i.head,
            "artifact": i.wasm_sha256,
            "set_sums": i.set_sums_sha256,
            "judge": {"hash": i.judge_hash},
            "records": sorted(f"{s}/{n}" for s, n in records),
            "tag": i.tag,
        },
        "checks": checks,
        "suite": suite,
    }


# ---------------------------------------------------------------------------------------------
# The command line


def _need_call(n: ast.AST) -> bool:
    if not isinstance(n, ast.Call):
        return False
    f = n.func
    return (isinstance(f, ast.Name) and f.id == "need") or (
        isinstance(f, ast.Attribute) and f.attr == "need"
    )


def needs_called(func) -> set[str]:
    """The needs a function's own source names as literal arguments of a `need(…)` or `….need(…)`
    call (spec 085, Decision 1). A need named any other way is not seen, so a check blocked by it
    is red in the gather; an unreadable source names none."""
    try:
        tree = ast.parse(textwrap.dedent(inspect.getsource(func)))
    except (OSError, TypeError, SyntaxError):
        return set()
    return {
        a.value
        for n in ast.walk(tree)
        if _need_call(n)
        for a in n.args
        if isinstance(a, ast.Constant) and isinstance(a.value, str)
    }


# The two files that define the needs' vocabulary; the scan skips them (Decision 1).
VOCABULARY_FILES = ("tests/harness/needs.py", "tests/harness/gather.py")


def hidden_ci_needs(repo: Path = paths.REPO) -> list[str]:
    """Every place a CI need is spelled where `needs_called` cannot see it (Decision 1, the
    pre-build review's F5 and its confirmation's c1), as `file:line: <string>`: a CI need string
    under tests/checks/ or in tests/conftest.py outside a `test_` function's body; under
    tests/harness/, one used as a call argument, a container member, a keyword value or a module
    constant (never a path piece such as `JOB_DIR / "oracle"`); and any `"needs: "` string,
    anywhere in that scope."""
    found = []
    files = sorted(
        {*repo.glob("tests/checks/**/*.py"), *repo.glob("tests/harness/*.py")}
        | (
            {repo / "tests" / "conftest.py"}
            if (repo / "tests" / "conftest.py").is_file()
            else set()
        )
    )
    for f in files:
        rel = f.relative_to(repo).as_posix()
        if rel in VOCABULARY_FILES:
            continue
        tree = ast.parse(f.read_text(encoding="utf-8"))
        harness = rel.startswith("tests/harness/")
        inside: set[int] = set()
        if not harness:
            for n in ast.walk(tree):
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith(
                    "test_"
                ):
                    # Its body only: decorators and default arguments are not inside (B2).
                    inside |= {id(m) for stmt in n.body for m in ast.walk(stmt)}
        parent = {id(c): n for n in ast.walk(tree) for c in ast.iter_child_nodes(n)}
        for n in ast.walk(tree):
            if not (isinstance(n, ast.Constant) and isinstance(n.value, str)):
                continue
            if n.value.startswith("needs: "):
                found.append(f"{rel}:{n.lineno}: {n.value!r}")
            elif n.value in CI_NEEDS and id(n) not in inside:
                up = parent.get(id(n))
                plain = (ast.Call, ast.Dict, ast.List, ast.Tuple, ast.Set, ast.keyword)
                # A module constant or a class attribute, or either through a conditional
                # expression (the confirmation's c1; the build review's B2).
                if isinstance(up, ast.IfExp):
                    up = parent.get(id(up))
                constant = isinstance(up, (ast.Assign, ast.AnnAssign)) and isinstance(
                    parent.get(id(up)), (ast.Module, ast.ClassDef)
                )
                if not harness or isinstance(up, plain) or constant:
                    found.append(f"{rel}:{n.lineno}: {n.value!r}")
    return found


def locked_version(name: str, lock: Path = paths.REPO / "uv.lock") -> str:
    """A package's version as `uv.lock` names it; empty when it names none."""
    for p in tomllib.loads(lock.read_text(encoding="utf-8")).get("package", []):
        if p.get("name") == name:
            return str(p.get("version", ""))
    return ""


class _Collector:
    """Each collected item's node id and `goal` marker, read as the plugin reads it, and the CI
    needs each goal check's own body names (spec 085, Decision 1)."""

    def __init__(self) -> None:
        self.items: list[tuple[str, str | None]] = []
        self.may_block: dict[str, frozenset[str]] = {}

    def pytest_collection_finish(self, session) -> None:
        from harness import plugin

        self.items = [(item.nodeid, plugin.area_of(item)) for item in session.items]
        for item in session.items:
            if plugin.area_of(item) is None:
                continue
            got = needs_called(getattr(item, "function", None)) & set(CI_NEEDS)
            if got:
                self.may_block[item.nodeid] = frozenset(got)


def collect(
    repo: Path = paths.REPO,
) -> tuple[list[str], list[str], dict[str, frozenset[str]]]:
    """The judge's collection at this commit: (goal checks, unit tests, the CI needs each goal
    check's body names). No artifacts needed."""
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
    return goal, [n for n, area in c.items if area is None], c.may_block


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
    goal, units, may_block = collect()
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
            set_sums_sha256=os.environ.get("SET_SUMS_SHA256", ""),
            wasmtime=locked_version("wasmtime"),
            may_block=may_block,
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
