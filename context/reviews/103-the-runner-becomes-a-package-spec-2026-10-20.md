# Review of 103 — The runner becomes a package: one module per concern

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent (pre-build reviewer for the chain 102–107)
- **Reviewed:** the specification as drafted (`context/specifications/103-the-runner-becomes-a-package.md`
  at `a4f31c8` on `claude/gallant-ride-9nxxmn`; the tree's `src/wasi_python/` is main's `a9064a2`
  state, 102 not yet applied)
- **Run:** none (pre-build review of the draft)
- **Re-ran:** `uv run pytest tests/checks/test_rules.py -k "specifications or open_question" -q
  -p no:cacheprovider` → 3 passed, 41 deselected, exit 0 (EXECUTED). `uv run python
  build/103/map.py` → 355 names mapped, 0 missing, 0 extra, 6,241 of 6,241 lines, two `!!!`
  edges (EXECUTED). `uv run python build/103/sites.py` → the per-edge qualified-site table
  (EXECUTED). `uv run python build/103/count_globals.py src/wasi_python/runner.py` → locks 12,
  mutable 40, hooks 8, class attrs of `_epoch_ticker` `_active _count _thread _cond`, global
  statements at 1426–1428 and 3441 (EXECUTED). `uv run python build/103/dups.py` → ten names
  shared with `mounts.py` and `tools.py` (EXECUTED). `wc -l src/wasi_python/*.py` → `runner.py`
  6,241, `mounts.py` 2,235, `tools.py` 2,450 (EXECUTED). Time box: 25 minutes, parallel-safe.

## Acceptance criteria against evidence

1. **Checks seen failing first** — not yet evidenced (pre-build): the five checks are named with
   their first failures. Check 1's two assertions cannot both pass as written (finding 3); check 1's
   walk meets a lock the spec does not name (finding 2).
2. **Every name once** — met on `a9064a2`: `map.py` maps 355 names, 0 missing, 0 extra
   (EXECUTED); the per-module counts sum to 355 (18+32+12+18+32+19+53+18+78+52+23, READ). Not met
   on the base the spec stacks on: 102 deletes `_set_async_stack`, `_wasmtime_version` and
   `_context_address` (`102-the-engine-seam.md:530,544`, READ), so the count there is 352 and
   criterion 2's "363 found" is 360 (finding 1).
3. **The order holds** — met as drafted: `map.py`'s edge list has exactly two upward edges,
   `_places -> runner: ['Defaults']` and `_home -> _call: ['_Call']` (EXECUTED); `_check_places`
   uses `Defaults` as an annotation only and reads `limits.file_calls`, `limits.open_files`
   (`runner.py:1660–1680`, READ); `_stack() -> list[_Call]` is annotation-only (`runner.py:3280`,
   READ). `tools.py` imports nothing from the package at module level; `mounts.py` imports
   `_Call` under `TYPE_CHECKING` (`mounts.py:51`) and `runner` inside `_Files.__init__`
   (`mounts.py:631`) (EXECUTED, grep); `cli.py:118` imports `Grant` late. No hidden cycle in the
   `_home`/`_call`/`_sessions`/`_places` quartet: every runtime reference points down the order.
4. **Verbatim** — the acceptance is checkable: `--color-moved=dimmed-zebra` plus the residue
   script's categories (import, docstring, prefix-stripped, hook body, alias, "Last:") name every
   permitted non-move line, and the uncategorised residue must be empty (READ, Decision 8).
5. **The fork hook** — partly met: today's `global` statement names 15 names (`runner.py:1426–1428`,
   EXECUTED); 15 minus `runner.py`'s two is 13, as the spec says; the 12 module-level locks of
   `runner.py` are those `count_globals.py` lists, and `_pending_warnings_lock` is the one the hook
   does not touch (EXECUTED). `__init__.py:151 _defaults_lock = threading.Lock()` is a thirteenth
   module-level lock in the package that the check's walk meets and the spec does not name
   (finding 2). "16 entries" counts four non-locks (finding 3).
6. **The judge's files** — met as a list: the 21 files that reach `runner._…` by grep plus
   `api.py` (`runner.CACHE_ENV`, line 1049), `paths.py:258` (`wasi_python._ARTIFACT_DIR`) and
   `test_api.py:29–44` (four `setattr` patches, three `_ARTIFACTS_ENV` reads) are 24 (EXECUTED,
   grep). The six names that stay through `runner` match the grep's residue (`_checked`,
   `_check_tools`, `_current_defaults`, `_pool`, `_pool_lock`, `_stop_async_calls`; `__file__`
   goes with the widened `_defaults_loads`) (EXECUTED). Two rows name functions 102 deletes
   (finding 1).
7. **Sameness** — the claim file's keys `spec`, `new`, `units` are keys `sameness.py` accepts
   (`sameness.py:293–294`, READ); a `new` entry may be a node or a file (`sameness.py:72`, READ).
   Met as a design.
8. **Size** — met as a design: the largest module is `_call` at 1,202 moved lines (EXECUTED) plus
   its imports; 106 puts `_platform.py` near 850 (`106:203`, READ), under the ceiling. `mounts.py`
   2,235 and `tools.py` 2,450 reproduce (EXECUTED).
9. **Lint and the public surface** — met as a design: `tests/public_api.txt` names no runner
   module (its only module path is `wasi_python.cli:main`, line 284, EXECUTED);
   `reexport_errors` refuses a public name bound from a name starting with `_`, not from a module
   starting with `_` (`api.py:474–491`, READ), so `from ._call import Completed` passes;
   `docstring_hits` subtracts public names before flagging (`api.py:632–642`, READ), so
   `_artifacts.py` in `INTERNAL_FILES` does not make `artifacts` look internal.
10. **The release** — the chain's one dispatch; nothing to evidence here.

## Findings, most severe first

1. **The tables stand on main's tree, not on the base the spec is stacked on** (Status line;
   Decision 1's `_engines` and `_call` rows; the move table's rows `4085–4117`, `4690–4858`,
   `3287–3456`; Decision 5's rows for `test_runner_calls.py` and `test_runner_cancel.py`;
   criterion 2) — every number is EXECUTED on `a9064a2`, while 102, which this file depends on,
   deletes `_set_async_stack` and `_wasmtime_version` (`102:544`) and `_context_address`
   (`102:530`), and rewrites `_wasmtime()`'s import (`102:562`) and `mounts.py`'s
   `_get_fuel`/`_set_fuel` (`102:91–92`).
   Failure: the builder on 102's tip finds 352 names, not 355; criterion 2 expects 363 and reads
   360; `test_runner_calls.py` is told to reach `_engines._set_async_stack` and
   `test_runner_cancel.py` `_call._context_address`, which do not exist; 104 and 106 read this
   module list as their contract and inherit three ghost names. Medium. Closes when the
   tables are re-measured on 102's reviewed tip (the scripts take the file path; `git show
   <102 tip>:src/wasi_python/runner.py`) and the three names are struck with the counts restated,
   or when the Status line says the tables are on `a9064a2`, names the three as gone by 102,
   and criterion 2 reads "352 + 8 = 360".
2. **Check 1 meets `__init__.py`'s `_defaults_lock` and the spec does not say what it does with
   it** (Decision 4, "Check 1"; `src/wasi_python/__init__.py:151`) — the walk covers "every
   `wasi_python.*` module in `sys.modules`" and asserts every lock found is in `RESET_BY_FORK`;
   `NOT_RESET` holds `_pending_warnings_lock` alone; 104's prototype counts 14 locks, naming
   `_defaults_lock` as the fourteenth (`104:36–37`, READ) and takes it into `_Process`
   (`104:129`).
   Failure: a walk that includes the package root finds `_defaults_lock`, which is in neither
   list, and the check fails on its first run; a walk narrowed to submodules to make it pass
   hides one module-level lock from the enumeration, the omission class the check exists to end,
   and the CHANGELOG's "a unit check finds every module-level lock" is not true. Medium. Closes
   when Decision 4 says the walk includes the package root, `NOT_RESET` names
   `("wasi_python", "_defaults_lock")` with "never reset today; spec 104 takes it into
   `_Process` (group I)", the floor reads "at least 14", and criterion 5 reads "`NOT_RESET` two".
3. **Check 1's two assertions cannot both pass as written** (Decision 4, "Check 1"; criterion 5)
   — `RESET_BY_FORK` has 16 entries, of which `_compiling`, `_zips`, `_sessions` and
   `_reaper_queue` are a dict, a dict, a `WeakSet` and a `SimpleQueue` (EXECUTED,
   `count_globals.py`), never found by a walk for lock types, so "every lock in `RESET_BY_FORK`
   was found and its `id` changed" fails on four entries; and the `ast` assertion asks the
   hook's `global` names plus `_module.name` targets to equal "`RESET_BY_FORK` minus the three
   class attributes" while only `_cond` is in the list and the hook's nested targets
   `_engines._epoch_ticker._thread`, `._active` and subscript targets (`_call._tool_threads[...]`,
   `_engines._counts[...]`, `_platform._fork[...]`) need a stated rule.
   Failure: the builder cannot write the check from the text; either assertion is loosened
   silently. Low, with its fix: two lists, `LOCKS_RESET_BY_FORK` (12: the eleven locks and
   `_engines._epoch_ticker._cond`) with the id-change assertion, and `REBOUND_BY_FORK` (4) covered
   by the `ast` assertion only; the `ast` assertion collects `global` names and depth-one
   `_module.name` `Attribute` targets, skips `Subscript` targets and attributes of attributes,
   and requires the set to equal the two lists' union minus `_cond` (15); criterion 5 reads
   "12 + 4 entries".
4. **`Session` stays in `runner.py` against the memo's table, and the reason is not written**
   (Decision 1's refinements; the memo's H1 row `_sessions.py … Session`) — the six bullets name
   every other departure; this one is the largest (457 lines, `runner.py:5785–6241`).
   Failure: 104's and 106's builders, told the memo's table is the start, look for `Session` in
   `_sessions.py`. Low, with its fix, a seventh bullet: "`Session` stays in `runner.py`: its
   constructor reads `_checked`, `_current_defaults`, `_refuse_forked` and `_open_session`
   (EXECUTED); in `_sessions.py` the first two would import upward, as `_checked` must stay
   beside `DEFAULTS`."
5. **Three numbers do not reproduce** (Design, the files table and the move table's
   `_artifacts.py` row; Decision 4, "the five it mutates in place") — `__init__.py`'s block
   from `_ARTIFACT_DIR` (line 36) to the end of `artifacts()` (line 125) is 90 lines, not "lines
   29–112, 101 lines" (lines 29–32 are imports and 34 is `__version__`, which stay; EXECUTED,
   `sed -n 36,125p | wc -l`); "the five it mutates in place" lists nine names and omits
   `_home._stack_size_found`, which the hook clears (ten). Low, with its fix: "`__init__.py`
   36–125, 90 lines", "`_artifacts.py` 117 + 90", "the ten it mutates in place" with
   `_stack_size_found` added.
6. **Decision 2's rule leans on a condition it does not state: a class or constant the judge
   patches by `setattr` must be read only in its defining module** (Decision 2, "How a name is
   reached"; check 3) — a from-imported copy in another module never sees the patch. It holds
   today: of the 45 names tests patch through `runner` (EXECUTED, grep over `tests/`), the
   classes and constants among them (`MAX_RESPONSE`, `_REMOVE_BUDGET`, `DEFAULTS`) are read in
   their own module only (EXECUTED, `map.py`'s edges), and `_after_walk` is a hook, reached by
   attribute. Low, with its fix: one sentence in Decision 2 naming the condition and the three
   names, and one assertion in check 3: for every `setattr(<module>, "NAME", …)` in `tests/`
   whose object is a class or constant, no package module from-imports `NAME`; or the sentence
   alone, naming 104 (which moves the seams off module globals) as the closer.
7. **`api.py`'s tables gain the ten new modules but not 102's `_wasmtime_ffi.py`**
   (Decision 5's `tests/harness/api.py` row; `102-the-engine-seam.md` names `INTERNAL_FILES`
   nowhere, EXECUTED grep) — after the chain, `internal_names()`, `internal_constants()` and
   the internal-module rule (`api.py:509–545, 611, 641`) skip the adapter.
   Failure: an adapter name in a public docstring is not refused. Low, with its fix: the row
   reads "the ten new modules and `_wasmtime_ffi.py` (`wasi_python._wasmtime_ffi`), unless
   102's build adds them, in which case 103 adds nothing for it and says so".

## Constitution checks

- §4.3, §4.4, §4.6: no guest import, export or artifact byte changes; the move is host-side
  Python only. Holds.
- §4.9: the new checks count lines, names, ids and `ast` nodes; none reads a clock. Holds.
- §4.10: every number is labelled; the ones that do not reproduce are findings 1 and 5.
- §4.13: `uv` only; `ruff`'s `I` rule orders the new import blocks. Holds.
- §4.14: a stacked build on 102's reviewed tip, the base commit named at build time. Holds,
  subject to finding 1 (the tables must be of that base).
- §4.15: no default loosens. Holds.
- §5.2: no open choice; the `_pending_warnings_lock` omission is handed to 104 in writing,
  which takes it (`104:94`). Holds.
- §5.6: the pre-build review required for the runner's code is this one.
- §7 never-do list: nothing tripped; no patch, no unpinned fetch, no copied code, no commit.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. The tables stand on main's tree, not on the base the spec is stacked on — **fixed**: the
   Research line says the tables are measured on `a9064a2` and reconciled with 102's text, names
   the three names 102 deletes with their adapter replacements, says 102's `mounts.py` edits may
   shift the cited line numbers (the builder re-finds by text), and asks the builder to re-run
   `map.py` on 102's tip; The problem and the move table read 355 on `a9064a2`, 352 on 102's tip;
   the three rows mark each name "gone on 102's tip"; the `_engines.py` and `_call.py` headings
   and Decision 1 rows say 16 and 77 and name `ffi.set_async_stack`, `ffi.version()`,
   `ffi.context_address`; Decision 5's `test_runner_calls.py` and `test_runner_cancel.py` rows
   drop the two names and say 102 re-pointed them to the adapter; criterion 2 reads 352 + 8 = 360.
   Also written in: `_wasmtime_ffi` is imported only inside functions, in 102's form, and check
   2 allows that late import anywhere (Decision 2, check 2).
2. Check 1 meets `__init__.py`'s `_defaults_lock` and the spec does not say what it does with it —
   **fixed**: Decision 4 says the walk includes the package root `wasi_python`; `NOT_RESET` has two
   entries, `("wasi_python._private_dirs", "_pending_warnings_lock")` "never reset today; spec 104
   decides" and `("wasi_python", "_defaults_lock")` "never reset today; spec 104 takes it into
   `_Process` (group I)"; the floor reads "at least 14"; the prose names `_defaults_lock` (line
   151) as the package's thirteenth module-level lock; criterion 5 reads "`NOT_RESET` 2".
3. Check 1's two assertions cannot both pass as written — **fixed** as the fix text says:
   `LOCKS_RESET_BY_FORK` (12: the eleven locks named one by one, and `_engines._epoch_ticker._cond`)
   carries the id-change assertion; `REBOUND_BY_FORK` (4: `_engines._compiling`, `_zip._zips`,
   `_sessions._sessions`, `_sessions._reaper_queue`) is covered by the `ast` assertion only; the
   `ast` assertion collects `global` names and depth-one `_module.name` `Attribute` targets, skips
   `Subscript` targets and attributes of attributes (each example named), and requires equality
   with the union minus `_cond`, 15 names; criterion 5 reads "12 entries, 4 and 2"; Decision 4
   also says check 1 is 103's until 104 lands and 104 names the retirement (Scope too).
4. `Session` stays in `runner.py` against the memo's table, and the reason is not written —
   **fixed**: a seventh bullet in Decision 1's refinements with the fix text (457 lines,
   `runner.py:5785–6241`; `_checked`, `_current_defaults`, `_refuse_forked`, `_open_session`;
   the first two would import upward).
5. Three numbers do not reproduce — **fixed**: "`__init__.py` 36–125, 90 lines" in the files
   table and the move table, "117 + 90" in Decision 1's `_artifacts.py` row, "the ten it mutates
   in place" with `_stack_size_found` added in Decision 4.
6. Decision 2's rule leans on a condition it does not state — **fixed**, both halves: Decision 2
   states the condition and names `MAX_RESPONSE`, `_REMOVE_BUDGET` and `DEFAULTS` (45 patched
   names, EXECUTED) with `_after_walk` as a hook reached by attribute; check 3 gains the
   assertion (for every `setattr(<module>, "NAME", …)` in `tests/` whose object is a class or a
   constant, no package module from-imports `NAME`), named as 103's until 104 moves the seams and
   retires it by name.
7. `api.py`'s tables gain the ten new modules but not 102's `_wasmtime_ffi.py` — **fixed**: the
   `tests/harness/api.py` row reads "the ten new modules and 102's `_wasmtime_ffi.py`
   (`wasi_python._wasmtime_ffi`), which 102 names in neither table (EXECUTED, grep), unless 102's
   build adds them, in which case 103 adds nothing for it and says so in the landing notes".

## Verdict

Builds once the two Mediums are written into the text: the tables re-measured on, or
reconciled with, 102's reviewed tip (finding 1), and `_defaults_lock` named in check 1's lists
(finding 2); the five Lows are write-ins whose fix text is above.
