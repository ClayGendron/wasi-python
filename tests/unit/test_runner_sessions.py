"""Sessions without artifacts (spec 055): the argument checks, the reaper's step and loop, and a
turn's waits on the session's clock base, all with fakes. Nothing here measures time."""

from __future__ import annotations

import queue
import struct

import pytest

import wasi_python
from wasi_python import Defaults, Session, _artifacts, _call, _sessions

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


def _state(idle: float | None, lifetime: float | None, last_end: float = 0.0, busy=False):
    s = _sessions._State()
    s.idle_s, s.lifetime_s, s.opened, s.last_end, s.busy = idle, lifetime, 0.0, last_end, busy
    return s


@pytest.fixture
def registry(monkeypatch):
    """A private registry of fake sessions, and a closer starter that records."""
    import weakref

    monkeypatch.setattr(_sessions, "_sessions", weakref.WeakSet())
    monkeypatch.setattr(_sessions, "_reaper_queue", queue.SimpleQueue())
    monkeypatch.setattr(_sessions, "_dropped", __import__("collections").deque())
    started: list[_sessions._State] = []
    monkeypatch.setattr(_sessions, "_start_ending", started.append)
    return started


def test_the_reaper_ends_what_is_due(registry) -> None:
    """Criterion 7: `_reap(now)` ends exactly what is due, with its reason, skips a busy session,
    hands each ending to the closer starter, and returns the wait to the next."""
    a, b, c, busy = (
        _state(10, 100),
        _state(50, 30),
        _state(None, None),
        _state(5, 5, busy=True),
    )
    keep = [a, b, c, busy]
    for s in keep:
        _sessions._sessions.add(s)
    assert _sessions._reap(20.0) == 10.0  # a is idle at 10; b's lifetime at 30 is next
    assert registry == [a] and a.ended == "idle" and a.closing.is_set()
    assert _sessions._reap(30.0) is None
    assert registry == [a, b] and b.ended == "lifetime"
    assert (c.ended, busy.ended) == (None, None)
    for s in keep:
        _sessions._sessions.discard(s)
    assert _sessions._reap(1e9) is None  # none open: no wait


def test_the_reaper_loop_ends_sessions_in_due_order(registry) -> None:
    """Criterion 7: the loop, driven by an injected clock and wait for a fixed number of rounds,
    ends sessions in due order. Stand-in: a reaper that ends a busy session."""
    states = [_state(30, None), _state(10, None), _state(20, None)]
    for s in states:
        _sessions._sessions.add(s)
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

    hour = 3600 * 10**9
    poll = _call._poll_oneoff(
        base, Waits(), realtime_ns=lambda: 0, monotonic_ns=lambda: base + hour
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
    """The re-review's F2: the ending's seconds end by the opening plus the lifetime plus the
    budget, whatever the start."""
    s = _state(None, 3600.0)
    s.shutdown_s = 5.0
    assert _sessions._ending_seconds(s, 100.0) == 5.0
    assert _sessions._ending_seconds(s, 3602.0) == 3.0
    assert _sessions._ending_seconds(s, 3605.0) == 0.0
    s.lifetime_s = None
    assert _sessions._ending_seconds(s, 10**6) == 5.0
