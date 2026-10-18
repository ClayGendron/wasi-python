# 023 — matplotlib, the first milestone

- **Status:** **landed 2026-10-18** (accepted on `7c3d606` as `40d8d12`; the build review, `../reviews/023-matplotlib-first-milestone-2026-10-18.md`, confirmed it; see the Landing notes' last part). Before landing: **built 2026-10-18; revised against its build review (F1 to F7: six fixed, F4 the lane's rebase checklist); confirmed** (the landing notes below). **Spec 051's callback scan binds this build** (051, Decision 4a; written in when 051 landed, at its build review's confirmation): `test_callbacks_have_the_types_cpython_calls` is green, and a mismatch it finds is fixed by a carried patch or an upstream release, never by an exclusion. drafted 2026-10-17; revised against its pre-build review
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

Built 2026-10-18 by an agent (Claude Opus 5.5) in the worktree `wasi_python-023`, branch
`spec/023-matplotlib-first-milestone`, from main `73fb50b`. Every number below is EXECUTED on
darwin-arm64 unless marked; fuel is the judge's driver's (fixed clock and entropy, exact). The
scratch scripts and logs are in the session scratchpad, not in git. The judge was run in the
worktree on its own build, never with `--accept`.

**Commits.** `5d55e5f` (pins, steps 10, 37, 55, 60, 70, `wasi-cc`, the stand-in, cross files,
assembler), `a994dba` (the judge), `b37cd99` (step 55 renamed), `b85ed85` (the runner),
`135fb1c` (the three patches, their drafts and facts sheets, CHANGELOG), `514230b` (the upstream
harness grants matplotlib's data), `9fc679f` (README), and the commit carrying these notes.

### What the build found that the specification did not foresee (decided by §6; for the review)

1. **Two more carried patches, as spec 051's binding status line requires.** The first link of
   the plot packages failed `test_callbacks_have_the_types_cpython_calls` with 24 findings
   (EXECUTED): 21 in kiwisolver (17 `METH_NOARGS` methods and 4 `strength` getters defined with
   one parameter), 2 in Pillow (`__arrow_c_schema__` and `__arrow_c_array__`, `METH_VARARGS`,
   one parameter), and one false positive (item 2). kiwisolver's trapped the guest: `Solver()
   .addConstraint(x >= 10)` ended in `indirect call type mismatch` (EXECUTED). Neither is fixed
   upstream (Pillow `main` `6085656`, kiwisolver `main` `ef031dd`, READ; both patches apply there,
   EXECUTED `git apply --check`). So `recipes/patches/pillow-13.0.0/0001-arrow-capsule-signatures.patch`
   (2 lines) and `recipes/patches/kiwisolver-1.5.1/0001-callback-signatures.patch` (21 lines,
   made by a script that rewrote each definition once and refused any other count), each with its
   draft under `context/upstream/patches/` and a facts sheet (`18-…`, `19-…`; owner decision 80).
   After them the scan reports none, and a new golden job, `plot_callbacks`, calls all 23 and
   prints native's output on both binaries. Carried patches: 2 → 5.
2. **The scan's one false positive is fixed in the judge, not excluded.** FreeType's BDF driver's
   property table begins `{"ADD_STYLE_NAME", BDF_ATOM = 1, 1, 0}`, sixteen bytes its code points
   at, which read as a single `PyMethodDef` `{name, table index 1, METH_VARARGS}`; table index 1 is
   CPython's parser rule `_tmp_6_rule` (EXECUTED: indices 1 to 22 are all parser rules or
   `_PyPegen_*`). The scan already reasons that table indices 1 to 20 are parser rules, never a
   callback (its member rule); `harness/callbacks.py` now applies that to single definitions too
   (`PARSER_RULES = 20`). On the baseline binary no single definition points at 1 to 20; on this
   one only that record does (EXECUTED). A unit check fails without the rule and passes with it.
   `EXCLUDED` stays empty. Coverage: 3,252 array entries, 1,989 singles, 1,138 getsets, 429
   members.
3. **Spec 035 changed Decision 6's arithmetic.** Decision 6 used 76,490 fuel per zip member;
   spec 035 (landed after this specification was drafted) reads the directory at about 25,000
   a member, and its landing notes re-derived "about 610 × 25,058 ≈ +15.3 M" for this build. So
   plain start grows about a third of Decision 6's estimate (the table below). Lower growth, from
   a cause outside this build; reported, not hidden.
4. **Unicode's data terms are pinned from Unicode's own repository at a commit**, not from
   unicode.org: `https://www.unicode.org/license.txt` has no versioned copy (EXECUTED: 404 for
   `Public/17.0.0/license.txt` and its `ucd/` forms) and its copyright year changes, which would
   break the pin. The pinned file is `unicode-org/unicodetools` at `4fd8eca9`'s `LICENSE`, the
   Unicode License V3 (the same terms as unicode.org's, its copyright line `2001-2024`; EXECUTED
   `diff`). HarfBuzz 14.1.0's tables are Unicode 17.0.0's (READ).
5. **The extension archives' install paths come from meson's install plan.** `meson install
   --tags python-runtime,data` installs no extension module (they carry the `runtime` tag,
   EXECUTED: 0 archives). Step 55 reads `meson-info/intro-installed.json` (built file → install
   path, e.g. `src/_backend_agg…so` → `matplotlib/backends/_backend_agg…so`) and lays each archive,
   with its `.deps` made absolute, at that path under `build/plot-modules/`; `gen_inittab.py` takes
   the names from there, as Decision 4 says.
6. **Step 55 is `55_matplotlib`**, not the Design's `55_plot_packages`: a sixteen-letter name
   broke `build.sh --list`'s fifteen-column layout (`test_list_cuts_the_real_descriptions_at_a_word`
   failed, EXECUTED).
7. **Pillow and kiwisolver are compiled at `-O2 -DNDEBUG`**, as steps 30 and 35 compile C;
   kiwisolver with cppy's `-std=c++11`. matplotlib and the meson libraries use meson's release
   `-O3`.
8. **Judge changes beyond Decision 8's list, each forced by an existing check:** `paths.PACKAGES`
   and `LICENCE_COMPONENTS` gain the thirteen components (so every new notice is checked against
   its pinned archive); `test_packages_carry_their_metadata`'s `DISTRIBUTIONS` gains the seven new
   distributions (the list says a later specification adds to it); the unit fixtures follow; the
   build-progress unit checks count thirteen steps; `harness/upstream.py` grants matplotlib's data
   to numpy's and pandas' own tests, as the runner grants it on every call (without it pandas'
   `importorskip("matplotlib")` met `NotADirectoryError` and `pandas-io-formats` failed to collect,
   EXECUTED; with it the group passes, 976 → 977 upstream tests). The judge's driver
   (`harness/guest.py`) grants the data only when a check asks (`mpl_data=True`), so the other
   checks' preopens are unchanged. The oracle's golden for the plot records its platform in
   `tests/jobs/plot_line.platform` (the `.expected` file must equal the guest's output, so the
   platform cannot live in it), and the reproduce check and `regen.py --check` run that job only
   on the recording platform.

### Acceptance criteria against evidence

1. **The checks exist and were seen failing first.** On the baseline set (main's, rebuilt here
   byte for byte: `python.wasm` `42344e2c…`): the milestone and the other plot checks failed with
   no `matplotlib/mpl-data.zip` in the zip, kiwisolver with `ModuleNotFoundError`, the data grant
   with exit 1 (no data folder at the path), the constructor check with "reviewed, but no longer
   linked" (EXECUTED). `test_usr_local_lib_holds_only_the_zip` passed on the baseline, as a guard
   should; it is the amended layout's guard. **On an unpatched build:** with patch 0001 moved
   aside, steps 55 and 60 ran and step 60 stopped: `ERROR: _GLOBAL__sub_I_ft2font_wrapper.cpp: a
   static constructor no review has read` (EXECUTED), never reaching Wizer. The check's reviewed
   list was first written from the research binaries; on this build two names differed
   (`__cxx_global_var_init.5` for the research's `.6`, no `register_mpl`), and each constructor
   was read before it was listed: libc++'s iostream `_GLOBAL__I_000100`; Agg's two guarded
   `sRGB_conv_base<…>::lut` tables filled with `pow()` (`__cxx_global_var_init`, `.5`, in
   `_image_wrapper.cpp`); kiwisolver's strength constants and `recursive_mutex`
   (`_GLOBAL__sub_I_kiwisolver.cpp`). None calls Python (EXECUTED, `llvm-objdump -dr`).
2. **A full build from pins in a clean clone** (`git clone` of the branch at `135fb1c` into the
   scratchpad, downloads linked, `scripts/build.sh --plain`, 8 min 13 s) applied all five patches,
   built every new step and gave **the same `SHA256SUMS`, every line, as the worktree's build**
   (11 min 22 s): `python.wasm` `e0224891…`, snapshot `8eb9e357…`, zip `16ee747c…`, `MANIFEST`
   `7ecc8851…`. Two checkouts at two paths, same bytes (EXECUTED, `diff`). Both binaries run the
   milestone (the judge, below). `MANIFEST` names the 18 new pins (62 `pin` lines), the 13
   `package` lines, and every new recipe, the five patches among them (EXECUTED, `grep`).
3. **The same-bytes rebuild on arm64 Linux: not run here** (no Linux host). Left to the release
   dry run's rebuild jobs (criterion 5), which the lane runs. Two risks were closed before it:
   `-ffile-prefix-map` everywhere (`test_artifacts_carry_no_build_path` passes, and the two
   checkouts above agree), and meson cannot take a host CMake path (`cmake` points at
   `build/no-cmake`; pkgconf is the pinned binary with its search path replaced).
4. **The judge** (below): green but for growth, every growth listed with its reason; Decision 6's
   comparison in the next table.
5. **A release dry run: not run here**; the lane's.

### What the set costs (Decision 6), measured

| | before (main's set) | after | growth | Decision 6 expected |
|---|---|---|---|---|
| `python.wasm` bytes | 31,786,374 | 36,911,971 | +5,125,597 (+16.1%) | about +19% |
| snapshot bytes | 65,548,702 | 70,897,198 | +5,348,496 (+8.2%) | – |
| stdlib zip bytes | 11,203,143 | 21,948,256 | +10,745,113 (+95.9%) | about +11 MB |
| zip members | 1,760 | 2,391 | +631 | about +610 |
| plain `-c pass` fuel | 150,988,365 | 166,511,583 | +15,523,218 (+10.3%) | about +47 M (+19%) |
| snapshot `-c pass` fuel | 81,868,626 | 83,372,077 | +1,503,451 (+1.8%) | about +2% |
| plain `import numpy` | 1,041,850,698 | 1,057,526,128 | +1.5% | +4.7%, less |
| plain `import pandas` | 4,898,860,027 | 4,915,384,247 | +0.3% | +1.3%, less |
| snapshot initial memory | 906 pages (56.6 MiB) | 916 pages (57.3 MiB) | +640 KiB | – |

- **Outside Decision 6 by more than a tenth, both lower:** plain start, +15.5 M against about
  +47 M: spec 035's reader (item 3 above); +15.5 M over 631 members is 24,601 a member, 035's
  own slope. `python.wasm`, +16.1% against about +19%: Decision 6 took the memo's +19.7% less
  qhull, but that figure also held contourpy (388,785 bytes, M2's) and `_qhull`'s wrapper; less
  contourpy and qhull the memo's growth is +5,556,351 (+17.5%), and this build's is 7.8% under
  that (INFERRED: `_qhull`'s wrapper, also left out, and other flags). Neither is a regression.
- The zip: 631 new members (fontTools 344, matplotlib 109, PIL 98, mpl_toolkits 24, packaging
  23, pyparsing 19, the rest METADATA and small packages); `matplotlib/mpl-data.zip` holds 204
  files, 9,673,776 bytes stored, deflated to 4,686,989 as the outer member.
- The data's cost in the runner (wall clock, a benchmark fact, median of five): extracting it
  takes 89.6 ms (204 files, 9 folders) once per process; the per-call tree comparison 2.4 ms.

### Numbers for the owner (34): pre-importing matplotlib in the snapshot

A scratch snapshot only (nothing of it lands): this build's `python.wasm` relinked with
`PREIMPORT` adding `os.environ['MPLCONFIGDIR'] = '/tmp/matplotlib'; import matplotlib,
matplotlib.pyplot; del os.environ['MPLCONFIGDIR']`, and Wizer given the data at its nested path
and a writable `/tmp`. Fuel through the judge's driver; the plot is `tests/jobs/plot_line.py`
with its PNG save; "fresh cache" is a fresh `MPLCONFIGDIR`, as the runner's fresh `HOME` gives.

| | snapshot, no pre-import (this build) | snapshot, matplotlib pre-imported |
|---|---|---|
| the plot, fresh font cache | 7,559,402,576 | 1,019,593,157 (7.4 times less) |
| the plot, kept font cache | 5,566,539,879 | 1,019,593,157 (5.5 times less) |
| `-c pass` | 83,372,077 | 106,643,622 (+23,271,545, +27.9%) |
| `import pandas` | 83,394,416 | 106,664,998 |
| snapshot bytes | 70,897,198 | 88,387,348 (+17,490,150, +24.7%) |
| initial memory per instance | 916 pages, 57.3 MiB | 1,184 pages, 74.0 MiB (+16.75 MiB) |
| snapshot deflated (as in the wheel) | 21,434,463 | 27,881,853 (+6,447,390) |

The plain reactor's plot is 9,104,956,971 (fresh cache) and 7,112,648,546 (kept). Without the
PNG save the pre-imported plot is 561,298,537 and the unimported one 7,101,319,629 (fresh) and
5,111,089,768 (kept): the save is about 0.46 G. With pre-import the font list lives in the
snapshot, so the cache, `HOME` and `root=False` stop mattering to a plot.

### Numbers for the owner (64): the wheel against PyPI's 100 MiB limit

The wheel built as spec 028 builds it (`cp -R build/artifacts src/wasi_python/artifacts; uv
build --wheel --build-constraints release/build-constraints.txt --require-hashes`):
**52,070,134 bytes (49.7 MiB)**, against 38,940,283 (37.1 MiB) for main's set built the same
way. Its large files, deflated: `python-stdlib.zip` 21,574,949 (21,948,256 raw: its members are
already deflated), `python-snapshot.wasm` 21,434,463 (70,897,198 raw), `python.wasm` 8,805,408
(36,911,971 raw); the next largest, `runner.py`, 38,562. Headroom to 100 MiB: 52.8 MB. With
matplotlib pre-imported the snapshot would deflate to 27,881,853, a wheel of about 58.5 MB
(INFERRED: the sum).

### The judge

The full `uv run pytest` (slow checks and numpy's and pandas' own tests included, the kit fetched
with `tests/upstream/fetch.py`) on this build, the last run:

```
1 failed, 1405 passed, 9 skipped, 14 xfailed in 626.47s (0:10:26)
wasi_python v1: 339/356 pass · 14 gap · 2 blocked · 1 fail   (unit suite 1066/1073, 7 skipped)
blocked by: prior-art clones 1 · three systems 1
gaps close with: README 10 · questions-for-the-owner 2 · 2026-10-17-matplotlib-on-the-current-line 2
ratchet vs 4921daffeb: lost 1 · absent 0 · unrun 0 · unrun locally 1 · gained 23 · grew 85 · more 1 · judge changed: … and 25 more
```

- **The one failure is a wall-clock window, not this change.**
  `test_a_deadline_during_a_door_call_under_cancel_is_named` needs the guest to reach the door
  within a 50 ms deadline; it failed once, with the machine's load average at 37 on 10 cores
  (other agents' builds), and passed in this build's two earlier full runs and five times of five
  on its own (EXECUTED). The deadline is set in `_instance`, after the runner's data work
  (INFERRED, READ `_run_checked`). The run before it had one other failure, two "question"
  headings in these notes (`test_specifications_have_no_open_question`), fixed; that check then
  passed with the rest of `test_rules.py`.
- **The two gaps** are the M2 ones, failing exactly as `tests/known_gaps.toml` says.
  `test_callbacks_have_the_types_cpython_calls` is green (spec 051's binding).
  `test_goldens_reproduce_under_the_pinned_oracle` reproduces every golden, `plot_line` included
  (darwin-arm64, its recording platform); every older golden rewrote byte for byte the same.
- **Gained 23 passes and 2 gaps:** the plot job ×2, the dpi check, the kiwisolver check ×2, the
  patched-callbacks job ×2, the data grant ×2, the `/usr/local/lib` listing ×2, the constructor
  check, the feature check ×2, the eight new source trees, and `test_wheel_carries_the_artifact_set`
  (the wheel built for question 64 below carries this set); the gaps are the two M2 checks.
  `more 1`: `pandas-io-formats` 976 → 977 upstream tests passing. `unrun locally 1`: the
  prior-art licence check, blocked in a worktree as everywhere but the main tree.
- **Grew, for the accept (`--accept-growth`), every one with its reason:**
  - bytes: `python.wasm` +5,125,597 (+16.1%), the snapshot +5,348,496 (+8.2%), the zip
    +10,745,113 (+95.9%): matplotlib's stack, above.
  - 38 plain-reactor checks, each +13.6 M to +19.1 M fuel: the 631 new zip members, about 24,600
    fuel each, read at every plain start (spec 035's reader).
  - 23 snapshot checks, each +1.3 M to +1.7 M (+1.1% to +1.8%): the snapshot `-c pass` itself
    grew +1.50 M; INFERRED: finalizing zipimport's larger directory dict at exit (`os._exit`
    skips it: `test_unbuffered_output_survives_a_hard_exit[snapshot]` fell by 1,593).
  - `test_packages_carry_their_metadata`: +149.0 M snapshot (+43.5%), +165.7 M plain: it lists
    every distribution and now parses seven more `METADATA` files, fontTools' 137 KB among them.
  - `test_metadata_answers_from_the_zips_directory[snapshot]` +4.8 M and
    `test_ctypes_stand_in_names_what_packages_import[snapshot]` +4.4 M: more distributions in
    `importlib.metadata`'s scans (INFERRED); `test_npy_files_round_trip[snapshot]` +1.75 M.
  - `test_a_reread_after_invalidate_caches_is_the_fast_read` +31.3 M: two directory reads of 631
    more members.
  - `test_the_fast_reader_builds_zipimports_dict` +55.1 M snapshot, +85.2 M small, +341.4 M
    padded (+18% to +29%): it builds the dict for the whole zip, 36% more members (the padded zip
    is this zip padded).
  - `test_resources_read_as_zipfile_reads_them` +1.32 G plain, +1.30 G snapshot (+27%, +29%): the
    check compares the reactor's reader with `zipfile.Path` over every tzdata and pandas entry,
    and `zipfile.Path`'s answers scan the whole member list (INFERRED from the 36% more members;
    the reactor's own reads are unchanged, `test_a_zone_load_does_not_grow_with_the_zip` passes).
  - `test_extra_preopens_work_on_the_snapshot` ×2, +2.20 M (+0.26%): the probe visits every heap
    object, and the heap holds the larger directory.
  - numpy's and pandas' own groups: `pandas-io-formats` +1.27 G (+2.4%), because
    `test_matplotlib.py` now imports matplotlib at collection; the others −0.6% to +0.4%.

### For the build review

- The three new patches and their drafts (`recipes/patches/`, `context/upstream/patches/`,
  `17-…` to `19-…`); 0001 for matplotlib is byte-identical to the pre-build review's re-made file
  (EXECUTED `diff`).
- The callback scan's `PARSER_RULES` rule (item 2): a judge change that removes one false finding;
  is the reasoning (table indices 1 to 20 are parser rules in the linked binary) sound for singles?
- The runner (`_zip_folder`, `_extract_data`, `_data_intact`, `_remove_entry`): a member name with
  `\` or `:` is refused too (beyond Decision 5's list, for Windows); a member's type is judged by
  its mode's type bits only, since Python's `writestr` records `0o600` without them; a file that
  Windows cannot replace while a guest holds it is kept when its CRC-32 and size are right. The
  per-call comparison costs about 2.4 ms of host time on every call.
- `tests/harness/constructors.py` is imported by step 60 (`PYTHONPATH=tests`): the build runs the
  judge's own check, as Decision 4 asks, so a judge change to that list is also a build input
  (it is not in `MANIFEST`, being under `tests/`).
- Decision 6's two lower-than-expected growths (above): the per-member cost is spec 035's.
- Not run here: the arm64 Linux rebuild (criterion 3) and the release dry run (criterion 5).

### Revised against the build review

The build review (a fresh agent, 2026-10-18; its file and evidence are under the main tree's
`build/reviews-evidence/023-buildreview/` until the lane copies the review into
`context/reviews/`) found the build does what this specification says and rebuilds to the same
bytes at a third checkout path. Its verdict: lands once F1 and F2 are fixed, F3 to F7 fixed or
answered in writing. Commits: `8500f38` (F2, F3), `93f1f54` (F1, F5), `cbac924` (F6),
`af59f3c` (F7), and the commit carrying this section.

**The judge after the fixes**, the full run (slow checks and the upstream groups included) on the
set rebuilt from pins, with the wheel rebuilt as spec 028 builds it (52,070,398 bytes: the README
in its description grew):

```
1417 passed, 9 skipped, 14 xfailed in 595.05s (0:09:55)
wasi_python v1: 342/358 pass · 14 gap · 2 blocked · 0 fail   (unit suite 1075/1082, 7 skipped)
blocked by: prior-art clones 1 · three systems 1
ratchet vs 4921daffeb: lost 0 · absent 0 · unrun 0 · unrun locally 1 · gained 25 · grew 85 · more 1 · judge changed: pyproject.toml, … and 29 more
```

Gained 25: the 23 above, `test_the_readme_carries_the_licences_credit_lines` (F1) and
`test_matplotlib_finds_its_data_through_the_runner` (F7). The door-deadline check passed. The
growth list is the one above, the same 90 metric changes on the same checks (85 growths); each
fuel figure moved by under 16,000 instructions against the earlier run (the upstream groups by up
to 0.00001%), within the judge's tolerance. Nothing new grew.

## Disposition (filled in by the builder, for the reviewer's confirmation)

Of the build review's seven findings (`build/reviews-evidence/023-buildreview/023-matplotlib-first-milestone-2026-10-18.md`
in the main tree), six are fixed here, each with a check seen failing on its mutant, and one (F4)
is answered: it is the lane's checklist for a rebase that has not happened yet. The branch is not
rebased: main is frozen for code until the 0.1.0a5 tag.

1. **F1, FreeType's credit line: fixed** (`93f1f54`). The README, which is the wheel's long
   description, now says in *matplotlib in the guest*, as `docs/FTL.TXT` asks: "Portions of this
   software are copyright © 2026 The FreeType Project (https://freetype.org). All rights
   reserved." The year is 2026, the latest year FreeType 2.14.3's headers name (the review,
   READ). A new rules check, `test_the_readme_carries_the_licences_credit_lines`
   (`scan.credit_errors`), fails while a `freetype-*` file is pinned and the README lacks the
   sentence (line breaks and a blockquote's `>` read as spaces). EXECUTED: with `©` written `(c)`
   the check failed; with the line it passes.
2. **F2, the constructor list compared as a set: fixed** (`8500f38`).
   `constructors.list_errors` counts each name (`Counter`), then compares the order;
   `REVIEWED_CONSTRUCTORS` is now in link order (`init`, `__wasilibc_initialize_environ_eagerly`,
   `_GLOBAL__I_000100`, `_mi_process_init`, `register_builtin_extensions`,
   `_GLOBAL__sub_I_kiwisolver.cpp`, `__cxx_global_var_init`, `__cxx_global_var_init.5`,
   `_GLOBAL__sub_I_unique.cpp`). EXECUTED with the review's own `ctor_mutant.py` on the real
   binary: one more `__cxx_global_var_init` gives `__cxx_global_var_init: a static constructor no
   review has read (1 more than reviewed)`, one more `_GLOBAL__I_000100` the same for it; the real
   list gives none. `tests/unit/test_constructors.py` holds both mutants, a new and a missing
   name, and another order. Step 60 runs the same function, so the build stops on them too.
3. **F3, the parser-rule exemption: fixed** (`8500f38`). A single definition at table index 1 to
   20 is skipped only when the name section names the function there `*_rule` or `_PyPegen_*`;
   any other function there, or a module without names, is checked as a method. Two unit checks:
   at index 1 a function named `_tmp_6_rule` is skipped; one named `handler` or `_rule_handler` is
   a finding, also with the names cleared. EXECUTED: with the guard removed both mutant cases fail
   (2 failed); with it, 12 pass with the real binary's scan
   (`test_callbacks_have_the_types_cpython_calls`, still 1,989 singles). The member rule's older
   assumption (type codes 0 to 20 against table indices) is unchanged: a member array is found
   by its shape before any table, and the module docstring states its cost; guarding it the same
   way would change spec 051's scan beyond this finding, so it is left to a later change.
4. **F4, the rebase: answered.** Not done; the lane says when. Its checklist, as the review lists
   it: the CHANGELOG entry moves from `0.1.0a5 — unreleased` to the next unreleased section;
   `runner.py` is merged with spec 054's `_run_checked` and preopen list, the order kept as zip,
   then matplotlib's data, then the import-path entries, and
   `test_matplotlib_data_is_granted_read_only`, `test_usr_local_lib_holds_only_the_zip`,
   `test_matplotlib_finds_its_data_through_the_runner` and 054's checks run on the merge; spec
   049's API check (`tests/harness/api.py --check`) sees `MPL_DATA_MEMBER`, `MPL_DATA_GUEST` and
   the new private functions as internal names (the README names none of them in code spans);
   the README's facts table is merged by hand. After the rebase the full judge runs again.
5. **F5, stale documents: fixed** (`93f1f54`). The README's build row is 8 min 13 s with its source
   (a clean clone, spec 023's landing notes); the README's first line, `pyproject.toml`'s
   `description` (a judge change) and the package docstring say numpy, pandas and matplotlib. The
   extraction time is in a dated research memo,
   `context/research/2026-10-18-matplotlib-data-extraction-time.md`, with the script and both
   runs (median 89.6 ms in the landing notes' run, 77.9 ms in the memo's at load 22; the per-call
   comparison 2.4 and 2.7 ms).
6. **F6, an unchecked binary left in `build/out/`: fixed** (`cbac924`, with the new file in
   `8500f38`). Step 60's gate is now `check_constructors` in `scripts/steps/constructors.sh`,
   sourced by step 60: a binary that fails is removed before the step stops. A unit check runs the
   function with a stand-in check that passes and one that fails; with the `rm` disabled the
   failing case fails (EXECUTED).
7. **F7, matplotlib through `wasi_python.run`: fixed** (`af59f3c`).
   `test_matplotlib_finds_its_data_through_the_runner` runs `import matplotlib` through the real
   runner (`root=True`) and asserts `get_data_path()` is the granted path, its `fonts/ttf` holds
   the 40 fonts and `matplotlibrc` is read from there (backend `Agg`). EXECUTED: it fails on main's
   set and passes on this one; about 0.5 s.

Step 60's script changed and a recipe was added, so the set was rebuilt from pins (6 min 45 s):
`python.wasm`, the snapshot and the zip are byte for byte the reviewed ones (`e0224891…`,
`8eb9e357…`, `16ee747c…`); only `MANIFEST` changes (`01fbade7…`: the new recipe line for
`scripts/steps/constructors.sh` and step 60's hash). The growth list is unchanged (below).

### Rebased onto main 5e66995

Rebased 2026-10-18 at the lane's request, after 0.1.0a5's tag (main now carries 049, 052, 053,
054, 056 and 058 beyond the base `73fb50b`). Thirteen commits replayed.

- **Conflicts: one, in `CHANGELOG.md`** (the patches commit). main's `0.1.0a5 — unreleased` is
  now dated; spec 023's entry was moved, unchanged, into `0.1.0a6 — unreleased`, after 053's and
  052's entries. Nothing of it is in the dated 0.1.0a5 section.
- **`src/wasi_python/runner.py` merged with no conflict hunk.** git applied the runner commit's
  four hunks (the two imports, the zip folder and data functions after `_zip_known`, `_remove_zips`'s
  unpacking, and `_run_checked`'s preopens) beside 053's async tools and 054's `import_path`
  without overlap. READ after the merge: `_run_checked` walks the grants with 054's import-path
  entries, then grants the zip's `lib/` at `/usr/local/lib`, then matplotlib's data, then the
  root and the grants; 054's import-path entries are guest paths served by those grants, not
  preopens of their own, so the order zip, data, import path holds. `diff 5e66995` shows the same
  hunks the review read; **no reviewed hunk changed in substance.**
- `README.md`, `context/upstream/README.md`, `tests/harness/` (052's changes to `upstream.py`,
  `plugin.py` and others) merged without conflict. Spec 049's API check, `uv run python
  tests/harness/api.py --check`, exits 0 with the runner's new internal names. `ruff check` and
  `ruff format --check` are clean on `src` and `tests`.
- **The set, rebuilt from pins** (`scripts/build.sh --plain`, 6 min 50 s): `python.wasm`
  `e0224891…`, the snapshot `8eb9e357…`, the zip `16ee747c…` and `MANIFEST` `01fbade7…`, byte for
  byte the set after the build review's fixes. `SHA256SUMS` of the set:
  `04f14aec59199c9c8d53c64666e4f093921c58051b4a30667845b9cfe1c100d6`. The binaries and zip did
  not change, so question 34's numbers stand as measured. The wheel, built as spec 028 builds it,
  is now `wasi_python-0.1.0a6-py3-none-any.whl`, **52,091,103 bytes** (49.7 MiB; the README in its
  description and the version moved it), still about 52.8 MB under PyPI's limit.
- **The judge.** The fast tier on three workers (`-n 3`): `1478 passed, 9 skipped`, `lost 0`,
  red only for growth. The full judge, serial, once:

```
1510 passed, 9 skipped, 14 xfailed in 554.55s (0:09:14)
wasi_python v1: 374/390 pass · 14 gap · 2 blocked · 0 fail   (unit suite 1136/1143, 7 skipped)
blocked by: prior-art clones 1 · three systems 1
gaps close with: README 10 · questions-for-the-owner 2 · 2026-10-17-matplotlib-on-the-current-line 2
ratchet vs 588ec65390: lost 0 · absent 0 · unrun 0 · unrun locally 1 · gained 25 · grew 86 · more 1 · judge changed: pyproject.toml, … and 29 more
```

- **Growth:** the same list as above, plus one check that is new on main: 053's
  `test_fuel_is_exact_across_async_tool_calls`, 92,028,958 → 93,529,167 fuel (+1.50 M, +1.6%), a
  snapshot check of the same class as the other 23 (the snapshot's start grew +1.50 M).

**Landed 2026-10-18** through the lane, after the 0.1.0a5 tag, 053 and 052. The builder rebased
onto main `5e66995` ("Rebased onto main 5e66995", above); the lane compared the rebased diff with
the reviewed one (`7ccf316` against its base `73fb50b`): they differ only by the CHANGELOG's
placeholder line and the new "Rebased" section (EXECUTED, `build/lane-023-diffdiff.txt`), so no
reviewed hunk changed. The build review (`../reviews/023-matplotlib-first-milestone-2026-10-18.md`:
"lands once F1 to F7", then "confirmed, it lands after its rebase") was committed on the detached
HEAD as `7c3d606`. **The main tree's full build from pins** (`scripts/build.sh --plain`, about 7
min) gave `SHA256SUMS` `04f14aec59199c9c8d53c64666e4f093921c58051b4a30667845b9cfe1c100d6`, byte for
byte the builder's (EXECUTED, `build/lane-023-build.log`, `cmp`). The set is frozen read-only as
`build/sets/s-8eb9e35734deeb21`; builders made from main after this landing judge against it.

The first accepting run (history line 58) left one check blocked: the oracle goldens check,
`test_goldens_reproduce_under_the_pinned_oracle`, because the main tree's oracle environment did
not yet hold matplotlib 3.11.2, the pin this specification adds to `tests/jobs/oracle/uv.lock`,
and the oracle runs `--offline`. The lane fetched the locked wheel once (the oracle's own command
with network on, hash-checked by uv against the lock); the check then passed alone, and the lane
judged and accepted again so that every check ran on this commit: `wasi_python v1: 374/390 pass ·
14 gap · 2 blocked · 0 fail (unit suite 1141/1143, 2 skipped)`, `blocked by: three systems 1 ·
wheel 1`, `ratchet vs 7c3d606d09: lost 0 · absent 0 · unrun 0 · gained 0 · grew 0` after
acceptance, `1515 passed, 4 skipped, 14 xfailed in 677.80s` (EXECUTED, `build/lane-023-accept2.log`).
Accepted with `--accept-judge` and `--accept-growth` (the snapshot's start, +1.50 M fuel, carried by
every snapshot check) as `40d8d12` (history lines 58 and 59); the rules tier passed (25/25); main
fast-forwarded. **For later landings:** a specification that adds a pin to the oracle's lock needs
the lane to fetch it once before the accepting run, or the goldens check is blocked, not run.
Question 34 (pre-import) and question 64 (the wheel, 52,091,103 bytes at 0.1.0a6) stay open with
this landing's numbers.
