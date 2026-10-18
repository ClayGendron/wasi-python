# Review of 053 — Async host functions (build review, with a security look)

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude Opus 5.5). I wrote none of the spec, its pre-build review
  or the build.
- **Reviewed:** `git diff 94167a8...9096925` on `spec/053-async-host-functions` (worktree
  `wasi_python-053`), rebased onto main `94167a8` (049, 054 and 056 landed). I judged from the
  spec (Decisions 1 to 13, the Confirmation's C-1 and C-2, criteria 1 to 22) and the diff. I
  used the landing notes only to find things to check.
- **Read:** AGENTS.md (rule 3a), the constitution (§4.4, §4.9, §4.15, §5.6, §7), the reviews
  README, the spec in full, the pre-build review and its Confirmation
  (`build/reviews-evidence/053-review/`), the 0.1.0a4 security review (F1, F2, N8) with its
  probes, and `src/wasi_python/tools.py` and `runner.py` as they stand at HEAD.
- **Re-ran:** all with `WASI_PYTHON_ARTIFACTS=…/build/sets/s-c4190ca065ada03a`, on
  darwin-arm64 with Python 3.14.2. The machine was heavily loaded by other agents (load
  average 44). Scripts and logs are beside this file.
  - `uv run pytest -m "not slow"` → `314/364 pass · 0 gap · 10 blocked · 1 fail`;
    `ratchet vs 5f56591135: lost 1 · … gained 10 · grew 0`. The one failure is spec 030's
    load-sensitive door-deadline check, `test_a_deadline_during_a_door_call_under_cancel_is_named`
    (`"deadline None None b''"` where `'in the door'` was expected). Run alone three times
    afterwards it passed 3 of 3 (`door-deadline-rerun.log`). It is the known flake spec 052 is
    fixing, not this change. This change does not touch the door's waits.
  - The new and changed checks alone (`test_async_tools.py`, `test_tools.py`,
    `test_runner_tools.py`, and the embedding checks matching "async or tools"): 241 passed.
  - `uv run ruff check src tests`: clean. `uv run ruff format --check src tests`: 79 files clean.
  - `uv run python tests/harness/api.py --check`: exit 0. `git diff 94167a8...HEAD --
    tests/public_api.txt`: empty.
  - **The full judge, once, with no flags** (`full-judge.log`):
    ```
    wasi_python v1: 322/364 pass · 0 gap · 42 blocked · 0 fail   (unit suite 1073/1081, 8 skipped)
      v1.4  embedding           157/157
    ratchet vs 5f56591135: lost 0 · absent 0 · unrun 0 · unrun locally 28 · gained 10 · grew 0 · upstream unrun 31 · judge changed: tests/checks/test_v1_4_embedding.py, tests/unit/test_async_tools.py, tests/unit/test_runner_tools.py and 1 more
    ================= 1395 passed, 50 skipped in 257.15s (0:04:17) =================
    ```
    The door-deadline check passed in this run. The 42 blocked are the worktree's missing
    source trees, as the landing notes say. `tests/public_api.txt` is not among the judge's
    changed files.
  - I re-made the builder's eleven stand-ins and ten mutants of my own, and ran each on a
    scratch copy of HEAD (`git archive`; never the worktree). Each copy file was restored and
    compared byte for byte (`mutants.py`, `mutants.txt`, `mutants-rerun.txt`, `mutant-logs/`).
  - Probes P1 to P6, below.

## Acceptance criteria against evidence

Labels: EXECUTED (I ran it), READ (I read code or text), INFERRED (reasoned, not run).

1. **Async callables accepted; async generators and async `host=` refused.** Met (EXECUTED).
   The check passes. My mutant R9 (the async `host=` refusal removed) is caught by
   `test_runner_tools.py` and by criterion 1's check ("the artifacts must not be looked up").
   `_is_async_callable` imports nothing from `wasi_python.tools` (READ).
2. **Awaited on the tool loop; context variables carried.** Met (EXECUTED). Mutant R6 (the post
   made in an empty `contextvars.Context`) is caught: the request variable reads `'unset'`.
   P4's case 1: `run` called from inside a running coroutine serves its async tool on
   `wasi-python-tool--loop`, answer `ok`.
3. **Every end cancels a started task.** Met (EXECUTED). Stand-in c3/c11 (abandon without
   cancelling) is killed: `AssertionError: []`. P4's case 2: a `run_async` cancelled mid-tool
   raises `CancelledError`, the tool saw its cancel, and 0 tasks are left.
4. **A task that ignores its cancel holds its slot.** Met (EXECUTED). Stand-in c4 is killed.
   P3, end to end: 40 calls to a tool that ignores its cancel gave 4 `timeout after 0.02 s` and
   36 answered at once with the quota's message. `tool_threads_running` was 5 after `run` (four
   work threads and the loop thread), and 0 after the release.
5. **An answered call starts no awaitable; C-2's single acquisition.** Met (EXECUTED).
   - Stand-in c5 is killed (`[1] == []`).
   - The two C-2 stand-ins are killed: 2 acquisitions, and "the bound's lock was taken twice".
   - My R1 (the start decided on the work thread at the post, so the wrapper's first step does
     not check) is killed (`[1] == []`).
   - READ: `_Bounded._begin` takes the lock once and is not built on `_proceed`. `_abandon`
     reads `post.started` under the same lock and cancels after releasing it. `_Ops.post` refuses
     an answered call before posting.
   - **Note:** `test_the_first_step_takes_the_lock_once` tests `_begin` on its own. That the
     wrapper calls it is pinned by criterion 5's busy-loop case (my R1 shows this).
6. **A late gate skips an async tool.** Met (EXECUTED). Stand-in c6 is killed. P2 (below)
   covers a late async gate that swallows its cancel and returns `True`: the tool never ran.
7. **Faults stay in the record; C-1's row.** Met (EXECUTED).
   - Stand-in c7/C-1 is killed: `'timeout' == 'tool_error'` at the 30 s fail-safe.
   - My R7 (`KeyboardInterrupt`/`SystemExit` re-raised from the wrapper) is killed.
   - My R10 (an unrequested `CancelledError` during a cancel answered as a fault) is killed.
   - P4's case 6: under `run_async`, a tool's own `KeyboardInterrupt` and `SystemExit(3)` came
     back as "(internal error)" faults naming them. Nothing reached `asyncio.run`, nothing was
     written to stderr, and 0 warnings.
   - **But:** F1 below is a hole in the C-1 branch of the wait.
8. **The loop's life.** Met (EXECUTED).
   - Stand-in c8/F3 is killed, and so is my R5 (no `loop.close()` in the run-down).
   - My R8 (`_instance` never calls `close()`) is killed by criterion 9: a loop thread stays
     alive.
   - P4's case 3a: a task a tool spawned under `run` was cancelled at the call's end, and no
     loop thread was left.
9. **A guest calls async tools under `run`.** Met (EXECUTED, in the full judge).
10. **`run_async` awaits on the caller's loop.** Met (EXECUTED). Stand-in c10 is killed.
11. **A timeout cancels.** Met (EXECUTED). It is killed by c3/c11 through criterion 3 (the first
    failure stops the run under `-x`). The builder showed this check failing on its own
    (READ, `mutants-rebased.txt`).
12. to 15. **The deadline, a `run_async` cancel, `cancel=`, Ctrl-C.** Met (EXECUTED, full judge,
    child processes).
16. **An ignoring tool is bounded end to end.** Met (EXECUTED). Stand-in c16 (`close()` joins
    the loop's thread) is killed at 120 s: "run waited for the tasks that ignore their cancel".
17. **One call's blocked loop does not starve another.** Met (EXECUTED). Stand-in c17 (one loop
    per process) is killed. P4's case 4 shows the same-call side, as the README says: while one
    async tool blocks its loop, the call's later async tools on that loop time out, and they
    were never started.
18. **Fuel is exact.** Met (EXECUTED, full judge).
19. **The judge change, as listed.** Met (READ). The diff to `test_tools.py` and
    `test_runner_tools.py` is the coroutine-gate row turned into an async-generator row, the
    `tool()` refusal row, and four async `host=` rows. No other existing check changed.
20. **The recipes ran.** The README's *Async tools* example, re-run as written: `b'1.08\n'`
    (EXECUTED). I did not re-run the MCP recipe. It needs an unpinned `mcp==2.3.0` fetched with
    `--isolated`; I rely on the landing notes' quoted output (READ).
21. **049 landed first.** Met (EXECUTED and READ).
    - `api.py --check` passes, and `tests/public_api.txt` is unchanged.
    - The README's generated block changes only in `run`'s `host`, `tools` and `gate` entries
      and in `tool`'s `Raises` (`run_async` is shown short).
    - The shared `Args:` text is identical in `run` and `run_async`, and it names no
      specification and no internal name.
    - `_check_tools` keeps 049's `limits` signature, with this spec's two refusals inside it.
    - 049's renames (`_MAX_ABANDONED`, `_DEADLINE_MARGIN_TICKS`, `_FAULT_CHARS`) are used by
      the new code.
    - Every new module-level name is private.
22. **The judge is green.** Met (EXECUTED): ruff clean; full judge 0 fail, lost 0, grew 0.

## Attacks (security look)

- **P2, the a4 review's F2 race probe adapted to async** (`p2_f2_async_races.py`). Each of three
  gate kinds (async; async that swallows its cancel and allows late; sync) was run against each
  of three ends (`timeout_s=0.05`, a cancel at a random time, a random deadline), six runs of 30
  calls each, under `run` and again under `run_async`.
  - The async gate holds the loop for 0 to 60 ms after allowing, so the tool's post often
    waits behind it.
  - `_Bounded._abandon` and `_begin` are instrumented without changing what they decide. The
    probe counts a slot that was already answered when `_begin` admitted it.
  - **On HEAD under `run`:** 1,126 calls, 536 bodies started, 68 of them abandoned. 0 answered
    first that then ran; 0 admitted after the answer; 0 effects after `run` returned; 0 tools
    run after a swallowing gate. **0 violations.**
  - **Under `run_async`:** 1,077 calls, 371 started. **0 violations.**
  - **The probe detects the defect:** on stand-in c5 (no first-step check), 70 bodies were
    admitted after their answer, and 1 effect landed after `run` returned
    (`p2_on_c5_mutant.log`). **The a4 review's F2 holds for coroutines** (EXECUTED).
- **P3, many async calls; counting leaks** (`p3_leaks.py`).
  - Three runs, each of 300 async and 300 sync calls with an async gate, all `ok`. They made 3
    private loops, and 0 were still open afterwards. No thread was left beyond the runner's own
    ticker and pool, and the `tool_threads_running` delta was 0.
  - The same under `run_async`: 0 tasks left on the caller's loop.
  - 0 warnings and 0 bytes on stderr throughout.
- **P4, loops** (`p4_loops.py`).
  - `run` inside a running loop works.
  - A `run_async` cancelled mid-tool cancels the tool's task.
  - Spawned tasks are cancelled at the call's end under `run`. Under `run_async` they outlive
    the call (asyncio.run's shutdown cancelled them), as the README says.
  - A tool that blocks its loop delays only that loop's later tools.
  - 0 warnings, and nothing on stderr from the runner.
  - One thing escaped, as expected: a `KeyboardInterrupt` raised by a task the tool *spawned*
    on the caller's loop reached the embedder's `asyncio.run`. That is the embedder's own task
    on its own loop, and Decision 6 limits the guarantee to the tool's own coroutine. See N3.
- **P6, the a4 review's F1 for async callables** (`p6_f1_async_partials.py`). The cases: a
  `partial` of an `async def`, a partial of a partial, a partial of an async bound method, and
  a partial of an object with an async `__call__`.
  - In each, the bound `user_id` and `api_key` are absent from the schema, and the secret is
    not in the descriptor.
  - Overriding either key is answered `invalid_arguments`.
  - A call with no arguments uses the bound values.
  - `functools.wraps` over an async partial, and `class: __call__ = partial(async def)`, are
    refused at `tool()`. That fails closed. **F1 holds** (EXECUTED).

## Findings, most severe first

1. **F1. A stale `started` read can report a tool that ran as "cancelled before it started".**
   Low; fix before landing. One line and a check. EXECUTED with a forced interleaving; not
   reproduced naturally in 6,000 calls.
   - **Where:** `tools.py:1713-1721`, `_ToolLoop.run`'s wait. Each slice it reads
     `started = ops.started(post)`, then `post.ended.is_set()`, then
     `future.done() and not started`. `started` is read before the other two.
   - **The race:** the post waited past the first 10 ms slice, because the loop was busy. Then
     the wrapper starts, runs the tool to its end, sets `ended`, and the posted future completes,
     all between the `ended` check and the `future.done()` check. The stale `started=False` then
     takes the C-1 branch. The branch closes the (finished) awaitable and raises
     `CancelledError("cancelled before it started")`.
   - **Failure** (`p1_stale_started.py`, log beside it): an `async def transfer(amount)`
     appended its effect (`effects: [100]`). The guest was answered `tool_error` "transfer
     failed (internal error)". The record says
     `fault='CancelledError: cancelled before it started', abandoned=False`. So the guest is
     told the call failed, and may retry and pay twice. The embedder's record says the tool
     never started, when it ran.
   - **How likely:** the window is two statements on the work thread. The loop thread must run
     the whole wrapper and the future's done-callback inside it. The GIL makes that rare: P1b,
     6,000 calls with a loop busy in one-slice bursts and switch intervals of 1 µs and 5 ms,
     found 0 (INFERRED: a free-threaded build makes it likelier). The result is wrong only
     for a call that was *not* abandoned; for an abandoned call nobody reads the answer.
   - **Fix:** decide the C-1 branch from the facts in an order that cannot go stale. The
     wrapper sets `ended` in its `finally` before its task completes. So a done future with
     `ended` still unset means the wrapper's body never ran. Test `future.done()` first, then
     re-check `post.ended.is_set()`, for example
     `if future.done() and not post.ended.is_set(): …` (the `started` read is not needed there).
     I tried exactly that line on the scratch copy (EXECUTED, `p1_on_fix.log`). P1 then answers
     `ok` with no fault, and all 10 unit checks pass, the C-1 row included. The copy was then
     restored to HEAD byte for byte.
   - **The check:** P1's injection, which makes the `ended` read return the pre-run value after
     letting the wrapper finish. It answers `ok` on the fix, and gives the fault on HEAD.
2. **N1 (note). Three defensive branches have no check that pins them** (EXECUTED: mutants R2,
   R3 and R4 survive all ten unit checks).
   - R2: cancelling the posted future instead of the task. The spec says never to (Decision 4,
     the pre-build review's R4).
   - R3: the wait's fourth end, "the private loop's thread is dead".
   - R4: `is_closed()` skipped in `_cancel_post` and `close()`.
   - All three are near-equivalent today. `_serve`'s `finally` always closes the loop before
     its thread ends, so the third end covers the fourth. `except BaseException` already
     swallows a closed loop's `RuntimeError`; my R4b, which also narrows that `except`, is
     killed. `_cancel_post` skips a closed loop before it would cancel.
   - So they are belt and braces, not defects. A later change could drop one without the judge
     noticing. A unit row each would pin them: `_cancel_post` on a loop that closes between the
     check and the call adds 0 log records; the wait ends when a fake thread reports dead with
     the loop open. Not required for landing.
3. **N2 (note). `_is_async` is now unused in `tools.py`** (READ). Its only caller,
   `_check_tools`, now imports `_is_async_generator`, and the runner has its own
   `_is_async_callable`. It is dead code to delete, or leave for a later tidy.
4. **N3 (note, docs). Under `run_async`, a `KeyboardInterrupt` from a task a tool *spawns*
   reaches the embedder's `asyncio.run`** (EXECUTED, P4 case 5). This is asyncio's rule for the
   embedder's own loop, and the spec scopes Decision 6 to the tool's own coroutine. The
   README's *Faults stay in the call* says "the tool raises", which is accurate. One clause
   ("tasks it spawns are yours: their exceptions reach your loop") would stop a reader reading
   it more widely. Optional.

## Constitution checks

- **§4.4 (two things, one tool protocol, gated on every call):** holds (READ). The guest
  package, the protocol and the imports are unchanged. An async gate is awaited before every
  tool, and a gate's fault or cancel fails closed (`denied`). An async `host=` is refused rather
  than served, so the raw door stays opaque and synchronous.
- **§4.9 (tests count):** holds (READ, grep). The new checks wait on events. Their
  `timeout_s`/`deadline_s` values only choose outcomes or act as fail-safes, and no check reads
  the clock.
- **§4.15 (safe by default):** holds. No new argument, default or channel. A loop thread starts
  only at an awaitable returned by a tool the embedder passed. The abandoned quota (4) and
  `tool_threads_running` cover async tools (P3).
- **§5.6:** this review re-ran the counted tests and the full judge, and checks each criterion.
- **§7:** nothing tripped. Not build-class: no `scripts/`, `recipes/`, `downloads/SHA256SUMS`
  or workflow change (READ, diff stat).

## Disposition (filled in by the author, then confirmed by the reviewer)

The author's full text is `build/reviews-evidence/053-buildreview/disposition.md`, and it is
written into the spec's landing notes at `e07630f`. In short:

1. **F1: fixed in `4b521c8`.**
   - The C-1 branch is now `future.done() and not post.ended.is_set()`, and no `started` is read
     before it.
   - The loop-closed branch checks `ended` again before it reports the loop stopped.
   - New check: `test_a_tool_that_ran_is_never_reported_as_not_started`. It forces the
     interleaving through the posted future's first `done()`.
2. **N1: answered in part.**
   - A row in `test_close_ends_the_calls_loop` pins `_cancel_post` on a loop that reports
     itself open but refuses the call.
   - R2 and R3 stay unpinned. The answer gives the reasons.
3. **N2: fixed.** `_is_async` is deleted.
4. **N3: fixed.** One README clause: tasks the tool spawns are yours, and under `run_async`
   their exceptions reach your loop.

## Verdict

**Lands once F1 is fixed.** F1 is a one-line reordering of the C-1 test, with P1's injection as
its check. Everything else holds:
- every criterion is met;
- all eleven stand-ins and my seven non-equivalent mutants are killed;
- the async F2 race probe finds 0 late starts in 2,203 calls;
- F1 (bound keywords) holds for async partials;
- no thread, loop or task leaks;
- the full judge is green with lost 0 and grew 0.

The notes need no change before landing.

## One line

Async tools are awaited where they belong and are never started after their call is answered.
One stale read can mislabel a finished tool as never started; fix that line, then it lands.

## Confirmation (2026-10-18)

The same reviewer checked `9096925..e07630f`: `4b521c8` (the fix and its check) and
`e07630f` (the notes). I did not take the author's word; I read the diff and re-ran the
evidence. All runs used `WASI_PYTHON_ARTIFACTS=…/build/sets/s-c4190ca065ada03a`. Mutants ran on
a fresh `git archive e07630f` copy in the scratchpad, never the worktree. Every file was
restored, and `tools.py` was compared with `e07630f` byte for byte. Logs are in the scratchpad's
`053-buildreview/confirm/`.

1. **F1: confirmed fixed (READ, EXECUTED).**
   - **READ.** `_ToolLoop.run`'s wait reads `future.done()` first and then `post.ended`. The
     wrapper sets `ended` in its `finally`, before its task can complete. So "done and
     `ended` unset" means the wrapper's body never ran, and neither read can go stale. No
     `started` read is left ahead of that test.
   - **READ.** The loop-closed branch now breaks when `ended` is set, and reads `started` only
     after that. So it cannot mislabel a finished tool as stopped either.
   - **The new check passes on the fix (11 of 11 unit checks), and it kills the old wait.** I
     restored the stale `started`/`ended` reads ahead of the test. The new check then fails
     with `('tool_error', …internal error) == ('ok', 'done')`.
   - It also kills a C-1 test that drops the `ended` re-check (`if future.done():`).
   - **The builder's account of my P1 holds** (EXECUTED: `p1_on_e07630f.log`, killed by a 20 s
     alarm, exit 142).
     - P1 injects on `ended.is_set()`. The fixed wait reads that only once `future.done()` is
       true.
     - P1 holds the loop until that injection fires. So the future never completes, and the
       wait spins on a loop that is busy but open. That is P1's own deadlock, not the code's.
     - My earlier trial of the one-line fix passed P1 only because it left the old
       `ended.is_set()` break in place ahead of the new test.
     - The new check injects at the read the fixed wait does make (the future's first
       `done()`), so it is the right form.
2. **Stand-ins and mutants on the fix (EXECUTED, `mutants-on-fix.txt`).**
   - **Still caught:** c4, c5, R1, c7/C-1 (rewritten against the new line, `'timeout' ==
     'tool_error'` at the 30 s fail-safe), c8/F3, R4b, and the old wait.
   - **Still surviving:** R2 (cancel the posted future), R3 (no thread-death end) and R4 (no
     `is_closed()` skip). They are near-equivalent, as N1 said, and the author's reasons for
     leaving them unpinned are sound.
   - **One new survivor:** the loop-closed branch's new `ended` re-check can be removed with
     all 11 unit checks still passing.
     - When it would matter: a tool that stops its own loop and still returns a value. If the
       wait sees the loop closed before its `ended.wait` returns, it would report the loop
       stopped and lose that value.
     - It is narrow, and the code is right as written. It adds to N1, and does not block.
3. **The a4 review's F2, async, re-run on `e07630f` (EXECUTED).**
   - Under `run`: 1,087 calls, 528 started, 69 abandoned that ran.
   - Under `run_async`: 1,080 calls, 391 started, 76 abandoned that ran.
   - In both: 0 bodies admitted after their answer, 0 ran after being answered first, 0 effects
     after `run` returned, and `tool_threads_running` back to 0. **0 violations.**
4. **N2 and N3: confirmed (READ, EXECUTED).** `_is_async` is gone, and a search finds no
   caller left. The README clause is accurate. `api.py --check` exits 0, and
   `tests/public_api.txt` is unchanged against `94167a8`.
5. **The judge (EXECUTED).** `ruff check` and `ruff format --check` are clean. Fast tier:
   ```
   wasi_python v1: 315/364 pass · 0 gap · 10 blocked · 0 fail · 39 deselected   (unit suite 1074/1082, 8 skipped)
     v1.4  embedding           157/157
   ratchet vs 5f56591135: lost 0 · absent 0 · unrun 0 · unrun locally 8 · gained 10 · grew 0 · upstream unrun 31 · not selected 27 · judge changed: tests/checks/test_v1_4_embedding.py, tests/unit/test_async_tools.py, tests/unit/test_runner_tools.py and 1 more
   1389 passed, 18 skipped, 39 deselected
   ```
   - The door-deadline check passed this time.
   - I saw no reason for a second full judge. The fix changes one wait in `tools.py`, which
     the unit and embedding checks in the fast tier cover in full. The lane judges the exact
     commit it accepts.
6. **One small inaccuracy in the notes, not blocking.** They say R4b "is pinned by" the new row.
   R4b was already caught before it, by the closed-loop row. What the new row adds is a pin on
   the `except` alone, the half of R4b that row did not cover.

**Confirmed, it lands.**
