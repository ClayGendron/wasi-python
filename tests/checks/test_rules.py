"""rules: the mechanically checkable parts of the constitution (§4, §5, §7)."""

from __future__ import annotations

import re
import subprocess
import sys
import tomllib
import types
from pathlib import Path

import pytest

from harness import history, needs, paths, scan

pytestmark = pytest.mark.goal("rules")

CODE_DIRS = ("recipes", "scripts", "src", "tests", "fixtures")
SPECS = paths.CONTEXT / "specifications"
RESEARCH = paths.CONTEXT / "research"


def test_no_module_level_name_is_bound_twice() -> None:
    """A second binding silently replaces the first; in a check file it makes other checks run the
    wrong code (spec 019's rebase lost two checks that way)."""
    files = scan.files_under(paths.REPO, "tests", "src", "scripts", "release")
    hits = scan.duplicate_name_hits(files, paths.REPO)
    assert not hits, scan.report(hits)


def test_the_readme_carries_the_licences_credit_lines() -> None:
    """Constitution §4.12: FreeType's licence makes a credit line in the distribution's
    documentation a condition of binary redistribution; the README, the wheel's description,
    carries it while FreeType is pinned (spec 023's build review, F1)."""
    errors = scan.credit_errors(paths.README.read_text(), paths.read_pin_list())
    assert not errors, scan.report(errors)


def test_carried_patches_follow_the_rules() -> None:
    """Constitution §4.1 (spec 020): every carried patch has its pull request draft, its CHANGELOG
    line and a safe shape, and the README counts them."""
    from harness import pins

    tops = {
        re.sub(r"\.tar\.\w+$", "", name)
        for name in paths.read_pin_list()
        if any(p.fullmatch(name) for p in pins.SOURCE_PATTERNS.values())
    }
    errors = scan.patch_errors(paths.REPO, tops)
    # The pull request drafts are this project's text, so no embedder's name either.
    names = scan.read_names(paths.EMBEDDERS)
    errors += scan.embedder_hits(paths.REPO, ["context/upstream/patches"], names)
    assert not errors, scan.report(errors)


def test_no_embedder_name_in_code() -> None:
    hits = scan.embedder_hits(paths.REPO, CODE_DIRS, scan.read_names(paths.EMBEDDERS))
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


def test_specifications_have_their_header_and_sections() -> None:
    errors = [e for s in sorted(SPECS.glob("*.md")) for e in scan.spec_shape_errors(s)]
    assert not errors, scan.report(errors)


def test_specifications_have_no_open_question() -> None:
    docs = sorted(SPECS.glob("*.md")) + [paths.README, paths.REPO / "AGENTS.md"]
    hits = [h for d in docs for h in scan.open_question_hits(d)]
    assert not hits, scan.report(hits)


# No module under src/ over 1,500 lines. The two over it today are not yet split; their
# entries equal their counts and can only shrink (a stale entry is a finding too), and an entry
# is deleted the day its file is at or under the ceiling.
LINE_CEILING = 1500
ALLOWED = {"mounts.py": 2206, "tools.py": 2449}


def test_no_module_under_src_is_over_the_line_ceiling() -> None:
    """A module a person can hold in their head: every `.py` under src/ is at most 1,500
    physical lines (code, comments, docstrings and blanks alike, as `wc -l` counts a file that
    ends in a newline), but the two files ALLOWED holds at exactly today's count."""
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
    """Spec 103, Decision 3: one module, `src/wasi_python/_wasmtime_ffi.py`, and its unit file
    reach wasmtime-py's private API (its underscore modules, the store context, the raw function
    handle, the from-pointer constructors and the pointer method); every other `.py` under `src/`
    and `tests/`, comments and docstrings included, drives the engine through the seam."""
    exempt = (scan.ENGINE_SEAM, scan.ENGINE_SEAM_UNIT)
    hits = scan.private_engine_hits(paths.REPO, ["src", "tests"], exempt)
    assert not hits, scan.report(hits)


def test_the_private_api_debt_is_documented() -> None:
    """Spec 103, Design, "The debt is documented": every entry of the seam's `NEEDED` and
    `OPTIONAL` tuples is a row of the debt sheet's table, every row is an entry, and the seam's
    docstring names every entry; read statically, so the check needs no wasmtime-py."""
    sheet = paths.CONTEXT / "upstream" / "34-wasmtime-py-public-api-for-the-runner" / "facts.md"
    errors = scan.private_api_debt_errors(paths.REPO / scan.ENGINE_SEAM, sheet)
    assert not errors, scan.report(errors)


def test_version_states_the_platform_semantics(guest) -> None:
    """Constitution §4.11: the guest's -V states the platform's facts, and the README says the
    same (spec 003, Decision 8)."""
    r = guest("plain", ["-V"], record=False)
    assert r.exit_code == 0, r.describe()
    line = r.text.strip()
    facts = ("32-bit", "no threads", "ctypes", "times slower than native")
    missing = [f for f in facts if f not in line]
    assert not missing, scan.report(missing, f"-V says {line!r}; it lacks")
    sentence = line.split(" ", 2)[-1]  # after "Python X.Y.Z"
    readme = " ".join(paths.README.read_text().split())
    assert sentence in readme, f"README does not carry the version sentence {sentence!r}"


def test_landed_specifications_cite_an_existing_review() -> None:
    reviews = paths.CONTEXT / "reviews"
    errors = [e for s in sorted(SPECS.glob("*.md")) for e in scan.landed_review_errors(s, reviews)]
    assert not errors, scan.report(errors)


def test_a_release_has_its_structural_review() -> None:
    """AGENTS.md, "Structure is reviewed": a released version (`X.Y.Z`, no `aN`, `bN` or `rcN`)
    has its structural review of `src/` under `context/reviews/`, scoring the rubric's eight
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


def test_executed_memos_label_their_claims() -> None:
    errors = [e for m in sorted(RESEARCH.glob("*.md")) for e in scan.memo_label_errors(m)]
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
            closer == "README.md" or closer.startswith("context/")
        ):
            errors.append(f"{gap.check}: closer {gap.closes_with} is not a file under context/")
        if not gap.reason.strip():
            errors.append(f"{gap.check}: empty reason")
        if "finding(s), digest " not in gap.match:
            errors.append(f"{gap.check}: match does not name an exact finding set (a digest)")
    raw = tomllib.loads(paths.KNOWN_GAPS.read_text()) if paths.KNOWN_GAPS.is_file() else {}
    assert set(raw) <= {"gap"}, f"unknown tables in known_gaps.toml: {sorted(set(raw) - {'gap'})}"
    assert not errors, scan.report(errors)


def _committed_volumes() -> dict[str, bytes] | None:
    """Every history volume in HEAD's tree, with its committed bytes (spec 062, Decision 10)."""
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
    """Every volume of the history (spec 062): the chain, the names, the budget, the replay with
    every digest, volume 1's seal, and every committed volume only extended."""
    accepted = paths.ACCEPTED.read_text() if paths.ACCEPTED.is_file() else None
    found = history.found_in(paths.PROGRESS)
    errors = history.errors(found, accepted, _committed_volumes(), history.SEALED)
    assert not errors, scan.report(errors)


def test_the_newest_acceptance_sits_on_the_commit_it_judged() -> None:
    """Constitution §5.7 (spec 029, Decisions 1 and 2): the newest acceptance commit's first
    parent is the commit its history line judged, it carries only the two progress files, and it
    was made on a clean tree. Committed history only, so the lane is never red between accepting
    and committing."""
    needs.need("git", "git history")
    errors = scan.acceptance_errors(paths.REPO)
    assert not errors, scan.report(errors)


def test_the_clean_acceptance_key_is_in_the_judge() -> None:
    """Rule 1 requires `dirty: false` of an acceptance whose judge holds this file (spec 029).
    Kept here, among the protected checks, so that deleting the file cannot quietly end the
    requirement (029's build review, finding 5)."""
    assert (paths.REPO / scan.FIRST_CLEAN_JUDGE).is_file(), scan.FIRST_CLEAN_JUDGE


def test_main_is_linear() -> None:
    """Constitution §4.14 (spec 029, Decision 3): main moves only by fast-forward."""
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
    """One version in __init__.py, read dynamically, with its changelog section (spec 004)."""
    version = _release_version_module()
    errors = version.check_errors(
        version.INIT.read_text(), version.PYPROJECT.read_text(), version.CHANGELOG.read_text()
    )
    assert not errors, scan.report(errors)


def test_releases_attest_and_verify_their_assets() -> None:
    workflow = paths.REPO / ".github" / "workflows" / "release.yml"
    errors = scan.release_attestation_errors(workflow.read_text())
    assert not errors, scan.report(errors)


RELEASE_WORKFLOW = paths.REPO / ".github" / "workflows" / "release.yml"


def test_the_release_signs_and_publishes_what_build_made() -> None:
    """Every job that checks, signs or publishes downloads the build's files by an id it has
    guarded, checks them against the SHA-256 of SHA256SUMS the build job handed on, and acts on
    nothing else; the publish jobs name their environments, setup-uv runs with no cache, and each
    job holds only the permissions it uses (spec 057; the a4 security review's F4 and N3)."""
    errors = scan.release_binding_errors(RELEASE_WORKFLOW.read_text())
    assert not errors, scan.report(errors)


def test_every_action_is_pinned_by_commit() -> None:
    """Every `uses:` in every workflow is local or pinned by a full commit (spec 057)."""
    errors = [
        f"{w.name}: {e}"
        for w in sorted((paths.REPO / ".github" / "workflows").glob("*.y*ml"))
        for e in scan.action_pin_errors(w.read_text())
    ]
    assert not errors, scan.report(errors)


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
    """The workflow's own check step, run in bash: the build's own files pass, and every other
    set of bytes fails closed (spec 057, Decision 3). Its absence fails every case."""
    script = scan.workflow_step_script(RELEASE_WORKFLOW.read_text(), "attest", scan.CHECK_STEP)
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
    """The workflow's own id guard, run in bash: an empty artifact-ids would download every
    artifact of the run, so only a non-empty decimal passes (spec 057, Decision 2)."""
    script = scan.workflow_step_script(
        RELEASE_WORKFLOW.read_text(), "attest", "The build job handed on an artifact id"
    )
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
    that host's own branch of the download script; and the four files know the same hosts
    (spec 012, Decision 1)."""
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


# Spec 048, Decision 5: the runner carries two guards for wasmtime advisories while the published
# floor of the `wasmtime` requirement admits a vulnerable wasmtime. Each advisory's patched
# versions, as its record lists them (`patched_versions` in
# context/research/2026-10-18-wasmtime-49-advisories/advisories/<id>.json). Never "at or past":
# wasmtime's releases are not one ordered line (v50.0.0-rc.1 came before v49.0.3).
WASMTIME_GUARDS = {
    "GHSA-96f6-r43r-8c24": ("36.0.17", "48.0.4", "49.0.2"),  # fd_readdir's dirent padding
    "GHSA-m9f7-9w4p-gv38": ("36.0.18", "48.0.6", "49.0.3"),  # path_rename's trailing slash
}
ADVISORIES = RESEARCH / "2026-10-18-wasmtime-49-advisories" / "advisories"


def _version(text: str) -> tuple[int, int, int]:
    parts = [int(p) for p in text.strip().split(".")]
    assert 1 <= len(parts) <= 3, text
    return (*parts, 0, 0)[:3]  # type: ignore[return-value]


def _guard_may_go(requirement: str, patched: tuple[str, ...]) -> bool:
    """Condition C1: a guard may go only when, for every release line the requirement admits,
    the advisory lists a patched version in that line at or below the lowest version the
    requirement admits in it. wasmtime releases only `M.0.P` (READ, the memo's releases.txt), so
    a line is a major version. An open top, a bound with a minor version, or an operator other
    than >=, <, <= and == admits lines no list can speak for: the guard stays."""
    low, high = None, None  # inclusive low; (high, inclusive)
    for clause in requirement.split(","):
        clause = clause.strip()
        op = next((o for o in (">=", "<=", "==", "<") if clause.startswith(o)), None)
        if op is None:
            return False
        version = _version(clause[len(op) :])
        if version[1] != 0:
            return False
        if op in (">=", "=="):
            low = version if low is None else max(low, version)
        if op in ("<", "<=", "=="):
            high = (version, op != "<")
    if low is None or high is None:
        return False
    listed = [_version(v) for v in patched]
    top, inclusive = high
    for major in range(low[0], top[0] + 1):
        lowest = max(low, (major, 0, 0))
        if lowest > top or (lowest == top and not inclusive):
            continue  # nothing in this line is admitted
        if not any(v[0] == major and v <= lowest for v in listed):
            return False
    return True


def _wasmtime_requirement() -> str:
    project = tomllib.loads((paths.REPO / "pyproject.toml").read_text())["project"]
    found = [d for d in project["dependencies"] if re.match(r"wasmtime\s*[<>=!~]", d)]
    assert len(found) == 1, project["dependencies"]
    return found[0][len("wasmtime") :].strip()


def test_the_rename_and_readdir_guard_match_the_floor() -> None:
    """Spec 048, criterion 7: each guard is in the runner while the published floor (the
    `wasmtime` requirement in pyproject.toml, not uv.lock) admits a wasmtime its advisory does
    not list as patched, and is gone, with its checks, once it does not."""
    rename, padding = WASMTIME_GUARDS["GHSA-m9f7-9w4p-gv38"], WASMTIME_GUARDS["GHSA-96f6-r43r-8c24"]
    table = {
        ">=49,<50": False,  # 49.0.0 is below 49.0.2 and 49.0.3
        ">=49.0.3,<50": True,  # 49.0.2 and 49.0.3 are at or below 49.0.3
        ">=49.0.3,<51": False,  # the 50 line has no listed patched version
        ">=49.0.2,<50": None,  # the padding guard may go, the rename guard not
        ">=49.0.3": False,  # an open top
    }
    for requirement, both in table.items():
        got = (_guard_may_go(requirement, padding), _guard_may_go(requirement, rename))
        want = (True, False) if both is None else (both, both)
        assert got == want, (requirement, got)
    import json

    for advisory, patched in WASMTIME_GUARDS.items():
        record = json.loads((ADVISORIES / f"{advisory}.json").read_text())
        listed = {v["patched_versions"] for v in record["vulnerabilities"]}
        assert listed == {", ".join(patched)}, (advisory, listed)
    requirement = _wasmtime_requirement()
    source = (paths.REPO / "src" / "wasi_python" / "mounts.py").read_text()
    this = Path(__file__).resolve()
    tests = [p for p in scan.files_under(paths.REPO, "tests") if p.suffix == ".py" and p != this]
    errors = []
    for advisory, patched in WASMTIME_GUARDS.items():
        where = f"{advisory}: wasmtime{requirement} admits"
        if not _guard_may_go(requirement, patched):
            if advisory not in source:
                errors.append(f"{where} a vulnerable wasmtime, and mounts.py names no guard")
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
    the loader's environment and keeps each name's driver mode (spec 059, Decisions 3 and 4; spec
    040, Decisions 5 and 7)."""
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
    """Decision 34 (spec 069, check c): the snapshot pre-imports the stdlib's bootstrap and no
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
    systems, and no system runs a group twice (spec 063, Decision 2)."""
    from harness import shards, upstream

    groups = [g for c in upstream.load_all().values() for g in c.groups]
    files = shards.test_files(paths.tracked_files("tests"))
    errors = shards.plan_errors(shards.load(), files, groups)
    assert not errors, scan.report(errors)


def test_every_package_names_its_own_suite() -> None:
    """Every component of the artifact (paths.PACKAGES, the source components, the linked
    runtimes) runs its own suite in the release, or says what reaches it, that it only builds
    another, or which specification will run it (spec 063, Decision 15)."""
    from harness import shards, upstream

    raw = tomllib.loads(shards.PACKAGES_FILE.read_text())
    suites = {p: len(c.groups) for p, c in upstream.load_all().items()}
    errors = shards.package_errors(raw, shards.components(), suites)
    assert not errors, scan.report(errors)


def test_release_judges_in_shards() -> None:
    """The release runs every shard of the plan in its system's judge job, hands on each record's
    id and SHA-256, and publishes nothing until the gather, which holds no assets, has read every
    record (spec 063, Decisions 6 to 9 and 13)."""
    from harness import shards

    errors = scan.release_shard_errors(RELEASE_WORKFLOW.read_text(), shards.load())
    assert not errors, scan.report(errors)


# The wasi-libc emulation layer, `src/wasi_python/mounts.py`, reads alone: it asks its host nine
# questions through a protocol it declares (`_CallContext`), and imports no sibling module but
# the engine seam, which its forward uses for the fuel-neutral call. The runner imports from
# `mounts`; never the other way, so the dependency graph stays acyclic and the unit checks drive
# the table with a fake context instead of patching another module's names.
MOUNTS = "mounts.py"
MOUNTS_MAY_IMPORT = (scan.ENGINE_SEAM.rsplit("/", 1)[-1].removesuffix(".py"),)


def _sibling_imports(path: Path, allowed: tuple[str, ...]) -> list[str]:
    """Every import of a package module in `path`, at any depth, whose module is not allowed:
    a relative import (`from . import x`, `from .x import y`) or an absolute one of this
    package, `TYPE_CHECKING` blocks included."""
    import ast

    package = path.parent.name
    hits = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        named: list[str] = []
        if isinstance(node, ast.ImportFrom):
            if node.level:
                named = [node.module.split(".")[0]] if node.module else [a.name for a in node.names]
            elif node.module and node.module.split(".")[0] == package:
                parts = node.module.split(".")
                named = parts[1:2] or [a.name for a in node.names]
        elif isinstance(node, ast.Import):
            named = [
                a.name.split(".")[1]
                for a in node.names
                if a.name.split(".")[0] == package and "." in a.name
            ]
        for module in named:
            if module not in allowed:
                hits.append(f"{path.name}:{node.lineno}: imports {module}")
    return hits


def test_mounts_imports_only_the_engine_seam() -> None:
    """`mounts.py` imports no sibling module, at module level, inside a function or under
    `TYPE_CHECKING`, except the engine seam; what it needs of the runner it asks of the
    `_CallContext` it is given."""
    hits = _sibling_imports(paths.REPO / "src" / "wasi_python" / MOUNTS, MOUNTS_MAY_IMPORT)
    assert not hits, scan.report(hits)


# The platform is chosen once. `src/wasi_python/_platform.py` holds every POSIX, Linux, macOS and
# Windows difference behind one interface, bound to `PLATFORM` at import by `_select`, the one
# function in the package that reads `sys.platform` or `os.name`; every caller reads
# `_platform.PLATFORM` through its module at the call, so a check that binds another platform
# for its duration is seen by every caller. A reader who asks what Windows does differently
# opens one file.
PLATFORM_MODULE = "_platform.py"
PLATFORM_CHOOSER = "_select"
PLATFORM_READ = re.compile(r"\bos\.name\b|\bsys\.platform\b")


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


def test_the_platform_is_chosen_once() -> None:
    """No `os.name` or `sys.platform` anywhere under `src/wasi_python/` but inside
    `_platform._select`, and no import that binds `PLATFORM` to a local name."""
    hits = _platform_hits(paths.REPO / "src" / "wasi_python")
    assert not hits, scan.report(hits)


# Code speaks for itself: a code file names no specification, memo, review, finding ID or
# `context/` path; its comments and docstrings give the reason in words, and the number lives in
# the document that cites the file. `src/` is held here, over every comment token and every
# docstring (through `tokenize`, so an identifier or a literal never trips it). Eight regexes:
# a specification number in any form, a decision number with or without one (case-sensitive:
# every citation writes "Decision 8", and "a decision" in prose stays free), the constitution,
# the memo, any form of the word "review", a numbered question, a `context/` path, and a one-
# or two-digit finding ID (`F3`, `N12`, `F4.2`, `S3`, `D3`, `C6`, `L1`; the look-arounds keep
# `F401` in a `noqa` and a word like `MD5` out). The regexes refuse more than citations: `C99`,
# `L1` as a cache level, `F1` as a key, and the words "memo" and "review" in any use; a comment
# that needs such a word writes around it. Where words will not do, CITATION_ALLOWED carries the
# exact token with a one-line reason; a citation of a `context/` document is never added.
CITATION_KINDS = {
    "specification number": re.compile(r"\bspec(?:ification)?s?\s+\d{3}\b", re.I),
    "decision number": re.compile(r"\bDecisions?\s+\d+\b"),
    "constitution": re.compile(r"\bconstitution\b", re.I),
    "memo": re.compile(r"\bmemo\b", re.I),
    "review": re.compile(r"\breviews?\b|\bre-review|\bconfirmation's\b", re.I),
    "question": re.compile(r"\bquestion\s+\d+\b", re.I),
    "context path": re.compile(r"\bcontext/"),
    "finding ID": re.compile(r"(?<![A-Za-z0-9_])[CDFLNS]\d{1,2}(?:\.\d+)?(?![A-Za-z0-9_])"),
}
CITATION_ALLOWED: tuple[tuple[str, str], ...] = ()  # (exact token, why words would not do)


def _prose(path: Path) -> list[tuple[int, str]]:
    """(line, text) for every comment token and every line of every docstring: a string that is
    the first token of a module, a class or a function body, or stands alone as a statement."""
    import io
    import tokenize

    out: list[tuple[int, str]] = []
    last: int | None = None
    opening = (None, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.NL)
    for tok in tokenize.generate_tokens(io.StringIO(path.read_text(encoding="utf-8")).readline):
        if tok.type == tokenize.COMMENT:
            out.append((tok.start[0], tok.string))
        elif tok.type == tokenize.STRING and last in opening:
            out += [(tok.start[0] + i, line) for i, line in enumerate(tok.string.splitlines())]
        if tok.type not in (tokenize.NL, tokenize.COMMENT):
            last = tok.type
    return out


def _citation_hits(root: Path) -> list[str]:
    allowed = {token for token, _ in CITATION_ALLOWED}
    hits = []
    for path in sorted(p for p in scan.files_under(root, ".") if p.suffix == ".py"):
        for line, text in _prose(path):
            for kind, pattern in CITATION_KINDS.items():
                for m in pattern.finditer(text):
                    if m.group(0) not in allowed:
                        hits.append(f"{scan.rel(path, paths.REPO)}:{line}: {kind} {m.group(0)!r}")
    return hits


def test_src_names_no_context_document() -> None:
    """No specification number, decision number, constitution, memo, review, numbered question,
    `context/` path or finding ID in any comment or docstring of any `.py` under `src/`."""
    hits = _citation_hits(paths.REPO / "src")
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
    only shrinks; `tools`, `cli` and the package itself are outside the rule, as is a class
    attribute or an attribute of a call's result (`process().observers`)."""
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
    # The tool protocol's validator and the host's answer, one concern each a helper would take.
    "tools.py:_make": 82,
    "tools.py:_ToolHost._answer": 83,
}


def test_no_function_is_over_eighty_lines() -> None:
    """No function or method in src/wasi_python, nested ones included, is over
    scan.FUNCTION_CEILING lines but for LONG_FUNCTIONS, which only shrinks."""
    files = [p for p in scan.files_under(paths.REPO, "src") if p.suffix == ".py"]
    hits = scan.long_function_hits(files, paths.REPO, LONG_FUNCTIONS)
    assert not hits, scan.report(hits)
