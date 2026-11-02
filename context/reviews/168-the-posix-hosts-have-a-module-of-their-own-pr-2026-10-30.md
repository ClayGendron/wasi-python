# Review of 168 — The POSIX hosts have a module of their own

- **Date:** 2026-10-30
- **Reviewer:** an agent (Claude Opus 5.5), a fresh sub-agent of the orchestrating session; not the author
- **Reviewed:** `0070b04e..2c462a94` on `spec/168-the-posix-hosts-have-a-module-of-their-own` (`91b9ab19` the build, `2c462a94` the specification's notes), with the specification and its pre-build review
- **Run:** 41160973120 on `2c462a94`, read by the orchestrator after this review: every judge leg green on Linux, Windows (7) and macOS (8), the 34 shard ratchets lost 0 and grew 0, no `GROWTH` line, the gather green; `ci-status` red on the review refusal alone. This review read no run and dispatched none.
- **Re-ran:** on `2c462a94`, with the main tree's artifact set read-only: `uv run pytest -m "not slow" -n 3 -q tests/unit tests/lint tests/checks/test_rules.py` → 3486 passed, 14 skipped, exit 0; criterion 8's seven unit files and `tests/unit/test_typecheck.py` → 284 passed, 6 skipped, exit 0 (the author's 282 plus the two type-check rows); `ruff check src tests` → "All checks passed!"; `ruff format --check src tests` → 196 files already formatted; `tests/harness/typecheck.py` → "both passes are clean"; `tests/harness/api.py --check` → exit 0. In a scratch copy of the head: `test_only_the_platform_modules_import_its_halves` with `from . import _platform, _platform_posix` planted at `_home.py:14` → 1 failed, "_home.py:14: imports _platform_posix past the platform module"; the same fault with the `_platform_posix` row deleted → 1 passed.
- **Time box:** 45 minutes (structural); kept.

Labels: EXECUTED means I ran it; READ means I read the file or diff cited; INFERRED means my reasoning.

**The move, checked by my own script (EXECUTED).** An `ast.dump` of every top-level name of the base's `_platform.py` against where it now lives, `_platform_common._flags` read back as `_flags`: 55 names on the base; 40 in `_platform_posix.py`, 14 still in `_platform.py`, 1 (`_flags`) in `_platform_common.py`; differ: none; gone: none; new: `_open_flags` only. No name already in `_platform_common.py` changed. A second, independent check, a sorted line-multiset diff of the base file against the two new files, shows only the five `_flags` call sites, ruff's re-wrap of `_DIR` and `_DIR_OPEN`, the imports, the docstrings, `_open_flags` and one new comment above `_TRAP_HANDLERS_REPLACED` (its old comment moved with `_TRAP_SIGNALS`). Every comment of a moved name moved with it.

**No stale reference (EXECUTED).** No file under `src/`, `tests/` or `scripts/` reads a moved name as `_platform.<name>`, by string or by `setattr`. The `from ._platform import` lines elsewhere (`_call`, `_sessions`, `_engines`, `_home`, `_places`) name only kept names. `_platform_posix.py` reads none of `_platform.py`'s names (ruff F821 and both mypy passes clean).

## Acceptance criteria against evidence

1. Sizes — met: 213, 1,166, 366, 502 (EXECUTED, `wc -l`); the ceiling check green in the fast tier.
2. The direction — met: `ORDER` has `_platform_posix` between `_platform_windows` and `_platform`; the new module imports `_platform_common` and `_process` at top level and `_wasmtime_ffi` late, as `LATE_ANYWHERE` allows; `LATE` unchanged (READ, EXECUTED).
3. The choice — met: `git diff -U0` shows no line of `_select`; the three platform reads are its three lines (EXECUTED); the halves row seen failing and passing as above (EXECUTED).
4. A move — met (EXECUTED, above).
5. Types — met: both passes clean; `type: ignore` 3 (EXECUTED); `pyproject.toml` and `tests/harness/typecheck.py` unchanged (READ).
6. No seam, no long function — met: no `monkeypatch.setattr(_platform…, "_…")` in `tests/`; the longest function of each platform module is `_remove_at` 76, `_remove_by_path` 76, `_walk` 74, `tell_interpreter` 10 (EXECUTED); `SEAM_ALLOWED`, `LONG_FUNCTIONS` untouched (READ); module-level mutable grep: none in the platform modules (EXECUTED).
7. Nothing public — met: `api.py --check` exit 0, `tests/public_api.txt` unchanged (EXECUTED).
8. The renamed tests — met: the four unit files change only the module a moved name is read from; no expectation changed (READ); 284 passed, 6 skipped (EXECUTED).
9. Every host — pending: the pull request's run, macOS included (`_Darwin` runs only there).

Judge edits (READ): `ORDER` (one entry), `RUNNER_FILES` (one entry), `PLATFORM_HALVES` (one row, one importer added), two rewritten comments and one docstring in `tests/checks/test_rules.py`, and the four unit files' imports and attribute reads. Each is in the list Decision 6 allows and has its reason under `[claim.judge]`. No check is weakened: the halves rule now holds one more module, and the planted fault shows the row is what catches it.

News file (READ, EXECUTED): `### For contributors`, a heading `HEADINGS` allows; one entry, its lead bold, linked last to the site; no specification or private module named; `harness.news.load` parses it; every claim list empty, `units = 0`. No package row.

Code speaks for itself (EXECUTED): no specification number, finding ID or `context/` path in the changed code, comments or docstrings.

Self-check: not read; this review made no `gh` call. The orchestrator reads the description's four boxes with the run.

## Structure

- R1 Contract: unchanged; `api.py --check` exit 0.
- R2 Safety: unchanged; the same code, byte for byte but the `_flags` reads.
- R3 Layering: Strong; one more module, edges down only, the host modules never import each other, private API still only in `_wasmtime_ffi.py`, `_places.py` and `_tool_host.py` as before.
- R4 Process state: unchanged; no mutable or lock.
- R5 Portability: Strong; each family in its module, chosen once in `_select`.
- R6 Testability: unchanged; tests read the classes where they live, patch only `PLATFORM`'s attributes.
- R7 Evolvability: toward Strong; `_platform.py` 1,351 → 213, the largest platform module 1,166 (78% of the ceiling).
- R8 Operability: unchanged; no message changes.

4a: the diff adds no concern, flag, mutable, seam, platform branch, private-API use or long function; Kind carries **structural**. 4b: nothing under `.github/` or `release/` changes.

## Findings, most severe first

1. **Low: the rubric still counts two modules below the platform module** (`context/reviews/README.md:78`) — R5 reads "`_platform.py` and the two below it, no other", and there are now three. Failure: the next structural review scores `_platform_posix.py` as a platform branch outside the platform modules. Fix text: "(`_platform.py` and the three below it, no other)". Context only; Scope moved it to the disposition, so it may ride with this review's commit.

## Constitution checks

- §4.1, §4.2: no upstream source, no download touched.
- §4.13: ruff, format, both type-check passes and the fast tier green (EXECUTED).
- §5.6: structural pre-build review exists and is cited in Status; its five Lows are taken (READ).
- §7: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Low 1 — context only; needs no round.

## Verdict

Lands on 2c462a94 once the run is green on Linux, Windows and macOS with no `GROWTH` line.

Rebased by the orchestrator onto `dev` `a1acec5c` (159's merge), so the plan that writes the `review` check's output runs: no conflict, and `git range-diff` shows every commit identical; the code this review read at `2c462a94` is `6b192a89` after the rebase.
