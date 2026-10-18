"""The pytest plugin that turns the test run into the progress scoreboard (spec 002).

Loaded by tests/conftest.py. All state lives on `config.stash`, so the plugin's own end-to-end
self-tests (pytester, in-process) never mix their records with the outer run's.
"""

from __future__ import annotations

import builtins
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

from harness import needs, paths, scoreboard


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


STATE = pytest.StashKey[State]()
HEAD_AT_START = pytest.StashKey[str]()
METRICS = pytest.StashKey[dict]()
NOTE = pytest.StashKey[str]()
FACTS = pytest.StashKey[dict]()
METRIC_NAMES = ("fuel", "bytes", "passes")  # passes: spec 050, Decision 12


def pytest_addoption(parser: pytest.Parser) -> None:
    g = parser.getgroup("progress", "the progress harness (spec 002)")
    g.addoption("--accept", metavar="REASON", help="record this run as the accepted state")
    g.addoption("--accept-judge", metavar="REASON", help="also accept a changed judge")
    g.addoption("--accept-growth", metavar="REASON", help="also accept fuel or bytes growth")
    g.addoption(
        "--accept-fewer-passes", metavar="REASON", help="also accept a fall in a pass count"
    )
    g.addoption("--partial", metavar="REASON", help="allow accepted passes to be blocked")
    g.addoption("--retire", metavar="NODEID", action="append", default=[], help="drop a check")
    g.addoption("--progress-dir", metavar="DIR", help="where accepted.json and history.jsonl live")
    g.addoption("--progress-latest", metavar="FILE", help="where the run record is written")
    g.addoption("--known-gaps", metavar="FILE", help="the known gaps file")


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


WORKTREE_REFUSAL = (
    "accept: only the landing lane accepts, in the main tree (constitution §5.7); "
    "this is a linked worktree"
)


def _same_folder(a: Path, b: Path) -> bool:
    """`os.path.samefile` when both exist, so case and links cannot slip past; otherwise the
    resolved paths (spec 029, condition A)."""
    if a.exists() and b.exists():
        return os.path.samefile(a, b)
    return a.resolve() == b.resolve()


def writes_accepted_state(progress: Path, repo: Path | None = None) -> bool:
    """Whether `progress` is the context/progress folder of any worktree of this repository, the
    main tree's included. Any other folder (the self-tests' own) holds no accepted state."""
    return any(_same_folder(progress, w / "context" / "progress") for w in paths.worktrees(repo))


def accept_refusal(reason: str | None, progress: Path, repo: Path | None = None) -> str | None:
    """Why `--accept` is refused before collection, or None (spec 029, Decisions 2 and 4). Only
    `--accept` writes; --accept-judge, --accept-growth and --partial write nothing without it.
    Where git is absent no folder is the repository's, and `--accept` proceeds."""
    if not reason or not writes_accepted_state(progress, repo):
        return None
    if paths.linked_worktree(repo):
        return WORKTREE_REFUSAL
    changed = paths.dirty_path(repo)
    if changed is not None:
        return (
            f"accept: refused on a dirty tree: {changed} has a change the judge could see "
            "(spec 029, Decision 2)"
        )
    return None


def head_moved(config: pytest.Config) -> str | None:
    """Why the acceptance would name a commit the judge did not see whole, or None."""
    start = config.stash.get(HEAD_AT_START, None)
    now = (paths.git("rev-parse", "HEAD") or "").strip()
    if start is None or now == start:
        return None
    return f"accept: HEAD moved during the run ({start[:12]} to {now[:12]}) (spec 029)"


def pytest_configure(config: pytest.Config) -> None:
    reason, progress = _opt(config, "--accept"), progress_dir(config)
    refusal = accept_refusal(reason, progress, paths.REPO)
    if refusal:
        pytest.exit(refusal, returncode=1)  # before collection; nothing is written
    if reason and writes_accepted_state(progress, paths.REPO):  # checked again when written
        config.stash[HEAD_AT_START] = (paths.git("rev-parse", "HEAD") or "").strip()
    config.addinivalue_line("markers", "goal(area): a v1 progress check (spec 002)")
    config.addinivalue_line("markers", "slow: a guest job or the oracle")
    gaps_file = _opt(config, "--known-gaps")
    gaps, errors = load_gaps(Path(gaps_file) if gaps_file else paths.KNOWN_GAPS)
    config.stash[STATE] = State(gaps=gaps, gap_errors=errors)


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
    """Record one line a passing check says of itself, kept as its reason in latest.json (spec
    051: the callback scan's coverage). It is never compared, so it is no metric."""

    def record(text: str) -> None:
        request.node.stash[NOTE] = _first_line(text)

    return record


@pytest.fixture
def fact(request: pytest.FixtureRequest):
    """Attach a named fact to the current check's record in latest.json, under `facts`:
    reported, never ratcheted (spec 050: a group's `passed_digest`, its outcome counts, the files
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
    files = paths.judge_files()
    return {
        "at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commit": _git("rev-parse", "HEAD"),
        "dirty": paths.dirty_path() is not None,  # a change the judge could see (spec 029)
        "platform": f"{sys.platform}-{platform.machine().lower()}",
        "host": paths.sha256_bytes(socket.gethostname().encode())[:12],
        "wasmtime": wasmtime_version,
        "artifact": paths.sha256_file(wasm) if wasm and wasm.is_file() else None,
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
    for name, plugin in config.pluginmanager.list_name_plugin():
        f = _module_file(plugin)
        if f is None:
            module = type(plugin).__module__
            if not (module.startswith("_pytest") or module == "builtins"):
                found.append(f"plugin {name} ({module})")
        elif not (f.is_relative_to(pytest_dir) or f in judged):
            found.append(f"plugin {name} from {f}")
    return found


def _read(path: Path) -> str | None:
    return path.read_text() if path.is_file() else None


@pytest.hookimpl(tryfirst=True)
def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    config = session.config
    state = config.stash.get(STATE, None)
    if state is None or config.getoption("collectonly"):
        return
    if not state.areas and (_opt(config, "--accept") or _opt(config, "--retire")):
        state.lines = ["RED: --accept refused: this run collected no goal checks"]
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
        return
    for node, area in state.areas.items():
        if node in state.deselected:
            state.records[node] = {"area": area, "status": "deselected", "reason": ""}
        elif node not in state.records:  # collected, never ran (-x, --maxfail, an interrupt)
            state.records[node] = {"area": area, "status": "unrun", "reason": "did not run"}
    for rec in state.records.values():
        rec.setdefault("need", None)
        rec.setdefault("metrics", {})
    meta = run_meta()
    partial = _opt(config, "--partial")
    meta["partial"] = partial
    meta["overrides"] = [
        f"{o} {_opt(config, o)}"
        for o in ("--progress-dir", "--known-gaps", "--progress-latest")
        if _opt(config, o)
    ]
    addopts = os.environ.get("PYTEST_ADDOPTS", "").strip()
    if addopts:
        meta["overrides"].append(f"PYTEST_ADDOPTS {addopts}")
    this_repo = Path(str(config.rootpath)).resolve() == paths.REPO.resolve()
    foreign = foreign_steering(config) if this_repo else []
    meta["foreign"] = foreign
    run = {
        "meta": meta,
        "checks": dict(sorted(state.records.items())),
        "deselected": sorted(state.deselected),
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
    red = ratchet.red(partial=bool(partial)) if accepted else []
    if foreign:
        red.append("steered from outside the judge: " + "; ".join(foreign[:3]))
    if state.gap_errors:
        red.append("tests/known_gaps.toml: " + "; ".join(state.gap_errors))

    latest = latest_path(config)
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(scoreboard.dumps(run))

    # accept() judges the ratchet itself (it honours --retire, --partial, --accept-growth);
    # it needs only pytest's verdict and a sound gaps file.
    green = exitstatus == 0 and not state.gap_errors and not foreign and not addopts
    reason = _opt(config, "--accept")
    accept_line = None
    # The tree and HEAD as the acceptance is written, not only as the run began (029's build
    # review, finding 2): an edit or a commit made meanwhile refuses it.
    late = (accept_refusal(reason, pdir, paths.REPO) or head_moved(config)) if reason else None
    if late:
        red.append(f"--accept refused: {late}")
    elif reason:
        history_text = _read(pdir / "history.jsonl") or ""
        try:
            new, line = scoreboard.accept(
                run,
                accepted,
                history_text,
                ratchet,
                green=green,
                reason=reason,
                judge_reason=_opt(config, "--accept-judge"),
                growth_reason=_opt(config, "--accept-growth"),
                partial_reason=partial,
                retire=_opt(config, "--retire"),
                fewer_reason=_opt(config, "--accept-fewer-passes"),
            )
        except scoreboard.AcceptRefused as e:
            red.append(f"--accept refused: {e}")
        else:
            pdir.mkdir(parents=True, exist_ok=True)
            (pdir / "accepted.json").write_text(scoreboard.dumps(new))
            with (pdir / "history.jsonl").open("a") as f:
                f.write(line + "\n")
            accept_line = f"accepted: {pdir / 'history.jsonl'} line {json.loads(line)['n']}"
            ratchet = scoreboard.compare(run, new, root)  # re-judged against what was accepted
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
