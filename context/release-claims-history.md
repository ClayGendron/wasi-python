# The release claims, by release

`release/version.py date` moves each file of the ledger (`release-claims/NNN-<slug>.toml`, one per pull request) here, under the version it dates and under the file's name, in file-name order, before the release pull request, and removes the file; the ledger's folder keeps its README alone. The release pull request's gather and acceptance read the version's blocks, with any file written since, as their claims (`progress/README.md`, "The release tier" and "Acceptance from CI's record"). Until 0.1.0 the release acceptance moved them. Until 0.1.2 the ledger was `release-tier-claims.toml` and this file `release-tier-claims-history.md`, and they carried release-tier claims alone; the 0.1.2 block below names the ledger by its old name, as it was written. Until specification 177 the ledger was the single file `release-claims.toml`, whose blocks `date` moved as one fence; 0.1.2's section and those before it keep that shape.

## 0.1.3

Moved by `release/version.py date` on 2026-11-01, before the release pull request.

`159-the-runs-take-the-shape-the-data-asks-for.toml`:

```toml
[[claim]]
spec = "159"
new = ["tests/checks/test_v1_3_upstream_suites.py::test_upstream_trap[sympy-slow-uniform-P]"]
retired = ["tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[sympy-r-stats-4-continuous-rv-2]"]
grows = ["tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[sympy-*"]
growth = "sympy's release tier under CPython 3.15.2. One group measured, on darwin arm64 against dev's set: sympy-r-stats-4-continuous-rv-2, the single test test_uniform_P, 3,542,150,840,058 fuel against the accepted 2,865,065,511,960 (+23.6%); its leg passed the release judge job's 30 minutes in the weekly-shape run 41201012715, so by the owner's choice of 2026-10-31 the group is retired and the test is the trap sympy-slow-uniform-P, run alone to the 50 G cap, a gap. Its neighbours, run on the same set: sympy-r-stats-4-continuous-rv-1 +0.070% and -3 -0.050%, the same passes. Why test_uniform_P grew is not established (CPython 3.15.2's C-stack check in tuple hashing is a hypothesis). The other sympy groups are read at the next weekly run, under CPython 3.15.2"
```

`165-python-docx-and-python-pptx.toml`:

```toml
[[claim]]
spec = "165"
new = [
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[python-docx-r]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[python-pptx-r]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[python-docx-r-bytesio-mocked-in-a-fixture]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[python-pptx-r-bytesio-mocked-in-a-fixture]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[python-pptx-r-bytesio-mocked-in-a-test]",
]
grows = ["tests/checks/test_v1_3_upstream_suites.py::*"]
growth = "python-docx 1.2.0 and python-pptx 1.0.2 join the zip, 214 members, so every guest's zip directory is larger: a plain start +1.93% and a snapshot start +1.01% in fuel (darwin arm64). Their whole suites measure 105.8 G (1,571 passes) and 150.0 G (2,677 passes) on darwin arm64; six tests that patch io.BytesIO for the whole interpreter fail under the driver's sys capture, as natively under --capture=sys"
```

`166-the-pins-move-for-0-1-3.toml`:

```toml
[[claim]]
spec = "166"
passes = [
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pypdf-r]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[soupsieve-r]",
]
grows = [
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-release-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[numpy-slow-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pandas-slow-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[soupsieve-r]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[scipy-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[scikit-learn-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[statsmodels-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[matplotlib-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[contourpy-*",
]
growth = "the pins move for 0.1.3's first pull request: CPython 3.15.2, numpy 2.5.4, pypdf 6.21.4, soupsieve 3.0.4, wrapt 2.5.2, tzdata 2026.6. Measured on darwin arm64 against dev's set: numpy's, pandas' and CPython's 18 release groups +0.199% in sum (median +0.134%, from -0.130% to +1.108%, cpython-release-b-inline the most), every pass count the same; pypdf-r -2.417% with 1,695 passes (1,474: three releases' new tests); soupsieve-r 31.4 G to 185.8 G (cap 280 G) with 400 passes (322): 3.0.4's new tests, and test_api.py, whole, moved to it from soupsieve-smoke, whose two new exhaustive tests measure about 141 G, past a smoke group's 100 G. The release groups over numpy (scipy, scikit-learn, statsmodels, matplotlib, contourpy) are read at the first weekly run after the merge, numpy 2.5.4 under each"

[[claim]]
spec = "166"
new = [
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pandas-slow-b-no-mmap]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pandas-slow-b-wasm32-int32]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-datasets-pandas-categories]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[statsmodels-graphics-to-multivariate-factor_rotation-pandas-inplace-deprecated]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[statsmodels-tsa-statespace-1-pandas-inplace-deprecated]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[statsmodels-tsa-statespace-2-pandas-inplace-deprecated]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[xarray-r-rest-pandas-multiindex-sel]",
]
changed = [
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[jinja2-r-no-asyncio-loop]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[jinja2-r-no-asyncio-loop-error]",
]
passes = [
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pandas-slow-a]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pandas-slow-b]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[scikit-learn-datasets]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[statsmodels-graphics-to-multivariate-factor_rotation]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[statsmodels-tsa-statespace-1]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[statsmodels-tsa-statespace-2]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[xarray-r-rest]",
]
fewer = "pandas 3.1.0, the second pull request: pandas-slow-a 2,259 -> 2,256 and pandas-slow-b 28 -> 26. 3.1.0 drops the slow mark from test_where_inplace_casting, test_unstack_number_of_levels_larger_than_int32_warns, test_pivot_number_of_levels_larger_than_int32_warns and test_isocalendar, so their six nodes move to the normal groups; beyond the owner's 41, slow-b's three test_categorical_dtype_high_cardinality_numeric cases ([c_high], [c_low], [python]), which 3.1.0 rewrote, fail as its wasm32-int32 class says, numpy's 32-bit default integer confirmed in the guest (the test's expected categories take numpy's 32-bit default integer; read_csv's int64 categories are native's); four new parallel-read tests pass. Known upstream failures the owner accepted on 2026-10-31 with pandas 3.1.0, the same natively: scikit-learn-datasets 356 -> 329 (27 openml tests: pandas 3.1.0 infers numeric categories, which scikit-learn 1.9.1's ARFF parser passes to re.search; class pandas-categories, closed by scikit-learn's next release), and statsmodels' graphics-to-multivariate-factor_rotation 423 -> 422, tsa-statespace-1 1,049 -> 1,037 and tsa-statespace-2 591 -> 590 (14 tests: pandas 3.1.0's Pandas4Warning on the inplace keyword statsmodels 0.15.0 passes; class pandas-inplace-deprecated, closed by statsmodels' next release). The 42nd, accepted by the owner on 2026-10-31 after xarray reached dev: xarray-r-rest loses one pass, xarray/tests/test_indexes.py::TestPandasMultiIndex::test_sel (pandas 3.1.0's MultiIndex.get_loc raises KeyError for a key longer than the index's depth where xarray 2026.9.0's test expects its own error; the same natively; class pandas-multiindex-sel, closed by xarray's next release)"
[claim.judge]
"tests/upstream/expected/jinja2-r/no-asyncio-loop.txt" = "CPython 3.15.2 (166's first pull request) collects the stray event loops of jinja2's async tests at other moments: four tests join the failed class (two that errored at teardown, two that see an earlier test's loop) and two leave it, passing; 106 members, jinja2-r's pass count unchanged; the weekly-shape run 41201012715 (shard upstream-release-039) saw it"
"tests/upstream/expected/jinja2-r/no-asyncio-loop-error.txt" = "the same trade: two tests join the teardown-error class and two leave it for the failed class; 13 members"
"tests/upstream/xarray.toml" = "a new class, pandas-multiindex-sel, in xarray-r-rest: test_sel fails on pandas 3.1.0, natively too, the 42nd test the owner accepted on 2026-10-31; fails-natively's reason names pandas 3.1.0, under which the test still fails natively"
"tests/upstream/expected/xarray-r-rest/pandas-multiindex-sel.txt" = "the class's one member, TestPandasMultiIndex::test_sel"
"tests/known_gaps.toml" = "jinja2-r-no-asyncio-loop counts 106 findings and jinja2-r-no-asyncio-loop-error 13, their digests following the trade; xarray-r-rest-pandas-multiindex-sel is a new gap of 1 finding, closed by xarray's next release; xarray-r-dataset-fails-natively's reason names pandas 3.1.0"
```

`167-pdfplumber-plotly-xarray-and-zstd.toml`:

```toml
[[claim]]
spec = "167"
new = [
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pdfplumber-r]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pdfminer-six-r]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[xarray-r-dataarray]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[xarray-r-rolling]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[xarray-r-backends]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[xarray-r-dataset]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[xarray-r-plot]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[xarray-r-arrays]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[xarray-r-coding]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[xarray-r-rest]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pdfplumber-r-no-processes]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pdfplumber-r-no-pypdfium2]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pdfplumber-r-no-pypdfium2-in-a-test]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pdfplumber-r-no-ghostscript]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pdfminer-six-r-no-cryptography]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pdfminer-six-r-no-cjk-cmaps]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[xarray-r-backends-no-mmap]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[xarray-r-rest-no-mmap]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[xarray-r-backends-no-threads]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[xarray-r-arrays-no-asyncio-loop-error]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[xarray-r-rest-no-asyncio-loop-error]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[xarray-r-coding-wasm32-int32]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[xarray-r-dataset-wasm32-int32]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[xarray-r-rest-wasm32-int32]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[xarray-r-dataset-fails-natively]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[xarray-r-rest-staged-tests-folder]",
]
grows = ["tests/checks/test_v1_3_upstream_suites.py::*"]
growth = "pdfplumber 0.11.10, pdfminer.six 20260107 and xarray 2026.9.0 join the zip, 185 members, so every guest's zip directory is larger: a plain start +1.68% and a snapshot start +0.77% in fuel (darwin arm64). Their release groups measure pdfplumber-r 171.5 G (104 passes), pdfminer-six-r 86.9 G (184 passes) and xarray's eight 1,536.7 G (7,712 passes) on darwin arm64; the failures fall in sixteen classes, each named in its family's TOML"

[[claim]]
spec = "167"
new = [
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[plotly-r]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[plotly-r-read-only-source]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[plotly-r-no-anywidget]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[plotly-r-no-scikit-image]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[plotly-r-no-ipython]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[plotly-r-no-polars-pyarrow]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[plotly-r-no-requests]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[plotly-r-wasm32-maxsize]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[plotly-r-fails-natively-in-one-session]",
]
grows = ["tests/checks/test_v1_3_upstream_suites.py::*"]
growth = "plotly 7.1.0 joins the zip, 1,529 members: on top of 175 and 176's directory read by folder, a plain start +0.21% and a snapshot start +2.11% in fuel (darwin arm64). Its release group, plotly-r, measures 214.8 G with 2,062 passes on darwin arm64; its 36 failures fall in eight classes, each named in its TOML"
```

`169-zstd-built-in.toml`:

```toml
[[claim]]
spec = "169"
passes = ["tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-release-archives]"]
grows = ["tests/checks/test_v1_3_upstream_suites.py::*"]
growth = "libzstd 1.5.7 is linked into _zstd, so test_zipimport's two Zstandard ZIP64 tests, which want the largefile resource, run in cpython-release-archives: 4 to 6 passes, 99.7 G to 248.9 G measured on darwin arm64, its cap 150 G to 380 G. Every other release group grows a little: shutil, tempfile and zipfile now import _zstd, compression.zstd and _zstdfile at module top, and every guest that runs a group imports shutil (pytest's pathlib, capture and tmpdir, or regrtest), about 10.4 M more fuel a guest (import shutil 410.0 M to 420.4 M on python.wasm, darwin arm64)"
```

`170-pillow-reads-and-writes-jpeg.toml`:

```toml
[[claim]]
spec = "170"
new = [
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pypdf-r-pillow-no-jpeg2k-or-tiff]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[openpyxl-r-pillow-no-jpeg2k-or-tiff]",
]
retired = [
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pypdf-r-pillow-zlib-only]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[openpyxl-r-pillow-zlib-only]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-datasets-pillow-zlib-only-at-setup]",
]
passes = [
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pypdf-r]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[scikit-learn-datasets]",
]
grows = [
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[scikit-learn-datasets]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pypdf-r]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[openpyxl-r]",
]
growth = "Pillow gains JPEG through libjpeg-turbo 3.2.0, and python.wasm grows by 520,394 bytes. Measured on darwin arm64: scikit-learn-datasets 65.6 G (Linux) to 90.9 G with 360 passes (356): the faces dataset's JPEG fixtures now write, so its four tests run, and its cap moves to 140 G by the 1.5 rule; pypdf-r 1,703 passes (1,695 after 166), eight JPEG tests passing, 358.8 G; openpyxl-r 63.2 G (+0.1%), its pass count the same"
```

`171-the-packages-a-set-carries.toml`:

```toml
[[claim]]
spec = "171"
grows = ["tests/checks/test_v1_3_upstream_suites.py::*"]
growth = "each distribution's .dist-info gains its top_level.txt, 58 members after 167, so every guest's zip directory is larger: a plain start 282,492,922 to 283,900,438 fuel (+0.50%) and a snapshot start 54,644,143 to 54,695,369 (+0.09%), measured on darwin arm64 against dev's set at a750e8fe"
```

`174-svg-to-png-through-cairo.toml`:

```toml
[[claim]]
spec = "174"
new = [
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cairocffi-r]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[imageio-r]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[cairocffi-r-no-ctypes-address]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[imageio-r-no-ctypes]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[imageio-r-no-processes]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[imageio-r-fails-natively]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[imageio-r-wasi-platform]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[imageio-r-legacy-tifffile]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[imageio-r-importlib-module-names]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[imageio-r-no-ctypes-warning]",
]
grows = ["tests/checks/test_v1_3_upstream_suites.py::*"]
growth = "cairo and cairocffi's bindings are linked in and cairocffi, CairoSVG, tinycss2, cssselect2 and imageio join the zip, 119 members, so every guest's zip directory is larger: a plain start +0.99% and a snapshot start +0.49% in fuel (darwin arm64). Their release groups measure cairocffi-r 11.1 G and imageio-r 295.1 G (106 passes) on darwin arm64; the failures fall in eight classes, each named in its family's TOML"
```

`176-the-end-of-a-call-frees-nothing.toml`:

```toml
[[claim]]
spec = "176"
grows = ["tests/checks/test_v1_3_upstream_suites.py::*"]
growth = "175 reads the stdlib zip by folder on the plain binary and keeps its dict past teardown, and 176 keeps teardown's freed blocks within a 1 MiB budget, so most calls end on less fuel; but the link now wraps the C library's allocators, and every allocation of every call checks one flag. Measured on darwin arm64 against 175's set, calls ended by os._exit(0): a bare call +0.36% (plain) and +0.61% (snapshot), a pandas groupby +0.20% and +0.23%; each whole call, teardown included, still uses less fuel than before (a pandas groupby 4,766,096,475 to 4,730,329,497 on the snapshot). A release group that allocates much and finalizes little grows by up to the wrappers' cost"
```

## 0.1.2

Moved by `release/version.py date` on 2026-10-29, before the release pull request.

```toml
[[claim]]
spec = "157"
grows = ["tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[*"]
growth = "the reactor gains the export `prepare`, a prepared instance's ending and five reseeds in `_refresh`, so both binaries are larger and every run unmarshals and refreshes a little more"
[claim.judge]
"context/release-tier-claims.toml" = "this block: the reason the upstream suites' fuel grows with 157's new reactor code, for the release pull request's acceptance"
```

## 0.1.1

Moved by `release/version.py date` on 2026-10-27, before the release pull request.

No block was in the ledger at the date.

One block was appended after the date, by 127's landing documents (`607b2d79`, pull request #25): it named every upstream suite's dropped fuel as a growth, since the move to wasmtime 50.0.1 left the release-tier groups, which run on Linux alone in CI, no fuel of the new engine. The release pull request's acceptance (`898bc091`) read it as its one growth reason. 154 removed it from the ledger before 0.1.2's date, since the acceptance from CI's record now records Linux's fuel, labelled, for a check only Linux ran when no fuel darwin measured under the current engine is accepted, so an engine move drops no such row's fuel; left in the ledger, the date would have moved it under 0.1.2, where its prefix would clear a real fuel growth. It is quoted here in a `text` fence, which the release's claims do not read:

```text
[[claim]]
spec = "127"
grows = ["tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[*"]
growth = "the upstream suites' fuel was last measured on darwin under wasmtime 49.0.0, and 127 moved the engine to 50.0.1; in CI the upstream groups run on Linux alone, whose fuel is not ratcheted, so the acceptance keeps no fuel of the other engine for these rows until a darwin run of the release tier measures them again"
[claim.judge]
"context/release-tier-claims.toml" = "this block: the reason the upstream suites' fuel measured under wasmtime 49 is dropped at the first release-tier acceptance since 127 moved the engine"
```

## 0.1.0

Moved at the release acceptance on `eac93d0f` (history line 94, accepted in `1aa0eff7`), the first release acceptance: 102, 114, 095 and 067.

```toml
[[claim]]
spec = "102"
new = [
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[numpy-slow-*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pandas-slow-*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-release-*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[contourpy-slow-rest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pandas-slow-b-no-threads]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[cpython-release-a-stdlib-zip-error]",
]
changed = [
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[contourpy-filled-*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[contourpy-lines-*",
]
passes = []
grows = [
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-fs]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-a]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-b]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-c]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[contourpy-1]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[contourpy-rest]",
]
growth = "102: the regrtest driver's Z line (it names a module's denied resource) moves every CPython group's fuel on this set, EXECUTED on d0d91cef: cpython-fs +43.8 M (+6.9e-4), cpython-a +43.3 M (+1.56e-4), cpython-b +53.0 M (+1.79e-4), cpython-c +73.8 M (+1.77e-4); the thirteen staged release JSONs cost nothing (cpython-fs and cpython-b equal to the instruction with them staged and the base's driver); contourpy's normal groups run -m 'not slow' (contourpy-1 +0.28%, contourpy-rest +3.7e-4; the survey, on 142bdd38)"
retired = []
units = 113  # 112 before wave 11's integration review, L1, counted 113 per file

[[claim]]
spec = "114"
growth = "114: the zip's two members move every release-tier group's fuel both ways; passes unchanged"

[[claim]]
spec = "095"
# 261 release groups, their classes and three traps, all new: scipy 172 groups (63.66 T),
# scikit-learn 38 (9.72 T), statsmodels 51 (12.84 T), 86.22 T measured on darwin-arm64 by node id
# with --tier release (the build's passes 1 to 4, sets d0d91cef and 1556bbd5); the four smoke
# groups are normal-tier rows, not claimed here
new = [
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[scipy-*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[scikit-learn-*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[statsmodels-*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[statsmodels-*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_trap[scipy-hypothesis-*",
]
changed = []
passes = []
grows = []
retired = []
units = 46  # tests/unit: 2,290 collected against main's 2,244

[[claim]]
spec = "067"
# 419 release groups of 23 families, their classes and seven traps, all new: 95.32 T measured
# on darwin-arm64 by node id with --tier release (sympy 80.92 T in 342 groups, the other 22
# families 14.40 T; sets d0d91cef and 1556bbd5, the judging set's MANIFEST with this
# specification's pins and patches), and the seven traps at 50 G each; the 42 smoke groups are
# normal-tier rows, not claimed here
new = [
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[fonttools-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pyparsing-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[packaging-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[python-dateutil-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[openpyxl-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[xlsxwriter-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pypdf-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[beautifulsoup4-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[soupsieve-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[jinja2-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[charset-normalizer-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[networkx-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[patsy-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[sympy-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[mpmath-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[attrs-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[more-itertools-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[joblib-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cloudpickle-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[narwhals-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[seaborn-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[reportlab-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[formulaic-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[sympy-slow-17141]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[fonttools-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pyparsing-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[python-dateutil-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[openpyxl-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pypdf-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[soupsieve-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[jinja2-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[charset-normalizer-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[networkx-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[mpmath-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[more-itertools-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[joblib-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[cloudpickle-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[narwhals-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[seaborn-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[reportlab-r*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_trap[sympy-slow-*",
]
changed = []
passes = []
grows = [
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[contourpy-filled-*",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[contourpy-lines-*",
]
growth = "067: the package driver moves every package-driver group's fuel both ways; passes unchanged (the wave 12 integration review's M1 and L3)"
retired = []
units = 37  # tests/unit/test_pure_suites.py, a new file: 36 collected; tests/unit/test_fetch_trees.py: 1 more
```

Moved at the second release acceptance of 0.1.0, on `d33f0383` (history line 97; the record's SHA-256 `bed3e5f204f4a8dc0fe3aef361621bfa607c3665ba1f9575d5ee9f7bc64fd9ec`), compared with the record of the first (`8a26e68c`, SHA-256 `ecb68db9acfc5ca5c298cf461c65779ac4e00e8f6041a34f17459ac8692850b3`): 067 and 122. 122's 162 closer changes explained every difference; 067's two entries were already in the first record.

```toml
[[claim]]
spec = "067"
# After 0.1.0's release acceptance: networkx's test_asadpour_integral_held_karp leaves
# networkx-r-approximation-1 for a trap of its own: on Linux x86_64 it did not end within its
# group's 710 G cap (dry run 39741960669), against about 442 to 470 G on darwin-arm64, on the
# same artifact set and wasmtime, so the guest takes a different path on Linux, which may be the
# product's. The group runs its other 44 tests in 100,156,534,716 fuel (EXECUTED): one accepted
# pass fewer, by this reason, and less fuel.
new = [
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_trap[networkx-r-trap-asadpour-integral-held-karp]",
]
changed = []
passes = [
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[networkx-r-approximation-1]",
]
grows = []
retired = []
units = 0

[[claim]]
spec = "122"
# The short README: the limitations it listed moved to docs/reference/limitations.md, and every
# known gap that named README.md as its closer names that page instead. A release-tier row changes
# its closer only; its status, need, area, facts and metrics are the same. Written by the lane at
# the release acceptance on d33f0383, where the comparison found these 162 rows and no other
# difference; 122 landed without its block.
new = []
changed = [
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[charset-normalizer-r-cli-writes-beside-input]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[charset-normalizer-r-no-threads]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[cloudpickle-r-captured-stdout]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[cloudpickle-r-no-processes]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[cpython-release-a-stdlib-zip-error]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[fonttools-r-doc-doctest-output]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[fonttools-r-rest-counted-clock]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[fonttools-r-rest-importlib-module-names]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[fonttools-r-rest-no-processes]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[fonttools-r-rest-read-only-source]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[fonttools-r-rest-sdist-lacks-data]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[fonttools-r-rest-zip-no-source]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[fonttools-r-ttlib-no-processes]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[jinja2-r-importlib-module-names]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[jinja2-r-no-asyncio-loop-error]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[jinja2-r-no-asyncio-loop]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[jinja2-r-read-only-source]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[jinja2-r-zip-package-loader]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[joblib-r-doc-doctest-output]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[joblib-r-joblib-cache-clock]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[joblib-r-no-asyncio-loop-error]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[joblib-r-no-asyncio-loop]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[joblib-r-no-mmap]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[joblib-r-no-processes]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[more-itertools-r-counted-clock]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[more-itertools-r-doc-doctest-output]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[more-itertools-r-no-threads]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[mpmath-r-doc-functions-2-doctest-output]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[mpmath-r-doc-libmp-doctest-output]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[mpmath-r-doc-matrices-doctest-output]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[narwhals-r-no-ctypes]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[narwhals-r-no-mmap]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[narwhals-r-no-terminal-size]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[narwhals-r-wasm32-int32]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[networkx-r-doc-doctest-output]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[networkx-r-other-no-threads]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[networkx-r-root-1-counted-clock]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[openpyxl-r-openpyxl-lxml-only]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[openpyxl-r-read-only-source]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pandas-slow-b-no-threads]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pyparsing-r-pyparsing-no-railroad]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pyparsing-r-unit-6-no-processes]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pypdf-r-no-processes]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[python-dateutil-r-no-tzset]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[python-dateutil-r-tz-cache]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[reportlab-r-importlib-module-names]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[reportlab-r-pytest-collects-helper-error]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[reportlab-r-reportlab-data-folder]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[reportlab-r-reportlab-no-accel]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[reportlab-r-reportlab-reference-attributes]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[reportlab-r-reportlab-tools-not-shipped]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-datasets-pillow-zlib-only-at-setup]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-decomposition-1-no-mmap]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-linear_model-1-no-mmap]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-linear_model-3-no-dev-null]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-linear_model-3-no-mmap]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-loss-to-cross_decomposition-no-mmap]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-metrics-no-mmap-at-setup]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-model_selection-3-no-mmap]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-neighbors-to-neural_network-no-mmap]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-preprocessing-to-semi_supervised-wasm32-int128]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-tests-1-1-no-openmp]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-tests-1-1-package-in-zip]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-tests-common-1-no-mmap]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-tests-common-2-no-mmap]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-tests-common-3-no-mmap]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-tests-common-4-no-mmap]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-tree-no-mmap]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-utils-no-mmap-estimator-checks]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scikit-learn-utils-no-mmap]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-integrate-1-no-processes]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-interpolate-1-no-native-id-test-names]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-interpolate-1-no-threads]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-interpolate-2-no-threads]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-interpolate-fitpack2-1-no-threads]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-io-harwell_boeing-to-io-enotsup-io-file-left-open-at-setup]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-io-harwell_boeing-to-io-enotsup-io-no-warning]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-io-harwell_boeing-to-io-enotsup-io]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-io-harwell_boeing-to-io-no-mmap]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-io-harwell_boeing-to-io-no-native-id-test-names]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-io-harwell_boeing-to-io-wasm32-memory]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-lib-to-fft-no-native-id-uarray]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-lib-to-fft-no-processes]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-ndimage-to-optimize-trustregion_constr-no-threads]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-optimize-1-1-no-processes]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-optimize-1-2-no-processes]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-optimize-2-no-fp-exceptions]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-optimize-3-no-processes]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-optimize-3-no-threads]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-signal-float32-rounding]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-signal-signaltools-no-threads]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-smoke-slow-9-no-threads]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-smoke-slow-9-wasm32-memory]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-sparse-1-no-fp-exceptions]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-sparse-csgraph-to-sparse-linalg-eigen-no-threads]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-spatial-no-threads]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-special-2-no-fp-exceptions]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-special-mpmath-10-mpmath-tolerance]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-special-mpmath-2-mpmath-tolerance]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-special-mpmath-37-mpmath-tolerance]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-special-mpmath-6-mpmath-tolerance]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-stats-1-mgc-3-no-processes]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-stats-1-stats-5-no-fp-exceptions]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-stats-fit-1-fit-flat-likelihood]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[scipy-stats-fit-2-no-fp-exceptions]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[seaborn-r-1-newer-dependencies]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[seaborn-r-1-no-pyarrow-interchange]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[seaborn-r-3-no-pyarrow-interchange]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[seaborn-r-5-newer-dependencies]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[seaborn-r-5c-newer-dependencies]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[seaborn-r-6-newer-dependencies]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[seaborn-r-8-newer-dependencies]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[soupsieve-r-no-alarm]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[statsmodels-base-to-datasets-left-out-datasets]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[statsmodels-base-to-datasets-wasm-is-not-emscripten]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[statsmodels-discrete-discrete-1-left-out-datasets-at-setup]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[statsmodels-discrete-discrete-1-left-out-datasets]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[statsmodels-discrete-discrete-2-left-out-datasets]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[statsmodels-emplike-left-out-datasets-at-setup]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[statsmodels-emplike-left-out-datasets]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[statsmodels-genmod-left-out-datasets-at-setup]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[statsmodels-genmod-left-out-datasets]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[statsmodels-graphics-to-multivariate-factor_rotation-left-out-datasets]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[statsmodels-graphics-to-multivariate-factor_rotation-no-processes]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[statsmodels-stats-4-upstream-xfail-platform]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[statsmodels-tests-to-treatment-left-out-datasets-at-setup]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-doc-1-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-doc-10-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-doc-11-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-doc-15-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-doc-2-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-doc-3-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-doc-6-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-doc-7-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-doc-8-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-docfiles-1-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-docfiles-2-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-docfiles-3-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-docfiles-4-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-docfiles-5-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-docfiles-6-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-docfiles-7-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-docfiles-8-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-docfiles-8b-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-docfiles-9-sympy-doctest]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-polys-2-s11-1-sympy-tooslow-fails]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-polys-4-s1-1-sympy-tooslow-fails]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-solvers-7-5a-sympy-solution-form]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-solvers-7-5b-sympy-solution-form]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-testing-1-sympy-source-tree]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[sympy-r-utilities-4-no-path-variable]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_trap[networkx-r-trap-asadpour-integral-held-karp]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_trap[scipy-hypothesis-hyp1f1]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_trap[scipy-hypothesis-lpmv]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_trap[scipy-hypothesis-yn]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_trap[sympy-slow-W25]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_trap[sympy-slow-function-range1]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_trap[sympy-slow-issue-15227]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_trap[sympy-slow-issue-3880]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_trap[sympy-slow-linear-new-order1-type2-de-lorentz-slow-check]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_trap[sympy-slow-nonlinear-3eq-order1-type1]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_trap[sympy-slow-nonlinear-3eq-order1-type3]",
]
passes = []
grows = []
retired = []
units = 0
```
