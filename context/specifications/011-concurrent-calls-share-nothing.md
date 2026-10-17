# 011 — Concurrent calls share nothing

- **Status:** landed, 2026-10-17. Reviewed before build
  (`../reviews/011-concurrent-calls-share-nothing-spec-2026-10-17.md`) and after
  (`../reviews/011-concurrent-calls-share-nothing-2026-10-17.md`).
- **Owner:** Clay Gendron
- **Kind:** the runner (`src/wasi_python/runner.py`), judge additions in `tests/`, `README.md`,
  `CHANGELOG.md`.
- **Depends on:** 006 (`run` never raises for what a guest does), 010 (the shadowed
  `poll_oneoff`).
- **Research it stands on:**
  - Spec 010's build review (`../reviews/010-a-sleeping-guest-keeps-its-deadline-2026-10-17.md`,
    finding 1, EXECUTED): 12 threads called `run` for 90 s. After the first few hundred calls,
    26,608 of 26,861 calls raised `TypeError` from wasmtime-py's `FUNCTIONS.allocate`. Stock
    wasmtime-py without spec 010's shadow did the same: 26,558 of 26,957. In 30 s runs, 8–14
    guest sleeps failed with `ENOTSUP`.
  - This specification's pre-build review, EXECUTED:
    - the proposed check failed today's runner in four fresh processes, with 242–286 of 320
      calls wrong;
    - wasmtime frees custom outputs on its own threads;
    - a host's `BaseException` crosses threads;
    - other traps in `host_alloc` were hidden.
  - The author's prototypes (EXECUTED, scratch `rev011a/pkg_author`, `author_stop.py`):
    - Decisions 1 and 2 below, run on the real artifacts under the same check (8 threads × 40
      calls, `setswitchinterval(1e-6)`, warm, two repetitions in each of three processes):
      0 wrong of 1,920. Both wasmtime-py tables stayed untouched by calls: `FUNCTIONS` at 2
      entries, `CUSTOM_OUTPUTS` at 0. Today's runner under the same check: 1–320 wrong per
      repetition, with 152–320 in all but one.
    - A host function that sets its store's epoch deadline to 0 through the caller's context
      and returns stops the guest with an `interrupt` trap at its next function entry. Nothing
      is raised through wasmtime-py.

## The defect

wasmtime-py keeps two process-wide tables of Python callbacks. They are plain lists with a free
list, and nothing locks them (READ, `wasmtime/_slab.py`).

- **`FUNCTIONS`** (`_func.py:227`). `Linker.define_func` adds an entry (`_linker.py:79`). The C
  `finalize` frees it when the last owner drops, either the linker or a store that instantiated
  through it. The trampoline reads it on every host call (`_func.py:192`).
- **`CUSTOM_OUTPUTS`** (`_wasi.py:26`). `WasiConfig.stdout_custom` and `stderr_custom` each add
  an entry. `custom_finalize` frees it. The free usually runs on one of wasmtime's own tokio
  worker threads, because the guest's first WASI call hands a clone of each output stream to a
  background task (the review, EXECUTED: 3,996 of 4,000 frees ran off the caller's thread).

Every `run` adds four entries: `poll_oneoff`, `host::call`, stdout and stderr. They are freed
later, on threads the runner does not choose. `allocate` and `deallocate` each take several
bytecodes, so two threads interleaving them can:

- give one slot to two callbacks;
- leave the free list pointing at a live entry, or at a tuple;
- orphan slots (the review, EXECUTED: 47–65 orphaned slots per 40 s run).

After that, every later `define_func` in the process raises, which breaks spec 006's promise
that `run` never raises for what a guest does. Worse, a guest's import, or its output, can reach
another call's function or buffer, and with it another call's host. That is a cross-tenant leak.
The users this project serves run many untrusted guests at once in one host process, so this is
the shape they will use.

The same review found three more things.

- **Exceptions cross threads.** An exception raised in a host function reaches its caller
  through wasmtime-py's process-wide `LAST_EXCEPTION` (`_func.py:211-216, 245-249`). The door and
  `poll_oneoff` catch `Exception`, so a host's `BaseException` still crosses threads. Examples
  are `asyncio.CancelledError`, `SystemExit` and `KeyboardInterrupt`. The review, EXECUTED:
  16,200 of another thread's calls raised the first thread's `CancelledError`. The door also
  re-raises a `Trap` from the guest's `host_alloc` on purpose today.
- **Hiding a trap is not a fix.** Answering −2 instead of re-raising (this draft's first
  Decision 3) is right for the deadline and for fuel, which trap again at the next check. But a
  `proc_exit`, an `unreachable` or a stack overflow inside `host_alloc` would then let the guest
  run on, and the call would report something other than what happened (the review, EXECUTED).
- **A stall.** With 8–12 threads starting at once, some first calls took 90–225 s, blocked in
  `wasmtime_module_delete` (EXECUTED, stock wasmtime-py as well). Concurrent cache misses each
  compile the module, then all but one drop their copy.

## Decisions

1. **Host functions are defined once per engine, never per call.**
   - The runner keeps one `Linker` per engine, so two at most. Each is made under the runner's
     lock the first time it is needed: `define_wasi()`, then `poll_oneoff` and `host::call`,
     each defined once.
   - After that, a call allocates nothing in `FUNCTIONS`. wasmtime's `Linker` is shareable, and
     `define_wasi` reads each store's own WASI context (the review, EXECUTED: about 164,000
     calls on one linker across 8–16 threads, each with its own output).
   - The two functions find the current call through a thread-local stack:
     - `run` pushes the call's state before instantiating, and pops it in a `finally`;
     - the state holds the door, the waits, the store's context address and the stop record
       (Decision 3);
     - the shared function uses the top entry only if the caller's context address equals the
       entry's (`caller._context()` has the store's address; the review, EXECUTED);
     - with an empty stack or a mismatched address, the door answers "no host" and
       `poll_oneoff` answers `EINVAL`.
   - This is right because a store's code, and so these two functions, run on the thread that
     entered the store, synchronously. That includes `_initialize`, the snapshot's entry and
     nested runs from a door (the review, EXECUTED).
   - **Output callbacks are different.** They run on wasmtime's own threads (the review,
     EXECUTED: 200 of 200), so they never go through the stack (Decision 2).
   - Each call keeps its linker in a local for the whole call. Clearing the cached linkers at
     exit, before the engines, then cannot free one in use.
2. **The guest's output never enters wasmtime-py's table.**
   - The runner registers its own C callbacks for stdout and stderr through wasmtime's C API,
     using the binding wasmtime-py already exposes (`wasmtime._ffi.wasi_config_set_stdout_custom`
     and `…_stderr_custom`).
   - Each callback's data word is a key in the runner's own table of `_Stream`s. A
     `threading.Lock` guards every read, insert and removal there, and the finalizer removes the
     key under that lock, on whatever thread wasmtime calls it.
   - Unlike `CUSTOM_OUTPUTS`, this table is a dict keyed by a counter that only grows. A key is
     never reused, so a late free can never remove a live call's stream.
   - The callback never raises and never prints. A missing key answers the length, so the bytes
     are dropped and the guest's write succeeds.
   - So `run` touches `CUSTOM_OUTPUTS` never and `FUNCTIONS` only once per engine, and calls
     made through `run` cannot race each other. Other wasmtime-py code in the same process still
     can: its exceptions reach a trapping call through `LAST_EXCEPTION`, and its own slab use can
     corrupt the table holding the runner's four entries (the build review, EXECUTED and
     INFERRED); the README says so. **No wasmtime-py code is replaced
     or patched:** the runner calls a binding wasmtime-py ships, as wasmtime-py itself does.
     Constitution §4.1 concerns source trees and is not touched.
   - The binding is in a private module, so a unit check pins its presence and its argument
     types. `pyproject.toml` already limits wasmtime to `>=49,<50`.
   - The review's alternative was rejected: replacing the slab's methods at run time works, but
     it rewrites a dependency's behaviour in place. Draining files or FIFOs was rejected too: it
     is more code and needs more threads.
3. **No exception crosses the trampoline; a stop is recorded and reported on the right
   thread.**
   - **Which exceptions stop the guest.** Both shared functions catch `BaseException`. An
     ordinary `Exception` from a host or a frame answers as today (the door −2, `poll_oneoff`
     `EINVAL`), and the guest carries on (`test_runner_reports_a_host_fault`). These stop it:
     - a `Trap` or `WasmtimeError` from the guest's own `host_alloc`, including its `ExitTrap`
       (each is an `Exception` subclass, so the door re-raises them to the shared function);
     - any `BaseException` that is not an `Exception`: `KeyboardInterrupt`, `SystemExit`,
       `CancelledError`.
   - **How it stops.** The function:
     1. records the cause on the call's state (the first one only);
     2. stops the guest: it sets the store's epoch deadline to 0 through
        `ffi.wasmtime_context_set_epoch_deadline(caller._context(), 0)`, the C API's way for a
        host function to act on its store;
     3. answers: the door −2, `poll_oneoff` `EINVAL`.
   - **When it stops.** The guest traps with `interrupt` at its next function entry (EXECUTED,
     `author_stop.py`; the review, EXECUTED, also on a fuel-metered store and a nested run).
     CPython calls a function almost every instruction, and the door's own caller calls
     `PyBuffer_Release` at once.
   - **A loop with no call.** It compares against a deadline cached at the function's entry
     (the review, READ in cranelift), so it runs until the call's own deadline, or forever
     without one, as epoch interruption already behaves. Straight-line code before the next
     check still runs, as with any epoch check. While a stop is recorded, every later door call
     or wait answers at once; host calls themselves have no epoch check.
   - **After the guest ends** and the store is closed:
     - a recorded non-`Exception` `BaseException` is re-raised from `run`, on the thread that
       called it;
     - a recorded `ExitTrap` sets `exit_code`;
     - a recorded `Trap` sets `trapped` to its name, ahead of whatever the guest did later.

     `fuel_used` is `None` for a stopped call, because the fuel count is stale after an
     interrupt (the review, EXECUTED).
   - **Ctrl-C.** Python runs a signal handler wherever the main thread next runs Python. When
     that is the first line of wasmtime-py's `trampoline`, outside every `try`, the
     `KeyboardInterrupt` cannot be caught. ctypes swallows it, and wasmtime aborts the process
     (the review, EXECUTED: exit 134 in 3 of 3 runs, today's runner as well).
     - So while `run` holds the main thread and the SIGINT handler is Python's default, the
       runner installs a handler that only sets a flag, and restores the default afterwards.
     - It never replaces an embedder's own handler, never acts on another thread, and a nested
       call keeps the outer swap.
     - The shared functions turn a set flag into a recorded `KeyboardInterrupt` and a stop, so
       the call raises `KeyboardInterrupt`. A wait on the main thread checks the flag in
       `TICK_S` slices.
     - A flag that no host function saw (a guest that computes and never waits or calls the
       door) is raised once the call has ended: at its deadline, or never with
       `deadline_s=None`, as before this change.
     - Under an embedder's handler that raises (asyncio's on a second Ctrl-C), the abort remains
       (the build review, EXECUTED); the README says to call `run` on a worker thread there.

   So Ctrl-C and a host's cancellation reach the call that caused them, and a trap in
   `host_alloc` reports what happened.
4. **One compile per module.** `_module` takes a lock per `(metered, digest)` key around a cache
   miss. It is the only lock held while compiling, never `_lock`, which the epoch ticker takes
   every round. A waiter looks in `_modules` again once it has the lock. If a compile raises, the
   next waiter retries. The stall is recorded before and after as a benchmark fact; it gets no
   check, since a check would have to measure time.
5. **Upstream.** An issue for wasmtime-py is drafted in the landing notes. It says the two tables
   need a lock, or `define_func` and the custom outputs need a form that does not allocate per
   use, and that exceptions cross threads through `LAST_EXCEPTION`. Filing it waits on the owner
   (`../questions-for-the-owner.md`, question 11).
6. **Checks.**
   - **The concurrency check** (v1.4), `test_concurrent_calls_get_their_own_results`. It runs in
     a child process (`sys.executable`, with a 120 s `timeout=`, a fail-safe and not a timing),
     because before the change it corrupts the process it runs in. In the child:
     - both engines are warmed first;
     - `sys.setswitchinterval(1e-6)` is set;
     - 8 threads make 40 calls each, a mix of a printed token, a token from the call's own host
       through the door, a 0.01 s sleep and then a token, a fuel-capped token, and a token
       printed before a deadline trap;
     - every call must return its own token, with its own trap where one is expected, and no
       call may raise.
     Before the change it must be seen failing (the review saw 242–286 wrong).
   - **The table checks** (unit, counting operations):
     - after one warm-up call per engine, further calls leave `len(FUNCTIONS.list)` unchanged
       and call `Linker.define_func` zero times;
     - `CUSTOM_OUTPUTS.allocate` is called zero times;
     - the runner's own output table holds no key once every call has ended and its frees have
       run (a bounded loop of `gc.collect()` and short waits, as a fail-safe).
   - **The binding check** (unit): `wasmtime._ffi` has both setters with the expected
     `argtypes`, and has `wasmtime_context_set_epoch_deadline`.
   - **The stop checks** (unit, through a WAT module and the shared linker): a `host_alloc`
     that exits, one that runs `unreachable` and one that overflows the stack; a door whose host
     raises `CancelledError`, `KeyboardInterrupt` or `SystemExit`. Each checks the door's answer
     as the guest stored it, the call's result, and an empty `LAST_EXCEPTION`.
   - **The Ctrl-C checks:** unit tests of the flag (a set flag stops the call before the host
     runs, an unseen flag is raised at the end, and an embedder's handler is left alone), and a
     v1.4 check, `test_ctrl_c_while_the_guest_runs_ends_the_call`. It runs in a child process:
     a SIGINT lands while the guest computes, or while it waits `10**6` s, and the call must
     raise `KeyboardInterrupt` with the next call working.
   - **A mismatched store** (unit): a stack entry for one store and a caller from another
     answers "no host".

## Intent

One process runs many guests at once, and each guest sees only its own call. Nothing the runner
puts in a process-wide table can be read or freed by another call, and anything a host raises
comes back to the call that raised it.

## Design

```
src/wasi_python/runner.py   _linker(engine): one per engine; a thread-local stack of call
                            states, checked against the caller's store;
                            the runner's own output callbacks and table (locked, keys never
                            reused);
                            both host functions catch BaseException, record it, stop the guest
                            through its epoch deadline, and run reports or re-raises it;
                            a per-key compile lock in _module
tests/unit/…                the table counts, the binding, the stops, the mismatched store
tests/checks/test_v1_4_embedding.py   concurrent calls get their own results (child process)
README.md, CHANGELOG.md
```

## Scope

In: the above. Out:
- the judge's own driver (`tests/harness/guest.py`), which is single-threaded;
- free-threaded CPython builds, where wasmtime-py is untested;
- fixing wasmtime-py itself (zero upstream patches; Decision 5).

## Acceptance criteria

1. The concurrency check, the table checks and the Ctrl-C check were seen failing before the
   change.
2. `uv run pytest` is green with `--accept-judge`.
3. A dry run of the release workflow passes every job.

## Landing notes

Built 2026-10-17 by the author agent; reviewed in
`../reviews/011-concurrent-calls-share-nothing-2026-10-17.md`.

**The build review's fixes.** The stop, the `BaseException` catch, `fuel_used`, the stack pop
and the wait's Ctrl-C check each now fail a test when removed (EXECUTED, five mutations). Two
things stay unchecked, by choice:
- the per-key compile lock, which only a racy count could show (the build review: 2 compiles
  against 12 in 12 cold threads);
- the `RLock`, which guards an INFERRED deadlock.

The output keys are freed in a `finally`. The default handler is restored only if the runner's
own is still installed. The README and Decision 2 now limit the isolation to calls made through
`run`, and the README's "Not protected" list names Ctrl-C under a raising handler (asyncio
included) and a guest that never waits under `deadline_s=None`. The reviewer's confirmation of the
pre-build review asked for four corrections to Decision 3 before building: the Ctrl-C rule, which
exceptions stop the guest, the call-free loop, and `fuel_used`. They are in the Decision as built.
It also suggested two refinements, which were taken: `run` removes its own two output keys once
the guest has ended, and the output lock is an `RLock`.

**Seen failing first** (EXECUTED).
- **The concurrency check's script on today's runner.** At 8 threads × 40 calls it failed in 2
  of 3 runs (8 wrong and 137 raised; 3 wrong and 172 raised; one clean run). So the check uses
  8 × 100: it failed in 6 of 6 runs, with 0–30 wrong and 178–766 raised per run.
- **`test_calls_add_nothing_to_wasmtime_pys_tables`:** `{'define_func': 6, 'custom outputs': 6}`
  over its three calls.
- **`test_ctrl_c_while_the_guest_computes_ends_the_call` on today's runner:** the child process
  died with SIGABRT (return code −6), after `Exception ignored while calling ctypes callback
  function <function trampoline>: KeyboardInterrupt`.
- **The unit tests of `tests/unit/test_runner_calls.py`:** they failed before the runner had
  `_Call`, `_drive` and `_linker`. The binding test passes on both; it pins a dependency's shape.

**After the change** (EXECUTED).
- `uv run pytest`: `128/131 pass · 1 gap · 2 blocked · 0 fail`, unit suite 211/211; ratchet
  `lost 0 · absent 0 · gained 3 · grew 0`, with the judge changed in `test_v1_4_embedding.py` and
  the new `test_runner_calls.py`.
- The concurrency script, 5 more runs: `800 calls, 0 wrong, 0 raised` each time.

**Ctrl-C** (EXECUTED, a script under Python's default handler, SIGINT 3 s into each call):

| case | new runner | today's runner |
|---|---|---|
| a guest that sleeps 30 s | `KeyboardInterrupt` after 2.97 s | the same |
| a guest that computes for 6 s, then sleeps | `KeyboardInterrupt` at its first host call, 6.07 s (3 of 3) | aborted, exit 134 |
| a guest that computes until its 20 s deadline | `KeyboardInterrupt` at the deadline, 20.08 s | the same |

The next call worked in every case that did not abort.

**The upstream issue, drafted** (filing waits on question 11):

> *Title:* `FUNCTIONS` and `CUSTOM_OUTPUTS` are shared, unlocked tables; concurrent use corrupts
> them.
>
> wasmtime-py keeps the callbacks of `Linker.define_func`/`Func` and of
> `WasiConfig.stdout_custom`/`stderr_custom` in two process-wide `Slab`s (`_func.FUNCTIONS`,
> `_wasi.CUSTOM_OUTPUTS`). `Slab.allocate` and `deallocate` are several bytecodes each and take
> no lock. Frees run from C finalizers: the custom outputs' frees run on wasmtime's tokio worker
> threads, because the WASI stdio stream is cloned into an `AsyncWriteStream` task. With threads
> that each create a linker, a WASI config and a store per call, the free list is corrupted after
> a few hundred calls. Every later `define_func` then raises `TypeError: list indices must be
> integers or slices, not tuple`, and a callback slot can be handed to two owners, so one store's
> import can call another store's function. Separately, an exception raised in a host function
> is passed through the module-global `LAST_EXCEPTION`, which another thread's call can pick up.
> And a `KeyboardInterrupt` delivered at the first line of `trampoline` is outside its `try`, and
> the process aborts. A lock around the slabs, a per-thread or per-store exception slot, and a
> `try` that covers the whole trampoline would fix these. A reproduction script is available.
