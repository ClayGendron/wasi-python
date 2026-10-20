# Review of 042 — seaborn and reportlab (the build)

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent (Claude), which wrote none of spec 042 or spec 038 and reviewed
  neither before. Time box: 45 minutes of reading (a package, build-class), plus waiting for CI.
- **Reviewed:** `ecc2423..69b3e34` on `spec/042-seaborn-and-reportlab`, which is three commits.
  The code is at `3c0b11d`; `69b3e34` changes `context/` only. It is a stacked build on spec
  038's `ecc2423`, so only 042's commits are reviewed here. The set is `SHA256SUMS` `c5baf6ff…`
  (EXECUTED: `shasum -a 256 build/artifacts/SHA256SUMS` in the worktree).
- **Run:** 39429969313 on `69b3e34`, whose code equals `3c0b11d`. Conclusion: failure, by growth only.
  - 22 jobs are green. They include both `rebuild from the pins` jobs, `the same bytes from every
    host`, `build and judge (arm64 macOS)` (the zero-patch step with 26 trees), the three
    `verify` jobs and every Windows leg.
  - Three macOS judge shards are red, each with `0 fail` and `lost 0`:
    - `own-guest`: 177 grew, 22 gained, 2 blocked;
    - `own-embedding`: 33 grew;
    - `upstream-macos`: 2 grew.
  - Every red line is a GREW line against main's `d066695`. There is no G7 line.
  - Its macOS records equal those of the builder's run 39421194888 in every status and every fuel
    row (EXECUTED, row by row). The builder's run has the same shape: the same three shards and
    the same counts, with 0 fail, lost 0 and no G7.
- **Re-ran:**
  - Five node ids on the worktree's set. Lane lock absent. Output in the scratch file
    `probe1.txt`. The ids: `test_a_left_out_folder_is_not_packed`,
    `test_reportlab_notice_carries_its_third_party_parts`,
    `test_seaborn_notice_carries_its_vendored_licences`,
    `test_reportlab_fonts_are_not_in_the_zip`, `test_seaborn_takes_its_scipy_paths[plain]`.
    Result: 5 passed, exit 0, ratchet lost 0.
  - My own script compared both notices with the pinned archives, byte for byte.
  - Two runner probes of `load_dataset`, through `wasi_python.run` on the snapshot.
  - A per-row comparison of the macOS shard records: 038's run 39415728849 (`ecc2423`) against
    042's run 39421194888 (`3c0b11d`).

## Acceptance criteria against evidence

1. **The checks exist and were seen failing first.** Met.
   - READ: `build/042/seen-failing-on-main-set.txt` has 13 failed and 1 passed. The one pass is
     the font check, as criterion 1 expects.
   - READ: the mutant files.
   - EXECUTED: the unit check's three spellings that should stop the build (`pkg/gone`, `pkg/su`,
     `pkg/sub/mod.pyc`) do stop it.
   - One part was never seen failing: the amended `load_dataset` assertion that no `~` folder is
     made (amendment 8). My probe 2 shows the set-up it was meant to catch does not happen through
     the runner (finding 2).
2. **The zip's names and bytes.** Met.
   - EXECUTED: the zip has 199 members under `reportlab`, `seaborn` and their `.dist-info`.
     These are 197 `.pyc` files and the two `METADATA` files.
   - No member is under `reportlab/fonts/` or `reportlab/graphics/barcode/`, and no name ends in
     `.pfb`, `.afm` or `.sfd`.
   - READ: the builder's `criterion2-and-mutants.txt` shows +2,041,073 bytes and `python.wasm`
     equal to 038's.
3. **The same bytes everywhere.** Met. READ, run 39421194888:
   - `rebuild from the pins` passed on both Linux hosts;
   - `the same bytes from every host` passed;
   - `build and judge (arm64 macOS)` passed, which holds the zero-patch step with 26 trees.
4. **The judge.** Met, apart from the growth account (finding 1).
   - EXECUTED, from the records: every new check passes on all three systems in CI.
   - The oracle check (`test_goldens_reproduce_under_the_pinned_oracle`) is blocked on CI on every
     system. Its local `regen.py --check` on darwin-arm64 is the builder's (READ).
5. **The numbers recorded.** Met (READ, the landing notes). The wheel is 84,660,765 bytes.
6. **The release.** Met as far as a branch run can go. Every job passes, the publishing ones
   aside, except the three growth-only macOS shards, on both runs. `gather` and the publishing jobs
   are skipped, as on 038's run.

## Findings, most severe first

1. **Medium: the growth account and the claim list leave rows out.** (Landing notes, "Decision
   12's table" and "For the lane".) They were built from the local fast tier, and every row was
   held to the metadata-reader cap, which is the looser one. So slow rows, and rows between the
   two snapshot caps, are missing.
   - **The evidence.** EXECUTED: I compared the macOS records of 038's run 39415728849 with 042's
     run 39421194888, row by row. Where a row was in both runs, the numbers equal the builder's
     local numbers exactly. So these rows are 042's own.
   - **Rows over their cap, not named.** Decision 12 caps a snapshot check that reads neither
     metadata nor resources at +0.70 M. Eighteen snapshot rows grow past that, by +0.74 M to
     +2.20 M. Two of them also pass the 1.89 M metadata cap. The builder's list names none of
     them. They are:
     - `test_plot_contour_job_matches_native[snapshot]` +2,204,755 (slow, not run locally);
     - `test_scipy_numeric_job_matches_native[snapshot]` +2,147,965 (slow);
     - `test_scipys_dotted_builtins_keep_their_import_names[snapshot]` +1,807,024;
     - `test_a_flat_convex_hull_raises_qhullerror[snapshot]` +1,730,098;
     - `test_a_singular_solve_raises_linalgerror[snapshot]` +1,605,081;
     - `test_ctypes_values_scipy_makes[snapshot]` +1,536,941;
     - `test_ctypes_stand_in_names_what_packages_import[snapshot]` +1,388,228;
     - `test_scipy_lapack_job_matches_native[snapshot]` +1,359,080;
     - `test_read_html_uses_lxml_by_default[snapshot]` +1,300,792;
     - nine more between +0.74 M and +1.16 M: `highs_reports…`, `matrix_market…`,
       `workers_run_serially…`, `a_python_callbacks…`, `scipy_edges_job`,
       `numpy_and_pandas_are_builtin…`, `scipy_solvers_job`, `regex_is_builtin…` and
       `the_guest_package_round_trips…`, each `[snapshot]`.
   - **A plain row over its cap.** `test_a_reread_after_invalidate_caches_is_the_fast_read` grows
     +8,684,729. That is over the plain cap of 5.97 M + 0.2% (about 7.77 M). It is not named.
   - **A fall not claimed.** `test_plot_line_job_matches_native[snapshot]` falls by -2,062,838.
     The claim list says three rows fell, "by at most 531,079".
   - **The growth flag is narrower than the claim list.** `--accept-growth` names only the start
     rows and the zip-walking rows. It does not name the networkx, metadata, pure-paths, Sobol,
     pandas-tz or upstream rows.
   - **Why it is not a regression.** No row is lost. Each of these rows is at most +0.06% of its
     accepted value, or +0.97% for the reread. That looks like the same member cost (INFERRED).
   - **Failure.** The lane accepts growth that Decision 12 calls "a finding for the build review,
     not a reason to accept". It would do so with no stated reason, and with one fall it never
     claimed.
   - **What closes it.** The builder compares the two CI records, with the slow rows included.
     For each row above its own row's cap, the builder names it with a reason: it reads metadata
     or resources, or it pays the member cost twice (the reread), or layout. The builder adds
     `plot_line[snapshot]` to "fell". The `--accept-growth` flag gains the over-cap groups, still
     beginning "042" and still paste-safe.
2. **Medium: the README and CHANGELOG wrongly say a writable root gets a `~` folder.**
   (`README.md`, *seaborn and reportlab*, the `load_dataset` line; `CHANGELOG.md`, the 042 entry.)
   Both say that with a writable root, `load_dataset` "makes a folder `/~/.cache/seaborn` in that
   root and then raises `URLError`". Through the runner that is false.
   - **Why.** With a writable root, `/tmp` is writable, so the runner sets `HOME` to a fresh
     `/tmp/.home-…` (`run()`'s docstring, `env`). seaborn's cache goes there.
   - **The evidence.** EXECUTED, `wasi_python.run(…, root=<tmp>, env={"MPLCONFIGDIR": "/mpl"})`:
     - `HOME` is `/tmp/.home-13ea2b8a…`;
     - `seaborn.get_data_home()` is `/tmp/.home-13ea2b8a…/.cache/seaborn`;
     - `load_dataset("tips")` raises `URLError … unknown url type: https`;
     - after the call, the root holds only `mpl/`, `tmp/` and `usr/`, so there is no `~` folder.
   - **Where the `~` folder does appear.** Decision 8's third case came from the pre-build review's
     driver, which gives a writable root and no `HOME`. So a `~` folder is made only by an embedder
     that gives a writable root without a `HOME`.
   - **The check.** The amended check's `assert not (cfg / "~").exists()` is right, but it was
     never seen failing. Through the runner, no case makes the folder.
   - **Failure.** A reader expects litter in their root that the runner does not leave. The
     published account of the sandbox is wrong about a write, which §4.11 asks to be documented
     exactly.
   - **What closes it.** The builder rewrites the line in both files. Suggested text: "with a
     writable root (where the runner also gives a fresh `HOME` under `/tmp`), it makes its cache
     folder under that `HOME`, removed after the call, and then raises `URLError` (`unknown url
     type: https`); an embedder that gives a writable root and no `HOME` gets a folder `/~/.cache/
     seaborn` in that root". Decision 8 gets the same note as amendment 10.
3. **Low: the roadmap still names a barcode change that will not happen in 042.**
   (`context/roadmap.md:110–111`.) It still says "042 (seaborn and reportlab; question 73 adds
   the barcode folder, written in before its build)". Amendment 9 says this is superseded. The
   reserved follow-up that ships the folder has no roadmap line, which the self-check's "every
   reserved follow-up has a roadmap line" asks for.
   - **Fix text:** "042 (seaborn and reportlab, without reportlab's barcode folder; decision 73's
     later change ships `reportlab/graphics/barcode/` with the QR and Code 128 golden lines and
     Sarna's acknowledgement in the README and CHANGELOG)".
4. **Low: three Sarna files have a different copyright year.** (`scripts/assemble_artifacts.py`,
   the `REPORTLAB_NOTICES` heading; Decision 4a.)
   - The heading says the notice "heads `__init__.py`, `code128.py`, … and `usps.py`".
   - Decision 4a says all seven carry "Copyright (c) 1996-2000 Tyler C. Sarna".
   - READ, the pinned wheel: `code128.py`, `code93.py` and `fourstate.py` say "Copyright (c) 2000
     Tyler C. Sarna". Apart from that year, the seven 31-line blocks are byte for byte the same.
   - Nothing ships from that folder now, so nothing is missing today.
   - **Fix text, for decision 73's later change:** the Sarna part's heading adds "(code128.py,
     code93.py and fourstate.py date their copyright 2000)", or the notice also carries that
     variant. Decision 4a reads "carry Tyler C. Sarna's copyright (1996-2000; 2000 in code128,
     code93 and fourstate)".

**Notes (no rank):**
- **C3 and §4.12.** §4.12's approval of Sarna's modules says "every material that mentions
  barcodes says" the acknowledgement. The README's barcode line mentions barcodes, and it does
  not carry the sentence. C3 and decision 73 put the sentence in with the later change, and the
  licence binds only once the code is distributed, so this holds today. Adding the sentence now
  would cost nothing; that is the lane's choice.
- **An unrelated hunk.** `assemble_artifacts.py`'s `xz` entry is reflowed onto one line, exactly
  100 columns, by `ruff format`. It is unrelated to 042 and harmless; the base file was not
  formatted.
- **"Reproduces on every platform" is not run.** That `pdf_reports` reproduces under the oracle on
  every platform is INFERRED. The oracle check is blocked on CI everywhere, and `regen.py --check`
  ran on darwin-arm64 only.

## The focus items

1. **Licences.** They hold. EXECUTED, byte for byte against the hash-checked pins (`shasum`
   equal to `SHA256SUMS`):
   - `LICENSES/reportlab.txt` has five parts:
     - the wheel's `licenses/LICENSE`;
     - the three leading `#` blocks, of 31 lines (`barcode/__init__.py`), 45 (`_glyphlist.py`)
       and 22 (`qrencoder.py`);
     - the MIT text, equal to `wasi-libc-2e6fb9d8-LICENSE-MIT` (`23f18e03…cca3`, the same bytes
       as the old `161b3195` pin).
   - **C1.** "Tyler C. Sarna" appears in exactly seven `.py` files of the wheel. `test.py` names
     him only in prose, at line 192.
   - **C2.** The seven names are in the part's heading line, outside the compared bytes.
   - **C3.** No barcode or font member is in the zip. The README and CHANGELOG name Sarna but do
     not carry the acknowledgement sentence.
   - **seaborn.** `LICENSES/seaborn.txt` holds `LICENSE.md` and the five `licences/` files
     (APPDIRS, HUSL, NUMPYDOC, PACKAGING, SCIPY), each byte for byte the sdist's.
   - Nothing else in the 143 shipped reportlab modules carries a third party's licence (READ: a
     grep for copyright and licence wording outside the two folders left out).
2. **Amendment 2.** It holds.
   - READ: `make_stdlib_zip._under` matches `folder.rstrip("/") + "/"` as a prefix, so it
     matches folders, never string prefixes.
   - READ: `Selection.check` raises one `SystemExit` line naming every unmatched `--drop`.
   - EXECUTED: the unit check covers `pkg/sub` and `pkg/sub/`, that `pkg/subway.py` is kept, and
     that `pkg/gone`, `pkg/su` and `pkg/sub/mod.pyc` each stop the build.
3. **Amendment 8.** The check was not weakened.
   - EXECUTED: with no root and a writable `/cfg`, the working folder is `/`, which does not
     exist. `os.makedirs("~/.cache/seaborn")` answers `[Errno 44] … '~'`, before any fetch.
   - The grant holds only matplotlib's `fontlist-v3.11.0.json`.
   - Nothing outside the grant is writable, so nothing can be written there. The added
     "no `~` in the grant" assertion is stricter than the PermissionError it replaces.
   - What it got wrong is the writable-root claim in the README (finding 2).
4. **The growth rows.** The builder's five reasons are true. The list of rows is incomplete
   (finding 1).
   - **The zip-walking rows** grow 2.9–3.6%, against 199/5,062 = 3.9% more members. The
     pre-existing checks pass on their own bounds.
   - **The pure-paths check.** Its program calls `zipfile.ZipFile(...).namelist()` on the whole
     zip (READ), which comes to about 86,000 fuel per member.
   - **The networkx atlas check** grows +18.1 M for two more distributions. That is inside the
     table's 25 M per distribution per read.
   - **Sobol and pandas-tz** read resources (INFERRED, as labelled).
   - Each of these rows is in the claim list. Only the start and zip-walking rows are in the
     growth flag.
   - **Upstream rows, against 038:** `cpython-fs` +75.7 M (+0.12%) and `numpy-lib` +112.1 M
     (+0.08%). Both are inside the plain cap's 0.2%.
5. **The claim list against the diff.**
   - The new passes, the four unit checks and the extended checks match the diff.
   - The rows changed and not claimed are finding 1's.
   - The flags are paste-safe: no `"`, `$`, backtick or `!` inside. Each begins "042".
6. **Spec 063.** `packages.toml` gives both packages as `later`, closed by spec 067. Spec 067 is
   reserved on main's roadmap (`context/roadmap.md:128–130`, "067 (the pure-Python packages' own
   tests in the release)"), and 39 other entries already name it.
7. **The goldens.** `tests/jobs/statistical_plots.platform` is `darwin-arm64`, and the job is in
   `jobs.PLATFORM_BOUND` (023's rule). `pdf_reports` is not bound. In the guest, both goldens pass
   on all three systems in CI (EXECUTED, from the records).

## The self-check

Every item is present. One is unchecked: "every reserved follow-up has a roadmap line" (finding
3).

## Constitution checks
- **§4.1 (patches):** none carried. `--drop` is a recipe rule.
- **§4.2 (pins):** two pins, URL plus SHA-256, recomputed here.
- **§4.6 (the artifact set):** `python.wasm` unchanged; the zip grows +199 members.
- **§4.10 (claims carry evidence):** held, except finding 2's line.
- **§4.11 (platform semantics documented):** finding 2.
- **§4.12 (licences):** held, and every notice is byte-exact. No font, and no barcode code, ships.
- **§4.15 (safe by default):** reportlab writes in memory with nothing writable (EXECUTED on CI,
  all three systems).
- **§7 (never-do list):** nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)
1. **Fixed, context only.** The landing notes gain *The rest, from CI*: the macOS records of
   042's run 39421194888 against 038's run 39415728849, every row in both, slow rows included
   (`build/042/ci_growth042.py`, `build/042/ci-growth-vs-038.txt`; 227 fuel rows; the reviewer's
   numbers, row for row). Each row above its binary's base cap is named with its reason:
   - the eighteen snapshot rows over +0.70 M: scipy's importers are metadata readers, since
     `import scipy.linalg` imports `importlib.metadata` (EXECUTED on both sets' snapshots,
     `build/042/probe-rows042.txt`: +1.67 M, against +0.48 M for `import numpy` and +0.60 M for
     `import regex`, which import none), so twelve are inside +1.89 M; the version readers
     (`numpy_and_pandas_are_builtin…`, `regex_is_builtin…`) likewise; `plot_contour[snapshot]`
     +2.20 M and `scipy_numeric[snapshot]` +2.15 M, past +1.89 M by 0.31 M and 0.26 M, and
     `read_html…` +1.30 M and `the_guest_package_round_trips…` +0.74 M, by layout (INFERRED:
     `plot_line[snapshot]` falls -2.06 M in the same family, and `import pandas` alone falls
     -118,032, EXECUTED);
   - `test_a_reread_after_invalidate_caches_is_the_fast_read` +8.68 M: it reads the directory
     twice, so it pays the member cost twice (INFERRED);
   - 033's metadata check (+20.2 M, +13.5 M) and `test_metadata_answers_from_the_zips_directory[snapshot]`
     (+1.51 M), inside their metadata caps; the upstream rows inside 0.2%.
   `plot_line[snapshot]` -2,062,838 is in "fell" (four rows). `--accept-growth` names every group,
   still beginning "042" and paste-safe.
2. **Fixed.** The README's and CHANGELOG's `load_dataset` lines take the review's text: through
   the runner with a writable root, the cache goes under the runner's fresh `HOME` in `/tmp`,
   removed after the call, then `URLError`; only an embedder that gives a writable root and no
   `HOME` gets `/~/.cache/seaborn`. Decision 8's note is amendment 10. The check's no-`~`
   assertion now comes first (litter in the caller's grant is the worse failure), and it was seen
   failing (EXECUTED, `build/042/mutant-home.txt`): with a mutant program that drops `HOME` and
   works in the writable grant (`build/042/mutant_home_plugin.py`), the assertion names the
   grant's `['fontlist-v3.11.0.json', '~']`; the real check passes on both binaries
   (`build/042/scipy-paths-reordered.txt`).
3. **Left to the lane**, which fixes main's roadmap line (the lane, 2026-10-20). Amendment 9
   records that C3 supersedes it.
4. **Recorded for decision 73's later change**: the Sarna part's heading then adds "(code128.py,
   code93.py and fourstate.py date their copyright 2000)", and Decision 4a reads "carry Tyler C.
   Sarna's copyright (1996-2000; 2000 in code128, code93 and fourstate)". Nothing ships from the
   folder now.

## Verdict
Lands once finding 1 (the growth account and claim list cover the CI rows above their caps,
with reasons, and the `plot_line[snapshot]` fall) and finding 2 (the README and CHANGELOG
`load_dataset` line, corrected for the runner's `HOME`) are answered.

One line: the packages, the licences and the leave-outs are right byte for byte, and both CI runs
are red by growth only. The growth account misses eighteen snapshot rows, one plain row and one
fall, and the README wrongly says a writable root gets a `~` folder.
