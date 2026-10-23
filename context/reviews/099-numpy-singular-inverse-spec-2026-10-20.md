# Review of 099 — numpy's own floating-point signals are kept in software, so a singular matrix raises `LinAlgError` (pre-build)

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent (Claude Code subagent). It wrote no part of spec 099.
- **Reviewed:** the specification as drafted on `spec/099-numpy-singular-inverse`, tip `3502ce1`, from main `958a22b`. That covers the spec, the drafting runs and prototype under `context/research/2026-10-20-numpy-floating-point-status/`, and the facts sheet `context/upstream/30-numpy-fp-status-without-fenv-flags/facts.md`. The pinned numpy 2.5.2 tree was read, read-only, from the main tree's `build/numpy-2.5.2`, with `build/numpy-build/compile_commands.json` beside it.
- **Time box:** 45 minutes (build-class).
- **Run:** none. This is a pre-build review of a draft: nothing is built, so there is no commit to dispatch the release workflow on. The build review runs its own.
- **Re-ran:** (`build/lane.lock` was absent each time; no judge tier, no native build, no container build)
  - The prototype, rebuilt in a scratch folder with wasi-sdk 34 and run under wasmtime 49.0.3 with numpy's real flags: `-O3 -fvisibility=hidden`, and in C++ `-std=c++17 -fwasm-exceptions -fexceptions`. Then again with the C and C++ objects put into two archives, the C++ archive linked first. Both runs printed exactly `run_one_header.out`'s six lines. `llvm-nm` shows `W wasi_python_fe_flags` in both objects. Exit 0 (EXECUTED).
  - A guest probe on main's set (`build/artifacts`, `SHA256SUMS` `f12cd25c`, plain binary) and the same program natively (`build/oracle/venv`, numpy 2.5.2 on OpenBLAS). It inverts 300 random integer matrices that are exactly rank-deficient (n from 3 to 7, rank below n, seed 99, half of them scaled by 0.1). It also inverts seven named near-singular matrices (EXECUTED; the numbers are in finding 1).
  - Counts from `compile_commands.json`: 198 entries, which are 166 C, 23 C++ and 9 `.pyx`. Every `.pyx` entry is a `cython` run, and the C it generates is compiled as its own `.c` entry. `npy_rename.h` appears once in each of the 166 C entries and in none of the C++ ones. No entry uses `-flto`. 140 C and 19 C++ entries use `-fvisibility=hidden`. All 189 compiled entries use `-O3` (EXECUTED).

## Acceptance criteria against evidence

The draft is judged on whether each criterion can be met and checked as written.

1. **The checks exist and were seen failing first.** Can be met. On main's set, checks 1 and 2 print `returned` and `returned silent` on the lines the spec names, on both binaries (EXECUTED by the author, `check*-guest-*.out`; READ here). Check 3 passes on main, as the spec intends. For check 4, main has no header, and 0 of 189 compiles carry it (READ, and matches my count). Check 4's gap is finding 3.
2. **The build.** Can be met. The mechanism covers every `fe*` call numpy compiles (READ; see *Mechanism* below). The header is the third recipe that `-include` adds. No script changes.
3. **The same bytes everywhere.** Can be met. `numpy/__config__.py` records absolute `-include` paths, but step 70 already makes it host-neutral, as it does for `npy_rename.h` (READ, `scripts/steps/70_zip.sh:3`, `scripts/make_stdlib_zip.py:87`).
4. **One word.** Can be met, and the prototype is good evidence. Weak definitions sit in every object, and the link keeps one. This held under numpy's real flags, under hidden visibility, with wasm exceptions, and with the objects in archives in either order (EXECUTED). No numpy compile uses LTO today. Under LTO, IR weak linkage would merge the copies the same way (INFERRED).
5. **The numbers recorded.** Can be met. Finding 1 adds the singular-detection probe to the facts the builder records.
6. **The judge.** Can be met. Finding 1 says which "no lost pass" claims are inferred and must be measured.
7. **The release.** Not applicable yet. This is a pre-build review.

### Mechanism (questions 1 to 3, 5 and 7 of the request)

- **Every path is covered** (READ). In the built tree only three places call `feraiseexcept`, `fetestexcept` or `feclearexcept`:
  - `ieee754.c.src`: `npy_get_floatstatus_barrier`, `npy_clear_floatstatus_barrier` and the four `npy_set_floatstatus_*`. This is C, so `c_args` covers it.
  - `float_status.hpp`'s inline `FloatStatus::Raise*`. Its only callers are in `half_private.hpp`, which `halffloat.cpp` uses. That file is C++, so `cpp_args` covers it. No file in numpy constructs a `FloatStatus` reader.
  - `ieee754.cpp`, which is not built: `numpy/_core/meson.build:653` builds the `.c.src`.

  So every raiser reaches the word: the integer, timedelta and modulo loops; complex `npymath`; `umath_linalg.cpp` through the C `npy_set_floatstatus_invalid`; and float16 casts through `npy_doublebits_to_halfbits` in `halffloat.cpp`. Every reader reaches the word too. No installed numpy header calls `fe*` (grep of `build/numpy-install`: none). So pandas and scipy need nothing.
- **scipy has its own cross file** (`recipes/wasi-scipy.cross`, step 57), so the force-include does not reach scipy's compiles. scipy calls no `fe*` function with a real mask. The one exception is Boost's `feclearexcept(FE_ALL_EXCEPT)`, which compiles to a call with mask 0. scipy reads numpy's status only through `PyUFunc_getfperr`. That is numpy's code, and it reads and clears the word. scipy's `.so.deps` name no npymath archive (READ). So the spec's claim that steps 50 and 57 are unchanged is plausible (INFERRED; the builder confirms by hash, as the spec says).
- **Snapshot and stale bits** (READ). Step 80 pre-imports no package (`80_snapshot.sh:3`, `PREIMPORT`, spec 069), so the word is 0 in the snapshot. Every numpy reader clears before it reads. The ufunc machinery and the casts clear before their loops. `umath_linalg`'s `get_fp_invalid_and_clear()` clears at the start of each loop (`umath_linalg.cpp:432`). Native numpy depends on this already, because hardware sets flags constantly. Bit `0x20` (`FE_INEXACT`) is never set: nothing calls `RaiseInexact`.
- **§4.1 holds.** This is a recipe (a force-included header plus a cross-file line). There is no patch and no pin, and a facts sheet is in folder 30, the next free number.
- **Question 106 is rightly kept out of scope** (Decision 4 (d)). It changes which LAPACK runs, not how a failure is reported. Finding 1 gives it a stronger argument than the draft does. Finding 2 is about where it is recorded.

## Findings, most severe first

1. **Medium. For `numpy.linalg`, "as natively" and "the software word holds a subset of what the hardware would" are not true.** (Decision 5, the paragraph that begins "Upstream suites"; also Intent, Decision 9's 044/045 bullet, the README bullet and the CHANGELOG line.) The subset argument holds for the integer, timedelta and float16 raisers, where the guest and native run the same code. It fails for `umath_linalg`. There, the guest's bundled `lapack_lite` and native's OpenBLAS disagree about which exactly-singular matrices report `info != 0`.

   Failure (EXECUTED; native numpy 2.5.2 on OpenBLAS against the guest on set `f12cd25c`; 300 exactly rank-deficient integer matrices, as in *Re-ran*):

   | native, guest today | count | after 099 |
   |---|---|---|
   | native raises, guest returns all-`nan` | 150 | fixed: the guest raises |
   | native returns finite, guest returns finite | 130 | unchanged |
   | native raises, guest returns finite | 12 | still silent; not `nan`s either, just wrong numbers |
   | native returns finite, guest returns all-`nan` | 8 | the guest raises `LinAlgError` where native returns (case indices 61, 94, 100, 185, 200, 219, 236, 248) |

   A named example of the third row: `np.linalg.inv(np.arange(1.0, 17.0).reshape(4, 4))` raises `Singular matrix` natively and returns finite numbers in the guest, before and after 099.

   So after the build the guest can raise where native does not. A test, golden or caller that passes natively with such a matrix would then fail in the guest. The spec's claims that "a test that passes natively passes here", that 044's and 045's goldens "matched native without the fallback", and that a program "never silently computes with `nan`s" therefore rest on inference, not evidence.

   The change is still a large net gain: 150 of 158 guest failures become native. Nothing here argues against the mechanism.

   **What closes it:**
   - Rewrite the Decision 5 argument to limit the subset claim to the non-LAPACK raisers.
   - Add a Decision 6 bullet stating both directions, with this probe's counts and the 4×4 example.
   - Qualify the Intent, the README bullet and the CHANGELOG line, for example: "raises `LinAlgError` when numpy's bundled LAPACK finds the matrix singular, as native numpy does on OpenBLAS for the cases checked; for a matrix singular only in exact arithmetic, the two LAPACKs can disagree, either way".
   - Have the builder run this probe (or a fixed list taken from it) on the new set and record it as facts in the landing notes.
   - Name the rows where a lost pass would show: `numpy-others` (`numpy/linalg/tests`), the matplotlib and scipy goldens that touch `numpy.linalg`, and pandas' groups. The lane's run is the evidence.
   - Add this divergence to question 106's case: on OpenBLAS the two LAPACKs would agree.

   Check 1's matrices are safe from this: `[[1, 2], [2, 4]]` meets an exact zero pivot in any LAPACK, and so does `cholesky` of `[[1, 2], [2, 1]]`.

2. **Low. Question 106 is cited but not recorded.** (*The owner's choices* 1, Decision 4 (d).) `context/questions-for-the-owner.md` says "Open: None" on this branch, and the latest numbers in use are 104 and 105. Fix text: add question 106 under *Open*. Say that nothing waits on it, give its default ("no, until answered"), and add finding 1's divergence as an argument for it. Or, if numbers are taken at build, say so in the spec. Per this project's memory, the lane asks the owner through AskUserQuestion.

3. **Low. Check 4's second part can be satisfied by the wrong build's records.** (*The checks* 4; `tests/harness/needs.py:110`.) `needs.need("compile records")` is met when any meson build has a `compile_commands.json`. Fix text: "the check reads `build/numpy-build/compile_commands.json` and fails, not skips, when that file is missing while the need is met". Also: "an entry is read when its command runs `wasi-cc` or `wasi-cxx` with `-c`, not by its file's extension". Today's extension rule gives the same 189 entries (EXECUTED), but a future `.S` or `.cc.in` source would escape it. Add a unit row for both points.

4. **Low. The drafting runs do not replay as written.** (`context/research/2026-10-20-numpy-floating-point-status/run_checks.sh`.) The script writes `$c-guest-$which.json`, but the folder holds `-guest-*.out` files whose first line was written by hand. Fix text: one line in the script, or in its header comment, saying how the `.out` is made from the `.json` (the `stdout` field, after a `# main set …: exit, trapped, stderr` line).

5. **Low. The draft widens the owner's answer without naming the narrower option.** (Decision 4.) The owner chose to fix the singular inverse. The draft also turns on warnings for integer division, integer overflow in division, timedelta division and float16 overflow. "One mechanism" is honest, but it can be split: giving only `FE_INVALID` a bit would fix `linalg`, and would also turn on timedelta `NaT` and complex `npymath`'s invalid. Fix text: add option (f), "only `FE_INVALID` real: refused, because native parity for numpy's own signals is the product's rule and a partial word is the odder state", so the owner sees the widening in the CHANGELOG and the README.

6. **Low. One fact in the facts sheet has no label.** (`facts.md`, *The short version*.) "and musl's on wasm32, which Emscripten shares" carries no source. Fix text: label it READ with the file read, or INFERRED, or drop it.

7. **Note. The fuel may go down, not up.** (Decision 5, "Fuel moves a little".) Today `fetestexcept(0)` is a real call into wasi-libc's out-of-line `fetestexcept`. The compiler cannot drop it, though it drops the result. After the change, the read is an inlined load and bit tests. Either direction fits the stated thresholds (0.1% and 0.5%). No change is needed beyond "moves" rather than "grows" in the claim text.

8. **Note. Upstream outcomes outside the pass digest may move.** Some numpy tests carry non-strict `xfail(IS_WASM)`: `test_umath.py:4437-4558` (complex branch cuts) and `test_regression.py:346`. These may change between xfailed and xpassed once complex `npymath`'s invalid flag is real. The judge treats non-strict xpass as upstream's own outcome (`tests/harness/upstream.py:628`). numpy's ini has no `xfail_strict`. pandas' has `xfail_strict`, but its only `WASM` xfails are `test_sas7bdat`'s tolerance cases, which are not floating-point signals. pandas' one non-skip `WASM` branch (`test_c_parser_only.py:96`) is a `nan`-to-int cast, a hardware signal that stays silent. The builder names any change in the per-outcome counts in the claim list.

## Constitution checks

- **§4.1:** holds. A recipe file and a cross-file line; no patch; a facts sheet with no upstream text sent.
- **§4.2:** holds. No new input.
- **§4.3 and §4.4:** hold. No host path, and no new import or export. Nothing the header adds is an import (prototype `llvm-nm -u`, READ).
- **§5.6:** holds. A pre-build review is required (recipe and artifact set), and this is it. The build review needs its own release-workflow run.
- **§7:** nothing tripped. No upstream tree is edited, no judge expectation is weakened, and no golden or allowance is edited. 066's class is emptied only on the stated condition and named in `--accept-judge`.

## Disposition (filled in by the author, then confirmed by the reviewer)

The author's answers, on `spec/099-numpy-singular-inverse` rebased onto main `21dff9d` (past `cf414a2`). The spec's section *Disposition of the pre-build review* holds the same, with pointers.

1. Finding 1 — **fixed in the text.** Decision 5 limits the subset argument to the non-LAPACK raisers and names where a lost pass would show: `numpy-others`, pandas' groups, the golden jobs that call `numpy.linalg` (`numpy_csv`, `modelling`, `scipy_numeric`, `scipy_lapack`, the plot goldens), and 044's and 045's goldens. Decision 6 gains a bullet with both directions: this review's counts (150, 130, 12, 8) and the author's own probe, `singular_probe.py` with a fixed seed (130, 141, 20, 12; EXECUTED, `singular_probe-crosstab.out`), with the 4×4 `arange` example and the author's case 26 for the other direction. The Intent, Decision 9, the README bullet, the CHANGELOG line and the accept flags now say "when numpy's bundled LAPACK finds the matrix singular". The builder records the probe as facts (criterion 5, the claim list). Check 1's two matrices are shown clear of it (exact zero and negative pivots). The owner answered question 106 meanwhile, "Both before 0.1.0": spec 100 (reserved, stacked on 099) moves numpy's linear algebra onto the set's OpenBLAS and is named as the closer of this divergence and of the `nan` matrix `ValueError`.
2. Finding 2 — **overtaken by the owner's answer.** Question 106 was answered before it went under *Open* (`context/decisions.md`, "numpy's linear algebra on OpenBLAS before 0.1.0 (question 106, 2026-10-20)"). *The owner's choices* cites that answer, and `questions-for-the-owner.md` stays "None".
3. Finding 3 — **fixed in the text.** Check 4 reads `build/numpy-build/compile_commands.json` and fails when it is missing while the need is met. It picks entries whose command runs `wasi-cc` or `wasi-cxx` with `-c` (189 on main's build, the same as by extension, EXECUTED). Check 5 gains rows for a `.S` file compiled by `wasi-cc -c`, a `wasi-cc` link without `-c`, and the missing file.
4. Finding 4 — **fixed.** `to_out.py` records the `.json` to `.out` conversion (a header line, then the `stdout` field) and makes the singular probe's cross table. `run_checks.sh` calls it and says so in its header.
5. Finding 5 — **fixed in the text.** Decision 4 (f), only `FE_INVALID` real, is refused for the reasons you gave. The CHANGELOG line names the widening.
6. Finding 6 — **fixed.** The facts sheet labels the Emscripten clause INFERRED, not read.
7. Note 7 — carried into the build: fuel "moves, up or down" in Decision 5, the claim list and the growth flag.
8. Note 8 — carried into the build: Decision 5 names the non-strict `xfail(IS_WASM)` tests, and the builder names any change in the per-outcome counts (criterion 5, the claim list).
9. A correction, added by the builder (2026-10-20, main `3ff1871`, `context/decisions.md`, "Correction and question 107"): the "native" numpy this review and the drafting runs called OpenBLAS was the oracle's `macosx_14_0_arm64` wheel, which uses Apple's Accelerate; the review's counts (150, 130, 12, 8) are against native Accelerate.

## Verdict

Passes for build once finding 1 (Medium) is answered in the text. The Lows are write-ins with their fix text and need no round. The mechanism is right and complete for the pinned numpy, and the single weak word holds under numpy's real flags. But for linear algebra the draft promises native behaviour that `lapack_lite` cannot give in either direction, so that promise must be qualified and measured, not inferred.

One line: the header is right, but for `linalg` "as natively" has to read "when numpy's own LAPACK says singular".

## Confirmation (2026-10-20, the same reviewer)

- **Read:** `spec/099-numpy-singular-inverse` at tip `e907bc3`, on main `21dff9d`.
- **Checked:** the diff `61c36c4..e907bc3` of the specification, the copied review's *Disposition*, `singular_probe.py` with its outputs, `to_out.py` and `run_checks.sh`.
- **Not run:** no build, no CI run and no judge tier. `build/lane.lock` was absent.
- **Review copy:** the body of the review copied to `context/reviews/099-numpy-singular-inverse-spec-2026-10-20.md` matches this file up to *Disposition* (EXECUTED, `diff`).

1. **Finding 1 (M1): sound.**
   - **The subset argument:** Decision 5 now limits it to the non-LAPACK raisers. For `umath_linalg` it says plainly that the argument fails.
   - **Where a lost pass would show:** Decision 5 names it (`numpy-others`, pandas' groups, the `numpy.linalg` golden jobs, the plot goldens, 044's and 045's goldens). A lost pass stops the entry and is never allowed.
   - **Decision 6:** it states both directions with both probes' counts and an example of each.
   - **The qualified wording:** the Intent, Decision 9, the README bullet, the CHANGELOG line and all three flags now say "when numpy's bundled LAPACK finds the matrix singular".
   - **The author's probe replays exactly** (EXECUTED). I re-ran `singular_probe.py` natively (`build/oracle/venv`) and in the guest (main's set `f12cd25c`, plain binary). Both outputs match the recorded `singular_probe-native.out` and `singular_probe-guest-plain.out` byte for byte. The crosstab's counts are 130, 141, 20 and 12, and case 26 is finite natively and all-`nan` in the guest. Its counts differ from my probe's (150, 130, 12, 8) because its entries run from −9 to 9 and it scales every second matrix. Both show the same two directions.
   - **Check 1 is clear of the divergence** (READ, and the arithmetic holds). LU of `[[1, 2], [2, 4]]` with partial pivoting gives 2 − 0.5 × 4 = 0 exactly. Cholesky of `[[1, 2], [2, 1]]` gives 1 − 2² = −3. So check 1 holds on any LAPACK, spec 100's OpenBLAS included.
   - **The closer:** spec 100 is reserved in the roadmap (line 129) on the owner's recorded answer to question 106 (`decisions.md:64`). It is a proper closer.
2. **Finding 2: overtaken, accepted.** The owner answered question 106, and the answer is cited.
3. **Finding 3 (L3): check 4 is now right.**
   - **The missing-file case:** the check reads `build/numpy-build/compile_commands.json` itself and fails, not skips, when that file is missing while the need is met.
   - **The compiler rule gives 189** (EXECUTED). Entries whose first argument ends in `scripts/wasi-cc` or `scripts/wasi-cxx` and that contain `-c` number 189 of main's 198, the same as the extension rule. The nine `cython` runs fall out.
   - **The unit rows** cover the `.S` file, a link without `-c`, both record shapes, empty records and the missing file.
   - **One point for the build review:** the spec says "runs `scripts/wasi-cc`". So the implementation should match the command's first argument by path suffix, as I did, and not a bare substring anywhere in the command.
4. **Findings 4 to 6: fixed** as stated. `run_checks.sh` now calls `to_out.py` through `uv run`. The facts sheet's clause is labelled INFERRED. Decision 4 (f) is written in, and the CHANGELOG names the widening.
5. **Notes 7 and 8:** carried into the build, in Decision 5, criterion 5, the claim list and the growth flag.

**Verdict: confirmed for build.** No finding remains open.
