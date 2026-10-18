# 053 — Async host functions

- **Status:** drafted 2026-10-18; awaiting its pre-build review. It changes neither the guest's
  imports nor its exports, the artifact set nor the build recipe, so §5.6 asks no review before
  build; one is asked for because it changes how the door waits, as 036's was.
- **Owner:** Clay Gendron
- **Kind:** the runner. `src/wasi_python/tools.py` (`tool()`'s refusal, `_Work`, `_Slot`,
  `_Bounded`, `_ToolHost`, a new internal `_ToolLoop`), `src/wasi_python/runner.py`
  (`run_async` passes its loop, `_check_tools`, `_checked`'s refusal of an async `host=`,
  `_tool_host`, `_instance` closes the call's loop), judge additions and a judge change in
  `tests/`, `README.md`, `CHANGELOG.md`. **Not build-class:** it touches no `scripts/`,
  `recipes/`, `downloads/SHA256SUMS` or release workflow, and not the guest package
  (`recipes/guest/host/`): the guest calls the door synchronously whatever the host does, so the
  zip, the snapshot and `MANIFEST` do not change. **It changes no line of
  `tests/public_api.txt`** (spec 049's snapshot): no name, signature, field, default or
  `stats()` key is added, removed or changed. It changes the behaviour behind three public names
  (`tool`, `run`'s and `run_async`'s `gate=` and `host=`) and their docstrings, so the README's
  generated reference changes in those entries only (Decision 12).
- **Depends on:** 036 (tools in the runner: the bound, the slot, the abandoned quota,
  `stats()["tool_threads_running"]`) and 031 (the protocol, `tool()`), landed; 015 (`run_async`,
  `cancel=`, the request's context), 030 (a cancel during a door call is named), 010 (waits end at
  the deadline) and 011 (concurrent calls share nothing), landed. **049** (the public API frozen)
  is being built in parallel; whichever lands second rebases (Decision 12).
- **Research it stands on:** `../research/2026-10-18-async-host-functions.md` (EXECUTED:
  `asyncio_probe.py` on Python 3.11.14 and 3.14.2, and `prototype_probe.py`, a throwaway patch
  that served async tools to a real guest through `run` and `run_async` on the frozen artifact set
  `s-f94dec535086b06c`); `../research/2026-10-17-the-runtime-for-agent-code.md` §3.2 (needs 5 to
  7: concurrency in the guest, async hosts, time inside the door) and §5 item 3 (the door bounded
  in time, "or an async `host` that `run_async` awaits on the caller's loop with the deadline as
  its timeout"); the owner's decisions 15 and 49 (`../decisions.md`).

## Terms

- **An async tool:** a tool whose function is a coroutine function (`async def`, a
  `functools.partial` of one, or an object whose `__call__` is `async def`), or more generally
  one whose call returns an awaitable. **An async gate** likewise.
- **The tool loop:** the asyncio event loop an async tool's awaitable runs on. Under
  `run_async`, the loop that awaits `run_async` (**the caller's loop**). Under `run`, a loop of
  the call's own on its own thread (**the private loop**).
- **The work thread:** spec 036's new daemon thread per tool call, which runs the gate, the tool
  and the result's encoding.
- **The door thread:** the thread the guest runs on, which waits beside the work thread (spec
  036's bound).

## The problem

The owner's decision 15: "an async host function awaited by the guest's door call, under the
call's deadline", with the tool protocol; decision 49 puts it in 0.1.0. Today `tool()` refuses
an `async def`, and `run` refuses a coroutine gate.

Many embedders' tools are coroutines: an MCP client session, an async HTTP client, an async
database driver (the agent-runtime memo §3.2, need 6). The README's recipe wraps each in a sync tool that posts the coroutine to the
embedder's loop and blocks on it (`run_coroutine_threadsafe(...).result(timeout=…)`). That works,
but every embedder writes it, and when the call times out or is cancelled nothing cancels the
coroutine: it runs on, unseen, with the embedder's authority (the memo, "Where things stand").
A coroutine, unlike a sync function, can be stopped: at its next `await`. The runner should
await it where it belongs and cancel it when the call ends.

## Decisions

1. **What is async: one rule.** The work thread calls the gate and the tool exactly where spec
   036 calls them. **When what a call returns is awaitable** (`inspect.isawaitable`), the
   runner awaits it on the tool loop and uses its result.
   - So `tool()` accepts an `async def`, a `partial` of one, and an object with an async
     `__call__`, and derives the schema from the hints as for a `def` (the return hint is the
     awaited value's, as Python writes it). A plain `def` that returns a coroutine (an adapter
     closing over a client) is served the same way.
   - **Why one rule, not a flag:** the memo's finding 6. `iscoroutinefunction` misses a `def`
     that returns a coroutine, and calling an `async def` runs none of its code, so calling it on
     the work thread and awaiting the result on the loop is the same as awaiting the call there.
     No `Tool` field is added, and the guest is not told: its function stays synchronous.
   - **Refused** by `tool()`, with `TypeError` naming the tool: an async generator function
     (`inspect.isasyncgenfunction`, after unwrapping `partial`s and looking at an object's
     `__call__`): "an async generator streams; protocol 1 answers each call once". Spec 031's
     Scope leaves streaming out, and an async generator object is not awaitable (finding 6), so
     without the refusal every call would be a fault.
   - `stubs()` renders an async tool as a `def`, as the guest calls it. Calling a `Tool` on the
     host (`Tool.__call__`) returns what the function returns: a coroutine for an `async def`.

2. **Where the awaitable runs: the caller's loop under `run_async`, a private loop under
   `run`.**
   - **`run_async`** reads `asyncio.get_running_loop()` when it is called, on the caller's
     thread, and the call's tools use that loop. Why: the objects an async tool uses are bound
     to the loop they were made on; a `Future` of one loop awaited on another raises
     `RuntimeError` (finding 1, case A7). The loop is free meanwhile: `run_async` only awaits
     its worker (case A1). The runner posts to that loop and never runs, stops or closes it.
   - **`run`** gives each call **its own loop, on its own daemon thread**, named
     `wasi-python-tool--loop` (the double hyphen: no tool name starts with one, so no tool thread
     `wasi-python-tool-<name>` has that name). Why not the caller's: `run` may be called with no
     loop at all, or from inside a coroutine, where its own thread blocks the loop and a coroutine
     posted to it never starts (finding 2, case A2). Why per call, not one per process: an async
     tool that blocks its loop (sync code inside an `async def`) would stall every other call's
     async tools, the starvation spec 036 refused a shared pool for (its review's finding 2) and
     spec 011's rule that concurrent calls share nothing.
   - The private loop is **started at the call's first awaitable**, under a lock of the call's
     own, so it is started once whichever work thread gets there first. A call whose gate and tools
     return no awaitable starts no loop and no thread: a call with only sync tools is exactly as
     today.
   - An embedder whose async tools need its loop's objects calls `run_async`. One that runs
     `run` on a worker thread (`asyncio.to_thread(run, …)`) gets a private loop; the README says
     so.

3. **How the door waits: spec 036's bound, unchanged, with the awaitable posted from the work
   thread.**
   - The work thread posts the awaitable to the tool loop wrapped in a coroutine of the
     runner's own (with `asyncio.run_coroutine_threadsafe`), and **waits for that coroutine's
     real end**: an event the wrapper sets in its `finally`, waited on in slices of one tick
     (`TICK_S`). If the tool loop is closed (`loop.is_closed()`) while it waits, it stops waiting
     and the call is a fault (Decision 6). Then it encodes the result, as today.
   - **Why the wrapper's end, not the posted future:** cancelling the future returned by
     `run_coroutine_threadsafe` wakes its waiter at once, before the task has ended, and a task
     that catches its `CancelledError` runs on (finding 4, case A4). Waiting on the wrapper's own
     event makes the work thread live exactly as long as the task.
   - **Why keep the work thread at all,** rather than post from the door thread: the gate and
     the result's encoding stay off the embedder's loop (a sync gate that blocks, or a large
     result to encode, never stalls it); and because the work thread lives as long as the task,
     036's abandoned quota (`MAX_ABANDONED`, 4 per call) and `stats()["tool_threads_running"]`
     cover an async tool that ignores its cancel with no new counter or limit. The cost is one
     thread start per async call, as for a sync call today.
   - **The context.** The work thread runs in a copy of the door thread's `contextvars`
     context (036); the task runs in a copy of the work thread's, made when it is posted
     (finding 3, case A3). So an async tool sees the caller's context variables, under
     `run_async` the request's (spec 015), as a sync tool does.
   - Nothing else of 036's bound changes: the ends and their order, the two-tick margin, the
     messages, the per-call quota, the slot per call.

4. **Every end cancels the task.** When the bound answers a call without its work (the tool's
   `timeout_s`; the run's deadline less two ticks; the run's `cancel` or the `run_async` task's
   cancellation; a pending Ctrl-C), it answers the guest at once, as today, and **asks the task in
   flight to cancel**, by cancelling the future `run_coroutine_threadsafe` returned, which asks
   its task to cancel on the loop's own thread (finding 4). The task gets `CancelledError` at its
   current `await`.
   - **No race between the answer and the post.** Abandoning the slot and posting the awaitable
     are both done under the bound's lock: either the task was posted first, and the abandon sees
     it and cancels it, or the abandon came first, and the work thread sees the slot answered
     and posts nothing (Decision 5).
   - **`abandoned`** keeps 036's meaning: the work had not ended when the guest was answered. A
     task cancelled at its next `await` usually ends a moment after the answer, so its outcome
     still says `abandoned=True`; its work thread then ends and frees its slot in the quota. A
     task that catches the `CancelledError` and goes on keeps its slot, as a sync tool does,
     until it ends.
   - **Why:** this is what "under the call's deadline" can mean for a coroutine. The guest is
     answered by the deadline as with any tool (036); the coroutine, which can be stopped, is
     stopped (the prototype's B3, B4 and B5).
   - **After the answer,** 036's Decision 6 holds: `timeout` lets the guest run on;
     `cancelled` stops it and the run is named `"cancelled"` (spec 030); Ctrl-C raises
     `KeyboardInterrupt` from `run`.

5. **An answered call starts nothing new.** Once the bound has answered a call, its work thread
   neither calls the tool (after a gate that returned late) nor posts an awaitable; an awaitable
   it already holds and did not post is closed (`close()`, where it has one) so no "never
   awaited" warning is printed. The outcome stays the one the guest was told.
   - This applies to sync tools too, a change to 036's behaviour: today a gate that blocks past
     the call's end and then allows still lets its tool run, unseen.
   - **Why:** the guest was told `timeout` or `cancelled`; a tool that starts afterwards is an
     effect with the embedder's authority that nobody asked for. The flag that keeps an async
     tool from being posted after the answer is the same one, so one rule is simpler than two.

6. **Faults are recorded as a sync tool's are.** What an awaitable raises follows spec 031's
   Decision 6 as the tool's own call does: `ToolDenied` crosses as `denied`, `ToolError` as
   `tool_error` with its message, and any other exception, a `BaseException` included, is a fault
   (`tool_error`, "<name> failed (internal error)", `fault` naming it). Three cases are named:
   - **`KeyboardInterrupt` and `SystemExit`** raised in the task are caught by the runner's
     wrapper. Left alone they would leave the caller's loop and surface in the embedder's own
     `asyncio.run` (finding 5, case A6), far from the call; a sync tool's are caught by `_Work`
     today.
   - **A `CancelledError` the runner did not ask for** (the caller's loop cancelling every task
     as it shuts down, or a tool that raises it itself) is a fault, `fault` beginning
     `"CancelledError"`. It is not answered `cancelled`: that kind means the run is being
     cancelled, after which the runner stops the guest (036, Decision 6), and here it is not.
   - **A closed tool loop** (posting raises `RuntimeError: Event loop is closed`, finding 5, case
     A5; or the loop closes while the work thread waits) is a fault. The call never hangs on a
     loop that will not run.
   - Nothing raises out of the frame host, as before. An async gate's faults fail closed
     (`denied`), as a sync gate's do.

7. **Async gates.** `gate=` may be async by Decision 1's rule: its awaitable is awaited on the
   tool loop, then its verdict is read as today (`None` or `True` allows; `False`,
   `ToolDenied` or `ToolError` refuses; anything else fails closed). `_check_tools` no longer
   refuses a coroutine gate. It refuses an async generator function as a gate, with `TypeError`,
   for Decision 1's reason. A sync gate with an async tool, or an async gate with a sync tool,
   each runs where its kind runs: the sync one on the work thread, the awaitable on the loop.

8. **The call's end closes its private loop, without waiting.** At every ending of a call with
   tools, a raise included, `_instance` closes the call's tool loop after the guest has stopped:
   - **A private loop:** every task on it is cancelled (a task an async tool spawned and never
     awaited included), they are awaited on the loop, then the loop stops and closes, and its
     thread ends (case A8). `run` does not wait for any of this: a task that ignores its cancel
     keeps the loop's thread alive until it ends, as an abandoned sync tool keeps its thread.
   - **The caller's loop:** only the runner's own tasks still running are asked to cancel
     (again; each was asked at its call's end). Nothing else on that loop is touched: its other
     tasks are the embedder's.
   - **`stats()["tool_threads_running"]`** counts a private loop's thread with the work
     threads, while it is alive: it is a thread the runner started for tools. So each `run` can
     leave behind at most its five work threads (036) and one loop thread.

9. **The raw door stays synchronous, and an async `host=` is refused.** `run` and `run_async`
   raise `TypeError` before any work when `host=` is a coroutine function or an async generator
   function: "host= must answer synchronously; serve an async host function as a tool
   (tools=)". The check does not import `wasi_python.tools` (spec 031: `import wasi_python`
   never imports it).
   - **Why refuse:** today an `async def` host answers every frame `HOST_FAULT` and its coroutine
     is never awaited (the memo, "Where things stand"): a silent failure, now a clear one before
     anything runs, as specs 013 and 014 do for every argument.
   - **Why not serve it:** decision 15 places the async host function "with the tool protocol".
     The raw door has no `timeout` or `cancelled` answer to give the guest, and its frames are
     opaque (§4.4). An embedder who wants an awaited, bounded, cancellable host call has it as a
     tool. A plain `def` that returns a coroutine is not detected by this check and is answered
     `HOST_FAULT`, as today.

10. **What does not change.**
    - **The guest, the protocol and the record.** Protocol 1's frames and kinds, the guest
      package, `ToolCall`, `ToolOutcome` and `ToolRecord` are unchanged; an async tool's outcome
      reads like a sync tool's.
    - **Fuel** counts only guest instructions: the same frames answered the same way spend the
      same fuel whether a tool is sync or async (through the judge's driver, as spec 036's
      criterion 17).
    - **Limits and defaults.** No new limit, default or argument. No channel opens without the
      embedder's explicit `tools=` (§4.15); the private loop is the runner's own thread, like a
      work thread, reachable only through the tools the embedder passed.
    - **Fork and exit.** No process-wide state is added: a private loop belongs to its call. A
      forked child has none (spec 015's refusal still applies); the count `_after_fork_in_child`
      resets already covers loop threads. At exit, a private loop's thread is a daemon; under
      `run_async`, the exit hook sets each call's cancel (spec 015), so its tool call is answered
      `cancelled` and its task asked to cancel.

11. **`batch` is not in this specification.** Spec 031's Decision 11 named "async tools and
    gates, and the guest's `batch` operation" for decision 15's specification. This one carries
    the first two and leaves `batch` out:
    - decision 15 asks for an async host function awaited by the door call; `batch` (several
      calls in one frame, so a guest gets concurrency) is a different feature, as useful with
      sync tools on their threads as with async ones (the agent-runtime memo §3.2, need 5);
    - it changes the guest package and so the zip: build-class, competing for the one
      build-class slot (§5.7), where this specification is not;
    - protocol 1 reserves `batch`, and an unknown operation is a clean `protocol` answer (spec
      031, Decision 7), so adding it later breaks no guest and no embedder.

    Where it goes is the order of the work, which is the owner's: question 90 in
    `../questions-for-the-owner.md`. Nothing here waits on it.

12. **The public API (spec 049).**
    - **Snapshot lines changed: none.** `tool`, `Tool`, `run`, `run_async`, `gate=`, `host=` keep
      their signatures and annotations (`gate`'s `Callable[[ToolCall], Any] | None` already
      admits an awaitable result); no field, constant, default or `stats()` key is added. No new
      name enters either `__all__`; `_ToolLoop` is internal and private by its underscore (049,
      Decision 4).
    - **Behaviour changed behind public names,** each allowed in a minor release by 049's
      Decision 8 as an addition (an argument that used to be refused is now accepted: `tool()`
      and `gate=` with an async callable), or, for `host=`, by spec 049's Decision 6 (a bad
      argument raises `TypeError`, a promised type). Before 0.1.0, the alphas may change anything
      anyway (049, Decision 8).
    - **Docstrings changed:** `tool`'s (async functions accepted, async generators refused, where
      the awaitable runs), `run`'s and `run_async`'s `tools`, `gate` and `host` entries (the
      shared text stays identical in both, 049's Decision 10). Written without specification
      numbers or internal names, as 049's Decision 10 requires, so they pass its checks whichever
      lands first.
    - **The order with 049.** If 049 lands first, this builder rebases, runs `uv run python
      tests/harness/api.py --write`, and the review checks that `tests/public_api.txt` did not
      change and that the README's generated block changed only in `tool`'s, `run`'s and
      `run_async`'s entries; it lands with `--accept-judge` as any judge change does. If this
      lands first, 049's builder writes those docstrings in its pass like any others. Either way
      049's renames (`MAX_ABANDONED` to `_MAX_ABANDONED`, `DEADLINE_MARGIN_TICKS` to
      `_DEADLINE_MARGIN_TICKS`) meet this specification's edits to `_Bounded`, and the second
      to land resolves them by name.

13. **Docs.**
    - **README, *Tools*:** a paragraph *Async tools*: an `async def` tool or gate; where it runs
      (the caller's loop under `run_async`, a loop of the call's own under `run`, so use
      `run_async` when the tool needs your loop's objects); every end cancels the task, so an
      async tool is stopped at its next `await` where a sync one is abandoned; a tool that
      catches `CancelledError` runs on and holds its slot; an async tool that blocks its loop
      delays every async tool on that loop; the private loop's thread in `tool_threads_running`.
      *Abandoned tools* says "a sync function cannot be stopped". *What `run` refuses*: drop "a
      gate that is a coroutine function"; add an async `host=` and an async generator as a tool
      or gate.
    - **The MCP recipe** becomes an `async def` tool that awaits `session.call_tool(...)`, with no
      loop argument and no `run_coroutine_threadsafe`, called through `run_async`. Run once by
      the builder against mcp's in-memory server with the version 036 used (`uv run --isolated
      --no-project --with mcp==2.3.0 …`), commands and output in the landing notes (§4.10).
    - ***From async code*:** the bullet "A door host that must await" says to serve it as an
      async tool, and keeps the raw-door bridge for a `host=` that must stay raw.
    - **CHANGELOG**, unreleased: Added, async tools and gates; Changed, an answered call starts
      no tool (Decision 5), and an async `host=` is refused.

## Intent

An embedder passes its coroutine functions as tools, as they are. The guest calls them like any
tool. Each is awaited on the embedder's loop under `run_async`, or on a loop of the call's own
under `run`, bounded by the same deadline, cancel and Ctrl-C as a sync tool, and cancelled when
its call ends. Nothing the guest sees changes.

## Design

```
src/wasi_python/tools.py     tool(): accepts async functions, refuses async generators;
                             _ToolLoop (internal): a caller's loop or a private one, started at
                               the first awaitable; run(awaitable, slot) posts a wrapper and
                               waits for its end; cancel(slot); close()
                             _Slot: the answered flag and the task posted, both under the
                               bound's lock
                             _Work: after the gate and after the tool, an awaitable result goes
                               to the loop; nothing starts once the slot is answered
                             _Bounded: each end that abandons a slot also cancels its task
                             _ToolHost(..., loop=None): owns the call's _ToolLoop; close()
src/wasi_python/runner.py    run_async passes asyncio.get_running_loop(); _check_tools accepts
                             an async gate, refuses an async generator gate; _checked refuses
                             an async host=; _tool_host passes the loop; _instance closes the
                             frame host's loop in its finally
tests/unit/test_async_tools.py           criteria 1 to 6, no artifacts
tests/unit/test_tools.py,
tests/unit/test_runner_tools.py          the judge change (criterion 17)
tests/checks/test_v1_4_embedding.py      criteria 7 to 16, the built artifact set
README.md, CHANGELOG.md
```

`_ToolHost`'s default invoke (`_inline`, used when a frame host is passed as a raw `host=`, as
031's checks do) awaits an awaitable on the frame host's private loop, without a bound, so the
same rule holds there; a frame host used that way is closed by its user (the runner closes the
ones it makes). `_tool_host` reads the loop as `c.get("tool_loop")`, so the dict spec 036's
criterion 17 builds by hand still works and gets a private loop.

## Scope

In: the above. Out:
- `batch` (Decision 11; question 90);
- an async raw `host=` (Decision 9) and async mount providers (spec 032's `FileProvider`: its
  calls are many, short and made synchronously by the guest's libc; decision 15 names the tool
  protocol);
- streaming results (async generators), progress, a tool's own access to the remaining deadline;
- trio and other loops: `run_async` is asyncio only (spec 015); under trio, `run` from a worker
  thread gives async tools a private asyncio loop;
- a process-wide ceiling on abandoned tasks (036, Decision 5's reason holds);
- any change to the guest package, the zip or the protocol.

## Acceptance criteria

Each new check is seen failing first: against today's code where the behaviour is missing, and
against the stand-in named where the property is the point. Nothing measures time. A tool that
must block waits on an event the check sets; a short `timeout_s` only chooses the outcome. Counts
are of calls, tasks, threads and outcomes; a fail-safe wait only keeps a broken build from
hanging the judge.

**Unit** (`tests/unit/test_async_tools.py`, no artifacts; the bound driven with fakes for the
ticker, `cancel` and the Ctrl-C flag, as 036's unit checks drive it, and a loop on a thread the
check owns standing for the caller's):

1. `test_async_callables_are_accepted_and_async_generators_refused`: `tool()` of an `async def`
   gives the same `descriptor()` as its `def` twin; a `partial` of one (with `name=`) and an
   object with an async `__call__` are accepted; an async generator function raises
   `TypeError` naming the tool. Through `run` and `run_async` (an executor whose `submit` must
   not be reached, artifact lookups counted), a coroutine gate passes the checks (through `run`
   the first artifact lookup is reached, 1; through `run_async` the executor's `submit` is
   reached, 1), and each of these raises with 0 lookups and 0 submits: an
   async generator gate; `host=` an `async def`; `host=` an async generator function. Seen
   failing first: today `tool()` refuses the `async def` and `run` refuses the coroutine gate,
   and the async `host=` is not refused.
2. `test_an_awaitable_is_awaited_on_the_tool_loop`: a frame host whose loop is the check's.
   An `async def` tool's answer is `ok` with its value; it ran on the loop's thread (by name)
   and saw a context variable the caller set; a `def` returning a coroutine is served the same;
   an async gate returning `False` answers `denied` and the tool's call counter stays 0; one
   returning `True` lets it run (counter 1). With no loop given, the first awaitable starts
   exactly one thread named `wasi-python-tool--loop`, three async calls later there is still
   one, and a frame host whose tools are all sync starts none.
3. `test_every_end_cancels_the_task`: with an `async def` tool that awaits an event forever
   and counts the `CancelledError`s it sees, each of the four ends (`timeout_s`, the deadline
   less two ticks, `cancel`, the Ctrl-C flag) answers its kind with `abandoned=True`; the task
   saw exactly 1 `CancelledError`; its work thread then ends (joined) and the tool-thread count
   returns to its value before. Stand-in: a bound that abandons without cancelling (the task
   sees 0, and its thread is still alive when the fail-safe join gives up).
4. `test_a_task_that_ignores_its_cancel_holds_its_slot`: an `async def` tool that catches
   `CancelledError` and waits for a release event; six calls with `timeout_s` set: four
   answered `timeout` abandoned, the fifth and sixth answered at once with the quota's message,
   the tool started 4 times; the tool-thread count is 4 above its value before until the
   release, then back. Stand-in: a work thread that waits on the posted future instead of the
   wrapper's end (finding 4: the count drops while the tasks still run, and the fifth call
   starts).
5. `test_an_answered_call_starts_nothing`: a sync gate that blocks on an event past the tool's
   `timeout_s`, then allows. The call is answered `timeout`; once the gate is released and the
   work thread joined, the tool's call counter is 0, for a sync tool and for an `async def` one,
   and no runner task was posted to the loop (0). Then a `def` tool that returns a coroutine and,
   inside its call, waits until the bound has answered (an event the check sets after the frame
   host returns): its coroutine is closed unposted (`inspect.getcoroutinestate` is
   `CORO_CLOSED`, and it never ran: its body's counter is 0), and no `RuntimeWarning` is recorded
   (`warnings.catch_warnings(record=True)`, `simplefilter("always")`, after `gc.collect()`: 0).
   Stand-in: 036's `_Work` (the sync tool's counter is 1).
6. Two checks.
   `test_faults_in_an_awaitable_stay_in_the_record`: an `async def` tool raising `ToolError`
   answers `tool_error` with its message; `ToolDenied`, `denied`; `KeyError`, a fault beginning
   `"KeyError"`; `KeyboardInterrupt` and `SystemExit`, faults beginning with their names, and
   the check's loop is still running afterwards (a later call on it answers `ok`); a tool that
   raises `asyncio.CancelledError` itself, a fault beginning `"CancelledError"`, kind
   `tool_error`; a frame host whose given loop is closed answers `tool_error` with a fault
   beginning `"RuntimeError"`, at once. Nothing raises out of the frame host in any case.
   `test_close_ends_the_calls_loop`: on a private loop, `close()` it cancels every task on it, one the tool spawned with
   `create_task` included (its counter of `CancelledError`s is 1), and its thread ends; with a
   task that ignores its cancel, `close()` returns while the thread is still alive (1 alive),
   which ends once the task is released; on the check's own loop, `close()` cancels only the
   runner's tasks, and a task the check made on that loop is still pending afterwards.

**End to end** (`tests/checks/test_v1_4_embedding.py`, the built artifact set; checks whose
defect would hang run in a child process with spec 015's 120 s fail-safe, as 036's do):

7. `test_a_guest_calls_an_async_tool_under_run`: two `async def` tools and an async gate that
   allows; the guest calls both, one result fed to `pandas.DataFrame`; stdout as expected;
   outcomes `list ok`, `call ok`, `call ok`; the tools ran on the thread named
   `wasi-python-tool--loop`; after `run` returns and the tool threads are joined, no thread of
   that name is alive and `stats()["tool_threads_running"]` is back to its value before.
8. `test_run_async_awaits_tools_on_the_callers_loop`: before `run_async`, the check makes a
   `Future` on its own loop; an `async def` tool awaits it; a coroutine of the check sets it
   after counting 1,000 turns of `await asyncio.sleep(0)`. The guest prints the value; the
   outcome is `ok`; the tool saw `asyncio.get_running_loop()` be the caller's. Stand-in: tools on
   a private loop under `run_async` (awaiting the caller's `Future` raises `RuntimeError`: the
   outcome is `tool_error` with that fault).
9. `test_a_timeout_cancels_an_async_tool`: tool A (`async def`, `timeout_s=0.05`) awaits an
   event forever; the guest catches `ToolTimeout`, then calls tool B (`async def`), which
   returns its value; stdout is A's timeout message and B's answer; outcomes A `timeout`
   abandoned, B `ok`; A's task saw exactly 1 `CancelledError`. Stand-in: the bound that does not
   cancel (0, at the fail-safe).
10. `test_the_deadline_cancels_an_async_tool` (child): under `deadline_s=3`, an `async def` tool
    with no `timeout_s` awaits forever; `run` returns; the last outcome is `timeout` with the
    message "<name> timed out at the run's deadline"; its task saw exactly 1 `CancelledError`;
    the same under `run_async`. `trapped` is not asserted (036's criterion 10's reason).
11. `test_cancelling_run_async_cancels_an_async_tool` (child): `run_async` with a one-worker
    executor; the task is cancelled once the tool has started (an event the tool sets); it
    raises `CancelledError`; the tool's task saw exactly 1 `CancelledError`; a new call on the
    same executor then completes.
12. `test_a_cancel_during_an_async_tool_is_named` (child): `run(cancel=event)`; the tool sets
    "started", the check sets the event; `trapped == "cancelled"`, `exit_code is None`,
    `fuel_used is None`, last outcome `cancelled` with `abandoned=True`; the task saw exactly 1
    `CancelledError`.
13. `test_ctrl_c_during_an_async_tool` (child, main thread): the tool sets "started", the child
    sends itself SIGINT; `run` raises `KeyboardInterrupt`; the task saw exactly 1
    `CancelledError`; the private loop's thread ends (joined) and the child exits 0.
14. `test_an_async_tool_that_ignores_its_cancel_is_bounded`: Criterion 4 end to end: six calls,
    four `timeout` abandoned, two at once, 4 starts; after `run` returns,
    `stats()["tool_threads_running"]` is 5 above its value before (four work threads and the
    private loop's thread, which `close()` could not finish); after the release and the joins it
    is back. Stand-in: `close()` that waits for the loop (the run does not return: the child's
    fail-safe).
15. `test_one_calls_blocked_loop_does_not_starve_another`: two `run` calls on two threads. A's
    `async def` tool (`timeout_s=0.05`) blocks its loop (it waits on a `threading.Event` inside
    the coroutine; the check sets it at the end) and is answered `timeout`; then B's `async def`
    tool (`timeout_s=5`, a fail-safe so the stand-in fails at once) answers `ok`. Stand-in: one
    loop for the process (B's call is answered `timeout`).
16. `test_fuel_is_exact_across_async_tool_calls`: through the judge's driver with
    `runner._tool_host(...)` as its host (036's criterion 17's way), one program of two tool
    calls spends equal fuel when its tools are `async def` and when they are their `def` twins,
    and equal fuel across two runs whose async tools await different numbers of
    `asyncio.sleep(0)`.

**The judge change and the whole:**

17. **The judge change, listed:** `tests/unit/test_tools.py`'s refusal case "an async def"
    (match "decision 15") becomes "an async generator function" (match "async generator"); in
    `tests/unit/test_runner_tools.py`'s `MISTAKES`, the coroutine gate row becomes an async
    generator gate row, and two rows are added: `host=` an `async def` and `host=` an async
    generator function, each `TypeError` matching "serve an async host function as a tool".
    No other existing check changes: every 031 and 036 check passes as it stands.
18. The README's MCP recipe, rewritten as Decision 13 says, ran once with `mcp==2.3.0` against
    mcp's in-memory server, through `run_async` (outcomes `list ok`, `call ok`, and a
    `tool_error` with the server's text for its error case); the README's first *Async tools*
    example ran as written. Commands and outputs in the landing notes.
19. If spec 049 has landed before this one: `uv run python tests/harness/api.py --check` passes
    after `--write`; `git diff tests/public_api.txt` is empty; the README block's diff touches
    only `tool`'s, `run`'s and `run_async`'s entries.
20. `ruff check` and `ruff format --check` are clean; `uv run pytest` is green with
    `--accept-judge`; lost 0; grew 0 (the artifact set does not change).

## The owner's choices

None open here. Decision 11 leaves `batch` to a later specification and asks its place in the
order of the work as question 90 (`../questions-for-the-owner.md`); nothing in this
specification waits on it.

## Landing notes

Not built.
