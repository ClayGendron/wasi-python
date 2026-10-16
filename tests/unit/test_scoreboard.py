"""The ratchet and acceptance as pure functions: every transition, both ways."""

from __future__ import annotations

import json

import pytest

from harness import paths, scoreboard

PLAT = "darwin-arm64"
FILE = "tests/checks/test_v1_2_portable_and_sealed.py"
A, B = f"{FILE}::test_guest_runs_here[plain]", f"{FILE}::test_guest_has_no_network"
C = "tests/checks/test_rules.py::test_ruff_check_is_clean"


def check(status, area="v1.2", metrics=None, need=None):
    return {"area": area, "status": status, "reason": "", "need": need, "metrics": metrics or {}}


def run(checks, **meta):
    m = {
        "at": "2026-10-16T00:00:00Z",
        "commit": "c2",
        "dirty": False,
        "platform": PLAT,
        "host": "h",
        "wasmtime": "49.0.0",
        "artifact": "art",
        "judge": {"hash": "j", "files": {"tests/conftest.py": "1"}},
        "partial": None,
    }
    m.update(meta)
    return {"meta": m, "checks": checks, "deselected": [], "collected_files": [FILE]}


def accepted(checks, judge_files=None):
    return {
        "schema": 1,
        "commit": "c1",
        "judge": {"hash": "j", "files": judge_files or {"tests/conftest.py": "1"}},
        "checks": checks,
    }


def acc(status="pass", fuel=None, bytes_=None, wasmtime="49.0.0", platform=PLAT):
    metrics = {}
    if fuel is not None or bytes_ is not None:
        metrics[platform] = {"wasmtime": wasmtime}
        if fuel is not None:
            metrics[platform]["fuel"] = fuel
        if bytes_ is not None:
            metrics[platform]["bytes"] = bytes_
    return {"status": status, "commit": "c1", "artifact": "art", "metrics": metrics}


def test_no_baseline_means_everything_passing_is_gained() -> None:
    r = scoreboard.compare(run({A: check("pass"), B: check("blocked")}), None)
    assert r.gained == [A] and r.red(partial=False) == []


@pytest.mark.parametrize("now", ["fail", "gap"])
def test_a_pass_that_fails_or_turns_gap_is_lost(now) -> None:
    r = scoreboard.compare(run({A: check(now)}), accepted({A: acc()}))
    assert r.lost == [A] and r.red(partial=True)


def test_a_pass_that_is_blocked_is_red_unless_partial() -> None:
    r = scoreboard.compare(run({A: check("blocked", need="plain binary")}), accepted({A: acc()}))
    assert r.unrun == [A]
    assert r.red(partial=False) and not r.red(partial=True)


def test_deselected_and_outside_are_reported_not_red() -> None:
    rec = run({A: check("deselected")})
    rec["collected_files"] = []
    r = scoreboard.compare(rec, accepted({A: acc(), C: acc()}))
    assert r.deselected == [A] and r.outside == [C] and r.red(partial=False) == []


def test_a_check_missing_from_its_collected_file_is_absent() -> None:
    r = scoreboard.compare(run({A: check("pass")}), accepted({A: acc(), B: acc()}))
    assert r.absent == [B] and r.red(partial=True)


def test_a_check_whose_file_is_gone_is_absent() -> None:
    gone = "tests/checks/test_gone.py::test_x"
    rec = run({})
    rec["collected_files"] = []
    r = scoreboard.compare(rec, accepted({gone: acc()}))
    assert r.absent == [gone]


def test_fuel_growth_beyond_the_tolerance_is_red_and_within_it_is_not() -> None:
    base = accepted({A: acc(fuel=1_000_000)})
    within = scoreboard.compare(run({A: check("pass", metrics={"fuel": 1_000_100})}), base)
    beyond = scoreboard.compare(run({A: check("pass", metrics={"fuel": 1_000_101})}), base)
    assert within.growth == [] and beyond.growth == [f"{A}: fuel 1000000 -> 1000101"]


def test_fuel_is_not_compared_across_wasmtime_versions_or_platforms() -> None:
    other_engine = accepted({A: acc(fuel=10, wasmtime="48.0.0")})
    r = scoreboard.compare(run({A: check("pass", metrics={"fuel": 99})}), other_engine)
    assert r.growth == [] and r.fuel_not_compared == [A]
    other_platform = accepted({A: acc(fuel=10, platform="linux-x86_64")})
    r = scoreboard.compare(run({A: check("pass", metrics={"fuel": 99})}), other_platform)
    assert r.growth == [] and r.fuel_not_compared == []


def test_any_bytes_growth_is_red() -> None:
    r = scoreboard.compare(
        run({A: check("pass", metrics={"bytes": 101})}), accepted({A: acc(bytes_=100)})
    )
    assert r.growth == [f"{A}: bytes 100 -> 101"]


def test_a_changed_judge_is_reported_not_red() -> None:
    r = scoreboard.compare(
        run({A: check("pass")}), accepted({A: acc()}, judge_files={"tests/conftest.py": "0"})
    )
    assert r.judge_changed == ["tests/conftest.py"] and r.red(partial=False) == []


def _accept(rec, base, history="", **kw):
    r = scoreboard.compare(rec, base)
    kw.setdefault("green", True)
    return scoreboard.accept(rec, base, history, r, reason="because", **kw)


@pytest.mark.parametrize(
    ("rec", "base", "kw", "refusal"),
    [
        (run({A: check("pass")}), None, {"green": False}, "not green"),
        (run({A: check("gap")}), accepted({A: acc()}), {}, "lost passes"),
        (run({}), accepted({B: acc()}), {}, "absent checks not retired"),
        (
            run({A: check("blocked", need="plain binary")}),
            accepted({A: acc()}),
            {},
            "say --partial",
        ),
        (
            run({A: check("pass", metrics={"fuel": 2})}),
            accepted({A: acc(fuel=1)}),
            {},
            "say --accept-growth",
        ),
        (
            run({A: check("pass")}),
            accepted({A: acc()}, judge_files={"x": "y"}),
            {},
            "say --accept-judge",
        ),
        (run({A: check("pass")}), accepted({A: acc(), C: acc()}), {"retire": [C]}, "not absent"),
    ],
)
def test_accept_refuses(rec, base, kw, refusal) -> None:
    with pytest.raises(scoreboard.AcceptRefused, match=refusal):
        _accept(rec, base, **kw)


def test_accept_keeps_the_minimum_metric_unless_growth_is_accepted() -> None:
    base = accepted({A: acc(fuel=1_000_000)})
    lower, _ = _accept(run({A: check("pass", metrics={"fuel": 999_000})}), base)
    assert lower["checks"][A]["metrics"][PLAT]["fuel"] == 999_000
    slightly_up, _ = _accept(run({A: check("pass", metrics={"fuel": 1_000_050})}), base)
    assert slightly_up["checks"][A]["metrics"][PLAT]["fuel"] == 1_000_000
    grown, line = _accept(
        run({A: check("pass", metrics={"fuel": 2_000_000})}), base, growth_reason="bigger job"
    )
    assert grown["checks"][A]["metrics"][PLAT]["fuel"] == 2_000_000
    assert json.loads(line)["growth_reason"] == "bigger job"


def test_accept_rebaselines_fuel_on_a_new_wasmtime() -> None:
    base = accepted({A: acc(fuel=10, wasmtime="48.0.0")}, judge_files={"uv.lock": "old"})
    new, _ = _accept(
        run({A: check("pass", metrics={"fuel": 99})}), base, judge_reason="wasmtime 49"
    )
    assert new["checks"][A]["metrics"][PLAT] == {"wasmtime": "49.0.0", "fuel": 99}


def test_accept_carries_over_checks_that_did_not_run_and_retires_on_request() -> None:
    gone = f"{FILE}::test_removed"
    base = accepted({A: acc(), B: acc(), gone: acc()})
    rec = run({A: check("pass"), B: check("blocked", need="plain binary")})
    new, line = _accept(rec, base, partial_reason="no artifacts here", retire=[gone])
    assert set(new["checks"]) == {A, B}
    assert new["checks"][B] == base["checks"][B]
    assert json.loads(line)["retired"] == [gone]


def test_a_pass_blocked_by_local_tooling_is_reported_not_red() -> None:
    r = scoreboard.compare(run({A: check("blocked", need="oracle")}), accepted({A: acc()}))
    assert r.unrun == [] and r.unrun_local == [A] and r.red(partial=False) == []


def test_a_metric_that_stops_being_recorded_is_red() -> None:
    r = scoreboard.compare(run({A: check("pass")}), accepted({A: acc(fuel=10)}))
    assert r.growth == [f"{A}: fuel is no longer recorded"]


def test_the_ratchet_and_red_lines_survive_the_line_cap() -> None:
    checks = {f"t.py::f{i}": check("fail", area="rules") for i in range(40)}
    ratchet = scoreboard.Ratchet(lost=["a", "b", "c"], growth=["x: fuel 1 -> 2"])
    lines = scoreboard.render(run(checks), ratchet, {}, ["the reason it is red"])
    assert len(lines) <= scoreboard.MAX_LINES
    assert lines[-1].startswith("  licence content")
    assert any(line.startswith("RED: the reason") for line in lines)
    assert any(line.startswith("GREW x") for line in lines)


def test_history_lines_chain_and_name_what_they_wrote() -> None:
    first_acc, first = _accept(run({A: check("pass")}), None)
    history = first + "\n"
    second_acc, second = _accept(run({A: check("pass")}), first_acc, history)
    history += second + "\n"
    one, two = json.loads(first), json.loads(second)
    assert (one["n"], one["prev"]) == (1, None)
    assert (two["n"], two["prev"]) == (2, paths.sha256_bytes(first.encode()))
    assert two["accepted"] == paths.sha256_bytes(scoreboard.dumps(second_acc).encode())
    assert two["passed"] == [A] and two["platform"] == PLAT and two["at"]
    assert scoreboard.history_errors(history, scoreboard.dumps(second_acc), first + "\n") == []


def test_history_errors_catch_tampering() -> None:
    acc1, l1 = _accept(run({A: check("pass")}), None)
    acc2, l2 = _accept(run({A: check("pass")}), acc1, l1 + "\n")
    history = f"{l1}\n{l2}\n"
    good = scoreboard.dumps(acc2)
    edited = good.replace('"pass"', '"fail"')
    assert scoreboard.history_errors(history, edited, None) == [
        "accepted.json is not the file the last history line wrote"
    ]
    rewritten = history.replace('"because"', '"other"', 1)
    assert "history line 2: prev does not hash line 1" in scoreboard.history_errors(
        rewritten, good, None
    )
    assert scoreboard.history_errors(rewritten, good, history)[-1] == (
        "history.jsonl does not extend its committed version (a line was rewritten)"
    )
    assert scoreboard.history_errors("", good, None) == [
        "accepted.json exists but the history is empty"
    ]


def test_systems_that_passed_read_the_history(work) -> None:
    history = work / "history.jsonl"
    lines = [
        {"artifact": "art", "platform": "darwin-arm64", "passed": [A]},
        {"artifact": "art", "platform": "linux-x86_64", "passed": [A]},
        {"artifact": "other", "platform": "win32-amd64", "passed": [A]},
        {"artifact": "art", "platform": "win32-amd64", "passed": [B]},
    ]
    history.write_text("".join(json.dumps(x) + "\n" for x in lines))
    assert scoreboard.systems_that_passed(history, "art") == {"darwin", "linux"}


def test_the_scoreboard_fits_in_25_lines_and_names_the_next_document() -> None:
    checks = {f"t.py::f{i}": check("fail", area="rules") for i in range(30)}
    checks.update({f"t.py::b{i}": check("blocked", need="runner") for i in range(5)})
    lines = scoreboard.render(run(checks), scoreboard.Ratchet(), {"runner": "spec-001.md"}, [])
    assert len(lines) <= 25
    assert "next: spec-001.md (unblocks 5, closes 0)" in lines
    assert sum(line.startswith("FAIL ") for line in lines) == scoreboard.MAX_FAIL_LINES
    assert any(line.startswith("+20 more failures") for line in lines)


def test_the_judge_includes_any_conftest_and_pytest_config(work, monkeypatch) -> None:
    (work / "tests").mkdir()
    (work / "tests" / "test_a.py").write_text("")
    (work / "conftest.py").write_text("")
    (work / "deep" / "er").mkdir(parents=True)
    (work / "deep" / "er" / "conftest.py").write_text("")
    (work / "pytest.ini").write_text("")
    (work / "build" / "x").mkdir(parents=True)
    (work / "build" / "x" / "conftest.py").write_text("")
    monkeypatch.setattr(paths, "REPO", work)
    assert sorted(paths.judge_files()) == [
        "conftest.py",
        "deep/er/conftest.py",
        "pytest.ini",
        "tests/test_a.py",
    ]
