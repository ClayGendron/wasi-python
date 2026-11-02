- **Project:** CairoSVG (https://github.com/Kozea/CairoSVG)
- **Against:** 2.9.1 (the pinned sdist, `cairosvg-2.9.1.tar.gz`)
- **Status:** drafted
- **Title:** Read VERSION through the package's loader, so CairoSVG imports from a zip
- **Files:** cairosvg/__init__.py
- **Why we carry it:** the guest imports CairoSVG from the stdlib zip, where `Path(__file__).resolve().parent / 'VERSION'` names no file: `import cairosvg` raises `NotADirectoryError` before anything else runs.

The patch is `recipes/patches/cairosvg-2.9.1/0001-read-version-through-the-package-loader.patch`, written by specification 174's build (2026-10-31). The owner sends this, or not; nothing has been posted, and no agent will post anything to CairoSVG.

## What the project asks of a contributor

Read 2026-10-31 (GitHub's contents API, `main`): the repository's top holds `.github`, `LICENSE`, `NEWS.rst`, `README.rst`, the package, `setup.cfg`, `setup.py` and the non-regression tests. It has no `CONTRIBUTING` file and no `AGENTS.md`, and its README states no rule for pull requests, nor anything about AI tools. So the text below is written as a pull request, and it says that an AI tool wrote the change, the honest default.

## Related reports

Searched 2026-10-31 (GitHub's issue search on `Kozea/CairoSVG`: "zip import", "VERSION file"): no issue or pull request is about this defect. The frozen branches above the line (PyInstaller, py2exe; WeasyPrint #540 and #269) are the same cause met earlier, each fixed for its own tool. The line is unchanged on `main` (read 2026-10-31: `cairosvg/__init__.py` line 21).

## The pull request

**Title:** Read VERSION through the package's loader, so CairoSVG imports from a zip

`cairosvg/__init__.py` reads its version with `(ROOT / 'VERSION').read_text()`, where `ROOT` is `Path(__file__).resolve().parent` when CairoSVG is not frozen. When CairoSVG is imported from a zip archive (a wheel or a zipapp on `sys.path`, an embedded interpreter's zipped library), that path is inside the archive and names no file, so `import cairosvg` raises `NotADirectoryError` (or `FileNotFoundError`).

Reproduction, with the released wheel itself on the path (a wheel is a zip that `zipimport` reads):

```
PYTHONPATH=cairosvg-2.9.1-py3-none-any.whl python -c "import cairosvg"
NotADirectoryError: [Errno 20] Not a directory: '.../cairosvg-2.9.1-py3-none-any.whl/cairosvg/VERSION'
```

The change keeps both frozen branches as they are, and in the plain case reads the same file with `importlib.resources.files(__name__).joinpath('VERSION').read_text(encoding='utf-8')`, which goes through the package's loader: a file from a folder, a member from a zip. `ROOT` keeps its value for any code that reads it. `importlib.resources.files` is in every Python CairoSVG supports (3.10 and later).

Nothing a user sees changes when CairoSVG is installed as files: the same bytes are read, and `cairosvg.VERSION` is the same string.

**Tested** on CPython 3.15.2 (macOS, arm64): from a zip of the patched package, `import cairosvg` succeeds and `cairosvg.VERSION` is `2.9.1`; from a zip of the released one it raises as above. The change was written with an AI tool (Claude Code, Claude Opus 5.5), and every line was read and run as described here.

## The evidence

EXECUTED on 2026-10-31 in specification 174's build (`context/specifications/174-svg-to-png-through-cairo.md`, landing notes):

- from a zip of the patched package, the VERSION line reads `2.9.1` (the import then needs cairocffi, as it does from files);
- in this project's guest (CPython 3.15.2 for `wasm32-wasip1`, CairoSVG in its stdlib zip), `import cairosvg` succeeds and `svg2png` writes a PNG.
