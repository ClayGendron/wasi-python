"""v1.4: bounded sessions (spec 055). One instance of the guest kept across turns.

The first checks drive the `turn` and `shutdown` exports raw, with the judge's own driver; the
rest use `wasi_python.Session`, the runner's sessions, end to end on the built set. Nothing here
measures time: bounds are driven by an injected clock and the reaper's one step, a turn that
must block waits on an event the check sets, and a short deadline only chooses an outcome."""

from __future__ import annotations

import math
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import pytest

from harness import needs

pytestmark = pytest.mark.goal("v1.4")
BINARY = pytest.mark.parametrize("which", ["plain", "snapshot"])
LOOP = "while True:\n    pass\n"


# ---------------------------------------------------------------------------------------------
# The exports, driven raw (criteria 1 to 3, and 34)


@BINARY
def test_turn_keeps_the_interpreter(guest_turns, which) -> None:
    """Criterion 1."""
    t = guest_turns(which)
    a = t.turn("x = 41")
    assert a.value == 0, a.describe()
    b = t.turn("print(x + 1)")
    assert (b.value, b.stdout) == (0, b"42\n"), b.describe()
    c = t.turn("raise SystemExit(3)")
    assert c.value == 3, c.describe()
    d = t.turn("print(x)")
    assert (d.value, d.stdout) == (0, b"41\n"), d.describe()
    e = t.turn("exit(4)")
    assert e.value == 260, e.describe()  # 256 plus the status: the turn asked to end
    q = guest_turns(which)
    assert q.turn("quit()").value == 256
    g = guest_turns(which)
    made = g.turn("import _reactor\n_reactor._exit_code = lambda e: 300\nraise SystemExit")
    assert made.value == 44, made.describe()  # 300's low byte; a guest's status sets no bit
    huge = g.turn("import _reactor\n_reactor._exit_code = lambda e: 2**100 + 4\nraise SystemExit")
    assert (huge.value, huge.stderr) == (4, b""), huge.describe()


def test_run_and_turn_exclude_each_other(guest_turns) -> None:
    """Criterion 2."""
    ran = guest_turns("snapshot", argv=["-c", "pass"])
    assert ran.run().value == 0
    refused = ran.turn("print('ran')")
    assert (refused.value, refused.stdout, refused.stderr) == (-1, b"", b"")
    turned = guest_turns("snapshot")
    assert turned.turn("pass").value == 0
    second = turned.run()
    assert second.value == 70, second.describe()
    assert b"run() may be called once per instance, and not after turn()" in second.stderr
    assert turned.turn_raw(0, -1).value == -1
    assert turned.turn_raw(0, 0).value == 0  # an empty turn

    def host(instance, request: bytes) -> bytes:
        instance.call_from_door("turn", 0, 0)
        return b""

    door = guest_turns("snapshot", host=host)
    r = door.turn("import _host\n_host.call(b'x')\nprint('back')")
    assert (r.value, r.stdout) == (0, b"back\n"), r.describe()
    assert door.inner == [-1]  # a turn from the door during a turn is refused
    trapped = guest_turns("snapshot")
    assert trapped.turn(LOOP, fuel=10**8).trapped == "out of fuel"
    after = trapped.turn("print('after')")
    assert (after.value, after.stdout, after.stderr) == (-1, b"", b"")


@BINARY
def test_a_null_code_buffer_is_a_memory_error(guest_turns, which) -> None:
    """Criterion 3."""
    t = guest_turns(which)
    r = t.turn_raw(0, 10)
    assert r.value == 1, r.describe()
    assert r.stderr.decode().strip().splitlines()[-1] == (
        "MemoryError: no memory for this turn's code"
    )
    assert t.turn("print(1)").value == 0


SHUTDOWN_TURN = (
    "import atexit\n"
    "atexit.register(print, 'bye')\n"
    "f = open('/out.txt', 'w'); f.write('x' * 100)\n"
    "def g():\n"
    "    pass\n"
)


@BINARY
def test_the_shutdown_export_raw(guest_turns, which) -> None:
    """Criterion 34: Python's shutdown runs atexit and flushes a file left open beside a function
    defined in __main__ (the memo's P10b: the snapshot loses it without the unfreeze); then every
    export refuses."""
    t = guest_turns(which)
    assert t.turn(SHUTDOWN_TURN).value == 0
    s = t.shutdown()
    assert s.value == 0, s.describe()
    assert s.stdout.endswith(b"bye\n"), s.stdout
    assert (t.root / "out.txt").read_bytes() == b"x" * 100
    for after in (t.turn("print('again')"), t.shutdown()):
        assert (after.value, after.stdout, after.stderr) == (-1, b"", b""), after.describe()
    assert t.run().value == 70
    fresh = guest_turns(which)
    assert fresh.shutdown().value == -1
    ran = guest_turns(which, argv=["-c", "pass"])
    assert ran.run().value == 0
    assert ran.shutdown().value == -1
    trapped = guest_turns(which)
    assert trapped.turn(LOOP, fuel=10**8).trapped == "out of fuel"
    no = trapped.shutdown()
    assert (no.value, no.stdout, no.stderr) == (-1, b"", b"")

    def host(instance, request: bytes) -> bytes:
        instance.call_from_door("shutdown")
        return b""

    door = guest_turns(which, host=host)
    assert door.turn("import _host\n_host.call(b'during a turn')").value == 0
    assert door.inner == [-1]
    handler = "import atexit, _host\natexit.register(_host.call, b'during the shutdown')\n"
    assert door.turn(handler).value == 0
    outer = door.shutdown()
    assert outer.value == 0, outer.describe()
    assert door.inner == [-1, -1]  # CPython forbids it: refused, and the outer one went on


# ---------------------------------------------------------------------------------------------
# Sessions through the runner, end to end on the built set


def _wp():
    needs.need("runner", "artifact dir")
    import wasi_python

    return wasi_python


def _open_count() -> int:
    return _wp().stats()["sessions_open"]


@pytest.fixture
def fake_clock(monkeypatch):
    """The sessions' clock, a value the check sets; the reaper thread paused, so only the check
    drives `_reap` (Decision 9: the judge never sleeps)."""
    from wasi_python._process import process

    now = [0.0]
    monkeypatch.setattr(process().observers, "clock", lambda: now[0])
    monkeypatch.setattr(process().observers, "reaper_paused", True)
    return now


@pytest.fixture
def exports_called(monkeypatch):
    """Each export called on a session's instance: (name, thread ident)."""
    from wasi_python._process import process

    seen: list[tuple[str, int]] = []
    monkeypatch.setattr(
        process().observers, "on_export", lambda name, ident: seen.append((name, ident))
    )
    return seen


def _blocking_tool(started: threading.Event, release: threading.Event):
    def block() -> str:
        """Block until the check releases it."""
        started.set()
        release.wait(60)
        return "ok"

    return block


def _handler_writing(path: str, text: str = "ran") -> str:
    return (
        "import atexit\n"
        "def _h():\n"
        f"    with open({path!r}, 'w') as f:\n"
        f"        f.write({text!r})\n"
        "atexit.register(_h)\n"
    )


def test_a_turn_refuses_mistakes_and_the_session_stays_open() -> None:
    """Criterion 5."""
    with _wp().Session() as s:
        cases = [
            ((b"x",), {}),
            (("a\0b",), {}),
            (("\ud800",), {}),
            (("1",), {"fuel": 5}),
            (("1",), {"deadline_s": 0}),
            (("1",), {"output_bytes": -1}),
            (("1",), {"cancel": "yes"}),
        ]
        for args, kwargs in cases:
            with pytest.raises((TypeError, ValueError)):
                s.run(*args, **kwargs)
            assert s.ended is None
        assert s.run("print(1)").stdout == b"1\n"


def test_an_old_artifact_set_is_named(guest_workdir) -> None:
    """Criterion 6: a set whose snapshot lacks the session exports is named before any folder is
    made; `run` with the same set runs its `run` as before."""
    wp = _wp()
    from harness import wat
    from wasi_python._process import process

    real = wp.artifacts()
    for module, named, unnamed in (
        (wat.BEFORE_SESSIONS, "turn", None),
        (wat.TURN_ONLY, "shutdown", "turn"),
    ):
        d = Path(tempfile.mkdtemp(prefix="old-", dir=guest_workdir))
        old = wp.Artifacts(
            wat.build(d, "old.wasm", module), real.plain, real.stdlib_zip, real.manifest
        )
        held, before = set(process().held), _open_count()
        with pytest.raises(wp.ArtifactsMissing) as e:
            wp.Session(artifacts=old, cache_dir=False)
        assert named in str(e.value)
        if unnamed is not None:
            assert f"export {unnamed}" not in str(e.value)
        assert set(process().held) == held and _open_count() == before
        done = wp.run([], artifacts=old, cache_dir=False)
        assert done.exit_code == 101, done  # the stand-in's run: the door says no host


def test_one_turn_at_a_time() -> None:
    """Criterion 8."""
    wp = _wp()
    started, release = threading.Event(), threading.Event()
    holder: dict = {}

    def again() -> str:
        """Run a turn of this same session from inside its turn."""
        holder["s"].run("1")
        return "ran"

    with wp.Session(tools=[_blocking_tool(started, release), again]) as s:
        holder["s"] = s
        code = (
            "from host import tools\n"
            "try:\n    tools.again()\nexcept Exception as e:\n    print(type(e).__name__)\n"
            "print(tools.block())\n"
        )
        result: dict = {}
        t = threading.Thread(target=lambda: result.setdefault("r", s.run(code)))
        t.start()
        assert started.wait(60)
        with pytest.raises(RuntimeError, match="already running"):
            s.run("1")
        release.set()
        t.join(60)
        r = result["r"]
        assert r.exit_code == 0 and r.stdout.endswith(b"ok\n"), r
        faults = [o.fault or "" for o in r.tools.outcomes if o.outcome == "tool_error"]
        assert faults and faults[0].startswith("RuntimeError"), r.tools.outcomes
        assert s.run("print(2)").stdout == b"2\n"

    def host(frame: bytes) -> bytes:
        holder["h"].run("1")
        return b"no"

    with wp.Session(host=host) as h:
        holder["h"] = h
        code = "import _host\ntry:\n    _host.call(b'x')\nexcept OSError:\n    print('fault')\n"
        r = h.run(code)
        assert (r.exit_code, r.stdout) == (0, b"fault\n"), r


def test_state_crosses_turns() -> None:
    """Criterion 9."""
    with _wp().Session() as s:
        turns = [
            "x = 41",
            "def double(v): return v * 2",
            "class P: k = 1",
            "square = lambda v: v * v",
            "import pandas as pd; df = pd.DataFrame({'a': [1, 2, 3]})",
            "print(double(x) + P.k, square(3), int(df.a.sum()))",
        ]
        results = [s.run(t) for t in turns]
        assert all(r.exit_code == 0 for r in results), results
        assert results[-1].stdout == b"83 9 6\n"
        assert s.ended is None


def test_the_last_expression_is_echoed() -> None:
    """Criterion 10."""
    with _wp().Session() as s:
        assert s.run("x = 41").stdout == b""
        assert s.run("x + 1").stdout == b"42\n"
        assert s.run("None").stdout == b""
        assert s.run("print(1); 2").stdout == b"1\n2\n"
        assert s.run("_ * 2").stdout == b"4\n"
        assert s.run("def f(): pass").stdout == b""


def test_an_exception_or_an_exit_keeps_the_session() -> None:
    """Criterion 11 (exit() and quit() end the session: criterion 41)."""
    with _wp().Session() as s:
        assert s.run("x = 1\ndef boom():\n    raise ValueError('from turn 1')").exit_code == 0
        r = s.run("1/0")
        assert r.exit_code == 1 and r.stderr.endswith(b"ZeroDivisionError: division by zero\n")
        assert b"<turn 2>" in r.stderr and b"1/0" in r.stderr, r.stderr
        r = s.run("boom()")
        assert r.exit_code == 1 and b"raise ValueError('from turn 1')" in r.stderr, r.stderr
        assert s.run("raise SystemExit(3)").exit_code == 3
        r = s.run("import sys; sys.exit('bye')")
        assert (r.exit_code, r.stderr) == (1, b"bye\n"), r
        assert s.run("print(x)").stdout == b"1\n"
        assert s.ended is None


def test_os_exit_and_a_trap_end_the_session() -> None:
    """Criterion 12."""
    wp = _wp()
    before = _open_count()
    s = wp.Session()
    r = s.run("import os; os._exit(4)")
    assert (r.exit_code, r.trapped) == (4, None), r
    assert (s.ended, s.shutdown_outcome) == ("exit", "skipped")
    with pytest.raises(wp.SessionEnded) as e:
        s.run("1")
    assert e.value.reason == "exit"
    assert _open_count() == before
    s = wp.Session(fuel=10**9)
    r = s.run(LOOP)
    assert (r.trapped, r.exit_code, s.ended) == ("out of fuel", None, "out of fuel"), r
    s = wp.Session()
    r = s.run(LOOP, deadline_s=0.5)
    assert (r.trapped, s.ended, s.shutdown_outcome) == ("deadline", "deadline", "skipped"), r
    stop = threading.Event()

    def halt() -> str:
        """Set the turn's cancel."""
        stop.set()
        return "set"

    s = wp.Session(tools=[halt])
    r = s.run("from host import tools\ntools.halt()\n" + LOOP, cancel=stop)
    assert (r.trapped, s.ended) == ("cancelled", "cancelled"), r
    assert _open_count() == before
    with wp.Session() as s:
        s.run("y = 5")
        early = threading.Event()
        early.set()
        r = s.run("print('ran')", cancel=early)
        assert (r.trapped, r.fuel_used, r.stdout, s.ended) == ("cancelled", None, b"", None)
        assert s.run("print(y)").stdout == b"5\n"


def test_the_idle_bound_by_an_injected_clock(fake_clock) -> None:
    """Criterion 13."""
    wp = _wp()
    from wasi_python import _sessions

    before = _open_count()
    s = wp.Session()
    assert s.run("pass").exit_code == 0
    fake_clock[0] = 899.9
    assert s.run("pass").exit_code == 0
    fake_clock[0] = 899.9 + 900.0
    with pytest.raises(wp.SessionEnded) as e:
        s.run("pass")
    assert (e.value.reason, s.ended) == ("idle", "idle")
    assert _open_count() == before
    with wp.Session(idle_s=None, lifetime_s=None) as forever:
        fake_clock[0] = 10**6
        assert forever.run("pass").exit_code == 0
    untouched = wp.Session()
    _sessions._reap(fake_clock[0] + 900.0)
    untouched.close()  # waits for the closer the reaper started
    assert untouched.ended == "idle"


def test_the_lifetime_by_an_injected_clock(fake_clock, monkeypatch) -> None:
    """Criterion 14."""
    wp = _wp()
    from wasi_python import _limits
    from wasi_python._process import process

    s = wp.Session()
    for t in range(0, 3600, 600):
        fake_clock[0] = float(t)
        assert s.run("pass").exit_code == 0
    fake_clock[0] = 3600.0
    with pytest.raises(wp.SessionEnded) as e:
        s.run("pass")
    assert e.value.reason == "lifetime"

    def late() -> str:
        """Move the sessions' clock past the lifetime."""
        fake_clock[0] = 3601.0
        return "late"

    fake_clock[0] = 0.0
    s = wp.Session(tools=[late], idle_s=None)
    fake_clock[0] = 3000.0
    r = s.run("from host import tools\nprint(tools.late())")
    assert (r.exit_code, r.stdout, s.ended) == (0, b"late\n", "lifetime"), r
    armed: list[tuple[str, int]] = []
    monkeypatch.setattr(
        process().observers, "on_arm", lambda kind, ticks: armed.append((kind, ticks))
    )
    fake_clock[0] = 0.0
    s = wp.Session(idle_s=None)
    fake_clock[0] = 3599.5
    r = s.run(LOOP)
    assert (r.trapped, s.ended) == ("deadline", "lifetime"), r
    assert armed[0] == ("turn", math.ceil(0.5 / _limits.TICK_S)), armed
    fake_clock[0] = 0.0
    s = wp.Session()
    r = s.run(LOOP, deadline_s=0.5)
    assert (r.trapped, s.ended) == ("deadline", "deadline"), r
    s = wp.Session(idle_s=None)
    fake_clock[0] = 3599.5
    r = s.run(LOOP, deadline_s=None)
    assert (r.trapped, s.ended) == ("deadline", "lifetime"), r
    fake_clock[0] = 0.0
    with wp.Session(lifetime_s=None, idle_s=None) as forever:
        fake_clock[0] = 10**6
        assert forever.run("pass").exit_code == 0


def test_per_turn_limits_are_per_turn() -> None:
    """Criterion 15."""
    wp = _wp()
    work = "def work():\n    t = 0\n    for i in range(300_000):\n        t += i\n    return t\n"
    with wp.Session(fuel=10**10) as probe:
        probe.run(work)
        cost = probe.run("work()").fuel_used
    budget = cost * 3 // 2
    with wp.Session(fuel=budget) as s:
        assert s.run(work).exit_code == 0
        used = [s.run("work()") for _ in range(3)]
        assert all(r.exit_code == 0 and r.fuel_used <= budget for r in used), used
        assert sum(r.fuel_used for r in used) > budget
    with wp.Session(output_bytes=1000) as s:
        r = s.run("print('x' * 1999)")
        assert (len(r.stdout), r.truncated) == (1000, ("stdout",)), r
        r = s.run("print('ok')")
        assert (r.stdout, r.truncated) == (b"ok\n", ()), r

    def ping() -> str:
        """Answer."""
        return "pong"

    with wp.Session(tools=[ping], max_tool_calls=2) as s:
        a = s.run("from host import tools\ntools.ping()")
        assert [(o.op, o.outcome) for o in a.tools.outcomes] == [("list", "ok"), ("call", "ok")]
        b = s.run(
            "for _ in range(3):\n"
            "    try:\n        tools.ping()\n    except Exception:\n        pass\n"
        )
        assert [o.outcome for o in b.tools.outcomes] == ["ok", "ok", "budget_exceeded"], b.tools
        c = s.run("tools.ping(); tools.ping()")
        assert [(o.op, o.outcome) for o in c.tools.outcomes] == [("call", "ok"), ("call", "ok")]


SIX = [
    "pass",
    "x = 41",
    "def double(v): return v * 2",
    "class P: k = 1",
    "square = lambda v: v * v",
    "print(double(x) + P.k, square(3))",
]


def test_turn_fuel_repeats() -> None:
    """Criterion 16: turns 2 to 6 of two sessions agree within 1,000 instructions."""
    wp = _wp()
    counts = []
    for _ in range(2):
        with wp.Session(fuel=10**10) as s:
            counts.append([s.run(t).fuel_used for t in SIX])
    spread = max(abs(a - b) for a, b in zip(counts[0][1:], counts[1][1:], strict=True))
    assert spread <= 1000, counts


def test_memory_is_per_session_and_not_a_trap() -> None:
    """Criterion 17."""
    with _wp().Session(memory_bytes=256 * 2**20) as s:
        r = s.run("import numpy as np\nnp.zeros(300_000_000, np.int8)")
        assert r.exit_code == 1 and b"_ArrayMemoryError" in r.stderr, r
        fill = (
            "keep = []\n"
            "try:\n    while True:\n        keep.append(bytearray(1 << 16))\n"
            "except MemoryError:\n    pass\n"
        )
        assert s.run(fill).exit_code == 0
        big = s.run("#" + "x" * (1 << 20))
        assert big.exit_code == 1, big
        assert big.stderr.decode().strip().splitlines()[-1] == (
            "MemoryError: no memory for this turn's code"
        )
        assert s.run("del keep").exit_code == 0
        assert s.ended is None


def test_mounts_and_grants_across_turns(guest_workdir) -> None:
    """Criterion 18."""
    wp = _wp()
    from harness.files import MemoryProvider

    p = MemoryProvider({})
    with wp.Session(mounts=[wp.Mount(p, "/m", writable=True)]) as s:
        r = s.run(
            "import os\nfd = os.open('/m/out.txt', os.O_WRONLY | os.O_CREAT)\nos.write(fd, b'a')"
        )
        # The create is the provider's empty write; the turn's own bytes arrive as it returns.
        assert r.exit_code == 0 and p.writes("/out.txt")[-1:] == [b"a"], (r, p.log)
        first = dict(r.files.calls)
        r = s.run("os.write(fd, b'b')\nos.close(fd)")
        assert p.writes("/out.txt")[-1] == b"ab", p.log
        assert dict(r.files.calls) != first or sum(r.files.calls.values()) <= sum(first.values())
    host = Path(tempfile.mkdtemp(prefix="grant-", dir=guest_workdir))
    with wp.Session(grants=[wp.Grant(host, "/w", writable=True)]) as s:
        assert s.run("open('/w/one.txt', 'w').write('1')").exit_code == 0
        assert (host / "one.txt").read_text() == "1"
    p = MemoryProvider({})
    s = wp.Session(mounts=[wp.Mount(p, "/m", writable=True)], max_file_calls=3)
    r = s.run("import os\nfor i in range(10):\n    os.path.exists(f'/m/{i}')\n")
    assert (r.trapped, s.ended) == ("out of file calls", "out of file calls"), r
    # A refused write-back stays dirty, and the next turn's ending offers it (the review's F7).
    opening = "import os\nfd = os.open('/m/f.txt', os.O_WRONLY | os.O_CREAT)\nos.write(fd, b'z')\n"
    p = MemoryProvider({})
    with wp.Session(mounts=[wp.Mount(p, "/m", writable=True)]) as pilot:
        r = pilot.run(opening)
        used = sum(r.files.calls.values()) - 1  # less the ending's own write-back
    p = MemoryProvider({})
    with wp.Session(mounts=[wp.Mount(p, "/m", writable=True)], max_file_calls=used + 2) as s:
        r = s.run(opening + "os.path.exists('/m/a')\nos.path.exists('/m/b')\n")
        assert r.trapped is None, r
        assert [w.cause for w in r.files.refused] == ["limit"], r.files
        assert [w for w in p.writes("/f.txt") if w] == []  # only the create's empty write
        s.run("pass")
        assert [w for w in p.writes("/f.txt") if w] == [b"z"], p.log


def test_sessions_share_nothing() -> None:
    """Criterion 19."""
    wp = _wp()
    before = _open_count()
    a, b = wp.Session(root=True), wp.Session(root=True)
    assert _open_count() == before + 2
    order = []

    def turns(s, x):
        order.append(s.run(f"x = {x}\n_ = open('/mine.txt', 'w').write('{x}')"))
        order.append(s.run("print(x, __import__('os').listdir('/'))"))

    ta = threading.Thread(target=turns, args=(a, 1))
    tb = threading.Thread(target=turns, args=(b, 2))
    ta.start(), tb.start()
    ta.join(60), tb.join(60)
    outs = sorted(r.stdout for r in order if r.stdout)
    assert outs[0].startswith(b"1 ") and outs[1].startswith(b"2 "), outs
    a.close(), b.close()
    assert _open_count() == before


def test_close_ends_and_cleans_up() -> None:
    """Criterion 21."""
    wp = _wp()
    from wasi_python._process import process

    held = set(process().held)
    s = wp.Session(root=True, shutdown_s=60)
    assert len(set(process().held) - held) == 2  # the private root and the scratch folder
    assert s.run("pass").exit_code == 0
    s.close()
    assert (s.ended, s.shutdown_outcome) == ("closed", "finished")
    assert set(process().held) == held
    s.close()
    with pytest.raises(wp.SessionEnded) as e:
        s.run("pass")
    assert e.value.reason == "closed"
    never = wp.Session()
    never.close()
    assert never.shutdown_outcome == "skipped"
    with pytest.raises(ZeroDivisionError):
        with wp.Session() as w:
            raise ZeroDivisionError
    assert w.ended == "closed"
    started, release = threading.Event(), threading.Event()
    s = wp.Session(tools=[_blocking_tool(started, release)])
    events: list[str] = []

    def turn():
        r = s.run("from host import tools\ntools.block()")
        events.append(f"turn {r.trapped}")

    t = threading.Thread(target=turn)
    t.start()
    assert started.wait(60)
    s.close()
    events.append("closed")
    release.set()
    t.join(60)
    assert events == ["turn cancelled", "closed"], events
    assert (s.ended, s.shutdown_outcome) == ("closed", "skipped")


def test_run_async_on_a_session() -> None:
    """Criterion 22."""
    import asyncio
    import concurrent.futures

    wp = _wp()
    started, release = threading.Event(), threading.Event()

    async def main() -> None:
        with wp.Session() as s:
            r = await s.run_async("print(3)")
            assert (r.exit_code, r.stdout) == (0, b"3\n"), r
        pool = concurrent.futures.ThreadPoolExecutor(1)
        s = wp.Session(tools=[_blocking_tool(started, release)])
        task = asyncio.ensure_future(
            s.run_async("from host import tools\ntools.block()", executor=pool)
        )
        await asyncio.get_running_loop().run_in_executor(None, started.wait, 60)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert s.ended == "cancelled"
        with wp.Session() as t:
            assert (await t.run_async("print(4)", executor=pool)).stdout == b"4\n"
        busy = threading.Event()
        blocker = pool.submit(busy.wait, 60)
        with wp.Session() as q:
            queued = asyncio.ensure_future(q.run_async("print(5)", executor=pool))
            await asyncio.sleep(0)
            queued.cancel()
            with pytest.raises(asyncio.CancelledError):
                await queued
            busy.set()
            blocker.result(60)
            assert q.ended is None
            assert (await q.run_async("print(6)", executor=pool)).stdout == b"6\n"
        pool.shutdown()

    asyncio.run(main())
    release.set()


def _child(script: str, *args: str) -> list[str]:
    _wp()
    out = subprocess.run(
        [sys.executable, "-c", script, *args], capture_output=True, text=True, timeout=120
    )
    assert out.returncode == 0, (out.returncode, out.stderr[-1500:])
    return out.stdout.splitlines()


CTRL_C = r"""
import signal, threading
signal.signal(signal.SIGINT, signal.default_int_handler)
import wasi_python

def go() -> str:
    "Send this process Ctrl-C."
    signal.raise_signal(signal.SIGINT)
    return "sent"

s = wasi_python.Session(tools=[go])
try:
    s.run("from host import tools\ntools.go()\nwhile True:\n    pass\n")
    print("returned")
except KeyboardInterrupt:
    print("KeyboardInterrupt", s.ended)
"""


def test_ctrl_c_during_a_turn() -> None:
    """Criterion 23."""
    assert _child(CTRL_C) == ["KeyboardInterrupt error"]


FORK = r"""
import os, sys, tempfile
import wasi_python
s = wasi_python.Session(root=True)
s.run("open('/kept.txt', 'w').write('k')")
pid = os.fork()
if pid == 0:
    try:
        s.run("pass")
        print("child ran", flush=True)
    except RuntimeError:
        print("child refused", flush=True)
    s.close()
    os._exit(0)
os.waitpid(pid, 0)
print(s.run("print(open('/kept.txt').read())").stdout.decode().strip())
s.close()
"""

EXIT_HOOK = r"""
import sys
import wasi_python
from wasi_python import runner
from wasi_python._process import process
grant = sys.argv[1]
g = [wasi_python.Grant(grant, "/g", writable=True)]
s = wasi_python.Session(root=True, shutdown_s=60, grants=g)
s.run(HANDLER)
print(" ".join(sorted(process().held)))
"""

DROPPED = r"""
import gc, sys
import wasi_python
from wasi_python import runner, _sessions
from wasi_python._process import process
process().observers.reaper_enabled = False  # the check drives the reaper's step
grant = sys.argv[1]
s = wasi_python.Session(shutdown_s=60, grants=[wasi_python.Grant(grant, "/g", writable=True)])
s.run(HANDLER)
before = wasi_python.stats()["sessions_open"]
del s
with process().sessions_lock:  # the finalizer takes no lock: it returns while this is held
    gc.collect()
_sessions._reap(process().observers.clock())
for closer in list(process().closers):
    closer.join()
print(before, wasi_python.stats()["sessions_open"])
"""

QUEUED_AT_EXIT = r"""
import gc, sys
import wasi_python
from wasi_python import runner
from wasi_python._process import process
process().observers.reaper_enabled = False  # no reaper: the state is on the queue at exit
grant = sys.argv[1]
s = wasi_python.Session(shutdown_s=60, grants=[wasi_python.Grant(grant, "/g", writable=True)])
s.run(HANDLER)
del s
gc.collect()
print("exiting")
"""


EXIT_MOUNT = r"""
import asyncio, sys
import wasi_python
from wasi_python import Errno, Mount, Session, Stat

log = sys.argv[1]


class Provider:
    "A writable provider that logs every write to a file the parent reads."

    def __init__(self):
        self.files = {}

    def stat(self, path):
        if path == "/":
            return Stat("dir", 0)
        return Stat("file", len(self.files[path])) if path in self.files else Errno.ENOENT

    def list(self, path):
        return [(p[1:], "file") for p in self.files] if path == "/" else Errno.ENOTDIR

    def read(self, path):
        return self.files.get(path, Errno.ENOENT)

    def write(self, path, data):
        self.files[path] = bytes(data)
        with open(log, "a") as f:
            f.write(f"{path} {bytes(data)!r}\n")

    def mkdir(self, path):
        return Errno.EPERM

    def remove(self, path):
        self.files.pop(path, None)

    def rmdir(self, path):
        return Errno.EPERM

    def rename(self, src, dst):
        self.files[dst] = self.files.pop(src)


asyncio.run(wasi_python.run_async(["-c", "pass"]))  # registers run_async's exit hook first
s = Session(mounts=[Mount(Provider(), "/m", writable=True)], shutdown_s=60)
s.run(
    "import os, atexit\n"
    "def h():\n    late = os.open('/m/late.txt', os.O_WRONLY | os.O_CREAT)\n"
    "    os.write(late, b'late')\n"
    "atexit.register(h)\n"
)
print("exiting")
"""


def test_fork_exit_and_the_collector(guest_workdir) -> None:
    """Criterion 24."""
    if hasattr(os, "fork"):
        assert _child(FORK) == ["child refused", "k"]
    handler = repr(_handler_writing("/g/handler.txt"))
    for name, script, want in (
        ("exit", EXIT_HOOK, None),
        ("dropped", DROPPED, None),
        ("queued", QUEUED_AT_EXIT, ["exiting"]),
    ):
        grant = Path(tempfile.mkdtemp(prefix=f"{name}-", dir=guest_workdir))
        lines = _child(script.replace("HANDLER", handler), str(grant))
        assert (grant / "handler.txt").read_text() == "ran", (name, lines)
        if name == "exit":
            temp = Path(tempfile.gettempdir())
            assert lines and all(not (temp / n).exists() for n in lines[0].split()), lines
        if name == "dropped":
            before, after = map(int, lines[-1].split())
            assert after == before - 1, lines
        if want is not None:
            assert lines == want
    # The build review's F1: at exit, after run_async has run once in the process (its exit
    # hook sets the interpreter's "exiting" flag first), the ending's write-back still reaches
    # a mount: the handler's descriptor, written and never closed, is handed over by the walk.
    log = Path(tempfile.mkdtemp(prefix="mount-", dir=guest_workdir)) / "writes.log"
    assert _child(EXIT_MOUNT, str(log)) == ["exiting"]
    assert "/late.txt b'late'" in log.read_text().splitlines(), log.read_text()


def test_a_session_on_the_plain_reactor() -> None:
    """Criterion 25."""
    with _wp().Session(snapshot=False) as s:
        a, b = s.run("print(1)"), s.run("print(2)")
        assert (a.exit_code, a.stdout, b.exit_code, b.stdout) == (0, b"1\n", 0, b"2\n")


def test_the_import_path_in_a_session(guest_workdir) -> None:
    """Criterion 30."""
    wp = _wp()
    from wasi_python._process import process

    lib = Path(tempfile.mkdtemp(prefix="lib-", dir=guest_workdir))
    (lib / "mylib.py").write_text("def boom():\n    raise ValueError('boom')\n")
    with wp.Session(grants=[wp.Grant(lib, "/lib")], import_path=["/lib"]) as s:
        r = s.run("import sys, mylib\nmylib.boom()")
        assert r.exit_code == 1 and b'File "<turn 1>", line 2' in r.stderr, r.stderr
        assert r.stdout == b""
        assert s.run("print(sys.path[-1])").stdout == b"/lib\n"
    w = Path(tempfile.mkdtemp(prefix="w-", dir=lib))
    held = set(process().held)
    with pytest.raises(ValueError, match="writable"):
        wp.Session(
            grants=[wp.Grant(lib, "/lib"), wp.Grant(w, "/lib/w", writable=True)],
            import_path=["/lib"],
        )
    assert set(process().held) == held


def test_a_turn_waits_on_the_sessions_clock_base_end_to_end(monkeypatch) -> None:
    """Criterion 31, its end-to-end part: each turn's call counts from the session's base."""
    wp = _wp()
    from wasi_python._process import process

    bases: list[int] = []
    monkeypatch.setattr(
        process().observers, "on_call", lambda kind, call: bases.append(call.origin_ns)
    )
    with wp.Session() as s:
        for _ in range(3):
            s.run("import time; time.sleep(0.01)")
    assert len(bases) >= 3 and bases[0] == bases[2], bases


def test_a_guest_cannot_make_session_run_raise() -> None:
    """Criterion 32."""
    with _wp().Session() as s:
        assert s.run("import _reactor\n_reactor.turn = lambda s, e: -1").exit_code == 0
        assert s.run("print(1)").stdout == b"1\n"
        assert s.run("_reactor._exit_code = lambda e: 300\nraise SystemExit").exit_code == 44
        assert s.run("_reactor._exit_code = lambda e: 'x'\nraise SystemExit").exit_code == 1
        assert s.run("del __import__('sys').modules['_reactor']").exit_code == 0
        assert s.run("print(2)").stdout == b"2\n"
        assert s.run("import atexit\natexit.register(print, 'handler ran')").exit_code == 0
        eight = (
            "def _raise(e):\n    raise SystemExit(9)\n"
            "_reactor._exit_code = _raise\nraise SystemExit"
        )
        r = s.run(eight)
        assert (r.exit_code, s.ended) == (1, None), r
        assert b"handler ran" not in r.stdout + r.stderr
        assert s.ended is None


def test_close_on_the_turns_own_thread() -> None:
    """Criterion 33."""
    wp = _wp()
    holder: dict = {}

    def host(frame: bytes) -> bytes:
        holder["s"].close()
        return b""

    s = wp.Session(host=host)
    holder["s"] = s
    r = s.run("import _host\n_host.call(b'x')\n" + LOOP)
    assert (r.trapped, s.ended) == ("cancelled", "closed"), r


def test_close_runs_python_shutdown(guest_workdir) -> None:
    """Criterion 35."""
    wp = _wp()
    from harness.files import MemoryProvider

    host = Path(tempfile.mkdtemp(prefix="close-", dir=guest_workdir))
    with wp.Session(grants=[wp.Grant(host, "/w", writable=True)], shutdown_s=60) as s:
        assert s.run(_handler_writing("/w/atexit.txt")).exit_code == 0
        assert (
            s.run("f = open('/w/buffered.txt', 'w'); f.write('x' * 100)\ndef g(): pass").exit_code
            == 0
        )
    assert (s.ended, s.shutdown_outcome) == ("closed", "finished")
    assert (host / "atexit.txt").read_text() == "ran"
    assert (host / "buffered.txt").stat().st_size == 100
    p = MemoryProvider({})
    with wp.Session(mounts=[wp.Mount(p, "/m", writable=True)], shutdown_s=60) as s:
        s.run("f = open('/m/buffered.txt', 'w'); f.write('x' * 100)\ndef g(): pass")
        assert b"x" * 100 not in p.writes("/buffered.txt")  # still in Python's buffer
    assert p.writes("/buffered.txt")[-1] == b"x" * 100, p.log
    skip = Path(tempfile.mkdtemp(prefix="skip-", dir=guest_workdir))
    with wp.Session(grants=[wp.Grant(skip, "/w", writable=True)], shutdown_s=0) as s:
        s.run(_handler_writing("/w/atexit.txt"))
        s.run("f = open('/w/buffered.txt', 'w'); f.write('x' * 100)")
    assert s.shutdown_outcome == "skipped"
    assert not (skip / "atexit.txt").exists()
    assert (skip / "buffered.txt").stat().st_size == 0


def test_expiry_runs_python_shutdown(
    guest_workdir, fake_clock, monkeypatch, exports_called
) -> None:
    """Criterion 36, the re-review's F2 included."""
    wp = _wp()
    from wasi_python import _limits, _sessions
    from wasi_python._process import process

    def session(name: str, **kw):
        fake_clock[0] = 0.0
        host = Path(tempfile.mkdtemp(prefix=f"{name}-", dir=guest_workdir))
        s = wp.Session(grants=[wp.Grant(host, "/w", writable=True)], **kw)
        assert s.run(_handler_writing("/w/h.txt")).exit_code == 0
        return s, host / "h.txt"

    s, written = session("idle", shutdown_s=60)
    fake_clock[0] = 900.0
    _sessions._reap(900.0)
    s.close()
    assert (s.ended, s.shutdown_outcome, written.read_text()) == ("idle", "finished", "ran")
    s, written = session("lifetime", shutdown_s=60, idle_s=None)
    fake_clock[0] = 3600.0
    _sessions._reap(3600.0)
    s.close()
    assert (s.ended, s.shutdown_outcome, written.read_text()) == ("lifetime", "finished", "ran")

    def late() -> str:
        """Move the sessions' clock past the lifetime."""
        fake_clock[0] = 3600.5
        return "late"

    fake_clock[0] = 0.0
    host = Path(tempfile.mkdtemp(prefix="turn-", dir=guest_workdir))
    s = wp.Session(grants=[wp.Grant(host, "/w", writable=True)], tools=[late], shutdown_s=60)
    s.run(_handler_writing("/w/h.txt"))
    r = s.run("from host import tools\ntools.late()")
    assert r.exit_code == 0 and (host / "h.txt").read_text() == "ran", r
    assert (s.ended, s.shutdown_outcome) == ("lifetime", "finished")
    s, written = session("capped", shutdown_s=60, idle_s=None)
    fake_clock[0] = 3599.5
    r = s.run(LOOP)
    assert (r.trapped, s.shutdown_outcome) == ("deadline", "skipped"), r
    assert not written.exists()
    armed: list[tuple[str, int]] = []
    monkeypatch.setattr(
        process().observers, "on_arm", lambda kind, ticks: armed.append((kind, ticks))
    )
    s, written = session("late", shutdown_s=5, idle_s=None)
    fake_clock[0] = 3602.0
    _sessions._reap(3602.0)
    s.close()
    assert ("ending", math.ceil(3 / _limits.TICK_S)) in armed, armed
    assert written.read_text() == "ran"
    for when, how in ((3605.0, "reaper"), (3610.0, "close")):
        s, written = session(how, shutdown_s=5, idle_s=None)
        exports_called.clear()
        fake_clock[0] = when
        if how == "reaper":
            _sessions._reap(when)
        s.close()
        assert (s.shutdown_outcome, written.exists()) == ("skipped", False), how
        assert [n for n, _ in exports_called if n == "shutdown"] == [], how


HOG = "import atexit\natexit.register(lambda: [0 for _ in iter(int, 1)])\n"


def test_a_hostile_atexit_is_stopped(guest_workdir) -> None:
    """Criterion 37, the re-review's F5 included."""
    wp = _wp()
    from wasi_python._process import process

    before, held = _open_count(), set(process().held)

    def ends(s, want: str) -> None:
        s.close()
        assert (s.ended, s.shutdown_outcome) == ("closed", want)
        assert _open_count() == before and set(process().held) == held

    s = wp.Session(fuel=10**9, shutdown_s=600)  # the fail-safe comes first if fuel did not bound it
    s.run(HOG)
    ends(s, "stopped")
    burn = "def burn():\n    t = 0\n    for i in range(N):\n        t += i\n"
    with wp.Session(fuel=10**11) as probe:
        probe.run(burn.replace("N", "100_000"))
        per = probe.run("burn()").fuel_used / 100_000
    n = int(10**9 / per)
    handler = burn.replace("N", str(n)) + "import atexit\natexit.register(burn)\n"
    s = wp.Session(fuel=4 * 10**9, shutdown_s=600)
    assert s.run(handler).exit_code == 0
    ends(s, "finished")
    s = wp.Session(fuel=10**9, shutdown_s=600)
    assert s.run(handler).exit_code == 0
    ends(s, "stopped")
    s = wp.Session(shutdown_s=0.5)
    s.run("import atexit\ndef spin():\n    while True:\n        pass\natexit.register(spin)\n")
    ends(s, "stopped")
    s = wp.Session(shutdown_s=0.5)
    s.run("import atexit, time\natexit.register(time.sleep, 10**6)\n")
    ends(s, "stopped")
    s = wp.Session(shutdown_s=60)
    s.run(
        "import atexit, sys\ndef h():\n    atexit.register(print, 'b')\n    sys.exit(7)\n"
        "atexit.register(h)\n"
    )
    ends(s, "finished")
    host = Path(tempfile.mkdtemp(prefix="exit-", dir=guest_workdir))
    s = wp.Session(grants=[wp.Grant(host, "/w", writable=True)], shutdown_s=60)
    s.run(_handler_writing("/w/h.txt") + "import os\natexit.register(os._exit, 5)\n")
    ends(s, "finished")
    assert not (host / "h.txt").exists()


def test_no_guest_code_after_a_stopped_ending(exports_called) -> None:
    """Criterion 38, the re-review's F4 included."""
    wp = _wp()
    from harness.files import MemoryProvider

    count = [0]

    def host(frame: bytes) -> bytes:
        count[0] += 1
        return b""

    s = wp.Session(host=host, shutdown_s=0.5)
    s.run(
        "import atexit, _host\ndef again():\n    while True:\n        _host.call(b'x')\n"
        "atexit.register(again)\n"
    )
    exports_called.clear()
    s.close()
    assert s.shutdown_outcome == "stopped"
    assert [n for n, _ in exports_called] == ["shutdown"]  # one call, and nothing after it
    seen = count[0]
    with wp.Session() as other:
        other.run("print(1)")
    assert count[0] == seen
    calls = [0]

    def ping() -> str:
        """Count."""
        calls[0] += 1
        return "p"

    s = wp.Session(tools=[ping], shutdown_s=0.5)
    s.run(
        "import atexit\nfrom host import tools\n"
        "def again():\n    while True:\n        try:\n            tools.ping()\n"
        "        except Exception:\n            pass  # past its budget: on until the deadline\n"
        "atexit.register(again)\n"
    )
    s.close()
    assert s.shutdown_outcome == "stopped"
    seen = calls[0]
    with wp.Session() as other:
        other.run("print(1)")
    assert calls[0] == seen
    p = MemoryProvider({})

    def interrupt(frame: bytes) -> bytes:
        raise KeyboardInterrupt

    before = _open_count()
    s = wp.Session(host=interrupt, mounts=[wp.Mount(p, "/m", writable=True)], shutdown_s=60)
    s.run(
        "f = open('/m/out.txt', 'w'); f.write('abc')\nimport atexit, _host\n"
        "def h():\n    f.flush()\n    _host.call(b'x')\natexit.register(h)\n"
    )
    with pytest.raises(KeyboardInterrupt):
        s.close()
    assert _open_count() == before
    assert s.shutdown_outcome == "stopped"
    assert [w for w in p.writes("/out.txt") if w] == [], p.log  # only the create's empty write


def test_no_shutdown_after_a_trap_or_exit(guest_workdir, exports_called) -> None:
    """Criterion 39."""
    wp = _wp()
    started, release = threading.Event(), threading.Event()
    for case in ("exit", "fuel", "close"):
        host = Path(tempfile.mkdtemp(prefix=f"{case}-", dir=guest_workdir))
        grants = [wp.Grant(host, "/w", writable=True)]
        exports_called.clear()
        if case == "exit":
            s = wp.Session(grants=grants, shutdown_s=60)
            s.run(_handler_writing("/w/h.txt"))
            s.run("import os; os._exit(4)")
        elif case == "fuel":
            s = wp.Session(grants=grants, shutdown_s=60, fuel=10**9)
            s.run(_handler_writing("/w/h.txt"))
            s.run(LOOP)
        else:
            s = wp.Session(grants=grants, shutdown_s=60, tools=[_blocking_tool(started, release)])
            s.run(_handler_writing("/w/h.txt"))
            t = threading.Thread(target=s.run, args=("from host import tools\ntools.block()",))
            t.start()
            assert started.wait(60)
            s.close()
            release.set()
            t.join(60)
        s.close()
        assert (s.shutdown_outcome, (host / "h.txt").exists()) == ("skipped", False), case
        assert [n for n, _ in exports_called if n == "shutdown"] == [], case


def test_exit_and_quit_end_the_session_through_the_shutdown(guest_workdir) -> None:
    """Criterion 41: as in Jupyter, sys.exit() keeps the session and exit() or quit() end it."""
    wp = _wp()
    for call, status in (("exit(5)", 5), ("quit()", 0)):
        host = Path(tempfile.mkdtemp(prefix="quit-", dir=guest_workdir))
        s = wp.Session(grants=[wp.Grant(host, "/w", writable=True)], shutdown_s=60)
        s.run(_handler_writing("/w/h.txt"))
        assert (
            s.run("import sys\ntry:\n    sys.exit(3)\nexcept SystemExit:\n    pass").exit_code == 0
        )
        assert s.run("raise SystemExit(3)").exit_code == 3 and s.ended is None
        r = s.run(f"print('a'); {call}; print('b')")
        assert (r.exit_code, r.trapped, r.stdout) == (status, None, b"a\n"), r
        assert (host / "h.txt").read_text() == "ran"
        assert (s.ended, s.shutdown_outcome) == ("quit", "finished")
        with pytest.raises(wp.SessionEnded) as e:
            s.run("pass")
        assert e.value.reason == "quit"
    s = wp.Session(shutdown_s=60)
    r = s.run(
        "import sys\ntry:\n    exit(3)\nexcept SystemExit:\n    pass\nprint(repr(sys.stdin.read()))"
    )
    assert (r.exit_code, r.stdout) == (0, b"''\n"), r
    assert s.ended == "quit"


ERROR_ROW = r"""
import signal, threading
signal.signal(signal.SIGINT, signal.default_int_handler)
import wasi_python
from wasi_python import runner
from wasi_python._process import process
seen = []
process().observers.on_export = lambda name, ident: seen.append(name)
s = wasi_python.Session(shutdown_s=60)
s.run("import atexit\natexit.register(print, 'handler')")

def noted():
    process().ctrl_c_pending = True  # as a Ctrl-C no host function saw

process().observers.after_export = noted
try:
    s.run("sum(range(10**6))")
    print("returned")
except KeyboardInterrupt:
    print("KeyboardInterrupt", s.ended, s.shutdown_outcome, seen.count("shutdown"))
"""


def test_a_turn_that_returns_after_close_runs_the_shutdown(
    guest_workdir, monkeypatch, exports_called
) -> None:
    """Criterion 42, F3's error row included."""
    wp = _wp()
    from wasi_python._process import process

    host = Path(tempfile.mkdtemp(prefix="race-", dir=guest_workdir))
    order: list[str] = []  # one list: the shutdown's handler, and close()'s return (F3)

    def door(frame: bytes) -> bytes:
        order.append("shutdown ran its handler")
        return b""

    s = wp.Session(grants=[wp.Grant(host, "/w", writable=True)], host=door, shutdown_s=60)
    s.run(_handler_writing("/w/h.txt") + "import _host\natexit.register(_host.call, b'x')\n")

    def closing() -> None:
        monkeypatch.setattr(process().observers, "after_export", None)
        t = threading.Thread(target=lambda: (s.close(), order.append("close returned")))
        t.start()
        while s.ended is None:
            t.join(0.001)
        closing.thread = t  # type: ignore[attr-defined]

    monkeypatch.setattr(process().observers, "after_export", closing)
    exports_called.clear()
    r = s.run("print(1)")
    order.append("turn returned")
    closing.thread.join(60)  # type: ignore[attr-defined]
    assert (r.exit_code, r.stdout) == (0, b"1\n"), r
    assert (host / "h.txt").read_text() == "ran"
    assert (s.ended, s.shutdown_outcome) == ("closed", "finished")
    shutdowns = [ident for n, ident in exports_called if n == "shutdown"]
    assert shutdowns == [threading.get_ident()], exports_called
    assert order.index("shutdown ran its handler") < order.index("close returned"), order
    assert order.index("shutdown ran its handler") < order.index("turn returned"), order
    assert _child(ERROR_ROW) == ["KeyboardInterrupt error skipped 0"]


def test_the_cap_on_open_files_in_a_session(guest_workdir) -> None:
    """Criterion 40 (spec 068's cap, per session: counted across turns and the ending)."""
    wp = _wp()
    host = Path(tempfile.mkdtemp(prefix="cap-", dir=guest_workdir))
    with wp.Session(
        grants=[wp.Grant(host, "/w", writable=True)], max_open_files=8, shutdown_s=60
    ) as s:
        first = s.run(
            "import errno\nkept = []\n"
            "try:\n    while True:\n        kept.append(open(f'/w/{len(kept)}.txt', 'w'))\n"
            "except OSError as e:\n    print(len(kept), e.errno == errno.EMFILE)\n"
        )
        count, emfile = first.stdout.split()
        assert emfile == b"True" and 0 < int(count) <= 8, first
        second = s.run(
            "try:\n    open('/w/more.txt', 'w')\n    print('opened')\n"
            "except OSError as e:\n    print(e.errno == errno.EMFILE)\n"
        )
        assert second.stdout == b"True\n", second  # a per-turn count would let it open
        third = s.run("kept.pop().close()\nkept.append(open('/w/again.txt', 'w'))\nprint('ok')")
        assert third.stdout == b"ok\n", third
        s.run(
            "import atexit\n"
            "def fill():\n    try:\n        while True:\n"
            "            kept.append(open('/w/x', 'w'))\n"
            "    except OSError:\n        pass\n"
            "atexit.register(fill)\n"
        )
        assert s.ended is None
    assert s.shutdown_outcome == "finished"


def test_a_closer_sees_the_openings_context(fake_clock) -> None:
    """The re-review's F7: an ending on a closer thread runs the embedder's code in a copy of the
    context taken when the session was opened."""
    import contextvars

    wp = _wp()
    from wasi_python import _sessions

    request = contextvars.ContextVar("request", default="none")
    seen: list[str] = []

    def host(frame: bytes) -> bytes:
        seen.append(request.get())
        return b""

    token = request.set("opening")
    s = wp.Session(host=host, shutdown_s=60)
    request.reset(token)
    s.run("import atexit, _host\natexit.register(_host.call, b'x')")
    fake_clock[0] = 900.0
    _sessions._reap(900.0)
    s.close()
    assert (s.ended, s.shutdown_outcome, seen) == ("idle", "finished", ["opening"])


def test_a_turn_frees_a_deep_structure() -> None:
    """Spec 078, criterion 10: on the runner's 8 MiB stack a turn that frees a 20,000-deep list
    (a trap at 512 KiB, which ended the session) completes, and the session goes on."""
    wp = _wp()
    with wp.Session() as s:
        r = s.run("x = []\nfor i in range(20000): x = [x]\ndel x\nprint('freed')")
        assert (r.exit_code, r.trapped, r.stdout) == (0, None, b"freed\n"), r
        assert s.ended is None
        assert s.run("print('on')").stdout == b"on\n"
