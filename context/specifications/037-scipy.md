# 037 — scipy, the first milestone

- **Status:** built 2026-10-19, awaiting its build review (Revised at build and the landing notes, below). **Spec 051's callback scan binds this build** (051, Decision 4a; written in when 051 landed): `test_callbacks_have_the_types_cpython_calls` is green, and a mismatch it finds is fixed by a carried patch or an upstream release, never by an exclusion. confirmed for build with conditions, written in. Drafted 2026-10-17; revised the
  same day against its pre-build review (`../reviews/037-scipy-spec-2026-10-17.md`): findings 1
  to 4 fixed in the text and the checks, 5 to 13 fixed or answered (the review's Disposition),
  and spec 040's asks written in, each conditional on 040 landing first. The review's
  Confirmation passed it with conditions A (Decision 15, the solvers' own tolerance options) and
  B (Decision 5, the patch script's identity, forced add and count check). It changes the build
  recipe and the artifact set (constitution §5.6). It is build-class: it touches `scripts/`,
  `recipes/`, `downloads/SHA256SUMS` and the release workflow (§5.7). Its second milestone is
  spec 038 (Decision 1).
  **Amended 2026-10-18 by spec 043's pre-build review** (`../reviews/043-matplotlib-second-milestone-spec-2026-10-17.md`, finding 1): the shared
  qhull's conditions are written into Decision 7 (a fourth `pkgconf` folder, the configure
  line), Decision 8 (the `PyInit__qhull` rename; "One qhull"), Design and acceptance
  criterion 8. They apply when 043 (matplotlib's second milestone) has landed before this is
  built; the rename applies in either order. Nothing else in this text changed.
- **Owner:** Clay Gendron
- **Kind:** the build recipe (pins; steps 00, 10, 38 (new), 57 (new), 60, 70; `scripts/build.sh`,
  `scripts/wasi-cc`, `scripts/gen_inittab.py`, `scripts/make_stdlib_zip.py`,
  `scripts/assemble_artifacts.py`, six new scripts listed in Design), recipe files (a cross file,
  rename headers, a per-file include map, a C shim file, a stand-in module), two carried patches
  to OpenBLAS, the reactor's `-V` banner, judge additions and changes (`tests/`, including the
  oracle's pins), the release workflow's tree count, `README.md`, `CHANGELOG.md`, `LICENSES/`,
  upstream drafts under `context/upstream/`.
- **Depends on:** 020 (carried patches), 012 (the same bytes from any host), 021, and
  specifications not yet built, each of which lands first (Decision 16): 023 (matplotlib M1: the
  pinned `pkgconf` and pybind11 3.1.0, `-lsetjmp`, `-l`/`-L` lines in `.deps`, `-pthread`
  dropped by `scripts/wasi-cc`, inittab names from install paths, the constructor check, the
  `target_features` check, the recording-platform rule for a golden), 033 (the `ctypes` stand-in
  package, `make_stdlib_zip.py --metadata`), 035 (the zip's directory read once; it changes this
  specification's numbers, not its design) and, if it is confirmed and lands first, 040 (x86_64
  in the same-bytes gate; Decisions 4 and 12). Where one of them lands in another shape than its
  text, this specification uses what landed and says so in its landing notes.
- **Research it stands on:** `../research/2026-10-17-what-scipy-needs.md` and its folder (the
  version, no Fortran in scipy 1.18.1, OpenBLAS 0.3.34 for wasm with five outside fixes, the
  signature clashes, the static-link work, the threads and exceptions findings, the sizes);
  `../research/2026-10-17-openblas-one-return-convention.md` and its folder (the `void`
  convention: 111 clashes to 0, ten LAPACK paths equal to native to about 1e-14, the patch made
  by `scripts/make_void.py`, upstream `develop` merged the same convention in #6008 to #6082
  except `ilaver_`); `../research/2026-10-17-what-else-the-default-profile-carries/outputs/tiers.txt`
  (scipy's Python part: 610 members, 5,573,340 bytes deflated); the owner's decisions 25 and 28 to
  32 (`../decisions.md`); the scipy 1.18.1 sdist, read while drafting in a scratch folder (SHA-256
  `52c4b742…2747307`, equal to PyPI's, EXECUTED), for its `meson.build` files and subprojects;
  the pre-build review's runs (EXECUTED there: Decision 4's make line built as written, the
  link-whole gate at 0, the archive identical without a host Fortran compiler and at another job
  count, the patch regenerated four ways and audited line by line, `target_features`, the import
  list).

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

1. **Two milestones, why the cut is here, and the build in four stages.** scipy's submodules
   import each other when imported: `scipy.linalg` imports `scipy.sparse.linalg` and
   `scipy.special` (`linalg/_matfuncs_inv_ssq.py`, READ); `scipy.optimize` imports HiGHS's
   module; `scipy.stats` imports nearly everything. A milestone that left out a submodule would
   ship a scipy whose own imports fail. So this milestone builds, links and judges **all of scipy
   except `scipy.odr`**. The cut is between "built and working" and "working at the sandbox's
   edges":
   - **037 (this one):** OpenBLAS, scipy, the link, the zip, the goldens, and the checks of
     everything scipy does natively, including three that fail today and are recorded as known
     gaps (Decision 9).
   - **038 (`038-scipy-second-milestone.md`):** it closes those three gaps. They fail only
     because the sandbox has no threads, nothing writable and no libffi: `mmread`/`mmwrite`,
     `qmc.Sobol` with nothing writable, and the `ctypes` values four scipy functions make.

   037 is larger than 023: two new steps, about 85 linked extension modules, six new scripts,
   three gates, three goldens and about fifteen licence files. One builder builds it, **in four
   stages, each green before the next** (the review's plan):
   1. step 38, the patch script and its v1.5 check (Decision 5), and the link-whole gate seen
      failing (111) and passing (0);
   2. step 10's f2py numpy, `scripts/f2py-host`, the cross file, and `meson setup` alone. If
      meson refuses the cross build, the builder stops here and writes a memo: that was the
      research's "kills" test;
   3. `ninja`, the shims, the direct-call gate, the per-file include log;
   4. step 60 (clashes, inittab renames, constructors), step 70, then the checks and goldens.

   AGENTS.md rule 7 applies to each stage: a stage that fails twice stops the specification with
   a memo. It never lands without a submodule, for the reason above.

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
     PyPI's (READ from its JSON while drafting; the review checked them again; checked against
     bytes on download like every pin): `numpy-2.5.2-cp315-cp315-macosx_14_0_arm64.whl`
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
     `cython_lapack` with 3.3.0 cleanly (EXECUTED), which is two modules, not proof. **The
     fallback is a named pin:** if 3.3.0 fails on scipy's sources after two attempts, step 57
     uses Cython 3.2.9's pure-Python wheel,
     `https://files.pythonhosted.org/packages/00/ec/e61deec9bcfbb0e1b36f8b5ba75cb44644419b4bfd0fdd666bffd21d9579/cython-3.2.9-py3-none-any.whl`,
     SHA-256 `a2b0e87f6b80790c929308ca0831d686f7a180feab684fe8cd4a4380bd96aaca` (READ: PyPI's JSON;
     3.2.9 is the newest 3.2 release), for scipy alone. One wheel serves every host; it compiles
     more slowly. It is added to `SHA256SUMS` only if the fallback is taken. If 3.2.9 does not run
     on Python 3.15 either, the fallback is a memo. Two Cythons in one binary are safe: each
     package has its own `_cyutility`.
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
   - **The make line.** It starts from the memo's, and differs from it: `CC` goes through
     `scripts/wasi-cc` (OpenBLAS's `-fPIC` is dropped), `-Wno-return-type` and `NO_CBLAS=0` are
     gone (the second is the default), and `-ffile-prefix-map`, `F_COMPILER` and `NUM_CORES` are
     added. The evidence for this exact line is the review's build (EXECUTED there): no error, the
     memo's seven warning classes and no other (so with `-Wreturn-type` on, no `void` value is
     used), an archive of 10,866,466 bytes, SHA-256 `761a55ed…0305c945`, no builder path in it,
     and the same bytes again with no `gfortran` on `PATH` and 3 make jobs instead of 10. The
     line: `make libs netlib` with `TARGET=WASM128_GENERIC ARCH=wasm OSNAME=WASI NOFORTRAN=1
     C_LAPACK=1 NO_LAPACKE=1 USE_THREAD=0 USE_LOCKING=0 NUM_THREADS=1 NUM_CORES=1
     F_COMPILER=GFORTRAN NO_SHARED=1 NO_AFFINITY=1 DYNAMIC_ARCH=0`, `HOSTCC=cc` (OpenBLAS builds
     its `getarch` tool for the build host; the build hosts already need `cc` for step 20), the
     SDK's `llvm-ar` and `llvm-ranlib`, and `CFLAGS="-O2 -ffile-prefix-map=$HERE=/wasi-python-build
     -D_WASI_EMULATED_SIGNAL -D_WASI_EMULATED_PROCESS_CLOCKS -D_WASI_EMULATED_GETPID
     -D_WASI_EMULATED_MMAN -DNO_SYSV_IPC -include sched.h -DARCH_WASM
     -I$HERE/recipes/openblas-include"`.
   - **The five outside fixes are recipe items** (memo finding 5): `ARCH=wasm` and `-DARCH_WASM`
     (OpenBLAS knows wasm only through `__EMSCRIPTEN__`), `-D_WASI_EMULATED_MMAN` and
     `-DNO_SYSV_IPC` (with `-lwasi-emulated-mman` at the final link; the neutral sysroot has the
     library, EXECUTED by the review), `-include sched.h` (its one WASI call, `sched_yield`, is
     already imported by today's `python.wasm`, EXECUTED by the review), and an empty stand-in
     `recipes/openblas-include/sys/ipc.h` (wasi-libc has none; with `NO_SYSV_IPC` nothing in it is
     used). None is a patch. No new import reaches the guest (§4.4).
   - **Host facts pinned on the make line.** `F_COMPILER=GFORTRAN`: `f_check` picks the first
     Fortran compiler it finds and falls back to `GFORTRAN` when it finds none (`f_check:63-68`,
     READ by the review; EXECUTED: no `gfortran`, same archive). The pin guards against a
     **different** compiler on a host's `PATH`, such as `flang`, which `f_check` would pick and
     which changes the `-DF_INTERFACE_*` flag on every C compile (`Makefile.system:1203`).
     `NUM_CORES=1`: getarch writes the host's core count, which reaches compiles only through
     `NUM_THREADS`; the line pins both. **Once spec 040 has landed** (x86_64 in the same-bytes
     gate), the builder also fixes on the make line every value `getarch` detects on x86_64 that
     reaches a compile flag. OpenBLAS builds `getarch` with `-march=native` on x86_64 hosts
     (`Makefile.system:206-207`, READ), so the builder compares, between an arm64 and an x86_64
     build, `config.h`, `config_kernel.h` and the compile-relevant lines of `Makefile.conf`, and
     sets each differing value explicitly. The x86_64 gate is what proves none is left.
   - **The log.** The step prints `config.h` and the archive's size and SHA-256 into its log.
     `c_check` sets `CROSS_SUFFIX` to the wrapper's folder, so `NM` and `OBJCOPY` name programs
     that do not exist; `libs`, `netlib` and `install` never use them (EXECUTED by the review).
   - **SIMD.** `WASM128_GENERIC` compiles OpenBLAS's kernels with `-msimd128` (GEMM, DOT, ROT,
     SUM and TRSM kernels). wasm SIMD is accepted as a host requirement, in the default build
     (decision 29). It is the only new feature (EXECUTED by the review). Only OpenBLAS is
     compiled with it; numpy, pandas and scipy are not.
   - The step then runs `make install` with the same variables and `PREFIX=$B/openblas-wasi`.
     That installs the archive, `cblas.h`, `f77blas.h`, `openblas_config.h` and OpenBLAS's own
     `lib/pkgconfig/openblas.pc` (EXECUTED by the review), which scipy finds through the pinned
     `pkgconf` (Decision 7).
   - **The link-whole gate.** The step links the archive with `--whole-archive` into a throwaway
     module (`wasm-ld --no-entry --allow-undefined`, as the memo's `scripts/link_whole.sh`) and
     dies on any `signature mismatch` warning, naming the first. The pristine 0.3.34 gives 111
     (EXECUTED by both memos); with the patches it gives 0 (EXECUTED by the review, on this make
     line). It is seen failing first by building without `recipes/patches/OpenBLAS-0.3.34/`.
   - Archive members are added in prerequisite order (`Makefile.tail:80`,
     `lapack-netlib/SRC/Makefile:634`, READ by the review), so the job count cannot reorder them.

5. **Two carried OpenBLAS patches, made by a script in the recipe** (spec 020's mechanism;
   §4.1).
   - **`recipes/patches/OpenBLAS-0.3.34/0001-c-lapack-subroutines-return-void.patch`**: every
     subroutine of C LAPACK returns `void`, as LAPACK's Fortran subroutines do; `xerbla_` gains
     its hidden length in the 20 f2c files that lacked it (rules R1 to R6, memo finding 2). 1,664
     files, 1,119,076 bytes, SHA-256
     `c8f96665197d0d5f3dd10b4f6a8abb0fb8da2000844d4225997e470a2577eaac` (EXECUTED by the review).
   - **`0002-ilaver-returns-void.patch`**: `ilaver_` returns `void`. One file, two hunks, 741
     bytes, SHA-256 `e7a8189b5d7b92a185a6635300b7106350fd36c14f03fe8f8fe272c53eeabd97` (EXECUTED
     by the review). scipy wraps `ilaver` as a subroutine in f2py and in `cython_lapack`;
     upstream `develop` still defines it `int` (memo finding 6).
   - **The script.** `scripts/make_openblas_void_patch.sh` (a recipe file, hashed in
     `MANIFEST`) makes both. It unpacks the pinned tarball into a fresh folder, commits it in a
     git repository run as `apply_patches.sh` runs git (`env -i`, an empty `HOME` and
     `XDG_CONFIG_HOME`, `GIT_CONFIG_NOSYSTEM=1`, `GIT_CONFIG_GLOBAL=/dev/null`, a ceiling), and
     runs `scripts/openblas_make_void.py` on it. **Condition B:** it adds the tree with
     `git add -A --force`, because the tarball's own `.gitignore` hides two of its files
     (`lapack-netlib/TESTING/CMakeLists.txt`, `relapack/test/config.h`; EXECUTED by the review)
     and an edit to an ignored file would otherwise be left out of the patch silently; it commits
     with a fixed identity (`-c user.name=wasi-python -c user.email=build@wasi-python.invalid`),
     since `env -i` and an empty `HOME` leave git none; and it stops, naming both numbers, if
     `openblas_make_void.py`'s "files changed" count differs from the count of
     `git diff --name-only` (1,665 today, EXECUTED by the review). None of these moves today's
     hashes (EXECUTED by the review: the two ignored files are not edited). That is the memo's `make_void.py`, moved into
     `scripts/` unchanged but for its header comment; the memo's copy stays as evidence. The
     script then writes 0001 with plain `git diff -- . ':!lapack-netlib/INSTALL/ilaver.c'` and
     0002 with plain `git diff -- lapack-netlib/INSTALL/ilaver.c`, no other option, and writes
     each draft's `Files:` line from `git diff --name-only`. A cleared configuration matters:
     the review got four different hashes for the same change from `diff.algorithm=histogram`,
     `--full-index`, `diff.noprefix` and the default (EXECUTED).
   - **The audit.** `scripts/audit_openblas_void.py` (adapted from the review's
     `audit_void.py`) pairs every changed line of 0001 with one of the convention's rules and
     fails on any line it cannot pair. The review's run: 2,016 `int` to `void`, 293 `return 0;`
     to `return;`, 56 hidden lengths added, 2 in `xerbla.c`, 0 unexplained (EXECUTED). So the
     review checks the script and its rules, not 26,000 lines, and the audit shows the script
     did only what its rules say.
   - **A v1.5 check, `test_the_openblas_patches_are_what_their_script_makes`**: where the
     pinned tarball is in `downloads/`, it runs the script into a folder under `build/harness`
     and compares both files, byte for byte, with the carried ones, then runs the audit on 0001.
     Seen failing first with a one-line edit to a copy of 0001.
   - **Why two patches.** 0001 is upstream's merged convention, backported by our own script;
     nothing is sent. 0002 is a real pull request to send. When OpenBLAS releases 0.3.35 with the
     convention, 0001 goes and the pin moves; 0002 goes when a release carries it.
   - **Their drafts**, under `context/upstream/patches/OpenBLAS-0.3.34/`, with spec 020's six
     header lines. 0001: `Status: merged https://github.com/OpenMathLib/OpenBLAS/pull/6082`; its
     body names the series (#6008, #6017, #6022, #6030, #6036, #6049, #6061, #6063, #6077, #6079,
     #6080, #6081, #6082), says the patch reaches the same convention by our script and is not
     upstream's diff, and says there is nothing to send. 0002: `Status: drafted`. Its case: ILAVER
     is a SUBROUTINE, and #6008 to #6082 made every other subroutine `void`. Its test: a
     three-line C caller declaring `void ilaver_(int *, int *, int *)`, linked against a wasm
     build of `develop`, gives one `signature mismatch` before the change and none after. The
     builder runs that on `develop` before the draft is offered and records the run in the
     draft. (`develop` linked whole already has 0 clashes, EXECUTED by the memo, so the
     link-whole count is not the test.)
   - **The `Files:` line.** Spec 020's rule makes it name every path. For 0001 that is 1,664
     paths, a line of about 49 KB, written by the script.
   - **Carried in git.** 0001 is text, about 1.1 MB (about 116 KB compressed), under
     `recipes/patches/`, as spec 020 requires; a script that edited the tree at build time
     instead would be an unrecorded source change (§7). It is not an artifact, so §4.6 does not
     exclude it (question 62, decided so).
   - **The WASI portability fixes are not carried.** `__wasi__` beside `__EMSCRIPTEN__` in
     `ctest.c`, `<sched.h>` for WASI in `common.h`, and `<sys/ipc.h>` inside the existing
     `NO_SYSV_IPC` guard in `driver/others/memory.c` all work today as recipe items (Decision 4).
     They are drafted as one courtesy pull request for the owner to send, so the recipe can
     shrink to make variables: `context/upstream/<n>-openblas-wasi-portability/pr.md`, `<n>` the
     next free number at build time.

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
   - **Per-file includes.** Some renames must reach one file only. `?gees_` is renamed only in
     `_flapackmodule.c`: `cython_lapack` calls the same `dgees_` with 15 arguments and must keep
     calling OpenBLAS. The force-included rename does reach f2py's calls (EXECUTED by the review:
     the pasted `F_FUNC` token is rescanned, both in the `extern` declaration and in the address
     f2py's table takes). `scipy.optimize._zeros` (`_zerosmodule.c`) and
     `scipy.optimize.cython_optimize._zeros` (Cython) share the init name `PyInit__zeros`; only
     the second is renamed. So `scripts/wasi-cc` gains one general rule: when
     `WASI_CC_FILE_INCLUDES` names a map file, a compile whose source path ends with an entry's
     suffix gets that entry's `-include <header>`, and the wrapper appends one line to the log
     file `WASI_CC_FILE_INCLUDES_LOG` names. Only step 57 sets either variable, so numpy, pandas,
     OpenBLAS and matplotlib compile byte for byte as before.
   - **The map is rendered into `build/`.** The recipe is `recipes/scipy_file_includes.txt`, its
     header paths written with `@ROOT@` as the cross files are. Step 57 renders it with
     `sed "s#@ROOT@#$HERE#g"` into `build/scipy-build/file-includes.txt`, points
     `WASI_CC_FILE_INCLUDES` at that copy and `WASI_CC_FILE_INCLUDES_LOG` at
     `build/scipy-build/file-includes.log`. Nothing is ever written under `recipes/`, which step
     90 would refuse (`assemble_artifacts.py:142-158`, READ by the review). The map has three
     entries: `_flapackmodule.c` → `recipes/scipy_flapack_rename.h`; `_fblasmodule.c` →
     `recipes/scipy_f2py_weak_api.h`; the `cython_optimize` `_zeros` C file →
     `recipes/scipy_cython_optimize_zeros.h`. `scipy_flapack_rename.h` includes
     `scipy_f2py_weak_api.h`. Step 57 checks the log: each entry matched exactly one compile.
   - **f2py's numpy API pointer, made weak in its two definers only.** `_fblas` and `_flapack`
     both define `_npy_f2py_ARRAY_API` (f2py's `PY_ARRAY_UNIQUE_SYMBOL`), a duplicate symbol in a
     static link (memo finding 7). numpy's own hook settles it: `__multiarray_api.h` writes every
     definition and declaration of the API pointer with `NPY_API_SYMBOL_ATTRIBUTE` (READ, step
     40's generated header). `scipy_f2py_weak_api.h` defines it as
     `__attribute__((weak, visibility("hidden")))`, and the map applies it to `_fblasmodule.c`
     and `_flapackmodule.c` alone. Their two definitions become weak; the linker keeps one.
     `fortranobject.c` (compiled once, in scipy's `_fortranobject` static library) keeps a
     strong `extern` reference, so a missing definition still fails the link rather than
     resolving to 0. Each module's `import_array()` writes the same numpy table into the one
     pointer. scipy's other `PY_ARRAY_UNIQUE_SYMBOL` names are distinct and untouched (READ by
     the review). INFERRED: the static link and the goldens prove it.
   - **The direct-call gate** (memo finding 6: f2py calls LAPACK through a function pointer, so
     a clash there links silently and traps at run time). `scripts/f2py_direct_calls.py`, our
     own (adopted from the memo's `scripts/gen_direct_calls.py`, which this project wrote), reads
     each routine's prototype from the generated `_fblasmodule.c` and `_flapackmodule.c` and
     writes one C file with one direct call per routine. Step 57 compiles it with
     `_flapackmodule.c`'s flags and per-file include, links it with what `_fblas` and `_flapack`
     link (their `.deps`, the g77-ABI wrapper library included), OpenBLAS's archive and the
     shims, and dies on any `signature mismatch` **or undefined symbol**, naming it. With the
     pristine archive it finds 37 mismatches (EXECUTED by the memo); with the patches and shims
     it must find 0.
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
     host-side numpy stand-in that pandas' and scipy's builds import. `scripts/f2py-host` runs
     `"$HOSTPY" -s -m numpy.f2py "$@"` with `PYTHONPATH` set to that folder alone (`-I` would
     ignore `PYTHONPATH`), and keeps `PYTHONHASHSEED=0`, `PYTHONDONTWRITEBYTECODE=1` and
     `SOURCE_DATE_EPOCH` from `scripts/build.sh`. f2py stamps `SOURCE_DATE_EPOCH`, or else the
     clock, into a comment of its output (`numpy/f2py/rules.py:161-168`, READ by the review), so
     the fixed value keeps the generated C the same on every run. Step 57 puts a folder holding
     the wrapper as `f2py` first on `PATH`, because scipy's `tools/generate_f2pymod.py` runs
     `f2py` from `PATH` (READ, line 295). f2py reads the `.pyf` files and writes C; it never runs
     scipy code. Its version is the wasm numpy's, 2.5.2, so the generated modules match
     `fortranobject.c`, which comes from step 40's install (present there, EXECUTED by the
     review).
   - **`recipes/wasi-scipy.cross`**, from the numpy and pandas cross files, with:
     - `[binaries]`: the same compilers, archiver and target Python; `pkg-config` the pinned
       `pkgconf` (023), and `cmake` a program that does not exist, as 023 does, so every
       dependency is found by `pkgconf` on every host;
     - `[properties]`: `numpy-include-dir`, step 40's installed `numpy/_core/include` (scipy
       reads it instead of running the target Python, READ: `scipy/meson.build:56-60`);
     - `c_args`: the pandas set, `-include @ROOT@/recipes/scipy_rename.h`, and the setjmp flags
       `-fwasm-exceptions -mllvm -wasm-enable-sjlj -mllvm -wasm-use-legacy-eh=false` (f2py's
       callbacks, `_zeros`, QUADPACK, SuperLU, qhull and `LowLevelCallable`'s `ccallback.h` use
       setjmp; memo finding 7 and the review);
     - `cpp_args`: the numpy set (standard C++ exceptions), the same include and setjmp flags,
       `-DDUCC0_NO_LOWLEVEL_THREADING` (ducc0's switch, which scipy sets for MinGW;
       `fft/_duccfft/meson.build:8`), `-DHIGHS_NO_DEFAULT_THREADS` (HiGHS then asks for one
       thread and starts `numThreads - 1 = 0` workers; `HighsParallel.h:21`,
       `HighsTaskExecutor.h:121-126`, READ), and `-DBOOST_MATH_PROMOTE_DOUBLE_POLICY=false`
       (below).
   - **`pkgconf` sees exactly three folders.** Step 57 sets both `PKG_CONFIG_PATH` and
     `PKG_CONFIG_LIBDIR` to `build/openblas-wasi/lib/pkgconfig`, step 40's numpy `pkgconfig`
     folder (`dependency('numpy')`) and pybind11's (023). `PKG_CONFIG_LIBDIR` replaces
     `pkgconf`'s default search path, so a host's own `.pc` file (an `openblas.pc` from a Linux
     package) can never be found if one of ours is missing. **When 043 has landed first**
     (Decision 8, "One qhull"; amended 2026-10-18), both variables gain a fourth folder, step
     37's `pkgconfig` folder holding `qhull_r.pc`, and still none of the host's. scipy asks
     `dependency('scipy-openblas', method: 'pkg-config', required: false)` first and finds
     nothing; then `dependency(['openblas', 'OpenBLAS'])` finds ours (READ:
     `scipy/meson.build:287-297`). No BLAS finder from numpy's vendored meson is needed.
   - **The configure line:** the line's meson 1.12.1, `meson setup --cross-file … --buildtype=release
     -Db_ndebug=if-release -D_without-fortran=true -Duse-pythran=false -Dblas=openblas
     -Dlapack=openblas -Duse-system-libraries=none` (`-Duse-system-libraries=qhull` when 043
     has landed first; Decision 8, amended 2026-10-18), then `ninja`. The release build type and
     asserts off are meson-python's defaults, as scipy's wheels are built. No ILP64 (wasm32's
     `int` is LP64's).
   - **Without pythran** (decision 31): five modules fall back to Cython or Python
     (`_group_columns`, `_max_len_seq_inner` and others; memo finding 7).
   - **Boost.Math's default policy without promotion to `long double`.** scipy already fixes
     `promote_double<false>` in its own Boost policies (`SpecialPolicy`, `StatsPolicy`,
     `BetaPolicyForStats`; `special/boost_special_functions.h:17-31, 680-685`, READ by the
     review), so most of its Boost calls never promote. A few use Boost's default policy, which
     does; `betaincc` (`boost::math::ibetac(a, b, x)`, `:194`) is one. On wasm32 a promoted call
     computes in software binary128; on the oracle's platform (macOS arm64) `long double` is
     `double`, so the promotion is a no-op there. `-DBOOST_MATH_PROMOTE_DOUBLE_POLICY=false`
     makes those few default-policy calls compute as the oracle's do. `scipy_numeric.py` prints
     one `betaincc` value, and the landing notes record the fuel of one `special.betaincc` call
     with and without the flag (a rebuild of `scipy.special` alone, measured once, a benchmark
     fact).
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
     `scipy.optimize.cython_optimize._zeros` → `PyInit_scipy_optimize_cython_optimize__zeros`,
     and (amended 2026-10-18) `scipy.spatial._qhull` → `PyInit_scipy_spatial__qhull`, with the
     same entry in `recipes/scipy_rename.h` (a global rename is right: scipy has one `_qhull`).
     matplotlib's second milestone (043) links `matplotlib._qhull`, whose init function is also
     `PyInit__qhull` (`_qhull_wrapper.cpp:299`; scipy's is Cython's from
     `scipy/spatial/meson.build:13`; READ by 043's review). scipy's is renamed in either order,
     because only scipy has the rename machinery; matplotlib keeps upstream's name.
     Its clash check runs on the final names. scipy's `_cyutility` is its own module,
     `scipy._cyutility`, distinct from pandas'. No other scipy name clashes with numpy's or
     pandas' (EXECUTED: the memo's two module lists compared while drafting; one common name,
     `_cyutility`) or with matplotlib M1's (READ: 023's module list).
   - **Clashes.** Step 60's `clashes()` already stops the build on `signature mismatch` and
     `duplicate symbol`. Each one found is fixed by a `scipy_rename.h` entry or a shim, never
     ignored.
   - **Constructors.** 023's check compares the functions `__wasm_call_ctors` calls with a
     reviewed list. Two kinds are new:
     - **OpenBLAS's `gotoblas_init`** (`driver/others/memory.c:3401`, `constructor(101)`, with
       `gotoblas_quit` as a destructor; READ by the review). At `_initialize` it reads the
       `OPENBLAS_*` environment variables. It does not touch Python. On the snapshot it ran at
       build time, so those variables do nothing there; the README says so.
     - **scipy's C++ static initializers** (HiGHS, Boost, pybind11 modules, sparsetools). The
       builder lists each and reads its source: one that touches Python would hang
       `_initialize`, as `ft2font`'s did (023, Decision 3). A grep while drafting found no
       namespace-scope pybind11 object in scipy's C++ (READ).
     The reviewed list grows by exactly the names the build shows, `gotoblas_init` among them
     (a judge change).
   - **OpenBLAS's buffer.** `BUFFER_SIZE` is 16 MiB on wasm (`common_wasm.h:87`, READ by the
     review). The first level-3 call maps it through the emulated `mmap`, which is `malloc`,
     and keeps it. The landing notes record the guest's memory after one `linalg.solve`, against
     the default memory limit's headroom.
   - **One qhull.** scipy compiles its vendored qhull 8.0.2 (`subprojects/qhull_r`), which
     carries scipy's own format-string fix (`subprojects/qhull_r/patches/poly2rc.patch`, a
     security-scanner finding; READ). 023 builds qhull in step 37 but links none of it. So this
     binary has one qhull, scipy's. Whichever of this specification and matplotlib's second
     milestone lands second makes the two share one qhull; a second copy would be a duplicate
     symbol. scipy's vendored `libqhull_r` is qhull 8.0.2's but for one hunk of `poly2_r.c`
     (EXECUTED by 043's drafting and its review, `diff -r`). **If 043 has landed first**
     (amended 2026-10-18, 043's review, finding 1), the shared qhull is step 37's, and this
     specification does all of:
     a. step 37 writes `qhull_r.pc` from a new recipe file, `recipes/qhull_r.pc.in`
        (`Version: 8.0.2`, `Libs: -L${libdir} -lqhull_r`, `Cflags: -I${includedir}` with
        `libqhull_r/` under it), because scipy asks `dependency('qhull_r', version : '8.0.2')`
        (`meson.build:272-281`, READ), which only a `.pc` answers once `cmake` is disabled;
     b. step 57 gains step 37's `pkgconfig` folder as a fourth `pkgconf` folder and configures
        with `-Duse-system-libraries=qhull` (Decision 7);
     c. the `PyInit__qhull` rename (Init names, above; it applies in either order);
     d. it carries scipy's fix as one qhull patch, defined once, with 043's name and header:
        `recipes/patches/qhull-8.0.2/0001-format-strings.patch`, the `poly2_r.c` hunk of
        upstream qhull's pull request 143 (merged as `1b67ec90`, unreleased) made against the
        qhull tarball with no offset, and its draft
        `context/upstream/patches/qhull-8.0.2/0001-format-strings.md` with `Status: merged
        https://github.com/qhull/qhull/pull/143` and `Files: src/libqhull_r/poly2_r.c`;
     e. once the `.pc` exists, matplotlib's own configure may find qhull through `pkgconf`
        instead of `find_library` (INFERRED by 043's review), so the builder checks that
        `_qhull`'s `.deps` still names step 37's archive once, and that 043's `plot_contour`
        job and its triangulation checks still pass on the patched qhull;
     f. acceptance criterion 8: one copy of qhull's functions in `python.wasm`.
     If this lands before 043, scipy keeps its vendored qhull here, and 043 does a, b, d, e
     and f (its Decision 6).

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
   - **`workers=`, stated per function** (corrected after the review's finding 5):
     - **serial, accepted:** `scipy.fft`'s `workers` (and `fftpack`'s through it): ducc0's
       threading is compiled out, so any value runs on one thread and gives the same result;
     - **raise:** `differential_evolution` and `brute` with `workers` other than 1 build a
       `multiprocessing` pool through `MapWrapper` (`_lib/_util.py:584-604`, READ by the review),
       and `cKDTree.query` with `workers` other than 1 starts `threading.Thread`s
       (`spatial/_ckdtree.pyx:1647`; `workers=-1` first reads `os.cpu_count()`, `:400`). Neither
       can work here, as for pandas' process pools. The build records the exact exception each
       raises; the README names the functions, the values and the exceptions, and a v1.3 check
       pins them (Decision 15).
   - **Absent by the platform, documented in the README, not gaps:**
     - `LowLevelCallable.from_ctypes` and any ctypes function pointer: no libffi in wasi-sdk
       (033's rule: making a ctypes function raises `OSError`).
     - `scipy.datasets` downloads: no `pooch`, no network (§4.15).
   - **Known gaps, closed by 038.** Each has its own check in 037's
     `tests/checks/test_v1_3_scipy.py`, which asserts the native behaviour on both binaries with
     nothing writable, and each is a `[[gap]]` in `tests/known_gaps.toml` naming that check, its
     exact finding, and `specifications/038-scipy-second-milestone.md` as its closer:
     - `test_matrix_market_round_trips_in_memory`: `mmwrite` of a sparse and a dense matrix to an
       `io.BytesIO`, then `mmread`, equal. Today: `RuntimeError`, because fast_matrix_market's
       default parallelism (0) starts a thread pool, and `std::thread` throws on WASI (READ:
       `read_body.hpp:477`, `task_thread_pool.hpp:137-142`; the memo's probe, EXECUTED).
     - `test_sobol_needs_nothing_writable`: `qmc.Sobol(d=2, scramble=False).random(4)` equals
       its known values (the first four points of the unscrambled Sobol sequence in two
       dimensions, written in the check). Today: `OSError`, because `_sobol.pyx` loads its
       direction numbers through `importlib.resources.as_file`, which copies to a temporary file
       (READ, lines 147-150).
     - `test_ctypes_values_scipy_makes`: `stats.geninvgauss.cdf`, `stats.genhyperbolic.cdf`,
       `stats.studentized_range.cdf` and `io.arff.loadarff` of a small ARFF text each return
       (the values are checked by 038's golden; here, that they return a finite number or a
       record array). Today: `OSError` from the `ctypes` stand-in: they make a `c_void_p` or
       `c_ulong` instance (READ: `_continuous_distns.py:4144, 5249, 12402`, `_arffread.py:485`).
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
    `getarch` with every host-detected value that reaches a compile set on the make line
    (Decision 4; the review found the archive and `config.h` identical without a host Fortran
    compiler and at another job count, EXECUTED); f2py's output, with `SOURCE_DATE_EPOCH` fixed
    (Decision 7); Cython's, from relative paths; scipy's `__config__.py` (Decision 10).
    - **Before spec 040 lands,** x86_64 Linux stays outside the gate, as today
      (`../research/2026-10-17-x86-64-rebuilds-differ-in-one-function.md`); its rebuild is run
      once and the landing notes say whether its differences grew beyond `npy_cpowl`.
    - **Once 040 has landed,** there is no x86_64 exception: arm64 Linux and x86_64 Linux must
      both give macOS's `SHA256SUMS`. Decision 4's x86_64 rule applies, and the landing notes
      record the x86_64 rebuild's wall time with scipy, under 040's emulated compiler, as a
      benchmark fact. If it nears 040's 360-minute limit, 040's Decision 11 applies before this
      specification lands.

13. **Licences** (§4.12; all approved by decision 25, Qhull and pybind11 also by question 35;
    every `LICENSES_bundled.txt` entry is BSD, MIT, BSL-1.0, the Qhull licence or Apache-2.0
    WITH LLVM-exception, READ by the review). `LICENSES/` gains, each as its project ships it:
    scipy's `LICENSE.txt` and `LICENSES_bundled.txt`; OpenBLAS's `LICENSE` and
    `lapack-netlib/LICENSE`; the licence files of each vendored subproject that is compiled in or
    packed (`boost_math`, `xsf`, `highs`, `duccfft`, `qhull_r`, `unuran`, `array_api_compat`,
    `array_api_extra`, `cobyqa`, `pyprima`); and of fast_matrix_market, its fast_float and ryu,
    SuperLU, ARPACK, PROPACK and uarray inside the scipy tree. The builder lists every
    compiled-in component of `LICENSES_bundled.txt` against a file in `LICENSES/`; ampgo
    (benchmarks only) and Chebfun (Python source with its notice in place) need none beyond
    scipy's own files. `scripts/assemble_artifacts.py` copies them and adds scipy to `PACKAGES`.

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
    - plain `-c pass`: about +16 M fuel if 035 has landed (about 605 members at about 26,700
      fuel each, the slope 035's review measured), or about +47 M if it has not (77,912 per
      member, `tiers.txt`); plus `gotoblas_init`, the C++ static constructors and about 85 more
      inittab entries, which are measured and named, not estimated.
    - snapshot `-c pass`: within 1% (its constructors ran at build time; its directory is
      already read).
    - every existing golden job: no change beyond the plain-start growth above; none imports
      scipy.
    A growth outside these by more than a tenth, or a plain `python.wasm` growth outside 18 to
    28 MB, is a finding for the build review, not a reason to accept.

15. **The checks**, each seen failing first.
    - **A pinned oracle.** `tests/jobs/oracle` gains scipy 1.18.1, pinned to one LAPACK:
      - on macOS arm64, **the `macosx_12_0_arm64` wheel**, which bundles scipy-openblas, by a
        direct-URL dependency with a platform marker
        (`https://files.pythonhosted.org/packages/8c/c5/ba929d7feb9b2332f96827c12e0e924b61973b59b4dea383b603372c65ce/scipy-1.18.1-cp315-cp315-macosx_12_0_arm64.whl`,
        SHA-256 `30f464bee641fa8e282577c7dce027308403213c6ca8270bba73285c91024bc5`, READ: PyPI's
        JSON). Left to itself, uv picks the `macosx_14_0_arm64` wheel on macOS 14 and later, and
        that wheel links Apple's Accelerate (the review, INFERRED from scipy's wheel builds), so
        the oracle's LAPACK would depend on the host's OS version;
      - elsewhere `scipy==1.18.1` (its Linux wheels bundle scipy-openblas).
      `uv.lock` records both. `oracle_env` sets `OPENBLAS_NUM_THREADS=1` and
      `VECLIB_MAXIMUM_THREADS=1`, so the oracle's sums are taken in one order. The oracle's numpy
      wheel is unchanged; with the tolerances below, its BLAS cannot reach a printed digit, and
      the five existing goldens must still reproduce (`regen.py --check`).
    - **The recording platform.** The scipy goldens are recorded on darwin-arm64, and the
      reproduce-under-the-oracle check runs them there only, by 023's rule for its plot job (if
      023 lands without a mechanism for this, a `RECORDED_ON` table in `tests/harness/jobs.py`
      maps each scipy job to `darwin-arm64`). The guest's output must equal the golden on every
      platform: the guest's arithmetic does not depend on its host.
    - **How values are printed.** Each float is printed with **significant** digits,
      `format(float(x) + 0.0, f".{k}g")`, never after an absolute `round`, so a p-value of
      `3e-12` keeps its digits. `k = 9` for direct results; `k = 6` for iterative ones.
      Residuals and errors are printed as a comparison with a stated bound
      (`residual < 1e-12: True`), not as numbers. No iteration counts, function-call counts,
      eigenvector or singular-vector signs, or timings. Every input is fixed in the file or drawn
      from a seeded `numpy.random.Generator(PCG64(…))`.
    - **Tolerances bound the iterative results.** Every solver and integrator is given a
      tolerance at least 1,000 times tighter than its printed precision: `rtol ≤ 1e-9` and
      `atol ≤ 1e-12` for `solve_ivp` and `odeint`; `gtol`, `xtol` and `ftol ≤ 1e-9` for
      `minimize`, `root`, `least_squares` and `curve_fit`; `epsabs ≤ 1e-12` and
      `epsrel ≤ 1e-10` for `quad` and `dblquad`. Then what is printed is bounded by tolerance,
      not by the path a step-size or line-search decision took. **Condition A:** each call sets
      the tolerance options its method actually takes, not only the generic names: `xatol` and
      `fatol` for Nelder-Mead; `ftol` and `gtol` for L-BFGS-B; `ftol` for SLSQP; `xtol` for
      `root` with `hybr`; `gtol` for BFGS; `xtol`, `ftol` and `gtol` for `least_squares` and
      `curve_fit`. Each also raises `maxiter` or `maxfev` far enough that it stops on tolerance,
      not on a cap, and the job prints each result's `success` (a `success: False` would be a
      path-dependent stop, and fails the golden). If a value still differs in its last printed
      digit, the job's input changes, never `k` or a tolerance upward.
    - **Golden jobs (v1.3),** in `JOBS`, their goldens written by `regen.py`:
      - `scipy_numeric.py` (`k = 9`): `linalg` (`solve`, `lu_factor` pivots and `U`'s diagonal,
        `qr`'s `|diag(R)|`, `cholesky`, `det`, an `inv` residual bound, `eigh` and `eigvalsh`
        values, `svdvals`, `expm`, `solve_triangular`); `sparse` (CSR build, product,
        `spsolve` through SuperLU, `eigsh` with a given `v0` and `tol=1e-12` through ARPACK,
        `csgraph.shortest_path` and `connected_components`); `fft` (`fft`, `rfft`, `dct`,
        `fftfreq`, and `fft` with `workers=4` equal to `workers=1`); `special` (`gamma`, `erf`,
        `jv`, `beta`, `betaincc`, `hyp2f1`, `ellipk`, `zeta`); `stats` (`norm.cdf` and `ppf`,
        `t.sf`, `beta.ppf`, `binom.pmf`, `describe`, `ttest_ind`, `pearsonr`, `linregress`,
        `gaussian_kde`); `interpolate` (`CubicSpline`, `make_interp_spline`, `griddata` linear,
        which runs qhull, `RBFInterpolator`); `signal` (`butter`, `lfilter`, `filtfilt`,
        `convolve`, `find_peaks`, `welch`); `ndimage` (`gaussian_filter`, `label`); `spatial`
        (`distance.cdist`, `cKDTree.query`, `ConvexHull.volume`, `Delaunay`'s simplex count);
        `cluster` (`hierarchy.linkage`).
      - `scipy_solvers.py` (`k = 6`, the tolerances above): `optimize` (`minimize` on Rosenbrock
        with BFGS, Nelder-Mead, L-BFGS-B and SLSQP with a constraint; `root` with `hybr`;
        `least_squares`; `curve_fit`; `brentq`; `linprog` and `milp` through HiGHS;
        `linear_sum_assignment`); `integrate` (`quad`, `dblquad`, `solve_ivp` with RK45 and
        BDF, `odeint`, `simpson`).
      - `scipy_lapack.py` (`k = 9`): every routine the memo found trapping, through
        `get_lapack_funcs` in all four precisions: `gesv`, `getrf`, `getrs`, `laswp`, `lauum`,
        `potrf`, `trtri`, `trtrs`; `gees` with a sort callback (`schur(…, sort="lhp")`, its
        eigenvalues as a sorted set and `sdim`); and `eig`, `svd`, `lstsq`, `pinv` and
        `qr_update` (through `cython_lapack`). **`ilaver()`** is printed only as "three integers,
        major 3": the guest's LAPACK is 3.12.0 (`ilaver.c:332-334`) and the oracle's may differ,
        so its numbers would compare two releases, not the call.
      Seen failing first: each fails on the current set (`ModuleNotFoundError: No module named
      'scipy'`); `scipy_lapack.py` also traps on a build with the OpenBLAS patches removed, which
      the builder runs once (Acceptance, criterion 1).
    - **Behaviour that must reach Python (v1.3,** `tests/checks/test_v1_3_scipy.py`, each on both
      binaries with nothing writable):
      - `linalg.solve` of a singular matrix raises `LinAlgError`;
      - `ConvexHull` of collinear points raises `QhullError` (qhull's `longjmp`, and scipy's
        message stream, which uses wasi-libc's `open_memstream`, present, EXECUTED by the
        review; if meson finds no `open_memstream` the stream falls back to `tempfile`, and this
        check fails);
      - `optimize.brentq` and `integrate.quad` with a Python function that raises `ValueError`
        re-raise it (the `setjmp` paths in `_zeros` and QUADPACK);
      - `linprog` of an infeasible problem returns `status == 2` (HiGHS ran with one thread);
      - `workers`: `fft.fft(x, workers=4)` equals `workers=1`; `differential_evolution(…,
        workers=2)` and `cKDTree.query(…, workers=2)` each raise the exception the build
        recorded, inside the call's fuel limit (they must not hang);
      - `import scipy.odr` raises `ImportError` whose message names "Fortran";
      - `python -V` names `scipy.odr` among the missing;
      - the three gap checks of Decision 9, failing today as their `[[gap]]` entries record.
    - **Rules and artifact checks (judge changes, under `--accept-judge`):**
      - v1.1: `python.wasm`'s `target_features` list gains `simd128` (decision 29); any other
        new feature still fails it.
      - v1.1: 023's constructor list gains `gotoblas_init` and the reviewed scipy names
        (Decision 8).
      - v1.5: `SOURCE_PATTERNS` and `needs.SOURCE_COMPONENTS` gain OpenBLAS and scipy; the
        release workflow's tree count rises by two; the patched-tree check covers OpenBLAS's
        two patches; `test_the_openblas_patches_are_what_their_script_makes` (Decision 5).
      - rules: `scan.cpp_exception_errors` judges `recipes/wasi-scipy.cross`; spec 020's
        `patch_errors` passes on the two patches and drafts.
      - `tests/known_gaps.toml`: the three gaps of Decision 9, each with its check and exact
        finding.
    - **Build-time gates, not judge checks:** step 38's link-whole gate (Decision 4); step 57's
      direct-call gate and per-file include log (Decision 6); step 60's clash detector.
    - **Unit checks** (no artifacts), each seen failing before its code exists:
      - `scripts/f2py_direct_calls.py` on a small generated module text;
      - `scripts/install_from_plan.py` on a small install plan (tags `tests` and extension
        modules skipped, destinations kept);
      - `scripts/gen_inittab.py`'s rename table, and its clash check on the renamed names;
      - `scripts/wasi-cc`'s per-file include: a matching path gets the header and a log line;
        and, **with the variable unset, the argv the wrapper executes is identical to today's**
        for a set of numpy-, pandas- and OpenBLAS-shaped command lines;
      - `scripts/audit_openblas_void.py` on small hand-made diffs: a line of each rule is paired;
        a line of none is named.

16. **Ordering with other build-class work** (§5.7: one build-class specification in flight, one
    landing at a time).
    - The queue ahead of this one, by the roadmap and by 035's Decision 12: 028 (milestone 1),
      033, 035, 023, and 040 if it is confirmed (its Decision 12 places it before 037).
      **037 builds after 023 lands**, because it uses 023's pins and link machinery (Depends
      on). If 040 has not landed when 037 starts, 037 builds under Decision 12's "before 040"
      rule, and 040's builder then gates scipy's objects (040, Decision 12).
    - **038 builds right after 037.**
    - **Tier A (spec 039)** is queued after 038, but nothing in it depends on scipy (039,
      Decision 14). If 037 or 038 stalls, 039 may build first. Whichever of 037 and 039 builds
      second rebases onto the other's step 70, `00_download.sh` and `assemble_artifacts.py`, and
      adds its packages to the metadata set. scikit-learn and statsmodels (decision 48) come
      after 038.
    - matplotlib's second milestone is not yet specified; Decision 8's qhull rule covers either
      order.
    - Files 037 shares with others: step 60 and `gen_inittab.py` (023, 035), step 70 and
      `make_stdlib_zip.py` (023, 033, 039), `scripts/wasi-cc` (023), step 10 and
      `scripts/line.conf` (040). Each is rebased onto main as it is when 037's builder starts.

## Intent

An agent's code solves, fits, tests, filters and integrates with scipy inside the same sealed
Python, and gets native scipy's answers, with no Fortran compiler anywhere and only recorded,
temporary changes to OpenBLAS.

## Design

| file | change |
|---|---|
| `downloads/SHA256SUMS`, `scripts/00_download.sh`, `scripts/line.conf` | the scipy sdist, the OpenBLAS tarball, three numpy host wheels (`*_NUMPY_HOST_WHEEL`) (Decision 2) |
| `scripts/steps/10_tools.sh` | the host numpy wheel into `build/tools/f2py-numpy` (Decision 7) |
| `scripts/f2py-host` | new: `python -s -m numpy.f2py` with only that folder on the path (Decision 7) |
| `scripts/steps/38_openblas.sh` | new: unpack, patch, copy, make, install, the log, the link-whole gate (Decision 4) |
| `recipes/openblas-include/sys/ipc.h` | new: the empty stand-in header |
| `scripts/make_openblas_void_patch.sh`, `scripts/openblas_make_void.py`, `scripts/audit_openblas_void.py` | new: the patches' maker, the convention's script (moved from the memo's folder), the audit (Decision 5) |
| `recipes/patches/OpenBLAS-0.3.34/0001-c-lapack-subroutines-return-void.patch`, `0002-ilaver-returns-void.patch` | new (Decision 5) |
| `context/upstream/patches/OpenBLAS-0.3.34/0001-…md`, `0002-…md` | their drafts |
| `context/upstream/<n>-openblas-wasi-portability/pr.md`, `context/upstream/<n>-scipy-c-lapack-signatures/pr.md`, `context/upstream/README.md` | courtesy drafts and their rows (Decisions 5, 6) |
| `scripts/steps/57_scipy.sh` | new: render the map, configure, build, shims, gates, the package (Decision 7) |
| `recipes/wasi-scipy.cross` | new (Decision 7) |
| `recipes/scipy_rename.h`, `recipes/scipy_flapack_rename.h`, `recipes/scipy_f2py_weak_api.h`, `recipes/scipy_cython_optimize_zeros.h`, `recipes/scipy_file_includes.txt`, `recipes/scipy_lapack_shims.c` | new (Decision 6) |
| `scripts/wasi-cc` | the per-file include rule and its log (Decision 6) |
| `scripts/f2py_direct_calls.py`, `scripts/install_from_plan.py` | new (Decisions 6, 7) |
| `scripts/gen_inittab.py`, `scripts/steps/60_link.sh` | scipy's modules, the rename table, the new archives and `-lwasi-emulated-mman` (Decision 8) |
| **When 043 has landed first** (amended 2026-10-18): `recipes/qhull_r.pc.in`, `scripts/steps/37_plot_libs.sh`, `recipes/patches/qhull-8.0.2/0001-format-strings.patch`, `context/upstream/patches/qhull-8.0.2/0001-format-strings.md` | one qhull, conditions a to f (Decision 8) |
| `recipes/scipy_odr_stand_in.py`, `recipes/reactor_bootstrap.py` | the `scipy.odr` stand-in; the banner (Decision 9) |
| `scripts/steps/70_zip.sh`, `scripts/make_stdlib_zip.py` | the scipy tree, its metadata, the stand-in, `scipy/__config__.py` made host-neutral (Decision 10) |
| `scripts/build.sh`, `scripts/assemble_artifacts.py`, `LICENSES/` | steps 38 and 57 in `ALL`; licences; `PACKAGES` (Decision 13) |
| `tests/jobs/scipy_numeric.py`, `scipy_solvers.py`, `scipy_lapack.py` and their `.expected`; `tests/jobs/oracle/pyproject.toml`, `uv.lock`; `JOBS`, `oracle_env` and the recording platform in `tests/harness/jobs.py` | the goldens and the pinned oracle (Decision 15) |
| `tests/checks/test_v1_3_scipy.py` | new: the behaviour checks and the three gap checks |
| `tests/checks/test_v1_5_rebuild_from_pins.py` | the patches-from-their-script check |
| `tests/checks/test_v1_1_artifact_set.py` (or 023's file), `tests/harness/pins.py`, `tests/harness/needs.py`, `tests/harness/scan.py`, `tests/known_gaps.toml` | the other judge changes (Decision 15) |
| `tests/unit/…` | the unit checks (Decision 15) |
| `.github/workflows/…` | the tree count, two more |
| `README.md`, `CHANGELOG.md` | scipy in the profile; the absences, the `workers` facts and the gaps; `OPENBLAS_*` on the snapshot; SIMD as a host requirement; the patches by path |

## Scope

In: Decisions 1 to 16. Out:

- **038's fixes for the three gaps** (Decision 9). Their checks are here.
- **pythran** (decision 31). A later specification may pin it and its three dependencies and
  measure what the five modules gain.
- **Pre-importing scipy in the snapshot** (question 61).
- **ILP64** BLAS, and a non-SIMD OpenBLAS target.
- **A Fortran compiler**, and with it `scipy.odr`. The memo's advice stands: re-check upstream
  LLVM's flang for wasm at each LLVM release.
- **matplotlib's `_qhull`** (its second milestone); Decision 8 says only how the two share qhull.
- **scipy's own test suite under the runtime** (roadmap milestone 6, hardening).

## Acceptance criteria

1. The checks exist and were seen failing first: the goldens and the behaviour checks on the
   current set; `scipy_lapack.py` trapping on a build without the OpenBLAS patches; the
   link-whole gate failing with 111 and the direct-call gate with 37 on that build; the
   patches-from-their-script check on an edited copy; the unit checks before their code. The
   three gap checks fail on the finished set exactly as their `[[gap]]` entries record.
2. The build went through Decision 1's four stages, each green before the next. A full build
   from pins in a clean clone applies both OpenBLAS patches with no offset, builds steps 38 and
   57, passes every gate, and makes a set whose binaries run the three goldens and the behaviour
   checks. `MANIFEST` names every new pin, recipe, script and patch.
3. The same-bytes rebuild on arm64 Linux gives the same `SHA256SUMS` as macOS, with no
   exception (spec 012). **Once 040 has landed,** the x86_64 Linux rebuild gives them too, with
   no exception; **before,** it is run once and reported (Decision 12). If a difference cannot be
   fixed after two attempts, the build stops and a memo records it (AGENTS.md rule 7); it does
   not land with an exception.
4. The reviewer runs `scripts/make_openblas_void_patch.sh` on a fresh unpack of the pinned
   tarball and gets 0001 = `c8f96665197d0d5f3dd10b4f6a8abb0fb8da2000844d4225997e470a2577eaac`
   and 0002 = `e7a8189b5d7b92a185a6635300b7106350fd36c14f03fe8f8fe272c53eeabd97`, whatever the
   reviewer's own git configuration; `scripts/audit_openblas_void.py` reports 0 unexplained
   lines in 0001.
5. The landing notes record, each measured: the three binaries' and the zip's bytes, the zip's
   member count, the number of scipy modules linked, the new constructors by name
   (`gotoblas_init` among them), plain and snapshot `-c pass` fuel, the fuel of `import scipy`,
   `import scipy.linalg`, `import scipy.stats` and `import scipy.optimize` on both binaries, the
   snapshot's bytes and `-c pass` fuel if it pre-imported `scipy.stats` (for question 61), the
   guest's memory after one `linalg.solve`, the fuel of `special.betaincc` with and without the
   Boost flag (Decision 7), the exceptions the `workers` cases raise, and, once 040 has landed,
   the x86_64 rebuild's wall time. Each bound of Decision 14 holds or is a finding.
6. `uv run pytest` is green with `--accept-judge` and `--accept-growth`, each reason stated.
7. A release dry run passes every job. The build and rebuild jobs' step times (their limit is
   120 minutes on 3- and 4-core runners) are recorded as benchmark facts in the landing notes.
8. **When 043 has landed first** (amended 2026-10-18): `llvm-nm` on the unstripped link finds
   each of qhull's functions (`qh_new_qhull` among them) defined once in `python.wasm`;
   condition e's checks pass; and the `QhullError` check and the spatial goldens pass on the
   shared qhull.

## The owner's choices

None open here. Two are recorded in `../questions-for-the-owner.md`, each decided here as written
so nothing waits: **61**, whether the default snapshot pre-imports scipy (decided: no, until the
build's numbers are in; Decision 11); **62**, whether a 1.1 MB carried patch may live in git
(decided: yes; Decision 5). The pre-build review agreed with both.

## Revised at build (2026-10-19)

Written by the builder, before its build review. Main had moved since the confirmation: 023, 040,
059, 057, 046, 047, 055, 069, 071, 062 and 051 landed; 043 and 063 had not. Each item says what
changed and why; each is small and none changes a decision's purpose. The reviewer checks each.

1. **What landed first, taken as the Depends on line allows.** 023's pkgconf, pybind11 3.1.0,
   `.deps` lines and install-path inittab names are used as landed. 040 and 059 landed: x86_64
   Linux builds natively with `-ffp-contract=off` and is in the same-bytes gate with no
   exception, so Decision 12's "once 040 has landed" branch applies. Decision 4's x86_64 rule
   was run (EXECUTED, the landing notes): OpenBLAS's prebuild with step 38's variables writes
   the same `config.h` on macOS arm64, Linux arm64 and Linux x86_64 (`config_kernel.h` is not
   written for this target), and its `Makefile.conf` differs only in link-only lines (the
   wrapper's folder, `CEXTRALIB`'s paths, `FC`, `FEXTRALIB`, `NOFORTRAN`); no value needed
   pinning. 043 has not landed: scipy keeps its vendored qhull (Decision 8's last sentence); the
   `PyInit__qhull` rename is made anyway. 069 landed (decision 34): no package is pre-imported,
   so Decision 11 holds by rule, question 61 is answered by decision 34, and criterion 5's
   "snapshot if it pre-imported `scipy.stats`" is not measured. 071 landed during the build; the
   branch was rebased onto it and rebuilt.
2. **Patch 0001 is two files; ilaver's is 0003.** The convention's one diff is 1,119,076 bytes,
   over the rules check's 1 MiB for a tracked file (`test_no_artifact_or_large_file_is_tracked`).
   `scripts/make_openblas_void_patch.sh` cuts that one `git diff` at the first file at or after
   `lapack-netlib/SRC/s`: `0001-c-lapack-subroutines-return-void-1-of-2.patch` (581,415 bytes,
   841 files, `a88c863b…`) and `0002-…-2-of-2.patch` (537,661 bytes, 823 files, `fd8777b7…`);
   concatenated they are byte for byte the confirmed 0001, `c8f96665…`. `0003-ilaver-returns-void.patch`
   is the confirmed 0002, `e7a8189b…`. Criterion 4 reads: the script gives these three files,
   the first two concatenated `c8f96665…`, the third `e7a8189b…`.
3. **The convention's script runs R4 and R5 as functions** (`scripts/openblas_make_void.py`), so
   that no module-level name is bound twice (`test_no_module_level_name_is_bound_twice`); the
   patches it makes are unchanged (EXECUTED: `cmp`).
4. **The audit's counts.** 2,004 `int`→`void` pairs and 12 lines git's diff removes and adds back
   unchanged (blank lines inside a run) make the review's 2,016; 293 `return 0;`→`return;`; 56
   hidden lengths (20 prototypes, four of them broken over two lines, and 36 calls); 2 in
   `xerbla.c`; 0 unexplained. 0003 adds one of each of the first two rules.
5. **f2py runs with `-s -P`** (`scripts/f2py-host`): meson runs it from a scipy source folder,
   where `scipy/signal` hid the stdlib's `signal` from f2py's own `import subprocess` (EXECUTED,
   the first `meson setup`).
6. **Step 57's inputs.** A copy of step 40's numpy stand-in with numpy.random's `.pxd` files
   beside it (stats._unuran cimports numpy.random); ninja builds only the installed targets not
   tagged `tests` (`install_from_plan.py --targets`: `special._test_internal` uses the FPU's
   rounding modes, which WASI lacks); `scripts/wasi-cc` expands a response file (`@file`, which
   meson wrote for stats._unuran's link), untouched for a command with none. 95 extension modules
   are linked (Decision 8's "about 85").
7. **More of scipy's side of the ABI than the memo's six, each a recipe** (Decision 6's rule,
   "fixed by a `scipy_rename.h` entry or a shim, never ignored"; each found by step 60's clash
   detector):
   - scipy.special: xsf defines about forty functions in headers without `inline` (453 others
     have it), and five modules compile them, so `recipes/scipy_special_xsf.h` makes xsf's
     `XSF_HOST_DEVICE` say `inline` in those files; `xsf::numpy`, `xsf::numbers`,
     `xsf::struve_h`, `struve_l` and `wrap_PyUFunc_getfperr`, defined in headers outside that
     macro (and the last by five Cython modules too), are renamed per module
     (`recipes/scipy_special_{special_ufuncs,gufuncs,ufuncs_cxx,ellip_harm_2,cython_special}.h`);
   - stats' vendored numpy.random distributions (`random_standard_uniform` and three more), SuperLU's
     `c_abs` and Cython's `__pyx_module_is_main__cyutility`: entries in `recipes/scipy_rename.h`;
   - linalg._batched_linalg declares `?getrf` and `?getri` returning `int`, and optimize._trlib
     passes `dlagtm` a hidden length: shims (`wasi_scipy_int_?getrf_`, `?getri_`,
     `wasi_scipy_dlagtm_`) and two per-file headers;
   - numpy's own f2c LAPACK and BLAS (`lapack_lite`, numpy being built with no BLAS) define 479
     of OpenBLAS's names with `int` returns: `recipes/wasi-numpy.cross` gives numpy
     `-DBLAS_SYMBOL_PREFIX=numpy_lapack_lite_`, the hook its `lapack_lite_names.h` exists for.
     numpy's archives change; its arithmetic does not (its goldens and own test groups pass).
   The per-file map gained a third column, a count, because `xsf_wrappers.cpp` is compiled into
   two modules; the log check holds each entry to its count.
8. **SuperLU takes the GIL back** (`recipes/scipy_superlu_gil.h`, per file): its calls release
   the GIL with CPython's `PyEval_SaveThread` and its memory hooks reacquire it with numpy's
   `NPY_ALLOW_C_API`, which is empty in a numpy built without threads (`NPY_NO_SMP`); every
   `spsolve` aborted (EXECUTED). The header gives `_superlu_utils.c` numpy's threaded
   definitions of the three macros.
9. **The `ctypes` stand-in, two narrow additions** (spec 033's `_types.py` and `__init__.py`):
   `import scipy` runs `_lib._ccallback_c`, which casts the addresses of its own test callbacks
   to `CFUNCTYPE` types at import, and every `integrate.quad` asks for `ctypes._CFuncPtr`. So
   `cast(int_or_None, F)` with `F` a function type gives an `F` that holds the integer and raises
   `OSError` when called, and `ctypes._CFuncPtr` names the function types' base. Every other cast
   and every other instance still raises; no foreign call can be made, and `-V` keeps "no ctypes".
   Spec 038's Decision 3 ("any other cast raises") is amended to keep these (a dated line there).
10. **One carried scipy patch in 037**, as spec 051's binding status line requires: the callback
    scan found five uarray callbacks with fewer parameters than CPython passes
    (`recipes/patches/scipy-1.18.1/0001-uarray-callback-signatures.patch`, its facts sheet under
    `context/upstream/patches/scipy-1.18.1/`; scipy `main` has the same lines). Spec 038's two
    patches become `0002-…` and `0003-…` (a dated line there).
11. **freopen is refused in the reactor** (`recipes/freopen_refusal.c`, `-Wl,--wrap=freopen`, as
    046's iconv guard is linked): its one caller is qhull's `TO <file>` option, and wasi-libc's
    freopen is the only user of `fd_renumber`, a WASI call the runner's descriptor shadows (spec
    068) do not cover; without the refusal `python.wasm` gained that import
    (`test_every_descriptor_import_is_shadowed`). `TO` now fails as an unopenable file does.
12. **Printing in `scipy_lapack.py`.** Single precisions print 5 significant digits, double 9
    (float32 holds about 7, and its last bits follow the order of a sum); a real eigenvalue's
    imaginary part below 1e-4 of its size prints as 0, a stated bound; the Schur input was shifted
    once (`-0.5` on the diagonal) when `cgees`'s real part `-0.0230225` sat on a fifth-digit
    boundary, as Decision 15 says (the input changes, never `k`).
13. **What the `workers` cases raise** (Decision 9, recorded by the build): `differential_evolution`
    and `brute` raise `AttributeError` (the pool's queue needs `os.pipe`), `cKDTree.query` raises
    `RuntimeError` ("can't start new thread").
14. **The Sobol gap is a silent zero, not an `OSError`.** `_sobol.pyx` swallows the temporary-file
    error in a `noexcept` function ("Exception ignored") and every point is 0. The gap records that,
    and the README warns of it until spec 038.
15. **How the checks run.** The behaviour checks run through `wasi_python.run` with no root and
    no grant, so nothing is writable, as an embedder runs it; the gap checks report each item as
    a finding with its digest, as `known_gaps.toml` requires. scipy's dotted builtins have their
    own check and budget (the existing check's comment asks for a split per package), with a table
    of the two names native scipy itself gives differently (`uarray._uarray`; a circular import
    of `_matfuncs_sqrtm_triu` imported first). The licence check takes a source tarball before a
    wheel of the same version (numpy's host wheel is a build tool). The build-progress unit
    checks count the steps instead of fixing sixteen.
16. **scipy's own test suite is `later`, closer spec 066**, when 063's `packages.toml` reaches this
    branch: scipy `later` (reason: its suite, larger than numpy's, is roadmap milestone 6 and this
    milestone's Scope leaves it out; its first gaps close in 038), OpenBLAS `via scipy`. scipy
    gets no suite group now: the judge's upstream kit has never run it, and fitting its groups to
    the release shards' budgets is a specification's work, not a builder's.
17. **Step 38 runs `make libs` and then `make netlib`**, not Decision 4's `make libs netlib`: given
    both goals at once, GNU make 4 (the Linux hosts') runs them in parallel and both `ar -ru` the
    one archive, which lost 20 members on the first linux/arm64 build (EXECUTED: `cgetrs_*_single.o`,
    `?laswp_plus.o` and others missing; step 57's direct-call gate stopped on their undefined
    symbols). macOS's make had run them in turn: its archive is byte for byte the same either way
    (`0a58aa19…`, EXECUTED).
18. **Step 57 sets `GIT_CEILING_DIRECTORIES` to `build/`**: HiGHS's meson stamps `git describe`
    into `HIGHS_GITHASH` (`vcs_tag`), which from a checkout of this repository named its commit
    and dirty state (`v0.1.0a6-88-g662ec7f` in the linux/arm64 clone), so `python.wasm`'s data
    depended on where and when it was built. With the ceiling git finds no repository and the tag
    is meson's fallback, `unknown`, on every host (EXECUTED: `HConfig.h`). Decision 12's "f2py's
    output, Cython's, `__config__.py`" list of host-side inputs gains this one.
19. **ducc0's C++ (`scipy/fft/_duccfft/pyduccfft.cxx`) is compiled at `-Os`**, through the
    per-file map, whose second field may now be a flag (`scripts/wasi-cc` appends it after the
    compile's own, so the last `-O` wins). At `-O3`, `-O2` and `-O1` the pinned clang (wasi-sdk
    33, LLVM `4434dabb`) orders the `try_table` blocks of ducc0's `make_pass` functions
    differently on every run: eight compiles of the file on one host gave eight objects; at
    `-Os` eight gave one (EXECUTED). It is the only one of scipy's 910 compiles that differed
    between two compiles (each compiled twice, EXECUTED), and it was the last difference between
    the macOS and linux/arm64 sets (eight functions). A compiler fault, not a host fact: an issue
    text is drafted (`context/upstream/23-llvm-wasm-try-table-order/issue.md`). `scipy.fft` may
    run somewhat slower than at `-O3` (not measured).
20. **python.wasm grew more than Decision 14 expected** (the landing notes give each figure):
    a finding for the build review, as Decision 14 says.

## Landing notes

Built 2026-10-19 by a builder agent (Claude Opus 5.5) in the worktree `wasi_python-037`, branch
`spec/037-scipy`, from main `d900dd9`, rebased onto main `23f1c4f` (071 landed) and rebuilt from an
empty `build/`. The machine: Apple arm64, macOS 26.5, 10 cores; Docker with the research images
`wp040-arm64` and `wp040-amd64`. Every claim is EXECUTED unless labelled. Evidence is under the
worktree's git-ignored `build/037/`. Not yet reviewed: the build review is next, then the lane.

### Commits

- `febbeff` the checks first; `3aa0d5b` the build; `662ec7f` step 38's two makes, `2687418`
  step 57's git ceiling and the next commit ducc0 at `-Os` (Revised at build, items 17 to 19,
  each found by a linux/arm64 build that differed from macOS's);
  the commit carrying these notes, the README and the spec's revision.

### The four stages (Decision 1, criterion 2)

1. **Step 38.** The pristine archive linked whole: 111 signature mismatches, the first `zlascl_`
   (`build/037/seen-failing-38-unpatched.log`); with the three patches 0. The patches apply with
   no offset. `libopenblas.a` 10,874,882 bytes, `0a58aa19…`; the memo's seven warning classes and
   no other (19,998 `-Wunused-function` … 16 `-Wincompatible-pointer-types-discards-qualifiers`).
   The patch script regenerates all three byte for byte; the audit finds 0 unexplained lines.
   The v1.5 check was seen failing on a copy of 0001 with one added line edited (`+void` to
   `+int`: "the carried patch is not what the script makes").
2. **meson setup** accepted the cross build at the second attempt (the first stopped at `f2py -v`:
   item 5 of Revised at build). scipy found `openblas` 0.3.34 through the pinned pkgconf
   (`scipy-openblas`: not found), numpy 2.5.2, pybind11 3.1.0 and `open_memstream`.
3. **ninja, the shims, the gates.** 95 extension archives, 249 compiler warnings; each per-file
   include matched its count (`_flapackmodule.c`, `_fblasmodule.c`, `/_zeros.c`,
   `_special_ufuncs.cpp`, `_gufuncs.cpp`, `/_ufuncs_cxx.cpp`, `xsf_wrappers.cpp` twice,
   `/_ellip_harm_2.c`, `/cython_special.c`, `_batched_linalg_module.cc`, `/trlib_tri_factor.c`,
   `/_superlu_utils.c`); the direct-call gate calls 621 routines with 0 mismatches and no
   undefined symbol. Against the pristine archive the same gate finds 57 mismatches
   (`build/037/seen-failing-direct-calls-unpatched.log`; the memo counted 37 on its own probe).
4. **Step 60** stopped four times before it linked, each a finding fixed by a recipe (Revised at
   build, items 7 and 11): 65 duplicate symbols in scipy.special and against numpy's copies,
   479 then 10 signature mismatches (numpy's lapack_lite; scipy's own declarations), 146 new
   constructors, and the `fd_renumber` import. Then steps 70 to 90.

A python.wasm relinked from this build with the pristine archive (scratch, past the clash
detector, which would stop on its 75 mismatches) traps in `scipy_lapack.py` after its first line
("uninitialized element"; `build/037/seen-failing-scipy-lapack-unpatched.txt`).

### Seen failing first (criterion 1)

On main's frozen set `s-1a7242a7` (069's): every check of `test_v1_3_scipy.py`, both scipy
dotted-builtin checks, the licence, metadata and constructor checks, 31 failed, 0 passed
(`build/037/seen-failing-checks.log`); the guest said `ModuleNotFoundError: No module named
'scipy'`. The unit checks of the new scripts failed to import in a clone of main with only the
new test file (`ModuleNotFoundError: No module named 'audit_openblas_void'`). On the finished
set the three gap checks fail as their `[[gap]]` entries record (6 xfailed).

### The constructors (Decision 8)

146 new, by name in `tests/harness/constructors.py`: `gotoblas_init`, wasm-ld's
`.Lregister_call_dtors`, uarray's, fast_matrix_market's six, HiGHS's (each of its C++ files: its
string constants), stats._qmc_cy's, and twelve `__cxx_global_var_init.7` to `.12` from xsf in
special._gufuncs and special._special_ufuncs. Each one's direct-call graph was walked in the
unstripped link (a scratch tool over `llvm-objdump -d`): 270 functions reached in all, none of
CPython's (no name starting `Py` or `_Py`); the only indirect calls are in `operator new` (the new
handler), `std::__terminate` (the terminate handler) and stdio's `fwrite`, `fflush`,
`__overflow`, `vfprintf` (FILE's write function). The reached set is libc++'s strings, maps and
hash tables, `__cxa_atexit`, `malloc`, the exception and abort path, `getenv` and `atoi`.
`target_features` gains exactly `+simd128`.

### The x86_64 rule (Decision 4) and the same bytes (Decision 12, criterion 3)

OpenBLAS's prebuild with step 38's variables (`build/037/getarch/`): `config.h` identical on macOS
arm64, linux/arm64 and linux/amd64 (emulated); `Makefile.conf` differs only in link-only lines.
No value needed pinning. The x86_64 rebuild itself is the release dry run's (the lane's).

LINUX_RESULT

### The numbers (Decision 14, criterion 5)

| | main `23f1c4f` (`s-c50ca51f`) | this set |
|---|---:|---:|
| `python.wasm` | 41,099,661 | 84,182,825 (+43,083,164, +104.8%) |
| `python-snapshot.wasm` | 44,633,983 | 87,966,107 (+43,332,124) |
| `python-stdlib.zip` | 22,197,173, 2,421 members | 27,854,941, 3,029 members (+5,657,768, +608) |
| wheel (question 64) | 43,749,018 | 65,702,780 (+21,953,762) |
| plain `-c pass` | 167,481,449 | 185,170,438 (+17,688,989, +10.6%) |
| snapshot `-c pass` | 15,631,800 | 17,126,241 (+1,494,441, +9.6%) |
| plain / snapshot `os._exit(0)` | 139,087,456 / 967,649 | 155,539,560 / 988,971 |
| plain / snapshot `import scipy` | | 1,380,857,267 / 1,090,726,590 |
| plain / snapshot `import scipy.linalg` | | 2,954,317,407 / 2,629,804,646 |
| plain / snapshot `import scipy.stats` | | 9,005,338,958 / 8,668,973,776 |
| plain / snapshot `import scipy.optimize` | | 4,688,873,085 / 4,362,575,402 |
| linear memory after `pass` / after one 200×200 `linalg.solve` (plain) | | 41,943,040 / 66,781,184 |
| `special.betaincc(2.5, 3.5, 0.3)`, with / without `-DBOOST_MATH_PROMOTE_DOUBLE_POLICY=false` | | 636,132 / 1,127,190 (both print `0.703247011`; each figure includes one `print`) |

- **Against Decision 14's bounds.** The zip is inside (+608 members, +5.66 MB). `python.wasm`'s
  +43.1 MB is outside 18 to 28 MB, **a finding for the build review**: the code section grew
  29.3 MB (scipy's archives 24.1 MB of code, OpenBLAS's 5.2 MB, by the link map), the `name`
  section 10.6 MB (C++'s long mangled names: HiGHS, Boost, xsf, pybind11), data 3.0 MB. The
  estimate came from Pyodide's `.so` files, which (INFERRED) are optimized for size and carry
  no name section. Plain start grew 17.7 M: 16.5 M before `main` (608 members at about 27,000 each, and
  the constructors), and 1.2 M at exit. The snapshot's start grew 21,000 (the zip) and its exit
  1.47 M: the C++ static destructors the constructors registered (HiGHS's strings and the rest)
  and OpenBLAS's `gotoblas_quit`, which run at every exit; Decision 14's "within 1%" did not
  count them.
- **Memory.** One `solve` leaves 24.8 MB more linear memory than a bare run (OpenBLAS's 16 MiB
  buffer and scipy.linalg's import), far inside the default 1 GiB.
- **The Boost flag** halves `betaincc`'s cost (binary128 in software without it) and leaves the
  value alone; without it `python.wasm` is 272,602 bytes larger.
- **The wheel** is 65.7 MB, 34.3 MB under PyPI's 100 MB (question 64 stays open, no landing
  crosses it).
- **Build time** (a benchmark fact): 18 steps from empty in 17 min 11 s on macOS while a
  container build ran beside it (14 min 53 s at `3aa0d5b`, also beside one; step 38 alone 1 min
  57 s).

### The judge

The full `uv run pytest -n 3`, once, on `2687418` with the set built from empty there, no
`--accept` (`build/037/full-judge.log`, `build/037/latest-full.json`; the upstream kit fetched by
`tests/upstream/fetch.py`):

```
wasi_python v1: 556/580 pass · 21 gap · 3 blocked · 0 fail   (unit suite 1277/1284, 7 skipped)
blocked by: prior-art clones 1 · three systems 1 · wheel 1
ratchet vs 9dad163977: lost 0 · absent 0 · unrun 0 · unrun locally 1 · gained 24 · grew 161 · more 2 · judge changed: tests/checks/test_v1_1_artifact_set.py, tests/checks/test_v1_3_data_stack.py, tests/checks/test_v1_3_scipy.py and 22 more
RED: 161 metric(s) grew
1833 passed, 10 skipped, 21 xfailed in 888.05s (0:14:48)
```

- **0 fail, lost 0.** The 21 gaps are main's 15 and Decision 9's six (three checks, two binaries).
  The 3 blocked need prior-art clones, the three-system release and a built wheel in `dist/`,
  which this worktree has not (the wheel was built aside, above). `ruff check` and `ruff format
  --check` are clean.
- **Gained 24**: the 19 passing checks of `test_v1_3_scipy.py`, the two scipy dotted-builtin
  checks, the two new source trees and the patches-from-their-script check. **More 2**: pandas' own
  tests that skip without scipy (`importorskip("scipy")`) now run and pass: `pandas-frame` +73,
  `pandas-groupby` +1 (INFERRED from the import; the groups pass whole).
- **The callback scan** (051) is green over the larger binary: 4,137 method-array entries, 3,425
  single definitions, 1,439 getset entries, 568 member entries, no mismatch after the uarray
  patch. The constructor list is the reviewed 155; the features are the line's 10 and `simd128`;
  the imports are main's (no `fd_renumber`, item 11).
- **Grew 161**, each with its cause (`build/037/growth.txt`, every line):
  - the binaries' bytes, +43,083,164 and +43,332,124, and the zip's, +5,657,768: scipy and
    OpenBLAS (the numbers above);
  - every plain-reactor start, +16.0 M to +17.7 M fuel (+6% to +11.7% of the smaller checks):
    608 more zip members at about 27,000 each and the new constructors before `main`, about 1.2 M
    of static destructors at exit (the numbers above);
  - every snapshot start, +1.39 M to +1.53 M (+5.9% to +9.4%): the static destructors at exit
    (HiGHS's strings and the rest, OpenBLAS's `gotoblas_quit`) and 21,000 for the larger zip;
  - the checks that walk the zip's directory or its resources (`test_the_zips_directory.py`, up
    to +24%) and `importlib.metadata`'s walk: 608 more members, one more distribution;
  - the rest, 0.004% to 5%: the same start and exit cost on longer runs (the upstream groups,
    the golden jobs of numpy, pandas, matplotlib, lxml and regex).
- **Accept reasons** for the lane:
  - `--accept-judge "spec 037: scipy's checks, goldens and oracle pin (scipy 1.18.1, macosx_12_0
    wheel on macOS arm64, one BLAS thread), the three gaps closed by spec 038, the reviewed
    constructors and simd128, scipy and OpenBLAS in the judge's lists, scipy's own dotted-builtin
    check with native scipy's two names, the licence source's tarball-first rule, the step
    count in the progress unit checks, the patches-from-their-script check"`;
  - `--accept-growth "spec 037: scipy and OpenBLAS are linked (python.wasm +43.1 MB, a finding
    for the build review under Decision 14) and their package is in the zip (+608 members, +5.7
    MB): every plain start pays about 16.5 M for the members and the constructors and every
    exit about 1.2 to 1.5 M for the C++ static destructors; zip-walking checks scale with the
    members"`.

### For the lane

- Build-class: it changes `scripts/`, `recipes/`, `downloads/SHA256SUMS` and the release workflow.
  Accept with `--accept-judge` (the judge files above), `--accept-growth` and `--accept`.
- The main tree needs five new pins in `downloads/` (`scripts/00_download.sh` fetches them).
- **When 063 lands first**, its `tests/upstream/packages.toml` gains `scipy` (`later`, closer spec
  066, Revised at build item 16) and `openblas` (`via scipy`), and `test_v1_3_scipy.py` takes its
  place by 063's rule (g); the release workflow's zero-patch count rises by two over whatever
  it is then.
- 043 (matplotlib M2) builds after this: Decision 8's conditions a to f fall to it.
