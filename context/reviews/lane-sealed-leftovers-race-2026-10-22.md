# Review of the lane's judge change: a folder removed during the sealed-leftovers scan

- **Date:** 2026-10-22
- **Reviewer:** a fresh agent (Claude Opus 5.5); not the author (the lane)
- **Reviewed:** 618f891e on origin/wave/12 (parent 855c7530): `tests/harness/litter.py` (+10 -1), `tests/unit/test_host_litter.py` (+12)
- **Run:** none dispatched. The caller limited this review to local single node ids. The release acceptance that found the race is the lane's to re-run.
- **Time box:** 25 minutes (a judge-only change)
- **Re-ran (on HEAD 618f891e, no `build/lane.lock`):**
  - `uv run pytest -q -p no:cacheprovider tests/unit/test_host_litter.py` → 24 passed, exit 0
  - `tests/unit/test_several_cores.py::test_a_parallel_run_judges_as_a_serial_run[node ids]`, `[whole]` and `[-k]`, each alone → 1 passed each, exit 0
  - the parent's `sealed_leftovers`, run from a copy in the scratchpad with the row's fake walk → raises `FileNotFoundError`
  - `ruff check` and `ruff format --check` on both files → clean

## Acceptance criteria against evidence
1. A folder that vanishes between the walk listing it and the `lstat` is not an error. Met (EXECUTED): the new row passes, and the parallel-run test's three node ids pass alone.
2. The new row fails on the old code. Met (EXECUTED): the parent's scan, given the same fake walk, raises `FileNotFoundError`.
3. The fix cannot hide a real sealed leftover. Met (READ/INFERRED). A folder that is gone is not left over. A sealed folder that still has entries cannot be emptied, so it cannot vanish unless something unseals it first. And the scan only writes a warning to stderr (`plugin.py:218-225`). It never fails a check or changes a verdict.
4. The fix is narrow. Met (READ): only `FileNotFoundError` is caught. `PermissionError`, `NotADirectoryError` and other errors still raise.

## Findings, most severe first
1. **Low: the row tests only the vanished folder** (`tests/unit/test_host_litter.py:167-176`). If a later edit caught too much (for example a bare `except` that returned `[]` for the whole scan), this row would still pass. `test_sealed_leftovers_are_named` partly covers this end to end. Fix text: have the fake walk yield both the vanished folder and a real sealed folder, then assert that the result is exactly the real one, e.g. `sealed = tmp_path / "sealed"; sealed.mkdir(); sealed.chmod(0o555)`, walk yields `[(str(gone), [], []), (str(sealed), [], [])]`, assert `== [str(sealed)]`, then `chmod(0o755)` in a `finally`. Put it under the `BINDS` skip, as the sibling row is.
2. **Note: no other unguarded stat on this path.** `root.is_dir()` returns False and does not raise. `os.walk` with the default `onerror=None` skips a folder whose listing fails, and it catches the errors from `entry.is_dir()` and `entry.is_symlink()` itself. The one other `lstat` reached from configure, `paths._make_guest_tmp` (`paths.py:69`), reads the judge's own guest root, and no worker removes that. `_chmod` already catches `OSError`. `litter_in` and `inventory` walk a run's own folders, which no other worker touches.
3. **Note: this is a judge change.** The judge's hash moves, so the lane accepts with `--accept-judge`, and the review sees the judge-hash line (AGENTS.md rule 4). The commit message says "A judge change". It gives a reason and does not weaken a check, a golden output or a gap.
4. **Note: code speaks for itself.** The docstrings of `_writable` and of the row give the reason in words ("another worker's guest removed after the walk listed it"). Neither names a spec, review or `context/` path.
5. **Note: structure.** No module-level mutable, no new platform branch (the `win32` guard was already there), no `src/` change. The new function is six lines, and `litter.py` is 231 lines. Not structural.

## Constitution checks
- §4 constraints: none touched beyond the judge. Rule 3 (check first): the row was written and seen failing on the old code; this review confirmed that. Rule 4 (never weaken the judge): holds; the scan is advisory and the change is narrow. Rule 8 (the implementer never reviews): this reviewer wrote none of it.
- §7 never-do list: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)
1. Low 1: (the lane) fixed in the commit after 618f891e: the row's fake walk yields the vanished folder and a really sealed one, and asserts the scan names exactly the sealed one; seen failing on the old code (FileNotFoundError), 24 passed on the fix.

## Verdict
Lands. The fix is correct, narrow and cannot change a verdict; Low 1 is an optional write-in that makes the row stronger.
