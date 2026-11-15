# 178: The runner's entry points share one argument check and one async wrapper

- **Status:** built 2026-11-14, in review; drafted 2026-11-14; asked for by the owner on 2026-11-14 ("Start building", `context/decisions.md` "0.1.5's scope" once that lands; today it is on the branch of pull request #105).
- **Date:** 2026-11-14
- **Owner:** Clay Gendron
- **Kind:** **structural**, runner code, parallel-safe, **a judge change** for the package's shape lists and for five test files that name a moved name. By AGENTS.md's letter it adds no module-level mutable or lock, no private-API use, no platform branch and no seam, and it takes no module or function past its ceiling. It is structural by its subject and by its reservation: the import graph gains a module, and it closes the 0.1.3 and 0.1.4 structural reviews' Medium M1. Reviewed before it is built against the eight rows of `../reviews/README.md` (Decision 7). Code: `src/wasi_python/runner.py` and a new `src/wasi_python/_entry.py`. Judge: `ORDER` and `LATE`, `RUNNER_FILES`, `LONG_FUNCTIONS`, and the call sites of Decision 5. Nothing an embedder sees changes, and no verdict moves.
- **Depends on:** nothing unlanded. Landed: 104 (the runner is a package, and its order check), 105 (one owner for the process state), 108 (the structural rules), 142 (the 80-line allowance judged by length), 162, 163 and 164 (the code that moves, as they left it). It is the first half of 115 (`../roadmap.md:19`); 115's second half, a typed argument record and docstrings that say "as for `run`", builds on this one.
- **Research it stands on:** `../reviews/0.1.3-structural-review-2026-11-01.md` (M1, M2, L6, L7) and `../reviews/0.1.4-structural-review-2026-11-05.md` (M1 carried, "the first `src/` change of 0.1.5"); the roadmap's reservation (`../roadmap.md:21`); `168-the-posix-hosts-have-a-module-of-their-own.md` (the shape of a move and its proof); `src/wasi_python/runner.py` read whole, and the modules it imports, on `dev` at `25e49df5`; the rules in `tests/checks/test_rules.py`, `tests/unit/test_runner_package.py` and `tests/harness/api.py`, read and run on the same commit.

Labels: EXECUTED, run and seen; READ, read from a file, cited; INFERRED, reasoned. Line numbers are `runner.py`'s at `25e49df5` unless a file is named.

## The problem

`runner.py` is 1,476 lines of its 1,500-line ceiling, 98% (EXECUTED, `wc -l`). Two structural reviews in a row named it Medium M1, and the second found its promise "before 0.1.4" lapsed (READ). The next public argument of the run family costs about ten lines of docstring in each of three or four entry points, so it would take the module past the ceiling. That change would then split the module under pressure, or add `runner.py` to `ALLOWED`, which the ceiling check's comment permits (READ, `tests/checks/test_rules.py:168-172`).

Two things in the module are not entry points. The argument check (`_checked`, 80 lines, with `_check_tools` and `_ToolArgs`) is shared by `run`, `run_async` and `Session.__init__` already. The async machinery (`_check_executor`, `_submit` and the pool it keeps, the registry of running calls in `process().live`, and the exit hook that stops them) is shared by both `run_async`s. Together they are lines 546 to 858, 313 lines (EXECUTED, `ast`).

One thing is written twice. `run_async` (`:477-543`) and `Session.run_async` (`:1385-1435`) each claim an `OutputFeed`, wrap `on_output` in `_Late`, register the call's event in `live` under `live_lock`, submit in a copy of the context, await, run the cancel dance, take the event out of `live` and end the feed (READ). A fix to one copy has to be made in the other by hand.

## Decisions

### 1. One module, `_entry.py`, below `runner.py`

`src/wasi_python/_entry.py` holds what the run family's entry points share. In `ORDER` (`tests/unit/test_runner_package.py:24-46`) it stands between `_sessions` and `runner`. At runtime it imports only modules before it: `_limits`, `_outputs`, `_places`, `_results`, `_snapshot`, `_call` (`_CheckedCall`) and `_process` (`process`). It imports neither `_sessions` nor `runner` at runtime. Under `TYPE_CHECKING` it names `Defaults` from `.runner`, `Completed` from `._call`, `OutputChunk` from `._outputs` and `Tool`, `ToolCall` from `.tools`, as `_places.py:26` already names `Defaults` (READ). The order check skips imports under `TYPE_CHECKING` (READ, `test_runner_package.py:126-127`), and `mypy --strict` reads such a cycle without complaint, so the runtime graph stays acyclic. As in `runner.py`, `asyncio` and `concurrent.futures` are imported inside the functions that use them, or under `TYPE_CHECKING`.

The name says what it is for: the entry points' shared work. It is not "arguments", since the pool and the async wrapper are not arguments. A second module (checks apart from the pool) was weighed and refused: both halves together are about 415 lines, and two modules cost two `ORDER` entries for no reader's gain.

### 2. What moves

Ten top-level names move from `runner.py` to `_entry.py`, in this order, each unchanged but for Decision 3:

| name | lines at `25e49df5` | length |
|---|---|---|
| `_check_executor` | 546-557 | 12 |
| `_submit` | 560-601 | 42 |
| `_pool_future_done` | 604-610 | 7 |
| `_register_exit_hook` | 613-629 | 17 |
| `_stop_async_calls` | 632-657 | 26 |
| `_keep_release` | 660-677 | 18 |
| `_take_live` | 680-687 | 8 |
| `_checked` | 690-769 | 80 |
| `_ToolArgs` | 772-778 | 7 |
| `_check_tools` | 781-856 | 76 |

Lengths EXECUTED, an `ast` walk, def to last line. The reservation names seven; three more must go with them (READ): `_pool_future_done` is `_submit`'s done-callback, and `_register_exit_hook` and `_stop_async_calls` are the exit hook over the same pools and the same `live`, which `_keep_release` and `_take_live` write. Left behind, they would import `_entry` from `runner` and back, or split one protocol over two files.

Stay in `runner.py`: `Defaults`, `DEFAULTS`, `_current_defaults` (the public type, the binding `set_defaults` replaces, and the seam the judge patches), `_run_checked_flushed`, `stats`, `_ExitFlag` and `Session`.

Two names are new in `_entry.py`: `_serving` and `_awaited` (Decision 4).

### 3. The defaults are read in `runner.py` and passed down

`_checked`, `_check_tools` and `_submit` read the defaults through `_current_defaults` today (`:724`, `:846`, `:587`). `_entry.py` cannot call it: that would import `runner`. And the judge counts every read by patching `runner._current_defaults` (READ, `tests/checks/test_v1_4_public_api.py:417-430`, one read per call). So the read stays in `runner.py`, and what it read is passed:

- `_checked(..., limits: Defaults, ...)`: `limits` is required, keyword-only, where it was `Defaults | None = None`. Its first line, the fallback read, goes. `run` and `run_async` pass `limits=_current_defaults()`; `Session.__init__` already passes the `limits` it read (READ, `:1051`). Its docstring says the `limits` are the ones its entry point read, once. `_checked` becomes 79 lines.
- `_check_tools(host, tools, gate, max_tool_calls, limits: Defaults, *, max_tool_request_bytes=_UNSET)`: `limits` required. Its six lines that read once, whichever limit is unset, become four that read `limits` (`:845-850`). It becomes 74 lines.
- `_submit(executor, defaults: Callable[[], Defaults], fn, *args)`: it takes the reader, not a value, and calls it under `pool_lock` where it called `_current_defaults()`, so the newest `set_defaults` still sizes the pool (READ, `test_the_pool_takes_the_newest_size`). The callers pass `_current_defaults`, looked up in `runner.py` at the call, so a patched reader is the one the pool reads.

`run` gains the `limits=` line, so its listed length rises from 182 to 183, with that reason in the news file's `[claim.judge]` (`../reviews/README.md`, checklist item 4). The two ways to keep it at 182 were weighed and refused: folding `cache = …` into the `return` makes a line of 101 characters, past the 100 of `pyproject.toml:84` (EXECUTED); reading `cache_dir` before `_checked` changes which error a call with two bad arguments raises first.

### 4. One async wrapper, in two parts

The feed's claim must come before every argument check, and the rest after. A call refused for a bad argument has spent its feed today, and `test_a_feed_used_twice_is_refused` holds that (READ, `tests/unit/test_runner_streaming.py:388-400`). So the shared wrapper is a context manager that both coroutines enter first, and a coroutine both await last. Between them each entry point keeps its own checks, in today's order.

```python
@contextlib.contextmanager
def _serving(on_output: object) -> Iterator[None]:
    """The feed `on_output` is, claimed for one call before any check, and ended whatever the
    outcome, so its follower ends."""


async def _awaited(
    on_output: Callable[[OutputChunk], object] | None,  # checked: a callable, a feed, or None
    event: threading.Event,  # the call's cancel; it goes into `live` for the exit hook
    executor: concurrent.futures.Executor | None,  # checked by the caller
    defaults: Callable[[], Defaults],  # `_submit`'s reader of the pool's size
    build: Callable[[_outputs._Late | None, asyncio.AbstractEventLoop], tuple[Any, ...]],
    *,
    claim: Callable[[], None] | None = None,  # a session's claim of its turn
    release: Callable[[], None] | None = None,  # and its release, kept beside `event`
) -> Completed: ...
```

`_awaited` does, in this order, what both copies do today: get the running loop; `_register_exit_hook()`; `claim()` if given; `late = _outputs._Late.around(on_output)`; under `live_lock`, refuse if `exiting`, else `live[event] = None`; `_submit(executor, defaults, contextvars.copy_context().run, *build(late, loop))`, where `build` returns the function and its arguments with `late` in place of `on_output`; on any `BaseException` before the submit returns, `_take_live(event)` and `release()` if given, then raise; after it, `_keep_release(event, future, release)` if given; await the future, then `_Late.check(late)`; on `CancelledError`, a queued future is cancelled and `_take_live(event)()` runs the turn's release unless the exit hook ran it, and a running one gets `event.set()` and is awaited to its end before the error is raised; finally `_take_live(event)`. About 56 lines (INFERRED). For a call, `live[event]` stays `None`, so `_take_live(event)()` is a no-op, which is today's plain `pop` (READ, `:680-687`).

What each caller passes (INFERRED, the bodies to be written):

- `run_async`: `with _entry._serving(on_output):` around its body; inside, `_refuse_forked`, `event = threading.Event()`, `_entry._checked(..., event, ..., asynchronous=True, limits=_current_defaults())`, `cache`, `_entry._check_executor(executor)`, `wt`; then `build` returns `(_run_checked_flushed, wt, replace(checked, on_output=late), host, cache, artifacts, loop)`, and it returns `await _entry._awaited(checked.on_output, event, executor, _current_defaults, build)`. No `claim`, no `release`.
- `Session.run_async`: `with _entry._serving(on_output):`; inside, `_refuse_forked`, `self._turn_args`, `self._turn_io`, `_entry._check_executor(executor)`, `event = threading.Event()`; `build` returns `(_sessions._session_turn, state, data, fuel, deadline, output, event, loop, "turn", io._replace(on_output=late))`; it returns `await _entry._awaited(io.on_output, event, executor, _current_defaults, build, claim=lambda: self._claim(here=False), release=self._release_claim)`.

The order of every step with an effect is today's, in both (READ against `:477-543` and `:1385-1435`). The steps that move are the `_Late` wrap, which has no effect, and the session's `threading.Event()`, made before its claim instead of after. In `run_async` the running loop is got after `_engines._wasmtime()`, not before. That differs only for a coroutine stepped with no running loop where wasmtime-py cannot load.

### 5. No seam; the tests follow the names

No test patches a moved name (EXECUTED, `grep -rnoE 'setattr\(\s*(runner|_runner)\s*,\s*"\w+"' tests`: `DEFAULTS` four times, `_current_defaults` once, `run` three times, none of the ten). `SEAM_ALLOWED` is unchanged at 18 (`tests/checks/test_rules.py:1638-1667`); `_current_defaults` stays in `runner.py` and stays patched there, at `test_v1_4_public_api.py:423`. The seam rule covers `_entry` by its pattern (READ, `tests/harness/scan.py:3419`), so a later patch of an `_entry` name is red.

The calls of moved names, each retargeted to `_entry`, with no expectation changed (EXECUTED, `grep -rnoE 'runner\._\w+' tests`):

- `tests/checks/test_v1_4_public_api.py:396`: `runner._checked(...)` becomes `_entry._checked(..., limits=runner._current_defaults())`. Its assertion stands: after `set_defaults(new)`, the record has `new.memory_bytes`. The read the call makes is still counted by the same test's second half (one read for `run`, one for `run_async`).
- `tests/unit/test_runner_limits.py:122` and `tests/unit/test_runner_tools.py:854`: `runner._checked(...)` becomes `_entry._checked(..., limits=wasi_python.defaults())`.
- `tests/unit/test_runner_tools.py:176`, `:180`, `:181`: `runner._check_tools(...)` gains `wasi_python.defaults()` as its fifth argument; `:182`: `runner._ToolArgs` becomes `_entry._ToolArgs`.
- `tests/unit/test_runner_async.py:261`, `:265`: `runner._submit(None, abs, n)` becomes `_entry._submit(None, runner._current_defaults, abs, n)`.
- `tests/checks/test_v1_2_hostile_guest.py:2593`: `runner._stop_async_calls()` in the `STOPPED` program becomes `_entry._stop_async_calls()`, and the program's import line names `_entry`.

Each file imports `_entry` from `wasi_python`. These change call sites, not checks. The one judgement a reviewer should make is the first: `_checked` no longer reads the defaults itself, so the line cannot show that it does. What a call applies is the one `Defaults` its entry point read, since `limits` is required, and the count shows the entry point reads once (INFERRED).

### 6. What the judge needs, and what it does not

- `ORDER`: `"_entry"` after `"_sessions"`. `LATE`: `("runner.py", "_check_tools", "tools")` becomes `("_entry.py", "_check_tools", "tools")`, the same late import in its new file.
- `RUNNER_FILES` (`tests/harness/api.py:39-60`): `"_entry.py"` after `"_sessions.py"`. Not `DEFINING`: it defines no public name.
- `LONG_FUNCTIONS` (`tests/checks/test_rules.py:1691-1703`): `runner.py:run_async` lowered from 217 to its measured length, about 188 (INFERRED: 217 − 69 + 40). `runner.py:Session.run_async` deleted, at about 72 lines (INFERRED: 102 − 54 + 24). `run` raised from 182 to 183 (Decision 3), claimed; `Session.__init__` 187 unchanged. Net, the list loses one entry and about 130 listed lines.
- Unchanged: `ALLOWED` (empty), `LINE_CEILING`, `SEAM_ALLOWED`, `PROCESS_OWNER`, `MAY_IMPORT_MOUNTS`, `TOOLS`, `tests/public_api.txt`, `UNTYPED`, the `ignores` metric, `tests/release_shards.toml`.
- The rules that hold the move, each green before (EXECUTED, `-rA` on `25e49df5`) and after: `test_no_module_under_src_is_over_the_line_ceiling`, `test_no_function_is_over_eighty_lines`, `test_the_judge_patches_the_runner_only_through_the_process_object`, `test_no_lock_is_made_at_module_level_outside_the_process`, `test_no_mutable_is_bound_at_module_level_outside_the_process`, `test_no_module_level_name_is_bound_twice`, `test_api_lists_every_module_of_the_package`, and in `test_runner_package.py` `test_the_runner_modules_import_in_the_written_order`, `test_the_tool_modules_import_in_their_written_order`, `test_a_module_imports_by_name_only_what_never_changes` (so `runner.py` writes `_entry._checked`, never `from ._entry import _checked`) and `test_every_runner_name_is_defined_in_one_module` (so no moved name stays bound in `runner.py`, not even as an alias).

### 7. The eight rows

The scores are the 0.1.4 review's (READ); what this change moves:

- **R1 Contract** (Strong): unchanged. No public name, signature or docstring moves; the snapshot is the same; no failure changes type or order. L7 stands as written (Decision 8).
- **R2 Safety** (Strong): unchanged. Every argument is still checked before any side effect, in the same order (Decision 4). The live registration and the cancel dance are written once, so their next fix cannot miss a copy.
- **R3 Layering** (Strong): holds. One node joins the graph, below `runner`, importing only modules before it at runtime; one name under `TYPE_CHECKING` points up, as `_places.py` already does. No engine private API.
- **R4 Process state** (Strong): unchanged. No new mutable or lock. The moved code reads `process().pool_lock`, `pools`, `pool_done`, `live_lock`, `live` and `exiting` at each use, as before; both locks stay leaves in `_process.py`'s order (READ, `_process.py:18`). The meaning of a `live` entry, `None` for a call and `(future, release)` for a turn, is now written in one file.
- **R5 Portability** (Strong): untouched; no platform branch.
- **R6 Testability** (Adequate): unchanged. No seam added; `SEAM_ALLOWED` 18; `_current_defaults` stays the one defaults seam, handed to `_submit` as a parameter, the form R6 asks for. No branch only the judge takes.
- **R7 Evolvability** (Adequate, moving toward Weak): moves back toward Adequate. `runner.py` from 98% to about 73% of the ceiling; `LONG_FUNCTIONS` from seven entries to six and about 130 listed lines fewer, though `run` rises by one (Decision 3); `_checked` from 80 lines to 79. `mypy --strict` must still pass. M2 is not closed: `_checked` still takes every keyword, and the docstrings are still written four times (115).
- **R8 Operability** (Strong): unchanged. `stats()`, the records and the trap strings are untouched; the exit hook is the same code.

### 8. What the owner or reviewer decides

- **The feed's claim.** L7's first half (claim the feed after the checks, so a refused call leaves it unspent) is a change of behaviour that a test pins. This specification keeps today's order and leaves L7 carried. The owner may instead carry it here: `_serving` goes away, `_awaited` claims the feed, and `test_a_feed_used_twice_is_refused` changes its expectation, a judge change with its reason in the news file. Recommended: keep it out, and give L7 its own reserved line. The 0.1.5 preparation, when it retires 178's line, adds L7's: both halves, the feed claimed after the checks in `_awaited` and `output_keep`'s `TypeError`.
- **`test_v1_4_public_api.py:396`** (Decision 5). The reviewer judges whether the retargeted line plus the count is as strong as the line was. If not, the stronger check is the reviewer's to name.

## Design

### Files

- `src/wasi_python/_entry.py` (new, about 415 lines, INFERRED: 308 moved, a docstring, imports, `_serving` about 10, `_awaited` about 56): Decisions 1 to 4. Its docstring says in words what the module holds and why the defaults come from above.
- `src/wasi_python/runner.py` (about 1,100 lines, INFERRED: 1,476 − 313 moved − 5 import lines − 29 in `run_async` − 30 in `Session.run_async` + 1 in `run`). Its imports lose `atexit`, `functools`, `queue`, `NamedTuple`, and the modules `_places`, `_results` and `_snapshot`; they gain `_entry` on the line that names the others (EXECUTED, `grep` of each name outside the moved block: each appears only in its import line). `from ._snapshot import Snapshot` stays.
- The judge: Decisions 5 and 6.
- `context/changes/178-the-runners-entry-points-share-one-check.md`: the news file.

Comments and docstrings name no specification, review or `context/` path.

### The order of the moves

1. **The move.** Cut the ten names into `_entry.py`, make Decision 3's three edits, point every caller at `_entry`, update the imports and the shape lists. `ruff format`, `ruff check`, `tests/harness/typecheck.py`.
2. **The wrapper.** Write `_serving` and `_awaited`; rewrite the two coroutines' bodies onto them; set `LONG_FUNCTIONS` to the measured lengths.
3. **The order rule, seen failing.** A planted module-level `from . import runner` in `_entry.py` turns `test_the_runner_modules_import_in_the_written_order` red; the hit line is recorded; removed, it is green.
4. **The move is a move.** A scratch script, outside the repository, compares `ast.dump` of each moved name on the base with its node in `_entry.py`. It must report differences only in `_checked`, `_check_tools` and `_submit`, each Decision 3's edit, and two new names, `_serving` and `_awaited`.
5. **The tests.** Retarget Decision 5's call sites; run the files of criterion 7 on the base and the branch.

### The news file

Under `### For contributors`: the runner's argument checks and its async plumbing have a module of their own, and the two async entry points share one wrapper; nothing an embedder sees changes. No package row. Every claim list empty. `[claim.judge]` names each changed judge file with its reason, as 168's did.

## Intent

`runner.py` holds the entry points and the session, and nothing else, at about 73% of its ceiling, so the next public argument lands without a split under pressure. The argument check, the pool and the live registry live in one module below it. The async wrapper is written once. Nothing an embedder sees changes, and no verdict moves.

## Scope

**In:** Decisions 1 to 6, and the news file.

**Out:** any change of behaviour; L7, both halves (Decision 8); L6, the `_TurnKind` tuple, which the review said 178 may carry and which touches `_sessions.py`, not the entry points; 115's second half, the typed argument record and the shared docstrings; `_call.py` at 1,402 lines (93%); moving `_run_checked_flushed`, which `run` also calls; `../roadmap.md`, whose reservation line is the release's preparation to retire.

## Acceptance criteria

1. **Sizes.** `wc -l`: `runner.py` at most 1,150 and so under 1,350 (90%), `_entry.py` at most 460, both recorded (EXECUTED). `test_no_module_under_src_is_over_the_line_ceiling` green, `ALLOWED` empty.
2. **The order.** The four shape checks of `test_runner_package.py` green, `ORDER` and `LATE` as Decision 6 says; the order rule seen failing under step 3's fault, its hit line recorded.
3. **A move.** Step 4's script reports only Decision 3's three edits and the two new names; its output recorded.
4. **Long functions.** `test_no_function_is_over_eighty_lines` green; `LONG_FUNCTIONS` holds six entries, `run` 183 with its claim, `Session.__init__` 187, `run_async` at its measured length below 217, and no function of `_entry.py` past 80.
5. **No seam, no state.** `test_the_judge_patches_the_runner_only_through_the_process_object`, the lock and mutable rules and `test_no_module_level_name_is_bound_twice` green; `SEAM_ALLOWED` unchanged.
6. **The defaults.** `test_set_defaults_changes_what_run_reads` and `test_the_pool_takes_the_newest_size` green, with only Decision 5's one edit to the first.
7. **Behaviour.** With the artifact set, the same pass and skip counts on the base and on the branch, both recorded, for `tests/unit/test_runner_async.py`, `test_runner_streaming.py` (`test_a_feed_used_twice_is_refused` unchanged), `test_runner_sessions.py`, `test_runner_tools.py`, `test_runner_limits.py`, `tests/checks/test_v1_4_sessions.py -k "run_async or exit"`, and the async, cancel and exit rows of `tests/checks/test_v1_4_embedding.py` (`-k "async or cancel or exit"`) and `test_v1_2_hostile_guest.py`.
8. **Nothing public.** `tests/harness/api.py --check` exits 0 with `tests/public_api.txt` unchanged; `test_the_public_api_matches_its_snapshot` and `test_api_lists_every_module_of_the_package` green.
9. **Types and words.** `test_src_type_checks_under_mypy_strict` green, `tests/harness/typecheck.py` both passes clean, `ignores` unchanged; `ruff check`, `ruff format --check` and `uv run pytest tests/lint` green.
10. **The run.** The pull request's run green on Linux and Windows with no `GROWTH` line, its id recorded.

## Landing notes

Built 2026-11-14 on `spec/178-the-runners-entry-points-share-one-check`, from `142da9fa` (the spec and its pre-build review on `dev` at `25e49df5`), by an agent (Claude Opus 5.5), a sub-agent of the orchestrator's session. The pre-build review, `../reviews/178-the-runners-entry-points-share-one-check-spec-2026-11-14.md`, says it may be built as written; its fix text for Lows 1 to 4 and 6 is applied above (Decisions 1, 3, 4 and 8, criterion 7); Low 5 is a note for the pull request's review. L7 stays out, as Decision 8 recommends. The review's optional end-to-end row was not added.

Labels as above: EXECUTED, run and seen; READ; INFERRED.

- **Sizes (criterion 1).** `wc -l`: `runner.py` 1,476 → 1,114 (74% of the ceiling), `_entry.py` 419; all of `src/` 17,330 → 17,387 (EXECUTED). Both under the criterion's 1,150 and 460. The prototype's 1,101 and 412 differ by the two `build` lambdas, which `ruff format` writes one element a line, since neither tuple fits in 100 columns (EXECUTED).
- **Check first.** With `ORDER`, `LATE` and `RUNNER_FILES` edited before the module existed, `test_api_lists_every_module_of_the_package` was red ("api.py lists _entry.py, not one file under the package") and `test_the_tool_modules_import_in_their_written_order` red ("runner.py:818 (_check_tools imports tools late, not in LATE)"); both green after the move (EXECUTED).
- **The order (criterion 2).** Step 3's fault, a module-level `from . import runner` planted in `_entry.py`: `_entry.py:24 (_entry imports runner, not before it in ORDER)`; removed, green (EXECUTED). The four shape checks of `test_runner_package.py` green.
- **A move (criterion 3).** Step 4's script, `ast.dump` of each of the ten names in the base's `runner.py` against `_entry.py`: `_check_executor`, `_pool_future_done`, `_register_exit_hook`, `_stop_async_calls`, `_keep_release`, `_take_live` and `_ToolArgs` identical; `_submit`, `_checked` and `_check_tools` differ (Decision 3's edits, with `_checked`'s and `_submit`'s docstrings); none left in `runner.py`, none lost; new in `_entry.py`: `_awaited`, `_serving` (EXECUTED).
- **Long functions (criterion 4).** `ast` lengths, def to last line: `run` 183, `run_async` 197, `Session.__init__` 187, `Session.run_async` 77; in `_entry.py` `_checked` 79, `_check_tools` 74, `_awaited` 57, `_submit` 45 (EXECUTED). `LONG_FUNCTIONS` holds six entries: `run_async` 217 → 197 (Decision 6 inferred about 188; the difference is the `build` lambda's nine lines), `Session.run_async` deleted, `run` 182 → 183, claimed in the news file. Net, 121 listed lines fewer (EXECUTED).
- **Rules (criteria 2, 4, 5, 8, 9).** `uv run pytest tests/checks/test_rules.py` → 143 passed, 5 skipped (needs: prior-art clones 1, artifact dir 1, git history 3); `tests/checks/test_rules.py` with `tests/unit/test_runner_package.py` → 147 passed, 5 skipped; the named rules by keyword (ceiling, eighty, seam, lock, mutable, bound twice, api lists, order, by name, one module, news) → 17 passed; `test_src_type_checks_under_mypy_strict` and `test_the_public_api_matches_its_snapshot` → 2 passed (EXECUTED). `SEAM_ALLOWED`, `ALLOWED`, `LINE_CEILING` and `tests/public_api.txt` unchanged (READ, the diff).
- **The defaults (criterion 6).** `test_set_defaults_changes_what_run_reads` and `test_the_pool_takes_the_newest_size` → 2 passed, with only Decision 5's edit to the first (EXECUTED).
- **Nothing public (criterion 8).** `uv run python -I tests/harness/api.py --check` → exit 0 (EXECUTED). `import wasi_python` loads neither `asyncio` nor `concurrent.futures` (EXECUTED, `sys.modules`).
- **Types and words (criterion 9).** `uv run python -I tests/harness/typecheck.py` → "both passes are clean"; `type: ignore` 4 → 4, `Any` 486 → 488; `uv run ruff check src tests` clean; `uv run ruff format --check src tests` → 219 files already formatted; `uv run pytest tests/lint` → 14 passed (EXECUTED).
- **Behaviour (criterion 7), without the artifact set.** `tests/unit/test_runner_async.py`, `test_runner_streaming.py`, `test_runner_sessions.py`, `test_runner_tools.py`, `test_runner_limits.py`, `test_snapshot.py`, `tests/checks/test_v1_4_embedding.py`, `test_v1_2_hostile_guest.py`, `test_v1_4_sessions.py` and `test_v1_4_public_api.py`, `-n 4 -rA`: 175 passed, 463 skipped, 4 failed on the base and on the branch, the same node ids in a `diff` of the `-rA` lists (EXECUTED). The four fail on the base too: `test_a_triangulation_leaves_every_writable_grant_as_it_was`, `test_a_class_tools_construction_keywords_are_fixed[a partial __init__]` and `test_the_removal_never_deletes_what_the_guest_may_not[home]`, `[private]`, this machine's. `test_v1_4_sessions.py -k "run_async or exit"` → 7 skipped; `test_v1_4_embedding.py -k "async or cancel or exit"` → 35 skipped; `test_a_feed_used_twice_is_refused` unchanged, passed (EXECUTED). Every guest-backed row skipped here, since this machine has no artifact set: the pass and skip counts with the set are the pull request's run's to show.
- **Unit suite.** `uv run pytest tests/unit -n 4` → 3,617 passed, 104 skipped, 1 failed: `test_runner_grants.py::test_the_walk_judges_links`, which fails as root in this container on the base too (EXECUTED).
- **Low 5.** The two rewritten coroutines read against the base's `:477-543` and `:1385-1435`: the feed is claimed by `_serving` before every check, the checks run in today's order, then `_awaited` gets the loop, registers the exit hook, claims the turn, registers the event and submits, releasing the claim on a refused submit and keeping it beside the event after (READ). No session row holds the turn's feed claim before its checks; the pull request's reviewer reads the same.
- **The run (criterion 10).** Not yet: the pull request's run is the orchestrator's to open and record.
