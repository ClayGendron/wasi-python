# 015 — Run from async code

- **Status:** draft, 2026-10-17. It changes the runner's API, so it is reviewed before it is
  built.
- **Owner:** Clay Gendron
- **Kind:** the runner (`src/wasi_python/runner.py`, `src/wasi_python/__init__.py`), judge
  additions in `tests/`, `README.md`, `CHANGELOG.md`.
- **Depends on:** 010 (waits end at the deadline), 011 (concurrent calls share nothing), 013 and
  014 (arguments checked before any work).
- **Research it stands on:**
  - The owner's requirement (2026-10-17): the project "needs to work with FastAPI or more
    generally with async web server programs", with "multiple python instances running at once
    that don't block the main application".
  - The author's probe (EXECUTED; benchmark facts, scratch `async/probe.py`). On a 10-core Mac,
    one CPU-bound guest takes 4.39 s. Through `asyncio.to_thread`:

    | guests at once | wall time | parallel speedup | event-loop lag, max |
    |---|---|---|---|
    | 1 | 4.39 s | 1.0× | 2.3 ms |
    | 4 | 4.88 s | 3.6× | 13.9 ms |
    | 8 | 6.94 s | 5.1× | 21.4 ms |

    wasmtime-py releases the GIL while wasm runs, so guests run in parallel and the loop stays
    responsive. Calling `run()` directly in a coroutine blocked the loop for 4,377 ms.
  - The author's prototype (EXECUTED, scratch `async/cancel_proto.py`). A store gets an
    epoch-deadline callback through wasmtime's C API,
    `wasmtime_store_epoch_deadline_callback`. That is the same private binding module
    `wasmtime._ffi` that spec 011 already uses and pins.
    - Another thread set a cancel flag at 0.50 s.
    - A guest in an endless loop stopped at 0.51 s.
    - The callback runs on the guest's own thread, so no store is touched from another thread.

## The problem

`run` is synchronous. It is safe and parallel from threads, but an async application has three
problems:
- it must know to move the call off the event loop;
- it has no way to stop a guest whose request was cancelled: the guest runs to its deadline,
  60 s by default;
- it has no bound on how many guests run at once, each allowed 1 GiB by default.

A web server that runs untrusted code per request needs all three.

## Decisions

1. **`run(..., cancel=None)`.** The caller may pass a `threading.Event`. Once it is set, the
   guest stops within one tick (`TICK_S`, 10 ms) whether it computes or waits, and the call
   returns `trapped == "cancelled"`. `fuel_used` is `None`, as for any interrupted call.
   - **How it stops a computing guest.** A store with a `cancel` gets an epoch deadline of one
     tick and an epoch-deadline callback. At each tick, on the guest's own thread, the callback
     does one of three things:
     - stops the guest with a trap the runner reports as `"cancelled"`, if the event is set;
     - stops it as `"deadline"`, if the call's deadline has passed (spec 010's `stop_at`
       count);
     - otherwise extends the deadline by one tick.

     The epoch ticker runs while any such call runs. A call without `cancel` is unchanged.
   - **How it stops a waiting guest.** A wait in `poll_oneoff` also ends when the event is
     set: `_Waits` checks it with the deadline.
   - **Safety.** The callback is one more host function in the sense of spec 011. It never
     raises into wasmtime-py: it answers with a wasmtime error made through the C API.
     Its C callback object and data are held by the call, and the epoch-deadline callback has
     its own C finalizer (a no-op), so no wasmtime-py table is touched.
2. **`run_async(...)`.** A coroutine with `run`'s arguments, plus `executor=None`, which
   returns `run`'s `Completed`.
   - It runs `run` in an executor:
     - the caller's `concurrent.futures.Executor` if one is given;
     - otherwise one process-wide `ThreadPoolExecutor` the runner makes on first use, with
       `os.cpu_count()` workers.

     Calls beyond that many wait their turn, so concurrent guests are bounded by the pool, and
     so is their memory (workers × `memory_bytes`). The README states the arithmetic.
   - It passes its own `cancel` event. If the awaiting task is cancelled, `run_async` sets the
     event, waits for the call to end (one tick, then the usual clean-up of the store, `HOME`
     and a private root), and re-raises `CancelledError`. So cancellation frees the worker and
     the guest's memory before the caller moves on. A call still queued is not started.
   - Arguments are checked as in specs 013 and 014. The check runs before the call is queued,
     so a bad argument raises at once, in the coroutine.
   - It never blocks the event loop: argument checks, queueing and awaiting are all it does
     there.
3. **Ctrl-C.** Calls from `run_async` run on worker threads, so spec 011's deferral does not
   apply and is not needed: Python delivers SIGINT to the main thread, where the event loop or
   the server handles it. Shutting down the default pool at exit cancels nothing; a server
   shuts down by cancelling its tasks, which stops their guests (Decision 2).
4. **Checks.** Each check counts; none measures time.
   - A v1.4 check, `test_async_calls_do_not_block_the_loop`. Four `run_async` calls of a
     CPU-bound guest run while a coroutine counts its own turns of `await asyncio.sleep(0)`.
     The count must reach at least 1,000 before the calls end. A blocked loop counts 0 to a
     handful. Each call must return its own output.
   - A v1.4 check, `test_cancelling_an_async_call_stops_its_guest`. A guest that loops forever
     (and one that sleeps `10**6` s) runs under `deadline_s=None`. Its task is cancelled once
     the guest has started, signalled by a door call. The task must raise `CancelledError`, and
     afterwards the call's private root must be gone and the pool must accept a new call that
     completes. A 120 s fail-safe, not a timing, guards it.
   - A v1.4 check that `run(cancel=event)` returns `trapped == "cancelled"` and
     `fuel_used is None` for a busy guest and a sleeping one.
   - A unit test of the epoch-deadline callback's three outcomes, with fakes.
   - A unit test that `run_async` refuses a bad argument before queueing: the executor is never
     called.
   - Each new test is seen failing first.
5. **Docs.** The README gains a short "From async code" section with a FastAPI example (an
   endpoint that awaits `run_async`) and the memory arithmetic. The CHANGELOG gains a line.

## Intent

An async web server can run many untrusted guests at once without blocking its event loop, and
a cancelled request stops its guest within a tick.

## Design

```
src/wasi_python/runner.py   run(cancel=); the epoch-deadline callback; _Waits checks cancel;
                            run_async(); the default pool
src/wasi_python/__init__.py run_async exported
tests/unit/…                the callback's outcomes; run_async checks before queueing
tests/checks/test_v1_4_embedding.py   the loop is not blocked; cancellation stops the guest;
                            run(cancel=)
README.md, CHANGELOG.md
```

## Scope

In: the above. Out:
- a process pool: wasm already runs in parallel on threads;
- a warm instance pool (the principal engineer's direction 10);
- an async host function: the door stays synchronous, and a host that must await something
  runs it with `asyncio.run_coroutine_threadsafe` on its own loop, which the README shows in one
  line.

## Acceptance criteria

1. The checks exist and were seen failing before the change.
2. `uv run pytest` is green with `--accept-judge`.
3. A dry run of the release workflow passes every job.

## Landing notes

Not built.
