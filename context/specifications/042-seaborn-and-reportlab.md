# 042 — seaborn and reportlab

- **Status:** **Spec 051's callback scan binds this build** (051, Decision 4a; written in when 051 landed): `test_callbacks_have_the_types_cpython_calls` is green, and a mismatch it finds is fixed by a carried patch or an upstream release, never by an exclusion. drafted 2026-10-17. Revised 2026-10-18 against its pre-build review
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
   - eight modules under `reportlab/graphics/barcode/` (`__init__.py`, `code128.py`,
     `code39.py`, `code93.py`, `common.py`, `fourstate.py`, `usps.py` and `test.py`) carry
     "Copyright (c) 1996-2000 Tyler C. Sarna" under the **four-clause BSD licence**. Its clause 2
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
     - `reportlab/graphics/barcode/__init__.py`: Sarna's four-clause BSD notice, with a line
       naming the eight files that carry it (Decision 4a);
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

Not built.
