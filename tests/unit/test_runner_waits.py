"""The runner's answer to poll_oneoff (spec 010): the wait is bounded by the call's deadline and
the subscriptions are read as wasmtime reads them. Fakes stand in for time: these tests count
what the runner asks to sleep, never how long anything takes."""

from __future__ import annotations

import struct

from wasi_python import _call, _limits

TICK = _limits.TICK_S


class FakeTime:
    def __init__(self, deadline_after: int | None = None) -> None:
        self.t, self.sleeps, self.deadline_after = 0.0, [], deadline_after

    def now(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.sleeps.append(s)
        self.t += s

    def deadline_passed(self) -> bool:
        return self.deadline_after is not None and len(self.sleeps) >= self.deadline_after


def test_a_long_wait_stops_at_the_deadline() -> None:
    fake = FakeTime(deadline_after=50)
    _call._Waits(fake.now, fake.sleep, fake.deadline_passed).wait(3600.0)
    assert len(fake.sleeps) == 50 and max(fake.sleeps) <= TICK


def test_a_wait_without_a_deadline_is_one_sleep() -> None:
    fake = FakeTime()
    _call._Waits(fake.now, fake.sleep, None).wait(0.2)
    assert fake.sleeps == [0.2]


def test_a_wait_in_the_past_sleeps_not_at_all() -> None:
    fake = FakeTime(deadline_after=50)
    _call._Waits(fake.now, fake.sleep, fake.deadline_passed).wait(0.0)
    assert fake.sleeps == []


def clock(userdata: int, clock_id: int, timeout: int, absolute: bool = False) -> bytes:
    return struct.pack("<QB7xIxxxxQQH6x", userdata, 0, clock_id, timeout, 0, 1 if absolute else 0)


def fd(userdata: int, tag: int, number: int) -> bytes:
    return struct.pack("<QB7xI28x", userdata, tag, number)


def plan(subs: list[bytes], realtime: int = 10**18, monotonic: int = 5 * 10**9):
    return _call._poll_plan(b"".join(subs), len(subs), realtime, monotonic)


def test_subscriptions_and_events_have_wasi_sizes() -> None:
    assert len(clock(1, 1, 0)) == 48 and len(fd(1, 1, 4)) == 48
    assert struct.calcsize(_call.EVENT) == 32


def test_zero_or_too_many_subscriptions_are_refused() -> None:
    assert _call._poll_plan(b"", 0, 0, 0).errno == _call.EINVAL
    many = _call.MAX_SUBSCRIPTIONS + 1
    assert _call._poll_plan(clock(1, 1, 0) * many, many, 0, 0).errno == _call.ENOMEM


def test_an_unknown_tag_or_a_cpu_clock_is_refused() -> None:
    bad_tag = struct.pack("<QB39x", 1, 9)
    assert plan([bad_tag]).errno == _call.EINVAL
    assert plan([clock(1, 2, 10)]).errno == _call.EINVAL  # the process CPU-time clock


def test_the_shortest_clock_wins_and_absolute_waits_count_from_now() -> None:
    p = plan([clock(7, 1, 3_000_000_000), clock(8, 1, 1_000_000_000)])
    assert (p.errno, p.wait_ns, [e[0] for e in p.events]) == (None, 1_000_000_000, [8])
    p = plan([clock(9, 1, 5 * 10**9 + 250_000_000, absolute=True)])
    assert (p.wait_ns, [e[0] for e in p.events]) == (250_000_000, [9])
    past = plan([clock(9, 0, 10**18 - 5, absolute=True)])
    assert past.wait_ns == 0


def test_descriptors_follow_wasmtime() -> None:
    assert plan([fd(1, 1, 1)]).errno == _call.EBADF  # stdout for reading
    assert plan([fd(1, 2, 0)]).errno == _call.EBADF  # stdin for writing
    assert plan([fd(1, 1, 3)]).errno == _call.EBADF  # the preopened root
    p = plan([fd(5, 1, 0), fd(6, 2, 1), fd(7, 1, 9), clock(8, 1, 10**9)])
    assert (p.errno, p.wait_ns) == (None, 0)
    assert [(e[0], e[2], e[3]) for e in p.events] == [(5, 1, 1), (6, 2, 1), (7, 1, 1)]


def test_every_clock_due_is_reported_with_no_bytes() -> None:
    p = plan([clock(1, 1, 0), clock(2, 1, 10**9), clock(3, 1, 0)])
    assert (p.wait_ns, p.events) == (0, ((1, 0, 0, 0, 0), (3, 0, 0, 0, 0)))


def test_a_wait_ends_one_round_after_the_deadline_count() -> None:
    assert _call._stop_at(count=40, ticks=10) == 51


POLLER = """
(module
  (import "wasi_snapshot_preview1" "poll_oneoff" (func $p (param i32 i32 i32 i32) (result i32)))
  (memory (export "memory") 1)
  (func (export "poll") (param i32 i32 i32 i32) (result i32)
    (call $p (local.get 0) (local.get 1) (local.get 2) (local.get 3))))
"""
PAGE = 65536


class Raises:
    def wait(self, seconds: float) -> None:
        raise RuntimeError("a fault in the wait")


def poll(
    subs: bytes,
    in_ptr: int = 1024,
    out_ptr: int = 8192,
    n: int = 1,
    nevents: int = 64,
    waits=None,
    monotonic: int = 0,
) -> tuple[int, bytes]:
    """Call the runner's poll_oneoff from a one-page module, as a guest does: the arguments are
    i32s, so a pointer at or above 2**31 arrives negative."""
    import wasmtime as wt

    engine = wt.Engine()
    store = wt.Store(engine)
    linker = wt.Linker(engine)
    i32 = wt.ValType.i32()
    shadow = _call._poll_oneoff(
        1000,
        waits or _call._Waits(FakeTime().now, FakeTime().sleep, None),
        lambda: 10**18,
        lambda: 1000 + monotonic,
    )
    linker.define_func(
        "wasi_snapshot_preview1", "poll_oneoff", wt.FuncType([i32] * 4, [i32]), shadow, True
    )
    exports = linker.instantiate(store, wt.Module(engine, POLLER)).exports(store)
    memory = exports["memory"]
    memory.write(store, subs, 1024)
    signed = [v - (1 << 32) if v >= 1 << 31 else v for v in (in_ptr, out_ptr, n, nevents)]
    errno = exports["poll"](store, *signed)
    return errno, bytes(memory.read(store, 8192, 8192 + 32))


def test_out_of_bounds_pointers_answer_efault() -> None:
    one = clock(1, 1, 0)
    assert poll(one)[0] == 0
    for where in (
        {"in_ptr": PAGE - 40},
        {"out_ptr": PAGE - 16},
        {"nevents": PAGE - 2},
        {"in_ptr": 2**32 - 1},
        {"nevents": 2**31},
    ):
        assert poll(one, **where)[0] == _call.EFAULT, where


def test_counts_are_unsigned_and_capped_at_4096() -> None:
    assert _call.MAX_SUBSCRIPTIONS == 4096
    assert poll(clock(1, 1, 0), n=0)[0] == _call.EINVAL
    assert poll(clock(1, 1, 0), n=4097)[0] == _call.ENOMEM
    assert poll(clock(1, 1, 0), n=2**32 - 1)[0] == _call.ENOMEM


def test_a_fault_in_the_wait_answers_einval() -> None:
    assert poll(clock(1, 1, 10**9), waits=Raises())[0] == _call.EINVAL


def test_an_absolute_wait_counts_from_the_guests_origin() -> None:
    fake = FakeTime()
    waits = _call._Waits(fake.now, fake.sleep, None)
    errno, event = poll(clock(9, 1, 5_250_000_000, absolute=True), waits=waits, monotonic=5 * 10**9)
    assert (errno, fake.sleeps) == (0, [0.25])
    assert struct.unpack(_call.EVENT, event) == (9, 0, 0, 0, 0)
