"""Write (or, with --check, verify) the golden outputs of the jobs, natively, under the oracle.

    uv run python tests/jobs/regen.py            # write tests/jobs/<job>.expected
    uv run python tests/jobs/regen.py --check    # exit 1 unless every .expected reproduces
    uv run python tests/jobs/regen.py --online   # allow uv to fetch the pinned oracle first
    uv run python tests/jobs/regen.py --job svg_to_png   # one job only (repeatable)

Each job runs twice, with PYTHONHASHSEED 0 and 1; the two outputs must agree, or nothing is
written. Every uv download lands under build/oracle/. A
platform-bound job (the plot) also records the platform that made it, in
tests/jobs/<job>.platform, and --check reproduces it only on that platform.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness import jobs, paths  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify instead of writing")
    ap.add_argument("--online", action="store_true", help="let uv fetch the pinned oracle")
    ap.add_argument("--job", action="append", choices=jobs.JOBS, help="only this job")
    a = ap.parse_args()
    workdir = paths.BUILD / "oracle" / "runs"
    status = 0
    for job in a.job or jobs.JOBS:
        if a.check and not jobs.reproducible_here(job):
            print(f"skipped {job}: recorded on another platform than {jobs.this_platform()}")
            continue
        first = jobs.run_native(job, 0, workdir, offline=not a.online)
        second = jobs.run_native(job, 1, workdir, offline=not a.online)
        why = jobs.compare(first, second)
        if why:
            print(f"ERROR {job}: two hash seeds disagree: {why}")
            status = 1
            continue
        target = jobs.expected_path(job)
        if a.check:
            why = jobs.compare(target.read_bytes(), first) if target.is_file() else "missing"
            print(f"{'ok' if why is None else 'ERROR'} {job}: {why or 'reproduces'}")
            status |= why is not None
        else:
            target.write_bytes(first)
            print(f"wrote {target.relative_to(paths.REPO)} ({len(first)} bytes)")
            if job in jobs.PLATFORM_BOUND:
                jobs.platform_path(job).write_text(jobs.this_platform() + "\n")
                print(f"wrote {jobs.platform_path(job).relative_to(paths.REPO)}")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
