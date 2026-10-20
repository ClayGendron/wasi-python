"""Async tools and gates (spec 053), with no guest: an awaitable a tool or a gate returns is
awaited on the tool loop (a loop the check owns stands for `run_async`'s caller's loop; with none
given, the call's own private loop), it starts only at its wrapper's first step, every end
cancels a started task, faults stay in the record, and the call's loop is closed at its end.

Fakes stand in for the ticker, `cancel`, the Ctrl-C flag and the clock. Nothing here measures
time: a tool that must wait awaits an event the check sets, a fake clock or ticker moves an end
only once the tool says it has started, and every `join(60)` or `wait(60)` is a fail-safe."""

from __future__ import annotations

import asyncio
import concurrent.futures
import contextvars
import functools
import gc
import inspect
import json
import logging
import threading
import warnings
from collections.abc import Iterator
from typing import Any

import pytest

from wasi_python import _artifacts, _call, _home, runner
from wasi_python import tools as T
from wasi_python.tools import ToolDenied, ToolError, tool

LOOP_THREAD = "wasi-python-tool--loop"
REQUEST = contextvars.ContextVar("request", default="unset")


def call_frame(name: str, args: Any = None, id: int = 1) -> bytes:
    return json.dumps({"v": 1, "id": id, "op": "call", "tool": name, "args": args or {}}).encode()


def answer(raw: bytes) -> tuple[str, Any]:
    a = json.loads(raw)
    return ("ok", a["value"]) if a["ok"] else (a["error"]["kind"], a["error"]["message"])


def kind(raw: bytes) -> str:
    return answer(raw)[0]


class Ticks:
    def __init__(self, n: int = 0) -> None:
        self.n = n

    def __call__(self) -> int:
        return self.n


class Clock:
    """A fake clock for `timeout_s`. A call's first read, from which the bound sets the call's
    end, gives 0; every later read gives 9, past that end, once `moved()` is true. `arm()` makes
    the next read a first read again, for the next call."""

    def __init__(self, moved: Any) -> None:
        self.moved, self.fresh = moved, True

    def arm(self) -> None:
        self.fresh = True

    def __call__(self) -> float:
        if self.fresh:
            self.fresh = False
            return 0.0
        return 9.0 if self.moved() else 0.0


class CallerLoop:
    """A running loop on a thread the check owns, standing for `run_async`'s caller's loop."""

    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, name="caller-loop")
        self.thread.daemon = True
        self.thread.start()

    def run(self, coro: Any) -> Any:
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result(60)

    def close(self) -> None:
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(60)
        self.loop.close()


@pytest.fixture
def caller() -> Iterator[CallerLoop]:
    c = CallerLoop()
    yield c
    c.close()


def _join_tool_threads() -> None:
    for t in threading.enumerate():
        if t.name.startswith("wasi-python-tool-"):
            t.join(60)  # a fail-safe, not a timing


@pytest.fixture(autouse=True)
def joined() -> Iterator[None]:
    yield
    _join_tool_threads()


def _host(tools: list, *, gate=None, loop=None, start=None, **kw) -> Any:
    """A frame host with spec 036's bound and spec 053's tool loop, both counting their threads
    into `host.counted`."""
    counted: list = []
    bound = T._Bounded(tick_s=0.001, count=counted.append, **kw)
    extra = {} if start is None else {"start": start}
    tool_loop = T._ToolLoop(loop, count=counted.append, **extra)
    host = T._ToolHost(tools, gate=gate, invoke=bound, tool_loop=tool_loop)
    host.counted, host.bound = counted, bound
    return host


def _last(host: Any) -> T.ToolOutcome:
    return host.record.outcomes[-1]


def _loop_threads() -> set[threading.Thread]:
    return {t for t in threading.enumerate() if t.name == LOOP_THREAD}


# -------------------------------------------------------------------------------------------------
# Criterion 1: async callables are accepted, async generators and an async host= refused.


async def fetch(code: str, n: int = 1) -> dict:
    """Fetch a region.

    Args:
        code: The region code.
    """
    return {"code": code, "n": n}


def fetch_twin(code: str, n: int = 1) -> dict:
    """Fetch a region.

    Args:
        code: The region code.
    """
    return {"code": code, "n": n}


class AsyncCall:
    async def __call__(self, code: str) -> str:
        """Answer asynchronously."""
        return code


async def streams(code: str):
    yield code


async def async_gate(call: Any) -> bool:
    return True


async def agen_gate(call: Any):
    yield True


async def async_host(frame: bytes) -> bytes:
    return frame


async def agen_host(frame: bytes):
    yield frame


class AsyncHost:
    async def __call__(self, frame: bytes) -> bytes:
        return frame


class Reached(Exception):
    pass


class Recording(concurrent.futures.Executor):
    def __init__(self) -> None:
        self.submitted: list[Any] = []

    def submit(self, fn, /, *args, **kwargs):
        self.submitted.append(fn)
        raise Reached("submit")


def test_async_callables_are_accepted_and_async_generators_refused(monkeypatch) -> None:
    assert tool(fetch).descriptor() == tool(fetch_twin, name="fetch").descriptor()
    assert tool(functools.partial(fetch), name="pfetch").name == "pfetch"
    assert tool(AsyncCall(), name="acall").input_schema["properties"] == {
        "code": {"type": "string"}
    }
    with pytest.raises(TypeError, match="streams: an async generator streams"):
        tool(streams)

    lookups: list = []

    def found():
        lookups.append(1)
        raise Reached("lookup")

    monkeypatch.setattr(_artifacts, "find_artifacts", found)
    lookup = tool(fetch_twin, name="lookup")

    # A coroutine gate passes the checks: the first lookup, or the executor's submit, is reached.
    with pytest.raises(Reached, match="lookup"):
        runner.run(["-c", "pass"], tools=[lookup], gate=async_gate)
    ex = Recording()
    with pytest.raises(Reached, match="submit"):
        asyncio.run(runner.run_async(["-c", "pass"], tools=[lookup], gate=async_gate, executor=ex))
    assert (len(lookups), len(ex.submitted)) == (1, 1)

    refused = [
        ({"tools": [lookup], "gate": agen_gate}, "async generator"),
        ({"host": async_host}, "serve an async host function as a tool"),
        ({"host": agen_host}, "serve an async host function as a tool"),
        ({"host": AsyncHost()}, "serve an async host function as a tool"),
        ({"host": functools.partial(async_host)}, "serve an async host function as a tool"),
    ]
    for kw, match in refused:
        lookups.clear()
        ex = Recording()
        with pytest.raises(TypeError, match=match):
            runner.run(["-c", "pass"], **kw)
        with pytest.raises(TypeError, match=match):
            asyncio.run(runner.run_async(["-c", "pass"], executor=ex, **kw))
        assert (lookups, ex.submitted) == ([], []), kw


# -------------------------------------------------------------------------------------------------
# Criterion 2: an awaitable is awaited on the tool loop.


async def where() -> dict:
    """Say where it runs."""
    await asyncio.sleep(0)
    return {"thread": threading.current_thread().name, "request": REQUEST.get()}


def test_an_awaitable_is_awaited_on_the_tool_loop(caller) -> None:
    def adapter() -> dict:
        """A plain function returning a coroutine."""
        return where()

    ran: list = []

    @tool
    def counted() -> int:
        """Count."""
        ran.append(1)
        return len(ran)

    async def refuse(call: Any) -> bool:
        return False

    async def allow(call: Any) -> bool:
        return True

    host = _host([tool(where), tool(adapter, name="adapter")], loop=caller.loop)
    REQUEST.set("from the caller")
    want = {"thread": "caller-loop", "request": "from the caller"}
    assert answer(host(call_frame("where"))) == ("ok", want)
    assert answer(host(call_frame("adapter"))) == ("ok", want)

    host = _host([counted], gate=refuse, loop=caller.loop)
    assert answer(host(call_frame("counted"))) == ("denied", "counted was refused")
    assert ran == []
    host = _host([counted], gate=allow, loop=caller.loop)
    assert answer(host(call_frame("counted"))) == ("ok", 1)

    # With no loop given: one private loop thread, started at the first awaitable.
    before = _loop_threads()
    host = _host([counted, tool(where)])
    assert answer(host(call_frame("counted")))[0] == "ok"
    assert _loop_threads() - before == set()  # sync tools start no loop
    for _ in range(3):
        kind_, value = answer(host(call_frame("where")))
        assert (kind_, value["thread"]) == ("ok", LOOP_THREAD)
    assert len(_loop_threads() - before) == 1
    host.close()
    _join_tool_threads()
    assert _loop_threads() - before == set()
    assert host._loop._loop.is_closed()
    assert sum(host.counted) == 0


# -------------------------------------------------------------------------------------------------
# Criterion 3: every end cancels a started task.


def _waiter(started: threading.Event, cancels: list, then=None, timeout_s=None) -> T.Tool:
    @tool(name="wait", timeout_s=timeout_s)
    async def wait() -> int:
        """Wait for ever."""
        started.set()
        if then is not None:
            then()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancels.append(1)
            raise
        return 1

    return wait


def test_every_end_cancels_a_started_task(caller, monkeypatch) -> None:
    started, cancels = threading.Event(), []

    def check(host: Any, want: str) -> None:
        assert kind(host(call_frame("wait"))) == want
        assert _last(host).abandoned is True
        _join_tool_threads()
        assert cancels == [1], cancels
        assert sum(host.counted) == 0
        cancels.clear()
        started.clear()

    # The tool's timeout_s, on a clock that moves only once the tool has started.
    clock = Clock(started.is_set)
    check(_host([_waiter(started, cancels, timeout_s=1.0)], loop=caller.loop, clock=clock),
          "timeout")  # fmt: skip

    # The deadline less two ticks, moved by the tool.
    ticks = Ticks(0)
    waiter = _waiter(started, cancels, then=lambda: setattr(ticks, "n", 8))
    check(_host([waiter], loop=caller.loop, stop_at=10, ticks=ticks), "timeout")

    # The call's cancel, set by the tool.
    cancel = threading.Event()
    check(_host([_waiter(started, cancels, then=cancel.set)], loop=caller.loop, cancel=cancel),
          "cancelled")  # fmt: skip

    # A pending Ctrl-C, through the runner's own wiring, on a private loop.
    monkeypatch.setattr(_home, "_ctrl_c_watched", lambda: True)
    monkeypatch.setitem(_home._ctrl_c, "pending", False)
    before = runner.stats()["tool_threads_running"]
    waiter = _waiter(started, cancels, then=lambda: _home._ctrl_c.__setitem__("pending", True))
    host = _call._tool_host({"tools": (waiter,), "gate": None, "tool_calls": 1000}, None, None)
    assert kind(host(call_frame("wait"))) == "cancelled"
    assert _last(host).abandoned is True
    host.close()
    _join_tool_threads()
    assert cancels == [1]
    assert runner.stats()["tool_threads_running"] == before
    assert _home._ctrl_c["pending"] is True


# -------------------------------------------------------------------------------------------------
# Criterion 4: a task that ignores its cancel holds its slot.


def test_a_task_that_ignores_its_cancel_holds_its_slot(caller) -> None:
    starts: list = []
    release = asyncio.Event()

    @tool(name="stubborn", timeout_s=1.0)
    async def stubborn() -> int:
        """Ignore every cancel until released."""
        starts.append(1)
        while True:
            try:
                await release.wait()
                return 1
            except asyncio.CancelledError:
                continue

    # Each call's end comes once its own tool has started.
    seen = [0]
    clock = Clock(lambda: len(starts) > seen[0])
    host = _host([stubborn], loop=caller.loop, clock=clock)
    answers = []
    for _ in range(6):
        clock.arm()
        seen[0] = len(starts)
        answers.append(answer(host(call_frame("stubborn"))))
    assert (
        answers
        == [("timeout", "stubborn timed out after 1 s")] * 4
        + [("timeout", "stubborn timed out: 4 earlier tool calls are still running")] * 2
    )
    assert [o.abandoned for o in host.record.outcomes] == [True] * 4 + [False] * 2
    assert len(starts) == 4
    assert sum(host.counted) == 4
    caller.loop.call_soon_threadsafe(release.set)
    _join_tool_threads()
    assert sum(host.counted) == 0


# -------------------------------------------------------------------------------------------------
# Criterion 5: an answered call starts no awaitable (the review's F1, the Confirmation's C-2).


@pytest.fixture
def posted(monkeypatch) -> threading.Event:
    """Set once the runner has posted a wrapper to a loop."""
    event = threading.Event()
    real = asyncio.run_coroutine_threadsafe

    def post(coro, loop):
        future = real(coro, loop)
        event.set()
        return future

    monkeypatch.setattr(T.asyncio, "run_coroutine_threadsafe", post)
    return event


def test_an_answered_call_starts_no_awaitable(caller, posted) -> None:
    runs: list = []
    coros: list = []

    async def body() -> int:
        runs.append(1)
        return 1

    def pay() -> int:
        """Pay, asynchronously."""
        coros.append(body())
        return coros[-1]

    with warnings.catch_warnings(record=True) as seen:
        warnings.simplefilter("always")
        # The loop is busy when the post arrives; the call's end comes once the post is made.
        blocking, blocker = threading.Event(), threading.Event()

        def block() -> None:
            blocking.set()
            blocker.wait(60)

        caller.loop.call_soon_threadsafe(block)
        assert blocking.wait(60)
        host = _host([tool(pay, timeout_s=1.0)], loop=caller.loop,
                     clock=Clock(posted.is_set))  # fmt: skip
        assert kind(host(call_frame("pay"))) == "timeout"
        assert _last(host).abandoned is True
        blocker.set()
        _join_tool_threads()
        assert runs == []
        assert inspect.getcoroutinestate(coros[-1]) == inspect.CORO_CLOSED

        # An async gate, the same way: the gate never runs, nor does the tool.
        posted.clear()
        gate_runs, tool_runs = [], []

        async def gate_body(call: Any) -> bool:
            gate_runs.append(1)
            return True

        def gate(call: Any) -> Any:
            coros.append(gate_body(call))
            return coros[-1]

        @tool(timeout_s=1.0)
        def plain() -> int:
            """Count."""
            tool_runs.append(1)
            return 1

        blocking.clear()
        blocker.clear()
        caller.loop.call_soon_threadsafe(block)
        assert blocking.wait(60)
        host = _host([plain], gate=gate, loop=caller.loop,
                     clock=Clock(posted.is_set))  # fmt: skip
        assert kind(host(call_frame("plain"))) == "timeout"
        blocker.set()
        _join_tool_threads()
        assert (gate_runs, tool_runs) == ([], [])
        assert inspect.getcoroutinestate(coros[-1]) == inspect.CORO_CLOSED

        # A coroutine held by the work thread when the call is answered: closed, never posted.
        posted.clear()
        entered, answered = threading.Event(), threading.Event()

        def late() -> int:
            """Return a coroutine only after the call was answered."""
            entered.set()
            answered.wait(60)
            coros.append(body())
            return coros[-1]

        host = _host([tool(late, timeout_s=1.0)], loop=caller.loop,
                     clock=Clock(entered.is_set))  # fmt: skip
        assert kind(host(call_frame("late"))) == "timeout"
        answered.set()
        _join_tool_threads()
        assert runs == [] and not posted.is_set()
        assert inspect.getcoroutinestate(coros[-1]) == inspect.CORO_CLOSED
        del coros[:]
        gc.collect()
    assert [w for w in seen if issubclass(w.category, RuntimeWarning)] == []


class CountingLock:
    """The bound's lock, counted, and never waited on for long: a second acquisition by the
    thread that holds it fails at once instead of hanging the check."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.acquired = 0

    def __enter__(self) -> CountingLock:
        if not self.lock.acquire(timeout=5):  # a fail-safe: a re-entry would deadlock
            raise AssertionError("the bound's lock was taken twice")
        self.acquired += 1
        return self

    def __exit__(self, *exc: object) -> None:
        self.lock.release()


def test_a_tool_that_ran_is_never_reported_as_not_started(caller, monkeypatch) -> None:
    """The build review's F1: the work thread's wait must not decide "cancelled before it
    started" from a read that went stale. The loop is busy when the post arrives, so the wait
    passes its first slice with `started` and `ended` both false. Then, inside the wait's first
    read of the posted future, the loop is released and the read returns only once the wrapper
    has run the tool to its end and the future has completed. The tool ran, so the call must be
    answered with its value; a wait that trusts a `started` read taken before that answers
    `tool_error`, "CancelledError: cancelled before it started"."""
    effects: list = []
    hold = threading.Event()
    real_post = asyncio.run_coroutine_threadsafe

    class Released:
        """The posted future, whose first `done()` lets the loop run the wrapper to its end."""

        def __init__(self, future: Any) -> None:
            self.future, self.first = future, True

        def done(self) -> bool:
            if self.first:
                self.first = False
                hold.set()
                concurrent.futures.wait([self.future], timeout=60)  # a fail-safe, not a timing
            return self.future.done()

    monkeypatch.setattr(
        T.asyncio, "run_coroutine_threadsafe", lambda coro, loop: Released(real_post(coro, loop))
    )

    @tool
    async def transfer(amount: int) -> str:
        """Move money."""
        effects.append(amount)
        return "done"

    caller.loop.call_soon_threadsafe(hold.wait, 60)  # busy when the post arrives
    host = _host([transfer], loop=caller.loop)
    assert answer(host(call_frame("transfer", {"amount": 100}))) == ("ok", "done")
    assert effects == [100]
    o = _last(host)
    assert (o.outcome, o.fault, o.abandoned) == ("ok", None, False)


def test_the_first_step_takes_the_lock_once() -> None:
    """The Confirmation's C-2: the wrapper's first step is one acquisition of the bound's lock
    that checks the call is unanswered, marks the start and records the task. Built from 056's
    self-locking `_proceed` it would deadlock; built from two acquisitions, an abandon could fall
    between them."""
    bound = T._Bounded(tick_s=0.001)
    bound._lock = CountingLock()
    task = object()

    slot = T._Slot()
    slot.post = T._Post(None)
    assert bound._begin(slot, task) is True
    assert (bound._lock.acquired, slot.post.started, slot.post.task) == (1, True, task)

    slot = T._Slot()
    slot.post = T._Post(None)
    assert bound._abandon(slot) is True
    bound._lock.acquired = 0
    assert bound._begin(slot, task) is False
    assert (bound._lock.acquired, slot.post.started, slot.post.task) == (1, False, None)


# -------------------------------------------------------------------------------------------------
# Criterion 6: a late gate skips an async tool (spec 056's rule, extended).


def test_a_late_gate_skips_an_async_tool(caller, posted) -> None:
    called: list = []

    async def body() -> str:
        return "sent"

    def transfer() -> str:
        """Move money."""
        called.append(1)
        return body()

    for gate_kind in ("sync", "async"):
        moved, answered = threading.Event(), threading.Event()
        posted.clear()

        def sync_gate(call: Any, moved=moved, answered=answered) -> bool:
            moved.set()
            answered.wait(60)
            return True

        async def late_gate(call: Any, moved=moved, answered=answered) -> bool:
            moved.set()
            await asyncio.to_thread(answered.wait, 60)
            return True

        gate = sync_gate if gate_kind == "sync" else late_gate
        host = _host([tool(transfer, timeout_s=1.0)], gate=gate, loop=caller.loop,
                     clock=Clock(moved.is_set))  # fmt: skip
        assert kind(host(call_frame("transfer"))) == "timeout"
        assert _last(host).abandoned is True
        posts_before_release = posted.is_set()
        answered.set()
        _join_tool_threads()
        assert called == [], gate_kind
        if gate_kind == "sync":
            assert not posted.is_set()  # the gate is sync: nothing was posted at all
        else:
            assert posts_before_release  # only the gate's own coroutine
        assert sum(host.counted) == 0


# -------------------------------------------------------------------------------------------------
# Criterion 7: faults in an awaitable stay in the record.


def test_faults_in_an_awaitable_stay_in_the_record(caller) -> None:
    def raising(exc: BaseException) -> T.Tool:
        @tool(name="boom")
        async def boom() -> int:
            """Raise."""
            raise exc

        return boom

    internal = ("tool_error", "boom failed (internal error)")
    cases = [
        (ToolError("no region"), ("tool_error", "no region"), None),
        (ToolDenied("not today"), ("denied", "not today"), None),
        (KeyError("/host/secret"), internal, "KeyError"),
        (KeyboardInterrupt(), internal, "KeyboardInterrupt"),
        (SystemExit(3), internal, "SystemExit"),
        (asyncio.CancelledError(), internal, "CancelledError"),
    ]
    for exc, want, fault in cases:
        host = _host([raising(exc)], loop=caller.loop)
        assert answer(host(call_frame("boom"))) == want, exc
        got = _last(host).fault
        assert (got or "").startswith(fault or "") and (fault is None) == (got is None), got
    assert caller.thread.is_alive()
    assert answer(_host([tool(where)], loop=caller.loop)(call_frame("where")))[0] == "ok"

    # An unrequested CancelledError while the run is being cancelled is answered `cancelled`.
    cancel = threading.Event()

    @tool(name="boom")
    async def cancelled_while_cancelling() -> int:
        """Raise CancelledError as the run is cancelled."""
        cancel.set()
        raise asyncio.CancelledError

    host = _host([cancelled_while_cancelling], loop=caller.loop, cancel=cancel)
    assert kind(host(call_frame("boom"))) == "cancelled"

    with warnings.catch_warnings(record=True) as seen:
        warnings.simplefilter("always")
        # A closed loop: answered at once, the awaitable closed.
        closed = asyncio.new_event_loop()
        closed.close()
        host = _host([tool(where)], loop=closed)
        assert kind(host(call_frame("where"))) == "tool_error"
        assert _last(host).fault.startswith("RuntimeError")

        # The private loop's thread cannot start.
        def refuse(thread: threading.Thread) -> None:
            raise RuntimeError("can't start new thread")

        host = _host([tool(where)], start=refuse)
        assert kind(host(call_frame("where"))) == "tool_error"
        assert _last(host).fault.startswith("RuntimeError")
        assert sum(host.counted) == 0

        # The Confirmation's C-1: the wrapper is cancelled before its first step, on a loop
        # that stays open. The callback below cancels the first task it finds, re-queueing
        # itself until the post has made one, so the cancel lands before the task's first step.
        coros: list = []
        runs: list = []

        async def body() -> int:
            runs.append(1)
            return 1

        def early() -> int:
            """Return a coroutine whose wrapper is cancelled before it starts."""
            coros.append(body())
            return coros[-1]

        def cancel_first() -> None:
            tasks = asyncio.all_tasks(caller.loop)
            if not tasks:
                caller.loop.call_soon(cancel_first)
            for t in tasks:
                t.cancel()

        caller.loop.call_soon_threadsafe(cancel_first)
        host = _host([tool(early, timeout_s=30)], loop=caller.loop)  # 30 s: a fail-safe
        assert kind(host(call_frame("early"))) == "tool_error"
        assert _last(host).fault.startswith("CancelledError")
        _join_tool_threads()
        assert (runs, sum(host.counted)) == ([], 0)
        assert inspect.getcoroutinestate(coros[-1]) == inspect.CORO_CLOSED
        assert caller.thread.is_alive() and not caller.loop.is_closed()
        del coros[:]
        gc.collect()
    assert [w for w in seen if issubclass(w.category, RuntimeWarning)] == []


# -------------------------------------------------------------------------------------------------
# Criterion 8: the call's loop, closed at its end; a loop that ends is closed and ends the wait.


class Records(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def test_close_ends_the_calls_loop(caller) -> None:
    cancels: list = []
    free = threading.Event()

    async def background() -> None:
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancels.append(1)
            raise

    async def ignoring() -> None:
        while not free.is_set():
            try:
                await asyncio.sleep(0.001)
            except asyncio.CancelledError:
                continue

    @tool
    async def spawn() -> int:
        """Spawn a task and return."""
        asyncio.get_running_loop().create_task(background())
        return 1

    @tool
    async def spawn_ignoring() -> int:
        """Spawn a task that ignores its cancel."""
        asyncio.get_running_loop().create_task(ignoring())
        return 1

    host = _host([spawn])
    assert kind(host(call_frame("spawn"))) == "ok"
    host.close()
    _join_tool_threads()
    assert cancels == [1]
    assert host._loop._loop.is_closed() and sum(host.counted) == 0

    before = _loop_threads()
    host = _host([spawn_ignoring])
    assert kind(host(call_frame("spawn_ignoring"))) == "ok"
    host.close()  # returns at once
    assert len(_loop_threads() - before) == 1
    free.set()
    _join_tool_threads()
    assert _loop_threads() - before == set()
    assert host._loop._loop.is_closed() and sum(host.counted) == 0

    # On the caller's loop, only the runner's own tasks: the check's own stays pending.
    mine = asyncio.run_coroutine_threadsafe(asyncio.Event().wait(), caller.loop)
    host = _host([tool(where)], loop=caller.loop)
    assert kind(host(call_frame("where"))) == "ok"
    host.close()
    assert not mine.done()
    mine.cancel()

    # cancel and close on a closed loop: nothing raised, logged or warned.
    handler = Records()
    logging.getLogger().addHandler(handler)
    try:
        with warnings.catch_warnings(record=True) as seen:
            warnings.simplefilter("always")
            closed = asyncio.new_event_loop()
            closed.close()
            tool_loop = T._ToolLoop(closed)
            tool_loop.close()
            post = T._Post(None)
            post.loop, post.started = closed, True
            post.task = asyncio.Future(loop=closed)
            T._cancel_post(post)

            # A loop that closes between the check and the call (the build review's N1).
            class Closing:
                def is_closed(self) -> bool:
                    return False

                def call_soon_threadsafe(self, *args: Any) -> None:
                    raise RuntimeError("Event loop is closed")

            post.loop = Closing()
            T._cancel_post(post)
            gc.collect()
    finally:
        logging.getLogger().removeHandler(handler)
    assert (handler.records, list(seen)) == ([], [])


def test_a_loop_that_ends_is_closed_and_ends_the_wait() -> None:
    async def interrupt() -> None:
        raise KeyboardInterrupt

    @tool(timeout_s=30)  # a fail-safe: a wait that never ends would answer `timeout`
    async def spawns_an_interrupt() -> int:
        """Spawn a task that raises KeyboardInterrupt out of the loop."""
        asyncio.get_running_loop().create_task(interrupt())
        await asyncio.Event().wait()
        return 1

    @tool(timeout_s=30)  # a fail-safe, as above
    async def stops_its_loop() -> int:
        """Stop the loop it runs on."""
        asyncio.get_running_loop().stop()
        await asyncio.Event().wait()
        return 1

    for t in (spawns_an_interrupt, stops_its_loop):
        before = _loop_threads()
        host = _host([t, tool(where)])
        assert kind(host(call_frame(t.name))) == "tool_error", t.name
        assert _last(host).fault is not None
        _join_tool_threads()
        assert host._loop._loop.is_closed()
        assert _loop_threads() - before == set()
        assert sum(host.counted) == 0
        assert answer(host(call_frame("where"))) == ("tool_error", "where failed (internal error)")
        assert "stopped" in _last(host).fault


# -------------------------------------------------------------------------------------------------
# Spec 075 (the 0.1.0a6 security review's F1): a gate allows a call only when it returns `None` or
# `True`; an awaitable's result counts only if the awaitable returned.


class SubExit(GeneratorExit):
    """A subclass of `GeneratorExit`, as a gate's or a tool's own code might raise."""


class OwnBase(BaseException):
    """An embedder's own `BaseException`."""


class _RaisingIterator:
    def __init__(self, exc: BaseException) -> None:
        self.exc = exc

    def __iter__(self) -> _RaisingIterator:
        return self

    def __next__(self) -> Any:
        raise self.exc


class BareAwait:
    """An awaitable whose `__await__` is a bare iterator that raises at its first step."""

    def __init__(self, exc: BaseException) -> None:
        self.exc = exc

    def __await__(self) -> _RaisingIterator:
        return _RaisingIterator(self.exc)


def _gate(form: str, what: tuple[str, Any]) -> Any:
    """A gate of `form` that raises a fresh exception from `what`'s factory, or returns its
    value (spec 075, criterion 1)."""
    how, x = what

    def act() -> Any:
        if how == "raise":
            raise x()
        return x

    async def body(call: Any) -> Any:
        return act()

    if form == "sync":
        return lambda call: act()
    if form == "async def":
        return body
    if form == "def returning a coroutine":
        return lambda call: body(call)
    if form == "async __call__":

        class Gate:
            async def __call__(self, call: Any) -> Any:
                return act()

        return Gate()
    if form == "a Future given the exception":

        async def future_gate(call: Any) -> Any:
            future = asyncio.get_running_loop().create_future()
            future.set_exception(x())
            return await future

        return future_gate
    assert form == "a bare __await__ iterator"
    return lambda call: BareAwait(x())


GATE_FORMS = ("sync", "async def", "def returning a coroutine", "async __call__")
EXTRA_FORMS = ("a Future given the exception", "a bare __await__ iterator")
RAISES = [
    (GeneratorExit, "GeneratorExit"),
    (SubExit, "SubExit"),
    (lambda: GeneratorExit("text"), "GeneratorExit: text"),
    (KeyboardInterrupt, "KeyboardInterrupt"),
    (lambda: SystemExit(3), "SystemExit: 3"),
    (asyncio.CancelledError, "CancelledError"),
    (OwnBase, "OwnBase"),
]
REFUSING = [
    pytest.param(form, ("raise", exc), fault, id=f"{form}-{fault}")
    for form in GATE_FORMS
    for exc, fault in RAISES
] + [
    pytest.param(form, ("raise", exc), fault, id=f"{form}-{fault}")
    for form in EXTRA_FORMS
    for exc, fault in RAISES[:2]
]
ALLOWING = [
    pytest.param(form, ("return", value), None, id=f"{form}-returns {value}")
    for form in GATE_FORMS[1:]
    for value in (None, True)
]


@pytest.mark.parametrize("where", ["private", "caller"])
@pytest.mark.parametrize(("form", "what", "fault"), REFUSING + ALLOWING)
def test_a_gate_refuses_unless_it_returns_an_allow(caller, where, form, what, fault) -> None:
    """Spec 075, criterion 1: every gate form, on `run`'s private loop and on `run_async`'s
    caller's loop, refuses on any raise (a `BaseException` included, `GeneratorExit` and its
    subclasses too, however the awaitable delivers it), keeps the fault, and never runs the
    tool; it allows only on a return of `None` or `True`."""
    ran: list = []

    @tool(name="effect")
    def effect() -> int:
        """An effect the gate guards."""
        ran.append(1)
        return 1

    with warnings.catch_warnings(record=True) as seen:
        warnings.simplefilter("always")
        loop = caller.loop if where == "caller" else None
        host = _host([effect], gate=_gate(form, what), loop=loop)
        got = answer(host(call_frame("effect")))
        outcome = _last(host)
        host.close()
        _join_tool_threads()
        gc.collect()
    if what[0] == "return":
        assert (got, outcome.fault, ran) == (("ok", 1), None, [1])
    else:
        assert got == ("denied", "effect was refused")
        assert (outcome.outcome, outcome.fault, ran) == ("denied", fault, [])
    assert caller.thread.is_alive() and not caller.loop.is_closed()
    assert [w for w in seen if issubclass(w.category, RuntimeWarning)] == []


def _boom(form: str, exc: Any) -> T.Tool:
    async def boom() -> int:
        """Raise."""
        raise exc()

    if form == "async def":
        return tool(boom, name="boom")
    if form == "def returning a coroutine":

        def adapter() -> int:
            """Return a coroutine that raises."""
            return boom()

        return tool(adapter, name="boom")

    class Boom:
        async def __call__(self) -> int:
            """Raise."""
            raise exc()

    return tool(Boom(), name="boom")


@pytest.mark.parametrize("where", ["private", "caller"])
@pytest.mark.parametrize("form", GATE_FORMS[1:])
@pytest.mark.parametrize(("exc", "fault"), RAISES[:2], ids=["GeneratorExit", "SubExit"])
def test_an_async_tool_that_raises_generatorexit_is_a_fault(
    caller, where, form, exc, fault
) -> None:
    """Spec 075, criterion 2: an async tool that raises `GeneratorExit` or a subclass is a
    fault, never `ok` with `None`."""
    with warnings.catch_warnings(record=True) as seen:
        warnings.simplefilter("always")
        host = _host([_boom(form, exc)], loop=caller.loop if where == "caller" else None)
        got = answer(host(call_frame("boom")))
        host.close()
        _join_tool_threads()
        gc.collect()
    assert got == ("tool_error", "boom failed (internal error)")
    assert (_last(host).outcome, _last(host).fault) == ("tool_error", fault)
    assert [w for w in seen if issubclass(w.category, RuntimeWarning)] == []


class _FirstStep:
    """An `ops` whose first step raises `GeneratorExit` (the wrapper then ends with neither a
    return nor an error) or returns `start`'s verdict."""

    def __init__(self, start: Any) -> None:
        self._start = start

    def post(self, post: Any) -> bool:
        return True

    def start(self, task: Any) -> bool:
        if isinstance(self._start, type) and issubclass(self._start, BaseException):
            raise self._start
        return self._start

    def started(self, post: Any) -> bool:
        return post.started

    def ending(self) -> str | None:
        return None


@pytest.mark.parametrize("where", ["private", "caller"])
def test_the_tool_loop_gives_a_value_only_when_the_awaitable_returned(
    caller, where, monkeypatch
) -> None:
    """Spec 075, criterion 3: `_ToolLoop.run` gives a value only once the awaitable returned
    (Decision 1); a skipped post still raises `_NotStarted` first."""
    given = caller.loop if where == "caller" else None
    runs: list = []

    async def body() -> bool:
        runs.append(1)
        return True

    with warnings.catch_warnings(record=True) as seen:
        warnings.simplefilter("always")
        # The cleanups are in `finally`: a failing assertion must not leave the private loop's
        # thread running, or every later check's `joined` fail-safe waits 60 s on it (spec
        # 075's build review, F1).
        loop = T._ToolLoop(given)
        try:
            # The wrapper's first step raises GeneratorExit: neither a return nor an error.
            coro = body()
            with pytest.raises(RuntimeError, match="^the awaitable ended without a result$"):
                loop.run(coro, _FirstStep(GeneratorExit))
            assert inspect.getcoroutinestate(coro) == inspect.CORO_CLOSED

            # A skipped post: `_NotStarted`, not the RuntimeError above (Decision 1's order).
            coro = body()
            with pytest.raises(T._NotStarted):
                loop.run(coro, _FirstStep(False))
            assert inspect.getcoroutinestate(coro) == inspect.CORO_CLOSED
        finally:
            loop.close()

        # Through the frame host: the gate's call is refused, with the backstop's fault.
        ran: list = []

        @tool(name="effect")
        def effect() -> int:
            """An effect the gate guards."""
            ran.append(1)
            return 1

        def begin(self: Any, slot: Any, task: Any) -> bool:
            raise GeneratorExit

        monkeypatch.setattr(T._Bounded, "_begin", begin)
        host = _host([effect], gate=async_gate, loop=given)
        try:
            assert answer(host(call_frame("effect"))) == ("denied", "effect was refused")
            fault = "RuntimeError: the awaitable ended without a result"
            assert (_last(host).outcome, _last(host).fault, ran) == ("denied", fault, [])
        finally:
            host.close()
        _join_tool_threads()
        gc.collect()
    assert runs == []
    assert caller.thread.is_alive() and not caller.loop.is_closed()
    assert [w for w in seen if issubclass(w.category, RuntimeWarning)] == []


def test_a_generatorexit_thrown_into_the_wrapper_is_raised_on(monkeypatch) -> None:
    """Spec 075, Decision 2 (its build review, N1): a `GeneratorExit` met at the wrapper's
    `await` is recorded and raised on, so the wrapper never ends as though its awaitable had
    returned (the reviewer's X2, recorded but not re-raised, ends it with `StopIteration`)."""
    monkeypatch.setattr(T.asyncio, "current_task", lambda: object())  # no loop needed
    loop = asyncio.new_event_loop()
    try:
        post = T._Post(loop.create_future())
        wrapper = T._ToolLoop()._wrapper(post, None)
        assert wrapper.send(None) is post.awaitable  # the wrapper waits at its `await`
        thrown = GeneratorExit()
        with pytest.raises(GeneratorExit) as raised:
            wrapper.throw(thrown)
        assert raised.value is thrown
        assert (post.error, post.returned, post.ended.is_set()) == (thrown, False, True)
        assert inspect.getcoroutinestate(wrapper) == inspect.CORO_CLOSED
    finally:
        loop.close()
