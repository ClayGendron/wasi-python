"""release/ci_plan.py: which jobs a run of the release workflow needs, from the paths it changes.

Each row of the decision table, the two pushes that set every output false, what `full` takes,
the shards each shape selects, and the outputs as the workflow reads them."""

from __future__ import annotations

import importlib.util
import json
import shutil
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
    # The platform module and the engine's pin: the host-specific code, which keeps its macOS legs.
    ("src/wasi_python/_platform.py", {"runner", "platform"}),
    ("src/wasi_python/_platform_windows.py", {"runner", "platform"}),
    ("src/wasi_python/_platform_common.py", {"runner", "platform"}),
    ("src/x/_platform.py", {"runner"}),
    ("pyproject.toml", {"runner"}),
    ("uv.lock", {"runner", "platform"}),
    ("tests/harness/gather.py", {"harness"}),
    ("tests/conftest.py", {"harness"}),
    ("tests/judge_options/wasi_python_judge_options.py", {"harness"}),
    ("tests/judge_options/pyproject.toml", {"harness"}),
    ("tests/release_shards.toml", {"harness"}),
    ("tests/known_gaps.toml", {"harness"}),
    ("context/embedders.txt", {"harness"}),
    ("context/release-claims.toml", {"harness"}),
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
    ("context/specifications/138-x.md", {"docs"}),
    ("context/reviews/138-x-pr-2026-10-25.md", {"docs"}),
    ("context/changes/notes/deeper.md", {"docs"}),
    ("context/changes/README.md", {"docs"}),
    ("README.md", {"docs"}),
    ("CHANGELOG.md", {"docs"}),
    ("SECURITY.md", {"docs"}),
    ("LICENSE", {"docs"}),
    ("mkdocs.yml", {"docs"}),
    (".gitignore", {"docs"}),
    # The files an agent's tool loads by itself, at any depth: quick alone, and reviewed.
    (".claude/settings.json", {"agents"}),
    (".claude/hooks/x.sh", {"agents"}),
    (".agents/skills/x/SKILL.md", {"agents"}),
    ("AGENTS.md", {"agents"}),
    ("CLAUDE.md", {"agents"}),
    ("context/CLAUDE.md", {"agents"}),
    ("docs/AGENTS.md", {"agents"}),
    ("context/claude.md", {"agents"}),
    ("docs/Agents.md", {"agents"}),
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
        "coverage": [],
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


def test_a_src_only_pull_request_runs_own_on_linux_and_windows_and_verify_on_linux() -> None:
    """A change to the runner alone takes no macOS leg on a pull request: the post-merge run
    judges it on macOS within the hour."""
    d = ci_plan.decide(["src/wasi_python/runner.py"], PR_DEV)
    assert d.runner and not d.platform and not d.full and d.tier == "normal" and not d.rebuild
    sel = ci_plan.select(d, PLAN)
    assert sel["macos"] == []
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
def test_set_or_harness_runs_the_upstream_groups_and_no_macos_leg(path) -> None:
    sel = ci_plan.select(ci_plan.decide([path], PR_DEV), PLAN)
    assert sel["macos"] == []
    assert set(UPSTREAM_LINUX) <= set(sel["linux"])
    assert sel["build"] is False and sel["release"] == []


def test_a_moved_key_sets_set_with_no_path_of_its_own() -> None:
    """The key holds the workflows' env too: a change to an env value moves it, so the decision
    job compares the key at the head with the key at the merge base."""
    assert not ci_plan.decide(["tests/unit/test_x.py"], PR_DEV).set
    d = ci_plan.decide(["tests/unit/test_x.py"], PR_DEV, key_moved=True)
    assert d.set
    assert set(UPSTREAM_LINUX) <= set(ci_plan.select(d, PLAN)["linux"])


@pytest.mark.parametrize(
    "path",
    [
        "src/wasi_python/_platform.py",
        "src/wasi_python/_platform_windows.py",
        "src/wasi_python/_platform_common.py",
        "uv.lock",
    ],
)
def test_the_platform_module_or_the_engine_pin_keeps_its_macos_legs(path) -> None:
    """The host-specific code and the engine's pin: a pull request that changes either runs every
    own shard on macOS, and the macOS upstream shard, beside Linux and Windows."""
    d = ci_plan.decide([path], PR_DEV)
    assert d.platform and not d.full
    sel = ci_plan.select(d, PLAN)
    assert sel["macos"] == [n for n in shards.on(shards.load(), "macos")]
    assert sel["linux"] == _own_on("linux")
    assert sel["build"] is False


def test_the_macos_upstream_shard_runs_on_full_or_the_platform_alone() -> None:
    macos_upstream = [n for n, s in PLAN.items() if s.kind == "upstream" and "macos" in s.systems]
    assert macos_upstream
    for path in ("src/wasi_python/runner.py", "tests/harness/plugin.py", "scripts/build.sh"):
        sel = ci_plan.select(ci_plan.decide([path], PR_DEV), PLAN)
        assert not set(macos_upstream) & set(sel["macos"]), path
    for d in (
        ci_plan.decide(["uv.lock"], PR_DEV),
        ci_plan.decide(["src/x.py"], PUSH_DEV),
    ):
        assert set(macos_upstream) <= set(ci_plan.select(d, PLAN)["macos"])


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
    assert sel["build"] is False  # the build shard runs where the pins are compiled alone
    assert "build/build" not in sel["selected"]
    assert sel["verify"] == list(ci_plan.VERIFY_RUNNERS)


@pytest.mark.parametrize(
    ("event", "build"),
    [
        (PR_DEV, False),
        (PUSH_DEV, False),
        (PR_MAIN, True),
        (SCHEDULE, True),
        (DISPATCH, True),
        (ci_plan.Event("workflow_dispatch", DISPATCH.ref, weekly=True), True),
    ],
    ids=[
        "pull-request",
        "push-to-dev",
        "release-pull-request",
        "weekly",
        "dispatch",
        "weekly-dispatch",
    ],  # fmt: skip
)
def test_the_build_shard_runs_exactly_where_the_rebuilds_compile(event, build) -> None:
    """The build shard reads a build tree, which the x86-64 rebuild compiles from the pins
    exactly when the plan rebuilds and judges: the release pull request, the weekly run and a
    dispatch; never a push to dev or a pull request into dev. A tag rebuilds and judges nothing
    (the row below)."""
    changed = None if event in (SCHEDULE, DISPATCH) or event.weekly else ["src/x.py"]
    d = ci_plan.decide(changed, event)
    sel = ci_plan.select(d, PLAN)
    assert sel["build"] is build and d.rebuild is build
    assert ("build/build" in sel["selected"]) is build
    assert ci_plan.outputs(d, sel, [])["build"] == ("true" if build else "false")


def test_a_tag_publishes_what_the_release_pull_request_judged() -> None:
    """A pushed tag compiles the set from the pins on three hosts, installs the wheel fresh on
    three systems and publishes; it judges nothing again, since its tree is the one the release
    pull request judged plus the commit that recorded it: no judge leg, no build shard, no
    gather, and no tier."""
    d = ci_plan.decide(None, TAG)
    assert d.rebuild and d.publish and not d.judge and d.tier == ""
    sel = ci_plan.select(d, PLAN)
    assert all(sel[s] == [] for s in (*shards.OWN_SYSTEMS, "release"))
    assert sel["build"] is False and sel["selected"] == [] and sel["coverage"] == []
    assert sel["verify"] == list(ci_plan.VERIFY_RUNNERS)
    out = ci_plan.outputs(d, sel, [])
    assert (out["judge"], out["build"], out["rebuild"], out["publish"]) == (
        "false",
        "false",
        "true",
        "true",
    )
    assert out["tier"] == ""
    assert all(out[s] == "[]" for s in (*shards.OWN_SYSTEMS, "release"))
    assert json.loads(out["verify"]) == list(ci_plan.VERIFY_RUNNERS)


@pytest.mark.parametrize(
    ("changed", "event"),
    [
        (["src/x.py"], PR_DEV),
        (["docs/x.md"], PR_DEV),
        (["src/x.py"], PR_MAIN),
        (["src/x.py"], PUSH_DEV),
        (["context/progress/accepted.json"], PUSH_DEV),
        (None, SCHEDULE),
        (None, DISPATCH),
        (None, ci_plan.Event("workflow_dispatch", "refs/heads/main")),
        (None, ci_plan.Event("workflow_dispatch", "refs/tags/v0.1.1")),
    ],
    ids=[
        "pull-request",
        "docs-pull-request",
        "release-pull-request",
        "push-to-dev",
        "acceptance",
        "weekly",
        "dispatch",
        "dispatch-on-main",
        "dispatch-on-a-tag",
    ],  # fmt: skip
)
def test_only_a_pushed_tag_publishes(changed, event) -> None:
    """Every other event's publish output is false: a dispatch, even on a tag, never publishes."""
    d = ci_plan.decide(changed, event)
    assert not d.publish
    assert ci_plan.outputs(d, ci_plan.select(d, PLAN), [])["publish"] == "false"


@pytest.mark.parametrize("message", ["citest:fullness", "say citest:full here", "ci:full"])
def test_only_a_line_of_its_own_asks_for_full(message) -> None:
    e = ci_plan.Event("pull_request", "refs/pull/7/merge", "dev", (), (f"x\n\n{message}\n",))
    assert not ci_plan.decide(["src/x.py"], e).full


def test_another_label_is_not_full() -> None:
    e = ci_plan.Event("pull_request", "refs/pull/7/merge", "dev", ("ci:fuller",), ())
    assert not ci_plan.decide(["src/x.py"], e).full


@pytest.mark.parametrize(
    "event",
    [PR_MAIN, SCHEDULE, ci_plan.Event("workflow_dispatch", "refs/heads/main")],
    ids=["release-pull-request", "schedule", "dispatch-on-main"],
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


# ---------------------------------------------------------------------------------------------
# The files an agent's tool loads by itself: quick alone, but a news file and a review, as code

AGENTS_PATHS = [".claude/settings.json", ".claude/hooks/x.sh", "AGENTS.md"]


@pytest.mark.parametrize("path", AGENTS_PATHS)
def test_an_agents_change_runs_quick_alone_and_is_not_documentation(path) -> None:
    """A hook in the agents' settings runs on every machine that opens the repository, so a change
    to it is reviewed; nothing the judge's shards run reads it, so quick alone runs."""
    d = ci_plan.decide([path], PR_DEV)
    assert not d.docs_only and d.agents and not d.judge
    sel = ci_plan.select(d, PLAN)
    assert sel["selected"] == [] and sel["verify"] == [] and sel["build"] is False


def test_an_agents_change_carries_its_news_file_and_its_review() -> None:
    assert _news_refusals(["AGENTS.md"])
    alone = ci_plan.Commit("a" * 40, ("AGENTS.md", NEWS), (AUTHOR,))
    (refusal,) = _review_refusals(_pr(commits=[alone]), changed=("AGENTS.md", NEWS))
    assert "no review file" in refusal
    review = ci_plan.Commit("b" * 40, (REVIEW,), (OTHER,))
    changed = ["AGENTS.md", NEWS, REVIEW]
    d = ci_plan.decide(changed, PR_DEV)
    assert ci_plan.refusals(d, PR_DEV, changed, _pr(commits=[alone, review])) == []


def test_an_agents_change_after_the_review_is_refused() -> None:
    code = ci_plan.Commit("a" * 40, ("src/x.py", NEWS), (AUTHOR,))
    review = ci_plan.Commit("b" * 40, (REVIEW,), (OTHER,))
    hook = ci_plan.Commit("c" * 40, (".claude/settings.json",), (AUTHOR,))
    changed = ("src/x.py", NEWS, REVIEW, ".claude/settings.json")
    (refusal,) = _review_refusals(_pr(commits=[code, review, hook]), changed=changed)
    assert "cccccccccccc" in refusal and ".claude/settings.json" in refusal


def test_an_agents_file_beside_code_runs_the_codes_shards() -> None:
    """A guard: the row takes quick alone only for a change that is the agents' files and
    documentation, never for code beside them."""
    d = ci_plan.decide(["AGENTS.md", "src/x.py"], PR_DEV)
    assert d.runner and d.judge and not d.docs_only


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
    sel = ci_plan.select(ci_plan.decide(None, SCHEDULE), PLAN)
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


LINUX_OWN = [n for n in shards.on(shards.load(), "linux") if PLAN[n].kind == "own"]


def test_coverage_runs_on_every_linux_own_leg_of_a_merge_grade_run_alone() -> None:
    """The runner's coverage is measured in legs that run anyway: every Linux leg of the product's
    own shards, on a run with the merge-grade set (a merge into dev, ci:full, the release shape).
    Codecov merges a commit's uploads into the badge's one number."""
    labelled = ci_plan.Event(
        "pull_request", ref="refs/pull/7/merge", base_ref="dev", labels=("ci:full",)
    )
    for changed, event in ((["src/x.py"], PUSH_DEV), (None, SCHEDULE), (["src/x.py"], labelled)):
        d = ci_plan.decide(changed, event)
        sel = ci_plan.select(d, PLAN)
        assert sel["coverage"] == LINUX_OWN, event
        assert json.loads(ci_plan.outputs(d, sel, [])["coverage"]) == LINUX_OWN
    for changed in (["src/x.py"], ["docs/x.md"]):
        sel = ci_plan.select(ci_plan.decide(changed, PR_DEV), PLAN)
        assert sel["coverage"] == [], changed


def test_the_coverage_shards_are_every_own_shard_of_the_plan_on_linux() -> None:
    """own-rest alone holds the rules and the harness's self-tests, which barely run the runner:
    the product's own shards on Linux are what measure it."""
    assert "own-runner" in LINUX_OWN and "own-rest" in LINUX_OWN
    assert list(ci_plan.COVERAGE_SHARDS) == LINUX_OWN


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
    assert json.loads(got["selected"]) and got["build"] == "false"
    assert json.loads(got["review_refusals"]) == []


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
    assert sel["macos"] == shards.on(shards.load(), "macos") and sel["build"] is False


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


TEMPLATE = paths.REPO / ".github" / "PULL_REQUEST_TEMPLATE.md"


def _filled(who: str, keep_guidance: bool) -> str:
    """The pull request template with its author line filled in, as an author types it: after the
    colon, before the guidance, or in place of it."""
    lines = TEMPLATE.read_text().splitlines()
    (k,) = [k for k, line in enumerate(lines) if line.startswith("Author:")]
    lines[k] = (
        lines[k].replace("Author:", f"Author: {who}", 1) if keep_guidance else f"Author: {who}"
    )
    return "\n".join(lines) + "\n"


@pytest.mark.parametrize("keep_guidance", [True, False], ids=["before the guidance", "in place"])
@pytest.mark.parametrize("who", ["Clay Gendron", AUTHOR], ids=["a person", "a session"])
def test_the_templates_author_line_filled_in_names_the_author(who, keep_guidance) -> None:
    body = _filled(who, keep_guidance)
    assert ci_plan.authors_of(body) == [who]
    (refusal,) = _review_refusals(_pr(_review(reviewer=who), body=body))
    assert "names the author" in refusal


def test_the_unfilled_template_names_no_author() -> None:
    assert ci_plan.authors_of(TEMPLATE.read_text()) == []


@pytest.mark.parametrize(
    "after",
    [
        "Specifications: 999-a-change",
        "**Specifications:** 999-a-change",
        "- every new check seen failing first",
        "- [ ] The Windows legs of this pull request's run were read.",
        "## What changed",
        "| who | what |",
    ],
    ids=["a field", "a bold field", "a list item", "a box", "a heading", "a table"],
)
def test_an_empty_author_line_followed_by_no_name_names_no_one(after) -> None:
    assert ci_plan.authors_of(f"Author:\n\n{after}\n") == []
    assert ci_plan.authors_of(f"- **Author:**  \n{after}\n") == []
    assert ci_plan.authors_of("Author:\n") == []


@pytest.mark.parametrize("who", ["Clay Gendron", AUTHOR], ids=["a person", "a session"])
def test_a_name_on_the_line_after_an_empty_author_line_is_the_author(who) -> None:
    body = f"Author:\n\n{who}\n\nSpecifications: 999-a-change\n"
    assert ci_plan.authors_of(body) == [who]
    assert ci_plan.authors_of(f"Author: <!-- guidance -->\n<!-- more -->\n{who}\n") == [who]
    review = _review(reviewer=who)
    code = ci_plan.Commit("a" * 40, ("src/x.py", NEWS), ())
    pr = _pr(review, commits=[code, ci_plan.Commit("b" * 40, (REVIEW,), ())], body=body)
    (refusal,) = _review_refusals(pr)
    assert "names the author" in refusal


def test_the_filled_template_is_refused_for_nothing_and_a_skip_word_in_its_guidance_is() -> None:
    """The guidance is dropped only to read the author: the squash merge's message is the
    description as written, its comments included, so a skip word inside one is still refused."""
    changed = ["src/x.py", NEWS, REVIEW]
    d = ci_plan.decide(changed, PR_DEV)
    body = _filled(AUTHOR, keep_guidance=True)
    assert ci_plan.refusals(d, PR_DEV, changed, _pr(body=body)) == []
    guided = body.replace("<!-- What changed", "<!-- [skip ci] What changed", 1)
    assert guided != body
    (refusal,) = ci_plan.refusals(d, PR_DEV, changed, _pr(body=guided))
    assert "[skip ci]" in refusal


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


def _plan_outputs(changed: list[str], event, pr) -> dict[str, str]:
    """The outputs the decision job writes for a pull request read whole, as `main` makes them."""
    d = ci_plan.decide(changed, event)
    refused = ci_plan.refusals(d, event, changed, pr)
    return ci_plan.outputs(
        d, ci_plan.select(d, PLAN), refused, ci_plan.review_check(d, event, changed, pr)
    )


def test_the_review_check_is_an_output_of_its_own_and_ci_status_still_reads_it() -> None:
    """The review job reads review_refusals alone: the review file's refusals, never a missing
    news file or a skip word. ci-status keeps them among its own refusals until the ruleset
    requires the review job."""
    changed = ["src/x.py", NEWS, REVIEW]
    pr = _pr(review=_review(verdict="Does not land."))
    out = _plan_outputs(changed, PR_DEV, pr)
    review = json.loads(out["review_refusals"])
    assert review and all("Lands" in r for r in review)
    assert set(review) <= set(json.loads(out["refusals"]))
    no_news = _plan_outputs(["src/x.py", REVIEW], PR_DEV, _pr())
    assert not any(
        "news file" in r and "CHANGELOG" in r for r in json.loads(no_news["review_refusals"])
    )
    assert any("CHANGELOG" in r for r in json.loads(no_news["refusals"]))
    skip = _pr()
    skip.title = "x [skip ci]"
    assert json.loads(_plan_outputs(changed, PR_DEV, skip)["review_refusals"]) == []


def test_the_review_check_asks_nothing_of_documentation_or_of_main() -> None:
    assert json.loads(_plan_outputs(["docs/index.md"], PR_DEV, _pr())["review_refusals"]) == []
    out = _plan_outputs(["src/x.py"], PR_MAIN, _pr(review=_review(verdict="No.")))
    assert json.loads(out["review_refusals"]) == []
    missing = _plan_outputs(["src/x.py", NEWS], PR_DEV, _pr())
    assert json.loads(missing["review_refusals"])  # code with no review file


def test_a_pull_request_whose_base_cannot_be_read_is_refused_its_review() -> None:
    """With no change read, no review file was read either: the review check fails closed
    rather than saying a review it never read holds."""
    d = ci_plan.decide(None, PR_DEV)
    refused = ci_plan.review_check(d, PR_DEV, None, None)
    assert refused and "could not be read" in refused[0]
    assert refused[0] in ci_plan.refusals(d, PR_DEV, None, None)
    assert ci_plan.review_check(ci_plan.decide(None, PR_MAIN), PR_MAIN, None, None) == []


def test_a_reused_run_still_reads_the_review() -> None:
    """The review file's push re-uses the code head's run, every output false, and the review
    job reads that push's review file."""
    changed = ["src/x.py", NEWS, REVIEW]
    d = ci_plan.decide(changed, PR_DEV, reused=(7, "run 7, green on 111111111111"))
    bad = _pr(review=_review(verdict="Does not land."))
    assert ci_plan.review_check(d, PR_DEV, changed, bad)
    assert ci_plan.review_check(d, PR_DEV, changed, _pr()) == []


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


def test_a_run_red_only_on_its_review_and_ci_status_is_reused() -> None:
    """The review job's verdict is not the code's: a run whose only red jobs are review and
    ci-status, which waited for the review file, is re-used by the review file's push and by an
    edit."""
    waiting = {**GREEN, "review": "failure"}
    runs = [{"databaseId": 7, "headSha": CODE_HEAD, "status": "completed"}]
    assert _reuse(runs, {7: waiting})[0] == 7
    assert _edit([_run(THIS_RUN, status="in_progress"), _run(7)], {7: waiting})[0] == 7
    judge_red = {**waiting, "judge (windows-2025, own-a)": "failure"}
    assert _reuse(runs, {7: judge_red})[0] is None
    assert _edit([_run(7)], {7: judge_red}) == (None, "")


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


# GitHub's second form: a message that ends with the trailer line skip-checks: true, in either
# spelling. The description's line endings may be a browser's, \r\n.

TRAILERS = ["skip-checks: true", "skip-checks:true", "Skip-Checks: TRUE", "  skip-checks: true  "]
TRAILER_CASES = {
    **{
        f"{trailer!r} {name}": ("A change", BODY + eol + trailer + eol)
        for trailer in TRAILERS
        for name, eol in (("lf", "\n"), ("crlf", "\r\n"))
    },
    "the title alone": ("skip-checks: true", ""),
}


@pytest.mark.parametrize(("title", "body"), TRAILER_CASES.values(), ids=list(TRAILER_CASES))
def test_the_skip_checks_trailer_is_refused(title, body) -> None:
    pr = _pr(body=body)
    pr.title = title
    changed = ["src/x.py", NEWS, REVIEW]
    refused = [
        r
        for r in ci_plan.refusals(ci_plan.decide(changed, PR_DEV), PR_DEV, changed, pr)
        if "skip-checks" in r
    ]
    assert len(refused) == 1, refused


@pytest.mark.parametrize(
    "line",
    ["skip-checks: false", "the skip-checks: true trailer is refused", "skip-checks: truely"],
)
def test_a_line_that_is_no_skip_trailer_is_not_refused(line) -> None:
    """A guard: a line that is no trailer, or a sentence that names one, is not refused."""
    pr = _pr(body=BODY + "\n" + line + "\n")
    pr.title = "A change"
    changed = ["src/x.py", NEWS, REVIEW]
    assert ci_plan.refusals(ci_plan.decide(changed, PR_DEV), PR_DEV, changed, pr) == []


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
    ("M", "context/release-claims.toml"),
    ("M", "context/release-claims-history.md"),
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


def test_the_preparation_may_not_carry_an_agents_file() -> None:
    """The preparation asks no review file, so the agents' settings ride in it never."""
    extra = ("M", ".claude/settings.json")
    assert not ci_plan.is_release_preparation([*PREPARATION, extra], version_line_only=True)


def test_only_the_version_line_may_move_in_the_version_file() -> None:
    bumped = '--- a/x\n+++ b/x\n@@ -3 +3 @@\n-__version__ = "0.1.0"\n+__version__ = "0.1.1"\n'
    assert ci_plan.version_line_only(bumped)
    more = bumped + "@@ -9,0 +10 @@\n+import os\n"
    assert not ci_plan.version_line_only(more)
    assert not ci_plan.version_line_only("")


# The ledger in a preparation: date's move, with any claim block the preparation adds, or the
# preparation is refused, named.

LEDGER_HEADER = "# The release claims ledger.\n# Appended by its pull request.\n"
LEDGER_BLOCK = (
    '[[claim]]\nspec = "140"\ngrows = ["tests/checks/test_v1_3_x.py::test_slow"]\n'
    'growth = "a pin moved"\n'
)
LEDGER_HISTORY = "# The release claims, by release\n\nIntro.\n\n## 0.1.0\n\nMoved.\n"


def _moved(ledger: str = LEDGER_HEADER + "\n" + LEDGER_BLOCK) -> tuple[str, str]:
    return news.move_ledger(ledger, LEDGER_HISTORY, "0.1.1", "2026-10-26")


def test_a_preparation_whose_ledger_is_dates_exact_move_is_a_preparation() -> None:
    head_ledger, head_history = _moved()
    base = (LEDGER_HEADER + "\n" + LEDGER_BLOCK, LEDGER_HISTORY)
    assert ci_plan.ledger_move_refusal(base, (head_ledger, head_history), "0.1.1") is None
    assert ci_plan.ledger_move_refusal(base, base, "0.1.1") is None  # the ledger not touched


EXTRA = (
    '[[claim]]\nspec = "999"\npasses = ["tests/checks/test_v1_3_x.py::test_new"]\n'
    'fewer = "two tests moved to the release tier"\n'
)


def test_a_preparation_may_add_a_claim_block_to_the_ledger() -> None:
    """The preparation is where a reason missing at a merge is written, by the author who knows
    it: a block added before date's move (so moved under the version beside the base's) or after
    it (so left in the ledger) is admitted, of any claim's kind."""
    base = (LEDGER_HEADER + "\n" + LEDGER_BLOCK, LEDGER_HISTORY)
    before = _moved(LEDGER_HEADER + "\n" + LEDGER_BLOCK + "\n" + EXTRA)
    assert ci_plan.ledger_move_refusal(base, before, "0.1.1") is None
    head_ledger, head_history = _moved()
    after = (head_ledger + "\n" + EXTRA, head_history)
    assert ci_plan.ledger_move_refusal(base, after, "0.1.1") is None
    empty = (LEDGER_HEADER, LEDGER_HISTORY)
    assert ci_plan.ledger_move_refusal(empty, _moved(LEDGER_HEADER + "\n" + EXTRA), "0.1.1") is None


def test_a_preparation_that_edits_or_drops_a_ledger_block_is_refused_named() -> None:
    """The base's blocks are reasons already given: date moves them whole, and a preparation that
    edits or drops one, breaks an added block's shape or rewrites the header is refused."""
    base = (LEDGER_HEADER + "\n" + LEDGER_BLOCK, LEDGER_HISTORY)
    head_ledger, head_history = _moved()
    edited = head_history.replace("a pin moved", "a pin moved twice")
    why = ci_plan.ledger_move_refusal(base, (head_ledger, edited), "0.1.1")
    assert why and "dropped or edited" in why, why
    dropped = _moved(LEDGER_HEADER + "\n" + EXTRA)
    assert "dropped or edited" in ci_plan.ledger_move_refusal(base, dropped, "0.1.1")
    # A key or sub-table appended after the base's last block continues that block, under its
    # spec: an edit of it, not an added block.
    tail = '[claim.judge]\n"tests/known_gaps.toml" = "a new allowance"\n'
    continued = _moved(LEDGER_HEADER + "\n" + LEDGER_BLOCK + tail)
    why_tail = ci_plan.ledger_move_refusal(base, continued, "0.1.1")
    assert why_tail and "[[claim]]" in why_tail, why_tail
    broken = '[[claim]]\nspec = "999"\ngrows = ["x"]\n'  # grows without its growth
    kept = ci_plan.ledger_move_refusal(base, (head_ledger + "\n" + broken, head_history), "0.1.1")
    assert kept and "growth" in kept, kept
    renamed = ci_plan.ledger_move_refusal(base, ("# another\n", head_history), "0.1.1")
    assert renamed and "header" in renamed, renamed
    moved_by_hand = head_history.replace("Moved by `release/version.py date`", "Moved", 1)
    assert "no section" in ci_plan.ledger_move_refusal(base, (head_ledger, moved_by_hand), "0.1.1")
    changed = [VERSION_FILE, "CHANGELOG.md", *ci_plan.LEDGER_FILES]
    d = ci_plan.decide(changed, PR_DEV, preparation_refusal=why)
    assert not d.docs_only and d.judge
    assert any(why in r for r in ci_plan.refusals(d, PR_DEV, changed, _pr(commits=[])))


# ---------------------------------------------------------------------------------------------
# A path git would quote is read by its name

QUOTED = [
    ".github/workflows/\u00e9.yml",
    "src/wasi_python/\u00e9.py",
    'src/a"b.py',
    "src/tab\there.py",
    "src/new\nline.py",
]


@pytest.fixture
def quoted_repo(tmp_path, monkeypatch):
    """A repository whose second commit adds five names git quotes, made in the index alone, so
    no such name is ever written to a disk."""
    git = shutil.which("git")
    if git is None:
        pytest.skip("needs: git")
    config = tmp_path / "gitconfig"
    config.write_text("[user]\n\tname = t\n\temail = t@t\n[commit]\n\tgpgsign = false\n")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    repo = tmp_path / "repo"
    subprocess.run([git, "init", "-q", "-b", "dev", str(repo)], check=True)

    def run(*args: str, stdin: bytes | None = None) -> str:
        return (
            subprocess.run(
                [git, "-C", str(repo), *args], check=True, capture_output=True, input=stdin
            )
            .stdout.decode()
            .strip()
        )

    run("commit", "-q", "--allow-empty", "-m", "start")
    base = run("rev-parse", "HEAD")
    blob = run("hash-object", "-w", "--stdin", stdin=b"x\n")
    for path in QUOTED:  # git for Windows refuses a quote, a tab or a newline unless told
        run("-c", "core.protectNTFS=false", "update-index", "--add", "--cacheinfo",
            f"100644,{blob},{path}")  # fmt: skip
    run("commit", "-q", "-m", "quoted")
    return repo, base, run("rev-parse", "HEAD")


def test_a_path_git_quotes_is_read_by_its_name(quoted_repo) -> None:
    repo, base, head = quoted_repo
    assert sorted(ci_plan._diff(base, head, repo=repo)) == sorted(QUOTED)


def test_a_commits_quoted_paths_are_read_by_their_names(quoted_repo) -> None:
    repo, base, head = quoted_repo
    (commit,) = ci_plan.read_pull_request(repo, base, head, BODY, []).commits
    assert sorted(commit.paths) == sorted(QUOTED)


def test_the_status_pairs_read_a_quoted_path(quoted_repo) -> None:
    repo, base, head = quoted_repo
    assert sorted(ci_plan.status_pairs(base, head, repo=repo)) == sorted(("A", p) for p in QUOTED)


def test_a_quoted_workflow_path_runs_full_and_a_quoted_runner_path_runs_macos(quoted_repo) -> None:
    repo, base, head = quoted_repo
    d = ci_plan.decide(ci_plan._diff(base, head, repo=repo), PR_DEV)
    assert d.workflow and d.full and d.runner
    assert ci_plan.select(d, PLAN)["macos"]


# ---------------------------------------------------------------------------------------------
# An edit that leaves the base alone re-uses the newest run on its head when that run is green

EDIT_HEAD = "4" * 40
THIS_RUN = 100


def _edited() -> object:
    """A pull request into dev whose description was edited, its base left alone."""
    return ci_plan.Event("pull_request", ref="refs/pull/7/merge", base_ref="dev", action="edited")


def _run(run_id: int, sha: str = EDIT_HEAD, status: str = "completed") -> dict:
    return {"databaseId": run_id, "headSha": sha, "status": status}


def _edit(runs, jobs):
    return ci_plan.reusable_after_edit(EDIT_HEAD, runs, THIS_RUN, jobs_of=lambda i: jobs.get(i))


def test_an_edit_reuses_the_newest_green_run_on_its_head() -> None:
    run, why = _edit([_run(THIS_RUN, status="in_progress"), _run(7)], {7: GREEN})
    assert run == 7 and "run 7" in why
    changed = ["src/x.py", NEWS, REVIEW]
    d = ci_plan.decide(changed, _edited(), reused=(run, why))
    out = ci_plan.outputs(d, ci_plan.select(d, PLAN), [])
    assert d.quiet and {k for k, v in out.items() if v == "true"} == set()
    assert any("run 7" in w for w in d.why)


NOT_GREEN = {
    "failed": ([_run(7)], {7: {**GREEN, "judge (windows-2025, own-a)": "failure"}}),
    "cancelled": ([_run(7)], {7: {**GREEN, "gather the shards' records": "cancelled"}}),
    "unfinished": ([_run(7, status="in_progress")], {7: GREEN}),
}


@pytest.mark.parametrize("state", list(NOT_GREEN))
def test_an_edit_after_a_run_that_is_not_green_runs_the_selection(state) -> None:
    runs, jobs = NOT_GREEN[state]
    assert _edit(runs, jobs) == (None, "")


def test_an_edit_after_a_run_on_another_head_runs_the_selection() -> None:
    assert _edit([_run(7, sha=CODE_HEAD)], {7: GREEN}) == (None, "")


def test_an_edit_never_reuses_an_older_green_run_behind_the_newest() -> None:
    """A retarget's run, cancelled by a later edit, stands before a green run into dev: the edit
    may not reach past it, or the release pull request would wear the narrow run's green."""
    cancelled = {**GREEN, "judge (macos-15, own-a)": "cancelled"}
    assert _edit([_run(9), _run(7)], {9: cancelled, 7: GREEN}) == (None, "")


def test_a_base_change_never_reuses() -> None:
    env = {"GITHUB_EVENT_NAME": "pull_request", "GITHUB_REF": "refs/pull/8/merge",
           "GITHUB_BASE_REF": "main", "PLAN_ACTION": "edited"}  # fmt: skip
    assert ci_plan.event_of(env).edited
    assert not ci_plan.event_of({**env, "PLAN_OLD_BASE": "dev"}).edited
    assert not ci_plan.event_of({**env, "PLAN_ACTION": "synchronize"}).edited


def test_an_edit_skips_its_own_run() -> None:
    red = {**GREEN, "quick": "failure"}
    assert _edit([_run(THIS_RUN), _run(7)], {THIS_RUN: GREEN, 7: red}) == (None, "")
    assert _edit([_run(THIS_RUN), _run(7)], {THIS_RUN: red, 7: GREEN})[0] == 7


def test_an_edit_reuses_a_run_that_was_itself_a_reuse() -> None:
    quiet = {"plan": "success", "quick": "success", "gather the shards' records": "skipped",
             "verify (ubuntu-24.04)": "skipped", "ci-status": "success"}  # fmt: skip
    assert _edit([_run(9), _run(7)], {9: quiet, 7: GREEN})[0] == 9


def test_an_edit_reads_its_description_anew() -> None:
    changed = ["src/x.py", NEWS, REVIEW]
    d = ci_plan.decide(changed, _edited(), reused=(7, "re-uses run 7"))
    pr = _pr(body=BODY + "\nnow [skip ci]\n")
    assert any("[skip ci]" in r for r in ci_plan.refusals(d, _edited(), changed, pr))


def _listed(run_id: int, owner: str, number: int = 7) -> dict:
    """One run of the Actions runs listing, on the edit's head, of pull request `number`."""
    return {"id": run_id, "head_sha": EDIT_HEAD, "status": "completed", "conclusion": "success",
            "head_repository": {"full_name": owner},
            "pull_requests": [{"number": number}]}  # fmt: skip


KEPT = {"databaseId": 7, "headSha": EDIT_HEAD, "status": "completed", "conclusion": "success"}


def test_a_run_from_a_fork_is_never_reused() -> None:
    """A fork's branch of the same name at the same head is listed by branch and event alike;
    only the run's head repository tells them apart."""
    payload = {"workflow_runs": [_listed(8, "someone/wasi-python"),
                                 _listed(7, "ClayGendron/wasi-python")]}  # fmt: skip
    assert ci_plan.runs_of(payload, "ClayGendron/wasi-python", 7) == [KEPT]


def test_a_run_of_another_pull_request_on_the_same_branch_and_head_is_never_reused() -> None:
    """One branch may be the head of two pull requests, into dev and into main: their runs share
    the listing, and only a run's pull requests say which one it judged."""
    payload = {"workflow_runs": [_listed(8, "ClayGendron/wasi-python", number=9),
                                 _listed(7, "ClayGendron/wasi-python")]}  # fmt: skip
    assert ci_plan.runs_of(payload, "ClayGendron/wasi-python", 7) == [KEPT]
    assert ci_plan.green_runs({"GH_TOKEN": "x", "GITHUB_REPOSITORY": "o/r"}, "b") is None
