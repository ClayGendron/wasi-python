"""The acceptance from CI's record: `uv run pytest --accept-from <record.json> --claims <news>`.

Each refusal of the local acceptance in the form it takes for a gather's merged record, a row
each; the reasons drawn from the news files' claims; what the history line and the commit message
say. Every row uses fixtures: no row reads or writes the repository's accepted state."""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from harness import accept_from, history, news, paths, scoreboard

HEAD = "c" * 40
BASE = "b" * 40
W = "a" * 64  # python.wasm
S = "5" * 64  # the set's own SHA256SUMS
WT = "49.0.0"
DARWIN, LINUX, WINDOWS = "darwin-arm64", "linux-x86_64", "win32-amd64"
JUDGE = {"hash": "j" * 64, "files": {"tests/harness/plugin.py": "1" * 64}}
PROBE = history.PROBE
RULE = "tests/checks/test_rules.py::test_a_rule"
TOOLS = "tests/checks/test_v1_4_tools.py::test_tools"
GROUP = f"{scoreboard.UPSTREAM_FILE}::test_upstream_suite[g1]"
GOAL = sorted([PROBE, RULE, TOOLS, GROUP])
AREAS = {PROBE: "v1.2", RULE: "rules", TOOLS: "v1.4", GROUP: "v1.3"}
# What each check measured, and where: the upstream group runs on Linux alone.
MEASURED = {
    PROBE: (DARWIN, {"fuel": 7}),
    RULE: (DARWIN, {}),
    TOOLS: (DARWIN, {"fuel": 100}),
    GROUP: (LINUX, {"passes": 10, "fuel": 913}),
}
RUN_KEYS = ("macos/own", "linux/own", "linux/up", "windows/own")
PLATFORM_OF = {"macos": DARWIN, "linux": LINUX, "windows": WINDOWS}


def _record() -> dict:
    """A green post-merge gather's merged record of HEAD, in gather.merge's shape."""
    checks = {}
    for node in GOAL:
        platform, metrics = MEASURED[node]
        entry = {"area": AREAS[node], "status": "pass", "reason": "", "need": None}
        checks[node] = {
            **entry,
            "metrics": dict(metrics),
            "source": {**entry, "platform": platform},
            "worst_platform": platform,
        }
    runs = {
        key: {
            "platform": PLATFORM_OF[key.split("/")[0]],
            "suite": {"passed": 1, "skipped": 0, "total": 1},
            "commit": HEAD,
            "dirty": False,
            "overrides": ["--progress-latest /tmp/r/latest.json"],
            "foreign": [],
            "probe": "pass",
        }
        for key in RUN_KEYS
    }
    return {
        "meta": {
            "commit": HEAD,
            "artifact": W,
            "set_sums": S,
            "judge": {"hash": JUDGE["hash"]},
            "records": sorted(RUN_KEYS),
            "tag": False,
            "set_source": "reused wasi-python-set-0123",
            "tier": "normal",
            "foreign": [],
            "event": "push",
            "ref": "refs/heads/dev",
            "base_ref": "",
            "selected": None,
            "red": [],
        },
        "checks": checks,
        "deselected": [],
        "release_checks": [],
        "collected_files": sorted({n.split("::")[0] for n in GOAL}),
        "suite": {},
        "runs": runs,
    }


def _start() -> tuple[dict, str]:
    """The accepted state before the merge: a local darwin acceptance of BASE."""
    checks = {}
    for node in GOAL:
        metrics = {"fuel": 7} if node == PROBE else {"fuel": 100} if node == TOOLS else {}
        if node == GROUP:
            metrics = {"passes": 10, "fuel": 500}
        checks[node] = {"area": AREAS[node], "status": "pass", "reason": "", "need": None}
        checks[node]["metrics"] = metrics
    run = {
        "meta": {
            "at": "2026-10-25T00:00:00Z",
            "commit": BASE,
            "dirty": False,
            "platform": DARWIN,
            "host": "h",
            "wasmtime": WT,
            "artifact": W,
            "set_sums": S,
            "judge": copy.deepcopy(JUDGE),
            "tier": "normal",
        },
        "checks": checks,
        "deselected": [],
        "release_checks": [],
        "collected_files": sorted({n.split("::")[0] for n in GOAL}),
        "suite": {},
    }
    return scoreboard.accept(
        run, None, [], scoreboard.compare(run, None), green=True, reason="start"
    )


@pytest.fixture
def inputs(tmp_path: Path) -> accept_from.Inputs:
    accepted, line = _start()
    return accept_from.Inputs(
        record=_record(),
        accepted=accepted,
        history_lines=[line],
        history_errors=[],
        goal_nodes=list(GOAL),
        head=HEAD,
        subject="A change (#12)",
        judge=copy.deepcopy(JUDGE),
        wasmtime=WT,
        claims=[],
        at="2026-10-26T00:00:00Z",
        host="ci",
        record_sha256="d" * 64,
        repo=tmp_path,
    )


def refused(i: accept_from.Inputs) -> str:
    with pytest.raises(accept_from.Refused) as e:
        accept_from.accept(i)
    return str(e.value)


def claim(**fields) -> news.Claim:
    return news.Claim(spec="999", **fields)


# ---------------------------------------------------------------------------------------------
# A green record of the checked-out commit is accepted


def test_a_green_post_merge_record_is_accepted_onto_its_commit(inputs) -> None:
    a = accept_from.accept(inputs)
    line = json.loads(a.line)
    assert line["commit"] == HEAD and line["dirty"] is False and line["n"] == 2
    assert line["artifact"] == W and line["set_sums"] == S and line["tier"] == "normal"
    assert line["platform"] == DARWIN and line["platforms"] == sorted([DARWIN, LINUX, WINDOWS])
    assert line["record"] == "d" * 64 and line["source"] == "ci"
    assert a.accepted["commit"] == HEAD and a.accepted["judge"] == JUDGE
    assert {c["commit"] for c in a.accepted["checks"].values()} == {HEAD}


SKIP_WORDS = ("[skip ci]", "[ci skip]", "[no ci]", "[skip actions]", "[actions skip]")


def test_the_commit_message_names_the_merge_and_carries_no_skip_word(inputs) -> None:
    """The acceptance commit starts a run whose plan is quiet; a skip word would also skip a
    release pull request whose head it is."""
    inputs.claims = [claim(grows=[TOOLS], growth="the tool table is larger")]
    inputs.record["checks"][TOOLS]["metrics"] = {"fuel": 120}
    a = accept_from.accept(inputs)
    first, *rest = a.message.splitlines()
    assert first == "Accepted: A change (#12)"
    assert "growth: 999: the tool table is larger" in rest
    assert not any(word in a.message.lower() for word in SKIP_WORDS)


def test_the_three_systems_need_is_met_by_the_records_platforms(inputs, tmp_path) -> None:
    """The record's probe passed on three systems; the history line names them, so the need is
    met on the next local run of the same bytes."""
    a = accept_from.accept(inputs)
    folder = tmp_path / "progress"
    folder.mkdir()
    (folder / "history.jsonl").write_text(inputs.history_lines[0] + "\n" + a.line + "\n")
    assert history.systems_that_passed(folder, W) == {"darwin", "linux", "win32"}


def test_darwin_fuel_is_keyed_darwin_and_linux_fuel_is_not_ratcheted(inputs) -> None:
    """The record is read as the darwin run it contains: a check darwin ran keeps darwin's fuel;
    the upstream group, run on Linux alone, keeps darwin's accepted fuel and takes the record's
    pass count, which the gather holds equal on every system."""
    inputs.record["checks"][GROUP]["metrics"] = {"passes": 11, "fuel": 99999}
    a = accept_from.accept(inputs)
    group = a.accepted["checks"][GROUP]["metrics"]
    assert set(group) == {DARWIN}
    assert group[DARWIN]["fuel"] == 500 and group[DARWIN]["passes"] == 11
    assert a.accepted["checks"][TOOLS]["metrics"][DARWIN]["fuel"] == 100


def test_the_ignores_count_is_taken_from_the_record(inputs) -> None:
    """The count of the type checker's escapes is source text, held equal on every system: a
    record that measured it on Linux alone is applied over darwin's accepted count, so a fall
    measured anywhere is accepted."""
    inputs.accepted["checks"][RULE]["metrics"] = {DARWIN: {"wasmtime": WT, "ignores": 25}}
    inputs.record["checks"][RULE]["metrics"] = {"ignores": 3}
    inputs.record["checks"][RULE]["source"]["platform"] = LINUX
    inputs.record["checks"][RULE]["worst_platform"] = LINUX
    a = accept_from.accept(inputs)
    assert a.accepted["checks"][RULE]["metrics"][DARWIN]["ignores"] == 3


def _group_entry(inputs, **fields) -> dict:
    """The upstream group's accepted darwin entry, edited."""
    entry = inputs.accepted["checks"][GROUP]["metrics"][DARWIN]
    entry.update(fields)
    for name in [k for k, v in entry.items() if v is None]:
        del entry[name]
    return entry


@pytest.mark.parametrize("before", ["another engine", "none recorded"])
def test_a_check_only_linux_ran_takes_linuxs_fuel_when_none_is_of_this_engine(
    inputs, before
) -> None:
    """When no fuel darwin measured under this wasmtime is accepted, Linux's is recorded, labelled
    with the system that measured it, so an engine move leaves the group a fuel and needs no
    claim."""
    _group_entry(inputs, wasmtime="48.0.0" if before == "another engine" else WT)
    if before == "none recorded":
        _group_entry(inputs, fuel=None)
    a = accept_from.accept(inputs)
    assert a.reasons == []
    assert a.accepted["checks"][GROUP]["metrics"] == {
        DARWIN: {"wasmtime": WT, "passes": 10, "fuel": 913, "fuel_platform": LINUX}
    }


def test_linux_first_fuel_keeps_the_lower_and_is_never_a_growth(inputs) -> None:
    """Linux's fuel moves between runs, so it is never compared, and within one system the lower
    is kept."""
    _group_entry(inputs, fuel=500, fuel_platform=LINUX)
    for measured, kept in ((600, 500), (400, 400)):
        inputs.record["checks"][GROUP]["metrics"] = {"passes": 10, "fuel": measured}
        a = accept_from.accept(inputs)
        assert a.reasons == []
        group = a.accepted["checks"][GROUP]["metrics"][DARWIN]
        assert group["fuel"] == kept and group["fuel_platform"] == LINUX


def test_darwin_fuel_replaces_another_systems_without_a_claim(inputs) -> None:
    """The first fuel darwin measures under this engine takes over from Linux's, whole, and the
    row is compared darwin to darwin from then on."""
    inputs.accepted["checks"][TOOLS]["metrics"][DARWIN].update(fuel=100, fuel_platform=LINUX)
    inputs.record["checks"][TOOLS]["metrics"] = {"fuel": 200}
    a = accept_from.accept(inputs)
    assert a.reasons == []
    assert a.accepted["checks"][TOOLS]["metrics"][DARWIN] == {"wasmtime": WT, "fuel": 200}


# ---------------------------------------------------------------------------------------------
# The local acceptance's refusals, each in its form for CI's record


def test_1_a_linked_worktree_is_no_refusal(inputs, monkeypatch) -> None:
    """CI's checkout is a fresh clone and the record, not the tree, carries what was judged."""
    monkeypatch.setattr(paths, "linked_worktree", lambda repo=None: True)
    assert accept_from.accept(inputs).line


def test_2_a_dirty_tree_is_refused(inputs) -> None:
    inputs.dirty = "src/wasi_python/runner.py"
    assert "dirty" in refused(inputs) and "src/wasi_python/runner.py" in refused(inputs)


@pytest.mark.parametrize("where", ["the record", "a shard"])
def test_3_a_record_of_another_commit_is_refused(inputs, where) -> None:
    if where == "the record":
        inputs.record["meta"]["commit"] = BASE
    else:
        inputs.record["runs"]["windows/own"]["commit"] = BASE
    assert "HEAD" in refused(inputs)


def test_4_an_empty_collection_or_another_one_is_refused(inputs) -> None:
    inputs.goal_nodes = []
    assert "collected no goal check" in refused(inputs)
    inputs.goal_nodes = [*GOAL, "tests/checks/test_rules.py::test_new"]
    assert "not this commit's collection" in refused(inputs)


def test_5_a_shard_is_refused(inputs) -> None:
    inputs.options = ("--shard",)
    assert "--shard" in refused(inputs)


@pytest.mark.parametrize(
    "edit, words",
    [
        (lambda r: r["meta"].update(red=["G4 linux/own: 1 unit test(s) failed"]), "red line"),
        (lambda r: r["meta"].pop("red"), "no verdict"),
        (lambda r: r["meta"].update(foreign=["plugin x"]), "outside the judge"),
        (lambda r: r["runs"]["linux/up"].update(foreign=["plugin x"]), "outside the judge"),
        (lambda r: r["runs"]["linux/up"].update(dirty=True), "dirty"),
        (
            lambda r: r["runs"]["linux/up"].update(
                overrides=["--progress-latest x", "--known-gaps y"]
            ),
            "--progress-latest",
        ),
    ],
    ids=["red", "no verdict", "foreign", "a shard's foreign", "a dirty shard", "an override"],
)
def test_6_a_record_that_is_not_green_is_refused(inputs, edit, words) -> None:
    edit(inputs.record)
    assert words in refused(inputs)


def test_7_a_lost_pass_is_refused_and_no_claim_clears_it(inputs) -> None:
    inputs.record["checks"][TOOLS]["source"]["status"] = "fail"
    inputs.record["checks"][TOOLS]["status"] = "fail"
    inputs.claims = [claim(changed=[TOOLS], grows=[TOOLS], growth="x", retired=[TOOLS])]
    assert "lost" in refused(inputs) and TOOLS in refused(inputs)


def _drop(i: accept_from.Inputs, node: str) -> None:
    del i.record["checks"][node]
    i.goal_nodes.remove(node)


def test_8_an_absent_check_is_retired_only_by_a_claim(inputs) -> None:
    _drop(inputs, RULE)
    assert "absent" in refused(inputs) and RULE in refused(inputs)
    inputs.claims = [claim(retired=[RULE])]
    a = accept_from.accept(inputs)
    assert RULE not in a.accepted["checks"] and json.loads(a.line)["retired"] == [RULE]


def test_8_a_retired_claim_that_is_not_absent_is_refused(inputs) -> None:
    inputs.claims = [claim(retired=[TOOLS])]
    assert "not absent" in refused(inputs) and TOOLS in refused(inputs)


@pytest.mark.parametrize("need", ["artifact dir", "upstream kit"], ids=["protected", "upstream"])
def test_9_a_blocked_accepted_pass_is_always_refused(inputs, need) -> None:
    node = TOOLS if need == "artifact dir" else GROUP
    for entry in (inputs.record["checks"][node], inputs.record["checks"][node]["source"]):
        entry.update(status="blocked", need=need, reason=f"needs {need}")
    inputs.claims = [claim(changed=[node], retired=[node], grows=[node], growth="x")]
    assert "blocked" in refused(inputs) or "did not run" in refused(inputs)


def _release(i: accept_from.Inputs) -> None:
    """The record is the release pull request's into main, whose own rows still need a claim."""
    i.record["meta"].update(event="pull_request", ref="refs/pull/9/merge", base_ref="main")
    i.record["meta"]["set_source"] = "built"


def test_10_growth_is_cleared_by_grows_with_its_growth(inputs) -> None:
    _release(inputs)
    inputs.record["checks"][TOOLS]["metrics"] = {"fuel": 120}
    assert "unclaimed" in refused(inputs) and f"{TOOLS}: fuel 100 -> 120" in refused(inputs)
    inputs.claims = [claim(grows=["tests/checks/test_v1_4_*"], growth="the tool table is larger")]
    a = accept_from.accept(inputs)
    assert json.loads(a.line)["growth_reason"] == "999: the tool table is larger"
    assert a.accepted["checks"][TOOLS]["metrics"][DARWIN]["fuel"] == 120


def test_11_a_fall_in_a_pass_count_is_cleared_by_passes_with_its_reason(inputs) -> None:
    _release(inputs)
    inputs.record["checks"][GROUP]["metrics"] = {"passes": 8, "fuel": 913}
    assert "fell" in refused(inputs)
    inputs.claims = [claim(passes=[GROUP])]  # named, with no reason for the fall
    assert "fell" in refused(inputs)
    inputs.claims = [claim(passes=[GROUP], fewer="two tests moved to the release tier")]
    a = accept_from.accept(inputs)
    assert json.loads(a.line)["fewer_reason"] == "999: two tests moved to the release tier"
    assert a.accepted["checks"][GROUP]["metrics"][DARWIN]["passes"] == 8


def test_12_a_judge_change_that_moves_no_verdict_needs_no_claim(inputs) -> None:
    """Only a verdict-bearing judge file needs a reason; the judge's hash in the history records
    every other change, and a `judge` claim for such a file is ignored, not passed on."""
    inputs.judge = {"hash": "k" * 64, "files": {"tests/harness/plugin.py": "2" * 64}}
    inputs.record["meta"]["judge"]["hash"] = "k" * 64
    a = accept_from.accept(inputs)
    line = json.loads(a.line)
    assert line["judge_reason"] is None and line["judge_changed"] == ["tests/harness/plugin.py"]
    inputs.claims = [claim(judge={"tests/harness/plugin.py": "it reads the record"})]
    assert json.loads(accept_from.accept(inputs).line)["judge_reason"] is None


def test_12_a_verdict_bearing_judge_file_is_cleared_by_judge(inputs) -> None:
    _release(inputs)
    files = {"tests/harness/plugin.py": "1" * 64, "tests/known_gaps.toml": "2" * 64}
    inputs.judge = {"hash": "k" * 64, "files": files}
    inputs.record["meta"]["judge"]["hash"] = "k" * 64
    why = refused(inputs)
    assert "judge" in why and "tests/known_gaps.toml" in why, why
    inputs.claims = [claim(judge={"tests/known_gaps.toml": "a new allowance"})]
    a = accept_from.accept(inputs)
    assert json.loads(a.line)["judge_reason"] == "999: tests/known_gaps.toml: a new allowance"


def test_12_the_records_judge_must_be_this_checkouts(inputs) -> None:
    inputs.record["meta"]["judge"]["hash"] = "k" * 64
    assert "judge hash" in refused(inputs)


def test_13_a_tier_move_is_cleared_by_moved(inputs) -> None:
    _release(inputs)
    inputs.record["release_checks"] = [GROUP]
    for entry in (inputs.record["checks"][GROUP], inputs.record["checks"][GROUP]["source"]):
        entry.update(status="deselected", reason="release tier")
    inputs.record["deselected"] = [GROUP]
    assert "moved between tiers" in refused(inputs)
    inputs.claims = [claim(moved={GROUP: "its tests are slow"})]
    a = accept_from.accept(inputs)
    assert a.accepted["checks"][GROUP]["tier"] == "release"
    assert json.loads(a.line)["tier_move_reason"] == "999: its tests are slow"


def test_a_check_the_record_did_not_select_keeps_its_accepted_row_and_its_pass(inputs) -> None:
    """A merge's run judges no build shard: its checks ran in no record, which the gather allows
    as not selected. The acceptance keeps their accepted rows, and their passes stay in the
    history's passed set, as a normal run keeps the release tier's."""
    before = copy.deepcopy(inputs.accepted["checks"][TOOLS])
    start = json.loads(inputs.history_lines[-1])
    inputs.record["checks"][TOOLS] = {
        "area": AREAS[TOOLS],
        "status": "deselected",
        "reason": "",
        "need": None,
        "metrics": {},
        "worst_platform": DARWIN,
    }
    inputs.record["deselected"] = [TOOLS]
    a = accept_from.accept(inputs)
    assert a.accepted["checks"][TOOLS] == before
    line = json.loads(a.line)
    assert line["passed_removed"] == []
    assert line["counts"] == start["counts"]


def test_14_a_history_that_does_not_replay_is_refused(inputs) -> None:
    inputs.history_errors = ["history line 1: prev does not hash line 0"]
    assert "history" in refused(inputs)


# ---------------------------------------------------------------------------------------------
# On dev an unclaimed row is recorded, not refused; the release reconciles it


def _grow(i: accept_from.Inputs) -> None:
    i.record["checks"][TOOLS]["metrics"] = {"fuel": 120}


def _fall(i: accept_from.Inputs) -> None:
    i.record["checks"][GROUP]["metrics"] = {"passes": 8, "fuel": 913}


def _move(i: accept_from.Inputs) -> None:
    i.record["release_checks"] = [GROUP]
    for entry in (i.record["checks"][GROUP], i.record["checks"][GROUP]["source"]):
        entry.update(status="deselected", reason="release tier")
    i.record["deselected"] = [GROUP]


def _judge(i: accept_from.Inputs) -> None:
    i.judge = {"hash": "k" * 64, "files": {**JUDGE["files"], "tests/known_gaps.toml": "2" * 64}}
    i.record["meta"]["judge"]["hash"] = "k" * 64


GREW = {"kind": "grows", "check": TOOLS, "metric": "fuel", "old": 100, "new": 120}
FELL = {"kind": "passes", "check": GROUP, "metric": "passes", "old": 10, "new": 8}
MOVED = {"kind": "moved", "check": GROUP, "old": "normal", "new": "release"}
JUDGED = {"kind": "judge", "file": "tests/known_gaps.toml", "old": None, "new": "2" * 64}


@pytest.mark.parametrize(
    ("edit", "row"),
    [(_grow, GREW), (_fall, FELL), (_move, MOVED), (_judge, JUDGED)],
    ids=["a growth", "a fall in passes", "a tier move", "a verdict-bearing judge file"],
)
def test_on_dev_an_unclaimed_row_is_accepted_and_written_unclaimed(inputs, edit, row) -> None:
    """A merge is accepted when its run is green: a row no claim gives a reason for is written
    into the history line, with its values, for the release to reconcile, and accepted.json takes
    the new value as a claimed row's would."""
    edit(inputs)
    a = accept_from.accept(inputs)
    line = json.loads(a.line)
    assert line["schema"] == 3 and line["event"] == "push"
    assert line["unclaimed"] == [row]
    checks = a.accepted["checks"]
    if row is GREW:
        assert checks[TOOLS]["metrics"][DARWIN]["fuel"] == 120
    elif row is FELL:
        assert checks[GROUP]["metrics"][DARWIN]["passes"] == 8
    elif row is MOVED:
        assert checks[GROUP]["tier"] == "release"
    else:
        assert a.accepted["judge"]["files"]["tests/known_gaps.toml"] == "2" * 64
    assert any(r.startswith("unclaimed: ") for r in a.reasons), a.reasons


def test_on_dev_a_claimed_row_writes_no_unclaimed_row(inputs) -> None:
    _grow(inputs)
    inputs.claims = [claim(grows=[TOOLS], growth="the tool table is larger")]
    line = json.loads(accept_from.accept(inputs).line)
    assert line["unclaimed"] == [] and line["growth_reason"] == "999: the tool table is larger"


def test_on_dev_a_lost_pass_and_an_unretired_absent_check_are_still_refused(inputs) -> None:
    """Those are losses, not growth: no line records them, and no claim but `retired` clears the
    absent check."""
    inputs.record["checks"][TOOLS]["source"]["status"] = "fail"
    inputs.record["checks"][TOOLS]["status"] = "fail"
    assert "lost" in refused(inputs) and TOOLS in refused(inputs)
    inputs.record["checks"][TOOLS]["source"]["status"] = "pass"
    inputs.record["checks"][TOOLS]["status"] = "pass"
    _drop(inputs, RULE)
    assert "absent, and no claim retires it" in refused(inputs) and RULE in refused(inputs)


def _accepted_on_dev(i: accept_from.Inputs, edit=_grow) -> accept_from.Inputs:
    """The inputs of the next acceptance, after `edit`'s row was accepted unclaimed on dev."""
    edit(i)
    a = accept_from.accept(i)
    i.accepted, i.history_lines = a.accepted, [*i.history_lines, a.line]
    return i


def test_the_release_is_refused_while_a_row_accepted_unclaimed_has_no_claim(inputs) -> None:
    """The refusal names the row, the line that wrote it and the ledger that would clear it."""
    _release(_accepted_on_dev(inputs))
    why = refused(inputs)
    assert "history line 2" in why and TOOLS in why and "fuel 100 -> 120" in why, why
    assert f"{news.LEDGER}/NNN-<slug>.toml" in why and news.LEDGER == "context/release-claims"


def test_a_ledger_claim_clears_a_row_accepted_unclaimed(inputs, tmp_path) -> None:
    _release(_accepted_on_dev(inputs))
    (tmp_path / news.LEDGER).mkdir(parents=True)
    (tmp_path / news.LEDGER / "999-the-table.toml").write_text(
        '[[claim]]\nspec = "999"\ngrows = ["' + TOOLS + '"]\ngrowth = "the table grew"\n'
    )
    inputs.claims = news.ledger_claims(tmp_path)
    line = json.loads(accept_from.accept(inputs).line)
    assert line["event"] == "pull_request" and line["unclaimed"] == []


@pytest.mark.parametrize(
    ("edit", "kind", "claimed"),
    [
        (_fall, "passes", claim(passes=[GROUP], fewer="two tests moved")),
        (_move, "moved", claim(moved={GROUP: "its tests are slow"})),
        (_judge, "judge", claim(judge={"tests/known_gaps.toml": "a new allowance"})),
    ],
    ids=["a fall in passes", "a tier move", "a verdict-bearing judge file"],
)
def test_each_kind_of_unclaimed_row_is_reconciled_by_its_own_claim(inputs, edit, kind, claimed):
    _release(_accepted_on_dev(inputs, edit))
    assert f"{kind} " in refused(inputs)
    inputs.claims = [claimed]
    assert accept_from.accept(inputs).line


def test_a_row_accepted_unclaimed_before_the_last_release_is_not_asked_again(inputs) -> None:
    _release(_accepted_on_dev(inputs))
    inputs.claims = [claim(grows=[TOOLS], growth="the tool table is larger")]
    a = accept_from.accept(inputs)
    inputs.accepted, inputs.history_lines = a.accepted, [*inputs.history_lines, a.line]
    inputs.claims = []
    assert accept_from.accept(inputs).line  # the next release: nothing since the last one


def test_the_last_release_is_the_newest_line_of_a_release_pull_request() -> None:
    """A line from before the event key was written marks a release by CI's source and the
    release tier; the start of history stands in when no release was accepted."""
    rows = [{"kind": "grows", "check": "a", "metric": "fuel", "old": 1, "new": 2}]
    lines = [
        json.dumps({"n": 1, "commit": "1", "source": "ci", "tier": "release"}),
        json.dumps({"n": 2, "commit": "2", "schema": 3, "event": "push", "unclaimed": rows}),
        json.dumps({"n": 3, "commit": "3", "schema": 3, "event": "pull_request", "unclaimed": []}),
        json.dumps({"n": 4, "commit": "4", "schema": 3, "event": "push", "unclaimed": rows}),
    ]
    assert accept_from.since_release(lines) == ([(4, rows[0])], "3")
    assert accept_from.since_release(lines[:3]) == ([], "3")
    assert accept_from.since_release(lines[:2]) == ([(2, rows[0])], "1")
    assert accept_from.since_release(lines[1:2]) == ([(2, rows[0])], None)


# ---------------------------------------------------------------------------------------------
# What else the record must be


@pytest.mark.parametrize(
    "meta",
    [
        {"event": "pull_request", "ref": "refs/pull/7/merge", "base_ref": "dev"},
        {"event": "push", "ref": "refs/tags/v0.1.1", "tag": True},
        {"event": "workflow_dispatch", "ref": "refs/heads/dev"},
        {"event": "schedule", "ref": "refs/heads/dev"},
    ],
    ids=["a pull request into dev", "a tag", "a dispatch", "the weekly run"],
)
def test_only_a_merge_into_dev_or_a_release_pull_request_is_accepted(inputs, meta) -> None:
    inputs.record["meta"].update(meta)
    assert "only a push to dev or a release pull request" in refused(inputs)


def test_a_release_pull_requests_record_is_accepted(inputs) -> None:
    inputs.record["meta"].update(event="pull_request", ref="refs/pull/9/merge", base_ref="main")
    inputs.record["meta"]["set_source"] = "built"
    assert accept_from.accept(inputs).line


@pytest.mark.parametrize("source", ["", "reused", "cached somewhere"])
def test_a_set_neither_built_nor_reused_by_its_key_is_refused(inputs, source) -> None:
    inputs.record["meta"]["set_source"] = source
    assert "set_source" in refused(inputs)


def test_a_file_that_is_not_a_merged_record_is_refused(inputs) -> None:
    del inputs.record["runs"]
    assert "merged record" in refused(inputs)


@pytest.mark.parametrize(
    "option", ["--accept", "--partial", "--retire", "--accept-growth", "--tier"]
)
def test_every_reason_comes_from_the_news_files_not_a_flag(inputs, option) -> None:
    inputs.options = (option,)
    assert option in refused(inputs)


def test_every_refusal_is_named_at_once(inputs) -> None:
    inputs.dirty = "src/x.py"
    inputs.record["meta"]["red"] = ["G1 x"]
    text = refused(inputs)
    assert "dirty" in text and "red line" in text


# ---------------------------------------------------------------------------------------------
# Which news files give the reasons: those changed since the last acceptance


@pytest.fixture
def repo(tmp_path, monkeypatch) -> Path:
    git = shutil.which("git")
    if git is None:
        pytest.skip("needs: git")
    config = tmp_path / "gitconfig"
    config.write_text("[user]\n\tname = t\n\temail = t@t\n[commit]\n\tgpgsign = false\n")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    path = tmp_path / "repo"
    subprocess.run([git, "init", "-q", "-b", "dev", str(path)], check=True)
    return path


NEWS = """# {n}: a change

## Changelog

### For contributors

- **Change {n} moves.** It moved. [The release process](https://claygendron.github.io/wasi-python/contributing/release-process/)

## Claims

```toml
[[claim]]
spec = "{n}"
growth = "{n} grew"
grows = ["x"]
```
"""


def _commit(repo: Path, message: str) -> str:
    def run(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
        ).stdout.strip()

    run("add", "-A")
    run("commit", "-q", "--allow-empty", "-m", message)
    return run("rev-parse", "HEAD")


def test_the_reasons_are_the_news_files_changed_since_the_last_acceptance(repo) -> None:
    changes = repo / "context" / "changes"
    changes.mkdir(parents=True)
    (changes / "README.md").write_text("# the folder\n")
    (changes / "100-old.md").write_text(NEWS.format(n="100"))
    accepted_at = _commit(repo, "the last accepted merge")
    (changes / "200-new.md").write_text(NEWS.format(n="200"))
    _commit(repo, "a merge since")
    got = accept_from.news_since(repo, accepted_at, changes)
    assert [c.spec for c in got] == ["200"]
    assert accept_from.news_since(repo, None, changes)[0].spec == "100"  # no acceptance yet: all


def test_a_last_acceptance_outside_this_history_is_refused(repo) -> None:
    changes = repo / "context" / "changes"
    changes.mkdir(parents=True)
    _commit(repo, "start")
    with pytest.raises(accept_from.Refused, match="not in this commit's history"):
        accept_from.news_since(repo, "e" * 40, changes)


# ---------------------------------------------------------------------------------------------
# The command: pytest answers --accept-from before any session, and runs no check


def _progress(tmp_path: Path) -> Path:
    accepted, line = _start()
    folder = tmp_path / "progress"
    folder.mkdir()
    (folder / "accepted.json").write_text(scoreboard.dumps(accepted))
    (folder / "history.jsonl").write_text(line + "\n")
    return folder


def _wire(monkeypatch, judge: dict) -> None:
    monkeypatch.setattr(accept_from, "_collect", lambda: list(GOAL))
    monkeypatch.setattr(accept_from, "_head", lambda: HEAD)
    monkeypatch.setattr(accept_from, "_subject", lambda: "A change (#12)")
    monkeypatch.setattr(accept_from, "_dirty", lambda: None)
    monkeypatch.setattr(accept_from, "_wasmtime", lambda: WT)
    monkeypatch.setattr(accept_from, "_budget", lambda: None)  # its own rows hold the budget
    monkeypatch.setattr(accept_from, "news_since", lambda repo, since, folder: [])
    monkeypatch.setattr(paths, "judge_files", lambda: judge["files"])
    monkeypatch.setattr(paths, "judge_hash", lambda files: judge["hash"])


def _args(tmp_path: Path, folder: Path, record: Path, *more: str) -> list[str]:
    return [
        "-p",
        "harness.plugin",
        "--accept-from",
        str(record),
        "--claims",
        str(tmp_path / "changes"),
        "--progress-dir",
        str(folder),
        "--progress-latest",
        str(tmp_path / "out" / "latest.json"),
        *more,
    ]


def test_the_command_writes_the_acceptance_and_its_message(pytester, tmp_path, monkeypatch) -> None:
    folder = _progress(tmp_path)
    record = tmp_path / "record.json"
    record.write_text(json.dumps(_record()))
    _wire(monkeypatch, JUDGE)
    pytester.makepyfile(test_never="def test_never():\n    raise SystemExit('a check ran')\n")
    result = pytester.runpytest(*_args(tmp_path, folder, record))
    assert result.ret == 0, result.stdout.str()[-2000:]
    result.stdout.fnmatch_lines([f"accepted: {folder / 'history.jsonl'} line 2"])
    lines = (folder / "history.jsonl").read_text().splitlines()
    assert len(lines) == 2 and json.loads(lines[1])["commit"] == HEAD
    assert json.loads((folder / "accepted.json").read_text())["commit"] == HEAD
    assert not history.errors(
        history.found_in(folder), (folder / "accepted.json").read_text(), None
    )
    message = (tmp_path / "out" / accept_from.MESSAGE_FILE).read_text()
    assert message.startswith("Accepted: A change (#12)\n") and "[skip ci]" not in message


def test_the_command_refuses_and_writes_nothing(pytester, tmp_path, monkeypatch) -> None:
    folder = _progress(tmp_path)
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    record = tmp_path / "record.json"
    red = _record()
    red["meta"]["red"] = ["G4 linux/own: 1 unit test(s) failed"]
    record.write_text(json.dumps(red))
    _wire(monkeypatch, JUDGE)
    result = pytester.runpytest(*_args(tmp_path, folder, record, "--shard", "own-a"))
    assert result.ret == 1
    result.stdout.fnmatch_lines(["RED: --accept-from refused: --shard is refused*", "*red line*"])
    assert {p.name: p.read_bytes() for p in folder.iterdir()} == before
    assert not (tmp_path / "out" / accept_from.MESSAGE_FILE).exists()


def test_the_command_needs_the_news_files_folder(pytester, tmp_path, monkeypatch) -> None:
    folder = _progress(tmp_path)
    record = tmp_path / "record.json"
    record.write_text(json.dumps(_record()))
    _wire(monkeypatch, JUDGE)
    args = [a for a in _args(tmp_path, folder, record) if a != "--claims"]
    args.remove(str(tmp_path / "changes"))
    result = pytester.runpytest(*args)
    assert result.ret == 1
    result.stdout.fnmatch_lines(["*--accept-from takes its reasons from --claims*"])


def test_a_news_folder_outside_the_repository_is_refused(repo, tmp_path) -> None:
    _commit(repo, "start")
    since = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    with pytest.raises(accept_from.Refused, match="not a folder of this repository"):
        accept_from.news_since(repo, since, tmp_path / "elsewhere")


def test_the_release_pull_requests_acceptance_names_the_release() -> None:
    """dev's tip, the release pull request's head, is itself an acceptance, whose subject would
    read twice; the release's acceptance names the version and both tiers instead."""
    release = {"meta": {"event": "pull_request", "base_ref": "main"}}
    merge = {"meta": {"event": "push", "ref": "refs/heads/dev"}}
    assert accept_from.subject_of(merge, "A change (#12)", "0.1.1") == "A change (#12)"
    assert (
        accept_from.subject_of(release, "Accepted: A change (#12)", "0.1.1")
        == "the release pull request of 0.1.1 into main, both tiers"
    )


def test_the_release_records_claims_are_the_ledgers_too(repo: Path) -> None:
    """The release pull request's acceptance also reads the release ledger: the blocks still in
    it and the ones the date moved under this version."""
    (repo / "src" / "wasi_python").mkdir(parents=True)
    (repo / "src" / "wasi_python" / "__init__.py").write_text('__version__ = "0.1.1"\n')
    (repo / news.LEDGER).mkdir(parents=True)
    (repo / news.LEDGER / "140-a-pin.toml").write_text(
        '[[claim]]\nspec = "140"\ngrows = ["x"]\ngrowth = "y"\n'
    )
    (repo / news.LEDGER_HISTORY).write_text("# history\n")
    _commit(repo, "start")
    release = {"meta": {"event": "pull_request", "base_ref": "main"}}
    merge = {"meta": {"event": "push", "ref": "refs/heads/dev"}}
    assert [c.spec for c in accept_from.release_claims(release, repo, [])] == ["140"]
    assert accept_from.release_claims(merge, repo, []) == []


def test_the_release_reads_the_news_files_bump_removed_from_git(repo: Path) -> None:
    """A reason written at the merge still counts at the release: each news file a commit since
    the last release removed (bump, or date for one merged after bump) is read at that commit's
    parent. One removed before the last release is not read, nor is a file of another shape."""
    changes = repo / "context" / "changes"
    changes.mkdir(parents=True)
    (changes / "100-old.md").write_text(NEWS.format(n="100"))
    _commit(repo, "the change before the last release")
    (changes / "100-old.md").unlink()
    released = _commit(repo, "the last release's bump")
    (changes / "200-new.md").write_text(NEWS.format(n="200"))
    (changes / "README.md").write_text("# the folder\n")
    _commit(repo, "a merge since")
    (changes / "300-late.md").write_text(NEWS.format(n="300"))
    _commit(repo, "a merge after the bump")
    (changes / "200-new.md").unlink()
    (changes / "README.md").unlink()
    _commit(repo, "bump")
    (changes / "300-late.md").unlink()
    _commit(repo, "date")
    got = accept_from.removed_news(repo, released)
    assert sorted(c.spec for c in got) == ["200", "300"]
    assert [c.spec for c in accept_from.removed_news(repo, None)] == ["300", "200", "100"]
    line = json.dumps({"n": 1, "commit": released, "schema": 3, "event": "pull_request"})
    release = {"meta": {"event": "pull_request", "base_ref": "main"}}
    specs = [c.spec for c in accept_from.release_claims(release, repo, [line])]
    assert sorted(specs) == ["200", "300"]
    with pytest.raises(accept_from.Refused, match="not in this commit's history"):
        accept_from.removed_news(repo, "e" * 40)


def test_a_news_file_claim_read_from_git_clears_a_row_accepted_unclaimed(inputs, repo) -> None:
    """The row accepted unclaimed on dev, the news file that names it removed by bump: the
    release's acceptance reads the file from git and is cleared by its claim."""
    changes = repo / "context" / "changes"
    changes.mkdir(parents=True)
    (changes / "200-new.md").write_text(NEWS.format(n="200").replace('["x"]', f'["{TOOLS}"]'))
    _commit(repo, "a merge")
    (changes / "200-new.md").unlink()
    _commit(repo, "bump")
    _release(_accepted_on_dev(inputs))
    assert "fuel 100 -> 120" in refused(inputs)
    inputs.claims = accept_from.removed_news(repo, None)
    assert accept_from.accept(inputs).line


def test_a_check_past_its_familys_fuel_cap_is_not_accepted(inputs) -> None:
    """The budget is held at the acceptance too, so a merge that took a check past its cap is
    refused on its own post-merge run, and a listed check is accepted."""
    from harness import budget

    caps = {"test_v1_2_portable_and_sealed": 50, "test_v1_4_tools": 99, "g": 10**6}
    families = {GROUP: "g"}
    inputs.budget = (budget.Budget(60, caps, ()), families, {"150": "drafted"})
    why = refused(inputs)
    assert f"{TOOLS}: fuel 100 is past its family test_v1_4_tools's cap 99" in why, why
    over = (budget.Over(TOOLS, "150", "the tools grew"),)
    inputs.budget = (budget.Budget(60, caps, over), families, {"150": "drafted"})
    assert accept_from.accept(inputs).accepted["checks"][TOOLS]["status"] == "pass"


def test_a_claimed_growth_past_its_cap_is_still_refused(inputs) -> None:
    from harness import budget

    inputs.record["checks"][TOOLS]["metrics"] = {"fuel": 120}
    inputs.claims = [claim(grows=[TOOLS], growth="the tool table is larger")]
    caps = {"test_v1_2_portable_and_sealed": 50, "test_v1_4_tools": 110, "g": 10**6}
    inputs.budget = (budget.Budget(60, caps, ()), {GROUP: "g"}, {"150": "drafted"})
    assert f"{TOOLS}: fuel 120 is past its family test_v1_4_tools's cap 110" in refused(inputs)
