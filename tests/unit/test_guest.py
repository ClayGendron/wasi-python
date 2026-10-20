"""The judge's guest driver: dispatch, the door, exits, fuel, and seeding (criterion 6)."""

from __future__ import annotations

import os
import shutil
import struct
from pathlib import Path

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


def test_the_clock_steps_by_the_runs_clock_step(work) -> None:
    # spec 087, Decision 3: a check can make a guest second a count of clock reads.
    assert _run(work, "step.wasm", wat.CLOCK_STEP_PROBE).exit_code == 1
    assert _run(work, "step.wasm", wat.CLOCK_STEP_PROBE, clock_step_ns=2_000_000).exit_code == 2_000


def test_a_changed_clock_step_is_the_stated_resolution(work) -> None:
    # At the default step the resolution is spec 065's, held by its own guard; a changed step
    # states itself, so time.get_clock_info tells that run the truth (spec 087, Decision 3).
    r = _run(work, "res.wasm", wat.CLOCK_RES_PROBE, clock_step_ns=2_000_000)
    assert r.exit_code == 2_000


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


INDIRECT_MISMATCH = """
(module
  (memory (export "memory") 1)
  (type $one (func (param i32) (result i32)))
  (type $two (func (param i32 i32) (result i32)))
  (table 1 funcref)
  (elem (i32.const 0) $f)
  (func $f (param i32 i32) (result i32) (local.get 0))
  (func (export "_start")
    (drop (call_indirect (type $one) (i32.const 1) (i32.const 0)))))
"""


def test_a_trap_keeps_its_first_line_and_its_cause(work) -> None:
    """spec 050, Decision 14: every such trap's first line is alike; the cause tells them apart."""
    r = _run(work, "mismatch.wasm", INDIRECT_MISMATCH)
    assert r.exit_code is None and r.trapped and "indirect call" not in r.trapped
    assert r.trap_cause == "wasm trap: indirect call type mismatch"
    assert _run(work, "spin.wasm", wat.SPIN, fuel=10_000).trap_cause is None
    assert _run(work, "cmd.wasm", wat.COMMAND_EXIT_7).trap_cause is None


def test_the_cause_is_the_line_after_caused_by() -> None:
    text = (
        "error while executing at wasm backtrace:\n    0: 0x1 - f\n\nCaused by:\n    wasm trap: x\n"
    )
    assert guest.trap_cause(text) == "wasm trap: x"
    assert guest.trap_cause("no cause here") is None


def test_turns_drives_one_instance_across_calls(work) -> None:
    """Spec 055: the raw turn driver writes each turn's code through host_alloc into one kept
    instance, and calls the exports as they are."""
    stdlib = work / "stdlib.zip"
    stdlib.write_bytes(b"")
    t = guest.turns(
        wat.build(work, "turns.wasm", wat.TURNS),
        workdir=work,
        python_version="3.15.0",
        stdlib=stdlib,
    )
    try:
        assert t.turn("ab").value == 2 + ord("a")
        assert t.turn(b"z").value == 1 + ord("z")
        assert t.turn("").value == 0  # an empty turn passes (0, 0)
        assert t.turn_raw(0, 0).value == 0
        assert t.shutdown().value == 4  # one instance: four turns counted
        assert t.run().value == 0
    finally:
        t.close()


# Spec 081: a measured run's inputs name no host path, so its fuel does not depend on where the
# checkout is. The driver refuses one before it runs.


def test_host_paths_are_found_in_every_input_the_guest_sees(work) -> None:
    """An argument, an environment variable, a file's guest path and contents, and a grant's
    guest path that name the root, as written or in forward slashes, are each named."""
    repo = paths.REPO
    found = guest.host_paths_in(
        [repo],
        ["-c", "print(1)", str(repo / "build" / "x"), (repo / "y").as_posix()],
        env={"HOME": "/home", "DATA": str(repo)},
        files={
            "/plain.txt": "no path here",
            "/a.py": f"open({str(repo)!r})".encode(),
            f"/{repo.name}.txt": "",
            str(repo / "z"): "",
        },
        preopens=[("/ro", work, False), (str(work), work, False)],
    )
    assert found == [
        "argv[3]",
        "argv[4]",
        "env DATA",
        "the contents of /a.py",
        f"file {repo / 'z'}",
        f"grant {work}",
    ]


def test_a_root_is_found_in_its_file_uri(work) -> None:
    """A root with a space or a non-ASCII letter is percent-encoded in a `file:` URI."""
    root = work / "a b é"
    uri = (root / "secret.txt").as_uri()
    assert "%20" in uri
    assert guest.host_paths_in([root], ["-c", f"open_url({uri!r})"]) == ["argv[2]"]


def test_a_windows_root_is_found_escaped_and_in_any_case() -> None:
    """A Windows path written inside code by `repr` or JSON has its backslashes doubled; on
    Windows a drive or folder in another case is the same path. The root is Windows-shaped on
    every system (on POSIX it is a relative path, which has no URI)."""
    import json

    root = Path(r"C:\Users\runner\work")
    inside = r"C:\Users\runner\work\wasi_python\secret.txt"
    code = ["-c", f"a = {inside!r}", "-c", json.dumps({"p": inside}), inside]
    assert guest.host_paths_in([root], code) == ["argv[2]", "argv[4]", "argv[5]"]
    lower = inside.lower()
    assert guest.host_paths_in([root], [lower], fold_case=False) == []
    assert guest.host_paths_in([root], [lower], fold_case=True) == ["argv[1]"]


def test_guest_paths_and_other_folders_are_not_host_paths(work) -> None:
    other = work / "elsewhere"
    assert guest.host_paths_in([other], ["/ro/x", str(work)], env={"T": "/tmp"}) == []
    assert guest.host_paths_in([other], [str(other / "f")]) == ["argv[1]"]


def test_the_system_temp_folder_is_a_root_unless_it_is_slash_tmp(work, monkeypatch) -> None:
    """On Linux the temp folder is `/tmp`, a path guests are given as their own; anywhere else
    (macOS' `/var/folders/…`, Windows' `%TEMP%`) it is a host path."""
    wasm = wat.build(work, "plain.wasm", wat.PLAIN_REACTOR)
    monkeypatch.setattr(guest.tempfile, "gettempdir", lambda: "/tmp")
    assert guest.run(wasm, ["/tmp/x"], workdir=work, env={"TMPDIR": "/tmp"}).exit_code == 101
    temp = Path("/var/folders/zz/somewhere/T")
    monkeypatch.setattr(guest.tempfile, "gettempdir", lambda: str(temp))
    with pytest.raises(ValueError, match=r"host path in argv\[1\]"):
        guest.run(wasm, [str(temp / "x")], workdir=work)


def test_a_measured_run_with_a_host_path_is_refused_before_it_runs(work) -> None:
    wasm = wat.build(work, "plain.wasm", wat.PLAIN_REACTOR)
    runs = len(list(work.glob("run-*")))
    with pytest.raises(ValueError, match=r"host path in argv\[1\]: its fuel would depend"):
        guest.run(wasm, [str(work / "f")], workdir=work)
    elsewhere = Path("/somewhere/else")
    with pytest.raises(ValueError, match=r"host path in grant /somewhere/else"):
        guest.run(
            wasm,
            [],
            workdir=work,
            preopens=[(str(elsewhere), work, False)],
            host_roots=[elsewhere],
        )
    assert len(list(work.glob("run-*"))) == runs  # refused before its root was made
    assert guest.run(wasm, [str(work / "f")], workdir=work, measured=False).exit_code == 101


# Spec 083: the driver answers a file's times and inode number itself, never the host's.

STAT = struct.Struct("<QQB7xQQQQQ")  # dev, ino, filetype, nlink, size, atim, mtim, ctim
DIRENT = struct.Struct("<QQIB3x")  # d_next, d_ino, d_namlen, d_type
YEAR = 365 * 86400 * 10**9


def _tick(n: int) -> int:
    return guest.REALTIME_START_NS + n * guest.CLOCK_STEP_NS


def _file_facts(work: Path, grant: Path, atime_ns: int) -> tuple[list[bytes], int]:
    """FILE_FACTS once over `grant`, whose `f` is made afresh (a new host inode) with the given host
    times; at its first frame the host appends to `f` and sets its times a year apart, and at its
    third (after the guest's read) the host reads `f` too. The door frames and the fuel."""
    shutil.rmtree(grant, ignore_errors=True)
    grant.mkdir()
    (grant / "f").write_bytes(b"0123456789abcdefghij")
    os.utime(grant / "f", ns=(atime_ns, atime_ns + YEAR))
    frames: list[bytes] = []

    def host(frame: bytes) -> bytes:
        frames.append(frame)
        if len(frames) == 1:
            with open(grant / "f", "ab") as f:
                f.write(b"more")
            os.utime(grant / "f", ns=(atime_ns + 2 * YEAR, atime_ns + 3 * YEAR))  # atime < mtime
        elif len(frames) == 3:
            (grant / "f").read_bytes()
        return b""

    wasm = wat.build(work, "facts.wasm", wat.FILE_FACTS)
    r = guest.run(wasm, [], workdir=work, host=host, preopens=[("/g", grant, True)])
    assert r.exit_code == 0, r.describe()
    return frames, r.fuel


def _no_ctim(stat: bytes) -> bytes:
    return stat[:56]


def _listing(data: bytes) -> dict[bytes, tuple[int, bytes]]:
    """Each whole entry of a listing: its name, its d_ino and its three padding bytes."""
    out, at = {}, 0
    while at + DIRENT.size <= len(data):
        _next, ino, namlen, _kind = DIRENT.unpack_from(data, at)
        name = data[at + DIRENT.size : at + DIRENT.size + namlen]
        out[bytes(name)] = (ino, bytes(data[at + 21 : at + 24]))
        at += DIRENT.size + namlen
    return out


def test_a_files_times_and_inode_are_the_drivers(work) -> None:
    """Spec 083, Decisions 2 and 3: two runs over a file made afresh with other host times send
    the same answers (but `ctim`, which hosts move by their own rules) and spend the same fuel.
    The inode is a count from 1, the times the clock's values, a time set exactly comes back as
    set, a time set "now" is a later clock value, and a stream's zeros pass through (F4). A stat
    writes only its inode and times: its padding keeps the guest's bytes (the review's N1)."""
    grant = work / "grant"
    first, fuel_1 = _file_facts(work, grant, 10 * YEAR)
    second, fuel_2 = _file_facts(work, grant, 40 * YEAR)
    assert len(first) == len(second) == 9, (len(first), len(second))
    stats_1 = [f for i, f in enumerate(first) if i not in (2, 4)]
    stats_2 = [f for i, f in enumerate(second) if i not in (2, 4)]
    assert [_no_ctim(s) for s in stats_1] == [_no_ctim(s) for s in stats_2]
    assert first[4] == second[4], "the listings differ"
    assert fuel_1 == fuel_2, (fuel_1, fuel_2)
    a, b, d, f, g, h, i = (STAT.unpack(s) for s in stats_1)
    assert all(s[17:24] == b"\xaa" * 7 for s in stats_1), "a stat wrote its padding"
    assert (a[1], a[5], a[6], a[7]) == (1, _tick(1), _tick(1), _tick(1)), a
    assert (b[1], b[5], b[6]) == (1, _tick(2), _tick(2)), b
    assert b[7] in (_tick(1), _tick(2)), b
    assert (d[1], d[5], d[6], d[7]) == (b[1], b[5], b[6], b[7]), (b, d)  # reads moved nothing
    entries = _listing(first[4])
    assert entries[b"f"][0] == 1, entries
    assert all(0 < ino < 2**30 for ino, _ in entries.values()), entries
    assert all(pad == bytes(3) for _, pad in entries.values()), entries
    assert (f[1], f[5], f[6]) == (1, 111, 222), f
    assert (g[1], g[5], g[6]) == (1, 333, 444), g
    assert h[5] == h[6] and _tick(2) < h[5] <= _tick(10), h
    assert (i[1], i[5], i[6], i[7]) == (0, 0, 0, 0), i


def test_a_read_alone_moves_no_answered_time(work) -> None:
    """Spec 083, Decision 2 (the review's F1): a host moves a file's atime when it is read,
    depending on the file's past, so an atime move alone never gives a new answer; a move of
    mtim or ctim gives atim and the moved times one new clock value together."""
    frames, _ = _file_facts(work, work / "grant", 10 * YEAR)
    b, d = STAT.unpack(frames[1]), STAT.unpack(frames[3])
    assert d[5:8] == b[5:8], (b, d)
    ticks = iter(range(1, 100))
    facts = guest.FileFacts(lambda: _tick(next(ticks)))
    raw = STAT.pack(1, 77, 4, 1, 5, 100, 100, 100)
    first = STAT.unpack(facts.filestat(raw))
    read = STAT.unpack(facts.filestat(STAT.pack(1, 77, 4, 1, 5, 900, 100, 100)))
    assert read[5:8] == first[5:8] == (_tick(1),) * 3
    written = STAT.unpack(facts.filestat(STAT.pack(1, 77, 4, 1, 6, 900, 950, 100)))
    assert written[5:8] == (_tick(2), _tick(2), _tick(1)), written


def test_a_shadowed_file_call_costs_the_guest_only_its_own_instructions(work) -> None:
    """Spec 083, Decision 1: the forward through the driver's trampoline is fuel-neutral, so a
    loop over a shadowed call costs what the same loop over a call it leaves alone costs."""
    shadowed = guest.run(
        wat.build(work, "s.wasm", wat.stat_loop("fd_filestat_get", 50)), [], workdir=work
    )
    left = guest.run(
        wat.build(work, "l.wasm", wat.stat_loop("fd_fdstat_get", 50)), [], workdir=work
    )
    assert (shadowed.exit_code, left.exit_code) == (0, 0)
    assert shadowed.fuel == left.fuel > 0, (shadowed.fuel, left.fuel)


def test_the_forward_never_runs_a_guest_out_of_fuel_early(work) -> None:
    """Spec 083, Decision 1 (the review's F2): at the budget's edge a shadowed call ends a run
    exactly as a call the driver leaves alone does, and an out-of-fuel run spends its cap."""
    stat = wat.build(work, "s.wasm", wat.stat_loop("fd_filestat_get", 50))
    plain = wat.build(work, "p.wasm", wat.stat_loop("fd_fdstat_get", 50))
    full = guest.run(stat, [], workdir=work).fuel
    for budget in range(full - 1, full - 16, -1):
        a = guest.run(stat, [], workdir=work, fuel=budget)
        b = guest.run(plain, [], workdir=work, fuel=budget)
        assert (a.exit_code, a.trapped, a.fuel) == (b.exit_code, b.trapped, b.fuel), budget
        if a.trapped == "out of fuel":
            assert a.fuel == budget, (budget, a.fuel)


def test_a_cut_listing_entry_keeps_no_host_byte(work) -> None:
    """Spec 083, Decision 3 (the review's F8): whole entries get counted inode numbers and zero
    padding; of an entry cut at the buffer's end, only the d_ino and padding bytes present are
    zeroed, and every other byte is left as wasmtime wrote it."""
    names = [b"alpha", b"be", b"gamma"]
    data = b"".join(
        DIRENT.pack(i + 1, 0xC000_0000_0000_0000 + i, len(n), 4)[:21] + b"\xee\xee\xee" + n
        for i, n in enumerate(names)
    )
    third = 2 * DIRENT.size + len(names[0]) + len(names[1])
    for cut in range(third + 1, third + DIRENT.size):
        buf = bytearray(data[:cut])
        guest.FileFacts(lambda: _tick(1)).listing(buf)
        whole = _listing(bytes(buf))
        assert [ino for ino, _ in whole.values()] == [1, 2], cut
        assert all(pad == bytes(3) for _, pad in whole.values()), cut
        for at in range(third, cut):
            off = at - third
            zeroed = 8 <= off < 16 or 21 <= off < 24
            assert buf[at] == (0 if zeroed else data[at]), (cut, off)
