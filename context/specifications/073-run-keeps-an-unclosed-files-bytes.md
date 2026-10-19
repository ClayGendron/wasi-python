# 073 — `run` keeps an unclosed file's buffered bytes

- **Status:** **drafted 2026-10-19** on `spec/073-run-keeps-unclosed-files-bytes` from main
  `08de0c8` (`ede53a7`); **revised 2026-10-19 against its pre-build review**
  (`../reviews/073-run-keeps-an-unclosed-files-bytes-spec-2026-10-19.md`, written in the lane's scratchpad with its probes, to be copied
  by the lane; verdict "ready once F1 to F4 are written in"; F1 to F8 are written in, and
  "Disposition of the pre-build review" says where), rebased onto main `2968512`. It is
  scheduled behind the packages (the owner, 2026-10-19): it builds when a build slot has no
  package ready. It changes the build recipe (`recipes/reactor_bootstrap.py`, compiled into both
  binaries at step 60), so it is reviewed once before it is built (constitution §5.6). It changes
  neither the guest's imports nor its exports. A different agent reviews the build.
- **Date:** 2026-10-19
- **Owner:** Clay Gendron
- **Kind:** **build-class** (§5.7): it changes `recipes/reactor_bootstrap.py` (the module
  `_reactor`: `run` gives every program a fresh `__main__`, and runs a script and `-m` in it). It
  touches no `scripts/`, no `downloads/SHA256SUMS`, no patch, no pin and no workflow. It is also a
  judge change: four checks added and one docstring edited in
  `tests/checks/test_v1_4_embedding.py`; one gap entry removed and one added in
  `tests/known_gaps.toml` (Decision 7). It changes `README.md` (the snapshot's facts) and
  `CHANGELOG.md` (0.1.0a7), and adds dated amendment lines to specs 003 and 069. It changes no
  public name, signature, field, default or option:
  **`tests/public_api.txt` does not change.** It changes nothing in `src/`. **The lane accepts it
  with `--accept-judge` and `--accept-growth`** (Decision 8).
- **Depends on:** 003 (the reactor and `_reactor.run`), 054 (the import path's prelude, which
  calls `_reactor.run` from a `-c` program), 055 (sessions, which keep their own unfreeze at
  close), 069 (the snapshot pre-imports no package; its check (b) and its gap (h), which this
  closes); all landed. It meets 081, 083 and 065 in flight (Decision 10).
- **Research it stands on:** spec 055's addendum, section 8, P10b
  (`../research/2026-10-18-bounded-sessions.md`); spec 069's review, R1 and R2, and 069's
  Decision 4; and this specification's measurement (EXECUTED,
  `../research/2026-10-19-run-and-the-frozen-main/`, the section below). CPython 3.15.0's
  `Python/pylifecycle.c` (`finalize_modules`, `add_main_module`), `Python/gc.c`
  (`_PyGC_Freeze`, `_PyGC_GetObjects`), `Modules/main.c` (`pymain_run_python`) and
  `Lib/runpy.py`, from the pinned tarball in the main tree's `build/Python-3.15.0` (READ); and
  `Python/pythonrun.c` (`_PyRun_SimpleFile`, `set_main_loader`), read for the review's F1.
  The pre-build review's own probes (EXECUTED there, beside the review): `cases1.out` to
  `cases7.out` and `native.out`.

## The problem

A program opens a file, writes to it, and ends without closing it. Native CPython writes the
bytes out when the interpreter finalizes, because the file object is freed and its finalizer
flushes and closes it. `run` on the snapshot loses them when `__main__` also defines a function.
The file ends up empty. The plain binary keeps them. This is the known gap
`test_run_keeps_an_unclosed_files_bytes[snapshot]` (spec 069, check h).

This specification's measurement found a second loss beside it. A program run as a script
(`run(["prog.py"])`) or as a module (`run(["-m", "prog"])`) loses the same bytes on **both**
binaries, though native `python prog.py` and `python -m prog` keep them. Its cause is different,
and its fix is in the same function, so this specification takes both.

## The cause (EXECUTED)

**On the snapshot, `__main__`'s namespace is in the frozen heap.**

1. The snapshot's initializer ends with `gc.collect(); gc.freeze()` (`recipes/reactor_main.c`,
   `wizer_initialize`). `gc.freeze()` moves every object the collector tracks into its permanent
   generation (`_PyGC_Freeze`). The collector never examines that generation again. `__main__`'s
   module object and its dict were made at start (`add_main_module`), so both are frozen.
2. A `-c` or stdin program runs in that dict: `exec(code, main.__dict__)`
   (`recipes/reactor_bootstrap.py`, `run`).
3. A function defined there points back at the dict (`g.__globals__`). The dict and the function
   now form a cycle, and the open file hangs from the dict.
4. At the end of `run`, `Py_FinalizeEx` reaches `finalize_modules`. Its removal step sets every
   `sys.modules` entry to `None`. Nothing else holds `__main__`'s module object, so it dies there,
   on both binaries (EXECUTED, `probe_when.out`: the weakref callback fires while `sys.modules`
   still has all 41 or 72 entries).
5. The dict survives, because the function still points at it. Two later steps could free it.
   The shutdown's collection (`_PyGC_CollectNoFail`) frees it on the plain binary. On the snapshot
   that collection skips the dict, because it is frozen. The wipe of surviving modules
   (`finalize_modules_clear_weaklist`) skips it too, because its module's weakref is already dead.
6. So the dict is never freed, the file object is never finalized, and its buffered bytes never
   reach the host. On the plain binary, an object in that dict is finalized during the shutdown's
   collection (`probe_when.out`: "a value in __main__ finalized: sys.modules 0, os wiped False");
   on the snapshot it is never finalized.

Each step has a probe that removes it (`probe.out`, against main's set):

| program on the snapshot | bytes kept | what it shows |
|---|---|---|
| open, write 100, `def g` (the gap) | 0 | the defect |
| the same without `def g` | 100 | no cycle: the module's death frees the dict by reference counting |
| `class C: pass` instead of `def g` | 100 | a class with no method makes no cycle |
| `h = lambda: 0` instead of `def g` | 0 | any function makes the cycle |
| the gap, plus `sys.kept = sys.modules['__main__']` | 100 | a module that survives is wiped, frozen or not |
| the gap, plus `gc.unfreeze()` at its end | 100 | the frozen generation is what hides the dict |
| the gap, in a fresh `__main__` made at run time | 100 | a namespace made after the freeze is collected |
| a `zipfile.ZipFile` left open, plus `def g` | archive unreadable (135 bytes) | it is every finalizer, not only a flush |

The plain binary keeps 100 bytes, and a readable archive, in every row. So does native CPython
3.15.0 for the gap's program (`native.out`).

**The script and `-m` loss is runpy's temporary module.** `run` runs a script with
`runpy.run_path(target, run_name="__main__")` and a module with
`runpy.run_module(target, run_name="__main__", alter_sys=True)`. Both run the code in a temporary
module (`runpy._TempModule`) that is removed when the call returns. The temporary module's dict
and its functions are then garbage, with the file in them. Native CPython loses the bytes the same
way when called like this: `runpy.run_path` keeps 0 bytes on the pinned host Python, with the
collector on or off, and `-X dev` reports the raw `FileIO` finalized while still open
(`native.out`). Native `python prog.py` and `python -m prog` keep 100. CPython's own entry points
run both in `__main__` itself (`Modules/main.c`, `pymain_run_python`: `pymain_run_file`, and
`runpy._run_module_as_main`), and `__main__` lives until finalization. A fresh `__main__` made at
run time and left to the interpreter's end keeps 100 too, natively and on both binaries
(`native.out`, `probe_in_main.out`). Why the collector's finalizers lose the bytes in one shape and
keep them in the other was not established (INFERRED: the order in which the file's three layers
are finalized; one native probe, a module dropped mid-run, reports the text layer first and still
keeps 0). This specification rests only on the measured fact: a namespace that is still `__main__`
when the interpreter finalizes keeps the bytes, which is what CPython's own entry points rely on.

| mode (through `wasi_python.run`, `probe_runner.out`) | plain | snapshot |
|---|---|---|
| `-c` | 100 | 0 |
| stdin | 100 | 0 |
| a script, `/prog.py` | 0 | 0 |
| a directory, `/app` holding `__main__.py` (`probe_dir.out`) | 0 | 0 |
| `-m prog` (a read-only grant on the import path) | 0 | 0 |

Where it happens, in one line each:
- the freeze: `recipes/reactor_main.c`, `wizer_initialize`,
  `run_private("import gc\ngc.collect()\ngc.freeze()\n")`;
- the namespace: `recipes/reactor_bootstrap.py`, `run`, `main = sys.modules["__main__"]` and the
  `exec(..., main.__dict__)` of the `-c` and stdin branches;
- the temporary modules: the same function's `runpy.run_module(...)` and `runpy.run_path(...)`
  (a file, a directory or a zip);
- the finalization: `recipes/reactor_main.c`, `run`, `Py_FinalizeEx()`.

## The options, measured (EXECUTED)

Every number is fuel (wasm instructions) from the judge's driver, against main's set
`s-c50ca51fae5eb55b-c9dcb5b8`, one run each; the driver seeds entropy and steps the clock, so a
row repeats. "Bare" is `-c pass`; "the gap" is check (h)'s program. Each fix is simulated by
code appended to, or wrapped around, the program, so it runs inside `_reactor.run` before
`Py_FinalizeEx`, as the real change would.

| option | bare, snapshot | the gap, snapshot (bytes) | after `import pandas`, snapshot | bare, plain | check (b): plain ÷ snapshot |
|---|---|---|---|---|---|
| today | 15,631,800 | 16,185,307 (0) | 4,600,110,254 | 167,476,282 | 10.71 |
| 1. `gc.unfreeze()` before finalizing, as a session's close does | 43,851,798 (+28.2 M, ×2.81) | 44,409,524 (100) | 4,644,580,241 (+44.5 M) | 167,989,079 (+0.5 M) | **3.82: fails 8** |
| 2. flush every live file object at the end (a walk of `gc.get_objects()`) | 17,518,685 (+1.9 M) | 18,230,216 (100) | 5,072,276,241 (+472 M) | 444,220,984 (+276.7 M) | 25.4 |
| 3. Python's shutdown under its own budget, as spec 055's close | as option 1 | as option 1 | as option 1 | as option 1 | as option 1 |
| 4. a fresh, unfrozen `__main__` per program | +10,904 | +62,918 (100) | +1,288,886 | +29,676 | 10.71 |

Sources: `probe.out` (options 1 and 2). Option 4's row is the pre-build review's like-for-like
measurement (`cases5.out`: today's `run` against a prototype of Decisions 1 to 3, both exec'd
into `_reactor` and called through the same `-c` wrapper, so the wrapper's compile is the same on
both sides). The same pair gives a script `pass` −117,389 (snapshot) and −1,035,053 (plain), and
`-m` −8,386 and −73,283: those rows fall, because runpy's temporary module is gone. The plain
binary's `import pandas` row rises +17,327 and its gap row falls −20,085. This draft's own first
figure, about +0.53 M (`probe_fresh_cost.out`), was an upper bound: most of it was the compile of
the wrapper's extra lines, which the precompiled bootstrap never pays (one extra line that only
makes a module cost +196 K, the review's `cases1.out`).

What each covers, and what it restates:

1. **Unfreeze before finalizing.** It gives the snapshot CPython's teardown exactly, so it keeps
   every row above, and also the residual case below. But it costs 28.2 M on every snapshot
   call, most of it the shutdown's collections now walking and freeing the bootstrap's heap. A
   bare call becomes 2.8 times dearer, and the snapshot's start only 3.8 times cheaper than the
   plain start. **It restates spec 069's check (b)**, whose factor of 8 it fails, and it undoes
   the reason 069's Decision 4 kept the freeze. It does not fix a script or `-m`, which lose
   their bytes on the plain binary too.
2. **Flush every live file.** It does more than CPython does in one way and less in another. It
   flushes but does not finalize, so a `ZipFile` left open still has no central directory
   (`probe.out`: "zip BAD" after the walk). Its walk costs 276.7 M on the plain binary, whose heap
   is all young, and 472 M on the snapshot after `import pandas`, as spec 055 found (P11). It
   restates nothing in (b), only because the plain start grows more than the snapshot's. Spec 055
   rejected it for the same reasons.
3. **Python's shutdown under a budget, as 055 does.** `run` already runs Python's shutdown: its
   C entry calls `Py_FinalizeEx()` inside the call's own fuel and deadline
   (`recipes/reactor_main.c`, `run`). What a session's close adds is the unfreeze and a separate
   budget around it. So its fuel is option 1's, it restates (b) the same way, and it adds a limit
   to `run`'s public API (a `shutdown` budget), which spec 049 would have to allow. It buys
   nothing option 1 does not.
4. **A fresh `__main__` per program.** The namespace is made at run time, after the freeze, so the
   collector tracks it as it tracks the plain binary's. It keeps every row of the cause's table,
   on both binaries, for about eleven thousand instructions on a bare snapshot run. It **does not
   restate (b)**: the factor stays at 10.7. Run a script and `-m` in that same `__main__`, as
   CPython's own entry points do, and they keep their bytes too (`probe_in_main.out`: 100 on
   both binaries), for fewer instructions than today.

**The residual, which option 4 leaves.** A program can hang its own objects on the frozen heap
itself. Then the frozen heap reaches them, and on the snapshot they are never finalized. Two
measured shapes (EXECUTED):
- **A pre-imported class patched from `__main__`.** `json.JSONEncoder.default = default`, with
  `default` defined in the program, a common idiom: the frozen class now reaches the program's
  function, its `__globals__`, and the open file. The bytes are lost on the snapshot with a fresh
  `__main__`, and kept on the plain binary and with option 1 (`probe_patch.out`).
- **An open file stored as an attribute of a pre-imported module.** `import json;
  json.log = open(...)`. Of the 70 modules in a snapshot program's `sys.modules` at its start, 15
  lose the bytes this way (their module objects die at removal, like `__main__`'s, and their dicts
  are frozen cycles): `_colorize _reactor _zip_directory ast collections csv dataclasses encodings
  io json os.path posixpath re reprlib site`. The plain binary keeps all 70 (`probe_modules.out`).
  Keeping those modules alive to the wipe closes this shape (+2.8 M, simulated) but not the
  patched class (`probe_keep.out`, `probe_patch.out`), so it is not taken.

Only option 1 closes the residual, at 28.2 M per call. That trade (the snapshot's cheap start
against a corner the program builds itself) touches the owner's decision 34 and the reason the
freeze was kept, so it is the owner's. It is question 103; this specification does not wait on it
(Decision 6).

## Decisions

1. **Option 4: every program gets a fresh `__main__`, made at run time.**
   - `_reactor` captures the names of the interpreter's own `__main__` once, when it is imported
     (before any program, and before the snapshot's freeze): `__name__`, `__doc__`,
     `__package__`, `__loader__`, `__spec__` and `__builtins__`, as CPython's `add_main_module`
     and the module type make them.
   - `run`, after `_refresh` and before it dispatches on the mode, makes a new module named
     `__main__`, gives its dict those names, and puts it in `sys.modules["__main__"]`. Every mode
     then runs in it.
   - It is made in `run`'s own frame, before the program's `exec`, so a program's stack is as deep
     as today (spec 054's check pins `traceback.extract_stack()` at 2 frames, and 4 under the
     import path's prelude). The builder may make it inside `run`'s `try`, so a `MemoryError`
     there is reported as any other (the review's note).
   - **Both binaries.** The plain binary's `__main__` is not frozen, but one code path is simpler
     to state and to check, and a fresh module costs it about 30 thousand instructions (the
     review's `cases5.out`).
   - **The prelude.** Under an import path, the runner's prelude (`_import_prelude`) is a `-c`
     program that calls `_reactor.run` again. The outer call makes a fresh `__main__`, the prelude
     binds no name in it, and the inner call makes another for the caller's program. The names
     come from the capture, not from the current `__main__`, so nesting cannot leak names.
   - *Why:* it is the only measured option that keeps the gap's bytes without restating (b), and
     it gives the snapshot the plain binary's teardown for everything a program keeps in
     `__main__`. The old, frozen `__main__` is dropped from `sys.modules`; nothing else holds it, so
     reference counting frees it.

2. **A script runs in `__main__` itself, with native CPython's globals** (the review's F1).
   - **A file** (`pkgutil.get_importer(target)` is `None`, runpy's own test): `code =
     runpy._get_code_from_file(target, "__main__")`, which reads a `.pyc` or compiles source as
     `run_path` does. Then `run` does what CPython's `_PyRun_SimpleFile` does for a script
     (`Python/pythonrun.c`): it sets `__file__` to the target, sets `__loader__` to
     `importlib.machinery.SourceFileLoader("__main__", target)`, or `SourcelessFileLoader` when
     the target ends in `.pyc` (`set_main_loader`; CPython's `maybe_pyc_file` also takes a
     `.pyc` by its magic number under another name, which `run` does not, a corner recorded
     here), runs `exec(code, main.__dict__)`, and removes `__file__` again in a `finally`, as
     CPython does on every path. `__package__` and `__spec__` stay the fresh `__main__`'s `None`.
   - **A directory or a zip:** `sys.path.insert(0, target)`, then
     `runpy._run_module_as_main("__main__", alter_argv=False)`. This is CPython's own path for
     such a target (`Modules/main.c`: `pymain_sys_path_add_path0`, then
     `pymain_run_module(L"__main__", 0)`).
   - **The globals, now native's** (`native_atexit.out`, and the review's `native.out`):

     | mode | `__file__` during the run | `__package__` | `__spec__` | `__loader__` | `__file__` in an `atexit` handler |
     |---|---|---|---|---|---|
     | a file | the target | `None` (today `''`) | `None` | `SourceFileLoader` (today `None`) | absent (today the handler sees an empty module) |
     | a `.pyc` file | the target | `None` | `None` | `SourcelessFileLoader` | absent |
     | a directory or zip | its `__main__.py` | `''` | named `__main__` | `SourceFileLoader` | its `__main__.py` |
     | `-m` | the module's file | its parent, `''` at top level | the module's | its loader | the module's file |

     In every mode `__builtins__` becomes the builtins module, as in `-c` and as native CPython
     gives `__main__`, where today `exec` into a temporary module inserts the builtins' dict.
   - **Three changes a user can see, all toward native** (the review's F3, EXECUTED there,
     `cases3.out`), each held by a check row (check C and check E, Decision 7):
     - an `atexit` handler in a script, a directory or `-m` finds the program's `__main__`: its
       classes and functions (so pickling a `__main__` class there works), and `__file__` for a
       directory or `-m`. Today it finds the restored, empty `__main__`, and pickling raises
       `AttributeError`;
     - a directory or zip without `__main__.py` prints CPython's line,
       `/usr/local/bin/python.wasm: can't find '__main__' module in '/empty'`, and returns 1.
       Today it prints an `ImportError` traceback (exit 1);
     - `-m`'s change is Decision 3's.
   - The "can't open file" message is unchanged: the `OSError` still rises from runpy's frame
     (`_get_code_from_file`), which `_only_runpy` checks. A script's traceback is unchanged byte
     for byte (the review's `cases3.out`): `_report` strips runpy's frames, and a file script now
     has none above its own.
   - *Why native, not runpy's values:* the spec's promise is "as CPython's own entry points";
     nothing in `tests/` pins `''` or a `None` loader (the review's grep); and the change costs
     two assignments. Check C pins native's values, so a later drift is caught.
   - *Why runpy's private helpers:* the pinned stdlib zip carries a fixed `runpy`, and CPython's
     own `-m` calls `runpy._run_module_as_main`, so these helpers are what the interpreter itself
     relies on. Check C pins the globals, so a CPython upgrade that changes them is caught.

3. **`-m` runs as CPython's own `-m` does: `runpy._run_module_as_main(target)`.**
   - It runs the module in `__main__`'s dict and sets `sys.argv[0]` to the module's file, as
     `run_module(..., alter_sys=True)` did during the call (spec 054's check:
     `['/code/pkg/__main__.py', 'x', 'y']`).
   - Its globals are today's (`__spec__` the module's spec, `__loader__` its loader, `__file__` its
     origin), except `__builtins__`, as for a script; they match native's (`native_atexit.out`).
   - **Its traceback shows CPython's frames** (the review's F3). `_report` strips runpy's frames
     only for a script, so an `-m` traceback shows them, as native does. Today it shows
     `run_module`, `_run_module_code` and `_run_code`; after, `_run_module_as_main` and
     `_run_code`, both `"<frozen runpy>"`, byte for byte native's (the review's `cases3.out`,
     `native.out`). Check E holds the frame names.
   - A module that cannot be found now ends as native's does: `_run_module_as_main` calls
     `sys.exit(f"{sys.executable}: No module named prog")` (READ, `Lib/runpy.py`), and the guest's
     `sys.executable` is `/usr/local/bin/python.wasm` (`probe_runner.out`), so `run` prints that
     line and returns 1 (`_exit_code`). Today it prints an `ImportError` traceback. No check pins
     today's form (`grep` of `tests/`); check E pins the new line (the review's `cases3.out` saw
     it from the prototype).

4. **The freeze stays, and check (b) is not restated.** `wizer.initialize` keeps
   `gc.collect(); gc.freeze()`, and `START_FACTOR` stays 8. The builder records (b)'s factor on the
   built set; it must be at least 10 (today 10.71, and 10.71 with option 4's like-for-like cost:
   (167,476,282 + 29,676) ÷ (15,631,800 + 10,904)).

5. **Sessions are unchanged.** A session's turns run in the `__main__` they find, and its close
   keeps 055's `gc.unfreeze()` before `Py_FinalizeEx`, which also covers the residual. A fresh
   `__main__` for sessions would not let the close drop the unfreeze, because of the residual, so
   it is not in scope.

6. **The residual is checked, documented and asked, not fixed here.**
   - Check D holds the patched-class shape on both binaries. `[plain]` passes. `[snapshot]` fails,
     and a gap entry allows exactly that failure, naming question 103 as its closer (Decision 7).
   - The README's snapshot facts gain one: an object a program hangs on a module or class the
     snapshot pre-imported may never be finalized, so close files with `with` (the review's
     note: "may", since most such hooks are measured fine, `cases2.out`).
   - Question 103 asks the owner whether to pay option 1's 28.2 M per snapshot call to close it.
     The agent's recommendation is no. If the owner says yes, a later specification adds the
     unfreeze to `run`, restates (b), and removes the gap.

7. **The judge changes, named.** All in `tests/checks/test_v1_4_embedding.py` (v1.4) and
   `tests/known_gaps.toml`:
   - **(h), edited:** `test_run_keeps_an_unclosed_files_bytes`'s docstring loses "a known gap until
     spec 073" and says the program runs in a fresh `__main__` (Decision 1). Its body is unchanged.
   - **The gap entry for (h)`[snapshot]` is removed**, with its comment block.
   - **A, new: `test_run_keeps_unclosed_files_in_every_mode`** (`@BINARY`, through
     `wasi_python.run`, recording no fuel, since `run` answers entropy and clocks from the host).
     Five modes: `-c`; stdin (`argv=[]`, the program as `stdin`); a script (`/prog.py` in the
     call's root); a directory (`/app`, holding the program as `__main__.py`); `-m prog` (a
     read-only grant at `/code` on `import_path`, as spec 054's check makes one). Two programs
     in each: the gap's (`UNCLOSED`, writing `/out.txt`), and a `zipfile.ZipFile("/out.zip", "w")`
     left open after `writestr("a.txt", "x" * 100)`, beside a `def`. A finding is
     `"<mode>: a file left open kept <n> of 100 bytes"` or `"<mode>: a zip
     left open is unreadable"`, reported through `scan.report(findings, "unclosed file")`. Today it
     fails with 3 findings on the plain binary (the file, in a script, a directory and `-m`) and 7
     on the snapshot (both programs in `-c` and stdin; the file in the other three); a zip left
     open in a script, a directory or `-m` happens to stay readable on both
     (`probe_check_a.out`). After the build, none.
   - **C, new: `test_every_program_runs_in_an_unfrozen_main`** (`@BINARY`, through
     `wasi_python.run`, no fuel). In each of A's five modes the program prints: whether its
     globals are in a collector generation (`any(o is globals() for o in gc.get_objects())`;
     `gc.get_objects()` never lists the frozen generation, `_PyGC_GetObjects`); whether they are
     `sys.modules["__main__"].__dict__`; their dunder names; and `__name__`, `__file__`,
     `__package__`, `__spec__`'s name, `__loader__`'s type name and `__builtins__`' type name. It
     also registers an `atexit` handler that prints whether `sys.modules["__main__"]` holds the
     program's class `C`, whether pickling `C()` round-trips, and its `__file__` (or none). It
     asserts `True`, `True`, today's names, and native's values (Decision 2's table; `-c` and
     stdin as `test_main_starts_as_native`'s six names, with `__loader__` a `type` and
     `__builtins__` a `module`); in the handler, `C` present and the pickle round-trips in every
     mode, with `__file__` absent for `-c`, stdin and a file, and kept for a directory and `-m`.
     Today it fails on the snapshot's `-c` and stdin (frozen), on both binaries' script
     (`__package__` `''`, `__loader__` `None`), and on both binaries' script, directory and `-m`
     (`__builtins__` a `dict`; the handler finds no `C`).
   - **D, new: `test_run_keeps_a_file_a_patched_stdlib_class_reaches`** (`@BINARY`, through the
     `guest` fixture, recording fuel). The program: `import json`, open `/out.txt`, write 100
     bytes, define `default(self, o)`, set `json.JSONEncoder.default = default`. It asserts 100
     bytes, and reports a shortfall as `"<binary>: a file reached from a patched stdlib class kept
     <n> of 100 bytes"` through `scan.report(findings, "frozen heap")`. `[plain]` passes today and
     after. `[snapshot]` fails today and after with `frozen heap: 1 finding(s), digest
     049b78ef7b5a: snapshot: a file reached from a patched stdlib class kept 0 of 100 bytes`
     (computed with `scan.report`).
   - **E, new: `test_module_and_directory_errors_read_as_native`** (`@BINARY`, through
     `wasi_python.run`, no fuel; the review's F3). Three rows: `-m nope` (no such module) prints
     exactly `/usr/local/bin/python.wasm: No module named nope` and a newline on stderr and
     returns 1; a directory `/empty` without `__main__.py` prints exactly
     `/usr/local/bin/python.wasm: can't find '__main__' module in '/empty'` and a newline and
     returns 1; `-m boom`, a module whose function divides by zero, returns 1 and its traceback's
     frames are named, in order, `_run_module_as_main`, `_run_code`, `<module>` and `f`, the first
     two in `"<frozen runpy>"`. It pins names and order, not runpy's line numbers, so a patch
     release of CPython does not fail it. Today every row fails on both binaries.
   - **The gap entry for D`[snapshot]`, new:**
     ```toml
     [[gap]]
     check = "tests/checks/test_v1_4_embedding.py::test_run_keeps_a_file_a_patched_stdlib_class_reaches[snapshot]"
     match = "1 finding(s), digest 049b78ef7b5a"
     reason = "on the snapshot, an object a program hangs on a pre-imported module or class is reached from the frozen heap and never finalized, so a file it reaches loses its buffered bytes (spec 073, Decision 6; question 103)"
     closes_with = "context/questions-for-the-owner.md"
     ```
   - No golden output or harness constant changes, and no upstream allowance change is expected
     (Decision 10 says what the builder does if an upstream outcome moves). `START_FACTOR` stays
     8.

8. **The fuel moves, and how the lane accepts it.** Every check that runs a program on either
   binary pays the fresh `__main__`: about +11 K on a bare snapshot run and +30 K on a bare plain
   one, up to +1.3 M after `import pandas` on the snapshot (the review's `cases5.out`). Script and
   `-m` rows fall, by up to −1.0 M (a plain script), since runpy's temporary module is gone. So
   many rows move past the tolerance of one part in ten thousand, in both directions. The builder lists the rows that moved, their largest
   rise in instructions and in percent, and the bare row's rise, in the Landing notes. The lane
   accepts with `--accept-judge` (Decision 7's changes) and `--accept-growth` naming the fresh
   `__main__`.

9. **Why not a smaller change to the gap alone.** Unfreezing only `__main__`'s dict is not
   possible: `gc.unfreeze()` moves the whole permanent generation. Clearing `__main__`'s dict at
   the end of `_reactor.run` would run before `atexit` handlers, which may use it, and it is not
   what CPython does. Keeping `__main__` alive to the wipe (the "main-kept-alive" row) wipes it
   in reverse import order, after modules it may use (`os` was imported after `__main__`), where
   CPython frees it first.

10. **How it meets the specifications in flight.**
    - **083** (the judge's driver answers file times and inode numbers; confirmed for build, and
      it builds after 065 lands): both add checks to `tests/checks/test_v1_4_embedding.py`, at
      different places, and both edit `tests/known_gaps.toml` (083 narrows 065's stepped-clock
      gap; 073 removes (h)'s and adds D's), so they meet in two files, each merge textual. The
      order in flight is 081, then 065, then 083. Both restate fuel; whichever lands second takes main's progress files
      and accepts again, as AGENTS.md rule 6a says. Check D and (h) write a file through the
      driver, so their fuel depends on the file's time and inode number until 083 lands (083
      measured that spread at 102 instructions at most, within every row's tolerance); after 083,
      it is fixed.
    - **081** (guest fuel independent of the checkout path; its guard refuses a measured run whose
      inputs name a host path): check D and (h) pass guest paths only (`/out.txt`), and A and C
      record no fuel. No textual overlap: 081 edits `tests/harness/guest.py`,
      `tests/checks/conftest.py` and the lxml check.
    - **The upstream suites are consumers** (the review's F5). numpy's and pandas' suites run
      the judge's `drive.py` as a script (`tests/harness/upstream.py`, `guest_argv`), and spec
      065's CPython groups run `regrtest_drive.py` as a script too. So every upstream group moves
      from runpy's temporary module to `__main__`, with native's script globals. During the run
      what they see differs only in `__builtins__`, `__package__` and `__loader__`: today's
      temporary module is also `sys.modules["__main__"]` and carries the same `__file__`, which
      their `M` lines read. So no outcome is expected to move (INFERRED). **If any upstream
      outcome moves**, the builder stops, names the group, the test and the cause, and treats it
      as a further judge change, reviewed as a delta before the build is called built; nothing in
      `tests/upstream/*.toml` or `tests/upstream/expected/` is edited to absorb it (AGENTS.md
      rule 4). If 065 lands first, its groups run in 073's full judge like the others.
    - **069**'s check (b) is not restated (Decision 4).
    - **Build-class order.** At most three build-class specifications are built at once (§5.7);
      this one edits only `recipes/reactor_bootstrap.py`, so a rebase meets another recipe change
      only there.

## Intent

A program that leaves a file open keeps its bytes, through `run`, on both binaries and in every
mode, as native CPython keeps them. The snapshot keeps its cheap start: the freeze stays, and
check (b) holds unchanged. The one corner left (an object a program hangs on the frozen heap) is
checked, documented and put to the owner.

## Design

- `recipes/reactor_bootstrap.py`:
  - at import: `_MAIN_NAMES = dict(sys.modules["__main__"].__dict__)`, with a comment citing this
    specification and `add_main_module`;
  - `_fresh_main()`: `main = type(sys)("__main__")`, `main.__dict__.update(_MAIN_NAMES)`,
    `sys.modules["__main__"] = main`, return `main`; a comment says why (the frozen heap, the
    cause above, Decision 1);
  - `run`: `main = _fresh_main()` replaces `main = sys.modules["__main__"]`; the `-m` branch calls
    `runpy._run_module_as_main(target)` after `sys.argv = [target, *rest]`; the script branch
    tests `pkgutil.get_importer(target)` and takes Decision 2's two paths (for a file: the code
    from `runpy._get_code_from_file`, `__file__` and the loader set, `exec`, and `__file__`
    removed in a `finally`). The module docstring
    gains one sentence on the fresh `__main__`.
- `tests/checks/test_v1_4_embedding.py`: (h)'s docstring; checks A, C, D and E (Decision 7),
  beside (h).
- `tests/known_gaps.toml`: (h)'s entry and its comment removed; D's entry added with a comment
  naming this specification and question 103.
- `README.md`, the snapshot's facts after "`run` treats its arguments as CPython's command line
  does": every program runs in a fresh `__main__`, and a script and `-m` run in it as CPython's
  own entry points run them; a fourth snapshot fact, the residual and its advice ("close files
  with `with`").
- `CHANGELOG.md`, 0.1.0a7: one **Fixed** bullet (the snapshot's unclosed files, and a script's
  and `-m`'s on both binaries) and one **Changed** bullet naming what moves toward native: a
  script's `__package__` and `__loader__`, `__builtins__` a module, an `atexit` handler that
  finds the program's `__main__`, `-m`'s not-found line and traceback frames, and a directory's
  "can't find '__main__' module" line;
  and spec 069's bullet loses "Known and unchanged: `run` on the snapshot loses …".
- `context/roadmap.md`: 073's paragraph says drafted, then built, then landed, as it goes.
- Specs 003 (its `run` paragraph) and 069 (Decision 4): one dated amendment line each, written in
  with this revision (the review's F6). Spec 055's addendum is a research memo, which is never
  edited after the fact (`context/README.md`), so it gets no line; this specification cites it.

## Scope

In: `_reactor.run`'s namespace and its script and `-m` paths; the judge changes of Decision 7;
the README, CHANGELOG and roadmap lines.

Out:
- the freeze itself, and check (b)'s factor (Decision 4);
- the residual's fix (Decision 6; question 103);
- sessions (Decision 5);
- `_report`'s handling of tracebacks, which is unchanged;
- a file held only in a reference cycle that the program drops while it runs, which CPython also
  may not flush (`native.out`; the README already says so for sessions);
- anything in `src/`, `scripts/` or the workflow.

## Acceptance criteria

Each check is seen failing first, before the code it guards, on main's set
`build/sets/s-c50ca51fae5eb55b-c9dcb5b8`, and against each stand-in named. Stand-ins are built
in the worktree from the branch's recipe with one change each, run, and dropped; their output goes
to `build/073/*.log`.

1. **The checks fail first, as Decision 7 says.** On main's set: A fails with 3 findings on the
   plain binary (digest `e6d5609d06d8`) and 7 on the snapshot (digest `98d69ac9128b`;
   `probe_check_a.out` ran its logic); C fails on the snapshot's `-c` and stdin and on both
   binaries' script, directory and `-m`; E fails on all three rows on both binaries; D`[plain]` passes and D`[snapshot]` fails with digest
   `049b78ef7b5a`; (h)`[snapshot]` fails with digest `7da6e52329c1`.
2. **After the build, the gap closes.** (h)`[snapshot]` passes, its gap entry is gone, and the
   scoreboard shows one gap fewer from it. A, C and E pass on both binaries. D`[plain]` passes;
   D`[snapshot]` fails with exactly its gap entry's digest.
3. **What must not move.** `test_main_starts_as_native` (both binaries; it pins the six names
   only, and check C pins their values, the review's F2) and
   `test_the_import_path_reaches_every_mode` (both binaries; its stack depths 2 and 4, its `-m`
   argv, its script's exit code 3) pass unchanged. Check (b) passes with `START_FACTOR` 8, and its
   factor on the built set is at least 10; the Landing notes record both counts.
4. **The fresh `__main__`'s cost, counted.** The snapshot's `-c pass` fuel on the built set
   against main's accepted row for check (b): the rise is at most 0.1 M instructions (measured
   like for like at +10,904; an eager import of `runpy`, about 20 M, would fail it). The Landing
   notes give the number and the command.
5. **Stand-ins.** Each fails what it names:
   - **S1**, the fresh `__main__` made but `-c` and stdin still `exec` in the old one: A (the
     snapshot's `-c` and stdin rows), C and (h)`[snapshot]` fail.
   - **S2**, the script branch left on `runpy.run_path`: A's and C's script and directory rows
     fail, and E's directory row.
   - **S3**, the `-m` branch left on `runpy.run_module`: A's and C's `-m` rows fail, and E's two
     `-m` rows.
   - **S4**, the fresh `__main__` a bare `type(sys)("__main__")`, without the captured names: C's
     `-c` and stdin rows fail (`__builtins__` a `dict`, `__loader__` `None`). It does not fail
     `test_main_starts_as_native`, whose six names the module type and `exec` still give (the
     review's F2, `cases4.out`).
   - **S5**, the file-script branch giving runpy's `__package__` `''` and `__loader__` `None`:
     C's script row fails.
   - **S7**, the file-script branch without the `finally` that removes `__file__`: C's script
     row fails in its `atexit` part.
   - **S6**, `gc.unfreeze()` added before `Py_FinalizeEx` in `run` (option 1): D`[snapshot]` passes,
     which the judge reports as a failure ("passes, but tests/known_gaps.toml still lists it"),
     and check (b) fails at about 3.8. This is the evidence that option 1's numbers hold on a real
     build.
6. **The README and CHANGELOG lines** of the Design; `tests/public_api.txt` unchanged
   (`tests/harness/api.py` finds no change).
7. **The judge, in the worktree, without `--accept`,** against the built set: the fast tier
   while building, then the full judge with `-n 3` (the machine is shared) before "built": 0
   fail, no pass lost, one gap fewer ((h)) and one more (D); every growth is the fresh
   `__main__`'s or the script and `-m` change's, listed as Decision 8 says; the judge change named
   (`tests/checks/test_v1_4_embedding.py`, `tests/known_gaps.toml`); `ruff check` and
   `ruff format --check` green.
8. **The lane** rebuilds the set from the pins in the main tree, compares it with the builder's
   on the same base, judges serially and accepts, as §5.7 says for a build-class change.

## The measurement (EXECUTED)

Evidence: `../research/2026-10-19-run-and-the-frozen-main/`. Against
`build/sets/s-c50ca51fae5eb55b-c9dcb5b8` in the main tree (main's set at `08de0c8`), read only;
macOS arm64, wasmtime-py 49.0.0, the worktree's own `uv` environment. Each script names its
command in its docstring.

- `probe.py` → `probe.out`: the cause's rows and the options' costs (the tables above).
- `probe_when.py` → `probe_when.out`: when `__main__`'s module dies and when a value in it is
  finalized, per binary.
- `probe_modes.py` → `probe_modes.out`, and `probe_runner.py` → `probe_runner.out`: the gap's
  program in each mode, through the driver and through `wasi_python.run`.
- `probe_in_main.py` → `probe_in_main.out`: a script and `-m` run in a fresh `__main__` keep 100
  on both binaries.
- `probe_fresh_cost.py` → `probe_fresh_cost.out`: the fresh `__main__`'s own cost: +533,134
  (bare, snapshot), +577,332 (the gap, snapshot), +540,848 (bare, plain), against a control
  running the same wrapper.
- `probe_globals.py` → `probe_globals.out`: each mode's namespace today (check C's expected
  values).
- `probe_check_a.py` → `probe_check_a.out`: check A's logic on main's set, with its findings.
- `probe_dir.py` → `probe_dir.out`: a directory target today (its bytes and its namespace).
- `native_atexit.sh` → `native_atexit.out` (added for the revision): native CPython 3.15.0's
  `__main__` globals for a script, a `.pyc`, a directory and `-m`, during the run and in an
  `atexit` handler (Decision 2's table).
- `probe_modules.py` → `probe_modules.out`: the residual's module shape, 15 of 70 modules.
- `probe_patch.py` → `probe_patch.out`: the residual's patched-class shape, and that only
  option 1 closes it.
- `probe_keep.py` → `probe_keep.out`: keeping the snapshot's modules alive closes the module shape
  for +2.8 M, but not the patched class.
- `native.sh` → `native.out`: native CPython 3.15.0 (the build's pinned host Python,
  `build/tools/python` in the main tree) on each mode and on files whose last references are
  garbage.

## Landing notes

Not built. The builder fills this in: the commits; the checks seen failing first and each
stand-in's failure; the rebuilt set's hashes; check (b)'s two counts and factor; the bare row's
rise (criterion 4); the rows that moved, up and down (Decision 8); the user-visible changes of
Decisions 2 and 3 as check C and E saw them (the `atexit` handler, `-m`'s not-found line and
traceback frames, the directory's "can't find '__main__' module" line, a script's `__package__`
and `__loader__`); any upstream outcome that moved (Decision 10); the fast tier and the full
judge's last lines; and the lines for the lane (`--accept-judge`, `--accept-growth`).

## Disposition of the pre-build review

The review: `../reviews/073-run-keeps-an-unclosed-files-bytes-spec-2026-10-19.md` (verdict "ready once F1 to F4 are written in";
written in the lane's scratchpad, to be copied by the lane).

1. **F1 (Medium) — fixed: native's script globals.** Decision 2 now gives a file script
   `__package__` `None` and a `SourceFileLoader` (`SourcelessFileLoader` for a `.pyc`), and
   removes `__file__` after the run, as `_PyRun_SimpleFile` does; check C pins native's values
   and S5 is runpy's values; S7 is new. No measured reason was found to keep runpy's: a native
   probe added for the revision (`native_atexit.out`) confirms the values, including that an
   `atexit` handler sees no `__file__` after a native script.
2. **F2 (Low-Medium) — fixed.** S4 names check C's `-c` and stdin rows; criterion 3 says
   `test_main_starts_as_native` pins names only and C pins their values.
3. **F3 (Low-Medium) — fixed.** Decision 2 names the `atexit` change and the "can't find
   '__main__' module" line; Decision 3 names the `-m` traceback frames; check C gains its
   `atexit` part and new check E holds the three error-path rows; the CHANGELOG's **Changed**
   bullet and the Landing notes list them. "Tracebacks are unchanged" now says a script's.
4. **F4 (Low) — fixed.** Option 4's row is the review's like-for-like measurement (+10,904
   snapshot, +29,676 plain on `-c pass`; script and `-m` rows fall, by up to −1,035,053);
   Decision 1's and option 4's prose, Decision 4's factor (10.71), Decision 8's band and
   criterion 4's bound (0.1 M) follow; the first figure is kept as the upper bound it was, with
   why. Question 103's "about 0.5 M" and the roadmap's become "about 11 thousand".
5. **F5 (Low) — fixed.** Decision 10 names the upstream suites as consumers and says the
   builder stops and treats a moved outcome as a further judge change, reviewed as a delta;
   Decision 7 says "no upstream allowance change is expected".
6. **F6 (Low) — fixed.** Dated amendment lines in spec 003's `run` paragraph and spec 069's
   Decision 4. Not in spec 055's addendum, a research memo, which is not edited after the fact.
7. **F7 (Low) — fixed.** D's gap reason ends "(spec 073, Decision 6; question 103)".
8. **F8 (Low) — fixed.** Decision 10: 083 confirmed, building after 065, and meeting 073 in
   `tests/known_gaps.toml` as well as the check file, both merges textual; the order 081, 065,
   083.

The review's notes, taken: the README says "may never be finalized"; the builder may make the
fresh `__main__` inside `run`'s `try`. Its note on a relative script target (native makes
`__file__` absolute) and the script's directory not on `sys.path` are older than this
specification and stay out of scope.
