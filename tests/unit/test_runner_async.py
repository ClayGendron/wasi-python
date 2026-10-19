"""Run from async code (spec 015): the epoch callback's decisions, run_async's refusals and the
default pool's size. Fakes stand in for wasmtime; nothing here measures time."""

from __future__ import annotations

import asyncio
import concurrent.futures
import ctypes
import threading
from types import SimpleNamespace

import pytest

from wasi_python import runner

STOP = 77  # what the fake error maker returns


@pytest.fixture
def epoch(monkeypatch):
    """A fake call on this thread's stack, the context it is checked against, and a delta."""
    monkeypatch.setattr(runner, "_stop_error", lambda delta=None: STOP)
    monkeypatch.setattr(runner, "_ctrl_c_watched", lambda: False)
    monkeypatch.setattr(runner._epoch_ticker, "count", classmethod(lambda cls: 100))
    holder = ctypes.c_int(0)
    context = ctypes.pointer(holder)
    call = SimpleNamespace(
        context=ctypes.addressof(holder),
        stopped=None,
        cancel=threading.Event(),
        stop_at=None,
        ended=None,
    )
    stack = runner._stack()
    stack.append(call)
    runner._calls.lost = False
    delta = (ctypes.c_uint64 * 1)()
    yield SimpleNamespace(call=call, context=context, delta=delta, holder=holder)
    stack.remove(call)
    runner._calls.lost = False


def answer(e) -> int:
    return runner._epoch_answer(e.context, e.delta)


def test_the_epoch_callback_continues_by_up_to_five_ticks(epoch) -> None:
    assert answer(epoch) == 0 and epoch.delta[0] == runner.CANCEL_TICKS == 5
    epoch.call.stop_at = 102  # two ticks left
    assert answer(epoch) == 0 and epoch.delta[0] == 2
    epoch.call.stop_at = 101  # one tick left: never 0
    assert answer(epoch) == 0 and epoch.delta[0] == 1
    assert epoch.call.ended is None and epoch.call.stopped is None


def test_the_epoch_callback_ends_a_call_at_its_deadline_and_at_a_cancel(epoch) -> None:
    epoch.call.stop_at = 100
    assert answer(epoch) == STOP and epoch.call.ended == "deadline"
    epoch.call.ended = None
    epoch.call.cancel.set()  # a cancel is named before a deadline
    assert answer(epoch) == STOP and epoch.call.ended == "cancelled"


def test_a_recorded_stop_holds_under_the_epoch_callback(epoch) -> None:
    """Spec 015's review, finding 1: a callback that continued undid spec 011's stops."""
    epoch.call.stopped = KeyboardInterrupt()
    epoch.call.cancel.set()
    epoch.call.stop_at = 100
    assert answer(epoch) == STOP
    assert epoch.call.ended is None  # the stop is the outcome, not the cancel or the deadline


def test_a_deferred_ctrl_c_becomes_a_stop(epoch, monkeypatch) -> None:
    monkeypatch.setattr(runner, "_ctrl_c_watched", lambda: True)
    monkeypatch.setitem(runner._ctrl_c, "pending", True)
    epoch.call.cancel.set()
    assert answer(epoch) == STOP
    assert isinstance(epoch.call.stopped, KeyboardInterrupt) and epoch.call.ended is None
    assert runner._ctrl_c["pending"] is False


def test_a_fault_in_the_epoch_callback_stops_the_guest(epoch) -> None:
    """Finding 2: a callback that raised wrote no answer, and the guest lost its deadline."""

    class Raising:
        def is_set(self):
            raise ZeroDivisionError("from is_set")

    epoch.call.cancel = Raising()
    assert answer(epoch) == STOP
    assert isinstance(epoch.call.stopped, ZeroDivisionError)


def test_another_stores_context_is_not_this_call(epoch) -> None:
    other = ctypes.c_int(0)
    assert runner._epoch_answer(ctypes.pointer(other), epoch.delta) == STOP
    assert runner._calls.lost is True and epoch.call.ended is None


def test_a_lost_call_stops_the_guest_and_drive_says_so(epoch, monkeypatch) -> None:
    """Spec 015's confirmation, findings 22 and 26: a stack lookup that raises sets the thread's
    flag and stops the guest; `_drive` then raises, and clears the flag for the next call."""

    def broken():
        raise RuntimeError("stack")

    monkeypatch.setattr(runner, "_stack", broken)
    assert answer(epoch) == STOP and runner._calls.lost is True
    monkeypatch.undo()

    class WasmtimeError(Exception):
        pass

    wt = SimpleNamespace(
        ExitTrap=type("ExitTrap", (Exception,), {}),
        Trap=type("Trap", (Exception,), {}),
        WasmtimeError=WasmtimeError,
    )

    class Linker:
        def instantiate(self, store, module):
            runner._calls.lost = True  # as the callback does
            raise WasmtimeError("stopped by wasi_python")

    # This `_drive` gets stand-ins, not wasmtime, so on Linux a process that has made no engine yet
    # has no wasmtime trap handlers for spec 071's guard to find; the guard is not what this tests
    # (spec 080, Decision 2).
    monkeypatch.setattr(runner, "_trap_handlers_ready", lambda: None)
    call = SimpleNamespace(cancel=None, stopped=None, ended=None)
    with pytest.raises(RuntimeError, match="lost track of a call"):
        runner._drive(wt, Linker(), None, None, call, None)
    assert runner._calls.lost is False


class Recording(concurrent.futures.Executor):
    def __init__(self) -> None:
        self.submitted = []

    def submit(self, fn, /, *args, **kwargs):
        self.submitted.append(fn)
        raise AssertionError("submit must not be reached")


def test_run_async_refuses_a_bad_argument_before_queueing() -> None:
    ex = Recording()
    with pytest.raises(TypeError):
        asyncio.run(runner.run_async(["-c", 1], executor=ex))
    with pytest.raises(ValueError):
        asyncio.run(runner.run_async(["-c", "pass"], fuel=-1, executor=ex))
    assert ex.submitted == []


def test_run_async_refuses_a_process_or_interpreter_pool() -> None:
    pools = [concurrent.futures.ProcessPoolExecutor(1)]
    interpreters = getattr(concurrent.futures, "InterpreterPoolExecutor", None)
    if interpreters is not None:
        pools.append(interpreters(1))
    try:
        for pool in pools:
            with pytest.raises(TypeError, match="threads of this process"):
                asyncio.run(runner.run_async(["-c", "pass"], executor=pool))
    finally:
        for pool in pools:
            pool.shutdown()
    with pytest.raises(TypeError):
        asyncio.run(runner.run_async(["-c", "pass"], executor=object()))


def test_async_workers_is_checked_like_the_other_limits() -> None:
    assert runner.Defaults(1 << 30, 60.0, 16 << 20).async_workers == runner._default_workers()
    assert 1 <= runner._default_workers() <= 8
    assert runner.Defaults(1 << 30, 60.0, 16 << 20, 3).async_workers == 3
    for bad, error in ((True, TypeError), (2.0, TypeError), (0, ValueError), (1025, ValueError)):
        with pytest.raises(error):
            runner.Defaults(1 << 30, 60.0, 16 << 20, bad)


def test_run_refuses_a_cancel_that_is_not_an_event() -> None:
    with pytest.raises(TypeError, match="threading.Event"):
        runner.run(["-c", "pass"], cancel=asyncio.Event())


def test_a_forked_child_of_a_used_runner_is_refused(monkeypatch) -> None:
    monkeypatch.setitem(runner._fork, "forked", True)
    with pytest.raises(RuntimeError, match="forked"):
        runner.run(["-c", "pass"])
    with pytest.raises(RuntimeError, match="forked"):
        asyncio.run(runner.run_async(["-c", "pass"]))


def test_a_host_function_returning_under_a_set_event_stops_the_guest(monkeypatch) -> None:
    """A wait the cancel ended, or a door call made after it, sets the store's epoch deadline to
    0, so the guest meets the callback at its next entry instead of finishing (spec 015's
    landing notes; its build review, F4)."""
    holder = ctypes.c_int(0)
    caller = SimpleNamespace(_context=lambda: ctypes.pointer(holder))
    now = []
    monkeypatch.setattr(runner, "_epoch_now", lambda c: now.append(c))
    monkeypatch.setattr(runner, "_ctrl_c_watched", lambda: False)
    event = threading.Event()
    call = SimpleNamespace(  # `ended` as every `_Call` has it; the entry guard reads it (spec 030)
        context=ctypes.addressof(holder),
        stopped=None,
        ended=None,
        cancel=event,
        poll=lambda c, *a: 0,
    )
    function = runner._shared("poll", -1, -2)
    stack = runner._stack()
    stack.append(call)
    try:
        assert function(caller, 1, 2, 3, 4) == 0 and now == []
        event.set()
        assert function(caller, 1, 2, 3, 4) == 0 and now == [caller]
        call.cancel = None  # a call without `cancel` is unchanged
        assert function(caller, 1, 2, 3, 4) == 0 and now == [caller]
    finally:
        stack.remove(call)


def test_a_call_cancelled_before_it_runs_never_starts_its_guest(monkeypatch) -> None:
    """Spec 015, Decision 1: `run` checks the event once more just before it instantiates."""
    # Stand-ins, not wasmtime: no engine need exist, so spec 071's guard is set aside (spec 080).
    monkeypatch.setattr(runner, "_trap_handlers_ready", lambda: None)

    class Linker:
        def instantiate(self, store, module):
            raise AssertionError("the guest must not start")

    wt = SimpleNamespace(ExitTrap=Exception, Trap=Exception, WasmtimeError=Exception)
    event = threading.Event()
    event.set()
    call = SimpleNamespace(cancel=event, stopped=None, ended=None)
    done = runner._drive(wt, Linker(), None, None, call, 10)
    assert (done.exit_code, done.trapped, done.metered) == (None, "cancelled", False)
    assert call.ended == "cancelled"


def test_the_stop_error_is_real_and_never_leaves_a_zero_delta(monkeypatch) -> None:
    """Spec 015's build review, F2: an error wasmtime can own, or, when none can be made, a
    continue by one tick, never by 0."""
    from wasmtime import _ffi

    delta = (ctypes.c_uint64 * 1)()
    address = runner._stop_error(delta)
    assert address and delta[0] == 0
    _ffi.wasmtime_error_delete(ctypes.cast(address, ctypes.POINTER(_ffi.wasmtime_error_t)))

    def broken(message):
        raise MemoryError

    monkeypatch.setattr(_ffi, "wasmtime_error_new", broken)
    assert runner._stop_error(delta) == 0 and delta[0] == 1
    delta[0] = 0
    monkeypatch.setattr(
        _ffi, "wasmtime_error_new", lambda m: ctypes.POINTER(_ffi.wasmtime_error_t)()
    )
    assert runner._stop_error(delta) == 0 and delta[0] == 1
