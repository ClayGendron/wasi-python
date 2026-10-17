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
