# Deep recursion on the wasm stack: why it traps, and what fixes how much

- **Status:** executed, 2026-10-18 (scratch binaries and runs in a scratch folder; nothing in the
  repository or the main tree's `build/` was changed by it).
- **Owner:** Clay Gendron
- **Researcher:** a research agent (Claude Opus 5.5), drafting spec 071.
- **Feeds:** spec 071, deep recursion raises `RecursionError` instead of trapping the guest; spec
  065 (its five trap entries).
- **Stands on:** `2026-10-18-cpythons-own-tests-under-the-runtime.md`, finding 4.1 (the defect,
  its first cases, and the cause it inferred).
- **Evidence:** beside this memo, `2026-10-18-deep-recursion-on-the-wasm-stack/`. The scripts
  (`probe.py`, the case files, `cpy071.py`, `export_sp.py`, `research_main.c` and its diff) and
  `evidence/`, whose `INDEX.txt` names what each output shows. Every run is against the frozen set
  `build/sets/s-4eb5418a2b1bb553-c353b1d9`, read in place, or a scratch binary relinked from it
  (`evidence/relink.txt`).

Terms used below:

- The **linear stack** is the C stack the compiler keeps in the guest's linear memory: 16 MiB at
  the bottom of memory (`-z stack-size=16777216 -Wl,--stack-first`). A C function uses it only
  for locals whose address is taken.
- The **native stack** is the machine stack wasmtime runs wasm frames on. `max_wasm_stack` bounds
  it. Every wasm call uses it, whether or not it touches the linear stack.
- CPython's **C-stack guard** raises `RecursionError` ("Stack overflow (used N kB)") when the
  linear stack pointer comes within 16 KiB of the bottom of a range it believes is the stack.
  That range is its **window**.
- A **shape** is one way of recursing: a `__repr__` that calls `repr(self)`, `json.dumps` of a
  nested list, and so on. A **level** is one step of it.
- **Fuel** counts the guest's instructions. Depths are counts too: none depends on the machine.

## 1. The cause: two stacks, and the guard watches the wrong one (EXECUTED, READ)

- **The guard's window is the whole 16 MiB linear stack, not 4 MB.** CPython 3.15 asks the
  thread for its stack (`hardware_stack_limits`, `Python/ceval.c:141–190`, READ). The
  cross-build defines `HAVE_PTHREAD_GETATTR_NP` (`pyconfig.h:1032`, READ), and wasi-libc's
  `pthread_getattr_np` answers the main thread's `stack` and `stack_size`, which `__init_tp` sets
  to `__stack_high` and `__stack_high - __stack_low` (wasi-sdk 33's `libc.a`, disassembled,
  READ). So `Py_C_STACK_SIZE` (4,000,000) is never used; the earlier memo's 4 MB was INFERRED.
  EXECUTED: with a 64 MiB native stack, `pickle.dumps` of a 100,000-deep list, compiling
  `1+1+…` with 100,000 terms, and `repr` recursion under `sys.setrecursionlimit(100000)` all
  raise "Stack overflow (used 16368 kB)" (`evidence/snap-67108864.jsonl`).
- **wasmtime's native stack is 512 KiB.** Setting `max_wasm_stack = 524288` gives the same trap
  depth (416) and the same fuel (7,491,592) as not setting it (EXECUTED). wasmtime-py's own
  docstring says "defaults to 2MB" (READ, `wasmtime/_config.py:397`); that is stale.
- **The native stack runs out first, by far.** Each level of a shape costs native bytes and
  linear bytes in a ratio fixed by the shape. Measured with a research copy of the snapshot that
  exports the stack pointer, so its value at the trap is read (`export_sp.py`; same fuel as the
  set's binary), on the runner's engine (fuel and epoch interruption), at 512 KiB
  (`evidence/counted-sp-default.jsonl`, `bis-sp-default.jsonl`):

  | shape | trap depth | native B a level | linear B a level | native/linear |
  |---|---|---|---|---|
  | `__repr__` calling `repr(self)` (the memo's case) | 416 | 1,260 | 533 | 2.4 |
  | `__getattr__`, `__eq__`, `__len__`, `__hash__`, `__str__`, `__iter__` | 405–477 | 1,099–1,295 | 469–534 | 2.2–2.5 |
  | `functools.lru_cache` recursion | 306 | 1,713 | 552 | 3.1 |
  | `map` with a recursive lambda; `functools.reduce` | 370; 387 | 1,417; 1,355 | 516; 469 | 2.8; 2.9 |
  | `sorted(key=…)` recursion; `cmp_to_key` | 247; 229 | 2,123; 2,289 | 2,212; 2,232 | 1.0 |
  | `np.vectorize`; `np.frompyfunc`; `np.apply_along_axis` | 171; 219; 369 | 3,066; 2,394; 1,421 | 1,154; 2,144; 1,127 | 2.7; 1.1; 1.3 |
  | `pickle` of a recursive `functools.partial` | 1 call | | | 1.2 |
  | `json.dumps(…, default=f)` returning nested objects | 1,081 | 485 | 82 | 5.9 |
  | `repr` of a nested list | 1,912 | 274 | 33 | 8.4 |
  | `json.dumps` of a nested list | 1,478 | 354 | 49 | 7.3 |
  | `json.loads` of `[[[…]]]` | 1,204 | 435 | 17 | 25 |
  | `==` of two nested lists | 1,551 | 338 | 17 | 20 |
  | `hash` of a nested tuple | 2,504 | 209 | 17 | 13 |
  | `pickle.dumps` of a nested list | 1,016 | 516 | 193 | 2.7 |
  | freeing a nested `list`, `tuple`, `frozenset` | 2,325 | 225 | 0 | none |
  | freeing a nested `dict` | 1,415 | 370 | 0 | none |

  The window would have to be 16 MiB / 512 KiB = 32 times smaller before the first row could
  raise. And a chain of frees moves the linear stack not at all, so no window can see it: CPython
  3.15's trashcan (`_Py_Dealloc`, `Objects/object.c:3288`, READ) and its `Py_EnterRecursiveCall`
  both measure the linear stack pointer.
- **Python-to-Python recursion is not affected.** `def f(n): return f(n + 1)` raises
  `RecursionError` at 996 frames in every configuration (EXECUTED). Python frames call no C.
- **Freeing is where much of it bites.** A program that catches its `RecursionError` still traps
  when the deep structure is freed at exit: `copy.deepcopy` and a numpy object array print their
  `RecursionError`, then trap (`evidence/snap-default.jsonl`, `diag.jsonl`). `inspect.unwrap` of
  `unittest.mock.call` builds a 1,000-long chain of `_Call` objects and traps freeing it, with
  13.9 KB of linear stack in use (`evidence/t5-0.jsonl`).
- **Native CPython, for comparison** (`evidence/native.txt`, the pinned host Python 3.15.0, an
  8 MiB stack): every Python-through-C shape raises at the recursion limit (997); nested
  `repr`, `json`, `pickle` and compile raise "Stack overflow (used 8144 kB)"; `hash` of a
  100,000-deep tuple and a 100,000-long chain of `map` objects crash it with SIGSEGV.

## 2. The window: CPython's own API, from a recipe (EXECUTED)

CPython 3.15 has a call for exactly this: `PyUnstable_ThreadState_SetStackProtection(tstate,
start, size)` sets the guard's window (`Include/cpython/pystate.h:309`; documented for embedders
that switch stacks, `Doc/c-api/threads.rst:754`; READ). `research_main.c` is the recipe's
`reactor_main.c` plus one function that reads a window size from the environment variable
`RESEARCH_C_STACK` and calls it at `run()` with `start = &__stack_high - size`. The research
binary was relinked from the main tree's build with CPython's own link command; with the recipe
unchanged that relink reproduces the set's `python.wasm` byte for byte but for the module's name
(`evidence/relink.txt`).

- **The sweep** (the shapes of section 1 that trapped, runner's engine, 512 KiB;
  `evidence/counted-L*.jsonl`):

  | window | Python-through-C shapes that raise | first to trap again |
  |---|---|---|
  | 128 KiB | all 23 | none (json's `default=` hook still traps, as before) |
  | 160 KiB | all 23 | none, `lru_cache` 268 levels in, 12% from its trap |
  | 192 KiB | 22 | `lru_cache` traps at 306, as before |

  128 KiB is a quarter of the native stack and holds a margin of about a quarter over the worst
  shape measured (`lru_cache`, ratio 3.1). The message is CPython's: "Stack overflow (used
  112 kB)", the window less the guard's 16 KiB.
- **Depths under a 128 KiB window:** `__repr__` 214 levels, `__getattr__` 214, `__eq__` 244,
  `__len__` 228, `__hash__` 221, `__str__` 235, `__format__` 177, `lru_cache` 208, `map` 222,
  `reduce` 245, `min(key=…)` 187, a dataclass's `repr` 202, `pickle`'s `__reduce__` 164,
  `re.sub` with a recursive callback 148, `np.vectorize` 99, `np.apply_along_axis` 101,
  `np.frompyfunc` 53, `sorted(key=…)` 52, pandas `Series.map` 160. `eval` and `exec` recursion
  raise `MemoryError` ("Parser stack overflowed", 183 and 157): the parser checks the same guard
  and raises its own error. Each depth is about half the trap depth before (416, 306, 171, 247
  …): the cost of the fix. Native CPython stops all of these at its recursion limit, 1,000.
- **Engines and binaries.** On wasmtime's default engine (no fuel, no epoch) the native frames
  are about a fifth smaller (trap depths 542 against 416 for `__repr__`), and the window gives the
  same depths as on the runner's engine (`evidence/counted-bare-*.jsonl`). The research snapshot,
  made with step 80's wizer command, gives the same depths as the plain binary
  (`evidence/snap-research-*.jsonl`). The wasmtime 49.0.3 CLI at its default stack: without the
  window, exit 134 and "call stack exhausted"; with it, `RecursionError`
  (`evidence/cli.txt`).
- **Ordinary work is untouched.** numpy (`inv`, `svd`, `fft`, `sort`, `einsum`), pandas (a
  groupby, a merge, `to_csv` and `read_csv`, a pivot table, `to_datetime`), sqlite3, json, pickle,
  `re` with a 500-way alternation, compiling 300 functions, a deflated zip, decimal, and
  matplotlib saving PNG, SVG and PDF all run under the window; the deepest linear stack they write
  is 27.6 KB, and their fuel is the same within 0.02% (10,351,079,200 against 10,352,616,417;
  EXECUTED, `sink.py`).
- **Nothing else changes.** `sys.getrecursionlimit()` is still 1,000. The guest has no
  `_interpreters`, so the main thread's state is the only one a window must cover (EXECUTED,
  `t7.py`). The hostile-guest check's program (`sys.setrecursionlimit(10**8)` and Python
  recursion) still ends in a stack-overflow trap after about 38 G fuel, window or not
  (`evidence/t6-*.jsonl`).
- **What the window does not fix at 512 KiB** (`evidence/rest-29.jsonl`,
  `bis-parser-L128.jsonl`): every data shape whose ratio is above 4 (nested `repr` and `str`,
  `json` both ways, `==`, `hash`), freeing (any ratio), and the parser, whose frames keep almost
  nothing in linear memory: `eval` of 142 nested parentheses traps (native: `SyntaxError` at 200),
  and of `-` repeated 3,223 times. CPython's WASI build sets the parser's own limit, `MAXSTACK`,
  to 4,000 (`Parser/parser.c:11–19`, READ), which needs more than 512 KiB here. Printing a
  834-deep `ExceptionGroup` traps. Only `pickle.dumps` of nested data (ratio 2.7) newly raises.

## 3. Spec 065's five trap entries (EXECUTED)

Each run alone through the judge's own driver (`cpy071.py`, the research snapshot, the stage of
the earlier memo at `/cpy`):

| entry | 512 KiB | 512 KiB, window | 1 MiB, window | 2 MiB, window |
|---|---|---|---|---|
| `test_functools` `test_recursive_pickle` | trap | **passes** | passes | |
| `test_doctest` `test_issue35753` | trap | trap (freeing `_Call` chain) | passes | |
| `test_exceptions` `test_recursion_in_except_handler` | trap | trap (freeing) | passes | |
| `test_syntax` `test_error_on_parser_stack_overflow` | trap | trap (parser) | passes | |
| `test_traceback`, whole module | trap | | trap (exception groups) | **runs to its end** |

At 2 MiB with the window, `test_traceback` runs 434 tests; its errors are all
`CExcReportingTests`, which imports the absent `_testcapi` (the earlier memo's `no-test-modules`
class). So the window alone closes one entry; the other four need a larger native stack (or the
source changes of section 6).

## 4. What a larger native stack buys, with the window (EXECUTED)

Each case at a fixed depth, the structure not freed (`os._exit`), under the 128 KiB window
(`evidence/fixed-*.jsonl`):

| case | 512 KiB | 1 MiB | 2 MiB | 8 MiB |
|---|---|---|---|---|
| `repr`, `json.dumps` of a 100,000-deep list | trap | `RecursionError` | `RecursionError` | `RecursionError` |
| `json.loads`, `==` at 100,000 | trap | trap | trap | `RecursionError` |
| `eval` of 100,000 `-`, of 199 parentheses | trap | `MemoryError` | `MemoryError` | `MemoryError` |
| printing a 10,000-deep `ExceptionGroup` | trap | trap | trap | runs |
| freeing a 10,000-deep list, dict, tuple | trap | trap | trap | runs |
| freeing a 100,000-deep list | trap | trap | trap | trap |
| `hash` of a 100,000-deep tuple; 100,000 `map`s | trap | trap | trap | trap (native CPython crashes too) |
| compiling `1+1+…` with 100,000 terms | trap | trap | trap | trap (30,000 raise; not followed further) |

With the window, a native stack 25 times the window covers every data shape measured that
CPython guards; freeing stays bounded by the stack alone, at about 225 to 370 native bytes a
level.

## 5. Raising the runner's stack (EXECUTED, READ)

- **wasmtime-py's 2 MiB cap is not real.** Above 2 MiB, wasmtime refuses `max_wasm_stack`
  because it exceeds `async_stack_size` (the earlier memo). wasmtime-py does not wrap the setter,
  but its library exports `wasmtime_config_async_stack_size_set` (`nm` of
  `_libwasmtime.dylib`, READ); called through `wasmtime._ffi.dll`, it lets 64 MiB through
  (EXECUTED). The runner already calls that library this way for epochs and fuel.
- **The real cap is the host thread.** A synchronous call runs wasm on the calling thread's own
  stack. wasmtime's limit only stops wasm; it does not make the thread larger. With 64 MiB set on
  the main thread (16 MiB at most: CPython links its macOS executable with `-stack_size
  0x1000000`), freeing a 100,000-deep list killed the host process with SIGSEGV (exit 139, no
  trap, no output); on a 128 MiB thread the same run finished (EXECUTED,
  `evidence/mainthread.txt`). Thread stacks by host (READ): `python.exe` on Windows reserves
  2,000,000 bytes (`PCbuild/python.vcxproj:98`), and its threads take the same default; macOS
  gives `python`'s main thread and Python's threads 16 MiB (`configure.ac:3785`, Issue #18075);
  Linux gives `ulimit -s`, usually 8 MiB, to both; an application that embeds Python sets its own. So 512 KiB
  is safe on every thread Python makes; 2 MiB is not safe on Windows' main thread.
- **So a larger stack needs a thread the runner owns,** made with `threading.stack_size`. Then
  `run`'s host functions (the door, providers, tools) run on that thread, not the caller's. The
  README promises "A provider runs synchronously on the thread that runs the guest" and handles
  Ctrl-C on the main thread (*Time and threads*, *Safety*; READ), so that is a change of the
  runner's documented behaviour, not a setting.

## 6. Other ways (INFERRED unless marked)

- **Carry CPython patches.** (a) A depth counter in `_Py_Dealloc` on WASI, so a chain of frees
  hands objects to the trashcan after a fixed depth, as CPython 3.13's trashcan did by count.
  That would close the freeing rows and, by the causes above, the `test_doctest`,
  `test_exceptions` and `test_traceback` entries. (b) A smaller WASI `MAXSTACK` in the parser
  (one constant upstream already sets for WASI), for `test_syntax`. (c) A count in
  `Py_EnterRecursiveCall` on WASI, like 3.13's `Py_C_RECURSION_LIMIT` ("based on wasmtime 16"),
  for the data shapes. None was built: the main tree's CPython build was removed by the landing
  lane's rebuild at 21:20, mid-research, and (c) touches an inline used by every object file.
  Upstream's own position is a large runtime stack (its WASI CI sets `max-wasm-stack` to 32 MiB,
  `Platforms/WASI/wasmtime.toml`, READ), so these patches might never be temporary.
- **`-fstack-protector-all`** gives every function a linear frame, so the guard would see every
  level. A level would still cost 5 to 15 times more native than linear bytes, so the window
  would have to shrink to about 50 KB; and every call pays a canary.
- **Lowering `-z stack-size` instead of the window** moves the guard the same way but also takes
  real linear space from C code with large locals; the window keeps the 16 MiB and moves only the
  guard.

## 7. wasmtime 50 (EXECUTED)

wasmtime-py 50 is not on PyPI (`uv pip compile` of `wasmtime>=50` with prereleases allowed:
"only wasmtime<=49.0.0 is available"), so nothing was measured on it. Native frame sizes are
Cranelift's and may move with any wasmtime; the window's depths are CPython's (linear bytes) and
do not. A check at the stated stack is what would see a wasmtime whose frames grew by more than
the quarter of margin.

## What it decides

- The defect is two stacks: CPython guards a 16 MiB linear stack; wasmtime gives wasm 512 KiB of
  native stack, which every C level spends 1 to 25 times faster, and chains of frees without
  limit.
- A 128 KiB window, set from the recipe through CPython's own API, makes every Python-through-C
  shape measured raise at wasmtime's default stack, on both binaries, on any engine, for about
  half the depth it reached before trapping. Ordinary work does not notice.
- Data recursion in C, freeing deep structures, the parser and exception groups need a larger
  native stack (2 MiB closes spec 065's five; 8 MiB the data shapes) or carried patches. A larger
  stack in the runner needs a thread the runner owns.

## One line

wasmtime runs out of native stack long before CPython's 16 MiB guard looks; a 128 KiB window
fixes recursion through Python code for every embedder, and the rest needs more stack than a
caller's thread can promise.
