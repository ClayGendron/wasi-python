"""Read-only mounts (spec 032): the runner's own boundary code, which does not depend on the host,
so these run on the judge's machine only. Raw preview1 calls through the mount linker, with the
call on the thread's stack (harness/files.py); fuel and provider calls are counted, nothing is
timed."""

from __future__ import annotations

import os
import struct
import sys
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
    assert m.table.record().calls == {
        "stat": 2,
        "list": 0,
        "read": 0,
        "write": 0,
        "mkdir": 0,
        "remove": 0,
        "rmdir": 0,
        "rename": 0,
    }


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
    assert provider.calls == {
        "stat": 0,
        "list": 2,
        "read": 1,
        "write": 0,
        "mkdir": 0,
        "remove": 0,
        "rmdir": 0,
        "rename": 0,
    }
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
    the two guarded calls (fd_readdir, path_rename) and the three counted ones (path_open,
    fd_close, fd_renumber; spec 068), and reports no file record; a call with one uses the mount
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
    assert set(served) <= set(mounts_module.GUARDED + mounts_module.COUNTED), served
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


# How today's native linker (wasmtime 49.0.0 alone) ends the rename loop, per system (spec 076,
# Decision 5). The guard ends `returned ENOTDIR` on every system: it carries wasmtime 49.0.3's
# rule, a path ending in `/` needs a folder source (spec 048). On Linux and macOS 49.0.0 puts the
# source's slash back and the kernel answers ENOTDIR too. On Windows 49.0.0 strips the slash and
# renames the file `f` to `e` with no kind check (its `via_parent/rename.rs` re-appends the slash
# under `#[cfg(unix)]` only; READ); the next turn renames the folder `d` over the file `e`, which
# Windows allowed on GitHub's `windows-2025-vs2026` image, version 20261007.264.1 (spec 058's
# cause); from then on `f/` is missing, ENOENT. Seen there: `returned 44` against the guard's
# `returned 54`, with equal fuel (spec 063's dry runs, EXECUTED). Another image may differ: a red
# run there is a fact about the reference, decided by spec 076's Decision 9.
NATIVE_RENAME_END = {
    "linux": f"returned {ENOTDIR}",
    "darwin": f"returned {ENOTDIR}",
    "win32": f"returned {ENOENT}",
}


def test_the_rename_rule_forward_is_fuel_neutral(tmp_path) -> None:
    """Criterion 4: a metered guard call whose shadow forwards a path_filestat_get (on the stat
    trampoline) and then a path_rename, and a fd_readdir, spends exactly the guest fuel today's
    native calls spend, and ends the same way with the same fuel at every cap from 1 up to past
    its need: each forward's allowance is set back. The guard's loop ends ENOTDIR on every
    system; today's native loop ends as `NATIVE_RENAME_END` says for this system (spec 076,
    Decision 5), so on Windows a loop that completes ends differently on the two sides."""
    native_end = NATIVE_RENAME_END[sys.platform]
    guarded_end = f"returned {ENOTDIR}"  # the renames of d succeed; f/ is refused

    def native_as_guarded(end: tuple[str, int]) -> tuple[str, int]:
        return (guarded_end, end[1]) if end[0] == native_end else end

    full = _rename_loop(tmp_path, False, 10**9)
    assert full[0] == native_end, full
    assert _rename_loop(tmp_path, True, 10**9) == (guarded_end, full[1])
    need = full[1]
    for cap in [*range(1, 40, 3), *range(need - 30, need + 3)]:
        native = native_as_guarded(_rename_loop(tmp_path, False, cap))
        assert _rename_loop(tmp_path, True, cap) == native, cap


def test_a_guard_call_leaves_the_other_calls_native(tmp_path) -> None:
    """Criterion 5: the guard linker shadows exactly fd_readdir and path_rename, and the three
    calls spec 068 counts (path_open, fd_close, fd_renumber); every other descriptor call
    (fd_read, fd_write, fd_seek and the rest) reaches wasmtime without passing the guard table,
    and the table makes no provider call."""
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
    assert sorted(set(seen)) == [
        "fd_close",
        "fd_readdir",
        "fd_renumber",
        "path_open",
        "path_rename",
    ]
    assert g.table.record().calls == dict.fromkeys(
        ("stat", "list", "read", "write", "mkdir", "remove", "rmdir", "rename"), 0
    )  # spec 034's eight keys (Decision 11)


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


# Writable mounts (spec 034): the runner's own guards, which do not depend on the host.

WRITE_HALF = ("write", "mkdir", "remove", "rmdir", "rename")
ALL = files.RIGHTS_ALL


def _written(provider: MemoryProvider) -> dict[str, int]:
    return {k: provider.calls[k] for k in WRITE_HALF}


def test_a_writable_mount_is_asked_for(placeholder) -> None:
    """Spec 034, acceptance 8 (guard: the writable check): a mount not made writable, over a
    provider that has the write half, answers every write-shaped call EPERM and never calls the
    write half."""
    provider = MemoryProvider()
    r = Mounted(provider, placeholder).raw
    f = r.open(3, "a.txt")[1]
    assert f is not None
    rows = {
        "x": r.open(3, "n", files.O_CREAT | files.O_EXCL, ALL)[0],
        "w": r.open(3, "a.txt", files.O_CREAT | files.O_TRUNC, ALL)[0],
        "truncate": r.open(3, "a.txt", files.O_TRUNC)[0],
        "create": r.open(3, "n", files.O_CREAT)[0],
        "r+": r.open(3, "a.txt", 0, ALL)[0],
        "mkdir": r.path_call("path_create_directory", 3, "n"),
        "remove": r.path_call("path_unlink_file", 3, "a.txt"),
        "rmdir": r.path_call("path_remove_directory", 3, "e"),
        "rename": r.rename(3, "a.txt", 3, "c"),
        "link": r.link(3, "a.txt", 3, "c"),
        "symlink": r.symlink("a.txt", 3, "l"),
        "path set-times": r.path_set_times(3, "a.txt", 0),
        "file set-times": r("fd_filestat_set_times", f, 0, 0, 0),
        "preopen set-times": r("fd_filestat_set_times", 3, 0, 0, 0),
        "set size": r("fd_filestat_set_size", f, 0),
    }
    assert rows == dict.fromkeys(rows, 63), rows
    assert _written(provider) == dict.fromkeys(WRITE_HALF, 0)


class _Missing(MemoryProvider):
    def __init__(self, method: str) -> None:
        super().__init__()
        setattr(self, method, None)


class _AsyncWrite(MemoryProvider):
    async def write(self, path, data):  # type: ignore[override]
        return None


@pytest.mark.parametrize(
    ("mount", "match"),
    [
        (Mount(MemoryProvider(), "/w", writable="yes"), r"mounts\[0\] at /w: writable must be"),
        (Mount(MemoryProvider(), "/w", writable=1), "writable must be True or False"),
        (Mount(MemoryProvider(), "/w", writable=None), "writable must be True or False"),
        *[
            (Mount(_Missing(m), "/w", writable=True), rf"mounts\[0\] at /w: .*no callable {m}")
            for m in WRITE_HALF
        ],
        (Mount(_AsyncWrite(), "/w", writable=True), r"write\(\) is a coroutine function"),
    ],
)
def test_a_writable_mount_is_checked_before_any_work(mount, match) -> None:
    """Spec 034, acceptance 8: `writable` must be a real bool, and a writable mount's provider
    must have the whole write half, none of it a coroutine function; each is a TypeError naming
    the mount, raised by run and run_async before the provider or a door host is called."""
    import asyncio

    from wasi_python import run, run_async

    frames: list[bytes] = []
    for call in (run, lambda *a, **k: asyncio.run(run_async(*a, **k))):
        with pytest.raises(TypeError, match=match):
            call(["-c", "pass"], host=frames.append, mounts=[mount])
    assert (mount.provider.total(), frames) == (0, [])


def test_writes_are_bounded(placeholder) -> None:
    """Spec 034, acceptance 12 (guard: the growth bound): with a staging bound of 1,000 bytes, a
    size past it, a write after a seek to it, a second file whose bytes would take the sum past
    it, and a one-byte `fd_pwrite` at 2**40 each answer EFBIG and change nothing; the table's
    staged count never passes the bound. (Each is asserted before the next, so a runner without
    the bound fails before it tries to allocate 2**40 bytes.)"""
    provider = MemoryProvider({"/f": b"x" * 10})
    m = Mounted(provider, placeholder, writable=True, staging=1000)
    r = m.raw
    f = r.open(3, "f", 0, ALL)[1]
    assert f is not None and m.table.staged == 10
    assert r("fd_filestat_set_size", f, 1001) == 22
    assert (r.filestat(f)[3], m.table.staged) == (10, 10)
    assert r.seek(f, 1000, 0) == (0, 1000)
    assert r.write(f, b"y") == (22, 0)
    assert (r.filestat(f)[3], m.table.staged) == (10, 10)
    assert r("fd_filestat_set_size", f, 990) == 0
    assert (r.filestat(f)[3], m.table.staged) == (990, 990)
    g = r.open(3, "g", files.O_CREAT, ALL)[1]
    assert g is not None
    assert r.write(g, b"z" * 11) == (22, 0)
    assert (r.filestat(g)[3], m.table.staged) == (0, 990)
    assert r.write(g, b"z" * 10) == (0, 10)
    assert (r.filestat(g)[3], m.table.staged) == (10, 1000)
    assert r.write(f, b"y", 2**40) == (22, 0)
    assert (r.filestat(f)[3], m.table.staged) == (990, 1000)


def test_an_unlinked_folder_holds_nothing(placeholder) -> None:
    """Spec 034, acceptance 9's raw part (guard: the unlinked-folder rule): a folder open while
    the guest removes it and makes it again answers every path call through the old descriptor
    ENOENT and lists only `.` and `..` from cookie 0, each with no provider call; a file open
    while the guest removes it keeps its buffer and is never written back."""
    provider = MemoryProvider()
    m = Mounted(provider, placeholder, writable=True)
    r = m.raw
    d = r.open(3, "e", files.O_DIRECTORY)[1]
    f = r.open(3, "a.txt", 0, ALL)[1]
    assert d is not None and f is not None
    assert r.write(f, b"kept") == (0, 4)
    rows = {
        "rmdir": r.path_call("path_remove_directory", 3, "e"),
        "mkdir": r.path_call("path_create_directory", 3, "e"),
        "remove": r.path_call("path_unlink_file", 3, "a.txt"),
    }
    y = r.open(3, "e/y", files.O_CREAT, ALL)[1]
    assert y is not None and r("fd_close", y) == 0
    assert rows == {"rmdir": 0, "mkdir": 0, "remove": 0}
    before = provider.total()
    rows = {
        "open": r.open(d, "y")[0],
        "open to write": r.open(d, "z", files.O_CREAT, ALL)[0],
        "stat": r.path_filestat(d, "y")[0],
        "readlink": r.readlink(d, "y")[0],
        "set-times": r.path_set_times(d, "y", 0),
        "mkdir": r.path_call("path_create_directory", d, "z"),
        "remove": r.path_call("path_unlink_file", d, "y"),
        "rmdir": r.path_call("path_remove_directory", d, "z"),
        "rename": r.rename(d, "y", 3, "z"),
        "re-list": r.readdir_names(d),
        "the file's bytes": (r.seek(f, 0, 0), r.read(f, [4])),
        "the file's sync": r("fd_sync", f),
        "the file's close": r("fd_close", f),
    }
    assert rows == {
        "open": 44,
        "open to write": 44,
        "stat": 44,
        "readlink": 44,
        "set-times": 44,
        "mkdir": 44,
        "remove": 44,
        "rmdir": 44,
        "rename": 44,
        "re-list": (0, [(".", 3), ("..", 3)]),
        "the file's bytes": ((0, 0), (0, 4, b"kept")),
        "the file's sync": 0,
        "the file's close": 0,
    }, rows
    assert provider.total() == before
    assert provider.tree["/e/y"] == b"" and "/a.txt" not in provider.tree


def test_the_runner_answers_namespace_calls_it_can(placeholder, tmp_path) -> None:
    """Spec 034, Decision 6: the calls the runner answers with no provider call: the mount
    itself (Linux's answers, wasmtime's reference), a rename into its own subfolder, a rename or
    rmdir strictly above a more specific preopen (EBUSY), a rename or link to another
    descriptor (EPERM when that side is read-only, EXDEV when both may be written), a link or
    symlink within (ENOTSUP); and a rename onto itself, one `stat`."""
    rw, ro = tmp_path / "rw", tmp_path / "ro"
    rw.mkdir()
    ro.mkdir()
    (rw / "w.txt").write_bytes(b"w")
    (ro / "r.txt").write_bytes(b"r")
    provider = MemoryProvider()
    folders = [(rw, "/rw", True), (ro, "/ro", False), (tmp_path / "rw", "/m/d/inner", True)]
    m = Mounted(provider, placeholder, writable=True, folders=folders)
    r = m.raw
    rows = {
        "mkdir of the mount": r.path_call("path_create_directory", 3, "."),
        "remove of the mount": r.path_call("path_unlink_file", 3, "."),
        "rmdir of the mount": r.path_call("path_remove_directory", 3, "."),
        "rename of the mount": r.rename(3, ".", 3, "q"),
        "rename onto the mount": r.rename(3, "a.txt", 3, "."),
        "rename into its own subfolder": r.rename(3, "e", 3, "e/sub"),
        "rmdir above a nested preopen": r.path_call("path_remove_directory", 3, "d"),
        "rename above a nested preopen": r.rename(3, "d", 3, "q"),
        "rename onto a folder above one": r.rename(3, "e", 3, "d"),
        "rmdir at a nested preopen": r.path_call("path_remove_directory", 3, "d/inner"),
        "rename to a writable grant": r.rename(3, "a.txt", 4, "c"),
        "rename from a writable grant": r.rename(4, "w.txt", 3, "c"),
        "rename to a read-only grant": r.rename(3, "a.txt", 5, "c"),
        "link to a writable grant": r.link(3, "a.txt", 4, "c"),
        "link to a read-only grant": r.link(3, "a.txt", 5, "c"),
        "link within": r.link(3, "a.txt", 3, "c"),
        "symlink within": r.symlink("a.txt", 3, "l"),
    }
    assert rows == {
        "mkdir of the mount": 20,
        "remove of the mount": 31,
        "rmdir of the mount": 28,
        "rename of the mount": 10,
        "rename onto the mount": 10,
        "rename into its own subfolder": 28,
        "rmdir above a nested preopen": 10,
        "rename above a nested preopen": 10,
        "rename onto a folder above one": 10,
        "rmdir at a nested preopen": 63,
        "rename to a writable grant": 75,
        "rename from a writable grant": 75,
        "rename to a read-only grant": 63,
        "link to a writable grant": 75,
        "link to a read-only grant": 63,
        "link within": 58,
        "symlink within": 58,
    }, rows
    assert provider.total() == 0
    assert (r.rename(3, "a.txt", 3, "./a.txt"), r.rename(3, "nope", 3, "nope")) == (0, 44)
    assert dict(provider.calls) == {**dict.fromkeys(provider.calls, 0), "stat": 2}
    assert sorted(p.name for p in rw.iterdir()) == ["w.txt"]


SPIN_DIRTY = (
    "import os\n"
    "flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC\n"
    "fds = [os.open(f'/w/{{n}}.txt', flags) for n in range({files})]\n"
    "for fd in fds:\n"
    "    os.write(fd, b'dirty')\n"
)


def test_the_walk_is_bounded_and_keeps_its_record(placeholder) -> None:
    """Spec 034, acceptance 12 (guards: the limit in the walk, the fault catch in the walk,
    `refused_total`): when the walk's write-backs would pass `max_file_calls`, the provider's
    calls stop exactly at the limit, each unmade write-back is one RefusedWrite for the limit,
    and the run keeps its exit and its fuel count (the walk names no end and spends no fuel:
    exactly, on the table, below; a guest's fuel differs run to run, so `run()` shows only that
    it is counted); a walk `write` that raises does not stop the walk; 1,001 refused `mkdir`s
    and one refused write-back are 1,000 kept and 1,002 counted."""
    needs.need("runner", "artifact dir")
    from wasi_python import RefusedWrite, run

    code = SPIN_DIRTY.format(files=4)
    ends = []
    for limit in (None, 6):  # 4 creates, then 2 of the 4 write-backs
        provider = MemoryProvider({})
        mounts = [Mount(provider, "/w", writable=True)]
        done = run(["-c", code], mounts=mounts, max_file_calls=limit, fuel=10**12)
        ends.append((done.exit_code, done.trapped, done.fuel_used is not None))
    assert ends == [(0, None, True)] * 2, ends
    assert provider.total() == 6 and provider.writes() == [b""] * 4 + [b"dirty"] * 2
    assert done.files.refused == tuple(
        RefusedWrite("/w", "write", (f"/{n}.txt",), Errno.EIO, "exit", "limit") for n in (2, 3)
    )
    provider = MemoryProvider({})
    m = Mounted(provider, placeholder, writable=True, file_calls=1, fuel=10**6)
    f = m.raw.open(3, "n", files.O_CREAT | files.O_TRUNC, ALL)[1]
    assert f is not None and m.raw.write(f, b"n") == (0, 1)
    fuel = m.store.get_fuel()
    m.table.walk()
    assert (m.store.get_fuel(), m.call.ended, m.call.stopped) == (fuel, None, None)
    assert provider.writes() == [b""] and m.table.record().refused_total == 1
    provider = MemoryProvider({})

    def raises(path, data):
        if data:
            raise ValueError("broke")

    provider.answers[("write", "/0.txt")] = raises
    done = run(["-c", SPIN_DIRTY.format(files=2)], mounts=[Mount(provider, "/w", writable=True)])
    assert done.exit_code == 0 and provider.writes("/1.txt") == [b"", b"dirty"]
    assert [r.cause for r in done.files.refused] == ["fault"]
    provider = MemoryProvider({})
    provider.answers[("mkdir", "/m")] = Errno.EACCES
    provider.answers[("write", "/0.txt")] = lambda path, data: Errno.ENOSPC if data else None
    code = SPIN_DIRTY.format(files=1) + (
        "for _ in range(1001):\n"
        "    try:\n"
        "        os.mkdir('/w/m')\n"
        "    except PermissionError:\n"
        "        pass\n"
    )
    done = run(["-c", code], mounts=[Mount(provider, "/w", writable=True)])
    assert done.exit_code == 0, done
    assert (len(done.files.refused), done.files.refused_total) == (1000, 1002)
    assert {r.method for r in done.files.refused} == {"mkdir"}


OWED = f"""(module
  (import "{P1}" "path_open"
    (func $open (param i32 i32 i32 i32 i32 i64 i64 i32 i32) (result i32)))
  (import "{P1}" "fd_write" (func $write (param i32 i32 i32 i32) (result i32)))
  (import "{P1}" "path_filestat_get" (func $stat (param i32 i32 i32 i32 i32) (result i32)))
  (import "{P1}" "fd_close" (func $close (param i32) (result i32)))
  (memory (export "memory") 1)
  (data (i32.const 100) "f.txt")
  (data (i32.const 200) "a.txt")
  (data (i32.const 220) "g.txt")
  (data (i32.const 300) "\\90\\01\\00\\00\\04\\00\\00\\00")
  (data (i32.const 400) "data")
  (func (export "run") (local $fd i32)
    (i32.store (i32.const 600) (call $open (i32.const 3) (i32.const 0) (i32.const 100)
      (i32.const 5) (i32.const 9) (i64.const {files.RIGHTS_ALL}) (i64.const 0) (i32.const 0)
      (i32.const 500)))
    (local.set $fd (i32.load (i32.const 500)))
    (i32.store (i32.const 604) (call $write (local.get $fd) (i32.const 300) (i32.const 1)
      (i32.const 504)))
    (i32.store (i32.const 608) (call $stat (i32.const 3) (i32.const 0) (i32.const 200)
      (i32.const 5) (i32.const 512)))
    (i32.store (i32.const 612) (call $close (local.get $fd)))
    (i32.store (i32.const 616) (call $open (i32.const 3) (i32.const 0) (i32.const 220)
      (i32.const 5) (i32.const 0) (i64.const {files.READ_RIGHTS}) (i64.const 0) (i32.const 0)
      (i32.const 580)))))"""


def test_a_close_stopped_by_a_cancel_is_owed(placeholder) -> None:
    """Spec 034, acceptance 16 (guard: the reserved number): a guest writes a provider file; a
    provider whose `stat` sets the call's cancel is called, and the file's `fd_close` follows
    with no function entry between: the close answers ECANCELED, an open after it makes no call,
    the number stays reserved (not free, still counted), and the walk writes it back once, with
    nothing refused. With the file-call limit instead: the close answers EIO, no write is made,
    and the record names the file once, at "exit", for the limit."""
    from wasi_python import RefusedWrite

    for case in ("cancel", "limit"):
        cancel = threading.Event()
        provider = MemoryProvider()
        if case == "cancel":
            provider.answers[("stat", "/a.txt")] = lambda path, c=cancel: (c.set(), Stat("file"))[1]
        m = Mounted(
            provider,
            placeholder,
            writable=True,
            wat=OWED,
            cancel=cancel,
            file_calls=2 if case == "limit" else None,
        )
        with m.entered():
            m.instance.exports(m.store)["run"](m.store)
        answers = struct.unpack("<5I", m.raw.get(600, 20))
        number = m.raw.u32(500)
        stopped = 11 if case == "cancel" else 29
        assert answers == (0, 0, 0, stopped, stopped), (case, answers)
        assert number not in m.table.table and number in m.table.owed, case
        assert number not in m.table.free and m.table.opened == 1, case
        assert provider.writes() == [b""] and provider.total() == 2, case
        m.table.walk()
        record = m.table.record()
        if case == "cancel":
            assert provider.writes() == [b"", b"data"]
            assert (record.refused, record.refused_total) == ((), 0)
        else:
            assert provider.writes() == [b""]
            assert record.refused == (
                RefusedWrite("/m", "write", ("/f.txt",), Errno.EIO, "exit", "limit"),
            )


def test_a_refused_rename_or_removal_moves_no_descriptor(placeholder) -> None:
    """Spec 034, Decision 7 (the build review, F1(b)): descriptors follow only a namespace call
    the provider accepted. A rename the provider refuses leaves a descriptor at its `src`
    writing back to `src` and one at its `dst` still writing back to `dst`; a refused `remove`
    unlinks nothing; a refused `rmdir` leaves a folder descriptor that still asks the provider."""
    provider = MemoryProvider()
    r = Mounted(provider, placeholder, writable=True).raw
    f, g = r.open(3, "a.txt", 0, ALL)[1], r.open(3, "b.txt", 0, ALL)[1]
    d = r.open(3, "d", files.O_DIRECTORY)[1]
    assert None not in (f, g, d)
    assert (r.write(f, b"A"), r.write(g, b"B")) == ((0, 1), (0, 1))
    provider.answers[("rename", "/a.txt")] = Errno.EACCES
    provider.answers[("remove", "/b.txt")] = Errno.EACCES
    provider.answers[("rmdir", "/d")] = Errno.EACCES
    assert r.rename(3, "a.txt", 3, "b.txt") == 2
    assert r.path_call("path_unlink_file", 3, "b.txt") == 2
    assert r.path_call("path_remove_directory", 3, "d") == 2
    reads = provider.calls["read"]
    assert r.open(d, "x.txt")[0] == 0 and provider.calls["read"] == reads + 1
    assert (r("fd_close", f), r("fd_close", g)) == (0, 0)
    assert provider.writes() == [b"Aello, mount\n", b"B\n"]
    assert [e[1] for e in provider.log if e[0] == "write"] == ["/a.txt", "/b.txt"]


GATED = f"""(module
  (import "{P1}" "path_open"
    (func $open (param i32 i32 i32 i32 i32 i64 i64 i32 i32) (result i32)))
  (import "{P1}" "path_filestat_get" (func $stat (param i32 i32 i32 i32 i32) (result i32)))
  (import "{P1}" "path_create_directory" (func $mkdir (param i32 i32 i32) (result i32)))
  (import "{P1}" "path_rename" (func $rename (param i32 i32 i32 i32 i32 i32) (result i32)))
  (memory (export "memory") 1)
  (data (i32.const 100) "new.txt")
  (data (i32.const 200) "a.txt")
  (data (i32.const 220) "newdir")
  (func (export "run")
    (i32.store (i32.const 600) (call $stat (i32.const 3) (i32.const 0) (i32.const 200)
      (i32.const 5) (i32.const 512)))
    (i32.store (i32.const 604) (call $mkdir (i32.const 3) (i32.const 220) (i32.const 6)))
    (i32.store (i32.const 608) (call $rename (i32.const 3) (i32.const 200) (i32.const 5)
      (i32.const 3) (i32.const 220) (i32.const 6)))
    (i32.store (i32.const 612) (call $open (i32.const 3) (i32.const 0) (i32.const 100)
      (i32.const 7) (i32.const 9) (i64.const {files.RIGHTS_ALL}) (i64.const 0) (i32.const 0)
      (i32.const 500)))))"""
PAST_THE_LIMIT = (
    "import os\n"
    "for i in range(50):\n"
    "    try:\n"
    "        {call}\n"
    "    except OSError:\n"
    "        pass\n"
    "print('after the loop')\n"
)


def test_the_write_half_is_gated(placeholder) -> None:
    """Spec 034, Decision 10 (the build review's confirmation, N1): a create at open and a
    namespace call are provider calls like any other. Past `max_file_calls`, `mkdir`s and
    writing opens stop at exactly the limit and the run ends "out of file calls"; once the
    call's cancel is set (by a provider's `stat`, with no function entry after it), a `mkdir`,
    a `rename` and a create at open each answer ECANCELED with no provider call."""
    needs.need("runner", "artifact dir")
    from wasi_python import run

    for call in ("os.mkdir(f'/w/d{i}')", "open(f'/w/f{i}', 'w')"):
        provider = MemoryProvider({})
        done = run(
            ["-c", PAST_THE_LIMIT.format(call=call)],
            mounts=[Mount(provider, "/w", writable=True)],
            max_file_calls=5,
        )
        assert (done.exit_code, done.trapped, done.stdout) == (None, "out of file calls", b"")
        assert provider.total() == 5 and done.files.calls == provider.calls, call
    cancel = threading.Event()
    provider = MemoryProvider()
    provider.answers[("stat", "/a.txt")] = lambda path: (cancel.set(), Stat("file"))[1]
    m = Mounted(provider, placeholder, writable=True, wat=GATED, cancel=cancel)
    with m.entered():
        m.instance.exports(m.store)["run"](m.store)
    assert struct.unpack("<4I", m.raw.get(600, 16)) == (0, 11, 11, 11)
    assert provider.total() == 1 and _written(provider) == dict.fromkeys(WRITE_HALF, 0)
    assert m.table.record().refused_total == 0  # an unmade call is not a refusal (N3)


# Spec 061: a provider's OSError carries its errno.


def test_a_generator_listing_that_raises_answers_its_errno(placeholder) -> None:
    """Criterion 5: a `list` written as a generator runs its body while the runner iterates it,
    so an `OSError` raised there is the answer of its errno too, before or after a `yield`, and
    so is one an iterable's own `__iter__` raises; the listing is dropped whole, nothing is
    held, and any other exception stays a fault."""
    import errno

    def generator(make, after_one):
        def how(path):
            def listing():
                if after_one:
                    yield ("a", "file")
                raise make()

            return listing()

        return how

    class RaisingIterable:
        """Not a generator: its `__iter__` raises, so `iter()` runs provider code (the build
        review, F2)."""

        def __iter__(self):
            raise FileNotFoundError("x")

    cases = [
        (lambda path: RaisingIterable(), 44),
        (generator(lambda: FileNotFoundError(errno.ENOENT, "gone"), False), 44),
        (generator(lambda: FileNotFoundError(errno.ENOENT, "gone"), True), 44),
        (generator(lambda: PermissionError("no"), True), 2),
        (generator(lambda: ValueError("broke"), True), 29),
    ]
    for how, want in cases:
        provider = MemoryProvider()
        provider.answers[("list", "/d")] = how
        m = Mounted(provider, placeholder)
        staged = m.table.staged
        assert m.raw.open(3, "d", files.O_DIRECTORY) == (want, None)
        assert (m.table.staged, m.table.opened) == (staged, 0)
        assert provider.calls["list"] == 1
        record = m.table.record()
        assert len(record.faults) == (1 if want == 29 else 0), record.faults


def test_a_mapped_oserror_leaves_nothing_of_itself(placeholder) -> None:
    """Criterion 6: the runner holds no reference to a mapped exception (nor so to the
    provider's frame), and the record keeps neither its message nor its class's name."""
    import errno
    import gc
    import weakref

    class Local:
        pass

    class _SecretNotFound(FileNotFoundError):
        pass

    refs: list[weakref.ref] = []

    class Holding(MemoryProvider):
        def stat(self, path):
            self._count("stat", path)
            local = Local()
            refs.append(weakref.ref(local))
            e = _SecretNotFound(errno.ENOENT, "the-secret-message-061")
            refs.append(weakref.ref(e))
            raise e

    m = Mounted(Holding(), placeholder)
    assert m.raw.path_filestat(3, "a.txt")[0] == 44
    gc.collect()
    assert [r() for r in refs] == [None, None]
    record = repr(m.table.record())
    assert "the-secret-message-061" not in record and "_SecretNotFound" not in record, record

    # The listing's path (the build review, F2): a raise from a generator `list`'s body.
    listed: list[weakref.ref] = []

    def listing(path):
        def body():
            e = _SecretNotFound(errno.ENOENT, "the-secret-message-061")
            listed.append(weakref.ref(e))
            yield ("a", "file")
            raise e

        return body()

    provider = MemoryProvider()
    provider.answers[("list", "/d")] = listing
    m = Mounted(provider, placeholder)
    assert m.raw.open(3, "d", files.O_DIRECTORY) == (44, None)
    gc.collect()
    assert [r() for r in listed] == [None]
    record = repr(m.table.record())
    assert "the-secret-message-061" not in record and "_SecretNotFound" not in record, record


# The memo's table (2026-10-18-a-providers-oserror-carries-its-errno): macOS and Linux EXECUTED,
# Windows READ (CPython's errnomodule.c: the WSA values) and INFERRED (MSVC's small numbers).
_ERRNO_NAMES = (
    "EPERM ENOENT EIO EACCES EBUSY EEXIST EXDEV ENOTDIR EISDIR EINVAL EFBIG ENOSPC EROFS "
    "ENAMETOOLONG ENOTEMPTY ENOSYS EDQUOT ESTALE ETIMEDOUT ECANCELED ENOTSUP EOPNOTSUPP"
).split()
_HOSTS = {
    "macOS": (1, 2, 5, 13, 16, 17, 18, 20, 21, 22, 27, 28, 30, 63, 66, 78, 69, 70, 60, 89, 45, 102),
    "Linux": (
        1,
        2,
        5,
        13,
        16,
        17,
        18,
        20,
        21,
        22,
        27,
        28,
        30,
        36,
        39,
        38,
        122,
        116,
        110,
        125,
        95,
        95,
    ),
    "Windows": (
        *(1, 2, 5, 13, 16, 17, 18, 20, 21, 22, 27, 28, 30, 38, 41, 40),
        *(10069, 10070, 10060, 105, 129, 10045),
    ),
}


def test_the_host_errno_table_is_by_name() -> None:
    """Criterion 7: the table from a host's errno names to the members is built by name, reaches
    every member on macOS's, Linux's and Windows's numbers (EOPNOTSUPP as ENOTSUP), holds no
    refused number, takes only plain ints, and skips a name the host lacks, so that importing
    `wasi_python` never fails for one."""
    import errno
    import subprocess
    import sys

    table = mounts_module._errno_table(vars(errno))
    assert set(table.values()) == set(Errno)
    keys = {getattr(errno, e.name) for e in Errno}
    if errno.EOPNOTSUPP != errno.ENOTSUP:
        keys.add(errno.EOPNOTSUPP)
    assert set(table) == keys
    assert all(table[getattr(errno, e.name)] is e for e in Errno)
    for refused in ("EINTR", "EAGAIN", "EBADF", "EFAULT"):
        assert getattr(errno, refused) not in table, refused
    assert mounts_module._HOST_ERRNO == table

    for host, numbers in _HOSTS.items():
        names = dict(zip(_ERRNO_NAMES, numbers, strict=True))
        hosted = mounts_module._errno_table(names)
        assert set(hosted.values()) == set(Errno), host
        assert hosted[names["EOPNOTSUPP"]] is Errno.ENOTSUP, host
        assert len(hosted) == (21 if host == "Linux" else 22), (host, len(hosted))

    class Sneaky(int):
        pass

    for bad in (True, Sneaky(errno.ENOENT)):
        assert (
            Errno.ENOENT not in mounts_module._errno_table({**vars(errno), "ENOENT": bad}).values()
        )
    without = {k: v for k, v in vars(errno).items() if k != "ESTALE"}
    lacking = mounts_module._errno_table(without)
    assert Errno.ESTALE not in lacking.values() and len(lacking) == len(table) - 1

    code = (
        "import errno\n"
        "del errno.ESTALE\n"
        "import wasi_python\n"
        "from wasi_python import mounts\n"
        "print(mounts.Errno.ESTALE in mounts._HOST_ERRNO.values())\n"
    )
    child = subprocess.run(
        [sys.executable, "-I", "-c", code], capture_output=True, text=True, check=False
    )
    assert (child.returncode, child.stdout.strip()) == (0, "False"), child.stderr[-500:]


# Spec 068: a cap on files open at once. The call's table counts the descriptors the guest holds
# (wasmtime's numbers it opened, and its open mount files), and answers EMFILE at the cap before
# wasmtime or the provider is asked. Forwards and provider calls are counted, nothing is timed.

EMFILE = 33  # ENOENT (44) is bound above


def _forwards(table) -> list[str]:
    """Each call the table forwards to wasmtime, by name, from now on."""
    seen: list[str] = []
    real = table.forward

    def forward(caller, name, args, stat=False):
        seen.append(name)
        return real(caller, name, args, stat)

    table.forward = forward
    return seen


def _folder(tmp_path: Path) -> Path:
    folder = tmp_path / "w"
    (folder / "sub").mkdir(parents=True)
    for i in range(5):
        (folder / f"f{i}").write_bytes(b"x")
    return folder


def test_open_files_are_counted_on_a_call_without_mounts(tmp_path) -> None:
    """Spec 068, criterion 1: under a cap of 3, exactly three opens succeed and the fourth is
    EMFILE without reaching wasmtime; a close frees one slot; a failed open holds nothing;
    closing what the guest did not open frees nothing; fd_renumber moves and frees as wasmtime
    does, a number onto itself included; with no cap, nothing is refused; and below the cap the
    three counted calls answer as plain wasmtime does."""
    folder = _folder(tmp_path)
    g = files.Guarded([(folder, "/w", False)])
    g.table.open_files = 3
    forwarded = _forwards(g.table)
    r = g.raw
    opened = [r.open(3, "f0"), r.open(3, "f1"), r.open(3, "sub", files.O_DIRECTORY)]
    assert [e for e, _ in opened] == [0, 0, 0], opened
    a, b, c = (n for _, n in opened)
    assert len({a, b, c}) == 3
    assert r.open(3, "f2") == (EMFILE, None)
    assert forwarded.count("path_open") == 3
    assert r.open(3, "missing") == (EMFILE, None)  # at the cap, before the path is walked
    assert forwarded.count("path_open") == 3
    assert r("fd_close", a) == 0
    a = r.open(3, "f2")[1]
    assert a is not None and r.open(3, "f3")[0] == EMFILE
    assert r("fd_close", b) == 0
    assert r.open(3, "missing")[0] == ENOENT  # forwarded, and holds nothing
    b = r.open(3, "f3")[1]
    assert b is not None
    assert r("fd_close", 2**20) == EBADF
    assert r.open(3, "f4")[0] == EMFILE
    assert r("fd_close", 0) == 0  # stdin: not the guest's to count
    assert r.open(3, "f4")[0] == EMFILE
    assert r("fd_renumber", a, b) == 0  # b closed, a moved there: one slot free
    a = r.open(3, "f0")[1]
    assert a is not None and r.open(3, "f1")[0] == EMFILE
    assert r("fd_renumber", a, 1) == 0  # a held number onto stdout: still held, as 1
    assert r.open(3, "f1")[0] == EMFILE
    assert r("fd_close", 1) == 0
    a = r.open(3, "f1")[1]
    assert a is not None
    # (t) a held number onto itself: wasmtime keeps it, and so does the count.
    assert r("fd_renumber", a, a) == 0
    assert r.open(3, "f2")[0] == EMFILE
    # (u) stderr onto a held number: that number is closed, and its slot freed.
    assert r("fd_renumber", 2, a) == 0
    assert r.open(3, "f2")[0] == 0
    assert r.open(3, "f3")[0] == EMFILE

    free = files.Guarded([(folder, "/w", False)])
    free.table.open_files = None
    assert {free.raw.open(3, f"f{i % 5}")[0] for i in range(50)} == {0}

    def rows(r) -> list[object]:
        out: list[object] = []
        a, b = r.open(3, "f0"), r.open(3, "f1")
        out += [a, b, r.open(3, "sub", files.O_DIRECTORY), r.open(3, "missing")]
        out += [_answer(r.open, 99, "f0"), _answer(r.open, 3, "f2", 0x10)]
        out += [r("fd_renumber", a[1], a[1]), r("fd_renumber", a[1], b[1])]
        out += [r("fd_renumber", 2**31 - 1, 2**31 - 1)]
        out += [r("fd_close", b[1]), r("fd_close", 2**20), r("fd_close", 0), r.open(3, "f3")]
        return out

    plain = rows(files.grant_raw([(folder, "/w", False)]))
    guarded = rows(files.Guarded([(folder, "/w", False)]).raw)
    assert guarded == plain


def test_mount_files_count_toward_the_open_file_cap(placeholder, tmp_path) -> None:
    """Spec 068, criterion 2: mount files count with wasmtime's under one cap; a refused open in
    a mount makes no provider call and spends no file call; a close of either kind frees a slot
    for either kind; a renumber of two held grant numbers frees one, with mounts as without."""
    folder = _folder(tmp_path)
    provider = MemoryProvider()
    m = Mounted(provider, placeholder, folders=[(folder, "/w", False)])
    m.table.open_files = 4
    forwarded = _forwards(m.table)
    r = m.raw
    mount = [r.open(3, "a.txt")[1], r.open(3, "b.txt")[1]]
    grant = [r.open(4, "f0")[1], r.open(4, "f1")[1]]
    assert None not in mount + grant
    assert forwarded.count("path_open") == 2
    assert r.open(4, "f2") == (EMFILE, None)
    assert forwarded.count("path_open") == 2
    assert r.open(3, "a.txt") == (EMFILE, None)
    assert m.table.record().calls["read"] == 2
    assert r("fd_close", mount[0]) == 0
    assert r.open(4, "f2")[0] == 0
    assert r("fd_close", grant[0]) == 0
    assert r.open(3, "a.txt")[0] == 0
    assert r.open(3, "b.txt")[0] == EMFILE and r.open(4, "f3")[0] == EMFILE
    # The build review's F1: in a table with mounts, a renumber of two held grant numbers closes
    # one and frees its slot, as in a guard table.
    held = sorted(m.table.held)
    assert len(held) == 2 and r("fd_renumber", held[0], held[1]) == 0
    assert r.open(4, "f3")[0] == 0
    assert r.open(4, "f4")[0] == EMFILE

    m = Mounted(provider, placeholder, file_calls=3)
    m.table.open_files = 2
    r = m.raw
    assert [r.open(3, "a.txt")[0] for _ in range(4)] == [0, 0, EMFILE, EMFILE]
    assert m.table.total == 2 and m.call.ended is None
