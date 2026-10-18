"""Read-only mounts (spec 032): the runner's own boundary code, which does not depend on the host,
so these run on the judge's machine only. Raw preview1 calls through the mount linker, with the
call on the thread's stack (harness/files.py); fuel and provider calls are counted, nothing is
timed."""

from __future__ import annotations

import os
import struct
import threading
from pathlib import Path

import pytest
import wasmtime as wt

from harness import files, needs, paths
from harness.files import MemoryProvider, Mounted
from wasi_python import Errno, Mount, Stat, runner
from wasi_python import mounts as mounts_module

EFAULT, EINVAL, ENAMETOOLONG, ENOTSUP, EBADF = 21, 28, 37, 58, 8


@pytest.fixture
def placeholder(tmp_path) -> Path:
    path = tmp_path / "placeholder"
    path.mkdir()
    return path


# Acceptance 8, the raw guards: nothing the guest passes reaches the provider but a normalized
# path; a bad pointer, length or count is answered before any provider call.


def test_guest_arguments_never_reach_the_provider(placeholder) -> None:
    provider = MemoryProvider()
    m = Mounted(provider, placeholder)
    r, end = m.raw, files.MEMORY_END
    f = r.open(3, "a.txt")[1]
    d = r.open(3, "d", files.O_DIRECTORY)[1]
    assert f is not None and d is not None
    before = dict(provider.calls)
    rows = {
        "path past memory": r("path_open", 3, 0, end - 2, 4, 0, files.READ_RIGHTS, 0, 0, 0),
        "path length past memory": r("path_filestat_get", 3, 0, files.PATH, end, files.RESULT),
        "path of 4,097 bytes": r.open(3, "x/" * 2048 + "y")[0],
        "stat result past memory": r("path_filestat_get", 3, 0, *r.path("a.txt"), end - 8),
        "open result past memory": r("path_open", 3, 0, *r.path("b.txt"), 0, 0, 0, 0, end),
        "iovec array past memory": r("fd_read", f, end - 4, 1, files.RESULT),
        "iovec past memory": r("fd_read", f, r.iovecs([8], buffer=end - 4), 1, files.RESULT),
        "a second iovec past memory": r(
            "fd_pread", f, r.iovecs([2, 8], buffer=end - 6), 2, 0, files.RESULT
        ),
        "1,025 iovecs": r("fd_read", f, r.iovecs([1] * 1025), 1025, files.RESULT),
        "nread past memory": r("fd_read", f, r.iovecs([4]), 1, end),
        "readdir buffer past memory": r("fd_readdir", d, end - 10, 100, 0, files.RESULT),
        "readdir length past memory": r("fd_readdir", 3, files.DIRBUF, end, 0, files.RESULT),
        "readdir used past memory": r("fd_readdir", 3, files.DIRBUF, 64, 0, end),
        "readlink buffer past memory": r("path_readlink", 3, *r.path("a.txt"), end, 8, 0),
        "fdstat past memory": r("fd_fdstat_get", f, end - 8),
        "filestat past memory": r("fd_filestat_get", f, end - 8),
        "seek result past memory": r("fd_seek", f, 0, 0, end),
    }
    assert rows == {
        "path past memory": EFAULT,
        "path length past memory": EFAULT,
        "path of 4,097 bytes": ENAMETOOLONG,
        "stat result past memory": EFAULT,
        "open result past memory": EFAULT,
        "iovec array past memory": EFAULT,
        "iovec past memory": EFAULT,
        "a second iovec past memory": EFAULT,
        "1,025 iovecs": EINVAL,
        "nread past memory": EFAULT,
        "readdir buffer past memory": EFAULT,
        "readdir length past memory": EFAULT,
        "readdir used past memory": EFAULT,
        "readlink buffer past memory": EFAULT,
        "fdstat past memory": EFAULT,
        "filestat past memory": EFAULT,
        "seek result past memory": EFAULT,
    }
    assert provider.calls == before  # not one provider call
    assert r.tell(f) == (0, 0)  # and nothing moved


def test_a_path_is_normalized_before_the_provider_sees_it(placeholder) -> None:
    """Decision 5: `.`, empty parts and `..` within the mount are resolved by the runner; a
    climb above the descriptor's folder, an absolute path, a NUL, a long part and a path a more
    specific preopen owns are refused before any call."""
    provider = MemoryProvider()
    grant = placeholder.parent / "nested"
    grant.mkdir()
    m = Mounted(provider, placeholder, folders=[(grant, "/m/g", False)])
    r = m.raw
    assert r.path_filestat(3, "./d//x.txt/")[0] == 54  # a file named as a folder
    assert r.path_filestat(3, "d/../a.txt")[0] == 0
    d = r.open(3, "d", files.O_DIRECTORY)[1]
    for base, path, errno in [
        (3, "..", 63),
        (3, "d/../..", 63),
        (d, "..", 63),
        (d, "../a.txt", 63),
        (3, "/a.txt", 63),
        (3, "", 44),
        (3, "a\0", 28),
        (3, "x" * 256, 37),
        (3, "g", 63),
        (3, "g/inside", 63),
        (3, "d/../g/./x", 63),
    ]:
        assert r.path_filestat(base, path)[0] == errno, (base, path)
    assert provider.paths == [
        ("stat", "/d/x.txt"),
        ("stat", "/a.txt"),
        ("list", "/d"),
    ]


# Decision 10: the call's cancel and deadline are checked before every provider call.


def test_a_cancel_or_a_passed_deadline_stops_the_provider_call(placeholder, monkeypatch) -> None:
    provider = MemoryProvider()
    cancel = threading.Event()
    m = Mounted(provider, placeholder, cancel=cancel, stop_at=100)
    monkeypatch.setattr(runner._epoch_ticker, "count", classmethod(lambda cls: 99))
    assert m.raw.path_filestat(3, "a.txt")[0] == 0
    monkeypatch.setattr(runner._epoch_ticker, "count", classmethod(lambda cls: 100))
    assert m.raw.path_filestat(3, "a.txt")[0] == 73  # ETIMEDOUT
    monkeypatch.setattr(runner._epoch_ticker, "count", classmethod(lambda cls: 0))
    m.store.set_epoch_deadline(2**40)
    cancel.set()
    assert m.raw.path_filestat(3, "a.txt")[0] == 11  # ECANCELED
    assert provider.calls["stat"] == 1


def test_the_file_call_limit_names_the_end(placeholder) -> None:
    """Decision 8: the call that would pass the limit is not made; it answers EIO, names the
    call's end "out of file calls" and stops the guest at its next entry; every later file call
    answers the stopped code without a call."""
    provider = MemoryProvider()
    m = Mounted(provider, placeholder, file_calls=2)
    r = m.raw
    assert [r.path_filestat(3, "a.txt")[0] for _ in range(3)] == [0, 0, 29]
    assert m.call.ended == "out of file calls" and m.call.stopped is None
    with pytest.raises(files.Ends, match="interrupt"):  # the deadline was set to 0 in that step
        r.path_filestat(3, "a.txt")
    m.store.set_epoch_deadline(2**40)
    assert r.path_filestat(3, "a.txt")[0] == 29  # spec 030's guard: no host function runs
    assert provider.calls["stat"] == 2
    assert m.table.record().calls == {"stat": 2, "list": 0, "read": 0}


def test_a_named_end_holds_under_the_epoch_callback(monkeypatch) -> None:
    """Decision 8: `_epoch_answer` keeps an end already named, under `cancel=` too."""
    import ctypes
    from types import SimpleNamespace

    monkeypatch.setattr(runner, "_stop_error", lambda delta=None: 77)
    monkeypatch.setattr(runner, "_ctrl_c_watched", lambda: False)
    holder = ctypes.c_int(0)
    call = SimpleNamespace(
        context=ctypes.addressof(holder),
        stopped=None,
        cancel=threading.Event(),
        stop_at=None,
        ended="out of file calls",
    )
    call.cancel.set()
    stack = runner._stack()
    stack.append(call)
    try:
        assert runner._epoch_answer(ctypes.pointer(holder), (ctypes.c_uint64 * 1)()) == 77
    finally:
        stack.remove(call)
    assert call.ended == "out of file calls"


# Acceptance 12, the exact part: a forward is fuel-neutral and keeps wasmtime's traps.

P1 = "wasi_snapshot_preview1"
LOOP = f"""(module
  (import "{P1}" "fd_fdstat_get" (func $g (param i32 i32) (result i32)))
  (memory (export "memory") 1)
  (func $leaf (result i32) (i32.const 7))
  (func (export "run") (param $n i32) (result i32) (local $e i32)
    (block $done (loop $l
      (br_if $done (i32.eqz (local.get $n)))
      (local.set $e (i32.or (local.get $e) (call $g (i32.const 1) (i32.const 64))))
      (drop (call $leaf))
      (local.set $n (i32.sub (local.get $n) (i32.const 1)))
      (br $l)))
    (local.get $e)))"""
BAD_POINTER = f"""(module
  (import "{P1}" "fd_read" (func $r (param i32 i32 i32 i32) (result i32)))
  (memory (export "memory") 1)
  (func (export "run") (result i32)
    (drop (call $r (i32.const 4) (i32.const 64) (i32.const 1) (i32.const 0)))
    (call $r (i32.const 4) (i32.const 65536) (i32.const 1) (i32.const 0))))"""


def _loop(placeholder: Path, mounted: bool, cap: int, n: int = 200) -> tuple[str, int]:
    """How the loop ends and the fuel it used, on the mount linker or today's."""
    provider = MemoryProvider()
    m = Mounted(provider, placeholder, fuel=cap, wat=LOOP)
    if mounted:
        run, enter = m.instance.exports(m.store)["run"], m.entered
    else:  # the same store's configuration on today's linker
        instance = m.plain.instantiate(m.store, wt.Module(m.engine, LOOP))
        run, enter = instance.exports(m.store)["run"], m.entered
    try:
        with enter():
            end = f"returned {run(m.store, n)}"
    except wt.Trap as e:
        end = f"trap {e.trap_code}"
    except files.Ends as e:
        end = f"stopped {e.message}"
    assert provider.total() == 0
    return end, cap - m.store.get_fuel()


def test_forwards_cost_no_fuel_and_keep_traps(placeholder, tmp_path) -> None:
    """Spec 032, acceptance 12 (exact part, N2): a guest that calls a WASI function N times
    spends exactly the fuel it spends on today's linker, and ends the same way with the same
    fuel used at every cap from 1 up to past its need; a forwarded bad pointer ends the call
    with the same `trapped` and fuel used, and the error is wasmtime-py's own wrapper."""
    full = _loop(placeholder, False, 10**9)
    assert full == _loop(placeholder, True, 10**9)
    assert full[0] == "returned 0"
    need = full[1]
    for cap in [*range(1, 60), *range(need - 40, need + 3)]:
        assert _loop(placeholder, True, cap) == _loop(placeholder, False, cap), cap
    folder = tmp_path / "folder"
    folder.mkdir()
    ends = []
    for mounted in (False, True):
        m = Mounted(MemoryProvider(), placeholder, folders=[(folder, "/f", False)], fuel=10**6)
        module = wt.Module(m.engine, BAD_POINTER)
        if mounted:
            call, linker = m.call, m.linker
        else:
            call = runner._Call(m.store, None, None, 0)
            linker = m.plain
        call.stopped = None
        driven = runner._drive(wt, linker, m.store, module, call, 10**6, plain=m.plain)
        used = runner._fuel_used(10**6, driven, call, m.store.get_fuel)
        ends.append((driven.exit_code, driven.trapped, used))
        if mounted:
            assert isinstance(call.stopped, wt.WasmtimeError) and call.stopped.ptr()
    assert ends[0] == ends[1], ends
    assert ends[0][1] and ends[0][2] and ends[0][2] > 0, ends


# Acceptance 9: a bad mount is refused before any work.


class Async:
    async def stat(self, path):
        return Stat("dir")

    def list(self, path):
        return []

    def read(self, path):
        return b""


class NoRead:
    def stat(self, path):
        return Stat("dir")

    def list(self, path):
        return []

    read = None


@pytest.mark.parametrize(
    ("kw", "error", "match"),
    [
        ({"mounts": "/work"}, TypeError, "iterable of Mount"),
        ({"mounts": Mount(MemoryProvider(), "/w")}, TypeError, "iterable of Mount"),
        ({"mounts": [("/w", MemoryProvider())]}, TypeError, r"mounts\[0\] must be a Mount"),
        ({"mounts": [Mount(NoRead(), "/w")]}, TypeError, r"mounts\[0\] at /w: .*read"),
        ({"mounts": [Mount(object(), "/w")]}, TypeError, r"no callable stat"),
        ({"mounts": [Mount(Async(), "/w")]}, TypeError, r"stat\(\) is a coroutine function"),
        ({"mounts": [Mount(MemoryProvider(), b"/w")]}, TypeError, "must be a str"),
        ({"mounts": [Mount(MemoryProvider(), "w")]}, ValueError, "must be absolute"),
        ({"mounts": [Mount(MemoryProvider(), "/w/")]}, ValueError, "ends in '/'"),
        ({"mounts": [Mount(MemoryProvider(), "/a/../b")]}, ValueError, "'..'"),
        ({"mounts": [Mount(MemoryProvider(), "/a\0")]}, ValueError, "null byte"),
        ({"mounts": [Mount(MemoryProvider(), "/usr/local/lib")]}, ValueError, "runtime's own"),
        (
            {"mounts": [Mount(MemoryProvider(), "/w"), Mount(MemoryProvider(), "/w")]},
            ValueError,
            r"mounts\[1\] at /w: a grant or another mount",
        ),
        ({"mounts": [Mount(MemoryProvider(), "/")], "root": True}, ValueError, "whole filesys"),
        ({"mounts": [Mount(MemoryProvider(), "/")], "root": "/x"}, ValueError, "whole filesys"),
        ({"max_file_calls": True}, TypeError, "max_file_calls"),
        ({"max_file_calls": "10"}, TypeError, "max_file_calls"),
        ({"max_file_calls": -1}, ValueError, "max_file_calls"),
        ({"max_file_calls": 2**63}, ValueError, "max_file_calls"),
    ],
)
def test_a_bad_mount_is_refused_before_any_work(tmp_path, kw, error, match) -> None:
    import asyncio

    from wasi_python import Grant, run, run_async

    provider, frames = MemoryProvider(), []
    for call in (run, lambda *a, **k: asyncio.run(run_async(*a, **k))):
        with pytest.raises(error, match=match):
            call(["-c", "pass"], host=frames.append, **kw)
    assert (provider.total(), frames) == (0, [])
    grant = Grant(tmp_path, "/w")
    with pytest.raises(ValueError, match="a grant or another mount"):
        run(["-c", "pass"], grants=[grant], mounts=[Mount(provider, "/w")])
    assert provider.total() == 0


def test_nesting_is_allowed_and_the_mounts_are_plain() -> None:
    provider = MemoryProvider()
    grants = runner._check_grants([runner.Grant("/h", "/w/g")])
    mounts = runner._check_mounts(
        iter([Mount(provider, "/w"), Mount(provider, "/w/inner"), Mount(provider, "/")]),
        grants,
        False,
    )
    assert [m.guest for m in mounts] == ["/w", "/w/inner", "/"]
    assert runner.DEFAULTS.file_calls == 10_000


# Acceptance 13: every descriptor import of each binary is shadowed or reviewed forward-safe.


@pytest.mark.parametrize("name", ["python.wasm", "python-snapshot.wasm"])
def test_every_descriptor_import_is_shadowed(name) -> None:
    from harness import wasm

    needs.need("artifact dir")
    binary = paths.artifact_dir() / name
    imported = {i.name for i in wasm.parse_file(binary).imports if i.module == wasm.WASI}
    takes_a_descriptor = {
        n for n in imported if n.startswith(("fd_", "path_", "sock_")) or n == "poll_oneoff"
    }
    allowed = set(mounts_module.SHADOWED) | set(mounts_module.FORWARD_SAFE)
    assert takes_a_descriptor - allowed == set()
    assert len(mounts_module.SHADOWED) == 29
    assert set(mounts_module.SHADOWED).isdisjoint(mounts_module.FORWARD_SAFE)
    # memo finding 1: 26 file calls and the preopen pair, beside the four sock_* and poll_oneoff
    assert len({n for n in takes_a_descriptor if n.startswith(("fd_", "path_"))}) == 28


def test_the_mount_linker_shadows_every_call(placeholder) -> None:
    """Each of the 29 reaches the mount table: on a number of the table it is served (EBADF from
    the table's answer for a call on a closed provider number is wasmtime's own)."""
    seen = []
    m = Mounted(MemoryProvider(), placeholder)
    real = m.table.__class__.__call__

    def counting(self, caller, name, *args):
        seen.append(name)
        return real(self, caller, name, *args)

    m.table.__class__.__call__ = counting  # type: ignore[method-assign]
    try:
        for name, params in mounts_module.SIGNATURES.items():
            try:
                m.raw(name, *([2**31 - 1] * len(params)))
            except files.Ends:
                pass
    finally:
        m.table.__class__.__call__ = real  # type: ignore[method-assign]
    assert sorted(set(seen)) == sorted(mounts_module.SHADOWED)


def test_renumber_and_close_keep_the_table_true(placeholder) -> None:
    """Decision 1: fd_renumber onto or from a provider number, or the mount's preopen, answers
    ENOTSUP and changes nothing; closing the mount's preopen drops it from the table, and a later
    open that reuses its number is wasmtime's."""
    folder = placeholder.parent / "real"
    folder.mkdir()
    (folder / "r.txt").write_bytes(b"real\n")
    m = Mounted(MemoryProvider(), placeholder, folders=[(folder, "/r", False)])
    r = m.raw
    f = r.open(3, "a.txt")[1]
    g = r.open(4, "r.txt")[1]
    assert f is not None and g is not None and f >= 2**30 and g < 2**30
    table = dict(m.table.table)
    for a, b in [(g, f), (f, g), (g, 3), (3, g), (g, 2**30 + 5), (2**31 - 1, g)]:
        assert r("fd_renumber", a, b) == ENOTSUP, (a, b)
    assert m.table.table == table
    assert r.read(f, [5])[2] == b"hello" and r.read(g, [4])[2] == b"real"
    assert r("fd_close", 3) == 0
    assert 3 not in m.table.table
    again = r.open(4, "r.txt")[1]
    assert again == 3  # wasmtime reuses the freed number
    assert r.read(3, [4])[2] == b"real"
    assert m.table.calls["read"] == 1


def test_the_staging_bound_and_the_open_limit(placeholder) -> None:
    """Decision 8: a read that would pass the staging bound is EFBIG and dropped; the open after
    MAX_MOUNT_FILES is EMFILE with no call; a closed number is reused, the lowest first."""
    provider = MemoryProvider({"/big": b"x" * 100, "/small": b"y"})
    m = Mounted(provider, placeholder, staging=150)
    r = m.raw
    big = r.open(3, "big")[1]
    assert big is not None
    assert r.open(3, "big")[0] == 22  # EFBIG: 200 > 150
    assert m.table.staged == 100
    assert r("fd_close", big) == 0 and m.table.staged == 0
    r = Mounted(provider, placeholder).raw
    numbers = [r.open(3, "small")[1] for _ in range(mounts_module.MAX_MOUNT_FILES)]
    assert numbers == list(range(2**30, 2**30 + 1024))
    before = provider.calls["read"]
    assert r.open(3, "small")[0] == 33  # EMFILE
    assert provider.calls["read"] == before
    assert r("fd_close", 2**30 + 7) == 0 and r("fd_close", 2**30 + 3) == 0
    assert [r.open(3, "small")[1] for _ in range(2)] == [2**30 + 3, 2**30 + 7]


def test_a_listing_is_kept_and_listed_again_from_cookie_zero(placeholder) -> None:
    """Decision 6: the listing made at open serves the first pass; fd_readdir from cookie 0 after
    that lists again, as rewinddir expects; a folder made from EISDIR is listed at its first
    fd_readdir."""
    provider = MemoryProvider()
    r = Mounted(provider, placeholder).raw
    d = r.open(3, "d", files.O_DIRECTORY)[1]
    assert provider.calls["list"] == 1
    first = r.readdir(d)
    assert r.readdir(d, cookie=2) == (0, 29, first[2][51:])
    assert provider.calls["list"] == 1
    assert r.readdir(d) == first and provider.calls["list"] == 2
    e = r.open(3, "d")[1]
    assert provider.calls == {"stat": 0, "list": 2, "read": 1}
    assert r.readdir(e) == first and provider.calls["list"] == 3


def test_a_folder_stat_comes_from_the_mount(placeholder) -> None:
    """dev hashes the mount's guest path and ino the provider path (zero-keyed SipHash-1-3, as
    `_wasi_ino`), so a run repeats exactly; an open file's fstat needs no provider call."""
    provider = MemoryProvider()
    r = Mounted(provider, placeholder).raw
    f = r.open(3, "a.txt")[1]
    calls = dict(provider.calls)
    assert r.filestat(f)[0] == 0 and provider.calls == calls
    dev, ino = struct.unpack("<QQ", r.get(files.RESULT, 16))
    assert dev == runner._siphash13(b"/m") and ino == runner._siphash13(b"/a.txt")
    assert r.get(files.RESULT + 40, 24) == bytes(24)  # no times from fstat


# Acceptance 10: a call without mounts is unchanged.


def test_a_call_without_mounts_is_unchanged(monkeypatch) -> None:
    """A call without mounts uses the guard linker (spec 048, Decision 7), whose only shadows are
    fd_readdir and path_rename, and reports no file record; a call with one uses the mount
    linker. Concurrent calls with and without mounts on two threads each get their own results,
    and each provider sees only its own call's paths (spec 011's pattern)."""
    needs.need("runner", "artifact dir")
    from wasi_python import run

    used, served = [], []
    real_drive, real_call = runner._drive, mounts_module._Files.__call__

    def drive(wt_, linker, *args, **kw):
        used.append(linker)
        return real_drive(wt_, linker, *args, **kw)

    def counted(self, caller, name, *args):
        served.append(name)
        return real_call(self, caller, name, *args)

    monkeypatch.setattr(runner, "_drive", drive)
    monkeypatch.setattr(mounts_module._Files, "__call__", counted)
    done = run(["-c", "import json; print(json.dumps([1]))"])
    assert (done.exit_code, done.stdout, done.files) == (0, b"[1]\n", None)
    engine = runner._engine(False)
    assert used == [runner._guard_linker(wt, engine)]
    assert set(served) <= {"fd_readdir", "path_rename"}, served
    served.clear()
    a, b = MemoryProvider({"/x": b"from a\n"}), MemoryProvider({"/x": b"from b\n"})
    results: dict[str, object] = {}

    def one(key: str, provider: MemoryProvider | None) -> None:
        mounts = [] if provider is None else [Mount(provider, f"/{key}")]
        code = f"print(open('/{key}/x').read(), end='')" if provider else "print('none')"
        for _ in range(3):
            results.setdefault(key, []).append(run(["-c", code], mounts=mounts).stdout)  # type: ignore[union-attr]

    threads = [
        threading.Thread(target=one, args=(k, p)) for k, p in (("a", a), ("b", b), ("c", None))
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results == {
        "a": [b"from a\n"] * 3,
        "b": [b"from b\n"] * 3,
        "c": [b"none\n"] * 3,
    }
    assert {p for _, p in a.paths} == {"/x"} and {p for _, p in b.paths} == {"/x"}
    mount_linker = runner._mount_linker(wt, engine)
    assert sum(linker is mount_linker for linker in used) == 6 and mount_linker is not used[0]
    assert sum(linker is used[0] for linker in used) == 4
    assert served  # the control: the mounted calls reached the shadows


def test_the_errno_values_are_preview1s() -> None:
    """Decision 3: the Errno set, by value (wasi-libc's wasip1.h)."""
    assert {e.name: e.value for e in Errno} == {
        "EACCES": 2, "EBUSY": 10, "ECANCELED": 11, "EDQUOT": 19, "EEXIST": 20, "EFBIG": 22,
        "EINVAL": 28, "EIO": 29, "EISDIR": 31, "ENAMETOOLONG": 37, "ENOENT": 44, "ENOSPC": 51,
        "ENOSYS": 52, "ENOTDIR": 54, "ENOTEMPTY": 55, "ENOTSUP": 58, "EPERM": 63, "EROFS": 69,
        "ESTALE": 72, "ETIMEDOUT": 73, "EXDEV": 75,
    }  # fmt: skip


def test_a_listing_is_judged_as_it_is_gathered(placeholder) -> None:
    """Decision 8: a listing is kept as its encoded entries (24 bytes and the name each) and
    judged against the staging bound while it is gathered: past it, EFBIG, and the provider's
    iterator is closed, not drained."""
    drawn = []

    class Many(MemoryProvider):
        def list(self, path):
            self._count("list", path)

            def names():
                for i in range(10**6):
                    drawn.append(i)
                    yield (f"n{i:04}", "file")

            return names()

    m = Mounted(Many(), placeholder, staging=1000)
    assert m.raw.open(3, ".", files.O_DIRECTORY)[0] == 22
    assert len(drawn) < 40 and m.table.staged == 0
    assert m.table.record().faults == ()


def test_the_record_keeps_the_first_thousand_faults(placeholder) -> None:
    class Broken(MemoryProvider):
        def stat(self, path):
            self._count("stat", path)
            raise OSError("x" * 500)

    provider = Broken()
    m = Mounted(provider, placeholder)
    for _ in range(1001):
        assert m.raw.path_filestat(3, "a.txt")[0] == 29
    record = m.table.record()
    assert len(record.faults) == 1000 and record.calls["stat"] == 1001 == provider.calls["stat"]
    assert record.faults[0] == mounts_module.FileFault(
        "stat", "/a.txt", ("OSError: " + "x" * 500)[:200]
    )
    with pytest.raises(TypeError):
        record.calls["stat"] = 0  # type: ignore[index]  # read-only


def test_a_finished_call_holds_nothing(monkeypatch) -> None:
    """The build review, F3: when run() returns, no call, mount table or staged file of it is
    left for the cyclic collector, whatever ended the guest: an exit with a mount file still
    open, or running out of fuel while holding one. Counted with the collector off."""
    import gc

    needs.need("runner", "artifact dir")
    from wasi_python import run

    provider = MemoryProvider({"/big": b"x" * (1 << 20)})
    hold = "f = open('/m/big', 'rb'); f.read(1)\n"
    endings = {
        "an exit": (hold + "import os; os._exit(0)", None, None),
        "out of fuel": (hold + "while True: pass", 400_000_000, None),
        "out of file calls": (hold + "import os\nwhile True: os.stat('/m/big')", None, 5),
    }

    def alive() -> int:
        kinds = (runner._Call, mounts_module._Files, mounts_module._Open)
        return sum(type(o) in kinds for o in gc.get_objects())

    for name, (code, fuel, calls) in endings.items():
        gc.collect()
        before = alive()
        gc.disable()
        try:
            mounts = [Mount(provider, "/m")]
            done = run(["-c", code], mounts=mounts, fuel=fuel, max_file_calls=calls)
            left = alive() - before
        finally:
            gc.enable()
        assert done.exit_code == 0 or done.trapped in ("out of fuel", name), (name, done)
        assert left == 0, (name, left)


def test_an_abi_error_keeps_the_grants_fuel(placeholder, tmp_path) -> None:
    """The build review, F4.2: a served call that meets an argument its ABI cannot carry ends
    the run with the fuel a grant reports for the same guest, not None."""
    guest = f"""(module
  (import "{P1}" "path_open"
    (func $o (param i32 i32 i32 i32 i32 i64 i64 i32 i32) (result i32)))
  (memory (export "memory") 1)
  (data (i32.const 100) "a.txt")
  (func (export "run") (result i32)
    (call $o (i32.const 3) (i32.const 0) (i32.const 100) (i32.const 5) (i32.const 16)
      (i64.const 2) (i64.const 2) (i32.const 0) (i32.const 0))))"""
    tree = files.write_tree(tmp_path / "tree")
    ends = []
    for mounted in (False, True):
        # the same layout on both sides: the mount's placeholder, or the tree's folder, at 3
        m = Mounted(MemoryProvider(), placeholder if mounted else tree, fuel=10**6, wat=guest)
        module = wt.Module(m.engine, guest)
        if mounted:
            call, linker = m.call, m.linker
        else:
            call, linker = runner._Call(m.store, None, None, 0), m.plain
        driven = runner._drive(wt, linker, m.store, module, call, 10**6, plain=m.plain)
        used = runner._fuel_used(10**6, driven, call, m.store.get_fuel)
        ends.append((driven.exit_code, used))
    assert ends[0] == ends[1] and ends[0][1] is not None and ends[0][1] > 0, ends


def test_a_listing_is_counted_as_what_it_holds() -> None:
    """The build review, F2: a kept listing holds what the staging bound counts for it (its
    encoded entries and their offsets, measured by tracemalloc, within a small constant), and
    gathering one past the bound peaks near the bound, not several times it."""
    import tracemalloc

    from wasi_python.mounts import _Files

    names = 20_000

    class Generated:
        def stat(self, path):
            return Stat("dir")

        def read(self, path):
            return Errno.EISDIR

        def list(self, path):
            return ((f"n{i:07}", "file") for i in range(names))

    def gathered(staging: int) -> tuple[int, int, int, int]:
        table = _Files([(Mount(Generated(), "/m"), 3)], [], None, staging, False)
        table._ask = lambda caller, mount, method, path: (0, mount.provider.list(path))
        tracemalloc.start()
        try:
            errno, listing, held = table._list(None, table.mounts[0], "/", 1)
            now, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        del listing
        return errno, held, now, peak

    errno, held, now, peak = gathered(1 << 30)
    assert errno == 0 and held > names * 32
    assert held <= now <= held + 4096, (held, now)  # what is kept is what is counted
    bound = held // 2
    errno, _, now, peak = gathered(bound)
    assert errno == 22  # EFBIG, judged while gathering
    assert peak <= bound * 1.25 + 65536, (bound, peak)  # the gathering is counted too


def test_a_mount_writes_zero_dirent_padding(placeholder) -> None:
    """Every fd_readdir entry a mount writes has its three padding bytes after d_type zeroed,
    over a buffer filled with 0xFF first, on full and cut-short buffers alike: the runner never
    copies host memory into the guest there (wasmtime 49.0.0's own fd_readdir does, on a grant:
    GHSA-96f6-r43r-8c24)."""
    r = Mounted(MemoryProvider(), placeholder).raw
    d = r.open(3, "d", files.O_DIRECTORY)[1]
    for fd in (3, d):
        for size in (4096, 22, 23, 25, 47, 48, 50, 80):  # 22, 23, 47, 48 end in a header's padding
            r.put(files.DIRBUF, b"\xff" * 4096)
            assert r("fd_readdir", fd, files.DIRBUF, size, 0, files.RESULT) == 0
            data, pos, entries = r.get(files.DIRBUF, r.u32(files.RESULT)), 0, 0
            while pos < len(data):
                header = data[pos : pos + 24]
                assert header[21:24] == b"\x00" * len(header[21:24]), (fd, size, pos, header)
                entries += 1
                if len(header) < 24:
                    break
                pos += 24 + struct.unpack_from("<I", header, 16)[0]
            assert entries >= 1
            assert r.get(files.DIRBUF + len(data), 1) == b"\xff"  # nothing past what it used


# Spec 048: the guard. A call without mounts runs on the guard linker, which shadows only
# fd_readdir and path_rename, and forwards both with wasmtime 49.0.2's zeroed dirent padding and
# 49.0.3's trailing-slash rename rule (GHSA-96f6-r43r-8c24, GHSA-m9f7-9w4p-gv38).

ENOTDIR, ENOENT, EPERM = 54, 44, 63


def _pads(data: bytes, skip: range = range(0)) -> list[tuple[int, bytes]]:
    """Each entry's offset and its padding bytes (21 to 24 of the header, as far as `data`
    reaches), walking by 24 + d_namlen; bytes at offsets in `skip` are left out."""
    out, pos = [], 0
    while pos < len(data):
        header = data[pos : pos + 24]
        out.append((pos, bytes(header[i] for i in range(21, len(header)) if pos + i not in skip)))
        if len(header) < 24:
            break
        pos += 24 + struct.unpack_from("<I", header, 16)[0]
    return out


def test_a_grant_readdir_writes_zero_dirent_padding(tmp_path, monkeypatch) -> None:
    """Criterion 3: the forwarded (no-provider) sibling of `test_a_mount_writes_zero_dirent_
    padding`. A guard table forwards fd_readdir on a real folder over a buffer filled with 0xFF;
    every entry's padding is zero within [buf, buf + used), on full and cut-short buffers, and
    nothing past `used` is touched. wasmtime 49.0.0 leaves host bytes in the padding only as its
    heap happens to hold them (GHSA-96f6-r43r-8c24), so each forwarded listing, the guest's and
    any the guard makes on its own page, then gets such bytes, 0xA5, in every entry's padding,
    where wasmtime's layout puts it, before its count is written: what the guard must zero,
    every time. A `used` pointer inside the buffer gets wasmtime's count, and the padding is
    zeroed even where that count lands on a d_namlen the walk would follow (the build review,
    F1: `buf + 16`) or on padding (F4: `buf + 72`)."""
    real_forward = mounts_module._Files.forward
    layout: dict[str, list[int]] = {}  # the entries' offsets, when `used` hides one

    def soiled(self, caller, name, args, stat=False):
        errno = real_forward(self, caller, name, args, stat)
        if name == "fd_readdir" and errno == 0:
            if stat:  # the guard's own listing, on its page
                page = self.forwards.page
                read = lambda at, n: bytes(page.read(caller, at, at + n))  # noqa: E731
                write = lambda at, data: page.write(caller, data, at)  # noqa: E731
            else:
                memory = mounts_module._Memory(caller)
                read, write = memory.read, memory.write
            buf, used = args[1] & 0xFFFFFFFF, args[4] & 0xFFFFFFFF
            data = bytearray(read(buf, struct.unpack("<I", read(used, 4))[0]))
            starts = [pos for pos, _ in _pads(bytes(data))]
            if not stat and buf <= used < buf + len(data):
                starts = layout["d"]
            for pos in starts:
                for at in range(pos + 21, min(pos + 24, len(data))):
                    if not used <= buf + at < used + 4:  # the count is written after the entries
                        data[at] = 0xA5
            write(buf, bytes(data))
        return errno

    monkeypatch.setattr(mounts_module._Files, "forward", soiled)
    tree = files.write_tree(tmp_path / "tree")
    r = files.Guarded([(tree, "/m", False)]).raw
    d = r.open(3, "d", files.O_DIRECTORY)[1]
    assert d is not None
    for fd in (3, d):
        for size in (4096, 22, 23, 25, 47, 48, 50, 80):  # 22, 23, 47, 48 end in a header's padding
            r.put(files.DIRBUF, b"\xff" * 4096)
            assert r("fd_readdir", fd, files.DIRBUF, size, 0, files.RESULT) == 0
            used = r.u32(files.RESULT)
            pads = _pads(r.get(files.DIRBUF, used))
            assert pads and all(pad == bytes(len(pad)) for _, pad in pads), (fd, size, pads)
            assert r.get(files.DIRBUF + used, 1) == b"\xff"  # nothing past what it used
    # `used` inside the buffer. The folder `d` lists `.`, `..` and `x.txt` at 0, 25 and 51.
    r.put(files.DIRBUF, b"\xff" * 4096)
    assert r("fd_readdir", d, files.DIRBUF, 4096, 0, files.RESULT) == 0
    count = r.u32(files.RESULT)  # wasmtime's count for this listing
    layout["d"] = [pos for pos, _ in _pads(r.get(files.DIRBUF, count))]
    assert (count, layout["d"]) == (80, [0, 25, 51])
    for offset in (72, 16):  # the third entry's padding; the first entry's d_namlen
        inside = files.DIRBUF + offset
        r.put(files.DIRBUF, b"\xff" * 4096)
        assert r("fd_readdir", d, files.DIRBUF, 4096, 0, inside) == 0
        assert r.u32(inside) == count, offset  # wasmtime's count, written last, is kept
        data = r.get(files.DIRBUF, count)
        kept = range(offset, offset + 4)
        left = {
            pos: bytes(data[i] for i in range(pos + 21, pos + 24) if i not in kept)
            for pos in layout["d"]
        }
        assert all(pad == bytes(len(pad)) for pad in left.values()), (offset, left)
        assert r.get(files.DIRBUF + count, 1) == b"\xff", offset  # nothing past it


def _over_its_listing(tmp_path, monkeypatch, then=None):
    """A guard over the folder `d` (`.`, `..`, `x.txt`: entries at 0, 25 and 51, 80 bytes) whose
    guest listing, once wasmtime has written it, gets 0xA5 in every entry's padding, as host
    bytes would be; `then(self, caller, name, args, stat)` replaces the guard's own listing."""
    real = mounts_module._Files.forward

    def forward(self, caller, name, args, stat=False):
        if stat and name == "fd_readdir" and then is not None:
            return then(self, caller, name, args, stat, real)
        errno = real(self, caller, name, args, stat)
        if name == "fd_readdir" and not stat and errno == 0:
            memory = mounts_module._Memory(caller)
            for pos in (0, 25, 51):
                memory.write((args[1] & 0xFFFFFFFF) + pos + 21, b"\xa5\xa5\xa5")
        return errno

    monkeypatch.setattr(mounts_module._Files, "forward", forward)
    tree = files.write_tree(tmp_path / "tree")
    g = files.Guarded([(tree, "/m", False)])
    d = g.raw.open(3, "d", files.O_DIRECTORY)[1]
    g.raw.put(files.DIRBUF, b"\xff" * 4096)
    return tree, g, d


def test_a_listing_that_cannot_be_listed_again_is_zeroed_whole(tmp_path, monkeypatch) -> None:
    """Decision 4's fallback (the build review's confirmation, C1): with `used` over its own
    listing and the guard's second listing failing, the guest gets EIO, a count of 0 and a
    listing of zeros: no byte of the first listing, its host bytes included, is left; nothing
    past it is touched."""
    _, g, d = _over_its_listing(tmp_path, monkeypatch, lambda *a: EBADF)
    r, used = g.raw, files.DIRBUF + 16
    assert r("fd_readdir", d, files.DIRBUF, 4096, 0, used) == 29  # EIO
    assert r.u32(used) == 0
    assert r.get(files.DIRBUF, 80) == bytes(80)
    assert r.get(files.DIRBUF + 80, 1) == b"\xff"


def test_a_listing_that_shrinks_between_the_two_is_zeroed_past_the_second(
    tmp_path, monkeypatch
) -> None:
    """Decision 4 (C1): the folder loses its file between the guest's listing and the guard's
    second one. The guest gets the second listing (`.` and `..`, 51 bytes) with zero padding,
    and the first listing's bytes past it, host bytes included, are zeroed."""

    def emptied(self, caller, name, args, stat, real):
        for child in (tree / "d").iterdir():
            child.unlink()
        return real(self, caller, name, args, stat)

    tree = tmp_path / "tree"
    _, g, d = _over_its_listing(tmp_path, monkeypatch, emptied)
    r, used = g.raw, files.DIRBUF + 16
    assert r("fd_readdir", d, files.DIRBUF, 4096, 0, used) == 0
    assert r.u32(used) == 51
    data = r.get(files.DIRBUF, 80)
    assert [data[pos + 21 : pos + 24] for pos in (0, 25)] == [b"\0\0\0", bytes(3)], data.hex()
    assert data[51:80] == bytes(29), data.hex()
    assert r.get(files.DIRBUF + 80, 1) == b"\xff"


def test_the_second_listing_never_outgrows_the_guests_memory(tmp_path, monkeypatch) -> None:
    """Decision 4 (C2): the guard's second listing asks for no more than the guest's buffer can
    hold in its memory, `min(length, memory - buf)`, so its page never grows past the guest's
    memory and a `length` past the store's memory limit is not a way to EIO: the answer is
    wasmtime's 0 and the listing's padding is zero."""
    for length, limit in ((0xFFFFFFF0, None), (0x3FFF0000, 64 << 20)):
        _, g, d = _over_its_listing(tmp_path / hex(length), monkeypatch)
        if limit is not None:
            g.store.set_limits(memory_size=limit)
        r, used = g.raw, files.DIRBUF + 16
        assert r("fd_readdir", d, files.DIRBUF, length, 0, used) == 0, hex(length)
        assert r.u32(used) == 80
        data = r.get(files.DIRBUF, 80)
        assert all(data[p + 21 : p + 24] == bytes(3) for p in (0, 25, 51)), data.hex()
        guest = g.instance.exports(g.store)["memory"].data_len(g.store)
        assert g.table.forwards.page.data_len(g.store) <= guest, hex(length)


def test_the_rename_is_forwarded_by_its_plain_names(tmp_path, monkeypatch) -> None:
    """Decision 1 (the build review, F2): once a slash-named source passes as a folder, the
    rename is forwarded with every trailing slash trimmed from both paths, so whatever replaces
    the source between the guard's stat and wasmtime's rename is renamed by its plain name and
    never followed. Here the folder `d` is swapped for a link out, `d -> ../outside`, right after
    the stat answers "folder", as a concurrent call or another host process could: the link
    itself is renamed, and the folder outside every grant stays where it is, on every host."""
    grant, outside = tmp_path / "grant", tmp_path / "outside"
    (grant / "d").mkdir(parents=True)
    (outside / "canary.txt").parent.mkdir()
    (outside / "canary.txt").write_text("CANARY")
    try:
        os.symlink("target", tmp_path / "probe")
    except OSError as e:
        pytest.skip(f"this host cannot make a symbolic link ({e.errno})")
    real_type, real_forward = mounts_module._Files._source_type, mounts_module._Files.forward
    forwarded = []

    def swapped(self, caller, fd, source):
        errno = real_type(self, caller, fd, source)
        if errno == 0:
            os.rmdir(grant / "d")
            os.symlink("../outside", grant / "d")
        return errno

    def recorded(self, caller, name, args, stat=False):
        if name == "path_rename":
            memory = mounts_module._Memory(caller)
            forwarded.append((memory.read(args[1], args[2]), memory.read(args[4], args[5])))
        return real_forward(self, caller, name, args, stat)

    monkeypatch.setattr(mounts_module._Files, "_source_type", swapped)
    monkeypatch.setattr(mounts_module._Files, "forward", recorded)
    r = files.Guarded([(grant, "/w", True)]).raw
    assert r.rename(3, "d/", 3, "stolen//") == 0
    assert forwarded == [(b"d", b"stolen")]
    assert sorted(p.name for p in grant.iterdir()) == ["stolen"]
    assert os.readlink(grant / "stolen") == "../outside"
    assert sorted(p.name for p in outside.iterdir()) == ["canary.txt"]
    assert (outside / "canary.txt").read_text() == "CANARY"


RENAME_LOOP = f"""(module
  (import "{P1}" "path_rename" (func $mv (param i32 i32 i32 i32 i32 i32) (result i32)))
  (import "{P1}" "fd_readdir" (func $ls (param i32 i32 i32 i64 i32) (result i32)))
  (memory (export "memory") 1)
  (func $leaf (result i32) (i32.const 7))
  (func (export "run") (param $n i32) (result i32) (local $e i32)
    (block $done (loop $l
      (br_if $done (i32.eqz (local.get $n)))
      ;; "d/e/f/" at 100, written by the host. d/ -> e, e/ -> d: a real folder named with a
      ;; slash, so the rule stats, then renames
      (local.set $e (i32.or (local.get $e) (call $mv (i32.const 3) (i32.const 100) (i32.const 2)
        (i32.const 3) (i32.const 102) (i32.const 1))))
      (local.set $e (i32.or (local.get $e) (call $mv (i32.const 3) (i32.const 102) (i32.const 2)
        (i32.const 3) (i32.const 100) (i32.const 1))))
      ;; f/ -> e: a file named with a slash, refused (ENOTDIR on either side)
      (local.set $e (i32.or (local.get $e) (call $mv (i32.const 3) (i32.const 104) (i32.const 2)
        (i32.const 3) (i32.const 102) (i32.const 1))))
      (local.set $e (i32.or (local.get $e)
        (call $ls (i32.const 3) (i32.const 1024) (i32.const 512) (i64.const 0) (i32.const 2048))))
      (drop (call $leaf))
      (local.set $n (i32.sub (local.get $n) (i32.const 1)))
      (br $l)))
    (local.get $e)))"""


def _rename_loop(base: Path, guarded: bool, cap: int, n: int = 40) -> tuple[str, int]:
    """How the loop ends and the fuel it used, on the guard linker or today's."""
    folder = base / f"{'guarded' if guarded else 'plain'}-{cap}"
    (folder / "d").mkdir(parents=True)
    (folder / "f").write_bytes(b"f")
    g = files.Guarded([(folder, "/w", True)], fuel=cap, wat=RENAME_LOOP)
    if guarded:
        exports = g.instance.exports(g.store)
    else:  # the same store's configuration on today's linker
        exports = g.plain.instantiate(g.store, wt.Module(g.engine, RENAME_LOOP)).exports(g.store)
    exports["memory"].write(g.store, b"d/e/f/", 100)  # by the host: no fuel on either side
    run = exports["run"]
    try:
        with g.entered():
            end = f"returned {run(g.store, n)}"
    except wt.Trap as e:
        end = f"trap {e.trap_code}"
    except files.Ends as e:
        end = f"stopped {e.message}"
    return end, cap - g.store.get_fuel()


def test_the_rename_rule_forward_is_fuel_neutral(tmp_path) -> None:
    """Criterion 4: a metered guard call whose shadow forwards a path_filestat_get (on the stat
    trampoline) and then a path_rename, and a fd_readdir, spends exactly the guest fuel today's
    native calls spend, and ends the same way with the same fuel at every cap from 1 up to past
    its need: each forward's allowance is set back."""
    full = _rename_loop(tmp_path, False, 10**9)
    assert full == _rename_loop(tmp_path, True, 10**9)
    assert full[0] == f"returned {ENOTDIR}"  # the renames of d succeed; f/ is refused
    need = full[1]
    for cap in [*range(1, 40, 3), *range(need - 30, need + 3)]:
        assert _rename_loop(tmp_path, True, cap) == _rename_loop(tmp_path, False, cap), cap


def test_a_guard_call_leaves_the_other_calls_native(tmp_path) -> None:
    """Criterion 5: the guard linker shadows exactly fd_readdir and path_rename; every other
    descriptor call (path_open, fd_read, fd_write, fd_seek and the rest) reaches wasmtime
    without passing the guard table, and the table makes no provider call."""
    seen = []
    g = files.Guarded([(tmp_path, "/w", False)])
    real = g.table.__class__.__call__

    def counting(self, caller, name, *args):
        seen.append(name)
        return real(self, caller, name, *args)

    g.table.__class__.__call__ = counting  # type: ignore[method-assign]
    try:
        for name, params in files.RAW_SIGNATURES.items():
            try:
                g.raw(name, *([2**31 - 1] * len(params)))
            except files.Ends:
                pass
    finally:
        g.table.__class__.__call__ = real  # type: ignore[method-assign]
    assert sorted(set(seen)) == ["fd_readdir", "path_rename"]
    assert g.table.record().calls == {"stat": 0, "list": 0, "read": 0}


def _answer(fn, *args, **kw) -> object:
    try:
        return fn(*args, **kw)
    except files.Ends as e:
        return ("ends", e.message)


def test_a_call_without_mounts_is_unchanged_but_for_the_two_fixes(tmp_path) -> None:
    """Criterion 5b, the before-and-after guard: on a call without mounts the guard table is
    never reported (`done.files is None`), and the raw fd_readdir and path_rename answers (errno,
    any trap and its message, every byte written but each entry's d_ino and padding) are
    today's native answers, except the two fixes: zeroed padding, and the trailing-slash rule
    (with a path past MAX_PATH unread once a slash is seen, condition C2)."""
    sides = []
    for name in ("native", "guarded"):
        tree = files.write_tree(tmp_path / name / "tree")
        w = tmp_path / name / "w"
        (w / "sub").mkdir(parents=True)
        (w / "w.txt").write_bytes(b"w\n")
        folders = [(tree, "/m", False), (w, "/w", True)]
        sides.append(files.grant_raw(folders) if name == "native" else files.Guarded(folders).raw)
    native, guarded = sides
    end, P, W = files.MEMORY_END, 3, 4
    unaligned = files.RESULT + 1

    def readdir(r, fd, size=4096, cookie=0, buf=files.DIRBUF, used=files.RESULT):
        r.clear()
        r.put(files.DIRBUF, b"\xff" * 4096)
        errno = r("fd_readdir", fd, buf, size, cookie, used)
        if errno or used != files.RESULT:
            return errno
        data = r.get(files.DIRBUF, r.u32(files.RESULT))
        return errno, files.masked_dirents(data, (*range(8, 16), 21, 22, 23))

    def rows(r) -> dict[str, object]:
        D = r.open(P, "d", files.O_DIRECTORY)[1]
        F = r.open(P, "a.txt")[1]
        out: dict[str, object] = {}
        for size, cookie in [(4096, 0), (4096, 1), (4096, 2), (4096, 3), (10, 0), (24, 0),
                             (25, 0), (30, 0), (50, 0), (0, 0), (4096, -1)]:  # fmt: skip
            out[f"readdir {size} {cookie}"] = _answer(readdir, r, D, size, cookie)
        out["readdir the file"] = _answer(lambda: readdir(r, F))
        out["readdir nothing"] = _answer(lambda: readdir(r, 99))
        out["readdir buffer past memory"] = _answer(lambda: readdir(r, D, 100, buf=end - 10))
        out["readdir used past memory"] = _answer(lambda: readdir(r, D, used=end))
        out["readdir used unaligned"] = _answer(lambda: readdir(r, D, used=unaligned))
        for label, a, old, b, new in [
            ("within", W, "w.txt", W, "v.txt"),
            ("back", W, "v.txt", W, "w.txt"),
            ("a folder", W, "sub", W, "sub2"),
            ("a folder, slash", W, "sub2/", W, "sub"),
            ("a folder, both slashes", W, "sub/", W, "sub2/"),
            ("a folder back", W, "sub2", W, "sub"),
            ("nothing", W, "missing", W, "x"),
            ("read-only", P, "a.txt", P, "c.txt"),
            ("read-only folder, slash", P, "d/", P, "c"),
            ("to nothing", W, "w.txt", 99, "x"),
            ("from the file", F, "w.txt", W, "x"),
            ("not UTF-8", W, "w.txt", W, "\udcff".encode("utf-8", "surrogatepass")),
            ("not UTF-8, slash", W, "w.txt", W, b"\xff/"),
        ]:
            out[f"rename {label}"] = _answer(r.rename, a, old, b, new)
        for label, args in [
            ("old past memory", (W, end - 2, 4, W, files.PATH2, 1)),
            ("new past memory", (W, files.PATH, 1, W, end - 2, 4)),
            ("old length past memory", (W, files.PATH, end, W, files.PATH2, 1)),
        ]:
            r.path("w.txt")
            r.path("x", files.PATH2)
            out[f"rename {label}"] = _answer(r, "path_rename", *args)
        return out

    want, got = rows(native), rows(guarded)
    assert list(want) == list(got)
    differ = {k: (want[k], got[k]) for k in want if want[k] != got[k]}
    assert differ == {}, differ
    # The fixes. The padding: each guarded entry's bytes 21 to 24 are zero.
    D = guarded.open(P, "d", files.O_DIRECTORY)[1]
    guarded.put(files.DIRBUF, b"\xff" * 4096)
    assert guarded("fd_readdir", D, files.DIRBUF, 4096, 0, files.RESULT) == 0
    pads = _pads(guarded.get(files.DIRBUF, guarded.u32(files.RESULT)))
    assert len(pads) == 3 and all(pad == bytes(3) for _, pad in pads), pads
    # The rule: a slash on either path needs a source that is a folder; the stat's own errno
    # otherwise (a missing source reads ENOENT even on a read-only grant, Decision 3).
    # The rows marked "order" are Decision 3's recorded errno order: once a slash is seen the
    # guard reads both paths and stats the source before wasmtime sees the call, so its answer
    # comes first where today's native and wasmtime 49.0.3 answer EBADF (a bad descriptor) or
    # EPERM (a read-only or mixed pair) first. Nothing is renamed either way.
    rule = {
        "a file, slash": (W, "w.txt/", W, "x", ENOTDIR),
        "to a slash": (W, "w.txt", W, "x/", ENOTDIR),
        "nothing, slash": (W, "missing/", W, "x", ENOENT),
        "read-only file, slash": (P, "a.txt/", P, "x", ENOTDIR),  # order: 49.0.3 EPERM
        "read-only nothing, slash": (P, "missing/", P, "x", ENOENT),  # order: 49.0.3 EPERM
        "read-only folder, to a slash": (P, "d", P, "x/", EPERM),
        "to a bad descriptor, slash": (W, "w.txt", 99, "x/", ENOTDIR),  # order: 49.0.3 EBADF
        "a file, slash, to read-only": (W, "w.txt/", P, "x", ENOTDIR),  # order: 49.0.3 EPERM
        "to an over-long slash": (W, "sub", W, "x/" * 2050, ENAMETOOLONG),  # unread, unforwarded
    }
    answers = {k: guarded.rename(a, old, b, new) for k, (a, old, b, new, _) in rule.items()}
    assert answers == {k: v[-1] for k, v in rule.items()}
    assert sorted(p.name for p in (tmp_path / "guarded" / "w").iterdir()) == ["sub", "w.txt"]
    # The guard table is never reported (Decision 7): `files` is None without mounts.
    needs.need("runner", "artifact dir")
    from wasi_python import run

    done = run(["-c", "import os; print(len(os.listdir('/usr/local/lib')))"])
    assert (done.exit_code, done.files) == (0, None), done
