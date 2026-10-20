"""A cancel during a door call is named (spec 030): the shared host function's except branch and
its entry guard, with a fake call and a fake caller. No artifacts; nothing here measures time."""

from __future__ import annotations

import pytest
import wasmtime

from wasi_python import _call, _home, _wasmtime_ffi
from wasi_python._process import process

REFUSED, STOPPED, ANSWER = 11, 22, 0
CONTEXT = 4242  # the fake caller's store context address


class FakeCall:
    """A call as `_shared` sees it. Its door may end the call as the epoch callback does inside
    host_alloc (`ends`, set while the door runs) and then raise; `stop` records the first cause
    as `_Call.stop` does; the deadline half of a stop is the patched `_epoch_now`, which the
    fixture counts."""

    def __init__(self, raises: BaseException | None = None, ends: str | None = None) -> None:
        self.context = CONTEXT
        self.stopped: BaseException | None = None
        self.ended: str | None = None
        self.cancel = None
        self.raises, self.ends = raises, ends
        self.served = 0
        self.stops: list[BaseException] = []

    def door(self, caller: object, *args: int) -> int:
        self.served += 1
        if self.ends is not None:
            self.ended = self.ends  # the callback, run in host_alloc, ended the call
        if self.raises is not None:
            raise self.raises
        return ANSWER

    def stop(self, caller: object, cause: BaseException) -> None:
        self.stops.append(cause)
        if self.stopped is None:
            self.stopped = cause


@pytest.fixture
def shared(monkeypatch):
    """The shared door function, with this thread's stack, the caller's context and the epoch
    deadline faked; yields a function that pushes a call, runs one door call and pops it."""
    deadlines: list[object] = []
    monkeypatch.setattr(_wasmtime_ffi, "context_address", lambda caller: CONTEXT)
    monkeypatch.setattr(_call, "_epoch_now", lambda caller: deadlines.append(caller))
    monkeypatch.setattr(_home, "_ctrl_c_watched", lambda: False)
    function = _call._shared("door", REFUSED, STOPPED)
    caller = object()

    def serve(call: FakeCall) -> int:
        stack = _home._stack()
        stack.append(call)
        try:
            return function(caller, 1, 2, 3, 4)
        finally:
            stack.remove(call)

    serve.deadlines = deadlines  # type: ignore[attr-defined]
    serve.caller = caller  # type: ignore[attr-defined]
    return serve


@pytest.mark.parametrize("error", [wasmtime.WasmtimeError("x"), wasmtime.Trap("y")])
def test_the_callbacks_own_error_is_not_a_stop(shared, error) -> None:
    """With `ended` set, the epoch callback's error surfacing through host_alloc is not recorded:
    the run is named from `ended`; the deadline is set to 0, so the guest stops at its next
    function entry by the runner's own act (Decisions 1 and 3)."""
    call = FakeCall(raises=error, ends="cancelled")
    assert shared(call) == STOPPED
    assert call.stopped is None
    assert call.stops == []
    assert shared.deadlines == [shared.caller]


def test_ctrl_c_after_the_callback_ended_the_call_is_recorded(shared) -> None:
    """Only a wasmtime error is the callback's: a KeyboardInterrupt is recorded as before."""
    cause = KeyboardInterrupt()
    call = FakeCall(raises=cause, ends="cancelled")
    assert shared(call) == STOPPED
    assert call.stopped is cause


def test_a_wasmtime_error_before_the_call_ended_is_recorded(shared) -> None:
    """With `ended` unset, a trap or exit inside host_alloc is the call's stop, as before (spec
    011)."""
    cause = wasmtime.WasmtimeError("x")
    call = FakeCall(raises=cause)
    assert shared(call) == STOPPED
    assert call.stopped is cause


def test_an_ended_call_is_not_served(shared) -> None:
    """With `ended` set, the entry returns `stopped` and the host function is not called
    (Decision 2)."""
    call = FakeCall()
    call.ended = "deadline"
    assert shared(call) == STOPPED
    assert call.served == 0
    assert call.stopped is None


def test_a_ctrl_c_pending_at_an_ended_call_is_recorded(shared, monkeypatch) -> None:
    """The entry guard sits after the Ctrl-C check (spec 015's order; the pre-build review's
    third builder note): a call with `ended` set and a Ctrl-C pending records KeyboardInterrupt
    and is not served (spec 030's build review, finding 3)."""
    monkeypatch.setattr(_home, "_ctrl_c_watched", lambda: True)
    monkeypatch.setattr(process(), "ctrl_c_pending", True)
    call = FakeCall()
    call.ended = "cancelled"
    assert shared(call) == STOPPED
    assert isinstance(call.stopped, KeyboardInterrupt)
    assert call.served == 0
    assert process().ctrl_c_pending is False


def test_a_live_call_is_served(shared) -> None:
    """The control: with neither `stopped` nor `ended` set, the host function answers."""
    call = FakeCall()
    assert shared(call) == ANSWER
    assert call.served == 1
