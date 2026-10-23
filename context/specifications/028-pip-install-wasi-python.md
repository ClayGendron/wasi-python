# 028 — `pip install wasi-python` runs programs

- **Status:** drafted 2026-10-17; revised against its pre-build review (`../reviews/028-pip-install-wasi-python-spec-2026-10-17.md`), whose confirmation passed it for build with three conditions, written in. It is build-class (it changes the release workflow; constitution §5.7), so it builds after spec 027 lands (condition C). Built 2026-10-17 on `spec/028-pip-install-wasi-python`; build-reviewed (`../reviews/028-pip-install-wasi-python-2026-10-17.md`, verdict: lands once finding 2 is fixed and a dry run passes); revised against it the same day (findings 1 to 3) and confirmed. Landed 2026-10-17 (accepted on `f7b8df2` as `d98249b`; dry run 39090912968).
- **Owner:** Clay Gendron
- **Kind:** packaging (`pyproject.toml`: the dependency, the empty extra, the dev group; `uv.lock`), the runner (`src/wasi_python/runner.py`: its module docstring at line 9 and `_wasmtime`'s message; `src/wasi_python/__init__.py`'s docstring), judge checks in `tests/checks/test_v1_4_embedding.py`, the release workflow's install check, `README.md`, `CHANGELOG.md`, and a one-line amendment note in specs 001 (line 155), 004 (lines 71, 78) and 019 (Decision 5) pointing here.
- **Depends on:** 001 (the runner and its `run` extra), 004 (the release's install check), 019 (the command line's import error).
- **Research it stands on:** the owner's decision of 2026-10-17 (`../decisions.md`, "Install as `pip install wasi-python`, without the `run` extra"), after 0.1.0a3's smoke test showed `pip install wasi-python` alone cannot run a program; wasmtime-py's 49.0.0 wheels on PyPI (8 to 10 MB each, one for every major platform: macOS arm64 and x86_64, manylinux and musllinux arm64 and x86_64, Windows arm64 and amd64; EXECUTED, PyPI's JSON).

## The problem

The wheel carries the artifact set, but `wasi_python.run` needs wasmtime-py, which only the `run` extra brings. A user who types the obvious `pip install wasi-python` gets an `ImportError` on the first `run` call. Spec 001 made the extra optional so that an embedder that only wants the artifacts (another language's host, or its own wasmtime binding) carries nothing more; that is a few megabytes beside an artifact set of about 100 MB. One cost is larger: the bound `wasmtime>=49,<50` now applies to every install, so an embedder whose own environment needs wasmtime 50 or later can no longer install wasi-python beside it with plain `pip install`; it installs with `pip install --no-deps wasi-python` and uses `artifacts()` with its own binding (the reason Decision 3's lazy import still matters). The owner has chosen the simpler install with this trade-off.

## Decisions

1. **wasmtime-py becomes a required dependency:** `dependencies = ["wasmtime>=49,<50"]`, the same bound the extra had (the runner is tested on 49 only; spec 004). This is the reason §4.13 asks for: `run()` and the `wasi-python` command cannot work without it. The dev group's copy of the bound is removed, so the two cannot drift (the project dependency already brings wasmtime into the dev environment).
2. **The `run` extra stays, empty:** `run = []`, so `pip install "wasi-python[run]"`, the 0.1.0a3 README and spec 001's text keep working. It is documented as kept for compatibility.
3. **Importing the package stays lazy about wasmtime.** `import wasi_python` and `artifacts()` still work where wasmtime-py cannot load; only `run` imports it. The check `test_package_imports_without_wasmtime` keeps guarding this, its docstring reworded. The import error now says `wasi_python.run needs wasmtime-py (wasmtime>=49,<50), which installs with wasi-python; reinstall it or install wasmtime directly`. A wasmtime that is installed but cannot load (its pure `py3-none-any` wheel on an unsupported platform raises `RuntimeError` naming the architecture) has its own error chained under the same message: `_wasmtime` catches `ImportError`, `RuntimeError` and `OSError` and raises `ImportError` from it (condition B). A check asserts the message names `wasmtime>=49,<50`.
4. **The release proves the plain install.** The workflow's install check installs the built wheel as `wasi-python @ ./<wheel>` (no extra) and runs a program, so a release whose wheel could not run on a plain install never publishes. A second line installs `wasi-python[run] @ ./<wheel>` and asserts the installed metadata: `Provides-Extra` is exactly `["run"]` and no `Requires-Dist` carries an `extra ==` marker (an unknown extra installs silently, so an import alone would prove nothing).
5. **Docs.** The README's install line becomes `pip install wasi-python` (and `uv add wasi-python`); the CHANGELOG says the extra is no longer needed and is kept empty.

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

In: the above. Out: pinning wasmtime-py tighter than `>=49,<50`; vendoring wasmtime; a separate artifacts-only package.

## Acceptance criteria

1. A new v1.4 check reads `pyproject.toml` with `tomllib`: `project.dependencies` is exactly one requirement which `packaging.requirements.Requirement` parses as name `wasmtime`, specifier `>=49,<50`, no marker; `project.optional-dependencies` is exactly `{"run": []}`; the dev group names no wasmtime. Seen failing first on today's file.
2. In a fresh environment, `uv run --isolated --no-project --with "wasi-python @ <wheel>"` runs a program through `wasi_python.run` and through `wasi-python run`; the same with `[run]` asserts the installed metadata as Decision 4 says (condition A).
3. `test_package_imports_without_wasmtime` still passes; a check, in a subprocess whose `sys.meta_path` begins with a finder that raises `RuntimeError` for `wasmtime`, calls `run` and finds an `ImportError` naming `wasmtime>=49,<50` whose `__cause__` is that `RuntimeError` (condition B).
4. `uv run pytest` green with `--accept-judge`; lost 0; grew 0. A release dry run passes, its install check using the plain name.

## Landing notes

Built 2026-10-17 by the implementer (Claude Opus 5.5), on darwin-arm64, uv 0.9.22, in the worktree `wasi_python-028`; not yet reviewed. Each claim is labelled. The artifact set is the frozen one, `build/sets/4befe9de64edc783` of the main tree, read only. Scratch outputs are under `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/b028/`.

**What was built** (READ: the diff). `pyproject.toml`: `dependencies = ["wasmtime>=49,<50"]`, `run = []`, the dev group without wasmtime, each with its reason in a comment; `uv.lock` from `uv lock` (wasmtime moves from the `run` extra to `dependencies`, the marker leaves `requires-dist`, `provides-extras = ["run"]` stays, the dev group loses wasmtime). `src/wasi_python/runner.py`: the module docstring, and `_wasmtime` catching `ImportError`, `RuntimeError` and `OSError` and raising `ImportError("wasi_python.run needs wasmtime-py (wasmtime>=49,<50), which installs with wasi-python; reinstall it or install wasmtime directly")` from the original. `src/wasi_python/__init__.py`: its docstring. `tests/checks/test_v1_4_embedding.py`: `test_package_imports_without_wasmtime`'s docstring, and two new v1.4 checks, `test_a_plain_install_brings_wasmtime` (criterion 1) and `test_a_wasmtime_that_cannot_load_is_named` (criterion 3: a child process whose `sys.meta_path` begins with a finder that raises `RuntimeError` for `wasmtime`). `.github/workflows/release.yml`: the verify job installs `wasi-python @ ./<wheel>` for the program and the command, and a third line installs `wasi-python[run] @ ./<wheel>` and asserts `Provides-Extra == ["run"]` and no `Requires-Dist` with an `extra ==` marker. `README.md` ("Running it": the plain install, `uv add`, the empty extra, the `--no-deps` route), `CHANGELOG.md` (0.1.0a4), and one amendment note each in specs 001, 004 and 019.

**Seen failing first** (EXECUTED). Both new checks ran on today's `pyproject.toml` and runner, before any other edit: `test_a_plain_install_brings_wasmtime` failed `assert 0 == 1` (`project.dependencies` was `[]`); `test_a_wasmtime_that_cannot_load_is_named` failed with the finder's `RuntimeError` escaping `_wasmtime` uncaught. After the change both pass, with `test_package_imports_without_wasmtime` (3 passed).

**Criterion 1** (EXECUTED): the check passes on the changed file, by `tomllib` and `packaging.requirements.Requirement`, as written.

**Criterion 2** (EXECUTED). The wheel was built with the release's own command, `uv build --wheel --build-constraints release/build-constraints.txt --require-hashes`, with the frozen set copied into `src/wasi_python/artifacts/` first (as the build job does) and removed after, into `dist/` under the scratch folder: `wasi_python-0.1.0a4-py3-none-any.whl`, 38,788,843 bytes. Its `METADATA` holds `Requires-Dist: wasmtime<50,>=49` (no marker) and `Provides-Extra: run`. Then, with `WASI_PYTHON_ARTIFACTS=""` as the workflow sets it, the workflow's three lines by hand:
- `uv run --isolated --no-project --with "wasi-python @ ./<wheel>" python -c …` installed wasmtime 49.0.0, found the wheel's own artifacts, and printed `Completed(exit_code=0, stdout=b'6\n', stderr=b'', trapped=None, fuel_used=None, truncated=())`; exit 0.
- the same install, `wasi-python run -- -c "print(1)"`, printed exactly the line the workflow wants.
- `--with "wasi-python[run] @ ./<wheel>"` printed `Provides-Extra: ['run'] Requires-Dist: ['wasmtime<50,>=49']`; exit 0.

The same lines against a wheel built from today's `HEAD` (no change; in `headdist/`) fail: the `[run]` metadata line raises `AssertionError: ["wasmtime<50,>=49; extra == 'run'"]`, and the plain install's `run` raises `ImportError: wasi_python.run needs wasmtime-py: pip install "wasi-python[run]"`. So each line catches what it is there for.

**Criterion 3** (EXECUTED): `test_package_imports_without_wasmtime` passes; the `RuntimeError` check passes. The command line reports the new message with exit 1 (`{"error": "wasi_python.run needs wasmtime-py (wasmtime>=49,<50), …", "kind": "ImportError"}`, wasmtime blocked by `sys.modules['wasmtime'] = None`), as spec 019's Decision 5 expects.

**Criterion 4** (EXECUTED, without `--accept`: only the lane accepts). `uv sync`, then `WASI_PYTHON_ARTIFACTS=<frozen set> uv run pytest`: 762 passed, 19 skipped, exit 0. `wasi_python v1: 184/195 pass · 0 gap · 11 blocked · 0 fail`; v1.4 72/72 (70 before, plus the two new checks); `ratchet vs 567d64204b: lost 0 · absent 0 · unrun 0 · unrun locally 9 · gained 2 · grew 0 · judge changed: pyproject.toml, tests/checks/test_v1_4_embedding.py, uv.lock`. The ninth check unrun locally is the oracle check, blocked because this worktree has no oracle environment. The lane accepts with `--accept-judge`. `ruff check` and `ruff format --check` clean on `src` and `tests`. The release dry run is not run here: it needs a push the builder is not allowed to make (INFERRED: its install step is the three lines above, run on three systems).

**Revised against the build review** (`../reviews/028-pip-install-wasi-python-2026-10-17.md`), 2026-10-17, by the implementer; its three findings are taken.
- Finding 1: `test_a_wasmtime_that_cannot_load_is_named` is parametrized over `RuntimeError` and `OSError` (a platform wheel whose native library will not load). Seen failing first (EXECUTED): with `OSError` dropped from `_wasmtime`'s `except`, `[OSError]` fails and `[RuntimeError]` passes; restored, both pass (`cmp` against the kept copy).
- Finding 2: `runner.py`'s module docstring now says a call that names no root has no `/` and nothing writable (spec 025), and that `root=True` makes a fresh private one. No behaviour and no judge input changes.
- Finding 3: the dev-group compare uses `packaging.utils.canonicalize_name`. Seen failing first (EXECUTED): with `"Wasmtime>=49,<50"` added to the dev group, the check fails; restored, it passes.
- The judge again (EXECUTED, without `--accept`): 763 passed, 19 skipped, exit 0; `wasi_python v1: 185/196 pass · 0 gap · 11 blocked · 0 fail`; v1.4 73/73; `ratchet vs 567d64204b: lost 0 · absent 0 · unrun 0 · unrun locally 9 · gained 3 · grew 0 · judge changed: pyproject.toml, tests/checks/test_v1_4_embedding.py, uv.lock`. `ruff check` and `ruff format --check` clean. Criterion 4's release dry run is still outstanding: it needs the push.

**Landed 2026-10-17** through the lane: rebased onto main (range-diff: both commits unchanged), judged on a detached HEAD at `f7b8df2` (778 passed, 4 skipped; v1 lost 0, grew 0), accepted with `--accept-judge` (`d98249b`, the two progress files alone; the rules tier passed on it), and main fast-forwarded. Release dry run 39090912968 on `d98249b`: every job passed; the verify job on Windows, Linux and macOS installed the wheel as plain `wasi-python @ ./<wheel>`, ran a program and the command line, and asserted the `[run]` metadata (criterion 4).
