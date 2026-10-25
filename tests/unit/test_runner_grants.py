"""Typed grants: the identity check against wasmtime's own numbers, the argument rules,
the rules between grants, and the raw WASI calls a read-only grant refuses. Nothing here needs
the artifact set, so the `verify` job runs this file on Linux, macOS and Windows; nothing here
measures time."""

from __future__ import annotations

import os
import struct
import sys
import tempfile
from pathlib import Path

import pytest
import wasmtime as wt

from harness import files
from wasi_python import Grant, _engines, _places, _platform, _platform_windows
from wasi_python._process import process

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
    walked = [_platform.PLATFORM.walk("t", str(f), judge=True) for f in folders]
    stores: list[wt.Store] = []
    try:
        store, linker, engine = _store([(w.path, f"/g{i}") for i, w in enumerate(walked)])
        stores.append(store)
        exports = linker.instantiate(store, wt.Module(engine, _engines._CHECK_WAT)).exports(store)
        memory = exports["memory"]
        for i, w in enumerate(walked):
            assert exports["stat"](store, 3 + i) == 0
            reported = struct.unpack("<Q", bytes(memory.read(store, 72, 80)))[0]
            assert w.identity is not None and reported == _places._wasi_ino(w.identity)
        preopens = [_places._Preopen(f"g{i}", w, f"/g{i}", False) for i, w in enumerate(walked)]
        _places._check_preopens(wt, linker, store, wt.Module(engine, _engines._CHECK_WAT), preopens)
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
    walked = _platform.PLATFORM.walk("t", str(a), judge=True)
    store, linker, engine = _store([(str(b), "/g")])  # wasmtime opened another folder
    check = wt.Module(engine, _engines._CHECK_WAT)
    with pytest.raises(RuntimeError, match="changed between its check and the call"):
        _places._check_preopens(
            wt, linker, store, check, [_places._Preopen("grant 0", walked, "/g", False)]
        )
    for name in ("/other", "/h"):  # another name, of another length and of the same length
        other = _platform.PLATFORM.walk("t", str(b), judge=True)
        store, linker, engine = _store([(str(b), name)])
        check = wt.Module(engine, _engines._CHECK_WAT)
        with pytest.raises(RuntimeError):
            _places._check_preopens(
                wt, linker, store, check, [_places._Preopen("grant 0", other, "/g", False)]
            )
    other = _platform.PLATFORM.walk("t", str(b), judge=True)
    store, linker, engine = _store([(str(b), "/other")])  # the right folder at another name
    check = wt.Module(engine, _engines._CHECK_WAT)
    with pytest.raises(RuntimeError):
        _places._check_preopens(
            wt, linker, store, check, [_places._Preopen("grant 0", other, "/g", False)]
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
        _places._check_grants([Grant(tmp_path, guest)])


def test_the_argument_types(tmp_path) -> None:
    with pytest.raises(TypeError, match="writable must be True or False"):
        _places._check_grants([Grant(tmp_path, "/d", writable="no")])  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="not bytes"):
        _places._check_grants([Grant(bytes(tmp_path), "/d")])  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="must be a Grant"):
        _places._check_grants([(str(tmp_path), "/d")])
    for not_iterable in ("/d", b"/d", Grant(tmp_path, "/d"), 3):
        with pytest.raises(TypeError, match="iterable of Grant"):
            _places._check_grants(not_iterable)
    # True asks for a private root (kept as None), None and False mean none
    assert (_places._check_root(True), _places._check_root(None)) == (None, False)
    with pytest.raises(TypeError, match="not bytes"):
        _places._check_root(bytes(tmp_path))
    with pytest.raises(ValueError, match="same guest path"):
        _places._check_grants([Grant(tmp_path, "/d"), Grant(tmp_path, "/d", writable=True)])
    once = _places._check_grants(iter([Grant(tmp_path, "/d"), Grant(tmp_path, "/d/out")]))
    assert once == (Grant(str(tmp_path), "/d"), Grant(str(tmp_path), "/d/out"))  # a tuple of str
    assert _places._check_root(False) is False


def _w(*chain: tuple[int, int], missing: bool = False) -> _platform._Walked:
    w = _platform._Walked("/x", tuple(chain), [], closer=os.close)
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
        _places._judge(home, [], [cache])  # root above the cache
    with pytest.raises(ValueError, match="is inside the module cache"):
        _places._judge(None, [("g", rw, _w((9, 9), CACHE, HOME, TOP))], [cache])
    with pytest.raises(ValueError, match="read-only but inside root"):
        _places._judge(proj, [("g", ro, data)], [cache])
    with pytest.raises(ValueError, match="read-only but inside g2"):
        _places._judge(None, [("g", ro, proj), ("g2", rw, proj)], [cache])  # the same folder
    _places._judge(None, [("g", ro, proj), ("g2", rw, out)], [cache])  # writable inside read-only
    _places._judge(proj, [], [cache])
    # A cache not made yet: only a grant above its deepest existing ancestor is refused.
    not_yet = ("the module cache", None, (HOME, TOP))
    _places._judge(proj, [], [not_yet])
    with pytest.raises(ValueError, match="holds the module cache"):
        _places._judge(home, [], [not_yet])
    # A root still to be made is above nothing, but inside whatever its ancestor is inside.
    _places._judge(_w(HOME, TOP, missing=True), [], [cache])
    with pytest.raises(ValueError, match="is inside the module cache"):
        _places._judge(_w(CACHE, HOME, TOP, missing=True), [], [cache])


@pytest.mark.skipif(not POSIX, reason="making a link needs privileges on Windows")
def test_the_walk_judges_links(tmp_path) -> None:
    """A link in a folder this user can write is refused, a link in one it cannot is followed,
    and a missing root's tail is returned for making."""
    target = tmp_path / "target"
    target.mkdir()
    (tmp_path / "link").symlink_to(target)
    with pytest.raises(ValueError, match="passes through the link 'link'"):
        _platform.PLATFORM.walk("g", str(tmp_path / "link" / "."), judge=True)
    followed = _platform.PLATFORM.walk("g", str(tmp_path / "link"), judge=False)
    try:
        assert followed.identity == _platform.PLATFORM.identity_of(target)
    finally:
        followed.close()
    sealed = tmp_path / "sealed"
    sealed.mkdir()
    (sealed / "link").symlink_to(target)
    sealed.chmod(0o555)
    try:
        walked = _platform.PLATFORM.walk("g", str(sealed / "link"), judge=True)
        assert walked.identity == _platform.PLATFORM.identity_of(target)
        walked.close()
    finally:
        sealed.chmod(0o755)
    missing = _platform.PLATFORM.walk(
        "root", str(tmp_path / "new" / "deeper"), judge=True, may_make=True
    )
    try:
        assert missing.missing == ("new", "deeper") and missing.identity is None
        assert missing.chain[0] == _platform.PLATFORM.identity_of(tmp_path)
    finally:
        missing.close()
    with pytest.raises(ValueError, match="does not exist"):
        _platform.PLATFORM.walk("g", str(tmp_path / "nothing"), judge=True)
    (tmp_path / "file").write_text("x")
    with pytest.raises(ValueError, match="is not a folder"):
        _platform.PLATFORM.walk("g", str(tmp_path / "file"), judge=True)


def test_the_walk_takes_dot_dot_on_the_real_file_system(tmp_path) -> None:
    """On every system and its real file system (no link, so no skip): a
    `..` is taken on the folders walked. After a missing folder it is refused for a root and a
    grant alike, and nothing is made; after a file it is "is not a folder"; after a real folder
    it is that folder's parent."""
    (tmp_path / "sub").mkdir()
    (tmp_path / "x").mkdir()
    (tmp_path / "a-file").write_text("x")
    for may_make in (True, False):
        with pytest.raises(ValueError, match="does not exist"):
            _platform.PLATFORM.walk(
                "root", str(tmp_path / "new" / ".." / "y"), judge=True, may_make=may_make
            )
    assert sorted(p.name for p in tmp_path.iterdir()) == ["a-file", "sub", "x"]
    with pytest.raises(ValueError, match="is not a folder"):
        _platform.PLATFORM.walk("g", str(tmp_path / "a-file" / ".." / "x"), judge=True)
    walked = _platform.PLATFORM.walk("g", str(tmp_path / "sub" / ".." / "x"), judge=True)
    try:
        assert walked.identity == _platform.PLATFORM.identity_of(tmp_path / "x")
        assert walked.chain[1] == _platform.PLATFORM.identity_of(tmp_path)
    finally:
        walked.close()


# A model of the Win32 path rules the Windows walk meets, as Microsoft's "File path
# formats on Windows systems" states them (READ; the model is INFERRED
# from it): `.` and `..` evaluated by text; a drive-relative `D:x` resolved against drive D's
# current folder; a rooted `\x` against the current drive; a single trailing period trimmed from
# each segment and trailing spaces and periods from the last; a reserved device name in the last
# segment is the device. A verbatim `\\?\` path is taken literally. Identities are `(1, n)`.
# The reserved names are Microsoft's and CPython's `ntpath` together, matched
# upper-cased as CPython matches them, and a segment that holds a reserved character names
# nothing (Win32's ERROR_INVALID_NAME).
_WIN_FOLDERS = [
    "c:\\", "c:\\b", "c:\\b\\a", "c:\\b\\a ", "c:\\b\\a \\x", "c:\\b\\sub", "c:\\b\\sub\\x",
    "c:\\b\\x", "c:\\b\\a.", "c:\\b\\a.\\x", "c:\\b\\nul", "c:\\b\\nul\\x", "c:\\b\\.hidden",
    "c:\\b\\v1.2", "c:\\b\\cache", "c:\\b\\cache\\made", "d:\\", "d:\\work", "d:\\work\\proj",
    "d:\\work\\proj\\sub", "\\\\srv\\share", "\\\\srv\\share\\x", "c:\\b\\com0",
]  # fmt: skip
_WIN_TREE = {path: (1, n) for n, path in enumerate(_WIN_FOLDERS, 1)}
_WIN_FILES = {"c:\\b\\f.txt": (1, 100)}
_WIN_LINKS = {"c:\\b\\link": (1, 200)}
_WIN_CWD = {"C:": "C:\\b", "D:": "D:\\work\\proj"}
_WIN_DEVICES = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
_WIN_DEVICES |= {f"{p}{c}" for p in ("COM", "LPT") for c in "123456789\u00b9\u00b2\u00b3"}
_WIN_CHARS = set('"*<>?|' + "".join(map(chr, range(32))))


def _win_resolve(s: str) -> str | None:
    """The folder a Win32 path names, as a lower-case key; None for a device."""
    import ntpath

    if s.startswith("\\\\?\\"):
        drive, _, tail = ntpath.splitroot(s)
        return (drive[4:] + "\\" + tail).rstrip("\\").lower() if tail else drive[4:].lower() + "\\"
    last_kept = not s.endswith(("\\", "/"))
    s = s.replace("/", "\\")
    if s.startswith("\\\\"):
        drive, _, rest = ntpath.splitroot(s)
    elif s[1:2] == ":" and s[2:3] != "\\":
        s = _WIN_CWD[s[:2].upper()] + "\\" + s[2:]
        drive, rest = s[:2], s[3:]
    elif s.startswith("\\"):
        drive, rest = "C:", s[1:]
    elif s[1:2] == ":":
        drive, rest = s[:2], s[3:]
    else:
        s = _WIN_CWD["C:"] + "\\" + s
        drive, rest = s[:2], s[3:]
    out: list[str] = []
    for seg in rest.split("\\"):
        if seg == "..":
            if out:
                out.pop()
        elif seg not in ("", "."):
            out.append(seg[:-1] if seg.endswith(".") else seg)
    if out and last_kept:
        out[-1] = out[-1].rstrip(" .")
        if out[-1].split(".")[0].rstrip(" ").upper() in _WIN_DEVICES:
            return None
    if any(_WIN_CHARS.intersection(seg) for seg in out):
        return None
    if not out:
        return (drive if drive.startswith("\\\\") else drive + "\\").lower()
    return (drive + "\\" + "\\".join(out)).lower()


class _WinFake:
    """A stand-in for the Windows platform's `open_handle`, `close_held` and `_drive_folder`
    over the model: it records every path opened and every handle still held."""

    def __init__(self) -> None:
        self.opened: list[str] = []
        self.held: dict[int, str] = {}
        self.next = 1

    def open(self, path: str, follow: bool, access: int = 0) -> tuple[int, int, tuple]:
        self.opened.append(path)
        key = _win_resolve(path)
        if key is None:
            raise OSError(1, "Incorrect function", path)
        if key in _WIN_TREE:
            found = (0x10, _WIN_TREE[key])
        elif key in _WIN_FILES:
            found = (0x20, _WIN_FILES[key])
        elif key in _WIN_LINKS:
            found = (0x10 | 0x400, _WIN_LINKS[key])
        else:
            raise FileNotFoundError(2, "The system cannot find the file specified", path)
        h, self.next = self.next, self.next + 1
        self.held[h] = key
        return h, found[0], found[1]

    def close(self, h: int) -> None:
        del self.held[h]

    def install(self, monkeypatch) -> _platform_windows._Windows:
        """A Windows platform object whose handle calls are this model's."""
        platform = _platform_windows._Windows()
        monkeypatch.setattr(platform, "open_handle", self.open)
        monkeypatch.setattr(platform, "close_held", self.close)
        monkeypatch.setattr(
            process().observers, "drive_folder", lambda drive: _WIN_CWD[(drive or "C:").upper()]
        )
        return platform


def _win_chain(walked_path: str) -> tuple:
    """The true chain of the folder a walked path names: its identity and each ancestor's."""
    key = _win_resolve(walked_path)
    assert key is not None and key in _WIN_TREE, walked_path
    if key.startswith("\\\\"):
        parts = key.split("\\")
        root, rest = "\\\\" + parts[2] + "\\" + parts[3], [p for p in parts[4:] if p]
        prefixes = [root] + [root + "\\" + "\\".join(rest[:k]) for k in range(1, len(rest) + 1)]
    else:
        parts = [p for p in key.split("\\") if p]
        prefixes = [parts[0] + "\\"] + [
            parts[0] + "\\" + "\\".join(parts[1:k]) for k in range(2, len(parts) + 1)
        ]
    return tuple(_WIN_TREE[p] for p in reversed(prefixes))


def test_the_windows_walk_takes_dot_dot_on_walked_folders(monkeypatch) -> None:
    """On every system: the judged Windows walk over the
    Win32 model above. `..` is taken on the folders walked (refused after a missing folder or a
    file); a name Windows rewrites (a `:`, a trailing space or period, a reserved device name) is
    refused before it is opened; a rooted path takes the current drive; a drive's root keeps its
    separator; and no `..` leaks a handle. The superscript device names,
    the console names and the reserved characters are refused the same way, and `COM0` is not."""
    fake = _WinFake()
    windows = fake.install(monkeypatch)

    def walk(path: str, may_make: bool = False) -> _platform._Walked:
        return windows.walk("g", path, judge=True, may_make=may_make)

    def refused(path: str, match: str, may_make: bool = False) -> None:
        with pytest.raises(ValueError, match=match):
            walk(path, may_make)
        assert fake.held == {}, (path, fake.held)

    def walked_to(path: str, want: str, held: set[str] | None = None) -> None:
        w = walk(path)
        try:
            assert w.path == want, (path, w.path)
            assert w.chain == _win_chain(want), path
            assert w.missing == ()
            if held is not None:  # the folders still held: the ones on the way, none popped
                assert set(fake.held.values()) == held, (path, fake.held)
        finally:
            w.close()
        assert fake.held == {}, (path, fake.held)

    rewrites = "a name Windows rewrites"
    refused(r"C:\b\new\..\x", "does not exist", may_make=True)
    refused(r"C:\b\new\..\x", "does not exist")
    refused(r"C:\b\f.txt\..\x", "is not a folder")
    walked_to(r"C:\b\sub\..\x", r"C:\b\x", held={"c:\\", "c:\\b", "c:\\b\\x"})
    walked_to(r"C:\..\b", r"C:\b")
    refused(r"C:\b\link\..\x", "link or junction")
    missing = walk(r"C:\b\new\deeper", may_make=True)
    assert missing.missing == ("new", "deeper") and missing.chain == _win_chain(r"C:\b")
    missing.close()
    refused(r"C:\b\cache\new\..\made", "does not exist", may_make=True)
    walked_to("sub\\x", r"C:\b\sub\x")  # relative: the current folder of the current drive
    walked_to(r"\b\x", r"C:\b\x")  # rooted with no drive: qualified with the current drive
    walked_to("D:sub", r"D:\work\proj\sub")  # drive-relative: that drive's current folder
    walked_to(r"C:\b\..", "C:\\")  # a drive's root keeps its separator
    walked_to(r"\\srv\share\x\..", "\\\\srv\\share\\")
    walked_to(r"\\srv\share\x\..\..\x", r"\\srv\share\x")
    walked_to(r"\\?\C:\b\sub\..\x", r"\\?\C:\b\x")
    walked_to("C:/b/sub/x/", r"C:\b\sub\x")
    walked_to(r"C:\b\.hidden", r"C:\b\.hidden")  # a period inside a name is no rewrite
    walked_to(r"C:\b\v1.2", r"C:\b\v1.2")
    walked_to(r"C:\b\COM0", r"C:\b\COM0")  # no source reserves COM0
    # Two more cases, and the rest of the names Windows rewrites: each is
    # refused before anything is opened for it.
    before = len(fake.opened)
    for path, may_make in [
        (r"C:\b\D:sub", False),
        (r"\\?\C:\b\a ", False),
        (r"C:\b\a \x", False),
        (r"C:\b\a.\x", False),
        (r"C:\b\...", False),
        (r"C:\b\sub::$INDEX_ALLOCATION", False),
        (r"C:\b\new.", True),
        (r"C:\b\new\NUL", True),  # a reserved name in a root still to be made: nothing is made
        (r"C:\b\nul\x", False),
        (r"C:\b\nul.txt", False),
        (r"C:\b\Com1.log", True),
        (r"C:\b\LPT9", True),
        (r"C:\b\aux .x", True),
        # Microsoft's superscript names, CPython's console names and reserved
        # characters; the three roots still to be made are refused before anything is made.
        ("C:\\b\\new\\COM\u00b9", True),
        (r"C:\b\new\CONIN$", True),
        (r"C:\b\new\a*b", True),
        ("C:\\b\\com\u00b2\\x", False),
        ("C:\\b\\Com\u00b3.log", False),
        ("C:\\b\\LPT\u00b9", False),
        ("C:\\b\\lpt\u00b2 .x", True),
        ("C:\\b\\lpt\u00b3.txt", True),
        (r"C:\b\conout$.log", False),
    ]:
        refused(path, rewrites, may_make)
    rewritten = ("D:sub", "a ", "a.", "...", "::", "new.", "NUL", "nul", "Com1", "LPT9", "aux")
    rewritten += ("COM\u00b9", "CONIN$", "a*b", "com\u00b2", "Com\u00b3", "LPT\u00b9")
    rewritten += ("lpt\u00b2", "lpt\u00b3", "conout$")
    assert not [p for p in fake.opened[before:] if p.rsplit("\\", 1)[-1].startswith(rewritten)]


def test_the_windows_walk_records_the_true_chain(monkeypatch) -> None:
    """Over every spelling of up to
    three components from a small alphabet, under seven heads, whenever the judged Windows walk
    accepts a path, the chain it records is the true chain of the folder its walked path names,
    and no handle is left held."""
    import itertools

    fake = _WinFake()
    windows = fake.install(monkeypatch)
    alphabet = ["b", "sub", "x", "a", "a ", "a.", "..", ".", "", "D:sub", "nul", "f.txt", "work"]
    heads = ["C:\\", "D:\\", "\\", "", "\\\\?\\C:\\", "D:", "\\\\srv\\share\\"]
    accepted = refused = 0
    for head in heads:
        for k in (1, 2, 3):
            for combo in itertools.product(alphabet, repeat=k):
                path = head + "\\".join(combo)
                try:
                    w = windows.walk("g", path, judge=True)
                except ValueError:
                    refused += 1
                else:
                    try:
                        assert w.chain == _win_chain(w.path), (path, w.path)
                    finally:
                        w.close()
                    accepted += 1
                assert fake.held == {}, path
    # 642 accepted and 16,011 refused on macOS: the fuzz is not vacuous on either side.
    assert accepted + refused == 16_653 and accepted > 600 and refused > 15_000, (accepted, refused)


@pytest.mark.skipif(sys.version_info < (3, 13), reason="ntpath.isreserved is new in Python 3.13")
def test_a_rewritten_name_is_one_ntpath_refuses() -> None:
    """The Windows walk refuses exactly the names Python's own
    `ntpath.isreserved` refuses, for one path component, over every name of one to three pieces
    (a leading `x\\` keeps `ntpath` from reading `D:` as a drive)."""
    import itertools
    import ntpath

    pieces = ["", ".", "..", " ", "a", "nul", "NUL", "com\u00b9", "LPT\u00b3", "conin$"]
    pieces += ["CONOUT$", "com0", "com10", "x*y", "a\x01", "D:", "?", "|", "<", '"', ".txt"]
    pieces += [" .x", "con\u0131n$", "\u0131", "K", "s"]
    names = ["".join(c) for k in (1, 2, 3) for c in itertools.product(pieces, repeat=k)]
    names = [n for n in names if n]  # 18,275 spellings (16,175 distinct)
    differ = [n for n in names if _platform_windows._rewritten(n) != ntpath.isreserved("x\\" + n)]
    assert not differ, sorted(map(ascii, set(differ)))[:8]
    refused = sum(map(_platform_windows._rewritten, names))
    assert len(names) == 18_275 and 0 < refused < len(names), (len(names), refused)


RAW = r"""(module
  (import "wasi_snapshot_preview1" "path_open"
    (func $po (param i32 i32 i32 i32 i32 i64 i64 i32 i32) (result i32)))
  (import "wasi_snapshot_preview1" "fd_allocate" (func $fa (param i32 i64 i64) (result i32)))
  (import "wasi_snapshot_preview1" "fd_renumber" (func $fr (param i32 i32) (result i32)))
  (import "wasi_snapshot_preview1" "fd_write" (func $fw (param i32 i32 i32 i32) (result i32)))
  (import "wasi_snapshot_preview1" "fd_read" (func $fd (param i32 i32 i32 i32) (result i32)))
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
    (call $fw (local.get 0) (i32.const 200) (i32.const 1) (i32.const 208)))
  (func (export "read") (param i32) (result i32)
    (call $fd (local.get 0) (i32.const 200) (i32.const 1) (i32.const 208))))"""
EPERM, ENOTSUP = 63, 58
READ, WRITE, ALL = 1 << 1, 1 << 6, (1 << 29) - 1
TRUNC = 8


def test_a_read_only_grant_refuses_raw_writes(tmp_path) -> None:
    """Every raw preview1 write-type call, on a preopen made as the runner
    makes a read-only grant (`fs_mutable=False`); fd 4 is a writable control. A descriptor used
    in a mode it was not opened for is refused with the host's errno, per system:
    a write through the grant's read descriptor, and a read through a write-only
    descriptor of the writable grant. The read asks for two real bytes, and a control read through
    the same export, its count and buffer zeroed first, shows it does."""
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
    wrong_mode = files.wrong_mode_errno(sys.platform)
    assert ex["write"](store, ro_fd) == wrong_mode  # EBADF on POSIX, EACCES on Windows
    errno, wo_fd = open_(4, "w.txt", 0, WRITE)
    assert errno == 0
    assert ex["read"](store, wo_fd) == wrong_mode  # the read twin
    errno, rw_fd = open_(4, "w.txt", 0, READ | WRITE)
    assert errno == 0
    # fd_renumber onto the grant's file only moves the writable descriptor to that number.
    assert ex["renumber"](store, rw_fd, ro_fd) == 0
    assert ex["write"](store, ro_fd) == 0
    assert (ro / "f.txt").read_text() == "original" and (rw / "w.txt").read_text() == "XX"
    assert sorted(p.name for p in ro.iterdir()) == ["f.txt"]
    # The control: the same `read` export through a descriptor that may read reads two bytes.
    memory.write(store, bytes(4), 208)
    memory.write(store, bytes(2), 300)
    errno, r_fd = open_(3, "f.txt", 0, READ)
    assert errno == 0
    assert ex["read"](store, r_fd) == 0
    assert struct.unpack("<I", bytes(memory.read(store, 208, 212)))[0] == 2
    assert bytes(memory.read(store, 300, 302)) == b"or"


@pytest.mark.skipif(not POSIX, reason="POSIX permission bits")
def test_a_folder_one_may_search_but_not_list_is_walked(tmp_path) -> None:
    """wasmtime opens a grant below such a folder, so the walk passes through it too;
    a folder one may not even search is refused with ValueError."""
    (tmp_path / "noread" / "child").mkdir(parents=True)
    (tmp_path / "noread").chmod(0o311)
    try:
        walked = _platform.PLATFORM.walk("g", str(tmp_path / "noread" / "child"), judge=True)
        walked.close()
        (tmp_path / "noread").chmod(0o000)
        if os.access(tmp_path / "noread", os.X_OK):  # run as root: no permission refuses it
            return
        with pytest.raises(ValueError, match="cannot be walked"):
            _platform.PLATFORM.walk("g", str(tmp_path / "noread" / "child"), judge=True)
    finally:
        (tmp_path / "noread").chmod(0o755)


@pytest.mark.skipif(POSIX, reason="junctions are Windows'")
def test_a_junction_is_refused_on_windows(tmp_path) -> None:
    """Windows' link rule: every reparse point on the way is refused;
    a junction needs no privilege to make."""
    import _winapi

    target = tmp_path / "target"
    target.mkdir()
    _winapi.CreateJunction(str(target), str(tmp_path / "junction"))
    with pytest.raises(ValueError, match="link or junction"):
        _platform.PLATFORM.walk("g", str(tmp_path / "junction"), judge=True)
    with pytest.raises(ValueError, match="link or junction"):
        _platform.PLATFORM.walk("g", str(tmp_path / "junction" / "."), judge=True)


@pytest.mark.skipif(POSIX, reason="Windows holds every walked folder")
def test_a_walked_folder_cannot_be_moved_on_windows(tmp_path) -> None:
    """Decision 5: while the walk holds its handles, no folder on the way can be renamed, so no
    swap can happen before the identity check."""
    (tmp_path / "a" / "b").mkdir(parents=True)
    walked = _platform.PLATFORM.walk("g", str(tmp_path / "a" / "b"), judge=True)
    try:
        for old, new in ((tmp_path / "a", tmp_path / "c"), (tmp_path / "a" / "b", tmp_path / "d")):
            with pytest.raises(PermissionError):
                os.rename(old, new)
    finally:
        walked.close()
    os.rename(tmp_path / "a", tmp_path / "c")  # released: it moves again


# The raw parity table. The same rows run on a read-only grant (plain
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
    "pstat 'a.txt/x'",
    "pstat 'a.txt/' following links",
    "pstat 'a.txt/.' following links",
    "pstat 'a\\x00'",
    "pstat 'x' * 256",
    "readlink 'a.txt'",
    "readlink 'd'",
    "readlink 'a.txt/'",
}
# Rows whose grant answer differs between POSIX systems, compared only on the systems named
# (the landing notes, "Revised after landing", second part). A read whose end passes 2**63 - 1
# is EINVAL on Linux, the reference, and the mount answers so everywhere; macOS answers 0 (and
# fd_pread counts at most 64 KiB of the end). A stat of `a.txt/` or `a.txt/.` without
# SYMLINK_FOLLOW (`os.lstat`) is ENOTDIR on macOS and on the mount, as an open of either is on
# every system and as the same stat following links is on Linux too; Linux's grant answers the
# file's stat to the no-follow stat alone, a deliberate difference in Decision 6.
SYSTEM_ROWS = {
    "pread at 2**63 - 1": {"linux"},
    "read at 2**63 - 1": {"linux"},
    "pstat 'a.txt/'": {"darwin"},
    "pstat 'a.txt/.'": {"darwin"},
    "pread 100,000 at 2**63 - 65,536": {"linux"},
    "pread 100,000 at 2**63 - 65,537": {"linux"},
    "read 100,000 at 2**63 - 100,000": {"linux"},
    "read 100,000 at 2**63 - 100,001": {"linux"},
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
    # Nothing to read at an offset of 2**63 or more: still EINVAL, on every system.
    for at in (2**63, -1):  # -1 is 2**64 - 1 as an i64
        row(f"pread nothing at {at}", r.pread, F, [], at)
        row(f"pread an empty buffer at {at}", r.pread, F, [0], at)
    row("seek to 2**63 for nothing", lambda: (r.seek(F, 2**63 - 1, 0), r.seek(F, 1, 1)))
    row("read nothing at 2**63", r.read, F, [])
    row("read an empty buffer at 2**63", r.read, F, [0])
    # fd_pread counts at most 64 KiB of a read's end (wasmtime's MAX_READ_SIZE_ALLOC); fd_read
    # counts all of it (Linux only, SYSTEM_ROWS).
    top = 2**63 - 1
    row("pread 100,000 at 2**63 - 65,536", r.pread, F, [100_000], top - 65_535)
    row("pread 100,000 at 2**63 - 65,537", r.pread, F, [100_000], top - 65_536)
    row(
        "read 100,000 at 2**63 - 100,000",
        lambda: (r.seek(F, top - 99_999, 0), r.read(F, [100_000])),
    )
    row(
        "read 100,000 at 2**63 - 100,001",
        lambda: (r.seek(F, top - 100_000, 0), r.read(F, [100_000])),
    )
    row("seek back again", r.seek, F, 0, 0)
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
    row("pstat 'a.txt/' following links", r.path_filestat, P, "a.txt/", 1)
    row("pstat 'a.txt/.' following links", r.path_filestat, P, "a.txt/.", 1)
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
    # A grant as the runner serves it: wasmtime's own calls, but for the two the guard forwards
    # with wasmtime 49.0.2's and 49.0.3's fixes.
    grant = files.Guarded([(tree, "/m", False), (sides[0], "/w", True)]).raw
    mount = files.Mounted(files.MemoryProvider(), placeholder, folders=[(sides[1], "/w", True)])
    return grant, mount


def test_raw_calls_answer_as_a_grant_does(tmp_path) -> None:
    """Each of the 29 shadowed calls on a provider file, folder and
    preopen answers as on a read-only grant's (errno and every byte written), but for Decision
    6's deliberate differences, asserted in the next test."""
    grant, mount = _two_sides(tmp_path)
    want, got = _parity_script(grant), _parity_script(mount.raw)
    assert list(want) == list(got)
    differ = {
        label: (want[label], got[label])
        for label in want
        if want[label] != got[label]
        and (POSIX or label not in HOST_ROWS)
        and sys.platform in SYSTEM_ROWS.get(label, {sys.platform})
    }
    assert differ == {}, differ
    assert sorted(p.name for p in (tmp_path / "w-mount").iterdir()) == ["w.txt"]
    assert sorted(p.name for p in (tmp_path / "tree").iterdir()) == ["a.txt", "b.txt", "d", "e"]


def test_the_deliberate_differences_are_as_decided(tmp_path) -> None:
    """Where a mount answers otherwise than a read-only grant,
    each answer is the one the table decides (and the grant's is asserted where it does not
    depend on the host, or per system where it does)."""
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

    # `..` resolved by text: one provider call on one normalized path. A POSIX grant walks each
    # part; a Windows grant resolves `..` by text as the mount does: cap-std's own Windows open
    # pops the name before each `..` before any lookup (READ, cap-primitives 4.0.3,
    # `src/fs/manually/open.rs`, `Context::new`'s `#[cfg(windows)]` block; EXECUTED for
    # `missing/../a.txt` in release dry run 39105048310).
    assert both(lambda r: r.open(3, "missing/../a.txt")[0]) == (44 if POSIX else 0, 0)
    assert both(lambda r: r.open(3, "a.txt/../b.txt")[0]) == (54 if POSIX else 0, 0)
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
    # Reads at the end of i64, as Linux answers a grant (the reference), on every system: the
    # end of an fd_read past 2**63 - 1 is EINVAL; fd_pread counts at most 64 KiB of it.
    top = 2**63 - 1
    assert [m.pread(mf, [size], at)[0] for size, at in [
        (4, top), (4, top - 3), (4, top - 4), (1, top), (1, top - 1),
        (100_000, top - 65_535), (100_000, top - 65_536),
    ]] == [28, 28, 0, 28, 0, 28, 0]  # fmt: skip
    for at, size, errno in [
        (top, 4, 28),
        (top - 3, 4, 28),
        (top - 4, 4, 0),
        (top - 99_999, 100_000, 28),
        (top - 100_000, 100_000, 0),
    ]:  # noqa: E501
        m.seek(mf, at, 0)
        assert m.read(mf, [size])[0] == errno, (at, size)
    m.seek(mf, top, 0)
    assert (m.read(mf, [0])[0], m.read(mf, [])[0]) == (0, 0)  # nothing to read: no refusal
    # A trailing slash or slash-dot on a file names a folder: ENOTDIR, as macOS answers and as
    # an open of it answers everywhere (Linux's grant answers the file's stat to a stat).
    assert (m.path_filestat(3, "a.txt/")[0], m.path_filestat(3, "a.txt/.")[0]) == (54, 54)


# The raw write rows. Each row runs on a fresh tree, as a writable grant (wasmtime behind the
# runner's guard, as every call without mounts runs) and as a writable mount (the runner's mount
# linker over the in-memory provider); preopen 3 is the tree on each side, 4 a writable folder and 5
# a read-only one. A row's whole result (the errno and every byte written; dev, ino, times and
# numbers masked) and the tree it leaves, after the call's ending, are compared. Decision 12's
# deliberate differences are asserted in the test after this one.

C, X, T, D = files.O_CREAT, files.O_EXCL, files.O_TRUNC, files.O_DIRECTORY
R, RW = files.READ_RIGHTS, files.RIGHTS_ALL
W_ONLY = files.FD_WRITE | files.FD_SEEK


def _opened(path, oflags=0, rights=RW, fdflags=0, then=None):
    """A row that opens `path` from the tree's preopen: the errno, and for a file opened, its
    fdstat, its filestat, what `then` gives, and its close."""

    def row(r: files.Raw):
        errno, fd = r.open(3, path, oflags, rights, fdflags)
        if fd is None:
            return errno
        out = [errno, r.fdstat(fd), r.filestat(fd)]
        if then is not None:
            out.append(then(r, fd))
        out.append(r("fd_close", fd))
        return out

    return row


def _write_rows() -> dict[str, object]:
    rows: dict[str, object] = {}
    shapes = {
        "r+": (0, RW),
        "w": (C | T, RW),
        "x": (C | X, RW),
        "a": (C, W_ONLY),
        "truncate": (T, R),
        "create read-only": (C, R),
        "exclusive alone": (X, RW),
        "x and truncate": (C | X | T, RW),
        "write-only": (0, W_ONLY),
    }
    for path in ("a.txt", "new", "d", "missing/x", "a.txt/x", "a.txt/", "new/", "d/", "."):
        for shape, (oflags, rights) in shapes.items():
            rows[f"open {shape} {path!r}"] = _opened(path, oflags, rights)
    for name, flag in (("SYNC", files.SYNC), ("DSYNC", files.DSYNC), ("RSYNC", files.RSYNC)):
        rows[f"open {name} to write"] = _opened("a.txt", 0, RW, flag)
    for path in ("d", "a.txt", "missing"):
        rows[f"open O_DIRECTORY with a write right {path!r}"] = _opened(path, D, RW)
    rows["open O_DIRECTORY and O_CREAT"] = _opened("d", D | C, R)
    rows["open O_DIRECTORY and O_TRUNC"] = _opened("new", D | T, R)
    then = {
        "write": lambda r, fd: (r.write(fd, b"zz"), r.tell(fd), r.pread(fd, [20], 0)),
        "two ciovecs": lambda r, fd: (
            r.put(files.BUFFER, b"abcdef"),
            r("fd_write", fd, r.iovecs([0, 2, 3]), 3, files.RESULT),
            r.u32(files.RESULT),
            r.pread(fd, [20], 0),
        ),
        "pwrite past the end": lambda r, fd: (
            r.write(fd, b"q", 20),
            r.filestat(fd),
            r.tell(fd),
            r.pread(fd, [30], 0),
        ),
        "pwrite at 2**63": lambda r, fd: r.write(fd, b"q", -(2**63)),
        "pwrite at 2**64 - 1": lambda r, fd: r.write(fd, b"q", -1),
        "an empty pwrite past the end": lambda r, fd: (r.write(fd, b"", 100), r.filestat(fd)),
        "a seek past the end, then a write": lambda r, fd: (
            r.seek(fd, 20, 0),
            r.write(fd, b"s"),
            r.tell(fd),
            r.pread(fd, [30], 0),
        ),
        "a seek to 2**63, then a write": lambda r, fd: (
            r.seek(fd, 2**62, 0),
            r.seek(fd, 2**62, 1),
            r.write(fd, b"s"),
        ),
        "set size 0": lambda r, fd: (r("fd_filestat_set_size", fd, 0), r.pread(fd, [20], 0)),
        "set size 20": lambda r, fd: (r("fd_filestat_set_size", fd, 20), r.pread(fd, [30], 0)),
        "set size 2**63": lambda r, fd: r("fd_filestat_set_size", fd, -(2**63)),
        "sync": lambda r, fd: (r.write(fd, b"y"), r("fd_sync", fd), r("fd_datasync", fd)),
        "set APPEND, then write": lambda r, fd: (
            r("fd_fdstat_set_flags", fd, files.APPEND),
            r.fdstat(fd),
            r.write(fd, b"q"),
            r.tell(fd),
            r("fd_fdstat_set_flags", fd, 0),
            r.write(fd, b"Q"),
            r.tell(fd),
            r.pread(fd, [30], 0),
        ),
        "allocate": lambda r, fd: r("fd_allocate", fd, 0, 10),
        "set times": lambda r, fd: [r("fd_filestat_set_times", fd, 0, 0, f) for f in (0, 3, 12)],
        "a write, a seek and a read": lambda r, fd: (
            r.write(fd, b"XY"),
            r.seek(fd, 0, 0),
            r.read(fd, [20]),
        ),
    }
    for name, fn in then.items():
        rows[f"r+ then {name}"] = _opened("a.txt", 0, RW, then=fn)
    rows["w then a write"] = _opened("new", C | T, RW, then=then["write"])
    rows["append then pwrite and write"] = _opened(
        "a.txt",
        0,
        RW,
        files.APPEND,
        then=lambda r, fd: (
            r.write(fd, b"zz", 0),
            r.tell(fd),
            r.write(fd, b"yy"),
            r.tell(fd),
            r.pread(fd, [30], 0),
        ),
    )
    rows["read-only, then the write calls"] = _opened(
        "a.txt",
        0,
        R,
        then=lambda r, fd: (
            r.write(fd, b"zz"),
            r.write(fd, b"zz", 0),
            r("fd_filestat_set_size", fd, 0),
            r("fd_sync", fd),
            r("fd_datasync", fd),
            r("fd_filestat_set_times", fd, 0, 0, 0),
        ),
    )
    rows["read-only, pwrite at 2**63"] = _opened("a.txt", 0, R, then=then["pwrite at 2**63"])
    rows["write-only, then reads"] = _opened(
        "a.txt", 0, W_ONLY, then=lambda r, fd: (r.read(fd, [3]), r.pread(fd, [3], 0))
    )
    rows["x twice"] = lambda r: (r.open(3, "n", C | X, RW)[0], r.open(3, "n", C | X, RW)[0])

    def folder(r: files.Raw):
        fd = r.open(3, "d", D)[1]
        return [
            r.write(fd, b"zz"),
            r.write(fd, b"zz", 0),
            r("fd_filestat_set_size", fd, 0),
            r("fd_sync", fd),
            r("fd_datasync", fd),
            r("fd_fdstat_set_flags", fd, files.APPEND),
            r("fd_allocate", fd, 0, 1),
            r("fd_filestat_set_times", fd, 0, 0, 0),
        ]

    rows["a folder, the write calls"] = folder
    rows["the preopen, the write calls"] = lambda r: [
        r.write(3, b"zz"),
        r("fd_filestat_set_size", 3, 0),
        r("fd_sync", 3),
        r("fd_datasync", 3),
        r("fd_fdstat_set_flags", 3, files.APPEND),
        r("fd_allocate", 3, 0, 1),
        [r("fd_filestat_set_times", 3, 0, 0, f) for f in (0, 3, 12)],
    ]
    for path in ("a.txt", ".", "d", "d/", "missing", "", "/x", ".."):
        rows[f"path set times {path!r}"] = lambda r, p=path: r.path_set_times(3, p, 0)
    rows["path set times, bad flags"] = lambda r: r.path_set_times(3, "a.txt", 3)
    calls = {
        "mkdir": "path_create_directory",
        "unlink": "path_unlink_file",
        "rmdir": "path_remove_directory",
    }
    for name, call in calls.items():
        for path in (
            "new", "new/", "d", "e", "a.txt", "missing", "missing/x", "a.txt/x", "a.txt/", "d/",
            "e/", ".", "..", "d/.", "e/.", "d/..", "new/.", "missing/.", "a.txt/.", "", "/x",
        ):  # fmt: skip
            rows[f"{name} {path!r}"] = lambda r, c=call, p=path: r.path_call(c, 3, p)
    for src, dst in [
        ("a.txt", "new"), ("a.txt", "b.txt"), ("d", "e"), ("e", "d"), ("a.txt", "d"),
        ("d", "a.txt"), ("d", "d/sub"), ("e", "e/sub"), ("a.txt", "a.txt"), ("d", "d"),
        ("d", "./d/"), ("missing", "missing"), ("missing", "new"), ("a.txt", "missing/c"),
        ("a.txt", "b.txt/c"), ("a.txt", "b.txt/"), ("a.txt/", "c"), ("d/", "f"), ("d", "f/"),
        ("a.txt", "newname/"), ("missing/", "x"), ("a.txt/", "a.txt"), ("a.txt", "a.txt/"),
        (".", "q"), ("a.txt", "."), ("a.txt", ".."), ("e", "e/."), ("e/.", "f"),
        ("d/..", "x"), ("d/../", "x"), ("e", "d/.."), ("a.txt", ""), ("", "x"),
        ("d/x.txt", "e/x.txt"), ("e", "d/e2"),
    ]:  # fmt: skip
        rows[f"rename {src!r} {dst!r}"] = lambda r, s=src, d=dst: r.rename(3, s, 3, d)
    rows["rename to a read-only folder"] = lambda r: r.rename(3, "a.txt", 5, "c")
    rows["rename from a read-only folder"] = lambda r: r.rename(5, "r.txt", 3, "c")
    rows["link to a read-only folder"] = lambda r: r.link(3, "a.txt", 5, "c")
    rows["link following links within"] = lambda r: r.link(3, "a.txt", 3, "c", 1)
    rows["link following links to a read-only folder"] = lambda r: r.link(3, "a.txt", 5, "c", 1)
    rows["link following links to a writable folder"] = lambda r: r.link(3, "a.txt", 4, "c", 1)
    rows["a file renamed while open"] = lambda r: (
        lambda fd: (r.rename(3, "a.txt", 3, "moved"), r.write(fd, b"M"), r("fd_close", fd))
    )(r.open(3, "a.txt", 0, RW)[1])
    rows["a file removed while open"] = lambda r: (
        lambda fd: (
            r.path_call("path_unlink_file", 3, "a.txt"),
            r.write(fd, b"gone"),
            r.seek(fd, 0, 0),
            r.read(fd, [20]),
            r.filestat(fd),
            r("fd_close", fd),
        )
    )(r.open(3, "a.txt", 0, RW)[1])
    return rows


# Rows whose answer on a writable grant is Linux's on Linux and the host's own elsewhere: the
# mount gives Linux's everywhere (wasmtime's reference; EXECUTED on wasmtime 49 in a Linux
# container in the build, and on macOS, which answers otherwise here). Each holds Linux's answer.
LINUX_ROWS: dict[str, object] = {
    "unlink 'd'": 31,
    "unlink 'e'": 31,
    "unlink 'd/'": 31,
    "unlink 'e/'": 31,
    "unlink '.'": 31,
    "unlink 'd/.'": 31,
    "unlink 'e/.'": 31,
    "unlink 'd/..'": 31,
    "rename '.' 'q'": 10,
    "rename 'a.txt' '.'": 10,
    "rename 'e' 'e/.'": 10,
    "rename 'e/.' 'f'": 10,
    "rename 'd/..' 'x'": 10,
    "rename 'd/../' 'x'": 10,
    "rename 'e' 'd/..'": 10,
    "open w 'new/'": 31,
    "open x 'new/'": 31,
    "open a 'new/'": 31,
    "open create read-only 'new/'": 31,
    "open x and truncate 'new/'": 31,
    "open w 'a.txt/'": 31,
    "open x 'a.txt/'": 31,
    "open a 'a.txt/'": 31,
    "open create read-only 'a.txt/'": 31,
    "open x and truncate 'a.txt/'": 31,
    "open w 'd/'": 31,
    "open x 'd/'": 31,
    "open a 'd/'": 31,
    "open create read-only 'd/'": 31,
    "open x and truncate 'd/'": 31,
    "open x '.'": 20,
    "open x and truncate '.'": 20,
    "read-only, pwrite at 2**63": [0, (0, 4, 0, files.READ_RIGHTS, files.READ_RIGHTS),
                                  (0, 4, 1, 13), (28, 0), 0],
    "path set times 'missing'": 0,
}  # fmt: skip
# Rows wasmtime answers by its own logic, the same on every host; every other row's grant answer
# is the host's own, so it is compared on POSIX hosts only (the release dry run's Windows `verify`
# job asserts the mount's side, as the mounts' rows do).
WASMTIME_ROWS = {
    "open SYNC to write",
    "open DSYNC to write",
    "open RSYNC to write",
    "open O_DIRECTORY and O_CREAT",
    "open O_DIRECTORY and O_TRUNC",
    "r+ then allocate",
    "path set times, bad flags",
    *(
        "rename 'a.txt' 'newname/'",
        "rename 'a.txt' 'b.txt/'",
        "rename 'a.txt' 'a.txt/'",
    ),
}
# A file renamed to a name ending in `/`: ENOTDIR, the source's stat deciding it, on the guarded
# grant (the guard carries wasmtime 49.0.3's rule; 49.0.0 strips the target's `/` and renames)
# and on the mount (`RENAME_SLASH_NEEDS_FOLDER`), the same on every host.
SLASH_ROWS = {
    "rename 'a.txt' 'newname/'": 54,
    "rename 'a.txt' 'b.txt/'": 54,
    "rename 'a.txt' 'a.txt/'": 54,
    "rename 'd' 'f/'": 0,  # a folder: renamed by its plain names
}


def _write_sides(root: Path) -> tuple[files.Raw, Path, files.Mounted, files.MemoryProvider]:
    root.mkdir()
    out = []
    for side in ("grant", "mount"):
        w, ro = root / f"{side}-w", root / f"{side}-ro"
        w.mkdir()
        ro.mkdir()
        (ro / "r.txt").write_bytes(b"r")
        out.append([(w, "/w", True), (ro, "/ro", False)])
    tree = files.write_tree(root / "tree")
    grant = files.Guarded([(tree, "/m", True), *out[0]]).raw  # the guarded grant
    placeholder = root / "placeholder"
    placeholder.mkdir()
    provider = files.MemoryProvider()
    mount = files.Mounted(provider, placeholder, writable=True, folders=out[1])
    return grant, tree, mount, provider


def _attempt(fn, r: files.Raw) -> object:
    try:
        return fn(r)
    except files.Ends as e:
        return ("ends", e.message)


def _on_disk(tree: Path) -> list[str]:
    return sorted(
        p.relative_to(tree).as_posix() + ("/" if p.is_dir() else "=" + p.read_bytes().hex())
        for p in tree.rglob("*")
    )


def _in_memory(provider: files.MemoryProvider) -> list[str]:
    return sorted(
        p.lstrip("/") + ("/" if data is None else "=" + data.hex())
        for p, data in provider.tree.items()
    )


def test_raw_write_calls_answer_as_a_writable_grant_does(tmp_path) -> None:
    """Each call that can write, on a provider file, folder and preopen
    of a writable mount, answers as on a writable grant's (the whole result, and the tree left
    after the call's ending), but for Decision 12's differences, asserted next. A row whose
    grant answer is the host's own is asserted per system: Linux's answer on the mount
    everywhere, and the grant's beside it on Linux."""
    import sys

    rows = _write_rows()
    differ, linux = {}, {}
    for i, (label, fn) in enumerate(rows.items()):
        grant, tree, mount, provider = _write_sides(tmp_path / str(i))
        want = _attempt(fn, grant)
        got = _attempt(fn, mount.raw)
        mount.table.walk()  # the call's ending
        want_tree, got_tree = _on_disk(tree), _in_memory(provider)
        if label in SLASH_ROWS and (want, got) != (SLASH_ROWS[label],) * 2:
            linux[label] = (SLASH_ROWS[label], want, got)
        if label in LINUX_ROWS:
            if got != LINUX_ROWS[label]:
                linux[label] = (LINUX_ROWS[label], got)
            if sys.platform != "linux":
                want = got
        if (want, want_tree) != (got, got_tree) and (POSIX or label in WASMTIME_ROWS):
            differ[label] = ((want, want_tree), (got, got_tree))
    assert linux == {}, linux
    assert differ == {}, differ
    assert len(rows) > 200


def test_the_write_differences_are_as_decided(tmp_path) -> None:
    """Where a writable mount answers otherwise than a writable
    grant, each answer is the one the table decides; the grant's is asserted beside it on POSIX
    hosts (on Windows its answers are the host's, which the release dry run first sees)."""
    grant, tree, mount, provider = _write_sides(tmp_path / "one")
    g, m = grant, mount.raw

    def both(fn) -> tuple[object, object]:
        mounted = _attempt(fn, m)
        return (_attempt(fn, g) if POSIX else None), mounted

    def grant_says(value: object) -> object:
        return value if POSIX else None

    # Unflushed writes are seen only through their own descriptor until its close.
    fds = [r.open(3, "a.txt", 0, RW)[1] for r in (g, m)]
    assert [r.write(fd, b"++", 13) for r, fd in zip((g, m), fds, strict=True)] == [(0, 2)] * 2
    assert both(lambda r: r.path_filestat(3, "a.txt")[3]) == (grant_says(15), 13)
    assert [r("fd_close", fd) for r, fd in zip((g, m), fds, strict=True)] == [0, 0]
    assert both(lambda r: r.path_filestat(3, "a.txt")[3]) == (grant_says(15), 15)
    # Two descriptors on one path: two buffers, and the later write-back replaces the earlier.
    pairs = [(r.open(3, "b.txt", 0, RW)[1], r.open(3, "b.txt", 0, RW)[1]) for r in (g, m)]
    for r, (one, two) in zip((g, m), pairs, strict=True):
        assert (r.write(one, b"1111"), r.write(two, b"22")) == ((0, 4), (0, 2))
        assert (r("fd_close", two), r("fd_close", one)) == (0, 0)
    assert provider.tree["/b.txt"] == b"1111"
    assert not POSIX or (tree / "b.txt").read_bytes() == b"2211"
    # A write past the staging bound: EFBIG (the grant's is the host's own: EINVAL on Linux).
    fds = [r.open(3, "a.txt", 0, RW)[1] for r in (g, m)]
    assert m.write(fds[1], b"zz", 2**63 - 1) == (22, 0)
    # A rename or link to another writable preopen: EXDEV, where two grants succeed.
    assert both(lambda r: r.rename(3, "b.txt", 4, "c")) == (grant_says(0), 75)
    assert both(lambda r: r.link(3, "a.txt", 4, "c2")) == (grant_says(0), 75)
    # A link or symlink within: ENOTSUP, where a grant on a POSIX host makes it.
    assert both(lambda r: r.link(3, "a.txt", 3, "c3")) == (grant_says(0), 58)
    assert both(lambda r: r.symlink("a.txt", 3, "l")) == (grant_says(0), 58)
    # The set-times calls succeed and change nothing, with no provider call, even where a grant
    # would answer the host's error for the path.
    before = provider.total()
    assert both(lambda r: r.path_set_times(3, "a.txt/", 0)) == (grant_says(54), 0)
    assert both(lambda r: r("fd_filestat_set_times", 3, 0, 0, 0)) == (grant_says(0), 0)
    assert provider.total() == before
    # A change by the embedder while a descriptor is open is not seen: the write-back goes to
    # the path the descriptor holds.
    fd = m.open(3, "e2", files.O_CREAT, RW)[1]
    provider.tree["/moved"] = provider.tree.pop("/e2")  # the embedder renames it
    assert (m.write(fd, b"E"), m("fd_close", fd)) == ((0, 1), 0)
    assert (provider.tree["/e2"], provider.tree["/moved"]) == (b"E", b"")
    # rmdir through a folder above a nested writable grant: the grant removes the nested
    # preopen's host folder; the mount answers EPERM at it and EBUSY above it.
    if POSIX:
        inner = tree / "d" / "inner"
        inner.mkdir()
        nested = files.Guarded([(tree, "/m", True), (inner, "/m/d/inner", True)]).raw
        assert nested.path_call("path_remove_directory", 3, "d/./inner") == 0
    placeholder = tmp_path / "nested-placeholder"
    placeholder.mkdir()
    (tmp_path / "inner").mkdir()
    nested_mount = files.Mounted(
        files.MemoryProvider(),
        placeholder,
        writable=True,
        folders=[(tmp_path / "inner", "/m/d/inner", True)],
    ).raw
    assert nested_mount.path_call("path_remove_directory", 3, "d/./inner") == 63
    assert nested_mount.path_call("path_remove_directory", 3, "d") == 10


# The Windows grant's listing at the v1.4 parity's "sorted listing" row, as release run
# 39135024458 printed it (EXECUTED, both binaries): the two `tmp…` names are a
# `TemporaryFile` and a `NamedTemporaryFile` whose open file Windows would not unlink or rename.
WINDOWS_LISTING = ["a.txt", "b.txt", "copy2.txt", "cr.txt", "g", "h", "save.txt", "tmp7zr2b8wp",
                   "tmpwlt5wwnt", "x.txt"]  # fmt: skip


@pytest.mark.parametrize("system", ["linux", "darwin", "win32"])
def test_the_write_parity_asserts_each_systems_grant(system) -> None:
    """The v1.4 write parity's per-system table gives each of the three systems its own
    grant answer, exactly, and one mount answer for all. A Windows grant renames a folder over a
    file and lists what follows from that; Linux's and macOS's grants answer `ENOTDIR` (54) and
    list what the mount lists. A `tmp…` slot takes only a name `tempfile` makes; a system the
    table does not name is an error, never a pass."""
    rename = files.write_by_system("rename a folder over a file", system)
    listing = files.write_by_system("sorted listing", system)
    mount = files.WRITE_MOUNT["sorted listing"]
    assert files.WRITE_MOUNT["rename a folder over a file"] == ["errno", 54]
    assert files.answer_matches(mount, mount)
    if system == "win32":
        assert rename is None
        assert files.answer_matches(listing, WINDOWS_LISTING)
        assert files.answer_matches(listing, [*WINDOWS_LISTING[:7], "tmp5nmlsrcc", "tmp6scne7rq",
                                              "x.txt"])  # fmt: skip
        assert not files.answer_matches(listing, mount)
        for slot in ("tmp7zr2b8w", "tmp7zr2b8wpq", "tmp7ZR2B8WP", "final.bin"):
            assert not files.answer_matches(listing, [*WINDOWS_LISTING[:7], slot,
                                                      *WINDOWS_LISTING[8:]])  # fmt: skip
        assert not files.answer_matches(listing, WINDOWS_LISTING[:-1])
    else:
        assert rename == ["errno", 54]
        assert listing == mount
        assert files.answer_matches(listing, mount)
        assert not files.answer_matches(listing, WINDOWS_LISTING)
        assert not files.answer_matches(listing, [n for n in mount if n != "e"])
    with pytest.raises(KeyError):
        files.write_by_system("sorted listing", "freebsd")
