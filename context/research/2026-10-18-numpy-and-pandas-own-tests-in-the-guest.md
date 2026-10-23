# numpy's and pandas' own tests run in the guest, and what they found

- **Status:** executed, 2026-10-18 (a time-boxed prototype in the drafting session's scratch folder; nothing in the repository was changed by it).
- **Corrected 2026-10-18** (spec 050's pre-build review, findings F11 and F13): the drafting first said none of numpy's test folders has an `__init__.py`; only `_core/tests` lacks one. `evidence/prototype/drive.py` is the driver the runs used, copied after them under that name from the scratch folder's `drive4.py`, which `batch2.py` and `hunt.py` name. Nothing else changed.
- **Corrected 2026-10-18** (spec 050's build): "Fuel repeats" holds for one grant. A pandas group's fuel also depends on what else the grant holds: with numpy's tests staged beside pandas', `pandas/tests/tslibs` took 38,949,120,223 instructions and without them 38,961,587,990 (320 parts in a million), and `internals` by 89 parts in a million the other way (EXECUTED; pytest lists the grant's root folder, and the allocations shift the collector's timing, INFERRED). The judge therefore stages both packages in every run. Within one grant, runs repeat to under one part in a million.
- **Owner:** Clay Gendron
- **Researcher:** the drafting agent (Claude Opus 5.5) of spec 050.
- **Feeds:** spec 050 (numpy's and pandas' own tests under the runtime), which judges what this memo found; question 89 in `../questions-for-the-owner.md` (numpy's C test modules); three follow-ups named under "What it decides".
- **Stands on:** `2026-10-16-the-spike-that-proved-the-build.md` ("No test suites ran … The first release gate should run numpy's and pandas' own test subsets"); `2026-10-16-a-principal-engineers-direction.md` ("the upstream test subsets … are the cheapest way to find the next `os.dup`"); `2026-10-17-numpy-npy-files-need-dup.md`; the roadmap, milestone 6.

## How it was run (EXECUTED)

- The frozen artifact set `build/sets/s-0cdc7b2bd78db6f5` (CPython 3.15.0, numpy 2.5.2, pandas 3.0.6, carried patch 0001), copied to the scratch folder. The **snapshot** binary.
- The judge's own driver, `tests/harness/guest.py`, imported from a scratch copy that differs in one line (it keeps the trap's backtrace and cause instead of its first line). Its seeded random, its stepped clock, its fuel meter. Root `/` writable (as in every judge run), one read-only grant at `/t` holding the test kit, the copied test folders and a driver program.
- **The test kit** (pure-Python wheels, each downloaded from PyPI and checked against PyPI's published SHA-256 with `shasum -a 256 -c`, all OK): pytest 9.0.3, pluggy 1.7.0, iniconfig 2.3.1, packaging 26.3, pygments 2.21.0, hypothesis 6.152.1, sortedcontainers 2.4.0. pytest 9.0.3 because pandas 3.0.6 declares `pytest>=8.3.4,<9.1` (READ: its `pyproject.toml`, `test` extra); hypothesis 6.152.1 because numpy 2.5.2 pins it (READ: `requirements/test_requirements.txt`); hypothesis 6.152.1 needs only `sortedcontainers` (READ: PyPI's `requires_dist`). A first pass used the dev group's pytest 9.1.1 without hypothesis.
- **The tests:** every `tests` folder under `build/numpy-2.5.2/numpy` (the patched tree), and `build/pandas-3.0.6/pandas/tests` with `pandas/conftest.py`. The product's zip holds no `tests` folder (`make_stdlib_zip.py` skips them; 0 members, EXECUTED), and numpy's `_core/tests` has no `__init__.py`; the other twelve test folders have one (READ; corrected, see the status).
- **The driver** (`evidence/prototype/drive.py`): puts the kit first on `sys.path`; appends `/t/tests/<pkg path>` to the `__path__` of `numpy`, `numpy._core`, `numpy.lib`, … and of `pandas`, so `numpy._core.tests._locales` and `pandas.tests.extension.base` import from the grant while the packages themselves stay the product's; loads a hypothesis profile with numpy's own "np.test() profile" values (`database=None, derandomize=True, deadline=None`, every health check suppressed); calls `pytest.main` with a plugin that streams one line per test start and per outcome, flushed (`python -u`).
- **Commands:** per file, per directory and per group, through scratch scripts (`evidence/prototype/batch2.py`, `hunt.py`, `probe.py`), all with `uv run` from the repository's root. Outputs and tables are in `evidence/`.

## Findings

### 1. pytest runs in the guest, with six adaptations (EXECUTED)

| option | without it |
|---|---|
| `-p no:faulthandler` | `OSError: [Errno 58] Not supported` before collection: pytest's faulthandler plugin duplicates stderr's descriptor |
| `--capture=sys` | `INTERNALERROR> OSError: [Errno 58] Not supported`: fd capture duplicates descriptors |
| `-o log_file=/tmp/pytest.log` | `FileNotFoundError: … '/dev/null'`: the logging plugin opens `os.devnull`, which WASI has not |
| `--basetemp=/tmp/pytest` | every `tmp_path` test errors with `AttributeError: module 'os' has no attribute 'getuid'` (pytest's `get_user_id` exempts win32 and emscripten, not wasi; READ `_pytest/compat.py:269`) |
| `-p no:cacheprovider` | not tried: the grant is read-only and the cache is not wanted (INFERRED) |
| `--import-mode=importlib` | the default `prepend` also ran `test_abc.py`; importlib avoids `sys.path` changes and the name clash of numpy's six `test_regression.py` files (INFERRED) |

A run's fixed start costs: about 5.9 G fuel for a numpy session without hypothesis, about 9 to 11 G with it, and 11.3 G for a pandas session (pandas' `conftest.py`; `test_flags.py`, 5 tests). numpy's own wasm skips apply by themselves (`IS_WASM`: "fp errors don't work in wasm", "wasm doesn't support asyncio").

### 2. The numbers (EXECUTED; fuel is guest instructions)

| run | passed | failed | error | xfailed | xpassed | skipped | fuel |
|---|---|---|---|---|---|---|---|
| numpy, 143 files one session each, pytest 9.1.1, no hypothesis | 15,206 | 43 | 228 | 20 | 1 | 581 | 1,572 G |
| the same with the kit | 17,069 | 43 | 228 | 21 | 1 | 656 | 2,190 G |
| numpy, three sessions, full mode, kit, `--basetemp` | 20,726 | 31 | 3 | 25 | 1 | 678 | 1,207 G |
| **numpy, three sessions, fast mode (`-m "not slow"`)** | **20,658** | **31** | **3** | **25** | **1** | **663** | **502 G** |
| pandas, 40 directory sessions, full mode | 163,633 | 3,171 | 754 | 764 | 94 | 27,915 | 4,419 G |
| pandas, the same, fast mode (`-m "not slow and not network and not db"`, `--no-strict-data-files`) | 161,274 | 2,487 | 320 | 751 | 94 | 27,950 | 3,922 G |
| **pandas, eight chosen groups, fast mode** | **41,911** | **234** | **0** | **123** | **81** | **2,920** | **1,117 G** |

The fast modes are upstream's own defaults: `numpy.test()` adds `-m "not slow"` (`numpy/_pytesttester.py:164`), `pandas.test()` runs `-m "not slow and not network and not db"` (`pandas/util/_tester.py:43`) (READ). numpy's slow-marked tests (83 in these files, 68 of them passing) cost 705 G of its 1,207 G; pandas' fast mode (with `--no-strict-data-files`) saves only 497 G of 4,419 G.

Per group, fast mode (`evidence/numpy-fast-groups.txt`, `evidence/pandas-chosen-groups.txt`):

| group | passed | fuel |
|---|---|---|
| numpy `_core/tests` (selected files) | 8,568 | 195.8 G |
| numpy `lib/tests` | 4,823 | 131.4 G |
| numpy others (`fft`, `linalg`, `ma`, `matrixlib`, `polynomial`, `random`, `testing`, `tests`) | 7,267 | 174.9 G |
| pandas `frame` | 10,831 | 337.1 G |
| pandas `groupby` | 22,156 | 460.3 G |
| pandas `reshape` | 2,657 | 101.2 G |
| pandas `io/parser` | 3,401 | 85.8 G |
| pandas `io/formats` | 955 | 53.6 G |
| pandas `tslibs` | 590 | 38.6 G |
| pandas `internals` | 258 | 18.1 G |
| pandas `libs` | 1,063 | 22.4 G |

**Fuel repeats.** numpy `lib`, run twice: 131,407,102,123 and 131,407,102,344 (+221); pandas `reshape`: 101,218,193,451 and 101,218,193,519 (+68). Both under 2 parts in 10⁹, far inside the ratchet's 0.01% (EXECUTED).

**Wall-clock (a benchmark fact, arm64 macOS, M-series, one process):** the numpy `lib` group took 25.4 s and pandas `reshape` 30.7 s, each including the snapshot's compile. About 5 G fuel a second, so the 1.62 T of the chosen groups is about six minutes (INFERRED from the two).

### 3. Four numpy C functions trap the guest (EXECUTED; the code READ)

Six numpy test files ended in a wasm trap, `wasm trap: indirect call type mismatch`, which kills the whole guest. A crash hunter (`hunt.py`: run, name the test that started and never reported, deselect it, run again) found the tests; numpy 2.5.2's source names the cause: a C function called through a pointer of a different signature. Native code tolerates that; WebAssembly's `call_indirect` checks the signature and traps.

| C function (numpy 2.5.2) | declared | called as | tests that trap |
|---|---|---|---|
| `_get_castingimpl(module, args)`, `_core/src/multiarray/convert_datatype.c:248` | 2 parameters | `METH_VARARGS \| METH_KEYWORDS` (3), `multiarraymodule.c:4789` | `test_casting_unittests.py` (40 found before the hunt's cap, every `test_simple_cancast`, `test_simple_direct_casts`, …), `test_arraymethod.py` (at collection), `test_stringdtype.py::test_cast_method_names` |
| `array_descr_set(self, arg)`, `_core/src/multiarray/getset.c:388` | 2 | a setter (3: `closure`), `getset.c:787` | `test_records.py::TestRecord::test_assign_dtype_attribute[0-2]`, `test_stringdtype.py::test_view_distinct_instance` |
| `gentype___copy__(self)`, `_core/src/multiarray/scalartypes.c.src:2128` | 1 | `METH_NOARGS` (2), `:2700` | `test_regression.py::TestRegression::test_scalar_copy` |
| `sfloat___reduce__(self)`, `_core/src/umath/_scaled_float_dtype.c:192` | 1 | `METH_NOARGS` (2), `:205` | `test_custom_dtypes.py::TestSFloat::test_np_save_load` |

Frame 0 of each backtrace is CPython's caller: `cfunction_call`, `getset_set`, `method_vectorcall_NOARGS`, `cfunction_vectorcall_NOARGS` (EXECUTED). Plain user code reaches two of them (EXECUTED, snapshot, `-c`):

```
copy.copy(np.float64(1.5))                         trap (indirect call type mismatch)
copy.copy(np.int32(3))                             trap
np.bool_(True).__copy__()                          trap
a = np.zeros(4, np.int32); a.dtype = np.float32    trap
copy.deepcopy({'a': np.float64(1.5)})              works
np.float64(2).copy()                               works
```

The embedder sees a trap, not a Python exception. pandas, in every directory, full mode, hit no trap (EXECUTED).

### 4. pandas' warnings point inside pandas, because the zip's code objects carry relative names (EXECUTED; the cause READ)

2,428 of pandas' 2,487 fast-mode failures (all directories) are one message: `Warning not set with correct stacklevel. File where warning is raised: pandas/core/... != /t/tests/...`. pandas' `find_stack_level` (`pandas/util/_exceptions.py:37`) walks out of frames whose `co_filename` starts with `os.path.dirname(pd.__file__)`. In the guest that directory is `/usr/local/lib/python315.zip/pandas`, but `co_filename` is `pandas/core/frame.py` (EXECUTED), because `scripts/make_stdlib_zip.py`'s `pyc()` compiles each member with its relative name (`compile(source, name, …)`, line 140, READ). So `find_stack_level()` answers 0 (EXECUTED) and every pandas `FutureWarning` or `DeprecationWarning` names a pandas file instead of the caller's line. numpy's `test_suppress_warnings_module` fails for the same reason (it filters by module file). The fix is a recipe change (compile with the name the module is imported under), which changes the zip and the snapshot: a build-class follow-up.

### 5. Carried patch 0001 changes two numpy behaviours (EXECUTED; READ)

With `isfileobj` false on WASI, `np.save` of a `MaskedArray` writes the data without raising `NotImplementedError` (native raises it from `MaskedArray.tofile`): `numpy/ma/tests/test_core.py::TestMaskedArray::test_maskedarray_tofile_raises_notimplementederror` fails with `DID NOT RAISE`. And reading a truncated `.npy` takes the buffer path, whose message is not the one `numpy/lib/tests/test_format.py::test_file_truncated` expects. Both belong in the patch's upstream draft before it is sent.

### 6. What fails for platform reasons already documented (EXECUTED)

| cause | numpy (fast) | pandas (chosen groups) |
|---|---|---|
| no `dup`: `fromfile`/`tofile` on a real file (`OSError` 58) | 8 failed, 3 errors (the file left open is reported at finalization) | — |
| no `mmap` | 5 | 40 |
| no `ctypes` calls (the stand-in raises) | 8 | — |
| no processes (`subprocess`) | 3 | 1 |
| no `/dev/null` | 1 | — |
| numpy's test-only modules are not in the product (`_rational_tests`, `_multiarray_tests`, `numpy.conftest`) | 3 | — |

### 7. What cannot be selected, and why (EXECUTED)

- **numpy's C test modules are not linked** (`scripts/gen_inittab.py:27` leaves out `*_tests` and `_simd`, READ). 23 files fail to import because of them: `_core/tests/` `test_api`, `test_argparse`, `test_array_coercion`, `test_arrayobject`, `test_arrayprint`, `test_conversion_utils`, `test_cpu_dispatcher`, `test_deprecations`, `test_dtype`, `test_extint128`, `test_getlimits`, `test_hashtable`, `test_indexing`, `test_mem_overlap`, `test_multiarray`, `test_multithreading`, `test_nditer`, `test_numeric`, `test_scalarbuffer`, `test_scalarmath`, `test_ufunc`, `test_umath`, and `lib/tests/test_stride_tricks`; two more need `_simd` (`test_simd`, `test_simd_module`). These are the heart of numpy's core suite; question 89 asks whether to reach them.
- `test_memmap.py` (every test needs `mmap`), `tests/test_ctypeslib.py` (it reads `_multiarray_umath.__file__`, which a builtin module has not), `f2py`, `typing` (mypy) and `_pyinstaller`.
- pandas' sdist ships no `pandas/tests/io/data` (0 members, READ `tar tzf`), so data-file tests error unless `--no-strict-data-files` (pandas' own switch, `conftest.py:106`) turns them into skips. `io/pytables` stops at its `conftest.py` (`importorskip("tables")`); `io/test_clipboard.py`'s 320 errors are its Qt fixtures.

## What it decides

- The judge can run the upstream suites in the guest with no change to the artifact set: pytest and hypothesis are pure Python, the tests come from the pinned source trees, and the packages' test folders join the product's packages through `__path__`. Spec 050.
- Upstream's fast modes, grouped, cost 0.5 T (numpy) and 3.9 T (all of pandas) fuel; a product-centred pandas subset of eight groups costs 1.1 T. Fuel repeats run to run.
- Three follow-ups, each its own specification: a carried patch for the four C signatures (§4.1; upstream will take it, as these are undefined behaviour in C); the zip's code objects named as they are imported (a recipe change, build-class); patch 0001's draft amended for the two behaviours of finding 5.
- Reaching numpy's C test modules is the owner's (question 89).

## One line

pytest runs in the guest; 62,569 of numpy's and pandas' own tests pass there in 1.6 T fuel, and on the way they found four numpy functions that trap the guest and a zip naming fault that points every pandas warning at pandas.
