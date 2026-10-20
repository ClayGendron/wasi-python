"""Sameness against a release record, and claim lists (spec 092).

The release records here are made by `gather.merge` itself from synthetic shard records, so the
rows test the merged record the release workflow writes, not a copy of its shape."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import types
from pathlib import Path

import pytest

from harness import gather, paths, sameness

A = "tests/checks/test_a.py::test_everywhere"  # every system; fuel differs by platform
D = "tests/checks/test_a.py::test_descriptors"  # blocked on Windows only (descriptor limit)
ORACLE = "tests/checks/test_rules.py::test_oracle"  # blocked by the oracle everywhere in CI
U = "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[g1]"  # Linux only in CI
B = "tests/checks/test_v1_5_x.py::test_tree"  # the build shard only
GOAL = sorted([A, D, ORACLE, U, B])
FILES = sorted({n.split("::")[0] for n in GOAL} | {"tests/unit/test_u.py"})
DARWIN, LINUX, WIN = "darwin-arm64", "linux-x86_64", "win32-amd64"
SCRIPT = str(paths.REPO / "tests" / "harness" / "sameness.py")


def _pass(**metrics) -> dict:
    return {"area": "v1.3", "status": "pass", "reason": "", "need": None, "metrics": metrics}


def _blocked(need: str) -> dict:
    return {"area": "v1.3", "status": "blocked", "reason": need, "need": need, "metrics": {}}


def _shard(platform: str, shard: str, ran: dict, suite: tuple[int, int, int]) -> dict:
    checks = {
        n: ran.get(n, {"area": "v1.3", "status": "deselected", "reason": "", "need": None})
        for n in GOAL
    }
    for c in checks.values():
        c.setdefault("metrics", {})
    return {
        "meta": {"platform": platform, "shard": shard, "foreign": []},
        "checks": checks,
        "deselected": sorted(n for n, c in checks.items() if c["status"] == "deselected"),
        "collected_files": FILES,
        "suite": dict(zip(("passed", "skipped", "total"), suite, strict=True)),
    }


def shard_records() -> dict[tuple[str, str], dict]:
    upstream = {**_pass(passes=5, fuel=1000), "facts": {"passed_digest": "d1"}}
    return {
        ("build", "build"): _shard(DARWIN, "build", {B: _pass(bytes=10)}, (2, 0, 2)),
        ("macos", "own"): _shard(
            DARWIN, "own", {A: _pass(fuel=100), D: _pass(), ORACLE: _blocked("oracle")}, (5, 1, 6)
        ),
        ("linux", "own"): _shard(
            LINUX, "own", {A: _pass(fuel=200), D: _pass(), ORACLE: _blocked("oracle")}, (5, 1, 6)
        ),
        ("linux", "up"): _shard(LINUX, "up", {U: upstream}, (0, 0, 0)),
        ("windows", "own"): _shard(
            WIN,
            "own",
            {A: _pass(fuel=300), D: _blocked("descriptor limit"), ORACLE: _blocked("oracle")},
            (4, 2, 6),
        ),
    }


def release(records: dict | None = None) -> dict:
    i = types.SimpleNamespace(
        goal_nodes=GOAL,
        head="c" * 40,
        wasm_sha256="a" * 64,
        set_sums_sha256="s" * 64,
        judge_hash="j" * 64,
        tag=False,
    )
    return gather.merge(records or shard_records(), i)


def local() -> dict:
    """The lane's darwin run of the same judge: the oracle runs here; upstream fuel is darwin's."""
    upstream = {**_pass(passes=5, fuel=1234), "facts": {"passed_digest": "d1"}}
    checks = {A: _pass(fuel=100), D: _pass(), ORACLE: _pass(), U: upstream, B: _pass(bytes=10)}
    return {
        "meta": {"platform": DARWIN, "foreign": []},
        "checks": checks,
        "deselected": [],
        "collected_files": FILES,
        "suite": {"passed": 7, "skipped": 1, "total": 8},
    }


# ---------------------------------------------------------------------------------------------
# A release record read as the darwin run it contains (Decisions 1 to 4)


def test_a_release_record_and_its_darwin_twin_are_the_same() -> None:
    r, lane = release(), local()
    assert r["checks"][D]["status"] == "blocked"  # the merged status is still the worst
    assert sameness.differences(r, lane) == []
    assert sameness.differences(lane, r) == []
    assert sameness.differences(r, r) == []
    notes = sameness.notes(r, lane)
    assert "not run on any system in the release: 1 (oracle 1)" in notes
    assert "release fuel not from darwin, not compared: 1 (linux-x86_64 1)" in notes


def test_a_check_no_shard_ran_is_not_compared_but_one_present_on_one_side_is() -> None:
    lane = local()
    lane["checks"][ORACLE]["status"] = "fail"
    assert sameness.differences(release(), lane) == []
    del lane["checks"][ORACLE]
    assert sameness.differences(release(), lane) == [f"{ORACLE}: only in the first record"]


@pytest.mark.parametrize(
    ("edit", "want"),
    [
        (lambda r: r["checks"][A].update(status="fail"), f"{A}: status 'pass' != 'fail'"),
        (lambda r: r["checks"][A]["metrics"].update(fuel=101), f"{A}: fuel 100 != 101"),
        (lambda r: r["checks"][B]["metrics"].update(bytes=11), f"{B}: bytes 10 != 11"),
        (lambda r: r["checks"][U]["metrics"].update(passes=6), f"{U}: passes 5 != 6"),
        (lambda r: r["suite"].update(passed=6), "suite: "),
        (lambda r: r["meta"].update(foreign=["plugin x"]), "meta.foreign: "),
        (
            lambda r: r["collected_files"].append("tests/unit/test_v.py"),
            "collected_files: tests/unit/test_v.py only in the second record",
        ),
        (lambda r: r["deselected"].append(A), f"deselected: {A} only in the second record"),
    ],
)
def test_a_difference_from_the_darwin_view_is_named(edit, want) -> None:
    lane = copy.deepcopy(local())
    edit(lane)
    found = sameness.differences(release(), lane)
    assert any(line.startswith(want) for line in found), found


def test_a_shard_steered_from_outside_differs() -> None:
    records = shard_records()
    records[("linux", "up")]["meta"]["foreign"] = ["conftest.py outside the judge"]
    r = release(records)
    assert r["meta"]["foreign"] == ["conftest.py outside the judge"]
    assert any(line.startswith("meta.foreign: ") for line in sameness.differences(r, local()))


def test_linux_fuel_is_not_compared_and_darwin_fuel_is() -> None:
    records = shard_records()
    records[("linux", "up")]["checks"][U]["metrics"]["fuel"] = 9999  # Linux: not the lane's
    assert sameness.differences(release(records), local()) == []
    records[("macos", "own")]["checks"][A]["metrics"]["fuel"] = 200  # darwin: compared
    assert sameness.differences(release(records), local()) == [
        f"{A}: fuel 200 != 100 (beyond 0.0001)"
    ]


def test_two_releases_compare_darwin_fuel_only() -> None:
    """Linux fuel moves between two CI runs of one judge (cpython-b 291.7e9 and 302.0e9 in runs
    39346796670 and 39351481374); only darwin fuel is held, by G5 (Decision 3)."""
    records = shard_records()
    records[("linux", "up")]["checks"][U]["metrics"]["fuel"] = 1100
    assert sameness.differences(release(), release(records)) == []
    assert "release fuel not from darwin, not compared: 1 (linux-x86_64 1)" in sameness.notes(
        release(), release(records)
    )
    records[("macos", "own")]["checks"][A]["metrics"]["fuel"] = 200
    assert sameness.differences(release(), release(records)) == [
        f"{A}: fuel 100 != 200 (beyond 0.0001)"
    ]


def test_two_run_records_of_two_platforms_compare_no_fuel() -> None:
    a, b = local(), local()
    b["meta"]["platform"] = LINUX
    b["checks"][A]["metrics"]["fuel"] = 500
    assert sameness.differences(a, b) == []
    assert "fuel not compared across platforms: 2 (darwin-arm64 against linux-x86_64)" in (
        sameness.notes(a, b)
    )


def test_the_darwin_suite_is_the_build_and_macos_runs_together() -> None:
    r = release()
    assert set(r["runs"]) == {"build/build", "macos/own", "linux/own", "linux/up", "windows/own"}
    assert r["runs"]["macos/own"] == {
        "platform": DARWIN,
        "suite": {"passed": 5, "skipped": 1, "total": 6},
    }
    lane = local()
    lane["suite"] = {"passed": 5, "skipped": 1, "total": 6}  # the macOS shard's alone: not enough
    assert sameness.differences(r, lane) == [
        "suite: {'passed': 7, 'skipped': 1, 'total': 8} != {'passed': 5, 'skipped': 1, 'total': 6}"
    ]


def test_a_unit_test_skipped_on_one_host_only_is_a_note_across_kinds() -> None:
    """Between a release record and a run record, the suite's total and failing count decide;
    a test that skips on one host and passes on the other is named (Decision 2)."""
    r, lane = release(), local()
    lane["suite"] = {"passed": 6, "skipped": 2, "total": 8}
    assert sameness.differences(r, lane) == []
    assert any(n.startswith("unit tests skipped on one host") for n in sameness.notes(r, lane))
    lane["suite"] = {"passed": 6, "skipped": 1, "total": 8}  # one fails: a difference
    assert [d[:7] for d in sameness.differences(r, lane)] == ["suite: "]
    other = local()  # two records of one kind: the suite whole, as before
    other["suite"] = {"passed": 6, "skipped": 2, "total": 8}
    assert [d[:7] for d in sameness.differences(local(), other)] == ["suite: "]


def test_a_release_record_from_before_092_is_refused(tmp_path) -> None:
    old = release()
    del old["runs"], old["deselected"], old["collected_files"], old["meta"]["foreign"]
    for c in old["checks"].values():
        c.pop("worst_platform")
    with pytest.raises(sameness.NotComparable, match="before spec 092"):
        sameness.differences(old, local())
    a, b = tmp_path / "old.json", tmp_path / "lane.json"
    a.write_text(json.dumps(old))
    b.write_text(json.dumps(local()))
    r = subprocess.run([sys.executable, SCRIPT, str(a), str(b)], capture_output=True, text=True)
    assert r.returncode == 2 and "before spec 092" in r.stderr, r.stderr


# ---------------------------------------------------------------------------------------------
# Claim lists (Decision 5)

N = "tests/checks/test_new.py::test_added"
R = "tests/checks/test_a.py::test_retired"
G = "tests/checks/test_a.py::test_gap_closed"


def before() -> dict:
    run = local()
    run["checks"][R] = _pass()
    run["checks"][G] = {
        **_pass(),
        "status": "gap",
        "reason": "the named failure",
        "closer": "README.md",
    }
    return run


def after() -> dict:
    """What the second record has that the first lacks, one row of each kind."""
    run = copy.deepcopy(before())
    run["checks"][N] = _pass()
    run["collected_files"] = sorted([*run["collected_files"], "tests/checks/test_new.py"])
    del run["checks"][R]
    run["checks"][G] = _pass()
    run["checks"][U]["metrics"]["passes"] = 6
    run["checks"][U]["facts"] = {"passed_digest": "d2"}
    run["checks"][A]["metrics"]["fuel"] = 200
    run["suite"] = {"passed": 10, "skipped": 1, "total": 11}
    return run


FULL = """
[[claim]]
spec = "100"
new = ["tests/checks/test_new.py::test_added"]
retired = ["tests/checks/test_a.py::test_retired"]
units = 2

[[claim]]
spec = "101"
changed = ["tests/checks/test_a.py::test_gap_closed"]
passes = ["tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[g1]"]
grows = ["tests/checks/test_a.py::test_everywhere"]
growth = "101: fuel, the reason"
units = 1
"""


def claims(tmp_path: Path, text: str) -> list:
    f = tmp_path / "claims.toml"
    f.write_text(text)
    return sameness.load_claims(f)


def test_every_difference_has_its_claim(tmp_path) -> None:
    found = sameness.differences(before(), after())
    assert len(found) >= 9, found  # each kind is really there to explain
    assert sameness.unexplained(before(), after(), claims(tmp_path, FULL)) == []


@pytest.mark.parametrize(
    ("text", "left"),
    [
        # a fuel claim never explains a status, nor a pass count
        ('[[claim]]\nspec = "1"\ngrows = ["*"]\ngrowth = "1: g"\n', f"{G}: status"),
        ('[[claim]]\nspec = "1"\ngrows = ["*"]\ngrowth = "1: g"\n', f"{U}: passes"),
        # nor a changed claim a fuel row
        ('[[claim]]\nspec = "1"\nchanged = ["*"]\n', f"{A}: fuel"),
        # new is directional: it never explains a check that went away
        ('[[claim]]\nspec = "1"\nnew = ["*"]\n', f"{R}: only in the first record"),
        ('[[claim]]\nspec = "1"\nretired = ["*"]\n', f"{N}: only in the second record"),
        # the suite moves by exactly the claimed units, or it is unexplained
        ('[[claim]]\nspec = "1"\nunits = 2\n', "suite: "),
    ],
)
def test_a_claim_explains_its_own_kind_only(tmp_path, text, left) -> None:
    rest = sameness.unexplained(before(), after(), claims(tmp_path, text))
    assert any(line.startswith(left) for line in rest), rest


def test_a_file_entry_and_a_prefix_entry(tmp_path) -> None:
    for entry in ("tests/checks/test_new.py", "tests/checks/test_new*"):
        text = f'[[claim]]\nspec = "1"\nnew = ["{entry}"]\n'
        rest = sameness.unexplained(before(), after(), claims(tmp_path, text))
        assert not any("test_new" in line for line in rest), (entry, rest)


def test_except_drops_a_specs_claims(tmp_path) -> None:
    rest = sameness.unexplained(before(), after(), claims(tmp_path, FULL), drop={"101"})
    assert any(line.startswith(f"{G}: status") for line in rest)
    assert not any(line.startswith(f"{N}:") for line in rest)


@pytest.mark.parametrize(
    "text",
    [
        '[[claim]]\nnew = ["x"]\n',  # no spec
        "[[claim]]\nspec = 92\n",  # spec not a string
        '[[claim]]\nspec = "1"\ngrows = ["x"]\n',  # growth without its reason
        '[[claim]]\nspec = "1"\nnews = ["x"]\n',  # a key the shape does not name
        '[[claim]]\nspec = "1"\nnew = "x"\n',  # not a list
        '[[claim]]\nspec = "1"\nunits = "2"\n',  # not a number
        '[claims]\nspec = "1"\n',  # not [[claim]]
        "[[claim]\n",  # not TOML
    ],
)
def test_a_bad_claim_list_is_refused(tmp_path, text) -> None:
    with pytest.raises(sameness.ClaimError):
        claims(tmp_path, text)


def test_the_command_prints_only_what_no_claim_explains(tmp_path) -> None:
    a, b, c = tmp_path / "a.json", tmp_path / "b.json", tmp_path / "c.toml"
    a.write_text(json.dumps(before()))
    b.write_text(json.dumps(after()))
    c.write_text(FULL + '\n[[claim]]\nspec = "102"\nnew = ["tests/checks/test_z.py"]\n')

    def run(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True)

    plain = run(str(a), str(b))
    assert plain.returncode == 1 and plain.stdout.count("\n") >= 9
    claimed = run("--claims", str(c), str(a), str(b))
    assert (claimed.returncode, claimed.stdout) == (0, ""), claimed.stdout + claimed.stderr
    assert "claimed, not seen: 102 new tests/checks/test_z.py" in claimed.stderr
    assert "explained by claims: 100 4 · 101 6" in claimed.stderr, claimed.stderr
    dropped = run("--claims", str(c), "--except", "100", str(a), str(b))
    assert dropped.returncode == 1 and f"{N}: only in the second record" in dropped.stdout
    bad = tmp_path / "bad.toml"
    bad.write_text('[[claim]]\nspec = "1"\nnews = []\n')
    refused = run("--claims", str(bad), str(a), str(b))
    assert refused.returncode == 2 and "news" in refused.stderr


def test_a_fuel_fact_follows_the_fuel_rules(tmp_path) -> None:
    """Spec 091's fuel facts are fuel: compared to the tolerance between darwin rows only, and
    explained by a grows claim (the rebase onto wave 01)."""
    records = shard_records()
    records[("linux", "up")]["checks"][U]["facts"]["fuel_facts"] = {"f": 1000}
    records[("macos", "own")]["checks"][A]["facts"] = {"fuel_facts": {"f": 1000}}
    first = copy.deepcopy(release(records))  # merge shares the shard records' dicts
    records[("linux", "up")]["checks"][U]["facts"]["fuel_facts"] = {"f": 2000}  # Linux: not held
    records[("macos", "own")]["checks"][A]["facts"] = {"fuel_facts": {"f": 2000}}
    second = release(records)
    assert sameness.differences(first, second) == [
        f"{A}: fuel_facts f 1000 != 2000 (beyond 0.0001)"
    ]
    grows = f'[[claim]]\nspec = "1"\ngrows = ["{A}"]\ngrowth = "1: g"\n'
    assert sameness.unexplained(first, second, claims(tmp_path, grows)) == []


# ---------------------------------------------------------------------------------------------
# The build review's findings (F1 to F4)


def test_a_failure_on_another_system_is_a_difference_no_claim_explains(tmp_path) -> None:
    """F1: the darwin view never hides a merged status worse than its source's; only a block by a
    CI need on a system that lacks it (descriptor limit, Windows) is no difference."""
    records = shard_records()
    records[("windows", "own")]["checks"][A].update(status="fail", reason="boom", metrics={})
    r = release(records)
    want = f"{A}: status 'pass' on {DARWIN}, 'fail' on {WIN}"
    assert sameness.differences(r, local()) == [want]
    assert sameness.differences(r, r) == [want]  # even against itself: the run was red
    every = '[[claim]]\nspec = "1"\nchanged = ["*"]\ngrows = ["*"]\ngrowth = "1: g"\n'
    assert sameness.unexplained(r, local(), claims(tmp_path, every)) == [want]
    records = shard_records()  # a CI need on a system that does not lack it is no exemption
    records[("linux", "own")]["checks"][D].update(status="blocked", need="descriptor limit")
    assert sameness.differences(release(records), local()) == [
        f"{D}: status 'pass' on {DARWIN}, 'blocked' on {LINUX}"
    ]


@pytest.mark.parametrize(
    "entry",
    [
        {"status": "fail", "need": None},
        {"status": "pass", "need": None},
        {"status": "blocked", "need": "upstream kit"},
    ],
)
def test_a_check_without_a_source_that_ran_is_refused(entry) -> None:
    """F2: only a check every record deselected or blocked by a CI need may lack a source."""
    r = release()
    r["checks"][A].pop("source")
    r["checks"][A].update(entry)
    with pytest.raises(sameness.NotComparable, match=A.replace("[", r"\[")):
        sameness.differences(r, local())


def test_a_malformed_suite_is_refused_in_one_line(tmp_path) -> None:
    """F3: a non-number in a darwin run's suite is exit 2, one line, not a traceback."""
    r = release()
    r["runs"]["macos/own"]["suite"]["passed"] = "5"
    a, b = tmp_path / "r.json", tmp_path / "l.json"
    a.write_text(json.dumps(r))
    b.write_text(json.dumps(local()))
    got = subprocess.run([sys.executable, SCRIPT, str(a), str(b)], capture_output=True, text=True)
    assert got.returncode == 2 and got.stderr.startswith("sameness.py: "), got.stderr
    assert "Traceback" not in got.stderr


def test_except_without_claims_is_an_argument_error(tmp_path) -> None:
    """F4."""
    a = tmp_path / "a.json"
    a.write_text(json.dumps(local()))
    got = subprocess.run(
        [sys.executable, SCRIPT, "--except", "092", str(a), str(a)], capture_output=True, text=True
    )
    assert got.returncode == 2 and "--except" in got.stderr, got.stderr


def test_a_read_only_files_block_on_windows_alone_is_no_difference() -> None:
    """Spec 094's need joins F1's exception through gather.CI_NEEDS, on Windows only."""
    records = shard_records()
    records[("windows", "own")]["checks"][A].update(status="blocked", need="read-only files")
    assert sameness.differences(release(records), local()) == []
    records[("linux", "own")]["checks"][A].update(status="blocked", need="read-only files")
    assert sameness.differences(release(records), local()) == [
        f"{A}: status 'pass' on {DARWIN}, 'blocked' on {LINUX}"
    ]
