# 075 — tools.py small fixes

- **Status:** drafted 2026-10-19 on `spec/075-tools-small-fixes` from main `d900dd9`; reviewed
  before build the same day (`../reviews/075-tools-small-fixes-spec-2026-10-19.md`, written in
  the coordinator's scratchpad, `075-review/`, with its probes q1 to q3, and copied in by the
  lane; verdict: "ready once F1 and F2 are written in"); **revised against it 2026-10-19** (F1,
  F2, N1 and N3 written in; the section "Disposition of the pre-build review"), and rebased
  onto main `23f1c4f` (071 and 069 landed; neither touches `tools.py` or the two unit files);
  **confirmed for build 2026-10-19** (the review's Confirmation: "Confirmed for build", with two
  cosmetic points, c1 and c2, taken at the build). It changes neither the guest's imports nor
  its exports, the artifact set nor the build recipe, so §5.6 asks no review before build. One is asked for because
  Decisions 1 to 3 change the gate's fail-closed path, the control §4.4 names. A different
  agent reviews the build.
- **Date:** 2026-10-19
- **Owner:** Clay Gendron
- **Kind:** the runner, host side only; **parallel-safe**, not build-class (§5.7). It edits
  `src/wasi_python/tools.py` (`_Post`, `_ToolLoop._wrapper`, `_ToolLoop.run`, `_ToolHost`'s
  `list` branch and two private methods beside `_list_answer`), adds unit checks to
  `tests/unit/test_async_tools.py` and `tests/unit/test_tools.py`, changes one item of
  `README.md` (*Async tools*, **Faults stay in the call**) and adds one entry to `CHANGELOG.md`
  under `0.1.0a7 — unreleased`. It touches no `scripts/`, `recipes/`, `downloads/SHA256SUMS`,
  workflow or guest package, so the artifact set does not change and no rebuild is needed.
  **It changes no line of `tests/public_api.txt`** (spec 049): no public name, signature,
  field, default or docstring changes, so the README's generated reference does not change.
  New checks under `tests/` change the judge hash: **the lane accepts it with
  `--accept-judge`.** No existing check, golden output, gap or allowance is edited.
- **Depends on:** 053 (async host functions: `_ToolLoop`, the wrapper, Decisions 6 and 7),
  056 (an answered call starts nothing), 060 (the tool list encoded once, Decision 12) and 055
  (sessions share `_ToolLoop`), all landed. Spec 070's Decision 6 sent 060's N1 here; the
  lane's ruling on 070's build review (F4) added the a6 security review's F1.
- **Research it stands on:**
  - `../reviews/0.1.0a6-security-review-2026-10-18.md`, F1, with its probe
    `probes/p24_gate_generatorexit.py` and the helper's `tools-probes/a4_async_ceiling_context.log`
    case 1 (in the main tree, `build/reviews-evidence/a6-security/`);
  - `../reviews/060-a-per-run-budget-of-request-bytes-2026-10-18.md`, N1, with its P7 (a
    benchmark fact: 0.90 ms of CPU per refused `list` frame for an 18 MB list);
  - this draft's probes, EXECUTED on Python 3.14.2 in this worktree at `d900dd9`, kept in the
    main tree under `build/reviews-evidence/075-draft/`:
    - `probe_main.py` (`probe_main.out`): every gate form and exception below, on main;
    - `probe_fixed.py` (`probe_fixed.out`): the same rows against a scratch copy of `tools.py`
      with Decisions 1 and 2 applied by `apply_fix.py`;
    - `probe_backstop.py` (`probe_backstop.out`): a wrapper that ends with neither a return nor
      an error, on main and on the fixed copy;
  - the pre-build review's probes (EXECUTED there, in `075-review/probes/` with `logs/`): q1,
    thirteen kinds of awaitable handed back by a gate and by a tool on both loops (6 kinds fail
    open on main, 0 on the fix); q2, a real SIGINT against an async gate under `asyncio.run`
    and under `loop.run_until_complete`; q3, criterion 3's fault and a skipped post, on main and
    on the fix; and the mutants `m1` and `m1b`.

## Intent

Two small faults in the host's tool code, each named by a review and each left for this spec.

After it:
- a gate allows a call only when it returns `None` or `True`. An async gate that raises
  `GeneratorExit` refuses, as a sync gate already does, and the record keeps its fault;
- an async tool that raises `GeneratorExit` is a fault, not an `ok` with `None`;
- the result of any awaitable counts only if the awaitable returned;
- a tool list over the 16 MiB answer cap is refused from its length, on every `list` frame,
  without its answer being built.

## The problem

**F1 (the a6 security review).** The README says: "A gate that raises anything else refuses
too, and the record keeps its fault." Spec 053's Decision 6 says any other exception, "a
`BaseException` included, is a fault", and Decision 7 says a gate's "anything else fails
closed". That holds for a sync gate. It fails for an async gate that raises `GeneratorExit` or a
subclass (EXECUTED, `probe_main.out`):

| gate | raises | outcome on main | the tool |
|---|---|---|---|
| sync | `GeneratorExit`, a subclass | `denied`, fault recorded | not run |
| `async def`; a `def` returning a coroutine; an object with an async `__call__` | `GeneratorExit`, a subclass | **`ok`, no fault** | **ran** |
| any of the four | `KeyboardInterrupt`, `SystemExit`, `CancelledError`, `RuntimeError` | `denied`, fault recorded | not run |

The same holds under a private loop (as `run`) and a caller's loop (as `run_async`). An async
*tool* that raises `GeneratorExit` is answered `ok`, value `None`.

Why (READ, `tools.py` at `d900dd9`, lines 1727 to 1764). `_ToolLoop._wrapper` awaits the
awaitable and re-raises `GeneratorExit` without keeping it (`except GeneratorExit: raise`). Its
`finally` sets `ended`. `_ToolLoop.run` sees `ended` with no error and returns `post.value`,
still `None`. `_Work` reads `None` from a gate as "allow", and from a tool as its result.

So the async path allows by default: anything that ends the wrapper without an error reads as
a return of `None`. Only the embedder's own gate or tool code can raise `GeneratorExit` there;
a guest cannot. It is a broken promise about the embedder's control, not a way in for the guest
(the review). But "fails closed" is the gate's contract.

**N1 (spec 060's build review).** `_answer`'s `list` branch builds the whole answer
(`self._list_answer(frame_id)`, a copy of the kept array) and then measures it against
`_TOOL_RESPONSE_BYTES`. A list over the cap is built on every `list` frame only to be refused
(EXECUTED, `probe_main.out`: three refused frames, three builds). The cost is per frame, so
`max_tool_calls` bounds it, and the README is honest as written. The review called the fix
optional; spec 070's Decision 6 placed it here.

## Decisions

1. **An awaitable's result counts only if it returned** (F1, the review's first fix).
   - `_Post` gains `returned`, `False` until the wrapper sets it. The wrapper sets it on the
     statement after `post.value = await post.awaitable`, in the same `try`.
   - `_ToolLoop.run`, after its wait, checks in this order: `skipped` raises `_NotStarted`; an
     error is raised; **no `returned` raises `RuntimeError("the awaitable ended without a
     result")`**; else it returns `post.value`.
   - So the runner allows a gate's call only on a clear allow: the awaitable returned, and what
     it returned is `None` or `True`. Every other end refuses, whatever ended it.
   - *Reason:* the fault is a default, not a missing `except`. Main gives a value whenever the
     wrapper ends without an error. Catching `GeneratorExit` alone (Decision 2) fixes the case
     the review found. It leaves the default open for any other path that ends the wrapper
     with neither: today, a fault in its own first step that is a `GeneratorExit`
     (EXECUTED, `probe_backstop.out`: main gives `None`, so a gate would allow; the fix raises).
     A positive mark closes the class. It costs one attribute and one test of it.

2. **The wrapper keeps the `GeneratorExit` it re-raises** (the review's second fix, the
   helper's variant).
   - `except GeneratorExit as e: post.error = e; raise` around the await. The re-raise stays,
     so the wrapper's own close path is as it was (the review: "leave the wrapper's own close
     path as it is").
   - The work thread then raises it, and `_Work` catches it as any other `BaseException`: a
     gate's call is `denied` ("<name> was refused") with `fault` `GeneratorExit` (or
     `GeneratorExit: <text>`, or the subclass's name); a tool's is `tool_error` ("<name>
     failed (internal error)") with the same fault (EXECUTED, `probe_fixed.out`, all 16
     `GeneratorExit` rows).
   - *Reason:* spec 053's Decision 6 says the fault is recorded "with `fault` naming it". With
     Decision 1 alone the record would say `RuntimeError: the awaitable ended without a
     result`, true but not what the embedder's code raised. Both decisions together: the record
     names the cause, and the default is closed.
   - The first step's own `except GeneratorExit: raise` (around `ops.start`) is left as it is.
     That block awaits nothing, so nothing throws into it; if anything did, Decision 1 refuses.
   - Re-raising out of the task is what main does: the task holds the exception and
     `run_coroutine_threadsafe` reads it, so asyncio logs nothing (EXECUTED: `probe_fixed.out`
     ran with asyncio's debug logging and `-W always`, and shows no log line or warning).

3. **Which exceptions propagate: none.** Nothing a gate or a tool raises leaves the frame host,
   `run`, `run_async` or the caller's loop. This spec keeps spec 031's Decision 6 and spec
   053's Decisions 6 and 7 as they are, and makes the async gate obey them as the sync gate
   already does. The table, for a gate of any form, sync or async:

   | the gate | the call | the tool |
   |---|---|---|
   | returns `None` or `True` (after its awaitable returned, if any) | goes on | runs |
   | returns `False` | `denied`, no fault | not run |
   | returns anything else | `denied`, fault `TypeError: the gate returned …` | not run |
   | raises `ToolDenied` or `ToolError` | `denied`, its message, no fault | not run |
   | raises `CancelledError` while the run is being cancelled (its `cancel` set, which under `run_async` includes the task's cancellation; or, under `run` only, a Ctrl-C pending) | `cancelled` | not run |
   | raises any other exception, `Exception` or `BaseException`: `KeyboardInterrupt`, `SystemExit`, `GeneratorExit`, `CancelledError` at any other time, a custom `BaseException` | `denied`, fault naming it | not run |
   | its awaitable ends without returning (Decision 1) | `denied`, fault `RuntimeError: the awaitable ended without a result` | not run |
   | the call was answered before its awaitable started (spec 056, 053 Decision 5) | `cancelled` (unread) | not run |

   The table is what `_Work` answers. **At a deadline or a `timeout_s`** the record shows the
   bound's answer instead: the bound has already answered `timeout` and dropped the work's
   result, so a `CancelledError` the gate then meets (the runner cancels a started task at
   every end) is `denied` in `_Work` but the record says `timeout`, `abandoned` (the review's
   N3; `_ended` names a deadline "deadline", not "cancelled").

   Each one, and why it stays in the call:
   - **`KeyboardInterrupt`.** It stays in the call, and how a real Ctrl-C reaches a gate
     depends on the entry point (the review's F2).
     - **Under `run`,** the guest runs on the main thread, and `_deferred_ctrl_c` turns Ctrl-C
       into a flag. A gate runs on a work thread or on the private loop's thread, so a real
       Ctrl-C never lands in its code: a `KeyboardInterrupt` there is the gate's own `raise`.
       The bound reads the flag, answers `cancelled`, and `run` raises `KeyboardInterrupt`
       after the call (spec 036, Decision 6). That path does not change.
     - **Under `run_async`,** the runner defers nothing: the guest runs on a worker thread, so
       `_deferred_ctrl_c` passes straight through and no Ctrl-C flag is ever pending. Ctrl-C
       belongs to the embedder's loop. Under `asyncio.run` its handler cancels the main task,
       `run_async` sets the call's `cancel`, the gate meets `CancelledError` and the tool does
       not run (EXECUTED by the review's q2, `logs/q2_*_asyncio.run-sleepy.log`); the call is
       answered `cancelled`, the table's `CancelledError` row (READ: `_cancelling` and the
       bound; `run_async` raises on its cancel, so q2 saw no record to show the kind).
     - **The edge, EXECUTED** (the review's q2, a real SIGINT, `logs/q2_main_busy.log` and
       `logs/q2_fixed_busy.log`, the same on main and on the fix): an embedder that runs its
       loop on the main thread itself (`loop.run_until_complete`), with Python's default
       handler, while an async gate's own code runs. The gate raises `KeyboardInterrupt`; the
       call is `denied` with fault `KeyboardInterrupt`; the guest gets `ToolDenied` and runs
       on; `run_async` returns normally; the embedder never sees its Ctrl-C. Spec 053 decided
       this (a `KeyboardInterrupt` in the wrapper's task stays in the call), and this spec
       keeps it: refusing is the closed direction. The README now says what it costs
       (Decision 8): the Ctrl-C is consumed, and the run goes on to its own ends.
     - Raised out of a work thread instead, it would end that thread with a traceback; out of a
       task on the caller's loop, it would leave the embedder's `asyncio.run`, far from the call
       (spec 053, finding 5, case A6).
   - **`SystemExit`.** A gate's `sys.exit()` is not the embedder's exit. On a work thread it
     would end the thread silently; on the caller's loop it would leave `asyncio.run`. So it
     is a fault (053, Decision 6).
   - **`CancelledError`.** Answered `cancelled` only when the run is being cancelled, as the
     bound would answer it a slice later; else a fault (053, Decision 6, the review's F7 c).
     Either way the tool does not run.
   - **`GeneratorExit`.** A fault, by Decisions 1 and 2: this spec's fix.
   - The sync gate already gives every row (EXECUTED, `probe_main.out`). Nothing in `_Work`'s
     gate block changes.

4. **An async tool gets the same fix.** It shares `_ToolLoop.run` with the gate, so Decisions 1
   and 2 apply to it unchanged: `GeneratorExit` or a subclass from an `async def` tool, a `def`
   returning a coroutine or an object with an async `__call__` is `tool_error`, "<name> failed
   (internal error)", fault naming it. *Reason:* the review's table; the record must not say
   `ok` for a tool that raised (its asset 4, the integrity of the result).

5. **The checks are unit checks over the frame host,** with spec 053's stand-ins: `_ToolLoop()`
   for `run`'s private loop and `_ToolLoop(caller.loop)`, a running loop on a thread the check
   owns, for `run_async`'s caller's loop (`tests/unit/test_async_tools.py`'s `_host` and
   `CallerLoop`). *Reason:* the fault is entirely host side; the guest calls the door the same
   way whatever the gate does, and spec 053's own fault checks are unit checks of this kind. A
   guest check would add an artifact set and minutes to show the same rows.

6. **An oversized tool list is refused from its exact length, on every frame, before the answer
   is built** (060's N1).
   - The kept array moves into `_tools_array()`: encoded at the first need, kept, as spec 060's
     Decision 12 encodes it (once per frame host, with `_encode`'s settings).
   - `_list_length(frame_id)` gives the exact length of the answer `_list_answer` would build,
     from parts: `{"v":`, the version, `,"id":`, the id as JSON (`null` or its digits),
     `,"ok":true,"tools":`, the array and `}`.
   - The `list` branch refuses with `too_large` and the same message, "the tool list is over the
     16 MiB cap", when that length is over `_TOOL_RESPONSE_BYTES`; only otherwise does it call
     `_list_answer`. Nothing measures the built answer again.
   - *Why exact, per frame:* the id's length moves the answer's. `null` is 4 bytes, an id 1 to
     16 digits. A list that fits with id 9 is one byte over with id 10. So a verdict remembered
     at the first `list` frame (the review's other fix) would answer a later frame wrongly,
     either way. An exact length keeps today's boundary to the byte: an answer of exactly
     16 MiB is sent, one byte more is refused.
   - *Why one measure:* a second `len(answer)` after building would repeat the rule in two
     places, and hide a wrong `_list_length` that undercounts. A check holds `_list_length(i)
     == len(_list_answer(i))` instead (criterion 5).
   - *Why at all,* when the review said it can wait: it is two lines in the file this spec
     already changes, and spec 070 placed it here.

7. **Nothing else changes.** Protocol 1's bytes, every answer's kind and message, `ToolOutcome`,
   `ToolRecord`, the public API and its README reference, fuel (only guest instructions count),
   the zip, the snapshot and `MANIFEST`. The one README change is Decision 8's clause.

8. **The README and the CHANGELOG.**
   - *Async tools*, **Faults stay in the call** names `GeneratorExit` beside `KeyboardInterrupt`,
     `SystemExit` and `CancelledError`, and says that from a gate any of them refuses the call
     (`denied`), as from a sync gate. *Reason:* the item lists the `BaseException`s by name;
     leaving out the one that failed would leave the reader to guess.
   - The same item gains one clause (the review's F2): on a loop you run yourself on the main
     thread without `asyncio.run`, a Ctrl-C that lands inside a gate's or a tool's own code
     refuses that call and is not raised again; `asyncio.run` turns Ctrl-C into a cancel of the
     call. *Reason:* without it an operator's Ctrl-C can vanish, and the run goes on to its
     deadline (60 s by default). The behaviour stays; the embedder is told what it costs.
   - `CHANGELOG.md`, under `0.1.0a7 — unreleased`, one **Fixed** entry naming both items,
     citing the a6 security review's F1 and spec 060's N1.

## Design

```
src/wasi_python/tools.py   _Post: a `returned` slot, False until set (Decision 1)
                           _ToolLoop._wrapper: `post.returned = True` after the await;
                             `except GeneratorExit as e: post.error = e; raise` (Decision 2)
                           _ToolLoop.run: after `skipped` and `error`, no `returned` raises
                             RuntimeError("the awaitable ended without a result") (Decision 1)
                           _ToolHost._tools_array(), _ToolHost._list_length(frame_id);
                             _list_answer builds from _tools_array(); the list branch
                             refuses from _list_length before it builds (Decision 6)
tests/unit/test_async_tools.py   criteria 1 to 3
tests/unit/test_tools.py         criteria 4 and 5
README.md                        Async tools, Faults stay in the call (Decision 8)
CHANGELOG.md                     0.1.0a7 — unreleased: one Fixed entry
```

No other function changes. `_Work`'s gate and tool blocks are untouched: they already treat a
raised `BaseException` as the table says.

## Scope

In: Decisions 1 to 8. Out, each with its reason:
- **The first step's `except GeneratorExit: raise`.** Left as it is (Decision 2); Decision 1
  covers it.
- **`_Work`'s gate block.** It is right for every row once `_ToolLoop.run` raises; changing it
  (for example, refusing every awaited `None`) would refuse a gate that allows by returning
  `None`, which the README promises works.
- **A real Ctrl-C raised into a gate's or a tool's code on a main-thread loop the embedder runs
  itself,** outside `asyncio.run` (EXECUTED by the review's q2: the call is refused, the Ctrl-C
  consumed). Spec 053 decided that a `KeyboardInterrupt` in the wrapper's task stays in the call
  (Decision 3 here); that decision is not reopened. The README says what it costs (Decision 8).
  Under `run` this cannot happen: the Ctrl-C is a flag, and gates run off the main thread.
- **A Ctrl-C in the `select` of a `run_until_complete` loop,** which leaves the call's work
  thread waiting until the embedder closes its loop (the review's N2, q2): spec 053's F7 (d), as
  decided.
- **The `list` answer's copy into guest memory,** per frame and bounded by `max_tool_calls`, as
  the README says (spec 060's Scope).
- **Any change to `scripts/`, `recipes/`, the guest package or the workflow.**

## Acceptance criteria

Each check is written before the code it holds. Each is run on main's code first, and each
stand-in is applied alone to a scratch copy and run by node id. The builder's evidence goes in
the main tree under `build/reviews-evidence/075-build/`.

1. **`test_a_gate_refuses_unless_it_returns_an_allow`** (unit, `tests/unit/test_async_tools.py`),
   parametrized over four gate forms (a sync `def`; an `async def`; a `def` returning a
   coroutine; an object with an async `__call__`), two loops (`_ToolLoop()` and
   `_ToolLoop(caller.loop)`), and these raises: `GeneratorExit()`, a subclass of
   `GeneratorExit`, `GeneratorExit("text")`, `KeyboardInterrupt()`, `SystemExit(3)`,
   `asyncio.CancelledError()` (no cancel set) and a custom `BaseException` subclass. Two more
   gate forms carry the `GeneratorExit()` and subclass raises only (the review's N1, q1): an
   `async def` that awaits a `Future` of the running loop given `set_exception(GeneratorExit())`
   (or the subclass); and a `def` returning an object whose `__await__` is a bare iterator whose
   `__next__` raises it. Each row:
   - the answer is `denied`, "effect was refused";
   - the outcome's `fault` begins with the raised type's own name (`GeneratorExit: text` for the
     third);
   - the tool ran 0 times;
   - the caller's loop thread is alive and its loop open;
   - no `RuntimeWarning` was raised (`warnings.catch_warnings(record=True)`).

   And, as its allow rows, the three async forms returning `None` and returning `True` each give
   `ok` and run the tool once, under both loops.

   *Seen failing on main:* 26 rows give `ok`, and the tool runs: the 18 with an async form and a
   `GeneratorExit` (3 forms × 3 raises × 2 loops; `probe_main.out` shows 12 of them) and the 8
   of the two extra forms (2 forms × 2 raises × 2 loops; the review's q1, `logs/q1_main.log`).
   The other rows pass on main; they pin what must not move.
   *Stand-ins:* S1, main's code (26 failed). S2, Decision 1 alone, without Decision 2's
   `post.error = e` (the 26 fail on the fault's name: `RuntimeError: the awaitable ended…`).
   S3, `_Work` refuses every `None` an awaitable gives, in place of Decisions 1 and 2 (the
   allow rows with `None` fail, and the 26 have no fault). S4, Decision 2's `except` catching
   `GeneratorExit` itself but not a subclass, written as `except GeneratorExit as e: if type(e)
   is GeneratorExit: …` (the 10 subclass rows fail).

2. **`test_an_async_tool_that_raises_generatorexit_is_a_fault`** (unit, same file), over the
   three async tool forms, the two loops and `GeneratorExit()` and a subclass: the answer is
   `tool_error`, "boom failed (internal error)", `fault` begins with the type's name, and no
   `RuntimeWarning`.
   *Seen failing on main:* all 12 rows give `ok` with value `None` (`probe_main.out`, 4 rows).
   *Stand-ins:* S1 (12 failed); S2 (12 fail on the fault's name).

3. **`test_the_tool_loop_gives_a_value_only_when_the_awaitable_returned`** (unit, same file).
   - `_ToolLoop.run(coro, ops)`, under both loops, with an `ops` whose `start` raises
     `GeneratorExit` (so the wrapper ends with neither a return nor an error), raises
     `RuntimeError` "the awaitable ended without a result"; the coroutine is closed
     (`inspect.getcoroutinestate` is `CORO_CLOSED`) and never ran; no `RuntimeWarning`.
   - Through the frame host, with `T._Bounded._begin` patched to raise `GeneratorExit`: an async
     gate's call is `denied`, "effect was refused", with `fault` exactly
     **`RuntimeError: the awaitable ended without a result`**, and the tool ran 0 times. Not
     `GeneratorExit`: the first step's `except GeneratorExit: raise` does not record it, on
     purpose (Decision 2), so Decision 1's backstop is what refuses (the review's F1, EXECUTED
     there, `logs/q3_fixed.log`).
   - **A skipped post keeps its order** (the review's F1). `_ToolLoop.run(coro, ops)`, under both
     loops, with an `ops` whose `start` returns `False`, raises `_NotStarted`, not
     `RuntimeError`; the coroutine is `CORO_CLOSED` and never ran; no `RuntimeWarning`.

   *Seen failing on main:* `run` returns `None` (`probe_backstop.out`), and the gate allows
   (the review's q3, `logs/q3_main.log`: `ok`, the tool run). The skipped-post row passes on
   main; it pins Decision 1's order.
   *Stand-ins:* S1 (fails the first two parts); S5, Decision 2 alone, without Decision 1 (fails
   the first two parts); **S11, the `skipped` test moved after the `returned` test** in
   `_ToolLoop.run` (fails the skipped-post row: `RuntimeError`, not `_NotStarted`). Today S11
   survives every other unit check (the review's `m1b`, 260 passed), so this row is its only
   catch.

4. **`test_an_oversized_tool_list_is_refused_before_it_is_built`** (unit,
   `tests/unit/test_tools.py`). `T._ToolHost._list_answer` is wrapped to count its calls, and
   `_TOOL_RESPONSE_BYTES` patched to 100. A host with three tools answers `list` frames with
   ids 1 and 2 and one with no id:
   - each is `too_large`, "the tool list is over the 16 MiB cap", with the frame's id (or
     `null`);
   - each outcome is `op == "list"`, `tool is None`, `outcome == "too_large"`;
   - `_list_answer` was called **0** times.

   With the cap restored, two `list` frames call it twice and are answered `ok`.
   *Seen failing on main:* `_list_answer` is called 3 times (`probe_main.out`, "N1").
   *Stand-ins:* S1 (3 calls); S6, `_list_length` computed as `len(self._list_answer(frame_id))`
   (3 calls).

5. **`test_the_tool_list_cap_is_exact_for_each_id`** (unit, same file). For a host with three
   tools, `L(i)` is `len(T._encode({"v": 1, "id": i, "ok": True, "tools": descriptors}))`,
   computed with the real `_encode`.
   - `host._list_length(i) == len(host._list_answer(i))` for `i` in `None`, 0, 9, 10 and
     `2**53 - 1`.
   - With the cap patched to `L(9)`, on one host, frames in this order: id 9 is `ok` (byte for
     byte `L(9)` long), id 10 is `too_large`, no id is `too_large`, id 0 is `ok`.
   - With the cap patched to `L(9) - 1`: id 9 and id 0 are `too_large`.

   *Seen failing on main:* it passes on main, which measures the built answer; it pins the
   boundary the new code must keep, and its stand-ins show it bites.
   *Stand-ins:* S7, `>=` for `>` (id 9 at the cap is refused); S8, the id's length left out
   (`_list_length` counts a fixed one digit: id 10 and no id pass and are sent over the cap);
   S9, the verdict remembered at the first `list` frame (id 10 is answered `ok` after id 9);
   S10, the envelope one byte short (id 10 passes).

6. **The documents.** The README's **Faults stay in the call** names `GeneratorExit`, says a
   gate's fault refuses, and carries the Ctrl-C clause, as Decision 8 says. `CHANGELOG.md` has
   one **Fixed** entry under `0.1.0a7 — unreleased`. The existing checks of specs 053 and 060
   (`test_faults_in_an_awaitable_stay_in_the_record`, `test_the_tool_list_is_encoded_once` and
   the rest of both files) pass unchanged.

7. **Nothing else moves.** The fast tier (`uv run pytest -m "not slow" -n 3`) while building,
   then the full judge once (`uv run pytest -n 6`, or `-n 3` beside another judge), in the
   worktree, without `--accept`: lost 0, grew 0, the judge change named (the two unit files).
   `ruff check` and `ruff format --check` are clean on `src tests recipes/guest`.
   `uv run python tests/harness/api.py --check` exits 0: `tests/public_api.txt` and the README's
   reference do not change.

## Disposition of the pre-build review

The review: `075-tools-small-fixes-spec-2026-10-19.md`, written in the coordinator's scratchpad
(`075-review/`, its probes q1 to q3 and mutants beside it) and copied to `context/reviews/` by
the lane. Verdict: "ready once F1 and F2 are written in". It found no fail-open path on the fix
across 13 kinds of awaitable, where main fails open on 6 (24 rows).

- **F1 (low), criterion 3's fault and a skipped-post row.** Written in. Criterion 3 states the
  exact fault, `RuntimeError: the awaitable ended without a result`, and why it is not
  `GeneratorExit`. It gains the skipped-post row (`ops.start` returns `False`: `_NotStarted`,
  the coroutine closed) under both loops, with stand-in S11, the review's `m1b`.
- **F2 (low), the Ctrl-C edge.** Written in. Decision 3's `KeyboardInterrupt` bullet is split
  by entry point: the flag is `run`'s alone; under `run_async` Ctrl-C reaches the call only as
  its cancel. The edge is relabelled EXECUTED, citing q2, there and in the Scope. The table's
  `CancelledError` row scopes "a Ctrl-C pending" to `run`. Decision 8 and criterion 6 add the
  README clause the review gives.
- **N1, two more awaitable rows.** Written into criterion 1: a `Future` given
  `set_exception(GeneratorExit())` and a bare `__await__` iterator, each with `GeneratorExit` and
  a subclass, under both loops (8 rows that fail on main). The stand-in counts move with them.
- **N2, a Ctrl-C in a `run_until_complete` loop's `select`.** No change: spec 053's F7 (d), as
  decided; named in the Scope.
- **N3, the table at a deadline.** Written in, below the table: the record shows the bound's
  `timeout`, not `_Work`'s `denied`.
- **N4, the backstop pinned through the first step only.** No change: as the review says, that
  is the one path left, and criterion 3 pins it there.
- **N5 and N6.** No change: Decision 6 reads correctly, and the constitution checks hold.

## Landing notes

Not built. This specification waits for its pre-build review's confirmation.
