# Review of 028 — `pip install wasi-python` runs programs (the specification, before build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the specification or the decision behind it. I read `AGENTS.md` and the constitution (§4.2, §4.13, §4.14, §5.2, §5.6, §5.7, §6.4). Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `context/specifications/028-pip-install-wasi-python.md` as drafted (`ae35507`).
- **Read:** `pyproject.toml`; `uv.lock`'s `wasi-python` entry; `src/wasi_python/__init__.py`; `src/wasi_python/runner.py` (the module docstring, `_wasmtime`, the other `import wasmtime` sites); `src/wasi_python/cli.py`'s imports; `tests/checks/test_v1_4_embedding.py` (`test_package_imports_without_wasmtime`); `tests/harness/paths.py` (`JUDGE_PATHS`), `tests/harness/needs.py` (`wheel`), `tests/harness/artifacts.py` (`wheel_errors`), `release/version.py` (`check_errors`); `.github/workflows/release.yml` (the `env` block, the build job's judge, the verify job's install check); `release/build-constraints.txt`; `README.md` ("Running it"); `CHANGELOG.md`; specs 001 (Decision on the extra, line 155), 004 (verify, lines 71-80) and 019 (Decision 5); `context/decisions.md` ("Install as `pip install wasi-python`"); reviews 004 and 019 where they quote the extra; wasmtime-py 49.0.0's `_ffi.py` as installed.
- **Ran (EXECUTED, darwin-arm64, uv 0.9.22, pip 26.2.1).** Nothing in the repository was edited but this file; I did not run the judge or `scripts/build.sh` in the main tree. Work is under `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev028-029/`:
  - `repo028/`: `git archive HEAD` of the package files with the change applied (`dependencies = ["wasmtime>=49,<50"]`, `run = []`), built with the release's own command (`uv build --wheel --build-constraints release/build-constraints.txt --require-hashes`) into `dist028/`; `repoHEAD/` and `distHEAD/`, the same for today's `pyproject.toml`.
  - Each wheel's `METADATA`; `uv lock` on the changed copy and its diff against today's lock.
  - Installs of the changed wheel: `uv run --isolated --no-project --with "wasi-python[run] @ …"`, the same with `[nosuch]` and `[nosuch3]` (an extra that does not exist), plain `wasi-python @ …`; `pip install` into a seeded venv (`venvpip/`) with `[run]` and `[nosuch]`; `uv pip install` into fresh venvs (`venvuv/`, `venvuv2/`) with `[run]` and `[nosuch]`.
  - Criterion 2 by hand: the changed wheel installed plain, `wasi_python.run` on a pandas sum and `wasi-python run -- -c "print(1)"`, with `WASI_PYTHON_ARTIFACTS` pointed at the main tree's `build/artifacts/` (read only; the scratch wheel carries no set).
  - Today's wheel installed plain, calling `run`.
  - PyPI's JSON for wasmtime 49.0.0 (the file list).

## What holds

- **An empty extra is valid and quiet.** EXECUTED: hatchling 1.32.4 writes `Provides-Extra: run` and `Requires-Dist: wasmtime<50,>=49` with no marker. `pip install "wasi-python[run] @ file://…"` prints nothing; `pip install "…[nosuch]"` prints `WARNING: wasi-python 0.1.0a3 does not provide the extra 'nosuch'`. So pip tells the two apart, and `[run]` gets no warning. `uv pip install` likewise warns only for `[nosuch]`. The installed metadata reads `['wasmtime<50,>=49'] ['run']`.
- **The plain install runs programs.** EXECUTED: `uv run --isolated --no-project --with "wasi-python @ <changed wheel>"` installs wasmtime 49.0.0. `run([...pandas sum...])` returns `0 b'6\n'`. `wasi-python run -- -c "print(1)"` prints exactly the line the workflow expects. On today's wheel the same plain install raises `ImportError wasi_python.run needs wasmtime-py: pip install "wasi-python[run]"`, which is the problem the spec states.
- **The lock change is small and the judge sees it.** EXECUTED: `uv lock` on the changed copy moves wasmtime from `[package.optional-dependencies] run` to `dependencies`, drops the marker from `requires-dist`, and keeps `provides-extras = ["run"]`. READ: `pyproject.toml` and `uv.lock` are both in `JUDGE_PATHS`, so the judge hash changes, and criterion 4 already says `--accept-judge`. The workflow sets `UV_LOCKED: "1"`, so the lock must be committed with the change; the Design lists it.
- **Nothing else in the judge trips.** READ: no check reads `Requires-Dist`, `Provides-Extra` or `optional-dependencies` today. `wheel_errors` compares only the artifact files inside the wheel. `release/version.py check_errors` reads only the version lines. The same-bytes job builds the wheel twice from one tree, so the new metadata is the same on both. `release/build-constraints.txt` pins only the build backend, so a runtime dependency does not touch it.
- **The lazy import still matters and is still tested.** READ: every `import wasmtime` in the package is inside a function or under `TYPE_CHECKING`. It matters for three users: an embedder that installs with `--no-deps` to keep its own wasmtime binding; a platform where wasmtime-py installs but cannot load (next section); and the import cost of `import wasi_python`. `test_package_imports_without_wasmtime` sets `sys.modules['wasmtime'] = None`, so it covers every case in which importing wasmtime would fail.
- **The release check proves the plain install.** READ and INFERRED: with the dependency missing or still behind the extra, the plain line's `run` call raises `ImportError` and the step fails. The build job runs the judge after `uv build`, so `dist/` holds the real wheel there. A wheel-reading check would therefore see the published metadata in CI.
- **The reason §4.13 asks for is written** (Decision 1).

## Acceptance criteria against evidence

1. Metadata check: **not well defined** (Finding 2). Its two sources write the requirement in different forms, and "no requirement" for the extra has no stated test.
2. Fresh install runs: **reachable.** EXECUTED by hand above. The `[run]` half proves nothing about the extra (Finding 1). The criterion does not say where it runs or which artifact set it uses.
3. Lazy import: **reachable.** It passes today, and nothing in the change touches it.
4. Green with `--accept-judge`: **reachable**, once Finding 2 makes the new check precise.

## Findings, most severe first

1. **Medium. The `[run]` install line cannot catch a broken extra.** (Decision 4; criterion 2; `release.yml` verify)
   - The defect. Decision 4 says the second line, which installs `wasi-python[run] @ ./<wheel>` and imports the package, means "the compatibility extra cannot break unseen".
   - Failure. EXECUTED: `uv run --isolated --no-project --with "wasi-python[nosuch3] @ <wheel>" python -I -c "print('exit ok')"` prints `exit ok`, exits 0 and gives no warning. The workflow installs with `uv run --with`, which is this command. If a later edit deleted `run = []`, the line would still pass. Only pip and `uv pip install` warn, and neither fails.
   - Fix. Have the line assert the metadata it installed: `importlib.metadata.metadata("wasi-python").get_all("Provides-Extra") == ["run"]`, and no `Requires-Dist` carries an `extra ==` marker. Or drop the line and say the criterion-1 check guards the extra. Either way, correct Decision 4's sentence.

2. **Medium. Criterion 1's check is not defined well enough to build one way.** (Criterion 1)
   - The defect. The check reads "the built wheel's metadata (or `pyproject.toml` where no wheel is built)" and looks for the string `Requires-Dist: wasmtime<50,>=49`. READ: `dist/` holds a wheel only in the release build job. Locally, and in the verify job (a fresh checkout), the check reads `pyproject.toml`, which writes `"wasmtime>=49,<50"` in another order and another syntax. "Declared with no requirement" has no stated test for either source.
   - Failure. INFERRED: a string match written for the wheel fails on `pyproject.toml`. A loose match (`"wasmtime" in deps`) passes a marker or a different bound. The two branches can drift apart.
   - Fix. Write the test. Always read `pyproject.toml` with `tomllib`: `project.dependencies` is exactly one requirement, and `packaging.requirements.Requirement` gives name `wasmtime`, specifier `>=49,<50` and no marker. `optional-dependencies` is exactly `{"run": []}`. `packaging` is in the lock through pytest (READ). When `dist/` holds the wheel, also parse its `METADATA`. Its `Requires-Dist` list must parse to that same single requirement. `Provides-Extra` must be exactly `["run"]`. Asking for exactly one dependency also makes §4.13 mechanical: a dependency added later turns the check red until a specification gives its reason. The fail-first evidence is today's wheel, EXECUTED: `Requires-Dist: wasmtime<50,>=49; extra == 'run'`.

3. **Medium. The cost to an embedder that brings its own wasmtime is not stated.** (The problem; Decision 1; Scope)
   - The defect. The problem section puts the cost at "a few megabytes" against about 100 MB. It leaves out the version bound. Spec 001 kept the extra optional for "another language's host, or its own wasmtime binding". A Python embedder on wasmtime-py 50 or later can no longer `pip install wasi-python` beside it. The resolver refuses, or `pip` downgrades its wasmtime to 49.
   - Failure. INFERRED from the bound `<50`. Nothing in the spec or README tells that embedder what to do.
   - Fix. Name the trade-off in the problem section, so the owner's decision covers it. Add one README line: an embedder that brings its own wasmtime installs with `pip install --no-deps wasi-python` and uses `artifacts()`. That route is why the lazy import (Decision 3) still matters.

4. **Low. Where wasmtime-py installs but cannot load, the new message is never shown.** (Decision 3)
   - The defect. READ: wasmtime 49.0.0 publishes a `py3-none-any` wheel (8,262,567 bytes, EXECUTED, PyPI JSON) beside its platform wheels. Its `_ffi.py` raises `RuntimeError("unsupported architecture for wasmtime: …")`, or `RuntimeError` on 32-bit, at import. `_wasmtime()` catches only `ImportError`. Before this spec, a plain install on such a host did not install wasmtime, and users got the install message. Now `pip install wasi-python` succeeds there, and `run` raises wasmtime's own `RuntimeError`.
   - Fix. One sentence in Decision 3: a wasmtime that is installed but cannot load raises its own error, which names the platform, and the runner passes it through. Or catch `RuntimeError` and `OSError` too, and chain it with the platform in the message. Neither message has a check today (READ: no test asserts the text). Add one that asserts `wasmtime>=49,<50` in the `ImportError` with wasmtime blocked, as the lazy-import check already blocks it.

5. **Low. Text that this change makes false is not in the Kind.** (Kind; Design)
   - READ: `runner.py:9` ("wasmtime-py (the `run` extra) is imported only …"); spec 001 line 155 (the message naming `wasi-python[run]`); spec 004 lines 71 and 78 (verify installs "with the `run` extra … so the `run` extra's own pin … is what is tested"); spec 019 Decision 5 ("wasmtime stays optional", which quotes the old message); `CHANGELOG.md:212` (the `run` extra).
   - Fix. List each in the Kind. Give specs 001, 004 and 019 a one-line amendment note pointing to 028, as earlier amendments did. Name 019 under "Depends on".

6. **Low (§6.4). Say what happens to the dev group's `wasmtime>=49,<50`.**
   - READ: `[dependency-groups] dev` repeats the bound. Once wasmtime is a project dependency, the dev group's copy is redundant. If kept, the two bounds can drift apart. Decide one way and write it down. Dropping it is the smaller choice. Keeping it is harmless if the metadata check compares the two.

## Constitution checks

- **§4.2:** not tripped. wasmtime-py is a runtime dependency of the wheel, not a build input. The range is the one the extra already published. The build pins nothing new.
- **§4.13:** the reason is written (Decision 1). Uses uv only. Finding 2's exactly-one-dependency check would enforce the rule from now on.
- **§4.14, §5.7:** the change touches `.github/workflows/release.yml`. By AGENTS.md rule 2 that makes it build-class, so it waits for 027, the build-class change now in flight. The drafting commit's message says so ("builds after 027 lands"). The specification does not. Put it in the header.
- **§4.15:** no default loosened. A plain install now carries a runner, but `run()` keeps every default.
- **§5.2:** open choices in Findings 2, 3 and 4.
- **§5.6:** the spec changes neither the guest's imports or exports nor the artifact set or the build recipe, so this pre-build review is not strictly required. It was asked for.
- **§6.4:** Finding 6.

## Disposition (filled in by the author, then confirmed by the reviewer)

All six findings are taken.

1. **Fixed.** Decision 4's second line asserts the installed metadata (`Provides-Extra` exactly `["run"]`, no `extra ==` marker), and its sentence no longer claims an import proves it.
2. **Fixed.** Criterion 1 reads `pyproject.toml` with `tomllib` and `packaging`, as you wrote.
3. **Fixed.** The problem section names the `<50` bound's cost and the `--no-deps` route; the README gains that line (Design).
4. **Fixed.** `_wasmtime` catches `ImportError`, `RuntimeError` and `OSError` and chains the original under the message; criterion 3 adds a `RuntimeError` case asserting the text.
5. **Fixed.** The Kind lists `runner.py:9`, `__init__.py`, and amendment notes for specs 001, 004 and 019; 019 is under "Depends on".
6. **Fixed.** The dev group's copy is removed; criterion 1 asserts it names no wasmtime.

## Verdict

Revise first, lightly. The change does what it says. EXECUTED: an empty extra is valid. pip and `uv pip` accept `[run]` without a warning, and a plain install runs a program and the command. Nothing in today's judge trips beyond the expected judge-hash change. But the release's `[run]` line cannot fail on a missing extra (Finding 1). The new metadata check has no single definition (Finding 2). And the cost to an embedder on another wasmtime is not stated (Finding 3).

One line: make wasmtime required as written, but define the metadata check from `pyproject.toml` and the wheel, assert `Provides-Extra` instead of trusting a silent `uv run --with "[run]"`, and state the `--no-deps` route for embedders on another wasmtime.

## Confirmation

- **Date:** 2026-10-17
- **Reviewer:** the same fresh agent (Claude Opus 5.5); not the author.
- **Reviewed:** the specification as revised in `d6f2792`, and the Disposition above (`b8824bc`), by `git diff ae35507 b8824bc -- context/specifications/028-pip-install-wasi-python.md`. I wrote nothing in the repository but this section. I did not commit or stage it.

### Each disposition against its finding

1. **The `[run]` line: closed.** READ: Decision 4 now asserts `Provides-Extra` is exactly `["run"]` and that no `Requires-Dist` has an `extra ==` marker. It also says why an import alone proves nothing. One loose end is condition A.
2. **The metadata check: closed.** READ: criterion 1 uses `tomllib` and `packaging`, requires exactly one dependency, `{"run": []}`, and no wasmtime in the dev group. It no longer reads the wheel's `METADATA`. That is acceptable, because Decision 4's install line now checks the published wheel's metadata on three systems.
3. **The `<50` cost: closed.** READ: the problem section names it and the `--no-deps` route. The Design adds the README line.
4. **A wasmtime that cannot load: closed, with condition B.** READ: `_wasmtime` catches `ImportError`, `RuntimeError` and `OSError`, and criterion 3 tests the `RuntimeError` case.
5. **Stale text: closed.** READ: the Kind names `runner.py:9`, `__init__.py`, and the amendment notes for 001, 004 and 019. 019 is under "Depends on".
6. **The dev group: closed.** READ: it is removed, and criterion 1 asserts that. INFERRED: the dev environment still gets wasmtime, because the editable project depends on it. EXECUTED earlier: the relocked `wasi-python` entry lists `dependencies = [{ name = "wasmtime" }]`.

### Conditions left (each a sentence; none changes the design)

- **A. Criterion 2 still says "the same with `[run]` imports".** Make it match Decision 4: the `[run]` install asserts the metadata.
- **B. Name the type `_wasmtime` raises.** I assume `ImportError`, raised `from` the original, so `run()`'s callers and the command line's `"kind"` see one type whatever went wrong. Say it. Criterion 3's `RuntimeError` case needs a stand-in `wasmtime` module whose import raises. `sys.modules[...] = None` only gives `ImportError`. Say how the check builds it: a folder on `sys.path` in the child process.
- **C. The class.** The change edits `release.yml`, so it is build-class (AGENTS.md rule 2) and waits for 027. The header still does not say so.

### §5.2

After A to C, nothing is left to the build.

### Verdict

**Passes for build**, once A to C are written in. All six findings are closed.

One line: the revision closes every finding; align criterion 2 with Decision 4, name the raised type and how the `RuntimeError` stand-in is built, and mark the spec build-class.

### The confirmation's conditions, written in by the author

Each condition is written into the specification's Decisions or criteria, marked by its letter.
