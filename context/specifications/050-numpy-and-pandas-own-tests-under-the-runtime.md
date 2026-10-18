# 050 — numpy's and pandas' own tests under the runtime

- **Status:** drafted 2026-10-18. It changes the judge's design (a second, stricter way to admit
  known failures, and a metric that must not fall), so it asks for a pre-build design review,
  though §5.6 does not require one: it changes no import, export, artifact or build recipe.
- **Owner:** Clay Gendron
- **Kind:** the judge only. New: `tests/upstream/` (the guest-side driver, the two packages'
  configuration, the selections and expectations, the test kit's pins and its fetcher),
  `tests/harness/upstream.py`, `tests/checks/test_v1_3_upstream_suites.py`,
  `tests/unit/test_upstream.py`. Changed: `tests/harness/needs.py` (one need),
  `tests/harness/plugin.py` and `tests/harness/scoreboard.py` (the `passes` metric),
  `tests/harness/guest.py` (the trap's cause kept), the scoreboard's "not machine-checked" line,
  `context/progress/README.md`, `README.md`, `CHANGELOG.md`, and the research memo it stands on.
  **Not build-class:** it touches no `scripts/`, `recipes/`, `downloads/SHA256SUMS` or release
  workflow, and rebuilds nothing (Decision 16).
- **Depends on:** landed specs only. 002 (the harness: checks, gaps, needs, the ratchet, the
  findings phrase), 020 (each source tree equals its pinned tarball plus the recorded patches;
  the tests are read from those trees), 021 (the patched numpy tree, whose own test of the patch
  now runs here too), 017 (read-only grants). It conflicts with nothing in flight: specs 039 and
  later change the zip, which moves these checks' fuel as it moves every snapshot check's.
- **Research it stands on:** `../research/2026-10-18-numpy-and-pandas-own-tests-in-the-guest.md`
  (written with this specification; EXECUTED on the frozen set `s-0cdc7b2bd78db6f5`, its
  evidence in the drafting session's folder, copied beside it): pytest in the guest and its six
  adaptations; every number below; the four numpy functions that trap the guest; the zip's
  relative code names behind 2,428 pandas failures. Also the spike memo ("The first release gate
  should run numpy's and pandas' own test subsets"), the principal engineer's direction (item 5:
  "the cheapest way to find the next `os.dup`"), the autonomous-ports memo (lesson 14: "numpy's
  and pandas' own test subsets, whose pass counts ratchet") and the roadmap, milestone 6.

## The problem

The judge's semantic oracle for numpy and pandas is five golden jobs. They prove a CSV read, a
groupby, a CSV write, random numbers and compression. They cannot find a numpy function that
crashes the guest, because no golden job calls it. The scoreboard says so on its last lines:
"not machine-checked: … numpy/pandas test subsets".

numpy and pandas ship tens of thousands of tests of their own. The drafting runs put them in the
guest. pytest runs there with six adaptations. Upstream's own fast modes pass 20,658 numpy tests
in 502 G fuel, and eight product-centred pandas groups pass 41,911 tests in 1,117 G. On the way
they found what no golden job could:

- **four numpy C functions trap the guest.** `copy.copy(np.float64(1.5))` and
  `a.dtype = np.float32` end the whole call in a wasm trap, not a Python exception;
- **every pandas warning points inside pandas,** because the zip's code objects carry relative
  file names; 2,428 of pandas' fast-mode failures are this one cause;
- **carried patch 0001 changes two numpy behaviours** (saving a masked array no longer raises;
  a truncated file's message differs).

This specification makes those suites a judge job: a ratcheted pass count, a fuel metric per
group, and every failure named with its closer, so the next `os.dup` is found by the judge and
not by a user.

## Decisions

1. **What runs.** numpy's and pandas' own tests, from the pinned source trees, in the
   **snapshot** binary, through the judge's own driver (`tests/harness/guest.py`), with pytest
   running inside the guest. One guest session per group (Decision 8), one check per group. The
   snapshot, not the plain binary: it is the binary embedders call, its numpy and pandas are the
   same compiled code, and the plain binary's import path is already proved by the golden jobs;
   both would double the cost (EXECUTED cost per group, Decision 8).

2. **The test kit: seven pure-Python wheels, pinned by the judge.**
   `tests/upstream/kit.txt` holds one line per wheel, `<sha256>  <url>`, as `downloads/SHA256SUMS`
   does (hashes recomputed from the downloads while drafting; each equals PyPI's published
   digest):

   ```
   2c5efc453d45394fdd706ade797c0a81091eccd1d6e4bccfcd476e2b8e0ab5d9  https://files.pythonhosted.org/packages/d4/24/a372aaf5c9b7208e7112038812994107bc65a84cd00e0354a88c2c77a617/pytest-9.0.3-py3-none-any.whl
   7dd7b0d8832ba3cb632c306926ded123429211b83641b35dc5c41ad2d34f9bec  https://files.pythonhosted.org/packages/40/9e/2b38731e0fc536806f16490e1a12d7f0dc2a1235aa8cc07bcc75416a7daa/pluggy-1.7.0-py3-none-any.whl
   9121e2c1fdb355232495be3194c8dfe87ccc2d5dee45947b78e68f499790d7a7  https://files.pythonhosted.org/packages/56/43/4ca9e49d27a1fcf6bece6f6aec0ea46bb9112489b93d4b688fb415457bdb/iniconfig-2.3.1-py3-none-any.whl
   d7193f7c8e4e93f444fde0262bf90af30e16fa0ad0ad44cb553c87339b23cd1c  https://files.pythonhosted.org/packages/63/34/ba1c580383c9eada3711951fef0795c80b829a078d72188184bcab9dd527/packaging-26.3-py3-none-any.whl
   2363c69b61c4a97c838da3b130dcd6468f4848992b21a82f2a63ec34377137d9  https://files.pythonhosted.org/packages/71/46/17f022dd3e953bf20a04a028a21ec746d942f8d2af30fa0f124fa0e6a684/pygments-2.21.0-py3-none-any.whl
   40a3619d9e0cb97b018857c7986f75cf5de2e5ec0fa8a0b172d00747758f749e  https://files.pythonhosted.org/packages/5d/83/860fb3075e00b0fc19a22a2301bc3c96f00437558c3911bdd0a3573a4a53/hypothesis-6.152.1-py3-none-any.whl
   a163dcaede0f1c021485e957a39245190e74249897e2ae4b2aa38595db237ee0  https://files.pythonhosted.org/packages/32/46/9cb0e58b2deb7f82b84065f37f3bffeb12413f947f9388e4cac22c4621ce/sortedcontainers-2.4.0-py2.py3-none-any.whl
   ```

   - **The versions.** pytest 9.0.3, the newest pytest pandas 3.0.6 accepts
     (`pytest>=8.3.4,<9.1`, its `test` extra; READ). hypothesis 6.152.1, the version numpy 2.5.2
     pins (`requirements/test_requirements.txt`; READ); pandas asks `>=6.116.0`. The others are
     pytest's and hypothesis's requirements at the versions the dev group already locks
     (`uv.lock`: pluggy 1.7.0, iniconfig 2.3.1, packaging 26.3, pygments 2.21.0) and
     sortedcontainers 2.4.0, hypothesis's one requirement (READ: PyPI's `requires_dist`).
   - **Not the dev group's pytest.** The judge's own pytest is 9.1.1, outside pandas' range, and
     the guest's kit should move only when the suites need it, not when the judge's tooling
     does.
   - **Not in `downloads/SHA256SUMS`.** Every line there becomes a `pin` line in `MANIFEST`
     (`scripts/assemble_artifacts.py`, the `pins` loop; READ), so test-only wheels would change
     the artifact set and make this build-class. The kit is judge input, pinned in the judge, as
     the oracle is (spec 002, Decision 11). It is still pinned by URL and SHA-256 and verified
     before use (§4.2).
   - **Fetching.** `uv run python tests/upstream/fetch.py` downloads each URL into
     `build/upstream/wheels/` and keeps a file only if its SHA-256 matches; any mismatch deletes it
     and exits non-zero. The judge never fetches. The harness unpacks the wheels with `zipfile`;
     no wheel's code runs natively, only inside the guest (§4.8).
   - **Licences** (READ, each wheel's metadata): pytest, pluggy, iniconfig MIT; packaging
     Apache-2.0 OR BSD-2-Clause; pygments BSD-2-Clause; hypothesis MPL-2.0; sortedcontainers
     Apache-2.0. None ships in the release or the wheel, so §4.12 does not reach them; the memo
     records them.

3. **Where the tests come from: the pinned source trees, copied read-only.**
   `tests/harness/upstream.py` stages, for each guest session, a fresh folder under
   `build/harness/upstream/` and grants it read-only at `/upstream`:

   ```
   /upstream/kit/                     the seven wheels, unpacked
   /upstream/judge/drive.py           tests/upstream/drive.py
   /upstream/judge/numpy.ini          tests/upstream/numpy.ini
   /upstream/judge/pandas.ini         tests/upstream/pandas.ini
   /upstream/tests/numpy/**/tests/    every folder named `tests` under build/numpy-2.5.2/numpy,
                                        except under numpy/_core/src/ (vendored code's own tests)
   /upstream/tests/pandas/conftest.py build/pandas-3.0.6/pandas/conftest.py
   /upstream/tests/pandas/tests/      build/pandas-3.0.6/pandas/tests
   ```

   Files are copied whole (data files included), skipping `__pycache__` and the litter names the
   harness already skips. The trees are the ones spec 020 proves equal to their pinned tarballs
   plus the recorded patches, so the tests are the pinned release's, with patch 0001's own test
   (`test_save_load_without_dup`) among them. **Not a test zip built by the build:** that is a
   build step, a new build output and a build-class change, for files the judge can read where
   they already are. **Not the product's zip:** it carries no `tests` folder (0 members,
   EXECUTED), and must not.
   pandas' sdist ships no `pandas/tests/io/data` (READ, `tar tzf`): those tests become skips
   through pandas' own `--no-strict-data-files` (`pandas/conftest.py:106`; Decision 6).

4. **How the guest finds them: the test folders join the product's packages.** numpy and pandas
   are imported from the product (builtin modules and the zip). The driver appends
   `/upstream/tests/<package path>` to the `__path__` of each package that owns a test folder,
   before pytest starts:

   - numpy: `numpy`, `numpy._core`, `numpy.lib`, `numpy.linalg`, `numpy.fft`, `numpy.random`,
     `numpy.ma`, `numpy.polynomial`, `numpy.matrixlib`, `numpy.testing`;
   - pandas: `pandas`.

   So `numpy._core.tests._locales` (numpy's test folders are namespace packages; they have no
   `__init__.py`, READ) and `pandas.tests.extension.base` import from the grant, and nothing of
   the product is replaced (EXECUTED). One test notices: `test_public_api.py::test_api_importable`
   finds `numpy.conftest` listed but not importable, because the product carries no
   `numpy/conftest.py` (Decision 10's class "test-only modules").

5. **pytest's options in the guest, each with its reason (EXECUTED unless marked).** The driver
   calls `pytest.main` with exactly these, then the group's own (Decision 8):

   | option | why |
   |---|---|
   | `-p no:faulthandler` | the plugin duplicates stderr's descriptor: `OSError: [Errno 58]` before collection |
   | `--capture=sys` | fd capture duplicates descriptors: `INTERNALERROR> OSError: [Errno 58]` |
   | `-o log_file=/tmp/pytest.log` | the logging plugin's default is `os.devnull`; WASI has no `/dev/null` |
   | `--basetemp=/tmp/pytest` | pytest's default temporary root calls `os.getuid`, which WASI lacks (it exempts win32 and emscripten, not wasi: `_pytest/compat.py:269`, READ); every `tmp_path` test errored |
   | `-p no:cacheprovider` | the cache would be written into the read-only grant; nothing reads it (INFERRED) |
   | `--import-mode=importlib` | no `sys.path` insertion, and numpy's six `test_regression.py` files cannot clash (INFERRED; `prepend` also ran one file) |
   | `--rootdir=/upstream/tests -c /upstream/judge/<pkg>.ini` | node ids are `numpy/…` and `pandas/…`; the configuration is Decision 6's |
   | `-q --tb=no --no-header -rN` | the stream (Decision 11) is the record; the terminal report is not read |

   The driver sets `sys.dont_write_bytecode = True` and runs under `python -u`. `/tmp` is in the
   guest's writable root, as in every judge run (guest.py's root is writable by design). The
   pytest-on-WASI facts (`getuid`, `/dev/null`) are pytest's to fix; drafting an upstream note
   is outside this specification (Scope).

6. **Upstream's own configuration, transcribed.** `tests/upstream/numpy.ini` is numpy 2.5.2's
   `pytest.ini` `filterwarnings` block (`error` and its ignores; READ) plus
   `ignore::pytest.PytestAssertRewriteWarning` (the driver imports hypothesis before pytest, so
   `_hypothesis_globals` cannot be rewritten; with `error` this warning stopped the run,
   EXECUTED; pandas' own configuration ignores it). numpy's markers (`slow`, `valgrind_error`,
   `leaks_references`, `parallel_threads`, `iterations`, `thread_unsafe`) are registered by the
   driver, as numpy's `conftest.py` does; numpy's `conftest.py` itself is not used, because it
   imports `numpy._core._multiarray_tests`, which the product does not link (READ, line 14).
   `tests/upstream/pandas.ini` is pandas 3.0.6's `[tool.pytest.ini_options]` (READ): its
   `markers`, `filterwarnings`, `xfail_strict = true` and `empty_parameter_set_mark`; not its
   `--junitxml` or `--durations`. pandas' `conftest.py` is used as is. The pandas sessions add
   `--no-strict-data-files`. hypothesis gets numpy's own "np.test() profile" values, registered
   by the driver as the profile `judge`: `database=None, derandomize=True, deadline=None,
   print_blob=True`, every health check suppressed. Derandomized and with the driver's seeded
   random and stepped clock, a group's fuel repeats (Decision 12).

7. **Upstream's own fast selection.** numpy sessions run `-m "not slow"`, `numpy.test()`'s
   default (`numpy/_pytesttester.py:164`); pandas sessions run `-m "not slow and not network
   and not db"`, `pandas.test()`'s default (`pandas/util/_tester.py:43`) (READ). Whatever
   upstream marks slow it also leaves out of its own default run. numpy's slow tests cost 705 G
   of its 1,207 G for 68 passes (EXECUTED).

8. **The groups, and what is left out.** Each group is one guest session and one check,
   `test_upstream_suite[<group>]`, so one group's trap or failure never hides another's, and fuel
   is a metric per group. Each group's fuel cap is about 1.5 times its drafting fuel, so a
   runaway ends as "out of fuel", a failure (the harness default, 2×10¹¹, is too small for
   most).

   | group | paths | passed | fuel (drafting) | cap |
   |---|---|---|---|---|
   | `numpy-core` | `numpy/_core/tests` | 8,568 | 195.8 G | 3.0×10¹¹ |
   | `numpy-lib` | `numpy/lib/tests` | 4,823 | 131.4 G | 2.0×10¹¹ |
   | `numpy-others` | `numpy/{fft,linalg,ma,matrixlib,polynomial,random,testing}/tests`, `numpy/tests` | 7,267 | 174.9 G | 2.7×10¹¹ |
   | `pandas-frame` | `pandas/tests/frame` | 10,831 | 337.1 G | 5.1×10¹¹ |
   | `pandas-groupby` | `pandas/tests/groupby` | 22,156 | 460.3 G | 7.0×10¹¹ |
   | `pandas-reshape` | `pandas/tests/reshape` | 2,657 | 101.2 G | 1.6×10¹¹ |
   | `pandas-io-parser` | `pandas/tests/io/parser` | 3,401 | 85.8 G | 1.3×10¹¹ |
   | `pandas-io-formats` | `pandas/tests/io/formats` | 955 | 53.6 G | 8.1×10¹⁰ |
   | `pandas-tslibs` | `pandas/tests/tslibs` | 590 | 38.6 G | 5.8×10¹⁰ |
   | `pandas-internals` | `pandas/tests/internals` | 258 | 18.1 G | 2.8×10¹⁰ |
   | `pandas-libs` | `pandas/tests/libs` | 1,063 | 22.4 G | 3.4×10¹⁰ |
   | **all** | | **62,569** | **1,619 G** | |

   **numpy: all of it that can run.** Every numpy test folder is in a group except `f2py` (it
   compiles extensions), `typing` (it runs mypy) and `_pyinstaller`. Inside the groups, these
   files are not selected (`--ignore`), each named with its reason and closer in
   `tests/upstream/numpy.toml`:

   | files | reason | closes with |
   |---|---|---|
   | 23 files that import numpy's C test modules (`_core/tests/` `test_api`, `test_argparse`, `test_array_coercion`, `test_arrayobject`, `test_arrayprint`, `test_conversion_utils`, `test_cpu_dispatcher`, `test_deprecations`, `test_dtype`, `test_extint128`, `test_getlimits`, `test_hashtable`, `test_indexing`, `test_mem_overlap`, `test_multiarray`, `test_multithreading`, `test_nditer`, `test_numeric`, `test_scalarbuffer`, `test_scalarmath`, `test_ufunc`, `test_umath`; `lib/tests/test_stride_tricks`) | `_multiarray_tests`, `_umath_tests`, `_rational_tests`, `_operand_flag_tests` are not linked (`scripts/gen_inittab.py:27`) | `context/questions-for-the-owner.md` (question 89) |
   | `test_simd.py`, `test_simd_module.py` | `_simd` is not linked | the same |
   | `test_casting_unittests.py`, `test_arraymethod.py` | they trap the guest (Decision 9); `test_arraymethod` at collection | the research memo |
   | `test_memmap.py` | every test needs `mmap`, which WASI lacks | `README.md` |
   | `tests/test_ctypeslib.py` | it reads `_multiarray_umath.__file__`, which a builtin module has not | `README.md` |

   **pandas: eight groups, chosen for the product and the budget.** pandas' fast mode over all 40
   directories costs 3,922 G (EXECUTED), about 13 minutes; too much for a judge that runs on every
   landing. The eight are the golden job's path (`io/parser` reads CSV, `io/formats` writes it,
   `groupby`), the frame core (`frame`, `reshape`, `internals`) and the C layers under them
   (`libs`, `tslibs`): 1,117 G. Left out, by budget alone, with their fast-mode cost:
   `arithmetic` 489 G, `indexes` 275 G, `extension` 275 G, `arrays` 220 G, `series` 207 G,
   `window` 176 G, `resample` 116 G, `tseries` 107 G, `indexing` 85 G, `scalar` 79 G, `dtypes`
   65 G, `strings` 62 G, `computation` 61 G, `tools` 52 G, `io/json` 41 G, `copy_view` 34 G,
   `base` 31 G and smaller ones; and by cause, `io/pytables` (stops at
   `importorskip("tables")`), `io/test_clipboard.py` (Qt fixtures), `plotting` (no matplotlib in
   this set), `io/excel` and `io/sas` (all skips). None trapped (EXECUTED, full mode). Adding a
   group is a judge change with its drafting numbers.

   **The budget.** All groups and traps together stay under 1.8×10¹² fuel; a change that grows
   past it says why. On the drafting machine that is about six minutes (a benchmark fact:
   numpy `lib` took 25.4 s and pandas `reshape` 30.7 s, compile included).

9. **Tests that trap the guest are deselected, and each is checked to still trap.** A trap ends
   the session, so a trapping test cannot run in its group. `tests/upstream/numpy.toml` lists
   each as a `[[trap]]` entry: a node id or node-id prefix, the trap's cause, the reason and the
   closer. The group passes them to pytest as `--deselect` (a prefix deselects every
   parametrization, EXECUTED). Two whole files are `--ignore`d (Decision 8). Then
   `test_upstream_trap_still_traps[<id>]` runs each entry alone in its own session (cap 5×10¹⁰)
   and asserts: the guest trapped, the trap's cause is `indirect call type mismatch`, and the last
   test the stream started (Decision 11) begins with the entry's node id. A trap that no longer
   traps fails the check with "remove the entry", so a fix is seen the day it lands.

   | id | node id (prefix) or file | the C function (numpy 2.5.2, READ) |
   |---|---|---|
   | `castingimpl-casting-unittests` | `numpy/_core/tests/test_casting_unittests.py` | `_get_castingimpl(module, args)`, `convert_datatype.c:248`, registered `METH_VARARGS \| METH_KEYWORDS` |
   | `castingimpl-arraymethod` | `numpy/_core/tests/test_arraymethod.py` | the same (INFERRED: frame 0 `cfunction_call`, at collection) |
   | `castingimpl-stringdtype` | `numpy/_core/tests/test_stringdtype.py::test_cast_method_names` | the same |
   | `descr-set-records` | `numpy/_core/tests/test_records.py::TestRecord::test_assign_dtype_attribute` | `array_descr_set(self, arg)`, `getset.c:388`, a setter |
   | `descr-set-stringdtype` | `numpy/_core/tests/test_stringdtype.py::test_view_distinct_instance` | the same |
   | `gentype-copy` | `numpy/_core/tests/test_regression.py::TestRegression::test_scalar_copy` | `gentype___copy__(self)`, `scalartypes.c.src:2128`, `METH_NOARGS` |
   | `sfloat-reduce` | `numpy/_core/tests/test_custom_dtypes.py::TestSFloat::test_np_save_load` | `sfloat___reduce__(self)`, `_scaled_float_dtype.c:192`, `METH_NOARGS` |

   Each closes with the research memo, which names the follow-up: a carried patch (§4.1) fixing
   the four signatures, with its upstream pull request drafted. With the traps deselected the
   `numpy-core` group ran to its end (EXECUTED). `tests/upstream/pandas.toml` has no trap entry:
   pandas trapped nowhere, in full mode (EXECUTED).

10. **Expected failures are classes, strict both ways.** A test that runs and fails for a known
    reason is admitted by an `[[expected]]` class in the package's TOML, never by an `xfail`
    marker or a `known_gaps.toml` entry. A class has: `id`; `group`; `outcome` (`failed` or
    `error`); either `match` (a regular expression searched in the one-line reason) or `nodes`
    (an explicit list of node ids); `count`; `digest` (the first 12 hex digits of the SHA-256 of
    the sorted node ids, one per line); `reason` (one line); `closes_with` (an existing path under
    `context/` or `README.md`, as spec 002's gaps). The check sorts each failed or errored test
    into the first class of its group that matches; then:
    - a test no class takes is a finding: `unexpected <outcome> <node id> — <reason>`;
    - a class whose tests differ from its `count` and `digest` is a finding:
      `class <id>: expected <n> (<digest>), saw <m> (<digest>)`. One more or one fewer is red, so
      a fix shows ("remove or shrink the class"), and a new failure that happens to match a
      class's text still changes its digest;
    - a collection error, an `INTERNALERROR`, a pytest exit code other than 0 or 1, a missing end
      line, a trap or "out of fuel" is a finding, never admitted;
    - a pass, a skip, an `xfail` and a non-strict `xpass` are upstream's own outcomes and not
      findings; pandas' strict `xpass` arrives as `failed` (`[XPASS(strict)]`) and needs a class.

    The check reports `N finding(s), digest <12 hex>` (spec 002, Decision 4), so the usual gap
    machinery still works for a whole check if ever needed. Why classes, not spec 002's gaps
    alone: a gap admits one check's findings under one closer, and a group's failures have
    several closers (the README's platform facts, the memo's defects, question 89). Why not a
    per-test list: 193 of pandas' failures are one cause, and the digest pins the exact set
    without a 193-line entry. The classes the drafting runs found, by group (EXECUTED; the
    builder writes each digest from the first run on the frozen set and reviews that the run
    matches these counts):

    | group | class | outcome | count | match / nodes | closes with |
    |---|---|---|---|---|---|
    | `numpy-core` | `no-dup` | failed | 8 | `OSError: \[Errno 58\] Not supported` | `README.md` |
    | `numpy-core` | `no-dup-file-left-open` | error | 3 | `PytestUnraisableExceptionWarning: Exception ignored while finalizing file` | `README.md` |
    | `numpy-core` | `no-processes` | failed | 3 | `wasi does not support processes` | `README.md` |
    | `numpy-core` | `test-only-modules` | failed | 1 | nodes: `test_numerictypes.py::Test_sctype2char::test_third_party_scalar_type` | question 89 |
    | `numpy-lib` | `no-mmap` | failed | 5 | `mmap is unavailable` | `README.md` |
    | `numpy-lib` | `no-dev-null` | failed | 1 | `No such file or directory: '/dev/null'` | `README.md` |
    | `numpy-lib` | `patch-0001-truncated-message` | failed | 1 | nodes: `numpy/lib/tests/test_format.py::test_file_truncated` | the memo |
    | `numpy-others` | `no-ctypes` | failed | 8 | `ctypes is unavailable` | `README.md` |
    | `numpy-others` | `patch-0001-masked-save` | failed | 1 | nodes: `numpy/ma/tests/test_core.py::TestMaskedArray::test_maskedarray_tofile_raises_notimplementederror` | the memo |
    | `numpy-others` | `test-only-modules` | failed | 2 | nodes: `numpy/tests/test_public_api.py::test_NPY_NO_EXPORT`, `…::test_api_importable` | question 89 |
    | `numpy-others` | `zip-code-names` | failed | 1 | nodes: `numpy/testing/tests/test_utils.py::test_suppress_warnings_module` | the memo |
    | `pandas-frame` | `zip-code-names` | failed | 21 | `Warning not set with correct stacklevel` | the memo |
    | `pandas-groupby` | `zip-code-names` | failed | 71 | the same | the memo |
    | `pandas-reshape` | `zip-code-names` | failed | 7 | the same | the memo |
    | `pandas-io-parser` | `zip-code-names` | failed | 73 | the same | the memo |
    | `pandas-io-parser` | `no-mmap` | failed | 40 | `mmap is unavailable` | `README.md` |
    | `pandas-io-formats` | `zip-code-names` | failed | 21 | `Warning not set with correct stacklevel` | the memo |
    | `pandas-tslibs` | `no-processes` | failed | 1 | `wasi does not support processes` | `README.md` |

    Totals: numpy 31 failed and 3 errors, pandas 234 failed, matching the drafting runs. `README.md`
    is the closer only for a fact the README states (a permanent platform fact); the README gains
    the one it lacks, `/dev/null` (Decision 17).

11. **The outcome stream.** The driver writes `/tmp/upstream/outcomes.txt` in the guest's
    writable root, flushing every line: `S <node id>` when a test starts; `R <outcome> <node id>
    -- <reason>` for every outcome (passes included; the reason is the crash message's first line,
    or a skip's reason, at most 200 characters, newlines replaced); `X <node id> -- <reason>` for
    a collection error; `E <pytest exit code>` last. The host reads it from the run's root after
    the guest returns, so nothing depends on the guest's stdout buffering or size. On a trap the
    last `S` line with no `R` line names the test that trapped. The reason is the class's input,
    so it never contains host paths: the grant's paths are guest paths (`/upstream/…`).

12. **Metrics: fuel per group, and a pass count that must not fall.** Each group check records
    `fuel` (the ratchet's 0.01% applies: the drafting runs repeated within 221 instructions in
    131 G and 68 in 101 G, EXECUTED) and a new metric, **`passes`**: the number of `R passed`
    lines. The harness learns it: `metric("passes", n)` is allowed (`plugin.py`); in the ratchet
    (`scoreboard.py`), a `passes` value **below** the accepted one on the same platform is red,
    with the line `<node>: passes <old> -> <new>`; acceptance keeps the **maximum** of the old and
    new values, and a fall is accepted only with `--accept-growth "<why>"` (the flag already means
    "a metric moved the wrong way, and here is why"). So no pass is lost quietly, even to a skip
    or a deselection (rule 5). `build/progress/latest.json` carries each group's `passes` with its
    other metrics; `context/progress/README.md` documents the metric.

13. **The needs.** The group and trap checks call `need("snapshot binary", "stdlib zip",
    "manifest", "wasmtime-py", "source tree numpy" or "source tree pandas", "upstream kit")`.
    `upstream kit` is new (`needs.py`): met when every file of `tests/upstream/kit.txt` is in
    `build/upstream/wheels/` with its SHA-256; provided by this specification. Like `oracle` and
    the source trees it is local tooling, not a protected need: an accepted pass blocked by it is
    "unrun locally", reported, not red (spec 002, Decision 6). The lane's main tree holds the
    source trees and fetches the kit once; the landing notes say so.

14. **The trap's cause, kept.** `guest.Result.trapped` keeps today's first line, and `Result`
    gains `trap_cause`: the text after the trap message's `Caused by:` line (`wasm trap:
    indirect call type mismatch`), or `None`. Today's first line is "error while executing at wasm
    backtrace:" for every such trap (EXECUTED), which cannot tell one cause from another.

15. **Marked `slow`, in the full judge.** The group and trap checks are `slow`, like the golden
    jobs: `uv run pytest -m "not slow"` skips them, the full `uv run pytest` and so the lane runs
    them. About six minutes on the drafting machine (Decision 8's benchmark fact); the release dry
    run does not run them, since its workflow is not changed (Scope).

16. **Not build-class.** No file under `scripts/` or `recipes/`, no line of
    `downloads/SHA256SUMS`, no release workflow, no rebuild. It is a judge change: every new and
    changed file is under `tests/` (or is the scoreboard's README), so acceptance takes
    `--accept-judge`. The pre-build design review is asked for in the status line because the
    `passes` metric and the classes change how the judge admits failure.

17. **What the README and the CHANGELOG say.** README: the platform paragraph gains "no
    `/dev/null`" (`os.devnull` names a path that does not exist), and a short "Known defects"
    list until each closes: `copy.copy` of a numpy scalar, `__copy__` on one, and assigning
    `ndarray.dtype` end the call in a trap, not an exception; pandas' warnings name a pandas file,
    not the caller's line; `np.save` of a masked array writes its data without its mask instead
    of raising. "Measured" gains a row: numpy's and pandas' own tests, 62,569 passing in the
    guest (the accepted count). The scoreboard's "not machine-checked" line drops "numpy/pandas
    test subsets". CHANGELOG: one line under the next alpha's "Judge" heading.

18. **The follow-ups this opens, by name, so nothing is left open here.** Each closer above is
    an existing path when this lands: the memo (written with this specification), `README.md`,
    and question 89. The memo names three follow-up specifications, each its own work: a carried
    patch for the four numpy C signatures (Decision 9's table) with its pull request drafted;
    the zip's code objects compiled under the name they are imported by (a `scripts/` change,
    build-class); patch 0001's draft amended for its two behaviours. When one lands, it edits the
    classes or trap entries it closes, as a judge change, and the `passes` metric rises.

## Intent

The judge runs numpy's and pandas' own tests inside the guest, counts every pass, names every
failure with what will close it, and turns red when a pass is lost, a failure appears, or a
known failure goes away unrecorded.

## Design

```
tests/upstream/kit.txt               the seven wheels: "<sha256>  <url>" (Decision 2)
tests/upstream/fetch.py              downloads the kit into build/upstream/wheels/, verifying each
                                       hash; never run by the judge
tests/upstream/drive.py              guest side: kit on sys.path, test folders on the packages'
                                       __path__ (Decision 4), hypothesis profile `judge`, markers,
                                       pytest.main with Decision 5's options, the outcome stream
                                       (Decision 11)
tests/upstream/numpy.ini             numpy's pytest.ini filterwarnings, plus one ignore (Decision 6)
tests/upstream/pandas.ini            pandas' [tool.pytest.ini_options], less junit and durations
tests/upstream/numpy.toml            marker; packages for __path__; [groups.<name>] paths and
                                       fuel caps; [[not_selected]]; [[trap]]; [[expected]]
tests/upstream/pandas.toml           the same for pandas (no trap entries)
tests/harness/upstream.py            load and validate the TOML; stage /upstream (Decision 3);
                                       build each group's argv; run it through guest.run with a
                                       read-only grant at /upstream; parse the stream; sort into
                                       classes; findings; passes
tests/harness/guest.py               Result.trap_cause (Decision 14)
tests/harness/needs.py               the need "upstream kit"
tests/harness/plugin.py              metric("passes", n) allowed
tests/harness/scoreboard.py          passes: red when it falls; accept keeps the maximum;
                                       NOT_MACHINE_CHECKED without "numpy/pandas test subsets"
tests/checks/test_v1_3_upstream_suites.py
                                     test_upstream_suite[<group>] (11, slow)
                                     test_upstream_trap_still_traps[<id>] (7, slow)
                                     test_upstream_expectations_are_well_formed (rules, fast)
tests/unit/test_upstream.py          the stream parser, the sorting into classes, the digest, the
                                       argv, on fixed inputs; no guest
context/progress/README.md           the passes metric
README.md, CHANGELOG.md              Decision 17
context/research/2026-10-18-numpy-and-pandas-own-tests-in-the-guest.md
                                     the memo, with its evidence folder
```

A group's run, in order: stage `/upstream`; argv = `-u /upstream/judge/drive.py <package>
<group>`, the driver reading the group's paths, `--ignore`s, `--deselect`s and marker from a
JSON file the harness writes into the grant (so no argument parsing is duplicated in the
guest); `guest.run(snapshot, argv, workdir, stdlib, env={"TMPDIR": "/tmp", "HOME": "/tmp"},
fuel=<cap>, preopens=[("/upstream", <stage>, False)])`; read the stream; findings; record
`fuel` and `passes`; assert no finding.

## Scope

In: numpy's test folders as Decision 8 groups them, and the eight pandas groups; the test kit
pinned and fetched by the judge; the trap entries and their check; the expected classes; the
`passes` metric; the need; README, CHANGELOG, the scoreboard's line; the memo.

Out:
- **Fixing what the suites found.** The four C signatures, the zip's code names and patch 0001's
  behaviours are follow-up specifications (Decision 18).
- **numpy's C test modules** and the 25 files that need them: question 89.
- **The plain binary.** Decision 1.
- **The rest of pandas** (2.8 T fuel in fast mode) and numpy's slow tests: by budget; each can
  be added later as a judge change with its numbers.
- **The release workflow.** These checks do not run in the release dry run; adding the kit and
  the source trees there is a build-class change of its own.
- **Other packages' suites** (matplotlib, scipy, tier A): each package's own specification may
  add groups through this mechanism once it lands.
- **Upstream notes** to pytest about `getuid` and `/dev/null` on WASI.
- **Wall-clock.** No check reads a clock (§4.9); the six minutes are a benchmark fact.

## Acceptance criteria

1. `uv run python tests/upstream/fetch.py` fetches the seven wheels into `build/upstream/wheels/`
   and each SHA-256 equals its `kit.txt` line; altering one byte of a kept wheel makes the need
   `upstream kit` unmet (a unit check on a scratch copy). The judge never opens the network.
2. **Seen failing first.** Before the classes and trap entries are written, the 11 group checks
   run on the frozen set and fail with the drafting runs' findings (numpy 31 failed and 3
   errors, pandas 234 failed, and a trap in `numpy-core` while its trap entries are absent); the
   builder records the counts and compares them with Decision 10's table. Any difference is
   explained in the landing notes before a class is written.
3. With the TOML complete, every `test_upstream_suite[<group>]` passes on the frozen set:
   no finding; passes per group equal Decision 8's table (62,569 in all). Any difference is
   explained in the landing notes; the guest is the same bytes on every host, so a host is not
   an explanation.
4. Every `test_upstream_trap_still_traps[<id>]` passes: seven traps, each with cause `indirect
   call type mismatch`, each at a test whose node id begins with its entry. A unit check shows
   that an entry whose test passes yields "remove the entry".
5. **Strictness, shown on fixed streams** (`tests/unit/test_upstream.py`): one extra failure
   matching a class's text turns the class's digest wrong (red); one fewer turns it wrong (red); a
   failure no class takes is a finding; a collection error, exit code 2 to 5, a missing `E` line,
   a trap and "out of fuel" are findings; skips, `xfail` and non-strict `xpass` are not.
6. **The `passes` metric** (unit checks on the ratchet): a value below the accepted one is red
   with `passes <old> -> <new>`; `--accept-growth` accepts it; without it, acceptance keeps the
   maximum; a value above is "gained", not red; `metric("passes", …)` is accepted and an unknown
   name still raises.
7. **Fuel repeats:** each group run twice in one session (a one-off check by the builder, not a
   judge check) gives fuel within 0.01%; the landing notes give both values for every group.
8. `test_upstream_expectations_are_well_formed` (rules) passes: every `closes_with` exists;
   every class has `count` > 0 and a 12-hex `digest` and exactly one of `match` and `nodes`;
   ids are unique per group; every group's paths and every `not_selected` and `trap` file exist
   in the staged source tree when the need is met; the sum of the groups' caps and the trap caps
   is at most 1.8×10¹² (Decision 8).
9. The product is untouched and the tests cannot change it: a unit check shows the preopens
   built for a group grant `/upstream` read-only; the change has no file under `scripts/`,
   `recipes/`, `downloads/` or `.github/` (`git diff --stat`), so the artifact set is the frozen
   set's.
10. `uv run ruff check`, `uv run ruff format --check`, and `uv run pytest` green, with
    `--accept-judge` naming the new checks and the harness changes; ratchet vs the base: lost 0,
    grew 0 (no existing check's fuel moves: the harness changes record, they do not run the
    guest differently), gained 19 (11 groups, 7 traps, 1 rule). The scoreboard's last lines no
    longer list "numpy/pandas test subsets".

## The owner's choices

None open here: every choice this specification needs is decided above (§5.2). One question is
new and is the owner's, because it would add a build output: **question 89**, whether to reach
numpy's 25 core test files that need its C test modules, through a judge-only binary built
beside the product and never published (the agent's recommendation, as a later build-class
specification), or by linking the modules into the product, or not at all. This specification
builds without it: those files are `not_selected`, closed by the question.

## Landing notes
