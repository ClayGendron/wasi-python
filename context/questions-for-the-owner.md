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

- **Asked:** 2026-10-18; revised after spec 071's pre-build review. **Source:**
  `specifications/071-deep-recursion-raises-recursionerror.md`, Decisions 1 and 5 to 8;
  `research/2026-10-18-deep-recursion-on-the-wasm-stack.md`, sections 3 to 6 and its addendum.
- **The facts** (EXECUTED unless marked; arm64 and x86_64 Linux, the runner's engine):
  - CPython guards C recursion by the stack in linear memory, 16 MiB. wasmtime gives wasm frames
    a separate native stack of 512 KiB by default, and every C level spends it faster: 2 to 3
    times for most recursion through Python code, about 6 times for callbacks out of expat, up
    to 25 times for C over nested data, and without limit for chains of frees, which move the
    linear stack not at all.
  - Spec 071 narrows CPython's guard to 128 KiB from the recipe. Then, at the default stack, 64
    of the 70 recursion shapes the review measured raise `RecursionError` on both hosts; x86_64's
    thinnest margin is about a ninth (`heapq` with a recursive `__lt__`). Recursion through a
    callback out of expat does not: a `pyexpat` handler that parses again traps on both hosts,
    `xml.sax` and `ElementTree` parser targets on x86_64.
  - Still trapping at 512 KiB (the lower host's edges): those expat callbacks past about 95
    levels; freeing a nested list more than about 2,000 deep (a dict 1,300); `json.loads` past
    1,100 levels; `repr` of nested lists past 1,800 and `==` past 1,350; source with more than
    about 130 nested brackets; an `ExceptionGroup` nested past 720. Five of spec 065's nine trap
    entries are among them (`test_doctest`'s `test_issue35753`, `test_exceptions`'
    `test_recursion_in_except_handler`, both `test_syntax` `test_error_on_parser_stack_overflow`
    entries, `test_traceback` whole), and a sixth once the judge's driver uses the runner's engine
    (`test_ordered_dict`'s `test_highly_nested`, freeing a 1,000-deep `OrderedDict`). The window
    closes the other four (`test_recursive_pickle`).
  - More native stack closes them. With the window, 1 MiB closes four of the original five
    entries, 2 MiB all five, 8 MiB `json.loads`, `==` and freeing 10,000-deep structures (arm64;
    x86_64 needs up to 696 KiB for the expat shapes). Left even at 8 MiB: freeing 100,000-deep
    structures, a 100,000-term expression, and two shapes that crash native CPython too.
  - wasm runs on the calling thread's own stack. A limit larger than the thread has killed the
    host process with SIGSEGV, no trap. `python.exe` on Windows reserves 2,000,000 bytes per
    thread (READ), so the runner cannot raise its stack on a caller's thread.
- **Why it is yours:** each option changes something you set. (a) changes the runner's documented
  behaviour (host functions run on the thread that runs the guest, the README's *Time and
  threads*). (b) carries source patches that §4.1 wants temporary, and they may never be. (d)
  takes depth from every working program.
- **The options:**
  - **(a) A stack the runner owns.** The runner runs each guest on a thread of its own with an
    8 MiB stack, and the README asks other embedders for the same. It closes all six entries and
    every data limit measured above but those left at 8 MiB, the expat callbacks included. No
    change to CPython; it is what CPython's own WASI CI does (32 MiB). The costs, all from `run`'s
    host functions (the door, providers, tools) running on the runner's thread instead of the
    caller's:
    - a thread-bound object used in a host function (a `sqlite3` connection, say) stops working;
    - `contextvars` and thread-locals the caller set (a web request's context, a tracing span) are
      not seen there unless the runner copies the context into the thread;
    - `signal.signal` is refused off the main thread (already true under `run_async`);
    - Ctrl-C lands on the caller's thread, so the runner must stop the guest from another thread;
    - `threading.stack_size` is process-wide, so the runner must set it under a lock or keep its
      own pool, or it changes the threads other code makes;
    - under `run_async` with the caller's `executor`, the guest runs on the caller's threads,
      whose stack the runner does not choose, so (a) means a second hop there too.
    Embedders that keep wasmtime's default still meet the limits. A runner change (parallel-safe),
    plus a window knob above 4 MiB (spec 071, Decision 2).
  - **(b) Carry CPython patches for WASI**: a depth count in `_Py_Dealloc` (CPython 3.13's
    trashcan counted), a smaller parser `MAXSTACK`, a count in `Py_EnterRecursiveCall` like 3.13's
    `Py_C_RECURSION_LIMIT` (INFERRED; not built). They would cover embedders that keep wasmtime's
    default stack, and the runner keeps the caller's thread; whether they reach the expat
    callbacks depends on the count chosen (INFERRED). But C over data would stop at a fixed count
    (several hundred levels) where native allows thousands, and upstream's WASI answer is a large
    stack, so the patches may stay for good. Build-class, three patches with drafted pull
    requests.
  - **(c) Keep them as documented limits.** Nothing changes; the README lists the depths, spec
    071's checks hold them, and the six entries stay trap entries in spec 065.
  - **(d) A smaller window, 64 KiB.** It closes the expat callbacks at the default stack for any
    embedder (EXECUTED for `ElementTree` on x86_64: 248 KiB needed at 64 KiB; INFERRED for
    `pyexpat`), with no thread change and no patch. But every raising depth scales with the
    window less 16 KiB, so it halves them again: `__repr__` near 92 levels instead of 214,
    `sorted(key=…)` near 22 instead of 52. It closes none of spec 065's entries and none of the
    data limits. A one-line recipe change (build-class).
- **The agent's recommendation:** (a), at 8 MiB. It reaches furthest, diverges from CPython in
  nothing, and follows upstream's own model; its thread costs are real and listed above, and the
  default `run_async` pool already runs host functions on a worker thread. Choose (b) only if
  embedders that keep wasmtime's default stack must be covered too; (d) only if the expat
  callbacks matter more than ordinary depth.
- **Meanwhile:** spec 071 builds without the answer. Its limits are documented and checked; the
  five (six) trap entries name this question as their closer. Nothing else waits on it.

## The owner's direction for the product (2026-10-17)

"I am thinking of this more as a safe runtime for agent code. The use case is much more
powerful web agents that can access code and interact with their data and tools (either through
a file system, tools in the host program, api calls, mcp, etc.) its main use case is to work with
~/Git/repos/vfs and run on top of that where vfs manages the permissions and governance."

The code stays embedder-neutral (§4.5). The capabilities that agent use needs are built as
general features; `research/2026-10-17-the-runtime-for-agent-code.md` studies which. State
across turns is researched before any specification (`research/2026-10-17-state-across-agent-turns.md`).
