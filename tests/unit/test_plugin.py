"""The plugin end to end (criterion 5): a small inner pytest session per case, through pytester,
with its own progress directory and gaps file, so nothing here touches the real ratchet."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from harness import paths, plugin, scoreboard

INNER = """
import pytest
from harness import needs

pytestmark = pytest.mark.goal("rules")

def test_ok(metric):
    metric("fuel", {fuel})
    metric("bytes", {size})

def test_blocked():
    needs.need("runner")

def test_failing():
    assert not {fail}, "the named failure"
"""


@pytest.fixture
def inner(pytester: pytest.Pytester):
    progress = pytester.path / "progress"
    progress.mkdir()
    latest = pytester.path / "latest.json"
    gaps = pytester.path / "gaps.toml"

    def run(*args, fuel=1_000_000, size=100, fail=True, source=None, gaps_text=""):
        # Same size, same second: Python would reuse the old bytecode, so drop it first.
        shutil.rmtree(pytester.path / "__pycache__", ignore_errors=True)
        pytester.makepyfile(test_inner=source or INNER.format(fuel=fuel, size=size, fail=fail))
        gaps.write_text(gaps_text)
        result = pytester.runpytest(
            "-p",
            "harness.plugin",
            "--progress-dir",
            str(progress),
            "--progress-latest",
            str(latest),
            "--known-gaps",
            str(gaps),
            *args,
        )
        record = json.loads(latest.read_text()) if latest.is_file() else None
        return result, record

    run.progress = progress
    return run


def status(record, name):
    return record["checks"][f"test_inner.py::{name}"]["status"]


def accepted_file(progress: Path) -> dict:
    return json.loads((progress / "accepted.json").read_text())


def test_states_pass_blocked_and_fail(inner) -> None:
    result, record = inner()
    assert result.ret == 1
    assert [status(record, n) for n in ("test_ok", "test_blocked", "test_failing")] == [
        "pass",
        "blocked",
        "fail",
    ]
    assert record["checks"]["test_inner.py::test_ok"]["metrics"] == {
        "fuel": 1_000_000,
        "bytes": 100,
    }
    result.stdout.fnmatch_lines(["*wasi_python v1: 1/3 pass*", "*blocked by: runner 1*"])


def test_unnamed_skip_and_a_skip_naming_a_met_need_are_failures(inner) -> None:
    source = (
        "import pytest\n"
        "pytestmark = pytest.mark.goal('rules')\n"
        "def test_unnamed():\n    pytest.skip('not today')\n"
        "def test_met_need():\n    pytest.skip('needs: git')\n"
    )
    result, record = inner(source=source)
    assert result.ret == 1
    assert status(record, "test_unnamed") == status(record, "test_met_need") == "fail"


def test_an_error_in_setup_is_a_failure(inner) -> None:
    source = (
        "import pytest\n"
        "pytestmark = pytest.mark.goal('rules')\n"
        "@pytest.fixture\ndef broken():\n    raise RuntimeError('setup broke')\n"
        "def test_x(broken):\n    pass\n"
    )
    result, record = inner(source=source)
    assert result.ret == 1 and status(record, "test_x") == "fail"


GAP = (
    '[[gap]]\ncheck = "test_inner.py::test_failing"\nmatch = "{match}"\n'
    'reason = "known"\ncloses_with = "README.md"\n'
)


def test_a_gap_that_fails_as_named_is_a_gap(inner) -> None:
    result, record = inner("-k", "not blocked", gaps_text=GAP.format(match="the named failure"))
    assert result.ret == 0 and status(record, "test_failing") == "gap"


def test_a_gap_that_fails_differently_is_a_failure(inner) -> None:
    result, record = inner(gaps_text=GAP.format(match="another failure"))
    assert result.ret == 1 and status(record, "test_failing") == "fail"
    assert (
        "fails differently from its gap"
        in record["checks"]["test_inner.py::test_failing"]["reason"]
    )


def test_a_gap_that_passes_is_a_failure(inner) -> None:
    result, record = inner(fail=False, gaps_text=GAP.format(match="the named failure"))
    assert result.ret == 1 and status(record, "test_failing") == "fail"


def _accept_baseline(inner, **kw):
    result, _ = inner("--accept", "baseline", fail=False, **kw)
    assert result.ret == 0, result.stdout.str()
    return accepted_file(inner.progress)


def test_accept_writes_the_baseline_and_a_chained_history(inner) -> None:
    base = _accept_baseline(inner)
    assert base["checks"]["test_inner.py::test_ok"]["status"] == "pass"
    _accept_baseline(inner)
    history = (inner.progress / "history.jsonl").read_text()
    accepted_text = (inner.progress / "accepted.json").read_text()
    assert scoreboard.history_errors(history, accepted_text, None) == []
    assert [json.loads(x)["n"] for x in history.splitlines()] == [1, 2]


def test_a_lost_pass_is_red_and_cannot_be_accepted(inner) -> None:
    _accept_baseline(inner)
    result, _ = inner("--accept", "try", gaps_text=GAP.format(match="the named failure"))
    assert result.ret == 1
    result.stdout.fnmatch_lines(["*LOST test_inner.py::test_failing*", "*--accept refused*"])


def test_a_blocked_pass_is_red_unless_partial(inner, monkeypatch) -> None:
    _accept_baseline(inner)
    source = INNER.format(fuel=1_000_000, size=100, fail=False).replace(
        "def test_ok(metric):", "def test_ok(metric):\n    needs.need('runner')"
    )
    result, _ = inner(source=source)
    assert result.ret == 1
    result.stdout.fnmatch_lines(["*unrun 1*"])
    result, _ = inner("--partial", "no runner here", source=source)
    assert result.ret == 0


def test_deselected_and_path_limited_runs_are_not_red(inner, pytester) -> None:
    _accept_baseline(inner)
    result, record = inner("-k", "not test_ok", fail=False)
    assert result.ret == 0 and status(record, "test_ok") == "deselected"
    pytester.makepyfile(test_other="def test_unit():\n    pass\n")
    result = pytester.runpytest(
        "-p",
        "harness.plugin",
        "--progress-dir",
        str(inner.progress),
        "--progress-latest",
        str(pytester.path / "latest2.json"),
        "test_other.py",
    )
    assert result.ret == 0


def test_an_absent_check_is_red_until_retired(inner) -> None:
    _accept_baseline(inner)
    full = INNER.format(fuel=1_000_000, size=100, fail=False)
    source = full[: full.index("def test_failing")]
    result, _ = inner(source=source)
    assert result.ret == 1
    result.stdout.fnmatch_lines(["*ABSENT test_inner.py::test_failing*"])
    result, _ = inner(
        "--accept", "drop it", "--retire", "test_inner.py::test_failing", source=source
    )
    assert result.ret == 0
    assert "test_inner.py::test_failing" not in accepted_file(inner.progress)["checks"]


def test_fuel_over_the_tolerance_is_red_and_under_it_is_not(inner) -> None:
    _accept_baseline(inner)
    result, _ = inner(fuel=1_000_100, fail=False)
    assert result.ret == 0
    result, _ = inner(fuel=1_000_101, fail=False)
    assert result.ret == 1
    result.stdout.fnmatch_lines(["*GREW test_inner.py::test_ok: fuel 1000000 -> 1000101*"])
    result, _ = inner("--accept", "more", fuel=1_000_101, fail=False)
    assert result.ret == 1
    result, _ = inner(
        "--accept", "more", "--accept-growth", "a bigger probe", fuel=1_000_101, fail=False
    )
    assert result.ret == 0


def test_bytes_growth_is_red(inner) -> None:
    _accept_baseline(inner)
    result, _ = inner(size=101, fail=False)
    assert result.ret == 1


def test_accept_keeps_the_minimum_metric(inner) -> None:
    _accept_baseline(inner)
    inner("--accept", "lower", fuel=900_000, fail=False)
    inner("--accept", "back up a little", fuel=900_050, fail=False)
    metrics = accepted_file(inner.progress)["checks"]["test_inner.py::test_ok"]["metrics"]
    assert next(iter(metrics.values()))["fuel"] == 900_000


def test_fuel_on_another_wasmtime_is_not_compared(inner, monkeypatch) -> None:
    _accept_baseline(inner)
    real = plugin.run_meta

    def other_engine():
        meta = real()
        meta["wasmtime"] = "50.0.0"
        return meta

    monkeypatch.setattr(plugin, "run_meta", other_engine)
    result, _ = inner(fuel=5_000_000, fail=False)
    assert result.ret == 0
    result.stdout.fnmatch_lines(["*fuel not compared*"])


def test_a_changed_judge_needs_accept_judge(inner, monkeypatch) -> None:
    _accept_baseline(inner)
    real = plugin.run_meta

    def new_judge():
        meta = real()
        files = dict(meta["judge"]["files"], **{"tests/harness/new.py": "abc"})
        meta["judge"] = {"hash": paths.judge_hash(files), "files": files}
        return meta

    monkeypatch.setattr(plugin, "run_meta", new_judge)
    result, _ = inner(fail=False)
    assert result.ret == 0
    result.stdout.fnmatch_lines(["*judge changed: tests/harness/new.py*"])
    result, _ = inner("--accept", "harness edit", fail=False)
    assert result.ret == 1
    result, _ = inner("--accept", "harness edit", "--accept-judge", "a new module", fail=False)
    assert result.ret == 0


def test_a_run_stopped_early_reports_unrun_checks(inner) -> None:
    source = (
        "import pytest\n"
        "pytestmark = pytest.mark.goal('rules')\n"
        "def test_first():\n    assert False\n"
        "def test_second():\n    pass\n"
    )
    result, record = inner("-x", source=source)
    assert result.ret == 1
    assert status(record, "test_first") == "fail"
    assert status(record, "test_second") == "unrun"


# The build review's attacks (context/reviews/002-the-progress-harness-2026-10-16.md), each kept.

SCANNER = """
import pytest
from harness import scan

pytestmark = pytest.mark.goal("rules")

def test_scanner():
    findings = {findings!r}
    assert not findings, scan.report(findings)
"""


def _digest_gap(findings: list[str]) -> str:
    from harness import scan

    m = f"{len(findings)} finding(s), digest {scan.digest(findings)}"
    return (
        f'[[gap]]\ncheck = "test_inner.py::test_scanner"\nmatch = "{m}"\n'
        'reason = "known"\ncloses_with = "README.md"\n'
    )


def test_a_gap_admits_exactly_its_findings_and_no_new_one(inner) -> None:
    known = ["a.c:1", "b.c:2"]
    result, record = inner(source=SCANNER.format(findings=known), gaps_text=_digest_gap(known))
    assert result.ret == 0 and status(record, "test_scanner") == "gap"
    more = [*known, "src/new.c:1"]
    result, record = inner(source=SCANNER.format(findings=more), gaps_text=_digest_gap(known))
    assert result.ret == 1 and status(record, "test_scanner") == "fail"
    fewer = known[:1]
    result, record = inner(source=SCANNER.format(findings=fewer), gaps_text=_digest_gap(known))
    assert result.ret == 1 and status(record, "test_scanner") == "fail"


@pytest.mark.parametrize("how", ["@pytest.mark.xfail(strict=True)\n", ""])
def test_an_xfail_without_a_gap_entry_is_a_failure(inner, how) -> None:
    body = "    assert False\n" if how else "    pytest.xfail('later')\n"
    source = f"import pytest\npytestmark = pytest.mark.goal('rules')\n{how}def test_x():\n{body}"
    result, record = inner(source=source)
    assert result.ret == 1 and status(record, "test_x") == "fail"


def test_removing_a_goal_marker_makes_its_accepted_passes_absent(inner) -> None:
    _accept_baseline(inner)
    unmarked = INNER.format(fuel=1_000_000, size=100, fail=False).replace(
        'pytestmark = pytest.mark.goal("rules")', ""
    )
    result, _ = inner(source=unmarked)
    assert result.ret == 1
    result.stdout.fnmatch_lines(["*ABSENT test_inner.py::*"])


def test_a_run_narrowed_to_one_node_id_is_not_absent_and_cannot_retire(inner) -> None:
    _accept_baseline(inner)
    result, _ = inner("test_inner.py::test_ok", fail=False)
    assert result.ret == 0
    result.stdout.fnmatch_lines(["*absent 0*not selected 1*"])
    result, _ = inner(
        "test_inner.py::test_ok", "--accept", "x", "--retire", "test_inner.py::test_failing"
    )
    assert result.ret == 1
    result.stdout.fnmatch_lines(["*--retire names checks that are not absent*"])


def test_a_pass_blocked_by_local_tooling_is_not_red(inner) -> None:
    _accept_baseline(inner)
    source = INNER.format(fuel=1_000_000, size=100, fail=False).replace(
        "def test_ok(metric):", "def test_ok(metric):\n    needs.need('oracle-missing-here')"
    )
    source = source.replace(
        "from harness import needs",
        "from harness import needs\n"
        "needs.VOCABULARY['oracle-missing-here'] = needs.Need("
        "'oracle-missing-here', lambda: False, 'x')",
    )
    result, _ = inner(source=source)
    assert result.ret == 0
    result.stdout.fnmatch_lines(["*unrun locally 1*"])


def test_accept_with_no_goal_checks_is_refused(inner, pytester) -> None:
    pytester.makepyfile(test_plain="def test_unit():\n    pass\n")
    result = pytester.runpytest(
        "-p",
        "harness.plugin",
        "--progress-dir",
        str(inner.progress),
        "test_plain.py",
        "--accept",
        "nothing",
    )
    assert result.ret == 1
    result.stdout.fnmatch_lines(["*collected no goal checks*"])


def test_a_metric_that_stops_being_recorded_is_red(inner) -> None:
    _accept_baseline(inner)
    source = INNER.format(fuel=1_000_000, size=100, fail=False).replace(
        '    metric("bytes", 100)\n', ""
    )
    result, _ = inner(source=source)
    assert result.ret == 1
    result.stdout.fnmatch_lines(["*GREW test_inner.py::test_ok: bytes is no longer recorded*"])


def test_gained_carry_over_and_another_platform_end_to_end(inner, monkeypatch) -> None:
    result, record = inner(fail=False)
    result.stdout.fnmatch_lines(["*gained 2*"])
    _accept_baseline(inner)
    real = plugin.run_meta

    def linux():
        meta = real()
        meta["platform"] = "linux-x86_64"
        return meta

    monkeypatch.setattr(plugin, "run_meta", linux)
    result, _ = inner("--accept", "on linux", fuel=5_000_000, fail=False)
    assert result.ret == 0  # another platform's fuel is its own baseline
    metrics = accepted_file(inner.progress)["checks"]["test_inner.py::test_ok"]["metrics"]
    assert metrics["linux-x86_64"]["fuel"] == 5_000_000
    assert next(v for k, v in metrics.items() if k != "linux-x86_64")["fuel"] == 1_000_000
    result, _ = inner("-k", "test_ok", "--accept", "partial run", fail=False)
    assert result.ret == 0
    assert "test_inner.py::test_failing" in accepted_file(inner.progress)["checks"]


def test_overridden_judge_inputs_are_announced(inner) -> None:
    result, _ = inner(fail=False)
    result.stdout.fnmatch_lines(["*JUDGE INPUTS OVERRIDDEN: --progress-dir*"])
