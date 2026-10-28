"""The fast tier's budget as pure functions: the fuel caps, the quick job's times, the list of
checks a specification will move."""

from __future__ import annotations

from pathlib import Path

from harness import budget

A = "tests/checks/test_v1_2_hostile_guest.py::test_a[plain]"
U = f"{budget.UPSTREAM_FILE}::test_upstream_suite[numpy-core]"
R = f"{budget.UPSTREAM_FILE}::test_upstream_suite[numpy-slow-a]"
FAMILIES = {U: "numpy", R: "numpy"}


def family(node: str) -> str:
    return budget.family_of(node, FAMILIES)


def entry(fuel: int | None = None, tier: str | None = None) -> dict:
    e: dict = {"status": "pass", "metrics": {}}
    if fuel is not None:
        e["metrics"]["darwin-arm64"] = {"wasmtime": "49.0.0", "fuel": fuel}
    if tier:
        e["tier"] = tier
    return e


def caps(**kw: int) -> dict[str, int]:
    return {"test_v1_2_hostile_guest": 100, "numpy": 1_000, **kw}


def test_a_family_is_the_file_or_the_upstream_package() -> None:
    assert family(A) == "test_v1_2_hostile_guest"
    assert family(U) == "numpy"
    assert family(f"{budget.UPSTREAM_FILE}::test_upstream_trap[x]") == "upstream"


def test_fuel_past_its_familys_cap_is_over_budget_and_at_it_is_not() -> None:
    at = {"checks": {A: entry(100), U: entry(1_000)}}
    assert budget.fuel_over(at, caps(), family) == []
    past = {"checks": {A: entry(101), U: entry(1_001)}}
    assert budget.fuel_over(past, caps(), family) == [
        f"{A}: fuel 101 is past its family test_v1_2_hostile_guest's cap 100",
        f"{U}: fuel 1,001 is past its family numpy's cap 1,000",
    ]


def test_a_release_tier_check_and_a_check_without_fuel_have_no_budget() -> None:
    accepted = {"checks": {R: entry(10**9, tier="release"), A: entry()}}
    assert budget.fuel_over(accepted, caps(), family) == []


def test_a_family_with_fuel_and_no_cap_is_a_finding_and_a_cap_for_none_is_stale() -> None:
    accepted = {"checks": {"tests/checks/test_v1_9_new.py::test_b": entry(5)}}
    assert budget.fuel_over(accepted, {}, family) == [
        "tests/checks/test_v1_9_new.py::test_b: records fuel, and its family test_v1_9_new has "
        "no cap in the budget"
    ]
    assert budget.stale_caps({"checks": {A: entry(1)}}, caps(), family) == [
        "the cap for numpy names no family with fuel"
    ]


def test_a_cap_for_a_new_check_file_waits_for_its_first_acceptance() -> None:
    """A check file no accepted check comes from is new: its family's cap is not stale before
    its first acceptance, and a file with accepted checks has no such allowance."""
    accepted = {"checks": {A: entry(1), U: entry(1)}}
    files = ["tests/checks/test_v1_2_hostile_guest.py", "tests/checks/test_v1_9_new.py"]
    assert budget.new_families(accepted, files) == {"test_v1_9_new"}
    with_new = caps(test_v1_9_new=10, test_v1_8_old=10)
    assert budget.stale_caps(accepted, with_new, family, {"test_v1_9_new"}) == [
        "the cap for test_v1_8_old names no family with fuel"
    ]


def _junit(*cases: tuple[str, str, float]) -> str:
    rows = "".join(f'<testcase classname="{c}" name="{n}" time="{t}"/>' for c, n, t in cases)
    return f'<testsuites><testsuite name="pytest">{rows}</testsuite></testsuites>'


def test_a_goal_check_past_the_seconds_in_quick_is_over_budget(tmp_path: Path) -> None:
    (tmp_path / "tests" / "checks").mkdir(parents=True)
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    (tmp_path / "tests" / "checks" / "test_rules.py").write_text("")
    (tmp_path / "tests" / "unit" / "test_x.py").write_text("")
    report = _junit(
        ("tests.checks.test_rules", "test_slow[case]", 61.25),
        ("tests.checks.test_rules", "test_quick", 60.0),
        ("tests.unit.test_x", "test_a_unit_test_is_no_goal_check", 500.0),
    )
    assert budget.time_over([report], 60, set(), tmp_path) == [
        "tests/checks/test_rules.py::test_slow[case]: 61.2 s in quick, past 60 s"
    ]
    release = {"tests/checks/test_rules.py::test_slow[case]"}
    assert budget.time_over([report], 60, release, tmp_path) == []


def test_a_listed_check_is_reported_with_its_specification_and_a_stale_entry_is_a_finding() -> None:
    line = f"{A}: fuel 101 is past its family test_v1_2_hostile_guest's cap 100"
    number = "150"  # a written specification's number, as `closes_with` gives it
    specs = {number: "drafted 2026-10-25"}
    unlisted = budget.Budget(60, caps(), ())
    bad, reported = budget.findings([line], unlisted, specs)
    assert len(bad) == 1 and "list it under [[over]]" in bad[0] and reported == []
    listed = budget.Budget(60, caps(), (budget.Over(A, number, "it grew with its guest"),))
    assert budget.findings([line], listed, specs) == (
        [],
        [f"{line}: specification {number} moves it"],
    )
    unwritten = budget.Budget(60, caps(), (budget.Over(A, "151", "no such"),))
    bad, _ = budget.findings([line], unwritten, specs)
    assert bad == [f"{line}: its [[over]] entry names '151', no specification"]
    assert budget.findings([], listed, specs) == ([f"[[over]] {A} is not over budget"], [])


def test_a_runs_own_fuel_past_its_cap_is_over_budget_and_a_release_check_is_not() -> None:
    checks = {
        A: {"status": "pass", "metrics": {"fuel": 101}},
        U: {"status": "pass", "metrics": {"fuel": 1_000}},
        R: {"status": "pass", "metrics": {"fuel": 10**9}},
        "tests/checks/test_v1_2_hostile_guest.py::test_b": {"status": "fail", "metrics": {}},
    }
    assert budget.run_fuel_over(checks, caps(), family, {R}) == [
        f"{A}: fuel 101 is past its family test_v1_2_hostile_guest's cap 100"
    ]


def test_a_run_of_some_shards_reports_no_entry_as_stale() -> None:
    """A pull request runs some shards: an [[over]] entry whose check did not run there is not
    stale there."""
    listed = budget.Budget(60, caps(), (budget.Over(A, "150", "it grew with its guest"),))
    assert budget.findings([], listed, {}, stale=False) == ([], [])


def test_a_time_past_the_seconds_is_a_warning_and_never_a_failure(tmp_path: Path) -> None:
    (tmp_path / "tests" / "checks").mkdir(parents=True)
    (tmp_path / "tests" / "checks" / "test_rules.py").write_text("")
    report = tmp_path / "rules.xml"
    report.write_text(_junit(("tests.checks.test_rules", "test_slow", 75.0)))
    summary = tmp_path / "summary.md"
    lines = budget.time_warnings([report], 60, set(), tmp_path, summary)
    assert lines == [
        "::warning title=fast-tier budget::tests/checks/test_rules.py::test_slow: 75.0 s in quick,"
        " past 60 s"
    ]
    assert "tests/checks/test_rules.py::test_slow: 75.0 s in quick" in summary.read_text()
    assert budget.time_warnings([tmp_path / "none.xml"], 60, set(), tmp_path, None) == [
        f"::warning title=fast-tier budget::no timing report at {tmp_path / 'none.xml'}"
    ]


def test_an_entry_needs_its_reason_and_a_specification_still_to_land(tmp_path: Path) -> None:
    line = f"{A}: fuel 101 is past its family test_v1_2_hostile_guest's cap 100"
    number = "150"
    unsaid = budget.Budget(60, caps(), (budget.Over(A, number, " "),))
    assert budget.findings([line], unsaid, {number: "drafted"})[0] == [
        f"{line}: its [[over]] entry gives no reason"
    ]
    listed = budget.Budget(60, caps(), (budget.Over(A, number, "it grew with its guest"),))
    for status in ("landed 2026-10-30", "**landed 2026-10-30**", "Superseded by 151"):
        assert budget.findings([line], listed, {number: status})[0] == [
            f"{line}: its [[over]] entry names {number!r}, which has landed and moves nothing now"
        ], status
    folder = tmp_path / "specifications"
    folder.mkdir()
    (folder / f"{number}-x.md").write_text("# x\n\n- **Status:** **landed 2026-10-30**, then\n")
    (folder / "README.md").write_text("no number\n")
    assert budget.spec_status(folder) == {number: "landed 2026-10-30, then"}
