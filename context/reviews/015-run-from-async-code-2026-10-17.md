# Review of 015 — Run from async code (the build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I read `AGENTS.md`, the constitution (§4, especially §4.5, §4.9, §4.10 and §4.15; §7), `context/reviews/README.md` and the 014 build review (for its format). Then I read specification 015 with its landing notes, its pre-build review with both confirmations, and the diff. I did not rely on the landing notes. Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** the scratch clone's `git diff 11085c7 HEAD` (three commits, `3a1692b`, `d00a314`, `7293a2a`): `src/wasi_python/runner.py`, `src/wasi_python/__init__.py`, `tests/checks/test_v1_4_embedding.py`, the new `tests/unit/test_runner_async.py`, `tests/unit/test_runner_calls.py`, `README.md`, `CHANGELOG.md` and the specification.
- **Re-ran (EXECUTED, darwin-arm64, 10 cores, CPython 3.14.2, wasmtime-py 49.0.0, the main tree's `build/artifacts` read only, `WASI_PYTHON_CACHE` the main tree's `build/cwasm-cache`).** Probes, outputs and logs are under `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev015c/` (`pytest-full.txt`, `repeat5.txt`, `repeat_load.txt`, `mutate.py`, `mutations.txt`, `standins-rerun.txt`, `m2_sleep_then_compute.txt`, `logs/`, `probes/*.py` with their `.txt`).
  - `uv run pytest -p no:cacheprovider` in the clone → `147/155 pass · 0 gap · 8 blocked · 0 fail (unit suite 308/314, 6 skipped)`; v1.4 `57/57`; `455 passed, 14 skipped`; ratchet vs `f1db97f37c`: `lost 0 · absent 0 · unrun 0 · unrun locally 6 · gained 9 · grew 0 · judge changed: tests/checks/test_v1_4_embedding.py, tests/unit/test_runner_async.py, tests/unit/test_runner_calls.py`; `next: context/research/2026-10-16-reproducible-builds-on-linux.md (unblocks 4, closes 0)`; **exit 0**. The 8 blocked are the clone's missing source trees, oracle, prior-art clones and wheel. I did not pass `--accept`.
  - `uv run ruff check src tests` → all checks passed; `uv run ruff format --check src tests` → 44 files already formatted.
  - The nine new v1.4 checks, five times in a row: `9 passed` each time. Then three times more with 20 busy shell loops on the 10 cores: `9 passed` each time. No flake seen.
  - **How I mutated.** I never edited the clone. Each mutation went into its own copy of the package and tests (`rev015c/mNN/`), run with the clone's venv and `PYTHONPATH` set to the copy. I checked that `wasi_python.runner.__file__` was the copy in the test process and in a child. At the end the clone's tracked files were `cmp`-equal to copies I took first (`orig/`), and `git status` was clean.
  - I did not commit, push, run `scripts/build.sh` or touch `build/artifacts/`. My pytest runs rewrote untracked state under the clone's `build/`. The only file I wrote outside the scratch folder's `rev015c/` is this review.

## Decisions against the code

- **Decision 1, `run(cancel=)` (READ, EXECUTED).**
  - `cancel` is checked in `_checked` (`runner.py:446-447`): anything but a `threading.Event` is a `TypeError` before any work. A unit test covers it.
  - The first deadline is `min(CANCEL_TICKS, ticks)` with a `cancel` and `ticks` without (`runner.py:568`). m03, which sets `ticks` always, hangs the busy async cancel check (caught).
  - `_watch` (`runner.py:850-864`) makes one `CFUNCTYPE` object under its own lock, keeps it in a module global for the life of the process, and passes a NULL data pointer and a NULL finalizer. No per-call ctypes object exists. A call without `cancel` gets no callback (`runner.py:598`).
  - **`_epoch_answer`** (`runner.py:779-820`) follows the specified order: the lookup (a context that is not the top call's, or a raising lookup, sets `_calls.lost` and stops); a recorded stop; a deferred Ctrl-C, which becomes `call.stopped = KeyboardInterrupt()`; the event (`ended = "cancelled"`); the deadline, `count >= stop_at` (`ended = "deadline"`); otherwise `delta[0] = max(1, min(CANCEL_TICKS, left))` and 0. The whole body is in `try/except BaseException`; a fault records itself as the stop. It never touches `kind` (`_on_epoch` ignores it). It never deletes the error it returns.
  - **But `_stop_error` can return 0 with `delta` left at 0** on four of its five callers (finding 2). EXECUTED (`p1_stop_error.txt`): with `wasmtime_error_new` made to raise, the cancel, deadline, recorded-stop and lost-call paths each return `0` with `delta 0`; only the fault path writes `delta 1`. READ, wasmtime 49 `crates/c-api/src/store.rs:165-176` and `crates/wasmtime/src/runtime/vm/libcalls.rs:707-733`: `delta` starts at 0, and `Continue(0)` sets the deadline to the current epoch, so the callback runs again at the very next check.
  - **The outcomes, end to end (EXECUTED).** `p3_misc.txt`: a pre-set event gives `cancelled`, `exit_code None`, empty stdout and **0 door calls** (the guest never started). A nested `run` with its own `cancel` inside the outer door, whose host sets the outer event too, gives `cancelled` for both. `p4_ctrl_c.txt`: SIGINT to a main-thread `run(cancel=, deadline_s=None)` whose guest never waits raises `KeyboardInterrupt` (outcome 2 closes spec 011's hole for these calls). A deadline under `cancel` is named `deadline` and ends a little later than without (benchmark facts: 69/218/1031 ms against 61/207/1014 ms for 0.05/0.2/1.0 s).
  - `_drive` (`runner.py:638-686`): clears `_calls.lost` at the push, reads and clears it in the `finally`, and raises `RuntimeError("wasi_python lost track of a call")` if it was set, before reading `call.stopped`. The cancelled-before-instantiate path returns `_Driven(None, "cancelled", False, None)` inside the `try`, so the stack is popped. After `call.stopped`, it names `call.ended`. `_fuel_used` returns `None` when `call.ended` is set.
  - `_Waits` gains `cancel.is_set` among its checks, and a `cancel` call's waits are sliced under `deadline_s=None` (`runner.py:571-574`). m02 (no event check in the wait) hangs the sleeping async cancel check (caught).
  - The ticker runs for a call with a deadline or a `cancel` (`runner.py:600`).
- **The landing notes' deviation: a shared host function sets the epoch deadline to 0 when the event is set (READ, EXECUTED).** It is sound.
  - It runs only when `call.cancel is not None` (`runner.py:757`), so only on a store that has the callback. A deadline of 0 there always reaches `_epoch_answer`, never wasmtime's own interrupt trap.
  - It runs only after the call's own function returned normally. A recorded stop returns earlier (`runner.py:751-752`); a host exception goes to `call.stop`.
  - The callback then applies the same order. A recorded stop still wins over the cancel, and a cancel over a deadline, as Decision 1 says.
  - It can rename a guest that was about to exit normally as `"cancelled"`. That is the intended meaning: the event was set while the call ran. It cannot rename a stop, a trap or a lost call.
  - `caller` is the current store's caller, so in a nested call it marks only the inner store.
  - Its coverage is weaker than the landing notes say (finding 4).
- **Decision 2, `run_async` (READ, EXECUTED).**
  - It checks every argument in the coroutine before anything is queued. `_check_executor` looks up `InterpreterPoolExecutor` with `getattr` and checks it first, then `ProcessPoolExecutor`, then requires an `Executor`. The unit tests cover both pools and a non-executor.
  - The mechanism is as specified (`runner.py:266-316`). A fresh event is registered; the call is submitted as `contextvars.copy_context().run`; on `CancelledError`, `future.cancel()` true re-raises; otherwise the event is set and the coroutine waits until `future.done()`, swallowing any outcome, then re-raises the first `CancelledError`. The event leaves the registry in a `finally`. The bare `raise` re-raises the outer `CancelledError`, because the inner `except` has ended (READ; EXECUTED below).
  - EXECUTED (`p3_misc.txt`): a door host sees a `ContextVar` set in the coroutine (`['request-7']`). `asyncio.timeout(0.5)` around a busy guest under `deadline_s=None` raises `TimeoutError`.
  - EXECUTED (`p2_concurrent.txt`, `p2b_staggered.txt`): 36, then 60, concurrent `run_async` calls on the default pool. A third were cancelled by `asyncio.timeout(0.3)` while busy or queued. Meanwhile a thread rewrote `DEFAULTS.async_workers` between 2 and 4 every 3 ms (290 resizes, 30 pools made). Result: every quick call printed its own token, every cancelled one raised `TimeoutError`, no other exception, `_live` empty, and no `wasi-python*` entry left in the temporary directory.
- **Decision 3, Ctrl-C (READ, EXECUTED).** Workers are not the main thread, so `_deferred_ctrl_c` yields and does nothing. `run(cancel=)` on the main thread is covered by outcome 2 (`p4`).
- **Decision 4, the default pool (READ, EXECUTED).**
  - `Defaults.async_workers` uses `field(default_factory=_default_workers)`, which is `min(process_cpu_count() or cpu_count() or 1, 8)`. `_check_workers` refuses `bool`, non-integers and values outside 1–1024. `Defaults` from three arguments works (unit test).
  - `_submit` does the lookup, any resize and `submit` under `_pool_lock`. The old pool is shut down with `wait=False`, so its running and queued calls finish. Every pool made is appended to `_pools` and never removed (finding 7).
  - m15 (no lock in `_submit`) survives. No count-based check can see that race. The lock is right by reading, and `p2b` saw no `RuntimeError` across 290 resizes.
- **Decision 5, fork (READ, EXECUTED).**
  - `_fork["used"]` is set under `_lock` just before `wt.Engine` (`runner.py:1327`).
  - `_after_fork_in_child` takes no lock. It assigns new `_pool_lock` and `_live_lock` objects (`global`), clears the pool, `_pools` and `_live`, resets the ticker's `_thread`, `_active` and `_cond`, and marks the child if `used`. Every user of those locks reads the module global at call time, so the new objects are the ones used.
  - It does not renew `_lock`. A parent thread inside `stats()`, or inside `_engine` before `used` is set, at the moment of the fork leaves `_lock` held in a child that is not refused (finding 8, INFERRED, a very narrow window).
  - `run` and `run_async` call `_refuse_forked()` first, before any lock.
  - The v1.4 fork check passes in both of its forms. m16 (child not marked) is caught.
- **Decision 6, exit (READ, EXECUTED).**
  - On the first `run_async`, `_register_exit_hook` imports `concurrent.futures.thread`, then registers with `threading._register_atexit`, else `atexit`, under `_pool_lock`.
  - The hook copies `_live` under `_live_lock` and sets each event. It then copies `_pools` under `_pool_lock` and shuts each down with `cancel_futures=True`, outside the lock.
  - m06 (no events set), m07 (`atexit` only) and m11 (registered without the import first) each hang the exit check (caught). m05 (no pool shutdown) survives: the queued call's event is already set, so it starts and returns at `_drive`'s pre-instantiate check. The bound holds either way. The shutdown only saves the compile and the zip placement.
  - **Deadlock (INFERRED).** None found. No code path holds two of `_live_lock`, `_pool_lock` and `concurrent.futures`' `_global_shutdown_lock` while waiting for a third in another order. The hook never holds a runner lock while it calls `shutdown`. A `_submit` holding `_pool_lock` waits only on the pool's own locks, which the main thread does not hold while the hook runs. `_python_exit` runs after our hook, on the same thread, and releases its lock before it joins.
  - **Race (EXECUTED, `p6_exit_race.txt`).** The hook sets events, then shuts pools down. A `run_async` on a daemon thread's loop can register its event after the copy and submit before the shutdown. Its guest then runs with its event unset, and exit hangs (finding 3).
- **Decision 7, the checks.** See "The checks" below.
- **Decision 8, the docs.** See finding 1 and finding 9.

## The checks

- **They count (READ).** Each new v1.4 check compares stdout lines, exit codes, `trapped`, `fuel_used` and directory entries. The `timeout=120` on the child, the host's `gate.wait(60)` and `started.wait(120)` are fail-safes: none is asserted on. `deadline_s=0.2` in the deadline check is the limit under test, not a measurement. §4.9 holds.
- **Not flaky (EXECUTED).** 5 runs idle and 3 under 20 busy loops: 9/9 each time. The non-blocking check also holds when `async_workers` is smaller than 4 (INFERRED from the code): the first workers wait on the gate, which the loop sets, and later calls find it already set.
- **Stand-ins (EXECUTED).** The author's table in `standins.txt` matches its script. I re-ran M1 and M3 in copies (`standins-rerun.txt`): M1 fails the non-blocking check (and both async cancel checks); M3 fails both async cancel checks. My m06, m07 and m11 stand for M4, and my m16 stands for M5.
- **The M2 case that passes** (`test_cancelling_an_async_call_stops_its_guest[sleeping]` under "the callback always continues"). The landing notes explain it correctly. The wait's own event check ends the sleep, the guest exits 0, and `run_async` still waits for the worker. So the property that check names holds without the callback. That is acceptable. A cheap change makes the case see the callback too (finding 5, EXECUTED).

### Mutations (EXECUTED, `mutations.txt`, `standins-rerun.txt`, `logs/`)

Each run selects the nine new v1.4 checks, `tests/unit/test_runner_async.py` and `tests/unit/test_runner_calls.py` (35 tests; the baseline passes all 35). "Caught" means at least one test failed.

| # | mutation | result |
|---|---|---|
| m01 | no `_epoch_now` in `_shared` (door and wait) | caught: `test_run_with_cancel[sleeping]` |
| m01b | `_epoch_now` after the door only, not after a wait | **survives** (finding 4) |
| m01c | `_epoch_now` after a wait only, not after the door | **survives** (the wait half covers that test) |
| m02 | a wait does not end at the event | caught: async cancel `[sleeping]` (fail-safe) |
| m03 | first deadline `ticks` (2**62 under `None`) | caught: async cancel `[busy]` (fail-safe) |
| m04 | no event check before instantiation | **survives** (finding 4) |
| m05 | exit hook sets events but shuts no pool down | survives; near-equivalent (above) |
| m06 | exit hook shuts pools down but sets no event | caught: exit check |
| m07 | exit hook through `atexit` | caught: exit check |
| m08 | no `contextvars` copy | **survives** (finding 4) |
| m09 | a queued call is never `cancel()`ed; the event is set and awaited | survives; near-equivalent: the queued call starts and returns at the pre-instantiate check |
| m10 | `_fuel_used` ignores `call.ended` | caught: `run_with_cancel` ×2, unit |
| m11 | exit hook registered without importing `concurrent.futures.thread` first | caught: exit check |
| m12 | a recorded stop does not hold in the callback | caught: stop check, unit |
| m13 | the callback does not enforce the deadline | caught: deadline check, unit |
| m14 | `_drive` does not name `call.ended` | caught: `run_with_cancel` ×2, deadline check |
| m15 | no lock in `_submit` | survives; a race no count can see |
| m16 | fork hook does not mark the child | caught: fork check |
| m17 | no Ctrl-C outcome in the callback | caught: unit |
| s1 | stand-in M1 | caught: non-blocking check, async cancel ×2 |
| s3 | stand-in M3 | caught: async cancel ×2 |

## Acceptance criteria against evidence

1. *The checks exist and were seen failing before the change.* **Met.** Each fails for a missing name on `main` (the landing notes). Each fails against its stand-in (`standins.txt`; M1 and M3 re-run by me). One sleeping case passes under M2, with a correct explanation.
2. *`uv run pytest` is green with `--accept-judge`.* **Met, pending the acceptance run.** EXECUTED: exit 0, `lost 0 · gained 9 · grew 0`, the judge changed in the three named files.
3. *A dry run of the release workflow passes every job.* **Not shown.** Nothing is pushed. Linux and Windows have not run the new checks.

## Findings, most severe first

1. **"Within 50 ms" is not true under GIL contention, and the README and CHANGELOG say it without a condition** (`README.md` "From async code" first bullet, the `cancel` sentence, the exit bullet; `CHANGELOG.md` 0.1.0a3). Low-medium (§4.10).
   - The callback and the clean-up both need the GIL. An async server's event loop is a Python thread that wants the GIL.
   - EXECUTED (`p5_latency.txt`, benchmark facts, 15 trials each, a busy guest on the main thread, the event set from another thread):
     - idle process: set → the callback's stop decision 0–47 ms; set → `run` returns 1–48 ms;
     - one other Python thread spinning: set → stop 0–200 ms (2 of 15 over 50 ms: 138 and 200); set → return **181–457 ms**.
   - The specification's Intent hedges ("once the guest runs"). The README says "The guest stops within 50 ms of the cancel, … and then `CancelledError` … reaches the caller". The exit bullet says "exit waits about 50 ms for each guest". The guests stop in parallel, so that is not "for each", and the clean-up is extra.
   - **Fix.** Say "the guest is checked every 50 ms (5 ticks) while it runs, so it usually stops within about 50 ms. The check and the clean-up need the GIL, so a busy Python thread in the process, such as a loaded event loop, delays both". Put the measured figures in the landing notes as benchmark facts. The same goes for the CHANGELOG line and the `cancel` sentence in the parameter list.
2. **`_stop_error()` returns 0 with `delta` at 0 when an error cannot be made, on four of its five paths** (`runner.py:795-803`, `823-839`). Low.
   - Decision 1 says "every path returns … 0 after writing a `delta` of at least 1, or an error". The function's own docstring says "if one cannot be made, continue for one tick (never 0)". Only the fault path passes `delta`. The lookup-failed, recorded-stop, cancel and deadline paths call `_stop_error()` with no argument.
   - EXECUTED (`p1_stop_error.txt`): with `wasmtime_error_new` raising, each of those four returns `0` with `delta 0`. `ctypes.cast(...).value or 0` does the same if the binding returns NULL.
   - READ: wasmtime then runs `Continue(0)`. That sets the deadline to the current epoch, so the callback runs again at the next function entry or loop back-edge, taking the GIL each time. A transient failure therefore spins rather than waiting one tick. If the failure is permanent (a changed binding), the guest is never stopped, and under `cancel=` its deadline is lost too. The v1.4 checks would then hang to their fail-safe, so the judge would see that case.
   - The unit tests replace `_stop_error` with a fake, so the real one is never run by a unit test. The binding check asserts only that `wasmtime_error_new` is callable, not its shape.
   - **Fix.** Pass `delta` on every path (`_stop_error(delta)`), so the "never 0" rule holds everywhere. Add a unit test that makes `wasmtime_error_new` raise and requires `delta[0] >= 1` for each outcome. Add `wasmtime_error_new`'s `argtypes` and `restype` to the binding check.
3. **The exit hook can miss a call that starts while it runs** (`runner.py:376-387`). Low.
   - The hook copies `_live` and sets those events, then shuts the pools down. A `run_async` on another thread's loop can add its event after the copy and submit before the shutdown. Its worker then runs a guest whose event is never set, and `concurrent.futures` joins that worker at exit.
   - EXECUTED (`p6_exit_race_child.py`, `p6_exit_race.txt`): the real hook, with one scheduling delay injected between its two halves (a set subclass and a lock wrapper; no runner code changed). The late call's guest reached its door, the hook resumed, and the process **hung at exit for 45 s** until killed.
   - INFERRED: the window is microseconds wide without the injected delay. It needs a loop on a non-main thread that starts a call while the interpreter exits, which is the exit check's own shape. With the default 60 s deadline, exit then waits up to 60 s; under `deadline_s=None`, for ever.
   - **Fix.** Under `_pool_lock`, set an `_exiting` flag that makes `_submit` raise the same `RuntimeError` a shut-down pool raises. Shut the pools down first, then copy `_live` and set the events. Any call that submitted before the flag then added its event before the copy.
4. **Three promises have no check that fails when they break, and the landing notes overstate one** (`tests/`). Low.
   - **The deviation's wait half (m01b).** With `_epoch_now` kept after the door but dropped after a wait, everything passes. The landing notes say `test_run_with_cancel[sleeping]` covers "a wait or the door". In that test the door's host sets the event, so the door half fires and the guest never sleeps. Only dropping both halves (m01) is caught. The case the deviation was written for, a sleeping guest cancelled from outside that would exit soon after waking, is not checked.
   - **No guest start once cancelled (m04).** Decision 1 says a call cancelled during set-up "never starts the guest". Without the check, every test passes: the callback still names the call `cancelled` within 5 ticks. EXECUTED (`p3_misc.txt`): the built code gives 0 door calls for a pre-set event.
   - **The context copy (m08).** Decision 2 says a door host sees the request's context variables. Without `copy_context()`, every test passes. EXECUTED (`p3_misc.txt`): the built code does pass the variable.
   - **Fix (all deterministic, counts only).**
     - A unit test of `_shared("poll", …)`: a fake call whose `poll` sets the event, with `_epoch_now` monkeypatched to count. Assert one call. Do the same for `"door"`.
     - A unit test of `_drive` with a set event and a fake linker whose `instantiate` records itself. Assert it is never called and the result is `"cancelled"`. Optionally, a v1.4 case: a pre-set event, and the door host counts to 0.
     - In `LOOP_FREE`, set a `ContextVar` in `main()` and have the host return it, so the check also requires the copy.
     - Correct the landing-notes sentence.
5. **The sleeping async cancel case could also see the callback** (`CANCEL_ASYNC`). Info.
   - EXECUTED (`m2_sleep_then_compute.txt`). I changed the sleeping guest to `time.sleep(10**6)` followed by `while True: pass`. The built code passes both cases in 4.5 s. Under stand-in M2, both cases fail (the guest wakes, then computes for ever).
   - **Fix.** Take that guest, or say in the landing notes why the current one is kept.
6. **`import wasi_python` now imports `asyncio`, `ssl` and 54 more modules** (`runner.py:19-22`). Info.
   - EXECUTED: 127 modules after `import wasi_python` at `11085c7`, 183 now. `ssl`, `asyncio` and `concurrent.futures` are new. A program that never uses `run_async` pays for them.
   - Also, the first `run_async` imports `wasmtime` (about 12 ms, a benchmark fact) and `concurrent.futures.thread` on the event loop.
   - **Fix.** Import `asyncio`, `contextvars` and `concurrent.futures` inside `run_async` and its helpers. The annotations are already strings.
7. **`_pools` keeps every default pool ever made** (`runner.py:334`, `351`). Info.
   - EXECUTED (`p2b_staggered.txt`): after 290 resizes, 30 shut-down pools are held. Each keeps its exited threads' objects.
   - **Fix.** Drop pools whose threads have all exited when appending, or hold them in a `weakref.WeakSet`. The exit hook needs only live ones.
8. **The fork hook does not renew `_lock`** (`runner.py:401-411`). Info, INFERRED.
   - Suppose a parent thread holds `_lock` at the fork, inside `stats()` or inside `_engine` before it sets `used`. Then a child that is not refused deadlocks on its first `run`. The window is a few bytecodes.
   - **Fix.** Assign a new `_lock` in the hook too. It is only an assignment, as the hook's rule requires.
9. **Doc nits** (`README.md`, the spec). Low.
   - "`run_async` takes `run`'s arguments, plus `executor`". It does not take `cancel` (passing it is a `TypeError`). Say "except `cancel`".
   - The `trapped` list (`"out of fuel"`, `"deadline"`, or a trap's first line) does not name `"cancelled"`.
   - The limitations paragraph still lists "Ctrl-C for a guest that never waits … with `deadline_s=None` (it runs on)". Under `cancel=` that is now closed (EXECUTED, `p4`). Add "unless the call has a `cancel`".
   - Decision 6 says that if `threading._register_atexit` is missing, "the README's sentence on exit says that exit can wait". The README's exit bullet does not say so.
   - The Starlette disconnect sentence is INFERRED from Starlette's documented behaviour, not run. The landing notes say so. It is acceptable as written.
   - The spec's status line reads "built 2026-10-17, awaiting its build review". Housekeeping at landing.

## Constitution checks

- **§4.1 zero upstream patches; §4.2 pins; §4.6 the artifact set.** Untouched. The change is host-side only.
- **§4.4 two imports.** Holds. The epoch callback is wasmtime's store API, not a guest import.
- **§4.5 embedder-neutral.** Holds. The code names no embedder. The README names FastAPI, Starlette, gunicorn and trio as frameworks a host app may use, not as consumers that get anything special. No default or test refers to one.
- **§4.9 tests count.** Holds (above). The latency figures in this review are benchmark facts, not checks.
- **§4.10 evidence.** The landing notes' claims reproduce, except the coverage sentence (finding 4). The README's 50 ms claim is not true as stated under GIL contention (finding 1).
- **§4.13 tooling.** No new dependency: `asyncio`, `contextvars` and `concurrent.futures` are stdlib. ruff is clean.
- **§4.15 safe by default.** No default is loosened.
  - `async_workers` is a new bound with a stated reason: memory per worker, and the measured speedup flattening past 8.
  - `run_async` takes `DEFAULTS` for every limit (`_checked`).
  - Under `cancel=`, the deadline is enforced by the callback instead of wasmtime's interrupt. It still holds (the deadline check, `p3`), 1–2 ticks later. The ticker already needed the GIL, so that adds no new dependence.
  - No channel opens.
  - Finding 2's permanent-failure case would lose the deadline under `cancel=`. That is a fault path, not a default, and the v1.4 checks would hang on it.
- **§7 never-do list.** Nothing tripped. The judge changed in three files, so the acceptance needs `--accept-judge`.

## Verdict

**Does not land yet.** The design is built as decided, and every behaviour I probed is right:
- cancellation, busy or sleeping, from `run` or `run_async`;
- the order of outcomes;
- stops and deadlines under `cancel`;
- Ctrl-C;
- concurrency with resizes;
- exit and fork.

The deviation is sound. The judge is green and steady under load.

Before landing:
- correct the 50 ms claim in the README and CHANGELOG (finding 1);
- make the "never return 0 with `delta` 0" rule true on every path (finding 2);
- add the deterministic checks for the three unguarded promises, and correct the coverage sentence (finding 4).

Finding 3 is a small reorder of the exit hook and should come with them. Findings 5–9 are optional. It then lands once the `--accept-judge` run is recorded on `main`.

One line: `run_async` and `run(cancel=)` work as specified and the judge holds, but the README promises 50 ms that a busy event loop does not keep, one stop path can return a zero delta, and three promises have no check that fails when they break.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. F1 — Fixed: README and CHANGELOG say the check runs every 50 ms while the guest computes, at once at a wait or door call, and that it and the clean-up need the GIL, quoting your measurement; the exit bullet says the guests stop together. The spec's Intent says the same.
2. F2 — Fixed: `_stop_error(delta)` writes 1 on every path that makes no error (a raise, or a NULL error); every caller passes `delta`. `test_the_stop_error_is_real_and_never_leaves_a_zero_delta` runs the real function, frees the real error, and covers both failure paths; it fails on the first version (EXECUTED, `standins2.txt`). The binding's shape was already pinned in `test_the_bindings_the_runner_calls_exist`.
3. F3 — Fixed: `_stop_async_calls` sets `_hook["exiting"]` and shuts the pools down under `_pool_lock` first, then sets the events; `_submit` raises "cannot schedule new futures after interpreter shutdown" once exiting.
4. F4 — Fixed: `test_a_host_function_returning_under_a_set_event_stops_the_guest`, `test_a_call_cancelled_before_it_runs_never_starts_its_guest`, and a `ContextVar` the door host must see in `test_async_calls_do_not_block_the_loop`; each fails without its behaviour (EXECUTED, `standins2.txt`). The landing notes no longer overstate the coverage.
5. F5 — Taken: the sleeping async guest computes after it wakes; stand-in M2 now fails both cases (EXECUTED).
6. F6 — Fixed: lazy imports; `import wasi_python` adds 92 modules, as on `main` (EXECUTED).
7. F7 — Answered: each replaced pool is shut down when it is replaced; its threads end once idle, and its list entry is an object with no threads. Pools are replaced only when an embedder changes `DEFAULTS.async_workers`, a configuration step, so the list grows with deliberate changes, not with calls. The exit hook needs the old pools that still have queued calls, and a prune would need the executor's private thread list.
8. F8 — Fixed: the fork hook renews `_lock`, `_epoch_callback_lock`, `_outputs_lock`, `_pool_lock`, `_live_lock` and empties `_compiling`, by assignment only.
9. F9 — Fixed: "`run`'s arguments except `cancel`"; `"cancelled"` in the `trapped` list; the Ctrl-C note says `cancel=` closes that hole; the exit bullet names the fallback; the status line is updated.

## Confirmation (2026-10-17)

- **Reviewer:** the build reviewer above (Claude Opus 5.5), not the author.
- **Read:** the dispositions above, and the clone's `git diff 7293a2a HEAD`: the runner, the three test files, the README, the CHANGELOG and the specification. The clone is rebased onto `main` at `11b8bd8` (spec 007), with `3d4132b` and `9d7bc97` on top. I also read the author's `build015/standins2.py` and `standins2.txt`.
- **Re-ran (EXECUTED, darwin-arm64).** Artifacts: spec 007's clone's set (`build007/repo/build/artifacts`). Cache: a scratch one, `rev015c/conf/cache`, so I wrote nothing in the main tree. Logs are in `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev015c/conf/`.
  - `uv run pytest -p no:cacheprovider` → `152/163 pass · 0 gap · 11 blocked · 0 fail (unit suite 312/318, 6 skipped)`; v1.4 `57/57`; `464 passed, 17 skipped`.
    - Ratchet vs `11085c7a1e`: `lost 0 · absent 0 · unrun 0 · unrun locally 9 · gained 9 · grew 0`. The judge changed in `test_v1_4_embedding.py`, `test_runner_async.py` and `test_runner_calls.py`.
    - `next:` reproducible-builds-on-linux (unblocks 7). **Exit 0.**
    - The 11 blocked are the clone's missing source trees, oracle, prior-art clones, wheel and three systems.
  - `ruff check` is clean, and `ruff format --check` reports 46 files already formatted.
  - I ran the new v1.4 checks and `test_runner_async.py` (24 tests) three times idle and twice under 20 busy loops on 10 cores. All 24 passed every time.
  - Mutations, each in its own copy (`conf/mutate2.py`, `conf/mutations.txt`). Afterwards the clone's changed files were `cmp`-equal to my copies (`conf/orig/`), and `git status` was clean. The only tracked file I wrote is this section.

### Each disposition

1. **F1 — confirmed.** READ: the README's cancel bullet, the `cancel` sentence in the argument list, the exit bullet ("together … about as long as one cancel"), the CHANGELOG line and the spec's Intent now carry the GIL condition and quote the measurement. "At once when it waits" means within one 10 ms slice of the wait. That is fair.
2. **F2 — confirmed.**
   - READ: every caller passes `delta`. `_stop_error` writes 1 whenever it returns 0, whether from a raise or a NULL error.
   - EXECUTED: the restored no-delta write (f2) and a NULL error returned as 0 (f2b) each fail `test_the_stop_error_is_real_and_never_leaves_a_zero_delta`.
   - One sentence of the disposition is not accurate. It says the binding's shape "was already pinned in `test_the_bindings_the_runner_calls_exist`", but that test still asserts only `callable(_ffi.wasmtime_error_new)` (READ). The new test calls the real function and deletes the real error, so a changed shape now fails it. That is enough, so no change is needed.
3. **F3 — confirmed for the default pool. A residual remains for a caller's `executor`** (new finding N1 below).
   - READ: the hook sets `exiting` and copies the pools under `_pool_lock`, shuts them down, then copies `_live` and sets the events. `_submit` refuses once `exiting` is set.
   - EXECUTED (`conf/p7_exit_race_child.py`, `p7_exit_race.txt`): the revised hook, paused right after its `_live` copy. A late `run_async` on the default pool raised `RuntimeError: cannot schedule new futures after interpreter shutdown`, and the process **exited 0**.
   - Mutation f3 (the `exiting` check dropped) survives. Like m15, that race cannot be counted.
4. **F4 — confirmed.**
   - EXECUTED: m01b (no deadline of 0 after a wait), m04 (no check before instantiating) and m08 (no context copy) are each caught by their new test.
   - m01c (no deadline of 0 after the door only) still survives. It is an artificial branch on `kind`: the code has one shared line for both kinds, and the sleeping check covers the door half through the wait half. No action.
   - The landing-notes sentence is corrected.
5. **F5 — confirmed.** READ: the sleeping async guest now runs `while True: pass` after its sleep. The author's `standins2.txt` shows stand-in M2 failing both cases. My earlier run of the same variant showed the same (`rev015c/m2_sleep_then_compute.txt`).
6. **F6 — confirmed.** EXECUTED: `import wasi_python` brings the process to 127 modules, the same as `main` at `11b8bd8`. It adds 92, and `asyncio`, `ssl` and `concurrent.futures` are not among them. The imports are local, and the module-level annotations are strings.
7. **F7 — confirmed; the answer is accepted.**
   - EXECUTED (`conf/p8_pools.py`, `p8_pools.txt`): I made 30 resizes with calls in between, then waited 1 s. Of 29 replaced pools, none had a live thread. Together they held 57 dead `Thread` objects, and the process had 5 live threads.
   - So "an object with no threads" is true of live threads. Each entry still holds its exited `Thread` objects, which is a few small objects per deliberate resize, not per call.
   - The reason to keep the pools is sound (READ). A replaced pool shut down with `wait=False` still runs its queued calls, and the exit hook's `cancel_futures=True` is what drops them. Pruning safely would need `_threads`, which is private. A bounded, configuration-driven growth is an acceptable cost.
8. **F8 — confirmed.** READ: the fork hook assigns new `_lock`, `_epoch_callback_lock`, `_outputs_lock` (an `RLock`, as before), `_pool_lock` and `_live_lock`, and a new empty `_compiling`. It takes no lock. Every user reads these module globals at call time. The fork check passes.
9. **F9 — confirmed.** READ, each in the README:
   - "`run`'s arguments except `cancel`";
   - `"cancelled"` in the `trapped` list;
   - the Ctrl-C limitation now says "and no `cancel` … with `cancel=`, the runner's check ends it";
   - the exit bullet names the missing `_register_atexit` case.

   Two housekeeping nits remain:
   - The status line still ends with the pre-build clause "It changes the runner's API, so the reviewer confirms the revision before it is built".
   - This review now has two "Disposition" headings: the template's empty one and the author's.

### New finding

N1. **At exit, a call on a caller's `executor` can still be missed.** Low.
- `_submit` checks `exiting` only for the default pool. A `run_async(executor=mine)` that registers its event after the hook's `_live` copy still submits, and nothing sets its event.
- EXECUTED (`p7_exit_race.txt`, the same pause after the `_live` copy): the late call's guest ran, and the process **hung at exit for 60 s** until killed. `concurrent.futures` joins the caller's pool too.
- INFERRED: the window is microseconds wide without the injected pause. It needs a caller executor and a call started from a non-main loop during exit.
- **Fix (two lines).** In `_stop_async_calls`, set a flag under `_live_lock` together with the copy. In `run_async`, check that flag where the event is added, and raise the same `RuntimeError`. Alternatively, name the case in the spec's "Left over" and in the README's exit bullet.

### Verdict

**Lands.** All nine dispositions are confirmed. Each fix is in the code or the text, and each new check fails without its behaviour. F7's answer holds on the evidence. The judge is green with the spec 007 artifacts and steady under load. N1 is low and narrow. Fix it in this change, or record it as a known gap; it does not block. The landing still needs the `--accept-judge` run recorded on `main`. Acceptance criterion 3, a release-workflow dry run (Linux and Windows run these checks first), is still to be shown.

One line: every finding is fixed or soundly answered. One narrow exit race remains for a caller's own executor, and it does not block landing.

## Disposition of the confirmation

- N1 — Fixed: `run_async` refuses with "cannot schedule new futures after interpreter shutdown" when `_hook["exiting"]` is set, checked under `_live_lock` where it adds its event; the hook sets `exiting` before it reads `_live`, so a call is either in the hook's list or refused.
- The status line and the doubled Disposition heading are fixed. F2's sentence about the binding test was wrong, as you say: the real-function test covers the shape.

## Follow-up: the fork check on Windows (2026-10-17)

- **Reviewer:** the build reviewer above (Claude Opus 5.5), not the author.
- **Reviewed:** the main tree's uncommitted `git diff tests/checks/test_v1_4_embedding.py`, on top of `bbeac1f`. I also read the dry run's log (`gh run view 39038155556`), the harness's `needs.py` and `plugin.py`, and `release.yml`.
- **Evidence:** logs are in `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev015c/winfork/`.
  - READ, the dry run's log. Windows gave v1.4 56/57; the only failure was this check, skipped without a known need. Linux and macOS ran it and passed it (57/57 each).
  - EXECUTED on macOS, with the main tree's artifacts: the changed check passes through its fork path.
  - EXECUTED: I ran the new `NO_FORK` child with `os.fork` and `os.register_at_fork` deleted first, to stand in for Windows. It prints exactly the two expected lines.
  - EXECUTED: I then removed the runner's `hasattr` guard, in a copy of the package. The same child fails with `AttributeError: module 'os' has no attribute 'register_at_fork'`.
  - ruff is clean on the file. I changed nothing in the tree except this section.

**Verdict: honest, and the right shape. Keep the branch; do not add a platform need.**
- The harness's needs are inputs that a document provides. A blocked check feeds the `next:` line ("what to do next"). A need for `fork` could never be met on Windows. It would be a permanent "blocked" that points at no work.
- The tree's own precedent is a branch inside the check: the `os.name == "posix"` branches at `test_v1_4_embedding.py:278` and `:332` still assert what does apply.
- On Windows there is no fork, so what applies is this: the hook's guard keeps the import working, and the runner is never marked forked.
- Be clear what a Windows pass means. This branch is a smoke check. It can fail only in ways every other check on that host would also fail: an import error, or a refused call. A green `test_a_forked_child_is_refused` on win32 therefore says "nothing fork-related breaks here". It does not say "the refusal was checked". The docstring says as much. The refusal itself is checked on Linux and macOS, as the dry run shows.
- The change alters the judge, so its acceptance needs `--accept-judge`.

**Anything else in 015's checks that is Windows-specific in the same way?** None.
- Every other 015 check passed on windows-2025 in this dry run (READ).
- 015's new unit tests do not run in the verify jobs ("unit suite 0/0"). They use no platform-specific call, except `ProcessPoolExecutor(1)`, which is never started.
- **One latent case of the same kind, not 015's.** `tests/checks/test_v1_2_hostile_guest.py:394` uses `@pytest.mark.skipif(sys.platform == "win32", reason="no RLIMIT_NOFILE to lower on Windows")`. That is a skip that names no need. It has passed only because the Windows verify job runs `test_v1_1_artifact_set.py`, `test_v1_2_portable_and_sealed.py`, `test_v1_3_data_stack.py` and `test_v1_4_embedding.py`, not the hostile-guest file (READ, the job's command).
- The first run of the judge on Windows that includes that file will fail the same way. Give it the same treatment now: a branch that asserts what applies on Windows, or a recorded gap. Spec 016 is the natural place.
