# 078 — The runner runs each guest on a stack of its own

- **Status:** drafted 2026-10-19 on `spec/078-the-runner-runs-each-guest-on-a-stack-of-its-own`
  from main `3561e55`, with its research
  (`../research/2026-10-19-the-runners-own-stack.md`). It changes neither the guest's imports nor
  its exports, the artifact set nor the build recipe, so §5.6 asks no review before build; it
  changes where every guest runs and how Ctrl-C reaches it, so the author recommends one, the
  lane deciding. A different agent reviews the build.
- **Date:** 2026-10-19
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe**, not build-class (§5.7): it changes `src/wasi_python/runner.py`,
  `src/wasi_python/mounts.py` (one line: a provider is called on the home thread), `tests/`,
  `README.md` and `CHANGELOG.md`; no `scripts/`, `recipes/`, `downloads/SHA256SUMS` or workflow.
  The artifact set does not change and is not rebuilt. **No line of `tests/public_api.txt`
  changes**: no name, signature, field or default; `run`'s, `run_async`'s and `Session.run`'s
  docstrings gain `RuntimeError` reasons and say where a host function runs, so the README's
  generated reference changes in those entries. It is a **judge change** (the section "The
  judge's changes"): the lane accepts it with `--accept-judge`; no fuel moves (Decision 9).
- **Depends on:** 071 (the 128 KiB window, the stated stack, the signal guard), 053 (async host
  functions), 055 (sessions), 015 (`run_async`, `cancel`, Ctrl-C), 032 and 034 (providers), all
  landed. It meets 065, 083 and 073 in flight (Decision 13).
- **Research it stands on:** `../research/2026-10-19-the-runners-own-stack.md` and its evidence
  folder (everything below marked EXECUTED is there); `../research/2026-10-18-deep-recursion-on-the-wasm-stack.md`
  with its addendum; question 102 and its answer (`../decisions.md`, "100 to 103 … answered",
  2026-10-19); spec 071's build review, F1; the 0.1.0a7 security review, F4.

## The problem

wasmtime runs wasm on the calling thread's own stack and gives it 512 KiB. Spec 071 narrowed
CPython's guard so that recursion through Python code raises `RecursionError` inside that, but
much still ends the call in a trap: recursion in C over nested data (`repr`, `==`, `json` both
ways), the parser, deep exception groups, callbacks out of expat, freeing deep structures, XPath
and XSLT, and a raised recursion limit. Eight of spec 065's CPython tests are trap entries for
this reason. A larger stack is the fix upstream uses, but a limit larger than the thread kills
the host process, and the runner does not own the caller's thread: Linux's main thread has 8 MiB,
Windows' 2 MB, musl's default threads 128 KiB. On musl that already kills the host today: a
recursing guest run from a default thread, or through `run_async`'s own pool (spec 071's build
review, F1). The owner chose, on 2026-10-19 (question 102, option (a)): the runner runs each guest
on a thread of its own with an 8 MiB stack, and the README asks other embedders for the same.

Three facts shape the design (the research):

- an 8 MiB wasm stack needs a thread of at least 8 MiB plus 48 KiB for the runner's own frames
  (EXECUTED on five host configurations), and wasmtime-py must raise wasmtime's async stack size
  to take it, or the engine aborts the process (EXECUTED, READ);
- on musl, CPython 3.14 and later guess their thread's stack as 4,000,000 bytes, so any callback
  from deeper in the guest ends the process with a fatal error unless the runner tells the
  interpreter the thread's real stack (EXECUTED, READ);
- today a provider, the door's host function, `signal.signal`, thread-locals and context
  variables all run on the caller's thread, and the README promises it.

## Decisions

1. **The runner gives the guest an 8 MiB wasm stack.**
   - `_WASM_STACK = 8 << 20`. `_engine` sets `cfg.max_wasm_stack = _WASM_STACK` and, before
     `wt.Engine(cfg)`, wasmtime's async stack size to the same, through wasmtime-py's library:
     `wasmtime._ffi.dll.wasmtime_config_async_stack_size_set(cfg.ptr(), _WASM_STACK)` (argument
     types set once: `c_void_p`, `c_size_t`; no result). The runner already calls that library this
     way (the epoch deadline and its callback).
   - **Why the async size.** Above 2 MiB wasmtime refuses a config whose `max_wasm_stack` exceeds
     `async_stack_size` (READ, `config.rs:2632–2633`), and wasmtime-py's engine unwraps the error,
     so the process aborts (EXECUTED, `p1_config.out`: exit −6 at 2 MiB + 4 KiB, 8 MiB, 16 MiB).
     wasmtime-py 49 has no setter for it. The async size is used only by async calls, which the
     runner never makes (READ, `config.rs:862–877`).
   - **Why 8 MiB.** The owner's answer. It closes every trap entry and every data limit the
     research measured but chains of frees and a few deep C walks, each now 10 to 16 times deeper
     (Decision 11); it is the stack native CPython has on Linux's main thread. More would cost
     memory per running guest for what is left, which grows only linearly with the stack.
   - **Fuel does not move** (EXECUTED, `fuel078.out`: the same fuel for five programs at 512 KiB
     and 8 MiB, on the caller's thread and on a fresh one).

2. **Every entry into wasm runs on a guest thread of its own, made for that entry, with 9 MiB of
   stack.**
   - `_HOST_ROOM = 1 << 20` and `_THREAD_STACK = _WASM_STACK + _HOST_ROOM`, private constants with
     a comment naming this specification.
   - **The entries:** `_drive` (each `run`, from the signal guard to the export's return); a
     session's opening (the signal guard, the preopen check, the instantiation and the mount
     table's bind); each turn (`_drive_turn`, `_initialize` and `host_alloc` included); each
     ending's `shutdown` export. Nothing else enters wasm: the runner's check module and
     trampolines run only inside these. **No wasm runs on a caller's thread.**
   - **The home thread** is the thread that made the call (`run`'s caller, `run_async`'s worker,
     the thread that claimed a turn, the thread that runs an ending). It waits while the guest
     thread runs, and serves the embedder's code (Decision 4).
   - **How the thread is made.** `threading.stack_size` is one value per interpreter (READ,
     CPython's `interp->threads.stacksize`). The runner, under a lock of its own
     (`_stack_size_lock`), sets it to `_THREAD_STACK`, starts the thread and restores the value it
     found, in one block, so threads other code makes keep their size. A thread another thread
     starts in that window also gets 9 MiB; harmless, and said in the README. The thread is named
     `wasi-python-guest` and takes the home thread's daemon flag (threading's default). It runs in
     a copy of the home thread's `contextvars` context, so the tool threads it starts copy the
     caller's context, as today. A thread that cannot start raises `RuntimeError` from the call,
     before any guest code.
   - **Why 1 MiB of host room.** The most measured below the guest's frames, with a door or
     provider callback at the deepest point, is 48 KiB (EXECUTED, `p5-*.log`: darwin, glibc and
     musl, aarch64 and x86_64). Since the embedder's code no longer runs there (Decision 4), the
     room holds only the runner's own frames (its callbacks, the epoch callback, the output
     writers, the tool protocol's frame host, whose nesting is bounded), and Windows' trap handler,
     which runs on the faulting thread (INFERRED). 1 MiB is about twenty times the measure.
   - **Why a thread per entry, not a pool.** A start and join costs 36 to 50 µs on darwin
     (benchmark, `p3_handoff-darwin.out`) against 20 to 25 ms for the smallest warm call. A thread
     per entry has no lifecycle (no idle reaping, no fork or exit handling, no stuck thread to
     account for), returns its touched stack at exit, and keeps concurrency the callers': N callers
     still run N guests at once. A pool would need a bound, which would queue calls `run` does not
     queue today.
   - **Why not the async fiber** (wasmtime's `call_async`, which runs wasm on a stack wasmtime
     allocates): wasmtime-py does not wrap it, the WASI linker and every callback would change, and
     CPython 3.14's guard would see each callback on a foreign stack (INFERRED from section 3 of
     the research). Not taken.
   - **Why not hop only when the caller's thread is too small.** Where host functions run, and
     whether a guest can kill the host, would then depend on the caller's thread: a Linux or darwin
     main thread cannot take 8 MiB (EXECUTED, SIGSEGV), a darwin worker thread can. One rule for
     every call.

3. **The guest thread checks its own stack before any wasm, and tells the interpreter where it
   guesses.**
   - **The check.** `_guest_stack()` reads the thread's real bounds from the platform: Linux
     `pthread_getattr_np`, `pthread_attr_getstack` and `pthread_attr_getguardsize` (the usable
     bottom is the address plus the guard); macOS `pthread_get_stackaddr_np` and
     `pthread_get_stacksize_np`; Windows `GetCurrentThreadStackLimits`. If the usable size is
     below `_WASM_STACK + _HOST_ROOM // 2`, or the bounds cannot be read (another platform, a
     failed call, any exception), the entry raises `RuntimeError` before any wasm: "the guest's
     thread has N bytes of stack, less than the 8.5 MiB its 8 MiB wasm stack needs (did other code
     change threading.stack_size while the runner started it?); the call was refused". So a limit
     larger than the thread can never be reached: the SIGSEGV of the earlier memo, and the SIGILL
     and SIGSEGV the research measured below W plus 48 KiB.
   - **Telling the interpreter.** On CPython 3.14 or later on Linux without glibc
     (`sys.implementation.name == "cpython"`, `sys.version_info >= (3, 14)`, `sys.platform`
     Linux, `platform.libc_ver()[0] != "glibc"`), which mirrors CPython's own condition for
     guessing (READ, `Python/ceval.c`, `hardware_stack_limits`), the guest thread calls
     `PyUnstable_ThreadState_SetStackProtection(PyThreadState_Get(), bottom, size)` through
     `ctypes.pythonapi` with the bounds it read, before any wasm. Without it, a callback from more
     than about 4,000,000 bytes into the thread ends the process with "Fatal Python error:
     _Py_CheckRecursiveCall: Unrecoverable stack overflow" (EXECUTED, `musl-guess.log`, 3.14.5 and
     3.14.0); with it the same guest completes (EXECUTED). Every callback counts, the runner's own
     included (its WASI shadows, output writers and epoch callback are Python called from wasm).
   - **CPython 3.14.0 on musl** has no such call (EXECUTED: it is in 3.14.1 and later). There every
     entry is refused with `RuntimeError`: "CPython 3.14.0 on this C library guesses its thread's
     stack and cannot be told the guest thread's; use CPython 3.14.1 or later". Refusing keeps the
     host alive; running would let any deep guest kill it.
   - **Elsewhere nothing is told.** glibc, macOS and Windows give CPython its real bounds (READ);
     Windows' own computation also subtracts the thread's stack guarantee, which the runner's
     bounds would not, so telling it would lower its guard. CPython 3.11 to 3.13 count C recursion
     and read no stack pointer (EXECUTED: musl 3.13 survives without the call).

4. **The embedder's code runs on the home thread.**
   - **What is handed home:** the door's host function (`host=`; `_door`'s `host(…)` call) and
     every provider method (`_Files._invoke`'s call, in `mounts.py`, which serves reads, writes,
     the ending's write-backs and every other provider call). The guest thread puts the function
     and its arguments in the call's home inbox and waits; the home thread runs it and hands back
     the value or the exception, which the guest thread then meets exactly as it meets a direct
     call today (an `Exception` is the provider's fault or the door's `HOST_FAULT`; any other
     `BaseException` stops the call and is raised from `run`). A call made on the home thread
     itself (the mount table's ending walk, `table.walk()`, which runs after the guest) calls
     directly.
   - **What stays on the guest thread:** the runner's own code that serves the guest: WASI's
     calls, the runner's shadows (`poll_oneoff`, the guard table, the open-file cap), the output
     writers, the epoch callback, and the tool protocol's frame host. Tools and gates already run
     on threads of their own (spec 036) and are unchanged.
   - **So nothing the README promised about host functions changes:** a `sqlite3` connection made
     with `check_same_thread` (the default), a database session bound to its thread, a
     `threading.local`, the caller's context variables (live: a value a host function sets is
     seen by the caller after `run`, as today), and `signal.signal` on the main thread all keep
     working, because they run where they ran.
   - **The cost** (benchmarks, not checks): two thread hand-offs per door or provider call, 7.0 to
     7.7 µs per round trip on darwin, against 31.5 µs for a provider `stat` and 44 µs for a door
     call today: about a quarter more host time per such call there. In the loaded Linux VM the
     hand-off measured 33 to 495 µs; the builder re-measures it on a quiet Linux host and the
     landing notes state it. No fuel moves; WASI calls served by wasmtime itself (grants, the zip)
     are not handed anywhere.
   - **Why not run them on the guest thread** (what question 102 listed as option (a)'s costs):
     every one of those costs would land on embedders, the README's promise ("A provider runs
     synchronously on the thread that runs the guest", read as the caller's thread) would break
     after the public API's freeze, and the host room would have to hold arbitrary embedder code
     below 8 MiB of wasm frames, on musl inside the interpreter's guess. Handing two call sites
     home answers all of them at a measured per-call price.

5. **Ctrl-C reaches the guest from the home thread.**
   - **Deferred as today.** While the home thread is the main thread under Python's default SIGINT
     handler, `_deferred_ctrl_c` installs `_note_ctrl_c`, which only sets the flag. Nothing raises
     in the runner's own code, which matters: an exception from a signal handler can land between
     any two bytecodes (EXECUTED, `p6-p3-glibc-arm64.out`: once in four 3.11 runs it landed outside
     a loop's `try`).
   - **Read on the guest thread through the call.** `_Call` gains `ctrl_c: bool`, set where the
     call is built, on the home thread (`_ctrl_c_watched()` there). The shared host functions, the
     epoch callback and the tool protocol's bound read `call.ctrl_c and _ctrl_c["pending"]`
     instead of asking which thread they run on, since on the guest thread `_ctrl_c_watched()` is
     always false. The waits' checks, built on the home thread, keep reading the flag.
   - **A main-thread call is polled.** A call whose home is the main thread (whatever its SIGINT
     handler) gets the epoch callback, its deadline checked every `CANCEL_TICKS` ticks, and the
     ticker, as a call with `cancel` does. So Ctrl-C stops a guest that computes without waiting
     or calling back, even with `deadline_s=None`, within about 50 ms of guest time (today it runs
     on: EXECUTED, `failfirst-main-darwin.out`). The cost is one epoch callback per 50 ms of such a
     call; no fuel.
   - **An embedder's handler that raises** (its own, or asyncio's on a second Ctrl-C) raises in the
     home thread, never in a wasmtime-py trampoline, since none runs there. Raised while the home
     waits, it is recorded as the call's stop (`home.raised`): the epoch callback stops the guest
     at its next check, the home keeps serving until the guest thread ends, and `run` raises it.
     Raised inside a provider or door host, it is that function's `BaseException`, as today. Today
     such an interrupt is dropped by ctypes and the call runs to its deadline (EXECUTED,
     `failfirst-main-darwin.out`), and the README says it can abort the process.
   - **If the home stops serving anyway** (a second exception landing inside its own bookkeeping),
     a `finally` clears `home.serving`; a guest thread waiting for a hand-off checks it every
     `CANCEL_TICKS` ticks and treats the call as stopped, and the epoch callback stops the guest.
     The guest thread then ends at its next check, or at its deadline. No process abort and no
     host hang follow; Python cannot guard against an exception landing inside that `finally`
     itself, and the README says so in one line.

6. **Deadlines and `cancel` are unchanged.** The epoch callback and the provider gate (`_gate`,
   which runs on the guest thread before a provider call is handed home) read them as today; the
   ticker is process-wide. A provider or door host blocked on the home thread holds the guest, as
   it does today, and the README's "your provider's own time is outside the deadline" stands.

7. **`run_async` keeps its executor; the guest thread is a second hop.** The worker (the default
   pool's or the caller's `executor`'s) is the home thread: it waits and serves the provider and
   the door host, as it runs them today, never on the event loop. The guest runs on its own thread,
   so the executor's thread size no longer matters: musl's 128 KiB pool threads, or an executor of
   small threads, can no longer be killed by a recursing guest (closing spec 071's build review
   F1). `async_workers` still bounds how many guests run at once; each running guest holds the
   blocked worker, as today, and its guest thread. The task's cancellation sets the call's event,
   as today.

8. **Sessions.**
   - The opening runs its wasm (Decision 2) on one guest thread; each turn on a fresh one, with
     the claiming thread as home; each ending's `shutdown` export on one, with the ending's thread
     as home (`close()`'s caller, the turn's thread, or a closer). A store may change threads
     between turns (EXECUTED, `turns078.out`: the same output and fuel as on one thread).
   - `state.turn_thread` stays the claiming thread, which is where host functions run, so a host
     function that calls `close()` from inside its own turn still returns at once (spec 055).
   - The turn's trap-handler check (spec 071, Decision 9) moves with `_drive_turn` onto the guest
     thread, still the last thing before guest code; the opening's and the ending's checks move
     with their wasm.

9. **The signal guard, fuel and the record.** `_trap_handlers_ready()` reads process-wide signal
   dispositions, so it gives the same answer on the guest thread, now the last step before wasm in
   every entry. Fuel does not move (Decision 1). `Completed` is unchanged.

10. **The C-stack window stays 128 KiB; no knob here.**
    - **Measured** (EXECUTED, `window-arm64.jsonl`, arm64 only): at 8 MiB a 256 KiB window, spec
      071's `W/32`, about doubles every depth through Python code (`__repr__` 214 to 462,
      `lru_cache` 208 to 449, `sorted(key=…)` 52 to 111, `np.frompyfunc` 53 to 115, a `pyexpat`
      handler 137 to 294) and the data shapes still raise. At 512 KiB the same window traps nine of
      twelve rows.
    - **Why not here.** A wider window is useful only as a knob the guest is told, so other
      embedders keep 128 KiB: a new contract the guest reads from its environment, a recipe change
      (build-class, reviewed before build), and research this one has not done (x86_64, whose
      frames are up to 29% larger, would need about 8.3 MiB at 256 KiB for `json.loads`, over W;
      INFERRED). 078 stays parallel-safe, before 0.1.0, as the roadmap has it. The knob is a
      follow-up for the owner to place (the section "For the owner").

11. **What it closes, measured.**
    - **Spec 065's eight trap entries** all trap at 512 KiB and pass at 8 MiB (EXECUTED,
      `cpy078.out`, each alone through the judge's driver on the runner's engine):
      `c-stack-doctest`, `c-stack-exceptions`, `c-stack-syntax`, `c-stack-syntax-lazy-import`,
      `c-stack-ordered-dict-py`, `c-stack-ordered-dict-py-subclass`,
      `c-stack-ordered-dict-subclass`, and `c-stack-traceback`, whose module now runs to its end
      (434 tests; its 167 errors and one failure are not traps: 139 import the absent `_testcapi`,
      28 write a temporary module where the research driver's directory is read-only, and
      `MiscTest.test_windows_only_module_error` fails; `traceback-8m.txt`).
    - **The README's limits** (EXECUTED, `edges-*.jsonl`; arm64 / x86_64 at 8 MiB):
      - now raise `RecursionError`, or the parser's `MemoryError`, at any depth tried (to 400,000):
        `repr`, `==` and `json.dumps` of nested lists, `json.loads` of nested arrays,
        `json.dumps` with a nesting `default=`, `eval` of nested parentheses (199, the tokenizer's
        most) and of nested unary operators, and callbacks out of expat (`pyexpat`, `xml.sax`, an
        `ElementTree` target);
      - now complete: printing a 100,000-deep `ExceptionGroup`;
      - now raise their library's own error first: XPath (`XPathEvalError` at libxml2's limit) and
        XSLT (`XSLTApplyError` at `xsltMaxDepth`);
      - still trap, deeper: freeing a nested list or tuple past 37,433 / 32,753 (2,325 at 512 KiB),
        a nested dict past 22,785 / 20,962 (1,415), `hash` of a nested tuple past 40,313 / 40,312
        (2,504), compiling an expression of more than 58,227 / 52,402 terms (3,614), C14N of a tree
        23,818 / 23,817 deep (1,477), and recursion that reaches a `sys.setrecursionlimit` above
        47,642 / 43,670 (2,958);
      - unchanged: a chain of more than 1,897 `map` objects raises and then ends in an
        `unreachable` trap, at the same depth on both stacks, so not the stack's (INFERRED: the
        window's hard limit reaching `Py_FatalError`, spec 071's review, N1).
      - Not re-measured: RelaxNG validation of a deep tree (criterion 9 measures it).

12. **Other embedders are asked for the same** (the README's fourth step). Give the guest 8 MiB of
    `max_wasm_stack`, with `async_stack_size` at least as large; make every call into the guest on
    a thread with 8 MiB plus your own frames (the runner gives 9 MiB; neither a Linux nor a Windows
    main thread has it); on CPython 3.14.1 or later on musl, tell the interpreter that thread's
    stack; or keep wasmtime's 512 KiB and meet the limits measured there, which the README keeps.

13. **Where this meets other specifications.**
    - **065** (CPython's own tests in the release; in the lane, build-class). Question 102's answer
      says its trap entries name 078 as their closer once 078 is drafted: each of the eight
      entries' `closes_with` becomes this file, and its reason "closes with spec 078 (an 8 MiB
      stack)". **If 065 lands first,** this builder removes the eight entries and their gaps in
      `tests/known_gaps.toml`, lets the seven tests run in their groups and `test_traceback` in
      `cpython-a`, and derives the classes of `test_traceback`'s results with 065's own driver
      (each into an existing class where one fits, any new one with its reason and closer), all
      with `--accept-judge`. **If 078 lands first,** 065's builder derives on that main: no
      `c-stack-*` entry, and `test_traceback` in its group.
    - **083** (the judge's driver answers file times; built after 065). Both edit
      `tests/harness/guest.py`'s `run()`; the merge is textual. Whichever lands second rebases and
      re-runs the fast tier.
    - **073** (`run` keeps an unclosed file's bytes; it undoes the freeze and finalizes on the
      snapshot, question 103). Finalizing frees what a program leaves, so a structure deeper than
      the freeing limit, left in a global, ends a call that used to finish in a trap: about 2,000
      deep at 512 KiB, about 32,000 at 8 MiB (INFERRED from Decision 11). Whichever lands second
      states that limit in its README line.
    - **071's checks** change here (the section "The judge's changes").
    - **087** (the 0.1.0a7 security review's guest follow-ups): F4's rows are rewritten here at
      8 MiB; its optional lower `xsltMaxDepth` no longer matters to `run`, whose XSLT now stops at
      libxslt's own limit, but still would to embedders at 512 KiB.
    - **086** (the toolchain move) changes Cranelift's frames, so it re-measures Decision 11's
      edges; the host room does not depend on the guest's frames.

## Intent

Every guest the runner starts runs on a thread the runner made, with 9 MiB of stack, 8 MiB of it
for wasm, checked before any wasm runs; the caller's thread, however small, can no longer be
overrun. The embedder's own code still runs on the caller's thread, as before. So recursion in C
over nested data, the parser, deep exception groups, expat callbacks, XPath and XSLT raise instead
of trapping, spec 065's eight trap entries close, the rest traps ten to sixteen times deeper, a
recursing guest cannot kill a host on musl, and Ctrl-C reaches a guest that never calls back.

## Design

```
src/wasi_python/runner.py
  _WASM_STACK = 8 << 20          # spec 078, Decision 1
  _HOST_ROOM = 1 << 20           # spec 078, Decision 2: the runner's own frames, measured <= 48 KiB
  _THREAD_STACK = _WASM_STACK + _HOST_ROOM
  _stack_size_lock = threading.Lock()   # reset in _after_fork_in_child
  _on_entry: Callable[[str], None] | None = None   # test hook: told each entry, on its guest thread

  _engine(metered): cfg.max_wasm_stack = _WASM_STACK; async_stack_size(cfg, _WASM_STACK)

  class _Home:                    # one per entry; made on the home thread
      ident, inbox (SimpleQueue), serving, raised, result
      call(fn, *args)             # on the home thread: fn(*args); else hand it home and wait,
                                  #   in CANCEL_TICKS slices, stopping if `serving` was cleared
      serve()                     # the home's loop: inbox.get(timeout=CANCEL_TICKS * TICK_S);
                                  #   run each hand-off, catching BaseException into its box;
                                  #   an exception raised into the loop -> `raised` (first kept);
                                  #   until the guest thread's DONE; finally: serving = False

  _on_guest_thread(kind, home, fn, *args) -> result
      under _stack_size_lock: old = threading.stack_size(_THREAD_STACK); start the thread
          (target: contextvars.copy_context().run(_guest_body, ...), name "wasi-python-guest");
          finally threading.stack_size(old)
      home.serve(); join; raise home.raised, or fn's exception; else return fn's result
  _guest_body(home, kind, fn, args)        # on the guest thread
      bottom, size = _guest_stack()        # Decision 3; RuntimeError if small or unreadable
      _tell_interpreter(bottom, size)      # musl CPython >= 3.14 only; 3.14.0 -> RuntimeError
      if _on_entry: _on_entry(kind)
      result = fn(*args)                   # then DONE to the inbox, whatever happened

  _Call: + home, + ctrl_c (bool, from _ctrl_c_watched() on the home thread)
  _door(host, admit, home): response = home.call(host, request)
  _shared / _epoch_answer: Ctrl-C from call.ctrl_c; stop when call.home.raised or not serving
  _instance: watched = home thread is main -> epoch deadline min(CANCEL_TICKS, ticks), _watch,
      ticker wanted; done = _on_guest_thread("run", home, _drive, ...)
  _tool_host, _session_tool_host: ctrl_c=lambda: call_watched and _ctrl_c["pending"]
  _open_session: the guard, _check_preopens, instantiate, bind -> _on_guest_thread("open", ...)
  _turn_inside: _on_guest_thread("turn", home, _drive_turn, ...)
  _shutdown: the export -> _on_guest_thread("shutdown", ...)

src/wasi_python/mounts.py
  _Files._invoke: answer = self.call.home.call(getattr(mount.provider, method), *args)
      (directly when there is no call, or on the home thread)
```

- `_guest_stack()` resolves its C functions once, lazily, per platform, with `ctypes`, as 071's
  `_trap_handlers_ready` does; any exception inside it answers "unreadable".
- The hand-off box is a lock the guest thread waits on in slices; the inbox is the home's only
  queue, so hand-offs are served in order.
- `KeyboardInterrupt` and `SystemExit` raised by the embedder's code travel back in the box as
  any `BaseException`, unchanged.

## Scope

In: the above, its checks, the judge's driver at 8 MiB, the README and the CHANGELOG.

Out, each with its reason:
- A wider C-stack window, or a knob for it: Decision 10.
- A pool of guest threads: Decision 2.
- A `run()` option for the stack or for running on the caller's thread: a public-API change after
  the freeze (spec 049) with no user asking; the one rule is simpler.
- Carried CPython patches (question 102's option (b)): not chosen.
- Chains of frees past the new limits: no guard sees them (the earlier memo); they stay documented
  limits, now 16 times deeper.
- `signals_based_traps = False` (spec 071, Decision 9): the owner's, and unrelated.

## Acceptance criteria

The checks are written first. Each is new or restated, written before the code, and seen failing
first on main `3561e55` (or against the stand-in named). Depths are counts; nothing measures time. A child process has a
120 s limit only so a hang fails the row instead of the run (as spec 071's criterion 11). New
unit checks go in `tests/unit/test_runner_threads.py`; behavioural ones in
`tests/checks/test_v1_2_hostile_guest.py`.

1. **Every entry runs on a guest thread with room, once.** `test_every_entry_runs_on_a_guest_thread`,
   through the real runner with `_on_entry` recording `(kind, threading.get_ident(),
   _guest_stack())`: one `run`; `run_async` on its own pool and with a `ThreadPoolExecutor`; a
   `Session` opened, run two turns and closed; a session ended by its idle bound (the reaper's
   injected clock, spec 055) so a closer runs the ending. Asserts: exactly one entry per `run`, per
   opening, per turn and per ending (`["run"]`, `["open", "turn", "turn", "shutdown"]`); every
   entry's thread is not the home thread; every usable size is at least `_WASM_STACK +
   _HOST_ROOM // 2`. Seen failing first: on main no guest thread exists (the hook is never called).

2. **The stated engine and thread.** `test_the_runner_states_its_wasm_stack` (restated in
   `tests/unit/test_runner_calls.py`): both engines are made with `max_wasm_stack` 8 MiB, the
   async stack size set to the same through the library (a recording stand-in for the
   `_ffi.dll` call), `_THREAD_STACK == _WASM_STACK + 1 MiB`.
   `test_the_guest_driver_makes_the_runners_engine` (restated): the judge's driver makes the same
   engine. Seen failing first: on main both say 512 KiB.

3. **A thread with too little stack is refused before any wasm.** `test_a_small_guest_thread_is_refused`:
   with `_guest_stack` replaced by a stand-in answering 8 MiB, then by one that raises, `run`, a
   session's opening and a turn each raise `RuntimeError` naming the stack; the door host, the
   provider and `_on_entry` are never called; the next call, with the real function, works. And
   with `threading.stack_size` replaced by a stand-in that sets 256 KiB whatever it is asked (a
   library lowering it at the same moment), the call is refused the same way, on the real thread. Seen failing first: on main
   nothing is refused.

4. **The interpreter is told where it guesses.** `test_the_interpreter_is_told_its_stack`, with
   stand-ins for the platform, the C library's name, the version and `ctypes.pythonapi`: on Linux,
   musl, CPython 3.14.1 the stand-in `PyUnstable_ThreadState_SetStackProtection` is called once
   per entry with the thread's bounds; on musl and 3.14.0 (no such function) the entry raises
   `RuntimeError` naming 3.14.1, before any wasm; on glibc, macOS, Windows and 3.13 it is never
   called. Seen failing first: on main nothing calls it.

5. **The calling thread's size no longer matters.** `test_a_guest_cannot_overrun_a_small_calling_thread[<row>]`,
   each row in a child process: `run` from a thread made with `threading.stack_size(256 * 1024)`
   whose guest frees a 20,000-deep list, then spec 071's `__repr__` recursion; and `run_async` on
   an executor whose threads have 256 KiB. Each completes (`ok`, `RecursionError`), the child
   exits 0. Seen failing first: on main the first kills the child with SIGILL on darwin (EXECUTED,
   `failfirst-main-darwin.out`, a 2,000-deep list), SIGSEGV on Linux.

6. **The embedder's code keeps the caller's thread.** `test_host_functions_run_on_the_callers_thread`:
   a door host and a provider each record `threading.get_ident()`, read a `ContextVar` and a
   `threading.local` the caller set, use a `sqlite3` connection the caller made (default
   `check_same_thread`), and set a second `ContextVar`; on POSIX, from the main thread, the door
   host also calls `signal.signal(SIGUSR1, …)` and restores it. Asserts: the caller's ident, the
   caller's values, no `ProgrammingError` or `ValueError`, and the caller sees the value set inside
   (the context is live, not a copy). The same through `Session.run` and through `run_async`
   (ident: the worker's). Seen failing first against a stand-in runner that calls host functions
   on the guest thread: every assertion but the values read fails.

7. **Ctrl-C stops a guest that never calls back.** `test_ctrl_c_stops_a_computing_guest`, in a
   child on its main thread: `run(["-c", "import _host\n_host.call(b'go')\nwhile True: pass"],
   host=h, deadline_s=None)`, where `h` starts a timer that calls `_thread.interrupt_main()` (a
   simulated SIGINT on every host). Asserts: `run` raises `KeyboardInterrupt`; the next call
   prints `1`; the child exits 0. A session turn the same way. Seen failing first: on main the
   child never ends and is killed at its limit (EXECUTED, `failfirst-main-darwin.out`).

8. **An embedder's raising handler stops the call and cannot abort the host.**
   `test_an_embedders_raising_sigint_handler_stops_the_call`, in a child: a SIGINT handler that
   raises `KeyboardInterrupt`; the same guest with `cancel=threading.Event()` and
   `deadline_s=None`; the door host's timer sends SIGINT to the main thread
   (`signal.pthread_kill` on POSIX, `_thread.interrupt_main()` on Windows). Asserts: `run` raises
   `KeyboardInterrupt`, the next call works, the child exits 0. Seen failing first: on main ctypes
   drops the interrupt in `_on_epoch` and the call runs on (EXECUTED: to its 30 s deadline,
   `"deadline"`; with `deadline_s=None`, to the child's limit).

9. **The limits at 8 MiB hold, and what now raises raises.**
   - `test_deep_data_limits[<kind>]` (restated): through `run`, metered, each kind runs a depth that
     completes, a quarter below the lower host's edge, and one at least 40% past the higher host's
     that ends in `"stack overflow"`; then a third call prints `ok`:

     | kind | completes at | traps at | edge arm64 / x86_64 |
     |---|---|---|---|
     | freeing a nested list | 24,000 | 52,500 | 37,433 / 32,753 |
     | freeing a nested dict | 15,000 | 32,000 | 22,785 / 20,962 |
     | `hash` of a nested tuple | 30,000 | 57,000 | 40,313 / 40,312 |
     | compiling `1+1+…` (raises `RecursionError` below the edge) | 39,000 | 82,000 | 58,227 / 52,402 |
     | C14N of a deep tree built in Python | 17,000 | 34,000 | 23,818 / 23,817 |
     | recursion reaching a raised `sys.setrecursionlimit` (raises below the edge) | 32,000 | 67,000 | 47,642 / 43,670 |

   - `test_deep_data_raises[<kind>]` (new): each ends in the named exception, no trap, the next call
     works: `json.loads` of 400,000 nested arrays, `==` and `repr` and `json.dumps` of 400,000-deep
     lists, a 2,000-level nesting `default=` (`RecursionError`); `eval` of 199 parentheses and of
     100,000 unary minuses (`MemoryError`, "Parser stack overflowed"); a `pyexpat` handler, an
     `xml.sax` handler and an `ElementTree` target parsing again without bound (`RecursionError`);
     printing a 10,000-deep `ExceptionGroup` (completes); XPath of 6,000 nested parentheses and of
     6,000 chained predicates (`XPathEvalError`); XSLT `call-template` 4,000 deep and
     `apply-templates` over a 4,000-deep tree (`XSLTApplyError`); RelaxNG validation of a 5,000-deep
     tree built in Python (the builder measures it; it joins whichever table its outcome names).
   - Seen failing first: on main every deep row of both traps at 512 KiB (EXECUTED,
     `edges-512k-arm64.jsonl`), and the restated completing depths trap.
   - `test_a_stack_overflow_is_named` stays as it is: its program still traps "stack overflow" at
     8 MiB (EXECUTED, `named.out`, 9.77 G fuel).

10. **Sessions.** Criterion 1 covers where a session's wasm runs. Spec 055's checks pass unchanged,
    among them a host function's `close()` from inside its own turn. And
    `test_a_turn_frees_a_deep_structure`: a turn that frees a 20,000-deep list completes and the
    session goes on (seen failing first: on main it traps and ends the session).

11. **Linux's faulthandler orders still hold.** Spec 071's criterion 11 keeps its rows; its deep
    program becomes freeing a 200,000-deep list, which still traps at 8 MiB (`json.loads` now
    raises). Seen failing first: with the old program on the branch, the "trapped" rows read a
    `RecursionError` instead.

12. **The judge.** The fast tier, and one full run (`uv run pytest -n 3`) against main's set
    `build/sets/s-c50ca51fae5eb55b-c9dcb5b8`: no failure, no accepted pass lost, and no fuel metric
    grown (Decision 1); the ratchet's only moves are the checks above and the judge change.

13. **CPython's suite.** As Decision 13 says, by landing order; on the set, each of the eight
    entries' tests passes by full id through 065's driver, and `test_traceback` has no trap.

14. **Docs.** The README and CHANGELOG below; `test_rules.py` passes; the API reference is
    regenerated (`tests/harness/api.py --write`) for the changed docstrings; `tests/public_api.txt`
    does not change.

15. **Every release host.** Criteria 1, 3, 5, 7, 8 and 9 run on Linux, macOS and Windows in the
    release (Windows in the dry run before the tag, AGENTS.md 6b).

16. **musl, by the builder** (the release has no musl host). In Alpine on aarch64 and x86_64,
    with the built runner: criterion 5's rows and the research's `list-door` edge complete on
    CPython 3.14.1 or later and on 3.13; on 3.14.0 every entry is refused with criterion 4's
    message and the host lives. The landing notes carry the logs, as spec 071's build review did.

## The judge's changes

- `tests/harness/guest.py`: `WASM_STACK = 8 << 20`; `engine()` sets the async stack size to it
  through the library; each `run()` and each `Turns` instance's calls (its instantiation included)
  run on a thread of `WASM_STACK + 1 MiB`. The driver's own host functions stay on that thread:
  they are the judge's, bound to no thread. Fuel does not move (EXECUTED, `fuel078.out`).
- `tests/unit/test_runner_calls.py`: criterion 2's two restated units.
- `tests/checks/test_v1_2_hostile_guest.py`: `test_deep_data_limits` restated (criterion 9), new
  `test_deep_data_raises`, criteria 5, 7 and 8, and the faulthandler child's deep program
  (criterion 11).
- `tests/checks/test_v1_4_sessions.py`: criterion 10's new check.
- `tests/unit/test_runner_threads.py`: new (criteria 1, 3, 4, 6).
- By landing order with 065: `tests/upstream/python.toml`, its `expected/` lists and
  `tests/known_gaps.toml` (Decision 13).

The lane accepts with `--accept-judge "spec 078: the runner and the judge's driver run each guest
on a 9 MiB thread of its own with an 8 MiB wasm stack; 071's deep-data limits restated at 8 MiB,
new checks for what now raises, for the guest thread, its stack check, the interpreter told its
stack on musl, small calling threads, host functions on the caller's thread and Ctrl-C; the
faulthandler child traps by freeing"`. No `--accept-growth`.

## README

The platform facts' **Deep recursion** bullet, rewritten (the lower host's numbers, rounded down):

> - **Deep recursion**: recursion that runs through Python code (a `__repr__` that calls
>   `repr(self)`, `lru_cache`, a `sort` key, a numpy, pandas or lxml callback) raises
>   `RecursionError` ("Stack overflow (used 112 kB)") after 40 to 250 levels, where native Python
>   allows 1,000. The runner runs each guest on a thread of its own with 8 MiB of native stack
>   (spec 078), and CPython's guard watches 128 KiB of the C stack in linear memory (spec 071), so
>   recursion in C over nested data raises too: `repr`, `==`, `json` both ways, the parser, expat's
>   callbacks; XPath and XSLT stop at their own limits with their own errors. Some recursion still
>   ends the call with the trap "stack overflow": freeing a nested list more than about 32,000 deep
>   (a dict 20,000); `hash` of a nested tuple past 40,000 (natively a crash); compiling an
>   expression of more than about 52,000 terms; C14N of a tree about 23,000 deep; recursion that
>   reaches a `sys.setrecursionlimit` above about 43,000. A chain of more than 1,897 `map` objects
>   ends in the trap "unreachable". The trap ends only that call. An embedder that keeps wasmtime's
>   512 KiB meets lower limits (*From any language*, step 4).

*Running it*: the paragraph on the calling thread's stack (and musl's 128 KiB) is replaced by:

> `run` runs each guest on a thread of its own, made for the call, with 9 MiB of stack, 8 MiB of
> it for wasm (spec 078); the calling thread's own size does not matter, musl's 128 KiB threads
> included. Your `host` function and providers still run on the thread that called `run`, which
> waits. A thread another thread starts while the runner starts its own gets 9 MiB too
> (`threading.stack_size` is one value per interpreter). On Windows, CPython commits a thread's
> whole stack, so each running guest commits 9 MiB. On CPython 3.14.0 on musl every call is
> refused with `RuntimeError`: that interpreter guesses its thread's stack and cannot be told
> (use 3.14.1 or later).

*Mounts*, **Time and threads**: "A provider runs synchronously on the thread that called `run`
(under `run_async`, the worker thread, never the event loop's) while the guest waits on its own
thread." The rest stands.

*From async code*: the `executor` bullet adds "the guest itself runs on a thread of the runner's
own, so the executor's thread size does not matter"; the memory bullet adds "and a guest thread
with a 9 MiB stack".

*From any language*, step 4, rewritten:

> 4. **Give the guest 8 MiB of native stack, on a thread with room for it.** Set `max_wasm_stack`
>    to 8 MiB; above 2 MiB wasmtime also needs `async_stack_size` at least as large, or it refuses
>    the engine (wasmtime-py has no setter: call its library's
>    `wasmtime_config_async_stack_size_set`; its engine then aborts the process on the refusal).
>    wasm runs on the calling thread's own stack, so make every call into the guest on a thread
>    with 8 MiB plus your own frames (the runner gives 9 MiB; a Linux main thread has 8 MiB and a
>    Windows one 2 MB, too little: a guest that uses its stack then kills the process). On CPython
>    3.14.1 or later on musl, tell the interpreter that thread's stack
>    (`PyUnstable_ThreadState_SetStackProtection`), or a host function called from deep in the
>    guest ends the process. With wasmtime's default 512 KiB instead, recursion through Python
>    code still raises, except through expat's callbacks, and the recursion the *Deep recursion*
>    bullet listed before spec 078 traps, at the depths it gave (moved here unchanged). On Linux,
>    install `faulthandler` … (unchanged).

*Safety*, "Enforced": the deep-recursion bullet becomes "deep recursion through Python code raises
`RecursionError`, and recursion in C over nested data too: the guest runs on a thread of the
runner's own with 8 MiB of wasm stack, whose size is checked before any wasm runs, so a guest
cannot use more stack than its thread has (see *Deep recursion* for what still traps)"; the Ctrl-C
sentence becomes "While `run` holds the main thread, Ctrl-C ends the call at the guest's next wait,
door call or epoch check (every 50 ms of computation), and is raised from `run`; an embedder's own
SIGINT handler that raises lands in the runner's wait, never in wasmtime, and stops the call the
same way."

*Not protected*: remove "Ctrl-C for a guest that never waits or calls the door …", "Ctrl-C under an
embedder's SIGINT handler that raises …" and "a call on a thread with less stack than the guest's
512 KiB … musl …"; rewrite the stack-overflow item to "recursion in C over very deep data and
freeing very deep structures, past the limits under *Deep recursion*"; add "a second exception
from your SIGINT handler landing inside the runner's own clean-up, after which `run` may return
before the guest's thread has stopped (it stops at its next check or its deadline)".

## CHANGELOG (the open release's section)

> - **Each guest runs on a stack of its own** (spec 078; question 102). The runner runs every guest
>   on a thread it makes for the call, with 9 MiB of stack, 8 MiB of it for wasm (it was 512 KiB on
>   the caller's thread), and checks that thread's stack before any wasm runs. Recursion in C over
>   nested data (`repr`, `==`, `json` both ways), the parser, deep exception groups, expat's
>   callbacks, XPath and XSLT now raise instead of ending the call in a trap; freeing nested
>   structures, deep `hash`, long expressions, C14N and very high recursion limits still trap, 10 to
>   16 times deeper (the README lists them). A recursing guest can no longer kill a host whose
>   calling thread is small, such as musl's 128 KiB threads and `run_async`'s pool there. Your
>   `host` function and providers still run on the thread that called `run`. Ctrl-C now stops a
>   guest that computes without calling back, and an embedder's SIGINT handler that raises stops the
>   call instead of being lost. **Changed:** each running guest holds one more thread (9 MiB of
>   stack reserved; committed on Windows); a door or provider call costs one thread hand-off each
>   way. On CPython 3.14.0 on musl every call is refused (use 3.14.1 or later). No public name,
>   signature or default changes; fuel does not change.

## For the owner

- **The window knob** (Decision 10, measured): at 8 MiB a 256 KiB window would about double every
  depth through Python code (`__repr__` 214 to 462), still below native's 1,000. It needs the guest
  to read its window from its environment, a recipe change and research on x86_64. It is not in
  078. Whether to reserve it as a follow-up is the owner's to place in the roadmap.
- **The hand-off's price** (Decision 4): keeping providers and the door host on the caller's thread
  costs a thread hand-off each way per call (7 to 8 µs on darwin, a quarter more host time per
  provider `stat`). The alternative, running them on the guest thread, is faster per call but
  breaks thread-bound objects, thread-locals, `signal.signal` and live context variables in host
  functions, which the README promised. 078 keeps the promise.
- **CPython 3.14.0 on musl** is refused outright (Decision 3); every later 3.14 has the call.

## Landing notes

None yet: drafted, not built.
