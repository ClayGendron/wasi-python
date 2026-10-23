# Review of wave 08's integration (042, 066, 099)

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent (Claude). It wrote none of 042, 066 or 099 and reviewed none of them before. It is the wave's integration reviewer (AGENTS.md rule 8; constitution §5.7).
- **Reviewed:** `wave/08` at `72bc5ed` (pushed): 042, then 066, then 099, rebased by the lane onto main `5805af0`.
- **The lane's set:** rebuilt in the main tree from `wave/08`. `SHA256SUMS` hashes to `b5a66245…` (EXECUTED: `shasum -a 256 build/artifacts/SHA256SUMS`). `python.wasm` 93,793,595 bytes, the snapshot 98,682,976, the zip 49,771,987 (`build/wave-08/build.log`, 19 steps, exit 0).
- **Ran:** reads only, while `build/lane.lock` existed. `git range-diff` for the wave and each entry; the flags parsed from `build/wave-08/flags.json` and `build/wave-08/accept.sh`; the CI records of runs 39421194888 (042), 39415728849 (038, 042's base), 39451333969 (066, run 124) and 39454475153 (099, run 125), downloaded with `gh run download` into this scratchpad and compared row by row (`predict2.py`, `prediction.json`). No judge tier ran. Nothing was dispatched.

## 1. The prediction (written 2026-10-20 14:42 EDT, before reading the accept's result)

(Written at 14:42 EDT, before the accept ended. Only the two finding references were renumbered afterwards; no number or row changed.)

It is made from the three entries' claim lists and *For the lane*, `accepted.json` (wave 07, `1cd25e2`, set `dc6ba3a5`), and the entries' CI records. Run 124 changed no artifact byte. So its macOS records are wave 07's set on CI. 233 of its fuel rows equal `accepted.json` exactly, and none differ (EXECUTED). So CI's macOS fuel can stand for this machine's.

Method, per fuel row: the wave's value is predicted as accepted + 042's delta + 099's delta.
- 042's delta: run 39421194888 minus 038's run 39415728849, macOS records. Where a row has no macOS record in both (the upstream groups other than `cpython-fs` and `numpy-lib`), the Linux records of the same runs. Where neither run has the row (044's scikit-learn rows), the start cost 042 measured: plain +4.83 M, snapshot +0.53 M.
- 099's delta: run 125 minus run 124, macOS records, else their Linux records.
- Growth is above the ratchet's tolerance, `FUEL_TOLERANCE = 1e-4` (`tests/harness/scoreboard.py`).

### The scoreboard

| | predicted |
|---|---|
| rows | 850 (wave 07's 769, 042's 11, 066's 63, 099's 7; 099's own fast tier on the wave counted 850) |
| pass | **763**: 704 + 11 (042) + 41 (066: 40 groups, and `matplotlib-rest-b1-no-fp-exceptions`, emptied by 099, as a pass) + 7 (099) |
| gap | **85**: wave 07's 63 + 066's 22 (23 classes less the emptied one; `known_gaps.toml` holds 85 `[[gap]]` entries, EXECUTED) |
| blocked | 2, as in wave 07 |
| fail | **0** |
| per goal | rules 45/45 · v1.1 45/46 · v1.2 160/161 · v1.3 233/318 · v1.4 230/230 · v1.5 50/50 |
| unit suite | 1,878/1,885 (099's fast tier on the wave) |

### The ratchet: lost 0 · absent 0 · unrun 0 · fewer 0 · gained 59 · grew about 231

- **lost 0, absent 0, unrun 0, fewer 0.** No check is retired. No accepted upstream group changes its passes: numpy's, pandas' and CPython's groups have the same passes in all four runs (EXECUTED, the Linux and macOS records; 099's own comparison against wave 07's dry run says the same of the outcome counts and digests).
- **gained 59:**
  - 042, 11: `test_statistical_plots_job_matches_native`, `test_pdf_reports_job_matches_native`, `test_reportlab_runs_its_pure_paths[plain, snapshot]`, `test_seaborn_takes_its_scipy_paths[plain, snapshot]`, `test_reportlab_fonts_are_not_in_the_zip`, `test_seaborn_notice_carries_its_vendored_licences`, `test_reportlab_notice_carries_its_third_party_parts`, `test_reportlab_writes_a_pdf_with_nothing_writable`, `test_source_tree_matches_its_tarball[seaborn]`. Its four unit checks are in the unit suite.
  - 066, 41: `test_upstream_suite[<group>]` for the 40 groups, and `test_upstream_class[matplotlib-rest-b1-no-fp-exceptions]` (empty list, passes: 099's Decision 7). The other 22 class rows are new gaps, not gains.
  - 099, 7: checks 1 to 3 on both binaries and check 4.
- **grew, bytes, 2:**
  - the zip, `test_stdlib_zip_is_bytecode_only_and_deflated`: 47,730,899 → **49,771,987** (+2,041,088 = 042's +2,041,073 and 099's +15, exactly the lane's file);
  - the snapshot, `test_binary_is_a_core_wasm_module[snapshot]`: 98,620,293 → **98,682,976** (**+62,683**). That is 042's members and 099's −260. 042 measured +74,056 on 038's base; on wave 07's base its share is +62,943. Smaller than claimed (L2).
- **grew, fuel, about 229** of the 249 accepted fuel rows (the model: 229 up, 6 down, 14 within the tolerance):
  - **214 rows from 042's macOS deltas**, every one in 042's claim list: every guest row by the 199 members' start cost (plain about +4.8 M, so +1.9% on a bare start; snapshot about +0.5 M); the four zip-walking rows of `test_v1_3_the_zips_directory.py` (+2.7% to +3.3%, the largest); the pure-paths scan; networkx; the metadata readers; scipy's importers on the snapshot; `plot_contour` and `scipy_numeric` snapshot; the reread (+8.68 M). 099's 21 claimed rows are all among them, its delta added (+0.011% to +0.085%).
  - **6 scikit-learn rows** that neither 042 nor 038 ran (044 landed after 042's base), by 042's start cost and 099's macOS delta: `test_scikit_learn_runs_without_threads[plain]` (+0.036%), `test_scikit_learn_modules_are_builtin[plain]` (+0.033%), `test_scikit_learn_reads_its_files_from_the_zip[plain]` (+0.033%) and `[snapshot]` (+0.027%), `test_machine_learning_job_matches_native[plain]` (+0.027%) and `[snapshot]` (+0.018%). Borderline: `test_scikit_learn_modules_are_builtin[snapshot]` and `test_scikit_learn_runs_without_threads[snapshot]` (−0.004% to +0.014%: they import scipy, which reads metadata, +1.67 M in 042's probe). An interaction: 042's claim covers them in kind ("every guest fuel row"), not by row.
  - **9 upstream groups, estimated from Linux** (an interaction no entry measured on darwin):
    | group | 042 (Linux) | 099 (Linux) | predicted |
    |---|---|---|---|
    | `pandas-frame` | +547 M | +126 M | +0.19% |
    | `numpy-core` | +55 M | +212 M | +0.17% |
    | `pandas-reshape` | −22 M | +159 M | +0.13% |
    | `cpython-c` | +371 M | +126 M | +0.12% |
    | `numpy-others` | +47 M | +147 M | +0.11% |
    | `pandas-libs` | +6 M | +23 M | +0.11% |
    | `cpython-b` | +244 M | 0 | +0.08% |
    | `pandas-tslibs` | +4 M | +13 M | +0.04% |
    | `pandas-internals` | +6 M | +3 M | +0.04% |
    and **`cpython-fs`** from 042's macOS delta (+75.7 M) and 099's Linux one: +0.09%.
    042's reason (each guest the group starts pays the members' start cost) and 099's (numpy's
    status read is now an inlined load and bit tests, either way per ufunc call) hold for them.
    But 042's flag names only `cpython-fs` and `numpy-lib`, and 099's says "the rest within 0.01%
    or down". So any of these that grows is named here first (M2).
  - Within the tolerance or uncertain: `numpy-lib` (+0.007%), `cpython-a` (0.000%), `pandas-io-parser` (−0.005%). `cpython-archives` is not predictable from CI: its Linux fuel moved −1.6% between runs 124 and 125, which differ only by 099 (noise or a timing-bound test; its darwin value rose in each of the last three accepts).
- **fell (recorded, not red):** `test_binary_is_a_core_wasm_module[plain]` 93,793,855 → 93,793,595 (−260, 099); `test_plot_line_job_matches_native[snapshot]` (−0.028%), `test_dotted_builtins_keep_their_import_names[snapshot]` (−0.023%), `test_unbuffered_output_survives_a_hard_exit[snapshot]` (−133, −0.010%, borderline); from Linux, `pandas-groupby` (−0.08%) and `pandas-io-formats` (−0.04%).
- **The judge changed:** the files of the three `--accept-judge` texts.

### The new rows' own numbers (not ratcheted: new metrics)

- 066's 40 groups: each about 066's darwin measurement on `dc6ba3a5` plus 042's start cost per guest it starts (plus a little where pytest reads every distribution's entry points: two more distributions), far inside each 1.5× cap. Passes: **17,974**, 066's 17,972 with `matplotlib-rest-b1` at **3,369** (099: its two `test_mlab` cases now raise `LinAlgError`). Every other group's passes equal 066's table.
- **The untested interaction:** 099 ran only `matplotlib-rest-b1` of 066's 40 groups. matplotlib's and contourpy's suites run numpy heavily and, natively, with warnings as errors. 099's argument (a signal the guest now gives is one native gives at the same place) covers the non-LAPACK signals. It does not cover `lapack_lite` (099's Decision 6): a test that inverts a matrix singular only in exact arithmetic may newly raise. So the lane's run is the first evidence for 39 groups. Prediction: all pass, the passes as above. Any group that fails or has fewer passes is a finding against 099, never an allowance.
- 042's two jobs equal their goldens with 099 in the set: `statistical_plots` reaches `numpy.linalg` only through calls that succeed (099 changes nothing unless LAPACK reports a failure). 044's `machine_learning` golden passed with 099 in run 125 on all three systems.
- `test_goldens_reproduce_under_the_pinned_oracle` passes on the lock the lane regenerated.
- **A host risk, not a result:** `matplotlib-mathtext` was voided twice by host litter (`.DS_Store` in the guest root) in 066's rebuild. The accept log's first line reports 30 sealed folders under `build/harness` (which the run says it never reads). A group voided by a `HostLitter` line is a host failure, re-run once the litter is gone (066's *For the lane*).

## 2. What the accept did (attempt 1, refused)

The lane's first attempt ended at 14:55 after 20 min 28 s and was **refused**. The lane renamed its log and record to `build/wave-08/accept-attempt1-void.log` and `latest-attempt1-void.json`. Nothing was accepted: `git diff -- context/progress/` is empty (EXECUTED). This review compares that record with the prediction. The record is the wave's own numbers on `b5a66245`, apart from the rows the host voided.

`wasi_python v1: 760/850 pass · 84 gap · 3 blocked · 3 fail (unit suite 1883/1885, 2 skipped)` `ratchet vs e9a76ce1aa: lost 1 · absent 0 · unrun 0 · unrun locally 1 · gained 58 · grew 235`

| | predicted | attempt 1 | the difference |
|---|---|---|---|
| pass | 763 | 760 | −3: the three rows below |
| gap | 85 | 84 | the mathtext class failed with its group |
| blocked | 2 | 3 | `test_goldens_reproduce_under_the_pinned_oracle`: `needs oracle` (M1) |
| fail | 0 | 3 | `test_upstream_suite[matplotlib-mathtext]` and its `no-processes` class: `HostLitter`, `/.DS_Store … /tmp/work/result_images/.DS_Store (after the run)`; `test_the_openblas_patches_are_what_their_script_makes`: `git rm --cached` refused a `.DS_Store` (L1) |
| lost | 0 | 1 red (openblas, host litter) and 1 unrun locally (the oracle, not red) | |
| gained | 59 | 58 | mathtext's group, voided |
| grew | about 231 | 235: 2 bytes and 233 fuel rows | below |
| fewer | 0 | 0 | |
| fell | python.wasm −260 and about 5 | 3: python.wasm −260, `plot_line[snapshot]` −0.015%, `scipy_solvers[snapshot]` −0.019% | |

So every difference from the prediction is a host failure or the oracle's block. No entry's check fails. No pass is lost to an entry.

### The numbers against the prediction (EXECUTED: `compare.py`, `compare-attempt1.txt`)

- **Bytes:** the zip 49,771,987 (+2,041,088) and the snapshot 98,682,976 (+62,683), as predicted; python.wasm −260.
- **The lane's set is 099's set plus exactly 042's members.** python.wasm is the same bytes (`ee45b241…`) as 099's worktree build. The zip holds 099's 5,473 members unchanged (CRC and size) and adds 199, equal to `build/042/names.txt` (reportlab 143, seaborn 54, two `METADATA`). `MANIFEST` differs by 042's two `package` lines, two `pin` lines, three `recipe` lines (its scripts) and `x-snapshot-zip`; `LICENSES/` by `seaborn.txt` and `reportlab.txt` (EXECUTED).
- **Fuel, 233 rows grew.** 213 move as 042's and 099's macOS records say (each entry's claim, within about 2 M on a snapshot row, the layout 042 names). The rest are interactions:
  - **The scikit-learn rows, 8** (044 landed after 042's base, so neither 042 nor 099 claims them by row): `test_scikit_learn_reads_its_files_from_the_zip[plain]` **+0.218%** (+38.2 M) and `[snapshot]` **+0.191%** (+32.6 M); `test_scikit_learn_runs_without_threads[plain]` +0.087% and `[snapshot]` +0.043%; `test_machine_learning_job_matches_native[plain]` +0.061% and `[snapshot]` +0.048%; `test_scikit_learn_modules_are_builtin[plain]` +0.039% and `[snapshot]` +0.014%. The first two are well past the start cost the prediction gave them (+0.033%, +0.027%). INFERRED from the check: `all_estimators()` walks every sklearn package with `pkgutil`, and listing a package in a zip reads the whole member directory, so it grows with the member count, as 042's other zip-walking rows do.
  - **Upstream groups, 12 grew on darwin:** `cpython-fs` +0.159% (inside 042's "0.2 percent"), `pandas-libs` +0.090%, `pandas-reshape` +0.075%, `cpython-archives` +0.063%, `pandas-frame` +0.059%, `pandas-internals` +0.048%, `cpython-c` +0.046%, `cpython-a` +0.041%, `pandas-groupby` +0.039%, `numpy-others` +0.033%, `pandas-io-formats` +0.030%, `pandas-tslibs` +0.024%. `numpy-core` +0.007%, `numpy-lib` +0.004%, `cpython-b` +0.003% and `pandas-io-parser` +0.003% are inside the tolerance. The prediction had the direction for nine and the magnitude for few: Linux deltas are a poor guide to darwin's upstream fuel (`numpy-core` predicted +0.17%, measured +0.007%). Each is 042's start cost per guest and 099's status reads, in kind. Neither flag names them by row (M2).
  - **Small snapshot rows** predicted flat that grew by +0.010% to +0.075% (`matrix_market`, `ctypes_values_scipy_makes`, `scipy_odr`, `sobol_needs_nothing_writable`, the iconv workaround, `unbuffered_output[snapshot]` +708 fuel): 042's and 099's snapshot layout moves do not add; within the "about 2 M by layout" 042 claims.
- **066's 40 groups with 099 and 042 (the untested interaction): as predicted.** 39 groups ran (mathtext voided). Every one passes. Every one has 066's passes, except `matplotlib-rest-b1`, 3,367 → **3,369**. With mathtext's 985 that is **17,974**. Fuel is within +0.19% of 066's measurement on `dc6ba3a5` (`mpl-axes_grid1` the most), far inside each 1.5× cap. `test_upstream_class[matplotlib-rest-b1-no-fp-exceptions]` passes with its empty list; the other 21 classes that ran are gaps. No group lost a pass to 099's `lapack_lite` path.
- **042's and 099's new checks:** all eleven and all seven pass. `statistical_plots` and `pdf_reports` equal their goldens with 099 in the set; checks 1 to 3 pass with 042's members. 044's `machine_learning` golden passes too (099's N1).

### Sameness (rule 6a)

`tests/harness/sameness.py` is read-only: it reads two JSON records, prints the differences and exits 0, 1 or 2; it writes nothing (READ, its `main`). No reviewer's record exists on `b5a66245`: under the owner's rule no entry ran CI after its rebase. So I ran it once, between run 124's merged record (066 on `dc6ba3a5`) and attempt 1's record, to show every difference has a cause (EXECUTED, `sameness-124-vs-attempt1.txt`: 260 lines, exit 1):
- 224 fuel lines and 3 bytes lines: the grew list above;
- 22 rows only in the second record: 042's 11 and 099's 7, among them;
- `rest-b1` passes 3,367 → 3,369 and its class gap → pass: 099;
- the closers of `contourpy-config-1-text-rendering` and `pillow-fli-overflow-native`: 066's confirming review's L2, written after run 124 (066's notes say so);
- mathtext and openblas: the host failures; `test_wheel_carries_the_artifact_set`: blocked locally, as always;
- the unit suite 1,875 → 1,885: 042's four and 099's six unit rows. What the lane should run after the wave's dry run (spec 092 has landed, so the merged record reads): `uv run python tests/harness/sameness.py <dry run's release-record-1/record.json> build/progress/latest.json`. A clean result is every line a blocked-locally row or a claim.

## 3. The rebases (EXECUTED, `git range-diff`)

- **The wave onto main `5805af0`:** `2516875..f340225` against `5805af0..72bc5ed`: all 34 commits `=`. Main's three new commits touch only `AGENTS.md` and `context/` (EXECUTED, `git diff --stat 2516875 5805af0`).
- **042 onto `2516875` (the lane's rebase):** `ecc2423..b8dd5a4` (the reviewed code `3c0b11d`, the notes `69b3e34`, the review's answers) against `2516875..38be0b2`. Commits 2 to 4 are `=`; commit 5 (`38be0b2`) is context only. Commit 1 differs only in the named files, and every hunk keeps both sides: `release.yml` (the count 27, `^27 passed`, the comment "twenty-seventh"), `README.md`, `assemble_artifacts.py` (`PACKAGES`), `70_zip.sh` (the comment paragraphs, `--metadata`, the four `--drop`s in order, `--keep` once), `test_v1_3_data_stack.py` (sorted, both specs in the comment), `artifacts.py` (044's `return errors` kept), `jobs.py`, `needs.py`, `paths.py`, `pins.py`, the oracle's `pyproject.toml` and `uv.lock`, `test_v1_1_artifact_set.py` and `test_artifact_rules.py` (context lines only). Two of 042's hunks vanished because main made the identical change (the `needs` import in `test_v1_3_default_profile.py`, the `xz` line's format in `assemble_artifacts.py`): no effect. `tests/jobs/statistical_plots.py` is byte-identical. The zero-patch count is right: `needs.SOURCE_COMPONENTS` holds 26 names on main and 27 on the wave, so `release.yml`'s `^27 passed` is right and the lane's 26 → 27 correction is right.
- **066 onto `38be0b2`:** `2516875..7382bf1` against `38be0b2..66cc120`: all twelve `=`; `66cc120` touches only its spec.
- **099 onto `66cc120`:** `2516875..d91b219` against `66cc120..f340225`. Commits 3, 4 and 5 differ, only in `CHANGELOG.md`, `README.md` and `context/upstream/README.md`: the five named hunks (rows 30, 32, 33; the CHANGELOG bullets, 099's first; 066's "No floating-point exception flags" bullet replaced word for word, 066's other four bullets kept). Every other commit is `=`. Three new commits: `352d219` (the judge edit), `e44885f` and `f340225` (its spec only).
- **The judge edit (`352d219`) is right against both specs.** 066's *For the lane* says 099 empties the class when 066 lands first; 099's Decision 7 says it keeps its id, an empty list and its closer, and its gap goes. The edit keeps `id` and `match`, empties `expected/matplotlib-rest-b1/no-fp-exceptions.txt`, removes the `[[gap]]`, puts the reason in the past tense, and sets `closes_with` to 099's spec. Decision 7 says "keeps … its closer", but `numpy.toml`'s rule, which Decision 7 cites, says an emptied class keeps "the closer that emptied it", as 038's `no-ctypes` class does. So the closer change follows the rule. No stale reference remains (`git grep` of `Until spec 099`, `spec 099, reserved`, `no-fp-exceptions` in the README, CHANGELOG, roadmap and tests: only the class's id).
- `ruff check` and `ruff format --check` on `src` and `tests` at the tip: green (EXECUTED, `--no-cache`).

## 4. The flags (EXECUTED, `flags_check.py`)

- `accept.sh` passes exactly `flags.json`'s three texts (parsed with `shlex`).
- Paste-safe: no double quote, backquote, `$` or backslash, ASCII only. Each begins with the wave's line, then each entry's text after "042 ", "066:" and "099:", joined by " ; ".
- Each entry's own flag text is inside the wave's verbatim, except 042's `--accept-judge`, which ends "the zero-patch count 27 (26 before its rebase onto wave 07, the lane's correction)" for the entry's "26". Right (§3).
- 066 has no `--accept-growth`, as its *For the lane* says; its rows are new.
- What the texts miss: M2 and L2.

## 5. Findings, most severe first

**Not a finding against any entry: the host refused attempt 1.** Finder is writing `.DS_Store` files into the main tree's `build/`: `build/harness/.DS_Store` (741 KB) and `build/harness/openblas-void/.DS_Store` were written at 14:55, during the run. That voided `matplotlib-mathtext` (a third time: twice in 066's rebuild) and broke the OpenBLAS patch check. The lane names the cause: System Settings' Storage pane and Finder windows on the checkout, which no one can close while the owner is away. Attempt 2 therefore runs outside HOME (§7).

1. **M1: the oracle check is blocked in the lane, and no system in the release runs it.** `test_goldens_reproduce_under_the_pinned_oracle` (044's, passing on main) was `blocked, needs oracle`, counted as "unrun locally", not red. Cause (EXECUTED): `jobs.oracle_command` runs `uv run --frozen --offline` against `build/oracle/`; the venv there holds scikit-learn but not seaborn or reportlab, and its cache holds no seaborn wheel. So the offline sync of 042's lock fails and the need is unmet. The release does not run it either (sameness's note: "not run on any system in the release: oracle 1"). **Failure scenario:** the oracle lock the lane regenerated in 042's rebase, or 042's two new goldens, stop reproducing under the pinned oracle, and the wave lands with the old pass carried forward and nobody sees it until a later `regen.py`. **Fix (the lane):** sync the oracle once with network (the oracle's own environment: `UV_CACHE_DIR=build/oracle/cache`, `UV_PROJECT_ENVIRONMENT=build/oracle/venv`, `UV_PYTHON` its Python, `uv sync --frozen --project tests/jobs/oracle`; the wheels are hash-pinned in the lock), then let attempt 2 run the check. It must pass.
2. **M2: the growth texts do not name 19 rows that grew.** All of them come from claimed mechanisms, and I can account for each. But by the letter of §5.7 they are unclaimed growth:
   - 8 scikit-learn rows, `test_scikit_learn_reads_its_files_from_the_zip` +0.218% and +0.191% the most (042's members × 044's `all_estimators` walk; 044 is not on 042's measured base);
   - 11 upstream groups other than `cpython-fs` and `numpy-lib`, +0.024% to +0.090% (042's flag names only those two; 099's says "the rest within 0.01% or down", which these break where numpy runs). **Failure scenario:** the history line says less than happened, and the next lane cannot tell an interaction from a regression in these rows. **Fix:** attempt 2 has to run again anyway, so add one clause to `--accept-growth` before it, for example: `; the wave (042 with 044 and 099, from the integration review): scikit-learn rows by 042s start cost, and its file-reading check plus 0.22 percent as all_estimators walks the 199 more members; on darwin eleven more upstream groups up 0.02 to 0.09 percent by their guests start cost and numpys status reads, cpython-fs plus 0.16 percent`. Then check the run's growth against it again.
3. **L1: the OpenBLAS patch script loses a race with Finder.** `unstage_litter` in `scripts/make_openblas_void_patch.sh` runs `git rm -q --cached -- "$p"`. If the OS rewrites a `.DS_Store` between `git add -A` and the `rm`, git refuses ("staged content different from both the file and the HEAD … use -f"), and the check fails as a lost pass, not as a `HostLitter` void. This is spec 037's script (in main since wave 06), not this wave's. Follow-up: `git rm -q --cached -f -- "$p"` (the file stays on disk either way). Until then, a Finder window on `build/` breaks the lane.
4. **L2: 042's growth text says "snapshot plus 74056".** On wave 07's base the snapshot grows +62,683 (042's share +62,943). The number is from 038's base. Text only; fix it in the same edit as M2, or write the measured number in the landing notes.
5. **L3: 042's build review was not confirmed in writing.** Its *Disposition* heading says "then confirmed by the reviewer", but nothing confirms it, unlike 066's and 099's confirming reviews. Its one code change after run 39421194888 is the order of two assertions in `test_seaborn_takes_its_scipy_paths` (`57f9a65`, three lines). I read it: harmless. Both nodes pass in attempt 1. The landing notes should say the lane read it (§5.6, a fix to code for a finding is read by the lane).
6. **Note:** §5.7 asks the lane to compare its set with the release workflow's build of the same tip. Under the owner's rule of 2026-10-20 that build is the wave's dry run, after acceptance. The comparison moves there (§6).

## 6. What the wave's dry run must confirm (Linux and Windows; the darwin accept cannot)

- The CI build of the accepted commit gives `SHA256SUMS` `b5a66245…` on both Linux hosts and macOS: python.wasm `ee45b241…`, the snapshot `9c2af970…`, the zip `fb12a1e6…`; "the same bytes from every host" passes. The zero-patch step prints `27 passed`.
- 066's fourteen `upstream-plot-*` shards on Linux with 042 and 099 in the set. Only darwin has run them with 099. All 40 groups pass with 17,974 passes, `rest-b1` 3,369, and the `collected` facts 518, 419 and 36 in every split group. **mathtext needs this run most:** no clean run of it exists on wave 07's or wave 08's set yet (voided twice in 066's rebuild and once here). If attempt 2 voids it again, the dry run's Linux record is its only evidence.
- numpy's, pandas' and CPython's upstream groups on Linux and Windows with both 042 and 099: the same passes and digests.
- Windows, with 042's members and 099's flags together (each passed Windows alone, in runs 39421194888 and 39454475153): 099's checks 1 to 3, 042's `pdf_reports` golden (it reproduces everywhere), `test_reportlab_writes_a_pdf_with_nothing_writable`, and seaborn's `load_dataset` outcome.
- `test_goldens_reproduce_under_the_pinned_oracle` does not run in the release (M1), so the dry run cannot stand in for the lane on it.
- Then sameness between the dry run's merged record and the lane's record (§2).

## 7. Attempt 2 in a clone outside HOME (the lane's question, 15:00 EDT)

The lane will rebuild and accept in a clone of `72bc5ed` at `/private/tmp/…/scratchpad/w08-tree`, because the litter writer (System Settings' Storage pane and Finder) only writes under HOME, and then copy `context/progress/` back to the main tree.

**Sound, on five conditions.**

1. **The clone's set must equal `b5a66245`, byte for byte.** Yes, it must. The prediction, the claim lists and this comparison are all against that set, and §2 shows it is 099's set plus exactly 042's 199 members. The artifacts carry no checkout path: the release builds them in other paths on two Linux hosts and macOS and requires the same bytes. So a different hash is a defect (a path in an artifact, or a different input), not a new baseline. If it differs, stop and find why before accepting. The two v1.5 failures the lane saw with a copied build tree are the build tree's records (absolute paths in compile records), not the artifacts; a fresh build in the clone is right.
2. **Every need that attempt 1 had must be met in the clone, or rows go quietly unrun.** A blocked check whose need is not protected counts as "unrun locally", which is not red (`scoreboard.PROTECTED_NEEDS` holds only the artifacts, the runner and the wheel). In the clone as it stands (READ):
   - **the upstream kit:** `build/upstream/wheels/` does not exist (the main tree has 7 wheels). Without it, **every upstream group is blocked**: numpy's, pandas' and CPython's 16 accepted groups would be "unrun locally", and 066's 40 groups would be recorded blocked, not passing. Copy the main tree's wheels (the need checks each one's SHA-256 against `kit.txt`) or run `tests/upstream/fetch.py` in the clone;
   - **the oracle** (M1): `build/oracle/` is fresh in the clone. Sync it with network, as M1 says;
   - **the prior-art clones:** `context/prior_art/` holds only `README.md`, so `test_every_prior_art_clone_has_its_licence_recorded` (rules, passing on main) would be unrun locally. Copy or clone them, read-only, as the main tree has them. The condition: attempt 2's scoreboard shows blocked exactly 2 (wheel, three systems) and no `unrun locally` part in its ratchet line.
3. **Path independence, shown by the lane's own two runs.** Spec 081 measured two checkouts for 148 rows, and argued the upstream groups by reading only (their trees did not exist then); 066's package groups came later, behind 081's guard, which refuses any measured run that hands the guest a host path under the checkout or the temp roots. Attempt 1 (in HOME) and attempt 2 (in the clone) are a two-checkout run of every row on one set. So run `uv run python tests/harness/sameness.py build/wave-08/latest-attempt1-void.json <the clone's build/progress/latest.json>` (read-only). Clean means: differences only in the three rows the host voided in attempt 1 (mathtext's group and class, the OpenBLAS check) and the oracle check once synced; no fuel difference beyond the tolerance on any other row. Any other difference is a path dependence: a finding, and the accept waits.
4. **The copy back is exact.** The main tree's acceptance commit holds the clone's `context/progress/` files byte for byte, on parent `72bc5ed` (the clone's HEAD), and nothing else. Then `test_progress_history_is_intact` and the committed-prefix check run in the main tree by node id. The history line's `host` is this machine's either way; its `dirty` is the clone's (clean).
5. **The same flags, with M2's clause and L2's number**, since attempt 2 is a new run anyway.

The clone sits in this session's scratchpad under `/private/tmp`. macOS may clean `/private/tmp` after some days, so the lane should keep nothing there that the landing notes cite as evidence: copy the log and record into the main tree's `build/wave-08/`.

## 8. Verdict

**Lands once** the lane's second acceptance is green on `72bc5ed` with:
- no host litter, so `matplotlib-mathtext` and the OpenBLAS check run clean (in the clone outside HOME, on §7's five conditions: the set equal to `b5a66245`, every need met, sameness against attempt 1 clean, the progress copied back exactly);
- the oracle synced, so `test_goldens_reproduce_under_the_pinned_oracle` runs and passes (M1);
- `--accept-growth` widened by M2's clause (and L2's number);
- its ratchet showing lost 0 and fewer 0, every grown row inside §2's list. Nothing outside it is expected: attempt 1 already measured every row but mathtext, the OpenBLAS check and the oracle check, and those three record no fuel growth. L1 and L3 are answered in writing in the landing notes. No entry needs to change code, and none is ejected.

One line: the three rebases are exactly what was reviewed plus the named hunks and a correct judge edit; the lane's set is 099's set plus 042's 199 members; and the wave's numbers match the prediction apart from three host failures, a blocked oracle and nineteen interaction rows the flags must name.

## 9. Addendum: attempt 3, accepted in the clone (read 16:00 EDT)

Attempt 2 in the clone was refused: the oracle's venv had been made inside the checkout (`tests/jobs/oracle/build/oracle/venv`), so three rules checks scanned its site-packages and lost their passes (`accept-attempt2-staylvenv.log`). Not an entry's. Attempt 3 was accepted in the clone: history line 89, commit `72bc5ed`, `set_sums` `b5a66245`, `dirty` false, no partial or fewer reason, `passed_removed` empty, nothing retired (EXECUTED, the clone's `history-00060.jsonl`).

**Against the prediction (EXECUTED, `compare-attempt3.txt`: the clone's `accepted.json` against wave 07's):**

| | predicted | attempt 3 |
|---|---|---|
| scoreboard | 763/850 · 85 gap · 2 blocked · 0 fail | **763/850 · 85 gap · 2 blocked · 0 fail** |
| per goal | rules 45/45 · v1.1 45/46 · v1.2 160/161 · v1.3 233/318 · v1.4 230/230 · v1.5 50/50 | the same |
| gained | 59 | 59 (81 new rows: 59 pass, 22 gap) |
| lost, absent, fewer | 0 | 0 |
| grew | about 231 | 235 (2 bytes, 233 fuel), the same rows as attempt 1 |
| fell | | 3 (python.wasm −260, `plot_line[snapshot]`, `scipy_solvers[snapshot]`) |

- 066's 40 groups: 17,974 passes, as predicted. `matplotlib-mathtext` ran clean for the first time on wave 07's or 08's set: 985 passes, 296,610,152,067 fuel (−0.037% on wave 06's 296.7 G).
- The oracle check now passes (M1 closed in the clone). The OpenBLAS check passes (no litter).
- The growth text carries M2's clause and L2's number (the history line, EXECUTED).

**§7's conditions:**
1. **The set:** the clone's `SHA256SUMS` is byte-identical to the main tree's (`cmp`): `b5a66245`. Met.
2. **The needs:** blocked exactly 2 (wheel, three systems); the upstream wheels (7), the prior-art clones (31 entries) and the oracle are present. Met. One small residue: the unit suite ran 1,878/1,885 with 7 skipped, against 1,883 and 2 skipped in attempt 1. Four of the five are `test_guest.py`'s reference-build tests (`build/brett-3.14.7` is not in the clone). They passed in attempt 1 on the same code. A note, not a finding.
3. **Path independence:** every one of the 358 metrics (fuel, bytes, passes) that both attempt 1 (in HOME) and attempt 3 (in `/private/tmp`) recorded is **identical to the instruction** (EXECUTED, row by row). The only differences are the four statuses the host or the oracle changed in attempt 1 (mathtext's group and class, the OpenBLAS check, the oracle check). That is spec 081's two-checkout test done on every row, upstream and package groups included. The lane's `sameness-attempt1-vs-3.txt` says the same (9 lines). I could not re-run it on the same record: the clone's `build/progress/latest.json` has since been rewritten by a later run, so the lane should keep its own copy of attempt 3's record with the notes.
4. **The copy back:** not done yet when read (the main tree's `context/progress/` is unchanged). The lane copies the clone's two files byte for byte onto `72bc5ed`, commits only them, and runs `test_progress_history_is_intact` by node id in the main tree.
5. **The flags:** met.

**Final verdict: lands as accepted in the clone, once the progress files are copied back exactly (condition 4).** M1, M2 and L2 are closed. L1 and L3 stay as written answers in the landing notes. The wave's dry run carries §6.

One line: attempt 3 matches the prediction row for row, its numbers are identical to attempt 1's in another checkout, and the wave lands once its two progress files reach the main tree unchanged.
