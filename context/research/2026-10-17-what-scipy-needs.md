# What scipy needs on wasm32-wasip1

- **Status:** executed, 2026-10-17. Research only; nothing in the repository was built or changed.
  Box: one working session, about 2.5 hours; finished inside it.
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5), asked by the owner's session to study scipy, the
  last item on the constitution's post-v1 list (§2: "matplotlib, then ... sqlite, bz2, lzma, then
  scipy").
- **Feeds:** a future specification that adds scipy; `../constitution.md` §4.1 (zero patches),
  §4.12 (the owner approves each linked licence); `questions-for-the-owner.md`.
- **Stands on:** `2026-10-16-cpp-exceptions-and-wasi-hosts.md` (standard EH and setjmp on SDK 33),
  `2026-10-16-build-time-profiles-of-the-core-c-libraries.md` (numpy and pandas are about 40% of
  `python.wasm`), `2026-10-17-sqlite-bz2-and-lzma.md` (the pattern for a new library step).
- **Evidence:** `2026-10-17-what-scipy-needs/` beside this memo: `scripts/` (the build and probe
  scripts written for this memo), `probes/` (small C and C++ programs), `outputs/` (every number
  quoted below), copied from the session scratchpad without the built `.wasm` and archive files
  and the few outputs over 200 KB, which artifacts-never-in-git keeps out. Downloads sit in `dl/`, each in its own
  directory, each checked against a published SHA-256.
- **Repository state:** `main` at `0ea00df`. The probes used the repository's own build tree
  read-only: `build/tools/wasi-sdk-33.0-arm64-macos` (clang 22.1.0-wasi-sdk, LLVM `4434dabb`),
  `build/tools/wasmtime-v49.0.3-aarch64-macos`, the host Python 3.15.0 and Cython 3.3.0 in
  `build/tools/`, and the CPython and numpy headers in `build/`.
- **Machine (benchmark facts only):** Apple arm64, macOS 26.5.2.
- **Prior art read:** `context/prior_art/pyodide-recipes` @ `01bd0af` (scipy, libopenblas, libf2c,
  libboost recipes) and `context/prior_art/pyodide` @ `6754c1f`. Both MPL-2.0, already recorded.
  No new clone was made. Pyodide's published wheels were downloaded only to measure them.

## The question

Can scipy be compiled into this project's statically linked `python.wasm`, from pinned released
sources, with zero patches to any source tree? What does it need, what breaks on WASI, what
would it cost, and what is the first experiment?

Terms used below:

- **BLAS / LAPACK**: the standard linear-algebra libraries scipy calls. BLAS is the basic
  operations (matrix multiply). LAPACK is the solvers built on it (LU, QR, SVD, eigenvalues).
  The reference versions are written in Fortran.
- **f2c**: an old tool that translates Fortran 77 to C.
- **f2py**: numpy's generator of C wrappers that let Python call Fortran-ABI functions.
- **Signature clash**: a function called with one wasm type (parameters and result) but defined
  with another. Natively this is usually harmless. In wasm it is a trap. That is the central
  finding of this memo.

## Method

- **Sources (EXECUTED).** scipy 1.18.1 sdist (PyPI, SHA-256 `52c4b742…2747307`, `OK`) and
  OpenBLAS 0.3.34 (GitHub release, SHA-256 `cd7e1298…f197dfed`, `OK`, equal to GitHub's asset
  digest). Each was unpacked into a scratch directory and read.
- **Toolchain probes (EXECUTED).** Small programs compiled with the pinned wasi-sdk 33 and run
  under the pinned wasmtime 49.0.3 (`probes/`).
- **OpenBLAS build (EXECUTED).** `scripts/build_openblas.sh` builds OpenBLAS for
  `wasm32-wasip1` in a fresh copy of the tarball. The pristine unpacked tree was then diffed
  against a fresh unpack: no difference (`outputs/source-trees-diff.txt`).
- **ABI probe (EXECUTED).** scipy's own BLAS/LAPACK wrappers were generated on the host
  (`_fblasmodule.c`, `_flapackmodule.c` with numpy 2.5.2's f2py; `cython_blas`/`cython_lapack`
  with scipy's `_generate_pyx.py` and the line's Cython 3.3.0), compiled for wasm32, and linked
  against the OpenBLAS archive with `wasm-ld` (`scripts/abi_probe.sh`,
  `scripts/gen_direct_calls.py`). The link is only a detector; nothing of scipy was run.
- **A flang check (EXECUTED).** The official LLVM 23.1.3 macOS arm64 release
  (SHA-256 `a3f181b1…dca32eb3`, `OK`) was listed for flang, then deleted.
- **Web (READ).** The LLVM flang-for-wasm issue and pull request, read on 2026-10-17. Listed
  under Sources.
- **Sizes (EXECUTED).** Pyodide 314.0.7's scipy, OpenBLAS, numpy and pandas wheels, checked
  against the hashes in its `pyodide-lock.json` (all `True`), then measured.

## Findings

### 1. The version: scipy 1.18.1 fits the line

- **EXECUTED.** On 2026-10-17, PyPI's latest scipy is 1.18.1 (2026-08-21). It is the first
  release with cp315 wheels (20 of them). 1.18.0 and earlier have none.
- **READ** (`pyproject.toml`). `requires-python >=3.12`; numpy `>=2.0.0,<2.8` at build and run
  time, so the line's numpy 2.5.2 fits. Build requirements: meson-python `<0.22`, Cython
  `>=3.2.0,<3.3.0`, pybind11 `>=2.13.2,<3.1.0`, pythran `>=0.19.0,<0.20.0` on Python 3.15.
- **A friction to note (READ, INFERRED).** The line pins Cython 3.3.0. scipy's `pyproject.toml`
  says `<3.3.0`, but its `meson.build` checks only `>=3.2.0` (line 63). This project runs meson
  directly, not through pip, so the upper bound is not enforced. It may still be a real
  incompatibility. The probe cythonized `cython_blas.pyx` and `cython_lapack.pyx` with 3.3.0
  without error (EXECUTED). That is two of scipy's many Cython modules, not proof for all.
- **Pyodide** builds scipy 1.18.0 against OpenBLAS 0.3.31 (READ: `packages/scipy/meta.yaml`,
  `packages/libopenblas/meta.yaml`).

### 2. scipy itself no longer needs a Fortran compiler

This is the most important change since Pyodide's recipe was designed.

- **READ** (`meson.options`, `meson.build:89-109`). scipy 1.18.1 has an option
  `_without-fortran`: "build without a Fortran compiler (the deprecated `scipy.odr` will be
  missing)". With it set, meson never adds the Fortran language.
- **EXECUTED** (`find`). The whole sdist has 7 Fortran files. Five are ODRPACK
  (`scipy/odr/odrpack/*.f`). One is a doc example. One is HiGHS's optional Fortran API
  (`subprojects/highs/highs/interfaces/highs_fortran_api.f90`), which scipy does not build.
  ARPACK, PROPACK, QUADPACK, MINPACK, FITPACK, L-BFGS-B and SLSQP are now C in this release
  (the paths Pyodide's recipe edits, like `arpack/arnaud/src` and `_propack/PROPACK/src`, are C).
- **EXECUTED.** f2py's output for `_fblas` and `_flapack` has empty Fortran wrapper files
  (`_fblas-f2pywrappers.f`, `_flapack-f2pywrappers.f`: 0 bytes). So the f2py modules are pure C
  that call BLAS and LAPACK through the Fortran calling convention.
- **What is lost:** `scipy.odr` only, which scipy has deprecated (READ: the option's text).
- **So the only Fortran left is BLAS/LAPACK itself.** The question becomes: is there a
  BLAS/LAPACK that compiles with a C compiler and has a consistent ABI on wasm?

### 3. No Fortran compiler can target wasm32-wasip1 today

- **EXECUTED.** The pinned SDK's clang does not compile Fortran:
  `clang --target=wasm32-wasip1 -c daxpy1.f` gives
  `error: invalid value 'f95-cpp-input' in '-x f95-cpp-input'`. The SDK ships no flang.
- **EXECUTED.** The official LLVM 23.1.3 macOS arm64 release tarball (10,782 paths) contains
  no file whose path mentions flang. So no released, unpatched flang binary was available to
  try on this host.
- **READ (web, 2026-10-17).** Upstream flang support for wasm is in progress, not done.
  - Meta-issue llvm/llvm-project#226471, opened 2026-09-25: the goal is
    `flang --target=wasm32-unknown-emscripten`. "Building and testing a WebAssembly flang-rt"
    (the Fortran runtime library) is listed as pending. WASI is not mentioned.
  - Pull request #226427 (FIR CodeGen support for wasm32/wasm64) was open, not merged, at its
    last activity on 2026-10-07. Its author says it "does not include runtime ... changes".
  - The working Fortran-to-wasm compilers in use (r-wasm/flang-wasm, for webR) are patched
    LLVM builds aimed at Emscripten.
- **INFERRED.** A flang route needs (a) a flang that targets wasm32, (b) a flang runtime built
  for wasm32-wasip1, and (c) an ABI that matches what scipy's C expects. Today (a) means a
  patched LLVM, and (b) does not exist. Constitution §4.1 rules out a patched compiler. The
  flang route is closed until upstream LLVM ships both. It is worth re-checking each LLVM release.
- **Not tried:** LFortran, which documents a WASI target. It is a different compiler with
  partial Fortran 77 coverage of LAPACK's size; not studied here.

### 4. What Pyodide does, and why none of it fits our rules

**READ** (`pyodide-recipes` @ `01bd0af`).

- **scipy**: 5 patch files (`packages/scipy/patches/0001`–`0005`) plus about 30 `sed` edits of
  scipy's tree in the build script. Most change `void` to `int` on functions that call BLAS or
  LAPACK. One empties `SuperLU/SRC/input_error.c`. A patched f2c is cloned at build time without
  a pin (`git clone https://github.com/hoodmane/f2c.git --depth 1`).
- **OpenBLAS**: 3 patches plus `sed` edits that change `void` to `int` across
  `common_interface.h`, `cblas.h`, `interface/*.c` and `lapack-netlib/SRC/*.c`. Built with
  `NOFORTRAN=1`, so its LAPACK is OpenBLAS's C translation, not Fortran.
- **libf2c**: CLAPACK 3.2.1's runtime with 7 patches, folded into `libopenblas.so`.
- **Why `int` everywhere (READ: `packages/scipy/info.md`, patch 0002's message):** f2c makes
  every Fortran subroutine return `int`. scipy's C declares them `void`. Emscripten traps on the
  difference, so Pyodide moves every side to `int`.
- **Fit with our rules:** every one of those edits is a source change. Constitution §4.1 forbids
  them; §4.2 forbids the unpinned clone. Pyodide is still the best map of where the problems are.
  Its `int` convention is not needed by us if scipy is built without Fortran (finding 2): then
  nothing f2c-generated is left in scipy.

### 5. OpenBLAS 0.3.34 builds for wasm32-wasip1 with no patch

**EXECUTED** (`scripts/build_openblas.sh`, `outputs/openblas-wasm128.log`).

- OpenBLAS now has its own wasm architecture (READ: `Changelog.txt`: 0.3.32 "moved the
  preliminary support for a Web Assembly target to its own WASM architecture and
  WASM128_GENERIC target", with SIMD GEMM, DOT, ROT and SUM kernels; 0.3.34 added SIMD TRSM).
- The build: `make libs netlib` with the SDK's clang, `TARGET=WASM128_GENERIC`, `NOFORTRAN=1`
  (`C_LAPACK=1`), `USE_THREAD=0`, `USE_LOCKING=0`, `NO_SHARED=1`, `NO_LAPACKE=1`. It took
  50 s on this machine (benchmark fact).
- It needed five things from outside the tree. Each is a command-line flag or a recipe file:
  1. `ARCH=wasm` on the make line. OpenBLAS's probe (`ctest.c`) only knows wasm through
     `__EMSCRIPTEN__`, so for WASI it found no architecture and stopped
     (`Makefile.: No such file or directory`).
  2. `-DARCH_WASM` in `CFLAGS`, for the same reason: the generated `config.h` had empty
     `OS_`/`ARCH_` lines, and `common.h` then missed `common_wasm.h` (`BUFFER_SIZE` undeclared).
  3. `-D_WASI_EMULATED_MMAN` (wasi-libc's malloc-backed `mmap`) and `-DNO_SYSV_IPC`. The final
     link then needs `-lwasi-emulated-mman`.
  4. `-include sched.h`. `common.h` includes `<sched.h>` only for named OSes, and calls
     `sched_yield`.
  5. An empty stand-in `sys/ipc.h` on the include path. `driver/others/memory.c` includes it on
     every non-Windows OS; wasi-libc has none. With `NO_SYSV_IPC`, nothing from it is used.
- **The result.** `libopenblas_wasm128-r0.3.34.a`, 11,095,502 bytes, SHA-256
  `9e5fb7eb…df8610287`, 3,782 objects, 3,811 defined functions. Every routine checked is present:
  `dgemm_ dgesv_ dgees_ dgesdd_ dsyevr_ zgees_ zladiv_ zdotc_ cdotu_ chla_transtype_ xerbla_
  xerbla_array_ lsame_ dgejsv_ dgesvdq_ dgges3_ dsysv_rook_ cblas_dgemm ilaenv_ dlamch_ dlartgp_
  dgelsy_` (`outputs/openblas-symbols-check.txt`).
- Its undefined symbols are libc, libm, compiler-rt and `mmap`/`munmap`. There is no thread
  call (`outputs/openblas-undefined.txt`).
- **Not done:** OpenBLAS adds `-fPIC` itself. This project's `scripts/wasi-cc` drops it for
  numpy. The spec would pass `CC` through that wrapper. The `-m32` OpenBLAS adds was accepted.
- **SIMD.** `WASM128_GENERIC` compiles with `-msimd128` (`Makefile.wasm`). The wasm SIMD
  proposal is standard and on by default in wasmtime. A host without SIMD could not load the
  module. A generic non-SIMD target was not tried.
- **Other C LAPACKs (INFERRED):** CLAPACK 3.2.1 is LAPACK 3.2.1 (2009). scipy's `cython_lapack`
  declares `dgeqrt` and `dtpqrt` (READ: `cython_lapack_signatures.txt`), which arrived in
  LAPACK 3.4. So CLAPACK is too old. Translating Reference-LAPACK ourselves with f2c would
  rebuild what OpenBLAS already ships, and would bring f2c's `int` convention, which clashes
  with scipy (finding 6). OpenBLAS's C LAPACK is the only current, released, C-only LAPACK
  found.

### 6. The blocker: signature clashes, and the worst ones are invisible at link time

On native targets a caller that declares a function `void` and a definition that returns `int`
agree in practice. In wasm the function's type includes its result, so they do not. There are
two cases (both EXECUTED):

- **A direct call with the wrong type.** `wasm-ld` warns `function signature mismatch` and
  replaces the call with a stub that traps. Step 60's `clashes()` already fails the build on
  this warning.
- **A call through a function pointer.** `wasm-ld` says nothing. The call traps at run time.
  `probes/def.c` + `probes/use.c` (an `int` function called through a `void` pointer, as f2py's
  table does) linked with 0 warnings and ran to `wasm trap: indirect call type mismatch`
  (`outputs/probe-indirect-run.txt`).

What the probes found (`outputs/abi-*.txt`):

| where the clash is | count | how it shows | example |
|---|---|---|---|
| inside OpenBLAS 0.3.34 alone (archive linked whole) | **111** functions | link warning; trap when reached | `dlaqp3rk.c` declares `extern int dgemm_(...)`; `interface/gemm.c` defines `void dgemm_` |
| scipy's `cython_blas`/`cython_lapack` against OpenBLAS (beyond the 111) | **47** | link warning | scipy `void dgesv_` vs OpenBLAS `int dgesv_`; `xerbla_array_` (OpenBLAS has a 4th, hidden length argument); `chla_transtype_` (scipy: returns `char`; OpenBLAS: result through a pointer) |
| scipy's f2py `_flapack` against OpenBLAS (of 621 routines in `_fblas` and `_flapack`) | **37** | **no warning; trap at run time** | `gesv getrf getrs laswp lauum potrf trtri trtrs` × 4 precisions (OpenBLAS returns `int`, f2py calls `void`); `ilaver`; `?gees` (f2py passes two hidden string lengths, 17 arguments against 15) |

- **The cause inside OpenBLAS (READ, EXECUTED counts).** 515 of the 2,067 C files in
  `lapack-netlib/SRC` declare the routines they call as `int`-returning (f2c style, for example
  `extern /* Subroutine */ int dgemm_(...)`). OpenBLAS defines its BLAS as `void`
  (`interface/gemm.c:257`) and 26 of its own LAPACK routines as `int`
  (`interface/lapack/*.c`, for example `gesv.c:63`). Natively the mix never matters.
- **It traps in real calls (EXECUTED, `probes/lapack_run.c`).** Each caller declaration matched
  OpenBLAS's own definition, so only OpenBLAS's internal clashes remained (5 link warnings). On
  a 64×64 matrix, `dgesv_`, `dgeqrf_` and `dsyev_` ran and match native LAPACK (host numpy
  2.5.2) to 12 digits: `x0=-0.036999190064`, `r00=-2.151611140845`, `wmax=3.116080858571`.
  `dgesdd_` (SVD) trapped in `signature_mismatch:dlarft_`
  (`outputs/probe-lapack-run.txt`, `outputs/native-lapack.txt`).
- **Complex results are not a problem here (EXECUTED).** `zdotc_`, `cdotu_` and `zladiv_` did
  not clash. On wasm32, a C function returning a complex value takes a hidden result pointer as
  its first argument, the same shape as f2c's `void f(complex *ret, ...)` (INFERRED from the
  absence of a warning, not from reading the ABI document).
- **What this means.** OpenBLAS's C LAPACK cannot be used on wasm as released. The fix is
  either upstream or a recipe layer:
  - **Upstream, OpenBLAS (preferred):** one convention for every subroutine in `C_LAPACK`
    builds. Making the 515 files' `extern int` declarations and the 26 `int NAME(...)`
    interface routines `void` would remove all 111 internal clashes and the 33 `int`/`void`
    clashes with scipy (INFERRED). The files are generated, so this is a mechanical change.
    OpenBLAS is adding wasm support release by release, and Pyodide carries the same problem as
    a `sed`, so the change has a second user.
  - **Upstream, scipy (small):** `?gees`'s two literal hidden lengths
    (`flapack_gen.pyf.src:1199`, `:1229`, the lines Pyodide's patch 0003 removes),
    `chla_transtype` and `xerbla_array` in `cython_lapack_signatures.txt` (Pyodide's patch 0004
    removes `chla_transtype`).
  - **Recipe-only (possible, heavier):** a compiler wrapper that renames a clashing symbol in
    the files that call it, plus a generated C shim with the caller's signature that forwards
    to the definition (the `npy_rename.h` pattern, per file). Both sides of most clashes are in
    OpenBLAS, compiled by one `make` with global flags. So the rename must be chosen per source
    file, which only a wrapper around `CC` can do. That is about 150 shims generated by a
    script from the pristine sources. It would work under §4.1, but it is not "the smallest
    thing" (§6.4), and it must be regenerated and re-checked at every OpenBLAS release.
- **The judge needs a new check (INFERRED).** The existing clash detector cannot see the 37
  f2py clashes. A test that imports `scipy.linalg` is not enough either. The test has to call
  each wrapped routine, or the build has to run the direct-call probe
  (`scripts/gen_direct_calls.py`: one direct call per f2py prototype, so `wasm-ld` checks it).

### 7. Other static-link work scipy brings

All recipe-level; none needs a source change (READ or EXECUTED as marked).

- **BLAS discovery (READ).** scipy calls `dependency('openblas')`. The line's meson 1.12.1 has
  no BLAS finder (no `mesonbuild/dependencies/blas_lapack.py`), and the cross files set
  `pkg-config = 'false'`. numpy's vendored meson has one, `OpenBLASSystemDependency`, which takes
  `openblas_includedir` and `openblas_librarydir` from the cross file's `[properties]`
  (`blas_lapack.py:336-357, 448-501`). Step 40 already runs scipy-compatible meson from numpy's
  tree. A recipe `.pc` file with a pinned pkg-config is the alternative.
- **setjmp (EXECUTED).** f2py's callback code includes `<setjmp.h>`. wasi-libc refuses it
  without EH: `#error Setjmp/longjmp support requires Exception handling support`. With
  `-fwasm-exceptions -mllvm -wasm-enable-sjlj -mllvm -wasm-use-legacy-eh=false`,
  `_flapackmodule.c` compiles. The final link then needs `-lsetjmp` (the exceptions memo ran
  setjmp on SDK 33). Other setjmp users in scipy (READ): qhull, `_zerosmodule.c`,
  `__quadpack.h`, SuperLU's `_superlu_utils.c`. The cross file's `c_args` gain these flags.
- **Duplicate symbols (EXECUTED, READ).** `_fblasmodule.o` and `_flapackmodule.o` both define
  `_npy_f2py_ARRAY_API`. It is f2py's `PY_ARRAY_UNIQUE_SYMBOL` (`fortranobject.h:15`). As
  shared objects they never meet; statically they do (`duplicate symbol`). Both hold the same
  numpy API pointer, so one definition would be correct. How to get there without a patch (a
  per-file rename through the wrapper, with one module keeping the plain name for
  `fortranobject.c`) is spec work. Other C copies may clash with numpy (scipy vendors numpy's
  `logfactorial.c`); step 60's detector will name them.
- **Init-function names (EXECUTED).** `gen_inittab.py` refuses two modules that share a
  `PyInit_` name. scipy has two real clashes. `scipy.optimize._zeros` and
  `scipy.optimize.cython_optimize._zeros` collide with each other. scipy's `_cyutility` (the
  Cython shared utility module, built at `scipy/`) collides with pandas' `_cyutility`. Each
  needs a recipe rename of its init function and a matching `gen_inittab` entry.
  `_group_columns` and `_max_len_seq_inner` also appear twice in scipy's `meson.build`, but as
  the pythran and non-pythran alternatives; only one of each is built.
- **Scale (EXECUTED counts).** 97 distinct extension-module names (112 `extension_module`
  calls); 224 C++ sources in scipy and its subprojects. Pyodide's wheel has 107 `.so` files.
- **Host tools (READ, EXECUTED).** f2py from numpy has to run on the build host. The probe used
  numpy 2.5.2's cp315 wheel in a scratch venv; the step would pin that wheel per build host, as
  Cython is pinned. pybind11 (headers) and, if used, pythran (pure Python, with gast, beniget
  and ply) are new pinned wheels. `-Duse-pythran=false` drops pythran: 5 modules then fall back
  to Cython or Python (READ: `meson.build`; the speed cost is unmeasured).
- **Bytecode in the tree (EXECUTED).** Running scipy's generators left
  `scipy/_build_utils/__pycache__` in the unpacked tree. `common.sh` already sets
  `PYTHONDONTWRITEBYTECODE=1` for this reason (spec 003, Decision 4). The scratch tree was
  cleaned and re-diffed.

### 8. What WASI lacks, and which submodules feel it

- **Threads (EXECUTED).** The SDK's libc++ for `wasm32-wasip1` has `_LIBCPP_HAS_THREADS 1`, so
  `<thread>`, `<mutex>` and `<atomic>` compile. At run time `std::thread::hardware_concurrency()`
  is 1, a mutex works, and constructing a `std::thread` throws
  `std::system_error: thread constructor failed: Not supported` (`outputs/probe-thread2.txt`).
  The error is catchable under standard EH; uncaught, it ends the program.
  - **HiGHS** (`scipy.optimize.linprog`, `milp`; READ: `highs/parallel/*`) has a thread pool and
    no WASI guard. **INFERRED:** with a concurrency of 1 it should start no worker. If it does
    start one, the solver throws. This is the first thing to test after linalg.
  - **ducc0** (`scipy.fft`) has a switch, `-DDUCC0_NO_LOWLEVEL_THREADING` (READ:
    `infra/threading.h:57`), which scipy already sets for MinGW. A cross-file flag. `workers=`
    then has no effect.
  - **fast_matrix_market** (`scipy.io.mmread`/`mmwrite`) uses a thread pool (READ:
    `task_thread_pool.hpp`). With one thread it should run inline (INFERRED, untested).
  - **Python-level threading.** 14 modules outside `tests/` (two of them test helpers) import
    `threading`, `concurrent` or `multiprocessing` (EXECUTED: grep). Most
    use a lock or a thread-local, which CPython provides without threads. Any code that starts
    a thread fails as it does today for pandas.
- **C++ exceptions (READ, INFERRED).** pybind11 modules (`optimize`, `_highspy`,
  `_fast_matrix_market`, `fft/_duccfft`, `spatial`), Boost.Math (`scipy.special`, `stats`), xsf
  and HiGHS all throw and catch. The line already compiles C++ with standard EH
  (`cpp_exception_errors` in `tests/harness/scan.py` checks the cross files; `60_link.sh` links
  `-lunwind`). The scipy cross file needs the same `cpp_args`, and the scan's list of cross files
  grows by one.
- **setjmp/longjmp:** works with EH (finding 7). Affects `scipy.spatial` (qhull),
  `scipy.optimize` (zeros, f2py callbacks), `scipy.integrate` (quadpack), `scipy.sparse.linalg`
  (SuperLU). An EH-less host cannot run these, which is already true for the line.
- **dlopen: none (EXECUTED: no `dlopen` or `LoadLibrary` in scipy's C, C++ or Python).**
- **Signals: none outside HiGHS's test framework (`extern/catch.hpp`) (EXECUTED).**
- **ctypes (EXECUTED: imported by `_lib/_ccallback.py`, `integrate/_quadpack_py.py`,
  `io/arff/_arffread.py`, `stats/_continuous_distns.py`).** This project ships a ctypes
  stand-in (`recipes/ctypes_stub.py`). `LowLevelCallable.from_ctypes` will not work. Whether
  the four imports survive the stand-in is unchecked.
- **mmap:** OpenBLAS's buffers use wasi-libc's emulated `mmap`, which is malloc
  underneath. It is a libc library, not a new import (INFERRED; the import list was not checked).

### 9. Size and cost (INFERRED from Pyodide, with measured inputs)

Measured (EXECUTED, `outputs/pyodide-sizes.txt`, `outputs/pyodide-scipy-breakdown.txt`, Pyodide
314.0.7, all hashes match its lock file):

| Pyodide wheel | download | `.so` total |
|---|---|---|
| scipy 1.18.0 (107 `.so`, including a vendored `scipy.libs/libopenblas.so` of 6,467,976 B) | 14,029,750 B | 27,256,642 B |
| numpy 2.4.6 | 2,960,568 B | 5,237,696 B |
| pandas 3.0.2 | 4,177,749 B | 8,559,037 B |

- scipy's own `.so` by submodule: `special` 4.5 MB, `sparse` 4.1 MB, `optimize` 3.1 MB,
  `linalg` 3.0 MB, `spatial` 1.5 MB, `stats` 1.0 MB, `io` 0.9 MB, `fft` 0.8 MB, the rest under
  0.6 MB each.
- scipy's Python files and data outside tests: 639 files, 13.4 MB unpacked, 3.8 MB deflated.
- Our own `python.wasm` is 31,760,992 B (EXECUTED: `build/out/`). numpy and pandas are about
  40% of its code (READ: the profiles memo), about 12.7 MB. Pyodide's numpy plus pandas `.so`
  is 13.8 MB. The ratio is about 0.92.
- **Estimate (INFERRED):** scipy plus OpenBLAS adds about 0.92 × 27.3 MB ≈ **25 MB** to
  `python.wasm`. A static link shares one copy of libc++ and Boost templates where Pyodide has
  one per module, so 20–25 MB is the likely range. `cython_lapack` references the whole LAPACK,
  so `--gc-sections` will not trim OpenBLAS much. `python.wasm` would go from about 32 MB to
  about 52–57 MB.
- **The snapshot** carries the same code. If scipy is not pre-imported, it grows by about the
  same 20–25 MB, from 65.5 MB (EXECUTED: `build/out/python-snapshot.wasm`) to about 85–90 MB.
  Pre-importing scipy adds its import-time memory on top (unmeasured).
- **The stdlib zip** grows by about 3.8 MB if tests stay out.
- **Profiles.** scipy roughly doubles the data stack. It is a strong case for the build-time
  profiles of the profiles memo: a scipy profile beside the data profile, not scipy in every set.

### 10. Licences of what would be linked in

All READ from the sdists (`LICENSES_bundled.txt`, `LICENSE` files).

| component | licence | new to the project? |
|---|---|---|
| scipy | BSD-3-Clause | yes (same licence as numpy and pandas) |
| OpenBLAS (BLAS, kernels, drivers) | BSD-3-Clause | yes |
| LAPACK inside OpenBLAS (`lapack-netlib`, C translation) | modified BSD (LAPACK's own) | yes |
| ReLAPACK inside OpenBLAS | MIT | only if `BUILD_RELAPACK=1`; the default leaves it out |
| Boost.Math (headers) | BSL-1.0 | **yes, a new licence family** |
| HiGHS | MIT | yes |
| Qhull | the Qhull licence (permissive, custom) | **yes, a custom licence** |
| xsf | BSD-3-Clause AND MIT AND BSD-3-Clause-LBNL AND Apache-2.0 WITH LLVM-exception | Apache-2.0 WITH LLVM-exception is already shipped (libc++) |
| ducc0 | BSD-3-Clause | yes |
| UNU.RAN, SuperLU, ARPACK, L-BFGS-B, biasedurn, uarray | BSD-3-Clause | yes |
| fast_matrix_market | BSD-2-Clause; its fast_float MIT; its ryu BSL-1.0 | yes |
| pybind11 (headers compiled in) | BSD-3-Clause | yes |
| pythran runtime headers (if pythran is used) | BSD-3-Clause | yes; not checked further |
| array-api-compat, array-api-extra, Tempita (pure Python) | MIT | yes |
| PRIMA (pyprima), cobyqa (pure Python) | BSD-3-Clause | yes |

Constitution §4.12: none of these is linked until the owner approves it. The new families are
BSL-1.0, the Qhull licence, BSD-3-Clause-LBNL and BSD-2-Clause. MIT and the BSDs need notices
in the release; all are permissive.

## Recommended route

1. **scipy 1.18.1 with `-D_without-fortran=true`.** No Fortran compiler. `scipy.odr` is
   absent and documented as such.
2. **OpenBLAS 0.3.34 as the BLAS and LAPACK,** built by a new step from its release tarball:
   `NOFORTRAN=1`, no threads, static, `TARGET=WASM128_GENERIC`, with the five outside fixes of
   finding 5. The step builds in a copy of the tree, or the release workflow's diff must ignore
   build products. It goes through `scripts/wasi-cc` so `-fPIC` is dropped.
3. **Fix the ABI upstream, not here.** Open an OpenBLAS issue and pull request for one return
   convention in `C_LAPACK` builds (finding 6). Open a small scipy one for `?gees`'s hidden
   lengths and the two `cython_lapack` signatures. While they are pending, scipy waits (§4.1:
   "the project waits or ships without the feature").
4. **The same OpenBLAS pull request can carry the four portability fixes** (`ctest.c` and
   `__wasi__`, the `sys/ipc.h` guard, `<sched.h>`), so the recipe shrinks to make variables.
5. **Build scipy through numpy's vendored meson** with a `recipes/wasi-scipy.cross`:
   `openblas_includedir`/`openblas_librarydir`, the EH and sjlj flags, `DUCC0_NO_LOWLEVEL_THREADING`,
   and `-Duse-pythran=false` at first.
6. **Ship it as a profile,** not in every artifact set (finding 9).

The fallback, if upstream does not move: the generated rename-and-shim layer of finding 6. It
keeps §4.1 but costs about 150 generated shims, per release.

## The first experiment

What to try first, and what proves or kills the route. Each step is a scratch clone, like the
sqlite memo's.

1. **The library alone (hours).** Done in this memo up to the trap. Next: apply the candidate
   upstream fix (all `C_LAPACK` subroutines `void`) to a scratch copy, rebuild, and link the
   archive whole. **Proves:** 0 internal clashes, and `dgesdd_`, `dgees_`, `dsyevr_`, `zgesdd_`
   match native. **Kills the upstream plan:** clashes that are not return types (argument
   counts, callbacks) in large numbers.
2. **scipy.linalg only (a day).** Configure scipy with the cross file; build `_fblas`,
   `_flapack`, `cython_blas`, `cython_lapack`, `_decomp_*` and their Cython deps; link them into
   `python.wasm` with step 60's pattern. Run the direct-call probe: 0 clashes. In the guest, run
   `solve`, `lu`, `qr`, `svd`, `eigh`, `schur` (the `gees` path) and compare with native 3.15.0
   and scipy 1.18.1. **Kills:** a clash class the shims cannot express, or meson refusing the
   cross build.
3. **The C++ and thread-bearing submodules (a day).** `scipy.special` (Boost, xsf),
   `scipy.optimize.linprog` and `milp` (HiGHS), `scipy.fft` (ducc), `scipy.spatial` (qhull,
   setjmp). **Proves:** HiGHS solves with one thread; a qhull error raises a Python exception.
   **Kills scipy.optimize's LP parts only:** HiGHS insists on a worker thread.
4. **Everything, then measure.** The full build: link clashes (step 60's detector), size, fuel
   to `import scipy`, and the snapshot. Compare with the 20–25 MB estimate.

## Questions for the owner

1. **Licences (§4.12).** May BSL-1.0 (Boost.Math, ryu), the Qhull licence, BSD-3-Clause-LBNL
   (in xsf), BSD-2-Clause (fast_matrix_market) and the BSD/MIT set of finding 10 be linked?
   Without Boost there is no `scipy.special` or `scipy.stats`; without Qhull no
   `scipy.spatial.ConvexHull`/`Delaunay`.
2. **Upstream contact.** May the agent prepare an OpenBLAS issue and pull request (the return
   convention plus the WASI portability fixes) and a scipy one (`gees` and two signatures) for
   you to send? Sending is an outward action, yours to take (§7).
3. **Waiting versus the shim layer.** If upstream is slow, do we wait (§4.1's default), or
   accept a generated per-file rename-and-shim layer of about 150 functions as a recipe?
4. **scipy.odr.** Accept its absence? scipy has deprecated it.
5. **SIMD.** OpenBLAS's wasm target uses wasm SIMD (`-msimd128`). Is SIMD acceptable as a host
   requirement, as EH already is? Or should OpenBLAS be built for a non-SIMD generic target at a
   speed cost (unmeasured)?
6. **Profile or not.** scipy roughly doubles `python.wasm`. Should it ship only in a scipy
   profile, which makes the profiles work a prerequisite?
7. **pythran.** Build without it at first (5 modules fall back to slower code), or pin pythran
   and its three dependencies as build tools?

## Where it stopped

- The route is clear up to one blocker: signature clashes between OpenBLAS's C LAPACK, its own
  BLAS, and scipy's declarations. OpenBLAS builds, its LAPACK is complete, and three solvers
  give native answers. The SVD path traps.
- Not done: no part of scipy was configured with meson, compiled as a whole, or run. Only the
  BLAS/LAPACK wrappers were compiled and linked as a detector.
- Not done: the candidate OpenBLAS fix was not tried, even in scratch. Writing it would be our
  own patch to someone else's tree; it is upstream work for the owner to approve (question 2).
- Not done: HiGHS, ducc, fast_matrix_market, qhull and Boost on WASI are read, not run.
- Not done: LFortran; a non-SIMD OpenBLAS target; pythran on Python 3.15; whether scipy's four
  `ctypes` imports survive the stand-in.
- The scratch tree is kept in the scratchpad for the next session: OpenBLAS's build, the probe
  objects, the host venv with numpy 2.5.2. The LLVM tarball was deleted after listing.

## Sources (READ, web, 2026-10-17)

- [llvm/llvm-project#226471, Flang WebAssembly meta-issue](https://github.com/llvm/llvm-project/issues/226471)
- [llvm/llvm-project#226427, FIR CodeGen target support for WebAssembly](https://github.com/llvm/llvm-project/pull/226427)
- [r-wasm/flang-wasm](https://github.com/r-wasm/flang-wasm)
- [LFortran: Fortran on web](https://lfortran.org/blog/2024/05/fortran-on-web-using-lfortran/)
- [Fortran on WebAssembly (George Stagg)](https://gws.phd/posts/fortran_wasm/)

## One line

scipy 1.18.1 needs no Fortran compiler any more and OpenBLAS 0.3.34 builds for WASI without a
patch, but OpenBLAS's C LAPACK mixes `int` and `void` returns, which wasm turns into traps (some
invisible to the linker), so scipy waits on one mechanical upstream fix to OpenBLAS and a small
one to scipy, plus the owner's licence approvals.
