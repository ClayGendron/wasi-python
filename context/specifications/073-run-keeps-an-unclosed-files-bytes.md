# 073 — `run` keeps an unclosed file's buffered bytes

- **Status:** **landed 2026-10-20 in wave 02** (039, 041, 073, 093) on main `b0c7a74`: accepted on `2bb98c8`, history line 83, 630/701 pass, 0 fail; the integration review `../reviews/wave-02-integration-2026-10-20.md` ("lands as merged at 170b4e2", every changed row attributed); the dry run 39363060501 dispatched on the acceptance as main moved (see "Landed in wave 02" below). Before: **built 2026-10-19** on `spec/073-run-keeps-unclosed-files-bytes`; **rebuilt the same day against its build review** (B1 fixed, B2 to B4 written in; the review, `../reviews/073-run-keeps-an-unclosed-files-bytes-build-2026-10-19.md`, written in the lane's scratchpad, "lands once B1 is fixed and rebuilt"), rebased onto main `a6dfc17` (the Landing notes): the full judge has 0 fail and no lost pass; its growth is this specification's, listed for the lane; a delta look at the B1 hunk follows. Before that: **drafted 2026-10-19** on `spec/073-run-keeps-unclosed-files-bytes` from main `08de0c8` (`ede53a7`); **revised 2026-10-19 against its pre-build review** (`../reviews/073-run-keeps-an-unclosed-files-bytes-spec-2026-10-19.md`, written in the lane's scratchpad with its probes, to be copied by the lane; verdict "ready once F1 to F4 are written in"; F1 to F8 are written in, and "Disposition of the pre-build review" says where), rebased onto main `2968512`. **Amended 2026-10-19 (question 103 answered)**, rebased onto main `3561e55`: the owner chose "Yes, unfreeze before finalizing" (`../decisions.md`, "100 to 103 … answered"), so `run` on the snapshot also undoes the freeze before it finalizes, check D's gap is gone and check (b) is restated (the section "Amendment of 2026-10-19"); the same reviewer confirms the amendment. It is scheduled behind the packages (the owner, 2026-10-19): it builds when a build slot has no package ready. It changes the build recipe (`recipes/reactor_bootstrap.py`, compiled into both binaries at step 60), so it is reviewed once before it is built (constitution §5.6). It changes neither the guest's imports nor its exports. A different agent reviews the build.
- **Date:** 2026-10-19
- **Owner:** Clay Gendron
- **Kind:** **build-class** (§5.7): it changes `recipes/reactor_bootstrap.py` (the module `_reactor`: `run` gives every program a fresh `__main__`, and runs a script and `-m` in it) and `recipes/reactor_main.c` (`run` on the snapshot undoes the freeze before `Py_FinalizeEx`, through a reference `wizer.initialize` takes; Decision 4). It touches no `scripts/`, no `downloads/SHA256SUMS`, no patch, no pin and no workflow. It is also a judge change: four checks added and one docstring edited in `tests/checks/test_v1_4_embedding.py`; one gap entry removed in `tests/known_gaps.toml`; check (b)'s `START_FACTOR` restated from 8 to 3, with its docstring, in `tests/checks/test_v1_3_data_stack.py` (Decision 7). It changes `README.md` (the snapshot's facts) and `CHANGELOG.md` (0.1.0a7), and adds dated amendment lines to specs 003 and 069. It changes no public name, signature, field, default or option: **`tests/public_api.txt` does not change.** It changes nothing in `src/`. **The lane accepts it with `--accept-judge` and `--accept-growth`** (Decision 8).
- **Depends on:** 003 (the reactor and `_reactor.run`), 054 (the import path's prelude, which calls `_reactor.run` from a `-c` program), 055 (sessions, whose close already unfreezes, and whose reference to `gc.unfreeze` this shares; Decision 5), 069 (the snapshot pre-imports no package; its check (b), which this restates, and its gap (h), which this closes); all landed. The owner's answer to question 103 (`../decisions.md`). It meets 081, 083 and 065 in flight (Decision 10).
- **Research it stands on:** spec 055's addendum, section 8, P10b (`../research/2026-10-18-bounded-sessions.md`); spec 069's review, R1 and R2, and 069's Decision 4; and this specification's measurement (EXECUTED, `../research/2026-10-19-run-and-the-frozen-main/`, the section below). CPython 3.15.0's `Python/pylifecycle.c` (`finalize_modules`, `add_main_module`), `Python/gc.c` (`_PyGC_Freeze`, `_PyGC_GetObjects`), `Modules/main.c` (`pymain_run_python`) and `Lib/runpy.py`, from the pinned tarball in the main tree's `build/Python-3.15.0` (READ); and `Python/pythonrun.c` (`_PyRun_SimpleFile`, `set_main_loader`), read for the review's F1. The pre-build review's own probes (EXECUTED there, beside the review): `cases1.out` to `cases7.out` and `native.out`.

## The problem

A program opens a file, writes to it, and ends without closing it. Native CPython writes the bytes out when the interpreter finalizes, because the file object is freed and its finalizer flushes and closes it. `run` on the snapshot loses them when `__main__` also defines a function. The file ends up empty. The plain binary keeps them. This is the known gap `test_run_keeps_an_unclosed_files_bytes[snapshot]` (spec 069, check h).

This specification's measurement found a second loss beside it. A program run as a script (`run(["prog.py"])`) or as a module (`run(["-m", "prog"])`) loses the same bytes on **both** binaries, though native `python prog.py` and `python -m prog` keep them. Its cause is different, and its fix is in the same function, so this specification takes both.

## The cause (EXECUTED)

**On the snapshot, `__main__`'s namespace is in the frozen heap.**

1. The snapshot's initializer ends with `gc.collect(); gc.freeze()` (`recipes/reactor_main.c`, `wizer_initialize`). `gc.freeze()` moves every object the collector tracks into its permanent generation (`_PyGC_Freeze`). The collector never examines that generation again. `__main__`'s module object and its dict were made at start (`add_main_module`), so both are frozen.
2. A `-c` or stdin program runs in that dict: `exec(code, main.__dict__)` (`recipes/reactor_bootstrap.py`, `run`).
3. A function defined there points back at the dict (`g.__globals__`). The dict and the function now form a cycle, and the open file hangs from the dict.
4. At the end of `run`, `Py_FinalizeEx` reaches `finalize_modules`. Its removal step sets every `sys.modules` entry to `None`. Nothing else holds `__main__`'s module object, so it dies there, on both binaries (EXECUTED, `probe_when.out`: the weakref callback fires while `sys.modules` still has all 41 or 72 entries).
5. The dict survives, because the function still points at it. Two later steps could free it. The shutdown's collection (`_PyGC_CollectNoFail`) frees it on the plain binary. On the snapshot that collection skips the dict, because it is frozen. The wipe of surviving modules (`finalize_modules_clear_weaklist`) skips it too, because its module's weakref is already dead.
6. So the dict is never freed, the file object is never finalized, and its buffered bytes never reach the host. On the plain binary, an object in that dict is finalized during the shutdown's collection (`probe_when.out`: "a value in __main__ finalized: sys.modules 0, os wiped False"); on the snapshot it is never finalized.

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

The plain binary keeps 100 bytes, and a readable archive, in every row. So does native CPython 3.15.0 for the gap's program (`native.out`).

**The script and `-m` loss is runpy's temporary module.** `run` runs a script with `runpy.run_path(target, run_name="__main__")` and a module with `runpy.run_module(target, run_name="__main__", alter_sys=True)`. Both run the code in a temporary module (`runpy._TempModule`) that is removed when the call returns. The temporary module's dict and its functions are then garbage, with the file in them. Native CPython loses the bytes the same way when called like this: `runpy.run_path` keeps 0 bytes on the pinned host Python, with the collector on or off, and `-X dev` reports the raw `FileIO` finalized while still open (`native.out`). Native `python prog.py` and `python -m prog` keep 100. CPython's own entry points run both in `__main__` itself (`Modules/main.c`, `pymain_run_python`: `pymain_run_file`, and `runpy._run_module_as_main`), and `__main__` lives until finalization. A fresh `__main__` made at run time and left to the interpreter's end keeps 100 too, natively and on both binaries (`native.out`, `probe_in_main.out`). Why the collector's finalizers lose the bytes in one shape and keep them in the other was not established (INFERRED: the order in which the file's three layers are finalized; one native probe, a module dropped mid-run, reports the text layer first and still keeps 0). This specification rests only on the measured fact: a namespace that is still `__main__` when the interpreter finalizes keeps the bytes, which is what CPython's own entry points rely on.

| mode (through `wasi_python.run`, `probe_runner.out`) | plain | snapshot |
|---|---|---|
| `-c` | 100 | 0 |
| stdin | 100 | 0 |
| a script, `/prog.py` | 0 | 0 |
| a directory, `/app` holding `__main__.py` (`probe_dir.out`) | 0 | 0 |
| `-m prog` (a read-only grant on the import path) | 0 | 0 |

Where it happens, in one line each:
- the freeze: `recipes/reactor_main.c`, `wizer_initialize`, `run_private("import gc\ngc.collect()\ngc.freeze()\n")`;
- the namespace: `recipes/reactor_bootstrap.py`, `run`, `main = sys.modules["__main__"]` and the `exec(..., main.__dict__)` of the `-c` and stdin branches;
- the temporary modules: the same function's `runpy.run_module(...)` and `runpy.run_path(...)` (a file, a directory or a zip);
- the finalization: `recipes/reactor_main.c`, `run`, `Py_FinalizeEx()`.

## The options, measured (EXECUTED)

Every number is fuel (wasm instructions) from the judge's driver, against main's set `s-c50ca51fae5eb55b-c9dcb5b8`, one run each; the driver seeds entropy and steps the clock, so a row repeats. "Bare" is `-c pass`; "the gap" is check (h)'s program. Each fix is simulated by code appended to, or wrapped around, the program, so it runs inside `_reactor.run` before `Py_FinalizeEx`, as the real change would.

| option | bare, snapshot | the gap, snapshot (bytes) | after `import pandas`, snapshot | bare, plain | check (b): plain ÷ snapshot |
|---|---|---|---|---|---|
| today | 15,631,800 | 16,185,307 (0) | 4,600,110,254 | 167,476,282 | 10.71 |
| 1. `gc.unfreeze()` before finalizing, as a session's close does | 43,851,798 (+28.2 M, ×2.81) | 44,409,524 (100) | 4,644,580,241 (+44.5 M) | 167,989,079 (+0.5 M) | **3.82: fails 8** |
| 2. flush every live file object at the end (a walk of `gc.get_objects()`) | 17,518,685 (+1.9 M) | 18,230,216 (100) | 5,072,276,241 (+472 M) | 444,220,984 (+276.7 M) | 25.4 |
| 3. Python's shutdown under its own budget, as spec 055's close | as option 1 | as option 1 | as option 1 | as option 1 | as option 1 |
| 4. a fresh, unfrozen `__main__` per program | +10,904 | +62,918 (100) | +1,288,886 | +29,676 | 10.71 |

Sources: `probe.out` (options 1 and 2). Option 4's row is the pre-build review's like-for-like measurement (`cases5.out`: today's `run` against a prototype of Decisions 1 to 3, both exec'd into `_reactor` and called through the same `-c` wrapper, so the wrapper's compile is the same on both sides). The same pair gives a script `pass` −117,389 (snapshot) and −1,035,053 (plain), and `-m` −8,386 and −73,283: those rows fall, because runpy's temporary module is gone. The plain binary's `import pandas` row rises +17,327 and its gap row falls −20,085. This draft's own first figure, about +0.53 M (`probe_fresh_cost.out`), was an upper bound: most of it was the compile of the wrapper's extra lines, which the precompiled bootstrap never pays (one extra line that only makes a module cost +196 K, the review's `cases1.out`).

What each covers, and what it restates:

1. **Unfreeze before finalizing.** It gives the snapshot CPython's teardown exactly, so it keeps every row above, and also the residual case below. But it costs 28.2 M on every snapshot call, most of it the shutdown's collections now walking and freeing the bootstrap's heap. A bare call becomes 2.8 times dearer, and the snapshot's start only 3.8 times cheaper than the plain start. **It restates spec 069's check (b)**, whose factor of 8 it fails, and it undoes the reason 069's Decision 4 kept the freeze. It does not fix a script or `-m`, which lose their bytes on the plain binary too.
2. **Flush every live file.** It does more than CPython does in one way and less in another. It flushes but does not finalize, so a `ZipFile` left open still has no central directory (`probe.out`: "zip BAD" after the walk). Its walk costs 276.7 M on the plain binary, whose heap is all young, and 472 M on the snapshot after `import pandas`, as spec 055 found (P11). It restates nothing in (b), only because the plain start grows more than the snapshot's. Spec 055 rejected it for the same reasons.
3. **Python's shutdown under a budget, as 055 does.** `run` already runs Python's shutdown: its C entry calls `Py_FinalizeEx()` inside the call's own fuel and deadline (`recipes/reactor_main.c`, `run`). What a session's close adds is the unfreeze and a separate budget around it. So its fuel is option 1's, it restates (b) the same way, and it adds a limit to `run`'s public API (a `shutdown` budget), which spec 049 would have to allow. It buys nothing option 1 does not.
4. **A fresh `__main__` per program.** The namespace is made at run time, after the freeze, so the collector tracks it as it tracks the plain binary's. It keeps every row of the cause's table, on both binaries, for about eleven thousand instructions on a bare snapshot run. It **does not restate (b)**: the factor stays at 10.7. Run a script and `-m` in that same `__main__`, as CPython's own entry points do, and they keep their bytes too (`probe_in_main.out`: 100 on both binaries), for fewer instructions than today.

**The residual, which option 4 leaves.** A program can hang its own objects on the frozen heap itself. Then the frozen heap reaches them, and on the snapshot they are never finalized. Two measured shapes (EXECUTED):
- **A pre-imported class patched from `__main__`.** `json.JSONEncoder.default = default`, with `default` defined in the program, a common idiom: the frozen class now reaches the program's function, its `__globals__`, and the open file. The bytes are lost on the snapshot with a fresh `__main__`, and kept on the plain binary and with option 1 (`probe_patch.out`).
- **An open file stored as an attribute of a pre-imported module.** `import json; json.log = open(...)`. Of the 70 modules in a snapshot program's `sys.modules` at its start, 15 lose the bytes this way (their module objects die at removal, like `__main__`'s, and their dicts are frozen cycles): `_colorize _reactor _zip_directory ast collections csv dataclasses encodings io json os.path posixpath re reprlib site`. The plain binary keeps all 70 (`probe_modules.out`). Keeping those modules alive to the wipe closes this shape (+2.8 M, simulated) but not the patched class (`probe_keep.out`, `probe_patch.out`), so it is not taken.

Only option 1 closes the residual, at 28.2 M per call. That trade (the snapshot's cheap start against a corner the program builds itself) touched the owner's decision 34 and the reason the freeze was kept, so it was put to the owner as question 103. **The owner answered "Yes, unfreeze before finalizing"** (2026-10-19), so this specification takes options 4 and 1 together (Decision 4; the amendment's measurement below).

## Decisions

1. **Option 4: every program gets a fresh `__main__`, made at run time.**
   - `_reactor` captures the names of the interpreter's own `__main__` once, when it is imported (before any program, and before the snapshot's freeze): `__name__`, `__doc__`, `__package__`, `__loader__`, `__spec__` and `__builtins__`, as CPython's `add_main_module` and the module type make them.
   - `run`, after `_refresh` and before it dispatches on the mode, makes a new module named `__main__`, gives its dict those names, and puts it in `sys.modules["__main__"]`. Every mode then runs in it.
   - It is made in `run`'s own frame, before the program's `exec`, so a program's stack is as deep as today (spec 054's check pins `traceback.extract_stack()` at 2 frames, and 4 under the import path's prelude). The builder may make it inside `run`'s `try`, so a `MemoryError` there is reported as any other (the review's note).
   - **Both binaries.** The plain binary's `__main__` is not frozen, but one code path is simpler to state and to check, and a fresh module costs it about 30 thousand instructions (the review's `cases5.out`).
   - **The prelude.** Under an import path, the runner's prelude (`_import_prelude`) is a `-c` program that calls `_reactor.run` again. The outer call makes a fresh `__main__`, the prelude binds no name in it, and the inner call makes another for the caller's program. The names come from the capture, not from the current `__main__`, so nesting cannot leak names.
   - *Why, now that the snapshot also unfreezes (Decision 4):* the unfreeze alone fixes `-c` and stdin on the snapshot, but not a script, a directory or `-m`, which lose their bytes on the plain binary too, in runpy's temporary module; the fresh `__main__` is what fixes those, on both binaries, and it keeps a program's namespace out of the frozen heap while it runs. The old, frozen `__main__` is dropped from `sys.modules`; nothing else holds it, so reference counting frees it.

2. **A script runs in `__main__` itself, with native CPython's globals** (the review's F1).
   - **A file** (`pkgutil.get_importer(target)` is `None`, runpy's own test): `code = runpy._get_code_from_file(target, "__main__")`, which reads a `.pyc` or compiles source as `run_path` does. Then `run` does what CPython's `_PyRun_SimpleFile` does for a script (`Python/pythonrun.c`): it sets `__file__` to the target, sets `__loader__` to `importlib.machinery.SourceFileLoader("__main__", target)`, or `SourcelessFileLoader` when the target ends in `.pyc` (`set_main_loader`; CPython's `maybe_pyc_file` also takes a `.pyc` by its magic number under another name, which `run` does not, a corner recorded here), runs `exec(code, main.__dict__)`, and removes `__file__` again in a `finally`, as CPython does on every path. `__package__` and `__spec__` stay the fresh `__main__`'s `None`.
   - **A directory or a zip:** `sys.path.insert(0, target)`, then `runpy._run_module_as_main("__main__", alter_argv=False)`. This is CPython's own path for such a target (`Modules/main.c`: `pymain_sys_path_add_path0`, then `pymain_run_module(L"__main__", 0)`).
   - **The globals, now native's** (`native_atexit.out`, and the review's `native.out`):

     | mode | `__file__` during the run | `__package__` | `__spec__` | `__loader__` | `__file__` in an `atexit` handler |
     |---|---|---|---|---|---|
     | a file | the target | `None` (today `''`) | `None` | `SourceFileLoader` (today `None`) | absent (today the handler sees an empty module) |
     | a `.pyc` file | the target | `None` | `None` | `SourcelessFileLoader` | absent |
     | a directory or zip | its `__main__.py` | `''` | named `__main__` | `SourceFileLoader` | its `__main__.py` |
     | `-m` | the module's file | its parent, `''` at top level | the module's | its loader | the module's file |

     In every mode `__builtins__` becomes the builtins module, as in `-c` and as native CPython gives `__main__`, where today `exec` into a temporary module inserts the builtins' dict.
   - **Three changes a user can see, all toward native** (the review's F3, EXECUTED there, `cases3.out`), each held by a check row (check C and check E, Decision 7):
     - an `atexit` handler in a script, a directory or `-m` finds the program's `__main__`: its classes and functions (so pickling a `__main__` class there works), and `__file__` for a directory or `-m`. Today it finds the restored, empty `__main__`, and pickling raises `AttributeError`;
     - a directory or zip without `__main__.py` prints CPython's line, `/usr/local/bin/python.wasm: can't find '__main__' module in '/empty'`, and returns 1. Today it prints an `ImportError` traceback (exit 1);
     - `-m`'s change is Decision 3's.
   - The "can't open file" message is unchanged: the `OSError` still rises from runpy's frame (`_get_code_from_file`), which `_only_runpy` checks. A script's traceback is unchanged byte for byte (the review's `cases3.out`): `_report` strips runpy's frames, and a file script now has none above its own.
   - *Why native, not runpy's values:* the spec's promise is "as CPython's own entry points"; nothing in `tests/` pins `''` or a `None` loader (the review's grep); and the change costs two assignments. Check C pins native's values, so a later drift is caught.
   - *Why runpy's private helpers:* the pinned stdlib zip carries a fixed `runpy`, and CPython's own `-m` calls `runpy._run_module_as_main`, so these helpers are what the interpreter itself relies on. Check C pins the globals, so a CPython upgrade that changes them is caught.

3. **`-m` runs as CPython's own `-m` does: `runpy._run_module_as_main(target)`.**
   - It runs the module in `__main__`'s dict and sets `sys.argv[0]` to the module's file, as `run_module(..., alter_sys=True)` did during the call (spec 054's check: `['/code/pkg/__main__.py', 'x', 'y']`).
   - Its globals are today's (`__spec__` the module's spec, `__loader__` its loader, `__file__` its origin), except `__builtins__`, as for a script; they match native's (`native_atexit.out`).
   - **Its traceback shows CPython's frames** (the review's F3). `_report` strips runpy's frames only for a script, so an `-m` traceback shows them, as native does. Today it shows `run_module`, `_run_module_code` and `_run_code`; after, `_run_module_as_main` and `_run_code`, both `"<frozen runpy>"`, byte for byte native's (the review's `cases3.out`, `native.out`). Check E holds the frame names.
   - A module that cannot be found now ends as native's does: `_run_module_as_main` calls `sys.exit(f"{sys.executable}: No module named prog")` (READ, `Lib/runpy.py`), and the guest's `sys.executable` is `/usr/local/bin/python.wasm` (`probe_runner.out`), so `run` prints that line and returns 1 (`_exit_code`). Today it prints an `ImportError` traceback. No check pins today's form (`grep` of `tests/`); check E pins the new line (the review's `cases3.out` saw it from the prototype).

4. **`run` on the snapshot undoes the freeze before it finalizes** (the owner's answer to question 103: "Yes, unfreeze before finalizing").
   - **The freeze stays for the start.** `wizer.initialize` keeps `gc.collect(); gc.freeze()`: a program still runs with the bootstrap's heap out of the collector's way, and pays its teardown only at the end.
   - **The reference.** `wizer.initialize` takes a strong reference to `gc.unfreeze` into the existing static `unfreeze_function` (`recipes/reactor_main.c`), once, before the freeze and before any program exists. `gc` is already imported there (the freeze imports it), and it is already in a snapshot program's `sys.modules` at its start (`probe_modules.out`), so nothing a program sees changes. On the plain reactor nothing is frozen and the reference is not taken there.
   - **The call.** In `run`, after `_reactor.run` returns and `turn_function` is cleared, and before `Py_FinalizeEx`: if `unfreeze_function` is set, call it; an error is shown and dropped with `show_and_drop()`, as `shutdown` does; then `Py_CLEAR(unfreeze_function)`. So `atexit` handlers and the teardown see the whole heap, exactly as a session's close gives them (spec 055, Decision 8).
   - **Why a reference taken at build, not a lookup at the end.** A program can replace `gc.unfreeze` or `sys.modules["gc"]`; a lookup after it would call the program's stand-in, and the snapshot would lose the bytes again. Spec 055 took its reference before any guest code for the same reason (its re-review's N1). Check D's third program holds it (not measurable before the build: on today's binary the bytes are lost either way; stand-in S8 shows it).
   - **Cost** (EXECUTED; the amendment's table): about +28.2 M fuel on every snapshot `run`, the shutdown's collections now walking and freeing the bootstrap's heap. A bare snapshot run goes from 15.6 M to about 43.9 M.
   - **A metered `run` pays it after the program has ended** (the confirmation's A1, EXECUTED there, `meter.out`). The bootstrap flushes the program's output before `Py_FinalizeEx`, so a `fuel=` cap sized for the program alone can now run out in the teardown: simulated, `print('hello')` capped at 40 M used 29.4 M and exited 0 before; with the unfreeze it ends `exit_code None`, `trapped "out of fuel"`, with `hello` already on stdout (a cap of 70 M passes, using 57.8 M). How such an ending is reported does not change: it is the "out of fuel" every metered call already has, and a session's shutdown is reported the same way ("stopped"). The README and the CHANGELOG say to size the cap for it (Design).
   - **What else could the +28 M break** (READ, the confirmation and this amendment's grep of `src/` and `tests/`):
     - `run`'s default fuel is `None`, no cap (`src/wasi_python/runner.py`, `run` and `run_async`), and so is `wasi-python run`'s without `--fuel` (`src/wasi_python/cli.py`). No default changes meaning.
     - No README example passes a `fuel=` number to `run`.
     - The capped checks that expect a program to finish on the snapshot have margins of a gigainstruction or more: `test_v1_3_lxml.py`'s two (40 G and 20 G, for about 31 G and less), `test_a_cpp_exception_reaches_python` in `test_v1_3_data_stack.py` (50 G), the dotted-builtins check in `test_v1_1_artifact_set.py` (10 G, for about 6.0 G), 071's recursion checks (10¹¹) and `test_v1_4_embedding.py`'s `fuel=10**9` to `10**15` calls. The caps of 400 M "past start-up" (`test_a_mounted_run_out_of_fuel_counts_the_cap`, the endings check) are on programs that loop forever and must end "out of fuel" anyway; the start-up they pass is unchanged, since the unfreeze comes after the program.
     - So no check needs a new cap or a new row; the full judge (criterion 7) is what confirms each still passes, and the builder names any that does not as a finding before "built".
   - **Check (b) is restated from 8 to 3.** The snapshot's start becomes 3.82 times cheaper than the plain start (167,505,958 ÷ 43,851,082, projected from the like-for-like measurements). 3 leaves 27% of margin, as 069 left about 25%. The margin is expected to widen as packages land: the plain start grows with the zip's members (spec 039, about 30 K a member). The snapshot's grows too, but far less: its frozen heap holds zipimport's directory of the whole zip, which the unfreeze's teardown now frees, about 0.36 M of the 28.2 M across today's 2,658 members, some 135 instructions a member (the confirmation's A2, EXECUTED there, `cases9.out`, "zd"). A faster plain start would narrow the margin; that specification would restate (b) again. A pre-imported package is refused by check (a) whatever (b) says. The reason in the check's docstring and in `--accept-judge` is question 103's answer.

5. **Sessions are unchanged, and nothing unfreezes twice.**
   - `run` and `turn` exclude each other in one instance (`run_called`, `turned`; spec 055, Decision 2), and `run` refuses after a turn before it reaches the unfreeze. So the freeze is undone at most once per instance: by `run`, or by a session's `shutdown`.
   - On the snapshot, the first `turn` now finds `unfreeze_function` already set, so its `if (unfreeze_function == NULL)` branch is skipped. The object is the same `gc.unfreeze`, and it was taken before any guest code at all, which is earlier than 055's first turn: 055's N1 holds, and more strongly. `shutdown` calls it and clears it, as today. On the plain reactor a session takes its reference at the first turn, as today.
   - A session's turns still run in the `__main__` they find (no fresh one); its close keeps 055's unfreeze. 055's checks (`test_the_shutdown_export_raw`, `test_close_runs_python_shutdown` and the rest of `tests/checks/test_v1_4_sessions.py`) must pass unchanged (criterion 3).

6. **The residual is closed, not documented.** With the unfreeze, a file a program hangs on a pre-imported class or module keeps its bytes on the snapshot (EXECUTED, `probe_combined.out`: the patched class and `json.log` both keep 100). Check D becomes a passing check on both binaries, with no gap entry. The README's corner paragraph (the earlier draft's fourth snapshot fact) is not written.

7. **The judge changes, named.** In `tests/checks/test_v1_4_embedding.py` (v1.4), `tests/known_gaps.toml` and, for check (b), `tests/checks/test_v1_3_data_stack.py` (v1.3):
   - **(h), edited:** `test_run_keeps_an_unclosed_files_bytes`'s docstring loses "a known gap until spec 073" and says the program runs in a fresh `__main__` (Decision 1). Its body is unchanged.
   - **The gap entry for (h)`[snapshot]` is removed**, with its comment block.
   - **A, new: `test_run_keeps_unclosed_files_in_every_mode`** (`@BINARY`, through `wasi_python.run`, recording no fuel, since `run` answers entropy and clocks from the host). Five modes: `-c`; stdin (`argv=[]`, the program as `stdin`); a script (`/prog.py` in the call's root); a directory (`/app`, holding the program as `__main__.py`); `-m prog` (a read-only grant at `/code` on `import_path`, as spec 054's check makes one). Two programs in each: the gap's (`UNCLOSED`, writing `/out.txt`), and a `zipfile.ZipFile("/out.zip", "w")` left open after `writestr("a.txt", "x" * 100)`, beside a `def`. A finding is `"<mode>: a file left open kept <n> of 100 bytes"` or `"<mode>: a zip left open is unreadable"`, reported through `scan.report(findings, "unclosed file")`. Today it fails with 3 findings on the plain binary (the file, in a script, a directory and `-m`) and 7 on the snapshot (both programs in `-c` and stdin; the file in the other three); a zip left open in a script, a directory or `-m` happens to stay readable on both (`probe_check_a.out`). After the build, none.
   - **C, new: `test_every_program_runs_in_an_unfrozen_main`** (`@BINARY`, through `wasi_python.run`, no fuel). In each of A's five modes the program prints: whether its globals are in a collector generation (`any(o is globals() for o in gc.get_objects())`; `gc.get_objects()` never lists the frozen generation, `_PyGC_GetObjects`); whether they are `sys.modules["__main__"].__dict__`; their dunder names; and `__name__`, `__file__`, `__package__`, `__spec__`'s name, `__loader__`'s type name and `__builtins__`' type name. It also registers an `atexit` handler that prints whether `sys.modules["__main__"]` holds the program's class `C`, whether pickling `C()` round-trips, and its `__file__` (or none). It asserts `True`, `True`, today's names, and native's values (Decision 2's table; `-c` and stdin as `test_main_starts_as_native`'s six names, with `__loader__` a `type` and `__builtins__` a `module`); in the handler, `C` present and the pickle round-trips in every mode, with `__file__` absent for `-c`, stdin and a file, and kept for a directory and `-m`. Today it fails on the snapshot's `-c` and stdin (frozen), on both binaries' script (`__package__` `''`, `__loader__` `None`), and on both binaries' script, directory and `-m` (`__builtins__` a `dict`; the handler finds no `C`).
   - **D, new: `test_run_keeps_a_file_the_stdlib_reaches`** (`@BINARY`, through the `guest` fixture, recording the last run's fuel). Three programs, each opening `/out.txt`, writing 100 bytes and not closing it:
     - **the patched class:** `import json`, define `default(self, o)`, set `json.JSONEncoder.default = default`;
     - **the module attribute:** `import json`, `json.log = open('/out.txt', 'w')`;
     - **the tampered unfreeze:** the patched class, after `import gc; gc.unfreeze = lambda: None` (Decision 4's reference).

     A shortfall is a finding, `"<binary>: a file reached from a patched stdlib class kept <n> of 100 bytes"`, `"<binary>: a file stored on a stdlib module kept <n> of 100 bytes"` or `"<binary>: a file reached after gc.unfreeze was replaced kept <n> of 100 bytes"`, reported through `scan.report(findings, "frozen heap")`. `[plain]` passes today and after. `[snapshot]` fails today with `frozen heap: 3 finding(s), digest cfb1afda1a48` (the three strings in this order; computed with `scan.report` by the confirmation), and passes after the build. **It has no gap entry.**
   - **E, new: `test_module_and_directory_errors_read_as_native`** (`@BINARY`, through `wasi_python.run`, no fuel; the review's F3). Three rows: `-m nope` (no such module) prints exactly `/usr/local/bin/python.wasm: No module named nope` and a newline on stderr and returns 1; a directory `/empty` without `__main__.py` prints exactly `/usr/local/bin/python.wasm: can't find '__main__' module in '/empty'` and a newline and returns 1; `-m boom`, a module whose function divides by zero, returns 1 and its traceback's frames are named, in order, `_run_module_as_main`, `_run_code`, `<module>` and `f`, the first two in `"<frozen runpy>"`. It pins names and order, not runpy's line numbers, so a patch release of CPython does not fail it. Today every row fails on both binaries.
   - **Check (b), restated:** `tests/checks/test_v1_3_data_stack.py`, `START_FACTOR = 3` (from 8), its comment and the check's docstring saying that spec 073 restated it by the owner's answer to question 103 (the snapshot finalizes as CPython does, at about +28 M a run). Its body and its message are unchanged.
   - No golden output or other harness constant changes, and no upstream allowance change is expected (Decision 10 says what the builder does if an upstream outcome moves).

8. **The fuel moves, and how the lane accepts it.**
   - **Every snapshot `run` grows by about +28.2 M**, the unfreeze's teardown (+28.2 M on a bare run and on the gap's, +45.2 M after `import pandas`; `probe_combined.out`). So every snapshot fuel row grows past the tolerance of one part in ten thousand: about +180% on a bare row, about +1% on a pandas row.
   - **Every program also pays the fresh `__main__`**: about +11 K on a bare snapshot run and +30 K on a bare plain one, up to +1.3 M after `import pandas` on the snapshot (the review's `cases5.out`). Script and `-m` rows fall by up to −1.0 M (a plain script), since runpy's temporary module is gone. Plain rows move by these amounts only.
   - The builder lists the rows that moved, their largest rise in instructions and in percent, and the bare snapshot row's rise, in the Landing notes. The lane accepts with `--accept-judge` (Decision 7's changes, check (b)'s restated factor among them, with question 103's answer as its reason) and `--accept-growth` naming the measured +28 M per snapshot `run` from finalizing the unfrozen heap (question 103's answer), and the fresh `__main__`'s few thousand.

9. **Why not a smaller change to the gap alone.** Unfreezing only `__main__`'s dict is not possible: `gc.unfreeze()` moves the whole permanent generation. Clearing `__main__`'s dict at the end of `_reactor.run` would run before `atexit` handlers, which may use it, and it is not what CPython does. Keeping `__main__` alive to the wipe (the "main-kept-alive" row) wipes it in reverse import order, after modules it may use (`os` was imported after `__main__`), where CPython frees it first.

10. **How it meets the specifications in flight.**
    - **083** (the judge's driver answers file times and inode numbers; confirmed for build, and it builds after 065 lands): both add checks to `tests/checks/test_v1_4_embedding.py`, at different places, and both edit `tests/known_gaps.toml` (083 narrows 065's stepped-clock gap; 073 removes (h)'s), so they meet in two files, each merge textual. The order in flight is 081, then 065, then 083. Both restate fuel; whichever lands second takes main's progress files and accepts again, as AGENTS.md rule 6a says. Check D and (h) write a file through the driver, so their fuel depends on the file's time and inode number until 083 lands (083 measured that spread at 102 instructions at most, within every row's tolerance); after 083, it is fixed.
    - **081** (guest fuel independent of the checkout path; its guard refuses a measured run whose inputs name a host path): check D and (h) pass guest paths only (`/out.txt`), and A and C record no fuel. No textual overlap: 081 edits `tests/harness/guest.py`, `tests/checks/conftest.py` and the lxml check.
    - **The upstream suites are consumers** (the review's F5). numpy's and pandas' suites run the judge's `drive.py` as a script (`tests/harness/upstream.py`, `guest_argv`), and spec 065's CPython groups run `regrtest_drive.py` as a script too. So every upstream group moves from runpy's temporary module to `__main__`, with native's script globals. During the run what they see differs only in `__builtins__`, `__package__` and `__loader__`: today's temporary module is also `sys.modules["__main__"]` and carries the same `__file__`, which their `M` lines read. So no outcome is expected to move (INFERRED). **If any upstream outcome moves**, the builder stops, names the group, the test and the cause, and treats it as a further judge change, reviewed as a delta before the build is called built; nothing in `tests/upstream/*.toml` or `tests/upstream/expected/` is edited to absorb it (AGENTS.md rule 4). If 065 lands first, its groups run in 073's full judge like the others.
    - **069**'s check (b) is restated from 8 to 3 (Decision 4), with question 103's answer as the reason; 069's Decision 4 carries a dated amendment line saying so.
    - **Build-class order.** Up to four build-class specifications are built at once while the packages come first (§5.7 as amended 2026-10-19), and 073 takes a slot only when no package is ready. It edits `recipes/reactor_bootstrap.py` and `run`/`wizer_initialize` in `recipes/reactor_main.c`, so a rebase meets another recipe change only there.

## Intent

A program that leaves a file open keeps its bytes, through `run`, on both binaries and in every mode, as native CPython keeps them. On the snapshot, `run` finalizes exactly as CPython does, a file the program hung on the stdlib included, by the owner's choice (question 103); it pays about 28 M instructions a call for it, and check (b) is restated to say so.

## Design

- `recipes/reactor_bootstrap.py`:
  - at import: `_MAIN_NAMES = dict(sys.modules["__main__"].__dict__)`, with a comment citing this specification and `add_main_module`;
  - `_fresh_main()`: `main = type(sys)("__main__")`, `main.__dict__.update(_MAIN_NAMES)`, `sys.modules["__main__"] = main`, return `main`; a comment says why (the frozen heap, the cause above, Decision 1);
  - `run`: `main = _fresh_main()` replaces `main = sys.modules["__main__"]`; the `-m` branch calls `runpy._run_module_as_main(target)` after `sys.argv = [target, *rest]`; the script branch tests `pkgutil.get_importer(target)` and takes Decision 2's two paths (for a file: the code from `runpy._get_code_from_file`, `__file__` and the loader set, `exec`, and `__file__` removed in a `finally`). The module docstring gains one sentence on the fresh `__main__`.
- `recipes/reactor_main.c`: `wizer_initialize` takes `unfreeze_function` before the freeze; `run` calls and clears it before `Py_FinalizeEx` (Decision 4); the comments above `run`, above `turn`'s first-turn branch and above the freeze say so (the freeze's comment loses "unfrozen, a bare run on the snapshot costs 43.8 M fuel instead of 15.6 M", which becomes what `run` pays); the file's header says `run` finalizes as a session's close does.
- `tests/checks/test_v1_4_embedding.py`: (h)'s docstring; checks A, C, D and E (Decision 7), beside (h).
- `tests/checks/test_v1_3_data_stack.py`: `START_FACTOR = 3`, its comment and check (b)'s docstring.
- `tests/known_gaps.toml`: (h)'s entry and its comment removed. No entry is added.
- `README.md`: the snapshot's facts after "`run` treats its arguments as CPython's command line does" say every program runs in a fresh `__main__`, a script and `-m` in it as CPython's own entry points run them, and that `run` on the snapshot finalizes as CPython does (no corner paragraph); the *Measured* table's snapshot `-c pass` row becomes the built set's count (about 43.9 M guest instructions, from 15.6 M), its milliseconds re-measured by the builder as a benchmark fact, and "most of it finalizing the interpreter" kept; any other sentence that quotes the bare snapshot start (the builder greps `15.6`) follows; and one sentence beside `run`'s `fuel` (the confirmation's A1): `fuel` counts the interpreter's finalization, after the program's last line; on the snapshot that is about 28 million instructions (about 45 million after `import pandas`), and a cap that runs out there ends `"out of fuel"`, with `exit_code` `None`, after the program's own output was written; size a metered call's `fuel` to cover it, as for a session's shutdown.
- `CHANGELOG.md`, 0.1.0a7: one **Fixed** bullet (the snapshot's unclosed files, a file the program hung on the stdlib, and a script's and `-m`'s on both binaries), which also says a bare snapshot call now costs about 43.9M guest instructions instead of 15.6M (question 103), most of it after the program has ended, so a `fuel=` cap must cover the finalization (about 28M; about 45M after `import pandas`) or the call ends "out of fuel" after its output; and one **Changed** bullet naming what moves toward native: a script's `__package__` and `__loader__`, `__builtins__` a module, an `atexit` handler that finds the program's `__main__`, `-m`'s not-found line and traceback frames, and a directory's "can't find '__main__' module" line; and spec 069's bullet loses "Known and unchanged: `run` on the snapshot loses …".
- `context/roadmap.md`: 073's paragraph says drafted, then built, then landed, as it goes.
- Specs 003 (its `run` paragraph) and 069 (Decision 4): one dated amendment line each, written in with this revision (the review's F6) and restated by the amendment (069's names the unfreeze and the factor of 3). Spec 055's addendum is a research memo, which is never edited after the fact (`context/README.md`), so it gets no line; this specification cites it.

## Scope

In: `_reactor.run`'s namespace and its script and `-m` paths; the judge changes of Decision 7; the README, CHANGELOG and roadmap lines.

In, by the amendment: the unfreeze before `run` finalizes on the snapshot, and check (b)'s restated factor (Decision 4).

Out:
- the freeze itself, which stays for the start (Decision 4);
- sessions (Decision 5);
- `_report`'s handling of tracebacks, which is unchanged;
- a file held only in a reference cycle that the program drops while it runs, which CPython also may not flush (`native.out`; the README already says so for sessions);
- anything in `src/`, `scripts/` or the workflow.

## Acceptance criteria

Each check is seen failing first, before the code it guards, on main's set `build/sets/s-c50ca51fae5eb55b-c9dcb5b8`, and against each stand-in named. Stand-ins are built in the worktree from the branch's recipe with one change each, run, and dropped; their output goes to `build/073/*.log`.

1. **The checks fail first, as Decision 7 says.** On main's set: A fails with 3 findings on the plain binary (digest `e6d5609d06d8`) and 7 on the snapshot (digest `98d69ac9128b`; `probe_check_a.out` ran its logic); C fails on the snapshot's `-c` and stdin and on both binaries' script, directory and `-m`; E fails on all three rows on both binaries; D`[plain]` passes and D`[snapshot]` fails with digest `cfb1afda1a48`; (h)`[snapshot]` fails with digest `7da6e52329c1`.
2. **After the build, the gap closes.** (h)`[snapshot]` passes, its gap entry is gone, and the scoreboard shows one gap fewer from it. A, C, D and E pass on both binaries.
3. **What must not move.** `test_main_starts_as_native` (both binaries; it pins the six names only, and check C pins their values, the review's F2) and `test_the_import_path_reaches_every_mode` (both binaries; its stack depths 2 and 4, its `-m` argv, its script's exit code 3) and every check in `tests/checks/test_v1_4_sessions.py` pass unchanged. Check (b) passes with `START_FACTOR` 3, and its factor on the built set is between 3.5 and 4.2 (projected 3.82); the Landing notes record both counts.
4. **The cost, counted.** The snapshot's `-c pass` fuel on the built set against main's accepted row for check (b) (15,631,800 at the measurement): the rise is between +27.7 M and +28.8 M (projected +28,219,282: the unfreeze's +28,208,378 and the fresh `__main__`'s +10,904). Below that, the unfreeze did not run; above it, something else was added (an eager import of `runpy`, about 20 M, would show). The plain binary's `-c pass` rises by at most 0.1 M (projected +29,676). The Landing notes give the numbers and the command.
5. **Stand-ins.** Each fails what it names:
   - **S1**, the fresh `__main__` made but `-c` and stdin still `exec` in the old one: A (the snapshot's `-c` and stdin rows), C and (h)`[snapshot]` fail.
   - **S2**, the script branch left on `runpy.run_path`: A's and C's script and directory rows fail, and E's directory row.
   - **S3**, the `-m` branch left on `runpy.run_module`: A's and C's `-m` rows fail, and E's two `-m` rows.
   - **S4**, the fresh `__main__` a bare `type(sys)("__main__")`, without the captured names: C's `-c` and stdin rows fail (`__builtins__` a `dict`, `__loader__` `None`). It does not fail `test_main_starts_as_native`, whose six names the module type and `exec` still give (the review's F2, `cases4.out`).
   - **S5**, the file-script branch giving runpy's `__package__` `''` and `__loader__` `None`: C's script row fails.
   - **S7**, the file-script branch without the `finally` that removes `__file__`: C's script row fails in its `atexit` part.
   - **S6**, `run` without the unfreeze (the design before the amendment): D`[snapshot]` fails (the patched class and the module attribute), and criterion 4's count rises only about 11 K.
   - **S8**, `run` looking `gc.unfreeze` up from `sys.modules["gc"]` after the program instead of the reference `wizer.initialize` took: D's tampered-unfreeze row fails on the snapshot.
   - **S9**, the reference taken but `Py_CLEAR` left out and `shutdown` reached in a session: no check can see it, since `run` and `turn` exclude each other; the builder shows instead, with `tests/checks/test_v1_4_sessions.py` green, that a session's shutdown still unfreezes once (`test_the_shutdown_export_raw[snapshot]`).
6. **The README and CHANGELOG lines** of the Design; `tests/public_api.txt` unchanged (`tests/harness/api.py` finds no change).
7. **The judge, in the worktree, without `--accept`,** against the built set: the fast tier while building, then the full judge with `-n 3` (the machine is shared) before "built": 0 fail, no pass lost, one gap fewer ((h)) and none added; every growth is the unfreeze's, the fresh `__main__`'s or the script and `-m` change's, listed as Decision 8 says; the judge change named (`tests/checks/test_v1_4_embedding.py`, `tests/known_gaps.toml`, `tests/checks/test_v1_3_data_stack.py`); `ruff check` and `ruff format --check` green.
8. **The lane** rebuilds the set from the pins in the main tree, compares it with the builder's on the same base, judges serially and accepts, as §5.7 says for a build-class change.

## The measurement (EXECUTED)

Evidence: `../research/2026-10-19-run-and-the-frozen-main/`. Against `build/sets/s-c50ca51fae5eb55b-c9dcb5b8` in the main tree (main's set at `08de0c8`), read only; macOS arm64, wasmtime-py 49.0.0, the worktree's own `uv` environment. Each script names its command in its docstring.

- `probe.py` → `probe.out`: the cause's rows and the options' costs (the tables above).
- `probe_when.py` → `probe_when.out`: when `__main__`'s module dies and when a value in it is finalized, per binary.
- `probe_modes.py` → `probe_modes.out`, and `probe_runner.py` → `probe_runner.out`: the gap's program in each mode, through the driver and through `wasi_python.run`.
- `probe_in_main.py` → `probe_in_main.out`: a script and `-m` run in a fresh `__main__` keep 100 on both binaries.
- `probe_fresh_cost.py` → `probe_fresh_cost.out`: the fresh `__main__`'s own cost: +533,134 (bare, snapshot), +577,332 (the gap, snapshot), +540,848 (bare, plain), against a control running the same wrapper.
- `probe_globals.py` → `probe_globals.out`: each mode's namespace today (check C's expected values).
- `probe_check_a.py` → `probe_check_a.out`: check A's logic on main's set, with its findings.
- `probe_dir.py` → `probe_dir.out`: a directory target today (its bytes and its namespace).
- `native_atexit.sh` → `native_atexit.out` (added for the revision): native CPython 3.15.0's `__main__` globals for a script, a `.pyc`, a directory and `-m`, during the run and in an `atexit` handler (Decision 2's table).
- `probe_combined.py` → `probe_combined.out` (added for the amendment): the combined design, a fresh `__main__` and, on the snapshot, the unfreeze, against today, like for like.
- `probe_modules.py` → `probe_modules.out`: the residual's module shape, 15 of 70 modules.
- `probe_patch.py` → `probe_patch.out`: the residual's patched-class shape, and that only option 1 closes it.
- `probe_keep.py` → `probe_keep.out`: keeping the snapshot's modules alive closes the module shape for +2.8 M, but not the patched class.
- `native.sh` → `native.out`: native CPython 3.15.0 (the build's pinned host Python, `build/tools/python` in the main tree) on each mode and on files whose last references are garbage.

## Landing notes

### What was built

On `spec/073-run-keeps-unclosed-files-bytes`, rebased onto main `a6dfc17` (081, the README corrections, the answered questions, the 0.1.0a7 release and the 0.1.0a8 bump): `e2aee03` (the checks first), `6ab51ab` (the recipe, the judge's restatements, README and CHANGELOG), `e02808a` (the first landing notes), then the build review's fixes and these notes. First built from an empty `build/` with `scripts/build.sh --plain` (16 steps in 16 min 21 s, `build/073/build.log`); **rebuilt after B1** with every step again (9 min 9 s, `build/073/build2.log`), the downloads copied from the main tree and verified by the build (49 pins, 0 fetched).

- `recipes/reactor_bootstrap.py`: `_MAIN_NAMES`, captured at import; `_fresh_main()`, called inside `run`'s `try`; `_run_file()` for a script file (code from `runpy._get_code_from_file`, `__file__` and a `SourceFileLoader` or `SourcelessFileLoader` **taken from `_frozen_importlib_external`** (B1), `exec`, `__file__` removed in a `finally`); `-m` through `runpy._run_module_as_main(target)`; a directory or zip through `sys.path.insert(0, target)` and `runpy._run_module_as_main("__main__", alter_argv=False)`; `_only_runpy` skips the reactor's own frames.
- `recipes/reactor_main.c`: `wizer_initialize` takes `unfreeze_function` (`gc.unfreeze`) before `gc.collect(); gc.freeze()`, and aborts the build if it cannot; `run` calls it after the bootstrap returns and before `Py_FinalizeEx`, with `show_and_drop()` on an error, then clears it; a forward declaration of `show_and_drop`; the comments of Decision 4.
- Judge: checks A, C (with its `warnings` row, B1), D and E and (h)'s docstring (`tests/checks/test_v1_4_embedding.py`); (h)'s gap entry removed (`tests/known_gaps.toml`); check (b)'s `START_FACTOR` 8 → 3 with its comment and docstring (`tests/checks/test_v1_3_data_stack.py`). No other check, golden, allowance or harness constant changed.
- `README.md`: the run paragraph (every program in a fresh `__main__`), a fourth snapshot fact (the unfreeze), the `fuel` sentence (A1; "more after large imports … up to about 90M", B2), the *Measured* rows for the snapshot's `-c pass` (43.8M, 16 ms) and `import pandas` / `import numpy` (4.66G / 0.81G). `CHANGELOG.md`: one **Fixed** and one **Changed** bullet in main's `## 0.1.0a8 — unreleased` section, replacing its placeholder.

### The artifact set (EXECUTED, the rebuild)

`build/artifacts/`; after the S6 stand-in below, steps 60, 80 and 90 rebuilt it to the same bytes (`build/073/rebuild-good2.log`, every file `cmp`-equal):

| file | bytes | SHA-256 |
|---|---|---|
| `SHA256SUMS` | – | `8a30505a0b65337587b93343a98d083a616bfea50853f21ab71d700beb69412f` |
| `python.wasm` | 41,101,929 | `95af9257191bdbefb5875fa1b740b43e5ac7d74df256c2c1e3e8ac758d7f996b` |
| `python-snapshot.wasm` | 44,632,292 | `3592321dfe3adebd1b9cdc999cfa882dd57525e21e80857f35b0ce9ba5bee6c0` |
| `python-stdlib.zip` | 22,197,173 | `02026895917b7e22923db1bad99a02ee1d22f7382ff63715271e39fb9032d1fe` |

The zip is byte for byte main's: only the two binaries change. (The first build, before B1, was `SHA256SUMS` `82365b44…`, snapshot 44,641,933 bytes.)

### Criteria, with their evidence

1. **The checks fail first** (EXECUTED, `build_first_fail.out`, on a fresh `cp -Rp` copy of `build/sets/s-c50ca51fae5eb55b-c9dcb5b8`, whose zip has one link): A fails with 3 findings on the plain binary (`e6d5609d06d8`) and 7 on the snapshot (`98d69ac9128b`); C fails on both; E fails on both; D`[plain]` passes and D`[snapshot]` fails with **`frozen heap: 3 finding(s), digest cfb1afda1a48`**, the confirmation's digest; (h)`[snapshot]` is its gap. C's `warnings` row, added for B1, was seen failing on the first build's set, on the script row of both binaries (`(True, True)`), and passing on `-c` and stdin (`build/073/c-b1-before.log`).
2. **After the build** (EXECUTED, the full judge on the rebuilt set): (h)`[snapshot]` passes and its gap entry is gone; A, C, D and E pass on both binaries.
3. **What must not move** (EXECUTED, the full judge): `test_main_starts_as_native`, `test_the_import_path_reaches_every_mode` and all of `tests/checks/test_v1_4_sessions.py` pass. Check (b) passes with `START_FACTOR` 3 at **3.829** (plain 167,554,032 ÷ snapshot 43,758,719; `build_measure.out`), inside 3.5 to 4.2.
4. **The cost, counted** (EXECUTED, `build_measure.out`, main's set copy against the rebuilt set, through the judge's driver): the snapshot's `-c pass` **15,631,800 → 43,758,719, +28,126,919 (+179.93%)**, inside the band of +27.7 M to +28.8 M. The plain binary's `-c pass` 167,481,449 → 167,554,032, **+72,583**, inside 0.1 M. The gap's row: snapshot +28,142,117 and 0 → 100 bytes; plain +107,895. `import pandas`: snapshot +61,373,676 (+1.33%), plain +96,629. The pandas row is sensitive to allocation timing: the same program with one more line (`import gc`) gives 4,645,086,882 on the same set, 16.5 M less (EXECUTED); the first build gave +46,282,284. So "about 45 M to 60 M after `import pandas`" (INFERRED: the shutdown's work depends on where collections fell).
5. **Stand-ins** (EXECUTED on the first build, `build_standins.py` → `build_standins.out`; each a one-change recipe, steps 60, 80 and 90 rebuilt, seven checks run, the recipe restored). B1 changed only `_run_file`'s import, which no stand-in touches; S6 was run again on the rebuild and fails as before.
   - **S1** (`-c` and stdin `exec` in the old `__main__`): C, (h) and A fail, on both binaries.
   - **S2** (the script branch on `runpy.run_path`): C, E and A (script and directory rows) fail.
   - **S3** (`-m` on `runpy.run_module`): C, E and A (the `-m` row) fail.
   - **S4** (no captured names): only C fails (`-c` first), as the review's F2 said; `test_main_starts_as_native` passes.
   - **S5** (runpy's `__package__` `''` and `__loader__` `None`): C's script row fails.
   - **S6** (no unfreeze): D`[snapshot]` fails with `cfb1afda1a48`, on both builds.
   - **S7** (no `finally`): C's script row fails (its `atexit` part).
   - **S8** (`gc.unfreeze` looked up after the program): D`[snapshot]` fails on its tampered row alone, `frozen heap: 1 finding(s), digest be4330beba1d`.
   - **S9**: no check can see it; `tests/checks/test_v1_4_sessions.py` is green on the rebuilt set, `test_the_shutdown_export_raw[snapshot]` among them.
6. **README and CHANGELOG** as above; `tests/public_api.txt` unchanged (the public-API checks pass).
7. **The judge, in the worktree, without `--accept`** (EXECUTED, on the rebuilt set, with the upstream kit and the oracle copied from the main tree, hash-checked by the judge's needs; `build/progress/latest.json` kept, a copy in `build/073/latest-full3.json`): **the full judge** (`uv run pytest -n 3`, `build/073/full3.log`): `wasi_python v1: 545/562 pass · 14 gap · 3 blocked · 0 fail (unit suite 1504/1511, 7 skipped)`; `blocked by: prior-art clones 1 · three systems 1 · wheel 1`; `ratchet vs dfbf8e044f: lost 0 · absent 0 · unrun 0 · unrun locally 1 · gained 9 · grew 140 · judge changed: tests/checks/test_v1_3_data_stack.py, tests/checks/test_v1_4_embedding.py, tests/known_gaps.toml`; `RED: 140 metric(s) grew`; `2049 passed, 10 skipped, 14 xfailed in 583.18s`. The 9 gained are A, C, D and E on both binaries and (h)`[snapshot]`. Before B1, the fast tier and two full runs on the first build gave the same verdicts (`build/073/fast-built.log`, `full.log`, `full2.log`). `ruff check` and `ruff format --check` are green on `src/` and `tests/` (the rules tier).
8. **The lane's** rebuild and serial judgement are the lane's.

### The fuel that moved (EXECUTED, `build_growth.py` → `build_growth.out`, the rebuild)

159 rows moved against `accepted.json`: 151 up, 8 down.
- **Snapshot rows** rise by the unfreeze: a bare run's +28.1 M (about +178%) is the floor; the median snapshot row rises +28.6 M; rows that imported much rise more, up to +70.2 M (`test_ctypes_stand_in_names_what_packages_import[snapshot]`, +1.40%) and +65.5 M on lxml's encodings check (+0.21%). The review measured the unfreeze's share of those two directly (B2: +69.8 M and +69.5 M by appending `gc.unfreeze()` on main's set); the rest of the encodings row is INFERRED to be the fresh `__main__` freeing globals the frozen one leaked.
- **Plain rows** move by the fresh `__main__` and the bootstrap's own growth: from −1,384,757 to +1,805,420 (`test_plot_line_job_matches_native[plain]`). The regex job, +9,880,830 on the first build, is now −60,720: that rise was B1's `warnings` import, not `__main__` living to finalization as the first notes said.
- **Upstream groups** run `drive.py` as a script on the snapshot. Most move by under 0.3%, in both directions (pandas-groupby +0.11%, pandas-tslibs −0.04%). **numpy-core rises +4,484,058,023 (+2.21%)**, 203.36 G → 207.84 G, with its counts unchanged (9,519 passed; `passed_digest` `df21e78e7032`). It is **not** the unfreeze: the S6 stand-in (no unfreeze) gives 207.80 G (EXECUTED, `build_numpycore_S6.out`), so the unfreeze is +42 M of it. On the first build, whose scripts imported `warnings` before the program, the same group was −73.6 M. Its cause inside the suite was not established here after two attempts (AGENTS.md rule 7); **the build review's delta look measured it** (its addendum, "numpy-core's +4.48 G: located and measured", EXECUTED there): 4.29 G of it is one parametrised test, `test_string_comparisons` in `test_strings.py`, whose 504 conversions of 32,768-element lists of Python bools cost about 25% more (25.8 M → 32.4 M a call; `int` and `float` lists unchanged). numpy finds each element's DType in `_global_pytype_to_type_dict`, a dict keyed by the type object, and so by its address; `bool`'s static `PyBool_Type` moved 0x780 with the rebuilt binary's data segment, so its hash and probe sequence changed. A link-layout effect, not 073's semantics: any change to the binary's size can flip it either way (the first build, one line different, gave −73.6 M), and numpy-core carries a layout-sensitive term of a few G for the next build-class spec. The rest is the unfreeze-sized +30 M to +60 M every group pays. **No upstream outcome moved**: 20 groups pass and 12 are gaps with their recorded digests, as accepted (Decision 10). Falls need no acceptance (B4).

### Amendments at build, with their reasons

- **B1 (the build review): the file loaders come from `_frozen_importlib_external`.** `from importlib.machinery import …` ran that module's `__getattr__`, which imports `warnings` and `_py_warnings` into every script run (+10.0 M on a `pass` script, the review's `cases14.out`); native CPython's scripts start without them. CPython's `set_main_loader` takes the loaders from the same place. Check C gained a row that every mode starts with `('warnings' in sys.modules, '_py_warnings' in sys.modules) == (False, False)`, as native 3.15.0 starts in all five (EXECUTED natively).
- **`_only_runpy` skips the reactor's own frames** before it tests for runpy's. `_run_file` is a helper frame (`<reactor>`) between `run` and runpy's `_get_code_from_file`, so without this the "can't open file" line would have become a traceback; with it the line is unchanged.
- **The plain binary's bare row rose +72,583, not the projected +29,676** (B3). INFERRED: on the plain binary the bootstrap is unmarshalled and run on every call, and it grew by two functions and a docstring paragraph; copying six names costs only a few hundred instructions. It is inside criterion 4's 0.1 M bound.
- **Snapshot rows rise by more than 28 M after heavy imports** (up to +70 M; above). The README's `fuel` sentence says "more after large imports: about 45M to 60M after `import pandas`, up to about 90M after many" (B2).
- **The released 0.1.0a7 CHANGELOG section is not edited.** The Design asked spec 069's bullet to lose its "Known and unchanged" sentence; 0.1.0a7 was released before this build, so its notes stand as published and the 0.1.0a8 section says what changed.
- **S1 fails more than criterion 5 named** (also (h) and A on the plain binary): the old `__main__` is out of `sys.modules`, so its dict dies early on both binaries.

### For the lane

- `--accept-judge "spec 073: checks A (test_run_keeps_unclosed_files_in_every_mode), C (test_every_program_runs_in_an_unfrozen_main, with its warnings row), D (test_run_keeps_a_file_the_stdlib_reaches) and E (test_module_and_directory_errors_read_as_native); (h)'s docstring and its gap entry removed; check (b)'s START_FACTOR restated from 8 to 3 by the owner's answer to question 103 (run on the snapshot undoes the freeze before finalizing; measured 3.829)"`.
- `--accept-growth "spec 073: question 103's answer: run on the snapshot finalizes the unfrozen heap, about +28 M fuel a run (+28,126,919 on -c pass), more after large imports (up to +70 M, the unfreeze's share measured by the build review); plain rows move by the fresh __main__ and the larger bootstrap (up to +1.8 M); upstream numpy-core +4.48 G (+2.21%), counts unchanged, not the unfreeze (+42 M of it), its cause in the suite not established"`. (Superseded by the claim list below: the build review's delta look measured numpy-core's cause, and a wave's reasons start with the number.)
- ~~An open point for the lane: numpy-core's +2.21% is the one growth without a measured cause.~~ Closed by the build review's delta look (the numpy-core paragraph above).

#### Claim list (wave 1)

Taken from the builder's full judge on the rebuilt set (`e02808a`'s judge with B1's recipe, `-n 3`, `build/073/full3.log`, record `build/073/latest-full3.json`: `545/562 pass · 14 gap · 3 blocked · 0 fail`; `ratchet vs dfbf8e044f: lost 0 · gained 9 · grew 140`), the build review's delta look on `e1bd770` (its fast tier `grew 119`, check C and numpy-core re-run to within 119 fuel), and a row-by-row comparison of that record with `accepted.json` at the own base, main `a6dfc17` (152 metrics above it, 140 beyond the ratchet's 0.01%, 9 below). The rebuilt set's `SHA256SUMS` is `8a30505a…`.

- **New checks (8), goal v1.4, each `pass` on the rebuilt set:**
  - `tests/checks/test_v1_4_embedding.py::test_run_keeps_unclosed_files_in_every_mode[plain]` and `[snapshot]` (A);
  - `tests/checks/test_v1_4_embedding.py::test_every_program_runs_in_an_unfrozen_main[plain]` and `[snapshot]` (C, with its `warnings` row);
  - `tests/checks/test_v1_4_embedding.py::test_run_keeps_a_file_the_stdlib_reaches[plain]` and `[snapshot]` (D);
  - `tests/checks/test_v1_4_embedding.py::test_module_and_directory_errors_read_as_native[plain]` and `[snapshot]` (E).
- **A gap closes (gap → pass):** `tests/checks/test_v1_4_embedding.py::test_run_keeps_an_unclosed_files_bytes[snapshot]` ((h)); its entry is removed from `tests/known_gaps.toml`. Gained 9 in all.
- **A check restated:** `tests/checks/test_v1_3_data_stack.py::test_the_snapshot_starts_cheaper_than_plain` ((b)), `START_FACTOR` 8 → 3 by question 103's answer; it passes at 3.829.
- **Retired checks:** none. No `--retire`.
- **Passes that move:** none fall. No upstream group's counts or digests move (20 pass, 12 gaps as accepted). No `--accept-fewer-passes`.
- **Rows that grow (140 on the own base), every one this spec's two recipe changes:**
  - **bytes:** `test_binary_is_a_core_wasm_module[plain]` 41,099,661 → 41,101,929 (+2,268). The snapshot falls 1,691 bytes; the zip is unchanged.
  - **snapshot fuel rows** (the unfreeze before `Py_FinalizeEx`, question 103): the bare run +28.1 M (`-c pass` 15,631,800 → 43,758,719); most snapshot rows +28 M to +29 M; more after large imports, up to +70.2 M (`test_ctypes_stand_in_names_what_packages_import[snapshot]`) and +65.5 M (`test_encodings_are_wasi_libcs_as_documented`); a few rise less (lxml's `test_the_readmes_encoding_workaround_reads_what_iconv_cannot`, +7.4 M).
  - **plain fuel rows and the jobs** (the fresh `__main__` and the larger bootstrap): from −1.4 M to +7.3 M (`test_lxml_xml_job_matches_native`, +7.26 M, +0.03%; the plain bare run +72,583).
  - **upstream groups** (all run `drive.py` on the snapshot): +7.7 M (pandas-io-parser) to +543 M (pandas-groupby, +0.11%); **numpy-core +4,484,058,023 (+2.21%)**, a link-layout effect in numpy's address-keyed type lookup for Python bools (the paragraph above), not 073's semantics; on a different binary it is a different number, of either sign.
  - **Rows main added since `a6dfc17`** (spec 065's CPython groups, 078's, 083's and 089's checks, and any other row that runs a snapshot program) were never judged on this set; they move for the same two reasons (each snapshot run about +28 M or more), and their numbers are the wave run's. A grown row on the wave tip that is a snapshot run, a plain-run move of a few M, or `python.wasm`'s bytes, is this claim's unless another entry also claims it.
- **The judge hash changes**, in three files: `tests/checks/test_v1_4_embedding.py`, `tests/checks/test_v1_3_data_stack.py`, `tests/known_gaps.toml`.
- **The flags** (paste-safe):
  - `--accept-judge "073: checks A, C, D and E on both binaries (run keeps unclosed files in every mode, every program in an unfrozen native __main__ with no warnings import, a file the stdlib reaches, -m and directory errors as native); check h closes and its gap entry goes; check b START_FACTOR restated from 8 to 3 by the answer to question 103, measured 3.829"`
  - `--accept-growth "073: run on the snapshot unfreezes before finalizing (question 103), about +28 M fuel a snapshot run, up to +70 M after large imports; plain runs and jobs move by the fresh __main__ and the larger bootstrap, -1.4 M to +7.3 M; python.wasm +2,268 bytes; upstream groups on the snapshot +0.01 to +0.27 percent, and numpy-core +4.48 G, a link-layout effect in the bool-keyed type lookup of test_string_comparisons, measured by the build review, not this spec semantics"`
  - no `--accept-fewer-passes`, no `--retire`.
- **Sameness:** the reviewer's records are `073-review/build-review/reviewer-full-latest.json` (the first build) and `073-review/delta/reviewer-targeted-latest.json` and `reviewer-fast-latest.json` (the rebuilt set) in the lane's scratchpad; the builder's full record on the rebuilt set is `build/073/latest-full3.json` in this worktree. No reviewer full record exists on the rebuilt set: the fuel rows compare against the builder's.
- **Not yet read:** this branch has no CI run (the wave's entry criterion 2; build-class, so rule 2's "built" test asks for one).

The lane moved 073 from wave 1 to wave 2, after the 039 and 041 chain (three build-class entries were over wave 1's cap). The section below restates this list's growth claim for that tip; its `--accept-growth` text replaces the one above.

#### Rebased onto wave/02 (`1ef8256`: main `e8ba20a`, wave 01 landed, then 039 and 041; 2026-10-19)

`git rebase wave/02` replayed 073's ten commits, from main `a6dfc17`. Five hunks conflicted, in three files; I resolved each one as 073's builder. `recipes/reactor_bootstrap.py` and `recipes/reactor_main.c` merged cleanly: nothing since `a6dfc17` touched them. So did `tests/checks/test_v1_4_embedding.py` (078, 084 and 087 also edit it), `tests/checks/test_v1_3_data_stack.py` (039 changed its jobs' runner), `context/roadmap.md` and the dated lines in specs 003 and 069. `git range-diff` shows eight commits `=`; the build commit and B1's commit show `!`, by these hunks alone.

1. **The build commit, `tests/known_gaps.toml`:** wave/02's file whole, less 073's own entry. The base keeps 078's removal of the nine C-stack trap gaps and 041's removal of 039's Tier A gaps. 073 removes only the `test_run_keeps_an_unclosed_files_bytes[snapshot]` entry, with its three-line comment. The resolved file is wave/02's with exactly those ten lines gone (checked by `diff`).
2. **The build commit, `README.md`, the *Measured* table:** four rows.
   - **The snapshot's `-c pass`:** 073's row (16 ms; the unfreeze before finalizing), with 039's tier A fact kept: "43.7M guest instructions (15.6M before spec 073); with tier A in the zip, 20.4M without spec 073 (spec 039) and about 28M more with it". The merged set's own number is the wave run's.
   - **`os._exit(0)`:** unchanged on both sides.
   - **`import pandas` / `import numpy`:** 073's row.
   - **The plain reactor:** 039's row (218M with tier A's members). 073 did not change that row, and its plain cost, +72,583, is below the row's precision.
3. **The build commit, `CHANGELOG.md`, `## 0.1.0a8 — unreleased`:** both sides kept. The base's bullets come first (078, 085, 084, 065, 083, 087, 039, 041), then 073's **Fixed** and **Changed** bullets. On 073's base the section held only the placeholder `- (what changed)`, which 073 replaced; wave/02 no longer has it.
4. **B1's commit, `README.md`, the same table:** B1 changed 43.7M to 43.8M in the snapshot row and rewrote the pandas and numpy row (4.66G / 0.81G). Both are applied to the merged rows; 039's tier A clause and the plain row are kept. B1's `fuel` paragraph and CHANGELOG lines ("more after large imports … up to about 90M") applied cleanly.

**Semantic changes:** none in the recipe, the checks or the runner. Things I checked:
- Check (b)'s `START_FACTOR` 3 still holds with margin on the chain. INFERRED: plain about 218M over a snapshot of about 20.4M + 28M gives about 4.5.
- No check on the merged tree caps a snapshot run's fuel near 073's cost; the smallest caps are 10**8 for a session turn's loop and 10**9 for a run.
- Check C's start rows assert that `warnings` is absent. Tier A pre-imports nothing (039), so nothing changes there.

**Restated growth claim, on top of the 039 and 041 chain.** 039 claims the tier A start cost (+50.6 M a plain run, +4.7 M a snapshot run, a distribution scan per upstream session, CPython's groups +0.13% to +4.27%). 041 claims the Styler and atlas rows and the zip-layout moves. 073 claims, beyond those:
- every snapshot run's unfreeze before `Py_FinalizeEx`: about +28 M a run (+28.1 M on `-c pass` on 073's own base), more after large imports, up to about +70 M. INFERRED: on the chain the floor may be a few M higher, since the snapshot's frozen heap holds the zip directory, which tier A grew by 2,014 members.
- the plain runs' and jobs' moves from the fresh `__main__` and the larger bootstrap: −1.4 M to +7.3 M on 073's own base;
- `python.wasm` about +2.3 K bytes (+2,268 on 073's own base); the snapshot's bytes move by a few K either way (−1,691 on the own base);
- every upstream group, CPython's five included, by its snapshot runs' unfreeze, and numpy-core's link-layout term, which on a different binary is a different number of either sign (+4.48 G on 073's own base, −73.6 M on its first build).

The lane can split a grown snapshot row on the wave tip like this. 039's and 041's shares are in their claims, so the rest, about +28 M or more a snapshot run, is 073's. A plain row that moved by more than 039's +50.6 M start, or 041's zip-layout moves, plus a few M is not 073's.

- `--accept-growth "073: beyond the 039 and 041 claims, every snapshot run unfreezes before finalizing (question 103), about +28 M fuel a run and up to about +70 M after large imports, the floor perhaps a few M more with tier A in the frozen zip directory; plain runs and jobs move by the fresh __main__ and the larger bootstrap, -1.4 M to +7.3 M on its own base; python.wasm about +2.3 K bytes, the snapshot a few K either way; every upstream group by its snapshot runs, and numpy-core by a link-layout term in the bool-keyed type lookup of test_string_comparisons, measured by the build review, of either sign on a new binary (+4.48 G on its own base)"`
- `--accept-judge`: unchanged (above). No `--accept-fewer-passes`, no `--retire`.

**The fast tier on `08ca833`** (`uv run pytest -m "not slow" -n 3`). It ran against a private copy of main's set (wave 01's acceptance: `python.wasm` `5f8d1b29…`, `set_sums` `89b14f67…`), copied to `build/wave01-set`, because no set has 039's, 041's and 073's recipes yet. Log: `build/073/fast-wave02.log`.
- **Result:** `wasi_python v1: 545/701 pass · 0 gap · 6 blocked · 29 fail · 121 deselected (unit suite 1731/1738, 7 skipped)`; `ratchet vs 47b3695c2d: lost 10 · gained 1 · grew 0`.
- **ruff:** `ruff check` and `ruff format --check` green.
- **Every fail needs a rebuilt set or this worktree's stale source trees.** No unit test fails.
  - **073's eight rows, which need 073's rebuilt binaries.** Each gives the digest it gave on main's set at criterion 1:
    - `test_run_keeps_an_unclosed_files_bytes[snapshot]` ((h), `7da6e52329c1`; its gap entry is gone, so it is a fail here);
    - `test_run_keeps_unclosed_files_in_every_mode[plain]` (`e6d5609d06d8`) and `[snapshot]` (`98d69ac9128b`);
    - `test_every_program_runs_in_an_unfrozen_main[plain]` and `[snapshot]`;
    - `test_run_keeps_a_file_the_stdlib_reaches[snapshot]` (`cfb1afda1a48`);
    - `test_module_and_directory_errors_read_as_native[plain]` and `[snapshot]`.
  - **039's and 041's nineteen rows, which need tier A's set.** Eight of them (the four artifact-set rows, the two metadata rows and the two gb18030 rows) are among the lost passes:
    - `test_artifact_set_is_complete`, `test_manifest_is_well_formed`, `test_manifest_recipes_match_the_tree` and `test_licence_notices_cover_every_component`;
    - `test_tqdm_notice_carries_the_mpl_and_its_source`;
    - `test_packages_carry_their_metadata[plain]` and `[snapshot]`;
    - `test_v1_3_default_profile.py`'s eight rows (pure-Python paths, threadpoolctl, the Styler, the networkx atlas, each on both binaries);
    - `test_gb18030_is_never_silently_wrong[plain]` and `[snapshot]` (html5lib);
    - `test_excel_output_needs_a_writable_folder_or_xlsxwriter_in_memory`, both rows.
  - **Two rows that read this worktree's source trees,** made by 073's own build from `a6dfc17`'s recipes, before 041's pandas patch and 087's regex patch: `test_source_tree_matches_its_tarball[pandas]` and `[regex]`. Both are among the lost passes, and a rebuild from the wave tip clears them.
  - **The lost 10:** 039's and 041's eight above and the two source-tree rows. None is a 073 row.
  - **The 1 gained:** `test_run_keeps_a_file_the_stdlib_reaches[plain]`, which passes on main's set, as at criterion 1. Check (b) passes with `START_FACTOR` 3.

## Disposition of the pre-build review

The review: `../reviews/073-run-keeps-an-unclosed-files-bytes-spec-2026-10-19.md` (verdict "ready once F1 to F4 are written in"; written in the lane's scratchpad, to be copied by the lane).

1. **F1 (Medium) — fixed: native's script globals.** Decision 2 now gives a file script `__package__` `None` and a `SourceFileLoader` (`SourcelessFileLoader` for a `.pyc`), and removes `__file__` after the run, as `_PyRun_SimpleFile` does; check C pins native's values and S5 is runpy's values; S7 is new. No measured reason was found to keep runpy's: a native probe added for the revision (`native_atexit.out`) confirms the values, including that an `atexit` handler sees no `__file__` after a native script.
2. **F2 (Low-Medium) — fixed.** S4 names check C's `-c` and stdin rows; criterion 3 says `test_main_starts_as_native` pins names only and C pins their values.
3. **F3 (Low-Medium) — fixed.** Decision 2 names the `atexit` change and the "can't find '__main__' module" line; Decision 3 names the `-m` traceback frames; check C gains its `atexit` part and new check E holds the three error-path rows; the CHANGELOG's **Changed** bullet and the Landing notes list them. "Tracebacks are unchanged" now says a script's.
4. **F4 (Low) — fixed.** Option 4's row is the review's like-for-like measurement (+10,904 snapshot, +29,676 plain on `-c pass`; script and `-m` rows fall, by up to −1,035,053); Decision 1's and option 4's prose, Decision 4's factor (10.71), Decision 8's band and criterion 4's bound (0.1 M) follow; the first figure is kept as the upper bound it was, with why. Question 103's "about 0.5 M" and the roadmap's become "about 11 thousand".
5. **F5 (Low) — fixed.** Decision 10 names the upstream suites as consumers and says the builder stops and treats a moved outcome as a further judge change, reviewed as a delta; Decision 7 says "no upstream allowance change is expected".
6. **F6 (Low) — fixed.** Dated amendment lines in spec 003's `run` paragraph and spec 069's Decision 4. Not in spec 055's addendum, a research memo, which is not edited after the fact.
7. **F7 (Low) — fixed, then superseded.** D's gap reason ended "(spec 073, Decision 6; question 103)"; the amendment removes the gap, since question 103's answer closes it.
8. **F8 (Low) — fixed.** Decision 10: 083 confirmed, building after 065, and meeting 073 in `tests/known_gaps.toml` as well as the check file, both merges textual; the order 081, 065, 083.

The review's notes, taken: the README was to say "may never be finalized" (moot since the amendment, which writes no corner paragraph); the builder may make the fresh `__main__` inside `run`'s `try`. Its note on a relative script target (native makes `__file__` absolute) and the script's directory not on `sys.path` are older than this specification and stay out of scope.

## Amendment of 2026-10-19 (103 answered: unfreeze before finalizing)

The owner answered question 103: "Yes, unfreeze before finalizing" (`../decisions.md`, "100 to 103, and the toolchain move's place, answered (2026-10-19)"). What changed in this specification:

- **Kept:** option 4, the fresh `__main__` for every program, and a script and `-m` run in it (Decisions 1 to 3, unchanged); it still fixes a script, a directory and `-m` on both binaries.
- **Added:** `run` on the snapshot undoes the freeze before `Py_FinalizeEx`, through a reference to `gc.unfreeze` that `wizer.initialize` takes before the freeze, called as a session's `shutdown` calls it (Decision 4). `recipes/reactor_main.c` joins the Kind.
- **Sessions:** unchanged, and the freeze is undone at most once per instance (Decision 5).
- **Check D's gap closes:** D is a passing check on both binaries, with the patched class, the module attribute and a tampered `gc.unfreeze` (Decisions 6 and 7). No gap entry is added.
- **Check (b) is restated** from 8 to 3, with question 103's answer as the reason (Decisions 4 and 7); the lane accepts with `--accept-judge` and `--accept-growth`, the growth being the measured +28 M per snapshot `run` from finalizing the unfrozen heap (Decision 8).
- **The README:** the corner paragraph is not written; the snapshot's start cost is updated, and one sentence tells a metered `run` to size its `fuel` for the finalization (Design; the confirmation's A1).
- **Question 103** is gone from `../questions-for-the-owner.md` (main removed it); this specification points at `../decisions.md`.

**The fuel, re-measured for the combined design** (EXECUTED, `probe_combined.out`, against `build/sets/s-c50ca51fae5eb55b-c9dcb5b8`, one run each through the judge's driver). The probe runs the same private wrapper on both sides; the control runs the program in the frozen `__main__` with no unfreeze (today), the combined case in a fresh `__main__` and then, on the snapshot, `gc.unfreeze()`, before `Py_FinalizeEx`.

| program | binary | control fuel | combined fuel | combined − control | bytes kept: control → combined |
|---|---|---|---|---|---|
| bare (`pass`) | snapshot | 16,564,773 | 45,306,285 | +28,741,512 | – |
| bare (`pass`) | plain | 168,364,621 | 168,908,506 | +543,885 | – |
| the gap | snapshot | 17,057,309 | 45,836,593 | +28,779,284 | 0 → 100 |
| the gap | plain | 168,910,047 | 169,451,608 | +541,561 | 100 → 100 |
| the patched class | snapshot | 16,547,313 | 46,141,921 | +29,594,608 | 0 → 100 |
| the module attribute (`json.log`) | snapshot | 16,930,358 | 45,747,665 | +28,817,307 | 0 → 100 |
| a `ZipFile` left open | snapshot | 127,373,492 | 156,015,979 | +28,642,487 | unreadable → readable |
| `import pandas` | snapshot | 4,600,953,414 | 4,646,788,801 | +45,835,387 | – |
| `import pandas` | plain | 4,917,725,856 | 4,918,427,916 | +702,060 | – |

The plain binary keeps every file in both columns (`probe_combined.out`). The combined column's fresh `__main__` here is the wrapper's, whose compile costs about +0.53 M (`probe_fresh_cost.out`); the bootstrap's own costs +10,904 on the snapshot and +29,676 on plain (the review's `cases5.out`). So the unfreeze's own share is the combined run less the fresh-only run through the same wrapper (`probe_combined.out` against `probe_fresh_cost.out`): **+28,208,378** on a bare snapshot run, **+28,201,952** on the gap's, and **+45,192,576** after `import pandas`.

Projected for the built set (today's accepted-style counts plus the bootstrap's fresh `__main__` and the unfreeze's share):

| row | today | projected | change |
|---|---|---|---|
| bare, snapshot (check (b)'s measured run) | 15,631,800 | 43,851,082 | +28,219,282 (×2.81) |
| bare, plain | 167,476,282 | 167,505,958 | +29,676 |
| check (b)'s factor | 10.71 | **3.82** | restated from 8 to 3 |
| the gap, snapshot | 16,185,307 (0 bytes) | 44,450,177 (100 bytes) | +28,264,870 |
| `import pandas`, snapshot | 4,600,110,254 | 4,646,591,716 | +46,481,462 (+1.0%) |

These agree with option 1's direct measurement (`probe.out`: `-c pass` with `gc.unfreeze()` appended, 43,851,798). The builder measures the real rows on the built set (criteria 3 and 4).

### The confirmation of the amendment

The same reviewer confirmed the amendment "once A1 is written in", with A2 in the same pass (its section at the end of `../reviews/073-run-keeps-an-unclosed-files-bytes-spec-2026-10-19.md`, written in the lane's scratchpad with `cases9.py` and `meter.py`, to be copied by the lane). Its measurement agrees with this amendment's within 0.4% bare and 1.5% after pandas (+28,330,759 and +44.52 M), and gives check (b) about 3.81 on a fresh copy of the set.

- **A1 (Low-Medium) — written in.** Decision 4 says a metered `run` now pays the finalization after its program, with the simulated `print('hello')` at 40 M; the README gains a sentence on sizing `run`'s `fuel` and the CHANGELOG bullet says it. `run`'s default fuel is `None`, and no default, README example or check in `src/` or `tests/` has a cap the +28 M would break (Decision 4 lists the caps), so no check row is added. How an out-of-fuel finalization is reported is unchanged; no open point is raised.
- **A2 (Low) — written in.** Decision 4's margin "is expected to widen", naming the zip directory's share of the unfreeze (about 0.36 M across 2,658 members).
- **D's digest today** with its three findings, `cfb1afda1a48`, is in Decision 7 and criterion 1.
- **N1 (no action required) — noted for the builder.** It may use `show_and_drop` instead of `PyErr_Print` on `run`'s error path, as 055 did for `turn`.

### Landed in wave 02

- Every snapshot run unfreezes before finalizing: about +33 M to +34.5 M per snapshot run on the wave (+28 M of it 073's, the rest tier A's start and a slightly larger frozen heap), and the hard-exit row unchanged, as the mechanism says. **Correction to the accept text (the integration review's M1):** its numpy-core clause named a +4.48 G layout term; on this wave numpy-core grew +0.39 G (039's scans and 073's unfreeze), and the layout term is spec 091's separate fact string-comparisons, now 63.54 G. The snapshot's +739,926 bytes run about 15 K past the claims' sum: both snapshots hit wizer's cap of 10,000 data segments, where segments merge by heap layout. **The integration review's M2:** 073 had no release-workflow run of its own; under the owner's fix-forward rule (2026-10-19, `decisions.md`) the wave's dry run is its read, and a red line in its rows is fixed in the next wave.
- Reviews: `../reviews/073-*` and the wave's integration review. The lane's accept flags are in the history line's reasons, each prefixed by its number.
