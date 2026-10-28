"""One owner for the process's state: every lock, cache, counter, pool, registry and seam of the
runner is an attribute of one `_Process`, made in one place, reset for a fork by one method and
released at exit by another.

`process()` returns the one instance. Production code reads the state as `process().<name>` at
every use, never through a module-level binding of the instance or of one of its attributes, so
a lock the fork re-made or a cache the exit cleared is what every caller sees. This module
imports the standard library only; the sibling types it names are annotations.

The lock order. Four pairs are taken nested; everything else is a leaf.

1. `zip_lock` is taken first, and under it `cache_lock`, `held_lock` and `warnings_lock` may be
   taken, one at a time, never two at once: making a zip folder makes a private folder, whose
   constructor takes `held_lock`, and removing one takes `cache_lock`, then `warnings_lock` (a
   warning queued), then `held_lock` (the name dropped), each released before the next.
2. `stack_size_lock` is taken first, and under it a home's own `lock`, where a guest thread is
   started inside the stack-size window.
3. Every other lock is a leaf: nothing is taken under `pool_lock`, `live_lock`,
   `warnings_lock`, `epoch_callback_lock`, `outputs_lock`, `tool_threads_lock`, `cache_lock`,
   `held_lock`, `sessions_lock`, `closers_lock`, `ticker_cond`, `defaults_lock`, a `compiling`
   guard, a session's `lock` or a home's `lock`.
4. `warnings_lock` is held only while a warning is queued or the queue is flushed, and the
   flush runs outside every other lock, so an embedder's `showwarning` may take any lock it
   likes.
5. `outputs_lock` is re-entrant (a finalizer the collector runs inside a locked block re-enters
   it on the same thread); no other lock is.

A new lock is a leaf unless this list is amended, and the amendment names the pair.

The judge's rule: a unit check or a goal check patches nothing in `wasi_python` that starts with
an underscore except through `process()`: a field of `process().observers`, or an attribute of
`process()` itself. A function seam a check still replaces by name is an allowance, each named
with its closer in the specification that lists it.
"""

from __future__ import annotations

import atexit
import collections
import itertools
import os
import queue
import threading
import time
import weakref
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from concurrent.futures import Future, ThreadPoolExecutor

    import wasmtime

    from ._outputs import _Stream
    from ._sessions import _State

# A live call's cancel event maps to None, or, for a session's turn, to its future and the
# release of its claim, which the exit hook runs if its shutdown of the pools cancels the turn
# before it starts. The default pools map to the count of their futures not yet done; a done
# future puts its pool on `pool_done`, without a lock, and the next submit counts it under
# `pool_lock`, so a pool a resize replaced is let go once none of its futures is left.
_Queued = tuple["Future[Any]", Callable[[], None]]

# The counts `stats()` reports, each 0 when the process starts.
COUNTS = (
    "compiled",
    "loaded",
    "written",
    "sessions_open",
    "snapshots_made",
    "snapshots_restored",
)

# How a lock is recognised and made anew for a fork: by its exact type, through this table. Not
# `isinstance` and not `type(value)()`: on Python 3.11 and 3.12 `threading.Lock` and
# `threading.RLock` are factory functions, not types, and `type(threading.Lock())()` raises; the
# keys are what `type(threading.Lock())` returns on every version from 3.11. A `Condition` made
# anew is over a new lock and carries no waiters, which is right: a waiter was a thread the child
# does not have.
RENEW: dict[type, Callable[[], Any]] = {
    type(threading.Lock()): threading.Lock,
    type(threading.RLock()): threading.RLock,
    threading.Condition: lambda: threading.Condition(),
    queue.SimpleQueue: queue.SimpleQueue,
}


@dataclass(slots=True)
class _Observers:
    """The seams the judge sets, and nothing production reads for its own sake. Slots, so an
    assignment to a misspelt field raises `AttributeError` everywhere, in a program run as a
    subprocess as under monkeypatch. `None` means the production default: nothing is called, or
    the production closer, or the process's own drive folder."""

    after_walk: Callable[[], None] | None = None  # after every walk, before wasmtime opens
    on_entry: Callable[[str], None] | None = None  # each entry's kind, on its guest thread
    on_arm: Callable[[str, int], None] | None = None  # each arming: its kind and its ticks
    on_export: Callable[[str, int], None] | None = None  # each export called: name, thread
    after_export: Callable[[], None] | None = None  # after a turn's export returned
    on_call: Callable[[str, Any], None] | None = None  # each call built: its kind and the call
    on_capture: Callable[[str], None] | None = None  # each output capture opened: its kind
    clock: Callable[[], float] = time.monotonic  # the one clock the session bounds read
    start_ending: Callable[[_State], None] | None = None  # None: the production closer
    drive_folder: Callable[[str], str] | None = None  # None: `ntpath.abspath(drive or ".")`
    owner_of: Callable[[os.stat_result], int] | None = None  # None: the stat's own `st_uid`
    reaper_enabled: bool = True  # False: sessions open without the reaper thread
    reaper_paused: bool = False  # True: the loop sleeps and the judge drives `_reap` alone


class _Process:
    """The state of this process, in groups by concern. The constructor is the one place it is
    made; a second instance is cheap and touches nothing live, which is how the unit checks
    read it."""

    def __init__(self) -> None:
        # A. run_async's default pool, its live calls and its exit hook.
        self.pool_lock = threading.Lock()
        self.pool: ThreadPoolExecutor | None = None
        self.pool_size: int = 0
        self.pools: dict[ThreadPoolExecutor, int] = {}  # each kept pool: its futures not done
        self.pool_done: queue.SimpleQueue[ThreadPoolExecutor] = queue.SimpleQueue()
        self.live_lock = threading.Lock()
        self.live: dict[threading.Event, _Queued | None] = {}  # a queued session turn's, if any
        self.exit_hook_registered: bool = False
        self.exiting: bool = False
        # B. Private folders, the sweep and the warnings.
        self.held_lock = threading.Lock()
        # The names this process holds: NFS may treat flock as per-process.
        self.held: set[str] = set()
        self.sweep_claimed: bool = False  # under `cache_lock`
        self.sweep_swept: int = 0
        self.sweep_failed: dict[str, int] = {}  # failed sweeps of a name, in this process
        self.warnings_lock = threading.Lock()
        self.pending_warnings: list[str] = []  # given by the flush, outside every runner lock
        self.warned: set[str] = set()  # each folder is named once per process
        # C. Fork.
        self.fork_used: bool = False  # an engine exists: a fork from here on is refused
        self.forked: bool = False  # this is a child of a parent that made an engine
        # D. The trap-handler check's C functions, resolved once.
        self.handlers: dict[str, Any] = {}  # the C library's sigaction and dladdr, wasmtime's base
        # E. The zip, the preopen check and the manifest facts.
        self.zip_lock = threading.Lock()
        self.zips: dict[str, list[Any]] = {}
        self.check_modules: dict[bool, Any] = {}
        # Both keyed on (the path, *its stamp): device, inode, size, mtime_ns and ctime_ns.
        self.versions: dict[tuple[str, int, int, int, int, int], str] = {}
        self.guest_packages: dict[str, tuple[tuple[int, ...], bool]] = {}  # path: (stamp, answer)
        self.digests: dict[tuple[str, int, int, int, int, int], str] = {}
        # F. Under `cache_lock`: engines, modules, counts, snapshot folders; linkers; the epoch.
        self.cache_lock = threading.Lock()
        self.engines: dict[bool, wasmtime.Engine] = {}
        self.modules: dict[tuple[bool, str], wasmtime.Module] = {}
        self.compiling: dict[tuple[bool, str], threading.Lock] = {}
        self.counts: dict[str, int] = dict.fromkeys(COUNTS, 0)  # what `stats()` reports
        self.snapshot_folders: set[str] = set()  # each saved or loaded snapshot file's folder
        self.live_writable: dict[Any, str] = {}  # live calls' writable walks, and their names
        self.epoch_callback: Any | None = None  # the one C callback, made on first use
        self.epoch_callback_lock = threading.Lock()
        self.linkers: dict[Any, Any] = {}
        self.mount_linkers: dict[Any, Any] = {}
        self.counted_linkers: dict[Any, Any] = {}
        self.trampolines: dict[Any, Any] = {}
        self.ticker_cond = threading.Condition()
        self.ticker_thread: threading.Thread | None = None
        self.ticker_active: int = 0
        self.ticker_count: int = 0  # epochs advanced so far, updated after the engines are
        # G. The thread's call, the outputs, Ctrl-C, the tool threads and the stack window.
        self.calls = threading.local()  # its `stack`, `watched` and `lost`
        self.outputs: dict[int, _Stream] = {}
        # Re-entrant: a finalizer the collector runs inside a locked block re-enters it.
        self.outputs_lock = threading.RLock()
        self.output_keys = itertools.count(1)
        self.ctrl_c_pending: bool = False
        self.tool_threads_lock = threading.Lock()
        self.tool_threads_running: int = 0
        self.tool_threads_abandoned: int = 0  # running on after their call was answered
        self.stack_size_lock = threading.Lock()
        # threading.stack_size's value, while the window is open.
        self.stack_size_found: list[int] = []
        # H. Sessions and the reaper.
        self.sessions_lock = threading.Lock()
        self.sessions: weakref.WeakSet[_State] = weakref.WeakSet()
        self.reaper_thread: threading.Thread | None = None
        self.reaper_stop: bool = False
        self.reaper_hooked: bool = False  # the sessions' exit hook is registered
        self.reaper_queue: queue.SimpleQueue[Any] = queue.SimpleQueue()
        # Taken from the queue, not yet ended.
        self.dropped: collections.deque[_State] = collections.deque()
        self.closers_lock = threading.Lock()
        self.closers: set[threading.Thread] = set()
        # I. The defaults: `set_defaults` swaps the binding `run` reads under this lock.
        self.defaults_lock = threading.Lock()
        # J. Observers and overrides.
        self.observers = _Observers()
        # What the exit release calls first, bound by the zip and the private-folder modules at
        # their import; no-ops until then, so a fresh instance is safe to release.
        self.remove_zips: Callable[[], None] = lambda: None
        self.flush_warnings: Callable[[], None] = lambda: None

    def reset_after_fork(self) -> None:
        """Only assignments, and no lock taken: a lock may have been held by a thread the fork
        left out, so every lock, condition and queue is made anew, by the RENEW table rather than
        by a list. The parent's workers, tool threads, zip folders, compiling guards, ticker
        thread, sessions and reaper are not in the child; its facts of the kernel, the files, the
        engines, the outputs and the warnings are kept, and so are the snapshot folders: a child
        holds its parent's snapshots and files."""
        for name, value in list(vars(self).items()):
            factory = RENEW.get(type(value))
            if factory is not None:
                setattr(self, name, factory())
        self.pool, self.pool_size = None, 0
        self.pools.clear()
        self.live.clear()
        # A fork inside the runner's stack-size window leaves the child at the guest thread's
        # size; put back the value the runner found.
        if self.stack_size_found:
            threading.stack_size(self.stack_size_found[0])
            self.stack_size_found.clear()
        self.tool_threads_running = 0  # a child has none of its parent's tool threads
        self.tool_threads_abandoned = 0
        self.zips = {}  # the parent's zip folders stay the parent's: their locks are its
        self.compiling = {}  # per-digest guards, possibly held by lost threads
        self.ticker_thread, self.ticker_active = None, 0
        # A child has no reaper, no sessions and none open; the exit hook's registration is
        # inherited by the child's interpreter, so `reaper_hooked` is kept.
        self.sessions = weakref.WeakSet()
        self.closers.clear()
        self.dropped.clear()
        self.reaper_thread, self.reaper_stop = None, False
        self.counts["sessions_open"] = 0
        self.live_writable = {}  # the parent's calls are not the child's
        if self.fork_used:  # the fact the refusal needs: wasmtime does not survive a fork
            self.forked = True

    def release_at_exit(self) -> None:
        """Remove this process's zip folders, flush the warnings they queued, and free the cached
        linkers, modules and engines while wasmtime's bindings still exist."""
        self.remove_zips()
        self.flush_warnings()
        self.check_modules.clear()
        self.linkers.clear()
        self.mount_linkers.clear()
        self.counted_linkers.clear()
        self.trampolines.clear()
        self.modules.clear()
        self.engines.clear()


_PROCESS = _Process()


def process() -> _Process:
    """The one instance, made at import; never rebound."""
    return _PROCESS


if hasattr(os, "register_at_fork"):  # not on Windows, which has no fork
    os.register_at_fork(after_in_child=lambda: process().reset_after_fork())
atexit.register(process().release_at_exit)
