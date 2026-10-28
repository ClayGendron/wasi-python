"""Sessions: `SessionEnded`, the state of a session, the reaper, the endings and the shutdown,
the turns, and `_open_session`."""

from __future__ import annotations

import atexit
import contextvars
import enum
import functools
import math
import queue
import threading
import time
import types
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any, NamedTuple

from . import _artifacts, _call, _engines, _home, _outputs, _places, _platform, _private_dirs
from . import _snapshot as _snapshot  # its own line: the line above is full
from ._artifacts import GUEST_PACKAGE, Artifacts, ArtifactsMissing
from ._call import (
    ARGV0,
    MASK32,
    UNMETERED,
    Completed,
    Host,
    _Call,
    _CheckedCall,
    _Driven,
    _Waits,
)
from ._engines import _epoch_ticker
from ._fs_memory import STAGING_CEILING
from ._home import _Home
from ._limits import CANCEL_TICKS, NO_DEADLINE, TICK_S
from ._outputs import _Capture, _Stream
from ._places import _Preopen
from ._platform import _TRAP_HANDLERS_REPLACED, _Walked
from ._private_dirs import _Private
from ._process import process

if TYPE_CHECKING:
    import asyncio

    import wasmtime

    from ._fs_table import _Files
    from ._tool_host import _Bounded, _ToolHost, _ToolLoop

# ---------------------------------------------------------------------------------------------
# Sessions: one instance of the guest kept across turns, with an idle bound and a
# lifetime, ended by Python's own shutdown inside a small budget, as a Jupyter kernel is.

MAX_TURN_BYTES = 0x7FFFFFFF  # the `turn` export's length is an i32
SESSION_EXPORTS = ("turn", "shutdown")

# The clock the bounds read, and the hooks told of each arming, export and call, are the
# observers of the process: `process().observers`.


class SessionEnded(RuntimeError):
    """A session has ended, so it runs no more turns.

    Attributes:
        reason: Why it ended, the value of `Session.ended`: "closed", "idle", "lifetime",
            "quit", "exit" or "error", one of `Completed.trapped`'s four fixed strings, or
            wasmtime's words for a trap.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(f"the session has ended: {reason}")
        self.reason = reason


class _Either:
    """A stop that is set when either event is: a turn's `cancel`, or its session's closing; or
    when an exception was raised into the turn's home thread."""

    __slots__ = ("first", "second", "home")

    def __init__(
        self, first: threading.Event | None, second: threading.Event, home: _Home | None = None
    ) -> None:
        self.first, self.second, self.home = first, second, home

    def is_set(self) -> bool:
        if self.home is not None and self.home.raised is not None:
            return True
        return (self.first is not None and self.first.is_set()) or self.second.is_set()


class _Phase(enum.Enum):
    """Where a session is in its life."""

    OPENING = "opening"  # the store is being made; not yet registered: nothing can reach it
    OPEN = "open"  # at rest: a turn may be claimed, a bound may pass
    TURN = "turn"  # a turn is claimed, by the thread `holder` names
    STOPPING = "stopping"  # a turn runs and `ended` is set: it is being stopped
    MARKED = "marked"  # at rest, `ended` set, no one has claimed the ending
    ENDING = "ending"  # the ending is claimed, by `holder`: a thread, or `_CLOSER`
    ENDED = "ended"  # everything is released; terminal


class _Event(enum.Enum):
    OPENED = "opened"  # the store is made and the session registered
    CLAIM = "claim"  # a turn is claimed
    TAKE_TURN = "take turn"  # the thread that runs the claimed turn becomes its holder
    RELEASE = "release"  # a queued turn never started
    MARK = "mark"  # `ended` is set, by the first cause
    TURN_RETURNED = "turn returned"  # the turn's thread, or an abandoned turn's guest thread
    CLAIM_ENDING = "claim ending"  # someone will run the ending
    TAKE_OVER = "take over"  # a closer thread takes the claim made in its name
    RELEASED = "released"  # the store and folders are released


_SESSION_TABLE = {
    (_Phase.OPENING, _Event.OPENED): _Phase.OPEN,
    (_Phase.OPENING, _Event.RELEASED): _Phase.ENDED,  # a failed opening; nothing was counted
    (_Phase.OPEN, _Event.CLAIM): _Phase.TURN,
    (_Phase.OPEN, _Event.MARK): _Phase.MARKED,
    (_Phase.TURN, _Event.TAKE_TURN): _Phase.TURN,
    (_Phase.STOPPING, _Event.TAKE_TURN): _Phase.STOPPING,  # a close() came before the start
    (_Phase.TURN, _Event.RELEASE): _Phase.OPEN,
    (_Phase.TURN, _Event.MARK): _Phase.STOPPING,
    (_Phase.TURN, _Event.TURN_RETURNED): _Phase.OPEN,
    (_Phase.STOPPING, _Event.RELEASE): _Phase.MARKED,  # a queued turn cancelled after a close()
    (_Phase.STOPPING, _Event.TURN_RETURNED): _Phase.MARKED,
    (_Phase.MARKED, _Event.CLAIM_ENDING): _Phase.ENDING,
    (_Phase.ENDING, _Event.TAKE_OVER): _Phase.ENDING,
    (_Phase.ENDING, _Event.RELEASED): _Phase.ENDED,
}
# Every other pair is refused: a claim of the ending before a mark, and a move from OPENING by
# anything but OPENED or RELEASED, among them.
# Each of these events names the holder.
_HOLDER_EVENTS = (_Event.CLAIM, _Event.TAKE_TURN, _Event.CLAIM_ENDING, _Event.TAKE_OVER)
_STOPPED_PHASES = (_Phase.STOPPING, _Phase.MARKED)  # entered with `ended` set: `closing` too


def _move(state: _State, event: _Event, holder: int | None = None) -> _Phase:
    """Under `state.lock`: the phase after `event`, by the table; a pair not in it is a
    `RuntimeError` naming both. Sets `holder` (the claimant, kept through a mark, cleared by
    every other event), `closing` on entering STOPPING or MARKED and `done` on entering ENDED, so
    a wait handle can never disagree with the phase."""
    after = _SESSION_TABLE.get((state.phase, event))
    if after is None:
        raise RuntimeError(f"a session in {state.phase.name} cannot take {event.name}")
    state.phase = after
    if event in _HOLDER_EVENTS:
        state.holder = holder
    elif event is not _Event.MARK:
        state.holder = None
    if after in _STOPPED_PHASES:
        state.closing.set()
    elif after is _Phase.ENDED:
        state.done.set()
    return after


class _Guest(enum.Enum):
    """The interpreter inside a session's store, apart from the session's life."""

    UNTOUCHED = "untouched"  # no turn has called an export; `_initialize` is still to call
    ENTERED = "entered"  # a turn has called an export and has not yet reported
    SOUND = "sound"  # the last export returned: it may be entered for Python's shutdown
    UNSOUND = "unsound"  # the last export was unwound, or the turn raised, or was abandoned


class _GuestEvent(enum.Enum):
    ENTER = "enter"  # an export is called
    RETURNED = "returned"  # the export returned a status
    UNWOUND = "unwound"  # a trap, an exit or a stop unwound it
    FAILED = "failed"  # the turn raised in the embedder's process, or was abandoned


_GUEST_TABLE = {
    (_Guest.UNTOUCHED, _GuestEvent.ENTER): _Guest.ENTERED,
    (_Guest.SOUND, _GuestEvent.ENTER): _Guest.ENTERED,
    (_Guest.ENTERED, _GuestEvent.RETURNED): _Guest.SOUND,
    (_Guest.ENTERED, _GuestEvent.UNWOUND): _Guest.UNSOUND,
    (_Guest.UNTOUCHED, _GuestEvent.FAILED): _Guest.UNSOUND,
    (_Guest.ENTERED, _GuestEvent.FAILED): _Guest.UNSOUND,
    (_Guest.SOUND, _GuestEvent.FAILED): _Guest.UNSOUND,
}
# `ENTER` from `UNSOUND` is refused: an unsound guest always comes with `ended` set, so no turn
# follows. A turn cancelled before any guest code raises no event: the guest stays what it was.


def _move_guest(state: _State, event: _GuestEvent) -> _Guest:
    """The guest after `event`, by the table; a pair not in it is a `RuntimeError` naming both.
    `ENTER` is written on the turn's guest thread without the lock: the phase protects it (one
    turn at a time); the rest under `state.lock`."""
    after = _GUEST_TABLE.get((state.guest, event))
    if after is None:
        raise RuntimeError(f"a guest that is {state.guest.name} cannot take {event.name}")
    state.guest = after
    return after


class _State:
    """Everything a session holds: its store and folders, its limits, its phase and its guest.
    It never refers to its `Session`, so the collector can finalize a dropped one.

    What `lock` protects:

    1. `ended is None` exactly in `OPENING`, `OPEN` and `TURN`; `closing.is_set()` exactly when
       `ended is not None`.
    2. `holder` is the turn's thread in `TURN` and `STOPPING`, the ending's thread or `_CLOSER`
       in `ENDING`, and `None` otherwise. A turn and an ending are never held at once. The turn's
       thread is the one that claimed it until the turn starts, and the one that runs it from
       then on (`TAKE_TURN`): `run_async` claims on the event loop's thread and runs on a worker.
    3. In `ENDING` and `ENDED` no turn's guest thread lives: `STOPPING` leaves only when the
       turn's own thread, or the abandoned turn's guest thread at its end, says so.
    4. `done.is_set()` exactly in `ENDED`; `outcome` is written in the same lock hold that
       enters it.
    5. `guest is ENTERED` only in `TURN` or `STOPPING`; `guest is UNSOUND` only with `ended` set.
    6. The process's count of open sessions counts the states in `OPEN`, `TURN`, `STOPPING`,
       `MARKED` and `ENDING`; `_release_session` decrements once, in `ENDING`, never in
       `OPENING`.
    7. `phase`, `holder`, `ended` and `outcome` are written under the lock, through `_move` and
       `_mark`, with one exception: `close()` in a forked child writes `ended` and `outcome`
       lock-free and moves nothing (the store is the parent's; no thread of the child touches
       it).
    8. No session rests in `MARKED` while nobody holds it: every lock hold that enters `MARKED`
       claims the ending in the same hold, for its own thread or for `_CLOSER`, and a closer is
       started once the lock is released. A closer that cannot start runs the ending on the
       thread that started it, which then holds no lock.
    """

    def __init__(self, checked: _CheckedCall, wt: types.ModuleType) -> None:
        self.lock = threading.Lock()
        self.phase = _Phase.OPENING
        self.holder: int | None = None  # who holds the turn or the ending (invariant 2)
        self.ended: str | None = None  # why the session ended, by its first cause
        self.outcome: str | None = None  # how its ending went
        self.closing = threading.Event()  # set with `ended`: stops a running turn
        self.done = threading.Event()  # the ending has finished; everything is released
        self.guest = _Guest.UNTOUCHED
        self.opened = 0.0
        self.last_end = 0.0
        self.idle_s: float | None = None
        self.lifetime_s: float | None = None
        self.shutdown_s = 0.0
        self.checked = checked
        self.wt = wt  # wasmtime-py, lazily imported
        self.engine: wasmtime.Engine | None = None
        self.store: wasmtime.Store | None = None
        self.exports: Mapping[str, Any] | None = None  # the instance's, each called as a Func
        self.capture: _Capture | None = None  # the guest's output, made with the store
        self.table: _Files | None = None
        self.host: Host | None = None
        self.metered = False
        self.origin_ns = 0
        self.bounded: _Bounded | None = None
        self.private_loop: _ToolLoop | None = None
        self.scratch: _Private | None = None
        self.private: _Private | None = None
        self.walked: list[_Walked] = []
        self.home: _call._GuestHome | None = None  # made after the preopens are listed
        self.context: contextvars.Context | None = None  # taken at the opening, for a closer
        self.ending_home: _Home | None = None  # the ending's home thread, while it runs
        self.set_digests: _artifacts._Checked | None = None  # a snapshot's set, as checked
        self.captured: tuple[bytes, int] | None = None  # a making's image and files left open


_WAKE = object()


def _wake_reaper() -> None:
    process().reaper_queue.put(_WAKE)


def _take_dropped() -> list[_State]:
    """Every dropped session the reaper has been told of and not yet ended, in order."""
    p = process()
    out = []
    while True:
        try:
            item = p.reaper_queue.get_nowait()
        except queue.Empty:
            break
        if isinstance(item, _State):
            p.dropped.append(item)
    while p.dropped:
        out.append(p.dropped.popleft())
    return out


def _collected(state: _State) -> None:
    """The collector's finalizer for a dropped session: no lock, nothing closed; the state goes
    to the reaper, which ends it on its own thread."""
    p = process()
    if not p.forked:
        p.reaper_queue.put(state)


def _due(state: _State) -> tuple[float, str] | None:
    """The first moment one of the session's bounds passes, and which; None for no bound."""
    due = []
    if state.idle_s is not None:
        due.append((state.last_end + state.idle_s, "idle"))
    if state.lifetime_s is not None:
        due.append((state.opened + state.lifetime_s, "lifetime"))
    return min(due) if due else None


def _mark(state: _State, reason: str) -> bool:
    """Under the state's lock: set `ended` once, by the first cause, and move the phase (OPEN to
    MARKED, or TURN to STOPPING); True if this call set it. A second mark is no event."""
    if state.ended is not None:
        return False
    state.ended = reason
    _move(state, _Event.MARK)
    return True


def _in_context(context: contextvars.Context, state: _State) -> None:
    context.run(_end_quietly, state)


def _start_closer(state: _State) -> None:
    """Run an ending the runner starts itself on a closer thread of its own, in a copy of the
    context taken at the opening, or hand it to the observers' `start_ending`. The caller has
    claimed the ending for `_CLOSER` and holds no lock. A closer that cannot start, as on a host
    short of threads, never loses the ending: it runs here, on the calling thread, which waits
    for it (at most the session's `shutdown_s` of guest code, plus any call of the embedder's
    own code it makes)."""
    context = state.context.copy() if state.context is not None else None
    target = _end_quietly if context is None else functools.partial(_in_context, context)
    p = process()
    try:
        starter = p.observers.start_ending
        if starter is not None:
            starter(state)
            return
        thread = threading.Thread(
            target=target, args=(state,), name="wasi-python-session-closer", daemon=True
        )
        with p.closers_lock:
            p.closers.add(thread)
        try:
            thread.start()
        except BaseException:
            with p.closers_lock:
                p.closers.discard(thread)
            raise
    except BaseException:
        target(state)  # never raises: the outcome records how the ending went


def _end_quietly(state: _State) -> None:
    try:
        _end_session(state, _CLOSER)
    except BaseException:
        pass  # a closer has no caller: the outcome records the stop
    finally:
        p = process()
        with p.closers_lock:
            p.closers.discard(threading.current_thread())


def _reap(now: float) -> float | None:
    """The reaper's one step: end every session whose bound has passed at `now` and that has no
    turn running, each ending handed to the observers' `start_ending`, or to a closer thread;
    the seconds until the next is due, or None when none is."""
    for item in _take_dropped():  # the collector's finalizer queued them
        _end_dropped(item)
    p = process()
    with p.sessions_lock:
        states = list(p.sessions)
    wait: float | None = None
    for state in states:
        start = False
        with state.lock:
            due = _due(state)
            if state.phase is _Phase.MARKED:  # marked, and nobody holds it: never left so
                start = _claim_ending(state, _CLOSER)
            elif state.phase is not _Phase.OPEN or due is None:
                continue
            elif now >= due[0]:
                start = _mark(state, due[1]) and _claim_ending(state, _CLOSER)
            else:
                left = due[0] - now
                wait = left if wait is None else min(wait, left)
        if start:
            _start_closer(state)
    return wait


def _reaper_loop(
    get: Callable[[float | None], Any] | None = None,
    clock: Callable[[], float] | None = None,
    rounds: int | None = None,
) -> None:
    """The reaper: wait on the queue until the next bound is due or a session is dropped or
    changes, then take one step. `get` and `clock` are injected by the judge, with a number of
    `rounds`, so it never sleeps."""
    p = process()
    wait: float | None = None
    done = 0
    while rounds is None or done < rounds:
        done += 1
        try:
            item = (get or (lambda w: p.reaper_queue.get(timeout=w)))(wait)
        except queue.Empty:
            item = _WAKE
        if p.reaper_stop:
            if item is not _WAKE:
                p.reaper_queue.put(item)  # for the exit hook to drain
            return
        if isinstance(item, _State):
            p.dropped.append(item)  # `_reap` takes it, in order
        if p.observers.reaper_paused:
            wait = None
            continue
        try:
            wait = _reap((clock or p.observers.clock)())
        except BaseException:
            wait = TICK_S  # never dies: try again soon


def _end_dropped(state: _State) -> None:
    """A dropped session at rest is ended "closed" on a closer; one already marked, and held by
    nobody, keeps its reason and is ended on a closer too."""
    with state.lock:
        if state.phase is _Phase.OPEN:
            _mark(state, "closed")
        start = state.phase is _Phase.MARKED and _claim_ending(state, _CLOSER)
    if start:
        _start_closer(state)


def _ensure_reaper() -> None:
    """The reaper thread, a daemon started with the first session, and the exit hook."""
    p = process()
    with p.sessions_lock:
        if not p.reaper_hooked:
            atexit.register(_sessions_at_exit)  # after the process's release: so it runs first
            p.reaper_hooked = True
        if p.observers.reaper_enabled and p.reaper_thread is None and not p.reaper_stop:
            thread = threading.Thread(target=_reaper_loop, name="wasi-python-reaper", daemon=True)
            p.reaper_thread = thread
            thread.start()


def _sessions_at_exit() -> None:
    """Stop the reaper and wait for its step; end the sessions on the collector's queue and
    every session at rest, each on its own closer, side by side; mark those whose turn still
    runs; then wait for every ending in progress."""
    p = process()
    p.reaper_stop = True
    thread = p.reaper_thread
    p.reaper_queue.put(_WAKE)
    if thread is not None and thread is not threading.current_thread():
        thread.join()
    states: list[_State] = _take_dropped()
    with p.sessions_lock:
        states += [s for s in p.sessions if s not in states]
    for state in states:
        with state.lock:
            _mark(state, "closed")
            start = state.phase is _Phase.MARKED and _claim_ending(state, _CLOSER)
        if start:
            _start_closer(state)
    for state in states:
        state.done.wait()
    with p.closers_lock:
        closers = list(p.closers)
    for closer in closers:
        closer.join()


_CLOSER = -1  # the `holder` while a closer thread is being started for the ending


def _claim_ending(state: _State, owner: int) -> bool:
    """Under the state's lock: name who runs the ending, if no one does yet (a turn's
    thread, `close()`'s caller, or a closer). False once someone has it or it is over; a claim
    before the mark is refused by the table."""
    if state.phase in (_Phase.ENDING, _Phase.ENDED):
        return False
    _move(state, _Event.CLAIM_ENDING, owner)
    return True


def _end_session(state: _State, owner: int | None = None) -> BaseException | None:
    """The ending, on this thread, once: Python's shutdown if it applies, then
    everything released. `owner` is the claim the caller holds (`_claim_ending`); with none, it
    claims the ending if no one has. Returns what the embedder's code raised during it (a
    Ctrl-C, a `BaseException`), for a caller to raise; another's ending returns None at once."""
    me = threading.get_ident()
    with state.lock:
        if state.phase is _Phase.ENDED:
            return None
        if state.phase is _Phase.MARKED:
            _move(state, _Event.CLAIM_ENDING, me)
        elif state.phase is _Phase.ENDING and owner is not None and state.holder == owner:
            _move(state, _Event.TAKE_OVER, me)
        else:
            return None
    outcome, raised = "skipped", None
    try:
        if _shutdown_applies(state):
            outcome, raised = _shutdown(state)
    except BaseException as e:
        outcome, raised = "stopped", e
    finally:

        def finish() -> None:
            try:
                _release_session(state)
            finally:
                with state.lock:
                    state.outcome = outcome
                    _move(state, _Event.RELEASED)  # sets `done`
                _wake_reaper()

        home = state.ending_home
        if home is None:
            finish()
        else:  # never while the ending's guest thread runs
            home.finish(finish)
    # what the release's removals queued, outside every lock
    _private_dirs._flush_warnings()
    return raised


def _shutdown_applies(state: _State) -> bool:
    """Python's shutdown runs only on a sound guest (the last export returned; ENDING holds no
    turn), with a budget, in a process that did not fork, on a store still open."""
    return (
        state.guest is _Guest.SOUND
        and state.shutdown_s > 0
        and not process().forked
        and state.store is not None
    )


def _ending_seconds(state: _State, now: float) -> float:
    """The seconds the ending may run guest code: its budget, capped so it ends by the opening
    plus the lifetime plus the budget."""
    end = now + state.shutdown_s
    if state.lifetime_s is not None:
        end = min(end, state.opened + state.lifetime_s + state.shutdown_s)
    return end - now


def _shutdown(state: _State) -> tuple[str, BaseException | None]:
    """Python's shutdown through the `shutdown` export, inside the budget: ("finished" or
    "stopped" or "skipped", what the embedder's code raised)."""
    left = _ending_seconds(state, process().observers.clock())
    if left <= 0:
        return "skipped", None
    if (
        _platform.PLATFORM.trap_handlers_ready() is not None
    ):  # a trap in the shutdown could end this process
        return "skipped", None
    ticks = max(1, math.ceil(left / TICK_S))
    fuel = state.checked.fuel if state.metered else None
    home = state.ending_home = _Home()  # the ending's home thread
    call, _out, _err, tool_host = _arm(state, "ending", fuel, ticks, None, 0, None, home)
    wt = state.wt
    assert state.table is not None  # the store is open: an ending runs before the release
    try:
        with _epoch_ticker(state.engine, True):
            value, exited, trapped, lost = _home._on_guest_thread(
                "shutdown", home, call, _shutdown_export, state, call
            )
        raised: BaseException | None = None
        cause = call.stopped
        if lost:
            outcome = "stopped"
        elif cause is not None:
            outcome = "finished" if isinstance(cause, wt.ExitTrap) else "stopped"
            if not isinstance(cause, (wt.Trap, wt.WasmtimeError)):
                raised = cause  # a Ctrl-C, or the embedder's own BaseException
            cause.__traceback__ = None
        elif call.ended is not None or trapped is not None:
            outcome = "stopped"
        elif exited is not None or value in (0, 120):
            outcome = "finished"
        else:
            outcome = "stopped"  # a runner fault: quiet here
        if raised is None and not lost:
            # the table's walk, its Ctrl-C check included, and made at exit too, whatever
            # run_async's exit hook set
            state.table.walk(ending=True)
        return outcome, raised
    finally:
        if tool_host is not None and state.private_loop is not None:
            state.private_loop.cancel_tasks()  # the loop itself closes with the session's release


def _shutdown_export(state: _State, call: _Call) -> tuple[int | None, int | None, str | None, bool]:
    """The `shutdown` export, on the ending's guest thread: (its value, an exit code, a
    trap's name, whether the runner lost track of the call)."""
    wt, store, exports = state.wt, state.store, state.exports
    assert exports is not None  # the store is open: an ending runs before the release
    value = exited = None
    trapped: str | None = None
    stack = _home._stack()
    stack.append(call)
    process().calls.lost = False
    try:
        on_export = process().observers.on_export
        if on_export is not None:  # told the home thread, the thread that made the call
            on_export("shutdown", _home_ident(call))
        value = exports["shutdown"](store)
    except wt.ExitTrap as e:
        exited = e.code
    except wt.Trap as e:
        trapped = _call._trap_name(e)
        e.__traceback__ = None
    except wt.WasmtimeError as e:
        trapped = _call._first_line(str(e))
        e.__traceback__ = None
    finally:
        stack.pop()
        calls = process().calls
        lost, calls.lost = getattr(calls, "lost", False), False
    return value, exited, trapped, lost


def _release_session(state: _State) -> None:
    """Close the store and free everything the session held; never raises."""
    steps: list[Callable[[], Any]] = []
    if state.private_loop is not None:
        steps.append(state.private_loop.close)
    if state.store is not None:
        steps.append(state.store.close)
    if state.capture is not None:  # after the store: nothing more can arrive
        steps.append(state.capture.close)
    if state.table is not None:
        steps.append(state.table.release)
    for w in state.walked:
        steps.append(w.close)
    if state.scratch is not None:
        steps.append(state.scratch.remove)
    if (home := state.home) is not None:
        steps.append(lambda: _call._release_home(home))
    if state.private is not None:
        steps.append(state.private.remove)
    for step in steps:
        try:
            step()
        except BaseException:
            pass
    state.store = state.exports = state.table = None
    p = process()
    with p.cache_lock:
        if state.phase is _Phase.ENDING:  # counted since its opening; a failed opening never was
            p.counts["sessions_open"] -= 1
    with p.sessions_lock:
        p.sessions.discard(state)


def _arm(
    state: _State,
    kind: str,
    fuel: int | None,
    ticks: int,
    stop: _Either | None,
    output_bytes: int | None,
    loop: asyncio.AbstractEventLoop | None,
    home: _Home,
) -> tuple[_Call, _Stream, _Stream, _ToolHost | None]:
    """One call into the session's instance: its fuel and epoch deadline re-armed, its waits on
    the session's clock base, fresh output streams, a frame host and mount counters of its own
    (step 2)."""
    store, table = state.store, state.table
    assert store is not None and table is not None  # a turn or an ending: the store is open
    if state.metered:
        store.set_fuel(UNMETERED if fuel is None else fuel)
    store.set_epoch_deadline(min(CANCEL_TICKS, ticks))  # the session's callback checks the rest
    obs = process().observers
    if obs.on_arm is not None:
        obs.on_arm(kind, ticks)
    stop_at = None if ticks >= NO_DEADLINE else _call._stop_at(_epoch_ticker.count(), ticks)
    checks: list[Callable[[], bool]] = []
    if stop_at is not None:
        checks.append(lambda: _epoch_ticker.count() >= stop_at)
    if stop is not None:
        checks.append(stop.is_set)
    if _home._ctrl_c_watched():
        checks.append(lambda: process().ctrl_c_pending)
    checks.append(home.stopped)  # a wait ends at an exception raised into the home
    waits = _Waits(
        lambda: time.perf_counter(),
        time.sleep,
        (lambda: any(check() for check in checks)) if checks else None,
    )
    out, err = _Stream("stdout", output_bytes), _Stream("stderr", output_bytes)
    assert state.capture is not None  # made with the store
    state.capture.retarget(out, err)
    host, admit, tool_host = state.host, None, None
    if state.checked.tools is not None:
        tool_host = _session_tool_host(state, stop_at, stop, loop, home)
        host, admit = tool_host, tool_host.admit
    table.new_turn()
    call = _Call(store, host, waits, state.origin_ns, stop, stop_at, admit, table=table, home=home)
    if obs.on_call is not None:
        obs.on_call(kind, call)
    return call, out, err, tool_host


def _session_tool_host(
    state: _State,
    stop_at: int | None,
    stop: _Either | None,
    loop: asyncio.AbstractEventLoop | None,
    home: _Home,
) -> _ToolHost:
    """A frame host per turn; one bound per session, so abandoned tool threads are counted
    across its turns; one private tool loop per session for its synchronous turns, or the
    caller's loop for a turn by run_async."""
    from ._tool_host import _ToolHost, _ToolLoop

    c = state.checked
    assert c.tools is not None and state.bounded is not None  # made together at the opening
    state.bounded.rearm(stop_at, stop, _call._home_context(home))
    if loop is not None:
        tool_loop = _ToolLoop(loop, count=_call._count_tool_threads)
    else:
        if state.private_loop is None:
            state.private_loop = _ToolLoop(None, count=_call._count_tool_threads)
        tool_loop = state.private_loop
    return _ToolHost(
        c.tools,
        gate=c.gate,
        max_calls=c.tool_calls,
        invoke=state.bounded,
        tool_loop=tool_loop,
        max_bytes=c.tool_request_bytes,
    )


class _TurnDone(NamedTuple):
    completed: Completed
    cause: str | None  # what ends the session, if the turn does
    returned: bool  # the export returned a status: the interpreter is sound


def _home_ident(call: _Call) -> int:
    home = call.home
    return threading.get_ident() if home is None else home.ident


def _drive_turn(
    state: _State, call: _Call, data: bytes, export: str = "turn"
) -> tuple[int | None, int | None, str | None, bool]:
    """(the export's value, an exit code, a trap's name, whether guest code ran), on this
    thread's stack, by `_drive`'s rules (steps 3 and 4); `export` is `turn`, or `prepare` for a
    making. Before any guest code, as in
    `_drive`, a turn is refused when wasmtime's trap handlers were replaced: the session then
    ends as on an error, without Python's shutdown."""
    not_ready = _platform.PLATFORM.trap_handlers_ready()
    if not_ready is not None:
        raise RuntimeError(_TRAP_HANDLERS_REPLACED.format(signal=not_ready))
    wt, store, exports = state.wt, state.store, state.exports
    assert exports is not None  # a claimed turn: the store is open
    value = exit_code = None
    trapped: str | None = None
    stack = _home._stack()
    stack.append(call)
    process().calls.lost = False
    try:
        if call.cancel is not None and call.cancel.is_set():  # before any guest code
            return None, None, "cancelled", False
        first = state.guest is _Guest.UNTOUCHED
        _move_guest(state, _GuestEvent.ENTER)
        if first and "_initialize" in exports:
            exports["_initialize"](store)
        p = 0
        if data:
            p = exports["host_alloc"](store, len(data)) & MASK32
            memory = exports["memory"]
            if p and p + len(data) <= memory.data_len(store):
                memory.write(store, data, p)
            else:
                p = 0  # the guest raises MemoryError for its code
        on_export = process().observers.on_export
        if on_export is not None:  # told the home thread, the thread that made the call
            on_export(export, _home_ident(call))
        value = exports[export](store, p, len(data))
    except wt.ExitTrap as e:
        exit_code = e.code
    except wt.Trap as e:
        trapped = _call._trap_name(e)
        e.__traceback__ = None
    except wt.WasmtimeError as e:
        trapped = _call._first_line(str(e))
        e.__traceback__ = None
    finally:
        stack.pop()
        calls = process().calls
        lost, calls.lost = getattr(calls, "lost", False), False
    if lost:
        raise RuntimeError("wasi_python lost track of a call")
    cause = call.stopped
    if cause is not None:
        value = exit_code = trapped = None
        if isinstance(cause, wt.ExitTrap):
            exit_code = cause.code
        elif isinstance(cause, wt.Trap):
            trapped = _call._trap_name(cause)
        elif isinstance(cause, wt.WasmtimeError):
            trapped = _call._first_line(str(cause))
        else:
            raise cause
        cause.__traceback__ = None
    elif call.ended is not None:
        value, exit_code, trapped = None, None, call.ended
    return value, exit_code, trapped, True


def _turn_inside(
    state: _State,
    data: bytes,
    fuel: int | None,
    deadline_s: float | None,
    output_bytes: int | None,
    cancel: threading.Event | None,
    loop: asyncio.AbstractEventLoop | None,
    home: _Home,
    export: str = "turn",
) -> _TurnDone:
    own = NO_DEADLINE if deadline_s is None else max(1, math.ceil(deadline_s / TICK_S))
    ticks, capped = own, False
    if state.lifetime_s is not None:  # the lifetime caps the turn's deadline
        left = state.opened + state.lifetime_s - process().observers.clock()
        cap = max(1, math.ceil(left / TICK_S))
        if cap < own:
            ticks, capped = cap, True
    stop = _Either(cancel, state.closing, home)
    call, out, err, tool_host = _arm(state, "turn", fuel, ticks, stop, output_bytes, loop, home)
    try:
        with _epoch_ticker(state.engine, True):
            value, exit_code, trapped, ran = _home._on_guest_thread(
                "turn", home, call, _drive_turn, state, call, data, export
            )
        assert state.capture is not None  # made with the store
        state.capture.settle()  # every byte the turn wrote, before its result is made
        after_export = process().observers.after_export
        if after_export is not None:
            after_export()
        returned = value is not None
        cause: str | None = None
        if returned:
            if not -1 < value <= 511:  # the C side owns the range
                raise RuntimeError("wasi_python lost track of a session")
            exit_code = value & 0xFF
            if value >= 256:
                cause = "quit"
        elif exit_code is not None:
            cause = "exit"
        elif trapped is not None and ran:
            cause = "lifetime" if trapped == "deadline" and capped else trapped
        fuel_used = None
        store, table = state.store, state.table
        assert store is not None and table is not None  # the turn ran: the store is open
        if ran and state.metered:
            budget = UNMETERED if fuel is None else fuel
            done = _Driven(exit_code, trapped, True, None)
            fuel_used = _call._fuel_used(budget, done, call, store.get_fuel)
        if export == "prepare" and value == 0:  # read here, before the claim is released
            memory = state.exports["memory"] if state.exports is not None else None
            state.captured = (_snapshot._capture(store, memory), table.open_now())
        if ran:
            table.walk()  # the write-backs, after the fuel is read
        context = _call._context_of(table)
        if context is not None:
            context.leave()  # between turns the table serves no call
        files = table.record() if state.checked.mounts else None
        record = None if tool_host is None else tool_host.record
        truncated = tuple(s.name for s in (out, err) if s.dropped)
        completed = Completed(
            exit_code,
            bytes(out.data),
            bytes(err.data),
            trapped,
            fuel_used,
            truncated,
            files,
            record,
            None if state.checked.start is None else state.checked.start.sha256,
        )
        return _TurnDone(completed, cause, returned)
    finally:
        if tool_host is not None:
            if loop is not None:
                tool_host.close()  # the caller's loop: the runner's tasks asked to cancel
            elif state.private_loop is not None:
                state.private_loop.cancel_tasks()  # the session's loop lives on


def _session_turn(
    state: _State,
    data: bytes,
    fuel: int | None,
    deadline_s: float | None,
    output_bytes: int | None,
    cancel: threading.Event | None,
    loop: asyncio.AbstractEventLoop | None,
    export: str = "turn",
) -> Completed:
    """A claimed turn, on this thread: run it, decide whether it ended the session, and if the
    session has ended by its return, run the ending here (step 6); `export` is the turn's. Its
    first step makes this thread the turn's holder, whichever thread claimed it, so a `close()`
    from this thread, a host function's or a provider's, returns at once."""
    with state.lock:
        _move(state, _Event.TAKE_TURN, threading.get_ident())
    done: _TurnDone | None = None
    error: BaseException | None = None
    home = _Home()  # this thread, while the turn runs on a guest thread
    try:
        try:
            with _home._deferred_ctrl_c():
                args = (state, data, fuel, deadline_s, output_bytes, cancel, loop, home, export)
                done = _turn_inside(*args)
        except BaseException as e:
            error = e
        if home.phase in _home._GUEST_MAY_RUN:  # forced out while the guest thread runs
            home.finish(lambda: _abandon_turn(state))  # run by the guest thread at its end
            raise error if error is not None else RuntimeError("wasi_python lost a turn")
        with state.lock:
            if error is not None:
                _move_guest(state, _GuestEvent.FAILED)  # whatever the export returned
                _mark(state, "error")
            elif done is not None:
                if done.returned:
                    _move_guest(state, _GuestEvent.RETURNED)  # the interpreter is sound
                elif done.cause is not None:
                    _move_guest(state, _GuestEvent.UNWOUND)  # a trap, an exit or a stop
                # else a cancel set before any guest code: the session is untouched
                if done.cause is not None:
                    _mark(state, done.cause)
                elif (
                    state.lifetime_s is not None
                    and process().observers.clock() >= state.opened + state.lifetime_s
                ):
                    _mark(state, "lifetime")
            _move(state, _Event.TURN_RETURNED)
            state.last_end = process().observers.clock()
            me = threading.get_ident()
            ended = state.phase is _Phase.MARKED and _claim_ending(state, me)  # this thread
        if ended:
            raised = _end_with_ctrl_c(state, me)
            if error is None and raised is not None:
                error = raised
    finally:
        _wake_reaper()
    if error is not None:
        raise error
    assert done is not None
    return done.completed


def _abandon_turn(state: _State) -> None:
    """A turn whose home was forced out, run by its guest thread at its end: the session ends as
    on an error, and only now may another thread enter its store, so its ending goes to a
    closer."""
    with state.lock:
        _move_guest(state, _GuestEvent.FAILED)
        _mark(state, "error")
        _move(state, _Event.TURN_RETURNED)
        state.last_end = process().observers.clock()
        start = state.phase is _Phase.MARKED and _claim_ending(state, _CLOSER)
    if start:
        _start_closer(state)
    _wake_reaper()


def _end_with_ctrl_c(state: _State, owner: int | None = None) -> BaseException | None:
    """The ending on this thread, with Ctrl-C deferred as for a turn; what it raised, if any."""
    try:
        with _home._deferred_ctrl_c():
            raised = _end_session(state, owner)
    except BaseException as e:
        return e
    return raised


def _open_session(
    wt: types.ModuleType,
    c: _CheckedCall,
    host: Host | None,
    chosen: _engines._Cache,
    artifacts: Artifacts | None,
    state: _State,
) -> None:
    """A session's opening: find the set and refuse one without the session exports, walk and
    judge the folders, make the store and instantiate it; no guest code runs."""
    found, checked = (
        (artifacts, None)
        if artifacts is not None
        else _artifacts._found_and_checked(c.binary == "snapshot")
    )
    checked = state.set_digests = _snapshot._same_set(c.start, found, checked)
    if c.tools is not None and not _artifacts._has_guest_package(found.manifest):
        raise ArtifactsMissing(
            f"{found.manifest} has no `recipe … {GUEST_PACKAGE}` line: this artifact set "
            "predates the tool protocol, so its guest cannot `from host import "
            "tools`; tools= needs a set built with the guest package"
        )
    cache = chosen.folder
    binary = found.snapshot if c.binary == "snapshot" else found.plain
    metered = c.fuel is not None
    engine = _engines._engine(metered)
    module = _engines._module(
        engine, metered, binary, cache, None if checked is None else checked.binary
    )
    names = {e.name for e in module.exports}
    missing = [n for n in SESSION_EXPORTS if n not in names]
    if missing:
        raise ArtifactsMissing(
            f"{binary} does not export {' or '.join(missing)}: this artifact set predates "
            "sessions; a Session needs a set built with them"
        )
    _snapshot._refuse_unprepared(c.start, binary, names)
    root = c.root
    entries = c.import_path
    walked_root, walked = _places._walk_grants(
        root, c.grants, found, cache, entries, c.import_serving, others=_engines._caches(chosen)
    )
    state.walked = [w for w in [walked_root, *(w for _, _, w in walked)] if w is not None]
    preopens: list[_Preopen] = []
    home = _Home()  # this thread, while the opening's wasm runs on a guest thread
    try:
        zip_want = None if checked is None else checked.zip
        root_path, state.private = _call._preopens(
            found, root, walked_root, walked, preopens, zip_want
        )
        state.walked += [p.walked for p in preopens]
        mounts = c.mounts
        fixed = None if c.start is None else c.start.home
        state.home = _call._guest_home(root_path, preopens, tuple(m.guest for m in mounts), fixed)
        store = state.store = wt.Store(engine)
        if metered:
            store.set_fuel(UNMETERED)  # instantiation's own memory fill
        if c.memory_bytes is not None:
            store.set_limits(memory_size=c.memory_bytes)
        wasi = wt.WasiConfig()
        state.origin_ns = time.perf_counter_ns()  # the session's clock base
        wasi.argv = [ARGV0, *entries]
        wasi.env = sorted({**_call.BASE_ENV, "HOME": state.home.guest, **(c.env or {})}.items())
        state.capture = _outputs._capture(wasi, _Stream("stdout", 0), _Stream("stderr", 0))
        scratch = state.scratch = _Private("wasi-python-")
        mounted: list[_Preopen] = []
        if mounts:
            placeholder = scratch.path / "mount"
            placeholder.mkdir()
            for i, mount in enumerate(mounts):
                w = _platform.PLATFORM.walk("", str(placeholder), judge=False)
                state.walked.append(w)
                mounted.append(_Preopen(f"mounts[{i}] at {mount.guest}", w, mount.guest, False))
        every = [*preopens, *mounted]
        for p in every:
            wasi.preopen_dir(p.walked.path, p.guest, p.writable)
        stdin_path = scratch.path / "stdin"
        stdin_path.write_bytes(b"")
        wasi.stdin_file = str(stdin_path)
        store.set_wasi(wasi)
        linker = _call._linker(wt, engine)
        from ._fs_table import _Files

        staging = STAGING_CEILING if c.memory_bytes is None else c.memory_bytes
        others = [p.guest for p in preopens]
        if mounts:
            guest_linker = _call._mount_linker(wt, engine)
            first = 3 + len(preopens)
            numbers = [(mount, first + i) for i, mount in enumerate(mounts)]
        else:
            guest_linker = _call._counted_linker(wt, engine)
            numbers = []
        table = state.table = _Files(
            numbers,
            others,
            c.file_calls,
            staging,
            metered,
            engine,
            open_files=c.open_files,  # per session: the store keeps them
            context=_call._Context(),
        )
        table.session = True
        store.set_epoch_deadline(NO_DEADLINE)  # no guest code runs before the first turn
        _call._watch(store)  # every turn can be stopped by a close
        check = _engines._check_module(wt, engine, metered)
        state.exports = _home._on_guest_thread(
            "open",
            home,
            None,
            _open_wasm,
            wt,
            linker,
            guest_linker,
            store,
            check,
            every,
            module,
            table,
            None if c.start is None else c.start.image,
        )
        state.engine, state.metered = engine, metered
        if c.tools is not None:
            from ._tool_host import _Bounded

            state.bounded = _Bounded(
                tick_s=TICK_S,
                ticks=lambda: _epoch_ticker.count(),
                ctrl_c=_call._ctrl_c_now,
                count=_call._count_tool_threads,
                abandoned=_call._count_abandoned,
                wait_s=state.lifetime_s,  # a turn's tool call waits at most the lifetime
            )
    except BaseException:

        def release() -> None:
            _release_session(state)
            with state.lock:
                _move(state, _Event.RELEASED)  # from OPENING: nothing was counted

        home.finish(release)  # never under a running guest
        raise


def _open_wasm(
    wt: Any,
    linker: Any,
    guest_linker: Any,
    store: Any,
    check: Any,
    every: list[_Preopen],
    module: Any,
    table: Any,
    image: bytes | None = None,
) -> Any:
    """A session's opening wasm, on its guest thread: the signal guard, the preopen
    check, the instantiation, the mount table's bind and a snapshot's image copied in; the
    instance's exports."""
    not_ready = _platform.PLATFORM.trap_handlers_ready()  # before any wasm runs
    if not_ready is not None:
        raise RuntimeError(_TRAP_HANDLERS_REPLACED.format(signal=not_ready))
    _places._check_preopens(wt, linker, store, check, every)  # the identity check, once
    instance = guest_linker.instantiate(store, module)
    table.bind(wt, store, linker, instance)
    if image is not None:
        _snapshot._restore(store, instance, image)
    return instance.exports(store)
