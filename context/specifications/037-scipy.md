# 037 — scipy, the first milestone

- **Status:** drafted 2026-10-17. It changes the build recipe and the artifact set, so it is
  reviewed once more before it is built (constitution §5.6). It is build-class: it touches
  `scripts/`, `recipes/`, `downloads/SHA256SUMS` and the release workflow (§5.7). Its second
  milestone is spec 038 (Decision 1).
- **Owner:** Clay Gendron
- **Kind:** the build recipe (pins; steps 00, 10, 38 (new), 57 (new), 60, 70; `scripts/build.sh`,
  `scripts/wasi-cc`, `scripts/gen_inittab.py`, `scripts/make_stdlib_zip.py`,
  `scripts/assemble_artifacts.py`, three new scripts), recipe files (a cross file, rename headers,
  a C shim file, a stand-in module), two carried patches to OpenBLAS, the reactor's `-V` banner,
  judge additions and changes (`tests/`), the release workflow's tree count, `README.md`,
  `CHANGELOG.md`, `LICENSES/`, upstream drafts under `context/upstream/`.
- **Depends on:** 020 (carried patches), 012 (the same bytes from any host), 021, and three
  specifications not yet built, each of which lands first (Decision 16): 023 (matplotlib M1: the
  pinned `pkgconf` and pybind11 3.1.0, `-lsetjmp`, `-l`/`-L` lines in `.deps`, `-pthread`
  dropped by `scripts/wasi-cc`, inittab names from install paths, the constructor check, the
  `target_features` check), 033 (the `ctypes` stand-in package, `make_stdlib_zip.py --metadata`)
  and 035 (the zip's directory read once; it changes this specification's numbers, not its
  design). Where one of them lands in another shape than its text, this specification uses what
  landed and says so in its landing notes.
- **Research it stands on:** `../research/2026-10-17-what-scipy-needs.md` and its folder (the
  version, no Fortran in scipy 1.18.1, OpenBLAS 0.3.34 for wasm with five outside fixes, the
  signature clashes, the static-link work, the threads and exceptions findings, the sizes);
  `../research/2026-10-17-openblas-one-return-convention.md` and its folder (the `void`
  convention: 111 clashes to 0, ten LAPACK paths equal to native to about 1e-14, the patch made
  by `scripts/make_void.py`, upstream `develop` merged the same convention in #6008 to #6082
  except `ilaver_`); `../research/2026-10-17-what-else-the-default-profile-carries/outputs/tiers.txt`
  (scipy's Python part: 610 members, 5,573,340 bytes deflated); the owner's decisions 25 and 28 to
  32 (`../decisions.md`); the scipy 1.18.1 sdist, read while drafting in a scratch folder (SHA-256
  `52c4b742…2747307`, equal to PyPI's, EXECUTED), for its `meson.build` files and subprojects.

## The problem

scipy is milestone 3 of 0.1.0 (`../roadmap.md`), in the default build (decision 30). Agents fit,
test, solve, filter and integrate; scipy is the second most used library after pandas in both
benchmarks the default-profile memo read. scikit-learn and statsmodels, both approved for 0.1.0
(decision 48), need it.

The research cleared the route up to one blocker and then removed it in scratch. scipy 1.18.1
builds without a Fortran compiler. OpenBLAS 0.3.34 is the only current, released LAPACK written in
C, and it builds for `wasm32-wasip1` with flags only. But its C LAPACK mixes `int` and `void`
returns for the same subroutines. wasm turns each mix into a trap, some invisible to the linker.
One mechanical convention, every subroutine `void`, removes all 111 clashes; upstream merged it
in `develop` but has not released it. The owner decided to carry such fixes as patches (decision
32). Nothing of scipy itself has been configured or run yet.

## Decisions

1. **Two milestones, and why the cut is here.** scipy's submodules import each other when
   imported: `scipy.linalg` imports `scipy.sparse.linalg` and `scipy.special`
   (`linalg/_matfuncs_inv_ssq.py`, READ); `scipy.optimize` imports HiGHS's module;
   `scipy.stats` imports nearly everything. A milestone that left out a submodule would ship a
   scipy whose own imports fail. So this milestone builds, links and judges **all of scipy except
   `scipy.odr`**. The cut is between "built and working" and "working at the sandbox's edges":
   - **037 (this one):** OpenBLAS, scipy, the link, the zip, the goldens.
   - **038 (`038-scipy-second-milestone.md`):** the three things that fail only because the
     sandbox has no threads, nothing writable and no libffi: `mmread`/`mmwrite`, `qmc.Sobol`
     with nothing writable, and the `ctypes` data pointers four scipy functions pass. They are
     known gaps here, each naming 038 as its closer (Decision 9).

   037 is about the size of 023 (one new C library step, one new package step, the link and zip
   changes, goldens). One builder builds it. The builder builds and gates OpenBLAS first
   (Decision 4's link-whole gate and Decision 6's direct-call gate) before any scipy work
   depends on it.

2. **The versions and pins.** Each is a URL and SHA-256 in `downloads/SHA256SUMS`, fetched by a
   `get` line in `scripts/00_download.sh`.
   - **scipy 1.18.1**, the sdist:
     `https://files.pythonhosted.org/packages/7e/74/66de6258867beb2ef08f35f9f2ac017a52cacd5081714d239ff1a442d458/scipy-1.18.1.tar.gz`,
     SHA-256 `52c4b7422442aba924d03ad4019852b08a92e64ea187b933135687bfe2747307` (EXECUTED: PyPI's
     digest and the downloaded bytes). It is the first release with cp315 wheels, so the oracle
     can run it (memo finding 1). Its numpy range (`>=2.0.0,<2.8`) holds the line's 2.5.2.
   - **OpenBLAS 0.3.34**:
     `https://github.com/OpenMathLib/OpenBLAS/releases/download/v0.3.34/OpenBLAS-0.3.34.tar.gz`,
     SHA-256 `cd7e129868320cc2d033afa920e31202dfe0b8066a5b66661900ccc0f197dfed` (EXECUTED by both
     memos; equal to GitHub's asset digest, re-read while drafting). It unpacks to
     `OpenBLAS-0.3.34`, the tree rule's name.
   - **numpy 2.5.2, the host wheel, one per build host, for f2py only** (Decision 7). scipy's
     build runs `f2py` on the build host, and f2py imports a real numpy. The names and hashes are
     PyPI's (READ from its JSON while drafting; checked against bytes on download like every
     pin): `numpy-2.5.2-cp315-cp315-macosx_14_0_arm64.whl`
     `e79aba74ffaf5f78a050d777c184cddf8fdffabab38acf5f3ef1fecbc17895d6`;
     `numpy-2.5.2-cp315-cp315-manylinux_2_27_aarch64.manylinux_2_28_aarch64.whl`
     `4ec954036759bcee3aa484f8603bd9c14f3e776293b85578b8734c2d72777c69`;
     `numpy-2.5.2-cp315-cp315-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl`
     `dc649493697006bc90614a5f0bbc8cb3cb1866715c474e473694968d7e6b99ab`. `scripts/line.conf`
     gains the three `*_NUMPY_HOST_WHEEL` host keys.
   - **Reused, not re-pinned:** Cython 3.3.0 (the line's), meson 1.12.1 (the line's), pybind11
     3.1.0 and pkgconf 3.0.7.post0 (023's).
   - **Cython 3.3.0 against scipy's `<3.3.0`.** scipy's `pyproject.toml` caps Cython below 3.3.0,
     but that cap is pip's; its `meson.build` checks only `>=3.2.0` (READ), and this project runs
     meson directly. The line keeps one Cython. The memo cythonized `cython_blas` and
     `cython_lapack` with 3.3.0 cleanly (EXECUTED), which is two modules, not proof. **Decided
     fallback:** if 3.3.0 fails on scipy's sources after two attempts (AGENTS.md rule 7), step 57
     uses a pinned Cython 3.2.x (the newest 3.2 release with cp315 wheels, one per build host)
     for scipy alone. Two Cythons in one binary are safe: each package has its own
     `_cyutility`.
   - **pybind11 3.1.0 against scipy's `<3.1.0`.** The same kind of cap ("pre-emptive upper
     bound", `pyproject.toml`); `meson.build` asks `>=2.13.2`. One binary must hold one pybind11:
     two versions' inline functions under one name would break the one-definition rule in a
     static link. So scipy uses 023's 3.1.0. There is no fallback version: a failure here stops
     the build and becomes a memo.

3. **LAPACK without Fortran.** No Fortran compiler targets `wasm32-wasip1` from a released,
   unpatched toolchain (memo finding 3: the SDK ships no flang; upstream flang for wasm is in
   progress and aims at Emscripten). scipy 1.18.1 needs none with `-D_without-fortran=true`
   (finding 2): ARPACK, PROPACK, QUADPACK, MINPACK, FITPACK, L-BFGS-B and SLSQP are C in this
   release, and f2py's Fortran wrapper files for `_fblas` and `_flapack` are empty. What remains
   is BLAS and LAPACK themselves. **OpenBLAS's own C translation of Reference-LAPACK
   (`NOFORTRAN=1`, which sets `C_LAPACK=1`) is the LAPACK.** CLAPACK 3.2.1 is too old (scipy
   declares `dgeqrt` and `dtpqrt`, from LAPACK 3.4), and translating Reference-LAPACK ourselves
   would rebuild what OpenBLAS ships. No f2c runtime is needed: OpenBLAS's translation carries
   its own prelude.

4. **Step 38: OpenBLAS** (`scripts/steps/38_openblas.sh`, after step 37, needing step 10).
   - It unpacks the tarball to `build/OpenBLAS-0.3.34`, applies its patches (`patch_tree`,
     Decision 5), and copies the patched tree with `cp -Rp` to `build/openblas-build`. It builds
     in the copy. OpenBLAS's `make` writes into its tree; the copy keeps the judged tree equal to
     its tarball plus the patches, whatever `make` writes.
   - The make line is the memo's (EXECUTED twice there to the same archive bytes), with `CC`
     through `scripts/wasi-cc` so OpenBLAS's `-fPIC` is dropped:
     `make libs netlib` with `TARGET=WASM128_GENERIC ARCH=wasm OSNAME=WASI NOFORTRAN=1
     C_LAPACK=1 NO_LAPACKE=1 USE_THREAD=0 USE_LOCKING=0 NUM_THREADS=1 NO_SHARED=1 NO_AFFINITY=1
     DYNAMIC_ARCH=0`, `HOSTCC=cc` (OpenBLAS builds its `getarch` tool for the build host; the
     build hosts already need `cc` for step 20), the SDK's `llvm-ar` and `llvm-ranlib`, and
     `CFLAGS="-O2 -ffile-prefix-map=@ROOT@=/wasi-python-build -D_WASI_EMULATED_SIGNAL
     -D_WASI_EMULATED_PROCESS_CLOCKS -D_WASI_EMULATED_GETPID -D_WASI_EMULATED_MMAN -DNO_SYSV_IPC
     -include sched.h -DARCH_WASM -I$HERE/recipes/openblas-include"`.
   - **The five outside fixes are recipe items** (memo finding 5): `ARCH=wasm` and `-DARCH_WASM`
     (OpenBLAS knows wasm only through `__EMSCRIPTEN__`), `-D_WASI_EMULATED_MMAN` and
     `-DNO_SYSV_IPC` (with `-lwasi-emulated-mman` at the final link), `-include sched.h`, and an
     empty stand-in `recipes/openblas-include/sys/ipc.h` (wasi-libc has none; with `NO_SYSV_IPC`
     nothing in it is used). None is a patch.
   - **Two more make variables fix host facts the memo's build picked up** (READ while drafting,
     in the memo's own generated `Makefile.conf`): `F_COMPILER=GFORTRAN` and `NUM_CORES=1`. The
     memo's macOS host had Homebrew's `gfortran` on `PATH`, so OpenBLAS's `f_check` chose
     `GFORTRAN`, which adds `-DF_INTERFACE_GFORT` to every C compile (`Makefile.system:1203`); a
     host without it would compile different code. `NUM_CORES` was the host's 10. Both are set on
     the make line, so every host compiles what the memo measured.
   - **SIMD.** `WASM128_GENERIC` compiles OpenBLAS's kernels with `-msimd128` (GEMM, DOT, ROT,
     SUM and TRSM kernels). wasm SIMD is accepted as a host requirement, in the default build
     (decision 29). Only OpenBLAS is compiled with it; numpy, pandas and scipy are not.
   - The step then runs `make install` with the same variables and
     `PREFIX=$B/openblas-wasi`. That installs the archive, the headers scipy includes, and
     OpenBLAS's own `lib/pkgconfig/openblas.pc`, which scipy finds through the pinned `pkgconf`
     (Decision 7).
   - **The link-whole gate.** The step links the archive with `--whole-archive` into a throwaway
     module (`wasm-ld --no-entry --allow-undefined`, as the memo's `scripts/link_whole.sh`) and
     dies on any `signature mismatch` warning, naming the first. The pristine 0.3.34 gives 111
     (EXECUTED by both memos); with the patches it gives 0 (EXECUTED: patch B). So the gate is
     seen failing first by building without `recipes/patches/OpenBLAS-0.3.34/`.
   - The step prints the archive's size and SHA-256. Spec 012's same-bytes rebuild compares the
     final artifacts; the archive's hash in both hosts' logs localises a difference if one
     appears.

5. **Two carried OpenBLAS patches** (spec 020's mechanism; §4.1).
   - **`recipes/patches/OpenBLAS-0.3.34/0001-c-lapack-subroutines-return-void.patch`**: the memo's
     patch B without `lapack-netlib/INSTALL/ilaver.c`. Every subroutine of C LAPACK returns
     `void`, as LAPACK's Fortran subroutines do; `xerbla_` gains its hidden length in the 20 f2c
     files that lacked it (rules R1 to R6, memo finding 2). 1,664 files. It is made by the memo's
     own script, `../research/2026-10-17-openblas-one-return-convention/scripts/make_void.py`,
     run on the pinned tarball, minus the one file. Patch B whole is 1,119,817 bytes, SHA-256
     `dde3be7a…3e92`, 116,496 bytes under `gzip -9` (EXECUTED while drafting, on the memo's
     scratch copy); 0001 is that less one small file section.
   - **`0002-ilaver-returns-void.patch`**: `ilaver_` returns `void`. One file, two hunks
     (`int ilaver_` to `void ilaver_`, `return 0;` to `return;`), the only section of patch B for
     that file (EXECUTED: read from patch B). scipy wraps `ilaver` as a subroutine in f2py and in
     `cython_lapack`; upstream `develop` still defines it `int` (memo finding 6).
   - **Why two.** 0001 is upstream's merged convention, backported by our own script; nothing is
     sent. 0002 is a real pull request to send. When OpenBLAS releases 0.3.35 with the
     convention, 0001 goes and the pin moves; 0002 goes when a release carries it.
   - **Their drafts**, under `context/upstream/patches/OpenBLAS-0.3.34/`, with spec 020's six
     header lines. 0001: `Status: merged https://github.com/OpenMathLib/OpenBLAS/pull/6082`; its
     body names the series (#6008, #6017, #6022, #6030, #6036, #6049, #6061, #6063, #6077, #6079,
     #6080, #6081, #6082), says the patch reaches the same convention by our script and is not
     upstream's diff, and says there is nothing to send. 0002: `Status: drafted`; its body is
     the pull request against `develop` (ILAVER is a SUBROUTINE; the C translation still returns
     `int`; callers that declare it `void` trap on wasm; tested by the memo's link-whole count on
     `develop`, 1 clash before, 0 after).
   - **The `Files:` line.** Spec 020's rule makes it name every path the patch touches. For
     0001 that is 1,664 paths, a line of about 49 KB (EXECUTED: the sum of path lengths and
     separators in patch B). The rule stands; the line is written by the same script.
   - **Reviewing 0001** is reviewing the script and its rules, then regenerating: the reviewer
     runs `make_void.py` on a fresh unpack of the pinned tarball, removes `ilaver.c`'s section,
     and compares the SHA-256 with the carried file (Acceptance, criterion 4). Nobody reads
     26,000 lines.
   - **Carried in git.** 0001 is text, about 1.1 MB, under `recipes/patches/`, as spec 020
     requires; a script that edited the tree at build time instead would be an unrecorded source
     change (§7). It is not an artifact, so §4.6 does not exclude it. The owner may say otherwise
     (question 62); nothing waits.
   - **The WASI portability fixes are not carried.** `__wasi__` beside `__EMSCRIPTEN__` in
     `ctest.c`, `<sched.h>` for WASI in `common.h`, and `<sys/ipc.h>` inside the existing
     `NO_SYSV_IPC` guard in `driver/others/memory.c` all work today as recipe items (Decision 4).
     They are drafted as one courtesy pull request for the owner to send, so the recipe can
     shrink to make variables: `context/upstream/<n>-openblas-wasi-portability/pr.md`, `<n>` the
     next free number at build time (035 takes 4).

6. **scipy's side of the ABI, as recipe files, not patches.** After the OpenBLAS patches, the
   memo's re-link left exactly six clashes on scipy's side (EXECUTED, finding 5): `?gees_` in
   f2py's `_flapack` (four precisions; f2py passes two hidden string lengths, 17 arguments
   against OpenBLAS's 15), and `chla_transtype_` and `xerbla_array_` in `cython_lapack`. §4.1
   asks for a recipe first, and each has one:
   - **`recipes/scipy_lapack_shims.c`**, six small C functions of ours, each with scipy's
     signature, each calling OpenBLAS's real one: `wasi_scipy_{s,d,c,z}gees_` take the 17
     arguments and drop the two lengths; `wasi_scipy_chla_transtype_(int *trans)` calls
     `chla_transtype_(&r, 1, trans)` and returns `r`; `wasi_scipy_xerbla_array_(name, len, info)`
     passes `(ftnlen)*len` as the hidden length. Step 57 compiles it with the SDK's clang into
     `build/scipy-shims/libscipy_lapack_shims.a`. It never includes a rename header.
   - **`recipes/scipy_rename.h`**, force-included in every scipy C and C++ compile (the cross
     file's `-include`, as `npy_rename.h` is for numpy): `chla_transtype_` and `xerbla_array_`
     to their shims (every scipy caller uses scipy's own declaration, so a global rename is
     right); `PyInit__cyutility` to `PyInit_scipy__cyutility` (it clashes with pandas'); and the
     C symbols that clash with numpy's copies, as step 60's detector names them (scipy vendors
     numpy's `logfactorial.c`; READ). Each entry is reviewed, as `npy_rename.h`'s are.
   - **Per-file includes.** Two renames must reach one file only. `?gees_` is renamed only in
     `_flapackmodule.c`: `cython_lapack` calls the same `dgees_` with 15 arguments and must keep
     calling OpenBLAS. And `scipy.optimize._zeros` (`_zerosmodule.c`) and
     `scipy.optimize.cython_optimize._zeros` (Cython) share the init name `PyInit__zeros`; only
     the second is renamed. So `scripts/wasi-cc` gains one general rule: when
     `WASI_CC_FILE_INCLUDES` names a map file, a compile whose source path ends with an entry's
     suffix gets that entry's `-include <header>`, and the wrapper appends one line to
     `$WASI_CC_FILE_INCLUDES.log`. Only step 57 sets the variable, so numpy, pandas and
     matplotlib compile byte for byte as before. The map is `recipes/scipy_file_includes.txt`
     (two lines); the headers are `recipes/scipy_flapack_rename.h` and
     `recipes/scipy_cython_optimize_zeros.h`. Step 57 checks the log: each entry matched exactly
     one compile.
   - **f2py's numpy API pointer.** `_fblas` and `_flapack` both define `_npy_f2py_ARRAY_API`
     (f2py's `PY_ARRAY_UNIQUE_SYMBOL`), a duplicate symbol in a static link (memo finding 7).
     numpy's own hook settles it: `__multiarray_api.h` writes every definition and declaration
     of the API pointer with `NPY_API_SYMBOL_ATTRIBUTE` (READ, step 40's generated header).
     `scipy_rename.h` defines it as `__attribute__((weak, visibility("hidden")))`. Both modules'
     definitions become weak, the linker keeps one, and `fortranobject.c` (compiled once, in
     scipy's `_fortranobject` static library) refers to that one. Each module's `import_array()`
     writes the same numpy table into it. Modules that use numpy's API without
     `PY_ARRAY_UNIQUE_SYMBOL` keep a `static` pointer, where the macro is unused. INFERRED: the
     static link and the goldens prove it.
   - **The direct-call gate** (memo finding 6: f2py calls LAPACK through a function pointer, so
     a clash there links silently and traps at run time). `scripts/f2py_direct_calls.py`, our
     own (adopted from the memo's `scripts/gen_direct_calls.py`, which this project wrote), reads
     each routine's prototype from the generated `_fblasmodule.c` and `_flapackmodule.c` and
     writes one C file with one direct call per routine. Step 57 compiles it with
     `_flapackmodule.c`'s flags and per-file include, links it with OpenBLAS's archive and the
     shims, and dies on any `signature mismatch`. With the pristine archive it finds 37 (EXECUTED
     by the memo); with the patches and shims it must find 0.
   - **Upstream.** The scipy side is a courtesy pull request for the owner to send, not a carried
     patch: the two `?gees` hidden lengths in `scipy/linalg/flapack_gen.pyf.src` (its
     `callstatement` and `callprotoargument`; every other f2py wrapper in scipy passes none, and
     `cython_lapack`'s `?gees` passes none), and `chla_transtype` and `xerbla_array` in
     `scipy/linalg/cython_lapack_signatures.txt`. `context/upstream/<n>-scipy-c-lapack-signatures/pr.md`.
     Before the owner sends it, the draft states scipy's policy on AI-written contributions as
     read then; where it forbids such text, the draft is the facts for the owner to write from,
     as numpy's is.

7. **Step 57: scipy** (`scripts/steps/57_scipy.sh`, after step 55; needing 10, 20, 38, 40).
   - It unpacks the sdist to `build/scipy-1.18.1` and applies its patches (none in 037; 038
     adds two). It builds out of tree in `build/scipy-build`.
   - **f2py on the host.** Step 10 installs the build host's pinned numpy wheel into its own
     folder, `build/tools/f2py-numpy`, never into `build/tools/pylib`: there it would shadow the
     host-side numpy stand-in that pandas' and scipy's builds import. `scripts/f2py-host` runs the
     host Python with only that folder on `PYTHONPATH`, as `python -m numpy.f2py`. Step 57 puts
     a folder holding it as `f2py` first on `PATH`, because scipy's
     `tools/generate_f2pymod.py` runs `f2py` from `PATH` (READ, line 295). f2py reads the
     `.pyf` files and writes C; it never runs scipy code. Its version is the wasm numpy's, 2.5.2,
     so the generated modules match `fortranobject.c`, which comes from step 40's install.
   - **`recipes/wasi-scipy.cross`**, from the numpy and pandas cross files, with:
     - `[binaries]`: the same compilers, archiver and target Python; `pkg-config` the pinned
       `pkgconf` (023), and `cmake` a program that does not exist, as 023 does, so every
       dependency is found by `pkgconf` on every host;
     - `[properties]`: `numpy-include-dir`, step 40's installed `numpy/_core/include` (scipy
       reads it instead of running the target Python, READ: `scipy/meson.build:56-60`);
     - `c_args`: the pandas set, `-include scipy_rename.h`, and the setjmp flags
       `-fwasm-exceptions -mllvm -wasm-enable-sjlj -mllvm -wasm-use-legacy-eh=false` (f2py's
       callbacks, `_zeros`, QUADPACK, SuperLU and qhull use setjmp; memo finding 7);
     - `cpp_args`: the numpy set (standard C++ exceptions), the same include and setjmp flags,
       `-DDUCC0_NO_LOWLEVEL_THREADING` (ducc0's switch, which scipy sets for MinGW;
       `fft/_duccfft/meson.build:8`), `-DHIGHS_NO_DEFAULT_THREADS` (HiGHS then asks for one
       thread whatever the host reports; `highs/parallel/HighsParallel.h:21`, READ), and
       `-DBOOST_MATH_PROMOTE_DOUBLE_POLICY=false` (below).
   - **`PKG_CONFIG_PATH`** holds exactly three folders: `build/openblas-wasi/lib/pkgconfig`,
     step 40's numpy `pkgconfig` folder (`dependency('numpy')`) and pybind11's (023). scipy asks
     `dependency('scipy-openblas', method: 'pkg-config', required: false)` first and finds
     nothing; then `dependency(['openblas', 'OpenBLAS'])` finds ours (READ:
     `scipy/meson.build:287-297`). No BLAS finder from numpy's vendored meson is needed.
   - **The configure line:** the line's meson 1.12.1, `meson setup --cross-file … --buildtype=release
     -Db_ndebug=if-release -D_without-fortran=true -Duse-pythran=false -Dblas=openblas
     -Dlapack=openblas -Duse-system-libraries=none`, then `ninja`. The release build type and
     asserts off are meson-python's defaults, as scipy's wheels are built. No ILP64 (wasm32's
     `int` is LP64's).
   - **Without pythran** (decision 31): five modules fall back to Cython or Python
     (`_group_columns`, `_max_len_seq_inner` and others; memo finding 7).
   - **Boost.Math without promotion to `long double`.** Boost's default policy computes many
     double-precision functions in `long double`. On wasm32 that is software binary128; on the
     oracle's platform (macOS arm64) `long double` is `double`, so the promotion is a no-op there
     already. `-DBOOST_MATH_PROMOTE_DOUBLE_POLICY=false` gives the guest the oracle's arithmetic
     and avoids software quad precision. The goldens check the values. The landing notes record
     the fuel of one Boost-backed call (`stats.beta.ppf`), so a later change of the flag can be
     measured against it.
   - **The shims and the gates.** The step compiles `recipes/scipy_lapack_shims.c`, runs the
     direct-call gate (Decision 6), and checks the per-file include log.
   - **The Python package, from meson's install plan.** `meson install` is not run: on a macOS
     host it fixes install names in installed extension modules, and here they are archives
     (step 40's comment); scipy tags its `_cyutility` module `python-runtime`, so even a
     `python-runtime` install would reach one. A new script, `scripts/install_from_plan.py`,
     reads `meson introspect --install-plan` and copies each file whose tag is `python-runtime`
     (or untagged Python source) to its destination under `build/scipy-install`, skipping every
     extension module and every file tagged `tests`. That places the generated `__config__.py`,
     the sdist's `version.py`, the `_external` packages (array-api-compat, array-api-extra,
     cobyqa, pyprima) and the data files (`stats/_sobol_direction_numbers.npz`) where an install
     would. It writes the extension-module list, with each module's build path, install path
     and tag, to `build/scipy-build/extension-modules.txt` for step 60.

8. **The extension modules become builtins.**
   - **Which.** Every extension module in that list except the seven tagged `tests`
     (`_lib/_test_ccallback`, `_lib/_test_deprecation_call`, `_lib/_test_deprecation_def`,
     `integrate/_test_multivariate`, `ndimage/_ctest`, `ndimage/_cytest`,
     `special/_test_internal`; EXECUTED: a scan of scipy's `meson.build` files while drafting,
     93 other `extension_module` calls, some of them pythran, ILP64 or `odr` alternatives not
     built here). About 85 are linked; the build records the count.
   - **Step 60** adds `scipy` to its package loop (023's install-path inittab names, from
     `extension-modules.txt`), and to the `_host` line: OpenBLAS's archive,
     `libscipy_lapack_shims.a`, scipy's static libraries from the `.deps` files (`-l` and `-L`
     lines honoured, as 023 makes them), and `-lwasi-emulated-mman`. `-lsetjmp` and the C++
     runtime libraries are already there after 023.
   - **Init names.** `scripts/gen_inittab.py` gains a table of renamed init functions:
     `scipy._cyutility` → `PyInit_scipy__cyutility` and
     `scipy.optimize.cython_optimize._zeros` → `PyInit_scipy_optimize_cython_optimize__zeros`.
     Its clash check runs on the final names. scipy's `_cyutility` is its own module,
     `scipy._cyutility`, distinct from pandas'. No other scipy name clashes with numpy's or
     pandas' (EXECUTED: the memo's two module lists compared while drafting; one common name,
     `_cyutility`) or with matplotlib M1's (READ: 023's module list).
   - **Clashes.** Step 60's `clashes()` already stops the build on `signature mismatch` and
     `duplicate symbol`. Each one found is fixed by a `scipy_rename.h` entry or a shim, never
     ignored.
   - **Constructors.** 023's check compares the functions `__wasm_call_ctors` calls with a
     reviewed list. scipy's C++ (HiGHS, Boost, pybind11 modules, sparsetools) adds static
     initializers. The builder lists each new one and reads its source: one that touches Python
     would hang `_initialize`, as `ft2font`'s did (023, Decision 3). A grep while drafting found
     no namespace-scope pybind11 object in scipy's C++ (READ). The reviewed list grows by
     exactly the names the build shows (a judge change).
   - **One qhull.** scipy compiles its vendored qhull 8.0.2 (`subprojects/qhull_r`), which
     carries scipy's own format-string fix (`subprojects/qhull_r/patches/poly2rc.patch`, a
     security-scanner finding; READ). 023 builds qhull in step 37 but links none of it. So this
     binary has one qhull, scipy's. Whichever of this specification and matplotlib's second
     milestone lands second makes the two share one qhull; a second copy would be a duplicate
     symbol. If M2 lands first (matplotlib then links step 37's qhull), step 57 uses
     `-Duse-system-libraries=qhull` against step 37's build instead, and this specification
     carries scipy's format-string fix as a qhull patch
     (`recipes/patches/qhull-8.0.2/0001-format-strings.patch`, `Status: merged`, upstream
     qhull's commit `1b67ec90`).

9. **What is in, what is out, and how an absence shows.**
   - **In:** every public submodule but one: `cluster`, `constants`, `datasets` (its loaders
     need `pooch` and a network; below), `differentiate`, `fft`, `fftpack`, `integrate`,
     `interpolate`, `io`, `linalg`, `misc`, `ndimage`, `optimize` (with HiGHS: `linprog`,
     `milp`), `signal`, `sparse` (with `csgraph` and `linalg`: SuperLU, ARPACK, PROPACK),
     `spatial` (qhull, `cKDTree`), `special` (Boost.Math, xsf), `stats`.
   - **Out, for good on this line: `scipy.odr`** (decision 28). It needs ODRPACK, which is
     Fortran, and scipy deprecated it for removal in 1.19 (READ: `odr/__init__.py`). With
     `_without-fortran` meson builds and installs none of it. A stand-in, `recipes/scipy_odr_stand_in.py`,
     is packed as `scipy/odr.py`. Importing it raises
     `ImportError("scipy.odr is not in this build: it needs a Fortran compiler, which
     wasm32-wasip1 does not have; scipy deprecated it for removal in 1.19")`. scipy's own
     `_lib/_public_api.py` already drops `scipy.odr` from its public list when the folder is
     missing (READ, line 62). The `-V` banner (`recipes/reactor_bootstrap.py`) gains it: "no
     ctypes, mmap, sockets, ssl, zstd or scipy.odr".
   - **Absent by the platform, documented in the README, not gaps:**
     - `LowLevelCallable.from_ctypes` and any ctypes function pointer: no libffi in wasi-sdk
       (033's rule: making a ctypes function raises `OSError`).
     - `workers=` above 1 where scipy uses processes or threads (`differential_evolution`,
       `brute`, `scipy.fft` with ducc's threading off: accepted and serial), as for pandas.
     - `scipy.datasets` downloads: no `pooch`, no network (§4.15).
   - **Known gaps, closed by 038** (`tests/known_gaps.toml`, each naming
     `specifications/038-scipy-second-milestone.md`):
     - `scipy.io.mmread` and `mmwrite` raise `RuntimeError`: fast_matrix_market's default
       parallelism (0) starts a thread pool, and `std::thread` throws on WASI (READ:
       `read_body.hpp:477`, `task_thread_pool.hpp:137-142`; the memo's probe, EXECUTED).
     - `stats.qmc.Sobol` with nothing writable raises `OSError`: `_sobol.pyx` loads its
       direction numbers through `importlib.resources.as_file`, which copies to a temporary file
       (READ, lines 147-150).
     - `stats.geninvgauss.cdf`, `stats.genhyperbolic.cdf`, `stats.studentized_range` (and so
       `tukey_hsd`), and `io.arff.loadarff` raise `OSError` from the `ctypes` stand-in: they make
       a `c_void_p` or `c_ulong` instance (READ: `_continuous_distns.py:4144, 5249, 12402`,
       `_arffread.py:485`).
   - **Threads at import.** 14 scipy modules import `threading` or `concurrent.futures` for
     locks and thread-locals (memo finding 8). They import; nothing starts a thread unless asked.

10. **The zip.** Step 70 gains `--tree "$B/scipy-install"`, `--metadata
    "$B/scipy-1.18.1/PKG-INFO"` (033's option), and
    `--file "$HERE/recipes/scipy_odr_stand_in.py=scipy/odr.py"`. `make_stdlib_zip.py` already
    skips `tests` folders, sources, `.pyi` and `.pxd`. `scipy/__config__.py` joins `REWRITE`: its
    "Machine Information" → "build" keys are set to the fixed values numpy's get (the walk
    already finds that dict by name), and the existing `--replace` texts take the build paths
    out of its compiler commands and dependency folders, so the zip stays the same bytes from
    any host (spec 012, Decision 5). The rule "an old text found in neither stops the build"
    becomes "found in none of the three".

11. **The snapshot does not pre-import scipy.** Step 80 is unchanged. A first `import scipy.stats`
    on the snapshot therefore pays scipy's whole import. Whether the default snapshot should
    pre-import it is the owner's (question 61, the scipy counterpart of question 34). The build
    measures and records the numbers that question needs (Acceptance, criterion 5).

12. **The same bytes from any host (spec 012).** arm64 macOS and arm64 Linux must give the same
    `SHA256SUMS`, with no exception. The new host-side inputs are each fixed: OpenBLAS's
    `getarch` with every host-detected value set on the make line (Decision 4); f2py's output,
    which is C made from `.pyf` text; Cython's, from relative paths; scipy's `__config__.py`
    (Decision 10). x86_64 Linux stays outside the gate, as it is today
    (`../research/2026-10-17-x86-64-rebuilds-differ-in-one-function.md`); its rebuild is run
    once and the landing notes say whether its differences grew beyond `npy_cpowl`.

13. **Licences** (§4.12; all approved by decision 25, Qhull and pybind11 also by question 35).
    `LICENSES/` gains, each as its project ships it: scipy's `LICENSE.txt` and
    `LICENSES_bundled.txt`; OpenBLAS's `LICENSE` and `lapack-netlib/LICENSE`; the licence files
    of each vendored subproject that is compiled in or packed (`boost_math`, `xsf`, `highs`,
    `duccfft`, `qhull_r`, `unuran`, `array_api_compat`, `array_api_extra`, `cobyqa`, `pyprima`);
    and of fast_matrix_market, its fast_float and ryu, SuperLU, ARPACK, PROPACK and uarray inside
    the scipy tree. The builder lists every compiled-in component of `LICENSES_bundled.txt`
    against a file in `LICENSES/`; ampgo (benchmarks only) and Chebfun (Python source with its
    notice in place) need none beyond scipy's own files. `scripts/assemble_artifacts.py` copies
    them and adds scipy to `PACKAGES`.

14. **What the set costs, so growth can be told from regression.** Today (EXECUTED while
    drafting, `build/out`): `python.wasm` 31,760,992 bytes, the snapshot 65,506,824, the zip
    11,140,635 bytes and 1,751 members. 023 comes first and moves all of these (its Decision 6).
    This specification's own growth, each measured by the build and recorded in the landing
    notes:
    - `python.wasm`: about +20 to +25 MB (INFERRED: Pyodide's scipy and OpenBLAS `.so` total
      27.3 MB, times the 0.92 ratio of our numpy and pandas to Pyodide's, less the C++ runtime
      and Boost templates a static link holds once; memo finding 9). `cython_lapack` refers to
      all of LAPACK, so little of OpenBLAS is dropped by the linker.
    - the snapshot: about the same bytes as `python.wasm`'s growth, since scipy is not
      pre-imported.
    - the zip: about +605 members and +5.6 MB (EXECUTED by the default-profile memo on the
      native wheel's Python part: 610 members, 5,573,340 bytes; `odr`'s few members leave, one
      stand-in comes).
    - plain `-c pass`: about +15 M fuel if 035 has landed (about 605 members at about 24,000
      fuel each, 035's slope), or about +47 M if it has not (77,912 per member, `tiers.txt`);
      plus the new static constructors and about 85 more inittab entries, which are measured
      and named, not estimated.
    - snapshot `-c pass`: within 1% (its constructors ran at build time; its directory is
      already read).
    - every existing golden job: no change beyond the plain-start growth above; none imports
      scipy.
    A growth outside these by more than a tenth, or a plain `python.wasm` growth outside 18 to
    28 MB, is a finding for the build review, not a reason to accept.

15. **The checks**, each seen failing first.
    - **Golden jobs (v1.3),** native scipy 1.18.1 as the oracle: `tests/jobs/oracle` gains
      `scipy==1.18.1` in `pyproject.toml` and `uv.lock`; `JOBS` gains three jobs; `regen.py`
      writes their goldens. Each prints a `versions` line with `scipy=1.18.1`. Each float is
      printed as numpy's job prints it (`round(x, k) + 0.0`, then `.{k}g`): `k = 9` for direct
      results and `k = 6` for iterative ones. No iteration counts, no eigenvector or singular
      vector signs (they depend on the LAPACK build), no timings. Every input is fixed in the
      file or drawn from a seeded `numpy.random.Generator(PCG64(…))`. If a printed value sits so
      near a rounding boundary that the guest and the oracle differ in its last digit, the job's
      input changes, never `k`.
      - `scipy_numeric.py`: `linalg` (`solve`, `lu_factor` pivots and `U`'s diagonal, `qr`'s
        `|diag(R)|`, `cholesky`, `det`, `inv` residual, `eigh` and `eigvalsh` values, `svdvals`,
        `expm`, `solve_triangular`); `sparse` (CSR build, product, `spsolve` through SuperLU,
        `eigsh` with a given `v0` through ARPACK, `csgraph.shortest_path` and
        `connected_components`); `fft` (`fft`, `rfft`, `dct`, `fftfreq`); `special` (`gamma`,
        `erf`, `jv`, `beta`, `hyp2f1`, `ellipk`, `zeta`); `stats` (`norm.cdf` and `ppf`,
        `t.sf`, `beta.ppf`, `binom.pmf`, `describe`, `ttest_ind`, `pearsonr`, `linregress`,
        `gaussian_kde`); `interpolate` (`CubicSpline`, `make_interp_spline`, `griddata`
        linear, which runs qhull, `RBFInterpolator`); `signal` (`butter`, `lfilter`,
        `filtfilt`, `convolve`, `find_peaks`, `welch`); `ndimage` (`gaussian_filter`, `label`);
        `spatial` (`distance.cdist`, `cKDTree.query`, `ConvexHull.volume`, `Delaunay`'s simplex
        count); `cluster` (`hierarchy.linkage`).
      - `scipy_solvers.py` (`k = 6`): `optimize` (`minimize` on Rosenbrock with BFGS,
        Nelder-Mead, L-BFGS-B and SLSQP with a constraint; `root` with `hybr`;
        `least_squares`; `curve_fit`; `brentq`; `linprog` and `milp` through HiGHS;
        `linear_sum_assignment`); `integrate` (`quad`, `dblquad`, `solve_ivp` with RK45 and
        BDF, `odeint`, `simpson`).
      - `scipy_lapack.py` (`k = 9`): every routine the memo found trapping, through
        `get_lapack_funcs` in all four precisions: `gesv`, `getrf`, `getrs`, `laswp`, `lauum`,
        `potrf`, `trtri`, `trtrs`; `ilaver()`; `gees` with a sort callback (`schur(…,
        sort="lhp")`, its eigenvalues as a sorted set and `sdim`); and `eig`, `svd`, `lstsq`,
        `pinv` and `qr_update` (through `cython_lapack`).
      Seen failing first: each fails on the current set (`ModuleNotFoundError: No module named
      'scipy'`); `scipy_lapack.py` also traps on a build with the OpenBLAS patches removed, which
      the builder runs once (Acceptance, criterion 1).
    - **Errors that must reach Python (v1.3,** `tests/checks/test_v1_3_scipy.py`, each on both
      binaries with nothing writable):
      - `linalg.solve` of a singular matrix raises `LinAlgError`;
      - `ConvexHull` of collinear points raises `QhullError` (qhull's `longjmp`, and scipy's
        message stream, which uses `open_memstream` and needs no temporary file; if meson finds
        no `open_memstream` the stream falls back to `tempfile`, and this check fails);
      - `optimize.brentq` and `integrate.quad` with a Python function that raises `ValueError`
        re-raise it (the `setjmp` paths in `_zeros` and QUADPACK);
      - `linprog` of an infeasible problem returns `status == 2` (HiGHS ran with one thread);
      - `import scipy.odr` raises `ImportError` whose message names "Fortran";
      - `python -V` names `scipy.odr` among the missing.
    - **Rules and artifact checks (judge changes, under `--accept-judge`):**
      - v1.1: `python.wasm`'s `target_features` list gains `simd128` (decision 29); any other
        new feature still fails it.
      - v1.1: 023's constructor list gains the reviewed scipy names (Decision 8).
      - v1.5: `SOURCE_PATTERNS` and `needs.SOURCE_COMPONENTS` gain OpenBLAS and scipy; the
        release workflow's tree count rises by two; the patched-tree check covers OpenBLAS's
        two patches.
      - rules: `scan.cpp_exception_errors` judges `recipes/wasi-scipy.cross`; spec 020's
        `patch_errors` passes on the two patches and drafts.
      - `tests/known_gaps.toml`: the three gaps of Decision 9, each with its exact finding.
    - **Build-time gates, not judge checks:** step 38's link-whole gate (Decision 4); step 57's
      direct-call gate and per-file include log (Decision 6); step 60's clash detector.
    - **Unit checks** (no artifacts): `scripts/f2py_direct_calls.py` on a small generated module
      text; `scripts/install_from_plan.py` on a small install plan (tags `tests` and extension
      modules skipped, destinations kept); `scripts/gen_inittab.py`'s rename table and its clash
      check on the renamed names; `scripts/wasi-cc`'s per-file include (a matching path gets the
      header and a log line; another path is compiled exactly as before), each seen failing
      before its code exists.

16. **Ordering with other build-class work** (§5.7: one build-class specification in flight, one
    landing at a time). The queue ahead of this one, by the roadmap and by 035's Decision 12:
    028 (milestone 1), 033, 035, then 023. **037 builds after 023 lands**, because it uses
    023's pins and link machinery (Depends on). **038 builds right after 037**, then tier A and
    the rest of milestone 4 as the roadmap orders them; scikit-learn and statsmodels (decision
    48) come after 038. matplotlib's second milestone is not yet specified; Decision 8's qhull
    rule covers either order. Files 037 shares with others: step 60 and `gen_inittab.py` (023,
    035), step 70 and `make_stdlib_zip.py` (023, 033), `scripts/wasi-cc` (023). Each is rebased
    onto main as it is when 037's builder starts.

## Intent

An agent's code solves, fits, tests, filters and integrates with scipy inside the same sealed
Python, and gets native scipy's answers, with no Fortran compiler anywhere and only recorded,
temporary changes to OpenBLAS.

## Design

| file | change |
|---|---|
| `downloads/SHA256SUMS`, `scripts/00_download.sh`, `scripts/line.conf` | the scipy sdist, the OpenBLAS tarball, three numpy host wheels (`*_NUMPY_HOST_WHEEL`) (Decision 2) |
| `scripts/steps/10_tools.sh` | the host numpy wheel into `build/tools/f2py-numpy` (Decision 7) |
| `scripts/f2py-host` | new: `python -m numpy.f2py` with only that folder on the path |
| `scripts/steps/38_openblas.sh` | new: unpack, patch, copy, make, install, the link-whole gate (Decision 4) |
| `recipes/openblas-include/sys/ipc.h` | new: the empty stand-in header |
| `recipes/patches/OpenBLAS-0.3.34/0001-c-lapack-subroutines-return-void.patch`, `0002-ilaver-returns-void.patch` | new (Decision 5) |
| `context/upstream/patches/OpenBLAS-0.3.34/0001-…md`, `0002-…md` | their drafts |
| `context/upstream/<n>-openblas-wasi-portability/pr.md`, `context/upstream/<n>-scipy-c-lapack-signatures/pr.md`, `context/upstream/README.md` | courtesy drafts and their rows (Decisions 5, 6) |
| `scripts/steps/57_scipy.sh` | new: configure, build, shims, gates, the package (Decision 7) |
| `recipes/wasi-scipy.cross` | new (Decision 7) |
| `recipes/scipy_rename.h`, `recipes/scipy_flapack_rename.h`, `recipes/scipy_cython_optimize_zeros.h`, `recipes/scipy_file_includes.txt`, `recipes/scipy_lapack_shims.c` | new (Decision 6) |
| `scripts/wasi-cc` | the per-file include rule and its log (Decision 6) |
| `scripts/f2py_direct_calls.py`, `scripts/install_from_plan.py` | new (Decisions 6, 7) |
| `scripts/gen_inittab.py`, `scripts/steps/60_link.sh` | scipy's modules, the rename table, the new archives and `-lwasi-emulated-mman` (Decision 8) |
| `recipes/scipy_odr_stand_in.py`, `recipes/reactor_bootstrap.py` | the `scipy.odr` stand-in; the banner (Decision 9) |
| `scripts/steps/70_zip.sh`, `scripts/make_stdlib_zip.py` | the scipy tree, its metadata, the stand-in, `scipy/__config__.py` made host-neutral (Decision 10) |
| `scripts/build.sh`, `scripts/assemble_artifacts.py`, `LICENSES/` | steps 38 and 57 in `ALL`; licences; `PACKAGES` (Decision 13) |
| `tests/jobs/scipy_numeric.py`, `scipy_solvers.py`, `scipy_lapack.py` and their `.expected`; `tests/jobs/oracle/pyproject.toml`, `uv.lock`; `JOBS` in `tests/harness/jobs.py` | the goldens (Decision 15) |
| `tests/checks/test_v1_3_scipy.py` | new: the error checks |
| `tests/checks/test_v1_1_artifact_set.py` (or 023's file), `tests/harness/pins.py`, `tests/harness/needs.py`, `tests/harness/scan.py`, `tests/known_gaps.toml` | the judge changes (Decision 15) |
| `tests/unit/…` | the unit checks (Decision 15) |
| `.github/workflows/…` | the tree count, two more |
| `README.md`, `CHANGELOG.md` | scipy in the profile; the absences and gaps; SIMD as a host requirement; the patches by path |

## Scope

In: Decisions 1 to 16. Out:

- **038's three gaps** (Decision 9).
- **pythran** (decision 31). A later specification may pin it and its three dependencies and
  measure what the five modules gain.
- **Pre-importing scipy in the snapshot** (question 61).
- **ILP64** BLAS, and a non-SIMD OpenBLAS target.
- **A Fortran compiler**, and with it `scipy.odr`. The memo's advice stands: re-check upstream
  LLVM's flang for wasm at each LLVM release.
- **matplotlib's `_qhull`** (its second milestone); Decision 8 says only how the two share qhull.
- **scipy's own test suite under the runtime** (roadmap milestone 6, hardening).

## Acceptance criteria

1. The checks exist and were seen failing first: the goldens and the error checks on the
   current set; `scipy_lapack.py` trapping on a build without the OpenBLAS patches; the
   link-whole gate failing with 111 and the direct-call gate with 37 on that build; the unit
   checks before their code.
2. A full build from pins in a clean clone applies both OpenBLAS patches with no offset, builds
   steps 38 and 57, passes every gate, and makes a set whose binaries run the three goldens and
   the error checks. `MANIFEST` names every new pin, recipe and patch.
3. The same-bytes rebuild on arm64 Linux gives the same `SHA256SUMS` as macOS, with no
   exception (spec 012). If a difference cannot be fixed after two attempts, the build stops and
   a memo records it (AGENTS.md rule 7); it does not land with an exception. The x86_64 rebuild
   is run once and reported (Decision 12).
4. The reviewer regenerates `0001` with `make_void.py` on a fresh unpack of the pinned tarball,
   less `ilaver.c`'s section, and gets the carried file's SHA-256; `0002` is that section.
5. The landing notes record, each measured: the three binaries' and the zip's bytes, the zip's
   member count, the number of scipy modules linked, the new constructors by name, plain and
   snapshot `-c pass` fuel, the fuel of `import scipy`, `import scipy.linalg`,
   `import scipy.stats` and `import scipy.optimize` on both binaries, and the snapshot's bytes and
   `-c pass` fuel if it pre-imported `scipy.stats` (for question 61), and the Boost flag's fuel
   fact (Decision 7). Each is inside Decision 14's bounds or is a finding.
6. `uv run pytest` is green with `--accept-judge` and `--accept-growth`, each reason stated.
7. A release dry run passes every job.

## The owner's choices

None open here. Two are recorded in `../questions-for-the-owner.md`, each decided here as written
so nothing waits: **61**, whether the default snapshot pre-imports scipy (decided: no, until the
build's numbers are in; Decision 11); **62**, whether a 1.1 MB carried patch may live in git
(decided: yes; Decision 5).

## Landing notes

Not built.
