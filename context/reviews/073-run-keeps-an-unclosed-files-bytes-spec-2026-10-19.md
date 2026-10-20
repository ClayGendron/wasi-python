# Review of 073 — `run` keeps an unclosed file's buffered bytes (the specification, before build)

- **Date:** 2026-10-19
- **Reviewer:** a fresh agent (Claude Opus 5.5). I wrote none of spec 073, its probes or
  question 103.
- **Reviewed:** `spec/073-run-keeps-unclosed-files-bytes` at `ede53a7` on main `08de0c8` (the
  spec, its evidence folder `context/research/2026-10-19-run-and-the-frozen-main/`, question 103;
  READ). I also read:
  - AGENTS.md;
  - specs 003 (the `run` paragraph), 055, 069 (Decision 4 and the hand-off to 073) and 071;
  - `recipes/reactor_main.c` (`init_interpreter`, `wizer_initialize`, `run`, `shutdown`) and
    `recipes/reactor_bootstrap.py`;
  - `src/wasi_python/runner.py` (`_import_prelude`);
  - `tests/checks/test_v1_4_embedding.py` ((h), `test_main_starts_as_native`,
    `test_the_import_path_reaches_every_mode`) and `tests/known_gaps.toml`;
  - the pinned CPython 3.15.0 sources in the main tree (`Lib/runpy.py`;
    `Python/pylifecycle.c`: `add_main_module`, `init_interp_main` and `finalize_modules`);
  - the 083 worktree's spec header, and the 065 worktree's guest drivers.
- **Ran (EXECUTED, macOS arm64, wasmtime-py 49.0.0).** All runs were against main's set
  `build/sets/s-c50ca51fae5eb55b-c9dcb5b8`, read only, through the judge's own driver, using the
  073 worktree's `uv` environment with `PYTHONPATH=tests`. Every probe's root and output is
  beside this file; no git tree was written. Probes:
  - `rv.py`: the runner. It takes a case module and runs each case on both binaries.
  - `cases1.py` → `.out`: the cause and the second loss reproduced, and the fresh `__main__`'s
    cost taken apart.
  - `cases2.py` → `.out`: nine "hang it on the stdlib" idioms under a simulated fresh `__main__`
    (the residual's real extent).
  - `proto_run.py`: the specification's Decisions 1 to 3 as I read them, written as `run2`. It is
    exec'd into `_reactor`'s namespace under the file name `<reactor>` and called from a `-c`
    expression, exactly as spec 054's prelude calls `_reactor.run`.
  - `cases3.py` → `.out`: today's `run` against `run2`, through the same wrapper, in each mode.
    It covers bytes, `__name__`, `sys.modules['__main__']`, the frozen test, pickling,
    `inspect.getsource`, `doctest.testmod`, `typing.get_type_hints`, the warnings registry, the
    globals, `sys.argv`, `sys.path[0]` and an `atexit` handler that pickles a `__main__` class.
    It also covers the error paths (a traceback in a script and in `-m`, `-m` of a missing
    module, a directory without `__main__.py`, a missing script), `-m pkg`, a zip target and the
    stack depth.
  - `cases5.py` → `.out`: the same pair, `run` and `run2`, on `-c pass`, the gap, a script,
    `-m` and `import pandas`. This is the fresh `__main__`'s cost with the wrapper's compile the
    same on both sides.
  - `cases4.py` → `.out`: stand-in S4 (a bare module as `__main__`) and a reference count.
  - `cases7.py` → `.out`: whether any loaded module holds the original `__main__`.
  - `native.out`: the pinned host CPython 3.15.0 (`build/tools/python`, `-I`). It gives
    `__main__`'s globals for a script, a directory, `-m` and `-c`, and the messages and
    traceback for `-m` of a missing module, a directory without `__main__.py` and an `-m`
    error.
- **The judge:** not run. The branch differs from main only in `context/`. Main's state was
  accepted at `4f89510`. The checks this review is about do not exist yet. Their digests I
  recomputed with `scan.report` (below).

## What holds

1. **The cause, and the second loss (EXECUTED, `cases1.out`).**
   - Check (h)'s program keeps 100 bytes on the plain binary and 0 on the snapshot (fuel
     168,035,122 and 16,185,307, the same as the author's `probe.out`).
   - The same program in a fresh `__main__` keeps 100 on both.
   - A script keeps 0 on both binaries, and so does a directory holding `__main__.py`.
     Today's `-m` keeps 0 on both too (`cases3.out`, the rows marked "run -m").
   - The mechanism is what the spec says it is. I read `finalize_modules`: the removal step and
     the shutdown's collection run before the module wipe, and the wipe sees only modules whose
     weakref is still alive. `add_main_module` runs in `init_interp_main`, before `_reactor` is
     imported, so the capture of Decision 1 sees the six names `test_main_starts_as_native`
     expects.
2. **Option 4 keeps CPython's semantics for `__main__`, with the exceptions of F1 and F3
   (EXECUTED in the prototype, `cases3.out`).** In every mode, on both binaries, the following
   all match today's run (and are better in the ways noted):
   - `__name__ == '__main__'`, and `sys.modules['__main__'].__dict__ is globals()`;
   - the globals are in a collector generation, which today is false on the snapshot's `-c`;
   - pickling a `__main__` class and function round-trips;
   - `inspect.getsource` of a script's function works;
   - `doctest.testmod()` finds and passes its one test;
   - `typing.get_type_hints` resolves a string annotation naming a `__main__` class;
   - a repeated warning is shown once (`__warningregistry__` is in the globals);
   - `sys.argv` is unchanged (`['/prog.py', 'a']`, `['/app', 'a']`, `['/code/prog.py', 'a']`),
     and so is `-m pkg`'s (`['/code/pkg/__main__.py', 'x']`, `__package__` `pkg`);
   - a zip target works (`__file__` `/app.zip/__main__.py`, `__spec__` `__main__`);
   - the "can't open file" line is unchanged;
   - a script's traceback is unchanged, byte for byte;
   - the stack depth under a prelude is 4.
   - `__builtins__` becomes the module in a script, a directory and `-m`, as natively
     (`native.out`).
   - The bytes are kept in all five modes.
   - The improvements: a file left open in a script, a directory, `-m` or a zip now keeps its
     100 bytes, and an `atexit` handler now finds the program's `__main__` (see F3).
   - **Multiprocessing-style lookups** (`sys.modules['__main__'].__spec__` and `__file__`) see
     the same values during the run as today's temporary module gives. No process can be
     spawned in WASI, so nothing further applies.
3. **Isolation (READ, EXECUTED).**
   - `run` is once per instance (`run_called` in `recipes/reactor_main.c`), and every
     `wasi_python.run` call is a fresh instance. So one run's `__main__` cannot reach the next,
     with or without this change.
   - A nested `_reactor.run` (the prelude, or a program calling it) stays within one program's
     own trust.
   - No loaded module holds the original `__main__` on either binary (`cases7.out`: 36 and 70
     modules, no holder). So nothing keeps the old frozen namespace reachable.
   - `sys.modules['__main__'] = new` keeps the key's original position, so the removal order at
     finalization is native's.
4. **Sessions are untouched (READ).** `turn`, `_run_turn` and `_setup` are not in the Design.
   A session's close keeps 055's unfreeze. `run` and `turn` exclude each other per instance.
5. **The residual is real and narrow, and check D's gap is honest (EXECUTED, `cases2.out`).**
   - Under a simulated fresh `__main__`, the program's file keeps 100 bytes on both binaries
     when it hangs a function on any of these: `sys.excepthook`, `warnings.showwarning`,
     `codecs.register`, `copyreg.pickle`, a root-logger filter, `sys.addaudithook` and
     `atexit.register`. A `logging.basicConfig(filename=…)` file also keeps its bytes.
   - Only the patched frozen class (`json.JSONEncoder.default = default`) loses them (0 bytes
     on the snapshot, 100 on the plain binary).
   - Together with the author's module-attribute shape (15 of 70 modules), check D and its gap
     describe the corner fairly.
6. **Digests (EXECUTED with `scan.report`).**
   - D[snapshot]: `frozen heap: 1 finding(s), digest 049b78ef7b5a: …`.
   - (h)[snapshot]: `unclosed file: 1 finding(s), digest 7da6e52329c1: …`, which is the current
     gap entry's digest.
   - A's digests are the author's (`probe_check_a.out`), and its finding strings match the
     Design.
7. **Rule 4.**
   - (h)'s gap is removed because (h) will pass.
   - D is a new check, and its gap pins an exact digest.
   - (h)'s docstring edit is named.
   - Check (b), `START_FACTOR`, the goldens and the upstream allowances are untouched.
   - The lane accepts with `--accept-judge`.
   - Nothing is weakened.
8. **Check (b) is not restated.** The fresh `__main__` costs about +11 K on the snapshot's bare
   run (F4). So (b)'s factor stays near 10.7.

## Findings, most severe first

### F1 (Medium): check C pins a script's non-native globals, and S5 guards them, while the spec says "as CPython's own entry points" (EXECUTED)

- Native `python prog.py` gives `__package__` **None** and `__loader__` a
  **`SourceFileLoader`** (`native.out`). This is `pymain_run_file` → `set_main_loader` in CPython
  3.15.
- Decision 2 keeps runpy's values instead: `__package__` `''` and `__loader__` `None`.
  - Check C asserts those.
  - Stand-in S5 ("`__package__` given as None: C's script row fails") makes the native value a
    failure.
- A directory and `-m` match native exactly. `-c` matches too.
- The spec's own framing is "run a script … as CPython's entry points do", and the intent is
  "as native CPython". Pinning a known divergence in a new check makes a later move to native a
  judge change.
- **Fix, either way, before build:**
  - **Native:** give a file script `__package__` None and
    `__loader__ = importlib.machinery.SourceFileLoader("__main__", target)`. These are two
    arguments to `_run_code`, or one update after it. Check C then pins native's values, and S5
    becomes "`__package__` `''`".
  - **Or record the divergence:** say in Decision 2 and in check C's docstring that these two
    values are runpy's, not native's, and why they are kept.

  I lean to native. It costs nothing, and nothing in `tests/` pins `''` (grep).

### F2 (Low-Medium): stand-in S4 is wrong, because `test_main_starts_as_native` cannot see it (EXECUTED, `cases4.out`)

- A bare `type(sys)("__main__")` already has `__name__`, `__doc__`, `__package__`,
  `__loader__` and `__spec__`, all set to None by the module type. `exec` then inserts
  `__builtins__`.
- So `sorted(globals())` prints the native six names on both binaries, and
  `test_main_starts_as_native` passes. What changes is the values: `__builtins__` is a `dict`
  and `__loader__` is `None`.
- That is caught by check C's `-c` and stdin rows, which ask for a `module` and a `type`.
- **Fix:**
  - S4 should name check C's `-c` and stdin rows as what fails.
  - Criterion 3's list of "what must not move" should not lean on `test_main_starts_as_native`
    for the names' values. Check C guards those.

### F3 (Low-Medium): user-visible changes the spec does not name (EXECUTED, `cases3.out`, `native.out`)

All three changes move toward native. None is pinned by a check (grep of `tests/` for
`run_module`, `can't find '__main__'` and `No module named` in checks). But the spec says
"Tracebacks are unchanged", which is true only for a script.

1. **An `-m` traceback changes frames.** Today it shows `in run_module`,
   `in _run_module_code` and `in _run_code`. After the change it shows
   `"<frozen runpy>", line 201, in _run_module_as_main` and `line 87, in _run_code`, which is
   byte for byte native's. (`_report` strips runpy's frames only for a script, so `-m` shows
   them, as native does.)
2. **A directory or zip without `__main__.py`.** Today it prints an `ImportError` traceback
   (exit 1). After the change it prints
   `/usr/local/bin/python.wasm: can't find '__main__' module in '/empty'` (exit 1), which is
   native's form.
3. **An `atexit` handler in a script, a directory or `-m` now finds `__main__`.** Today it sees
   the restored, empty module: no `__file__`, no classes, and pickling a `__main__` class there
   raises `AttributeError`. After the change it sees `__file__` and the classes, and the pickle
   works.

**Fix:** name the three in Decisions 2 and 3, in the CHANGELOG bullet and in the Landing notes'
list, beside the `-m` not-found line.

### F4 (Low): the fresh `__main__`'s cost is overstated about tenfold or more, and rows also fall (EXECUTED, `cases1.out`, `cases5.out`)

The 0.53 M of `probe_fresh_cost.out` is mostly the compile of the wrapper's extra lines. One
extra line that only makes a module costs +196 K on the snapshot (`cases1.out`, `modonly`). The
bootstrap is precompiled, so it pays no such compile.

With the compile the same on both sides (`run` against `run2` through one wrapper,
`cases5.out`):

| program | plain | snapshot |
|---|---|---|
| `-c pass` | +29,676 | +10,904 |
| the gap | −20,085 | +62,918 |
| a script (`pass`) | −1,035,053 | −117,389 |
| `-m` (`pass`) | −73,283 | −8,386 |
| `import pandas` | +17,327 | +1,288,886 |

So Decision 8's "every check … pays about 0.1 M to 0.6 M" is wrong in size and in sign. Rows
still move past one part in ten thousand, so `--accept-growth` is still needed.

**Fix:**
- Restate the following as an upper bound, and give this measurement beside them: table row 4,
  Decision 1's "the same half million", Decision 8's band, Decision 4's "10.36" and question
  103's "for about 0.5 M instructions".
- Say that script and `-m` rows fall.
- Criterion 4's 0.6 M bound may stay, since it would still catch an eager import of `runpy`
  (about 20 M), but 0.1 M fits the measurement better.

### F5 (Low): every upstream suite is a consumer, and Decision 7's "no upstream allowance changes" is a prediction (READ; the risk INFERRED low)

- numpy's and pandas' suites run `/…/judge/drive.py` as a **script**
  (`tests/harness/upstream.py`, `guest_argv`). Spec 065's CPython groups run
  `regrtest_drive.py` as a script too.
- So every upstream group moves from runpy's temporary module to `__main__`, not only 065's.
- During the run, what they can see differs only in `__builtins__`, because today's temporary
  module is also `sys.modules['__main__']` and carries the same `__file__`. Their `M` lines read
  `__file__` from `sys.modules` and are unchanged. So a moved outcome is unlikely.
- **Fix:** name these consumers in Decision 10. If any outcome moves, the builder stops and
  names it as a further judge change, reviewed as a delta. Decision 7's sentence should read
  "none expected".

### F6 (Low): dated amendment lines in landed specs that state the old path (READ)

- Spec 003's `run` paragraph says `-m` runs as `runpy.run_module(name, run_name="__main__",
  alter_sys=True)`, "as CPython's `-m` does".
- Spec 069's Decision 4 names 073 as the closer, with a fix "that keeps the heap frozen … need
  not" restate (b).
- 069 itself added such lines to 023 and 054.
- **Fix:** add an "Amended 2026-10-19 by spec 073" line to 003 and 069 (and to 055's addendum,
  P10b, if the lane wants it). Each line names option 4.

### F7 (Low): D's gap should name question 103 in its text (READ)

- Decision 6 says the entry names question 103 as its closer. But `closes_with` is the bare
  `context/questions-for-the-owner.md`, and the reason says only "(spec 073, Decision 6)".
- The precedent entries write "(question 89)" in the reason.
- **Fix:** add "question 103" to the reason.

### F8 (Low): Decision 10 is stale on 083 (READ)

- 083 is no longer "drafted". It was revised against its pre-build review and builds after 065
  lands.
- It also edits `tests/known_gaps.toml` (it narrows 065's stepped-clock gap). So 073 and 083
  meet there too, not only in `tests/checks/test_v1_4_embedding.py`. Both merges are textual.
- The order in flight is 081 (landing next), then 065, then 083. Whichever of 073 and 083 lands
  second takes main's progress files and accepts again, as Decision 10 says.
- **Fix:** update the sentence.

## Notes (no action required)

- **Native script facts that stay non-native, and predate this spec:**
  - The script's directory is not put on `sys.path[0]` (spec 003, isolated mode).
  - A relative target keeps a relative `__file__`, where native makes it absolute.
- **The README's new fact** ("an object a program hangs on a module or class the snapshot
  pre-imported is never finalized") is broader than what I measured (`cases2.out`). "May never
  be finalized" is more accurate, and the advice ("close files with `with`") stands.
- **`_fresh_main()` sits before the `try`**, so a `MemoryError` there reaches the C side's
  `PyErr_Print` and returns 1. That is acceptable. The builder may move it inside the `try`.
- **I did not verify that the old frozen `__main__` is freed when it is replaced.** In my
  harness, today's outer `run` still holds it in its local `main`. Nothing else holds it
  (`cases7.out`), and it holds only six names, so a leak would be harmless.
- **The README's "three facts of its own" becomes four.**

## Verdict

**Ready once F1 to F4 are written in.**
- F1: decide between native script globals and a recorded divergence, then adjust check C and
  S5 to match.
- F2: correct S4's expected failure.
- F3: name the `-m` traceback, the missing-`__main__.py` message and the `atexit` change.
- F4: restate the fuel numbers as bounds, with the measured values, and say rows fall too.

F5 to F8 are wording and can be written in at the same pass. The design itself (option 4, run
in `__main__` through runpy's own helpers, the freeze and check (b) kept, the residual as a gap
naming question 103) is sound and measured. I found no isolation hole and no judge weakening.

## One line

Option 4 fixes both losses as measured and keeps `__main__` native in every mode but one. The
exception is a script, where check C would pin runpy's `__package__ ''` and `__loader__ None`
instead of native's. S4 names the wrong check, three native-ward changes go unnamed, and the
fuel cost is about +0.01 M, not +0.5 M. Ready once F1 to F4.

## Confirmation of 073's revision (addendum)

- **Date:** 2026-10-19. **Reviewed:** the revision `a45a765` on the rebased draft `2bf489a`, on
  main `2968512`. I read `git diff 2bf489a a45a765`: the spec, the amendment lines in 003 and
  069, question 103, the roadmap line and the new `native_atexit.sh` and `.out`.
- **Ran (EXECUTED, the same set and setup as above):**
  - `native_atexit_rerun.out`: the author's `native_atexit.sh`, re-run by me with the pinned
    host CPython 3.15.0.
  - `proto_run_rev.py`: my prototype changed to the revised Decision 2. A file script now gets
    `__file__` set, then a `SourceFileLoader`, or a `SourcelessFileLoader` for a target ending
    in `.pyc`. The code runs by `exec` in `__main__`, and `__file__` is popped in a `finally`.
  - `cases8.py` → `.out`: today's `run` against the revised `run2`, on both binaries. The cases
    are a script, a `.pyc` (compiled by the pinned 3.15.0), a directory, `-m` and `-c`. Each
    reports its globals during the run, its stack depth, and an `atexit` handler that reads
    `__file__` and pickles a `__main__` class. Also covered: a script traceback, a script whose
    `sys.excepthook` reads `__main__.__file__`, a syntax error, a missing script, a script that
    is only `pass` (for fuel), and check E's three rows.
- **I read `_PyRun_SimpleFile` in `Python/pythonrun.c`.**

### The author's correction to F3 is right

- Native CPython pops `__file__` from `__main__` after a file script, on every path. It does so
  in `done:`, before `PyRun_SimpleFileExFlags` prints an error. It pops only a `__file__` it set
  itself, and a fresh `__main__` never has one, so the two match.
- So, natively, an `atexit` handler after a script sees no `__file__` (my re-run of
  `native_atexit.sh`: `atexit: __file__ None C True`). A directory and `-m` keep it.
- My F3 item 3 said the handler "sees `__file__` and the classes" in every mode. For a file
  script that described my runpy-valued prototype, not native. The classes and pickling part
  stands. The `__file__` part was wrong for a file script, and the revision's table is the
  correct account.

### Each finding

1. **F1 — confirmed (EXECUTED, `cases8.out`).** The revised `run2` matches native
   (`native_atexit_rerun.out`) row for row on both binaries:

   | mode | `__file__` during the run | `__loader__` | `__package__` | `__spec__` | in `atexit`: `__file__`, `C`, pickle |
   |---|---|---|---|---|---|
   | script | `/prog.py` | `SourceFileLoader` | `None` | `None` | `None`, True, True |
   | `.pyc` | `/prog.pyc` | `SourcelessFileLoader` | `None` | `None` | `None`, True, True |
   | directory | `/app/__main__.py` | `SourceFileLoader` | `''` | `__main__` | kept, True, True |
   | `-m` | `/code/atx.py` | `SourceFileLoader` | `''` | `atx` | kept, True, True |

   - `__builtins__` is a module in every mode.
   - Today the script, `.pyc`, directory and `-m` rows give `__loader__` `None` (script and
     `.pyc`), `__package__` `''`, `__builtins__` a `dict`, and an `AttributeError` in the
     handler. So check C fails today as the revision says.
   - The `finally` keeps the error paths native too. A script's `sys.excepthook` sees no
     `__file__`, today and after, as natively, where the pop comes before the error is printed.
   - A script traceback, a `SyntaxError` and the "can't open file" line are byte for byte
     today's.
   - S5 (runpy's values) and S7 (no pop) each fail check C's script row as stated. S7 fails
     through the `atexit` part.
   - The `.pyc`-by-extension corner is recorded honestly. `runpy._get_code_from_file` already
     reads compiled code under any name, so only the loader type can differ from native's
     magic-number test.
2. **F2 — confirmed (READ).** S4 names check C's `-c` and stdin rows and says
   `test_main_starts_as_native` cannot see it. Criterion 3 says that check pins the names only.
3. **F3 — confirmed (EXECUTED, `cases8.out`).** Check E's three rows hold on both binaries:
   - `/usr/local/bin/python.wasm: No module named nope`, exit 1;
   - `/usr/local/bin/python.wasm: can't find '__main__' module in '/empty'`, exit 1;
   - `-m boom`'s frames `_run_module_as_main` and `_run_code` in `"<frozen runpy>"`, then
     `<module>` and `f`.

   E pins names and order rather than runpy's line numbers, which is right. Today every row
   differs, so E fails first. Decisions 2 and 3, the CHANGELOG's **Changed** bullet and the
   Landing notes name all three changes.
4. **F4 — confirmed (READ; the numbers are `cases5.out`'s, rechecked).**
   - Table row 4, Decisions 1, 4 and 8, criterion 4 (0.1 M), question 103 and the roadmap now
     carry the like-for-like figures.
   - Decision 4's arithmetic gives 10.708.
   - The revised file branch, which also builds the loader, still falls for a script that is
     only `pass`: −1,045,834 plain and −127,315 snapshot (`cases8.out`). So "script rows fall"
     holds for the revision too.
5. **F5 — confirmed (READ).** Decision 10 names the upstream suites as consumers and says what
   the builder does if an outcome moves: it stops, takes a delta review and edits no allowance
   (rule 4). Decision 7 says "none expected". The list of what such a suite sees differently now
   includes `__package__` and `__loader__`, which is correct.
6. **F6 — confirmed (READ).** Dated amendment lines are in 003's `run` paragraph and 069's
   Decision 4. 055's addendum is a research memo, which `context/README.md` says is "never
   edited after the fact". Leaving it alone is right.
7. **F7 — confirmed.** The gap reason ends "(spec 073, Decision 6; question 103)".
8. **F8 — confirmed.** Decision 10 now states 083's status, the second file 083 and 073 share,
   and the order in flight.

### Anything new

- **N1 (no action required): a script's stack is three frames shallower.**
  - With runpy's frames gone, `traceback.extract_stack()` in a file script falls from 7 to 4
    frames under a prelude-like wrapper (`cases8.out`). Without a prelude that is 5 to 2, the
    same as `-c`.
  - A directory falls from 6 to 6 and `-m` from 7 to 6, so neither moves much.
  - The change is toward native (native gives 1), and no check pins a script's depth (spec 054
    pins only `-c`). The builder may add it to the **Changed** bullet.
- Nothing else is wrong. The revision opens no isolation hole and weakens no judge entry.

### Verdict

**Confirmed for build.**

### One line

Every finding, F1 to F8, is written in. The revised design matches native CPython in every mode,
including that `__file__` is gone after a file script, which corrects my F3. Confirmed for build.

## The amendment of 2026-10-19 (question 103 answered: unfreeze before finalizing)

- **Reviewed:** `c8ffcc6` on `spec/073-run-keeps-unclosed-files-bytes`, rebased onto main
  `3561e55`. I read `git diff fed3a44 c8ffcc6`: the amendment section, Decisions 4 to 8 and 10,
  the Design, criteria 3 to 5, S6 to S9, 069's amendment line and `probe_combined.py`/`.out`. I
  also re-read `run`, `reactor_turn` and `reactor_shutdown` in `recipes/reactor_main.c`, checks
  (a) and (b) in `tests/checks/test_v1_3_data_stack.py`, and `_PyGC_Unfreeze` and
  `_PyGC_CollectNoFail` in the pinned `Python/gc.c`.
- **Ran (EXECUTED).** All runs were against a fresh `cp -Rp` copy of main's set, `set/` beside
  this file. The original's `python-stdlib.zip` has 554 hard links, and the copy has 1.
  Everything earlier in this review ran against the original. Each of those comparisons ran
  both sides on the same set, so its differences stand, and on the copy the bare rows move by
  about 5 K at most.
  - `cases9.py` → `.out`: today's `run`, the fresh `__main__` alone, and the combined design. The
    combined design is the revised `run2` followed by a `gc.unfreeze` reference taken before the
    program and called after `run2` returns, as the C `run` will call it.
  - The programs in `cases9.py`: bare, the gap, the patched class, `json.log`, the tampered
    `gc.unfreeze`, a `ZipFile` left open, an `atexit` handler printing `gc.get_freeze_count()`,
    and `import pandas`. It also measures how much of the unfreeze is the zip directory.
  - `meter.py` → `.out`: a metered snapshot `run` through `wasi_python.run`.

### The five questions

1. **The unfreeze matches 055's close, and the reference cannot be defeated (READ, EXECUTED).**
   - The call sits where 055's `shutdown` makes it: after the bootstrap returns and before
     `Py_FinalizeEx`. The error handling is the same (`show_and_drop`, then `Py_CLEAR`).
     `_PyGC_Unfreeze` is a list merge and cannot fail.
   - `atexit` handlers see the whole heap: `gc.get_freeze_count()` is 0 in the handler under the
     combined design, against 9,801 without it (`cases9.out`, "atexit-sees").
   - The reference lives in a C static, which no Python code can reach, and is taken before any
     guest code. `gc` is already in a snapshot program's `sys.modules`.
   - A program that replaces `gc.unfreeze` still keeps its bytes when the reference was taken
     first (`cases9.out`, "combined tampered": 100). The same program loses them without the
     unfreeze (0). This is the "tampered" row, the one S8 asks the build to show.
   - A program calling `gc.freeze()` again is undone too, since the merge takes the whole
     permanent generation.
   - What a program can still do to lose bytes (`os._exit`, a trap) loses them natively as well.
2. **No double unfreeze, and none skipped after an exception (READ).**
   - `turn` refuses if `run_called` is set, and `run` sets it first. `run` refuses if `turned` is
     set. `shutdown` refuses unless `turned` is set and no turn is still running.
   - So the unfreeze runs at most once per instance, by `run` or by `shutdown`.
   - A trap mid-run leaves `run_called` set, so every later export refuses.
   - A Python exception out of `_reactor.run` takes the `PyErr_Print` path and then still reaches
     the unfreeze and `Py_FinalizeEx`.
   - The one way to skip it is a `SystemExit` escaping `_reactor.run`, since `PyErr_Print` then
     exits. Only the bootstrap's own code before its `try` could raise one; a program cannot.
     This is not new: 055 swapped `PyErr_Print` for `show_and_drop` in `turn` for this reason,
     and the builder may do the same in `run` (N1).
   - Unfreezing twice would be harmless anyway, because a merge of an empty list does nothing.
3. **`START_FACTOR` 3 is the right restatement, with one sentence to soften (EXECUTED, READ).**
   - The built set should land near 3.81: my copy gives 167,511,125 ÷ 43,973,504, against the
     author's projected 3.82. A factor of 3 leaves 27% of margin, as 069 left about 25%. That
     margin hides no growth, because the fuel ratchet is red on any growth of the bare snapshot
     row past one part in ten thousand.
   - Check (a) is independent of (b) and still refuses any pre-imported package, so it holds
     decision 34 whatever (b) says.
   - One sentence overstates. "The margin can only widen … the snapshot's start and its unfreeze
     depend only on the stdlib bootstrap" is not exact. The snapshot's frozen heap holds
     zipimport's directory of the whole zip (2,658 members today), and the unfreeze's teardown
     frees it. Clearing that directory early saves about 0.36 M of the 28.2 M (`cases9.out`,
     "zd"), about 135 instructions a member, so the unfreeze grows a little as packages land.
   - The plain start pays far more per member, so the margin should still widen. But a faster
     plain start would narrow it. Better wording: "is expected to widen" (A2).
4. **The growth reason is measured, and criterion 4's band is right (EXECUTED).**
   - The combined run less the fresh-only run, through one wrapper, costs +28,330,759 bare. The
     combined run less today's costs +28,341,704. The author has +28,208,378, a 0.4% difference.
     Both fall inside criterion 4's band of +27.7 M to +28.8 M.
   - On the gap the unfreeze costs +28.34 M. After `import pandas` it costs +44.52 M, against the
     author's +45.19 M (1.5%).
   - The bytes, on the snapshot, combined against today:
     - the gap: 0 → 100;
     - the patched class: 0 → 100;
     - `json.log`: 0 → 100;
     - the tampered unfreeze: 0 → 100;
     - a `ZipFile` left open: unreadable → readable.
   - The fresh `__main__` alone still loses the patched class, `json.log` and the tampered row on
     the snapshot. So D fails today with three findings and passes after the build.
   - The digest D fails with today is `frozen heap: 3 finding(s), digest cfb1afda1a48` (computed
     with `scan.report`, the three strings in Decision 7's order), so the builder can confirm it
     rather than discover it. The two-finding digest `963ab1406da3` is right.
   - On the plain binary nothing is taken or called, and its rows move only by the fresh
     `__main__`.
5. **What the amendment changes in my confirmation.**
   - Nothing in F1 to F8 breaks. Decisions 1 to 3, checks A, C and E, and S1 to S5 and S7 are
     unchanged.
   - F7 is superseded honestly: no D gap is written, and D now passes.
   - Check C's "unfrozen" test stays meaningful, since the unfreeze runs after the program.
   - One new user-visible effect is not written down (A1, below).

### Findings on the amendment

- **A1 (Low-Medium, EXECUTED, `meter.out`): a metered snapshot `run` now pays about +28 M after
  its program has ended.**
  - The bootstrap flushes the program's output before `Py_FinalizeEx`, so an embedder's cap
    sized for the program can now run out in the teardown.
  - Simulated: `print('hello')` capped at 40 M used 29.4 M and returned `exit_code 0` before the
    change. With the unfreeze it returns `exit_code None`, `trapped "out of fuel"` and stdout
    `hello\n`. A cap of 70 M passes, using 57.8 M.
  - The README says this for sessions ("Size a metered session's `fuel` to cover it"). It does
    not say it for `run`, and the Design changes only the *Measured* row and the CHANGELOG's
    cost sentence.
  - **Fix:** one README sentence beside `run`'s `fuel`. On the snapshot a run's finalization
    costs about 28 M (about 45 M after `import pandas`), and a cap that runs out there ends
    "out of fuel" after the program's own output was written. The CHANGELOG bullet should say
    so too.
  - No check in `tests/` caps a snapshot `run` near that cost. The smallest caps are 10⁹, and
    400 M "past start-up".
- **A2 (Low, EXECUTED):** Decision 4's "the margin can only widen" should become "is expected
  to widen" and name the zip directory's small share (item 3 above).
- **N1 (no action required):** the builder may use `show_and_drop` instead of `PyErr_Print` on
  `run`'s error path, as 055 did for `turn`. It is not new and no program can reach it.

### Verdict

**Confirmed once A1 is written in** (A2 at the same pass). The unfreeze through a reference
taken at wizer time is sound, cannot be defeated by a program, runs at most once per instance,
and costs what the amendment says. `START_FACTOR` 3 is an honest restatement for the owner's
answer.
