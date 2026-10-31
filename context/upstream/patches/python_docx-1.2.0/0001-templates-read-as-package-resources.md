- **Project:** python-docx (https://github.com/python-openxml/python-docx)
- **Against:** 1.2.0 (the pinned sdist, `python_docx-1.2.0.tar.gz`)
- **Status:** drafted
- **Title:** Read the default templates through the package's loader, so `Document()` works from a zip
- **Files:** src/docx/api.py, src/docx/parts/comments.py, src/docx/parts/hdrftr.py, src/docx/parts/settings.py, src/docx/parts/styles.py
- **Why we carry it:** the guest imports python-docx from the stdlib zip, so a path made from `__file__` names no file: `docx.Document()` raises `PackageNotFoundError`, and a document that lacks a settings, styles, comments, header or footer part cannot get one.

The patch is `recipes/patches/python_docx-1.2.0/0001-templates-read-as-package-resources.patch`, written by specification 165's build (2026-10-31). The owner sends this, or not; nothing has been posted, and no agent will post anything to python-docx.

## What the project asks of a contributor

Read 2026-10-31 (GitHub's contents API, `master`): the repository has no `CONTRIBUTING` file, no `.github` folder and no `AGENTS.md`, and its README and its documentation's "Contributor Guide" (`docs/dev/analysis/`, feature analyses) state no rule for issues or pull requests, and nothing about AI tools. So the text below is written as a pull request. It says that an AI tool wrote the change, which is the honest default.

## Related reports

Searched 2026-10-31 (GitHub's issue search on `python-openxml/python-docx`: "default.docx zip", "PackageNotFoundError default", "templates frozen", "pkgutil", "importlib.resources"). No open issue or pull request is about this defect. The closed ones on the same cause:

- #176, "Can't find default.docx when frozen (templates in library.zip)" (opened 2015, closed 2026-05-14);
- #735, "Add 'zip_safe' == False to setup.py" (closed unmerged, 2021): a zipped egg raised `PackageNotFoundError` from `Document()`;
- #289 and #654, `Document()` failing in a PyInstaller or cx_Freeze executable.

The defect is still on `master` (read 2026-10-31: `src/docx/api.py` lines 36-37 and both sites of `parts/hdrftr.py` build the path from `__file__`). A pull request could refer to #176.

## The pull request

**Title:** Read the default templates through the package's loader, so `Document()` works from a zip

`Document()` with no argument, and five parts that a document may lack (settings, styles, comments, header, footer), read their default template by a path built from `__file__`. When python-docx is imported from a zip archive (a wheel on `sys.path`, a zipped egg, a frozen application's `library.zip`, an embedded interpreter's stdlib zip), that path is inside the archive and names no file, so `Document()` raises `PackageNotFoundError` and the parts raise `NotADirectoryError` or `FileNotFoundError`.

Reproduction, with the released wheel itself on the path (a wheel is a zip that `zipimport` reads):

```
PYTHONPATH=python_docx-1.2.0-py3-none-any.whl python -c "import docx; docx.Document()"
docx.opc.exceptions.PackageNotFoundError: Package not found at '.../python_docx-1.2.0-py3-none-any.whl/docx/templates/default.docx'
```

The change reads each template with `pkgutil.get_data("docx", "templates/<name>")`, which goes through the package's loader: a file from a folder, a member from a zip. It works on every Python the project supports. Six sites change:

- `docx/api.py`, `_default_docx_path()`: returns an `io.BytesIO` of `default.docx` instead of its path. `Package.open` already takes a file-like object. The name is kept so the diff stays small; `_default_docx_stream` would say it better, and the patch can rename it if you prefer.
- `docx/parts/settings.py`, `styles.py`, `comments.py`, and `hdrftr.py` (footer and header): each `_default_*_xml()` returns the same bytes as before, read by `pkgutil.get_data` instead of `open`.

Each `get_data` result is cast to `bytes` for pyright's strict mode (`get_data` is typed `bytes | None`; it returns `None` only for a loader without `get_data`, which a package with files does not have). `os` is no longer imported by these modules.

Nothing a user sees changes when python-docx is installed as files: the same bytes are read, and the documents written are the same. The existing tests pass unchanged: `tests/test_api.py` mocks `_default_docx_path`, and the part tests compare the bytes each `_default_*_xml()` returns.

**Tested** on CPython 3.15.2 and 3.11.14 (macOS, arm64) with lxml 6.1.3: the project's own suite, 1,609 passed before and after the change, on each Python. From a zip of the patched package, `Document()` returns a document; from a zip of the released one it raises as above. The change was written with an AI tool (Claude Code, Claude Opus 5.5), and every line was read and run as described here.

## The evidence

Every figure here is EXECUTED on 2026-10-31 in specification 165's build (`context/specifications/165-python-docx-and-python-pptx.md`, landing notes):

- the native suites, stock and patched, on both Pythons: `pytest tests` with `src` on the path, 1,609 passed each;
- the reproduction from the released wheel on 3.15.2 and 3.11.14: `PackageNotFoundError`;
- from a zip of the patched package: `Document()` and every `_default_*_xml()` return the template's bytes;
- in this project's guest (CPython 3.15.2 for `wasm32-wasip1`, python-docx in its stdlib zip): `test_office_templates_read_from_the_zip` hashes each site's result and finds the zip member's bytes; on a set built from the stock sdist it fails, each site raising `NotADirectoryError` and `Document()` raising `PackageNotFoundError`.
