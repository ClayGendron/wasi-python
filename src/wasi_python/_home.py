"""The threads of a call (spec 078): the per-thread stack of calls, Ctrl-C on the main thread
(spec 015), and the home and guest threads a call runs on."""

from __future__ import annotations

import contextvars
import queue
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from . import _platform
from ._engines import _epoch_ticker
from ._limits import CANCEL_TICKS, TICK_S
from ._platform import _HOST_ROOM, _THREAD_STACK, _WASM_STACK

if TYPE_CHECKING:
    from ._call import _Call


_calls = threading.local()


def _stack() -> list[_Call]:
    stack = getattr(_calls, "stack", None)
    if stack is None:
        stack = _calls.stack = []
    return stack


# Ctrl-C while a guest runs on the main thread. Python's default handler raises KeyboardInterrupt
# wherever the main thread next runs Python, and when that is the first line of wasmtime-py's
# trampoline the exception cannot be caught and the process aborts (spec 011's review, EXECUTED:
# exit 134). So while run() holds the main thread under the default handler, Ctrl-C only sets a
# flag: the shared host functions turn it into a recorded stop, a wait ends at it, and a flag no
# host function saw is raised once the call has ended.
_ctrl_c = {"pending": False}


def _note_ctrl_c(signum: int, frame: Any) -> None:
    _ctrl_c["pending"] = True


def _ctrl_c_watched() -> bool:
    """Whether a Ctrl-C on the main thread is deferred for the call this thread serves: on the main
    thread, whether `_deferred_ctrl_c` holds it; on a guest thread, what its home answered when the
    entry began (spec 078, Decision 5)."""
    import signal

    if threading.current_thread() is threading.main_thread():
        return signal.getsignal(signal.SIGINT) is _note_ctrl_c
    return bool(getattr(_calls, "watched", False))


@contextmanager
def _deferred_ctrl_c() -> Iterator[None]:
    import signal

    main = threading.current_thread() is threading.main_thread()
    if not main or signal.getsignal(signal.SIGINT) is not signal.default_int_handler:
        yield  # another thread, an embedder's own handler, or a nested call: nothing to defer
        return
    _ctrl_c["pending"] = False
    signal.signal(signal.SIGINT, _note_ctrl_c)
    try:
        yield
    finally:
        if signal.getsignal(signal.SIGINT) is _note_ctrl_c:  # a host may have set its own
            signal.signal(signal.SIGINT, signal.default_int_handler)
        pending, _ctrl_c["pending"] = _ctrl_c["pending"], False
    if pending:
        raise KeyboardInterrupt


_GUEST_SLICE = CANCEL_TICKS * TICK_S  # how often a waiting thread looks up (Decisions 14, 15)
_stack_size_lock = threading.Lock()
_stack_size_found: list[int] = []  # the value threading.stack_size had, while the window is open
# Test hook: told each entry's kind ("run", "open", "turn", "shutdown"), on its guest thread, once
# its stack is checked and before any wasm (spec 078, criterion 1).
_on_entry: Callable[[str], None] | None = None


class _Stopped(BaseException):
    """The guest thread's stop when its home has stopped (an exception raised into the home, or a
    home that left): it stops the call as a host function's BaseException does (Decision 15)."""


class _ThreadTooSmall(RuntimeError):
    pass


_DONE = object()


class _Box:
    """One hand-off: a function and its arguments, run on the home thread; the guest thread waits
    on `lock`, which `answer` releases once."""

    __slots__ = ("fn", "args", "lock", "value", "error", "answered")

    def __init__(self, fn: Callable[..., Any], args: tuple[Any, ...]) -> None:
        self.fn, self.args = fn, args
        self.lock = threading.Lock()
        self.lock.acquire()
        self.value: Any = None
        self.error: BaseException | None = None
        self.answered = False

    def answer(self, value: Any = None, error: BaseException | None = None) -> None:
        if not self.answered:
            self.value, self.error, self.answered = value, error, True
            self.lock.release()

    def run(self) -> None:
        try:
            value = self.fn(*self.args)
        except BaseException as e:  # the embedder's own, met on the guest thread as today
            self.answer(error=e)
        else:
            self.answer(value)


class _Home:
    """The thread that made a call (spec 078, Decision 2): it waits while the call's guest thread
    runs, serves the embedder's code the guest thread hands it (Decision 4), and keeps the
    teardown of what the guest uses until the guest thread has ended (Decision 14)."""

    def __init__(self) -> None:
        self.ident = threading.get_ident()
        self.inbox: queue.SimpleQueue[Any] = queue.SimpleQueue()
        self.lock = threading.Lock()
        self.serving = False
        self.raised: BaseException | None = None
        self.watched = False  # this thread's _ctrl_c_watched(), for its guest thread (Decision 5)
        self.thread: threading.Thread | None = None
        # The start handshake (the build review's F1), under `lock`: "idle", "starting" (asked of
        # the OS), "running" (the guest body took it), "cancelled" (the start failed before the
        # body took it: the body, if the OS made the thread anyway, returns at once).
        self.state = "idle"
        self.done = True  # no guest thread is running
        self.ended = threading.Event()  # set by the guest body at its end, or by a cancelled start
        self.ended.set()
        self.abandoned = False
        self.steps: list[Callable[[], Any]] = []
        self.result: tuple[Any, BaseException | None] = (None, None)

    def stop(self, error: BaseException) -> None:
        """Keep the first exception raised into the home; the epoch callback, the runner's waits
        and any hand-off then stop the guest."""
        if self.raised is None:
            self.raised = error

    def stopped(self) -> bool:
        return self.raised is not None

    def call(self, fn: Callable[..., Any], *args: Any) -> Any:
        """fn(*args) on the home thread: directly when already there, else handed home and waited
        for in slices, until it is answered, the home has an exception, or it stops serving."""
        if threading.get_ident() == self.ident:
            return fn(*args)
        if self.raised is not None:  # the call has stopped: no more embedder code (F7)
            raise _Stopped()
        box = _Box(fn, args)
        self.inbox.put(box)
        while not box.lock.acquire(timeout=_GUEST_SLICE):
            if self.raised is not None or not self.serving:
                raise _Stopped()
        if box.error is not None:
            raise box.error
        return box.value

    def serve(self) -> None:
        """Run what the guest thread hands home until it is done. An exception raised into this
        loop is kept as the call's stop, and the hand-off in flight is answered with a stop."""
        self.serving = True
        item: Any = None
        try:
            while True:
                try:
                    item = None
                    item = self.inbox.get(timeout=_GUEST_SLICE)
                    if item is _DONE:
                        return
                    if self.raised is not None:  # stopped: answered, never run (F7)
                        item.answer(error=_Stopped())
                    else:
                        item.run()
                    item = None
                except queue.Empty:
                    continue
                except BaseException as e:
                    self.stop(e)
                    if item is _DONE:
                        return
                    if item is not None:
                        item.answer(error=_Stopped())
        finally:
            self.serving = False

    def finish(self, step: Callable[[], Any]) -> bool:
        """Run `step` now if no guest thread runs, and say so; else leave it to the guest thread,
        which runs it at its end, and stop the guest (an abandoned home is a stopped one)."""
        with self.lock:
            if not self.done:
                self.abandoned = True
                self.steps.append(step)
                self.stop(_Stopped())
                return False
        step()
        return True

    def body(self, kind: str, fn: Callable[..., Any], args: tuple[Any, ...]) -> None:
        """The guest thread: check its stack, tell the interpreter where it guesses, run fn; then
        hand the result home and run the steps an abandoned home left."""
        with self.lock:  # the start handshake (the build review's F1)
            if self.state == "cancelled":
                return  # its start failed: no wasm, nothing to tear down, nobody waiting
            self.state = "running"
        value: Any = None
        error: BaseException | None = None
        try:
            try:
                bounds = _platform._guest_stack()
                if bounds is None or bounds[1] < _WASM_STACK + _HOST_ROOM // 2:
                    have = "unreadable" if bounds is None else f"{bounds[1]:,} bytes"
                    raise _ThreadTooSmall(
                        f"the guest's thread has {have} of stack, less than the "
                        f"{(_WASM_STACK + _HOST_ROOM // 2) >> 20} MiB its {_WASM_STACK >> 20} MiB "
                        "wasm stack needs (did other code change threading.stack_size while the "
                        "runner started it?); the call was refused"
                    )
                _platform._tell_interpreter(*bounds)
                _calls.watched = self.watched
                if _on_entry is not None:
                    _on_entry(kind)
                # The ticker runs while any guest thread runs, so its epoch checks go on even if
                # its home has been forced out (spec 078, Decision 14).
                with _epoch_ticker(None, True):
                    value = fn(*args)
            except BaseException as e:
                error = e
        finally:
            self.result = (value, error)
            self.inbox.put(_DONE)
            with self.lock:
                self.done = True
                self.state = "idle"
                steps, self.steps = (self.steps, []) if self.abandoned else ([], self.steps)
            for step in steps:
                try:
                    step()
                except BaseException:
                    pass
            self.ended.set()


def _start_guest(home: _Home, kind: str, fn: Callable[..., Any], args: tuple[Any, ...]) -> None:
    """Start a guest thread with _THREAD_STACK bytes, restoring threading.stack_size without
    erasing a value another thread set inside the window (Decision 2, the review's F6)."""
    context = contextvars.copy_context()
    thread = threading.Thread(
        target=context.run, args=(home.body, kind, fn, args), name="wasi-python-guest"
    )
    with _stack_size_lock:
        old = threading.stack_size(_THREAD_STACK)
        _stack_size_found[:] = [old]
        try:
            try:
                with home.lock:  # the start handshake (the build review's F1)
                    home.state, home.done, home.thread = "starting", False, thread
                    home.serving = True  # before the guest can hand anything off (F7)
                    home.ended.clear()
                thread.start()
            except BaseException:
                # Raised before the OS made the thread, or after it did (an interrupt in start()'s
                # own wait): only a start the body has not taken is cancelled; a running guest is
                # kept, so the home waits for it and nothing is torn down under it.
                with home.lock:
                    if home.state == "starting":
                        home.state, home.done, home.serving = "cancelled", True, False
                        home.ended.set()
                raise
        finally:
            current = threading.stack_size(old)
            if current != _THREAD_STACK:
                threading.stack_size(current)  # another thread's, set inside the window
            _stack_size_found.clear()


def _join_guest(home: _Home) -> None:
    """Wait until the guest body has ended (its event, which a cancelled start also sets); an
    exception raised meanwhile stops the guest and the wait goes on (Decision 14; the build
    review's F1: never `thread.is_alive()` alone, which a forgotten thread would not answer)."""
    while True:
        try:
            if home.ended.wait(_GUEST_SLICE):
                return
            thread = home.thread
            if thread is None or not thread.is_alive():
                # A backstop (the delta review's D3): a thread that never ran its body, or whose
                # body ended without saying so (a second exception in the start's own handler, an
                # embedder's trace hook raising at its first frame), would never set `ended`. Under
                # the lock, a body not yet running is cancelled: it returns at once if it starts.
                with home.lock:
                    if not home.ended.is_set():
                        home.state, home.done, home.serving = "cancelled", True, False
                        home.ended.set()
                return
        except BaseException as e:
            home.stop(e)


def _on_guest_thread(kind: str, home: _Home, call: Any, fn: Callable[..., Any], *args: Any) -> Any:
    """fn(*args) on a guest thread of its own, this thread serving it as its home; returns or
    raises only once that thread has ended (spec 078, Decisions 2, 14 and 15). `call` is pushed on
    this thread's stack meanwhile, so a host function finds it as before (Decision 16)."""
    stack = _stack()
    if call is not None:
        stack.append(call)
    try:
        value: Any = None
        error: BaseException | None = None
        for attempt in (0, 1):
            home.raised = None
            home.watched = _ctrl_c_watched()
            try:
                _start_guest(home, kind, fn, args)
                home.serve()
            except BaseException as e:
                home.stop(e)
                raise
            finally:
                _join_guest(home)
                home.serving = False
            value, error = home.result
            home.result = (None, None)
            if not (attempt == 0 and isinstance(error, _ThreadTooSmall) and home.raised is None):
                break
    finally:
        if call is not None and stack and stack[-1] is call:
            stack.pop()
    if home.raised is not None:
        raise home.raised
    if error is not None:
        raise error
    return value
