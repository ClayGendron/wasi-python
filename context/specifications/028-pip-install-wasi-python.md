# 028 — `pip install wasi-python` runs programs

- **Status:** drafted 2026-10-17; revised against its pre-build review
  (`../reviews/028-pip-install-wasi-python-spec-2026-10-17.md`), whose confirmation passed it for
  build with three conditions, written in. It is build-class (it changes the release workflow;
  constitution §5.7), so it builds after spec 027 lands (condition C).
- **Owner:** Clay Gendron
- **Kind:** packaging (`pyproject.toml`: the dependency, the empty extra, the dev group;
  `uv.lock`), the runner (`src/wasi_python/runner.py`: its module docstring at line 9 and
  `_wasmtime`'s message; `src/wasi_python/__init__.py`'s docstring), judge checks in
  `tests/checks/test_v1_4_embedding.py`, the release workflow's install check, `README.md`,
  `CHANGELOG.md`, and a one-line amendment note in specs 001 (line 155), 004 (lines 71, 78) and
  019 (Decision 5) pointing here.
- **Depends on:** 001 (the runner and its `run` extra), 004 (the release's install check), 019
  (the command line's import error).
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
few megabytes beside an artifact set of about 100 MB. One cost is larger: the bound
`wasmtime>=49,<50` now applies to every install, so an embedder whose own environment needs
wasmtime 50 or later can no longer install wasi-python beside it with plain `pip install`; it
installs with `pip install --no-deps wasi-python` and uses `artifacts()` with its own binding
(the reason Decision 3's lazy import still matters). The owner has chosen the simpler install
with this trade-off.

## Decisions

1. **wasmtime-py becomes a required dependency:** `dependencies = ["wasmtime>=49,<50"]`, the
   same bound the extra had (the runner is tested on 49 only; spec 004). This is the reason
   §4.13 asks for: `run()` and the `wasi-python` command cannot work without it. The dev group's
   copy of the bound is removed, so the two cannot drift (the project dependency already brings
   wasmtime into the dev environment).
2. **The `run` extra stays, empty:** `run = []`, so `pip install "wasi-python[run]"`, the
   0.1.0a3 README and spec 001's text keep working. It is documented as kept for compatibility.
3. **Importing the package stays lazy about wasmtime.** `import wasi_python` and `artifacts()`
   still work where wasmtime-py cannot load; only `run` imports it. The check
   `test_package_imports_without_wasmtime` keeps guarding this, its docstring reworded. The
   import error now says `wasi_python.run needs wasmtime-py (wasmtime>=49,<50), which installs
   with wasi-python; reinstall it or install wasmtime directly`. A wasmtime that is installed
   but cannot load (its pure `py3-none-any` wheel on an unsupported platform raises
   `RuntimeError` naming the architecture) has its own error chained under the same message:
   `_wasmtime` catches `ImportError`, `RuntimeError` and `OSError` and raises `ImportError`
   from it (condition B). A check asserts the message
   names `wasmtime>=49,<50`.
4. **The release proves the plain install.** The workflow's install check installs the built
   wheel as `wasi-python @ ./<wheel>` (no extra) and runs a program, so a release whose wheel
   could not run on a plain install never publishes. A second line installs `wasi-python[run] @
   ./<wheel>` and asserts the installed metadata: `Provides-Extra` is exactly `["run"]` and no
   `Requires-Dist` carries an `extra ==` marker (an unknown extra installs silently, so an import
   alone would prove nothing).
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
README.md (the install line; `--no-deps` for an embedder with its own wasmtime), CHANGELOG.md
specs 001, 004, 019                    a one-line amendment note each
```

## Scope

In: the above. Out: pinning wasmtime-py tighter than `>=49,<50`; vendoring wasmtime; a separate
artifacts-only package.

## Acceptance criteria

1. A new v1.4 check reads `pyproject.toml` with `tomllib`: `project.dependencies` is exactly
   one requirement which `packaging.requirements.Requirement` parses as name `wasmtime`,
   specifier `>=49,<50`, no marker; `project.optional-dependencies` is exactly `{"run": []}`; the
   dev group names no wasmtime. Seen failing first on today's file.
2. In a fresh environment, `uv run --isolated --no-project --with "wasi-python @ <wheel>"` runs a
   program through `wasi_python.run` and through `wasi-python run`; the same with `[run]` asserts
   the installed metadata as Decision 4 says (condition A).
3. `test_package_imports_without_wasmtime` still passes; a check, in a subprocess whose
   `sys.meta_path` begins with a finder that raises `RuntimeError` for `wasmtime`, calls `run`
   and finds an `ImportError` naming `wasmtime>=49,<50` whose `__cause__` is that `RuntimeError`
   (condition B).
4. `uv run pytest` green with `--accept-judge`; lost 0; grew 0. A release dry run passes,
   its install check using the plain name.

## Landing notes

Not built.
