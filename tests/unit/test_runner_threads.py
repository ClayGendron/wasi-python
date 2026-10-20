"""The guest's own thread (spec 078): the stack it is given and checked against, the interpreter
told its stack where it guesses, the home thread that waits and serves, and a teardown that never
runs under a live guest. Stand-ins only: no wasm runs here. Nothing here measures time; a wait is
a count of events, and the slices the runner waits in are its own."""

from __future__ import annotations

import ctypes
import queue
import threading

import pytest

from wasi_python import _call, _home, _platform, runner
from wasi_python._process import process

MIB = 1 << 20


@pytest.fixture
def roomy(monkeypatch):
    """A guest stack check that always passes, so a test of the home can run on any host."""
    monkeypatch.setattr(_platform.PLATFORM, "stack_bounds", lambda: (4096, 64 * MIB))
    monkeypatch.setattr(_platform.PLATFORM, "tell_interpreter", lambda bottom, size: False)


def test_the_guest_thread_is_sized_from_the_wasm_stack() -> None:
    """Spec 078, criterion 2 (its constants): 8 MiB for wasm, 2 MiB of host room."""
    assert _platform._WASM_STACK == 8 * MIB
    assert _platform._HOST_ROOM == 2 * MIB
    assert _platform._THREAD_STACK == _platform._WASM_STACK + 2 * MIB


def test_a_guest_thread_is_not_the_home_and_has_room() -> None:
    """Spec 078, criterion 1, in miniature: the function runs once, on another thread, whose real
    stack is at least the refusal line, and the home's value comes back."""
    seen = []
    home = _home._Home()

    def fn() -> int:
        seen.append((threading.get_ident(), _platform.PLATFORM.stack_bounds()))
        return 7

    assert _home._on_guest_thread("run", home, None, fn) == 7
    ((ident, bounds),) = seen
    assert ident != threading.get_ident()
    assert bounds is not None and bounds[1] >= _platform._WASM_STACK + _platform._HOST_ROOM // 2
    assert home.done and home.ended.is_set()


def test_a_small_guest_thread_is_refused_after_one_retry(monkeypatch) -> None:
    """Spec 078, criterion 3: a thread whose stack reads under 9 MiB, or cannot be read, is
    refused before anything runs on it, once more made, then refused with RuntimeError."""
    for answer in ((4096, 8 * MIB), None):
        reads: list[object] = []
        ran: list[int] = []
        entries: list[str] = []

        def read(a=answer, reads=reads):
            reads.append(a)
            return a

        def fn(ran=ran) -> None:
            ran.append(1)

        monkeypatch.setattr(_platform.PLATFORM, "stack_bounds", read)
        monkeypatch.setattr(process().observers, "on_entry", entries.append)
        with pytest.raises(RuntimeError, match="less than the 9 MiB"):
            _home._on_guest_thread("run", _home._Home(), None, fn)
        assert (len(reads), ran, entries) == (2, [], []), (answer, reads)


def test_the_stack_size_is_restored_without_erasing_another(monkeypatch, roomy) -> None:
    """Spec 078, criterion 3 (the review's F6): the runner sets the guest thread's size, then
    restores what it found; if another thread set a size inside the window, that one is put back;
    it never calls threading.stack_size() without an argument, which would set 0."""
    calls = []
    answers = iter([0, 4 * MIB, 0])  # found 0; at the restore, another thread had set 4 MiB

    def stack_size(*args):
        assert args, "threading.stack_size() without an argument sets the size to 0"
        calls.append(args[0])
        return next(answers)

    monkeypatch.setattr(runner.threading, "stack_size", stack_size)
    _home._on_guest_thread("run", _home._Home(), None, lambda: None)
    assert calls == [_platform._THREAD_STACK, 0, 4 * MIB]


def test_windows_counts_its_stack_conservatively() -> None:
    """Spec 078, criterion 3 (the review's F7): high - low - guarantee - one page."""
    low, high, guarantee = 0x10000, 0x10000 + 10 * MIB, 64 * 1024
    bottom, size = _platform._windows_usable(low, high, guarantee)
    assert size == 10 * MIB - guarantee - 4096 and bottom == low + guarantee + 4096
    assert _platform._windows_usable(low, low + 4096, 0) is None


def test_an_unknown_platform_cannot_be_read() -> None:
    """Spec 078, criterion 4 (the review's F13): FreeBSD's bounds are not read, so its calls are
    refused by the stack check."""
    assert _platform._Posix().stack_bounds() is None


def test_the_interpreter_is_told_its_stack_where_it_guesses() -> None:
    """Spec 078, criterion 4: on musl with CPython 3.14.1 the runner tells the interpreter the
    thread's bounds once; with 3.14.0 (no such function) it refuses; elsewhere it tells nothing."""
    told = []

    def resolve(name, restype, *argtypes):
        if name == "PyThreadState_Get":
            return lambda: 0xABC
        return lambda tstate, bottom, size: told.append((tstate, bottom, size)) or 0

    def missing(name, restype, *argtypes):
        if name == "PyUnstable_ThreadState_SetStackProtection":
            raise AttributeError(name)
        return lambda: 0xABC

    linux, musl = _platform._Linux(), dict(implementation="cpython", libc="musl")
    assert linux.tell_interpreter(4096, 9 * MIB, version=(3, 14, 1), resolve=resolve, **musl)
    assert told == [(0xABC, 4096, 9 * MIB)]
    with pytest.raises(RuntimeError, match="use CPython 3.14.1 or later"):
        linux.tell_interpreter(4096, 9 * MIB, version=(3, 14, 0), resolve=missing, **musl)
    for host, other in (
        (linux, dict(implementation="cpython", libc="glibc", version=(3, 14, 2))),
        (_platform._Posix(), dict(implementation="cpython", libc="", version=(3, 14, 2))),
        (_platform._Darwin(), dict(implementation="cpython", libc="", version=(3, 14, 2))),
        (_platform._Windows(), dict(implementation="cpython", libc="", version=(3, 14, 2))),
        (linux, dict(implementation="cpython", libc="musl", version=(3, 13, 9))),
    ):
        assert not host.tell_interpreter(4096, 9 * MIB, resolve=resolve, **other), (host, other)
    assert len(told) == 1


def test_the_interpreter_prototypes_are_private() -> None:
    """Spec 078, criterion 4 (the review's F5): resolving the C API functions sets no restype or
    argtypes on ctypes.pythonapi's shared attributes."""
    shared = ctypes.pythonapi.PyThreadState_Get
    before = (shared.restype, shared.argtypes)
    _platform._pyapi("PyThreadState_Get", ctypes.c_void_p)
    assert (shared.restype, shared.argtypes) == before
    with pytest.raises(AttributeError):
        _platform._pyapi("NoSuchFunction_078", ctypes.c_int)


def test_a_hand_off_runs_on_the_home_and_carries_its_exception(roomy) -> None:
    """Spec 078, Decision 4: the guest thread hands a function home; it runs on the home thread,
    and its value, or its exception, comes back to the guest thread unchanged."""
    home = _home._Home()

    def fn():
        where = home.call(threading.get_ident)
        try:
            home.call(lambda: 1 / 0)
        except ZeroDivisionError as e:
            return where, type(e).__name__

    assert _home._on_guest_thread("run", home, None, fn) == (
        threading.get_ident(),
        "ZeroDivisionError",
    )


def test_the_home_keeps_its_call_on_its_stack(roomy) -> None:
    """Spec 078, Decision 16: while it serves, the home has its call on its own stack, so a host
    function there finds it as before; it is popped after."""
    home, call = _home._Home(), object()
    found = _home._on_guest_thread("run", home, call, lambda: home.call(lambda: _home._stack()[-1]))
    assert found is call and call not in _home._stack()


class _OnceRaisingInbox:
    """An inbox whose get raises KeyboardInterrupt once, after it has taken a hand-off."""

    def __init__(self) -> None:
        self.inner, self.raised = queue.SimpleQueue(), False

    def put(self, item) -> None:
        self.inner.put(item)

    def get(self, timeout=None):
        item = self.inner.get(timeout=timeout)
        if isinstance(item, _home._Box) and not self.raised:
            self.raised = True
            raise KeyboardInterrupt
        return item


def test_an_interrupted_hand_off_is_answered(roomy) -> None:
    """Spec 078, criterion 18 (the review's F2): an interrupt landing just after the home took a
    hand-off, or after the host function returned and before its box was released, still answers
    the guest (with a stop), the call raises KeyboardInterrupt, and both threads end."""
    home = _home._Home()
    home.inbox = _OnceRaisingInbox()
    met = []

    def fn():
        try:
            home.call(lambda: "never seen")
        except BaseException as e:
            met.append(type(e))
            raise

    with pytest.raises(KeyboardInterrupt):
        _home._on_guest_thread("run", home, None, fn)
    assert met == [_home._Stopped] and home.ended.is_set()

    class LateBox(_home._Box):
        def run(self) -> None:
            self.fn(*self.args)
            raise KeyboardInterrupt  # after the call, before the answer

    home, met = _home._Home(), []
    original = _home._Box
    _home._Box = LateBox
    try:
        with pytest.raises(KeyboardInterrupt):
            _home._on_guest_thread("run", home, None, fn)
    finally:
        _home._Box = original
    assert met == [_home._Stopped] and home.ended.is_set()


def test_the_home_waits_for_its_guest_thread(monkeypatch, roomy) -> None:
    """Spec 078, criterion 17 (the review's F1): an exception raised into the home while the guest
    runs stops the guest, and the call returns only once the guest thread has ended."""
    home = _home._Home()
    ended = threading.Event()

    def serve(self) -> None:
        raise KeyboardInterrupt  # just after the guest thread started

    monkeypatch.setattr(_home._Home, "serve", serve)

    def fn() -> None:
        while home.raised is None:  # the epoch callback's part: stop once the home has raised
            ended.wait(0.001)
        ended.set()

    with pytest.raises(KeyboardInterrupt):
        _home._on_guest_thread("run", home, None, fn)
    assert ended.is_set() and home.ended.is_set() and home.done


def test_an_abandoned_home_leaves_its_teardown_to_the_guest(monkeypatch, roomy) -> None:
    """Spec 078, criterion 17 (the review's F1 and the confirmation's C2): a home forced out of its
    join leaves the teardown to the guest thread, which runs it once, after its work; finishing an
    abandoned home stops the guest."""
    home = _home._Home()
    release = threading.Event()
    order: list[str] = []

    def serve(self) -> None:
        raise KeyboardInterrupt  # raised into the home while the guest runs

    def forced_out(home_) -> None:
        raise SystemExit("forced out of the join")  # and again, inside its join

    monkeypatch.setattr(_home._Home, "serve", serve)
    monkeypatch.setattr(_home, "_join_guest", forced_out)

    def fn() -> None:
        release.wait()
        order.append("guest done")

    with pytest.raises(SystemExit):
        _home._on_guest_thread("run", home, None, fn)
    assert home.thread.is_alive()
    ran_on = []
    assert (
        home.finish(lambda: (order.append("teardown"), ran_on.append(threading.get_ident())))
        is False
    )
    assert home.raised is not None  # abandoned means stopped
    release.set()
    home.thread.join()
    assert order == ["guest done", "teardown"]
    assert ran_on == [home.thread.ident]
    assert home.finish(lambda: order.append("after")) is True and order[-1] == "after"


def test_a_tool_copies_the_homes_context() -> None:
    """Spec 078, Decision 4 (the review's F12): with a home, a tool call's context is copied on
    the home thread, through one hand-off."""
    import contextvars

    var = contextvars.ContextVar("v078")
    home = _home._Home()
    var.set("set on the home")
    copy = _call._home_context(home)()  # called on the home itself: directly
    assert copy[var] == "set on the home"
    assert _call._home_context(None) is contextvars.copy_context


def test_an_interrupted_thread_start_keeps_its_guest(monkeypatch, roomy) -> None:
    """Spec 078, criterion 17 (the build review's F1): an interrupt raised inside Thread.start()
    after the OS made the thread leaves the guest known to its home: the call raises only once the
    guest has ended, and a teardown waits for it."""
    home = _home._Home()
    ended = threading.Event()
    real_start = threading.Thread.start

    def start(self) -> None:
        real_start(self)
        raise KeyboardInterrupt  # as in start()'s own wait, after the thread was made

    monkeypatch.setattr(threading.Thread, "start", start)

    def fn() -> None:
        while home.raised is None:  # the epoch callback's part
            ended.wait(0.001)
        ended.set()

    with pytest.raises(KeyboardInterrupt):
        _home._on_guest_thread("run", home, None, fn)
    assert ended.is_set() and home.ended.is_set() and home.done
    ran = []
    assert home.finish(lambda: ran.append(1)) is True and ran == [1]


def test_a_failed_thread_start_is_cancelled(monkeypatch, roomy) -> None:
    """Spec 078, criterion 17 (the build review's F1): a start that fails before the body takes
    it is cancelled: the call raises, nothing ran, and a body the OS starts anyway returns at
    once."""
    home = _home._Home()
    ran: list[int] = []

    def start(self) -> None:
        raise RuntimeError("can't start new thread")

    monkeypatch.setattr(threading.Thread, "start", start)
    with pytest.raises(RuntimeError, match="can't start"):
        _home._on_guest_thread("run", home, None, lambda: ran.append(1))
    cancelled = _home._HomePhase.CANCELLED
    assert (ran, home.phase, home.done, home.ended.is_set()) == ([], cancelled, True, True)
    home.body("run", lambda: ran.append(2), ())  # a body that starts after its cancel
    assert ran == [] and home.phase is cancelled


def test_a_stopped_home_answers_new_hand_offs_with_a_stop(roomy) -> None:
    """Spec 078 (the build review's F7): once the home has an exception, a new hand-off is not
    posted, and one already posted is answered with a stop, never run."""
    home = _home._Home()
    home.stop(KeyboardInterrupt())
    home.ident = -1  # as seen from a guest thread
    with pytest.raises(_home._Stopped):
        home.call(lambda: pytest.fail("ran after the stop"))
    box = _home._Box(lambda: pytest.fail("ran after the stop"), ())
    home.inbox.put(box)
    home.inbox.put(_home._DONE)
    home.serve()
    assert box.answered and isinstance(box.error, _home._Stopped)


def test_the_join_does_not_wait_for_a_thread_that_never_ran() -> None:
    """Spec 078 (the delta review's D3): a start left "starting" by a thread that never ran its
    body (a second exception in the start's handler, a trace hook raising at its first frame) is
    cancelled by the join, which returns; a body that starts after it returns at once."""
    home = _home._Home()
    ran: list[int] = []
    never = threading.Thread(target=lambda: None)  # made, never started: no body will run
    with home.lock:
        home.phase, home.thread = _home._HomePhase.STARTING, never
        home.ended.clear()
    _home._join_guest(home)
    cancelled = _home._HomePhase.CANCELLED
    assert (home.phase, home.done, home.ended.is_set()) == (cancelled, True, True)
    home.body("run", lambda: ran.append(1), ())
    assert ran == []
