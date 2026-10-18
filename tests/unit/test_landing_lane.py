"""The landing lane is guarded (spec 029): each rule against temporary git repositories made with
`git` only, under pytest's tmp_path. Nothing here measures time."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from harness import needs, paths, plugin, sameness, scan, scoreboard

GIT = shutil.which("git")
HISTORY = "context/progress/history.jsonl"
ACCEPTED = "context/progress/accepted.json"


RULES_FILE = paths.REPO / "tests" / "checks" / "test_rules.py"  # before any case moves REPO


def _load_rules():
    """The real rules checks, so each case runs the check itself, not a copy of its logic."""
    spec = importlib.util.spec_from_file_location("wasi_python_rules_checks", RULES_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rule_1() -> None:
    _load_rules().test_the_newest_acceptance_sits_on_the_commit_it_judged()


def rule_3() -> None:
    _load_rules().test_main_is_linear()


@pytest.fixture(autouse=True)
def quiet_git(tmp_path_factory, monkeypatch):
    """git without the caller's settings (signing, hooks, a default branch), and an identity."""
    if GIT is None:
        pytest.skip("needs: git")
    config = tmp_path_factory.getbasetemp() / "gitconfig"
    config.write_text("[user]\n\tname = t\n\temail = t@t\n[commit]\n\tgpgsign = false\n")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


def git(repo: Path, *args: str) -> str:
    r = subprocess.run([GIT, "-C", str(repo), *args], capture_output=True, text=True, check=False)
    assert r.returncode == 0, (args, r.stderr)
    return r.stdout.strip()


def write(repo: Path, rel: str, text: str) -> None:
    (repo / rel).parent.mkdir(parents=True, exist_ok=True)
    (repo / rel).write_text(text)


def commit(repo: Path, message: str, *files: str) -> str:
    """Commit `files` alone, or everything when none is named."""
    git(repo, "add", "-A", "--", *(files or ["."]))
    git(repo, "commit", "-q", "-m", message, "--", *files)
    return git(repo, "rev-parse", "HEAD")


def make_repo(path: Path) -> Path:
    git(path.parent, "init", "-q", "-b", "main", str(path))
    write(path, "src/code.py", "x = 1\n")
    write(path, "tests/conftest.py", "")
    write(path, ACCEPTED, "{}\n")
    write(path, HISTORY, "")
    commit(path, "start")
    return path


NO_KEY = object()


def accept(repo: Path, named: str | None = None, *, dirty=False, lane: bool = True):
    """Append an acceptance line naming `named` (HEAD by default), as `--accept` would, and write
    accepted.json; `lane` says whether the judge that wrote it is 029's (it knows this file).
    `dirty=NO_KEY` leaves the key out."""
    lines = [x for x in (repo / HISTORY).read_text().splitlines() if x.strip()]
    named = named or git(repo, "rev-parse", "HEAD")
    line = {"n": len(lines) + 1, "commit": named}
    if dirty is not NO_KEY:
        line["dirty"] = dirty
    (repo / HISTORY).write_text("".join(x + "\n" for x in [*lines, json.dumps(line)]))
    files = {scan.FIRST_CLEAN_JUDGE: "x"} if lane else {"tests/conftest.py": "x"}
    write(repo, ACCEPTED, json.dumps({"judge": {"files": files}, "n": line["n"]}) + "\n")


def commit_acceptance(repo: Path, *more: str) -> str:
    return commit(repo, "Accept", ACCEPTED, HISTORY, *more)


@pytest.fixture
def repo(tmp_path, monkeypatch) -> Path:
    """A temporary repository the rules read in place of this one."""
    r = make_repo(tmp_path / "repo")
    monkeypatch.setattr(paths, "REPO", r)
    return r


# ---------------------------------------------------------------------------------------------
# Rule 1: an acceptance sits on the commit it judged, and carries nothing else (Decision 1)


def test_an_acceptance_on_its_commit_carrying_only_the_two_files_holds(repo) -> None:
    write(repo, "src/code.py", "x = 2\n")
    commit(repo, "code")
    accept(repo)
    commit_acceptance(repo)
    rule_1()


def test_an_acceptance_carried_across_a_rebase_fails_naming_both_commits(repo) -> None:
    git(repo, "checkout", "-q", "-b", "side")
    write(repo, "src/code.py", "x = 2\n")
    judged = commit(repo, "the side's code")
    accept(repo)
    commit_acceptance(repo)
    git(repo, "checkout", "-q", "main")
    write(repo, "src/other.py", "y = 1\n")
    commit(repo, "main moved")
    git(repo, "checkout", "-q", "side")
    git(repo, "rebase", "-q", "main")
    parent = git(repo, "rev-parse", "HEAD^1")
    assert parent != judged
    with pytest.raises(AssertionError) as e:
        rule_1()
    assert judged[:12] in str(e.value) and parent[:12] in str(e.value), str(e.value)


def test_an_acceptance_that_also_carries_code_fails(repo) -> None:
    accept(repo)
    write(repo, "src/code.py", "x = 3\n")
    commit_acceptance(repo, "src/code.py")
    with pytest.raises(AssertionError, match="src/code.py"):
        rule_1()


def test_an_acceptance_appended_but_not_committed_holds(repo) -> None:
    accept(repo)
    commit_acceptance(repo)
    write(repo, "src/code.py", "x = 4\n")
    commit(repo, "next change")
    accept(repo)  # the lane between accepting and committing
    rule_1()


def test_a_dirty_acceptance_by_this_judge_fails_and_an_older_one_is_not_rejudged(repo) -> None:
    accept(repo, dirty=True, lane=False)
    commit_acceptance(repo)
    rule_1()
    write(repo, "src/code.py", "x = 5\n")
    commit(repo, "code")
    accept(repo, dirty=True)
    commit_acceptance(repo)
    with pytest.raises(AssertionError, match="dirty"):
        rule_1()


@pytest.mark.parametrize("dirty", [NO_KEY, None], ids=["no key", "null"])
def test_an_acceptance_by_this_judge_must_say_dirty_false(repo, dirty) -> None:
    accept(repo, dirty=dirty)
    commit_acceptance(repo)
    with pytest.raises(AssertionError, match="dirty"):
        rule_1()


def test_an_acceptance_named_by_a_merge_commits_second_parent_fails(repo) -> None:
    """First parent, not any parent: a merge whose second parent is the named commit fails."""
    git(repo, "checkout", "-q", "-b", "side")
    git(repo, "commit", "-q", "--allow-empty", "-m", "the side's empty change")
    judged = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-q", "main")
    write(repo, "src/code.py", "x = 9\n")
    first = commit(repo, "main's code")
    git(repo, "merge", "-q", "--no-ff", "--no-commit", "side")
    accept(repo, judged)
    commit(repo, "Accept as a merge")
    assert git(repo, "rev-parse", "HEAD^2") == judged
    with pytest.raises(AssertionError, match=f"sits on {first[:12]}"):
        rule_1()


def test_rule_1_is_blocked_in_a_shallow_clone(repo, tmp_path, monkeypatch) -> None:
    for n in range(2):
        write(repo, "src/code.py", f"x = {n}\n")
        commit(repo, "code")
        accept(repo)
        commit_acceptance(repo)
    shallow = tmp_path / "shallow"
    git(tmp_path, "clone", "-q", "--depth", "1", f"file://{repo}", str(shallow))
    monkeypatch.setattr(paths, "REPO", shallow)
    assert needs.VOCABULARY["git"].met()
    with pytest.raises(pytest.skip.Exception, match="needs: git history"):
        rule_1()
    with pytest.raises(pytest.skip.Exception, match="needs: git history"):
        rule_3()


# ---------------------------------------------------------------------------------------------
# Rule 3: main is linear (Decision 3)


def test_a_merge_commit_fails_and_a_linear_history_holds(repo) -> None:
    write(repo, "src/code.py", "x = 6\n")
    commit(repo, "linear")
    rule_3()
    git(repo, "checkout", "-q", "-b", "side", "HEAD~1")
    write(repo, "src/other.py", "y = 2\n")
    commit(repo, "side")
    git(repo, "checkout", "-q", "main")
    git(repo, "merge", "-q", "--no-ff", "-m", "a merge", "side")
    merge = git(repo, "rev-parse", "HEAD")
    with pytest.raises(AssertionError, match=merge[:12]):
        rule_3()


def test_this_repository_is_linear() -> None:
    rule_3()


# ---------------------------------------------------------------------------------------------
# dirty: a change the judge could see (Decision 2)


def test_untracked_files_outside_the_judge_are_clean_and_a_tracked_change_is_dirty(repo) -> None:
    write(repo, ".idea/workspace.xml", "<x/>\n")
    write(repo, "context/research/2026-10-17-a-draft/memo.md", "# draft\n")
    write(repo, HISTORY, '{"n": 1}\n')  # an acceptance not yet committed
    assert paths.dirty_path() is None
    assert plugin.run_meta()["dirty"] is False
    write(repo, "README.md", "edited\n")
    commit(repo, "readme")
    write(repo, "README.md", "edited again\n")
    assert paths.dirty_path() == "README.md"
    assert plugin.run_meta()["dirty"] is True


@pytest.mark.parametrize(
    "rel",
    [
        "tests/test_new.py",
        "src/new.py",
        "uv.lock",
        "deep/conftest.py",
        "context/specifications/030-a-draft.md",
        "context/reviews/029-a-review.md",
        "context/upstream/patches/a-draft.md",
    ],
)
def test_an_untracked_judge_input_is_dirty(repo, rel) -> None:
    """The rules read specifications, reviews and patch drafts: an untracked one there can turn a
    rule green on disk that the commit fails (the build review, finding 3)."""
    write(repo, rel, "\n")
    assert paths.dirty_path() == rel


def test_a_tracked_change_under_context_is_dirty(repo) -> None:
    write(repo, "context/specifications/001-a-spec.md", "# one\n")
    commit(repo, "a spec")
    write(repo, "context/specifications/001-a-spec.md", "# one, edited\n")
    assert paths.dirty_path() == "context/specifications/001-a-spec.md"


# ---------------------------------------------------------------------------------------------
# Only the lane accepts (Decision 4), and a dirty acceptance is refused when made (Decision 2)


WORKTREE_LINE = (
    "accept: only the landing lane accepts, in the main tree (constitution §5.7); "
    "this is a linked worktree"
)


@pytest.fixture
def lane(tmp_path, monkeypatch) -> tuple[Path, Path]:
    """A main tree and a linked worktree of it, outside it."""
    main = make_repo(tmp_path / "main")
    worktree = tmp_path / "wt"
    git(main, "worktree", "add", "-q", "-b", "spec/999-x", str(worktree))
    return main, worktree


def test_a_linked_worktree_is_told_from_the_main_tree(lane) -> None:
    main, worktree = lane
    assert paths.linked_worktree(main) is False
    assert paths.linked_worktree(worktree) is True
    assert paths.linked_worktree(worktree / "src") is True


def test_the_refusal_is_keyed_on_the_folder_written(lane, tmp_path) -> None:
    main, worktree = lane
    own, mains = worktree / "context" / "progress", main / "context" / "progress"
    link = tmp_path / "link"
    link.symlink_to(mains, target_is_directory=True)
    for target in (own, mains, link, worktree / "context" / ".." / "context" / "progress"):
        assert plugin.accept_refusal("x", target, worktree) == WORKTREE_LINE, target
    upper = worktree / "Context" / "Progress"
    if upper.exists():  # a filesystem that ignores case (macOS by default)
        assert plugin.accept_refusal("x", upper, worktree) == WORKTREE_LINE
    assert plugin.accept_refusal("x", tmp_path / "elsewhere", worktree) is None
    assert plugin.accept_refusal(None, own, worktree) is None  # --partial and the rest
    assert plugin.accept_refusal("x", mains, main) is None


def test_a_dirty_acceptance_is_refused_naming_the_path(lane, tmp_path) -> None:
    main, worktree = lane
    write(main, "src/code.py", "x = 7\n")
    refusal = plugin.accept_refusal("x", main / "context" / "progress", main)
    assert refusal is not None and "src/code.py" in refusal and "dirty" in refusal
    assert plugin.accept_refusal("x", tmp_path / "elsewhere", main) is None
    write(worktree, "src/code.py", "x = 8\n")  # both apply: the worktree's line is reported
    assert plugin.accept_refusal("x", worktree / "context" / "progress", worktree) == WORKTREE_LINE


DURING_THE_RUN = """
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.goal("rules")

def test_meanwhile():
    {action}
"""
EDIT = "Path(r'{repo}/src/code.py').write_text('x = 10\\n')"
MOVE = "subprocess.run(['git', '-C', r'{repo}', 'commit', '-q', '--allow-empty', '-m', 'm'])"


@pytest.mark.parametrize(
    "action, why", [(EDIT, "dirty"), (MOVE, "HEAD moved")], ids=["edit", "commit"]
)
def test_a_change_during_the_run_refuses_the_acceptance(repo, pytester, action, why) -> None:
    """Checked again when the acceptance is written (the build review, finding 2): a tracked edit
    or a new commit made while the judge runs refuses it, and nothing is written."""
    progress = repo / "context" / "progress"
    before = [(progress / f).read_bytes() for f in ("accepted.json", "history.jsonl")]
    pytester.makepyfile(test_inner=DURING_THE_RUN.format(action=action.format(repo=repo)))
    (pytester.path / "gaps.toml").write_text("")
    result = pytester.runpytest(
        "-p",
        "harness.plugin",
        "--progress-dir",
        str(progress),
        "--progress-latest",
        str(pytester.path / "latest.json"),
        "--known-gaps",
        str(pytester.path / "gaps.toml"),
        "--accept",
        "x",
    )
    assert result.ret == 1, result.stdout.str()[-2000:]
    result.stdout.fnmatch_lines([f"*--accept refused*{why}*"])
    assert [(progress / f).read_bytes() for f in ("accepted.json", "history.jsonl")] == before


def test_without_git_accept_proceeds(tmp_path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    assert paths.linked_worktree(plain) is False
    assert plugin.accept_refusal("x", plain / "context" / "progress", plain) is None


# ---------------------------------------------------------------------------------------------
# End to end, in a linked worktree of a temporary clone that carries this tree's judge


@pytest.fixture(scope="module")
def clone_worktree(tmp_path_factory) -> Path:
    if GIT is None:
        pytest.skip("needs: git")
    root = tmp_path_factory.mktemp("lane")
    env = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": str(root / "gitconfig"),
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    (root / "gitconfig").write_text("[user]\n\tname = t\n\temail = t@t\n")

    def run(cwd: Path, *args: str) -> str:
        r = subprocess.run(
            [GIT, "-C", str(cwd), *args], capture_output=True, text=True, env=env, check=False
        )
        assert r.returncode == 0, (args, r.stderr)
        return r.stdout

    clone = root / "repo"
    run(root, "clone", "-q", str(paths.REPO), str(clone))
    # The judge as it is on disk now (this tree may hold it uncommitted), committed in the clone.
    listed = run(paths.REPO, "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--")
    wanted = ("tests/", "pyproject.toml", "uv.lock")
    for rel in sorted({p for p in listed.split("\0") if p.startswith(wanted)}):
        source, dest = paths.REPO / rel, clone / rel
        if source.is_file():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
        elif dest.is_file():
            dest.unlink()
    run(clone, "add", "-A")
    run(clone, "commit", "-q", "--allow-empty", "-m", "this tree's judge")
    worktree = root / "wt"
    run(clone, "worktree", "add", "-q", "-b", "spec/999-x", str(worktree))
    return worktree


def judge(worktree: Path, *args: str) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "PYTEST_ADDOPTS"}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", *args],
        cwd=worktree,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


ONE_CHECK = "tests/checks/test_rules.py::test_known_gaps_are_well_formed"


@pytest.mark.parametrize("cores", [[], ["-n", "2"]], ids=["serial", "-n 2"])
def test_accept_in_a_worktree_is_refused_before_collection(clone_worktree, cores) -> None:
    history = clone_worktree / HISTORY
    before = history.read_bytes()
    r = judge(clone_worktree, ONE_CHECK, *cores, "--accept", "x")
    assert r.returncode == 1, r.stdout[-2000:] + r.stderr[-2000:]
    assert WORKTREE_LINE in r.stderr, r.stderr
    assert "collected" not in r.stdout, r.stdout[-2000:]
    assert history.read_bytes() == before
    assert not (clone_worktree / "build" / "progress" / "latest.json").exists()


def test_accept_elsewhere_and_partial_proceed_in_a_worktree(clone_worktree, tmp_path) -> None:
    before = (clone_worktree / HISTORY).read_bytes()
    elsewhere = tmp_path / "progress"
    r = judge(clone_worktree, ONE_CHECK, "--accept", "x", "--progress-dir", str(elsewhere))
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    assert (elsewhere / "history.jsonl").is_file()
    r = judge(clone_worktree, ONE_CHECK, "--partial", "no artifacts here")
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    assert (clone_worktree / HISTORY).read_bytes() == before


MEANWHILE = """
import os
import subprocess

import pytest

pytestmark = pytest.mark.goal("rules")

def test_meanwhile():
    subprocess.run(["git", "-C", os.getcwd(), "commit", "-q", "--allow-empty", "-m", "m"])
"""


def test_the_guards_hold_under_several_cores_in_a_main_tree(clone_worktree) -> None:
    """Spec 052, criterion 4: under -n 2 the controller refuses once, and nothing is written: on a
    dirty tree before collection, and when HEAD moves during the run (a worker commits)."""
    main = clone_worktree.parent / "repo"  # the clone itself: a main tree
    history = main / HISTORY
    before = history.read_bytes()
    start = subprocess.run(
        [GIT, "-C", str(main), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    probe = main / "tests" / "unit" / "test_probe_052.py"
    try:
        probe.write_text(MEANWHILE)  # untracked under tests/: a dirty tree
        r = judge(main, ONE_CHECK, "-n", "2", "--accept", "x")
        assert r.returncode == 1, r.stdout[-2000:] + r.stderr[-2000:]
        assert "dirty" in r.stderr and "collected" not in r.stdout, r.stderr[-2000:]
        assert history.read_bytes() == before
        subprocess.run([GIT, "-C", str(main), "add", str(probe)], check=True)
        subprocess.run([GIT, "-C", str(main), "commit", "-q", "-m", "probe"], check=True)
        r = judge(main, str(probe.relative_to(main)), "-n", "2", "--accept", "x", "--partial", "c")
        assert r.returncode == 1, r.stdout[-2000:] + r.stderr[-2000:]
        assert r.stdout.count("--accept refused") == 1, r.stdout[-2000:]
        assert "HEAD moved" in r.stdout, r.stdout[-2000:]
        assert history.read_bytes() == before
    finally:
        subprocess.run([GIT, "-C", str(main), "reset", "-q", "--hard", start], check=True)
        probe.unlink(missing_ok=True)


STEER_CONFTEST = """
import sys
import types

steer = types.ModuleType("steer052")  # a module with no file: never a judged one
exec("class Steer:\\n    pass\\n", steer.__dict__)
sys.modules["steer052"] = steer


def pytest_configure(config):
    config.pluginmanager.register(steer.Steer(), "steer052")
"""


def test_a_plugin_registered_while_collecting_is_foreign_on_any_cores(clone_worktree) -> None:
    """The build review's F2: a conftest that pytest loads only while collecting (below an
    argument, in a folder not named test*) is loaded by the workers alone under -n; each worker
    hands what steers it to the controller. Serial and -n 2 are both red, and judged the same."""
    folder = clone_worktree / "tests" / "unit" / "zz052"
    try:
        (folder / "inner").mkdir(parents=True)
        (folder / "inner" / "conftest.py").write_text(STEER_CONFTEST)
        (folder / "inner" / "test_zz052.py").write_text("def test_unit():\n    pass\n")
        records = []
        for tag, cores in (("serial", []), ("n2", ["-n", "2"])):
            latest = clone_worktree / "build" / f"steer-{tag}.json"
            r = judge(clone_worktree, "tests/unit/zz052", ONE_CHECK, *cores,
                      "--progress-latest", str(latest))  # fmt: skip
            assert r.returncode == 1, (tag, r.stdout[-2000:] + r.stderr[-2000:])
            assert "steered from outside the judge: plugin steer052" in r.stdout, tag
            records.append(json.loads(latest.read_text()))
        assert all(any("steer052" in f for f in rec["meta"]["foreign"]) for rec in records)
        assert sameness.differences(*records) == []
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def test_the_plugin_self_tests_pass_in_a_worktree(clone_worktree) -> None:
    r = judge(clone_worktree, "tests/unit/test_plugin.py", "tests/unit/test_checks_wiring.py")
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]


# ---------------------------------------------------------------------------------------------
# A worktree inside the repository is not judge input, and is named (Decision 5)


NOTE = (
    "note: a worktree inside the repository: .claude/worktrees/x "
    "(constitution §4.14 puts them outside)"
)


def test_a_worktree_inside_leaves_the_hash_and_is_named(repo) -> None:
    before = paths.judge_hash(paths.judge_files())
    git(repo, "worktree", "add", "-q", "-b", "spec/999-x", str(repo / ".claude/worktrees/x"))
    assert paths.judge_hash(paths.judge_files()) == before, sorted(paths.judge_files())
    assert paths.worktrees_inside() == [".claude/worktrees/x"]
    meta = plugin.run_meta()
    assert meta["notes"] == [NOTE]
    run = {"meta": meta, "checks": {}, "suite": {}}
    assert NOTE in scoreboard.render(run, None, {}, [])


def test_a_nested_repository_under_tests_stays_in_the_hash(repo) -> None:
    nested = repo / "tests" / "vendored"
    git(repo, "init", "-q", str(nested))
    write(nested, "check_more.py", "\n")
    assert "tests/vendored/check_more.py" in paths.judge_files()
