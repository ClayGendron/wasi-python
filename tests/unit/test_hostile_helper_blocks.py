"""The hostile-guest helper blocks, not fails, without an artifact set (spec 065, Decision 22 and
criterion 14): the two checks that read MANIFEST before starting a guest are `blocked` on the need
`manifest` when WASI_PYTHON_ARTIFACTS names an empty folder (`artifact dir` is then met:
`paths.artifact_dir()` returns the folder whenever the variable is set)."""

from __future__ import annotations

import json
import os
import subprocess
import sys

from harness import paths

FILE = "tests/checks/test_v1_2_hostile_guest.py"
CHECKS = ("test_matplotlib_data_is_granted_read_only", "test_usr_local_lib_holds_only_the_zip")


def test_the_two_checks_are_blocked_on_manifest_without_an_artifact_set(work) -> None:
    empty = work / "empty"
    empty.mkdir()
    record = work / "latest.json"
    env = {**os.environ, "WASI_PYTHON_ARTIFACTS": str(empty)}
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "no:cacheprovider",
            "-q",
            "-p",
            "no:xdist",
            *[f"{FILE}::{c}" for c in CHECKS],
            "--progress-latest",
            str(record),
        ],
        cwd=paths.REPO,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    checks = json.loads(record.read_text())["checks"]
    got = {node.split("::", 1)[1]: (c["status"], c.get("need")) for node, c in checks.items()}
    assert len(got) == 4, (r.stdout[-2000:], got)
    assert set(got.values()) == {("blocked", "manifest")}, got
