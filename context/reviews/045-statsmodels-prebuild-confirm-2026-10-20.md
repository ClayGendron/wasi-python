# Review of 045 — statsmodels, with formulaic, interface-meta and wrapt (pre-build confirmation)

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write spec 045, its phase 1, the
  2026-10-18 pre-build review or its 2026-10-20 confirmation of 044.
- **Reviewed:** `spec/045-statsmodels` at `194a64d`: phase 1 `0b73a2d` (44 files, on main
  `5805af0`) and one commit after it, `194a64d`, that only touches `context/` (R5a and R6a). The
  diff read was `origin/main...spec/045-statsmodels`. I read the specification in full, with "The
  builder's revision against main" (R1 to R12, R5a, R6a). I also read the original review's 045
  findings and its Disposition, AGENTS.md, the constitution, and `context/reviews/README.md`.
- **Time box:** 45 minutes (a package, build-class). Exceeded by about 15 minutes for the
  dry listing and the probes.
- **Run:** none. This is a pre-build review: nothing is built, and the caller said not to dispatch.
- **Re-ran (EXECUTED, darwin-arm64).** Before running anything, I checked that `build/lane.lock`
  was absent in the main tree. I did not touch the main tree's `build/`. Nothing was written to
  any branch or worktree. All output is under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/5c4a788f-6229-4fb4-8a87-05b4e7e5e695/scratchpad/045-confirm/`.
  - `shasum -a 256` on the builder's `downloads/` copies of the statsmodels sdist, the three pure
    wheels and `mne-python-2c4a3b03-LICENSE.txt`: each equals its `SHA256SUMS` line. Hashing the
    carried patch gives `751e7190…db58`, 2,979 bytes.
  - I unpacked the sdist into `sm-stock/`. `patch -p1 --dry-run` and then `patch -p1` applied
    the carried patch to a copy (`sm-patched/`) with no offset or fuzz.
  - `tools/dry.py` (mine). It imports the branch's and main's `make_stdlib_zip.py` from
    `git archive` copies. It applies the branch's `70_zip.sh` `--drop` and `--keep` lines to an
    install-like tree built as step 59 builds it: `statsmodels/` without `_build/`, plus
    `pyproject.toml`. Then it compares the old and the new `--drop` rule on every member of
    matplotlib's, scikit-learn's, reportlab's and statsmodels' inputs.
  - `tools/probe_patch.py` (mine), run with the builder's oracle venv (`python -I -B`,
    statsmodels 0.15.0, pandas 3.0.6, CPython 3.15.0). It loads datasets through the patched
    `utils.py` from disk and from a zip, with `spector.csv` removed. Separate one-liners checked
    the sixteen shapes, `wrapt.__wrapt__._using_c_extension`, the x13 input, and Tukey's HSD with
    `statsmodels.stats.libqsturng` blocked.
  - `pytest -p no:cacheprovider --noconftest` on scratch copies (`branch/`, `mainrun/`):
    - 045's five unit checks plus wave 08's
      `test_build_scripts.py::test_a_left_out_folder_is_not_packed` against the branch's code:
      **6 passed**.
    - The same five against main's `make_stdlib_zip.py`, `gen_inittab.py` and stand-in:
      **3 failed, 2 passed**, each failure for its stated reason.

## 1. The original review's findings that concern 045

- **Finding 4 (Medium), why a patch and not a recipe: confirmed.** Decision 7 now uses 041's
  form. A recorded recipe was looked for first. The files-where-it-looks route is ruled out,
  because the path lies inside the zip's own name. A run-time replacement "could work here …
  because the read runs when a loader is called". It is rejected on width (`load_csv` and
  `elec_equip`'s `_get_data` would be copies of upstream code), on spec 020's blindness to it,
  and on the missing exit. READ.
- **Finding 5 (Medium), `--leave-out NAME` against 042's check: confirmed, superseded by R3.**
  - **The premise moved.** 042 never added `--leave-out`. It uses 023's `--drop` (wave 08's
    `70_zip.sh` adds `--drop reportlab/fonts` and `--drop reportlab/graphics/barcode`; READ).
  - **The new form.** R3 drops the separate `--leave-out-file` option. It uses 13 `--keep
    statsmodels/datasets/<name>=__init__.py,data.py` lines and 9 `--drop` lines (8 `src/`
    folders and `sandbox/rlsdata.txt`), and widens `--drop` to also take the one member whose
    name equals its argument.
  - **Same 53 members (EXECUTED, `tools/dry.py`).** 554 tree members, 501 kept, 53 left out.
    That is 15 `src/` folders (8 public-domain, 7 of the thirteen) and 21 files outside them.
    The 21 files equal `STATSMODELS_LEFT_OUT_FILES` in the v1.1 check, compared in one collation.
    Every `--keep` found both files it names (`Selection.check()` passed). Under main's rule the
    same lines stop: "matched no member: statsmodels/sandbox/rlsdata.txt".
  - **No other package's members change (EXECUTED).** I ran main's and the branch's `Selection`
    over every member of the inputs the existing drops apply to: the matplotlib 3.11.2 sdist's
    `lib/matplotlib`, the scikit-learn sdist's `sklearn/`, the reportlab 5.0.1 wheel, and
    statsmodels' tree. With main's three drops plus wave 08's two, the old and new rules take the
    same members. The list of differences is empty. With `rlsdata.txt` added, the only
    difference is `statsmodels/sandbox/rlsdata.txt`. No member in those inputs is named exactly
    like an existing drop argument.
  - **Why, from the code (READ).** The only new branch is `name == folder` in
    `Selection.take`. `self.drop` is stripped of trailing `/`. Member names are file names, so
    a folder's own name never arrives as a member (`wheel_members` skips directory entries).
    `--file` and `--metadata` names do not collide with any drop either.
  - **Finding 5's own ask holds.** An exact name is the name before compilation:
    `test_a_drop_takes_one_file_by_its_exact_name` asserts that `api.pyc` does not match the
    member that comes from `api.py`, and that the build stops naming it. No existing check is
    edited. Its residue is L1.
- **Finding 6, for 045 (inherits the weak-duplicate gate): confirmed.** Step 60's gate reads
  `$archives`, which now holds statsmodels' 26 archives, because step 60's package loop gains
  `statsmodels:"$B/statsmodels-modules"` (READ). The link-map check names only scikit-learn's
  generators, which is right for it. statsmodels is C only and has no shared Cython utility
  module, so I expect no weak duplicate from it (INFERRED). See N2.
- **Finding 7 (Low), `open_data_file` and the `ValueError`: confirmed (EXECUTED).**
  - **The patch as carried.** The helper is `_open_data_file`, private. Its summary line ends in
    a period. It falls back to `importlib.resources` only when
    `base_dir.is_relative_to(datasets_dir)`.
  - **From disk, with `spector.csv` removed:** longley (16, 7) and elec_equip (257, 1) load.
    spector raises `FileNotFoundError`. Outside `statsmodels/datasets`, a missing CSV raises
    `FileNotFoundError` and a present one loads, shape (1, 2).
  - **From a zip of the patched package (CPython's zipimport reader):** the same four outcomes.
- **Finding 8 (Low), the message depends on 035's reader: confirmed.**
  `test_left_out_datasets_say_so` compares only `type(e).__name__` against `FileNotFoundError`
  (READ). Acceptance criterion 5 records the guest's message.
- **Finding 9 (Low), `rlsdata.txt` and Decision 10's list: confirmed.** `rlsdata.txt` leaves
  (EXECUTED above). The v1.1 check names it. Decision 10's list of what stays is corrected (READ).
- **Finding 10 (Low), seaborn imports statsmodels: confirmed.** Decision 14 has the row, bounded
  at the plain-start row plus 2 M. READ: seaborn 0.13.2's `regression.py:10-15` tries `import
  statsmodels`, and statsmodels' `__init__.py` imports only `_version`. 042 is in wave 08, so
  this row can only be measured once 045 is rebased onto it (R1 says so).
- **Finding 11, for 045 (`get_rdataset` with each grant): confirmed in the spec, with a residue
  in the README (L4).**
- **Finding 13, for 045 (question 80): confirmed.** R11 records the answer, and the sheet moved
  unchanged.
- **Finding 14, for 045 (wrapt "at import"): confirmed.** Decision 6 says it (READ).

## 2. R1 to R12 against main (`5805af0`)

- **R1: confirmed.** These are on main: `stage_scipy_cimports.sh`, `install_from_plan.py
  --modules-only`, step 58, packaging 26.3, patsy, narwhals and typing-extensions. 042 is not on
  main (READ). Two things still say otherwise: the header's "Depends on … 042 (`--leave-out`)"
  and the Kind line (L3).
- **R2: confirmed.** statsmodels' `git_version.py` does `import setuptools_scm` and calls
  `setuptools_scm.get_version(root=ROOT)`, where `ROOT = Path(__file__).parent.parent.parent`,
  the sdist's top folder, which holds `PKG-INFO` (READ). The stand-in accepts a `str` or a
  `Path` and ignores other keyword arguments. It stops with a one-line message naming the file.
  Running `-m` gives the same answer as before. The unit check failed on main's stand-in with
  `AttributeError: module 'setuptools_scm' has no attribute 'get_version'` and passes on the
  branch. The matplotlib guard passes on both (EXECUTED).
  - The version script writes nothing into the tree at configure time. `--write` only runs from
    `add_dist_script`, or when `_version.py` is missing (READ, `statsmodels/meson.build:38-62`).
    So spec 020's tree check is not disturbed.
- **R3: confirmed (§1, finding 5).** The new unit check failed on main's code with `assert not
  True` and passes on the branch (EXECUTED). One claim is true of main but not of the base 045
  will land on: see L1.
- **R4: confirmed.**
  - **`hdrboxplot` reaches `Pool()`.** It creates a figure first (`create_mpl_ax`,
    `functional.py:366`). `Pool()` is reached unconditionally in `_band_quantiles` (`:461`),
    whatever `use_brute` is. `rng` and `kernel_rng` are its 0.15.0 keyword names
    (`deprecate_kwarg("seed", "rng")`). READ.
  - **The x13 lookup comes first.** `x13_arima_analysis` calls `_check_x12` at its first line
    (`x13.py:549`), before it reads its input. The co2 series resamples natively (526 rows, `MS`).
    EXECUTED and READ.
  - **The judge additions are as listed (READ):** `scan.MESON_BUILDS`, the dotted-builtins
    `own` tuple, `LICENCE_COMPONENTS`, `PACKAGES`, `DISTRIBUTIONS`, `SOURCE_PATTERNS`,
    `SOURCE_COMPONENTS`, the build shard's node id, `packages.toml`, `test_build_progress` and
    `test_artifact_rules`. They are judge changes for `--accept-judge`.
- **R5: the line ranges are exact (EXECUTED, reading the sdist).** `parallel.py` 1-12 is the
  docstring that closes at line 12. `docstring.py` 1 is its only notice line. `qsturng_.py`
  1926-1961 runs from `def _phi` to the docstring's close. `_stl.pyx` 3-13 runs from "(c) 2019
  Kevin Sheppard" to the Cleveland citation. `boxplots.py` 3-4 and `quantile_regression.py` 1-16
  are exact too. `STATSMODELS_PARTS` and `STATSMODELS_LINES` agree with these ranges. The MNE
  text is pinned and verifies.
- **R5a: one claim is wrong (M1).** The other importer claims hold (READ):
  - `tools/docstring.py` is imported by exactly the eight modules R5a names.
  - `graphics/boxplots.py` is imported by `graphics/api.py`, which `statsmodels.api` imports.
  - `quantile_regression.py` is imported by `statsmodels/api.py:143`.
  - `tsa/stl/_stl` is imported by `tsa/seasonal/__init__.py:6` and `tsa/stl/mstl.py:29`.
  - `tools/parallel.py` is imported only inside a function, `distributed_estimation.py:654`.
- **R6 and R6a: for the owner (§5).** The numbers are the builder's own output (READ,
  `build/045/native/`): "1 failed, 20911 passed, 356 skipped, 146 xfailed … in 467.93s", and
  "21412 tests collected". See N1.
- **R7: confirmed (READ).** The weak-duplicate gate covers statsmodels' archives. `--against`
  stops on a CPython builtin's init name. 051's callback scan and 096's slot scan read the plain
  binary, so statsmodels is covered without a list. The Status carries 051's sentence but not
  096's (L2).
- **R8: true on main, and it will move on the base 045 lands on (L1).** The tree count is 27 on
  main plus statsmodels, but wave 08 already makes it 27 with seaborn
  (`wave/08:.github/workflows/release.yml:86`), so after the rebase it is 28. There are 22
  carried patches on main and on wave 08, so 23 holds (EXECUTED, `git ls-tree`).
- **R9: confirmed.** The base set's `SHA256SUMS` is `dc6ba3a5…` (EXECUTED, `shasum` on the
  builder's `build/045/base-set/`).
- **R10: confirmed.** `statistical_models.expected` is 3,007 bytes, SHA-256 `6a855bc1…2bad29`.
  It is recorded on `darwin-arm64` and `PLATFORM_BOUND`. The oracle pins `statsmodels==0.15.0`,
  formulaic and interface-meta by version, and wrapt by URL to the guest's own wheel (EXECUTED and
  READ).
- **R11: confirmed (EXECUTED: hash, apply).** The sheet at
  `context/upstream/patches/statsmodels-0.15.0/0001-datasets-from-a-zip.md` describes the patch
  as carried: private, the `is_relative_to` fallback, `FileNotFoundError` kept. Its
  "When spec 045 is built, this file moves …" paragraph is the unchanged text, as 044's sheet
  kept it (N5).
- **R12:** this review.

## 3. The recipe as it binds the build

- **The four pins** (EXECUTED, hashed). Each wheel has no `.so` or `.pyd`, no
  `entry_points.txt` and no `tests/` folder. wrapt's carries `_wrappers.c` as source and
  `__wrapt__.py`. Natively, with the guest's pure wheel, `_using_c_extension` is `False`.
- **Step 59** (READ, compared with step 58 line by line). It is step 58's pattern, with these
  differences:
  - no OpenMP gate (C only);
  - the version gate (meson's "Project version", `PKG-INFO`, `_version.py`);
  - the stand-in and the pinned packaging wheel on `PYTHONPATH` for `meson setup` alone;
  - no `@NUMPY_INCLUDE@`, because statsmodels asks the target Python for `np.get_include()`
    (`statsmodels/meson.build:1-19`, `run_command` from the source subdirectory with
    `os.path.relpath`; INFERRED to resolve as it does for pandas at step 50);
  - `_build/` removed and `pyproject.toml` copied in.

  Everything unpacks, builds and stages under `build/`. Nothing goes into `recipes/` or the
  system.
- **The cross file** is pandas' flags without the rename header, C only (READ).
- **The include map's suffixes match meson's layout.** statsmodels compiles Cython through a
  `generator(... output: '@BASENAME@.c')` whose outputs meson places in the target's private
  folder. The smoothers are declared in `_smoothers/meson.build`, so their C files are
  `…/_smoothers/_conventional<SO>.p/_conventional.c`. `_tools` is declared in
  `statespace/meson.build`. READ. The step stops unless each entry matched exactly one compile,
  so a wrong suffix ends stage 2, not the link.
- **The four rename headers and `gen_inittab.RENAMED`** agree name for name (READ). The unit
  check fails on main with "two modules share an init function name: ['_conventional', '_tools',
  '_univariate', '_univariate_diffuse']" (EXECUTED). Only these three base names repeat among
  the 19 modules declared literally in statsmodels' `meson.build` files (EXECUTED, `grep`; the
  other seven are declared in loops, and the step's count of 26 covers them).
- **Step 60 and step 70 hunks:** statsmodels' archives are named by import path, as scipy's and
  scikit-learn's are. The tree, the `METADATA` line, three wheels and the 22 rule lines are
  added (READ).
- **`assemble_artifacts.statsmodels_parts`** and the judge's `statsmodels_notice_errors` read the
  same ranges and pinned texts. The datasets part stops the build if a shipped dataset's
  `COPYRIGHT` does not say public domain (READ).
- **Cross-suite effects:** none found. No file under `tests/` on main or wave 08 names
  statsmodels, formulaic or wrapt. pandas' eight upstream groups contain no `importorskip` of
  statsmodels (EXECUTED, `grep` of the pinned pandas 3.0.6 sdist's run folders). Wave 08's
  seaborn jobs call no lowess, logistic or robust fit (EXECUTED, `grep`). So no other check flips
  when statsmodels appears.

## 4. The twelve new guest checks

These are the 11 node ids in `test_v1_3_default_profile.py` plus
`test_v1_1_artifact_set.py::test_left_out_dataset_files_are_not_in_the_zip`. The thirteenth new
artifact check, the notice check, needs the source tree.

- **They test the criteria.** Each maps to a Decision 11 or 12 line:
  - the golden on both binaries;
  - the sixteen datasets' shapes on both binaries (the shapes equal native's, EXECUTED under
    the oracle);
  - the thirteen left out, type only, with `import statsmodels.api` working;
  - formulaic against patsy and wrapt pure, on both binaries;
  - x13 and `get_rdataset` through `wasi_python.run` with no root and no grant;
  - `hdrboxplot` with matplotlib's grant and a config folder;
  - 26 builtins with the four renames, on both binaries;
  - the 21 files and no `src/` member in the zip.
- **Seen failing for the right reason (READ, the builder's
  `build/045/seen-failing-base.txt`, on main's set `dc6ba3a5`).** It shows `FFFFFFFFFFFFs`, 12
  failed and 1 skipped:
  - six fail with `ModuleNotFoundError: No module named 'statsmodels'` (the golden ×2, the
    datasets ×2, the left-out check, `hdrboxplot`);
  - two with `… 'formulaic'`;
  - the builtins check ×2 with `AssertionError: []`;
  - the zip check with "the zip has no statsmodels data";
  - `says_what_it_lacks` with exit 1.

  The skip is the notice check, which needs the source tree (L5). Acceptance criterion 1's
  build-time failures still come later: `NotADirectoryError` without the patch, and the
  left-out check on a zip without the rules.

## 5. The owner's two open points (for information; not ranked)

- **The suite moving to spec 095.**
  - 066's Decision 13 reserves 095 for scipy's and scikit-learn's tests, "statsmodels' too if
    045 adds an entry". So 095 fits its reservation's text.
  - The roadmap's reserved line for 095 does not name statsmodels yet
    (`context/roadmap.md:133`). If the owner picks 095, that line gains it (N4).
  - The one native failure is `statsmodels/graphics/tests/test_tsaplots.py::test_plot_month`
    (READ, `junit.xml`).
  - The `later` entry satisfies AGENTS.md's spec 063 rule, as scikit-learn's and scipy's do on
    main. So statsmodels would ship in 0.1.0 without its suite in the release, like those two,
    unless 095 is also in 0.1.0.
- **The six components.** Three facts the owner should have:
  - **`libqsturng`, and `_phi` with it, is dead code in this build.** statsmodels imports it in
    one place, a fallback that runs only when `scipy.stats.studentized_range` is missing, which
    means scipy older than 1.7 (`sandbox/stats/multicomp.py:78-89`, READ). This build carries
    scipy 1.18.1. With `statsmodels.stats.libqsturng` blocked, `import statsmodels.api` and
    `pairwise_tukeyhsd` both work, p-values `[0.035, 0.001107, 0.028048]`, and libqsturng is
    never loaded (EXECUTED under the oracle). So declining `_phi` costs only a user's direct
    `import statsmodels.stats.libqsturng`. R5a says Tukey's HSD would break; that is M1.
    `_phi`'s own comment says its licence "is not explicitly listed" and that
    `scipy.stats.norm.isf(p)` is "an acceptable alternative".
  - **MNE-Python's text.** `parallel.py` says "License: Simplified BSD" (two-clause). The pinned
    MNE text is today's BSD-3-Clause, "Copyright 2011-2025 MNE-Python authors". Its conditions
    include all of BSD-2's, so shipping it is the cautious choice. `parallel.py` is reached only
    by `DistributedModel.fit`.
  - **The other four are on `import statsmodels.api`'s path:** `docstring.py`, `boxplots.py`,
    `quantile_regression.py` and `_stl`. As R5a says, declining any of them means statsmodels
    stays out.

## Findings, most severe first

1. **M1 (Medium): R5a tells the owner that leaving `stats/libqsturng/` out breaks Tukey's HSD.
   It does not.** (`context/specifications/045-statsmodels.md`, R5a, the bullet "`stats/libqsturng/`
   is imported only by `sandbox/stats/multicomp.py`, which `pairwise_tukeyhsd` uses. Leaving the
   folder out … makes Tukey's HSD raise `ModuleNotFoundError`".)
   - **Failure.** The owner is being asked about `_phi` now. They would weigh a decline as
     losing Tukey's HSD. In fact `multicomp.py` imports libqsturng only in the `except
     ImportError` branch after `from scipy.stats import studentized_range`, which scipy 1.18.1
     provides. EXECUTED: `pairwise_tukeyhsd` gives its p-values with the module blocked, and
     libqsturng is never loaded. This is the same kind of defect as the original review's
     finding 1: an owner decision on incomplete facts.
   - **Fix text** (replace that bullet):
     > `stats/libqsturng/` is imported in one place: `sandbox/stats/multicomp.py:78-89`, as a
     > fallback when `scipy.stats.studentized_range` is missing (scipy older than 1.7). This
     > build carries scipy 1.18.1, so statsmodels' own code never imports it. EXECUTED by the
     > confirming review: with it blocked, `import statsmodels.api` and `pairwise_tukeyhsd`
     > work. Leaving the folder out (`--drop statsmodels/stats/libqsturng`) costs only a user's
     > direct `import statsmodels.stats.libqsturng` (`ModuleNotFoundError`). `_phi` lives
     > inside `qsturng_.py`, so it cannot leave alone; its own comment names
     > `scipy.stats.norm.isf` as an acceptable alternative.

     The lane corrects the owner's question to match, if it has already been put.
   - **Evidence that closes it:** the corrected text. It is context only, so the reviewer or
     the builder may write it in.

2. **L1 (Low): R3 and R8 are written against main, but 045 lands after wave 08.**
   - **Failure.** R3 says "042's `test_a_left_out_folder_is_not_packed` does not exist on main,
     so the review's finding 5 has no check left to protect". Wave 08 brings exactly that check
     (`wave/08:tests/unit/test_build_scripts.py:325`). It also brings two more `--drop` lines.
     R8's tree count of 27 is wave 08's count already, so 045's is 28. A builder who trusts the
     text could skip re-running 042's check after the rebase.
   - **Fix text** (append to R3):
     > After wave 08 (042) lands, its `test_a_left_out_folder_is_not_packed` pins `--drop`'s
     > folder form, and it passes under the widened rule (EXECUTED by the confirming review on
     > the branch's `make_stdlib_zip.py`; its three "matches nothing" cases, `pkg/gone`,
     > `pkg/su` and `pkg/sub/mod.pyc`, still stop). Old and new rules take the same members
     > over the matplotlib, scikit-learn, reportlab and statsmodels inputs for every drop main
     > and wave 08 carry. The builder re-runs the check by node id after the rebase, and the
     > make_stdlib_zip docstring and 042's check docstring are read together.

     Append to R8: "On wave 08's base (seaborn's tree) the count is 28."

3. **L2 (Low): the Status lacks spec 096's binding sentence.** 096 asks the lane to add to each
   unlanded build-class specification: "spec 096's slot scan is green, and a mismatch it finds
   is fixed by a carried patch or an upstream release, never by an exclusion." R7 mentions the
   scan, but the Status carries only 051's. Fix: add that sentence to the Status beside 051's.

4. **L3 (Low): text the revision overrides is still written as the decision.** This is the same
   kind of residue as 044's L3. The places:
   - the Kind line ("new `--leave-out-file` option");
   - Depends on ("042 (`--leave-out`)");
   - Decision 3 (`recipes/statsmodels_build/setuptools_scm.py`);
   - Decision 9's last-but-one bullet, and Decision 12's unit checks
     (`test_a_left_out_file_must_match_one_member`);
   - the Design table (`tests/unit/test_build_scripts.py`, "the three unit checks", "the five
     behaviour checks"; the actual file is `tests/unit/test_statsmodels_build.py`, with five
     unit and six behaviour checks).

   The Status's "the revision governs" makes it unambiguous. Fix: rewrite each place, or start
   each with "(revised: R2 / R3 / R4)", before the build review.

5. **L4 (Low): the README states an INFERRED outcome as fact.** "With `cache=True` they first
   make `~/statsmodels_data`: with no root … `FileNotFoundError` on `'~'`". Decision 11 labels
   this INFERRED for statsmodels, and no check runs `cache=True`. The same holds for
   `hdrboxplot`'s README line until the guest gives it. Fix: the landing notes record
   `get_rdataset("iris", cache=True)` with no root and with a root, measured on the built set,
   and the README keeps only what was measured.

6. **L5 (Low): the notice check was not seen failing.** It was skipped on the base set (no
   source tree). R5 shows only that it passes. Fix: in the build shard, or by hand once stage 2
   has a tree, run `test_statsmodels_notice_carries_its_bundled_parts` against a notice that
   lacks one part (for example `_stl.pyx` 3-13) and record the failure line, as 044 did with
   `_pprint.py`.

7. **N1 (Note):** R6's counts do not add up. The collect-only run says 21,412. The full run's
   outcomes add up to 21,414 (20,911 + 1 + 356 + 146). The one failure is
   `test_tsaplots.py::test_plot_month`. Whichever spec runs the suite should state the run's
   own total and name that test.

8. **N2 (Note):** the weak-duplicate gate's first link with statsmodels should add nothing. If it
   stops, each pattern added to `recipes/weak-duplicates-allowed.txt` is a recipe change with
   its reason, and the build review reads it.

9. **N3 (Note):** 096's named records are "one or more per compiled package with a static
   record". scipy and scikit-learn have none on main either. Whether statsmodels gets one (a
   Cython type it defines) is a judge change for the lane to decide. It is not required by 045's
   text.

10. **N4 (Note):** if the owner answers spec 095, the roadmap's reserved line for 095 names
    statsmodels (045) too (the self-check's "every reserved follow-up has a roadmap line").

11. **N5 (Note):** the facts sheet keeps its future-tense "When spec 045 is built, this file
    moves …" paragraph, as "moves unchanged" requires. 044's sheet did the same. No action.

## Constitution checks

- **§4.1:** holds. One patch, applied with no offset, hashed `751e7190`, its sheet under
  `context/upstream/patches/`, named in the CHANGELOG. The stand-in is a recipe file shared with
  023's.
- **§4.2:** holds. Four pins and the MNE text, each verified (EXECUTED).
- **§4.4:** holds. No new import; the modules link numpy's headers and scipy's capsules.
- **§4.6:** holds. Only `python.wasm`, the zip and `LICENSES/` grow.
- **§4.8:** holds. Everything unpacks under `build/`, and the version script and Tempita run as
  build tools.
- **§4.10:** holds, except M1 (a READ claim that is wrong) and L4 (an INFERRED claim in the
  README).
- **§4.12:** awaits the owner on the six components (§5). The datasets part ships only
  public-domain sets, and the build stops otherwise.
- **§4.15:** holds. Nothing writable is added.
- **§5.6:** this is the confirming pre-build review.
- **§7:** nothing tripped.

## Verdict

**Build once M1 is answered.** M1 is one context-only paragraph, and the owner's question
must carry the corrected fact. L1 to L5 are answered in writing by the build review, and N1 to N5
are recorded in the landing notes. The original findings 4, 5, 6 (for 045) and 7 to 11 are
confirmed. The widened `--drop` changes no other package's members (EXECUTED). The design is
ready to build, with the owner's answers on the six components and the suite still due before
landing.

## One line

The revision answers every earlier 045 finding, and the widened `--drop` leaves out exactly the
same 53 members and nothing else, but R5a tells the owner that dropping libqsturng breaks Tukey's
HSD when it is dead code next to scipy 1.18.1, so correct that before the owner answers, then
build.

## Disposition (the builder, 2026-10-20)

The review above is the reviewer's text, copied unchanged from the lane's scratchpad. The owner
answered both open points through the lane on 2026-10-20. All six components are approved, each
with its notice as phase 1 writes it. statsmodels' suite goes to spec 095, before 0.1.0, and
formulaic, interface-meta and wrapt go to 067. Both answers are written into R5a and R6.

1. **M1: fixed in the text.** R5a's libqsturng bullet is replaced with the review's fix text,
   word for word. It ends by naming the correction. The lane carried the corrected fact to the
   owner, and the owner approved all six, so nothing ships differently.
2. **L1: fixed in the text.** The review's paragraph is appended to R3, and R8 gains "On wave
   08's base, which adds seaborn's tree, the count is 28". After the rebase onto wave 08, the
   builder re-runs `tests/unit/test_build_scripts.py::test_a_left_out_folder_is_not_packed` by
   node id, sets the release tree count to 28, and records both in the landing notes.
3. **L2: fixed.** The Status carries 096's sentence beside 051's.
4. **L3: fixed.** Each place the revision overrides now starts with "(revised: Rn …)" and the
   new form: the Kind line, Depends on, Decision 3's stand-in bullet, Decision 9's option bullet,
   Decision 12's unit checks, and the two Design rows (`tests/unit/test_statsmodels_build.py`,
   five unit checks; the golden and six behaviour checks).
5. **L4: answered; done at the build.** The landing notes will record `get_rdataset("iris",
   cache=True)` measured on the built set, with no root and with a root, and what `hdrboxplot`
   raises in the guest. The README then keeps only the measured outcomes. Until then the README's
   two lines stand as drafted. The README changes with the build commit, before any review of
   it.
6. **L5: answered; done at the build.** Once step 59 has a tree, the builder runs
   `test_statsmodels_notice_carries_its_bundled_parts` against a notice without `_stl.pyx` lines
   3-13 and records the failure line, then against the real notice.
7. **N1: fixed in R6.** It now states both totals (21,412 by `--co`, 21,414 by outcome) and names
   `test_tsaplots.py::test_plot_month`.
8. **N2: noted.** If the weak-duplicate gate stops at the first link, each new pattern carries
   its reason, and the build review reads it. The landing notes say what the gate found.
9. **N3: noted for the lane.** No statsmodels record is added to 096's named list; 045's text
   does not require one. It is the lane's call.
10. **N4: fixed.** The roadmap's reserved line for 095 names statsmodels (045), with the owner's
    answer.
11. **N5: no action**, as the review says.
