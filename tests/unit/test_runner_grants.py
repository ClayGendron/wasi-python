"""Typed grants (spec 017): the identity check against wasmtime's own numbers, the argument rules,
the rules between grants, and the raw WASI calls a read-only grant refuses. Nothing here needs
the artifact set, so the `verify` job runs this file on Linux, macOS and Windows; nothing here
measures time."""

from __future__ import annotations

import os
import struct
import tempfile
from pathlib import Path

import pytest
import wasmtime as wt

from harness import files
from wasi_python import Grant, runner

POSIX = os.name == "posix"


def _store(folders: list[tuple[str, str]]) -> tuple[wt.Store, wt.Linker, wt.Engine]:
    engine = wt.Engine()
    store = wt.Store(engine)
    config = wt.WasiConfig()
    for host, guest in folders:
        config.preopen_dir(host, guest, False)
    store.set_wasi(config)
    linker = wt.Linker(engine)
    linker.define_wasi()
    return store, linker, engine


def _folders(tmp_path: Path) -> list[Path]:
    """A scratch folder and, on Windows, one under the real temporary folder, whose path the
    runners spell with an 8.3 short name: neither may be refused."""
    folders = [tmp_path / "a"]
    folders[0].mkdir()
    if not POSIX:
        folders.append(Path(tempfile.mkdtemp()))
    return folders


def test_the_grant_identity_matches_wasmtimes(tmp_path) -> None:
    """Decision 5's formula, pinned: a wasmtime that hashes a folder's identity otherwise, or a
    platform the formula misses, fails here first (and at run time refuses every grant)."""
    folders = _folders(tmp_path)
    walked = [runner._walk("t", str(f), judge=True) for f in folders]
    stores: list[wt.Store] = []
    try:
        store, linker, engine = _store([(w.path, f"/g{i}") for i, w in enumerate(walked)])
        stores.append(store)
        exports = linker.instantiate(store, wt.Module(engine, runner._CHECK_WAT)).exports(store)
        memory = exports["memory"]
        for i, w in enumerate(walked):
            assert exports["stat"](store, 3 + i) == 0
            reported = struct.unpack("<Q", bytes(memory.read(store, 72, 80)))[0]
            assert w.identity is not None and reported == runner._wasi_ino(w.identity)
        preopens = [runner._Preopen(f"g{i}", w, f"/g{i}", False) for i, w in enumerate(walked)]
        runner._check_preopens(wt, linker, store, wt.Module(engine, runner._CHECK_WAT), preopens)
        assert all(w.held == [] for w in walked)  # released after the check
    finally:
        for w in walked:
            w.close()
        for store in stores:  # Windows cannot remove a folder a store still holds open
            store.close()
        for f in folders[1:]:
            f.rmdir()


def test_a_preopen_that_is_not_the_walked_folder_is_refused(tmp_path) -> None:
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    walked = runner._walk("t", str(a), judge=True)
    store, linker, engine = _store([(str(b), "/g")])  # wasmtime opened another folder
    check = wt.Module(engine, runner._CHECK_WAT)
    with pytest.raises(RuntimeError, match="changed between its check and the call"):
        runner._check_preopens(
            wt, linker, store, check, [runner._Preopen("grant 0", walked, "/g", False)]
        )
    for name in ("/other", "/h"):  # another name, of another length and of the same length
        other = runner._walk("t", str(b), judge=True)
        store, linker, engine = _store([(str(b), name)])
        check = wt.Module(engine, runner._CHECK_WAT)
        with pytest.raises(RuntimeError):
            runner._check_preopens(
                wt, linker, store, check, [runner._Preopen("grant 0", other, "/g", False)]
            )
    other = runner._walk("t", str(b), judge=True)
    store, linker, engine = _store([(str(b), "/other")])  # the right folder at another name
    check = wt.Module(engine, runner._CHECK_WAT)
    with pytest.raises(RuntimeError):
        runner._check_preopens(
            wt, linker, store, check, [runner._Preopen("grant 0", other, "/g", False)]
        )


@pytest.mark.parametrize(
    ("guest", "error"),
    [
        ("data", "must be absolute"),
        ("/", "pass root= instead"),
        ("/data/", "ends in '/'"),
        ("/a//b", "empty"),
        ("/a/./b", "'.'"),
        ("/a/../b", "'..'"),
        ("/usr/local/lib", "the runtime's own"),
        ("/usr/local/lib/python3.15", "the runtime's own"),
        ("/a\0b", "null byte"),
    ],
)
def test_a_bad_guest_path_is_refused(tmp_path, guest, error) -> None:
    with pytest.raises(ValueError, match=error):
        runner._check_grants([Grant(tmp_path, guest)])


def test_the_argument_types(tmp_path) -> None:
    with pytest.raises(TypeError, match="writable must be True or False"):
        runner._check_grants([Grant(tmp_path, "/d", writable="no")])  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="not bytes"):
        runner._check_grants([Grant(bytes(tmp_path), "/d")])  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="must be a Grant"):
        runner._check_grants([(str(tmp_path), "/d")])
    for not_iterable in ("/d", b"/d", Grant(tmp_path, "/d"), 3):
        with pytest.raises(TypeError, match="iterable of Grant"):
            runner._check_grants(not_iterable)
    # spec 025: True asks for a private root (kept as None), None and False mean none
    assert (runner._check_root(True), runner._check_root(None)) == (None, False)
    with pytest.raises(TypeError, match="not bytes"):
        runner._check_root(bytes(tmp_path))
    with pytest.raises(ValueError, match="same guest path"):
        runner._check_grants([Grant(tmp_path, "/d"), Grant(tmp_path, "/d", writable=True)])
    once = runner._check_grants(iter([Grant(tmp_path, "/d"), Grant(tmp_path, "/d/out")]))
    assert once == (Grant(str(tmp_path), "/d"), Grant(str(tmp_path), "/d/out"))  # a tuple of str
    assert runner._check_root(False) is False


def _w(*chain: tuple[int, int], missing: bool = False) -> runner._Walked:
    w = runner._Walked("/x", tuple(chain), [])
    if missing:
        w.missing = ("new",)
    return w


TOP, HOME, CACHE, PROJ, DATA, OUT = ((1, i) for i in range(6))


def test_the_rules_compare_identities() -> None:
    """Decision 4 on made-up chains (the folder first): home holds the cache and a project; the
    project holds data and out."""
    home, proj = _w(HOME, TOP), _w(PROJ, HOME, TOP)
    data, out = _w(DATA, PROJ, HOME, TOP), _w(OUT, PROJ, HOME, TOP)
    cache = ("the module cache", CACHE, (CACHE, HOME, TOP))
    ro, rw = Grant("h", "/g"), Grant("h", "/g", writable=True)
    with pytest.raises(ValueError, match="holds the module cache"):
        runner._judge(home, [], [cache])  # root above the cache
    with pytest.raises(ValueError, match="is inside the module cache"):
        runner._judge(None, [("g", rw, _w((9, 9), CACHE, HOME, TOP))], [cache])
    with pytest.raises(ValueError, match="read-only but inside root"):
        runner._judge(proj, [("g", ro, data)], [cache])
    with pytest.raises(ValueError, match="read-only but inside g2"):
        runner._judge(None, [("g", ro, proj), ("g2", rw, proj)], [cache])  # the same folder
    runner._judge(None, [("g", ro, proj), ("g2", rw, out)], [cache])  # writable inside read-only
    runner._judge(proj, [], [cache])
    # A cache not made yet: only a grant above its deepest existing ancestor is refused.
    not_yet = ("the module cache", None, (HOME, TOP))
    runner._judge(proj, [], [not_yet])
    with pytest.raises(ValueError, match="holds the module cache"):
        runner._judge(home, [], [not_yet])
    # A root still to be made is above nothing, but inside whatever its ancestor is inside.
    runner._judge(_w(HOME, TOP, missing=True), [], [cache])
    with pytest.raises(ValueError, match="is inside the module cache"):
        runner._judge(_w(CACHE, HOME, TOP, missing=True), [], [cache])


@pytest.mark.skipif(not POSIX, reason="making a link needs privileges on Windows")
def test_the_walk_judges_links(tmp_path) -> None:
    """A link in a folder this user can write is refused, a link in one it cannot is followed
    (memo §7a), and a missing root's tail is returned for making."""
    target = tmp_path / "target"
    target.mkdir()
    (tmp_path / "link").symlink_to(target)
    with pytest.raises(ValueError, match="passes through the link 'link'"):
        runner._walk("g", str(tmp_path / "link" / "."), judge=True)
    followed = runner._walk("g", str(tmp_path / "link"), judge=False)
    try:
        assert followed.identity == runner._identity_of(target)
    finally:
        followed.close()
    sealed = tmp_path / "sealed"
    sealed.mkdir()
    (sealed / "link").symlink_to(target)
    sealed.chmod(0o555)
    try:
        walked = runner._walk("g", str(sealed / "link"), judge=True)
        assert walked.identity == runner._identity_of(target)
        walked.close()
    finally:
        sealed.chmod(0o755)
    missing = runner._walk("root", str(tmp_path / "new" / "deeper"), judge=True, may_make=True)
    try:
        assert missing.missing == ("new", "deeper") and missing.identity is None
        assert missing.chain[0] == runner._identity_of(tmp_path)
    finally:
        missing.close()
    with pytest.raises(ValueError, match="does not exist"):
        runner._walk("g", str(tmp_path / "nothing"), judge=True)
    (tmp_path / "file").write_text("x")
    with pytest.raises(ValueError, match="is not a folder"):
        runner._walk("g", str(tmp_path / "file"), judge=True)


RAW = r"""(module
  (import "wasi_snapshot_preview1" "path_open"
    (func $po (param i32 i32 i32 i32 i32 i64 i64 i32 i32) (result i32)))
  (import "wasi_snapshot_preview1" "fd_allocate" (func $fa (param i32 i64 i64) (result i32)))
  (import "wasi_snapshot_preview1" "fd_renumber" (func $fr (param i32 i32) (result i32)))
  (import "wasi_snapshot_preview1" "fd_write" (func $fw (param i32 i32 i32 i32) (result i32)))
  (memory (export "memory") 1)
  (data (i32.const 200) "\2c\01\00\00\02\00\00\00")
  (data (i32.const 300) "XX")
  (func (export "open") (param i32 i32 i32 i32 i64 i32) (result i32)
    (call $po (local.get 0) (i32.const 0) (local.get 1) (local.get 2) (local.get 3)
      (local.get 4) (local.get 4) (local.get 5) (i32.const 0)))
  (func (export "allocate") (param i32) (result i32)
    (call $fa (local.get 0) (i64.const 0) (i64.const 10)))
  (func (export "renumber") (param i32 i32) (result i32) (call $fr (local.get 0) (local.get 1)))
  (func (export "write") (param i32) (result i32)
    (call $fw (local.get 0) (i32.const 200) (i32.const 1) (i32.const 208))))"""
EPERM, ENOTSUP = 63, 58
READ, WRITE, ALL = 1 << 1, 1 << 6, (1 << 29) - 1
TRUNC = 8


def test_a_read_only_grant_refuses_raw_writes(tmp_path) -> None:
    """The raw preview1 rows of memo §1 and the review's extras, on a preopen made as the runner
    makes a read-only grant (`fs_mutable=False`); fd 4 is a writable control."""
    ro, rw = tmp_path / "ro", tmp_path / "rw"
    ro.mkdir()
    rw.mkdir()
    (ro / "f.txt").write_text("original")
    (rw / "w.txt").write_text("")
    engine = wt.Engine()
    store = wt.Store(engine)
    config = wt.WasiConfig()
    config.preopen_dir(str(ro), "/ro", False)
    config.preopen_dir(str(rw), "/rw", True)
    store.set_wasi(config)
    linker = wt.Linker(engine)
    linker.define_wasi()
    ex = linker.instantiate(store, wt.Module(engine, RAW)).exports(store)
    memory = ex["memory"]

    def open_(fd: int, name: str, oflags: int, rights: int) -> tuple[int, int]:
        memory.write(store, name.encode(), 100)
        errno = ex["open"](store, fd, 100, len(name.encode()), oflags, rights, 0)
        return errno, struct.unpack("<I", bytes(memory.read(store, 0, 4)))[0]

    assert open_(3, "f.txt", 0, ALL)[0] == EPERM
    assert open_(3, "f.txt", TRUNC, READ)[0] == EPERM
    assert open_(3, "new.txt", 1, READ)[0] == EPERM  # O_CREAT
    errno, ro_fd = open_(3, "f.txt", 0, READ)
    assert errno == 0
    assert ex["allocate"](store, ro_fd) == ENOTSUP
    errno, rw_fd = open_(4, "w.txt", 0, READ | WRITE)
    assert errno == 0
    # fd_renumber onto the grant's file only moves the writable descriptor to that number.
    assert ex["renumber"](store, rw_fd, ro_fd) == 0
    assert ex["write"](store, ro_fd) == 0
    assert (ro / "f.txt").read_text() == "original" and (rw / "w.txt").read_text() == "XX"
    assert sorted(p.name for p in ro.iterdir()) == ["f.txt"]


@pytest.mark.skipif(not POSIX, reason="POSIX permission bits")
def test_a_folder_one_may_search_but_not_list_is_walked(tmp_path) -> None:
    """wasmtime opens a grant below such a folder, so the walk passes through it too (the build
    review, finding 6); a folder one may not even search is refused with ValueError."""
    (tmp_path / "noread" / "child").mkdir(parents=True)
    (tmp_path / "noread").chmod(0o311)
    try:
        walked = runner._walk("g", str(tmp_path / "noread" / "child"), judge=True)
        walked.close()
        (tmp_path / "noread").chmod(0o000)
        if os.access(tmp_path / "noread", os.X_OK):  # run as root: no permission refuses it
            return
        with pytest.raises(ValueError, match="cannot be walked"):
            runner._walk("g", str(tmp_path / "noread" / "child"), judge=True)
    finally:
        (tmp_path / "noread").chmod(0o755)


@pytest.mark.skipif(POSIX, reason="junctions are Windows'")
def test_a_junction_is_refused_on_windows(tmp_path) -> None:
    """Windows' link rule: every reparse point on the way is refused (the build review, finding
    5); a junction needs no privilege to make."""
    import _winapi

    target = tmp_path / "target"
    target.mkdir()
    _winapi.CreateJunction(str(target), str(tmp_path / "junction"))
    with pytest.raises(ValueError, match="link or junction"):
        runner._walk("g", str(tmp_path / "junction"), judge=True)
    with pytest.raises(ValueError, match="link or junction"):
        runner._walk("g", str(tmp_path / "junction" / "."), judge=True)


@pytest.mark.skipif(POSIX, reason="Windows holds every walked folder")
def test_a_walked_folder_cannot_be_moved_on_windows(tmp_path) -> None:
    """Decision 5: while the walk holds its handles, no folder on the way can be renamed, so no
    swap can happen before the identity check."""
    (tmp_path / "a" / "b").mkdir(parents=True)
    walked = runner._walk("g", str(tmp_path / "a" / "b"), judge=True)
    try:
        for old, new in ((tmp_path / "a", tmp_path / "c"), (tmp_path / "a" / "b", tmp_path / "d")):
            with pytest.raises(PermissionError):
                os.rename(old, new)
    finally:
        walked.close()
    os.rename(tmp_path / "a", tmp_path / "c")  # released: it moves again


# Spec 032, acceptance 3: the raw parity table. The same rows run on a read-only grant (plain
# wasmtime) and on a mount of the same tree (the runner's mount linker, its call on the stack);
# preopen 3 is the tree on each side and preopen 4 a writable folder. Every result is compared
# whole (the errno and every byte written), with dev, ino, times, descriptor numbers and a
# folder's size and link count left out by the harness. Decision 6's deliberate differences are
# asserted as that table says, in the test after this one.

# Rows whose grant answer is the host system's own error, not wasmtime's logic: asserted on
# POSIX hosts only (the landing notes name them); on Windows the mount's answer is still the
# reference's (wasmtime on Linux).
HOST_ROWS = {
    "file fd_advise",
    "file fd_write",
    "file fd_pwrite",
    "file fd_datasync",
    "file fd_sync",
    "open 'a.txt\\x00'",
    "open 'a.txt/'",
    "open 'a.txt/.'",
    "open 'x' * 256",
    "pstat 'a.txt/'",
    "pstat 'a.txt/.'",
    "pstat 'a.txt/x'",
    "pstat 'a\\x00'",
    "pstat 'x' * 256",
    "readlink 'a.txt'",
    "readlink 'd'",
    "readlink 'a.txt/'",
}


def _parity_script(r: files.Raw) -> dict[str, object]:
    """Every row on one side. The descriptors a row opens are named, never numbered."""
    out: dict[str, object] = {}

    def row(label: str, fn, *args) -> None:
        try:
            out[label] = fn(*args)
        except files.Ends as e:
            out[label] = ("ends", e.message)

    def opened(label: str, *args, **kw) -> int | None:
        try:
            errno, fd = r.open(*args, **kw)
        except files.Ends as e:
            out[label] = ("ends", e.message)
            return None
        out[label] = (errno, fd is not None)
        if fd is not None and label.startswith("open "):
            r("fd_close", fd)
        return fd

    P, W = 3, 4
    F = opened("the file F", P, "a.txt")
    D = opened("the folder D", P, "d", files.O_DIRECTORY)
    E = opened("the folder E (no O_DIRECTORY)", P, "e")
    assert F is not None and D is not None and E is not None, out
    for kind, T in (("file", F), ("dir", D), ("plain dir", E), ("preopen", P)):
        row(f"{kind} fd_advise", r, "fd_advise", T, 0, 0, 0)
        row(f"{kind} fd_advise 6", r, "fd_advise", T, 0, 0, 6)
        row(f"{kind} fd_advise -1", r, "fd_advise", T, 0, 0, -1)
        row(f"{kind} fd_allocate", r, "fd_allocate", T, 0, 10)
        row(f"{kind} fd_datasync", r, "fd_datasync", T)
        row(f"{kind} fd_sync", r, "fd_sync", T)
        row(f"{kind} fd_fdstat_get", r.fdstat, T)
        for flags in (0, files.APPEND, files.DSYNC, files.NONBLOCK, files.RSYNC, files.SYNC):
            row(f"{kind} set_flags {flags}", r, "fd_fdstat_set_flags", T, flags)
        row(f"{kind} set_flags unknown bit", r, "fd_fdstat_set_flags", T, 32)
        row(f"{kind} set_flags out of range", r, "fd_fdstat_set_flags", T, 1 << 16)
        row(f"{kind} fdstat after flags", r.fdstat, T)
        row(f"{kind} set_flags back", r, "fd_fdstat_set_flags", T, 0)
        row(f"{kind} set_rights", r, "fd_fdstat_set_rights", T, 0, 0)
        row(f"{kind} set_rights unknown bit", r, "fd_fdstat_set_rights", T, 1 << 30, 0)
        row(f"{kind} fd_filestat_get", r.filestat, T)
        row(f"{kind} set_size", r, "fd_filestat_set_size", T, 0)
        for flags in (0, 1, 2, 3, 12):
            row(f"{kind} set_times {flags}", r, "fd_filestat_set_times", T, 0, 0, flags)
        row(f"{kind} set_times unknown bit", r, "fd_filestat_set_times", T, 0, 0, 16)
        row(f"{kind} fd_write", r.write, T, b"zz")
        row(f"{kind} fd_pwrite", r.write, T, b"zz", 0)
        row(f"{kind} fd_tell", r.tell, T)
        row(f"{kind} fd_seek", r.seek, T, 0, 0)
        row(f"{kind} fd_read", r.read, T, [3])
        row(f"{kind} fd_pread", r.pread, T, [3], 1)
        if kind != "preopen":  # the preopen's listing order is the host's: compared by name
            row(f"{kind} fd_readdir", r.readdir, T)
    row("preopen fd_readdir names", r.readdir_names, P)
    # Seeks and reads on the file, in order: whence 3, an overflow, past the end, past i64.
    for offset, whence in [
        (0, 0), (3, 0), (1, 1), (-100, 1), (0, 2), (-1, 2), (5, 3), (-1, 0), (5, 256), (5, -1),
    ]:  # fmt: skip
        row(f"seek {offset} {whence}", r.seek, F, offset, whence)
    row("seek to 0", r.seek, F, 0, 0)
    row("read 3", r.read, F, [3])
    row("read two iovecs, the first empty", r.read, F, [0, 3, 3])
    row("read no iovec", r.read, F, [])
    row("read one empty iovec", r.read, F, [0])
    row("read the rest", r.read, F, [100])
    row("read at the end", r.read, F, [10])
    row("pread past the end", r.pread, F, [4], 1000)
    row("pread at 2**63 - 1", r.pread, F, [4], 2**63 - 1)
    row("pread at 2**64 - 1", r.pread, F, [4], -1)
    row("seek past then read", lambda: (r.seek(F, 100, 0), r.read(F, [4]), r.tell(F)))
    row("seek from the end", lambda: (r.seek(F, -2, 2), r.read(F, [4])))
    row("seek to 2**63 - 1", r.seek, F, 2**63 - 1, 0)
    row("read at 2**63 - 1", r.read, F, [4])
    row("seek to 2**63", r.seek, F, 1, 1)
    row("read at 2**63", r.read, F, [4])
    row("seek to 2**64 - 1", r.seek, F, 2**63 - 2, 1)
    row("seek past 2**64 - 1", r.seek, F, 1, 1)
    row("tell after it", r.tell, F)
    row("seek back", r.seek, F, 0, 0)
    # fd_readdir on the one-entry folder: cookies and short buffers, byte for byte.
    for size, cookie in [(4096, 0), (4096, 1), (4096, 2), (4096, 3), (4096, 10), (10, 0),
                         (24, 0), (25, 0), (30, 0), (50, 0), (0, 0), (4096, -1)]:  # fmt: skip
        row(f"readdir {size} {cookie}", r.readdir, D, size, cookie)
    # path_open from the preopen and from the folder.
    R, ALL = files.READ_RIGHTS, files.RIGHTS_ALL
    for label, base, path, oflags, rights, fdflags, dirflags in [
        ("'a.txt'", P, "a.txt", 0, R, 0, 0),
        ("''", P, "", 0, R, 0, 0),
        ("'/a.txt'", P, "/a.txt", 0, R, 0, 0),
        ("'a.txt\\x00'", P, b"a.txt\0", 0, R, 0, 0),
        ("'\\xff'", P, b"\xff", 0, R, 0, 0),
        ("'a.txt/'", P, "a.txt/", 0, R, 0, 0),
        ("'a.txt/.'", P, "a.txt/.", 0, R, 0, 0),
        ("'d/../a.txt'", P, "d/../a.txt", 0, R, 0, 0),
        ("'..'", P, "..", 0, R, 0, 0),
        ("'d/../../m/a.txt'", P, "d/../../m/a.txt", 0, R, 0, 0),
        ("'x' * 256", P, "x" * 256, 0, R, 0, 0),
        ("'x' * 255", P, "x" * 255, 0, R, 0, 0),
        ("'.'", P, ".", 0, R, 0, 0),
        ("'./a.txt'", P, "./a.txt", 0, R, 0, 0),
        ("'d/'", P, "d/", 0, R, 0, 0),
        ("'d/.'", P, "d/.", 0, R, 0, 0),
        ("'d//x.txt'", P, "d//x.txt", 0, R, 0, 0),
        ("'missing'", P, "missing", 0, R, 0, 0),
        ("O_DIRECTORY on a file", P, "a.txt", files.O_DIRECTORY, R, 0, 0),
        ("O_DIRECTORY on nothing", P, "missing", files.O_DIRECTORY, R, 0, 0),
        ("O_DIRECTORY on a folder", P, "d", files.O_DIRECTORY, R, 0, 0),
        ("for writing", P, "a.txt", 0, ALL, 0, 0),
        ("a folder for writing", P, "d", 0, ALL, 0, 0),
        ("truncating", P, "a.txt", files.O_TRUNC, R, 0, 0),
        ("creating", P, "new", files.O_CREAT, R, 0, 0),
        ("creating exclusively", P, "a.txt", files.O_CREAT | files.O_EXCL, R, 0, 0),
        ("exclusive alone", P, "a.txt", files.O_EXCL, R, 0, 0),
        ("creating under nothing", P, "missing/new", files.O_CREAT, R, 0, 0),
        ("O_DIRECTORY and O_CREAT", P, "d", files.O_DIRECTORY | files.O_CREAT, R, 0, 0),
        ("appending (read-only)", P, "a.txt", 0, R, files.APPEND, 0),
        ("non-blocking", P, "a.txt", 0, R, files.NONBLOCK, 0),
        ("SYNC", P, "a.txt", 0, R, files.SYNC, 0),
        ("DSYNC", P, "a.txt", 0, R, files.DSYNC, 0),
        ("no rights", P, "a.txt", 0, 0, 0, 0),
        ("the top right", P, "a.txt", 0, 1 << 29, 0, 0),
        ("following links", P, "a.txt", 0, R, 0, 1),
        ("unknown oflags", P, "a.txt", 16, R, 0, 0),
        ("oflags out of range", P, "a.txt", 1 << 16, R, 0, 0),
        ("unknown rights", P, "a.txt", 0, 1 << 30, 0, 0),
        ("unknown fdflags", P, "a.txt", 0, R, 32, 0),
        ("unknown lookup flags", P, "a.txt", 0, R, 0, 2),
        ("lookup flags out of range", P, "a.txt", 0, R, 0, -1),
        ("from the folder", D, "x.txt", 0, R, 0, 0),
        ("from the folder, '..'", D, "..", 0, R, 0, 0),
        ("from the folder, '../a.txt'", D, "../a.txt", 0, R, 0, 0),
        ("from the folder, '.'", D, ".", 0, R, 0, 0),
        ("from the file", F, "a.txt", 0, R, 0, 0),
        ("from the file, creating", F, "x", files.O_CREAT, R, 0, 0),
        ("from the file, not UTF-8", F, b"\xff", 0, R, 0, 0),
        ("from nothing", 99, "a.txt", 0, R, 0, 0),
    ]:
        opened(f"open {label}", base, path, oflags, rights, fdflags, dirflags)
    for label, base, path in [
        ("'a.txt'", P, "a.txt"), ("'d'", P, "d"), ("'missing'", P, "missing"),
        ("'a.txt/'", P, "a.txt/"), ("'a.txt/.'", P, "a.txt/."), ("''", P, ""),
        ("'/a.txt'", P, "/a.txt"), ("'..'", P, ".."), ("'.'", P, "."), ("'d/..'", P, "d/.."),
        ("'d/../../m'", P, "d/../../m"), ("'\\xff'", P, b"\xff"), ("'a\\x00'", P, b"a\0"),
        ("'x' * 256", P, "x" * 256), ("'d/x.txt'", P, "d/x.txt"), ("'a.txt/x'", P, "a.txt/x"),
        ("from the folder", D, "x.txt"), ("from the file", F, "a.txt"),
    ]:  # fmt: skip
        row(f"pstat {label}", r.path_filestat, base, path)
    row("pstat following links", r.path_filestat, P, "a.txt", 1)
    row("pstat unknown lookup flags", r.path_filestat, P, "a.txt", 2)
    for label, base, path in [
        ("'a.txt'", P, "a.txt"), ("'d'", P, "d"), ("'missing'", P, "missing"), ("''", P, ""),
        ("'/a.txt'", P, "/a.txt"), ("'..'", P, ".."), ("'a.txt/'", P, "a.txt/"),
        ("from the file", F, "a.txt"),
    ]:  # fmt: skip
        row(f"readlink {label}", r.readlink, base, path)
    # Every write-shaped path call: EPERM on a read-only grant, before any provider call.
    for name in ("path_create_directory", "path_remove_directory", "path_unlink_file"):
        for path in ("new", "d", "a.txt", "", "/x", "..", b"\xff", b"a\0", "missing/x", "e"):
            row(f"{name} {path!r}", r.path_call, name, P, path)
        row(f"{name} from the file", r.path_call, name, F, "x")
        row(f"{name} from the folder", r.path_call, name, D, "x.txt")
    row("rename within", r.rename, P, "a.txt", P, "c.txt")
    row("rename nothing", r.rename, P, "missing", P, "c.txt")
    row("rename from the file", r.rename, F, "a.txt", P, "c.txt")
    row("rename to the file", r.rename, P, "a.txt", F, "c.txt")
    row("rename to nothing", r.rename, P, "a.txt", 99, "c.txt")
    row("rename to a writable grant", r.rename, P, "a.txt", W, "c.txt")
    row("rename from a writable grant", r.rename, W, "w.txt", P, "c.txt")
    row("rename not UTF-8", r.rename, P, "a.txt", P, "\udcff".encode("utf-8", "surrogatepass"))
    row("link within", r.link, P, "a.txt", P, "c.txt")
    row("link following links", r.link, P, "a.txt", P, "c.txt", 1)
    row("link unknown flags", r.link, P, "a.txt", P, "c.txt", 2)
    row("link to nothing", r.link, P, "a.txt", 99, "c.txt")
    row("link to a writable grant", r.link, P, "a.txt", W, "c.txt")
    row("link from a writable grant", r.link, W, "w.txt", P, "c.txt")
    row("symlink", r.symlink, "a.txt", P, "l")
    row("symlink from the file", r.symlink, "a.txt", F, "l")
    for flags in (0, 1, 3, 4, 12):
        row(f"path set_times {flags}", r.path_set_times, P, "a.txt", flags)
    row("path set_times unknown bit", r.path_set_times, P, "a.txt", 16)
    row("path set_times from the file", r.path_set_times, F, "a.txt", 0)
    row("path set_times unknown lookup flags", r.path_set_times, P, "a.txt", 0, 2)
    # The forward-safe calls on a mount's preopen: wasmtime's answers, as for a grant's.
    row("prestat of the preopen", r.prestat, P)
    row(
        "prestat name of the preopen",
        lambda: (r("fd_prestat_dir_name", P, files.BUFFER, 2), r.get(files.BUFFER, 2)),
    )
    row("sock_shutdown on the preopen", r, "sock_shutdown", P, 3)
    # Closing: the file twice, the folders, then the preopen itself.
    row("close the file", r, "fd_close", F)
    row("close the file again", r, "fd_close", F)
    row("fstat after close", r.filestat, F)
    row("close the folder", r, "fd_close", D)
    row("close the plain folder", r, "fd_close", E)
    row("close the preopen", r, "fd_close", P)
    row("open from the closed preopen", r.open, P, "a.txt")
    row("prestat of the closed preopen", r, "fd_prestat_get", P, files.RESULT)
    return out


def _two_sides(tmp_path: Path) -> tuple[files.Raw, files.Mounted]:
    tree = files.write_tree(tmp_path / "tree")
    placeholder = tmp_path / "placeholder"
    placeholder.mkdir()
    sides = []
    for name in ("w-grant", "w-mount"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "w.txt").write_bytes(b"w\n")
        sides.append(tmp_path / name)
    grant = files.grant_raw([(tree, "/m", False), (sides[0], "/w", True)])
    mount = files.Mounted(files.MemoryProvider(), placeholder, folders=[(sides[1], "/w", True)])
    return grant, mount


def test_raw_calls_answer_as_a_grant_does(tmp_path) -> None:
    """Spec 032, acceptance 3: each of the 29 shadowed calls on a provider file, folder and
    preopen answers as on a read-only grant's (errno and every byte written), but for Decision
    6's deliberate differences, asserted in the next test."""
    grant, mount = _two_sides(tmp_path)
    want, got = _parity_script(grant), _parity_script(mount.raw)
    assert list(want) == list(got)
    differ = {
        label: (want[label], got[label])
        for label in want
        if want[label] != got[label] and (POSIX or label not in HOST_ROWS)
    }
    assert differ == {}, differ
    assert sorted(p.name for p in (tmp_path / "w-mount").iterdir()) == ["w.txt"]
    assert sorted(p.name for p in (tmp_path / "tree").iterdir()) == ["a.txt", "b.txt", "d", "e"]


def test_the_deliberate_differences_are_as_decided(tmp_path) -> None:
    """Spec 032, Decision 6's table: where a mount answers otherwise than a read-only grant,
    each answer is the one the table decides (and the grant's is asserted where it does not
    depend on the host)."""
    grant, mount = _two_sides(tmp_path)
    g, m = grant, mount.raw

    def both(fn) -> tuple[object, object]:
        out = []
        for side in (g, m):
            try:
                out.append(fn(side))
            except files.Ends as e:
                out.append(("ends", e.message))
        return out[0], out[1]

    # `..` resolved by text: one provider call on one normalized path.
    assert both(lambda r: r.open(3, "missing/../a.txt")[0]) == (44, 0)
    assert both(lambda r: r.open(3, "a.txt/../b.txt")[0]) == (54, 0)
    # A path over 4,096 bytes: ENAMETOOLONG, unread (a grant's answer is the host's).
    assert m.open(3, "a/" * 2048 + "b")[0] == 37
    assert m.path_filestat(3, "x" * 4097)[0] == 37
    # A guest pointer past memory: EFAULT, where wasmtime ends the run.
    end = files.MEMORY_END
    assert both(lambda r: r("path_open", 3, 0, end - 2, 4, 0, files.READ_RIGHTS, 0, 0, 0)) == (
        ("ends", "Pointer out of bounds"),
        21,
    )
    gf, mf = g.open(3, "a.txt")[1], m.open(3, "a.txt")[1]
    assert gf is not None and mf is not None
    assert (gf < 2**30, mf >= 2**30) == (True, True)  # the high range (Decision 1)
    for side in (g, m):
        side.iovecs([1] * 1025)
    # More than 1,024 iovecs: EINVAL (bounded work), where wasmtime reads one byte.
    assert (g("fd_read", gf, files.IOVECS, 1025, files.RESULT), g.u32(files.RESULT)) == (0, 1)
    assert m("fd_read", mf, files.IOVECS, 1025, files.RESULT) == 28
    # fd_renumber never moves a provider number (Decision 1): ENOTSUP, where a grant succeeds.
    assert (g("fd_renumber", gf, gf), m("fd_renumber", mf, mf)) == (0, 58)
    # The forward-safe calls on a provider number: EBADF, as wasmtime answers an unknown number.
    assert (g("sock_shutdown", gf, 3), m("sock_shutdown", mf, 3)) == (57, 8)
    assert (
        g("fd_prestat_dir_name", gf, files.BUFFER, 8),
        m("fd_prestat_dir_name", mf, files.BUFFER, 8),
    ) == (54, 8)  # noqa: E501
    assert (g("fd_prestat_get", gf, files.RESULT), m("fd_prestat_get", mf, files.RESULT)) == (8, 8)
    # Letter case is the provider's: this one's names are exact.
    assert m.open(3, "A.TXT")[0] == 44
