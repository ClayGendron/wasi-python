# A lighter exit

- **Status:** research, 2026-10-31. Nothing in `recipes/`, `scripts/`, `src/`, `tests/` or the judge changed. It answers the owner's choice of 2026-10-31, "Research a lighter exit": measure what a lighter exit saves, prove which guarantees it keeps, and specify only if nothing native-visible changes.
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5), briefed by the session's lead agent.
- **Stands on:** spec 073 (`run` unfreezes, then `Py_FinalizeEx`, so a program's objects are finalized as natively); spec 157 (`_reactor._end`, a starting image's lighter ending); specs 055 and 162 (sessions end through `shutdown`); `2026-10-31-the-start-cost-of-the-zips-directory.md`, whose side finding started this.
- **Evidence:** [`2026-10-31-a-lighter-exit/`](2026-10-31-a-lighter-exit/), beside this file: every script named below and every `out-*.tsv` quoted. The spike binaries, the compiled cache and `prof-snap-pass.tsv` (221 KB) stay in the worktree's git-ignored `build/lx/`.
- **Repository state:** worktree `research/a-lighter-exit` at `dev` `a750e8fe`. The guest ran spec/167's set (`43005960`, CPython 3.15.2), the zip memo's set, through `wasi_python.run` with fuel metered. Native is the pinned host CPython 3.15.2, run with `-I` in a scratch folder.

Labels: EXECUTED means run here; READ means read in source; INFERRED means arithmetic or reasoning from those.

Terms. **Teardown** is `Py_FinalizeEx`, with the snapshot's `gc.unfreeze()` before it. The **frozen heap** is what `wizer.initialize` froze; **young** objects are those made since. A **probe** is a guest program whose outcome (stdout, stderr, exit code, files left) is compared with native CPython's. **Fuel** is wasmtime's count of executed instructions.

## The short version

1. **Teardown is 57.4 M of a bare snapshot call's 58.5 M, and 43.0 M of the plain binary's 323.8 M.** Three collections cost 27 M on the snapshot, the wipe of surviving modules 18.5 M, the interpreter's own state 10.9 M. Freeing memory is 18.5 M of the whole.
2. **Today matches native on all 45 probes on both binaries.**
3. **Every ending that skips the frozen heap's teardown changes something native-visible.** The young-only endings, spec 157's `_end` among them, differ on 6 to 12 of 35 probes, because what a program hangs on a pre-imported module is reached only through that heap.
4. **Skipping teardown only when nothing is left to finalize matched native on 43 probes; the 44th found a hole.** Its exactness can be tested, never shown, and it never skips on the plain binary or after `import numpy`.
5. **One change is exact: teardown frees nothing.** It keeps all 45 probes and the session probe, and saves 18.5 M on a bare snapshot call, 15.0 M plain, 67 M after a pandas groupby. It is worth a small specification.

## 1. Where the 57.4 M goes (EXECUTED)

wasmtime reports the guest's stack when fuel runs out, so `prof.py` reruns one call with its fuel cap stepped by 50,000 (100,000 plain) and records the stack at each stop. wasmtime keeps 20 frames; a cut stack takes its neighbours' phase. Teardown is the call less the same call ending in `os._exit(0)`: 1,159,714 on the snapshot, about 280.9 M plain (three runs; its hash seed is random).

| phase of `Py_FinalizeEx`, in order | snapshot | plain |
|---|---|---|
| `atexit` (no handler), flush stdout and stderr | 0.05 M | under 0.1 M |
| `gc.unfreeze()`, in `run` | 0.12 M | none |
| collection 1, the whole heap | 7.15 M | 4.5 M |
| `sys.modules` values to `None`, cleared; builtins restored | 0.75 M | 0.6 M |
| collection 2: the dead modules' cycles | 15.5 M | 6.1 M |
| the wipe of surviving modules' dicts | 18.5 M | 18.5 M |
| collection 3 | 4.65 M | 4.3 M |
| the interpreter's state, types, free lists | 10.9 M | 9.0 M |
| **teardown** | **57.4 M** | **43.0 M** |

By the function on top: 26.6 M deallocation, 19.3 M the collector's walk, 11.7 M the allocator; stubbing every free entry point saves 18.46 M. The zip memo's 23 M for plain teardown does not reproduce.

Teardown grows with what a program imported (`out-variants.tsv`):

| call | snapshot: call, teardown | plain: call, teardown |
|---|---|---|
| `pass` | 58.6 M, 57.4 M (98%) | 323.9 M, 42.9 M (13%) |
| `import numpy` | 831 M, 101.6 M (12%) | 1,226 M, 95.6 M (8%) |
| a pandas groupby | 4,711 M, 323.6 M (7%) | 5,131 M, 317.8 M (6%) |

## 2. What must survive (EXECUTED)

A wrapper runs each of `probes.py`'s 45 probes through `_reactor.run`, as the C side does, then raises `SystemExit(rc)` (today's ending) or runs a candidate and leaves by `os._exit(rc)`. **Native and today agree on all 45, on both binaries** (`out-matrix*.tsv`).

- **Unclosed files reach the host:** P01 plain; P02 beside a `def` (073's gap); P03 a `ZipFile`; P04 a script; P05 `-m`; P06 a `gzip` file, which natively ends unreadable with "Exception ignored"; P42 a `StringIO` and a closed file.
- **`atexit` runs, in order:** P07 prints `c b a`; P08 one handler raises, the rest run; P26 a `logging.MemoryHandler` flushes.
- **The program's finalizers run as natively:** P09 two `__del__` in `__main__`, in order; P10 cyclic garbage; P11 a weakref callback, which natively does not fire; P12 `weakref.finalize`; P13 a suspended generator's `finally`; P34 `atexit` before `__del__`; P40 `__del__` on an untracked instance.
- **What a finalizer sees:** P31 `sys.modules` cleared; P32 an import fails; P33 an import from cyclic garbage succeeds, collection 1 being first; P35 a global module intact.
- **Objects hung where only teardown reaches them:** P14 a `__del__`, P15 a file, P16 a `ZipFile` on `json` (frozen); P17 073's patched class; P18 an object on `fractions` (imported later); P19 a weakref to a program class kept on `json`; P30 an audit hook whose closure holds a file.
- **Streams and the exit code:** P20 output without a newline; P21 `sys.stdout` replaced by a file; P39 `sys.__stdout__` written after `sys.stdout` was replaced; P22 `sys.exit(3)`; P23 `SystemExit('bye')`; P24 an uncaught exception; P25 a stdout whose flush raises gives exit 120 and "Exception ignored".
- **Other teardown effects found:** P27 a `NamedTemporaryFile` and P28 a `TemporaryDirectory` are removed; P29 an uncommitted `sqlite3` insert rolls back; P37 `gc.callbacks` print; P38 a profiler; P44 and P45 an unclosed `os.scandir` iterator warns when the program turned warnings on. P36, P41 and P43 (hooks watching teardown) showed nothing natively and decide nothing.
- **Sessions:** `sess.py`'s turns leave an unclosed file beside a `def`, an `atexit` handler writing a file, and a file on `json`; `shutdown` keeps all three on both binaries.

## 3. The candidates

All ran under one wrapper text. "Direct" savings omit the wrapper, which adds about 2.5 M to the snapshot's teardown. "Differ" counts probes unlike native.

| candidate | differ | bare snapshot | bare plain | pandas groupby, snapshot / plain |
|---|---|---|---|---|
| X: flush, `os._exit` | 28 of 35 | 57.4 M direct | 43.0 M direct | 323.6 / 317.8 M direct |
| A: `atexit`, flush, drop `__main__`'s names, collect the young heap | 12 of 35 | 59.5 M | 40.9 M | 281.1 / 267.3 M |
| B: `atexit`, flush, tear down `__main__` and the modules imported since the start | 9 of 35 | 59.1 M | 32.0 M | 120.5 / 81.2 M |
| G: `gc.disable()` before teardown | 8 of 43 | 7.0 M direct | 4.2 M direct | |
| D: skip the interpreter's state | 1 of 45 | 10.9 M direct | 9.1 M direct | 49.8 / 47.8 M direct |
| **E: teardown frees nothing** | **0 of 45** | **18.5 M direct** | **15.0 M direct** | **67.5 / 67.2 M direct** |
| D and E | 1 of 45 | 25.4 M direct | 20.6 M direct | 101.2 / 101.2 M direct |
| F: skip teardown when nothing is left to finalize | 0 of 43, then 2 of 2 | about 57 M when it skips (INFERRED) | 0, never skips | 0, never skips |

Sources: `out-matrix*.tsv`, `out-work*.tsv`, `out-variants.tsv`, `out-gc.tsv`. D and E are spike binaries: `stub.py` puts `return` first in the named functions.

**A, the young-only ending.** It loses what a program hung on a pre-imported module (P14, P15, P16, P30) or on a module imported later (P18). Deleting `__main__`'s names one at a time leaves a finalizer without its globals (P31, P35). It fires weakref callbacks native does not (P11, P19) and writes a valid gzip where native's is cut short (P06). Adding spec 157's walk that flushes every open writer (AW, `_end` itself) fixes P15 and P30: 10 of 35 differ. Spec 157 accepted this for images; the owner's bar for `run` does not.

**B, the program's modules.** It keeps the order of finalizers (P18, P35) but not their reach: what the frozen heap holds stays alive (P14, P16, P17). Its finalizers see `sys.modules` intact and imports succeed (P31, P32). With the writer walk, 6 of 35 differ.

**CPython's own options.** None shortens finalization (READ: `Python/pylifecycle.c`, `Python/initconfig.c`); `os._exit` is X. `gc.disable()` skips collection 1, since `PyGC_Collect` returns at once when the collector is off (READ, `Python/gc.c:1794-1801`); it differs on 8 probes, 073's own among them, for 7.0 M. Why the later collections then miss those files was not established.

**D, skip the interpreter's state.** That step still finalizes objects a program can reach: an audit hook's closure (P30), and by the same path the codec registry (INFERRED). 10.9 M does not pay for it.

**E, teardown frees nothing.** Every finalizer still runs, in CPython's order, with CPython's state; only the memory's return to the allocator is skipped. The prototype stubbed `free`, `PyObject_Free`, `PyMem_Free`, `PyMem_RawFree`, `_PyMem_RawFree` and `PyObject_GC_Del` for the whole call; the program's own frees are 0.03 M (the floor falls to 1,134,503).

**F, skip only when nothing is left to finalize.** After `atexit` and the flush, a walk of the young heap decides. It skips teardown when it finds no young object with a finalizer; no weakref whose callback comes from outside `weakref` and `_weakrefset`; no class with `__del__` whose instances are untracked; no instance of an extension type outside a list of inert modules; and no audit hook, `gc.callbacks` entry, profiler, tracer or monitoring tool. Then it flushes `sys.__stdout__` and `sys.__stderr__` too, as their finalizers would, and leaves. Otherwise it falls back to today's ending. The frozen heap needs no walk: its only objects with finalizers are the nine standard-stream objects (`out-frozen.tsv`).

- It matched native on 43 probes on both binaries, skipping on ten (P07, P08, P12, P20, P22 to P25, P39, P42) (`out-matrix-f2.tsv`).
- **P44 and P45, written after, found a hole.** An `os.scandir` iterator is untracked and its class frozen, so the walk never sees it, and its warning is lost. Each such hole is a silent difference, found only by enumerating every type in the build with a finalizer or a visible deallocation, numpy's, pandas' and lxml's Cython types among them.
- It skips only for stdlib programs. `decimal` brings `_contextvars.Context`, numpy `ContextVar`, pandas Cython types; each falls back until audited. On plain the whole bootstrap is young and holds such types, so it never skips.
- Falling back costs the walk: `gc.get_objects()` is 0.13 M after `pass`, 1.25 M after `import numpy`, 6.3 M after a pandas groupby (`out-walk.tsv`).

## 4. Risks

- **Repeated `run` on one instance:** none. `run` refuses a second call, `shutdown` runs once, and the runner closes the store after each call (READ: `recipes/reactor_main.c`; `src/wasi_python/_call.py`). Unfreed memory goes with the instance.
- **Memory under E:** teardown's allocations get no freed blocks, so memory may grow a little. The prototype freed nothing for a whole pandas groupby and fit 1 GiB (INFERRED: teardown's share is small). A heap filled in teardown would trap where native would not; the specification measures it as a benchmark fact.
- **Files the host sees unflushed:** none under E (P01 to P06, P15 to P17, P21, P30, P42, sessions); under A, B and F, as listed.
- **Embedders relying on teardown:** E keeps its files and output. Its fuel falls, so a call that ran out in teardown may finish. Spec 069's check (b), plain over snapshot, rises from about 5.5 to about 7.7 (INFERRED: 323.9 − 15.0 over 58.6 − 18.5).

## 5. Recommendation

**Build no ending that skips teardown.** A and B change what native shows. F is the only design that could meet the owner's bar, and its exactness is a list of cases a probe can test and a missed case breaks silently: the 44th probe found one after 43 passed. It needs a C walk, an audit-hook watch and an audit of every extension type with a finalizer, and saves about 57 M only on stdlib-only snapshot calls.

**Specify E, "teardown frees nothing."** About 30 lines in `recipes/reactor_main.c`: just before `Py_FinalizeEx`, in `run` and `shutdown`, a `PyMem_SetAllocator` hook on the raw, mem and object domains whose `malloc`, `calloc` and `realloc` call the previous allocator and whose `free` does nothing. Public API; a recipe, not a patch (§4.1).

- **Saves** 18.5 M of a bare snapshot call (58.5 M to about 40 M), 15.0 M plain, 25 M after `import numpy`, 67 M after a pandas groupby: the stub's figures; the hook covers fewer entry points, so it may save a little less.
- **Keeps** 45 of 45 probes and the session probe.
- **Review:** it changes the build recipe, so it is reviewed before it is built (§5.6). It changes neither the guest's imports nor its exports, nor `src/`, so it is not structural.
- **Checks:** the probes that discriminate (P01 to P06, P09 to P19, P25, P29 to P33, P37, P39, P44) become rows on both binaries; a bare snapshot call's teardown stays under 45 M; check (b)'s rise is growth its news file claims.
- **Beside the zip memo:** its option (a) saves 19.3 M of the same teardown, partly by not freeing; the two overlap, so measure them together if both are built (INFERRED).

### Questions for the owner

1. **Specify "teardown frees nothing" (recommended), or leave teardown as it is?** 18.5 M a bare snapshot call; nothing native-visible changes on 45 probes.
2. **Should `run` offer an image's ending as a documented, non-native choice?** About 57 M a bare call and 280 M after pandas; 10 of 35 probes change; a public API change. Not recommended here.

## Not run, and unsettled

- No binary was rebuilt. E and D are spike copies; the `PyMem_SetAllocator` hook was not built, so its figure is the specification's first measurement.
- A, B and F ran as Python after `_reactor.run`, not in C.
- Memory growth under E was measured after, for specification 176 (EXECUTED, `mem.py`, `out-memory.tsv`): on the spike that frees nothing, teardown grew linear memory by at most 64 KiB in eight cases, from a bare call to a 2,000,000-key dict and a 10⁶-row pandas groupby; the stock binaries' teardown grew it by nothing. A counting hook in native CPython 3.15.2 (`tally/`, `out-native-tally.tsv`) found teardown asks at most 51,211 bytes of the three domains in nine stdlib programs.
- Native ran on macOS; probes compare outcomes, not stderr's text.

## One line

Teardown is 57.4 M of a bare snapshot call, and every way of skipping it changes something a program can see; letting it run but free nothing saves 18.5 M and changes nothing 45 probes can see, so that is the one specification worth writing.
