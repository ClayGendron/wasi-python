# 189: The package imports itself by name

- **Status:** drafted 2026-11-15; asked for by the owner on 2026-11-15 ("Can we also update the imports so they aren't relative? Have that as a seperate PR?"). Waits on its review before it is built (Decision 8).
- **Date:** 2026-11-15
- **Owner:** Clay Gendron
- **Kind:** **structural**, runner code, parallel-safe in every file but the package's own, **a judge change** for the package-shape check, for one stand-in and for the lint configuration. By AGENTS.md's letter it adds no module-level mutable or lock, no private-API use, no platform branch and no seam, and it takes no module or function past its ceiling. It is structural by its subject: every edge of the import graph is rewritten, and the check that holds the graph's order reads a new form. Reviewed before it is built against the eight rows of `../reviews/README.md` (Decision 7). Code: the 28 modules under `src/wasi_python/` that import a sibling. No wasm build; nothing under `recipes/` or `scripts/` changes, so no `recipe` line of MANIFEST moves.
- **Depends on:** nothing unlanded. Landed: 104 (the runner is a package, and its order check), 108 (the structural rules), 178 (the module list as it stands, `_entry.py` among it).
- **Research it stands on:** every `.py` under `src/wasi_python/` and `recipes/guest/host/`, parsed with `ast` on `dev` at `338ed06d`; ruff's `flake8-tidy-imports` rule TID252, run over the five trees `tests/checks/test_rules.py` lints; the readers of imports in `tests/unit/test_runner_package.py`, `tests/harness/api.py`, `tests/harness/scan.py` and `tests/checks/test_rules.py`, read and run on the same commit; the guest package's loaders in `tests/unit/test_guest_tools.py` and `tests/unit/test_results.py`, and `scripts/steps/70_zip.sh`, which zips it.

Labels: EXECUTED, run and seen; READ, read from a file, cited; INFERRED, reasoned. Line numbers are at `338ed06d`.

## The problem

The package names itself only by dots. Every one of its 172 imports of a sibling is relative, `from . import _process` or `from ._call import run_call`, in 28 modules; none is `from wasi_python…` (EXECUTED, `ast` over `src/wasi_python/`). The owner asked for them to be absolute. A reader then sees in each line where a name comes from, and a search for `wasi_python._call` finds every module that leans on it.

Nothing holds either form today. Ruff's selection, `E F I UP B`, has no rule on relative imports (READ, `pyproject.toml`), so a converted tree would drift back one line at a time.

And the package-shape check reads the relative form only. `_imports` in `tests/unit/test_runner_package.py:90` keeps an `ImportFrom` only when its `level` is above 0. On a converted tree it sees no import at all, and its four checks pass on nothing (EXECUTED: 172 imports seen on `dev`, 0 on the converted copy; a planted `from wasi_python import runner as _late_runner` in `_limits.py`, a module that may not import the runner, passes the order check on the copy). A conversion without a change to the judge would loosen it in silence. That is the finding this specification is mostly about.

## Decisions

### 1. What is there

172 relative imports in 28 modules, 410 names (EXECUTED; ruff counts names, so it reports 410). All are one dot; none climbs.

- **Module level:** 122.
- **Under `if TYPE_CHECKING:`:** 23.
- **Late, inside a function:** 27. Of these, 14 are the engine seam `from . import _wasmtime_ffi as ffi` (`_call.py` 728, 759, 772, 831, 948, 969; `_engines.py` 40, 139, 213; `_fs_table.py` 230, 253, 297; `_outputs.py` 662; `_platform_posix.py` 872), late so that `import wasi_python` does not load the FFI. The other 13 are the cycles and costs `LATE` already lists: `_tool_host` four times, `_fs_memory` three, `_fs_table`, `tools` and `runner` twice each, among them `_results.py:139` and `cli.py:373`.

The most are in `_call.py` (30), `_sessions.py` (19), `runner.py` (14), `__init__.py` (9) and `_entry.py` (9).

Nothing else in the wheel imports the package: `tests/`, `scripts/` and `release/` hold no relative import (EXECUTED, TID252 over all five trees: 410 in `src/wasi_python`, 11 in `recipes/guest`, none elsewhere).

### 2. Each becomes absolute, in place

`from . import x` becomes `from wasi_python import x`; `from .x import y` becomes `from wasi_python.x import y`; aliases stay. Every module's `__package__` is `wasi_python`, so the two forms resolve the same way, through the same `sys.modules` entry and the same attribute lookup, including in `__init__.py` while the package is half-loaded (INFERRED from the import system's rules; EXECUTED below). No `import wasi_python.x` form is used: it binds a different name, `wasi_python`, and would change what each module holds.

Every import stays where it is. A late import stays in its function, and one under `TYPE_CHECKING` stays there. The lines are reordered only as isort's rule `I` already orders them, since `wasi_python` now sorts as a first-party name.

The conversion was tried on a copy of `src/` (EXECUTED, the scratch tree): ruff's fix for TID252, then its fix for `I`, then `ruff format`. On that copy:

- each module's tree, with every relative import read as its absolute twin, is the same as `dev`'s, statement for statement, and each module imports the same names in the same order;
- `import wasi_python` loads the same 24 modules as on `dev`, so the import's cost is unchanged. Nothing in the repository measures import time (READ: no `importtime` or import-time check under `tests/`, `scripts/` or `.github/`), so the module list is the measure, and acceptance criterion 4 holds it;
- the growth is at most 11 lines a module, from lines that now wrap: `runner.py` 1,114 to 1,125, `_sessions.py` 1,244 to 1,253, `_call.py` 1,402 to 1,411, `_tool_host.py` 1,073 to 1,081. All stay under the ceiling of 1,500.

### 3. The guest package stays relative

`recipes/guest/host/` holds 11 relative imports: `tools.py` and `display.py` import the protocol's names from `.`, and `figures.py` imports `display` late. They stay as they are, for two reasons.

- **It is not one package name.** The guest imports it as `host`, from the zip (`scripts/steps/70_zip.sh:303-306`). The unit checks load the same files on the host "under a fresh private name", `_guest_host_{n}`, with a fake `_host` beside them (READ, `tests/unit/test_guest_tools.py:44-60`, `tests/unit/test_results.py:545-566`). An absolute `from host import …` would reach a different module, or none, under each of those names.
- **It is a recipe file.** Every tracked file under `recipes/` is a `recipe` line of MANIFEST (READ, `tests/harness/paths.py:699`). An edit there makes the change build-class and needs a rebuild of the artifact set, for no change to what runs.

### 4. The guard: ruff's TID252, the guest package excepted

`pyproject.toml` gains `TID252` in `select`, `ban-relative-imports = "all"` under `[tool.ruff.lint.flake8-tidy-imports]`, and a `per-file-ignores` entry that excepts `recipes/guest/host/*.py` from TID252, with a comment giving Decision 3's reason. `test_ruff_check_is_clean` already runs ruff over the five trees (READ, `tests/checks/test_rules.py:94-106`), so any relative import that comes back under `src/` is red with no new check.

Ruff over a rules row in `test_rules.py`: the rule exists, it names the line, and its fix is the conversion itself. The per-file entry is narrower than leaving `recipes/guest` out of the rule: it excepts one rule in one folder.

`pyproject.toml` is a judge file (READ, `tests/harness/paths.py:330`, `JUDGE_PATHS`), so this is named in the claims. It adds a rule and loosens none.

### 5. The judge change: the shape check reads both forms

`tests/unit/test_runner_package.py` changes so that its four checks see the same imports after the conversion as before it:

- `_imports` keeps an `ImportFrom` that is relative, as now, or whose module is `wasi_python` or starts with `wasi_python.`, and reads the latter as its relative twin: `from wasi_python import a` as `from . import a`, `from wasi_python.x import y` as `from .x import y`. `_named_modules`, `_order_errors`, `_from_imports`, `_by_name_errors` and `_seam_errors` then read the twin and are otherwise unchanged. `ORDER`, `TOOLS`, `LATE`, `LATE_ANYWHERE`, `ABOVE`, `FILESYSTEM`, `MAY_IMPORT_MOUNTS`, `BY_NAME_MODULES` and `SENTINELS` are unchanged.
- A new check refuses any `import wasi_python` or `import wasi_python.x` statement under `src/wasi_python/`, read from the module's tree, so that no import of a sibling escapes the walker. None exists today (EXECUTED, `ast`; the four `from wasi_python import …` lines `grep` finds are examples inside docstrings).
- The comments and docstrings that show the relative form (lines 61, 91, 112, 173, 227 and 303) show the absolute one.

Seen failing (acceptance criterion 2): the planted `_limits.py` import of The problem passes today on the converted copy and must fail with the change.

Reading both forms tightens the check: a relative import that slipped past ruff would still be judged.

### 6. The readers that hold, and two that follow

Read and found to handle both forms already, so unchanged:

- `tests/harness/api.py:506`, the public-API walker (`node.level > 0` or a module whose first part is `wasi_python`);
- `sibling_imports` in `tests/harness/scan.py:3692`, which `tests/checks/test_rules.py:1504` and `:1618` use, and the import tracer at `scan.py:5761`;
- the platform rules at `tests/checks/test_rules.py:1533-1580`, which match a module by its last part (`_imports_windows`) or by its end (`_platform_hits`);
- `tests/unit/test_scan.py:3496-3506`, which feeds relative strings to `sibling_imports`; they stay valid input.

Two follow the new form:

- `tests/checks/test_v1_4_public_api.py:157-159` plants `from .runner import _UNSET as UNSET` in a copy of `__init__.py` as the one re-export the check must refuse. It plants `from wasi_python.runner import _UNSET as UNSET` instead, the form the package now uses, and still asserts the same one finding. A judge change, named in the claims.
- `tests/unit/test_wasmtime_ffi.py:138`'s comment, "else `from . import` finds the old one", says `from wasi_python import`.

No test patches a name by its module path in a way the form changes: a patch of `wasi_python._call.x` reaches the same module object either way.

### 7. The eight rows

The scores are the 0.1.4 review's (READ); what this change moves:

- **R1 Contract** (Strong): unchanged. No public name, signature or docstring changes; `tests/public_api.txt` is the same.
- **R2 Safety** (Strong): unchanged. No code path changes; each module binds the same names in the same order.
- **R3 Layering** (Strong): holds, and is easier to read: each edge names its module whole. The order check judges the same edges (Decision 5), and the late engine seam stays late.
- **R4 Process state** (Strong): unchanged. No mutable, no lock.
- **R5 Portability** (Strong): unchanged; no platform branch.
- **R6 Testability** (Adequate): unchanged. No seam; `SEAM_ALLOWED` unchanged; the guest package's private-name loading keeps working (Decision 3).
- **R7 Evolvability** (Adequate): holds. Up to 11 lines a module (Decision 2); `_call.py` from 93.5% to 94.1% of the ceiling, already past the 90% reviews watch. `mypy --strict` must still pass.
- **R8 Operability** (Strong): unchanged.

### 8. What the owner or reviewer decides

Whether Decision 3's exception is the right one, or whether the guest package should also be made absolute in a build-class change of its own. This specification recommends leaving it.

## Design

### Files

- `src/wasi_python/*.py`, the 28 modules that import a sibling: imports only.
- `pyproject.toml`: the rule, its option and the per-file exception (Decision 4).
- `tests/unit/test_runner_package.py`: Decision 5.
- `tests/checks/test_v1_4_public_api.py` and `tests/unit/test_wasmtime_ffi.py`: Decision 6.
- `context/changes/189-the-package-imports-itself-by-name.md`: the news file.

### The order of the moves

1. The judge first: change `test_runner_package.py` (Decision 5) and see it still green on the relative tree, then see the planted absolute import red on a converted copy.
2. `pyproject.toml`'s rule, then `ruff check --fix --unsafe-fixes --select TID252 src`, then `ruff check --fix --select I src`, then `ruff format src`. No edit by hand.
3. The comparison script of Decision 2 over `dev` and the branch: the same trees with relative imports read as absolute, the same imports per module, the same 24 modules from `import wasi_python`. Its output recorded.
4. Decision 6's two edits.

### The news file

`context/changes/189-the-package-imports-itself-by-name.md`, For contributors only, one bullet: the package imports its own modules by name, and ruff refuses a relative import under `src/`. Package rows: none. Claims: no new, retired, changed, passing or growing check; `units = 0`; `[claim.judge]` names `pyproject.toml` (the rule added), `tests/unit/test_runner_package.py` (reads both forms, and refuses `import wasi_python`) and `tests/checks/test_v1_4_public_api.py` (the stand-in in the package's form).

## Intent

Every import of the package by itself names `wasi_python`, and the checks that hold the import graph judge exactly what they judged before.

## Scope

**In:** Design's files. **Out:** the guest package (Decision 3); any change to what a module imports, where, or in what order; `tests/`, `scripts/` and `release/`, which import the package by name already.

## Acceptance criteria

1. **No relative import.** TID252 over the five trees finds none outside `recipes/guest/host/` and the 11 there; `test_ruff_check_is_clean` green.
2. **The judge.** The four checks of `test_runner_package.py` green on the branch, and the new `import wasi_python` check; on the branch with step 1's planted import, the order check red, its line recorded; on `dev` with the changed file, still green.
3. **A mechanical change.** Step 3's script reports no difference; its output recorded.
4. **Import cost.** `import wasi_python` loads the same modules on `dev` and the branch, both lists recorded.
5. **Sizes.** `test_no_module_under_src_is_over_the_line_ceiling` green, `ALLOWED` empty, growth at most 11 lines a module.
6. **Nothing public.** `uv run python -I tests/harness/api.py --check` exits 0 with `tests/public_api.txt` unchanged; `test_the_public_api_matches_its_snapshot` green; the re-export check refuses the new stand-in with the one finding.
7. **The guest package.** `tests/unit/test_guest_tools.py` and `tests/unit/test_results.py` green; nothing under `recipes/` changed; MANIFEST's recipe check green.
8. **Types and words.** `test_src_type_checks_under_mypy_strict` green, `tests/harness/typecheck.py` both passes clean; `ruff check`, `ruff format --check` and `uv run pytest tests/lint` green.
9. **The run.** The pull request's run green on Linux and Windows with no `GROWTH` line, its id recorded.

## Landing notes

None yet.
