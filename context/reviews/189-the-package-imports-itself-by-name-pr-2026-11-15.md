# Review of 189 — The package imports itself by name

- **Date:** 2026-11-15
- **Reviewer:** an agent (Claude), a fresh sub-agent of https://claude.ai/code/session_01BD1pVHiZoxnwRv6JCqJKeC; not the author
- **Reviewed:** pull request #109, `338ed06d..57901867`, with the specification and its pre-build review, in a detached worktree of `57901867`
- **Run:** 43658743724 on `57901867`, finished (READ). `plan`, `build` (set reused), `verify`, `quick`, all 13 Linux, 11 Windows and 14 macOS `judge` legs and `gather` are green. `gather`: "1120/2361 pass · 37 gap · 6 blocked · 0 fail", no `GROWTH` line. `review` and `ci-status` are red only for want of this file.
- **Box:** 45 minutes (structural), besides the run's wait.
- **Re-ran** (EXECUTED; plants in `git archive` copies of dev and the branch, never in the worktree):
  - `ruff check src tests`, `ruff format --check src tests`: clean. `uv run mypy`: no issues in 32 files. `typecheck.py`: both passes clean.
  - `tests/lint` with `tests/checks/test_rules.py`: 157 passed, 5 skipped. `tests/unit -n 4`: 3,632 passed, 104 skipped, 1 failed, the known root-only `test_the_walk_judges_links`.
  - `api.py --check`: exit 0. `public_api.txt`, `known_gaps.toml`, `tests/upstream/`, `recipes/`, `scripts/`, `release/`, `.github/`: unchanged.
  - My comparison of all 52 `.py` files under `src/` and `recipes/`: with each relative import read as its absolute twin, `ast.dump` and the sequence of imports are equal in every file. Every non-blank changed line lies inside an import statement. 172 relative imports in 28 modules on dev, 0 under `src/` on the branch.
  - `import wasi_python`: the same 24 package modules and 130 new `sys.modules` entries, in order, on both trees, `wasmtime` not loaded. Every module's globals are equal (one digest); both star imports give exactly their `__all__`.
  - TID252: a relative import planted in `src/` or `tests/` is refused at its line; one in `recipes/guest/host/` is excepted. Dev's config does not refuse it.
  - The judge on plants: module-level `from wasi_python import runner` in `_limits.py` gives `_limits.py:240 (_limits imports runner, not before it in ORDER)`; a late `import wasi_python.runner` gives `_limits.py:243 (… import a sibling by \`from\`)`; a late `from wasi_python._call import _run_checked` in `_sessions.py` gives "not in LATE" and "by from: function". Dev's file passes all three. The branch's file on dev's tree: 5 passed. Line-free, `_imports` is 172 entries (`1a63838b8eb3dabd`) and `_from_imports` 146 (`374106e8ac35f120`) on both trees; dev's file reads 0 on the branch.

Labels: EXECUTED, ran it; READ, read it; INFERRED, reasoned.

## Acceptance criteria against evidence

1. No relative import — met (EXECUTED).
2. The judge — met; plants red, digests equal and as the notes give them (EXECUTED).
3. A mechanical change — met (EXECUTED).
4. Import cost — met (EXECUTED). The notes' 127 entries against my 130 is a difference of baseline, equal across trees (INFERRED).
5. Sizes — met: `_call.py` 1,411, the largest (EXECUTED).
6. Nothing public — met (EXECUTED).
7. The guest package — met (EXECUTED).
8. Types and words — met (EXECUTED).
9. The run — met (READ); its id is not yet in the notes (finding 1).

## Findings, most severe first

No High and no Medium.

1. **Low: one box of the self-check is unticked, and the notes wait on the run** (pull request #109's description; the specification's landing notes, "The run"). "The Windows legs … were read" is empty because the run had not finished. It has now finished, with all 11 windows-2025 legs green (READ). Fix: tick the box and name run 43658743724. In the landing notes, replace "Waits on the pull request's run." with "Run 43658743724 on `57901867`: every leg green on Linux (13), Windows (11) and macOS (14), `gather` 1120/2361 pass, 0 fail, no `GROWTH` line; `review` and `ci-status` waited on the review file."
2. **Low: the specification's news-file paragraph still says `units = 0`** (`context/specifications/189-the-package-imports-itself-by-name.md:125`). The built news file says `units = 1`, which is right. Decision 5 adds one unit test, and `sameness.explain` needs the suite to grow by exactly the claimed count (READ, `tests/harness/sameness.py:415-438`). Failure: none in the run; the specification misdescribes the claim. Fix text: replace "`units = 0`" with "`units = 1`, the new check of Decision 5".

## Constitution checks

- §4.10 and §4.13 hold: the claims I re-ran agree.
- §5.6: the structural pre-build review is cited; its Lows 1 to 6 are applied and disposed (READ).
- Judge: nothing is loosened. `pyproject.toml` adds a rule. `test_runner_package.py` keeps every table, reads a superset and adds a check, both seen red where dev's file is blind. The re-export stand-in keeps its one finding; the `test_wasmtime_ffi.py` comment stays true (INFERRED).
- Checklist 4: `[claim.judge]` names all four judge files with reasons. `units = 1` is right. No `GROWTH` row to claim; `LONG_FUNCTIONS` untouched (READ).
- 4a, structure: no row scores down. No concern, flag, mutable, seam, platform branch, private-API use or function past 80 lines; the Kind line carries **structural** by its subject (R3). Dev → branch (EXECUTED): `src/` 17,387 → 17,424 lines; functions over 80, 6 → 6; mutables 0 → 0; private-API lines 90 → 90; platform reads 3 → 3; `Any` 488 → 488; `type: ignore` 4 → 4. R3 holds Strong: the same edges and late seams, each named whole. R7 holds Adequate: `_call.py` at 94.1% of its ceiling, up 0.6. The other rows are unchanged.
- 4b: nothing under `.github/` or `release/` changes (EXECUTED).
- Decision 3 holds: the guest package ships as `host` (READ, `70_zip.sh:303-306`) and loads in the unit checks as `_guest_host_{n}`; only a relative import resolves under both (INFERRED).
- §7: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Fixed. The description's Windows box is ticked and names run 43658743724; the landing notes' run line is replaced with the fix text (c465241d).
2. Fixed. The specification says `units = 1`, the new check of Decision 5 (c465241d).

## Verdict

Lands at `57901867`: the change is only the imports, the same modules load and bind the same names, the judge is strengthened and nothing is loosened, and run 43658743724 is green except `review` and `ci-status`, which wait on this file; the two Lows are write-ins.
