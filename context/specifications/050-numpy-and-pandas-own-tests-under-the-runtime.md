# 050 — numpy's and pandas' own tests under the runtime

- **Status:** **landed 2026-10-18** (accepted on `34eb315` as `d903110`; release dry run not yet run). Its build review (`../reviews/050-numpy-and-pandas-own-tests-under-the-runtime-2026-10-18.md`) confirmed it after the rebase onto 051; the rebase delta's review (`../reviews/050-numpy-and-pandas-own-tests-under-the-runtime-rebase-2026-10-18.md`) confirmed it lands; see the Landing notes' last section. What follows is the status as it stood before the landing. **Spec 051 lands before this one** (the lane's order, 2026-10-18). This specification rebases onto 051 and re-derives its tables on 051's artifact set: the seven `[[trap]]` entries and their gaps (their callbacks are fixed by 051's patch 0002), the six `zip-code-names` classes and the two `patch-0001-*` classes (fixed by 051), `test_casting_unittests.py` and `test_arraymethod.py` (out of `not_selected`), and each group's `passes`. Where its text says 051 edits these files after it lands, this specification does that work itself; 051's Decision 12 is done here. confirmed for build with conditions, written in. Drafted 2026-10-18; revised the same day against its pre-build review (`../reviews/050-numpy-and-pandas-own-tests-under-the-runtime-spec-2026-10-18.md`, findings F1 to F15, each answered in its Disposition and written in below). The review's Confirmation set one condition, C1: what a fixed class or trap becomes. It is written into Decisions 9, 10, 17 and 19 and criteria 4 and 8. The Confirmation's builder notes stay in the review; one of them, a file a recorded patch creates, is written into Decision 3. This specification changes how the judge admits failure and adds a metric that must not fall. §5.6 did not require a pre-build review, since it changes no import, export, artifact or build recipe; it asked for one. Built 2026-10-18 on `spec/050-upstream-tests`; awaiting its review (Landing notes).
- **Owner:** Clay Gendron
- **Kind:** the judge only.
  - **New:**
    - `tests/upstream/`: the guest-side driver, the two packages' configuration, the selections, the admitted failures by node id, the test kit's pins and its fetcher;
    - `tests/harness/upstream.py`;
    - `tests/checks/test_v1_3_upstream_suites.py`;
    - `tests/unit/test_upstream.py`;
    - 12 entries in `tests/known_gaps.toml` (on spec 051's set; 26 on the set before it).
  - **Changed:**
    - `tests/harness/needs.py` (one need);
    - `tests/harness/plugin.py` and `tests/harness/scoreboard.py` (the `passes` metric, its own ratchet list and flag, and a refusal to accept with these checks unrun);
    - `tests/harness/guest.py` (the trap's cause kept);
    - the scoreboard's "not machine-checked" line;
    - `context/progress/README.md`, `AGENTS.md` (rule 4 names the new allowance files);
    - spec 002, by dated amendment lines (Decision 19);
    - `README.md`, `CHANGELOG.md`;
    - a dated correction in the research memo.

  **Not build-class:** it touches no `scripts/`, `recipes/`, `downloads/SHA256SUMS` or release workflow, and rebuilds nothing (Decision 16).
- **Depends on:** landed specs only.
  - 002: the harness (checks, gaps, needs, the ratchet, the findings phrase).
  - 020: each source tree equals its pinned tarball plus the recorded patches; the tests are read from those trees.
  - 021: the patched numpy tree, whose own test of the patch runs here too.
  - 017: read-only grants.

  It conflicts with nothing in flight. Specs 039 and later change the zip, which moves these checks' fuel as it moves every snapshot check's. Spec 051 (drafted) fixes most of what these suites found and edits this specification's files when it lands after this one.
- **Research it stands on:** `../research/2026-10-18-numpy-and-pandas-own-tests-in-the-guest.md`. It was written with this specification, EXECUTED on the frozen set `s-0cdc7b2bd78db6f5`, with its evidence beside it. It covers pytest in the guest and its six adaptations, every number below, the four numpy functions that trap the guest, and the zip's relative code names behind 2,428 pandas failures.
  - **Earlier memos and plans:**
    - the spike memo ("The first release gate should run numpy's and pandas' own test subsets");
    - the principal engineer's direction (item 5: "the cheapest way to find the next `os.dup`");
    - the autonomous-ports memo (lesson 14: "numpy's and pandas' own test subsets, whose pass counts ratchet");
    - the roadmap, milestone 6.
  - **The pre-build review's runs:**
    - the kit's pins against PyPI;
    - the staged files against the tarballs' members;
    - one pandas group run twice to the instruction;
    - the active hypothesis settings at collection's end;
    - the classes recounted.
  - **Revision runs** (EXECUTED 2026-10-18): upstream's `--strict-markers --strict-config` in the guest. pandas `libs` gave 1,063 passed and 8 skipped, as before. numpy `test_datetime.py` and `test_io.py` together gave 688 passed, 2 failed, 6 xfailed and 8 skipped. Neither raised a configuration error.

## The problem

The judge's semantic oracle for numpy and pandas is five golden jobs. They prove a CSV read, a groupby, a CSV write, random numbers and compression. They cannot find a numpy function that crashes the guest, because no golden job calls it. The scoreboard says so on its last lines: "not machine-checked: … numpy/pandas test subsets".

numpy and pandas ship tens of thousands of tests of their own. The drafting runs put them in the guest. pytest runs there with six adaptations. Upstream's own fast modes pass 20,658 numpy tests in 502 G fuel, and eight product-centred pandas groups pass 41,911 tests in 1,117 G. On the way they found what no golden job could:

- **four numpy C functions trap the guest.** `copy.copy(np.float64(1.5))` and `a.dtype = np.float32` end the whole call in a wasm trap, not a Python exception;
- **every pandas warning points inside pandas,** because the zip's code objects carry relative file names; 2,428 of pandas' fast-mode failures are this one cause;
- **carried patch 0001 changes two numpy behaviours** (saving a masked array no longer raises; a truncated file's message differs).

This specification makes those suites a judge job:
- a ratcheted pass count;
- a fuel metric per group;
- every known failure shown on the scoreboard as a gap, by node id, with its closer.

So the next `os.dup` is found by the judge and not by a user.

## Decisions

1. **What runs.** numpy's and pandas' own tests run inside the guest:
   - from the pinned source trees;
   - in the **snapshot** binary;
   - through the judge's own driver (`tests/harness/guest.py`), with pytest running in the guest;
   - one guest session per group (Decision 8).

   **The snapshot, not the plain binary.** It is the binary embedders call, and its numpy and pandas are the same compiled code. The plain binary's import path is already proved by the golden jobs. Running both would double the cost (EXECUTED cost per group, Decision 8).

2. **The test kit: seven pure-Python wheels, pinned by the judge.** `tests/upstream/kit.txt` holds one line per wheel, `<sha256>  <url>`, as `downloads/SHA256SUMS` does. The hashes were recomputed from the downloads while drafting; each equals PyPI's published digest, and the pre-build review checked them again (EXECUTED).

   ```
   2c5efc453d45394fdd706ade797c0a81091eccd1d6e4bccfcd476e2b8e0ab5d9  https://files.pythonhosted.org/packages/d4/24/a372aaf5c9b7208e7112038812994107bc65a84cd00e0354a88c2c77a617/pytest-9.0.3-py3-none-any.whl
   7dd7b0d8832ba3cb632c306926ded123429211b83641b35dc5c41ad2d34f9bec  https://files.pythonhosted.org/packages/40/9e/2b38731e0fc536806f16490e1a12d7f0dc2a1235aa8cc07bcc75416a7daa/pluggy-1.7.0-py3-none-any.whl
   9121e2c1fdb355232495be3194c8dfe87ccc2d5dee45947b78e68f499790d7a7  https://files.pythonhosted.org/packages/56/43/4ca9e49d27a1fcf6bece6f6aec0ea46bb9112489b93d4b688fb415457bdb/iniconfig-2.3.1-py3-none-any.whl
   d7193f7c8e4e93f444fde0262bf90af30e16fa0ad0ad44cb553c87339b23cd1c  https://files.pythonhosted.org/packages/63/34/ba1c580383c9eada3711951fef0795c80b829a078d72188184bcab9dd527/packaging-26.3-py3-none-any.whl
   2363c69b61c4a97c838da3b130dcd6468f4848992b21a82f2a63ec34377137d9  https://files.pythonhosted.org/packages/71/46/17f022dd3e953bf20a04a028a21ec746d942f8d2af30fa0f124fa0e6a684/pygments-2.21.0-py3-none-any.whl
   40a3619d9e0cb97b018857c7986f75cf5de2e5ec0fa8a0b172d00747758f749e  https://files.pythonhosted.org/packages/5d/83/860fb3075e00b0fc19a22a2301bc3c96f00437558c3911bdd0a3573a4a53/hypothesis-6.152.1-py3-none-any.whl
   a163dcaede0f1c021485e957a39245190e74249897e2ae4b2aa38595db237ee0  https://files.pythonhosted.org/packages/32/46/9cb0e58b2deb7f82b84065f37f3bffeb12413f947f9388e4cac22c4621ce/sortedcontainers-2.4.0-py2.py3-none-any.whl
   ```

   - **The versions.**
     - pytest 9.0.3 is the newest pytest pandas 3.0.6 accepts (`pytest>=8.3.4,<9.1`, its `test` extra; READ).
     - hypothesis 6.152.1 is the version numpy 2.5.2 pins (`requirements/test_requirements.txt`; READ); pandas asks for `>=6.116.0`.
     - pluggy 1.7.0, iniconfig 2.3.1, packaging 26.3 and pygments 2.21.0 are pytest's requirements at the versions the dev group already locks (`uv.lock`).
     - sortedcontainers 2.4.0 is hypothesis's one requirement (READ: PyPI's `requires_dist`).
   - **Not the dev group's pytest.** The judge's own pytest is 9.1.1, outside pandas' range. The guest's kit should move only when the suites need it, not when the judge's tooling does.
   - **Pinned in the judge, as the oracle is.** The precedent is spec 002, Decision 11: the oracle's packages are pinned in their own `uv.lock` under `tests/`, and the judge's own pytest in `uv.lock`, none of them in `downloads/SHA256SUMS`. The kit is judge input, hashed, and in `JUDGE_PATHS`, so a change to it is a judge change.
   - **Not in `downloads/SHA256SUMS`.** Every line there becomes a `pin` line in `MANIFEST` (`scripts/assemble_artifacts.py`, the `pins` loop; READ). Test-only wheels there would change the artifact set and make this build-class. The kit is still pinned by URL and SHA-256 and verified before use, as §4.2 asks.
   - **A rules line.** `test_upstream_files_are_well_formed` (Decision 17) checks every `kit.txt` line:
     - 64 hex digits, two spaces, then a `https://files.pythonhosted.org/` URL;
     - the URL's basename is a `py3-none-any` or `py2.py3-none-any` wheel.
   - **Fetching.** `uv run python tests/upstream/fetch.py` downloads each URL to a temporary name in `build/upstream/wheels/`. It renames the file only after its SHA-256 matches; a mismatch deletes it and exits non-zero. The judge never fetches.
   - **Unpacking.** The harness unpacks the wheels with `zipfile`. It refuses an absolute member name and any member with a `..` part (§4.8: downloads are untrusted, even hashed ones). No wheel's code runs natively; it runs only inside the guest.
   - **Licences** (READ, each wheel's metadata):
     - pytest, pluggy, iniconfig: MIT;
     - packaging: Apache-2.0 OR BSD-2-Clause;
     - pygments: BSD-2-Clause;
     - hypothesis: MPL-2.0;
     - sortedcontainers: Apache-2.0.

     None ships in the release or the wheel, so §4.12 does not reach them; the memo records them.

3. **Where the tests come from: the source trees of the artifact's own pins, members only.** Once per judge run, `tests/harness/upstream.py` stages a folder under `build/harness/upstream/<run>/`. Every group and trap check grants it read-only at `/upstream`:

   ```
   /upstream/kit/                     the seven wheels, unpacked
   /upstream/judge/drive.py           tests/upstream/drive.py
   /upstream/judge/numpy.ini          tests/upstream/numpy.ini
   /upstream/judge/pandas.ini         tests/upstream/pandas.ini
   /upstream/judge/<group>.json       each group's argv (Decision 8)
   /upstream/tests/numpy/<pkg>/tests/ the test folders the groups and trap entries name, only
   /upstream/tests/pandas/conftest.py build/pandas-3.0.6/pandas/conftest.py
   /upstream/tests/pandas/tests/<dir> the pandas groups' folders, with pandas/tests/__init__.py
                                        and the conftest.py files on their path
   ```

   - **Tied to the artifact under judgment.** Before staging, the harness reads the artifact's `MANIFEST`. The checks **fail** (they are not blocked) when either of these holds:
     - the `pin` line for `numpy-<v>.tar.gz` or `pandas-<v>.tar.gz` names another file or hash than the tarball the source tree came from (`pins.source_pair`);
     - the `recipe` lines for `recipes/patches/<top>/*.patch` differ from the patches in the repository, which spec 020 proves are the ones the tree carries.

     The failure says which, for example `tests from numpy-2.6.0.tar.gz, artifact built from numpy-2.5.2.tar.gz`. A mismatch is a judge-input error, not missing tooling, so it must not hide as "blocked".
   - **Tarball members only.** The harness reads each tarball's member names once per run. It stages only files whose paths are members, or files a recorded patch creates (read from each patch's `+++ b/` lines whose `---` side is `/dev/null`). Today no recorded patch creates a file: 0001 and spec 051's 0002 change existing files only. Any other file found in a staged folder is left out and listed in `build/progress/latest.json`, so a file a build left in a tree never runs in the guest. The review counted numpy's 493 and pandas' 1,122 test files: all are tarball members today (EXECUTED).
   - **Not a test zip built by the build.** That would be a build step, a new build output and a build-class change, for files the judge can read where they already are.
   - **Not the product's zip.** The zip carries no `tests` folder (0 members, EXECUTED), and must not.
   - **pandas' missing test data.** pandas' sdist ships no `pandas/tests/io/data` (READ, `tar tzf`). Those tests become skips through pandas' own `--no-strict-data-files` (`pandas/conftest.py:106`; Decision 6).

4. **How the guest finds them: the test folders join the product's packages.** numpy and pandas are imported from the product (builtin modules and the zip). Before pytest starts, the driver appends `/upstream/tests/<package path>` to the `__path__` of each package that owns a staged test folder:
   - numpy: `numpy`, `numpy._core`, `numpy.lib`, `numpy.linalg`, `numpy.fft`, `numpy.random`, `numpy.ma`, `numpy.polynomial`, `numpy.matrixlib`, `numpy.testing`;
   - pandas: `pandas`.

   So `numpy.lib.tests`, `numpy._core.tests._locales` and `pandas.tests.extension.base` import from the grant, and nothing of the product is replaced (EXECUTED). Twelve of numpy's thirteen test folders have an `__init__.py`; `_core/tests` has none and imports as a namespace package (READ, corrected from the memo by the review's finding F11).

   - **The guard.** At session end the driver writes one `M <module> <file>` line for every `sys.modules` entry whose `__file__` starts with `/upstream/tests/`. Any module that is neither under a `tests` package nor `pandas.conftest` is a finding: a product module came from the grant. Appending keeps the product's entry first, so this cannot happen today (READ); the guard makes it checked, not assumed.
   - **One test notices the setup.** `test_public_api.py::test_api_importable` finds `numpy.conftest` listed but not importable, because the product carries no `numpy/conftest.py`. This is class `test-only-modules` in Decision 10.

5. **pytest's options in the guest, each with its reason (EXECUTED unless marked).** The driver calls `pytest.main` with exactly these, then the group's own (Decision 8):

   | option | why |
   |---|---|
   | `-p no:faulthandler` | the plugin duplicates stderr's descriptor: `OSError: [Errno 58]` before collection |
   | `--capture=sys` | fd capture duplicates descriptors: `INTERNALERROR> OSError: [Errno 58]` |
   | `-o log_file=/tmp/pytest.log` | the logging plugin's default is `os.devnull`; WASI has no `/dev/null` |
   | `--basetemp=/tmp/pytest` | pytest's default temporary root calls `os.getuid`, which WASI lacks (it exempts win32 and emscripten, not wasi: `_pytest/compat.py:269`, READ); every `tmp_path` test errored |
   | `-p no:cacheprovider` | the cache would be written into the read-only grant; nothing reads it (INFERRED) |
   | `--import-mode=importlib` | no `sys.path` insertion, and numpy's six `test_regression.py` files cannot clash (INFERRED; `prepend` also ran one file) |
   | `--strict-markers --strict-config` | upstream's own `addopts`, both packages (READ); a misspelled marker fails instead of passing; EXECUTED in the revision runs with no configuration error |
   | `--rootdir=/upstream/tests -c /upstream/judge/<pkg>.ini` | node ids are `numpy/…` and `pandas/…`; the configuration is Decision 6's |
   | `-q --tb=no --no-header -rN` | the stream (Decision 11) is the record; the terminal report is not read |

   upstream's other `addopts` are left out: numpy's `-l -ra` and pandas' `--capture=no --durations=30 --junitxml=…`. They shape the terminal report, which nothing reads, or write a file.

   The driver sets `sys.dont_write_bytecode = True` and runs under `python -u`. `/tmp` is in the guest's writable root, as in every judge run: `guest.py`'s root is writable by design. The pytest-on-WASI facts (`getuid`, `/dev/null`) are pytest's to fix. Drafting an upstream note is outside this specification (Scope).

6. **Upstream's own configuration, transcribed; the hypothesis profiles stated.**
   - **numpy.** `tests/upstream/numpy.ini` is numpy 2.5.2's `pytest.ini` `filterwarnings` block (`error` and its ignores; READ), plus `ignore::pytest.PytestAssertRewriteWarning`. That warning comes because the driver imports hypothesis before pytest, so `_hypothesis_globals` cannot be rewritten. With `error` it stopped the run (EXECUTED); pandas' own configuration ignores it.

     The driver registers numpy's markers, as numpy's `conftest.py` does: `slow`, `valgrind_error`, `leaks_references`, `parallel_threads`, `iterations`, `thread_unsafe`. numpy's `conftest.py` itself is not used, because it imports `numpy._core._multiarray_tests`, which the product does not link (READ, line 14).
   - **pandas.** `tests/upstream/pandas.ini` is pandas 3.0.6's `[tool.pytest.ini_options]` (READ): its `markers`, `filterwarnings`, `xfail_strict = true` and `empty_parameter_set_mark`; not its `--junitxml` or `--durations`. pandas' `conftest.py` is used as is. The pandas sessions add `--no-strict-data-files`.
   - **The driver's profile.** The driver registers and loads the hypothesis profile `judge` before pytest starts. It holds numpy's own "np.test() profile" values: `database=None, derandomize=True, deadline=None, print_blob=True`, every health check suppressed.
   - **What each session ends up using:**
     - numpy sessions run under `judge`.
     - pandas sessions run under pandas' own `pandas_ci`, which pandas' `conftest.py` registers and loads (`max_examples=15`, two health checks suppressed; `pandas/conftest.py:206–216`). It is registered while `judge` is current, so it inherits `derandomize=True` and `database=None`. The review saw exactly that at collection's end (EXECUTED: `derandomize=True max_examples=15 database=None`).

     So both packages run their own example counts, derandomized and with no database.
   - **The check of it.** Once collection finishes, the driver writes the active settings into the stream as one line: `P derandomize=<b> database=<repr> max_examples=<n>`. A group whose line shows `derandomize=False` or a database is a finding. With the driver's seeded random and stepped clock, a group's fuel then repeats (Decision 12).

7. **Upstream's own fast selection.** numpy sessions run `-m "not slow"`, `numpy.test()`'s default (`numpy/_pytesttester.py:164`). pandas sessions run `-m "not slow and not network and not db"`, `pandas.test()`'s default (`pandas/util/_tester.py:43`) (both READ). Whatever upstream marks slow, it also leaves out of its own default run. numpy's slow tests cost 705 G of its 1,207 G, for 68 passes (EXECUTED).

8. **The groups, and what is left out.** Each group is one guest session and one check, `test_upstream_suite[<group>]`, so one group's trap or failure never hides another's, and fuel is a metric per group. The harness writes each group's argv into `/upstream/judge/<group>.json` (paths, `--ignore`s, marker), so the guest parses no argument list of its own. Each group's fuel cap is about 1.5 times its drafting fuel, so a runaway ends as "out of fuel", which is a failure (the harness default, 2×10¹¹, is too small for most groups).

   | group | paths | passed (drafting) | fuel (drafting) | passed, spec 051's set | fuel, spec 051's set | cap |
   |---|---|---|---|---|---|---|
   | `numpy-core` | `numpy/_core/tests` | 8,568 | 195.8 G | 9,519 | 203.1 G | 3.1×10¹¹ |
   | `numpy-lib` | `numpy/lib/tests` | 4,823 | 131.4 G | 4,825 | 131.4 G | 2.0×10¹¹ |
   | `numpy-others` | `numpy/{fft,linalg,ma,matrixlib,polynomial,random,testing}/tests`, `numpy/tests` | 7,267 | 174.9 G | 7,269 | 175.3 G | 2.7×10¹¹ |
   | `pandas-frame` | `pandas/tests/frame` | 10,831 | 337.1 G | 10,852 | 344.8 G | 5.2×10¹¹ |
   | `pandas-groupby` | `pandas/tests/groupby` | 22,156 | 460.3 G | 22,227 | 478.7 G | 7.2×10¹¹ |
   | `pandas-reshape` | `pandas/tests/reshape` | 2,657 | 101.2 G | 2,664 | 103.3 G | 1.6×10¹¹ |
   | `pandas-io-parser` | `pandas/tests/io/parser` | 3,401 | 85.8 G | 3,474 | 89.7 G | 1.35×10¹¹ |
   | `pandas-io-formats` | `pandas/tests/io/formats` | 955 | 53.6 G | 976 | 54.4 G | 8.2×10¹⁰ |
   | `pandas-tslibs` | `pandas/tests/tslibs` | 590 | 38.6 G | 590 | 39.0 G | 5.9×10¹⁰ |
   | `pandas-internals` | `pandas/tests/internals` | 258 | 18.1 G | 258 | 18.3 G | 2.8×10¹⁰ |
   | `pandas-libs` | `pandas/tests/libs` | 1,063 | 22.4 G | 1,063 | 23.1 G | 3.5×10¹⁰ |
   | **all** | | **62,569** | **1,619 G** | **63,717** | **1,661 G** | **2.519×10¹²** |

   **Re-derived on spec 051's set** (`s-f94dec535086b06c`, EXECUTED; the landing notes). 051 landed first. Its patch 0002 lets `test_casting_unittests.py` and `test_arraymethod.py` run in `numpy-core` (+951 passes), and its other fixes pass the tests its classes held. Each cap is at least 1.5 times the fuel on 051's set; seven were raised.

   **How the drafting numbers were made.** The numpy numbers came from explicit file lists in the order `sort` gives (`test_hermite_e.py` before `test_hermite.py`). pytest collects a directory in its own order, which puts those two the other way round. The builder's first run on the specified argv sets the baseline. The pass counts must equal the table's; fuel may differ slightly, and the landing notes give both.

   **numpy: all of it that can run.** Every numpy test folder is in a group except three: `f2py` (it compiles extensions), `typing` (it runs mypy) and `_pyinstaller`. Inside the groups, these files are not selected (`--ignore`). Each is named with its reason and closer in `tests/upstream/numpy.toml`:

   | files | reason | closes with |
   |---|---|---|
   | 23 files that import numpy's C test modules (`_core/tests` `test_api`, `test_argparse`, `test_array_coercion`, `test_arrayobject`, `test_arrayprint`, `test_conversion_utils`, `test_cpu_dispatcher`, `test_deprecations`, `test_dtype`, `test_extint128`, `test_getlimits`, `test_hashtable`, `test_indexing`, `test_mem_overlap`, `test_multiarray`, `test_multithreading`, `test_nditer`, `test_numeric`, `test_scalarbuffer`, `test_scalarmath`, `test_ufunc`, `test_umath`; `lib/tests/test_stride_tricks`) | `_multiarray_tests`, `_umath_tests`, `_rational_tests`, `_operand_flag_tests` are not linked (`scripts/gen_inittab.py:27`) | `context/questions-for-the-owner.md` (number 89) |
   | `test_simd.py`, `test_simd_module.py` | `_simd` is not linked | the same |
   | ~~`test_casting_unittests.py`, `test_arraymethod.py`~~ | they trapped the guest (Decision 9); removed on spec 051's set, where they run in `numpy-core` | spec 051 |
   | `test_memmap.py` | every test needs `mmap`, which WASI lacks | `README.md` |
   | `tests/test_ctypeslib.py` | it reads `_multiarray_umath.__file__`, which a builtin module has not | `README.md` |

   The scoreboard's "not machine-checked" line names what this leaves out (Decision 17).

   **pandas: eight groups, chosen for the product and the budget.** pandas' fast mode over all 40 directories costs 3,922 G (EXECUTED). That is about 13 minutes (INFERRED from the drafting machine's rate, Decision 15), too much for a judge that runs on every landing. The eight groups cost 1,117 G:
   - the golden job's path: `io/parser` reads CSV, `io/formats` writes it, and `groupby`;
   - the frame core: `frame`, `reshape`, `internals`;
   - the C layers under them: `libs`, `tslibs`.

   **Left out by budget alone**, with their fast-mode cost: `arithmetic` 489 G, `indexes` 275 G, `extension` 275 G, `arrays` 220 G, `series` 207 G, `window` 176 G, `resample` 116 G, `tseries` 107 G, `indexing` 85 G, `scalar` 79 G, `dtypes` 65 G, `strings` 62 G, `computation` 61 G, `tools` 52 G, `io/json` 41 G, `copy_view` 34 G, `base` 31 G, and smaller ones.

   **Left out by cause:**
   - `io/pytables` stops at `importorskip("tables")`;
   - `io/test_clipboard.py` needs Qt fixtures;
   - `plotting` has no matplotlib in this set;
   - `io/excel` and `io/sas` are all skips.

   None trapped (EXECUTED, full mode). Adding a group is a judge change, with its drafting numbers.

   **The budget (two rules).**
   - **Caps.** The groups' caps and the trap checks' caps (Decision 9) sum to at most 3×10¹². On spec 051's set there is no trap entry, and the groups' caps sum to 2.519×10¹² (before it: 2.47×10¹² + 7 × 5×10¹⁰ = 2.82×10¹²). The rules check enforces it (Decision 17).
   - **Fuel spent.** The fuel the checks actually use stays under 1.8×10¹² (1.661×10¹² on spec 051's set; 1.62×10¹² at drafting). This is a review rule. Each landing's notes sum the group and trap checks' recorded `fuel` metrics and say why if the sum is over.

9. **Tests that trap the guest are deselected, and each is a gap until fixed.** A trap ends the session, so a trapping test cannot run in its group. `tests/upstream/numpy.toml` lists each as a `[[trap]]` entry: a node id or node-id prefix, the reason and the closer.
   - **In the group.** The group passes each entry to pytest as `--deselect` (a prefix deselects every parametrization, EXECUTED). Two whole files are `--ignore`d instead (Decision 8).
   - **The trap check.** `test_upstream_trap[<id>]` runs each entry alone in its own session (cap 5×10¹⁰). It asserts the run completes without a trap. While the defect lasts it fails with one finding, `trap: <cause> at <node>`. The node is the last `S` (test) or `C` (collector) line in the stream with no matching `R` or `X` line. A trap at collection names its collector this way (the review's F5).
   - **The gap.** Each trap check is one gap in `tests/known_gaps.toml`. Its `match` is that one finding's count and digest, and it closes with spec 051, which fixes all four functions. So a different cause, or a trap at another test, is red.
   - **When the fix lands** (condition C1), the trap check passes and its gap is removed, as spec 002 says. The same landing then removes the `[[trap]]` entry, so its tests run in their group again, under the group's classes. That makes the trap check absent, so the landing retires it with `--retire`. The harness reports an accepted `gap` whose check is absent as `absent` too, not only an accepted pass (Decision 19), so `--retire` can take it. A trap entry is not kept as a guard: once its tests are back in the group, the group guards them, and any new trap fails the group.

   | id | node id (prefix) or file | the C function (numpy 2.5.2, READ) |
   |---|---|---|
   | `castingimpl-casting-unittests` | `numpy/_core/tests/test_casting_unittests.py` | `_get_castingimpl(module, args)`, `convert_datatype.c:248`, registered `METH_VARARGS \| METH_KEYWORDS` |
   | `castingimpl-arraymethod` | `numpy/_core/tests/test_arraymethod.py` | the same (INFERRED from frame 0 `cfunction_call`, at collection; the builder records frame 0 from `trap_cause` and marks it EXECUTED) |
   | `castingimpl-stringdtype` | `numpy/_core/tests/test_stringdtype.py::test_cast_method_names` | the same |
   | `descr-set-records` | `numpy/_core/tests/test_records.py::TestRecord::test_assign_dtype_attribute` | `array_descr_set(self, arg)`, `getset.c:388`, a setter |
   | `descr-set-stringdtype` | `numpy/_core/tests/test_stringdtype.py::test_view_distinct_instance` | the same |
   | `gentype-copy` | `numpy/_core/tests/test_regression.py::TestRegression::test_scalar_copy` | `gentype___copy__(self)`, `scalartypes.c.src:2128`, `METH_NOARGS` |
   | `sfloat-reduce` | `numpy/_core/tests/test_custom_dtypes.py::TestSFloat::test_np_save_load` | `sfloat___reduce__(self)`, `_scaled_float_dtype.c:192`, `METH_NOARGS` |

   With the traps deselected, the `numpy-core` group ran to its end (EXECUTED).

   **On spec 051's set none of the seven traps** (EXECUTED: each entry alone ran with no trap). As condition C1 says, the entries, their gaps and the `not_selected` line for the two files are deleted, and their tests run in `numpy-core`. The trap check is defined only while an entry exists, so today there is none; the mechanism stays for the next trap. `tests/upstream/pandas.toml` has no trap entry: pandas trapped nowhere, in full mode (EXECUTED).

10. **Known failures are classes, each one gap, listed by node id.** A test that runs and fails for a known reason belongs to a class. It is never admitted by an `xfail` marker. Each class is admitted the way spec 002 admits every known failure: as a gap with its closer, on the scoreboard (the review's F1).
    - **Definition.** A class is an `[[expected]]` entry in the package's TOML: `id`, `group`, `outcome` (`failed` or `error`), `match` (a regular expression searched in the one-line reason), `reason`, `closes_with`.
    - **Its members.** They are listed, one sorted node id per line, in `tests/upstream/expected/<group>/<class>.txt` (100 lines on spec 051's set; 268 before it). A `git diff` of a list shows exactly which tests were admitted or released (the review's F3).
    - **Sorting.** The group's run sorts each failed or errored test into the first class of its group whose `outcome` and `match` fit.
    - **The group check, `test_upstream_suite[<group>]`.** It passes when every failure and error falls in a class, and the protocol holds. Its findings are:
      - a failure no class takes: `unexpected <outcome> <node id> — <reason>`;
      - a collection error;
      - an `INTERNALERROR`;
      - a pytest exit code other than 0 or 1;
      - a missing `E` line;
      - a trap, or "out of fuel";
      - the profile (Decision 6) or the module guard (Decision 4) failing.

      None of these is ever admitted by a class. The group check passes only when nothing is unknown, so it admits nothing by itself.
    - **The class check, `test_upstream_class[<group>-<class>]`.** It reads the group's result through a session cache, so the guest runs once per group per judge run. It compares the class's actual members with its list file:
      - **The list is exact.** The check fails with one finding per member, the node id itself. Its gap admits exactly that set by count and digest (spec 002, Decision 4).
      - **The list is wrong.** The findings also name each id added (`+<node id>`) and removed (`-<node id>`). So the digest no longer matches the gap, and the check is red with the names in its message. The fix edits the list and the gap together; the review sees the names.
      - **The class is empty** (condition C1). The check passes, and its gap fails with spec 002's "remove the gap". The fix removes the gap and **keeps the class**, with an empty list file, as a passing check: the scoreboard shows gap → pass. The class keeps guarding. If the same failure comes back, it shows as `+<node id>` and the check is red. A class is deleted only when its `match` can no longer occur, for example after a re-pin; that is a judge change with `--retire`.
    - **What it gives.** The scoreboard shows each class as a gap under its closer, in `gaps close with:` and in `next:`. A fix lands as spec 002 says every fix lands: a gap becomes a pass. pass, skip, `xfail` and non-strict `xpass` are upstream's own outcomes, not class members. pandas' strict `xpass` arrives as `failed` with `[XPASS(strict)]` and needs a class if it occurs.

    The classes the drafting runs found, by group (EXECUTED; the review recounted each with these expressions, EXECUTED). The builder writes each list from the first run on the frozen set, and the review compares the lists with these counts:

    | group | class | outcome | count | match | closes with |
    |---|---|---|---|---|---|
    | `numpy-core` | `no-dup` | failed | 8 | `OSError: \[Errno 58\] Not supported` | `README.md` |
    | `numpy-core` | `no-dup-file-left-open` | error | 3 | `PytestUnraisableExceptionWarning: Exception ignored while finalizing file` | `README.md` |
    | `numpy-core` | `no-processes` | failed | 3 | `wasi does not support processes` | `README.md` |
    | `numpy-core` | `test-only-modules` | failed | 1 | `No module named 'numpy\._core\._rational_tests'` | `context/questions-for-the-owner.md` |
    | `numpy-lib` | `no-mmap` | failed | 5 | `mmap is unavailable` | `README.md` |
    | `numpy-lib` | `no-dev-null` | failed | 1 | `No such file or directory: '/dev/null'` | `README.md` |
    | `numpy-lib` | `patch-0001-truncated-message` | failed | 1 | `Regex pattern did not match` | spec 051 |
    | `numpy-others` | `no-ctypes` | failed | 8 | `ctypes is unavailable` | `README.md` |
    | `numpy-others` | `patch-0001-masked-save` | failed | 1 | `DID NOT RAISE <class 'NotImplementedError'>` | spec 051 |
    | `numpy-others` | `test-only-modules` | failed | 2 | `not really public but looked public\|has no attribute '_multiarray_tests'` | `context/questions-for-the-owner.md` |
    | `numpy-others` | `zip-code-names` | failed | 1 | `^AssertionError: ?$` | spec 051 |
    | `pandas-frame` | `zip-code-names` | failed | 21 | `Warning not set with correct stacklevel` | spec 051 |
    | `pandas-groupby` | `zip-code-names` | failed | 71 | the same | spec 051 |
    | `pandas-reshape` | `zip-code-names` | failed | 7 | the same | spec 051 |
    | `pandas-io-parser` | `zip-code-names` | failed | 73 | the same | spec 051 |
    | `pandas-io-parser` | `no-mmap` | failed | 40 | `mmap is unavailable` | `README.md` |
    | `pandas-io-formats` | `zip-code-names` | failed | 21 | `Warning not set with correct stacklevel` | spec 051 |
    | `pandas-tslibs` | `no-processes` | failed | 1 | `wasi does not support processes` | `README.md` |

    That is 18 classes and 18 gaps. numpy has 31 failed and 3 errors; pandas has 234 failed.

    **What the classes are on spec 051's set** (EXECUTED; the landing notes):
    - the build review's F5 split `numpy-others` `test-only-modules`: `test_api_importable` (`numpy.conftest`, which the zip does not carry) is class `no-conftest`, closed by the README; `test-only-modules` keeps `test_NPY_NO_EXPORT` (question 89);
    - 051 empties the six `zip-code-names` classes and the two `patch-0001-*` classes; by condition C1 they stay, with empty lists and no gaps, as passing checks;
    - the two returning files fail 28 tests with `ctypes is unavailable`: a new class, `numpy-core` `no-ctypes`, closed by the README.

    So there are 20 classes: 12 with members and gaps (100 node ids; the README closes 10, question 89 closes 2) and 8 empty. numpy has 56 failed and 3 errors; pandas has 41 failed. A generic `match` (the bare `AssertionError: `) is safe: any other test that fails that way joins the class, shows as `+<node id>`, and turns red. **Closers:**
    - `README.md` closes only a fact the README states (a permanent platform fact). The README gains the one it lacks, `/dev/null` (Decision 18).
    - Spec 051 closes the defects it fixes. If 051 is not yet in the repository when this is built, the memo stands in, and 051 moves the closers when it lands.
    - The flaky-looking `no-dup-file-left-open` errors are unraisable-exception reports, which pytest attaches to whichever test runs when the file is collected. Its list names the three `test_fromfile*` nodes; if another test's change moves them, the `+`/`-` lines show it.

11. **The outcome stream.** The driver writes `/tmp/upstream/outcomes.txt` in the guest's writable root, flushing every line:

    | line | written when |
    |---|---|
    | `C <collector node id>` | a collector starts (`pytest_collectstart`) |
    | `S <node id>` | a test starts |
    | `R <outcome> <node id> -- <reason>` | every outcome, passes included; the reason is the crash message's first line, or a skip's reason, at most 200 characters, newlines replaced |
    | `X <node id> -- <reason>` | a collection error |
    | `P derandomize=… database=… max_examples=…` | collection ends (Decision 6) |
    | `M <module> <file>` | at session end, for each module from `/upstream/tests/` (Decision 4) |
    | `E <pytest exit code>` | last |

    The host reads the file from the run's root after the guest returns, so nothing depends on the guest's stdout buffering or size. On a trap, the last `S` or `C` line with no `R` or `X` line names the test or collector that trapped. The reason is the class's input, so it never contains host paths: the grant's paths are guest paths (`/upstream/…`).

12. **Metrics: fuel per group, and a pass count with its own ratchet and flag.**
    - **Fuel.** Each group check records `fuel`, and the ratchet's 0.01% applies. The drafting runs repeated within 221 instructions in 131 G and 68 in 101 G, and the review's pair to the instruction (EXECUTED).
    - **Passes.** Each group check records a new metric, **`passes`**: the number of `R passed` lines. The harness learns it as follows (the review's F2):
      - **Recording.** `metric("passes", n)` is allowed (`plugin.py`).
      - **A fall.** In the ratchet (`scoreboard.py`), a `passes` value below the accepted one on the same platform goes to its own list, `fewer`, not to `growth`. It is red. It prints as `FEWER <node>: passes <old> -> <new>`, before any `GREW` line, and is never cut.
      - **A rise.** A higher value goes to its own reported list, `more`. It is not in `gained`, which counts checks.
      - **Accepting a fall.** It needs its own flag, `--accept-fewer-passes "<why>"`. The reason is recorded in its own `history.jsonl` field, `fewer_reason`. `--accept-growth` does not accept it: one unrelated growth must not carry a lost pass.
      - **Without the flag,** acceptance keeps the maximum of the old and new values. With it, the new value is kept.
    - **A substitution.** A count cannot see one test move from pass to skip while another moves from skip to pass. So each group also records `passed_digest`, the 12 hex digits of the sorted passing ids, in `build/progress/latest.json`. It is reported, not ratcheted. What this decision promises is that **no fall in the number of passes goes unaccepted** (the review's F12).
    - **Documentation.** `context/progress/README.md` documents the metric, the list and the flag.

13. **The needs, and acceptance with these checks unrun.** The group, class and trap checks call `need("snapshot binary", "stdlib zip", "manifest", "wasmtime-py", "source tree numpy" or "source tree pandas", "upstream kit")`.
    - **The new need.** `upstream kit` is new (`needs.py`): it is met when every file of `tests/upstream/kit.txt` is in `build/upstream/wheels/` with its SHA-256. This specification provides it.
    - **Local tooling, not protected.** Like `oracle` and the source trees, it is local tooling: an accepted pass blocked by it is "unrun locally", reported, not red (spec 002, Decision 6). So a run without the kit, such as the release workflow's, stays green.
    - **But not at acceptance** (the review's F9). `--accept` refuses while any check in `tests/checks/test_v1_3_upstream_suites.py` that has an accepted pass or gap is unrun locally, unless `--partial "<why>"` is given. `--partial` prints on the scoreboard and is recorded. Without this, the lane could accept a change that breaks what the suites catch, on a machine that lost `build/upstream/wheels/`, and keep the old `passes`. This is a judge change only (`scoreboard.py`), not a `scripts/` change.
    - **The lane rule** in `context/progress/README.md`: the landing notes cite the scoreboard's ratchet line showing `unrun locally 0`.
    - **A MANIFEST mismatch fails** (Decision 3); it is never a need.

14. **The trap's cause, kept.** `guest.Result.trapped` keeps today's first line, and `Result` gains `trap_cause`: the text after the trap message's `Caused by:` line (`wasm trap: indirect call type mismatch`), or `None`. Today's first line is "error while executing at wasm backtrace:" for every such trap (EXECUTED), which cannot tell one cause from another.

15. **Marked `slow`, in the full judge.** The group, class and trap checks are `slow`, like the golden jobs. `uv run pytest -m "not slow"` skips them; the full `uv run pytest`, and so the lane, runs them. The release dry run does not run them: its workflow is not changed (Scope).
    - **The cost** (a benchmark fact, the review's F15). On the drafting machine, the numpy `lib` group took 25.4 s and pandas `reshape` 30.7 s, compile included: about 5 G fuel a second. So the 1.62 T is about six minutes (INFERRED). The lane's last full judges took 180 s, 239 s and 538 s, so the full judge roughly doubles.
    - **The landing notes** record the full judge's time before and after.
    - **The knob** if it is too much is the pandas groups, never the strictness.

16. **Not build-class.**
    - **What it does not touch:** no file under `scripts/` or `recipes/`, no line of `downloads/SHA256SUMS`, no release workflow, no rebuild.
    - **What it is:** a judge change. Every new and changed file is under `tests/`, or is documentation (`context/progress/README.md`, `AGENTS.md`, spec 002's amendment lines, the README, the CHANGELOG, the memo's correction). So acceptance takes `--accept-judge`.

17. **The rules check, and what the scoreboard says it does not check.** `test_upstream_files_are_well_formed` (rules, fast) checks:
    - every `kit.txt` line (Decision 2);
    - every `closes_with` exists;
    - every class has a list file, sorted and unique; a non-empty list has exactly one gap entry in `known_gaps.toml`, and an empty list has none (condition C1);
    - every trap entry has its gap;
    - ids are unique per group;
    - every group's paths and every `not_selected` and `trap` file are tarball members, when the need is met;
    - the caps' sum is at most 3×10¹² (Decision 8).

    The scoreboard's "not machine-checked" line drops "numpy/pandas test subsets". It gains "numpy's 25 files that need its C test modules (number 89) · pandas beyond eight groups", so the line says exactly what is left.

18. **What the README and the CHANGELOG say.**
    - **README, the platform paragraph,** gains "no `/dev/null`" (`os.devnull` names a path that does not exist).
    - **README, a short "Known defects" list,** until each closes. Spec 051 closed all three (the traps, pandas' warnings, the masked-array save), so on its set the list is gone.
    - **README, "Measured,"** gains a row: numpy's and pandas' own tests, 63,717 passing in the guest on spec 051's set (the accepted count), and 12 gaps.
    - **CHANGELOG:** one line under the next alpha's "Judge" heading.

19. **Spec 002, amended by dated lines, as spec 029 amended its Decision 5.** Spec 002's states (Decision 3) and gaps (Decision 4) are not changed: the classes and traps are ordinary gaps. The amendment lines say this:
    - **Decision 5 (needs):** the need `upstream kit`, provided by spec 050.
    - **Decisions 6 and 7 (ratchet, acceptance):**
      - the `fewer` and `more` lists;
      - `--accept-fewer-passes` and its `history.jsonl` field `fewer_reason`;
      - the refusal to accept with these checks unrun locally unless `--partial`;
      - an accepted `gap` whose check is absent from a run that collected its whole file is reported `absent`, as an accepted pass is, so `--retire` can take it (condition C1).
    - **Decision 8 (metrics):** `passes`, which must not fall; acceptance keeps the maximum.
    - **Decision 17 (not machine-checked):** the line's new text.

    `AGENTS.md` rule 4 names `tests/upstream/*.toml` and `tests/upstream/expected/` beside `tests/known_gaps.toml`, as files the judge's acceptance must justify. So does `context/progress/README.md`.

20. **How the builder runs the groups in a worktree** (the review's F7). In a worktree outside the repository (§4.14), `paths.BUILD` and `paths.DOWNLOADS` are the worktree's own, so the source-tree needs are unmet and every check here would be blocked. The builder therefore, before judging:
    - **Links the inputs.** It makes read-only links in the worktree to the main tree's `downloads/numpy-2.5.2.tar.gz`, `downloads/pandas-3.0.6.tar.gz`, `build/numpy-2.5.2` and `build/pandas-3.0.6`.
    - **Fetches the kit.** It runs `uv run python tests/upstream/fetch.py` in the worktree, or links `build/upstream/wheels`.
    - **Points at the frozen set.** It sets `WASI_PYTHON_ARTIFACTS` to the frozen set its class allows (rule 6a).

    It confirms that the judge's conftest walk and `dirty_path` ignore the links (`build/` and `downloads/` are in `NOT_SOURCE`; READ). Its landing notes record the scoreboard line showing the checks ran (on spec 051's set 32: 11 groups, 20 classes, 1 rule). Criteria 2, 3 and 7 are run there, and the lane re-runs them in the main tree.

## Intent

The judge runs numpy's and pandas' own tests inside the guest and counts every pass. It shows every known failure as a gap with what will close it, listed by node id. It turns red when a pass is lost, a failure appears, or a known failure goes away unrecorded.

## Design

```
tests/upstream/kit.txt               the seven wheels: "<sha256>  <url>" (Decision 2)
tests/upstream/fetch.py              downloads the kit into build/upstream/wheels/ (temporary name,
                                       renamed after the hash matches); never run by the judge
tests/upstream/drive.py              guest side: kit on sys.path; test folders on the packages'
                                       __path__ (Decision 4); hypothesis profile `judge`; markers;
                                       pytest.main with Decision 5's options and the group's JSON;
                                       the outcome stream (Decision 11)
tests/upstream/numpy.ini             numpy's pytest.ini filterwarnings, plus one ignore (Decision 6)
tests/upstream/pandas.ini            pandas' [tool.pytest.ini_options], less junit and durations
tests/upstream/numpy.toml            marker; packages for __path__; [groups.<name>] paths and fuel
                                       caps; [[not_selected]]; [[trap]]; [[expected]]
tests/upstream/pandas.toml           the same for pandas (no trap entries)
tests/upstream/expected/<group>/<class>.txt
                                     each class's sorted node ids (Decision 10)
tests/harness/upstream.py            load and validate the TOML; the MANIFEST tie and the member
                                       filter; stage /upstream once per run (Decision 3); run a
                                       group through guest.run with a read-only grant; parse the
                                       stream; sort into classes; findings; passes; a session
                                       cache of group results
tests/harness/guest.py               Result.trap_cause (Decision 14)
tests/harness/needs.py               the need "upstream kit"
tests/harness/plugin.py              metric("passes", n) allowed; --accept-fewer-passes
tests/harness/scoreboard.py          the fewer and more lists; FEWER lines; accept keeps the
                                       maximum unless the flag; fewer_reason; refusal when these
                                       checks are unrun locally; NOT_MACHINE_CHECKED's new text
tests/checks/test_v1_3_upstream_suites.py
                                     test_upstream_suite[<group>] (11, slow)
                                     test_upstream_class[<group>-<class>] (20, slow; 12 gaps)
                                     test_upstream_trap[<id>] (slow; defined only while a
                                       [[trap]] entry exists: none on spec 051's set)
                                     test_upstream_files_are_well_formed (rules, fast)
tests/known_gaps.toml                12 entries: the classes with members
tests/unit/test_upstream.py          the stream parser, the sorting, the class lists' +/- findings,
                                       the trap node from S or C lines, the MANIFEST tie, the member
                                       filter, the safe unzip, the argv, on fixed inputs; no guest
tests/unit/test_scoreboard.py        the passes metric, FEWER, the flag, the refusal (criterion 6)
context/progress/README.md, AGENTS.md, spec 002 (amendment lines), README.md, CHANGELOG.md
context/research/2026-10-18-numpy-and-pandas-own-tests-in-the-guest.md
                                     a dated correction (the __init__.py sentence; the driver file)
```

**A group's run, in order:**
1. Stage `/upstream` once per judge run, after the MANIFEST tie.
2. Build the argv: `-u /upstream/judge/drive.py <package> <group>`.
3. Run it: `guest.run(snapshot, argv, workdir, stdlib, env={"TMPDIR": "/tmp", "HOME": "/tmp"}, fuel=<cap>, preopens=[("/upstream", <stage>, False)])`.
4. Read the stream.
5. Sort the failures into classes.
6. Record `fuel` and `passes`.
7. Cache the result for the group's class checks.
8. Assert no finding.

## Scope

In:
- numpy's test folders, as Decision 8 groups them, and the eight pandas groups;
- the test kit, pinned and fetched by the judge;
- the trap entries and their gaps;
- the classes, their lists and their gaps;
- the `passes` metric, its list and its flag;
- the need and the acceptance refusal;
- README, CHANGELOG, AGENTS.md rule 4, spec 002's amendment lines, and the memo's correction.

Out:
- **Fixing what the suites found.** Spec 051 fixes the four C signatures (with two more its scan found), the zip's code names and patch 0001's behaviours.
- **numpy's C test modules** and the 25 files that need them: the owner's (number 89).
- **The plain binary** (Decision 1).
- **The rest of pandas** (2.8 T fuel in fast mode) **and numpy's slow tests:** left out by budget. Each can be added later as a judge change with its numbers.
- **The release workflow.** These checks are blocked there, since the kit and the source trees are absent. Before a release, someone should confirm that `history.jsonl` holds an accepted run of these checks on the release's artifact hash, as `three systems` does for platforms. Making that a rule is a later, build-class change to the release rules. This specification only records it, in `context/progress/README.md`. (Amended: spec 063 makes it the rule; the release runs these checks in shards and its gather ties them to the lane's acceptance.)
- **Other packages' suites** (matplotlib, scipy, tier A). Each package's own specification may add groups through this mechanism once it lands.
- **Upstream notes** to pytest about `getuid` and `/dev/null` on WASI.
- **Wall-clock.** No check reads a clock (§4.9). The six minutes are a benchmark fact.

## Acceptance criteria

1. **Fetching the kit.**
   - `uv run python tests/upstream/fetch.py` fetches the seven wheels into `build/upstream/wheels/`, and each SHA-256 equals its `kit.txt` line.
   - A wheel with one byte changed makes the need `upstream kit` unmet. A unit check shows it on a scratch copy.
   - A member named `../x` or `/x` is refused by the unzip, also shown by a unit check.
   - The judge never opens the network.
2. **Seen failing first.** The builder runs the 11 group checks on the frozen set before writing any class, list, trap entry or gap. They fail with the drafting runs' findings:
   - numpy: 31 failed and 3 errors;
   - pandas: 234 failed;
   - `numpy-core`: a trap while its trap entries are absent.

   The builder records the counts and compares them with Decision 10's table. Any difference is explained in the landing notes before a class is written.
3. **With the TOML, the lists and the gaps complete,** the run on the frozen set gives:
   - 11 groups `pass`; the classes with members `gap` (12 on spec 051's set), the emptied ones `pass` (8); every trap `gap` (none on spec 051's set);
   - `passes` per group equal to Decision 8's table (63,717 in all on spec 051's set; 62,569 before it). Any difference is explained in the landing notes; the guest is the same bytes on every host, so a host is not an explanation.
   - each pandas group's `P` line shows `derandomize=True database=None max_examples=15`, and each numpy group's shows `derandomize=True database=None`;
   - no `M` line names a product module.
4. **Traps.** (On spec 051's set there is none; this held on the set before it.) Every `test_upstream_trap[<id>]` fails with exactly one finding, `trap: wasm trap: indirect call type mismatch at <node>`, admitted by its gap. The node of `castingimpl-arraymethod` is its collector (a `C` line). Unit checks show three things:
   - a stream that ends after a `C` line names that collector;
   - an entry whose test now passes makes the check pass, and its gap "remove the gap";
   - a different cause is a different finding;
   - an emptied class with its list file emptied and its gap removed passes, and a returning failure shows as `+<node id>` (condition C1).
5. **Strictness, shown on fixed streams** (`tests/unit/test_upstream.py`):
   - a class with one more member than its list fails with `+<node id>`, and with one fewer with `-<node id>`, so its gap's digest no longer matches;
   - a failure no class takes is a group finding;
   - a collection error, exit code 2 to 5, a missing `E` line, a trap and "out of fuel" are group findings;
   - a `P` line with `derandomize=False` is a group finding;
   - skips, `xfail` and non-strict `xpass` are not findings.
6. **The `passes` metric** (unit checks on the ratchet):
   - a value below the accepted one is red, in `fewer`, printed `FEWER <node>: passes <old> -> <new>` before any `GREW` line;
   - `--accept-fewer-passes` accepts it and records `fewer_reason`;
   - **in a run with fuel growth and a fall in passes, `--accept-growth` alone is refused;**
   - without the flag, acceptance keeps the maximum;
   - a higher value is in `more`, not in `gained`;
   - `metric("passes", …)` is accepted, and an unknown name still raises;
   - `--accept` with an accepted upstream check unrun locally is refused unless `--partial`.
7. **Fuel repeats.** The builder runs each group twice in one session; this is a one-off check by the builder, not a judge check. The two fuel values are within 0.01%, and the landing notes give both for every group. The notes also sum the group and trap checks' fuel against the 1.8×10¹² budget.
8. `test_upstream_files_are_well_formed` passes, with every rule Decision 17 lists. The caps sum to at most 3×10¹².
   - **Unit checks:** an empty list with no gap passes the rule; an empty list with a gap, and a non-empty list without one, each fail it (condition C1).
   - **A scoreboard unit check:** an accepted `gap` whose check is absent is reported `absent`, and `--retire` accepts it.
9. **The tests are the artifact's, and cannot change it.** Unit checks show:
   - a `MANIFEST` whose numpy `pin` or patch `recipe` line differs from the tree's tarball or patches makes the checks fail (not blocked), naming both;
   - a stray file in a scratch tree's test folder is not staged, and is listed;
   - the preopens built for a group grant `/upstream` read-only.

   The change has no file under `scripts/`, `recipes/`, `downloads/` or `.github/` (`git diff --stat`).
10. **The full judge.** `uv run ruff check`, `uv run ruff format --check` and `uv run pytest` are green, with `--accept-judge` naming the new checks, the lists, the gaps and the harness changes.
    - **Ratchet against the base:** lost 0, grew 0, fewer 0. No existing check's fuel moves: the harness changes record, they do not run the guest differently.
    - **Gained:** 20 on spec 051's set (11 groups, 8 emptied classes and the rule; 12 before it). The 12 gaps are on the scoreboard under their closers.
    - **Unrun locally:** 0.
    - **The tail:** the scoreboard's last lines carry Decision 17's new "not machine-checked" text.
    - **The time:** the landing notes give the full judge's time before and after (Decision 15).

## The owner's choices

None open here. Every choice this specification needs is decided above (§5.2). One choice is the owner's, number 89 in `../questions-for-the-owner.md`, because it would add a build output: whether to reach numpy's 25 core test files that need its C test modules, and how. The options are:
- a judge-only binary, built beside the product and never published (the agent's recommendation, as a later build-class specification);
- linking the modules into the product;
- neither.

This specification builds without an answer: those files are `not_selected`, closed by number 89. The time the full judge takes is the owner's to weigh (Decision 15), and the pandas groups are the knob.

## Landing notes

The current numbers are spec 051's set's, in the last section ("Rebased onto spec 051 and re-derived on its set"). The sections before it record the build and its review on the set before 051 (`s-0cdc7b2bd78db6f5`), and keep that set's counts.

Built 2026-10-18 by the builder (Claude Opus 5.5) in the worktree `wasi_python-050`, branch `spec/050-upstream-tests`, against the frozen set `s-0cdc7b2bd78db6f5`. Not yet reviewed; the review goes under `context/reviews/` and is cited here before the lane lands it. Every number below is EXECUTED unless marked.

**Setup (Decision 20).** Read-only symbolic links in the worktree to the main tree's `downloads/numpy-2.5.2.tar.gz`, `downloads/pandas-3.0.6.tar.gz`, `build/numpy-2.5.2` and `build/pandas-3.0.6`; the kit fetched with `uv run python tests/upstream/fetch.py` (seven wheels, each `shasum -a 256` equal to its `kit.txt` line); `WASI_PYTHON_ARTIFACTS` set to the frozen set. The links are ignored by git and by the judge: `build/` and `downloads/` are in `NOT_SOURCE` (READ), and the run record's 97 judge files hold no `build/` or `downloads/` path. Nothing in the main tree was written.

**What changed.** As the Design lists, with these builder details:
- `tests/upstream/pandas.toml` has a `support` list: files staged for import but never collected. It holds `pandas/conftest.py` and three files of `pandas/tests/extension/` (`__init__.py`, `decimal/__init__.py`, `decimal/array.py`), because `groupby/aggregate/test_other.py` and `reshape/concat/test_concat.py` import `pandas.tests.extension.decimal` (READ). Without them one test fails and one file does not collect. They are tarball members, and the rules check says so.
- The two ini files transcribe upstream's configuration in full (numpy's `filterwarnings` block, pandas' four keys), including the lines the drafting prototype left out (numpy's matplotlib and `_pack_` ignores; pandas' `error::pytest.PytestWarning` and its later ignores). The outcomes equal the drafting runs' exactly (below), so none of those lines changed a result.
- A trap entry that names a whole file is `--ignore`d in its group, one with `::` is `--deselect`ed. A trap check runs its entry with no marker expression, so a `slow` mark could not hide it.
- The trapped node is the last `S` or `C` line of the stream. An `S` line's `R` lines do not close it, so a trap in a test's teardown still names that test.
- `plugin.py` gains a `fact(name, value)` fixture: facts on a check's record in `build/progress/latest.json`, under `facts`, never ratcheted (named `fact`, not `note`, since spec 051's `note(text)` landed first). Each group records `passed_digest`, its outcome counts and `left_out` (the staged folders' files that are not tarball members: none today).
- The reviewer's builder note is followed: an accepted `gap` whose check is absent is its own branch beside the accepted-pass case in `scoreboard.compare`, so a vanished gap is `absent`, never `lost`.
- `--accept`'s refusal counts any accepted pass or gap in the upstream file that did not run here, whether blocked, deselected, unrun or outside the run (`upstream unrun` on the ratchet line).

**Seen failing first (criterion 2).** The 11 groups, run one at a time through the harness's own `Session` before any class, list, trap entry or gap existed (`build/upstream-first/`):
- `numpy-core` trapped, as the criterion says: `trap: wasm trap: indirect call type mismatch at numpy/_core/tests/test_custom_dtypes.py::TestSFloat::test_np_save_load`, after 75 passed and 3 failed (fuel 41,964,185,383).
- `numpy-lib` 7 failed, `numpy-others` 12 failed. Every node and outcome equals `numpy-fast-nonpass.txt` (0 differences).
- pandas: frame 21, groupby 71, reshape 7, io-parser 113, io-formats 21, tslibs 1, internals 0, libs 0 failed: 234. The 234 `<outcome> <node>` lines equal `pandas-chosen-nonpass.txt` exactly.
- With the seven trap entries written, `numpy-core` ran to its end: 8,568 passed, 12 failed and 3 errors. So numpy has 31 failed and 3 errors, as Decision 10 says.

Every class count then equals Decision 10's table (8, 3, 3, 1; 5, 1, 1; 8, 1, 2, 1; 21, 71, 7, 73, 40, 21, 1), with no failure left over. The lists hold 268 node ids.

**Traps (criterion 4).** Each entry alone, in its own session, ends in `wasm trap: indirect call type mismatch`:
- `castingimpl-casting-unittests` at `test_casting_unittests.py::TestCasting::test_simple_cancast[BoolDType]`;
- `castingimpl-arraymethod` at its collector, `numpy/_core/tests/test_arraymethod.py` (a `C` line). Frame 0 is `cfunction_call` (EXECUTED: the full trap message, printed by a scratch script), the same caller as `_get_castingimpl`'s other traps, so Decision 9's INFERRED cause now stands EXECUTED;
- the other five at the node ids of Decision 9's table (`test_assign_dtype_attribute[0]` for the records entry).

Each check fails with exactly one finding and is a gap closed by spec 051.

**The judge's run (criteria 3, 8, 10).** `uv run ruff check` and `uv run ruff format --check` clean. `WASI_PYTHON_ARTIFACTS=…/s-0cdc7b2bd78db6f5 uv run pytest`, the full judge, exit 0:

```
wasi_python v1: 250/284 pass · 25 gap · 9 blocked · 0 fail   (unit suite 924/932, 8 skipped)
  v1.3  data stack          31/57  gap 25 blocked 1
  rules constitution rules  23/24  blocked 1
gaps close with: 051-what-the-upstream-tests-found 15 · README 8 · questions-for-the-owner 2
next: context/specifications/051-what-the-upstream-tests-found.md (unblocks 0, closes 15)
ratchet vs 361775dd62: lost 0 · absent 0 · unrun 0 · unrun locally 7 · gained 12 · grew 0 · judge changed: … and 33 more
not machine-checked: publication · copying from prior art · numpy's 25 files that need its C test modules (number 89) · pandas beyond eight groups
1175 passed, 17 skipped, 25 xfailed in 511.40s (0:08:31)
```

- The 37 checks ran: 11 groups and the rule `pass`, 18 classes and 7 traps `gap`.
- Ratchet against main's accepted state: lost 0, grew 0, no `FEWER`, gained 12 (11 groups and the rule). No existing check's fuel moved.
- `unrun locally 7` is this worktree's local tooling: the oracle and the cpython, zlib, bzip2, xz and sqlite trees, which it does not link. None is an upstream check. The lane's run in the main tree must show `unrun locally` absent (criterion 10), and `--accept` refuses otherwise.
- Every group's `P` line: numpy `derandomize=True database=None max_examples=100`, pandas `derandomize=True database=None max_examples=15`. No `M` line names a product module: pandas' sessions load `pandas.conftest` and `tests` modules only.

**Passes and fuel per group (criteria 3 and 7).** Passes equal Decision 8's table in every group, 62,569 in all. Fuel, three times with the final stage: the judge's run, then each group twice in one scratch session through the same `Session`:

| group | passes | fuel, judge | fuel, session run 1 | fuel, session run 2 | 1 vs 2 | most apart, ppm |
|---|---|---|---|---|---|---|
| `numpy-core` | 8,568 | 194,253,054,091 | 194,253,091,032 | 194,253,111,993 | 20,961 | 0.30 |
| `numpy-lib` | 4,823 | 131,291,228,156 | 131,291,256,682 | 131,291,256,682 | 0 | 0.22 |
| `numpy-others` | 7,267 | 175,318,947,857 | 175,318,959,281 | 175,318,959,281 | 0 | 0.07 |
| `pandas-frame` | 10,831 | 344,546,610,939 | 344,546,631,033 | 344,546,631,101 | 68 | 0.06 |
| `pandas-groupby` | 22,156 | 474,701,025,317 | 474,701,015,287 | 474,701,015,287 | 0 | 0.02 |
| `pandas-reshape` | 2,657 | 103,013,881,395 | 103,013,883,469 | 103,013,883,469 | 0 | 0.02 |
| `pandas-io-parser` | 3,401 | 88,662,885,049 | 88,662,916,159 | 88,662,916,210 | 51 | 0.35 |
| `pandas-io-formats` | 955 | 54,405,022,973 | 54,405,027,359 | 54,405,027,478 | 119 | 0.08 |
| `pandas-tslibs` | 590 | 38,949,118,319 | 38,949,117,180 | 38,949,098,990 | 18,190 | 0.50 |
| `pandas-internals` | 258 | 18,265,292,986 | 18,265,293,054 | 18,265,293,292 | 238 | 0.02 |
| `pandas-libs` | 1,063 | 23,059,933,239 | 23,059,931,845 | 23,059,931,862 | 17 | 0.06 |
| **all** | **62,569** | **1,646,467,000,321** | | | | |

Every pair is within 0.5 parts in a million, far inside the ratchet's 0.01% (100 ppm). Fuel differs from the drafting runs by up to 0.6% (`pandas-libs` 23.06 G against 22.45 G): a different driver (the stream goes to a file, `C`, `P` and `M` lines) and a different grant. As Decision 8 says, the first run on the specified argv sets the baseline.

**A failure mode found, and fixed before it could come back.** The first judge run staged each package when its first check asked. Its fuel then disagreed with the scratch runs by up to 320 ppm (`pandas-tslibs`, 38,949,117,044 against 38,961,587,412) and 110 ppm (`numpy-others`). A scratch script isolated the cause: the same group, with numpy's tests staged beside pandas' or not, gives 38,949,120,223 or 38,961,587,990 for `tslibs`, and 18,265,293,632 or 18,263,674,142 for `internals` (the other way). pytest lists the grant's root folder, and the extra allocations move the collector's timing (INFERRED). A run narrowed to pandas' checks would then have shown `GREW` on an unchanged product. The fix: a run's stage always holds every package with a source tree, whichever check prepares it first. `test_the_stage_holds_every_package_whichever_check_asks_first` failed before the fix and passes after it. The memo has a dated correction saying so.

**The budget (Decision 8).** The caps sum to 2.821×10¹², under 3×10¹² (the rules check). The recorded fuel of the 11 groups sums to 1.646×10¹². The 7 trap checks are gaps, and a gap records no metric; their sessions took 9.1 to 11.9 G each, 73.2 G together, in the first scratch run. That gives 1.72×10¹² for the 18, under the 1.8×10¹² budget.

**Unit checks (criteria 1, 4, 5, 6, 8, 9).** `tests/unit/test_upstream.py` (57), `test_scoreboard.py` (+8 functions, 10 cases), `test_plugin.py` (+1) and `test_guest.py` (+2) were written first and seen failing (an import error for the new module; 10 failures in the ratchet and plugin checks, 3 of them the upstream refusal before its check file existed; 2 for the trap cause; 1 for the stage). All pass now. They cover:
- a wheel with one byte changed leaves `upstream kit` unmet; the unzip refuses `../x`, `/x`, `a/../../x` and `a/..\x`;
- the MANIFEST tie fails naming both tarballs, both hashes, or both patch hashes;
- a stray file and a `__pycache__` file are not staged and are listed; a patch-created file is;
- the grant is `("/upstream", stage, False)`; the argv;
- every finding of criterion 5, on fixed streams;
- `+`/`-` ids, with a `…[2020-01-01 00:00:00]`-style id that `scan.digest` partly normalises;
- an emptied class passes, and a returning failure shows as `+<node id>`;
- a trap entry that passes makes its gap say "remove the gap";
- the rules for empty and non-empty lists and gaps;
- `FEWER`, `more`, the flag, `fewer_reason`, the maximum, and the refusal of `--accept-growth` alone;
- an absent gap retired by `--retire`;
- the upstream refusal unless `--partial`;
- `metric("passes")` allowed, and an unknown name still raises.

**Not build-class (criterion 9).** No change under `scripts/`, `recipes/`, `downloads/` or `.github/` (`git status`, `git diff --stat`).

**The time (Decision 15; a benchmark fact, arm64 macOS).** The full judge with the upstream file left out (`--ignore`) took 221.4 s wall (pytest's 195.6 s). The full judge with it took 536.8 s (pytest's 511.4 s). So these checks add about 5¼ minutes, as Decision 15 estimated. The pandas groups are the knob.

**For the lane.** Fetch the kit in the main tree first (`uv run python tests/upstream/fetch.py`), judge, and cite the ratchet line with no `unrun locally` and no `upstream unrun` count. `--accept-judge` names the new checks, the lists, the gaps and the harness changes.

**After the build review** (to be filed as `context/reviews/050-numpy-and-pandas-own-tests-under-the-runtime-2026-10-18.md`; findings F1 to F6, each fixed; its Disposition gives the detail). Each fix's unit case was written first; the F3, F4 and F6 cases failed before their fix, and the F1 and F2 cases guard code that was already right (they kill the review's surviving mutants U5, U6, S9 and S13).
- **F1.** `test_a_manifest_mismatch_fails_the_checks_through_prepare_not_blocks` goes through `Session.prepare` and requires an `AssertionError` (not a skip) naming both tarballs.
- **F2.** The refusal's cases are split: an accepted pass or gap that is `blocked` or `deselected` alone, and an accepted gap outside the run alone.
- **F3.** `render` never cuts the ratchet line, the `FEWER` lines, `RED` or the "not machine-checked" lines; `LOST`, `ABSENT` and `GREW` give way first, then `FAIL` lines, then the lines above. Checked with 0, 2, 6 and 11 `FEWER` lines and three each of the others.
- **F4.** A `passes` no longer recorded is `FEWER … passes <old> -> none`, so only `--accept-fewer-passes` can drop it.
- **F5.** `test_api_importable` gets its own class, `numpy-others-no-conftest`, closed by the README, which now states that the zip carries no `tests` folders and no `conftest.py`. `test-only-modules` keeps `test_NPY_NO_EXPORT` (question 89). So there are **19 classes and 26 gaps**: spec 051 closes 15, the README 9, question 89 2. Decision 10's table counted 18; the split is the review's.
- **F6.** A trap check that did not trap also needs an `E` line and an `S` or `C` line under its entry's node id; otherwise "the entry ran nothing".

The full judge after the fixes, exit 0:

```
  v1.3  data stack          31/58  gap 26 blocked 1
gaps close with: 051-what-the-upstream-tests-found 15 · README 9 · questions-for-the-owner 2
ratchet vs 361775dd62: lost 0 · absent 0 · unrun 0 · unrun locally 7 · gained 12 · grew 0 · judge changed: … and 34 more
1188 passed, 17 skipped, 26 xfailed in 443.67s (0:07:23)
```

The 38 checks: 12 `pass`, 26 `gap`. Passes 62,569. The groups' fuel sums to 1,646,467,107,285, 0.07 ppm from the run before the fixes (the fixes run nothing differently in the guest).

**Rebased onto spec 051 and re-derived on its set** (2026-10-18, `s-f94dec535086b06c`; EXECUTED). The body's tables, criteria and Design now give these counts beside the earlier set's.
- **Rebase.** One conflict in `tests/harness/plugin.py`: spec 051 landed a `note(text)` fixture first, so this specification's `note(name, value)` is renamed `fact(name, value)`, recorded under `facts`. That is the only change to `tests/harness/` from the reviewed code (`guest.py`, `needs.py`, `scoreboard.py` and `upstream.py` are byte-identical to `3907985`'s). README conflicts were merged with 051's text.
- **The tie** holds with 051's `recipe` lines for `0001` (amended) and `0002`.
- **Seen first, as they stood:** every group ran with no finding. The six `zip-code-names` and the two `patch-0001-*` classes are empty; every other class equals its list. The seven trap entries, each alone, no longer trap (`test_casting_unittests.py` 904 passed and 28 failed, all `OSError: ctypes is unavailable`; the other six passed). numpy-lib gains two passes (the truncated-message test, and `test_save_masked_without_dup`, which amended patch 0001 adds).
- **C1 applied.** The eight emptied classes keep their ids and empty lists and lose their gaps; the seven `[[trap]]` entries, their gaps and the `not_selected` entry for the two returning files are deleted. `test_upstream_trap` is defined only while a trap entry exists (an empty parametrization would be a skip naming no need). The returning files' 28 failures are a new class, `numpy-core-no-ctypes`, closed by the README (it states that ctypes calls raise).
- **Caps** raised to at least 1.5 times the new fuel where needed (numpy-core 3.1×10¹¹, frame 5.2×10¹¹, groupby 7.2×10¹¹, io-parser 1.35×10¹¹, io-formats 8.2×10¹⁰, tslibs 5.9×10¹⁰, libs 3.5×10¹⁰); they sum to 2.519×10¹².
- **Passes, judge's fuel, and each group twice in one session:** numpy-core 9,519, 203,078,170,200 (203,078,175,300 / 203,078,175,317); numpy-lib 4,825, 131,417,583,434 (131,417,587,463 / 131,417,589,146); numpy-others 7,269, 175,315,688,633 (175,315,700,040 twice); pandas-frame 10,852, 344,819,783,016 (344,819,777,287 / 344,819,777,236); pandas-groupby 22,227, 478,743,979,551 (478,743,797,770 twice); pandas-reshape 2,664, 103,347,417,535 (103,347,419,796 twice); pandas-io-parser 3,474, 89,652,537,969 (89,652,525,304 / 89,652,525,202); pandas-io-formats 976, 54,364,789,367 (54,364,781,173 / 54,364,779,609); pandas-tslibs 590, 38,969,563,583 (38,969,542,622 / 38,969,562,648); pandas-internals 258, 18,266,840,927 (18,266,840,485 / 18,266,840,400); pandas-libs 1,063, 23,065,428,403 (23,065,428,080 / 23,065,428,148). Every pair within 0.01% (the most apart, groupby, 0.38 ppm). **63,717 passes**; group fuel **1.661×10¹²**, under the 1.8×10¹² budget.
- **The full judge** on 051's set, exit 0: `v1.3 data stack 45/58 gap 12 blocked 1`; `gaps close with: README 10 · questions-for-the-owner 2`; `ratchet vs 614520fff6: lost 0 · absent 0 · unrun 0 · unrun locally 7 · gained 20 · grew 0`; `1263 passed, 17 skipped, 12 xfailed in 521.05s`. The 32 upstream checks: 20 `pass` (11 groups, 8 emptied classes, the rule), 12 `gap`. The class lists hold 100 node ids. README's Measured row (63,717; 12 gaps) and the CHANGELOG line follow; the README's "Known defects" list is removed (051 closed all three).

**Landed 2026-10-18** through the lane. The rebase delta (`93ccd9c..612fb70`) was reviewed by a fresh agent, as the build review's item 7 asked (`../reviews/050-numpy-and-pandas-own-tests-under-the-runtime-rebase-2026-10-18.md`; verdict: confirmed, it lands; three low findings). Rebased onto main `1c0123c` (spec 034 and 049's revision); `git range-diff` shows all five commits unchanged (`=`). The lane answered the delta review's findings: F1 (numpy.toml's run of blank lines collapsed) and F3 (a comment in both configs: an emptied class's closer is a record, and failures that come back need a gap with a new closer) in `d672e16`, comment and whitespace only, made after the review as the review allows; F2 (this status line) here. Both reviews, written in scratchpads, were committed on the detached HEAD as `34eb315`. The kit was fetched in the main tree (`tests/upstream/fetch.py`: seven wheels, each hash checked), and the full judge ran there on `34eb315` against 051's accepted set: `wasi_python v1: 294/308 pass · 12 gap · 2 blocked · 0 fail (unit suite 1023/1025, 2 skipped)`, v1.3 `46/58 gap 12`, `gaps close with: README 10 · questions-for-the-owner 2`, `ratchet vs 34eb315196: lost 0 · absent 0 · unrun 0 · gained 0 · grew 0`, `1317 passed, 4 skipped, 12 xfailed in 550.30s` (EXECUTED, `build/lane-050-accept.log`). Accepted with `--accept-judge` as `d903110` (history line 50); the rules tier passed (24/24); main fast-forwarded. The release dry run waits on the owner's push.
