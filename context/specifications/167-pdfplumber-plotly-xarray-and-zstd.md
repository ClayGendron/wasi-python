# 167: pdfplumber, plotly, xarray and zstd

- **Status:** drafted 2026-10-30, to be reviewed before it is built (the guest's imports and the build recipe: constitution §5.6). The owner chose it on 2026-10-30 (decisions.md, "The scope of 0.1.3"). It also waits on the owner: the five licences are not yet approved under constitution §4.12, and the wheel crosses decision 64's 100 MB line (The owner's choices).
- **Date:** 2026-10-30
- **Owner:** Clay Gendron
- **Kind:** **build-class**, **a judge change**, three carried patches; not structural: nothing under `src/` changes. The files are in Design.
- **Depends on:** landed: 007, 020, 035 (the zip's resource reader), 041 (Decision 4), 042 (an sdist for its notices; growth measured from the pins), 063 and 067, 157. Siblings: 166 lands first (CPython 3.15.2 holds `Modules/_zstd/`; pandas 3.1.0's patch folder; the oracle on the new line). 165 edits the same recipe and judge files; whichever lands second rebases and recounts. 162 to 164 and 168 touch `src/` only.
- **Research it stands on:** `../research/2026-10-30-what-0-1-3-could-carry.md`, items E and F; `../decisions.md` line 529 and question 64 (line 245); `../roadmap.md` line 89. **The drafting reads** (2026-10-30, scratch folder only): the wheels of pdfplumber 0.11.10, pdfminer.six 20260107, plotly 7.1.0, xarray 2026.9.0 and pypdfium2 5.14.0, unpacked in uv's cache on this machine (READ); each tree compiled with Python 3.14 and deflated at level 9 (EXECUTED, a scratch script, not step 70's); the oracle's CPython 3.15.0 asked for its libzstd (EXECUTED: `1.5.7`); the 0.1.2 wheel listed with `unzip -v` (EXECUTED); pandas 3.0.6's `io/common.py` in the main tree's build and 3.1.0's in uv's cache (READ).

## The problem

The memo called these pure Python over the zip, and libzstd three surfaces. The code says five things it did not.

1. pdfminer.six imports `cryptography` at the top of `pdfminer/pdfdocument.py` (lines 13 and 14). So `import pdfplumber` fails without it, and cryptography is Rust, out of 0.1.3. Only AES needs it.
2. pdfplumber requires pypdfium2, a native wheel. Only `page.to_image` reaches it (`pdfplumber/display.py:7`, imported inside `page.py:598`).
3. plotly 7.1.0 opens its validators' JSON by path (`plotly/validator_cache.py:18-26`) and its sample data by path (`plotly/data/__init__.py:400-405`). A path into the zip does not open, so every figure would fail.
4. pandas' `compression="zstd"` imports `zstandard`, not the standard library (`pandas/io/common.py:905-911` in 3.0.6, the same in 3.1.0). Linking libzstd gives two surfaces, not three.
5. The 0.1.2 wheel is 98,385,354 bytes, and the zip sits in it almost unshrunk (53,915,154 bytes stored as 53,139,109; EXECUTED). This change and 165 together take it past 100 MB, with or without plotly.

## Decisions

### 1. The pins, and what stays out

pdfplumber 0.11.10 with pdfminer.six 20260107, which it pins exactly; plotly 7.1.0; xarray 2026.9.0 (READ, their METADATA). The builder reads PyPI once at build and takes the newest. Each package taken from an sdist is first compared with its wheel through step 70's `walk` and `wheel_members` (`scripts/make_stdlib_zip.py:113`, `:149`), as 041 did for networkx; a difference beyond the patched and dropped files stops the build. plotly is 7, not the memo's 6: 7.1.0 is current, MIT, and stands on narwhals as 6 did. Every other requirement is carried. Out: pypdfium2 and cryptography (native), kaleido (a browser), anywidget, and xarray's optional engines and accelerators (netCDF4, h5netcdf, zarr, dask, numba, bottleneck, flox, cftime, pooch).

### 2. pdfminer imports cryptography where AES runs

A carried patch moves the two imports into one helper that the AES paths call (`pdfdocument.py:527-546`, `574-586`, `655`, `664`). Then `import pdfplumber` works, plain and RC4 files read, and an AES file raises `ModuleNotFoundError: No module named 'cryptography'`, as pypdf's AES raises `DependencyError` today. A stand-in `cryptography` would mislead every package that looks for the real one, pypdf first. pdfminer.six comes from its sdist, staged under `build/pure-install/` (041, Decision 4).

### 3. pdfminer's CJK maps stay out

`--drop pdfminer/cmap` leaves out 149 files, about 6.4 MB deflated. pdfminer opens them by path (`pdfminer/cmapdb.py:249-285`), which the zip cannot serve, and they are Adobe's data under Adobe's terms (`cmap/README.txt`). Identity-H and a font's own ToUnicode table are code, so most files read. Text in a font that names a predefined CJK map and has no ToUnicode table comes out as `(cid:N)`. The limitations page says so.

### 4. plotly reads its data as package data

plotly already reads plotly.js and its templates with `pkgutil.get_data` (`plotly/offline/offline.py:85-86`, `plotly/io/_templates.py:84`). A carried patch makes the validator cache and `_get_dataset` do the same, the dataset handed to the backend as a file object. plotly then comes from its sdist. `package_data/widgetbundle.js` is dropped: only `FigureWidget` reads it, by path, under Jupyter. `plotly.min.js` stays: `write_html` embeds it by default. `to_image` raises plotly's own error naming kaleido.

### 5. xarray from its sdist, with its notices

xarray adapts code from dask, seaborn and scikit-learn (comments at `xarray/backends/locks.py:16`, `plot/utils.py:163`, `util/deprecation_helpers.py:78`). Their notices are in the sdist's `licenses/` folder; the wheel carries `LICENSE` only. So the sdist is the pin, as seaborn's was (042). The HTML view reads its CSS and icons through `importlib.resources` (`core/formatting_html.py:33-36`), which 035's reader serves. netCDF4, HDF5, zarr, dask, non-standard calendars and `xarray.tutorial` fail by name.

### 6. The zip's growth is measured first

| distribution | estimate in the zip (INFERRED) |
|---|---|
| plotly with `_plotly_utils`, without the widget bundle | 8.3 MB (bytecode of `graph_objs` 4.6, `plotly.min.js` 1.5) |
| xarray | 1.6 MB |
| pdfminer.six without `cmap/` | 0.3 MB |
| pdfplumber | 0.1 MB |

About 10.4 MB and 1,750 members, 19% of the zip. Before any pin lands, the build measures each with step 70's own functions, as 042 did, and records the snapshot's bytes (the zip's directory sits in it) and a plain start's fuel. Recommended threshold: plotly lands if its measured growth is at most 9.0 MB; above it, plotly waits and the rest lands.

### 7. libzstd 1.5.7 linked in as `_zstd`

The pin is zstd 1.5.7's release tarball, the version the oracle's CPython links, so the golden compares compressed bytes as `compress.py` does for bz2 and xz. Step 35 compiles `lib/common`, `compress`, `decompress` and `dictBuilder` outside the tree, as it does bzip2 (`35_stdlib_libs.sh:26-38`), with `-O2 -DZSTD_DISABLE_ASM -DXXH_NAMESPACE=ZSTD_ -DZSTD_LEGACY_SUPPORT=0`, and without `ZSTD_MULTITHREAD`: the guest has no threads, and pre-1.0 frames are not read. Step 60 adds a Setup.local line for `_zstd` from CPython's four files (`Modules/Setup.stdlib.in:69`), puts `libzstd.a` in the weak-duplicate gate (`60_link.sh:98-100`) and `_zstd` in the dropped-module check (`:139-141`). `nb_workers` above 0 raises `ZstdError` (INFERRED). zstd is BSD-3-Clause or GPLv2; the set takes BSD-3-Clause and ships `LICENSE`. The `-V` line drops "zstd" (`recipes/reactor_bootstrap.py:24-28`).

### 8. pandas' `compression="zstd"` through the standard library

A carried patch in `recipes/patches/pandas-3.1.0/`: when `zstandard` cannot be imported, `get_handle` opens `compression.zstd.ZstdFile`, passing `level` on; `zstandard` stays first. The draft links pandas' own issue if one exists. A stand-in `zstandard` is refused, as in Decision 2.

### 9. The checks

Four golden jobs match native under the oracle, which gains the four pins and `zstandard` (natively pulling cryptography and pypdfium2, which no job reaches):

- `pdf_tables`: reportlab draws a ruled table on two pages; pdfplumber prints the text, the words' rounded boxes and `extract_tables()`; a file pypdf encrypts with RC4 opens with its password.
- `plotly_figures`: a `go.Figure` and a `px.scatter` of `px.data.iris()`; the hashes of `to_json()` and of `to_html(div_id=…, include_plotlyjs=False)`; the length and hash of a full `write_html`; `to_image`'s error.
- `labelled_arrays`: alignment, `groupby("time.month")`, `rolling`, `interp` through scipy, a DataFrame round trip, `_repr_html_`'s hash, and netCDF3 bytes written and read back.
- `zstd`: `compression.zstd` at three levels, a trained dictionary, a streaming `ZstdFile`, `tarfile`'s `w:zst` and `zipfile`'s `ZIP_ZSTANDARD`, each length and SHA-256 with its round trip; pandas' zstd CSV round-tripped and read by `compression.zstd`, its compressed bytes not printed (natively they come from `zstandard`).

Guest rows, each seen failing on today's set: `_zstd` joins `test_stdlib_c_modules_are_builtin` (`tests/checks/test_v1_1_artifact_set.py:348`); after `import pdfplumber`, `cryptography` is not in `sys.modules`, and an AES decrypt names it; `page.to_image()` names pypdfium2.

Own suites (063, 067): a survey first, then four families, a smoke group in the normal tier and the whole suite in the release tier. Expected classes: no cryptography, no pypdfium2, no processes (`pdfplumber.repair` runs Ghostscript), no kaleido, absent optional engines. `zstd` is `kind = "via"`, via `compression.zstd`, added to `stdlib_modules`. CPython's `test_zstd` (`tests/upstream/python/cpython-b.txt:140`) and the archive modules' zstd tests now run; a cap that must rise is a judge change with that reason.

### 10. The halves split

The zstd half changes the binaries; the package half changes the zip and carries the size question. Recommended: the zstd half (Decisions 7 and 8, its rows of 9) takes its own number and lands first. Until the owner answers, it is this specification's first pull request.

## Intent

`import pdfplumber`, `plotly` and `xarray` work from the zip with native's answers; `compression.zstd`, `tarfile`'s zstd modes and pandas' `compression="zstd"` work; what does not is named on the limitations page.

## Design

- Recipe: `scripts/00_download.sh` and `downloads/SHA256SUMS` (zstd, three sdists, pdfplumber's wheel, the test sources); `scripts/steps/35_stdlib_libs.sh`, `60_link.sh`; `70_zip.sh` (three sdists staged in `build/pure-install/`, three `--drop`s); `scripts/assemble_artifacts.py` (`PACKAGES`, `WHEELS`, the notices, plotly.js's bundled-licence comments among them); `recipes/reactor_bootstrap.py`; five lines in `recipes/snapshot-packages.txt`.
- Patches: `recipes/patches/<pdfminer.six top>/0001-import-cryptography-where-aes-runs.patch`, `recipes/patches/plotly-7.1.0/0001-validators-and-datasets-as-package-data.patch`, `recipes/patches/pandas-3.1.0/0002-zstd-from-the-standard-library.patch`, and a draft each under `../upstream/patches/`.
- Judge: four jobs under `tests/jobs/` and their rows in `tests/checks/test_v1_3_default_profile.py` and `test_v1_3_data_stack.py`; the guest rows; `tests/harness/paths.py`; four families under `tests/upstream/`; `packages.toml`; `tests/release_shards.toml`; `tests/jobs/oracle/pyproject.toml`.
- Documents: `docs/reference/packages.md` and `docs/reference/limitations.md` (the `_zstd` line goes; Decisions 2 to 5's limits come in).

## Scope

In: the ten decisions. Out: cryptography, pypdfium2, kaleido and a widget; pdfminer's CJK maps; xarray's file engines and dask; zstd's threads and legacy frames; the PyPI limit itself, which is the owner's request.

## Acceptance criteria

1. Before any pin lands, the zip's growth per distribution, measured with step 70's functions, is in the landing notes, and plotly is held to the owner's threshold (EXECUTED).
2. The zip's names differ from the starting set's by exactly the computed additions, none under `pdfminer/cmap/` or named `widgetbundle.js`; every tree is its tarball plus its patches (the build shard).
3. The four golden jobs match native (`tests/jobs/regen.py --check`, and their checks in the guest).
4. `_zstd` is a builtin, and the AES and `to_image` rows give their named errors, each seen failing first.
5. `python.wasm -V` names no zstd, and `_missing_stdlib_info.py` names no `_zstd` (a check).
6. The survey's classes are recorded; the four families and CPython's zstd tests pass in their tiers; every growth is claimed in the news file.
7. MANIFEST has a `package` and a notice for each of the five; the wheel's size is recorded against 100 MB (EXECUTED).
8. The fast tier, `tests/lint` and `ci-status` are green.

## The owner's choices

1. **The licences (§4.12).** Recommended: approve pdfplumber (MIT), pdfminer.six (MIT), plotly (MIT) with plotly.js 4.1.1 and the MIT and BSD-3-Clause libraries its bundled notices name, xarray (Apache-2.0) with the BSD-3-Clause notices of the code it adapts, and libzstd (BSD-3-Clause, of its BSD-or-GPLv2 choice). A further licence the build finds in a notice folder comes back before landing. Alternative: all but plotly.
2. **The wheel crosses 100 MB.** About 110 MB with this change and 165, about 102 MB without plotly (INFERRED from Decision 6 and 165's estimate). Recommended: the owner asks PyPI now to raise `wasi-python`'s file limit, to 200 MB; the build goes on, and 0.1.3's publication waits on PyPI's answer. Alternative: stop carrying a file in the wheel, a product change of its own.
3. **plotly.** Recommended: 7.1.0, landing if its measured growth is at most 9.0 MB. Alternative: plotly waits for 0.1.4.
4. **pandas' zstd.** Recommended: carry Decision 8's patch. Alternative: no patch; the documentation shows `pd.read_csv(compression.zstd.open(path))`.
5. **The split.** Recommended: the zstd half takes its own number and lands first.

## Landing notes

To be written at the landing.
