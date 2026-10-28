"""rules: the mechanically checkable parts of the constitution."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tomllib
import types
from pathlib import Path

import pytest

from harness import history, needs, news, paths, scan

pytestmark = pytest.mark.goal("rules")

CODE_DIRS = ("recipes", "scripts", "src", "tests", "fixtures", "docs")
SPECS = paths.CONTEXT / "specifications"
RESEARCH = paths.CONTEXT / "research"
LIMITATIONS = paths.REPO / "docs" / "reference" / "limitations.md"


def test_no_module_level_name_is_bound_twice() -> None:
    """A second binding silently replaces the first; in a check file it makes other checks run the
    wrong code (a rebase once lost two checks that way)."""
    files = scan.files_under(paths.REPO, "tests", "src", "scripts", "release")
    hits = scan.duplicate_name_hits(files, paths.REPO)
    assert not hits, scan.report(hits)


def test_the_wheel_carries_every_component_licence() -> None:
    """Some linked components' licences ask for a notice in the distribution's documentation
    (FreeType's for one), so the wheel's .dist-info/licenses/LICENSE is the project's licence
    followed by every licence the artifact set carries: the release workflow rewrites LICENSE
    with release/licences.py before each wheel build and checks one wheel it built."""
    errors = scan.licence_step_errors(RELEASE_WORKFLOW.read_text(encoding="utf-8"))
    assert not errors, scan.report(errors)


def test_carried_patches_follow_the_rules() -> None:
    """Every carried patch has its pull request draft, its CHANGELOG
    line and a safe shape, and the README counts them."""
    from harness import pins

    # a release tag's archive (`-tag.tar.gz`) unpacks to its tag's folder, the name less `-tag`
    tops = {
        re.sub(r"(-tag)?\.tar\.\w+$", "", name)
        for name in paths.read_pin_list()
        if any(p.fullmatch(name) for p in pins.SOURCE_PATTERNS.values())
    }
    errors = scan.patch_errors(paths.REPO, tops)
    # The pull request drafts are this project's text, so no embedder's name either.
    names = scan.read_names(paths.EMBEDDERS)
    errors += scan.embedder_hits(paths.REPO, ["context/upstream/patches"], names)
    assert not errors, scan.report(errors)


def test_no_embedder_name_in_code() -> None:
    """The code and the public pages (the README and the site) name no embedder."""
    hits = scan.embedder_hits(
        paths.REPO, (*CODE_DIRS, "README.md"), scan.read_names(paths.EMBEDDERS)
    )
    assert not hits, scan.report(hits)


def test_no_artifact_or_large_file_is_tracked() -> None:
    needs.need("git")
    bad = []
    for f in paths.tracked_files("."):
        p = paths.REPO / f
        if f.endswith((".wasm", ".cwasm", ".zip")) or ".tar." in f:
            bad.append(f"{f}: an artifact or archive")
        elif p.is_file() and p.stat().st_size > 1 << 20:
            bad.append(f"{f}: {p.stat().st_size} bytes")
    assert not bad, scan.report(bad)


def test_every_prior_art_clone_has_its_licence_recorded() -> None:
    needs.need("prior-art clones")
    errors = scan.prior_art_errors(paths.PRIOR_ART)
    assert not errors, scan.report(errors)


def test_no_test_reads_a_clock() -> None:
    tests = paths.REPO / "tests"
    files = scan.files_under(tests, "checks", "unit", "jobs") + sorted(tests.glob("test_*.py"))
    hits = scan.clock_hits(files, paths.REPO)
    assert not hits, scan.report(hits)


def _ruff(*args: str) -> subprocess.CompletedProcess:
    ruff = Path(sys.executable).parent / "ruff"
    return subprocess.run(
        [str(ruff), *args, "src", "tests", "recipes/guest"],
        cwd=paths.REPO,
        capture_output=True,
        text=True,
        check=False,
    )


def test_ruff_check_is_clean() -> None:
    r = _ruff("check", "--quiet")
    assert r.returncode == 0, (r.stdout + r.stderr).strip().splitlines()[:3]


def test_ruff_format_is_clean() -> None:
    r = _ruff("format", "--check", "--quiet")
    assert r.returncode == 0, (r.stdout + r.stderr).strip().splitlines()[:3]


# The runner's package is type-checked whole under mypy's --strict (pinned exactly in the dev
# group; the platform pinned to linux in pyproject.toml, so three systems give one verdict): every
# function annotated, every generic given its parameters, no `Any` leaking from a declared return.
# A module still carrying errors is listed here with why, in words; an entry whose module is
# clean is a finding, so the list can only shrink, and an error anywhere else is one too.
UNTYPED: dict[str, str] = {}

MYPY_ERROR = re.compile(r"^src[\\/]wasi_python[\\/]([^:]+):\d+: error: .*\[([a-z-]+)\]\s*$", re.M)


def test_src_type_checks_under_mypy_strict() -> None:
    """`mypy` as pyproject.toml configures it (--strict, python 3.11, the linux platform, the files
    `src/wasi_python`): an exit of 2 (a crash or a configuration error) fails; an error in a
    module UNTYPED does not name fails; a module UNTYPED names with no error left fails."""
    mypy = Path(sys.executable).parent / "mypy"
    r = subprocess.run(
        [str(mypy), "--no-error-summary"],
        cwd=paths.REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode != 2, (r.stdout + r.stderr).strip().splitlines()[:5]
    errors = [(module, code) for module, code in MYPY_ERROR.findall(r.stdout)]
    findings = [
        line
        for line in r.stdout.splitlines()
        if (m := MYPY_ERROR.match(line)) is not None and m.group(1) not in UNTYPED
    ]
    for module in UNTYPED:
        if not any(found == module for found, _ in errors):
            findings.append(f"UNTYPED names {module}, which has no error left: delete its entry")
    assert not findings, scan.report(findings)


def test_build_scripts_call_python_only_through_uv_or_a_path() -> None:
    scripts = scan.every_file(paths.REPO / "scripts")
    hits = scan.bare_python_hits(scripts, paths.REPO)
    assert not hits, scan.report(hits)


# No module under src/ over 1,500 lines. A module over it that is not yet split has an entry
# equal to its count, which can only shrink (a stale entry is a finding too), and an entry is
# deleted the day its file is at or under the ceiling.
LINE_CEILING = 1500
ALLOWED: dict[str, int] = {}


def test_no_module_under_src_is_over_the_line_ceiling() -> None:
    """A module a person can hold in their head: every `.py` under src/ is at most 1,500
    physical lines (code, comments, docstrings and blanks alike, as `wc -l` counts a file that
    ends in a newline), but a file ALLOWED holds, at exactly today's count."""
    files = [p for p in scan.files_under(paths.REPO, "src") if p.suffix == ".py"]
    counts = {p: len(p.read_text(encoding="utf-8").splitlines()) for p in files}
    findings = []
    for p, count in sorted(counts.items()):
        allowed = ALLOWED.get(p.name)
        if allowed is not None and count != allowed:
            findings.append(f"{scan.rel(p, paths.REPO)}: {count:,} lines, ALLOWED says {allowed:,}")
        elif allowed is None and count > LINE_CEILING:
            findings.append(f"{scan.rel(p, paths.REPO)}: {count:,} lines, over {LINE_CEILING:,}")
    for name in ALLOWED:
        if sum(1 for p in files if p.name == name) != 1:
            findings.append(f"ALLOWED names {name}, which is not one file under src/")
    assert not findings, scan.report(findings)


# The process's state has one owner, `src/wasi_python/_process.py`: a lock made anywhere else
# at module level is inherited across a fork, held by a thread the child does not have, and a
# cache or registry anywhere else is one more list the fork reset and the exit release must
# remember. The owner's own module is the one place such bindings live.
PROCESS_OWNER = "_process.py"


def _runner_modules_but_the_owner() -> list[Path]:
    package = paths.REPO / "src" / "wasi_python"
    return [p for p in sorted(package.glob("*.py")) if p.name != PROCESS_OWNER]


def test_no_lock_is_made_at_module_level_outside_the_process() -> None:
    """No `Lock()`, `RLock()` or `Condition()` is bound at module or class level in any module of
    the package but the owner's: every lock is an attribute of the one process object, which
    re-makes each of them for a fork by looking at itself."""
    hits = scan.module_lock_hits(_runner_modules_but_the_owner(), paths.REPO)
    assert not hits, scan.report(hits)


def test_no_mutable_is_bound_at_module_level_outside_the_process() -> None:
    """No dict, list or set, and no deque, WeakSet, queue, counter or thread-local, is bound at
    module or class level in any module of the package but the owner's, apart from `__all__`, an
    upper-case table that is only read, and a ctypes `_fields_` declaration."""
    hits = scan.module_mutable_hits(_runner_modules_but_the_owner(), paths.REPO)
    assert not hits, scan.report(hits)


def test_only_the_engine_seam_touches_wasmtimes_private_api() -> None:
    """One module, `src/wasi_python/_wasmtime_ffi.py`, and its unit file
    reach wasmtime-py's private API (its underscore modules, the store context, the raw function
    handle, the from-pointer constructors and the pointer method); every other `.py` under `src/`
    and `tests/`, comments and docstrings included, drives the engine through the seam."""
    exempt = (scan.ENGINE_SEAM, scan.ENGINE_SEAM_UNIT)
    hits = scan.private_engine_hits(paths.REPO, ["src", "tests"], exempt)
    assert not hits, scan.report(hits)


def test_the_private_api_debt_is_documented() -> None:
    """Every entry of the seam's `NEEDED` and
    `OPTIONAL` tuples is a row of the debt sheet's table, every row is an entry, and the seam's
    docstring names every entry; read statically, so the check needs no wasmtime-py."""
    sheet = paths.CONTEXT / "upstream" / "34-wasmtime-py-public-api-for-the-runner" / "facts.md"
    errors = scan.private_api_debt_errors(paths.REPO / scan.ENGINE_SEAM, sheet)
    assert not errors, scan.report(errors)


def test_version_states_the_platform_semantics(guest) -> None:
    """The guest's -V states the platform's facts, and the limitations page says the same, so
    a reader of the page and a reader of the binary are told one thing."""
    r = guest("plain", ["-V"], record=False)
    assert r.exit_code == 0, r.describe()
    line = r.text.strip()
    facts = ("32-bit", "no threads", "ctypes", "times slower than native")
    missing = [f for f in facts if f not in line]
    assert not missing, scan.report(missing, f"-V says {line!r}; it lacks")
    sentence = line.split(" ", 2)[-1]  # after "Python X.Y.Z"
    page = " ".join(LIMITATIONS.read_text(encoding="utf-8").split())
    where = scan.rel(LIMITATIONS, paths.REPO)
    assert sentence in page, f"{where} does not carry the version sentence {sentence!r}"


def test_landed_specifications_cite_an_existing_review() -> None:
    reviews = paths.CONTEXT / "reviews"
    errors = [e for s in sorted(SPECS.glob("*.md")) for e in scan.landed_review_errors(s, reviews)]
    assert not errors, scan.report(errors)


def test_a_release_has_its_structural_review() -> None:
    """AGENTS.md, "Structure is reviewed": a released version (`X.Y.Z`, no `aN`, `bN` or `rcN`)
    has its structural review of `src/` on file among the reviews, scoring the rubric's eight
    rows. A prerelease needs none from the judge: its string is what the tree carries all
    cycle."""
    version = _release_version_module()
    current = version.read_version(version.INIT.read_text())
    errors = scan.structural_review_errors(current, paths.CONTEXT / "reviews")
    assert not errors, scan.report(errors)


def test_built_structural_specifications_cite_their_pre_build_review() -> None:
    """A specification whose Kind line carries **structural** was reviewed before it was built:
    once built or landed, it cites its own `-spec-` review, and the file exists."""
    reviews = paths.CONTEXT / "reviews"
    errors = [
        e
        for s in sorted(SPECS.glob("*.md"))
        for e in scan.structural_spec_review_errors(s, reviews)
    ]
    assert not errors, scan.report(errors)


def test_generated_pages_are_current() -> None:
    """The documentation's two generated pages, the Python API and the command line, each hold
    exactly one block, equal to what the live package renders, so neither page can fall behind
    the code it describes."""
    from harness import api, cli_doc

    _, api_block = api.render()
    pages = [
        (api.PAGE, api.readme_block, api_block, api.WRITE),
        (cli_doc.PAGE, cli_doc.page_block, cli_doc.render(cli_doc.live_parser()), cli_doc.WRITE),
    ]
    errors = []
    for page, read_block, live, write in pages:
        where = scan.rel(page, paths.REPO)
        count, block = read_block(page.read_text(encoding="utf-8") if page.is_file() else "")
        if count != 1 or block is None:
            errors.append(f"{where}: {count} generated blocks, not one; run {write}")
        elif block.strip("\n") != live.strip("\n"):
            errors.append(f"{where}: differs from the live render; run {write}")
    assert not errors, scan.report(errors)


# The writing conventions are lint: the quick job's lint step runs them by their folder, they gate
# ci-status, and they are no goal check, so no area counts them and the ratchet never holds them.
# The rules that hold more than writing stay goal checks: the embedder names (a hard constraint),
# the release's structural review, the landed specifications' reviews and the structural
# specifications' reviews before their build.
LINT_FILE = paths.REPO / "tests" / "lint" / "test_writing_conventions.py"
LINT_RULES = (
    "test_specifications_have_their_header_and_sections",
    "test_specifications_have_no_open_question",
    "test_markdown_paragraphs_are_one_line_each",
    "test_executed_memos_label_their_claims",
    "test_readme_carries_the_codecov_badge",
    "test_code_outside_src_names_no_context_document",
    "test_no_string_names_a_context_document",
    "test_src_names_no_context_document",
)
KEPT_RULES = (
    "test_no_embedder_name_in_code",
    "test_a_release_has_its_structural_review",
    "test_landed_specifications_cite_an_existing_review",
    "test_built_structural_specifications_cite_their_pre_build_review",
)


def _functions(path: Path) -> set[str]:
    import ast

    if not path.is_file():
        return set()
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}


def test_the_writing_conventions_are_lint_not_goal_checks() -> None:
    """The eight writing rules live in tests/lint, which marks no goal check and which the fast
    tier does not collect; the four that hold more than writing stay here; and the quick job runs
    the folder as its lint step, with no `if:` or `continue-on-error` on it, on the rules step or
    on the job."""
    here, there = _functions(Path(__file__)), _functions(LINT_FILE)
    errors = [f"{n} is a goal check here, not lint" for n in LINT_RULES if n in here]
    errors += [
        f"{n} is not in {scan.rel(LINT_FILE, paths.REPO)}" for n in LINT_RULES if n not in there
    ]
    errors += [f"{n} is no longer a goal check" for n in KEPT_RULES if n not in here]
    lint = paths.REPO / "tests" / "lint"
    if any("mark.goal" in f.read_text(encoding="utf-8") for f in sorted(lint.glob("*.py"))):
        errors.append("a file under tests/lint marks a goal check")
    ini = tomllib.loads((paths.REPO / "pyproject.toml").read_text())["tool"]["pytest"]
    if "lint" not in ini["ini_options"].get("norecursedirs", []):
        errors.append("the fast tier collects tests/lint: norecursedirs does not name lint")
    errors += scan.lint_step_errors(RELEASE_WORKFLOW.read_text())
    assert not errors, scan.report(errors)


def test_known_gaps_are_well_formed() -> None:
    from harness import plugin

    gaps, errors = plugin.load_gaps(paths.KNOWN_GAPS)
    checks_dir = paths.REPO / "tests" / "checks"
    for gap in gaps.values():
        file, _, name = gap.check.partition("::")
        func = name.split("[", 1)[0]
        source = paths.REPO / file
        if not (source.is_file() and source.parent == checks_dir):
            errors.append(f"{gap.check}: not a file under tests/checks/")
        elif f"def {func}(" not in source.read_text():
            errors.append(f"{gap.check}: no such check")
        closer = gap.closes_with.split(" ", 1)[0]
        if not (paths.REPO / closer).is_file() or not (
            closer == "README.md" or closer.startswith(("context/", "docs/"))
        ):
            errors.append(
                f"{gap.check}: closer {gap.closes_with} is not a file under context/ or docs/"
            )
        if not gap.reason.strip():
            errors.append(f"{gap.check}: empty reason")
        if "finding(s), digest " not in gap.match:
            errors.append(f"{gap.check}: match does not name an exact finding set (a digest)")
    raw = tomllib.loads(paths.KNOWN_GAPS.read_text()) if paths.KNOWN_GAPS.is_file() else {}
    assert set(raw) <= {"gap"}, f"unknown tables in known_gaps.toml: {sorted(set(raw) - {'gap'})}"
    assert not errors, scan.report(errors)


def _committed_volumes() -> dict[str, bytes] | None:
    """Every history volume in HEAD's tree, with its committed bytes."""
    if not needs.VOCABULARY["git"].met():
        return None
    rel = paths.PROGRESS.relative_to(paths.REPO).as_posix()
    listed = paths.git("ls-tree", "--name-only", "HEAD", "--", f"{rel}/")
    if listed is None:
        return None
    out = {}
    for path in listed.split("\n"):
        name = path.rsplit("/", 1)[-1]
        if path and history.first_line_of(name) is not None:
            r = subprocess.run(
                ["git", "-C", str(paths.REPO), "show", f"HEAD:{path}"],
                capture_output=True,
                check=False,
            )
            if r.returncode == 0:
                out[name] = r.stdout
    return out


def test_progress_history_is_intact() -> None:
    """Every volume of the history: the chain, the names, the budget, the replay with
    every digest, volume 1's seal, and every committed volume only extended."""
    accepted = paths.ACCEPTED.read_text() if paths.ACCEPTED.is_file() else None
    found = history.found_in(paths.PROGRESS)
    errors = history.errors(found, accepted, _committed_volumes(), history.SEALED)
    assert not errors, scan.report(errors)


def test_the_newest_acceptance_sits_on_the_commit_it_judged() -> None:
    """The newest acceptance commit's first
    parent is the commit its history line judged, it carries only the two progress files, and it
    was made on a clean tree. Committed history only, so the lane is never red between accepting
    and committing."""
    needs.need("git", "git history")
    errors = scan.acceptance_errors(paths.REPO)
    assert not errors, scan.report(errors)


def test_the_clean_acceptance_key_is_in_the_judge() -> None:
    """Rule 1 requires `dirty: false` of an acceptance whose judge holds this file.
    Kept here, among the protected checks, so that deleting the file cannot quietly end the
    requirement."""
    assert (paths.REPO / scan.FIRST_CLEAN_JUDGE).is_file(), scan.FIRST_CLEAN_JUDGE


# The judge files whose change needs `--accept-judge`, written again here: a change to the list is
# a change to this tuple too, so it is a judge change a reader sees.
VERDICT_BEARING = (
    "tests/known_gaps.toml",
    "tests/upstream/*.toml",
    "tests/upstream/expected/**",
    "tests/upstream/python/**",
    "tests/release_shards.toml",
    "tests/public_api.txt",
    "context/release-tier-claims.toml",
)


def test_the_verdict_bearing_files_are_judge_files() -> None:
    """The list `--accept-judge` reads names the known gaps, the upstream suites' allowances, their
    expected failures, CPython's plan, the shard plan, the public API's list and the release tier's
    claims, and nothing else; each entry matches a file the judge's hash holds, so a change to one
    is seen as a judge change and none of them is a name that matches nothing."""
    errors = []
    if paths.VERDICT_BEARING != VERDICT_BEARING:
        errors.append(f"paths.VERDICT_BEARING is {paths.VERDICT_BEARING}, not {VERDICT_BEARING}")
    files = paths.judge_files()
    for pattern in paths.VERDICT_BEARING:
        if not any(paths.is_verdict_bearing(f, (pattern,)) for f in files):
            errors.append(f"{pattern} matches no file the judge's hash holds")
    assert not errors, scan.report(errors)


def test_main_is_linear() -> None:
    """Main moves only by fast-forward."""
    needs.need("git", "git history")
    errors = scan.merge_commit_errors(paths.REPO)
    assert not errors, scan.report(errors)


def _release_version_module() -> types.ModuleType:
    """`release/version.py`, loaded by path: the one reader of the version string."""
    import importlib.util

    path = paths.REPO / "release" / "version.py"
    spec = importlib.util.spec_from_file_location("release_version", path)
    version = importlib.util.module_from_spec(spec)
    sys.modules["release_version"] = version  # dataclasses look their module up here
    spec.loader.exec_module(version)
    return version


def test_the_version_is_released_by_the_book() -> None:
    """One version in __init__.py, read dynamically, with its changelog section."""
    version = _release_version_module()
    errors = version.check_errors(
        version.INIT.read_text(), version.PYPROJECT.read_text(), version.CHANGELOG.read_text()
    )
    assert not errors, scan.report(errors)


def test_the_news_files_have_their_shape() -> None:
    """Every news file in the changes folder reads: its changelog lines under the CHANGELOG's
    headings, its package rows, and one claim block in the claims' shape; the release assembles
    them and the acceptance from CI takes its reasons from them."""
    folder = paths.REPO / news.CHANGES
    errors = []
    for f in sorted(folder.glob("*.md")) if folder.is_dir() else []:
        if f.name == "README.md":
            continue
        try:
            news.load(f)
        except news.NewsError as e:
            errors.append(str(e))
    assert not errors, scan.report(errors)


def test_releases_attest_and_verify_their_assets() -> None:
    workflow = paths.REPO / ".github" / "workflows" / "release.yml"
    errors = scan.release_attestation_errors(workflow.read_text())
    assert not errors, scan.report(errors)


RELEASE_WORKFLOW = paths.REPO / ".github" / "workflows" / "release.yml"
# The local action every reader of the build's files runs.
ASSETS_ACTION = paths.REPO / scan.ASSETS_ACTION_FILE


def test_the_release_signs_and_publishes_what_build_made() -> None:
    """Every job that checks, signs or publishes reads the build's files through the one local
    action, which downloads them by an id it has guarded and checks them against the SHA-256 of
    SHA256SUMS the build job handed on, and acts on nothing else; the publish jobs name their
    environments, setup-uv runs with no cache, and each job holds only the permissions it uses."""
    errors = scan.release_binding_errors(RELEASE_WORKFLOW.read_text(), ASSETS_ACTION.read_text())
    assert not errors, scan.report(errors)


def test_every_action_is_pinned_by_commit() -> None:
    """Every `uses:` in every workflow and every local action is local or pinned by a full
    commit."""
    github = paths.REPO / ".github"
    errors = [
        f"{w.relative_to(github).as_posix()}: {e}"
        for w in sorted([*github.glob("workflows/*.y*ml"), *github.glob("actions/*/action.y*ml")])
        for e in scan.action_pin_errors(w.read_text())
    ]
    assert not errors, scan.report(errors)


def test_every_job_checks_out_the_head_commit() -> None:
    """A pull request's jobs check out its head, never the merge ref: the merge ref is a merge
    commit nobody will merge, which the history rules refuse, and the up-to-date rule makes the
    head the tree the squash puts on dev."""
    errors = scan.checkout_ref_errors(RELEASE_WORKFLOW.read_text())
    assert not errors, scan.report(errors)


CI_STATUS_CASES = {
    "every job succeeded or was skipped": (
        {"plan": "success", "quick": "success", "build": "skipped"},
        "[]",
        0,
    ),
    "a failed job": ({"plan": "success", "quick": "failure"}, "[]", 1),
    "a cancelled job": ({"plan": "success", "gather": "cancelled"}, "[]", 1),
    "a refusal": ({"plan": "success"}, '["a pull request may not write accepted state"]', 1),
    "no plan": ({"plan": "failure"}, "", 1),
}


@pytest.mark.parametrize("case", CI_STATUS_CASES)
def test_ci_status_fails_on_a_job_that_did_not_pass_or_a_refusal(case, tmp_path) -> None:
    """ci-status's own step, run in bash with this environment's python3: green only when every
    job it needs succeeded or was skipped and the plan refused nothing."""
    import json

    script = scan.workflow_step_script(
        RELEASE_WORKFLOW.read_text(),
        "ci-status",
        "Every job succeeded or was skipped, and the plan refused nothing",
    )
    results, refusals, want = CI_STATUS_CASES[case]
    (tmp_path / "status.sh").write_text(script)
    r = subprocess.run(
        ["bash", "-e", str(tmp_path / "status.sh")],
        env={
            "PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin",
            "NEEDS": json.dumps({job: {"result": v, "outputs": {}} for job, v in results.items()}),
            "REFUSALS": refusals,
        },
        capture_output=True,
        text=True,
    )
    assert (r.returncode != 0) == bool(want), (r.returncode, r.stdout + r.stderr)


def test_one_required_check_holds_every_job() -> None:
    """ci-status is the one required check: it always runs, needs every other job, and passes
    only when each succeeded or was skipped by the plan and the plan refused nothing; every other
    job gates on the decision job's outputs with if:, never a paths: filter, so a skipped job
    reports success and the check is always reported; only a pull request's older run is
    cancelled."""
    errors = scan.ci_status_errors(RELEASE_WORKFLOW.read_text())
    assert not errors, scan.report(errors)


def test_the_accept_jobs_accept_a_green_merge_and_only_the_push_holds_the_key() -> None:
    """accept-record runs after a merge into dev only when every job it needs is green, with
    contents: read and no secret; accept-push alone is in the accept environment and holds the
    deploy key, runs no code of the repository, commits the two progress files alone and pushes
    only onto the commit judged; no other job or workflow names the key."""
    github = paths.REPO / ".github" / "workflows"
    others = {
        w.name: w.read_text() for w in sorted(github.glob("*.y*ml")) if w.name != "release.yml"
    }
    errors = scan.accept_job_errors(RELEASE_WORKFLOW.read_text(), others)
    assert not errors, scan.report(errors)


ACCEPT_RELEASE_WORKFLOW = paths.REPO / ".github" / "workflows" / "accept-release.yml"


def test_the_release_acceptance_is_pushed_from_devs_own_context() -> None:
    """The release pull request's run accepts its record in accept-record and pushes nothing;
    accept-release.yml, run by its completion on dev's own context, alone beside accept-push in
    the accept environment, runs no code of the repository and pushes that acceptance onto dev
    only while dev's tip is the head the run judged, and is red when it cannot."""
    errors = scan.accept_release_errors(ACCEPT_RELEASE_WORKFLOW.read_text())
    ci_plan = _ci_plan_module()
    event = ci_plan.Event("pull_request", "refs/pull/9/merge", "main")
    d = ci_plan.decide(["src/x.py"], event)
    outputs = ci_plan.outputs(d, ci_plan.select(d, ci_plan.load_shards()), [])
    context = {"event_name": "pull_request", "ref": "refs/pull/9/merge", "base_ref": "main"}
    ran = scan.jobs_that_run(RELEASE_WORKFLOW.read_text(), outputs, context)
    if "accept-record" not in ran:
        errors.append("the release pull request's run does not accept its record")
    errors += [f"the release pull request's run runs {j}" for j in ("accept-push",) if j in ran]
    assert not errors, scan.report(errors)


def test_the_release_pull_request_checks_what_its_tag_will() -> None:
    """On a pull request into main the build job's version step holds now what the tag's run and
    the owner's push will: the version's section dated, its tag not yet made, and main's tip in
    the head's history, so the push to main is a fast-forward."""
    errors = scan.release_version_errors(RELEASE_WORKFLOW.read_text())
    assert not errors, scan.report(errors)


def test_the_weekly_run_opens_an_issue_when_red_and_never_accepts() -> None:
    """The weekly schedule and the dispatch input that selects its shape; one job with issues:
    write that opens or updates an issue when a job of the run failed or was cancelled; the
    accept jobs run on a merge into dev alone."""
    errors = scan.weekly_errors(RELEASE_WORKFLOW.read_text())
    assert not errors, scan.report(errors)


ACCEPT_PUSH_STEP = "Commit the acceptance alone, and push it while dev is the commit judged"
ACCEPT_RELEASE_STEP = (
    "Commit the release's acceptance alone, and push it while dev is the head judged"
)
ACCEPT_PUSH_CASES = {
    "dev is the commit judged": ("judged", (), 0, "pushed"),
    "dev moved on": ("moved", (), 0, "nothing is pushed"),
    "a third file changed": ("judged", ("src/x.py",), 1, "accepted.json and one history volume"),
    # The release's acceptance: no later merge carries a release-tier acceptance, so a dev that
    # moved on is red there.
    "the release: dev is the head judged": ("judged", (), 0, "pushed"),
    "the release: dev moved on": ("moved", (), 1, "nothing is pushed"),
    "the release: a third file changed": (
        "judged",
        ("src/x.py",),
        1,
        "accepted.json and one history volume",
    ),
}


def _git_in(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    assert r.returncode == 0, (args, r.stderr)
    return r.stdout.strip()


@pytest.mark.parametrize("case", ACCEPT_PUSH_CASES)
def test_the_accept_push_step_pushes_only_the_acceptance_onto_the_judged_tip(
    case, tmp_path, monkeypatch
) -> None:
    """accept-push's own step, run in bash against a clone of a bare remote: it commits
    accepted.json and the new history volume alone, with the message accept-record wrote, and
    pushes it onto dev only while dev is the commit judged; when dev moved on it pushes nothing
    and succeeds; anything else changed refuses."""
    needs.need("git")
    tip, extra, want, words = ACCEPT_PUSH_CASES[case]
    config = tmp_path / "gitconfig"
    config.write_text("[user]\n\tname = t\n\temail = t@t\n[commit]\n\tgpgsign = false\n")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    remote, work, clone = tmp_path / "remote.git", tmp_path / "work", tmp_path / "clone"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "dev", str(remote)], check=True)
    subprocess.run(["git", "init", "-q", "-b", "dev", str(work)], check=True)
    progress = work / "context" / "progress"
    progress.mkdir(parents=True)
    (progress / "accepted.json").write_text("{}\n")
    (progress / "history.jsonl").write_text('{"n": 1}\n')
    (work / "src").mkdir()
    (work / "src" / "x.py").write_text("x = 1\n")
    _git_in(work, "add", "-A")
    _git_in(work, "commit", "-q", "-m", "the merge")
    judged = _git_in(work, "rev-parse", "HEAD")
    _git_in(work, "remote", "add", "origin", str(remote))
    _git_in(work, "push", "-q", "origin", "HEAD:refs/heads/dev")
    if tip == "moved":
        _git_in(work, "commit", "-q", "--allow-empty", "-m", "a newer merge")
        _git_in(work, "push", "-q", "origin", "HEAD:refs/heads/dev")
    before = _git_in(work, "ls-remote", "origin", "refs/heads/dev").split()[0]
    subprocess.run(["git", "clone", "-q", str(remote), str(clone)], check=True)
    _git_in(clone, "checkout", "-q", "--detach", judged)
    acceptance = tmp_path / "acceptance"
    (acceptance / "context" / "progress").mkdir(parents=True)
    (acceptance / "build" / "progress").mkdir(parents=True)
    (acceptance / "context" / "progress" / "accepted.json").write_text('{"commit": 1}\n')
    (acceptance / "context" / "progress" / "history.jsonl").write_text('{"n": 1}\n')
    (acceptance / "context" / "progress" / "history-00002.jsonl").write_text('{"n": 2}\n')
    message = "Accepted: the merge (#1)\n\nno row needed a reason\n"
    (acceptance / "build" / "progress" / "acceptance-message.txt").write_text(message)
    for rel in extra:
        (clone / rel).write_text("changed\n")
    if case.startswith("the release"):
        script = scan.workflow_step_script(
            ACCEPT_RELEASE_WORKFLOW.read_text(), "accept-release", ACCEPT_RELEASE_STEP
        )
    else:
        script = scan.workflow_step_script(
            RELEASE_WORKFLOW.read_text(), "accept-push", ACCEPT_PUSH_STEP
        )
    (tmp_path / "push.sh").write_text(script)
    r = subprocess.run(
        ["bash", "-e", str(tmp_path / "push.sh")],
        cwd=clone,
        env={**os.environ, "GITHUB_SHA": judged, "JUDGED": judged, "ACCEPTANCE": str(acceptance)},
        capture_output=True,
        text=True,
    )
    assert r.returncode == want, r.stdout + r.stderr
    assert words in r.stdout + r.stderr
    after = _git_in(work, "ls-remote", "origin", "refs/heads/dev").split()[0]
    if not case.endswith("dev is the commit judged") and not case.endswith(
        "dev is the head judged"
    ):
        assert after == before
        return
    assert _git_in(clone, "rev-parse", f"{after}^") == judged
    changed = _git_in(clone, "show", "--name-only", "--format=", after).split()
    assert changed == ["context/progress/accepted.json", "context/progress/history-00002.jsonl"]
    assert _git_in(clone, "log", "-1", "--format=%B", after) + "\n" == message


def _fake_assets(folder: Path) -> str:
    """A release-assets folder as the build job writes it: a wheel, the set's .tar.xz, and their
    SHA256SUMS (`release/version.py`, `write_assets`). Returns the SHA-256 of SHA256SUMS."""
    import hashlib

    assets = folder / "release-assets"
    assets.mkdir()
    (assets / "wasi_python-0.1.0a6-py3-none-any.whl").write_bytes(b"wheel bytes")
    (assets / "wasi-python-0.1.0a6-wasm32-wasip1.tar.xz").write_bytes(b"tar bytes")
    sums = "".join(
        f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n"
        for p in sorted(assets.iterdir())
    )
    (assets / "SHA256SUMS").write_text(sums)
    return hashlib.sha256(sums.encode()).hexdigest()


def _resum(assets: Path) -> None:
    import hashlib

    names = sorted(p.name for p in assets.iterdir() if p.name != "SHA256SUMS")
    (assets / "SHA256SUMS").write_text(
        "".join(f"{hashlib.sha256((assets / n).read_bytes()).hexdigest()}  {n}\n" for n in names)
    )


CHECK_CASES = {
    "the build's own files": (lambda a, h: h, 0),
    "SUMS_SHA256 empty": (lambda a, h: "", 1),
    "SUMS_SHA256 another hash": (lambda a, h: "0" * 64, 1),
    "the wheel's bytes changed": (
        lambda a, h: (a / "wasi_python-0.1.0a6-py3-none-any.whl").write_bytes(b"evil") and h,
        1,
    ),
    "the wheel swapped, SHA256SUMS rewritten to match": (
        lambda a, h: (
            (a / "wasi_python-0.1.0a6-py3-none-any.whl").write_bytes(b"evil") and (_resum(a) or h)
        ),
        1,
    ),
    "the .tar.xz removed": (
        lambda a, h: (a / "wasi-python-0.1.0a6-wasm32-wasip1.tar.xz").unlink() or h,
        1,
    ),
    "an extra file": (lambda a, h: (a / "evil.whl").write_bytes(b"x") and h, 1),
    "a hidden file": (lambda a, h: (a / ".hidden").write_bytes(b"x") and h, 1),
    "a sub-folder": (lambda a, h: (a / "more").mkdir() or h, 1),
}


@pytest.mark.parametrize("case", CHECK_CASES)
def test_the_release_check_refuses_other_bytes(case, tmp_path) -> None:
    """The local action's own check step, run in bash: the build's own files pass, and every
    other set of bytes fails closed. Its absence fails every case."""
    script = scan.action_step_script(ASSETS_ACTION.read_text(), scan.CHECK_STEP)
    change, want = CHECK_CASES[case]
    good = _fake_assets(tmp_path)
    sums = change(tmp_path / "release-assets", good)
    (tmp_path / "check.sh").write_text(script)
    r = subprocess.run(
        ["bash", "-e", str(tmp_path / "check.sh")],
        cwd=tmp_path,
        env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "SUMS_SHA256": sums},
        capture_output=True,
        text=True,
    )
    assert (r.returncode != 0) == bool(want), (r.returncode, (r.stdout + r.stderr)[-300:])


GUARD_CASES = {
    "empty": ("", 1),
    "12x": ("12x", 1),
    "1,2": ("1,2", 1),
    "a decimal": ("123456789", 0),
}


@pytest.mark.parametrize("case", GUARD_CASES)
def test_the_id_guard_refuses_a_missing_id(case, tmp_path) -> None:
    """The local action's own id guard, run in bash: an empty artifact-ids would download every
    artifact of the run, so only a non-empty decimal passes."""
    script = scan.action_step_script(ASSETS_ACTION.read_text(), scan.GUARD_STEP)
    value, want = GUARD_CASES[case]
    (tmp_path / "guard.sh").write_text(script)
    r = subprocess.run(
        ["bash", "-e", str(tmp_path / "guard.sh")],
        env={"PATH": "/usr/bin:/bin", "ASSETS_ID": value},
        capture_output=True,
        text=True,
    )
    assert (r.returncode != 0) == bool(want), (r.returncode, r.stdout + r.stderr)


def test_every_build_host_has_its_whole_table() -> None:
    """Each build host names its five inputs in scripts/line.conf; each is pinned and fetched in
    that host's own branch of the download script; and the four files know the same hosts."""
    import importlib.util

    scripts = paths.REPO / "scripts"
    spec = importlib.util.spec_from_file_location("wasi_python_line_hosts", scripts / "line.py")
    line = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(line)
    errors = scan.host_table_errors(
        (scripts / "line.conf").read_text(),
        scan.SH_HOST_KEY.findall((scripts / "line.sh").read_text()),
        getattr(line, "HOSTS", {}).values(),
        (scripts / "00_download.sh").read_text(),
        paths.read_pin_list(),
    )
    assert not errors, scan.report(errors)


# The runner carries two guards for wasmtime advisories while the published floor of the
# `wasmtime` requirement admits a vulnerable wasmtime. Each advisory's vulnerable versions, as
# its record states them (`vulnerable_version_range` in the advisory's own JSON record): a list
# of spans, one per release line the advisory knows. A version outside every span is one the
# advisory does not call vulnerable. That is the advisory's own statement, span by span, not an
# "at or past" reading (wasmtime's releases are not one ordered line: v50.0.0-rc.1 came before
# v49.0.3), and the two sandbox checks of the hostile-guest file, which run the attacks against
# the installed engine, are the standing proof that the engine holds.
WASMTIME_GUARDS = {
    # fd_readdir's dirent padding
    "GHSA-96f6-r43r-8c24": "< 36.0.17, >= 37.0.0, < 48.0.4, >= 49.0.0, < 49.0.2",
    # path_rename's trailing slash
    "GHSA-m9f7-9w4p-gv38": "<= 36.0.17, >= 37.0.0, <= 48.0.5, >= 49.0.0, <= 49.0.2",
}
ADVISORIES = RESEARCH / "2026-10-18-wasmtime-49-advisories" / "advisories"

Version = tuple[int, int, int]


def _version(text: str) -> Version:
    parts = [int(p) for p in text.strip().split(".")]
    assert 1 <= len(parts) <= 3, text
    return (*parts, 0, 0)[:3]  # type: ignore[return-value]


def _after(version: Version) -> Version:
    """The next version after `version`: versions are integer triples, so the next is one patch
    on. A bound is written as half-open from here: `> v` and `<= v` both become `after(v)`."""
    return (version[0], version[1], version[2] + 1)


def _clauses(text: str) -> list[tuple[str, Version]] | None:
    """A comma list of `op version` clauses, or None for an operator outside >=, >, <, <=, ==."""
    out = []
    for clause in text.split(","):
        clause = clause.strip()
        op = next((o for o in (">=", "<=", "==", ">", "<") if clause.startswith(o)), None)
        if op is None:
            return None
        out.append((op, _version(clause[len(op) :])))
    return out


def _spans(vulnerable: str) -> list[tuple[Version, Version | None]]:
    """An advisory's vulnerable range as half-open spans [low, high): a lower bound followed by an
    upper bound is one span, a lone upper bound opens at 0.0.0, a lone lower bound has no top
    (None)."""
    clauses = _clauses(vulnerable)
    assert clauses is not None, vulnerable
    spans: list[tuple[Version, Version | None]] = []
    low: Version | None = None
    for op, version in clauses:
        if op in (">=", ">"):
            assert low is None, vulnerable  # two lower bounds in a row bound nothing
            low = version if op == ">=" else _after(version)
        elif op in ("<", "<="):
            high = version if op == "<" else _after(version)
            spans.append((low or (0, 0, 0), high))
            low = None
        else:  # ==
            assert low is None, vulnerable
            spans.append((version, _after(version)))
    if low is not None:
        spans.append((low, None))
    return spans


def _guard_may_go(requirement: str, vulnerable: str) -> bool:
    """A guard may go when no version the requirement admits lies in any of the advisory's
    vulnerable spans. wasmtime releases only `M.0.P` (READ, wasmtime's list of releases). An open
    top, a bound with a minor version, or an operator other than >=, <, <= and == keeps the
    guard: a requirement so written admits versions no reading of the spans should speak for."""
    clauses = _clauses(requirement)
    if clauses is None or any(op == ">" for op, _ in clauses):
        return False
    low: Version | None = None
    high: Version | None = None  # exclusive
    for op, version in clauses:
        if version[1] != 0:
            return False
        if op in (">=", "=="):
            low = version if low is None else max(low, version)
        if op in ("<", "<=", "=="):
            top = version if op == "<" else _after(version)
            high = top if high is None else min(high, top)
    if low is None or high is None:
        return False
    for span_low, span_high in _spans(vulnerable):
        if max(low, span_low) < (high if span_high is None else min(high, span_high)):
            return False  # some admitted version is vulnerable
    return True


def _wasmtime_requirement() -> str:
    project = tomllib.loads((paths.REPO / "pyproject.toml").read_text())["project"]
    found = [d for d in project["dependencies"] if re.match(r"wasmtime\s*[<>=!~]", d)]
    assert len(found) == 1, project["dependencies"]
    return found[0][len("wasmtime") :].strip()


def test_the_rename_and_readdir_guard_match_the_floor() -> None:
    """Each guard is in the runner while the published floor (the
    `wasmtime` requirement in pyproject.toml, not uv.lock) admits a wasmtime its advisory calls
    vulnerable, and is gone, with its checks, once it does not."""
    rename, padding = WASMTIME_GUARDS["GHSA-m9f7-9w4p-gv38"], WASMTIME_GUARDS["GHSA-96f6-r43r-8c24"]
    table = {
        ">=49,<50": False,  # 49.0.0 lies in both 49 spans
        ">=50,<51": True,  # the 50 line lies outside every span
        ">=49.0.3,<51": True,  # 49.0.3 and the 50 line lie outside every span
        ">=49.0.2,<50": None,  # 49.0.2 is outside the padding's spans, inside the rename's
        ">=49.0.3": False,  # an open top
    }
    for requirement, both in table.items():
        got = (_guard_may_go(requirement, padding), _guard_may_go(requirement, rename))
        want = (True, False) if both is None else (both, both)
        assert got == want, (requirement, got)
    import json

    for advisory, vulnerable in WASMTIME_GUARDS.items():
        record = json.loads((ADVISORIES / f"{advisory}.json").read_text())
        listed = {v["vulnerable_version_range"] for v in record["vulnerabilities"]}
        assert listed == {vulnerable}, (advisory, listed)
    requirement = _wasmtime_requirement()
    package = paths.REPO / "src" / "wasi_python"
    source = "\n".join((package / name).read_text() for name in FILESYSTEM_IMPORTS)
    this = Path(__file__).resolve()
    tests = [p for p in scan.files_under(paths.REPO, "tests") if p.suffix == ".py" and p != this]
    errors = []
    for advisory, vulnerable in WASMTIME_GUARDS.items():
        where = f"{advisory}: wasmtime{requirement} admits"
        if not _guard_may_go(requirement, vulnerable):
            if advisory not in source:
                errors.append(f"{where} a vulnerable wasmtime, and the filesystem names no guard")
        else:
            left = [str(p.relative_to(paths.REPO)) for p in tests if advisory in p.read_text()]
            if advisory in source or left:
                errors.append(f"{where} only patched ones; remove the guard and {left}")
    assert not errors, scan.report(errors)


def test_every_host_compiles_natively_with_the_fallback_kept() -> None:
    """Every build host compiles with its own pinned clang (its COMPILER_SDK_DIR is its own SDK),
    or, with the fallback's one-line switch thrown, with another host's SDK under the pinned qemu
    while carrying the five emulation names; exactly one key carries those names, each pinned and
    fetched in its branch beside another host's SDK, so the fallback is runnable; step 10 still
    lays out and probes the emulated compiler, and the launcher still clears the emulator's and
    the loader's environment and keeps each name's driver mode."""
    scripts = paths.REPO / "scripts"
    errors = scan.compiler_table_errors(
        (scripts / "line.conf").read_text(),
        (scripts / "00_download.sh").read_text(),
        paths.read_pin_list(),
        scan.code_text(scripts / "steps" / "10_tools.sh") or "",
        scan.code_text(scripts / "clang-emulated"),
    )
    assert not errors, scan.report(errors)


PREIMPORT_DEFINE = re.compile(r'^#define PREIMPORT "(.*)"\s*$', re.M)
PREIMPORT_OVERRIDE = re.compile(r"-DPREIMPORT|PREIMPORT=")
PREIMPORT_COPY = re.compile(r'^\s*PREIMPORT\s*=\s*"', re.M)


def test_the_pre_import_list_is_the_stdlib_bootstrap() -> None:
    """Decision 34: the snapshot pre-imports the stdlib's bootstrap and no
    package. The recipe's `#define` is the list's one source; no build step overrides it, and the
    MANIFEST writer keeps no copy of its own."""
    recipe = (paths.REPO / "recipes" / "reactor_main.c").read_text()
    found = PREIMPORT_DEFINE.findall(recipe)
    want = "import " + ", ".join(paths.PREIMPORT)
    assert found == [want], f"recipes/reactor_main.c defines PREIMPORT as {found}, not [{want!r}]"
    hits = []
    for rel in paths.tracked_files("scripts", "recipes", ".github"):
        p = paths.REPO / rel
        try:
            text = p.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        hits += [f"{rel}: overrides PREIMPORT" for _ in PREIMPORT_OVERRIDE.finditer(text)]
    writer = (paths.REPO / "scripts" / "assemble_artifacts.py").read_text()
    if PREIMPORT_COPY.search(writer):
        hits.append("scripts/assemble_artifacts.py: carries its own PREIMPORT list")
    assert not hits, scan.report(hits)


def test_release_shards_cover_the_judge() -> None:
    """The release's shard plan holds every test file and every upstream group: one rest shard
    takes what no other names, every group is in one Linux shard, our own shards run on all three
    systems, and no system runs a group twice."""
    from harness import shards, upstream

    configs = upstream.load_all()
    groups = [g for c in configs.values() for g in c.groups]
    release = {g.name for c in configs.values() for g in c.groups.values() if g.tier == "release"}
    files = shards.test_files(paths.tracked_files("tests"))
    errors = shards.plan_errors(shards.load(), files, groups, release)
    assert not errors, scan.report(errors)


def test_every_package_names_its_own_suite() -> None:
    """Every component of the artifact (paths.PACKAGES, the source components, the linked
    runtimes) runs its own suite in the release, or says what reaches it, that it only builds
    another, or which specification will run it."""
    from harness import shards, upstream

    raw = tomllib.loads(shards.PACKAGES_FILE.read_text())
    suites = {p: len(c.groups) for p, c in upstream.load_all().items()}
    errors = shards.package_errors(raw, shards.components(), suites)
    assert not errors, scan.report(errors)


def test_release_judges_in_shards() -> None:
    """The release runs the shards the plan selects in their system's judge job, each leg
    uploading its record under its own name, names no shard by hand, and publishes nothing until
    the gather, which holds no assets, has read every record."""
    from harness import shards

    errors = scan.release_shard_errors(RELEASE_WORKFLOW.read_text(), shards.load())
    assert not errors, scan.report(errors)


def test_the_runners_coverage_rides_a_judge_leg() -> None:
    """No job runs the fast tier a third time for the badge: the Linux legs the plan names, every
    own shard of the plan on Linux, run their shards under coverage.py and send the reports to
    Codecov, which merges them into the README's badge, and Codecov's token reaches those upload
    steps alone. own-rest alone holds the rules and the harness's self-tests, which barely run the
    runner, so the badge would stop measuring it."""
    from harness import shards

    errors = scan.coverage_errors(RELEASE_WORKFLOW.read_text())
    plan = shards.load()
    linux_own = [n for n in shards.on(plan, "linux") if not plan[n].groups]
    named = list(_ci_plan_module().COVERAGE_SHARDS)
    if named != linux_own:
        errors.append(
            f"the plan measures coverage on {named}, not every Linux own shard {linux_own}"
        )
    assert not errors, scan.report(errors)


def _ci_plan_module() -> types.ModuleType:
    """`release/ci_plan.py`, loaded by path: the decision job's script."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "release_ci_plan_rules", paths.REPO / "release" / "ci_plan.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # dataclasses look their module up here
    spec.loader.exec_module(mod)
    return mod


# Every event of the release shape: each judges the whole plan, both tiers, and rebuilds.
RELEASE_SHAPES = {
    "a pushed tag": ("push", "refs/tags/v0.1.1", ""),
    "a pull request into main": ("pull_request", "refs/pull/9/merge", "main"),
    "a dispatch on main": ("workflow_dispatch", "refs/heads/main", ""),
    "the weekly run": ("schedule", "refs/heads/dev", ""),
}


@pytest.mark.parametrize("shape", RELEASE_SHAPES)
def test_the_judge_matrices_are_the_shard_plan_on_every_release(shape) -> None:
    """The workflow writes no shard (test_release_judges_in_shards); each judge job's legs are
    the decision job's output for its system, generated from tests/release_shards.toml. On every
    run of the release shape that output is the plan's own list for the system, in its order,
    the release tier's included, with the build shard, both rebuilds and same-bytes."""
    from harness import shards

    ci_plan = _ci_plan_module()
    name, ref, base = RELEASE_SHAPES[shape]
    d = ci_plan.decide(None if name != "pull_request" else [], ci_plan.Event(name, ref, base))
    sel = ci_plan.select(d, ci_plan.load_shards())
    plan = shards.load()
    errors = [
        f"{system}: the plan's {shards.on(plan, system)}, the decision job's {sel[system]}"
        for system in (*shards.OWN_SYSTEMS, "release")
        if sel[system] != shards.on(plan, system)
    ]
    if not (d.rebuild and sel["build"] and d.tier == "release"):
        errors.append(f"{shape}: rebuild {d.rebuild}, build {sel['build']}, tier {d.tier}")
    assert not errors, scan.report(errors)


# The wasi-libc emulation layer reads alone: five modules, which ask their host nine questions
# through a protocol `mounts.py` declares (`_CallContext`) and import nothing of the runner but
# the engine seam, which the table's forward uses for the fuel-neutral call. Among themselves
# they form a chain with `mounts.py`, the vocabulary, at the bottom: the bytes that cross the
# WASI boundary, then the descriptor and path calls, then the table that dispatches to them.
# The two handler modules name the table for a type checker only. The runner imports from the
# group, never the other way, so the dependency graph stays acyclic and the unit checks drive
# the table with a fake context instead of patching another module's names.
ENGINE_SEAM_MODULE = scan.ENGINE_SEAM.rsplit("/", 1)[-1].removesuffix(".py")
FILESYSTEM_IMPORTS = {  # module: (at runtime, under TYPE_CHECKING only)
    "mounts.py": ((), ()),
    "_fs_memory.py": (("mounts",), ()),
    "_fs_descriptors.py": (("mounts", "_fs_memory"), ("_fs_table",)),
    "_fs_paths.py": (("mounts", "_fs_memory"), ("_fs_table",)),
    "_fs_table.py": (
        ("mounts", "_fs_memory", "_fs_descriptors", "_fs_paths", ENGINE_SEAM_MODULE),
        (),
    ),
}


def test_the_filesystem_imports_only_itself_and_the_engine_seam() -> None:
    """Each module of the filesystem imports, at module level, inside a function or under
    `TYPE_CHECKING`, only what its row of FILESYSTEM_IMPORTS names: at runtime the first column,
    for a type checker the first or the second; and every module the table names is one file
    under the package. What the group needs of the runner it asks of the `_CallContext` it is
    given."""
    package = paths.REPO / "src" / "wasi_python"
    hits = []
    for name, (runtime, typing_only) in FILESYSTEM_IMPORTS.items():
        path = package / name
        if not path.is_file():
            hits.append(f"FILESYSTEM_IMPORTS names {name}, which is not one file under the package")
            continue
        for line, module, typing in scan.sibling_imports(path):
            if module in runtime or (typing and module in typing_only):
                continue
            hits.append(f"{name}:{line}: imports {module}{' for a type checker' if typing else ''}")
    named = {m for runtime, typing in FILESYSTEM_IMPORTS.values() for m in runtime + typing}
    for module in sorted(named - {ENGINE_SEAM_MODULE}):
        if f"{module}.py" not in FILESYSTEM_IMPORTS:
            hits.append(f"FILESYSTEM_IMPORTS lets the group import {module}, which is not in it")
    assert not hits, scan.report(hits)


# The platform is chosen once. `src/wasi_python/_platform.py` holds the one interface, the POSIX,
# Linux and macOS hosts and the choice, bound to `PLATFORM` at import by `_select`, the one
# function in the package that reads `sys.platform` or `os.name`; `_platform_windows.py` holds
# Windows, and `_platform_common.py` what both families run, below both. Every caller reads
# `_platform.PLATFORM` through its module at the call, so a check that binds another platform
# for its duration is seen by every caller. A reader who asks what Windows does differently
# opens `_platform_windows.py`, and `_platform.py`'s docstring lists every difference. Only
# `_platform.py` imports the Windows module or names the Windows class (by import, as an
# attribute such as `_platform._Windows`, or bare): a caller that made a Windows platform itself
# would choose a platform outside `_select`.
PLATFORM_MODULE = "_platform.py"
PLATFORM_CHOOSER = "_select"
PLATFORM_WINDOWS = "_platform_windows"
WINDOWS_CLASS = "_Windows"
WINDOWS_HOMES = (PLATFORM_MODULE, f"{PLATFORM_WINDOWS}.py")  # where the class may be named
PLATFORM_READ = re.compile(r"\bos\.name\b|\bsys\.platform\b")


def _imports_windows(node: object) -> bool:
    """Whether an import statement names the Windows platform module, in any of its forms."""
    import ast

    if isinstance(node, ast.Import):
        return any(a.name.split(".")[-1] == PLATFORM_WINDOWS for a in node.names)
    if isinstance(node, ast.ImportFrom):
        if node.module and node.module.split(".")[-1] == PLATFORM_WINDOWS:
            return True
        return any(a.name == PLATFORM_WINDOWS for a in node.names)
    return False


def _names_windows_class(node: object) -> bool:
    """Whether a node names the Windows class: imported, read as an attribute, or bare."""
    import ast

    if isinstance(node, ast.ImportFrom):
        return any(a.name == WINDOWS_CLASS for a in node.names)
    if isinstance(node, ast.Attribute):
        return node.attr == WINDOWS_CLASS
    return isinstance(node, ast.Name) and node.id == WINDOWS_CLASS


def _platform_hits(package: Path) -> list[str]:
    import ast

    hits = []
    for path in sorted(package.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        chooser: tuple[int, int] | None = None
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.endswith(PLATFORM_MODULE.removesuffix(".py"))
            ):
                for alias in node.names:
                    if alias.name == "PLATFORM":
                        hits.append(f"{path.name}:{node.lineno}: binds PLATFORM by import")
            if path.name != PLATFORM_MODULE and _imports_windows(node):
                hits.append(
                    f"{path.name}:{node.lineno}: imports the Windows platform outside "
                    f"{PLATFORM_MODULE}"
                )
            if path.name not in WINDOWS_HOMES and _names_windows_class(node):
                hits.append(
                    f"{path.name}:{node.lineno}: names the Windows class outside {PLATFORM_MODULE}"
                )
            if (
                path.name == PLATFORM_MODULE
                and isinstance(node, ast.FunctionDef)
                and node.name == PLATFORM_CHOOSER
            ):
                chooser = (node.lineno, node.end_lineno or node.lineno)
        for n, line in enumerate(text.splitlines(), 1):
            if PLATFORM_READ.search(line) and not (
                chooser is not None and chooser[0] <= n <= chooser[1]
            ):
                hits.append(f"{path.name}:{n}: reads the platform outside {PLATFORM_CHOOSER}")
    return hits


# The platform's door. What both platform families share lives in `_platform_common.py` and
# what Windows does in `_platform_windows.py`; every other module reaches either through
# `_platform`, which has a delegate for what a caller needs of the shared half, so the platform
# module stays the one place a reader looks. Only the platform modules import the halves:
# `_platform_common` by `_platform.py` and `_platform_windows.py`, `_platform_windows` by
# `_platform.py`.
PLATFORM_HALVES = {
    "_platform_common": ("_platform.py", "_platform_windows.py"),
    PLATFORM_WINDOWS: (PLATFORM_MODULE,),
}


def test_only_the_platform_modules_import_its_halves() -> None:
    """No module under `src/wasi_python/` imports `_platform_common` or `_platform_windows`,
    at module level, inside a function or under `TYPE_CHECKING`, but the platform modules
    PLATFORM_HALVES names; every other caller goes through `_platform`."""
    package = paths.REPO / "src" / "wasi_python"
    hits = []
    for path in sorted(package.glob("*.py")):
        for line, module, _ in scan.sibling_imports(path):
            allowed = PLATFORM_HALVES.get(module)
            if allowed is not None and path.name not in allowed:
                hits.append(f"{path.name}:{line}: imports {module} past the platform module")
    assert not hits, scan.report(hits)


def test_the_platform_is_chosen_once() -> None:
    """No `os.name` or `sys.platform` anywhere under `src/wasi_python/` but inside
    `_platform._select`, no import that binds `PLATFORM` to a local name, and no import of the
    Windows platform module, nor any naming of the Windows class, but `_platform.py`'s."""
    hits = _platform_hits(paths.REPO / "src" / "wasi_python")
    assert not hits, scan.report(hits)


# Seams are injected, not patched: a check or a unit test sets a seam through a field of the
# process object, never by replacing a private name of a runner module by `setattr` or by
# assignment, in its code or in a child program it runs. These are the private names the judge
# still patches by name, each with what closes it. An entry leaves when its seam is fixed; none
# is ever added; an entry no test patches any more is red.
SEAM_ALLOWED = (
    # _home: the guest thread's home. The flag its watch reads, the stack it asks for, the join
    # it runs and the box it keeps become fields or constructor parameters of the home.
    "_ctrl_c_watched",
    "_stack",
    "_join_guest",
    "_Box",
    # _call: the typed call. Its clock and its stop error come from the process object's clock
    # and the call's own state; the drive is the lifecycle table's.
    "_epoch_now",
    "_stop_error",
    "_drive",
    # _sessions: the session's turn. Both are rows of its lifecycle table.
    "_drive_turn",
    "_abandon_turn",
    # _engines and _artifacts: the compile miss, the artifact check's cache and the two artifact
    # folders become observers or fields of the process object, or parameters of artifacts().
    "_module_miss",
    "_found_and_checked",
    "_ARTIFACT_DIR",
    "_CHECKOUT_ARTIFACT_DIR",
    # _private_dirs: the sweep's budget and its drop hook become parameters of the remover.
    "_REMOVE_BUDGET",
    "_drop",
    # _places and runner: the walk, the preopen check and the defaults, patched by one check
    # each; constructor parameters of the places and the call.
    "_walk_grants",
    "_check_preopens",
    "_current_defaults",
)


def test_the_judge_patches_the_runner_only_through_the_process_object() -> None:
    """No `<fixture>.setattr(<runner module>, "_name", …)` and no `<runner module>._name = …`
    in any `.py` under `tests/`, in code or in a program string, but for SEAM_ALLOWED, which
    only shrinks; the tool protocol's three modules, `cli` and the package itself are outside
    the rule, as is a class attribute or an attribute of a call's result
    (`process().observers`)."""
    files = [p for p in scan.files_under(paths.REPO, "tests") if p.suffix == ".py"]
    hits = scan.seam_hits(files, paths.REPO, SEAM_ALLOWED)
    assert not hits, scan.report(hits)


# A function a person can read whole: none over 80 lines, def to last line. These are the
# functions over it on the tree the check was built on, measured by scan.long_function_hits
# (the length beside each key is the record, not the test: the check reads the ceiling). An
# entry leaves when its function is at or under 80 lines; none is ever added; a stale entry
# is red.
LONG_FUNCTIONS = {
    # The two entry points and the session's opening each validate every argument before any
    # work; a shared argument object would carry the checks out of them.
    "runner.py:run": 151,
    "runner.py:run_async": 176,
    "runner.py:Session.__init__": 173,
    "runner.py:Session.run_async": 82,
    "_sessions.py:_open_session": 150,
    # The engine instance's assembly: the linker, the store and the imports, one builder each.
    "_call.py:_instance": 159,
    # The process object's fields, one line each; a dataclass would make them declarations.
    "_process.py:_Process.__init__": 82,
}


def test_no_function_is_over_eighty_lines() -> None:
    """No function or method in src/wasi_python, nested ones included, is over
    scan.FUNCTION_CEILING lines but for LONG_FUNCTIONS, which only shrinks."""
    files = [p for p in scan.files_under(paths.REPO, "src") if p.suffix == ".py"]
    hits = scan.long_function_hits(files, paths.REPO, LONG_FUNCTIONS)
    assert not hits, scan.report(hits)


def test_api_lists_every_module_of_the_package() -> None:
    """Every `.py` under src/wasi_python is in the API harness's lists, as a module that defines
    public names or as an internal one, and every name those lists hold is one file there: a
    module the lists do not know is one whose private names could reach a public docstring or
    the README unseen."""
    from harness import api

    package = paths.REPO / "src" / "wasi_python"
    files = {p.name for p in package.glob("*.py")}
    listed = set(api.DEFINING) | set(api.INTERNAL_FILES)
    hits = [f"src/wasi_python/{name}: in no list of api.py" for name in sorted(files - listed)]
    hits += [f"api.py lists {name}, not one file under the package" for name in listed - files]
    assert not hits, scan.report(hits)


# The table owns its state. The descriptor and path calls, and the poll the runner answers
# itself, receive the table as `files` and change it only through its methods, so each invariant
# of the state (`staged` is the sum of the rows' `held`, `opened` counts the table and the owed
# rows, `held` holds only wasmtime's numbers, a stop's fuel is recorded once) is kept in one
# file. No allowance: there is no list to grow.
TABLE_HANDLERS = ("_fs_descriptors.py", "_fs_paths.py", "_call.py")


def test_the_handlers_change_the_table_only_through_its_methods() -> None:
    """No handler module writes a field of the table by hand, in any of the five forms: a plain,
    annotated or augmented assignment, a subscript store or a `del` whose target is rooted at
    `files`, or a mutator call `files.<field>.<add, discard, pop, …>(…)`; a read is not a write."""
    package = paths.REPO / "src" / "wasi_python"
    handlers = [package / name for name in TABLE_HANDLERS]
    hits = [f"{p.name}: not found" for p in handlers if not p.is_file()]
    hits += scan.table_write_hits([p for p in handlers if p.is_file()], paths.REPO)
    assert not hits, scan.report(hits)


def test_the_oracles_lock_is_its_projects() -> None:
    """The oracle's lock is generated: a text merge can leave it unparsable to uv, and the oracle
    then only reads as unavailable. Read from the files alone, so it holds on every system."""
    from harness import jobs

    errors = scan.lock_errors(
        (jobs.ORACLE_PROJECT / "uv.lock").read_text(),
        (jobs.ORACLE_PROJECT / "pyproject.toml").read_text(),
    )
    assert not errors, scan.report(errors, "tests/jobs/oracle/uv.lock")


# ---------------------------------------------------------------------------------------------
# A faster release run: a proven set reused on branch dispatches

SET_CACHE_WORKFLOW = paths.REPO / ".github" / "workflows" / "set-cache.yml"


def set_key_module():
    """release/set_key.py, imported by path (it is a script, not a package)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "wasi_python_set_key", paths.REPO / "release" / "set_key.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def set_key_inputs() -> dict:
    """What scan.set_key_errors reads, from this checkout."""
    sk = set_key_module()
    tracked = paths.tracked_files(*sk.TREES)
    tests = paths.REPO / sk.GATE_ROOT
    return {
        "closure": sk.closure(paths.REPO),
        "tracked": tracked,
        "texts": {
            rel: (paths.REPO / rel).read_text(errors="replace")
            for rel in tracked
            if (paths.REPO / rel).is_file()
        },
        "release_text": RELEASE_WORKFLOW.read_text(),
        "key_env": sk.ENV,
        "gate_root": sk.GATE_ROOT,
        "gates": sk.GATES,
        "tests_names": sorted(p.name for p in tests.iterdir() if p.suffix == ".py" or p.is_dir()),
        "gate_imports": scan.local_import_files(paths.REPO, sk.GATE_ROOT, sk.GATES),
        "root_names": sorted({rel.split("/")[0] for rel in paths.tracked_files()}),
        "pyproject_text": (paths.REPO / "pyproject.toml").read_text(),
        "members": scan.workspace_members(paths.REPO, (paths.REPO / "pyproject.toml").read_text()),
    }


def test_the_set_key_names_every_build_input() -> None:
    """The key of a reused set holds every input of the build: every tracked file under scripts/
    and recipes/, every repository path they name, the gate the build runs from tests/ with its
    imports, and the build's environment: the first of the key's three layers of proof."""
    needs.need("git", "git history")
    errors = scan.set_key_errors(**set_key_inputs())
    assert not errors, scan.report(errors)


def test_the_release_reuses_a_set_only_on_a_branch() -> None:
    """Only a dispatch on a branch other than main reuses a set; the build job's conditional
    steps, build-shard, the cache's readers and writers, and set-cache.yml follow the reuse
    rules: where a set may be reused, how it is checked, who writes the cache and who reads it."""
    errors = scan.release_reuse_errors(
        RELEASE_WORKFLOW.read_text(),
        SET_CACHE_WORKFLOW.read_text() if SET_CACHE_WORKFLOW.is_file() else "",
        set_key_module().ENV,
    )
    assert not errors, scan.report(errors)


DECIDE_CASES = {
    "a dispatch on a branch, cached": (
        {"GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REF_TYPE": "branch"},
        "refs/heads/spec/x",
        "false",
        "true",
        "true",
    ),
    "a pushed tag": (
        {"GITHUB_EVENT_NAME": "push", "GITHUB_REF_TYPE": "tag"},
        "refs/tags/v1",
        "",
        "true",
        "false",
    ),
    "a dispatch on a tag ref": (
        {"GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REF_TYPE": "tag"},
        "refs/tags/v1",
        "false",
        "true",
        "false",
    ),
    "a dispatch on main": (
        {"GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REF_TYPE": "branch"},
        "refs/heads/main",
        "false",
        "true",
        "false",
    ),
    "from-source": (
        {"GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REF_TYPE": "branch"},
        "refs/heads/spec/x",
        "true",
        "true",
        "false",
    ),
    "a miss": (
        {"GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REF_TYPE": "branch"},
        "refs/heads/spec/x",
        "false",
        "false",
        "false",
    ),
    "an empty hit": (
        {"GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REF_TYPE": "branch"},
        "refs/heads/spec/x",
        "false",
        "",
        "false",
    ),
    # A pull request into dev and a push to dev are judged from the cached set; a pull request
    # into main, the release, builds its own.
    "a pull request into dev, cached": (
        {
            "GITHUB_EVENT_NAME": "pull_request",
            "GITHUB_REF_TYPE": "branch",
            "GITHUB_BASE_REF": "dev",
        },
        "refs/pull/7/merge",
        "",
        "true",
        "true",
    ),
    "a pull request into main, cached": (
        {
            "GITHUB_EVENT_NAME": "pull_request",
            "GITHUB_REF_TYPE": "branch",
            "GITHUB_BASE_REF": "main",
        },
        "refs/pull/8/merge",
        "",
        "true",
        "false",
    ),
    "a push to dev, cached": (
        {"GITHUB_EVENT_NAME": "push", "GITHUB_REF_TYPE": "branch"},
        "refs/heads/dev",
        "",
        "true",
        "true",
    ),
    "a push to main, cached": (
        {"GITHUB_EVENT_NAME": "push", "GITHUB_REF_TYPE": "branch"},
        "refs/heads/main",
        "",
        "true",
        "false",
    ),
    "the weekly run on dev, cached": (
        {"GITHUB_EVENT_NAME": "schedule", "GITHUB_REF_TYPE": "branch"},
        "refs/heads/dev",
        "",
        "true",
        "true",
    ),
    "a pull request into dev, a miss": (
        {
            "GITHUB_EVENT_NAME": "pull_request",
            "GITHUB_REF_TYPE": "branch",
            "GITHUB_BASE_REF": "dev",
        },
        "refs/pull/7/merge",
        "",
        "false",
        "false",
    ),
}


@pytest.mark.parametrize("case", DECIDE_CASES)
def test_the_reuse_decision_refuses_tags_and_main(case, tmp_path) -> None:
    """The inputs job's own decision step, run in bash: reuse only where a cached set is trusted
    (a pull request into dev, a push to dev, the weekly run on dev, a dispatch from a branch other
    than main), not from-source, with the key cached; any other value builds from source."""
    script = scan.workflow_step_script(RELEASE_WORKFLOW.read_text(), "inputs", scan.DECIDE_STEP)
    event, ref, from_source, hit, want = DECIDE_CASES[case]
    out = tmp_path / "out"
    (tmp_path / "decide.sh").write_text(script)
    r = subprocess.run(
        ["bash", "-e", str(tmp_path / "decide.sh")],
        env={
            "PATH": "/usr/bin:/bin",
            **event,
            "GITHUB_REF": ref,
            "FROM_SOURCE": from_source,
            "HIT": hit,
            "GITHUB_OUTPUT": str(out),
        },
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert out.read_text() == f"reuse={want}\n", (out.read_text(), r.stdout)


# The build reads its pins by exact name, and the release checks every inner file.

COMMON_SH = paths.REPO / "scripts" / "steps" / "common.sh"
PIN_FUNCTIONS = ("die", "pin_line", "pinned", "pin_of")


def _shell_functions(text: str, names: tuple[str, ...]) -> str:
    """The named functions' definitions, taken from a script's text as written, so a row can
    run them without sourcing the script whole (common.sh finds the repository from $0 and
    sources the line and the removal helper at load)."""
    out = []
    for name in names:
        m = re.search(rf"^{name}\(\) \{{\n.*?^\}}\n", text, re.M | re.S)
        if m:
            out.append(m[0])
    return "".join(out)


def _sha(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


# case -> (the files in downloads/, the SHA256SUMS lines as (file whose bytes are hashed, name),
# the call, the exit status wanted (0 or not), what the output must hold)
PIN_CASES = {
    "an exact pin": (
        {"foo.tar.gz": b"foo"},
        [("foo.tar.gz", "foo.tar.gz")],
        "pinned foo.tar.gz",
        0,
        "downloads/foo.tar.gz",
    ),
    "a dot is only a dot": (
        {"foo.tar.gz": b"unpinned", "fooXtar.gz": b"pinned"},
        [("fooXtar.gz", "fooXtar.gz")],
        "pinned foo.tar.gz",
        1,
        "foo.tar.gz is not pinned",
    ),
    "a name pinned twice": (
        {"foo.tar.gz": b"foo"},
        [("foo.tar.gz", "foo.tar.gz"), ("foo.tar.gz", "foo.tar.gz")],
        "pinned foo.tar.gz",
        1,
        "foo.tar.gz is pinned twice",
    ),
    "a numeric-looking name is text": (
        {"100": b"a", "1e2": b"b"},
        [("100", "100")],
        "pinned 1e2",
        1,
        "1e2 is not pinned",
    ),
    "a numeric-looking name matches itself": (
        {"100": b"a"},
        [("100", "100")],
        "pinned 100",
        0,
        "downloads/100",
    ),
    "bytes that changed": (
        {"foo.tar.gz": b"changed"},
        [("foo.tar.gz", "foo.tar.gz")],
        "pinned foo.tar.gz",
        1,
        "does not match its pin",
    ),
    "pin_of an exact pin": (
        {},
        [("foo.tar.gz", "foo.tar.gz")],
        "pin_of foo.tar.gz",
        0,
        _sha(b"foo"),
    ),
    "pin_of: a dot is only a dot": (
        {},
        [("fooXtar.gz", "fooXtar.gz")],
        "pin_of foo.tar.gz",
        1,
        "foo.tar.gz is not pinned",
    ),
    "pin_of a name pinned twice": (
        {},
        [("foo.tar.gz", "foo.tar.gz"), ("foo.tar.gz", "foo.tar.gz")],
        "pin_of foo.tar.gz",
        1,
        "foo.tar.gz is pinned twice",
    ),
}
PIN_BYTES = {"foo.tar.gz": b"foo", "fooXtar.gz": b"pinned", "100": b"a"}


@pytest.mark.parametrize("shell", ["sh", "bash"])
@pytest.mark.parametrize("case", PIN_CASES)
def test_a_pin_is_selected_by_its_exact_name_and_once(case, shell, tmp_path) -> None:
    """common.sh's own pinned() and pin_of(), taken from its text and run under sh and bash: a
    pin is found by its exact name, never by a pattern that lets `.` match another character,
    never by comparing numbers, and exactly once."""
    import shutil

    found = shutil.which(shell)
    assert found, f"no {shell} on PATH"
    text = COMMON_SH.read_text()
    files, lines, call, want, shows = PIN_CASES[case]
    needed = ("die", call.split()[0])
    missing = [n for n in needed if not re.search(rf"^{n}\(\) \{{$", text, re.M)]
    assert not missing, f"common.sh defines no {', '.join(missing)}()"
    d, b = tmp_path / "downloads", tmp_path / "build"
    d.mkdir()
    b.mkdir()
    for name, data in files.items():
        (d / name).write_bytes(data)
    (d / "SHA256SUMS").write_text("".join(f"{_sha(PIN_BYTES[f])}  {n}\n" for f, n in lines))
    script = f'set -eu\nD="{d}"\nB="{b}"\n' + _shell_functions(text, PIN_FUNCTIONS) + call + "\n"
    (tmp_path / "pin.sh").write_text(script)
    r = subprocess.run([found, str(tmp_path / "pin.sh")], capture_output=True, text=True)
    out = r.stdout + r.stderr
    assert (r.returncode != 0) == bool(want), (r.returncode, out[-300:])
    assert shows in out, out[-300:]


def test_no_pin_is_looked_up_by_a_pattern() -> None:
    """No script selects a line of SHA256SUMS with `grep "  $…"`, where a `.` in the name
    matches any character; pins are selected by their exact name field."""
    hits = scan.pin_lookup_hits(scan.files_under(paths.REPO, "scripts"), paths.REPO)
    assert not hits, scan.report(hits)


def test_meson_never_downloads_a_subproject() -> None:
    """Every meson configure under scripts/steps/ passes --wrap-mode=nodownload through
    MESON_WRAP (HarfBuzz its own stricter nofallback), so a wrap pkg-config does not satisfy
    fails the build instead of fetching; contourpy's configure is the one exemption, for the
    sdist that was checked."""
    steps = {p.name: p.read_text() for p in sorted((paths.REPO / "scripts" / "steps").glob("*.sh"))}
    errors = scan.meson_wrap_errors(steps)
    assert not errors, scan.report(errors)


def test_curl_keeps_https_at_tls_1_2() -> None:
    """Every curl command in scripts/ and the workflows stays on HTTPS, on every redirect too,
    at TLS 1.2 or later; the download script has one."""
    files = scan.files_under(paths.REPO, "scripts") + sorted(
        (paths.REPO / ".github" / "workflows").glob("*.y*ml")
    )
    errors = scan.curl_flag_errors(files, paths.REPO)
    assert not errors, scan.report(errors)
    assert scan.curl_lines((paths.REPO / "scripts" / "00_download.sh").read_text())


def test_every_download_the_licences_read_goes_through_its_pin() -> None:
    """scripts/assemble_artifacts.py reads no file under downloads/ but through pinned_bytes,
    which checks it against its pin first; the pin list itself is the one plain read."""
    writer = paths.REPO / "scripts" / "assemble_artifacts.py"
    hits = scan.downloads_read_hits(writer.read_text(), "scripts/assemble_artifacts.py")
    assert not hits, scan.report(hits)


def test_the_same_bytes_job_checks_every_inner_file() -> None:
    """The same-bytes job checks every file inside the set's tarball against its SHA256SUMS,
    refuses any other file and any symlink, and requires every published file to be listed."""
    errors = scan.same_bytes_inner_errors(RELEASE_WORKFLOW.read_text(), paths.ARTIFACT_FILES)
    assert not errors, scan.report(errors)


def test_the_build_job_verifies_the_set_again_before_it_packs() -> None:
    errors = scan.producer_reverify_errors(RELEASE_WORKFLOW.read_text())
    assert not errors, scan.report(errors)


def test_contourpys_exemption_holds_only_for_the_checked_sdist() -> None:
    """A bump of contourpy's unpacked folder fails the meson rule until the new sdist is checked
    for wrap files and the exemption is renewed."""
    steps = {p.name: p.read_text() for p in sorted((paths.REPO / "scripts" / "steps").glob("*.sh"))}
    steps["55_matplotlib.sh"] = steps["55_matplotlib.sh"].replace(
        "contourpy-1.4.0", "contourpy-1.5.0"
    )
    errors = scan.meson_wrap_errors(steps)
    assert any("exempt only for contourpy-1.4.0" in e and "unpacks 1.5.0" in e for e in errors), (
        errors
    )
