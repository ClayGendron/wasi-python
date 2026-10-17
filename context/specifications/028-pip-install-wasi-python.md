# 028 — `pip install wasi-python` runs programs

- **Status:** drafted 2026-10-17.
- **Owner:** Clay Gendron
- **Kind:** packaging (`pyproject.toml`, `uv.lock`), the runner's import message
  (`src/wasi_python/runner.py`, `src/wasi_python/__init__.py`'s docstring), a judge check in
  `tests/checks/test_v1_4_embedding.py`, the release workflow's install check, `README.md`,
  `CHANGELOG.md`.
- **Depends on:** 001 (the runner and its `run` extra), 004 (the release's install check).
- **Research it stands on:** the owner's decision of 2026-10-17 (`../decisions.md`, "Install as
  `pip install wasi-python`, without the `run` extra"), after 0.1.0a3's smoke test showed
  `pip install wasi-python` alone cannot run a program; wasmtime-py's 49.0.0 wheels on PyPI
  (8 to 10 MB each, one for every major platform: macOS arm64 and x86_64, manylinux and musllinux
  arm64 and x86_64, Windows arm64 and amd64; EXECUTED, PyPI's JSON).

## The problem

The wheel carries the artifact set, but `wasi_python.run` needs wasmtime-py, which only the
`run` extra brings. A user who types the obvious `pip install wasi-python` gets an `ImportError`
on the first `run` call. Spec 001 made the extra optional so that an embedder that only wants the
artifacts (another language's host, or its own wasmtime binding) carries nothing more; that is a
few megabytes beside an artifact set of about 100 MB, and the owner has chosen the simpler
install.

## Decisions

1. **wasmtime-py becomes a required dependency:** `dependencies = ["wasmtime>=49,<50"]`, the
   same bound the extra had (the runner is tested on 49 only; spec 004). This is the reason
   §4.13 asks for: `run()` and the `wasi-python` command cannot work without it.
2. **The `run` extra stays, empty:** `run = []`, so `pip install "wasi-python[run]"`, the
   0.1.0a3 README and spec 001's text keep working. It is documented as kept for compatibility.
3. **Importing the package stays lazy about wasmtime.** `import wasi_python` and `artifacts()`
   still work where wasmtime-py cannot load; only `run` imports it. The check
   `test_package_imports_without_wasmtime` keeps guarding this, its docstring reworded. The
   import error now says `wasi_python.run needs wasmtime-py (wasmtime>=49,<50), which installs
   with wasi-python; reinstall it or install wasmtime directly`.
4. **The release proves the plain install.** The workflow's install check installs the built
   wheel as `wasi-python @ ./<wheel>` (no extra) and runs a program, so a release whose wheel
   could not run on a plain install never publishes. A second line installs `wasi-python[run] @
   ./<wheel>` and imports the package, so the compatibility extra cannot break unseen.
5. **Docs.** The README's install line becomes `pip install wasi-python` (and `uv add
   wasi-python`); the CHANGELOG says the extra is no longer needed and is kept empty.

## Intent

The command a user guesses first is the one that works.

## Design

```
pyproject.toml, uv.lock               the dependency; the empty extra
src/wasi_python/runner.py             the import error's text
src/wasi_python/__init__.py           its docstring
tests/checks/test_v1_4_embedding.py   the lazy-import check's docstring; a check of the metadata
.github/workflows/release.yml         the plain install and the extra
README.md, CHANGELOG.md
```

## Scope

In: the above. Out: pinning wasmtime-py tighter than `>=49,<50`; vendoring wasmtime; a separate
artifacts-only package.

## Acceptance criteria

1. A new v1.4 check reads the built wheel's metadata (or `pyproject.toml` where no wheel is
   built) and finds `Requires-Dist: wasmtime<50,>=49` without a marker, and the extra `run`
   declared with no requirement; seen failing first on today's metadata.
2. In a fresh environment, `uv run --isolated --no-project --with "wasi-python @ <wheel>"` runs a
   program through `wasi_python.run` and through `wasi-python run`; the same with `[run]`
   imports.
3. `test_package_imports_without_wasmtime` still passes.
4. `uv run pytest` green with `--accept-judge`; lost 0; grew 0. A release dry run passes,
   its install check using the plain name.

## Landing notes

Not built.
