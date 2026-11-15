# Review of 189 — The package imports itself by name (before it is built)

- **Date:** 2026-11-15
- **Reviewer:** an agent (Claude), a fresh sub-agent of https://claude.ai/code/session_01BD1pVHiZoxnwRv6JCqJKeC; not the author
- **Reviewed:** the specification as drafted, `context/specifications/189-the-package-imports-itself-by-name.md` at `5fbb68ee` on `spec/189-the-package-imports-itself-by-name` (from `dev` at `338ed06d`), against every `.py` under `src/wasi_python/` and `recipes/guest/host/`, `pyproject.toml`'s ruff tables, `tests/unit/test_runner_package.py` whole, `tests/harness/api.py` (the walker, `reexport_errors`, the child loader), `tests/harness/scan.py` (`sibling_imports`, the import tracer), `tests/checks/test_rules.py` (`_ruff`, the filesystem and platform rules, `LONG_FUNCTIONS`, the ceiling), `tests/checks/test_v1_4_public_api.py`, `tests/unit/test_wasmtime_ffi.py`, the guest loaders in `tests/unit/test_guest_tools.py` and `tests/unit/test_results.py`, `scripts/steps/70_zip.sh`, `tests/harness/news.py` and `release/ci_plan.py`'s `classify`.
- **Run:** none; a pre-build review has no pull request run. Nothing dispatched, no `gh`.
- **Box:** 45 minutes (structural); kept.
- **Re-ran:** on the base and on a converted copy of my own (`git archive 5fbb68ee` into a scratch folder outside the repository; ruff 0.17.1, the lock's pin, `--fix --unsafe-fixes` for TID252, then `--fix` for `I`, then `ruff format`), all EXECUTED:
  - An `ast` survey of the base: 172 relative imports, all one dot, 410 names, 28 modules; 122 at module level, 23 under `TYPE_CHECKING`, 27 inside a function; no `from wasi_python…` and no `import wasi_python…` statement. The 27 late ones are 14 of `_wasmtime_ffi` (at the lines Decision 1 gives) and 13 that are exactly `LATE`'s 13 rows.
  - TID252 with `ban-relative-imports = "all"` over the five trees: 421, that is 410 in `src/` and 11 in `recipes/guest/host/`. The fix leaves 0 relative imports and writes no `import wasi_python.x` form. Afterwards `ruff check` is clean and `ruff format` changes nothing.
  - Each module's `ast.dump`, with every relative import read as its absolute twin, equals the copy's in all 33 files. No statement moved, and every late or `TYPE_CHECKING` import stays where it was. `isort`'s 8 fixes therefore touch only the blank lines between sections (INFERRED from the equal trees).
  - Growth: `runner.py` +11, `_call.py` +9, `_sessions.py` +9, `_tool_host.py` +8; `src/` 17,387 → 17,424. No function's length changes, so `LONG_FUNCTIONS` holds as it stands.
  - `import wasi_python` from each tree: the same 24 package modules and the same 130 new `sys.modules` entries, with neither `_wasmtime_ffi` nor `wasmtime` loaded. After importing `cli`, `tools`, `_tool_host`, `_fs_memory` and `_wasmtime_ffi` as well, the insertion order of `sys.modules` is the same (equal digests). Every one of the 32 modules binds the same global names on both trees (equal digest), and `from wasi_python import *` and `from wasi_python.tools import *` each give exactly their `__all__`.
  - The shape check, unchanged, on the copy: 4 passed. With The problem's plant (`from wasi_python import runner as _late_runner` in `_limits.py`), the order checks still pass: 2 passed. That is the specification's finding, reproduced.
  - A prototype of Decision 5, written from its text alone: `_imports` reads `from wasi_python[.x]` as its relative twin (`ast.copy_location`), and a new test refuses `import wasi_python[.x]` at any depth. On the copy with the plant: `_limits.py:14 (_limits imports runner, not before it in ORDER)`. Without the plant: 5 passed. On the base tree: 5 passed. Read line-free, the walker gives the same 172 imports on both trees, and `_from_imports` the same 146 entries (equal digests).
  - The guard prototyped in the copy's `pyproject.toml`: `ruff check` over the five trees exits 0. A relative import planted in `src/` and one in `tests/` are each refused by TID252, while one in `recipes/guest/host/` is excepted.
  - On the copy, with `PYTHONPATH` set to its `src/` (and `wasi_python` checked to load from there): `test_runner_package.py`, `test_v1_4_public_api.py`, `test_wasmtime_ffi.py`, `test_guest_tools.py`, `test_results.py`, `test_scan.py` and `test_src_type_checks_under_mypy_strict` gave 640 passed and 1 failed. The base gave 640 passed; the extra test on the copy is my prototype's. The one failure is `test_the_package_is_typed`, which asks git whether `py.typed` is tracked, and the copy is not a checkout. `tests/harness/typecheck.py`: "both passes are clean". `api.py --check --package <copy>`: exit 0. The rules by keyword (ruff, mypy, ceiling, filesystem, platform, seam, mutable): 10 passed and 1 skipped (needs the artifact set).
  - `uv run pytest tests/lint -q -p no:cacheprovider` on the branch with this file: 14 passed.

Labels: EXECUTED means I ran it; READ means I read the file cited; INFERRED means my reasoning.

## Acceptance criteria against evidence

1. No relative import — met on the copy: 0 in `src/`, and the 11 in the guest package excepted (EXECUTED).
2. The judge — met on my prototype: the plant is red with its line, the converted tree is green, and the base is green (EXECUTED). Finding 2 adds what the plant alone does not show.
3. A mechanical change — met: the trees are equal statement for statement (EXECUTED).
4. Import cost — met: the same modules, loaded in the same order (EXECUTED).
5. Sizes — met: at most 11 lines a module, the largest `_call.py` at 1,411 of 1,500 (EXECUTED).
6. Nothing public — met on the copy: `api.py --check` exits 0 and the star exports are unchanged (EXECUTED). Since `reexport_errors` reads every `ImportFrom` whatever its level (READ, `api.py:534-552`), the retargeted stand-in is judged exactly as the relative one was (INFERRED).
7. The guest package — met: no file under `recipes/` changes, and both loaders' files are green on the copy (EXECUTED).
8. Types and words — met on the copy (EXECUTED).
9. The run — only the pull request can show it. `classify` sets `runner` for `src/` and `pyproject.toml`, and `platform` for the `_platform_*` files (READ, `release/ci_plan.py:156-185`), so the Windows legs run.

The line numbers Decision 6 and Decision 3 cite name what they say (READ). `tests/harness/paths.py:330` is `"pyproject.toml"` in `JUDGE_PATHS`, and `:699` is `recipe_files`.

## Findings, most severe first

There is no High and no Medium. Every name stays bound and every import stays where it was. The import graph keeps its edges. The judge reads a superset of what it read before.

1. **Low: one of the fourteen engine-seam imports carries no alias** (`src/wasi_python/_engines.py:40`). Decision 1 says all fourteen are `from . import _wasmtime_ffi as ffi`. `_wasmtime()`'s import is bare, `from . import _wasmtime_ffi  # noqa: F401`, and is there only for its `ImportError` (READ). The fix keeps the comment (EXECUTED). Fix text, Decision 1: "Of these, 14 import the engine seam, 13 as `from . import _wasmtime_ffi as ffi` and one, `_engines.py:40`, bare, for its `ImportError` alone (`# noqa: F401`)."
2. **Low: the plant shows the order check only.** `_from_imports`, which drives the by-name and seam checks, reads the same twin. But no criterion shows that it still finds its entries on the converted tree. A twin that kept `wasi_python.x` as its module would empty that list in silence while leaving the order check red (INFERRED). On my prototype the walker reads the same 172 imports and `_from_imports` the same 146 entries on both trees (EXECUTED). Fix text, criterion 2, at its end: "and, read without line numbers, `_imports` over every module gives the same 172 entries on `dev` and on the branch, and `_from_imports` the same 146; both digests recorded."
3. **Low: Decision 5's new check leaves two details unsaid.** Fix text, Decision 5's second bullet, after "read from the module's tree": "at any depth (module level, inside a function, under `TYPE_CHECKING`), by `ast.walk`." Its first bullet, at its end: "The twin keeps the original's line (`ast.copy_location`), so a finding names the line in the file."
4. **Low: `[claim.judge]` leaves out one judge file the change edits.** `tests/unit/test_wasmtime_ffi.py` is under `tests/`, which is a judge path (READ, `paths.py:323-330`), and Decision 6 edits its comment. The news file's claims name "each judge file changed, with its reason" (READ, `tests/harness/news.py:31`). Fix text, The news file: "…and `tests/unit/test_wasmtime_ffi.py` (a comment names the import's new form; no assertion changes)."
5. **Low: the news entry needs a page to link.** `entry_errors` refuses an entry that does not end with a link to the documentation site (READ, `news.py:173-191`). The specification names none. Fix text, The news file: "…one bullet, ending with a link to `contributing/principles/`, whose 'uv only' line names ruff."
6. **Low: the guard is wider than the news bullet says.** TID252 is selected for every tree `test_ruff_check_is_clean` lints, so it also refuses a relative import in `tests/`, `scripts/` and `release/` (EXECUTED for `tests/`). That is right, but the bullet says "under `src/`". Fix text, The news file: "ruff refuses a relative import anywhere it lints, the guest package excepted."
7. **A note: one route around the walker stays open, as it is today.** An import by `importlib.import_module("wasi_python.x")` is invisible to every reader, before and after. None exists in `src/` (EXECUTED, `grep`: the only `__import__` hits are guest code inside strings at `_call.py:410-413`). Nothing is loosened, so no fix is needed.

## The open question (Decision 8)

Keep the guest package relative, as recommended. Both reasons hold. First, the zip ships it as `host` (READ, `70_zip.sh:303-306`), while the unit checks load the same files as `_guest_host_{n}` through `spec_from_file_location` with `submodule_search_locations` (READ). A relative import resolves against whichever name was given. An absolute `from host import …` would resolve to a module named `host` on the host's `sys.path`, which is none, or the wrong one (INFERRED). Second, any edit there moves a `recipe` line and makes the change build-class, for no change to what runs. The per-file entry is the narrowest exemption: one rule, one folder. A new file in `host/` inherits it, and a file anywhere else in `recipes/guest/` does not (EXECUTED).

## Equivalence of the two forms

The forms resolve the same way. In a module whose `__package__` is `wasi_python`, `from .x import y` resolves to the absolute name `wasi_python.x` before `_gcd_import` runs, so both forms take the same path through `sys.modules`. `from . import x` and `from wasi_python import x` both end in `_handle_fromlist` on the package object (INFERRED from the import system; EXECUTED as the equal load orders above).

The absolute form cannot run `__init__.py` again or out of turn. A submodule's body runs only after its parent is in `sys.modules`, so `from wasi_python import _process` inside a half-loaded `__init__.py`, or a late `from wasi_python import _wasmtime_ffi as ffi`, finds the same partly built package object a relative import would. The comment at `test_wasmtime_ffi.py:138` stays true for the same reason.

The `from` form is the one that keeps names identical. `from wasi_python import x` binds `x`, as `from . import x` did. `import wasi_python.x` would bind `wasi_python` instead and change every module's namespace, which Decision 2 rules out and Decision 5's new check refuses. `import *` cannot change either. Four modules declare an `__all__` (`__init__`, `mounts`, `tools`, `_wasmtime_ffi`), and no rewrite touches one. For the rest, the star takes a module's public globals, and those are the same on both trees (READ for the four `__all__`s; EXECUTED for the globals, by the digest above).

The forms differ only for a file loaded under another package name. No test loads a `src/` module that way (READ: every `spec_from_file_location` under `tests/` loads a script or the guest package). `test_v1_4_public_api.py`'s scratch copy is loaded as `wasi_python` itself, and its origin is checked (READ, `api.py:1066-1077`).

## Structure

Measured by the README's commands on `5fbb68ee` and on my converted copy (EXECUTED).

| measurement | before | after (copy) |
|---|---|---|
| `src/` lines | 17,387 | 17,424 (+37, wrapped import lines) |
| largest module | `_call.py` 1,402 (93.5%) | 1,411 (94.1%) |
| functions over 80 | 6 | 6, none longer |
| mutables and locks (grep) | 0 | 0 |
| private-API lines (grep) | 90 | 90 |
| platform reads | 3 | 3 |
| `Any` / `type: ignore` | 488 / 4 | 488 / 4 |
| relative imports in `src/` | 172 | 0 |

The structure line (step 4a): the change adds no concern, lifecycle flag, module-level mutable, test seam, platform branch or private-API use, and takes no function past 80 lines. No row scores it down. The Kind line carries **structural** all the same, by its subject (R3), so this review is the one it asks for.

- R1 Contract: unchanged. The snapshot holds, and the star exports are identical.
- R2 Safety: unchanged. Each module binds the same names in the same order.
- R3 Layering: holds Strong. The same edges and the same late seams, and the order check now reads both forms. Each edge names its module whole.
- R4 Process state: unchanged.
- R5 Portability: unchanged. The platform rules match by a module's last part or its end, so they read either form (READ, `test_rules.py:1533-1580`).
- R6 Testability: unchanged. No seam, and the guest package's private-name loading is untouched.
- R7 Evolvability: holds Adequate. `_call.py` moves 0.6 points nearer its ceiling, already past the 90% that reviews watch. mypy is clean on the copy.
- R8 Operability: unchanged.

## The judge

Every reader of imports was checked (READ, then EXECUTED on the copy). `api.py:506`, `sibling_imports` and the tracer at `scan.py:5761` read both forms already, so the filesystem rule (`test_rules.py:1491`), the platform-halves rule (`:1611`) and the platform rules judge the converted tree as they judged the relative one.

`shards.py:461` and `test_build_scripts.py:898` read jobs and stand-ins, not `src/`. `test_runner_package.py` is the one reader that sees only the relative form. Decision 5 makes it read a superset, and its tables (`ORDER`, `LATE`, `TOOLS` and the rest) are unchanged.

The stand-in's retarget keeps its strength. `pyproject.toml` gains a rule and loosens none, and nothing in the repository reads ruff's tables (READ, `grep`). The judge change strengthens the check; it does not loosen it.

## Constitution checks

- §4.10: the specification labels its claims, and each one I re-ran agrees, but for finding 1's count of aliases.
- §4.13: ruff, format and mypy are green on the copy (EXECUTED). Ruff stays at its lock pin, 0.17.1 (READ, `uv.lock`), which runs TID252 with `ban-relative-imports = "all"` and its unsafe fix (EXECUTED). Its config lives in `pyproject.toml`'s `[tool.ruff.lint]`, which has no `per-file-ignores` table yet (READ).
- §5.6: this is the structural pre-build review the Kind line asks for. Nothing touches the guest's imports or exports, the artifact set or the build recipe.
- §7: nothing tripped. No `.github/` or `release/` file changes (step 4b: none to read).

## Disposition (filled in by the author, then confirmed by the reviewer)

1. to 7. Lows with fix text, and a note; they need no round.

## Verdict

May be built as written: no High or Medium stands. The builder applies the fix text of Lows 1 to 6, and keeps the guest package relative as Decision 3 recommends.
