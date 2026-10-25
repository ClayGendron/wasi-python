"""release/ci_plan.py: which jobs a run of the release workflow needs, from the paths it changes.

Each row of the decision table, the two pushes that set every output false, what `full` takes,
the shards each shape selects, and the outputs as the workflow reads them."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys

import pytest

from harness import paths, shards

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
    assert {k for k, v in out.items() if v == "true"} == set()


@pytest.mark.parametrize(
    "changed",
    [
        ACCEPT + ["src/x.py"],
        ["context/progress/accepted.json"],
        ["context/progress/history-00060.jsonl"],
        ["context/progress/accepted.json", "context/progress/README.md"],
        ["context/progress/accepted.json", "context/progress/history-00060.jsonl.bak"],
    ],
)
def test_anything_more_or_less_than_an_acceptance_is_full(changed) -> None:
    d = ci_plan.decide(changed, PUSH_DEV)
    assert not d.quiet and d.full


def test_the_acceptance_paths_on_a_pull_request_are_refused() -> None:
    d = ci_plan.decide(ACCEPT, PR_DEV)
    assert d.progress and not d.quiet
    refusals = ci_plan.refusals(d, PR_DEV, ACCEPT)
    assert len(refusals) == 1 and "context/progress/accepted.json" in refusals[0]


def test_progress_is_refused_on_a_pull_request_only() -> None:
    changed = ["context/progress/accepted.json", "src/x.py"]
    assert ci_plan.refusals(ci_plan.decide(changed, PR_DEV), PR_DEV, changed)
    assert ci_plan.refusals(ci_plan.decide(changed, PUSH_DEV), PUSH_DEV, changed) == []
    assert ci_plan.refusals(ci_plan.decide(["src/x.py"], PR_DEV), PR_DEV, ["src/x.py"]) == []


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
