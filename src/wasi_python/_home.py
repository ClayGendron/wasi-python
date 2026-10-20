"""The threads of a call: the per-thread stack of calls, Ctrl-C on the main thread, and the
home and guest threads a call runs on."""

from __future__ import annotations

import contextvars
import enum
import queue
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from . import _platform
from ._engines import _epoch_ticker
from ._limits import CANCEL_TICKS, TICK_S
from ._platform import _HOST_ROOM, _THREAD_STACK, _WASM_STACK
from ._process import process

if TYPE_CHECKING:
    from ._call import _Call


def _stack() -> list[_Call]:
    calls = process().calls
    stack = getattr(calls, "stack", None)
    if stack is None:
        stack = calls.stack = []
    return stack


# Ctrl-C while a guest runs on the main thread. Python's default handler raises KeyboardInterrupt
# wherever the main thread next runs Python, and when that is the first line of wasmtime-py's
# trampoline the exception cannot be caught and the process aborts (spec 011's review, EXECUTED:
# exit 134). So while run() holds the main thread under the default handler, Ctrl-C only sets a
# flag: the shared host functions turn it into a recorded stop, a wait ends at it, and a flag no
# host function saw is raised once the call has ended. The flag is `process().ctrl_c_pending`.


def _note_ctrl_c(signum: int, frame: Any) -> None:
    process().ctrl_c_pending = True


def _ctrl_c_watched() -> bool:
    """Whether a Ctrl-C on the main thread is deferred for the call this thread serves: on the main
    thread, whether `_deferred_ctrl_c` holds it; on a guest thread, what its home answered when the
    entry began (spec 078, Decision 5)."""
    import signal

    if threading.current_thread() is threading.main_thread():
        return signal.getsignal(signal.SIGINT) is _note_ctrl_c
    return bool(getattr(process().calls, "watched", False))


@contextmanager
def _deferred_ctrl_c() -> Iterator[None]:
    import signal

    main = threading.current_thread() is threading.main_thread()
    if not main or signal.getsignal(signal.SIGINT) is not signal.default_int_handler:
        yield  # another thread, an embedder's own handler, or a nested call: nothing to defer
        return
    p = process()
    p.ctrl_c_pending = False
    signal.signal(signal.SIGINT, _note_ctrl_c)
    try:
        yield
    finally:
        if signal.getsignal(signal.SIGINT) is _note_ctrl_c:  # a host may have set its own
            signal.signal(signal.SIGINT, signal.default_int_handler)
        pending, p.ctrl_c_pending = p.ctrl_c_pending, False
    if pending:
        raise KeyboardInterrupt


_GUEST_SLICE = CANCEL_TICKS * TICK_S  # how often a waiting thread looks up (Decisions 14, 15)


class _Stopped(BaseException):
    """The guest thread's stop when its home has stopped (an exception raised into the home, or a
    home that left): it stops the call as a host function's BaseException does (Decision 15)."""


class _ThreadTooSmall(RuntimeError):
    pass


class _Done:
    """The guest thread's last word in the inbox: its body has ended."""


_DONE = _Done()


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


class _HomePhase(enum.Enum):
    """Where a home is in its guest thread's life: never started or its body ended (`IDLE`,
    `DONE`); a start asked of the OS that the body has not taken (`STARTING`); the body running
    (`RUNNING`); the home forced out while a guest thread may still run, its teardown left to
    that thread (`ABANDONED`); a start that failed before the body took it (`CANCELLED`)."""

    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    ABANDONED = "abandoned"
    CANCELLED = "cancelled"
    DONE = "done"


class _HomeEvent(enum.Enum):
    START = "start"  # a start asked of the OS
    TAKE = "take"  # the body's first line
    CANCEL = "cancel"  # the start failed before the body took it
    LEAVE = "leave"  # the home is forced out: a step left for the guest thread
    END = "end"  # the body's last line
    LOST = "lost"  # the thread is dead and its body never reported


_HOME_TABLE = {
    (_HomePhase.IDLE, _HomeEvent.START): _HomePhase.STARTING,
    (_HomePhase.DONE, _HomeEvent.START): _HomePhase.STARTING,  # the one retry after a small stack
    (_HomePhase.STARTING, _HomeEvent.TAKE): _HomePhase.RUNNING,
    (_HomePhase.STARTING, _HomeEvent.CANCEL): _HomePhase.CANCELLED,
    (_HomePhase.STARTING, _HomeEvent.LEAVE): _HomePhase.ABANDONED,
    (_HomePhase.RUNNING, _HomeEvent.LEAVE): _HomePhase.ABANDONED,
    (_HomePhase.ABANDONED, _HomeEvent.TAKE): _HomePhase.ABANDONED,  # it runs, then the steps
    (_HomePhase.ABANDONED, _HomeEvent.LEAVE): _HomePhase.ABANDONED,  # a second step
    (_HomePhase.CANCELLED, _HomeEvent.TAKE): _HomePhase.CANCELLED,  # a late body: returns at once
    (_HomePhase.RUNNING, _HomeEvent.END): _HomePhase.DONE,
    (_HomePhase.ABANDONED, _HomeEvent.END): _HomePhase.DONE,  # the steps go to the guest thread
    (_HomePhase.RUNNING, _HomeEvent.LOST): _HomePhase.DONE,
    (_HomePhase.ABANDONED, _HomeEvent.LOST): _HomePhase.DONE,  # the steps stay: nothing runs them
}
# Every other pair is refused; `START` from `CANCELLED` among them, since a late body of the
# cancelled start could take the new start as its own.

_SERVING = (_HomePhase.STARTING, _HomePhase.RUNNING)  # a guest thread may hand work home
_GUEST_MAY_RUN = (*_SERVING, _HomePhase.ABANDONED)  # a guest thread may still be running
_NO_GUEST = (_HomePhase.IDLE, _HomePhase.CANCELLED, _HomePhase.DONE)  # no guest thread runs


class _Home:
    """The thread that made a call (spec 078, Decision 2): it waits while the call's guest thread
    runs, serves the embedder's code the guest thread hands it (Decision 4), and keeps the
    teardown of what the guest uses until the guest thread has ended (Decision 14).

    What `lock` protects:

    1. `phase` is written under the lock only, through `_move`, which refuses a pair the table
       does not hold with a `RuntimeError` naming both.
    2. `ended.is_set()` only in `IDLE`, `CANCELLED` and `DONE`; `START` clears it in the same
       lock hold; `CANCEL` and `LOST` set it after theirs, and `END` sets it after the steps have
       run, so `DONE` precedes `ended.is_set()` by the steps' run (the join waits on `ended`).
    3. `thread` is the guest thread from `START` until the next `START`; `None` before the first.
    4. `steps` grows only in `ABANDONED`; `END` from `ABANDONED` empties it into the guest
       thread's hands; `LOST` from `ABANDONED` keeps them in `DONE`: the thread is dead and
       nothing can run them.
    5. `raised` is set in `ABANDONED` (`finish` stops the guest with a `_Stopped` at least).
    6. A guest thread may hand work home in `STARTING` and `RUNNING`; no guest thread runs in
       `IDLE`, `CANCELLED` and `DONE` (`done`).
    """

    def __init__(self) -> None:
        self.ident = threading.get_ident()
        self.inbox: queue.SimpleQueue[_Box | _Done] = queue.SimpleQueue()
        self.lock = threading.Lock()
        self.raised: BaseException | None = None
        self.watched = False  # this thread's _ctrl_c_watched(), for its guest thread (Decision 5)
        self.thread: threading.Thread | None = None
        self.phase = _HomePhase.IDLE
        self.ended = threading.Event()  # set by the guest body at its end, or by a cancelled start
        self.ended.set()
        self.steps: list[Callable[[], Any]] = []
        self.result: tuple[Any, BaseException | None] = (None, None)

    @property
    def done(self) -> bool:
        """No guest thread is running: nothing is torn down under one."""
        return self.phase in _NO_GUEST

    def _move(self, event: _HomeEvent) -> _HomePhase:
        """Under `lock`: the phase after `event`, by the table; a pair not in it is a
        `RuntimeError` naming both."""
        after = _HOME_TABLE.get((self.phase, event))
        if after is None:
            raise RuntimeError(f"a home in {self.phase.name} cannot take {event.name}")
        self.phase = after
        return after

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
            if self.raised is not None or self.phase not in _SERVING:
                raise _Stopped()
        if box.error is not None:
            raise box.error
        return box.value

    def serve(self) -> None:
        """Run what the guest thread hands home until it is done. An exception raised into this
        loop is kept as the call's stop, and the hand-off in flight is answered with a stop."""
        item: _Box | _Done | None = None
        while True:
            try:
                item = None
                item = self.inbox.get(timeout=_GUEST_SLICE)
                if isinstance(item, _Done):  # the guest thread has ended
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
                if isinstance(item, _Done):
                    return
                if item is not None:
                    item.answer(error=_Stopped())

    def finish(self, step: Callable[[], Any]) -> bool:
        """Run `step` now if no guest thread runs, and say so; else leave it to the guest thread,
        which runs it at its end, and stop the guest (an abandoned home is a stopped one)."""
        with self.lock:
            if self.phase in _GUEST_MAY_RUN:
                self._move(_HomeEvent.LEAVE)
                self.steps.append(step)
                self.stop(_Stopped())
                return False
        step()
        return True

    def body(self, kind: str, fn: Callable[..., Any], args: tuple[Any, ...]) -> None:
        """The guest thread: check its stack, tell the interpreter where it guesses, run fn; then
        hand the result home and run the steps an abandoned home left."""
        with self.lock:  # the start handshake (the build review's F1)
            if self._move(_HomeEvent.TAKE) is _HomePhase.CANCELLED:
                return  # its start failed: no wasm, nothing to tear down, nobody waiting
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
                p = process()
                p.calls.watched = self.watched
                on_entry = p.observers.on_entry
                if on_entry is not None:
                    on_entry(kind)
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
                abandoned = self.phase is _HomePhase.ABANDONED
                self._move(_HomeEvent.END)
                steps, self.steps = (self.steps, []) if abandoned else ([], self.steps)
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
    p = process()
    with p.stack_size_lock:
        old = threading.stack_size(_THREAD_STACK)
        p.stack_size_found[:] = [old]
        try:
            try:
                with home.lock:  # the start handshake (the build review's F1)
                    home._move(_HomeEvent.START)  # serving, before the guest can hand off (F7)
                    home.thread = thread
                    home.ended.clear()
                thread.start()
            except BaseException:
                # Raised before the OS made the thread, or after it did (an interrupt in start()'s
                # own wait): only a start the body has not taken is cancelled; a running guest is
                # kept, so the home waits for it and nothing is torn down under it.
                with home.lock:
                    if home.phase is _HomePhase.STARTING:
                        home._move(_HomeEvent.CANCEL)
                        home.ended.set()
                raise
        finally:
            current = threading.stack_size(old)
            if current != _THREAD_STACK:
                threading.stack_size(current)  # another thread's, set inside the window
            p.stack_size_found.clear()


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
                        cancel = home.phase is _HomePhase.STARTING  # a body never taken
                        home._move(_HomeEvent.CANCEL if cancel else _HomeEvent.LOST)
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
