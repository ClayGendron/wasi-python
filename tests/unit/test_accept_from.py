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


def test_10_growth_is_cleared_by_grows_with_its_growth(inputs) -> None:
    inputs.record["checks"][TOOLS]["metrics"] = {"fuel": 120}
    assert "unclaimed" in refused(inputs) and f"{TOOLS}: fuel 100 -> 120" in refused(inputs)
    inputs.claims = [claim(grows=["tests/checks/test_v1_4_*"], growth="the tool table is larger")]
    a = accept_from.accept(inputs)
    assert json.loads(a.line)["growth_reason"] == "999: the tool table is larger"
    assert a.accepted["checks"][TOOLS]["metrics"][DARWIN]["fuel"] == 120


def test_11_a_fall_in_a_pass_count_is_cleared_by_passes_with_its_reason(inputs) -> None:
    inputs.record["checks"][GROUP]["metrics"] = {"passes": 8, "fuel": 913}
    assert "fell" in refused(inputs)
    inputs.claims = [claim(passes=[GROUP])]  # named, with no reason for the fall
    assert "fell" in refused(inputs)
    inputs.claims = [claim(passes=[GROUP], fewer="two tests moved to the release tier")]
    a = accept_from.accept(inputs)
    assert json.loads(a.line)["fewer_reason"] == "999: two tests moved to the release tier"
    assert a.accepted["checks"][GROUP]["metrics"][DARWIN]["passes"] == 8


def test_12_a_judge_file_changed_is_cleared_by_judge(inputs) -> None:
    inputs.judge = {"hash": "k" * 64, "files": {"tests/harness/plugin.py": "2" * 64}}
    inputs.record["meta"]["judge"]["hash"] = "k" * 64
    assert "judge" in refused(inputs) and "tests/harness/plugin.py" in refused(inputs)
    inputs.claims = [claim(judge={"tests/harness/plugin.py": "it reads the record"})]
    a = accept_from.accept(inputs)
    assert json.loads(a.line)["judge_reason"] == "999: tests/harness/plugin.py: it reads the record"


def test_12_the_records_judge_must_be_this_checkouts(inputs) -> None:
    inputs.record["meta"]["judge"]["hash"] = "k" * 64
    assert "judge hash" in refused(inputs)


def test_13_a_tier_move_is_cleared_by_moved(inputs) -> None:
    inputs.record["release_checks"] = [GROUP]
    for entry in (inputs.record["checks"][GROUP], inputs.record["checks"][GROUP]["source"]):
        entry.update(status="deselected", reason="release tier")
    inputs.record["deselected"] = [GROUP]
    assert "moved between tiers" in refused(inputs)
    inputs.claims = [claim(moved={GROUP: "its tests are slow"})]
    a = accept_from.accept(inputs)
    assert a.accepted["checks"][GROUP]["tier"] == "release"
    assert json.loads(a.line)["tier_move_reason"] == "999: its tests are slow"


def test_14_a_history_that_does_not_replay_is_refused(inputs) -> None:
    inputs.history_errors = ["history line 1: prev does not hash line 0"]
    assert "history" in refused(inputs)


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

### Changed

- **Change {n}**: it moved.

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


def test_the_release_records_claims_are_the_ledgers_too(tmp_path: Path) -> None:
    """The news files that claimed a release-tier row were assembled and removed by bump before
    the release pull request, so its acceptance also reads the release-tier ledger: the blocks
    still in it and the ones the date moved under this version."""
    (tmp_path / "src" / "wasi_python").mkdir(parents=True)
    (tmp_path / "src" / "wasi_python" / "__init__.py").write_text('__version__ = "0.1.1"\n')
    (tmp_path / "context").mkdir()
    (tmp_path / news.LEDGER).write_text('[[claim]]\nspec = "140"\ngrows = ["x"]\ngrowth = "y"\n')
    (tmp_path / news.LEDGER_HISTORY).write_text("# history\n")
    release = {"meta": {"event": "pull_request", "base_ref": "main"}}
    merge = {"meta": {"event": "push", "ref": "refs/heads/dev"}}
    assert [c.spec for c in accept_from.release_claims(release, tmp_path)] == ["140"]
    assert accept_from.release_claims(merge, tmp_path) == []
