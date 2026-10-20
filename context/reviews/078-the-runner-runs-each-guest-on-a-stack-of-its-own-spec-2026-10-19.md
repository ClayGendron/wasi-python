# Review of 078 — The runner runs each guest on a stack of its own (the specification, before build)

- **Date:** 2026-10-19
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I wrote none of the spec, the
  memo or its probes. I read `AGENTS.md`; question 102 (`git show 3561e55^:context/questions-for-the-owner.md`)
  and its answer in `context/decisions.md`; specs 071, 053 and 055 and 071's two reviews, for the
  shape; the README's *Time and threads* and *Deep recursion*; and the code the spec changes:
  `src/wasi_python/runner.py` (`_call`, `_instance`, `_drive`, `_Call`, `_calls`, `_shared`,
  `_epoch_answer`, `_watch`, `_door`, `_ctrl_c_watched`, `_deferred_ctrl_c`, `_shutdown`,
  `_collected`, `_start_closer`, `_sessions_at_exit`, `_register_exit_hook`, `run_async`) and
  `src/wasi_python/mounts.py` (`_Files.__call__`, `_ask`, `_gate`, `_invoke`, `_made`, `_list`,
  `_listed`, `_close`). Also wasmtime 49.0.3's source (`context/prior_art/wasmtime-v49`,
  `crates/wasmtime/src/config.rs:857–881, 2632–2633`, `crates/c-api/include/wasmtime/async.h:68`,
  `crates/c-api/src/async.rs:20`); CPython's 3.14 branch (`context/prior_art/cpython` at
  `7c04882`: `Python/ceval.c:444–577`, `Python/thread_nt.h:195–215`, `Python/thread_pthread.h:835–873`,
  `Modules/_threadmodule.c:2141–2170`, `Lib/platform.py:160–220`); wasmtime-py 49.0.0's
  `_bindings.py`, `_managed.py` and `_store.py`; and spec 065's branch at `5294520`
  (`tests/upstream/python.toml`, `tests/known_gaps.toml`). Each claim is labelled EXECUTED, READ
  or INFERRED.
- **Reviewed:** `spec/078-the-runner-runs-each-guest-on-a-stack-of-its-own` at `b002c8b`, on main
  `3561e55`: `git diff 3561e55..b002c8b`, 48 files, every one under `context/` (READ). Main has
  since moved (0.1.0a7 released, `a6dfc17`); spec 065's branch has moved to `5294520` and now
  carries nine trap entries, not eight (F8).
- **Ran (EXECUTED; darwin arm64 with the project's CPython 3.14.2 and wasmtime-py 49.0.0, and
  linux/amd64 in the repository's `wp040-amd64` image under emulation with uv's CPython 3.14.2;
  a fresh `cp -Rp` copy of `build/sets/s-c50ca51fae5eb55b-c9dcb5b8`).** Nothing was written in
  any git tree. The run folders, the set copy, the downloaded wheel and the scratch clone are
  deleted; the probes and their outputs sit in `probes/` beside this file:
  - `fuel_epoch.py`, `fuel_pandas.py` → `fuel_epoch.out`: does the epoch callback that Decision 5
    adds to every main-thread call move fuel? Main's runner, unchanged; each program plain, with
    `cancel=threading.Event()` (the callback every 5 ticks and the ticker), and with a deadline.
  - `close_while_running.py` → `close_while_running.out`: wasmtime-py's `Store.close()` on one
    thread while another thread runs wasm in that store (F1).
  - `home_model.py` → `home_model.out`: a model of the spec's `_Home` as its Design section
    states it, with an interrupt landing just after `inbox.get()` (F2). A model, not runner code.
  - `cpy_tee.py` → `cpy_tee.out`: spec 065's ninth trap entry (`test_itertools`
    `TestPurePythonRoughEquivalents.test_tee_recipe`) at 512 KiB and 8 MiB on linux/amd64,
    through the 078 worktree's judge driver, read only (F8).
  - `win_symbol.out`: wasmtime-py 49.0.0's `win_amd64` wheel, downloaded from the URL in
    `uv.lock` into its own folder, searched for the setter's name (F5).
  - `rules.txt`: `uv run pytest tests/checks/test_rules.py -n 3` in a scratch clone of `b002c8b`.

## What holds

- **The mechanism is right, and the research behind it is careful (READ, EXECUTED).** wasmtime
  refuses `max_wasm_stack > async_stack_size` (`config.rs:2632–2633` at 49.0.3). The C setter
  takes `size_t` (`async.h:68`; `async.rs:20`, `usize`), so `c_size_t` is the right type. The
  async size is used only by `call_async` fibers (`config.rs:862–877`), which the runner never
  makes. The research shows the engine aborting at every size above 2 MiB without the setter
  (`p1_config.out`). A thread of W plus 48 KiB was enough on five host setups (`p5-*.log`). On
  musl, CPython 3.14 must be told the thread's stack, and once told it survives (`musl-guess.log`).
- **The musl condition mirrors CPython's own (READ).** CPython guesses its stack on Linux unless
  built for glibc or Android (`ceval.c:465–467`). `platform.libc_ver()` asks
  `os.confstr('CS_GNU_LIBC_VERSION')` first (`platform.py:181–186`), so the spec's test reads
  the C library actually loaded. `ctypes.pythonapi` is a `PyDLL`, so the `ValueError` that
  `PyUnstable_ThreadState_SetStackProtection` sets for a too-small size is raised (`ceval.c:559–563`).
- **Fuel does not move (EXECUTED, two ways).** The research measured the judge's driver at
  512 KiB and 8 MiB, on the caller's thread and on a fresh one (`fuel078.out`). I measured the
  other half, the epoch callback Decision 5 adds to main-thread calls. Through main's runner,
  `hello` (15,762,954), a 30-million-step loop (85,195,283,416) and numpy (793,590,169) used the
  same fuel plain, with the callback and with a deadline. pandas varies from run to run in the
  runner whatever the mode (seven runs, ±150,000), because the runner, unlike the judge's driver,
  does not seed the guest's randomness. So the runner's own fuel is not the judge's measure, and
  the judge's measure does not move.
- **Spec 071's signal guard still answers correctly off the main thread (READ).**
  `_trap_handlers_ready` reads process-wide dispositions with `sigaction` and the loader's
  `dladdr`. Nothing in it depends on the calling thread. It moves with the wasm, and stays the
  last step before guest code.
- **The deadlock cases the brief listed mostly hold (READ, INFERRED from the Design).**
  - A host function that calls `run()` again runs on the home thread. The nested call makes its
    own guest thread, and the home serves both inboxes. No runner lock is held while serving.
    Today such a nested call starts wasm deep in the caller's stack; under 078 it gets a fresh
    9 MiB thread, which is better.
  - A provider shared by two sessions is called on each call's own home. Nothing in the runner is
    shared between them.
  - `run_async` with a full executor: the home is the worker, serving itself, so a hand-off needs
    no second worker.
  - Cancel and a deadline during a hand-off: the provider or door host holds the guest, as today.
    The README's "your provider's own time is outside the deadline" still holds.
  - `close()` from a host function inside its own turn still returns at once, because
    `turn_thread` stays the claiming thread, where host functions run.
  - Async door hosts are refused (`runner.py:1181`), and gates and tools already run on threads
    of their own.

  The cases that break are an interrupt landing in the home's own bookkeeping (F1, F2) and the
  listing iterator (F4).
- **The checks are mostly written first and count outcomes.** Criteria 1 to 4 fail on main
  because the hook, the 8 MiB stack, the refusal and the musl call do not exist yet. Criterion 5
  fails today with SIGILL, criterion 7 hangs, criterion 8 runs to its deadline (all three EXECUTED
  by the research), and criteria 9 and 10 trap at 512 KiB. None asserts a time. The 120 s child
  limit only turns a hang into a failed row, as in spec 071. Two gaps: F11 (the 0.5 s timers) and
  F1/F2 (they need checks of their own).
- **Rules (EXECUTED).** `test_rules.py`: 42 passed, 2 skipped.

## Findings, most severe first

### F1 (critical). The spec lets `run` return while the guest thread is still running, and `_instance` then closes the store under it: the host dies

- **EXECUTED.** Closing a wasmtime-py store on one thread while another thread runs wasm in it
  killed the process with SIGSEGV (exit −11) three times out of three
  (`close_while_running.out`). `Store.close()` is `wasmtime_store_delete`, with no guard against
  a running store (READ, `_managed.py:29–44`, `_store.py:30–31`).
- **Where the spec allows it (READ).** Decision 5's last bullet: "If the home stops serving
  anyway … the guest thread then ends at its next check, or at its deadline. No process abort and
  no host hang follow". The README's new *Not protected* line: "after which `run` may return
  before the guest's thread has stopped". `_on_guest_thread` in the Design runs `home.serve();
  join` with no `finally`. Once the home leaves before the join, `_instance`'s `finally` runs on
  a store that is still executing (READ, `runner.py:2659–2676`). That `finally` calls
  `store.close()`, pops the output keys, runs `table.release()` and removes the private root.
- **How the home can leave early.** An embedder's raising SIGINT handler can fire between
  `start()` and `serve()`, inside `serve()`'s own `finally`, or during the join. The research
  showed such an exception landing outside a loop's `try` (`p6-p3-glibc-arm64.out`).
  `PyThreadState_SetAsyncExc` can do the same on a home that is not the main thread.
- **Sessions have the same hole.** `busy` is cleared in the turn's `finally`. The reaper or a
  closer could then start the ending on a second guest thread in the same store while the first
  still runs (INFERRED).
- **Asked.**
  - Teardown of the store, the outputs, the table and the private root happens only after the
    guest thread has ended. Join in a `finally` that loops through exceptions, keeping the first
    one as the call's stop and stopping the guest through the epoch callback.
  - If the home is forced out anyway, hand the teardown to the guest thread: a flag under a lock
    that the guest body checks at its end. Then "`run` returned early" stays a Python limit and
    never becomes a use-after-free.
  - A session's `busy` is released only when the guest thread ends.
  - Add a check: an exception injected into the home after the guest thread starts (a stand-in
    `serve` that raises once). The child exits 0, and the store is closed only after the guest
    thread has ended (an `_on_entry`-style hook records the order).
  - Remove "No process abort … follow", or make it true.

### F2 (high). A hand-off taken but never answered hangs the call for good

- **INFERRED from the Design; EXECUTED on a model of it (`home_model.out`).** As the Design
  states it, `serve()` catches an exception raised into its loop into `raised` and goes on
  looping. Meanwhile the guest side waits on its box "stopping if `serving` was cleared".
- **How it hangs.** An interrupt that lands after `inbox.get()` returns, but before the item's
  own `try`, loses the hand-off. So does one that lands after the host function returns, but
  before the box is released. `serving` stays true, so the guest waits for ever. The home waits
  for DONE for ever. The epoch callback cannot help, because the guest is inside a host function,
  not in wasm. The model, with the interrupt injected at exactly that point: the guest was "still
  waiting after 60 slices" (my cap), with `home.raised` set to `KeyboardInterrupt`.
- **Asked.**
  - `serve()` keeps the item in flight. Its `except` puts the exception in that item's box and
    releases it.
  - The guest's wait also stops when `home.raised` is set, not only when `serving` is cleared.
  - Add a check with a stand-in inbox whose `get` raises `KeyboardInterrupt` once after
    dequeuing. `run` raises `KeyboardInterrupt`, and the next call works.

### F3 (high). The judge's changes are incomplete: accepted checks break, and the spec does not list them (rule 4)

READ. Under the design, host functions and providers run on the home thread. There `runner._stack()`
is empty, `_on_export` reports the guest thread's ident, and the shared functions read
`call.ctrl_c` and `call.home`. These accepted checks then fail or change meaning, and none is in
"The judge's changes":

- **`tests/checks/test_v1_4_embedding.py`.** Line 973 (`door-deadline`) and line 3492 (a door
  host) run `runner._stack()[-1].stop_at = …`. Line 1817 (`past_deadline`, in a provider) is
  commented "this provider runs on the guest's thread, under its call". On the home thread each
  raises `IndexError`, which becomes `HOST_FAULT` or a provider fault.
- **`tests/checks/test_v1_4_sessions.py:1230`,
  `test_a_turn_that_returns_after_close_runs_the_shutdown`.** It asserts
  `shutdowns == [threading.get_ident()]` through `_on_export("shutdown", threading.get_ident())`
  (`runner.py:4225`). That call moves onto the guest thread with the export.
- **Unit tests whose fake calls lack `ctrl_c` and `home`, and which patch `_ctrl_c_watched`.**
  `tests/unit/test_runner_async.py:73` (`test_a_deferred_ctrl_c_becomes_a_stop`),
  `test_runner_cancel.py:111`, `test_runner_tools.py:353`, `test_async_tools.py:346` and
  `test_runner_mounts.py:171–181`. With `call.ctrl_c and …` the fake call raises
  `AttributeError`, which is recorded as the stop instead of `KeyboardInterrupt`.
- **`tests/harness/files.py:677, 727`, `test_runner_calls.py:72` and `test_runner_mounts.py:253, 640`.**
  They build `runner._Call(…)` by position. They break if `home` becomes a required parameter.

Asked: choose, per check, between keeping the seam and restating the check, and list every
restatement with its reason. Keeping seams is cheaper and changes less of the judge:

- the home pushes the call on its own `_stack()` while it serves, so `runner._stack()[-1]`
  still finds the call in a host function;
- `_on_export` is told the home's ident, the thread spec 055 means;
- `_Call` gains `home=None` (meaning "call directly") and `ctrl_c` with defaults.

The unit tests of the Ctrl-C order still need restating to the new reading. They are judge
changes and are named.

### F4 (medium). Provider code still runs on the guest thread: the listing's iterator, and the method lookup

READ. Decision 4 hands home only `_invoke`'s call. But `_Files._list` (`mounts.py:980–1033`)
runs `iter(answer)`, every `next(iterator)` and `_close(iterator)` on the guest thread. For a
generator `list`, which spec 061 supports explicitly ("a generator method's body included",
`mounts.py:1004–1005`), that is the provider's own body. Such a provider that uses a thread-bound
`sqlite3` connection or a `threading.local` breaks, which is exactly what criterion 6 promises
will not happen. The Design's line also evaluates `getattr(mount.provider, method)` on the guest
thread, so a provider's `__getattr__` or a property runs there.

Asked:
- hand home the whole gathering of a listing, or `iter`, `next` and `close` each;
- hand home the lookup and the call as one step;
- add a generator `list` that uses the caller's `sqlite3` connection to criterion 6.

Two smaller leaks are worth a README line rather than code. `bytes(response)` of a `bytes`
subclass with `__bytes__` runs on the guest thread (`_door`). So does `_described(e)`, the
`str()` of a provider's exception.

### F5 (medium). The ctypes call into wasmtime: correct as measured, but the spec should make it impossible to mis-call and say what happens without it

- **What holds.** The signature is `void (wasm_config_t*, size_t)` throughout 49.x (READ, 49.0.3
  header). `pyproject.toml` pins `wasmtime>=49,<50`. The symbol is in the darwin wheel (the
  research), in Linux glibc and musl (the research ran there) and in the `win_amd64` wheel's
  `_wasmtime.dll` (EXECUTED, `win_symbol.out`). There is no safer route at 8 MiB:
  - wasmtime-py has no setter (`p1_config.out`);
  - the async size is unused here;
  - staying at or below 2 MiB avoids the call, but the 128 KiB window needs about 3.2 MiB of
    native stack on arm64 and 4.2 MiB on x86_64 before the data shapes raise (INFERRED from the
    memo's 25 native bytes per linear byte), so 2 MiB would not deliver the owner's (a).

  The runner already calls `wasmtime._ffi` directly (`_watch`, `_epoch_now`, `_send_outputs`).
- **Asked.**
  - Resolve the symbol once into a private prototype, `CFUNCTYPE(None, POINTER(_bindings.wasm_config_t), c_size_t)(("wasmtime_config_async_stack_size_set", _ffi.dll))`.
    Never set `argtypes` on the shared `_ffi.dll` attribute, which other code in the process may
    also use.
  - Do the same for `ctypes.pythonapi.PyThreadState_Get` and
    `PyUnstable_ThreadState_SetStackProtection`, with `PYFUNCTYPE`. The research's probe sets
    `restype` on the shared attribute (`stackrun.py`, `protect`).
  - If the symbol is missing, raise `RuntimeError` naming wasmtime-py's version before
    `max_wasm_stack` is set and before `Engine(cfg)`. Never build an engine at 8 MiB without the
    async size, which aborts the process.
  - Add that case to criterion 2.
  - Draft the upstream wasmtime-py change, a `Config.async_stack_size` setter, under
    `context/upstream/`, and prefer the setter when present. This adaptation is temporary in the
    same spirit as §4.1.

### F6 (medium). `threading.stack_size` is shared, and the runner's restore can undo another library's setting

- **INFERRED; READ for the mechanism.** The runner sets and restores under its own lock, but
  other code is not under it. Suppose another thread sets the size to B inside the runner's
  window. The runner's thread is then started with B, and refused if B is small: a spurious
  `RuntimeError`. Then the runner restores the value it found and silently erases B. If that
  library raised the size for its own deep recursion, its later threads get less stack than it
  asked for, and can crash.
- **No read-only getter.** `threading.stack_size()` with no argument sets 0
  (`_threadmodule.c:2144–2159`), so the obvious "read it to check" is itself a bug.
- **Asked.**
  - Restore with `current = threading.stack_size(old)`. If `current != _THREAD_STACK`, someone
    changed it inside the window, so put theirs back with `threading.stack_size(current)`.
  - On a refusal caused by a small thread, retry once.
  - Tell the builder never to call `threading.stack_size()` without an argument.
  - Low: `os.fork()` inside the window leaves the child at 9 MiB. `_after_fork_in_child` can
    restore a saved value.

### F7 (medium). Windows is designed from reading alone, and the lane never runs it

- **What is unmeasured (READ, INFERRED).** Every Windows claim:
  - the bound read with `GetCurrentThreadStackLimits`;
  - the guard pages and stack guarantee below it (CPython subtracts the guarantee,
    `ceval.c:446–452`);
  - wasmtime's vectored handler running on the faulting thread within the host room;
  - the 9 MiB that CPython commits rather than reserves (`thread_nt.h:204`: `_beginthreadex`
    with flags 0);
  - criterion 9's depth margins on Windows x64.
- **Why it matters.** AGENTS.md 6b says Windows runs only in the release's dry run, and
  0.1.0a4's tag failed there.
- **Asked.**
  - Compute Windows' usable size as `high − low − guarantee − one page`. Being conservative
    costs nothing against 512 KiB of slack.
  - The builder dispatches the release workflow on the branch commit before writing "built", or
    the lane runs a dry run before landing this one. Criteria 3, 5, 7, 8 and 9 on Windows are the
    gate, not only the tag's.

### F8 (medium). Spec 065 now has nine trap entries; the ninth passes at 8 MiB on x86_64

- **READ.** 065's branch at `5294520` added `c-stack-itertools-tee`
  (`test_itertools.TestPurePythonRoughEquivalents.test_tee_recipe`, Linux x86-64 only, "closing
  with spec 078"). Decision 11, Decision 13, criterion 13, the CHANGELOG and the `--accept-judge`
  reason all say eight. The roadmap still says six.
- **EXECUTED (`cpy_tee.out`, linux/amd64).** At 512 KiB the test traps ("call stack exhausted",
  2,488,912,867 fuel). At 8 MiB it passes ("Result: SUCCESS", 2,637,598,792).
- **Asked.** Make it nine everywhere, with this measure. The roadmap's "six" is a `context/` fix.

### F9 (low). The host room holds more than the runner's frames

INFERRED. Decision 2 says the 1 MiB holds "only the runner's own frames". Other code also runs
on the guest thread inside any callback, at the deepest point:
- the cyclic collector's finalizers and weakref callbacks, the embedder's included;
- audit hooks (ctypes raises audit events);
- `sys.settrace` and `sys.setprofile` functions set for all threads.

On CPython 3.14 and later, the interpreter's own guard turns Python recursion there into
`RecursionError` (real bounds, or told bounds on musl). On 3.11 to 3.13 C recursion is counted,
not measured. So a finalizer doing deep C work, such as `repr` of deep data, has 1 MiB where today
it had the caller's thread less 512 KiB.

Asked: one README line. Perhaps 2 MiB of room, which is only reserved, except committed on
Windows.

### F10 (low). An exception on a home that is not the main thread is noted but not acted on

INFERRED. `PyThreadState_SetAsyncExc`, as used by `pytest-timeout`'s thread method and by some
notebook kernels, can land in `serve()` on a worker home. It is recorded in `raised`. But only
main-thread calls, or calls with a `cancel` or deadline, get the epoch callback, so the guest
runs on until it ends.

Asked: give every call the epoch callback. It costs one callback per 50 ms of guest time and no
fuel (EXECUTED above).

### F11 (low). Criteria 7 and 8 start Ctrl-C from a 0.5 s timer

READ. The verdict does not depend on the delay: an early interrupt is seen at the door's return.
But the rule prefers counts. Asked: trigger the interrupt after the ticker has advanced N ticks,
as `test_v1_4_embedding.py`'s `ticks(n)` helper does.

### F12 (low). Tools see a copy of the context taken at the guest thread's start

INFERRED. A provider that sets a `ContextVar` on the home during a call sets it in the home's
live context. A tool the frame host starts later copies the guest thread's context, which was
copied at thread start, so the tool does not see the value. Today it would. Asked: say so in the
README, or copy the home's context when a tool starts.

### F13 (low). Unknown platforms are refused outright

READ. A platform where the bounds cannot be read is refused on every call. wasmtime-py 49
publishes Android wheels, and FreeBSD has no branch. Today those run. Asked: one README and
CHANGELOG line.

### F14 (low). The check reads the thread's size, not its room at the wasm entry

INFERRED. glibc carves static TLS and its thread descriptor out of the requested stack, inside
the range that `pthread_getattr_np` reports. The frames above the entry also count. The
512 KiB of slack between the refusal line and W plus 48 KiB absorbs ordinary TLS. Asked: say in
the code and the spec what the check measures.

### Notes (no change asked)

- `_stack_size_lock` is held across `Thread.start()`, which waits for the new thread to start.
  No callback runs under it, so it cannot deadlock (INFERRED).
- Starting threads during `atexit` already works: spec 055's closers do it
  (`_sessions_at_exit`), so a session ending at exit can start its guest thread (READ).
- glibc caches freed thread stacks, but `advise_stack_range` returns the touched pages at thread
  exit, so "returns its touched stack" holds closely enough (INFERRED).

## The owner's three points

- **The window knob.** Reserve it as a follow-up, placed after 086 (the toolchain move changes
  Cranelift's frames, which the knob's x86_64 numbers depend on). The measure is strong (every
  depth through Python code roughly doubles at 256 KiB on arm64). It needs the guest to read a
  contract and a recipe change, which do not belong in a parallel-safe runner change.
- **The hand-off's price.** Accept it. About a quarter more host time per provider or door call
  on darwin, no fuel, and it keeps the frozen API's promise about where host functions run. Have
  the builder state a quiet Linux number, as the spec asks. Fix F4 first: the promise must hold
  for generator listings too.
- **CPython 3.14.0 on musl.** Accept the refusal. The alternative, a smaller W for that one
  interpreter, makes the stack depend on the host for a superseded point release. Put it in the
  CHANGELOG's **Changed**, as the spec does.

## Constitution checks

- §4.1: no upstream patch. The wasmtime-py setter is an FFI adaptation; F5 asks for its upstream
  draft.
- §5.6 and §5.7: parallel-safe as claimed. No `scripts/`, `recipes/`, `SHA256SUMS` or workflow.
  The diff is `context/` only.
- Rule 4: the judge change must be complete (F3) and accepted with `--accept-judge`.
- Tests count operations: they do, except F11.

## Scoreboard

Pre-build, `context/`-only diff: `test_rules.py` passed (42, 2 skipped). The full judge belongs
to the build.

## Verdict

**Ready once:**

- F1 and F2 are designed in, each with a check:
  - the home never tears down a store whose guest thread runs;
  - a hand-off taken is always answered, and the guest's wait stops on `raised`;
- F3's checks are each kept by a seam or listed as a restatement with its reason;
- F4 hands the listing's iteration and the method lookup home, and criterion 6 covers a generator
  `list`;
- F5's guarded, private FFI and its missing-symbol refusal are specified;
- F8 makes it nine entries.

F6 and F7 should be written in; F7's Windows run may be taken by the builder and reported in the
landing notes. F9 to F14 may be written in or answered in the landing notes. The design itself
(a thread per entry, the 8 MiB stack, the stack check, the musl call, the home thread for
embedder code, polled Ctrl-C) is sound and well measured.

## One line

The thread, the stack and the musl call are right and measured. But the home thread can leave
while the guest still runs, which closes a live store (SIGSEGV, EXECUTED). An interrupted
hand-off can hang the call. Accepted checks that read `runner._stack()` or thread idents break
without being listed. And a generator `list` still runs on the guest thread. Fix those four, and
make it nine 065 entries, then build.

## Confirmation of 078's revision (addendum to the pre-build review)

- **Date:** 2026-10-19. **Reviewer:** the same fresh agent.
- **Reviewed:** `40c7d27` on `spec/078-the-runner-runs-each-guest-on-a-stack-of-its-own`, rebased
  onto main `a6dfc17`. I read the whole revised specification (Decisions 1 to 16, the Design,
  criteria 1 to 18, the judge's changes, the disposition) and
  `context/upstream/21-wasmtime-py-async-stack-size/facts.md`. I checked the binding in
  wasmtime-py 49.0.0's `_bindings.py:3729–3733` and the research's new `p1b_binding.out`.
  Nothing was run again: the revision changes text, and my earlier probes are the evidence it
  cites.

### F5's departure, judged

Accepted. It is better than what I asked for. Five reasons:

- **The binding is wasmtime-py's own.** `_bindings.py:3729–3733` declares
  `wasmtime_config_async_stack_size_set` with `restype None` and
  `argtypes [POINTER(wasm_config_t), c_size_t]` (READ). `_ffi` re-exports it with
  `from ._bindings import *`. The bindings are generated from the C headers of the same release,
  so the prototype matches the library by construction. That is safer than a hand-written
  prototype, which could drift from the library.
- **No shared attribute is touched.** The runner sets no `argtypes` or `restype` anywhere, which
  was the point of my ask.
- **It is pinned, and checked before anything dangerous.**
  - `pyproject.toml` pins `wasmtime>=49,<50`.
  - Every 49.x has the function with `size_t` (READ, 49.0.3's `async.h:68`).
  - If a later wasmtime-py renames or drops the binding, and has no `Config.async_stack_size`,
    `_engine` raises `RuntimeError` naming the version. It does so before `max_wasm_stack` is set
    and before `Engine` is made, so wasmtime's refusal, which aborts the process, is never
    reached. Criterion 2 covers this case with both routes removed.
  - If a later release changes the C signature, its regenerated binding changes with it, so the
    call is still made through a correct prototype.
- **The private module is no new kind of risk.** The runner already calls `_ffi` directly for
  `_epoch_now`, `_watch` and `_send_outputs`, under the same pin.
- **The property is preferred once wasmtime-py has it.** The upstream ask is written as a facts
  sheet, which the project's policy on Bytecode Alliance projects requires. It is posted only if
  the owner chooses.

Builder note: look up the binding with `getattr(_ffi, name, None)` and check it is callable, so
an `AttributeError` can never escape from somewhere other than the stated `RuntimeError`.

### F1 and F2, against my probes

- **F1 holds (READ, against `close_while_running.out`).**
  - `_on_guest_thread` joins in a `finally` loop that survives exceptions. Each exception becomes
    the call's stop through `home.stop`, so the epoch callback, now on every call (F10), ends the
    guest.
  - The teardown is registered with the home and run through `home.finish()`. It runs once,
    under the home's lock, and never while the guest runs. If the home was forced out, the guest
    thread runs it itself at its end.
  - A session's `busy` is held until the guest thread ends.

  So `store.close()` can no longer run under a live guest, which is the SIGSEGV case. Criterion 17
  injects an exception at three points: after the start, during the join, and in the loop's own
  `except`. A session row is included. It is seen failing first against the draft, with SIGSEGV.
- **F2 holds (READ, against `home_model.out`).**
  - `serve` keeps the item it has taken in a variable. Its `except` answers that item's box with
    the exception.
  - The guest's wait also ends when `home.raised` is set or when the home has stopped serving.

  In my model's scenario, the interrupt lands just after `get()` returns, and the item is now
  answered. A hand-off that `serve` never took is ended by `raised`. Criterion 18 covers both
  landing points.

### Still open

- **C1 (medium). A guest blocked in one of the runner's own waits does not see `home.raised`.**
  - **INFERRED from the Design; READ for today's behaviour.** Decision 5 keeps "the waits' checks,
    built on the home thread": the deadline, `cancel` and the Ctrl-C flag. `home.raised` is read
    only by the epoch callback, which runs only while wasm runs, and by a hand-off's wait.
  - **The failing case.** A guest sleeping in `poll_oneoff` (`time.sleep(10**6)`,
    `deadline_s=None`). An embedder's raising SIGINT handler, or a `PyThreadState_SetAsyncExc` on
    a worker home, lands in `serve`. `raised` is set, but the guest sleeps on to its timeout. The
    home's join loop waits with it: for this program, a hang.
  - **Why it is a regression.** Today the handler's exception is raised inside the
    `poll_oneoff` shadow's sleep on the main thread, and `_shared` turns it into the call's stop.
    The same gap applies to the tool protocol's bound, which waits for a tool on the guest thread.
  - **Fix (text only).**
    - Add `lambda: home.raised is not None` to the waits' checks and to the tool bound's stop
      reading.
    - Add a sleeping-guest row to criterion 8, and a waiting-for-a-tool row if cheap.
- **C2 (low). The window between `thread.start()` and the `try` that joins.** In the Design,
  `start()` runs inside the stack-size block. Then come `threading.stack_size(old)` and
  `_stack().append(call)`, and only then the `try`.
  - An exception landing in those few bytecodes leaves without the join loop. Memory stays safe,
    because `finish()` hands the teardown to the guest thread.
  - But nothing sets `raised`, so the guest is not stopped, and a hand-off it makes waits for
    ever. The guest thread then never ends, and its teardown never runs: a leaked thread and
    store, not a crash.
  - **Fix.** Either open the `try` before `start()`, or let `finish()` call `home.stop(...)` with
    a private stop when it marks the home abandoned. The second makes "abandoned" imply
    "stopped". The builder may take it and say so in the landing notes.
- **Already answered.** F3 to F14 are each answered as I asked, or better:
  - F3: four seams, the named checks run unchanged, and one comment is listed. The builder runs
    them first and lists any other check the build moves.
  - F4: every site where embedder code runs is handed home, and the builder must list any other.
    Criterion 6 covers all four shapes.
  - F6: the restore pattern, never a no-argument call, one retry, and the fork restored.
  - F7: the conservative Windows count. The lane runs the release workflow on all three systems
    before landing.
  - F8: nine entries, with `cpy_tee.out`.
  - F9: 2 MiB of host room in a 10 MiB thread, refused below 9 MiB.
  - F10: every call polled. No fuel moves (`fuel_epoch.out`).
  - F11: the interrupt is started on ticks.
  - F12: the tool context is copied on the home.
  - F13 and F14: stated in the spec, the README and the CHANGELOG.

  The roadmap's "six" stays the lane's `context/` fix.

## Verdict on the revision

**Confirmed once C1 is written into the specification:** the runner's own waits, and the tool
bound, also stop on `home.raised`, and criterion 8 gains a sleeping-guest row. It is a text change
the lane can check is there. C2 may be written in, or taken by the builder and reported in the
landing notes. F5's departure, using wasmtime-py's own declared binding and refusing before any
engine when it is missing, is accepted. F1 and F2 are closed by design and by checks seen failing
first.

## One line (confirmation)

All fourteen findings are answered, and F5's departure is sound. One gap is left: a guest asleep
in the runner's own wait must also wake on `home.raised`. Write that in, then build.
