"""A cancel during a door call is named: the shared host function's except branch and
its entry guard, with a fake call and a fake caller; and one call on the artifact set, a deadline
reached while the guest writes, leaves no thread behind. Nothing here measures time; the
deadline is a limit the guest reaches, not a timing."""

from __future__ import annotations

import threading

import pytest
import wasmtime

from harness import needs
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
    """With `ended` unset, a trap or exit inside host_alloc is the call's stop, as before."""
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
    """The entry guard sits after the Ctrl-C check:
    a call with `ended` set and a Ctrl-C pending records KeyboardInterrupt
    and is not served."""
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


def test_a_deadline_under_output_leaves_no_thread() -> None:
    """A guest that writes for ever under a 0.2 s deadline and a 4 KiB cap is stopped by the
    deadline with stdout named, and the call leaves no thread that was not there after a
    warm-up call. The deadline also covers start-up, which a loaded host can take past it: the
    door, called after the first write, tells whether the writes ran, and only then are the
    4 KiB and the name required."""
    needs.need("runner", "artifact dir")
    import wasi_python

    wasi_python.run(["-c", "pass"])  # the epoch ticker's thread, which stays
    reached: list[int] = []
    code = (
        "import os, _host\nos.write(1, b'x' * 8192)\n_host.call(b'w')\n"
        "while True:\n    os.write(1, b'x' * 65536)\n"
    )
    before = set(threading.enumerate())
    done = wasi_python.run(
        ["-c", code],
        host=lambda frame: reached.append(1) or b"",
        deadline_s=0.2,
        output_bytes=4096,
    )
    after = set(threading.enumerate())
    assert done.trapped == "deadline", done.trapped
    if reached:
        assert (done.stdout, done.truncated) == (b"x" * 4096, ("stdout",)), done.truncated
    assert [t.name for t in after - before] == []
