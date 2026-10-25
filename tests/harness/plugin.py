"""The pytest plugin that turns the test run into the progress scoreboard.

Loaded by tests/conftest.py. All state lives on `config.stash`, so the plugin's own end-to-end
self-tests (pytester, in-process) never mix their records with the outer run's.

On several cores (`-n N`, pytest-xdist) the workers collect and run, and make each
record exactly as a serial run does; the record rides to the controller on its report, and each
worker's collection in its `workeroutput`. Workers write nothing and guard nothing: the controller
alone runs the acceptance's guards, writes the run record and accepts.

`--accept-from <record.json> --claims <folder>` runs no check: it records a green CI run's merged
record as the accepted state, with the news files' reasons (harness/accept_from.py). The local
`--accept` stays, for a machine that must accept without CI.
"""

from __future__ import annotations

import builtins
import importlib.metadata
import json
import os
import platform
import socket
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pytest

from harness import history, litter, needs, news, paths, scoreboard


@dataclass
class Gap:
    check: str
    raises: str
    match: str
    reason: str
    closes_with: str


@dataclass
class State:
    gaps: dict[str, Gap] = field(default_factory=dict)
    gap_errors: list[str] = field(default_factory=list)
    areas: dict[str, str] = field(default_factory=dict)  # node id -> area of collected checks
    records: dict[str, dict] = field(default_factory=dict)
    deselected: list[str] = field(default_factory=list)
    collected_files: set[str] = field(default_factory=set)
    narrowed_files: set[str] = field(default_factory=set)  # files given as node ids, not whole
    suite_total: int = 0
    suite_passed: int = 0
    suite_skipped: int = 0
    lines: list[str] = field(default_factory=list)
    facts: dict[str, dict] = field(default_factory=dict)  # node id -> the check's `fact` values
    crashed: dict[str, str] = field(default_factory=dict)  # failed reports carrying no record
    collections: int = 0  # workers that handed their collection over
    worker_foreign: list[str] = field(default_factory=list)  # what steered a worker
    shard_items: int | None = None  # under --shard: the items it selected
    shard_units: list[str] = field(default_factory=list)  # under --shard: its unit tests


STATE = pytest.StashKey[State]()
HEAD_AT_START = pytest.StashKey[str]()
METRICS = pytest.StashKey[dict]()
NOTE = pytest.StashKey[str]()
FACTS = pytest.StashKey[dict]()
METRIC_NAMES = ("fuel", "bytes", "passes")  # passes: an upstream suite's count
WORKERS = pytest.StashKey[int]()
RECORD_PROPERTY = "wasi_python.record"  # a goal check's record, on a worker's report
SUITE_PROPERTY = "wasi_python.suite"  # a unit test's tally, on a worker's report
AREA_PROPERTY = "wasi_python.area"  # a goal check's area, on its setup report
WORKER_OUTPUT = "wasi_python.collection"  # a worker's collection, in its workeroutput
COLLECTION_KEYS = ("areas", "deselected", "collected_files", "narrowed_files")


def is_worker(config) -> bool:
    """An xdist worker. Never `PYTEST_XDIST_WORKER`: a pytest that a check
    starts inherits it."""
    return hasattr(config, "workerinput")


def distributing(config) -> bool:
    """Whether this process is an xdist controller dealing tests to workers (Decision 7)."""
    option = getattr(config, "option", None)
    return (
        not is_worker(config)
        and getattr(option, "dist", "no") != "no"
        and bool(getattr(option, "tx", None))
        and not getattr(option, "collectonly", False)
    )


def pytest_addoption(parser: pytest.Parser) -> None:
    g = parser.getgroup("progress", "the progress harness")
    g.addoption("--accept", metavar="REASON", help="record this run as the accepted state")
    g.addoption("--accept-judge", metavar="REASON", help="also accept a changed judge")
    g.addoption("--accept-growth", metavar="REASON", help="also accept fuel or bytes growth")
    g.addoption(
        "--accept-fewer-passes", metavar="REASON", help="also accept a fall in a pass count"
    )
    g.addoption("--partial", metavar="REASON", help="allow accepted passes to be blocked")
    g.addoption("--retire", metavar="NODEID", action="append", default=[], help="drop a check")
    g.addoption(
        "--progress-dir", metavar="DIR", help="where accepted.json and the history volumes live"
    )
    g.addoption("--progress-latest", metavar="FILE", help="where the run record is written")
    g.addoption("--known-gaps", metavar="FILE", help="the known gaps file")
    g.addoption(
        "--accept-tier-move", metavar="REASON", help="also accept checks that moved between tiers"
    )
    g.addoption(
        "--tier",
        choices=scoreboard.TIERS,
        help="normal (the default) leaves the release-tier checks unrun; release runs both tiers",
    )
    g.addoption(
        "--accept-from",
        metavar="RECORD",
        help="record a green CI run's merged record as the accepted state; runs no check",
    )
    g.addoption(
        "--claims",
        metavar="FOLDER",
        help="with --accept-from: the news files whose claims give every reason",
    )
    g.addoption("--shard", metavar="NAME", help="run one shard of the release's plan")
    g.addoption("--shard-plan", metavar="FILE", help="the shard plan (tests/release_shards.toml)")


def _opt(config: pytest.Config, name: str):
    return config.getoption(name)


def progress_dir(config: pytest.Config) -> Path:
    d = _opt(config, "--progress-dir")
    return Path(d) if d else paths.PROGRESS


def latest_path(config: pytest.Config) -> Path:
    f = _opt(config, "--progress-latest")
    return Path(f) if f else paths.LATEST


def load_gaps(path: Path) -> tuple[dict[str, Gap], list[str]]:
    if not path.is_file():
        return {}, []
    gaps, errors = {}, []
    for i, raw in enumerate(tomllib.loads(path.read_text()).get("gap", []), 1):
        try:
            gap = Gap(
                check=raw["check"],
                raises=raw.get("raises", "AssertionError"),
                match=raw["match"],
                reason=raw["reason"],
                closes_with=raw["closes_with"],
            )
        except KeyError as e:
            errors.append(f"gap {i}: missing field {e}")
            continue
        if gap.check in gaps:
            errors.append(f"gap {i}: {gap.check} is listed twice")
        if not isinstance(getattr(builtins, gap.raises, None), type):
            errors.append(f"gap {i}: raises names {gap.raises}, not a builtin exception")
        gaps[gap.check] = gap
    return gaps, errors


WORKTREE_REFUSAL = "accept: a local acceptance is made in the main tree; this is a linked worktree"


def _same_folder(a: Path, b: Path) -> bool:
    """`os.path.samefile` when both exist, so case and links cannot slip past; otherwise the
    resolved paths."""
    if a.exists() and b.exists():
        return os.path.samefile(a, b)
    return a.resolve() == b.resolve()


def writes_accepted_state(progress: Path, repo: Path | None = None) -> bool:
    """Whether `progress` is the progress folder of any worktree of this repository, the
    main tree's included. Any other folder (the self-tests' own) holds no accepted state."""
    return any(_same_folder(progress, w / "context" / "progress") for w in paths.worktrees(repo))


def accept_refusal(reason: str | None, progress: Path, repo: Path | None = None) -> str | None:
    """Why `--accept` is refused before collection, or None. Only
    `--accept` writes; --accept-judge, --accept-growth and --partial write nothing without it.
    Where git is absent no folder is the repository's, and `--accept` proceeds."""
    if not reason or not writes_accepted_state(progress, repo):
        return None
    if paths.linked_worktree(repo):
        return WORKTREE_REFUSAL
    changed = paths.dirty_path(repo)
    if changed is not None:
        return f"accept: refused on a dirty tree: {changed} has a change the judge could see"
    return None


def head_moved(config: pytest.Config) -> str | None:
    """Why the acceptance would name a commit the judge did not see whole, or None."""
    start = config.stash.get(HEAD_AT_START, None)
    now = (paths.git("rev-parse", "HEAD") or "").strip()
    if start is None or now == start:
        return None
    return f"accept: HEAD moved during the run ({start[:12]} to {now[:12]})"


def pytest_configure(config: pytest.Config) -> None:
    reason, progress = _opt(config, "--accept"), progress_dir(config)
    if not is_worker(config):  # the lane's guards run once, in the controller
        refusal = accept_refusal(reason, progress, paths.REPO)
        if refusal:
            pytest.exit(refusal, returncode=1)  # before collection; nothing is written
        if reason and writes_accepted_state(progress, paths.REPO):  # checked again when written
            config.stash[HEAD_AT_START] = (paths.git("rev-parse", "HEAD") or "").strip()
    config.addinivalue_line("markers", "goal(area): a v1 progress check")
    config.addinivalue_line("markers", "slow: a guest job or the oracle")
    gaps_file = _opt(config, "--known-gaps")
    gaps, errors = load_gaps(Path(gaps_file) if gaps_file else paths.KNOWN_GAPS)
    config.stash[STATE] = State(gaps=gaps, gap_errors=errors)
    if not is_worker(config):
        refusal = shard_refusal(config)
        if refusal:
            pytest.exit(refusal, returncode=4)  # before collection
    config.stash[WORKERS] = len(config.option.tx) if distributing(config) else 0
    for scratch in litter.scratch_roots() if not is_worker(config) else []:
        if left := litter.sealed_leftovers(scratch):
            sys.stderr.write(  # what a killed judge left sealed, and the recovery
                f"host litter: {len(left)} sealed folder(s) under {scratch} (first:"
                f" {left[0]}): a judge running in this checkout now, or one killed earlier; this"
                f" run never reads them; once no judge runs here, `chmod -R u+w {scratch}` then"
                " `rm -rf` clears them\n"
            )
    if distributing(config):
        config.pluginmanager.register(Controller(config), "wasi_python.controller")


def area_of(item: pytest.Item) -> str | None:
    m = item.get_closest_marker("goal")
    return m.args[0] if m and m.args else None


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    state = config.stash[STATE]
    root = Path(str(config.rootpath)).resolve()
    for arg in config.args:
        if "::" in arg:  # a run narrowed to node ids does not judge the rest of their files
            path = Path(arg.split("::", 1)[0])
            path = (Path(str(config.invocation_params.dir)) / path).resolve()
            try:
                state.narrowed_files.add(path.relative_to(root).as_posix())
            except ValueError:
                pass
    for item in items:
        state.collected_files.add(item.nodeid.split("::", 1)[0])
        area = area_of(item)
        if area is None:
            continue
        state.areas[item.nodeid] = area
        gap = state.gaps.get(item.nodeid)
        if gap is not None:
            item.add_marker(
                pytest.mark.xfail(
                    strict=True,
                    raises=getattr(builtins, gap.raises, AssertionError),
                    reason=f"gap: {gap.reason}",
                )
            )

    if not _opt(config, "--shard") and run_tier(config) == "normal":
        # The normal tier never runs a release-tier check, not even by node id: its rows keep
        # what the release acceptance accepted.
        release = set(release_checks())
        out = [i for i in items if i.nodeid in release]
        if out:
            config.hook.pytest_deselected(items=out)
            items[:] = [i for i in items if i.nodeid not in release]
    shard = _opt(config, "--shard")
    if shard:  # after every area is recorded, so a check outside the shard is `deselected`
        from harness import shards

        plan = shards.load(shard_plan(config))
        mine = set(shards.select([i.nodeid for i in items], plan, shards.group_of())[shard])
        kept = [i for i in items if i.nodeid in mine]
        out = [i for i in items if i.nodeid not in mine]
        if out:
            config.hook.pytest_deselected(items=out)
            items[:] = kept
        state.shard_items = len(kept)
        state.shard_units = [i.nodeid for i in kept if area_of(i) is None]


def shard_plan(config: pytest.Config) -> Path:
    from harness import shards

    f = _opt(config, "--shard-plan")
    return Path(f) if f else shards.PLAN


def shard_refusal(config: pytest.Config) -> str | None:
    """Why `--shard` is refused before anything runs: a shard is one serial, unaccepted,
    whole-plan selection of a name the plan holds."""
    name = _opt(config, "--shard")
    if not name:
        return None
    from harness import shards

    try:
        plan = shards.load(shard_plan(config))
    except (OSError, KeyError, TypeError, ValueError) as e:
        return f"refused: --shard {name}: the plan does not load ({e})"
    if name not in plan:
        return f"refused: --shard {name}: the plan holds no such shard"
    if getattr(config.option, "numprocesses", None):
        return (
            f"refused: --shard {name} with -n: a shard runs serially: the shards are the "
            "parallelism"
        )
    if _opt(config, "--accept") or _opt(config, "--retire"):
        return f"refused: --shard {name} with --accept or --retire: a shard never accepts"
    if any("::" in arg for arg in config.args):
        return f"refused: --shard {name} with a node id: a shard selects from the whole judge"
    if _opt(config, "--tier"):
        return f"refused: --shard {name} with --tier: a shard's tier is its shard's"
    return None


def release_checks() -> list[str]:
    """Every release-tier check, by the upstream files of this tree."""
    from harness import upstream

    return sorted(upstream.release_checks(upstream.load_all()))


def run_tier(config: pytest.Config) -> str:
    shard = _opt(config, "--shard")
    if shard:
        from harness import shards

        return shards.tier_of(shards.load(shard_plan(config)), shard)
    return _opt(config, "--tier") or "normal"


def pytest_deselected(items: list[pytest.Item]) -> None:
    for item in items:
        item.config.stash[STATE].collected_files.add(item.nodeid.split("::", 1)[0])
        if area_of(item) is not None:
            item.config.stash[STATE].deselected.append(item.nodeid)


@pytest.fixture
def metric(request: pytest.FixtureRequest):
    """Record a counted metric (`fuel`, `bytes` or `passes`) for the current check."""

    def record(name: str, value: int) -> None:
        if name not in METRIC_NAMES:
            raise ValueError(f"unknown metric {name}")
        request.node.stash.setdefault(METRICS, {})[name] = int(value)

    return record


@pytest.fixture
def note(request: pytest.FixtureRequest):
    """Record one line a passing check says of itself, kept as its reason in latest.json (the
    callback scan's coverage, say). It is never compared, so it is no metric."""

    def record(text: str) -> None:
        request.node.stash[NOTE] = _first_line(text)

    return record


@pytest.fixture
def fact(request: pytest.FixtureRequest):
    """Attach a named fact to the current check's record in latest.json, under `facts`:
    reported, never ratcheted (a group's `passed_digest`, its outcome counts, the files
    left out of its staging)."""

    def record(name: str, value) -> None:
        request.node.stash.setdefault(FACTS, {})[name] = value

    return record


def _first_line(text: str) -> str:
    for line in text.strip().splitlines():
        if line.strip():
            return line.strip()[:240]
    return ""


def _skip_reason(rep: pytest.TestReport) -> str:
    lr = rep.longrepr
    if isinstance(lr, tuple) and len(lr) == 3:
        return str(lr[2])
    return str(lr)


def _set(state: State, node: str, area: str, status: str, reason: str = "", **extra) -> None:
    current = state.records.get(node)
    if current is not None and current["status"] == "fail":
        return  # a failure in any phase stands
    facts = state.facts.get(node)
    state.records[node] = {
        "area": area,
        "status": status,
        "reason": reason,
        **extra,
        **({"facts": facts} if facts else {}),
    }


def _facts(state: State, node: str, facts: dict) -> None:
    state.facts[node] = dict(facts)
    if node in state.records:
        state.records[node]["facts"] = dict(facts)


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    rep = yield
    _judge(item, call, rep)
    if is_worker(item.config):
        _carry(item, rep)
    return rep


def _carry(item: pytest.Item, rep: pytest.TestReport) -> None:
    """On a worker, the node's current record (or a unit test's tally) rides on its report to the
    controller, which keeps the last one per node."""
    state = item.config.stash[STATE]
    area = area_of(item)
    if area is None:
        if rep.when == "call" or (rep.when == "setup" and not rep.passed):
            rep.user_properties.append((SUITE_PROPERTY, [bool(rep.passed), bool(rep.skipped)]))
        return
    if rep.when == "setup":  # known to the controller even if no worker finishes cleanly
        rep.user_properties.append((AREA_PROPERTY, [item.nodeid, area]))
    if item.nodeid in state.records:
        record = json.loads(json.dumps(state.records[item.nodeid]))  # plain values, a snapshot
        rep.user_properties.append((RECORD_PROPERTY, [item.nodeid, record]))


class Controller:
    """The xdist controller's half. Workers collect and run;
    this takes each goal check's record and each unit tally from the reports, and each worker's
    collection when it goes down. Registered only while xdist distributes."""

    def __init__(self, config: pytest.Config) -> None:
        self.config = config

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        state = self.config.stash[STATE]
        carried = False
        for name, value in report.user_properties:
            if name == RECORD_PROPERTY:
                node, record = value
                if node in state.crashed:  # a crash outranks a later run of the same check
                    carried = True
                    continue
                state.records[node] = record
                if record.get("facts"):
                    state.facts[node] = record["facts"]
                carried = True
            elif name == AREA_PROPERTY:
                node, area = value
                state.areas[node] = area
            elif name == SUITE_PROPERTY:
                passed, skipped = value
                state.suite_total += 1
                state.suite_passed += passed
                state.suite_skipped += skipped
                carried = True
        if report.failed and not carried:  # xdist's report for a check whose worker died
            state.crashed.setdefault(report.nodeid, _first_line(str(report.longrepr)))

    def pytest_testnodedown(self, node, error) -> None:
        out = getattr(node, "workeroutput", {}).get(WORKER_OUTPUT)
        if not out:
            return  # a worker that died sends nothing; the others collected the same checks
        state = self.config.stash[STATE]
        state.collections += 1
        state.areas.update(out["areas"])
        state.deselected += [n for n in out["deselected"] if n not in state.deselected]
        state.collected_files.update(out["collected_files"])
        state.narrowed_files.update(out["narrowed_files"])
        state.worker_foreign += [f for f in out.get("foreign", []) if f not in state.worker_foreign]


def _judge(item: pytest.Item, call: pytest.CallInfo, rep: pytest.TestReport):
    state = item.config.stash[STATE]
    area = area_of(item)
    if area is not None and rep.when == "call" and FACTS in item.stash:
        _facts(state, item.nodeid, item.stash[FACTS])
    if area is None:
        if rep.when == "call" or (rep.when == "setup" and not rep.passed):
            state.suite_total += 1
            state.suite_passed += rep.passed
            state.suite_skipped += rep.skipped
        return rep
    node = item.nodeid
    gap = state.gaps.get(node)
    if rep.skipped and not hasattr(rep, "wasxfail"):
        reason = _skip_reason(rep)
        need = needs.parse_reason(reason)
        known = needs.VOCABULARY.get(need) if need else None
        if known is None or known.met():
            why = (
                f"skipped, and the need {need!r} is met"
                if known
                else f"skipped without a known need: {reason}"
            )
            rep.outcome = "failed"
            rep.longrepr = why
            _set(state, node, area, "fail", why)
        else:
            _set(state, node, area, "blocked", f"needs {need}", need=need)
        return rep
    if hasattr(rep, "wasxfail") and rep.skipped:  # failed as a gap: in the named way?
        message = call.excinfo.exconly() if call.excinfo else ""
        if gap is not None and gap.match not in message:
            why = f"fails differently from its gap (expected {gap.match!r}): {_first_line(message)}"
            del rep.wasxfail  # pytest counts a report as failed only without it
            rep.outcome = "failed"
            rep.longrepr = why
            _set(state, node, area, "fail", why)
        elif gap is None:  # an xfail marker or pytest.xfail() is not an allowance
            why = f"xfailed without an entry in tests/known_gaps.toml: {rep.wasxfail}"
            del rep.wasxfail
            rep.outcome = "failed"
            rep.longrepr = why
            _set(state, node, area, "fail", why)
        else:
            _set(state, node, area, "gap", _first_line(message), closer=gap.closes_with)
        return rep
    if rep.failed and "XPASS" in str(rep.longrepr):
        why = (
            "passes, but tests/known_gaps.toml still lists it: remove the gap"
            if gap is not None
            else "passes under an xfail marker that no gap entry names"
        )
        rep.longrepr = why
        _set(state, node, area, "fail", why)
        return rep
    if rep.failed:
        message = call.excinfo.exconly() if call.excinfo else str(rep.longrepr)
        _set(state, node, area, "fail", _first_line(message))
    elif rep.when == "call" and rep.passed:
        metrics = item.stash.get(METRICS, {})
        _set(state, node, area, "pass", item.stash.get(NOTE, ""), metrics=dict(metrics))
    return rep


# ---------------------------------------------------------------------------------------------
# Several cores: one way to run in parallel, and the judge's scheduler

REFUSAL = "refused: {} ({})"


def xdist_refusal(option) -> str | None:
    """Why these raw options are refused, or None: every xdist 3.8.0 option is decided (the
    table of Decision 7). The ini keys `rsyncdirs`, `rsyncignore` and `looponfailroots` can come
    only from pyproject.toml, which is judged, and do nothing without the refused options."""
    get = lambda name, default=None: getattr(option, name, default)  # noqa: E731
    n = get("numprocesses")
    rows = [
        (n == "logical", "-n logical", "it needs psutil, which is not pinned"),
        (get("dist", "no") not in ("no", "load"), f"--dist {get('dist')}", "only -n deals"),
        (get("distload", False), "-d/--distload", "use -n"),
        (get("dist", "no") == "load" and not n and not get("distload", False),
         "--dist load without -n", "nothing to distribute"),
        (get("loadscopereorder", True) is False, "--no-loadscope-reorder",
         "the size order starts the longest group first"),
        (get("maxschedchunk") is not None, "--maxschedchunk", "the judge's scheduler ignores it"),
        (bool(get("tx")), "--tx", "other interpreters are not the judged environment"),
        (bool(get("px")), "--px", "other interpreters are not the judged environment"),
        (bool(get("rsyncdir")), "--rsyncdir", "remote hosts are not the judged environment"),
        (bool(get("rsyncignore")), "--rsyncignore", "remote hosts are not the judged environment"),
        (get("looponfail", False), "-f/--looponfail",
         "its child would judge and accept again on every change"),
        (get("maxworkerrestart") not in (None, "0"),
         f"--max-worker-restart {get('maxworkerrestart')}",
         "a dead worker's check is never run again: it fails"),
    ]  # fmt: skip
    for refused, name, why in rows:
        if refused:
            return REFUSAL.format(name, why)
    return None


RAW_REFUSAL = pytest.StashKey["str | None"]()


@pytest.hookimpl(wrapper=True, specname="pytest_cmdline_main")
def pytest_cmdline_main_raw_options(config: pytest.Config):
    """Read the options as given, before any implementation of the hook runs: xdist's own
    (tryfirst, in whatever order it was registered) turns -n into --tx entries and `auto` into
    a number. A worker carries the options it was given, and is skipped."""
    if not is_worker(config):
        config.stash[RAW_REFUSAL] = xdist_refusal(config.option)
        if hasattr(config.option, "maxworkerrestart") and config.option.maxworkerrestart is None:
            # No replacement worker: xdist would deal a dead worker's check again, and could hang.
            # Set before xdist's DSession reads it in its configure.
            config.option.maxworkerrestart = "0"
    return (yield)


@pytest.hookimpl(tryfirst=True)
def pytest_cmdline_main(config: pytest.Config):
    """Refuse before anything runs: before looponfail's loop (under -f the controller's
    pytest_configure never runs) and before any session (Decision 7). `--accept-from` is answered
    here too, before any session: it runs no check."""
    why = config.stash.get(RAW_REFUSAL, None)
    if why:
        print(why, file=sys.stderr)
        return 1
    if not is_worker(config) and config.getoption("--accept-from", None):
        from harness import accept_from

        return accept_from.main(config)
    return None


UPSTREAM_FILE = "tests/checks/test_v1_3_upstream_suites.py"


def upstream_scopes(configs: dict | None = None) -> dict[str, str]:
    """The exact map of node ids that share a unit of work: an upstream group's check and each of
    its classes' checks (Decision 6). No prefix is guessed."""
    from harness import upstream

    configs = upstream.load_all() if configs is None else configs
    scopes: dict[str, str] = {}
    for c in configs.values():
        for g in c.groups:
            scopes[f"{UPSTREAM_FILE}::test_upstream_suite[{g}]"] = f"upstream {g}"
        for k in c.expected:
            scopes[f"{UPSTREAM_FILE}::test_upstream_class[{k.group}-{k.id}]"] = (
                f"upstream {k.group}"
            )
        # CPython's named entries read their group's run, as a class does
        for kind, entries in (
            ("deselected", c.deselected),
            ("environment", c.environment),
            ("host", c.host_dependent),
        ):
            for e in entries:
                scopes[f"{UPSTREAM_FILE}::test_upstream_{kind}[{e.group}-{e.id}]"] = (
                    f"upstream {e.group}"
                )
    return scopes


def scope_of(nodeid: str, scopes: dict[str, str]) -> str:
    return scopes.get(nodeid, nodeid)


@pytest.hookimpl(optionalhook=True)
def pytest_xdist_make_scheduler(config, log):
    """The judge's scheduler: xdist's LoadScope dealing with `scope_of`, which keeps node ids as
    they are (`--dist loadgroup` appends `@group` to them). xdist's own hook is trylast."""
    from xdist.scheduler import LoadScopeScheduling

    scopes = upstream_scopes()

    class JudgeScheduling(LoadScopeScheduling):
        def _split_scope(self, nodeid: str) -> str:
            return scope_of(nodeid, scopes)

    return JudgeScheduling(config, log)


def scheduler_name(config: pytest.Config) -> str | None:
    """The class of the scheduler xdist used, or None for a serial run (Decision 8)."""
    dsession = config.pluginmanager.getplugin("dsession")
    sched = getattr(dsession, "sched", None)
    return type(sched).__name__ if sched is not None else None


def locked_versions(lock: Path | None = None) -> dict[str, str | None]:
    """The versions uv.lock pins for pytest-xdist and execnet."""
    try:
        packages = tomllib.loads((lock or paths.REPO / "uv.lock").read_text()).get("package", [])
    except (OSError, tomllib.TOMLDecodeError):
        return {"pytest-xdist": None, "execnet": None}
    pins = {p.get("name"): p.get("version") for p in packages}
    return {"pytest-xdist": pins.get("pytest-xdist"), "execnet": pins.get("execnet")}


def xdist_versions() -> dict[str, str | None]:
    """The installed versions: the pytest-xdist distribution, `xdist.__version__`, execnet."""
    found: dict[str, str | None] = {}
    for key, dist in (("pytest-xdist", "pytest-xdist"), ("execnet", "execnet")):
        try:
            found[key] = importlib.metadata.version(dist)
        except importlib.metadata.PackageNotFoundError:
            found[key] = None
    try:
        import xdist

        found["xdist"] = getattr(xdist, "__version__", None)
    except ImportError:
        found["xdist"] = None
    return found


def xdist_folder() -> Path | None:
    """xdist's package folder, when every installed version is the one uv.lock pins (Decision 5:
    `locate_file("xdist")`, never `locate_file("")`, which is all of site-packages)."""
    have, pins = xdist_versions(), locked_versions()
    if not (
        pins["pytest-xdist"] is not None
        and have["pytest-xdist"] == have["xdist"] == pins["pytest-xdist"]
        and have["execnet"] == pins["execnet"]
    ):
        return None
    try:
        dist = importlib.metadata.distribution("pytest-xdist")
    except importlib.metadata.PackageNotFoundError:
        return None
    return Path(str(dist.locate_file("xdist"))).resolve()


# ---------------------------------------------------------------------------------------------
# The end of the run: the record, the ratchet, acceptance


def _git(*args: str) -> str:
    try:
        r = subprocess.run(
            ["git", "-C", str(paths.REPO), *args], capture_output=True, text=True, check=False
        )
    except OSError:
        return ""
    return r.stdout.strip() if r.returncode == 0 else ""


def run_meta() -> dict:
    """Facts about this run; a function so self-tests can replace it."""
    try:
        import importlib.metadata as md

        wasmtime_version = md.version("wasmtime")
    except Exception:
        wasmtime_version = None
    d = paths.artifact_dir()
    wasm = d / "python.wasm" if d else None
    sums = d / "SHA256SUMS" if d else None
    files = paths.judge_files()
    return {
        "at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commit": _git("rev-parse", "HEAD"),
        "dirty": paths.dirty_path() is not None,  # a change the judge could see
        "platform": f"{sys.platform}-{platform.machine().lower()}",
        "host": paths.sha256_bytes(socket.gethostname().encode())[:12],
        "wasmtime": wasmtime_version,
        "artifact": paths.sha256_file(wasm) if wasm and wasm.is_file() else None,
        # The whole set, by its own SHA256SUMS; the set check holds every
        # file to it.
        "set_sums": paths.sha256_file(sums) if sums and sums.is_file() else None,
        "judge": {"hash": paths.judge_hash(files), "files": files},
        "notes": [paths.WORKTREE_NOTE.format(w) for w in paths.worktrees_inside()],
    }


def _module_file(plugin: object) -> Path | None:
    f = getattr(plugin, "__file__", None)
    return Path(f).resolve() if f else None


def foreign_steering(config: pytest.Config) -> list[str]:
    """What, in a run of this repository, steers pytest from outside the judge: a config file
    other than pyproject.toml, or a plugin that is neither pytest's own nor a judged file."""
    found = []
    pyproject = (paths.REPO / "pyproject.toml").resolve()
    inipath = Path(str(config.inipath)).resolve() if config.inipath else None
    if inipath != pyproject:
        found.append(f"pytest is configured from {inipath or 'no file'}, not pyproject.toml")
    pytest_dir = Path(pytest.__file__).resolve().parents[1] / "_pytest"
    judged = {(paths.REPO / f).resolve() for f in paths.judge_files()}
    xdist_dir = xdist_folder()  # None unless every version is uv.lock's

    def allowed(f: Path) -> bool:
        return f in judged or (xdist_dir is not None and f.is_relative_to(xdist_dir))

    for name, plugin in config.pluginmanager.list_name_plugin():
        f = _module_file(plugin)
        if f is None:
            module = type(plugin).__module__
            if module.startswith("_pytest") or module == "builtins":
                continue
            if module == "__channelexec__" and is_worker(config) and xdist_dir is not None:
                # xdist's worker loop: xdist/remote.py, sent to the worker and run by execnet
                # under this name, so its class has no file.
                code = getattr(getattr(type(plugin), "__init__", None), "__code__", None)
                made_in = Path(code.co_filename).resolve() if code is not None else None
                # The class's code must come from xdist's own remote.py (execnet compiles it under
                # its real file name), never from a class that only takes the name.
                if (
                    type(plugin).__qualname__ == "WorkerInteractor"
                    and made_in is not None
                    and made_in.is_relative_to(xdist_dir)
                ):
                    continue
            defined = _module_file(sys.modules.get(module))  # an object: its type's module file
            if defined is None or not allowed(defined):
                found.append(f"plugin {name} ({module})")
        elif not (f.is_relative_to(pytest_dir) or allowed(f)):
            found.append(f"plugin {name} from {f}")
    return found


def _this_repo(config: pytest.Config) -> bool:
    return Path(str(config.rootpath)).resolve() == paths.REPO.resolve()


def _read(path: Path) -> str | None:
    return path.read_text() if path.is_file() else None


def retired_by_news(ratchet: scoreboard.Ratchet, root: Path) -> dict[str, str]:
    """The absent checks a news file at this commit retires, each with its claim's reason: so a
    change that removes a check, with its claim, keeps its own run and the run after its merge
    green until the accept job consumes the claim. A broken news file retires nothing (the rules
    check that holds their shape reports it)."""
    try:
        claims = [c for n in news.folder(root / news.CHANGES) for c in n.claims]
    except news.NewsError:
        return {}
    found = {n: news.reason(claims, "retired", n) for n in ratchet.absent}
    return {n: why for n, why in found.items() if why}


@pytest.hookimpl(tryfirst=True)
def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    config = session.config
    state = config.stash.get(STATE, None)
    if state is None or config.getoption("collectonly"):
        return
    if is_worker(config):  # hand the collection over; write nothing, accept nothing
        config.workeroutput[WORKER_OUTPUT] = {
            "areas": dict(state.areas),
            "deselected": list(state.deselected),
            "collected_files": sorted(state.collected_files),
            "narrowed_files": sorted(state.narrowed_files),
            # A conftest loaded only during collection, and what it registers, is seen only by
            # the workers: each judges what steers it.
            "foreign": foreign_steering(config) if _this_repo(config) else [],
        }
        return
    for node, why in state.crashed.items():  # a crash outranks any record
        if node in state.areas:
            state.records[node] = {
                "area": state.areas[node],
                "status": "fail",
                "reason": f"worker crashed: {why}",
            }
    if not state.areas and (_opt(config, "--accept") or _opt(config, "--retire")):
        state.lines = ["RED: --accept refused: this run collected no goal checks"]
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
        return
    tier = run_tier(config)
    release = release_checks()
    leave = set(release) if tier == "normal" and not _opt(config, "--shard") else set()
    for node, area in state.areas.items():
        if node in state.deselected:
            why = "release tier" if node in leave else ""
            state.records[node] = {"area": area, "status": "deselected", "reason": why}
        elif node not in state.records:  # collected, never ran (-x, --maxfail, an interrupt)
            state.records[node] = {"area": area, "status": "unrun", "reason": "did not run"}
    for rec in state.records.values():
        rec.setdefault("need", None)
        rec.setdefault("metrics", {})
    meta = run_meta()
    meta["workers"] = config.stash.get(WORKERS, 0)
    meta["scheduler"] = scheduler_name(config)
    partial = _opt(config, "--partial")
    meta["partial"] = partial
    meta["overrides"] = [
        f"{o} {_opt(config, o)}"
        for o in ("--progress-dir", "--known-gaps", "--progress-latest", "--shard-plan")
        if _opt(config, o)
    ]
    meta["tier"] = tier
    shard = _opt(config, "--shard")
    meta["shard"] = shard or None
    if shard:  # what a gather compares with the plan's share
        from harness import shards

        meta["units"] = {
            "count": len(state.shard_units),
            "digest": shards.units_digest(state.shard_units),
        }
    addopts = os.environ.get("PYTEST_ADDOPTS", "").strip()
    if addopts:
        meta["overrides"].append(f"PYTEST_ADDOPTS {addopts}")
    this_repo = _this_repo(config)
    foreign = foreign_steering(config) if this_repo else []
    foreign += [f for f in state.worker_foreign if f not in foreign]
    meta["foreign"] = foreign
    run = {
        "meta": meta,
        "checks": dict(sorted(state.records.items())),
        "deselected": sorted(state.deselected),
        "release_checks": release,
        "collected_files": sorted(state.collected_files - state.narrowed_files),
        "suite": {
            "passed": state.suite_passed,
            "skipped": state.suite_skipped,
            "total": state.suite_total,
        },
    }
    pdir = progress_dir(config)
    accepted_text = _read(pdir / "accepted.json")
    accepted = json.loads(accepted_text) if accepted_text else None
    root = Path(str(config.rootpath))
    ratchet = scoreboard.compare(run, accepted, root)
    ratchet.retired = retired_by_news(ratchet, root)
    red = ratchet.red(partial=bool(partial)) if accepted else []
    if config.stash.get(WORKERS, 0) and not state.collections:
        red.append("no worker handed its collection over: the record is incomplete")
    unknown = sorted(n for n in state.crashed if n not in state.areas)
    if unknown:
        red.append("a worker crashed while running " + ", ".join(unknown[:3]))
    if foreign:
        red.append("steered from outside the judge: " + "; ".join(foreign[:3]))
    if state.gap_errors:
        red.append("tests/known_gaps.toml: " + "; ".join(state.gap_errors))
    if shard and not state.shard_items:
        red.append(f"shard {shard} selected nothing")
        session.exitstatus = pytest.ExitCode.TESTS_FAILED

    latest = latest_path(config)
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(scoreboard.dumps(run))

    # accept() judges the ratchet itself (it honours --retire, --partial, --accept-growth);
    # it needs only pytest's verdict and a sound gaps file.
    green = exitstatus == 0 and not state.gap_errors and not foreign and not addopts
    reason = _opt(config, "--accept")
    accept_line = None
    # The tree and HEAD as the acceptance is written, not only as the run began:
    # an edit or a commit made meanwhile refuses it.
    late = (accept_refusal(reason, pdir, paths.REPO) or head_moved(config)) if reason else None
    if late:
        red.append(f"--accept refused: {late}")
    elif reason:
        try:
            new, line = scoreboard.accept(
                run,
                accepted,
                history.lines(pdir),
                ratchet,
                green=green,
                reason=reason,
                judge_reason=_opt(config, "--accept-judge"),
                growth_reason=_opt(config, "--accept-growth"),
                partial_reason=partial,
                retire=_opt(config, "--retire"),
                fewer_reason=_opt(config, "--accept-fewer-passes"),
                tier_move_reason=_opt(config, "--accept-tier-move"),
            )
        except scoreboard.AcceptRefused as e:
            red.append(f"--accept refused: {e}")
        else:
            pdir.mkdir(parents=True, exist_ok=True)
            (pdir / "accepted.json").write_text(scoreboard.dumps(new))
            where = history.target(pdir, line)  # the newest volume, or a new one
            with where.open("a", encoding="utf-8", newline="\n") as f:
                f.write(line + "\n")
            accept_line = f"accepted: {where} line {json.loads(line)['n']}"
            ratchet = scoreboard.compare(run, new, root)  # re-judged against what was accepted
            ratchet.retired = retired_by_news(ratchet, root)
            red = [r for r in red if r.startswith("tests/known_gaps.toml")]
            red += ratchet.red(partial=bool(partial))
    elif _opt(config, "--retire"):
        red.append("--retire needs --accept")

    providers = {name: n.provided_by for name, n in needs.VOCABULARY.items()}
    state.lines = scoreboard.render(run, ratchet, providers, red)
    if accept_line:
        state.lines.append(accept_line)
    if red and session.exitstatus == 0:
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


def pytest_terminal_summary(terminalreporter, exitstatus: int, config: pytest.Config) -> None:
    state = config.stash.get(STATE, None)
    if not state or not state.lines:
        return
    terminalreporter.section("progress", sep="=")
    for line in state.lines:
        terminalreporter.write_line(line)
