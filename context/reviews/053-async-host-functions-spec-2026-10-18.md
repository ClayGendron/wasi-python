# Review of 053 — Async host functions (the specification, before build)

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I wrote none of the spec, the memo or the code. I read `AGENTS.md`; the constitution (§4.4, §4.5, §4.15, §5.2, §5.6, §6); `context/reviews/README.md` and 031's pre-build review (for the shape); decisions 15 and 49; specs 015, 030, 031 and 036; spec 049 and its built branch's `tests/public_api.txt`; the 0.1.0a4 security review (`build/reviews-evidence/a4-security/`, F1 and F2); and the code the spec changes (`tools.py`: `tool`, `_make`, `_is_async`, `_type_hints`, `_derived`, `_Work`, `_Slot`, `_Bounded`, `_ToolHost`; `runner.py`: `run`, `run_async`, `_checked`, `_check_tools`, `_instance`, `_door`, `_tool_host`, `stats`, `_after_fork_in_child`, the Ctrl-C deferral). Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `spec/053-async-host-functions` at `faf63d7` (`git diff 62d2c56...faf63d7`): the spec, the memo `research/2026-10-18-async-host-functions.md` with its probe folder, and question 90.
- **Spec 056:** its worktree (`../wasi_python-056`, branch `spec/056-the-a4-security-reviews-findings`) is at `28800bc` with no commit and no change (READ, `git status`, `git log main..`). So 056's text could not be compared. What 053 must say about it is finding F2.
- **Ran (EXECUTED, darwin-arm64).** Nothing was written in any tree. Scripts and outputs are beside this file:
  - `probe_r.py` → `probe_r.txt`, on Python 3.11.14 and 3.14.2 (`uv run --isolated --no-project python -I`): R1 (a post cancelled before the loop runs it), R2 (a done and a pending `Future` of another loop), R3 (a post to a closed loop), R4 (cancelling a post whose loop has closed).
  - `probe_r5.py` → `probe_r5.txt`: a private loop whose thread ends with the loop unclosed.
  - `scripts/probe_e2e.py` → `probe_e2e.txt`: E1, through the real runner and a real guest, using the memo's own throwaway patch (`prototype_probe.py`, copied unchanged into `scripts/`), from a `git archive faf63d7` export under `export/`, against the frozen set `build/sets/s-f94dec535086b06c` (read only), wasmtime-py 49.0.0.
- **Scoreboard:** not re-run. The diff touches only `context/` (READ), so the judge's state is main's, and running it would write into a tree.

## What holds

- **The loop choice (Decision 2) is right.** Under `run_async` the caller's loop is free while the worker waits, and loop-bound objects need it (memo A1, A7, EXECUTED by the author; my R2 agrees: a pending `Future` of another loop raises `RuntimeError`). Under `run` the caller's loop may be absent or blocked (memo A2), so a private loop per call is needed. Per call, not per process, matches spec 011 and 036's review F2.
- **Keeping 036's work thread (Decision 3)** keeps the gate and the result's encoding off the embedder's loop. Waiting on the wrapper's own end (not the posted future) makes the quota and `tool_threads_running` cover a task that ignores its cancel. The memo's A4 shows why the posted future is the wrong thing to wait on (READ, INFERRED sound).
- **Contextvars (Decision 3)**: the task copies the posting thread's context (memo A3; READ: `call_soon_threadsafe` captures the context, and `create_task` copies it).
- **No double answer.** Only the door thread's `invoke` return answers a frame. The work thread and the task never write to the guest (READ `_ToolHost._answer`, INFERRED from Decision 3).
- **Spec 049: no snapshot line changes (READ).** The built `tests/public_api.txt` holds signatures, annotations, fields, defaults, `stats keys` and `outcome kinds`, and no docstrings. `gate: Callable[[ToolCall], Any] | None` and `host: Callable[[bytes], bytes | bytearray | memoryview] | None` stay as they are. 053 adds no kind, field or key. At rebase, 049's new `tool` docstring ("TypeError: … the function is async") must change, which Decision 12 already covers.
- **Security review F1 is not reopened (READ, INFERRED).** An async tool's schema goes through the same `_make` → `_type_hints` / `_derived` path as a sync one. Both unwrap `partial`s, and 053 adds no second path. A plain `def` that returns a coroutine closes over its authority, so nothing is published. This holds on one condition: 056's fix must sit in that shared path, before any async branch. Criterion 1's partial must also follow 056's rule (F6).
- **§4.4:** no new import. Every call, async or not, still passes the gate. An async gate's fault fails closed (Decision 6). **§4.15:** no new channel, limit or default. The private loop is reachable only through the tools the embedder passed. **Not build-class:** no guest, zip or recipe change (READ: the diff, and Decision 10).
- **No wall-clock in the checks.** `timeout_s` values only choose outcomes, and the waits are fail-safes.
- **Embedder-neutral:** asyncio only, trio users are named and pointed to `run`, and the MCP recipe is a README example run once with a pinned version, not a dependency.
- **Question 90** is framed fairly. The fact checks out: the host answers `batch` with a clean `protocol` error, "(batch is reserved for a later version)", READ `_answer`. The recommendation is labelled as the agent's, and nothing in 053 waits on it. One note for the lane: its notes say 055 may also take number 90, so renumber at landing.

## Acceptance criteria against the design

1. Refusals and acceptances: sound. Two wording fixes are in F6: the partial, and the "submit must not be reached … reached, 1" phrasing.
2. Awaited on the tool loop, one private loop thread: sound.
3. Every end cancels: sound, but each end must fire after the tool signals it started (F6).
4. Ignored cancel holds the slot: sound if the release is awaited without blocking the loop (F6). The stand-in (waiting on the posted future) does catch the regression.
5. An answered call starts nothing: **insufficient.** It never posts before the answer and then answers before the loop turns, which is where the defect is (F1). Its sync half belongs to 056 (F2).
6. Faults and close: add `loop.is_closed()` (F6), and cases for a loop that dies (F3).
7. Under `run`: sound.
8. Caller's loop: the claimed stand-in failure is not reliable (F5). Only the loop-identity assertion catches the stand-in. 9 to 16. Sound as drafted. They are counted, and child processes guard the ones that could hang. 15's stand-in is sufficient. 17 to 20. Sound. 17's match strings should be re-read against 049's branch at rebase. 049 did not change `_make`'s or `_check_tools`'s refusal text (READ, `git diff main spec/049…`).

## Findings, most severe first

1. **F1. An answered call can still start its async tool. High; blocks the build.** (Decisions 4 and 5; EXECUTED.) Decision 4 posts the wrapper under the bound's lock. On abandon, it cancels the future that `run_coroutine_threadsafe` returned. But posting is not starting. If that future is cancelled before the loop has run the post's callback, the loop still creates the task. The task's first step is scheduled before the cancel. So the tool's coroutine runs up to its first `await`, or to its end if it never awaits, after the guest was answered.
   - R1, on 3.11.14 and 3.14.2: `cf.cancel() -> True`, then the effects were `['effect before first await', 'wrapper saw CancelledError']`. A body with no `await` ran to completion.
   - E1, through the real runner with the memo's own patch: the caller's loop was busy when the tool was posted. The guest got `ToolTimeout pay_def timed out after 0.05 s` and then called `mark()`. Only then did the tool's effect run: `[('paid', 5, True)]`, where `True` means "after the guest's answer". Outcomes were `timeout` with `abandoned=True`, then `mark ok`.
   - **Failure:** `async def transfer(amount): bank.debit(amount); await audit()` (or an MCP `call_tool`, whose request can be written before its first real suspension) is posted while the embedder's loop is busy for a moment. `timeout_s` or the deadline answers the guest, which retries. Then the first transfer runs anyway. This is the security review's F2 again, now for async tools, and it breaks Decision 5's own promise.
   - **Fix:** take the start decision for an awaitable on the loop thread. The runner's wrapper does it at its first step, under the bound's lock, before it touches the tool's awaitable. If the slot is already answered, it closes the awaitable unawaited (`close()`, so no warning). Otherwise it marks the slot started. An abandon after that mark is a normal abandon and cancels the task. This also covers eager task factories (3.12+), whose first step runs inside the post's callback, still on the loop thread (INFERRED).
   - **Add a criterion:** a check-owned loop blocked on an event when the post arrives; the call answered `timeout`; then the loop released. Expect the tool body's counter at 0, the coroutine `CORO_CLOSED`, and 0 `RuntimeWarning`. Stand-in: Decision 4 as drafted (counter 1).
   - **For sync tools,** state the same rule in the same words: the check and the "started" mark are made together under the bound's lock, immediately before `t.fn(**args)`. Otherwise a check-then-call window remains (INFERRED).

2. **F2. 053 must rebase onto 056's rule, not re-decide it. Medium; write it in.** (Decision 5, criterion 5, Decision 13's CHANGELOG line; READ.) 053 never names 056 or the security review. Its Decision 5 decides F2 for sync tools ("a change to 036's behaviour"). Criterion 5's sync case and the CHANGELOG's "Changed, an answered call starts no tool" claim it too. 056 lands first and owns that rule.
   - **Failure:** two definitions of "answered, so not started" land. They can differ in whether the check is atomic with the call, and in what is recorded. The security review's fix says "skip the tool and record that". 053 says "the outcome stays the one the guest was told", with `abandoned=True` for a tool that never ran. The record then disagrees with itself, or the CHANGELOG names the change twice.
   - **Write in:** "056's rule, as landed, holds for sync tools. This spec extends it to awaitables (F1's definition) and changes nothing else about it." Drop the sync half from Decision 5, criterion 5 and the CHANGELOG, or mark it as 056's. Take 056's recording of a skipped start, whatever it is. At 053's rebase the lane checks that the two texts agree, because 056's text did not exist when this review was written.

3. **F3. The private loop can die without being closed, and then the wait never ends. Medium-low; write it in.** (Decisions 3, 6 and 8; EXECUTED R5.) Decision 3's wait ends on the wrapper's event or on `loop.is_closed()`. Two cases end `run_forever`, and with it the loop thread, while the loop is neither closed nor running: a task the tool spawned raises `KeyboardInterrupt` or `SystemExit` (the wrapper cannot catch it, because it is in another task), or a tool calls `asyncio.get_running_loop().stop()`. R5 printed: `loop thread alive False; loop closed False; running False; the wrapper's end seen False` for both.
   - **Failure:** the work thread waits forever, holding one quota slot and one `tool_threads_running` for the life of the process. Every later async call of that run is answered only at `timeout_s` or the deadline. With `deadline_s=None` and no `timeout_s`, it is never answered. Decision 8's shutdown is posted to a loop that will never run it, so the loop's selector and self-pipe are never closed.
   - **Fix:** the loop thread's target owns the loop's whole life. It wraps `run_forever` in `try`/`finally`. On any return or raise it cancels the remaining tasks, runs them down, and closes the loop (with `shutdown_asyncgens`). The wait ends when the loop is closed or its thread is dead. Add a check per case: answered `tool_error` with a fault, the thread count back, the loop closed.

4. **F4. Cancel and close must never raise or leak, including on a loop that has closed. Low-medium; write it in.** (Decisions 6 and 8; EXECUTED R3 and R4.)
   - R4: `cf.cancel()` on a post whose loop has closed returns `True` and raises nothing. But `concurrent.futures` logs "exception calling callback for <Future …>" with a traceback. Decision 8's re-cancel on a closed caller's loop would print that on the embedder's stderr.
   - R3: Decision 6's closed-loop post leaves the tool's coroutine never awaited (1 `RuntimeWarning`). Decision 5's `close()` rule covers only the answered path.
   - **Write in:** `_ToolLoop.cancel()` and `close()` skip a closed loop, catch everything (an exception from `_instance`'s `finally` would replace the call's result or its original exception), and close every awaitable they did not get to run, on every fault path.

5. **F5. Criterion 8's stand-in does not fail the way the spec says. Low.** (EXECUTED R2.) A done `Future` of another loop, awaited on a private loop, returns its value with no error: `('done', 7)` against `('pending', 'RuntimeError')`. The setter counts its 1,000 `sleep(0)` turns regardless of the tool, so it finishes long before the guest reaches its call (INFERRED: guest start-up takes far longer). Under the stand-in the tool then sees a done `Future` and answers `ok`. Only the loop-identity assertion catches it.
   - **Fix:** the setter starts counting when the tool signals that it is awaiting, and the tool records that the future was pending when awaited.

6. **F6. Criterion wording that would let a check pass or fail for the wrong reason. Low.**
   - Criterion 4: the release must be awaited without blocking the loop (an `asyncio.Event` set with `call_soon_threadsafe`, or polling). On a private loop, a `threading.Event` wait blocks it, only the first tool starts, and "started 4 times" fails for the wrong reason.
   - Criterion 3: each end fires after the tool signals it started. With F1's fix, an earlier end leaves the task never started and shows 0 `CancelledError`, by design.
   - Criterion 6's close: assert `loop.is_closed()`. A regression that ends the thread but never closes the loop leaks descriptors and passes a thread count.
   - Criterion 1: the partial binds no keyword (or binds positionally), so it does not depend on how 056 rules on bound keywords (security F1). Reword "an executor whose `submit` must not be reached … `submit` is reached, 1".

7. **F7. Failure modes the spec does not name. Low.**
   - (a) The private loop's thread cannot start (the operating system's thread limit). 036's Decision 5 makes this a `tool_error` fault, counted in and out. Say the same here.
   - (b) Decision 9: say whether the async `host=` check unwraps `partial`s and looks at an object's `__call__`, as `_is_async` does. Otherwise `host=MyAsyncHost()` still answers −2 to every frame, silently.
   - (c) An unrequested `CancelledError` while the call's `cancel` is set is recorded as a `tool_error` fault in a run named `"cancelled"`. This happens when `asyncio.run`'s shutdown cancels the `run_async` task and the runner's wrapper together (INFERRED). Answer `cancelled` when `_ended()` says so.
   - (d) Decision 6's "the call never hangs on a loop that will not run" is true only for a closed loop. A caller's loop that is stopped or blocked is bounded only by `timeout_s`, the deadline or the cancel, like a blocked sync tool. Its work thread waits until the loop runs or closes. Say so.

8. **F8. README facts to add under *Async tools*. Low; documentation.** (INFERRED.)
   - Under `run_async`, tasks an async tool spawns outlive the call (Decision 8 cancels them only on a private loop).
   - An abandoned async tool that ignores its cancel on the caller's loop keeps that loop's `asyncio.run()` from returning at shutdown, because `asyncio.run` gathers every task. An abandoned sync tool never did this: its thread is a daemon.
   - Threads from a private loop's default executor (`asyncio.to_thread`) are not counted in `tool_threads_running`.

## Constitution checks

- **§4.4:** holds. No new import, the door's frames are unchanged, and every call is gated.
- **§4.5:** holds (asyncio only; no embedder named).
- **§4.9:** holds (counts only; F5 is about correctness, not timing).
- **§4.15:** holds. No new channel, limit or default.
- **§5.2:** holds, apart from the 056 interaction, which the spec leaves unaddressed (F2). Question 90 blocks nothing.
- **§5.6:** a pre-build review is not required (no import, export, artifact or recipe change). This one was asked for, as 036's was.
- **§7:** nothing tripped. The probes are my own.

## Disposition (filled in by the author, then confirmed by the reviewer)

The author's answers are in `da7dc72`, in the spec's section "Revised against the pre-build review", and in `disposition.md` beside this file. The reviewer's check of each answer is below, and in detail under "Confirmation".

1. **F1:** fixed in Decision 4 and new criterion 5. **Confirmed** (EXECUTED C1 and E1r), with one wording gap: C-2 below.
2. **F2:** fixed in "Depends on", Decision 5, criterion 6 and the CHANGELOG. **Confirmed** against 056's uncommitted worktree code (READ).
3. **F3:** fixed in Decisions 3 and 8 and criterion 8's second check. **Confirmed** (EXECUTED C5).
4. **F4:** fixed in Decisions 4 and 8 and criteria 7 and 8. **Confirmed** (READ). One path is still missing: C-1 below.
5. **F5:** fixed in criterion 10. **Confirmed** (READ; R2's fact is now what the criterion relies on).
6. **F6:** fixed in criteria 1, 3, 4 and 8 and in the criteria preamble. **Confirmed** (READ).
7. **F7:** (a) to (d) fixed in Decisions 2, 3, 6 and 9 and criteria 1, 7 and 19. **Confirmed** (READ).
8. **F8:** all three facts added to Decision 13. **Confirmed** (READ).

## Verdict

**Ready once F1 to F4 are written in.** F5 to F8 are small text edits, best made in the same pass. The design is sound: the loops are chosen correctly, 036's bound is reused correctly, the public API is unchanged, and security F1 is not reopened. But as drafted, Decision 4 lets an answered async tool start, which is the very defect 056 fixes for sync tools, and 053 must build on 056's rule rather than decide it a second time.

## One line

Right loops, right bound, no API change; but "answered, so not started" must be decided on the loop thread at the task's first step, and on 056's terms.

## Confirmation (2026-10-18)

- **Reviewed:** `git diff faf63d7 da7dc72` on `spec/053-async-host-functions`, which changes only the spec, plus `disposition.md`. I also read spec 056's uncommitted code in `../wasi_python-056` (read only): `_Work.__call__(proceed)`, `_Bounded._proceed` and `_Bounded._abandon`.
- **Ran (EXECUTED, darwin-arm64, Python 3.11.14 and 3.14.2).** Nothing was written in any tree except this git-ignored file. The probes are in `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/5c4a788f-6229-4fb4-8a87-05b4e7e5e695/scratchpad/053-review/`:
  - `probe_c1.py` → `probe_c1.txt`: C1 (R1's scenario against the revised wrapper), C2 (a wrapper cancelled before its first step) and C3 (056's `proceed` called while holding the bound's lock);
  - `probe_c5.py` → `probe_c5.txt`: R5's two cases against the revised loop thread;
  - `scripts/probe_e2e_revised.py` → `probe_e2e_revised.txt`: E1 through the real runner, with the memo's patch amended to the revised Decision 4. It used the `faf63d7` export and the frozen set `s-f94dec535086b06c`.

### Each finding against its answer

- **F1, confirmed.** The revised Decision 4 makes the wrapper's first step decide, on the loop's thread, under the bound's lock. The abandon cancels only a task that has started, and never the posted future.
  - C1 (the busy loop, the answer arriving first): `body runs 0; coroutine CORO_CLOSED; wrapper ended True`, both for a body that awaits and for one that never does, on both Pythons.
  - E1r, through the real runner: the guest got `ToolTimeout` and called `mark()`, and the effects list stayed `[]`, with `started False`. The draft gave `[('paid', 5, True)]`. stderr was empty: no warning, no log.
  - New criterion 5, with the draft as its stand-in, would catch a regression.
- **F2, confirmed.** 056 is listed under "Depends on" and lands first. Decision 5 quotes 056's rule and defers to 056's landed text at rebase. 056's worktree code matches what 053 quotes (READ):
  - `_Work` asks `proceed` after the gate and before `t.fn`;
  - `_proceed` is `not slot.abandoned`, read under `_Bounded._lock`;
  - a skipped tool returns `failed("cancelled", "<name> was not run: its call had ended")`, which nobody reads, and the record keeps 036's `abandoned=True`.

  The sync half is out of 053: its criterion 6 covers only async tools, and its CHANGELOG defers the sync line to 056. 056's check and its call to `t.fn` are separate, so the decision is taken before the answer and the call follows it outside the lock. That is consistent with "one of two orders" and is 056's to own (INFERRED).
- **F3, confirmed.** C5 ran the revised loop-thread target: `run_forever` in a `try`, then a `finally` that cancels, runs down, runs `shutdown_asyncgens` and closes, and a wait that also ends when the thread is dead. For both of R5's cases the result was `wait ended True; wrapper's end True (CancelledError); loop closed True; thread alive False`. The wrapper's `CancelledError` comes from the run-down, which the runner did not ask for, so it is the `tool_error` fault that criterion 8 expects. asyncio itself logs "Task exception was never retrieved" for the tool's own spawned task. That log is the tool's, not the runner's cancel or close, so it does not contradict "never log". Criterion 8 asserts 0 log records only for `cancel()` and `close()` on a closed loop, which is right.
- **F4, confirmed in the text.** R4's log came from cancelling the posted future, which the runner now never does. R3's closed-loop post is covered by criterion 7 (0 `RuntimeWarning`s). One path is still missing: C-1.
- **F5 to F8, confirmed** (READ):
  - criterion 10 waits for "awaiting" and asserts that the `Future` was pending;
  - criterion 4 uses an `asyncio.Event` set through `call_soon_threadsafe`;
  - criterion 3 fires each end after "started";
  - criterion 8 asserts `is_closed()`;
  - criterion 1's partial binds nothing, and its executor sentence is fixed;
  - F7 (a) to (d) are each written in, with checks for (a) to (c);
  - the three README facts are in Decision 13.

### Two gaps left by the revision, both small

- **C-1. A wrapper cancelled before its first step never runs its `finally`. Low-medium.** (Decision 4's fourth sub-bullet; EXECUTED C2.)
  - Decision 4 says "The wrapper's `finally` closes the awaitable if it was never started. That covers a `CancelledError` thrown into the wrapper before its first statement ran." That is not so. A coroutine that has not started, when cancelled, raises at once without running any of its body, its `try`/`finally` included.
  - C2: the loop's own cancel-all reached the wrapper before its first step. Result: `its finally ran False; the posted future ended with CancelledError; RuntimeWarnings 1`.
  - **Failure:** two things cancel a wrapper before its first step: `asyncio.run`'s shutdown on the caller's loop, and the private loop's run-down. In both, the wrapper's event is never set and the tool's awaitable is never closed. So the runner warns, which Decision 4 promises it never does. And the work thread's wait ends only when the loop closes or its thread dies. That is soon in both common cases. But a caller's loop that cancels its tasks and stays open holds the work thread and its quota slot until the loop closes.
  - **Write in:** the work thread's wait also ends when the posted future is done while the slot has not started (read under the bound's lock). Then the work thread closes the awaitable and answers as Decision 6 says (`cancelled` if the run is being cancelled, a `CancelledError` fault otherwise). Add one row to criterion 7: a wrapper cancelled before its first step is answered, with 0 `RuntimeWarning`s and the work thread ended.
- **C-2. Name the one locked step; do not build it from 056's `proceed`. Low; a correctness trap.** (Decision 4's "first step" and Design; EXECUTED C3 as a model.)
  - 056's `_Bounded._proceed` takes `self._lock` itself, and that lock is a non-reentrant `threading.Lock` (READ).
  - Read literally, Decision 4 says the wrapper "takes the bound's lock and asks `proceed`", then marks itself started "still under the lock". Built that way, it deadlocks the loop's thread. C3: `returned False; thread stuck True`. Under `run_async`, that thread runs the embedder's event loop.
  - Built the other obvious way, `proceed()` and then a mark in a second acquisition, it reopens F1. An abandon in the gap sees "not started", does nothing, and the task runs uncancelled after the answer (INFERRED from Decision 4's abandon rule).
  - **Write in:** one `_Bounded` method that, in a single acquisition of the lock, checks 056's predicate (`not slot.abandoned`), and if it holds, marks the slot started and records the task, returning whether to go on. The wrapper's first step calls only that. Criterion 5's busy-loop case already catches the two-acquisition form if its abandon lands in the gap. The builder can make that certain with an injected hook between the two steps.

### Verdict on the revision

**Ready to build once C-1 and C-2 are written in.** Each is a sentence or two in Decision 4, plus one row in criterion 7. Every one of F1 to F8 is answered correctly, and the design's fixes held when I ran them (C1, C5, E1r). Neither gap needs a design change or another review round: the lane can check the two sentences, and the build review checks the code.

### One line

The revision fixes F1 to F8. It still needs a work-thread exit for a wrapper cancelled before its first step, and one named locked step instead of 056's self-locking `proceed`.
