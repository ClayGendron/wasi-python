# 042 — seaborn and reportlab

- **Status:** **landed 2026-10-20 in wave 08** (042, 066, 099) on main `faa9c93`: accepted on `72bc5ed`, history line 89, 763/850 pass, 0 fail, on a set rebuilt from the same pins in a clone of wave 08 outside the home folder (`SHA256SUMS` `b5a66245`, equal byte for byte to the set rebuilt in the main tree; attempt 1 in the main tree void by macOS host litter, spec 089); the integration review `../reviews/wave-08-integration-2026-10-20.md` (lands once the progress files are copied back unchanged; done, every grown row inside its prediction or its M2 clause); the dry run 39488145764 dispatched as main moved. Before: **Built, a stacked build on spec 038's tip `ecc2423` (main `958a22b`); release run
  39421194888, red by growth only; awaiting its build review** (Landing notes). **Spec 051's callback scan binds this build** (051, Decision 4a; written in when 051 landed): `test_callbacks_have_the_types_cpython_calls` is green, and a mismatch it finds is fixed by a carried patch or an upstream release, never by an exclusion. drafted 2026-10-17. Revised 2026-10-18 against its pre-build review
  (`../reviews/042-seaborn-and-reportlab-spec-2026-10-17.md`): all nine findings are written in
  here and in question 73, and the review's Disposition says where; the reviewer's confirmation
  (2026-10-18) passed it for build with three conditions: **C1**, Sarna's licence is in seven
  files, not eight (`graphics/barcode/test.py` names him only in prose) — the builder corrects
  "eight" in Decisions 4a and 7 and in question 73 at the start of the build and records it;
  **C2**, the line naming Sarna's files sits in the notice's heading, outside the block the new
  check compares byte for byte; **C3**, the barcode folder ships only through the later change
  that follows a "yes" to question 73 (c), with Sarna's acknowledgement. It changes the build recipe and the artifact set, so it is reviewed before it is
  built (constitution §5.6). It is build-class: it touches `scripts/`, `downloads/SHA256SUMS`
  and the release workflow (§5.7). It carries no upstream patch.
- **Owner:** Clay Gendron
- **Kind:** the build recipe (two pins in `downloads/SHA256SUMS` and `scripts/00_download.sh`;
  `scripts/make_stdlib_zip.py` gains `--leave-out`; `scripts/steps/70_zip.sh`;
  `scripts/assemble_artifacts.py`), judge additions and changes (two golden jobs and the
  oracle's two pins, six other checks, one unit check, the judge's package, licence and
  source-tree lists, spec 033's metadata set), the release workflow's tree count, `README.md`,
  `CHANGELOG.md`, `LICENSES/`.
- **Depends on:** specifications not yet built, each landing first (Decision 13): 023
  (matplotlib M1: matplotlib, Pillow's `_imaging`, the data grant at
  `/usr/local/lib/python315.zip/matplotlib/mpl-data`, the plot job's recording-platform rule)
  and 039 (tier A: charset-normalizer, which reportlab requires; pypdf, which the PDF job reads
  back with; `build/pure-install/`; `tests/checks/test_v1_3_default_profile.py`;
  `jobs.run_in_guest`). Through 039: 035 (the zip's directory is read once) and 037 and 038
  (scipy, which 039 waits for; seaborn's clustering and kernel densities use it). Landed: 033
  (the zip keeps `METADATA`; `--metadata`; `tree_members`), 020 (carried patches and the tree
  check), 012 (the same bytes from any host), 018 (no litter in the zip). Not waited for: 043
  (matplotlib M2, contourpy) and 041 (Decision 13). Where any of these
  lands in another shape than its text, this specification uses what landed and says so in its
  landing notes.
- **Research it stands on:** `../research/2026-10-17-what-else-the-default-profile-carries.md`
  (tier A's seaborn and reportlab rows; "Where it stopped": neither was run, for want of
  matplotlib and Pillow; `outputs/reportlab.txt`, reportlab stopping at
  `ModuleNotFoundError: No module named 'PIL'` in today's guest);
  `../research/2026-10-17-matplotlib-on-the-current-line.md` (the research matplotlib binary the
  drafting ran in); spec 039, Decision 15 (this specification named, its pins recorded: 247
  members, 3,312,570 bytes); spec 041, Decision 4 (a pure package that needs a patch comes from
  its sdist) and Decision 9 (ordering with this one); the owner's decision 43 (both approved,
  with their licences; constitution §4.12). **The drafting runs** (EXECUTED 2026-10-17 in the
  session's scratch folder, outside the repository; nothing in the repository was changed by
  them):
  - PyPI's JSON for both: the current release, its files and their SHA-256; the reportlab wheel
    and the seaborn sdist downloaded and their hashes recomputed (`shasum -a 256`, equal to
    PyPI's); the seaborn wheel (039's download) and the reportlab sdist downloaded to compare;
  - each archive READ: the wheels' `.dist-info`, the sdists' licence files, every non-Python
    file, the font files' copyright strings, and the code paths named below;
  - the members and deflated bytes step 70 would add, computed with step 70's own
    `wheel_members`, `walk`, `pyc` and `member` (spec 033's, imported read-only from
    `scripts/`) under the line's Python 3.15.0;
  - **the guest:** the research matplotlib binary (`python-mplp-stripped.wasm`, plain reactor,
    matplotlib 3.11.2, Pillow 13.0.0, kiwisolver 1.5.1) on scratch zips: its own zip (2,432
    members) plus charset-normalizer 3.5.2 and pypdf 6.21.1 (039's pins), minimal `METADATA`
    for numpy, pandas, matplotlib and pillow (stand-ins for 033's and 023's), and the two
    packages packed by step 70's functions; run through the judge's `harness.guest.run` with the
    data grant, a writable `/out` and `MPLCONFIGDIR`; and once with `/` read-only and no
    writable folder, to model the runner's default (spec 025). The research set carries
    contourpy and `_qhull`, which M1 leaves out; the two jobs import neither (EXECUTED: their
    `sys.modules` at the end);
  - **natively:** CPython 3.15.0 (the oracle's pinned interpreter) with the pinned numpy,
    pandas, matplotlib, Pillow, pypdf, charset-normalizer and the two packages, once without
    and once with scipy 1.18.1 (037's pin); each job under `PYTHONHASHSEED` 0 and 1, and once
    with `TZ=Asia/Tokyo` and `LC_ALL=de_DE.UTF-8`; reportlab zipped on `sys.path` natively;
    `zipimport.zipimporter` on CPython 3.12.12, 3.13.11 and 3.15.0.

  **The revision's runs** (EXECUTED 2026-10-18, the same set-up): the revised jobs (no barcode
  or QR line in `pdf_reports`; a `seaborn.objects` line in `statistical_plots`) natively without
  and with scipy, under both seeds, and in another time zone and locale; in the guest on a
  zip with both `reportlab/fonts/` and `reportlab/graphics/barcode/` left out; the members and
  bytes of that zip; seaborn's scipy-path attributes natively with and without scipy.

  **The pre-build review's runs** (`../reviews/042-seaborn-and-reportlab-spec-2026-10-17.md`,
  "Ran"): the pins against PyPI; the 215 members from the pins, equal to the drafting zip's;
  the jobs natively with numpy's OpenBLAS wheel and 037's scipy pin; the seaborn job in the
  guest; `load_dataset` with nothing writable, with only `MPLCONFIGDIR` writable and with a
  writable root; the modules `import seaborn` adds with and without scipy; which notices
  survive compilation. Findings marked "the review" are from these.

  The drafting programs, their outputs and the measurements are in the scratch folder named in
  the drafter's report; the builder writes the jobs from Decision 10, not from those files.

## The problem

Agents draw statistical plots and write PDF reports. seaborn is the second most used plotting
library in the memo's usage counts, and reportlab the standard way to build a PDF from code
(the memo's finding 1). Both are pure Python, and both were approved with tier A (decision 43).
Neither could be run when tier A was specified: seaborn needs matplotlib, and reportlab imports
Pillow when it is imported (`reportlab/lib/utils.py:15`, `from PIL import Image`; the memo's
guest run stopped there). Spec 023 brings both. So spec 039 left them to this specification,
with one warning: reportlab finds its fonts under `reportlab/fonts/` by path, which may fail
from a zip (039, Decision 15).

The drafting ran both in a guest with matplotlib. Almost everything works and equals native
Python byte for byte. Four things needed a decision:
- **reportlab's bundled fonts.** They fail from the zip (`TTFError: Can't open file
  "Vera.ttf"`), because of an upstream bug that any Python 3.13 or later has. And most of them
  carry licences the owner has not approved: Adobe and Monotype Type 1 programs marked "All
  Rights Reserved", and a GPL font.
- **seaborn's notices.** Its wheel ships one licence file. The five licences of the code it
  vendors are only in its sdist.
- **reportlab's third-party code** (the pre-build review's finding 1). Its barcode modules are
  Tyler C. Sarna's, under the four-clause BSD licence with its advertising clause, which §4.12
  does not list; its glyph list is Adobe's (BSD-3-Clause); its QR encoder is MIT. Their notices
  are comments, which compilation drops, so the zip would ship the code with no notice.
- **What a golden can print.** PNG bytes and any raster inside an SVG go through deflate, whose
  library differs between the oracle and the guest; a least-squares line moves by the last bit
  between numpy's own `lapack_lite` in the guest and the host's LAPACK.

## Decisions

1. **What goes in: seaborn 0.13.2 and reportlab 5.0.1, pure Python, nothing native.** Their
   requirements are already in the profile when this is built (READ, each `METADATA`):
   - seaborn: `numpy>=1.20,!=1.24.0`, `pandas>=1.2`, `matplotlib>=3.4,!=3.6.1` (2.5.2, 3.0.6
     and 3.11.2). Its `stats` extra is scipy and statsmodels: scipy comes with 037;
     statsmodels with tier B (decision 48).
   - reportlab: `pillow>=9.0.0` (13.0.0, spec 023) and `charset-normalizer` (3.5.2, spec 039,
     used only by `reportlab/lib/rparsexml.py`). Its extras stay out: `accel` (`rl_accel`, a C
     extension), `pycairo` (`rlPyCairo`, `freetype-py`), `bidi` (`rlbidi`) and `shaping`
     (`uharfbuzz`).

   No compiled code is added: `python.wasm` does not change. Both are current on PyPI on
   2026-10-17 (seaborn 0.13.2 uploaded 2024-01-25; reportlab 5.0.1 on 2026-08-20; READ). The
   two add **199 members and 2,036,192 bytes** to the zip (Decision 12), not 039's 247 and
   3,312,570, because reportlab's fonts are left out (Decision 4) and, until the owner approves
   the four-clause BSD, its barcode folder too (Decision 4a).
2. **The pins: seaborn by its sdist, reportlab by its wheel.**
   - **seaborn's sdist, not its wheel.** The wheel's `.dist-info` holds one notice,
     `LICENSE.md`. seaborn vendors five pieces of other projects' code in `seaborn/external/`
     (appdirs, husl, numpydoc's `docscrape`, packaging's `version`, scipy's `kde`), and their
     licences are only in the sdist, under `licences/` (READ: `tar -t`). The zip ships the
     vendored code as bytecode, and four of the five licences ask that a binary
     redistribution carry the notice. The sdist is one pin that holds the code and every
     notice. **The same members, EXECUTED:** the sdist's `seaborn/`, walked by step 70's `walk`,
     gives 54 members; the wheel's `wheel_members` gives the same 54 names and bytes outside
     `.dist-info`. Its `PKG-INFO` equals the wheel's `METADATA` byte for byte (`cmp`), and its
     `LICENSE.md` the wheel's. Its top folder is `seaborn-0.13.2`, its file name without
     `.tar.gz`, as spec 020's rules require. It has no `.egg-info`.
   - **reportlab's wheel.** Its sdist is not the same package: the wheel has
     `reportlab/lib/extformat.py`, which the sdist's `src/reportlab/` lacks, and the sdist has
     three files the wheel does not (`MANIFEST.in` and two text files under
     `graphics/barcode/`; EXECUTED, the same comparison). The sdist holds no notice the wheel
     lacks: its `LICENSE` equals the wheel's `licenses/LICENSE` (`cmp`). With no patch to carry
     (spec 041, Decision 4), the wheel is the pin.
   - The lines for `scripts/00_download.sh`, after spec 039's block of pure-Python pins (one
     line per pin, as spec 003 requires):

     ```sh
     get https://files.pythonhosted.org/packages/86/59/a451d7420a77ab0b98f7affa3a1d78a313d2f7281a57afb1a34bae8ab412/seaborn-0.13.2.tar.gz seaborn-0.13.2.tar.gz
     get https://files.pythonhosted.org/packages/db/cb/dacbc268cb68d0428ea2cbd85266195a9ab3e677449589ddae59bd7542ac/reportlab-5.0.1-py3-none-any.whl reportlab-5.0.1-py3-none-any.whl
     ```

     and for `downloads/SHA256SUMS` (each equal to PyPI's digest and recomputed from the
     downloaded file, 1,457,696 and 1,957,258 bytes):

     ```
     93e60a40988f4d65e9f4885df477e2fdaff6b73a9ded434c1ab356dd57eefff7  seaborn-0.13.2.tar.gz
     1c36e6bb0e71780c72331eba60da7f602e8d4389a8723825af71342e49d791e8  reportlab-5.0.1-py3-none-any.whl
     ```

     Both are host-neutral. `MANIFEST` gains a `pin` line for each through
     `assemble_artifacts.py`'s existing loop. Spec 039 recorded seaborn's wheel
     (`636f8336…1987`) as a fact; it was never pinned, so nothing is replaced.
3. **The pure paths, and what has none.**
   - **reportlab without `_rl_accel`.** `reportlab/lib/rl_accel.py` tries
     `from _rl_accel import <name>` for each of its eleven functions and, on `ImportError`,
     defines the Python version (READ, lines 20–30 and below). With no `_rl_accel` in the
     guest, every function is the Python one. The drafting's PDFs equal native ones byte for
     byte (Decision 10), and native here also had no `rl_accel` (it is an extra).
   - **No bitmap rendering in reportlab.** `reportlab.graphics.renderPM` needs `rlPyCairo`
     (`rl_settings.py:169`: `renderPMBackend='rlPyCairo'`, "rl_renderPM is gone"). It is a
     Cairo binding, not carried, so `renderPM.drawToString(…, fmt="PNG")` raises
     `RenderPMError: cannot import desired renderPM backend rlPyCairo`, exactly as natively
     without it (EXECUTED both). A drawing goes to PDF (`renderPDF`) or SVG (`renderSVG`); a
     bitmap chart comes from matplotlib or seaborn.
   - **seaborn** is pure. Its optional paths: kernel densities use `scipy.stats.gaussian_kde`
     when scipy imports and its own copy (`seaborn/external/kde.py`) when not; `clustermap`
     needs `scipy.cluster`; `regplot(lowess=True)`, `logistic=True` and `robust=True` need
     statsmodels (READ, `_statistics.py:32`, `_stats/density.py:10`, `matrix.py:11`,
     `regression.py:11`). Each is tried **when seaborn is imported**, inside
     `try … except ImportError`. So once 037 is in the set, `import seaborn` also imports
     `scipy.stats` and `scipy.cluster.hierarchy`: natively it adds 971 modules with scipy, 502
     of them scipy's, against 407 without (the review, EXECUTED). seaborn catches only
     `ImportError`, so a scipy that failed to import that way would leave seaborn on its own
     copies, silently; a check makes the scipy path visible (Decision 11). EXECUTED natively:
     with scipy, `seaborn.matrix._no_scipy` and `seaborn._statistics._no_scipy` are `False`
     and `seaborn._statistics.gaussian_kde.__module__` is `scipy.stats._kde`; without it they
     are `True`, `True` and `seaborn.external.kde`.
4. **reportlab's fonts are left out of the zip.** `reportlab/fonts/` holds 32 files, 1,151,736
   deflated bytes of the wheel's 2,771,471 (EXECUTED). They are left out, for three reasons
   that each suffice:
   - **Their licences are not approved** (§4.12: "Nothing with a licence the owner has not
     approved is linked in"). READ from the files: sixteen Type 1 programs (`_a______.pfb` to
     `zy______.pfb`: Courier, Symbol, ZapfDingbats, Adobe Sans and Serif MM, and eight whose
     notices name Arial and Times New Roman) that say "Adobe Systems Incorporated. All Rights
     Reserved", eight of them under Monotype's copyright too, with no grant to redistribute;
     Dark Garden
     (`DarkGardenMK.pfb`, `.afm`, `.sfd`) under the GPL version 2 or later with a font
     exception; `callig15` under its author's own free-use terms; `hb-test.ttf`, a test font
     with no notice. Only the four Bitstream Vera files have terms the owner has approved (for
     matplotlib's fonts). reportlab's own `LICENSE` (BSD) does not cover the fonts.
   - **None can be read from the zip.** reportlab finds a zip install through
     `zipimporter._files` (`reportlab/lib/utils.py`, `zipImported` at line 145 and the block
     from line 273; READ). CPython 3.13 replaced that attribute with `_get_files()`
     (EXECUTED: `hasattr(zipimporter(…), "_files")` is `True` on 3.12.12, `False` on 3.13.11
     and 3.15.0). So reportlab decides it is installed as files, sets `__rl_loader__` to
     `None`, and `rl_isfile` and `open_for_read` never look in the zip:
     `TTFont("Vera", "Vera.ttf")` and a path inside the zip both raise `TTFError: Can't open
     file …`, and embedding a Type 1 font from it raises `AssertionError: file … not found`
     (EXECUTED in the guest; and natively with reportlab zipped on `sys.path`, the same
     `TTFError`). It is an upstream bug on every Python from 3.13.
   - **Nothing else needs them.** The fourteen standard PDF fonts (Helvetica, Times, Courier,
     Symbol, ZapfDingbats) are drawn from metrics in reportlab's Python modules and are not
     embedded; the `.pfb` files serve only `renderPM`, which has no backend here (Decision 3).
     **EXECUTED:** the drafting's reportlab probe gave the same output, line for line, on a zip
     with the fonts and on one without them.

   **Unicode text still works, with a real font file.** `TTFont` takes any TrueType file the
   guest can open. matplotlib's data grant is a real folder, so
   `os.path.join(matplotlib.get_data_path(), "fonts", "ttf", "DejaVuSans.ttf")` works in every
   call (DejaVu Sans is Bitstream Vera extended; its terms are approved). EXECUTED: "Grüße,
   naïve café: Σ x² ≤ 10 €" embedded in DejaVu Sans gave a PDF equal to native byte for byte
   (42,199 bytes), and pypdf read the text back. A font in a granted folder works the same way.

   **Why not a carried patch** to make the zip's fonts readable (a few lines in
   `reportlab/lib/utils.py` using `_get_files()`): it would serve only the four Vera files,
   which DejaVu supersedes, and §4.1 and §6.2 ask for as few patches as can be. The bug is the
   owner's to report or not (question 73); nothing here waits on it.

   **4a. reportlab's barcode folder is left out too, until the owner approves the four-clause
   BSD** (the review's finding 1). READ from the wheel's files:
   - seven modules under `reportlab/graphics/barcode/` (`__init__.py`, `code128.py`,
     `code39.py`, `code93.py`, `common.py`, `fourstate.py` and `usps.py`) carry
     "Copyright (c) 1996-2000 Tyler C. Sarna" under the **four-clause BSD licence**
     (corrected from "eight" at the build, the confirmation's C1: `test.py` names him only in
     prose, "Ty Sarna contributed a barcode module", with no copyright line and no licence;
     EXECUTED at the build, a search of the pinned wheel's `.py` files for "Tyler C. Sarna"
     finds exactly these seven). Its clause 2
     asks a binary redistribution to reproduce the notice. Its clause 3 is the advertising
     clause: "All advertising materials mentioning features or use of this software must
     display the following acknowledgement: This product includes software developed by Tyler
     C. Sarna." §4.12 does not list this licence, and decision 43's "reportlab (BSD)" was read
     from reportlab's own `LICENSE` only.
   - every other module of that folder imports its `__init__.py`, one of Sarna's files, and no
     module outside the folder imports anything in it (READ: `grep -rl barcode`). So the folder
     goes or stays whole: 16 members, 124,642 deflated bytes (EXECUTED).
   - `reportlab/graphics/barcode/qrencoder.py` (in the folder) is "Copyright (c) 2014 Open End
     AB" and "Copyright (c) 2009 Kazuhiko Arase", "Licensed under the MIT license", with no MIT
     text in the file.
   - `reportlab/pdfbase/_glyphlist.py` (outside it, imported by the PDF code) is Adobe's Glyph
     List, "Copyright 2002-2019 Adobe", BSD-3-Clause.
   - The notices are comments, which compilation drops: "Sarna", "Adobe" and "Arase" are in no
     `.pyc` (the review, EXECUTED).

   **Decided now, so nothing waits:** step 70 passes `--leave-out reportlab/graphics/barcode/`
   until the owner approves the four-clause BSD with its acknowledgement (question 73, part c).
   `pdf_reports` draws no barcode and no QR code. EXECUTED: on a zip without the folder, the
   revised `pdf_reports` gave the same eleven lines in the guest as natively, and
   `statistical_plots` the same first seventeen. When the owner approves, one later change removes the
   `--leave-out`, adds a QR code and a Code 128 barcode as SVG lines to `pdf_reports` (the
   drafting's first job drew them, and they equalled native in the guest, EXECUTED), records the
   licence in §4.12, and puts Sarna's acknowledgement in the README's barcode line and the
   CHANGELOG. If the owner declines, the folder stays out and the README says barcodes are not
   carried.

   **The notices ship now, for every third-party part** (Decision 7): Adobe's because its code
   ships; Sarna's and the QR encoder's so that `LICENSES/reportlab.txt` is already right the
   day the folder ships, and because a notice for code left out harms nothing.

   **The lesser items, READ, for the owner's facts, not for a notice:** `graphics/svgpath.py`
   says it is "derived from that used by svglib" (svglib is LGPL-3.0; the file carries no other
   terms, so INFERRED that its author contributed it under reportlab's licence);
   `lib/normalDate.py` is "derived from an original version created by Jeff Bauer … used with
   his kind permission"; `graphics/barcode/ecc200datamatrix.py` has a method "basically
   verbatim from huBarcode which is BSD licensed", with no huBarcode notice anywhere in the
   wheel (it is in the folder left out); `platypus/paragraph.py` has a URI regex "derived from
   Django validator". None names terms the wheel could supply; question 73 lists them.
5. **How step 70 leaves a folder out: `make_stdlib_zip.py --leave-out PREFIX`.** Today's
   `wheel_members` packs a wheel whole, apart from tests, sources and metadata. The option:
   - `--leave-out <prefix>` (repeatable): no member whose name in the zip starts with
     `<prefix>` is packed, from any input. The prefix must end in `/` (a folder) and be
     relative; otherwise the build stops naming it.
   - **The build stops when a prefix matches nothing**, naming it, so a renamed upstream folder
     cannot leave the files in silently.
   - It is a small function, `left_out(members, prefixes, matched)`, which filters
     `(data, name)` pairs and records which prefixes matched; `main` applies it to every
     input and checks `matched` at the end. The unit check calls it directly (Decision 11), as
     spec 033's unit checks call `tree_members`.
   - A prefix is matched against the member's name **as its input gives it, before `.py`
     becomes `.pyc`**. With a trailing `/` this changes nothing; the unit check pins it.
   - **One mechanism** (the review's finding 8). Spec 023 leaves `matplotlib/testing/`,
     `matplotlib/sphinxext/` and most of `matplotlib/backends/` out of an install tree (its
     Decision 4), and names no mechanism. If 023 lands any member-exclusion option in
     `make_stdlib_zip.py`, for trees or for wheels, this specification extends that option to
     every input and adds none of its own, and says so in its landing notes. If 023 left its
     files out by staging (deleting from a copied tree), `--leave-out` is added as above.
6. **Step 70, and the other recipe files.**
   - `scripts/steps/70_zip.sh`, beside spec 039's sdists (and 041's, if it landed first):
     `remove "$B/seaborn-0.13.2"`; unpack `pinned seaborn-0.13.2.tar.gz` into `$B`;
     `patch_tree "$B/seaborn-0.13.2"` (no patches; spec 020's rule applies to every tree);
     `cp -R "$B/seaborn-0.13.2/seaborn" "$B/pure-install/seaborn"`; then
     `--metadata "$B/seaborn-0.13.2/PKG-INFO"`. reportlab is one more
     `--wheel "$(pinned reportlab-5.0.1-py3-none-any.whl)"` line with
     `--leave-out reportlab/fonts/` and, until the owner's approval, `--leave-out
     reportlab/graphics/barcode/`, under a comment naming question 73.
   - `scripts/assemble_artifacts.py`: `PACKAGES` gains `seaborn` and `reportlab`; `WHEELS`
     gains reportlab's wheel; reportlab's notice is the wheel's `licenses/LICENSE` plus three
     parts, and seaborn's is built from its tree (Decision 7).
   - The judge's `pins.SOURCE_PATTERNS` and `needs.SOURCE_COMPONENTS` gain `seaborn`
     (`seaborn-[\w.]+\.tar\.gz`), so spec 020's tree check and `<top>` rule cover it.
   - The release workflow's zero-patch job counts one more tree (seaborn's) than main's count
     when this lands.
7. **Licences and notices** (§4.12; seaborn (BSD-3-Clause) and reportlab (BSD) approved by
   decision 43; each ships with its notice).
   - **`LICENSES/seaborn.txt`** holds the sdist's `LICENSE.md`, then each file of `licences/`
     in name order, each part headed by its path in the sdist: `APPDIRS_LICENSE` (MIT),
     `HUSL_LICENSE` (MIT), `NUMPYDOC_LICENSE` (BSD-2-Clause), `PACKAGING_LICENSE`
     (BSD-2-Clause; packaging offers Apache-2.0 or BSD, and this is the BSD text seaborn ships)
     and `SCIPY_LICENSE` (BSD-3-Clause). **§4.12 holds, by 039's precedent:** scipy (question
     25) and packaging (question 35) are approved by name, and MIT and the BSD family are
     approved for tier A by decision 43; spec 039 shipped sympy's nested `latex2sympy` notice
     (MIT, a third party's code inside an approved package) as a second part of sympy's notice
     on that ground, and 039's review confirmed it (039, Decision 8). The notices must ship:
     those in docstrings survive compilation (appdirs, kde, docscrape), those in comments do
     not (husl, version; the review, EXECUTED). Each file is named in the `licences` dict as
     pyyaml's notice is (039, Decision 8).
   - **`LICENSES/reportlab.txt`** is the wheel's `licenses/LICENSE` (through the existing
     `wheel_licences`), then three parts, each headed by its path in the wheel and each the
     file's **leading comment block** (its first lines that begin with `#`, up to the first
     line that does not; 31, 45 and 22 lines, READ), byte for byte, read from the pinned wheel
     after `pinned`'s hash check:
     - `reportlab/graphics/barcode/__init__.py`: Sarna's four-clause BSD notice, the part's
       heading naming the seven files that carry it (Decision 4a; "eight" corrected at the
       build, C1), so the naming line sits outside the bytes the check compares (C2);
     - `reportlab/pdfbase/_glyphlist.py`: Adobe's BSD-3-Clause notice;
     - `reportlab/graphics/barcode/qrencoder.py`: Open End AB's and Kazuhiko Arase's lines,
       followed by the MIT text it names. The MIT text is the one already pinned and shipped,
       `downloads/wasi-libc-161b3195-LICENSE-MIT` (1,023 bytes, a generic MIT text with no
       holder's name; SHA-256 `23f18e03…1cca3`), so no new pin is needed.

     No font notice: no font ships (Decision 4). Sarna's acknowledgement goes in the README and
     the CHANGELOG only when the barcode folder ships (Decision 4a).
   - The judge's `paths.PACKAGES` and `paths.LICENCE_COMPONENTS` gain both, so
     `test_manifest_is_well_formed` and `test_licence_notices_cover_every_component` require a
     `package` line and a notice holding each pinned archive's top-level licence. Two new
     checks hold seaborn's five vendored notices and reportlab's three parts (Decision 11).
8. **What a guest sees: the edges, stated.** Each is a check, a golden line or a README line
   (Design), and each was EXECUTED in the guest while drafting unless marked.
   - **seaborn needs matplotlib's writable cache.** `import seaborn` imports
     `matplotlib.pyplot`; with nothing writable it raises matplotlib's `OSError` ("Matplotlib
     requires access to a writable cache directory"), as spec 023's Decision 7 states for
     matplotlib. With `MPLCONFIGDIR` on a writable grant it works.
   - **`sns.load_dataset` cannot fetch, and how it fails depends on what is writable** (the
     review's finding 3). `get_data_home()` takes `~/.cache/seaborn`, which
     `os.path.expanduser` leaves as it is (the guest has no `HOME`), and calls `os.makedirs` on
     that relative path before any fetch (READ, `seaborn/utils.py:516-520`). EXECUTED (the
     review, the guest, working folder `/`):
     - nothing writable: `import seaborn` itself raises matplotlib's `OSError` (above);
     - only a writable `MPLCONFIGDIR` grant, the README's set-up: `get_data_home()` and
       `load_dataset("tips")` raise `PermissionError: [Errno 63] Operation not permitted: '~'`;
     - a writable root: `get_data_home()` **creates the folder `/~/.cache/seaborn` in the
       caller's root**, and `load_dataset` then raises `URLError: <urlopen error unknown url
       type: https>` (no network, no TLS).

     The route is a CSV in a granted folder and `pd.read_csv`. The drafting probe saw only the
     third case, since the harness's root is writable.
   - **seaborn uses scipy once 037 is in** (Decision 3): kernel densities through
     `scipy.stats.gaussian_kde`, `clustermap` through `scipy.cluster.hierarchy`, and `import
     seaborn` pays scipy's import. A check asserts that path (Decision 11).
   - **Bivariate kernel densities** (`kdeplot(x=…, y=…)`, `jointplot(kind="kde")`) draw
     contours, which need contourpy, which matplotlib's second milestone (spec 043) brings. In
     the research set, which carries contourpy, a bivariate `kdeplot` gave the same RGBA as
     native (EXECUTED). Built with 043 landed, they work; without it they raise as 023's known
     gap for `contour` says (INFERRED from 023's text). The README says whichever is true when
     this lands; no golden line draws one.
   - **statsmodels-backed fits** (`lowess`, `logistic`, `robust`) raise seaborn's own
     `RuntimeError` naming statsmodels until tier B brings it, as natively without it.
   - **reportlab writes PDFs in memory with nothing writable:** a canvas, a platypus document,
     `renderPDF` and `renderSVG`, with `/` read-only and no writable folder (EXECUTED in the
     model of the runner's default). Unlike openpyxl (039, Decision 9), it needs no `tempfile`.
   - **reportlab's bundled fonts are not there** (Decision 4): `TTFont("Vera", "Vera.ttf")`
     raises `TTFError`; DejaVu Sans from matplotlib's data, or any TrueType file in a granted
     folder, is the route.
   - **No bitmap rendering in reportlab** (Decision 3).
   - **No barcodes or QR codes from reportlab** until the owner approves the four-clause BSD
     (Decision 4a): `from reportlab.graphics.barcode import qr` raises `ModuleNotFoundError`.
   - **JPEG images:** 023's Pillow has no JPEG decoder (zlib only). `drawImage("photo.jpg", …)`
     by path embeds the JPEG undecoded and works; through `ImageReader` or a PIL image it raises
     `OSError: decoder jpeg not available`. PNG works both ways.
   - **Repeatable PDFs:** reportlab stamps the time and a random document ID unless
     `invariant=1` is passed; two default saves differ (EXECUTED). With `invariant=1` the bytes
     are the same in the guest and natively.
9. **The snapshot does not pre-import either.** Step 80 and `PREIMPORT` are unchanged, as for
   tier A (039, Decision 10) and matplotlib (question 34). On the research binary's plain
   reactor, with a warm `MPLCONFIGDIR` and before spec 035 (EXECUTED): `import seaborn` took
   10,205,012,918 fuel, against 6,326,099,650 for `import matplotlib.pyplot` (seaborn also
   imports pandas); `import reportlab.pdfgen.canvas, reportlab.platypus` 2,261,505,518; and the
   graphics modules with Pillow 2,451,276,784. **These were taken without scipy.** In the built
   set `import seaborn` also imports `scipy.stats` and `scipy.cluster.hierarchy` (Decision 3),
   so the built number will be higher by about that import (037's landing notes record
   `import scipy.stats`); the build review reads it so, not as a regression. Tier B's
   statsmodels will add more. The landing notes record both imports on the snapshot, so a later
   decision has the built numbers.
10. **Two golden jobs**, `tests/jobs/statistical_plots.py` and `tests/jobs/pdf_reports.py`,
    each run on the plain binary and checked against its `.expected` like the others
    (`jobs.compare`, the versions line first, from `importlib.metadata.version`). Each prints
    only what native Python prints the same way on the recording platform, under both hash
    seeds and in any time zone and locale. **Which runs used which version of the jobs** (the
    review's finding 5):
    - the drafting's first versions (`statistical_plots` ending with a `lowess:` line, without
      `clustermap` or `seaborn.objects`; `pdf_reports` with a QR code and a Code 128 barcode):
      natively without scipy under both seeds, in another zone and locale, and in the guest,
      all equal to native (EXECUTED);
    - `statistical_plots` with `clustermap`, before the `seaborn.objects` line: natively with
      scipy under both seeds (EXECUTED), and by the review with numpy's OpenBLAS wheel and
      037's scipy pin, under both seeds and in another zone and locale (EXECUTED, the review);
      in the guest without scipy, all but `clustermap` equal to native;
    - **the versions this specification describes** (the revision's runs): natively without
      and with scipy, under both seeds and in another zone and locale, all equal; in the guest
      on a zip without reportlab's fonts and barcode folder, `pdf_reports`' eleven lines equal
      native, and `statistical_plots`' first seventeen lines equal native, the eighteenth
      (`clustermap`) raising for want of scipy (EXECUTED).

    The native side of every drafting run used numpy's and scipy's `macosx_14_0_arm64` wheels,
    which link **Apple's Accelerate**, not OpenBLAS (the review, READ: numpy's `__config__`); the
    review reproduced the golden with numpy's OpenBLAS wheel and 037's pinned scipy wheel, so
    either BLAS the oracle picks on darwin-arm64 gives the same golden (finding 4).
    - **What may be printed, and why.**
      - A figure's **RGBA buffer**, by its full SHA-256 and shape, as spec 023's plot job does.
        EXECUTED: every figure drawn in the drafting had the same RGBA in the guest as natively,
        except those holding a least-squares fit: a `regplot`, and a `seaborn.objects` plot
        with `so.PolyFit` (the revision's run; the job's objects plot uses `so.Agg` instead).
      - A figure's **SVG**, by its SHA-256, saved with `metadata={"Date": None}` and
        `rcParams["svg.hashsalt"]` fixed, **only when the figure holds no raster**. A heatmap's
        colour bar is an image, which the SVG embeds as a deflated PNG; its SVG and PDF differed
        from native while its RGBA did not (EXECUTED). **No PNG bytes**: every PNG differed
        from native while its pixels did not, since deflate's library differs (039, Decision
        11, says the same of `.xlsx` parts).
      - **Fitted and estimated values as text at nine significant digits**
        (`format(float(x) + 0.0, ".9g")`, 037's rule), not as pixels. A `regplot`'s line comes
        from a least-squares fit (`np.linalg.pinv`): numpy's linear algebra in the guest is
        numpy's own `lapack_lite`, natively the host's LAPACK (Accelerate in the drafting), and
        037 leaves the guest's numpy as it is, so scipy's arrival does not move it (the review,
        READ). The line's values differed in the last bits
        (`-1.1205186260286517` natively, `-1.120518626028651` in the guest), which moved 76
        pixels by one level (82 by up to two without the confidence band; EXECUTED). Kernel
        densities come from scipy's `gaussian_kde` when scipy imports and from seaborn's copy
        when not; natively both printed the same nine digits (EXECUTED).
      - A **PDF's bytes** by length and SHA-256, only when built with `invariant=1` and
        `pageCompression=0` (reportlab's default compresses every stream with deflate); a
        compressed PDF only by what pypdf reads back.
    - **`statistical_plots`** (the versions of numpy, pandas, matplotlib and seaborn): a
      fixed frame of 120 rows from `numpy.random.Generator(PCG64(42))` (three dose groups, ten
      days, `x` normal and `y` linear in `x` plus a group offset and noise), printed as its
      shape, the sum and the standard deviation of `y`; `sns.set_theme(style="whitegrid",
      palette="deep")` and the first palette colours and `husl`'s; then, each at 4 × 3 inches
      and 80 dpi unless a grid sets its own size, the RGBA and SVG lines of `scatterplot` (hue
      and style), `lineplot` (`errorbar="sd"`), `barplot` (`errorbar=("ci", 95)`,
      `n_boot=500`, `seed=0`), `histplot` (stacked by group, 12 bins), `boxplot`, `stripplot`
      (`jitter=False`), `ecdfplot`, `relplot` (one column per group), `pairplot`
      (`diag_kind="hist"`), the RGBA line only of a `heatmap` with annotations, and the RGBA and
      SVG lines of one `seaborn.objects` plot (`so.Plot(df, x="x", y="y", color="dose")
      .add(so.Dot()).add(so.Line(), so.Agg()).on(fig).plot()`, seaborn's newer interface; the
      review's finding 9); then, as text at nine digits (the confidence band at six):
      `regplot`'s line and band (`n_boot=200`, `seed=0`), `kdeplot`'s curve, `violinplot`'s
      outlines, and `clustermap`'s row and column leaf orders and its row linkage. Each array
      is printed as the SHA-256 prefix of its text and its first three values. Eighteen lines.
    - **`pdf_reports`** (the versions of reportlab, pypdf, matplotlib and pillow), all built in
      memory:
      - a two-page canvas letter (`invariant=1`, `pageCompression=0`): Helvetica-Bold,
        Times-Roman and Courier, a line, a filled rectangle, a circle, a link, a title and an
        author; its length, SHA-256 and pypdf's read-back (pages, title, author, each page's
        text); the same letter compressed, by its read-back only; one `stringWidth`;
      - a platypus report of `sales.csv` grouped by region (count, sum, mean): a title, a
        paragraph with markup, the table with a grid and a coloured header, a bulleted list, a
        page break, a long paragraph, and a footer with page numbers; its length, SHA-256 and
        read-back;
      - charts as drawings: a bar chart of the totals and a line chart of the monthly sales on
        one drawing, by the SHA-256 of `renderPDF.drawToString(…, invariant=1,
        pageCompression=0)` and of `renderSVG.drawToString(…)`; a pie chart as SVG; and
        `renderPM`'s `RenderPMError`, first line. No barcode and no QR code until the owner
        approves (Decision 4a);
      - DejaVu Sans from `matplotlib.get_data_path()` registered with `TTFont`, a line of
        accented and mathematical text, the PDF's length, SHA-256 and read-back (Decision 4);
      - a matplotlib figure saved to PNG in memory and drawn with `drawImage` through
        `ImageReader`: the image's size and the `/Width` and `/Height` of the PDF's image object,
        not its bytes (reportlab re-deflates the pixels).

      Eleven lines. It reads `sales.csv` from the job's data folder, as 039's jobs do.
    - **Three lines not yet run in a guest with scipy** (the review's finding 2): `kdeplot`,
      `violinplot` and `clustermap`. The drafting guest had no scipy. There `kdeplot` and
      `violinplot` ran through seaborn's own `external/kde.py` and equalled native, and
      `clustermap` raised `RuntimeError: clustermap requires scipy to be available` (EXECUTED).
      In the built guest, after 037, the first two run through `scipy.stats.gaussian_kde` and
      the third through `scipy.cluster.hierarchy.linkage`. Natively the kernel densities print
      the same nine digits through either path, and `clustermap`'s line is the same under both
      seeds and both BLAS builds (EXECUTED); the leaf orders are integers and the linkage is
      printed at nine digits. So the three are expected to equal native (INFERRED). If one does
      not, it is a finding for the build review, taken under AGENTS.md rule 7; no line is
      dropped to get a pass. Because the two kernel-density paths print the same digits, the
      golden cannot show which ran; `test_seaborn_takes_its_scipy_paths` does (Decision 11).
      If the lane ever builds this before 037, the builder leaves the `clustermap` line out and
      says so in the landing notes (Decision 13).
    - **The oracle.** `tests/jobs/oracle/pyproject.toml` gains `seaborn==0.13.2` and
      `reportlab==5.0.1`; `uv.lock` is regenerated with every download under `build/oracle/`.
      Both are pure wheels, so nothing is built on the host. The oracle's seaborn is the wheel,
      whose package equals the sdist's byte for byte (Decision 2). The oracle's reportlab keeps
      its fonts; neither job uses them. Pillow, pypdf, charset-normalizer and scipy come from
      023, 039 and 037. `regen.py` runs both jobs with `MPL_IGNORE_SYSTEM_FONTS=1` and a fresh
      `MPLCONFIGDIR`, as 023 runs its plot job, and under 037's `oracle_env`
      (`OPENBLAS_NUM_THREADS=1`, `VECLIB_MAXIMUM_THREADS=1`), so the oracle's sums are taken in
      one order whichever numpy wheel uv picks for the host (finding 4). `statistical_plots` is recorded on darwin-arm64
      and reproduced there only, by 023's rule for plot jobs (or 037's `RECORDED_ON`, whichever
      landed); `pdf_reports` prints no pixel and reproduces on every platform. `jobs.JOBS`
      gains both.
    - The drafting fuel on the research binary's plain reactor, before 035 and without scipy,
      was 27,284,234,515 for the revised `statistical_plots` with a fresh `MPLCONFIGDIR` (it
      builds matplotlib's font cache; the run stopped at `clustermap`) and 15,852,565,377 for
      the revised `pdf_reports` (EXECUTED). The built `statistical_plots` also pays scipy's
      import and `clustermap`. The judge records the built numbers.
    - The drafts are not repository code; the builder writes the jobs, clean under the
      repository's `ruff format` and `ruff check`.
11. **The other checks.** Acceptance criterion 1 lists how each is seen failing first.
    - **v1.3, `test_reportlab_runs_its_pure_paths[plain, snapshot]`** in
      `tests/checks/test_v1_3_default_profile.py`: `import _rl_accel` raises
      `ModuleNotFoundError`; `reportlab.lib.rl_accel._c_funcs == {}` and its `_py_funcs` names
      all eleven functions; `renderPM.drawToString` raises `RenderPMError` naming `rlPyCairo`;
      no zip member name starts with `reportlab/fonts/`; `TTFont("Vera", "Vera.ttf")` raises
      `TTFError`; `from reportlab.graphics.barcode import qr` raises `ModuleNotFoundError`
      (while Decision 4a's leave-out stands); and a canvas PDF built in memory with
      `invariant=1` starts with `%PDF-`.
    - **v1.3, `test_seaborn_takes_its_scipy_paths[plain, snapshot]`** in the same file (the
      review's finding 2): after `import seaborn`, `seaborn.matrix._no_scipy is False`,
      `seaborn._statistics._no_scipy is False`, and
      `seaborn._statistics.gaussian_kde.__module__` starts with `scipy.`. It also holds the
      `load_dataset` edge (finding 3): run through `wasi_python.run` with only a writable grant
      at `/cfg` and `MPLCONFIGDIR=/cfg`, `seaborn.load_dataset("tips")` raises
      `PermissionError` naming `'~'`. The program prints a line per fact and the check compares
      them, with no path of the host in any line.
    - **v1.1, `test_reportlab_fonts_are_not_in_the_zip`** in
      `tests/checks/test_v1_1_artifact_set.py`: the artifact zip has no member under
      `reportlab/fonts/` and no member whose name ends in `.pfb`, `.afm` or `.sfd` (the font
      formats of Decision 4; matplotlib's AFM files are inside its one inner archive, 023's
      Decision 4, so no outer name ends so). While Decision 4a's leave-out stands, it also
      asserts no member under `reportlab/graphics/barcode/`; the change that ships the folder
      after the owner's approval removes that assertion under its own `--accept-judge`. It
      reads the zip on the host, so it holds the licence decision with no guest run.
    - **v1.1, `test_seaborn_notice_carries_its_vendored_licences`** in the same file:
      `LICENSES/seaborn.txt` holds a heading naming each of `LICENSE.md` and the five
      `licences/` files; **when the pinned sdist is in `downloads/` and passes its hash
      check**, each part equals that file of the sdist byte for byte. Without the download it
      checks the headings only, as `licence_errors` does for every notice (the review's
      finding 6; `paths.licence_source` returns `None` when the pin is absent).
    - **v1.1, `test_reportlab_notice_carries_its_third_party_parts`** in the same file (the
      review's finding 1): `LICENSES/reportlab.txt` holds the wheel's `LICENSE` and a heading
      naming each of `reportlab/graphics/barcode/__init__.py`, `reportlab/pdfbase/_glyphlist.py`
      and `reportlab/graphics/barcode/qrencoder.py`; the Sarna part says "This product includes
      software developed by Tyler C. Sarna."; the QR part holds the pinned MIT text. When the
      pinned wheel and `wasi-libc-161b3195-LICENSE-MIT` are in `downloads/` and pass their hash
      checks, each part equals the leading comment block of its file in the wheel, and the MIT
      text equals the pin, byte for byte; without them, the headings and the acknowledgement
      line only.
    - **v1.4, `test_reportlab_writes_a_pdf_with_nothing_writable`** in
      `tests/checks/test_v1_4_embedding.py`, through `wasi_python.run` with no root and no
      grant (the runner's own defaults): a program builds a canvas PDF and a platypus PDF in
      memory and prints each one's first five bytes and its length; the exit code is 0 and both
      start with `%PDF-`.
    - **v1.3, spec 033's `test_packages_carry_their_metadata`:** its set of distributions gains
      `seaborn` and `reportlab`, each at its `MANIFEST` version.
    - **Unit, `test_a_left_out_folder_is_not_packed`** in `tests/unit/test_build_scripts.py`:
      `left_out` over a list of members drops exactly those under the prefix and keeps the rest
      with their bytes; it records the prefix as matched; it matches a `pkg/sub/mod.py` member
      against the name before compilation (so `pkg/sub/` drops `pkg/sub/mod.py`, and a prefix
      written with `.pyc` matches nothing); with a prefix that matches nothing, `main`'s check
      stops the build with one line naming it; a prefix without a trailing `/` stops it too.
12. **What it costs, stated so growth can be told from regression.**

    **Members and bytes** (EXECUTED, step 70's rules): **+199 members**: seaborn 55 (54
    `.pyc` and `METADATA`; 541,099 deflated bytes as a standalone zip holds them) and reportlab
    144 (143 `.pyc` and `METADATA`; 1,495,093), **2,036,192 bytes**. The revision's zips with
    and without the two differed by exactly those 199 names. Before Decision 4a the count was
    215 (reportlab 160, 1,619,735 bytes); the review reproduced those 215 from the pins (the
    barcode folder is 16 members, 124,642 bytes, and returns with the owner's approval). The
    plain binary does not change. `MANIFEST` gains 2 `package` and 2 `pin` lines; the `recipe`
    lines of `70_zip.sh`, `00_download.sh`, `make_stdlib_zip.py` and `assemble_artifacts.py`
    change.

    **Fuel on a plain start.** Before spec 035 the first 215 members cost 16,524,794 more on a
    plain `-c pass` (300,539,672 to 317,064,466; 76,860 per member, EXECUTED on the research
    binary, close to 039's 77,867). After 035 a member costs about 26,900 (039, Decision 13,
    from 035's reader prototype). The rows below take 039's measured slopes for 199 members; the
    caps are 039's per member.

    | metric | expected | cap |
    |---|---|---|
    | plain `-c pass` | +199 × 26,900 ≈ +5.4 M (INFERRED) | ≤ +199 × 30,000 = +5.97 M |
    | every other plain check that does not query `importlib.metadata` | the same | ≤ +5.97 M + 0.2% of its accepted value |
    | plain checks that query `importlib.metadata` | +5.4 M + 199 × 4,844 ≈ +6.3 M | ≤ +199 × 36,000 = +7.16 M + 0.2% |
    | snapshot checks that neither read metadata nor resources | +199 × 2,399 ≈ +0.48 M | ≤ +199 × 3,500 = +0.70 M |
    | snapshot checks that query `importlib.metadata` | the row above plus 199 × 4,844 ≈ +0.96 M | ≤ +199 × 9,500 = +1.89 M |
    | 033's `test_packages_carry_their_metadata[plain, snapshot]` and 035's check 6 comparison | two more distributions read, about 18.9 M each per read (039's measurement) | on top of the rows above, ≤ 25 M per distribution per read: ≤ +50 M, and ≤ +100 M for 035's comparison |
    | the zip's `bytes` | +2,036,192 | ≤ +2.2 MB |
    | the snapshot's `bytes` | +199 × 366 ≈ +72.8 KB | ≤ +199 × 1,000 = +199 KB |
    | the plain binary's `bytes` | 0 | 0 |

    The new jobs' and checks' fuel are new metrics, and they include scipy's import wherever
    seaborn is imported (Decision 9): that is not growth against an accepted metric. A growth
    above a cap is a finding for the build review, not a reason to accept. If 035's check 6 was
    re-based as 039 proposed, its bound already follows the member count.

    **The wheel** carries the zip, which is already deflated, so it grows by about 2.0 MB. The
    landing notes record its built size (question 64).
13. **Ordering.** This specification is build-class, so it overlaps no other build-class change
    (§5.7).
    - **It builds after 023 and 039.** 023 brings matplotlib and Pillow (reportlab imports
      Pillow when imported; seaborn imports matplotlib). 039 brings charset-normalizer and pypdf,
      `build/pure-install/`, the default-profile check file and `jobs.run_in_guest`. 039 itself
      builds after 033, 035 and 023, and after 038 (039's Decision 14, since 037 is confirmed for
      build), so scipy is in the set when this is built and the `clustermap` line runs.
    - **The owner's answer on the four-clause BSD is not waited for.** Without it the barcode
      folder is left out (Decision 4a); with it, the folder comes in by a later, small change.
    - **043 (matplotlib M2) is not waited for.** The roadmap puts it before 037 (043's
      Decision 13), so it is expected to land before this; if it has not, this builds anyway
      and only the README's line on bivariate densities differs (Decision 8).
    - **With 041, whichever is confirmed for build first after 039 lands builds first.** The
      second rebases onto the other's step 70, `assemble_artifacts.py`, the release workflow's
      tree count and the README's default-profile section, as 041's Decision 9 says. Nothing
      here depends on 041, nor 041 on this.
    - **Not split.** Two packages through one seam (two pins, one option, two jobs) cost one
      rebuild, one review and one accept. One builder builds it in three steps, each green
      before the next: (1) `--leave-out` with its unit check, the pins, step 70 and the
      notices, with the zip's names checked (criterion 2); (2) the two jobs and the oracle;
      (3) the other checks, the README and the growth account.

## Intent

An agent's code in the default profile draws seaborn's statistical plots and writes PDF reports
with reportlab (text, tables, charts, Unicode text in an embedded font, images), with results
equal to native Python's. reportlab's PDFs need nothing writable. No file with an unapproved
licence ships, every third-party notice in the shipped code ships with it, and where the
sandbox says no, the README says so first.

## Design

| file | change |
|---|---|
| `downloads/SHA256SUMS`, `scripts/00_download.sh` | the two pins of Decision 2 |
| `scripts/make_stdlib_zip.py` | `--leave-out <prefix>` and `left_out` (Decision 5) |
| `scripts/steps/70_zip.sh` | unpack, patch and stage seaborn's sdist; its `--metadata`; reportlab's `--wheel`, `--leave-out reportlab/fonts/` and, until the owner's approval, `--leave-out reportlab/graphics/barcode/` (Decisions 4a and 6) |
| `scripts/assemble_artifacts.py` | `PACKAGES` +2, `WHEELS` +1, seaborn's notice from its tree with the five vendored licences, reportlab's notice with its three third-party parts and the pinned MIT text (Decisions 6 and 7) |
| `tests/jobs/statistical_plots.py`, `pdf_reports.py` and their `.expected` | Decision 10; goldens written by `regen.py` |
| `tests/jobs/oracle/pyproject.toml`, `uv.lock` | `seaborn==0.13.2`, `reportlab==5.0.1` |
| `tests/harness/jobs.py` | `JOBS` gains both; `statistical_plots` recorded on darwin-arm64 (023's or 037's mechanism); both run under 037's `oracle_env` |
| `tests/harness/paths.py` | `PACKAGES` and `LICENCE_COMPONENTS` gain both |
| `tests/harness/pins.py`, `tests/harness/needs.py` | `seaborn` in `SOURCE_PATTERNS` and `SOURCE_COMPONENTS` |
| `tests/checks/test_v1_3_default_profile.py` | the two job checks, `test_reportlab_runs_its_pure_paths` and `test_seaborn_takes_its_scipy_paths` (Decisions 10 and 11) |
| `tests/checks/test_v1_3_data_stack.py` | 033's metadata set gains both |
| `tests/checks/test_v1_1_artifact_set.py` | `test_reportlab_fonts_are_not_in_the_zip`, `test_seaborn_notice_carries_its_vendored_licences`, `test_reportlab_notice_carries_its_third_party_parts` |
| `tests/checks/test_v1_4_embedding.py` | `test_reportlab_writes_a_pdf_with_nothing_writable` |
| `tests/unit/test_build_scripts.py` | `test_a_left_out_folder_is_not_packed` |
| `.github/workflows/release.yml` | the zero-patch job's tree count, one more than main's |
| `README.md` | below |
| `CHANGELOG.md` | under the unreleased section: seaborn and reportlab; reportlab's fonts and barcode folder left out and why; DejaVu as the Unicode font; the edges of Decision 8, including that `load_dataset` with a writable root makes a folder named `~` there |

**The README.** In "What the default profile carries" (spec 039): seaborn and reportlab in the
table (the plotting row beside matplotlib; reportlab beside pypdf), and one line each for the
edges of Decision 8: seaborn's cache folder (`MPLCONFIGDIR`); `load_dataset`'s three outcomes
and `pd.read_csv` on a granted file as the route; seaborn using scipy; no barcodes or QR codes
from reportlab, pending the owner's decision on their licence; bivariate
densities with spec 043; statsmodels-backed fits after tier B; reportlab's PDFs in memory with
nothing writable and `invariant=1` for repeatable bytes; Unicode text through DejaVu Sans from
`matplotlib.get_data_path()` (the two lines that register it) or a TrueType file in a granted
folder, since reportlab's own fonts are not shipped; no bitmap rendering in reportlab (use
matplotlib, or `renderSVG`); JPEGs by path, not decoded. The recipe paragraph says a wheel may
have a folder left out of the zip, and which one.

## Scope

In: Decisions 1 to 13. Out:
- **reportlab's bundled fonts, and a patch to read them from the zip:** left out (Decision 4).
  Reporting the `_files` bug to reportlab is the owner's (question 73).
- **reportlab's barcode folder,** until the owner approves the four-clause BSD (Decision 4a;
  question 73). Shipping it is a later change of its own.
- **`rl_accel`, `rlPyCairo`, `freetype-py`, `rlbidi`, `uharfbuzz`:** native or Cairo-bound
  extras, not carried.
- **A JPEG decoder for Pillow** (libjpeg): spec 023's scope, not this one.
- **contourpy, and so bivariate densities:** matplotlib's second milestone, spec 043.
- **statsmodels:** tier B (decision 48). When it lands, seaborn's `lowess`, `logistic` and
  `robust` fits work; this specification's goldens print none of them, so nothing here changes.
- **seaborn's datasets:** they are downloaded from GitHub at run time; there is no network.
- **Pre-importing either** (Decision 9).

## Acceptance criteria

1. **The checks exist and were seen failing first** on the set the builder starts from (023
   and 039 landed, and 041 if it built first), each recorded in the landing notes:
   - `test_statistical_plots_job_matches_native` and `test_pdf_reports_job_matches_native`:
     `ModuleNotFoundError` for seaborn and for reportlab;
   - `test_reportlab_runs_its_pure_paths`: `ModuleNotFoundError: reportlab`; and against a
     zip built without `--leave-out reportlab/fonts/`, the member assertion fails naming a
     `reportlab/fonts/` member; and against one built without the barcode leave-out, the
     `qr` import succeeds and the check fails;
   - `test_seaborn_takes_its_scipy_paths`: `ModuleNotFoundError: seaborn`; and against a copy
     of the built zip with no `scipy/` members, it fails naming `_no_scipy` and
     `seaborn.external.kde`;
   - `test_reportlab_fonts_are_not_in_the_zip`: passes on the starting set, which has no
     reportlab; so it is seen failing against copies of the built set whose zip was made
     without either `--leave-out`, naming the fonts and the barcode folder;
   - `test_seaborn_notice_carries_its_vendored_licences`: no `LICENSES/seaborn.txt`; and
     against copies of the built set whose notice lacks one vendored licence, or has one byte
     changed (with the download present), or lacks one heading (with `downloads/` absent);
   - `test_reportlab_notice_carries_its_third_party_parts`: against 039's notice builder (the
     wheel's `LICENSE` alone), naming the three missing parts; and against copies whose notice
     has one byte changed in a part, or lacks the acknowledgement line, with and without
     `downloads/`;
   - `test_reportlab_writes_a_pdf_with_nothing_writable`: `ModuleNotFoundError: reportlab`;
   - `test_packages_carry_their_metadata` and `test_licence_notices_cover_every_component`
     with the two added: the two missing;
   - `test_a_left_out_folder_is_not_packed`: against 039's `make_stdlib_zip.py` (no
     `left_out`), and against a mutant `left_out` that keeps the folder, and one that matches
   compiled names.
2. **The zip's names and bytes.** A full build from pins in a clean clone gives a `python.wasm`
   byte for byte the one it started from (`cmp`). Against the starting set's zip, the sorted
   name lists (`unzip -Z1 … | LC_ALL=C sort`) differ only by the 199 names added (54 under
   `seaborn/`, `seaborn-0.13.2.dist-info/METADATA`, 143 under `reportlab/`,
   `reportlab-5.0.1.dist-info/METADATA`), exactly those a script computes from the pins with
   step 70's rules and the two leave-outs, and none removed; none starts with
   `reportlab/fonts/` or `reportlab/graphics/barcode/`;
   every shared member is the same bytes; seaborn's `METADATA` equals its `PKG-INFO` (`cmp`)
   and reportlab's equals its wheel's.
3. **The same bytes everywhere.** A manual run of the release workflow on the reviewed commit
   passes its `rebuild`, `same-bytes` and zero-patch jobs, the last with the new tree count;
   its run number goes in the landing notes.
4. **The judge.** `uv run pytest` is green with `--accept "<reason>"`, `--accept-judge "<the
   two jobs and goldens; the oracle's two pins and its environment; the six checks and the
   unit check; the package, licence and source-tree lists; 033's metadata set>"` and
   `--accept-growth "<the account>"`, and loses no pass. The account gives the build's
   measured number for each row of Decision 12's table against its expectation and cap, the
   members actually added, and the kde, violin and clustermap lines' result in the guest with
   scipy (Decision 10). The
   goldens reproduce under the pinned oracle (`regen.py --check`; `statistical_plots` on
   darwin-arm64). The two jobs pass `ruff check` and `ruff format --check`.
5. **The numbers recorded.** The landing notes give: plain and snapshot `-c pass`; `import
   seaborn` and `import reportlab.pdfgen.canvas, reportlab.platypus` on the snapshot (Decision
   9); each job's fuel; the zip's, the snapshot's and the wheel's sizes.
6. **The release.** A release dry run passes every job (criterion 3's run).

## The owner's choices

None open here. The owner's decision 43 (seaborn and reportlab, with their licences) is applied
as written. Three facts this specification found are recorded as question 73 in
`../questions-for-the-owner.md`, each decided here so that nothing waits: reportlab's wheel
carries fonts whose licences the owner has not approved (left out); reportlab's barcode modules
are under the four-clause BSD licence with an advertising clause, which §4.12 does not list
(left out until the owner approves it; their notices ship now); and reportlab cannot read its
own files from a zip on any Python from 3.13 (an upstream bug this specification does not need
fixed; reporting it is the owner's).

## Landing notes

**Built** 2026-10-20 in the harness's worktree `.claude/worktrees/agent-af86ca8005c1af7dc` on
`spec/042-seaborn-and-reportlab`, a stacked build (constitution §4.14) on spec 038's tip
`ecc2423` (scipy M2 with its build review answered), itself on main `958a22b`; it rebases onto
038's final tip or main when 038 lands. Phase 1 (pins, recipe, checks, jobs) ran nothing that
builds, on 038's earlier tip `442493b`; phase 2 restacked onto `ecc2423` with
`git rebase --onto origin/spec/038-scipy-second-milestone 442493b`, **no conflict** (038's two
newer commits touch only `tests/`, `README.md` and `context/`, none of this specification's
hunks), then built from empty and judged. Not reviewed, not accepted. Logs and evidence are
under the worktree's `build/042/`.

### What changed (phase 1)

- **Recipe.** The two pins of Decision 2 in `downloads/SHA256SUMS` and `scripts/00_download.sh`,
  as written; both fetched and verified (`build/042/download.log`: 1,457,696 and 1,957,258
  bytes, `downloads: 86 pins, 2 fetched, 86 verified`). Step 70 unpacks seaborn's sdist beside
  tier A's, gives it `patch_tree` (no patches), stages `seaborn/` under `build/pure-install/`,
  passes its `PKG-INFO` with `--metadata`, adds reportlab's wheel, and leaves out
  `reportlab/fonts` and `reportlab/graphics/barcode` with spec 023's `--drop` (amendment 2).
  `assemble_artifacts.py`: `PACKAGES` +2, `WHEELS` +1 (reportlab), seaborn's notice from its tree
  (`SEABORN_NOTICES`, the licence and the five vendored ones), reportlab's three leading comment
  blocks read from the pinned wheel after its hash check, and the MIT text (`reportlab_parts`).
  The release's zero-patch count is 26 trees (25 on this base, +1).
- **Judge.** The two jobs and their goldens (`statistical_plots` recorded on darwin-arm64), the
  oracle's two pins and its regenerated `uv.lock`; `jobs.JOBS` +2, `PLATFORM_BOUND` +1,
  `jobs.run_in_guest` passes keyword arguments to the guest (both jobs need matplotlib's cache
  folder and data grant); in `test_v1_3_default_profile.py` the two job checks,
  `test_reportlab_runs_its_pure_paths` and `test_seaborn_takes_its_scipy_paths`; in
  `test_v1_1_artifact_set.py` the font, seaborn-notice and reportlab-notice checks, their rules in
  `tests/harness/artifacts.py`, each with a self-test of its mutants in
  `tests/unit/test_artifact_rules.py`; `test_reportlab_writes_a_pdf_with_nothing_writable` in
  `test_v1_4_embedding.py`; `test_a_left_out_folder_is_not_packed` in
  `tests/unit/test_build_scripts.py`; both in `paths.PACKAGES`, `LICENCE_COMPONENTS`, 033's
  metadata set and the artifact rules' synthetic set; seaborn in `pins.SOURCE_PATTERNS` and
  `needs.SOURCE_COMPONENTS`; both in `tests/upstream/packages.toml` (`later`, closed by spec 067,
  as spec 063 asks: seaborn's sdist carries `tests/` but the zip takes only its package;
  reportlab is pinned as a wheel, which carries no tests). The new checks sit in files already
  in their release shards.
- `README.md` (the table's plotting and PDF rows, *seaborn and reportlab* under *What the
  default profile carries*, and the recipe paragraph's leave-out sentence), `CHANGELOG.md` (under
  the one unreleased section, 0.1.0a8).

### Amendments at build, each with its reason

1. **C1: seven Sarna files, not eight** (Decisions 4a and 7, corrected in place). EXECUTED: a
   search of the pinned wheel's `.py` files for "Tyler C. Sarna" finds `__init__`, `code128`,
   `code39`, `code93`, `common`, `fourstate` and `usps`. Question 73 is answered and no longer
   in `../questions-for-the-owner.md`; its answer in `../decisions.md` names no count, so
   nothing there changes. **C2:** the seven files are named in the Sarna part's heading
   (`… its leading comment (Tyler C. Sarna's BSD-4-Clause notice, which heads __init__.py, …
   and usps.py in reportlab/graphics/barcode/)`), outside the 31 lines compared byte for byte.
   **C3:** the barcode folder stays out; the owner approved its licence (§4.12, question 73),
   and decision 73 says a later change ships it, adds the QR and Code 128 lines and puts Sarna's
   acknowledgement in the README's barcode line and the CHANGELOG.
2. **Decision 5's one mechanism is spec 023's `--drop`; no `--leave-out` is added.** 023 landed
   `--drop`, `--keep` and `--inner` in `make_stdlib_zip.py` (`Selection`). They apply to every
   input (`add` calls `take` for the stdlib, trees, wheels, metadata and files alike), match a
   member's name as its input gives it, before `.py` becomes `.pyc`, and stop the build in one
   line when a rule matches nothing. So, by Decision 5's own rule, this specification extends
   nothing and adds no option or `left_out`. A `--drop` names a folder, with or without a
   trailing slash, never a string prefix: Decision 11's "a prefix without a trailing `/` stops
   the build" becomes "a name that is not a folder (`pkg/su`) matches nothing and stops it". The
   unit check pins the folder boundary (`pkg/sub` keeps `pkg/subway.py`), both spellings, the
   stop, and matching before compiling, which a folder rule cannot show (a compiled member is
   under the same folder) and `--keep`'s file names can (`pkg/sub=mod.py`). EXECUTED, seen
   failing against three mutants of the rule (`build/042/mutant_plugin.py`, run by node id): one
   that keeps the folder, one that matches a string prefix (drops `pkg/subway.py`), one given
   compiled names (drops the kept `mod.py`).
3. **The MIT text's pin is `wasi-libc-2e6fb9d8-LICENSE-MIT`**, not `161b3195`: spec 086 moved
   the toolchain to wasi-sdk 34. The same bytes (SHA-256 `23f18e03…cca3`, 1,023 bytes); the
   name follows the line's `WASI_LIBC_COMMIT`.
4. **The QR encoder's notice and the MIT text are two parts**, so each compares byte for byte:
   the comment block headed by its path, then the MIT text headed `The MIT licence
   reportlab/graphics/barcode/qrencoder.py names (wasi-libc-2e6fb9d8-LICENSE-MIT)`. The check
   compares the MIT part with MANIFEST's pin line for that file, so it holds without
   `downloads/` too (Decision 11 asked only for its heading there).
5. **043 landed first**: the README says bivariate kernel densities work through contourpy;
   phase 2 confirms it with one guest probe.
6. **The jobs as written** (Decision 10 gives their content; the text is the builder's): every
   figure at 80 dpi through `rcParams["figure.dpi"]`, grids by their own `height`; the frame's
   group offsets 0, 1 and 2 and `y = 1.5x + offset + N(0, 0.5)`; `clustermap` of the mean of
   `y` by day and dose (10 × 3, `figsize=(4, 4)`); the image line reads the PDF's image object
   through pypdf. Eighteen and eleven lines. EXECUTED under the oracle: both seeds agree, and
   both jobs give the same bytes with `TZ=Asia/Tokyo LC_ALL=de_DE.UTF-8`
   (`build/042/regen-write.log`); `tests/jobs/regen.py --check` reproduces all 26 jobs
   (`build/042/regen-check.txt`).
7. **Members and bytes, measured from the pins** (EXECUTED: step 70's own `walk`,
   `wheel_members`, `sdist_metadata`, `Selection`, `pyc` with spec 051's code prefix and
   `member`, under the oracle's CPython 3.15.0; `build/042/members042.py`, the names in
   `build/042/names.txt`): **199 members**, seaborn 55 (542,483 bytes as a
   standalone zip) and reportlab 144 (1,498,634), **2,041,117 bytes**; reportlab whole would be
   192 members. Decision 12's 541,099 and 1,495,093 were measured before spec 051 compiled each
   module under its zip path; the sum stays under the 2.2 MB cap.
8. **`load_dataset` through the runner raises `FileNotFoundError` naming `'~'`, not
   `PermissionError`** (Decision 8 and the check, amended; commit `3c0b11d`). Seen on the built
   set: with only a writable `/cfg` grant and no root, `os.makedirs` of the relative
   `~/.cache/seaborn` has no root to resolve against and answers `ENOENT`. The pre-build
   review's `PermissionError [Errno 63]` was its own driver's read-only root (`EPERM`, as the
   README's *Grants* says of a read-only folder). The check now asserts `FileNotFoundError '~'`
   and that no `~` folder appears in the grant; the README states both outcomes. The property
   the review asked for holds: it fails before any fetch, naming `'~'`, and writes nothing.
9. **The roadmap's "question 73 adds the barcode folder, written in before its build" is
   superseded by C3** and decision 73 (the lane, 2026-10-20): the folder stays out, and the
   acknowledgement sentence is not added now; the later change ships both. For that change (the
   build review's finding 4): `code128.py`, `code93.py` and `fourstate.py` date Sarna's copyright
   2000, the other four 1996-2000; its Sarna heading adds "(code128.py, code93.py and
   fourstate.py date their copyright 2000)".
10. **Decision 8's third `load_dataset` case is an embedder's, not the runner's** (the build
    review's finding 2). Through `wasi_python.run` with a writable root, `/tmp` is writable, so the
    runner gives a fresh `HOME` under `/tmp`; seaborn's cache folder goes there, removed after the
    call, and `load_dataset` raises `URLError`; no `~` folder is made in the root (the review,
    EXECUTED). Only an embedder that gives a writable root and no `HOME` gets `/~/.cache/seaborn`
    in it, as the pre-build review's driver did. The README and CHANGELOG say so. The check's
    no-`~` assertion now comes before its output assertion, and is seen failing on a mutant
    whose program drops `HOME` and works in the writable grant (`build/042/mutant_home_plugin.py`,
    `build/042/mutant-home.txt`: the grant holds `fontlist-v3.11.0.json` and `~`).

### Acceptance criterion 1: seen failing first (EXECUTED)

On main's accepted set (wave 06, `SHA256SUMS` `f12cd25c…`, cloned to the worktree's
`build/old-artifacts/`, `WASI_PYTHON_ARTIFACTS` pointing at it; `build/042/seen-failing-on-main-set.txt`):
both job checks and `test_reportlab_runs_its_pure_paths`, `test_seaborn_takes_its_scipy_paths`
and `test_reportlab_writes_a_pdf_with_nothing_writable` fail with `ModuleNotFoundError` for
seaborn or reportlab; the two notice checks name `LICENSES/seaborn.txt is missing` and `MANIFEST
names no reportlab`; `test_licence_notices_cover_every_component`, `test_manifest_is_well_formed`
and `test_packages_carry_their_metadata` name the two missing; `test_reportlab_fonts_are_not_in_the_zip`
passes, as criterion 1 expects. The three new rules' self-tests name every mutant criterion 1
lists for them (a font or barcode member, a vendored licence missing or one byte changed, the
notice 039's builder wrote, one byte changed in a part, the acknowledgement removed, with and
without the pinned archive), and the left-out unit check its three mutants (amendment 2). The
fast tier on 038's set (`SHA256SUMS` `c3a849c0`, the starting set; `build/042/fast-tier-038-set.txt`)
fails exactly the new and extended checks (13, with the recipe staleness rows). On copies of the
built set (`build/042/mutants042.py`, `build/042/mutant-*.txt`): with reportlab's fonts and
barcode folder put back as step 70 would pack them without either `--drop` (48 members),
`test_reportlab_fonts_are_not_in_the_zip` names 32 font-folder members, 16 barcode members and
21 font files, and `test_reportlab_runs_its_pure_paths[plain]` fails on `qr` imported and the
font members (bundled `Vera.ttf` still raises `TTFError` there: the `_files` bug); with no
`scipy/` member, `test_seaborn_takes_its_scipy_paths[plain]` fails with `_no_scipy` True, True and
`seaborn.external.kde`; with one byte changed in Adobe's part (downloads present),
`test_reportlab_notice_carries_its_third_party_parts` names `_glyphlist.py`'s part. The
without-`downloads/` mutants are the rules' self-tests (step 90's own code writing the notice).

### Phase 2: the build and its evidence (EXECUTED)

- **Built from empty** at `dfe8add` (phase 1 restacked; `3c0b11d` changes only a check and the
  README): every step ok in 12 min (`build/042/build.log`), the direct-call gate 0 mismatches.
  `SHA256SUMS` `c5baf6ff…`; `python.wasm` 84,791,487 bytes (`0b1b7373…`), the snapshot
  89,536,562, the zip 46,490,210 (4,498 `.pyc`, 763 data files); `MANIFEST` +2 `package` and +2
  `pin` lines.
- **Criterion 2** against 038's set (`build/042/criterion2-and-mutants.txt`): `python.wasm` is the
  same bytes; the zip adds exactly the 199 names of `build/042/names.txt` (54 under `seaborn/`,
  its `METADATA`, 143 under `reportlab/`, its `METADATA`), removes none, and changes no shared
  member; seaborn's `METADATA` equals its `PKG-INFO` and reportlab's its wheel's; no member under
  `reportlab/fonts/` or `reportlab/graphics/barcode/`. The zip grows by 2,041,073 bytes. The
  zero-patch check passes 26 trees locally (`test_source_tree_matches_its_tarball[seaborn]`
  included; `build/042/new-checks-on-built-set.txt`).
- **The guest** (`build/042/new-checks-on-built-set.txt`, `build/042/scipy-paths-on-built-set.txt`):
  both jobs equal their goldens. **The kde, violin and clustermap lines, the three not run
  in a guest with scipy before, equal native**, through `scipy.stats.gaussian_kde` and
  `scipy.cluster.hierarchy`, and so does the `seaborn.objects` line. Every other new check
  passes on both binaries. A bivariate `kdeplot` draws a `QuadContourSet` (`build/042/probe042.txt`),
  so the README's line holds.
- **The fast tier** (`-n 3`, `build/042/fast-tier.txt`): 628/768 pass, 0 fail, 3 blocked (prior-art
  clones, three systems, wheel); unit suite 1834/1841. Against 038's set on this machine
  (`build/042/growth-vs-038-set.txt`, `build/042/caps-vs-038-set.txt`): 13 checks move fail to pass,
  none falls; 182 fuel rows grow, 3 fall by at most 531,079 (layout).

**Criterion 5 and Decision 12's table, measured against 038's set (EXECUTED):**

| metric | expected | cap | measured |
|---|---|---|---|
| plain `-c pass` | ≈ +5.4 M | ≤ +5.97 M | +4,827,939 (240,667,890 → 245,495,829; 24,261 a member) |
| other plain checks | the same | ≤ +5.97 M + 0.2% | median +4,849,046; the rows listed below exceed it |
| snapshot `-c pass` | ≈ +0.48 M | ≤ +0.70 M | +529,199 (50,420,297 → 50,949,496; 2,659 a member) |
| other snapshot checks | ≈ +0.48 M | ≤ +0.70 M (+1.89 M reading metadata) | median +522,128; the rows listed below exceed it |
| the zip's bytes | +2,036,192 | ≤ +2.2 MB | +2,041,073 |
| the snapshot's bytes | ≈ +72.8 KB | ≤ +199 KB | +74,056 |
| the plain binary's bytes | 0 | 0 | 0 |

Above a row's cap, each read with its reason (a finding for the build review, as Decision 12 says;
none is a regression of the guest):
- `test_v1_3_the_zips_directory.py`'s four checks that walk every member (`test_resources_read_as_zipfile_reads_them[plain, snapshot]`
  +410.5 M and +410.0 M, `test_the_fast_reader_builds_zipimports_dict[padded, small, snapshot]` +107.2 M, +26.6 M,
  +17.2 M): each grows by 2.9% to 3.6%, in proportion to the 199 members on 5,261 (3.8%); the row
  Decision 12 names for 035's comparison, which follows the member count.
- `test_the_default_profile_runs_its_pure_python_paths[plain, snapshot]` +17.2 M and +15.6 M: its
  program lists every zip member through `zipfile` (the mypyc scan), in Python, about 80,000 a
  member.
- `test_networkx_atlas_reads_from_the_zip[plain, snapshot]` +18.1 M and +13.7 M: `import networkx`
  reads every distribution's entry points (the README says so), two more distributions; inside
  the table's ≤ 25 M per distribution per read.
- `test_the_sobol_options_need_nothing_writable[snapshot]` +5.03 M (0.049%) and
  `test_the_pandas_tz_job_matches_native[snapshot]` +1.95 M (0.041%): above the snapshot row's
  +0.70 M and +1.89 M (INFERRED: each reads metadata or resources across the zip; the plain rows of
  the same programs are within their caps).

**The rest, from CI** (the build review's finding 1). The local fast tier has no slow rows, and
the list above held every row to the looser metadata cap. The complete account compares the
macOS shard records of 042's run 39421194888 with 038's run 39415728849 on `ecc2423`, every row in
both, slow rows included (`build/042/ci_growth042.py`, `build/042/ci-growth-vs-038.txt`; EXECUTED:
227 fuel rows; where a row is also in the local records, its numbers are the local ones exactly).
Every row above its binary's base cap (snapshot +0.70 M, plain +5.97 M + 0.2%) is named here or
above:
- **Metadata readers, inside their own cap**: `test_packages_carry_their_metadata[plain, snapshot]`
  +20.2 M and +13.5 M (two more distributions read, inside the table's ≤ 50 M);
  `test_metadata_answers_from_the_zips_directory[snapshot]` +1.51 M,
  `test_numpy_and_pandas_are_builtin_at_manifest_versions[snapshot]` +0.83 M and
  `test_regex_is_builtin_at_manifest_version[snapshot]` +0.75 M (each calls
  `importlib.metadata.version`, inside +1.89 M).
- **scipy's importers, metadata readers too.** EXECUTED (`build/042/probe_rows042.py`,
  `build/042/probe-rows042.txt`, the snapshot of each set): `import scipy.linalg` imports
  `importlib.metadata` and grows +1.67 M, `import scipy.spatial` +1.01 M, while `import numpy`
  (+0.48 M), `import lxml.html` (+0.52 M) and `import regex` (+0.60 M) import no metadata and grow
  by about the snapshot's own start cost (+0.52 M). So these, all importing scipy, are under the
  +1.89 M metadata cap: `test_scipys_dotted_builtins_keep_their_import_names[snapshot]` +1.81 M,
  `test_a_flat_convex_hull_raises_qhullerror` +1.73 M, `test_a_singular_solve_raises_linalgerror`
  +1.61 M, `test_ctypes_values_scipy_makes` +1.54 M, `test_ctypes_stand_in_names_what_packages_import`
  +1.39 M, `test_scipy_lapack_job_matches_native` +1.36 M, `test_highs_reports_an_infeasible_problem`
  +1.15 M, `test_matrix_market_round_trips_in_memory` +1.12 M,
  `test_workers_run_serially_or_raise_as_documented` +0.91 M,
  `test_a_python_callbacks_exception_comes_back_through_c` +0.89 M, `test_scipy_edges_job_matches_native`
  +0.85 M and `test_scipy_solvers_job_matches_native` +0.82 M, each `[snapshot]`.
- **Past the metadata cap too, by layout**: `test_plot_contour_job_matches_native[snapshot]`
  +2,204,755 (+0.020%) and `test_scipy_numeric_job_matches_native[snapshot]` +2,147,965 (+0.021%),
  0.31 M and 0.26 M over +1.89 M. INFERRED: a snapshot row moves by up to about 2 M with the heap's
  layout; in the same family `test_plot_line_job_matches_native[snapshot]` **falls** -2,062,838, and
  `import pandas` alone falls -118,032 (EXECUTED, the probe).
- **Layout, near the start cost**: `test_read_html_uses_lxml_by_default[snapshot]` +1.30 M (it
  imports pandas, lxml and bs4; INFERRED) and `test_the_guest_package_round_trips_through_the_door[snapshot]`
  +0.74 M.
- **Plain, the member cost paid twice**: `test_a_reread_after_invalidate_caches_is_the_fast_read`
  +8,684,729 (+0.97%), over the plain cap of about 7.77 M: it reads the zip's directory, invalidates
  the caches and reads it again, so it pays the 199 members' start-up cost twice (2 × 4.83 M is
  9.7 M; INFERRED from its name and docstring).
- **Fell** (four rows): `test_plot_line_job_matches_native[snapshot]` -2,062,838 (-0.023%),
  `test_dotted_builtins_keep_their_import_names[snapshot]` -531,079, `test_pickling_a_deep_list_raises`
  -7,345, `test_unbuffered_output_survives_a_hard_exit[snapshot]` -133: layout.
- **Upstream** (`upstream-macos`, against 038): `cpython-fs` +75.7 M (+0.12%) and `numpy-lib`
  +112.1 M (+0.08%), inside the plain cap's 0.2% (the review's numbers).

The new checks' and jobs' fuel are new metrics. On the snapshot, through the judge's driver
(`build/042/probe042.txt`): `import reportlab.pdfgen.canvas, reportlab.platypus` 1,883,877,927;
`import matplotlib.pyplot` in a fresh `MPLCONFIGDIR` (its font cache built) 7,952,872,789, and with
`import seaborn` after it 19,313,780,558, so `import seaborn` itself about 11.36 G, scipy's
`stats` and `cluster` and pandas included (Decision 9). The wheel's size is the release run's.

**Criteria 3 and 6, the release workflow: run 39421194888 on `3c0b11d`** (read back with `gh run
view 39421194888 --json jobs` and `--log-failed`, `build/042/ci-failed.log`). Conclusion failure,
by growth only: 22 jobs green, among them `rebuild from the pins` on both Linux hosts, `the same
bytes from every host`, the zero-patch step with **26 trees** (inside `build and judge`), all
three `verify` jobs and **every Windows leg**; three macOS judge shards red, each `0 fail`,
`lost 0`, every red line a GREW line against main's accepted `d066695` (so 037's and 038's growth
is in them too): `own-guest` 177 rows grew, `own-embedding` 33, `upstream-macos` 2
(`cpython-fs` 62,994,222,641 → 63,099,098,748, +0.17%; `numpy-lib` 132,538,457,029 →
132,552,796,296, +0.01%). No G7 line. `gather` and the publishing jobs were skipped, as on 038's
own run 39415728849 on `ecc2423`, which went red on the same three shards. The CI build's
`python.wasm` (`0b1b7373…`), snapshot (`cd38ffd4…`) and zip (`fe40e208…`) are the local build's
bytes. **The wheel:** `wasi_python-0.1.0a8-py3-none-any.whl`, 84,660,765 bytes (question 64).

### Rebased onto main `2516875` for wave 08 (the lane, 2026-10-20)

Wave 07 (038 and 044) landed, so this branch's base `ecc2423` is inside main.
`git rebase --onto origin/main ecc2423` replayed the four commits; only the first conflicted,
in fourteen files, all where 044 added scikit-learn beside the same lines. Every hunk keeps both:
- `.github/workflows/release.yml`: both sides moved the zero-patch count from 25 to 26 (044's
  scikit-learn sdist, 042's seaborn's), so the merged count is **27** (`^27 passed`), and the
  comment says seaborn's sdist is the twenty-seventh.
- `README.md`, *What the default profile carries*: main's sentence (with scipy and scikit-learn)
  with 042's "and seaborn and reportlab (spec 042)".
- `scripts/assemble_artifacts.py` (`PACKAGES`), `tests/harness/paths.py` (`LICENCE_COMPONENTS`
  and `PACKAGES`), `tests/harness/needs.py` (`SOURCE_COMPONENTS`), `tests/harness/pins.py`
  (`SOURCE_PATTERNS`), `tests/unit/test_artifact_rules.py` (the synthetic set's pins and
  packages), `tests/jobs/oracle/pyproject.toml`: scikit-learn's entry, then 042's.
- `tests/checks/test_v1_3_data_stack.py`: the distributions in sorted order, `reportlab`,
  `scikit-learn`, `scipy`, `seaborn`; the spec comment names both 044 and 042.
- `scripts/steps/70_zip.sh`: the header comment holds 044's paragraph, then 042's; the arguments
  hold scikit-learn's `--metadata`, then seaborn's, and the four `--drop` rules (matplotlib's
  two, `sklearn/datasets/images`, then reportlab's two), with `--keep` once.
- `tests/harness/jobs.py`: `JOBS` and `PLATFORM_BOUND` gain `machine_learning`, then 042's; the
  platform comment holds both sentences.
- `tests/checks/test_v1_1_artifact_set.py`: 044's two checks, then 042's helper and three checks.
- `tests/harness/artifacts.py`: 044's `sklearn_notice_errors`, given back its closing
  `return errors`, then 042's rules.
- `tests/jobs/oracle/uv.lock`: not merged by hand. It was taken from main and regenerated with the
  pinned uv (0.9.22) under the oracle's environment: "Added reportlab v5.0.1, Added seaborn
  v0.13.2", the same 31 lines as before (`build/042/oracle-relock.txt`).

The other three commits replayed cleanly, as did `CHANGELOG.md`, `downloads/SHA256SUMS`,
`scripts/00_download.sh`, `tests/upstream/packages.toml` and the other check files. Not rebuilt
(the lane). EXECUTED on the rebased tree: ruff check and ruff format --check pass; the rules
check gives 43 passed, 1 skipped; the unit checks of the artifact rules, the build scripts and
the pins give 86 passed (`build/042/*-w08.txt`); of the pin and fetch checks of v1.5, 47 pass and
`test_every_compile_contracts_nothing` fails only because this worktree's `build/` predates 044
(no `sklearn-build/compile_commands.json`), not by anything in this branch.

### The builder's self-check

- Rebased today onto the named stacked base, 038's tip `ecc2423` (on main `958a22b`); the base is
  in the Status line and above; no conflict.
- CI run 39421194888 dispatched on this exact commit's code (`3c0b11d`; the commit after it
  touches only `context/`) and read: red lines GREW only, no G7; the Windows legs green.
- Every number above is from a measured run on this base, labelled EXECUTED; the growth list is
  this build's, against 038's set on this machine.
- For the lane: below.
- Every new check seen failing first (criterion 1 above); none has a Windows or Linux branch of
  its own (each runs the same program on every host; the jobs' goldens are compared in the guest
  everywhere, and `statistical_plots`' oracle reproduces on darwin-arm64 only, by 023's rule).
- No gap is added; the reserved follow-up (the barcode folder) is decision 73's later change.
- `tests/upstream/packages.toml` has both reason lines (closer spec 067). README rows changed: the
  default profile table (plotting, PDF), *seaborn and reportlab*, the recipe paragraph.
- CHANGELOG under the one unreleased section (0.1.0a8). No new question.
- ruff check, ruff format --check (`src/`, `tests/`), the rules check (43 passed, 1 skipped) and
  the fast tier (0 fail): green, output in `build/042/`.

### For the lane

- **Wave kind:** a package, stacked on 038 (the chain 037, 038, 042). Build-class (it touches
  `scripts/`, `downloads/SHA256SUMS` and the release workflow). Dry-run needs: none beyond the
  wave's own; its release run 39421194888 already ran every Windows leg green.
- **Claim list** (against 038's entry):
  - new passes: `test_statistical_plots_job_matches_native`, `test_pdf_reports_job_matches_native`,
    `test_reportlab_runs_its_pure_paths[plain, snapshot]`, `test_seaborn_takes_its_scipy_paths[plain, snapshot]`,
    `test_reportlab_fonts_are_not_in_the_zip`, `test_seaborn_notice_carries_its_vendored_licences`,
    `test_reportlab_notice_carries_its_third_party_parts`, `test_reportlab_writes_a_pdf_with_nothing_writable`,
    `test_source_tree_matches_its_tarball[seaborn]`, and the unit checks
    `test_a_left_out_folder_is_not_packed`, `test_reportlab_fonts_and_barcodes_are_named_in_the_zip`,
    `test_seaborn_notice_carries_its_vendored_licences`, `test_reportlab_notice_carries_its_third_party_parts`;
  - checks extended (judge changed): `test_packages_carry_their_metadata[plain, snapshot]`,
    `test_licence_notices_cover_every_component`, `test_manifest_is_well_formed` (the two
    distributions and components), the artifact rules' synthetic set, `jobs.run_in_guest`;
  - grown, with reasons: the zip's bytes +2,041,073 and the snapshot's +74,056 (199 members);
    every guest fuel row by the members' start-up cost (plain about +4.4 M to +6.2 M, snapshot
    about +0.5 M); the zip-walking rows of `test_v1_3_the_zips_directory.py`,
    `test_the_default_profile_runs_its_pure_python_paths` and `test_networkx_atlas_reads_from_the_zip`
    in proportion to the member count or two more distributions (listed above); the Sobol and
    pandas-tz snapshot rows by under 0.05%; the metadata readers (033's check +20.2 M and
    +13.5 M, and the snapshot rows that read a version); scipy's importers on the snapshot (scipy
    imports `importlib.metadata`), +0.82 M to +1.81 M; `test_plot_contour_job_matches_native[snapshot]`
    +2.20 M and `test_scipy_numeric_job_matches_native[snapshot]` +2.15 M (layout, past the
    metadata cap by 0.31 M and 0.26 M); `test_read_html_uses_lxml_by_default[snapshot]` +1.30 M and
    `test_the_guest_package_round_trips_through_the_door[snapshot]` +0.74 M (layout);
    `test_a_reread_after_invalidate_caches_is_the_fast_read` +8.68 M (the member cost twice); on
    `upstream-macos`, `cpython-fs` +75.7 M and `numpy-lib` +112.1 M against 038 (inside 0.2%); every
    row by name in *The rest, from CI* above;
  - fell: four rows, `test_plot_line_job_matches_native[snapshot]` -2,062,838,
    `test_dotted_builtins_keep_their_import_names[snapshot]` -531,079,
    `test_pickling_a_deep_list_raises` -7,345 and `test_unbuffered_output_survives_a_hard_exit[snapshot]`
    -133 (layout); retired: none; passes lost: none.
- **Flags** (paste-safe):
  - `--accept "042 seaborn 0.13.2 and reportlab 5.0.1 pure in the zip, reportlab without its fonts and barcode folder, both notices with their third-party parts"`
  - `--accept-judge "042 two golden jobs and goldens, the oracle pins and lock, eight new checks and four unit checks, the package licence metadata and source-tree lists, the zero-patch count 26"`
  - `--accept-growth "042 199 zip members: zip plus 2041073 bytes, snapshot plus 74056, plain start plus 4.83 M and snapshot start plus 0.53 M; zip-walking rows and the pure-paths scan in proportion to the member count; the reread pays the member cost twice, plus 8.68 M; metadata and entry-point readers, networkx, 033s metadata check and scipy importers on the snapshot, read two more distributions; plot_contour and scipy_numeric snapshot plus 2.20 M and 2.15 M, read_html and the guest package snapshot, by layout, as plot_line snapshot falls 2.06 M; Sobol and pandas-tz snapshot under 0.05 percent; upstream cpython-fs and numpy-lib inside 0.2 percent"`
- **Native slot:** released at the end of the build (no native build since).

### Landed in wave 08

- Accepted with the integration review's M2 clause and L2 number in `--accept-growth` (the snapshot +62,943 on the wave, against 74,056 on 042's own base) and the lane's correction of the zero-patch count in `--accept-judge` to 27 (26 before the rebase onto wave 07).
- The integration review's M1: the oracle venv was synced online with seaborn 0.13.2 and reportlab 5.0.1 before the accept, and `test_goldens_reproduce_under_the_pinned_oracle` passed.
- L3: this spec's build review has no recorded confirmation; its one later code change swaps two assertions, read by the integration reviewer and found harmless.
- Reviews: `../reviews/042-*` and the wave's integration review.
