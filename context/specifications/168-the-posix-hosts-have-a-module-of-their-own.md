# 168: The POSIX hosts have a module of their own

- **Status:** drafted 2026-10-30, to be reviewed before it is built (structural). The owner chose 0.1.3's scope on 2026-10-30 (decisions.md, "The scope of 0.1.3"), which carries this split from 0.1.2 (`../roadmap.md`, 0.1.3, "Carried from 0.1.2"). Its numbers were measured on a prototype of the split in a scratch copy of the package, outside the repository.
- **Date:** 2026-10-30
- **Owner:** Clay Gendron
- **Kind:** **structural**, runner code, parallel-safe, **a judge change** for the package's shape lists. By AGENTS.md's letter it adds no mutable, lock, private-API use, platform read or seam. It is structural by its subject: host code leaves `_platform.py`, the import graph gains a module, and it closes a structural review's Medium. Its pre-build review reads it against rows R3, R5 and R7 of `../reviews/README.md`. Code: `src/wasi_python/_platform.py`, a new `_platform_posix.py`, `_platform_common.py` (one function), `_private_dirs.py` (two calls). Judge: `ORDER`, `RUNNER_FILES`, `PLATFORM_HALVES`, their comments, and four unit files that name a moved name. Nothing an embedder sees changes.
- **Depends on:** nothing unlanded. Landed: 104 (the shape checks), 107 (one interface, chosen once), 108 (the structural rules), 116 (the two type-checker passes), 131 (the split this mirrors), 141 and 147 (code that moves here unchanged). Lands before 162, which adds the copy-on-write restore behind the platform object: its protocol line goes in `_platform.py`, its POSIX half in `_platform_posix.py`. A branch that changes the POSIX classes rebases onto this one. 159's `platform` flag reads changed paths under `src/wasi_python/` that begin `_platform`, so the new module keeps macOS on a pull request.
- **Research it stands on:** `../reviews/0.1.2-structural-review-2026-10-28.md` (Medium M1, rows R5 and R7); `131-the-platform-module-is-split.md` (the shape, and the proof of a move).

## The problem

`src/wasi_python/_platform.py` is 1,351 lines of its 1,500-line ceiling (EXECUTED, `wc -l` on `dev` `b6c4c899`). It stood at 1,016 at 0.1.1. In 0.1.2 it grew by 335 lines, almost all in the POSIX classes and their helpers (147, 150, 141). The 0.1.2 structural review's Medium M1 says the next POSIX change takes it past the ceiling, and the split is then done under pressure. 162's copy-on-write restore is that next change.

By `ast` (EXECUTED, a scratch script over each top-level node): `_Posix` is 444 lines, `_Linux` 144, `_Darwin` 142, and the helpers only they run about 400 more. The interface, the choice and what callers read are about 200.

## Decisions

### 1. One module, `_platform_posix.py`, below `_platform.py`

The POSIX classes and everything only they run move to `src/wasi_python/_platform_posix.py`. `_platform.py` keeps the interface, the choice and the door callers use. Each host family now has its module, as Windows has since 131. The name begins `_platform`, so R5's platform modules, the rules' lists and 159's flag all cover it.

The imports point one way. `_platform_posix` imports `_platform_common` and `_process`, and `_wasmtime_ffi` late inside `_wasmtime_base`, as `LATE_ANYWHERE` allows. `_platform` imports both host modules. Neither host module imports the other. `ORDER` gains `"_platform_posix"` between `"_platform_windows"` and `"_platform"`; `LATE` is unchanged.

On the prototype (EXECUTED, after `ruff format`): `_platform.py` **211** lines, `_platform_posix.py` **1,165**, `_platform_common.py` **365** (358 today), `_platform_windows.py` **502**, unchanged. `ruff check` clean; `mypy` "no issues found in 29 source files"; `tests/harness/typecheck.py` "both passes are clean".

### 2. What moves where

A name moves when only the POSIX classes run it, or such a name needs it. It stays when a caller outside the platform modules reads it from `_platform`, or it is the interface or the choice.

**To `_platform_posix.py`, forty names, byte for byte** (`_platform.py:112–190` and `:255–1308`), each with its comment:

- the classes `_Posix`, `_Linux`, `_Darwin`, `_Entry`;
- `_DIR`, `_DIR_OPEN`, `MAX_LINKS`, `_CACHE_DIR_OPEN`, `_CACHE_FILE_OPEN`, `_FD_NAMES`;
- the seven `_ACL_*` constants, `_OVERFLOW_UID`, `_ROOT_ADVICE`, `_ROOT_LIST_ADVICE`, `_CACHE_HINT`, `_OWNED_RULE`, `_OWNED_HINT`;
- the way's judge: `_way`, `_listed_writer`, `_principal`, `_advice`, `_owner_trusted`;
- the steps by descriptor: `_fd_name`, `_writable`, `_real_dir_at`, `_remove_at`, `_enter`;
- Linux's: `_TRAP_SIGNALS`, `_TRAP_SIGNALS_X86_64`, `_pyapi`, `_DlInfo`, `_load_base`, `_handler_base`, `_wasmtime_base`.

**Stays in `_platform.py`:** the docstring, whose list of every difference stays where a reader starts; `_same_file`, `_refuse_forked`, `_close` (read by `_private_dirs`, `runner`, `_call`); `_WASM_STACK`, `_HOST_ROOM`, `_THREAD_STACK` (imported by `_engines` and `_home`); `_TRAP_HANDLERS_REPLACED` (imported by `_call` and `_sessions`); `_Platform`; the three delegates; `_select`; `PLATFORM`; `_conforms`, which holds `_Darwin` and `_Posix` to the protocol under the type checker.

### 3. `_flags` goes below both, with a delegate

`_flags` builds `_DIR` and the cache's open flags at the POSIX module's top level. `_private_dirs.py:38` and `:173` run it on every system, with `O_BINARY`, a Windows flag. The POSIX module may not import `_platform.py`, and Windows runs `_flags` too. So it moves to `_platform_common.py`, as `_rewritten` did. `_platform.py` gains the delegate `_open_flags(*names)`, and `_private_dirs.py`'s two calls read `_platform._open_flags(…)`. A function never crosses a module by import, and a runner name is defined once, so the delegate has its own name.

### 4. The door stays the door

`_platform.py` imports `_Darwin`, `_Linux` and `_Posix` by name (classes, which the by-name rule allows). It keeps `Identity` and `_Walked` re-exported with the `as` form, so `_call.py:30`, `_sessions.py:38` and `_places.py:21` change nothing. `_select` is unchanged to the byte. The docstring gains one sentence: the POSIX classes live in `_platform_posix.py`.

The new module's docstring says what it holds, that only the platform module imports it, and that it reads no platform. It names neither `sys.platform` nor `os.name`: the platform rule reads every line.

### 5. No seam; the tests follow the names

No test patches a name of `_platform` (READ, `grep -rnE "setattr\(_platform\b" tests/`: none). The patches are attributes of the instance `_platform.PLATFORM`, which the seam rule leaves out. `SEAM_ALLOWED` is unchanged.

The tests name each moved name by its new module, as 131's did (READ, `grep -rn` over `tests/`):

- `tests/unit/test_runner_threads.py`: `_Posix` (101, 126), `_Linux` (119, 400), `_Darwin` (127, 412, 422), `_pyapi` (140, 143);
- `tests/unit/test_runner_calls.py`: `_Linux` (342), `_Darwin` (356);
- `tests/unit/test_runner_module_caches.py`: `_Linux` (289), `_Darwin` (291);
- `tests/unit/test_runner_module_cache_read.py`: `_Entry` (554);
- each imports `_platform_posix`.

No expectation changes. Every `_platform._WASM_STACK` in the judge stays. `_not_used`'s warning keeps its `stacklevel`: a moved method adds no frame.

### 6. What the judge needs, and what it does not

- `ORDER`: Decision 1. `RUNNER_FILES`: `"_platform_posix.py"`.
- `PLATFORM_HALVES`: `"_platform_posix": ("_platform.py",)`, and `_platform_common`'s importers gain `"_platform_posix.py"`. The row is seen failing first (Design, step 3).
- The comments above `PLATFORM_MODULE` and `PLATFORM_HALVES` are rewritten in words: `_platform.py` holds the interface and the choice, `_platform_posix.py` the POSIX hosts, `_platform_windows.py` Windows, `_platform_common.py` what both run.
- Unchanged: `_platform_hits`, `LATE`, `SEAM_ALLOWED`, `LONG_FUNCTIONS` (no function changes length; the longest moved is `_remove_at`, 76), `ALLOWED`, `tests/harness/typecheck.py`, `pyproject.toml`'s mypy settings, `tests/public_api.txt`, the `ignores` metric (3).

### 7. The next cut is named, not made (decided; the owner's alternative is to make it now)

The POSIX module starts 335 lines under the ceiling, and 0.1.2 alone added 335 lines of POSIX code. So the next cut is named now. `_Linux` with its trap-check helpers goes to `_platform_linux.py`, about 230 lines. `_Darwin` with the four `_ACL_*` constants only it reads goes to `_platform_darwin.py`, about 180. `_platform_posix.py` is left near 805 (estimated from `ast` sizes). The rule: a specification that would take `_platform_posix.py` past 1,350 lines makes that cut first, as 129's review made 131 a precondition.

Reason: this specification is one move of whole classes, with every verdict the same before and after, so one script proves it. The per-host cut is a second move of the same kind. The owner's alternative, three modules now, costs two more `ORDER` entries, two more `PLATFORM_HALVES` rows and two docstrings, and saves a later specification.

## Intent

The POSIX hosts live in one file of their own, as Windows does. `_platform.py` keeps the interface, the one choice and the door, at about 210 lines, so host code no longer grows it. The import graph stays acyclic. Nothing an embedder sees changes, and no verdict moves.

## Design

### Files

- `src/wasi_python/_platform_posix.py` (new, about 1,165 lines): Decision 2's names, `_flags` read as `_platform_common._flags`.
- `src/wasi_python/_platform.py` (about 211): the rest, Decisions 3 and 4.
- `src/wasi_python/_platform_common.py`: `_flags`; its docstring names it.
- `src/wasi_python/_private_dirs.py`: two calls.
- The judge: Decisions 5 and 6.
- `context/changes/168-the-posix-hosts-have-a-module-of-their-own.md`: the news file.

Comments and docstrings name no specification, review or `context/` path.

### The order of the moves

1. **The common half.** Move `_flags`, add `_open_flags`, change the two calls. Run the shape checks and `tests/unit/test_runner_sweep.py`.
2. **The POSIX module.** Move the forty names, retarget the tests, update the three lists. `ruff format`, `ruff check`, `tests/harness/typecheck.py`.
3. **The halves row, seen failing.** A planted `from . import _platform, _platform_posix` in `_home.py` turns `test_only_the_platform_modules_import_its_halves` red. On the prototype: "_home.py:14: imports _platform_posix past the platform module" (EXECUTED). Removed, it is green.
4. **The move is a move.** A scratch script compares `ast.dump` of every top-level name of the base's `_platform.py` with its node after the split, `_platform_common._flags` read back as `_flags`. On the prototype (EXECUTED): "53 top-level names on the base; 41 moved; differ: []; gone: []; new: ['_open_flags']".
5. **The words.** The docstrings and the rule comments.

### The news file

Under `### Changed`: **The POSIX hosts have a module of their own** (spec 168). `_platform.py` held the POSIX, Linux and macOS hosts at 1,351 of its 1,500 lines; they are now `_platform_posix.py`, and `_platform.py` keeps the interface, the choice and the door at about 210. Nothing an embedder sees changes. No package row. Every claim list empty; the judge-hash line names the changed judge files.

## Scope

**In:** Decisions 1 to 6, and the news file.

**Out:** any change of behaviour; the per-host cut (Decision 7); `_call.py` at 1,361 lines, the other module M1 names; 162's restore; a snapshot file's access lists; `context/reviews/README.md`'s R5 sentence ("the two below it" becomes three at the pre-build disposition); `../roadmap.md`.

## Acceptance criteria

1. **Sizes.** `wc -l` of the four platform modules within 30 lines of 211, 1,165, 365 and 502, recorded (EXECUTED). `test_no_module_under_src_is_over_the_line_ceiling` green, `ALLOWED` empty.
2. **The direction.** `test_the_runner_modules_import_in_the_written_order`, `test_a_module_imports_by_name_only_what_never_changes` and `test_every_runner_name_is_defined_in_one_module` green, `ORDER` as Decision 1 says, `LATE` unchanged.
3. **The choice.** `test_the_platform_is_chosen_once` green; `git diff` against the base shows no line of `_select`; `test_only_the_platform_modules_import_its_halves` green, and seen failing under step 3's fault, the hit line recorded.
4. **A move.** Step 4's script reports no difference and one new name, `_open_flags`; its output recorded.
5. **Types.** `test_src_type_checks_under_mypy_strict` green; `tests/harness/typecheck.py` "both passes are clean"; `ignores` unchanged.
6. **No seam, no long function.** `test_the_judge_patches_the_runner_only_through_the_process_object`, `test_no_function_is_over_eighty_lines`, `test_no_lock_is_made_at_module_level_outside_the_process`, `test_no_mutable_is_bound_at_module_level_outside_the_process` and `uv run pytest tests/lint` green, `SEAM_ALLOWED` and `LONG_FUNCTIONS` unchanged.
7. **Nothing public.** `tests/harness/api.py --check` exits 0 with `tests/public_api.txt` unchanged; `test_api_lists_every_module_of_the_package` green.
8. **The renamed tests.** The unit files `test_runner_grants.py`, `test_runner_threads.py`, `test_runner_calls.py`, `test_runner_sweep.py`, `test_runner_module_caches.py`, `test_runner_module_cache_read.py` and `test_snapshot.py` give the same pass and skip counts on the branch as on the base, both recorded. On the prototype and its base: 254 passed, 34 skipped, each (EXECUTED).
9. **Every host runs it.** The pull request's run is green on Linux, Windows and macOS with no `GROWTH` line, its id recorded. macOS runs by 159's `platform` flag, or the `ci:full` label before 159 is built: `_Darwin` runs only there.

## Landing notes

To be written at the landing.
