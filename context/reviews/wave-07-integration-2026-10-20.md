# Review of wave 07 — the integration of 038 (scipy's second milestone) and 044 (scikit-learn)

- **Date:** 2026-10-20
- **Reviewer:** Claude Opus 5.5, the wave's integration reviewer. A fresh agent: it reviewed none of
  the wave's entries and wrote none of their code.
- **Reviewed:** `wave/07` at `e9a76ce`, on main `3ff1871`; 038's 12 commits (`00bba19..3d7f9c7`)
  against its reviewed tip `5cd171d`; 044's 10 commits (`7d1ef9b..e9a76ce`) against its reviewed
  tip `089723c`.
- **Run:** none of my own (the lane dispatches the wave's dry run; the brief forbids a dispatch).
  Read instead, from their shard records (`gh run download`, no gather job so no
  `release-record-1`): 038's runs 39415728849 and 39416337718 (both on `ecc2423`), 044's runs
  39416371904 (`026ba56`) and 39418201520 (`4a087fa`), and, as the baseline on main's set,
  wave 06's dry run 39398491514 on `c5fc7a4`.
- **Re-ran:** no judge tier (`build/lane.lock` rules; brief). EXECUTED: `git range-diff`,
  `git diff --stat`, `git ls-tree`, `git show` of the wave tip in the main tree's object store (read
  only); a scratchpad script that applies the ratchet's own rules
  (`tests/harness/scoreboard.py`: `FUEL_TOLERANCE` 1e-4, `COUNTS_UP` = passes, bytes on any rise)
  to the downloaded darwin-arm64 records against `3ff1871:context/progress/accepted.json`
  (d066695's accept, main `c5fc7a4`). Check: the same script on wave 06's dry run gives 0 grown
  rows against that state, so CI's macOS fuel equals the lane's local darwin fuel row for row.
- **Time box:** 45 minutes (a package chain).

## Acceptance criteria against evidence

1. **Each rebase equals its reviewed tip** — met. `git range-diff 958a22b..5cd171d 3ff1871..3d7f9c7`:
   12 of 12 commits `=`. `git range-diff 5cd171d..089723c 3d7f9c7..e9a76ce`: 10 of 10 `=`.
   `git diff --stat 089723c e9a76ce` and `git diff --stat 5cd171d 3d7f9c7` both show only
   `context/decisions.md` (+55) and `context/roadmap.md` (+5 -1), which is exactly
   `git diff --stat 958a22b 3ff1871`. The lane's reading holds. EXECUTED.
2. **The named conflicts are resolved right on the tip** — met. EXECUTED with `git show e9a76ce:`.
   - 22 `.patch` files under `recipes/patches/` (`git ls-tree -r`): OpenBLAS 3, kiwisolver 2,
     libxml2 1, lxml 1, matplotlib 2, networkx 1, numpy 2, pandas 1, Pillow 1, qhull 1, regex 2,
     scikit_learn 1, scipy 4.
   - README says 22 in all three places 044 named: the facts table row (line 41, "upstream patches
     carried: 22", keeping kiwisolver's `tp_clear` and lxml's `fake_cython` among the merged
     upstream), the platform-facts sentence (line 56, "twenty-two carried patches") and the build
     section (line 531, "twenty-two today"). No "twenty-one" or "21 carried" is left.
   - CHANGELOG: one unreleased section, `## 0.1.0a8 — unreleased`, holding 096's entry, then
     044's (line 20), then 037's (whose "Known gaps until spec 038" is 037's own landed text),
     then 038's (line 66). Both entries are under 0.1.0a8; the heading is unchanged.
   - 044's rebase 3 had no hunk: 038's entry reads as on `5cd171d` and 044's is unchanged
     (range-diff `=` on both commits confirms it).
3. **The set** — confirmed: the wave tip's set is 044's `dc6ba3a5…2471`. EXECUTED/READ:
   `scripts/assemble_artifacts.py:684-708` writes `MANIFEST` from `git ls-files recipes scripts`
   (minus `bench_*`), the pins in `downloads/SHA256SUMS` and constants (`SOURCE_DATE_EPOCH` is the
   constant 1767225600 from `scripts/build.sh:20`). `git diff --stat 1dba792 e9a76ce -- scripts
   recipes downloads src .github` is empty (1dba792 is the commit 044 built from empty); the
   paths that changed since are `CHANGELOG.md`, `README.md`, `context/` and `tests/` (checks,
   `jobs/oracle/sklearn_native_tests.sh`, `known_gaps.toml`, `upstream/`), none hashed and none
   read by a build step. The brief's list should add `README.md`; it changes nothing. Both Linux
   rebuilds of runs 39416371904 and 39418201520 printed a `SHA256SUMS` hashing to `dc6ba3a5`, and
   every shard record's `set_sums` is `dc6ba3a5`; 038's runs give `c3a849c0`, wave 06's `f12cd25c`.
4. **The claim lists against the expected growth** — met for 038; one gap for 044 (Finding 1).
   The prediction is below.
5. **The flags are paste-safe and start with their spec number** — met. All six texts: no `"`,
   `$`, backtick, `!` or backslash; each begins `038: ` or `044: `. 038's `--accept-growth` holds
   `±` (non-ASCII, harmless inside double quotes). The joined texts are in the appendix and in
   `wave07-flags.txt` beside this review.

## The prediction: what the lane's acceptance on `e9a76ce` should print against main

Platform darwin-arm64, wasmtime 49.0.0 (the same as accepted, so every fuel row is compared).
Per-row numbers: `prediction-rows.tsv` beside this review (214 rows: node, main, 038's run, 044's
run, the three percentages).

### Lost: 0. Fewer passes: 0. Absent: 0 (no `--retire`).

On every CI run, wave 06's dry run included, two accepted passes are blocked there and pass only
locally: `test_rules.py::test_every_prior_art_clone_has_its_licence_recorded` (the clones) and the
oracle goldens check. Neither entry touches the first.

One risk, not a prediction: `test_v1_3_data_stack.py::test_goldens_reproduce_under_the_pinned_oracle`
(an accepted pass; blocked on CI, so no run has shown it with this wave) now iterates `JOBS` with
`scipy_edges` and `machine_learning`. 038's build review ran it with `scipy_edges` (pass). No record
shows it run with `machine_learning`. It needs the oracle venv synced with 044's
`scikit-learn==1.9.1` pin (`tests/jobs/oracle/uv.lock`); spec 023's landing met exactly this (the
history line: "the oracle venv lacked 023's new pin"). Expected: pass. Blocked means the venv was
not synced (sync it, then judge); a mismatch on `machine_learning` is 044's.

### Gained: 27 (15 are 038's, 12 are 044's)

- 038 (its claim list: 6 new guest rows, 9 gaps that pass): `test_v1_3_scipy.py::`
  `test_scipy_edges_job_matches_native`, `test_ndarray_ctypes_gives_the_arrays_address`,
  `test_the_sobol_options_need_nothing_writable`, `test_matrix_market_round_trips_in_memory`,
  `test_sobol_needs_nothing_writable`, `test_ctypes_values_scipy_makes`, each `[plain]` and
  `[snapshot]` (12); `test_v1_3_upstream_suites.py::test_upstream_class[cpython-a-no-ctypes]`,
  `[cpython-c-no-ctypes]`, `[numpy-others-no-ctypes]` (3; on CI these ran on Linux, gap to pass).
- 044 (its 12 new checks): `test_v1_3_default_profile.py::` `test_machine_learning_job_matches_native`,
  `test_scikit_learn_runs_without_threads`, `test_scikit_learn_reads_its_files_from_the_zip`,
  `test_scikit_learn_modules_are_builtin`, each `[plain]` and `[snapshot]` (8),
  `::test_scikit_learn_says_what_it_lacks`; `test_v1_1_artifact_set.py::test_scikit_learn_notice_carries_its_bundled_parts`,
  `::test_the_sample_images_are_not_in_the_zip`;
  `test_v1_5_rebuild_from_pins.py::test_source_tree_matches_its_tarball[scikit_learn]`.
- Not the wave's, may appear: `test_v1_1_artifact_set.py::test_wheel_carries_the_artifact_set`
  (gained on every CI run, wave 06's included; locally it needs a wheel in `dist/`).
- The unit suite's rows are counted apart (038's 5, 044's 10 test functions).

### More passes: 3 (038's)

`test_upstream_suite[cpython-a]` 5,864 → 5,865; `[cpython-c]` 7,872 → 7,877; `[numpy-others]`
7,269 → 7,277. Every other group keeps its count (CI, all four runs).

### Grown: 217 to 228 lines

**Bytes, 3 rows (exact; the set is `dc6ba3a5`):**

| row | main | wave | change | whose |
|---|---|---|---|---|
| `test_binary_is_a_core_wasm_module[plain]` | 84,794,273 | 93,793,855 | +8,999,582 (+10.61%) | 038 −2,786, 044 +9,002,368 |
| `test_binary_is_a_core_wasm_module[snapshot]` | 89,468,144 | 98,620,293 | +9,152,149 (+10.23%) | 038 −5,638, 044 +9,157,787 |
| `test_stdlib_zip_is_bytecode_only_and_deflated` | 44,445,945 | 47,730,899 | +3,284,954 (+7.39%) | 038 +3,192, 044 +3,281,762 |

**Fuel measured on CI's macOS shards, 211 rows (exact; both 044 runs equal on all 211; 044 is
below 038 on none of them):** +0.031% to +7.747%, median +1.483%. 117 of them already grew on
038's run (038's claim) and rose again by 044 (+0.050% to +7.51% over 038's run); 94 grew only
with 044 (+0.031% to +7.747%). By file:

| file | rows | range against main |
|---|---|---|
| `test_v1_3_the_zips_directory.py` | 20 | +0.203% to +7.747% |
| `test_v1_4_embedding.py` | 33 | +0.178% to +4.942% |
| `test_v1_2_portable_and_sealed.py` | 5 | +0.395% to +4.665% |
| `test_v1_2_hostile_guest.py` | 42 | +0.031% to +4.657% |
| `test_v1_1_artifact_set.py` | 12 | +0.164% to +4.656% |
| `test_v1_3_matplotlib.py` | 14 | +0.052% to +4.598% |
| `test_v1_3_default_profile.py` | 16 | +0.186% to +3.225% |
| `test_v1_3_data_stack.py` | 24 | +0.190% to +2.546% |
| `test_v1_3_regex.py` | 8 | +0.186% to +2.248% |
| `test_v1_3_lxml.py` | 18 | +0.201% to +2.155% |
| `test_v1_3_scipy.py` | 18 | +0.150% to +1.100% |
| `test_v1_3_upstream_suites.py` (`cpython-fs`) | 1 | +0.167% (63,099,389,920) |

The named rows: `cpython-fs` 62,994,222,641 → 63,099,389,920 (038 +0.046%, 044 +76.0 M, both
claimed); `test_unbuffered_output_survives_a_hard_exit[snapshot]` 1,265,275 → 1,289,733 (+1.93%:
038 +0.39%, 044 +1.53%, both claimed); `test_metadata_answers_from_the_zips_directory[plain]`
+2.72% (+14.3 M, 044's "one more distribution"); 033's `test_ctypes_stand_in_names_what_packages_import`
+1.69% / +1.61%; `test_threadpoolctl_finds_no_native_pools` +2.81% / +1.59%. The largest,
`test_resources_read_as_zipfile_reads_them[snapshot]` +7.747%, is 044's "the zip-directory checks
walk them". The CI-darwin `numpy-lib` row does not grow (−0.045%).

**Fuel the lane measures on darwin and CI ran only on Linux, 3 rows certain and 11 possible.**
Estimate: main's accepted darwin value moved by 038's darwin measure where one exists (its node-id
runs: cpython-a +0.044%, cpython-b +0.067%, cpython-c +0.038%, numpy-others −0.038%) plus 044's
Linux change over 038's runs; for the ten groups with no darwin number, Linux main (39398491514) to
Linux 044 (39416371904, 39418201520). Linux runs of the same commit differ by up to 0.07% (numpy-core
156.51 G and 156.62 G) and, for `cpython-archives`, by 1.65% (168.36 G and 165.58 G, both on
`ecc2423`), so each range is wide by that.

| group | main (darwin) | expected on the wave | range | grows? | whose |
|---|---|---|---|---|---|
| `cpython-c` | 399,539,998,880 | about +2.96% (411.4 G) | +2.8% to +3.2% | yes | 038 +0.038%; **044 +2.92% / +2.96% on Linux, unclaimed (Finding 1)** |
| `cpython-a` | 276,737,572,275 | about +0.10% | +0.05% to +0.15% | yes | 038 +0.044% (claimed); 044 +0.048% / +0.054% (unclaimed) |
| `cpython-b` | 296,446,251,252 | about +0.09% | +0.05% to +0.15% | yes | 038 +0.067% (claimed); 044 +0.020% (unclaimed); see the note |
| `pandas-io-parser` | 94,278,067,299 | about +0.07% | −0.05% to +0.17% | likely | 038 ±0.1% (claimed); 044 +0.015% to +0.056% |
| `numpy-others` | 177,648,959,738 | about +0.01% | −0.06% to +0.07% | maybe | 038 −0.038%; 044 +0.036% to +0.052% |
| `numpy-core` | 156,703,624,522 | about −0.07% | −0.17% to +0.07% | maybe | 038 ±0.1% |
| `cpython-archives` | 167,072,877,061 | about −1.5% | −1.7% to +0.8% | maybe | noisy group (above); not either entry's above +0.1% |
| `pandas-frame` | 354,715,941,554 | about −0.05% | −0.15% to +0.05% | maybe | 038 ±0.1% |
| `pandas-groupby` | 487,336,198,393 | about −0.02% | −0.12% to +0.10% | maybe | 038 ±0.1% |
| `pandas-reshape` | 103,214,719,111 | about −0.04% | −0.14% to +0.07% | maybe | 038 ±0.1% |
| `pandas-io-formats` | 89,587,450,915 | about −0.10% | −0.20% to +0.03% | maybe | 038 ±0.1% |
| `pandas-libs` | 27,312,838,317 | about −0.08% | −0.18% to +0.03% | maybe | 038 ±0.1% |
| `pandas-internals` | 21,677,802,521 | about −0.07% | −0.17% to +0.04% | maybe | 038 ±0.1% |
| `pandas-tslibs` | 38,784,886,154 | about −0.09% | −0.20% to +0.02% | maybe | 038 ±0.1% |

`cpython-fs` and `numpy-lib` are measured on CI's macOS shard (above). No group's passes fall.

**A note on `cpython-b`.** On Linux its fuel takes one of two values whatever the set: 293.45 G on
wave 05's run 39371419248 and 096's run 39386471189, 303.18 G on 037's run 39382879444, 293.66 G on
wave 06's dry run, 303.21 G on 038's and 303.27 G on 044's. Darwin measured 296.45 G at wave 06's
accept and 296.65 G on 038's set (038's node-id run), so on darwin I expect the row above. If the
lane reads `cpython-b` near +3.3%, that is this two-valued group, not either entry's change (it moved
on runs with neither entry); it is in this table so it ejects nothing, and the lane names it in its
own words in the growth reason.

**Totals:** grown lines 217 (3 bytes, 211 CI-darwin fuel, cpython-a, -b, -c) to 228 (with all
eleven possible groups); gained 27; more passes 3; lost 0; fewer 0. The judge changed (both entries'
checks), so `--accept-judge` is needed; no `--retire`, `--accept-fewer-passes` or `--partial`.

## Findings, most severe first

1. **Medium — 044's claim list does not name the upstream groups that grow on darwin and that its
   own CI ran only on Linux** (`context/specifications/044-scikit-learn.md`, "Rows that grow" and
   the `--accept-growth` text). `cpython-c` grows +2.92% (run 39416371904) and +2.96% (39418201520)
   over 038's runs on Linux, which on darwin is about +12 G fuel against main: pydoc's apropos
   imports every builtin (READ: `tests/known_gaps.toml`, the `cpython-c-pydoc-imports-scipy`
   entry), and scikit-learn's 69 are now among them, as wave 06's accept measured +6.29% for scipy's
   95 (INFERRED from that cause; the gap's digest `c1977f2d517b` is unchanged on both 044 runs, so
   no new environment finding). `cpython-a` (+0.05%), `cpython-b` (+0.02%), `numpy-others` and
   `pandas-io-parser` (+0.02% to +0.06%) rise by the zip's new directory entries. 044's list claims
   `cpython-fs` only, the one macOS upstream row. Failure: the lane's accept prints
   `GREW test_upstream_suite[cpython-c]` at about +3%, which no claim list names. It is in this
   table, so it ejects nothing; to close it, the lane passes 044's growth text with the clause the
   appendix adds (`wave07-flags.txt` carries it), and the clause goes into 044's claim list in the
   landing notes. Evidence that would close it without the clause: none; the row will move.
2. **Low — 044's claim list's "Changed checks" omits the oracle goldens check**, which now also
   reproduces `machine_learning` (`tests/checks/test_v1_3_data_stack.py:274-284`, it iterates
   `jobs.JOBS`). 038's list names it for `scipy_edges`. Fix text for 044's claim list:
   "`test_v1_3_data_stack.py::test_goldens_reproduce_under_the_pinned_oracle` also reproduces
   `machine_learning` on darwin-arm64 (the oracle venv needs the `scikit-learn==1.9.1` pin
   synced before the lane's accept)." The prediction's risk line asks the lane to sync it first.
3. **Note — the brief's list of later-touched paths should add `README.md`.** It is not hashed;
   the set prediction stands.
4. **Note — 044's "185 fuel rows, all up, none down" is against 038's fast record.** Against
   038's CI run three darwin rows fall slightly (`test_encodings_are_wasi_libcs_as_documented`
   −0.197%, `test_the_readmes_encoding_workaround_reads_what_iconv_cannot` −0.262%,
   `test_lxml_xml_job_matches_native` −0.048%). A fall is never red; nothing to do.

## Constitution checks

- §4.1 patches: 22 recorded patches, each entry's two scipy patches and 044's one in `MANIFEST`
  through `recipes/` (`git ls-files recipes scripts`); README and CHANGELOG agree on 22.
- §4.14 / §5.7: one stacked package chain (038 then 044), no other entry; each rebase equals its
  reviewed tip; main's commits under the wave touch only `context/`.
- §5.6: each entry's review is on the tip (038 build and delta, 044 build); their Mediums were
  answered in `5cd171d` and `089723c`, which the range-diff shows unchanged.
- §7: nothing tripped. No judge file, golden, allowance or progress file changed by the wave other
  than as each entry's claim list and `--accept-judge` state.

## Disposition (the lane fills in; then confirmed here)

1. Finding 1 — the lane passes the amended `--accept-growth` (appendix) / or answers why not.
2. Finding 2 — the lane syncs the oracle venv before its accept; the fix text goes into 044's
   claim list with the landing notes.

## Verdict (provisional)

Lands as merged at `e9a76ce`, provided the lane's acceptance shows nothing beyond the prediction
above (no lost pass, every grown row in a claim list or in this table) and passes 044's growth text
with Finding 1's clause; the final verdict follows the lane's acceptance output.

## Appendix: the joined flags (038's text, then "; ", then 044's)

All three begin `038: `, and every part is paste-safe (no `"`, `$`, backtick or `!`). The growth
flag carries 044's text with Finding 1's clause appended (after "one more distribution's
metadata"); the as-written join is the second block, for reference only.

```
--accept "038: scipy's sandbox edges (spec 037's three gaps closed): carried scipy patches 0003 (Matrix Market's default parallelism 1 on WASI) and 0004 (Sobol's direction numbers read without a temporary file); the ctypes stand-in holds numeric and c_void_p values and casts to c_void_p, with CPython's truth and argument rules, no memory (its buffer refuses with the stand-in's OSError) and nothing with an address; the zip differs from 037's in exactly two members; 044: scikit-learn 1.9.1 built in, stacked on 038: 69 modules as builtins, 411 zip members, the golden equal to native on both binaries; the weak-duplicate gate and the link-map check for every package; sklearn.utils._random renamed off CPython's _random (B11); both callback scans clean with its modules; the owner approved B1 (decisions.md, 2026-10-20)"
--accept-judge "038: the edges golden (tests/jobs/scipy_edges.py, .expected, .platform, JOBS and PLATFORM_BOUND) run with nothing writable; the guest address check; the Sobol options check (the build review's Low 7); five host unit checks of the stand-in (its value rules at wasm32's sizes, no buffer, CPython's truth and argument types, its imports held to struct and sys); 033's guest and unit stand-in checks changed to Decision 3's rule; spec 037's six scipy [[gap]] entries removed because their checks pass; the no-ctypes classes of cpython-a, cpython-c and numpy-others emptied (their expected lists empty, their classes kept with a closed-by-038 reason) and their three [[gap]] entries removed, because no test in those groups meets the stand-in's OSError: cpython-a +1, cpython-c +5 and numpy-others +8 passes; 044: the machine_learning golden with the oracle's scikit-learn pin and OMP_NUM_THREADS=1; four scikit-learn behaviour checks; the notice check (build shard) and the sample-image check; the constructor list's three newrand constructors; scikit-learn in the package, licence, source-tree and metadata lists, MESON_BUILDS, CPP_CROSS_FILES, COMPONENT_NAMES and packages.toml, its suite later with spec 095 as its closer; scikit-learn's own dotted-builtin run; the release tree count 26"
--accept-growth "038: the stand-in's types carry the value rules: the first type lookup +1.35 M fuel on the plain reactor and +1.30 M on the snapshot, import scipy (which builds them) +1.65 M and scipy.optimize +3.8 M, so every check that imports scipy grows 0.05% to 0.19% and threadpoolctl's check +0.90% / +0.35%; 033's guest check +1.39% / +1.32%, help(ctypes) rendering every simple type's value methods (+63 M on the snapshot) and more steps; test_unbuffered_output_survives_a_hard_exit[snapshot] +0.39% (+4,967 fuel, measured on 037's set and 038's: +740 in the snapshot's start and about +3,750 in -u's unbuffered stdio, the same modules loaded; a heap-layout move of the rebuilt snapshot, large in percent only because os._exit skips finalization: a 1.27 M base where other snapshot rows are about 50 M and move up to ±19 k); the upstream groups cpython-a +0.044%, cpython-b +0.067%, cpython-c +0.038% (more tests run), cpython-fs +0.046% (test_io's no-ctypes tests make the first type lookup), numpy-lib -0.074%; 27 slow job rows +0.001% to +0.096% (scipy's three jobs, the symbolic job +0.082%, the rest below +0.07%); not measured on darwin-arm64 on this set, expected within ±0.1% for the same causes: numpy-core, cpython-archives and the eight pandas groups (pandas-frame, pandas-groupby, pandas-reshape, pandas-io-parser, pandas-io-formats, pandas-tslibs, pandas-libs, pandas-internals); the zip +3,192 bytes in two members, python.wasm -2,786 and the snapshot -5,638; 180 fast-tier rows, 27 slow rows and cpython-fs move against main, fast-tier median +0.011%; 044: python.wasm +9.00 MB and the snapshot +9.16 MB by scikit-learn's 69 modules and its static libraries; the zip +3.28 MB by 411 members; every plain start +11.2 M fuel (27,240 per member) and every snapshot start +1.05 M by those members' directory entries; the zip-directory checks walk them, and macOS's cpython-fs suite +76.0 M (0.12 percent) over 038's run by rebuilding the zip's directory after its cache is invalidated; one more distribution's metadata; measured in CI on Linux only, over 038's run (the integration review's table): cpython-c about +2.9 percent, since pydoc's apropos imports every builtin and scikit-learn's 69 are now among them (wave 06 measured +6.29 percent for scipy's 95), cpython-a about +0.05 percent, and numpy-others, pandas-io-parser and cpython-b below +0.06 percent, by the same directory entries"
```

As written, without Finding 1's clause (not recommended):

```
--accept-growth "038: the stand-in's types carry the value rules: the first type lookup +1.35 M fuel on the plain reactor and +1.30 M on the snapshot, import scipy (which builds them) +1.65 M and scipy.optimize +3.8 M, so every check that imports scipy grows 0.05% to 0.19% and threadpoolctl's check +0.90% / +0.35%; 033's guest check +1.39% / +1.32%, help(ctypes) rendering every simple type's value methods (+63 M on the snapshot) and more steps; test_unbuffered_output_survives_a_hard_exit[snapshot] +0.39% (+4,967 fuel, measured on 037's set and 038's: +740 in the snapshot's start and about +3,750 in -u's unbuffered stdio, the same modules loaded; a heap-layout move of the rebuilt snapshot, large in percent only because os._exit skips finalization: a 1.27 M base where other snapshot rows are about 50 M and move up to ±19 k); the upstream groups cpython-a +0.044%, cpython-b +0.067%, cpython-c +0.038% (more tests run), cpython-fs +0.046% (test_io's no-ctypes tests make the first type lookup), numpy-lib -0.074%; 27 slow job rows +0.001% to +0.096% (scipy's three jobs, the symbolic job +0.082%, the rest below +0.07%); not measured on darwin-arm64 on this set, expected within ±0.1% for the same causes: numpy-core, cpython-archives and the eight pandas groups (pandas-frame, pandas-groupby, pandas-reshape, pandas-io-parser, pandas-io-formats, pandas-tslibs, pandas-libs, pandas-internals); the zip +3,192 bytes in two members, python.wasm -2,786 and the snapshot -5,638; 180 fast-tier rows, 27 slow rows and cpython-fs move against main, fast-tier median +0.011%; 044: python.wasm +9.00 MB and the snapshot +9.16 MB by scikit-learn's 69 modules and its static libraries; the zip +3.28 MB by 411 members; every plain start +11.2 M fuel (27,240 per member) and every snapshot start +1.05 M by those members' directory entries; the zip-directory checks walk them, and macOS's cpython-fs suite +76.0 M (0.12 percent) over 038's run by rebuilding the zip's directory after its cache is invalidated; one more distribution's metadata"
```

One line: the wave is the two reviewed chains unchanged, its set is `dc6ba3a5`, and the lane should
see about 217 to 228 grown rows, 27 gained and 0 lost, with `cpython-c` +3% the one row 044 did not
claim.

## Addendum: the lane's acceptance against the prediction (2026-10-20)

**Inputs (read only):** `build/wave-07/cmp/accepted-before.json` (byte-identical to
`3ff1871:context/progress/accepted.json`), `latest.json` (the run: darwin-arm64, wasmtime 49.0.0,
set `dc6ba3a5`, commit `e9a76ce`, 3 workers) and `accepted-after.json` (commit `e9a76ce`, 767
checks). I compared them with the scratchpad script from the prediction, which applies the
ratchet's rules (EXECUTED). Run: 704 pass, 63 gap, 2 blocked (the wheel and the three systems
check, neither accepted as a pass), 0 fail. Every row the run passed or matched as a gap is in
`accepted-after.json` with the run's status.

| line | predicted | actual | verdict |
|---|---|---|---|
| lost | 0 | 0 | as predicted |
| fewer passes | 0 | 0 | as predicted |
| absent | 0 | 0 | as predicted |
| more passes | 3 (cpython-a +1, cpython-c +5, numpy-others +8) | the same 3, the same counts | as predicted |
| gained | 27 (038's 15, 044's 12), the wheel check possible | the same 27, node for node; the wheel check blocked | as predicted |
| grown, bytes | 3 rows, exact | the same 3, equal to CI's values to the byte | as predicted |
| grown, CI-darwin fuel | 211 rows, exact | the same 211, every value equal to 044's CI runs | as predicted |
| grown, Linux-only groups | 3 certain plus up to 11 possible; 217 to 228 lines in all | 7 rows; 221 lines in all | inside the table (below) |

**The ten groups measured on darwin for the first time, and cpython-a, -b, -c and numpy-others, as
the lane measured them against main:**

| group | predicted range | actual | inside? |
|---|---|---|---|
| `cpython-c` | +2.8% to +3.2% | +2.995% (GREW) | yes. 044's row, closed by Finding 1's clause, which the lane passed |
| `cpython-a` | +0.05% to +0.15% | +0.078% (GREW) | yes. 038's claim plus 044's clause |
| `cpython-b` | +0.05% to +0.15%; +3.3% contingency | +0.044% (GREW) | it grew less than my lower bound and less than 038's claimed +0.067%. Its growth is claimed, not new. The two-valued contingency did not happen |
| `cpython-archives` | −1.7% to +0.8% | +0.141% (GREW) | yes. Above 038's "±0.1%" but inside my table's range for this noisy group |
| `pandas-groupby` | −0.12% to +0.10% | +0.039% (GREW) | yes. Inside 038's ±0.1% |
| `pandas-internals` | −0.17% to +0.04% | +0.029% (GREW) | yes. Inside 038's ±0.1% |
| `pandas-io-parser` | −0.05% to +0.17% | +0.019% (GREW) | yes. Inside 038's ±0.1% plus 044's clause |
| `numpy-core` | −0.17% to +0.07% | −0.092% | yes. Not grown |
| `numpy-others` | −0.06% to +0.07% | −0.030% | yes. Not grown |
| `pandas-frame` | −0.15% to +0.05% | −0.052% | yes |
| `pandas-io-formats` | −0.20% to +0.03% | −0.037% | yes |
| `pandas-libs` | −0.18% to +0.03% | −0.010% | yes |
| `pandas-reshape` | −0.14% to +0.07% | −0.003% | yes |
| `pandas-tslibs` | −0.20% to +0.02% | −0.013% | yes |

`cpython-fs` +0.167% and `numpy-lib` −0.046% are equal to CI's macOS values.

**Risk line resolved:** the oracle goldens check passed (it reproduces `scipy_edges` and
`machine_learning`). The prior-art licence check passed. Finding 2's claim-list text is still owed
in 044's landing notes. Finding 1 is closed by the clause passed in `--accept-growth`; its text
goes into 044's claim list with the landing notes.

**Rows outside the prediction table and the claim lists:** none. The one reading outside a stated
range is `cpython-b`, which grew less than both the range and 038's claim. That is a smaller
growth of a claimed row, so it ejects nothing.

## Verdict (final)

Lands as merged at `e9a76ce`. Every lost, fewer, absent, gained, more and grown line of the lane's
acceptance is in the prediction or a claim list, and no entry is ejected.
