# 103 — The runner becomes a package: one module per concern

- **Status:** **built on `dcd5fbe` on `spec/103-the-runner-becomes-a-package`, stacked on
  102's `c15adf4`, 2026-10-20, reviewed** (`../reviews/103-the-runner-becomes-a-package-2026-10-20.md`:
  lands; the landing notes below; the code's last commit is `dcd5fbe`, the review's three Lows,
  on `ea08708`, the build the review read at `2a9546c`). Drafted 2026-10-20 on
  `claude/gallant-ride-9nxxmn` (tree `a9064a2`) from main `5feb7e9`, with its research; its
  pre-build review is `../reviews/103-the-runner-becomes-a-package-spec-2026-10-20.md`. It is
  the second of the chain 102 → 103 → 104 → 105 → 106 → 107 (the memo's section 8): 104, 105 and
  106 build on its module list, so the list is the contract this file fixes. A different agent
  reviews the build.
- **Date:** 2026-10-20
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe** (§5.7). It changes `src/wasi_python/` only (the runner's text moved
  into eleven modules, `__init__.py`'s and `mounts.py`'s import lines), plus the mechanical
  import updates in the 24 test and harness files that name runner privates, one rules check,
  one unit file, one shard line and the API harness's module tables. It changes no artifact
  byte, no guest import or export, and **no line of `tests/public_api.txt`** (`runner`, `mounts`
  and `cli` are documented internal; spec 049). It is a judge change (the lane accepts with
  `--accept-judge`). No growth: no fuel row and no byte row can move.
- **Depends on:** **102** (the engine seam: `src/wasi_python/_wasmtime_ffi.py`, which every
  `_ffi` call site below already reads; built and reviewed, not landed, hence the stack). Landed:
  049 (the public API frozen; `DEFAULTS` read through one helper), 015 (fork and `run_async`'s
  pool), 016 and 084 (`_private_dirs`: the lock protocol, a private root never outlives its
  call), 017 and 076 (`_places`: grants judged by identity, the Windows walk), 023 (`_zip`:
  matplotlib's data), 055 (`_sessions`), 071 (`_platform`: the trap-handler guard), 078
  (`_home`: each guest on a stack of its own), 087 (`_artifacts`: the set checked against its
  SHA256SUMS), 092 (`sameness.py`). None of their decisions changes; each keeps its module.
- **Research it stands on:** `../research/2026-10-20-a-design-review-of-the-runner.md` (H1, M5,
  L1; the module table in H1; section 8, the owner's four decisions). Every number in this file
  is EXECUTED on `a9064a2` by the scripts under `build/103/` (`map.py`, `sites.py`, `table.py`,
  `count_globals.py`, `dups.py`; scratch, not committed) unless marked READ or INFERRED.
  **The tables are measured on `a9064a2` and reconciled with 102's text** (the pre-build
  review's finding 1): 102 deletes three of `runner.py`'s names, `_set_async_stack` and
  `_wasmtime_version` (`_engines.py`'s rows) and `_context_address` (`_call.py`'s row), each
  replaced by an adapter operation (`102-the-engine-seam.md`, "The runner's side", READ), so on
  102's reviewed tip the runner binds **352** names, not 355, and the three are struck below
  where they would appear. 102 also rewrites `_wasmtime()`'s import and `mounts.py`'s `bind`,
  `forward` and `__call__`, so `mounts.py`'s line numbers below are `a9064a2`'s; the builder
  re-finds each site by its text. The builder re-runs `map.py` on 102's tip (`git show <102
  tip>:src/wasi_python/runner.py`) before the move and records its counts in the landing notes.

## The problem

`src/wasi_python/runner.py` is 6,241 lines and binds 355 top-level names on `a9064a2`
(EXECUTED, `ast`; the `grep` in the memo's method gives 341, missing the names bound by tuple
assignment and the three definitions under a decorator; 352 on 102's tip, which deletes three). It holds 22 concerns in sequence (the memo's H1). Process state
is the glue: 12 module-level locks, one class-level `Condition` (`_epoch_ticker._cond`), 40
mutable module globals (dicts, lists, sets, a `deque`, a `SimpleQueue`, a `WeakSet`, a
thread-local, a counter) and 8 test hooks (EXECUTED, `count_globals.py`). `_after_fork_in_child`
names 15 of them in a `global` statement and re-creates them by hand; `_release` clears eight
caches by name. A new global that is forgotten is a silent fork hazard, and no check enumerates
the locks. `__init__.py` imports `runner` last, under a "Last:" comment, because `runner` imports
`Artifacts`, `ArtifactsMissing` and `artifacts()` back from it (L1). `mounts.py` imports `runner`
inside `_Files.__init__` and reaches nine of its private names (H4; spec 106 ends that).

One file is the architecture. The next four specifications (104 to 107) each need a place to put
one concern, and there is none. This specification makes the places. It moves text. It changes
no behaviour.

## Decisions

### 1. The module list, and what moves where

`runner.py` becomes the thin entry of a package of eleven modules under `src/wasi_python/`,
beside `_wasmtime_ffi.py` (102's), `mounts.py`, `tools.py`, `cli.py` and `__init__.py`. The memo's
table (H1) is the start; a name goes where its dependencies say, and three of the memo's rows
are refined for that reason (named below). Every top-level name of today's `runner.py` moves to
exactly one module, or stays in `runner.py`; the full table is in *Design*. The modules, in the
import order Decision 2 fixes, with their line counts (EXECUTED, `map.py`: each name's span plus
the comment and blank lines directly above it; each module adds its docstring and import lines,
about 20 to 40 more, INFERRED):

| module | lines | what it holds |
|---|---|---|
| `_wasmtime_ffi.py` | 102's | the one module that touches wasmtime-py's private API (spec 102) |
| `_limits.py` | 159 | the tick constants (`TICK_S`, `NO_DEADLINE`, `CANCEL_TICKS`), the limit checks (`_integer_limit`, `_seconds_limit`, `_shutdown_limit`, `_check_limits`), `_text`, `_check_inputs`, the worker count, and the sentinel `_UNSET` |
| `_platform.py` | 375 | what the operating system decides: `_flags`, the kernel identity, the two lock implementations (`_try_lock`, `_unlock_close`, `_same_file`), fork (`_fork`, `_refuse_forked`), `_dir_fd_ok`, `_open_dir`, `_close`, the stack sizes (`_WASM_STACK`, `_HOST_ROOM`, `_THREAD_STACK`) and the three stack probes, `_tell_interpreter`, and the trap-handler guard (spec 071) |
| `_artifacts.py` | 117 + 90 | the artifact set: `Artifacts`, `ArtifactsMissing`, `artifact_dir`, `artifacts` and their constants from `__init__.py` (lines 36–125, 90 lines, EXECUTED); `_found_and_checked` and `_Checked` (spec 087), `_digest` and `_digests`, `_hash_file`, `_stamp`, `_version_tag`, `_has_guest_package` |
| `_engines.py` | 273 | wasmtime-py's import (`_wasmtime`, which keeps 102's adapter import inside it), the two engines (`_engine` calls `ffi.set_async_stack`; 102 deleted `_set_async_stack` and `_wasmtime_version`), compiled modules and the `.cwasm` cache (`_module`, `_module_miss`, `_private`, `_cache_dir`), `_lock` and `_counts`, the epoch ticker, and the preopen check's WAT module (`_CHECK_WAT`, `_check_module`) |
| `_private_dirs.py` | 536 | `_Private` and its lock protocol (spec 016), the sweep (`_sweep_once`, `_sweep_entry`), the budgeted tree remover and its two walks (spec 084), the queued warnings (`_warn_later`, `_flush_warnings`), `_remove_fresh_home` |
| `_zip.py` | 263 | the private copy of the stdlib zip and matplotlib's data (`_zip_folder`, `_copy_zip`, `_extract_data`, `_data_intact`, `_remove_zips`; specs 017 and 023) |
| `_places.py` | 892 | `Grant`; the argument checks for root, grants, mounts and the import path; the POSIX and Windows walks, `_Walked`, `_judge`; SipHash-1-3 and `_check_preopens` (spec 017, Decision 5); `_walk_grants`, `_runtime_folders`, `_shared_folders`; `_real_dir_at`, `_real_dir` (spec 024) |
| `_home.py` | 326 | the threads of a call: the per-thread stack of calls (`_calls`, `_stack`), Ctrl-C on the main thread (`_ctrl_c`, `_ctrl_c_watched`, `_deferred_ctrl_c`), and the home and guest threads (`_Home`, `_Box`, `_start_guest`, `_join_guest`, `_on_guest_thread`; spec 078) |
| `_call.py` | 1,202 | one call: `Completed`; `_run_checked` to `_instance`; `_drive`, `_Call`, `_shared` and the epoch callback (`_context_address` is 102's `ffi.context_address`; the one `_epoch_callback` object lives here, where 102's Decision 7 writes "`_engine.py` and `_call.py`"); the linkers and trampolines; the output streams; `poll_oneoff`; the door; the tool host (`_tool_host`, `_count_tool_threads`) |
| `_sessions.py` | 924 | `SessionEnded`, `_State`, the reaper, the endings and the shutdown, the turns, `_open_session` (spec 055) |
| `runner.py` | 1,174 | the thin entry: `Defaults`, `DEFAULTS`, `_current_defaults`; `run`, `run_async`, their argument checking (`_checked`, `_check_tools`, `_is_async_callable`), `run_async`'s pool and exit hook; `stats`; `Session`; the two process hooks `_after_fork_in_child` and `_release`; and the re-exports `__init__.py` needs (`Completed`, `Grant`, `SessionEnded`) |

**Why these refinements of the memo's table** (each is a dependency, EXECUTED by `map.py`'s
edge list):

- **`_artifacts.py` takes the whole of the set's code, not only the two classes.** `runner`
  imports `artifacts()` from `__init__` too, so moving only `Artifacts` and `ArtifactsMissing`
  would leave the cycle and the "Last:" comment. With `artifact_dir`, `artifacts` and their
  constants in `_artifacts.py`, `__init__.py` imports everything at its top and defines only
  `__version__`, `defaults`, `set_defaults` and `__all__`. The set's digests and stamps
  (`_found_and_checked`, `_digest`, `_stamp`, `_version_tag`, `_has_guest_package`) go with it:
  they are facts about the set's files, and `_zip` and `_engines` both read them. Spec 106's one
  stamp (M4) then has one module to change.
- **The engine module is `_engines.py`, plural.** `_engine()` is a function `_call` and
  `_sessions` call, and they also reach the module's `_lock` by attribute (Decision 2). A
  module named `_engine` would shadow the function in every importer. The same rule names no
  other module after a function or class in the package. Two modules hold a name equal to
  their own file name, `_call._call` and `_sessions._sessions`; no other module imports either
  name, so nothing shadows.
- **The linkers and trampolines live in `_call.py`, not `_engines.py`.** `_runner_linker` is
  built from `_shared`, the host-function wrapper, which reads the call stack, the Ctrl-C flag
  and the epoch answer. In `_engines.py` they would import upward.
- **The thread-local call stack and Ctrl-C live in `_home.py`, not `_call.py`.** `_Home.body`
  sets `_calls.watched` and `_on_guest_thread` reads `_stack()` and `_ctrl_c_watched()`; in
  `_call.py` they would make `_home` import upward. They are thread state; the home module is
  the threads module.
- **The preopen check's WAT module (`_CHECK_WAT`, `_check_modules`, `_check_module`) lives in
  `_engines.py`.** It is a per-engine compiled module cached under `_lock`, like the linkers'
  engine keys; `_check_preopens` itself stays in `_places.py` and takes the module as its
  argument, as today.
- **`_real_dir_at` and `_real_dir` live in `_places.py`**: they open through `_DIR`, the walk's
  flags. **`_dir_fd_ok`, `_open_dir`, `_close` live in `_platform.py`**: `_private_dirs`,
  `_places` and `_call` all ask the platform that question.
- **`_checked`, `_check_tools` and `_is_async_callable` stay in `runner.py`.** They read
  `_current_defaults()`, which must stay beside `DEFAULTS` (spec 049, Decision 2: the binding
  `run` reads is `runner.DEFAULTS`, which `set_defaults` replaces). `Defaults` stays with them.
  `_places._check_places` names `Defaults` in an annotation only.
- **`Grant`, `Completed` and `SessionEnded` are defined below `runner.py` and re-exported by
  it.** `_check_grants` constructs `Grant`, `_instance` and `_turn_inside` construct
  `Completed`; a definition in `runner.py` would be an upward import. `SessionEnded` goes with
  the session machinery it names. `runner.py` keeps the three names, so `from .runner import
  Completed` (`tests/unit/test_cli.py`) and `__init__.py`'s import block still work, and
  `tests/harness/api.py`'s `reexport_errors` passes: it refuses a public name bound from a name
  starting with `_`, and the module's name is not the name.
- **`Session` stays in `runner.py`**, against the memo's `_sessions.py` row, its largest
  departure (457 lines, `runner.py:5785–6241`). Its constructor reads `_checked`,
  `_current_defaults`, `_refuse_forked` and `_open_session` (EXECUTED, `map.py`'s edges); in
  `_sessions.py` the first two would import upward, since `_checked` must stay beside
  `DEFAULTS`. `_sessions.py` holds the machinery, `runner.py` the class the embedder sees.
- **The memo's `_process.py` is 104's**, not made here. The two process hooks stay in
  `runner.py`, the top of the order, where they can reach every module (Decision 4). 104 puts
  `_process` first in Decision 2's order and `process` in check 3's by-name list; both lists are
  written in the checks as plain tuples so 104 extends them by one entry each.

### 2. The import order, and how a module reaches another

**The order.** A module imports only modules before it in this list:

```
_wasmtime_ffi < _limits < _platform < _artifacts < _engines < _private_dirs < _zip
             < _places < _home < _call < _sessions < runner
```

`mounts.py` and `tools.py` stand beside the list: `_places` and `_call` import `mounts` at
module level (`Mount`, `METHODS`, `STAGING_CEILING`, `FileRecord`), as `runner.py` does today;
`mounts.py` imports no runner module at module level, so there is no cycle. `cli.py` and
`__init__.py` are above `runner`. The edge list below is EXECUTED (`map.py`): every reference
from a name in one module to a name in another, by module. There are **two upward
references, both annotations**: `_places._check_places(limits: Defaults)` and
`_home._stack() -> list[_Call]`. Each becomes an `if TYPE_CHECKING:` import, as `mounts.py`
already does for `_Call`. Nothing else points upward.

| from | to (names it reads) |
|---|---|
| `_engines` | `_limits` (`TICK_S`); `_platform` (`_WASM_STACK`, `_fork`); `_artifacts` (`_digest`, `ArtifactsMissing`) |
| `_private_dirs` | `_platform` (`_dir_fd_ok`, `_flags`, `_kernel_identity`, `_same_file`, `_try_lock`, `_unlock_close`); `_engines` (`_lock`) |
| `_zip` | `_artifacts` (`Artifacts`, `_digest`, `_hash_file`, `_stamp`, `_version_tag`); `_private_dirs` (`_Private`) |
| `_places` | `_limits` (`_UNSET`, `_integer_limit`, `_text`); `_platform` (`_flags`); `_zip` (`_zip_known`); `_artifacts` (`Artifacts`); `mounts` |
| `_home` | `_limits` (`CANCEL_TICKS`, `TICK_S`); `_platform` (the three stack sizes, `_guest_stack`, `_tell_interpreter`); `_engines` (`_epoch_ticker`) |
| `_call` | `_limits`, `_platform`, `_artifacts`, `_engines`, `_private_dirs`, `_zip`, `_places`, `_home`; `mounts` |
| `_sessions` | every module above it but `_zip` |
| `runner` | every module |

**How a name is reached.** Two forms, chosen by what the name is, so that both the fork hook
(Decision 4) and the judge's patches (Decision 5) keep working:

- **By `from ._x import name`:** a class (dataclasses, `NamedTuple`s, exceptions, `_Walked`,
  `_Home`, `_epoch_ticker`), a type alias (`Identity`, `Host`), an immutable constant (an `int`,
  `float`, `str`, `bytes`, a tuple or `frozenset` of those, a compiled regex), and the sentinels
  `_UNSET` and `_DONE`. These bindings never change and the objects are never mutated, so a
  copy of the binding is safe.
- **By `from . import _x` and `_x.name` at every use:** a function, a hook, and every mutable
  object (a lock, a dict, a list, a set, a queue, a thread-local, `BASE_ENV`). The lookup
  happens at call time in the defining module, so a lock the fork hook re-makes, a seam the
  judge replaces (`monkeypatch.setattr(_platform, "_trap_handlers_ready", …)`) and a cache
  `_release` clears are seen by every caller. A function imported by `from` would be a copy the
  patch misses: today `monkeypatch.setattr(runner, "_ctrl_c_watched", …)` reaches `_shared`
  because both are one module; after the split `_shared` lives in `_call` and the seam in
  `_home`, and `_call._shared` must read `_home._ctrl_c_watched()`.

The cost is measured: **244 references on 226 lines** change by gaining a module prefix
(EXECUTED, `sites.py`, by `ast`; the build's count may differ by a few lines, INFERRED):
`runner.py` 86 lines, `_sessions` 57, `_call` 48, `_private_dirs` 15, `_zip` 9, `_places` 7,
`_engines` 2, `_home` 2. These are the qualified call sites Decision 3 allows, and the only
kind of non-move line inside a function body. A unit check enforces the two forms by
introspection (check 3 below): every `from ._x import name` in the package, module-level or
late, binds a class, an alias, an immutable constant or a named sentinel; everything else is
reached by attribute.

**Late imports.** `runner.py` already imports inside functions, and the pattern stays only
where it stays today or where it breaks a cycle it already breaks:

- `from .tools import …` inside `_check_tools` (`runner`), `_tool_host` (`_call`),
  `_session_tool_host` and `_open_session` (`_sessions`): `wasi_python.tools` is imported only
  when tools are given, a promise `__init__.py`'s docstring makes. Unchanged.
- `from .mounts import _Files` inside `_instance` (`_call`) and `_open_session` (`_sessions`);
  `SIGNATURES`, `COUNTED`, `GUARDED`, `trampoline_wat`, `stat_trampoline_wat` inside the
  linker and trampoline builders (`_call`). Unchanged.
- `import wasmtime as wt`, `import signal`, `import asyncio`, `import inspect` and the other
  standard-library late imports. Unchanged.
- `from . import ArtifactsMissing` inside `_run_checked`, `_open_session`, `_found_and_checked`
  and `_module_miss`: the cycle these broke is gone, so each becomes a module-level
  `from ._artifacts import ArtifactsMissing` and the late line is deleted.
- `mounts.py`, inside `_Files.__init__`: today `from . import runner`; after, `from . import
  _call, _engines, _home, _places, runner` (spec 106 replaces all five with its protocol). The
  sites it changes are listed in *Design*.
- No other late import of a package module is allowed; check 3 lists these and refuses any
  other.

**`__init__.py`** imports `_artifacts` (public names), `mounts` and `runner` at its top. The
"Last:" comment and the three `# noqa: E402` go. `__version__`, `_defaults_lock`, `defaults`,
`set_defaults` and `__all__` stay as they are. `set_defaults` keeps assigning
`_runner.DEFAULTS`. `import wasi_python` still loads no wasmtime-py: no module in the order
imports `wasmtime` at module level (`if TYPE_CHECKING:` only), and `_wasmtime_ffi`, whose own
import loads wasmtime-py, is imported only inside the functions that call it, as `from . import
_wasmtime_ffi as ffi`, exactly where 102 put each of those lines (102's Decision 2 and "The
runner's side"; `_wasmtime()` keeps its adapter import inside it, 102's Decision 7). A late
import of `_wasmtime_ffi` is therefore allowed in any function of any module; check 2 lists
it as the one module that may be late-imported anywhere.

**The condition the second form rests on** (the pre-build review's finding 6): a class or a
constant the judge replaces with `monkeypatch.setattr(<module>, "NAME", …)` must be read only in
its defining module, because a from-imported copy elsewhere never sees the patch. It holds today:
of the 45 names tests patch through `runner` (EXECUTED, grep over `tests/`), the classes and
constants among them are `MAX_RESPONSE`, `_REMOVE_BUDGET` and `DEFAULTS`, and each is read in
its own module only (EXECUTED, `map.py`'s edges; `_after_walk` is a hook, reached by attribute).
Check 3 holds the condition: for every such `setattr` in `tests/` whose object is a class or a
constant, no package module from-imports the name. Spec 104 moves the seams off module
globals; until it lands, the assertion is 103's.

### 3. Text moves verbatim

The reviewer reads the change as moves, so the change is only moves. A moved block keeps every
byte: no rename, no rewording, no reformatting, no reordering, no docstring edit, no comment
edit, no type-annotation edit. Inside each new module the names keep today's relative order in
`runner.py`, so the module reads as a sequence of cuts from today's file. A section comment
(`# Grants (spec 017). …`, `# The removal (spec 084). …`) moves with the first name below it. A
comment made stale by the move (one that says "this module" of a name now elsewhere) is left as
it is and listed in the landing notes; spec 106's M2 pass rewrites comments.

The only lines that are not moves are these, and nothing else:

1. **Import lines**: each module's `import` block; the deleted late imports of
   `ArtifactsMissing`; the `TYPE_CHECKING` imports; `__init__.py`'s import block;
   `mounts.py`'s five-module late import. `ruff`'s `I` rule orders them.
2. **Each new module's docstring**: a few sentences naming its concern and the specifications
   it carries (M2's "one `# spec NNN` per concern at its module docstring"). `runner.py` keeps
   today's docstring unchanged.
3. **The qualification of a moved name at a call site in another module**: `_lock` becomes
   `_engines._lock`, `_trap_handlers_ready()` becomes `_platform._trap_handlers_ready()`
   (Decision 2's second form). A qualified line differs from its source line only by one or
   more `_module.` prefixes. In `mounts.py`, `self._runner._siphash13` becomes
   `self._places._siphash13` and so on (*Design* lists the twelve sites).
4. **The two process hooks**, `_after_fork_in_child` and `_release`, whose bodies Decision 4
   writes out: `_release` changes by qualification only; `_after_fork_in_child` also loses
   thirteen names from its `global` statement and splits two tuple assignments.
5. **One alias line in `_artifacts.py`**, `find_artifacts = artifacts`, right after
   `artifacts()`. Today it is `runner.py`'s import alias `from . import artifacts as
   find_artifacts`; `_found_and_checked` keeps reading `find_artifacts()`, and the five test files
   that patch `runner.find_artifacts` patch `_artifacts.find_artifacts`. It is the one line that
   is neither an import, a docstring nor a qualification.

Nothing else changes: no function's body gains or loses a line, no signature changes, no
default changes, no message changes. The reviewer's command and the residue script are in
Decision 8.

### 4. The mutable globals stay globals, in the module their functions moved to; the two process hooks reach them by attribute

Spec 104 gathers process state into one object. This specification does not. Every lock,
cache, hook and counter stays a module global, in the module its functions moved to (the table
in *Design*). What changes is how the two functions that rebind or clear them from outside
reach them.

**`_after_fork_in_child`** stays in `runner.py` and is registered there, as today, with
`os.register_at_fork(after_in_child=…)` where `os` has it. Its docstring is unchanged ("Only
assignments, and no lock…"). Its body becomes:

```python
    global _pool_lock, _live_lock
    _pool_lock, _live_lock = threading.Lock(), threading.Lock()
    _private_dirs._held_lock = threading.Lock()
    # A fork inside the runner's stack-size window leaves the child at the guest thread's size;
    # put back the value the runner found (spec 078, the review's F6).
    if _home._stack_size_found:
        threading.stack_size(_home._stack_size_found[0])
        _home._stack_size_found.clear()
    _home._stack_size_lock = threading.Lock()
    # A child has none of its parent's tool threads (spec 036, Decision 8).
    _call._tool_threads_lock, _call._tool_threads["running"] = threading.Lock(), 0
    _zip._zip_lock, _zip._zips = threading.Lock(), {}  # the parent's zip folders stay the parent's
    _engines._lock, _call._epoch_callback_lock, _call._outputs_lock = (
        threading.Lock(),
        threading.Lock(),
        threading.RLock(),
    )
    _engines._compiling = {}
    _pool.update(pool=None, size=0)
    _pools.clear()
    _live.clear()
    _engines._epoch_ticker._thread, _engines._epoch_ticker._active = None, 0
    _engines._epoch_ticker._cond = threading.Condition()
    # A child has no reaper, no sessions and none open (spec 055, Decision 13).
    _sessions._sessions_lock, _sessions._sessions = threading.Lock(), weakref.WeakSet()
    _sessions._reaper_queue, _sessions._closers_lock = queue.SimpleQueue(), threading.Lock()
    _sessions._closers.clear()
    _sessions._dropped.clear()
    _sessions._reaper.update(thread=None, stop=False, hooked=_sessions._reaper["hooked"])
    _engines._counts["sessions_open"] = 0
    if _platform._fork["used"]:
        _platform._fork["forked"] = True
```

Every line is today's with a module prefix, except the first two (the `global` statement keeps
only `runner.py`'s own two locks, and the tuple that made three locks makes two, with
`_held_lock` on its own line) and the `_lock` tuple, which gains prefixes only. An assignment to
a module attribute rebinds the module's global, and every function in that module reads its
globals at call time, so the new lock is the one taken next. A module that copied the binding
with `from ._x import _lock` would keep the dead lock; Decision 2's second form forbids that,
and check 3 refuses it.

**The names the fork hook rebinds** (15, the `global` statement's list today, EXECUTED), each
with its module after the move: `runner` (`_pool_lock`, `_live_lock`); `_private_dirs`
(`_held_lock`); `_home` (`_stack_size_lock`); `_call` (`_tool_threads_lock`,
`_epoch_callback_lock`, `_outputs_lock`); `_zip` (`_zip_lock`, `_zips`); `_engines` (`_lock`,
`_compiling`); `_sessions` (`_sessions_lock`, `_sessions`, `_reaper_queue`, `_closers_lock`).
Plus the three class attributes of `_engines._epoch_ticker` it resets (`_thread`, `_active`,
`_cond`), and the ten it mutates in place (`_tool_threads`, `_pool`, `_pools`, `_live`,
`_stack_size_found`, `_closers`, `_dropped`, `_reaper`, `_counts`, `_fork`). The two locks it
does not touch today, `_pending_warnings_lock` (`_private_dirs`) and `__init__.py`'s
`_defaults_lock` (line 151, the package's thirteenth module-level lock), it does not touch
after: the move adds nothing and removes nothing from what the hook does. Spec 104 takes both
(`_defaults_lock` into `_Process`, its group I; the memo's H1 names the omission class; this
file only makes each visible).

**`_release`** stays in `runner.py`, registered with `@atexit.register` at import, before any
session can register `_sessions_at_exit` (so the order `_ensure_reaper` relies on holds:
`_sessions_at_exit` runs first). Its body is today's, qualified:
`_zip._remove_zips()`, `_private_dirs._flush_warnings()`, `_engines._check_modules.clear()`,
`_call._linkers.clear()`, `_call._mount_linkers.clear()`, `_call._guard_linkers.clear()`,
`_call._trampolines.clear()`, `_call._stat_trampolines.clear()`, `_engines._modules.clear()`,
`_engines._engines.clear()`.

**Check 1, the fork list by introspection** (`tests/unit/test_runner_package.py`,
`test_every_module_level_lock_is_remade_after_fork`). A child interpreter (`sys.executable
-c`, as `tests/unit/test_runner_sweep.py` runs one) imports `wasi_python`, walks the package
root `wasi_python` and every `wasi_python.*` module in `sys.modules`, and every module-level
attribute that is a lock (`type(threading.Lock())`, `type(threading.RLock())`,
`threading.Condition`), plus `_engines._epoch_ticker._cond`, records `(module, name, id(lock))`,
calls `runner._after_fork_in_child()`, records again, and prints both as JSON. Two lists are
written in the check:

- `LOCKS_RESET_BY_FORK`, 12 entries: the eleven module-level locks the hook re-makes
  (`runner._pool_lock`, `runner._live_lock`, `_private_dirs._held_lock`,
  `_home._stack_size_lock`, `_call._tool_threads_lock`, `_call._epoch_callback_lock`,
  `_call._outputs_lock`, `_zip._zip_lock`, `_engines._lock`, `_sessions._sessions_lock`,
  `_sessions._closers_lock`) and `_engines._epoch_ticker._cond`.
- `REBOUND_BY_FORK`, 4 entries, the names the hook rebinds that are not locks:
  `_engines._compiling`, `_zip._zips`, `_sessions._sessions`, `_sessions._reaper_queue`.
- `NOT_RESET`, 2 entries, each with its sentence: `("wasi_python._private_dirs",
  "_pending_warnings_lock")`, "never reset today; spec 104 decides", and `("wasi_python",
  "_defaults_lock")`, "never reset today; spec 104 takes it into `_Process` (group I)".

The check asserts: every lock the walk found is in `LOCKS_RESET_BY_FORK` or `NOT_RESET`; every
entry of `LOCKS_RESET_BY_FORK` was found and its `id` changed; every entry of `NOT_RESET` was
found and its `id` did not change; at least 14 locks were found (the twelve, plus the two), so
an empty or narrowed walk cannot pass. A second assertion reads `_after_fork_in_child` by
`ast`: it collects the hook's `global` names and its depth-one `_module.name` `Attribute`
targets (an `Attribute` whose value is a bare `Name`), skips `Subscript` targets
(`_call._tool_threads["running"]`, `_engines._counts[...]`, `_platform._fork[...]`) and
attributes of attributes (`_engines._epoch_ticker._thread`, `._active`, `._cond`), and requires
the set to equal the union of the two lists minus `_engines._epoch_ticker._cond`: 15 names, the
`global` statement's list today. So the hook, the lists and the modules agree three ways. This
check is 103's until 104 lands: 104's Decision 3 check (`RENEW`, one table in `_process.py`)
replaces it, and 104 names the retirement in its `--accept-judge` reason. Seen failing first:
the builder adds a `_spare_lock = threading.Lock()` to `_zip.py` without touching the hook, runs
the check, and records the one-line failure (the lock is found and in neither list); then
removes it.

### 5. The judge's 24 files are updated mechanically, to the defining module

Every test, check and harness file that names a runner private is updated to the module the
name moved to, in the same form it used (attribute, `monkeypatch.setattr(module, "name", …)`,
or `from … import`). No facade: `runner.py` re-exports only `Completed`, `Grant` and
`SessionEnded` (public names `__init__.py` imports), nothing that starts with `_` and no
internal constant. A test that reaches `_sweep_state` reaches `_private_dirs._sweep_state`,
and the dependency is on the page. No assertion changes; no row is removed, skipped or
loosened. The files, and what each takes from where (EXECUTED, from both forms of reference;
`runner` names that stay are left out):

| file | names, by new module |
|---|---|
| `tests/unit/test_async_tools.py` | `_call`: `_tool_host`; `_home`: `_ctrl_c`, `_ctrl_c_watched`; `_artifacts`: `find_artifacts` |
| `tests/unit/test_inline_sessions.py` | `_platform`: `_trap_handlers_ready` |
| `tests/unit/test_runner_async.py` | `_call`: `_drive`, `_epoch_answer`, `_epoch_now`, `_shared`, `_stop_error`; `_engines`: `_epoch_ticker`; `_home`: `_calls`, `_ctrl_c`, `_ctrl_c_watched`, `_stack`; `_limits`: `CANCEL_TICKS`, `_default_workers`; `_platform`: `_fork`, `_trap_handlers_ready` |
| `tests/unit/test_runner_calls.py` | `_call`: `HOST_FAULT`, `NO_HOST`, `_Call`, `_Driven`, `_drive`, `_fuel_used`, `_linker`, `_output_free`, `_output_write`; `_engines`: `_engine`, `_engines` (`_set_async_stack` is gone: 102 re-pointed `test_the_async_stack_size_property_is_preferred` to `_wasmtime_ffi.set_async_stack`); `_home`: `_ctrl_c`, `_deferred_ctrl_c`, `_note_ctrl_c`, `_stack`; `_platform`: `_THREAD_STACK`, `_WASM_STACK`, `_fork`, `_trap_handlers_ready` |
| `tests/unit/test_runner_cancel.py` | `_call`: `_epoch_now`, `_shared` (`_context_address` is gone: 102 re-pointed the `shared` fixture to `_wasmtime_ffi.context_address`); `_home`: `_ctrl_c`, `_ctrl_c_watched`, `_stack` |
| `tests/unit/test_runner_data.py` | `_zip`: `MPL_DATA_MEMBER`, `_data_intact`, `_extract_data`, `_remove_entry` |
| `tests/unit/test_runner_grants.py` | `_engines`: `_CHECK_WAT`; `_places`: `_Preopen`, `_Walked`, `_check_grants`, `_check_preopens`, `_check_root`, `_close_held`, `_identity_of`, `_judge`, `_rewritten`, `_walk`, `_walk_windows`, `_wasi_ino`, `_win_open` |
| `tests/unit/test_runner_inputs.py` | `_limits`: `_check_inputs` |
| `tests/unit/test_runner_limits.py` | `_limits`: `_UNSET`, `_check_limits`; `_artifacts`: `find_artifacts` |
| `tests/unit/test_runner_mounts.py` | `_call`: `_Call`, `_drive`, `_epoch_answer`, `_fuel_used`, `_guard_linker`, `_mount_linker`, `_stop_error`; `_engines`: `_engine`, `_epoch_ticker`; `_home`: `_ctrl_c_watched`, `_stack`; `_places`: `Grant`, `_check_grants`, `_check_mounts`, `_siphash13` |
| `tests/unit/test_runner_sessions.py` | `_call`: `CLOCK`, `MONOTONIC`, `SUBSCRIPTION`, `_poll_oneoff`; `_sessions`: `_State`, `_collected`, `_dropped`, `_ending_seconds`, `_reap`, `_reaper_loop`, `_reaper_queue`, `_sessions`, `_start_ending`; `_artifacts`: `find_artifacts` |
| `tests/unit/test_runner_sets.py` | `_artifacts`: `_found_and_checked`, `_ARTIFACTS_ENV`; `_engines`: `_module_miss`, `_modules`; `_zip`: `_zips` |
| `tests/unit/test_runner_sweep.py` | `_call`: `_trap_code_name`, `_trap_name`; `_engines`: `_lock`; `_platform`: `_dir_fd_ok`, `_kernel_identity`, `_try_lock`, `_unlock_close`; `_private_dirs`: `_Private`, `_REMOVE_BUDGET`, `_drop`, `_flush_warnings`, `_held`, `_held_lock`, `_owned`, `_pending_warnings`, `_remove_tree`, `_sweep_once`, `_sweep_state`, `_warned`; `_sessions`: `_remove_home`; `_zip`: `_zip_lock` |
| `tests/unit/test_runner_threads.py` | `_call`: `_home_context`; `_home`: `_Box`, `_DONE`, `_Home`, `_Stopped`, `_join_guest`, `_on_entry`, `_on_guest_thread`, `_stack`; `_platform`: `_HOST_ROOM`, `_THREAD_STACK`, `_WASM_STACK`, `_guest_stack`, `_pyapi`, `_tell_interpreter`, `_windows_usable` |
| `tests/unit/test_runner_tools.py` | `_artifacts`: `_has_guest_package`, `find_artifacts`; `_call`: `Completed`, `HOST_FAULT`, `_count_tool_threads`, `_door`, `_tool_host`, `_tool_threads_lock`; `_home`: `_ctrl_c`, `_ctrl_c_watched`; `_limits`: `_UNSET`; `_places`: `_walk_grants` |
| `tests/unit/test_runner_waits.py` | `_call`: `EBADF`, `EFAULT`, `EINVAL`, `ENOMEM`, `EVENT`, `MAX_SUBSCRIPTIONS`, `_Waits`, `_poll_oneoff`, `_poll_plan`, `_stop_at`; `_limits`: `TICK_S` |
| `tests/checks/test_v1_2_hostile_guest.py` | `_call`: `MAX_RESPONSE`, `_drive`; `_engines`: `_epoch_ticker`; `_home`: `_Box`, `_Home`, `_join_guest`, `_on_entry`; `_limits`: `CANCEL_TICKS`; `_places`: `_after_walk`; `_platform`: `_HOST_ROOM`, `_WASM_STACK`, `_guest_stack`; `_sessions`: `_abandon_turn`, `_drive_turn`, `_reap`, `_session_clock` |
| `tests/checks/test_v1_4_embedding.py` | `_call`: `_outputs`, `_tool_host`; `_engines`: `_engines`, `_epoch_ticker`; `_home`: `_stack`; `_limits`: `CANCEL_TICKS`, `TICK_S`; `_places`: `_check_preopens`; `_platform`: `_fork`, `_try_lock`, `_unlock_close`; `_private_dirs`: `_sweep_state` |
| `tests/checks/test_v1_4_public_api.py` | `_limits`: `_UNSET`; `_artifacts`: `find_artifacts`; and `_defaults_loads` reads every `.py` under `src/wasi_python/`, not `runner.__file__` alone, so a `DEFAULTS` read outside `_current_defaults` is refused wherever it is written (the check is widened, not weakened) |
| `tests/checks/test_v1_4_sessions.py` | `_home`: `_ctrl_c`; `_limits`: `TICK_S`; `_private_dirs`: `_held`; `_sessions`: `_after_export`, `_closers`, `_on_arm`, `_on_call`, `_on_export`, `_reap`, `_reaper`, `_session_clock`, `_sessions_lock` |
| `tests/harness/files.py` | `_call`: `UNMETERED`, `_Call`, `_guard_linker`, `_linker`, `_mount_linker`; `_home`: `_stack` |
| `tests/harness/api.py` | `_engines`: `CACHE_ENV`; `_artifacts`: `_ARTIFACTS_ENV` (line 1049's `top._ARTIFACTS_ENV`); and its tables: `INTERNAL_FILES` and `INTERNAL_MODULES` gain the ten new modules **and 102's `_wasmtime_ffi.py` (`wasi_python._wasmtime_ffi`)**, which 102 names in neither table (EXECUTED, grep), unless 102's build adds them, in which case 103 adds nothing for it and says so in the landing notes; `DEFINING` gains `_artifacts.py`, `_call.py`, `_places.py` and `_sessions.py` (the files that now define public names), so criterion 6's internal-name rule and the `from __future__ import annotations` rule keep covering every module |
| `tests/harness/paths.py` | `_artifacts`: `_ARTIFACT_DIR` (two reads) |
| `tests/test_api.py` | `_artifacts`: `_ARTIFACT_DIR`, `_CHECKOUT_ARTIFACT_DIR` (four patches), `_ARTIFACTS_ENV` |

That is 24 files: the 20 the memo counts, `tests/harness/files.py`, and the three that reach
`__init__.py`'s artifact names, which move to `_artifacts.py` (Decision 1). `tests/unit/test_cli.py`
keeps `from wasi_python.runner import Completed` and `runner.run` unchanged. The `runner`
names each file keeps (`DEFAULTS`, `Defaults`, `run`, `run_async`, `stats`, `_checked`,
`_check_tools`, `_current_defaults`, `_pool`, `_pool_lock`, `_stop_async_calls`) are not
listed; they do not move. `tests/release_shards.toml` adds `tests/unit/test_runner_package.py`
to `own-runner` (rule (g) of spec 063: a runner unit file is in a files shard on all three
systems).

### 6. A rules check: no module under `src/` over 1,500 lines

`tests/checks/test_rules.py::test_no_module_under_src_is_over_the_line_ceiling`. For every
`.py` file under `src/` (`scan.files_under(paths.REPO, "src")`), its line count is the number
of physical lines `str.splitlines()` returns for its text: code, comments, docstrings and blank
lines alike, the number `wc -l` prints for a file that ends in a newline. The ceiling is
**1,500**. Two files are over it today and are not this specification's to split: `mounts.py`
(2,235 lines) and `tools.py` (2,450 lines; EXECUTED, `wc -l`). The check holds them in
`ALLOWED = {"mounts.py": 2235, "tools.py": 2450}`, and the allowance can only shrink: a file in
`ALLOWED` fails the check when it has more lines than its number, and **also when it has fewer**
(a stale entry: the change that shrank the file lowers the number in the same change, or the
check names the entry and the count), and an entry whose file is gone is a finding too. So an
entry always equals its file's count, and the day a file is at or under 1,500 its entry is
deleted. Every other file is held to 1,500. The counts are measured on the tree, never typed
from memory: the builder records the two counts EXECUTED with `wc -l` at the build, and the
check's message prints the count it measured. This check is 103's to own (the 107 review's
ruling, 2026-10-20): 107 owns the function-length ceiling (the memo's "no function over 80")
and the test-seam allowance check; 104 owns the checks on where a module-level lock or mutable
may live, which supersede check 1 below once `_Process` exists. Seen failing first: on today's
tree the check reports `src/wasi_python/runner.py: 6,241 lines, over 1,500`; after the move,
the largest module is `_call.py` at about 1,240 (INFERRED from the 1,202 above plus its imports
and docstring), with 260 lines of room, and `runner.py` about 1,230.

### 7. Acceptance is sameness: the fast tier on the frozen baseline set moves no verdict

The guest does not change, so no fuel row, byte row or pass can move. The proof is the memo's
section 8 rule: `tests/harness/sameness.py` between two fast-tier records on the frozen baseline
set (the `v0.1.0a7` release's, verified against its `SHA256SUMS` and named by
`WASI_PYTHON_ARTIFACTS`). The builder keeps the record of 102's reviewed tip
(`build/progress/latest.json` after `uv run pytest -m "not slow" -n 3` there, copied to
`build/103/before.json`), builds, runs the same command, copies `build/103/after.json`, and
runs

```
uv run python tests/harness/sameness.py --claims build/103/claims.toml \
    build/103/before.json build/103/after.json
```

which must print nothing and exit 0. `build/103/claims.toml` (committed under `context/`
with the landing notes, as the wave's claim list carries it) holds one `[[claim]]`: `spec =
"103"`, `new = ["tests/checks/test_rules.py::test_no_module_under_src_is_over_the_line_ceiling",
"tests/unit/test_runner_package.py"]`, `units = <the unit file's row count>`. No `grows`, no
`retired`, no `changed`, no `passes`. A difference the claim does not explain is a defect of
the move, never a row to accept. The other criteria are counted in *Acceptance criteria*.

### 8. How the reviewer verifies "verbatim"

Two readings, both mechanical, both recorded in the review:

1. **The moved blocks**, with git's move detection across files (git 2.43 here, EXECUTED;
   `--color-moved` is in git since 2.15, READ):

   ```
   git diff --color-moved=dimmed-zebra --color-moved-ws=no --color=always \
       <102's reviewed tip>..<103's tip> -- src/wasi_python/ | less -R
   ```

   A moved block shows dimmed; the reviewer reads only what is not dimmed. A non-move hunk may
   contain: an import line; a module docstring line; a line that differs from a dimmed line
   only by one or more `_module.` prefixes (Decision 3, item 3); a line of the two hooks'
   bodies as Decision 4 writes them; the alias line `find_artifacts = artifacts`; and, in
   `__init__.py` and `mounts.py`, the import lines and the twelve qualified sites *Design*
   lists. Anything else is a finding.
2. **The residue script**, `build/103/verbatim.py`, committed with the landing notes under
   `context/research/2026-10-20-the-runner-split/` as evidence: it reads today's `runner.py`
   from git (`git show <base>:src/wasi_python/runner.py`) and `__init__.py`, and the eleven
   modules plus `__init__.py` after, strips blank lines, and compares the two multisets of
   lines. For each line only on the new side it strips every `_module.` prefix
   (`_limits.`, `_platform.`, `_artifacts.`, `_engines.`, `_private_dirs.`, `_zip.`, `_places.`,
   `_home.`, `_call.`, `_sessions.`, `runner.`) and looks again; what remains must be an import
   line (`import …`, `from … import …`), a line inside a module docstring, a line of the two
   hooks' bodies, or the alias line. For each line only on the old side, it must be an import
   line, a line of the two hooks' old bodies, or the "Last:" comment. The script prints the
   residue by category and its counts; the landing notes record the counts and that the
   uncategorised residue is empty.

## Intent

A reader who wants the private-folder protocol opens `_private_dirs.py` and reads 540 lines
that are about that. A reader who wants to know what Windows does differently opens
`_platform.py`. The fork hook names every lock by its module, and a check finds every lock
and proves the hook re-makes it. `__init__.py` imports in order. Nothing the embedder sees
changes: not a name, not a message, not a fuel count. Spec 104 then has a module per concern to
put a `_Process` object into; 105 has `_call.py` to type; 106 has `_platform.py` to give an
interface.

## Design

### The files

| file | change |
|---|---|
| `src/wasi_python/_limits.py`, `_platform.py`, `_artifacts.py`, `_engines.py`, `_private_dirs.py`, `_zip.py`, `_places.py`, `_home.py`, `_call.py`, `_sessions.py` | new: the moved text (the table below), a docstring, imports |
| `src/wasi_python/runner.py` | 6,241 → about 1,230 lines: what Decision 1's last row keeps, imports, the two hooks as Decision 4 writes them, the re-exports `from ._call import Completed`, `from ._places import Grant`, `from ._sessions import SessionEnded` |
| `src/wasi_python/__init__.py` | `Artifacts`, `ArtifactsMissing`, `artifact_dir`, `artifacts`, `_ARTIFACT_DIR`, `_ARTIFACTS_ENV`, `_checkout_artifact_dir`, `_CHECKOUT_ARTIFACT_DIR` move to `_artifacts.py` (lines 36–125 today, 90 lines with their blank lines, EXECUTED; lines 29–34, the imports and `__version__`, stay); the import block moves to the top; the "Last:" comment and the `# noqa: E402` go |
| `src/wasi_python/mounts.py` | the `TYPE_CHECKING` import `from .runner import _Call` becomes `from ._call import _Call`; `_Files.__init__`'s `from . import runner` becomes `from . import _call, _engines, _home, _places, runner`, storing each on the instance beside `self._runner`; twelve sites qualified: line 646 `runner._siphash13` → `_places._siphash13`; 724 `r._ctrl_c_watched() and r._ctrl_c["pending"]` → `self._home._ctrl_c_watched() and self._home._ctrl_c["pending"]` (723's `r._hook["exiting"]` stays: `_hook` stays in `runner`); 759 and 763 `self._runner._trampoline_module` and `._stat_trampoline_module` → `self._call.…`; 847 `r, call = self._runner, self.call` → `r, call = self._call, self.call` (so 849, 853 and 858's `r._epoch_now` hold); 852 `r._epoch_ticker.count()` → `self._engines._epoch_ticker.count()`; 1048, 1167, 1504, 1651, 1902 `self._runner._siphash13` → `self._places._siphash13`. Nothing else in `mounts.py` changes |
| `tests/unit/test_runner_package.py` | new: checks 1 to 4 below |
| `tests/checks/test_rules.py` | check 5 (Decision 6) |
| the 24 files of Decision 5 | import and attribute updates; `api.py`'s tables; `test_v1_4_public_api.py`'s `_defaults_loads` widened |
| `tests/release_shards.toml` | `tests/unit/test_runner_package.py` in `own-runner` |
| `CHANGELOG.md` | one entry under the one unreleased section (below) |
| `context/roadmap.md` | one reserved line for the chain, if 102's has not already written it (below) |

### The move table: every top-level name of today's `runner.py`

355 names on `a9064a2` (EXECUTED, `table.py`), each in exactly one row, three of them marked
as gone on 102's tip (352 there); today's line numbers are the reviewer's index into
`a9064a2`'s `runner.py`. Within a module the rows are in today's order,
and that is the order the module keeps.

**`_limits.py`** (18 names)

| today's lines | names, in today's order |
|---|---|
| 70–73 | `TICK_S`, `NO_DEADLINE`, `CANCEL_TICKS`, `MAX_WORKERS` |
| 85–229 | `LIMIT_MAX`, `_shown`, `_integer_limit`, `_deadline_limit`, `_seconds_limit`, `_shutdown_limit`, `_check_limits`, `_text`, `_check_inputs`, `_cpus`, `_default_workers`, `_check_workers` |
| 299–304 | `_Unset`, `_UNSET` |

**`_platform.py`** (32 names)

| today's lines | names, in today's order |
|---|---|
| 788–881 | `_identity`, `_flags`, `_kernel_identity`, `_BUSY`, `_try_lock`, `_unlock_close`, `_same_file` |
| 1412–1420 | `_fork`, `_refuse_forked` |
| 2934–2949 | `_dir_fd_ok`, `_open_dir`, `_close` |
| 4074–4076 | `_WASM_STACK`, `_HOST_ROOM`, `_THREAD_STACK` |
| 4391–4564 | `_stack_api`, `_guest_stack`, `_posix_stack`, `_darwin_stack`, `_windows_stack`, `_windows_usable`, `_pyapi`, `_tell_interpreter`, `_TRAP_SIGNALS`, `_TRAP_SIGNALS_X86_64`, `_TRAP_HANDLERS_REPLACED`, `_handlers`, `_DlInfo`, `_load_base` |
| 4567–4622 | `_handler_base`, `_wasmtime_base`, `_trap_handlers_ready` |

**`_artifacts.py`** (12 names from `runner.py`, plus `__init__.py`'s eight)

| today's lines | names, in today's order |
|---|---|
| `__init__.py` 36–125 | `_ARTIFACT_DIR`, `_ARTIFACTS_ENV`, `_checkout_artifact_dir`, `_CHECKOUT_ARTIFACT_DIR`, `ArtifactsMissing`, `Artifacts`, `artifact_dir`, `artifacts`; then the alias `find_artifacts = artifacts` (Decision 3, item 5) |
| 3854–3855 | `_stamp` |
| 3910–3954 | `_hash_file`, `_versions`, `_version_tag`, `GUEST_PACKAGE`, `_guest_packages`, `_has_guest_package` |
| 3977 | `_digests` |
| 4625–4687 | `SET_SUMS`, `_Checked`, `_found_and_checked`, `_digest` |

**`_engines.py`** (18 names on `a9064a2`; 16 on 102's tip)

| today's lines | names, in today's order |
|---|---|
| 69 | `CACHE_ENV` |
| 1465–1477 | `_wasmtime` |
| 2529–2539 | `_CHECK_WAT`, `_check_modules` |
| 2594–2598 | `_check_module` |
| 3957–3976 | `_cache_dir`, `_lock`, `_engines`, `_modules` |
| 3978 | `_counts` |
| 4085–4117 | `_set_async_stack` (gone on 102's tip: `ffi.set_async_stack`), `_engine` |
| 4690–4858 | `_module`, `_compiling`, `_module_miss`, `_private`, `_wasmtime_version` (gone on 102's tip: `ffi.version()`), `_epoch_ticker` |

**`_private_dirs.py`** (32 names)

| today's lines | names, in today's order |
|---|---|
| 784–787 | `_LOCK_NAME`, `_held_lock`, `_held`, `_sweep_state` |
| 884–1086 | `_Taken`, `_Private`, `_drop`, `_abandon`, `_sweep_once`, `_owned`, `_sweep_entry`, `_unlink_quietly`, `_REMOVE_BUDGET`, `_REMOVE_BATCH`, `_SWEEP_TRIES`, `_DIR_OPEN`, `_pending_warnings_lock`, `_pending_warnings` |
| 1087–1406 | `_warned`, `_Spent`, `_Removal`, `_remove_tree`, `_is_folder`, `_listing`, `_remove_at`, `_enter`, `_long_path`, `_remove_by_path`, `_first_error`, `_warn_later`, `_flush_warnings`, `_remove_fresh_home` |

**`_zip.py`** (19 names)

| today's lines | names, in today's order |
|---|---|
| 2267–2439 | `_zip_lock`, `_zips`, `MPL_DATA_MEMBER`, `MPL_DATA_GUEST`, `_ZipFolder`, `_zip_folder`, `_zip_folder_locked`, `_zip_known`, `_remove_entry`, `_real_folder`, `_member_parts`, `_extract_data`, `_write_member`, `_holds` |
| 2442–2522 | `_remove_extra`, `_record`, `_data_intact`, `_copy_zip`, `_remove_zips` |

**`_places.py`** (53 names)

| today's lines | names, in today's order |
|---|---|
| 339–355 | `Grant` |
| 1642–1886 | `ZIP_GUEST`, `MAX_LINKS`, `_M64`, `_host_path`, `_guest_path`, `_check_root`, `_check_grants`, `_check_places`, `_under`, `_check_import_path`, `_check_mounts`, `Identity`, `_Walked`, `_close_held` |
| 1889–2034 | `_walk`, `_DIR`, `_walk_posix`, `_walked_posix`, `_writable`, `_make_missing`, `_WALK_ACCESS`, `_STAT_ACCESS`, `_SHARE_READ_WRITE`, `_OPEN_EXISTING`, `_BACKUP_SEMANTICS`, `_OPEN_REPARSE_POINT`, `_ATTRIBUTE_DIRECTORY`, `_ATTRIBUTE_REPARSE_POINT` |
| 2035–2259 | `_win_api`, `_win`, `_ByHandle`, `_win_open`, `_WIN_DEVICES`, `_WIN_RESERVED_CHARS`, `_rewritten`, `_drive_folder`, `_walk_windows`, `_chain`, `_identity_of`, `_judge` |
| 2542–2591 | `_rotl`, `_siphash13`, `_wasi_ino`, `_Preopen` |
| 2601–2741 | `_check_preopens`, `_after_walk`, `_walk_grants`, `_judge_import_path`, `_runtime_folders`, `_shared_folders` |
| 3858–3907 | `_real_dir_at`, `_real_dir` |

**`_home.py`** (18 names)

| today's lines | names, in today's order |
|---|---|
| 3277–3284 | `_calls`, `_stack` |
| 3589–3624 | `_ctrl_c`, `_note_ctrl_c`, `_ctrl_c_watched`, `_deferred_ctrl_c` |
| 4077–4082 | `_GUEST_SLICE`, `_stack_size_lock`, `_stack_size_found`, `_on_entry` |
| 4120–4383 | `_Stopped`, `_ThreadTooSmall`, `_DONE`, `_Box`, `_Home`, `_start_guest`, `_join_guest`, `_on_guest_thread` |

**`_call.py`** (78 names on `a9064a2`; 77 on 102's tip)

| today's lines | names, in today's order |
|---|---|
| 66–68 | `ARGV0`, `NO_HOST`, `HOST_FAULT` |
| 74–82 | `MASK32`, `UNMETERED`, `MAX_RESPONSE`, `BASE_ENV`, `Host` |
| 307–336 | `Completed` |
| 2744–2931 | `_run_checked`, `_preopens`, `_home_of`, `_call`, `_call_deferred`, `_home_folder` |
| 2952–3274 | `_import_prelude`, `_instance`, `_fuel_used`, `_Driven`, `_drive`, `_Call` |
| 3287–3456 | `_context_address` (gone on 102's tip: `ffi.context_address`), `_shared`, `_epoch_now`, `_epoch_answer`, `_stop_error`, `_on_epoch`, `_epoch_callback`, `_epoch_callback_lock`, `_watch`, `_linkers`, `_mount_linkers`, `_guard_linkers`, `_trampolines`, `_stat_trampolines` |
| 3459–3580 | `_linker`, `_runner_linker`, `_mount_linker`, `_guard_linker`, `_stat_trampoline_module`, `_trampoline_module`, `_outputs`, `_outputs_lock`, `_output_keys`, `_output_write`, `_output_free`, `_send_outputs` |
| 3627–3635 | `EINVAL`, `ENOMEM`, `EBADF`, `EFAULT`, `EIO`, `MAX_SUBSCRIPTIONS`, `SUBSCRIPTION`, `EVENT`, `CLOCK`, `FD_READ`, `FD_WRITE`, `REALTIME`, `MONOTONIC`, `ABSTIME` |
| 3638–3851 | `_Plan`, `_stop_at`, `_poll_plan`, `_Waits`, `_poll_oneoff`, `_Stream`, `_first_line`, `_trap_name`, `_trap_code_name`, `_door_answer`, `_door` |
| 4000–4050 | `_tool_threads_lock`, `_tool_threads`, `_count_tool_threads`, `_home_context`, `_ctrl_c_now`, `_tool_host` |

**`_sessions.py`** (52 names)

| today's lines | names, in today's order |
|---|---|
| 4861–4863 | the section comment "Sessions (spec 055)…" |
| 4865–4962 | `MAX_TURN_BYTES`, `SESSION_EXPORTS`, `_session_clock`, `_on_arm`, `_on_export`, `_after_export`, `_on_call`, `SessionEnded`, `_Either`, `_State`, `_sessions_lock`, `_sessions`, `_reaper`, `_reaper_queue` |
| 4963–5092 | `_WAKE`, `_dropped`, `_closers_lock`, `_closers`, `_wake_reaper`, `_take_dropped`, `_collected`, `_due`, `_mark`, `_start_closer`, `_end_quietly`, `_start_ending`, `_reap`, `_reaper_loop` |
| 5095–5374 | `_end_dropped`, `_ensure_reaper`, `_sessions_at_exit`, `_CLOSER`, `_claim_ending`, `_end_session`, `_shutdown_applies`, `_ending_seconds`, `_shutdown`, `_shutdown_export`, `_release_session`, `_drop_keys`, `_remove_home`, `_arm` |
| 5377–5782 | `_session_tool_host`, `_TurnDone`, `_home_ident`, `_drive_turn`, `_turn_inside`, `_session_turn`, `_abandon_turn`, `_end_with_ctrl_c`, `_open_session`, `_open_wasm` |

**`runner.py`** keeps 23 names

| today's lines | names, in today's order |
|---|---|
| 1–17 | the module docstring, unchanged |
| 232–296 | `Defaults`, `DEFAULTS`, `_current_defaults` |
| 358–776 | `run`, `_run_checked_flushed`, `run_async`, `_check_executor`, `_pool_lock`, `_pool`, `_pools`, `_live_lock`, `_live`, `_hook`, `_submit`, `_register_exit_hook`, `_stop_async_calls` |
| 1423–1462 | `_after_fork_in_child` (Decision 4's body) and the `os.register_at_fork` statement |
| 1480–1633 | `_checked`, `_is_async_callable`, `_check_tools` |
| 3981–3995 | `stats` |
| 4053–4066 | `_release` (Decision 4's body) |
| 5785–6241 | `Session` |

Where the 60 mutable globals land (the memo's count; EXECUTED here as 12 locks, 40 mutable
objects and 8 hooks): `runner` 6 (`_pool_lock`, `_pool`, `_pools`, `_live_lock`, `_live`,
`_hook`); `_platform` 5 (`_identity`, `_fork`, `_stack_api`, `_handlers`, and `_BUSY`, a set
never written); `_artifacts` 3 (`_versions`, `_guest_packages`, `_digests`); `_engines` 7
(`_check_modules`, `_lock`, `_engines`, `_modules`, `_counts`, `_compiling`, and
`_epoch_ticker`'s class state); `_private_dirs` 7 (`_held_lock`, `_held`, `_sweep_state`,
`_pending_warnings_lock`, `_pending_warnings`, `_warned`, and `_LOCK_NAME`, a regex);
`_zip` 2; `_places` 2 (`_win_api`, `_after_walk`); `_home` 5 (`_calls`, `_ctrl_c`,
`_stack_size_lock`, `_stack_size_found`, `_on_entry`); `_call` 12 (the five linker and
trampoline caches, `_epoch_callback`, `_epoch_callback_lock`, `_outputs`, `_outputs_lock`,
`_output_keys`, `_tool_threads_lock`, `_tool_threads`); `_sessions` 13 (`_session_clock`,
the four hooks, `_sessions_lock`, `_sessions`, `_reaper`, `_reaper_queue`, `_dropped`,
`_closers_lock`, `_closers`, `_start_ending`). Spec 104 reads this list.

### The checks, first

Each is written before the move and seen failing first, as recorded.

1. **`test_every_module_level_lock_is_remade_after_fork`** (`tests/unit/test_runner_package.py`;
   Decision 4). Seen failing first with the one-line spare lock.
2. **`test_the_runner_modules_import_in_the_written_order`** (same file). `ast` over every `.py`
   in `src/wasi_python/`: each relative import at module level names a module earlier in
   Decision 2's order (`ORDER`, written in the check), or `mounts` from `_places`, `_call`,
   `_sessions` or `runner`, or anything from `__init__.py` and `cli.py`; an import under
   `if TYPE_CHECKING:` may name any module (annotation only); no module imports `tools` at
   module level, and none imports `_wasmtime_ffi` at module level (its import loads wasmtime-py).
   Late imports of package modules (inside a `def`) are allowed only at the sites Decision 2
   lists (`LATE`, a list of `(file, function, module)` written in the check), except
   `_wasmtime_ffi`, which any function may import late (102's form, `from . import
   _wasmtime_ffi as ffi`); any other is a finding. `ORDER` is a plain tuple; 104 prepends
   `_process`. Seen failing first: today `runner.py` has `from . import
   Artifacts` at module level, `__init__` is `runner`'s importer and importee, and the check
   reports it.
3. **`test_a_module_imports_by_name_only_what_never_changes`** (same file; Decision 2's two
   forms). For every `from ._x import name` in the package (module-level and late), the object
   `wasi_python._x.name` is a class, a generic alias (`typing.get_origin(obj) is not None`), an
   instance of `int`, `float`, `str`, `bytes`, `tuple`, `frozenset` or `re.Pattern`, or one of
   `SENTINELS = ("_UNSET", "_DONE")`, a plain tuple 104 extends with `process`; anything else (a
   function, a dict, a lock, a hook) is a finding naming the importer, the name and its type. No
   module anywhere imports by `from` a name in Decision 4's `LOCKS_RESET_BY_FORK` or
   `REBOUND_BY_FORK`. And, Decision 2's condition: for every `monkeypatch.setattr(<module>,
   "NAME", …)` in `tests/` whose `NAME` on that module is a class or a constant by the rule
   above, no package module from-imports `NAME` (today `MAX_RESPONSE`, `_REMOVE_BUDGET`,
   `DEFAULTS`; 104 moves the seams and may retire this assertion by name). Seen failing first: the builder writes the
   check before the move and runs it on a one-module draft that does `from ._home import
   _ctrl_c_watched`; it names the import.
4. **`test_every_runner_name_is_defined_in_one_module`** (same file). Over the eleven runner
   modules (not `mounts.py`, `tools.py`, `cli.py`, `_wasmtime_ffi.py`, which share ten names
   with the runner today: `EBADF`, `_flags`, `_close`, `_shown` and six more, EXECUTED
   `dups.py`), no top-level name (def, class or assignment, dunders excepted) is bound in two
   modules; and each of the eleven begins with a docstring. Seen failing first: on a draft with
   `_stamp` left in both `_zip.py` and `_artifacts.py`.
5. **`test_no_module_under_src_is_over_the_line_ceiling`** (`tests/checks/test_rules.py`;
   Decision 6). Seen failing first on today's `runner.py`.
6. **The existing 2,616 fast-tier tests** (EXECUTED, the memo's collection count) and the
   unit suite are the behaviour check: every one passes unchanged, which Decision 7's sameness
   run proves.

### The CHANGELOG and the roadmap

- `CHANGELOG.md`, under the one unreleased section: "**The runner is a package** (spec 103; the
  runner design review's H1, M5, L1). `runner.py` (6,241 lines) is eleven modules, one per
  concern (`_limits`, `_platform`, `_artifacts`, `_engines`, `_private_dirs`, `_zip`,
  `_places`, `_home`, `_call`, `_sessions`, and `runner` as the thin entry), the text moved
  verbatim, in a written import order with no cycle; `__init__.py` no longer imports `runner`
  last; a unit check finds every module-level lock and proves the fork hook re-makes it; a rule
  holds every module under `src/` to 1,500 lines. Nothing the embedder sees changes: no public
  name, no message, no fuel count."
- `context/roadmap.md`: "Reserved: 102 to 107, the runner's structural chain (the design review
  of 2026-10-20, section 8): 102 the engine seam, 103 the runner as a package of one module
  per concern, 104 one owner for process state and the test seams off module globals, 105
  typed call state and a type checker, 106 `mounts.py` behind a protocol and one platform
  module, 107 a structural review as a stage; parallel-safe, stacked, one wave, one dispatch
  on the chain's tip, the `v0.1.0a7` set as the baseline; the owner, 2026-10-20." (Written by
  102's builder if it lands the line first; 103 then writes nothing.)

## Scope

In: Decisions 1 to 8. Out:

- **The `_Process` object, the fork reset as one method, and the test hooks off module globals**
  (H5): spec 104. This file leaves every hook where its functions moved and names the modules.
  Check 1 is 103's until 104 lands; 104 retires it for its own, by name.
- **A typed `_CheckedCall`, the phase enums, mypy** (H3, M1): spec 105.
- **`mounts.py` behind a protocol, `_platform.py`'s one interface, one stamp, the finding IDs
  out of comments** (H4, M3, M4, M2): spec 106. `mounts.py` changes here only in the lines
  that name the moved privates.
- **Splitting `mounts.py` or `tools.py`**: nobody's yet; Decision 6 holds them at today's size.
- **The 80-line function rule, the test-seam allowance check and the pre-build review for a
  new module-level mutable** (the memo's section 5): spec 107. **The checks on where a lock or
  a mutable may live**: spec 104. The module size ceiling is this specification's (Decision 6).
- **Any rename, reorder, reword or behaviour change**: refused by Decision 3.

## Acceptance criteria

1. **The checks exist and were seen failing first**, as *The checks* says, each failure's one
   line recorded in the landing notes (five checks; check 2's failure on today's tree, check 5's
   on today's `runner.py`, checks 1, 3 and 4 on the named drafts).
2. **Every name once.** A script over 102's tip's `runner.py` (352 names: `a9064a2`'s 355 less
   the three 102 deletes) and `__init__.py`'s eight finds each defined exactly once across
   `src/wasi_python/`'s eleven runner modules; the count is in the landing notes (360 found, 0
   missing, 0 twice).
3. **The order holds.** Check 2 passes; the two `TYPE_CHECKING` imports are the only upward
   references; `python -c "import wasi_python, sys; assert 'wasmtime' not in sys.modules"`
   exits 0 (EXECUTED by the builder).
4. **Verbatim.** `build/103/verbatim.py`'s uncategorised residue is empty; its counts (import
   lines, docstring lines, qualified lines, hook lines, the alias) are in the landing notes,
   with the qualified-line count against Decision 2's 226 (a difference is explained there).
5. **The fork hook.** Check 1 passes; `LOCKS_RESET_BY_FORK` names 12 entries, `REBOUND_BY_FORK`
   4 and `NOT_RESET` 2; the walk found at least 14 locks.
6. **The judge's files.** The 24 files of Decision 5 import from the defining module; no file
   reads a private name through `runner` but the three re-exports; `rg 'runner\._' tests/`
   finds only `_checked`, `_check_tools`, `_current_defaults`, `_pool`, `_pool_lock` and
   `_stop_async_calls` (the names that stay).
7. **Sameness.** Decision 7's command prints nothing and exits 0 against the record of 102's
   reviewed tip, on the `v0.1.0a7` set; both records' `suite` lines are in the landing notes,
   with the unit tally grown by exactly the new file's rows.
8. **Size.** Check 5 passes; each module's line count is in the landing notes, the largest
   under 1,300.
9. **Lint.** `uv run ruff check src tests` and `uv run ruff format --check src tests` are
   clean; `test_no_module_level_name_is_bound_twice` and `test_v1_4_public_api.py` pass with
   `tests/public_api.txt` byte-identical (`git diff --stat` shows it untouched).
10. **The release.** The chain's one dispatch of the release workflow on its final tip (the
    owner's rule, section 8 of the memo) shows every judge shard green with no growth line; its
    run id is in the chain's landing notes. 103 alone dispatches no run (AGENTS.md rule 2's
    rebase-only rule, extended to the chain by the owner).

## For the lane

- **Kind:** parallel-safe; second entry of the six-entry wave the owner approved for 102 to
  107 (past §5.7's five, the owner, 2026-10-20). It conflicts textually with every other entry
  of the chain in `src/wasi_python/` by construction; the chain is rebased in order, each
  builder naming its conflicts. It shares no file with any entry outside the chain except
  `CHANGELOG.md`, `context/roadmap.md` and `tests/release_shards.toml` (textual merges).
- **No growth:** no artifact byte, no fuel row, no byte row. No pass moves.
- **The claim list** (each line starts "103:"; the numbers are filled from the builder's fast
  tier on the baseline set):
  - 103: **new nodes, each passing:** `tests/checks/test_rules.py::test_no_module_under_src_is_over_the_line_ceiling`
    (no fuel; its reason the largest module and its count); `tests/unit/test_runner_package.py`
    (four rows).
  - 103: **unit rows:** the suite grows by the new file's four rows; no existing row changes
    its verdict.
  - 103: **retired checks:** none. **Lost passes:** none. **Rows that grow:** none.
  - **The judge hash changes** in `tests/checks/test_rules.py`, `tests/unit/test_runner_package.py`,
    `tests/release_shards.toml`, `tests/harness/api.py`, `tests/harness/files.py`,
    `tests/harness/paths.py`, `tests/test_api.py` and the 20 unit and check files of Decision 5.
- **The flags** (paste-safe):

  ```
  --accept "103: the runner is a package of eleven modules, one per concern, its text moved verbatim in a written acyclic import order; the fork hook names every lock by module and a check finds every lock by introspection; __init__ imports in order; no public name, message or fuel count changes"
  --accept-judge "103: a rules check holds every module under src/ to 1,500 lines (mounts.py and tools.py held at today's 2,235 and 2,450); tests/unit/test_runner_package.py (the fork list by introspection, the import order, by-name imports only of what never changes, every runner name in one module); the 24 test and harness files that named runner privates now name the defining module; api.py's INTERNAL_FILES, INTERNAL_MODULES and DEFINING list the new modules; test_v1_4_public_api's DEFAULTS-loads scan reads every module; no existing expectation edited"
  ```

- **Dry-run needs:** none of its own; the chain's one dispatch on 107's tip (criterion 10).
  The Windows shards run the new unit file as any other (`own-runner`), and check 1's child
  interpreter runs there too: `_after_fork_in_child` is a plain function on every platform,
  only its registration is POSIX-only.

## One line

`runner.py`'s 6,241 lines become eleven modules, one concern each, in a written import order,
the text moved byte for byte, the fork hook naming every lock by its module and a check
proving it; nothing the embedder sees changes.

## Landing notes

Built 2026-10-20 in the worktree `/home/user/wt/103`, branch `spec/103-the-runner-becomes-a-package`,
from the base `c15adf4` (102's built tip on `spec/102-the-engine-seam`, under build review: main
`5feb7e9`, the memo `a9064a2`, the chain's specifications and reviews, 102's three commits).
Every number here is EXECUTED on that base or on the built commit, with its command; the
outputs are kept under `build/103/` in the worktree (git-ignored): `map-on-base.txt`,
`sites-on-base.txt`, `count_globals-on-base.txt`, `dups-on-base.txt`, `seen-failing.txt`,
`fast.log`, `built.json`, `claims.toml`, `sameness-102.txt`, `sameness-baseline.txt`,
`verbatim.txt`, `unit-smoke.log`. The move's scripts and the residue script are committed as
evidence under `../research/2026-10-20-the-runner-split/` (`split.py`, `wrap_comment.py`,
`do-split.sh`, `retarget.py`, `verbatim.py`, `claims.toml`); `map.py`, `sites.py`, `table.py`,
`count_globals.py` and `dups.py` stay scratch under `build/103/`, as the Research line says.

- **Commits, in the order built:** `bbdafa3` (the checks first: `tests/unit/test_runner_package.py`,
  the size-ceiling rules check, `api.py`'s module tables, the `DEFAULTS`-loads scan over every
  module, the shard line), `b92aa5b` (the split: the ten new modules, `runner.py`, `__init__.py`,
  `mounts.py`, and the 25 judge files re-pointed), `859dad1` (the new lines name no
  specification: the owner's rule of 2026-10-20, "Code speaks for itself", `AGENTS.md` on the
  PR branch at `b7a1250`; the moved text keeps what it carried), `ea08708` (fifteen child
  interpreters the checks run from a string reach moved names, so each string's own import
  line names the modules; three lines the mechanical update had put inside a string by mistake
  are removed), `2a9546c` (this Status line and these notes, first written), `dcd5fbe` (the
  build review's three Lows in the unit file: check 3 resolves the name a file imports a runner
  module by, check 1's child loads every module of the package, a tuple or frozenset is
  unchanging only when each element is), and the commit after it, which carries the review
  `../reviews/103-the-runner-becomes-a-package-2026-10-20.md` (verdict: lands; four Lows, three
  fixed in `dcd5fbe`, the fourth answered in its Disposition) and this updated list.
- **CI: none of its own; the chain's one dispatch on the final tip** (criterion 10, the owner's
  rule for the chain). The fast tier below is the build's judge.
- **The base re-measured (EXECUTED on `c15adf4`, the scripts copied from `build/103/` with the
  three names 102 deleted struck from `map.py`):** `map.py`: 352 top-level names mapped, 0
  missing, 0 extra, 6,220 of 6,220 lines; spans plus the gap above each: `_limits` 159,
  `_platform` 374, `_artifacts` 117, `_engines` 255, `_private_dirs` 536, `_zip` 263, `_places`
  892, `_home` 326, `_call` 1,200, `_sessions` 924, `runner` 1,174 (the draft's 375, 273 and
  1,202 for `_platform`, `_engines` and `_call` are `a9064a2`'s, before 102 deleted
  `_set_async_stack`, `_wasmtime_version` and `_context_address`); two upward edges, both
  annotations (`_places -> runner: ['Defaults']`, `_home -> _call: ['_Call']`); `sites.py`: 244
  qualified Name nodes on 226 lines; `count_globals.py`: locks 12, mutable 40, hooks 8, global
  statements at 1426–1428 and 3443; `dups.py`: the ten names shared with `mounts.py` and
  `tools.py`; `wc -l`: `runner.py` 6,220, `mounts.py` 2,208 (102 took it from 2,235), `tools.py`
  2,450.
- **Every name once (criterion 2):** a script over the base's `runner.py` (352 names) and
  `__init__.py`'s eight finds 360 defined across the eleven modules, 0 missing, 0 twice; one
  name is defined only after the move, `find_artifacts` (the alias line, Decision 3, item 5).
  `uv run python -c "import wasi_python, sys; assert 'wasmtime' not in sys.modules"` exits 0
  (criterion 3).
- **Sizes after the move (`wc -l`, criterion 8):** `_limits` 171, `_platform` 389, `_artifacts`
  222, `_engines` 275, `_private_dirs` 560, `_zip` 282, `_places` 917, `_home` 347, `_call`
  1,178, `_sessions` 960, `runner` 1,225 (the largest, under 1,300), `__init__` 121,
  `mounts.py` 2,212, `tools.py` 2,450. The check's `ALLOWED` reads `{"mounts.py": 2212,
  "tools.py": 2450}`: 102 took `mounts.py` to 2,208 and the four lines that store the modules
  on `_Files` (Design) take it to 2,212, both measured, not the draft's 2,235.
- **The qualified lines (Decision 2's count):** `split.py` inserted 213 `_module.` prefixes on
  202 lines outside the two hooks (`runner` 59, `_sessions` 58, `_call` 50, `_private_dirs`
  15, `_zip` 9, `_places` 7, `_engines` 2, `_home` 2); the hooks' bodies hold 28 more qualified
  lines, 230 in all against the draft's 226 lines and 244 references. The difference: `sites.py`
  counted every `Name` node without resolving scope (a local that shadows a global, as
  `_check_tools`'s own `import functools`, is not qualified), with a syntactic kind
  classification where the build uses check 3's runtime rule (`HOST_FAULT` and `NO_HOST` are
  `int`s, so by `from`; `BASE_ENV`, `_BUSY`, `_WAKE`, the eight hooks and the two ctypes
  callbacks `_output_write`, `_output_free` are reached by attribute), and on `a9064a2`'s three
  extra names. Every by-`from` name is a class, an alias, an `int`, `float`, `str`, `bytes`,
  tuple, frozenset, regex or sentinel (check 3, EXECUTED by introspection).
- **The checks were seen failing first (criterion 1; `build/103/seen-failing.txt`):**

```
== c15adf4 (102's tip, the base), 2026-10-20: the new checks before the split ==

-- tests/unit/test_runner_package.py (checks 1 to 4) --
E       AssertionError: Traceback (most recent call last):
E           File "<string>", line 4, in <module>
E             from wasi_python import _engines, runner
E         ImportError: cannot import name '_engines' from 'wasi_python' (/home/user/wt/103/src/wasi_python/__init__.py)
E         
E       assert 1 == 0
E        +  where 1 = CompletedProcess(args=['/home/user/wt/103/.venv/bin/python', '-c', '\nimport json, sys, threading\nimport wasi_python\...\nImportError: cannot import name \'_engines\' from \'wasi_python\' (/home/user/wt/103/src/wasi_python/__init__.py)\n').returncode
E       AssertionError: findings: 15 finding(s), digest 81718f3a471a: runner.py:55 (runner imports __init__, not before it in ORDER); runner.py:56 (runner imports __init__, not before it in ORDER); runner.py:2756 (_run_checked imports __init__ late, not in LATE); runner.py:3055 (_instance imports mounts late, not in LATE); +11 more
(the check's first draft reported a sixteenth finding, `__main__.py:3 (__main__ imports cli, not before it in ORDER)`; ABOVE then named `__main__`, and the re-run on the base gave the 15 above)
E       AssertionError: findings: 10 finding(s), digest d7b55a3a75a4: _limits.py does not exist; _platform.py does not exist; _artifacts.py does not exist; _engines.py does not exist; _private_dirs.py does not exist; +5 more
E       assert not ['_limits.py does not exist', '_platform.py does not exist', '_artifacts.py does not exist', '_engines.py does not exist', '_private_dirs.py does not exist', '_zip.py does not exist', ...]
FAILED tests/unit/test_runner_package.py::test_every_module_level_lock_is_remade_after_fork
FAILED tests/unit/test_runner_package.py::test_the_runner_modules_import_in_the_written_order
FAILED tests/unit/test_runner_package.py::test_every_runner_name_is_defined_in_one_module
3 failed, 1 passed in 1.90s

-- tests/checks/test_rules.py::test_no_module_under_src_is_over_the_line_ceiling (check 5) --
E       AssertionError: findings: 1 finding(s), digest 285846d82b67: src/wasi_python/runner.py: 6,220 lines, over 1,500
E       assert not ['src/wasi_python/runner.py: 6,220 lines, over 1,500']
FAIL tests/checks/test_rules.py::test_no_module_under_src_is_over_the_line_ceiling — AssertionError: findings: 1 finding(s), digest 285846d82b67: src/wasi_python/runner.py: 6,220 lines, over 1,500
FAILED tests/checks/test_rules.py::test_no_module_under_src_is_over_the_line_ceiling
1 failed in 0.18s

-- tests/checks/test_v1_4_public_api.py (api.py's DEFINING names files that do not exist yet) --
E       FileNotFoundError: [Errno 2] No such file or directory: '/home/user/wt/103/src/wasi_python/_artifacts.py'
FAIL tests/checks/test_v1_4_public_api.py::test_the_public_api_matches_its_snapshot — FileNotFoundError: [Errno 2] No such file or directory: '/home/user/wt/103/src/wasi_python/_artifacts.py'
FAILED tests/checks/test_v1_4_public_api.py::test_the_public_api_matches_its_snapshot
1 failed in 4.30s

== after the split, the three drafts the spec names (each change reverted right after) ==

-- check 1: a _spare_lock = threading.Lock() added to _zip.py, the hook untouched --
E       AssertionError: locks in neither list: [('wasi_python._zip', '_spare_lock')]
1 failed in 0.24s

-- check 3: a from ._home import _ctrl_c_watched added to _call.py --
1
E       AssertionError: findings: 1 finding(s), digest 4d95eb327264: _call.py:26 imports _ctrl_c_watched from _home by from: function
1 failed in 1.09s

-- check 4: a _stamp left in _zip.py as well as _artifacts.py --
E       AssertionError: findings: 1 finding(s), digest 45955d5d4093: _stamp is bound in _artifacts.py and _zip.py
1 failed in 0.22s
```

  Check 3 passed on the base (no module from-imported a runner name there) and failed on the
  draft above. `test_v1_4_public_api.py` failed on the base only because `api.py`'s `DEFINING`
  named files that did not exist yet.
- **The residue script (criterion 4; `uv run python build/103/verbatim.py c15adf4`):** two
  steps, the base against the splitter's output (`build/103/preformat/`, before ruff sorted the
  imports and formatted) and that output against the tree; the uncategorised residue is empty
  on every side. The step-1 counts are Decision 8's categories: import lines 136 new and 13 old,
  docstring lines 24, qualified lines 202 (each the source of an old line with one `_module.`
  prefix stripped per name), hook lines 31 new and 32 old, the alias 1, the "Last:" comment 1.
  Step 2 names the 19 lines ruff format changed, each listed under *Differences* below.

```
lines (blank lines stripped): base 5694, split 5840, tree 5873
step 1, only in the split, by category:
  import: 136
  docstring: 24
  qualified: 202
  hook: 31
  alias: 1
  uncategorised: 0
step 1, only in the base, by category:
  import: 13
  hook: 32
  last: 1
  qualified source: 202
  uncategorised: 0
step 2, only in the tree, by category:
  import: 12
  wrapped fragment: 53
  uncategorised: 0
step 2, only in the split, by category:
  import: 13
  wrapped: 19
  uncategorised: 0
the lines the formatter wrapped (each a qualified line past 100 columns, or the moved comment):
  _platform._fork["used"] = True  # before the engine exists: a fork from here on is refused
  create = _platform._flags("O_RDWR", "O_CREAT", "O_EXCL", "O_NOFOLLOW", "O_CLOEXEC", "O_BINARY")
  owns = _platform._same_file(fd, lock_path)  # a sweeper may have removed it, still empty
  with _engines._lock:  # after the drop, so a sweep that runs first cannot spend the retry
  fd = os.open(lock_path, _platform._flags("O_RDWR", "O_NOFOLLOW", "O_NONBLOCK", "O_CLOEXEC", "O_BINARY"))
  _DIR = (_platform._flags("O_PATH") or _platform._flags("O_SEARCH") or os.O_RDONLY) | _platform._flags(
  "O_DIRECTORY", "O_NOFOLLOW", "O_CLOEXEC"
  found, checked = (artifacts, None) if artifacts is not None else _artifacts._found_and_checked(snapshot)
  _Preopen("the stdlib folder", _places._walk("", str(folder.lib), judge=False), ZIP_GUEST, False)
  return Path(p.walked.path), (os.dup(fd) if fd is not None and _platform._dir_fd_ok() else None)
  not_ready = _platform._trap_handlers_ready()  # spec 071, Decision 9: before every entry into the guest
  _private_dirs._flush_warnings()  # what the release's removals queued, outside every lock (spec 084)
  if _platform._trap_handlers_ready() is not None:  # a trap in the shutdown could end this process
  module = _engines._module(engine, metered, binary, cache, None if checked is None else checked.binary)
  root_path, state.private = _call._preopens(found, root, walked_root, walked, preopens, zip_want)
  "tool_request_bytes": _limits._integer_limit("max_tool_request_bytes", max_tool_request_bytes),
  expired = _sessions._mark(state, due[1]) and _sessions._claim_ending(state, me if here else _CLOSER)
  if _platform._fork["forked"]:  # the store and folders are the parent's: touch nothing (lock-free)
uncategorised residue: none
```

- **The fast tier on the frozen `v0.1.0a7` set** (`WASI_PYTHON_ARTIFACTS=/home/user/wasi_python/build/baseline-a7/set/wasi-python-0.1.0a7`,
  `uv run pytest -m "not slow" -n 3 -q -p no:cacheprovider`, on `ea08708`, under the machine's
  `build/fast-tier.lock`): **83 failed, 2368 passed, 52 skipped in 324.41s (0:05:24)**; a first run on `859dad1` (its failure list, `build/103/failed-859dad1.txt`; its log was overwritten by the kept run)
  showed 102 failures, the 19 beyond the baseline all child-script strings whose import line
  lacked a module (`NameError` in the child, or in its ticker thread, so a deadline or Ctrl-C
  never fired), fixed in `ea08708` and re-run by node id (19 passed, `build/103/rerun-19.log`); the 83 failures are the chain's baseline's
  `failing-nodes.txt` exactly (82 checks of an artifact set older than the tree, and
  `test_runner_grants.py::test_the_walk_judges_links`, which needs a non-root user). The record
  is `build/103/built.json`.
- **Sameness (criterion 7).** Against 102's built record (`/home/user/wt/102/build/102/built.json`):

```
note: explained by claims: 103 3
sameness exit 0
```

  Against the chain's baseline (`/home/user/wasi_python/build/baseline-a7/baseline.json`):

```
note: explained by claims: 103 2
tests/checks/test_rules.py::test_only_the_engine_seam_touches_wasmtimes_private_api: only in the second record
tests/checks/test_rules.py::test_the_private_api_debt_is_documented: only in the second record
collected_files: tests/unit/test_wasmtime_ffi.py only in the second record
suite: {'passed': 1833, 'skipped': 13, 'total': 1847} != {'passed': 1854, 'skipped': 13, 'total': 1868}
sameness exit 1
```

  What the baseline comparison prints is 102's work, which the baseline predates (its two
  rules checks, its unit file, its 17 unit rows); with 102's claim list beside 103's
  (`build/103/claims-chain.toml`, the two files concatenated) it prints nothing:

```
note: explained by claims: 102 4 · 103 3
sameness exit 0
```

  The three records' `suite` lines: the baseline `{'passed': 1833, 'skipped': 13, 'total':
  1847}` (`a9064a2`), 102's `{'passed': 1850, 'skipped': 13, 'total': 1864}` (`d77425d`),
  103's `{'passed': 1854, 'skipped': 13, 'total': 1868}` (`ea08708`): the unit tally grows by
  exactly the new file's four rows.
- **The judge's files (criterion 6):** 25, not 24: the 24 of Decision 5 and
  `tests/unit/test_wasmtime_ffi.py`, 102's new file, which names `_wasmtime` (`_engines`),
  `_output_write`, `_output_free` and `_stop_error` (`_call`). `rg 'runner\._' tests/` finds
  `_checked`, `_check_tools`, `_current_defaults`, `_pool`, `_pool_lock`, `_stop_async_calls`
  (the six that stay), `__file__`, and `_after_fork_in_child` in the new unit file (check 1
  calls the hook where it lives). `tests/unit/test_cli.py` keeps `from wasi_python.runner import
  Completed`; `test_v1_4_embedding.py` keeps its `from wasi_python.runner import DEFAULTS`.
  `tests/public_api.txt` is untouched (`git diff --stat c15adf4` does not list it). `api.py`'s
  tables gain the ten modules and 102's `_wasmtime_ffi.py` (102 added nothing for it: its
  `INTERNAL_FILES`, `INTERNAL_MODULES` and `DEFINING` on `c15adf4` are the three original tuples,
  EXECUTED).
- **Lint (criterion 9):** `uv run ruff check src tests` and `uv run ruff format --check src
  tests` clean on every commit; `test_no_module_level_name_is_bound_twice` passes.
- **One stale comment left as it is (Decision 3):** `runner.py`'s module docstring still says
  wasmtime-py "is imported only here, when a call is made"; the import is `_engines._wasmtime`'s
  now. Spec 106's comment pass rewrites it.
- **The mutable globals, by module after the move (`count_globals.py` on each file, EXECUTED;
  spec 104 reads this):** `runner` locks 2 (`_pool_lock`, `_live_lock`), mutable 4; `_platform`
  mutable 5; `_artifacts` mutable 3; `_engines` lock 1, mutable 5; `_private_dirs` locks 2,
  mutable 4; `_zip` lock 1, mutable 1; `_places` mutable 1, hook 1; `_home` lock 1, mutable 3,
  hook 1; `_call` locks 3, mutable 9 (`BASE_ENV` counted), hook 1; `_sessions` locks 2, mutable
  5, hooks 5: 12 locks, 40 mutables, 8 hooks, as the Design's list.

### Differences from the specification's text, each with its reason

1. **The new lines name no specification** (commit `859dad1`): the ten module docstrings say
   their concern in words, without the "one `# spec NNN` per concern" Decision 3 item 2 asked
   for, and the unit file, the rules check and the harness comments name no decision or
   specification; the owner's rule of 2026-10-20 ("Code speaks for itself", `AGENTS.md` at
   `b7a1250`) binds every new line under `src/` and `tests/`. The moved text keeps its "spec
   NNN" mentions; spec 106 removes them.
2. **Nineteen lines the formatter changed** (Decision 3 allows a qualified line to differ by its
   prefixes only; ruff's 100-column limit forces these): 18 qualified lines went past 100
   columns and `ruff format` wrapped them, in its own way, so the move stays mechanical and
   reproducible (`do-split.sh`); and one, `_private_dirs._flush_warnings()  # what the release's
   removals queued, outside every lock (spec 084)` in `_sessions._end_session`, carries a
   trailing comment the formatter cannot wrap, so the comment moved to the line above
   (`wrap_comment.py`). The residue script's step 2 lists all nineteen and proves each tree line
   is a fragment of one of them.
3. **`mounts.py` stores the home module as `self._home_module`**, not `self._home`: `_Files._home`
   is the home-thread dispatcher method. The other three are `self._call`, `self._engines`,
   `self._places`, as Design says; the twelve sites read as Design lists them with that one
   name.
4. **`__init__.py` drops `os`, `dataclass` and `Path`** from its import block (unused after the
   artifact block moved; ruff refuses an unused import), against "lines 29–34 ... stay".
5. **Check 3 reads imports from the runner's eleven modules only**, not from `mounts` and
   `tools`: the unchanged late imports Decision 2 keeps bring a function (`trampoline_wat`) and
   a dict (`SIGNATURES`), which are those modules' own forms; and `__init__.py` is left out,
   since it re-exports `run`, `artifacts` and the other public functions by name. Check 2's
   `ABOVE` also names `__main__.py` (it imports `cli`).
6. **`tests/unit/test_runner_tools.py` imports `_artifacts as artifacts_module`**: the file has a
   helper named `_artifacts` (its stand-in artifact set), and a second module-level binding of
   the name is what `test_no_module_level_name_is_bound_twice` refuses.
7. **`tests/harness/paths.py`'s docstring** was reflowed by one line break where the new name
   `wasi_python._artifacts._ARTIFACT_DIR` took it past 100 columns.
8. **The residue script compares three texts, not two**: the base, the splitter's output and
   the tree, so the formatter's wraps (item 2) are proved to be fragments and nothing else.
9. **The draft's "244 references on 226 lines" is 213 on 202 plus the hooks' 28** (above).

### For the lane

- Kind: parallel-safe; second entry of the chain's wave, stacked on 102's `c15adf4`; conflicts
  by construction with every chain entry in `src/wasi_python/` (the chain rebases in order).
- The claim list (`build/103/claims.toml`, also under the research folder): one claim, `spec =
  "103"`, `new = ["tests/checks/test_rules.py::test_no_module_under_src_is_over_the_line_ceiling",
  "tests/unit/test_runner_package.py"]`, `units = 4`. No row grows, none is retired, no pass
  moves; the judge hash changes in the 25 files above, `tests/checks/test_rules.py`,
  `tests/unit/test_runner_package.py` and `tests/release_shards.toml`.
- The flags (paste-safe):

  ```
  --accept "103: the runner is a package of eleven modules, one per concern, its text moved verbatim in a written acyclic import order; the fork hook names every lock by module and a check finds every lock by introspection; __init__ imports in order; no public name, message or fuel count changes"
  --accept-judge "103: a rules check holds every module under src/ to 1,500 lines (mounts.py and tools.py held at today's 2,212 and 2,450); tests/unit/test_runner_package.py (the fork list by introspection, the import order, by-name imports only of what never changes, every runner name in one module); the 25 test and harness files that named runner privates now name the defining module; api.py's INTERNAL_FILES, INTERNAL_MODULES and DEFINING list the new modules and the engine seam; test_v1_4_public_api's DEFAULTS-loads scan reads every module; no existing expectation edited"
  ```

### The builder's self-check

- rebased onto the named stacked base today (102's `c15adf4`); the base commit in the Status
  line: checked.
- CI run dispatched on this exact commit and read: **unchecked by the chain's rule** (one
  dispatch on the chain's final tip; 103 dispatches none).
- every number from a measured run on this base, labelled EXECUTED; the growth list is this
  build's (empty): checked.
- "For the lane": the claim list, the exact flags, each reason beginning with the spec number,
  the wave kind, dry-run needs: checked.
- every new check seen failing first: checked (five checks, above). A Windows and a Linux
  branch: none added; the move changes no branch, and the Windows walk moved verbatim (check 1's
  child interpreter runs on every platform: the hook is a plain function there).
- every gap names its closer; every reserved follow-up has a roadmap line: checked (no new gap;
  the roadmap line is 102's to write; `CHANGELOG.md` and `context/roadmap.md` untouched here by
  the builder's brief, the lane adds the CHANGELOG entry of Design at the landing).
- packages.toml has its reason line; README rows the spec changes listed: not applicable (no
  package, no README row).
- CHANGELOG under the one unreleased section: **unchecked** (the brief: do not touch
  `CHANGELOG.md`; the entry's text is in Design).
- ruff check, ruff format --check, the fast tier: green (the baseline's 83), output in
  `build/103/`: checked.
