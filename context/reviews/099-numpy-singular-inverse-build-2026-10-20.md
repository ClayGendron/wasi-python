# Review of 099 — numpy's own floating-point signals are kept in software, so a singular matrix raises `LinAlgError` (the build)

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent (Claude), not the author. It did not write 099 and did not review it before the build.
- **Reviewed:** `spec/099-numpy-singular-inverse` at `f7448c7`. Its own commits are `94b5cb8..f7448c7` on main `3ff1871`; the code diff is `3ff1871..f7448c7`. It was built on `21dff9d`. Main has since moved to `2516875` (wave 07), and that is weighed under M1.
- **Time box:** 45 minutes (build-class), plus the wait for CI.
- **Run:** 39442912523, the reviewer's own release-workflow run on `f7448c7`. EXECUTED and read back: 24 jobs passed, 4 skipped, and 1 red, `judge (macos-15, own-guest)` (`384/758 pass · 6 gap · 2 blocked · 0 fail`; ratchet `lost 0 · absent 0 · gained 7 · grew 15`; no G7 line). Its 15 grown rows equal the builder's run's 15, row for row and number for number (`diff` of the two records' growth lists). Checks 1 to 3 passed in all three systems' own-guest shards, and check 4 in the build job. Every Windows job is green.
- **Builder's run read back:** 39432450036 on `b0e1593`. 24 jobs passed, 4 were skipped (gather and the three release-only jobs, as a red judge makes them), and 1 was red: `judge (macos-15, own-guest)`. Its ratchet: `lost 0 · absent 0 · gained 7 · grew 15`, with no G7 line. The reviewer recomputed the 15 grown rows from that shard's record against `b0e1593`'s `accepted.json` (fuel tolerance 1e-4, darwin-arm64 metrics). They are exactly the claim list's 15: the zip +15 bytes, and fourteen fuel rows from +0.0103% to +0.0330%. That is growth only.
- **Re-ran (EXECUTED, `build/lane.lock` absent, `df -h ~` 54 GiB free):**
  - Unit rows: `uv run pytest tests/unit/test_scan.py -k npy_fenv` → 6 passed, exit 0.
  - Three check nodes on the worktree's set (`SHA256SUMS` 7519b047): `test_every_numpy_compile_keeps_its_floating_point_flags_in_software`, `test_numpys_own_floating_point_signals_reach_errstate[snapshot]` and `test_a_singular_matrix_raises_linalgerror[plain]` → 3 passed, exit 0, `grew 0`.
  - Three probes in the guest, on both binaries (scratchpad scripts, `wasi-python run`).
  - The flag word read from both binaries' data segments.
  - Main's weak-duplicate gate (`2516875:scripts/weak_duplicates.py`) run on 099's numpy archives.
  - A side effect: the node run replaced the worktree's `build/progress/latest.json` (git-ignored, not committed) with a 3-node record. The builder's fast-tier output is still in `build/099/fast.log`.

## Acceptance criteria against evidence

1. **Checks exist and were seen failing first** — met (READ). `build/099/seen-failing-first.log` is described in Phase 1: checks 1 and 2 fail on main's set, check 3 passes by design, check 4 fails on its first part, and on main's records there are 189 findings, one per compile.
2. **The build** — met on its base (READ plus EXECUTED in part).
   - 18 steps from an empty `build/`. 419 warnings, the same as main's.
   - `MANIFEST` differs by three lines. `LICENSES/` is unchanged.
   - Only numpy's 19 archives differ.
   - The reviewer's CI run rebuilt it from empty (`build and judge (arm64 macOS)` green on `f7448c7`).
3. **The same bytes everywhere** — met (READ, 39432450036). Both Linux rebuilds and "the same bytes from every host" pass. They pass again in run 39442912523, on `f7448c7`.
4. **One word** — met (EXECUTED).
   - `build/link/python.map` names `wasi_python_fe_flags` once: 4 bytes of `.bss` at `0x1956258`, from `dragon4.c.o`.
   - Neither `python.wasm` nor `python-snapshot.wasm` has a data segment covering that address. So the snapshot holds the word at 0.
   - The guest's imports are unchanged: `tests/public_api.txt` is not in the diff, and the import checks passed in both runs.
5. **The numbers recorded** — met (READ).
   - Sizes: −260, −256 and +15 bytes.
   - The fuel of checks 1 to 3, and every moved row named.
   - The upstream counts are recorded. The reviewer checked numpy-others, pandas-reshape, cpython-archives (Linux), and numpy-lib and cpython-fs (macOS): outcome counts and passed digests equal wave 06's dry run 39398491514 (EXECUTED, the shards' `latest.json`).
   - `singular_probe`'s four counts, labelled "against native Accelerate", with an example of each row. They are the same on both binaries (EXECUTED, `diff`): 130 (case 4), 141 (case 0), 20 (case 2, and `inv(arange(1,17).reshape(4,4))`), 12 (case 26).
   - `fp_probe`'s `nan` lines, and B1.
6. **The judge** — met. The local fast tier: 0 fail, lost 0, gained 7, grew 12. All 12 are among the CI run's 15, and each is claimed.
7. **The release** — met on `b0e1593`: red only on growth. The reviewer's run on `f7448c7`: red only on the same 15 growth lines.

## Findings, most severe first

1. **M1 (Medium): after the rebase onto main, the flag word stops step 60** (`recipes/npy_fenv_flags.h:122`).
   - **The defect.** Main `2516875` (wave 07, spec 044, Decision 6) added a gate to step 60: `scripts/weak_duplicates.py archives`. It stops the link on any global weak definition that two archives share, unless `recipes/weak-duplicates-allowed.txt` allows it. 099 defines `__attribute__((weak)) int wasi_python_fe_flags` in every numpy object, so 13 of numpy's archives define it weakly.
   - **The failure (EXECUTED).** Main's gate was run on 099's numpy archives. It printed `ERROR: weak definition shared by 13 archives: wasi_python_fe_flags: numpy__bounded_integers.a (weak), numpy__common.a (weak), … numpy_lapack_lite.a (weak) …` and `1 unreviewed`. So 099, once rebased for wave 08, does not build. The textual merge is clean (`git merge-tree`), so nothing warns before the build.
   - **Weighing the allow-list.** The list says never to list "a weak definition with C linkage … that keeps state of its own file". This word is C-linkage state, but sharing it across files is its purpose, and every copy is the same zero-initialised `int`. So listing it is defensible with that reason. A single strong definition is cleaner and needs no exception: the header says `extern int wasi_python_fe_flags;`, and a recipe C file linked once defines it, as step 60 already links `iconv_refusals.c`. That route also lets step 60's `link-map --require wasi_python_fe_flags` hold the one definition.
   - **What closes it.** On the rebase onto main's tip:
     - either the list entry with its reason, or the single definition with check 4's header regex and unit row updated;
     - a build from empty that passes step 60's gate;
     - `python.map` showing one definition;
     - a new dry run read back, with the claim list and flags re-derived on the wave 07 set (every size and fuel number in them changes with the rebase).
2. **B1 (answered; no finding): `lstsq` of a `nan` matrix raises `SystemError`.** The reviewer accepts shipping it on main until spec 100, for four reasons:
   - **It never returns silently.** It is still an exception, and the CHANGELOG and README name it.
   - **The interpreter stays sound (EXECUTED, both binaries, 300 iterations).**
     - Every iteration raised `SystemError` with a `ValueError` context.
     - After the loop: `sys.exc_info()` is empty, `np.geterr()` is restored, `LinAlgError`'s refcount moved by 0, and `sys.getallocatedblocks()` moved by 0.
     - Under `errstate(all="raise")`, an array add, an int add, a scalar multiply and a float16 cast raise nothing. So no flag is left set.
     - Afterwards `lstsq` of a good matrix is correct, a singular `inv` raises `LinAlgError`, and int `// 0` warns.
     - Other exceptions and imports behave normally.
     - The cause is CPython's `_Py_CheckFunctionResult` guard. It catches a call that returned while an error was pending. It does not signal corrupted state.
   - **No clean recipe exists.** `python_xerbla` sets the exception inside `lapack_lite`. Masking `fetestexcept` while `PyErr_Occurred()` would only move the `SystemError` to the gufunc's own return. A patch is spec 100's territory.
   - **The gate before a tag is in place.** Spec 100, built and stacked on 099, carries the check that turns this into native's `LinAlgError` (`test_v1_3_data_stack.py` on its branch, "099's B1, lstsq's SystemError"). The owner placed 100 before 0.1.0 (questions 106 and 107), and the roadmap orders it right after wave 08. No tag falls between them.
   - **One regression to note.** On main, `except ValueError` caught this case. After 099 it does not, until 100. It is acceptable only because 100 lands before any tag. If 100 slips past the next tag, this becomes a High.
3. **L1 (Low, context only): *The judge's changes* names a function that does not exist** (`context/specifications/099-numpy-singular-inverse.md:426` in *Design*'s table, `:533` in check 5, and `:586`). Each names `numpy_fenv_errors`; the diff has `npy_fenv_recipe_errors`, `npy_fenv_record_errors` and `npy_fenv_records_file_errors`. Fix text: at 426 and 586, "`tests/harness/scan.py`: `npy_fenv_recipe_errors`, `npy_fenv_record_errors` and `npy_fenv_records_file_errors`"; at 533, "where `npy_fenv_record_errors` does not exist".
4. **L2 (Low, context only): `--accept-growth` leaves out one `MANIFEST` line.** It says "MANIFEST one recipe line added, one changed". The landing notes count three (the snapshot's `x-snapshot-zip` too). Fix text: "MANIFEST one recipe line added, one changed, and the snapshot's x-snapshot-zip line". The flag is re-derived on the rebase anyway (M1).
5. **Note N1, for the lane.** Decision 9 has whichever of 099 and 044 lands second re-run 044's goldens. 044 is now on main, so that is 099. Wave 08's integration run is the evidence: a lost scikit-learn golden is a finding, never an allowance.

## Focus items, answered

- **The flag word:** one definition in the link, 0 in both binaries' data (criterion 4). Every numpy reader of the status reads after a clear in the same operation (READ, `build/numpy-2.5.2`): the ufunc loops (`ufunc_object.c` 992, 1176, 2127 and others, then `extobj.c:541`), casts and assignment (`array_assign_*.c`, `dtype_transfer.c:3416/3433`, `array_coercion.c:415/429`, `ctors.c`, `mapping.c`), scalar math (`scalarmath.c.src:1259/1294`), and `umath_linalg.cpp:436/447`. The first status reads after start, under `errstate(all="raise")`, raised nothing on both binaries (EXECUTED).
- **Blast radius:** no golden is in the diff. Upstream outcome counts and passed digests equal wave 06's (EXECUTED, five groups from two shards). The new integer, timedelta and float16 warnings appear only in checks 1 to 3.
- **Check 4:** a record counts as a compile when its first argument equals, or ends in `/` followed by, `scripts/wasi-cc` or `scripts/wasi-cxx`, and the command holds `-c` (`tests/harness/scan.py:470-477`). Unit rows cover the near misses: a link without `-c`, `-DX=scripts/wasi-cc` elsewhere in the command, the lookalike `scripts/not-wasi-cc`, a `.S` compile, both record shapes, and no records at all. CI's build job: `compiles 189, c 166, c++ 23, not compiles 9`, passing.
- **Question 107's correction:** applied in the README bullet (OpenBLAS natively, Accelerate in the macOS 14 arm64 wheel), the CHANGELOG ("exact parity is not a goal"), the spec's Decisions 6 and 9, the owner's choices, the landing notes, `singular_probe.py`'s docstring and `fp_probe-native.out`'s header. No sentence left calls native OpenBLAS the probes' reference (EXECUTED, grep).
- **Claims and flags:** the 12 local red lines are a subset of the CI run's 15, and all 15 are in the claim list with their numbers. The three flags each begin "099" and contain no `"`, `$`, backtick, `!` or backslash (EXECUTED).

## Self-check

Every item is present and checked. The CHANGELOG sits under main's one unreleased heading, `0.1.0a8 — unreleased`. Nothing is unchecked.

## Constitution checks

- **§4.1:** no patch. The adaptation is a recipe file, force-included by the cross file, with its removal condition and an `#error` for the day wasi-libc defines the flags. Holds.
- **Pins:** no new input, and `downloads/SHA256SUMS` is unchanged. Holds.
- **The artifact set and the guest's imports and exports (§5.6):** imports and exports are unchanged. The set changes and is recorded by hash, with a pre-build review and its Confirmation. Holds.
- **Tests count operations:** the new checks compare text, and fuel is recorded. Holds.
- **Never weaken the judge:** no golden, gap, allowance or progress file is edited. Holds.
- **§7:** nothing tripped. The upstream facts sheet (folder 30) keeps any text to numpy in the owner's words.

## Disposition (filled in by the author, then confirmed by the reviewer)

The builder's answers, on `spec/099-numpy-singular-inverse` rebased onto main `2516875`.

1. M1 — **closed by the allow-list.** The rebase replayed every commit with no conflict hunk. `recipes/weak-duplicates-allowed.txt` gains `wasi_python_fe_flags` with its reason: every copy is the same zero-filled 4-byte int, and sharing one object across files is the point, not state of one file. It touches `recipes/` only, not step 60, which spec 100 also edits. The rebuild from empty on `4fac7e2` passed step 60's gate (`270 archives, 21964 weak names, 0 unreviewed, 0 stale patterns`), and `python.map` names the word once (4 bytes of `.bss`, `dragon4.c.o`). The claim list and the three flags are re-derived on wave 07's set (`dc6ba3a5` → `5f203242`) from the fast tier and dry run 39454475153 on `6866dd1` (the spec's *Landing notes* and *For the lane*).
2. L1 — **fixed.** *Design*, check 5 and *The judge's changes* name `npy_fenv_recipe_errors`, `npy_fenv_record_errors` and `npy_fenv_records_file_errors`; *Design* also lists the allow-list file.
3. L2 — **fixed.** `--accept-growth` names every `MANIFEST` line: the header's new `recipe` line, the two changed `recipe` lines (`recipes/wasi-numpy.cross`, `recipes/weak-duplicates-allowed.txt`) and the snapshot's `x-snapshot-zip`.
4. N1 — written into *For the lane*: wave 08's integration run is the evidence that 044's goldens re-run with 099; a lost scikit-learn golden is a finding, never an allowance.
5. B1 — answered by the review; nothing to change. The README and CHANGELOG keep naming it, and spec 100 carries its check.

## Verdict

Lands once M1 is closed: rebased onto main's tip, the flag word passes spec 044's weak-duplicate gate (listed with its reason, or defined once), with a build from empty, one definition in `python.map`, and a dry run read back with the claim list and flags re-derived.
