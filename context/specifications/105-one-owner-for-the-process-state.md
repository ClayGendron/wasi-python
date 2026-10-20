# 105 — One owner for the process's state, and the test seams move off module globals

- **Status:** **built on `1f959c2` (the code; the commits after it carry these notes) on `spec/105-one-owner-for-the-process-state`, stacked on 104's
  reviewed tip `538e831` (rebased from its built tip `2a9546c` after 104's build review), 2026-10-20, awaiting the build review.** Drafted 2026-10-20 on
  `claude/gallant-ride-9nxxmn` from main `5feb7e9` (the memo's plan; the tree read is `a9064a2`,
  which adds only the memo). **Stacked on 104's reviewed tip** (constitution §4.14): the third
  entry of the chain 103 → 104 → 105 → 106 → 107 → 108 (the memo, section 8), built in its own
  worktree on `spec/105-one-owner-for-the-process-state` from 104's built tip `2a9546c`, then
  rebased onto its reviewed tip `538e831` (the *Rebase* bullet of the landing notes).
  **Reviewed before build** the same day
  (`../reviews/105-one-owner-for-the-process-state-spec-2026-10-20.md`, verdict "may be built
  once Decision 6's lock order is restated from a corrected scan and Decision 2 names the
  type-to-factory table"); **revised against all seven findings** (its *Disposition*): the lock
  order of Decision 6 comes from the corrected scanner, Decision 2 renews locks by a
  type-to-factory table, and the five Lows are written in. 104 is in the tree
  (`104-the-runner-becomes-a-package.md`); this revision reads its module names and its import
  rule. A different agent reviews the build.
- **Date:** 2026-10-20
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe** (§5.7). It touches `src/wasi_python/` only, the tests that set the
  runner's seams or read its state, and `tests/checks/test_rules.py`. No artifact byte changes.
  It **changes no line of `tests/public_api.txt`**: every name it moves starts with an
  underscore, and `stats()`, `set_defaults` and `defaults` answer as before. **A judge change**
  (two rules checks and one unit check): the lane accepts with `--accept-judge`.
- **Depends on:** **104** (the runner becomes a package; its reviewed tip is this branch's base).
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
(EXECUTED, `build/105/rules_proto.py`) finds **14 locks** bound at module or class level (13 in
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
  ticker's class attributes directly. Spec 104 moves these names into ten modules; every such
  reference then names a module that was chosen for where its function went, not for what the
  state is.

Spec 104 leaves the globals where their functions moved and makes the fork hook reassign them by
module attribute (READ, its Decision 4: "Every lock, cache, hook and counter stays a module
global, in the module its functions moved to"). That keeps 104 a pure move. This specification is
the second half: one object owns the state, resets it in one place, and carries the seams.

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
judge's rule in Decision 4 to see. This fits 104's import rule (READ, its Decision 2: a function
or a mutable is reached as `_module.name` at every use, so a rebinding is seen by every caller):
`process` is never rebound and the judge never patches it, so it may be imported by name, and
this specification adds `process` to 104's check 3 list of names a module may import by `from`
(`SENTINELS`, today `_UNSET` and `_DONE`), with that reason beside it. `_process` stands first in
104's import order, before `_wasmtime_ffi`, since it imports nothing of the package.

`_Process.__init__` is the one place the state is made. Every attribute is declared there with a
type, in groups by concern, in this order. The table lists every one of the 51 module-level
mutables and locks of `runner.py` (EXECUTED, `build/105/rules_proto.out`), the ticker's four class
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
`defaults_lock`; it is a binding, not a container; `set_defaults` keeps swapping it where 104
left it), the upper-case tables (`_BUSY`, `_WIN_DEVICES`, `SIGNATURES`, `_TYPE_TEXT`, `VALUED`,
`_ERRNO_ALIASES`, `_EMPTY`: read, never written), `_UNSET` and `_DONE` (sentinels), `_WAKE` (the
reaper's sentinel), the compiled regexes, the `CFUNCTYPE` callbacks (`_output_write`,
`_output_free`), and the ctypes `Structure._fields_` lists (declarations ctypes reads once). The
rules check of Decision 5 names each of these kinds as an exception.

`_epoch_ticker` stops carrying class state. It stays a context manager; `__enter__`, `__exit__`
and `_tick` read and write `process().ticker_*` under `process().ticker_cond`, and `count()`
returns `process().ticker_count`. Its behaviour is unchanged: one thread per process, started by
the first entry, advancing every engine's epoch once per `TICK_S`.

104's module list governs which module each group's functions sit in; this table names only the
state. Where each global sits on 104's tip (READ, 104's Decisions 4 and 5): group A in
`runner.py` (`_pool_lock`, `_live_lock`, `_pool`, `_pools`, `_live`, `_hook`); B in
`_private_dirs.py`; C in `_platform.py` (`_fork`); D in `_platform.py` and `_places.py`; E in
`_zip.py` (`_zip_lock`, `_zips`) and `_engines.py` (`_check_modules`, `_CHECK_WAT`) and
`_artifacts.py` (`_version_tag`'s and `_has_guest_package`'s caches); F in `_engines.py` (`_lock`,
`_engines`, `_modules`, `_compiling`, `_counts`, `_epoch_ticker`) and `_call.py` (the epoch
callback and its lock, the five linker and trampoline tables); G in `_home.py` (`_calls`,
`_ctrl_c`, `_stack_size_lock`, `_stack_size_found`, `_on_entry`) and `_call.py` (`_outputs`, its
lock and keys, `_tool_threads_lock`, `_tool_threads`); H in `_sessions.py`; I in `__init__.py`;
`_after_walk` and `_drive_folder` in `_places.py`, the session hooks and `_session_clock` in
`_sessions.py`. Whatever module 104's build left a name in, the state leaves that module for
`_process.py` and the code reads it through `process()`; the builder re-finds each by 104's move
table, not by this paragraph.

### 2. `reset_after_fork()` and `release_at_exit()` are methods

**`reset_after_fork()`** replaces `_after_fork_in_child`'s body. `os.register_at_fork(
after_in_child=...)` keeps its registration (in `_process.py`, where the method is); its handler
is `lambda: process().reset_after_fork()`. The method makes the changes the hook makes today
(READ, `runner.py:1424-1458`) and two more: `warnings_lock` and `defaults_lock` are made anew as
well, by the same rule (F8), where today's list leaves them (the pre-build review's finding 3;
104's Decision 4 leaves the omission visible and hands the decision here). So a child behaves as
it does on main, with two locks fewer to inherit held:

- **Every lock is made anew**, by introspection over one table, `RENEW`, written once in
  `_process.py` and read by the method and by Decision 3's check:
  `{type(threading.Lock()): threading.Lock, type(threading.RLock()): threading.RLock,
  threading.Condition: lambda: threading.Condition(), queue.SimpleQueue: queue.SimpleQueue}`.
  For every attribute whose value's exact type is a key, the attribute is rebound to the
  factory's result. The method lists no lock by name. The table, not `isinstance` and not
  `type(value)()`, because on Python 3.11 and 3.12 `threading.Lock` and `threading.RLock` are
  factory functions, not types (`isinstance(x, threading.Lock)` raises `TypeError`, and
  `type(threading.Lock())()` raises "cannot create '_thread.lock' instances"), and on 3.13 only
  `Lock` became a type (READ: the pre-build review's probe on 3.11.17, 3.12.3 and 3.13.16). The
  keys are what `type(threading.Lock())` returns on every version from 3.11, the project's
  minimum (`pyproject.toml`, `requires-python = ">=3.11"`). A `Condition` made anew is over a new
  `Lock` (today's `_cond = threading.Condition()` is the same); it carries no waiters, which is
  right: the ticker's waiter was a thread the child does not have. The reason for renewing at
  all is spec 015's build review F8: a lock may be held by a thread the fork left out, and a
  child that waits on it waits forever.
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
callable the zip module binds on the object at import, `process().remove_zips`, so
`_process.py` still imports no sibling), then `_flush_warnings()` the same way
(`process().flush_warnings`, bound by `_private_dirs.py`), then `check_modules`,
`linkers`, `mount_linkers`, `guard_linkers`, `trampolines`, `stat_trampolines`, `modules` and
`engines` cleared, in that order, while wasmtime's bindings still exist. `remove_zips` and
`flush_warnings` are declared in `__init__` like every other attribute, as `Callable[[], None]`
with a no-op default (`lambda: None`), and `release_at_exit` calls whatever is bound: a fresh
`_Process()` (Decision 3's check) and any order of the package's imports are safe (the pre-build
review's finding 7). The sessions' exit hook
(`_sessions_at_exit`) keeps its own registration in the sessions module, made at the first
session so it runs before this one, as today. The order of the three exit hooks does not change:
`_stop_async_calls` (threading's), then `_sessions_at_exit`, then `release_at_exit`.

### 3. A unit check that the fork reset reaches every lock, by introspection

`tests/unit/test_process.py` (new) holds `test_reset_after_fork_renews_every_lock_it_can_see`.
It builds a fresh `_Process()` (the constructor is the one place state is made, so a second
instance is cheap and touches no live state), records `{name: id(value)}` for every attribute
whose value's exact type is a key of `_process.RENEW` (Decision 2's table: the lock type, the
RLock type, `Condition`, `SimpleQueue`), calls `reset_after_fork()` on that instance, and asserts
that every recorded name is still bound, to an object of the same type, with a different `id`. It
asserts the recorded set has at least four names (one of each kind, so an empty walk cannot pass)
and that `observers` is the same object. A lock added to `_Process` later is seen by the record,
so it cannot be forgotten: the reset renews locks by the table, and the check finds them by the
same table, so the two cannot drift apart. A second row, `test_renew_knows_every_lock_kind`,
asserts `RENEW` has exactly the four keys and that each factory's result has its key's type, on
the Python running the judge.

**Which Pythons see it.** The judge runs on 3.14.2 in CI (`.github/workflows/release.yml`,
`UV_PYTHON`) and on 3.13 locally; no leg runs the project's minimum, 3.11. On 3.11 and 3.12 the
table's keys are the same types (`type(threading.Lock())` is `_thread.lock` on every version), so
the text of Decision 2 is what covers them, not a run. The risk that remains is named: a reset
that raised on 3.11 would be reported by Python as unraisable and ignored, and the child would
keep every inherited lock; the table has no call that differs between the versions, which is why
Decision 2 chose it over `isinstance` and `type(value)()`. A builder who can run 3.11 locally
runs this file on it once and records the line in the landing notes.

**104's check 1 is replaced.** 104's `test_every_module_level_lock_is_remade_after_fork`
(`tests/unit/test_runner_package.py`) walks module-level locks and requires at least 13, with a
`RESET_BY_FORK` list and an `ast` read of `_after_fork_in_child` (READ, 104's Decision 4). After
this specification there are no module-level locks and no `_after_fork_in_child`, so that check
would fail by construction. It is retired here, named in the `--accept-judge` reason, and
Decision 3's check is its successor: the same question (is every lock remade?) asked of the one
owner instead of the modules. 104's checks 2 to 4 stay; check 3 gains `process` in its by-name
list (Decision 1) and `_process` joins check 2's `ORDER` first.

Two more rows in the same file pin Decision 2's "reset" and "kept" lists on a fresh instance with
every field set to a marker: after `reset_after_fork()`, the reset fields equal a new instance's
(`pool`, `pool_size`, `pools`, `live`, `tool_threads_running`, `zips`, `compiling`,
`ticker_thread`, `ticker_active`, `sessions`, `closers`, `dropped`, `reaper_thread`,
`reaper_stop`, `counts["sessions_open"]`), and the kept fields hold their markers (`held`,
`sweep_claimed`, `kernel_identity`, `fork_used` with `forked` now `True`, `reaper_hooked`,
`ticker_count`, `warned`, `engines`). The three existing checks that fork a real process stay,
with their reads moved as Decision 4's table says: `tests/unit/test_runner_tools.py`'s
`FORK_HOOK` keeps asserting the tool-thread lock is a new object in the child, reading
`process().tool_threads_lock` at its lines 493 and 496; `tests/checks/test_v1_4_embedding.py`'s
refusal of a forked child and its `NO_FORK` row read `process().fork_used` and `forked`.

### 4. The seams become fields of one object; the judge's rule

`_process.py` also defines `_Observers`, a `@dataclass(slots=True)` (not frozen), held as
`process().observers`. Slots, so that an assignment to a misspelt field raises `AttributeError`
everywhere, in a subprocess program as under `monkeypatch` (the pre-build review's finding 4: on
a plain dataclass `process().observers.on_entyr = f` would succeed silently and the seam would
never be set). Its fields, with today's name and what the production code does with a `None`:

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
`AttributeError` on a misspelt field (its slots, and monkeypatch's default `raising=True`), so a
seam that no longer exists is loud. No new fixture is added; `fake_clock` and `exports_called` in
`tests/checks/test_v1_4_sessions.py` keep their names and set the fields this way.

**The rule the judge follows from this specification on**, written into `_process.py`'s
docstring: *a unit check or a goal check may patch nothing in `wasi_python` that starts
with an underscore except through `process()`: a field of `process().observers`, or an attribute
of `process()` itself.* A function seam that the judge still replaces by name is an allowance,
listed below, each with its closer. The check that enforces the rule (an AST walk of `tests/` for
`monkeypatch.setattr(<module>, "_name", …)` and `<module>._name = …` against an allowance list) is
**spec 108's**, which adds the structural rules checks the memo's section 5 asks for; 108's list
starts as the "stays" list below, and 107 removes the names its protocol fakes make unnecessary.
This specification adds the two rules checks of Decision 5 and no third.

**What moves in this specification** (every reference to state or to a seam; line numbers at
`a9064a2`, before 104's move; the builder re-finds each on 104's tip with the two greps of the
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
| `src/wasi_python/mounts.py` | 723–724, 852 (on 104's tip: `r._hook["exiting"]`, `self._home._ctrl_c["pending"]`, `self._engines._epoch_ticker.count()`; READ, 104's Design) | the three state reads → `process().exiting`, `process().ctrl_c_pending`, `process().ticker_count`; `self._home._ctrl_c_watched()` and `self._call._epoch_now` stay as calls until 107's protocol |

Of the 31 private names the unit files monkeypatch, **eleven move** here, because they are state
or seams: `_engines`, `_zips`, `_modules`, `_warned`, `_pending_warnings`, `_held`, `_sessions`,
`_reaper_queue`, `_dropped`, `_on_entry`, `_start_ending` (12 of the 51 lines, EXECUTED:
`_engines` twice, the rest once). **Twenty stay** (39 lines), each a
function the test replaces to fake a platform answer or to force an error path, and each named
here with its closer; moving them is out of this specification's scope, because each needs a
protocol or a platform seam, which is 107's design, not a field on the process object:

- **Platform answers, 107's `_platform.py` seam:** `_guest_stack` (2 lines, and 3 in
  `test_v1_2_hostile_guest.py`), `_tell_interpreter`, `_trap_handlers_ready` (2), `_dir_fd_ok`
  (2), `_win_open`, `_close_held`, `_try_lock` (2), `_unlock_close`, `_remove_tree` (5),
  `_drop` (2), `_drive`, `_stack`.
- **Engine and call paths, 107's call-context protocol or 106's typed call:** `_ctrl_c_watched`
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
   finds the 14 of the problem statement (EXECUTED, the prototype); on 104's tip the same 14 in
   their new modules (INFERRED: 104 moves them unchanged); after this specification, none.
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
   less the two `_fields_`); after this specification, none. 107's `_platform.PLATFORM`, a
   module-level binding to one chosen platform object, is a call to a class, outside this list;
   107 names it as its one platform seam and 108's seam check knows it by name (READ, 107's
   "How a check binds a platform"), so neither check here flags it.

Each is seen failing first: the builder runs both on 104's tip before writing `_process.py` and
records the counts in the landing notes. A unit row for each scanner in `tests/unit/test_scan.py`
(where `duplicate_name_hits`'s rows live) gives it a small module with one hit of every kind and
one of every exception.

### 6. Thread-safety is unchanged, and the lock order is written down

What is locked, and when, does not change. Every `with _x_lock:` becomes `with
process().x_lock:` at the same place; `_outputs_lock` stays an `RLock` (a finalizer the collector
runs inside a locked block re-enters it on the same thread); `_lock` keeps guarding what it guards
today under the name `cache_lock` (the engines, the modules, the counts, and the sweep's claim
flag at `runner.py:958`). A builder who finds a lock taken in a new place has made a mistake.

The lock order comes from the corrected scanner, `build/105/lock_order.py` (EXECUTED on
`a9064a2`; the pre-build review's finding 1 found the first version blind to attribute locks and
to calls more than one level down). It reads `runner.py` by `ast` and reports two things. First,
every `with` over a lock nested in another `with` over a lock inside one function, where a lock is
a name ending in `_lock` or `_cond`, the name `_lock`, or an attribute `.lock`, `.*_lock` or
`.*_cond` (so `state.lock`, `home.lock` and `self.lock` count). Second, every lock a function
takes when it is called, transitively, under a held lock, with the shortest call path: a bare
call resolves to the module-level function of that name, a class call to its `__init__`, a method
call to every class's method of that name (a call on an imported module, `os.close()`, resolves to
nothing). Its output (`build/105/lock_order.out`):

```
_stack_size_lock > home.lock   (_start_guest:4306)
_stack_size_lock > home.lock   (_start_guest:4315)
_zip_lock > _lock                  (_zip_folder > _Private.remove:958)
_zip_lock > _held_lock             (_zip_folder > _zip_folder_locked > _Private.__init__:900)
_zip_lock > _pending_warnings_lock (_zip_folder > _Private.remove > _warn_later:1367)
_zip_lock > _held_lock             (_zip_folder > _Private.remove > _drop:963)
```

Four pairs, no inversion (`_stack_size_lock` is taken at one place; `home.lock`, `_lock`,
`_held_lock` and `_pending_warnings_lock` take nothing under them), so there is no deadlock today
and none is introduced. `_process.py`'s docstring says the order in this form:

1. `zip_lock` is taken first, and under it `cache_lock`, `held_lock` and `warnings_lock` may be
   taken, one at a time, never two at once (`_zip_folder` makes a `_Private`, whose constructor
   takes `held_lock`, and removes one, which takes `cache_lock`, then `warnings_lock` through
   `_warn_later`, then `held_lock` through `_drop`, each released before the next).
2. `stack_size_lock` is taken first, and under it a home's own `lock` (`_start_guest`, at two
   sites).
3. Every other lock is a leaf: nothing is taken under `pool_lock`, `live_lock`, `warnings_lock`,
   `epoch_callback_lock`, `outputs_lock`, `tool_threads_lock`, `cache_lock`, `held_lock`,
   `sessions_lock`, `closers_lock`, `ticker_cond`, `defaults_lock`, a `compiling` guard, a
   session's `lock` or a home's `lock`.
4. `warnings_lock` is held only inside `_warn_later` and `_flush_warnings`, and
   `_flush_warnings` runs outside every other lock (spec 084), so an embedder's `showwarning`
   can take any lock it likes.
5. `outputs_lock` is re-entrant; no other lock is.

The docstring also says the rule for a change: a new lock is a leaf unless this list is amended,
and the amendment names the pair. The builder re-runs the scanner on 104's tip (where the
functions carry module prefixes, so the bare-name rule reads `_x.name()` as a call on a package
module: the scanner's module set is the file's imports, and the builder adds the package's
modules to what it follows) and on the built commit, and pastes both outputs into the landing
notes; the pairs must be these four and no other.

### 7. How the judge sees it

The fast tier, run in the builder's worktree against the frozen baseline set (the `v0.1.0a7`
release's, verified against its `SHA256SUMS`; the memo, section 8), gives the same verdicts as
the baseline record: `uv run python tests/harness/sameness.py <baseline>.json <this>.json` prints
only the new rows (the three checks of Decisions 3 and 5 and the unit rows), which the claim list
names. No fuel row moves: no guest byte changes, and the host's work per call changes by one
attribute read per state access. No golden output, gap, allowance or progress file is edited.
`ruff check` and `ruff format --check` are clean on `src/` and `tests/`.

### 8. Where this meets the rest of the chain

- **103** (`103-the-engine-seam.md`, drafted on this branch the same day) makes
  `src/wasi_python/_wasmtime_ffi.py`, which "holds no mutable state: constants, functions and
  one class" and is reset at no fork and released at no exit (READ, its Decisions 1 and 7). So
  `_Process` takes nothing from it; the two rules checks of Decision 5 scan it like any sibling
  and expect no hit (its `NEEDED` table is an upper-case display). The `_epoch_callback` object
  and the output table, which 103 keeps in the runner's modules, are group F's `epoch_callback`
  and group G's `outputs` here.
- **104** (`104-the-runner-becomes-a-package.md`, in the tree) leaves "every lock, cache, hook
  and counter" a module global in the module its functions moved to, keeps `_after_fork_in_child`
  and `_release` in `runner.py` reaching them as `_module.name`, and says "Spec 105 gathers
  process state into one object. This specification does not" (READ, its Decision 4). This
  specification deletes those module globals, both hooks' bodies (their registrations move to
  `_process.py`), and the `global` statements that remain after 104 (`runner.py`'s two-name
  statement in the fork hook and `_watch`'s; today four lines, EXECUTED); `grep -nE
  '^\s*global ' src/wasi_python/*.py` finds none afterwards. 104's check 1 is retired for
  Decision 3's (Decision 3); its checks 2 and 3 learn `_process` and `process` (Decision 1).
- **107** keeps its fallback for the platform: this specification gives `_Process` no `platform`
  field, so a check binds a platform as 107's module name says
  (`monkeypatch.setattr(_platform, "PLATFORM", …)`; READ, 107's "How a check binds a platform",
  which names that fallback). Group D's three tables (`kernel_identity`, `win_api`, `stack_api`)
  leave `_Process` for 107's platform object when 107 lands, as 107 says; group D exists here so
  that nothing is a module global in between.
- **106** (typed call state, explicit lifecycles, a type checker) reads group G: `calls` is the
  thread-local whose `stack` holds `_Call`s, and `_State` is what `sessions`, `dropped` and
  `start_ending` carry. The type checker 106 adds sees every attribute typed in
  `_Process.__init__`.
- **107** (`mounts.py` behind a call-context protocol, one platform module, one stamp) reads
  groups D, F and G: `exiting`, `ctrl_c_pending` and `ticker_count`, which `mounts.py` reads
  through `process()` after this specification, become the protocol's `exiting()`,
  `ctrl_c_pending()` and `deadline_passed()`; the platform tables of group D move behind
  `_platform.py`'s interface; the twenty names that stay in Decision 4 are its allowance list to
  shrink.
- **108** adds the check that enforces Decision 4's rule, with the allowance list.

## Intent

The process's state has one owner, made in one place, reset for a fork in one method that finds
every lock by looking rather than by a list, and released at exit by one method. The judge
reaches the runner's seams through that one object and nothing else, so the refactors that follow
(106, 107) move code without breaking tests that test nothing about behaviour. Two rules checks
keep it so: no lock and no mutable at module level outside `_process.py`.

## Design

| file | change |
|---|---|
| `src/wasi_python/_process.py` | new: `_Observers`, `_Process` (Decision 1's groups, `reset_after_fork`, `release_at_exit`, the `remove_zips` and `flush_warnings` callables the zip and warnings modules register), `process()`, the `register_at_fork` and `atexit` registrations, the lock order in the docstring (Decision 6) and the judge's rule (Decision 4) |
| the ten modules of 104 and `runner.py` | every module-level mutable and lock deleted; every read and write becomes `process().<attr>`; `_after_fork_in_child` and `_release` deleted with their `global` statements; the eight hooks, `_drive_folder`'s default and the reaper flags read from `process().observers`; `_epoch_ticker` reads `process().ticker_*` |
| `src/wasi_python/__init__.py` | `_defaults_lock` deleted; `set_defaults` takes `process().defaults_lock` |
| `src/wasi_python/mounts.py` | lines 723–724 and 852 read `process()` (Decision 4's table) |
| `tests/unit/test_process.py` | new: Decision 3's four rows (the introspective fork check, the `RENEW` row, the reset and kept fields) |
| `tests/unit/test_runner_package.py` (104's) | check 1 retired (Decision 3); check 2's `ORDER` gains `_process` first; check 3's by-name list gains `process` (Decision 1) |
| `tests/release_shards.toml` | `tests/unit/test_process.py` in `own-runner` (spec 063's rule (g), as 104 did for its file) |
| `tests/harness/scan.py` | `module_lock_hits`, `module_mutable_hits` (Decision 5) |
| `tests/checks/test_rules.py` | the two rules checks |
| `tests/unit/test_scan.py` | two unit rows for the scanners |
| the fifteen test files of Decision 4's table | each line named there |
| `CHANGELOG.md` | one line under the unreleased section (below) |

Nothing under `scripts/`, `recipes/`, `downloads/` or the release workflow changes. No pin, no
artifact byte, no line of `tests/public_api.txt`, no dependency.

**The CHANGELOG line**, under the unreleased section: "**The runner's process state has one
owner** (spec 105): every lock, cache, counter and registry of the runner is an attribute of one
`_Process` object, reset for a fork by introspection over its locks and released at exit by one
method; the judge's seams are fields of that object, not module globals; two rules checks keep
locks and mutables out of module level. No public name changes."

**The roadmap line** (`context/roadmap.md`, the reserved list): "Reserved: 105 (one owner for
the process's state: `_process.py`, one object with every lock, cache and registry, a fork reset
by introspection and one exit release; the test seams move onto it; two rules checks keep locks
and mutables off module level; parallel-safe, stacked on 104, the third of the chain 103–108 from
the design review memo of 2026-10-20)."

## Scope

In: Decisions 1 to 7. Out:

- **The twenty function seams the unit files still patch by name** (Decision 4): 107's
  platform module and call-context protocol, and 108's enforcing check.
- **Typed call state, the session and home phase enums** (H3): 106.
- **`mounts.py`'s imports of the runner** beyond the three state reads (H4): 107.
- **The engine adapter** (H2): 103, below this in the chain.
- **A change to what is locked or when** (Decision 6): none here; a finding that one is needed
  is its own specification.
- **A change to any default, limit or public name**: none.

## Acceptance criteria

1. **`_process.py` holds every name of Decision 1's table**, each with its type in `__init__`,
   and `grep -nE '^_[a-zA-Z_]+( *:[^=]+)? *= ' src/wasi_python/*.py` outside `_process.py`
   matches only constants (upper-case names, sentinels, regexes, callbacks): the builder pastes
   the remaining matches into the landing notes.
2. **Both rules checks were seen failing first**, on 104's tip, with their counts recorded (14
   locks and 38 mutables at `a9064a2`, EXECUTED; the builder's numbers on 104's tip), and pass
   on the built commit. Their two unit rows pass.
3. **The fork check of Decision 3 passes**, its record of at least four names, and the `RENEW`
   row with it; the three real-fork checks it names pass with their reads moved to `process()`
   (on POSIX; they skip on Windows as today); 104's check 1 is retired and named in the
   `--accept-judge` reason; a run of `tests/unit/test_process.py` on 3.11, if the builder has
   one, is recorded.
4. **No `global` statement** remains in `src/wasi_python/` (criterion of Decision 8; today four
   lines).
5. **Every test line of Decision 4's table changed**, and no test in `tests/` names a moved
   state global or a hook by its old spelling: `grep -rnE '\brunner\._(held|sweep_state|ctrl_c|
   fork|calls|engines|zips|outputs|pool|pools|live|hook|sessions|closers|reaper|reaper_queue|
   dropped|modules|digests|identity|warned|pending_warnings|counts|tool_threads|compiling|
   linkers|epoch_ticker|[a-z_]*_lock|after_walk|on_entry|on_arm|on_export|after_export|on_call|
   session_clock|start_ending|drive_folder)\b' tests/` finds nothing (today 96 lines, EXECUTED,
   `--include='*.py'`); the same for the module names 104 introduced in place of `runner`.
6. **Sameness.** The builder's fast tier on the frozen baseline set and the baseline record
   differ only in the rows the claim list names (Decision 7), by `tests/harness/sameness.py`.
   No fuel row moves; no pass is lost.
7. **Thread-safety unchanged**: the corrected scanner of Decision 6 (`build/105/lock_order.py`,
   its two reports, attribute locks matched, calls followed transitively), run on 104's tip and
   on the built commit, finds the four pairs Decision 6 lists (`stack_size_lock` over a home's
   `lock`; `zip_lock` over `cache_lock`, `held_lock` and `warnings_lock`) and no other; the
   builder pastes both outputs into the landing notes.
8. **The judge.** `uv run pytest -m "not slow" -n 6` in the worktree, green; `ruff check` and
   `ruff format --check` clean. The lane accepts the chain's wave with `--accept-judge` naming
   this specification's three checks and unit rows.
9. **The release.** One dispatch of the release workflow on the chain's final tip (the memo,
   section 8), every job green on all three systems, stands for this specification's "built";
   its run id goes in the landing notes.

## For the lane

- **Kind:** parallel-safe; a judge change. In the chain's wave it is the third entry, rebased
  onto 104's landed or wave tip in order; its conflicts, if any, are in the ten modules 104
  made (every one a deleted global or a `process().` read) and in the fifteen test files of
  Decision 4, each named at the rebase.
- **Shares files with:** 104 (every module of the package; this one deletes what 104 placed),
  106 (the typed `_Call` and `_State` that groups G and H name), 107 (`mounts.py`'s three reads
  and `_platform.py`'s tables), and any open specification that adds a module-level lock or
  mutable under `src/` (the rules checks of Decision 5 would fail it; its builder moves the name
  onto `_Process` at the rebase).
- **The claim list** (each line starts "105:"; the numbers are the builder's):
  - 105: **new checks, each passing:**
    `tests/checks/test_rules.py::test_no_lock_is_made_at_module_level_outside_the_process`,
    `tests/checks/test_rules.py::test_no_mutable_is_bound_at_module_level_outside_the_process`
    (both rules; no fuel).
  - 105: **unit rows:** `tests/unit/test_process.py` gains four; `tests/unit/test_scan.py` gains
    two; `tests/unit/test_runner_package.py` loses one (104's check 1, retired for Decision 3's).
  - 105: **retired checks:** 104's `test_every_module_level_lock_is_remade_after_fork`, replaced
    by `test_reset_after_fork_renews_every_lock_it_can_see` (Decision 3). **Lost passes:** none
    beyond that named retirement. **Rows that grow:** none (no artifact byte, no guest work).
  - **The judge hash changes** in `tests/checks/test_rules.py`, `tests/harness/scan.py`,
    `tests/unit/test_process.py`, `tests/unit/test_scan.py`, `tests/unit/test_runner_package.py`,
    `tests/release_shards.toml` and the fifteen test files of Decision 4.
- **The flags** (paste-safe; the lane folds them into the wave's):

  ```
  --accept "105: the runner's process state has one owner: every lock, cache, counter, pool, live set, reaper handle, sweep field, Ctrl-C flag, output table and thread-local is an attribute of one _Process object in _process.py, reset for a fork by introspection over its locks and released at exit by one method; the judge's seams (the eight hooks, the session clock, the closer starter, the drive folder, the reaper's enabled and paused flags) are fields of process().observers; no public name changes"
  --accept-judge "105: two rules checks, no threading.Lock, RLock or Condition and no mutable container or stateful object bound at module or class level under src/wasi_python outside _process.py (exceptions: __all__, upper-case display tables, ctypes _fields_); a unit check that reset_after_fork renews every lock, condition and queue it can see by the RENEW type-to-factory table, a row that RENEW knows the four kinds, and two rows for the reset and kept fields; unit rows for the two scanners; 104's module-level fork check retired for it (no module-level lock remains to walk); 104's import-order and by-name checks learn _process and process; the tests that set the runner's seams or read its state do so through process(); no existing expectation edited"
  ```

- **Dry-run needs:** none of its own; the chain's one dispatch on its final tip (criterion 9).

## One line

One object owns the runner's state, resets it for a fork by looking at itself, and carries the
judge's seams; two rules checks keep every lock and mutable off module level, and no public name
moves.

## Landing notes

Built 2026-10-20 in the worktree `/home/user/wt/105`, branch `spec/105-one-owner-for-the-process-state`,
from the base `2a9546c` (104's built tip on `spec/104-the-runner-becomes-a-package`, under build
review: main `5feb7e9`, the memo `a9064a2`, the chain's specifications and reviews, 103's and
104's commits). Every number here is EXECUTED on that base or on the built commit, with its
command; the outputs are kept under `build/105/` in the worktree (git-ignored):
`rules_proto-on-base.txt`, `seen-failing.txt`, `seen-failing-full.txt`, `test-sites-on-base.txt`,
`lock_order_pkg.py`, `lock_order-on-base.txt`, `lock_order-on-tip.txt`, `lock_order-whole-package.txt`, `fast.log`, `built.json`,
`claims.toml`, `claims-chain.toml`, `sameness-104.txt`, `sameness-baseline.txt`,
`sameness-baseline-chain.txt`. The writer's scratch `lock_order.py` and `rules_proto.py` are
copied there from the main tree's `build/105/`.

- **Commits, in the order built** (the hashes after the rebase onto 104's `538e831`; before it
  `e11c70a`, `591841b` and `27682ab` on `2a9546c`): `a73b0fe` (the checks first: `scan.module_lock_hits` and
  `scan.module_mutable_hits`, the two rules checks, two scanner rows in
  `tests/unit/test_scan.py`, `tests/unit/test_process.py` with its six rows, the shard line;
  all seen failing on the base), `1f959c2` (`_process.py`; every module-level lock, mutable,
  hook and seam of the twelve modules moved onto `_Process`; the fork hook and the exit release
  deleted from `runner.py` with their `global` statements; `mounts.py`'s three reads; the
  twenty-one test and harness files re-pointed at `process()`; 104's check 1 retired and its
  checks 2 and 3 taught `_process`, `process` and `mounts.py`'s late import of the owner;
  `api.py`'s module table; `mounts.py`'s held count), `e96f1b9` (this Status line and these
  notes, as first written on `2a9546c`), and the commit after it (the rebase's record below).
- **Rebase** (the coordinator, 2026-10-20): 104 gained two commits after this build's base (its
  build review's three Lows in `tests/unit/test_runner_package.py`: `_patched` builds its module
  map per file from `import wasi_python [as Z]` and `from wasi_python import X [as Y]`;
  `FORK_WALK` imports `_wasmtime_ffi`, `cli` and `tools`; `_is_unchanging` recurses into a
  tuple's and a frozenset's elements) and was rebased onto the PR branch, its tip `538e831`.
  `git rebase --onto 538e831 2a9546c` replayed the three commits with **one conflict, in
  `tests/unit/test_runner_package.py`**, on the code commit: 104's side (HEAD) carried the fork
  tables (`LOCKS_RESET_BY_FORK`, `REBOUND_BY_FORK`, `NOT_RESET`, `TICKER_COND`), `FORK_WALK` with
  its new import line, `_fork_walk`, `_hook_targets` and check 1 with its widened docstring; this
  side replaced that whole region with the `SENTINELS` line that names `process`. **Kept: this
  side's retirement** (check 1 and its tables gone, as Decision 3 says, `FORK_WALK`'s new import
  line with them, since the walk no longer exists) **and both of 104's fixes outside the region**,
  which merged without conflict and stay (`_patched`'s per-file alias map, which `_seam_errors`
  reads, and `_is_unchanging`'s recursion into tuple and frozenset elements, which check 3
  reads). `ORDER` (`_process` first), `LATE` (`mounts.py`'s binding of the owner) and
  `RUNNER_MODULES` are this side's, unconflicted. On the rebased tree `ruff check --fix` also
  reordered `tests/unit/test_process.py`'s two `wasi_python` imports (isort's order on the
  rebased configuration; no other change), folded into the code commit. After the resolution:
  `ruff check` and `ruff format --check` clean; `uv run pytest tests/unit/test_runner_package.py
  tests/unit/test_process.py tests/unit/test_scan.py tests/checks/test_rules.py -q` → 1 failed,
  265 passed, 3 skipped, the one failure `test_version_states_the_platform_semantics`, a
  baseline failure of the older artifact set. The fast tier and the sameness lines below are
  the rebased tip's; the run before the rebase is kept under them.
- **CI: none of its own; the chain's one dispatch on the final tip** (criterion 9, the owner's
  rule for the chain); its run id is the integrator's to write here when that dispatch is read.
  The fast tier below is the build's judge.
- **The base re-measured (EXECUTED on `2a9546c`):** `uv run python -I build/105/rules_proto.py
  src/wasi_python` (`build/105/rules_proto-on-base.txt`): **14 LOCK lines and 40 MUTABLE lines,
  38 without the two `_fields_`**, byte-for-byte the spec's `a9064a2` list with 104's module
  names in place of `runner.py`; the two rules checks on the base (criterion 2,
  `build/105/seen-failing-full.txt`): **14 locks** (`__init__` 1, `_call` 3, `_engines` 2 with
  `_epoch_ticker._cond`, `_home` 1, `_private_dirs` 2, `_sessions` 2, `_zip` 1, `runner` 2) and
  **38 mutables** (`_artifacts` 3, `_call` 8, `_engines` 5, `_home` 3, `_places` 1, `_platform`
  4, `_private_dirs` 4, `_sessions` 5, `_zip` 1, `runner` 4). `grep -nE '^\s*global '
  src/wasi_python/*.py`: **2 lines** on the base (`_call.py:759` `_epoch_callback`,
  `runner.py:536` `_pool_lock, _live_lock`; the spec's four at `a9064a2` were 104's two
  three-name statements folded into one each) and **none** on the built commit (criterion 4).
  The unit files' `monkeypatch.setattr(<module>, "_name", …)` lines (the problem statement's
  grep, with 104's module names, `tests/unit/*.py` less `test_runner_package.py`): **50 lines, 30
  distinct names** on the base (the spec's 51 and 31 at `a9064a2` less `_context_address`, which
  103 deleted); **38 lines, 19 names** on the built commit: the eleven names Decision 4 moves
  (`_engines` twice, `_zips`, `_modules`, `_warned`, `_pending_warnings`, `_held`, `_sessions`,
  `_reaper_queue`, `_dropped`, `_on_entry`, `_start_ending`: 12 lines) are gone, and the ones
  that stay are the twenty of Decision 4 less `_context_address`: `_ctrl_c_watched` (8),
  `_remove_tree` (5), `_try_lock` (2), `_trap_handlers_ready` (2), `_stop_error` (2),
  `_module_miss` (2), `_guest_stack` (2), `_epoch_now` (2), `_drop` (2), `_dir_fd_ok` (2),
  `_win_open`, `_walk_grants`, `_unlock_close`, `_tell_interpreter`, `_stack`, `_join_guest`,
  `_found_and_checked`, `_drive`, `_close_held` (1 each); in the checks `_guest_stack` (2),
  `_check_preopens` and `_current_defaults` (1 each). **Criterion 5's grep**, widened to 104's
  module names (`\b(runner|_home|…|wasi_python)\._(held|…|after_fork_in_child)\b`,
  `build/105/test-sites-on-base.txt`): **111 lines** on the base; on the built commit it finds
  only `_try_lock` (9 lines: a function seam, matched by the `[a-z_]*_lock` alternative) and
  `api.py`'s two `"wasi_python._engines"` module names, no state global and no hook.
- **Criterion 1's grep** (`grep -nE '^_[a-zA-Z_]+( *:[^=]+)? *= ' src/wasi_python/*.py` outside
  `_process.py`) matches only constants, sentinels, regexes, callbacks, aliases and dunders:
  `__init__` `__version__`, `__all__`; `_artifacts` `_ARTIFACT_DIR`, `_ARTIFACTS_ENV`,
  `_CHECKOUT_ARTIFACT_DIR`; `_engines` `_CHECK_WAT`; `_home` `_GUEST_SLICE`, `_DONE`; `_limits`
  `_UNSET`; `_places` `_DIR`, `_WALK_ACCESS`, `_STAT_ACCESS`, `_SHARE_READ_WRITE`,
  `_OPEN_EXISTING`, `_BACKUP_SEMANTICS`, `_OPEN_REPARSE_POINT`, `_ATTRIBUTE_DIRECTORY`,
  `_ATTRIBUTE_REPARSE_POINT`, `_WIN_DEVICES`, `_WIN_RESERVED_CHARS`; `_platform` `_BUSY`,
  `_WASM_STACK`, `_HOST_ROOM`, `_THREAD_STACK`, `_TRAP_SIGNALS`, `_TRAP_HANDLERS_REPLACED`;
  `_private_dirs` `_LOCK_NAME`, `_REMOVE_BUDGET`, `_REMOVE_BATCH`, `_SWEEP_TRIES`, `_DIR_OPEN`;
  `_sessions` `_WAKE`, `_CLOSER`; `_wasmtime_ffi` `__all__`, `_RECORDS`, `_HANDLE`,
  `_EPOCH_FINALIZER`; `mounts` `_ERRNO_ALIASES`, `_HOST_ERRNO`, `_RAISED`, `_ERRNO_SLOT`,
  `_Listing`, `__all__`; `tools` its 38 upper-case constants, `_KeySets` and `__all__`.
  `_process.py`'s own module-level names: `RENEW`, `_Observers`, `_Process`, `_PROCESS`,
  `process`.
- **Sizes after the move (`wc -l`):** `_process` 238, `__init__` 117, `_artifacts` 222, `_call`
  1,171, `_engines` 265, `_home` 344, `_limits` 171, `_places` 915, `_platform` 390,
  `_private_dirs` 560, `_sessions` 952, `_zip` 285, `runner` 1,164, `mounts.py` 2,213 (one more
  than 104's 2,212: the late import of the owner and its binding, less the unused `r =
  self._runner`; `ALLOWED` in `tests/checks/test_rules.py` reads the measured 2,213, as 104 set
  2,212), `tools.py` 2,450. `git diff --stat 2a9546c`: 35 files, +1,277 −761 (`src/` 13 files
  +624 −476; `tests/` 22 files +653 −285).
- **The checks were seen failing first (criterion 2; `build/105/seen-failing.txt`):**

```
== 2a9546c (104's tip, the base), 2026-10-20: the two rules checks before _process.py ==
E       AssertionError: findings: 14 finding(s), digest 66c511bb8226: src/wasi_python/__init__.py:57: _defaults_lock (Lock); src/wasi_python/_call.py:753: _epoch_callback_lock (Lock); src/wasi_python/_call.py:867: _outputs_lock (RLock); src/wasi_python/_call.py:1128: _tool_threads_lock (Lock); src/wasi_python/_engines.py:86: _lock (Lock); +9 more
E       AssertionError: findings: 38 finding(s), digest e96cbee45bfe: src/wasi_python/_artifacts.py:120: _versions (Dict); src/wasi_python/_artifacts.py:137: _guest_packages (Dict); src/wasi_python/_artifacts.py:158: _digests (Dict); src/wasi_python/_call.py:769: _linkers (Dict); src/wasi_python/_call.py:770: _mount_linkers (Dict); +33 more
FAILED tests/checks/test_rules.py::test_no_lock_is_made_at_module_level_outside_the_process
FAILED tests/checks/test_rules.py::test_no_mutable_is_bound_at_module_level_outside_the_process
2 failed, 47 deselected in 0.35s

-- tests/unit/test_process.py (the six rows) on the base --
E   ImportError: cannot import name '_process' from 'wasi_python' (/home/user/wt/105/src/wasi_python/__init__.py). Did you mean: '_places'?
ERROR tests/unit/test_process.py
1 error in 0.21s
```

  The two scanner rows of `tests/unit/test_scan.py` passed on the base once written (they read
  fixture modules, not the tree); the mutable row's first draft expected `c (Set)` for `c =
  set()`, a call, and found `c (set)`, and showed that the prototype paired no tuple target with
  a tuple value (`t, u = [], {}` escaped it), which the scanner now does. On the built commit
  the two rules checks, the two scanner rows, the six rows of `test_process.py` and 104's three
  remaining checks pass (`uv run pytest tests/unit/test_process.py
  tests/unit/test_runner_package.py tests/checks/test_rules.py::… tests/unit/test_scan.py::… -q`:
  15 passed, 2.24 s).
- **The fork check on the project's minimum Python (criterion 3):** `PYTHONPATH=src:tests uv run
  --python 3.11 --no-project --with pytest python -m pytest tests/unit/test_process.py -q` →
  **6 passed** on CPython 3.11.17, and **6 passed** on 3.12.3 the same way; the judge's own run is
  on 3.13.16. The three real-fork checks pass with their reads moved:
  `tests/unit/test_runner_tools.py::test_the_fork_hook_resets_the_tool_thread_count`
  (`FORK_HOOK` reads `process().tool_threads_lock`),
  `tests/checks/test_v1_4_embedding.py::test_a_forked_child_is_refused` (`NO_FORK` prints
  `process().fork_used, process().forked`) and
  `::test_a_forked_child_leaves_the_parents_zip_folder`, with
  `tests/unit/test_runner_async.py::test_a_forked_child_of_a_used_runner_is_refused`: 7 passed
  by node id in 28.38 s on the built tree.
- **The lock order (criterion 7; `build/105/lock_order_pkg.py`, the corrected scanner extended
  to the package: one module set, `_x.f()` resolved into module `_x`, a bare name resolved in
  its own module and then in the one module that defines it, so a class imported by `from`
  such as `_Private` is followed into its `__init__`, a method call into every class that
  defines the method, a call on an imported non-package module into nothing). Over the twelve
  runner modules (`mounts.py`, `tools.py` and `cli.py` left out as the spec's scanner left them
  out of `runner.py`: their methods share names with the runner's and the ambiguous resolution
  reports false paths through `tools._Bounded`). On the base:**

```
== (1) a with over a lock nested in another, in one function ==
_stack_size_lock > home.lock   (_home._start_guest:270)
_stack_size_lock > home.lock   (_home._start_guest:279)
== (2) a lock taken, transitively through calls, under a held lock: shortest path ==
_zip_lock > _engines._lock   (_zip._zip_folder > _private_dirs._Private.remove:108; held at _zip._zip_folder:47)
_zip_lock > _held_lock   (_zip._zip_folder > _zip._zip_folder_locked > _private_dirs._Private.__init__:48; held at _zip._zip_folder:47)
_zip_lock > _pending_warnings_lock   (_zip._zip_folder > _private_dirs._Private.remove > _private_dirs._warn_later:521; held at _zip._zip_folder:47)
_zip_lock > _held_lock   (_zip._zip_folder > _private_dirs._Private.remove > _private_dirs._drop:115; held at _zip._zip_folder:47)
== methods followed into every class that defines them ==
stop
```

  On the built commit:

```
== (1) a with over a lock nested in another, in one function ==
p.stack_size_lock > home.lock   (_home._start_guest:267)
p.stack_size_lock > home.lock   (_home._start_guest:276)
== (2) a lock taken, transitively through calls, under a held lock: shortest path ==
p.zip_lock > process().cache_lock   (_zip._zip_folder > _private_dirs._Private.remove:105; held at _zip._zip_folder:46)
p.zip_lock > process().held_lock   (_zip._zip_folder > _zip._zip_folder_locked > _private_dirs._Private.__init__:44; held at _zip._zip_folder:46)
p.zip_lock > p.warnings_lock   (_zip._zip_folder > _private_dirs._Private.remove > _private_dirs._warn_later:517; held at _zip._zip_folder:46)
p.zip_lock > p.held_lock   (_zip._zip_folder > _private_dirs._Private.remove > _private_dirs._drop:111; held at _zip._zip_folder:46)
== methods followed into every class that defines them ==
stop
```

  The four pairs of Decision 6 and no other, on both trees: `stack_size_lock` over a home's
  `lock` (two sites), `zip_lock` over `cache_lock`, `held_lock` (two paths) and `warnings_lock`.
  `stop` is the one method name two runner classes share (`_Home.stop` and the sessions'); it
  is followed into both and takes no lock. The same scanner over every module of the package
  (`build/105/lock_order-whole-package.txt`) adds only paths through `tools._ToolLoop._lock` and
  `tools._Bounded._lock`, those objects' own instance locks, reached by shared method names
  (`close`, `stop`, `call`, `read`, `write`, `fail`, `remove`) that the scanner follows into
  every class: false paths, not nestings.
- **The fast tier on the frozen `v0.1.0a7` set** (`WASI_PYTHON_ARTIFACTS=/home/user/wasi_python/build/baseline-a7/set/wasi-python-0.1.0a7`,
  `uv run pytest -m "not slow" -n 3 -q -p no:cacheprovider`, on `e96f1b9`, the rebased tip (its code is
  `1f959c2`'s), under the machine's `build/fast-tier.lock`): **83 failed, 2377 passed, 52
  skipped in 281.64s (0:04:41)**; the failures are the chain's
  baseline's `failing-nodes.txt` exactly (82 checks of an artifact set older than the tree, and
  `test_runner_grants.py::test_the_walk_judges_links`, which needs a non-root user). The record
  is `build/105/built.json`. **Before the rebase**, on `591841b` (the same code on `2a9546c`;
  `build/105/fast-591841b.log`, its record `build/105/built-591841b.json`): **83 failed, 2377
  passed, 52 skipped in 281.96s (0:04:41)**, the same 83. A first run, on the move's earlier form (`1d68dc5`; its failure
  list `build/105/failed-1d68dc5.txt`), gave **85 failed, 2375 passed, 52 skipped in 1626.84 s
  (0:27:06)**, two beyond the baseline:
  `test_v1_4_public_api.py::test_private_names_carry_an_underscore` found
  `wasi_python.process (import)`, the accessor bound by name in the public module without an
  underscore and not exported, so `__init__.py` now binds the module (`from . import _process`)
  and reads `_process.process().defaults_lock` (the fix, folded into `591841b`); and
  `test_build_progress.py::test_term_waits_for_the_step_then_stops_before_the_next[0]`, a pty
  that was "still open after 5000 reads" in a run five times slower than 104's 5:24 under another
  job's load (the load average fell from 1.83 to 0.27 as it ended), which passes alone by node
  id (2 passed, 2.75 s) and touches nothing this specification changes. The run above is the
  re-run on the final commit.
- **Sameness (criterion 6), on the rebased tip's record.** Against 104's built record
  (`/home/user/wt/104/build/104/built.json`), with `--claims build/105/claims.toml`:

```
note: explained by claims: 105 4
sameness exit 0
```

  Against the chain's baseline (`/home/user/wasi_python/build/baseline-a7/baseline.json`) with
  the chain's claims (`build/105/claims-chain.toml`: 103's, 104's and this one's concatenated):

```
note: explained by claims: 103 4 · 104 3 · 105 4
sameness exit 0
```

  Before the rebase (the record of `591841b`), both printed the same lines: `note: explained by
  claims: 105 4` / `sameness exit 0`, and `note: explained by claims: 103 4 · 104 3 · 105 4` /
  `sameness exit 0`.

  Without a claim list, against the chain's baseline, what prints is the chain's own work and
  nothing else (`build/105/sameness-baseline.txt`): 103's two rules checks and unit file, 104's
  ceiling check and unit file, this one's two rules checks and unit file, and the unit tally:

```
tests/checks/test_rules.py::test_no_lock_is_made_at_module_level_outside_the_process: only in the second record
tests/checks/test_rules.py::test_no_module_under_src_is_over_the_line_ceiling: only in the second record
tests/checks/test_rules.py::test_no_mutable_is_bound_at_module_level_outside_the_process: only in the second record
tests/checks/test_rules.py::test_only_the_engine_seam_touches_wasmtimes_private_api: only in the second record
tests/checks/test_rules.py::test_the_private_api_debt_is_documented: only in the second record
collected_files: tests/unit/test_process.py only in the second record
collected_files: tests/unit/test_runner_package.py only in the second record
collected_files: tests/unit/test_wasmtime_ffi.py only in the second record
suite: {'passed': 1833, 'skipped': 13, 'total': 1847} != {'passed': 1861, 'skipped': 13, 'total': 1875}
sameness exit 1
```

  The three records' `suite` lines: the baseline `{'passed': 1833, 'skipped': 13, 'total':
  1847}` (`a9064a2`), 104's `{'passed': 1854, 'skipped': 13, 'total': 1868}` (`ea08708`), this
  one's `{'passed': 1861, 'skipped': 13, 'total': 1875}` (`e96f1b9`, and `591841b` before the rebase): seven more rows, the one
  failing row (`test_the_walk_judges_links`) the same.

  The claim: `new` the two rules checks and `tests/unit/test_process.py`; `units = 7` (six rows
  in `test_process.py`, two in `test_scan.py`, one retired in `test_runner_package.py`). No row
  grows, no pass moves.
- **Lint (criterion 8):** `uv run ruff check src tests` and `uv run ruff format --check src
  tests` clean on every commit; `test_no_module_level_name_is_bound_twice` passes.
- **The judge's files (the claim list's hash line):** `tests/checks/test_rules.py`,
  `tests/harness/scan.py`, `tests/harness/api.py`, `tests/unit/test_process.py`,
  `tests/unit/test_scan.py`, `tests/unit/test_runner_package.py`, `tests/release_shards.toml`
  and sixteen test files re-pointed at `process()`: `test_v1_2_hostile_guest.py`,
  `test_v1_4_embedding.py`, `test_v1_4_public_api.py`, `test_v1_4_sessions.py`,
  `test_async_tools.py`, `test_runner_async.py`, `test_runner_calls.py`,
  `test_runner_cancel.py`, `test_runner_grants.py`, `test_runner_mounts.py`,
  `test_runner_sessions.py`, `test_runner_sets.py`, `test_runner_sweep.py`,
  `test_runner_threads.py`, `test_runner_tools.py` (Decision 4's fifteen) and `test_rules.py`'s
  `ALLOWED`. `tests/public_api.txt` is untouched (`git diff --stat 2a9546c` does not list it).

### The allowance list for 107 and 108: the test seams that stay, as built

Every name a unit or goal check still replaces by `monkeypatch.setattr(<module>, "_name", …)`
or by `m.setattr(…)` (the same fixture under a shorter name), or assigns by name as `<module>._name
= …`, each a function that fakes a platform answer or forces an error path, a constant, or a
class (Decision 4; EXECUTED on the built commit; the build review's finding 1 added the six lines
the first grep did not read): **nineteen functions in the unit files on 39 lines**
(`_context_address`, the twentieth of the draft, was deleted by 103), one constant and one class
in the unit files, two functions assigned by name in the hostile-guest programs, and three
functions in the checks. The tally reads both spellings of the fixture (`monkeypatch.` and `m.`)
and the `<module>._name = …` form, as 108's check will.

- Platform answers (107's `_platform.py` seam): `_guest_stack` (2 lines in the unit files, 2 in
  `test_v1_2_hostile_guest.py`), `_tell_interpreter`, `_trap_handlers_ready` (2), `_dir_fd_ok`
  (2), `_win_open`, `_close_held`, `_try_lock` (2), `_unlock_close`, `_remove_tree` (6 lines:
  five as `monkeypatch.setattr`, one as `m.setattr`, `test_runner_sweep.py:340`), `_drop` (2),
  `_drive` (assigned by name), `_stack`.
- Engine and call paths (107's call-context protocol or 106's typed call): `_ctrl_c_watched`
  (8), `_stop_error` (2), `_epoch_now` (2), `_module_miss` (2), `_found_and_checked`,
  `_join_guest` (assigned by name), `_walk_grants`.
- Constants and classes the unit files replace, for 107's platform seam or 108's list:
  `_REMOVE_BUDGET` (2 lines, `m.setattr(_private_dirs, "_REMOVE_BUDGET", 10_000,
  raising=False)`, `test_runner_sweep.py:740, 759`), `_Box` (`_home._Box = LateBox` and its
  restore, `test_runner_threads.py:215, 220`).
- Assigned by name in the hostile-guest programs, for 106's typed call or 107's protocol:
  `_drive_turn` (`_sessions._drive_turn, wasmtime.Store.close = drive_turn, close`,
  `test_v1_2_hostile_guest.py:3133`), `_abandon_turn` (`_sessions._abandon_turn = abandon`,
  `:3138`), beside `_drive` and `_join_guest` above.
- In the checks, for the same closers: `_guest_stack`, `_check_preopens`, `_current_defaults`.

None of these lines changes here: each is on the base as it is, and Decision 4 moves state and
seams, not function stand-ins. 108 seeds its allowance from this list.

Every seam the judge sets through the object, as built: `process().observers` fields
`on_entry`, `after_walk`, `on_arm`, `on_export`, `after_export`, `on_call`, `clock`,
`start_ending`, `drive_folder`, `reaper_enabled` (in two child programs), `reaper_paused`;
attributes of `process()`: `ticker_count`, `ctrl_c_pending`, `sweep_claimed`, `sweep_swept`,
`sweep_failed`, `warned`, `pending_warnings`, `held`, `fork_used`, `forked`, `engines`,
`modules`, `zips`, `sessions`, `reaper_queue`, `dropped`, `pool_lock`, `defaults_lock`; read:
`outputs`, `pool_size`, `tool_threads_lock`, `cache_lock`, `zip_lock`, `held_lock`,
`sessions_lock`, `closers`, `calls`, `ticker_count`.

### Differences from the specification's text, each with its reason

1. **`tests/unit/test_process.py` has six rows, not four**: Decision 3's four (the introspective
   fork check, the `RENEW` row, the reset fields, the kept fields) and two the builder's brief
   asked for, the exit release's order (`remove_zips` then `flush_warnings` run before the
   eight tables are cleared, and a fresh instance's defaults are no-ops) and the observers'
   refusal of a misspelt field (the slots, Decision 4). The claim's `units` is 7.
2. **`mounts.py` binds the owner in `_Files.__init__`**, through a late import named in 104's
   `LATE` list (`("mounts.py", "_Files.__init__", "_process")`), as `self._process = process()`,
   and reads `self._process.exiting`, `.ctrl_c_pending` and `.ticker_count`: 104's check 2
   forbids `mounts.py` a package import at module level, and the instance is never rebound
   (a fork resets it in place), so binding it on the object reads the same attributes
   `process()` would. The unused `r = self._runner` line of the flush method went with its one
   use; `mounts.py` is 2,213 lines and `ALLOWED` says so.
3. **`_drive_folder` is `_default_drive_folder`**, the name Decision 4's call form gives it:
   `(process().observers.drive_folder or _default_drive_folder)(drive)`.
4. **104's retired check took its tables with it**: `LOCKS_RESET_BY_FORK`, `REBOUND_BY_FORK`,
   `NOT_RESET`, `TICKER_COND`, `FORK_WALK`, `_fork_walk` and `_hook_targets` are deleted, and
   `_by_name_errors` loses its "the fork hook rebinds it" branch, since no module-level name is
   rebound by a fork any more (the by-name rule's `_is_unchanging` is what remains).
   `RUNNER_MODULES` is `ORDER` less `_wasmtime_ffi` (twelve modules: `_process` is a runner
   module for checks 3 and 4), not `ORDER[1:]`.
5. **The lock-order scanner is a package scanner**, `build/105/lock_order_pkg.py`, since the
   functions sit in twelve modules on 104's tip; Decision 6's "the builder adds the package's
   modules to what it follows" is its module-set argument and the `_x.f()` rule above; two
   defects of the first package run were fixed before the output above was taken (a class
   imported by `from` was not followed into its `__init__`, so `_Private.__init__`'s
   `held_lock` was missed; a method's path named its class without the method).
6. **The mutable scanner pairs a tuple target with a tuple value** (`a, b = {}, []`), which the
   prototype did not; the unit row `t, u = [], {}` pins it.
7. **`test_every_entry_runs_on_a_guest_thread_with_room`** takes `monkeypatch` and restores the
   entry hook with `monkeypatch.undo()`, where it saved and restored `_home._on_entry` by hand.
8. **`__init__.py` binds the owner's module, not its accessor**: `from . import _process` and
   `_process.process().defaults_lock`, where Decision 1 has every module do `from ._process
   import process`. The public module may bind only exported names and underscored ones
   (`test_v1_4_public_api.py::test_private_names_carry_an_underscore` found
   `wasi_python.process` on the first form); `__init__.py` is above 104's order, so the by-name
   rule does not read it either way.
9. **The counts of Decision 4 on this base**: 30 names on 50 lines, 11 moved on 12 lines, 19
   stay on 38 lines (above), against the draft's 31, 51, 12 and 20, 39 at `a9064a2`.
10. **Criterion 4's "today four lines"** is two on 104's tip (104 folded the hook's three
   `global` statements into one); none remain.
11. **The ticker's `count()` stays** as the production read in `_call.py` and `_sessions.py`,
    returning `process().ticker_count` (Decision 1); the judge and `mounts.py` read the attribute.

### For the lane

- Kind: parallel-safe; a judge change; third entry of the chain's wave, stacked on 104's
  `2a9546c`; conflicts by construction with every chain entry in `src/wasi_python/` (the chain
  rebases in order).
- The claim list (`build/105/claims.toml`): one claim, `spec = "105"`, `new = [the two rules
  checks, "tests/unit/test_process.py"]`, `units = 7`. No row grows, no pass moves; the one
  retired row is a unit row (104's `test_every_module_level_lock_is_remade_after_fork`), carried
  by `units`.
- The flags (paste-safe):

  ```
  --accept "105: the runner's process state has one owner: every lock, cache, counter, pool, live set, reaper handle, sweep field, Ctrl-C flag, output table and thread-local is an attribute of one _Process object in _process.py, reset for a fork by introspection over its locks and released at exit by one method; the judge's seams (the eight hooks, the session clock, the closer starter, the drive folder, the reaper's enabled and paused flags) are fields of process().observers; no public name changes"
  --accept-judge "105: two rules checks, no threading.Lock, RLock or Condition and no mutable container or stateful object bound at module or class level under src/wasi_python outside _process.py (exceptions: __all__, upper-case display tables, ctypes _fields_); a unit check that reset_after_fork renews every lock, condition and queue it can see by the RENEW type-to-factory table, a row that RENEW knows the four kinds, two rows for the reset and kept fields, a row for the exit release's order and one for the observers' slots; unit rows for the two scanners; 104's module-level fork check retired for it (no module-level lock remains to walk); 104's import-order and by-name checks learn _process and process, and its late-import list mounts' binding of the owner; api.py's module table gains _process.py; mounts.py's held line count is its measured 2,213; the tests that set the runner's seams or read its state do so through process(); no existing expectation edited"
  ```

- Dry-run needs: none of its own; the chain's one dispatch on its final tip (criterion 9).
- **The CHANGELOG line** (the integrator's, not the builder's: the brief kept `CHANGELOG.md`
  for the lane, which adds this text under the unreleased section at the landing): "**The runner's process state has one owner** (spec 105):
  every lock, cache, counter and registry of the runner is an attribute of one `_Process`
  object, reset for a fork by introspection over its locks and released at exit by one method;
  the judge's seams are fields of that object, not module globals; two rules checks keep locks
  and mutables out of module level. No public name changes."

### The builder's self-check

- rebased onto the named stacked base today (104's `2a9546c`); the base commit in the Status
  line: checked.
- CI run dispatched on this exact commit and read: **unchecked by the chain's rule** (one
  dispatch on the chain's final tip; 105 dispatches none). The chain's run id is written into
  these notes, under "CI", by the integrator when the final tip's dispatch is read (the build
  review's finding 2).
- every number from a measured run on this base, labelled EXECUTED; the growth list is this
  build's (empty): checked.
- "For the lane": the claim list, the exact flags, each reason beginning with the spec number,
  the wave kind, dry-run needs: checked.
- every new check seen failing first: checked (the two rules checks and the unit file, above;
  the scanner rows read fixtures). A Windows and a Linux branch: none added; `register_at_fork`
  keeps its `hasattr` guard in `_process.py`, and the real-fork checks skip on Windows as
  before.
- every gap names its closer; every reserved follow-up has a roadmap line: checked (no new gap;
  the roadmap line is in Design, `context/roadmap.md` untouched by the builder's brief).
- packages.toml has its reason line; README rows the spec changes listed: not applicable (no
  package, no README row).
- CHANGELOG under the one unreleased section: **unchecked** (the brief: do not touch
  `CHANGELOG.md`). The line is the integrator's: its text stands under "For the lane" above, and
  the lane adds it under the unreleased section at the landing (the build review's finding 2).
- ruff check, ruff format --check, the fast tier: green (the baseline's 83), output in
  `build/105/`: checked.
