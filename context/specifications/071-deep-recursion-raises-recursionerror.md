# 071 — Deep recursion raises RecursionError instead of trapping the guest

- **Status:** drafted 2026-10-18; awaiting its pre-build review. It changes the artifact set and
  the build recipe (`recipes/reactor_main.c`), so §5.6 asks for a review before it is built.
- **Owner:** Clay Gendron
- **Kind:** **build-class** (it touches `recipes/`): one call added to `recipes/reactor_main.c`,
  so `python.wasm`, the snapshot and `MANIFEST` change once; the stdlib zip does not. With it,
  small parallel-safe parts: one stated setting in `src/wasi_python/runner.py` (`_engine`), the
  same in the judge's guest driver (`tests/harness/guest.py`), new checks in
  `tests/checks/test_v1_2_hostile_guest.py` and `tests/unit/test_runner_calls.py`, `README.md`,
  `CHANGELOG.md`. A judge change (new checks, the judge's driver). No carried patch:
  `recipes/patches/` does not change, and CPython stays exactly its tarball. **No line of `tests/public_api.txt` changes**: no name,
  signature, default or docstring of the public API moves.
- **Depends on:** 003 (the reactor and its `init_interpreter`), 016 (a trap named by its kind:
  "stack overflow"), 049 (the public API frozen), all landed. 065 (CPython's own tests in the
  release, drafted) and 069 (the snapshot pre-imports no package, build-class, in flight) meet
  this one: Decision 7 and Decision 8.
- **Research it stands on:**
  - `../research/2026-10-18-deep-recursion-on-the-wasm-stack.md` and its evidence folder
    (EXECUTED: the two stacks and their sizes, native and linear bytes a level for about 40
    shapes, the window swept on a relinked research binary and its snapshot, wasmtime's default engine, the
    wasmtime CLI, spec 065's five trap entries by stack, a host crash from a stack the thread
    does not have; READ: CPython's guard, wasi-libc's `pthread_getattr_np`, the host thread
    sizes);
  - `../research/2026-10-18-cpythons-own-tests-under-the-runtime.md`, finding 4.1 (the defect
    and its first two cases) and section 8, item 1.

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
  16 KiB of the bottom ("Stack overflow (used 16368 kB)" at a 64 MiB native stack). The earlier
  memo's 4 MB was inferred and is wrong.
- wasmtime runs every wasm call on its **native stack**, 512 KiB by default (EXECUTED: the same
  depth and fuel with `max_wasm_stack = 524288` as without it; wasmtime-py's docstring says
  2 MB, which is stale).
- Each level spends native and linear bytes in a ratio fixed by its shape: 2 to 3 to 1 for
  recursion through Python code, up to 25 to 1 for C over nested data. So the native
  stack is gone long before CPython looks: the `__repr__` case uses 222 KB of its 16 MiB window
  when it traps. A chain of frees (a nested list going out of scope) moves the linear stack not
  at all, so CPython's trashcan, which measures the same pointer, never starts.

## Decisions

1. **CPython's C-stack window is the top 128 KiB of the linear stack, set by the recipe through
   CPython's own API.**
   - `init_interpreter` in `recipes/reactor_main.c` calls
     `PyUnstable_ThreadState_SetStackProtection(PyThreadState_Get(), &__stack_high - 131072,
     131072)` right after `Py_InitializeFromConfig` succeeds, and aborts if it fails (it cannot
     with this size; the minimum is 24 KiB). The snapshot carries the window from its build; the
     plain binary sets it at its own start. The guest has no subinterpreters and no threads, so
     the main thread's state is the only one (EXECUTED, the memo's section 2).
   - **Why a window, and why this call.** The guard then raises while wasmtime's default stack
     still has room. CPython documents the call for embedders whose stack is not the one the OS
     reports (`Doc/c-api/threads.rst:754`), which is this case exactly. It is a recipe file, not
     a patch (§4.1): CPython's tree stays its tarball.
   - **Why 128 KiB.** Swept on a research binary at wasmtime's default stack (the memo's section
     2): at 128 KiB and 160 KiB every Python-through-C shape measured raises (23 of them; the
     24th, `json.dumps` with a `default=` hook, spends most of each level in C and stays a limit
     of Decision 5); at 192 KiB `lru_cache` recursion traps again (ratio 3.1). 128 KiB is a
     quarter of the native stack, with about a quarter of margin over the worst shape, for
     engines and wasmtime versions whose frames differ (wasmtime's default engine has frames a
     fifth smaller; wasmtime 50 could not be measured: the memo's section 7).
   - **Why not a smaller `-z stack-size`.** It would move the guard the same way but also take
     real linear space from C code with large locals. The window keeps the 16 MiB and moves only
     the guard.
   - **What it costs.** Recursion through Python code now stops at about half the depth where it
     used to trap: `__repr__` 214 levels (416 before), `lru_cache` 208 (306), `np.vectorize` 99
     (171), `sorted(key=…)` 52 (247), pandas `Series.map` 160 (249, where the recursion limit
     already stopped it). Native CPython stops all of them at its recursion limit, 1,000. The
     message is CPython's: `RecursionError: Stack overflow (used 112 kB)`. `eval` and `exec`
     recursion raise CPython's parser error, `MemoryError: Parser stack overflowed`, at 183 and
     157 levels. Ordinary work does not notice: the memo's workload of numpy, pandas, sqlite3,
     json, pickle, `re`, compiling 300 functions and matplotlib writes at most 27.6 KB of linear
     stack and costs the same fuel within 0.02%. No memory changes.

2. **The window is fixed; no knob.**
   - A wider window helps only an embedder whose native stack is at least 25 times it, since
     data shapes (`json.loads`, `==`) need that ratio to raise rather than trap (the memo's
     section 4). For a stack `S` the window that keeps both kinds safe is `max(128 KiB, S/32)`,
     so a knob would matter only above 4 MiB.
   - **Why not now.** It would be a new contract the guest reads from its environment, with no
     user in this repository. An embedder with a large stack keeps every protection; it gets
     Python-through-C depth of about 214, not 1,000. If a later change gives the runner a stack
     above 4 MiB (Decision 6), that change adds the knob with it, and this formula is its
     starting point.

3. **The runner and the judge state their stack: 512 KiB, wasmtime's default, set explicitly.**
   - `_engine` in `src/wasi_python/runner.py` sets `cfg.max_wasm_stack = 512 * 1024` (a private
     constant `_WASM_STACK`, with a comment naming this specification). The judge's guest driver
     does the same (`engine()` in `tests/harness/guest.py`), so every check that runs Python runs
     at the contract's stack. The engines in `tests/harness/files.py` run small WAT modules, not
     Python, and stay as they are.
   - **Why state it.** The window is sized for it. wasmtime-py's docstring names another default,
     and a wasmtime that changed its default must not change the guest's behaviour without a
     specification. Compiled modules are unaffected: `max_wasm_stack` is not part of the code, and
     the cached `.cwasm` files deserialize under other stacks (EXECUTED, the memo's probes ran on
     the runner's cache).
   - **Why not larger.** A synchronous call runs wasm on the calling thread's own stack; wasmtime's
     limit stops only wasm. A 64 MiB limit on the main thread killed the host process with
     SIGSEGV, with no trap and no output (EXECUTED, the memo's section 5). `python.exe` on Windows
     reserves 2,000,000 bytes for its main thread and its threads (READ), so even 2 MiB is not
     safe there, and an application that embeds Python sets its own. wasmtime-py's apparent
     2 MiB cap is not the limit (an exported setter lifts it; EXECUTED); the host thread is.
   - No `run()` option for it: a larger stack needs a thread the runner owns (Decision 6).

4. **The embedder contract names the stack.** The README's "Any other embedder does the same
   three things" gains a fourth: give the guest at least 512 KiB of native stack
   (`max_wasm_stack`; wasmtime's default), on a host thread with room for it and for the host's
   own frames above it. With that, recursion through Python code raises `RecursionError`.
   A larger stack, on a thread that has it, also lifts the limits of Decision 5, with the memo's
   table: the data shapes then raise and the frees complete. 1 MiB covers nested `repr` and
   `json.dumps` and the parser; 8 MiB covers `json.loads`, `==` and freeing 10,000-deep
   structures.

5. **What still traps is documented, and its limits are checked.**
   - At 512 KiB, with the window (EXECUTED: depths bisected in the memo's section 1, unchanged by
     the window but for `pickle`; the parser and exception groups bisected under it, section 2):
     - freeing a nested `list`, `tuple` or `frozenset` more than about 2,300 deep, a nested `dict`
       more than about 1,400 deep (natively these free without limit);
     - recursion in C over deep data: `repr` or `str` of a nested list past about 1,900 levels,
       `json.dumps` past 1,470, `json.loads` past 1,200, `==` past 1,550, `hash` of a nested
       tuple past 2,500 (natively a crash at 100,000), a chain of `map` objects past 2,950
       (natively a crash), `json.dumps` with a `default=` hook that nests past 1,080;
     - the parser: source with more than about 140 nested brackets (natively `SyntaxError` at
       200), or more than 3,200 nested unary operators;
     - printing an `ExceptionGroup` nested more than about 830 deep.
   - **Why documented, not fixed here.** No window can see a chain of frees, and the data shapes
     and the parser need either more native stack than a caller's thread promises (Decision 3)
     or source changes to CPython (Decision 6). Constitution §4.11: a platform's semantics are
     documented, not disguised.
   - **Checked as limits** (criterion 4): a pair per kind, one depth that completes and one that
     ends in the named trap, so the numbers in the README stay true and a trap stays a reported
     trap the next call survives.

6. **Not in this specification: a larger runner stack, and carried CPython patches.** Each
   would close what Decision 5 lists; each is a separate decision with a cost this one does not
   pay. The section "For the owner" puts the choice.
   - **A stack the runner owns.** The runner would run each guest on a thread of its own, made
     with `threading.stack_size`. 2 MiB closes spec 065's five trap entries; 8 MiB closes the
     data shapes and 10,000-deep frees (EXECUTED, the memo's sections 3 and 4). But `run`'s host
     functions (the door, providers, tools) would then run on that thread, and the README
     promises "A provider runs synchronously on the thread that runs the guest" and handles
     Ctrl-C on the main thread: a change to the runner's documented behaviour, not a setting.
   - **Carried patches** (INFERRED, not built: the memo's section 6): a depth count in
     `_Py_Dealloc` on WASI (CPython 3.13's trashcan counted), a smaller WASI `MAXSTACK` in the
     parser, a count in `Py_EnterRecursiveCall` on WASI like 3.13's `Py_C_RECURSION_LIMIT`. They
     would protect every embedder at wasmtime's default stack. But upstream's answer for WASI is
     a large runtime stack (its CI sets 32 MiB), so §4.1's "temporary" may never come.

7. **Spec 065's trap entries: one closes, four are renamed.**
   - The window closes `test_functools`' `test_recursive_pickle` (EXECUTED, the memo's section 3).
     The other four still trap at 512 KiB, each now for a named reason:
     - `test_doctest`'s `test_issue35753`: freeing a 1,000-long chain of `_Call` objects;
     - `test_exceptions`' `test_recursion_in_except_handler`: freeing what the handlers chained;
     - `test_syntax`'s `test_error_on_parser_stack_overflow`: the parser's own limit, `MAXSTACK`
       4,000 on WASI, needs more than 512 KiB;
     - `test_traceback`, whole module: printing and freeing deep exception groups.
   - Their closer becomes the owner's answer to the choice in "For the owner" (the file
     `context/questions-for-the-owner.md`, where the lane numbers it), since what closes them is
     Decision 6's choice.
   - **If 065 lands first,** this builder removes `test_recursive_pickle`'s trap gap and retires
     its trap check (spec 050's condition C1: the check passes on this set), and rewrites the four
     reasons and closers, with `--accept-judge "<reason>"`. **If this lands first,** 065's builder
     derives on this set: four trap entries, with these reasons.

8. **Spec 069 meets this one in one file.** 069 changes `PREIMPORT` in `recipes/reactor_main.c`;
   this adds a call in `init_interpreter`. Whichever lands second rebases, with a conflict only
   if the hunks touch, and rebuilds (§5.7: build-class changes land one at a time). The window
   does not depend on what the snapshot imports.

## Intent

At wasmtime's default stack, for any embedder and on both binaries, recursion that runs through
Python code raises `RecursionError` instead of ending the guest. What still traps (C over very
deep data, freeing very deep structures, the parser, deep exception groups) is written down with
its limits, checked, and named as the owner's choice to close.

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

tests/harness/guest.py
  engine(): cfg.max_wasm_stack = 512 * 1024
```

- The call sits after the core phase and before the main phase, so the zip's reader and the
  imports that follow already run under the window. The comment above it says why in two
  lines: the guard measures linear memory; wasmtime's native stack is separate and smaller.
- `__stack_high` is defined by wasm-ld, as `__stack_low` (already used by `clear_unused_stack`) is.
- The checks' programs are the memo's case files, cut to what each criterion needs. Each prints
  one line: the outcome, the exception's message, and the depth reached, counted by a module
  global the recursive function increments.

## Scope

In: the above.

Out, each with its reason:
- A larger native stack in the runner, and any carried CPython patch: Decision 6.
- A knob for the window: Decision 2.
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
one program.

1. **Recursion through Python code raises, on both binaries.**
   `test_recursion_through_python_raises[<shape>-<binary>]` in
   `tests/checks/test_v1_2_hostile_guest.py`, through `wasi_python.run` at its defaults. Each
   program recurses until it is stopped, catches the exception, and prints its class, message
   and depth. The check asserts `trapped is None`, exit 0, the class, and a depth at least the
   memo's less a tenth (a floor, so the window cannot shrink unseen):

   | shape | class, and the message's start | depth at least |
   |---|---|---|
   | `__repr__` returning `repr(self)` (the memo's first case) | `RecursionError`, "Stack overflow (used 112 kB)" | 190 |
   | `__getattr__` returning `getattr(self, k)` | the same | 190 |
   | `__eq__` returning `self == o` | the same | 215 |
   | `__hash__` returning `hash(self)` | the same | 195 |
   | `__str__`, `__format__`, `__iter__`, `__len__` the same way | the same | 155 to 210 (each the memo's less a tenth) |
   | `map` with a lambda that maps itself | the same | 195 |
   | `sorted([1], key=k)` where `k` sorts again; `functools.cmp_to_key` | the same | 45 |
   | `min(key=…)`; `functools.reduce` | the same | 165; 220 |
   | `functools.lru_cache(None)` recursion | the same | 185 |
   | a class whose `__repr__` returns `repr([self])` | the same | 180 |
   | `pickle.dumps` of an object whose `__reduce__` nests it | the same | 145 |
   | `pickle.dumps` of a recursive `functools.partial` (spec 065's `test_recursive_pickle`) | `RecursionError` | none (one call) |
   | `pickle.dumps` of a 100,000-deep nested list (structure kept, `os._exit` after) | `RecursionError` | none |
   | `re.sub` with a callback that substitutes again | the same as `__repr__` | 130 |
   | `np.vectorize`; `np.frompyfunc`; `np.apply_along_axis` recursion | the same | 85; 45; 90 |
   | pandas `Series.map` recursion | the same | 140 |
   | `eval("f()")` and `exec("f()")` recursion | `MemoryError`, "Parser stack overflowed" | 160; 140 |
   | `sys.setrecursionlimit(100000)`, then the `__repr__` case | the same as `__repr__` | 190 |

   The snapshot runs every row. The plain binary runs the `__repr__`, `lru_cache`, recursive
   `partial` and `setrecursionlimit` rows (the others cost seconds each to import there and test
   nothing the snapshot does not). Seen failing first: on today's set every row traps but pandas
   `Series.map`, which stops at the recursion limit (249 levels, "maximum recursion depth
   exceeded"), so its message fails the check (EXECUTED). Under the window it stops sooner, at
   160: a path that was already safe loses depth.

2. **The window is 128 KiB.** `test_the_c_stack_window_is_128_kib`: the `__repr__` program's
   message is exactly `Stack overflow (used 112 kB)` (the window less CPython's 16 KiB guard),
   on both binaries. Stand-in: the research binary without the window traps; with a 160 KiB
   window the message reads 144 kB (EXECUTED).

3. **Any engine, any embedder.** `test_recursion_raises_on_wasmtimes_default_engine`: the
   judge's own driver with a `wasmtime.Config` left at wasmtime's defaults (no fuel, no epoch,
   no stack set) runs the `__repr__`, `lru_cache` and `np.frompyfunc` rows on the snapshot:
   `RecursionError` each. (`np.vectorize` is left out: on that engine it already stops at the
   recursion limit, EXECUTED.) And `test_recursion_raises_under_the_wasmtime_cli` (needs the pinned
   wasmtime CLI under `build/tools`; blocked, not failed, without it): `wasmtime run -W
   exceptions=y,unknown-imports-trap=y --invoke run` of the plain binary with the `__repr__`
   program exits 0 and prints `RecursionError`. Seen failing first: both trap on today's set
   (EXECUTED: the CLI exits 134).

4. **The limits of Decision 5 hold, and their traps are named and survived.**
   `test_deep_data_limits[<kind>]`, through `run` on the snapshot. Each kind runs a depth that
   completes and a depth that ends with `trapped == "stack overflow"` and `exit_code is None`;
   then a third call in the same process prints `ok`. Each program builds its structure and acts
   on it; the free kind ends with `del`, the others with `os._exit(0)` so freeing is not what is
   measured:

   | kind | completes at | traps at | the memo's last good depth |
   |---|---|---|---|
   | freeing a nested list | 2,000 | 3,000 | 2,325 |
   | `json.loads` of nested arrays | 1,000 | 2,000 | 1,204 |
   | `eval` of nested parentheses | 120 | 150 | 141 |

   The numbers are those the README states. Stand-in: run with `max_wasm_stack` at 2 MiB (on a
   thread with room) and the trapping depths complete or raise, so the check fails (INFERRED from
   the memo's sections 1 and 4: 3,000 frees need about 0.7 MB, 2,000 `json.loads` levels about
   0.9 MB, and 199 parentheses raise `MemoryError` at 1 MiB). The existing `test_a_stack_overflow_is_named` still passes unchanged
   (EXECUTED: its program still traps under the window, after about 38 G fuel).

5. **The stated stack.** `test_the_runner_states_its_wasm_stack` (a unit check in
   `tests/unit/test_runner_calls.py`): `_engine`'s config is made with `max_wasm_stack` equal
   to `512 * 1024`, read through a `wasmtime.Config` stand-in that records what is set, and
   `_WASM_STACK` is that number. Criterion 4's pair is the behavioural side: a different stack
   moves its trapping depth.

6. **Nothing else moves.** The full judge on the built set: no accepted pass lost, numpy's and
   pandas' own tests and spec 050's groups included (a test that recursed deeper than the window
   allows would show here, and is a finding before landing). Fuel does not grow beyond noise
   (the window costs one call at start; on the snapshot it is paid at build time). The builder
   records `-c pass` fuel on both binaries before and after, and the plain binary's start fuel.
   `sys.getrecursionlimit()` is still 1,000.

7. **The recipe is the only source change.** `recipes/patches/` is unchanged and the release's
   check that each tree equals its tarball plus the recorded patches passes (spec 020).
   `MANIFEST` records the recipe's new hash. The x86_64 rebuild gives the same bytes (spec 040).

8. **Docs.** README: the platform fact (a bullet after "No threads"), the fourth embedder step,
   and one line each under *Safety*'s "Enforced" and "Not protected", with the numbers above;
   CHANGELOG 0.1.0a6 entry. `test_rules.py` stays green.

9. **Spec 065.** As Decision 7 says, by landing order. If 065 has landed, its
   `test_recursive_pickle` trap check passes on the built set and its gap and check go; the four
   others still trap with the named reasons.

## README

After the "No threads" bullet of the platform facts:

> - **Deep recursion**: recursion that runs through Python code (a `__repr__` that calls
>   `repr(self)`, `lru_cache`, a `sort` key, a numpy or pandas callback) raises `RecursionError`
>   ("Stack overflow (used 112 kB)") after 50 to 250 levels, where native Python allows 1,000.
>   wasmtime gives wasm frames 512 KiB of native stack, and CPython's guard watches only the C
>   stack in linear memory, so the guest narrows that guard to 128 KiB. Recursion in C over very
>   deep data still ends the call with the trap "stack overflow": freeing a nested list more than
>   about 2,300 deep (a dict 1,400), `json.loads` past 1,200 levels, `repr` or `==` of nested
>   lists past 1,500, source with more than 140 nested brackets, an `ExceptionGroup` nested past
>   830. The trap ends only that call.

The fourth step of "Any other embedder does the same three things" (which becomes "four"):

> 4. **Give the guest at least 512 KiB of native stack** (`max_wasm_stack`, wasmtime's default),
>    on a host thread with room for it and for your own frames above it: wasm runs on the
>    calling thread's stack, and a limit larger than the thread can end the host process. With
>    it, recursion through Python code raises `RecursionError`. More stack, on a thread that has
>    it, lifts the data limits above: 1 MiB covers nested `repr` and `json.dumps` and the
>    parser; 8 MiB covers `json.loads`, `==`, and freeing 10,000-deep structures.

*Safety*, "Enforced": "recursion through Python code raises `RecursionError`; the C-stack guard
watches 128 KiB, sized for the runner's 512 KiB wasm stack". "Not protected": "recursion in C
over very deep data, and freeing very deep structures, end the call with a stack-overflow trap
(see the platform facts); the next call is unaffected".

## CHANGELOG (0.1.0a6)

> - **Deep recursion raises `RecursionError`** (spec 071). A `__repr__` that calls `repr(self)`,
>   `lru_cache` recursion, a recursive sort key or a numpy or pandas callback used to end the
>   guest in a wasm trap; it now raises, on both binaries and under any embedder that keeps
>   wasmtime's default 512 KiB stack. The guest narrows CPython's C-stack guard to 128 KiB with
>   CPython's own `PyUnstable_ThreadState_SetStackProtection`, called from the reactor's recipe:
>   no patch. Such recursion stops at about half the depth it reached before trapping (214 levels
>   for the `__repr__` case). The runner now states its wasm stack, 512 KiB, instead of taking
>   wasmtime's default. Recursion in C over very deep data, and freeing very deep structures,
>   still trap, with the limits the README lists. `python.wasm`, the snapshot and `MANIFEST`
>   change; the zip does not.

## For the owner

Spec 065's other four trap entries, and the limits of Decision 5, close only by a choice this
specification does not make (Decision 6). The text for `context/questions-for-the-owner.md`,
numbered by the lane:

> Deep data recursion, freeing deep structures, the parser and deep exception groups still trap
> at wasmtime's default stack (spec 071's limits; four of spec 065's trap entries). Which closes
> them? (a) The runner runs each guest on a thread of its own with an 8 MiB stack, and the
> README asks other embedders for the same: it closes all four entries (2 MiB is enough for
> them) and every data limit measured but 100,000-deep frees, a 100,000-term expression and the
> two shapes that crash native CPython too, with no change to CPython; but
> `run`'s host functions then run on the runner's thread, not the caller's. (b) Carry CPython
> patches for WASI (a depth count in `_Py_Dealloc`, a smaller parser `MAXSTACK`, a count in
> `Py_EnterRecursiveCall`): every embedder is covered at wasmtime's default stack, but the
> patches diverge from upstream, whose WASI answer is a larger stack, perhaps for good.
> (c) Keep them as documented limits.

The research's lean is (a): it needs no divergence from CPython, it is what upstream's own WASI
CI does, and it reaches furthest. (b) is the choice if embedders that keep wasmtime's default
must be covered too.

## Landing notes

Not built yet.
