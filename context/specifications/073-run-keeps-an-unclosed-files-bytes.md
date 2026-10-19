# 073 — `run` keeps an unclosed file's buffered bytes

- **Status:** **drafted 2026-10-19** on `spec/073-run-keeps-unclosed-files-bytes` from main
  `08de0c8`. It changes the build recipe (`recipes/reactor_bootstrap.py`, compiled into both
  binaries at step 60), so it is reviewed once before it is built (constitution §5.6). It changes
  neither the guest's imports nor its exports. A different agent reviews the build.
- **Date:** 2026-10-19
- **Owner:** Clay Gendron
- **Kind:** **build-class** (§5.7): it changes `recipes/reactor_bootstrap.py` (the module
  `_reactor`: `run` gives every program a fresh `__main__`, and runs a script and `-m` in it). It
  touches no `scripts/`, no `downloads/SHA256SUMS`, no patch, no pin and no workflow. It is also a
  judge change: three checks added and one docstring edited in
  `tests/checks/test_v1_4_embedding.py`; one gap entry removed and one added in
  `tests/known_gaps.toml` (Decision 7). It changes `README.md` (the snapshot's facts) and
  `CHANGELOG.md` (0.1.0a7). It changes no public name, signature, field, default or option:
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
  `Lib/runpy.py`, from the pinned tarball in the main tree's `build/Python-3.15.0` (READ).

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
| 4. a fresh, unfrozen `__main__` per program | ≤ 16,164,934 (≤ +0.53 M) | ≤ 16,762,639 (100) | ≤ +0.42 M | ≤ +0.54 M | ≥ 10.36 |

Sources: `probe.out` (options 1 and 2, and option 4's whole wrapper), `probe_fresh_cost.out`
(option 4's own cost, against a control running the same wrapper in the frozen `__main__`; it is
an upper bound, since the wrapper compiles four more lines than the bootstrap will run).

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
   on both binaries, for about half a million instructions. It **does not restate (b)**: the
   factor stays above 10. Run a script and `-m` in that same `__main__`, as CPython's own entry
   points do, and they keep their bytes too (`probe_in_main.out`: 100 on both binaries, for
   +2.1 M and +0.5 M with the wrapper's compile included).

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
     import path's prelude).
   - **Both binaries.** The plain binary's `__main__` is not frozen, but one code path is simpler
     to state and to check, and a fresh module costs it the same half million
     (`probe_fresh_cost.out`).
   - **The prelude.** Under an import path, the runner's prelude (`_import_prelude`) is a `-c`
     program that calls `_reactor.run` again. The outer call makes a fresh `__main__`, the prelude
     binds no name in it, and the inner call makes another for the caller's program. The names
     come from the capture, not from the current `__main__`, so nesting cannot leak names.
   - *Why:* it is the only measured option that keeps the gap's bytes without restating (b), and
     it gives the snapshot the plain binary's teardown for everything a program keeps in
     `__main__`. The old, frozen `__main__` is dropped from `sys.modules`; nothing else holds it, so
     reference counting frees it.

2. **A script runs in `__main__`, with the globals runpy gives it today.**
   - For a target that is a file (`pkgutil.get_importer(target)` is `None`, runpy's own test):
     `code = runpy._get_code_from_file(target, "__main__")`, then
     `runpy._run_code(code, main.__dict__, None, "__main__", None, "", target)`. These are the two
     calls `runpy.run_path` makes, with `__main__`'s dict in place of a temporary module's.
   - For a directory or a zip: `sys.path.insert(0, target)`, then
     `runpy._run_module_as_main("__main__", alter_argv=False)`. This is CPython's own path for
     such a target (`Modules/main.c`: `pymain_sys_path_add_path0`, then
     `pymain_run_module(L"__main__", 0)`).
   - The program's globals are what `run_path` gives it today: for a file (`probe_globals.out`),
     `__name__` `"__main__"`, `__file__` the target, `__package__` `""`, `__spec__` and
     `__loader__` `None`; for a directory (`probe_dir.out`), `__file__` its `__main__.py`,
     `__spec__` named `__main__`, `__loader__` a `SourceFileLoader`, since `run_path` and
     `_run_module_as_main` both find it with `_get_main_module_details`.
     One value changes: `__builtins__` becomes the builtins module, as in `-c` and as native
     CPython gives `__main__`, where today `exec` into a temporary module inserts its dict.
   - The "can't open file" message is unchanged: the `OSError` still rises from runpy's frames
     (`_get_code_from_file`), which `_only_runpy` checks. Tracebacks are unchanged: `_report`
     still strips runpy's frames for a script.
   - *Why runpy's private helpers:* the pinned stdlib zip carries a fixed `runpy`, and CPython's
     own `-m` calls `runpy._run_module_as_main`, so these helpers are what the interpreter itself
     relies on. Check C pins the globals, so a CPython upgrade that changes them is caught.

3. **`-m` runs as CPython's own `-m` does: `runpy._run_module_as_main(target)`.**
   - It runs the module in `__main__`'s dict and sets `sys.argv[0]` to the module's file, as
     `run_module(..., alter_sys=True)` did during the call (spec 054's check:
     `['/code/pkg/__main__.py', 'x', 'y']`).
   - Its globals are today's (`__spec__` the module's spec, `__loader__` its loader, `__file__` its
     origin), except `__builtins__`, as for a script.
   - A module that cannot be found now ends as native's does: `_run_module_as_main` calls
     `sys.exit(f"{sys.executable}: No module named prog")` (READ, `Lib/runpy.py`), and the guest's
     `sys.executable` is `/usr/local/bin/python.wasm` (`probe_runner.out`), so `run` prints that
     line and returns 1 (`_exit_code`). Today it prints an `ImportError` traceback. No check pins
     today's form (`grep` of `tests/`); the builder records the new line in the Landing notes.

4. **The freeze stays, and check (b) is not restated.** `wizer.initialize` keeps
   `gc.collect(); gc.freeze()`, and `START_FACTOR` stays 8. The builder records (b)'s factor on the
   built set; it must be at least 10 (today 10.71; 10.36 with option 4's measured upper bound).

5. **Sessions are unchanged.** A session's turns run in the `__main__` they find, and its close
   keeps 055's `gc.unfreeze()` before `Py_FinalizeEx`, which also covers the residual. A fresh
   `__main__` for sessions would not let the close drop the unfreeze, because of the residual, so
   it is not in scope.

6. **The residual is checked, documented and asked, not fixed here.**
   - Check D holds the patched-class shape on both binaries. `[plain]` passes. `[snapshot]` fails,
     and a gap entry allows exactly that failure, naming question 103 as its closer (Decision 7).
   - The README's snapshot facts gain one: an object a program hangs on a module or class the
     snapshot pre-imported is never finalized, so close files with `with`.
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
     asserts `True`, `True`, today's names and values per mode (`probe_globals.out`,
     `probe_dir.out`), with `__builtins__` a `module` in every mode. Today it fails on the
     snapshot's `-c` and stdin (frozen) and on both binaries' script, directory and `-m`
     (`__builtins__` a `dict`).
   - **D, new: `test_run_keeps_a_file_a_patched_stdlib_class_reaches`** (`@BINARY`, through the
     `guest` fixture, recording fuel). The program: `import json`, open `/out.txt`, write 100
     bytes, define `default(self, o)`, set `json.JSONEncoder.default = default`. It asserts 100
     bytes, and reports a shortfall as `"<binary>: a file reached from a patched stdlib class kept
     <n> of 100 bytes"` through `scan.report(findings, "frozen heap")`. `[plain]` passes today and
     after. `[snapshot]` fails today and after with `frozen heap: 1 finding(s), digest
     049b78ef7b5a: snapshot: a file reached from a patched stdlib class kept 0 of 100 bytes`
     (computed with `scan.report`).
   - **The gap entry for D`[snapshot]`, new:**
     ```toml
     [[gap]]
     check = "tests/checks/test_v1_4_embedding.py::test_run_keeps_a_file_a_patched_stdlib_class_reaches[snapshot]"
     match = "1 finding(s), digest 049b78ef7b5a"
     reason = "on the snapshot, an object a program hangs on a pre-imported module or class is reached from the frozen heap and never finalized, so a file it reaches loses its buffered bytes (spec 073, Decision 6)"
     closes_with = "context/questions-for-the-owner.md"
     ```
   - No golden output, upstream allowance or harness constant changes. `START_FACTOR` stays 8.

8. **The fuel moves, and how the lane accepts it.** Every check that runs a program on either
   binary pays the fresh `__main__`, about 0.1 M to 0.6 M (the build measures it), so most fuel
   rows grow past the tolerance of one part in ten thousand. Script and `-m` rows also lose
   runpy's temporary module, and may fall. The builder lists the rows that moved, their largest
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
    - **083** (drafted in `../wasi_python-083`; the judge's driver answers file times and inode
      numbers): both add checks to `tests/checks/test_v1_4_embedding.py`, at different places, so
      the merge is textual. Both restate fuel; whichever lands second takes main's progress files
      and accepts again, as AGENTS.md rule 6a says. Check D and (h) write a file through the
      driver, so their fuel depends on the file's time and inode number until 083 lands (083
      measured that spread at 102 instructions at most, within every row's tolerance); after 083,
      it is fixed.
    - **081** (guest fuel independent of the checkout path; its guard refuses a measured run whose
      inputs name a host path): check D and (h) pass guest paths only (`/out.txt`), and A and C
      record no fuel. No textual overlap: 081 edits `tests/harness/guest.py`,
      `tests/checks/conftest.py` and the lxml check.
    - **065** (CPython's own tests in the release): it runs its tests through the guest; a
      script's and `-m`'s namespace move from a temporary module to `__main__`, as natively. If
      065 lands first, 073's build runs its groups in the full judge, and any change in them is
      named in the Landing notes.
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
    tests `pkgutil.get_importer(target)` and takes Decision 2's two paths. The module docstring
    gains one sentence on the fresh `__main__`.
- `tests/checks/test_v1_4_embedding.py`: (h)'s docstring; checks A, C and D (Decision 7), beside
  (h).
- `tests/known_gaps.toml`: (h)'s entry and its comment removed; D's entry added with a comment
  naming this specification and question 103.
- `README.md`, the snapshot's facts after "`run` treats its arguments as CPython's command line
  does": every program runs in a fresh `__main__`, and a script and `-m` run in it as CPython's
  own entry points run them; a fourth snapshot fact, the residual and its advice ("close files
  with `with`").
- `CHANGELOG.md`, 0.1.0a7: one **Fixed** bullet (the snapshot's unclosed files, and a script's
  and `-m`'s on both binaries; `-m`'s not-found message is CPython's; `__builtins__` a module);
  and spec 069's bullet loses "Known and unchanged: `run` on the snapshot loses …".
- `context/roadmap.md`: 073's paragraph says drafted, then built, then landed, as it goes.

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
   binaries' script, directory and `-m`; D`[plain]` passes and D`[snapshot]` fails with digest
   `049b78ef7b5a`; (h)`[snapshot]` fails with digest `7da6e52329c1`.
2. **After the build, the gap closes.** (h)`[snapshot]` passes, its gap entry is gone, and the
   scoreboard shows one gap fewer from it. A and C pass on both binaries. D`[plain]` passes;
   D`[snapshot]` fails with exactly its gap entry's digest.
3. **What must not move.** `test_main_starts_as_native` (both binaries) and
   `test_the_import_path_reaches_every_mode` (both binaries; its stack depths 2 and 4, its `-m`
   argv, its script's exit code 3) pass unchanged. Check (b) passes with `START_FACTOR` 8, and its
   factor on the built set is at least 10; the Landing notes record both counts.
4. **The fresh `__main__`'s cost, counted.** The snapshot's `-c pass` fuel on the built set
   against main's accepted row for check (b): the rise is at most 0.6 M instructions. The Landing
   notes give the number and the command.
5. **Stand-ins.** Each fails what it names:
   - **S1**, the fresh `__main__` made but `-c` and stdin still `exec` in the old one: A (the
     snapshot's `-c` and stdin rows), C and (h)`[snapshot]` fail.
   - **S2**, the script branch left on `runpy.run_path`: A's and C's script and directory rows
     fail.
   - **S3**, the `-m` branch left on `runpy.run_module`: A's and C's `-m` rows fail.
   - **S4**, the fresh `__main__` without `__builtins__` and `__loader__`:
     `test_main_starts_as_native` fails.
   - **S5**, the script branch's `__package__` given as `None`: C's script row fails.
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
rise (criterion 4); the rows that moved (Decision 8); `-m`'s new not-found line; the fast tier and
the full judge's last lines; and the lines for the lane (`--accept-judge`, `--accept-growth`).
