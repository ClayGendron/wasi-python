# Review of 167 — pdfplumber, plotly, xarray and zstd

- **Date:** 2026-10-30
- **Reviewer:** an agent (Claude Opus), a fresh sub-agent of the orchestrating session; not the author
- **Reviewed:** the specification as drafted, `context/specifications/167-pdfplumber-plotly-xarray-and-zstd.md`, on `docs/0.1.3-specifications` at `4849fc4e`
- **Run:** none: a specification review
- **Re-ran:** no test run. Read the cached wheels of pdfplumber 0.11.10, pdfminer.six 20260107, plotly 7.1.0, xarray 2026.9.0 and pandas 3.1.0 in uv's cache, and pandas 3.0.6 and Python 3.15.0 from the main tree's `downloads/`; `unzip -v` of the 0.1.2 wheel. The zstd tarball and the four sdists are not on this machine.
- **Time box:** 45 minutes (a package); kept.

Labels: EXECUTED means I ran it; READ means I read the file cited; INFERRED means my reasoning. No `gh` call was made and no run was dispatched.

**The claims checked.**

- pdfminer.six imports cryptography at module top: **verified** (READ). `pdfminer/pdfdocument.py:13-14` imports it. `Requires-Dist: cryptography>=36.0.0` is in its METADATA. The uses are at `:539-542`, `:574-586`, `:656` and `:664-667`. No other module imports it.
- pdfplumber reaches pypdfium2 only through `to_image`: **verified** (`display.py:7`; `page.py:598` imports it inside the function; READ).
- plotly opens its files by path: **verified**, at `validator_cache.py:18-26` and `data/__init__.py:400-405`. There is also a third site the spec misses (Finding 3).
- pandas' zstd uses the third-party `zstandard`: **verified**. 3.0.6 calls `import_optional_dependency("zstandard")` at `io/common.py:905-906`; 3.1.0 does the same at `:914-915` (READ).
- The 0.1.2 wheel is 98,385,354 bytes, with the zip stored at 53,139,109: **verified** (EXECUTED).

Also READ: `Modules/Setup.stdlib.in:69` and `Modules/_zstd/` in 3.15.0; step 35 `:26-38`; step 60 `:98-100`, `:139-141`; `recipes/reactor_bootstrap.py:24-28`; `scripts/make_stdlib_zip.py:113`, `:149`; `tests/checks/test_v1_1_artifact_set.py:348`; `tests/upstream/python/cpython-b.txt:140`; `tests/harness/shards.py:327-373` (a `via` may name a listed stdlib module); `.github/workflows/release.yml:1502-1573`.

## Acceptance criteria against evidence

1. Growth measured before any pin — sound, but it bounds the zip, not the wheel (Finding 1).
2. The zip's names and the trees — not reachable as designed: the trees are not on the lists the tree check reads (Finding 5).
3. Four goldens — two print random hashes (Finding 4); `plotly_figures` fails on `px.data.iris()` (Finding 3).
4. `_zstd`, AES and `to_image` rows — testable; the `nb_workers` error is a different class (Finding 6).
5. `-V` and `_missing_stdlib_info` — testable.
6. Survey, families, CPython's `test_zstd` — sound; where pdfplumber's tests come from is not said (Finding 10).
7. MANIFEST, notices and the wheel against 100 MB — the licence list is incomplete (Finding 2), and the wheel needs a gate, not only a record (Finding 1).
8. Fast tier, lint, `ci-status` — sound.

## Findings, most severe first

1. **High: nothing stops a release whose wheel is over PyPI's limit, and the plotly threshold bounds the wrong number** (Decision 6; owner's choices 2 and 3; `release.yml:1502-1573`). Nothing under `tests/`, `release/` or `.github/` checks the wheel's size (READ). On a tag, `publish` creates the GitHub release before `pypi` uploads. The arithmetic: 98.39 MB, plus 165's 0.9, plus Decision 6's 10.4, plus libzstd in both binaries (about 0.5, INFERRED), plus 166 up to its bounds (0.5 to 3) comes to about 110.7 to 113 MB. PyPI's default limit is 100 MiB, 104,857,600 bytes (question 64). Without plotly it is about 102.3 to 104.8 MB. That is over decision 64's 100,000,000-byte line, so the owner is asked either way, but probably under PyPI's limit, with almost no margin. "About 102 MB without plotly" mixes up the two lines. **So 0.1.3 can likely ship without a PyPI request if plotly waits. With plotly it cannot.** Failure: plotly lands under its 9.0 MB threshold before PyPI has answered. The owner tags 0.1.3, `publish` creates the GitHub release, and `pypi` is refused with "file too large". The version is on GitHub and not on PyPI. Fix: (a) a check, red on the release pull request, that the wheel is at most `PYPI_FILE_LIMIT`, a number kept in the repository (104,857,600 until PyPI grants more, its source cited); (b) choice 2 restated with both lines and this arithmetic; (c) plotly's pull request merges only once the raised limit is recorded in `decisions.md`, not on the 9.0 MB zip threshold. If the limit has not come when the rest is ready, plotly moves to 0.1.4 and the release does not wait on PyPI's queue. (d) Every pull request of this specification records the wheel's bytes, not only the last.
2. **High: the owner's licence question leaves out licences that ship** (§4.12; choice 1). All READ unless marked:
   - pdfminer.six: `_saslprep.py` is Apache-2.0 (MongoDB, Inc.). `glyphlist.py` is under Adobe's glyph-list notice. `fontmetrics.py` is under the Adobe Core 35 AFM terms. `arcfour.py` and `runlength.py` are public domain.
   - plotly: `_plotly_utils/colors/carto.py` is CARTOColors under CC BY 3.0 US. `colorbrewer.py` is Apache-2.0. `cmocean.py` and the vendored pypng in `_plotly_utils/png.py` are MIT. The ten datasets carry no terms in the wheel; `gapminder` cites gapminder.org (CC BY 4.0, INFERRED) and `tips` cites Rdatasets. `plotly.min.js` names maplibre-gl-js as BSD-3-Clause and gives its text only by URL, and names polybooljs and Jon Schlinkert's code. The other bundled libraries are not named; d3 is one (INFERRED).
   - xarray: code copied from toolz (BSD-3-Clause, `compat/toolzcompat.py`), pandas (`compat/pdcompat.py`), NumPy (`compat/npcompat.py`) and flox (Apache-2.0, `groupers.py:641`). The HTML view's icons (`static/html/icons-svg-inline.html`) likely carry the sdist's IcoMoon notice, CC BY 4.0 or GPL (INFERRED: the sdist was not read).
   - libzstd: step 35 compiles `dictBuilder/divsufsort.c`, Yuta Mori's MIT code (INFERRED).
   
   Failure: the owner approves the list as written, and the set ships CC BY 3.0 and Apache-2.0 files under notices nobody approved. "A further licence the build finds in a notice folder" catches none of these, because they sit in file headers. Fix: before choice 1 is asked, the builder lists every licence in the headers of the files it stages (`Copyright|licen[cs]e`) and in each sdist's `licenses/`, with the file that carries it. Choice 1 names each one, and each dataset's source. A notice given only by URL (maplibre) becomes a pinned input, as statsmodels' `parallel_func` notice is (`scripts/00_download.sh:269`). The alternative to put to the owner: drop `package_data/datasets/` and `carto.py`.
3. **Medium: Decision 4 misses a site, and the datasets are gzip.** `election_geojson()` opens `package_data/datasets/election.geojson.gz` by path (`plotly/data/__init__.py:181-204`). `_get_dataset` reads `.csv.gz` files, and pandas reads a file object as uncompressed: `infer_compression` says "Cannot infer compression of a buffer, assume no compression" (3.1.0, READ). Failure: `px.data.iris()` fails to parse in `plotly_figures`, and `px.data.election_geojson()` raises `FileNotFoundError`, which no check calls. Fix text: "The patch hands the backend `gzip.GzipFile(fileobj=io.BytesIO(pkgutil.get_data(...)))` and covers `election_geojson`. The golden calls it. The builder's survey greps `__file__` in `plotly` and `_plotly_utils`, and the landing notes list the result."
4. **Medium: two golden hashes are random.** xarray's HTML view uses `uuid.uuid4()` for its element ids (`core/formatting_html.py:92-93`, `:154`, `:190`, `:242`, `:628`). `write_html` without `div_id` does too (`plotly/io/_html.py:143`; READ). Failure: `labelled_arrays` and `plotly_figures` never match native. Fix text: "`write_html(..., div_id=…)`, as `to_html` has. xarray's HTML is hashed after each UUID is replaced by a fixed token. `to_json` is called with `engine="json"`, so an orjson the oracle might bring in natively cannot change the bytes."
5. **Medium: Design leaves out the lists that tie a new tree to its tarball.** It names only `tests/harness/paths.py`. Packages also join through `pins.py`'s `SOURCE_PATTERNS`, which the tree check reads (`test_v1_5_rebuild_from_pins.py:153-162`); `needs.py`'s `SOURCE_COMPONENTS` (`:149`); `upstream.py`'s `PURE_SUITES` (`:52`); and `release.yml`'s count, "^28 passed", at `:344` and `:446`. 165's Design names all of them. Failure: the builder follows Design, so the patched pdfminer and plotly trees are never compared with their tarballs (§4.1), or the count fails every build. Fix: Design names these files. The count rises by four (zstd and three sdists), and whichever of 165 and 167 lands second recounts. The patch folder is `pdfminer_six-20260107`, the sdist's top folder.
6. **Low: `nb_workers` above 0 raises `ValueError`, not `ZstdError`** (`_zstdmodule.c`, `set_parameter_error`; `test_zstd.py:297-300`; READ 3.15.0). Fix the text.
7. **Low: the reason given for depending on 166.** 3.15.0 already holds `Modules/_zstd/` and the Setup line (READ). What 167 needs from 166 is pandas' patch folder and the oracle. Fix text: "The oracle's libzstd is checked again on 166's 3.15.2. If 166 takes its fallback A (pandas 3.0.x), the zstd patch is made against that tarball and kept in its folder."
8. **Low: Decision 8 forwards only `level`.** Fix text: "Any other key in `compression` raises `TypeError` naming it; none is dropped silently. pandas' own zstd tests skip without `zstandard` (INFERRED), so the golden is the only test of this path, and the survey says so."
9. **Low: drop `plotly/labextension/` too.** It is 4.6 MB raw, JupyterLab's front end only (READ). It may be missing from the sdist, which would stop Decision 1's comparison. Say whether Decision 6's 8.3 MB counts it.
10. **Low: the sources of the suites, and Decision 1's comparison.** Say where pdfplumber's tests come from: its sdist or a tagged tarball, pinned. As in 041, the sdist-to-wheel comparison is the builder's one-off, recorded in the landing notes, unless the wheels are pinned. "Stops the build" implies a build step.
11. **Low: the drafts.** Add 165's Decision 4 sentence: each draft follows the project's contribution rules, read at build; a facts sheet where they ask (question 80).
12. **Low: fuel on every plain start.** About 1,750 members at about 26 k fuel each (044, 045) is about +45 M on every plain `-c pass`, now about 250 M (044, READ), whether or not the program imports plotly. Put the figure in choice 3.
13. **Low: plotly 7, not the decided 6.** Choice 3 should say that this departs from decision "The scope of 0.1.3", which names plotly 6.

## Constitution checks

- §4.1: each patch is defensible. A stand-in `cryptography` or `zstandard` misleads pypdf and every probe. No recipe file can make plotly read from the zip. pandas' fallback is a feature, rightly put to the owner (choice 4). Drafts are planned. Finding 5 must be fixed for the tree check to hold.
- §4.12: not met as drafted (Finding 2).
- §4.11: the `-V` line and the limitations page change. Planned.
- §4.15, §4.4: no new channel. pdfplumber's `repair` and plotly's kaleido fail by name.
- Spec 063: four families and `zstd` via `compression.zstd`, valid under `shards.py`'s rule. Holds.
- Structure: nothing under `src/`. Agreed.
- §7: nothing tripped, once Finding 1 keeps a release from publishing a wheel PyPI refuses.

## Disposition (filled in by the author, then confirmed by the reviewer)

The author's answers, 2026-10-30. The split is taken: 167 is the packages (Part A); libzstd and pandas' zstd are Decision 10, a block of decisions B1 to B4 that the lane's next free number takes whole. One news file and one review belong to one number (`context/changes/README.md`). B may land first once the owner approves libzstd.

1. **Taken.** Decision 6: `wheel_errors` gains a row refusing a wheel over `PYPI_FILE_LIMIT` (104,857,600, the source cited beside it), red on every run that builds a wheel, the release pull request included (criterion 3, a unit row). Both lines and the arithmetic are written in Decision 6 and choice 2: 102.4 to 104.9 MB without plotly, 109.3 to 111.8 MB with it, now that `labextension/` is dropped too (Finding 9). plotly is its own commit range, last. Its pull request merges only once PyPI's raised limit is recorded in `decisions.md` (criterion 8). Otherwise it moves to 0.1.4, and the release does not wait. The 9.0 MB zip threshold is gone. Every pull request records the wheel's bytes (criterion 2). **Reviewer:** confirmed (READ, Decision 6, criteria 2, 3 and 8). `wheel_errors` already runs on the built wheel in `test_v1_1_artifact_set.py:453`, so the new row is red on the release pull request before any tag.
2. **Taken.** Choice 1 now names every licence this review found, each with its file: pdfminer's Apache-2.0, Adobe glyph-list, AFM and public-domain parts; plotly's CC BY 3.0 US CARTO scales, Apache-2.0 colorbrewer, MIT cmocean and pypng, plotly.js with its named bundled libraries, and the datasets' sources; xarray's toolz, pandas, NumPy and flox code and its icons; libzstd's divsufsort. maplibre's notice is pinned from its URL. Criterion 1 sweeps every staged file's headers and each sdist's `licenses/` before the owner is asked, and the owner is asked with the swept list. The alternatives offered are all but the datasets, or all but plotly. **Reviewer:** confirmed (READ, choice 1 and criterion 1). The sweep before the question catches what this review did not read. The IcoMoon and divsufsort lines stay INFERRED until the sweep runs.
3. **Taken.** Decision 4 now covers `election_geojson`, and hands the backend a `gzip.GzipFile` over the bytes. The survey greps `__file__` and lists each hit. The golden calls `election_geojson`. **Reviewer:** confirmed (READ, Decision 4 and the golden).
4. **Taken.** Decision 7: a fixed `div_id` for `to_html` and `write_html`; `to_json(engine="json")`; xarray's HTML hashed after each UUID becomes a fixed token. **Reviewer:** confirmed (READ, Decision 7).
5. **Taken.** Design names `pins.py` `SOURCE_PATTERNS`, `needs.py` `SOURCE_COMPONENTS`, `upstream.py` `PURE_SUITES` and the "28 passed" count at `release.yml:344` and `:446`. The count rises three here and one in Part B, and whichever of 165 and 167 lands second recounts. The patch folder is `pdfminer_six-20260107`. **Reviewer:** confirmed (READ, Design).
6. **Taken.** B1 says `ValueError`. **Reviewer:** confirmed (READ, B1).
7. **Taken.** Depends on says why 166 comes first: pandas' folder and the oracle. B rechecks the oracle's libzstd on 3.15.2, and makes its patch against whichever pandas 166 pins. **Reviewer:** confirmed (READ, Depends on, B).
8. **Taken.** B2: any key but `level` raises `TypeError` naming it. pandas' own zstd tests skip without `zstandard` (INFERRED), so B's golden is that path's only test. **Reviewer:** confirmed (READ, B2).
9. **Taken.** `labextension/` is dropped (about 1.45 MB deflated, EXECUTED with the drafting script). The 6.9 MB plotly estimate excludes it and the widget bundle. **Reviewer:** confirmed (READ, Decision 4 and criterion 4).
10. **Taken.** Decision 7 names pdfplumber's test source: its sdist if that holds `tests/`, else its tag's archive, pinned. Decision 1 makes the sdist-to-wheel comparison the builder's one-off, recorded in the landing notes. **Reviewer:** confirmed (READ, Decisions 1 and 7).
11. **Taken.** Decision 8. **Reviewer:** confirmed (READ, Decision 8).
12. **Taken.** Decision 9 gives about 45 M fuel on every plain start, and choice 3 cites it. **Reviewer:** confirmed (READ, Decision 9 and choice 3).
13. **Taken.** Decision 1 and choice 3 say 7.1.0 departs from the decision's "plotly 6". **Reviewer:** confirmed (READ, Decision 1 and choice 3).

## Verdict

Fit to build once the owner approves the licences of choice 1: the two Highs and the three Mediums are answered in the amended specification, and the ten Lows are written in, each confirmed above at the second reading of 2026-10-30. Part B (libzstd and pandas' zstd) builds under its own number once the owner approves libzstd.
