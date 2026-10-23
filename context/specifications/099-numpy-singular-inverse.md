# 099 — numpy's own floating-point signals are kept in software, so a singular matrix raises `LinAlgError`

- **Status:** **landed 2026-10-20 in wave 08** (042, 066, 099) on main `faa9c93`: accepted on `72bc5ed`, history line 89, 763/850 pass, 0 fail, on a set rebuilt from the same pins in a clone of wave 08 outside the home folder (`SHA256SUMS` `b5a66245`, equal byte for byte to the set rebuilt in the main tree; attempt 1 in the main tree void by macOS host litter, spec 089); the integration review `../reviews/wave-08-integration-2026-10-20.md` (lands once the progress files are copied back unchanged; done, every grown row inside its prediction or its M2 clause); the dry run 39488145764 dispatched as main moved. Before: **drafted 2026-10-20** on `spec/099-numpy-singular-inverse` from main `958a22b`, with its drafting runs; **reviewed before build** the same day (`../reviews/099-numpy-singular-inverse-spec-2026-10-20.md`, verdict "passes for build once finding 1 (Medium) is answered in the text"); **revised against every finding**, with the owner's answer to question 106 (spec 100, stacked on this one), and rebased onto main `3ff1871` (context only). *Disposition of the pre-build review* says where each went. **Confirmed for build** by the same reviewer (the review's *Confirmation*), no finding open. **Built 2026-10-20** from an empty `build/` on base `21dff9d` (rebased since onto `3ff1871`, context only); the dry run 39432450036 on `b0e1593`'s only red lines are its 15 claimed growth lines (*Landing notes*), with one build finding (B1) written in for the build review. **Build review** (`../reviews/099-numpy-singular-inverse-build-2026-10-20.md`): "lands once M1 is closed". **M1 closed**: rebased onto main `2516875` (wave 07; no conflict hunk), the flag word allowed by name in step 60's weak-duplicate gate, **rebuilt from empty** (set `5f203242`), and the dry run 39454475153 on `6866dd1`'s only red lines are its 22 claimed growth lines. Its Disposition is filled in. **Confirming review: lands** (`../reviews/099-numpy-singular-inverse-confirm-2026-10-20.md`; L1 carried by spec 100). **Rebased onto wave 08's tip** `66cc120` (042, 066): five named conflict hunks and 066's `no-fp-exceptions` class emptied, as Decision 7 provides; no new run. It changes the build recipe and the artifact set, so it was reviewed before it is built (constitution §5.6).
- **Date:** 2026-10-20
- **Owner:** Clay Gendron
- **Kind:** **build-class** (§5.7): a new recipe file, `recipes/npy_fenv_flags.h`, force-included into every numpy compile by `recipes/wasi-numpy.cross`; it changes `python.wasm`, the snapshot and the stdlib zip (numpy's `__config__.py` records the compile arguments), and `MANIFEST` gains one `recipe` line and changes one. It fixes a package already in the set and adds none, so it is not a package entry in a wave. No carried patch, no new pin, no step script changes. **And a judge change:** four new checks (seven nodes), one scan function and its unit rows; the lane accepts with `--accept-judge` and `--accept-growth`. The guest's imports and exports do not change; no line of `tests/public_api.txt` changes.
- **Depends on:** landed specifications only: 003 (numpy's cross build, its force-included rename header), 059 (the compile records the new check reads), 069 (the snapshot pre-imports no package). It meets 066, 044, 045 and 095 (Decision 9).
- **Research it stands on:** spec 066's survey (on its branch, `context/research/2026-10-20-the-compiled-packages-own-tests-under-the-runtime.md`, its addendum C2 and `failures.txt`: matplotlib's two `test_mlab` failures, `DID NOT RAISE LinAlgError`); the owner's decision of 2026-10-20 (`../decisions.md`, "Three answers for 0.1.0"). **The drafting runs** (EXECUTED 2026-10-20 on macOS arm64, in this worktree, on a private `cp -c` copy of main's set, wave 06's, `SHA256SUMS` `f12cd25c…`, `build/lane.lock` absent; native runs on the oracle's CPython 3.15.0 with the numpy 2.5.2 and matplotlib 3.11.2 wheels, `build/oracle/venv`): their programs and outputs are in `../research/2026-10-20-numpy-floating-point-status/`. The facts sheet for numpy is `../upstream/30-numpy-fp-status-without-fenv-flags/facts.md`.

## The problem

numpy reports some errors through the floating-point status flags. A flag is a bit the CPU sets when an operation divides by zero, overflows or gives an invalid result; C reads and sets them with `<fenv.h>`. numpy also sets flags itself, in software, for errors no hardware operation produces: an integer division by zero, a failed LAPACK call. Then its `np.errstate` machinery turns a set flag into a warning, an exception or a callback.

WebAssembly has no floating-point status flags. So in the guest:

1. **`numpy.linalg.inv` of a singular matrix returns `nan`s and raises nothing.** Natively it raises `LinAlgError: Singular matrix`. The same holds for `solve`, `tensorinv`, `tensorsolve`, `matrix_power(a, -1)` and `cholesky` of a matrix that is not positive definite (EXECUTED, `check1_singular-*.out`). A program that catches `LinAlgError` to take another path silently computes with `nan`s instead. matplotlib's `mlab.GaussianKDE` of rank-one data is one such caller: natively it raises, in the guest it returns (EXECUTED, `consumer_probe.out`).
2. **Integer division by zero and integer overflow in division warn nowhere**, and `np.errstate(divide="raise")` does not raise for them. Nor does a float64 to float16 overflow (EXECUTED, `check2_numpys_own_signals-*.out`).

The owner decided on 2026-10-20 that the first is fixed before 0.1.0. This specification fixes both, because they are one mechanism.

## Decisions

### 1. The mechanism (READ and EXECUTED)

- **`umath_linalg` signals a LAPACK failure by the invalid flag.** Each loop starts with `get_fp_invalid_and_clear()`, and when LAPACK's `info` is not 0 it fills the output with `nan` and ends with `set_fp_invalid_or_clear(1)`, which calls `npy_set_floatstatus_invalid()` (READ, numpy 2.5.2, `numpy/linalg/umath_linalg.cpp:433-449` and `1839-1871` for `inv`). Eleven loops do this: `eigh_wrapper`, `solve`, `solve1`, `inv`, `cholesky`, `eig_wrapper`, `svd_wrapper`, `qr_r_raw`, `qr_reduced`, `qr_complete`, `lstsq` (READ). `det` and `slogdet` do not.
- **Python turns the flag into the exception.** `numpy/linalg/_linalg.py` wraps each call in `errstate(call=_raise_linalgerror_singular, invalid='call')` and its five siblings (READ, lines 143-160 and the ten `with errstate(call=…)` sites). After the loop, numpy's ufunc machinery reads the flags and calls the callback.
- **The flag is set by `feraiseexcept` and read by `fetestexcept`** (READ, `numpy/_core/src/npymath/ieee754.c.src:331-405`, the compiled form of `npymath`; the C++ `float_status.hpp` does the same for float16 conversions).
- **wasi-libc defines no flag.** Its `bits/fenv.h` for `wasm32-wasip1` has `FE_ALL_EXCEPT 0` and `FE_TONEAREST 0`, nothing else (EXECUTED, wasi-sdk 34's sysroot). numpy then defines `FE_INVALID`, `FE_DIVBYZERO`, `FE_OVERFLOW` and `FE_UNDERFLOW` as 0 itself (READ, `ieee754.c.src:343-354`; `float_status.hpp:28-52` as `constexpr` zeros).
- **So the raise is lost at compile time, not at run time.** `npy_set_floatstatus_invalid()` compiles to `feraiseexcept(0)`, and the read to `fetestexcept(0)`. The prototype shows it (EXECUTED, `prototype/run.sh`, `run.out`): numpy's pattern compiled with wasi-sdk 34 and run under wasmtime 49.0.3 reads status 0 after an explicit invalid raise. **This rules out any link-time fix**: a `feraiseexcept` that kept flags would still be passed a mask of 0.
- **The guest confirms the error path is taken.** `inv`'s loop fills its output with `nan` only when `call_gesv` fails; the guest's all-`nan` result is that fill (READ, `umath_linalg.cpp:1857-1863`; EXECUTED, `fp_probe-guest-*.out`). LU of `[[1, 2], [2, 4]]` meets an exact zero pivot (2 − 0.5 × 4), so `info` is 2 in any LAPACK. **That is not true of every singular matrix** (Decision 6): which matrices make LAPACK report `info != 0` depends on the LAPACK, and the guest's is not native's.

### 2. What else relies on this path (READ, by `grep` of the pinned trees)

- **Only numpy calls `feraiseexcept`, `fetestexcept` or `feclearexcept` with real masks.** The only callers in numpy are `ieee754.c.src` (and its unbuilt C++ twin) and `float_status.hpp`. No file in CPython 3.15.0, pandas, scipy, matplotlib, contourpy, kiwisolver, Pillow, regex, OpenBLAS or qhull calls them, but Boost.Math's `fpu_guard` inside scipy, which uses `FE_ALL_EXCEPT` (0 in wasi-libc) and is not compiled with numpy's flags.
- **numpy's explicit raisers** (`npy_set_floatstatus_*`, `FloatStatus::Raise*`): the integer and timedelta division, remainder and divmod loops (`loops_arithmetic`, `loops_modulo`, `loops.c.src`), float16 conversions (`half_private.hpp`, `halffloat.cpp`), complex `npymath` (`npy_math_complex.c.src:252`) and `umath_linalg`. The `loops_exponent_log` raisers are in its AVX2 and AVX-512 paths (`#ifdef SIMD_AVX2_FMA3`, `SIMD_AVX512F`), which the wasm build does not compile.
- **numpy's readers** (`npy_get_floatstatus_barrier`, `npy_clear_floatstatus_barrier`): the ufunc machinery (`extobj.c`, `ufunc_object.c`, `reduction.c`), casts and assignment (`dtype_transfer.c`, `array_assign_*.c`, `array_coercion.c`, `ctors.c`, `mapping.c`), `matmul`, `clip` and scalar math. They read whatever the raisers set; today that is always 0.
- **scipy reads numpy's status** through `PyUFunc_getfperr` in `scipy.special`'s `sf_error_check_fpe` and xsf's `set_error_check_fpe` (READ, `scipy/special/sf_error.cc:131`, `subprojects/xsf/include/xsf/numpy.h:33`). scipy raises no flag itself, and numpy clears the status before each ufunc loop, so scipy's special functions read 0 before and after this change (INFERRED).
- **Scalar integer math already works.** `np.int8(127) + np.int8(1)` and `np.int64(1) // np.int64(0)` warn in the guest today: scalar math returns its error codes, not flags (READ, `scalarmath.c.src:60-210`; EXECUTED, `check2_numpys_own_signals-guest-*.out`).

### 3. The fix: one force-included header that gives the flags bits and a word (EXECUTED)

`recipes/npy_fenv_flags.h`, force-included into every numpy C and C++ compile, as `recipes/npy_rename.h` is today:

- It includes `<fenv.h>` (and `<cfenv>` in C++) first, so the C library's declarations parse with their own names.
- **It stops the build if the C library ever defines a flag** (`#error`, naming this specification). A toolchain that brings real flags retires the recipe; it cannot run beside it.
- It defines `FE_INVALID 0x01`, `FE_DIVBYZERO 0x04`, `FE_OVERFLOW 0x08`, `FE_UNDERFLOW 0x10` and `FE_INEXACT 0x20`, and redefines `FE_ALL_EXCEPT` as their union.
- It declares one flag word, `int wasi_python_fe_flags`, **weak**, in every object: the static link keeps exactly one. And three `static inline` functions, `wasi_python_feraiseexcept`, `wasi_python_fetestexcept` and `wasi_python_feclearexcept`, that set, test and clear its bits. In C++ it adds the three names to `std` too, so `std::fetestexcept` would still compile (numpy calls none: READ).
- It renames numpy's three calls to them by `#define`, as `npy_rename.h` renames a symbol.

**What it changes:** numpy's own explicit raises are now seen by numpy's own reads. **What it does not change:** arithmetic. `1.0 / 0.0` still sets nothing; wasm has no flag for it to set.

The prototype (`prototype/npy_fenv_flags_one_header.h`, `run_one_header.sh`, `run_one_header.out`) compiles numpy's two patterns, a C translation unit shaped as `ieee754.c.src` and a C++ one shaped as `float_status.hpp`, with the header, links them, and runs them under wasmtime: a C invalid raise reads 8 (numpy's `NPY_FPE_INVALID`), a divide-by-zero 9, a clear 0, a C++ `FloatStatus::RaiseOverflow` 2 from the C reader, and `std::fetestexcept(FE_OVERFLOW)` 1. Each object carries the word as a weak definition (`W`); the linked module has one. Nothing the header adds is an import.

**Why the flag word is safe to share.** The guest has no threads; natively the flags are per thread. numpy clears the status before each ufunc loop and `umath_linalg` clears it at each loop's start, so a bit left set by one operation is cleared before the next reads it, as natively (READ, `ufunc_object.c`, `umath_linalg.cpp:433`). The snapshot is taken before numpy is imported (spec 069), so the word is 0 in every new instance. A bounded session keeps one instance across calls; a bit left set by one call is cleared by the next numpy operation, as in one native process.

**Why the cross file, both argument lines.** `c_args` covers `npymath` (`ieee754.c.src`, where the C raises and reads live), the loops and the readers. `umath_linalg.cpp` is C++ but calls `npy_set_floatstatus_invalid()`, a C function in `npymath`, so it needs nothing. `cpp_args` covers the C++ files that include `float_status.hpp` and call `FloatStatus::Raise*` inline: `halffloat.cpp` in `npymath` and every user of `half_private.hpp` (float16 conversions). Without it, float16 overflow would stay silent while integer division warned. Today `cpp_args` carries no force-included header; this adds the first.

### 4. The options weighed

- **(a) A recipe-level software fenv linked in, without bits at compile time. Refused, because it cannot work:** numpy's masks are 0 at compile time (Decision 1), so a `feraiseexcept` that kept flags would be asked to keep none. Shown by the prototype's first half (`run.out`).
- **(a′) The same with a separate C file for the word** (`prototype/npy_fenv_flags.h` and `.c`, also EXECUTED, `run.out`). It works, but it needs step 40 to compile and archive the C file and step 60 to link it, two script changes and a second recipe file. The weak word does the same in one file and touches no script (§6.4: fewer files). Chosen against.
- **(a″) Overriding wasi-libc's `feraiseexcept` by name, without the rename.** wasi-libc's `fenv.o` also defines `fegetround` and its siblings; any other caller pulls it in and the link fails on a duplicate. And it would change the function for every package, not only numpy. Refused.
- **(b) A carried numpy patch** (a status word in `ieee754.c.src` when `FE_INVALID` is undefined, or a check of LAPACK's `info` in `umath_linalg`). It would work, and it is the right shape upstream (the facts sheet). But §4.1 puts a recipe file first, and a rename header does the job without a source change. Refused here; the facts sheet records the upstream shape for the owner.
- **(c) A Python wrapper around `numpy.linalg`** that checks the result for `nan`. Wrong: a `nan` input legitimately gives a `nan` output, and it would fix none of the integer signals. Refused.
- **(d) Linking numpy against OpenBLAS** (in the set since 037) instead of its own `lapack_lite`. It changes which LAPACK runs, not how its failure is reported: the flag is still lost. It brings the guest closer to native OpenBLAS on which singular matrices fail (254 of 300 agree, against 249 with `lapack_lite`; Decision 6) and gives native's errors for `nan` matrices. The owner answered question 106 "Both before 0.1.0", and, after the correction, question 107 "Yes, before 0.1.0" (`../decisions.md`): it is spec 100, reserved, stacked on this one.
- **(e) `-DFE_INVALID=1` and the rest in the cross file.** numpy's masks would be real, but the calls would still go to wasi-libc's no-op functions. It needs the rename, so it needs the header.
- **(f) Only `FE_INVALID` given a bit** (the pre-build review's L5). The owner's decision names the singular inverse, and this narrower header would fix `numpy.linalg` alone, leaving integer division by zero, integer overflow in division, timedelta division by zero and float16 overflow silent. It would not even be "linalg only": timedelta's `NaT` results and complex `npymath` raise invalid too, so they would start warning while their divide-by-zero siblings stayed silent. **Refused**: native parity for numpy's own signals is the product's rule (constitution §2.3, the results match native Python), and a word with one bit real is an odder state to document than one with all of numpy's own signals real. The widening is named in the CHANGELOG line and the README bullet (Decision 7), so the owner sees it.

### 5. The blast radius: what moves

**Behaviour that becomes native** (EXECUTED natively; in the guest after the build, the checks):

- `numpy.linalg`: `inv`, `solve`, `tensorinv`, `tensorsolve` and `matrix_power(a, -1)` raise `LinAlgError: Singular matrix` **whenever numpy's bundled LAPACK finds the matrix singular**, for float32, float64, complex and stacked inputs; `cholesky` raises `LinAlgError: Matrix is not positive definite` whenever it finds a non-positive pivot. `errstate(all="ignore")` around them does not hide it, as natively (`_linalg.py`'s own `errstate` is innermost). For a matrix with an exact zero pivot, as check 1's, every LAPACK agrees and this is native behaviour. For a matrix singular only in exact arithmetic, the guest's LAPACK and native's can disagree, either way (Decision 6).
- Integer arrays: `// 0`, `% 0` and `divmod(…, 0)` warn `divide by zero encountered in …`; the smallest `int32` floor-divided by −1 warns `overflow encountered in floor_divide`; timedelta `// 0` warns. Under `np.errstate(divide="raise")` they raise `FloatingPointError`.
- float64 to float16 overflow warns `overflow encountered in cast`, and raises under `errstate(over="raise")`.
- `eig`, `eigh`, `svd`, `lstsq` and their callers (`pinv`, `matrix_rank`, `cond`, `norm(…, 2)`) raise `LinAlgError` whenever numpy's LAPACK reports a failure. Which inputs make `lapack_lite` fail is `lapack_lite`'s, not this specification's (Decision 6).

**Rows** (INFERRED; the builder measures and claims each, *For the lane*):

- **New passes:** the four checks below, seven nodes.
- **Bytes grow:** `python.wasm` and the snapshot by the bit tests the compiler no longer folds away, and by the inlined set, test and clear (INFERRED: under 8 KB each; above 16 KB is a finding for the build review). The zip by about 140 bytes: `numpy/__config__.py` records both argument lines, each gaining `-include, …/recipes/npy_fenv_flags.h` (READ, the installed `__config__.py`, lines 38 and 54).
- **Fuel moves a little, either way, on rows that run numpy ufuncs:** each status read was a real out-of-line call to wasi-libc's `fetestexcept(0)`, whose result the compiler folded to 0; it becomes an inlined load and four bit tests. So a row may go down as well as up (the pre-build review's note 7; INFERRED: a few instructions per ufunc call, under 0.1% on any row; above 0.5% either way is a finding for the build review). Golden outputs do not change: no golden job divides integers by zero or inverts a singular matrix (READ, `tests/jobs/*.py`).
- **Upstream suites: no pass is lost and no class moves** (INFERRED). numpy's own tests of these signals are skipped on wasm by `IS_WASM` ("fp errors don't work in wasm", READ: `test_linalg.py` lines 1169 and 1998, `test_errstate.py`, `test_half.py`, `test_function_base.py`, `ma/tests/test_core.py`, `test_casting_floatingpoint_errors.py`), and `platform.machine()` stays `wasm32`, so they stay skipped. No expected class in `tests/upstream/numpy.toml` or `pandas.toml` names a floating-point signal (READ). **For the non-LAPACK raisers** (integer, timedelta and modulo loops, float16 conversions, complex `npymath`) the guest and native run the same numpy code, so a signal the guest now gives is one native numpy gives at the same place: the software word holds a subset of what the hardware would, and a test that passes natively passes here. **For `umath_linalg` that argument does not hold** (the pre-build review's finding 1): the guest raises when `lapack_lite` reports a failure, and `lapack_lite` can fail on a matrix native's LAPACK (OpenBLAS or Accelerate) inverts (Decision 6). So a test, golden or caller that inverts a matrix singular only in exact arithmetic may newly raise in the guest. **Where a lost pass would show**, and so what the lane's run is the evidence for: the upstream group `numpy-others` (`numpy/linalg/tests`), pandas' groups (`pandas-frame`, `pandas-groupby`, `pandas-reshape`, `pandas-io-*`, `pandas-tslibs`), the golden jobs that call `numpy.linalg` (`numpy_csv`, `modelling`, `scipy_numeric`, `scipy_lapack`, READ: `tests/jobs/*.py`), matplotlib's plot goldens (`plot_line`, `plot_contour`, `plot_callbacks`: its affine transforms call `numpy.linalg.inv`), and, when they land, spec 044's and 045's goldens. Any lost pass is a finding, never an allowance: the builder stops and reports it.
- **Upstream outcomes outside the pass digest may move** (the pre-build review's note 8). numpy's non-strict `xfail(IS_WASM)` tests (`test_umath.py:4437-4558`, complex branch cuts; `test_regression.py:346`) may move between xfailed and xpassed once complex `npymath`'s invalid flag is real. The judge counts a non-strict xpass as upstream's own outcome (`tests/harness/upstream.py:628`), and numpy's ini has no `xfail_strict`. pandas' `xfail_strict` `WASM` cases are `test_sas7bdat` tolerances, not floating-point signals. The builder names any change in the per-outcome counts in the claim list.
- **`MANIFEST`:** one new `recipe` line (`recipes/npy_fenv_flags.h`), one changed (`recipes/wasi-numpy.cross`), and the snapshot's `x-snapshot-zip` line. `LICENSES/` does not change: the header is ours.

### 6. What stays different from native, and says so

- **Signals only the hardware gives stay silent.** Float division by zero, `log(0)`, `sqrt(-1)`, `exp(1000)`, a `nan` cast to an integer, and the same on numpy scalars return native's values with no `RuntimeWarning`, and `np.errstate(all="raise")` does not raise for them (EXECUTED, `check3_hardware_signals-*.out`). Float floor division by zero is one of them: numpy computes it as `a / b` (READ, `npy_math_internal.h.src:550-564`). Check 3 holds this, and the README says it.
- **The guest's LAPACK and native's disagree on which singular matrices fail, either way** (the pre-build review's finding 1; EXECUTED). numpy in the guest runs its bundled `lapack_lite`; native wheels run OpenBLAS, or Apple's Accelerate in the `macosx_14_0_arm64` wheel. For a matrix singular only in exact arithmetic, rounding decides whether a pivot is exactly 0, and the LAPACKs round differently. Two probes **against native Accelerate** (the oracle's `macosx_14_0_arm64` wheel: both the review and the drafting runs used it, believing it OpenBLAS; corrected on main `3ff1871`, `../decisions.md`, "Correction and question 107"), against the guest on main's set (`lapack_lite`; an all-`nan` result is numpy's error fill, so it raises after this specification):

  | native Accelerate | guest, after 099 | review's probe (300) | drafting probe (300, `singular_probe.py`) |
  |---|---|---|---|
  | raises | raises (all-`nan` today) | 150 | 130 |
  | finite | finite | 130 | 141 |
  | raises | **finite**, wrong numbers, no exception | 12 | 20 |
  | finite | **raises `LinAlgError`** | 8 | 12 |

  Examples: `np.linalg.inv(np.arange(1.0, 17.0).reshape(4, 4))` raises natively and returns finite numbers in the guest, before and after this specification; the drafting probe's case 26 (n 4, rank at most 2) returns finite natively and raises in the guest after it (`singular_probe-crosstab.out`). So for `numpy.linalg` this specification gives "raises when numpy's bundled LAPACK finds the matrix singular", not "raises exactly when native does". It turns 130 to 150 silent `nan` results per 300 into native's exception, and adds 8 to 12 raises native would not make. **Against native OpenBLAS** (spec 100's author, numpy's `macosx_11_0_arm64` wheel, OpenBLAS 0.3.34; `../decisions.md`, "Correction and question 107"): the guest agrees on 249 of 300 with `lapack_lite` and this specification, and on 254 with spec 100's link to the set's OpenBLAS; native Accelerate and native OpenBLAS agree with each other on
  243. The rest are rounding-edge cases (pivots of 1e-16 or less) that wasm does not reproduce (INFERRED there: no fused multiply-add). **So spec 100 narrows this, it does not close it**: exact singular-matrix parity is not a goal in wasm (the owner's answer to question 107), and the README says so. The builder runs `singular_probe.py` on the new set, both binaries, and records the four counts and one example of each row in the landing notes, as facts, not as a check.
- **A LAPACK failure the hardware would add stays silent.** Natively an `inf` in a matrix can make LAPACK's arithmetic raise the invalid flag with `info` 0, and numpy then raises `LinAlgError`; the guest raises only when `info` says so (INFERRED from Decision 1).
- **numpy's own LAPACK is not native's.** numpy in the guest is built with no BLAS, so it runs its bundled `lapack_lite` (spec 037's cross-file comment). Its error routine raises `ValueError` where native's (Accelerate's in these runs) prints and returns: `np.linalg.svd(a, compute_uv=False)`, `svdvals`, `matrix_rank`, `norm(a, 2)`, `cond` and `lstsq` of a matrix of `nan` raise `ValueError: On entry to DLASCL parameter number 5 had an illegal value` (4 for `lstsq`) in the guest, where native Accelerate raises `LinAlgError: SVD did not converge` (EXECUTED, `fp_probe-*.out`). That is not a flag, and this specification does not change it; the README says it, and spec 100 closes it (its OpenBLAS error routine sets no Python exception). `svd` with vectors, `pinv`, `eigh` and `eigvalsh` of a `nan` matrix return all-`nan` in the guest today; after the build each raises `LinAlgError` if `lapack_lite` reported a failure, else returns as today. The builder records which, as facts in the landing notes, not as checks.

### 7. The README, the CHANGELOG and `packages.toml`

- **The platform facts list** (`README.md`, the bullets after *matplotlib in the guest*'s example, beside "**No threads**", line 315 on main): a new bullet, after "No threads":

  > - **No floating-point status flags in wasm**: arithmetic sets none, so what only the hardware signals stays silent: `np.array([1.0]) / 0`, `np.log(0.0)`, `np.sqrt(-1.0)`, `np.exp(1000.0)`, a `nan` cast to an integer and the same on numpy scalars give native's values with no `RuntimeWarning`, and `np.errstate(all="raise")` does not raise for them; check with `numpy.isfinite` where it matters. numpy's own signals are kept in software (`recipes/npy_fenv_flags.h`, spec 099): integer division by zero, integer overflow in division and float16 overflow warn, or raise under `np.errstate`, as natively, and `numpy.linalg` raises `LinAlgError` when its LAPACK finds a matrix singular or not positive definite. That LAPACK is numpy's own bundled `lapack_lite` until spec 100; native numpy's is OpenBLAS (Accelerate in the macOS 14 arm64 wheel). For a matrix singular only in exact arithmetic, LAPACKs round differently, so the guest may return finite numbers where native raises, or raise where native returns: exact singular-matrix parity is not a goal in wasm. Until spec 100, a matrix of `nan` can raise `ValueError` ("On entry to DLASCL …") where native raises `LinAlgError`, and `numpy.linalg.lstsq` of one raises `SystemError`, with that `ValueError` as its context.

  (Revised at build: the `SystemError` clause for build finding B1, and the native LAPACK named correctly after the correction of question 107; *Landing notes*.)

  **If spec 066 lands first**, its bullet "**No floating-point exception flags**" (on its branch, `README.md:318-322`, "Until spec 099 lands, …") is replaced by this one, word for word.
- ***How it is built*, the recipe files** (`README.md:623` on main): after "three rename headers for symbols that only collide in a static link,", add "a header that keeps numpy's own floating-point signals in a software flag word, since wasm has none (`npy_fenv_flags.h`),".
- **The patches row** (`README.md:41`): unchanged. It already says every other adaptation is a recipe file.
- **CHANGELOG**, under `## 0.1.0a8 — unreleased`, first (the newest landing): "**A singular matrix raises `LinAlgError`** (spec 099; spec 066's survey). wasm has no floating-point status flags, and numpy reports a failed LAPACK call by one, so `numpy.linalg.inv`, `solve`, `tensorinv`, `tensorsolve` and `matrix_power(a, -1)` of a singular matrix, and `cholesky` of one not positive definite, returned `nan`s. A recipe header, `recipes/npy_fenv_flags.h`, keeps the signals numpy raises itself in a software flag word: these raise `LinAlgError` whenever numpy's bundled LAPACK (`lapack_lite`) finds the matrix singular; for a matrix singular only in exact arithmetic that is not always where native numpy does (LAPACKs round differently; exact parity is not a goal in wasm). The same word makes integer division by zero, integer overflow in division and float16 overflow warn, or raise under `np.errstate`, as natively: a widening of the owner's question, named here. Signals only the hardware gives (float division by zero, `log(0)`, invalid casts) stay silent; the README says so." (Its singular-matrix clause revised at build after the correction of question 107.) At build it gained one sentence, for build finding B1: "One case gets worse until spec 100: `numpy.linalg.lstsq` of a matrix of `nan` raised `ValueError` from `lapack_lite` and now raises `SystemError` with that `ValueError` as its context (native: `LinAlgError`)."
- **`tests/upstream/packages.toml`: no line changes.** numpy's suite already runs (spec 050); this adds no package. **If spec 066 lands first**, its `no-fp-exceptions` class (matplotlib's `rest` group, two `test_mlab` members, `closes_with = "spec 099"`) is emptied by this specification's builder: it keeps its id, an empty member list and its closer, as `numpy.toml`'s rule for an emptied class says, and its gap goes. That is a named judge change in `--accept-judge`.
- **`context/upstream/README.md`:** a row for folder 30 at build time: "numpy | its own floating-point signals are lost where `<fenv.h>` defines no flags (wasm32), so `numpy.linalg` raises no `LinAlgError` | a facts sheet (spec 099); spec 099 keeps them by a recipe (`recipes/npy_fenv_flags.h`) until numpy does; numpy's AI policy keeps the text in the owner's words".

### 8. No new step, pin or patch

The header is a recipe file, read by the existing cross file through the existing `-include` mechanism. Step 40 already rewrites `@ROOT@` in the cross file. `scripts/` is not edited; no input is added to `downloads/SHA256SUMS`; `recipes/patches/` does not change. The drafting files under `../research/` are evidence; the builder writes the recipe fresh from Decision 3.

### 9. Where this meets other specifications

- **066** (the compiled packages' own tests). Its survey found the defect; its `no-fp-exceptions` class names this specification as its closer, and its README bullet says "Until spec 099 lands". If 099 lands first, 066's re-survey on a set with 099 sees `test_mlab`'s two cases pass, and 066 drops the class and the bullet before it lands. If 066 lands first, Decision 7 says what this builder changes. Either way the two share `README.md` (one bullet) and nothing else but the CHANGELOG.
- **044 (scikit-learn), 045 (statsmodels).** Both catch `LinAlgError` to fall back (INFERRED from their wide use of `numpy.linalg`; not read here). With this specification their fallbacks run when `lapack_lite` finds a matrix singular, which is native's decision for an exact zero pivot and may not be for a matrix singular only in exact arithmetic (Decision 6). So a golden of theirs that matched native before 099 may change after it, either way. The builder of whichever lands second re-runs those goldens; a lost pass is reported, never allowed (spec 100 narrows the divergence, it does not remove it).
- **100** (numpy's linear algebra on the set's OpenBLAS; reserved, stacked on 099, before 0.1.0, the owner's answers to questions 106 and 107). It closes Decision 6's `nan`-matrix difference (and build finding B1), narrows the singular-matrix one (249 to 254 of 300 against native OpenBLAS), and rewrites the README bullet's `lapack_lite` sentences. This specification's flag word stays: it is how numpy reports a LAPACK failure whichever LAPACK runs.
- **095** (scipy's and scikit-learn's own tests). scipy's suite also skips floating-point tests on wasm; nothing here changes its plan.
- **The upstream folder number 30** is the next free across main and the open branches (037, 038, 044, 066 and 096 go to 29). If another branch lands with 30 first, the builder renumbers.

## Intent

A program that inverts or solves a matrix numpy's LAPACK finds singular gets `LinAlgError` in the guest, as natively, and never silently computes with the `nan`s numpy's error path writes. Every signal numpy raises itself reaches `np.errstate`. Where the guest's LAPACK and native's disagree on a matrix singular only in exact arithmetic, the README says so: exact parity there is not a goal in wasm, and spec 100 narrows the gap. What the hardware alone would signal is stated plainly, held by a check, and left as it is.

## Design

| file | change |
|---|---|
| `recipes/npy_fenv_flags.h` | new (Decision 3): includes `<fenv.h>` and, in C++, `<cfenv>`; `#error` if the C library defines a flag; the five bits and `FE_ALL_EXCEPT`; the weak word `wasi_python_fe_flags`; the three `static inline` functions; their names in `std` for C++; the three `#define`s. A comment names spec 099 and says when to remove it (a toolchain whose `<fenv.h>` defines the flags, or a numpy release that keeps its own status without them) |
| `recipes/wasi-numpy.cross` | `c_args`: `'-include', '@ROOT@/recipes/npy_fenv_flags.h'` after the two rename headers. `cpp_args`: the same pair, after `-DBLAS_SYMBOL_PREFIX=…`. The comment above the two lines says why (one line, spec 099) |
| `tests/harness/scan.py` | `npy_fenv_recipe_errors`, `npy_fenv_record_errors` and `npy_fenv_records_file_errors`: check 4's rules over the recipe and numpy's compile records |
| `recipes/weak-duplicates-allowed.txt` | one entry, `wasi_python_fe_flags`, with its reason (added at the rebase onto wave 07; the build review's M1) |
| `tests/checks/test_v1_3_data_stack.py` | checks 1, 2 and 3 |
| `tests/checks/test_v1_5_rebuild_from_pins.py` | check 4 |
| `tests/unit/test_scan.py` | check 5's rows |
| `context/upstream/30-numpy-fp-status-without-fenv-flags/facts.md` | drafted here; `context/upstream/README.md` gains its row at build |
| `README.md`, `CHANGELOG.md` | Decision 7 |

No step script changes (Decision 8). No pin changes.

## The checks, first

Each is written before the change it judges, and each was, or will be, seen failing first. The three programs are the drafting files `check1_singular.py`, `check2_numpys_own_signals.py` and `check3_hardware_signals.py`, passed by `-c` as the data-stack checks pass theirs, with nothing writable; each asserts exit 0, no trap, and stdout exactly as below. Each records fuel.

1. **v1.3, `test_a_singular_matrix_raises_linalgerror[which]`** (`test_v1_3_data_stack.py`, both binaries, fast tier). Expected stdout, native's (EXECUTED, `check1_singular-native.out`):

   ```
   inv LinAlgError Singular matrix
   inv float32 LinAlgError Singular matrix
   inv complex128 LinAlgError Singular matrix
   inv stacked LinAlgError Singular matrix
   solve LinAlgError Singular matrix
   solve matrix LinAlgError Singular matrix
   tensorinv LinAlgError Singular matrix
   tensorsolve LinAlgError Singular matrix
   matrix_power -1 LinAlgError Singular matrix
   cholesky LinAlgError Matrix is not positive definite
   cholesky upper LinAlgError Matrix is not positive definite
   inv under errstate ignore LinAlgError Singular matrix
   det 0.0
   slogdet 0.0 -inf
   inv regular [[1.0, -1.0], [-1.0, 2.0]]
   errstate after {'divide': 'warn', 'over': 'warn', 'under': 'ignore', 'invalid': 'warn'}
   ```

   The last four lines are controls: `det` and `slogdet` never raised, a regular inverse is exact, and `errstate` is left as it was. Seen failing first: on main's set both binaries print `returned` on each of the first twelve lines and the last four as above (EXECUTED, `check1_singular-guest-*.out`). **Its matrices are clear of Decision 6's divergence:** LU of `[[1, 2], [2, 4]]` meets an exact zero pivot (2 − 0.5 × 4 is exactly 0 in binary floating point), and Cholesky of `[[1, 2], [2, 1]]` an exactly negative one (1 − 2 × 2 = −3), in any LAPACK; both are `lapack_lite`'s all-`nan` today (EXECUTED) and native Accelerate's raise (EXECUTED; the drafting "native" was Accelerate, question 107's correction). An exact zero or negative pivot is the same in every LAPACK (READ, the arithmetic), so the check holds unchanged when spec 100 moves numpy onto OpenBLAS.
2. **v1.3, `test_numpys_own_floating_point_signals_reach_errstate[which]`** (`test_v1_3_data_stack.py`, both binaries, fast tier). Expected stdout, native's (EXECUTED, `check2_numpys_own_signals-native.out`):

   ```
   int floor_divide by 0 returned warns RuntimeWarning divide by zero encountered in floor_divide
   int remainder by 0 returned warns RuntimeWarning divide by zero encountered in remainder
   int divmod by 0 returned warns RuntimeWarning divide by zero encountered in divmod
   int32 min floor_divide -1 returned warns RuntimeWarning overflow encountered in floor_divide
   timedelta floor_divide 0 returned warns RuntimeWarning divide by zero encountered in floor_divide
   float64 to float16 overflow returned warns RuntimeWarning overflow encountered in cast
   int scalar floor_divide 0 returned warns RuntimeWarning divide by zero encountered in scalar floor_divide
   int8 scalar add overflow returned warns RuntimeWarning overflow encountered in scalar add
   int floor_divide by 0 under raise FloatingPointError divide by zero encountered in floor_divide silent
   float16 overflow under raise FloatingPointError overflow encountered in cast silent
   int floor_divide by 0 under ignore returned silent
   ```

   The float16 lines prove the C++ half of the recipe (`cpp_args`); the scalar lines are controls that already pass. Seen failing first: on main's set lines 1 to 6 and 9 and 10 say `returned silent` on both binaries (EXECUTED, `check2_numpys_own_signals-guest-*.out`).
3. **v1.3, `test_hardware_floating_point_signals_stay_silent_as_documented[which]`** (`test_v1_3_data_stack.py`, both binaries, fast tier). It holds Decision 6 and the README's sentence. Expected stdout, the guest's (EXECUTED, `check3_hardware_signals-guest-*.out`; native warns on every line and raises on the last, `check3_hardware_signals-native.out`):

   ```
   float divide by 0 returned silent
   float floor_divide by 0 returned silent
   log 0 returned silent
   sqrt -1 returned silent
   exp 1000 returned silent
   nan to int64 returned silent
   float scalar divide by 0 returned silent
   float divide by 0 under raise returned silent
   ```

   It passes on main's set and must still pass after the build: it is the check that the recipe changed only numpy's own signals. Its docstring names the README bullet. If a future toolchain gives wasm real flags, this check turns red with the header's `#error`, and both go together.
4. **v1.5, `test_every_numpy_compile_keeps_its_floating_point_flags_in_software`** (`test_v1_5_rebuild_from_pins.py`, fast). Two parts:
   - Without a build: `recipes/wasi-numpy.cross` has exactly one `c_args` and one `cpp_args` line, and each carries `'-include', '@ROOT@/recipes/npy_fenv_flags.h'` once; the header defines the five bits, the weak word and the three renames, and holds the `#error` guard.
   - With the compile records (`needs.need("compile records")`, as spec 059's check). The need is met when any meson build has its records, so **the check reads `build/numpy-build/compile_commands.json` itself and fails, not skips, when that file is missing while the need is met** (the pre-build review's L3). An entry is read **by its compiler, not its file's extension**: its command (the `command` string or the `arguments` list) runs `scripts/wasi-cc` or `scripts/wasi-cxx` (the cross file's compilers) with `-c`. Every such entry carries `-include <path>/recipes/npy_fenv_flags.h` exactly once. On main's build that rule reads 189 entries (166 C, 23 C++) and leaves out the 9 `cython` runs (READ, the drafting count; the review counted the same 189 by both rules). Its reason in `latest.json` is the counts.

   Seen failing first: on main both parts fail (no header; 0 of 189 compiles carry it).
5. **Unit rows, `tests/unit/test_scan.py`** (no artifact needed). Each fails on main, where `npy_fenv_record_errors` does not exist:
   - records where every compiler entry carries the include give no finding;
   - a `wasi-cxx … -c` entry without it is named; a `wasi-cc … -c` entry with it twice is named;
   - an entry whose file has an unusual extension (`x.S`, compiled by `wasi-cc -c`) without the include is named: the rule goes by compiler (L3);
   - a `cython` entry, and a `wasi-cc` entry without `-c` (a link), are not read;
   - a `command` string and an `arguments` list are both read;
   - an empty record list is a finding (a build that compiled nothing cannot pass);
   - the check's file rule: the need met but `build/numpy-build/compile_commands.json` missing is a finding, not a skip (L3; on a temporary tree).

## Scope

In: Decisions 1 to 8. Out:

- **Signals only the hardware gives** (Decision 6): wasm has no flags; emulating them would mean checking every float operation, which no recipe can do.
- **numpy on OpenBLAS instead of `lapack_lite`** (Decision 4 (d)): spec 100, reserved, stacked on this one, before 0.1.0 (the owner's answers to questions 106 and 107). It closes Decision 6's `nan`-matrix difference and narrows the singular-matrix one.
- **Exact singular-matrix parity with native**: not a goal in wasm (the owner's answer to question 107); the README says so.
- **numpy's skipped wasm tests.** They stay skipped by `IS_WASM`; running them would need a judge change to numpy's staging, not this specification.
- **Sending anything upstream**: the facts sheet is for the owner.

## Acceptance criteria

1. **The checks exist and were seen failing first,** as *The checks* says, each failure recorded in the landing notes (check 3 is seen passing on main and after).
2. **The build.** From an empty `build/` in a clean clone, `scripts/build.sh` compiles every numpy C and C++ file with the header, links with no `duplicate symbol` and no `signature mismatch` (step 60's own detector), and makes a set whose binaries pass every check. `MANIFEST` names the header by hash. `LICENSES/` is unchanged.
3. **The same bytes everywhere** (spec 012): the arm64 Linux rebuild gives macOS's `SHA256SUMS`, and the release's x86_64 rebuild too.
4. **One word.** The builder shows from step 60's link map (`build/link/python.map`) that `wasi_python_fe_flags` has one definition, and that the guest's imports equal main's (`tests/public_api.txt` and the import checks unchanged).
5. **The numbers recorded** in the landing notes: both binaries' and the zip's bytes, checks 1 to 3's fuel, every other fuel row that moves (up or down), each named with its percentage, any change in the upstream groups' per-outcome counts (xfailed, xpassed; Decision 5), and, as facts on the new set and both binaries: the outcome of each `nan`-matrix case Decision 6 names (`fp_probe.py`'s lines), and `singular_probe.py`'s four counts against native with one example of each row (`to_out.py --crosstab`; Decision 6). The singular probe's counts are facts, not a pass condition: they are spec 100's starting point.
6. **The judge.** The fast tier in the worktree, green but for the growth named here; the lane's run on three cores. The lane accepts with `--accept-judge` and `--accept-growth`.
7. **The release.** A release dry run on the branch passes every job on all three systems but growth lines (AGENTS.md rule 2's "built").

## The judge's changes

- `tests/harness/scan.py`: `npy_fenv_recipe_errors`, `npy_fenv_record_errors` and `npy_fenv_records_file_errors`.
- `tests/checks/test_v1_3_data_stack.py`: checks 1 to 3. `tests/checks/test_v1_5_rebuild_from_pins.py`: check 4. `tests/unit/test_scan.py`: check 5.
- No golden output, gap, allowance or progress file is edited, and no check is weakened. Only if spec 066 lands first, its `no-fp-exceptions` class is emptied, as Decision 7 says, and named in `--accept-judge`.

## The owner's choices

None blocks the build.

1. **Question 106, answered: "Both before 0.1.0"** (`../decisions.md`, "numpy's linear algebra on OpenBLAS before 0.1.0 (question 106, 2026-10-20)"). The lane asked after the pre-build review's finding 1. This specification lands with "as natively" qualified for `lapack_lite`; spec 100 (reserved, stacked on 099) links numpy's linear algebra to the set's OpenBLAS before 0.1.0. Nothing here waits on it.
2. **Question 107, answered: "Yes, before 0.1.0"** (`../decisions.md`, "Correction and question 107"). The "native" of 099's probes and of its review was Accelerate (the oracle's `macosx_14_0_arm64` wheel), not OpenBLAS; against native OpenBLAS the guest agrees on 249 of 300 singular matrices with this specification and on 254 with spec 100. The owner kept spec 100 before 0.1.0 for its `nan`-matrix errors, numpy and scipy agreeing, a newer LAPACK and less fuel; exact singular-matrix parity is not a goal in wasm. This specification's counts stay as measured, labelled "against native Accelerate".
3. **The facts sheet for numpy** (folder 30). Nothing is sent; numpy's AI policy keeps any text in the owner's words. If numpy takes the fix, the recipe goes with the release that has it.

## For the lane

- **Kind:** build-class, not a package; in a wave it is one of the "at most two other build-class changes". It shares `recipes/wasi-numpy.cross` with any specification that changes numpy's compile flags (none open today, READ), `README.md` and `CHANGELOG.md` with 066 and every entry (textual merges), and `tests/checks/test_v1_3_data_stack.py` with spec 096's successors.
- **Pre-build review: required** (§5.6, the build recipe and the artifact set).
- **The rebuild:** step 40 (numpy), 60 (link), the snapshot, 70 (zip: `numpy/__config__.py`) and 90 change their outputs. Steps 50 (pandas), 57 (scipy) and 58 (scikit-learn) do not: their archives equal wave 07's by hash (EXECUTED). Steps 10 to 38 do not run differently. Step 60's weak-duplicate gate passes with the allow-list entry (`0 unreviewed, 0 stale patterns`).
- **The claim list** (measured on wave 07's base: the builder's rebuild from empty and fast tier on `4fac7e2`, and dry run 39454475153 on `6866dd1`; each line starts "099:"):
  - 099: **new checks (7 nodes), each passing:** `test_v1_3_data_stack.py::test_a_singular_matrix_raises_linalgerror[plain]` (fuel 1,160,431,549) and `[snapshot]` (830,157,273); `::test_numpys_own_floating_point_signals_reach_errstate[plain]` (1,159,335,453) and `[snapshot]` (829,059,005); `::test_hardware_floating_point_signals_stay_silent_as_documented[plain]` (1,156,599,764) and `[snapshot]` (826,321,490); `test_v1_5_rebuild_from_pins.py::test_every_numpy_compile_keeps_its_floating_point_flags_in_software` (no fuel; its reason `compiles 189, c 166, c++ 23, not compiles 9`). **Unit rows:** six in `tests/unit/test_scan.py` (the unit suite 1,846/1,853).
  - 099: **retired checks:** none. **Lost passes:** none (the fast tier and every dry-run shard: `lost 0`). Every upstream group's outcome counts (xfailed and xpassed included) and pass digest equal wave 07's dry run 39442080658 (numpy-core, numpy-lib, numpy-others, the eight pandas groups, cpython-a to c, -fs, -archives, on Linux, macOS and Windows; EXECUTED, the shards' records, `build/099/compare-upstream.sh`): note 8 moved nothing.
  - 099: **against the wave's other entries (042, 066; the rebase onto `66cc120`):** `test_v1_3_upstream_suites.py::test_upstream_suite[matplotlib-rest-b1]` gains two passes, 3,367 (066's) → 3,369, the two `test_mlab` KDE cases that now raise `LinAlgError`; its fuel 323,475,630,138 (066's) → 323,522,622,516 (+0.015%; EXECUTED by node id on 099's set). `test_upstream_class[matplotlib-rest-b1-no-fp-exceptions]`: 066's gap → a pass, its class emptied (the judge change in `--accept-judge`; one gap fewer). No 042 row moves with 099: its 13 member checks fail only in this worktree, whose set predates 042 (*Landing notes*).
  - 099: **rows that grow, 22** (the dry run's only red job, `judge (macos-15, own-guest)`, `grew 22`, no G7 line; its `gained 7` is 099's six guest nodes and `test_wheel_carries_the_artifact_set`, blocked locally for want of a wheel, not 099's; check 4 passed in the build job): bytes `test_v1_1_artifact_set.py::test_stdlib_zip_is_bytecode_only_and_deflated` 47,730,899 → 47,730,914; fuel, +0.0109% to +0.0846%: `test_lxml_xml_job_matches_native` (+0.0846%), `test_recursion_through_python_raises[np-frompyfunc-snapshot]` (+0.0518%), `test_savefig_rejects_a_negative_dpi` (+0.0473%), `test_packages_carry_their_metadata[snapshot]` (+0.0365%), `test_scikit_learn_reads_its_files_from_the_zip[snapshot]` (+0.0237%), `test_the_sobol_options_need_nothing_writable[plain]` (+0.0182%), `test_scipy_edges_job_matches_native[snapshot]` (+0.0169%), `test_scipys_dotted_builtins_keep_their_import_names[snapshot]` (+0.0168%), `test_machine_learning_job_matches_native[snapshot]` (+0.0151%), `test_sqlite_job_matches_native` (+0.0148%), `test_contourpy_runs_one_thread` (+0.0145%), `test_delaunay_triangulation_runs` (+0.0133%), `test_npy_files_round_trip[plain]` (+0.0133%), `test_scipy_lapack_job_matches_native[snapshot]` (+0.0133%), `test_pandas_styler_renders_from_the_zip[snapshot]` (+0.0130%), `test_numpy_and_pandas_are_builtin_at_manifest_versions[plain]` (+0.0129%), `test_modelling_job_matches_native` (+0.0117%), `test_recursion_through_python_raises[np-vectorize-snapshot]` (+0.0114%) and `[pd-map-snapshot]` (+0.0112%), `test_a_python_callbacks_exception_comes_back_through_c[snapshot]` (+0.0109%), `test_plot_contour_job_matches_native[snapshot]` (+0.0109%). The shard's other moved fuel rows are within ±0.01% (down to −0.0305%). The local fast tier's 12 red lines are among these 22.
  - 099: **bytes that shrink:** `test_binary_is_a_core_wasm_module[plain]` 93,793,855 → 93,793,595 (−260) and `[snapshot]` 98,620,293 → 98,620,033 (−260).
  - 099: **facts for spec 100:** `singular_probe.py` against native Accelerate on both binaries: 130 raise as native, 141 finite as native, 20 finite where native raises, 12 raise where native returns (the same as on `21dff9d`); `fp_probe.py`'s `nan` lines; build finding B1 (`lstsq` of `nan` raises `SystemError`).
  - 099: **`MANIFEST`**, four lines: one added (`recipes/npy_fenv_flags.h`), two changed (`recipes/wasi-numpy.cross`, `recipes/weak-duplicates-allowed.txt`), and the snapshot's `x-snapshot-zip`.
  - **The judge hash changes** in `tests/harness/scan.py`, `tests/checks/test_v1_3_data_stack.py`, `tests/checks/test_v1_5_rebuild_from_pins.py` and `tests/unit/test_scan.py`.
- **The flags** (paste-safe, with the measured numbers on wave 07's set):

  ```
  --accept "099: numpy's own floating-point signals are kept in software (recipe recipes/npy_fenv_flags.h, force-included into every numpy compile, its weak flag word allowed by name in recipes/weak-duplicates-allowed.txt): numpy.linalg raises LinAlgError when numpy's bundled lapack_lite finds a matrix singular or not positive definite (for a matrix singular only in exact arithmetic not always where native does; spec 100 narrows it), and integer division by zero, integer overflow in division and float16 overflow warn or raise under np.errstate, as natively; signals only the hardware gives stay silent, as documented; lstsq of a nan matrix now raises SystemError (build finding B1, closed by spec 100)"
  --accept-judge "099: checks that inv, solve, tensorinv, tensorsolve, matrix_power(-1) of an exactly singular matrix and cholesky of one not positive definite raise LinAlgError as natively, that numpy's own integer and float16 signals reach errstate as natively, that hardware-only signals stay silent as the README says, and that every numpy compile (by compiler, from numpy's own compile records, missing records a failure) carries the header; the npy_fenv scanners and six unit rows; and, as Decision 7 provides with 066 landing first, 066's class matplotlib-rest-b1 no-fp-exceptions emptied (its two test_mlab members pass with 099: id, match and reason kept, closes_with this specification, the expected list empty, its gap removed from known_gaps)"
  --accept-growth "099: numpy compiled with real flag bits and a software flag word (recipes/npy_fenv_flags.h): the zip +15 bytes (47,730,899 -> 47,730,914; numpy/__config__.py records the -include in both argument lines), while python.wasm and the snapshot each shrink 260 bytes; fuel moves either way on rows that run numpy ufuncs, the status read now an inlined load and bit tests where it was an out-of-line libc call: twenty-one rows up +0.0109% to +0.0846% (test_lxml_xml_job_matches_native the most), the rest within 0.01% or down; MANIFEST one recipe line added, two changed (recipes/wasi-numpy.cross, recipes/weak-duplicates-allowed.txt), and the snapshot's x-snapshot-zip line; with 066 in the wave, matplotlib-rest-b1 runs 3,369 passes (066 alone 3,367: the two test_mlab cases now raise LinAlgError) at 323,522,622,516 fuel (+0.015% on 066's measurement)"
  ```

- **Dry-run needs:** the release workflow on the branch (criterion 7), done on wave 07's base: run 39454475153 on `6866dd1` (24 jobs passed, 4 skipped, 1 red for growth only). Checks 1 to 3 passed in the macOS, Linux and Windows `own-guest` records; check 4 in the build job. The first dry run, 39432450036 on `b0e1593` (wave 06's base), stays in *Landing notes* as history.
- **044's goldens with 099** (the build review's N1; Decision 9): wave 08's integration run is the evidence that they re-run with 099, and a lost scikit-learn golden is a finding, never an allowance. Run 39454475153 already ran them: `test_machine_learning_job_matches_native` passed on all three systems (+0.0151% fuel on macOS's snapshot row).
- **The native slot:** used 08:10 to 08:25 (the first build) and 11:42 to 11:53 (the rebuild on wave 07) on 2026-10-20, and released at 11:53; no native build is pending.

## Disposition of the pre-build review

The review (`../reviews/099-numpy-singular-inverse-spec-2026-10-20.md`) re-ran the prototype under numpy's real flags and in archives, counted the compile records, and probed 300 exactly rank-deficient matrices natively and in the guest. Every finding is written in; no decision changed but the record of question 106, which the owner answered while this was revised.

- **M1 (Medium), written in.** Decision 5 limits the subset argument to the non-LAPACK raisers and names where a lost pass would show (`numpy-others`, pandas' groups, the `numpy.linalg` goldens, 044's and 045's goldens). Decision 6 gains the divergence with both probes' counts (the review's 150, 130, 12, 8; the drafting `singular_probe.py`'s 130, 141, 20, 12) and an example of each direction, and names spec 100 as its closer. The Intent, Decision 9, the README bullet, the CHANGELOG line and the flags say "when numpy's bundled LAPACK finds the matrix singular", not "as natively". Criterion 5 and the claim list have the builder record the probe as facts. Check 1's matrices are shown clear of it. Question 106's case (now spec 100's) carries the divergence. **Corrected at build** (question 107, main `3ff1871`): both probes' "native" was Accelerate, not OpenBLAS; the counts stay, labelled "against native Accelerate"; against native OpenBLAS the guest agrees on 249 of 300 with this specification and 254 with spec 100, so spec 100 narrows the divergence rather than closing it, and Decisions 6 and 9, the Intent, the README bullet, the CHANGELOG line and the flags say so.
- **L2, written in, then overtaken.** Question 106 was going under *Open*; the owner answered it first ("Both before 0.1.0", `../decisions.md`), so *The owner's choices* cites the answer and `questions-for-the-owner.md` stays "None".
- **L3, written in.** Check 4 reads numpy's own `compile_commands.json` and fails when it is missing while the need is met; it picks entries by compiler (`wasi-cc` or `wasi-cxx` with `-c`: 189 on main's build, the same as by extension); unit rows for both.
- **L4, written in.** `to_out.py` makes each `.out` from its `.json` (a header line, then the `stdout` field) and the singular probe's cross table; `run_checks.sh` calls it and says so.
- **L5, written in.** Decision 4 (f), only `FE_INVALID` real, refused with its reasons; the CHANGELOG line names the widening.
- **L6, written in.** The facts sheet's Emscripten clause is labelled INFERRED, not read here.
- **Notes 7 and 8, carried into the build.** Fuel rows may go down as well as up (Decision 5, the claim list, the growth flag); numpy's non-strict `xfail(IS_WASM)` outcomes may move, and the builder names any change in the per-outcome counts (Decision 5, criterion 5, the claim list).
- Rebased onto main `21dff9d` (context only: the owner's answers on 066 and on question 106 at `cf414a2`, and a roadmap line).

## One line

Give numpy's flags bits and a word in a recipe header, so the signals numpy raises itself reach `np.errstate`: a singular matrix raises `LinAlgError` whenever numpy's own LAPACK says so (exact parity with native's LAPACK is not a goal in wasm), integer and float16 signals as natively, and what only the hardware signals stays silent and says so.

## Landing notes

### Phase 1: what needs no fresh artifact set (2026-10-20, base main `21dff9d`)

(Built on `21dff9d`; rebased afterwards onto main `3ff1871`, whose two new commits touch only `context/`, so the set built on `21dff9d` is the set of the rebased tip.)

- **The recipe:** `recipes/npy_fenv_flags.h`, as Decision 3 says, written fresh from the decision (the drafting prototype's form: guard, five bits, weak word, three inline functions, their names in `std`, three renames), with a comment naming spec 099 and when to remove it. `recipes/wasi-numpy.cross` force-includes it in `c_args`, after the two rename headers, and in `cpp_args`, after `-DBLAS_SYMBOL_PREFIX`; one comment line set says why.
- **The judge:** checks 1 to 3 in `tests/checks/test_v1_3_data_stack.py` (their programs and expected text equal the drafting files and outputs byte for byte, EXECUTED by a comparison script); check 4 in `tests/checks/test_v1_5_rebuild_from_pins.py`; `npy_fenv_recipe_errors`, `npy_fenv_record_errors` and `npy_fenv_records_file_errors` in `tests/harness/scan.py`; six unit rows in `tests/unit/test_scan.py`. **The confirmation's point for the build review is implemented:** an entry is a compile when its first argument equals, or ends in `/` followed by, `scripts/wasi-cc` or `scripts/wasi-cxx`, and it holds `-c`; a name found elsewhere in the command (`-DX=scripts/wasi-cc`) or a lookalike path (`scripts/not-wasi-cc`) is not, and a unit row holds both.
- **Seen failing first** (EXECUTED, `build/099/seen-failing-first.log`, on a private `cp -c` copy of main's set `f12cd25c`, the checks written before the recipe): checks 1 and 2 fail on both binaries, every case `returned` or `returned silent` as the drafting runs showed; check 3 passes on both; check 4 fails on its first part (`c_args force-includes recipes/npy_fenv_flags.h 0 times`, and `cpp_args`, and the header missing). Check 4's second part, run on main's records through `scan.npy_fenv_records_file_errors`: 189 findings, one per compile (166 C, 23 C++, 9 not compiles). The unit rows fail on main by construction (the three functions do not exist there); the recipe row failed before the header was written.
- **After the recipe** (EXECUTED, `build/099/units.log`): `tests/unit/test_scan.py` 213/213, the six new rows among them; check 4's first part passes and its second part is blocked here (no compile records in this worktree's `build/`). Checks 1 and 2 cannot pass before the rebuild.
- **A smoke compile of four real numpy files** (EXECUTED, `../research/2026-10-20-numpy-floating-point-status/build_smoke.py` and `.out`): `ieee754.c`, `halffloat.cpp`, `umath_linalg.cpp` and `loops_arithmetic.dispatch.c`, each from main's own compile command with the header added, into a scratch folder: each compiles with the warning count it has without the header (0, 0, 8, 2), each carries `W wasi_python_fe_flags`, and `ieee754.c` no longer calls wasi-libc's `feraiseexcept` or `fetestexcept` (without the header it does). Not a build: the set is phase 2's.
- **`README.md`, `CHANGELOG.md`, `context/upstream/README.md`:** Decision 7's texts, written in (the platform-facts bullet after "No threads", the recipe-files clause, the CHANGELOG bullet first under `## 0.1.0a8 — unreleased`, folder 30's row).
- **`MANIFEST`** is the build's: step 90 lists every tracked file under `recipes/` and `scripts/`, so phase 2's set gains the header's `recipe` line and changes the cross file's. Nothing to write by hand.
- **Not run in phase 1:** the fast tier. Two other agents' judges were running on the machine (`pgrep -fl pytest`: 066's upstream groups with `-n 3`, 042's checks), so only single node ids and the rules check ran. ruff check and ruff format --check are green.

### Phase 2: the build (criteria 2, 4 and 5; EXECUTED 2026-10-20, macOS arm64, the native slot)

- **`scripts/build.sh` from an empty `build/`** in this worktree (the downloads `cp -c` cloned from the main tree's; step 00 verified every pin): 18 steps in 14 m 50 s, exit 0 (`build/099/build.log`). Step 40's log has 419 `warning:` lines, as main's has: the header adds none.
- **Check 4's rule on the new records:** 189 compiles (166 C, 23 C++), each force-including the header once; 9 `cython` runs not read.
- **One word** (criterion 4): `build/link/python.map` names `wasi_python_fe_flags` once, 4 bytes of `.bss`, the copy of one object (`dragon4.c.o`); every other object's weak copy was dropped.
- **The archives:** pandas' 45, scipy's 95, the plot modules' 13, lxml's 2 and regex's 1 equal main's byte for byte; numpy's 19 differ, as they must. So steps 50 and 57 are unchanged.
- **The set**, `SHA256SUMS` `7519b047…`, against main's `f12cd25c…`:
  - `python.wasm` 84,794,273 → 84,794,013 bytes (**−260**); the snapshot 89,468,144 → 89,467,888 (**−256**); the zip 44,445,945 → 44,445,960 (**+15**: `numpy/__config__.py` records the `-include` in both argument lines). The binaries shrink: each status read was an out-of-line call into wasi-libc's `fetestexcept`, now an inlined load (the pre-build review's note 7).
  - `MANIFEST` differs in exactly three lines: the new `recipe` line for `recipes/npy_fenv_flags.h`, the changed `recipes/wasi-numpy.cross` line, and the snapshot's `x-snapshot-zip` line.
  - `LICENSES/` is identical.
- **The seven new nodes pass** on the new set (`build/099/new-nodes.log`). Fuel: check 1 1,147,409,887 (plain) and 827,401,831 (snapshot); check 2 1,146,003,003 and 826,093,482; check 3 1,143,432,283 and 823,466,914; check 4 records none (its reason: compiles 189, c 166, c++ 23, not compiles 9).

### Phase 2: the facts for spec 100 (criterion 5; EXECUTED, both binaries, identical)

- **`singular_probe.py`, against native Accelerate** (the oracle's `macosx_14_0_arm64` wheel; first written here as "OpenBLAS", corrected after question 107) and the built set (`lapack_lite`), the four rows (`../research/2026-10-20-numpy-floating-point-status/singular_probe-built-crosstab-*.out`):

  | native Accelerate | built set | count | example |
  |---|---|---|---|
  | raises | raises | 130 | case 4 (n 6, rank at most 2) |
  | finite | finite | 141 | case 0 (n 7, rank at most 4) |
  | raises | finite | 20 | case 2 (n 5, rank at most 3); `inv(arange(1, 17).reshape(4, 4))` |
  | finite | raises | 12 | case 26 (n 4, rank at most 2) |

  Exactly as Decision 6 predicted from main's all-`nan` results: every all-`nan` case now raises. Against native OpenBLAS the comparison is spec 100's author's, not run here: 249 of 300 agree with `lapack_lite` and this specification, 254 with spec 100 (`../decisions.md`, "Correction and question 107").
- **`fp_probe.py` on the built set** (`fp_probe-built-*.out`): every linalg case of a singular or not positive definite matrix now raises as natively; `svd(nan)` with vectors, `pinv(nan)`, `eigh(nan)` and `eigvalsh(nan)`, all-`nan` returns on main, now raise native's `LinAlgError`; integer, timedelta and float16 signals warn as natively; hardware signals stay silent (check 3). `svd(nan, compute_uv=False)`, `svdvals`, `matrix_rank`, `norm(…, 2)` and `cond` of `nan` still raise `ValueError` (DLASCL) from `lapack_lite`, as on main.
- **Build finding B1: `lstsq` of a `nan` matrix now raises `SystemError`** (`xerbla_probe.py`, run natively, on main's set and on the built set, plain; `xerbla_probe-*.out`). numpy's `lapack_lite` error routine (`python_xerbla`) sets a Python `ValueError` and returns; `dgelsd` then reports a failure, so `umath_linalg` raises the invalid flag, and numpy's errstate calls the `LinAlgError` callback while the `ValueError` is still set. The result is `SystemError: <class 'numpy.linalg.LinAlgError'> returned a result with an exception set`, its context the `ValueError`. On main the same call raised that `ValueError`; natively (Accelerate, in this run) the error routine prints and returns, and numpy raises `LinAlgError: SVD did not converge in Linear Least Squares`. Both `lstsq` shapes probed (3×3 and 2×3) show it; `svd(nan, compute_uv=False)` does not (its call reports no failure after the error routine). INFERRED: a native numpy built with `lapack_lite` on hardware with flags does the same; it is upstream's, reached here because the flag now works. **Answer, for the build review to weigh:** it is still an exception (no call returns silently), it is narrower than what this specification fixes (the singular family, and four `nan` cases that now match native), and spec 100 removes it (OpenBLAS's error routine sets no Python exception). So it is written into Decision 7's README bullet and CHANGELOG line, not fixed here; no recipe can stop `python_xerbla` from setting an exception without a source change. Spec 100's builder adds the check that turns it into native's `LinAlgError` (a new failure mode becomes a check). If the lane or the review prefers it fixed before 099 lands, the smallest fix is a carried numpy patch to `python_xerbla`, which is spec 100's territory.
- `lstsq` of `[[inf, 1], [1, 1]]` returns in the guest, before and after; natively it raises. A LAPACK difference or a hardware flag (Decision 6), not this specification's.

### Phase 2: the fast tier (criterion 6; EXECUTED, `-n 3`, started 08:39 with no other judge running)

- `build/099/fast.log`: **`616/758 pass · 6 gap · 3 blocked · 0 fail`**, unit suite 1,831/1,838 (7 skipped); 2,447 passed, 10 skipped, 6 xfailed in 8 m 14 s. Blocked: prior-art clones, three systems, wheel (as on any worktree). The six gaps are spec 038's, as on main.
- **Ratchet:** `lost 0 · gained 7 · grew 12`. The 7 gained are this specification's new nodes. No pass is lost.
- **Every metric that moved** (`build/099/moved.txt`, latest against accepted): 85 fuel rows up, 93 down, the largest +0.033% (`test_packages_carry_their_metadata[snapshot]`) and −0.028% (`test_the_guest_package_round_trips_through_the_door[snapshot]`): numpy's status read is a few instructions different per ufunc call, either way (Decision 5, note 7). Python-only rows move by about +326 fuel each (the binary's layout). **The 12 red lines**, each above the ratchet's tolerance:
  - bytes: `test_stdlib_zip_is_bytecode_only_and_deflated` 44,445,945 → 44,445,960 (+15);
  - fuel, +0.0103% to +0.0330%: `test_packages_carry_their_metadata[snapshot]`, `test_a_pandas_warning_names_the_callers_line[plain]`, `test_dotted_builtins_keep_their_import_names[snapshot]`, `test_npy_files_round_trip[snapshot]` and `[plain]`, `test_recursion_through_python_raises[np-apply-along-axis-snapshot]` and `[np-frompyfunc-snapshot]`, `test_a_python_callbacks_exception_comes_back_through_c[plain]`, `test_pandas_styler_renders_from_the_zip[snapshot]`, `test_numpy_and_pandas_are_builtin_at_manifest_versions[snapshot]`, `test_scipy_odr_is_left_out_by_name[snapshot]`. The binaries' byte rows went down (−260 and −256), which is not growth.
- The upstream groups (slow) and the goldens did not run here; the dry run judges them on three systems.

### Phase 2: the release dry run (criteria 3 and 7; READ, run 39432450036 on `b0e1593`)

- **24 jobs passed, 4 skipped, 1 red:** `judge (macos-15, own-guest)`, `384/758 pass · 6 gap · 2 blocked · 0 fail`, ratchet `lost 0 · gained 7 · grew 15`. **Its only red lines are the 15 growth lines** in *For the lane* (the zip's 15 bytes and fourteen fuel rows within +0.0330%, three of them slow rows the local fast tier does not run: the scipy solvers golden, the Delaunay triangulation and contourpy's one thread). No G7 line. `gather` and the release-only jobs were skipped, as a red judge makes them.
- **The same bytes everywhere** (criterion 3): both Linux rebuilds (x86_64 and arm64) and "the same bytes from every host" passed; the three `verify` jobs passed; every Windows shard passed.
- **Checks 1 to 3 passed** in the macOS, Linux and Windows `own-guest` records; check 4 in the build job's record.
- **The upstream groups** (macOS and Linux shards): every group's outcome counts and pass digest equal wave 06's dry run 39398491514 (READ, the shards' `latest.json` against wave 06's): numpy-core, numpy-lib, numpy-others, pandas-frame, -groupby, -internals, -io-formats, -io-parser, -libs, -reshape, -tslibs, cpython-a, -b, -c, -fs and -archives. numpy-lib's macOS fuel moved −0.022%.
- So 099 is **built**: every red line in its dry run is a growth line it claims.

### The builder's self-check

```
- rebased onto main's tip today: main 3ff1871 (the build ran on 21dff9d; 3ff1871 adds context only);
- CI run dispatched on this exact commit and read: 39432450036 on b0e1593; red lines GREW only
  (15); the Windows legs green;
- every number from a measured run on this base, labelled EXECUTED; the growth list is this
  build's (the fast tier's 12 and the dry run's 15), not the draft's;
- "For the lane": the claim list, the three flags each beginning "099", the wave kind
  (build-class, not a package), dry-run needs met;
- every new check seen failing first (checks 1, 2 and 4 on main's set; check 3 passes there by
  design); the Windows, Linux and macOS guest shards each ran checks 1 to 3;
- no gap added; reserved follow-up spec 100 has its roadmap line (main 3ff1871);
- packages.toml: no line changes (Decision 7); README rows: the platform-facts bullet and the
  recipe-files clause; context/upstream/README.md: folder 30's row;
- CHANGELOG under the one unreleased section (0.1.0a8 — unreleased); no new question (106 and
  107 answered);
- ruff check, ruff format --check, the fast tier: green but for the claimed growth, output in
  build/099/.
```

### For the build review: what to weigh

- **Build finding B1** (Phase 2, the facts): `lstsq` of a `nan` matrix now raises `SystemError` where main raised `ValueError`. Written into the README and CHANGELOG, closed by spec 100, not fixed here.
- **The correction of question 107**: the probes' "native" was Accelerate; the text says so throughout.

### After the build review: rebased onto wave 07 and rebuilt (2026-10-20, EXECUTED)

The build review (`../reviews/099-numpy-singular-inverse-build-2026-10-20.md`) said "lands once M1 is closed": main `2516875` (wave 07: 038, 044) added spec 044's weak-duplicate gate to step 60, and 099's weak flag word, defined in 13 numpy archives, would stop it.

- **The rebase** onto main `2516875`: all eight commits replayed with **no conflict hunk** (`build/099/rebase-07.log`). The CHANGELOG bullet stays first under `## 0.1.0a8 — unreleased`, above 096's and wave 07's.
- **M1 closed by the allow-list**, the lane's recommended form: `recipes/weak-duplicates-allowed.txt` gains one line, `wasi_python_fe_flags`, with its reason (every copy the same zero-filled 4-byte int; sharing one object across files is the point, not state of one file; `python.map` shows one definition). It touches `recipes/` only, so step 60 and spec 100's change to it are untouched. `recipes/npy_fenv_flags.h`'s comment names the entry. The list parses with the gate's own reader (20 patterns); `tests/unit/test_sklearn_build.py` and `tests/unit/test_scan.py` pass (223). Chosen over a single strong definition (an `extern` in the header and a recipe C file linked by step 60) because it changes no script, and spec 100 also edits step 60.
- **The rebuild from empty** on `4fac7e2` (the worktree's `build/` emptied, wave 07's new pins cloned in; `df -h ~` 56 GiB free; `build/099/build-07.log`): 19 steps in 11 m 25 s, exit 0, ended 11:53. Step 60's gate: `weak duplicates: 270 archives, 21964 weak names, 0 unreviewed, 0 stale patterns`. `python.map` names `wasi_python_fe_flags` once, 4 bytes of `.bss`, from one numpy object (`dragon4.c.o`). Step 40: 189 compiles carry the header, 419 warnings as main's. Only numpy's 19 archives differ from wave 07's; pandas' 45, scipy's 95, scikit-learn's 69, the plot modules' 13, lxml's 2 and regex's 1 are equal by hash.
- **The set**, `SHA256SUMS` `5f203242…`, against wave 07's `dc6ba3a5…`: `python.wasm` 93,793,855 → 93,793,595 (−260); the snapshot 98,620,293 → 98,620,033 (−260); the zip 47,730,899 → 47,730,914 (+15). `MANIFEST` differs in four lines: the header's new `recipe` line, the changed `recipes/wasi-numpy.cross` and `recipes/weak-duplicates-allowed.txt` lines, and the snapshot's `x-snapshot-zip`. `LICENSES/` is identical.
- **The seven new nodes pass** (`build/099/new-nodes-07.log`): check 1 1,160,431,549 (plain) and 830,157,273 (snapshot); check 2 1,159,335,453 and 829,059,005; check 3 1,156,599,764 and 826,321,490; check 4 `compiles 189, c 166, c++ 23, not compiles 9`.
- **The facts for spec 100 hold unchanged** on both binaries (`*-wave07-*.out`): the singular probe's cross table equals the first build's byte for byte (130, 141, 20, 12 against native Accelerate), and `lstsq` of `nan` still raises B1's `SystemError`.
- **The fast tier** (`-n 3`, started 11:56 with no lane lock and no other judge; `build/099/fast-07.log`): `636/776 pass · 0 gap · 3 blocked · 0 fail`, unit suite 1,846/1,853; ratchet `lost 0 · gained 7 · grew 12`. 33 fuel rows up and 161 down, from +0.0518% to −0.0303%. The 12 red lines: the zip (+15 bytes) and eleven fuel rows from +0.0109% to +0.0518% (`test_recursion_through_python_raises[np-frompyfunc-snapshot]` the most).
- **The release dry run on wave 07's base** (READ, run 39454475153 on `6866dd1`, dispatched when fewer than three runs were live): 24 jobs passed, 4 skipped, 1 red, `judge (macos-15, own-guest)`: `406/776 pass · 0 gap · 2 blocked · 0 fail`, ratchet `lost 0 · gained 7 · grew 22` (the 7 gained there are 099's six guest nodes and `test_wheel_carries_the_artifact_set`, blocked locally for want of a wheel, not 099's; check 4 passed in the build job), no G7 line. **Its only red lines are the 22 growth lines** in *For the lane* (the zip's 15 bytes and 21 fuel rows from +0.0109% to +0.0846%, slow goldens among them). Both Linux rebuilds, the same-bytes job, the three `verify` jobs and every Windows shard passed. Checks 1 to 3 passed in all three systems' `own-guest` records, check 4 in the build job; scikit-learn's goldens passed on all three. Every upstream group equals wave 07's dry run 39442080658 in outcome counts and pass digest. So 099 is built on wave 07's base: every red line is a growth line it claims.
- **The owner's new CI rule** (main `30e9b41`, AGENTS.md rules 2, 3a and 8): this run stands, because the rebase added a code change (the allow-list entry). A later rebase onto wave 08's tip that only resolves named conflict hunks, with the fast tier green, dispatches no new run; the wave's dry run is the check.

### Rebased onto wave 08's tip (2026-10-20, `origin/wave/08` = `66cc120`: 042, then 066, on main `2516875`)

The confirming review (`../reviews/099-numpy-singular-inverse-confirm-2026-10-20.md`) says lands; its Disposition is written (L1 carried by spec 100 at its restack, N1's clause written in above). `git rebase origin/wave/08` replayed 099's fifteen commits. **Five conflict hunks**, in three commits, each resolved as 099's builder; the progress files are the wave's and were not touched:

1. **`context/upstream/README.md`** (the phase 1 commit): 066's rows 32 and 33 against 099's row
   30. Kept all three, in folder order: 30, 32, 33.
2. **`CHANGELOG.md`** (the phase 1 commit): 066's bullet against 099's, both new under `## 0.1.0a8 — unreleased`. Kept both, 099's first (the wave's last entry is the newest), then 066's, then 096's; one blank line between bullets. Later commits' edits to 099's bullet (B1's sentence, question 107's correction) then applied cleanly.
3. **`README.md`** (the phase 1 commit): 066's platform-facts bullets against 099's. As Decision 7 says for 066 landing first, 066's bullet "**No floating-point exception flags**" ("Until spec 099 lands, …") is replaced word for word by 099's "**No floating-point status flags in wasm**"; 066's four other new bullets (`__file__`, Pillow without `mmap`, no `resource`, at most 4 GiB) are kept, after it.
4. **`README.md`** (the phase 2 commit): the same bullet's last line, where phase 2 adds the `lstsq` `SystemError` clause, against 066's bullets after it. Took 099's two lines; kept 066's four bullets.
5. **`README.md`** (question 107's correction): the same bullet's `lapack_lite` sentences, corrected on 099's side, against 066's bullets. Took 099's corrected sentences; kept 066's four bullets.

**One judge change beyond the hunks, the one Decision 7 provides for "if 066 lands first"** (commit `352d219`): 066's class `no-fp-exceptions` (`tests/upstream/matplotlib.toml`, group `matplotlib-rest-b1`, two `test_mlab` members) is emptied, as spec 041 emptied `styler-templates`: it keeps its id, match and reason (now in the past tense), its `closes_with` becomes this specification, `tests/upstream/expected/matplotlib-rest-b1/no-fp-exceptions.txt` is empty, and its `[[gap]]` leaves `tests/known_gaps.toml`. 066's own spec names this as 099's to do (its *For the lane*, "099's order").

**Checked after the rebase** (EXECUTED; the worktree's set is 099's on wave 07, `5f203242`, built before 042, so 042's members are not in it; no rebuild):

- **The fast tier** (`-n 3`, started 13:26 with no lane lock and no other fast tier; `build/099/fast-08.log`): `631/850 pass · 0 gap · 4 blocked · 13 fail`, unit suite 1,878/1,885; ratchet `lost 6 · gained 8 · grew 11`. **The 13 failures are 042's member checks on a set without its members, blocked in this worktree, as 066 saw on the same kind of set**: `test_artifact_set_is_complete`, `test_manifest_is_well_formed`, `test_manifest_recipes_match_the_tree`, `test_seaborn_notice_carries_its_vendored_licences`, `test_reportlab_notice_carries_its_third_party_parts`, `test_licence_notices_cover_every_component`, `test_packages_carry_their_metadata[plain]` and `[snapshot]`, `test_reportlab_runs_its_pure_paths[plain]` and `[snapshot]`, `test_seaborn_takes_its_scipy_paths[plain]` and `[snapshot]`, `test_reportlab_writes_a_pdf_with_nothing_writable`. The 6 lost are six of those 13. **No 099, numpy, pandas or CPython row fails.** Gained 8: 099's seven and 042's `test_reportlab_fonts_are_not_in_the_zip`. Grew 11: the zip's 15 bytes and ten fuel rows of 099's claim (+0.0109% to +0.0518%).
- **`matplotlib-rest-b1`, run by node id** (the upstream kit cloned from the main tree's pinned wheels; `build/099/rest-b1.log`): `test_upstream_suite[matplotlib-rest-b1]` passes with **3,369 passes** (066 measured 3,367: the two `test_mlab` cases now pass) and 12 failures, all `no-processes`'s; fuel 323,522,622,516 (066's 323,475,630,138, +0.015%). `test_upstream_class[matplotlib-rest-b1-no-fp-exceptions]` **passes** with its empty list; `[matplotlib-rest-b1-no-processes]` stays a gap, 12 findings, digest `f80d3722a2b8`, unchanged.
- **No run dispatched.** The hunks are text, and the class change is the judge change Decision 7 names; the wave's dry run judges both (the owner's rule). The lane decides if the class change needs its own run.

### Landed in wave 08

- Its confirming review's L1 (the allow-list reason's archive count, 17 not 13, and a long header line) is carried by spec 100 at its restack, as the Disposition says.
- The judge edit beyond the rebase hunks (066's class `no-fp-exceptions` emptied, its closer this spec) was checked by the integration review against 066's spec and Decision 7.
- Reviews: `../reviews/099-*` and the wave's integration review.
