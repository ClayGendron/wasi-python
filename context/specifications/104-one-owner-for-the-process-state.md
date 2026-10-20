# 104 — One owner for the process's state, and the test seams move off module globals

- **Status:** **drafted 2026-10-20** on `claude/gallant-ride-9nxxmn` from main `5feb7e9` (the
  memo's plan; the tree read is `a9064a2`, which adds only the memo), awaiting its pre-build
  review. **Stacked on 103's reviewed tip** (constitution §4.14): the third entry of the chain
  102 → 103 → 104 → 105 → 106 → 107 (the memo, section 8). It is built in its own worktree on
  `spec/104-one-owner-for-the-process-state`, its header naming 103's base commit at build time.
  A different agent reviews the build.
- **Date:** 2026-10-20
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe** (§5.7). It touches `src/wasi_python/` only, the tests that set the
  runner's seams or read its state, and `tests/checks/test_rules.py`. No artifact byte changes.
  It **changes no line of `tests/public_api.txt`**: every name it moves starts with an
  underscore, and `stats()`, `set_defaults` and `defaults` answer as before. **A judge change**
  (two rules checks and one unit check): the lane accepts with `--accept-judge`.
- **Depends on:** **103** (the runner becomes a package; its reviewed tip is this branch's base).
  Landed: **015** (the pool, the live set and the fork refusal; the decisions this one keeps),
  **055** (the reaper, the session clock and the session hooks), **084** (the sweep's state),
  **078** (the stack-size window and `_on_entry`), **036** (the tool-thread count), **049** (the
  defaults lock), **052** and **092** (`tests/harness/sameness.py`, the judge of "no verdict
  moved").
- **Research it stands on:** `../research/2026-10-20-a-design-review-of-the-runner.md`: finding
  H1's process-state half ("Process state is the glue between them"), finding H5 (test seams are
  module globals in production code) and section 8 (the chain and its baseline).

## The problem

`runner.py` keeps the process's state in module globals. At `a9064a2` an AST walk of `src/`
(EXECUTED, `build/104/rules_proto.py`) finds **14 locks** bound at module or class level (13 in
`runner.py`, among them `_epoch_ticker._cond`, and `__init__.py`'s `_defaults_lock`) and **38
mutable containers or stateful objects** bound at module level (dicts, lists, sets, a `WeakSet`, a
`deque`, a `SimpleQueue`, an `itertools.count`, a `threading.local`), all in `runner.py`. Beside
them sit **eight test hooks** (`_after_walk`, `_on_entry`, `_on_arm`, `_on_export`,
`_after_export`, `_on_call`, `_session_clock`, `_start_ending`), one seam function the tests
replace (`_drive_folder`), and two judge-only flags inside a production dict (`_reaper["enabled"]`,
`_reaper["paused"]`). With `_epoch_callback`, a scalar cache, that is 60 names in `runner.py`
(READ: the memo's count) that are state or seams, not code.

Three costs follow (the memo, H1 and H5; each READ in the source at `a9064a2`):

- **The fork reset is a hand-written list.** `_after_fork_in_child` (`runner.py:1424`) names
  every lock and cache it re-creates, through three `global` statements and nineteen
  assignments. A lock added later and left off the list is a silent hazard: a child may inherit
  it held by a thread the fork left behind. No check enumerates the locks and asserts each is new.
- **The exit release is another list.** `_release` (`runner.py:4054`) clears eight caches by
  name.
- **The judge is coupled to private spellings.** Eleven unit files monkeypatch **31 distinct
  private names** of `runner` on **51 lines** (EXECUTED: `grep -ohE
  'monkeypatch\.setattr\(runner, *"_[a-zA-Z_]+"' tests/unit/*.py`; the memo's 20 on `30e9b41`
  is READ, and INFERRED to be a narrower count: the function seams alone), and the checks read
  `runner._held`, `_sweep_state`,
  `_ctrl_c`, `_fork`, `_calls`, `_engines`, `_zips`, `_outputs`, `_pool`, the locks and the
  ticker's class attributes directly. Spec 103 moves these names into ten modules; every such
  reference then names a module that was chosen for where its function went, not for what the
  state is.

Spec 103 leaves the globals where their functions moved and makes the fork hook reassign them by
module attribute. That keeps 103 a pure move. This specification is the second half: one object
owns the state, resets it in one place, and carries the seams.

## Decisions

### 1. One class, one instance, one function: `src/wasi_python/_process.py`

`_process.py` is a new module with one class, `_Process`, and one function, `process()`, which
returns the one instance the module makes at import. It imports the standard library only. The
types it names from sibling modules (`_State`, `_Stream`, `_Call`, `_Private`, `Defaults`) are
written as strings under `from __future__ import annotations` and imported under
`typing.TYPE_CHECKING`, so no sibling is imported at run time and no cycle exists: every other
module does `from ._process import process` at its top, and `_process.py` imports none of them.
`__init__.py` keeps its import order; `_process.py` is imported first by whichever sibling loads
first, and it needs nothing loaded before it.

Production code reaches the state as `process().<attribute>`. A module may bind `p = process()`
inside a function; no module binds the instance at module level, so there is one spelling for the
judge's rule in Decision 4 to see.

`_Process.__init__` is the one place the state is made. Every attribute is declared there with a
type, in groups by concern, in this order. The table lists every one of the 51 module-level
mutables and locks of `runner.py` (EXECUTED, `build/104/rules_proto.out`), the ticker's four class
attributes, `__init__.py`'s lock and the scalar cache, and the attribute each becomes. A dict that
only carried named flags becomes one attribute per flag; a dict that is a table stays a dict.

| group | today, in `runner.py` (`a9064a2`) | attribute on `_Process` |
|---|---|---|
| **A. `run_async`'s pool and the exit hook** (spec 015) | `_pool_lock` | `pool_lock: threading.Lock` |
| | `_pool["pool"]`, `_pool["size"]` | `pool: ThreadPoolExecutor \| None`, `pool_size: int` |
| | `_pools` | `pools: list[ThreadPoolExecutor]` |
| | `_live_lock`, `_live` | `live_lock: threading.Lock`, `live: set[threading.Event]` |
| | `_hook["registered"]`, `_hook["exiting"]` | `exit_hook_registered: bool`, `exiting: bool` |
| **B. Private folders, the sweep and the warnings** (specs 016, 084) | `_held_lock`, `_held` | `held_lock: threading.Lock`, `held: set[str]` |
| | `_sweep_state["claimed"]`, `["swept"]`, `["failed"]` | `sweep_claimed: bool`, `sweep_swept: int`, `sweep_failed: dict[str, int]` |
| | `_identity` | `kernel_identity: dict[str, str \| None]` |
| | `_pending_warnings_lock`, `_pending_warnings`, `_warned` | `warnings_lock: threading.Lock`, `pending_warnings: list[str]`, `warned: set[str]` |
| **C. Fork** (spec 015) | `_fork["used"]`, `_fork["forked"]` | `fork_used: bool`, `forked: bool` |
| **D. Platform tables**, resolved once | `_win_api`, `_stack_api`, `_handlers` | `win_api: dict[str, Any]`, `stack_api: dict[str, Any]`, `handlers: dict[str, Any]` |
| **E. The zip, the preopen check and the manifest facts** (specs 017, 036, 069) | `_zip_lock`, `_zips` | `zip_lock: threading.Lock`, `zips: dict[str, list[Any]]` |
| | `_check_modules` | `check_modules: dict[bool, Any]` |
| | `_versions`, `_guest_packages`, `_digests` | `versions: dict[Path, str]`, `guest_packages: dict[str, tuple[tuple[int, ...], bool]]`, `digests: dict[tuple[str, int, int], str]` |
| **F. Engines, modules, linkers and the epoch** (specs 010, 011, 015) | `_lock` | `cache_lock: threading.Lock` (engines, modules, the counts and the sweep's claim, as today) |
| | `_engines`, `_modules`, `_compiling` | `engines: dict[bool, Engine]`, `modules: dict[tuple[bool, str], Module]`, `compiling: dict[tuple[bool, str], threading.Lock]` |
| | `_counts` | `counts: dict[str, int]` (the four keys `stats()` copies) |
| | `_epoch_callback`, `_epoch_callback_lock` | `epoch_callback: Any \| None`, `epoch_callback_lock: threading.Lock` |
| | `_linkers`, `_mount_linkers`, `_guard_linkers`, `_trampolines`, `_stat_trampolines` | `linkers`, `mount_linkers`, `guard_linkers`, `trampolines`, `stat_trampolines`, each `dict[Any, Any]` |
| | `_epoch_ticker._cond`, `._thread`, `._active`, `._count` | `ticker_cond: threading.Condition`, `ticker_thread: threading.Thread \| None`, `ticker_active: int`, `ticker_count: int` |
| **G. The thread's call, the outputs, Ctrl-C, the tool threads and the stack window** (specs 011, 036, 078) | `_calls` | `calls: threading.local` (its `stack`, `watched` and `lost`, as today) |
| | `_outputs`, `_outputs_lock`, `_output_keys` | `outputs: dict[int, _Stream]`, `outputs_lock: threading.RLock`, `output_keys: itertools.count` |
| | `_ctrl_c["pending"]` | `ctrl_c_pending: bool` |
| | `_tool_threads_lock`, `_tool_threads["running"]` | `tool_threads_lock: threading.Lock`, `tool_threads_running: int` |
| | `_stack_size_lock`, `_stack_size_found` | `stack_size_lock: threading.Lock`, `stack_size_found: list[int]` |
| **H. Sessions and the reaper** (spec 055) | `_sessions_lock`, `_sessions` | `sessions_lock: threading.Lock`, `sessions: weakref.WeakSet[_State]` |
| | `_reaper["thread"]`, `["stop"]`, `["hooked"]` | `reaper_thread: threading.Thread \| None`, `reaper_stop: bool`, `reaper_hooked: bool` |
| | `_reaper["enabled"]`, `["paused"]` | `observers.reaper_enabled`, `observers.reaper_paused` (Decision 4) |
| | `_reaper_queue`, `_dropped` | `reaper_queue: queue.SimpleQueue[Any]`, `dropped: collections.deque[_State]` |
| | `_closers_lock`, `_closers` | `closers_lock: threading.Lock`, `closers: set[threading.Thread]` |
| **I. The defaults** (spec 049) | `__init__._defaults_lock` | `defaults_lock: threading.Lock` |
| **J. Observers and overrides** (Decision 4) | the eight hooks, `_drive_folder`, the two reaper flags | `observers: _Observers` |

Not moved, with the reason: `DEFAULTS` (a frozen `Defaults` value, replaced whole under
`defaults_lock`; it is a binding, not a container; `set_defaults` keeps swapping it where 103
left it), the upper-case tables (`_BUSY`, `_WIN_DEVICES`, `SIGNATURES`, `_TYPE_TEXT`, `VALUED`,
`_ERRNO_ALIASES`, `_EMPTY`: read, never written), `_UNSET` and `_DONE` (sentinels), `_WAKE` (the
reaper's sentinel), the compiled regexes, the `CFUNCTYPE` callbacks (`_output_write`,
`_output_free`), and the ctypes `Structure._fields_` lists (declarations ctypes reads once). The
rules check of Decision 5 names each of these kinds as an exception.

`_epoch_ticker` stops carrying class state. It stays a context manager; `__enter__`, `__exit__`
and `_tick` read and write `process().ticker_*` under `process().ticker_cond`, and `count()`
returns `process().ticker_count`. Its behaviour is unchanged: one thread per process, started by
the first entry, advancing every engine's epoch once per `TICK_S`.

If `103-the-runner-becomes-a-package.md` exists when the builder starts, its module list governs
which module each group's functions sit in; this table names only the state. Read on the memo's
table (INFERRED from the line ranges, since 103 is not yet drafted): group A sits in `_call.py`
(`run_async`'s pool) or `runner.py`, B in `_private_dirs.py`, C in `runner.py` or `_platform.py`,
D in `_platform.py` and `_places.py`, E in `_zip.py` and `_engine.py`, F in `_engine.py`, G in
`_call.py`, `_platform.py` and `_home.py`, H in `_sessions.py`, I in `__init__.py`. Whatever 103
chose, the state leaves that module for `_process.py` and the code reads it through `process()`.

### 2. `reset_after_fork()` and `release_at_exit()` are methods

**`reset_after_fork()`** replaces `_after_fork_in_child`'s body. `os.register_at_fork(
after_in_child=...)` keeps its registration (in `_process.py`, where the method is); its handler
is `lambda: process().reset_after_fork()`. The method makes exactly the same changes the hook
makes today (READ, `runner.py:1424-1458`), so a child behaves as it does on main:

- **Every lock is made anew**, by introspection: for every attribute whose value is a
  `threading.Lock`, `threading.RLock` or `threading.Condition`, a new object of the same type.
  The method lists no lock by name. The reason is spec 015's build review F8: a lock may be held
  by a thread the fork left out, and a child that waits on it waits forever. A `Condition` made
  anew carries no waiters, which is right: the ticker's waiter was a thread the child does not
  have.
- **The pool and the live calls:** `pool = None`, `pool_size = 0`, `pools.clear()`,
  `live.clear()`. The parent's workers are not in the child.
- **The stack window** (spec 078, F6): if `stack_size_found` holds a value,
  `threading.stack_size` is put back to it and the list is cleared.
- **The tool threads** (spec 036, Decision 8): `tool_threads_running = 0`.
- **The zip table:** `zips = {}`. The parent's zip folders are the parent's: their lock files
  are held through descriptors the parent owns, and `release_at_exit` in the child must not
  remove them. The folders on disk are untouched; only the child's table is empty.
- **The compiling guards:** `compiling = {}` (per-digest locks, possibly held by lost threads).
- **The ticker:** `ticker_thread = None`, `ticker_active = 0`; `ticker_count` is kept (a count
  is a count).
- **Sessions and the reaper** (spec 055, Decision 13): `sessions = weakref.WeakSet()`,
  `reaper_queue = queue.SimpleQueue()`, `closers.clear()`, `dropped.clear()`,
  `reaper_thread = None`, `reaper_stop = False`; `reaper_hooked` is kept (the `atexit`
  registration is inherited by the child's interpreter state, so registering again would run
  the exit hook twice); `counts["sessions_open"] = 0`.
- **The fork flag:** `if fork_used: forked = True`. `fork_used` is kept on purpose: it is the
  fact the refusal needs. A child of a parent that made an engine is refused (`_refuse_forked`),
  because wasmtime does not support use across a fork; a child of a parent that only imported
  the package runs normally.

**Deliberately kept across a fork**, as today, each with its reason: `held` and the sweep
fields (the child shares the parent's lock descriptors, so the names the parent holds are held
in the child too, and a sweep the parent claimed is claimed); `kernel_identity`, `win_api`,
`stack_api`, `handlers` (facts of the kernel and the C library, the same in the child);
`versions`, `guest_packages`, `digests`, `check_modules` (facts of files, unchanged by a fork);
`engines`, `modules` and the five linker tables (a child that would use them is refused; a child
that would not never reads them); `epoch_callback` (one ctypes callback, valid in the child);
`outputs` and `output_keys` (the parent's streams; a key is never reused, in the child too);
`calls` (the forking thread's call stack, which the child's one thread inherits: the refusal
reads it); `ctrl_c_pending`, `exiting`, `exit_hook_registered` (the threading exit hook is
inherited); `warned` and `pending_warnings` (a warning the parent owed is flushed by whichever
process reaches `_flush_warnings` first, as today); `counts` but `sessions_open`; and the
observers (the judge sets them before it forks, in the programs that test the fork). The method
runs only assignments and takes no lock, for the same reason F8 gives.

**`release_at_exit()`** replaces `_release`'s body and keeps its `atexit` registration, now in
`_process.py`: `_remove_zips()` (which `_zip.py` provides; `_process.py` reaches it through a
callable the zip module registers on the object at import, `process().remove_zips`, so
`_process.py` still imports no sibling), then `_flush_warnings()` the same way
(`process().flush_warnings`, registered by the warnings' module), then `check_modules`,
`linkers`, `mount_linkers`, `guard_linkers`, `trampolines`, `stat_trampolines`, `modules` and
`engines` cleared, in that order, while wasmtime's bindings still exist. The sessions' exit hook
(`_sessions_at_exit`) keeps its own registration in the sessions module, made at the first
session so it runs before this one, as today. The order of the three exit hooks does not change:
`_stop_async_calls` (threading's), then `_sessions_at_exit`, then `release_at_exit`.

### 3. A unit check that the fork reset reaches every lock, by introspection

`tests/unit/test_process.py` (new) holds `test_reset_after_fork_renews_every_lock_it_can_see`.
It builds a fresh `_Process()` (the constructor is the one place state is made, so a second
instance is cheap and touches no live state), records `{name: id(value)}` for every attribute
whose value is a `threading.Lock`, `threading.RLock` or `threading.Condition`, and for every
`queue.SimpleQueue`, calls `reset_after_fork()` on that instance, and asserts that every recorded
name is still bound, to an object of the same type, with a different `id`. It asserts the recorded
set is not empty and that `observers` is the same object. A lock added to `_Process` later is
seen by the record, so it cannot be forgotten: the reset renews locks by introspection, and the
check finds them the same way, so the two cannot drift apart.

Two more rows in the same file pin Decision 2's "reset" and "kept" lists on a fresh instance with
every field set to a marker: after `reset_after_fork()`, the reset fields equal a new instance's
(`pool`, `pool_size`, `pools`, `live`, `tool_threads_running`, `zips`, `compiling`,
`ticker_thread`, `ticker_active`, `sessions`, `closers`, `dropped`, `reaper_thread`,
`reaper_stop`, `counts["sessions_open"]`), and the kept fields hold their markers (`held`,
`sweep_claimed`, `kernel_identity`, `fork_used` with `forked` now `True`, `reaper_hooked`,
`ticker_count`, `warned`, `engines`). The three existing fork checks that fork a real process
stay as they are: `tests/unit/test_runner_tools.py`'s `FORK_HOOK` (the tool-thread lock is a new
object in the child), `tests/checks/test_v1_4_embedding.py`'s refusal of a forked child and its
`NO_FORK` row.

### 4. The seams become fields of one object; the judge's rule

`_process.py` also defines `_Observers`, a plain (not frozen) dataclass, held as
`process().observers`. Its fields, with today's name and what the production code does with a
`None`:

| field | today | type | `None` means |
|---|---|---|---|
| `after_walk` | `_after_walk` | `Callable[[], None] \| None` | nothing is called after a walk |
| `on_entry` | `_on_entry` | `Callable[[str], None] \| None` | no entry is reported |
| `on_arm` | `_on_arm` | `Callable[[str, int], None] \| None` | no arming is reported |
| `on_export` | `_on_export` | `Callable[[str, int], None] \| None` | no export is reported |
| `after_export` | `_after_export` | `Callable[[], None] \| None` | nothing runs after a turn's export |
| `on_call` | `_on_call` | `Callable[[str, Any], None] \| None` | no call is reported |
| `clock` | `_session_clock` | `Callable[[], float]` | never `None`; the default is `time.monotonic` |
| `start_ending` | `_start_ending` | `Callable[[_State], None] \| None` | the production closer, `_start_closer` |
| `drive_folder` | `_drive_folder` | `Callable[[str], str] \| None` | `ntpath.abspath(drive or ".")` |
| `reaper_enabled` | `_reaper["enabled"]` | `bool` | the default is `True` |
| `reaper_paused` | `_reaper["paused"]` | `bool` | the default is `False` |

The production code calls each through the object, at the lines that call the global today
(READ, `runner.py`: 2770, 4271, 5060 and 5099, 5090, 5216, 5266, 5346, 5372, 5445, 5492, 5503,
5583, 5588, 5611, 5967, 6044, 2127, 2130, 5086, 5108): `obs = process().observers` then `if
obs.on_entry is not None: obs.on_entry(kind)`, `(obs.start_ending or _start_closer)(state)`,
`(obs.drive_folder or _default_drive_folder)(drive)`, `obs.clock()`. The two reaper flags keep
their meaning: `reaper_enabled` False means the judge opens sessions without the thread;
`reaper_paused` True means the loop sleeps and the judge drives `_reap` alone.

**The one way the judge sets a seam.** In a check or a unit test:
`monkeypatch.setattr(process().observers, "<field>", value)`, where `process` is `from
wasi_python._process import process`. In a program the judge runs as a subprocess:
`process().observers.<field> = value` before the first call. The dataclass raises
`AttributeError` on a misspelt field (monkeypatch's default `raising=True`), so a seam that no
longer exists is loud. No new fixture is added; `fake_clock` and `exports_called` in
`tests/checks/test_v1_4_sessions.py` keep their names and set the fields this way.

**The rule the judge follows from this specification on**, written into `_process.py`'s
docstring: *a unit check or a goal check may patch nothing in `wasi_python` that starts
with an underscore except through `process()`: a field of `process().observers`, or an attribute
of `process()` itself.* A function seam that the judge still replaces by name is an allowance,
listed below, each with its closer. The check that enforces the rule (an AST walk of `tests/` for
`monkeypatch.setattr(<module>, "_name", …)` and `<module>._name = …` against an allowance list) is
**spec 107's**, which adds the structural rules checks the memo's section 5 asks for; 107's list
starts as the "stays" list below, and 106 removes the names its protocol fakes make unnecessary.
This specification adds the two rules checks of Decision 5 and no third.

**What moves in this specification** (every reference to state or to a seam; line numbers at
`a9064a2`, before 103's move; the builder re-finds each on 103's tip with the two greps of the
problem statement and `grep -rnE '\brunner\._(held|sweep_state|ctrl_c|fork|calls|engines|zips|
outputs|pool|sessions|closers|reaper|…)\b' tests/`):

| file | lines | what changes |
|---|---|---|
| `tests/unit/test_runner_threads.py` | 66 | `_on_entry` → `observers.on_entry` |
| `tests/unit/test_runner_sessions.py` | 109–111, 113; 128, 135, 144 | `_sessions`, `_reaper_queue`, `_dropped` → `process().sessions` …; `_start_ending` → `observers.start_ending`; `runner._sessions.add` → `process().sessions.add` |
| `tests/unit/test_runner_grants.py` | 332–334 | `_drive_folder` → `observers.drive_folder` (`_win_open`, `_close_held` stay) |
| `tests/unit/test_runner_calls.py` | 194; 268–269, 323–324 | `_ctrl_c["pending"]` → `ctrl_c_pending`; `_engines` → `engines`; `_fork["used"]` → `fork_used` |
| `tests/unit/test_runner_sets.py` | 87–88 | `_modules`, `_zips` → `modules`, `zips` |
| `tests/unit/test_runner_sweep.py` | 32–36, 51, 84, 216, 270, 343–344, 492, 782, 787, 790, 820, 831, 856, 890, 901 | `_sweep_state[…]` → `sweep_claimed`, `sweep_swept`, `sweep_failed`; `_warned`, `_pending_warnings`, `_held` → the attributes; `_lock`, `_zip_lock`, `_held_lock` → `cache_lock`, `zip_lock`, `held_lock` |
| `tests/unit/test_runner_cancel.py` | 112, 118 | `_ctrl_c` → `ctrl_c_pending` |
| `tests/unit/test_runner_async.py` | 24; 36, 40, 97, 108, 122, 132; 75, 79; 184 | `_epoch_ticker.count` → `ticker_count = 100`; `_calls.lost` → `process().calls.lost`; `_ctrl_c` → `ctrl_c_pending`; `_fork["forked"]` → `forked` |
| `tests/unit/test_runner_mounts.py` | 128, 130, 132 | `_epoch_ticker.count` → `ticker_count` |
| `tests/unit/test_runner_tools.py` | 354–355, 360; 493, 496 | `_ctrl_c` → `ctrl_c_pending`; `_tool_threads_lock` → `tool_threads_lock` (the fork program) |
| `tests/unit/test_async_tools.py` | 347, 349, 357 | `_ctrl_c` → `ctrl_c_pending` |
| `tests/checks/test_v1_2_hostile_guest.py` | 787, 876; 2750–2751, 2764, 2767; 2789, 2798; 2706–2707 | `_after_walk` → `observers.after_walk`; the by-hand save and restore of `_on_entry` → `monkeypatch.setattr(process().observers, "on_entry", entry)`; `_session_clock()` → `observers.clock()`; `_epoch_ticker.count()` → `ticker_count` |
| `tests/checks/test_v1_4_sessions.py` | 163–164, 174, 418, 875, 989, 1214, 1221; 728, 746, 1180, 1187 (programs); 233, 239, 582–588, 721, 734, 737, 860, 866, 1015, 1020, 1185 | the fixtures and the hooks → `observers.*`; `_reaper["enabled"] = False` → `process().observers.reaper_enabled = False`; `_held`, `_sessions_lock`, `_closers`, `_ctrl_c` → the attributes |
| `tests/checks/test_v1_4_embedding.py` | 950, 953; 1258–1259, 1293, 2284–2285, 2297, 3090, 3971; 1856–1857, 2298; 1435; 1478 | `_outputs` → `outputs`; `_epoch_ticker.count()` reads → `ticker_count`; the three `count = classmethod(...)` overrides → `process().ticker_count = <value>` (the ticker adds to it, so a value past the deadline stays past it); `_count += 1000` → `ticker_count += 1000`; `_engines` → `engines`; `print(runner._fork)` → `print(process().fork_used, process().forked)` with its expected line restated; `_sweep_state["swept"]` → `sweep_swept` |
| `tests/checks/test_v1_4_public_api.py` | 444–445, 450 | `_pool_lock` → `process().pool_lock` (the racing wrapper is set with `monkeypatch.setattr(process(), "pool_lock", racing)`); `_pool["size"]` → `pool_size` |
| `src/wasi_python/mounts.py` | 723–724, 852 | `r._hook["exiting"]` → `process().exiting`; `r._ctrl_c["pending"]` → `process().ctrl_c_pending`; `r._epoch_ticker.count()` → `process().ticker_count`; `r._ctrl_c_watched()` and `r._epoch_now` stay as calls on the runner until 106's protocol |

Of the 31 private names the unit files monkeypatch, **eleven move** here, because they are state
or seams: `_engines`, `_zips`, `_modules`, `_warned`, `_pending_warnings`, `_held`, `_sessions`,
`_reaper_queue`, `_dropped`, `_on_entry`, `_start_ending` (14 lines). **Twenty stay**, each a
function the test replaces to fake a platform answer or to force an error path, and each named
here with its closer; moving them is out of this specification's scope, because each needs a
protocol or a platform seam, which is 106's design, not a field on the process object:

- **Platform answers, 106's `_platform.py` seam:** `_guest_stack` (2 lines, and 3 in
  `test_v1_2_hostile_guest.py`), `_tell_interpreter`, `_trap_handlers_ready` (2), `_dir_fd_ok`
  (2), `_win_open`, `_close_held`, `_try_lock` (2), `_unlock_close`, `_remove_tree` (5),
  `_drop` (2), `_drive`, `_stack`.
- **Engine and call paths, 106's call-context protocol or 105's typed call:** `_ctrl_c_watched`
  (8), `_stop_error` (2), `_epoch_now` (2), `_context_address`, `_module_miss` (2),
  `_found_and_checked`, `_join_guest`, `_walk_grants`.
- In the checks, the same kinds stay for the same closers: `_guest_stack`, `_check_preopens`,
  `_current_defaults`.

Public names the tests patch (`run`, `find_artifacts`, `DEFAULTS`, `MAX_RESPONSE`,
`threading.stack_size`, `_Home.serve`, `_Files.__call__`) are outside the rule: the first four
are the public surface, the rest are methods of objects the tests build.

### 5. Two rules checks: no lock and no mutable at module level outside `_process.py`

Both live in `tests/checks/test_rules.py`, with their scanners in `tests/harness/scan.py`
beside `duplicate_name_hits`, over `src/wasi_python/*.py` except `_process.py`, by `ast`. Each
reports `file:line: name (kind)` through `scan.report`. Both walk the module body and the body of
every class defined at module level (so `_epoch_ticker._cond` is seen), and read `Assign` and
`AnnAssign` targets.

1. **`test_no_lock_is_made_at_module_level_outside_the_process`**
   (`scan.module_lock_hits`): a hit is a binding whose value is a call to `Lock`, `RLock` or
   `Condition`, written as `threading.X(...)` or a bare `X(...)`. No exceptions. At `a9064a2` it
   finds the 14 of the problem statement (EXECUTED, the prototype); on 103's tip the same 14 in
   their new modules (INFERRED: 103 moves them unchanged); after this specification, none.
2. **`test_no_mutable_is_bound_at_module_level_outside_the_process`**
   (`scan.module_mutable_hits`): a hit is a binding whose value is a dict, list or set display or
   comprehension, or a call to `dict`, `list`, `set`, `bytearray`, `collections.deque`,
   `collections.defaultdict`, `collections.OrderedDict`, `weakref.WeakSet`,
   `weakref.WeakValueDictionary`, `weakref.WeakKeyDictionary`, `queue.SimpleQueue`,
   `queue.Queue`, `itertools.count` or `threading.local` (with or without the module prefix).
   **Exceptions**, each a kind the code has today: `__all__`; an upper-case name bound to a dict,
   set or list display (a table that is only read: `_BUSY`, `_WIN_DEVICES`'s neighbours,
   `SIGNATURES`, `_TYPE_TEXT`, `VALUED`, `_ERRNO_ALIASES`, `_EMPTY`); and the name `_fields_`
   inside a class body (a ctypes declaration). Tuples, frozensets, compiled regexes, `CFUNCTYPE`
   callbacks, sentinels and frozen dataclass values are not in the list, so they need no
   exception. At `a9064a2` it finds the 38 of the problem statement (EXECUTED: the prototype's 40
   less the two `_fields_`); after this specification, none.

Each is seen failing first: the builder runs both on 103's tip before writing `_process.py` and
records the counts in the landing notes. A unit row for each scanner in `tests/unit/test_scan.py`
(where `duplicate_name_hits`'s rows live) gives it a small module with one hit of every kind and
one of every exception.

### 6. Thread-safety is unchanged, and the lock order is written down

What is locked, and when, does not change. Every `with _x_lock:` becomes `with
process().x_lock:` at the same place; `_outputs_lock` stays an `RLock` (a finalizer the collector
runs inside a locked block re-enters it on the same thread); `_lock` keeps guarding what it guards
today under the name `cache_lock` (the engines, the modules, the counts, and the sweep's claim
flag at `runner.py:958`). A builder who finds a lock taken in a new place has made a mistake.

The lock order, from an AST walk of every `with` over a name ending in `_lock`, `_cond` or
`.lock` nested in another, and of every call under such a `with` to a function that takes one
(EXECUTED, `build/104/lock_order.py` on `a9064a2`; the builder re-runs it on 103's tip): **no
`with` over a lock is nested in another in `runner.py`**; the one acquisition under a held lock is
`_zip_folder`, which holds `_zip_lock` while `_Private.remove` takes `_lock` and then
`_held_lock`, one after the other. So the order is short, and `_process.py`'s docstring says it
in this form:

1. `zip_lock` is taken first, and under it `cache_lock` and `held_lock` may be taken, never both
   at once.
2. Every other lock is a leaf: nothing is taken under `pool_lock`, `live_lock`, `warnings_lock`,
   `epoch_callback_lock`, `outputs_lock`, `tool_threads_lock`, `stack_size_lock`,
   `sessions_lock`, `closers_lock`, `ticker_cond`, `defaults_lock`, a `compiling` guard, or a
   session's or home's own `lock`.
3. `warnings_lock` is held only inside `_warn_later` and `_flush_warnings`, and
   `_flush_warnings` runs outside every other lock (spec 084), so an embedder's `showwarning`
   can take any lock it likes.
4. `outputs_lock` is re-entrant; no other lock is.

The docstring also says the rule for a change: a new lock is a leaf unless this list is amended,
and the amendment names the pair.

### 7. How the judge sees it

The fast tier, run in the builder's worktree against the frozen baseline set (the `v0.1.0a7`
release's, verified against its `SHA256SUMS`; the memo, section 8), gives the same verdicts as
the baseline record: `uv run python tests/harness/sameness.py <baseline>.json <this>.json` prints
only the new rows (the three checks of Decisions 3 and 5 and the unit rows), which the claim list
names. No fuel row moves: no guest byte changes, and the host's work per call changes by one
attribute read per state access. No golden output, gap, allowance or progress file is edited.
`ruff check` and `ruff format --check` are clean on `src/` and `tests/`.

### 8. Where this meets the rest of the chain

- **102** (`102-the-engine-seam.md`, drafted on this branch the same day) makes
  `src/wasi_python/_wasmtime_ffi.py`, which "holds no mutable state: constants, functions and
  one class" and is reset at no fork and released at no exit (READ, its Decisions 1 and 7). So
  `_Process` takes nothing from it; the two rules checks of Decision 5 scan it like any sibling
  and expect no hit (its `NEEDED` table is an upper-case display). The `_epoch_callback` object
  and the output table, which 102 keeps in the runner's modules, are group F's `epoch_callback`
  and group G's `outputs` here.
- **103** leaves the globals in the module their functions moved to, and a fork hook that
  reassigns them by module attribute. This specification deletes those module globals, that
  hook's body, and the four `global` statements of `runner.py` (`global` is not needed when state
  is an attribute); `grep -nE '^\s*global ' src/wasi_python/*.py` finds none afterwards (today
  4 lines, EXECUTED).
- **105** (typed call state, explicit lifecycles, a type checker) reads group G: `calls` is the
  thread-local whose `stack` holds `_Call`s, and `_State` is what `sessions`, `dropped` and
  `start_ending` carry. The type checker 105 adds sees every attribute typed in
  `_Process.__init__`.
- **106** (`mounts.py` behind a call-context protocol, one platform module, one stamp) reads
  groups D, F and G: `exiting`, `ctrl_c_pending` and `ticker_count`, which `mounts.py` reads
  through `process()` after this specification, become the protocol's `exiting()`,
  `ctrl_c_pending()` and `deadline_passed()`; the platform tables of group D move behind
  `_platform.py`'s interface; the twenty names that stay in Decision 4 are its allowance list to
  shrink.
- **107** adds the check that enforces Decision 4's rule, with the allowance list.

## Intent

The process's state has one owner, made in one place, reset for a fork in one method that finds
every lock by looking rather than by a list, and released at exit by one method. The judge
reaches the runner's seams through that one object and nothing else, so the refactors that follow
(105, 106) move code without breaking tests that test nothing about behaviour. Two rules checks
keep it so: no lock and no mutable at module level outside `_process.py`.

## Design

| file | change |
|---|---|
| `src/wasi_python/_process.py` | new: `_Observers`, `_Process` (Decision 1's groups, `reset_after_fork`, `release_at_exit`, the `remove_zips` and `flush_warnings` callables the zip and warnings modules register), `process()`, the `register_at_fork` and `atexit` registrations, the lock order in the docstring (Decision 6) and the judge's rule (Decision 4) |
| the ten modules of 103 and `runner.py` | every module-level mutable and lock deleted; every read and write becomes `process().<attr>`; `_after_fork_in_child` and `_release` deleted with their `global` statements; the eight hooks, `_drive_folder`'s default and the reaper flags read from `process().observers`; `_epoch_ticker` reads `process().ticker_*` |
| `src/wasi_python/__init__.py` | `_defaults_lock` deleted; `set_defaults` takes `process().defaults_lock` |
| `src/wasi_python/mounts.py` | lines 723–724 and 852 read `process()` (Decision 4's table) |
| `tests/unit/test_process.py` | new: Decision 3's three rows |
| `tests/harness/scan.py` | `module_lock_hits`, `module_mutable_hits` (Decision 5) |
| `tests/checks/test_rules.py` | the two rules checks |
| `tests/unit/test_scan.py` | two unit rows for the scanners |
| the fifteen test files of Decision 4's table | each line named there |
| `CHANGELOG.md` | one line under the unreleased section (below) |

Nothing under `scripts/`, `recipes/`, `downloads/` or the release workflow changes. No pin, no
artifact byte, no line of `tests/public_api.txt`, no dependency.

**The CHANGELOG line**, under the unreleased section: "**The runner's process state has one
owner** (spec 104): every lock, cache, counter and registry of the runner is an attribute of one
`_Process` object, reset for a fork by introspection over its locks and released at exit by one
method; the judge's seams are fields of that object, not module globals; two rules checks keep
locks and mutables out of module level. No public name changes."

**The roadmap line** (`context/roadmap.md`, the reserved list): "Reserved: 104 (one owner for
the process's state: `_process.py`, one object with every lock, cache and registry, a fork reset
by introspection and one exit release; the test seams move onto it; two rules checks keep locks
and mutables off module level; parallel-safe, stacked on 103, the third of the chain 102–107 from
the design review memo of 2026-10-20)."

## Scope

In: Decisions 1 to 7. Out:

- **The twenty function seams the unit files still patch by name** (Decision 4): 106's
  platform module and call-context protocol, and 107's enforcing check.
- **Typed call state, the session and home phase enums** (H3): 105.
- **`mounts.py`'s imports of the runner** beyond the three state reads (H4): 106.
- **The engine adapter** (H2): 102, below this in the chain.
- **A change to what is locked or when** (Decision 6): none here; a finding that one is needed
  is its own specification.
- **A change to any default, limit or public name**: none.

## Acceptance criteria

1. **`_process.py` holds every name of Decision 1's table**, each with its type in `__init__`,
   and `grep -nE '^_[a-zA-Z_]+( *:[^=]+)? *= ' src/wasi_python/*.py` outside `_process.py`
   matches only constants (upper-case names, sentinels, regexes, callbacks): the builder pastes
   the remaining matches into the landing notes.
2. **Both rules checks were seen failing first**, on 103's tip, with their counts recorded (14
   locks and 38 mutables at `a9064a2`, EXECUTED; the builder's numbers on 103's tip), and pass
   on the built commit. Their two unit rows pass.
3. **The fork check of Decision 3 passes**, its record non-empty, and the three real-fork checks
   it names pass unchanged (on POSIX; they skip on Windows as today).
4. **No `global` statement** remains in `src/wasi_python/` (criterion of Decision 8; today four
   lines).
5. **Every test line of Decision 4's table changed**, and no test in `tests/` names a moved
   state global or a hook by its old spelling: `grep -rnE '\brunner\._(held|sweep_state|ctrl_c|
   fork|calls|engines|zips|outputs|pool|pools|live|hook|sessions|closers|reaper|reaper_queue|
   dropped|modules|digests|identity|warned|pending_warnings|counts|tool_threads|compiling|
   linkers|epoch_ticker|[a-z_]*_lock|after_walk|on_entry|on_arm|on_export|after_export|on_call|
   session_clock|start_ending|drive_folder)\b' tests/` finds nothing (today 96 lines, EXECUTED,
   `--include='*.py'`); the same for the module names 103 introduced in place of `runner`.
6. **Sameness.** The builder's fast tier on the frozen baseline set and the baseline record
   differ only in the rows the claim list names (Decision 7), by `tests/harness/sameness.py`.
   No fuel row moves; no pass is lost.
7. **Thread-safety unchanged**: the lock-order scan of Decision 6 on the built commit finds the
   one acquisition under a held lock it finds today and no other; the builder records its output.
8. **The judge.** `uv run pytest -m "not slow" -n 6` in the worktree, green; `ruff check` and
   `ruff format --check` clean. The lane accepts the chain's wave with `--accept-judge` naming
   this specification's three checks and unit rows.
9. **The release.** One dispatch of the release workflow on the chain's final tip (the memo,
   section 8), every job green on all three systems, stands for this specification's "built";
   its run id goes in the landing notes.

## For the lane

- **Kind:** parallel-safe; a judge change. In the chain's wave it is the third entry, rebased
  onto 103's landed or wave tip in order; its conflicts, if any, are in the ten modules 103
  made (every one a deleted global or a `process().` read) and in the fifteen test files of
  Decision 4, each named at the rebase.
- **Shares files with:** 103 (every module of the package; this one deletes what 103 placed),
  105 (the typed `_Call` and `_State` that groups G and H name), 106 (`mounts.py`'s three reads
  and `_platform.py`'s tables), and any open specification that adds a module-level lock or
  mutable under `src/` (the rules checks of Decision 5 would fail it; its builder moves the name
  onto `_Process` at the rebase).
- **The claim list** (each line starts "104:"; the numbers are the builder's):
  - 104: **new checks, each passing:**
    `tests/checks/test_rules.py::test_no_lock_is_made_at_module_level_outside_the_process`,
    `tests/checks/test_rules.py::test_no_mutable_is_bound_at_module_level_outside_the_process`
    (both rules; no fuel).
  - 104: **unit rows:** `tests/unit/test_process.py` gains three; `tests/unit/test_scan.py` gains
    two.
  - 104: **retired checks:** none. **Lost passes:** none. **Rows that grow:** none (no artifact
    byte, no guest work).
  - **The judge hash changes** in `tests/checks/test_rules.py`, `tests/harness/scan.py`,
    `tests/unit/test_process.py`, `tests/unit/test_scan.py` and the fifteen test files of
    Decision 4.
- **The flags** (paste-safe; the lane folds them into the wave's):

  ```
  --accept "104: the runner's process state has one owner: every lock, cache, counter, pool, live set, reaper handle, sweep field, Ctrl-C flag, output table and thread-local is an attribute of one _Process object in _process.py, reset for a fork by introspection over its locks and released at exit by one method; the judge's seams (the eight hooks, the session clock, the closer starter, the drive folder, the reaper's enabled and paused flags) are fields of process().observers; no public name changes"
  --accept-judge "104: two rules checks, no threading.Lock, RLock or Condition and no mutable container or stateful object bound at module or class level under src/wasi_python outside _process.py (exceptions: __all__, upper-case display tables, ctypes _fields_); a unit check that reset_after_fork renews every lock, condition and queue it can see by introspection, with two rows for the reset and kept fields; unit rows for the two scanners; the tests that set the runner's seams or read its state do so through process(); no existing expectation edited"
  ```

- **Dry-run needs:** none of its own; the chain's one dispatch on its final tip (criterion 9).

## One line

One object owns the runner's state, resets it for a fork by looking at itself, and carries the
judge's seams; two rules checks keep every lock and mutable off module level, and no public name
moves.

## Landing notes

Filled in when it lands.
