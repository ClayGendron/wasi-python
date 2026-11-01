# 167: pdfplumber, plotly, xarray and zstd

## Changelog

### New

- **Tables and text from PDF files.** pdfplumber 0.11.10 with pdfminer.six 20260107 is in the zip: each page's text, its words with their positions, its ruling lines and `extract_tables()`, and files encrypted with RC4. AES needs `cryptography` and page images need pypdfium2, which the set does not carry; each raises `ModuleNotFoundError` naming it. [Packages](https://claygendron.github.io/wasi-python/reference/packages/)
- **Labelled arrays.** xarray 2026.9.0 is in the zip: named dimensions, alignment on labels, `groupby`, `rolling`, `resample`, interpolation through scipy, pandas round trips, the HTML view, and netCDF3 files through scipy. Its other file engines and its tutorial data are not carried. [Packages](https://claygendron.github.io/wasi-python/reference/packages/)
- **Interactive plotly figures.** plotly 7.1.0 is in the zip: graph objects and plotly express, its datasets, JSON, and HTML pages that carry plotly.js or load it from plotly's CDN. Static images need kaleido, which cannot run here, and `FigureWidget` needs a notebook; both raise. [Packages](https://claygendron.github.io/wasi-python/reference/packages/)

### For contributors

- **A carried patch lets pdfminer.six start without cryptography.** `recipes/patches/pdfminer_six-20260107/0001-import-cryptography-where-aes-runs.patch` moves pdfminer's two `cryptography` imports into the one helper its AES paths call, so plain and RC4 files read without it. [Carrying a patch](https://claygendron.github.io/wasi-python/contributing/carrying-a-patch/)
- **A carried patch lets plotly read its data from the zip.** `recipes/patches/plotly-7.1.0/0001-data-as-package-data.patch` reads the validators' table and the datasets through the package's loader, as plotly already reads plotly.js. [Carrying a patch](https://claygendron.github.io/wasi-python/contributing/carrying-a-patch/)
- **The wheel's size is checked against PyPI's file limit.** The artifact rules refuse a wheel over 104,857,600 bytes (100 MiB), PyPI's limit until it raises the project's, on every run that builds one, so no tag makes a GitHub release whose wheel PyPI would refuse. [Release process](https://claygendron.github.io/wasi-python/contributing/release-process/)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "167"
new = [
  "tests/checks/test_v1_3_default_profile.py::test_plotly_figures_job_matches_native",
  "tests/checks/test_v1_3_default_profile.py::test_plotly_reads_its_data_from_the_zip*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[plotly-smoke]",
  "tests/checks/test_v1_5_rebuild_from_pins.py::test_source_tree_matches_its_tarball[plotly]",
]
grows = ["tests/checks/*"]
growth = "plotly 7.1.0 joins the zip: 1,529 members (1,507 of plotly, 20 of _plotly_utils, its METADATA and top_level.txt), without its JupyterLab extension and widget script. Measured on darwin arm64 against dev's set at 4d199003, where a plain start reads the zip's directory by folder (175 and 176): the zip 58,380,379 to 65,464,893 bytes (+7,084,514, +12.1%), 6,860 to 8,389 members; python-snapshot.wasm 108,918,607 to 109,648,301 (+729,694), the zip's directory being in the image; a plain start (-c pass) 135,069,500 to 135,356,448 fuel (+286,948, +0.21%) and a snapshot start 35,257,807 to 36,000,887 (+743,080, +2.11%); the wheel, built by hand as the release workflow builds it, 105,156,248 to 112,145,034 bytes (+6,988,786), under the 268,435,456 the wheel's check allows"
units = 0
[claim.judge]
"tests/upstream/plotly.toml" = "plotly's own suite, from its 7.1.0 release tag (its sdist holds no tests), with pytz as a test-only wheel and the writable /tmp/work as its working folder: a smoke group in the normal tier (11.5 G measured, 17 G cap) and the whole suite in the release tier (214.8 G, 322 G cap), less three not-selected parts (test_px, whose conftest imports polars and pyarrow; the kaleido tests; the renderers' tests, which need requests, a browser and a server), with eight classes: a read-only source, no anywidget, no scikit-image, no IPython, no polars or pyarrow, no requests, sys.maxsize's 32 bits, and a test that fails natively when run in one session with test_colors.py"
"tests/upstream/packages.toml" = "plotly names its own suite"
"tests/known_gaps.toml" = "plotly's eight classes' gaps, by their findings' digests"
"tests/release_shards.toml" = "plotly-smoke joins upstream-pure-smoke-b; plotly-r joins upstream-release-067, its minutes 9.5 estimated from the fuel"
"context/release-claims/167-pdfplumber-plotly-xarray-and-zstd.toml" = "167's plotly block: plotly-r and its eight classes are new"
"tests/upstream/expected/plotly-r/fails-natively-in-one-session.txt" = "the members of the class plotly-r-fails-natively-in-one-session"
"tests/upstream/expected/plotly-r/no-anywidget.txt" = "the members of the class plotly-r-no-anywidget"
"tests/upstream/expected/plotly-r/no-ipython.txt" = "the members of the class plotly-r-no-ipython"
"tests/upstream/expected/plotly-r/no-polars-pyarrow.txt" = "the members of the class plotly-r-no-polars-pyarrow"
"tests/upstream/expected/plotly-r/no-requests.txt" = "the members of the class plotly-r-no-requests"
"tests/upstream/expected/plotly-r/no-scikit-image.txt" = "the members of the class plotly-r-no-scikit-image"
"tests/upstream/expected/plotly-r/read-only-source.txt" = "the members of the class plotly-r-read-only-source"
"tests/upstream/expected/plotly-r/wasm32-maxsize.txt" = "the members of the class plotly-r-wasm32-maxsize"
```
