# Review of 071 — Deep recursion raises RecursionError instead of trapping the guest (the specification, before build)

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I wrote none of the spec, the
  memo, question 102 or the research probes. I read `AGENTS.md`; the constitution (§4 whole,
  §5.6, §5.7); `context/decisions.md`; the CPython-suite memo
  (`research/2026-10-18-cpythons-own-tests-under-the-runtime.md`, finding 4.1 and section 8);
  060's pre-build review, for the shape; spec 065 at `b215132`, spec 069 at `68062f3` and spec
  055 at `e1ee581`, for where they meet this one; the code the spec changes
  (`recipes/reactor_main.c`: `init_interpreter`, `wizer_initialize`, `run`,
  `clear_unused_stack`; `src/wasi_python/runner.py`: `_engine`, `run_async`, `_submit`;
  `tests/harness/guest.py`: `engine`; `tests/checks/test_v1_2_hostile_guest.py`:
  `test_a_stack_overflow_is_named`); the README's embedder steps, *Time and threads* and
  *Safety*; and CPython 3.15.0's own source for the guard, unpacked from
  `downloads/Python-3.15.0.tar.xz` into my scratch folder (`Python/ceval.c:141–330`,
  `Python/pystate.c:1590–1600, 2245`, `Python/pylifecycle.c:943`,
  `Include/internal/pycore_ceval.h:210–232`, `Include/internal/pycore_pythonrun.h:44–66`,
  `Include/cpython/pystate.h:309`, `Doc/c-api/threads.rst:754–787`). Each claim is labelled
  EXECUTED, READ or INFERRED.
- **Reviewed:** `spec/071-deep-recursion-raises-recursionerror` at `2265b90` (`e63b18a` the
  draft, `2265b90` question 102), on main `ef1441b`: `git diff ef1441b..2265b90`. The diff
  touches only `context/` (READ). Its merge base is `e21623e`, one commit behind `ef1441b` (the
  a6 security review), and main has since moved to `7d377dd` (spec 046 landed: lxml, libxml2
  and libxslt built in, set `s-ff5246a2c2f1a52b`; READ, `git log main`). The diff shows the a6
  review as deleted only because of that base.
- **Ran (EXECUTED; darwin-arm64 natively, and linux/amd64 in the repository's own
  `wp040-amd64` Docker image under emulation, with wasmtime-py 49.0.0 on CPython 3.13; the frozen
  set `build/sets/s-4eb5418a2b1bb553-c353b1d9`, read only; the research's own binaries in
  `scratchpad/s071/` read only: `relink/research/python.wasm`, sha256 `1f623f0d…`, as
  `evidence/relink.txt` records, and `research-snapshot.wasm`, which set the window from
  `RESEARCH_C_STACK` at each `run`).** Nothing was written in any git tree or in the main tree's
  `build/`. Scripts and outputs sit in `probes/` beside this file:
  - `extra_cases.py`, `extra2_cases.py`: 50 recursion shapes the memo did not measure
    (dunders, metaclasses, descriptors, generators, `asyncio`, `sqlite3`, numpy's
    `__array__`/`__array_ufunc__`/object sorts, pandas, `copy`, `decimal`, `json`'s
    `object_hook`, `pickle`'s `__setstate__`, `xml.etree`, `pyexpat`, `xml.sax`, `minidom`,
    `csv`, `heapq`, `bisect`, `itertools.groupby`, PIL). `extra-29.jsonl`: each at 512 KiB with
    the 128 KiB window, through the research probe.
  - `stackmin.py` → `stackmin-{arm64,amd64}-{orig,extra,extra2}.jsonl`, tabulated in
    `margin-table.txt`: for each shape, the smallest `max_wasm_stack` (8 KiB steps) at which it
    does not trap, under the 128 KiB window, on the runner's engine (fuel and epoch). The ratio
    512 KiB / that stack is the real margin, per host.
  - `window-amd64.jsonl`: the three thinnest shapes at 64, 96 and 128 KiB windows (x86_64).
    `bare-amd64.jsonl`: two of them on wasmtime's default engine (x86_64).
  - `fixed512.py` with `crit4_cases.py`, `crit4b_cases.py` → `crit4-amd64.jsonl`,
    `crit4b-amd64.jsonl`: criterion 4's programs at 512 KiB on x86_64, at the spec's depths and
    in steps between them. `fixed-amd64.jsonl`: the memo's fixed-depth data cases at 1 MiB on
    x86_64.
  - `imports_cases.py` → `imports-plain-29.jsonl`: the deepest linear stack `import numpy`,
    `import pandas`, matplotlib and a small workload write on the plain binary (spec 069 moves
    those imports into each run).
  - `cpyrun.py` → `cpy-29.jsonl`, `cpy-29b.jsonl`, `cpy-0.jsonl`: 82 of CPython's own test
    modules (`Lib/test` from the pinned tarball, preopened read-only at `/cpy`) under `unittest`,
    on the research snapshot, with the window, and without it for every module that did not run
    clean. `cpy-amd64-29.jsonl`: 19 of them on x86_64. `trap-kinds.txt`: the trap codes, and
    `test_ordered_dict` on a fuel-only engine (`cpyrun_fuelonly.py`).
  - `rules.txt`: `uv run pytest tests/checks/test_rules.py -n 3` in the worktree.

## What holds

- **The mechanism is CPython's own and does what the spec says (READ, EXECUTED).**
  `PyUnstable_ThreadState_SetStackProtection(tstate, start, size)` is in 3.15.0
  (`Include/cpython/pystate.h:309`, exported with `PyAPI_FUNC`; `Python/ceval.c:250`). It
  refuses a size below `_PyOS_MIN_STACK_SIZE`, which on wasm32 is 3 × 2,048 × 4 = 24 KiB
  (`pycore_pythonrun.h:52–66`), and otherwise sets `c_stack_top = start + size`,
  `c_stack_hard_limit = start + 8 KiB`, `c_stack_soft_limit = start + 16 KiB`
  (`tstate_set_stack`, `ceval.c:194`). So "Stack overflow (used 112 kB)" at a 128 KiB window is exactly
  `top − soft` (EXECUTED: every raising shape here prints 112 or 113 kB). The call is a recipe
  line using a documented API; `recipes/patches/` and CPython's tree stay as they are, so
  §4.1 is met. The unstable tier may change in 3.16; the recipe already leans on the private
  `_Py_InitializeMain` and `config._init_main`, and a changed signature fails the compile, not
  the run (READ, INFERRED).
- **The snapshot keeps the window (READ, INFERRED).** The limits live in the thread state, in
  linear memory, which Wizer captures. Nothing resets them: `_PyThreadState_Attach`
  (`pystate.c:2245`) and the core start (`pylifecycle.c:943`) call
  `_Py_InitializeRecursionLimits` only while `c_stack_hard_limit == 0`, and a new thread state
  is the only thing that zeroes it (`pystate.c:1593`). `run` skips `init_interpreter` on the
  snapshot. The research set the window at each `run`, not before the snapshot, so this exact
  path was not executed; criterion 2 (the message exactly "used 112 kB" on both binaries) is the
  check that would see a lost window, which would print 16368 kB or trap.
- **One thread state, whatever the host does (READ, EXECUTED).** No threads, no
  `_interpreters` in the guest (the memo's `t7.py`). Under spec 055 a session's turns may come
  from several host threads, but the window is linear-memory state and `max_wasm_stack` is
  measured from each call's entry, so a turn on any thread with room behaves as a `run`
  (INFERRED). `run_async` runs the guest on a worker thread: 16 MiB on macOS, `ulimit -s` on
  glibc Linux, 2,000,000 bytes on Windows (the memo, READ), all above 512 KiB.
- **The fix holds for nearly every shape, and its depths do not depend on the host
  (EXECUTED).** Of my first batch of 34 shapes (`extra-29.jsonl`; the second batch is F1's), none
  traps at 512 KiB on arm64 under the window: 23 raise "Stack overflow", 8 stop at the recursion limit with 10.5 to 12.4 KB of
  linear stack, as before, and 3 end in an ordinary Python exception (`asyncio`, `sqlite3`'s
  wrapper, and one case of mine that raised outside its `try`). Where it raises, the depth is set by linear bytes, so it is the same on arm64 and
  x86_64: `__repr__` 214, `lru_cache` 208, `np.vectorize` 99, `sorted(key=)` 52 on both
  (`stackmin-*-orig.jsonl`, `at_512`). Criterion 1's floors are therefore host-independent; only
  whether a shape raises or traps depends on the host.
- **The 512 KiB default and the explicit setting (READ, EXECUTED).** `_engine` is private;
  `run` and `run_async` take no engine; `tests/public_api.txt` does not change. A cached
  `.cwasm` deserializes under any `max_wasm_stack` (EXECUTED: `stackmin.py` deserialized one
  module under each stack size it tried). Setting 512 KiB is a no-op on wasmtime 49 and pins it
  against a later default change. An embedder with its own engine is outside the runner;
  README step 4 speaks to them.
- **Imports fit the window (EXECUTED).** On the plain binary (which imports at run time, as the
  snapshot will under spec 069), `import pandas` writes at most 44,096 bytes of linear stack,
  matplotlib with `pyplot` 28,128, a numpy/pandas/matplotlib PNG workload 44,096
  (`imports-plain-29.jsonl`). The guard raises only past 112 KiB. 069 and this spec do not
  interfere beyond one file.
- **1 MiB on x86_64 does what README step 4 says (EXECUTED, `fixed-amd64.jsonl`).** At 1 MiB
  with the window, `repr`, `json.dumps` and `pickle.dumps` of a 100,000-deep list raise
  `RecursionError`, `eval` of 100,000 `-` and of 199 parentheses raise `MemoryError`;
  `json.loads`, `==`, frees and exception groups still trap, as the memo found on arm64.
- **The existing named-trap check is unaffected (READ, EXECUTED by the research).**
  `test_a_stack_overflow_is_named` recurses in Python only and traps freeing at exit, window or
  not (`evidence/t6-29.jsonl`: "call stack exhausted" after 37,980,121,886 fuel).

## Acceptance criteria against the design

| # | Criterion | Would it catch its defect? |
|---|---|---|
| 1 | Python-through-C rows raise, both binaries, depth floors | Yes for the window's loss or shrinkage. The floors are host-independent (above). But every row runs on every release host, and the set of rows leaves out the shapes that trap (F1). |
| 2 | message exactly "used 112 kB" | Yes: a lost or resized window changes the number. The stand-in is honest. |
| 3 | default engine; wasmtime CLI | Yes, but the default engine has far more margin than the runner's own (`bare-amd64.jsonl`: ElementTree 344 KiB bare against 576 KiB with fuel), so it guards the easy case. How the judge's driver takes a default `Config` is unstated (F11). |
| 4 | data limits, a completing and a trapping depth | Its trapping side would catch a larger stack. Its completing side sits 1% below the x86_64 edge for frees (F2). |
| 5 | `_WASM_STACK` stated | Yes, as a unit check. |
| 6 | nothing else moves | Only for the judge as it stands; CPython's suite is not in it until 065 lands (F6). |
| 7 | recipe the only source change | Yes (spec 020's check). |
| 8 | docs | Text needs F1, F2, F7, F9. |
| 9 | spec 065 by landing order | Depends on 065's text agreeing (F5). |

## Findings, most severe first

### F1 (high). The 128 KiB window does not make every Python-through-C shape raise, on either host: callbacks out of expat trap at wasmtime's default stack, and x86_64 was never measured

The spec's Intent, Decision 1, the README text, the CHANGELOG and question 102 all say that, at
512 KiB, "recursion that runs through Python code raises `RecursionError` … for any embedder",
with "about a quarter of margin over the worst shape". The sweep behind it measured 23 shapes on
darwin-arm64 only, and the worst was `lru_cache`.

EXECUTED (`margin-table.txt`; the smallest stack at which each shape stops trapping under the
window, runner's engine):

| shape | arm64 | x86_64 | at 512 KiB |
|---|---|---|---|
| `xml.parsers.expat` `StartElementHandler` that parses again | 544 KiB | 696 KiB | **traps on both** |
| `xml.sax` `ContentHandler.startElement` that parses again | 504 KiB | 640 KiB | raises on arm64 with 2% to spare; **traps on x86_64** |
| `xml.etree.ElementTree` `XMLParser(target=…)` whose `start` parses again | 448 KiB | 576 KiB | raises on arm64; **traps on x86_64** |
| `heapq.heapify` with a `__lt__` that heapifies again | 416 KiB | 456 KiB | raises; margin 1.23 / 1.12 |
| `functools.lru_cache` recursion (the memo's worst) | 352 KiB | 400 KiB | raises; margin 1.45 / 1.28 |
| `json.loads(object_hook=…)` recursion | 352 KiB | 392 KiB | raises; margin 1.45 / 1.31 |

These are not regressions: without the window they trap too, sooner (INFERRED: the window
only adds a place to raise). The defect is in what the spec promises and checks. So the memo's
"about a quarter" is the arm64 margin of one shape; x86_64 frames on the
runner's engine are up to 29% larger than arm64's for the same shape (0 to 14% for the memo's
24 shapes, 5 to 29% for mine; `compare.txt`), and C libraries with heavy native frames (expat) behave like the data shapes
of Decision 5, at a native/linear ratio near 6. Windows was not measurable here; its wasm
frames use Cranelift's own convention, so x86_64 Linux is the nearer proxy (INFERRED). The
default engine is far roomier (ElementTree 344 KiB bare on x86_64, `bare-amd64.jsonl`), so the
thin case is the runner's own fuel-and-epoch engine, the one most users get.

A smaller window would reach them, at a price (EXECUTED, `window-amd64.jsonl`, x86_64): the
ElementTree shape needs 576 KiB at 128 KiB, 416 KiB at 96 KiB (margin 1.23) and 248 KiB at
64 KiB (2.06). Scaling the expat row the same way (INFERRED: about 6.2 native bytes per linear
byte), 96 KiB is not enough for it and 64 KiB is. But depths scale with the window less 16 KiB:
at 64 KiB, `__repr__` would stop near 92 levels and `sorted(key=)` near 22.

Asked of the spec, before build:
1. Re-measure the window on x86_64 as well as arm64 (the image `wp040-amd64` runs wasmtime-py
   49 under emulation; `probes/stackmin.py` does the bisection), and state the margin per host
   and per shape in the memo and Decision 1, the C-library callbacks included.
2. Decide, and say why: keep 128 KiB and move "recursion through a callback from expat
   (`pyexpat`, `xml.sax`, `ElementTree`'s parser target)" into Decision 5's documented limits,
   with a criterion-4-style pair; or take a smaller window and its depths. Either way the
   Intent, README, CHANGELOG and question 102's facts stop saying "every" or "any".
3. Add the thinnest shape that still raises (`heapq` with `__lt__`, margin 1.12 on x86_64) to
   criterion 1, so a wasmtime whose frames grow by a tenth turns a check red on the host where
   it happens, before a user's guest traps.

### F2 (medium). Criterion 4 and the README's limits are arm64's numbers; on x86_64 the free check's completing depth sits 1% below the edge

Native frames set these depths, so they differ by host (EXECUTED, `crit4b-amd64.jsonl`, x86_64,
512 KiB, window):

| kind | spec: completes / traps | README "about" | last good on x86_64 |
|---|---|---|---|
| freeing a nested list | 2,000 / 3,000 | 2,300 | 2,025 (2,050 traps) |
| `json.loads` of nested arrays | 1,000 / 2,000 | 1,200 | 1,100 (1,125 traps) |
| `eval` of nested parentheses | 120 / 150 | 140 | 132 (135 traps) |

The pairs pass on x86_64 today (`crit4-amd64.jsonl`), but 2,000 frees completes with 1% to
spare. A wasmtime patch release, real AVX hardware against the emulated run, or Windows' frames
could make it trap, and the release's Windows job is the first place that would show
(AGENTS.md 6b). The README's "about 2,300 … 1,200 … 140" overstate x86_64 by 6 to 14%.
Asked: choose completing depths with room on both hosts (for example 1,500, 800 and 100) and
trapping depths well past the arm64 edge (3,000, 2,000 and 150 are fine); state the README's
limits as the lower host's (about 2,000, 1,100, 130), or as ranges. The memo's other depths in
Decision 5 (repr 1,900, `json.dumps` 1,470, `==` 1,550, `hash` 2,500, `map` 2,950, groups 830)
are arm64's too and need the same treatment.

### F3 (medium). The judge's driver is not the runner's engine, so the judge sees more stack than users get

Decision 3 says the judge's driver sets 512 KiB "so every check that runs Python runs at the
contract's stack". The stack, yes; the frames, no. `guest.engine()` turns on fuel only; the
runner turns on fuel and epoch interruption (READ, `guest.py:45–51`, `runner.py:3411–3422`),
and epoch checks make Cranelift's frames larger (INFERRED from what follows). EXECUTED: CPython's
`test_ordered_dict` (`CPythonOrderedDictSubclassTests.test_highly_nested`, freeing a
1,000-deep `OrderedDict`) ends in a stack-overflow trap on the runner's engine, with or without
the window, and passes, 299 run, on a fuel-only engine (`cpy-0.jsonl`, `cpy-29.jsonl`, and the
`cpyrun_fuelonly.py` run in this folder). The CPython-suite memo lists it as passing (297, its
`per-module-results.tsv`), because it ran through this driver. So spec 065's five trap entries,
the memo's section 3 table and the upstream suites (which also run through `guest.run`,
`upstream.py:709–713`, READ) all measure an engine with more room than `run` gives; a sixth
CPython test traps on the runner's engine and the judge does not see it.
Asked: `engine()` in `tests/harness/guest.py` also sets `epoch_interruption = True` (with a
deadline far off, as the research's `probe.py` does), in this specification since it already
edits that function, so the claim becomes true; or the spec says plainly that the judge's
driver is roomier and by how much. Either way, criterion 1 and 4 already run through `run`,
which is right.

### F4 (medium). lxml's callback shapes are unmeasured; the builder's set has them

Main now carries lxml with libxml2 and libxslt (spec 046 landed at `41dffc2`), after the frozen
set this research used, which has no lxml (READ: `MANIFEST` has no line naming it; my lxml
probes fail to import there). libxml2 parser targets, XPath extension functions, resolvers and
XSLT extension elements all call Python from deep C, the class F1 shows to be the thin end.
Asked: the builder measures them on the built set (target parser, XPath extension function,
resolver, `XSLT` with a Python extension) and either lists them with Decision 5's limits or in
criterion 1. Also: rebase onto main and reword "on main ef1441b" accordingly.

### F5 (medium-low). Spec 065's text says the opposite of Decision 7

065 at `b215132` says 071 "closes the five trap entries", that if 071 lands first 065's builder
re-derives with "no trap entries", and that each trap gap closes with spec 071's file (its
lines 49–50, 95–97, 121–131, 448; READ). 071's Decision 7 closes one, keeps four, and moves
their closer to question 102. Whichever lands second will find two specifications that
disagree. Asked: name, in Decision 7, the 065 sentences it supersedes, and have 065 revised (or
the lane's landing notes say which governs), so 065's builder is not following the old text.

### F6 (low). CPython's own suite under the window: measured by the research for five entries only; a criterion should cover it

Criterion 6 judges the landed judge; CPython's suite joins it only with 065. The memo ran only
the five trap entries under the window. Decision 7 says that if 071 lands first, "065's builder
derives on this set", so a test that passes today and fails under the window would become one
of 065's expected failures without anyone choosing that.

EXECUTED (`cpy-29.jsonl`, `cpy-0.jsonl`): 82 modules most likely to recurse (json, pickle,
copy, descr, class, ast, compile, sys, dataclasses, xml_etree and its C twin, pyexpat,
plistlib, marshal, exceptions, exception_group, builtin, call, typing, grammar, patma,
tokenize, re, collections, functools, isinstance, richcmp, reprlib and 54 more) on the research
snapshot, with and without the window. 80 ran to a result (`test_datetime` blocked on my
probe's fake clock and `test_logging` passed my 900 s limit; both harness limits, not the
guest). In none of the 80 did the window lose a pass: 65 ran clean under it; 12 ended with
failures, errors or a trap and give the identical counts and failing tests without it (among
them the trap in `test_exceptions`, a known 065 entry, the one in `test_ordered_dict`, F3, and
my fuel cap in `test_math`); 3 did not load (a missing test module, a missing file, a
module-level skip). Nineteen of them, the parsers and recursion-heavy ones, also give
the same counts on x86_64 under the window (`cpy-amd64-29.jsonl`). So the risk looks small. But
this is 80 of about 490 modules, under `unittest` rather than regrtest, and the research ran
none of it.

Asked: a criterion that the builder runs the CPython-suite memo's harness over every module on
the built set and compares per-module passes with the memo's 27,503; a loss is a finding before
landing, not a derived class.

### F7 (low). The CHANGELOG section is wrong

The spec writes its entry under 0.1.0a6. `v0.1.0a6` is tagged and main's CHANGELOG opens with
"0.1.0a7 — unreleased" (READ). Asked: the unreleased section, as spec 046 did at `64db5bb`.

### F8 (low). Question 102: one false fact, option (a)'s cost incomplete, and an option missing

- Its second fact ("all 23 … raise … for every embedder") is false by F1.
- Option (a)'s threading cost is right as far as it goes (a thread-bound `sqlite3` connection,
  Ctrl-C from another thread) but leaves out: `contextvars` and thread-locals set by the caller
  (a web request's context, a tracing span) are not seen by a provider or tool on the runner's
  thread unless the runner copies the context; `signal.signal` refuses a non-main thread
  (already true under `run_async`); `threading.stack_size` is process-wide, so the runner must
  set it under a lock or keep its own pool, or it changes threads other code makes; and under
  `run_async` with a caller's `executor` the guest runs on the caller's threads, whose stack
  the runner does not choose, so (a) means a second hop there. "`run_async` already runs host
  functions on a worker thread" is true of the default pool only.
- A fourth option follows from F1: a smaller window (64 KiB), which closes the expat shapes at
  the default stack for every embedder at the cost of halving the depths again. It closes none
  of the four 065 entries.

### F9 (low). The cost to working programs, and the README's lower bound

- "After 50 to 250 levels": `np.sort` of an object array whose `__lt__` sorts again stops at
  42, `repr` of a `pd.Series` holding itself at 51, `sorted([A(), A()])` with a recursive
  `__lt__` at 53 (EXECUTED, `extra-29.jsonl`, `extra2`). Say "40 to 250".
- The change is not only "traps become errors": a program that recursed between the new and the
  old depth and finished (a dataclass `__eq__` over a 300-long linked list, say: about 244 levels
  now, about 470 before; INFERRED from `eq_self`) used to work and now raises. Decision 1 and
  the CHANGELOG say "about half the depth it reached before trapping", which is true; one
  sentence saying such programs now raise would make it plain.

### F10 (low). Decision 8 names 069 only; 055 also edits `init_interpreter`

055 (at `e1ee581`) takes a strong reference to the bootstrap's turn function in
`init_interpreter` and adds two exports to `recipes/reactor_main.c` (READ, its Decision on
`turn`). Its hunk lands near the bootstrap's import; this one right after
`Py_InitializeFromConfig`. Asked: name 055 beside 069, and say a RecursionError inside a turn
no longer ends the session (055's "a trap ends the session" loses this case).

### F11 (low). Criterion 3's "the judge's own driver with a default `Config`"

`tests/harness/guest.py`'s `engine()` takes no configuration and caches one fuel engine for the
session (READ). The check must either build its own engine or the driver grows a parameter, a
judge change either way. Say which, so the builder does not swap the cached engine under other
checks.

### Notes (no change asked)

- **N1. The bottom 8 KiB of the window is now reachable (READ, INFERRED).** A recursion check
  that finds the stack pointer between `start` and `start + 8 KiB` calls `Py_FatalError
  ("Unrecoverable stack overflow")` (`ceval.c:285–304`), an abort and an "unreachable" trap,
  not a RecursionError; one that finds it below `start` does nothing (`_Py_MakeRecCheck`), so
  the guard goes quiet and the native stack decides. CPython's own invariant (no two checks
  more than 8 KiB of linear stack apart, `pycore_pythonrun.h:44`) keeps both rare; no shape
  here showed either. Before the window, both lay 16 MiB down and were never reached.
- **N2. The calling thread.** The README could say, beside the runner's stated stack, that
  `run` needs a calling thread with 512 KiB plus the host's own frames free; an application that
  shrank `threading.stack_size` or passes `run_async` an executor with small threads does not
  have it. This is true today too.
- **N3.** The research binaries hung at interpreter exit for minutes after printing their last
  line, three times on arm64, never on x86_64 (my `stackmin.py`, which keeps an engine per stack size; the
  research's `probe.py` keeps one). It did not affect any result; noted only so a builder who
  sees it knows it is not the guest.
- **N4.** Python-to-Python recursion and `test_a_stack_overflow_is_named` are untouched, as the
  spec says.

## Constitution checks

- §4.1: met; no patch, a recipe line through a documented API (READ).
- §4.3: one window for every host; no host-specific branch (READ).
- §4.10: the memo labels its claims; but "for any embedder", "every Python-through-C shape" and
  "about a quarter of margin" are stated beyond what was run (F1, F2).
- §4.11: the right instinct, documenting what still traps; the list is incomplete (F1, F4).
- §4.15: no default loosened; `max_wasm_stack` is pinned at today's value (READ).
- §5.2: the open choice is put to the owner as question 102, not left in the spec; F1 adds one
  decision the spec must make itself (keep 128 KiB and list expat, or shrink).

## Scoreboard

`uv run pytest tests/checks/test_rules.py -n 3` in the worktree: 38 pass, 2 blocked (the
worktree has no artifact directory and no prior-art clones), 0 fail (EXECUTED, `rules.txt`).
The diff is `context/` only, so the rest of the judge is main's.

## Verdict

**Ready once F1 to F5** are answered in the specification (F6 to F11 written in), with a short
confirmation by a reviewer, since F1's answer may move the window. The mechanism is right: one
recipe line, CPython's own API, no patch, a stated stack. What is wrong is how far it was said
to reach: expat's callbacks still trap at the default stack on arm64, and expat's, SAX's and
ElementTree's on x86_64; the margin was measured on one host; criterion 4's numbers are that
host's; and the judge's driver measures a roomier engine than the runner's.

## One line

The window is the right fix and the right call, but it was sized and checked on arm64 and on a
roomier engine than users get: expat callbacks still trap, x86_64 has a thinner margin, and the
spec must say so, check it, and pick its numbers for both hosts before it is built.

## Confirmation of 071's revision (addendum to the pre-build review)

- **Date:** 2026-10-18. **Reviewer:** the same fresh agent, still not the author.
- **Reviewed:** `spec/071-deep-recursion-raises-recursionerror` at `8d9f74e`, rebased onto main
  `6fd89e0` (READ, `git log`): the spec rewrite, question 102's revision, and the memo's addendum
  with its `v2/` scripts and evidence. The lane's rulings are taken as given: keep 128 KiB; the
  expat traps are listed and closed by question 102; numbers that hold on both hosts; epoch
  interruption in `guest.engine()` as a judge change; four of 065's nine entries close, and
  `test_highly_nested` becomes a new one. New scope since the review: Decision 9 (063's F3).
- **Ran (EXECUTED).** Scripts and logs are in `confirm/` beside this file. Nothing was written in
  a git tree or in the main tree's `build/`.
  - `d9.py` with `chain.c`: in each case a fresh process runs the spec's detection, as A
    (`sigaction` + `dladdr` + `os.path.samefile` with `wasmtime._ffi.dll._name`), and as an
    alternative B (`dladdr`'s load base compared with that of a wasmtime-py symbol). It then
    runs four traps on a runner-like engine: `unreachable`, stack exhaustion, an out-of-bounds
    load, and division by zero. The cases are: nine faulthandler orders, a Python-level
    `signal.signal` after the first engine, and a native handler installed before or after
    the first engine. The native handler (`chain.c`) is a stand-in for a crash reporter. In
    mode 1 it chains with the original siginfo and context; in mode 2 it reports and exits.
    `d9-amd64.log` and `d9-arm64.log` ran on Debian glibc 2.41 (the `wp040-*` images);
    `d9-musl-amd64.log` and `d9-musl-arm64.log` ran on Alpine (musl), where wasmtime-py 49.0.0
    installs and runs.
  - `rules.txt`: `test_rules.py` on `8d9f74e`: 38 pass, 2 blocked (no artifacts or clones in the
    worktree), 0 fail.
  - READ: wasmtime 49's `crates/wasmtime/src/runtime/vm/sys/unix/signals.rs` (`foreach_handler`,
    `trap_handler`) and `crates/wasmtime/src/config.rs:3024–3043` in `context/prior_art/wasmtime-v49`;
    CPython 3.15.0's `Modules/faulthandler.c:536–576`.

### The pre-build findings

Each finding is answered in the text (READ, against the spec's Disposition):

- **F1.** Both hosts' margins are in Decision 1. Expat callbacks are a listed limit, with a
  criterion-4 pair, and option (d) is in question 102. The `heapq` row is in criterion 1. The
  "every" and "any" overclaims are gone from the spec and question 102. They survive in the
  memo's closing sections (C6).
- **F2.** The lower host's numbers are used throughout. They agree with mine: frees 2,033
  against my bracket of 2,025 to 2,050; `json.loads` 1,121 against 1,100 to 1,125; brackets 132
  against 132 to 135. One slip in criterion 4 remains (C5).
- **F3.** The driver now makes the runner's engine, named as a judge change.
  `test_highly_nested` is listed by id. Criterion 6 separates what the engine moves from what
  the window moves.
- **F4.** Criterion 10 measures the four lxml shapes on the built set, on both hosts.
- **F5.** Decision 7 rewrites the 065 entries: four close, five (six) remain. 065's text agrees.
- **F6.** Criterion 6 runs the CPython suite through 065's groups, or through the memo's
  harness against the 27,503 passes.
- **F7 to F11.** All written in. N2 is in the README.

Question 102 is fair and now complete: the costs of option (a) are listed, option (d) is there,
and the false fact is gone.

### Decision 9, scrutinised

- **What holds (EXECUTED, all four Linux runs):**
  - **Faulthandler orders:** detection agrees with the outcome in every order. "None",
    "enabled before" and "enabled after, then disabled" read wasmtime's handlers and return all
    four traps. "Enabled after" and "enabled before, disabled after" read `python` or `SIG_DFL`,
    and the host dies with SIGILL (exit −4).
  - **musl and glibc:** identical results. The handler is the first word of `struct sigaction`
    in both.
  - **Refusing is right, not merely safe.** A Python-level `signal.signal(SIGSEGV, …)` after the
    first engine does not kill the host on a trap; it hangs it forever at full CPU (exit
    "TIMEOUT" after 30 s). The handler returns, and the faulting instruction runs again. The
    check refuses that case too.
  - **Warning is not enough.** A warning would let the next trap end the process, and with it
    every other guest the process is running. Repair is not possible from Python: a `ctypes`
    callback cannot run in a fault's context.
  - **The not-taken alternative is honestly put.** `signals_based_traps = False` does remove the
    defect. wasmtime 49 then forces the heap and table Spectre mitigations off: silently when
    they are unset (which is why the memo's "nospectre" probe needed no flag), and it refuses the
    engine when they are set on (`config.rs:3024–3043`). That is a sandbox loosening, and the
    owner's call under §4.15.
- **Cost (EXECUTED):** 10.7 to 19.9 µs per check with A, 5.2 to 9.9 µs with B, across both
  architectures and both C libraries. That is noise beside an instantiation.
- **Races (READ, INFERRED):**
  - Signal dispositions are process-wide, and reading them takes no lock, so concurrent `run`s
    each read safely.
  - The three reads are not atomic together, and the check is point-in-time. A change after it
    (from another thread, or from a host function during the call) is not caught; see C2.
  - The spec names the other-thread case. It does not name the same-thread case: a provider,
    tool or door host that enables faulthandler, or imports a library that installs a handler,
    in the middle of a call.

### Open items

- **C1 (medium). "Exact" holds for faulthandler only; for other handlers the check is
  conservative, and the text should say so.**
  - EXECUTED, all four runs: a native handler installed after the first engine that chains with
    the original context (as breakpad, crashpad and the JVM's libjsig do) lets all four traps
    return, yet both detections refuse it. A non-chaining one (mode 2) ends the host with its
    own exit code, 77, and is rightly refused. The two cannot be told apart from the handler's
    address, so refusing stays the right default.
  - Asked:
    - Decision 9 and the memo's A3 say "exact for faulthandler's orders; conservative for any
      other handler installed after the first call".
    - The `RuntimeError` message names the signal and "a handler installed or removed after the
      first run (faulthandler, `signal.signal`, or a native crash reporter)", not faulthandler
      alone.
    - The README tells embedders to install crash reporters before the first run. EXECUTED:
      `chain-before` returns every trap.
    - Criterion 11 gains a row for `signal.signal(SIGSEGV, …)` after the first call: refused
      (today it hangs the host). A chaining native-handler row would document the conservative
      refusal; that row is optional.
- **C2 (medium). Check before every entry into guest code, not once per instantiation.**
  - Spec 055's turns re-enter an existing instance. A faulthandler change between two turns
    would therefore pass a once-per-instantiation check, and a trap in the second turn would
    kill the host.
  - The check should also sit at the top of `_drive`, before `_check_preopens` runs its own wasm
    (`runner.py:2611–2615`), not just before `linker.instantiate`.
  - Asked:
    - Decision 9 says "before each call into the guest (each `run`, each session turn)". 055's
      turn path inherits that; 055 is not landed, so whichever lands second carries it.
    - *Not protected* says "a handler change made during a call, by a host function on the
      calling thread or by another thread".
- **C3 (low). Identify wasmtime's library by load base, not by path.**
  - `os.path.samefile(_ffi.dll._name, dli_fname)` stats the file twice for each signal. It
    raises if the wheel is upgraded or deleted on disk under a long-running process (an
    exception the spec's "a failed `sigaction` or `dladdr`" rule does not cover). It mismatches
    if the file is replaced in place.
  - Comparing `dli_fbase` with `dladdr` of a wasmtime-py symbol (`_ffi.dll.wasm_engine_new`)
    touches no file, costs half as much (EXECUTED, B above), and agreed with A in every case.
  - Either way, any exception should count as "not in place".
- **C4 (low). Make the message's remedy exact.**
  - "`faulthandler.disable()` undoes an `enable()` made after the first run" is true. EXECUTED:
    the "enabled after, then disabled" case returns every trap.
  - The other cases (enabled before and disabled after, a `signal.signal`, a native handler) have
    no Python-level undo; restart the process.
- **C5 (low). Criterion 4's rule versus one of its numbers.** The rule asks for the trapping
  depth to sit at least 40% past the higher host's edge. Freeing at 3,000 is 29% past arm64's
  2,324. Use 3,300, or restate the rule.
- **C6 (low). The memo's closing sections still overclaim.** "What it decides" and "One line"
  still say every shape raises "on any engine" and "for every embedder". Bring them in line with
  the addendum.

## Verdict on the revision

**Confirmed for build once C1 and C2 are written into the specification.** Both are text
changes: Decision 9's claim and message, the placement of the check, a criterion-11 row, and two
README and *Not protected* lines. They need no further review beyond the lane checking they are
there. C3 to C6 may be written in, or taken by the builder and answered in the landing notes.

The 128 KiB window, its numbers for both hosts, the judge-engine change and the handling of
065's entries are sound as revised. Decision 9's mechanism (read the handlers, refuse before
the guest runs) is the right one: on glibc and musl, on x86_64 and aarch64, it catches every
fatal faulthandler order and the hang a Python signal handler causes. It refuses one
crash-reporter setup that would have worked; the remedy is to install the reporter before the
first run.

## One line (confirmation)

The revision answers all eleven findings, and Decision 9 is the right guard. It must say it is
exact only for faulthandler, name any late handler in its message, and run before every entry
into the guest, not once per instantiation.
