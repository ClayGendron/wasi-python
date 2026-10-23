# Async host functions: where the coroutine runs, and what stops it

- **Status:** research, 2026-10-18. It commits the project to nothing. It feeds spec 053 (`../specifications/053-async-host-functions.md`).
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5), the author of spec 053's draft. It wrote none of the code it reads. Box: 60 minutes; stopped at about 50.
- **The question,** from the owner's decision 15 (2026-10-17, `../decisions.md`): "yes, as a later specification, with the tool protocol: an async host function awaited by the guest's door call, under the call's deadline"; and decision 49 (2026-10-18): 0.1.0 carries it. Concretely: when a tool is a coroutine function, on which event loop does its coroutine run, from `run` and from `run_async`; how does the door thread wait for it; and what do a timeout, the deadline, a cancel and Ctrl-C do to the coroutine in flight?

## Labels

EXECUTED means run here, in this box, with the command and output beside it in `2026-10-18-async-host-functions/`. READ means read from a file, cited by path. INFERRED means the researcher's reasoning. Nothing below measures time as a result; the probes' waits are fail-safes, and each line they print is a count or a boolean.

## Where things stand (READ)

- **A tool call today** (spec 036; `src/wasi_python/tools.py`, `_Bounded`, `_Work`, `_Slot`). The door thread (the guest's thread, or `run_async`'s worker) hands the call's work (the gate, the tool, the result's encoding) to a new daemon thread, in a copy of the door thread's `contextvars` context, and waits beside it in slices of one tick. The call ends at the first of: the work's answer, the tool's `timeout_s`, the run's deadline less two ticks, the run's `cancel`, a pending Ctrl-C. A call answered without its work leaves the thread running, "abandoned"; one call may hold 4 (`MAX_ABANDONED`), and `runner.stats()` counts the threads alive (`tool_threads_running`).
- **An async tool is refused** by `tool()` ("async tools come with a later specification (decision 15)", `tools.py`, `_make`), and a coroutine gate by `run` (`runner.py`, `_check_tools`). Spec 031's Decision 11 assigned "async tools and gates, and the guest's `batch` operation" to the later specification.
- **The bridge embedders use meanwhile.** The README's MCP recipe wraps the client's coroutine in a sync tool: `asyncio.run_coroutine_threadsafe(session.call_tool(...), loop).result(timeout=…)` (`README.md`, *Tools*). The README's *From async code* gives the same advice for a raw `host=`. The tool thread then blocks on the loop; when the call is abandoned, the coroutine is not cancelled and runs on (INFERRED: nothing in the recipe cancels `future`).
- **The raw door** calls `host` inline on the door thread (`runner.py`, `_door`). An `async def` passed as `host=` is not refused: its call returns a coroutine, which is not bytes, so every frame is answered `HOST_FAULT` (−2) and the coroutine is never awaited (READ, `_door`'s `frame`: `if not isinstance(response, (bytes, bytearray, memoryview)): return HOST_FAULT`).

## Findings

### 1. From `run_async`, the caller's loop is free to run the tool (EXECUTED)

`asyncio_probe.py`, case A1, on Python 3.11.14 and 3.14.2: a worker thread posts a coroutine to the loop that awaits the worker through `asyncio.wrap_future` (what `run_async` does). The tool ran on that loop (`on the caller's loop True`, on `MainThread`, where `asyncio.run` runs it), and the loop kept turning while the worker waited (`loop turned while the worker waited: True`).

So under `run_async` an async tool can run on the embedder's own loop, beside the objects bound to it. That matters: a `Future` made by one loop and awaited on another raises `RuntimeError` (case A7: "a Future of another loop: RuntimeError: Task <Task pending …"). An MCP client session, an HTTP client's connection pool and an `asyncio.Lock` in use are such objects (INFERRED from A7: each awaits futures of the loop it was made on).

### 2. From `run`, the caller's thread may hold a loop that cannot run (EXECUTED)

Case A2: a coroutine posted to a loop whose own thread is blocked (as when `run()` is called directly inside a coroutine, which blocks the loop: spec 015's probe measured 4,377 ms of a blocked loop) did not start while the thread was blocked (`started while it was blocked: False`), and started once the loop turned again (`True`). A tool waiting on it would time out every call. And `run`'s caller may have no loop at all.

So a call made with `run` needs a loop of its own for its async tools (INFERRED). Case A8 shows a loop on its own daemon thread can be shut down cleanly at the call's end: cancel every task on it (a task the tool spawned and never awaited included), await them on the loop, stop, close; the thread ended (`clean: loop thread alive a second after the shutdown request: False`).

### 3. The context reaches the task (EXECUTED)

Case A3: a task made by `run_coroutine_threadsafe` ran in a copy of the posting thread's context, a value set inside `contextvars.Context.run` on that thread included (`the task saw the posting thread's context: True ('from the request')`); the loop thread's own value stayed `'unset'`. (READ: `call_soon_threadsafe` copies the calling thread's context into its handle, and the task made inside that handle copies it again.) So an async tool posted from spec 036's tool thread, which runs in a copy of the door thread's context, sees the request's context variables, as a sync tool does.

### 4. Cancelling the posted future is not the task's end (EXECUTED)

Case A4. `run_coroutine_threadsafe` returns a `concurrent.futures.Future`. Its `cancel()` returned `True` at once and its waiter woke with `CancelledError` at once, in both cases below, **before the task had ended** (`task ended when the waiter woke: False`):

- a task that lets the `CancelledError` through ended shortly after (`ended within the next second: True`, `steps after the cancel: 0`);
- a task that catches it and goes on kept running (`ended within the next second: False`, `steps after the cancel: >0`) until the probe released it.

So a runner that waits on the posted future learns nothing about whether the tool stopped. A coroutine of the runner's own, wrapping the tool's awaitable and setting an event in its `finally`, marks the real end (both cases: `ended once released: True`). A thread that waits on that event lives exactly as long as the task (INFERRED), so spec 036's abandoned-thread quota and `tool_threads_running` would cover an async tool that ignores its cancel with no new count.

### 5. The ends that can bite (EXECUTED)

- **A closed loop** refuses the post: `RuntimeError: Event loop is closed` (case A5). A tool call posted to a caller's loop that has closed must be answered as a fault, never hang.
- **`KeyboardInterrupt` and `SystemExit` raised in a task leave the loop:** `asyncio.run raised KeyboardInterrupt` (and `SystemExit`), on both versions (case A6). A tool's `BaseException` on the caller's loop would surface in the embedder's own `asyncio.run`, far from the call. A wrapper that catches `BaseException` keeps it in the call (`in a wrapper: caught …`), as spec 031's `_Work` keeps a sync tool's.
- **A task that ignores its cancel keeps a private loop's thread alive** (case A8, `suppresses: … alive a second after the shutdown request: True`) until it ends (`ended once released: True`). The call's end must not wait for that thread.

### 6. What counts as async (EXECUTED)

Case A9: `inspect.iscoroutinefunction` is true for an `async def`, a `functools.partial` of one and an object whose class's `__call__` is `async def`; false for an async generator function and for a plain `def` that returns a coroutine. `inspect.isawaitable` is true for a coroutine object and a `Future`, false for an async generator object. A coroutine object made on one thread runs on another thread's loop (case A7: made on the main thread, it ran on `'loop-thread'`): calling an `async def` runs none of its code.

So one rule covers every form: call the gate or the tool where spec 036 calls it, and if what it returns is awaitable, await that on a loop. An async generator is neither and is refused up front (INFERRED: protocol 1 answers once; a stream is out of its scope, spec 031's Scope).

### 7. A prototype through the real runner (EXECUTED)

`prototype_probe.py`, against the frozen artifact set `build/sets/s-f94dec535086b06c` (main's tree; it carries the guest package) and wasmtime-py 49.0.0, on darwin-arm64. It patches, in its own process only, `tools._Work` to await an awaitable result on a loop and wait for the task's real end (finding 4), and `tools._Bounded._abandon` to ask the in-flight task to cancel. Since `tool()` still refuses `async def`, each tool is a plain function returning a coroutine (finding 6's rule covers it). A real guest calls `from host import tools`:

| case | what it showed |
|---|---|
| B1 `run`, a private loop | exit 0; `{'n': 3, 'thread': 'wasi-python-tool-loop'}`; outcomes `list ok`, `call fetch ok` |
| B2 `run_async` | exit 0; the tool ran on the caller's loop (`True`), which turned meanwhile (`True`) |
| B3 `timeout_s=0.05` | the guest printed `ToolTimeout stall timed out after 0.05 s`; outcome `timeout`, abandoned `True`; the task saw `CancelledError` (`True`); tool threads back to where they were (`True`) |
| B4 `deadline_s=1`, no `timeout_s` | `ToolTimeout stall timed out at the run's deadline`; the task saw `CancelledError` (`True`) |
| B5 the `run_async` task cancelled during an async tool | the task raised `CancelledError`; the tool's task saw `CancelledError` (`True`); the next call on the same loop printed its answer |

The guest, the door, the frame host and the bound needed no change beyond the two patched acts. The guest package was not touched: it calls the door synchronously either way.

## What this means for the specification (INFERRED)

1. An async tool can be served entirely in the runner. The guest's package, the zip, the binary and the protocol's frames do not change, so the work is not build-class.
2. The loop: the caller's under `run_async` (finding 1), a private one per call under `run` (finding 2), started only when a call first meets an awaitable and shut down, without waiting, when the call ends.
3. The wait: keep spec 036's thread per call and its bound; post only the awaitable to the loop, wrapped so its real end is seen (finding 4), and keep the gate and the result's encoding off the embedder's loop.
4. The ends: each of 036's ends also asks the task to cancel. That is what "under the call's deadline" can mean for a coroutine, which, unlike a sync function, can be stopped at its next `await`.
5. Faults: a closed loop, a `BaseException`, a cancel nobody asked for: each a `tool_error` fault in the record, as for a sync tool (finding 5).
6. The raw door stays synchronous; decision 15 puts the async host function "with the tool protocol". An `async def` passed as `host=` should be refused up front rather than answer −2 to every frame.

## Not studied

- `batch` (many calls in one frame, so a guest gets concurrency from async tools). It is a protocol operation and a guest change, so build-class; spec 053 leaves it out and asks the owner where it belongs (question 90).
- Async mount providers (spec 032's `FileProvider`). Their calls are many, short and made synchronously by the guest's libc; decision 15 names the tool protocol only.
- trio. `run_async` is asyncio only (spec 015); under trio an embedder calls `run` from a worker thread, and its async tools would then run on a private asyncio loop.

## One line

An async tool needs only the runner: post its coroutine to the caller's loop under `run_async` or to a loop of the call's own under `run`, wait for the task's real end on spec 036's tool thread, and cancel the task at every end the bound already has.
