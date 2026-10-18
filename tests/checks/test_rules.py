"""rules: the mechanically checkable parts of the constitution (§4, §5, §7)."""

from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from harness import needs, paths, scan, scoreboard

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


def _committed(path: Path) -> str | None:
    if not needs.VOCABULARY["git"].met():
        return None
    rel = path.relative_to(paths.REPO)
    r = subprocess.run(
        ["git", "-C", str(paths.REPO), "show", f"HEAD:{rel}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return r.stdout if r.returncode == 0 else None


def test_progress_history_is_intact() -> None:
    history = paths.HISTORY.read_text() if paths.HISTORY.is_file() else ""
    accepted = paths.ACCEPTED.read_text() if paths.ACCEPTED.is_file() else None
    errors = scoreboard.history_errors(history, accepted, _committed(paths.HISTORY))
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


def test_the_version_is_released_by_the_book() -> None:
    """One version in __init__.py, read dynamically, with its changelog section (spec 004)."""
    import importlib.util
    import sys

    path = paths.REPO / "release" / "version.py"
    spec = importlib.util.spec_from_file_location("release_version", path)
    version = importlib.util.module_from_spec(spec)
    sys.modules["release_version"] = version  # dataclasses look their module up here
    spec.loader.exec_module(version)
    errors = version.check_errors(
        version.INIT.read_text(), version.PYPROJECT.read_text(), version.CHANGELOG.read_text()
    )
    assert not errors, scan.report(errors)


def test_releases_attest_and_verify_their_assets() -> None:
    workflow = paths.REPO / ".github" / "workflows" / "release.yml"
    errors = scan.release_attestation_errors(workflow.read_text())
    assert not errors, scan.report(errors)


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


def test_x86_64_compiles_with_an_aarch64_compiler() -> None:
    """Every build host compiles with an arm64 build of the pinned clang: its own SDK's, or, on
    x86_64 Linux, the arm64 Linux SDK's under the pinned qemu, with its five packages pinned and
    fetched in that host's branch, step 10 laying out and probing the emulated compiler, and the
    launcher clearing the emulator's and the loader's environment and keeping each name's driver
    mode (spec 040, Decisions 4, 5 and 7)."""
    scripts = paths.REPO / "scripts"
    errors = scan.compiler_table_errors(
        (scripts / "line.conf").read_text(),
        (scripts / "00_download.sh").read_text(),
        paths.read_pin_list(),
        scan.code_text(scripts / "steps" / "10_tools.sh") or "",
        scan.code_text(scripts / "clang-emulated"),
    )
    assert not errors, scan.report(errors)
