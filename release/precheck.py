"""The checks a pull request's run makes that need no artifact set, run here before a push.

    uv run python release/precheck.py              # quick's steps, then the plan's refusals
    uv run python release/precheck.py --plan-only  # the plan's refusals alone, in a second
    uv run python release/precheck.py --install    # run it before every git push, from now on

It runs the `run:` script of every step of the release workflow's quick job, read from the
workflow itself, in the runner's shell and with the workflow's and the job's env:, so this and CI
cannot drift apart. Then it reads this branch as the decision job
would read it as a pull request into dev (against the merge base with origin/dev) and prints what
ci-status and the review job would refuse, through the decision job's own reading of a run. A
refusal that is a mistake (no news file, a review signed by its author) fails here. A review
that only waits on its reviewer (none yet, one a later code commit left behind, a verdict that
does not land yet) is printed and does not fail: in CI it keeps the two checks red without
failing the run.

It reads no pull request description, which only GitHub has, so a skip word or an author named
there alone is not seen here. It judges the commits at HEAD and quick's steps on the working
tree; uncommitted changes are named first. Exit 0 when nothing failed.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKFLOW = REPO / ".github" / "workflows" / "release.yml"
HOOK = "#!/bin/sh\n# Installed by release/precheck.py --install: the checks CI makes first.\n"
HOOK_BODY = 'exec uv run python release/precheck.py "$@" < /dev/null\n'
BASE = "origin/dev"


def _module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _scan():
    sys.path.insert(0, str(REPO / "tests"))
    from harness import scan

    return scan


def quick_steps(text: str) -> list[tuple[str, str]]:
    """The quick job's steps that run a script, each as its name and its script, in order."""
    scan = _scan()
    jobs = scan.workflow_jobs(scan.without_comments(text))
    out = []
    for step in scan.workflow_steps(jobs.get("quick", [])):
        f = scan.step_fields(step)
        if isinstance(f.get("run"), str):
            out.append((str(f.get("name") or f["run"].splitlines()[0]), f["run"]))
    if not out:
        raise SystemExit("the release workflow's quick job has no step with a run: script")
    return out


def _plain(value: str) -> str | None:
    """A YAML scalar's text, unquoted; None for an expression, which only a runner can read."""
    value = value.strip()
    if "${{" in value:
        return None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def quick_env(text: str) -> dict[str, str]:
    """The workflow's top-level env: and quick's own, as quick's steps see them."""
    scan = _scan()
    body = scan.without_comments(text)
    out: dict[str, str] = {}
    inside = False
    for line in body.splitlines():
        if line.startswith("env:"):
            inside = True
            continue
        if inside and line and not line.startswith(" "):
            break
        if inside and (m := re.fullmatch(r"  ([A-Za-z0-9_]+):\s*(.*)", line)):
            if (v := _plain(m[2])) is not None:
                out[m[1]] = v
    for key, value in scan._job_map(scan.workflow_jobs(body).get("quick", []), "env").items():
        if (v := _plain(value)) is not None:
            out[key] = v
    return out


# The shell GitHub's runner uses for a run: step on Linux.
SHELL = ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c"]


def run_quick() -> list[str]:
    """Each of quick's scripts in the runner's shell at the repository's root, with quick's env;
    the names of those that failed."""
    failed = []
    (REPO / "build" / "ci").mkdir(parents=True, exist_ok=True)
    text = WORKFLOW.read_text(encoding="utf-8")
    env = {**os.environ, **quick_env(text)}
    for name, script in quick_steps(text):
        start = time.monotonic()
        print(f"precheck: {name} ...", flush=True)
        r = subprocess.run([*SHELL, script], cwd=REPO, env=env)
        took = time.monotonic() - start
        print(f"precheck: {name}: {'ok' if r.returncode == 0 else 'FAILED'} ({took:.0f} s)")
        if r.returncode != 0:
            failed.append(name)
    return failed


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO), *args], check=True, capture_output=True, text=True
    ).stdout


def plan_refusals(base_ref: str = BASE) -> tuple[list[str], list[str]] | None:
    """What ci-status would refuse of this branch as a pull request into dev, split into the
    mistakes and the review's waits; None when the base cannot be read. The decision job's own
    reading of a run does the work, given a pull request's variables and no token, so it reads
    git alone and re-uses no run."""
    ci_plan = _module("ci_plan", REPO / "release" / "ci_plan.py")
    try:
        base = git("rev-parse", "--verify", f"{base_ref}^{{commit}}").strip()
    except subprocess.CalledProcessError:
        return None
    environ = {
        "GITHUB_EVENT_NAME": "pull_request",
        "GITHUB_REF": "refs/pull/0/merge",
        "GITHUB_BASE_REF": "dev",
        "PLAN_HEAD": git("rev-parse", "HEAD").strip(),
        "PLAN_BASE": base,
        "PLAN_HEAD_REF": git("rev-parse", "--abbrev-ref", "HEAD").strip(),
        "PLAN_ACTION": "synchronize",
    }
    event, changed, moved, pr, reused, preparation, refused_preparation = ci_plan.from_runner(
        environ
    )
    d = ci_plan.decide(changed, event, moved, reused, preparation, refused_preparation)
    refused = ci_plan.refusals(d, event, changed, pr)
    waits = [r for r in refused if ci_plan.only_waiting([r])]
    return [r for r in refused if r not in waits], waits


def report_plan() -> bool:
    """Print the plan's refusals; whether one of them is a mistake that would fail the run."""
    got = plan_refusals()
    if got is None:
        print(
            f"precheck: the plan: {BASE} cannot be read, so it was not run (git fetch origin dev)"
        )
        return False
    mistakes, waits = got
    for r in waits:
        print(f"precheck: the plan: waits, red and not failed in CI: {r}")
    for r in mistakes:
        print(f"precheck: the plan: REFUSED, the run would fail: {r}")
    if not mistakes and not waits:
        print("precheck: the plan: refuses nothing")
    return bool(mistakes)


def install() -> int:
    """Write the pre-push hook, unless a hook of another making is there."""
    hooks = Path(git("rev-parse", "--git-path", "hooks").strip())
    hooks = hooks if hooks.is_absolute() else REPO / hooks
    hook = hooks / "pre-push"
    if hook.exists() and not hook.read_text(encoding="utf-8").startswith(HOOK):
        print(f"precheck: {hook} is someone else's hook; add this line to it: {HOOK_BODY.strip()}")
        return 1
    hooks.mkdir(parents=True, exist_ok=True)
    hook.write_text(HOOK + HOOK_BODY, encoding="utf-8")
    hook.chmod(0o755)
    print(f"precheck: installed {hook}; `git push --no-verify` skips it once")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="precheck.py")
    ap.add_argument("--plan-only", action="store_true", help="the plan's refusals alone")
    ap.add_argument("--install", action="store_true", help="install the pre-push hook")
    ap.add_argument("hook_args", nargs="*", help=argparse.SUPPRESS)  # git's remote and its URL
    a = ap.parse_args(argv)
    if a.install:
        return install()
    dirty = git("status", "--porcelain").splitlines()
    if dirty:
        print(
            f"precheck: {len(dirty)} uncommitted paths; quick's steps read them, the plan does not"
        )
    failed = [] if a.plan_only else run_quick()
    if report_plan():
        failed.append("the plan")
    if failed:
        print("precheck: FAILED: " + ", ".join(failed))
        return 1
    print("precheck: passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
