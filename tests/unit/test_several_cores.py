"""The judge on several cores (spec 052): a parallel run judges as a serial run.

Each end-to-end case runs a small inner suite in a subprocess (xdist's workers are processes),
with its own progress folder, gaps file and run record, so nothing here touches the real ratchet.
"""

from __future__ import annotations

import json
import os
import sys
import types
from pathlib import Path

import pytest

from harness import paths, plugin, sameness, upstream

TESTS = paths.REPO / "tests"

GOALS = """
import os
import pytest
from harness import needs

pytestmark = pytest.mark.goal("rules")

def test_pass_metrics(metric, note, fact):
    metric("fuel", 1_000_000)
    metric("bytes", 100)
    metric("passes", 7)
    note("seven passed")
    fact("counts", {"passed": 7, "failed": 0})
    fact("digest", "abc")

def test_gap():
    assert False, "the named failure"

def unmet(monkeypatch):
    monkeypatch.setitem(needs.VOCABULARY, "runner", needs.Need("runner", lambda: False, "-"))

def test_blocked(monkeypatch):
    unmet(monkeypatch)
    needs.need("runner")

@pytest.mark.slow
def test_deselected():
    pass
"""
FAILING = """
@pytest.fixture
def broken_teardown():
    yield
    raise RuntimeError("teardown broke")

def test_gap_differs():
    assert False, "something else"

@pytest.mark.xfail(strict=True)
def test_xfail_without_a_gap():
    assert False

def test_xpass():
    pass

def test_skip_without_a_need():
    pytest.skip("not today")

def test_teardown_fails_after_a_pass(broken_teardown, metric):
    metric("fuel", 5)
"""
UNITS = """
import pytest

def test_unit_one():
    pass

def test_unit_two():
    pass

def test_unit_skipped():
    pytest.skip("not here")
"""
GAP = (
    '[[gap]]\ncheck = "test_goals.py::{}"\nmatch = "{}"\n'
    'reason = "known"\ncloses_with = "README.md"\n'
)
GREEN_GAPS = GAP.format("test_gap", "the named failure")
ALL_GAPS = (
    GREEN_GAPS + GAP.format("test_gap_differs", "the named failure") + GAP.format("test_xpass", "x")
)


@pytest.fixture
def suite(pytester: pytest.Pytester, monkeypatch):
    """`suite(green)` writes the inner suite; `suite.run(tag, *args)` runs it once in a
    subprocess and returns (result, record)."""
    monkeypatch.setenv("PYTHONPATH", str(TESTS))
    monkeypatch.delenv("PYTEST_ADDOPTS", raising=False)
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")

    def write(green: bool = False) -> None:
        pytester.makepyfile(test_goals=GOALS + ("" if green else FAILING), test_units=UNITS)
        (pytester.path / "gaps.toml").write_text(GREEN_GAPS if green else ALL_GAPS)

    def run(tag: str, *args: str, progress: Path | None = None, timeout: int = 300):
        latest = pytester.path / f"{tag}.json"
        progress = progress or pytester.path / f"progress-{tag}"
        progress.mkdir(exist_ok=True)
        result = pytester.runpytest_subprocess(
            "-p",
            "harness.plugin",
            "-p",
            "no:cacheprovider",
            "--progress-dir",
            str(progress),
            "--progress-latest",
            str(latest),
            "--known-gaps",
            str(pytester.path / "gaps.toml"),
            *args,
            timeout=timeout,
        )
        record = json.loads(latest.read_text()) if latest.is_file() else None
        return result, record

    write.run = run
    write.path = pytester.path
    return write


def board(result) -> list[str]:
    """The scoreboard's lines: the progress section, up to the next separator."""
    lines = result.outlines
    start = next(i for i, line in enumerate(lines) if line.strip("= ") == "progress")
    rest = lines[start + 1 :]
    end = next((i for i, line in enumerate(rest) if line.startswith("=")), len(rest))
    return rest[:end]


SHAPES = {
    "whole": ["-m", "not slow"],
    "node ids": [
        "test_goals.py::test_pass_metrics",
        "test_goals.py::test_teardown_fails_after_a_pass",
        "test_units.py::test_unit_one",
    ],
    "-k": ["-k", "pass or unit"],
}


@pytest.mark.parametrize("shape", SHAPES)
def test_a_parallel_run_judges_as_a_serial_run(suite, shape) -> None:
    """Criterion 1: every kind of record, serially and under -n 2 and -n 3, the same."""
    suite()
    serial_result, serial = suite.run("serial", *SHAPES[shape])
    assert serial is not None, serial_result.stdout.str()[-2000:]
    for n in ("2", "3"):
        result, record = suite.run(f"n{n}", "-n", n, *SHAPES[shape])
        assert record is not None, result.stdout.str()[-3000:] + result.stderr.str()[-2000:]
        assert sameness.differences(serial, record) == [], n
        for key in ("checks", "deselected", "collected_files", "suite"):
            assert record[key] == serial[key], (n, key)
        assert board(result) == board(serial_result), n
        assert result.ret == serial_result.ret, n
        assert all(r["status"] != "unrun" for r in record["checks"].values()), n
        assert record["meta"]["workers"] == int(n) and serial["meta"]["workers"] == 0
    if shape == "whole":  # every kind of record is in it
        statuses = {k.split("::")[1]: v["status"] for k, v in serial["checks"].items()}
        assert statuses == {
            "test_pass_metrics": "pass",
            "test_gap": "gap",
            "test_blocked": "blocked",
            "test_deselected": "deselected",
            "test_gap_differs": "fail",
            "test_xfail_without_a_gap": "fail",
            "test_xpass": "fail",
            "test_skip_without_a_need": "fail",
            "test_teardown_fails_after_a_pass": "fail",
        }
        assert serial["suite"] == {"passed": 2, "skipped": 1, "total": 3}
        assert serial["checks"]["test_goals.py::test_pass_metrics"]["facts"]


def _history(progress: Path) -> list[dict]:
    text = (
        (progress / "history.jsonl").read_text() if (progress / "history.jsonl").is_file() else ""
    )
    return [json.loads(line) for line in text.splitlines()]


def test_one_acceptance_by_the_controller(suite) -> None:
    """Criterion 2: a green run accepted under -n 3 writes one history line and one
    accepted.json, as a serial acceptance does; a failing run then writes nothing."""
    suite(green=True)
    serial_progress, parallel_progress = suite.path / "p-serial", suite.path / "p-parallel"
    for progress in (serial_progress, parallel_progress):
        progress.mkdir()
    r1, _ = suite.run("a-serial", "-m", "not slow", "--accept", "r", progress=serial_progress)
    r2, _ = suite.run(
        "a-n3", "-m", "not slow", "-n", "3", "--accept", "r", progress=parallel_progress
    )
    assert r1.ret == 0 and r2.ret == 0, r2.stdout.str()[-3000:]
    lines_s, lines_p = _history(serial_progress), _history(parallel_progress)
    assert len(lines_s) == len(lines_p) == 1

    def drop(d: dict) -> dict:
        return {k: v for k, v in d.items() if k not in ("at", "accepted")}

    assert drop(lines_p[0]) == drop(lines_s[0])
    acc_s = json.loads((serial_progress / "accepted.json").read_text())
    acc_p = json.loads((parallel_progress / "accepted.json").read_text())
    assert acc_p["checks"] == acc_s["checks"]
    suite(green=False)
    r3, _ = suite.run("a-fail", "-n", "3", "--accept", "r", progress=parallel_progress)
    assert r3.ret == 1
    assert len(_history(parallel_progress)) == 1


# ---------------------------------------------------------------------------------------------
# Criterion 3: workers write nothing and guard nothing


class _Options(types.SimpleNamespace):
    pass


class _FakeConfig:
    def __init__(self, tmp: Path, worker: bool) -> None:
        self.stash = pytest.Stash()
        self.values = {
            "--accept": "r",
            "--progress-dir": str(paths.PROGRESS),
            "--progress-latest": str(tmp / "latest.json"),
            "--known-gaps": str(tmp / "gaps.toml"),
            "collectonly": False,
        }
        self.option = _Options(dist="no", tx=[], collectonly=False)
        if worker:
            self.workerinput = {"workerid": "gw0"}
            self.workeroutput = {}

    def getoption(self, name):
        return self.values.get(name)

    def addinivalue_line(self, *_):
        pass


def test_a_worker_writes_nothing_and_hands_its_collection_over(tmp_path) -> None:
    config = _FakeConfig(tmp_path, worker=True)
    config.values["--progress-dir"] = str(tmp_path / "progress")
    state = plugin.State()
    state.areas = {"t.py::a": "rules"}
    state.records = {"t.py::a": {"area": "rules", "status": "pass", "reason": ""}}
    config.stash[plugin.STATE] = state
    session = types.SimpleNamespace(config=config, exitstatus=0)
    plugin.pytest_sessionfinish(session, 0)
    assert set(config.workeroutput[plugin.WORKER_OUTPUT]) == {
        "areas",
        "deselected",
        "collected_files",
        "narrowed_files",
    }
    assert sorted(p.name for p in tmp_path.rglob("*")) == []


def test_a_worker_skips_the_lanes_guards(tmp_path) -> None:
    """The accept refusal and the HEAD stash run in the controller only (Decision 4). The same
    config without `workerinput` is refused here (a linked worktree or a dirty tree) or has its
    HEAD stashed (the lane's clean main tree)."""
    worker = _FakeConfig(tmp_path, worker=True)
    try:
        plugin.pytest_configure(worker)
    except BaseException as e:  # pytest.exit would end this whole run: make it a failure
        pytest.fail(f"a worker ran the lane's guards: {e}")
    assert plugin.HEAD_AT_START not in worker.stash
    plain = _FakeConfig(tmp_path, worker=False)
    try:
        plugin.pytest_configure(plain)
    except BaseException as e:  # pytest.exit
        assert "accept: " in str(e)
    else:
        assert plugin.HEAD_AT_START in plain.stash


# ---------------------------------------------------------------------------------------------
# Criterion 5: the allowance is narrow


class _Manager:
    def __init__(self, plugins: list) -> None:
        self.plugins = plugins

    def list_name_plugin(self):
        return [(f"p{i}", p) for i, p in enumerate(self.plugins)]


def _steering(plugins: list) -> list[str]:
    config = types.SimpleNamespace(
        inipath=paths.REPO / "pyproject.toml", pluginmanager=_Manager(plugins)
    )
    return plugin.foreign_steering(config)


def _xdist_plugins() -> list:
    import xdist.dsession
    import xdist.looponfail
    import xdist.plugin

    reporter = object.__new__(xdist.dsession.TerminalDistReporter)
    return [xdist.plugin, xdist.looponfail, reporter]


def test_xdist_and_the_controller_are_allowed_at_the_locked_versions() -> None:
    controller = plugin.Controller(types.SimpleNamespace(stash=pytest.Stash()))
    assert _steering([*_xdist_plugins(), controller]) == []


@pytest.mark.parametrize("which", ["pytest-xdist", "xdist", "execnet"])
def test_xdist_at_another_version_is_foreign(monkeypatch, which) -> None:
    versions = dict(plugin.xdist_versions())
    versions[which] = "0.0.0"
    monkeypatch.setattr(plugin, "xdist_versions", lambda: versions)
    found = _steering(_xdist_plugins())
    assert len(found) == 3, found


def test_other_plugins_stay_foreign(tmp_path) -> None:
    import iniconfig

    impostor = types.ModuleType("xdist_impostor")
    impostor.__file__ = str(tmp_path / "xdist" / "plugin.py")
    stranger = types.ModuleType("stranger")
    stranger.__file__ = str(tmp_path / "stranger.py")
    found = _steering([iniconfig, impostor, stranger])
    assert len(found) == 3, found  # iniconfig: site-packages outside xdist/ (C1)


# ---------------------------------------------------------------------------------------------
# Criterion 6: one way to run in parallel

REFUSED = {
    "-n logical": ["-n", "logical"],
    "--dist each": ["-n", "2", "--dist", "each"],
    "--dist loadfile": ["-n", "2", "--dist", "loadfile"],
    "-d": ["-d"],
    "--no-loadscope-reorder": ["-n", "2", "--no-loadscope-reorder"],
    "--maxschedchunk": ["-n", "2", "--maxschedchunk", "2"],
    "--tx": ["-n", "2", "--tx", "popen"],
    "--px": ["--px", "popen"],
    "--rsyncdir": ["--rsyncdir", "tests"],
    "--rsyncignore": ["--rsyncignore", "x"],
    "--looponfail": ["-f"],
}


@pytest.mark.parametrize("option", REFUSED)
def test_each_refused_option_exits_before_anything_runs(suite, option) -> None:
    suite(green=True)
    result, record = suite.run("refused", *REFUSED[option], timeout=120)
    assert result.ret == 1, result.stdout.str()[-2000:]
    assert record is None
    assert list((suite.path / "progress-refused").iterdir()) == []
    assert any(option.split()[0] in line and "spec 052" in line for line in result.errlines), (
        result.errlines
    )


ALLOWED = {
    "--maxprocesses": ["-n", "2", "--maxprocesses", "1"],
    "--max-worker-restart": ["-n", "2", "--max-worker-restart", "0"],
    "--dist load": ["-n", "2", "--dist", "load"],
    "--loadscope-reorder": ["-n", "2", "--loadscope-reorder"],
    "--testrunuid": ["-n", "2", "--testrunuid", "x"],
}


def test_each_allowed_option_judges_as_serial(suite) -> None:
    suite(green=True)
    _, serial = suite.run("allowed-serial", "-m", "not slow")
    for option, args in ALLOWED.items():
        result, record = suite.run("allowed", "-m", "not slow", *args)
        assert record is not None, (option, result.stdout.str()[-2000:])
        assert sameness.differences(serial, record) == [], option
    assert record["meta"]["workers"] == 2


# ---------------------------------------------------------------------------------------------
# Criterion 7: the scopes, exactly and in effect


def test_the_upstream_scopes_are_exact() -> None:
    configs = upstream.load_all()
    scopes = plugin.upstream_scopes(configs)
    by_hand: dict[str, str] = {}
    for c in configs.values():
        for g in c.groups:
            by_hand[f"{plugin.UPSTREAM_FILE}::test_upstream_suite[{g}]"] = f"upstream {g}"
        for k in c.expected:
            by_hand[f"{plugin.UPSTREAM_FILE}::test_upstream_class[{k.group}-{k.id}]"] = (
                f"upstream {k.group}"
            )
    assert scopes == by_hand
    groups = {g for c in configs.values() for g in c.groups}
    assert set(scopes.values()) == {f"upstream {g}" for g in groups}
    other = f"{plugin.UPSTREAM_FILE}::test_upstream_files_are_well_formed"
    assert plugin.scope_of(other, scopes) == other
    assert plugin.scope_of("tests/x.py::test_y", scopes) == "tests/x.py::test_y"


def test_the_collected_upstream_ids_fall_in_their_groups(pytester) -> None:
    """Every collected node id of the upstream file is either in the map or its own scope, and
    each group's check shares its scope with all its classes."""
    configs = upstream.load_all()
    scopes = plugin.upstream_scopes(configs)
    groups = {g for c in configs.values() for g in c.groups}
    classes = sum(len(c.expected) for c in configs.values())
    assert len(scopes) == len(groups) + classes
    for c in configs.values():
        for k in c.expected:
            node = f"{plugin.UPSTREAM_FILE}::test_upstream_class[{k.group}-{k.id}]"
            group = f"{plugin.UPSTREAM_FILE}::test_upstream_suite[{k.group}]"
            assert plugin.scope_of(node, scopes) == plugin.scope_of(group, scopes)


SCOPED = """
import os
import pytest

pytestmark = pytest.mark.goal("rules")

@pytest.mark.parametrize("g", [{group!r}])
def test_upstream_suite(fact, g):
    fact("pid", os.getpid())

{others}

@pytest.mark.parametrize("k", [{klass!r}])
def test_upstream_class(fact, k):
    fact("pid", os.getpid())
"""


def test_xdist_deals_with_the_judges_scheduler(suite) -> None:
    """End to end: a group's check and its class's check run in one worker, and the record names
    the judge's scheduler."""
    configs = upstream.load_all()
    k = next(k for c in configs.values() for k in c.expected)
    others = "\n".join(
        f"def test_other_{i}(fact):\n    fact('pid', os.getpid())\n" for i in range(6)
    )
    folder = suite.path / "tests" / "checks"
    folder.mkdir(parents=True)
    (folder / "test_v1_3_upstream_suites.py").write_text(
        SCOPED.format(group=k.group, klass=f"{k.group}-{k.id}", others=others)
    )
    (suite.path / "gaps.toml").write_text("")
    result, record = suite.run("scoped", "-n", "4", "--rootdir", str(suite.path), "tests/checks")
    assert record is not None, result.stdout.str()[-3000:]
    pids = {n.split("::")[1]: r["facts"]["pid"] for n, r in record["checks"].items()}
    suite_pid = next(v for n, v in pids.items() if n.startswith("test_upstream_suite"))
    class_pid = next(v for n, v in pids.items() if n.startswith("test_upstream_class"))
    assert suite_pid == class_pid
    assert record["meta"]["scheduler"] == "JudgeScheduling"


# ---------------------------------------------------------------------------------------------
# sameness: one definition of "the same answer" (Decision 12)


def _record(**checks) -> dict:
    return {
        "checks": {
            name: {"area": "rules", "need": None, "metrics": {}, **fields}
            for name, fields in checks.items()
        },
        "deselected": [],
        "collected_files": ["t.py"],
        "suite": {"passed": 1, "skipped": 0, "total": 1},
    }


def test_sameness_counts_what_must_be_equal() -> None:
    a = _record(
        p={"status": "pass", "reason": "n", "metrics": {"fuel": 1_000_000, "bytes": 5}},
        f={"status": "fail", "reason": "at /tmp/x1"},
    )
    assert sameness.differences(a, a) == []
    b = json.loads(json.dumps(a))
    b["checks"]["p"]["metrics"]["fuel"] = 1_000_090  # 9e-5: within the tolerance
    b["checks"]["f"]["reason"] = "at /tmp/x2"  # a failure's reason is not compared
    assert sameness.differences(a, b) == []
    b["checks"]["p"]["metrics"]["fuel"] = 1_000_200  # 2e-4: beyond it
    b["checks"]["p"]["reason"] = "m"
    b["checks"]["p"]["metrics"]["bytes"] = 6
    b["suite"]["passed"] = 0
    found = sameness.differences(a, b)
    assert len(found) == 4, found
    c = json.loads(json.dumps(a))
    c["checks"]["f"]["status"] = "pass"
    del c["checks"]["p"]
    assert len(sameness.differences(a, c)) == 2


def test_sameness_command_exits_by_its_answer(tmp_path) -> None:
    import subprocess

    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text(json.dumps(_record(p={"status": "pass", "reason": ""})))
    b.write_text(json.dumps(_record(p={"status": "fail", "reason": ""})))
    script = str(TESTS / "harness" / "sameness.py")
    same = subprocess.run([sys.executable, script, str(a), str(a)], capture_output=True, text=True)
    differ = subprocess.run(
        [sys.executable, script, str(a), str(b)], capture_output=True, text=True
    )
    assert (same.returncode, same.stdout) == (0, "")
    assert differ.returncode == 1 and "status" in differ.stdout


def test_a_worker_is_known_by_workerinput_only(monkeypatch) -> None:
    monkeypatch.setenv("PYTEST_XDIST_WORKER", "gw9")
    assert plugin.is_worker(types.SimpleNamespace()) is False
    assert plugin.is_worker(types.SimpleNamespace(workerinput={})) is True
    assert os.environ["PYTEST_XDIST_WORKER"] == "gw9"
