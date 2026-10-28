"""The plugin end to end (criterion 5): a small inner pytest session per case, through pytester,
with its own progress directory and gaps file, so nothing here touches the real ratchet."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from harness import history, paths, plugin

INNER = """
import pytest
from harness import needs

pytestmark = pytest.mark.goal("rules")

def test_ok(metric):
    metric("fuel", {fuel})
    metric("bytes", {size})

def unmet(monkeypatch):
    # "runner" made unmet for this case, so it holds whatever this repository provides.
    monkeypatch.setitem(needs.VOCABULARY, "runner", needs.Need("runner", lambda: False, "-"))

def test_blocked(monkeypatch):
    unmet(monkeypatch)
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
    text = (inner.progress / "history.jsonl").read_text()
    accepted_text = (inner.progress / "accepted.json").read_text()
    assert history.errors(history.found_in(inner.progress), accepted_text, None) == []
    assert [json.loads(x)["n"] for x in text.splitlines()] == [1, 2]


def test_a_lost_pass_is_red_and_cannot_be_accepted(inner) -> None:
    _accept_baseline(inner)
    result, _ = inner("--accept", "try", gaps_text=GAP.format(match="the named failure"))
    assert result.ret == 1
    result.stdout.fnmatch_lines(["*LOST test_inner.py::test_failing*", "*--accept refused*"])


def test_a_blocked_pass_is_red_unless_partial(inner, monkeypatch) -> None:
    _accept_baseline(inner)
    source = INNER.format(fuel=1_000_000, size=100, fail=False).replace(
        "def test_ok(metric):",
        "def test_ok(metric, monkeypatch):\n    unmet(monkeypatch)\n    needs.need('runner')",
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


def test_a_local_run_replaces_fuel_another_system_measured(inner) -> None:
    """A fuel the accepted entry says another system measured is not compared with this run's,
    and this system's own measurement replaces it at the next acceptance, label and all."""
    _accept_baseline(inner)
    f = inner.progress / "accepted.json"
    state = json.loads(f.read_text())
    (entry,) = state["checks"]["test_inner.py::test_ok"]["metrics"].values()
    entry["fuel_platform"] = "elsewhere-x"
    f.write_text(json.dumps(state, sort_keys=True, indent=1) + "\n")
    result, _ = inner(fuel=5_000_000, fail=False)
    assert result.ret == 0, result.stdout.str()
    result.stdout.fnmatch_lines(["*fuel not compared (measured on another system)*"])
    result, _ = inner("--accept", "x", fuel=5_000_000, fail=False)
    assert result.ret == 0, result.stdout.str()
    (entry,) = accepted_file(inner.progress)["checks"]["test_inner.py::test_ok"]["metrics"].values()
    assert entry["fuel"] == 5_000_000 and "fuel_platform" not in entry


def _judge_with(monkeypatch, name: str) -> None:
    real = plugin.run_meta

    def new_judge():
        meta = real()
        files = dict(meta["judge"]["files"], **{name: "abc"})
        meta["judge"] = {"hash": paths.judge_hash(files), "files": files}
        return meta

    monkeypatch.setattr(plugin, "run_meta", new_judge)


def test_a_changed_verdict_bearing_file_needs_accept_judge(inner, monkeypatch) -> None:
    _accept_baseline(inner)
    _judge_with(monkeypatch, "tests/upstream/new.toml")
    result, _ = inner(fail=False)
    assert result.ret == 0
    result.stdout.fnmatch_lines(["*judge changed: tests/upstream/new.toml*"])
    result, _ = inner("--accept", "allowance edit", fail=False)
    assert result.ret == 1
    result, _ = inner("--accept", "allowance edit", "--accept-judge", "a new family", fail=False)
    assert result.ret == 0


def test_another_judge_change_is_accepted_without_accept_judge(inner, monkeypatch) -> None:
    _accept_baseline(inner)
    _judge_with(monkeypatch, "tests/harness/new.py")
    result, _ = inner("--accept", "harness edit", "--accept-judge", "a new module", fail=False)
    assert result.ret == 1
    result.stdout.fnmatch_lines(["*--accept-judge is unnecessary*"])
    result, _ = inner("--accept", "harness edit", fail=False)
    assert result.ret == 0
    line = json.loads(history.lines(inner.progress)[-1])
    assert "tests/harness/new.py" in line["judge_changed"] and line["judge_reason"] is None


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


# Attacks on the plugin, each kept.

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

    # A platform no host is, so the case holds on every system (the release's first Linux run: on a
    # Linux host "linux-x86_64" was the baseline's own platform, not another).
    other = "plan9-amd64"

    def elsewhere():
        meta = real()
        meta["platform"] = other
        return meta

    monkeypatch.setattr(plugin, "run_meta", elsewhere)
    result, _ = inner("--accept", "on another platform", fuel=5_000_000, fail=False)
    assert result.ret == 0  # another platform's fuel is its own baseline
    metrics = accepted_file(inner.progress)["checks"]["test_inner.py::test_ok"]["metrics"]
    assert metrics[other]["fuel"] == 5_000_000
    assert next(v for k, v in metrics.items() if k != other)["fuel"] == 1_000_000
    result, _ = inner("-k", "test_ok", "--accept", "partial run", fail=False)
    assert result.ret == 0
    assert "test_inner.py::test_failing" in accepted_file(inner.progress)["checks"]


def test_overridden_judge_inputs_are_announced(inner) -> None:
    result, _ = inner(fail=False)
    result.stdout.fnmatch_lines(["*JUDGE INPUTS OVERRIDDEN: --progress-dir*"])


PASSES = """
import pytest

pytestmark = pytest.mark.goal("v1.3")

def test_group(metric, fact):
    metric("fuel", 10)
    metric("passes", {passes})
    fact("passed_digest", "abc")
    with pytest.raises(ValueError):
        metric("speed", 1)
"""


def test_passes_ratchet_end_to_end_with_its_own_flag(inner) -> None:
    """`metric("passes")` is allowed, a fall is FEWER and red, and only
    --accept-fewer-passes accepts it; the fact reaches latest.json."""
    result, record = inner("--accept", "base", source=PASSES.format(passes=5))
    assert result.ret == 0, result.stdout.str()
    assert record["checks"]["test_inner.py::test_group"]["facts"] == {"passed_digest": "abc"}
    result, _ = inner("--accept", "try", "--accept-growth", "x", source=PASSES.format(passes=4))
    assert result.ret == 1
    result.stdout.fnmatch_lines(
        ["*FEWER test_inner.py::test_group: passes 5 -> 4*", "*--accept-fewer-passes*"]
    )
    result, _ = inner(
        "--accept",
        "fell",
        "--accept-fewer-passes",
        "upstream moved one",
        source=PASSES.format(passes=4),
    )
    assert result.ret == 0, result.stdout.str()
    entry = accepted_file(inner.progress)["checks"]["test_inner.py::test_group"]
    assert next(iter(entry["metrics"].values()))["passes"] == 4
    last = (inner.progress / "history.jsonl").read_text().splitlines()[-1]
    assert json.loads(last)["fewer_reason"] == "upstream moved one"


# ---------------------------------------------------------------------------------------------
# The plugin writes the line where history.target says, and says so (criteria 7, 8)


def _filler_volume(progress: Path, lines: int, passed=()) -> bytes:
    """An old-format history.jsonl over the volume budget; each line carries `passed`, so the
    history replays. The plugin does not check the chain, so the fillers need none."""
    text = "".join(
        json.dumps({"n": n, "passed": sorted(passed), "reason": "x" * 9_000}, sort_keys=True) + "\n"
        for n in range(1, lines + 1)
    )
    (progress / "history.jsonl").write_text(text)
    data = (progress / "history.jsonl").read_bytes()
    assert len(data) > history.BUDGET
    return data


def test_accept_starts_a_volume_when_the_newest_is_full_and_says_where(inner) -> None:
    before = _filler_volume(inner.progress, 60)
    result, _ = inner("--accept", "into a new volume", fail=False)
    assert result.ret == 0, result.stdout.str()
    volume = inner.progress / "history-00061.jsonl"
    result.stdout.fnmatch_lines([f"*accepted: {volume} line 61*"])
    assert (inner.progress / "history.jsonl").read_bytes() == before
    result, _ = inner("--accept", "into the same volume", fail=False)
    assert result.ret == 0, result.stdout.str()
    result.stdout.fnmatch_lines([f"*accepted: {volume} line 62*"])
    assert [json.loads(x)["n"] for x in volume.read_text().splitlines()] == [61, 62]
    assert [p.name for p in history.volumes(inner.progress)] == ["history.jsonl", volume.name]
    assert b"\r" not in volume.read_bytes()


def test_an_oversize_line_is_refused_through_the_plugin(inner) -> None:
    gone = [f"tests/checks/test_gone.py::test_number[{i:060d}]" for i in range(7_000)]
    before = _filler_volume(inner.progress, 1, passed=gone)
    result, _ = inner("--accept", "too big", fail=False)
    assert result.ret == 1
    result.stdout.fnmatch_lines(["*--accept refused: the history line would be*bytes, over*"])
    assert (inner.progress / "history.jsonl").read_bytes() == before
    assert sorted(p.name for p in inner.progress.iterdir()) == ["history.jsonl"]


# ---------------------------------------------------------------------------------------------
# --shard, a named selection of the judge's own checks (acceptance 3)

SHARD_PLAN = """
[shard.a]
files = ["test_inner.py"]
systems = ["macos", "linux", "windows"]

[shard.rest]
rest = true
systems = ["macos", "linux", "windows"]

[shard.empty]
files = ["test_absent.py"]
systems = ["macos", "linux", "windows"]
"""
UNITS = "def test_u1():\n    pass\n\ndef test_u2():\n    pass\n"


@pytest.fixture
def sharded(inner, pytester: pytest.Pytester):
    plan = pytester.path / "plan.toml"
    plan.write_text(SHARD_PLAN)
    pytester.makepyfile(test_units=UNITS)

    def run(*args, **kw):
        return inner("--shard-plan", str(plan), *args, **kw)

    return run


def test_a_shard_runs_exactly_its_items_and_deselects_the_rest(sharded) -> None:
    from harness import shards

    result, record = sharded("--shard", "rest", fail=False)
    assert result.ret == 0, result.stdout.str()
    checks = record["checks"]
    assert {n for n, c in checks.items() if c["status"] != "deselected"} == set()
    assert (
        set(record["deselected"])
        == set(checks)
        == {
            "test_inner.py::test_ok",
            "test_inner.py::test_blocked",
            "test_inner.py::test_failing",
        }
    )
    units = ["test_units.py::test_u1", "test_units.py::test_u2"]
    assert record["meta"]["shard"] == "rest"
    assert record["meta"]["units"] == {"count": 2, "digest": shards.units_digest(units)}
    assert record["suite"]["total"] == 2
    result, record = sharded("--shard", "a", fail=False)
    ran = {n for n, c in record["checks"].items() if c["status"] != "deselected"}
    assert ran == set(record["checks"]) and record["deselected"] == []
    assert record["meta"]["units"] == {"count": 0, "digest": shards.units_digest([])}
    assert record["suite"]["total"] == 0


def test_a_shard_that_selects_nothing_is_red(sharded) -> None:
    result, record = sharded("--shard", "empty", fail=False)
    assert result.ret != 0
    result.stdout.fnmatch_lines(["*RED:*shard empty selected nothing*"])
    assert record["meta"]["shard"] == "empty"


@pytest.mark.parametrize(
    ("args", "why"),
    [
        (("--shard", "nope"), "the plan holds no such shard"),
        (("--shard", "a", "--accept", "x"), "with --accept or --retire"),
        (("--shard", "a", "--retire", "test_inner.py::test_ok"), "with --accept or --retire"),
        (("--shard", "a", "test_inner.py::test_ok"), "with a node id"),
        (("--shard", "a", "-n", "2"), "with -n"),
        (("--shard", "a", "--tier", "release"), "with --tier"),
    ],
)
def test_shard_refusals_come_before_collection(sharded, args, why) -> None:
    result, record = sharded(*args, fail=False)
    assert result.ret != 0
    assert why in result.stdout.str() + result.stderr.str()
    assert record is None  # nothing ran, nothing was written


def test_without_shard_the_record_says_none(sharded) -> None:
    result, record = sharded(fail=False)
    assert record["meta"]["shard"] is None
    assert "units" not in record["meta"]
    assert record["deselected"] == []


def test_run_meta_records_the_sets_own_sha256sums(tmp_path, monkeypatch) -> None:
    """The run names the whole artifact set by its SHA256SUMS."""
    (tmp_path / "python.wasm").write_bytes(b"\0asm")
    monkeypatch.setenv(paths.ARTIFACTS_ENV, str(tmp_path))
    assert plugin.run_meta()["set_sums"] is None
    (tmp_path / "SHA256SUMS").write_text("x  python.wasm\n")
    assert plugin.run_meta()["set_sums"] == paths.sha256_file(tmp_path / "SHA256SUMS")


# ---------------------------------------------------------------------------------------------
# The two tiers: the normal tier leaves every release-tier check unrun

OK = "test_inner.py::test_ok"


@pytest.fixture
def tiers(inner, monkeypatch):
    """The inner file's test_ok made a release-tier check."""
    monkeypatch.setattr(plugin, "release_checks", lambda: [OK])
    return inner


def test_the_normal_tier_deselects_every_release_tier_check(tiers) -> None:
    result, record = tiers(fail=False)
    assert result.ret == 0, result.stdout.str()
    assert record["meta"]["tier"] == "normal" and record["release_checks"] == [OK]
    assert record["checks"][OK]["status"] == "deselected" and OK in record["deselected"]
    assert record["checks"][OK]["reason"] == "release tier"
    result, record = tiers(OK, fail=False)  # by node id too
    assert record["checks"][OK]["status"] == "deselected"


def test_the_release_tier_runs_both_tiers(tiers) -> None:
    result, record = tiers("--tier", "release", fail=False)
    assert result.ret == 0, result.stdout.str()
    assert record["meta"]["tier"] == "release" and record["release_checks"] == [OK]
    assert record["checks"][OK]["status"] == "pass"
    assert status(record, "test_blocked") == "blocked"


def test_a_check_that_moves_tiers_needs_its_own_flag(inner, monkeypatch) -> None:
    _accept_baseline(inner)
    monkeypatch.setattr(plugin, "release_checks", lambda: [OK])
    result, _ = inner("--accept", "again", fail=False)
    assert result.ret == 1
    result.stdout.fnmatch_lines(["*MOVED test_inner.py::test_ok*", "*--accept-tier-move*"])
    result, _ = inner("--accept", "again", "--accept-tier-move", "it is slow", fail=False)
    assert result.ret == 0, result.stdout.str()
    entry = accepted_file(inner.progress)["checks"][OK]
    assert entry["tier"] == "release" and entry["status"] == "pass"
    line = json.loads((inner.progress / "history.jsonl").read_text().splitlines()[-1])
    assert line["tier_move_reason"] == "it is slow" and OK not in line["passed_removed"]
    result, _ = inner(fail=False)
    assert result.ret == 0, result.stdout.str()
    result.stdout.fnmatch_lines(["*release tier not run 1*"])


def test_the_judge_reads_the_release_checks_from_the_upstream_files() -> None:
    from harness import upstream

    assert plugin.release_checks() == sorted(upstream.release_checks(upstream.load_all()))


RETIRING = """# 999: a check goes

## Changelog

### Changed

- **A check goes**: it is retired.

## Claims

```toml
[[claim]]
spec = "999"
retired = ["test_inner.py::test_failing"]
```
"""


def test_an_absent_check_a_news_file_retires_is_listed_and_the_run_green(inner, pytester) -> None:
    """A shard's run and the quick job's rules step read the news files at their commit: an
    absent check one retires is listed with its reason, and the run stays green; the acceptance
    still retires it only from the claim or --retire."""
    _accept_baseline(inner)
    full = INNER.format(fuel=1_000_000, size=100, fail=False)
    source = full[: full.index("def test_failing")]
    changes = pytester.path / "context" / "changes"
    changes.mkdir(parents=True)
    (changes / "999-a-check-goes.md").write_text(RETIRING)
    result, _ = inner(source=source)
    assert result.ret == 0, result.stdout.str()[-2000:]
    result.stdout.fnmatch_lines(["*RETIRED test_inner.py::test_failing · 999: retired*"])
    result, _ = inner("--accept", "drop it", source=source)
    assert result.ret == 1  # a local acceptance still says --retire
    result.stdout.fnmatch_lines(["*absent checks not retired*"])


GROWING = """# 999: a check grows

## Changelog

### Changed

- **A check grows**: it does more.

## Claims

```toml
[[claim]]
spec = "999"
grows = ["test_inner.py::test_ok"]
growth = "it does more"
```
"""


def test_a_growth_a_news_file_claims_is_listed_and_the_run_green(inner, pytester) -> None:
    """A shard's run reads the news files at its commit: a growth one claims is listed with its
    reason and the run stays green, so the gather runs and the accept job can consume the claim;
    a local acceptance still needs --accept-growth."""
    _accept_baseline(inner)
    changes = pytester.path / "context" / "changes"
    changes.mkdir(parents=True)
    (changes / "999-a-check-grows.md").write_text(GROWING)
    result, _ = inner(fuel=1_000_101, fail=False)
    assert result.ret == 0, result.stdout.str()[-2000:]
    result.stdout.fnmatch_lines(["*CLAIMED test_inner.py::test_ok: fuel 1000000 -> 1000101*"])
    result, _ = inner("--accept", "more", fuel=1_000_101, fail=False)
    assert result.ret == 1
