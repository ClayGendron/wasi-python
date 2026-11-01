# Review of 172 — A class for tests the collector moves

- **Date:** 2026-11-01
- **Reviewer:** an agent (Claude), a fresh sub-agent of the orchestrating session; not the author
- **Reviewed:** `60a895c3` on `9c0d879e` (#90, one commit, rebased onto #71 and #87); round 2, `60a895c3..dacd490c`
- **Run:** 41274473100 on `dacd490c`: `gather` and all 31 Linux judge shards green; `review` and `ci-status` red only for this file's absence (as the orchestrator reports; not dispatched or polled by me)
- **Windows legs:** all 11 windows-2025 legs green on 41274473100
- **Re-ran:** `tests/lint` → 14 passed; `tests/unit/test_upstream.py` → 95 passed; `tests/checks/test_rules.py` → 134 passed, 2 skipped; the ten new unit rows against `dev`'s `upstream.py` given only `Klass`'s two fields and `klass_of`, in a scratch copy → 10 failed; tqdm-smoke's suite check and six class checks by node id on 175-176's set (state B) and 167's (state A), each → 1 passed, 6 xfailed, exit 0.
- **Box:** 45 minutes (a judge change); used about 45.

## Acceptance criteria against evidence

1. A node-limited class claims its tests in either order and outcome, first — met. EXECUTED: the unit row passes on head and fails on `dev`'s judge. READ: `judge_group` routes a named node to `_limited_finding` before the `OUTCOMES` filter and before the ordinary classes, which now iterate `ordinary` only.
2. A named test that passes or fails for another cause is a group finding — met. EXECUTED as above. READ: a pass, skip, xfail or xpass of a named node reaches `_limited_finding` (the filter that drops them comes after), and another cause is never handed to an ordinary class.
3. Its list is its nodes; an absent one changes the digest — met. EXECUTED. READ: `class_findings` returns nothing when neither named test is a member, so the case of both absent shows as a gap check that passes, which the plugin turns red ("remove the gap"); held either way.
4. The rules of Decision 3 — met in code, and six of its seven refusals have a row (finding 2). EXECUTED: each row fails on `dev`'s judge.
5. tqdm-smoke's checks give the same verdicts and digests in both states — met. EXECUTED on two of the builder's sets: the suite check passes and all six gaps match their counts and digests on each. The stream my run left for 167's set shows state A (`test_iter_basic_overhead` fails and errors at teardown, `test_iter_overhead_simplebar_hard` errors at setup on the deallocator); for 175-176's set my run's stream was overwritten by the next, and the builder's saved stream of the same set shows state B (READ).

Rebase onto #71: `dev`'s three lists, written by `bedf8f30` (#71), held `test_iter_basic_overhead` in `no-asyncio-loop-error` and `test_iter_overhead_simplebar_hard` in `no-threads` and `no-threads-error` (state B). The branch is one commit on `9c0d879e`, and its diff to `dev` removes exactly those three lines and changes exactly the four gaps (one added, three counts and digests); nothing #71 wrote is undone (EXECUTED, `git diff origin/dev...HEAD`). Each count falls by one, as one member leaving each list must.

Judge files: `tests/harness/upstream.py`, `tests/upstream/tqdm.toml`, the three list files and `tests/known_gaps.toml` are each claimed under `[claim.judge]` with a reason, owned by Decision 4 and by the owner's decision of 2026-10-31 in `context/decisions.md`. No pass is lost: the two tests passed in no state before and pass in none now; they move from three classes to one that still holds them to fail. The new pattern is the exact union of `no-threads`' and `no-asyncio-loop-error`'s (READ), as the owner asked. This is a judge change made with its reason, not a quiet weakening; its one loosening, that either test may fail or error for any of the three causes, is the decision itself.

Writing rules: no code file names a specification, memo or `context/` path; the new comment in `tqdm.toml` and the `Klass` docstring give the reason in words; `tests/lint` green. No check counts time.

Structure (4a): not structural; nothing under `src/`. `judge_group` about 60 lines; no allowance raised.

Code under `.github/` and `release/` (4b): none changed.

Self-check: the Windows-legs box is unticked, with the reason that the run had not started (finding 3).

## Findings, most severe first

1. **The claim's reasons for the three list files name the wrong test** (`context/changes/172-a-class-for-tests-the-collector-moves.md`, `[claim.judge]`) — they were written in state A, before the rebase onto #71, and say the opposite of the diff. Failure: the acceptance record keeps `no-asyncio-loop-error.txt` = "test_iter_overhead_simplebar_hard leaves" while the diff removes `test_iter_basic_overhead`, and the other two the reverse; a reader of the history after 0.1.3 is told a false fact about which line moved. Low. Fix: `"…/no-asyncio-loop-error.txt" = "test_iter_basic_overhead leaves for collector-timing"`, `"…/no-threads-error.txt" = "test_iter_overhead_simplebar_hard leaves for collector-timing"`, `"…/no-threads.txt" = "test_iter_overhead_simplebar_hard leaves for collector-timing"`; or, state-free, "the named test in this list leaves for collector-timing".
2. **The refusal of `nodes` in CPython's family has no row** (`tests/harness/upstream.py` `class_shape_errors`; `tests/unit/test_upstream.py`) — Decision 3 names it; Acceptance criterion 4 lists six rows, none for it. Failure: an edit that drops the `runner == "regrtest"` branch passes every row, and a class with `nodes` in a CPython plan then claims nothing, because `regrtest.py`'s judge compares `k.outcome`, which a node-limited class leaves empty, so its named tests fall to the ordinary classes and its gap reads "remove the gap", a red that points away from the cause. Low. Fix: a seventh case built on a config whose `runner` is `"regrtest"`, expecting "only a pytest family's judge reads them", seen failing first.
3. **The self-check's Windows box is unticked** (#90's description) — with its reason. Low. Fix: tick it once the orchestrator has read the Windows legs of the head's run.

Noted, not a finding: the class holds the two tests the owner named. If a later set's collector fires during a third test of `tests_perf.py`, that test moves class and tqdm-smoke is red again, as it should be until a person looks; Decision 5's follow-up would cover it.

## Constitution checks

- §4 constraints: no upstream patch, pin, artifact or `src/` file moves; uv only; no code file names a specification; the judge changes with its reason under `[claim.judge]` and the owner's recorded approval; no golden output or allowance is edited to turn a run green without a claim.
- §7 never-do list: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Claim reasons — fixed in `dacd490c` with the replacement text given above; `units` 10 → 11. Confirmed.
2. CPython's refusal row — fixed in `dacd490c`: `test_a_node_limited_class_in_cpythons_family_is_refused`; the specification's criterion 4, Design line and landing notes name it. Confirmed.
3. Windows box — ticked in #90's description by the orchestrator after reading 41274473100's Windows legs. Confirmed.

## Round 2

- **Reviewed:** `60a895c3..dacd490c`, one fix commit: the news file, the specification and one unit row. Its trailer names Claude Opus 5.5.
- **Re-ran** (EXECUTED): `tests/unit/test_upstream.py` and `tests/lint` on `dacd490c` → 110 passed (96 and 14). The new row, in a scratch copy of `dacd490c` with the `runner == "regrtest"` refusal deleted → 1 failed; restored → passes. So it was seen failing first, as the builder reports.
- **Read:** the three reasons now match the diff's lines: `no-asyncio-loop-error.txt` loses `test_iter_basic_overhead`; the other two lose `test_iter_overhead_simplebar_hard`. `units = 11` counts the eleven rows. The row's docstring names no specification. No judge file, gap or list changed in this round, so the tqdm-smoke probes of round 1 still stand.
- **Run:** 41274473100 on `dacd490c`: green but for this file's absence, Windows legs included.

## Verdict

Lands on dacd490c: the node-limited class is built as the specification and the owner's decision say, each new row was seen failing on `dev`'s judge, both of the collector's states give the same verdicts and digests, and the rebase keeps #71's lists less the two tests; round 1's three Lows are fixed and read, and run 41274473100 is green on every judge shard, Linux and Windows.
