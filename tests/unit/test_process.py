"""The process's state has one owner, and a fork or an exit resets it in one place.

The owner re-makes every lock, condition and queue it holds for a fork by looking at itself
through one type-to-factory table, so a lock added later cannot be left off a list; the fields a
child must not inherit are reset and the facts a child shares are kept; the exit release removes
the zip folders and flushes the warnings before it clears the caches; and the observers refuse a
misspelt field, in a subprocess program as under monkeypatch.
"""

from __future__ import annotations

import collections
import dataclasses
import queue
import threading
import weakref

import pytest

from wasi_python import _process
from wasi_python._process import _Observers, _Process

LOCK, RLOCK = type(threading.Lock()), type(threading.RLock())

# What a fork resets, each with the value a fresh instance holds (`counts` by its one key).
RESET = (
    "pool",
    "pool_size",
    "pools",
    "live",
    "tool_threads_running",
    "zips",
    "compiling",
    "ticker_thread",
    "ticker_active",
    "sessions",
    "closers",
    "dropped",
    "reaper_thread",
    "reaper_stop",
    "stack_size_found",
)
# What a fork keeps, each with a marker the check sets.
KEPT = {
    "held": {"a-name"},
    "sweep_claimed": True,
    "sweep_swept": 3,
    "sweep_failed": {"a-name": 1},
    "handlers": {"dladdr": "a function"},
    "check_modules": {True: "a module"},
    "versions": {"a manifest": "314"},
    "guest_packages": {"a path": ((1, 2), True)},
    "digests": {("a path", 1, 2): "a digest"},
    "engines": {True: "an engine"},
    "modules": {(True, "a digest"): "a module"},
    "counts": {"compiled": 1, "loaded": 2, "written": 3, "sessions_open": 0},
    "epoch_callback": "a callback",
    "linkers": {"an engine": "a linker"},
    "mount_linkers": {"an engine": "a linker"},
    "counted_linkers": {"an engine": "a linker"},
    "trampolines": {"an engine": "a module"},
    "ticker_count": 42,
    "outputs": {1: "a stream"},
    "ctrl_c_pending": True,
    "exit_hook_registered": True,
    "exiting": True,
    "reaper_hooked": True,
    "warned": {"a folder"},
    "pending_warnings": ["a warning"],
    "fork_used": True,
}


class _Anchor:
    """A weak-referenceable member for a WeakSet."""


def _renewable(p: _Process) -> dict[str, int]:
    return {name: id(value) for name, value in vars(p).items() if type(value) in _process.RENEW}


def test_reset_after_fork_renews_every_lock_it_can_see() -> None:
    p = _Process()
    before = _renewable(p)
    kinds = {type(getattr(p, name)) for name in before}
    assert len(before) >= 4 and kinds == set(_process.RENEW), sorted(before)
    observers = p.observers
    p.reset_after_fork()
    after = _renewable(p)
    assert sorted(after) == sorted(before), "a renewed lock changed its name or its kind"
    kept = sorted(name for name in before if after[name] == before[name])
    assert not kept, f"locks the reset did not re-make: {kept}"
    assert p.observers is observers


def test_renew_knows_every_lock_kind() -> None:
    assert set(_process.RENEW) == {LOCK, RLOCK, threading.Condition, queue.SimpleQueue}
    for kind, factory in _process.RENEW.items():
        assert type(factory()) is kind, kind


def test_reset_after_fork_resets_what_a_child_must_not_inherit() -> None:
    p, fresh = _Process(), _Process()
    anchor = _Anchor()
    p.pool, p.pool_size, p.pools = object(), 7, [object()]
    p.live = {threading.Event()}
    p.tool_threads_running = 3
    p.zips = {"a digest": [object(), (1, 2), None]}
    p.compiling = {(True, "a digest"): threading.Lock()}
    p.ticker_thread, p.ticker_active = object(), 2
    p.sessions = weakref.WeakSet([anchor])
    p.closers = {threading.current_thread()}
    p.dropped = collections.deque([anchor])
    p.reaper_thread, p.reaper_stop = object(), True
    p.counts["sessions_open"] = 5
    old = threading.stack_size()
    p.stack_size_found = [old]
    p.reset_after_fork()
    for name in RESET:
        got, want = getattr(p, name), getattr(fresh, name)
        assert type(got) is type(want) and got == want, (name, got)
        if name == "sessions":
            assert len(got) == 0
    assert p.counts["sessions_open"] == 0
    assert threading.stack_size() == old
    del anchor


def test_reset_after_fork_keeps_the_facts_a_child_shares() -> None:
    p = _Process()
    calls, output_keys, observers = p.calls, p.output_keys, p.observers
    for name, value in KEPT.items():
        setattr(p, name, value)
    assert p.forked is False
    p.reset_after_fork()
    for name, value in KEPT.items():
        assert getattr(p, name) is value, name  # the same object, not a copy
    assert p.forked is True, "a child of a parent that made an engine is marked"
    assert p.calls is calls and p.output_keys is output_keys and p.observers is observers
    plain = _Process()
    plain.reset_after_fork()
    assert (plain.fork_used, plain.forked) == (False, False), "an engine-less parent's child runs"


def test_release_at_exit_removes_zips_and_flushes_warnings_before_it_clears_the_caches() -> None:
    p = _Process()
    tables = (
        "check_modules",
        "linkers",
        "mount_linkers",
        "counted_linkers",
        "trampolines",
        "modules",
        "engines",
    )
    for name in tables:
        getattr(p, name)["a key"] = "a value"
    order: list[tuple[str, bool]] = []
    p.remove_zips = lambda: order.append(("remove_zips", all(getattr(p, n) for n in tables)))
    p.flush_warnings = lambda: order.append(("flush_warnings", all(getattr(p, n) for n in tables)))
    p.release_at_exit()
    assert order == [("remove_zips", True), ("flush_warnings", True)]
    assert all(getattr(p, name) == {} for name in tables)
    fresh = _Process()
    fresh.release_at_exit()  # the defaults are no-ops: a fresh instance is safe to release


def test_the_observers_refuse_a_misspelt_field() -> None:
    observers = _Observers()
    with pytest.raises(AttributeError):
        observers.on_entyr = lambda kind: None  # type: ignore[attr-defined]
    assert [f.name for f in dataclasses.fields(observers)] == [
        "after_walk",
        "on_entry",
        "on_arm",
        "on_export",
        "after_export",
        "on_call",
        "clock",
        "start_ending",
        "drive_folder",
        "reaper_enabled",
        "reaper_paused",
    ]
    assert (observers.reaper_enabled, observers.reaper_paused) == (True, False)
    assert observers.start_ending is None and observers.drive_folder is None
