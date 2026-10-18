"""Tools in the runner (spec 036), with no guest: `run` refuses its tool arguments before any
work, the door asks `admit(length)` before it reads a frame, and the bound of one tool call
answers each of its ends in order. Fakes stand in for wasmtime, the ticker, `cancel` and the
Ctrl-C flag. Nothing here measures time: a tool that must block waits on an event the check
sets, and a short `timeout_s` only chooses the outcome."""

from __future__ import annotations

import asyncio
import concurrent.futures
import functools
import json
import os
import struct
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

import pytest

from wasi_python import Artifacts, ArtifactsMissing, runner
from wasi_python import tools as T
from wasi_python.tools import tool


def call_frame(name: str, args: Any = None, id: int = 1) -> bytes:
    return json.dumps({"v": 1, "id": id, "op": "call", "tool": name, "args": args or {}}).encode()


def kind(raw: bytes) -> str | None:
    a = json.loads(raw)
    return None if a["ok"] else a["error"]["kind"]


def value(raw: bytes) -> Any:
    a = json.loads(raw)
    assert a["ok"], a
    return a["value"]


@pytest.fixture
def release():
    """An event every blocking tool here waits on, set at the end, and the tool threads joined,
    so no check leaves a thread behind for the next one to count."""
    event = threading.Event()
    yield event
    event.set()
    for t in threading.enumerate():
        if t.name.startswith("wasi-python-tool-"):
            t.join(60)  # a fail-safe, not a timing


# -------------------------------------------------------------------------------------------------
# Criterion 1: refusals before anything runs.


@tool
def lookup(code: str) -> str:
    """Look something up."""
    return code


def plain(code: str) -> str:
    """A plain function, which run() passes through tool()."""
    return code


def unhinted(code):
    return code


async def async_gate(call):
    yield None  # an async generator: refused as a gate (spec 053)


async def async_host(frame):
    return frame


async def agen_host(frame):
    yield frame


class AsyncHost:
    async def __call__(self, frame):
        return frame


def _twin() -> T.Tool:
    @tool(name="lookup")
    def other(code: str) -> str:
        """Another tool with the same name."""
        return code

    return other


MISTAKES = [
    ({"host": lambda f: f, "tools": [lookup]}, TypeError, "pass host= for the raw door or tools="),
    ({"host": lambda f: f, "tools": []}, TypeError, "not both"),
    ({"gate": lambda call: None}, TypeError, "gate= without tools="),
    ({"max_tool_calls": 10}, TypeError, "max_tool_calls= without tools="),
    ({"max_tool_calls": None}, TypeError, "max_tool_calls= without tools="),
    ({"tools": [lookup, _twin()]}, ValueError, r"tools\[1\].*'lookup'"),
    ({"tools": [plain, plain]}, ValueError, r"tools\[1\].*'plain'"),
    ({"tools": [lookup], "gate": 5}, TypeError, "gate must be"),
    ({"tools": [lookup], "gate": async_gate}, TypeError, "async generator"),
    ({"host": async_host}, TypeError, "serve an async host function as a tool"),
    ({"host": agen_host}, TypeError, "serve an async host function as a tool"),
    ({"host": AsyncHost()}, TypeError, "serve an async host function as a tool"),
    ({"host": functools.partial(async_host)}, TypeError, "serve an async host function as a tool"),
    ({"tools": [lookup], "max_tool_calls": True}, TypeError, "max_tool_calls"),
    ({"tools": [lookup], "max_tool_calls": -1}, ValueError, "max_tool_calls"),
    ({"tools": [lookup], "max_tool_calls": 2**63}, ValueError, "max_tool_calls"),
    ({"tools": [lookup], "max_tool_calls": "10"}, TypeError, "max_tool_calls"),
    ({"tools": "lookup"}, TypeError, "iterable of Tool"),
    ({"tools": lookup}, TypeError, "iterable of Tool"),
    ({"tools": [5]}, TypeError, r"tools\[0\] must be a Tool or a function"),
    ({"tools": [unhinted]}, TypeError, "unhinted"),
]


class Recording(concurrent.futures.Executor):
    def __init__(self) -> None:
        self.submitted: list[Any] = []

    def submit(self, fn, /, *args, **kwargs):
        self.submitted.append(fn)
        raise AssertionError("submit must not be reached")


@pytest.mark.parametrize(("kw", "error", "match"), MISTAKES)
def test_run_refuses_mistakes_before_anything_runs(monkeypatch, kw, error, match) -> None:
    lookups = []

    def found():
        lookups.append(1)
        raise AssertionError("the artifacts must not be looked up")

    monkeypatch.setattr(runner, "find_artifacts", found)
    ex = Recording()
    with pytest.raises(error, match=match):
        runner.run(["-c", "pass"], **kw)
    with pytest.raises(error, match=match):
        asyncio.run(runner.run_async(["-c", "pass"], executor=ex, **kw))
    assert (lookups, ex.submitted) == ([], [])


def test_the_tool_call_limit_has_a_default() -> None:
    assert runner.DEFAULTS.tool_calls == 1000
    assert runner.Defaults(1 << 30, 60.0, 16 << 20).tool_calls == 1000
    assert runner.Defaults(1 << 30, 60.0, 16 << 20, tool_calls=None).tool_calls is None
    with pytest.raises(ValueError, match="tool_calls"):
        runner.Defaults(1 << 30, 60.0, 16 << 20, tool_calls=-1)
    with pytest.raises(TypeError, match="tool_calls"):
        runner.Defaults(1 << 30, 60.0, 16 << 20, tool_calls=True)


def test_the_tools_are_checked_into_plain_tools() -> None:
    c = runner._check_tools(None, iter([lookup, plain]), None, runner._UNSET)
    assert [type(t) for t in c["tools"]] == [T.Tool, T.Tool]
    assert [t.name for t in c["tools"]] == ["lookup", "plain"]
    assert (c["gate"], c["tool_calls"]) == (None, 1000)
    assert runner._check_tools(None, [], None, None)["tool_calls"] is None  # None: no limit
    none = runner._check_tools(lambda f: f, None, None, runner._UNSET)
    assert none == {"tools": None, "gate": None, "tool_calls": None}


def _artifacts(folder: Path, manifest: str) -> Artifacts:
    (folder / "MANIFEST").write_text(manifest)
    return Artifacts(
        snapshot=folder / "python-snapshot.wasm",
        plain=folder / "python.wasm",
        stdlib_zip=folder / "python-stdlib.zip",
        manifest=folder / "MANIFEST",
    )


OLD_MANIFEST = "python 3.15.0\nrecipe 33a5 recipes/hostmodule.c\n"
GUEST_LINE = "recipe bf59 recipes/guest/host/tools.py\n"


def test_an_artifact_set_without_the_guest_package_is_refused(tmp_path, monkeypatch) -> None:
    walks = []
    monkeypatch.setattr(runner, "_walk_grants", lambda *a: walks.append(a))
    old = _artifacts(tmp_path, OLD_MANIFEST)
    with pytest.raises(ArtifactsMissing, match="recipe … recipes/guest/host/tools.py"):
        runner.run(["-c", "pass"], tools=[lookup], artifacts=old)
    assert walks == []  # refused before the grants are walked, so before the guest starts
    assert runner._has_guest_package(old.manifest) is False
    (tmp_path / "MANIFEST").write_text(OLD_MANIFEST + GUEST_LINE)  # its stamp changes
    assert runner._has_guest_package(old.manifest) is True
    assert runner._has_guest_package(old.manifest) is True  # from the cache


# -------------------------------------------------------------------------------------------------
# Criterion 2: the door refuses by length before it reads.


class Memory:
    def __init__(self, size: int = 4096) -> None:
        self.buf = bytearray(size)
        self.reads = 0

    def data_len(self, caller: Any) -> int:
        return len(self.buf)

    def read(self, caller: Any, start: int, stop: int) -> bytearray:
        self.reads += 1
        return self.buf[start:stop]

    def write(self, caller: Any, data: bytes, at: int) -> None:
        self.buf[at : at + len(data)] = data


class Caller:
    def __init__(self, memory: Memory) -> None:
        self.memory, self.next = memory, 2048

    def get(self, name: str) -> Any:
        return {"memory": self.memory, "host_alloc": self.alloc}[name]

    def alloc(self, caller: Any, n: int) -> int:
        p, self.next = self.next, self.next + n
        return p


def _answer(memory: Memory) -> bytes:
    (p,) = struct.unpack("<I", memory.buf[16:20])
    (n,) = struct.unpack("<I", memory.buf[20:24])
    return bytes(memory.buf[p : p + n])


def test_the_door_refuses_by_length_before_reading() -> None:
    hosted, admitted = [], []

    def host(frame: bytes) -> bytes:
        hosted.append(bytes(frame))
        return b"hosted"

    def refuses(length: int) -> bytes:
        admitted.append(length)
        return b"refused"

    def passes(length: int) -> None:
        admitted.append(length)

    memory = Memory()
    memory.buf[100:103] = b"abc"
    assert runner._door(host, refuses)(Caller(memory), 100, 3, 16, 20) == 0
    assert (memory.reads, admitted, hosted, _answer(memory)) == (0, [3], [], b"refused")

    memory, admitted[:] = Memory(), []
    memory.buf[100:103] = b"abc"
    assert runner._door(host, passes)(Caller(memory), 100, 3, 16, 20) == 0
    assert (memory.reads, admitted, hosted, _answer(memory)) == (1, [3], [b"abc"], b"hosted")

    memory, hosted[:] = Memory(), []
    memory.buf[100:103] = b"abc"
    assert runner._door(host)(Caller(memory), 100, 3, 16, 20) == 0  # the raw door: unchanged
    assert (memory.reads, hosted, _answer(memory)) == (1, [b"abc"], b"hosted")

    memory, admitted[:] = Memory(), []  # addresses past memory: a fault, before admit
    assert runner._door(host, refuses)(Caller(memory), 4000, 200, 16, 20) == runner.HOST_FAULT
    assert (memory.reads, admitted) == (0, [])


def test_a_frame_host_behind_the_door_counts_a_refused_frame_unread() -> None:
    host = T._ToolHost([lookup], max_calls=1)
    door = runner._door(host, host.admit)
    memory = Memory(1 << 21)
    big = T._TOOL_REQUEST_BYTES + 1
    assert door(Caller(memory), 4096, big, 16, 20) == 0
    assert (memory.reads, kind(_answer(memory))) == (0, "too_large")
    assert door(Caller(memory), 4096, 3, 16, 20) == 0  # frame 2, past max_calls=1
    assert (memory.reads, kind(_answer(memory))) == (0, "budget_exceeded")
    assert [o.request_bytes for o in host.record.outcomes] == [big, 3]


# -------------------------------------------------------------------------------------------------
# Criterion 3: the bound of one tool call answers in order.


class Ticks:
    def __init__(self, n: int = 0) -> None:
        self.n = n

    def __call__(self) -> int:
        return self.n


def _host(tools: list, *, stop_at=None, cancel=None, ctrl_c=None, ticks=None, **kw) -> Any:
    counted = []
    bound = T._Bounded(
        tick_s=0.001,
        stop_at=stop_at,
        ticks=ticks,
        cancel=cancel,
        ctrl_c=ctrl_c,
        count=counted.append,
        **kw,
    )
    host = T._ToolHost(tools, invoke=bound)
    host.counted = counted
    return host


def _blocking(release: threading.Event, started: list, timeout_s=None, then=None) -> T.Tool:
    @tool(name="slow", timeout_s=timeout_s)
    def slow() -> int:
        """Wait for the check."""
        started.append(1)
        if then is not None:
            then()
        release.wait()
        return 1

    return slow


def _last(host: Any) -> T.ToolOutcome:
    return host.record.outcomes[-1]


def test_the_bound_answers_in_order(release, monkeypatch) -> None:
    started: list = []

    # The tool's timeout_s.
    host = _host([_blocking(release, started, timeout_s=0.01)])
    assert kind(host(call_frame("slow"))) == "timeout"
    o = _last(host)
    assert (o.op, o.tool, o.outcome, o.abandoned) == ("call", "slow", "timeout", True)
    assert o.message == "slow timed out after 0.01 s"

    # The call's deadline less two ticks: the tool moves the fake ticker there.
    ticks = Ticks(0)
    host = _host([_blocking(release, started, then=lambda: setattr(ticks, "n", 8))],
                 stop_at=10, ticks=ticks)  # fmt: skip
    assert kind(host(call_frame("slow"))) == "timeout"
    o = _last(host)
    assert (o.outcome, o.abandoned, o.message) == ("timeout", True, "slow timed out at the "
                                                    "run's deadline")  # fmt: skip

    # The call's cancel.
    cancel = threading.Event()
    host = _host([_blocking(release, started, then=cancel.set)], cancel=cancel)
    assert kind(host(call_frame("slow"))) == "cancelled"
    assert (_last(host).abandoned, _last(host).message) == (True, "slow was cancelled")

    # A pending Ctrl-C, read through the runner's own wiring, and never cleared.
    monkeypatch.setattr(runner, "_ctrl_c_watched", lambda: True)
    monkeypatch.setitem(runner._ctrl_c, "pending", False)
    slow = _blocking(release, started, then=lambda: runner._ctrl_c.__setitem__("pending", True))
    c = {"tools": (slow,), "gate": None, "tool_calls": 1000}
    host = runner._tool_host(c, None, None)
    assert kind(host(call_frame("slow"))) == "cancelled"
    assert _last(host).abandoned is True
    assert runner._ctrl_c["pending"] is True  # the bound reads the flag; _shared clears it
    assert len(started) == 4


def test_too_little_time_or_too_many_abandoned_answers_at_once(release) -> None:
    started: list = []
    # Fewer than two ticks left: timeout at once, and neither gate nor tool runs.
    gated: list = []
    bound = T._Bounded(tick_s=0.001, stop_at=11, ticks=Ticks(10))
    host = T._ToolHost([_blocking(release, started)], gate=gated.append, invoke=bound)
    assert kind(host(call_frame("slow"))) == "timeout"
    assert (started, gated, _last(host).abandoned) == ([], [], False)
    # Exactly two ticks left: the end is already reached, so the same (the build review's F5).
    bound = T._Bounded(tick_s=0.001, stop_at=12, ticks=Ticks(10))
    host = T._ToolHost(
        [_blocking(release, started, timeout_s=0.01)], gate=gated.append, invoke=bound
    )
    assert kind(host(call_frame("slow"))) == "timeout"
    assert (started, gated, _last(host).abandoned) == ([], [], False)
    assert _last(host).message == "slow timed out: the run's deadline is too near to start it"
    # Three ticks left: the call starts.
    host = _host([_blocking(release, started, timeout_s=0.01)], stop_at=13, ticks=Ticks(10))
    assert kind(host(call_frame("slow"))) == "timeout" and started == [1]

    # A fifth call while 4 are abandoned is answered at once; its work never starts.
    started.clear()
    host = _host([_blocking(release, started, timeout_s=0.01)])
    answers = [kind(host(call_frame("slow", id=i))) for i in range(6)]
    assert answers == ["timeout"] * 6
    assert len(started) == T._MAX_ABANDONED == 4
    outcomes = host.record.outcomes
    assert [o.abandoned for o in outcomes] == [True] * 4 + [False] * 2
    assert outcomes[4].message == "slow timed out: 4 earlier tool calls are still running"
    assert host.counted == [1, 1, 1, 1]  # four threads counted in, none out yet

    # A slot frees when its thread ends.
    release.set()
    for t in threading.enumerate():
        if t.name.startswith("wasi-python-tool-"):
            t.join(60)
    assert sum(host.counted) == 0
    assert kind(host(call_frame("slow", id=7))) is None  # released: it returns at once


def test_a_late_result_is_dropped_and_each_call_gets_its_own(release) -> None:
    started: list = []
    slow = _blocking(release, started, timeout_s=0.01)

    @tool
    def fast() -> str:
        """Answer at once, after the slow call's late result has arrived."""
        release.set()
        for t in threading.enumerate():
            if t.name.startswith("wasi-python-tool-slow"):
                t.join(60)
        return "fast's own"

    host = _host([slow, fast])
    assert kind(host(call_frame("slow"))) == "timeout"
    assert value(host(call_frame("fast"))) == "fast's own"
    assert [o.outcome for o in host.record.outcomes] == ["timeout", "ok"]


def test_a_thread_that_cannot_start_is_a_fault(release) -> None:
    started: list = []

    def refuse(thread: threading.Thread) -> None:
        raise RuntimeError("can't start new thread")

    host = _host([_blocking(release, started)], start=refuse)
    assert kind(host(call_frame("slow"))) == "tool_error"
    o = _last(host)
    assert (o.op, o.tool, o.outcome, o.abandoned) == ("call", "slow", "tool_error", False)
    assert o.message == "slow failed (internal error)"
    assert o.fault.startswith("RuntimeError"), o.fault
    assert (started, sum(host.counted)) == ([], 0)


def test_a_fault_in_the_bound_keeps_the_call_in_the_record(release) -> None:
    """The 031 build review's F5: if the bound fails after the tool started, the record still
    names the call and its tool, and says the tool may still run."""
    started: list = []
    seen = []

    def ticks() -> int:
        seen.append(1)
        if len(seen) > 1:
            raise ZeroDivisionError("the ticker broke")
        return 0

    host = _host([_blocking(release, started)], stop_at=100, ticks=ticks)
    assert kind(host(call_frame("slow"))) == "tool_error"
    o = _last(host)
    assert (o.op, o.tool, o.outcome, o.abandoned) == ("call", "slow", "tool_error", True)
    assert o.fault.startswith("ZeroDivisionError"), o.fault
    assert started == [1]


def test_the_tool_runs_in_a_copy_of_the_callers_context(release) -> None:
    import contextvars

    var = contextvars.ContextVar("request")
    seen = []

    @tool
    def where() -> str:
        """Say where it ran."""
        seen.append((var.get(None), threading.get_ident()))
        return "ok"

    var.set("from the caller")
    host = _host([where])
    assert value(host(call_frame("where"))) == "ok"
    assert seen[0][0] == "from the caller" and seen[0][1] != threading.get_ident()


# -------------------------------------------------------------------------------------------------
# The count of tool threads, the fork hook and the record's default.


def test_stats_counts_tool_threads() -> None:
    before = runner.stats()["tool_threads_running"]
    runner._count_tool_threads(1)
    assert runner.stats()["tool_threads_running"] == before + 1
    runner._count_tool_threads(-1)
    assert runner.stats()["tool_threads_running"] == before


FORK_HOOK = r"""
import os, sys
from wasi_python import runner

runner._count_tool_threads(7)  # as if seven tool threads ran in the parent
lock = runner._tool_threads_lock
pid = os.fork()
if pid == 0:
    fresh = runner._tool_threads_lock is not lock
    os.write(1, f"child {runner.stats()['tool_threads_running']} {fresh}\n".encode())
    os._exit(0)
os.waitpid(pid, 0)
print("parent", runner.stats()["tool_threads_running"])
"""


@pytest.mark.skipif(not hasattr(os, "fork"), reason="no fork on this system")
def test_the_fork_hook_resets_the_tool_thread_count() -> None:
    """Decision 8, in a forked child (the build review's F4): the child has none of its
    parent's tool threads, and a lock of its own. Run in a fresh process, since the hook
    rebinds every lock of the runner."""
    out = subprocess.run(
        [sys.executable, "-I", "-c", FORK_HOOK], capture_output=True, text=True, timeout=120
    )
    assert out.returncode == 0, out.stderr[-1500:]
    assert out.stdout.splitlines() == ["child 0 True", "parent 7"], out.stdout


def test_abandoned_calls_are_counted_past_the_listed_outcomes(release) -> None:
    """The build review's F2: with no frame limit, 1,000 `list` frames fill the listed
    outcomes; the four abandoned calls after them are still counted in `abandoned`."""
    started: list = []
    bound = T._Bounded(tick_s=0.001)
    host = T._ToolHost([_blocking(release, started, timeout_s=0.01)], max_calls=None, invoke=bound)
    listing = json.dumps({"v": 1, "id": 1, "op": "list"}).encode()
    for _ in range(T._RECORD_OUTCOMES):
        assert json.loads(host(listing))["ok"]
    assert [kind(host(call_frame("slow"))) for _ in range(5)] == ["timeout"] * 5
    record = host.record
    assert (record.frames, len(record.outcomes), record.unlisted) == (1005, 1000, 5)
    assert record.abandoned == 4  # the fifth was answered at once, never started
    assert T.ToolRecord(1, (), 0).abandoned == 0  # the field is last, with a default


def _held_slot(monkeypatch, hold: threading.Event, filled: threading.Event) -> None:
    """Make each slot's `filled.set()` hold the tool's thread after setting it, before the
    thread's `finally` runs: the window the build review's F3 found."""

    class Held(threading.Event):
        def set(self) -> None:
            super().set()
            filled.set()
            hold.wait(60)  # a fail-safe, not a timing: the check sets it

    made = T._Slot.__init__

    def init(self) -> None:
        made(self)
        self.filled = Held()

    monkeypatch.setattr(T._Slot, "__init__", init)


def test_a_result_that_finished_at_an_end_is_delivered(release) -> None:
    """The build review's F3, case A: the work finishes and its thread ends before the bound
    sees the deadline; its answer stands, and nothing is counted abandoned."""
    gate = threading.Event()

    @tool
    def quick() -> str:
        """Answer once released."""
        gate.wait(60)
        return "done"

    seen = []

    def ticks() -> int:
        seen.append(1)
        if len(seen) == 1:
            return 0  # before the start
        gate.set()
        for t in threading.enumerate():
            if t.name == "wasi-python-tool-quick":
                t.join(60)
        return 100  # past the deadline

    bound = T._Bounded(tick_s=0.001, stop_at=50, ticks=ticks)
    host = T._ToolHost([quick], invoke=bound)
    assert value(host(call_frame("quick"))) == "done"
    assert (_last(host).outcome, _last(host).abandoned, bound._abandoned) == ("ok", False, 0)


def test_a_result_filled_before_an_end_is_delivered(release, monkeypatch) -> None:
    """The build review's F3, case B: the work has filled its slot, but its thread has not yet
    reached its `finally`, when the bound sees the deadline. The result is in hand, so it is
    the answer, and the call is not counted abandoned, now or after the thread ends."""
    gate, hold, filled = threading.Event(), threading.Event(), threading.Event()
    _held_slot(monkeypatch, hold, filled)

    @tool
    def quick() -> str:
        """Answer once released."""
        gate.wait(60)
        return "done"

    seen = []

    def ticks() -> int:
        seen.append(1)
        if len(seen) == 1:
            return 0  # before the start
        gate.set()
        filled.wait(60)  # the slot is filled; its thread is held before its finally
        return 100  # past the deadline

    bound = T._Bounded(tick_s=0.001, stop_at=50, ticks=ticks)
    host = T._ToolHost([quick], invoke=bound)
    try:
        answer = host(call_frame("quick"))
        assert (_last(host).outcome, _last(host).abandoned, bound._abandoned) == ("ok", False, 0)
        assert value(answer) == "done"
    finally:
        hold.set()
        for t in threading.enumerate():
            if t.name == "wasi-python-tool-quick":
                t.join(60)
    assert bound._abandoned == 0


def test_a_call_ended_at_its_gate_never_runs_its_tool(release) -> None:
    """Spec 056 (the a4 security review's F2): the gate moves one end of the call (the tool's
    `timeout_s` on a fake clock, the deadline on a fake ticker, `cancel`), then waits until the
    call has been answered and released. It allows; the tool never runs, and the thread ends.
    A gate that allowed before the end still starts its tool, which then runs on (abandoned),
    as before."""
    ran: list = []
    gated: list = []

    def make(timeout_s=None):
        @tool(name="transfer", timeout_s=timeout_s)
        def transfer() -> str:
            """Move money."""
            ran.append(1)
            return "sent"

        return transfer

    moved, reads = threading.Event(), []

    def clock() -> float:  # the first read sets the call's end at 1.0; after the move, 9.0
        reads.append(1)
        return 9.0 if len(reads) > 1 and moved.is_set() else 0.0

    ticks = Ticks(0)
    cancel = threading.Event()
    ends = [
        ("timeout", make(1.0), dict(clock=clock), moved.set),
        ("timeout", make(), dict(stop_at=10, ticks=ticks), lambda: setattr(ticks, "n", 8)),
        ("cancelled", make(), dict(cancel=cancel), cancel.set),
    ]
    for want, transfer, kw, end in ends:
        answered = threading.Event()

        def gate(call, end=end, answered=answered):
            gated.append(call.seq)
            end()
            answered.wait(60)  # a fail-safe, not a timing: set once the host has answered
            return True

        counted: list = []
        bound = T._Bounded(tick_s=0.001, count=counted.append, **kw)
        host = T._ToolHost([transfer], gate=gate, invoke=bound)
        assert kind(host(call_frame("transfer"))) == want
        assert _last(host).abandoned is True
        answered.set()
        for t in threading.enumerate():
            if t.name == "wasi-python-tool-transfer":
                t.join(60)
        assert (ran, sum(counted), bound._abandoned) == ([], 0, 0)
    assert gated == [1, 1, 1]

    # The other order: the gate allowed, the tool started, then the call was cancelled.
    cancel = threading.Event()
    bound = T._Bounded(tick_s=0.001, cancel=cancel)
    slow = _blocking(release, ran, then=cancel.set)
    host = T._ToolHost([slow], gate=lambda call: True, invoke=bound)
    assert kind(host(call_frame("slow"))) == "cancelled"
    assert (_last(host).abandoned, ran) == (True, [1])


def test_the_tool_starts_only_if_its_call_was_not_answered() -> None:
    """Spec 056, F2: the check between the gate and the tool, and the mark of an answered call,
    are taken under one lock, so exactly one of them wins."""
    bound = T._Bounded(tick_s=0.001)
    slot = T._Slot()
    assert bound._abandon(slot) is True
    assert bound._proceed(slot) is False
    slot = T._Slot()
    assert bound._proceed(slot) is True
    assert bound._abandon(slot) is True  # the tool runs on, abandoned, as spec 036 says


def test_completed_has_no_tool_record_by_default() -> None:
    done = runner.Completed(0, b"", b"", None, None)
    assert done.tools is None and done.files is None
    assert runner.Completed.__dataclass_fields__.keys() >= {"tools"}
    assert list(runner.Completed.__dataclass_fields__)[-1] == "tools"
