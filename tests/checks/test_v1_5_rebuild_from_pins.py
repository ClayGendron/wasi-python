"""v1.5: the whole thing rebuilds from pinned sources, with zero patches to any upstream tree."""

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


@pytest.mark.parametrize("component", ["cpython", "numpy", "pandas", "zlib"])
def test_source_tree_matches_its_tarball(component) -> None:
    needs.need(f"source tree {component}")
    tarball, tree = pins.source_pair(component)
    pinned = paths.read_pin_list()[tarball.name]
    actual = paths.sha256_file(tarball)
    assert actual == pinned, scan.report([f"{tarball.name}: sha256 {actual}, pinned {pinned}"])
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
        [] if good else ["no release workflow with workflow_dispatch runs the zero-patch check"]
    )
    assert not missing, scan.report(missing)


def test_stdlib_zip_names_no_build_host(artifacts) -> None:
    """_sysconfigdata and numpy's __config__ say nothing about the machine that built them, so the
    zip, and the snapshot that holds its offsets, are the same bytes from any host (spec 012,
    Decision 5)."""
    needs.need("stdlib zip")
    errors = rules.host_fact_errors(artifacts.path("python-stdlib.zip"), str(paths.REPO))
    assert not errors, scan.report(errors)


def test_release_workflow_rebuilds_on_a_second_host() -> None:
    """An arm64 Linux runner rebuilds the set beside the build, and nothing is signed or
    published until its SHA256SUMS equals the set's (spec 012, Decisions 7 and 8)."""
    workflow = paths.REPO / ".github" / "workflows" / "release.yml"
    errors = scan.rebuild_gate_errors(workflow.read_text())
    assert not errors, scan.report(errors)
