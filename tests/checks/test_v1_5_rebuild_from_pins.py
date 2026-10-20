"""v1.5: the whole thing rebuilds from pinned sources; each upstream tree is its tarball plus
exactly the recorded patches."""

from __future__ import annotations

import hashlib
import importlib.util
import json
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
    """Every file under scripts/, steps included."""
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
    """Every file a get or research line fetches has its line in SHA256SUMS."""
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
    one pin's line gone it fails and names the file."""
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


OPENBLAS_PATCHES = (
    "0001-c-lapack-subroutines-return-void-1-of-2.patch",
    "0002-c-lapack-subroutines-return-void-2-of-2.patch",
    "0003-ilaver-returns-void.patch",
)


def test_the_openblas_patches_are_what_their_script_makes() -> None:
    """OpenBLAS's three carried patches are byte for byte what their script makes from the pinned
    tarball (scripts/make_openblas_void_patch.sh, git run with no caller configuration), each
    draft's `Files:` line is the script's, and the audit pairs every changed line of the
    convention's two with one of its rules."""
    import sys

    needs.need("source tree openblas")
    out = paths.HARNESS_TMP / "openblas-void"
    shutil.rmtree(out, ignore_errors=True)
    env = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "PYTHON": sys.executable}
    made = subprocess.run(
        ["sh", str(SCRIPTS / "make_openblas_void_patch.sh"), str(out)],
        env=env,
        capture_output=True,
        text=True,
    )
    assert made.returncode == 0, made.stderr[-1500:]
    carried = paths.REPO / "recipes" / "patches" / "OpenBLAS-0.3.34"
    drafts = paths.REPO / "context" / "upstream" / "patches" / "OpenBLAS-0.3.34"
    assert sorted(p.name for p in carried.glob("*.patch")) == list(OPENBLAS_PATCHES)
    errors = []
    for name in OPENBLAS_PATCHES:
        if (out / name).read_bytes() != (carried / name).read_bytes():
            errors.append(f"{name}: the carried patch is not what the script makes")
        files = ", ".join((out / f"{name}.files").read_text().split())
        draft = (drafts / name.replace(".patch", ".md")).read_text()
        if f"- **Files:** {files}\n" not in draft:
            errors.append(f"{name}: its draft's Files: line is not the script's")
    assert not errors, scan.report(errors)
    audit = subprocess.run(
        [sys.executable, "-I", str(SCRIPTS / "audit_openblas_void.py")]
        + [str(carried / n) for n in OPENBLAS_PATCHES],
        capture_output=True,
        text=True,
    )
    assert audit.returncode == 0, audit.stdout[-1500:]
    shutil.rmtree(out, ignore_errors=True)


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
    zip, and the snapshot that holds its offsets, are the same bytes from any host."""
    needs.need("stdlib zip")
    errors = rules.host_fact_errors(artifacts.path("python-stdlib.zip"), str(paths.REPO))
    assert not errors, scan.report(errors)


def test_release_workflow_rebuilds_on_two_more_hosts() -> None:
    """An arm64 Linux runner and an x86_64 Linux runner rebuild the set beside the build, each
    within its own time limit and printing its core count and binfmt_misc entries, and nothing is
    signed or published until each one's SHA256SUMS and wheel equal the set's."""
    workflow = paths.REPO / ".github" / "workflows" / "release.yml"
    errors = scan.rebuild_gate_errors(workflow.read_text())
    assert not errors, scan.report(errors)


def test_every_compile_contracts_nothing() -> None:
    """Every compile carries -ffp-contract=off, set once in the toolchain's own clang.cfg and
    clang++.cfg by step 10, and nothing overrides it: no recipe file, no compiler command in the
    build's records (every meson build's compile_commands.json, the autoconf Makefiles, CPython's
    cross-build Makefile, step 60's command files), no source pragma, and the compiler's own -cc1
    line says so. Without a build, the record parts are blocked."""
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
    # numpy and pandas compile, and reactor_main.c is compiled in step 60.
    errors += scan.fp_pragma_hits([*trees, paths.REPO / "recipes"])
    read.append(f"source trees, meson folders and recipes/ grepped for pragmas: {len(trees) + 1}")
    for clang in sorted((paths.BUILD / "tools").glob("wasi-sdk-*/bin/clang")):
        errors += scan.fp_compiler_errors(clang.parent)
        read.append(f"{clang.parent.parent.name}: clang and clang++ probed with -###")
    print("\n".join(read))
    assert not errors, scan.report(errors) + "\nread:\n" + "\n".join(read)


def test_every_numpy_compile_keeps_its_floating_point_flags_in_software(note) -> None:
    """numpy's own floating-point signals are kept in software. Without a
    build: the numpy cross file force-includes recipes/npy_fenv_flags.h once in `c_args` and once
    in `cpp_args`, and the header holds its guard, bits, weak word and renames. With the compile
    records: every compile in numpy's own `compile_commands.json`, picked by compiler (the first
    argument's path ends in scripts/wasi-cc or scripts/wasi-cxx, with `-c`), carries the header
    exactly once; numpy's file missing while another build's records exist is a failure."""
    header = paths.REPO / scan.NPY_FENV_HEADER
    errors = scan.npy_fenv_recipe_errors(
        (paths.REPO / scan.NPY_FENV_CROSS).read_text(),
        header.read_text() if header.is_file() else None,
    )
    assert not errors, scan.report(errors)
    needs.need("compile records")
    errors, counts = scan.npy_fenv_records_file_errors(paths.REPO)
    assert not errors, scan.report(errors)
    note(", ".join(f"{k} {v}" for k, v in counts.items()))


def _nm_names(nm: Path, *args: str) -> set[str]:
    """Symbol names llvm-nm prints with -j (names only) for the given flags and files."""
    out = subprocess.run([str(nm), "-j", *args], capture_output=True, text=True, check=True).stdout
    return {s for s in out.splitlines() if s and not s.endswith(":")}


def test_one_lapack_is_linked(note) -> None:
    """numpy runs on the set's OpenBLAS, the one scipy runs (spec 100, check 4), in the form of
    test_one_qhull_is_linked. Without a build: the numpy cross file names step 10's pkgconf and no
    BLAS_SYMBOL_PREFIX, recipes/numpy_lapack_abi.h sets numpy's prefix, the per-file map has its
    four entries, and step 40 asks meson for OpenBLAS with no fallback. With the build: each
    per-file entry matched its count (the log missing is a failure); numpy compiled no
    lapack_lite f2c file and carries no BLAS_SYMBOL_PREFIX; its linear-algebra and core modules'
    .deps name only step 38's OpenBLAS; in python.wasm's link map every symbol libopenblas.a
    defines comes from it, once, with no lapack_lite and every wasi_numpy_ shim once from numpy's
    shims archive; and the shims are exactly the wasi_numpy_ names numpy's two linear-algebra
    objects call, less xerbla (the review's L6)."""
    header = paths.REPO / scan.ONE_LAPACK_HEADER
    errors = scan.one_lapack_recipe_errors(
        (paths.REPO / scan.ONE_LAPACK_CROSS).read_text(),
        header.read_text() if header.is_file() else None,
        (paths.REPO / scan.ONE_LAPACK_MAP).read_text(),
        (paths.REPO / scan.ONE_LAPACK_STEP).read_text(),
    )
    assert not errors, scan.report(errors)
    needs.need("compile records")
    build = paths.BUILD / "numpy-build"
    log = build / "file-includes.log"
    entries = scan.include_map_entries((paths.REPO / scan.ONE_LAPACK_MAP).read_text())
    errors = scan.include_log_errors(entries, log.read_text() if log.is_file() else None)
    records = build / "compile_commands.json"
    objects = sorted(str(p.relative_to(build)) for p in build.rglob("*.o"))
    errors += scan.numpy_blas_record_errors(
        json.loads(records.read_text()) if records.is_file() else [], objects
    )
    archive = paths.BUILD / "openblas-wasi" / "lib" / scan.ONE_LAPACK_ARCHIVE
    deps = {}
    for pattern in (
        "numpy/linalg/_umath_linalg.*.so.deps",
        "numpy/linalg/lapack_lite.*.so.deps",
        "numpy/_core/_multiarray_umath.*.so.deps",
    ):
        found = sorted(build.glob(pattern))
        if len(found) != 1:
            errors.append(f"build/numpy-build/{pattern}: {len(found)} files, not 1")
            continue
        deps[found[0].name] = found[0].read_text().split()
    errors += scan.numpy_deps_errors(deps, archive)
    nm = paths.BUILD / "tools" / _line_values()["WASI_SDK_DIR"] / "bin" / "llvm-nm"
    shims = paths.BUILD / "numpy-shims" / scan.ONE_LAPACK_SHIMS
    link_map = paths.BUILD / "link" / "python.map"
    linalg = [
        *build.glob("numpy/linalg/_umath_linalg.*.so.p/umath_linalg.cpp.o"),
        *build.glob("numpy/linalg/lapack_lite.*.so.p/lapack_litemodule.c.o"),
    ]
    for path, what in ((archive, "step 38"), (shims, "step 40"), (link_map, "step 60")):
        if not path.is_file():
            errors.append(f"no {path.relative_to(paths.BUILD)}: {what} has not run")
    if len(linalg) != 2:
        errors.append(f"{len(linalg)} of numpy's two linear-algebra objects found")
    if not errors:
        called = {n for n in _nm_names(nm, "-u", *map(str, linalg)) if n.startswith("wasi_numpy_")}
        with link_map.open(errors="replace") as f:
            errors += scan.one_lapack_errors(
                f,
                _nm_names(nm, "-g", "--defined-only", str(archive)),
                _nm_names(nm, "-g", "--defined-only", str(shims)),
                called,
            )
        note(f"{len(called - {scan.ONE_LAPACK_XERBLA})} shims called and defined")
    assert not errors, scan.report(errors)


def _line_values() -> dict[str, str]:
    """scripts/line.conf as the build reads it, through its own parser."""
    spec = importlib.util.spec_from_file_location("wasi_python_line", SCRIPTS / "line.py")
    assert spec is not None and spec.loader is not None
    line = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(line)
    return line.read(SCRIPTS / "line.conf")


def test_every_build_python_is_pinned() -> None:
    """Every Python a build step runs is the pinned host Python or one built from pins:
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


# The backend's try_table order: the research's reduced reproducer, copied under the judge's
# paths and named by its hash, compiled 64 times by each unpacked clang in the set's exception
# mode. wasi-sdk 33's clang (LLVM 22.1.0) nests its try_table blocks by heap address and gives
# two objects; LLVM's fd76c9bd (in wasi-sdk 34) gives one.
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
    """Each pinned clang under build/tools/ compiles the reduced
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


# scipy's ducc0 FFT: wasi-sdk 33's clang compiled it
# to another object on every run (32 compiles, 32 objects), the one file of scipy's 910 that did.
DUCC0 = "scipy/fft/_duccfft/pyduccfft.cxx"
DUCC0_RUNS = 3


@pytest.mark.slow
def test_ducc0s_fft_compiles_to_one_object(tmp_path) -> None:
    """`pyduccfft.cxx`, compiled
    three times at once with its own command from the build's compile_commands.json, gives one
    object, so `python.wasm` is the same bytes from every build with no exception. It counts
    distinct objects, never time. The opposite of the withdrawn still-needed check, which passed on
    wasi-sdk 33 because three compiles gave three objects."""
    import json
    import shlex

    needs.need("compile records")
    build = paths.BUILD / "scipy-build"
    (entry,) = [
        e
        for e in json.loads((build / "compile_commands.json").read_text())
        if e["file"].endswith(DUCC0)
    ]
    keep, skip = [], 0
    for word in shlex.split(entry["command"]):
        if skip:
            skip -= 1
        elif word in ("-MQ", "-MF", "-o"):
            skip = 1
        elif word != "-MD":
            keep.append(word)
    sdk = paths.BUILD / "tools" / _line_values()["WASI_SDK_DIR"]
    env = {"PATH": "/usr/bin:/bin", "WASI_SDK_PATH": str(sdk)}
    if (build / "file-includes.txt").is_file():
        env["WASI_CC_FILE_INCLUDES"] = str(build / "file-includes.txt")
        env["WASI_CC_FILE_INCLUDES_LOG"] = str(tmp_path / "file-includes.log")
    objects = [tmp_path / f"compile-{n}.o" for n in range(DUCC0_RUNS)]
    runs = [
        subprocess.Popen([*keep, "-o", str(o)], cwd=entry["directory"], env=env) for o in objects
    ]
    assert all(r.wait() == 0 for r in runs), f"a compile of {DUCC0} failed"
    digests = sorted({hashlib.sha256(o.read_bytes()).hexdigest() for o in objects})
    print(f"{DUCC0}: {len(digests)} object(s) in {DUCC0_RUNS} compiles")
    assert len(digests) == 1, (
        f"{DUCC0}: {len(digests)} objects in {DUCC0_RUNS} compiles "
        f"({', '.join(d[:12] for d in digests)}): the clang varies again (spec 086, Decision 7)"
    )


# One qhull: scipy's spatial._qhull and
# matplotlib's _qhull both link step 37's libqhull_r, never scipy's vendored copy.
QHULL_ARCHIVE = Path("plot-libs") / "lib" / "libqhull_r.a"
QHULL_MODULE_DEPS = ("plot-modules/matplotlib/matplotlib", "scipy-modules/scipy/spatial")
LINK_MAP_FUNCTION = re.compile(r"^\s+-\s+[0-9a-f]+\s+[0-9a-f]+\s+(\S+?)\((.+)\):\(([^)]+)\)$")


def test_one_qhull_is_linked() -> None:
    """Every function step 37's libqhull_r.a defines that python.wasm
    links comes from that archive and is linked once (the link map), `qh_new_qhull` among them;
    the map names no qhull archive of scipy's own; and each _qhull module's .deps names qhull
    only as step 37's archive or `-lqhull_r` (condition e). Without a build, blocked."""
    needs.need("compile records")
    archive = paths.BUILD / QHULL_ARCHIVE
    link_map = paths.BUILD / "link" / "python.map"
    assert archive.is_file(), f"no build/{QHULL_ARCHIVE}: step 37 has not run"
    assert link_map.is_file(), "no build/link/python.map: step 60 has not run"
    nm = paths.BUILD / "tools" / _line_values()["WASI_SDK_DIR"] / "bin" / "llvm-nm"
    listed = subprocess.run(
        [str(nm), "-g", "-j", "--defined-only", str(archive)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    defined = {s for s in listed if s and not s.endswith(":")}
    assert "qh_new_qhull" in defined, f"build/{QHULL_ARCHIVE} does not define qh_new_qhull"
    errors = []
    linked: dict[str, list[str]] = {}
    with link_map.open(errors="replace") as f:
        for line in f:
            if "qhull" not in line:
                continue
            if "subprojects/qhull_r" in line:
                errors.append(f"the link map names scipy's vendored qhull: {line.strip()[-160:]}")
                continue
            m = LINK_MAP_FUNCTION.match(line.rstrip("\n"))
            if m and m[3] in defined:
                linked.setdefault(m[3], []).append(m[1])
    for name, sources in sorted(linked.items()):
        if len(sources) != 1:
            errors.append(f"{name} is linked {len(sources)} times")
        if any(Path(s).resolve() != archive.resolve() for s in sources):
            errors.append(f"{name} comes from {sorted(set(sources))}, not build/{QHULL_ARCHIVE}")
    if "qh_new_qhull" not in linked:
        errors.append("python.wasm links no qh_new_qhull from the link map")
    for folder in QHULL_MODULE_DEPS:
        deps = sorted((paths.BUILD / folder).glob("_qhull.*.so.deps"))
        if len(deps) != 1:
            errors.append(f"build/{folder}: {len(deps)} _qhull .deps files, not 1")
            continue
        for dep in deps[0].read_text().split():
            if "qhull" in dep and dep != "-lqhull_r" and Path(dep).resolve() != archive.resolve():
                errors.append(f"{deps[0].relative_to(paths.BUILD)} names {dep}")
    print(f"qhull: {len(linked)} of {len(defined)} functions linked from build/{QHULL_ARCHIVE}")
    assert not errors, scan.report(errors)


CPYTHON_CONFIGURE = paths.REPO / "tests" / "cpython_configure.txt"
PYCONFIG = Path("Python-3.15.0") / "cross-build" / "wasm32-wasip1" / "pyconfig.h"
DEFINE = re.compile(r"^\s*#\s*define\s+(\S+)(?:\s+(.*?))?\s*$")


def _defines(text: str) -> set[str]:
    """Every #define of a header, indented or not, as `NAME VALUE`."""
    return {
        f"{m[1]} {m[2] or ''}".rstrip() for line in text.splitlines() if (m := DEFINE.match(line))
    }


def test_the_guests_configure_results_are_recorded() -> None:
    """Every #define of the guest CPython's pyconfig.h equals
    tests/cpython_configure.txt, so a toolchain that flips a configure result (wasi-sdk 34 flipped
    ten HAVE_* lines) fails here and its specification says why. A line holding a reserved
    embedder's name is not written in the file; the file's
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
