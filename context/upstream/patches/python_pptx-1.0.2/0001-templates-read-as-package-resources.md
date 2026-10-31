- **Project:** python-pptx (https://github.com/scanny/python-pptx)
- **Against:** 1.0.2 (the pinned sdist, `python_pptx-1.0.2.tar.gz`)
- **Status:** drafted
- **Title:** Read the default templates through the package's loader, so `Presentation()` works from a zip
- **Files:** src/pptx/api.py, src/pptx/oxml/__init__.py, src/pptx/shapes/shapetree.py, tests/shapes/test_shapetree.py, tests/test_api.py, tests/test_package.py
- **Why we carry it:** the guest imports python-pptx from the stdlib zip, so a path made from `__file__` names no file: `pptx.Presentation()` raises `PackageNotFoundError`, and a notes slide, a theme or an OLE object's default icon cannot be made.

The patch is `recipes/patches/python_pptx-1.0.2/0001-templates-read-as-package-resources.patch`, written by specification 165's build (2026-10-31). The owner sends this, or not; nothing has been posted, and no agent will post anything to python-pptx.

## What the project asks of a contributor

Read 2026-10-31 (GitHub's contents API, `master`): the repository's `.github` folder holds only `workflows`; there is no `CONTRIBUTING` file and no `AGENTS.md`, and the README states no rule for issues or pull requests, and nothing about AI tools. So the text below is written as a pull request. It says that an AI tool wrote the change, which is the honest default. The project's last push was 2024-08-07 (the 1.0.2 release), so a reply may be slow.

## Related reports

Searched 2026-10-31 (GitHub's issue search on `scanny/python-pptx`: "default.pptx zip", "PackageNotFoundError default", "templates frozen", "pkgutil"). No open issue or pull request is about this defect. Near it:

- #804 (open), "Embedding custom pptx template within executable file": a user's own template in a frozen executable, not the package's default;
- #1007 (closed), `PackageNotFoundError` naming `site-packages\pptx\templates\default.pptx`: an install that lacked the file, not a zip.

The defect is still on `master` (read 2026-10-31: `src/pptx/api.py` lines 42-43 build the path from `__file__`).

## The pull request

**Title:** Read the default templates through the package's loader, so `Presentation()` works from a zip

`Presentation()` with no argument, `parse_from_template()` (the theme, the notes master and a notes slide), and an OLE object's default icon read their file by a path built from `__file__`. When python-pptx is imported from a zip archive (a wheel on `sys.path`, a zipped egg, a frozen application's `library.zip`, an embedded interpreter's stdlib zip), that path is inside the archive and names no file, so `Presentation()` raises `PackageNotFoundError` and the other sites raise `NotADirectoryError` or `FileNotFoundError`.

Reproduction, with the released wheel itself on the path (a wheel is a zip that `zipimport` reads):

```
PYTHONPATH=python_pptx-1.0.2-py3-none-any.whl python -c "import pptx; pptx.Presentation()"
pptx.exc.PackageNotFoundError: Package not found at '.../python_pptx-1.0.2-py3-none-any.whl/pptx/templates/default.pptx'
```

The change reads each file with `pkgutil.get_data("pptx", "templates/<name>")`, which goes through the package's loader: a file from a folder, a member from a zip. It works on every Python the project supports, 3.8 included, where `importlib.resources.files` does not exist. Three sites change:

- `pptx/api.py`, `_default_pptx_path()`: returns an `io.BytesIO` of `default.pptx` instead of its path, typed `IO[bytes]`. `Package.open` already takes a file-like object. The name is kept so the diff stays small; `_default_pptx_stream` would say it better, and the patch can rename it if you prefer.
- `pptx/oxml/__init__.py`, `parse_from_template()`: parses the same bytes, read by `pkgutil.get_data` instead of `open`.
- `pptx/shapes/shapetree.py`, `_OleObjectElementCreator._icon_image_file`: for a default icon, returns an `io.BytesIO` of the EMF file instead of its absolute path. A user's `icon_file` passes through unchanged. The image part is made from the same bytes; the only difference is that `Image.from_file` sees a stream, so the part's `filename` is the generic `image.<ext>` instead of the icon's file name; that name reaches no saved XML here, because the OLE element uses only the part's relationship id, so nothing saved changes. One corner: a later `add_picture` of the very same icon bytes reuses that part, so the picture's `descr` reads `image.wmf` instead of the icon's file name.

Each `get_data` result is cast to `bytes` for pyright's strict mode (`get_data` is typed `bytes | None`). `os` is no longer imported by these modules.

Three tests named a template by its path, and change with it:

- `tests/test_api.py`: `Package.open` is called once, with a stream holding `default.pptx`'s bytes;
- `tests/test_package.py`: opens the default template from a stream;
- `tests/shapes/test_shapetree.py`: the icon test splits in two, a user's icon file passed through unchanged, and each default icon read as its template's bytes. The test count is the same.

**Tested** on CPython 3.15.2 and 3.11.14 (macOS, arm64) with lxml 6.1.3, Pillow 13.0.0 and XlsxWriter 3.2.9: the project's own suite, 2,700 passed before and after the change, on each Python. From a zip of the patched package, `Presentation()` returns a presentation, and a notes slide and an OLE object's default icon are made; from a zip of the released one, `Presentation()` raises as above. The change was written with an AI tool (Claude Code, Claude Opus 5.5), and every line was read and run as described here.

## The evidence

Every figure here is EXECUTED on 2026-10-31 in specification 165's build (`context/specifications/165-python-docx-and-python-pptx.md`, landing notes):

- the native suites, stock and patched, on both Pythons: `pytest tests` with `src` on the path, 2,700 passed each;
- the reproduction from the released wheel on 3.15.2 and 3.11.14: `PackageNotFoundError`;
- from a zip of the patched package: `Presentation()`, the three XML templates and the four icons return the template's bytes (`parse_from_template`'s tree serialises as the member's does);
- in this project's guest (CPython 3.15.2 for `wasm32-wasip1`, python-pptx in its stdlib zip): `test_office_templates_read_from_the_zip` hashes each site's result and finds the zip member's bytes; on a set built from the stock sdist it fails, each site raising `NotADirectoryError` and `Presentation()` raising `PackageNotFoundError`.
