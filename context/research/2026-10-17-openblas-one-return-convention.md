# One return convention for OpenBLAS's C LAPACK on wasm32-wasip1

- **Status:** executed 2026-10-17, in scratch only; nothing in the build was changed. A research memo, not a built change: the carried patch it describes is reviewed by the specification that carries it.
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5), asked by the owner's session to run step 1 of the first experiment of `2026-10-17-what-scipy-needs.md`.
- **Feeds:** `2026-10-17-what-scipy-needs.md` (its finding 6, its recommended route items 3 and 4, its questions 2 and 3); `../constitution.md` §4.1 (carried patches, amended 2026-10-17); `questions-for-the-owner.md`.
- **Stands on:** `2026-10-17-what-scipy-needs.md` (the build flags, the 111 clashes, the trap in `dgesdd_`, the scipy probe objects).
- **Evidence:** `2026-10-17-openblas-one-return-convention/`: `scripts/` (every script written for this memo), `probes/` (`lapack_void.c`) and `outputs/` (every number below; the build logs and the two variant patches, over 200 KB each, stayed in scratch). The patch itself (1,119,817 bytes, SHA-256 `dde3be7a…3e92`) is not in git: `scripts/make_void.py` regenerates it byte for byte from the pinned tarball (finding 7). Build trees, archives and `.wasm` files are not evidence to copy into git.
- **Repository state:** `main` at `efa3f12`, read only. Tools used from it, read only: `build/tools/wasi-sdk-33.0-arm64-macos` (clang 22.1.0-wasi-sdk, LLVM `4434dabb`), `build/tools/wasmtime-v49.0.3-aarch64-macos` (49.0.3), and `scripts/steps/apply_patches.sh` (run on a scratch tree). Native reference: Apple clang 17.0.0. numpy 2.5.2 from the scipy memo's scratch host venv (`outputs/tools.txt`).
- **Machine (benchmark facts only):** Apple arm64, macOS 26.5.2. A wasm build of OpenBLAS took about 54 s, the native one about 58 s.
- **Upstream read:** a shallow clone of OpenBLAS `develop` at `0fee0ebe` (2026-10-17), deepened to 470 commits to read history, now `context/prior_art/openblas` (recorded in its README). BSD-3-Clause. Read and built, never copied.

## The question

The scipy memo found that OpenBLAS 0.3.34's C LAPACK mixes `int` and `void` returns for the same subroutines, and that wasm turns each mix into a trap. It proposed one convention, every subroutine `void`, as the upstream fix. Its first experiment, step 1, asks: applied to a scratch copy, does that convention remove every internal clash, do `dgesdd_`, `dgees_`, `dsyevr_` and `zgesdd_` then match native, and are there clashes that are not return types (argument counts, callbacks)? This memo also asks how big the change is as a patch, whether it applies cleanly, and whether OpenBLAS upstream has already made it.

Terms:

- **Signature clash:** one function name with two wasm types (parameters and result) across objects. wasm-ld warns `function signature mismatch` for a direct call and links a trapping stub.
- **Return-only clash:** the parameters agree and only the result differs (`int` against `void`).
- **Hidden length:** f2c's extra `ftnlen` argument carrying a Fortran string's length.
- **C LAPACK:** OpenBLAS's C translation of Reference-LAPACK, built with `NOFORTRAN=1` (`C_LAPACK=1`).

## Method

- **Input (EXECUTED).** `OpenBLAS-0.3.34.tar.gz`, copied from the scipy memo's download folder. SHA-256 `cd7e129868320cc2d033afa920e31202dfe0b8066a5b66661900ccc0f197dfed`, `OK` against the digest the scipy memo recorded from GitHub's asset (`outputs/tarball-sha256.txt`). Unpacked into `pristine/`. At the end that tree still equals a fresh unpack (`outputs/pristine-tree-diff.txt`, empty).
- **Build (EXECUTED).** `scripts/build_wasm.sh` copies a tree and runs the scipy memo's make line with its flags unchanged (direct SDK clang, `TARGET=WASM128_GENERIC ARCH=wasm`, `C_LAPACK=1`, no threads, static, the five outside fixes). `scripts/build_native.sh` builds the same tree for the host (`TARGET=ARMV8`, the same LAPACK choice).
- **Detectors (EXECUTED).** `scripts/link_whole.sh` links the archive with `--whole-archive` and counts wasm-ld's warnings (goal 0). wasm-ld prints one warning per name, so a second detector, `scripts/objsigs.py`, reads every object's type, import, function and linking sections and lists every wasm type each global function name has, in every object.
- **The change (EXECUTED).** `scripts/make_void.py` applies the convention to a scratch git copy of the tree (`work/tree`). The patch is `git diff` against the pristine commit.
- **Runs (EXECUTED).** `probes/lapack_void.c` calls ten LAPACK entry points on fixed inputs, one process each. `scripts/run_probe.sh` builds it for wasm (run under wasmtime) and natively. `scripts/compare.py` compares wasm with native. `scripts/numpy_ref.py` compares wasm with numpy.
- **scipy side (EXECUTED).** `scripts/scipy_side.sh` re-links the scipy memo's own compiled scipy objects (`cython_blas.o`, `cython_lapack.o`, and its direct-call probes of f2py's prototypes) against each archive.
- **Upstream (EXECUTED, READ).** The `develop` clone was grepped, diffed against 0.3.34, its history read, and built with the same script.

## Findings

### 1. The baseline reproduces the scipy memo exactly

- **EXECUTED.** The pristine build gives an archive of 11,095,502 bytes, SHA-256 `9e5fb7eb…df8610287`, the same bytes the scipy memo built (`outputs/archive-hashes.txt`).
- **EXECUTED.** Linked whole, it gives 111 warnings, the same 111 names as the scipy memo's `abi-openblas-internal.txt` (`outputs/link-whole-pristine.summary`, `clash-names-pristine.txt`). `objsigs.py` independently finds the same 111 names among 3,782 objects (`outputs/objsigs-pristine.txt`).
- **EXECUTED** (`scripts/classify.py`, `outputs/clash-classes-pristine.txt`). 110 of the 111 are return-only. In 100 the callers say `int` and the definition is `void`, for example `dgemm_` called from the f2c file `dlarft.c`. In 10 the callers say `void` and the definition is `int`: `?larft_` (re-imported from Reference-LAPACK as `int`) and OpenBLAS's own `?trtrs_` and `?laed3_` (`interface/lapack`).
- **EXECUTED.** One clash is an argument count: `xerbla_` is declared with 2 parameters where it takes 3. wasm-ld shows one object (`sgeqp3rk.o`). `objsigs.py` shows the real extent: 20 objects (`?geqp3rk`, `?gedmd`, `?gedmdq`, and DEPRECATED `?geqrs`), all missing the hidden length.

### 2. The convention, applied by a script

**EXECUTED** (`scripts/make_void.py`, counts in `outputs/make-void-B.txt`). The rules:

| rule | where | what | count |
|---|---|---|---|
| R1 | `lapack-netlib/SRC`, `SRC/DEPRECATED`, `INSTALL`, `TESTING/MATGEN` | an `int` return on a subroutine's declarator becomes `void` (declarations) | 1,842 |
| R1 | the same | the same, on definitions | 60 |
| R2 | `interface/lapack/*.c` | `int NAME(` becomes `void NAME(` | 26 |
| R3 | inside every definition R1 or R2 changed | `return 0;` becomes `return;` | 294 |
| R4 | `common_interface.h` | `int BLASFUNC(xerbla)` and the `?getrf`, `?gesv`, `?potrf`... prototypes become `void` | 79 |
| R5 | `driver/others/xerbla.c` | `xerbla_` returns `void` | 3 |
| R6 | 20 f2c files | `xerbla_(char *, integer *)` gains `ftnlen`; its 36 calls gain `(ftnlen)N` | 20 + 36 |

- The subroutine names are taken from the sources, not typed in: every `name_` that f2c marked `/* Subroutine */` (2,154 names), plus OpenBLAS's own LAPACK routines and `xerbla_`. f2c writes an INTEGER function as `integer`, never `int`, so `int` before such a name always means a subroutine (READ: the f2c prelude, `typedef blasint integer`).
- **EXECUTED.** The patched tree compiles with no error and no new warning class: the counts of each `-W` class are identical before and after (`outputs/warn-classes-*.txt`).
- **A side note (EXECUTED counts).** The scipy memo said 515 files declare their callees `int`. In 0.3.34, 1,549 `SRC` files contain an `int name_(` declarator, mostly `xerbla_` (1,584 declarations in all). Files with an `int` subroutine other than `xerbla_`: 112. The 515 was counted another way and is not reconciled here.

### 3. Goal 0 is reached; the only non-return clash was `xerbla_`'s hidden length

| build | wasm-ld warnings, archive linked whole | names with more than one type (`objsigs.py`) |
|---|---|---|
| 0.3.34 pristine | 111 | 111 |
| A: R1–R5 (returns only) | 1 (`xerbla_`, 2 vs 3 parameters) | 1 (`xerbla_`, in 20 objects) |
| **B: R1–R6 (the patch)** | **0** | **0** |
| `develop` @ `0fee0ebe` | 0 | 0 |

(EXECUTED: `outputs/link-whole-*.summary`, `outputs/objsigs-*.txt`.)

- **Argument counts (EXECUTED).** One class only: the missing hidden length on `xerbla_` in 20 objects. It is mechanical too (R6), and it is what upstream did (finding 6).
- **Callbacks (EXECUTED, READ).** None. f2c's untyped `L_fp` is declared in every file but used in no prototype (READ: `grep "L_fp [a-z]"` finds nothing). The 20 drivers that take a SELECT function take a typed pointer, for example `logical(*select)(doublereal*,doublereal*)` in `dgees.c:732`. The probe's `dgees_` sorts through such a C callback under wasmtime: the indirect call ran, `select_called=1`, `sdim=32` (finding 4).
- **So the condition that would kill the upstream plan (clashes that are not return types, in large numbers) did not occur.**

### 4. The routines match native and numpy

**EXECUTED** (`outputs/probe-wasm-B.txt`, `probe-native-B.txt`, `compare-wasm-vs-native-B.txt`, `compare-wasm-vs-numpy-B.txt`).

Inputs: the scipy memo's 64×64 symmetric positive definite matrix `1/(1+i+j) + I` for `dgesv_`, `dpotrf_`, `dgeqrf_`, `dsyev_`, `dsyevr_` and the memo's own trapping `dgesdd_` call (`dgesdd64`); a fixed 64-bit LCG for a 64×64 general matrix (`dgetrf_`, `dgees_`), an 80×48 real matrix (`dgesdd_`) and an 80×48 complex one (`zgesdd_`). Integers (`info`, all 64 pivots, `sdim`) must be equal. A vector passes when `max|wasm − ref| ≤ 1e-10 × max|ref|`.

| routine | before (pristine archive, same probe) | after (patch B) vs native, same patched tree | after vs numpy 2.5.2 |
|---|---|---|---|
| `dgesv_` | trap `signature_mismatch:dgesv_` | pass, 4.8e-16 | pass, 1.5e-15 |
| `dgetrf_` | trap `signature_mismatch:dgetrf_` | pass, pivots equal, 1.7e-15 | (not compared) |
| `dpotrf_` | trap `signature_mismatch:dpotrf_` | pass, 1.6e-16 | (not compared) |
| `dgeqrf_` | ran | pass, 1.0e-16 | (not compared) |
| `dsyev_` | ran | pass, 6.4e-16 | pass, 5.7e-16 |
| `dsyevr_` | trap `signature_mismatch:dlarft_` | pass, 6.4e-16; residual `|Az−wz|` ok | pass, 5.0e-16 |
| `dgesdd_` 64×64 (the memo's call) | trap `signature_mismatch:dlarft_` | pass, s0 = 3.1160808585710318 | pass, 1.4e-16 |
| `dgesdd_` 80×48 | trap `signature_mismatch:dlarft_` | pass, 2.4e-15; residual `|A−USVᵀ|` ok | pass, 1.3e-15 |
| `zgesdd_` 80×48 | ran | pass, 1.6e-15; residual ok | pass, 2.3e-15 |
| `dgees_` 64×64, sorted by a callback | ran | pass, 5.9e-15, `sdim` equal; residual `|AZ−ZT|` ok | pass, eigenvalues as a set 1.1e-14; `sdim` = numpy's count of Re > 0 |

- The native reference is a native build of the same patched tree (`TARGET=ARMV8`, C LAPACK), so it runs the same LAPACK code with different BLAS kernels. numpy's is an independent LAPACK (the Fortran Reference-LAPACK in numpy's bundled OpenBLAS; INFERRED from how numpy wheels are built, not checked). The largest difference anywhere is 1.1e-14, rounding level.
- The probe declares every routine `void`, the new convention and scipy's. Against the pristine archive that alone causes the `dgesv_`, `dgetrf_` and `dpotrf_` traps: these are the `int`-against-`void` clashes scipy's f2py calls would hit (EXECUTED). `zgesdd_` and `dgees_` ran on the pristine archive because these inputs reach no clashing call (INFERRED).
- The scipy memo's native values reappear: `x0=-0.036999190064`, `wmax=3.116080858571`, and `dgesdd` `s0=3.116080858571` (EXECUTED).

### 5. On the scipy side, only scipy's own clashes remain

**EXECUTED** (`scripts/scipy_side.sh`, `outputs/scipy-side-summary.txt`, `scipy-*-*.names`). The scipy memo's compiled scipy objects, re-linked unchanged against each archive. Counted: warnings whose pair names a scipy object.

| archive | `cython_blas` + `cython_lapack` | f2py `_flapack` (direct-call probe) | f2py `_fblas` |
|---|---|---|---|
| 0.3.34 pristine | 57 | 37 | 0 |
| **patch B** | **2**: `chla_transtype_`, `xerbla_array_` | **4**: `?gees_` | 0 |
| `develop` | 3: those two and `ilaver_` | 5: `?gees_` and `ilaver_` | 0 |

- What is left after patch B is exactly the scipy-side list of the scipy memo: `?gees`'s two literal hidden lengths in `flapack_gen.pyf.src`, and the two `cython_lapack` signatures. The memo's INFERRED claim that the convention removes the `int`/`void` clashes with scipy now holds at link level. Nothing of scipy was run.
- `_fblas` has no clash before or after (BLAS was already `void`).

### 6. Upstream `develop` has already made this change, unreleased

- **EXECUTED** (`git ls-remote`). The newest release tag is `v0.3.34` (2026-07-16). No 0.3.35.
- **READ** (`git log`, `outputs/upstream-develop-void.txt`). Between 2026-09-03 and 2026-10-02 the maintainer (martin-frbg) merged a series that makes C LAPACK's subroutines `void`, "like the original LAPACK subroutines": #6008 (`larft_sig`), #6017 (`fix-lapack-signatures`, the `interface/lapack` routines), #6022, #6030, #6061, #6063 (`f2c-lapack-s`/`-d`/`-c`/`-z`, "Fix compiler warnings", with large removals of unused f2c prelude), #6036, #6049, #6077, #6079, #6080 ("Fix compiler warnings and function signatures"), #6081 ("Fix function signature of XERBLA") and #6082 ("Make XERBLA a void function, matching its Fortran SUBROUTINE origins"). The commit messages say nothing of wasm; the motive read from them is compiler warnings and LAPACK fidelity (INFERRED).
- **EXECUTED.** `develop` has 0 `int NAME(` in `interface/lapack`, `void BLASFUNC(xerbla)` in `common_interface.h`, 1,599 `void xerbla_(` declarations and no `int xerbla_(`. It builds with the scipy memo's flags and the same five outside fixes, links whole with 0 clashes, and the probe passes against the native reference on all ten calls (`outputs/probe-wasm-develop.txt`).
- **One gap upstream (EXECUTED).** `lapack-netlib/INSTALL/ilaver.c:322` is still `/* Subroutine */ int ilaver_`. ILAVER is a SUBROUTINE. scipy wraps it in f2py and in `cython_lapack`, which call it `void`, so it clashes on `develop` (finding 5); patch B changes it. The other `int` left in `INSTALL` (`?lamc1`–`?lamc5`, `mysub_`) are internal or test code with agreeing declarations; they made no clash on `develop`.
- **The patch is therefore a backport (INFERRED).** It was made by our own script, not copied, but it reaches the state upstream reached, plus `ilaver_`. Under §4.1 it would be deleted when an OpenBLAS release carries upstream's change. OpenBLAS released 0.3.33 in April and 0.3.34 in July (READ: the release list), so 0.3.35 is plausibly near; no date is announced in what was read.

### 7. The patch

**EXECUTED** (`openblas-0.3.34-c-lapack-void.patch`, `outputs/patch-breakdown.txt`, `outputs/apply-patches.log`).

- **Size.** 1,665 files, 2,369 lines removed and 2,369 added (every change is in place). 26,136 patch lines, 1,119,817 bytes, SHA-256 `dde3be7a6e27c0b5a4bbdee252a8b1a654ec0bf37b13d9f97f859a9b540e3e92`. By folder: 1,549 `lapack-netlib/SRC`, 48 `TESTING/MATGEN`, 36 `SRC/DEPRECATED`, 26 `interface/lapack`, 4 `INSTALL`, `common_interface.h`, `driver/others/xerbla.c`.
- **What dominates.** 1,475 of the 1,665 files change only their `xerbla_` declaration (1,599 changed lines). The other changes: 438 lines of other subroutines `int` → `void`, 294 `return 0;` → `return;`, 36 `xerbla_` calls gain their length.
- **It applies with zero offset.** The repository's own `scripts/steps/apply_patches.sh`, run on a fresh unpack in scratch with the patch as `0001-openblas-c-lapack-void.patch`: `applied`, 1,665 files "cleanly", no offset, fuzz or skip. The applied tree equals the scripted tree byte for byte (`diff -r`). Every file is mode 100644; no new, deleted, renamed or binary file (`git apply --summary` is empty), so it meets `recipes/patches/README.md`'s rules as read.
- **It is reproducible.** Re-running `make_void.py` on the pristine commit gives a diff with the same SHA-256 as the patch file.
- **A smaller variant fails (EXECUTED, one attempt).** `--keep-xerbla-int` leaves `xerbla_` as 0.3.34 defines it (`int`): 190 files, 784 lines each way (`outputs/variant-C-keep-xerbla-int.patch`). It leaves 1 clash: in 15 objects f2c grouped `xerbla_` into one declaration with other subroutines (`extern int sgemm_(...), xerbla_(...)`), so turning the group's `int` to `void` turns `xerbla_` too. Fixing that needs splitting declarations, which is no longer a one-token rule. Not pursued; upstream chose `void` for `xerbla_` anyway.

### 8. The four WASI portability fixes: not in `develop`, and not in this patch

- **EXECUTED** (`diff`, `grep` of `develop`). None of the scipy memo's portability fixes is upstream: `ctest.c` still knows wasm only as `__EMSCRIPTEN__` (line 180); `common.h` includes `<sched.h>` only for named OSes (lines 113, 117); `driver/others/memory.c` guards `<sys/shm.h>` with `NO_SYSV_IPC` but includes `<sys/ipc.h>` outside the guard (lines 146–148, 1729–1731). `-DARCH_WASM` follows from `ctest.c`. (`-D_WASI_EMULATED_MMAN`/`-lwasi-emulated-mman` is a wasi-libc choice, not an OpenBLAS defect.)
- **They should not ride in the same patch (INFERRED).** §4.1 makes a recipe file the first answer, and all four already work as recipe items (make variables, `CFLAGS`, one stand-in header). They are a different concern from the ABI, and upstream has already done the ABI part without them. They are their own small upstream pull request: `__wasi__` beside `__EMSCRIPTEN__` in `ctest.c`, `<sched.h>` for it in `common.h`, and `<sys/ipc.h>` moved inside the existing `NO_SYSV_IPC` guard. If that lands, the recipe shrinks to make variables.

## What it decides

- **The upstream plan is proven in scratch.** One `void` convention, applied mechanically, takes OpenBLAS's C LAPACK from 111 internal clashes to 0. The only non-return clash was `xerbla_`'s missing hidden length, mechanical too. No callback clash exists. The SVD, Schur, symmetric eigen, complex SVD, LU, Cholesky and solve paths run under wasmtime and agree with native to about 1e-14.
- **No OpenBLAS pull request is needed for the convention.** Upstream merged it in `develop` in September and October 2026. Two small ones remain worth drafting: `ilaver_` to `void`, and the WASI portability fixes. The scipy pull request of the scipy memo (`?gees` lengths, two `cython_lapack` signatures) is unchanged.
- **For the scipy route, the choice is waiting or a large temporary patch (INFERRED).** Waiting for 0.3.35 is §4.1's default and costs only time; scipy's next steps can run in scratch on patch B meanwhile. Carrying patch B on 0.3.34 is allowed by §4.1 (recorded, reviewed, deleted at 0.3.35), but it is 1,665 files: a reviewer would review the script and the rule, and check the patch by regenerating it, not by reading 26,000 lines. If 0.3.35 ships without the `ilaver_` fix, the carried patch shrinks to one file.
- **The judge.** wasm-ld's count of warnings with the archive linked whole is enough for goal 0. `objsigs.py` is the stronger form: it reads every object, so it names every caller of a clash, not the first. Neither sees f2py's indirect calls; the scipy memo's direct-call probe still does.

## The owner's earlier answers, applied

The draft asked three questions; two are already answered.

1. **Wait or carry.** Question 32 answered it: build our own fixes, carry them, and draft the upstream pull requests. So when scipy is built, patch B is carried on 0.3.34, reviewed as its script and rules with the patch regenerated and hashed, and deleted when a release carries upstream's change (the draft says `Status: merged` for the convention, upstream's pull requests #6008 to #6082).
2. **Upstream drafts.** The same answer's scope ("any project, with a drafted pull request") covers drafting `ilaver_` to `void` and the WASI portability fixes for OpenBLAS.
3. **The clone.** Kept as prior art, `context/prior_art/openblas`.

scipy itself still waits on questions 25 (licences), 29 (SIMD) and 30 (a profile).

## Where it stopped

- Done: step 1's three parts, plus the same checks on upstream `develop`.
- Not done: scipy itself (steps 2–4 of the first experiment). The scipy-side counts come from re-linking the scipy memo's objects, not from a scipy build.
- Not done: OpenBLAS's own LAPACK test suite under wasm. Ten calls on fixed inputs are evidence, not coverage.
- Not done: the native build of the *pristine* tree; the native reference is the patched tree, and numpy is the independent one.
- Two-strikes record: the R6 regex took three tries to match line-broken prototypes (tooling, not a hypothesis). The `--keep-xerbla-int` variant failed once and was not retried (finding 7).
- Scratch kept: `work/` (trees, archives, wasm), `upstream/develop`, `applytest/`.

## One line

Making every C LAPACK subroutine `void` (and giving `xerbla_` its hidden length in 20 files) takes OpenBLAS 0.3.34 on wasm from 111 clashes to 0, and the SVD, Schur and eigen routines then match native to about 1e-14. The script-made patch is 1,665 files and applies with zero offset. Upstream `develop` has already made the same change, unreleased, except for `ilaver_`.
