# 167: pdfplumber, plotly, xarray and zstd

- **Status:** first pull request built 2026-10-31 on `spec/167-pdfplumber-plotly-xarray-and-zstd` (pdfplumber with pdfminer.six, and xarray), not landed; plotly is a later pull request under this number, and Decision 10 (libzstd) is specification 169. Drafted 2026-10-30 and reviewed before it is built (the guest's imports and the build recipe: constitution §5.6): `../reviews/167-pdfplumber-plotly-xarray-and-zstd-spec-2026-10-30.md`, its Disposition taken. The owner chose it on 2026-10-30 (decisions.md, "The scope of 0.1.3") and approved choice 1's licences on 2026-10-31 (decisions.md, "The decisions of 2026-10-31 morning on the 0.1.3 work"; constitution §4.12, #72). plotly waits on PyPI's raised file limit (choice 2).
- **Date:** 2026-10-30
- **Owner:** Clay Gendron
- **Kind:** **build-class**, **a judge change**, three carried patches; not structural: nothing under `src/` changes. Two parts: A, the packages, is this specification's pull request; B, libzstd, is a decision block that specification 169 takes whole (Decision 10; `169-zstd-built-in.md`).
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

B changes the binaries, A the zip. One news file and one review belong to one number (`../changes/README.md`), so B is specification 169, with these decisions; the owner approved libzstd on 2026-10-31.

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

**How the work is split** (the owner, 2026-10-31, `../decisions.md`, "The decisions of 2026-10-31 morning on the 0.1.3 work"). This specification lands in two pull requests, and Decision 10 is a number of its own:

1. **This pull request:** pdfplumber with pdfminer.six, and xarray (Decisions 1 to 3, 5 to 9, as far as they concern these three distributions), and the wheel-size row of Decision 6.
2. **plotly** (Decisions 1, 4 and its parts of 6, 7 and 9): a later pull request under this number, merged only once PyPI's raised file limit is recorded in `../decisions.md` (criterion 8); the owner has asked PyPI for 256 MB. Until then a merge keeps the wheel under 104,857,600 bytes.
3. **libzstd and pandas' zstd** (Decision 10, B1 to B4): specification 169, drafted separately.

### The first pull request

Built 2026-10-31 by an agent (Claude Opus 5.5), a builder sub-agent of the orchestrating session, on `spec/167-pdfplumber-plotly-xarray-and-zstd`, first on `dev` at `d64f8146`, then rebased onto `dev` at `30566232` once 166's first pull request (#67) and the owner's decisions (#72) merged, the set rebuilt from the pins (`scripts/build.sh`, every step), and rebased again onto `117bcd67` once 165 (#70) merged, steps 70 to 90 rebuilt over it. The suites were measured on the set at `30566232` plus this change; the size, the start's fuel and the checks below on the set at `117bcd67` plus this change. Everything below is EXECUTED on an arm64 Mac (Darwin 25.5.0) unless marked.

**Pins** (Decision 1): PyPI read once on 2026-10-31; pdfplumber 0.11.10, pdfminer.six 20260107 and xarray 2026.9.0 are the newest, and each file's SHA-256 is PyPI's. pdfplumber is its wheel (no patch); pdfminer.six and xarray are their sdists. **The one-off comparison** (Decision 1): pdfminer.six's and xarray's sdist packages equal their wheels file for file (`diff -rq`, no difference; xarray's wheel also carries `xarray/tests`, which the zip skips), and pdfplumber's release tag's package equals its wheel. **Test sources** (Decision 7): neither pdfplumber's nor pdfminer.six's sdist holds the files its tests read (pdfplumber's `tests/pdfs/`, pdfminer's `samples/` and `tools/`), so each is tested from its release tag's archive, pinned as `pdfplumber-0.11.10-tag.tar.gz` and `pdfminer_six-20260107-tag.tar.gz`; xarray from its sdist. The tree count in `release.yml` rises from 30 (165's two) to 32 (pdfminer.six's and xarray's sdists).

**The licence sweep** (criterion 1), every staged file's header (`Copyright|licen[cs]e`) and each sdist's licence folder: pdfplumber, none in its files (MIT, its wheel's `LICENSE.txt`). pdfminer.six: `_saslprep.py` (MongoDB, Apache-2.0, with Matthias Valvekens' changes under pyHanko's MIT licence), `glyphlist.py` (Adobe Glyph List notice), `fontmetrics.py` (Adobe Core 35 AFM terms), `arcfour.py` and `runlength.py` (public domain); `latin_enc.py` and `pdffont.py` only name the glyph "copyright". xarray: `compat/pdcompat.py`, `core/utils.py`, `core/accessor_str.py`, `core/resample_cftime.py`, `coding/cftime_offsets.py`, `coding/cftimeindex.py`, `coding/frequencies.py` (pandas, BSD-3-Clause), `compat/npcompat.py` (NumPy, BSD-3-Clause), `compat/toolzcompat.py` (toolz, BSD-3-Clause), `util/deprecation_helpers.py` (scikit-learn, BSD-3-Clause), `backends/locks.py` (dask, BSD-3-Clause), `plot/utils.py` (seaborn, BSD-3-Clause, and a function from matplotlib), `groupers.py:641` (flox); its `licenses/` folder holds ANYTREE (Apache-2.0), DASK, NUMPY, PANDAS, SCIKIT_LEARN, SEABORN (BSD-3-Clause), ICOMOON (CC BY 4.0, the HTML view's icons) and PYTHON (PSF). All are within the owner's approval of 2026-10-31 (constitution §4.12: "xarray (Apache-2.0) with the BSD-3-Clause and Apache-2.0 code it adapts", and the notices the pre-build review listed, IcoMoon's among them) or already approved (PSF, matplotlib's licence). Two lines for the owner to read, not asked again since each is an MIT or PSF notice of an approved kind: pyHanko's MIT licence on Valvekens' changes in `_saslprep.py`, and Python's PSF licence in xarray's folder (no file of the package cites it). `LICENSES/pdfminer-six.txt` carries pdfminer's LICENSE, the five notices above by their lines, and the plain Apache-2.0 text; `LICENSES/xarray.txt` its LICENSE and the eight files of its `licenses/` folder; `LICENSES/pdfplumber.txt` its wheel's licence.

**The `__file__` survey** (Decision 4's rule, read for these three): pdfplumber reads nothing by path but the user's files (`repair.py` runs Ghostscript); pdfminer.six reads its `cmap/` folder by path (`cmapdb.py:249-285`), left out by Decision 3, and `glyphlist.py` and `fontmetrics.py` only in their converters; xarray reads its HTML view's files through `importlib.resources` (`core/formatting_html.py:33-36`), which works from the zip (the golden hashes the view).

**Seen failing first.** The unit row `test_a_wheel_must_fit_pypis_file_limit` failed before `PYPI_FILE_LIMIT` existed. On a set built with pdfminer.six's sdist unpatched (the patch moved aside, steps 70 to 90), `test_pdfplumber_needs_cryptography_only_for_aes` failed on both binaries and `test_pdf_tables_job_matches_native` failed, each on `import pdfplumber` raising `ModuleNotFoundError: No module named 'cryptography'`; with the patch both pass, plain and snapshot, as does `test_labelled_arrays_job_matches_native` (criterion 5). The labelled-arrays golden first differed in its HTML view: numpy's 32-bit default integer prints `dtype=int64` for an int64 array, so the job uses a float column, as the guest's own limits say.

**The patch, natively** (Decision 2): pdfminer.six's suite from its 20260107 tag on CPython 3.15.0: 242 passed, stock and patched, with `cryptography`; without it, the stock tree fails to collect 10 files, and the patched tree passes 234 and fails exactly the 8 AES tests, each naming `cryptography`. The draft is `../upstream/patches/pdfminer_six-20260107/0001-import-cryptography-where-aes-runs.md` (pdfminer's `CONTRIBUTING.md` asks for an issue first, a test and a CHANGELOG line; it says nothing of AI tools; no open issue asks for this, #429 is the history).

**In the guest** (criterion 7), the set at the head: pdfplumber-smoke 36 passes, 41.4 G; pdfminer-six-smoke 44 passes, 11.5 G; xarray-smoke 31 passes, 39.7 G. pdfplumber-r 104 passes, 171.5 G, with 31 expected (8 CLI tests start a subprocess, 17 render through pypdfium2, 6 repair through Ghostscript); pdfminer-six-r 184 passes, 86.9 G, with 14 expected (8 AES samples need cryptography; 6 read the left-out CJK maps). xarray's suite runs in eight release groups, 7,712 passes and 1,536.7 G in sum (plot 491.4 G, arrays 349.8 G, rest 225.0 G, rolling 151.9 G, dataset 103.2 G, coding 79.3 G, backends 78.5 G, dataarray 57.6 G), with 182 expected: 161 need `mmap` (scipy's netCDF3 reader maps a file opened by path; natively with `mmap.mmap` raising, the same 160 of `test_backends.py` and one of `test_concat.py` fail, and 161 of 162 natively failing tests are these, the 162nd `test_repr` below), 10 asyncio tests meet the loop's ENOTSUP, 8 meet the 32-bit default integer, one needs a thread, `TestDataset::test_repr` fails natively at these pins too, and `test_find_stack_level` counts the staged tests folder, which is not the package's folder in the zip. Two test-only wheels join `kit-extra.txt` for xarray's family: pytest-asyncio (already there) and pytz 2026.6, which `test_combine.py` and `test_variable.py` import at their top. Natively the whole xarray suite (without matplotlib) is 7,342 passed and 1 failed (`test_repr`). Reading a netCDF3 file by path needs `open_dataset(path, mmap=False)` or an open file in the guest (EXECUTED); the limitations page says so.

**Size and fuel** (criterion 2), against `dev`'s set at `117bcd67` (165's set, built in its worktree; `python.wasm` the same bytes): the zip 54,960,042 → 57,051,943 bytes (+2,091,901, +3.81%), 6,476 → 6,661 members, exactly the 185 additions (pdfminer 33 members, 330,670 bytes with its METADATA; pdfplumber 23, 125,143; xarray 128, 1,636,088), none under `pdfminer/cmap/`, no member changed; `python-snapshot.wasm` 104,660,252 → 104,864,834 (+204,582); `python.wasm` unchanged (nothing compiled moves); a plain start (`-c pass`) 277,589,139 → 282,253,209 fuel (+4,664,070, +1.68%, 25.2 k a member; Decision 9 estimated 26 k), a snapshot start 54,177,689 → 54,596,257 (+0.77%). The zip's growth was the same, byte for byte, against 166's set before 165 merged. **The wheel**, built by hand as the release workflow builds it (`release/licences.py append`, `uv build --wheel`, `licences.py check`, then `wheel_errors` on it, which passes): **101,631,881 bytes**, 3,225,719 under PyPI's 104,857,600 (the owner's interim line of 2026-10-31, which replaces decision 64's 100,000,000). Before 165 merged the same change made a wheel of 100,462,797 bytes.

**The smoke bound.** The three smoke groups add 92.5 G to the test-source smoke groups, 877.2 G with 165's (its notes), so about 969.7 G under the 1 T bound; `test_upstream_files_are_well_formed` passes.

**The budget.** `tests/lint/budget.toml` gains caps for the three families (twice each smoke group's fuel), and 165's `budget.new_upstream_families` lets a new family's cap wait for its first acceptance (this branch carried the identical hunk until 165 merged).

**Local runs at the head** (darwin arm64, the set at `117bcd67` plus this change): `ruff` clean; the fast tier (`-m "not slow" -n 3`) 4,402 passed, its only failures the two `test_ctrl_c_stops_a_computing_guest` cases, whose child missed its wall-clock limit while the machine's load average was about 270 (other builders compiling), and which pass alone (2 passed); `tests/unit` and `tests/lint` 3,515 passed; the three new guest checks and the two goldens (and 165's documents golden) pass; the three smoke groups pass (11.5 G, 41.4 G, 39.7 G); `test_source_tree_matches_its_tarball` 32 passed; `--shard=build` 56 passed; `test_wheel_carries_the_artifact_set` passes on the hand-built wheel. The release groups ran on the set at `30566232` plus this change, all ten green with their sixteen classes.

