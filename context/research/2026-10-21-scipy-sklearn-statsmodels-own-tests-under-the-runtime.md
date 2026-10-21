# scipy's, scikit-learn's and statsmodels' own tests under the runtime (spec 095's survey)

- **Status:** EXECUTED 2026-10-21, darwin-arm64; spec 095's Decision 1 survey. Its delta to
  Decisions 7 to 12 is in the specification ("Delta from the survey") for a context-only delta
  review; nothing is built on it before that verdict.
- **Owner:** Clay Gendron
- **Sets** (each copied with `cp -c -Rp` into the builder's worktree and checked with `shasum -a 256
  -c SHA256SUMS`, both OK):
  - scipy and scikit-learn: wave 09's set from the main tree (main plus 100, numpy on OpenBLAS,
    and 097), `SHA256SUMS` `142bdd38…`;
  - statsmodels: 045's build-reviewed set, `SHA256SUMS` `14adfa5f…`.
- **How** (the scripts in this folder; `jobs.tsv` lists every session): the judge's own embedder
  (`tests/harness/guest.py`, the snapshot binary, `measured=False` because the stage is under the
  worktree), `tests/upstream/package_drive.py` unchanged, one guest session at a time, paused with
  `SIGSTOP` whenever the main tree's `build/lane.lock` existed (once, for about 15 minutes). The
  stage is the specification's: every top-level `<package>/**/tests` folder of the pinned sdist
  (scipy's `odr/tests` left out), each one's ancestor `__init__.py`, the conftests, the kit's seven
  wheels, the transcribed `.ini` (Decision 6), scipy's three `.npz` files made in the guest
  (Decision 5), the family `env` (Decision 7: `SCIPY_XSLOW=1`; `SKLEARN_RUN_FLOAT32_TESTS=1`,
  `SKLEARN_SEED=0`). One session per top-level tests folder (119 normal-tier sessions, 34
  release-tier, three re-runs), each with `--continue-on-collection-errors` so a file that cannot
  load stops only itself (the judge instead `--ignore`s its not-selected files). Fuel caps were
  survey caps (3 to 8 T a session), not the rule's.
- **Wall clock** (a benchmark fact): about 3 hours of guest time in one process for about 60 T of
  fuel in all (the tiers below, plus collections, probes and the runs a clock-timed test stopped),
  about 0.18 s per G, the drafting probes' rate.

## Findings

1. **No trap.** No session ended in a trap in either tier of any package.
2. **The guard held.** In every session the only module loaded from the stage outside a `tests`
   folder was the package's own `conftest.py`. No staged `__init__.py` was imported (spec 095,
   Decision 4).
3. **The measured price** (`summary.md`; each session's fuel includes its start):

   | family | tier | fuel | passed | failed | error | skipped |
   |---|---|---|---|---|---|---|
   | scipy | normal | 7.345 T | 75,623 | 331 | 147 | 4,212 |
   | scikit-learn | normal | 9.611 T | 34,287 | 1,485 | 62 | 9,716 |
   | statsmodels | normal | 14.225 T | 19,791 | 38 | 798 | 417 |
   | **normal, all three** | | **31.18 T** | 129,701 | | | |
   | scipy | release (at least) | 22.02 T | 18,363 | 8 | 0 | 374 |

   - The normal tier is 2.8 times today's about 11.2 T of upstream fuel. statsmodels is the
     largest part: 14.2 T, against 045's inferred 3 T; its tests are heavy per test (`stats`
     2.53 T for 3,014 outcomes, `discrete` 1.57 T, `tsa` 1.49 T, `regression` 1.36 T).
   - **The release tier is a lower bound:** `special` and `stats` each stopped at the survey's
     6 T session cap (after 57 and 150 of their slow tests: `test_mpmath.py` at 5,000 points, and
     `stats`' slow fits). Every other release session ended. `interpolate`'s 22 slow tests are
     1.64 T, `sparse/linalg`'s 13 are 2.59 T; the three `SCIPY_XSLOW` keyword entries are 3.11 T
     for 4,832 tests.
4. **The start of a session costs 12 to 32 G.** A session of a few tests measured 20.1 G for
   scipy (`constants`, 16 tests), 26.2 G for scikit-learn (`callback`, none) and 31.8 G for
   statsmodels (`sandbox`, 2 tests). The driver imports every `package_paths` key first. With only
   the run's own ancestors, scipy's `constants` started at 12.4 G; statsmodels' `sandbox` then
   failed to load `test_pca.py`, which imports `statsmodels.multivariate.tests`, so a group must
   keep the ancestors of every tests folder its files import.
5. **One test never ends under the judge's counted clock.** scipy's
   `signal/tests/test_signaltools.py::test_choose_conv_method[numpy]` times both convolution
   methods with `measure=True`, which repeats each until a fixed time has passed. Under the
   judge's clock (each read advances 1 µs) that takes far more work than natively: `signal`'s
   normal session spent its 3 T cap inside it, a re-run with a 4 T cap did the same, and the test
   alone spent 600 G without an outcome. Without it, `signal`'s normal tier is 250.2 G (5,558
   outcomes). It is not a product defect: the time a guest sees is the embedder's.
6. **Collection: what cannot load** (each with `--continue-on-collection-errors`):
   - scipy: the five files of spec 095's Decision 8 on the seven test-only C modules, the three
     `test_cython_abi.py` (`ctypes.pythonapi`), the two `ilp64_test_package` files; no other.
     `special/tests/test_data.py` loads with the derived `.npz` files.
   - scikit-learn: the three `mmap` files of Decision 8, and no other; but its
     `callback/tests/conftest.py` ignores the whole folder on wasm (`pytest_ignore_collect`
     returning `_IS_WASM`): upstream's own choice, 54 test functions never collected.
   - statsmodels: **six** files fail at import on a left-out dataset, not two:
     `discrete/tests/test_constrained.py` (`spector`), `discrete/tests/test_margins.py`
     (`cpunish`), `emplike/tests/test_anova.py` (`star98`), `genmod/tests/test_glm_weights.py`
     (`cpunish`), `stats/tests/test_oaxaca.py` (`ccard`), `tsa/vector_ar/tests/test_vecm.py`
     (`interest_inflation`). Whole-suite collection: 21,172 tests (045's builder counted 21,412
     natively).
   - statsmodels' tests use two markers its sdist registers nowhere, `thread_unsafe` (313 uses,
     pytest-run-parallel's) and `skip_randomstate_check`; under `--strict-markers` three files of
     `base/` failed to collect until the `.ini` registered both.
7. **Failures by reason** (`failures.txt`, normal tier unless marked):

   | family | reason | members | class it fits |
   |---|---|---|---|
   | scipy | `module 'threading' has no attribute 'get_native_id'` | 335 (288 in `io`: temporary names made from the thread id) | `no-native-id` |
   | scipy | `module 'os' has no attribute 'pipe'` | 44 (+2 release) | `no-processes` (multiprocessing pools) |
   | scipy | `can't start new thread`, `thread constructor failed: Not supported` | 39 (+1 release) | `no-threads` |
   | scipy | `OSError: [Errno 58] Not supported` | 21 (all in `io`: `test_wavfile.py`, `test_fortran.py`, `test_paths.py`) | new class; the call that answers `ENOTSUP` is to be named in the build (not read in the survey) |
   | scipy | `mmap is unavailable` | 16 | `no-mmap` |
   | scipy | `DID NOT WARN … RuntimeWarning` | 12 | `no-fp-exceptions` |
   | scipy | `Found unexpected modules: ['scipy.odr']` | 1 | new: the `scipy.odr` stand-in module is visible to the public-API check |
   | scipy | one each: `DID NOT RAISE ValueError`, `SpecialFunctionError`, two unraisable-exception warnings, four bare `AssertionError`s, two `DID NOT WARN` of other kinds | 11 | to be read one by one in the build |
   | scipy release | `array is too big` | 2 | `wasm32-memory` |
   | scikit-learn | `mmap is unavailable` | 1,536 | `no-mmap` (memory-mapped test data, joblib's memmapping) |
   | scikit-learn | `encoder jpeg not available` | 4 | `pillow-zlib-only` |
   | scikit-learn | one each: `/dev/null`, `Errno 58`, `__check_build` in the zip, three asserts | 7 | to be read one by one |
   | statsmodels | `FileNotFoundError` naming a left-out dataset | 832 (`spector` 428, `cpunish` 230, `star98` 65, `ccard` 42, …) | `left-out-datasets` |
   | statsmodels | `On entry to DLASCL parameter number # had an illegal value` | 1 | a `nan` reaching LAPACK (as 100's research saw in numpy) |
   | statsmodels | three others | 3 | to be read one by one |

8. **Skips that name a mode** (`skips.txt`): scikit-learn 1,077 skip because `SCIPY_ARRAY_API`
   is unset (747 and 330 in two wordings), and 7,011 more because an array-API backend is not
   installed (torch 3,605, dpnp 1,933, array_api_strict 989, cupy 484); scipy 73 (`MArray`, also
   `SCIPY_ARRAY_API`); statsmodels none. scikit-learn's 211 `numpydoc` skips are a pure test-only
   dependency the kit lacks (a `kit_extra` candidate, shared with 067); its `polars`, `pyarrow` and
   `lightgbm` skips are compiled packages the product does not carry.
9. **The derived files** (Decision 5): `boost.npz` 1,270,643 bytes, 111 `.npy` members,
   5,776,895,950 fuel; `gsl.npz` 51,433 bytes, 3 members, 1,240,909,650; `local.npz` 203,438
   bytes, 8 members, 1,569,087,909. 8.59 G in all per scipy stage. SHA-256 `57b5c2b6…`,
   `cbf1afdd…`, `6c29e58c…` (repeatability is criterion 5's, at the build).
10. **The keyword entries** (Decision 7, by full id, computed from scipy's own `_distr_params.py`
    read as data and checked against a collection with `SCIPY_XSLOW=1`; `keywords.txt`): 19
    `test_rv_generic[i-distdata<i>]` cases (the sixteen names, three of them listed twice),
    `test_accuracy[numpy-case68-…]` and `[numpy-case100-…]` (`studentized_range`, `levy_stable`;
    four ids), and `test_axis_nan_policy_full or (test_axis_nan_policy_fast and kruskal)`. Each is
    prefixed by its class (`TestMakeDistribution and (…)`, `TestTanhSinh and (…)`) so it matches
    no other file in the same group.

## Smoke selection, the clock-stepped test and the split (EXECUTED 2026-10-21, after the delta review)

By the builder who took over spec 095 from the drafter, answering the delta review's D-M1 to
D-M3 and D-L2. The folder `smoke/` holds the scripts, the job lists and the records.

- **Set:** the main tree's frozen `build/artifacts` (wave 10's, statsmodels included),
  `SHA256SUMS d0d91cef…`, copied with `cp -c -Rp` into the builder's worktree and checked with
  `shasum -a 256 -c` (all OK). The three sdists copied and their SHA-256 checked against their
  pins (scipy's and scikit-learn's in `downloads/SHA256SUMS`, statsmodels' in the set's
  `MANIFEST`).
- **How:** the survey's stand-in (`smoke/scripts/survey.py`, repointed, with a `clock_step_ns`
  switch and a one-hook plugin that writes `sys.modules` at the end of a session), the judge's
  embedder, one guest at a time, never while `build/lane.lock` existed. Stopping another process
  is not permitted in this sandbox, so a session the lane's lock found running was ended and run
  again after (`runjobs.py`); the lock held twice (06:45 to 07:08 and 07:33 to 07:54, EDT); no
  record was kept from an ended session. The machine was loaded (load average up to 97 from other agents'
  work), so wall clock is not a fact here; fuel is.
- **The derived files repeat:** `boost.npz`, `gsl.npz`, `local.npz` made in the guest again with
  the same SHA-256 as the survey's (`57b5c2b6…`, `cbf1afdd…`, `6c29e58c…`) on another set (fuel
  5.78, 1.24, 1.57 G).
- **The build's own list of compiled modules** (`smoke/builtins.txt`, from the guest's
  `sys.builtin_module_names`): scipy 95 in 31 subpackages, scikit-learn 69 in 19, statsmodels 26
  in 11.
- **Import is not evidence of a touch.** Every scipy session imported 91 of the 95 compiled
  modules before any test ran, because the driver imports every `package_paths` key first. The
  four it does not are imported lazily: `_fmm_core` (only `test_mmio.py` imported it),
  `_matfuncs_sqrtm_triu` (`test_matfuncs.py`, `test_batch.py`), `cython_optimize._zeros`,
  `_unuran.unuran_wrapper`. So the cover is read from the files (READ), with the four lazy ones
  confirmed by import (EXECUTED).
- **Per-file probes** (`smoke/probes.tsv`: label, session fuel in G, exit, trap, outcomes; less
  20.1 G for a scipy start, 26.4 G for scikit-learn's and statsmodels'): 117 candidate files or
  folders and three draft groups. Five ran out of their 150 G probe caps and were left to the
  release tier: scipy `interpolate/tests/test_rbfinterp.py`, scikit-learn
  `ensemble/tests/test_gradient_boosting.py` and `manifold/tests/test_t_sne.py`, statsmodels
  `tsa/holtwinters/tests/test_holtwinters.py` and `tsa/tests/test_exponential_smoothing.py`;
  `nonparametric/tests/test_kde.py` ended at 149.5 G. scikit-learn's
  `utils/tests/test_cython_blas.py` skips whole ("could not import 'cython'") and was dropped.
- **The final groups, each measured whole once** (`smoke/jobs-final.tsv`; failures by reason in
  `smoke/smoke-failures.txt`): `scipy-smoke-a` 207.36 G (2,033 passed), `scipy-smoke-b` 221.78 G
  (2,322 passed, 28 failed, 147 errors, all of measured reasons), `scikit-learn-smoke` 205.48 G
  (1,467 passed, 2 failed), `statsmodels-smoke` 135.96 G (939 passed, 4 failed, 40 errors, all
  `left-out-datasets`): **770.6 G**. No trap, no collection error. The specification's Decision 7
  gives the rule, the paths and the cover.
- **The clock-timed test runs with a 1 ms clock step:** `scipy/signal/tests/test_signaltools.py::
  test_choose_conv_method[numpy]` passed, one outcome, 37.92 G for the session (start and the
  file's collection included), with `clock_step_ns = 1_000_000` and `-k "test_choose_conv_method
  and not _2"`, no `-m`.
- **numpy's `tofile` refuses even with a path:** in the guest, `np.arange(4.0).tofile(
  "/tmp/w/p.bin")` raised `OSError: [Errno 58] Not supported` (0.89 G). It is `enotsup-io`'s call.
- **The split, proved** (`smoke/split.py` over the three pinned tarballs and `smoke/plan.toml`,
  output `smoke/split.txt`): every staged test file is in exactly one tier under the smoke kind's
  rules (scipy 329 files, 63 in smoke paths; scikit-learn 256, 37; statsmodels 285, 26); six
  mutants per family are each refused with their own line.
