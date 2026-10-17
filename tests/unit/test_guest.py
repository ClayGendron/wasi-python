"""The judge's guest driver: dispatch, the door, exits, fuel, and seeding (criterion 6)."""

from __future__ import annotations

import pytest

from harness import guest, paths, wat


def _run(work, name, source, **kw):
    return guest.run(wat.build(work, name, source), [], workdir=work, **kw)


def test_dispatch_calls_initialize_before_run_on_a_plain_reactor(work) -> None:
    assert _run(work, "order.wasm", wat.INIT_ORDER).exit_code == 5


def test_dispatch_calls_run_alone_on_a_snapshot(work) -> None:
    mod = guest.module(wat.build(work, "snap.wasm", wat.SNAPSHOT))
    assert guest.kind(mod) == "snapshot"
    assert _run(work, "snap.wasm", wat.SNAPSHOT).exit_code == 101  # no host bound


def test_dispatch_runs_a_command_and_reads_its_exit(work) -> None:
    r = _run(work, "cmd.wasm", wat.COMMAND_EXIT_7)
    assert (r.exit_code, r.trapped) == (7, None)


def test_a_module_without_an_entry_point_is_refused(work) -> None:
    with pytest.raises(ValueError, match="no _start and no run"):
        _run(work, "none.wasm", wat.NO_ENTRY)


def test_door_with_no_host_returns_no_host(work) -> None:
    assert _run(work, "plain.wasm", wat.PLAIN_REACTOR).exit_code == 100 - guest.NO_HOST


def test_door_round_trips_through_a_host(work) -> None:
    seen = []

    def host(frame: bytes) -> bytes:
        seen.append(frame)
        return frame[::-1]

    assert _run(work, "plain.wasm", wat.PLAIN_REACTOR, host=host).exit_code == 0
    assert seen == [b"abc"]


def test_door_reports_a_host_that_raises_as_a_fault(work) -> None:
    def host(frame: bytes) -> bytes:
        raise RuntimeError("boom")

    r = _run(work, "plain.wasm", wat.PLAIN_REACTOR, host=host)
    assert r.exit_code == 100 - guest.HOST_FAULT


def test_a_third_import_does_not_instantiate(work) -> None:
    r = _run(work, "third.wasm", wat.THIRD_IMPORT)
    assert r.exit_code is None and r.trapped and "sneak" in r.trapped


def test_fuel_cap_traps_after_exactly_the_cap(work) -> None:
    r = _run(work, "spin.wasm", wat.SPIN, fuel=10_000)
    assert (r.exit_code, r.trapped, r.fuel) == (None, "out of fuel", 10_000)


def test_random_is_the_same_on_every_run(work) -> None:
    first = _run(work, "rand.wasm", wat.RANDOM_PROBE).exit_code
    second = _run(work, "rand.wasm", wat.RANDOM_PROBE).exit_code
    assert first == second
    import hashlib

    want = int.from_bytes(hashlib.sha256((0).to_bytes(8, "little")).digest()[:4], "little")
    assert first == want - (1 << 32 if want >= 1 << 31 else 0)


def test_the_clock_starts_at_a_fixed_time_and_ticks_per_call(work) -> None:
    assert _run(work, "clock.wasm", wat.CLOCK_PROBE).exit_code == 1


def test_fuel_of_a_deterministic_module_is_exact(work) -> None:
    a = _run(work, "plain.wasm", wat.PLAIN_REACTOR, host=lambda f: f[::-1]).fuel
    b = _run(work, "plain.wasm", wat.PLAIN_REACTOR, host=lambda f: f[::-1]).fuel
    assert a == b > 0


# Against a real CPython: Brett's 3.14.7 build, a command module, when it is unpacked.

REF = paths.REFERENCE_BUILD


@pytest.fixture
def cpython(work):
    if not (REF / "python.wasm").is_file():
        pytest.skip("Brett's reference build is not unpacked under build/")

    def run(*argv, **kw):
        return guest.run(
            REF / "python.wasm",
            list(argv),
            workdir=work,
            python_version="3.14.7",
            stdlib=REF / "lib" / "python3.14",
            **kw,
        )

    return run


def test_cpython_prints_and_exits(cpython) -> None:
    assert cpython("-I", "-c", "print(1)").stdout == b"1\n"
    assert cpython("-I", "-c", "import sys; sys.exit(3)").exit_code == 3


def test_cpython_sees_only_its_root(cpython) -> None:
    code = (
        "import os\nprint(sorted(os.listdir('/')))\n"
        "try:\n    os.listdir('/..'); print('escaped')\nexcept OSError:\n    print('refused')\n"
    )
    r = cpython("-I", "-c", code, files={"/data/x.txt": "x"})
    assert r.text.split("\n")[:2] == ["['data', 'usr']", "refused"], r.describe()


def test_cpython_runaway_stops_at_the_fuel_cap(cpython) -> None:
    r = cpython("-I", "-c", "while True: pass", fuel=10**9)
    assert (r.exit_code, r.trapped, r.fuel) == (None, "out of fuel", 10**9)


def test_cpython_fuel_repeats_without_a_seed(cpython) -> None:
    a = cpython("-I", "-c", "import json; print(json.dumps({'a': [1, 2]}))").fuel
    b = cpython("-I", "-c", "import json; print(json.dumps({'a': [1, 2]}))").fuel
    assert abs(a - b) <= a * 1e-4, (a, b)


def test_fuel_counts_no_memory_image_copy(work) -> None:
    """The driver meters from after instantiation, so a page of data costs no fuel (spec 008)."""
    with_data = guest.run(wat.build(work, "d.wasm", wat.command_with_data(True)), [], workdir=work)
    without = guest.run(wat.build(work, "n.wasm", wat.command_with_data(False)), [], workdir=work)
    assert (with_data.exit_code, without.exit_code) == (0, 0)
    assert with_data.fuel == without.fuel, (with_data.fuel, without.fuel)


def test_initialize_is_metered(work) -> None:
    """_initialize runs guest code (the reactor's constructors), so it counts (spec 008)."""
    light = guest.run(wat.build(work, "l.wasm", wat.reactor_with_init(0)), [], workdir=work)
    heavy = guest.run(wat.build(work, "h.wasm", wat.reactor_with_init(1000)), [], workdir=work)
    assert (light.exit_code, heavy.exit_code) == (0, 0)
    assert heavy.fuel - light.fuel >= 3000, (light.fuel, heavy.fuel)


def test_a_failed_instantiation_spends_nothing(work) -> None:
    """A module that cannot be instantiated reports no fuel spent, not the unmetered budget."""
    r = guest.run(wat.build(work, "x.wasm", wat.THIRD_IMPORT), [], workdir=work)
    assert r.trapped is not None and r.fuel == 0, r
