"""The ratchet and acceptance as pure functions: every transition, both ways."""

from __future__ import annotations

import json

import pytest

from harness import history, paths, scoreboard

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


def _accept(rec, base, text="", **kw):
    r = scoreboard.compare(rec, base)
    kw.setdefault("green", True)
    lines = [x for x in text.split("\n") if x.strip()]
    return scoreboard.accept(rec, base, lines, r, reason="because", **kw)


def test_the_judge_changed_line_says_how_many_files_it_leaves_out() -> None:
    changed = ["a.py", "b.py", "c.py", "d.py"]
    line = scoreboard._ratchet_line(scoreboard.Ratchet(judge_changed=changed), None)
    assert line.endswith("judge changed: a.py, b.py, c.py and 1 more"), line
    line = scoreboard._ratchet_line(scoreboard.Ratchet(judge_changed=changed[:3]), None)
    assert line.endswith("judge changed: a.py, b.py, c.py"), line


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
    text = first + "\n"
    second_acc, second = _accept(run({A: check("pass")}), first_acc, text)
    text += second + "\n"
    one, two = json.loads(first), json.loads(second)
    assert (one["n"], one["prev"]) == (1, None)
    assert (two["n"], two["prev"]) == (2, paths.sha256_bytes(first.encode()))
    assert two["accepted"] == paths.sha256_bytes(scoreboard.dumps(second_acc).encode())
    assert one["passed_added"] == [A] and two["passed_added"] == two["passed_removed"] == []
    assert two["passed_digest"] == history.digest([A]) and "passed" not in two
    assert two["platform"] == PLAT and two["at"] and two["schema"] == 2
    found = {history.FIRST: text.encode()}
    committed = {history.FIRST: (first + "\n").encode()}
    assert history.errors(found, scoreboard.dumps(second_acc), committed) == []


def test_history_errors_catch_tampering() -> None:
    acc1, l1 = _accept(run({A: check("pass")}), None)
    acc2, l2 = _accept(run({A: check("pass")}), acc1, l1 + "\n")
    text = f"{l1}\n{l2}\n"
    good = scoreboard.dumps(acc2)
    edited = good.replace('"pass"', '"fail"')

    def errors(t, accepted, committed=None):
        found = {history.FIRST: t.encode()} if t else {}
        return history.errors(found, accepted, committed and {history.FIRST: committed.encode()})

    assert errors(text, edited) == ["accepted.json is not the file the last history line wrote"]
    rewritten = text.replace('"because"', '"other"', 1)
    assert "history line 2: prev does not hash line 1" in errors(rewritten, good)
    assert errors(rewritten, good, text)[-1] == (
        "history.jsonl does not extend its committed version (a line was rewritten)"
    )
    assert errors("", good) == ["accepted.json exists but the history is empty"]


def test_systems_that_passed_read_the_history(work) -> None:
    lines = [
        {"artifact": "art", "platform": "darwin-arm64", "passed": [A]},
        {"artifact": "art", "platform": "linux-x86_64", "passed": [A]},
        {"artifact": "other", "platform": "win32-amd64", "passed": [A]},
        {"artifact": "art", "platform": "win32-amd64", "passed": [B]},
    ]
    (work / history.FIRST).write_text("".join(json.dumps(x) + "\n" for x in lines))
    assert history.systems_that_passed(work, "art") == {"darwin", "linux"}


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


def test_accept_drops_a_metric_no_longer_recorded_when_growth_is_accepted() -> None:
    """A check that stops recording a metric is "growth" until accepted; accepting it with a
    reason drops the old figure, so the next run is not red over it again."""
    base = accepted({A: acc(fuel=1_000_000)})
    kept, _ = _accept(run({A: check("pass")}), base, growth_reason="its fuel was noise")
    assert kept["checks"][A]["metrics"].get(PLAT, {}) in ({}, {"wasmtime": "49.0.0"})
    rec = run({A: check("pass")})
    assert scoreboard.compare(rec, kept).growth == []


def test_files_an_os_writes_are_not_part_of_the_judge(tmp_path, monkeypatch) -> None:
    """A `.DS_Store` that Finder writes into `tests/` must not change the judge's hash, or a hash
    accepted on a desktop could never match CI's (spec 011 concurrency-check review, F3)."""
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text("")
    monkeypatch.setattr(paths, "REPO", tmp_path)
    monkeypatch.setattr(paths, "JUDGE_PATHS", ("tests",))
    clean = paths.judge_files()
    for name in {".DS_Store", *paths.OS_LITTER}:
        (tmp_path / "tests" / name).write_bytes(b"\0")
    assert paths.judge_files() == clean == {"tests/test_a.py": paths.sha256_bytes(b"")}


# ---------------------------------------------------------------------------------------------
# The `passes` metric, its own list and flag, absent gaps, and the upstream refusal (spec 050)

UP = "tests/checks/test_v1_3_upstream_suites.py"
G = f"{UP}::test_upstream_suite[pandas-libs]"


def acc_passes(passes, fuel=None, status="pass"):
    a = acc(status, fuel=fuel if fuel is not None else 10)
    a["metrics"][PLAT]["passes"] = passes
    return a


def test_fewer_passes_are_red_in_their_own_list_and_print_first() -> None:
    rec = run({G: check("pass", area="v1.3", metrics={"fuel": 99, "passes": 1062})})
    rec["collected_files"] = [UP]
    r = scoreboard.compare(rec, accepted({G: acc_passes(1063)}))
    assert r.fewer == [f"{G}: passes 1063 -> 1062"]
    assert r.growth == [f"{G}: fuel 10 -> 99"]  # fuel growth stays in growth
    assert r.more == [] and r.gained == []
    assert any("pass count" in why for why in r.red(partial=True))
    lines = scoreboard.render(rec, r, {}, r.red(partial=False))
    fewer = next(i for i, line in enumerate(lines) if line.startswith("FEWER "))
    grew = next(i for i, line in enumerate(lines) if line.startswith("GREW "))
    assert lines[fewer] == f"FEWER {G}: passes 1063 -> 1062" and fewer < grew


@pytest.mark.parametrize("n_fewer", [0, 2, 6, 11])
def test_every_fewer_line_the_red_line_and_the_tail_survive_the_line_cap(n_fewer) -> None:
    """The build review's F3: eleven FEWER lines and three each of LOST, ABSENT and GREW must not
    push the RED line or the "not machine-checked" lines off the scoreboard."""
    fewer = [f"t.py::g{i}: passes 9 -> 8" for i in range(n_fewer)]
    checks = {f"t.py::f{i}": check("fail", area="rules") for i in range(40)}
    ratchet = scoreboard.Ratchet(
        fewer=fewer,
        lost=["l1", "l2", "l3"],
        absent=["a1", "a2", "a3"],
        growth=["x: fuel 1 -> 2"] * 5,
    )
    lines = scoreboard.render(run(checks), ratchet, {}, ["the reason it is red"])
    assert len(lines) <= scoreboard.MAX_LINES
    assert sum(line.startswith("FEWER ") for line in lines) == n_fewer
    assert any(line.startswith("RED: the reason") for line in lines)
    assert lines[-2].startswith("not machine-checked") and lines[-1].startswith("  licence")
    assert lines[0].startswith("wasi_python v1:") and any(x.startswith("ratchet vs") for x in lines)


def test_a_passes_metric_no_longer_recorded_is_fewer_not_growth() -> None:
    """The build review's F4: dropping `passes` must not ride on --accept-growth."""
    rec = run({G: check("pass", area="v1.3", metrics={"fuel": 10})})
    base = accepted({G: acc_passes(1063)})
    r = scoreboard.compare(rec, base)
    assert r.fewer == [f"{G}: passes 1063 -> none"] and r.growth == []
    with pytest.raises(scoreboard.AcceptRefused, match="say --accept-fewer-passes"):
        _accept(rec, base, growth_reason="unrelated growth")
    new, _ = _accept(rec, base, fewer_reason="the group no longer counts passes")
    assert "passes" not in new["checks"][G]["metrics"][PLAT]


def test_more_passes_are_reported_in_more_not_gained() -> None:
    rec = run({G: check("pass", area="v1.3", metrics={"fuel": 10, "passes": 1064})})
    r = scoreboard.compare(rec, accepted({G: acc_passes(1063)}))
    assert r.more == [f"{G}: passes 1063 -> 1064"] and r.gained == [] and r.fewer == []
    assert r.red(partial=False) == []


def test_fewer_passes_need_their_own_flag_and_growth_does_not_carry_them() -> None:
    rec = run({G: check("pass", area="v1.3", metrics={"fuel": 99, "passes": 1000})})
    rec["collected_files"] = [UP]
    base = accepted({G: acc_passes(1063)})
    with pytest.raises(scoreboard.AcceptRefused, match="say --accept-fewer-passes"):
        _accept(rec, base, growth_reason="the zip grew")
    new, line = _accept(
        rec, base, growth_reason="the zip grew", fewer_reason="a test moved to slow upstream"
    )
    assert new["checks"][G]["metrics"][PLAT]["passes"] == 1000
    assert new["checks"][G]["metrics"][PLAT]["fuel"] == 99
    assert json.loads(line)["fewer_reason"] == "a test moved to slow upstream"


def test_without_the_flag_acceptance_keeps_the_most_passes() -> None:
    base = accepted({G: acc_passes(1063)})
    more = run({G: check("pass", area="v1.3", metrics={"fuel": 10, "passes": 1070})})
    new, line = _accept(more, base)
    assert new["checks"][G]["metrics"][PLAT]["passes"] == 1070
    assert json.loads(line)["fewer_reason"] is None
    fell = run({G: check("pass", area="v1.3", metrics={"fuel": 10, "passes": 1060})})
    with pytest.raises(scoreboard.AcceptRefused, match="say --accept-fewer-passes"):
        _accept(fell, base)


def test_an_accepted_gap_whose_check_is_absent_is_absent_and_retire_takes_it() -> None:
    gone = f"{FILE}::test_once_a_gap"
    base = accepted({A: acc(), gone: acc("gap")})
    r = scoreboard.compare(run({A: check("pass")}), base)
    assert r.absent == [gone] and r.lost == []
    new, line = _accept(run({A: check("pass")}), base, retire=[gone])
    assert gone not in new["checks"] and json.loads(line)["retired"] == [gone]


def test_an_accepted_gap_now_failing_or_outside_is_not_lost_or_absent() -> None:
    rec = run({A: check("fail")})
    rec["collected_files"] = []
    base = accepted({A: acc("gap"), B: acc("gap")})
    r = scoreboard.compare(rec, base)
    assert r.lost == [] and r.absent == [] and r.outside == []


@pytest.mark.parametrize("status", ["pass", "gap"])
@pytest.mark.parametrize("now", ["blocked", "deselected"])
def test_accept_refuses_while_an_accepted_upstream_check_is_blocked_or_deselected(
    now, status
) -> None:
    """The case Decision 13 was written for (the pre-build review's F9): every upstream check is
    in the run, blocked because the kit is gone, or deselected. Nothing else in the run would
    refuse (the build review's F2: an accepted pass and an accepted gap, each alone)."""
    checks = {
        A: check("pass"),
        G: check(now, area="v1.3", need="upstream kit" if now == "blocked" else None),
    }
    rec = run(checks)
    rec["collected_files"] = [FILE, UP]
    base_entry = acc_passes(1063) if status == "pass" else acc("gap")
    base = accepted({A: acc(), G: base_entry})
    r = scoreboard.compare(rec, base)
    assert r.upstream_unrun == [G] and r.absent == [] and r.lost == []
    with pytest.raises(scoreboard.AcceptRefused, match="upstream suite check"):
        _accept(rec, base)
    new, line = _accept(rec, base, partial_reason="no kit here")
    assert new["checks"][G] == base["checks"][G]
    assert json.loads(line)["partial_reason"] == "no kit here"


def test_accept_refuses_while_an_accepted_upstream_gap_is_outside_the_run() -> None:
    gap = f"{UP}::test_upstream_class[pandas-tslibs-no-processes]"
    rec = run({A: check("pass")})  # the upstream file was not collected
    base = accepted({A: acc(), gap: acc("gap")})
    r = scoreboard.compare(rec, base)
    assert r.upstream_unrun == [gap] and r.absent == []
    with pytest.raises(scoreboard.AcceptRefused, match="upstream suite check"):
        _accept(rec, base)
    _accept(rec, base, partial_reason="fast tier")


def test_a_passing_upstream_check_is_not_unrun() -> None:
    rec = run(
        {A: check("pass"), G: check("pass", area="v1.3", metrics={"fuel": 10, "passes": 1063})}
    )
    assert scoreboard.compare(rec, accepted({A: acc(), G: acc_passes(1063)})).upstream_unrun == []
