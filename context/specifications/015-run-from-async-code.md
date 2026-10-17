# 015 — Run from async code

- **Status:** built and reviewed 2026-10-17 (`../reviews/015-run-from-async-code-2026-10-17.md`);
  revised twice before build against its pre-build review and its confirmation
  (`context/reviews/015-run-from-async-code-spec-2026-10-17.md`).
- **Owner:** Clay Gendron
- **Kind:** the runner (`src/wasi_python/runner.py`, `src/wasi_python/__init__.py`), judge
  additions in `tests/`, `README.md`, `CHANGELOG.md`.
- **Depends on:** 010 (waits end at the deadline), 011 (concurrent calls share nothing), 013 and
  014 (arguments checked before any work).
- **Research it stands on:**
  - The owner's requirement (2026-10-17): the project "needs to work with FastAPI or more
    generally with async web server programs", with "multiple python instances running at once
    that don't block the main application".
  - The author's probe (EXECUTED; benchmark facts, scratch `async/probe.py`; re-run by the
    reviewer with the same shape). On a 10-core Mac, one CPU-bound guest takes 4.39 s. Through
    `asyncio.to_thread`:

    | guests at once | wall time | parallel speedup | event-loop lag, max |
    |---|---|---|---|
    | 1 | 4.39 s | 1.0× | 2.3 ms |
    | 4 | 4.88 s | 3.6× | 13.9 ms |
    | 8 | 6.94 s | 5.1× | 21.4 ms |

    wasmtime-py releases the GIL while wasm runs, so guests run in parallel and the loop stays
    responsive. Calling `run()` directly in a coroutine blocked the loop for 4,377 ms.
  - The author's prototype and the reviewer's probes (EXECUTED, scratch `async/cancel_proto.py`,
    `rev015a/e1…e7`). A store gets an epoch-deadline callback through wasmtime's C API,
    `wasmtime_store_epoch_deadline_callback`, from the same private binding module
    `wasmtime._ffi` that spec 011 already uses. It stopped a busy guest on the real runner, on
    both binaries, with and without fuel. It runs on the guest's own thread. 20,000 returned
    errors leaked nothing. Fuel stayed exact (3,300,000,002 with and without 962 callbacks).
  - The reviewer's per-tick cost (EXECUTED, benchmark facts, 16 guests on 10 cores): with the
    main thread idle, about 1–2% more CPU; with the main thread busy in Python, 13–17% more wall
    time at one callback per tick, because each callback waits for the GIL.

## The problem

`run` is synchronous. It is safe and parallel from threads, but an async application has three
problems:
- it must know to move the call off the event loop;
- it has no way to stop a guest whose request was cancelled: the guest runs to its deadline,
  60 s by default;
- it has no bound on how many guests run at once, each allowed 1 GiB by default.

A web server that runs untrusted code per request needs all three. Two more come with servers:
they fork worker processes, and they exit with work in flight.

## Decisions

1. **`run(..., cancel=None)`.** The caller may pass a `threading.Event`. Once it is set and the
   guest runs, the guest stops within `CANCEL_TICKS` ticks (5 ticks of `TICK_S`, 50 ms), whether
   it computes or waits. The call returns `trapped == "cancelled"`, with `fuel_used` `None`, as
   for any interrupted call. `run` also checks the event once just before it instantiates, so a
   call cancelled during compilation or set-up never starts the guest; it returns the same
   result. Before that point (finding the artifacts, compiling, placing the zip) the event is not
   watched.
   - **The first deadline.** A store whose call has a `cancel` gets an epoch deadline of
     `min(CANCEL_TICKS, ticks)` ticks, not `ticks`, so the callback first runs within
     `CANCEL_TICKS` ticks whatever the call's deadline (`ticks` is 2**62 under
     `deadline_s=None`). A call without `cancel` keeps `ticks`.
   - **The callback.** One module-level `CFUNCTYPE` callback, `_on_epoch`, is set on every store
     whose call has a `cancel`, with a NULL finalizer. It finds its `_Call` the way spec 011's
     shared functions do: the top of this thread's stack, checked against the caller's context
     address. No per-call ctypes object exists. A call without `cancel` gets no callback and is
     unchanged.
   - **Its outcomes, in this order:**
     1. a recorded stop (`call.stopped`, spec 011: a host's exception, an exit, Ctrl-C): answer
        with an error, so the stop holds;
     2. Ctrl-C pending while the runner defers it on this thread (spec 011's flag): record
        `KeyboardInterrupt` as the stop and answer with an error. This closes spec 011's "a guest
        that never waits" hole for these calls;
     3. the event is set: record `"cancelled"` on the call (`call.ended`) and answer with an
        error;
     4. the call's deadline has passed (`count >= stop_at`, the test spec 010's waits use):
        record `"deadline"` and answer with an error. So a deadline never ends early;
     5. otherwise continue: write `delta[0] = min(CANCEL_TICKS, ticks left to the deadline)`, at
        least 1, and return 0.
   - **No call found.** The stack is pushed before instantiation, so the callback always finds its
     call; if it ever does not (the lookup raises, or no context matches), it sets a flag on this
     thread (`_calls.lost`) and answers with an error, which stops the guest. `_drive` clears the
     flag when it pushes the call, and reads and clears it after the pop; if it was set, it raises
     `RuntimeError("wasi_python lost track of a call")` rather than name an outcome it does not
     know. So a stale flag never reaches the next call on that thread. A unit test drives both halves with fakes.
   - **Its faults.** The whole body sits in `try/except BaseException`. Every path returns an
     int: 0 after writing a `delta` of at least 1, or an error made with `wasmtime_error_new`. On
     an exception the callback records it as the call's stop and answers with an error, so a
     fault stops the guest; `_drive` then raises it, as for any recorded stop. The callback never
     writes `kind` (wasmtime panics on a value other than 0 or 1) and never deletes the error it
     returns (wasmtime owns it).
   - **Naming the outcome.** An error from the callback reaches Python as `WasmtimeError` with a
     backtrace message, and a store with a callback never traps with `INTERRUPT`. So `_drive`
     never parses the message: after `call.stopped`, it reads `call.ended`. `_fuel_used` returns
     `None` when `call.ended` is set.
   - **The ticker.** It runs while any call with a deadline or a `cancel` runs, so a cancelled
     guest under `deadline_s=None` still stops. A busy guest under `cancel=` stops at its deadline
     1–2 ticks later than without it (spec 010's `+ 1`, and the count trailing the engines).
   - **A waiting guest.** `_Waits` checks `cancel.is_set()` with the deadline, and a call with a
     `cancel` has its waits sliced even under `deadline_s=None`; the wait ends, and the callback
     names the outcome at the guest's next tick.
   - **Cost.** One callback per `CANCEL_TICKS` ticks while the guest computes, not one per tick,
     which divides the reviewer's measured cost by about five. The latency is the price, and
     50 ms is below what a web request notices.
   - **Nested calls.** A `run` from inside a door has its own store and its own `cancel`. The outer
     call's `cancel` is seen when the outer guest runs again.
2. **`run_async(...)`.** A coroutine with `run`'s arguments except `cancel`, plus
   `executor=None`. It returns `run`'s `Completed`.
   - **Arguments** are checked as in specs 013 and 014, in the coroutine, before anything is
     queued, so a bad argument raises at once. The worker calls an inner entry point that does not
     check them again. `run_async` takes no `cancel`: a caller cancels its task.
   - **The executor.** The caller's `concurrent.futures.Executor`, which must run callables on
     threads of this process. `ProcessPoolExecutor` and `InterpreterPoolExecutor` are refused by
     type with `TypeError` (the second is looked up with `getattr` and checked first: it exists
     only from 3.14, and it subclasses `ThreadPoolExecutor`): neither can carry a `threading.Event` or a host callable. Without one,
     the runner's default pool (Decision 4).
   - **The mechanism.**
     1. Make a fresh `threading.Event` for the call and register it (Decision 6).
     2. `cf = executor.submit(contextvars.copy_context().run, inner, …, cancel=event)`, so a door
        host sees the request's context variables, as `asyncio.to_thread` gives it.
     3. `await asyncio.wrap_future(cf)`.
     4. On `CancelledError`: if `cf.cancel()` returns true, the call never started; re-raise.
        Otherwise set the event, then `await asyncio.wrap_future(cf)` until `cf.done()`, swallowing
        any outcome of the call (a further `CancelledError`, the call's result, or an exception the
        call raised), and re-raise the first `CancelledError`, so `asyncio.timeout` still turns it
        into `TimeoutError`.
     5. In a `finally`, the event leaves the registry.
     So when a cancelled `run_async` raises, its worker is free and the guest's memory, `HOME` and
     private root are gone. `asyncio.timeout` still raises `TimeoutError` (EXECUTED by the
     reviewer).
   - **What bounds the wait.** It is bounded while the guest is in wasm or in a wait. A door host
     that blocks keeps the worker, and keeps the cancelled task waiting: the epoch does not
     interrupt host code. The README says so.
   - It never blocks the event loop: argument checks, submitting and awaiting are all it does
     there. A shut-down executor raises `RuntimeError` from `submit`, and after interpreter
     shutdown has begun the message is "cannot schedule new futures after interpreter shutdown"
     (or, on a first `run_async`, the same kind of error from registering the exit hook). All pass
     through.
3. **Ctrl-C.** Calls from `run_async` run on worker threads, where spec 011's deferral does not
   apply and is not needed: Python delivers SIGINT to the main thread, where the event loop or the
   server handles it. `run(cancel=)` on the main thread is covered by Decision 1's outcome 2. Under
   an embedder's own raising SIGINT handler, a `KeyboardInterrupt` can land at the callback's
   first bytecode, outside its `try`, as at spec 011's trampoline; the README's advice for that
   handler (run on a worker thread) names the callback too.
4. **The default pool.** One process-wide `ThreadPoolExecutor`, made under `_lock` on first use,
   with `DEFAULTS.async_workers` workers.
   - `Defaults` gains `async_workers`, a field with a default, so `Defaults` built from its
     first three arguments works as before. Its default is `min(cpus, 8)`, where `cpus` is
     `os.process_cpu_count()` where it exists (3.13), else `os.cpu_count()`, else 1. It is checked
     like the other limits: an integer from 1 to 1024, never `bool`.
   - **Why 8** (§4.15, a new limit needs a stated reason): at the defaults, a worker holds up to
     1 GiB of guest memory, 32 MiB of output and a copy of `stdin`, so 8 workers bound a process
     at about 8.3 GiB. Past 8 the measured speedup flattens (5.1× at 8 on 10 cores). A host with
     more memory raises it.
   - `os.process_cpu_count()` honours CPU affinity; neither it nor `cpu_count()` sees a
     container's CPU quota. The README says so, and says to set `async_workers` in a container.
   - Setting `DEFAULTS` to a new value takes effect at the next `run_async`: if the size differs,
     a new pool is made, and the old one is shut down without waiting, so its calls finish. The
     lookup, any resize and the `submit` happen under one lock, so a resize on another thread
     never makes a `submit` meet a shut-down pool. During a resize the old pool's running calls
     and the new pool's overlap, so for that time more than `async_workers` guests can run.
   - The bound covers `run_async` on the default pool only. It does not cover `run` from the
     caller's own threads, a caller's executor, or a framework's thread pool for synchronous
     endpoints. The README gives the arithmetic per process, with output, disk (the 0.1.0a2
     review's F2) and descriptors, and multiplies it for a server with several worker processes.
5. **Fork.** A process forked after the runner made an engine cannot run guests safely:
   the child inherits state from threads that no longer exist (locks inside wasmtime, the
   runner's `_lock`, the ticker's condition), wasmtime does not support use across a fork, and on
   macOS it aborts in the child. The runner refuses on every host rather than rely on what
   wasmtime does not promise. So:
   - A flag, `_used`, is set just before the runner first calls `wt.Engine`. Where
     `os.register_at_fork` exists (not on Windows, which has no fork), an `after_in_child` hook
     takes no lock and only assigns: it drops the default pool, resets the epoch ticker
     (`_thread = None`, `_active = 0`) and the live-events registry, and, if `_used` is set,
     marks the child as forked. The parent's engines, modules and linkers stay in the runner's
     caches and are freed at the child's exit as they would be in the parent. The reviewer ran
     that for a parent that was idle when it forked, and it was harmless (EXECUTED,
     `rev015b/f1_fork_exit.txt`). A parent that forks while a guest runs on another thread is not
     covered: its child could hang at exit (INFERRED, not run). The README's advice, warm up after
     the fork, avoids both.
   - In such a child, `run` and `run_async` raise `RuntimeError` before any work and before
     taking any lock: "wasi_python was
     used before this process was forked; use it in the child only, or start processes with
     'spawn' or 'forkserver'".
   - A child of a parent that only imported `wasi_python` runs normally: wasmtime sets up its
     trap handling in `Engine::new` (READ), and the reviewer ran such a child on macOS
     (EXECUTED).
   - The README says: warm the runner up after the fork (for example in gunicorn's `post_fork`),
     never before.
6. **Exit.** At interpreter exit, guests started by `run_async` are stopped and queued calls are
   not started, so exit waits at most `CANCEL_TICKS` ticks for each running guest plus its
   clean-up, except for a worker in host code (below).
   - Every live `run_async` event is in a registry. On the first `run_async`, the runner imports
     `concurrent.futures.thread` and then registers a hook with `threading._register_atexit` (the
     hook `concurrent.futures` itself uses). `threading` runs those hooks in reverse order of
     registration, so ours runs before that module's join of the pool's workers; registered
     before that import it would run after, and exit would hang (EXECUTED by the confirming
     reviewer, both orders, `rev015b/x1_order.txt`). The hook sets each event and shuts every
     default pool down with `cancel_futures=True`. If that private hook is missing, `atexit` is
     used and the README's sentence on exit says that exit can wait.
   - The bound holds while each worker's guest is in wasm or in a wait. A worker inside a door
     host, compiling a module or placing the zip keeps exit waiting until that step ends.
   - `run` from the caller's own threads is unaffected: those threads are the caller's.
7. **Checks.** Each check counts; none measures time. Each new test is seen failing first.
   - v1.4, `test_async_calls_do_not_block_the_loop`. Four `run_async` calls of a guest that first
     calls the door, then prints its token. The door's host waits on a `threading.Event` that a
     coroutine sets once it has counted 1,000 turns of `await asyncio.sleep(0)`. A blocked loop
     never counts, so the host's 120 s fail-safe answers `b"late"` and the guest prints `LATE`.
     Each call must print its own token, and none `LATE`.
   - v1.4, `test_cancelling_an_async_call_stops_its_guest[busy|sleeping]`, in a child process with
     `tempfile.tempdir` set to an empty directory. The executor is a one-worker
     `ThreadPoolExecutor`, wrapped to count finished items. The guest calls the door, which sets a
     `started` event, then loops forever or sleeps `10**6` s, under `deadline_s=None`, with no
     other call running. The coroutine awaits `started` through `asyncio.to_thread`, then cancels
     the task. The task must raise `CancelledError`; at that moment the finished count must be 1
     and no `wasi-python-*` entry may remain in the directory; then a new call on the same
     executor completes. A 120 s fail-safe guards the child.
   - The three checks below run their call in a child process with the 120 s fail-safe, because
     the defect each one guards would make the call run forever:
     - v1.4, `test_run_with_cancel[busy|sleeping]`: the door's host sets the call's own event and
       returns; the guest then loops or sleeps under `deadline_s=None`. `trapped ==
       "cancelled"`, and `fuel_used is None` under a fuel cap.
     - v1.4, `test_a_stop_holds_under_cancel`: a door host raises `CancelledError` under
       `cancel=`, and the guest catches the door's error and computes, under `deadline_s=None`;
       `run` raises `CancelledError`.
     - v1.4, `test_a_deadline_under_cancel_is_named`: a busy guest under `cancel=` and
       `deadline_s=0.2` reads `trapped == "deadline"`, with `fuel_used is None` under a fuel cap.
   - "Seen failing first" means against a stand-in that has the API but lacks the property, not
     only against a missing name: a `run_async` that calls `run` inside the coroutine (the
     non-blocking check, which must then reach its fail-safe and print `LATE`), a callback that
     always continues (the cancellation, stop and
     deadline checks), a `run_async` that awaits without waiting for its worker (the cancellation
     check), no exit hook (the exit check), and no fork hook (the fork check). The build review
     records each.
   - v1.4, `test_exit_stops_async_guests`: a child runs a loop on a daemon thread, starts two
     `run_async` calls of a busy guest under `deadline_s=None` on a one-worker default pool,
     waits until the first has called the door, and returns from its main module. The child must
     exit 0 within the 120 s fail-safe.
   - v1.4, `test_a_forked_child_is_refused` (POSIX): a fresh parent process, started for the
     check, runs one call, then forks; in the
     child, `run` raises the `RuntimeError` above and the child exits 0, with no abort and no hang.
     A child of a parent that only imported the package runs a call.
   - Unit: the callback's five outcomes with fakes, in order; an `is_set` that raises gives an
     int, a recorded stop and an error; a stack lookup that raises sets `_calls.lost`, gives an
     int and an error, and `_drive` then raises `RuntimeError` and leaves the flag clear; `delta`
     is never written below 1.
   - Unit: `run_async` refuses a bad argument and a process or interpreter pool before the executor
     is called (the interpreter pool case skips where it does not exist); `async_workers` is
     checked like the other limits; `Defaults` built from three arguments still works.
   - The binding check in `tests/unit/test_runner_calls.py` gains
     `wasmtime_store_epoch_deadline_callback` (its four `argtypes`) and `wasmtime_error_new`.
8. **Docs.** The README gains "From async code":
   - an ASGI endpoint (FastAPI shown) that awaits `run_async` inside `asyncio.timeout(...)`; the
     timeout also bounds the time a request waits in the queue, since `deadline_s` starts only
     when a worker picks the call up;
   - what cancels a call: the task being cancelled, by the app's timeout, a task group or
     shutdown. A client that disconnects does not cancel a plain endpoint's task in Starlette, so
     its guest runs to its deadline; the README says that and claims nothing more;
   - a synchronous endpoint that calls `run` already keeps the loop free, in the framework's
     thread pool, but cannot be cancelled and is not bounded by `async_workers`;
   - the arithmetic per process (Decision 4), forking (Decision 5) and exit (Decision 6);
   - a door host that must await something uses
     `asyncio.run_coroutine_threadsafe(coro, loop).result(timeout=…)`, never without a timeout;
   - `run_async` is asyncio only; under trio, use `run(cancel=)` from a worker thread.

   The CHANGELOG gains a line.

## Intent

An async web server can run many untrusted guests at once without blocking its event loop, with a
stated bound per process, and a cancelled request stops its guest within about 50 ms once the
guest runs, when other Python threads leave the GIL free.

## Design

```
src/wasi_python/runner.py   run(cancel=); _on_epoch; _Call.ended; _Waits checks cancel;
                            run_async(); the default pool; Defaults.async_workers;
                            the fork and exit hooks
src/wasi_python/__init__.py run_async exported
tests/unit/…                the callback's outcomes and faults; run_async's refusals;
                            async_workers; the bindings
tests/checks/test_v1_4_embedding.py   the loop is not blocked; cancellation stops the guest;
                            run(cancel=); stops and deadlines under cancel; exit; fork
README.md, CHANGELOG.md
```

## Scope

In: the above. Out:
- a process pool: wasm already runs in parallel on threads;
- a warm instance pool (the principal engineer's direction 10);
- an async door, or a door bounded by host time: a later specification (the agent-runtime memo,
  item 3);
- a per-call queue-time limit: `asyncio.timeout` around the call covers it;
- trio: `run(cancel=)` is the portable piece;
- free-threaded CPython, as in spec 011;
- a container's CPU quota: the caller sets `async_workers`.

## Acceptance criteria

1. The checks exist and were seen failing before the change.
2. `uv run pytest` is green with `--accept-judge`.
3. A dry run of the release workflow passes every job.

## Landing notes

Built 2026-10-17 by the implementer (Claude Opus 5.5) in a scratch clone of `main`, after the
pre-build review and its two confirmations passed it for build. **Not yet reviewed and not
accepted.** Every claim below was run (EXECUTED) on macOS arm64, CPython 3.14.2, wasmtime-py
49.0.0, against the 0.1.0a2 artifact set, unless it says otherwise.

### What was built

- `run(cancel=)`, `run_async(executor=)`, `Defaults.async_workers`, the epoch callback
  (`_epoch_answer`, `_on_epoch`, `_watch`), the default pool, the exit hook and the fork hook, all
  in `src/wasi_python/runner.py`; `run_async` exported from the package. `run` is split into
  `_checked` (every argument, before any work) and `_run_checked` (the worker's entry), so
  `run_async` checks in the coroutine and the worker never checks again.
- `cancel` must be a `threading.Event`; anything else is refused with `TypeError` before any
  work, like the other arguments.

### One change to Decision 1, found while building

Decision 1 said a waiting guest's wait ends at the cancel "and the callback names the outcome at
the guest's next tick". EXECUTED: a guest whose `time.sleep` ended at the cancel then finished
before its next callback, so the call returned `exit_code 0` instead of `"cancelled"`. Now, when
a shared host function (a wait or the door) returns while the call's event is set, it sets the
store's epoch deadline to 0, as spec 011's stop does; the callback then runs at the guest's next
function entry and names the call `"cancelled"`. `test_run_with_cancel[sleeping]` covers both
halves together, and a unit test (`test_a_host_function_returning_under_a_set_event_stops_the_guest`)
the host function's half alone (the build review, F4).

### Seen failing first (Decision 7)

Against `main` each new check fails for a missing name. Against the stand-ins (scratch
`build015/standins.py`, output `standins.txt`), each runner change made by text replacement and
reverted afterwards:

| stand-in | checks that fail |
|---|---|
| `run_async` runs the call in the coroutine | `test_async_calls_do_not_block_the_loop` (the host's fail-safe answered: LATE) |
| the epoch callback always continues | `test_run_with_cancel[busy]` and `[sleeping]`, `test_a_stop_holds_under_cancel`, `test_a_deadline_under_cancel_is_named`, `test_cancelling_an_async_call_stops_its_guest[busy]` and `[sleeping]` |
| `run_async` does not wait for its worker | `test_cancelling_an_async_call_stops_its_guest[busy]` and `[sleeping]` |
| no exit hook | `test_exit_stops_async_guests` (the child never exits; the 120 s fail-safe) |
| no fork hook | `test_a_forked_child_is_refused` |

In the first build, `test_cancelling_an_async_call_stops_its_guest[sleeping]` passed under "the
callback always continues": the cancel ended the sleep and the guest exited. Its guest now
computes once it wakes, so only the callback can end it, and that stand-in fails it too (the
build review, F5; EXECUTED, scratch `build015/standins2.txt`).

After the build review, each new check was also run against the code without its behaviour
(`standins2.txt`), and each failed: no deadline of 0 after a host function under a set event; no
check before instantiating; the first `_stop_error`, which left `delta` at 0 when no error could
be made; and no context copy (the loop check's `ContextVar`).

The unit tests (`tests/unit/test_runner_async.py`, 12) cover the callback's five outcomes and
their order, a fault, a context that is not the call's, the lost-call flag and `_drive`'s
`RuntimeError`, `run_async`'s refusals before queueing, `async_workers`, a `cancel` that is not
an event, and the fork refusal. The binding check gains the callback's and the error's shapes.

### The judge

`uv run pytest` in the clone, rebased onto `11085c7` (Release 0.1.0a2), artifacts from the main
tree, before the build review (the landing's run on `main` follows): 147/155 pass, 0 gap, 0 fail, 8 blocked (the clone has no source trees, oracle, prior-art
clones or wheel); v1.4 57/57; unit suite 308/314, 6 skipped; ratchet lost 0, gained 9, grew 0;
judge changed: `tests/checks/test_v1_4_embedding.py`, `tests/unit/test_runner_async.py`,
`tests/unit/test_runner_calls.py`. ruff check and format: clean. The `--accept-judge` run is made
on `main` after the build review.

### After the build review

- The README and CHANGELOG no longer promise "within 50 ms" with no condition: the check runs
  every 50 ms while the guest computes and at once at a wait or a door call, and needs the GIL,
  as does the clean-up; the reviewer's measurement with another thread spinning is quoted (F1).
- `_stop_error` writes a `delta` of 1 on every path that makes no error, and a unit test runs the
  real function (F2).
- The exit hook marks the runner as exiting and shuts the pools down before it sets the events,
  and `_submit` refuses once it is exiting, so a call cannot slip between the two (F3).
- Three new unit tests and a `ContextVar` in the loop check (F4); the sleeping async guest
  computes after it wakes (F5).
- `asyncio`, `concurrent.futures` and `contextvars` are imported where they are used: `import
  wasi_python` loads 92 modules, as on `main` (F6, EXECUTED).
- The fork hook makes every lock the runner takes anew, and empties `_compiling` (F8).
- The README's argument list, `trapped` values, the Ctrl-C note and the exit fallback are
  corrected (F9).
- The build review's confirmation (verdict: lands) found one more gap, N1: a call on the caller's
  own executor could still slip past the exit hook. `run_async` now checks the hook's `exiting`
  flag under `_live_lock`, where it adds its event, and the hook sets that flag before it reads
  the events.

### Left over

- The per-tick cost under a busy event loop (the review's finding 12) is not re-measured with
  `CANCEL_TICKS = 5`.
- FastAPI itself was not run: the README example is the shape of an ASGI endpoint, and what it
  says about disconnects is from Starlette's documented behaviour (INFERRED).
- Windows and Linux run these checks first in the release workflow's verify jobs.
