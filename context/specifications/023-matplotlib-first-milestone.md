# 023 — matplotlib, the first milestone

- **Status:** **Spec 051's callback scan binds this build** (051, Decision 4a; written in when 051 landed, at its build review's confirmation): `test_callbacks_have_the_types_cpython_calls` is green, and a mismatch it finds is fixed by a carried patch or an upstream release, never by an exclusion. drafted 2026-10-17; revised against its pre-build review
  (`../reviews/023-matplotlib-first-milestone-spec-2026-10-17.md`), whose confirmation passed it
  for build with five definitions (A to E), now written in. Question 35 (licences, §4.12) was answered on
  2026-10-17: the whole list is approved, so it may be built.
- **Owner:** Clay Gendron
- **Kind:** the build recipe (pins; steps 00, 10, 37 (new), 55 (new), 60, 70; `scripts/build.sh`,
  `scripts/wasi-cc`, `scripts/gen_inittab.py`, `scripts/assemble_artifacts.py`), recipe files
  (stand-ins, cross files), one carried patch, the runner (the zip folder's
  layout and a second runtime grant: matplotlib's data), judge additions and changes (`tests/`,
  `tests/harness/pins.py`, `tests/harness/needs.py`, `tests/harness/scan.py`, `tests/jobs/`), the
  release workflow's count, `README.md`, `CHANGELOG.md`, `LICENSES/`.
- **Depends on:** 017 (typed grants, the zip folder; its Decision 2 is amended here), 020
  (carried patches), 021 (landed first); the owner's answers to question 2 (matplotlib's data as
  a read-only grant, answered) and 35 (licences).
- **Research it stands on:** `../research/2026-10-17-matplotlib-on-the-current-line.md` (the whole
  set built and run in scratch, pixel-equal to native; its "ordered steps" and "new pins" are this
  specification's base), `../research/2026-10-16-what-matplotlib-needs.md`,
  `../research/2026-10-16-where-package-data-lives.md`; the pre-build review's measurements
  (fuel by zip member, the constructor lists, the data grant run through the real runner).

## The problem

matplotlib is first on §2's list after v1. Agents plot, and a plot saved to a file is the most
common thing their code makes that is not text. The research built matplotlib 3.11.2 and its
native stack for wasm32-wasip1 and matched native output pixel for pixel; this specification
brings the first, smallest useful part of that into the build.

## Decisions

1. **The milestone (M1).** `import matplotlib; matplotlib.use("agg")`, `plt.plot(...)`, `savefig`
   to PNG in a granted folder, with the RGBA buffer equal to the golden's. Built in: four C
   libraries (FreeType, HarfBuzz, SheenBidi, libraqm); matplotlib's `ft2font`, `_path`, `_image`,
   `_backend_agg`, `_c_internal_utils` and `_tri`; kiwisolver; Pillow's `_imaging`,
   `_imagingmath` and `_imagingmorph` (zlib only); and cycler, pyparsing, packaging and fonttools
   in the zip. **`_qhull` is left out of the link**, as `_tkagg` is: it cannot work without the
   second patch (a writable `/dev/null`), and leaving it out drops qhull's code (about 302 KB) and
   the `fd_renumber` import. qhull is still built in step 37, because matplotlib's configure
   requires it, but nothing of it is linked. Two known gaps in `tests/known_gaps.toml`, each
   closed by the research memo, which names the fix (M2): a Delaunay `Triangulation(x, y)` raises
   `ImportError` for `matplotlib._qhull`, and `contour` raises `ModuleNotFoundError` for
   `contourpy`. Triangles given explicitly work through `_tri`.
2. **The versions and pins** are the memo's "new pins", each a URL and SHA-256 in
   `downloads/SHA256SUMS`, fetched by `get` lines in `scripts/00_download.sh`. FreeType 2.14.3,
   HarfBuzz 14.1.0 and libraqm 0.10.5 are held at matplotlib's own wrap versions, because those
   give native pixel parity. Two files are saved under names that fit the tree rule (the `get`
   line chooses the local name; bytes and hashes are the memo's): GitHub's qhull archive as
   `qhull-8.0.2.tar.gz`, and SheenBidi's as `SheenBidi-3.0.0.tar.gz` (it unpacks to
   `SheenBidi-3.0.0`). The three `pkgconf` wheels (one per build host, a build tool only) are
   checked against PyPI's hashes on download like every pin. setuptools, setuptools_scm and
   meson-python are not pinned: small stand-ins under `recipes/` take the place of the first two
   (meson-python's stand-in is M2's, for contourpy).
3. **One carried patch:** `recipes/patches/matplotlib-3.11.2/0001-ft2font-enums-without-python.patch`,
   matplotlib's own fix (PR #30291, commit `8e5591bc`, merged for 3.12): `ft2font`'s enums no
   longer touch Python during static initialization, which hangs `_initialize` before Python
   starts. It is upstream's change whole, in `git diff` form, made against the pinned tarball with
   no offset: its changed lines equal `8e5591bc`'s in all four files, and it deletes
   `src/_enums.h` as upstream does. It keeps upstream's `ci/mypy-stubtest-allowlist.txt` line, so
   the patch stays the merged commit; that file builds nothing. `Files:
   ci/mypy-stubtest-allowlist.txt, src/_enums.h, src/_image_wrapper.cpp, src/ft2font_wrapper.cpp`.
   Its draft's header says `Status: merged <the pull request's url>`, and its body says there is
   nothing to send. The patch goes when the pin moves to a release that carries it.
4. **The build.**
   - **Step 10** installs the pinned `pkgconf` wheel for the build host into the tools folder.
   - **A new step 37, the plot libraries**, after step 35: FreeType, HarfBuzz, SheenBidi, libraqm
     and qhull, each from its pinned source into `build/<top>`, unpacked, patched (none today) and
     judged as spec 020 does, with the flags the memo lists (C: `-fwasm-exceptions -mllvm
     -wasm-enable-sjlj -mllvm -wasm-use-legacy-eh=false`; C++: `-fwasm-exceptions -mllvm
     -wasm-use-legacy-eh=false`; `-ffile-prefix-map` everywhere: the research `python.wasm` held
     12 builder paths from pybind11's headers). libraqm finds the other three through the pinned
     `pkgconf`. FreeType is built with `-Dzlib=system` against step 30's zlib, so one zlib is
     linked and one security fix covers it (§5.5).
   - **`scripts/wasi-cc` drops `-pthread`.** It would add the `+atomics` feature, a new host
     requirement; numpy and pandas never pass it (EXECUTED by the memo and the review), so their
     bytes do not change.
   - **A new step 55, the plot packages**, after step 50, needing steps 10, 20, 30 and 37: Pillow
     and kiwisolver compiled directly from their source lists against step 30's zlib, the source
     list sorted with `LC_ALL=C` so the object order is fixed; matplotlib (patched) with meson
     (`-Dsystem-freetype=true -Dsystem-libraqm=true -Dsystem-qhull=true -DrcParams-backend=Agg
     -Db_lto=false -Dmacosx=false`, the pinned `pkgconf`, pybind11's `pkgconfig` folder),
     installed with `--tags python-runtime,data` and `-Dpython.bytecompile=-1`. meson looks every program up in the cross file
     before `PATH`, so matplotlib's `find_program('python3', 'python')` runs the cross file's
     `python`, `scripts/python-wasi-cross` (step 20's pinned build-Python, EXECUTED by the review's
     confirmation), which passes `PYTHONPATH` through; the `setuptools_scm` stand-in reaches it
     there. No unpinned interpreter runs, and no shim is needed. The cross file sets `cmake` to a program that does not exist,
     so meson finds qhull the same way on every host.
   - **Step 60** takes the inittab names from the install paths (`scripts/gen_inittab.py`),
     honours `-l`/`-L` lines in `.deps`, adds `-lsetjmp`, and leaves `_tkagg` and `_qhull` out.
     **At its end it runs the constructor check** (Decision 7) on the linked `python.wasm`, so a
     build with a new static constructor stops before step 80, which would hang on it.
   - **Step 70** packs the new packages into the zip, leaving out what cannot run or is not
     built: every file of `matplotlib/backends/` except exactly `__init__`, `registry`,
     `_backend_pdf_ps`, `backend_mixed`, `backend_agg`, `backend_pdf`, `backend_ps`, `backend_svg`,
     `backend_pgf` and `backend_template` (a plot with PNG, PDF, PS, EPS and SVG saves imports the
     first eight, EXECUTED by the review's confirmation); `matplotlib/testing/`, `matplotlib/sphinxext/`, `matplotlib/tests/`
     and each package's `tests/`; and contourpy (M2). `matplotlib/mpl-data/` goes in as **one
     member**, `matplotlib/mpl-data.zip`, an inner archive of the data folder, because every zip
     member costs every plain call (Decision 6). The inner archive's files are stored and the
     outer member is deflated, so the data is compressed once and the stdlib zip's rule
     (`stdlib_zip_errors`: every member deflated, no source) holds unchanged; member order and
     times are fixed as step 70 already writes them. fontTools' `.data/` is skipped.
     fontTools goes in whole in M1: its table modules load by name at run time, so a trim needs an
     import trace first (Scope).
   - **Step 80 is unchanged in M1:** matplotlib is not pre-imported (question 34).
   - **`scripts/assemble_artifacts.py`** gains the licences (Decision 9) and the new packages in
     `PACKAGES` and `WHEELS`; `scripts/build.sh`'s `ALL` gains steps 37 and 55.
5. **The zip folder's layout and matplotlib's data grant.** matplotlib finds its data only at
   `Path(__file__).with_name("mpl-data")`, which with its code in the zip is
   `/usr/local/lib/python315.zip/matplotlib/mpl-data` (memo finding 3; EXECUTED by the review
   through the real runner: a read-only grant at that path works on both binaries).
   - **Spec 017's Decision 2 is amended.** The private zip folder now holds `lib/python315.zip`
     and `mpl-data/`. `lib/` is granted read-only at `/usr/local/lib`, so the guest sees only the
     zip there, as before; `mpl-data/` is granted read-only at the data path, after the zip's
     grant, with spec 017's identity check. Both stay inside the one private folder, so
     `_runtime_folders` judges them with the zip, and the sweep and `_release` remove them with
     no new lock and no new held folder. A zip with no `matplotlib/mpl-data.zip` member gives no
     data grant.
   - **Extraction.** The runner extracts the inner archive once per process and zip, from its
     private copy after that copy's SHA-256 check, never from the artifact path. It reads the
     deflated outer member into memory whole (a deflated member seeks backward slowly) and opens
     the inner archive from there. It refuses a
     member name that is absolute, holds `..`, or is a link, and a member that is not a regular
     file or folder. Each file is written, read back once and compared with the member's CRC-32
     and size: CRC-32 catches accidents; the trust anchor is the zip's SHA-256 and the 0700
     folder, and anyone who can write that folder can write after any check. It records every
     path with its type and stamp.
   - **Per call**, before granting, it compares the whole `mpl-data/` tree with the record: the
     same set of names, each a regular file or folder as recorded, no link, each file's stamp
     equal. On any difference it removes the folder's data and extracts again, with
     `_copy_zip`'s Windows fallback for a file a running guest holds open.
   - **The cost.** Every process pays the extraction at its first call, whether it plots or not
     (about 204 files, 9.6 MB); its time goes in the memo as a benchmark fact.
   - **Embedders without the runner** extract `matplotlib/mpl-data.zip` themselves and preopen
     it read-only at that path; the README's embedder contract says so in one line.
6. **What the set costs, stated so growth can be told from regression.** zipimport reads the
   whole central directory at each plain start, about 76,490 instructions per member (EXECUTED by
   the review: 681 more members took plain `pass` from 241.46 M to 293.98 M fuel, +21.7%; the
   snapshot, whose directory is already read, +2.0%). Decision 4's exclusions drop about 70
   members and the inner archive replaces 204 with one (INFERRED from the review's per-member
   cost and the research zip's listing). So the expected growth, each to be measured and
   recorded by the build:
   - plain `-c pass`: about +47 M fuel (+19%), from about 610 new members;
   - snapshot `-c pass`: about +2%; plain `import numpy` and `import pandas` move as the
     review measured (+4.7%, +1.3%), less with the smaller directory;
   - `python.wasm`: about +19% (the memo's +19.7%, less qhull's 302 KB);
   - the zip: about +11 MB (code, plus the data compressed inside the inner archive).
   A growth outside these by more than a tenth is a finding for the build review, not a reason
   to accept. A trimmed fontTools (Scope) is the next lever on plain start.
7. **The font cache.** On the plain reactor, and on the snapshot while matplotlib is not
   pre-imported, each call with a fresh `HOME` rebuilds matplotlib's font list (about 2.0 G
   fuel, EXECUTED by the memo). With no writable `/tmp` (`root=False` and no writable grant
   there), `import matplotlib` raises `OSError` (EXECUTED by the review). The README says both;
   that an embedder can set `MPLCONFIGDIR` to a writable grant to keep the cache between calls;
   and that a shared, writable `MPLCONFIGDIR` is trusted by later calls: its JSON names font
   files, so one call can make the next parse a font it chose. The runner sets nothing.
8. **The checks**, each seen failing first:
   - **v1.3, the milestone.** `tests/jobs/plot_line.py`, a fixed plot program, is a job like the
     others: the pinned oracle (`tests/jobs/oracle`, Python 3.15.0) gains matplotlib 3.11.2 and its
     dependencies at the same versions in `pyproject.toml` and `uv.lock`, and `regen.py` writes
     `plot_line.expected` with `MPL_IGNORE_SYSTEM_FONTS=1` and a fresh `MPLCONFIGDIR` (so the
     oracle uses only matplotlib's bundled fonts, as the guest does: natively it otherwise listed
     1,378 of the Mac's fonts, EXECUTED), and with the full SHA-256 of the RGBA bytes, the shape, and the platform
     that made it (darwin-arm64). The guest's run must give the same hash and shape on every
     platform (its pixels do not depend on the host). The reproduce-under-the-oracle check runs
     this job on the recording platform only, because native matplotlib's pixels may differ off it
     (its own tests allow it in 61 places). The guest's PNG is decoded in the harness with the
     stdlib (zlib and the five PNG filters) and its pixels must equal the RGBA golden; its bytes
     are pinned too (`b8759b7b…` on both binaries, EXECUTED by the review).
   - v1.3: `savefig(dpi=-1)` raises `ValueError`; adding contradictory required constraints to
     a kiwisolver `Solver` raises `UnsatisfiableConstraint`.
   - v1.2: the data grant refuses writes and `mkdir` (`PermissionError`, errno 63 in the guest);
     `/usr/local/lib` lists exactly `['python315.zip']` on both binaries; and the v1.2 and v1.4
     probes that do not import matplotlib give the same output as before (the existing checks
     pass unchanged, except those named under the judge changes below).
   - **v1.1, the constructor check.** The list of functions `__wasm_call_ctors` calls in
     `python.wasm`, by name from the name section, equals a reviewed list in the judge. Today it
     has 5; the patched research build 10; the unpatched one 11, the extra being
     `_GLOBAL__sub_I_ft2font_wrapper.cpp` (EXECUTED by the review). A new constructor fails the
     check until reviewed. It fails first on the unpatched build and never hangs, unlike a run.
   - v1.1: `python.wasm`'s `target_features` equal a fixed list of all ten features (EXECUTED by
     the review), so `+atomics`, `+simd128` or `+tail-call` would each fail it; its imports are
     still WASI preview1 and the door.
   - The two known gaps (Decision 1) name their checks and the memo as closer.
   - **Judge changes**, under `--accept-judge`: `test_the_zip_is_read_only_and_shared` reads the
     zip in the folder's `lib/`; `SOURCE_PATTERNS` and `needs.SOURCE_COMPONENTS` gain FreeType,
     HarfBuzz, SheenBidi, libraqm, qhull, Pillow, kiwisolver and matplotlib (fifteen trees), and
     the release workflow's count becomes `^15 passed`; `scan.cpp_exception_errors` judges every
     C++ build's flags (HarfBuzz, matplotlib, kiwisolver), not only numpy's and pandas'.
9. **Licences.** `LICENSES/` gains, each with its notice: FreeType's `LICENSE.TXT`,
   `docs/FTL.TXT`, `src/bdf/README` and `src/pcf/README` (its BDF and PCF drivers are built);
   HarfBuzz's `COPYING` and `src/ms-use/COPYING` (Microsoft, MIT), and the Unicode data terms of
   its tables, pinned like the wasi-libc notices (the text by URL and SHA-256 from unicode.org,
   since HarfBuzz's tree carries no copy); SheenBidi's (Apache-2.0); libraqm's; matplotlib's whole `LICENSE/` folder and
   Agg's `extern/agg24-svn/src/copying`; kiwisolver's; Pillow's (HPND); pybind11's and cppy's
   (BSD-3-Clause); those of the four pure packages; and with the data, the fonts' (OFL for DejaVu's
   and STIX's and Last Resort, DejaVu's public-domain part, Bitstream Vera, BaKoMa),
   `pdfcorefonts/readme.txt` beside the AFM files with the AMS notice of `cm*.afm`, and the
   ColorBrewer, Yorick, Solarized and Qt-editor notices that matplotlib's `meson.build` lists.
   qhull's is not needed: nothing of it is linked. The 2026-10-16 approval covers FreeType's
   FTL, SheenBidi and the fonts; question 35 now asks about every other licence here.

## Intent

An agent's code makes a line plot and saves it as a PNG in a granted folder, inside the same
sealed Python, and the image is the one native matplotlib makes.

## Design

```
downloads/SHA256SUMS, scripts/line.conf, scripts/00_download.sh   the pins and their get lines
scripts/steps/10_tools.sh                         the pinned pkgconf
scripts/steps/37_plot_libs.sh                     FreeType, HarfBuzz, SheenBidi, libraqm, qhull
scripts/steps/55_plot_packages.sh                 Pillow, kiwisolver, matplotlib
scripts/steps/60_link.sh, 70_zip.sh               as Decision 4; 60 runs the constructor check
scripts/wasi-cc, gen_inittab.py, build.sh, assemble_artifacts.py   as Decision 4
recipes/                                          the stand-ins and cross files
recipes/patches/matplotlib-3.11.2/0001-…patch      Decision 3; its draft under context/upstream/
src/wasi_python/runner.py                         the zip folder's layout, the data and its grant
tests/checks/…, tests/known_gaps.toml             Decision 8
tests/harness/pins.py, needs.py, scan.py          fifteen trees; C++ flags for every C++ build
tests/jobs/plot_line.py, .expected, oracle/       the golden (Decision 8)
.github/workflows/…                               the zero-diff count, 15
README.md, CHANGELOG.md, LICENSES/                Decisions 5, 7, 9
```

## Scope

In: M1. Out:
- Triangulation through `_qhull` and contourpy, with the second patch (`_qhull` without a
  writable `/dev/null`), its new upstream pull request (question 36) and the meson-python
  stand-in: the next specification (M2).
- Pre-importing matplotlib in the snapshot: question 34.
- Trimming fontTools to what matplotlib reaches: it needs a native import trace over PNG, PDF,
  PS and SVG saves, with `ttLib`'s tables kept whole; a later specification, measured against
  Decision 6's plain-start cost.
- Goldens for SVG and PDF output: M2.

## Acceptance criteria

1. The checks exist and were seen failing first: the milestone, the data grant and the
   constructor check on the current set, and the constructor check on an unpatched build.
2. A full build from pins in a clean clone applies the patch, builds every new step, and makes a
   set whose binaries run the milestone; `MANIFEST` names every new pin and recipe.
3. The same-bytes rebuild on arm64 Linux gives the same `SHA256SUMS` (spec 012), with no
   exception. If a difference cannot be fixed after two attempts, the build stops and a memo
   records it (AGENTS.md rule 7); it does not land with an exception.
4. `uv run pytest` is green with `--accept-judge` and `--accept-growth`, the growth inside
   Decision 6's expected numbers, each measured and recorded in the landing notes.
5. A release dry run passes every job.

## Landing notes

Not built.
