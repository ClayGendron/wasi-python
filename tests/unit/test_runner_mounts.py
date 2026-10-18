"""Read-only mounts (spec 032): the runner's own boundary code, which does not depend on the host,
so these run on the judge's machine only. Raw preview1 calls through the mount linker, with the
call on the thread's stack (harness/files.py); fuel and provider calls are counted, nothing is
timed."""

from __future__ import annotations

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
    """A call without mounts uses today's linker object and never reaches a shadow; a call with
    one uses the mount linker. Concurrent calls with and without mounts on two threads each get
    their own results, and each provider sees only its own call's paths (spec 011's pattern)."""
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
    assert used == [runner._linker(wt, engine)] and served == []
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
