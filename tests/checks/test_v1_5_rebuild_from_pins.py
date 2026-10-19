"""v1.5: the whole thing rebuilds from pinned sources; each upstream tree is its tarball plus
exactly the recorded patches (constitution §4.1, spec 020)."""

from __future__ import annotations

import hashlib
import importlib.util
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from harness import artifacts as rules
from harness import needs, paths, pins, scan

pytestmark = pytest.mark.goal("v1.5")

SCRIPTS = paths.REPO / "scripts"
DOWNLOAD_SCRIPT = SCRIPTS / "00_download.sh"


def _scripts():
    """Every file under scripts/, steps included (spec 003, Decision 13)."""
    return scan.every_file(SCRIPTS)


def test_pin_list_is_well_formed() -> None:
    paths.read_pin_list()  # raises with the line on any malformed or repeated entry


def test_every_pin_is_fetched_from_a_literal_url() -> None:
    errors = scan.url_errors(DOWNLOAD_SCRIPT, paths.read_pin_list())
    assert not errors, scan.report(errors)


def test_download_script_verifies_and_never_writes_the_pins() -> None:
    errors = scan.download_script_errors(DOWNLOAD_SCRIPT)
    assert not errors, scan.report(errors)


def test_every_fetched_file_is_pinned() -> None:
    """Every file a get or research line fetches has its line in SHA256SUMS (spec 057)."""
    errors = scan.unpinned_fetch_errors(DOWNLOAD_SCRIPT, paths.read_pin_list())
    assert not errors, scan.report(errors)


FAKE_UNAME = """#!/bin/sh
case "$1" in -s) echo "$FAKE_S";; -m) echo "$FAKE_M";; *) echo "$FAKE_S";; esac
"""
FAKE_CURL = """#!/bin/sh
echo "curl must not run: $*" >&2
exit 99
"""
HOSTS = {
    "MACOS_ARM64": ("Darwin", "arm64"),
    "LINUX_AARCH64": ("Linux", "aarch64"),
    "LINUX_X86_64": ("Linux", "x86_64"),
}


def _run_download(repo: Path, bin_dir: Path, host: str) -> subprocess.CompletedProcess:
    s, m = HOSTS[host]
    return subprocess.run(
        ["sh", str(repo / "scripts" / "00_download.sh")],
        env={"PATH": f"{bin_dir}:/usr/bin:/bin", "FAKE_S": s, "FAKE_M": m},
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("host", HOSTS)
def test_download_step_fails_on_a_fetched_file_with_no_pin(host, tmp_path) -> None:
    """The download step, run on a copy with a fake file per fetched name, a fake uname for each
    build host and a curl that fails if called: with every pin it passes, N of N verified; with
    one pin's line gone it fails and names the file (spec 057, Decision 5; the a4 review's N1)."""
    repo, bin_dir = tmp_path / "repo", tmp_path / "bin"
    (repo / "scripts").mkdir(parents=True)
    (repo / "downloads").mkdir()
    bin_dir.mkdir()
    for name in ("00_download.sh", "line.sh", "line.conf"):
        shutil.copy(SCRIPTS / name, repo / "scripts" / name)
    for name, text in (("uname", FAKE_UNAME), ("curl", FAKE_CURL)):
        (bin_dir / name).write_text(text)
        (bin_dir / name).chmod(0o755)
    text = (repo / "scripts" / "00_download.sh").read_text()
    names = {name or url.rsplit("/", 1)[-1] for url, name in scan.GET.findall(text)}
    sums = []
    for name in sorted(names):
        (repo / "downloads" / name).write_bytes(f"fake {name}\n".encode())
        sums.append(f"{paths.sha256_file(repo / 'downloads' / name)}  {name}\n")
    (repo / "downloads" / "SHA256SUMS").write_text("".join(sums))
    whole = _run_download(repo, bin_dir, host)
    summary = whole.stdout.strip().splitlines()[-1] if whole.stdout.strip() else ""
    m = re.match(r"downloads: (\d+) pins, 0 fetched, (\d+) verified", summary)
    assert whole.returncode == 0 and m and m[1] == m[2], (whole.returncode, whole.stderr[-300:])
    (repo / "downloads" / "SHA256SUMS").write_text(
        "".join(line for line in sums if not line.endswith("  zlib-1.3.1.tar.gz\n"))
    )
    short = _run_download(repo, bin_dir, host)
    assert short.returncode == 1, (short.returncode, short.stdout[-300:])
    assert "zlib-1.3.1.tar.gz" in short.stderr and "curl must not run" not in short.stderr, (
        short.stderr
    )


def test_no_build_script_fetches_outside_the_download_script() -> None:
    hits = scan.fetch_hits(_scripts(), DOWNLOAD_SCRIPT.name, paths.REPO)
    assert not hits, scan.report(hits)


def test_every_repository_path_a_recipe_names_exists() -> None:
    files = _scripts() + scan.every_file(paths.REPO / "recipes")
    errors = scan.recipe_path_errors(files, paths.REPO)
    assert not errors, scan.report(errors)


def test_toolchain_is_pinned_for_linux_and_macos() -> None:
    errors = scan.toolchain_errors(paths.read_pin_list())
    assert not errors, scan.report(errors)


def test_cpp_is_compiled_with_exceptions() -> None:
    errors = scan.cpp_exception_errors(paths.REPO)
    assert not errors, scan.report(errors)


def test_pure_python_packages_are_pinned() -> None:
    errors = scan.pure_python_errors(paths.read_pin_list())
    assert not errors, scan.report(errors)


@pytest.mark.parametrize("component", needs.SOURCE_COMPONENTS)
def test_source_tree_matches_its_tarball(component) -> None:
    needs.need(f"source tree {component}")
    tarball, tree = pins.source_pair(component)
    pinned = paths.read_pin_list()[tarball.name]
    actual = paths.sha256_file(tarball)
    assert actual == pinned, scan.report([f"{tarball.name}: sha256 {actual}, pinned {pinned}"])
    top = re.sub(r"\.tar\.\w+$", "", tarball.name)
    assert pins.top_dir(tarball) == top, f"{tarball.name}: its top folder is not {top}"
    drift = pins.tree_drift(tarball, tree)
    assert not drift, scan.report(drift)


def test_release_workflow_runs_the_zero_patch_check() -> None:
    workflows = sorted((paths.REPO / ".github" / "workflows").glob("*.y*ml"))
    good = [
        w
        for w in workflows
        if re.search(r"\bworkflow_dispatch\b", w.read_text())
        and "test_source_tree_matches_its_tarball" in w.read_text()
    ]
    missing = (
        []
        if good
        else ["no release workflow with workflow_dispatch checks the trees against their tarballs"]
    )
    assert not missing, scan.report(missing)


def test_stdlib_zip_names_no_build_host(artifacts) -> None:
    """_sysconfigdata and numpy's __config__ say nothing about the machine that built them, so the
    zip, and the snapshot that holds its offsets, are the same bytes from any host (spec 012,
    Decision 5)."""
    needs.need("stdlib zip")
    errors = rules.host_fact_errors(artifacts.path("python-stdlib.zip"), str(paths.REPO))
    assert not errors, scan.report(errors)


def test_release_workflow_rebuilds_on_two_more_hosts() -> None:
    """An arm64 Linux runner and an x86_64 Linux runner rebuild the set beside the build, each
    within its own time limit and printing its core count and binfmt_misc entries, and nothing is
    signed or published until each one's SHA256SUMS and wheel equal the set's (spec 012,
    Decision 7; spec 040, Decision 6)."""
    workflow = paths.REPO / ".github" / "workflows" / "release.yml"
    errors = scan.rebuild_gate_errors(workflow.read_text())
    assert not errors, scan.report(errors)


def test_every_compile_contracts_nothing() -> None:
    """Every compile carries -ffp-contract=off, set once in the toolchain's own clang.cfg and
    clang++.cfg by step 10, and nothing overrides it: no recipe file, no compiler command in the
    build's records (every meson build's compile_commands.json, the autoconf Makefiles, CPython's
    cross-build Makefile, step 60's command files), no source pragma, and the compiler's own -cc1
    line says so (spec 059, Decisions 1, 2 and 4). Without a build, the record parts are blocked."""
    step_10 = SCRIPTS / "steps" / "10_tools.sh"
    files = {
        rel: (paths.REPO / rel).read_text(errors="replace")
        for rel in paths.tracked_files("scripts", "recipes")
        if (paths.REPO / rel).is_file() and rel != "scripts/steps/10_tools.sh"
    }
    errors = scan.fp_recipe_errors(scan.code_text(step_10), files)
    assert not errors, scan.report(errors)
    needs.need("compile records")
    errors, read = scan.fp_record_errors(paths.REPO)
    trees = [pair[1] for c in needs.SOURCE_COMPONENTS if (pair := pins.source_pair(c))]
    trees += [paths.BUILD / name for name in scan.MESON_BUILDS if (paths.BUILD / name).is_dir()]
    # The project's own C under recipes/ too: the rename headers are force-included into every
    # numpy and pandas compile, and reactor_main.c is compiled in step 60 (the build review, F2).
    errors += scan.fp_pragma_hits([*trees, paths.REPO / "recipes"])
    read.append(f"source trees, meson folders and recipes/ grepped for pragmas: {len(trees) + 1}")
    for clang in sorted((paths.BUILD / "tools").glob("wasi-sdk-*/bin/clang")):
        errors += scan.fp_compiler_errors(clang.parent)
        read.append(f"{clang.parent.parent.name}: clang and clang++ probed with -###")
    print("\n".join(read))
    assert not errors, scan.report(errors) + "\nread:\n" + "\n".join(read)


def _line_values() -> dict[str, str]:
    """scripts/line.conf as the build reads it, through its own parser (spec 005)."""
    spec = importlib.util.spec_from_file_location("wasi_python_line", SCRIPTS / "line.py")
    assert spec is not None and spec.loader is not None
    line = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(line)
    return line.read(SCRIPTS / "line.conf")


def test_every_build_python_is_pinned() -> None:
    """Every Python a build step runs is the pinned host Python or one built from pins (spec 079):
    step 10's shim comes first on every step's PATH, build.sh puts a refusing stand-in for every
    other Python name behind it, and the build's records (each meson build's log and build.ninja,
    every config.log, the folders steps put on PATH, step 10's gate line) name no other
    interpreter. Without a build, the record part is blocked."""
    errors = scan.host_python_recipe_errors(paths.REPO)
    assert not errors, scan.report(errors)
    needs.need("compile records")
    steps = {
        p.name: p.read_text(errors="replace") for p in sorted((SCRIPTS / "steps").glob("*.sh"))
    }
    errors, read = scan.host_python_record_errors(paths.REPO, _line_values(), steps)
    print("\n".join(read))
    assert not errors, scan.report(errors) + "\nread:\n" + "\n".join(read)


# The backend's try_table order (spec 086, Decision 7 (a)): the memo's reproducer
# (context/research/2026-10-19-the-try-table-order-in-llvm/), copied under the judge's paths and
# named by its hash, compiled 64 times by each unpacked clang in the set's exception mode. wasi-sdk
# 33's clang (LLVM 22.1.0) nests its try_table blocks by heap address and gives two objects; LLVM's
# fd76c9bd (in wasi-sdk 34) gives one.
TRY_TABLE_FIXTURE = paths.REPO / "tests" / "fixtures" / "try-table-order.ll"
TRY_TABLE_SHA256 = "63a709ecfd611ccbe7d2beb4d5c5c2b85e450fa2217296d117957b398ee138a3"
TRY_TABLE_RUNS = 64
TRY_TABLE_FLAGS = (
    "--target=wasm32-wasip1",
    "-O3",
    "-fwasm-exceptions",
    "-mllvm",
    "-wasm-use-legacy-eh=false",
    "-c",
    "-Xclang",
    "-disable-llvm-passes",
)


def test_the_backend_orders_try_tables_alike(tmp_path) -> None:
    """Spec 086, Decision 7 (a): each pinned clang under build/tools/ compiles the reduced
    try_table case to one object in 64 runs. It counts distinct objects, never time. A run with no
    clang found fails: the check must compile something to pass."""
    digest = hashlib.sha256(TRY_TABLE_FIXTURE.read_bytes()).hexdigest()
    assert digest == TRY_TABLE_SHA256, f"{TRY_TABLE_FIXTURE.name} is {digest}, not the memo's"
    needs.need("compile records")
    clangs = sorted((paths.BUILD / "tools").glob("wasi-sdk-*/bin/clang"))
    assert clangs, "no build/tools/wasi-sdk-*/bin/clang: nothing was compiled"
    errors = []
    for clang in clangs:
        sdk = clang.parent.parent.name
        seen: dict[str, int] = {}
        for i in range(TRY_TABLE_RUNS):
            out = tmp_path / f"{sdk}-{i}.o"
            done = subprocess.run(
                [str(clang), *TRY_TABLE_FLAGS, str(TRY_TABLE_FIXTURE), "-o", str(out)],
                capture_output=True,
                text=True,
            )
            assert done.returncode == 0, f"{sdk}: clang failed: {done.stderr.strip()[-300:]}"
            h = hashlib.sha256(out.read_bytes()).hexdigest()
            seen[h] = seen.get(h, 0) + 1
        print(f"{sdk}: {len(seen)} object(s) in {TRY_TABLE_RUNS} runs")
        if len(seen) != 1:
            counts = ", ".join(f"{h[:12]} x{n}" for h, n in sorted(seen.items()))
            errors.append(f"{sdk}: {len(seen)} objects in {TRY_TABLE_RUNS} runs ({counts})")
    assert not errors, "\n".join(errors)


CPYTHON_CONFIGURE = paths.REPO / "tests" / "cpython_configure.txt"
PYCONFIG = Path("Python-3.15.0") / "cross-build" / "wasm32-wasip1" / "pyconfig.h"
DEFINE = re.compile(r"^\s*#\s*define\s+(\S+)(?:\s+(.*?))?\s*$")


def _defines(text: str) -> set[str]:
    """Every #define of a header, indented or not, as `NAME VALUE`."""
    return {
        f"{m[1]} {m[2] or ''}".rstrip() for line in text.splitlines() if (m := DEFINE.match(line))
    }


def test_the_guests_configure_results_are_recorded() -> None:
    """Spec 086, Decision 7 (c): every #define of the guest CPython's pyconfig.h equals
    tests/cpython_configure.txt, so a toolchain that flips a configure result (wasi-sdk 34 flipped
    ten HAVE_* lines) fails here and its specification says why. A line holding a word
    context/embedders.txt reserves is not written in the file (constitution §4.5); the file's
    digest, over every line, covers it. Without a build, blocked."""
    text = CPYTHON_CONFIGURE.read_text().splitlines()
    digests = [line.split()[1] for line in text if line.startswith("digest ")]
    assert len(digests) == 1, "tests/cpython_configure.txt holds no single digest line"
    recorded = {line for line in text if line.strip() and not line.startswith(("#", "digest "))}
    needs.need("compile records")
    header = paths.BUILD / PYCONFIG
    assert header.is_file(), f"no build/{PYCONFIG}"
    built = _defines(header.read_text(errors="replace"))
    reserved = scan.read_names(paths.EMBEDDERS)
    visible = {line for line in built if not any(name in line.lower() for name in reserved)}
    new = sorted(visible - recorded)
    gone = sorted(recorded - visible)
    errors = [f"+{line} (built, not recorded)" for line in new]
    errors += [f"-{line} (recorded, not built)" for line in gone]
    digest = hashlib.sha256("\n".join(sorted(built)).encode()).hexdigest()
    if not errors and digest != digests[0]:
        errors.append(f"a line holding a reserved word moved: digest {digest}, not {digests[0]}")
    assert not errors, "\n".join(errors)
