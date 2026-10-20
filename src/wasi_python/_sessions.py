"""Sessions: `SessionEnded`, the state of a session, the reaper, the endings and the shutdown,
the turns, and `_open_session`."""

from __future__ import annotations

import atexit
import functools
import math
import os
import queue
import secrets
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, NamedTuple

from . import _artifacts, _call, _engines, _home, _places, _platform, _private_dirs
from ._artifacts import GUEST_PACKAGE, Artifacts, ArtifactsMissing
from ._call import ARGV0, MASK32, UNMETERED, Completed, Host, _Call, _Driven, _Stream, _Waits
from ._engines import _epoch_ticker
from ._home import _Home
from ._limits import CANCEL_TICKS, NO_DEADLINE, TICK_S
from ._places import _Preopen, _Walked
from ._platform import _TRAP_HANDLERS_REPLACED
from ._private_dirs import _Private
from ._process import process
from .mounts import STAGING_CEILING, Mount

# ---------------------------------------------------------------------------------------------
# Sessions (spec 055): one instance of the guest kept across turns, with an idle bound and a
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
    when an exception was raised into the turn's home thread (spec 078, C1)."""

    __slots__ = ("first", "second", "home")

    def __init__(
        self, first: threading.Event | None, second: threading.Event, home: Any = None
    ) -> None:
        self.first, self.second, self.home = first, second, home

    def is_set(self) -> bool:
        if self.home is not None and self.home.raised is not None:
            return True
        return (self.first is not None and self.first.is_set()) or self.second.is_set()


class _State:
    """Everything a session holds: its store and folders, its limits and its flags. It never
    refers to its `Session`, so the collector can finalize a dropped one (Decision 13)."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.ended: str | None = None
        self.outcome: str | None = None
        self.busy = False
        self.closing = threading.Event()  # set with `ended`: stops a running turn
        self.done = threading.Event()  # the ending has finished; everything is released
        self.turn_thread: int | None = None
        self.ending_thread: int | None = None
        self.called = False  # a turn's export was called
        self.sound = False  # the last turn's export returned: the interpreter is safe to enter
        self.needs_initialize = False
        self.opened = 0.0
        self.last_end = 0.0
        self.idle_s: float | None = None
        self.lifetime_s: float | None = None
        self.shutdown_s = 0.0
        self.c: dict[str, Any] = {}
        self.wt: Any = None
        self.engine: Any = None
        self.store: Any = None
        self.exports: Any = None
        self.keys: tuple[int, int] = (0, 0)
        self.table: Any = None
        self.host: Host | None = None
        self.metered = False
        self.origin_ns = 0
        self.bounded: Any = None
        self.private_loop: Any = None
        self.scratch: _Private | None = None
        self.private: _Private | None = None
        self.walked: list[_Walked] = []
        self.home: tuple[str, Path | None, int | None] | None = None
        self.counted = False
        self.context: Any = None  # a copy taken at the opening, for a closer (the re-review's F7)
        self.ending_home: Any = None  # the ending's home thread, while it runs (spec 078)


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
    to the reaper, which ends it on its own thread (the review's F9, the Confirmation's N2)."""
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
    """Under the state's lock: set `ended` once, by the first cause; True if this call set it."""
    if state.ended is not None:
        return False
    state.ended = reason
    state.closing.set()
    return True


def _start_closer(state: _State) -> None:
    """Run an ending the runner starts itself on a closer thread of its own (Decision 8)."""
    context = state.context.copy() if state.context is not None else None
    target = _end_quietly if context is None else functools.partial(context.run, _end_quietly)
    thread = threading.Thread(
        target=target, args=(state,), name="wasi-python-session-closer", daemon=True
    )
    p = process()
    with p.closers_lock:
        p.closers.add(thread)
    thread.start()


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
    the seconds until the next is due, or None when none is (Decision 9)."""
    for item in _take_dropped():  # the collector's finalizer queued them (Decision 13)
        _end_dropped(item)
    p = process()
    with p.sessions_lock:
        states = list(p.sessions)
    wait: float | None = None
    for state in states:
        start = False
        with state.lock:
            due = _due(state)
            if state.ended is not None or state.busy or due is None:
                continue
            if now >= due[0]:
                start = _mark(state, due[1]) and _claim_ending(state, _CLOSER)
            else:
                left = due[0] - now
                wait = left if wait is None else min(wait, left)
        if start:
            (p.observers.start_ending or _start_closer)(state)
    return wait


def _reaper_loop(
    get: Callable[[float | None], Any] | None = None,
    clock: Callable[[], float] | None = None,
    rounds: int | None = None,
) -> None:
    """The reaper: wait on the queue until the next bound is due or a session is dropped or
    changes, then take one step. `get` and `clock` are injected by the judge, with a number of
    `rounds`, so it never sleeps (Decision 9)."""
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
    with state.lock:
        start = not state.busy and _mark(state, "closed") and _claim_ending(state, _CLOSER)
    if start:
        (process().observers.start_ending or _start_closer)(state)


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
    runs; then wait for every ending in progress (Decision 13; the re-review's F8)."""
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
            start = not state.busy and _claim_ending(state, _CLOSER)
        if start:
            _start_closer(state)
    for state in states:
        state.done.wait()
    with p.closers_lock:
        closers = list(p.closers)
    for closer in closers:
        closer.join()


_CLOSER = -1  # `ending_thread` while a closer thread is being started for the ending


def _claim_ending(state: _State, owner: int) -> bool:
    """Under the state's lock: name who runs the ending, if no one does yet (Decision 8: a turn's
    thread, `close()`'s caller, or a closer)."""
    if state.ending_thread is not None or state.done.is_set():
        return False
    state.ending_thread = owner
    return True


def _end_session(state: _State, owner: int | None = None) -> BaseException | None:
    """The ending (Decision 8), on this thread, once: Python's shutdown if it applies, then
    everything released. `owner` is the claim the caller holds (`_claim_ending`); with none, it
    claims the ending if no one has. Returns what the embedder's code raised during it (a
    Ctrl-C, a `BaseException`), for a caller to raise; another's ending returns None at once."""
    me = threading.get_ident()
    with state.lock:
        if state.done.is_set():
            return None
        if state.ending_thread is None:
            state.ending_thread = me
        elif owner is not None and state.ending_thread == owner:
            state.ending_thread = me
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
                state.done.set()
                _wake_reaper()

        home = state.ending_home
        if home is None:
            finish()
        else:  # never while the ending's guest thread runs (spec 078, Decision 14)
            home.finish(finish)
    # what the release's removals queued, outside every lock (spec 084)
    _private_dirs._flush_warnings()
    return raised


def _shutdown_applies(state: _State) -> bool:
    return (
        state.called
        and state.sound
        and not state.busy
        and state.shutdown_s > 0
        and not process().forked
        and state.store is not None
    )


def _ending_seconds(state: _State, now: float) -> float:
    """The seconds the ending may run guest code: its budget, capped so it ends by the opening
    plus the lifetime plus the budget (the re-review's F2)."""
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
        _platform._trap_handlers_ready() is not None
    ):  # a trap in the shutdown could end this process
        return "skipped", None  # (spec 071, Decision 9)
    ticks = max(1, math.ceil(left / TICK_S))
    fuel = state.c["fuel"] if state.metered else None
    home = state.ending_home = _Home()  # the ending's home thread (spec 078)
    call, _out, _err, tool_host = _arm(state, "ending", fuel, ticks, None, 0, None, home)
    wt = state.wt
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
            outcome = "stopped"  # a runner fault: quiet here (the re-review's N3)
        if raised is None and not lost:
            # spec 034's walk, its Ctrl-C check included (the re-review's F4), and made at exit
            # too, whatever run_async's exit hook set (the build review's F1)
            state.table.walk(ending=True)
        return outcome, raised
    finally:
        if tool_host is not None and state.private_loop is not None:
            state.private_loop.cancel_tasks()  # the loop itself closes with the session's release


def _shutdown_export(state: _State, call: _Call) -> tuple[int | None, int | None, str | None, bool]:
    """The `shutdown` export, on the ending's guest thread (spec 078): (its value, an exit code, a
    trap's name, whether the runner lost track of the call)."""
    wt, store = state.wt, state.store
    value = exited = None
    trapped: str | None = None
    stack = _home._stack()
    stack.append(call)
    process().calls.lost = False
    try:
        on_export = process().observers.on_export
        if on_export is not None:  # told the home thread, the one spec 055 means
            on_export("shutdown", _home_ident(call))
        value = state.exports["shutdown"](store)
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
    steps.append(lambda: _drop_keys(state.keys))
    if state.table is not None:
        steps.append(state.table.release)
    for w in state.walked:
        steps.append(w.close)
    if state.scratch is not None:
        steps.append(state.scratch.remove)
    if state.home is not None:
        steps.append(lambda: _remove_home(state.home))
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
        if state.counted:
            p.counts["sessions_open"] -= 1
            state.counted = False
    with p.sessions_lock:
        p.sessions.discard(state)


def _drop_keys(keys: tuple[int, int]) -> None:
    p = process()
    with p.outputs_lock:
        for key in keys:
            p.outputs.pop(key, None)


def _remove_home(home: tuple[str, Path | None, int | None]) -> None:
    name, tmp, tmp_fd = home
    try:
        _private_dirs._remove_fresh_home(name, tmp, tmp_fd)
    finally:
        _platform._close(tmp_fd)


def _arm(
    state: _State,
    kind: str,
    fuel: int | None,
    ticks: int,
    stop: Any,
    output_bytes: int | None,
    loop: Any,
    home: Any = None,
) -> tuple[_Call, _Stream, _Stream, Any]:
    """One call into the session's instance: its fuel and epoch deadline re-armed, its waits on
    the session's clock base, fresh output streams, a frame host and mount counters of its own
    (Decision 7, step 2)."""
    store = state.store
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
    if home is not None:
        checks.append(home.stopped)  # a wait ends at an exception raised into the home (C1)
    waits = _Waits(
        lambda: time.perf_counter(),
        time.sleep,
        (lambda: any(check() for check in checks)) if checks else None,
    )
    out, err = _Stream("stdout", output_bytes), _Stream("stderr", output_bytes)
    p = process()
    with p.outputs_lock:
        p.outputs[state.keys[0]], p.outputs[state.keys[1]] = out, err
    host, admit, tool_host = state.host, None, None
    if state.c.get("tools") is not None:
        tool_host = _session_tool_host(state, stop_at, stop, loop, home)
        host, admit = tool_host, tool_host.admit
    state.table.new_turn()
    call = _Call(store, host, waits, state.origin_ns, stop, stop_at, state.table, admit, home=home)
    if obs.on_call is not None:
        obs.on_call(kind, call)
    return call, out, err, tool_host


def _session_tool_host(
    state: _State, stop_at: int | None, stop: Any, loop: Any, home: Any = None
) -> Any:
    """A frame host per turn; one bound per session, so abandoned tool threads are counted
    across its turns; one private tool loop per session for its synchronous turns, or the
    caller's loop for a turn by run_async (Decision 5, Decision 11)."""
    from .tools import _ToolHost, _ToolLoop

    c = state.c
    state.bounded.rearm(stop_at, stop, _call._home_context(home))
    if loop is not None:
        tool_loop = _ToolLoop(loop, count=_call._count_tool_threads)
    else:
        if state.private_loop is None:
            state.private_loop = _ToolLoop(None, count=_call._count_tool_threads)
        tool_loop = state.private_loop
    return _ToolHost(
        c["tools"],
        gate=c["gate"],
        max_calls=c["tool_calls"],
        invoke=state.bounded,
        tool_loop=tool_loop,
        max_bytes=c.get("tool_request_bytes"),
    )


class _TurnDone(NamedTuple):
    completed: Completed
    cause: str | None  # what ends the session, if the turn does
    returned: bool  # the export returned a status: the interpreter is sound


def _home_ident(call: Any) -> int:
    home = getattr(call, "home", None)
    return threading.get_ident() if home is None else home.ident


def _drive_turn(
    state: _State, call: _Call, data: bytes
) -> tuple[int | None, int | None, str | None, bool]:
    """(the export's value, an exit code, a trap's name, whether guest code ran), on this
    thread's stack, by `_drive`'s rules (Decision 7, steps 3 and 4). Before any guest code, as in
    `_drive`, a turn is refused when wasmtime's trap handlers were replaced (spec 071, Decision
    9): the session then ends as on an error, without Python's shutdown."""
    not_ready = _platform._trap_handlers_ready()
    if not_ready is not None:
        raise RuntimeError(_TRAP_HANDLERS_REPLACED.format(signal=not_ready))
    wt, store, exports = state.wt, state.store, state.exports
    value = exit_code = None
    trapped: str | None = None
    stack = _home._stack()
    stack.append(call)
    process().calls.lost = False
    try:
        if call.cancel is not None and call.cancel.is_set():  # before any guest code
            return None, None, "cancelled", False
        state.called = True
        if state.needs_initialize:
            state.needs_initialize = False
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
        if on_export is not None:  # told the home thread, the one spec 055 means (spec 078)
            on_export("turn", _home_ident(call))
        value = exports["turn"](store, p, len(data))
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
    loop: Any,
    home: Any = None,
) -> _TurnDone:
    home = home if home is not None else _Home()
    own = NO_DEADLINE if deadline_s is None else max(1, math.ceil(deadline_s / TICK_S))
    ticks, capped = own, False
    if state.lifetime_s is not None:  # the lifetime caps the turn's deadline (the review's F4)
        left = state.opened + state.lifetime_s - process().observers.clock()
        cap = max(1, math.ceil(left / TICK_S))
        if cap < own:
            ticks, capped = cap, True
    stop = _Either(cancel, state.closing, home)
    call, out, err, tool_host = _arm(state, "turn", fuel, ticks, stop, output_bytes, loop, home)
    try:
        with _epoch_ticker(state.engine, True):
            value, exit_code, trapped, ran = _home._on_guest_thread(
                "turn", home, call, _drive_turn, state, call, data
            )
        after_export = process().observers.after_export
        if after_export is not None:
            after_export()
        returned = value is not None
        cause: str | None = None
        if returned:
            if not -1 < value <= 511:  # the C side owns the range (Decision 2)
                raise RuntimeError("wasi_python lost track of a session")
            exit_code = value & 0xFF
            if value >= 256:
                cause = "quit"
        elif exit_code is not None:
            cause = "exit"
        elif trapped is not None and ran:
            cause = "lifetime" if trapped == "deadline" and capped else trapped
        fuel_used = None
        if ran and state.metered:
            budget = UNMETERED if fuel is None else fuel
            done = _Driven(exit_code, trapped, True, None)
            fuel_used = _call._fuel_used(budget, done, call, state.store.get_fuel)
        if ran:
            state.table.walk()  # spec 034, Decision 8, after the fuel is read
        files = state.table.record() if state.c.get("mounts") else None
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
        )
        return _TurnDone(completed, cause, returned)
    finally:
        if tool_host is not None:
            if loop is not None:
                tool_host.close()  # the caller's loop: the runner's tasks asked to cancel
            elif state.private_loop is not None:
                state.private_loop.cancel_tasks()  # the session's loop lives on (spec 053)


def _session_turn(
    state: _State,
    data: bytes,
    fuel: int | None,
    deadline_s: float | None,
    output_bytes: int | None,
    cancel: threading.Event | None,
    loop: Any,
) -> Completed:
    """A claimed turn, on this thread: run it, decide whether it ended the session, and if the
    session has ended by its return, run the ending here (Decision 7, step 6)."""
    done: _TurnDone | None = None
    error: BaseException | None = None
    home = _Home()  # this thread, while the turn runs on a guest thread (spec 078)
    try:
        try:
            with _home._deferred_ctrl_c():
                done = _turn_inside(state, data, fuel, deadline_s, output_bytes, cancel, loop, home)
        except BaseException as e:
            error = e
        if not home.done:  # forced out while the guest thread runs (spec 078, Decision 14)
            home.finish(lambda: _abandon_turn(state))
            raise error if error is not None else RuntimeError("wasi_python lost a turn")
        with state.lock:
            if error is not None:
                state.sound = False  # whatever the export returned: no shutdown (F3's error row)
                _mark(state, "error")
            elif done is not None:
                if done.returned:
                    state.sound = True  # the export returned: the interpreter is sound
                elif done.cause is not None:
                    state.sound = False  # a trap, an exit or a stop unwound it
                # else a cancel set before any guest code: the session is untouched
                if done.cause is not None:
                    _mark(state, done.cause)
                elif (
                    state.lifetime_s is not None
                    and process().observers.clock() >= state.opened + state.lifetime_s
                ):
                    _mark(state, "lifetime")
            state.busy = False
            state.turn_thread = None
            state.last_end = process().observers.clock()
            me = threading.get_ident()
            ended = state.ended is not None and _claim_ending(state, me)  # the turn's thread (F3)
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
    on an error, and only now may another thread enter its store (spec 078, Decision 14)."""
    with state.lock:
        state.sound = False
        _mark(state, "error")
        state.busy = False
        state.turn_thread = None
        state.last_end = process().observers.clock()
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
    wt: Any,
    c: dict[str, Any],
    host: Host | None,
    snapshot: bool,
    cache_dir: Any,
    artifacts: Artifacts | None,
    state: _State,
) -> None:
    """Decision 6: find the set and refuse one without the session exports, walk and judge the
    folders, make the store and instantiate it; no guest code runs."""
    found, checked = (
        (artifacts, None) if artifacts is not None else _artifacts._found_and_checked(snapshot)
    )

    if c.get("tools") is not None and not _artifacts._has_guest_package(found.manifest):
        raise ArtifactsMissing(
            f"{found.manifest} has no `recipe … {GUEST_PACKAGE}` line: this artifact set "
            "predates the tool protocol (spec 031), so its guest cannot `from host import "
            "tools`; tools= needs a set built with the guest package"
        )
    cache = _engines._cache_dir(cache_dir)
    binary = found.snapshot if snapshot else found.plain
    metered = c["fuel"] is not None
    engine = _engines._engine(metered)
    module = _engines._module(
        engine, metered, binary, cache, None if checked is None else checked.binary
    )
    names = {e.name for e in module.exports}
    missing = [n for n in SESSION_EXPORTS if n not in names]
    if missing:
        raise ArtifactsMissing(
            f"{binary} does not export {' or '.join(missing)}: this artifact set predates "
            "sessions (spec 055); a Session needs a set built with them"
        )
    root = c["root"]
    entries, serving = c.get("import_path", ()), c.get("import_serving", ())
    walked_root, walked = _places._walk_grants(root, c["grants"], found, cache, entries, serving)
    state.walked = [w for w in [walked_root, *(w for _, _, w in walked)] if w is not None]
    preopens: list[_Preopen] = []
    home = _Home()  # this thread, while the opening's wasm runs on a guest thread (spec 078)
    try:
        zip_want = None if checked is None else checked.zip
        root_path, state.private = _call._preopens(
            found, root, walked_root, walked, preopens, zip_want
        )
        state.walked += [p.walked for p in preopens]
        mounts: tuple[Mount, ...] = c.get("mounts", ())
        tmp, tmp_fd = _call._home_folder(root_path, preopens, tuple(m.guest for m in mounts))
        home_guest = None
        if tmp is not None:
            name = f".home-{secrets.token_hex(16)}"
            try:
                if tmp_fd is not None:
                    os.mkdir(name, dir_fd=tmp_fd)
                else:
                    (tmp / name).mkdir()
            except BaseException:
                _platform._close(tmp_fd)
                raise
            state.home = (name, tmp, tmp_fd)
            home_guest = f"/tmp/{name}"
        store = state.store = wt.Store(engine)
        if metered:
            store.set_fuel(UNMETERED)  # instantiation's own memory fill (spec 008)
        if c["memory_bytes"] is not None:
            store.set_limits(memory_size=c["memory_bytes"])
        wasi = wt.WasiConfig()
        state.origin_ns = time.perf_counter_ns()  # the session's clock base (the review's F6)
        wasi.argv = [ARGV0, *entries]
        fresh = {} if home_guest is None else {"HOME": home_guest}
        wasi.env = sorted({**_call.BASE_ENV, **fresh, **(c["env"] or {})}.items())
        state.keys = _call._send_outputs(wasi, _Stream("stdout", 0), _Stream("stderr", 0))
        scratch = state.scratch = _Private("wasi-python-")
        mounted: list[_Preopen] = []
        if mounts:
            placeholder = scratch.path / "mount"
            placeholder.mkdir()
            for i, mount in enumerate(mounts):
                w = _places._walk("", str(placeholder), judge=False)
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
        from .mounts import _Files

        staging = STAGING_CEILING if c["memory_bytes"] is None else c["memory_bytes"]
        others = [p.guest for p in preopens]
        if mounts:
            guest_linker = _call._mount_linker(wt, engine)
            first = 3 + len(preopens)
            numbers = [(mount, first + i) for i, mount in enumerate(mounts)]
        else:
            guest_linker = _call._guard_linker(wt, engine)
            numbers = []
        table = state.table = _Files(
            numbers,
            others,
            c["file_calls"],
            staging,
            metered,
            engine,
            open_files=c["open_files"],  # spec 068, per session: the store keeps them (Decision 5)
        )
        table.session = True
        store.set_epoch_deadline(NO_DEADLINE)  # no guest code runs before the first turn
        _call._watch(store)  # every turn can be stopped by a close (Decision 6)
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
        )
        state.needs_initialize = "_initialize" in state.exports
        state.wt, state.engine, state.metered = wt, engine, metered
        if c.get("tools") is not None:
            from .tools import _Bounded

            state.bounded = _Bounded(
                tick_s=TICK_S,
                ticks=lambda: _epoch_ticker.count(),
                ctrl_c=_call._ctrl_c_now,
                count=_call._count_tool_threads,
            )
    except BaseException:
        home.finish(lambda: _release_session(state))  # never under a running guest (spec 078)
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
) -> Any:
    """A session's opening wasm, on its guest thread (spec 078): the signal guard, the preopen
    check, the instantiation and the mount table's bind; the instance's exports."""
    not_ready = _platform._trap_handlers_ready()  # spec 071, Decision 9: before any wasm runs
    if not_ready is not None:
        raise RuntimeError(_TRAP_HANDLERS_REPLACED.format(signal=not_ready))
    _places._check_preopens(wt, linker, store, check, every)  # spec 017, Decision 5; once
    instance = guest_linker.instantiate(store, module)
    table.bind(wt, store, linker, instance)
    return instance.exports(store)
