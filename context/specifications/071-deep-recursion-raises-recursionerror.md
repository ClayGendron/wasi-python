# 071 — Deep recursion raises RecursionError instead of trapping the guest

- **Status:** drafted 2026-10-18 (`0a379ac`, question 102 at `f5c6151`, both rebased onto main
  `6fd89e0`); reviewed before build the same day
  (`scratchpad/071-review/071-deep-recursion-raises-recursionerror-spec-2026-10-18.md`, for the
  lane to copy to `../reviews/`; verdict: "ready once F1 to F5 are answered, with F6 to F11
  written in"); revised against all eleven findings with the lane's rulings, and given new scope
  by the lane from spec 063's build review (its F3: Linux's faulthandler crash, Decision 9). The
  section "Disposition of the pre-build review" says where each went (`8d9f74e`). **Confirmed for
  build** by the same reviewer (the file's section "Confirmation of 071's revision": "confirmed
  for build once C1 and C2 are written in"); C1 to C6 written in (the section "Disposition of the
  confirmation"), for the lane to check. **Built 2026-10-18** on main `6cc30bb` (the Landing
  notes): the set's `SHA256SUMS` `a48b92aa…`; judge 488/505, 0 fail, lost 0, grew 63 (each named
  below). It changes the artifact set and the build recipe
  (`recipes/reactor_main.c`), so §5.6 asks for the review before build.
- **Owner:** Clay Gendron
- **Kind:** **build-class** (it touches `recipes/`): one call added to `recipes/reactor_main.c`,
  so `python.wasm`, the snapshot and `MANIFEST` change once; the stdlib zip does not. With it:
  - in the runner (`src/wasi_python/runner.py`): `_engine` states its wasm stack; a new private
    check, `_trap_handlers_ready`, refuses a call on Linux when wasmtime's trap handlers are not
    in place (Decision 9); `run`'s and `run_async`'s docstrings gain one `RuntimeError` reason,
    so the README's generated reference changes in those two entries;
  - **a judge change:** the guest driver's engine becomes the runner's (`engine()` in
    `tests/harness/guest.py`: fuel, epoch interruption, 512 KiB; Decision 3), which can move
    outcomes in every check and upstream group that runs through it (Decision 8); new checks in
    `tests/checks/test_v1_2_hostile_guest.py` and `tests/unit/test_runner_calls.py`; trap
    entries in `tests/known_gaps.toml` by landing order (Decision 7);
  - `README.md`, `CHANGELOG.md` (0.1.0a7).

  No carried patch: `recipes/patches/` does not change, and CPython stays exactly its tarball.
  **No line of `tests/public_api.txt` changes.**
- **Depends on:** 003 (the reactor and its `init_interpreter`), 016 (a trap named by its kind:
  "stack overflow"), 049 (the public API frozen), 068 (the open-file cap, which also edits
  `runner.py`), all landed. It meets 065 (CPython's own tests in the release), 063 (the release
  judges in parallel shards), 055 (bounded sessions) and 069 (the snapshot pre-imports no
  package): Decisions 7 to 9.
- **Research it stands on:**
  - `../research/2026-10-18-deep-recursion-on-the-wasm-stack.md`, its addendum, and its evidence
    folder (`v2/` for the addendum): the two stacks; the window swept on a relinked research
    binary and its snapshot; edges on arm64 and x86_64; the judge driver's engine; Linux's
    faulthandler crash, its mechanism and its exact detection;
  - the pre-build review's probes (`scratchpad/071-review/probes/`, its `margin-table.txt`
    copied into the memo's `v2/evidence/`): 74 shapes' margins on both hosts, CPython's own
    modules under the window;
  - spec 063's build review, F3, and its probes (`scratchpad/063-buildreview/sigill_probe/`);
  - `../research/2026-10-18-cpythons-own-tests-under-the-runtime.md`, finding 4.1.

## The problem

Plain user code ends the whole guest in a wasm trap where native Python raises
`RecursionError`. A `__repr__` that calls `repr(self)` traps after 416 levels; `repr` of a
100,000-deep nested list traps; so do `functools.lru_cache` recursion past 306 levels,
`np.vectorize` recursion past 171, and pickling a recursive `functools.partial` (EXECUTED, the
memo's section 1). A trap ends the `run`, and under spec 055 the whole session, with no
traceback. For a model's code this is the common failure: a recursion bug the model would read
and fix if it saw the `RecursionError`.

The cause (EXECUTED, READ; the memo's section 1) is two stacks:

- CPython 3.15 guards C recursion by the **linear stack**, the C stack in the guest's memory.
  Its window is the whole 16 MiB: wasi-libc's `pthread_getattr_np` reports
  `__stack_low`..`__stack_high`, and CPython raises only when the stack pointer comes within
  16 KiB of the bottom ("Stack overflow (used 16368 kB)" at a 64 MiB native stack).
- wasmtime runs every wasm call on its **native stack**, 512 KiB by default (EXECUTED: the same
  depth and fuel with `max_wasm_stack = 524288` as without it; wasmtime-py's docstring says
  2 MB, which is stale).
- Each level spends native and linear bytes in a ratio fixed by its shape: 2 to 3 to 1 for most
  recursion through Python code, about 6 to 1 for callbacks out of expat, up to 25 to 1 for C
  over nested data. So the native stack is gone long before CPython looks: the `__repr__` case
  uses 222 KB of its 16 MiB window when it traps. A chain of frees moves the linear stack not at
  all, so CPython's trashcan, which measures the same pointer, never starts.

A second defect reaches the same place (spec 063's build review, F3; the memo's A3): on Linux,
if the host enables or disables `faulthandler` after the runner's first engine exists, any guest
trap (a stack overflow included) kills the host process with SIGILL instead of returning
`trapped`.

## Decisions

1. **CPython's C-stack window is the top 128 KiB of the linear stack, set by the recipe through
   CPython's own API.**
   - `init_interpreter` in `recipes/reactor_main.c` calls
     `PyUnstable_ThreadState_SetStackProtection(PyThreadState_Get(), &__stack_high - 131072,
     131072)` right after `Py_InitializeFromConfig` succeeds, and aborts if it fails (it cannot
     with this size; the minimum is 24 KiB). The snapshot carries the window from its build; the
     plain binary sets it at its own start. The guest has no subinterpreters and no threads, so
     the main thread's state is the only one (EXECUTED, the memo's section 2). Nothing resets the
     limits once set (READ, the review: `_Py_InitializeRecursionLimits` runs only while the hard
     limit is zero).
   - **Why a window, and why this call.** The guard then raises while wasmtime's default stack
     still has room. CPython documents the call for embedders whose stack is not the one the OS
     reports (`Doc/c-api/threads.rst:754`). It is a recipe line, not a patch (§4.1).
   - **Why 128 KiB, on both hosts** (the lane's ruling on F1). At 512 KiB on the runner's engine,
     under the window, 64 of the 70 shapes in the review's table raise `RecursionError` on both
     arm64 and x86_64 (some at the recursion limit, as before); the three callbacks out of expat
     trap (Decision 5); three end in another exception of their own. The memo's `json.dumps`
     with a nesting `default=` hook traps too and is a Decision 5 limit. The thinnest that still raise, as 512 KiB over the smallest stack at which the shape
     stops trapping (EXECUTED, the review's `margin-table.txt`):

     | shape | arm64 | x86_64 |
     |---|---|---|
     | `heapq.heapify` whose `__lt__` heapifies again | 1.23 | **1.12** |
     | `functools.lru_cache` recursion | 1.45 | 1.28 |
     | `json.loads(object_hook=…)` recursion | 1.45 | 1.31 |
     | `itertools.groupby` key recursion | 1.49 | 1.36 |

     x86_64's frames are 0 to 29% larger than arm64's for the same shape, so x86_64 sets the
     margin: about a ninth, not the quarter the first draft claimed from arm64 alone. Windows
     could not be measured; its wasm frames use Cranelift's own convention, so x86_64 Linux is
     the nearer proxy (INFERRED), and the release's Windows job runs criterion 1.
   - **Why not a smaller window** (the review's F1, the lane's ruling). 96 KiB would not reach
     the `pyexpat` shape; 64 KiB would (EXECUTED for `ElementTree` on x86_64: 248 KiB needed at
     64 KiB; INFERRED for `pyexpat`), but every depth scales with the window less 16 KiB:
     `__repr__` would stop near 92 levels, `sorted(key=…)` near 22. That cuts ordinary depths too
     far for three parser shapes; they stay limits (Decision 5) and option (d) of question 102.
   - **Why not a smaller `-z stack-size`.** It would move the guard the same way but also take
     real linear space from C code with large locals.
   - **What it costs.** Recursion through Python code now stops at about half the depth where it
     used to trap: `__repr__` 214 levels (416 before), `lru_cache` 208 (306), `np.vectorize` 99
     (171), `sorted(key=…)` 52 (247); the lowest measured are `np.sort` of objects whose `__lt__`
     sorts again (42), `repr` of a pandas `Series` holding itself (51) and `sorted` with a
     recursive `__lt__` (53) (the review, EXECUTED). Native CPython stops all of them at its
     recursion limit, 1,000. These depths are set by linear bytes, so they are the same on both
     hosts. **A program that recursed between the new depth and the old one used to finish and
     now raises** (a dataclass `__eq__` over a 300-long linked list: about 244 levels now, about
     470 before; INFERRED from the `__eq__` row). The message is CPython's: `RecursionError:
     Stack overflow (used 112 kB)`. `eval` and `exec` recursion raise CPython's parser error,
     `MemoryError: Parser stack overflowed`, at 183 and 157 levels. Ordinary work does not
     notice: the memo's workload writes at most 27.6 KB of linear stack and `import pandas` at
     most 44 KB on the plain binary (the review), against the guard's 112 KiB; fuel is the same
     within 0.02%. No memory changes.

2. **The window is fixed; no knob.**
   - A wider window helps only an embedder whose native stack is at least 25 times it, since data
     shapes need that ratio to raise rather than trap (the memo's section 4). For a stack `S` the
     window that keeps both kinds safe is `max(128 KiB, S/32)`, so a knob would matter only
     above 4 MiB.
   - **Why not now.** It would be a new contract the guest reads from its environment, with no
     user in this repository. If a later change gives the runner a stack above 4 MiB (question
     102, option (a)), that change adds the knob with it, and this formula is its start.

3. **The runner and the judge's driver make the same engine: fuel, epoch interruption, and a
   512 KiB wasm stack, stated.**
   - `_engine` in `src/wasi_python/runner.py` sets `cfg.max_wasm_stack = 512 * 1024` (a private
     constant `_WASM_STACK`, with a comment naming this specification).
   - **The judge's driver** (`engine()` in `tests/harness/guest.py`) sets the same three:
     `consume_fuel`, `epoch_interruption` (with each store's deadline set far off, `2**40`, as the
     research's probes do, so no check is interrupted) and `max_wasm_stack`. **This is a judge
     change** (the review's F3, the lane's ruling): epoch checks make Cranelift's frames larger,
     so a driver without them measured more stack than `run` gives (the memo's A2). With it,
     every check and upstream group that runs through `guest.run` sees the runner's frames.
     Decision 8 says what that can move.
   - **Why state the stack.** The window is sized for it. wasmtime-py's docstring names another
     default, and a wasmtime that changed its default must not change the guest's behaviour
     without a specification. Compiled modules are unaffected: a cached `.cwasm` deserializes
     under any `max_wasm_stack` (EXECUTED by the research and by the review). Epoch
     interruption does change the compiled code, so the judge's driver compiles its module once
     more; the runner's cache is untouched.
   - **Why not larger.** A synchronous call runs wasm on the calling thread's own stack; wasmtime's
     limit stops only wasm. A 64 MiB limit on the main thread killed the host process with
     SIGSEGV, with no trap and no output (EXECUTED, the memo's section 5). `python.exe` on Windows
     reserves 2,000,000 bytes for its main thread and its threads (READ), so even 2 MiB is not
     safe there. wasmtime-py's apparent 2 MiB cap is not the limit (an exported setter lifts it;
     EXECUTED); the host thread is. No `run()` option for it: a larger stack needs a thread the
     runner owns (question 102).

4. **The embedder contract names the stack.** The README's "Any other embedder does the same
   three things" gains a fourth: give the guest at least 512 KiB of native stack
   (`max_wasm_stack`; wasmtime's default), on a host thread with room for it and for the host's
   own frames above it. With that, recursion through Python code raises `RecursionError`,
   except through callbacks out of expat (Decision 5). A larger stack, on a thread that has it,
   also lifts the limits of Decision 5 (the memo's section 4: 1 MiB covers nested `repr` and
   `json.dumps` and the parser on both hosts, EXECUTED on x86_64 by the review; 8 MiB covers
   `json.loads`, `==` and freeing 10,000-deep structures, EXECUTED on arm64). The README also
   says (the review's N2) that `run` itself needs a calling thread with 512 KiB plus the host's
   own frames free, which an application that shrank `threading.stack_size`, or passes
   `run_async` an executor with small threads, may not have.

5. **What still traps is documented, with the lower host's numbers, and checked.**
   - At 512 KiB, with the window, on the runner's engine. The README states the lower of the two
     hosts, rounded down (EXECUTED, the memo's A1):

     | case | the README says "more than about" | arm64 / x86_64 last good depth |
     |---|---|---|
     | a callback out of expat that parses again: `pyexpat` handler; `xml.sax` `ContentHandler`; `ElementTree` `XMLParser(target=…)` | 100; 95; 105 levels | 130 / 101; raises at 118 / 95; raises at 122 / 109 |
     | freeing a nested `list` or `tuple` | 2,000 deep | 2,324 / 2,033 |
     | freeing a nested `dict` | 1,300 deep | 1,414 / 1,301 |
     | `repr` or `str` of a nested list | 1,800 levels | 1,912 / 1,805 |
     | `json.dumps` of a nested list | 1,350 | 1,478 / 1,354 |
     | `json.loads` of nested arrays | 1,100 | 1,204 / 1,121 |
     | `==` of nested lists | 1,350 | 1,551 / 1,357 |
     | `hash` of a nested tuple (natively a crash at 100,000) | 2,500 | 2,504 / 2,503 |
     | a chain of `map` objects (natively a crash) | 1,850 (it raises up to 1,897, then traps) | 1,897 / 1,897 |
     | `json.dumps` with a `default=` hook that nests | 950 | 1,081 / 953 |
     | source with nested brackets (natively `SyntaxError` at 200) | 130 | 141 / 132 |
     | source with nested unary operators (raises up to here) | 2,900 | 3,222 / 2,926 |
     | printing a nested `ExceptionGroup` | 720 | 833 / 722 |

   - **lxml** (the review's F4). Main now carries lxml with libxml2 and libxslt (spec 046), after
     the frozen set this research used. Its callbacks call Python from deep C, the class the
     expat rows show to be the thin end. The builder measures four shapes on the built set, on
     both hosts (criterion 10): an `etree.XMLParser(target=…)` whose `start` parses again, an
     XPath extension function that evaluates XPath again, a `Resolver` that parses again, and
     `XSLT` with a Python extension element or function that transforms again. Each that traps
     at 512 KiB joins this table, with its edge and a criterion-4 pair; each that raises joins
     criterion 1 with its floor.
   - **Why documented, not fixed here.** No window can see a chain of frees; the data shapes, the
     parser and the expat callbacks need more native stack than a caller's thread promises
     (Decision 3), source changes to CPython, or a window that halves every ordinary depth.
     That choice is question 102's. Constitution §4.11: a platform's semantics are documented,
     not disguised.
   - **Checked as limits** (criterion 4): a pair per kind, one depth that completes on both hosts
     with a quarter of room, and one that ends in the named trap well past both edges, so the
     README stays true and a trap stays a reported trap the next call survives.

6. **Not in this specification: a larger runner stack, carried CPython patches, or a smaller
   window.** Each would close part of what Decision 5 lists, each with a cost this one does not
   pay. Question 102 (`../questions-for-the-owner.md`) puts the choice, options (a) to (d).

7. **Spec 065's trap entries: four close, five remain under question 102** (the review's F5,
   and 065's C7, which is this specification's edit).
   - 065 (at `01c5567`) now lists nine trap entries by full id. This specification's window
     closes the four `test_recursive_pickle` variants (`TestPartialC`, `TestPartialCSubclass`,
     `TestPartialPy`, `TestPartialPySubclass`; EXECUTED with `-m test_recursive_pickle`, which
     selects every class's method of that name, on the research snapshot; criterion 9 confirms
     each by id on the built set, on both hosts).
   - The other five still trap at 512 KiB, each for a reason this specification names:
     `test_doctest`'s `test_issue35753` (freeing a 1,000-long chain of `_Call` objects);
     `test_exceptions`' `test_recursion_in_except_handler` (freeing what the handlers chained);
     both `test_syntax` `test_error_on_parser_stack_overflow` entries (the parser's `MAXSTACK`,
     4,000 on WASI, needs more than 512 KiB); `test_traceback`, whole module (printing and freeing
     deep exception groups). Their closer is **question 102**: each gap's `closes_with` is
     `context/questions-for-the-owner.md`, and its reason names question 102.
   - Three more join them through Decision 3 (Decision 8; the build found three variants, not
     one).
   - 065's present text agrees with this (its lines 66–69 and 193–205 at `01c5567`). The first
     draft's Decision 7 ("one closes, four are renamed") is superseded by this one.
   - **If 065 lands first,** this builder removes the four `test_recursive_pickle` trap gaps and
     retires their trap checks (spec 050's condition C1: each passes on this set), with
     `--accept-judge "<reason>"`. **If this lands first,** 065's builder derives on this set:
     five trap entries (eight, Decision 8), with these reasons.

8. **Where this meets other specifications.**
   - **065, through the judge's driver** (the lane's ruling on F3). Under the runner's engine,
     CPython's `test_ordered_dict` `test_highly_nested` (freeing a 1,000-deep `OrderedDict`)
     traps in three classes, `PurePythonOrderedDictTests`, `PurePythonOrderedDictSubclassTests`
     and `CPythonOrderedDictSubclassTests` (EXECUTED on the built set, each by id; the other
     `test_highly_nested` and every `test_highly_nested_subclass` pass); under the old fuel-only
     driver the module passed (the review; the CPython-suite memo, 297). So Decision 3 turns them
     from passes into traps in 065's groups. Each becomes a trap entry, by full id, with question
     102 as its closer and "freeing a 1,000-deep `OrderedDict` needs more than 512 KiB on the
     runner's engine" as its reason. Whichever of 065 and this lands second writes those entries
     and restates the counts (eight trap entries under question 102). Any other test the engine
     change moves, in 065's groups or in numpy's and pandas' (spec 050), is listed by the builder
     the same way (criterion 6), never absorbed into a class.
   - **063.** 063 adds a gap entry for the Linux faulthandler crash, naming this specification as
     its closer, and a README line. Decision 9 closes it: the host no longer dies; the call is
     refused with a `RuntimeError` that names faulthandler. Whichever lands second restates that
     gap's check to expect "the host survives: the call is refused, or the trap is returned", and
     removes the gap; the README line becomes Decision 9's.
   - **069 and 055, in one file** (the review's F10). 069 changes `PREIMPORT` in
     `recipes/reactor_main.c`; 055 takes a strong reference to the bootstrap's turn function in
     `init_interpreter` and adds two exports; this adds a call right after
     `Py_InitializeFromConfig`. Whichever lands second rebases, with a conflict only if the hunks
     touch, and rebuilds (§5.7). The window does not depend on what the snapshot imports. Under
     055, a `RecursionError` inside a turn is an ordinary exception: it no longer ends the session,
     where today's trap does; 055's "a trap ends the session" loses this case.

9. **On Linux, the runner refuses each entry into the guest when wasmtime's trap handlers are not
   in place** (new scope, from spec 063's build review, F3; the confirmation's C1 to C4).
   - **The defect** (EXECUTED, the memo's A3; 063's probes; the confirmation's `confirm/d9-*.log`):
     on Linux, a `faulthandler.enable()` after the first engine, or a `faulthandler.disable()`
     after the first engine when it was enabled before, makes any guest trap kill the host with
     SIGILL (exit −4), on x86_64 and aarch64, glibc and musl alike. A Python-level
     `signal.signal(SIGSEGV, …)` after the first engine is worse: a trap hangs the host forever at
     full CPU, since the handler returns and the faulting instruction runs again. macOS is
     unaffected (wasmtime uses Mach ports there). pytest's own faulthandler plugin enables at
     session start, before any engine, so a plain pytest run is safe; an inline pytester session
     is not.
   - **The mechanism** (READ): wasmtime installs its handlers for `SIGSEGV`, `SIGILL` and, on
     x86_64, `SIGFPE` when the first engine is made, saving the previous ones. faulthandler's
     handler, installed later, runs first on a trap, restores wasmtime's and re-raises from
     inside `raise()`, outside wasm; wasmtime passes that signal to the default action. A later
     `disable()` restores what preceded faulthandler, the default, over wasmtime's.
   - **Where the check runs** (C2): at the top of `_drive`, before `_check_preopens` (which runs
     wasm of its own) and before `linker.instantiate`: so before every entry into guest code,
     each `run`, and each session turn under spec 055, which re-enters a living instance. 055 is
     in its build review: whichever of 055 and this lands second puts the same call at the top of
     055's turn path (its entry into the instance), so a faulthandler change between two turns is
     refused at the second.
   - **What it reads** (C3). On Linux only (`sys.platform.startswith("linux")`), a private
     function `_trap_handlers_ready()` reads, with `sigaction(sig, NULL, &old)` through `ctypes`,
     the handler of `SIGSEGV`, `SIGILL` and, on x86_64, `SIGFPE` (wasmtime 49's set, READ,
     `sys/unix/signals.rs:72–92`), and asks `dladdr` for the load base (`dli_fbase`) of the object
     that holds it. Each must equal the load base of wasmtime-py's own library, read once with
     `dladdr` of the address of `wasmtime._ffi.dll.wasm_engine_new`. No file is touched, so an
     upgraded or replaced wheel on disk changes nothing (the confirmation: it agreed with a
     path comparison in every case, at half the cost, 5 to 10 µs). The handler is read as the
     first pointer of `struct sigaction`, which glibc and musl both put first. **Any exception,
     and any failed `sigaction` or `dladdr`, counts as "not in place".**
   - **What it says** (C1, C4). It raises `RuntimeError` before any guest code runs. The message
     names the signal, the cause and the exact remedy: "wasmtime's handler for SIGILL was
     replaced after the first run, by a handler installed or removed since (faulthandler,
     signal.signal, or a native crash reporter); a trap in the guest would end or hang this
     process, so the call was refused. If faulthandler.enable() was called after the first run,
     faulthandler.disable() undoes it; otherwise restart the process, and install faulthandler or
     any crash reporter before the first run." `faulthandler.disable()` after a late `enable()`
     restores wasmtime's handlers (EXECUTED: the "enabled after, then disabled" order returns every
     trap); the other cases have no Python-level undo.
   - **Exact for faulthandler, conservative for any other late handler** (C1; EXECUTED, the memo's
     A3 and the confirmation's `d9-*.log`, x86_64 and aarch64, glibc and musl). For every
     faulthandler order the check agrees with the outcome: where the trap returns, those signals
     point into wasmtime's library; where the host dies, at least one points elsewhere
     (faulthandler's handler, in the `python` executable, or `SIG_DFL`). For any other handler
     installed after the first engine it is conservative: a native handler that chains with the
     fault's original context (as breakpad, crashpad and the JVM's libjsig do) lets the traps
     return, yet it is refused, because from its address it cannot be told from one that does not
     chain (which ends the host with its own exit code, EXECUTED). The README tells embedders to
     install crash reporters before the first run, which the check accepts (EXECUTED: a native
     handler installed before the first engine returns every trap). It costs three `sigaction`
     and three `dladdr` calls per entry, through `ctypes`, and no fuel.
   - **Why refuse, not warn or repair.** A warning would let the next trap end the process, and
     every other guest it is running. wasmtime's saved handler is fixed at the first engine, so
     putting its handler back on top would cut faulthandler out of the chain for the host's own
     crashes; calling `faulthandler.disable()` repairs one order and is the fatal step in another;
     and a Python callback cannot run in a fault's context. Refusing turns a dead or hung host into
     an exception the host can see, before the guest runs.
   - **Why not `signals_based_traps = False`.** It removes the defect outright (EXECUTED: every
     order returns the trap, fuel unchanged), but wasmtime then forces its heap and table Spectre
     mitigations off, silently when unset, and refuses the engine when they are set on (READ,
     `config.rs:3024–3043`): a loosening of the sandbox that is the owner's to decide (§4.15). It
     also moves the native frames by host (the memo's A3). It is recorded in the memo for a later
     decision, not taken here.
   - **What it does not cover.** The check is point-in-time: a handler change made during a call,
     by a host function on the calling thread (a provider, tool or door host that enables
     faulthandler or imports a library that installs a handler) or by another thread, is not
     caught for that call; the next entry refuses. Embedders that drive the artifacts with their
     own wasmtime are outside the runner (the README says what to do). Windows is INFERRED
     unaffected (wasmtime uses a vectored handler that faulthandler's continues to; the host may
     print a "Windows fatal exception" traceback): the release's Windows job runs criterion 11 and
     is the evidence.
   - No upstream change is needed. CPython's faulthandler could chain to a previous
     `SA_SIGINFO` handler with the fault's context instead of re-raising; the memo notes it and
     nothing here depends on it.

## Intent

At wasmtime's default stack, on both binaries and both release hosts measured, recursion that
runs through Python code raises `RecursionError` instead of ending the guest, except through
callbacks out of expat. What still traps (expat callbacks, C over very deep data, freeing very
deep structures, the parser, deep exception groups) is written down with the lower host's limits,
checked, and named as the owner's choice to close (question 102). And on Linux, a host whose
faulthandler would turn a guest trap into its own death gets a refused call instead.

## Design

```
recipes/reactor_main.c
  #define C_STACK_WINDOW (128 * 1024)   /* spec 071: CPython's guard watches the top 128 KiB */
  extern unsigned char __stack_high;    /* beside the existing __stack_low */
  init_interpreter():
    status = Py_InitializeFromConfig(&config);  ... (unchanged) ...
    if (PyStatus_Exception(status)) Py_ExitStatusException(status);
    if (PyUnstable_ThreadState_SetStackProtection(PyThreadState_Get(),
            &__stack_high - C_STACK_WINDOW, C_STACK_WINDOW) < 0) { PyErr_Print(); abort(); }
    ... (the rest unchanged)

src/wasi_python/runner.py
  _WASM_STACK = 512 * 1024   # spec 071: wasmtime's default, stated; the window is sized for it
  _engine(): cfg.max_wasm_stack = _WASM_STACK
  _trap_handlers_ready() -> str | None    # Linux only; None when ready, else the signal's name
  _drive(): first, before _check_preopens and linker.instantiate (every entry into the guest):
      if (bad := _trap_handlers_ready()) is not None: raise RuntimeError(<the message>)

tests/harness/guest.py
  engine(): cfg.consume_fuel = True; cfg.epoch_interruption = True; cfg.max_wasm_stack = 512 * 1024
  run():    store.set_epoch_deadline(2**40) beside store.set_fuel(...)
```

- The window's call sits after the core phase and before the main phase, so the zip's reader
  and the imports that follow already run under it. A two-line comment says why: the guard
  measures linear memory; wasmtime's native stack is separate and smaller.
- `_trap_handlers_ready` resolves `sigaction` and `dladdr` from the C library, and wasmtime-py's
  load base, once, lazily, the first time it runs on Linux; it reads into a buffer larger than any
  `struct sigaction`; any exception inside it answers "not ready" (the signal's name, or
  `"unknown"`). The
  signal set is a module constant with a comment naming wasmtime 49's source; a re-pin of
  wasmtime re-reads it (criterion 11 runs on both Linux hosts in the release).
- The checks' programs are the memo's and the review's case files, cut to what each criterion
  needs. Each prints one line: the outcome, the exception's message, and the depth reached,
  counted by a module global the recursive function increments.

## Scope

In: the above.

Out, each with its reason:
- A larger native stack in the runner, carried CPython patches, a smaller window: Decision 6,
  question 102.
- A knob for the window: Decision 2.
- `signals_based_traps = False`: Decision 9, the owner's (§4.15).
- A count of the guard in the record (`Completed`): the guest's `RecursionError` is the guest's,
  in its own output.
- Native CPython's depth (1,000) for recursion through Python code: it needs about 1.7 MB of
  native stack on the runner's engine, which Decision 3 refuses on a caller's thread.
- Python-to-Python recursion: it calls no C and already raises at the recursion limit (EXECUTED,
  996 frames, window or not).

## Acceptance criteria

Each check below is new and is written before the code. Each is seen failing first: on today's
set (the frozen `s-4eb5418a2b1bb553-c353b1d9`, where every shape of criterion 1 traps), or
against the stand-in named with it. Depths are counts; fuel is the check's metric where it runs
one program. **Every number here holds on both arm64 and x86_64** (the lane's ruling); criteria
1 to 4 and 11 run on every release host.

1. **Recursion through Python code raises, on both binaries.**
   `test_recursion_through_python_raises[<shape>-<binary>]` in
   `tests/checks/test_v1_2_hostile_guest.py`, through `wasi_python.run` at its defaults. Each
   program recurses until it is stopped, catches the exception, and prints its class, message
   and depth. The check asserts `trapped is None`, exit 0, the class, and a depth at least the
   measured depth less a tenth (a floor, so the window cannot shrink unseen; the depths are the
   same on both hosts):

   | shape | class, and the message's start | depth at least |
   |---|---|---|
   | `__repr__` returning `repr(self)` (the memo's first case) | `RecursionError`, "Stack overflow (used 112 kB)" | 190 |
   | `__getattr__` returning `getattr(self, k)` | the same | 190 |
   | `__eq__` returning `self == o` | the same | 215 |
   | `__hash__` returning `hash(self)` | the same | 195 |
   | `__str__`, `__format__`, `__iter__`, `__len__` the same way | the same | 210, 155, 190, 205 |
   | `map` with a lambda that maps itself | the same | 195 |
   | `sorted([1], key=k)` where `k` sorts again; `functools.cmp_to_key` | the same | 45 |
   | `min(key=…)`; `functools.reduce` | the same | 165; 220 |
   | `functools.lru_cache(None)` recursion | the same | 185 |
   | **`heapq.heapify` of two objects whose `__lt__` heapifies again** (the thinnest margin: 1.12 on x86_64) | the same | 215 |
   | a class whose `__repr__` returns `repr([self])` | the same | 180 |
   | `pickle.dumps` of an object whose `__reduce__` nests it | the same | 145 |
   | `pickle.dumps` of a recursive `functools.partial` (spec 065's `test_recursive_pickle`) | `RecursionError` | none (one call) |
   | `pickle.dumps` of a 100,000-deep nested list (structure kept, `os._exit` after) | `RecursionError` | none |
   | `re.sub` with a callback that substitutes again | the same as `__repr__` | 130 |
   | `np.vectorize`; `np.frompyfunc`; `np.apply_along_axis` recursion | the same | 85; 45; 90 |
   | pandas `Series.map` recursion | the same | 140 |
   | `eval("f()")` and `exec("f()")` recursion | `MemoryError`, "Parser stack overflowed" | 160; 140 |
   | `sys.setrecursionlimit(100000)`, then the `__repr__` case | the same as `__repr__` | 190 |

   The snapshot runs every row. The plain binary runs the `__repr__`, `lru_cache`, `heapq`,
   recursive `partial` and `setrecursionlimit` rows. Seen failing first: on today's set every row
   traps but pandas `Series.map`, which stops at the recursion limit (249 levels, "maximum
   recursion depth exceeded"), so its message fails the check (EXECUTED). Under the window it
   stops sooner, at 160: a path that was already safe loses depth.

2. **The window is 128 KiB.** `test_the_c_stack_window_is_128_kib`: the `__repr__` program's
   message is exactly `Stack overflow (used 112 kB)` (the window less CPython's 16 KiB guard),
   on both binaries; on the snapshot this is also the check that the window survived Wizer.
   Stand-in: the research binary without the window traps; with a 160 KiB window the message
   reads 144 kB (EXECUTED).

3. **wasmtime's default engine, and the CLI.** `test_recursion_raises_on_wasmtimes_default_engine`
   makes **its own** engine from a `wasmtime.Config` left at wasmtime's defaults (no fuel, no
   epoch, no stack set), compiles the snapshot there, and runs the `__repr__`, `lru_cache` and
   `np.frompyfunc` rows through `guest.run` with that module handed in (the review's F11: the
   driver gains an optional `module=` parameter, a judge change; its cached engine is never
   swapped). `RecursionError` each. This engine has more room than the runner's (the review:
   `ElementTree` needs 344 KiB on it against 576 KiB on the runner's, x86_64), so criterion 1 is
   the thin case and this one checks only that the window does not depend on fuel or epochs.
   And `test_recursion_raises_under_the_wasmtime_cli` (needs the pinned wasmtime CLI under
   `build/tools`; blocked, not failed, without it): `wasmtime run -W
   exceptions=y,unknown-imports-trap=y --invoke run` of the plain binary with the `__repr__`
   program exits 0 and prints `RecursionError`. Seen failing first: both trap on today's set
   (EXECUTED: the CLI exits 134).

4. **The limits of Decision 5 hold, and their traps are named and survived.**
   `test_deep_data_limits[<kind>]`, through `run` on the snapshot. Each kind runs a depth that
   completes and a depth (or an unbounded recursion) that ends with `trapped == "stack
   overflow"` and `exit_code is None`; then a third call in the same process prints `ok`. Each
   program builds its structure and acts on it; the free kind ends with `del`, the others with
   `os._exit(0)` so freeing is not what is measured. The completing depth sits at least a
   quarter below the lower host's edge; the trapping one at least 40% past the higher host's
   (EXECUTED, the memo's A1; freeing traps at 3,300, 42% past arm64's 2,324, the confirmation's
   C5):

   | kind | completes at | traps at | last good depth, arm64 / x86_64 |
   |---|---|---|---|
   | freeing a nested list | 1,500 | 3,300 | 2,324 / 2,033 |
   | `json.loads` of nested arrays | 800 | 2,000 | 1,204 / 1,121 |
   | `eval` of nested parentheses | 100 | 199 (the most CPython's tokenizer accepts) | 141 / 132 |
   | a `pyexpat` start-element handler that parses again | 60 levels, bounded | unbounded | 130 / 101 |
   | an `xml.sax` handler; an `ElementTree` target, each parsing again | 60 levels, bounded | unbounded: `RecursionError` (arm64, 118 and 122 levels) or the named trap (x86_64) | raises / 95; raises / 109 |

   The last row's trapping side accepts either outcome, since it differs by host; it asserts
   that the host survives and the third call works. The numbers are those the README states.
   Stand-in: run with `max_wasm_stack` at 2 MiB (on a thread with room) and the trapping depths
   complete or raise, so the check fails (INFERRED from the memo's sections 1 and 4; the expat
   rows from the review's margins, which are all under 700 KiB). The existing
   `test_a_stack_overflow_is_named` still passes unchanged (EXECUTED: its program still traps
   under the window, after about 38 G fuel).

5. **The stated engine.** `test_the_runner_states_its_wasm_stack` (a unit check in
   `tests/unit/test_runner_calls.py`): `_engine`'s config is made with `max_wasm_stack` equal
   to `512 * 1024`, read through a `wasmtime.Config` stand-in that records what is set, and
   `_WASM_STACK` is that number. The same stand-in shows that `guest.engine()` sets fuel, epoch
   interruption and the same stack. Criterion 4's pairs are the behavioural side: a different
   stack moves their trapping depths.

6. **Nothing else moves; what does is named** (the review's F6 and F3).
   - The full judge on the built set: no accepted pass lost, numpy's and pandas' own tests and
     spec 050's groups included. Decision 3's engine change runs in the same judge, so the
     builder reports any test it moves separately from the window's: it runs the upstream groups
     once with the new driver on today's set (engine change only) and once on the built set.
   - **CPython's own suite.** If 065 has landed, its `cpython-*` groups are this check. If not,
     the builder runs the CPython-suite memo's harness (`run_many.py` over every module, through
     the judge's new driver) on the built set and compares per-module passes with the memo's
     27,503: no pass may be lost but `test_ordered_dict`'s `test_highly_nested` (Decision 8),
     and any other loss is a finding before landing, not a derived class.
   - Fuel does not grow beyond noise (the window costs one call at start; on the snapshot it is
     paid at build time; the handler check costs no fuel). The builder records `-c pass` fuel on
     both binaries before and after. `sys.getrecursionlimit()` is still 1,000.

7. **The recipe is the only source change.** `recipes/patches/` is unchanged and the release's
   check that each tree equals its tarball plus the recorded patches passes (spec 020).
   `MANIFEST` records the recipe's new hash. The x86_64 rebuild gives the same bytes (spec 040).

8. **Docs.** README: the platform fact (a bullet after "No threads"), the fourth embedder step,
   the calling thread's stack, and the lines under *Safety* below, with the lower host's
   numbers; the CHANGELOG entry under 0.1.0a7. `test_rules.py` stays green.

9. **Spec 065.** As Decision 7 says, by landing order. On the built set each of the four
   `test_recursive_pickle` variants passes by full id, on arm64 and x86_64; the five others still
   trap with the named reasons and name question 102; `test_ordered_dict`'s
   `test_highly_nested` variants are trap entries by Decision 8.

10. **lxml's callbacks, measured on the built set** (the review's F4). The builder runs the four
    lxml shapes of Decision 5 at 512 KiB on the runner's engine on both hosts, unbounded and
    bounded, and finds each one's edge (last good depth) as the memo's `v2/edges_run.py` does.
    Each that raises is added to criterion 1 with its floor; each that traps is added to
    Decision 5's table and the README with the lower host's edge, and gets a criterion-4 pair. The
    landing notes carry the numbers. If the built set has no lxml (a profile without it), the
    check is blocked with that reason.

11. **Linux's faulthandler: the host survives** (Decision 9). `test_a_faulthandler_change_cannot_kill_the_host[<order>]`
    in `tests/checks/test_v1_2_hostile_guest.py`, each order in a fresh host process
    (`subprocess`, the host's own Python), running `wasi_python.run` twice: a warm call, then a
    change to faulthandler in the order named, then a guest that overflows its stack
    (`json.loads('[' * 200000 + ']' * 200000)`):

    | order | Linux | macOS and Windows |
    |---|---|---|
    | never enabled | `trapped == "stack overflow"` | the same |
    | enabled before the first call | the same | the same |
    | enabled after the first call | `RuntimeError` naming faulthandler; host exit 0 | `trapped == "stack overflow"` |
    | enabled before, disabled after | the same `RuntimeError`; host exit 0 | `trapped == "stack overflow"` |
    | enabled after, then disabled | `trapped == "stack overflow"` | the same |
    | `signal.signal(signal.SIGSEGV, h)` after the first call (a Python handler) | the same `RuntimeError`; host exit 0 | `trapped == "stack overflow"` |

    The child's exit is 0 in every row; each child has a 120 s limit, so the hang the last row
    causes today fails the row instead of the run. The message names the signal and, for the
    late-enable row, `faulthandler.disable()` as the remedy. Seen failing first: on Linux today, rows 3 and 4 kill the
    child with exit −4 and the last row hangs it at full CPU (EXECUTED, 063's `product_probe.log`,
    the memo's `sigprobe-*.log`, the confirmation's `d9-*.log`). A second-entry row runs the
    warm call, changes faulthandler, and makes a second call in the same process: refused, as a
    session's second turn would be once 055 has landed (Decision 9, "Where the check runs"). A
    unit check (`tests/unit/test_runner_calls.py`) feeds `_trap_handlers_ready` a stand-in for
    `sigaction` and `dladdr` and shows it names the first signal whose handler lies outside
    wasmtime's library (by load base), and treats a failed call or any exception as not ready. On macOS and Windows the function
    returns `None` without reading anything.

## README

After the "No threads" bullet of the platform facts:

> - **Deep recursion**: recursion that runs through Python code (a `__repr__` that calls
>   `repr(self)`, `lru_cache`, a `sort` key, a numpy or pandas callback) raises `RecursionError`
>   ("Stack overflow (used 112 kB)") after 40 to 250 levels, where native Python allows 1,000; a
>   program that recursed deeper than that and finished on an earlier release now raises.
>   wasmtime gives wasm frames 512 KiB of native stack, and CPython's guard watches only the C
>   stack in linear memory, so the guest narrows that guard to 128 KiB. Some recursion still ends
>   the call with the trap "stack overflow": a callback out of expat (`pyexpat`, `xml.sax`, an
>   `ElementTree` parser target) that parses again more than about 95 levels deep; freeing a
>   nested list more than about 2,000 deep (a dict 1,300); `json.loads` past 1,100 levels;
>   `repr` of nested lists past 1,800 and `==` past 1,350; source with more than 130 nested
>   brackets; an `ExceptionGroup` nested past 720. The trap ends only that call.

The fourth step of "Any other embedder does the same three things" (which becomes "four"):

> 4. **Give the guest at least 512 KiB of native stack** (`max_wasm_stack`, wasmtime's default),
>    on a host thread with room for it and for your own frames above it: wasm runs on the
>    calling thread's stack, and a limit larger than the thread can end the host process. With
>    it, recursion through Python code raises `RecursionError`, except through expat's
>    callbacks. More stack, on a thread that has it, lifts the limits above: 1 MiB covers nested
>    `repr` and `json.dumps` and the parser; 8 MiB covers `json.loads`, `==`, and freeing
>    10,000-deep structures. On Linux, install `faulthandler`, and any crash reporter or signal
>    handler for `SIGSEGV`, `SIGILL` or `SIGFPE`, before your first engine, or not at all:
>    enabling or disabling one later makes any guest trap kill or hang your process.

Under *Running it*, beside the runner's defaults: "`run` runs the guest on the calling thread,
with 512 KiB of wasm stack; call it from a thread with that much free above your own frames.
Python's threads have about 2 MB or more on every host, but an application that lowered
`threading.stack_size`, or an executor with small threads passed to `run_async`, may not."

*Safety*, "Enforced": "recursion through Python code raises `RecursionError`; the C-stack guard
watches 128 KiB, sized for the runner's 512 KiB wasm stack"; "on Linux, each entry into the guest
is refused with `RuntimeError`, before guest code runs, when wasmtime's trap handlers have been
replaced since the first call (by faulthandler, `signal.signal` or a native crash reporter
installed or removed after it), since a guest trap would then end or hang the process; install
faulthandler and crash reporters before the first call. The check is exact for faulthandler and
refuses some crash reporters that would have worked". "Not protected": "recursion in C over very deep data, callbacks out of expat,
and freeing very deep structures end the call with a stack-overflow trap (see the platform
facts); the next call is unaffected"; "on Linux, a handler change made during a call, by a host
function on the calling thread or by another thread (the next call is refused)".

## CHANGELOG (0.1.0a7)

> - **Deep recursion raises `RecursionError`** (spec 071). A `__repr__` that calls `repr(self)`,
>   `lru_cache` recursion, a recursive sort key or a numpy or pandas callback used to end the
>   guest in a wasm trap; it now raises, on both binaries, at wasmtime's default 512 KiB stack.
>   The guest narrows CPython's C-stack guard to 128 KiB with CPython's own
>   `PyUnstable_ThreadState_SetStackProtection`, called from the reactor's recipe: no patch.
>   **Changed:** such recursion stops at about half the depth it reached before trapping (214
>   levels for the `__repr__` case, 40 to 250 by shape), so a program that recursed that deep and
>   finished now raises. Callbacks out of expat, recursion in C over very deep data, and freeing
>   very deep structures still trap, with the limits the README lists. The runner now states its
>   wasm stack, 512 KiB, instead of taking wasmtime's default. `python.wasm`, the snapshot and
>   `MANIFEST` change; the zip does not.
> - **On Linux, a host's faulthandler can no longer turn a guest trap into the host's death**
>   (spec 071). If `faulthandler` was enabled or disabled after the runner's first call, a guest
>   trap used to kill the host with SIGILL (and after a late `signal.signal` for `SIGSEGV`, hang
>   it); `run` now refuses such a call with `RuntimeError` before the guest runs, says why, and
>   names the remedy. Install faulthandler and crash reporters before the first call, or not at
>   all.

## For the owner

Spec 065's five remaining trap entries (eight with Decision 8), and the limits of Decision 5,
close only by a choice this specification does not make (Decision 6). It is **question 102** in
`../questions-for-the-owner.md`: (a) a stack the runner owns, 8 MiB, on a thread of its own;
(b) carried CPython patches for WASI; (c) documented limits, as now; (d) a smaller window. The
facts and each option's cost are there. The research's lean, and the question's recommendation,
is (a).

`signals_based_traps = False` (Decision 9) would make the faulthandler order harmless outright,
at the price of wasmtime's Spectre mitigations for heap and table accesses; the memo's A3 has
the measurements, should the owner want it weighed.

## Disposition of the pre-build review

- **F1** (expat callbacks trap; x86_64 never measured). Kept 128 KiB, as the lane ruled.
  Decision 1 now gives the margins on both hosts (x86_64's 1.12 for `heapq` is the thinnest) and
  says why not a smaller window; Decision 5 lists `pyexpat`, `xml.sax` and `ElementTree`
  callbacks as known traps with both hosts' edges; criterion 4 checks them; question 102 has
  (d). "Every" and "any" are gone where they overclaimed (the Problem, Decisions 1 and 4, the
  Intent, README, CHANGELOG, question 102). The `heapq` row is in criterion 1.
- **F2** (arm64's numbers). Criterion 4's completing depths are now 1,500, 800 and 100, a quarter
  below x86_64's edges; its trapping depths sit 40% past arm64's; the README and Decision 5
  state the lower host's limits; every number was measured on both hosts (the memo's A1).
- **F3** (the judge's driver is roomier). `guest.engine()` sets epoch interruption and the stack
  (Decision 3), named as a judge change; Decision 8 puts `test_ordered_dict`'s
  `test_highly_nested` under question 102, coordinated with 065; criterion 6 separates what the
  engine change moves from what the window moves.
- **F4** (lxml). Decision 5 and criterion 10: the builder measures four lxml callback shapes on
  the built set, on both hosts. Rebased onto main `6fd89e0`.
- **F5** (065's text). Decision 7 rewritten for 065's nine entries: four close, five (six)
  remain under question 102; 065's present text agrees, and the first draft's Decision 7 is named
  as superseded.
- **F6** (CPython's suite). Criterion 6: 065's groups if landed, otherwise the memo's harness
  against the 27,503 passes; no pass lost but the one Decision 8 names.
- **F7** (CHANGELOG section). 0.1.0a7.
- **F8** (question 102). The false "every embedder" fact removed; option (a)'s threading costs
  completed (contextvars and thread-locals, `signal.signal`, the process-wide
  `threading.stack_size`, a caller's `executor`); option (d), a smaller window, added with its
  depth cost.
- **F9.** "40 to 250"; Decision 1, the README and the CHANGELOG say that programs that recursed
  between the new and the old depth now raise.
- **F10.** Decision 8 names 055 beside 069, and that a `RecursionError` in a turn no longer ends
  the session.
- **F11.** Criterion 3's check makes its own engine and hands its module to `guest.run` through a
  new optional parameter; the cached engine is never swapped.
- **N1 to N4.** No change asked. N2 is taken into the README (Decision 4). N1 (the window's
  bottom 8 KiB can now reach `Py_FatalError`, an "unreachable" trap): no shape here showed it,
  and criterion 1 would see one as a failure.
- **New scope (063's F3).** Decision 9, criterion 11, the memo's A3, the README and CHANGELOG
  lines.

## Disposition of the confirmation

The confirmation (the same file, section "Confirmation of 071's revision"; probes in
`scratchpad/071-review/confirm/`): "confirmed for build once C1 and C2 are written in".

- **C1.** Decision 9 says it is exact for faulthandler and conservative for any other late
  handler; the message names any late handler (faulthandler, `signal.signal`, a native crash
  reporter); the README asks for crash reporters before the first run; criterion 11 has the
  `signal.signal` row, which hangs the host today.
- **C2.** The check is the first thing `_drive` does, before `_check_preopens`, so it runs
  before every entry into the guest; 055's turn path gets the same call from whichever of 055
  and this lands second; *Not protected* names a change made during a call, on the calling
  thread or another. Criterion 11 has a second-entry row.
- **C3.** wasmtime's library is identified by load base (`dli_fbase` of `wasm_engine_new`); any
  exception counts as not ready.
- **C4.** The message's remedy is exact: `faulthandler.disable()` undoes a late enable; the other
  cases need a restart.
- **C5.** Freeing traps at 3,300.
- **C6.** The memo's closing sections no longer overclaim.

## Landing notes

### What was built

On `spec/071-deep-recursion-raises-recursionerror`, rebased onto main `6cc30bb` (spec 047
landed; frozen set `s-a8221564acc6afc3`, `SHA256SUMS` `0923cd6e…`):

- `74b6007`: the checks first, with the judge's changes: criteria 1 to 4 and 11 in
  `tests/checks/test_v1_2_hostile_guest.py`, criterion 5 and 11's units in
  `tests/unit/test_runner_calls.py`; `engine()` in `tests/harness/guest.py` makes the runner's
  engine (fuel, epoch interruption with a far-off deadline, 512 KiB) and `guest.run` takes
  `own=(engine, module)`; a `wasmtime cli` need (`tests/harness/needs.py`, `paths.wasmtime_cli`).
- `baa8ec0`: the code. `recipes/reactor_main.c`: `C_STACK_WINDOW` and the
  `PyUnstable_ThreadState_SetStackProtection` call after `Py_InitializeFromConfig`.
  `src/wasi_python/runner.py`: `_WASM_STACK`, `max_wasm_stack` in `_engine`,
  `_trap_handlers_ready` (Linux; `sigaction` and `dladdr` by load base) as the first thing
  `_drive` does, the message `_TRAP_HANDLERS_REPLACED`, and the two docstrings.
- `164e16d`: criterion 10's four lxml rows in criterion 1; README (the *Deep recursion* fact, the
  fourth embedder step, the calling thread, *Safety*'s lines, the generated reference) and the
  CHANGELOG under 0.1.0a7; the build's evidence beside the memo
  (`2026-10-18-deep-recursion-on-the-wasm-stack/v3/`).
- Then these notes.

The set, built from empty with `scripts/build.sh --plain` in the worktree (16 steps, 7 min 52 s;
`build/artifacts/`): `SHA256SUMS` `a48b92aa15c5c62f65de42dbf428f6d56bfcbe7b054e86c3aff228d0e5f361f5`;
`python.wasm` `ce65e305…` (41,092,491 bytes, 283 more than main's), `python-snapshot.wasm`
`c3b589b8…`, `MANIFEST` `71ab999f…`; the stdlib zip `02026895…` is main's, byte for byte.

### Seen failing first

- On main's set, with the branch's checks (`build/failfirst-main.log`): 35 of criteria 1 to 3
  fail, 33 of them `('stack overflow', b'')`, pandas `Series.map` with "maximum recursion depth
  exceeded" at 249, and the default-engine check with a trap. Criterion 4's pairs pass there, as
  documented limits must; their stand-in, a 2 MiB stack (`build/standin-c4.py`), completes or
  raises every trapping depth, so the check fails. The four lxml rows also trap on main's set.
- Criterion 11 on Linux aarch64 with main's runner and set (`v3/evidence/faulthandler-orders-main-arm64.log`):
  "after" and "before-then-disable" kill the child (exit 132, SIGILL), "signal-after" hangs it
  (killed at 120 s); on the branch (`…-branch-arm64.log`, `…-branch-amd64.log`, x86_64 under
  emulation) those three are refused with the message, and the other three return
  `trapped stack overflow`. On macOS all six return the trap (the judge's run).
- Criterion 5's and 11's units fail on main (no `_WASM_STACK`, no `_trap_handlers_ready`).

### The criteria

1. All 34 rows pass on both binaries where they run (the 26 of the spec, `heapq` among them,
   plus lxml's four, criterion 10). Depths equal the research's (`__repr__` 214).
2. The message is exactly "Stack overflow (used 112 kB)" on both binaries.
3. The default engine raises for `__repr__`, `lru_cache` and `np.frompyfunc`; the wasmtime
   49.0.3 CLI runs the plain binary's `__repr__` recursion to a `RecursionError`, exit 0.
4. All six pairs hold on arm64; the numbers were chosen against x86_64's edges (the memo's A1).
5. The unit checks pass.
6. **The judge** (`uv run pytest -n 3`, `build/judge-071.log`, `build/progress/latest.json`
   kept): `wasi_python v1: 488/505 pass · 14 gap · 3 blocked · 0 fail (unit suite 1256/1263,
   7 skipped)`; `1744 passed, 10 skipped, 14 xfailed in 373.34s`; `ratchet vs 7511a10187: lost 0
   · absent 0 · unrun 0 · unrun locally 1 · gained 52 · grew 63 · judge changed:
   tests/checks/test_v1_2_hostile_guest.py, tests/harness/guest.py, tests/harness/needs.py and 2
   more`. The 52 gained are the new checks. numpy's and pandas' groups lose nothing under the new
   driver engine and the window together, so nothing needed the engine-only run criterion 6 kept
   for attributing a loss. **CPython's suite** (065 not on main): the memo's harness over all 557
   modules on the built set through the new driver (`build/cpy071/`,
   `v3/evidence/cpython-suite-vs-memo.txt`): 27,534 passes against the memo's 27,503. One module
   lost passes, `test_ordered_dict` (297 to 0, a trap: the three `test_highly_nested` variants of
   Decision 8, EXECUTED each by id, `v3/evidence/test-ordered-dict-variants.txt`); one gained,
   `test_functools` (0 to 328: the four `test_recursive_pickle` variants pass by id,
   `v3/evidence/test-recursive-pickle-variants.txt`). `test_doctest`, `test_exceptions`,
   `test_syntax` and `test_traceback` still trap, as Decision 7 says. Start fuel for `-c pass`:
   snapshot 83,535,208 on main's set, 83,485,437 here (−0.06%); plain 167,257,284 and 167,320,292
   (+0.04%). `sys.getrecursionlimit()` is 1,000.
7. `recipes/patches/` is unchanged; the rules and the patch checks pass in the judge.
8. README and CHANGELOG as above; `test_rules.py` and the API reference pass.
9. Recorded for spec 065 (not on main): on this set the four `test_recursive_pickle` variants
   pass by id; `test_doctest`'s `test_issue35753`, `test_exceptions`'
   `test_recursion_in_except_handler`, both `test_syntax` entries and `test_traceback` still trap;
   `test_ordered_dict`'s three `test_highly_nested` variants now trap. Whichever of 065 and this
   lands second removes the four, keeps the five and adds the three, each under question 102.
10. lxml's four shapes raise on both hosts, at 67, 81, 86 and 77 levels (target, XPath extension,
    resolver, XSLT extension), with margins 1.73, 1.78, 1.49 and 1.45 on x86_64 and 1.83, 2.00,
    1.60 and 1.56 on arm64 (`v3/evidence/lxml-*.jsonl`); so they are criterion 1 rows, floors 60,
    70, 75 and 65, and no README limit.
11. As in "Seen failing first".

### Growth, with its measured reason

63 metrics grew past the ratchet's tolerance (87 grew at all; 36 shrank): one binary's bytes and
fuel. All are within +0.24% (the largest: `test_a_pandas_warning_names_the_callers_line[snapshot]`,
+238,019 fuel, +0.24%; `test_upstream_suite[pandas-groupby]`, +217,416,915, +0.05%); the
binary grew 283 bytes (`test_binary_is_a_core_wasm_module[plain]`), the recipe's call and its
comment-free strings. Reason: a new `python.wasm` and snapshot. The plain binary's start runs one
more call (+63,008 fuel for `-c pass`); the snapshot's start is 49,771 fuel cheaper; elsewhere the
guest's memory layout differs by the relinked binary, so work that depends on addresses (hashing
of objects by id, the allocator's arenas, the collector's timing) moves a few parts in ten
thousand either way: the largest shrink is −0.14% (`test_npy_files_round_trip[snapshot]`) and
`numpy-core` is 159 M fuel cheaper. The engine change does not move fuel: fuel counts wasm
operators, and epoch checks are native code. The handler check costs no fuel.

### For the lane

- `--accept-judge "spec 071: the judge's driver makes the runner's engine (fuel, epoch
  interruption, 512 KiB); new checks for deep recursion, the window, the default engine and the
  CLI, the deep-data limits, the stated engine and Linux's faulthandler orders; a wasmtime cli
  need"`.
- `--accept-growth "spec 071's rebuilt python.wasm and snapshot (one recipe call): fuel moves a few
  parts in ten thousand either way with the relinked binary's layout, at most +0.24%; the plain
  start +63,008 fuel; the plain binary +283 bytes"`.
- **063's faulthandler gap** (`test_a_guest_trap_cannot_kill_a_host_that_enabled_faulthandler`,
  digest `b5a565e2e3c0`) is not on main at `6cc30bb`, so 063 lands after this and restates that
  check at its landing to "the host survives: the call is refused, or the trap is returned"; this
  branch's criterion 11 is the evidence. If 063 lands first, this branch does it at its rebase.
- **055** is not on main at `6cc30bb`: whichever lands second puts `_trap_handlers_ready()` at the
  top of 055's turn path (its entry into a living instance), with the same `RuntimeError`.
- **065**: criterion 9 above.
- The judge printed one `PytestUnraisableExceptionWarning` (a `KeyboardInterrupt` inside a store's
  `__del__`, from wasmtime-py's `_managed.py`), a warning, no failure; it names no check of this
  specification (INFERRED: a Ctrl-C check's interrupt landing in a worker's collector under
  `-n 3`).

### Departures from the specification, each with its reason

- **Criterion 1's message pattern** accepts "used 112 kB" or "used 113 kB": `sorted(key=…)` and
  `cmp_to_key` measure 113 kB at the check (the research's `counted-L131072.jsonl`); criterion 2
  still pins exactly 112 kB for `__repr__`.
- **Criterion 11's Python-handler row** installs `signal.signal(signal.SIGILL, …)`, not
  `SIGSEGV`: the guest's stack-overflow trap raises `SIGILL`, so that is the handler that hangs
  the host today (EXECUTED); a late `SIGSEGV` handler is refused all the same, by the same check.
- **Criterion 11's second-entry row** is the "after" row, which is a second call in one process;
  a session's second turn waits for 055 (above).
- **Criterion 3's driver parameter** is `own=(engine, module)`, since a store needs the module's
  engine too; such a run counts no fuel.
- **Decision 8** named one `test_ordered_dict` variant; the build found three, written into
  Decisions 7 and 8 and criterion 9.
- **Criterion 10** added four rows to criterion 1 and nothing to Decision 5, as it provides for
  shapes that raise.
