- **Project:** plotly.py (https://github.com/plotly/plotly.py)
- **Against:** 7.1.0 (the pinned sdist, `plotly-7.1.0.tar.gz`)
- **Status:** drafted
- **Title:** Read the validators' table and the datasets through the package's loader, so plotly works from a zip
- **Files:** plotly/validator_cache.py, plotly/data/__init__.py
- **Why we carry it:** the guest imports plotly from the stdlib zip, so a path built from `__file__` names no file: every figure fails with "Validator JSON file not found", and `px.data.iris()` and the other datasets, and `px.data.election_geojson()`, raise `NotADirectoryError`.

The patch is `recipes/patches/plotly-7.1.0/0001-data-as-package-data.patch`, written by specification 167's plotly pull request (2026-10-31). The owner sends this, or not; nothing has been posted, and no agent will post anything to plotly.py.

## What the project asks of a contributor

Read 2026-10-31 from the 7.1.0 tag's `CONTRIBUTING.md`: report a bug as an issue after checking for an existing one; a pull request works on a branch, changes the code generator rather than generated files (neither file here is generated: `codegen/` only imports `plotly.validator_cache`), passes `ruff`, and adds a `CHANGELOG.md` entry (the "Check changelog" job enforces it). It says nothing about AI tools. So the route is an issue, then the pull request below, which says that an AI tool wrote the change, the honest default.

## Related reports

Searched 2026-10-31 (`gh search issues --repo plotly/plotly.py "zip validators _validators.json"`): no issue. `plotly.offline` and `plotly.io._templates` already read `plotly.min.js` and the templates with `pkgutil.get_data`, so the change follows the package's own pattern.

## The pull request

**Title:** Read the validators' table and the datasets with `pkgutil.get_data`, so plotly works from a zip archive

`ValidatorCache.get_validator` opens `validators/_validators.json` by a path built from `__file__`, and `plotly.data`'s `election_geojson()` and `_get_dataset()` open `package_data/datasets/*.gz` the same way. When plotly is imported from a zip archive (a wheel on `sys.path`, a frozen application's archive, an embedded interpreter's stdlib zip), those paths are inside the archive and name no file, so building any figure raises `FileNotFoundError: Validator JSON file not found` and every dataset raises `NotADirectoryError`.

Reproduction, with the released wheel itself on the path:

```
PYTHONPATH=plotly-7.1.0-py3-none-any.whl python -c "import plotly.graph_objects as go; go.Figure(go.Scatter(x=[1], y=[2]))"
FileNotFoundError: Validator JSON file not found: .../plotly-7.1.0-py3-none-any.whl/plotly/validators/_validators.json
```

The change reads each file with `pkgutil.get_data("plotly", ...)`, which goes through the package's loader (a file from a folder, a member from a zip), as `plotly.offline` already reads `plotly.min.js`. A helper, `_dataset_file(name)`, returns a `gzip.GzipFile` over the bytes, which `election_geojson()` reads and which `_get_dataset()` hands to the backend's `read_csv` (a file object, so pandas, polars and pyarrow all read it; given a buffer, pandas would not infer gzip, hence the explicit `GzipFile`). `os` is no longer imported by either module. Nothing changes when plotly is installed as files: the same bytes are read.

**Tested** on CPython 3.15 (macOS, arm64) with pandas 3.0.6: from a zip of the stock package, `go.Figure(...)`, `px.data.iris()` and `px.data.election_geojson()` fail as above; from a zip of the patched package they return the 150-row iris frame, the 58-feature GeoJSON, and the figure's JSON. The change was written with an AI tool (Claude Code, Claude Opus 5.5), and every line was read and run as described here.

CHANGELOG line: "Fixed: plotly reads its validators' table and its datasets through the package's loader, so it works when imported from a zip archive".

## The evidence

EXECUTED on 2026-10-31 in specification 167's plotly build (`context/specifications/167-pdfplumber-plotly-xarray-and-zstd.md`, landing notes): the stock and patched zips natively, as above; in this project's guest (plotly in its stdlib zip), `test_plotly_figures_job_matches_native` gives native plotly's figures, JSON and HTML, and its datasets.
