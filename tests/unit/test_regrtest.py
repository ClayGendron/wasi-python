"""CPython's own tests in the guest, on fixed inputs (spec 065): the stream, the verdict, the
classes, the trap entries, the deselection, environment and host entries, the guard, the universe,
the rules, the stage from the tarball, and the driver's source. No guest runs here."""

from __future__ import annotations

import io
import re
import tarfile
from dataclasses import replace
from pathlib import Path

import pytest

from harness import paths, regrtest, upstream

CONFIGS = upstream.load_all()
PY = CONFIGS["python"]
DRIVER = (upstream.HERE / regrtest.DRIVER).read_text()


def _cfg(**kw) -> upstream.Config:
    """A small regrtest config: one group of two modules, one class, one environment entry."""
    base = dict(
        package="python",
        marker="",
        args=[],
        path_packages=[],
        markers=[],
        support=[],
        groups={"g": upstream.Group("g", (), 10**9, ("test_a", "test_b"), "python/g.txt")},
        not_selected=[upstream.NotSelected((), "r", "README.md", ("test_c",))],
        traps=[
            upstream.Trap("t", "", "r", "README.md", "g", "test.test_a.T.test_deep", ""),
            upstream.Trap("w", "", "r", "README.md", "g", "", "test_d"),
        ],
        expected=[upstream.Klass("no-x", "g", "error", "x is unavailable", "r", "README.md")],
        runner="regrtest",
        component="cpython",
        grant=regrtest.GRANT,
        resources="all",
        options=("--fail-env-changed",),
        warnings="error",
        deselected=[
            regrtest.Deselected("des", "g", ("test.test_b.Skips.test_one",), "r", "README.md")
        ],
        environment=[
            regrtest.Environment("env", "g", ("test_b",), ("sys.path",), "r", "README.md")
        ],
        host_dependent=[],
    )
    base.update(kw)
    return upstream.Config(**base)


LISTED = "L test_a\nL test_b\nL test_c\nL test_d\n"


def _run(trapped=None, cause=None, exit_code=0) -> regrtest.GuestRun:
    return regrtest.GuestRun(exit_code, trapped, cause, 10**9, "")


def _judge(text: str, cfg=None, run=None, here="darwin") -> regrtest.GroupOutcome:
    cfg = cfg or _cfg()
    return regrtest.judge_group(regrtest.parse_stream(text), run or _run(), cfg, "g", here)


CLEAN = (
    LISTED
    + "C test_a\nS test.test_a.T.test_one\nR passed test.test_a.T.test_one -- \n"
    + "D test_a PASSED kept\n"
    + "C test_b\nS test.test_b.U.test_two\n"
    + "R error test.test_b.U.test_two -- OSError: x is unavailable\n"
    + "D test_b FAILED kept\nE 2\n"
)


# ---------------------------------------------------------------------------------------------
# The stream and the verdict (criterion 2)


def test_a_clean_stream_passes_counts_passes_and_sorts_its_failure() -> None:
    o = _judge(CLEAN)
    assert o.findings == []
    assert o.passes == 1 and o.members == {"no-x": ["test.test_b.U.test_two"]}
    assert o.passed_digest == upstream.passed_digest(["test.test_a.T.test_one"])


def test_a_failing_subtest_sorts_by_its_own_id() -> None:
    text = CLEAN.replace(
        "R error test.test_b.U.test_two -- OSError: x is unavailable",
        "R error test.test_b.U.test_two [readinto] -- OSError: x is unavailable",
    )
    assert _judge(text).members == {"no-x": ["test.test_b.U.test_two [readinto]"]}


@pytest.mark.parametrize(
    ("change", "finding"),
    [
        (
            ("D test_b FAILED kept", "X test_b -- ImportError: no\nD test_b UNCAUGHT_EXC kept"),
            "failed to load",
        ),
        (
            (
                "D test_a PASSED kept",
                "D test_a ENV_CHANGED altered sys.path was modified by test_a",
            ),
            "ended ENV_CHANGED",
        ),
        (("D test_a PASSED kept", "D test_a INTERRUPTED kept"), "ended INTERRUPTED"),
        (("E 2", "E 3"), "exit code 3"),
        (("E 2\n", ""), "no E line"),
        (("L test_d\n", "L test_d\nL test_new\n"), "test_new is in no group"),
        (("L test_d\n", ""), "names test_d, which regrtest does not list"),
        (
            ("E 2", "M json /cpython/lib/json/__init__.py product\nE 2"),
            "product module came from the grant",
        ),
        (
            (
                "R passed test.test_a.T.test_one -- ",
                "R failed test.test_a.T.test_one -- AssertionError: no",
            ),
            "unexpected failed",
        ),
        (
            ("D test_a PASSED kept", "D test_a FAILED altered sys.path was modified by test_a"),
            "altered the environment",
        ),
    ],
)
def test_protocol_faults_are_group_findings(change, finding) -> None:
    assert change[0] in CLEAN
    o = _judge(CLEAN.replace(change[0], change[1]))
    assert any(finding in f for f in o.findings), o.findings


@pytest.mark.parametrize(
    "change",
    [
        ("R passed test.test_a.T.test_one -- ", "R skipped test.test_a.T.test_one -- needs x"),
        (
            "R passed test.test_a.T.test_one -- ",
            "R xfailed test.test_a.T.test_one -- AssertionError",
        ),
        ("D test_a PASSED kept", "D test_a SKIPPED kept"),
        ("D test_a PASSED kept", "D test_a RESOURCE_DENIED kept"),
        ("D test_a PASSED kept", "D test_a DID_NOT_RUN kept"),
        # the review's F3 case: a test's helper, half made, from the grant
        (
            "E 2",
            "M generate_build_details /cpython/Tools/build/generate-build-details.py test\nE 2",
        ),
        ("D test_b FAILED kept", "D test_b FAILED altered sys.path was modified by test_b"),
    ],
)
def test_upstreams_own_outcomes_and_admitted_changes_are_not_findings(change) -> None:
    assert _judge(CLEAN.replace(*change)).findings == []


def test_an_unexpected_success_sorts_as_a_failure() -> None:
    o = _judge(
        CLEAN.replace(
            "R passed test.test_a.T.test_one -- ",
            "R xpassed test.test_a.T.test_one -- unexpected success",
        )
    )
    assert any("unexpected failed test.test_a.T.test_one" in f for f in o.findings), o.findings


def test_a_trap_names_where_it_surfaced_at_or_after() -> None:
    text = LISTED + "C test_a\nS test.test_a.T.test_one\n"
    o = _judge(text, run=_run("error", "wasm trap: call stack exhausted"))
    assert o.findings[-1:] == [
        "trap: wasm trap: call stack exhausted at or after test.test_a.T.test_one"
    ]
    o = _judge(LISTED + "C test_a\n", run=_run("error", "wasm trap: call stack exhausted"))
    assert "at or after test_a" in o.findings[-1]


# ---------------------------------------------------------------------------------------------
# Environment entries (C1, D1, D2, D4)


@pytest.mark.parametrize(
    ("warnings", "admitted"),
    [
        ("sys.path was modified by test_b", True),
        ("sys.path_hooks was modified by test_b", False),  # D1: the resource named exactly
        ("sys.path was modified by test_b|Unraisable exception", False),  # D4: the bare line
        ("", False),  # D2: altered, and no warning line
    ],
)
def test_an_environment_entry_admits_only_its_kinds(warnings, admitted) -> None:
    line = f"D test_b FAILED altered {warnings}".rstrip()
    o = _judge(CLEAN.replace("D test_b FAILED kept", line))
    assert (o.findings == []) is admitted, o.findings
    assert o.environment["env"] == (["test_b"] if admitted else [])


def test_an_environment_entry_is_exact_like_a_class() -> None:
    assert regrtest.environment_findings([], ("test_b",)) == []
    assert regrtest.environment_findings(["test_b"], ("test_b",)) == ["test_b"]
    assert regrtest.environment_findings(["test_b", "test_e"], ("test_b",)) == [
        "test_b",
        "test_e",
        "+test_e",
    ]
    assert regrtest.environment_findings(["test_e"], ("test_b",)) == [
        "test_e",
        "+test_e",
        "-test_b",
    ]


def test_stand_in_an_entry_by_module_alone_admits_an_unraisable_exception() -> None:
    """The confirmation's C1 stand-in: matching the module without its kinds lets a new cause
    through; the real entry does not."""
    text = CLEAN.replace(
        "D test_b FAILED kept",
        "D test_b FAILED altered sys.path was modified by test_b|Unraisable exception",
    )
    any_kind = type(
        "AnyKind",
        (),
        {"id": "env", "group": "g", "modules": ("test_b",), "admits": lambda self, w: True},
    )()
    assert _judge(text, cfg=_cfg(environment=[any_kind])).findings == []
    assert _judge(text).findings != []


# ---------------------------------------------------------------------------------------------
# Trap entries (Decision 1, F5, C2)


def _trap(cfg, tid):
    return next(t for t in cfg.traps if t.id == tid)


def test_an_open_trap_entry_gives_one_finding_trap_or_no_trap() -> None:
    cfg = _cfg()
    t = _trap(cfg, "t")
    trapped = regrtest.trap_verdict(
        regrtest.parse_stream("C test_a\nS test.test_a.T.test_deep\n"),
        _run("error", "wasm trap: call stack exhausted"),
        t,
    )
    clean = regrtest.trap_verdict(
        regrtest.parse_stream(
            "C test_a\nS test.test_a.T.test_deep\nR passed test.test_a.T.test_deep -- \n"
            "D test_a PASSED kept\nE 0\n"
        ),
        _run(),
        t,
    )
    assert trapped.findings == clean.findings == ["open trap entry: t"]
    assert trapped.seen == "trap at or after test.test_a.T.test_deep"
    assert clean.seen == "no trap on this host"


@pytest.mark.parametrize(
    ("text", "run", "finding"),
    [
        (
            "C test_a\nS test.test_a.T.test_deep\n",
            _run("error", "wasm trap: indirect call type mismatch"),
            "another cause",
        ),
        ("C test_a\nS test.test_a.T.test_deep\n", _run("out of fuel"), "out of fuel"),
        ("C test_a\nD test_a PASSED kept\nE 4\n", _run(), "ran nothing"),
        (
            "C test_a\nS test.test_a.T.test_deep\n"
            "R error test.test_a.T.test_deep -- RecursionError: x\nD test_a FAILED kept\nE 2\n",
            _run(),
            "error without a trap",
        ),
    ],
)
def test_a_trap_entry_is_red_for_another_ending(text, run, finding) -> None:
    v = regrtest.trap_verdict(regrtest.parse_stream(text), run, _trap(_cfg(), "t"))
    assert any(finding in f for f in v.findings[1:]), v.findings


def test_a_whole_module_entry_that_runs_to_its_end_is_open_with_its_counts() -> None:
    """C2: where test_traceback does not trap, its failures (for want of _testcapi) are not judged
    while the entry is open; its counts are a fact. Without its D line it is red."""
    w = _trap(_cfg(), "w")
    lines = ["C test_d"] + [
        f"S test.test_d.T.t{i}\nR error test.test_d.T.t{i} -- ModuleNotFoundError: _testcapi"
        for i in range(96)
    ]
    lines += [
        f"S test.test_d.T.f{i}\nR failed test.test_d.T.f{i} -- AssertionError" for i in range(9)
    ]
    text = "\n".join(lines) + "\nD test_d FAILED kept\nE 2\n"
    v = regrtest.trap_verdict(regrtest.parse_stream(text), _run(), w)
    assert v.findings == ["open trap entry: w"] and v.counts == {"error": 96, "failed": 9}
    v = regrtest.trap_verdict(
        regrtest.parse_stream(text.replace("D test_d FAILED kept\n", "")), _run(), w
    )
    assert any("no D line" in f for f in v.findings), v.findings


def test_stand_in_a_whole_module_check_that_judges_its_failures_is_red() -> None:
    """C2's stand-in: judging test_traceback's failures as a group would turn a host with more
    stack headroom red."""
    text = (
        "C test_d\nS test.test_d.T.t\nR error test.test_d.T.t -- ModuleNotFoundError: _testcapi\n"
        "D test_d FAILED kept\nE 2\n"
    )
    as_group = regrtest.judge_group(
        regrtest.parse_stream(LISTED + text), _run(), _cfg(), "g", "linux"
    )
    assert any("unexpected error" in f for f in as_group.findings)
    assert regrtest.trap_verdict(
        regrtest.parse_stream(text), _run(), _trap(_cfg(), "w")
    ).findings == ["open trap entry: w"]


# ---------------------------------------------------------------------------------------------
# Deselection and host entries (Decision 21, C3)


def test_a_deselected_id_that_ran_is_reported() -> None:
    o = _judge(
        CLEAN.replace(
            "D test_b FAILED kept",
            "S test.test_b.Skips.test_one\n"
            "R passed test.test_b.Skips.test_one -- \nD test_b FAILED kept",
        )
    )
    assert o.deselected_ran == ["test.test_b.Skips.test_one"]
    assert _judge(CLEAN).deselected_ran == []


def test_a_group_spec_deselects_trap_and_entry_ids_but_not_whole_modules() -> None:
    spec = regrtest.group_spec(_cfg(), "g")
    assert spec["modules"] == ["test_a", "test_b"]
    assert spec["ignore"] == ["test.test_a.T.test_deep", "test.test_b.Skips.test_one"]
    assert spec["options"] == ["--fail-env-changed"] and spec["warnings"] == "error"
    assert regrtest.trap_spec(_cfg(), _trap(_cfg(), "t"))["match"] == ["test.test_a.T.test_deep"]
    assert regrtest.trap_spec(_cfg(), _trap(_cfg(), "w"))["modules"] == ["test_d"]


def _host(**kw) -> regrtest.HostEntry:
    base = dict(
        id="h",
        group="g",
        test="",
        module="",
        results={},
        passes={},
        digests={},
        reason="r",
        closes_with="README.md",
    )
    base.update(kw)
    return regrtest.HostEntry(**base)


def test_a_test_host_entry_is_checked_exactly_per_system_and_out_of_the_count() -> None:
    h = _host(test="test.test_a.T.test_one", results={"darwin": "passed", "linux": "skipped"})
    cfg = _cfg(host_dependent=[h])
    o = _judge(CLEAN, cfg=cfg, here="darwin")
    assert o.findings == [] and o.passes == 0
    o = _judge(CLEAN, cfg=cfg, here="linux")
    assert any("host entry h" in f and "passed" in f for f in o.findings), o.findings


def test_a_module_host_entry_checks_its_own_passes_per_system() -> None:
    digest = upstream.passed_digest(["test.test_a.T.test_one"])
    h = _host(
        module="test_a",
        results={"darwin": "PASSED"},
        passes={"darwin": 1},
        digests={"darwin": digest},
    )
    o = _judge(CLEAN, cfg=_cfg(host_dependent=[h]))
    assert o.findings == [] and o.passes == 0
    h2 = replace(h, passes={"darwin": 2})
    o = _judge(CLEAN, cfg=_cfg(host_dependent=[h2]))
    assert any("1 passes on darwin" in f for f in o.findings), o.findings


def test_a_module_host_entry_admits_a_load_error_only_where_recorded() -> None:
    text = CLEAN.replace(
        "D test_b FAILED kept", "X test_b -- ImportError: no\nD test_b UNCAUGHT_EXC kept"
    )
    h = _host(module="test_b", results={"darwin": "load-error", "linux": "FAILED"})
    cfg = _cfg(host_dependent=[h])
    assert not any("failed to load" in f for f in _judge(text, cfg=cfg, here="darwin").findings)
    assert any("failed to load" in f for f in _judge(text, cfg=cfg, here="linux").findings)


# ---------------------------------------------------------------------------------------------
# The rules (criterion 1, C5)


def _gaps(cfg) -> set[str]:
    out = {upstream.trap_node(t.id) for t in cfg.traps}
    out |= {regrtest.deselected_node(d.group, d.id) for d in cfg.deselected}
    out |= {regrtest.environment_node(e.group, e.id) for e in cfg.environment}
    out |= {regrtest.host_node(h.group, h.id) for h in cfg.host_dependent}
    return out


def test_the_small_config_passes_the_rules() -> None:
    assert regrtest.rule_errors(_cfg(), _gaps(_cfg())) == []


@pytest.mark.parametrize(
    ("kw", "error"),
    [
        ({"groups": {"g": upstream.Group("g", (), 1, ("test_b", "test_a"), "x")}}, "not sorted"),
        ({"groups": {"g": upstream.Group("g", (), 1, ("test_a", "test_a"), "x")}}, "twice"),
        (
            {
                "groups": {
                    "g": upstream.Group("g", (), 1, ("test_a", "test_monitoring", "test_z"), "x")
                }
            },
            "not last",
        ),
        (
            {
                "groups": {
                    "g": upstream.Group(
                        "g", (), 1, ("test_a", "test_profiling", "test_monitoring"), "x"
                    )
                }
            },
            "test_profiling",
        ),
        (
            {"not_selected": [upstream.NotSelected((), "r", "README.md", ("test_a",))]},
            "test_a is in g and not selected",
        ),
        (
            {"traps": [upstream.Trap("t", "", "r", "README.md", "nope", "test.test_a.T.x", "")]},
            "names no group",
        ),
        (
            {"traps": [upstream.Trap("t", "", "r", "README.md", "g", "test.test_z.T.x", "")]},
            "in no module of g",
        ),
        (
            {
                "deselected": [
                    regrtest.Deselected("des", "g", ("test.test_z.T.x",), "r", "README.md")
                ]
            },
            "in no module of g",
        ),
        (
            {"environment": [regrtest.Environment("env", "g", ("test_b",), (), "r", "README.md")]},
            "no kind of change",
        ),
    ],
)
def test_rule_variants_fail_with_their_own_line(kw, error) -> None:
    cfg = _cfg(**kw)
    errors = regrtest.rule_errors(cfg, _gaps(cfg))
    assert any(error in e for e in errors), errors


def test_an_entry_without_its_gap_fails_the_rules() -> None:
    errors = regrtest.rule_errors(_cfg(), set())
    assert any("deselection des has no gap" in e for e in errors), errors
    assert any("environment entry env has no gap" in e for e in errors), errors


def test_a_host_entry_must_record_each_system_its_group_runs_on() -> None:
    h = _host(test="test.test_a.T.test_one", results={"darwin": "passed", "linux": "maybe"})
    cfg = _cfg(host_dependent=[h])
    errors = regrtest.rule_errors(cfg, _gaps(cfg), systems_of={"g": {"darwin", "linux", "win32"}})
    assert any("records nothing for win32" in e for e in errors), errors
    assert any("linux = 'maybe'" in e for e in errors), errors


SOURCES = {
    "Lib/test/test_a.py": (
        "class Base:\n    def test_deep(self): pass\n\nclass T(Base):\n    pass\n"
    ),
    "Lib/test/test_b/__init__.py": "",
    "Lib/test/test_b/test_b.py": "class Skips:\n    def test_one(self): pass\n",
    "Lib/test/test_d.py": "",
    "Lib/test/test_e.py": "if True:\n    class C:\n        def test_x(self): pass\n",
}


def test_ids_resolve_in_the_tarballs_source_inherited_methods_included() -> None:
    assert regrtest.id_exists("test.test_a.T.test_deep", SOURCES)
    assert regrtest.id_exists("test.test_b.test_b.Skips.test_one", SOURCES)
    assert not regrtest.id_exists("test.test_a.T.test_gone", SOURCES)
    assert not regrtest.id_exists("test.test_a.Gone.test_deep", SOURCES)
    assert regrtest.id_exists("test.test_e.C.test_x", SOURCES)  # a class under an `if`


def test_a_stale_deselected_or_trap_id_fails_the_rules() -> None:
    cfg = _cfg(
        deselected=[
            regrtest.Deselected("des", "g", ("test.test_b.Skips.test_gone",), "r", "README.md")
        ]
    )
    members = set(SOURCES) | {"Lib/test/test_c.py"}
    errors = regrtest.rule_errors(cfg, _gaps(cfg), members=members, sources=SOURCES)
    assert any("test_gone names no test" in e for e in errors), errors
    assert not any("test.test_a.T.test_deep" in e for e in errors), errors


def test_a_listed_module_the_tarball_lacks_fails_the_rules() -> None:
    errors = regrtest.rule_errors(_cfg(), _gaps(_cfg()), members=set(SOURCES))
    assert any("test_c names no test module" in e for e in errors), errors


def test_the_judges_own_cpython_files_load_and_pass_the_rules_without_the_tarball() -> None:
    assert PY.runner == "regrtest" and set(PY.groups) == {
        "cpython-fs",
        "cpython-archives",
        "cpython-a",
        "cpython-b",
        "cpython-c",
    }
    assert sum(len(g.modules) for g in PY.groups.values()) == 542
    # nine, one the dry run found (F5), less the four spec 071 closed, plus its two (Decision 8)
    assert len(PY.traps) == 8 and len(PY.expected) == 25
    from harness import plugin, shards

    gaps, _ = plugin.load_gaps(paths.KNOWN_GAPS)
    assert regrtest.rule_errors(PY, set(gaps), systems_of=shards.group_systems()) == []


def test_each_family_has_its_own_cap_budget() -> None:
    assert upstream.caps({"python": PY}) <= regrtest.CAP_BUDGET
    big = replace(PY, groups={**PY.groups, "x": upstream.Group("x", (), 10**12, ("test_x",), "x")})
    errors = upstream.rule_errors({"numpy": CONFIGS["numpy"], "python": big}, set())
    assert any("/cpython family's fuel caps" in e for e in errors), errors
    assert not any("/upstream family's fuel caps" in e for e in errors), errors


# ---------------------------------------------------------------------------------------------
# The stage and the grant (criteria 9 and 10)


def _tarball(path: Path, files: dict[str, bytes]) -> Path:
    with tarfile.open(path, "w:xz") as t:
        for name, data in files.items():
            info = tarfile.TarInfo(f"Python-3.15.0/{name}")
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))
    return path


def test_the_stage_is_the_tarballs_bytes_and_lists_what_the_tree_adds(work) -> None:
    tar = _tarball(
        work / "Python-3.15.0.tar.xz", {"Lib/test/test_a.py": b"good\n", "Lib/os.py": b"x"}
    )
    tree = work / "Python-3.15.0"
    (tree / "Lib/test/__pycache__").mkdir(parents=True)
    (tree / "Lib/test/test_a.py").write_bytes(b"changed by a build\n")
    (tree / "Lib/test/__pycache__/x.pyc").write_bytes(b"")
    dest = work / "stage"
    left = regrtest.stage(tar, tree, dest)
    assert (dest / "lib/test/test_a.py").read_bytes() == b"good\n"
    assert not (dest / "lib/os.py").exists()
    assert left == ["Lib/test/__pycache__/x.pyc"]


def test_stand_in_a_stage_copied_from_the_tree_carries_its_bytes(work) -> None:
    """Criterion 10's stand-in: copying from the build's tree would stage what the build left."""
    tree = work / "Python-3.15.0"
    (tree / "Lib/test").mkdir(parents=True)
    (tree / "Lib/test/test_a.py").write_bytes(b"changed by a build\n")
    tar = _tarball(work / "Python-3.15.0.tar.xz", {"Lib/test/test_a.py": b"good\n"})
    regrtest.stage(tar, tree, work / "real")
    copied = work / "copied/lib/test"
    copied.mkdir(parents=True)
    (copied / "test_a.py").write_bytes((tree / "Lib/test/test_a.py").read_bytes())
    assert (work / "real/lib/test/test_a.py").read_bytes() != (copied / "test_a.py").read_bytes()


def test_a_cpython_group_gets_its_own_grant_alone(work) -> None:
    assert regrtest.preopens(work) == [("/cpython", work, False)]
    assert upstream.preopens(work) == [("/upstream", work, False)]


def test_the_upstream_stage_does_not_hold_cpython(work, monkeypatch) -> None:
    """numpy's and pandas' fuel depends on their whole grant: the /upstream session never stages
    a regrtest package (criterion 9)."""
    s = upstream.Session(work, CONFIGS)
    seen = []
    monkeypatch.setattr(upstream.Session, "_prepare", lambda self, p: seen.append(p) or [])
    from harness import pins

    monkeypatch.setattr(pins, "source_pair", lambda p, *a, **k: (Path("x"), Path("y")))
    s.prepare("numpy")
    assert seen == ["numpy", "pandas"]


def test_the_tie_names_the_cpython_tarball_and_its_patch_folder(work) -> None:
    tar = _tarball(work / "Python-3.15.0.tar.xz", {"Lib/test/test_a.py": b"x"})
    sha = paths.sha256_file(tar)
    good = paths.Manifest(python="3.15.0", pins={"Python-3.15.0.tar.xz": sha}, recipes={})
    assert upstream.tie_errors("python", good, tar, {}) == []
    other = paths.Manifest(python="3.15.0", pins={"Python-3.15.0.tar.xz": "0" * 64}, recipes={})
    errors = upstream.tie_errors("python", other, tar, {})
    assert errors and "Python-3.15.0.tar.xz" in errors[0]
    assert upstream.tree_top(tar) == "Python-3.15.0"


# ---------------------------------------------------------------------------------------------
# The driver's source (Decision 4, C1's hazard)


def test_the_driver_wraps_single_clear_caches_and_never_imports_ctypes() -> None:
    assert "single.clear_caches = _clear_caches" in DRIVER
    assert not re.search(r"^\s*(import ctypes|from ctypes)", DRIVER, re.M)


def test_the_driver_wraps_print_warning_with_its_orig_stderr() -> None:
    assert "support.print_warning = _print_warning" in DRIVER
    assert "_print_warning.orig_stderr = _original_print_warning.orig_stderr" in DRIVER


def test_the_print_warning_wrapper_keeps_what_the_original_reads() -> None:
    """Run the driver's wrapper against a stand-in support module: the original reads
    `print_warning.orig_stderr` off its own global name, which is the wrapper once installed."""
    src = DRIVER[DRIVER.index("_warnings_now: list") : DRIVER.index("# ---- A1")]
    stream = io.StringIO()
    support_ns: dict = {}
    exec(
        "def print_warning(msg):\n"
        "    stream = print_warning.orig_stderr\n"
        "    for line in msg.splitlines():\n"
        "        print(f'Warning -- {line}', file=stream)\n",
        support_ns,
    )
    support_ns["print_warning"].orig_stderr = stream
    support = type("S", (), {})()
    support.print_warning = support_ns["print_warning"]
    ns = {"support": support, "first_line": lambda t: str(t).splitlines()[0]}
    exec(src, ns)
    support_ns["print_warning"] = support.print_warning  # the global name now names the wrapper
    support.print_warning("sys.path was modified by test_b\n  Before: a")
    assert ns["_warnings_now"] == ["sys.path was modified by test_b"]
    assert stream.getvalue().startswith("Warning -- sys.path was modified by test_b")


# ---------------------------------------------------------------------------------------------
# "No trap" asks to be seen (C4)


def test_the_scoreboard_names_open_entries_with_no_trap_here() -> None:
    from harness import scoreboard

    node = "tests/checks/test_v1_3_upstream_suites.py::test_upstream_trap[{}]"
    checks = {
        node.format("a"): {"status": "gap", "facts": {"trap": "no trap on this host"}},
        node.format("b"): {"status": "gap", "facts": {"trap": "trap at or after x"}},
    }
    assert scoreboard.no_trap_here(checks) == ["a"]


def test_the_gather_names_entries_with_no_trap_on_any_system() -> None:
    from harness import gather

    node = "tests/checks/test_v1_3_upstream_suites.py::test_upstream_trap[{}]"

    def rec(**traps):
        return {
            "checks": {
                node.format(k): {"status": "gap", "facts": {"trap": v}} for k, v in traps.items()
            }
        }

    records = {
        ("linux", "s"): rec(a="no trap on this host", b="no trap on this host"),
        ("darwin", "s"): rec(a="no trap on this host", b="trap at or after x"),
    }
    assert gather.no_trap_anywhere(records) == ["a"]


def test_the_stated_clock_resolutions_are_the_ones_darwin_answered() -> None:
    """Realtime and monotonic at the step, the CPU-time clocks at a nanosecond (though every clock
    steps 1 µs): the values a darwin host answered before the judge stated them, so no accepted
    darwin result moved (spec 065; spec 002's dated line)."""
    from harness import guest

    assert guest.CLOCK_RESOLUTION_NS == {0: guest.CLOCK_STEP_NS, 1: guest.CLOCK_STEP_NS, 2: 1, 3: 1}
