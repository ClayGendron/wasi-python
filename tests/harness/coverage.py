"""The runner's line coverage, for the README's Codecov badge.

    uv run python tests/harness/coverage.py --measure   # the fast tier under coverage.py, locally

The release workflow measures it in legs that run anyway: on a run with the merge-grade set, each
Linux leg the plan names (`coverage` in release/ci_plan.py, every own shard on Linux) runs its
shard under coverage.py, measuring `src/wasi_python`, and sends its Cobertura XML report to
Codecov, which merges a commit's reports into the README's badge, so nothing in the tree holds
the number. `--measure` is the same measurement over
the whole fast tier on this machine: it runs `uv run pytest -m "not slow"` serially under
coverage.py and writes the run's log, a JSON report and the XML report under build/coverage/. A run
whose summary names a failed test or an error exits non-zero and its numbers are not reported.
The ratchet's verdict is not read: a lost or absent accepted check is the acceptance's business,
and it changes no line of the runner that ran. `--check` holds the README's one badge to Codecov's
for this repository.

Self-contained: it imports no other harness module, so it runs as a script.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
README = REPO / "README.md"
SOURCE = "src/wasi_python"
WORK = REPO / "build" / "coverage"
CODECOV = "https://codecov.io/gh/ClayGendron/wasi-python"
BADGE_TAG = f'<a href="{CODECOV}"><img alt="Coverage" src="{CODECOV}/graph/badge.svg"></a>'
BADGE = re.compile(r"https://codecov\.io/gh/[^\"' )]+/graph/badge\.svg")
SUMMARY = re.compile(r"^(?:=+ )?((?:\d+ \w+(?:, )?)+) in [\d.]+s(?: .*)?$")


def summary_names_failures(summary: str) -> bool:
    return bool(re.search(r"\b\d+ (?:failed|errors?)\b", summary))


def summary_of(log: str) -> str:
    """The pytest summary line's counts, read from the end of a log; empty when there is none."""
    for line in reversed(log.splitlines()):
        m = SUMMARY.match(line.strip())
        if m:
            return m[1]
    return ""


def badge_errors(readme: str) -> list[str]:
    """Why the README's coverage badge is not this repository's Codecov badge; empty when it is."""
    found = BADGE.findall(readme)
    if len(found) != 1:
        return [f"README.md: {len(found)} Codecov badges, not one: {BADGE_TAG}"]
    if BADGE_TAG not in readme:
        return [f"README.md: the coverage badge is not {BADGE_TAG}"]
    return []


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=REPO, text=True, capture_output=True, check=False)


def measure() -> tuple[str, dict[str, object]]:
    """Run the fast tier under coverage.py; return its summary and the report's totals."""
    WORK.mkdir(parents=True, exist_ok=True)
    data = f"--data-file={WORK / '.coverage'}"
    log = WORK / "pytest.log"
    env = dict(os.environ)
    if sys.version_info >= (3, 12):
        env["COVERAGE_CORE"] = "sysmon"  # the low-overhead tracer; the default is ten times slower
    with log.open("w") as out:
        run = subprocess.run(
            ["uv", "run", "coverage", "run", data, f"--source={SOURCE}"]
            + ["-m", "pytest", "-m", "not slow", "-p", "no:cacheprovider", "-q"],
            cwd=REPO,
            stdout=out,
            stderr=subprocess.STDOUT,
            env=env,
            check=False,
        )
    summary = summary_of(log.read_text())
    if not summary:
        raise SystemExit(f"no pytest summary line in {log}; exit {run.returncode}")
    for report in ("json", "xml"):
        r = _run(["uv", "run", "coverage", report, data, "-o", str(WORK / f"coverage.{report}")])
        if r.returncode:
            raise SystemExit(r.stderr.strip() or r.stdout.strip())
    totals = json.loads((WORK / "coverage.json").read_text())["totals"]
    return summary, totals


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--measure", action="store_true", help="run the fast tier under coverage.py")
    g.add_argument("--check", action="store_true", help="hold the README's badge to Codecov's")
    a = p.parse_args(argv)
    if a.check:
        errors = badge_errors(README.read_text(encoding="utf-8"))
        for e in errors:
            print(e)
        return 1 if errors else 0
    summary, totals = measure()
    if summary_names_failures(summary):
        print(f"not green ({summary}); see {WORK / 'pytest.log'}")
        return 1
    percent, ran, of = totals["percent_covered"], totals["covered_lines"], totals["num_statements"]
    print(f"coverage: {percent:.1f}% ({ran} of {of} statements), {summary}")
    print(f"reports in {WORK.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
