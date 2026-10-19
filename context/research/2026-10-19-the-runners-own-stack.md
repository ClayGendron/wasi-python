# The runner's own stack: an 8 MiB wasm stack on a thread of its own, and what it closes

- **Status:** executed, 2026-10-19 (probes in a scratch folder on a fresh `cp -Rp` copy of main's
  set; nothing in the main tree changed; the relinked research binary was written to the scratch
  folder only).
- **Owner:** Clay Gendron
- **Researcher:** a research agent (Claude Opus 5.5), drafting spec 078.
- **Feeds:** spec 078, the runner runs each guest on a stack of its own (question 102, answered
  (a) on 2026-10-19).
- **Stands on:** `2026-10-18-deep-recursion-on-the-wasm-stack.md` and its addendum (the two stacks,
  the 128 KiB window, the edges at 512 KiB, the SIGSEGV of a limit larger than the thread); spec
  071's build review, F1 (musl's 128 KiB threads); the 0.1.0a7 security review, F4.
- **Evidence:** beside this memo, `2026-10-19-the-runners-own-stack/`: the probes and, under
  `evidence/`, their outputs. Every guest run is main's set `s-c50ca51fae5eb55b-c9dcb5b8`
  (`python.wasm` `ab78e893…`, the snapshot `c50ca51f…`), copied, on wasmtime-py 49.0.0, unless a
  line says otherwise. darwin is arm64 macOS with the project's CPython 3.14.2; Linux ran in
  Docker on the same Mac: Debian 13 (glibc 2.41, the `wp040-*` images) and Alpine (musl), aarch64
  natively and x86_64 under emulation, with uv-managed CPython 3.14.2 (glibc) and 3.14.5 (musl).

Terms used below:

- **W** is `max_wasm_stack`, the native stack wasmtime lets wasm frames use.
- **T** is the size of the host thread that calls into wasm.
- A **guest thread** is a thread the runner makes to run wasm on; the **home thread** is the thread
  that called `run` (or a session's method) and waits.
- A **callback** is a host function the guest calls: the door, a provider, WASI, the runner's own.
- **Edge** is the last depth that completes; the next traps.

## 1. How wasmtime 49 takes an 8 MiB stack (EXECUTED, READ)

- **The limit is relative to the entry.** wasmtime sets the stack limit at the first entry from the
  host, as the stack pointer there less W, and keeps it for nested entries on a synchronous store
  (READ, `crates/wasmtime/src/runtime/func.rs:1525–1587` at 49.0.3). It stops only wasm: a host
  function runs on the same stack below the wasm frames, and wasmtime's own documentation says a
  thread without room for W aborts the process (READ, `config.rs:827–851`). The default W is
  512 KiB (READ, `config.rs:851`).
- **Above 2 MiB, wasmtime needs `async_stack_size` at least as large.** It refuses the config
  otherwise (READ, `config.rs:2632–2633`), and wasmtime-py's engine unwraps that error, so the
  process aborts (READ, `crates/c-api/src/engine.rs:37`; EXECUTED, `p1_config.out`: exit −6,
  "max_wasm_stack size cannot exceed the async_stack_size", at 2 MiB + 4 KiB, 8 MiB and 16 MiB). wasmtime-py 49 has no Python setter,
  but its library exports `wasmtime_config_async_stack_size_set`; with it set to W, the engine
  is made at every size tried (EXECUTED). wasmtime-py's own bindings declare that function too
  (`wasmtime._ffi.wasmtime_config_async_stack_size_set`, with its argument types; EXECUTED,
  `p1b_binding.out`), so calling it sets no argument types on a shared attribute. The async stack
  size is used only by async calls, which the runner does not make (READ, `config.rs:862–877`).
- **Fuel does not depend on W or on the thread** (EXECUTED, `fuel078.out`): five programs (a
  print, numpy, a pandas groupby, spec 071's `__repr__` recursion, freeing a 2,000-deep list) gave
  the same fuel at 512 KiB and 8 MiB, on the caller's thread and on a fresh one.
- **A session's store may change threads between turns** (EXECUTED, `turns078.out`): opened on
  the main thread, four turns each on a fresh 9 MiB thread gave the same output and the same fuel
  left as the four turns on one thread; the last freed a 20,000-deep list, which traps at 512 KiB.

## 2. How big the thread must be (EXECUTED, `p5-*.log`)

Probe 5 runs a guest through `wasi_python.run`, with the runner patched to W = 8 MiB, on a thread of
T bytes asked of `threading.stack_size`, each trial in its own process, and bisects T to 4 KiB. The
guests: freeing a 100,000-deep list (traps at the limit, no callback near it); the edge depth of a
list whose every level holds an object with a finalizer that calls the door (`list-door`) or a
provider (`list-provider`), so a callback runs at the deepest point.

| host | no callback at depth | a door callback at the deepest point |
|---|---|---|
| darwin arm64 | W − 12 KiB asked (macOS reports 12 KiB more: W) | W + 20 KiB (a provider callback: the same) |
| Linux glibc aarch64 | W + 12 KiB | W + 48 KiB |
| Linux glibc x86_64 | W + 12 KiB | W + 44 KiB |
| Linux musl aarch64 | W + 4 KiB | W + 44 KiB, once the interpreter is told its stack (section 3) |
| Linux musl x86_64 | W + 4 KiB | W + 44 KiB, the same |

- **Below that, the host dies.** darwin: SIGILL (exit −4) from T = 1 MiB to W − 16 KiB; Linux:
  SIGSEGV (−11) at 1 MiB. The **main thread** dies at W = 8 MiB on darwin and on Linux (−11):
  its stack is 8,372,224 bytes on darwin and 8 MiB on Linux (`env_facts.py`), less than W plus
  the frames above.
- **So W plus 48 KiB is the most measured**, with the runner's own callbacks and a trivial host
  function at the deepest point. Embedder code that does more at that point needs more.
- **The default threads** (`env_facts.py`): darwin 16 MiB (this CPython build), glibc 8 MiB, musl
  133,864 bytes (aarch64) and 133,880 (x86_64). `threading.stack_size` is one value per
  interpreter (READ, CPython 3.15.0's `Python/thread_nt.h:66–71`, `interp->threads.stacksize`).
- **Windows** (READ, not run): CPython starts a thread with `_beginthreadex(…, stacksize, …, 0,
  …)` (`Python/thread_nt.h:68–71`), so the size asked is committed, not only reserved; the main
  thread of `python.exe` has 2,000,000 bytes (the earlier memo, section 5).

## 3. The host interpreter's own guard, on musl (EXECUTED, READ)

- **CPython 3.14 and later read the stack pointer.** They raise `RecursionError` near the end of
  the thread's stack, and end the process with "Unrecoverable stack overflow" past it (READ,
  `Python/ceval.c`, `_Py_CheckRecursiveCall`, in the pinned 3.15.0 tarball). On glibc, macOS and
  Windows they read the thread's real bounds; on Linux without glibc they do not, and assume
  `Py_C_STACK_SIZE` (4,000,000 bytes) from where the thread state was attached
  (`hardware_stack_limits`, with the comment "musl supports HAVE_PTHRED_GETATTR_NP, but the
  resulting stack size … is much smaller than expected").
- **So on musl, a callback from deep in the guest kills the host** (EXECUTED,
  `musl-guess.log`): `list-door` at depth 20,000 on a 32 MiB thread ends the process (exit 134)
  with "Fatal Python error: _Py_CheckRecursiveCall: Unrecoverable stack overflow (used 3906 kB)
  while calling a Python object", in `wasmtime_func_call` under `_drive`. Any callback counts:
  the door, a provider, the runner's own WASI shadows, its output writers and its epoch callback
  are all Python called from wasm.
- **Telling the interpreter fixes it.** With the guest thread calling
  `PyUnstable_ThreadState_SetStackProtection(PyThreadState_Get(), low, size)` through
  `ctypes.pythonapi` with its real bounds (`pthread_getattr_np`), the same guest completes, and
  the edge needs T = W + 44 KiB on both architectures (EXECUTED). The call is in CPython 3.14.1
  and later, not 3.14.0 (EXECUTED: `ctypes.pythonapi` has it in 3.14.1, 3.14.2, 3.14.5 and
  3.15.0b2; not in 3.14.0, 3.13 or 3.12). 3.14.0 on musl dies the same way at the edge
  ("used 8195 kB"). CPython 3.13 counts C recursion instead and survives without it (EXECUTED).

## 4. What 8 MiB closes (EXECUTED)

### Spec 065's eight trap entries (`cpy078.py`, `cpy078.out`)

Each alone, through the 078 worktree's judge driver on the runner's engine (fuel, epoch
interruption), with the CPython-suite memo's research stage and driver (not 065's own driver,
whose adaptations differ), on a 64 MiB thread:

| entry (065 at `19c4acb`) | 512 KiB | 8 MiB |
|---|---|---|
| `c-stack-doctest` (`test_issue35753`) | trap | passes |
| `c-stack-exceptions` (`test_recursion_in_except_handler`) | trap | passes |
| `c-stack-syntax` and `c-stack-syntax-lazy-import` (both `test_error_on_parser_stack_overflow`) | trap | both pass |
| `c-stack-ordered-dict-py`, `-py-subclass`, `-subclass` (`test_highly_nested`) | trap, each | passes, each |
| `c-stack-traceback` (the module) | trap | runs to its end |

At 8 MiB `test_traceback` runs 434 tests: 193 skipped, 167 errors and one failure
(`traceback-8m.txt`). 139 errors import the absent `_testcapi`; 28 write a temporary module
where this research driver's working directory is read-only; the failure is
`MiscTest.test_windows_only_module_error` ("Unsupported platform for Windows-only standard
library module 'msvcrt'" not in the message). None is a trap. Their classes are 065's driver's to
derive.

### The edges (`edges8.py`, `cases078.py`; `edges-*.jsonl`, `kind8.out`)

The snapshot on the runner's metered engine, a 64 MiB thread, each depth a fresh instance; "raises"
means the case reached the largest depth tried with the named exception and no trap.

| case | 512 KiB, arm64 | 8 MiB, arm64 | 8 MiB, x86_64 |
|---|---|---|---|
| freeing a nested list; tuple | 2,325; 2,326 | 37,433; 37,434 | 32,753; 32,754 |
| freeing a nested dict | 1,415 | 22,785 | 20,962 |
| `repr` of a nested list | 1,912 | raises (400,000) | raises |
| `json.dumps` of a nested list | 1,478 | raises (400,000) | raises |
| `json.loads` of nested arrays | 1,204 | raises (400,000) | raises |
| `==` of nested lists | 1,551 | raises (400,000) | raises |
| `json.dumps` with a nesting `default=` | 1,082 | raises (400,000) | raises |
| `hash` of a nested tuple | 2,504 | 40,313 | 40,312 |
| a chain of `map` objects | raises to 1,897, then traps | the same: the trap is `unreachable`, at the same depth as at 512 KiB (INFERRED: the window's hard limit reaching `Py_FatalError`, not the stack) | the same |
| `eval` of nested parentheses | 141 | `MemoryError` at 199, the tokenizer's most | the same |
| `eval` of nested unary minus | raises to 3,222, then traps | `MemoryError` (400,000) | the same |
| compiling `1+1+…` | raises to 3,614, then traps | raises to 58,227, then traps | 52,402 |
| printing a nested `ExceptionGroup` | 833 | completes at 100,000 | the same |
| a `pyexpat` handler parsing again | 130 | raises (20,000 bounded) | raises |
| `xml.sax`; `ElementTree` target, parsing again | raise | raise | raise |
| plain Python recursion, limit raised, never reaching it | completes 400,000 | the same | the same |
| unbounded Python recursion reaching a raised `sys.setrecursionlimit` | raises up to a limit of 2,958, traps above | 47,642 | 43,670 |
| XPath nested parentheses; chained predicates | 356; 4,055 | `XPathEvalError` at 6,000 (libxml2's own limit) | the same |
| XSLT nested `call-template`; `apply-templates` over a deep tree | 461; 661 | `XSLTApplyError` at 4,000 (`xsltMaxDepth`) | the same |
| C14N of a tree built in Python | 1,477 | 23,818 | 23,817 |

- **Closed at 8 MiB:** every data shape CPython guards (they now meet the window and raise), the
  parser, deep exception groups, the expat callbacks, XPath and XSLT (their own limits come
  first), and spec 016's named overflow still traps (`named.out`: "stack overflow" at 9.38 G fuel
  at 512 KiB and 9.77 G at 8 MiB).
- **Left at 8 MiB:** chains of frees (no guard sees them), `hash` of a nested tuple, compiling
  very long expressions, C14N of very deep trees, a recursion limit raised past about 43,000, and
  the `map` chain, which does not move with the stack.
- x86_64 is the lower host by 0 to 14%, as at 512 KiB.

## 5. A wider window at 8 MiB (EXECUTED, `window078.py`, `window-arm64.jsonl`; arm64 only)

The plain binary relinked from the main tree's build with one research function that reads the
window from `RESEARCH_C_STACK` at `run()` (`research_main.diff`; the recipe unchanged relinks to
main's `python.wasm` byte for byte, `relink.txt`). Spec 071's criterion-1 programs and four data
shapes, depth at `RecursionError`:

| row | 128 KiB at 8 MiB | 192 KiB at 8 MiB | 256 KiB at 8 MiB | 192 KiB at 512 KiB | 256 KiB at 512 KiB |
|---|---|---|---|---|---|
| `__repr__` | 214 | 338 | 462 | 338 | trap |
| `__eq__` | 244 | 385 | 527 | 385 | trap |
| `lru_cache` | 208 | 329 | 449 | trap | trap |
| `heapq` | 244 | 385 | 526 | trap | trap |
| `sorted(key=…)` | 52 | 82 | 111 | 82 | 111 |
| `np.frompyfunc`; `np.vectorize` | 53; 99 | 84; 156 | 115; 200 | 84; 156 | 115; trap |
| lxml parser target | 67 | 106 | 145 | 106 | trap |
| `pyexpat` handler | 137 | 216 | 294 | trap | trap |
| `json.loads`, `==`, `repr`, `json.dumps` of 400,000-deep data | raise | raise | raise | trap | trap |

- At 8 MiB, 256 KiB (spec 071's formula, W/32) about doubles every depth through Python code
  and the data shapes still raise, on arm64. Native CPython stops all of them at 1,000.
- At wasmtime's default 512 KiB the same window traps nine of the twelve rows. So a wider window
  must be one the guest is told, a knob, or every other embedder loses what spec 071 gave.
- Not measured: x86_64, whose frames are up to 29% larger (the earlier memo, A1): `json.loads`
  needs 25 native bytes for each linear one, so 256 KiB of window asks about 6.4 MiB of native
  stack on arm64 and, INFERRED, about 8.3 MiB on x86_64, over W.

## 6. What a thread of its own costs (benchmarks; EXECUTED as such)

Wall-clock numbers here are benchmark facts, never test assertions.

- **Starting and joining a thread** (`p3_handoff.py`): 36 to 50 µs on darwin for 0, 9 and 16 MiB
  stacks; 57 to 466 µs in the Linux VM, which two other agents' builds were loading. Against
  `run`'s 20 to 25 ms for the smallest warm call (the README), about 0.2% on darwin.
- **Handing one callback to the waiting thread and back** (`p3_handoff.py`, a queue one way and a
  lock the other): 7.0 to 7.7 µs on darwin; 33 to 495 µs in the loaded Linux VM. **A provider's
  `stat` and a door call today** (`p4_callback_cost.py`, host time per guest call): 31.5 µs and
  43.5 to 44.0 µs on darwin; 32.4 to 32.9 µs and 46.4 to 47.7 µs in the VM. So handing provider
  and door calls home costs about a quarter more host time per call on darwin; the VM's numbers
  were too noisy to state one ratio.
- **The waiting thread and signals** (`p6_home_signals.py`): a main thread waiting on a queue in
  50 ms slices runs a flag-setting SIGINT handler during the wait (darwin; glibc with 3.14.2 and
  3.11.14), and Python's default handler raises `KeyboardInterrupt` inside the wait, where a loop
  can catch it. But once in four 3.11.14 runs it landed between two bytecodes outside the loop's
  `try` (`while True:`) and escaped: an exception from a signal handler can land anywhere.

## 7. Today's runner, on three of spec 078's checks (EXECUTED, `failfirst.py`, `failfirst-main-darwin.out`)

On darwin, main's runner (the 078 worktree's `src/`, unchanged), each case in a child process:

- **A 256 KiB calling thread** whose guest frees a 2,000-deep list: the host dies (exit −4,
  SIGILL). It is musl's case on any host whose thread is smaller than 512 KiB plus its frames.
- **Ctrl-C on the main thread while a guest computes, `deadline_s=None`, no `cancel`**
  (`_thread.interrupt_main()` from a timer the door host starts): the call never ends; the child
  was killed at its 120 s limit. The deferred flag is read only by callbacks, and this guest
  makes none.
- **An embedder's SIGINT handler that raises, with `cancel=` set** (three runs): the
  `KeyboardInterrupt` lands on the first line of `_on_epoch`, the ctypes callback, where ctypes
  prints "Exception ignored" and drops it; the call runs to its 30 s deadline and returns
  `"deadline"`. The README's *Not protected* says this case can abort the process; here it was
  lost instead.

## What it decides

- An 8 MiB wasm stack needs `async_stack_size` raised through wasmtime-py's library, and a thread
  of W plus at least 48 KiB for the runner's own frames; neither a Linux nor a darwin main thread
  has it.
- On musl, CPython 3.14.1 and later must be told the guest thread's stack, and 3.14.0 cannot be.
- 8 MiB closes all eight of spec 065's trap entries and every data limit the README lists but
  chains of frees, `hash`, long expressions, C14N and very high recursion limits, each now 10 to
  16 times deeper.
- A wider window would double the depths through Python code, but only as a knob the guest is
  told; it is its own question.
- Fuel does not move. A thread per call costs tens of microseconds; handing each provider and door
  call back to the caller's thread costs a few microseconds on darwin each.

## One line

At 8 MiB on a thread of its own, every recursion the README lists but chains of frees and a few
deep C walks raises instead of trapping, at no fuel, for a thread start per call.
