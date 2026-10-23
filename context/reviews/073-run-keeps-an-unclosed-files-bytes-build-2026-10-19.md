# Review of 073 — `run` keeps an unclosed file's buffered bytes (the build)

- **Date:** 2026-10-19
- **Reviewer:** a fresh agent (Claude Opus 5.5). I reviewed the spec before build, its revision, and its amendment for question 103. I wrote none of its code.
- **Reviewed:** `spec/073-run-keeps-unclosed-files-bytes` at `16392cf`, on main `2737b29`. Its commits are `b4153b5` (the checks), `e7f0fcf` (the recipe, the judge's changes, README and CHANGELOG) and `16392cf` (the landing notes). I read `git diff 2737b29 16392cf`: both recipes, the three test files, `known_gaps.toml`, README, CHANGELOG, the landing notes and the builder's `build_growth`/`build_measure` evidence.
- **The built set:** `build/artifacts`, whose SHA256SUMS hashes to `82365b44…` as stated. The two binaries differ from main's set, and the zip is the same. Comparisons used a fresh `cp -Rp` of main's set `s-c50ca51fae5eb55b-c9dcb5b8` (`../set/`; its zip has 1 link, the original 554).
- **Ran (EXECUTED, macOS arm64, wasmtime-py 49.0.0).** All evidence is in `build-review/` beside this file. I wrote nothing to a git tree. The judge writes `build/progress/latest.json` in the worktree (git-ignored); I saved the builder's copy as `builder-latest.json` first and put it back afterwards. Their full record stays in `build/073/latest-full2.json`.
  - **The fast tier:** `uv run pytest -m "not slow" -n 3` (`fast.log`, `reviewer-fast-latest.json`). Result: 508/562 pass, 0 gap, 3 blocked, 0 fail; lost 0, gained 9, grew 131; 2012 passed and 10 skipped. This is the builder's verdict. No unraisable warning this time.
  - **The full judge:** `uv run pytest -n 3` (`full.log`, `reviewer-full-latest.json`, the record for the lane's sameness step). Result: 545/562 pass, 14 gap, 3 blocked, 0 fail; lost 0, gained 9, grew 151; red only for growth; 2049 passed, 10 skipped and 14 xfailed in 620 s.
  - **Sameness:** `tests/harness/sameness.py build/073/latest-full2.json reviewer-full-latest.json` exits 0, with no differences.
  - The probes are `cases10` to `cases14` and `profdiff`, each a `.py` with its `.out`, listed under the findings.

## What holds

1. **The code is the confirmed design, kept small (READ).**
   - `reactor_bootstrap.py`:
     - `_MAIN_NAMES` is captured at import.
     - `_fresh_main()` is now inside `run`'s `try` (the review's note).
     - `_run_file()` follows `_PyRun_SimpleFile`: it sets `__file__` and a `SourceFileLoader`, or a `SourcelessFileLoader` for `.pyc`, runs `exec`, and pops `__file__` in a `finally`.
     - `-m` runs through `_run_module_as_main(target)`. A directory or zip goes through `sys.path.insert(0, target)` and then `_run_module_as_main("__main__", alter_argv=False)`.
   - `reactor_main.c`:
     - `wizer_initialize` takes `unfreeze_function` before the freeze, and aborts the build if it cannot.
     - `run` calls it after the bootstrap and before `Py_FinalizeEx`, uses `show_and_drop` on an error, then clears it. The plain binary takes nothing.
   - **The `_only_runpy` amendment is needed and safe.** `_run_file` adds a `<reactor>` frame before runpy's `_get_code_from_file`. Skipping only *leading* `<reactor>` frames keeps a user's own `OSError` reported as a traceback, because the user's frame is not runpy's.
2. **A program cannot defeat the unfreeze (READ, and EXECUTED by check D).**
   - The reference is a C static taken at build time, so no Python code can reach it.
   - D's tampered row (`gc.unfreeze = lambda: None`) passes on the built snapshot.
   - A program calling `gc.freeze()` before it ends is undone too, since the merge takes the whole permanent generation.
   - One way remains: an `atexit` handler that calls `gc.freeze()` re-freezes everything after the unfreeze. Native CPython loses the bytes the same way, so this is parity.
   - `run` and `turn`/`shutdown` exclude each other, so the unfreeze runs at most once per instance.
3. **The checks hold the design.**
   - All of these pass on both binaries in my full run: A, C, D and E; (h) without its gap; check (b) at 43,745,970 fuel (factor 3.831); `test_main_starts_as_native` and `test_the_import_path_reaches_every_mode`.
   - D's digest on main (`cfb1afda1a48`) is the confirmation's.
   - The stand-ins' evidence (`build_standins.out`) matches criterion 5. S1 fails more checks than named, which the notes explain correctly.
4. **Sessions are unchanged (EXECUTED).**
   - `tests/checks/test_v1_4_sessions.py` is not in the diff.
   - All 39 of its checks pass in my full run.
   - None of its fuel rows moved from `accepted.json`.
5. **Criterion 4 (EXECUTED, `cases14.out`).** The built snapshot's `-c pass` is 43,745,970, a rise of +28,114,170 over main's 15,631,800. That is inside +27.7 M to +28.8 M. The plain rise is +97,840, under 0.1 M.
6. **README and CHANGELOG.**
   - A1 is written in: the `fuel` sentence says a capped snapshot call ends "out of fuel", with `exit_code None`, after its output was written.
   - The four snapshot facts, the *Measured* rows and the 0.1.0a8 Fixed and Changed bullets are right.
   - Not editing the released 0.1.0a7 section is right.
7. **The unraisable `KeyboardInterrupt` is not 073's (EXECUTED: grep of earlier logs).**
   - The traceback is host-side: wasmtime-py's `Store.__del__` running in a pytest worker while a Ctrl-C check's `KeyboardInterrupt` arrives. Guest code cannot raise in the host's Python.
   - The same warning, with the same `KeyboardInterrupt`, appears in runs that predate 073's code: `build/reviews-evidence/061-buildreview/fast.log` (2026-10-18), `063-build4/full-n3.log`, `063-build6/fast-n3.log`, and 065's `fast-065d.log`.
   - It did not appear in either of my runs.

## Findings, most severe first

### B1 (Medium, EXECUTED): `_run_file`'s `from importlib.machinery import …` imports `warnings` in every script run, about +10 M fuel, and the landing notes give this growth the wrong reason

- **What triggers it.** `from importlib.machinery import SourceFileLoader, SourcelessFileLoader` makes `__import__` probe `hasattr(module, "__path__")`. `importlib.machinery` has a module `__getattr__` that runs `import warnings` before anything else, for its deprecated names. So the probe imports `warnings` and `_py_warnings` from the zip.
- **The stack I traced:** `importlib.machinery.__getattr__:36 ← <string> ← <reactor>:run` (`profdiff2.out`, and the `IMPORT` trace in my run).
- **Measured (`cases14.out`, the built set), a `pass` script with the same steps:**

  | binary | loaders from `_frozen_importlib_external` | the same with `from importlib.machinery import …` | difference |
  |---|---|---|---|
  | plain | 238,419,247 | 248,436,646 | +10.0 M |
  | snapshot | 65,639,400 | 75,628,526 | +10.0 M |

- **The regex job (plain), run three ways (`cases12.out`):**

  | run | fuel |
  |---|---|
  | main's set, direct | 603,192,551 |
  | built set, direct | 613,073,347 |
  | built set, `-c` wrapper running it in `__main__` | 604,477,099 |
  | built set, the same wrapper plus `from importlib.machinery …` | 614,790,945 |

  So the regex row's +9,880,830, the largest plain rise, is this import. It is not "`__main__` now living until finalization", the reason the landing notes and the planned `--accept-growth` line give (rule 5: a growth reason must be measured). My earlier prototype never showed it, because it used `import importlib.machinery as _m`, which makes no `__path__` probe.
- **It is not native.** A native 3.15.0 script starts without `warnings` or `_py_warnings` in `sys.modules`. The built `run` gives every script both (`cases14.out`: `True True`; native, `False False`).
- **Fix (one line):** take the loaders from `_frozen_importlib_external`, which is always in `sys.modules` and is where CPython's `set_main_loader` gets them (`_PyImport_GetImportlibExternalLoader`). For example: `import _frozen_importlib_external as _bx`, then `_bx.SourceFileLoader` and `_bx.SourcelessFileLoader`.
- **Then:**
  - rebuild;
  - re-run C and the script checks;
  - re-take the growth list;
  - correct the plain-rows sentence and the `--accept-growth` line.

  The other script rows (numpy and pandas jobs, upstream drivers) import `warnings` anyway, so only scripts that do not are affected.

### B2 (Low, EXECUTED): the heavy-import growth is the unfreeze, as the notes say; I measured it, and the README's "about 46 M after pandas" undersells the top rows

- On main's set, appending `gc.unfreeze()` to the program (the same point where the built `run` unfreezes) costs:
  - `-c pass`: +28,232,809;
  - `import pandas`: +43,990,624;
  - the ctypes stand-in check's program: +69,817,235 of its +71,913,024 (`cases10.out`);
  - lxml's encodings program: +69,506,555 of its +88,060,237 (`cases11.out`).
- The rest of the encodings row is INFERRED: the fresh `__main__` now frees program globals that the frozen `__main__` used to leak.
- The mechanism: the counts each shutdown collection reports are the same with and without the unfreeze (`cases10.out`, the `[gen:collected]` lines). So the extra fuel is the teardown walking the unfrozen bootstrap heap and freeing what its caches and module cycles held of the program's imports. Before the change, that was left unfreed at exit.
- The `--accept-growth` wording ("more after large imports, up to +88 M") is right. It could cite these numbers.
- The README's `fuel` sentence says "about 28M more (about 46M after `import pandas`)". "More after large imports, up to about 90M" would keep a metered embedder from under-sizing.

### B3 (Low, INFERRED): the plain bare rise's stated reason is imprecise

- The notes put +97,840 (against a projected +29,676) down to "`_MAIN_NAMES` captured at import". Copying six names costs a few hundred instructions.
- The likelier reason: on the plain binary the bootstrap is unmarshalled and run on every call, and it grew by two functions and a docstring paragraph.
- It is inside criterion 4's bound. Reword the reason or say it was not measured.

### B4 (Note, EXECUTED): the upstream moves are real, small, and in both directions

- My full run matches the builder's for every upstream group within 30 K, for example pandas-groupby −599,782,857 against −599,813,100. So the moves are reproducible, not noise.
- They run from −0.14% to +0.27% of each group.
- Falls need no acceptance. The rises are covered by B2's reason.
- I did not establish why pandas-groupby falls by 0.6 G. INFERRED: allocation and collection timing shift over a 480 G run (and B1's earlier `warnings` import changes the import order a little).
- No upstream outcome moved: 20 groups pass and 12 gaps keep their digests, in both runs.

## Verdict

**Lands once B1 is fixed and rebuilt.**
- B1: load the file loaders from `_frozen_importlib_external`, not `from importlib.machinery import …`.
- Re-take the growth list, and correct the plain-rows growth reason in the landing notes and in the `--accept-growth` line.
- Write in the README's heavy-import fuel sentence (B2) and B3's wording at the same pass.
- The delta is one line of `recipes/reactor_bootstrap.py`. A delta look at that hunk, with C, A, E and the regex row re-run, is enough. Everything else holds:
  - the recipe change, which no program can defeat;
  - the checks;
  - sessions, unchanged;
  - criterion 4 and check (b) at 3.831;
  - sameness between the builder's record and mine.

## One line

The build is the confirmed design and passes the full judge identically twice. But a `from importlib.machinery import` in `_run_file` imports `warnings` in every script run, about +10 M fuel and not native. That is the real cause of the largest plain rise, which the notes attribute to something else. Lands once that line is fixed and the growth re-taken.

## Addendum: the delta look at B1's fix and the rebuild

- **Reviewed:** `e1bd770` on main `a6dfc17`. The B1 fix is `2ecab3a`. The rebuilt set's SHA256SUMS hashes to `8a30505a…`, and its zip is main's. The owner's pause killed my first judge reruns; I ran them again.
- **Evidence:** in `delta/` beside this file. `nc.py` stages `/upstream` exactly as the judge's `Session` does, then runs numpy-core in the snapshot under variants. Its `.json` and `.log` files hold every run. `perfile.sh` and the `perpart*.sh` scripts bisect the group. `cases15.py` to `cases19.py` are the standalone probes, each with its `.out`.

### The B1 hunk (READ, EXECUTED)

- `_run_file` now takes `SourceFileLoader` and `SourcelessFileLoader` from `_frozen_importlib_external`, where CPython's `set_main_loader` gets them. Nothing else in the recipe moved.
- Check C's new row asserts that every mode starts with `warnings` and `_py_warnings` absent from `sys.modules`, as native 3.15.0 does. It fails on the first build's script rows, per the builder's `c-b1-before.log`. It passes in my run.
- The regex row's +9.88 M is gone. The builder measured −60,720.
- B2 and B3 are written in.
- **The fast tier, my run** (`uv run pytest -m "not slow" -n 3`, `delta/fast.log`, `delta/reviewer-fast-latest.json`): 508/562 pass, 0 fail; lost 0, gained 9, grew 119.
- **Check C and numpy-core, my run** (`delta/targeted.log`, `delta/reviewer-targeted-latest.json`): both pass. numpy-core's fuel is 207,839,613,587, against the builder's 207,839,613,706.
- I put the builder's `build/progress/latest.json` back afterwards.

### numpy-core's +4.48 G: located and measured

**What it is not (EXECUTED, `delta/*.json`).** Every run below is numpy-core on the snapshot, and every one has the same outcomes: 9,519 passed, 40 failed, 3 errors, 668 modules. Every instrumented run also has the same `gc.get_stats()`: 499, 44 and 11 collections per generation, with the same collected counts.

| run | fuel |
|---|---|
| main's set, the judge's own `drive.py` | 203,355,548,118 |
| main's set, a fresh `__main__` made by hand | 203,287,156,810 |
| main's set, padded with 4 KiB, 64 KiB or 1 MiB first | 203.22 G to 203.28 G |
| rebuilt set, `drive.py` as `run` now runs it | 207,839,613,706 |
| rebuilt set, through the old `runpy.run_path` | 207,576,790,307 |
| rebuilt set, in `__main__` with `__loader__` `None` | 207,545,652,817 |
| rebuilt set, `warnings` imported first (the first build's order) | 207,754,857,401 |

So the rise does not come from any of these:
- the script path, `__main__`'s globals or the order of the `warnings` import: every way of running `drive.py` on the rebuilt set costs about 207.6 G;
- the fresh `__main__`: one made by hand on main's set costs the baseline;
- the run-time heap layout: padding on main's set moves 60 M at most;
- collector work: the statistics are the same in every run;
- the unfreeze: the builder's S6 stand-in, without it, costs 207.80 G.

It is a property of the rebuilt binary.

**Where it is (EXECUTED).** I bisected by file and then by test:

| step | main's set | rebuilt set | difference |
|---|---|---|---|
| quarter q2 (9 of the 41 files) | 90.79 G | 95.12 G | +4.33 G |
| each of the other three quarters | | | +34 M to +66 M |
| `test_strings.py`, alone | 74.69 G | 79.00 G | +4.31 G (+5.77%) |
| each other q2 file, alone | | | +45 M to +59 M |
| `test_strings.py`, its classes | | | +62 M |
| `test_strings.py`, its module-level tests | | | +4.29 G |
| `test_string_comparisons`, its 84 cases alone | 61.44 G | 65.73 G | **+4.29 G (+6.99%)** |
| the module-level tests without those 84 cases | | | +49 M |

So 4.29 G of the 4.48 G is one parametrised test. The rest is the unfreeze-sized +30 M to +60 M that every group pays.

**The operation (EXECUTED, `cases17.out` to `cases19.out`).**
- The test's own array work (`astype`, `shuffle`, `tolist`, the ufuncs, `compare_chararrays`), run standalone, costs only the base +29.6 M more on the rebuilt set.
- The difference is in `assert_array_equal`, which turns `expected`, a list of 32,768 Python bools, into an array. On its own:

  | `np.array` of 32,768 elements, per call | main's set | rebuilt set |
  |---|---|---|
  | `bool` (`[True] * 32768`) | 25.8 M | 32.4 M (+25%, about 200 instructions an element) |
  | `int` | 23.07 M | 23.03 M |
  | `float` | 20.64 M | 20.70 M |

  The test makes six such conversions in each of its 84 cases, which accounts for the 4.29 G.

**Why only bool (READ, numpy 2.5.2's `array_coercion.c`, `npy_discover_dtype_from_pytype`).**
- numpy finds each element's DType from `type(element)`.
- `float` and `int` have pointer-equality fast paths. Every other type, `bool` included, is looked up in `_global_pytype_to_type_dict`, a dict keyed by type objects.
- A type hashes by its address.
- `bool`'s static `PyBool_Type` moved from `0x15c5558` to `0x15c5cd8` (+0x780), as every static moved, because the binary's data segment changed size (`cases19.out`, `id(bool)` on both sets).
- So `bool`'s hash, and its probe sequence in that dict, changed.

**The cause, in one sentence.** A link-layout effect: numpy's address-keyed dict lookup, made once per Python bool, costs about 200 instructions more after the static types moved. The measured facts are where the fuel goes, the per-call cost, that only `bool` is affected, and the address shift. The exact probe count is INFERRED.

**What follows.**
- This is not 073's semantics. Any change to the binary's size can flip it either way. The first build's layout, one line different, gave −73.6 M.
- The growth reason for the lane can say so plainly. A sentence in the memo or the landing notes would warn the next build-class spec that numpy-core carries a layout-sensitive term of a few G.

### Verdict

**Lands.**
- B1 is fixed correctly and held by check C's new row.
- B2 and B3 are written in.
- My counted reruns match the builder's.
- numpy-core's +4.48 G now has a measured cause: the layout effect above, with its counts unchanged.

The landing notes and the `--accept-growth` line should replace "its cause in the suite not established" with this cause:

> numpy-core +4.48 G: `test_string_comparisons`' 504 conversions of 32,768-bool lists cost about 25% more, because numpy's per-element `_global_pytype_to_type_dict` lookup is keyed by `bool`'s address, which moved 0x780 with the rebuilt binary's layout; not 073's semantics (the first build gave −73.6 M).

That edit is wording, in `context/` only. It needs no further review.

### One line

B1 is fixed and verified. numpy-core's +4.48 G is a link-layout artifact in numpy's type-keyed lookup for Python bools, concentrated in `test_string_comparisons`. Lands, with that cause written into the growth reason.
