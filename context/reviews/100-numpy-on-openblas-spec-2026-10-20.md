# Review of 100 — numpy's linear algebra, `dot` and `matmul` run on the set's OpenBLAS

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent (Claude, Opus 5.5) that wrote none of spec 099 or spec 100. This is the pre-build review constitution §5.6 requires, because the spec changes the build recipe and the artifact set.
- **Reviewed:** the specification as drafted, `spec/100-numpy-on-openblas` at `36650bb` (from main `cf414a2`), with its drafting runs in `context/research/2026-10-20-numpy-on-openblas/`; the owner's answers on main `3ff1871`; 099's branch at `0c8904b`, for the stacking questions.
- **Run:** none. A pre-build review of a draft needs no release run: nothing is built yet, and no counted test changes. The build review dispatches its own run.
- **Time box:** 45 minutes (build-class). Used: about 40.
- **Re-ran:** all EXECUTED, with `build/lane.lock` absent throughout.
  - `REPO=<main> WORK=<scratchpad> uv run --no-project python -I prototype/proto.py`. Its output matches `proto.txt` line for line, addresses included. Variant A: 36 signature mismatches. Variant B: 0 mismatches and 0 duplicate symbols.
  - `llvm-nm -u` on variant B's objects. They leave 36 `wasi_numpy_*` names undefined: 35 routines plus `xerbla`. They also leave 22 `cblas_*` names undefined, plus numpy's own `cblas_matrixproduct`. The shims object defines 54 names.
  - `uv run pytest tests/checks/test_v1_5_rebuild_from_pins.py::test_one_qhull_is_linked` (the model for check 4): 1 passed, 0.54 s.
  - `map_sizes.txt`'s eight `lapack_lite_f2c` objects add up to 1,915,393 bytes. This matches the spec. Main's `build/link/python.map` has 0 `cblas_` lines and 8,992 `numpy_lapack_lite_` lines.

The reviewer's self-check list does not apply. This is a draft before its build, so there is no CI run, no measured claim list and no fast-tier output to check yet. The build review checks the list.

## Acceptance criteria against evidence

1. **Checks exist, seen failing first.** Not yet: this is a draft. Checks 1 and 3 were seen failing on main (EXECUTED, `config-guest-plain.out`, `nan-guest-plain.out`). Check 2's failure on 099's tip is INFERRED, but 099 is built now (`0c8904b`), so the builder can run it (L2).
2. **The build.** Met in design (READ).
   - With `-Dblas=openblas -Dlapack=openblas`, numpy's meson tries `scipy-openblas` first. The limited `PKG_CONFIG_LIBDIR` hides it. Meson then tries `openblas` with `cblas` and `interface: lp64` (`numpy/meson.build:110-152`).
   - A found LAPACK drops the eight f2c sources (`numpy/linalg/meson.build:5-17`).
   - With `allow-noblas=false`, a failed detection is an error, not a silent fallback (`:162-166`, `:189-193`).
   - The vendored meson's probe links `dgemm_`, `cblas_dgemm` and `zungqr_` (`blas_lapack.py` `check_symbols`). The drafting ran it by hand with the SDK's clang (EXECUTED). It did not run it through `scripts/wasi-cc` with numpy's `c_args` (N3).
3. **The same bytes everywhere.** Plausible (READ). `openblas.pc` carries absolute host paths. `make_stdlib_zip.py` already rewrites `numpy/__config__.py` (`REWRITE`, line 87). Step 70's `--replace "$HERE=/wasi-python-build"` makes those paths neutral, as it does for scipy's (`scipy-config-guest.out`).
4. **One OpenBLAS.** Met in design (READ and EXECUTED, prototype B). Check 4 would prove it from the link map.
5. **pandas and scipy unchanged.** INFERRED in the spec, and the builder shows it by hash. Reasonable: neither compiles against anything step 40 changes except `numpy/__config__.py`, which neither compiles against.
6. **Numbers recorded.** Build-time. The INFERRED numbers are labelled, except the small-call fuel claim (L3).
7. **The judge.** The flags are drafted. The MANIFEST wording is short (L5).
8. **The release.** Build-time.

## Findings, most severe first

1. **M1 (Medium): under a memory cap, the guest can now exit where today it raises `MemoryError`** (spec Decision 6, the "Memory" bullet; OpenBLAS `driver/others/memory.c:2981-2987`).
   - **What happens.** OpenBLAS's first level-3 call allocates its 16 MiB buffer. After this spec, that means any 2-D float `matmul` or `dot`, and any `numpy.linalg` call. If the allocation fails, OpenBLAS retries ten times. Then it prints "OpenBLAS error: Memory allocation still failed after 10 retries, giving up." to stderr and calls `exit(1)`.
   - **Failure.** A guest run under `memory_bytes` with less than about 16 MiB of headroom calls `a @ a` on 2-D float64 arrays. Today numpy's own loop runs, or numpy raises `MemoryError`. After this spec the guest process ends with status 1. Inside a session, the session ends.
   - **Why it matters.** The spec weighs memory only against the default 1 GiB. The judge already holds `MemoryError` under a cap as a behaviour (`test_v1_3_data_stack.py:252`, with `memory_bytes=560 << 20`). scipy has had the same path since 037, but numpy's `matmul` is far more common.
   - **Evidence that would close it.**
     - Name the behaviour in Decision 6 and Decision 10, and in the README's platform facts.
     - Add one probe to criterion 6: on the built set, a `matmul` under a cap just above a bare numpy import's memory, with the outcome recorded on both binaries.
     - Or add a check, if the owner wants the behaviour held.
     - A fix, for example a smaller `BUFFER_SIZE` or a recipe that turns the failure into an error, is not required. That would be its own specification.

2. **L1 (Low): question 107 is answered** (spec "The owner's choices", the Status line; main `3ff1871`, `decisions.md`, "Correction and question 107"). The owner chose "Yes, before 0.1.0".
   - Fix text: replace "Decided until answered: (a)" with "Answered 2026-10-20 (main `3ff1871`): (a), 'Yes, before 0.1.0'; exact singular-matrix parity is not a goal in wasm."
   - Make Decision 1's closing sentence match.
   - Context only: the reviewer may write it in.

3. **L2 (Low): 099's build finding B1 is not named, and 099's sentences about it are not replaced** (spec Decisions 11 and 12, and check 3's "seen failing first").
   - **The gap.** 099's build (`0c8904b`) found that `lstsq` of a `nan` matrix now raises `SystemError`, with `lapack_lite`'s `ValueError` as its context. 099 wrote this into the README and CHANGELOG, "closed by spec 100". Spec 100 closes it, because OpenBLAS's `xerbla` prints and returns, and check 3 holds `lstsq raises LinAlgError`. But Decision 11 does not remove 099's B1 sentences. Its "seen failing first" lines describe main, not the stacked base.
   - **Fix text.** Decision 12 names B1 as closed. Decision 11 removes 099's README sentence ("…and `numpy.linalg.lstsq` of one raises `SystemError`…") and 099's CHANGELOG sentence ("One case gets worse until spec 100: …"). Checks 2 and 3 record their failure on 099's built tip, EXECUTED. That replaces "on 099's tip, 158 E and agree 291 (INFERRED)".

4. **L3 (Low): the fuel blast radius is understated, and one claim is labelled stronger than its evidence** (spec Decisions 6 and 9).
   - **Every numpy import moves.** `import numpy` runs `_sanity_check`, which calls `ones(2, float32).dot(...)` (`numpy/__init__.py:797`). With `HAVE_CBLAS`, that call is `cblas_sdot`. So fuel moves a little on every row that imports numpy, not only on rows that run linear algebra or products.
   - **"Small calls do not cost more" is a proxy.** It compares numpy's own 3×3 loop with scipy's `dgemm` and `getrf` wrappers, f2py's overhead included. numpy-on-OpenBLAS's cost for a 3×3 call was not measured.
   - Fix text: in Decision 9, say "every row that imports numpy (its import-time `dot`), most visibly those that run…". Label the small-call sentence INFERRED. Add to criterion 6: "a 3×3 `matmul` and `inv` per call on the built set, against the base".

5. **L4 (Low): the goldens argument covers digits, but two goldens print pixel hashes** (spec Decisions 6 and 7, and Decision 9's "Golden outputs do not change").
   - **The gap.** `plot_line` and `plot_contour` print the full SHA-256 of the RGBA buffer (`tests/jobs/plot_line.py`), recorded on darwin-arm64. matplotlib composes its affine transforms with `np.dot` on 3×3 matrices, which becomes `cblas_dgemm` after this spec. It inverts them with `numpy.linalg.inv`. Decision 7 also changes the native side's BLAS, from Accelerate to OpenBLAS. A pixel hash is not protected by "9 or 6 digits".
   - **Likely outcome.** The hashes probably hold: the guest without fused multiply-add already matches native with it today.
   - **Fix text.** Before the build, run `plot_line` and `plot_contour` natively in the drafting's `venv-openblas` against their `.expected`. Record the result as EXECUTED. Then say in Decision 9 that a changed pixel hash on either side is a finding, never an edit.

6. **L5 (Low): the MANIFEST claim misses changed lines** (spec Kind line, Decision 9's `MANIFEST` bullet, the `--accept-growth` text; `scripts/wasi-cc:65`).
   - **The gap.** `scripts/steps/40_numpy.sh` and `scripts/steps/60_link.sh` are MANIFEST `recipe` lines (main's `build/artifacts/MANIFEST`, line 258 and the `60_link.sh` line). So MANIFEST changes three existing lines, not one. Also, `scripts/wasi-cc`'s comment says "Only step 57 (scipy) sets them", which turns false once step 40 sets `WASI_CC_FILE_INCLUDES`. `scripts/wasi-cc` is a MANIFEST line too (line 273).
   - Fix text: "MANIFEST: three `recipe` lines added; four changed (`recipes/wasi-numpy.cross`, `scripts/steps/40_numpy.sh`, `scripts/steps/60_link.sh`, `scripts/wasi-cc`, whose comment now names steps 40 and 57)". Drop "`scripts/wasi-cc` does not change" from Decision 4.

7. **L6 (Low): the shim file shims 19 routines nobody calls, and typing them by hand risks a mistake no check can see** (spec Decision 4, `recipes/numpy_lapack_shims.c`; `umath_linalg.cpp:2351`).
   - **The facts.** Of the 54 names, 35 are called. Prototype B's objects leave exactly 35 routines plus `xerbla` undefined (EXECUTED). The other 19 are never referenced:
     - `sdot` and `ddot`;
     - the four `?dot?` routines;
     - the four Fortran `?gemm` routines;
     - the four `?potrs` and the four `?potri`;
     - `cgeev`, whose only caller sits under `#if 0`.
   - **The risk.** Every LAPACK argument is a pointer, an `i32` in wasm. A swapped argument in a hand-typed shim passes every signature scan, and only a test would catch it.
   - **Fix text.** Shim only the 35 names numpy calls. Write each as a pass-through in numpy's parameter order. Check 4's build half asserts that the shim archive's defined names equal the `wasi_numpy_*` names `umath_linalg.o` and `lapack_litemodule.o` leave undefined, less `xerbla`. A future numpy that calls a new routine then fails the link loudly, because the main link has no `--allow-undefined`.

8. **L7 (Low): the README and CHANGELOG sentences overstate or blur two numbers** (spec Decision 11).
   - The "46 of 300" and "57" are macOS arm64 measurements. The spec's own Scope says x86_64 was not run. Fix text: "…disagree on 46 (macOS arm64; the guest raising each time)…".
   - The CHANGELOG says "about 1.9 MB smaller". Decision 9 says 1.7 to 1.9, and the owner's record says about 1.8. Fix text: "the measured number, from the build".

9. **L8 (Low): the lane section misses three files shared with 099** (spec "For the lane"). 099 also changes `tests/harness/scan.py`, `tests/unit/test_scan.py` and `tests/checks/test_v1_5_rebuild_from_pins.py`, and spec 100 adds to all three. Fix text: name them beside `test_v1_3_data_stack.py`.

### Notes (no round needed)

- **N1: §4.1 and a facts sheet.** No patch is carried, so the letter of §4.1 asks for no facts sheet. The spec is right about that. Two reasons to write a short one anyway:
  - Precedent: 037's recipe-only scipy shims (`context/upstream/27-…`) and 099's recipe header (`30-…`) each got one.
  - The header's removal condition ("a numpy release that declares LAPACK's subroutines `void`") has no path to happen unless numpy hears about it.

  The reason the spec gives, numpy's AI policy, covers pull-request text, not a facts sheet. This is the owner's call.
- **N2: check 2's recorded string.** It is acceptable as a pinned fact.
  - Spec 012 makes the guest's bytes the same on every host. Wasm floating point is deterministic, so the 300 letters are the same on all three systems.
  - The invariant that matters is `agree 300`, numpy against scipy.
  - The recorded string adds a ratchet: an OpenBLAS pin change will move it, and that is a judge change. Say so in the docstring.
  - Consider also recording native OpenBLAS's string, and asserting the one direction that matters to a user: the guest never returns finite where native raises (0 of 300 today). That turns the 46 into a held property, not just a pinned accident.
- **N3: the meson probe** was linked with the bare SDK clang, not through `scripts/wasi-cc` with numpy's `c_args`, which carry 099's and the rename headers' `-include` lines. The risk is small: scipy's step 57 runs the same vendored probe through the same wrapper today, and `allow-noblas=false` makes a failure loud.
- **N4: the drafting runs reproduce.** The prototype re-ran identically. The native venv script checks both wheels against the oracle lock's hashes. `crosstab.txt`'s counts agree with the spec's table: 249 = EE 107 + FF 142, 254 = 107 + 147, 291 = 140 + 151.

## Focus questions, answered

1. **Do the shims cover every call, and does the prefix reach every call site?**
   - Yes. `BLAS_FUNC` appears in only four numpy sources outside the dropped f2c files: `umath_linalg.cpp`, `lapack_litemodule.c` and the two `python_xerbla.c` (grep, READ). The `_core` callers use only `CBLAS_FUNC`.
   - The map gives all four the header, five compiles in all. The shims cover all 35 called names (EXECUTED).
   - numpy never takes a LAPACK routine's address (grep for `&FNAME`, assignments and argument uses: none). So every call is direct.
   - A miss in either direction is caught at link time. A plain name called through an `int` declaration is a wasm-ld signature mismatch, which step 60's `clashes` stops on. A prefixed name with no shim is an undefined symbol, a link error, because the main link has no `--allow-undefined`.
   - Spec 051's callback scan and spec 096's slot scan look at indirect calls, so they would not see such a miss. They are not needed here.
   - `xerbla` is correct. `wasi_numpy_xerbla_` is defined by three `python_xerbla.o`, one per archive, and only one is pulled. `lapack_lite.xerbla()` alone calls it. OpenBLAS's three-argument `xerbla_` stays OpenBLAS's, as natively.
   - `info` still carries errors. `umath_linalg.cpp` reads only `info`, and `lapack_litemodule.c` returns the shim's 0 as its `'<name>_'` entry, as native showed.
2. **One OpenBLAS, one LAPACK.**
   - With `have_lapack`, no f2c object is built.
   - A same archive named twice, by path and by `-L`/`-l`, is still one set of lazy members for wasm-ld.
   - Every new definition is strong, so 044's weak-duplicate gate meets nothing new. 099's weak `wasi_python_fe_flags` is not in the shims: they compile outside the cross file.
   - Check 4 proves it from `python.map`, as `test_one_qhull_is_linked` does for qhull.
3. **The cblas move.**
   - The 22 names are `?gemm`, `?gemv`, `?syrk`, `?axpy`, `sdot`, `ddot` and the four `?dot?_sub`.
   - No `i?amax` is called, so `CBLAS_INDEX` never crosses the boundary.
   - The enums are `int`-sized with the same values (101, 111…). `CBLAS_INT` is `int`, matching LP64 `blasint`. Complex scalars pass as `void *` on both sides.
   - Prototype: 0 mismatches.
   - numpy's own tests compare products with tolerances (`assert_almost_equal`, `assert_allclose`) and pass natively on OpenBLAS. Exactness at the low bits is not asserted (READ, spot check).
4. **The native reference.** Reproducible (N4).
   - The 300-matrix check is robust across hosts. It pins a guest fact by design (N2).
   - It does lock in a string an OpenBLAS kernel or pin change would move. Acceptable as a pinned fact, re-recorded as a judge change with a reason.
5. **Blast radius and the claim list.** Mostly backed, with the bytes measured from the map.
   - Understated: every numpy import's fuel (L3) and the MANIFEST lines (L5).
   - Inferred on the wrong basis: pixel-hash goldens (L4).
   - Unweighed: the memory-cap exit (M1).
6. **§4.1.** Holds. Recipe files only, through numpy's own `BLAS_SYMBOL_PREFIX` hook. No carried patch, no new pin. A facts sheet is optional (N1).
7. **Stacking on 099.**
   - The two headers do not interact. 099's `npy_fenv_flags.h` includes only `<fenv.h>`/`<cfenv>` and defines `FE_*` and three wrappers. 100's header defines `BLAS_SYMBOL_PREFIX`.
   - `wasi-cc` appends the per-file `-include` after the cross file's, and both come before the source's own `#include "npy_cblas.h"`, whose `#ifndef` then keeps 100's prefix.
   - Textually, both edit the same two `wasi-numpy.cross` argument lines. That is a neighbour, not a conflict, on the stacked branch.
   - Behaviourally, 100 needs 099. Without it, no non-zero `info` reaches `LinAlgError`. 100 also closes 099's B1 (L2).

## Constitution checks

- **§4.1:** holds (recipe only; N1).
- **§4.2:** holds (no new pin). The oracle wheel's hash is already in the lock.
- **§4.3 and §4.4:** hold. Imports and exports do not change, and check 4 plus `public_api.txt` hold that.
- **§4.6:** holds. The artifact set changes, and that is why this pre-build review is required.
- **§5.6:** this pre-build review is the required one. A different agent reviews the build.
- **§7 never-do list:** nothing tripped. No golden output, gap, allowance or progress file is edited. The oracle pin is declared a judge change.

## Disposition (filled in by the author, then confirmed by the reviewer)

The author's answers, on `spec/100-numpy-on-openblas` after the rebase onto main `3ff1871`. The revision's runs are EXECUTED 2026-10-20 on macOS arm64, `build/lane.lock` absent, in `context/research/2026-10-20-numpy-on-openblas/`.

1. **M1 — answered in writing, with evidence; documented, not fixed.** New Decision 13.
   - **scipy's exposure since 037 is real** (EXECUTED, `cap_probe.py`, `cap-runs.txt`, main's set): under a 64 MiB cap, after `import numpy, scipy`, a 64 MiB array raises `MemoryError`, numpy's own 64×64 `matmul` runs, and scipy's `blas.dgemm` ends the run with exit 1 and "OpenBLAS error: Memory allocation still failed after 10 retries, giving up.", on both binaries; at 68 MiB (snapshot) and 72 MiB (plain) it returns. `cap_keep.py` (`cap-keep.txt`, 256 MiB): one early 4×4 `dgemm` maps the buffer, which OpenBLAS keeps (`blas_memory_free` only marks it unused, READ), so a later call after memory is filled returns; without the early call it exits 1.
   - **Recipe fixes weighed, all refused** (Decision 13 (a) to (e)): `BUFFERSIZE` is ignored on wasm (`common_wasm.h:87` defines `BUFFER_SIZE` unconditionally) and the buffer must hold GEMM's ~11.25 MiB `sgemm` panel anyway; `MAX_STACK_ALLOC` covers level-2 only; renaming `exit` in OpenBLAS's compile gains nothing, since no caller checks and nothing can unwind; mapping the buffer at initialization costs every instance 16 MiB; failing into numpy's error handling needs a patch to the allocator and its callers (out of scope, its own specification).
   - **Recommended and chosen: document and record.** Decisions 6 and 10 name it; Decision 11 adds a README platform-facts bullet with the early-call advice; criterion 6 records `cap_probe.py` (numpy's `a @ a`, 64, 68 and 72 MiB) and `cap_keep.py` (both `FIRST` values) on the built set, both binaries. Why: the behaviour is already in the binary (scipy), the outcome is a clean exit with a named reason, not a wrong answer or a trap, and every closing fix is a patch. No check holds it.
2. **L1 (question 107) — written in.** "The owner's choices" says "Answered 2026-10-20 (main `3ff1871`): (a), 'Yes, before 0.1.0'; exact singular-matrix parity is not a goal in wasm"; the Status line and Decision 1's closing say the same.
3. **L2 (B1) — written in, with runs on 099's built tip.** On a private copy of 099's set (`b0e1593`, `SHA256SUMS` `7519b047…`), both binaries: `lstsq` of a `nan` matrix raises `SystemError` (`nan-099-*.out`), and numpy agrees with scipy on 291 of 300 (`singular300-099-*.out`, `crosstab-099.txt`). Decision 9 and Decision 12 name B1 closed and why; Decision 11 removes 099's README sentences (from "That LAPACK is numpy's own bundled `lapack_lite` until spec 100" to the bullet's end) and its CHANGELOG sentence "One case gets worse until spec 100: …"; checks 2 and 3 record their failure on that tip, EXECUTED. The same run shows 099's `cholesky` of a `nan` matrix raising where native returns; this specification makes it native too.
4. **L3 (fuel radius) — written in.** Decision 9: every row that imports numpy moves (`_sanity_check`'s `x.dot(x)`, `numpy/__init__.py:797-799`, becomes `cblas_sdot`). Decision 6's small-call sentence is labelled INFERRED; criterion 6 adds the 3×3 `matmul` and `inv` per call on the built set against the base.
5. **L4 (pixel goldens) — run before the build.** `plot_goldens.sh` (`plot-goldens.txt`): `plot_line` and `plot_contour` natively, in the oracle's environment, print exactly their `.expected` on the oracle's Accelerate venv and on the same venv with numpy's OpenBLAS wheel (EXECUTED). Decisions 7 and 9 say so, and that a changed pixel hash on either side is a finding, never an edit.
6. **L5 (MANIFEST lines) — written in.** Kind line, Decision 9 and `--accept-growth`: three `recipe` lines added, four changed (`recipes/wasi-numpy.cross`, `scripts/steps/40_numpy.sh`, `scripts/steps/60_link.sh`, `scripts/wasi-cc`). Decision 4 and Design: `scripts/wasi-cc`'s line 65 comment becomes "Steps 40 (numpy, spec 100) and 57 (scipy) set them"; "does not change" is gone.
7. **L6 (19 uncalled shims) — taken.** Decision 4: 35 shims, the routines numpy calls, each a pass-through in numpy's parameter order; the 19 uncalled names get none. Check 4 asserts the shim archive's defined names equal the `wasi_numpy_*` names `umath_linalg.cpp.o` and `lapack_litemodule.c.o` leave undefined, less `xerbla`; check 5 gains two unit rows for it.
8. **L7 (README numbers) — written in.** The README bullet says "measured on macOS arm64"; the sizes row says macOS arm64; the CHANGELOG takes the build's measured size, never "about".
9. **L8 (lane's shared files) — written in.** "For the lane" names `test_v1_3_data_stack.py`, `test_v1_5_rebuild_from_pins.py`, `tests/harness/scan.py` and `tests/unit/test_scan.py`, and `context/upstream/README.md`.

Notes:

- **N1 — taken.** `context/upstream/31-numpy-lapack-subroutines-declared-int/facts.md`, drafted in 099's folder-30 form; its `README.md` row is added at build, after the rebase onto 099's tip (Decision 11). Nothing is sent.
- **N2 — taken.** Check 2 carries native OpenBLAS's 300 letters and asserts the guest is never finite where native raises (0 of 300 today, and on 099's tip); its docstring calls the recorded guest string a pinned fact that an OpenBLAS pin change re-records as a judge change.
- **N3 — no change**, for the review's reasons: `allow-noblas=false` makes a failed probe stop the build, and criterion 2 reads meson's "Run-time dependency openblas found" line.
- **N4 — no change.**

## Verdict

Passes for build once M1 is answered in writing. That means naming OpenBLAS's `exit(1)` on a failed buffer allocation under a memory cap in Decisions 6 and 10 and in the README, plus a recorded build-time probe. The Lows are write-ins: L1 to L3 and L7 to L8 only touch `context/` or the spec's prose; L4 to L6 are folded into the build.

## Confirmation

- **Date:** 2026-10-20. The same reviewer, against `spec/100-numpy-on-openblas` at `f25dbcb` (rebased onto main `3ff1871`) and its Disposition. Time box: 20 minutes.
- **Run:** none. This is still a pre-build review. I read files, re-read OpenBLAS's sources (read only, from `build/openblas-build`) and read the revision's runs. `build/lane.lock` was absent throughout.

### M1: confirmed. Document and record is acceptable.

- **The behaviour is already in the binary.** `cap-runs.txt` shows it on main's set, both binaries. Under 64 MiB, scipy's `dgemm` exits 1 with OpenBLAS's line. numpy's own `matmul` runs, and the 64 MiB array raises `MemoryError`. At 68 MiB (snapshot) and 72 MiB (plain), the `dgemm` returns. This spec moves the exposure onto a more common path; it does not create it.
- **The outcome is clean.** It is an exit with a named reason on stderr, not a trap and not a wrong answer. It needs a cap within about 16 MiB of what the program already holds.
- **`cap-keep.txt` backs the early-call advice.** With an early 4×4 `dgemm` (`FIRST=1`), the later call returns. Without it (`FIRST=0`), the run exits 1.
- **Each refusal holds (READ):**
  - **(a) A smaller buffer.** `common_wasm.h:87` defines `BUFFER_SIZE (16 << 20)` with no `#ifndef BUFFERSIZE` guard. Compare `common_arm64.h:179-186`, which has one. So `make BUFFERSIZE` adds `-DBUFFERSIZE` (`Makefile.system:1569-1570`), which the wasm header ignores. The `WASM128_GENERIC` blocking is `param.h`'s shared RISCV64/WASM128 block (P 128, Q 240, R 12288 for sgemm). So sgemm's packed B panel is Q × R × 4 bytes = 11,796,480 bytes, 11.25 MiB. A smaller buffer would need a patch, and would only lower the threshold.
  - **(b) A larger `MAX_STACK_ALLOC`.** It is 2048 in step 38's compile lines (3,782 occurrences in `openblas-build.log`). `STACK_ALLOC` is used only by the level-2 interfaces plus `gemmt`. numpy never calls `gemmt`, so "level-2 only" is right for this spec. A level-3 call still maps the buffer.
  - **(c) Renaming `exit`.** In `memory.c:2981-2987` the `failcount > 10` branch sits inside a `do … while (map_address == -1)` loop. A recipe `exit` that returned would just run again on every pass, an endless loop. Nothing above it can unwind.
  - **(d) Mapping at init.** Every instance would start 16 MiB larger. True by construction.
  - **(e) Failing into numpy's error handling.** It needs the allocator and its callers changed: a patch, out of scope.
- **Other parts of the answer check out.** `blas_memory_free` only clears `used` (READ), so a mapped buffer is kept, as stated. Decisions 6, 10, 11 and 13 and criterion 6's cap probes name and record the behaviour.

### L6: confirmed.

- **The list is right.** Decision 4's 35 names are `?gesv`, `?getrf`, `?potrf`, `?gesdd`, `?gelsd` and `?copy` in four precisions; `s/d/zgeev`; the four `?syevd`/`?heevd`; and `dgeqrf`, `zgeqrf`, `dorgqr`, `zungqr`. That is exactly the set I measured undefined in prototype B's objects, less `xerbla`. `cgeev` is rightly excluded: its only caller sits under `#if 0` (`umath_linalg.cpp:2351`).
- **The shape is right.** One pass-through per routine, in numpy's parameter order, returning 0.
- **Check 4 is right.** It now asserts the shim archive's defined names equal the `wasi_numpy_*` names the two numpy objects leave undefined, less `wasi_numpy_xerbla_`. It names a shim nobody calls and a call with no shim. A call with no shim also fails the main link, which has no `--allow-undefined`.

### The other answers

L1 to L5, L7 and L8, and notes N1 and N2, are written in as the Disposition says. I spot-read Decisions 4, 9 and 13 and check 4's text; I did not re-run L2's or L4's new probes. A detail worth keeping: 099's tip makes `cholesky` of a `nan` matrix raise where native returns, and this spec makes it native again (Disposition 3). Check 3 holds that.

### Verdict

**Confirmed for build.** M1 is answered in writing with runs; all five refusals are true against OpenBLAS 0.3.34's source. No finding stays open.
