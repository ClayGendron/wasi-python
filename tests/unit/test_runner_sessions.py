"""Sessions without artifacts: the argument checks, the reaper's step and loop, and a
turn's waits on the session's clock base, all with fakes. Rows that run a session on the artifact
set: a turn's output is every byte of its own and none of another's, past the cap or not; and
every session is ended, whichever thread closes it and whether its turn ran, was cancelled while
queued, or was abandoned. Nothing here measures time: a bound is driven by a stepped clock, and
every `join(60)` or `wait(60)` is a fail-safe for a row that would hang, never a verdict."""

from __future__ import annotations

import asyncio
import queue
import struct
import threading

import pytest

import wasi_python
from harness import calls, needs
from wasi_python import Defaults, Session, _artifacts, _call, _engines, _sessions
from wasi_python._process import process

NAN, INF = float("nan"), float("inf")


async def _async_host(frame: bytes) -> bytes:
    return frame


MISTAKES = [
    ({"root": 5}, TypeError),
    ({"grants": "x"}, TypeError),
    ({"mounts": [1]}, TypeError),
    ({"env": {"a": 1}}, TypeError),
    ({"host": _async_host}, TypeError),
    ({"fuel": -1}, ValueError),
    ({"deadline_s": 0}, ValueError),
    ({"memory_bytes": -1}, ValueError),
    ({"output_bytes": True}, TypeError),
    ({"max_file_calls": -1}, ValueError),
    ({"tools": "x"}, TypeError),
    ({"gate": print}, TypeError),
    ({"max_tool_calls": 3}, TypeError),
    ({"import_path": ["relative"]}, ValueError),
    ({"snapshot": "yes"}, TypeError),
    ({"max_open_files": -1}, ValueError),
]
BOUNDS = [
    (True, TypeError),
    (0, ValueError),
    (-1, ValueError),
    (NAN, ValueError),
    (INF, ValueError),
    ("10", TypeError),
]
SHUTDOWNS = [
    (None, TypeError),
    (True, TypeError),
    ("5", TypeError),
    (-1, ValueError),
    (NAN, ValueError),
    (INF, ValueError),
]


class Looked(Exception):
    """The artifact lookup was reached: the opening's checks had all passed."""


@pytest.fixture
def lookups(monkeypatch) -> list[int]:
    """Counts artifact lookups; each one stops the opening there."""
    seen: list[int] = []

    def find() -> None:
        seen.append(1)
        raise Looked

    monkeypatch.setattr(_artifacts, "find_artifacts", find)
    return seen


def test_session_refuses_mistakes_before_anything_runs(lookups) -> None:
    """Criterion 4: each mistake raises from Session(...) with no artifact lookup."""
    cases = list(MISTAKES)
    cases += [({"idle_s": v}, e) for v, e in BOUNDS] + [({"lifetime_s": v}, e) for v, e in BOUNDS]
    cases += [({"shutdown_s": v}, e) for v, e in SHUTDOWNS]
    for kwargs, error in cases:
        with pytest.raises(error):
            Session(**kwargs)
        assert lookups == [], kwargs
    with pytest.raises(Looked):
        Session(shutdown_s=0)  # accepted: the opening goes on to find the set
    assert lookups == [1]
    d = Defaults(memory_bytes=1, deadline_s=1, output_bytes=1)
    assert (d.session_idle_s, d.session_lifetime_s, d.session_shutdown_s) == (900.0, 3600.0, 5.0)
    base = {"memory_bytes": 1, "deadline_s": 1, "output_bytes": 1}
    with pytest.raises(ValueError):
        Defaults(**base, session_idle_s=0)
    for value, error in SHUTDOWNS:
        with pytest.raises(error):
            Defaults(**base, session_shutdown_s=value)
    assert Defaults(**base, session_shutdown_s=0).session_shutdown_s == 0
    assert wasi_python.defaults().session_shutdown_s == 5.0


def _state(
    idle: float | None,
    lifetime: float | None,
    last_end: float = 0.0,
    phase: _sessions._Phase = _sessions._Phase.OPEN,
):
    """A session's state at rest, or in the phase given, with its bounds."""
    s = _sessions._State(calls.BASE_CALL, _engines._wasmtime())
    s.idle_s, s.lifetime_s, s.opened, s.last_end, s.phase = idle, lifetime, 0.0, last_end, phase
    return s


@pytest.fixture
def registry(monkeypatch):
    """A private registry of fake sessions, and a closer starter that records."""
    import weakref

    monkeypatch.setattr(process(), "sessions", weakref.WeakSet())
    monkeypatch.setattr(process(), "reaper_queue", queue.SimpleQueue())
    monkeypatch.setattr(process(), "dropped", __import__("collections").deque())
    started: list[_sessions._State] = []
    monkeypatch.setattr(process().observers, "start_ending", started.append)
    return started


def test_the_reaper_ends_what_is_due(registry) -> None:
    """Criterion 7: `_reap(now)` ends exactly what is due, with its reason, skips a busy session,
    hands each ending to the closer starter, and returns the wait to the next."""
    a, b, c, busy = (
        _state(10, 100),
        _state(50, 30),
        _state(None, None),
        _state(5, 5, phase=_sessions._Phase.TURN),
    )
    keep = [a, b, c, busy]
    for s in keep:
        process().sessions.add(s)
    assert _sessions._reap(20.0) == 10.0  # a is idle at 10; b's lifetime at 30 is next
    assert registry == [a] and a.ended == "idle" and a.closing.is_set()
    assert _sessions._reap(30.0) is None
    assert registry == [a, b] and b.ended == "lifetime"
    assert (c.ended, busy.ended) == (None, None)
    for s in keep:
        process().sessions.discard(s)
    assert _sessions._reap(1e9) is None  # none open: no wait


def test_the_reaper_loop_ends_sessions_in_due_order(registry) -> None:
    """Criterion 7: the loop, driven by an injected clock and wait for a fixed number of rounds,
    ends sessions in due order. Stand-in: a reaper that ends a busy session."""
    states = [_state(30, None), _state(10, None), _state(20, None)]
    for s in states:
        process().sessions.add(s)
    now = [0.0]
    waits: list[float | None] = []

    def get(wait):
        waits.append(wait)
        if wait is not None:
            now[0] += wait  # the wait passes in fake time
        raise queue.Empty

    _sessions._reaper_loop(get=get, clock=lambda: now[0], rounds=4)
    assert registry == [states[1], states[2], states[0]]
    assert waits == [None, 10.0, 10.0, 10.0]


def test_a_dropped_session_is_ended_by_the_next_step(registry) -> None:
    """Criterion 24(c), its unit part: the finalizer only queues; the reaper's next step ends the
    session "closed" and starts its ending."""
    s = _state(None, None)
    _sessions._collected(s)
    assert s.ended is None and registry == []
    _sessions._reap(0.0)
    assert s.ended == "closed" and registry == [s]


def test_a_turn_waits_on_the_sessions_clock_base() -> None:
    """Criterion 31: a turn whose call is made an hour into the session waits 1 s for
    `time.sleep(1)`, which the guest sends as an absolute monotonic time. Stand-in: a base taken
    per turn (the wait is 3,601 s)."""
    base = 1_000_000_000
    waited: list[float] = []

    class Waits:
        def wait(self, seconds: float) -> None:
            waited.append(seconds)

    class Table:  # the call's table: no descriptor is polled here, and no stop is made
        def kind(self, fd: int) -> str | None:
            return None

        def record_stop(self, error: BaseException, caller: object) -> None:
            raise AssertionError("no stop is made")

    hour = 3600 * 10**9
    poll = _call._poll_oneoff(
        base, Waits(), realtime_ns=lambda: 0, monotonic_ns=lambda: base + hour, files=Table()
    )
    sub = struct.pack(_call.SUBSCRIPTION, 7, _call.CLOCK, _call.MONOTONIC, hour + 10**9, 0, 1)

    class Memory:
        def __init__(self) -> None:
            self.data = bytearray(4096)
            self.data[0 : len(sub)] = sub

        def data_len(self, caller) -> int:
            return len(self.data)

        def read(self, caller, start: int, stop: int) -> bytes:
            return bytes(self.data[start:stop])

        def write(self, caller, data: bytes, at: int) -> None:
            self.data[at : at + len(data)] = data

    class Caller:
        memory = Memory()

        def get(self, name: str):
            return self.memory

    assert poll(Caller(), 0, 1024, 1, 2048) == 0
    assert waited == [1.0]


def test_a_shutdown_budget_is_capped_by_the_lifetime() -> None:
    """The ending's seconds end by the opening plus the lifetime plus the
    budget, whatever the start."""
    s = _state(None, 3600.0)
    s.shutdown_s = 5.0
    assert _sessions._ending_seconds(s, 100.0) == 5.0
    assert _sessions._ending_seconds(s, 3602.0) == 3.0
    assert _sessions._ending_seconds(s, 3605.0) == 0.0
    s.lifetime_s = None
    assert _sessions._ending_seconds(s, 10**6) == 5.0


def _session() -> type[Session]:
    needs.need("runner", "artifact dir")
    return Session


def test_a_turn_gets_every_byte_of_its_own() -> None:
    """Sixty turns, each writing a distinct 100 KiB and a last line: each turn's stdout is its
    own bytes exactly and holds none of another's, so a turn's end gathers every byte it wrote
    before its result is made. Sixty, not two: a turn's end that gathered nothing would still
    find most turns' bytes already read, so two turns alone could pass it; sixty leave it
    almost no chance."""
    payload = 100 * 1024
    wrong = []
    with _session()() as s:
        for i in range(60):
            letter = "abcdefghijklmnopqrst"[i % 20]  # no two turns in a row alike
            done = s.run(f"import sys\nsys.stdout.write({letter!r} * {payload})\nprint({i})")
            own = letter.encode() * payload + f"{i}\n".encode()
            if (done.exit_code, done.stdout, done.truncated) != (0, own, ()):
                wrong.append((i, done.exit_code, len(done.stdout), done.truncated))
    assert wrong == []


def test_a_turn_past_the_cap_leaves_the_next_turn_whole() -> None:
    """A turn that writes a mebibyte under a 4 KiB cap keeps 4 KiB and names stdout; the next
    turn's one line is its whole output, nothing truncated."""
    with _session()(output_bytes=4096) as s:
        big = s.run("import os\nfor _ in range(16):\n    os.write(1, b'x' * 65536)")
        small = s.run("print('next')")
    assert (big.exit_code, big.stdout, big.truncated) == (0, b"x" * 4096, ("stdout",))
    assert (small.exit_code, small.stdout, small.truncated) == (0, b"next\n", ())


LOOP = "while True:\n    pass\n"


@pytest.fixture
def stepped(monkeypatch) -> list[float]:
    """The sessions' clock, a value the row steps; the reaper thread paused, so only the row
    drives `_reap`."""
    now = [0.0]
    monkeypatch.setattr(process().observers, "clock", lambda: now[0])
    monkeypatch.setattr(process().observers, "reaper_paused", True)
    return now


def test_close_from_a_host_function_in_a_run_async_turn_returns_at_once(stepped) -> None:
    """A host function runs on the thread that runs the turn, so its `close()` marks the session
    and returns at once, as it does under `run`; the turn is then stopped, and the session's
    ending has run by the time `run_async` returns. Before, the claim named the event loop's
    thread as the turn's, and the `close()` waited for a turn that could not return until it
    did."""
    seen: list[tuple[str | None, str | None]] = []
    held: dict[str, Session] = {}

    def host(frame: bytes) -> bytes:
        s = held["s"]
        s.close()
        seen.append((s.ended, s.shutdown_outcome))
        return b""

    async def main():
        s = held["s"] = _session()(host=host)
        task = asyncio.ensure_future(s.run_async("import _host\n_host.call(b'x')\n" + LOOP))
        await asyncio.wait({task}, timeout=60)  # a fail-safe, not a timing
        return s, task

    loop = asyncio.new_event_loop()  # not asyncio.run: a turn that never returns is reported
    s, task = loop.run_until_complete(main())
    assert task.done(), "a close() from the turn's own host function waited for its own turn"
    loop.close()
    assert seen == [("closed", None)]  # marked, and returned before the ending
    assert task.result().trapped == "cancelled"
    assert (s.ended, s.shutdown_outcome) == ("closed", "skipped")


def test_close_from_the_loop_thread_waits_for_the_ending(stepped) -> None:
    """The event loop's thread claimed the turn, but a worker runs it: a `close()` there waits
    for the turn to stop and the ending to run, so the outcome is set when it returns."""
    started = threading.Event()

    def host(frame: bytes) -> bytes:
        started.set()
        return b""

    async def main():
        s = _session()(host=host)
        task = asyncio.ensure_future(s.run_async("import _host\n_host.call(b'x')\n" + LOOP))
        await asyncio.get_running_loop().run_in_executor(None, started.wait, 60)
        s.close()  # on the loop's thread, while the guest loops on a worker
        outcome = s.shutdown_outcome
        done = await task
        return s, outcome, done

    s, outcome, done = asyncio.run(main())
    assert (s.ended, outcome) == ("closed", "skipped")
    assert done.trapped == "cancelled"


def test_a_queued_turn_cancelled_after_a_close_is_ended(stepped) -> None:
    """A turn claimed and still queued behind a busy worker, then closed from another thread and
    cancelled: its turn never starts, and a closer ends the session, so `close()` returns."""
    import concurrent.futures

    pool = concurrent.futures.ThreadPoolExecutor(1)
    busy = threading.Event()
    blocker = pool.submit(busy.wait, 60)
    s = _session()()
    closer = threading.Thread(target=s.close, daemon=True)

    async def main() -> None:
        queued = asyncio.ensure_future(s.run_async("print(5)", executor=pool))
        await asyncio.sleep(0)  # claimed and queued
        closer.start()
        while s.ended is None and closer.is_alive():
            closer.join(0.001)  # until close() has marked it; a wait, not a verdict
        queued.cancel()
        with pytest.raises(asyncio.CancelledError):
            await queued

    try:
        asyncio.run(main())
        closer.join(60)  # a fail-safe, not a timing
        assert not closer.is_alive(), "close() waits on a session nobody will end"
        assert (s.ended, s.shutdown_outcome) == ("closed", "skipped")
    finally:
        busy.set()
        blocker.result(60)
        pool.shutdown(wait=False)


def test_a_closer_that_cannot_start_ends_the_session_where_it_was_started(
    stepped, monkeypatch
) -> None:
    """The reaper's closer thread fails to start, as it can on a host short of threads: the
    ending runs on the reaper's own thread instead, so the session is ended and `close()`
    returns."""
    refused: list[_sessions._State] = []

    def refuse(state: _sessions._State) -> None:
        refused.append(state)
        raise RuntimeError("can't start new thread")

    s = _session()(idle_s=10)
    monkeypatch.setattr(process().observers, "start_ending", refuse)
    stepped[0] = 11.0
    _sessions._reap(stepped[0])
    assert refused.count(s._state) == 1
    closer = threading.Thread(target=s.close, daemon=True)
    closer.start()
    closer.join(60)  # a fail-safe, not a timing
    assert not closer.is_alive(), "close() waits on an ending nobody runs"
    assert (s.ended, s.shutdown_outcome) == ("idle", "skipped")


def test_an_abandoned_turns_session_dropped_is_ended_by_the_reaper(registry) -> None:
    """A turn whose home was forced out leaves its session marked "error" at the guest thread's
    end; the session is handed to a closer, once, and a dropped one is not left until exit. A
    session found marked and held by no one, by any path, is handed to a closer by the next
    step too."""
    s = _state(None, None, phase=_sessions._Phase.TURN)
    s.guest = _sessions._Guest.ENTERED
    _sessions._abandon_turn(s)
    _sessions._collected(s)
    _sessions._reap(0.0)
    assert (s.ended, s.phase, s.holder) == ("error", _sessions._Phase.ENDING, _sessions._CLOSER)
    assert registry == [s]
    resting = _state(None, None, phase=_sessions._Phase.MARKED)
    resting.ended = "error"
    process().sessions.add(resting)
    _sessions._reap(0.0)
    assert registry == [s, resting] and resting.phase is _sessions._Phase.ENDING
    process().sessions.discard(resting)


def _on_a_loop_thread(main) -> list:
    """`main()` run by `asyncio.run` on a thread of its own, joined with a fail-safe: a loop
    that is blocked cannot run its own timeout. What the loop's thread raised is raised here, so
    a skip or an error is reported as itself."""
    out: list = []
    raised: list[BaseException] = []

    def run() -> None:
        try:
            out.append(asyncio.run(main()))
        except BaseException as e:
            raised.append(e)

    runner = threading.Thread(target=run, daemon=True)
    runner.start()
    runner.join(60)  # a fail-safe, not a timing
    assert not runner.is_alive(), "the event loop never finished"
    if raised:
        raise raised[0]
    return out


def test_close_from_a_sync_tool_in_a_run_async_turn_ends_the_session(stepped) -> None:
    """A synchronous tool runs on a thread of its own. Its `close()` stops the turn; the tool's
    call is answered "cancelled" at the next tick, whatever the tool still does, so the turn
    returns, runs the ending, and the `close()` returns once the ending has finished."""
    make = _session()  # on this thread: a missing set skips the row here
    seen: list[tuple[str | None, str | None]] = []
    returned = threading.Event()
    held: dict[str, Session] = {}

    def closer() -> str:
        """Close the session this tool's turn runs in."""
        s = held["s"]
        s.close()
        seen.append((s.ended, s.shutdown_outcome))
        returned.set()
        return "closed"

    async def main():
        s = held["s"] = make(tools=[closer])
        return s, await s.run_async("from host import tools\ntools.closer()\n" + LOOP)

    [(s, done)] = _on_a_loop_thread(main)
    assert returned.wait(60), "the tool's close() never returned"  # a fail-safe, not a timing
    assert seen == [("closed", "skipped")]  # it waited for the ending, which had finished
    assert done.trapped == "cancelled"
    assert (s.ended, s.shutdown_outcome) == ("closed", "skipped")


def test_close_from_an_async_tool_in_a_run_async_turn_ends_the_session(stepped) -> None:
    """An asynchronous tool runs on the event loop that awaits the turn. Its `close()` stops the
    turn and holds the loop only until the ending has finished: the turn's worker answers the
    tool's call "cancelled" without the loop, so the loop goes on and the turn's await
    returns."""
    make = _session()  # on this thread: a missing set skips the row here
    seen: list[tuple[str | None, str | None]] = []
    held: dict[str, Session] = {}
    after: list[str] = []

    async def closer() -> str:
        """Close the session this tool's turn runs in."""
        s = held["s"]
        s.close()
        seen.append((s.ended, s.shutdown_outcome))
        return "closed"

    async def main():
        s = held["s"] = make(tools=[closer])
        done = await s.run_async("from host import tools\ntools.closer()\n" + LOOP)
        await asyncio.sleep(0)
        after.append("the loop went on")
        return s, done

    [(s, done)] = _on_a_loop_thread(main)
    assert seen == [("closed", "skipped")]
    assert after == ["the loop went on"]
    assert done.trapped == "cancelled"
    assert (s.ended, s.shutdown_outcome) == ("closed", "skipped")


def test_a_turns_stdin_answers_input() -> None:
    """A turn's `stdin` is `sys.stdin` for that turn: `input()` reads its lines, then end of
    file; the next turn without one reads end of file at once, and none reads another's
    leftover. Its reader has no descriptor, and descriptor 0 stays the session's own."""
    with _session()() as s:
        given = s.run(
            "a = input(); b = input()\nprint(a, b)\n"
            "try:\n    input()\nexcept EOFError:\n    print('eof')",
            stdin=b"first\nsecond\n",
        )
        assert (given.exit_code, given.stdout) == (0, b"first second\neof\n"), given
        leftover = s.run("import sys\nprint(repr(sys.stdin.read()))", stdin=b"one\ntwo\n")
        assert leftover.stdout == b"'one\\ntwo\\n'\n", leftover
        empty = s.run("try:\n    input()\nexcept EOFError:\n    print('eof')")
        assert (empty.exit_code, empty.stdout) == (0, b"eof\n"), empty
        no_fd = s.run(
            "import io, os, sys\n"
            "try:\n    sys.stdin.fileno()\nexcept io.UnsupportedOperation:\n    print('none')\n"
            "print(len(os.read(0, 10)))",
            stdin=b"x",
        )
        assert no_fd.stdout == b"none\n0\n", no_fd


def test_a_turns_stdin_is_checked_before_the_claim() -> None:
    """A `stdin` that is not bytes-like is a `TypeError`, and the session stays open."""
    with _session()() as s:
        with pytest.raises(TypeError, match="stdin must be bytes-like"):
            s.run("print(1)", stdin="text")  # type: ignore[arg-type]
        assert s.ended is None
        assert s.run("print(2)").stdout == b"2\n"


def test_a_turn_streams() -> None:
    """A turn's chunks, joined, are its output, and a turn's `output_keep` is its own; the
    streamed turn leaves no thread behind."""
    from wasi_python import OutputChunk

    with _session()() as s:
        s.run("pass")  # the engine, the module and the ticker, before counting
        before = set(threading.enumerate())
        chunks: list[OutputChunk] = []
        done = s.run(
            "import sys\nprint('out')\nprint('err', file=sys.stderr)", on_output=chunks.append
        )
        assert b"".join(c.data for c in chunks if c.stream == "stdout") == done.stdout == b"out\n"
        assert b"".join(c.data for c in chunks if c.stream == "stderr") == done.stderr == b"err\n"
        left = [t for t in threading.enumerate() if t not in before and t.is_alive()]
        assert not left, left
        tail = s.run("print('x' * 50 + 'END')", output_bytes=30, output_keep="tail")
        assert tail.stdout.endswith(b"END\n") and len(tail.stdout) == 30, tail
        assert s.run("print('whole')").stdout == b"whole\n"


def test_a_turn_streams_under_run_async() -> None:
    """Under `Session.run_async` the chunks reach the event loop's thread, and a feed follows
    the turn's task."""
    from wasi_python import OutputFeed

    make = _session()

    async def main():
        with make() as s:
            feed = OutputFeed()
            task = asyncio.ensure_future(s.run_async("print('a')\nprint('b')", on_output=feed))
            chunks = [c async for c in feed.follow(task)]
            return chunks, await task

    chunks, done = asyncio.run(main())
    assert b"".join(c.data for c in chunks) == done.stdout == b"a\nb\n"
