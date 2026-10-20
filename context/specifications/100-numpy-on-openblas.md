# 100 — numpy's linear algebra, `dot` and `matmul` run on the set's OpenBLAS

- **Status:** **drafted 2026-10-20** on `spec/100-numpy-on-openblas` from main `cf414a2`, with
  its drafting runs. It changes the build recipe and the artifact set, so it is **reviewed before
  it is built** (constitution §5.6). It is **stacked on spec 099** (§4.14): it is built from
  099's reviewed build tip once 099 is built and reviewed, and the header names that base commit
  then. A different agent reviews the build.
- **Date:** 2026-10-20
- **Owner:** Clay Gendron
- **Kind:** **build-class** (§5.7): step 40 finds the set's OpenBLAS through the pinned `pkgconf`
  and builds numpy against it; three new recipe files (`recipes/numpy_lapack_abi.h`,
  `recipes/numpy_lapack_shims.c`, `recipes/numpy_file_includes.txt`); `recipes/wasi-numpy.cross`
  and `scripts/steps/60_link.sh` change. It changes `python.wasm`, the snapshot and the stdlib zip
  (`numpy/__config__.py`), and `MANIFEST` gains three `recipe` lines and changes one. No carried
  patch, no new pin. It fixes a package already in the set and adds none, so it is not a package
  entry in a wave. **And a judge change:** four new checks (seven nodes), one scan function and its
  unit rows, and the oracle's numpy pin on macOS arm64 (Decision 7). The lane accepts with
  `--accept-judge` and `--accept-growth`. The guest's imports and exports do not change; no line
  of `tests/public_api.txt` changes.
- **Depends on:** **099** (numpy's floating-point signals in software; stacked: without it no
  LAPACK failure reaches `LinAlgError` at all). Landed: 037 (OpenBLAS 0.3.34 in the set, step 38,
  its `void` convention, scipy's shims and the per-file include map), 003 (numpy's cross build),
  059 (the compile records), 012 (the same bytes from any host), 069 (the snapshot pre-imports no
  package). It meets 044, 045, 066 and 095 (Decision 12).
- **Research it stands on:** the owner's answer to question 106 (`../decisions.md`, "numpy's
  linear algebra on OpenBLAS before 0.1.0"); spec 099's draft and its pre-build review (finding 1,
  the 300-matrix probe); spec 037's research on OpenBLAS's one return convention. **The drafting
  runs** (EXECUTED 2026-10-20 on macOS arm64, in this worktree, on a private `cp -c` copy of main's
  set, wave 06's, `SHA256SUMS` `f12cd25c…`, `build/lane.lock` absent; native runs on the oracle's
  CPython 3.15.0, once with the oracle's own venv and once with a private venv holding numpy
  2.5.2's `macosx_11_0_arm64` wheel and scipy 1.18.1's `macosx_12_0_arm64` wheel, each checked
  against its hash in `tests/jobs/oracle/uv.lock`): programs, scripts and outputs are in
  `../research/2026-10-20-numpy-on-openblas/`. Its scripts read `$REPO` (a checkout) and `$WORK`
  (a scratch folder holding the set's copy, the compile cache and the venv).

## The problem

numpy in the guest is built with no BLAS. So it runs its bundled `lapack_lite`: an f2c
translation of LAPACK 3.2.2 and the reference BLAS, inside numpy's own two linear-algebra
modules. scipy, in the same binary, runs OpenBLAS 0.3.34 (spec 037). Natively, numpy's wheels run
OpenBLAS too.

Spec 099's pre-build review found that the two LAPACKs disagree on which exactly singular matrices
fail. Matrices of `nan` also fail differently: numpy's `lapack_lite` raises `ValueError: On entry
to DLASCL parameter number 5 had an illegal value`, where native numpy raises `LinAlgError`. The
owner chose on 2026-10-20 to move numpy's linear algebra onto the set's OpenBLAS before 0.1.0,
"so its results and errors match native numpy on OpenBLAS" (question 106).

This specification does that. It also corrects one fact the decision rested on (Decision 1) and
says plainly what an OpenBLAS link can and cannot make native.

## Decisions

### 1. What the drafting found about "native" (EXECUTED)

- **The review's "native" was Apple's Accelerate, not OpenBLAS.** The oracle's venv on macOS arm64
  holds numpy's `macosx_14_0_arm64` wheel (its `WHEEL` file), and `numpy.show_config()` there
  names `accelerate` for BLAS and LAPACK. Spec 037 pinned scipy's oracle to the OpenBLAS wheel on
  that platform; numpy was left to uv, which takes the Accelerate wheel there. The 300-matrix probe
  run on that venv reproduces the review's table exactly: 150, 130, 12 and 8 (`crosstab.txt`,
  `nat_accel_inv vs guest_lite_inv`).
- **Native numpy on OpenBLAS** (the `macosx_11_0_arm64` wheel: scipy-openblas 0.3.34, the same
  OpenBLAS release as the set's, `USE64BITINT`, kernel `neoversen1`) raises `LinAlgError` on 107
  of the 300 matrices and returns finite numbers on 193 (`singular300-native-openblas.out`). It
  gives the same 300 letters, and bit-identical inverses, under OpenBLAS's `ARMV8` and `CORTEXA57`
  kernels too (`OPENBLAS_CORETYPE`, `singular300-native-openblas-*.out`).
- **The guest's OpenBLAS is what numpy would call.** numpy's `inv` calls `?gesv` against the
  identity. Natively, numpy's `inv` raises exactly when scipy's `lapack.dgesv(a, I)` reports
  `info > 0` (300 of 300), and the 193 finite inverses are bit-identical
  (`proxy_check-native-openblas.out`). So scipy's `dgesv` in today's guest stands for numpy on the
  set's OpenBLAS (INFERRED from that identity).

The 300 matrices, four ways (EXECUTED, `crosstab.txt`; E raises or `info > 0`, F finite):

| | native, OpenBLAS | native, Accelerate | guest today, `lapack_lite` (with 099) | guest, the set's OpenBLAS (this spec) |
|---|---|---|---|---|
| raises `LinAlgError` | 107 | 162 | 158 | 153 |
| agrees with native OpenBLAS | 300 | 243 | 249 | **254** |
| agrees with native Accelerate | 243 | 300 | 280 | 279 |
| agrees with the guest's scipy | — | — | 291 | **300** |

- **So OpenBLAS alone does not make exactly singular matrices native.** After this specification
  the guest still differs from native numpy on OpenBLAS on 46 of the 300. In every one the guest
  raises and native returns a finite inverse; native's smallest pivot there is a rounding residue
  between 4.9e-32 and 7.8e-16, so its "inverse" has entries near 1e16 or larger (`divergence.txt`).
  27 of the 46 are integer matrices; 19 are scaled by 0.1.
- **Why (INFERRED, with a model).** The guest's OpenBLAS is the same source as native's, but wasm
  has no fused multiply-add, and every compile here carries `-ffp-contract=off` (spec 059). Native
  arm64 fuses `a - l*u` into one rounding. Whether an exactly singular matrix meets an exact zero
  pivot depends on that rounding. A pure-Python LU with partial pivoting agrees with the guest's
  OpenBLAS on 280 of 300 when it rounds twice, and with native OpenBLAS on 268 when it fuses
  (`fma_model.py`, `fma_model.txt`). No recipe can give wasm a deterministic fused multiply-add.
  Native numpy itself is not one answer: Accelerate and OpenBLAS on the same Mac agree on 243.
- **`nan` matrices do become native.** For a 3×3 matrix of `nan`, every LAPACK routine numpy calls
  returns the same `info` on the guest's OpenBLAS as on native OpenBLAS: `dgesdd` −4 (both jobs),
  `dsyevd` 2, `dgelsd` 2 (with a queried `lwork`), `dgesv` 0, `dpotrf` 0, `dgeqrf` 0
  (`nan-guest-plain.out`, `nan-native-openblas.out`). With 099, numpy raises `LinAlgError` exactly
  when `info != 0`. So the `svd` family, `lstsq`, `eigh` and `eigvalsh` raise `LinAlgError` as
  natively, and `inv`, `solve`, `cholesky`, `qr` and `det` return `nan`s as natively (INFERRED from
  the equal `info` codes and 099's mechanism; check 3 holds it).

This changes the case for question 106, not its answer. The owner's choices (107) asks the owner
to confirm with these numbers. Until answered, this specification is built as the owner decided.

### 2. How numpy's meson finds the set's OpenBLAS (READ and EXECUTED)

- **numpy's own meson logic** (`numpy/meson.build:56-214`, READ): with `-Dblas=openblas` it tries
  pkg-config `scipy-openblas`, then `dependency('openblas', modules: ['cblas', 'interface: lp64'])`;
  with `-Dlapack=openblas`, `dependency('openblas', modules: ['lapack', 'interface: lp64'])`. A
  found BLAS adds `-DHAVE_CBLAS` to every compile that uses it. A found LAPACK drops
  `lapack_lite`'s eight f2c sources from both linear-algebra modules
  (`numpy/linalg/meson.build:5-17`).
- **numpy's vendored meson** finds OpenBLAS by pkg-config, then confirms it by linking a probe that
  calls `dgemm_`, `cblas_dgemm` and `zungqr_` (`blas_lapack.py:378-413`, `OpenBLASPkgConfigDependency`,
  READ). That probe links against `build/openblas-wasi/lib/libopenblas.a` through the SDK's clang:
  exit 0, three warnings from its `void f()` prototypes and nothing else (EXECUTED,
  `meson_probe.sh`, `meson_probe.out`).
- **The pkg-config file is OpenBLAS's own**, written by step 38's `make install`
  (`build/openblas-wasi/lib/pkgconfig/openblas.pc`), which scipy's step 57 already uses.
- **Step 40's changes:**
  - It stops, naming step 38, unless `build/openblas-wasi/lib/libopenblas.a` and its `openblas.pc`
    exist.
  - It sets `PKG_CONFIG_LIBDIR` and `PKG_CONFIG_PATH` to `build/openblas-wasi/lib/pkgconfig`
    alone, so no host's `openblas.pc` can be found (step 57's rule).
  - Its meson line takes `-Dblas=openblas -Dlapack=openblas -Dallow-noblas=false
    -Duse-ilp64=false` in place of `-Dallow-noblas=true -Dblas=none -Dlapack=none`. **`allow-noblas`
    turns false so a failed detection stops the build**: with it true, numpy falls back to
    `lapack_lite` silently (`numpy/meson.build:182-183`).
  - After the install it stops unless the installed `numpy/__config__.py` names `openblas` for
    both BLAS and LAPACK, and unless `build/numpy-build` holds no `lapack_lite_f2c*.o` object.
- **The cross file** gains `pkg-config = '@ROOT@/build/tools/pylib/pkgconf/.bin/pkgconf'` (step
  10's pinned pkgconf, as `wasi-scipy.cross` names it) and `cmake = '@ROOT@/build/no-cmake'` (no
  CMake method, as scipy's), in place of `pkg-config = 'false'`. Both argument lines lose
  `-DBLAS_SYMBOL_PREFIX=numpy_lapack_lite_`, and its four-line comment goes: with no `lapack_lite`
  in the link, nothing needs it.

### 3. LP64, plain names, one OpenBLAS (EXECUTED)

- **The set's OpenBLAS exports plain LP64 names.** `libopenblas.a` defines `dgesv_`,
  `cblas_dgemm`, `xerbla_` and the rest with no prefix and no suffix (`llvm-nm`,
  `meson_probe.out`); its `openblas.pc` says `USE_64BITINT=` (empty). scipy is built LP64 against
  it (spec 037, Decision 6: "No ILP64").
- **numpy takes LP64.** `use-ilp64` is false by default, and numpy then asks for `interface:
  lp64`, finds no symbol suffix (`blas_lapack.py:431-433`) and compiles `CBLAS_INT` as `int`
  (READ). Native wheels are ILP64 (scipy-openblas64, suffix `64_`). The difference shows only for
  an array dimension above 2³¹ − 1, which wasm32's 4 GiB memory cannot hold.
- **One OpenBLAS, never two.** An ILP64 numpy would need a second OpenBLAS, built with
  `INTERFACE64=1`, beside scipy's: two copies of every routine, about 5 MB more. Refused. scipy's
  modules' `.deps` name `build/openblas-wasi/lib/libopenblas.a` by path; numpy's will name the same
  archive, by path or as `-L` its folder and `-lopenblas`; step 60 sorts and dedups the archives
  and the `-L` and `-l` lines it links (`sort -u`), and wasm-ld takes an archive's member once
  (READ, `60_link.sh`). Check 4 holds it.
- **Everything numpy calls is already linked.** scipy's `cython_lapack` already pulls every LAPACK
  routine numpy calls into `python.wasm` (5,267,661 bytes from `libopenblas.a`, 5,788 map entries,
  `map_sizes.txt`). What comes in new is OpenBLAS's CBLAS layer: no `cblas_` symbol is linked
  today (0 lines in main's link map), and numpy's core calls 22 of them (Decision 6).

### 4. The ABI: numpy declares `int`, OpenBLAS defines `void` (READ and EXECUTED)

- **The clash.** numpy declares every LAPACK subroutine, and the four BLAS `?copy` routines, as
  returning `fortran_int` (`umath_linalg.cpp:98-405`, `lapack_litemodule.c:41-69`, READ). The
  set's OpenBLAS defines each of them `void`, as LAPACK's Fortran subroutines are and as scipy's
  f2py declares them (spec 037's convention). wasm-ld reads the wasm signature of each: 54 routines
  numpy declares, all present, all `void` but `sdot_` (`f32`) and `ddot_` (`f64`), and `xerbla_`
  takes three arguments (EXECUTED, `sigs.sh`, `sigs.txt`). numpy's `?dotc` and `?dotu` are already
  declared `void` with a result pointer, and match.
- **A mismatch is a trap.** wasm-ld warns and links a stub that traps. The prototype compiled
  numpy's three linear-algebra files and its six CBLAS callers with main's own compile commands as
  a found BLAS would (`-DHAVE_CBLAS`, no prefix), each `python_xerbla.c` in its module's archive,
  and linked them against `libopenblas.a`: **36 signature mismatches**, the 35 routines numpy
  calls and `xerbla_` (EXECUTED, `prototype/proto.py`, `proto.txt`, variant A). Step 60's detector
  would stop the build on each.
- **The fix: numpy's own hook, per file, and one shim per routine.**
  - `recipes/numpy_lapack_abi.h` is one line: `#define BLAS_SYMBOL_PREFIX wasi_numpy_`, with a
    comment naming this specification. `npy_cblas.h` defines the prefix only `#ifndef` (READ,
    `npy_cblas.h:49-50`), so a force-included definition wins. Every `BLAS_FUNC(name)` in the files
    that get it becomes `wasi_numpy_name_`.
  - **Per file, through spec 037's map.** `recipes/numpy_file_includes.txt` force-includes the
    header into `numpy/linalg/umath_linalg.cpp` (one compile), `numpy/linalg/lapack_litemodule.c`
    (one), `lapack_lite/python_xerbla.c` (two: numpy compiles it into both modules) and
    `common/python_xerbla.c` (one: `_multiarray_umath` compiles it once a BLAS is found,
    `numpy/_core/meson.build:1186-1190`). Step 40 sets `WASI_CC_FILE_INCLUDES` and its log as step
    57 does, and stops unless each entry matched exactly its count. `scripts/wasi-cc` does not
    change.
  - **Why per file:** numpy's core calls OpenBLAS's CBLAS directly, and its 22 `cblas_*`
    declarations already match OpenBLAS's (0 mismatches in both variants, EXECUTED). A prefix there
    would need 22 more shims for nothing.
  - `recipes/numpy_lapack_shims.c` defines, for each of the 54 names numpy's two files declare but
    `xerbla`, `wasi_numpy_<name>_` with numpy's prototype. A subroutine's shim calls OpenBLAS's
    `void` routine and returns 0, what an f2c subroutine returns; `wasi_numpy_sdot_` and
    `wasi_numpy_ddot_` return OpenBLAS's value; the four `?dot?` shims pass the result pointer.
    Step 40 compiles it alone, with no numpy flag and no rename header, into
    `build/numpy-shims/libnumpy_lapack_shims.a`, as step 57 compiles scipy's. Step 60 links it beside
    scipy's shims. The builder writes it by hand with numpy's typed prototypes; the drafting copy
    (`prototype/numpy_lapack_shims.c`, from `make_shims.py`) has `void *` arguments and proves only
    the wasm signatures.
  - **The prototype with the fix:** 0 signature mismatches, 0 duplicate symbols; `xerbla_` and
    `dgesv_` defined once, by OpenBLAS; `wasi_numpy_xerbla_` and `wasi_numpy_dgesv_` once each
    (EXECUTED, `proto.txt`, variant B). `umath_linalg.o` calls 35 `wasi_numpy_*` names and no plain
    LAPACK name (`llvm-nm -u`).
- **`xerbla`: OpenBLAS keeps its own, numpy keeps its own, as natively.** numpy's
  `python_xerbla.c` raises `ValueError` from inside LAPACK. Natively it never sees OpenBLAS's
  errors: the shared OpenBLAS calls its own `xerbla`, which prints ` ** On entry to DORGQR parameter
  number  5 had an illegal value` to stdout and returns; `lapack_lite.dorgqr(…, lda=0, …)` then
  returns `{'dorgqr_': 0, 'info': -5}`, while `lapack_lite.xerbla()` still raises numpy's
  `ValueError` (EXECUTED, `xerbla-native-openblas.out`). In a static link, numpy's three
  `python_xerbla.o` would take OpenBLAS's `xerbla_` calls and mismatch them (variant A). With the
  prefix they define `wasi_numpy_xerbla_`, which only `lapack_lite.xerbla()` calls; OpenBLAS's
  `xerbla_` stays OpenBLAS's. The guest then behaves as native on both lines (today it raises
  `ValueError` on the second, `xerbla-guest-plain.out`).
- **The return value.** `lapack_litemodule.c` returns the subroutine's value in its dict
  (`'dorgqr_'`); natively it reads 0 (above), and the shim returns 0. `umath_linalg.cpp` reads only
  `info`.
- **Every call is direct.** numpy never takes a LAPACK routine's address (READ: every `FNAME(...)`
  is a call or a declaration). So a shim with the wrong argument count, on either side, is a
  signature mismatch step 60's detector stops on; no function-pointer gate is needed, unlike
  scipy's f2py modules.

### 5. Threading stays off (READ)

The set's OpenBLAS is built with `USE_THREAD=0 USE_LOCKING=0 NUM_THREADS=1` (step 38) and its
configuration says `MAX_THREADS=1` and `USE_OPENMP=0`; numpy keeps `-Ddisable-threading=true`.
Nothing here changes either. Check 1 reads both from numpy's own configuration. `USE_LOCKING=0`
is safe because a guest has one thread; each instance has its own memory.

### 6. `dot` and `matmul` move to OpenBLAS too (EXECUTED)

- **numpy cannot use a BLAS without CBLAS**, and native numpy always has it. With a found BLAS,
  `_multiarray_umath` compiles `cblasfuncs.c` and its `HAVE_CBLAS` paths in `matmul`, `dot`,
  `vdot`, `arraytypes` and `ufunc_type_resolution` (READ). They call 22 CBLAS routines:
  `?gemm`, `?gemv`, `?syrk`, `?axpy`, `sdot`, `ddot` and the four `?dot?_sub` (EXECUTED, `llvm-nm
  -u` on the prototype's objects).
- **The other way, refused:** `-Dblas=none -Dlapack=openblas` would give numpy LAPACK without
  CBLAS, a configuration native numpy never ships (`numpy/meson.build:106-107`: "we can only use a
  BLAS which provides a CBLAS interface").
- **Speed** (fuel in today's guest, one 200×200 float64 matrix, per call, numpy's own code against
  the same routine on the set's OpenBLAS through scipy; `fuel-ops.txt`): `inv` 174.5 M against
  105.0 M (0.60); singular values 243.5 M against 170.4 M (0.70); `eigh` 415.9 M against 262.6 M
  (0.63); `matmul` 157.7 M against 69.3 M (0.44). On a 3×3 matrix, 2,000 calls (`fuel-small.txt`):
  `matmul` 18.1 k against 17.7 k per call and `inv` 66.2 k against 28.4 k, scipy's wrappers
  included, so small calls do not cost more.
- **Results.** The low bits of a product change, and they come no closer to native (EXECUTED,
  `matmul-compare.txt`, a 64×64 product): native numpy on OpenBLAS and on Accelerate agree to the
  bit on all 4,096 entries; the guest's numpy loop matches native on 1,250 (largest difference 8,318
  units in the last place, on an entry near zero), and the guest's OpenBLAS `dgemm` on 656 (6,018).
  The golden jobs print 9 significant digits (`numpy_csv`'s `det` and `inv`) or 6 (`modelling`'s
  `lstsq`), well above this (READ, `tests/jobs/*.py`).
- **Memory.** OpenBLAS maps a 16 MiB buffer at its first level-3 call (README). A numpy `matmul`
  or decomposition now pays it, as a scipy call already does; the default memory limit is 1 GiB.

### 7. The oracle's numpy on macOS arm64 is the OpenBLAS wheel (judge change)

- **Why.** The question's reference is native numpy on OpenBLAS, and Decision 1 shows the oracle
  runs Accelerate on the recording platform. The Linux and Windows wheels already bundle
  scipy-openblas. Spec 037 made the same choice for scipy.
- **What.** `tests/jobs/oracle/pyproject.toml`: `"numpy==2.5.2"` becomes two lines, as scipy's
  are: the `macosx_11_0_arm64` wheel's URL for `sys_platform == 'darwin' and platform_machine ==
  'arm64'` (its SHA-256 `50a68f4b…c2c6842` is already in the lock), and `numpy==2.5.2` elsewhere.
  The pinned uv rewrites `uv.lock`. The comment above says why, naming this specification.
- **What it moves.** Nothing expected: a 64×64 product is bit-identical between the two wheels
  (Decision 6), and the goldens print 9 or 6 digits. The builder runs
  `test_goldens_reproduce_under_the_pinned_oracle` on the new venv; a changed golden is a finding,
  never an edit.

### 8. The options weighed

- **(a) numpy's prefix hook per file, and shims. Chosen** (Decision 4): a recipe, numpy's own
  designed hook, no source change, and the existing per-file map.
- **(b) The prefix globally in the cross file, and 22 CBLAS shims more.** It works, but adds a
  shim for every call whose signature already matches. Refused (§6.4).
- **(c) A rename header of 54 `#define dgesv_ wasi_numpy_dgesv_` lines.** It also works (the
  pasted name is rescanned), but restates by hand what the prefix says in one line. Refused.
- **(d) A carried numpy patch declaring the subroutines `void`.** It is the right shape upstream,
  but §4.1 puts a recipe first, and (a) needs no source change. Refused here.
- **(e) LAPACK without CBLAS.** Refused (Decision 6).
- **(f) An ILP64 OpenBLAS for numpy.** Two OpenBLAS copies. Refused (Decision 3).
- **(g) Undoing OpenBLAS's `void` convention.** scipy's f2py and `cython_lapack` declare the
  subroutines `void`; spec 037 chose the convention to end 111 clashes. Refused.
- **(h) numpy's `python_xerbla` as the link's `xerbla_`.** It would keep `lapack_lite`'s
  `ValueError` for OpenBLAS's argument errors, where native prints and returns; and its two-argument
  `int` signature mismatches OpenBLAS's three-argument `void` callers. Refused.

### 9. The blast radius: what moves

**Behaviour that becomes native** (EXECUTED natively; INFERRED in the guest from the equal `info`
codes until the build; checks 2 and 3 hold it):

- A matrix of `nan`: `svd`, `svdvals`, `pinv`, `matrix_rank`, `norm(…, 2)`, `cond` raise
  `LinAlgError: SVD did not converge`; `lstsq` raises `… in Linear Least Squares`; `eigh` and
  `eigvalsh` raise `Eigenvalues did not converge`; `inv`, `solve`, `det` return `nan`s; `cholesky`
  returns `nan`s below the diagonal and zeros above, as natively. No `ValueError` comes from LAPACK.
- OpenBLAS's argument errors print OpenBLAS's line to stdout and return, as natively.
- numpy and scipy agree on which matrices are singular (300 of 300; 291 with 099 alone).

**Behaviour that stays different from native** (Decision 10).

**Rows** (INFERRED; the builder measures and claims each, *For the lane*):

- **New passes:** the four checks below, seven nodes.
- **Bytes shrink:** `python.wasm` and the snapshot lose `lapack_lite`'s f2c code, 1,915,393 bytes
  in main's link map (`map_sizes.txt`), and gain OpenBLAS's 22 CBLAS wrappers, numpy's
  `cblasfuncs.c` and `HAVE_CBLAS` paths, and the shims. Net about 1.7 to 1.9 MB smaller (INFERRED;
  outside 1.4 to 2.0 MB is a finding for the build review). A smaller row is not red; the README's
  sizes row is updated.
- **The zip grows** by a few hundred bytes: `numpy/__config__.py` gains its BLAS and LAPACK entries
  (made host-neutral by step 70, as scipy's are: `scipy-config-guest.out`).
- **Fuel moves on every row that runs numpy's linear algebra, `dot`, `matmul`, `einsum` or
  `tensordot`.** Large calls drop by 30 to 56 percent (Decision 6). Rows likely to move: the
  `numpy_csv`, `modelling`, scipy and matplotlib goldens (matplotlib's affine transforms use
  `numpy.linalg.inv` and `dot`), the upstream groups `numpy-core`, `numpy-lib`, `numpy-others`
  (`numpy/linalg/tests`) and `pandas-frame`, and spec 091's `string-comparisons` fuel fact, which
  moves with any rebuild's data layout. A row that grows by more than 1 percent is a finding for the
  build review, named with its reason.
- **Golden outputs do not change** (Decision 6's digits). A golden that changes is a finding.
- **Upstream suites: no pass is lost and no class moves** (INFERRED). numpy's linear-algebra tests
  that depend on ILP64 stay `xfail` (`HAS_LAPACK64` false, `test_linalg.py:2316`); its fork and
  subprocess tests stay skipped; no expected class in `tests/upstream/numpy.toml` or `pandas.toml`
  names `lapack_lite` or a BLAS (READ). Any lost pass is a finding, never an allowance.
- **`MANIFEST`:** three new `recipe` lines and one changed (`recipes/wasi-numpy.cross`); the
  snapshot's `x-snapshot-zip` line. `LICENSES/` does not change: `numpy.txt` keeps numpy's
  `license-files` as its `pyproject.toml` lists them (READ, `assemble_artifacts.py:469`), and
  OpenBLAS's and LAPACK's notices ship since spec 037.

### 10. What stays different from native, and says so

- **A matrix singular only in exact arithmetic.** Whether LAPACK meets an exact zero pivot is a
  rounding accident. The guest's OpenBLAS, without fused multiply-add, raises `LinAlgError` on 46
  of the 300 drafting matrices where native numpy on OpenBLAS (arm64) returns a meaningless finite
  inverse; none the other way (Decision 1). Native Accelerate differs from native OpenBLAS on 57 of
  the same 300. Check 2 holds the guest's answer; the README says it.
- **Signals only the hardware gives** stay silent (spec 099, Decision 6). One reaches linear
  algebra: natively, `det` of a `nan` matrix warns `invalid value encountered in det`; the guest
  returns the same `nan` silently.
- **ILP64** (Decision 3): `numpy.linalg.lapack_lite._ilp64` is `False`, natively `True`.
- **Low bits of products** (Decision 6).

### 11. The README, the CHANGELOG and `packages.toml`

- ***What you get*, the `python.wasm` row** (line 23): "numpy, pandas, scipy (with OpenBLAS)"
  becomes "numpy and scipy (sharing one OpenBLAS), pandas".
- ***Measured*, the sizes row** (line 43): the builder's measured sizes, with "numpy on OpenBLAS,
  `lapack_lite` gone (spec 100)".
- ***Measured*, the numpy kernels row** (line 50): "(no SIMD, no BLAS, no threads)" becomes "(no
  SIMD in numpy's own loops, no threads; the spike's measurement, before numpy's `dot`, `matmul`
  and `linalg` moved to OpenBLAS in spec 100)".
- **The platform facts**, spec 099's bullet "**No floating-point status flags in wasm**": its last
  sentence ("numpy's linear algebra runs on its own bundled LAPACK, so a matrix of `nan` can raise
  `ValueError` …") becomes "numpy's linear algebra runs on the set's OpenBLAS, as native numpy's
  does (spec 100)." A new bullet after it:

  > - **A matrix singular only in exact arithmetic** may raise `LinAlgError` in the guest where
  >   native numpy returns a huge, meaningless inverse, or the other way: whether LAPACK meets an
  >   exact zero pivot depends on rounding, and wasm has no fused multiply-add. Of 300 such test
  >   matrices, the guest and native numpy on OpenBLAS disagree on 46 (the guest raising each
  >   time), and native numpy on Accelerate and on OpenBLAS disagree on 57 (spec 100). Use
  >   `numpy.linalg.matrix_rank` or `cond` where it matters.
- ***scipy in the guest*, the `OPENBLAS_*` bullet** (line 263): after "OpenBLAS runs on one thread
  either way", add "; numpy's linear algebra, `dot` and `matmul` share it (spec 100)".
- ***How it is built*, the steps** (line 539): "build OpenBLAS's C LAPACK with its own `make` and
  scipy with meson" becomes "build OpenBLAS's C LAPACK with its own `make`, before numpy, whose
  linear algebra, `dot` and `matmul` call it, and scipy with meson".
- ***How it is built*, the recipe files** (line 623): after the rename headers, add "numpy's side
  of the LAPACK ABI (`numpy_lapack_abi.h`, a one-line header force-included into numpy's
  linear-algebra files by `numpy_file_includes.txt`, and `numpy_lapack_shims.c`),".
- ***Scope*** (line 3317): "threads; BLAS and SIMD;" becomes "threads; SIMD in numpy's own loops;".
- **The patches row** (line 41): unchanged.
- **CHANGELOG**, under `## 0.1.0a8 — unreleased`, first: "**numpy's linear algebra, `dot` and
  `matmul` run on the set's OpenBLAS** (spec 100; question 106). numpy was built with no BLAS and
  ran its bundled `lapack_lite`, an f2c LAPACK 3.2.2. It now finds the OpenBLAS 0.3.34 scipy uses,
  through numpy's own build options; a one-line recipe header (`recipes/numpy_lapack_abi.h`) and a
  file of shims (`recipes/numpy_lapack_shims.c`) bridge numpy's `int` declarations to OpenBLAS's
  `void` subroutines. A matrix of `nan` raises `LinAlgError` in `svd`, `lstsq` and `eigh` as
  natively, where it raised `ValueError: On entry to DLASCL …`; numpy and scipy agree on which
  matrices are singular; a 200×200 inverse, decomposition or product takes 30 to 56 percent less
  fuel; `python.wasm` is about 1.9 MB smaller. A matrix singular only in exact arithmetic is a
  rounding question, and the README says how the guest differs there."
- **`tests/upstream/packages.toml`: no line changes.** numpy's suite already runs (spec 050).

### 12. Where this meets other specifications

- **099** (its base). 099's mechanism turns `info != 0` into `LinAlgError`; this specification
  changes which LAPACK sets `info`. **Two corrections for 099's text**, context only, for the lane
  or 099's builder: its drafting files label the native runs "macosx_14_0_arm64, scipy-openblas",
  and its review's finding 1 says "numpy 2.5.2 on OpenBLAS"; both ran Accelerate (Decision 1). The
  CHANGELOG and README sentences 099 qualified "for `lapack_lite`" are replaced here (Decision 11).
  This specification shares `recipes/wasi-numpy.cross`'s two argument lines with 099 (099 adds its
  `-include`; this removes `-DBLAS_SYMBOL_PREFIX`), a textual neighbour on a stacked branch.
- **037, 038** (scipy). Nothing of scipy's changes: its archives compile against numpy's installed
  headers, which do not change (INFERRED; the builder confirms by hash). 038 shares
  `60_link.sh`'s `libs` line only if it touches it.
- **044, 045** (scikit-learn, statsmodels). Both call `numpy.linalg` and `dot` heavily. Whichever
  lands second re-measures its goldens' fuel and names each moved row. 044's weak-duplicate gate
  meets nothing here: every new definition is strong.
- **066** (the compiled packages' own tests). matplotlib's tests call `numpy.linalg`; fuel moves,
  outcomes do not (INFERRED).
- **095** (scipy's and scikit-learn's own tests). Nothing changes in its plan.

## Intent

numpy in the guest runs the LAPACK and BLAS native numpy runs, the one OpenBLAS scipy already
uses. A matrix of `nan` fails as it fails natively, numpy and scipy agree with each other, and
linear algebra costs less. Where rounding decides, as for a matrix singular only in exact
arithmetic, the difference from native is measured, held by a check and stated.

## Design

| file | change |
|---|---|
| `recipes/numpy_lapack_abi.h` | new (Decision 4): `#define BLAS_SYMBOL_PREFIX wasi_numpy_` and a comment: what it is for, spec 100, when it goes (a numpy release that declares LAPACK's subroutines `void`) |
| `recipes/numpy_lapack_shims.c` | new (Decision 4): 54 shims with numpy's typed prototypes and OpenBLAS's declarations; a header comment in the form of `scipy_lapack_shims.c`'s |
| `recipes/numpy_file_includes.txt` | new: four entries (`linalg/umath_linalg.cpp`, `linalg/lapack_litemodule.c`, `lapack_lite/python_xerbla.c 2`, `common/python_xerbla.c`), each `@ROOT@/recipes/numpy_lapack_abi.h`; a header comment in the form of `scipy_file_includes.txt`'s |
| `recipes/wasi-numpy.cross` | `pkg-config` and `cmake` as Decision 2; `-DBLAS_SYMBOL_PREFIX=numpy_lapack_lite_` and its comment out of both argument lines |
| `scripts/steps/40_numpy.sh` | Decision 2's checks, environment and meson options; the per-file map rendered into `build/numpy-build/file-includes.txt` before `meson setup`, its log checked after `ninja` as step 57 checks its own; the shims archive; the two post-install checks; the header comment says numpy links step 38's OpenBLAS |
| `scripts/steps/60_link.sh` | checks `build/numpy-shims/libnumpy_lapack_shims.a` and adds it to `libs` beside scipy's; its comment names spec 100 |
| `tests/jobs/oracle/pyproject.toml`, `uv.lock` | Decision 7 |
| `tests/harness/scan.py` | `one_lapack_errors(...)`: check 4's link-map rule |
| `tests/checks/test_v1_3_data_stack.py` | checks 1, 2 and 3 |
| `tests/checks/test_v1_5_rebuild_from_pins.py` | check 4 |
| `tests/unit/test_scan.py` | check 5's rows |
| `README.md`, `CHANGELOG.md` | Decision 11 |

No new pin; `downloads/SHA256SUMS` does not change. `recipes/patches/` does not change. The
drafting files under `../research/` are evidence; the builder writes the recipe files fresh.

## The checks, first

Each is written before the change it judges and seen failing first. Checks 1 to 3 run their
program by `-c` with nothing writable, on both binaries, in the fast tier; each asserts exit 0, no
trap, empty stderr, and stdout as below, and records fuel (about 3.3 G on the plain binary today:
they import numpy and scipy, `fuel-ops.txt`'s baseline).

1. **v1.3, `test_numpy_is_built_on_the_sets_openblas[which]`.** The program prints, for `blas`
   and `lapack` from `numpy.show_config(mode="dicts")["Build Dependencies"]`, the name, `found`,
   the version, the detection method and the OpenBLAS configuration; then whether numpy's two
   entries equal scipy's on those keys and the include and lib directories; then
   `numpy.linalg.lapack_lite._ilp64`. Expected (scipy's entries in today's guest,
   `scipy-config-guest.out`):

   ```
   blas openblas True 0.3.34 pkgconfig USE_64BITINT= DYNAMIC_ARCH=0 DYNAMIC_OLDER= NO_CBLAS= NO_LAPACK= NO_LAPACKE=1 NO_AFFINITY=1 USE_OPENMP=0 WASM128_GENERIC MAX_THREADS=1
   lapack openblas True 0.3.34 pkgconfig USE_64BITINT= DYNAMIC_ARCH=0 DYNAMIC_OLDER= NO_CBLAS= NO_LAPACK= NO_LAPACKE=1 NO_AFFINITY=1 USE_OPENMP=0 WASM128_GENERIC MAX_THREADS=1
   same as scipy True
   ilp64 False
   ```

   Seen failing first: on main's set numpy says `blas none None None None` and `lapack none None
   None None` (EXECUTED, `config-guest-plain.out`).
2. **v1.3, `test_a_rank_deficient_matrix_meets_the_sets_openblas[which]`.** The 300 matrices of
   099's review (seed 99, `singular300.py`): for each, numpy's `inv` (E raises `LinAlgError`, F
   finite, N all-`nan`, M mixed) and scipy's `lapack.dgesv(a, I)` (E `info > 0`, F `info == 0`).
   It prints `numpy <300 letters>`, `scipy <300 letters>` and `agree <count>`. Expected: both
   strings equal the guest's OpenBLAS answer (EXECUTED, `singular300-guest-plain.out`, its `gesv`
   row, the same on the snapshot), and `agree 300`:

   ```
   FEEFEFFFFEEFFEEEFEFEEFFFEEEFFEEFEFEEFFFFFFFEFFFFEFFEFEEEFEEFEFFEEEEFEFFFEFFEFEFEEEFFEFEFFEFFEEEFEFFEFEFEEEFFFFFFFFEFFFEFEEEFFEFFEEFEFEEFFFFEFFFEFFFFEEFEFEEFEFFFFFEFFFEFFEEEEFFEFFFEEEFFEEEFFEFFEFEEFEEFEEEEFEEEEEEEEFFEEFEEFEFFEFEEEEEFEEEEEEFEFEFEFFEEFEFEEEEEEFEFEEFEFFFFEEEEFEEEFFFFEEFEFEEEFEFFEEEEFEFF
   ```

   Its docstring records native numpy on OpenBLAS (arm64): the same letters but at the 46 indices
   `divergence.txt` lists (2, 10, 17, … 275), where native says F, and names the README bullet
   (Decision 10). Seen failing first: on main numpy prints `lapack_lite`'s letters with 158 N
   (`inv` row) and `agree 147`; on 099's tip, 158 E and `agree 291` (INFERRED from the same rows).
3. **v1.3, `test_numpy_linalg_errors_are_native_numpy_on_openblas[which]`.** Warnings ignored, a
   3×3 matrix of `nan` through fifteen calls, then `lapack_lite.xerbla()` and
   `lapack_lite.dorgqr(1, 1, 1, a, 0, a, a, 0, 0)`. Lines that begin ` ** On entry to` are
   OpenBLAS's `xerbla` on C's stdout, whose order against Python's buffered stdout is not
   Python's; the check takes them apart and compares them as a sorted list. Expected, native's
   (EXECUTED, `nan-native-openblas.out`, `xerbla-native-openblas.out`):

   ```
   svd                    raises LinAlgError: SVD did not converge
   svd no uv              raises LinAlgError: SVD did not converge
   pinv                   raises LinAlgError: SVD did not converge
   matrix_rank            raises LinAlgError: SVD did not converge
   norm 2                 raises LinAlgError: SVD did not converge
   cond                   raises LinAlgError: SVD did not converge
   lstsq                  raises LinAlgError: SVD did not converge in Linear Least Squares
   eigh                   raises LinAlgError: Eigenvalues did not converge
   eigvalsh               raises LinAlgError: Eigenvalues did not converge
   eig                    raises LinAlgError: Array must not contain infs or NaNs
   inv                    returns all-nan
   solve                  returns all-nan
   cholesky               returns mixed
   qr                     returns all-nan,mixed
   det                    returns all-nan
   xerbla                 raises ValueError: On entry to test parameter number -1 had an illegal value
   dorgqr lda 0           returns {'dorgqr_': 0, 'info': -5}
   ```

   and the OpenBLAS lines, sorted: ` ** On entry to DLASCL parameter number  4 had an illegal value`
   twice (from `lstsq`) and ` ** On entry to DORGQR parameter number  5 had an illegal value` once.
   Seen failing first: on main `svd` returns all-`nan`, five calls raise `ValueError: On entry to
   DLASCL …`, `eigh` returns, `cholesky` returns all-`nan` and `dorgqr` raises `ValueError`
   (EXECUTED, `nan-guest-plain.out`, `xerbla-guest-plain.out`).
4. **v1.5, `test_one_lapack_is_linked`** (`test_v1_5_rebuild_from_pins.py`, fast), in the form of
   `test_one_qhull_is_linked`. Two parts:
   - Without a build: `recipes/wasi-numpy.cross` names no `BLAS_SYMBOL_PREFIX` and names step 10's
     pkgconf; `recipes/numpy_file_includes.txt` has exactly the four entries and counts; step 40's
     meson line carries `-Dblas=openblas -Dlapack=openblas -Dallow-noblas=false`.
   - With the build (`needs.need("compile records")`): `build/numpy-build/file-includes.log`
     shows each entry exactly its count (fails, not skips, when the log is missing while the need
     is met); `build/numpy-build` holds no `lapack_lite_f2c*.o`; no entry of its
     `compile_commands.json` compiles a `lapack_lite/f2c*.c` file or carries `-DBLAS_SYMBOL_PREFIX`;
     `_umath_linalg`'s, `lapack_lite`'s and `_multiarray_umath`'s `.deps` name OpenBLAS only as
     `build/openblas-wasi/lib/libopenblas.a`, or as `-lopenblas` with `-L` that folder (scipy's
     name the archive by path; numpy's vendored meson may write either); and `one_lapack_errors` over `build/link/python.map`
     finds nothing: every function `libopenblas.a` defines that the link takes comes from that
     archive, once, `dgesv_`, `dgesdd_`, `cblas_dgemm` and `xerbla_` among them; no object named
     `lapack_lite_f2c*` and no symbol beginning `numpy_lapack_lite_`; every `wasi_numpy_*` symbol
     but `wasi_numpy_xerbla_` once, from `libnumpy_lapack_shims.a`, `wasi_numpy_dgesv_` among them;
     `wasi_numpy_xerbla_` once, from a numpy archive's `python_xerbla` object.

   Seen failing first: on main both parts fail (the prefix is there; no log; 1,915,393 bytes of
   `lapack_lite_f2c` objects in the map).
5. **Unit rows, `tests/unit/test_scan.py`** (no artifact). Each fails on main, where
   `one_lapack_errors` does not exist: a map where every routine comes from `libopenblas.a` once
   gives no finding; a routine linked twice is named; a routine from another archive is named; a
   `lapack_lite_f2c` object is named; a `numpy_lapack_lite_` symbol is named; a `wasi_numpy_`
   shim from another archive is named; a map with no `libopenblas.a` function is a finding.

## Scope

In: Decisions 1 to 11. Out:

- **Matching native on matrices singular only in exact arithmetic** (Decision 10): wasm has no
  deterministic fused multiply-add, and native numpy differs across BLAS libraries itself.
- **Signals only the hardware gives** (spec 099).
- **ILP64** (Decision 3).
- **A facts sheet or pull request for numpy's `int` declarations.** No patch is carried, so §4.1
  asks for none; numpy's AI policy keeps any text in the owner's words.
- **Native x86_64 numbers for the 300 matrices.** The drafting ran on arm64 only; the checks
  compare the guest with itself and with recorded native outputs, and the guest's bytes are the
  same on every host.

## Acceptance criteria

1. **The checks exist and were seen failing first,** each failure recorded in the landing notes.
2. **The build.** From an empty `build/` in a clean clone, on 099's reviewed tip,
   `scripts/build.sh` finds OpenBLAS (meson's log: `Run-time dependency openblas found: YES
   0.3.34` for BLAS and LAPACK), compiles no `lapack_lite` f2c file, matches each per-file entry
   its count, links with no `duplicate symbol` and no `signature mismatch`, and makes a set whose
   binaries pass every check. `MANIFEST` names the three recipe files by hash. `LICENSES/` is
   unchanged.
3. **The same bytes everywhere** (spec 012): the arm64 Linux rebuild gives macOS's `SHA256SUMS`,
   and the release's x86_64 rebuild too. `numpy/__config__.py` in the zip names no build host.
4. **One OpenBLAS.** Check 4 green; the guest's imports equal main's (`tests/public_api.txt` and
   the import checks unchanged); step 60's constructor check sees no new constructor.
5. **pandas and scipy unchanged.** Step 50's and step 57's archives are byte-identical to the
   base's (the builder shows the hashes).
6. **The numbers recorded** in the landing notes: both binaries' and the zip's bytes; checks 1 to
   3's fuel; every fuel row that moves, with its percentage; the 300-matrix probe and the `nan`
   probe on the new set, both binaries; the oracle's goldens on the new pin.
7. **The judge.** The fast tier in the worktree, green but for the growth named here; the lane's
   run on three cores. The lane accepts with `--accept-judge` and `--accept-growth`.
8. **The release.** A release dry run on the branch passes every job on all three systems but
   growth lines (AGENTS.md rule 2's "built").

## The judge's changes

- `tests/harness/scan.py`: `one_lapack_errors`.
- `tests/checks/test_v1_3_data_stack.py`: checks 1 to 3. `tests/checks/test_v1_5_rebuild_from_pins.py`:
  check 4. `tests/unit/test_scan.py`: check 5.
- `tests/jobs/oracle/pyproject.toml` and `uv.lock`: numpy's OpenBLAS wheel on macOS arm64
  (Decision 7).
- No golden output, gap, allowance or progress file is edited, and no check is weakened.

## The owner's choices

None blocks the build. Decided until answered:

1. **Question 107: does spec 100 still land before 0.1.0, given Decision 1?** The answer to 106
   rested on "on OpenBLAS the two LAPACKs would agree". Measured: the review's native was
   Accelerate; against native numpy on OpenBLAS, the guest moves from 249 to 254 of 300 exactly
   singular matrices, and the other 46 cannot follow without a fused multiply-add wasm lacks. What
   this specification does deliver: `nan` matrices fail as natively, no `ValueError` from LAPACK,
   numpy and scipy agree, LAPACK 3.12's algorithms in place of 3.2.2's, 30 to 56 percent less fuel
   on linear algebra, about 1.9 MB less binary. The cost: a stacked build-class landing before
   0.1.0, and every numpy fuel row moves. Options: (a) build it before 0.1.0, as specified; (b)
   after 0.1.0, 099 alone in 0.1.0; (c) not at all. **Decided until answered: (a)**, the owner's
   answer, whose other gains hold.

## For the lane

- **Kind:** build-class, stacked on 099; not a package. In a wave it is one of the "at most two
  other build-class changes", entering after 099 in the same stacked chain, or in the wave after.
  It shares `recipes/wasi-numpy.cross` with 099, `scripts/steps/60_link.sh` with any entry that
  touches its `libs` line (044, 045), `README.md` and `CHANGELOG.md` with every entry, and
  `tests/checks/test_v1_3_data_stack.py` with 099.
- **Pre-build review: required** (§5.6, the build recipe and the artifact set).
- **The rebuild:** steps 40 (numpy), 60, 70 (`numpy/__config__.py`), 80 and 90 change their
  outputs. Steps 50 and 57 compile against numpy's installed headers, which do not change
  (criterion 5). Steps 10 to 38 do not run differently.
- **The claim list** (the builder's measured numbers replace each INFERRED one; each line starts
  "100:"):
  - 100: **new checks (7 nodes), each passing:** checks 1 to 3 on `[plain]` and `[snapshot]`, and
    check 4. **Unit rows:** check 5's seven.
  - 100: **retired checks:** none. **Lost passes:** none.
  - 100: **rows that shrink, bytes:** `test_binary_is_a_core_wasm_module[plain]` and
    `[snapshot]`. **Rows that grow, bytes:** `test_stdlib_zip_is_bytecode_only_and_deflated`
    (`numpy/__config__.py`).
  - 100: **fuel rows that move:** each named, with its percentage and the reason (numpy's linear
    algebra and products on OpenBLAS; Decision 6).
  - **The judge hash changes** in `tests/harness/scan.py`, `tests/checks/test_v1_3_data_stack.py`,
    `tests/checks/test_v1_5_rebuild_from_pins.py`, `tests/unit/test_scan.py` and the oracle's
    `pyproject.toml` and `uv.lock`.
- **The flags** (the builder fills the measured numbers):

  ```
  --accept "100: numpy's linear algebra, dot and matmul run on the set's OpenBLAS 0.3.34 (step 40 finds it through the pinned pkgconf; recipes numpy_lapack_abi.h, numpy_lapack_shims.c and numpy_file_includes.txt bridge numpy's int declarations to OpenBLAS's void subroutines); lapack_lite is gone from the link; nan matrices fail as native numpy on OpenBLAS; a matrix singular only in exact arithmetic is a rounding question, as documented"
  --accept-judge "100: checks that numpy is built on the set's OpenBLAS as scipy is, that numpy and scipy agree on 300 rank-deficient matrices with the guest's recorded answer, that nan matrices and LAPACK's argument errors behave as native numpy on OpenBLAS, and that one OpenBLAS and no lapack_lite is linked; one_lapack_errors and its unit rows; the oracle's numpy on macOS arm64 is the OpenBLAS wheel; no existing expectation edited"
  --accept-growth "100: numpy on OpenBLAS: python.wasm -N bytes, the snapshot -N, the zip +N (numpy/__config__.py's BLAS and LAPACK entries); fuel rows that run numpy's linear algebra or products move: <rows and percentages>; MANIFEST three recipe lines added, one changed"
  ```

- **Dry-run needs:** the release workflow on the branch (criterion 8); the Windows judge shards
  run checks 1 to 3 as any guest check; check 4 needs a build's records.
- **For 099, context only** (Decision 12): the native runs in 099's drafting files and its review's
  finding 1 were numpy on Accelerate, not OpenBLAS.

## One line

Build numpy against the OpenBLAS scipy already uses, through numpy's own options, one prefix
header and a file of shims, so `nan` matrices fail as natively and linear algebra is cheaper;
where rounding alone decides, measure the difference and say so.

## Landing notes

Not built.
