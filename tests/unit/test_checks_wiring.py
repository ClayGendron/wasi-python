"""The real v1.1 check file, run in a subprocess against synthetic artifact sets (criterion 7):
the checks are wired to their rules, and a missing file blocks or fails the right checks."""

from __future__ import annotations

import json

import pytest
from test_artifact_rules import good_set

from harness import paths

CHECKS = paths.REPO / "tests" / "checks" / "test_v1_1_artifact_set.py"
PREFIX = "tests/checks/test_v1_1_artifact_set.py::"


@pytest.fixture
def run_checks(pytester: pytest.Pytester, work, monkeypatch):
    def run(artifact_dir):
        monkeypatch.setenv(paths.ARTIFACTS_ENV, str(artifact_dir))
        latest = work / "latest.json"
        (work / "gaps.toml").write_text("")
        pytester.runpytest_subprocess(
            str(CHECKS),
            "-p",
            "no:cacheprovider",
            "--progress-dir",
            str(work / "progress"),
            "--progress-latest",
            str(latest),
            "--known-gaps",
            str(work / "gaps.toml"),
        )
        checks = json.loads(latest.read_text())["checks"]
        return {k.removeprefix(PREFIX): v for k, v in checks.items()}

    return run


def test_a_good_set_passes_the_rules_it_owns(run_checks, work) -> None:
    checks = run_checks(good_set(work / "good"))
    passing = {
        "test_artifact_set_is_complete",
        "test_sha256sums_match_the_files",
        "test_no_compiled_module_in_the_set",
        "test_binary_is_a_core_wasm_module[plain]",
        "test_binary_is_a_core_wasm_module[snapshot]",
        "test_imports_are_wasi_and_the_door_only[plain]",
        "test_imports_are_wasi_and_the_door_only[snapshot]",
        "test_plain_reactor_exports",
        "test_snapshot_exports",
        "test_manifest_is_well_formed",
        "test_stdlib_zip_is_bytecode_only_and_deflated",
    }
    assert {k for k, v in checks.items() if v["status"] == "pass"} >= passing
    assert checks["test_binary_is_a_core_wasm_module[plain]"]["metrics"]["bytes"] > 0
    # The synthetic set's pins and recipes are not this repository's, so these two must fail.
    assert checks["test_manifest_pins_match_the_pin_list"]["status"] == "fail"
    assert "stale artifact" in checks["test_manifest_recipes_match_the_tree"]["reason"]
    wheel_check = checks["test_wheel_carries_the_artifact_set"]
    if any(paths.DIST.glob("wasi_python-*.whl")):  # a release build has put the real wheel there
        assert wheel_check["status"] == "fail", wheel_check  # it does not carry the synthetic set
    else:
        assert wheel_check["need"] == "wheel", wheel_check


def test_a_set_without_its_snapshot_fails_completeness_and_blocks_the_snapshot(
    run_checks, work
) -> None:
    d = good_set(work / "bad")
    (d / "python-snapshot.wasm").unlink()
    checks = run_checks(d)
    assert checks["test_artifact_set_is_complete"]["status"] == "fail"
    assert "python-snapshot.wasm is missing" in checks["test_artifact_set_is_complete"]["reason"]
    assert checks["test_snapshot_exports"]["status"] == "blocked"
    assert checks["test_snapshot_exports"]["need"] == "snapshot binary"
    assert checks["test_plain_reactor_exports"]["status"] == "pass"


def test_a_set_with_a_third_import_breaks_the_wall(run_checks, work) -> None:
    from harness import wat

    d = good_set(work / "third")
    wat.build(d, "python.wasm", wat.THIRD_IMPORT)
    checks = run_checks(d)
    wall = checks["test_imports_are_wasi_and_the_door_only[plain]"]
    assert wall["status"] == "fail" and "third import env::sneak" in wall["reason"]
    assert checks["test_sha256sums_match_the_files"]["status"] == "fail"


ONE_CHECK = str(
    paths.REPO / "tests" / "checks" / "test_v1_5_rebuild_from_pins.py::test_pin_list_is_well_formed"
)


def _run_repo(pytester: pytest.Pytester, work, *args: str):
    return pytester.runpytest_subprocess(
        ONE_CHECK,
        "-p",
        "no:cacheprovider",
        "--progress-dir",
        str(work / "progress"),
        "--progress-latest",
        str(work / "latest.json"),
        *args,
    )


def test_a_plugin_from_outside_the_judge_turns_the_run_red(pytester, work, monkeypatch) -> None:
    (work / "quiet.py").write_text("def pytest_configure(config):\n    pass\n")
    monkeypatch.setenv("PYTHONPATH", str(work))
    result = _run_repo(pytester, work, "-p", "quiet")
    assert result.ret == 1
    result.stdout.fnmatch_lines(["*steered from outside the judge: plugin quiet*"])


def test_a_config_file_other_than_pyproject_turns_the_run_red(pytester, work) -> None:
    (work / "pytest.ini").write_text("[pytest]\n")
    result = _run_repo(pytester, work, "-c", str(work / "pytest.ini"), "--rootdir", str(paths.REPO))
    assert result.ret == 1
    result.stdout.fnmatch_lines(["*is configured from*pytest.ini, not pyproject.toml*"])


def test_pytest_addopts_is_announced_and_blocks_acceptance(pytester, work, monkeypatch) -> None:
    monkeypatch.setenv("PYTEST_ADDOPTS", "-q")
    result = _run_repo(pytester, work)
    assert result.ret == 0
    result.stdout.fnmatch_lines(["*JUDGE INPUTS OVERRIDDEN:*PYTEST_ADDOPTS*"])
    result = _run_repo(pytester, work, "--accept", "x")
    assert result.ret == 1
    result.stdout.fnmatch_lines(["*--accept refused*PYTEST_ADDOPTS*"])
