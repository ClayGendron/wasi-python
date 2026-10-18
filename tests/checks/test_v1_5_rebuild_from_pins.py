"""v1.5: the whole thing rebuilds from pinned sources; each upstream tree is its tarball plus
exactly the recorded patches (constitution §4.1, spec 020)."""

from __future__ import annotations

import re

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
    errors += scan.fp_pragma_hits(trees)
    read.append(f"source trees and meson folders grepped for pragmas: {len(trees)}")
    for clang in sorted((paths.BUILD / "tools").glob("wasi-sdk-*/bin/clang")):
        errors += scan.fp_compiler_errors(clang.parent)
        read.append(f"{clang.parent.parent.name}: clang and clang++ probed with -###")
    print("\n".join(read))
    assert not errors, scan.report(errors) + "\nread:\n" + "\n".join(read)
