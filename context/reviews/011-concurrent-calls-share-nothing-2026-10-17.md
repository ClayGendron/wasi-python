# Review of 011 — Concurrent calls share nothing (the build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I read `AGENTS.md`, the
  constitution, `context/reviews/README.md`, the 010 build review (for its format),
  specification 011 with its landing notes, and its pre-build review with the dispositions and
  the reviewer's confirmation. Then I read the diff. I did not rely on the landing notes. Each
  claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** the uncommitted working tree on top of `9512e3a`: `src/wasi_python/runner.py`,
  `tests/checks/test_v1_4_embedding.py`, the new `tests/unit/test_runner_calls.py`, `README.md`
  and `CHANGELOG.md`. I ignored `context/questions-for-the-owner.md`, spec 010's dry-run note and
  spec 012's files, which another piece of work owns.
- **Re-ran (EXECUTED, darwin-arm64, host CPython 3.14.2, wasmtime-py 49.0.0, the artifacts in
  `build/artifacts/` read only).** Probes, outputs and the mutation log are under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev011b/`
  (`probes/*.py` with their `.txt`, `mutate.py`, `mutations.txt`, `logs/`, `pytest-full.txt`).
  - `uv run pytest` → `128/131 pass · 1 gap · 2 blocked · 0 fail (unit suite 211/211)`;
    `339 passed, 2 skipped, 1 xfailed`; ratchet `lost 0 · absent 0 · unrun 0 · gained 3 · grew 0
    · judge changed: tests/checks/test_v1_4_embedding.py, tests/unit/test_runner_calls.py`;
    **exit 0**. This matches the landing notes. The acceptance with `--accept-judge` is the
    author's.
  - `uv run ruff check src tests` → all checks passed; `uv run ruff format --check src tests` →
    40 files already formatted.
  - 20 mutations of the runner, each applied in place, run against the four test files that
    touch it, and restored byte for byte from a copy taken first (table below). At the end
    `git diff` was byte-identical to the diff saved before I started, the five changed files
    were `cmp`-equal to their copies, and `git status --porcelain` was unchanged.
  - For "before the change" I ran the committed runner (`git show HEAD:`) from a scratch
    package (`pkg_head/`) through `PYTHONPATH`, never the tree.
  - I did not commit, push, run `scripts/build.sh` or touch `build/artifacts/`. My pytest runs
    rewrote untracked state under `build/progress/`. The only tracked-tree file I wrote is this
    review.

## Decisions against the code

- **Decision 1, one linker per engine (READ, EXECUTED).** `_linker` builds it under `_lock` and
  caches it per engine (`runner.py:470-487`). `_instance` keeps it in a local. `_drive` pushes
  the `_Call` before `instantiate` and pops it in a `finally` (`:365-386`). `_shared` serves the
  top entry only when `_context_address(caller)` equals the entry's (`:435-465`). An empty stack
  or a mismatch answers `NO_HOST` or `EINVAL`. After warm-up, `FUNCTIONS` held 4 entries
  (2 engines × 2 functions) through every run below. `_linkers` held 2.
- **Decision 2, outputs (READ, EXECUTED).** `_send_outputs` calls
  `_ffi.wasi_config_set_stdout_custom`/`…_stderr_custom` with the runner's own `CFUNCTYPE`s. Its
  keys come from `itertools.count(1)` and are never reused. `_outputs_lock` is an `RLock`.
  `_output_write` never raises. `run` pops its two keys after the guest ends (`:344-346`). The
  binding's `argtypes` (`_bindings.py:2036`) match the runner's callback types. `CUSTOM_OUTPUTS`
  stayed at 0 entries in every run.
- **Decision 3, the stop (READ, EXECUTED).** Both shared functions catch `BaseException` and
  call `_Call.stop`. `stop` records the first cause, then sets the store's epoch deadline to 0
  (`:410-418`). `_drive` then reports or raises the cause (`:388-398`), and `fuel_used` is `None`
  when a stop was recorded (`:341`). See "The stop" below.
- **Decision 3, Ctrl-C (READ, EXECUTED).** `_deferred_ctrl_c` wraps `_call` only. So module
  compile, stdlib placement and the root's removal stay under the caller's own handler. It swaps
  the handler only on the main thread, and only from `default_int_handler`. See "Ctrl-C" below.
- **Decision 4, one compile per key (READ, EXECUTED).** `_module` takes a per-key `Lock` from
  `_compiling` and re-checks `_modules` under it. `_lock` is never held across a compile.
  EXECUTED (`compile_once.txt`): 12 threads started at once in a cold process with
  `cache_dir=False`. The change compiled 2 modules (one per engine), and all 12 results were
  right. The committed runner compiled 12. As a benchmark fact, the run took 6.4 s against 189 s.
- **Decision 6, the checks (READ).** They all exist. The concurrency check uses 8 × 100 calls,
  not the specified 8 × 40, and the landing notes give the reason. The stop checks for a host's
  `BaseException` do not check "the door's answer as the guest stored it", which Decision 6
  promises. That gap is why one mutation survives (finding 1).

## Concurrency (EXECUTED)

- **The check's own script** (`concurrent_check.txt`), 3 fresh processes:
  `800 calls, 0 wrong, 0 raised` each time. On the committed runner (`concurrent_check_head.txt`):
  6–7 wrong and 395–656 raised in 3 of 3 runs. So the check fails before the change.
- **The table check before the change** (`tables_head.txt`): `{'define_func': 6, 'custom
  outputs': 6}`, as the landing notes say.
- **My stress** (`stress.py`). It used 16 threads and `setswitchinterval(1e-6)`, with both
  engines and both binaries warmed. It mixed 15 kinds of call:
  - stdout plus stderr, and the plain reactor;
  - the door (checking the host saw this call's own frame), a 0.01 s sleep, fuel;
  - a deadline trap, out of fuel, `SystemExit(5)` and `os.abort()`;
  - a host `RuntimeError`, a host `CancelledError` and a host custom `BaseException`, each
    carrying the call's token;
  - a nested run from a door (with and without fuel), a nested run that trapped, and a nested
    run whose host raised.
- **Results with the change.** 16 × 60 twice and 16 × 400 once (6,400 calls, 87 s): 0 wrong and
  0 raised. Every `BaseException` came back with its own call's token. After the runs:
  - `FUNCTIONS` was still 4 and `CUSTOM_OUTPUTS` still 0;
  - `runner._outputs` was empty, `LAST_EXCEPTION` was `None`, and there were 2 linkers and
    4 compile guards;
  - no deadlock, under a 400–1,200 s `faulthandler` watchdog.
- **The same stress on the committed runner** (`stress_head.txt`): 895 raised and 10 wrong of
  960. That included crossings such as `deadline t-5-0: CancelledError: t-10-0`.
- **Other wasmtime-py code in the same process** (`neighbours.py`, 6 runner threads, 6 threads
  of plain wasmtime-py, 20 s each) is finding 3.

## The stop (EXECUTED, `stops.py`, `stops.txt`, `stops_fail.txt`)

A WAT guest stood in for the artifact set's binary through the public `run`, with and without
fuel. After the door call, the guest makes one `fd_write` (`after`), then calls an empty
function, then writes `end`.

| cause | result | `fuel_used` with fuel |
|---|---|---|
| buffer returned | exit 40, `after end` | 59 |
| host `RuntimeError` | exit 38 (the −2 seen), `after end` | 41 |
| `proc_exit(7)` in `host_alloc` | exit 7, `after` only | `None` |
| `unreachable` in `host_alloc` | trapped, `after` only | `None` |
| stack overflow in `host_alloc` | trapped, `after` only | `None` |
| `host_alloc` loops to the deadline / out of fuel | `deadline` / `out of fuel`, `after` only | `None` |
| host sleeps past a 0.2 s deadline | `deadline`, `after` only | `None` |
| host `CancelledError` / `SystemExit` | `run` raises it | — |

- `LAST_EXCEPTION` was `None` after every row.
- The import call (`after`) still runs after the stop. The guest stops at the next function
  entry (`end` never appears). This is as Decision 3 states.
- On the real artifacts, the snapshot and the plain reactor, with and without fuel: a host
  `CancelledError` raised from `run`. A host that slept past the deadline gave `deadline` with
  `fuel_used` `None`.
- **When `call.stop` itself fails.** I made only the stop's
  `wasmtime_context_set_epoch_deadline(ctx, 0)` raise. The cause is recorded before the call, so
  it is kept. The guest is not stopped and runs to its end (`after end`). `run` still raises the
  `CancelledError`, or reports exit 7. The degradation is safe.
- **Trap names (READ, pre-existing).** `unreachable` and stack overflow are both reported as
  `error while executing at wasm backtrace:`, the first line of wasmtime's message. That is how
  the runner already named the guest's own traps.

## Ctrl-C (EXECUTED, child processes; `ctrlc_*.txt`)

Each child sets `signal.default_int_handler` itself, then the parent sends SIGINT.

| case | the change | committed runner |
|---|---|---|
| guest computes, then sleeps 30 s, no deadline | `KeyboardInterrupt` at the sleep; handler restored; next call works | **SIGABRT (−6)** |
| sleep 30 s, no deadline | `KeyboardInterrupt` after 1.01 s | — |
| computes forever, 6 s deadline | `KeyboardInterrupt` at 6.08 s | — |
| computes, then ends normally | `KeyboardInterrupt` once it ends (result discarded) | — |
| `while True: print(...)`, no deadline | never ends (killed at 30 s) | the same (finding 4) |
| the same, 5 s deadline | `KeyboardInterrupt` at 5.08 s | the same |
| embedder handler that only records | call completes; handler called once and kept | — |
| embedder handler that raises | **SIGABRT (−6)** | — (finding 2) |
| `asyncio.run`, a second SIGINT after the first was handled | **SIGABRT (−6)** in `asyncio/runners.py:_on_sigint` | — (finding 2) |
| call on a worker thread | main gets `KeyboardInterrupt` in `join`; the worker's call completes normally | — |
| nested run from a door, inner computes / inner sleeps | the outer `run` raises `KeyboardInterrupt` | — |
| SIGINT during a cold compile (`cache_dir=False`) | `KeyboardInterrupt` after the compile; next call works | — |
| exception inside `run`; host raises `KeyboardInterrupt` | handler back to default | — |
| host installs its own handler during the call | **overwritten** with the default afterwards | — (finding 5) |

- **Random SIGINTs** (`ctrlc_loop.txt`). Three 30 s loops of mixed calls (door-heavy, compute
  and sleep, print; snapshot and plain) took 133 SIGINTs at random times each, landing during
  calls and between them.
  - With the change: 963 calls, 378 `KeyboardInterrupt`s, 0 wrong results, the handler was the
    default after every call, and there was no abort.
  - The committed runner aborted with −6 in both runs I made (`ctrlc_loop_head.txt`).

## Mutations (EXECUTED, `mutations.txt`, `logs/`)

"Caught" means a test failed. The tests run were `tests/unit/test_runner_calls.py`,
`tests/unit/test_runner_waits.py`, `tests/checks/test_v1_4_embedding.py` and
`tests/checks/test_v1_2_hostile_guest.py` (88 tests). Each mutation was restored and checked by
SHA-256.

| mutation | result |
|---|---|
| context check removed | caught: `test_a_caller_from_another_store_gets_no_host` |
| **no stop** (epoch deadline not set) | **survives** (finding 1) |
| **shared functions catch `Exception`, not `BaseException`** | **survives** (finding 1) |
| `run` does not pop its output keys | survives: wasmtime's free removes them; a refinement |
| `_output_free` keeps the key | survives: `run`'s pop removes them |
| both of the above | caught: `test_calls_add_nothing_to_wasmtime_pys_tables` |
| per-key compile lock removed | survives (Decision 4 names no check) |
| linker not cached (`define_func` per call) | caught: the table check and the concurrency check |
| Ctrl-C: never swap the handler | caught: the v1.4 Ctrl-C check and two unit tests |
| Ctrl-C: shared functions ignore the flag | caught: `test_ctrl_c_during_a_call_stops_it_and_is_raised_by_it` |
| Ctrl-C: flag checked only after the host function | caught: the same |
| Ctrl-C: an unseen flag not raised at the end | caught: `test_ctrl_c_no_host_function_saw_is_raised_when_the_call_ends` |
| **Ctrl-C: waits do not check the flag** | **survives** (finding 1) |
| **`fuel_used` counted for a stopped call** | **survives** (finding 1) |
| `_drive` ignores the recorded cause | caught: 8 tests |
| `_drive` swallows a `BaseException` cause | caught: 5 tests |
| later host calls not answered at once | survives (INFERRED: it matters only when straight-line code makes a second host call before a function entry) |
| **stack never popped** | **survives** (finding 1) |
| output lock a plain `Lock` | survives (the deadlock it prevents is INFERRED and needs the collector inside a locked block) |
| door answers −2 for a trap in `host_alloc` | caught: the exit and trap tests |

What three of the surviving mutations do, run from scratch packages against my probes
(EXECUTED):
- **`except Exception` in `_shared`** (`stress_baseexc.txt`). The 16 × 60 stress gave 15 wrong
  and 11 raised. The raises were crossings such as `mine t-15-11: CancelledError: t-2-11`. The
  judge stays green because in one thread wasmtime-py's own `LAST_EXCEPTION` carries the same
  exception back to the same caller.
- **No stop.** The WAT guest printed `end` after every `host_alloc` exit or trap, so the guest
  ran on. `run` still reported the recorded cause, so every test passed.
- **Waits ignore the flag.** Ctrl-C during a no-deadline 30 s sleep raised only after
  30.09 s instead of 1 s.

## Acceptance criteria against evidence

1. *The concurrency check, the table checks and the Ctrl-C check were seen failing before the
   change.* **Met.**
   - EXECUTED: the concurrency script, 3 of 3 runs on the committed runner (6–7 wrong,
     395–656 raised).
   - EXECUTED: the table counts were `{'define_func': 6, 'custom outputs': 6}`.
   - EXECUTED: the Ctrl-C check's scenario (compute, then sleep, under the default handler)
     aborted with −6.
   - READ: the unit file cannot import against the committed runner, which has no `_Call`.
2. *`uv run pytest` is green with `--accept-judge`.* **Met, pending the acceptance run**
   (EXECUTED: exit 0, `lost 0 · absent 0`, judge changed in the two named files).
3. *A dry run of the release workflow passes every job.* **Not shown.** Nothing is pushed.

## Findings, most severe first

1. **Two load-bearing parts of Decision 3 have no check: the stop itself and the
   `BaseException` catch. Seven mutations survive in all** (`runner.py:418, 457, 314, 341, 386`;
   `tests/unit/test_runner_calls.py`). Medium.
   - **The failure (EXECUTED, table above).** Change `except BaseException` to
     `except Exception` in `_shared`, and every test stays green. My stress then shows a host's
     `CancelledError` raised by another thread's `run` (11 of 960). That is the defect this
     specification exists to close.
   - Remove the stop, and every test stays green. The guest then runs on after a trap or an
     exit in `host_alloc`.
   - Also unguarded:
     - waits that ignore the Ctrl-C flag (a no-deadline sleep then ignores Ctrl-C until it ends);
     - `fuel_used` for a stopped call (no test goes through `_instance` with a stop and fuel);
     - a stack that is never popped (a `_Call` per call, and its host, kept for the life of the
       thread).
   - **Why the tests miss them.** In one thread, a `BaseException` that escapes `_shared` still
     comes back to the same caller through `LAST_EXCEPTION`. And `_drive` reports the recorded
     cause whether or not the guest was stopped.
   - **Fixes (all count; none measure time):**
     - In `test_a_hosts_base_exception_comes_back_to_its_own_call`, keep the store and the
       instance, then read the door's answer at offset 64 after `pytest.raises`. It must be −2;
       the mutant leaves 0. Decision 6 already promises this. Or add a host `CancelledError`
       kind, with a token, to the concurrency check.
     - Give the WAT guest a store after `call $empty`, and assert it is absent. The guest must
       not run past the stop.
     - Assert `runner._stack() == []` after `drive`.
     - A unit test through `run` with a WAT artifact set (as `probes/stops.py` does) that
       asserts `fuel_used is None` for an exit in `host_alloc` under fuel.
     - In the v1.4 Ctrl-C child, make the guest's final sleep `10**6` s. A regression in the
       wait's flag check then hits the 120 s fail-safe instead of passing.

2. **Ctrl-C still aborts the process under an embedder's handler that raises, and that includes
   `asyncio.run`** (`runner.py:548-551`; README "concurrent calls" bullet). Medium.
   - **The failure (EXECUTED, `ctrlc_1.txt`, `ctrlc_2.txt`).**
     - An embedder handler that raises `KeyboardInterrupt` gave SIGABRT (−6).
     - A plain script that calls `run` from inside `asyncio.run(main())`, and gets Ctrl-C twice
       (once before a guest wait, once after), also gave −6. asyncio installs its own handler,
       and the second time that handler raises inside wasmtime-py's trampoline.
   - The runner rightly leaves such handlers alone. But the README says only "an embedder's own
     handler is left alone". A reader would take Ctrl-C to be safe now.
   - **Fix.** Under "Not protected", say that Ctrl-C under a handler that raises (including
     asyncio's on a second Ctrl-C) can abort the process while a guest runs on the main thread.
     Say that a call made on a worker thread (`asyncio.to_thread`, a thread pool) is not
     affected. The drafted upstream issue already names the cause: the trampoline's first line
     sits outside its `try`.

3. **Other wasmtime-py code in the same process can still reach a runner call**
   (spec 011 Decision 2, "other wasmtime-py code in the process cannot race the runner"; README
   "concurrent calls in one process share nothing … never through wasmtime-py's shared callback
   tables"). Low–medium.
   - **The failure (EXECUTED, `neighbours.txt`).** Six threads made runner calls (door, and a
     deadline trap) beside six threads of plain wasmtime-py, for 20 s.
     - The plain code used one linker whose host function raises `ValueError`. Then 69 runner
       calls raised the neighbour's `ValueError` from `run`. A trapping runner call reads
       `LAST_EXCEPTION` in `enter_wasm` (`_func.py:231-250`).
     - The control, with the neighbours idle, gave 0.
     - The plain code calling `define_func` per call (so corrupting the slab) gave no wrong
       runner result in 20 s.
   - **INFERRED from `_slab.py`.** The runner's four `FUNCTIONS` entries live in the same slab
     the neighbours corrupt. A free list left pointing at a live slot can hand a runner slot to a
     neighbour.
   - So 006's promise and "share nothing" hold among runner calls, not against other wasmtime-py
     users in the process.
   - **Fix.**
     - Correct the sentence in Decision 2, and qualify the README to calls made through `run`.
     - Optionally, `_drive` could treat any non-wasmtime exception out of `instantiate`,
       `_initialize` or `run` as foreign, since the runner's own host functions never raise, and
       report it as a trap rather than raise it.

4. **The README's Ctrl-C sentence overstates when a call ends** (README "concurrent calls"
   bullet; spec Decision 3). Low.
   - "Ctrl-C ends the call at the guest's next host call, or at its deadline if it never makes
     one." But a "host call" here is only the door or a wait (`poll_oneoff`). Writes, reads and
     other WASI calls never run Python.
   - EXECUTED (`ctrlc_print_loop.txt`): `while True: print(...)` with `deadline_s=None` ignored
     SIGINT until killed at 30 s, with the change and with the committed runner alike. So it is
     not a regression. With no deadline there is no "at its deadline" either.
   - **Fix.** Say "at the guest's next wait or door call, or at its deadline; with
     `deadline_s=None`, a guest that never waits or calls the door runs on".

5. **Restoring the handler overwrites one installed during the call** (`runner.py:559`). Low.
   - EXECUTED (`ctrlc_2.txt`, `host_swaps_handler`): a host function on the main thread installed
     its own SIGINT handler. After `run`, the handler was `default_int_handler`.
   - **Fix.** Restore the default only if the handler is still `_note_ctrl_c`.

6. **Smaller points.** Info.
   - When `run` raises a recorded cause, it skips its own pop of the two output keys
     (`runner.py:337-346`, READ). wasmtime's free still removes them: EXECUTED
     (`outputs_on_raise.txt`), 0 keys right after a raising call. But the buffers live until
     that free. Popping in a `finally` would make the raise path match.
   - `_Call.stop` imports `_ffi` before it records the cause. The import cannot fail once
     wasmtime is loaded (INFERRED), but recording first costs nothing.
   - In `_shared`'s `except`, `call` may be the top entry even when the exception came from the
     context check itself. Then the cause would be recorded on that entry, not the caller's
     store. This is unreachable in practice (INFERRED).
   - The binding test pins `argtypes[0]` and `[2]`, not the callback types `[1]` and `[3]`.
     ctypes caches `CFUNCTYPE` classes by signature, so a changed signature would make every
     call raise `TypeError` loudly (INFERRED). Pinning
     `argtypes[1] is type(runner._output_write)` would say so directly.

## Constitution checks

- **§4.1, zero upstream patches.** Holds. No source tree is touched, and wasmtime-py is neither
  modified nor monkeypatched at run time.
  - The runner calls three private names: `wasmtime._ffi`/`_bindings` (the two output setters
    and `wasmtime_context_set_epoch_deadline`), and the private `_context()` of `Store` and
    `Caller`.
  - Decision 2 specifies this, gives the reason (the public `stdout_custom` allocates in the
    unlocked slab), pins the bindings with a unit check, and relies on `wasmtime>=49,<50` in
    `pyproject.toml` (READ).
  - I find it acceptable as specified. Calling a binding the dependency ships is not a patch.
  - `_context()` is not pinned by the binding test. If it vanished, every door call would record
    an `AttributeError` and `run` would raise it, so a break is loud (INFERRED).
- **§4.4, two imports.** Unchanged: WASI preview1, `poll_oneoff` (shadowed, as in 010) and
  `host::call`.
- **§4.5, embedder-neutral.** Holds.
- **§4.9, tests count.** Holds. The 120 s `timeout=`s are fail-safes. The output-table wait
  counts rounds. The 0.5 s in the Ctrl-C child is a trigger, not a measurement.
- **§4.10, evidence.** The landing notes' numbers reproduce (EXECUTED above). Two claims
  overstate: finding 3 (Decision 2's sentence) and finding 4 (the README).
- **§4.13, tooling.** No new dependency (`ctypes`, `itertools`, `contextlib` are stdlib).
- **§7, never-do list.** Nothing tripped. The judge changed in two files, and acceptance needs
  `--accept-judge`.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. **Finding 1 — fixed.** Each surviving mutation named in the finding now fails a test (EXECUTED
   by the author, each restored by `cmp`).
   - **No stop:** 6 tests fail. The WAT guest stores a 1 at 68 after its next function entry,
     and the tests require 0.
   - **`except Exception` in `_shared`:** 3 tests fail.
     `test_a_hosts_base_exception_comes_back_to_its_own_call` reads the door's own −2 at 64
     after the raise. An exception through the slot unwinds the guest before it stores the
     answer. The test keeps the instance through a wrapping linker.
   - **`fuel_used` counted for a stopped call:** fails `test_a_stopped_call_reports_no_fuel`.
     `_fuel_used` is now a function.
   - **Stack never popped:** 8 tests fail. `drive` asserts `runner._stack() == []`.
   - **Waits ignore the Ctrl-C flag:** the v1.4 Ctrl-C check is parametrized `computes` and
     `waits`, and the guest's sleep is `10**6` s. The `waits` case fails through its 120 s
     fail-safe (120.17 s).
   - The per-key compile lock and the `RLock` stay unchecked: the first needs timing to see, and
     the second guards an INFERRED deadlock. The landing notes say so.
2. **Finding 2 — answered in writing.** The README's "Not protected" list now names Ctrl-C under
   an embedder's handler that raises, asyncio's on a second Ctrl-C included, and says to call
   `run` on a worker thread there. Decision 3 says the same. The runner still leaves such
   handlers alone.
3. **Finding 3 — answered in writing.** Decision 2 and the README now say the isolation holds
   among calls made through `run`. Other wasmtime-py code in the process can still reach a
   trapping call through `LAST_EXCEPTION`, or corrupt the shared slab. The optional "treat
   foreign exceptions as traps" was not taken: it would also hide the runner's own bugs.
4. **Finding 4 — fixed.** The README now says "at the guest's next wait or door call, or during
   a wait, or else at its deadline". The "Not protected" list names a guest that never waits or
   calls the door under `deadline_s=None`.
5. **Finding 5 — fixed.** The default handler is restored only if the handler is still the
   runner's own.
6. **Finding 6 — fixed.**
   - The output keys are popped in a `finally`, so the raise path frees them too.
   - `_Call.stop` records the cause before it imports.
   - The binding test pins `argtypes[1]` and `[3]` to the runner's own callback types.
   - The unreachable context-check path is left as it is.

## Reviewer's confirmation, 2026-10-17

I checked the uncommitted fixes in the working tree: the runner, both test files, the README and
spec 011. Logs are in the same scratch folder: `pytest-full2.txt`, `mutate2.py`,
`mutations2.txt`, `logs2/` and `probes/confirm_*.txt`.

**Re-ran (EXECUTED).**
- `uv run pytest` → `129/132 pass` (unit suite 212/212), `341 passed`, ratchet `lost 0 · absent
  0 · gained 4`, judge changed in the same two files, exit 0.
- `ruff check` and `ruff format --check` are clean.
- 13 mutations of the fixed runner, each restored. Afterwards `git diff` and
  `git status --porcelain` were byte-identical to copies taken first, and `runner.py` was
  `cmp`-equal.

**Each finding.**
1. **Finding 1 — confirmed.** Every mutation the finding named now fails a test:
   - no stop → 6 fail;
   - `except Exception` in `_shared` → the 3 `BaseException` cases fail;
   - waits ignoring the flag → `test_ctrl_c_while_the_guest_runs_ends_the_call[waits]` fails
     through its fail-safe (157 s run);
   - `fuel_used` counted when stopped → `test_a_stopped_call_reports_no_fuel` fails;
   - stack not popped → 8 fail.

   The context check, never swapping the handler, and removing both key removals are still
   caught.

   Still surviving, as the author states:
   - later host calls not answered at once;
   - the `RLock`;
   - the per-key compile lock.

   One correction to the stated reason for the compile lock. It does not need timing to see: a
   cold start of 12 threads counted `stats()["compiled"]` as 2 with the lock and 12 without
   (EXECUTED, `compile_once.txt`). A check is optional, since the count without the lock is a
   race. But the spec's "only timing could show" should say "only a racy count could show".
   This does not block.

2. **Finding 2 — confirmed.** The README's "Not protected" list and Decision 3 now name the
   abort under a raising handler, asyncio's included, and point to a worker thread. This
   matches what I executed.

3. **Finding 3 — confirmed.** The README now scopes the isolation to calls made through `run`.
   It names other wasmtime-py code and the shared exception slot, and Decision 2 says the same.
   Declining the "foreign exception as trap" option is a reasonable call: it would hide the
   runner's own bugs.

4. **Finding 4 — confirmed.** The README now says "next wait or door call, or during a wait, or
   else at its deadline". The "Not protected" list names a guest that never waits or calls the
   door under `deadline_s=None`.

5. **Finding 5 — confirmed.** EXECUTED (`confirm_ctrlc.txt`): a host that installs its own
   handler during the call keeps it afterwards.
   - The default handler's restore and the other Ctrl-C cases are unchanged: compute then
     sleep, sleep, nested, an exception inside `run`, and a host `KeyboardInterrupt`.
   - The mutation that restores unconditionally survives the judge. The fix stands on my probe
     alone. A one-line unit test would pin it; this is optional.

6. **Finding 6 — confirmed.**
   - The output keys are popped in a `finally`.
   - `stop` records the cause before the import.
   - The binding test pins `argtypes[1]` and `[3]` by identity.

**Behaviour unchanged (EXECUTED).**
- 16 × 60 stress: 0 wrong, 0 raised, `FUNCTIONS` 4, `CUSTOM_OUTPUTS` 0, `_outputs` empty.
- The stop table reproduces, including when the stop's own call fails (`confirm_stops.txt`).

**Verdict (confirmation).** It lands once the acceptance run (`--accept-judge`) is recorded.
Criterion 3, a dry run of the release workflow, is still to be shown.

## Verdict

Does not land yet. The code holds: 0 wrong of 8,320 concurrent calls, no crossing, no leak and
no abort under the default handler. But the stop and the `BaseException` catch, the two parts
that make it hold, can be removed with the judge still green (1). Add those checks and correct
the README and spec text (2–5); then it lands.

One line: concurrent calls now get their own results and their own exceptions, but the judge
does not yet notice if the stop or the `BaseException` catch is taken away.
