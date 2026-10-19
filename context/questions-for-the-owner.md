# Questions for the owner

Questions the agent could not answer alone, written down so the work could go on (the owner's
instruction of 2026-10-16: "If you do have questions, please write them down in the repo and
continue working"). Each says what waits on it and what the agent did meanwhile. An answered
question moves to another document (research, spec, review, etc.) and is deleted from this
document.

## Open

### 100. Where the cap on open files protects: the process's own limit, and deep paths

- **Asked:** 2026-10-18. **Source:** spec 068's pre-build review, F1 and F2
  (`specifications/068-a-cap-on-open-files.md`, the Problem, Decisions 1, 5 and 7, and its
  disposition). Nothing waits on it: spec 068 builds as written.
- **F1, the fact:** a guest's descriptors share the embedder's process table, so the cap of
  1,024 keeps a guest from starving the process only where the process's soft `RLIMIT_NOFILE`
  is above 1,024 plus what it already holds, for every call and session at once. macOS starts a
  process at 256 and many Linux setups at 1,024; under those the host still runs out first, as
  today (EXECUTED by the review: 245 and 1,013 opens, then `EIO`; the embedder's `open()` failed).
- **F2, in one line:** on macOS, and on Linux without `openat2`, wasmtime holds one uncounted
  host descriptor per folder of a path while it resolves it, so a guest with a writable grant can
  build a deep folder and hold the process at its limit for its call under any cap (EXECUTED by
  the review: 500 deep, a 512-descriptor process held full); spec 068 states it, and spec 072, a
  bound on path depth, is named to close it.
- **The question:** should the library itself raise the process soft limit, or should the
  default drop below 256?
- **The agent's recommendation:** no to both. Keep 1,024, with the README's plain advice to
  raise the soft limit or set `max_open_files` below it; the library leaves the process's limits
  alone, and `wasi-python run` raises its own, since it owns its process. Meanwhile: 068 builds
  with that text.

### 101. Should the judge-only binary of question 89 also carry CPython's C test modules?

- **Asked:** 2026-10-18. **Source:** `specifications/065-cpythons-own-tests-in-the-release.md`,
  Decision 3; `research/2026-10-18-cpythons-own-tests-under-the-runtime.md`, sections 2 and 4.
- **The fact:** the build passes `--disable-test-modules` (`scripts/steps/20_cpython.sh:16`), so
  `_testcapi`, `_testinternalcapi`, `_testlimitedcapi`, `_testbuffer`, `_testmultiphase` and the
  `xx*` modules are absent. In the guest that skips about 500 of CPython's own tests and 11 of its
  modules whole, keeps 3 modules from loading (`test_class`, `test_with`, `test_getpath`, which
  import `_testinternalcapi` unguarded), errors 3 tests, and makes `test_monitoring`'s
  `TestCApiEventGeneration` skip in `setUp` with three monitoring tools left registered, which fails
  45 later tests (EXECUTED, the memo and spec 065's pre-build review). Spec 065 admits the 3 errors as
  a class, deselects the 5 `TestCApiEventGeneration` tests by name and leaves the 3 modules out, each
  a gap closed by this question.
- **Why it is yours:** you answered question 89 for numpy's C test modules: "(a), a judge-only
  binary linked with numpy's test modules, never shipped: a later build-class specification".
  CPython's are a different build of CPython itself (`--enable-test-modules`), a new build output
  that is never published, as numpy's would be.
- **The question:** should that later judge-only binary also be built with CPython's test modules,
  so the judge runs these tests there? Or leave them out for good, and the classes close with the
  README?
- **The agent's recommendation:** yes, in the same later specification as question 89's: one
  judge-only build, never shipped, run only for the tests that need it. The product is unchanged.
- **Meanwhile:** spec 065 builds without the answer; its class, its deselection entry and its three
  not-selected modules name this question as their closer. Nothing else waits on it.

### 102. What closes the deep-recursion traps the C-stack window cannot?

- **Asked:** 2026-10-18. **Source:** `specifications/071-deep-recursion-raises-recursionerror.md`,
  Decisions 5 to 7; `research/2026-10-18-deep-recursion-on-the-wasm-stack.md`, sections 3 to 6.
- **The facts** (EXECUTED unless marked, the memo):
  - CPython guards C recursion by the stack in linear memory, 16 MiB. wasmtime gives wasm frames
    a separate native stack of 512 KiB by default, and every C level spends it faster: 2 to 3
    times for recursion through Python code, up to 25 times for C over nested data, and without
    limit for chains of frees, which move the linear stack not at all.
  - Spec 071 narrows CPython's guard to 128 KiB from the recipe. Then all 23 Python-through-C
    shapes measured raise `RecursionError` at the default stack, for every embedder.
  - Still trapping at 512 KiB: freeing a nested list more than about 2,300 deep (a dict 1,400);
    `json.loads` past 1,200 levels; `repr` or `==` of nested lists past 1,500 to 1,900; source
    with more than about 140 nested brackets; an `ExceptionGroup` nested past 830. Four of spec
    065's five trap entries are among them (`test_doctest`'s `test_issue35753`,
    `test_exceptions`' `test_recursion_in_except_handler`, `test_syntax`'s
    `test_error_on_parser_stack_overflow`, `test_traceback` whole).
  - More native stack closes them. With the window, 1 MiB closes four of the five entries,
    2 MiB all five, 8 MiB `json.loads`, `==` and freeing 10,000-deep structures. Left even at
    8 MiB: freeing 100,000-deep structures, a 100,000-term expression, and two shapes that crash
    native CPython too.
  - wasm runs on the calling thread's own stack. A limit larger than the thread has killed the
    host process with SIGSEGV, no trap. `python.exe` on Windows reserves 2,000,000 bytes per
    thread (READ), so the runner cannot raise its stack on a caller's thread.
- **Why it is yours:** each option changes something you set. (a) changes the runner's documented
  behaviour (host functions run on the thread that runs the guest, the README's *Time and
  threads*). (b) carries source patches that §4.1 wants temporary, and they may never be.
- **The options:**
  - **(a) A stack the runner owns.** The runner runs each guest on a thread of its own with an
    8 MiB stack, and the README asks other embedders for the same. Closes all four entries and
    every data limit measured above but those left at 8 MiB. No change to CPython; it is what
    CPython's own WASI CI does (32 MiB). But `run`'s door, providers and tools then run on the
    runner's thread, not the caller's: a thread-bound object (a `sqlite3` connection, say) in a
    host function stops working, and Ctrl-C on the main thread must stop the guest from another
    thread. Embedders that keep wasmtime's default still meet the limits. A runner change
    (parallel-safe), plus a window knob above 4 MiB (spec 071, Decision 2).
  - **(b) Carry CPython patches for WASI**: a depth count in `_Py_Dealloc` (CPython 3.13's
    trashcan counted), a smaller parser `MAXSTACK`, a count in `Py_EnterRecursiveCall` like 3.13's
    `Py_C_RECURSION_LIMIT` (INFERRED; not built). Every embedder is covered at wasmtime's default
    stack, and the runner keeps the caller's thread. But C over data would stop at a fixed count
    (several hundred levels) where native allows thousands, and upstream's WASI answer is a large
    stack, so the patches may stay for good. Build-class, three patches with drafted pull
    requests.
  - **(c) Keep them as documented limits.** Nothing changes; the README lists the depths, spec
    071's checks hold them, and the four entries stay trap entries in spec 065.
- **The agent's recommendation:** (a), at 8 MiB. It reaches furthest, diverges from CPython in
  nothing, and follows upstream's own model; the thread change is real but bounded, and
  `run_async` already runs host functions on a worker thread. Choose (b) only if embedders that
  keep wasmtime's default stack must be covered too.
- **Meanwhile:** spec 071 builds without the answer. Its limits are documented and checked; the
  four trap entries name this question as their closer. Nothing else waits on it.

## The owner's direction for the product (2026-10-17)

"I am thinking of this more as a safe runtime for agent code. The use case is much more
powerful web agents that can access code and interact with their data and tools (either through
a file system, tools in the host program, api calls, mcp, etc.) its main use case is to work with
~/Git/repos/vfs and run on top of that where vfs manages the permissions and governance."

The code stays embedder-neutral (§4.5). The capabilities that agent use needs are built as
general features; `research/2026-10-17-the-runtime-for-agent-code.md` studies which. State
across turns is researched before any specification (`research/2026-10-17-state-across-agent-turns.md`).
