"""The local precheck: it runs the quick job's own scripts and installs its hook carefully."""

from __future__ import annotations

import importlib.util
import subprocess
import sys

from harness import paths, scan

SPEC = importlib.util.spec_from_file_location("precheck", paths.REPO / "release" / "precheck.py")
precheck = importlib.util.module_from_spec(SPEC)
sys.modules["precheck"] = precheck
SPEC.loader.exec_module(precheck)

WORKFLOW = (paths.REPO / ".github" / "workflows" / "release.yml").read_text()


def test_the_precheck_runs_every_scripted_step_of_quick_in_order() -> None:
    jobs = scan.workflow_jobs(scan.without_comments(WORKFLOW))
    want = [
        scan.step_fields(s)["run"]
        for s in scan.workflow_steps(jobs["quick"])
        if isinstance(scan.step_fields(s).get("run"), str)
    ]
    got = precheck.quick_steps(WORKFLOW)
    assert [script for _, script in got] == want
    assert any("ruff check" in s for s in want) and any("tests/lint" in s for s in want)


def _repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    return tmp_path


def test_the_hook_runs_the_precheck_and_leaves_anothers_hook_alone(tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    monkeypatch.setattr(precheck, "REPO", repo)
    assert precheck.install() == 0
    hook = repo / ".git" / "hooks" / "pre-push"
    assert "release/precheck.py" in hook.read_text() and hook.stat().st_mode & 0o100
    assert precheck.install() == 0  # its own hook is rewritten
    hook.write_text("#!/bin/sh\nmake check\n")
    assert precheck.install() == 1
    assert hook.read_text() == "#!/bin/sh\nmake check\n"
