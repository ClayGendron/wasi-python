"""The tool protocol's host side of a call.

It parses a frame, runs the tool on a thread of its own under a budget and a deadline, awaits
what the tool returns on the call's tool loop, and answers, keeping every frame in the record.
It imports the public module's types and the schema rules' validator, and is imported only
when a call is given tools, so `import wasi_python` never loads it.
"""

from __future__ import annotations

import asyncio
import binascii
import contextvars
import copy
import functools
import inspect
import json
import math
import re
import threading
import time
import typing
from collections.abc import Callable, Iterable
from typing import Any, NamedTuple

from . import _tool_schema
from ._tool_schema import _ECHO_CHARS, _TOOL_NESTING, _Json, _Validator
from .tools import PROTOCOL, Tool, ToolCall, ToolDenied, ToolError, ToolOutcome, ToolRecord

_PROTOCOLS = (1,)  # the versions this host serves
_TOOL_REQUEST_BYTES = 1 << 20  # a request frame's cap
_TOOL_RESPONSE_BYTES = 16 << 20  # an answer's cap: the default output cap per stream
_INT_CHARS = 64  # the longest integer literal a frame may hold
_MESSAGE_CHARS = 4096  # the longest message the guest is told
_FAULT_CHARS = 200  # a fault's type and first line, as a mount's FileFault
_RECORD_OUTCOMES = 1000  # the frames a record lists, whatever max_calls is
_MAX_ID = 2**53 - 1
_MAX_ABANDONED = 4  # tool threads one call may leave running before its next call is refused
# Abandoned tool threads alive in the whole process before any call's next tool call is refused:
# sixteen calls' worth, so a burst passes and a host notices long before it degrades.
_MAX_ABANDONED_IN_PROCESS = 64
_TOOL_WAIT_CEILING = 3600.0  # the longest a tool call waits when nothing else bounds it
_DEADLINE_MARGIN_TICKS = 2  # a tool call ends this many ticks before the run's deadline
_SURROGATE = re.compile("[\ud800-\udfff]")
# One token per match, never retried: an escape pair, a quote or a bracket (rule 3).
_TOKEN = re.compile(r'\\.|["\[\]{}]', re.S)


# -------------------------------------------------------------------------------------------------
# Frames


class _Refused(Exception):
    """A frame that breaks the protocol's rules: a `protocol` answer."""


def _nesting(text: str) -> int:
    """The deepest nesting of arrays and objects outside strings, in one pass over the text: a
    regular expression that skips whole strings would be retried at every quote of an
    unterminated one, which is quadratic on a guest's megabyte."""
    depth = deepest = 0
    inside = False
    for m in _TOKEN.finditer(text):
        token = m.group()
        if inside:
            inside = token != '"'  # an escape pair or a bracket stays inside the string
        elif token == '"':
            inside = True
        elif token in "[{":
            depth += 1
            if depth > deepest:
                deepest = depth
                if deepest > _TOOL_NESTING:
                    break
        elif token in "]}":
            depth -= 1
    return deepest


def _no_constant(name: str) -> Any:
    raise _Refused(f"the frame holds {name}, which JSON does not allow")


def _finite(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise _Refused(f"the number {_tool_schema._echo(text)} is out of range")
    return value


def _bounded_int(text: str) -> int:
    if len(text) > _INT_CHARS:
        raise _Refused(f"an integer of {len(text)} characters; at most {_INT_CHARS}")
    return int(text)


def _unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out = dict(pairs)
    if len(out) != len(pairs):
        seen: set[str] = set()
        for k, _ in pairs:
            if k in seen:
                raise _Refused(f"the frame repeats the key {_tool_schema._echo(k)}")
            seen.add(k)
    return out


def _parse(frame: bytes) -> _Json:
    """The frame's parse rules, then the `$bytes` objects decoded."""
    try:
        text = frame.decode("utf-8")
    except UnicodeDecodeError:
        raise _Refused("the frame is not UTF-8") from None
    depth = _nesting(text)
    if depth > _TOOL_NESTING:
        raise _Refused(f"the frame nests deeper than {_TOOL_NESTING} levels")
    try:
        value = json.loads(
            text,
            parse_constant=_no_constant,
            parse_float=_finite,
            parse_int=_bounded_int,
            object_pairs_hook=_unique_keys,
        )
    except _Refused:
        raise
    except (ValueError, RecursionError) as e:
        first = (str(e).splitlines() or [""])[0][:200]
        raise _Refused(f"the frame is not JSON ({first})") from None
    value = _decoded(value)
    if not isinstance(value, dict):
        raise _Refused("the frame is not a JSON object")
    return value


def _decoded(value: Any) -> Any:
    """Strings checked for lone surrogates, and each `{"$bytes": "<base64>"}` made bytes."""
    if isinstance(value, str):
        if _SURROGATE.search(value):
            raise _Refused(f"a string holds a lone surrogate: {_tool_schema._echo(value)}")
        return value
    if isinstance(value, list):
        return [_decoded(v) for v in value]
    if isinstance(value, dict):
        for k in value:
            if _SURROGATE.search(k):
                raise _Refused(f"a key holds a lone surrogate: {_tool_schema._echo(k)}")
        if "$bytes" in value:
            data = value["$bytes"]
            if len(value) != 1 or not isinstance(data, str):
                raise _Refused('a "$bytes" object must have that one key, holding a string')
            try:
                return binascii.a2b_base64(data.encode("ascii"), strict_mode=True)
            except (binascii.Error, UnicodeEncodeError):
                raise _Refused('a "$bytes" value is not strict base64') from None
        return {k: _decoded(v) for k, v in value.items()}
    return value


def _encode(answer: _Json) -> bytes:
    return json.dumps(answer, ensure_ascii=True, allow_nan=False, separators=(",", ":")).encode(
        "ascii"
    )


def _bounded(message: str) -> str:
    return message[:_MESSAGE_CHARS]


def _described(e: BaseException) -> str:
    """An exception's type name and the first line of its text, as a mount's `_described`
    (so `fault` reads as a mount's `FileFault`), but total over `BaseException`: a `__str__` that
    raises `SystemExit` gives the name alone."""
    try:
        name = type.__dict__["__name__"].__get__(type(e))  # the type's own name
        if type(name) is not str:
            name = "an exception"
    except BaseException:
        name = "an exception"
    try:
        text = str(e)
        if type(text) is not str:
            return name
        lines = str.splitlines(str.strip(text))
    except BaseException:
        return name
    return f"{name}: {lines[0]}" if lines else name


def _fault(e: BaseException) -> str:
    return _described(e)[:_FAULT_CHARS]


def _message_of(e: BaseException) -> str:
    """A ToolError's own text, bounded, as a plain str; raises whatever its __str__ raises."""
    text = str(e)
    return _bounded(text if type(text) is str else str.__str__(text))


class _Done(NamedTuple):
    """What the work gives: the answer's bytes and how it ended."""

    answer: bytes
    outcome: str  # "ok" or a kind
    message: str | None
    fault: str | None


class _Interrupted(NamedTuple):
    """What a bounded invoke gives when it did not wait for the work."""

    kind: str  # "timeout" or "cancelled"; "tool_error" when the bound itself failed
    abandoned: bool  # the work was left running
    message: str | None = None  # what the guest is told; by default "<name> timed out" and so on
    fault: str | None = None  # the bound's own exception, when it failed after the work started


class _Work:
    """The gate, then the tool, then the result's encoding, as one callable: what `invoke`
    runs. It touches no state of the frame host, so it may run, or finish late, elsewhere."""

    def __init__(self, host: _ToolHost, seq: int, frame_id: Any, tool: Tool, args: _Json) -> None:
        self.tool, self.seq, self.frame_id = tool, seq, frame_id
        self._gate, self._args, self._size = host._gate, args, host._size
        self._loop = host._loop

    def __call__(self, proceed: Callable[[], bool] | None = None, ops: _Ops | None = None) -> _Done:
        """`proceed`, from the bound, is asked once the gate has allowed and before the tool
        starts: False when the call was already answered, so the tool never runs.
        `ops`, from the bound too, lets an awaitable the gate or the tool returns start only at
        its wrapper's first step, under the bound's lock."""
        t = self.tool
        args = self._args
        skipped = f"{t.name} was not run: its call had ended"
        if self._gate is not None:
            call = ToolCall(self.seq, t, copy.deepcopy(args), self._size)
            refused = f"{t.name} was refused"
            try:
                verdict = self._gate(call)
                if inspect.isawaitable(verdict):
                    verdict = self._loop.run(verdict, ops)
            except _NotStarted:
                return self.failed("cancelled", skipped)
            except ToolError as e:
                try:
                    return self.failed("denied", _message_of(e))
                except BaseException as inner:
                    return self.failed("denied", refused, _fault(inner))
            except BaseException as e:  # a broken gate fails closed
                if self._cancelling(e, ops):
                    return self.failed("cancelled", f"{t.name} was cancelled")
                return self.failed("denied", refused, _fault(e))
            if verdict is False:
                return self.failed("denied", refused)
            if verdict is not None and verdict is not True:
                why = f"TypeError: the gate returned {type(verdict).__name__}, not None or a bool"
                return self.failed("denied", refused, why[:_FAULT_CHARS])
        if proceed is not None and not proceed():
            return self.failed("cancelled", skipped)
        internal = f"{t.name} failed (internal error)"
        try:
            value = t.fn(**args)
            if inspect.isawaitable(value):
                value = self._loop.run(value, ops)
        except _NotStarted:
            return self.failed("cancelled", skipped)
        except ToolError as e:
            how = "denied" if isinstance(e, ToolDenied) else "tool_error"
            try:
                return self.failed(how, _message_of(e))
            except BaseException as inner:
                return self.failed(how, internal, _fault(inner))
        except BaseException as e:
            if self._cancelling(e, ops):
                return self.failed("cancelled", f"{t.name} was cancelled")
            return self.failed("tool_error", internal, _fault(e))
        try:
            body = _tool_schema._to_json(value, 0)
            encoded = _encode({"v": PROTOCOL, "id": self.frame_id, "ok": True, "value": body})
        except BaseException as e:
            return self.failed("tool_error", internal, _fault(e))
        if len(encoded) > _TOOL_RESPONSE_BYTES:
            return self.failed(
                "too_large",
                f"the result of {t.name} is {len(encoded)} bytes encoded, over the "
                f"{_TOOL_RESPONSE_BYTES}-byte (16 MiB) cap",
            )
        return _Done(encoded, "ok", None, None)

    @staticmethod
    def _cancelling(e: BaseException, ops: _Ops | None) -> bool:
        """A `CancelledError` the runner did not ask for, met while the run is being cancelled:
        answered `cancelled`, as the bound would answer a slice later."""
        if not isinstance(e, asyncio.CancelledError) or ops is None:
            return False
        try:
            return ops.ending() == "cancelled"
        except BaseException:
            return False

    def failed(self, kind: str, message: str, fault: str | None = None) -> _Done:
        return _Done(_error(self.frame_id, kind, message), kind, message, fault)


def _error(frame_id: Any, kind: str, message: str) -> bytes:
    error = {"kind": kind, "message": _bounded(message)}
    return _encode({"v": PROTOCOL, "id": frame_id, "ok": False, "error": error})


def _inline(work: _Work) -> _Done | _Interrupted:
    return work()


# -------------------------------------------------------------------------------------------------
# The tool loop: where an awaitable a gate or a tool returns is awaited.

_LOOP_THREAD = "wasi-python-tool--loop"  # no tool name starts with "-": no tool thread has it
_LOOP_POLL_S = 0.01  # the work thread's wait, in slices: the runner's tick


class _NotStarted(Exception):
    """The call was answered before its awaitable started: it never runs."""


class _Post:
    """One awaitable posted to the tool loop: whether its wrapper started it, under the bound's
    lock, and how it ended. `ended` is set by the wrapper's `finally`, the task's real end;
    `returned` only once the awaitable returned, so nothing else reads as a value."""

    __slots__ = (
        "awaitable",
        "ended",
        "error",
        "loop",
        "returned",
        "skipped",
        "started",
        "task",
        "value",
    )

    def __init__(self, awaitable: Any) -> None:
        self.awaitable = awaitable
        self.ended = threading.Event()
        self.started = False  # set by the wrapper's first step, under the bound's lock
        self.skipped = False  # the first step found the call answered
        self.task: Any = None
        self.loop: Any = None
        self.value: Any = None
        self.returned = False  # the awaitable returned `value`
        self.error: BaseException | None = None


def _close_awaitable(awaitable: Any) -> None:
    """Close an awaitable that will never run, so no "never awaited" warning is printed."""
    try:
        close = getattr(awaitable, "close", None)
        if callable(close):
            close()
    except BaseException:
        pass


def _cancel_post(post: _Post) -> None:
    """Ask a started task to cancel, on its loop's own thread. A closed loop is skipped, and
    nothing raises, logs or warns. The posted future is never cancelled:
    on a closed loop that logs a traceback."""
    try:
        loop, task = post.loop, post.task
        if loop is None or task is None or loop.is_closed():
            return
        loop.call_soon_threadsafe(task.cancel)
    except BaseException:
        pass


class _ToolLoop:
    """The loop a call's awaitables run on: `loop`, the event
    loop that awaits `run_async`, which the runner never runs, stops or closes; or, with none,
    a private loop of the call's own, started at its first awaitable on a daemon thread that
    owns the loop's whole life. `count` is told +1 and -1 as that thread starts and ends."""

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop | None = None,
        *,
        count: Callable[[int], Any] = lambda delta: None,
        start: Callable[[threading.Thread], Any] = threading.Thread.start,
    ) -> None:
        self._given = loop
        self._loop = loop
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._tasks: set[asyncio.Task[Any]] = set()  # the runner's own tasks still running
        self._count, self._start = count, start

    def _get(self) -> asyncio.AbstractEventLoop:
        if self._given is not None:
            return self._given
        with self._lock:
            if self._loop is not None:
                thread = self._thread
                if self._loop.is_closed() or thread is None or not thread.is_alive():
                    raise RuntimeError("the call's tool loop has stopped")
                return self._loop
            loop = asyncio.new_event_loop()
            thread = threading.Thread(
                target=self._serve, args=(loop,), name=_LOOP_THREAD, daemon=True
            )
            self._count(1)
            try:
                self._start(thread)
            except BaseException:  # the operating system's thread limit: a fault of the call
                self._count(-1)
                loop.close()
                raise
            self._loop, self._thread = loop, thread
            return loop

    def _serve(self, loop: asyncio.AbstractEventLoop) -> None:
        """The private loop's thread: run the loop until it stops, however it stops, then cancel
        what is left, run it down, shut the async generators down and close the loop."""
        try:
            try:
                loop.run_forever()
            except BaseException:  # a task the tool spawned raised KeyboardInterrupt, say
                pass
            finally:
                try:
                    try:
                        tasks = asyncio.all_tasks(loop)
                        for task in tasks:
                            task.cancel()
                        if tasks:
                            gathered = asyncio.gather(*tasks, return_exceptions=True)
                            loop.run_until_complete(gathered)
                        loop.run_until_complete(loop.shutdown_asyncgens())
                    finally:
                        loop.close()
                except BaseException:
                    pass
        finally:
            self._count(-1)

    def run(self, awaitable: Any, ops: _Ops | None = None) -> Any:
        """Await `awaitable` on the loop, from the work thread, and give its result or raise
        what it raised. Raises `_NotStarted` when the call was answered before it started."""
        post = _Post(awaitable)
        try:
            if ops is not None and not ops.post(post):
                raise _NotStarted
            loop = self._get()
            post.loop = loop
            wrapper = self._wrapper(post, ops)
            try:
                future = asyncio.run_coroutine_threadsafe(wrapper, loop)
            except BaseException:
                wrapper.close()
                raise
        except BaseException:
            _close_awaitable(awaitable)
            raise
        thread = self._thread if self._given is None else None
        while not post.ended.wait(_LOOP_POLL_S):
            # `future.done()` first, then `ended`: the wrapper sets `ended` in its `finally`
            # before its task completes, so a done future with `ended` unset is a wrapper whose
            # body never ran. Read in this order, neither fact can go
            # stale (a `started` read before them could).
            if future.done() and not post.ended.is_set():
                _close_awaitable(awaitable)
                raise asyncio.CancelledError("cancelled before it started")
            if loop.is_closed() or (thread is not None and not thread.is_alive()):
                if post.ended.is_set():
                    break
                if not (post.started if ops is None else ops.started(post)):
                    _close_awaitable(awaitable)
                raise RuntimeError("the call's tool loop has stopped")
        if post.skipped:
            raise _NotStarted
        if post.error is not None:
            raise post.error
        if not post.returned:  # the wrapper ended with neither a return nor an error
            raise RuntimeError("the awaitable ended without a result")
        return post.value

    async def _wrapper(self, post: _Post, ops: _Ops | None) -> None:
        try:
            try:
                task = typing.cast("asyncio.Task[Any]", asyncio.current_task())  # run as a task
                if ops is None:
                    post.started, post.task = True, task
                    go = True
                else:
                    go = ops.start(task)  # one acquisition of the bound's lock
            except GeneratorExit:
                raise
            except BaseException as e:  # a fault of the runner's own: kept in the call
                post.error = e
                return
            if not go:
                post.skipped = True
                return
            with self._lock:
                self._tasks.add(task)
            try:
                post.value = await post.awaitable
                post.returned = True
            except GeneratorExit as e:  # kept, so the record names it;
                post.error = e  # re-raised, so the wrapper's own close path is unchanged
                raise
            except BaseException as e:  # KeyboardInterrupt and SystemExit stay in the call
                post.error = e
            finally:
                with self._lock:
                    self._tasks.discard(task)
        finally:
            if not post.started:
                _close_awaitable(post.awaitable)
            post.ended.set()

    def cancel_tasks(self) -> None:
        """At a session's turn's end: the runner's own tasks still pending
        are asked to cancel, on the loop's thread; the loop itself lives on for the next turn.
        Never waits, raises, logs or warns."""
        try:
            loop = self._loop
            if loop is None or loop.is_closed():
                return
            with self._lock:
                tasks = list(self._tasks)
            for task in tasks:
                loop.call_soon_threadsafe(task.cancel)
        except BaseException:
            pass

    def close(self) -> None:
        """At the call's end, never waiting: a private loop is asked to stop, and its thread
        runs it down and closes it; on the caller's loop only the runner's own tasks are asked
        to cancel. A closed loop is skipped; nothing raises, logs or warns."""
        try:
            loop = self._loop
            if loop is None or loop.is_closed():
                return
            if self._given is None:
                thread = self._thread
                if thread is not None and thread.is_alive():
                    loop.call_soon_threadsafe(loop.stop)
                return
            with self._lock:
                tasks = list(self._tasks)
            for task in tasks:
                loop.call_soon_threadsafe(task.cancel)
        except BaseException:
            pass


class _Ops:
    """What the work of one bounded call may ask its bound about its awaitables."""

    __slots__ = ("_bound", "_slot")

    def __init__(self, bound: _Bounded, slot: _Slot) -> None:
        self._bound, self._slot = bound, slot

    def post(self, post: _Post) -> bool:
        """Before posting: False if the call was answered (nothing is posted)."""
        with self._bound._lock:
            if self._slot.abandoned:
                return False
            self._slot.post = post
            return True

    def start(self, task: Any) -> bool:
        return self._bound._begin(self._slot, task)

    def started(self, post: _Post) -> bool:
        with self._bound._lock:
            return post.started

    def ending(self) -> str | None:
        return self._bound._ended()


class _Slot:
    """One tool call's result: filled by its own thread, read by its own call only, so a late
    result of an abandoned call is dropped, never delivered to a later one."""

    __slots__ = ("abandoned", "done", "fault", "filled", "finished", "post", "started")

    def __init__(self) -> None:
        self.filled = threading.Event()
        self.done: _Done | None = None
        self.fault: str | None = None  # the work raised past its own catch-all, or never started
        self.started = False  # its thread was started
        self.finished = False  # set under the bound's lock, as its thread ends
        self.abandoned = False  # set under the bound's lock, when the call was answered without it
        self.post: _Post | None = None  # the awaitable the work posted last


class _Bounded:
    """The bounded invoke: the work of one tool call runs on a new daemon
    thread, in a copy of the door thread's context, while the door thread waits beside it in
    slices of one tick. The call ends at the first of: the work's answer; a pending Ctrl-C or
    the call's `cancel` (`cancelled`); the call's deadline less two ticks, read from the ticker
    as the poll's waits read it, or the tool's `timeout_s` (`timeout`). A call left running is
    abandoned: its thread runs to its end unseen, and its result is dropped. One call may hold
    `_MAX_ABANDONED` of them, and the process `_MAX_ABANDONED_IN_PROCESS`; while either is
    full, a call's next tool call is answered `timeout` at once. With neither a `timeout_s` nor
    a deadline, a call waits at most `wait_s`: a session's lifetime, else `_TOOL_WAIT_CEILING`.

    Everything it needs is injected, so the judge drives it with fakes: `ticks` (the epoch
    ticker's count), `ctrl_c` (whether a Ctrl-C is pending; read, never cleared), `count` (told
    +1 and -1 as tool threads start and end), `abandoned` (told +1 and -1 as threads are
    abandoned and end, and answering the process's count after the change; it may be called
    under the bound's own lock, so it takes only a leaf), `start` (starts a thread) and `clock`
    (for `timeout_s`). It never raises an `Exception`: a thread that cannot start, or a fault of its
    own, is a `tool_error` answer that keeps the call and its tool in the record."""

    def __init__(
        self,
        *,
        tick_s: float,
        stop_at: int | None = None,
        ticks: Callable[[], int] | None = None,
        cancel: threading.Event | None = None,
        ctrl_c: Callable[[], bool] | None = None,
        count: Callable[[int], Any] = lambda delta: None,
        abandoned: Callable[[int], int] = lambda delta: 0,
        start: Callable[[threading.Thread], Any] = threading.Thread.start,
        clock: Callable[[], float] = time.monotonic,
        context: Callable[[], contextvars.Context] = contextvars.copy_context,
        wait_s: float | None = None,
    ) -> None:
        self._tick, self._stop_at, self._ticks = tick_s, stop_at, ticks
        self._wait_s = _TOOL_WAIT_CEILING if wait_s is None else wait_s
        self._cancel, self._ctrl_c, self._count = cancel, ctrl_c, count
        self._in_process = abandoned
        self._start, self._clock = start, clock
        self._context = context  # where a call's context is copied: the home thread
        self._lock = threading.Lock()
        self._abandoned = 0  # this call's threads still running after their call was answered

    def rearm(
        self,
        stop_at: int | None,
        cancel: Any,
        context: Callable[[], contextvars.Context] | None = None,
    ) -> None:
        """A session's next turn: its deadline and stop, and where its
        tool calls copy their context. The count of abandoned threads carries over, so
        it bounds the whole session, not each turn."""
        with self._lock:
            self._stop_at, self._cancel = stop_at, cancel
            if context is not None:
                self._context = context

    def _ended(self) -> str | None:
        """'cancelled' or 'deadline' when the run is ending, else None."""
        if self._ctrl_c is not None and self._ctrl_c():
            return "cancelled"
        if self._cancel is not None and self._cancel.is_set():
            return "cancelled"
        if self._stop_at is not None and self._ticks is not None:
            if self._ticks() >= self._stop_at - _DEADLINE_MARGIN_TICKS:
                return "deadline"
        return None

    def __call__(self, work: _Work) -> _Done | _Interrupted:
        name = work.tool.name
        internal = f"{name} failed (internal error)"
        slot: _Slot | None = None
        try:
            ended = self._ended()
            if ended == "cancelled":
                return _Interrupted("cancelled", False, f"{name} was cancelled")
            if ended == "deadline":
                too_near = f"{name} timed out: the run's deadline is too near to start it"
                return _Interrupted("timeout", False, too_near)
            with self._lock:
                full = self._abandoned >= _MAX_ABANDONED
            if full:
                busy = f"{name} timed out: {_MAX_ABANDONED} earlier tool calls are still running"
                return _Interrupted("timeout", False, busy)
            if self._in_process(0) >= _MAX_ABANDONED_IN_PROCESS:
                busy = (
                    f"{name} timed out: {_MAX_ABANDONED_IN_PROCESS} abandoned tool calls are "
                    "still running in this process"
                )
                return _Interrupted("timeout", False, busy)
            slot = _Slot()
            if not self._started(work, slot):
                return work.failed("tool_error", internal, slot.fault)
            return self._wait(work, slot)
        except Exception as e:
            fault = _fault(e)
            if slot is None or not slot.started:
                return work.failed("tool_error", internal, fault)
            if not self._abandon(slot):  # the work had finished: its answer stands
                return self._delivered(work, slot)
            return _Interrupted("tool_error", True, internal, fault)

    def _started(self, work: _Work, slot: _Slot) -> bool:
        """Start the work's thread; False, with the fault in the slot, if it cannot start."""
        context = self._context()

        def target() -> None:
            try:
                try:
                    proceed = functools.partial(self._proceed, slot)
                    slot.done = context.run(work, proceed, _Ops(self, slot))
                except BaseException as e:  # _Work catches its own; this is a last resort
                    slot.fault = _fault(e)
                slot.filled.set()
            finally:
                with self._lock:
                    slot.finished = True
                    if slot.abandoned:
                        self._abandoned -= 1
                        self._in_process(-1)
                self._count(-1)

        self._count(1)
        try:
            thread = threading.Thread(
                target=target, name=f"wasi-python-tool-{work.tool.name}", daemon=True
            )
            self._start(thread)
        except Exception as e:  # the operating system's thread limit
            self._count(-1)
            slot.fault = _fault(e)
            return False
        slot.started = True
        return True

    def _proceed(self, slot: _Slot) -> bool:
        """Whether the tool may start: False once the call was answered without it. Taken under
        the lock `_abandon` takes, so a call is either answered before its tool starts (the tool
        never runs) or after (it runs on, abandoned)."""
        with self._lock:
            return not slot.abandoned

    def _abandon(self, slot: _Slot) -> bool:
        """Mark the call answered without its work; False if the work had already finished or
        filled its slot (its thread may not have reached its `finally` yet),
        so its answer stands and nothing is counted. An awaitable it had started is asked
        to cancel; one not yet started sees the answer at its first step."""
        with self._lock:
            if slot.finished or slot.filled.is_set():
                return False
            slot.abandoned = True
            self._abandoned += 1
            self._in_process(1)
            started = (post := slot.post) is not None and post.started
        if started and post is not None:
            _cancel_post(post)
        return True

    def _begin(self, slot: _Slot, task: Any) -> bool:
        """The wrapper's first step: in one acquisition of the lock, check that the call is
        unanswered (the admission predicate), mark its awaitable started and record its task.
        Never built on `_proceed`, which takes the lock itself."""
        with self._lock:
            post = slot.post
            if slot.abandoned or post is None:
                return False
            post.started, post.task = True, task
            return True

    def _wait(self, work: _Work, slot: _Slot) -> _Done | _Interrupted:
        name, timeout = work.tool.name, work.tool.timeout_s
        if timeout is None and self._stop_at is None:  # nothing else bounds the wait
            timeout = self._wait_s
        until = None if timeout is None else self._clock() + timeout
        while True:
            pause = self._tick
            if until is not None:
                pause = max(0.0, min(pause, until - self._clock()))
            if slot.filled.wait(pause):
                return self._delivered(work, slot)
            ended = self._ended()
            if ended is None and until is not None and self._clock() >= until:
                ended = "timeout"
            if ended is None:
                continue
            if not self._abandon(slot):  # it finished just now: its answer stands
                return self._delivered(work, slot)
            if ended == "cancelled":
                return _Interrupted("cancelled", True, f"{name} was cancelled")
            if ended == "deadline":
                return _Interrupted("timeout", True, f"{name} timed out at the run's deadline")
            return _Interrupted("timeout", True, f"{name} timed out after {timeout:g} s")

    @staticmethod
    def _delivered(work: _Work, slot: _Slot) -> _Done:
        if slot.done is not None:
            return slot.done
        return work.failed("tool_error", f"{work.tool.name} failed (internal error)", slot.fault)


class _ToolHost:
    """The frame host: answers one call's protocol frames and keeps its counters and record.

    `admit(length)` is called with a frame's length before its bytes are read (the door
    does); `__call__(frame)` answers the frame. A raw `host=` calls only `__call__`, which then
    admits the frame itself, so every frame is counted exactly once. Nothing a frame, a gate or
    a tool does raises out of either."""

    def __init__(
        self,
        tools: Iterable[Tool],
        *,
        gate: Callable[[ToolCall], Any] | None = None,
        max_calls: int | None = 1000,
        invoke: Callable[[_Work], _Done | _Interrupted] = _inline,
        tool_loop: _ToolLoop | None = None,
        max_bytes: int | None = None,
    ) -> None:
        self._tools = tuple(tools)
        for t in self._tools:
            if not isinstance(t, Tool):
                raise TypeError(f"a frame host serves Tools; got {type(t).__name__}")
        self._by_name = {t.name: t for t in self._tools}
        if len(self._by_name) != len(self._tools):
            raise ValueError("two tools share a name")
        self._descriptors = [t.descriptor() for t in self._tools]
        self._gate, self._max_calls, self._invoke = gate, max_calls, invoke
        self._loop = tool_loop if tool_loop is not None else _ToolLoop()
        self._frames = 0
        self._abandoned = 0  # calls answered while their tool ran on, listed or not
        self._outcomes: list[ToolOutcome] = []
        self._pending: tuple[int, int] | None = None  # (seq, length) admitted, not yet read
        self._size = 0
        # The bytes of the frames admitted, whatever their answer, against max_bytes
        # (None: no limit; the runner passes the call's own); and the tool list, encoded once.
        self._max_bytes = max_bytes
        self._admitted = 0
        self._tools_json: bytes | None = None

    def close(self) -> None:
        """End the call's tool loop without waiting. Never raises."""
        self._loop.close()

    @property
    def record(self) -> ToolRecord:
        return ToolRecord(
            frames=self._frames,
            outcomes=tuple(self._outcomes),
            unlisted=self._frames - len(self._outcomes),
            abandoned=self._abandoned,
        )

    def _note(self, outcome: ToolOutcome) -> None:
        if outcome.abandoned:
            self._abandoned += 1
        if len(self._outcomes) < _RECORD_OUTCOMES:
            self._outcomes.append(outcome)

    def admit(self, length: int) -> bytes | None:
        """Count a frame from its length alone: an answer for one past `max_calls`, over the
        cap, or past `max_bytes`, else None; then the length counts against
        `max_bytes` and is kept for `__call__` to check."""
        self._frames += 1
        seq = self._frames
        self._pending = None
        answer = None
        if self._max_calls is not None and seq > self._max_calls:
            kind = "budget_exceeded"
            message = f"this run allows {self._max_calls} tool frames; this was frame {seq}"
        elif length > _TOOL_REQUEST_BYTES:
            kind = "too_large"
            message = f"the frame is {length} bytes; at most {_TOOL_REQUEST_BYTES} (1 MiB)"
        elif self._max_bytes is not None and self._admitted + length > self._max_bytes:
            kind = "budget_exceeded"
            message = (
                f"this run allows {self._max_bytes} bytes of tool requests; "
                f"{self._admitted} are used, and this frame is {length}"
            )
        else:
            self._admitted += length
            self._pending = (seq, length)
            return None
        answer = _error(None, kind, message)
        self._note(ToolOutcome(seq, None, None, kind, message, length, len(answer)))
        return answer

    def __call__(self, frame: bytes) -> bytes:
        if not isinstance(frame, (bytes, bytearray, memoryview)):
            frame = b""  # a runner bug: answered as an empty frame, never raised
        frame = bytes(frame)
        if self._pending is None:
            early = self.admit(len(frame))
            if early is not None:
                return early
        assert self._pending is not None
        seq, admitted = self._pending
        self._pending = None
        self._size = len(frame)
        if admitted != len(frame):
            message = f"the door admitted {admitted} bytes but passed {len(frame)}"
            answer = _error(None, "protocol", message)
            fault = f"RuntimeError: {message}"
            self._note(
                ToolOutcome(seq, None, None, "protocol", message, len(frame), len(answer), fault)
            )
            return answer
        try:
            return self._answer(seq, frame)
        except Exception as e:  # a bug here must not reach the guest's door as a fault
            message = "the host could not answer this frame (internal error)"
            answer = _error(None, "protocol", message)
            self._note(
                ToolOutcome(
                    seq, None, None, "protocol", message, len(frame), len(answer), _fault(e)
                )
            )
            return answer

    def _list_answer(self, frame_id: int | None) -> bytes:
        """`_encode` of the list answer, byte for byte, with the descriptors encoded once, at the
        first `list` frame, and the id spliced in: a guest that lists
        again and again no longer makes the host encode the list again."""
        return b"".join((*self._list_head(frame_id), self._tools_array(), b"}"))

    def _tools_array(self) -> bytes:
        """The descriptors array as `_encode` writes it, encoded at the first need and kept."""
        if self._tools_json is None:
            whole = _encode({"tools": self._descriptors})
            self._tools_json = whole[len(b'{"tools":') : -1]
        return self._tools_json

    @staticmethod
    def _list_head(frame_id: int | None) -> tuple[bytes, ...]:
        """The list answer's parts before its array: one source for its bytes and its length."""
        shown = b"null" if frame_id is None else str(frame_id).encode("ascii")
        version = str(PROTOCOL).encode("ascii")
        return (b'{"v":', version, b',"id":', shown, b',"ok":true,"tools":')

    def _list_length(self, frame_id: int | None) -> int:
        """The exact length of `_list_answer(frame_id)`, from its parts, without building it, so
        a list over the answer cap is refused before it is copied."""
        head = sum(len(part) for part in self._list_head(frame_id))
        return head + len(self._tools_array()) + len(b"}")

    def _answer(self, seq: int, frame: bytes) -> bytes:
        """The envelope of a frame: it parses, its id and version, its operation and, for a
        call, the tool it names; the call itself is `_call_answer`'s. `failed` notes an outcome
        with the operation and the name this frame has reached, read when it is called, so both
        are bound here before the call is handed on."""
        size = len(frame)
        op = name = None

        def failed(kind: str, message: str, frame_id: Any = None) -> bytes:
            answer = _error(frame_id, kind, message)
            self._note(ToolOutcome(seq, op, name, kind, _bounded(message), size, len(answer), None))
            return answer

        try:
            request = _parse(frame)
        except _Refused as e:
            return failed("protocol", str(e))
        frame_id = request.get("id")
        if type(frame_id) is not int or not 0 <= frame_id <= _MAX_ID:
            frame_id = None
        version = request.get("v")
        if type(version) is not int or version not in _PROTOCOLS:
            served = ", ".join(str(v) for v in _PROTOCOLS)
            return failed(
                "protocol",
                f"this host serves protocol version {served}; the frame asks for "
                f"{_tool_schema._echo(version) if 'v' in request else 'none'}",
                frame_id,
            )
        raw_op = request.get("op")
        if raw_op == "list":
            op = "list"
            if self._list_length(frame_id) > _TOOL_RESPONSE_BYTES:  # refused before it is built
                return failed("too_large", "the tool list is over the 16 MiB cap", frame_id)
            answer = self._list_answer(frame_id)
            self._note(ToolOutcome(seq, op, None, "ok", None, size, len(answer)))
            return answer
        if raw_op != "call":
            reserved = " (batch is reserved for a later version)" if raw_op == "batch" else ""
            return failed(
                "protocol",
                f"unknown operation {_tool_schema._echo(raw_op)}; "
                f"this host serves list and call{reserved}",
                frame_id,
            )
        op = "call"
        raw_name = request.get("tool")
        if not isinstance(raw_name, str):
            return failed("protocol", "a call names its tool with a string", frame_id)
        name = raw_name[:_ECHO_CHARS]
        t = self._by_name.get(raw_name)
        if t is None:
            offered = ", ".join(self._by_name) or "none"
            return failed(
                "unknown_tool",
                f"no tool named {_tool_schema._echo(raw_name)}; this run offers: {offered}",
                frame_id,
            )
        return self._call_answer(seq, t, name, request, frame_id, size, failed)

    def _call_answer(
        self,
        seq: int,
        t: Tool,
        name: str,
        request: _Json,
        frame_id: int | None,
        size: int,
        failed: Callable[..., bytes],
    ) -> bytes:
        """A call's answer once its tool is found: the arguments checked against its schema
        and its bound keywords, then the work invoked and its outcome noted, once."""
        op = "call"
        args = request.get("args", {})
        if not isinstance(args, dict):
            return failed(
                "invalid_arguments", f"{t.name}: the arguments must be an object", frame_id
            )
        error = _Validator(t._input_schema, keysets=t._keysets).check(args)
        if error is not None:
            return failed("invalid_arguments", f"{t.name}: {error}", frame_id)
        for k in args:
            if k in t._fixed:  # an open schema let a bound keyword through: refused as unknown
                message = (
                    f"{t.name}: {_tool_schema._where(None)}: unknown argument "
                    f"{_tool_schema._echo(k)}"
                )
                return failed("invalid_arguments", message, frame_id)
        work = _Work(self, seq, frame_id, t, args)
        done = self._invoke(work)
        if isinstance(done, _Interrupted):
            what = "timed out" if done.kind == "timeout" else "was cancelled"
            message = _bounded(done.message or f"{t.name} {what}")
            answer = _error(frame_id, done.kind, message)
            self._note(
                ToolOutcome(
                    seq, op, name, done.kind, message, size, len(answer), done.fault, done.abandoned
                )
            )
            return answer
        self._note(
            ToolOutcome(
                seq, op, name, done.outcome, done.message, size, len(done.answer), done.fault
            )
        )
        return done.answer
