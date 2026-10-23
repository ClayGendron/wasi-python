# Pre-build review of 075 — tools.py small fixes, 2026-10-19

- **Reviewer:** a fresh agent. I wrote none of 075. I wrote the 0.1.0a6 security review, whose F1 this spec closes, so I know the defect. I have no stake in this fix's design.
- **Under review:** `context/specifications/075-tools-small-fixes.md` on `spec/075-tools-small-fixes`, commit `3cd1e96`, over main `d900dd9`. The draft's probes are in the main tree at `build/reviews-evidence/075-draft/`.
- **Read:** the spec in full. In `tools.py` at `3cd1e96`: `_Post`, `_ToolLoop` (`run`, `_wrapper`, `close`), `_Ops`, `_Bounded._ended`, `_Work`'s gate and tool blocks, `_cancelling`, `_list_answer`, and `_answer`'s `list` branch. In `runner.py`: `run_async`'s cancel path, `_deferred_ctrl_c`, `_ctrl_c_watched` and `_ctrl_c_now`. Spec 053's Decisions 6 and 7, and its F7. The README's **Faults stay in the call**. The draft's `apply_fix.py` and its three probe outputs.
- **How I ran things:** `git archive 3cd1e96` twice into the scratch folder: `main/` as it stands, and `fixed/`, with the draft's own `apply_fix.py` applied (Decisions 1 and 2, the diff shown in `logs/`). Each was `uv sync`ed, and every probe ran with `uv run python -I` in each. Guest runs used the frozen set `build/sets/s-1a7242a7a8b518f4`, read only; the `.cwasm` cache went to the scratch folder. I touched no git tree. My probes are in `probes/`, and their logs in `logs/`, beside this file.
- **No judge run.** Nothing is built yet. On the fixed copy, the three unit files the spec touches or depends on (`test_async_tools.py`, `test_runner_tools.py`, `test_tools.py`) gave 232 passed (EXECUTED, `logs/fixed_unit_baseline.log`). So the draft's fix breaks no existing unit check.

Labels: **EXECUTED** (I ran it), **READ**, **INFERRED** (reasoned, not run).

## Short version

The design is right. A positive mark (`returned`) closes the class, not just the one exception. Recording `GeneratorExit` (Decision 2) keeps the cause in the record. I tried hard to find a call that goes through without an explicit allow, and on the fixed copy found none. Thirteen kinds of awaitable were each handed back by a gate and by a tool, on both loops.

- **On main,** six kinds fail open. All are in the `GeneratorExit` family, but not all are a `raise` in a coroutine. A `Future` given `set_exception(GeneratorExit())` fails open too, and so does a bare `__await__` iterator.
- **On the fixed copy,** none fails open. The only allows are real returns of `None` or `True`.

The BaseException table matches spec 053's Decisions 6 and 7. I executed the "INFERRED" Ctrl-C edge with a real SIGINT. It behaves exactly as the spec says: the call is refused, and the embedder's Ctrl-C is consumed. That should be said in the README item this spec already edits (F2).

Two small findings, both about wording and criteria. No design change is needed.

## Does any path still let a call through without an explicit allow?

### q1: thirteen kinds of awaitable (EXECUTED, `probes/q1_no_default_allow.py`, `logs/q1_main.log`, `logs/q1_fixed.log`)

Each was returned by an async gate and awaited by an async tool, under `_ToolLoop()` (as `run`) and `_ToolLoop(caller_loop)` (as `run_async`), through a real `_ToolHost` with a `_Bounded`.

| the awaitable | main, gate | main, tool | fixed, gate | fixed, tool |
|---|---|---|---|---|
| `__await__` iterator whose `__next__` raises `GeneratorExit` | **ok, tool ran** | **ok, `None`** | denied, `GeneratorExit` | tool_error, `GeneratorExit` |
| the same, a `GeneratorExit` subclass | **ok, ran** | **ok, `None`** | denied, `SubExit` | tool_error, `SubExit` |
| `@types.coroutine`: yield, then raise `GeneratorExit` | **ok, ran** | **ok, `None`** | denied | tool_error |
| `async def`: `await sleep(0)`, then raise `GeneratorExit` | **ok, ran** | **ok, `None`** | denied | tool_error |
| `Future.set_exception(GeneratorExit())`, awaited | **ok, ran** | **ok, `None`** | denied | tool_error |
| `Future.set_exception(SubExit())`, awaited | **ok, ran** | **ok, `None`** | denied | tool_error |
| `Future.set_exception(KeyboardInterrupt())` | denied | tool_error | denied | tool_error |
| a cancelled `Future` | denied, `CancelledError` | tool_error | same | same |
| a task that cancels itself | denied, `CancelledError` | tool_error | same | same |
| returns a coroutine object | denied, `TypeError: the gate returned coroutine…` | tool_error, `_NotJSON` | same | same |
| raises `StopIteration` | denied, `RuntimeError: coroutine raised StopIteration` | tool_error | same | same |
| a closed coroutine | denied, `RuntimeError: cannot reuse…` | tool_error | same | same |
| a `Future` of a closed loop | denied, `RuntimeError` | tool_error | same | same |
| `__await__` that returns `None` at once | ok (a real return of `None`) | ok, `None` | same | same |

Every row is the same under both loops. Afterwards the caller's loop thread ended cleanly. The only warning was the expected "never awaited" for the coroutine object a gate returned.

**Fail-open rows:** six kinds × two roles × two loops = 24 on main; 0 on the fixed copy.

### The other paths, read against the fixed code (READ, INFERRED)

- **`_ToolLoop.run`'s wait** can end only with `ended` set, or by raising: the C-1 branch raises `CancelledError`, and the closed-loop branch raises `RuntimeError` unless `ended` is set. With Decision 1, a value is given only when `returned` is set. The `Event` orders the loop thread's writes before the work thread's reads.
- **A real `KeyboardInterrupt` on a main-thread loop.**
  - If it lands between `post.value = await …` and `post.returned = True`, it is inside the same `try`. It is recorded, and the call is refused.
  - If it lands in the outer `finally` before `ended.set()`, the future is done with `ended` unset. The C-1 branch raises `CancelledError`, so the call is refused (or answered `cancelled`). Closed, though the fault text "cancelled before it started" would be wrong for a tool that had run. This needs a signal at one exact bytecode; INFERRED, not run.
- **`_Work`'s gate block** allows only on `None` or `True`. A truthy non-bool (`1`, `numpy.True_`) is refused with a fault (READ, `tools.py:1512-1516`).
- **`_NotStarted` and `proceed()`** both refuse (spec 056). They are unchanged.
- **By contract, `None` allows.** A gate that falls off its end without returning allows. That is the README's promise, and the spec's Scope rightly keeps it. It is the one "allow" that is not written as `return True`. It is deliberate, and outside this spec.

So, with Decisions 1 and 2: a call goes through only when the gate's code, or its awaitable, returned `None` or `True`, and the call was still live at `proceed()`.

## The BaseException table, against spec 053 and Ctrl-C

**Against 053 (READ).** Each row of Decision 3's table is what spec 053's Decisions 6 and 7 already require:
- `ToolDenied` and `ToolError` cross;
- any other exception, a `BaseException` included, is a fault;
- an unrequested `CancelledError` is `cancelled` only while `_ended()` says "cancelled";
- an async gate fails closed.

The only row that changes is `GeneratorExit`, which is the fix. The deadline is not a "being cancelled" end in `_ended`. So a `CancelledError` at a deadline is `denied` in `_Work`. But by then the bound has already answered `timeout` and dropped the work's result. The record shows `timeout` (READ). The table is accurate for `_Work`; one clause saying what the record shows there would help a reader (N3).

**Ctrl-C, executed with a real SIGINT** (`probes/q2_ctrl_c_main_thread_loop.py`; the guest calls one tool; the gate is async; `deadline_s=8`; logs `logs/q2_*`). The results were identical on main and on the fixed copy:

| the embedder | where the SIGINT lands | result |
|---|---|---|
| `asyncio.run`, the gate awaits `sleep(3)` | the loop | `asyncio.run`'s handler cancels the main task; `run_async` sets the call's `cancel`; the gate sees `CancelledError`; the tool does not run; the embedder gets `KeyboardInterrupt`. The table's CancelledError row, EXECUTED. |
| `asyncio.run`, the gate busy-loops for 3 s | the gate's code (the handler only schedules a cancel) | the gate finishes and allows. The cancel is processed after it. The tool ran in 4 of 6 runs (`logs/q2_asyncio_run_repeats.log`). That is the documented side of spec 056's race: the gate allowed before the call was answered, and the README says blocking async code holds the loop. Not a fail-open. |
| `loop.run_until_complete`, Python's default handler, the gate busy-loops | **the gate's code** | **the gate raises `KeyboardInterrupt`; the call is `denied`, fault `KeyboardInterrupt`; the guest gets `ToolDenied` and exits 0; `run_async` returns normally; the embedder never sees the Ctrl-C.** This is the spec's INFERRED edge, now EXECUTED, exactly as Decision 3 says. |
| `loop.run_until_complete`, the gate awaits `sleep(3)` | the loop's `select` | the embedder gets `KeyboardInterrupt` at once. The `run_async` coroutine is left pending. The call's work thread waits until the embedder closes its loop: alive 9 s later, past the deadline, and gone after `loop.close()`. Python prints "Task was destroyed but it is pending!" at exit. This is spec 053's F7 (d), as decided; not 075's (N2). |

- **Under `run`** (READ): the guest runs on the main thread and `_deferred_ctrl_c` turns SIGINT into a flag. Gates and tools run on work threads or the private loop's thread, so a real Ctrl-C never lands in their code. The bound answers `cancelled`, and `run` raises after the call. Unchanged by 075.
- **Under `run_async`** the runner defers nothing. The guest runs on a worker thread, so `_deferred_ctrl_c` passes straight through and `_ctrl_c_now()` is always false. Ctrl-C belongs to the embedder's loop, and reaches the call only as `run_async`'s cancel. Decision 3's KeyboardInterrupt bullet describes the `run` path only (F2).

## Do the stand-ins catch each regression?

I traced each stand-in against the criteria (READ, INFERRED unless named):

- **S1** (main): fails criteria 1 to 4, as the draft's probes show (EXECUTED by the draft; re-run by my q1 and q3).
- **S2** (Decision 1 without `post.error = e`): the 18 `GeneratorExit` rows give `denied` with `RuntimeError: the awaitable ended…`, failing criterion 1's "fault begins with the raised type's name". Criterion 2 fails the same way. Caught.
- **S3** (`_Work` refuses every awaited `None`): the allow rows with `None` fail. The 18 are denied with no fault. Caught.
- **S4** (only exact `GeneratorExit` recorded): a subclass is re-raised unrecorded, and Decision 1 gives `RuntimeError`. The six subclass rows fail on the fault's name. Caught.
- **S5** (Decision 2 without Decision 1): q3 shows main giving `ok` with the tool run when `_begin` raises `GeneratorExit`, so criterion 3 fails. Caught (EXECUTED, `logs/q3_main.log`).
- **S6 to S10** (the list): the equality row `_list_length(i) == len(_list_answer(i))` catches any under- or over-count. The ordered frames (9, 10, none, 0) catch a remembered verdict, a fixed one-digit id, `>=` for `>` and an envelope one byte short. Each bites by construction.
- **Not caught, and equivalent today:**
  - **M1b, the `skipped` test moved after `returned`** (EXECUTED, `logs/m1b_skipped_after_returned.log`): 260 passed across `test_async_tools.py`, `test_runner_tools.py`, `test_tools.py`, `test_runner_sessions.py`, `test_runner_async.py` and `test_runner_cancel.py`, and no planned criterion has a skipped post. A skipped post would then answer `denied` with a `RuntimeError` fault, not `_NotStarted`. That cannot be seen today: `_begin` refuses only an abandoned slot, whose result is dropped. But Decision 1 states the order, and a direct unit row costs four lines (F1). My q3 shows the fixed copy raises `_NotStarted` and closes the coroutine (EXECUTED, `logs/q3_fixed.log`).
  - **`returned = True` set just before the await**, after the first step: with Decision 2 in place, nothing after the first step ends without an error, so no criterion can tell. This is equivalent; criterion 3 pins the backstop through the first step, the one path left (N4).
  - **The first mutant I tried, `returned` tested before both `skipped` and `error`,** is caught by the existing `test_faults_in_an_awaitable_stay_in_the_record` (EXECUTED, `logs/m1_returned_before_skipped.log`).

## Findings

### F1. Criterion 3 needs its exact fault, and a skipped-post row. Low; write in before building (EXECUTED)

- **The fault.** The second part says an async gate's call is "`denied` with that fault" when `_Bounded._begin` raises `GeneratorExit`. Decision 2 leaves the first step's `except GeneratorExit: raise` unrecorded, on purpose. So the record holds **`RuntimeError: the awaitable ended without a result`**, not `GeneratorExit` (EXECUTED, `probes/q3_criterion3_fault.py`, `logs/q3_fixed.log`). "That fault" could be read either way, and a builder who asserts `GeneratorExit` would chase a failure the design intends. Write the string.
- **The order.** Add a row: `_ToolLoop.run(coro, ops)`, with an `ops` whose `start` returns `False`, raises `_NotStarted` (not `RuntimeError`), and the coroutine is `CORO_CLOSED`. Under both loops. Name its stand-in: S11, the `skipped` test moved after the `returned` test. Today that mutant survives 260 unit checks and every planned criterion (EXECUTED, `m1b`).

### F2. The Ctrl-C edge is now EXECUTED; say so, and tell the embedder. Low; write in before building (EXECUTED)

- **Relabel.** Decision 3's KeyboardInterrupt bullet and the Scope call the main-thread-loop edge INFERRED. My q2 ran it with a real SIGINT. The behaviour is the one the spec describes: the call is `denied` with fault `KeyboardInterrupt`, the run returns normally, and the embedder never sees its Ctrl-C (`logs/q2_main_busy.log`, `logs/q2_fixed_busy.log`). Cite it.
- **Scope the flag to `run`.** The bullet explains Ctrl-C through `_deferred_ctrl_c` and the bound's flag, and the table's CancelledError row says "or a Ctrl-C pending". Both are true only under `run`. Under `run_async` the runner defers nothing, and Ctrl-C reaches the call only as `run_async`'s cancel. Under `asyncio.run` that is the CancelledError row, which I executed (`logs/q2_*_asyncio.run-sleepy.log`). One sentence each.
- **The README.** Decision 8 already edits **Faults stay in the call**. Add one clause: on a loop you run yourself on the main thread without `asyncio.run`, a Ctrl-C that lands inside a gate's or a tool's own code refuses that call, and is not raised again; `asyncio.run` turns Ctrl-C into a cancel of the call. Without it, an operator's Ctrl-C can vanish, and the run goes on to its deadline (60 s by default). Refusing stays the closed direction; this only tells the embedder what it costs.

## Notes

- **N1. Add two awaitable rows to criterion 1** (optional). `Future.set_exception(GeneratorExit())` and a bare `__await__` iterator that raises it fail open on main by other mechanisms than a `raise` in a coroutine body (q1). The fix covers them by construction, because the `await` raises them. One row each would keep it so.
- **N2. A Ctrl-C in the `select` of a `run_until_complete` loop** leaves the call's work thread waiting until the embedder closes its loop (q2, sleepy). This is spec 053's F7 (d), decided, and it does not change here.
- **N3. The table at a deadline.** A `CancelledError` there is `denied` in `_Work`, but the record shows the bound's `timeout`, because the work's result is dropped. One clause would stop a reader expecting `denied` in the record.
- **N4. The backstop is pinned through the first step only.** After Decision 2, no path after the first step ends without an error. So `returned` set just before the `await` would pass every criterion. This is equivalent today; criterion 3 is the right and only place to pin it.
- **N5. Decision 6 (the list cap)** reads correctly. The id is 0 to `_MAX_ID` = 2**53 − 1 (16 digits), or `null`; `type(...) is int` keeps out `bool`. The version is `PROTOCOL`. If a later protocol echoes the frame's version, `_list_length` must follow; the equality row would catch a drift. The array is still encoded once per frame host, as spec 060 accepted.
- **N6. Constitution.** Host side only, with no import, export, artifact or recipe change (§4.4, §4.6). Parallel-safe. No default loosened (§4.15): the change only turns allows into refusals. §7: nothing tripped.

## Verdict

**Ready once F1 and F2 are written in.** Both are changes to wording and to criterion 3. No decision changes. Decisions 1 and 2 close every fail-open path I could find, on both loops: 24 on main, 0 on the draft's fix. The BaseException table matches spec 053. The Ctrl-C edge behaves as the spec says, and the README should say so too.

## One line

The `returned` mark plus a recorded `GeneratorExit` closes the async gate's default-allow for every awaitable I tried; write criterion 3's exact fault and a skipped-post row, and tell the embedder that a Ctrl-C landing in a gate on a self-run main-thread loop is consumed, then build.

## Confirmation (2026-10-19)

The same reviewer read `git diff c9c9740..9a2561e` in the -075 worktree. That is the revision `9a2561e`, rebased onto main `23f1c4f`; the draft I reviewed is now `c9c9740`. The diff touches only the specification. I touched no git tree.

**Each item (READ, checked against my probes' logs):**

- **F1: written in.**
  - Criterion 3's second part now states the fault exactly, `RuntimeError: the awaitable ended without a result`, and why it is not `GeneratorExit`. That matches `logs/q3_fixed.log`.
  - The skipped-post row is there: `ops.start` returns `False`; `_ToolLoop.run` raises `_NotStarted`, not `RuntimeError`; the coroutine is `CORO_CLOSED`; under both loops. That matches `logs/q3_fixed.log`.
  - S11 is named, and its effect is right: with `skipped` tested after `returned`, a skipped post has neither `returned` nor an error, so it raises `RuntimeError`.
  - "S1 and S5 fail the first two parts, the skipped row passes on main" is right too: `logs/q3_main.log` shows the skipped post raising `_NotStarted` on main.
- **F2: written in.**
  - The `KeyboardInterrupt` bullet is split by entry point. Under `run`, the flag, and gates run off the main thread. Under `run_async`, nothing is deferred, and Ctrl-C reaches the call as its cancel.
  - The edge is labelled EXECUTED, citing `q2_*_busy.log`, in Decision 3 and in the Scope. The table's `CancelledError` row scopes "a Ctrl-C pending" to `run`.
  - Decision 8 and criterion 6 carry the README clause as I gave it. N2 is named in the Scope.
- **N1: written in.** Criterion 1 has the two extra gate forms (a `Future` given `set_exception(GeneratorExit())`, and a bare `__await__` iterator), each with `GeneratorExit()` and a subclass, under both loops. I checked the new counts:
  - 2 forms × 2 raises × 2 loops = 8 rows, all failing open on main (`logs/q1_main.log`);
  - 18 + 8 = 26 failing on main, so S1, S2 and S3 each see 26;
  - S4's subclass rows are 6 + 4 = 10.
  - On the fix these rows give `denied` with faults `GeneratorExit` and `SubExit`, and no `RuntimeWarning` (`logs/q1_fixed.log`).
- **N3: written in.** At a deadline or a `timeout_s`, the record shows the bound's `timeout`, `abandoned`, not `_Work`'s `denied`. That agrees with `_ended` (READ) and with the a6 helper's `a1` log (`timeout`, abandoned `True`).
- **N2, N4, N5, N6:** answered as I suggested (no change).

**The rebase (EXECUTED: `git diff --stat d900dd9 23f1c4f`).**
- `src/wasi_python/tools.py`, `tests/unit/test_async_tools.py` and `tests/unit/test_tools.py` are unchanged, so the spec's line references and my probes still hold.
- `runner.py` moved with spec 071, but only around wasmtime's trap-signal handlers (SIGSEGV, SIGILL, SIGFPE). Its one `run_async` hunk is a docstring. `_deferred_ctrl_c`, `_ctrl_c_now`, `run_async`'s cancel path and `_tool_host` are untouched, so F2's account is still accurate.
- The README's **Faults stay in the call** item is unchanged and still needs Decision 8's edit. `CHANGELOG.md` already has `0.1.0a7 — unreleased`.

**Nothing new is wrong.** Two cosmetic points for the builder, neither a condition:

- **c1.** The `run_async` bullet labels "the call is answered `cancelled`" as EXECUTED by q2. q2 showed the gate meeting `CancelledError` and the tool not running. `run_async` raises on cancel, so no record came back to show the outcome kind. The `cancelled` label follows from `_cancelling` and the bound (READ). One word would make it exact.
- **c2.** A few prose lines run past 100 columns: the Status line (line 9) and criterion 6 (line 380). Reflow them when convenient.

**Confirmed for build.**
