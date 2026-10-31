# 167: pdfplumber, plotly, xarray and zstd

- **Status:** drafted 2026-10-30, to be reviewed before it is built (the guest's imports and the build recipe: constitution §5.6). The owner chose it on 2026-10-30 (decisions.md, "The scope of 0.1.3"). Revised the same day against its pre-build review, `../reviews/167-pdfplumber-plotly-xarray-and-zstd-spec-2026-10-30.md` (its Disposition). It waits on the owner: the licences of choice 1 are not yet approved under constitution §4.12, and plotly waits on PyPI (choice 2).
- **Date:** 2026-10-30
- **Owner:** Clay Gendron
- **Kind:** **build-class**, **a judge change**, three carried patches; not structural: nothing under `src/` changes. Two parts: A, the packages, is this specification's pull request; B, libzstd, is a decision block that the lane's next free number takes whole (Decision 10).
- **Depends on:** landed: 007, 020, 035 (the zip's resource reader), 041 (Decision 4), 042 (an sdist for its notices; growth measured from the pins), 063 and 067, 157. Siblings: 166 lands first (pandas' patch folder, the oracle; B rechecks the oracle's libzstd on 3.15.2, and makes its patch against whichever pandas 166 pins). 165 shares files; the second to land rebases. 162 to 164 and 168 touch `src/` only.
- **Research it stands on:** `../research/2026-10-30-what-0-1-3-could-carry.md`, items E and F; `../decisions.md` line 529 and question 64 (line 245); `../roadmap.md` line 89. **Drafting reads** (2026-10-30): the four wheels and pypdfium2's in uv's cache (READ); each tree compiled with Python 3.14 and deflated (EXECUTED, a scratch script, not step 70's); the oracle CPython's libzstd (EXECUTED: `1.5.7`); the 0.1.2 wheel (EXECUTED).

## The problem

1. pdfminer.six imports `cryptography` at the top of `pdfminer/pdfdocument.py` (lines 13 and 14), so `import pdfplumber` fails without it. Only AES needs it.
2. pdfplumber requires pypdfium2, a native wheel; only `page.to_image` reaches it (`display.py:7`, imported inside `page.py:598`).
3. plotly opens its validators, its datasets and its election map by path (`plotly/validator_cache.py:18-26`, `plotly/data/__init__.py:181-204` and `:400-405`). A path into the zip does not open.
4. pandas' `compression="zstd"` imports `zstandard`, not the standard library (`io/common.py:905-906` in 3.0.6, `:914-915` in 3.1.0).
5. The 0.1.2 wheel is 98,385,354 bytes, the zip in it almost unshrunk (EXECUTED). Nothing checks the wheel's size, and on a tag `publish` creates the GitHub release before `pypi` uploads (`.github/workflows/release.yml:1502`, `:1541`).

## Decisions

### 1. The pins, and what stays out

pdfplumber 0.11.10 with pdfminer.six 20260107, which it pins exactly; plotly 7.1.0; xarray 2026.9.0 (READ, their METADATA). The builder takes the newest at build. plotly is 7, departing from the decision's "plotly 6": 7.1.0 is current. pdfminer.six, plotly and xarray come from their sdists (041, Decision 4); the builder compares each sdist's package with its wheel once, through step 70's `walk` and `wheel_members` (`scripts/make_stdlib_zip.py:113`, `:149`), and records the result in the landing notes. Out: pypdfium2, cryptography, kaleido, anywidget, and xarray's optional engines.

### 2. pdfminer imports cryptography where AES runs

A carried patch, `recipes/patches/pdfminer_six-20260107/`, moves the two imports into one helper the AES paths call (`pdfdocument.py:539-542`, `574-586`, `656`, `664-667`). Plain and RC4 files read; an AES file raises `ModuleNotFoundError: No module named 'cryptography'`, as pypdf's AES raises `DependencyError` today. A stand-in `cryptography` would mislead pypdf's probe for the real one.

### 3. pdfminer's CJK maps stay out

`--drop pdfminer/cmap` leaves out 149 files, about 6.4 MB deflated. pdfminer opens them by path (`pdfminer/cmapdb.py:249-285`); Identity-H and ToUnicode tables are code, so most files read. A font that names a predefined CJK map and has no ToUnicode table reads as `(cid:N)`; the limitations page says so.

### 4. plotly reads its data as package data

plotly reads plotly.js with `pkgutil.get_data` (`plotly/offline/offline.py:85-86`). A carried patch does the same for the validators' JSON, `_get_dataset` and `election_geojson`, handing the backend `gzip.GzipFile(fileobj=io.BytesIO(...))`, since pandas reads a buffer as uncompressed. The survey greps `__file__` in `plotly` and `_plotly_utils`, and the landing notes list each hit. `package_data/widgetbundle.js` and `labextension/` are dropped: FigureWidget and JupyterLab only. `plotly.min.js` stays, since `write_html` embeds it. `to_image` raises plotly's error naming kaleido.

### 5. xarray from its sdist, with its notices

xarray carries code from dask, seaborn, scikit-learn, toolz, pandas, NumPy and flox (READ, the review's Finding 2). Its sdist's `licenses/` folder holds their notices; the wheel holds `LICENSE` only. Its HTML view reads its files through `importlib.resources` (`core/formatting_html.py:33-36`), which 035's reader serves. Its absent engines and `xarray.tutorial` fail by name.

### 6. The size: measured on every pull request, and gated

| distribution | in the zip (INFERRED) |
|---|---|
| plotly, less its two Jupyter parts | 6.9 MB |
| xarray | 1.6 MB |
| pdfminer.six without `cmap/` | 0.3 MB |
| pdfplumber | 0.1 MB |

The two lines are decision 64's 100,000,000 bytes and PyPI's limit, 104,857,600 bytes (100 MiB). From 98.39 MB, with 165's 0.9, Part B's 0.5 and 166's 0.5 to 3: about 102.4 to 104.9 MB without plotly, and 109.3 to 111.8 MB with it (INFERRED). So:

- `wheel_errors` (`tests/harness/artifacts.py:236`) gains a row: the wheel is at most `PYPI_FILE_LIMIT`, a constant beside it, 104,857,600 until PyPI grants more, with its source in a comment. It is red on any run that builds a wheel, the release pull request included, so no tag publishes a wheel PyPI refuses.
- plotly is its own commit range, last, and its pull request merges only once PyPI's raised limit is recorded in `decisions.md`. If it has not come when the rest is ready, plotly moves to 0.1.4; the release does not wait on PyPI.

### 7. The checks

Golden jobs match native under the oracle, which gains the pins:

- `pdf_tables`: reportlab draws a ruled table on two pages; pdfplumber prints the text, the words' rounded boxes and `extract_tables()`; a file pypdf encrypts with RC4 opens with its password.
- `plotly_figures`: a `go.Figure` and a `px.scatter` of `px.data.iris()`; `px.data.election_geojson()`'s feature count; `to_json(engine="json")`'s hash; `to_html` and `write_html` with a fixed `div_id`; `to_image`'s error.
- `labelled_arrays`: alignment, `groupby("time.month")`, `rolling`, `interp` through scipy, a DataFrame round trip, netCDF3 bytes round-tripped, and `_repr_html_` hashed after each UUID (`core/formatting_html.py:92-93`) is replaced by a fixed token.

Guest rows: after `import pdfplumber`, `cryptography` is not in `sys.modules`, and an AES decrypt names it; `page.to_image()` names pypdfium2.

Own suites (063, 067): a survey, then four families, a smoke group in the normal tier and the whole suite in the release tier. Test sources, pinned: the three sdists; pdfplumber's sdist if it holds `tests/`, else its release tag's archive. Expected classes: no cryptography, no pypdfium2, no processes (`pdfplumber.repair` runs Ghostscript), no kaleido, absent engines.

### 8. Upstream drafts

Each draft under `../upstream/patches/` follows its project's contribution rules, read at build, as a facts sheet where they ask (question 80).

### 9. Fuel on every start

About 1,750 more members cost about 45 M of fuel on every plain start, now about 250 M, (INFERRED: 26 k a member, 044 and 045). The news file claims it.

### 10. Part B, libzstd: a block the next number takes

B changes the binaries, A the zip. One news file and one review belong to one number (`../changes/README.md`), so B takes the next free number with these decisions, and may land first once libzstd is approved.

- **B1. libzstd 1.5.7 as `_zstd`.** The pin is zstd 1.5.7's release tarball, the oracle's version, so the golden compares compressed bytes. Step 35 compiles `lib/common`, `compress`, `decompress` and `dictBuilder` outside the tree, as bzip2 (`35_stdlib_libs.sh:26-38`), with `-O2 -DZSTD_DISABLE_ASM -DXXH_NAMESPACE=ZSTD_ -DZSTD_LEGACY_SUPPORT=0`, without `ZSTD_MULTITHREAD`. Step 60 adds `_zstd` from CPython's four files (`Modules/Setup.stdlib.in:69`), `libzstd.a` to the weak-duplicate gate (`60_link.sh:98-100`) and `_zstd` to the dropped-module check (`:139-141`). `nb_workers` above 0 raises `ValueError`. The `-V` line drops "zstd" (`recipes/reactor_bootstrap.py:24-28`).
- **B2. pandas' `compression="zstd"`.** A carried patch: without `zstandard`, `get_handle` opens `compression.zstd.ZstdFile` with `level`; any other key raises `TypeError` naming it. pandas' own zstd tests skip without `zstandard` (INFERRED), so B's golden is this path's only test.
- **B3. Its checks.** A `zstd` golden job: `compression.zstd` at three levels, a trained dictionary, a streaming `ZstdFile`, `tarfile`'s `w:zst`, `zipfile`'s `ZIP_ZSTANDARD`, each length and SHA-256 with its round trip; pandas' zstd CSV round-tripped and read by `compression.zstd`, its bytes not printed (the oracle's pandas writes through `zstandard`). `_zstd` joins `test_stdlib_c_modules_are_builtin` (`tests/checks/test_v1_1_artifact_set.py:348`); `-V` and `_missing_stdlib_info.py` name no zstd. `zstd` is `kind = "via"`, via `compression.zstd`, in `stdlib_modules`; CPython's `test_zstd` (`tests/upstream/python/cpython-b.txt:140`) and the archive modules' zstd tests run, and a cap that must rise is a judge change with that reason.
- **B4. Its files.** Those of B1 to B3, `downloads/SHA256SUMS`, `00_download.sh`, `assemble_artifacts.py`, `recipes/snapshot-packages.txt` (`zstd: compression.zstd`), and the tree lists of Design, one more each.

## Intent

pdfplumber, plotly and xarray work from the zip with native's answers; no wheel PyPI would refuse is tagged.

## Design

- Recipe: `scripts/00_download.sh`, `downloads/SHA256SUMS`; `scripts/steps/70_zip.sh` (three sdists staged in `build/pure-install/`, four `--drop`s); `scripts/assemble_artifacts.py` (`PACKAGES`, `WHEELS`, the notices); `recipes/snapshot-packages.txt` (`pdfminer-six`, `pdfplumber`, `plotly: plotly plotly.graph_objects plotly.express`, `xarray`).
- Patches: `recipes/patches/pdfminer_six-20260107/0001-import-cryptography-where-aes-runs.patch`, `recipes/patches/plotly-7.1.0/0001-data-as-package-data.patch`, each with its draft.
- The tree lists, each one more per sdist, so every patched tree is compared with its tarball (§4.1): `tests/harness/pins.py` (`SOURCE_PATTERNS`), `tests/harness/needs.py` (`SOURCE_COMPONENTS`), `tests/harness/upstream.py` (`PURE_SUITES`), and the "28 passed" count at `.github/workflows/release.yml:344` and `:446` (three more here, one in Part B; whichever of 165 and 167 lands second recounts).
- Judge: `tests/harness/artifacts.py` (`PYPI_FILE_LIMIT`) and its row in `tests/unit/test_artifact_rules.py`; three jobs under `tests/jobs/` and their rows in `tests/checks/test_v1_3_default_profile.py`; the guest rows; `tests/harness/paths.py`; four families under `tests/upstream/`; `packages.toml`; `tests/release_shards.toml`; `tests/jobs/oracle/pyproject.toml`.
- Documents: the packages and limitations pages.

## Scope

In: Decisions 1 to 9; Decision 10 as the next number's text. Out: cryptography, pypdfium2, kaleido, widgets, CJK maps, xarray's engines; the PyPI request, the owner's.

## Acceptance criteria

1. Before choice 1 is asked, the builder's sweep lists every licence in the headers (`Copyright|licen[cs]e`) of every file staged and in each sdist's `licenses/`, with its file (EXECUTED, in the landing notes).
2. The zip's growth per distribution, measured with step 70's functions, and the wheel's bytes are in each pull request's landing notes (EXECUTED).
3. `wheel_errors` refuses a wheel over `PYPI_FILE_LIMIT`, seen failing first (unit row).
4. The zip's names differ from the starting set's by exactly the computed additions, none under `pdfminer/cmap/`, `plotly/labextension/` or named `widgetbundle.js`; every tree is its tarball plus its patches (the build shard).
5. The three golden jobs match native (`tests/jobs/regen.py --check`, and their checks in the guest).
6. The AES and `to_image` rows give their named errors, each seen failing first.
7. The survey's classes are recorded; the four families pass in their tiers; every growth is claimed.
8. plotly's pull request cites PyPI's recorded limit in `decisions.md`.
9. The fast tier, `tests/lint` and `ci-status` are green.

## The owner's choices

1. **The licences (§4.12).** Recommended: approve, each shipped with its notice:
   - pdfplumber: MIT.
   - pdfminer.six: MIT; `_saslprep.py` Apache-2.0 (MongoDB, Inc.); `glyphlist.py` the Adobe Glyph List notice; `fontmetrics.py` the Adobe Core 35 AFM terms; `arcfour.py` and `runlength.py` public domain.
   - plotly: MIT; `_plotly_utils/colors/carto.py` CARTOColors, CC BY 3.0 US; `colorbrewer.py` Apache-2.0; `cmocean.py` and the vendored pypng MIT; plotly.js 4.1.1, MIT, with its bundled libraries (maplibre-gl-js BSD-3-Clause, its text pinned from its URL; polybooljs; Jon Schlinkert's code; d3, INFERRED); the ten datasets under their sources' terms (gapminder CC BY 4.0, INFERRED; tips from Rdatasets).
   - xarray: Apache-2.0; code from dask, seaborn, scikit-learn, toolz, pandas and NumPy (BSD-3-Clause) and flox (Apache-2.0); its HTML icons (IcoMoon, CC BY 4.0 or GPL, INFERRED).
   - Part B's libzstd 1.5.7: BSD-3-Clause, of its BSD-or-GPLv2 choice, with divsufsort (MIT, INFERRED).
   
   Criterion 1's sweep may add to this list; the owner is asked with the swept list. Alternatives: all but plotly's datasets (`px.data` then fails by name); all but plotly.
2. **PyPI's limit.** Recommended: ask PyPI now to raise `wasi-python`'s file limit to 200 MB; plotly waits on the recorded answer, and moves to 0.1.4 if it has not come. Alternative: plotly to 0.1.4 now. Without plotly, the wheel is 102.4 to 104.9 MB: past decision 64's line, at PyPI's.
3. **plotly.** Recommended: 7.1.0 (the decision named 6), about 6.9 MB of the zip and part of the 45 M fuel of Decision 9.
4. **pandas' zstd (B2).** Recommended: carry the patch. Alternative: document `pd.read_csv(compression.zstd.open(path))`.

## Landing notes

To be written at the landing.
