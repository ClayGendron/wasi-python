# Review of 011 — Concurrent calls share nothing (the specification, before build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I read `AGENTS.md`, the
  constitution, `context/reviews/README.md`, the 010 pre-build review (for its format), finding 1
  of the 010 build review and its probes (`rev010b/probes/p9*_slab.py`, `p9c_locked.py`,
  `p7*_stall.py`), the specification, the runner, and the wasmtime-py and wasmtime code named
  below. I did not rely on the specification's summary of wasmtime-py. Each claim is labelled
  EXECUTED, READ or INFERRED.
- **Reviewed:** `context/specifications/011-concurrent-calls-share-nothing.md` as drafted
  (untracked, as of 03:40 on 2026-10-17). The runner is `src/wasi_python/runner.py` at `9512e3a`.
- **Ran (EXECUTED, darwin-arm64, host CPython 3.14.2, wasmtime-py 49.0.0, the artifacts in
  `build/artifacts/` read only).**
  - Scripts and outputs are under
    `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev011a/`.
    Nothing under `build/` was written. No tracked file was edited.
  - Another agent was mutating `src/wasi_python/runner.py` in place while I started (the 010
    reviewer's `mutate2.py`). So I ran everything against copies: `pkg/` is the runner as committed
    at `9512e3a` (byte-identical, checked with `diff`); `pkg_spec/` is my prototype of Decisions
    1–3 as drafted, made by `make_spec_runner.py` (one linker per engine, a thread-local stack,
    the slab lock around the `WasiConfig` and `store.close()`, the door answering −2). With
    `SLAB_WRAP=1` it also wraps the slab's methods (finding 1's fix).
  - Probes `q2_nested.py` to `q6_baseexc_crossing.py`, each with its `.txt` output. They are
    quoted in the findings.
  - I did not run `uv run pytest`. The runner was being mutated in place, and the scoreboard
    writes under `build/progress/`. The scoreboard is the build review's job.
- **Read (READ):**
  - wasmtime-py 49.0.0: `_slab.py:15-32`; `_func.py:17-44, 188-250`; `_linker.py:64-91,
    116-129, 152-170`; `_wasi.py:26, 119-161, 197-215`; `_store.py:15-32, 92-98`;
    `_managed.py:29-95`; `_instance.py:49-80`; `_extern.py:7-22`; `_value.py:13-27`; `_ffi.py:38`
    (`cdll`: the GIL is released in every C call);
  - wasmtime v49 (`context/prior_art/wasmtime-v49/crates`): `c-api/src/linker.rs:12-23,
    112-146`; `c-api/src/wasi.rs:32-43, 169-310`; `c-api/src/store.rs:236-243`;
    `c-api/src/lib.rs:111-125`; `wasi/src/cli.rs:165-192`; `wasi/src/p1.rs:344-420`;
    `wasi/src/p2/write_stream.rs:130-160`; `wasi/src/runtime.rs:27-102`;
  - our code: `src/wasi_python/runner.py`; `recipes/hostmodule.c:1-80`.

## What holds

- **The defect is real, and the proposed check finds it.** EXECUTED, `q5_check_fresh.txt`. The
  check as specified (8 threads × 40 calls, `setswitchinterval(1e-6)`, a mix of print, door,
  sleep and deadline trap; both engines warmed first) against today's runner:
  - in three fresh processes, 286, 242 and 263 of 320 calls were wrong; in a fourth, 265
    (`q5_check_warm.txt`). Each run took 1.3–2.0 s;
  - the first failure is the `TypeError` from `FUNCTIONS.allocate`. `CUSTOM_OUTPUTS` breaks too:
    one call raised `list indices must be integers or slices, not method` from `stdout_custom`,
    and in several calls the guest's token came back on **stderr** with an empty stdout;
  - at the default switch interval it failed in 1 of 3 processes (48, 0, 0 wrong). So the
    `1e-6` interval is what makes the check reliable, as the spec says.
- **Cross-tenant output is EXECUTED, not only INFERRED.** `q3b_slab_race.txt`, mode `none`: a
  tiny WAT guest asks its door for its token and writes it to stdout. With no lock, 8 threads,
  20 s: 1,226 calls received another call's token on stderr and 133 on stdout. The spec can cite
  this for "a guest's import can run another call's function".
- **One linker per engine is safe to share (question 1).**
  - READ: `wasmtime_linker_instantiate` takes `&wasmtime_linker_t` (`linker.rs:137-146`).
    wasmtime-py's `Linker.instantiate` keeps no shared Python state, except the
    `LAST_EXCEPTION` read in `enter_wasm` (`_linker.py:152-170`, `_func.py:230-250`).
  - READ: `define_wasi` adds WASI functions that read each store's own context
    (`ctx.wasi.as_mut()`, `linker.rs:112-121`). So one linker serves stores with different
    `WasiConfig`s.
  - EXECUTED, `q3b_slab_race*.txt`, modes `spec` and `wrap`: one linker, 8–16 threads, about
    164,000 instantiations. Every call captured exactly its own token. `FUNCTIONS` stayed at one
    entry the whole time. On the real artifacts, the prototype passed the 8 × 40 check twice
    with 0 wrong, and `FUNCTIONS` stayed at 2 entries (`q5_spec_8x40.txt`).
- **No other allocation per call (question 3, part).** READ: `Instance.exports`, `Caller.get`
  and `wrap_extern` build `Func`/`Memory` with `_from_raw`, which allocates nothing
  (`_instance.py:49-80`, `_extern.py:7-22`). A store's copy of a linker's host functions does not
  free a `FUNCTIONS` entry while the linker lives.
- **The thread-local stack is correct for host functions (question 2).**
  - READ: wasmtime runs a store's code on the calling thread. A `define_func` function runs on
    that thread, inside the C call.
  - `linker.instantiate` (which runs any start function), `_initialize` (the plain reactor) and
    `run` (both binaries) are all entered from `_instance` on the caller's thread
    (`runner.py:314-321`). So the push must come before `instantiate`, as the spec says.
  - EXECUTED, `q2_nested.txt`, on today's runner and the prototype. An outer guest's door ran an
    inner `run`, on the same thread and on another thread it joined. The outer guest then called
    its door again and slept. It got `outer-first outer-second`, and the inner guest got
    `inner`. An inner guest that trapped on its deadline inside the outer door also left the
    outer call correct.
- **Decision 3 holds for the two traps it names (question 4).** EXECUTED,
  `q4_trap_in_alloc.txt`. A WAT guest's `host_alloc` loops until its epoch deadline, or until its
  fuel runs out. The door catches the trap and answers −2. The guest then traps again at its
  next function entry: `INTERRUPT` and `OUT_OF_FUEL`. READ: in `hostmodule.c:46-66`, the code
  after the door calls `PyBuffer_Release` and `free` (function entries) before anything else. So
  the real guest traps at once.
  - wasmtime does not poison a store after a trap in a nested call. The guest went on and
    returned normally in the control cases. That is safe for the host.
- **Decision 4** is the right shape. See finding 6 for one constraint.

## Acceptance criteria against evidence

1. *The four checks exist; the concurrency and allocation checks were seen failing before the
   change.* Not built. The concurrency check fails before the change (EXECUTED, above). The
   slab-lock check, as specified, also fails **after** the change (finding 1).
2. *`uv run pytest` is green with `--accept-judge`.* Not built. Before the change, the
   concurrency check also breaks every later `run` in the same pytest process (finding 4).
3. *A dry run of the release workflow passes every job.* Not built.

## Findings, most severe first

1. **Decision 2 does not hold: wasmtime frees the custom outputs on its own worker threads,
   outside the slab lock** (`runner.py:283-294`, `226`; wasmtime-py `_wasi.py:119-161, 211-215`;
   wasmtime `wasi/src/cli.rs:186-191`, `p2/write_stream.rs:143-148`, `runtime.rs:86-93`,
   `wasi/src/p1.rs:356-420`, `c-api/src/lib.rs:119-125`). High.
   - **Mechanism (READ).**
     - The first WASI call a guest makes builds its stdio descriptors (`p1.rs:356-420`).
       `get_stdout` calls `p2_stream()`.
     - wasmtime-py's `CustomOutputStream` does not override `p2_stream()`. So it wraps a clone of
       the stream in an `AsyncWriteStream`, which spawns a task on wasmtime-wasi's multi-thread
       tokio runtime. That task owns a clone of the `Arc` that holds the `ForeignData`.
     - `store.close()` drops the context and aborts the task. Tokio drops an aborted task's
       future later, on one of its worker threads. Whichever owner drops last runs
       `ForeignData::drop`, and so `custom_finalize` → `CUSTOM_OUTPUTS.deallocate`. Usually that
       is the tokio thread.
   - **What I saw (EXECUTED).**
     - `q3_finalize_thread.txt`, a WAT guest making one `fd_write`, 2,000 calls: 3,996 of 4,000
       frees ran on another (non-Python) thread, outside the lock. One free had still not run
       when the script ended. With a guest making no WASI call, all 4,000 ran on the caller's
       thread, under the lock.
     - `q3c_real_finalize.txt`, the real artifacts and the prototype, `print('x')` × 50, twice:
       100 of 100 frees ran on another thread, without the slab lock.
     - So "the free then happens at a time the runner chooses" is false for every real call.
   - **Effect (EXECUTED, `q3b_slab_race_2.txt`).** The prototype as drafted, 16 threads, 40 s,
     three runs. No output went to the wrong call (0 of about 55,600). But each run ended with
     47–65 free slots **orphaned**: they were reachable from no free-list entry, and no entry was
     live. That only happens when a `deallocate` interleaves with an `allocate`, so the
     interleaving happened. In the same runs with the slab's own methods wrapped in the lock,
     0 slots were orphaned.
   - **Effect (INFERRED from `_slab.py:15-32`).** The interleaving can also give one slot to two
     callers:
     1. `allocate` appends;
     2. a foreign `deallocate(j)` runs before `self.next += 1`;
     3. `next` becomes `j + 1`, which can be a live slot.
     Then one guest's output goes to another call's buffer, the leak the spec exists to close. It
     is rarer than the `FUNCTIONS` race, so the v1.4 check will not see it (finding 4).
   - **The drafted unit check cannot pass.** "Every `CUSTOM_OUTPUTS` … `deallocate` during `run`
     happens while the slab lock is held" fails 100 of 100 times on the real artifacts. And
     `Lock.locked()` says only that *some* thread holds the lock, not this one.
   - **Fix.** The free cannot be moved, so the lock must sit inside the table.
     - The runner wraps `CUSTOM_OUTPUTS.allocate` and `deallocate` with an `RLock`, once, when
       it first imports wasmtime. That is an instance attribute over the bound method, as
       `rev010b/probes/p9c_locked.py` did.
     - It wraps `FUNCTIONS` the same way. Then other wasmtime-py code in the process is covered
       too, and the README's stated limit goes away.
     - EXECUTED, mode `wrap`: 0 wrong and 0 orphaned in 2 × 40 s at 16 threads, and 0 wrong in
       2 × 20 s at 8 threads.
     - It needs an `RLock`. With no WASI call, the free runs on the caller's thread inside
       `close()`. A garbage collection inside `allocate` can also close a config.
     - Holding the lock around `store.close()` is then not needed.
     - Guard the wrap by shape: `type(slab) is _slab.Slab` and the methods are the class's own.
       If the shape is not that, fall back and warn. Pin it with a unit check, since `pyproject`
       allows any `wasmtime>=49,<50`.
     - The spec must decide in writing whether replacing a dependency's private methods at run
       time sits within §4.1. It changes no source tree, but it is a patch of a dependency in
       spirit, so the owner should rule.
     - The other fix keeps outputs out of the table entirely: stdout and stderr as files the
       runner drains with a cap (a FIFO on POSIX, a named pipe on Windows). That is far more
       code, and two more threads per call.
     - Rewrite the unit check either way:
       - every free, on any thread, ran while *its own* thread owned the lock;
       - frees equal allocations after a bounded wait for the asynchronous frees;
       - the free list reaches every non-live slot (no orphans). That is an operation count.

2. **"The only exception left is `KeyboardInterrupt`" is not true of the code: any
   `BaseException` from the host still crosses threads** (`runner.py:498-503`, `451-454`;
   `_func.py:212-216, 244-250`). Medium.
   - READ: the door and `poll_oneoff` catch `Exception`. `asyncio.CancelledError`, `SystemExit`,
     `GeneratorExit` and `gevent.Timeout` are `BaseException`s. A host callable that bridges to
     an event loop raises `CancelledError` in normal use.
   - EXECUTED, `q6_baseexc_crossing.txt`, 10 s. Thread A's host function raised `CancelledError`.
     Thread B's guest only executed `unreachable`. 16,200 of B's calls raised A's
     `CancelledError`, and 16,200 of A's calls got a bare `WasmtimeError`. In `run`, B would
     raise out of `run` for something its guest never did, against spec 006.
   - `KeyboardInterrupt` follows the same path. With concurrent calls, Ctrl-C can surface from a
     worker thread's `run`, while the main thread's call reports a "python exception" trap.
   - Fix: both host functions catch `BaseException` (the door answers −2, `poll_oneoff` answers
     `EINVAL`). Decide `KeyboardInterrupt` and `SystemExit` in writing. One option: catch them
     too, record them on the call's state, have later waits and doors answer at once, and
     re-raise from `run` on its own thread once the guest ends. The cost is that a guest with no
     deadline keeps running after Ctrl-C until it ends. The other option is to keep letting them
     through, and have the README say they may surface from another thread's `run`.

3. **Decision 3's "the trap's cause does not go away" holds only for the deadline and fuel; other
   traps in `host_alloc` now let the guest go on** (`runner.py:500-501`). Medium.
   - EXECUTED, `q4_trap_in_alloc.txt`. When `host_alloc` hit `proc_exit(7)`, `unreachable`, or a
     stack overflow, the door answered −2. The guest then ran to its end and returned normally.
     Today those calls end with exit code 7 or `trapped` set.
   - In the real guest, `host_alloc` is `malloc`. dlmalloc's `abort` on a corrupt heap is
     `unreachable`, and a deep Python stack can overflow inside it. After the change, the guest
     sees `OSError("the host faulted")` and goes on. The unwound frames never restore the C
     shadow-stack pointer (`__stack_pointer`), so each such door call leaks shadow stack
     (INFERRED). That damage stays inside the guest, but the call reports something other than
     what happened.
   - Also EXECUTED: after the −2, straight-line guest code runs before the next check. One
     `fd_write` ran after the deadline. That is bounded by code size, and epoch checks already
     work this way, so it is not new. It is worth one sentence.
   - Fix: the door records the caught trap (or exit) on the call's state and answers −2. `run`
     then reports the recorded trap's name, or `ExitTrap`'s code, ahead of whatever the guest
     did later. Correct the sentence in Decision 3, and add a unit test for each kind.

4. **The v1.4 check poisons its own process before the change, and cannot see finding 1 after
   it** (spec, Decision 6). Medium-low.
   - EXECUTED, `q5_check_warm.txt`. Once the table is corrupt, every later `run` in the process
     fails: repetitions 2 and 3 in the same process got 320 of 320 wrong. In pytest, every test
     after the check would fail too, and a regression would show as many unrelated lost passes.
     Run the check in a child process (`sys.executable`) with a 120 s `timeout=`. That also
     replaces the daemon-thread fail-safe, and it keeps `setswitchinterval` out of the judge's
     own process.
   - EXECUTED, `q3b_slab_race*.txt`: the drafted Decision 2 gave 0 wrong results in about
     89,000 WAT calls. So the v1.4 check passes against a design that is still unsafe. The
     unit-level slab checks (finding 1's rewrite) must carry that weight.
   - Warm both engines before the threads start, so the check fails on the tables and not on the
     stall (finding 6). Add a fuel-capped call to the mix, so both linkers run concurrently. The
     trapping call should print its token before it traps, so "its own trap" is checked by its
     bytes.

5. **Decision 1's reasoning names the wrong set of callbacks** (spec, Decision 1). Low.
   - EXECUTED, `q3d_write_thread.txt`: 200 of 200 stdout callbacks ran on a tokio thread, not on
     the guest's thread. The sentence "a host function runs on that same thread" is true for the
     two `define_func` functions only. The design is right, because outputs are per call and
     never go through the stack. The text should say that, so nobody later routes outputs
     through the thread-local stack.
   - Optional hardening, EXECUTED, `q2b_context_identity.txt`: `caller._context()` has the same
     address as the store's `_context()`. Each stack entry can carry its store's context address.
     The shared function then answers "no host" or `EINVAL` when the caller's address does not
     match. That makes a cross-wire impossible even under a scheduler that interleaves on one
     thread (greenlets).

6. **Smaller points on process-wide state (question 6).** Info.
   - Decision 4: the per-key lock must be the only lock held while compiling. The ticker takes
     `_lock` every round (`runner.py:839-840`), so compiling under `_lock` would stop every
     running call's deadline. Waiters must look in `_modules` again after they get the lock. If
     the compile raises, the next waiter retries (INFERRED).
   - The call must keep its linker in a local for the whole call. `_release` clears `_linkers` at
     exit, while daemon threads (the 120 s fail-safes) may still be inside `instantiate` with the
     GIL released. A local reference keeps the linker alive, as it does today for the engine and
     the module (INFERRED).
   - `_digests` and `_versions` write a dict without a lock. Two threads can only hash the same
     file twice; each write is one dict store. `_placing` is under `_lock`. The ticker's `_count`
     has one writer. No change needed (READ).
   - When the table is corrupt, `custom_call` prints `failed custom output…` to the host's own
     stdout (EXECUTED, `q3b_slab_race.txt`). That stops once finding 1 is fixed.
   - Free-threaded CPython stays out of scope. The wrapped-slab fix would still hold there; the
     unlocked design would race far more often (INFERRED).
   - The text of "The defect" says entries are "freed … by the garbage collector on whatever
     thread it runs". For outputs, wasmtime frees them on its own threads (finding 1). For
     `FUNCTIONS`, a store's drop frees them too, not only the linker's.

## Constitution checks

- §4.1 zero upstream patches: the drafted design holds. Finding 1's fix wraps wasmtime-py's
  private slab methods at run time. No source tree changes, but the owner should rule on it,
  and the spec must record the ruling.
- §4.4 two imports: unchanged; the door and `poll_oneoff` stay the only custom bindings.
- §4.5 embedder-neutral: holds.
- §4.9 tests count: the checks count results and allocations. The 120 s limit is a fail-safe.
  A child process's `timeout=` (finding 4) is a fail-safe too.
- §4.10 evidence: the spec labels its claims. "The free then happens at a time the runner
  chooses" is stated as fact. It is false (finding 1).
- §4.13 tooling: no new dependency.
- §7 never-do list: nothing tripped. Adding the checks changes the judge, which needs
  `--accept-judge`, as the spec says.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Finding 1 — Accepted; Decision 2 is replaced. The runner no longer uses `CUSTOM_OUTPUTS`
   at all: it registers its own C callbacks through the binding wasmtime-py ships
   (`wasmtime._ffi.wasi_config_set_stdout_custom`/`…_stderr_custom`), keyed into its own locked
   dict whose keys are never reused, so a free on a tokio thread can only remove its own
   stream. Neither the reviewer's run-time wrap of the slab's methods (rejected: it rewrites a
   dependency's behaviour in place, which the spec would have to defend under §4.1) nor files or
   FIFOs (more code and threads) is needed. EXECUTED by the author (scratch
   `rev011a/pkg_author`, the review's `q5_check.py`, 3 processes × 2 repetitions, warm): 0 wrong
   of 1,920, `FUNCTIONS` at 2 entries and `CUSTOM_OUTPUTS` at 0; today's runner in the same
   runs: 1–320 wrong per repetition. The unit checks are rewritten: `CUSTOM_OUTPUTS.allocate`
   is called zero times, and the runner's own table empties once the frees have run. A binding
   check pins the private module's shape.
2. Finding 2 — Accepted, and decided: both functions catch `BaseException`, record the first one
   on the call's state, stop the guest through its epoch deadline (Decision 3), and `run`
   re-raises a recorded non-trap exception on its own thread after closing the store. So
   `KeyboardInterrupt`, `SystemExit` and `CancelledError` no longer cross threads, and Ctrl-C
   still ends the call promptly: EXECUTED (`rev011a/author_stop.py`), setting the epoch
   deadline to 0 through the caller's context makes the guest trap with `interrupt` at its next
   function entry, with nothing raised through wasmtime-py.
3. Finding 3 — Accepted: a trap or exit in `host_alloc` is recorded and reported by `run`
   (`ExitTrap` sets `exit_code`, a `Trap` sets `trapped` to its name), and the guest is stopped
   as in 2; unit tests for exit, `unreachable` and stack overflow. The sentence on straight-line
   code before the next check is in Decision 3.
4. Finding 4 — Accepted: the check runs in a child process with a 120 s `timeout=`, warms both
   engines, adds a fuel-capped call, and has the trapping call print its token first. The table
   checks carry the weight for races the check cannot see.
5. Finding 5 — Accepted: Decision 1 says the output callbacks run on wasmtime's threads and never
   use the stack; the optional hardening is taken (each stack entry carries its store's context
   address; a mismatch answers "no host"/`EINVAL`), with a unit test.
6. Finding 6 — Accepted: the compile lock is the only lock held while compiling, waiters
   re-check `_modules`, a failed compile lets the next waiter retry; each call keeps its linker
   in a local; the defect text now says who frees what.

## Reviewer's confirmation, 2026-10-17

I re-read the revised specification and the author's prototype (`rev011a/pkg_author`, which
does Decision 2 only), and ran new probes against copies, never the tree. They are in the same
scratch folder, `c1_stop.py` to `c3c_sigint_flag.py`, each with its `.txt` output. I saw that
`src/wasi_python/runner.py` is already being edited, and did not review or run that.

1. **Finding 1 — confirmed.** The runner registers its own C callbacks through
   `wasmtime._ffi.wasi_config_set_stdout_custom` and `…_stderr_custom`, and keys them into its
   own locked dict.
   - The binding's `argtypes` match the callbacks (READ, `_bindings.py:2034-2038`).
   - EXECUTED, `c2_own_outputs.txt`: the WAT race harness, 16 threads, 2 × 40 s, about 36,000
     calls. 0 wrong, and 0 calls to `CUSTOM_OUTPUTS.allocate`. Right after a call returned, the
     table held 28–30 entries on average (at most 52), which is about the 32 of the calls still
     running. It was empty at the end.
   - Each key comes from a counter and is never reused, so a late free removes only its own key.
     A write whose key is gone answers the length and drops the bytes. The stream is read under
     the lock and written outside it, through a local reference. I found no path where a free,
     or a write after close, reaches another call's stream (READ).
   - Two small points, neither blocking.
     - Until wasmtime's thread frees an entry, that entry still holds the call's `_Stream`, up to
       16 MiB of captured output. If `run` removed its own two keys after `store.close()`, the
       late free would find nothing, and the "table empties" check would need no wait.
     - `_outputs_lock` is a plain `Lock`. A finalizer that runs on a thread already holding it
       would deadlock. That can only happen if the garbage collector closes an unclosed config
       inside one of the locked blocks. The runner closes its configs explicitly, so this is
       INFERRED and unlikely. An `RLock` costs nothing.
2. **Finding 2 — confirmed for exceptions a host raises; disputed for Ctrl-C (new finding A).**
   Catching `BaseException` and re-raising it on the calling thread closes the crossing I
   showed. But Ctrl-C usually does not arrive inside the host function.
3. **Finding 3 — confirmed, with one sentence to correct.**
   - The stop is sound, EXECUTED in `c1_stop.txt` and `c1b_nested_stop.txt`:
     - nothing reaches `LAST_EXCEPTION`;
     - a fuel-metered store also traps with `INTERRUPT`;
     - host calls made after the stop do not trap (imports have no check), so the guest is
       stopped only at its next function entry. That is why "later door calls and waits answer
       at once" is needed;
     - an inner store stopped inside an outer door traps alone, and the outer guest runs on
       normally.
   - The snapshot is compiled by the same engines, with epoch checks, so the stop applies to it
     too (INFERRED; not run on the artifacts).
   - **The sentence "a loop with no call traps at the next epoch tick" is wrong.**
     - READ, `cranelift/src/func_environ.rs:813-880`: a loop header compares the epoch with a
       deadline **cached** at function entry. It reloads the deadline only once the epoch passes
       the cached value.
     - EXECUTED: after a stop, a call-free loop ran until the *original* deadline (1.33 s with a
       1 s deadline, 4.05 s with 3 s, billions of iterations). With no deadline it never ended
       (killed after 60 s).
     - In the real guest, the door's caller calls `PyBuffer_Release` at once, so the door path
       still traps immediately. Correct the text: a call-free loop runs until the call's own
       deadline, or forever without one, as epoch interruption already behaves.
   - Also: after a stop, the fuel counter is stale (`fuel used 3` after billions of iterations).
     When a stop is recorded, `fuel_used` must be `None`, even when the recorded cause is an
     `ExitTrap`.
4. **Finding 4 — confirmed** as written: a child process with `timeout=`, both engines warmed, a
   fuel-capped call, and the token printed before the trap.
5. **Finding 5 — confirmed.** The context-address guard is in Decision 1, with a unit test.
6. **Finding 6 — confirmed** as written.

### New findings

A. **Ctrl-C while a busy guest runs on the main thread aborts the whole host process. This
   predates the revision, and Decision 3 cannot catch it as written.** High.
   - EXECUTED, `c3b_sigint_real.txt`. Today's runner, the real artifacts: a guest computes for
     about 2 s and then sleeps; SIGINT arrives at 0.5 s. The process died with **SIGABRT (exit
     134)** in 3 of 3 runs, after `Exception ignored while calling ctypes callback function
     <function trampoline>: KeyboardInterrupt`.
   - The cause: Python runs the signal handler at the first instruction of wasmtime-py's
     `trampoline`. That is outside its `try` and outside any runner code. ctypes swallows the
     exception and returns without the result written, and wasmtime aborts (`c3_sigint.py`
     reproduces it on a WAT guest).
   - So "Ctrl-C still ends the call promptly" holds only when the signal lands inside the
     runner's own Python code, such as a sleep.
   - Fix, EXECUTED in `c3c_sigint_flag.txt`, 10 of 10 with no abort:
     - while `run` executes on the main thread and the SIGINT handler is Python's default, the
       runner installs a handler that only sets a flag, and restores the default afterwards;
     - the shared host functions turn a set flag into the recorded `KeyboardInterrupt` and the
       stop;
     - `run` re-raises it.
     - In 1 of the 10, a WAT loop that calls only imports ran to its original deadline; that is
       the cached-deadline behaviour in item 3.
   - The handler may be swapped only on the main thread, and only when it is still the default,
     so an embedder's own handler is never replaced. Nested runs keep the outer swap. Record it
     as Decision 3's Ctrl-C rule, with a check that runs in a child process.
B. **Decision 3 should say which exceptions stop the guest.** Low.
   - "Both shared functions catch `BaseException` … On catching one, the function … stops the
     guest" can be read as stopping on an ordinary host `RuntimeError` too. Today that answers −2,
     and the guest carries on with `OSError`; `test_runner_reports_a_host_fault` checks this.
   - `Trap` and `ExitTrap` are themselves `Exception` subclasses.
   - The text should say:
     - a `Trap` or `WasmtimeError` from `host_alloc`, or any non-`Exception` `BaseException`,
       stops the guest;
     - any other `Exception` answers −2 or `EINVAL` as today, and the guest goes on.

### Verdict (confirmation)

Findings 1 and 4–6 are confirmed. Findings 2 and 3 are confirmed with corrections. The
revision can be built once Decision 3 takes the SIGINT rule (A), states which exceptions stop
the guest (B), and corrects the call-free-loop sentence and `fuel_used`. If the owner prefers,
A can be split into its own specification. Then the "Ctrl-C ends the call promptly" claim must
be removed from this one.

### Author's answer to the confirmation

- **(a) Refinements:** both taken. `run` removes its own two output keys once the guest has ended,
  and `_outputs_lock` is an `RLock`.
- **(b) Corrections:** both taken in Decision 3. A call-free loop runs to the call's own deadline,
  or forever without one, because the deadline is cached at function entry. `fuel_used` is `None`
  for any stopped call.
- **A (Ctrl-C aborts the process):** taken into this specification, as Decision 3's Ctrl-C rule,
  with the reviewer's design. While `run` holds the main thread under the default handler, Ctrl-C
  only sets a flag. The shared functions and main-thread waits turn it into a recorded stop, and
  a flag never seen is raised when the call ends. An embedder's handler is never replaced, other
  threads are never touched, and nested calls keep the outer swap.
  - EXECUTED by the author on the real artifacts: a guest that computes, then sleeps, with SIGINT
    while it computes raised `KeyboardInterrupt` at its first host call, 3 of 3. Today's runner
    aborted with exit 134.
  - A v1.4 check runs it in a child process. It fails on today's runner (return code −6) and
    passes on the new one.
- **B (which exceptions stop):** taken, in Decision 3's first bullet. An ordinary `Exception`
  answers as before, and the guest goes on.

## Verdict

Not ready to build. Decision 1 (one linker per engine, a thread-local stack) is sound, and I
confirmed it by execution. Decision 2 rests on a free that wasmtime performs on its own threads,
outside the lock, so the output table stays racy, and its unit check cannot pass. Revise
Decision 2 (finding 1), widen what the host functions catch (finding 2), keep the report of
non-recurring traps in `host_alloc` (finding 3), and isolate the concurrency check (finding 4).
Then build.

One line: share the linker as drafted, but put the lock inside wasmtime-py's tables, because
wasmtime frees output callbacks on its own threads.
