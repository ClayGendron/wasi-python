"""release/ci_plan.py: which jobs a run of the release workflow needs, from the paths it changes.

Each row of the decision table, the two pushes that set every output false, what `full` takes,
the shards each shape selects, and the outputs as the workflow reads them."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys

import pytest

from harness import news, paths, shards

_spec = importlib.util.spec_from_file_location(
    "release_ci_plan", paths.REPO / "release" / "ci_plan.py"
)
ci_plan = importlib.util.module_from_spec(_spec)
sys.modules["release_ci_plan"] = ci_plan  # dataclasses look their module up here
_spec.loader.exec_module(ci_plan)

PR_DEV = ci_plan.Event("pull_request", ref="refs/pull/7/merge", base_ref="dev")
PR_MAIN = ci_plan.Event("pull_request", ref="refs/pull/8/merge", base_ref="main")
PUSH_DEV = ci_plan.Event("push", ref="refs/heads/dev")
TAG = ci_plan.Event("push", ref="refs/tags/v0.1.1")
DISPATCH = ci_plan.Event("workflow_dispatch", ref="refs/heads/spec/138-x")
SCHEDULE = ci_plan.Event("schedule", ref="refs/heads/dev")
PLAN = ci_plan.load_shards(shards.PLAN)


# ---------------------------------------------------------------------------------------------
# The rows of the table: what each path sets


ROWS = [
    ("downloads/SHA256SUMS", {"set"}),
    ("scripts/build.sh", {"set"}),
    ("scripts/steps/apply_patches.sh", {"set"}),
    ("recipes/patches/x.patch", {"set"}),
    ("release/set_key.py", {"set", "workflow"}),
    ("release/build-constraints.txt", {"set", "workflow"}),
    ("tests/harness/constructors.py", {"set", "harness"}),
    ("src/wasi_python/runner.py", {"runner"}),
    ("pyproject.toml", {"runner"}),
    ("uv.lock", {"runner"}),
    ("tests/harness/gather.py", {"harness"}),
    ("tests/conftest.py", {"harness"}),
    ("tests/release_shards.toml", {"harness"}),
    ("tests/known_gaps.toml", {"harness"}),
    ("context/embedders.txt", {"harness"}),
    ("context/release-tier-claims.toml", {"harness"}),
    ("context/upstream/patches/x.md", {"harness"}),
    (".gitattributes", {"harness"}),
    ("tests/upstream/numpy.toml", {"upstream"}),
    ("tests/upstream/expected/numpy.txt", {"upstream"}),
    ("tests/checks/test_v1_3_upstream_suites.py", {"upstream"}),
    (".github/workflows/release.yml", {"workflow"}),
    (".github/actions/verify-artifact/action.yml", {"workflow"}),
    ("release/version.py", {"workflow"}),
    ("release/ci_plan.py", {"workflow"}),
    ("context/progress/accepted.json", {"progress"}),
    ("context/progress/history-00060.jsonl", {"progress"}),
    ("context/changes/138-pull-requests-into-dev.md", {"news"}),
    ("docs/index.md", {"docs"}),
    (".claude/settings.json", {"docs"}),
    ("context/specifications/138-x.md", {"docs"}),
    ("context/reviews/138-x-pr-2026-10-25.md", {"docs"}),
    ("context/changes/notes/deeper.md", {"docs"}),
    ("context/changes/README.md", {"docs"}),
    ("README.md", {"docs"}),
    ("CHANGELOG.md", {"docs"}),
    ("AGENTS.md", {"docs"}),
    ("SECURITY.md", {"docs"}),
    ("LICENSE", {"docs"}),
    ("mkdocs.yml", {"docs"}),
    (".gitignore", {"docs"}),
    # Paths in no row: not docs_only, so the own shards run.
    ("tests/unit/test_x.py", set()),
    ("tests/checks/test_rules.py", set()),
    ("tests/jobs/x.py", set()),
    ("tests/public_api.txt", set()),
    ("fixtures/a.json", set()),
    ("a-new-top-level-file.py", set()),
]


@pytest.mark.parametrize(("path", "flags"), ROWS, ids=[p for p, _ in ROWS])
def test_each_path_sets_its_rows(path, flags) -> None:
    assert ci_plan.classify(path) == frozenset(flags)


def test_every_tracked_path_maps_to_an_output_or_to_docs_only() -> None:
    """A tracked path with no row runs the own shards; only the folders the table names for that
    may hold one, so a new top-level path is placed by a change to the table, never by default."""
    loose = [
        p
        for p in paths.tracked_files()
        if not ci_plan.classify(p) and not p.startswith(ci_plan.OWN_ONLY)
    ]
    assert loose == []


# ---------------------------------------------------------------------------------------------
# The decision: the outputs a run's event and changed paths set


def test_a_docs_only_pull_request_runs_nothing_but_quick() -> None:
    d = ci_plan.decide(["docs/index.md", "context/reviews/x-pr-2026-10-25.md"], PR_DEV)
    assert d.docs_only and not d.full and not d.judge
    sel = ci_plan.select(d, PLAN)
    assert sel == {
        "macos": [],
        "linux": [],
        "windows": [],
        "release": [],
        "build": False,
        "verify": [],
        "selected": [],
    }


def test_an_empty_change_is_docs_only() -> None:
    assert ci_plan.decide([], PR_DEV).docs_only


@pytest.mark.parametrize(
    "path", ["context/changes/138-x.md", "tests/unit/test_x.py", "fixtures/a.json"]
)
def test_a_news_file_or_a_test_is_not_docs_only(path) -> None:
    d = ci_plan.decide(["docs/index.md", path], PR_DEV)
    assert not d.docs_only and d.judge


OWN = [n for n, s in PLAN.items() if s.kind == "own"]
UPSTREAM_LINUX = [n for n, s in PLAN.items() if s.kind == "upstream" and "linux" in s.systems]


def _own_on(system: str) -> list[str]:
    return [n for n in OWN if system in PLAN[n].systems]


def test_a_src_only_pull_request_runs_own_on_three_systems_and_verify_on_linux() -> None:
    d = ci_plan.decide(["src/wasi_python/runner.py"], PR_DEV)
    assert d.runner and not d.full and d.tier == "normal" and not d.rebuild
    sel = ci_plan.select(d, PLAN)
    assert sel["macos"] == _own_on("macos")
    assert sel["linux"] == _own_on("linux")
    assert sel["windows"] == _own_on("windows")
    assert sel["release"] == [] and sel["build"] is False
    assert sel["verify"] == ["ubuntu-24.04"]
    assert not set(sel["linux"]) & set(UPSTREAM_LINUX)


def test_a_test_only_pull_request_leaves_macos_and_the_upstream_groups_out() -> None:
    sel = ci_plan.select(ci_plan.decide(["tests/unit/test_x.py"], PR_DEV), PLAN)
    assert sel["macos"] == []
    assert sel["linux"] == _own_on("linux") and sel["windows"] == _own_on("windows")


def test_an_upstream_only_pull_request_runs_the_groups_on_linux_and_no_macos_leg() -> None:
    d = ci_plan.decide(["tests/upstream/numpy.toml"], PR_DEV)
    assert d.upstream
    sel = ci_plan.select(d, PLAN)
    assert sel["macos"] == []
    assert sel["linux"] == [n for n in PLAN if n in _own_on("linux") or n in UPSTREAM_LINUX]
    assert "upstream-windows" not in sel["windows"]


@pytest.mark.parametrize(
    "path", ["scripts/build.sh", "tests/harness/plugin.py", "downloads/SHA256SUMS"]
)
def test_set_or_harness_runs_macos_and_the_upstream_groups(path) -> None:
    sel = ci_plan.select(ci_plan.decide([path], PR_DEV), PLAN)
    assert sel["macos"] == _own_on("macos")
    assert set(UPSTREAM_LINUX) <= set(sel["linux"])
    assert sel["build"] is False and sel["release"] == []


def test_a_moved_key_sets_set_with_no_path_of_its_own() -> None:
    """The key holds the workflows' env too: a change to an env value moves it, so the decision
    job compares the key at the head with the key at the merge base."""
    assert not ci_plan.decide(["tests/unit/test_x.py"], PR_DEV).set
    d = ci_plan.decide(["tests/unit/test_x.py"], PR_DEV, key_moved=True)
    assert d.set
    assert ci_plan.select(d, PLAN)["macos"] == _own_on("macos")


def _whole(tier: str) -> dict:
    out = {s: shards.on(shards.load(), s) for s in shards.OWN_SYSTEMS}
    out["release"] = shards.on(shards.load(), "release") if tier == "release" else []
    return out


@pytest.mark.parametrize(
    ("changed", "event", "labels", "messages"),
    [
        ([".github/workflows/release.yml"], PR_DEV, (), ()),
        (["release/version.py"], PR_DEV, (), ()),
        (["src/x.py"], PR_DEV, ("ci:full",), ()),
        (["docs/index.md"], PR_DEV, ("ci:full",), ()),
        (["src/x.py"], PR_DEV, (), ("Fix the thing\n\ncitest:full\n",)),
        (["src/x.py"], PUSH_DEV, (), ()),
    ],
    ids=["workflow", "release", "label", "label-on-docs", "commit-line", "push-to-dev"],
)
def test_full_runs_the_merge_grade_set(changed, event, labels, messages) -> None:
    e = ci_plan.Event(event.name, event.ref, event.base_ref, labels, messages)
    d = ci_plan.decide(changed, e)
    assert d.full and d.judge and not d.docs_only and d.tier == "normal" and not d.rebuild
    sel = ci_plan.select(d, PLAN)
    assert {s: sel[s] for s in (*shards.OWN_SYSTEMS, "release")} == _whole("normal")
    assert sel["build"] is True
    assert sel["verify"] == list(ci_plan.VERIFY_RUNNERS)


@pytest.mark.parametrize("message", ["citest:fullness", "say citest:full here", "ci:full"])
def test_only_a_line_of_its_own_asks_for_full(message) -> None:
    e = ci_plan.Event("pull_request", "refs/pull/7/merge", "dev", (), (f"x\n\n{message}\n",))
    assert not ci_plan.decide(["src/x.py"], e).full


def test_another_label_is_not_full() -> None:
    e = ci_plan.Event("pull_request", "refs/pull/7/merge", "dev", ("ci:fuller",), ())
    assert not ci_plan.decide(["src/x.py"], e).full


@pytest.mark.parametrize(
    "event",
    [TAG, PR_MAIN, SCHEDULE, ci_plan.Event("workflow_dispatch", "refs/heads/main")],
    ids=["tag", "release-pull-request", "schedule", "dispatch-on-main"],
)
def test_a_release_shape_judges_both_tiers_and_rebuilds(event) -> None:
    d = ci_plan.decide(None if event is not PR_MAIN else ["src/x.py"], event)
    assert d.full and d.rebuild and d.tier == "release"
    sel = ci_plan.select(d, PLAN)
    assert {s: sel[s] for s in (*shards.OWN_SYSTEMS, "release")} == _whole("release")
    assert sel["build"] is True


def test_a_docs_only_release_pull_request_is_still_whole() -> None:
    d = ci_plan.decide(["docs/index.md"], PR_MAIN)
    assert d.full and d.judge and d.tier == "release"


def test_a_dispatch_rebuilds_and_judges_the_tier_it_asks() -> None:
    d = ci_plan.decide(None, DISPATCH)
    assert d.full and d.rebuild and d.tier == "normal"
    e = ci_plan.Event("workflow_dispatch", DISPATCH.ref, release_tier=True)
    assert ci_plan.decide(None, e).tier == "release"


def test_a_push_with_no_known_change_is_full() -> None:
    assert ci_plan.decide(None, PUSH_DEV).full


# The acceptance commit: accepted.json and the newest history volume, nothing else.
ACCEPT = ["context/progress/accepted.json", "context/progress/history-00060.jsonl"]


def test_the_acceptance_push_sets_every_output_false() -> None:
    d = ci_plan.decide(ACCEPT, PUSH_DEV)
    assert d.quiet
    assert not any(getattr(d, f) for f in (*ci_plan.FLAGS, "docs_only", "full", "rebuild", "judge"))
    sel = ci_plan.select(d, PLAN)
    assert sel["selected"] == [] and sel["verify"] == [] and sel["build"] is False
    out = ci_plan.outputs(d, sel, [])
    assert {k for k, v in out.items() if v == "true"} == {"acceptance"}


@pytest.mark.parametrize(
    "changed",
    [
        ACCEPT + ["src/x.py"],
        ["context/progress/accepted.json", "context/progress/README.md"],
        ["context/progress/accepted.json", "context/progress/history-00060.jsonl.bak"],
    ],
)
def test_anything_more_or_less_than_an_acceptance_is_full(changed) -> None:
    d = ci_plan.decide(changed, PUSH_DEV)
    assert not d.quiet and d.full


def _progress_refusals(changed: list[str], event) -> list[str]:
    """The refusals of accepted state alone, among every refusal the plan makes."""
    d = ci_plan.decide(changed, event)
    return [r for r in ci_plan.refusals(d, event, changed) if "accepted state" in r]


def test_the_acceptance_paths_on_a_pull_request_are_refused() -> None:
    d = ci_plan.decide(ACCEPT, PR_DEV)
    assert d.progress and not d.quiet
    refusals = _progress_refusals(ACCEPT, PR_DEV)
    assert len(refusals) == 1 and "context/progress/accepted.json" in refusals[0]


def test_progress_is_refused_on_a_pull_request_only() -> None:
    changed = ["context/progress/accepted.json", "src/x.py"]
    assert _progress_refusals(changed, PR_DEV)
    assert ci_plan.refusals(ci_plan.decide(changed, PUSH_DEV), PUSH_DEV, changed) == []
    assert _progress_refusals(["src/x.py"], PR_DEV) == []


# ---------------------------------------------------------------------------------------------
# A pull request that is not documentation only carries a news file

NEWS = "context/changes/999-a-change.md"


def _news_refusals(changed: list[str], event=PR_DEV) -> list[str]:
    d = ci_plan.decide(changed, event)
    return [r for r in ci_plan.refusals(d, event, changed) if "news file" in r]


def test_a_code_pull_request_without_a_news_file_is_refused() -> None:
    (refusal,) = _news_refusals(["src/x.py", "docs/index.md"])
    assert "context/changes/NNN-<slug>.md" in refusal


@pytest.mark.parametrize(
    "changed",
    [
        ["src/x.py", NEWS],
        [NEWS],
        ["docs/index.md", "context/reviews/999-a-change-pr-2026-10-25.md"],
        [],
    ],
    ids=["code and its news", "the news alone", "documentation only", "nothing"],
)
def test_a_news_file_or_documentation_alone_carries_no_news_refusal(changed) -> None:
    assert _news_refusals(changed) == []


def test_the_folders_readme_is_no_news_file() -> None:
    assert _news_refusals(["src/x.py", "context/changes/README.md"])


def test_only_a_pull_request_into_dev_is_held_to_a_news_file() -> None:
    """A push to dev is the merge of a pull request already held to it; the release pull request
    into main carries the news files of every change it releases, assembled by the bump."""
    for event in (PUSH_DEV, PR_MAIN, TAG, DISPATCH, SCHEDULE):
        assert _news_refusals(["src/x.py"], event) == [], event


def test_a_release_pull_request_refuses_accepted_state_no_acceptance_wrote() -> None:
    """Every commit the release pull request carries that changes accepted.json or a history
    volume must be an acceptance: those two files and nothing else. A hand-written change to the
    accepted state, on dev by a bypass or anywhere else, is refused, named by its commit."""
    acceptance = ci_plan.Commit("1" * 40, tuple(ACCEPT))
    readme = ci_plan.Commit("2" * 40, ("context/progress/README.md", "docs/index.md"))
    code = ci_plan.Commit("3" * 40, ("src/x.py",))
    forged = ci_plan.Commit("4" * 40, ("context/progress/accepted.json", "src/x.py"))
    alone = ci_plan.Commit("5" * 40, ("context/progress/accepted.json",))
    changed = [*ACCEPT, "src/x.py", "context/progress/README.md", "docs/index.md"]
    d = ci_plan.decide(changed, PR_MAIN)

    def refused(*commits):
        return ci_plan.refusals(d, PR_MAIN, changed, ci_plan.PullRequest("", list(commits), {}))

    assert refused(acceptance, readme, code) == []
    for bad in (forged, alone):
        out = refused(acceptance, bad, code)
        assert len(out) == 1 and bad.sha[:12] in out[0] and "accepted state" in out[0], out
    assert ci_plan.refusals(d, PR_MAIN, changed) == []  # no commits read: nothing to hold


def test_a_release_pull_request_carries_devs_acceptances_and_is_not_refused() -> None:
    """A release pull request's change is everything dev took since main, the acceptance commits
    the accept job pushed among it; each reached dev through its own refused-or-green check, and
    the release is judged whole."""
    changed = [*ACCEPT, "src/x.py", "docs/index.md"]
    d = ci_plan.decide(changed, PR_MAIN)
    assert d.progress and d.full and d.tier == "release"
    assert ci_plan.refusals(d, PR_MAIN, changed) == []
    assert ci_plan.refusals(ci_plan.decide(changed, PR_DEV), PR_DEV, changed)


# ---------------------------------------------------------------------------------------------
# The selection and the outputs as the workflow reads them


def test_the_whole_selection_is_the_shard_plan_on_every_system() -> None:
    """The matrix each judge job runs is generated from tests/release_shards.toml: run whole,
    each system's list is the plan's, in its order, and the build shard rides with it."""
    sel = ci_plan.select(ci_plan.decide(None, TAG), PLAN)
    for system in (*shards.OWN_SYSTEMS, "release"):
        assert sel[system] == shards.on(shards.load(), system), system
    pairs = {tuple(p.split("/", 1)) for p in sel["selected"]}
    want = {("build", "build")} | {
        (s, n) for s in (*shards.OWN_SYSTEMS, "release") for n in shards.on(shards.load(), s)
    }
    assert pairs == want


def test_selected_is_the_union_of_the_matrices() -> None:
    sel = ci_plan.select(ci_plan.decide(["src/x.py"], PR_DEV), PLAN)
    want = [f"{s}/{n}" for s in (*shards.OWN_SYSTEMS, "release") for n in sel[s]]
    assert sel["selected"] == want


def test_the_outputs_are_one_line_each_and_read_back() -> None:
    d = ci_plan.decide(["src/x.py"], PR_DEV)
    sel = ci_plan.select(d, PLAN)
    out = ci_plan.outputs(d, sel, [])
    assert all("\n" not in v for v in out.values())
    assert out["runner"] == "true" and out["full"] == "false" and out["tier"] == "normal"
    assert json.loads(out["macos"]) == sel["macos"]
    assert json.loads(out["verify"]) == ["ubuntu-24.04"]
    assert json.loads(out["selected"]) == sel["selected"]
    assert json.loads(out["refusals"]) == []
    assert out["build"] == "false" and out["judge"] == "true"
    for flag in (*ci_plan.FLAGS, "docs_only", "full", "rebuild", "judge", "build"):
        assert out[flag] in ("true", "false"), flag


def test_the_command_line_reads_paths_and_writes_github_output(tmp_path) -> None:
    out = tmp_path / "out"
    r = subprocess.run(
        [
            sys.executable,
            "-I",
            str(paths.REPO / "release" / "ci_plan.py"),
            "--files",
            "-",
            "--event",
            "pull_request",
            "--ref",
            "refs/pull/7/merge",
            "--base-ref",
            "dev",
            "--label",
            "ci:full",
        ],
        input="src/x.py\n\ndocs/index.md\n",
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "GITHUB_OUTPUT": str(out)},
    )
    assert r.returncode == 0, r.stderr
    got = dict(line.split("=", 1) for line in out.read_text().splitlines())
    assert got["full"] == "true" and got["runner"] == "true" and got["docs_only"] == "false"
    assert json.loads(got["selected"]) and got["build"] == "true"


def test_the_top_level_env_is_read_as_the_workflow_writes_it() -> None:
    text = 'name: x\non:\n  push:\nenv:\n  A: "1"\n  # a comment\n  B: two # trailing\njobs:\n'
    assert ci_plan.top_env(text) == {"A": "1", "B": "two"}
    real = ci_plan.top_env((paths.REPO / ".github" / "workflows" / "release.yml").read_text())
    assert set(real) >= {"SOURCE_DATE_EPOCH", "UV_VERSION", "UV_PYTHON", "UV_LOCKED"}


def test_the_key_moves_with_an_env_value_and_not_with_a_test(tmp_path) -> None:
    """The key at the head against the key at the merge base, in a scratch repository: a test
    file leaves it, a workflow's env value moves it."""
    repo = tmp_path / "repo"
    repo.mkdir()
    files = {
        "release/set_key.py": (paths.REPO / "release" / "set_key.py").read_text(),
        "release/build-constraints.txt": "x\n",
        "downloads/SHA256SUMS": f"{'1' * 64}  a.tar.gz\n",
        "scripts/build.sh": "echo\n",
        "tests/harness/__init__.py": "",
        "tests/harness/constructors.py": "",
        "tests/unit/test_x.py": "",
        ".github/workflows/release.yml": (
            "env:\n  SOURCE_DATE_EPOCH: '1'\n  UV_VERSION: '2'\n  UV_LOCKED: '1'\n"
            "  UV_PYTHON: '3'\n  UV_BUILD_CONSTRAINT: release/build-constraints.txt\njobs:\n"
        ),
    }
    for rel, text in files.items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(text)

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
        ).stdout.strip()

    git("init", "-q")
    git("add", "-A")
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base")
    base = git("rev-parse", "HEAD")
    (repo / "tests/unit/test_x.py").write_text("x = 1\n")
    git("add", "-A")
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "a test")
    assert ci_plan.key_moved(repo, base) is False
    workflow = repo / ".github/workflows/release.yml"
    workflow.write_text(workflow.read_text().replace("UV_VERSION: '2'", "UV_VERSION: '9'"))
    git("add", "-A")
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "an env value")
    assert ci_plan.key_moved(repo, base) is True


# Only the accepted state is refused: the progress folder's README is a document.


def test_the_progress_readme_alone_is_documentation_and_not_refused() -> None:
    changed = ["context/progress/README.md"]
    d = ci_plan.decide(changed, PR_DEV)
    assert ci_plan.classify(changed[0]) == frozenset({"docs"})
    assert d.docs_only and not d.progress
    assert ci_plan.refusals(d, PR_DEV, changed) == []


@pytest.mark.parametrize(
    "path", ["context/progress/accepted.json", "context/progress/history-00060.jsonl",
             "context/progress/history.jsonl"],
)  # fmt: skip
def test_the_accepted_state_alone_is_refused(path) -> None:
    assert _progress_refusals([path], PR_DEV), path


def test_a_pull_request_whose_base_cannot_be_read_is_judged_whole() -> None:
    """With no change to read, a pull request into dev fails closed: the merge-grade set."""
    d = ci_plan.decide(None, PR_DEV)
    assert d.full and d.judge and not d.docs_only
    assert "the pull request's base could not be read: the run is whole" in d.why
    sel = ci_plan.select(d, PLAN)
    assert sel["macos"] == shards.on(shards.load(), "macos") and sel["build"] is True


# ---------------------------------------------------------------------------------------------
# The review file: committed after the last code, signed by someone other than the author, and
# saying the change lands

REVIEW = "context/reviews/999-a-change-pr-2026-10-26.md"
AUTHOR = "https://claude.ai/code/session_01AUTHOR"
OTHER = "https://claude.ai/code/session_01REVIEWER"
BODY = f"- **Author:** {AUTHOR}\n- every new check seen failing first\n"


def _review(reviewer: str = OTHER, verdict: str = "Lands: nothing stands.") -> str:
    return (
        "# Review of 999 — a change\n\n- **Date:** 2026-10-26\n"
        f"- **Reviewer:** {reviewer}\n- **Run:** 1\n\n## Findings, most severe first\n\nNone.\n\n"
        f"## Verdict\n\n{verdict}\n"
    )


def _pr(review: str | None = None, commits=None, body: str = BODY):
    code = ci_plan.Commit("a" * 40, ("src/x.py", NEWS), (AUTHOR,))
    last = ci_plan.Commit("b" * 40, (REVIEW,), (OTHER,))
    return ci_plan.PullRequest(
        body=body,
        commits=[code, last] if commits is None else commits,
        files={REVIEW: _review() if review is None else review},
    )


def _review_refusals(pr, changed=("src/x.py", NEWS, REVIEW)) -> list[str]:
    changed = list(changed)
    d = ci_plan.decide(changed, PR_DEV)
    return [r for r in ci_plan.refusals(d, PR_DEV, changed, pr) if "review" in r]


def test_a_review_committed_last_by_another_session_that_lands_is_accepted() -> None:
    assert _review_refusals(_pr()) == []


def test_a_code_pull_request_with_no_review_file_is_refused() -> None:
    (refusal,) = _review_refusals(_pr(), changed=("src/x.py", NEWS))
    assert "no review file" in refusal and "999-a-change" in refusal


def test_a_review_of_another_news_files_name_is_no_review_of_this_one() -> None:
    other = "context/reviews/998-another-pr-2026-10-26.md"
    assert _review_refusals(_pr(), changed=("src/x.py", NEWS, other))


def test_a_code_commit_after_the_review_is_refused() -> None:
    code = ci_plan.Commit("a" * 40, ("src/x.py", NEWS), (AUTHOR,))
    review = ci_plan.Commit("b" * 40, (REVIEW,), (OTHER,))
    fix = ci_plan.Commit("c" * 40, ("src/x.py",), (AUTHOR,))
    (refusal,) = _review_refusals(_pr(commits=[code, review, fix]))
    assert "cccccccccccc" in refusal and "src/x.py" in refusal


def test_a_documentation_commit_after_the_review_is_allowed() -> None:
    code = ci_plan.Commit("a" * 40, ("src/x.py", NEWS), (AUTHOR,))
    review = ci_plan.Commit("b" * 40, (REVIEW,), (OTHER,))
    low = ci_plan.Commit("c" * 40, ("context/specifications/999-a-change.md",), (OTHER,))
    assert _review_refusals(_pr(commits=[code, review, low])) == []


@pytest.mark.parametrize(
    "reviewer", ["", "<the reviewer's session URL or a person; not the author>"]
)
def test_an_empty_reviewer_line_is_refused(reviewer) -> None:
    (refusal,) = _review_refusals(_pr(_review(reviewer=reviewer)))
    assert "Reviewer:" in refusal and "empty" in refusal


@pytest.mark.parametrize(
    "reviewer",
    [AUTHOR, f"{AUTHOR}.", f"`{AUTHOR}`", f"{AUTHOR}; not the author"],
    ids=["the url", "with a stop", "in backticks", "with words"],
)
def test_a_reviewer_line_that_is_the_authors_session_url_alone_is_refused(reviewer) -> None:
    (refusal,) = _review_refusals(_pr(_review(reviewer=reviewer)))
    assert "author" in refusal and AUTHOR in refusal


def test_the_author_is_read_from_the_code_commits_trailers_too() -> None:
    code = ci_plan.Commit(
        "a" * 40, ("src/x.py", NEWS), ("https://claude.ai/code/session_01TRAILER",)
    )
    review = ci_plan.Commit("b" * 40, (REVIEW,), ())
    pr = _pr(
        _review(reviewer="https://claude.ai/code/session_01TRAILER"),
        commits=[code, review],
        body="no author line\n",
    )
    assert _review_refusals(pr)


def test_a_person_named_as_the_author_may_not_review() -> None:
    pr = _pr(_review(reviewer="Clay Gendron"), body="- **Author:** Clay Gendron\n")
    assert _review_refusals(pr)


def test_a_reviewers_own_session_on_a_review_commit_is_not_an_author() -> None:
    """The review's own commit touches documentation alone: its trailer is the reviewer's."""
    assert _review_refusals(_pr(_review(reviewer=OTHER))) == []


def test_a_fresh_sub_agent_of_the_authors_session_may_review() -> None:
    reviewer = f"an agent (Claude), a fresh sub-agent of {AUTHOR}; not the author"
    assert _review_refusals(_pr(_review(reviewer=reviewer))) == []


@pytest.mark.parametrize(
    "verdict",
    ["Does not land yet: Medium 1.", "", "It lands.", "Landed elsewhere"],
    ids=["does not land", "no verdict", "not first", "another word"],
)
def test_a_verdict_that_does_not_begin_lands_is_refused(verdict) -> None:
    (refusal,) = _review_refusals(_pr(_review(verdict=verdict)))
    assert "Verdict" in refusal


def test_a_review_file_deleted_at_the_head_is_refused() -> None:
    pr = _pr()
    pr.files.clear()
    assert _review_refusals(pr)


def test_the_review_is_not_asked_of_documentation_or_of_main() -> None:
    docs = ["docs/index.md"]
    assert ci_plan.refusals(ci_plan.decide(docs, PR_DEV), PR_DEV, docs, _pr()) == []
    code = ["src/x.py"]
    assert ci_plan.refusals(ci_plan.decide(code, PR_MAIN), PR_MAIN, code, _pr()) == []


def test_the_pull_requests_commits_trailers_and_review_are_read_with_git(
    tmp_path, monkeypatch
) -> None:
    import shutil

    git = shutil.which("git")
    if git is None:
        pytest.skip("needs: git")
    config = tmp_path / "gitconfig"
    config.write_text("[user]\n\tname = t\n\temail = t@t\n[commit]\n\tgpgsign = false\n")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    repo = tmp_path / "repo"

    def run(*args: str) -> str:
        return subprocess.run(
            [git, "-C", str(repo), *args], check=True, capture_output=True, text=True
        ).stdout.strip()

    subprocess.run([git, "init", "-q", "-b", "dev", str(repo)], check=True)
    (repo / "README.md").write_text("x\n")
    run("add", "-A")
    run("commit", "-q", "-m", "start")
    base = run("rev-parse", "HEAD")
    (repo / "src").mkdir()
    (repo / "src" / "x.py").write_text("x = 1\n")
    run("add", "-A")
    run("commit", "-q", "-m", f"code\n\nClaude-Session: {AUTHOR}")
    (repo / "context" / "reviews").mkdir(parents=True)
    (repo / REVIEW).write_text(_review())
    run("add", "-A")
    run("commit", "-q", "-m", "review")
    head = run("rev-parse", "HEAD")
    pr = ci_plan.read_pull_request(repo, base, head, BODY, ["src/x.py", REVIEW])
    assert [c.paths for c in pr.commits] == [("src/x.py",), (REVIEW,)]
    assert [c.sessions for c in pr.commits] == [(AUTHOR,), ()]
    assert pr.files == {REVIEW: _review()} and pr.body == BODY


# ---------------------------------------------------------------------------------------------
# The accept jobs run after a merge into dev alone


def test_accept_is_set_by_a_merge_into_dev_and_the_release_pull_request() -> None:
    """The release pull request's record is accepted too: accept-record runs in its run, and the
    push onto dev is made by a workflow on dev's own context, never by the pull request's run."""
    d = ci_plan.decide(["src/x.py"], PR_MAIN)
    assert d.accept and ci_plan.outputs(d, ci_plan.select(d, PLAN), [])["accept"] == "true"
    reused = ci_plan.decide(ACCEPT, PR_MAIN, reused=(7, "run 7"))
    assert reused.quiet and not reused.accept  # a re-used run accepts nothing again


def test_accept_is_set_by_a_merge_into_dev_alone_among_the_rest() -> None:
    assert ci_plan.decide(["src/x.py"], PUSH_DEV).accept
    out = ci_plan.outputs(
        ci_plan.decide(["src/x.py"], PUSH_DEV),
        ci_plan.select(ci_plan.decide(["src/x.py"], PUSH_DEV), PLAN),
        [],
    )
    assert out["accept"] == "true"
    assert not ci_plan.decide(ACCEPT, PUSH_DEV).accept  # the acceptance's own push
    for event in (PR_DEV, TAG, DISPATCH, SCHEDULE):
        assert not ci_plan.decide(["src/x.py"], event).accept, event


# ---------------------------------------------------------------------------------------------
# A push of documentation alone onto a green head re-uses that head's run

GREEN = {"plan": "success", "quick": "success", "gather the shards' records": "success",
         "verify (ubuntu-24.04)": "success", "ci-status": "failure"}  # fmt: skip
CODE_HEAD, REVIEW_HEAD, NEW_HEAD = "1" * 40, "2" * 40, "3" * 40


def _reuse(runs, jobs, ancestors=(CODE_HEAD, REVIEW_HEAD), diffs=None, allowed=None):
    diffs = diffs or {
        CODE_HEAD: [REVIEW, "docs/index.md"],
        REVIEW_HEAD: ["docs/index.md"],
    }
    return ci_plan.find_reusable(
        NEW_HEAD,
        runs,
        jobs_of=lambda run_id: jobs[run_id],
        is_ancestor=lambda sha: sha in ancestors,
        changed_since=lambda sha: diffs[sha],
        **({} if allowed is None else {"allowed": allowed}),
    )


def test_a_docs_only_push_onto_a_green_head_reuses_its_run() -> None:
    """The code head's run is green but for ci-status, which waited for the review file: its
    judge and gather passed, so the review's push re-uses them."""
    run, why = _reuse([{"databaseId": 7, "headSha": CODE_HEAD, "status": "completed"}], {7: GREEN})
    assert run == 7 and CODE_HEAD[:12] in why


def test_a_run_whose_gather_did_not_pass_is_not_reused() -> None:
    red = {**GREEN, "gather the shards' records": "failure"}
    skipped = {**GREEN, "gather the shards' records": "skipped"}  # itself a re-use: walk past it
    runs = [
        {"databaseId": 9, "headSha": REVIEW_HEAD, "status": "completed"},
        {"databaseId": 7, "headSha": CODE_HEAD, "status": "completed"},
    ]
    assert _reuse(runs, {9: skipped, 7: GREEN})[0] == 7
    assert _reuse(runs, {9: skipped, 7: red})[0] is None
    judge_red = {**GREEN, "judge (windows-2025, own-a)": "failure"}
    assert _reuse(runs[1:], {7: judge_red})[0] is None


def test_a_run_behind_code_or_off_this_history_is_not_reused() -> None:
    runs = [{"databaseId": 7, "headSha": CODE_HEAD, "status": "completed"}]
    assert _reuse(runs, {7: GREEN}, diffs={CODE_HEAD: ["src/x.py"]})[0] is None
    assert _reuse(runs, {7: GREEN}, ancestors=())[0] is None  # rebased: the tree moved
    running = [{"databaseId": 7, "headSha": CODE_HEAD, "status": "in_progress"}]
    assert _reuse(running, {7: GREEN})[0] is None
    own = [{"databaseId": 7, "headSha": NEW_HEAD, "status": "completed"}]
    assert _reuse(own, {7: GREEN})[0] is None


def test_a_reused_run_sets_every_output_false_and_keeps_the_refusals() -> None:
    changed = ["src/x.py", NEWS, REVIEW]
    d = ci_plan.decide(changed, PR_DEV, reused=(7, "run 7, green on 111111111111"))
    assert d.quiet and not d.judge
    out = ci_plan.outputs(d, ci_plan.select(d, PLAN), [])
    assert {k for k, v in out.items() if v == "true"} == set()
    assert ci_plan.refusals(d, PR_DEV, changed, _pr()) == []
    assert ci_plan.refusals(d, PR_DEV, ["src/x.py", NEWS], _pr())  # still no review file
    assert any("run 7" in w for w in d.why)


def test_a_release_pull_request_re_uses_its_green_run_across_its_own_acceptance() -> None:
    """The release pull request's acceptance onto dev moves its head by the acceptance pair
    alone: its new run re-uses the green one, so the acceptance starts no second whole run and
    no second acceptance. Anything more, documentation included, is a commit main would receive
    unjudged, and runs whole."""
    runs = [{"databaseId": 7, "headSha": CODE_HEAD, "status": "completed"}]
    rule = ci_plan.reuse_rule(PR_MAIN)
    assert rule is ci_plan.is_acceptance
    assert ci_plan.reuse_rule(PR_DEV) is ci_plan.docs_only
    hit = _reuse(runs, {7: GREEN}, diffs={CODE_HEAD: ACCEPT}, allowed=rule)
    assert hit[0] == 7 and "the accepted state" in hit[1]
    for diff in ([*ACCEPT, "docs/index.md"], ["docs/index.md"], [*ACCEPT, "src/x.py"]):
        assert _reuse(runs, {7: GREEN}, diffs={CODE_HEAD: diff}, allowed=rule)[0] is None
    assert _reuse(runs, {7: GREEN}, diffs={CODE_HEAD: ACCEPT})[0] is None  # into dev's rule


def test_no_run_is_looked_for_without_a_token() -> None:
    assert ci_plan.green_runs({}, "spec/999-x") is None


# ---------------------------------------------------------------------------------------------
# The weekly run


def test_the_weekly_run_is_the_schedule_or_a_dispatch_asking_for_it() -> None:
    weekly = ci_plan.Event("workflow_dispatch", "refs/heads/dev", weekly=True)
    for event in (SCHEDULE, weekly):
        d = ci_plan.decide(None, event)
        assert d.weekly and d.rebuild and d.tier == "release" and not d.accept, event
        out = ci_plan.outputs(d, ci_plan.select(d, PLAN), [])
        assert out["weekly"] == "true"
    for event in (DISPATCH, PUSH_DEV, PR_DEV, TAG):
        assert not ci_plan.decide(None, event).weekly, event


# One specification may land by several pull requests on one day: the review's name is the news
# file's stem, then an optional infix of lowercase words, then -pr- and the date.


@pytest.mark.parametrize(
    "name",
    ["999-a-change-step-3-pr-2026-10-26.md", "999-a-change-step-4-pr-2026-10-26.md",
     "999-a-change-second-look-pr-2026-10-26.md"],
)  # fmt: skip
def test_a_review_named_with_an_infix_after_the_news_files_stem_is_accepted(name) -> None:
    path = f"context/reviews/{name}"
    pr = _pr(commits=[
        ci_plan.Commit("a" * 40, ("src/x.py", NEWS), (AUTHOR,)),
        ci_plan.Commit("b" * 40, (path,), (OTHER,)),
    ])  # fmt: skip
    pr.files.clear()
    pr.files[path] = _review()
    assert _review_refusals(pr, changed=("src/x.py", NEWS, path)) == []


@pytest.mark.parametrize(
    "name",
    ["998-another-step-3-pr-2026-10-26.md", "999-a-changed-pr-2026-10-26.md",
     "999-a-change-step-3-pr.md", "999-a-change-pr-2026-10.md",
     "999-a-change-Step-3-pr-2026-10-26.md"],
    ids=["another stem", "a longer word, not an infix", "no date", "half a date", "upper case"],
)  # fmt: skip
def test_a_review_of_another_stem_or_without_its_date_is_still_refused(name) -> None:
    path = f"context/reviews/{name}"
    pr = _pr()
    pr.files[path] = _review()
    (refusal,) = _review_refusals(pr, changed=("src/x.py", NEWS, path))
    assert "no review file" in refusal


# Two review files of one date: the one the branch's newest commit changed is read; when one
# commit changed both, the check cannot tell which signs the head, and refuses.

OLD_REVIEW = "context/reviews/999-a-change-step-1-pr-2026-10-26.md"


def test_on_a_tie_of_dates_the_review_the_newest_commit_changed_is_read() -> None:
    code = ci_plan.Commit("a" * 40, ("src/x.py", NEWS), (AUTHOR,))
    stale = ci_plan.Commit("b" * 40, (OLD_REVIEW,), (OTHER,))  # sorts last by path, older
    signed = ci_plan.Commit("c" * 40, (REVIEW,), (OTHER,))
    pr = _pr(commits=[code, stale, signed])
    pr.files[OLD_REVIEW] = _review(verdict="Does not land yet: High 1.")
    pr.files[REVIEW] = _review()
    assert _review_refusals(pr, changed=("src/x.py", NEWS, REVIEW, OLD_REVIEW)) == []


def test_two_reviews_of_one_date_changed_by_one_commit_are_refused() -> None:
    code = ci_plan.Commit("a" * 40, ("src/x.py", NEWS), (AUTHOR,))
    both = ci_plan.Commit("b" * 40, (REVIEW, OLD_REVIEW), (OTHER,))
    pr = _pr(commits=[code, both])
    pr.files[OLD_REVIEW] = _review()
    (refusal,) = _review_refusals(pr, changed=("src/x.py", NEWS, REVIEW, OLD_REVIEW))
    assert "two review files of one date" in refusal


# A skip word in the title or the description lands in the squash merge's message, and GitHub
# would start no run for the merge, so it would be neither judged nor accepted.


@pytest.mark.parametrize(
    "word", ["[skip ci]", "[ci skip]", "[no ci]", "[skip actions]", "[actions skip]", "[SKIP CI]"]
)
@pytest.mark.parametrize("where", ["title", "body"])
def test_a_skip_word_in_the_title_or_description_is_refused(word, where) -> None:
    pr = _pr(body=BODY + (f"\nthe message ends {word}\n" if where == "body" else ""))
    pr.title = f"A change {word}" if where == "title" else "A change"
    changed = ["src/x.py", NEWS, REVIEW]
    d = ci_plan.decide(changed, PR_DEV)
    refused = [r for r in ci_plan.refusals(d, PR_DEV, changed, pr) if "skip" in r]
    assert len(refused) == 1 and word.lower() in refused[0].lower()


def test_a_documentation_pull_request_with_a_skip_word_is_refused_too() -> None:
    pr = _pr(body="see [skip ci]\n")
    changed = ["docs/index.md"]
    assert ci_plan.refusals(ci_plan.decide(changed, PR_DEV), PR_DEV, changed, pr)


def test_a_title_and_description_without_a_skip_word_are_not_refused() -> None:
    pr = _pr()
    pr.title = "Skip the cache on CI: ci skips nothing"
    changed = ["src/x.py", NEWS, REVIEW]
    assert ci_plan.refusals(ci_plan.decide(changed, PR_DEV), PR_DEV, changed, pr) == []


# The acceptance commit carries no skip word (GitHub would skip a release pull request whose head
# it is): the plan is quiet on it instead, and only the plan runs.


@pytest.mark.parametrize(
    "changed",
    [ACCEPT, ["context/progress/accepted.json"], ["context/progress/history-00060.jsonl"],
     ["context/progress/accepted.json", "context/progress/history.jsonl",
      "context/progress/history-00060.jsonl"]],
    ids=["the acceptance", "accepted.json alone", "a volume alone", "two volumes"],
)  # fmt: skip
def test_a_push_of_the_accepted_state_alone_selects_nothing(changed) -> None:
    d = ci_plan.decide(changed, PUSH_DEV)
    assert d.quiet and d.acceptance and not d.accept and not d.judge
    out = ci_plan.outputs(d, ci_plan.select(d, PLAN), [])
    assert out["acceptance"] == "true" and out["accept"] == "false" and out["judge"] == "false"


def test_only_a_push_of_the_accepted_state_is_an_acceptance() -> None:
    for changed, event in ((ACCEPT, PR_DEV), (["src/x.py"], PUSH_DEV), (None, PUSH_DEV)):
        d = ci_plan.decide(changed, event)
        assert ci_plan.outputs(d, ci_plan.select(d, PLAN), [])["acceptance"] == "false"


# ---------------------------------------------------------------------------------------------
# The release's preparation: bump and date in one pull request into dev, judged as documentation

VERSION_FILE = "src/wasi_python/__init__.py"
PREPARATION = [
    ("M", VERSION_FILE),
    ("M", "CHANGELOG.md"),
    ("D", "context/changes/140-a-change.md"),
    ("M", "docs/reference/packages.md"),
    ("M", "context/release-tier-claims.toml"),
    ("M", "context/release-tier-claims-history.md"),
    ("A", "context/reviews/0.1.1-structural-review-2026-10-26.md"),
]


def test_bump_and_date_land_as_the_releases_documentation_change() -> None:
    """bump moves the version line and removes every news file, so its pull request carries no
    news file of its own; its change is the release's notes, the version, the ledger moved and the
    release's reviews, all of which the release pull request judges whole. It runs quick alone."""
    assert ci_plan.is_release_preparation(PREPARATION, version_line_only=True)
    assert not ci_plan.is_release_preparation(PREPARATION, version_line_only=False)
    for extra in (("M", "src/wasi_python/runner.py"), ("A", "context/changes/141-new.md"),
                  ("M", "tests/harness/gather.py")):  # fmt: skip
        assert not ci_plan.is_release_preparation([*PREPARATION, extra], version_line_only=True)
    assert not ci_plan.is_release_preparation(PREPARATION[1:], version_line_only=True)
    changed = [p for _, p in PREPARATION]
    d = ci_plan.decide(changed, PR_DEV, release_preparation=True)
    assert d.docs_only and not d.judge and not d.full
    assert ci_plan.refusals(d, PR_DEV, changed, _pr(commits=[])) == []
    plain = ci_plan.decide(changed, PR_DEV)
    assert not plain.docs_only and plain.judge


def test_only_the_version_line_may_move_in_the_version_file() -> None:
    bumped = '--- a/x\n+++ b/x\n@@ -3 +3 @@\n-__version__ = "0.1.0"\n+__version__ = "0.1.1"\n'
    assert ci_plan.version_line_only(bumped)
    more = bumped + "@@ -9,0 +10 @@\n+import os\n"
    assert not ci_plan.version_line_only(more)
    assert not ci_plan.version_line_only("")


# The ledger in a preparation: date's move exactly, or the preparation is refused, named.

LEDGER_HEADER = "# The release-tier claims ledger.\n# Appended by its pull request.\n"
LEDGER_BLOCK = (
    '[[claim]]\nspec = "140"\ngrows = ["tests/checks/test_v1_3_x.py::test_slow"]\n'
    'growth = "a pin moved"\n'
)
LEDGER_HISTORY = "# The release-tier claims, by release\n\nIntro.\n\n## 0.1.0\n\nMoved.\n"


def _moved(ledger: str = LEDGER_HEADER + "\n" + LEDGER_BLOCK) -> tuple[str, str]:
    return news.move_ledger(ledger, LEDGER_HISTORY, "0.1.1", "2026-10-26")


def test_a_preparation_whose_ledger_is_dates_exact_move_is_a_preparation() -> None:
    head_ledger, head_history = _moved()
    base = (LEDGER_HEADER + "\n" + LEDGER_BLOCK, LEDGER_HISTORY)
    assert ci_plan.ledger_move_refusal(base, (head_ledger, head_history), "0.1.1") is None
    assert ci_plan.ledger_move_refusal(base, base, "0.1.1") is None  # the ledger not touched


def test_a_preparation_that_adds_a_ledger_block_is_refused_named() -> None:
    """The ledger is a source of reasons the release pull request's acceptance consumes, so in a
    preparation, which asks no review file, its change must be date's move and nothing else."""
    base = (LEDGER_HEADER + "\n" + LEDGER_BLOCK, LEDGER_HISTORY)
    head_ledger, head_history = _moved()
    extra = (
        '[[claim]]\nspec = "999"\ngrows = ["tests/checks/test_v1_3_x.py::test_new"]\ngrowth = "x"\n'
    )
    added = head_history.replace("```\n", extra + "```\n", 1)
    why = ci_plan.ledger_move_refusal(base, (head_ledger, added), "0.1.1")
    assert why and "date's move" in why, why
    kept = ci_plan.ledger_move_refusal(base, (head_ledger + "\n" + extra, head_history), "0.1.1")
    assert kept and "header" in kept, kept
    changed = [VERSION_FILE, "CHANGELOG.md", *ci_plan.LEDGER_FILES]
    d = ci_plan.decide(changed, PR_DEV, preparation_refusal=why)
    assert not d.docs_only and d.judge
    assert any(why in r for r in ci_plan.refusals(d, PR_DEV, changed, _pr(commits=[])))
