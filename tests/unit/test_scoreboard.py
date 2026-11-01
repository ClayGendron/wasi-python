"""The ratchet and acceptance as pure functions: every transition, both ways."""

from __future__ import annotations

import json
import sys

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


ELSEWHERE = "linux-x86_64"  # a system other than the key's


def _measured_elsewhere(fuel: int) -> dict:
    """An accepted entry under darwin's key whose fuel another system measured."""
    entry = acc(fuel=fuel)
    entry["metrics"][PLAT]["fuel_platform"] = ELSEWHERE
    return entry


@pytest.mark.parametrize(
    "now",
    [{"fuel": 200}, {"fuel": 200, "fuel_platform": ELSEWHERE}, {"fuel": 50}],
    ids=["a darwin run against a linux fuel", "a linux fuel against a linux fuel", "a fall"],
)
def test_fuel_another_system_measured_is_never_compared(now) -> None:
    """Fuel differs between systems by more than the tolerance, and Linux's does not repeat
    between runs: a fuel either side measured on a system other than the run's is listed, never
    a growth, and its label is no metric that could stop being recorded."""
    r = scoreboard.compare(
        run({A: check("pass", metrics=now)}), accepted({A: _measured_elsewhere(100)})
    )
    assert r.growth == [] and r.red(partial=False) == []
    assert r.fuel_elsewhere == [A] and r.fuel_not_compared == []
    assert "fuel not compared (measured on another system) 1" in scoreboard._ratchet_line(r, None)


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
            accepted({A: acc()}, judge_files={"tests/known_gaps.toml": "y"}),
            {},
            "say --accept-judge",
        ),
        (run({A: check("pass")}), accepted({A: acc(), C: acc()}), {"retire": [C]}, "not absent"),
    ],
)
def test_accept_refuses(rec, base, kw, refusal) -> None:
    with pytest.raises(scoreboard.AcceptRefused, match=refusal):
        _accept(rec, base, **kw)


def test_accept_judge_is_refused_as_unnecessary_when_no_verdict_bearing_file_changed() -> None:
    harness_edit = accepted({A: acc()}, judge_files={"tests/harness/scan.py": "0"})
    with pytest.raises(scoreboard.AcceptRefused, match="--accept-judge is unnecessary"):
        _accept(run({A: check("pass")}), harness_edit, judge_reason="a new rule")
    new, line = _accept(run({A: check("pass")}), harness_edit)  # recorded by the hash alone
    assert json.loads(line)["judge_changed"] == ["tests/conftest.py", "tests/harness/scan.py"]
    assert json.loads(line)["judge_reason"] is None
    with pytest.raises(scoreboard.AcceptRefused, match="--accept-judge is unnecessary"):
        _accept(run({A: check("pass")}), accepted({A: acc()}), judge_reason="nothing changed")


@pytest.mark.parametrize(
    "verdict_file",
    [
        "tests/known_gaps.toml",
        "tests/upstream/numpy.toml",
        "tests/upstream/expected/numpy-core/x.txt",
        "tests/upstream/python/cpython-a.txt",
        "tests/release_shards.toml",
        "tests/public_api.txt",
        "context/release-claims/166-the-pins-move.toml",
        "context/release-claims/README.md",
    ],
)
def test_accept_judge_is_required_when_a_verdict_bearing_file_changed(verdict_file) -> None:
    files = {"tests/conftest.py": "1", verdict_file: "0"}
    moved = accepted({A: acc()}, judge_files=files)
    with pytest.raises(scoreboard.AcceptRefused, match="say --accept-judge") as e:
        _accept(run({A: check("pass")}), moved)
    assert verdict_file in str(e.value)
    _, line = _accept(run({A: check("pass")}), moved, judge_reason="a new allowance")
    assert json.loads(line)["judge_reason"] == "a new allowance"


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
    new, _ = _accept(run({A: check("pass", metrics={"fuel": 99})}), base)
    assert new["checks"][A]["metrics"][PLAT] == {"wasmtime": "49.0.0", "fuel": 99}


def test_accept_lets_the_keys_own_system_replace_another_systems_fuel() -> None:
    """The first fuel the key's own system measures replaces another system's whole, with no
    reason asked, and the label goes with it: two systems are never mixed in one number."""
    base = accepted({A: _measured_elsewhere(100)})
    new, _ = _accept(run({A: check("pass", metrics={"fuel": 200})}), base)
    assert new["checks"][A]["metrics"][PLAT] == {"wasmtime": "49.0.0", "fuel": 200}


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


@pytest.mark.parametrize("n_worktrees", [0, 1, 2, 10, 40])
def test_worktree_notes_take_one_line_and_leave_the_lost_line(n_worktrees) -> None:
    """However many worktrees sit inside the repository, their notes take at most one line, so
    the scoreboard still names the pass it lost; the record keeps every one."""
    names = [f".claude/worktrees/w{i:02}" for i in range(n_worktrees)]
    notes = [paths.WORKTREE_NOTE.format(w) for w in names]
    lost = "test_inner.py::test_failing"
    checks = {A: check("pass"), lost: check("fail", area="rules")}
    ratchet = scoreboard.Ratchet(lost=[lost])
    lines = scoreboard.render(run(checks, notes=notes), ratchet, {}, ["lost 1"])
    assert len(lines) <= scoreboard.MAX_LINES
    assert f"LOST {lost}" in lines
    shown = [line for line in lines if line.startswith("note: ")]
    assert len(shown) == min(1, n_worktrees)
    if n_worktrees == 1:
        assert shown == notes
    elif n_worktrees > 1:
        assert f"{n_worktrees} worktrees inside the repository" in shown[0]
        assert names[0] in shown[0]
        assert (names[-1] in shown[0]) == (n_worktrees <= scoreboard.WORKTREES_NAMED)


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
    accepted on a desktop could never match CI's."""
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text("")
    monkeypatch.setattr(paths, "REPO", tmp_path)
    monkeypatch.setattr(paths, "JUDGE_PATHS", ("tests",))
    clean = paths.judge_files()
    (tmp_path / "tests" / ".TemporaryItems").mkdir()
    (tmp_path / "tests" / ".TemporaryItems" / "x.py").write_text("")  # every part
    for name in {".DS_Store", "._test_a.py", *paths.OS_LITTER} - {".TemporaryItems"}:
        if sys.platform == "win32" and "\r" in name:
            continue  # a Windows file name cannot hold Icon\r's CR
        (tmp_path / "tests" / name).write_bytes(b"\0")
    assert paths.judge_files() == clean == {"tests/test_a.py": paths.sha256_bytes(b"")}


# ---------------------------------------------------------------------------------------------
# The `passes` metric, its own list and flag, absent gaps, and the upstream refusal

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
    """Eleven FEWER lines and three each of LOST, ABSENT and GREW must not
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
    """Dropping `passes` must not ride on --accept-growth."""
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
    """The case Decision 13 was written for: every upstream check is
    in the run, blocked because the kit is gone, or deselected. Nothing else in the run would
    refuse (an accepted pass and an accepted gap, each alone)."""
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


def test_the_line_carries_the_sets_sha256sums() -> None:
    """The lane's acceptance names the whole set, beside python.wasm."""
    r = run({A: check("pass")}, set_sums="s" * 64)
    _, line = scoreboard.accept(r, None, [], scoreboard.Ratchet(), green=True, reason="r")
    assert json.loads(line)["set_sums"] == "s" * 64
    _, line = scoreboard.accept(
        run({A: check("pass")}), None, [], scoreboard.Ratchet(), green=True, reason="r"
    )
    assert json.loads(line)["set_sums"] is None


# The release tier: rows a normal run does not run, moves between tiers, the carried passed set.

UPSTREAM = scoreboard.UPSTREAM_FILE
SLOW = f"{UPSTREAM}::test_upstream_suite[numpy-slow]"
SLOW_K = f"{UPSTREAM}::test_upstream_class[numpy-slow-wasm32-memory]"
CORE = f"{UPSTREAM}::test_upstream_suite[numpy-core]"


def tiered(checks, release=(), tier="normal", deselected=()):
    rec = run(checks, tier=tier)
    rec["release_checks"] = sorted(release)
    rec["deselected"] = sorted(deselected)
    rec["collected_files"] = [FILE, UPSTREAM]
    return rec


def released(status="pass", fuel=None):
    entry = acc(status, fuel=fuel)
    entry["tier"] = "release"
    return entry


def test_a_normal_run_leaves_accepted_release_tier_rows_in_their_own_list() -> None:
    rec = tiered(
        {A: check("pass"), SLOW: check("deselected", area="v1.3")},
        release=[SLOW, SLOW_K],
        deselected=[SLOW, SLOW_K],
    )
    base = accepted({A: acc(), SLOW: released(fuel=10), SLOW_K: released("gap")})
    r = scoreboard.compare(rec, base)
    assert r.release_tier == sorted([SLOW, SLOW_K])
    assert r.deselected == [] and r.upstream_unrun == [] and r.absent == [] and r.moved == []
    assert r.red(partial=False) == []
    assert "release tier not run 2" in scoreboard._ratchet_line(r, None)


def test_a_normal_acceptance_keeps_release_tier_rows_and_needs_no_partial() -> None:
    rec = tiered(
        {A: check("pass"), SLOW: check("deselected", area="v1.3")},
        release=[SLOW],
        deselected=[SLOW],
    )
    base = accepted({A: acc(), SLOW: released(fuel=10)})
    new, line = _accept(rec, base)
    assert new["checks"][SLOW] == base["checks"][SLOW]
    assert json.loads(line)["tier"] == "normal"


def test_a_release_run_ratchets_release_tier_rows_like_any_other() -> None:
    rec = tiered({SLOW: check("fail", area="v1.3")}, release=[SLOW], tier="release")
    r = scoreboard.compare(rec, accepted({SLOW: released()}))
    assert r.lost == [SLOW] and r.release_tier == []


def test_a_normal_acceptance_carries_release_tier_passes_in_the_history() -> None:
    # A release acceptance in which SLOW passed, then a normal one that did not run it.
    first = tiered(
        {A: check("pass"), SLOW: check("pass", area="v1.3")}, release=[SLOW], tier="release"
    )
    base, line1 = _accept(first, None)
    assert json.loads(line1)["tier"] == "release" and base["checks"][SLOW]["tier"] == "release"
    second = tiered(
        {A: check("pass"), SLOW: check("deselected", area="v1.3")},
        release=[SLOW],
        deselected=[SLOW],
    )
    _, line2 = _accept(second, base, line1)
    entry = json.loads(line2)
    assert SLOW not in entry["passed_removed"] and SLOW not in entry["passed_added"]
    assert entry["passed_digest"] == history.digest({A, SLOW})
    assert entry["counts"]["v1.3"] == "1/1"
    assert list(history.passed_sets([line1, line2]))[-1] == {A, SLOW}


def test_a_release_acceptance_writes_the_tier_only_on_release_tier_entries() -> None:
    rec = tiered(
        {A: check("pass"), SLOW: check("pass", area="v1.3")}, release=[SLOW], tier="release"
    )
    new, _ = _accept(rec, None)
    assert new["checks"][SLOW]["tier"] == "release" and "tier" not in new["checks"][A]


@pytest.mark.parametrize("tier", ["normal", "release"])
def test_a_normal_accepted_check_now_release_tier_is_moved_and_red(tier) -> None:
    status = "deselected" if tier == "normal" else "pass"
    rec = tiered({CORE: check(status, area="v1.3")}, release=[CORE], tier=tier)
    if tier == "normal":
        rec["deselected"] = [CORE]
    base = accepted({CORE: acc(fuel=5)})
    r = scoreboard.compare(rec, base)
    assert r.moved == [CORE] and r.release_tier == []
    assert any("moved between tiers" in w for w in r.red(partial=True))
    assert "moved 1" in scoreboard._ratchet_line(r, None)
    with pytest.raises(scoreboard.AcceptRefused, match="--accept-tier-move"):
        _accept(rec, base)


def test_accept_tier_move_rewrites_the_tier_and_nothing_else() -> None:
    rec = tiered({CORE: check("deselected", area="v1.3")}, release=[CORE], deselected=[CORE])
    base = accepted({CORE: acc(fuel=5)})
    new, line = _accept(rec, base, tier_move_reason="102: it is slow")
    assert new["checks"][CORE] == {**base["checks"][CORE], "tier": "release"}
    assert json.loads(line)["tier_move_reason"] == "102: it is slow"
    assert scoreboard.compare(rec, new).moved == []


def test_a_release_tier_entry_now_normal_is_moved_too() -> None:
    rec = tiered({SLOW: check("pass", area="v1.3")})
    r = scoreboard.compare(rec, accepted({SLOW: released()}))
    assert r.moved == [SLOW]
    new, _ = _accept(rec, accepted({SLOW: released()}), tier_move_reason="102: back")
    assert "tier" not in new["checks"][SLOW]


def test_a_release_tier_entry_whose_check_is_gone_is_absent_not_moved() -> None:
    rec = tiered({A: check("pass")})
    r = scoreboard.compare(rec, accepted({A: acc(), SLOW: released()}))
    assert r.absent == [SLOW] and r.moved == []


def test_a_history_line_with_and_without_a_tier_is_intact() -> None:
    plain = tiered({A: check("pass")})
    base, line1 = _accept(plain, None)
    del plain["meta"]["tier"]
    _, line2 = _accept(plain, base, line1)
    assert json.loads(line2)["tier"] == "normal"
    stripped = json.loads(line1)
    stripped.pop("tier")
    assert list(history.passed_sets([json.dumps(stripped, sort_keys=True)]))[-1] == {A}


def test_a_run_that_did_not_collect_a_moved_check_does_not_report_it() -> None:
    """A run of other files (a unit file, a node id) says nothing of a tier it never saw: the
    move is red where the upstream file is collected, as in every full or fast run."""
    rec = tiered({A: check("pass")}, release=[CORE])
    rec["collected_files"] = [FILE]
    r = scoreboard.compare(rec, accepted({A: acc(), CORE: acc(fuel=5)}))
    assert r.moved == [] and r.red(partial=False) == []


def test_a_shard_run_leaves_moves_to_the_gather() -> None:
    """A shard never accepts, and every shard collects the upstream file: a move would turn every
    leg red. The gather names each move once (G5); the shard's ratchet does not."""
    rec = tiered({CORE: check("deselected", area="v1.3")}, release=[CORE], deselected=[CORE])
    rec["meta"]["shard"] = "upstream-plot-a"
    r = scoreboard.compare(rec, accepted({CORE: acc(fuel=5)}))
    assert r.moved == [] and r.red(partial=False) == []


def test_an_absent_check_a_news_file_retires_is_listed_and_not_red() -> None:
    """The run's colour: an absent check a news file's claim retires is listed with its reason;
    the acceptance still takes the retirement only from the claim (or the local --retire)."""
    r = scoreboard.Ratchet(absent=["t.py::a", "t.py::b"], retired={"t.py::a": "999: retired"})
    assert r.red(partial=False) == ["1 accepted check(s) absent (retire them with --retire)"]
    r.retired["t.py::b"] = "999: retired"
    assert r.red(partial=False) == []
    run = {"meta": {}, "checks": {}, "suite": {}}
    lines = scoreboard.render(run, r, {}, [])
    assert "RETIRED t.py::a · 999: retired" in lines and not any("ABSENT" in x for x in lines)


def test_a_growth_or_fall_a_news_file_claims_is_listed_and_not_red() -> None:
    """A run's colour: a growth, a fall in a pass count or a tier move a news file claims is
    listed with its reason; an unclaimed one stays red; the acceptance still takes the reason
    only from the claim (CI) or --accept-growth and its kin (a local acceptance)."""
    grew, fell = "t.py::a: fuel 1 -> 2", "t.py::g: passes 5 -> 4"
    r = scoreboard.Ratchet(growth=[grew], fewer=[fell], moved=["t.py::m"])
    assert len(r.red(partial=False)) == 3
    r.claimed = {grew: "999: bigger", fell: "999: moved out", "t.py::m": "999: slow"}
    assert r.red(partial=False) == []
    lines = scoreboard.render({"meta": {}, "checks": {}, "suite": {}}, r, {}, [])
    assert f"CLAIMED {grew} · 999: bigger" in lines and not any(x.startswith("GREW") for x in lines)
