# 053 — Async host functions

- **Status:** **landed 2026-10-18** (accepted on `13934b0` as `8185e5f`; the build review, `../reviews/053-async-host-functions-2026-10-18.md`, confirmed it; see the Landing notes' last part). Before landing: built 2026-10-18; build-reviewed the same day ("lands once F1 is fixed"); F1 fixed and N1 to N3 answered (Landing notes, "Revised against the build review"); confirmed. Drafted 2026-10-18; reviewed before build the same day (`../reviews/053-async-host-functions-spec-2026-10-18.md`, written in the lane's evidence folder, `build/reviews-evidence/053-review/`, and copied in by the lane; verdict: "ready once F1 to F4 are written in", F5 to F8 small text edits); revised against it (the section "Revised against the pre-build review" says where each finding went); **confirmed for build 2026-10-18 with conditions C-1 and C-2, written in; builds after 056 lands** (the review's Confirmation: C-1 in Decisions 3 and 4 and criterion 7; C-2 in Decision 4 and the Design). It changes neither the guest's imports nor its exports, the artifact set nor the build recipe, so §5.6 asks no review before build. One was asked for because it changes how the door waits, as 036's was.
- **Owner:** Clay Gendron
- **Kind:** the runner. `src/wasi_python/tools.py` (`tool()`'s refusal, `_Work`, `_Slot`, `_Bounded`, `_ToolHost`, a new internal `_ToolLoop`), `src/wasi_python/runner.py` (`run_async` passes its loop, `_check_tools`, `_checked`'s refusal of an async `host=`, `_tool_host`, `_instance` closes the call's loop), judge additions and a judge change in `tests/`, `README.md`, `CHANGELOG.md`. **Not build-class:** it touches no `scripts/`, `recipes/`, `downloads/SHA256SUMS` or release workflow, and not the guest package (`recipes/guest/host/`). The guest calls the door synchronously whatever the host does, so the zip, the snapshot and `MANIFEST` do not change. **It changes no line of `tests/public_api.txt`** (spec 049's snapshot): no name, signature, field, default or `stats()` key is added, removed or changed. It changes the behaviour behind three public names (`tool`, and `run`'s and `run_async`'s `gate=` and `host=`) and their docstrings, so the README's generated reference changes in those entries only (Decision 12).
- **Depends on:**
  - 036 (tools in the runner: the bound, the slot, the abandoned quota, `stats()["tool_threads_running"]`) and 031 (the protocol, `tool()`), landed; 015 (`run_async`, `cancel=`, the request's context), 030 (a cancel during a door call is named), 010 (waits end at the deadline) and 011 (concurrent calls share nothing), landed.
  - **056** (the 0.1.0a4 security review's findings; `../wasi_python-056`, `spec/056-the-a4-security-reviews-findings`), **which lands first**. Its Decision 3 fixes that review's F2 ("a gate that allows late still runs the tool after its call timed out or was cancelled"). It owns the rule "a call answered before its tool starts never starts it" for sync tools. This specification rebases onto 056 and extends that rule to awaitables (Decision 5). 056's fix of the same review's F1 (a `partial`'s bound keywords) sits in `tool()`'s shared path, which an async tool's schema also takes.
  - **049** (the public API frozen) is being built in parallel; whichever lands second rebases (Decision 12).
- **Research it stands on:**
  - `../research/2026-10-18-async-host-functions.md` (EXECUTED: `asyncio_probe.py` on Python 3.11.14 and 3.14.2, and `prototype_probe.py`, a throwaway patch that served async tools to a real guest through `run` and `run_async` on the frozen artifact set `s-f94dec535086b06c`);
  - the pre-build review's probes (EXECUTED there, `probe_r.py`, `probe_r5.py`, `scripts/probe_e2e.py`):
    - R1: a post cancelled before the loop ran it still starts the tool;
    - R2: a done `Future` of another loop awaits without error;
    - R3 and R4: posting to a closed loop, and cancelling a post on one;
    - R5: a private loop whose thread ends with the loop unclosed;
    - E1: an answered call's async tool running after the guest's answer, through the real runner;
  - `../research/2026-10-17-the-runtime-for-agent-code.md` §3.2 (needs 5 to 7: concurrency in the guest, async hosts, time inside the door) and §5 item 3 (the door bounded in time, "or an async `host` that `run_async` awaits on the caller's loop with the deadline as its timeout");
  - the owner's decisions 15 and 49 (`../decisions.md`).

## Terms

- **An async tool:** a tool whose function is a coroutine function (`async def`, a `functools.partial` of one, or an object whose `__call__` is `async def`). More generally, a tool whose call returns an awaitable. **An async gate** likewise.
- **The tool loop:** the asyncio event loop an async tool's awaitable runs on.
  - Under `run_async`, it is the loop that awaits `run_async` (**the caller's loop**).
  - Under `run`, it is a loop of the call's own, on its own thread (**the private loop**).
- **The work thread:** spec 036's new daemon thread per tool call. It runs the gate, the tool and the result's encoding.
- **The door thread:** the thread the guest runs on. It waits beside the work thread (spec 036's bound).
- **The wrapper:** the runner's own coroutine around an awaitable, posted to the tool loop. **Its first step** is the first statement it runs, on the loop's thread.
- **`proceed`:** spec 056's question, asked under the bound's lock: has this call not been answered yet? (056's `_Bounded._proceed` takes the lock itself.)
- **`_start`:** this specification's one locked step (Decision 4): 056's predicate, the started mark and the task, in one acquisition of the bound's lock.

## The problem

The owner's decision 15: "an async host function awaited by the guest's door call, under the call's deadline", with the tool protocol. Decision 49 puts it in 0.1.0. Today `tool()` refuses an `async def`, and `run` refuses a coroutine gate.

Many embedders' tools are coroutines: an MCP client session, an async HTTP client, an async database driver (the agent-runtime memo §3.2, need 6).

The README's recipe wraps each in a sync tool. That tool posts the coroutine to the embedder's loop and blocks on it (`run_coroutine_threadsafe(...).result(timeout=…)`). That works, but every embedder has to write it. Worse, when the call times out or is cancelled, nothing cancels the coroutine: it runs on, unseen, with the embedder's authority (the memo, "Where things stand").

A coroutine, unlike a sync function, can be stopped at its next `await`. The runner should await it where it belongs, never start it once its call is answered, and cancel it when the call ends.

## Decisions

1. **What is async: one rule.** The work thread calls the gate and the tool exactly where spec 036 calls them. **When what a call returns is awaitable** (`inspect.isawaitable`), the runner awaits it on the tool loop and uses its result.
   - So `tool()` accepts an `async def`, a `partial` of one, and an object with an async `__call__`. It derives the schema from the hints as for a `def`. The return hint is the awaited value's, as Python writes it.
   - A plain `def` that returns a coroutine (an adapter closing over a client) is served the same way.
   - **Why one rule, not a flag:** the memo's finding 6. `iscoroutinefunction` misses a `def` that returns a coroutine. Calling an `async def` runs none of its code, so calling it on the work thread and awaiting the result on the loop is the same as awaiting the call there. When an awaitable is said to start is Decision 4's. No `Tool` field is added. The guest is not told: its function stays synchronous.
   - **Refused** by `tool()`, with `TypeError` naming the tool: an async generator function (`inspect.isasyncgenfunction`, after unwrapping `partial`s and looking at an object's `__call__`), with the message "an async generator streams; protocol 1 answers each call once". Spec 031's Scope leaves streaming out. An async generator object is not awaitable (finding 6), so without the refusal every call would be a fault.
   - `stubs()` renders an async tool as a `def`, as the guest calls it.
   - Calling a `Tool` on the host (`Tool.__call__`) returns what the function returns: a coroutine for an `async def`.

2. **Where the awaitable runs: the caller's loop under `run_async`, a private loop under `run`.**
   - **Under `run_async`.** It reads `asyncio.get_running_loop()` when it is called, on the caller's thread, and the call's tools use that loop.
     - Why: the objects an async tool uses are bound to the loop they were made on. A pending `Future` of one loop awaited on another raises `RuntimeError` (finding 1, case A7; the review's R2).
     - The loop is free meanwhile: `run_async` only awaits its worker (case A1).
     - The runner posts to that loop. It never runs, stops or closes it.
   - **Under `run`.** Each call gets **its own loop, on its own daemon thread**, named `wasi-python-tool--loop`. No tool name starts with a hyphen, so no tool thread `wasi-python-tool-<name>` can have that name.
     - Why not the caller's loop: `run` may be called with no loop at all. Or it may be called from inside a coroutine, where its own thread blocks the loop, and a coroutine posted to that loop never starts (finding 2, case A2).
     - Why one per call, not one per process: an async tool that blocks its loop (sync code inside an `async def`) would stall every other call's async tools. That is the starvation spec 036 refused a shared pool for (its review's finding 2), and it breaks spec 011's rule that concurrent calls share nothing.
   - The private loop is **started at the call's first awaitable**, under a lock of the call's own, so it is started once whichever work thread gets there first.
     - A call whose gate and tools return no awaitable starts no loop and no thread. A call with only sync tools is exactly as today.
     - **If the loop's thread cannot start** (the operating system's thread limit), the call is a `tool_error` fault, "<name> failed (internal error)", with `fault` naming the exception. The thread is counted in before `start()` and out again if `start()` raises, as spec 036's Decision 5 does for a work thread.
   - An embedder whose async tools need its loop's objects calls `run_async`. One that runs `run` on a worker thread (`asyncio.to_thread(run, …)`) gets a private loop. The README says so.

3. **How the door waits: spec 036's bound, unchanged, with the awaitable posted from the work thread.**
   - **The post and the wait.** The work thread posts the wrapper to the tool loop with `asyncio.run_coroutine_threadsafe`. It then **waits for the wrapper's real end**: an event the wrapper sets in its `finally`, waited on in slices of one tick (`TICK_S`). Once the wrapper has ended, the work thread encodes the result, as today.
   - **Four things end the wait:**
     1. the wrapper's event;
     2. the posted future being done while the slot has not started, read under the bound's lock (the Confirmation's C-1): the wrapper was cancelled before its first step, so its body, its `finally` included, never ran and never will;
     3. the tool loop being closed (`loop.is_closed()`);
     4. for a private loop, its thread no longer being alive.

     After the second, third and fourth, the work thread closes the tool's awaitable if it never started (`close()`, where it has one, so no "never awaited" warning) and answers as Decision 6 says: after the second, `cancelled` if the run is being cancelled, else a fault beginning `"CancelledError"`; after the third and fourth, a fault. The wait never depends on a loop's selector staying open.
   - **Why the wrapper's end, not the posted future.** Cancelling the future that `run_coroutine_threadsafe` returns wakes its waiter at once, before the task has ended. And a task that catches its `CancelledError` runs on (finding 4, case A4). Waiting on the wrapper's own event makes the work thread live exactly as long as the task.
   - **The private loop's thread owns the loop's whole life** (the review's F3).
     - Its target is `loop.run_forever()` in a `try`. Its `finally`, on any return or raise, does four things in order: cancels every task still on the loop; runs them down on the loop (a `gather` with `return_exceptions=True`); runs `loop.shutdown_asyncgens()`; and, in an inner `finally`, closes the loop. It catches everything, so the loop is closed whatever went wrong.
     - So the loop still ends closed when a tool stops it (`asyncio.get_running_loop().stop()`), or when a task the tool spawned raises `KeyboardInterrupt` or `SystemExit` out of `run_forever`. The wrapper cannot catch either, since that task is not its own. In both cases the review's R5 saw the thread end with the loop neither closed nor running.
     - The waiting work thread then sees the loop closed or the thread dead.
     - A private loop that has ended is not started again for that call. The call's later awaitables are faults at once ("the call's tool loop has stopped"). A tool that stops loops would stop the next one too.
     - A task that ignores its cancel during the run-down keeps the thread alive until it ends, as Decision 8 says.
   - **A caller's loop that is stopped or blocked** is neither closed nor the runner's to watch. Such a call is bounded only by 036's ends (its `timeout_s`, the deadline, the cancel, Ctrl-C), like a blocked sync tool. Its work thread waits until the loop runs again or closes, holding one slot of the abandoned quota (the review's F7 d).
   - **Why keep the work thread at all,** rather than post from the door thread:
     - the gate and the result's encoding stay off the embedder's loop, so a sync gate that blocks, or a large result to encode, never stalls it;
     - because the work thread lives as long as the task, 036's abandoned quota (`MAX_ABANDONED`, 4 per call) and `stats()["tool_threads_running"]` cover an async tool that ignores its cancel, with no new counter or limit.

     The cost is one thread start per async call, as for a sync call today.
   - **The context.** The work thread runs in a copy of the door thread's `contextvars` context (036). The task runs in a copy of the work thread's, made when it is posted (finding 3, case A3). So an async tool sees the caller's context variables (under `run_async`, the request's, spec 015), as a sync tool does.
   - Nothing else of 036's bound changes: the ends and their order, the two-tick margin, the messages, the per-call quota, the slot per call.

4. **An awaitable starts at the wrapper's first step, and every end cancels a started task.**
   - **Posting is not starting** (the review's F1; EXECUTED there).
     - R1, on 3.11.14 and 3.14.2: the post's future was cancelled before the loop ran the post's callback. The loop still made the task and ran the coroutine up to its first `await`, or to its end if it had none.
     - E1, through the real runner with the memo's own patch: the guest was answered `ToolTimeout`, and then the tool's effect ran.
     - So the start of an awaitable is decided **on the loop's thread, at the wrapper's first step**. Deciding it at the post is too early.
   - **The first step: one named method, one acquisition of the lock** (the Confirmation's C-2). `_Bounded` gains one method, `_start(slot, task) -> bool`. In a single acquisition of the bound's lock it checks 056's predicate (`not slot.abandoned`, the call not yet answered) and, if that holds, marks the slot started and records `task` in the slot; it returns whether to go on. The wrapper's first statement, before it touches the tool's awaitable, calls only `_start(slot, asyncio.current_task())`.
     - It must not be built from 056's `_proceed`. `_proceed` takes the lock itself, and the lock is a plain, non-reentrant `threading.Lock`: calling it while holding the lock deadlocks the loop's thread, which under `run_async` is the embedder's event loop (the Confirmation's C3: "thread stuck True"). And `_proceed` followed by a mark in a second acquisition reopens F1: an abandon in the gap sees "not started", cancels nothing, and the task runs after the answer.
     - If `_start` returns `False`, the wrapper closes the awaitable unawaited (`close()`, where it has one) and ends. The awaitable never started.
     - Otherwise it awaits the awaitable.
     - The wrapper's `finally` closes the awaitable if it was never started, on any path through its body. A wrapper cancelled before its first statement runs no part of its body, its `finally` included (the Confirmation's C2, EXECUTED: "its finally ran False; … 1 `RuntimeWarning`"); that case is the work thread's to finish, by Decision 3's second end of the wait.
     - The same holds with an eager task factory (Python 3.12 and later), whose first step runs inside the post's callback. That is still on the loop's thread, and still the wrapper's first statement (INFERRED).
     - The work thread may also ask 056's `_proceed` before posting, outside the lock, to save a post. `_start`'s answer is the one that decides.
   - **Every end cancels a started task.** The bound answers a call without its work at any of 036's ends: the tool's `timeout_s`; the run's deadline less two ticks; the run's `cancel` or the `run_async` task's cancellation; a pending Ctrl-C. It answers the guest at once, as today. Then, under the same lock as its abandon, it reads the slot:
     - if the wrapper has started, the bound asks the recorded task to cancel, with `loop.call_soon_threadsafe(task.cancel)`. The task gets `CancelledError` at its current `await`;
     - if the wrapper has not started, there is nothing more to do: the wrapper will see the answer at its first step.

     So exactly one of two orders holds for an awaitable, as 056's Decision 3 says for a sync tool. Either the call was answered first, and the awaitable never runs. Or it started first, and it is cancelled at its next `await`.
   - **The runner never cancels the posted future.** On a loop that has closed, that logs "exception calling callback for <Future …>" with a traceback on the embedder's stderr (the review's R4).
   - **Cancel and close never raise, log or warn** (the review's F4).
     - They skip a closed loop (`loop.is_closed()`).
     - They catch every exception, including a `RuntimeError` from a loop that closes between the check and the call. An exception from `_instance`'s `finally` would replace the call's result or its original exception.
     - On every fault path, each awaitable the runner did not get to run is closed: a post refused by a closed loop (the review's R3: 1 `RuntimeWarning` otherwise), a loop that ended, and a call answered first.
   - **`abandoned`** keeps 036's meaning, as 056 restates it: the call's gate or its tool ran on after the guest was answered.
     - A task cancelled at its next `await` usually ends a moment after the answer, so its outcome says `abandoned=True`. Its work thread then ends and frees its slot in the quota.
     - A task that catches the `CancelledError` and goes on keeps its slot, as a sync tool does, until it ends.
     - An awaitable skipped at its first step is recorded as 056 records a skipped tool (Decision 5).
   - **Why:** this is what "under the call's deadline" can mean for a coroutine. The guest is answered by the deadline, as with any tool (036). The coroutine, which can be stopped, is stopped (the prototype's B3, B4 and B5). An awaitable whose call was answered before it started never starts.
   - **After the answer,** 036's Decision 6 holds. `timeout` lets the guest run on. `cancelled` stops it, and the run is named `"cancelled"` (spec 030). Ctrl-C raises `KeyboardInterrupt` from `run`.

5. **An answered call starts nothing: spec 056's rule, extended to awaitables.**
   - **For sync tools, the rule is 056's, as landed.** Its Decision 3, as drafted in its worktree: `_Work` asks `proceed` "once the gate has allowed, or at once with no gate, and before the tool starts". A skipped tool returns an unread `cancelled` answer. "The record is not changed": the outcome already says `abandoned=True`. This specification does not re-decide that rule, its check or its record.
   - **For an async tool's function call,** 056's check already applies. Calling `t.fn(**args)` only makes the coroutine; when `proceed` says no, the function is never called and no coroutine exists.
   - **For an awaitable** (a tool's or a gate's), the start is Decision 4's wrapper first step, `_start`, which checks the same predicate as `proceed` and marks the start in the same acquisition of the lock. A skipped awaitable is recorded exactly as 056 records a skipped tool: an unread `cancelled` answer from the work thread, and no change to the record. An async gate's awaitable follows the same rule: a gate that has not started when its call is answered never starts.
   - **The rebase check.** 056 had no commit when this was written (the review's F2). At 053's rebase, the lane checks that 056's landed text still has this shape: a check made under the bound's lock, right before the tool's call; a skip that leaves the record unchanged. If it differs, 056's text governs. This specification's awaitable half then follows it in the same terms, and the lane records the difference in the landing notes rather than deciding the rule again.
   - **Why:** the guest was told `timeout` or `cancelled`. A tool that starts afterwards is an effect with the embedder's authority that nobody asked for (the security review's F2's failure scenario: an approval that arrives late, and then `transfer(amount)` runs). The review's E1 showed the same failure for an awaitable that is posted but not yet started.

6. **Faults are recorded as a sync tool's are.** What an awaitable raises follows spec 031's Decision 6, as the tool's own call does:
   - `ToolDenied` crosses as `denied`;
   - `ToolError` crosses as `tool_error`, with its message;
   - any other exception, a `BaseException` included, is a fault (`tool_error`, "<name> failed (internal error)", with `fault` naming it).

   Nothing raises out of the frame host, as before. An async gate's faults fail closed (`denied`), as a sync gate's do. Four cases are named:
   - **`KeyboardInterrupt` and `SystemExit`** raised in the wrapper's task are caught by the wrapper. Left alone, they would leave the caller's loop and surface in the embedder's own `asyncio.run`, far from the call (finding 5, case A6). A sync tool's are caught by `_Work` today. (Raised in a task the tool spawned, they are Decision 3's ended loop.)
   - **A `CancelledError` the runner did not ask for.** This happens when the caller's loop cancels every task as it shuts down, or when a tool raises it itself.
     - If, at that moment, the bound's ends say the run is being cancelled (its `cancel` is set, or a Ctrl-C is pending), the call is answered `cancelled`, as the bound would answer it a slice later (the review's F7 c). That is the case when `asyncio.run`'s shutdown cancels the `run_async` task and the wrapper together.
     - Otherwise it is a fault, with `fault` beginning `"CancelledError"`. It is not answered `cancelled`, because that kind means the run is being cancelled, after which the runner stops the guest (036, Decision 6), and here it is not.
   - **A closed tool loop.** Posting raises `RuntimeError: Event loop is closed` (finding 5, case A5), or the loop closes while the work thread waits. Either is a fault, and the awaitable is closed unrun (Decision 4).
   - **A private loop that ended** (Decision 3) is a fault.

   Under all four the call never hangs on a loop that will not run again. A caller's loop that is merely stopped or blocked is Decision 3's last case.

7. **Async gates.** `gate=` may be async, by Decision 1's rule.
   - Its awaitable is awaited on the tool loop, with Decision 4's start rule. Then its verdict is read as today: `None` or `True` allows; `False`, `ToolDenied` or `ToolError` refuses; anything else fails closed.
   - `_check_tools` no longer refuses a coroutine gate. It refuses an async generator function as a gate, with `TypeError`, for Decision 1's reason.
   - A sync gate with an async tool, or an async gate with a sync tool, each runs where its kind runs: the sync one on the work thread, the awaitable on the loop.

8. **The call's end closes its private loop, without waiting.** At every ending of a call with tools, a raise included, `_instance` closes the call's tool loop after the guest has stopped.
   - **A private loop.** `close()` asks the loop to stop, with `loop.call_soon_threadsafe(loop.stop)`. The loop's thread then does Decision 3's run-down: it cancels every task on the loop (a task an async tool spawned and never awaited included), runs them down, shuts down the async generators, and closes the loop. Then the thread ends (case A8).
     - `close()` skips a loop already closed or a thread already ended.
     - `run` does not wait for any of this. A task that ignores its cancel keeps the loop's thread alive until it ends, as an abandoned sync tool keeps its thread.
   - **The caller's loop.** Only the runner's own started tasks still running are asked to cancel, again: each was asked at its call's end. A closed loop is skipped. Nothing else on that loop is touched; its other tasks are the embedder's.
   - `close()` never raises, logs or warns (Decision 4).
   - **`stats()["tool_threads_running"]`** counts a private loop's thread with the work threads, while it is alive: it is a thread the runner started for tools. So each `run` can leave behind at most its five work threads (036) and one loop thread. Threads a tool starts itself (a private loop's default executor, through `asyncio.to_thread`) are not counted.

9. **The raw door stays synchronous, and an async `host=` is refused.**
   - `run` and `run_async` raise `TypeError` before any work when `host=` is a coroutine function or an async generator function. The message: "host= must answer synchronously; serve an async host function as a tool (tools=)".
   - The check reads `host=` as `tool()`'s check reads a tool: it unwraps `partial`s and, for an object that is not a function, looks at its class's `__call__` (the review's F7 b). So `host=MyAsyncHost()` is refused too.
   - The check does not import `wasi_python.tools` (spec 031: `import wasi_python` never imports it).
   - **Why refuse:** today an `async def` host answers every frame `HOST_FAULT`, and its coroutine is never awaited (the memo, "Where things stand"). That is a silent failure. It becomes a clear one before anything runs, as specs 013 and 014 do for every argument.
   - **Why not serve it:** decision 15 places the async host function "with the tool protocol". The raw door has no `timeout` or `cancelled` answer to give the guest, and its frames are opaque (§4.4). An embedder who wants an awaited, bounded, cancellable host call has it as a tool.
   - A plain `def` that returns a coroutine is not detected by this check. It is answered `HOST_FAULT`, as today.

10. **What does not change.**
    - **The guest, the protocol and the record.** Protocol 1's frames and kinds, the guest package, `ToolCall`, `ToolOutcome` and `ToolRecord` are unchanged. An async tool's outcome reads like a sync tool's.
    - **Fuel** counts only guest instructions. The same frames answered the same way spend the same fuel whether a tool is sync or async (through the judge's driver, as spec 036's criterion 17).
    - **Limits and defaults.** No new limit, default or argument. No channel opens without the embedder's explicit `tools=` (§4.15). The private loop is the runner's own thread, like a work thread, reachable only through the tools the embedder passed.
    - **Fork and exit.**
      - No process-wide state is added: a private loop belongs to its call.
      - A forked child has none (spec 015's refusal still applies). The count `_after_fork_in_child` resets already covers loop threads.
      - At exit, a private loop's thread is a daemon.
      - Under `run_async`, the exit hook sets each call's cancel (spec 015), so its tool call is answered `cancelled` and its started task asked to cancel.

11. **`batch` is not in this specification.** Spec 031's Decision 11 named "async tools and gates, and the guest's `batch` operation" for decision 15's specification. This one carries the first two and leaves `batch` out, for three reasons:
    - decision 15 asks for an async host function awaited by the door call. `batch` (several calls in one frame, so a guest gets concurrency) is a different feature, as useful with sync tools on their threads as with async ones (the agent-runtime memo §3.2, need 5);
    - it changes the guest package and so the zip. That makes it build-class, competing for the one build-class slot (§5.7), where this specification is not;
    - protocol 1 reserves `batch`, and an unknown operation gets a clean `protocol` answer (spec 031, Decision 7). So adding it later breaks no guest and no embedder.

    Where it goes is the order of the work, which is the owner's to decide: question 90 in `../questions-for-the-owner.md`. Nothing here waits on it.

12. **The public API (spec 049).**
    - **Snapshot lines changed: none.** `tool`, `Tool`, `run`, `run_async`, `gate=` and `host=` keep their signatures and annotations. `gate`'s `Callable[[ToolCall], Any] | None` already admits an awaitable result. No field, constant, default or `stats()` key is added. No new name enters either `__all__`. `_ToolLoop` is internal, and private by its underscore (049, Decision 4).
    - **Behaviour changed behind public names.** Each change is allowed in a minor release by 049:
      - `tool()` and `gate=` now accept an async callable they used to refuse: an addition (Decision 8);
      - an async `host=` now raises `TypeError`, a type 049 promises for a bad argument (Decision 6).

      Before 0.1.0, the alphas may change anything anyway (049, Decision 8).
    - **Docstrings changed:** `tool`'s (async functions accepted, async generators refused, where the awaitable runs), and the `tools`, `gate` and `host` entries of `run`'s and `run_async`'s. The shared text stays identical in both (049's Decision 10). The new text names no specification and no internal name, as 049's Decision 10 requires, so it passes 049's checks whichever lands first.
    - **The order with 049.**
      - If 049 lands first, this builder rebases and runs `uv run python tests/harness/api.py --write`. 049's own new `tool` docstring ("TypeError: … the function is async") changes then. The review checks that `tests/public_api.txt` did not change, and that the README's generated block changed only in the entries for `tool`, `run` and `run_async`. It lands with `--accept-judge`, as any judge change does.
      - If this lands first, 049's builder writes those docstrings in its pass, like any others.
      - Either way, 049's renames (`MAX_ABANDONED` to `_MAX_ABANDONED`, `DEADLINE_MARGIN_TICKS` to `_DEADLINE_MARGIN_TICKS`) meet this specification's edits to `_Bounded`. The second to land resolves them by name.

13. **Docs.**
    - **README, *Tools*: a new paragraph, *Async tools*.** It covers:
      - an `async def` tool or gate;
      - where it runs: the caller's loop under `run_async`, a loop of the call's own under `run`. Use `run_async` when the tool needs your loop's objects;
      - a call answered before its awaitable starts never starts it;
      - every later end cancels the task, so an async tool is stopped at its next `await`, where a sync one is abandoned;
      - a tool that catches `CancelledError` runs on and holds its slot;
      - an async tool that blocks its loop delays every async tool on that loop;
      - the private loop's thread is counted in `tool_threads_running`; threads a tool starts itself (`asyncio.to_thread` on the private loop's default executor) are not;
      - under `run_async`, tasks an async tool spawns outlive the call: the runner cancels only its own;
      - an abandoned async tool that ignores its cancel on the caller's loop keeps that loop's `asyncio.run()` from returning at shutdown, since `asyncio.run` gathers every task. An abandoned sync tool never does this, because its thread is a daemon.
    - **README, other *Tools* changes.** *Abandoned tools* says "a sync function cannot be stopped". *What `run` refuses* drops "a gate that is a coroutine function" and adds an async `host=` and an async generator as a tool or gate.
    - **The MCP recipe** becomes an `async def` tool that awaits `session.call_tool(...)`, with no loop argument and no `run_coroutine_threadsafe`, called through `run_async`. The builder runs it once against mcp's in-memory server, with the version 036 used (`uv run --isolated --no-project --with mcp==2.3.0 …`), and puts the commands and output in the landing notes (§4.10).
    - **README, *From async code*:** the bullet "A door host that must await" says to serve it as an async tool. It keeps the raw-door bridge for a `host=` that must stay raw.
    - **CHANGELOG, unreleased:**
      - Added: async tools and gates; a call answered before its awaitable starts never starts it, extending 056's fix to async tools.
      - Changed: an async `host=` is refused.

      The rule for sync tools is 056's line, not this one's.

## Intent

An embedder passes its coroutine functions as tools, as they are. The guest calls them like any tool. Each is awaited on the embedder's loop under `run_async`, or on a loop of the call's own under `run`. It is bounded by the same deadline, cancel and Ctrl-C as a sync tool. It is never started after its call was answered, and it is cancelled when its call ends. Nothing the guest sees changes.

## Design

```
src/wasi_python/tools.py     tool(): accepts async functions, refuses async generators
                             _ToolLoop (internal): a caller's loop or a private one
                               - the private loop is started at the first awaitable, on a
                                 thread whose target owns the loop's life (run_forever, then
                                 cancel, run down, shutdown_asyncgens, close)
                               - run(awaitable, slot): posts the wrapper and waits for its end,
                                 the posted future done with the slot unstarted, the loop's
                                 closing, or its thread's death; then closes an unstarted
                                 awaitable
                               - cancel(slot) and close(): skip a closed loop, never raise
                             the wrapper: its first step calls only _Bounded._start(slot, task),
                               then awaits the awaitable or closes it unrun
                             _Bounded._start(slot, task) -> bool: one acquisition of the lock;
                               056's predicate, the started mark and the task together (never
                               built on 056's self-locking _proceed)
                             _Slot: the started mark and the task, under the bound's lock
                             _Work: after the gate (056's proceed) and after the tool, an
                               awaitable result goes to the loop
                             _Bounded: an end that abandons a started slot cancels its task
                             _ToolHost(..., loop=None): owns the call's _ToolLoop; close()
src/wasi_python/runner.py    run_async passes asyncio.get_running_loop()
                             _check_tools accepts an async gate, refuses an async generator
                               gate
                             _checked refuses an async host= (partials and __call__ read)
                             _tool_host passes the loop
                             _instance closes the frame host's loop in its finally
tests/unit/test_async_tools.py           criteria 1 to 8, no artifacts
tests/unit/test_tools.py,
tests/unit/test_runner_tools.py          the judge change (criterion 19)
tests/checks/test_v1_4_embedding.py      criteria 9 to 18, the built artifact set
README.md, CHANGELOG.md
```

`_ToolHost`'s default invoke, `_inline`, is used when a frame host is passed as a raw `host=`, as 031's checks do. It awaits an awaitable on the frame host's private loop, without a bound, so the same rule holds there. It has no abandonment, so the first step always proceeds (056 passes no `proceed` there either). A frame host used that way is closed by its user; the runner closes the ones it makes.

`_tool_host` reads the loop as `c.get("tool_loop")`, so the dict that spec 036's criterion 17 builds by hand still works, and gets a private loop.

## Scope

In: the above. Out:
- `batch` (Decision 11; question 90);
- an async raw `host=` (Decision 9);
- async mount providers (spec 032's `FileProvider`): their calls are many, short and made synchronously by the guest's libc, and decision 15 names the tool protocol;
- streaming results (async generators), progress, and a tool's own access to the remaining deadline;
- trio and other loops: `run_async` is asyncio only (spec 015). Under trio, `run` from a worker thread gives async tools a private asyncio loop;
- a process-wide ceiling on abandoned tasks (036, Decision 5's reason holds);
- the rule for sync tools (056's);
- any change to the guest package, the zip or the protocol.

## Acceptance criteria

Each new check is seen failing first: against today's code where the behaviour is missing, and against the named stand-in where the property is the point.

Nothing measures time:
- a tool that must block waits on an event the check sets;
- a short `timeout_s` only chooses the outcome;
- counts are of calls, tasks, threads, warnings, log records and outcomes;
- a fail-safe wait only keeps a broken build from hanging the judge.

A tool that must wait on a loop without blocking it waits on an `asyncio.Event` that the check sets through `loop.call_soon_threadsafe`, never on a `threading.Event`, unless blocking the loop is the point.

**Unit** (`tests/unit/test_async_tools.py`, no artifacts). The bound is driven with fakes for the ticker, `cancel` and the Ctrl-C flag, as 036's unit checks drive it. A loop on a thread the check owns stands for the caller's.

1. `test_async_callables_are_accepted_and_async_generators_refused`:
   - `tool()` of an `async def` gives the same `descriptor()` as its `def` twin;
   - `functools.partial(fetch)`, binding nothing, with `name=` (so the check does not depend on 056's rule for bound keywords), is accepted, and so is an object with an async `__call__`;
   - an async generator function raises `TypeError` naming the tool.

   Then through `run` and through `run_async`. Artifact lookups are counted; the executor is a `Recording` executor that counts its `submit` calls and raises from them:
   - a coroutine gate passes the checks. Through `run`, the first artifact lookup is reached (1 lookup); through `run_async`, the executor's `submit` is reached (1 submit);
   - each of these raises `TypeError` with 0 lookups and 0 submits: an async generator gate; `host=` an `async def`; `host=` an async generator function; `host=` an object whose class's `__call__` is `async def`; `host=` a `partial` of an `async def`.

   Seen failing first: today `tool()` refuses the `async def`, `run` refuses the coroutine gate, and no async `host=` is refused.
2. `test_an_awaitable_is_awaited_on_the_tool_loop`. A frame host whose loop is the check's:
   - an `async def` tool's answer is `ok`, with its value;
   - it ran on the loop's thread (by name), and saw a context variable the caller set;
   - a `def` returning a coroutine is served the same way;
   - an async gate returning `False` answers `denied`, and the tool's call counter stays 0;
   - an async gate returning `True` lets the tool run (counter 1).

   With no loop given:
   - the first awaitable starts exactly one thread named `wasi-python-tool--loop`;
   - three async calls later there is still one;
   - a frame host whose tools are all sync starts none.
3. `test_every_end_cancels_a_started_task`. An `async def` tool sets a "started" event as its first statement, then awaits an event forever, counting the `CancelledError`s it sees. Each of the four ends (`timeout_s`, the deadline less two ticks, `cancel`, the Ctrl-C flag) is fired only after "started" is set. For each:
   - the call is answered with its kind, `abandoned=True`;
   - the task saw exactly 1 `CancelledError`;
   - its work thread then ends (joined), and the tool-thread count returns to its value before.

   Stand-in: a bound that abandons without cancelling. The task sees 0, and its thread is still alive when the fail-safe join gives up.
4. `test_a_task_that_ignores_its_cancel_holds_its_slot`. An `async def` tool catches `CancelledError` and then waits for a release `asyncio.Event`, which the check sets through `call_soon_threadsafe`, so the loop is never blocked. Six calls, with `timeout_s` set:
   - four are answered `timeout`, abandoned;
   - the fifth and sixth are answered at once, with the quota's message;
   - the tool started 4 times;
   - the tool-thread count is 4 above its value before until the release, then back.

   Stand-in: a work thread that waits on the posted future instead of the wrapper's end (finding 4). The count drops while the tasks still run, and the fifth call starts.
5. `test_an_answered_call_starts_no_awaitable` (the review's F1).
   - **The busy loop.** The check's loop is busy when the post arrives: a callback the check scheduled on it blocks on a `threading.Event`. An `async def` tool whose body counts its runs is called with `timeout_s` set. The call is answered `timeout`. Then the check releases the loop and joins the work thread. Expected:
     - the body's counter is 0;
     - the coroutine is `CORO_CLOSED` (`inspect.getcoroutinestate`);
     - 0 `RuntimeWarning`s are recorded (`warnings.catch_warnings(record=True)`, `simplefilter("always")`, after `gc.collect()`);
     - the record is what 056 gives a skipped tool (the outcome the guest was told; no new field).
   - The same for an async gate: its body's counter is 0, and the tool never runs.
   - **A coroutine held but not posted.** A `def` tool returns a coroutine, but inside its call it waits until the bound has answered (an event the check sets after the frame host returns). Its coroutine is closed unposted (`CORO_CLOSED`, its body's counter 0), with 0 `RuntimeWarning`s.
   - Stand-in: Decision 4 as first drafted (the post made under the lock, and the posted future cancelled at the end). The body's counter is 1, the review's R1 and E1.
   - **The single acquisition** (the Confirmation's C-2). A test hook injected between the predicate and the mark makes the abandon land in that gap. With `_start` as written the body's counter is 0 and the bound never deadlocks. Stand-ins: `_proceed` and then the mark in a second acquisition (the body's counter is 1); `_proceed` called while holding the lock (the loop's thread is stuck, and the check's fail-safe fires).
6. `test_a_late_gate_skips_an_async_tool`. 056's late-gate case, with an `async def` tool: a sync gate blocks on an event past the tool's `timeout_s`, then allows. Once it is released and the work thread joined:
   - the tool's function was never called (counter 0);
   - no wrapper was posted (0);
   - the record is as 056 gives it.

   The same with an async gate that returns late. Stand-in: 036's `_Work` (counter 1). The sync tool's case is 056's own check, not this one's.
7. `test_faults_in_an_awaitable_stay_in_the_record`. Each case is an `async def` tool or a frame host set up as named:

   | the tool or loop | the answer |
   |---|---|
   | raises `ToolError` | `tool_error`, with its message |
   | raises `ToolDenied` | `denied` |
   | raises `KeyError` | a fault beginning `"KeyError"` |
   | raises `KeyboardInterrupt` / `SystemExit` | a fault beginning with its name; the check's loop is still running afterwards (a later call on it answers `ok`) |
   | raises `asyncio.CancelledError` itself, the call's `cancel` unset | `tool_error`, a fault beginning `"CancelledError"` |
   | the same, the call's `cancel` set | `cancelled` |
   | the wrapper is cancelled before its first step (the check cancels every task on its loop, which stays open, while the loop is held busy and the post waits) | answered (`tool_error`, a fault beginning `"CancelledError"`), with 0 `RuntimeWarning`s, the awaitable `CORO_CLOSED`, and the work thread ended (joined) while the loop is still open (the Confirmation's C-1; stand-in: a wait without the posted future's end, which holds the work thread until the fail-safe) |
   | the frame host's given loop is closed | `tool_error`, a fault beginning `"RuntimeError"`, at once; the awaitable is closed (0 `RuntimeWarning`s) |
   | starting the private loop's thread raises `RuntimeError` (an injected `start`) | `tool_error`, a fault beginning `"RuntimeError"`; the tool-thread count is back |

   Nothing raises out of the frame host in any case.
8. Two checks on the loop's life.
   - `test_close_ends_the_calls_loop`:
     - on a private loop, `close()` cancels every task on it, including one the tool spawned with `create_task` (its counter of `CancelledError`s is 1). The thread ends and `loop.is_closed()` is `True`;
     - with a task that ignores its cancel, `close()` returns while the thread is still alive (1 alive). The thread ends once the task is released, and then the loop is closed;
     - on the check's own loop, `close()` cancels only the runner's tasks. A task the check made on that loop is still pending afterwards;
     - `cancel()` and `close()` on a closed loop raise nothing, and they add 0 log records (a handler on the root logger) and 0 warnings.
   - `test_a_loop_that_ends_is_closed_and_ends_the_wait` (the review's F3). Two cases: a tool that spawns a task raising `KeyboardInterrupt`; a tool that calls `asyncio.get_running_loop().stop()`. For each:
     - the call is answered `tool_error`, with a fault;
     - the private loop is closed, and its thread has ended;
     - the tool-thread count is back to its value before;
     - a later async call on the same frame host is answered `tool_error` at once.

     Stand-in: a loop thread without its `finally`. The wait never ends, and the fail-safe fires.

**End to end** (`tests/checks/test_v1_4_embedding.py`, the built artifact set). Checks whose defect would hang run in a child process with spec 015's 120 s fail-safe, as 036's do.

9. `test_a_guest_calls_an_async_tool_under_run`: two `async def` tools and an async gate that allows. The guest calls both tools, and one result is fed to `pandas.DataFrame`.
   - stdout is as expected;
   - the outcomes are `list ok`, `call ok`, `call ok`;
   - the tools ran on the thread named `wasi-python-tool--loop`;
   - after `run` returns and the tool threads are joined, no thread of that name is alive, and `stats()["tool_threads_running"]` is back to its value before.
10. `test_run_async_awaits_tools_on_the_callers_loop` (the review's F5).
    - Before `run_async`, the check makes a `Future` on its own loop.
    - An `async def` tool records whether that `Future` is done (it must be `False`). It signals "awaiting" with `caller_loop.call_soon_threadsafe(awaiting.set)`, then awaits the `Future`.
    - A coroutine of the check waits for "awaiting", then counts 1,000 turns of `await asyncio.sleep(0)`, then sets the `Future`.
    - Expected: the guest prints the value; the outcome is `ok`; the `Future` was pending when awaited; the tool saw `asyncio.get_running_loop()` be the caller's.
    - Stand-in: tools on a private loop under `run_async`. Awaiting the caller's pending `Future` raises `RuntimeError`, so the outcome is `tool_error` with that fault.
11. `test_a_timeout_cancels_an_async_tool`. Tool A (`async def`, `timeout_s=0.05`) awaits an event forever. The guest catches `ToolTimeout`, then calls tool B (`async def`), which returns its value.
    - stdout is A's timeout message and B's answer;
    - the outcomes are A `timeout` abandoned, B `ok`;
    - A's task saw exactly 1 `CancelledError`.

    Stand-in: the bound that does not cancel (0, at the fail-safe).
12. `test_the_deadline_cancels_an_async_tool` (child). Under `deadline_s=3`, an `async def` tool with no `timeout_s` awaits forever.
    - `run` returns;
    - the last outcome is `timeout`, with the message "<name> timed out at the run's deadline";
    - its task saw exactly 1 `CancelledError`.

    The same under `run_async`. `trapped` is not asserted, for 036's criterion 10's reason.
13. `test_cancelling_run_async_cancels_an_async_tool` (child). `run_async` with a one-worker executor. The task is cancelled once the tool has started (an event the tool sets).
    - The task raises `CancelledError`;
    - the tool's task saw exactly 1 `CancelledError`;
    - a new call on the same executor then completes.
14. `test_a_cancel_during_an_async_tool_is_named` (child). `run(cancel=event)`; the tool sets "started", and the check sets the event.
    - `trapped == "cancelled"`, `exit_code is None`, `fuel_used is None`;
    - the last outcome is `cancelled`, with `abandoned=True`;
    - the task saw exactly 1 `CancelledError`.
15. `test_ctrl_c_during_an_async_tool` (child, on its main thread). The tool sets "started", and the child sends itself SIGINT.
    - `run` raises `KeyboardInterrupt`;
    - the task saw exactly 1 `CancelledError`;
    - the private loop's thread ends (joined), and the child exits 0.
16. `test_an_async_tool_that_ignores_its_cancel_is_bounded`: criterion 4, end to end.
    - Six calls: four `timeout` abandoned, two answered at once, 4 starts.
    - After `run` returns, `stats()["tool_threads_running"]` is 5 above its value before: four work threads, and the private loop's thread, whose run-down waits on them.
    - After the release and the joins, it is back.

    Stand-in: a `close()` that waits for the loop. The run does not return, and the child's fail-safe fires.
17. `test_one_calls_blocked_loop_does_not_starve_another`. Two `run` calls on two threads.
    - A's `async def` tool (`timeout_s=0.05`) blocks its loop: it waits on a `threading.Event` inside the coroutine, which the check sets at the end. A is answered `timeout`.
    - Then B's `async def` tool (`timeout_s=5`, a fail-safe so the stand-in fails at once) answers `ok`.

    Stand-in: one loop for the process. B's call is answered `timeout`.
18. `test_fuel_is_exact_across_async_tool_calls`. Through the judge's driver, with `runner._tool_host(...)` as its host (as 036's criterion 17 does), one program of two tool calls spends equal fuel:
    - when its tools are `async def` and when they are their `def` twins;
    - across two runs whose async tools await different numbers of `asyncio.sleep(0)`.

**The judge change and the whole:**

19. **The judge change, listed.** Re-read the match strings against 049's branch at rebase.
    - `tests/unit/test_tools.py`: the refusal case "an async def" (match "decision 15") becomes "an async generator function" (match "async generator").
    - `tests/unit/test_runner_tools.py`, `MISTAKES`: the coroutine gate row becomes an async generator gate row. Four rows are added, each `TypeError` matching "serve an async host function as a tool": `host=` an `async def`, an async generator function, an object with an async `__call__`, and a `partial` of an `async def`.

    No other existing check changes: every 031, 036 and 056 check passes as it stands.
20. **The README's recipes ran.** The MCP recipe, rewritten as Decision 13 says, ran once with `mcp==2.3.0` against mcp's in-memory server, through `run_async`. Its outcomes: `list ok`, `call ok`, and a `tool_error` with the server's text for its error case. The README's first *Async tools* example ran as written. The commands and outputs are in the landing notes.
21. **049, if it landed first.** `uv run python tests/harness/api.py --check` passes after `--write`; `git diff tests/public_api.txt` is empty; the README block's diff touches only the entries for `tool`, `run` and `run_async`.
22. **The judge is green.** `ruff check` and `ruff format --check` are clean. `uv run pytest` is green with `--accept-judge`: lost 0, grew 0 (the artifact set does not change).

## The owner's choices

None open here. Decision 11 leaves `batch` to a later specification and asks its place in the order of the work as question 90 (`../questions-for-the-owner.md`). Nothing in this specification waits on it.

## Revised against the pre-build review (2026-10-18)

The review (`../reviews/053-async-host-functions-spec-2026-10-18.md`) found F1 to F8. Every finding is accepted and written in. The memo is unchanged: its facts still hold. What the review added (R1 to R5, E1) is cited from the review, under "Research it stands on".

1. **F1 (high): an answered call could still start its async tool.** Fixed in Decision 4.
   - The start of an awaitable is decided on the loop's thread, at the wrapper's first step, under the bound's lock, with 056's `proceed`. If the call was answered first, the awaitable is closed unawaited.
   - An abandon after that start cancels the recorded task, with `call_soon_threadsafe`. The posted future is never cancelled.
   - The new criterion 5 has a busy loop and the answer first. Its stand-in is Decision 4 as drafted (body counter 1).
   - The sync half of the review's last bullet (check and start together, under the lock, right before `t.fn`) is 056's to state. Decision 5 records it as what the lane checks at rebase.
2. **F2 (medium): rebase onto 056's rule, not re-decide it.** 056 is under "Depends on", landing first.
   - Decision 5 now states 056's rule (from its Decision 3, as drafted in its worktree: `proceed` after the gate; a skipped tool returns an unread `cancelled` answer; the record is not changed) and extends it to awaitables in the same terms.
   - It writes the rebase check for the lane: if 056's landed text differs, 056 governs and the difference is recorded, not decided again.
   - Criterion 5's sync case moved to 056 (the new criterion 6 covers only async tools and async gates). The CHANGELOG line for sync tools is 056's.
3. **F3 (medium-low): a private loop could die unclosed and hang the wait.** Fixed in Decision 3.
   - The loop's thread owns the loop's whole life: `run_forever` in a `try`, and a `finally` that cancels, runs down, runs `shutdown_asyncgens` and closes, catching everything.
   - The wait also ends when that thread is dead.
   - An ended private loop is not restarted for its call; its later awaitables are faults.
   - Decision 8's `close()` now only stops the loop, and the thread does the rest.
   - Criterion 8's second check covers both of R5's cases.
4. **F4 (low-medium): cancel and close on a closed loop.** Fixed in Decisions 4 and 8.
   - They skip a closed loop, catch everything, and never raise, log or warn.
   - The runner never cancels the posted future (the cause of R4's log).
   - Every awaitable not run is closed on every fault path (R3).
   - Criteria 7 and 8 count raised exceptions, log records and warnings: all 0.
5. **F5 (low): criterion 8's stand-in.** Now criterion 10: the setter starts counting only after the tool signals that it is awaiting, and the tool records that the `Future` was pending.
6. **F6 (low): criterion wording.**
   - Criterion 4: the release is an `asyncio.Event` set through `call_soon_threadsafe`; the criteria preamble says so for every such wait.
   - Criterion 3: each end fires after the tool signals that it started.
   - Criterion 8: `loop.is_closed()` is asserted.
   - Criterion 1: the partial binds nothing, and the executor sentence is reworded.
7. **F7 (low): unnamed failure modes.**
   - (a) The private loop's thread cannot start: a counted `tool_error` fault (Decision 2; criterion 7).
   - (b) The async `host=` check unwraps partials and reads `__call__` (Decision 9; criteria 1 and 19).
   - (c) An unrequested `CancelledError` while the run is being cancelled is answered `cancelled` (Decision 6; criterion 7).
   - (d) A stopped or blocked caller's loop is bounded only by 036's ends, and its work thread waits until the loop runs or closes (Decisions 3 and 6).
8. **F8 (low): README facts.** All three are added to Decision 13's *Async tools* paragraph: spawned tasks outlive a `run_async` call; an ignoring task on the caller's loop holds up `asyncio.run()`'s shutdown; a private loop's executor threads are not counted (also Decision 8).

### The Confirmation's conditions (2026-10-18)

The reviewer confirmed the revision (`da7dc72`) for build, once two conditions were written in. Both are now in:

- **C-1. A wrapper cancelled before its first step never runs its `finally`** (EXECUTED by the reviewer, `probe_c1.txt`, case C2: "its finally ran False; the posted future ended with CancelledError; RuntimeWarnings 1"). Decision 4 had wrongly said the wrapper's `finally` covers that case.
  - Written in: Decision 3's wait has a second end: the posted future is done while the slot has not started, read under the bound's lock. The work thread then closes the awaitable and answers as Decision 6 says.
  - Decision 4 now says that case is the work thread's to finish.
  - Criterion 7 gains its row.
- **C-2. One named locked step** (EXECUTED by the reviewer as a model, case C3: "thread stuck True"). 056's `_proceed` takes the non-reentrant lock itself, so calling it under the lock deadlocks the loop's thread, and calling it in a separate acquisition from the mark reopens F1.
  - Written in: Decision 4 names `_Bounded._start(slot, task) -> bool`, one acquisition that checks 056's predicate, marks the slot started and records the task. The wrapper's first step calls only that.
  - The Design and Terms say so.
  - Criterion 5 gains a check with an injected hook in the gap, and the two stand-ins.

## Landing notes

Built 2026-10-18 by the implementer (a builder agent, Claude Opus 5.5) in the worktree `wasi_python-053` on `spec/053-async-host-functions`, which the lane had rebased onto main with spec 056 landed (`0b98029`). The judge ran against the lane's frozen artifact set `build/sets/s-c4190ca065ada03a` (spec 035's; never rebuilt; `WASI_PYTHON_ARTIFACTS` pointed at it), on darwin-arm64 with wasmtime-py 49.0.0 and Python 3.14.2. Each claim is EXECUTED unless it says otherwise. Logs and scripts are under the worktree's `build/053/`, which is not kept, so the lines that matter are quoted here. Not yet reviewed.

**Commits.**
- `c3bd5d5`: the checks first (criteria 1 to 19);
- `9f407b0`: the code;
- `2e2ab18`: two checks strengthened against their stand-ins, and the docstrings of `run` and `run_async`;
- `70009e6`: README and CHANGELOG;
- this commit: these notes.

**056 against what this spec quotes (Decision 5).** 056's landed text and code agree with what Decision 5 quotes; nothing differed (READ, `src/wasi_python/tools.py` at `0b98029`, and `context/specifications/056-the-a4-security-reviews-findings.md`, Decision 3):
- `_Work.__call__(proceed)` asks `proceed` after the gate (or at once with no gate) and before `t.fn`;
- `_Bounded._proceed(slot)` is `not slot.abandoned`, read under `self._lock`, a plain `threading.Lock`;
- a skipped tool returns `failed("cancelled", "<name> was not run: its call had ended")`, which nobody reads;
- "The record is not changed": the outcome keeps `abandoned=True`.

This build extends that rule to awaitables in the same terms. A skipped awaitable gets the same unread `cancelled` answer, and the record is unchanged.

**What changed.**
- **`src/wasi_python/tools.py`.**
  - `tool()` refuses an async generator function (`_is_async_generator`, through `partial`s and at a callable object's `__call__`) where it refused every async function. Its docstring says how an async tool runs, with no specification number.
  - `_Work.__call__(proceed=None, ops=None)`: an awaitable returned by the gate or by the tool goes to `self._loop.run(awaitable, ops)`. `_NotStarted` gives 056's skip answer. A `CancelledError` met while the bound's ends say the run is being cancelled is answered `cancelled` (Decision 6, `_Work._cancelling`).
  - New internals: `_ToolLoop` (`_get`, `_serve`, `run`, `_wrapper`, `close`), `_Post`, `_Ops`, `_NotStarted`, `_cancel_post`, `_close_awaitable`, and the constants `_LOOP_THREAD` (`"wasi-python-tool--loop"`) and `_LOOP_POLL_S` (0.01, the runner's tick).
  - `_Slot` gains `post`.
  - `_Bounded._abandon` asks a started awaitable's task to cancel, after it has released the lock; `_Bounded._begin(slot, task)` is the one locked first step; `_Bounded._started` passes `_Ops(self, slot)` to the work.
  - `_ToolHost(..., tool_loop=None)` keeps a `_ToolLoop` (a private one by default) and gains `close()`.
- **`src/wasi_python/runner.py`.**
  - `run_async` sets `checked["tool_loop"] = asyncio.get_running_loop()`.
  - `_is_async_callable` (with no import of `wasi_python.tools`) refuses an async `host=` in `_check_tools`.
  - An async generator gate is refused where a coroutine gate was.
  - `_tool_host` builds `_ToolLoop(c.get("tool_loop"), count=_count_tool_threads)`.
  - `_instance`'s `finally` calls `tool_host.close()` first.
  - The docstrings of `run` and `run_async` gain a sentence each, with no specification number.
- **The judge.**
  - `tests/unit/test_async_tools.py` (new, 10 checks: criteria 1 to 8, the C-2 check included).
  - Ten checks appended to `tests/checks/test_v1_4_embedding.py` (criteria 9 to 18).
  - The judge change of criterion 19: `test_tools.py`'s row and five rows in `test_runner_tools.py`'s `MISTAKES`. The coroutine-gate row is replaced by an async generator gate row, and four async `host=` rows are added. Nothing else changed.
- **README.** *Tools* gains **Async tools** (the example, where it runs, stopped not abandoned, faults, what it does not do, what is counted). *Abandoned tools* now says "a sync function". *What `run` refuses* is updated. The MCP recipe is now an `async def`, and *From async code*'s bullet points to async tools.
- **CHANGELOG.** `0.1.0a5 — unreleased`: Added async tools and gates; Changed, an async `host=` is refused.

**Choices where the spec was silent, or read one way.**
- **`_Bounded._begin`, not `_start`.** `_Bounded._start` already holds the injected thread starter (spec 036), so the C-2 method is named `_begin(slot, task)`. It does exactly what the Confirmation's C-2 asks: one acquisition that checks `not slot.abandoned`, then marks `slot.post.started` and records the task. The wrapper's first step calls only it, through `_Ops.start`.
- **Criterion 5's C-2 check.** The spec described a hook injected between the predicate and the mark. The single method has no such gap to hook, so the check gives the bound a counting lock instead. That lock fails at once on a second acquisition by its holder, rather than hanging. The check then asserts one acquisition for each answer, `True` and `False`. Both of the spec's stand-ins fail it (below).
- **The unrequested `CancelledError` while cancelling** (Decision 6) applies to a gate's awaitable too: `cancelled`, otherwise `denied`, failing closed.
- **Fail-safes.** Each tool whose wait could, in a regression, never end has a `timeout_s` of 30 s: criterion 7's C-1 tool and criterion 8's two ended-loop tools. Under such a regression the call is answered `timeout`, which the check refuses, instead of hanging the judge. Criterion 16 runs `run` on a helper thread joined with a 120 s fail-safe.
- **Fake clocks.** A `Clock` whose first read in a call (from which the bound sets the call's end) gives 0. The first try used a clock read straight from the tool's flag: the work thread could set the flag before the door thread set the end, which then never came (seen hanging, then fixed; not a code defect).
- **Criterion 18's twins** have one docstring. With different docstrings the discovery answers differed, so fuel differed by 7,321 (92,025,871 against 92,033,192).

**Seen failing first.**
- Against `0b98029` (before any code):
  - `tests/unit/test_async_tools.py` gave `8 failed, 2 errors` (`TypeError: … async tools come with a later specification (decision 15)`, and `T.asyncio` missing);
  - the ten end-to-end checks gave `10 failed` (the same `TypeError`, in process or in the child).
- Then each named stand-in was applied to the built code, its checks run, and the file restored byte for byte (`build/053/mutants.txt`; `restored True` each time):

| stand-in | its checks |
|---|---|
| c3/c11: a bound that abandons without cancelling | `test_every_end_cancels_a_started_task` and `test_a_timeout_cancels_an_async_tool`: 2 failed (`[]`). The first try of the end-to-end check passed this stand-in, because the loop's closing at the run's end cancelled A anyway. Tool B now reports A's cancel count, which the call's end must already have produced. |
| c4: the wait ends at the cancel, as a wait on the cancelled posted future does | `test_a_task_that_ignores_its_cancel_holds_its_slot`: failed. The fifth call started, where the quota should have answered at once. The first form of this stand-in, `… and not future.done()`, equals the built code (the runner never cancels the posted future, so it is done only when the task is) and passed, so it was replaced. |
| c5: Decision 4 as first drafted, no first-step check | `test_an_answered_call_starts_no_awaitable`: `assert [1] == []` |
| C-2: `_proceed`, then the mark in a second acquisition | `test_the_first_step_takes_the_lock_once`: 2 acquisitions |
| C-2: `_proceed` called while holding the lock | the same check: "the bound's lock was taken twice" (it would deadlock) |
| c6: 036's `_Work`, no check after the gate | `test_a_late_gate_skips_an_async_tool`: failed |
| c7/C-1: the wait without the posted future's end | `test_faults_in_an_awaitable_stay_in_the_record`: `'timeout' == 'tool_error'` at the 30 s fail-safe |
| c8/F3: the loop's thread without its `finally` | `test_a_loop_that_ends_is_closed_and_ends_the_wait` and `test_close_ends_the_calls_loop`: 2 failed |
| c10: a private loop under `run_async` | `test_run_async_awaits_tools_on_the_callers_loop`: `b'' tool_error … False True` |
| c16: a `close()` that waits for the loop | `test_an_async_tool_that_ignores_its_cancel_is_bounded`: "run waited for the tasks that ignore their cancel", at 120 s. The first form called `run` directly and hung the judge, which led to the helper thread. |
| c17: one loop for the process | `test_one_calls_blocked_loop_does_not_starve_another`: B's run failed |

**Acceptance, with evidence.**

*Unit* (`tests/unit/test_async_tools.py`: 10 passed, 15 runs in a row; `test_tools.py`, `test_runner_tools.py` and `test_guest_tools.py`: 221 passed):

1. Criterion 1, `test_async_callables_are_accepted_and_async_generators_refused`:
   - the descriptors are equal;
   - `partial(fetch)` and an async `__call__` are accepted;
   - an async generator is refused;
   - a coroutine gate reaches 1 lookup through `run` and 1 submit through `run_async`;
   - the async generator gate and the four async `host=` forms each raise with 0 lookups and 0 submits.
2. Criterion 2: the tool ran on `caller-loop` with the caller's context variable, and the adapter did too; the async gate's `False` gave `denied` with the tool counter at 0, and its `True` gave counter 1; with no loop given, one `wasi-python-tool--loop` thread is started at the first awaitable and stays one after three calls, while sync tools start none. After `close()` the thread is gone, the loop is closed and the count is 0.
3. Criterion 3: each of the four ends answered its kind, abandoned, with exactly 1 `CancelledError` per case and the count back. The Ctrl-C flag is still set afterwards.
4. Criterion 4: four `stubborn timed out after 1 s`, two answered at once with the quota's message, 4 starts, the count at 4 until the release, then 0.
5. Criterion 5:
   - with the busy loop the body ran 0 times and the coroutine is `CORO_CLOSED`; the async gate's body ran 0 times and so did the tool; the coroutine the work thread held unposted was closed; 0 `RuntimeWarning`s in all;
   - the C-2 check: 1 acquisition for each answer.
6. Criterion 6: with a sync gate and with an async gate, the tool's function was called 0 times; the sync gate posted nothing; the count is back.
7. Criterion 7: every row of the table, including the C-1 row (`tool_error`, `CancelledError…`, body 0, `CORO_CLOSED`, the work thread ended, the loop still open and running, 0 warnings).
8. Criterion 8:
   - `close()` cancelled the spawned task once and closed the loop;
   - with an ignoring task, `close()` returned while 1 thread was still alive, and the loop closed after the release;
   - on the caller's loop, the check's own task was still pending;
   - `cancel` and `close` on a closed loop gave 0 log records and 0 warnings;
   - both ended-loop cases answered `tool_error` with a fault, closed the loop, ended the thread and brought the count back, and a later call was answered `tool_error` naming "stopped".

*End to end* (`tests/checks/test_v1_4_embedding.py`, the frozen set; all pass):

9. Criterion 9: stdout `EMEA 60 ['month', 'sales']\nb'\x00cba'\n`; the outcomes `list ok`, `call ok`, `call ok`; both tools on `wasi-python-tool--loop`; no loop thread afterwards; the count back.
10. Criterion 10 (child): `b'42\n' ok None True True` (the value; `ok`; no fault; the caller's loop; the `Future` pending when awaited).
11. Criterion 11: `a timed out after 0.5 s\nB's answer; A cancelled 1\n`; the outcomes A `timeout` abandoned, B `ok`; A's task saw `[1]`.
12. Criterion 12 (child): `timeout block timed out at the run's deadline [1] True`, then the same under `run_async`.
13. Criterion 13 (child): `cancelled [1]`, then `b'next\n'`.
14. Criterion 14 (child): `cancelled None None b'' cancelled True [1] True`.
15. Criterion 15 (child): `KeyboardInterrupt [1] True`.
16. Criterion 16: six lines as expected, 4 starts, `tool_threads_running` 5 above its value before (four work threads and the loop's thread), then back after the release.
17. Criterion 17: A `A done`, with its tool seen blocking; B `now`, `ok`.
18. Criterion 18: fuel `[92025871, 92025871, 92025871]` through the judge's driver (async with 0 and with 50 `sleep(0)`, and the sync twin).

*The whole:*

19. Criterion 19: the judge change listed above, and nothing else. Every 031, 036 and 056 check passes.
20. Criterion 20: the recipes.
    - The README's *Async tools* example, extracted from the README as written (`build/053/ readme_async_example.py`, with a final `print`): `b'1.08\n'`.
    - The MCP recipe, extracted as written and run against an in-memory `MCPServer` with one tool, `forecast(city, days=3) -> Forecast` (a `TypedDict`, `structured_output=True`), through `mcp.Client(server)`. The command was `uv run --isolated --no-project --with mcp==2.3.0 --with <worktree> python -I build/053/mcp_recipe.py`, with mcp 2.3.0. Output:

      ```
      0 None
      {'city': 'Oslo', 'highs': [4, 6]}
      ToolError Error executing tool forecast
      1 list None ok None None
      2 call forecast ok None None
      3 call forecast tool_error Error executing tool forecast None
      ```

      The server logs its own traceback for the Atlantis error on stderr; that is mcp's logging, not the runner's.
21. Criterion 21: **not done here.** Spec 049 landed on main (`6d6dfc5`, accepted; `3dfdab4`) while this was being built, and the coordinator said not to rebase. A read-only `git merge-tree --write-tree main HEAD` shows conflicts in `CHANGELOG.md`, `context/questions-for-the-owner.md`, `src/wasi_python/runner.py` and `src/wasi_python/tools.py`. After the rebase, the lane or the builder runs `uv run python tests/harness/api.py --write` and checks that `tests/public_api.txt` is unchanged, and that the README block changes only in the entries for `tool`, `run` and `run_async`.
22. Criterion 22: `ruff check` and `ruff format --check` are clean on `src` and `tests`. The full judge (`WASI_PYTHON_ARTIFACTS=…/s-c4190ca065ada03a uv run pytest`, no flags):

    ```
    wasi_python v1: 300/342 pass · 0 gap · 42 blocked · 0 fail   (unit suite 1069/1077, 8 skipped)
      v1.4  embedding           139/139
    ratchet vs 4921daffeb: lost 0 · absent 0 · unrun 0 · unrun locally 28 · gained 10 · grew 0 · upstream unrun 31 · judge changed: tests/checks/test_v1_4_embedding.py, tests/unit/test_async_tools.py, tests/unit/test_runner_tools.py and 1 more
    ================= 1369 passed, 50 skipped in 260.42s (0:04:20) =================
    ```

    The 42 blocked are this worktree's: numpy's and pandas' source trees, the oracle, the prior-art clones, the other source trees, three systems and the wheel. The fast tier gave `293/342 pass · 0 fail`, `lost 0 · gained 10 · grew 0`.

**For the build review.**
- **The locked steps.** Check these against Decision 4 and the Confirmation's C-2:
  - `_Bounded._begin` and `_Bounded._abandon`: the latter reads `slot.post.started` under the lock and cancels after releasing it;
  - `_Ops.post`, the check before posting, and `_Ops.started`, read under the lock in the work thread's wait.
- **`_ToolLoop.run`'s wait.** Its four ends; the order of the `ended` check before the C-1 branch, since the wrapper sets `ended` in its `finally` before the task completes; and the wrapper coroutine closed if `run_coroutine_threadsafe` refuses the post.
- **`_ToolLoop._serve`.** It swallows a `BaseException` out of `run_forever` and out of the run-down, so no "Exception in thread" is printed, and it closes the loop in an inner `finally`.
- **`_wrapper`.** It catches `BaseException` except `GeneratorExit`. A fault in its own first step is kept as the call's error.
- **`_instance`.** `close()` is first in its `finally`, before `store.close()`.
- **The rebase onto 049** (criterion 21), and 049's renames inside `_Bounded`.
- **The two strengthened checks** (criteria 11 and 16) and the replaced c4 stand-in.

### Rebased onto main (049, 054), 2026-10-18

At the coordinator's request, before the build review, the branch was rebased with `git rebase main` onto main `94167a8`. That main has 049 (the public API frozen, landed as `6d6dfc5`) and 054 (`import_path=`, landed as `c79a3a9`). Each claim is EXECUTED.

**Conflicts, and how each was resolved.**
- **`context/questions-for-the-owner.md`** (at the draft commit): both sides kept. Main's 91, 94, 92 and 93 come first, then this branch's 90; the context is otherwise untouched.
- **`tests/checks/test_v1_4_embedding.py`** (at the checks commit): both blocks appended at the file's end were kept. 054's import-path checks come first, then this spec's async checks.
- **`src/wasi_python/runner.py`**, two places:
  - At the code commit: 049's new signature `_check_tools(host, tools, gate, max_tool_calls, limits=None)` is kept, with this spec's `_is_async_callable` placed before it. Its body merged cleanly: 049's `(limits or _current_defaults()).tool_calls`, this spec's async `host=` refusal and async generator gate refusal, and 054's `import_path` threading through `_checked` and `_check_places` all stand.
  - At the docstring commit: 049's Google-style docstrings of `run` and `run_async` are kept. This spec's sentences are rewritten into their shared `Args:` entries, identical in both, as 049's Decision 10 requires, with no specification number:
    - `host`: "It must answer synchronously: an async one raises `TypeError`."
    - `tools`: a tool may be async, awaited on the loop that awaits `run_async` or on the call's own loop, never started once answered, cancelled at its call's end.
    - `gate`: "It may be async, as a tool may."
- **`src/wasi_python/tools.py`** (at the code commit): `tool()`'s docstring. 049's version (its `Args:`, `Returns:` and `Raises:`) is kept. This spec's async paragraph is added after the first paragraph. `Raises: TypeError` now reads "the function is an async generator function" where 049 had "the function is async".
  - 049's renames reached this spec's code with no conflict: `_Work` uses `_FAULT_CHARS` and `_TOOL_RESPONSE_BYTES`, and `_Bounded` uses `_MAX_ABANDONED` and `_DEADLINE_MARGIN_TICKS`. A search found none of the seventeen old names left without their underscore.
  - 056's `_proceed` and this spec's `_begin` both stand.
  - Every new module-level name is private: `_ToolLoop`, `_Post`, `_Ops`, `_NotStarted`, `_cancel_post`, `_close_awaitable`, `_is_async_generator`, `_LOOP_THREAD`, `_LOOP_POLL_S`.
- **`CHANGELOG.md`** (at the docs commit): both kept in `0.1.0a5 — unreleased`. 054's entry and 049's come first, then this spec's two.
- `README.md`'s prose, `tests/unit/test_tools.py` and `tests/unit/test_runner_tools.py` merged cleanly.

**Criterion 21: met.**
- `uv run python tests/harness/api.py --check`, before `--write`: only the README block differed. The entries were run's `host`, `tools` and `gate`, and tool's `Raises`; `run_async` is shown short.
- After `--write` (`9497ad9`): `git diff --quiet tests/public_api.txt` succeeded, so the snapshot is unchanged, and `--check` passes.

**Checks after the rebase.**
- `ruff check` and `ruff format --check` are clean.
- Fast tier: `315/364 pass · 0 gap · 10 blocked · 0 fail`, `lost 0 · gained 10 · grew 0`.
- Every stand-in was re-applied on the rebased code (`build/053/mutants-rebased.txt`), and each failed as named, with every file restored byte for byte:
  - c3/c11: 2 failed;
  - c4: failed;
  - c5: `[1] == []`;
  - the two C-2 stand-ins: 2 acquisitions, and "taken twice";
  - c6: failed;
  - c7/C-1: `'timeout' == 'tool_error'`;
  - c8: 2 failed;
  - c10: failed;
  - c16: "run waited …" at 120 s;
  - c17: failed.
- The full judge (`WASI_PYTHON_ARTIFACTS=…/s-c4190ca065ada03a uv run pytest`, no flags):

  ```
  wasi_python v1: 322/364 pass · 0 gap · 42 blocked · 0 fail   (unit suite 1073/1081, 8 skipped)
    v1.4  embedding           157/157
  ratchet vs 5f56591135: lost 0 · absent 0 · unrun 0 · unrun locally 28 · gained 10 · grew 0 · upstream unrun 31 · judge changed: tests/checks/test_v1_4_embedding.py, tests/unit/test_async_tools.py, tests/unit/test_runner_tools.py and 1 more
  ================= 1395 passed, 50 skipped in 262.13s (0:04:22) =================
  ```

  The 42 blocked are this worktree's, as before. `tests/public_api.txt` is not among the judge's changed files.
### Revised against the build review (2026-10-18)

The build review (`../reviews/053-async-host-functions-2026-10-18.md`, written in the scratchpad and copied in by the lane) said "lands once F1 is fixed". Its disposition, each claim EXECUTED:

1. **F1 (low): a stale `started` read could report a tool that ran as "cancelled before it started". Fixed in `4b521c8`.**
   - `_ToolLoop.run`'s wait now decides the C-1 branch as `future.done() and not post.ended.is_set()`, the line the reviewer tried. The wrapper sets `ended` in its `finally` before its task completes, so with the future read first and `ended` second, neither fact can go stale. No `started` read stays in that branch.
   - The loop-closed branch re-checks `ended` (and reads `started` only after it) before it reports the loop stopped, so it cannot mislabel a finished tool either.
   - The new check is `test_a_tool_that_ran_is_never_reported_as_not_started`. It forces the review's interleaving:
     - the caller's loop is busy when the post arrives, so the wait passes its first slice;
     - the posted future's first `done()` releases the loop, and returns only once the wrapper has run the tool to its end and the future has completed;
     - the wait as built at `58be89e` read `started` before that, and answered `tool_error` ("`AssertionError: assert ('tool_error'…ernal error)') == ('ok', 'done')`", the file restored afterwards, `restored True`). The fix answers `ok`, with `effects == [100]`, no fault and `abandoned=False`.
   - The injection is on the future's `done()`, not on `ended.is_set()` as the reviewer's P1 did. The fixed wait reads `ended.is_set()` only after the future is done, so P1's injection never fires on the fix. Run as it is, P1 holds the loop until its own `hold` is set, which never happens; that is a property of the probe, not of the code.
   - The C-1 stand-in (c7, now written against the new line) and the F3 stand-in (c8) were re-run on the fix and still fail as named: `'timeout' == 'tool_error'` at the 30 s fail-safe, and 2 failed.
2. **N1 (note): three defensive branches had no pinning check.** In part:
   - R4b is pinned by a row in `test_close_ends_the_calls_loop`: `_cancel_post` on a loop that reports open but refuses the call ("Event loop is closed") raises nothing and adds 0 log records and 0 warnings.
   - R2 (cancelling the posted future) stays covered as the review found: the runner keeps no reference to the future in `_cancel_post`, so the mutant needs a code change the review can see.
   - R3 (the thread-death end) stays unpinned. `_serve`'s `finally` always closes the loop before its thread ends, so the closed-loop end covers it, and forcing a dead thread with an open loop would need a fake thread swapped into the wait's local. It remains belt and braces, as the review says.
3. **N2: fixed.** `tools._is_async` is deleted. It had no caller, and `_is_async_generator`'s docstring no longer names it.
4. **N3: fixed.** README, *Async tools*, **Faults stay in the call**: "Tasks the tool spawns are yours: under `run_async` their exceptions reach your loop as asyncio delivers them, so a `KeyboardInterrupt` from one reaches your `asyncio.run`." `api.py --check` still passes (the generated block is unchanged).

**Checks after the fix:**
- `tests/unit/test_async_tools.py`: 11 passed, 8 runs in a row.
- `test_tools.py`, `test_runner_tools.py` and `test_guest_tools.py`: 221 passed.
- `ruff check` and `ruff format --check` are clean.
- Fast tier (`WASI_PYTHON_ARTIFACTS=…/s-c4190ca065ada03a uv run pytest -m "not slow"`): `315/364 pass · 0 gap · 10 blocked · 0 fail · 39 deselected (unit suite 1074/1082, 8 skipped)`, `v1.4 embedding 157/157`, `ratchet vs 5f56591135: lost 0 · absent 0 · unrun 0 · unrun locally 8 · gained 10 · grew 0`, `1389 passed, 18 skipped, 39 deselected`.
- The full judge was not re-run for this one-file fix. The lane judges the exact commit it accepts.

**Landed 2026-10-18** through the lane, after the 0.1.0a5 tag. The lane rebased the branch onto main `99097b6` (0.1.0a5 tagged, the version bumped to 0.1.0a6) with no conflict; its code diff equals the reviewed diff at `e07630f` line for line (EXECUTED, `build/lane-053-rebased.diff` against `build/reviews-evidence/053-buildreview/reviewed-e07630f.diff`). One lane commit, `4e8b32a`, moves the CHANGELOG entry from the dated 0.1.0a5 section to 0.1.0a6 (the notes above that name `0.1.0a5 — unreleased` predate the tag). Its pre-build review (`../reviews/053-async-host-functions-spec-2026-10-18.md`) and its build review (`../reviews/053-async-host-functions-2026-10-18.md`: "lands once F1 is fixed", then "confirmed, it lands") were committed on the detached HEAD as `13934b0`. The full judge there, on spec 035's artifact set: `wasi_python v1: 350/364 pass · 12 gap · 2 blocked · 0 fail (unit suite 1083/1085, 2 skipped)`, `ratchet vs 13934b0770: lost 0 · absent 0 · unrun 0 · gained 0 · grew 0` after acceptance, `1433 passed, 4 skipped, 12 xfailed in 517.02s` (EXECUTED, `build/lane-053-accept.log`). Accepted with `--accept-judge` as `8185e5f` (history line 56); the rules tier passed (24/24); main fast-forwarded. Owner question 90 (batched tool calls, after 0.1.0) stays open; nothing waits on it.
