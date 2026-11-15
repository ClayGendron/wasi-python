# Review of 178 — The runner's entry points share one argument check and one async wrapper

- **Date:** 2026-11-14
- **Reviewer:** an agent (Claude), a fresh sub-agent of https://claude.ai/code/session_01BD1pVHiZoxnwRv6JCqJKeC; not the author
- **Reviewed:** pull request #107, `25e49df5..f63c87b6`, with the specification and its pre-build review, in a detached worktree of `f63c87b6`
- **Run:** 43652810419 on `f63c87b6`, finished (READ). `plan`, `build` (set reused), `verify`, `quick`, all 31 Linux and 11 Windows `judge` legs and `gather` are green. `gather` reports "1228/2361 pass · 132 gap · 6 blocked · 0 fail", with no `GROWTH` line. The macOS, release and publish jobs are skipped, as on any pull request into `dev`. `review` and `ci-status` are red only because this file is missing.
- **Box:** 45 minutes (structural), besides the run's wait.
- **Re-ran** (EXECUTED, no artifact set here):
  - `ruff check`, `ruff format --check`: clean.
  - `tests/lint` with `tests/checks/test_rules.py`: 157 passed, 5 skipped (this machine's needs).
  - `tests/unit -n 4`: 3,617 passed, 104 skipped, 1 failed. The failure is the known root-only `test_the_walk_judges_links`.
  - `tests/harness/api.py --check` exits 0. `public_api.txt`, `known_gaps.toml` and `tests/upstream/` are unchanged.
  - The named rows pass: 20 by node id, and `test_a_feed_used_twice_is_refused`.
  - My own `ast` comparison against `origin/dev`:
    - Seven moved names are identical.
    - `_submit`, `_checked` and `_check_tools` differ only by Decision 3's edits and their docstrings.
    - Only `_awaited` and `_serving` are new. Nothing is left behind or lost.
  - A guest-free probe of `_awaited`:
    - A call returns its value.
    - A cancelled running call sets its event and is awaited to its end.
    - A cancelled queued turn releases its claim once.
    - A refused submit releases the claim.
    - `live` ends empty each time.
  - `import wasi_python` loads neither `asyncio` nor `concurrent.futures`.
  - Mutants: a literal `Defaults(…)` in `run_async` turns `test_set_defaults_changes_what_run_reads` red. `_serving` moved after the checks turns `test_a_feed_used_twice_is_refused` red.

Labels: EXECUTED, ran it; READ, read it; INFERRED, reasoned.

## Acceptance criteria against evidence

1. Sizes — met. `runner.py` has 1,114 lines and `_entry.py` 419 (EXECUTED).
2. Order — met. `ORDER` and `LATE` are as Decision 6 says (READ), and the shape rows pass (EXECUTED). The fault seen red is READ from the landing notes.
3. A move — met. My script agrees with the notes (EXECUTED).
4. Long functions — met. `run` is 183 lines (claimed), `run_async` 197, and `Session.run_async` 77 (removed from the list). The longest function in `_entry.py` is 79 (EXECUTED, READ).
5. No seam, no state — met. The rows pass, the mutables grep finds 0 (EXECUTED), and `SEAM_ALLOWED` is untouched (READ).
6. Defaults — met. The retargeted `:396` plus the count are as strong as before, since the literal mutant fails (EXECUTED).
7. Behaviour — met by the run. The guest-backed rows passed on both systems with 0 fail (READ). A lost pass would have turned the run red (INFERRED).
8. Nothing public — met (EXECUTED).
9. Types — met. `type: ignore` stays at 4, and `Any` goes from 486 to 488 (EXECUTED).
10. Run — met (READ).

I read both coroutines against the base's `:477-543` and `:1385-1435` (READ). In both, the feed is claimed before every check, and the checks keep their order. What moves has no effect: `_Late.around` only wraps, and the session's `Event` and `self._state` (bound only in `__init__`, `runner.py:732`) are taken before its claim.

## Findings, most severe first

No High and no Medium.

1. **Low: one box of the self-check is unticked** (pull request #107's description). "The Windows legs … were read" is empty because the run had not finished. It has now finished, with all 11 windows-2025 legs green (READ). Fix: tick the box and name run 43652810419.

## Constitution checks

- §4: §4.13 and §4.10 hold, since the re-run numbers match the notes. §4.15 holds: each entry point reads the defaults once and passes them down. The guest, the artifact set and the recipe are untouched.
- §5.6: it was reviewed before it was built, and that review's Lows 1 to 4 and 6 are applied (READ).
- Judge: nothing is loosened. Two `tests/checks/` files change a call site, `LONG_FUNCTIONS` loses one entry and 121 lines net, and every retargeted test keeps its assertions (READ).
- Checklist 4: `[claim.judge]` names all eight judge files with reasons, including `run`'s raise. The run has no `GROWTH` row to claim (READ).
- 4a, structure: no row scores down. The one new module sits below `runner`, the runtime graph stays acyclic, and the upward import is under `TYPE_CHECKING` only (R3). There is no mutable, lock, platform branch or seam (R4–R6), and private-API lines stay at 90 (EXECUTED). R7 improves: `runner.py` is at 74% of its ceiling. The Kind line carries **structural**.
- 4b: nothing under `.github/` or `release/` changes (EXECUTED).
- §7: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. The Windows box: a write-in that needs no round. Fixed: the description's box is ticked and names run 43652810419, whose 11 Windows legs were green.

## Verdict

Lands at `f63c87b6`: `ast` shows the move is a move, nothing public, default or behavioural changes, the judge is not loosened, and run 43652810419 is green except `review` and `ci-status`, which wait on this file; the one Low is a write-in.
