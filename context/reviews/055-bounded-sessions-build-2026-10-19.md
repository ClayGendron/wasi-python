# Build review of spec 055: bounded sessions

- **Date:** 2026-10-19
- **Reviewer:** a fresh agent (Claude Opus 5.5). It re-reviewed the specification's close revision and confirmed it, and wrote none of the code, the checks or the landing notes.
- **Reviewed:** `spec/055-bounded-sessions` in `wasi_python-055`, rebased onto main `6fd89e0` (068 and 070 in): commits `3e662d6` (the build), `0247cd2` (068's cap per session, F7's context, F3's claim under the lock), `c7b2621` (a rebase fix in `mounts.py`) and `19f09d1` (landing notes). I read the whole diff against `6fd89e0` for `recipes/reactor_main.c`, `recipes/reactor_bootstrap.py`, `src/wasi_python/mounts.py` and `src/wasi_python/tools.py`. In `runner.py` I read the session half: `_State`, the reaper, closers, the exit hook, `_claim_ending`, `_end_session`, `_shutdown`, `_release_session`, `_arm`, `_drive_turn`, `_turn_inside`, `_session_turn`, `_open_session`, `Session`, and the fork hook. In `tests/checks/test_v1_4_sessions.py` I read criteria 1–3, 21–24, 32–42 and the closer's context. I also read the README's *Sessions* text and the landing notes.
- **Set judged:** the builder's `build/artifacts` in the worktree. `shasum -a 256 -c SHA256SUMS` passed on every file (`SHA256SUMS` `ee4d00a3…`). For comparison only, I used main's frozen set `build/sets/s-ff5246a2c2f1a52b`, read-only.
- **Scoreboard (EXECUTED):**
  - Fast tier, `uv run pytest -m "not slow" -n 3`: 429/481, 0 fail, lost 0, gained 39, grew 60. 1,689 passed.
  - Full judge, `uv run pytest -n 3`: **444/481 pass · 2 gap · 35 blocked · 0 fail**; v1.4 204/204; lost 0, absent 0, gained 39, grew 66; judge changed. This equals the builder's figures. `build/progress/latest.json` is kept in the worktree, with a copy beside this file (`latest-full.json`).
  - `ruff check` and `ruff format --check` on `src` and `tests` are clean. `git status` in the worktree is clean.
- **Probes** (beside this file; each `.py` has its `.txt`):
  - `g1`–`g5`: the growth.
  - `s1`: the mount write-back at process exit.
  - `s2`: the real reaper, the cap and memory in the ending, isolation between sessions, closers racing the reaper, re-entrant `close()`, and a forged quit flag.

Labels: **EXECUTED** (I ran it), **READ** (code or document), **INFERRED** (reasoned, not run).

## Short version

The build is careful and close to the specification.
- **The lane-checked items hold.** F3's error row: a `run` that raises ends with `"error"` and no shutdown, whatever the export returned. C1: the exact-tuple and overflow-free reading, with the `2**100 + 4` row (READ, and checked by the judge, EXECUTED).
- **Concurrency is sound** as far as I could read and probe:
  - one claim under the state lock decides which thread runs the ending;
  - the reaper never runs embedder code;
  - closers run in the opening's context;
  - twelve sessions with three racing `close()` calls each ended once each, with `sessions_open` back where it started (EXECUTED).
- **Bounds hold in the ending:**
  - 068's cap: 5 files held plus 1, then 2 more, then `EMFILE` at 8;
  - `memory_bytes`: a `MemoryError` at 198 MiB under 256 MiB, and the ending finished;
  - the real reaper ends an idle session and runs its shutdown (all EXECUTED).
- **Security holds:**
  - a guest that forges the quit flag only ends its own session;
  - nested sessions keep their doors apart;
  - `close()` and `run()` from inside an ending return at once or raise `SessionEnded` (EXECUTED).

One defect: at process exit, the ending's mount write-back is silently skipped in any process that has used `run_async`. A run-level guard reads run_async's exit flag (F1, EXECUTED). The rest are low: criterion 16's plain-reactor spread (F2), a vacuous assertion in criterion 42 (F3), and the growth reasons, which I measured and which need restating (F4).

## Findings, most severe first

### F1. At process exit, the ending's mount write-back is lost once `run_async` has run in the process. Medium (EXECUTED)

**Evidence.** `_Files.walk` makes no provider call "once the interpreter is exiting" (`mounts.py:720`: `if r._hook["exiting"] or …`). `_hook["exiting"]` is set by `_stop_async_calls`. That is run_async's exit hook, registered through `threading._register_atexit` by the first `run_async` or `Session.run_async`. Hooks registered that way run before every `atexit` handler. The session exit hook (`_sessions_at_exit`, registered with `atexit`) therefore runs its endings with the flag already set, and each ending's walk (`_shutdown` → `state.table.walk()`) hands nothing over.

`s1_exit_mount_child.py` sets up a writable mount, and a turn registers a handler that writes a file through a raw descriptor it never closes, so only the ending's walk can hand those bytes over. Results:
- `close()`: the provider receives `b'late'`, with or without a prior `run_async`.
- Process exit with the session at rest, `run_async` never used: it receives `b'late'`.
- Process exit after one `wasi_python.run_async(["-c","pass"])`: it receives only the create's empty write. The bytes are lost and nothing records it.

The guard was right for `run`: no result would carry the record, and its call is being abandoned. A session's exit hook, though, runs endings on purpose. Decision 8 step 4 and Decision 13 promise their write-back, and this break depends on an unrelated API having been used once. Grants are unaffected, since they do not go through the walk.

**Fix.** The ending's walk must not read run_async's exit flag. For example, `walk()` takes a parameter that `_shutdown` passes, or the guard reads a flag of its own that only `run`'s calls set. Keep the deferred-Ctrl-C half of the guard (the re-review's F4). Add a case to criterion 24(b): a writable mount, a handler that leaves a raw descriptor written, and one `run_async` call earlier in the child; after exit the provider holds the bytes. Its stand-in is today's guard.

### F2. Criterion 16's spread on the plain reactor is 2,401 to 4,628 instructions. Low (READ the builder's log; INFERRED the cause)

**Evidence.**
- `build/055/spread.log`: on the snapshot, turns 2 to 6 of five sessions agree exactly (spread 0). On the plain reactor the spreads are 2,655, 3,867, 4,628, 2,401 and 3,063.
- That is above Decision 16's finding threshold (10) and above criterion 16's own band (1,000), so the check would fail if it ran on the plain reactor. It runs on the snapshot, the default, and passes (EXECUTED).
- The cause the builder gives fits the code: the plain reactor's first turn calls `init_interpreter(0)`, which gives a random hash secret, while the snapshot's secret is fixed at 0 (READ, `reactor_main.c`). A different secret per session moves dict and set work in every later turn (INFERRED).
- Linux is unmeasured. The builder had no Linux run, and neither did I.

**Fix (in writing; no code).**
- Decision 16, criterion 16 and the README's sessions text say that a turn's fuel repeats across sessions only on the snapshot.
- On the plain reactor, turns vary by a few thousand instructions with the per-session hash secret, as `run` varies there.
- Criterion 16 names the snapshot.
- The lane's or the release dry run's Linux job carries the Linux half, and its spread goes in the landing notes.

The band is not to be widened.

### F3. Criterion 42's ordering assertion is vacuous. Low (READ)

**Evidence.** `test_a_turn_that_returns_after_close_runs_the_shutdown` ends with `assert order == ["turn returned", "close returned"] or order[0] == "close returned"`. Either order passes it. The specification's clause, "the other thread's `close()` returned only after it [the shutdown]", is therefore not checked. The thread-identity assertion does still catch the stand-in "an ending run by the waiting `close()`'s thread".

**Fix.** Record the end of the shutdown's export call (`_on_export`, or a hook after it) and `close()`'s return in one list, and assert that the shutdown comes first.

### F4. The growth reasons, measured: restate them. Low (EXECUTED; one part INFERRED)

The builder attributed the snapshot's fuel growth to "its heap's layout", inferred. I measured it through the judge's own driver, `harness.guest.run`, whose seeded random and clock make fuel repeat exactly. Each run was made twice, on main's set and 055's, with the same runner (`g3`, `g4`, `g5`). My `g1` and `g2` used `run()` instead; through it, the snapshot's trivial job moves by about ±50,000 between identical runs (real entropy reseeds numpy), so single `run()` figures are noise at this size.

| binary | `-c pass` | `os._exit(0)` (no finalization) | finalization |
|---|---:|---:|---:|
| snapshot, main | 83,425,451 | 2,656,652 | 80,768,799 |
| snapshot, 055 | 83,470,313 | 2,654,349 | 80,815,964 |
| **snapshot, Δ** | **+44,862** | **−2,303** | **+47,165** |
| plain, main | 167,180,268 | 138,860,139 | 28,320,129 |
| plain, 055 | 167,377,978 | 138,979,414 | 28,398,564 |
| **plain, Δ** | **+197,710** | **+119,275** | **+78,435** |

- **Snapshot, trivial jobs.**
  - The start path does not grow. All of the growth is in `Py_FinalizeEx`.
  - The bootstrap adds five tracked objects to the frozen heap (freeze count 62,300 → 62,305) and five names to `_reactor` (16 → 21).
  - Finalization after `gc.unfreeze()` grows by only 7,708 (308,302,124 → 308,309,832). So the frozen teardown's +47 k is not proportional to what was added. Its cause is consistent with address-dependent work in the frozen teardown (INFERRED).
- **The largest growth, `test_extra_preopens_work_on_the_snapshot` (+1,389,264, +0.16%), is heap layout, now with evidence.**
  - Split, the check's program grows by +1.67 M before finalization, and its finalization by −0.27 M (`g4`).
  - The pre-finalization growth is its `isinstance(o, io.IOBase)` walk over the unfrozen heap. Alone, that walk costs 393,270,865 on main and 395,503,765 on 055 (+2.23 M, +0.57%) (`g5`).
  - The work is the same on both sets: 62,317 against 62,322 objects, 343 distinct types on both, and 1,695 classes on both.
  - The ABC caches are sets keyed by class identity. Identical work at a different cost means the cost moves with object addresses, which the larger bootstrap shifts.
- **Plain reactor.**
  - +119 k at start: unmarshalling and executing a bootstrap whose function code grew from 9,047 to 13,772 marshalled bytes (`g1`).
  - +78 k at finalization: tearing the larger `_reactor` down.
  - Departure 3, the reference released before `Py_FinalizeEx`, is in place. The builder measured that it saves about 0.6 M.
  - `run()`'s figure in the landing notes (+460 k, "+0.28%") is a single noisy `run()` measurement. The judge's own figures for the plain jobs grow by 0.08–0.14%, which fits the +198 k measured here.

**Fix.** Replace the `--accept-growth` reason and the landing notes' "`run`'s fuel" paragraph with the measured split:
- plain reactor: about +120 k loading the larger bootstrap at each start, and about +80 k finalizing it;
- snapshot: start unchanged, and about +45 k in finalization of the frozen heap;
- the largest, +0.16%: an `isinstance` walk whose work is unchanged and whose cost moves with object addresses (heap layout), measured;
- evidence: this review's `g3` to `g5`.

## Notes (none blocks)

- **N1. A turn that starts after the lifetime gets one tick rather than a refusal** (READ, `_turn_inside`: `cap = max(1, ceil(left / TICK_S))`). A `run_async` turn is claimed when it is queued, so it can start after the lifetime has passed if the pool is busy. It then runs up to one tick (10 ms) of guest code, `host_alloc` included. That is within the promise's own one-tick precision. Still, refusing in `_turn_inside` when `left <= 0` would make the docstring's "no turn starts at or after it" literally true.
- **N2. Departure 2 is acceptable.** A synchronous `run` that finds the session expired runs the ending on the caller's thread, in the caller's context, and only then raises `SessionEnded`. It can block for up to `shutdown_s` plus any embedder call. `Session.run`'s docstring could say so where it lists `SessionEnded`.

## The builder's departures, judged

1. **A new check file.** Accepted. The goal mark is the same, and 204/204 v1.4 passed.
2. **An expiry found by a synchronous `run` ends on the caller's thread.** Accepted, with N2. One found by `run_async` goes to a closer, as the specification says.
3. **`run` releases the turn reference before `Py_FinalizeEx`.** Accepted. It keeps `run` unchanged in behaviour, and my plain-finalization figure (+78 k, not +0.6 M) fits.
4. **`Session`'s argument wording.** Accepted. The docstrings are accurate against the code I read.
5. **Criterion 16's plain-reactor spread.** A finding, F2, as Decision 16 requires.
6. **The ending's output streams capped at 0.** Accepted. It is what Decision 8 says ("nothing is kept").
7. **`_claim_ending` under the state lock.** Accepted, and it is the right mechanism. A turn's thread claims the ending under the same lock that clears `busy`, so a racing `close()` waits on `done` instead of taking it. The racing-closers probe ended every session exactly once (EXECUTED).

## What was checked and held

- **F3's error row** (READ): in `_session_turn`, any exception out of the turn sets `sound = False` and marks `"error"` before the ending is claimed. That covers a deferred Ctrl-C raised after a normal export return, an embedder `BaseException` in the turn's walk, and a lost call. `_shutdown_applies` needs `sound`. Criterion 42's child checks the Ctrl-C case and passes: `KeyboardInterrupt error skipped 0` (EXECUTED by the judge).
- **C1** (READ): `turn_status` uses `PyTuple_CheckExact`, `PyTuple_GET_SIZE` and `PyTuple_GET_ITEM`, `PyLong_Check`, then `PyLong_AsUnsignedLongMask` and `PyErr_Clear`, then `& 0xFF`, and an identity test against `Py_True`. Criterion 1's rows give 44 for 300 and 4, with empty stderr, for `2**100 + 4` (EXECUTED by the judge).
- **The C side** (READ):
  - `turn` refuses before setting `turned` or `in_turn`, and copies the code, then frees it, before any Python runs.
  - The `gc.unfreeze` reference is taken by the first turn.
  - `shutdown` refuses without `turned`, during `in_turn`, and after `shut`. It sets `shut` before any Python runs, and returns 0 or 120.
  - No `PyErr_Print` is reachable from either export.
- **Concurrency** (READ and EXECUTED):
  - Lock order: no path takes `_sessions_lock` while holding a state lock, and the collector's finalizer takes none.
  - `_ToolLoop.close` never waits, so a `close()` from an async tool cannot deadlock the ending.
  - The exit hook drains the collector's queue (criterion 24(d), EXECUTED by the judge).
  - Closers run in a copy of the opening's context (test, EXECUTED by the judge).
- **Bounds** (EXECUTED, `s2`):
  - the real reaper ended an `idle_s=0.3` session and ran its shutdown;
  - 068's cap held through the ending (`2 33`: two more opens, then `EMFILE`);
  - `memory_bytes` held in the ending (198 MiB, then `MemoryError`; `"finished"`);
  - the ending's deadline cap (F2 of the re-review) is checked by criterion 36 with the armed ticks (EXECUTED by the judge).
- **Security** (EXECUTED, `s2`):
  - a guest that sets `_reactor._quit = True` ends only its own session (`quit`, `finished`), as `exit()` would;
  - session A's host function running a turn of session B: B's door reached B's host only;
  - `close()` and `run()` from inside an ending's host function returned at once or raised `SessionEnded("closed")`;
  - I found no path by which a guest runs past its turn's deadline, its ending's capped deadline, or its lifetime beyond one tick (N1).

## Verdict

**Lands once F1 is fixed**, with its check in criterion 24(b). F2 to F4 must be answered in writing before the landing: F2 in Decision 16 and the README, F3 with a real assertion, F4 with the restated growth reason. No re-review is needed for those three; F1's fix needs only a delta look by the lane.

## One line

A sound build whose bounds, races and security hold under probe; fix the exit-time mount write-back that run_async's exit flag silently drops, and restate criterion 16's scope, criterion 42's order check and the measured growth reasons.

## Delta look after the rebase onto 047 (2026-10-19)

AGENTS.md rule 2 asks for this because the numbers moved. The lane checked the F1 fix (`walk(ending=True)` ignores run_async's exit flag and keeps the Ctrl-C check). It also confirmed that the rebased diff equals the reviewed one line for line. I did not repeat either check.

- **Head and set.** The worktree is at `b3f0af7`, and `git status` is clean. The candidate set is `build/sets/s-9d43bf645dfcaa71`: `shasum -c` is all OK, and `SHA256SUMS` itself is `b0c4f376…` (EXECUTED).
- **Session checks on the candidate set** (EXECUTED; `delta-sessions.log`): I ran `WASI_PYTHON_ARTIFACTS=<candidate> uv run pytest -n 3 tests/checks/test_v1_4_sessions.py tests/unit/test_runner_sessions.py`. Result: 45 passed; v1.4 39/39, 0 fail, lost 0.
- **Growth against 047's set `s-a8221564acc6afc3`** (EXECUTED; `delta-growth.txt`; the same `g3`/`g4`/`g5` probes through the judge's seeded driver):

| row | 047's set | candidate | Δ |
|---|---:|---:|---:|
| plain `pass` | 167,230,744 | 167,474,151 | **+243,407** |
| plain start (`os._exit`) | 138,907,427 | 139,080,987 | +173,560 |
| plain finalization | 28,323,317 | 28,393,164 | +69,847 |
| snapshot `pass` | 83,491,413 | 83,482,875 | **−8,538** |
| snapshot start | 2,654,449 | 2,654,588 | +139 |
| snapshot finalization | 80,836,964 | 80,828,287 | −8,677 |
| extra-preopens check (snapshot) | 851,684,561 | 849,636,864 | **−2,047,697** |
| its `isinstance` walk alone | 396,676,672 | 394,495,938 | −2,180,734 |

The work is the same on both sets: 62,317 against 62,322 objects, 343 types on both, and 1,695 classes on both.

- **Plain reactor: the measured reason still fits.** The growth is at start, from the larger bootstrap, now about +174 k (it was +119 k on the old base), and in finalization, about +70 k. That is about +0.15% in all.
- **Snapshot: the address-dependent reason is now confirmed.**
  - On 047's base, the same bootstrap with the same five extra objects makes the snapshot's trivial job and the extra-preopens check *smaller*: −8.5 k and −2.05 M.
  - On the old base the same rows grew by +45 k and +1.39 M.
  - The work is identical and only the sign changed. So the cost moves with object addresses, not with what the bootstrap adds.
- **Correction to the `--accept-growth` reason**, which still quotes the old base's figures:
  - the bytes are now +7,234 and +12,013;
  - the plain reactor's `run` grows by about +175 k at start and +70 k in finalization (about +0.15%);
  - the snapshot's trivial jobs and `test_extra_preopens_work_on_the_snapshot` no longer grow on 047's base (−8.5 k and −2.05 M);
  - any snapshot job that does grow is address-dependent, which these two rows show by flipping sign with unchanged work.

  The lane should quote the grew list from its own serial record, `build/lane-055/latest-serial.json`.

**Delta verdict: confirmed, it lands**, once the `--accept-growth` reason is corrected as above.
