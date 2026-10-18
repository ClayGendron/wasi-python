# Review of 028 — `pip install wasi-python` runs programs (the build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the change, the specification,
  its pre-build review or its confirmation. I read `AGENTS.md`, the constitution (§4.2, §4.5,
  §4.10, §4.13, §4.14, §4.15, §5.6, §5.7, §7), specification 028 with its landing notes, its
  pre-build review with the confirmation and conditions A to C, the 027 build review (for the
  format), `src/wasi_python/runner.py` (the module docstring, `run`, `run_async`, `_wasmtime`,
  `_runtime_folders`), `tests/harness/paths.py` (`JUDGE_PATHS`), `tests/harness/needs.py`
  (`wheel`), wasmtime-py 49.0.0's `_ffi.py` as installed, and the diff. I did not rely on the
  landing notes. Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `git show 28b5675` on `spec/028-pip-install-wasi-python` (one commit, twelve
  files): `pyproject.toml`, `uv.lock`, `src/wasi_python/runner.py`, `src/wasi_python/__init__.py`,
  `tests/checks/test_v1_4_embedding.py`, `.github/workflows/release.yml`, `README.md`,
  `CHANGELOG.md`, amendment notes in specs 001, 004 and 019, and spec 028's landing notes.
- **Ran (EXECUTED, darwin-arm64, uv 0.9.22).** Outputs are under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev028b/`.
  - In the worktree: `uv sync` (nothing to change), then
    `WASI_PYTHON_ARTIFACTS=<main tree>/build/sets/4befe9de64edc783 uv run pytest -p no:cacheprovider`
    (`judge.log`); `uv run ruff check src tests`; `uv run ruff format --check src tests`. The
    judge overwrote the worktree's `build/progress/latest.json`; I restored the implementer's copy
    byte for byte (`cmp`). `git status` was clean before and after.
  - `co/`: `git archive 28b5675` unpacked, with the implementer's wheel
    (`wasi_python-0.1.0a4-py3-none-any.whl`, 38,788,843 bytes, sha256 `bf745de2…0426`) in
    `co/release-assets/`. The verify step's `run:` block was cut out of `release.yml` as written
    (`step.sh`) and run the way Actions runs `shell: bash` (`bash --noprofile --norc -eo pipefail`),
    with the workflow's `UV_LOCKED=1`, `UV_PYTHON=3.14.2`, `WASI_PYTHON_ARTIFACTS=""` and a fresh
    `UV_CACHE_DIR`, so wasmtime came from PyPI: twice, both with `/bin/bash` 3.2.57
    (`step-plain.log`, `step-plain-bash32.log`).
  - The same step against three wheels whose `METADATA` I rewrote (`tools/mutwheel.py`): the old
    marker (`extra == 'run'`), no `Provides-Extra`, and a second, marked `Requires-Dist`
    (`step-old.log`, `step-noextra.log`, `step-extramarker.log`).
  - `pip install <wheel>` in a fresh seeded venv (`venvpip/`), then the `wasi-python` command;
    `pip install "wasi-python[run] @ file://…"` there (warnings grepped); `pip install --no-deps`
    in another (`venvnodeps/`), then `artifacts()`, `run` and the command.
  - Stand-in `wasmtime` packages on `sys.path` whose `__init__` raises `RuntimeError`, `OSError`
    and `ValueError`, against the installed wheel (`stand-*/`).
  - 15 mutants of the runner and `pyproject.toml` in `co/` (`tools/mutants.py`, `mutants.txt`),
    each written, run against the three relevant checks, and restored; `cmp` against pristine
    copies afterwards.
  - `test_wheel_carries_the_artifact_set` in `co/` with the wheel in `dist/` (removed after).
  - `git merge-tree` of the branch against `main` (now `4444781`) and against
    `spec/030-a-cancel-in-the-door-is-named`.
  - In the main tree I wrote only this file. No commit, stage, push, checkout, restore or stash.
    I never passed `--accept`, and nothing wrote `context/progress/`.

## What holds

- **The judge (EXECUTED, `judge.log`).** 762 passed, 19 skipped, exit 0.
  `wasi_python v1: 184/195 pass · 0 gap · 11 blocked · 0 fail`; v1.4 72/72;
  `ratchet vs 567d64204b: lost 0 · absent 0 · unrun 0 · unrun locally 9 · gained 2 · grew 0 ·
  judge changed: pyproject.toml, tests/checks/test_v1_4_embedding.py, uv.lock`. This matches the
  landing notes number for number. `ruff check` and `ruff format --check` are clean. Of the nine
  unrun locally, I ran the `wheel` one by hand with the implementer's wheel: it passes. The rest
  need the oracle, the prior-art clones, the unpacked source trees or three systems.
- **The plain install runs programs (EXECUTED).** The verify step, run as Actions runs it, exits 0
  under bash 3.2: the pandas sum prints
  `Completed(exit_code=0, stdout=b'6\n', stderr=b'', trapped=None, fuel_used=None, truncated=())`,
  the command prints exactly the `want` line, and the `[run]` line prints
  `Provides-Extra: ['run'] Requires-Dist: ['wasmtime<50,>=49']`. Each line also prints
  `warning: --locked has no effect when used alongside --no-project`, which was already so before
  this change (the step ran with `UV_LOCKED=1` before too). `pip install <wheel>` in a fresh venv
  brings `wasmtime 49.0.0`, and `wasi-python run -- -c "print(1)"` prints the same line. pip prints
  no warning for `[run]`.
- **Each workflow line fails on what it is there for (EXECUTED).** Old marker: the first line
  fails with `ImportError: wasi_python.run needs wasmtime-py (wasmtime>=49,<50), …`, exit 1. No
  `Provides-Extra`: the third line fails `AssertionError: []`. A marked `Requires-Dist` beside the
  plain one: the third line fails, naming it. So the plain-install line and the metadata line
  each catch a real break, and the metadata line catches the case `uv run --with` would install
  silently (the pre-build review's finding 1).
- **The `--no-deps` route works as the README says (EXECUTED).** No wasmtime installed;
  `artifacts()` returns, and `wasmtime` is not in `sys.modules`; `run` raises the new
  `ImportError` with `ModuleNotFoundError` as its cause; the command prints
  `{"error": "wasi_python.run needs wasmtime-py (wasmtime>=49,<50), …", "kind": "ImportError"}` and
  exits 1, as spec 019's Decision 5 expects.
- **A wasmtime that cannot load (EXECUTED, READ).** wasmtime-py 49's `_ffi.py` raises
  `RuntimeError` on a 32-bit platform, an unknown platform or an unknown architecture, and
  `cdll.LoadLibrary` raises `OSError` when the native library cannot load. With a real stand-in
  package on `sys.path`: `RuntimeError` and `OSError` both reach the caller as `ImportError`, cause
  kept; a `ValueError` is not caught, which matches Decision 3's list.
- **The lazy import (READ, EXECUTED).** `run` and `run_async` call `_wasmtime()` before
  anything else needs wasmtime; `_runtime_folders` and the two `from wasmtime import _ffi` sites
  run only after it. A mutant adding `import wasmtime` at the runner's top fails both
  `test_package_imports_without_wasmtime` and the new finder check.
- **The release workflow on three systems (READ, INFERRED).** The verify job sets
  `defaults: run: shell: bash`, so Windows runs this step in Git Bash too, not pwsh. The new lines
  use the forms the old ones used: `uv run --isolated --no-project --with "<name> @ ./$wheel"`
  and a multi-line `python -c "…"` in double quotes. Those forms passed on all three systems in
  0.1.0a3's dry runs (READ: `context/progress/history.jsonl` row 6's reason, "five dry runs, the
  last green on three systems"; spec 027's landing cites run 39084581927). What is new is
  `r'extra\s*=='` inside the double quotes. Bash keeps a backslash before `s` as is (EXECUTED,
  bash 3.2; the same rule holds in every bash). No argument starts with `/`, so MSYS path
  conversion does not touch them (INFERRED). wasmtime 49.0.0 has a platform wheel for each
  runner (`windows-2025` amd64, `ubuntu-24.04` x86_64 manylinux, `macos-15` arm64; the
  specification's research line, EXECUTED there). Still, only the dry run proves Windows.
- **Nothing else moves (READ, EXECUTED).** `scripts/` and `recipes/` are untouched, so the
  artifact set and `MANIFEST` are unchanged; the wheel still carries exactly the set (the `wheel`
  check above). No workflow step runs `uv sync --no-install-project` or `--no-editable`, so the
  dev environment still gets wasmtime through the editable project. `packaging`, which the new
  check imports, is in the lock through pytest. The branch merges with `main` (`4444781`) and with
  `spec/030-a-cancel-in-the-door-is-named` without conflict (`git merge-tree`), although 030 also
  edits `runner.py`, the v1.4 check file and `CHANGELOG.md`.

## Mutants (EXECUTED, `mutants.txt`)

Caught (12 of 15): `_wasmtime` catching `ImportError` only; `from None`; the old message; the
eager top-level import; `dependencies = []`; `>=49` alone; a marker; a second dependency;
`run` not empty; `run` removed; the dev group repeating `wasmtime>=49,<50`; `wasmtime[x]`.

Survived (3): `OSError` dropped from the `except` (finding 1); `except Exception` (a broader catch
the specification does not forbid; no change asked); the dev group repeating the bound spelled
`Wasmtime>=49,<50` (finding 3). `co/` matched its pristine copies by `cmp` afterwards.

## The implementer's seven flags

1. **Nine checks unrun locally.** Agreed, and one fewer in fact: the `wheel` check passes with the
   built wheel. The rest need what a worktree lacks. No change asked.
2. **No release dry run.** Agreed that it needs a push. My bash run of the step and its three
   mutants is the best a reviewer can do here. Criterion 4 waits on the dry run (below).
3. **Old CHANGELOG text kept.** Agreed. `CHANGELOG.md:220` is 0.1.0a3's history; rewriting it
   would make it false about that release.
4. **The finder check, and the unchecked `OSError` path.** The finder follows criterion 3's
   wording; the confirmation suggested a folder on `sys.path`. They are equivalent at the
   `import` statement (EXECUTED: the folder stand-in gives the same `ImportError` and cause). The
   `OSError` gap is finding 1.
5. **The stale module docstring.** It should be fixed here (finding 2).
6. **Spec 004's amendment note.** Placed at the end of the same bullet that names the extra at
   lines 71 and 78; it covers both. Agreed. Spec 001's other two mentions (lines 39 and 182) and
   spec 002's line 160 still say "the `run` extra"; they describe what was built then, and the
   note at 001:155 points readers here. No change asked.
7. **`scripts/` untouched.** Confirmed (READ: the diff). The change is build-class only through
   `release.yml`, and spec 027, the build-class change before it, has landed (`dc188a6`,
   `64d7570`), as condition C required.

## Acceptance criteria against evidence

1. *The metadata check.* **Met** (EXECUTED). `test_a_plain_install_brings_wasmtime` reads
   `pyproject.toml` with `tomllib` and `packaging` as written: exactly one requirement, name
   `wasmtime`, `SpecifierSet(">=49,<50")`, no marker, no extras; `{"run": []}`; no wasmtime in the
   dev group. Eight of nine `pyproject.toml` mutants fail it, including today's file
   (`dependencies = []`, the extra holding the bound). The one survivor is finding 3.
2. *A fresh install runs a program; `[run]` asserts the metadata.* **Met** (EXECUTED), as above:
   `uv run --isolated --no-project` from a cold cache, the program, the command, and the metadata,
   plus pip.
3. *The lazy-import check passes; a `RuntimeError` finder gives an `ImportError` naming the bound,
   caused by it.* **Met** (EXECUTED). `test_a_wasmtime_that_cannot_load_is_named` fails on
   today's `_wasmtime` (the `ImportError`-only mutant), on `from None`, and on the old message.
4. *Green with `--accept-judge`; lost 0; grew 0; a release dry run.* **Not yet.** The judge is
   green with lost 0, grew 0 and the judge change named (EXECUTED, without `--accept`; only the
   lane accepts). The dry run is outstanding; it needs the push.

## Findings, most severe first

1. **Low. The `OSError` branch has no check.** (Decision 3; `_wasmtime`;
   `test_a_wasmtime_that_cannot_load_is_named`)
   - Failure. EXECUTED: dropping `OSError` from the `except` passes all three checks. Yet
     `OSError` is the likelier field case: a platform wheel whose native library will not load (a
     glibc wheel on musl, a missing system library) raises it from `cdll.LoadLibrary`.
   - Fix. Parametrize the check over `RuntimeError` and `OSError` (the finder raises the given
     type; the assertion compares the cause's type name). About three lines.

2. **Low. The runner's module docstring still describes the old default.** (`runner.py`, lines
   13–14: "a call that names no root gets a fresh private one, removed afterwards")
   - The defect. READ: since spec 025 a call with no root has no `/` and nothing writable;
     `root=True` is what makes a fresh private one (`run`'s own docstring, and constitution §4.15).
     The sentence is two lines below the text this change rewrites, in the paragraph that
     states the safety defaults, so a reader is told the opposite of the rule.
   - Fix. In this change, since the specification's Kind already names this docstring:
     "a call that names no root has no `/` and nothing writable (spec 025; `root=True` makes a
     fresh private one, removed afterwards)". Say so in the landing notes. It changes no
     behaviour and no judge input.

3. **Low (nit). The dev-group test does not normalize names.**
   (`test_a_plain_install_brings_wasmtime`)
   - Failure. EXECUTED: `dev = [..., "Wasmtime>=49,<50"]` passes; `Requirement(...).name` keeps
     the case as written. The bound could then drift again, which is what Decision 1 removed it to
     prevent.
   - Fix. Compare `packaging.utils.canonicalize_name(Requirement(d).name)` with `"wasmtime"`.

4. **For the record (no change asked).**
   - The `[run]` line asserts that no `Requires-Dist` carries an `extra ==` marker, not that the
     unmarked wasmtime requirement is there. The first line covers that in practice: a plain
     install without wasmtime fails its `run` (EXECUTED, the old-marker mutant).
   - Nothing in the judge reads `release.yml`'s install lines, so a later edit back to
     `wasi-python[run] @` would pass the judge. Specification 028 asks for no such check; the
     reviewed diff and the dry run carry it.
   - Spec 030 and this branch both add to `CHANGELOG.md`'s 0.1.0a4 section and edit
     `runner.py` and the v1.4 check file. They merge cleanly today; whichever lands second
     rebases and is judged again, as the lane does anyway.

## Constitution checks

- **§4.13:** the reason for the one new dependency is written (Decision 1) and next to it in
  `pyproject.toml`. The exactly-one-dependency check makes the rule mechanical from now on
  (EXECUTED: the second-dependency mutant fails it). uv only: the workflow and the checks use
  `uv run`; the child processes run `sys.executable`, as the existing check does.
- **§4.2:** not tripped. wasmtime-py is a runtime dependency of the wheel, not a build input; the
  build pins nothing new; `uv.lock` already held wasmtime 49.0.0 with hashes.
- **§4.5:** no embedder named (EXECUTED: the rules goal is green).
- **§4.10:** the landing notes label their claims, and what I re-ran matches them: the judge's
  counts, the wheel's size, its `METADATA`, the three lines' outputs and the error text.
- **§4.14, §5.7:** one specification on its own `spec/028-…` branch in an outside worktree; it is
  build-class through `release.yml` and was built after 027 landed.
- **§4.15:** no default loosened. A plain install now carries a runner, and `run()` keeps every
  default.
- **§5.6:** this review re-ran the counted tests and checked each criterion against evidence.
- **§7:** nothing tripped. No source tree, recipe or artifact touched; nothing committed or pushed
  by me.

## Disposition (filled in by the author, then confirmed by the reviewer)

All three findings are taken, in `ca54ff4` on `spec/028-pip-install-wasi-python` (after
`28b5675`). Each was seen failing first where a check could catch it (EXECUTED).

1. **Fixed.** `test_a_wasmtime_that_cannot_load_is_named` is parametrized over `RuntimeError`
   and `OSError`; the finder raises the given type, and the assertion compares the cause's type
   name. With `OSError` dropped from `_wasmtime`'s `except`, `[OSError]` fails and
   `[RuntimeError]` passes; restored, both pass.
2. **Fixed.** `runner.py`'s module docstring now reads: "a call that names no root has no `/`
   and nothing writable (spec 025; `root=True` makes a fresh private one, removed afterwards)".
   The landing notes say so. No behaviour and no judge input changes.
3. **Fixed.** The dev-group compare uses `packaging.utils.canonicalize_name`. With
   `"Wasmtime>=49,<50"` added to the dev group, the check fails; restored, it passes.
4. **For the record: no change**, as asked.

The judge after the revision (EXECUTED, in the worktree, without `--accept`): 763 passed,
19 skipped, exit 0; `wasi_python v1: 185/196 pass · 0 gap · 11 blocked · 0 fail`; v1.4 73/73;
`ratchet vs 567d64204b: lost 0 · absent 0 · unrun 0 · unrun locally 9 · gained 3 · grew 0 ·
judge changed: pyproject.toml, tests/checks/test_v1_4_embedding.py, uv.lock`. `ruff check` and
`ruff format --check` clean. Criterion 4's release dry run is still outstanding; it needs the
push, which is the owner's or the lane's.

## Verdict

**Lands once finding 2 is fixed and the dry run passes**; findings 1 and 3 are a few lines each
and can go in the same pass. The change does what the specification says. EXECUTED:
`pip install wasi-python` and `uv run --with "wasi-python @ <wheel>"` bring wasmtime 49.0.0 and
run a program and the command; `[run]` still installs, with no warning, and its metadata is what
Decision 4 says; `--no-deps` keeps `artifacts()` and gives one clear `ImportError`. The workflow's
three lines pass under bash as Actions runs them, and each fails on the break it is there for.
The judge is green with lost 0, grew 0. The gaps are small: one error type has no check, one
docstring sentence is false, and one name compare is case-sensitive.

One line: the plain install now runs programs and the release proves it; check the `OSError`
path, fix the stale no-root sentence, normalize the dev-group name, then dry-run and land.

## Confirmation (2026-10-17)

- **Reviewer:** the same fresh agent (Claude Opus 5.5); not the author.
- **Reviewed:** `git show ca54ff4` (`runner.py`'s module docstring, the two checks in
  `tests/checks/test_v1_4_embedding.py`, the specification's status line and landing notes), and
  the Disposition above.
- **Ran (EXECUTED, darwin-arm64).** Outputs are under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev028b/`.
  The same 15 mutants on `co2/`, a `git archive ca54ff4` copy (`mutants2.txt`; both files
  matched their pristine copies by `cmp` afterwards). In the worktree: `uv sync`, then
  `WASI_PYTHON_ARTIFACTS=<main tree>/build/sets/4befe9de64edc783 uv run pytest -p no:cacheprovider`
  (`judge2.log`), and `ruff check` and `ruff format --check` on `src` and `tests`. I restored the
  worktree's `build/progress/latest.json` byte for byte afterwards. I also ran `git merge-tree`
  of the branch with `main` and with `spec/030-…`. I wrote nothing but this section. No commit,
  stage, push, checkout, restore or stash. I never passed `--accept`.

### Each disposition against its finding

1. **Closed.** With `OSError` dropped from the `except`, `test_a_wasmtime_that_cannot_load_is_named[OSError]`
   now fails and `[RuntimeError]` passes (EXECUTED). The other runner mutants (catching
   `ImportError` only, `from None`, the old message) fail both parameters. The eager-import
   mutant fails both and the lazy-import check too.
2. **Closed.** READ: the module docstring now says a call with no root has no `/` and nothing
   writable (spec 025), and that `root=True` makes a fresh private one. This agrees with `run`'s
   docstring and §4.15. Only the docstring changed in `src/`, so the wheel I tested at `28b5675`
   behaves the same (INFERRED).
3. **Closed.** With `"Wasmtime>=49,<50"` in the dev group, `test_a_plain_install_brings_wasmtime`
   now fails (EXECUTED). All nine `pyproject.toml` mutants are caught.
4. **No change, as asked.**

Mutants now: 14 of 15 caught. The only survivor is `except Exception`, which the specification
does not forbid.

### The judge

EXECUTED: 763 passed, 19 skipped, exit 0. `wasi_python v1: 185/196 pass · 0 gap · 11 blocked ·
0 fail`; v1.4 73/73; `ratchet vs 567d64204b: lost 0 · absent 0 · unrun 0 · unrun locally 9 ·
gained 3 · grew 0 · judge changed: pyproject.toml, tests/checks/test_v1_4_embedding.py, uv.lock`.
That matches the Disposition. The finder check is now parametrized, so it has two ids: one more
gained, and nothing absent. ruff is clean. The branch merges with `main` and with
`spec/030-a-cancel-in-the-door-is-named` without conflict.

### Verdict

**028 lands.** All three findings are closed. Every criterion is met, except criterion 4's
release dry run. That run is the lane's job after the push, and the landing notes must cite it.
The lane then accepts with `--accept-judge`, naming the judge change above.

One line: the fixes close all three findings, and the judge is green with lost 0 and grew 0; land
it through the lane, which runs the dry run and accepts with `--accept-judge`.
