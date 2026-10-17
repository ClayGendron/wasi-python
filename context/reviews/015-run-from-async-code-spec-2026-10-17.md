# Review of 015 — Run from async code (the specification, before build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I read `AGENTS.md`, the
  constitution (§4.15 included), `context/reviews/README.md`, the 014 pre-build review (for its
  format), specs 010 and 011, the specification, and the runner (`_instance`, `_drive`, `_Call`,
  `_shared`, `_Waits`, `_stop_at`, `_epoch_ticker`, `_send_outputs`, `_deferred_ctrl_c`,
  `_trap_name`, `_release`). I also read wasmtime-py 49's `_bindings.py`, `_store.py` and
  `_func.py`, wasmtime 49's C API and store (`context/prior_art/wasmtime-v49/crates/c-api/src/store.rs`,
  `crates/c-api/include/wasmtime/store.h`, `crates/c-api/src/lib.rs`,
  `crates/wasmtime/src/runtime/store.rs`, `crates/wasmtime/src/runtime/vm/libcalls.rs`), and
  CPython 3.14's `Modules/_ctypes/callbacks.c` and `Lib/concurrent/futures/thread.py`. Each claim
  is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `context/specifications/015-run-from-async-code.md` as drafted (untracked), against
  the runner on `3ee5bbe`. The working tree also holds another author's uncommitted runner change
  (the store is now closed inside `_instance`; the 0.1.0a2 security review's F1). I read it for
  context only.
- **Ran (EXECUTED, darwin-arm64, 10 cores, host CPython 3.14.2, wasmtime-py 49.0.0, the artifacts in
  `build/artifacts/` read only, `WASI_PYTHON_CACHE=$PWD/build/cwasm-cache`).** The runner was not
  edited. Where a probe needed the callback on the real runner, it wrapped `runner._drive` from
  outside. Scripts and outputs are under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev015a/`:
  - `probe_rerun.txt`, `cancel_proto_rerun.txt`: the author's two probes, re-run;
  - `e1_callback.py` → `e1_callback.txt`: the callback on WAT modules (the error's type and text,
    fuel, ownership over 20,000 returns, a spec 011 stop);
  - `e1b_raise.py` → `e1b_raise.txt`: a callback that raises, or returns `None`;
  - `e2_bench.py` → `e2_bench.txt`: the per-tick cost with 16 busy guests (benchmark facts);
  - `e3_async.py` → `e3_async.txt`: `run_async`'s cancellation, prototyped with a fake `run`;
  - `e4_fork.py` → `e4_fork.txt`: a forked child of a process that used the runner;
  - `e5_turns.py` → `e5_turns.txt`: how many loop turns the drafted v1.4 check would see;
  - `e6_exit.py` → `e6_exit.txt`: interpreter exit with guests running and queued on a pool;
  - `e7_runner.py` → `e7_runner.txt`, `e7b_stop.py` and `e7c_control.py` → `e7b_stop.txt`: the
    callback on the real runner, both binaries, and a spec 011 stop under it.
  - I did not run `uv run pytest`. Nothing is built yet, and the scoreboard is the build review's
    job.
  - During the session the host's data volume filled up (1.8 TiB used, 120–290 MiB free), from
    other work on the machine. One control run failed with `ENOSPC` while placing a private root.
    It was re-run once space returned. My probes that ended with `os._exit` left a few private
    roots (11 MiB each) under the temporary directory. That is the 0.1.0a2 review's F6, seen again.

## What holds

- **The need is real.** EXECUTED (`probe_rerun.txt`): through `asyncio.to_thread`, 8 busy guests ran
  5.0× in parallel, and the loop's longest lag was 23 ms. `run()` called in a coroutine blocked the
  loop for 7,602 ms. This machine was busier than the author's, so the times are longer. The
  shape is the same.
- **A callback can stop a busy guest from another thread without touching its store.** EXECUTED
  (`cancel_proto_rerun.txt`; `e7_runner.txt`). On the real runner, the callback stopped a busy
  guest about 0.15 s after it started, on the snapshot and on the plain binary, with and without a
  fuel cap. The callback ran on the guest's own thread.
- **The callback's C contract is sound, if used as below.**
  - READ: the C signature is `wasmtime_error_t *(*)(wasmtime_context_t *, void *, uint64_t *delta,
    wasmtime_update_deadline_kind_t *kind)` (`store.h:254-259`). wasmtime-py's binding declares the
    return as `c_size_t` (`_bindings.py:2552`). That is the width of a pointer on every 64-bit host.
  - READ: a non-NULL return is moved into wasmtime and freed there (`store.rs:173-174`,
    `Some(err) => Err((*err).into())`). A NULL return continues with `delta`.
  - EXECUTED (`e1_callback.txt`): 20,000 returned errors with 4 KiB messages left the peak RSS flat
    (34, 35, 35, 35 MiB at each 5,000). The finalizer ran once per store, at `close`. So nothing
    leaks, and the error must never be deleted from Python.
  - READ: `kind` starts as CONTINUE, and any value other than 0 or 1 panics (`store.rs:166, 180`).
    So the runner must never write `kind`.
  - READ: wasmtime-py does not wrap this function at all. It keeps no table for it. So no
    wasmtime-py table is touched.
- **Fuel stays exact under `Continue`.** EXECUTED (`e1_callback.txt`): the same metered work used
  3,300,000,002 fuel with no callback and with 962 callbacks.
- **The pool keeps wasmtime alive until exit is safe.** EXECUTED (`e6_exit.txt`): at interpreter
  exit the pool's workers finished before the runner's `_release` freed the engines. So the
  ordering is safe (finding 8 is about how long it takes).
- **A queued call can be cancelled before it starts.** EXECUTED (`e3_async.txt`). With one worker
  busy, a second call that was cancelled while queued never started. This holds with
  `loop.run_in_executor` and with `executor.submit` plus `asyncio.wrap_future`. Cancelling the
  asyncio future calls the concurrent future's `cancel()`, which wins while the item is queued.

## Acceptance criteria against evidence

1. The checks exist and were seen failing first. This can be checked as written, but the
   non-blocking check passes or fails with the machine's speed (finding 5). The callback's unit
   test lists three outcomes. It needs a fourth, and an exception path (findings 1 and 2).
2. `uv run pytest` is green with `--accept-judge`. This is right: new checks change the judge.
3. A dry run of the release workflow passes. This is right, since `README.md` and `CHANGELOG.md`
   change.

## Findings, most severe first

1. **The callback, with the three outcomes in Decision 1, cancels spec 011's stop.** High. A host's
   `KeyboardInterrupt`, `CancelledError` or a trap in `host_alloc` would no longer stop the guest.
   - READ: spec 011 stops a guest by setting its epoch deadline to 0 (`_Call.stop`). When the
     deadline is reached, wasmtime calls the store's callback if there is one, instead of trapping
     (`store.rs:2361-2373`). A callback that answers "extend by one tick" lets the guest run on.
   - EXECUTED, WAT (`e1_callback.txt`, last two lines): a host function sets the deadline to 0,
     then the guest counts to 10⁹ with a call in each round. With no callback, the result is
     `Trap INTERRUPT`. With a callback that continues, the guest returns 1,000,000,000 after
     1,148 callbacks.
   - EXECUTED, real runner (`e7b_stop.txt`): a door host raises `KeyboardInterrupt`, and the guest
     catches the door's error and computes. Today's runner raises `KeyboardInterrupt` after
     0.08 s. With a continuing callback, the call is still running after 5 s.
   - Fix: give the callback a fourth outcome, and put it first. If `call.stopped` is set, answer
     with an error. The order is: a recorded stop, then `cancel`, then the deadline, then continue.
     Add the stop to the unit test of the outcomes, and add one v1.4 case: a door host that raises
     `CancelledError` under `cancel=` must still end the call.
2. **A callback that raises, or returns anything but an int, removes the call's deadline.** High.
   - READ: when a ctypes callback raises, CPython reports it as unraisable and writes nothing to
     the return slot (`callbacks.c`, `_CallPythonObject`: the result is written only
     `if (... && result)`). The same happens when the value is `None`, which `c_size_t` cannot
     hold.
   - EXECUTED (`e1b_raise.txt`): in both cases, on this host, wasmtime read the slot as NULL, with
     `delta` left at 0. So it continued with a deadline of "now", and called the callback again
     at the next check. In 3 s it ran 3.7–3.9 million times. The guest never stopped. Under spec 015
     this callback also enforces the deadline, so that call would have none.
   - INFERRED: on another ABI or build, the unwritten slot may hold a non-zero word. wasmtime would
     then free a pointer it never made.
   - Fix:
     - The whole body sits in `try/except BaseException`. Every path returns an int: 0 after
       writing `delta[0] = 1`, or a new error.
     - The `except` path returns an error, so a fault stops the guest. A stop is safer than running
       with no deadline.
     - Never return with `delta` at 0.
     - Unit tests: inject a `cancel` whose `is_set` raises, and a stack lookup that raises. Assert
       that an int comes back on every path.
   - One hole stays, and it is the same as spec 011's trampoline. A `KeyboardInterrupt` that a
     raising SIGINT handler throws at the callback's first bytecode is outside every `try`. That
     happens only on the main thread. See finding 14.
3. **The runner cannot name the outcome from the error, and a deadline no longer arrives as
   `INTERRUPT`.** Medium-high.
   - EXECUTED (`e1_callback.txt`): an error returned by the callback reaches Python as
     `WasmtimeError`, not `Trap`. Its text is `error while executing at wasm backtrace:\n …\n\nCaused
     by:\n    cancelled`.
   - EXECUTED (`e7_runner.txt`): today's `_drive` takes the first line, so `trapped` reads
     `'error while executing at wasm backtrace:'` on both binaries. The author's own probe prints
     the same first line (`cancel_proto_rerun.txt`).
   - READ: the C API cannot ask for the default interrupt. Its only kinds are CONTINUE and YIELD
     (`store.h:228-232`), and `Interrupt` comes only from a store with no callback
     (`store.rs:2366`). So under `cancel=`, a deadline will not be `TrapCode.INTERRUPT`, and
     `_trap_name` will not call it `"deadline"`. `_fuel_used` depends on that name.
   - Fix: the callback records its outcome on the `_Call` (`"cancelled"` or `"deadline"`) before it
     returns the error. `_drive` reads the record after `call.stopped` and before it looks at the
     exception. Never parse the message. A check: a busy guest under `cancel=` and
     `deadline_s=0.2` reads `trapped == "deadline"`, with `fuel_used is None` under a fuel cap.
4. **`run_async` as worded does not wait for the call, and the wait has limits the spec does not
   state.** Medium-high.
   - EXECUTED (`e3_async.txt`): the obvious reading, `await loop.run_in_executor(...)` and then, on
     `CancelledError`, set the event and `await` the same future, returns at once. That future is
     already cancelled. The worker was still running when the task ended. This held for one
     cancel, for two, and under `asyncio.timeout`.
   - EXECUTED: a form that works in every case:
     - submit with `executor.submit` and await `asyncio.wrap_future(cf)`;
     - on `CancelledError`, if `cf.cancel()` returns true, the call never started, so re-raise;
     - otherwise set the event, then loop `await asyncio.wrap_future(cf)` until `cf.done()`, and
       swallow further `CancelledError`s while doing so;
     - then re-raise the first `CancelledError`.
     The worker had finished before the task ended in all three cases, and `asyncio.timeout` still
     raised `TimeoutError`. Write this mechanism into Decision 2. No `asyncio.shield` is needed.
   - The wait is bounded only while the guest is in wasm or in a wait.
     - READ: the epoch does not interrupt a host function. A door host that blocks keeps the worker,
       and so keeps the cancelled task waiting. The Scope's one-line `run_coroutine_threadsafe`
       recipe blocks forever if the loop is closing (INFERRED). It must be `.result(timeout=…)`.
     - Cancellation is not checked while the artifacts are found, the module is compiled (spec 011
       saw cold compiles stall for 90–225 s), or the stdlib zip is placed.
     - Say "within one tick once the guest runs". Have `run` check `cancel.is_set()` once more just
       before it instantiates.
   - INFERRED from `asyncio.to_thread` (which copies the context) and `executor.submit` (which does
     not): `contextvars` do not reach the door host unless `run_async` submits
     `contextvars.copy_context().run`. A host that reads request-scoped context, such as tracing,
     needs this. Decide, and say which.
5. **The non-blocking check depends on speed.** Medium. §4.9 is met only in form.
   - EXECUTED (`e5_turns.txt`): while 4 guests ran through threads, the loop counted 514 turns of
     `sleep(0)` for an empty program, 315 for a 200,000-step loop, and 2,514 for a 2,000,000-step
     loop. So "at least 1,000" passes or fails with the guest's length on a given machine. A blocked
     loop counted 0.
   - Fix: make the count gate the guest, not race it. Each guest calls the door first, and the
     door's host waits on a `threading.Event` that the counting coroutine sets after N turns. The
     host has a 120 s fail-safe; on timeout it answers so that the guest prints a failure marker.
     A blocking `run_async` never lets the loop count, so the check fails at the fail-safe whatever
     the machine. Each guest then prints its own token.
   - The cancellation check:
     - pass `executor=ThreadPoolExecutor(1)`, so that "a new call completes" proves the one worker
       was freed;
     - assert that the cancelled call's future is done when `CancelledError` arrives;
     - say how "the private root is gone" is observed: for example, count `wasi-python-root-*`
       under a test-only `tempfile.tempdir`, in a child process.
6. **A forked worker cannot use a runner its parent used.** Medium. It is mostly a defect that
   exists today, but preloading servers make it likely, so the specification must decide it.
   - EXECUTED (`e4_fork.txt`, macOS): the parent ran one call through a pool, then forked.
     - `run` in the child aborted (exit −6): wasmtime panics with "cannot use Wasmtime in a forked
       process when mach ports are configured".
     - The parent's pool hung in the child. Its threads are gone, but the idle semaphore lets
       `submit` skip making a new one (READ, `thread.py:219-239`).
     - `_epoch_ticker._thread` was inherited dead and not `None`, so `__enter__` never starts a
       new one.
   - INFERRED for Linux, which was not run: wasmtime may work there, but no tick ever comes. So a
     child's deadlines and spec 010's sliced waits never end, and the default 60 s limit is gone.
     That breaks §4.15 without a word.
   - A server that warms the module at import, before it forks (gunicorn `--preload`), is exactly
     this.
   - Decide:
     - an `os.register_at_fork(after_in_child=…)` that resets the default pool and the ticker
       (`_thread = None`, `_active = 0`);
     - and either a clear error in a child whose parent used wasmtime, or dropping the parent's
       engines, modules and linkers without freeing them and starting again;
     - and a README sentence: warm up after the fork (in gunicorn's `post_fork`, say), not before.
     - wasmtime-py exposes `Config.macos_use_mach_ports` (READ, `_config.py:544`). It is untested
       here.
7. **`os.cpu_count()` does not bound what Decision 2 says it bounds.** Medium.
   - READ: `os.cpu_count()` counts the host's CPUs. It ignores CPU affinity (Python 3.13's
     `os.process_cpu_count()` does not) and a container's CPU quota (neither does).
   - INFERRED: in a 2-CPU container on a 64-core host, the default pool is 64 workers. At the
     defaults that is 64 GiB of guest memory.
   - The arithmetic is per process. Four uvicorn workers make four pools.
   - The arithmetic is also short. Per worker, the host holds up to `2 × output_bytes` of output and
     a copy of `stdin`, on top of `memory_bytes`: 1 GiB + 32 MiB at the defaults. Disk use
     (0.1.0a2 F2: about 0.9 GiB/s per guest) and the process's file descriptors (README, "Not
     protected") also scale with the pool. A web server's own sockets share those descriptors.
   - The bound covers only `run_async` on the default pool. It does not cover `run` from other
     threads, a caller's executor, or FastAPI's `def` endpoints, which run in anyio's thread pool.
   - Fix (§4.15: a new limit needs a default and a stated reason):
     - use `process_cpu_count()` where it exists, else `cpu_count()`;
     - cap it at a stated number;
     - make it settable without passing `executor=` everywhere;
     - in the README, give the per-process arithmetic, with output, disk and descriptors, and a
       multi-worker example.
8. **At exit the default pool runs every queued call to the end.** Medium-low.
   - EXECUTED (`e6_exit.txt`): three busy guests with 2 s deadlines on a one-worker pool delayed
     interpreter exit by 5.8 s. READ (`thread.py:23-37, 97-133`): the workers drain the queue
     before their stop markers. With `deadline_s=None` exit never ends.
   - "Cancels nothing" (Decision 3) is true, and it means exit waits for all of them.
     `asyncio.run` cancels the tasks that remain (READ), which makes `run_async` stop them. A
     server that exits by another path does not (INFERRED).
   - Decide: either keep a registry of live cancel events and queued futures, and set or cancel
     them all at shutdown (`threading._register_atexit` runs before the join, but it is private),
     or state the wait in the README.
9. **What cancels a request in FastAPI is narrower than the Intent suggests.** Medium-low. INFERRED:
   FastAPI is not installed here, so I could not run it.
   - Starlette does not cancel a plain endpoint's task when its client disconnects. So a gone
     client's guest runs to its deadline. Cancellation comes from the app's own timeouts, a
     `TaskGroup`, or shutdown.
   - The README must not say that a disconnect stops a guest unless that has been run against a
     pinned FastAPI.
   - The example should wrap the call in `asyncio.timeout(...)`. That timeout also bounds the time
     a request spends queued, which is the backpressure answer. The queue is otherwise unbounded,
     and `deadline_s` starts only when a worker picks the call up.
   - Say that a `def` endpoint calling `run` already keeps the loop free (anyio's pool), but cannot
     be cancelled.
10. **Under `cancel=`, the ticker and the deadline need two sentences.** Low.
    - EXECUTED by accident (`e7_runner.py`, first attempt): with `deadline_s=None` the ticker does
      not run, so the callback is never called. A cancelled guest then spun for more than 5
      minutes before I killed it. Decision 1 already says the ticker runs for any `cancel` call.
      The cancellation check covers it only if it runs a busy guest with `deadline_s=None` while
      no other call is running. Say so.
    - Spec 010's guarantee still holds: the callback stops at `count >= stop_at`, the same test
      `_Waits` uses. So a deadline never ends early.
    - INFERRED (`_stop_at`'s `+ 1`, and the count trailing the engines by up to one round): a busy
      guest under `cancel=` stops 1–2 ticks (10–20 ms) later than the same guest without it. State
      it.
11. **Callback lifetime: keep it simpler than Decision 1's "held by the call".** Low.
    - Use one module-level `CFUNCTYPE`. It finds its call through the thread's stack and the
      context address, as spec 011's shared functions do. READ: `_drive` pushes the call before
      `instantiate`, so `_initialize` and the snapshot's entry are covered. EXECUTED
      (`e7_runner.txt`): both binaries.
    - Pass a NULL finalizer. READ: `ForeignData` calls the finalizer only if it is `Some`
      (`lib.rs:119-124`). EXECUTED: the binding accepts its own function-pointer type called with
      no arguments, which is NULL.
    - Then no per-call ctypes object exists, and its lifetime never matters. That includes the
      working tree's new order, which closes the store inside `_instance`.
    - Add `wasmtime_store_epoch_deadline_callback` (its four `argtypes`) and `wasmtime_error_new`
      to the binding check in `tests/unit/test_runner_calls.py`.
    - State one limit. A nested `run` from a door has its own store and its own `cancel`. The outer
      call's cancel is seen only when the outer guest runs again (INFERRED from the design).
12. **The per-tick cost is small with an idle loop and noticeable with a busy one.** Low. Benchmark
    facts for the memo, EXECUTED (`e2_bench.txt`), 16 guests on 10 cores, each run twice:
    - main thread idle: wall time 2.59 s became 2.61–2.65 s, and CPU 24.2 s became 24.4 s (about
      1–2%), with about 2,900 callbacks;
    - main thread busy in Python, as a loaded server's loop is: wall time 3.39–3.49 s became
      3.90–3.98 s (13–17% slower). Callbacks fell to 1,748–1,850, because each one waits for the
      GIL.
    - An option, the author's call: for a call with `cancel` and no near deadline, continue by k > 1
      ticks, at k ticks of cancel latency.
13. **Executor and argument edges to decide.** Low.
    - A process or interpreter pool cannot carry a `threading.Event` or a host callable (INFERRED).
      Say "an executor that runs callables on threads of this process", and refuse
      `ProcessPoolExecutor` and `InterpreterPoolExecutor` by type, or document it.
    - `run_async(cancel=…)`: refuse it, or chain it. Pick one.
    - A shut-down executor raises `RuntimeError` at submit (EXECUTED, `e3_async.txt`). After
      interpreter shutdown starts, the message is "cannot schedule new futures after interpreter
      shutdown" (READ). State it.
    - Make the default pool under `_lock`.
    - `run` will check and copy `stdin` a second time in the worker unless `run_async` calls an
      inner, already-checked entry point.
14. **`run(cancel=)` on the main thread runs Python each tick there.** Low.
    - With the runner's own SIGINT deferral that is harmless.
    - Under an embedder's raising handler, a `KeyboardInterrupt` can land at the callback's first
      bytecode, which is finding 2's failure. The README's existing advice (run on a worker thread
      under such a handler) covers it. Name the callback there too.
    - An opportunity, optional: the callback can turn `_ctrl_c["pending"]` into a stop. Then Ctrl-C
      ends a computing guest within a tick under `cancel=`, which closes spec 011's "a guest that
      never waits" hole for these calls.
15. **The Scope should name four more things it leaves out.** Low.
    - **trio:** `run_async` is asyncio only. Under trio, `asyncio.get_running_loop()` raises
      (INFERRED). anyio on asyncio, which FastAPI uses, is fine. `run(cancel=)` is the portable
      piece.
    - **free-threaded CPython:** out, as in spec 011.
    - **an async door:** out, with the `.result(timeout=…)` fix from finding 4.
    - **a per-call queue-time limit:** out; finding 9's `asyncio.timeout` covers it.

## Constitution checks

- §4.4 two imports, §4.6 artifacts: untouched. The change is on the host side only.
- §4.5 embedder-neutral: holds if the README example is framed as "an ASGI endpoint (FastAPI
  shown)". FastAPI is a framework, not a consumer of this project. No code or test should name it.
- §4.9 tests count: the drafted non-blocking check counts, but its threshold depends on speed
  (finding 5). The fixes count only.
- §4.10 evidence: the author's probes reproduce in shape (`probe_rerun.txt`). The prototype's claim
  that the call "returns `trapped == "cancelled"`" is not yet true of the error path (finding 3).
- §4.13 tooling: no new dependency. `run_async` is standard library; FastAPI is not added.
- §4.15 safe by default: the concurrency bound is a new limit, and its default needs a stated reason
  (finding 7). Findings 1, 2 and 6 would each loosen the time limit without anyone deciding it.
- §5.2 no open questions: findings 4, 6, 7, 8 and 13 each need a decision written into the
  specification, not a question.
- §7 never-do list: nothing tripped. The spec uses a binding wasmtime-py ships, as spec 011 does.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Finding 1 —
2. Finding 2 —
3. Finding 3 —
4. Finding 4 —
5. Finding 5 —
6. Finding 6 —
7. Finding 7 —
8. Finding 8 —
9. Finding 9 —
10. Finding 10 —
11. Finding 11 —
12. Finding 12 —
13. Finding 13 —
14. Finding 14 —
15. Finding 15 —

## Verdict

Do not build yet. The approach is sound: worker threads, a `threading.Event`, and a per-store
epoch callback that stops the guest on its own thread. But the drafted callback would cancel spec
011's stops (finding 1). It could lose the deadline on any fault (finding 2). It would report its
stops as `'error while executing at wasm backtrace:'` (finding 3). And `run_async` as worded does
not wait for its worker (finding 4). Revise Decisions 1 and 2 for those four. Redesign the
non-blocking check so that it does not depend on speed (finding 5). Write decisions for fork, pool
size and exit (findings 6–8). Findings 9–15 are text and small tests.

One line: the design is right, but the callback must also honour spec 011's stops, survive its own
faults and record its outcome, and `run_async` must keep the concurrent future so that it can wait.
