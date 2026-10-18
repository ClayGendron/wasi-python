"""Spec 032's fixtures: an in-memory provider that counts its own calls, the same tree on disk, and
a table-driven raw preview1 module, so a parity row is data rather than a new guest.

`RAW_SIGNATURES` lists every preview1 call that takes a descriptor, with its raw wasm signature.
`raw_wat()` re-exports each one under its own name; `Raw` drives the exports on one store and
returns plain tuples, with the fields that differ by host or by design (`dev`, `ino`, times,
descriptor numbers, a folder's size and link count) left out, so a grant's answer and a mount's
can be compared with `==`.
"""

from __future__ import annotations

import re
import struct
import threading
from collections.abc import Callable, Iterator, Mapping
from contextlib import AbstractContextManager, contextmanager, nullcontext
from pathlib import Path
from typing import Any

WASI = "wasi_snapshot_preview1"

# Every preview1 call that names a descriptor, with its parameters (the result is one i32).
RAW_SIGNATURES: dict[str, tuple[str, ...]] = {
    "fd_advise": ("i32", "i64", "i64", "i32"),
    "fd_allocate": ("i32", "i64", "i64"),
    "fd_close": ("i32",),
    "fd_datasync": ("i32",),
    "fd_fdstat_get": ("i32", "i32"),
    "fd_fdstat_set_flags": ("i32", "i32"),
    "fd_fdstat_set_rights": ("i32", "i64", "i64"),
    "fd_filestat_get": ("i32", "i32"),
    "fd_filestat_set_size": ("i32", "i64"),
    "fd_filestat_set_times": ("i32", "i64", "i64", "i32"),
    "fd_pread": ("i32", "i32", "i32", "i64", "i32"),
    "fd_prestat_dir_name": ("i32", "i32", "i32"),
    "fd_prestat_get": ("i32", "i32"),
    "fd_pwrite": ("i32", "i32", "i32", "i64", "i32"),
    "fd_read": ("i32", "i32", "i32", "i32"),
    "fd_readdir": ("i32", "i32", "i32", "i64", "i32"),
    "fd_renumber": ("i32", "i32"),
    "fd_seek": ("i32", "i64", "i32", "i32"),
    "fd_sync": ("i32",),
    "fd_tell": ("i32", "i32"),
    "fd_write": ("i32", "i32", "i32", "i32"),
    "path_create_directory": ("i32", "i32", "i32"),
    "path_filestat_get": ("i32", "i32", "i32", "i32", "i32"),
    "path_filestat_set_times": ("i32", "i32", "i32", "i32", "i64", "i64", "i32"),
    "path_link": ("i32", "i32", "i32", "i32", "i32", "i32", "i32"),
    "path_open": ("i32", "i32", "i32", "i32", "i32", "i64", "i64", "i32", "i32"),
    "path_readlink": ("i32", "i32", "i32", "i32", "i32", "i32"),
    "path_remove_directory": ("i32", "i32", "i32"),
    "path_rename": ("i32", "i32", "i32", "i32", "i32", "i32"),
    "path_symlink": ("i32", "i32", "i32", "i32", "i32"),
    "path_unlink_file": ("i32", "i32", "i32"),
    "sock_accept": ("i32", "i32", "i32"),
    "sock_recv": ("i32", "i32", "i32", "i32", "i32", "i32"),
    "sock_send": ("i32", "i32", "i32", "i32", "i32"),
    "sock_shutdown": ("i32", "i32"),
}

PAGES = 2
MEMORY_END = PAGES * 65536  # the first address past the raw module's memory


def raw_wat() -> str:
    """One module that imports each call in `RAW_SIGNATURES` and exports it again, unchanged."""
    lines = ["(module"]
    for name, params in RAW_SIGNATURES.items():
        sig = f"(param {' '.join(params)}) (result i32)"
        lines.append(f'  (import "{WASI}" "{name}" (func ${name} {sig}))')
    lines.append(f'  (memory (export "memory") {PAGES})')
    for name, params in RAW_SIGNATURES.items():
        sig = f"(param {' '.join(params)}) (result i32)"
        gets = " ".join(f"(local.get {i})" for i in range(len(params)))
        lines.append(f'  (func (export "{name}") {sig} (call ${name} {gets}))')
    lines.append(")")
    return "\n".join(lines)


# Where the raw rows keep their arguments and results in the module's memory.
RESULT = 1024  # 64 bytes: a filestat, an fdstat, a new descriptor, a count
IOVECS = 2048
PATH = 4096
PATH2 = 6144
BUFFER = 8192  # 4 KiB for reads
DIRBUF = 12288  # 4 KiB for fd_readdir
SCRATCH_END = 16384

# preview1 constants the rows use
O_CREAT, O_DIRECTORY, O_EXCL, O_TRUNC = 1, 2, 4, 8
APPEND, DSYNC, NONBLOCK, RSYNC, SYNC = 1, 2, 4, 8, 16
FD_READ, FD_SEEK, FD_WRITE, FD_READDIR = 1 << 1, 1 << 2, 1 << 6, 1 << 14
RIGHTS_ALL = (1 << 30) - 1  # wasmtime 49's Rights::all()
READ_RIGHTS = RIGHTS_ALL & ~FD_WRITE
DIRECTORY, REGULAR_FILE = 3, 4


class Ends(Exception):
    """A call that ended the run instead of answering: wasmtime's error on a grant, or the error
    the runner recorded as the call's stop on a mount. `message` is its last line, without the
    frame number wasmtime puts first or the region it puts last."""

    def __init__(self, text: str) -> None:
        line = text.strip().splitlines()[-1].strip() if text.strip() else ""
        head, _, rest = line.partition(": ")
        if head.isdigit():
            line = rest
        self.message = line.split(": Region")[0]
        super().__init__(self.message)


class Raw:
    """Drives the raw module's exports on one store. `entered` wraps each call (the runner's
    mount side puts its call on the thread's stack there, and raises `Ends` when the call
    recorded a stop). A trap from wasmtime is raised as `Ends` too."""

    def __init__(
        self,
        store: Any,
        exports: Any,
        entered: Callable[[], AbstractContextManager[Any]] = nullcontext,
    ) -> None:
        self.store, self.exports, self.entered = store, exports, entered
        self.memory = exports["memory"]

    def __call__(self, name: str, *args: int) -> int:
        import wasmtime

        with self.entered():
            try:
                return self.exports[name](self.store, *args)
            except (wasmtime.Trap, wasmtime.WasmtimeError) as e:
                raise Ends(str(e)) from None

    def put(self, offset: int, data: bytes) -> None:
        self.memory.write(self.store, data, offset)

    def get(self, offset: int, size: int) -> bytes:
        return bytes(self.memory.read(self.store, offset, offset + size))

    def clear(self) -> None:
        self.put(RESULT, bytes(SCRATCH_END - RESULT))

    def u32(self, offset: int) -> int:
        return struct.unpack("<I", self.get(offset, 4))[0]

    def u64(self, offset: int) -> int:
        return struct.unpack("<Q", self.get(offset, 8))[0]

    def path(self, text: str | bytes, at: int = PATH) -> tuple[int, int]:
        data = text.encode() if isinstance(text, str) else text
        self.put(at, data)
        return at, len(data)

    def iovecs(self, sizes: list[int], at: int = IOVECS, buffer: int = BUFFER) -> int:
        """An iovec array at `at`, the buffers one after another from `buffer`."""
        out = b""
        for size in sizes:
            out += struct.pack("<II", buffer, size)
            buffer += size
        self.put(at, out)
        return at

    # The calls, with plain results.

    def open(
        self,
        base: int,
        path: str | bytes,
        oflags: int = 0,
        rights: int = READ_RIGHTS,
        fdflags: int = 0,
        dirflags: int = 0,
    ) -> tuple[int, int | None]:
        self.clear()
        ptr, size = self.path(path)
        args = (base, dirflags, ptr, size, oflags, rights, rights, fdflags, RESULT)
        errno = self("path_open", *args)
        return errno, (self.u32(RESULT) if errno == 0 else None)

    def filestat(self, fd: int) -> tuple:
        self.clear()
        return (self("fd_filestat_get", fd, RESULT), *self.filestat_fields())

    def path_filestat(self, base: int, path: str | bytes, flags: int = 0) -> tuple:
        self.clear()
        ptr, size = self.path(path)
        return (self("path_filestat_get", base, flags, ptr, size, RESULT), *self.filestat_fields())

    def filestat_fields(self) -> tuple:
        """filetype, nlink and size; a folder's link count and size are the host's own, so they
        are left out (dev, ino and the times always are)."""
        filetype = self.get(RESULT + 16, 1)[0]
        if filetype == DIRECTORY:
            return (filetype,)
        return filetype, self.u64(RESULT + 24), self.u64(RESULT + 32)

    def fdstat(self, fd: int) -> tuple:
        self.clear()
        errno = self("fd_fdstat_get", fd, RESULT)
        filetype, flags = struct.unpack_from("<BxH", self.get(RESULT, 4))
        return errno, filetype, flags, self.u64(RESULT + 8), self.u64(RESULT + 16)

    def read(self, fd: int, sizes: list[int]) -> tuple:
        self.clear()
        iovs = self.iovecs(sizes)
        errno = self("fd_read", fd, iovs, len(sizes), RESULT)
        n = self.u32(RESULT)
        return errno, n, self.get(BUFFER, sum(sizes))

    def pread(self, fd: int, sizes: list[int], offset: int) -> tuple:
        self.clear()
        iovs = self.iovecs(sizes)
        errno = self("fd_pread", fd, iovs, len(sizes), offset, RESULT)
        n = self.u32(RESULT)
        return errno, n, self.get(BUFFER, sum(sizes))

    def write(self, fd: int, data: bytes, at: int | None = None) -> tuple:
        self.clear()
        self.put(BUFFER, data)
        iovs = self.iovecs([len(data)])
        if at is None:
            errno = self("fd_write", fd, iovs, 1, RESULT)
        else:
            errno = self("fd_pwrite", fd, iovs, 1, at, RESULT)
        return errno, self.u32(RESULT)

    def seek(self, fd: int, offset: int, whence: int) -> tuple:
        self.clear()
        errno = self("fd_seek", fd, offset, whence, RESULT)
        return errno, self.u64(RESULT)

    def tell(self, fd: int) -> tuple:
        self.clear()
        errno = self("fd_tell", fd, RESULT)
        return errno, self.u64(RESULT)

    def readdir(self, fd: int, size: int = 4096, cookie: int = 0) -> tuple:
        """errno, the bytes used, and the buffer with each entry's d_ino zeroed."""
        self.clear()
        errno = self("fd_readdir", fd, DIRBUF, size, cookie, RESULT)
        used = self.u32(RESULT)
        return errno, used, masked_dirents(self.get(DIRBUF, used))

    def readdir_names(self, fd: int) -> tuple:
        """errno and the listing's (name, d_type) pairs, sorted: a host lists in its own order."""
        self.clear()
        errno = self("fd_readdir", fd, DIRBUF, 4096, 0, RESULT)
        data, pos, names = self.get(DIRBUF, self.u32(RESULT)), 0, []
        while pos + 24 <= len(data):
            namlen, d_type = struct.unpack_from("<IB", data, pos + 16)
            names.append((data[pos + 24 : pos + 24 + namlen].decode(), d_type))
            pos += 24 + namlen
        return errno, sorted(names)

    def prestat(self, fd: int) -> tuple:
        self.clear()
        errno = self("fd_prestat_get", fd, RESULT)
        return errno, self.get(RESULT, 8)

    def path_set_times(self, base: int, path: str, fst: int, lookup: int = 0) -> int:
        ptr, size = self.path(path)
        return self("path_filestat_set_times", base, lookup, ptr, size, 0, 0, fst)

    def readlink(self, base: int, path: str) -> tuple:
        self.clear()
        ptr, size = self.path(path)
        errno = self("path_readlink", base, ptr, size, BUFFER, 64, RESULT)
        return errno, self.u32(RESULT), self.get(BUFFER, 8)

    def path_call(self, name: str, base: int, path: str | bytes) -> int:
        """path_create_directory, path_remove_directory or path_unlink_file."""
        ptr, size = self.path(path)
        return self(name, base, ptr, size)

    def rename(self, base: int, old: str, new_base: int, new: str) -> int:
        a, n = self.path(old)
        b, m = self.path(new, PATH2)
        return self("path_rename", base, a, n, new_base, b, m)

    def link(self, base: int, old: str, new_base: int, new: str, flags: int = 0) -> int:
        a, n = self.path(old)
        b, m = self.path(new, PATH2)
        return self("path_link", base, flags, a, n, new_base, b, m)

    def symlink(self, target: str, base: int, new: str) -> int:
        a, n = self.path(target)
        b, m = self.path(new, PATH2)
        return self("path_symlink", a, n, base, b, m)


# d_ino only. The padding after d_type (21 to 24) is compared: the runner zeroes it on a grant's
# forwarded listing as a mount writes it (spec 048; wasmtime 49.0.0 fills it from uninitialized
# host memory, GHSA-96f6-r43r-8c24, fixed in wasmtime 49.0.2).
DIRENT_MASKED = tuple(range(8, 16))


def masked_dirents(data: bytes, masked: tuple[int, ...] = DIRENT_MASKED) -> bytes:
    """An fd_readdir buffer with what may differ by design zeroed in each entry's header: d_ino
    (bytes 8 to 16), or the bytes `masked` names. So entries compare by d_next, d_namlen, d_type,
    the padding and the name. An entry the buffer cut short is masked as far as it goes."""
    out = bytearray(data)
    pos = 0
    while pos < len(out):
        header = bytes(out[pos : pos + 24])
        for i in masked:
            if i < len(header):
                out[pos + i] = 0
        if len(header) < 24:
            break
        namlen = struct.unpack_from("<I", header, 16)[0]
        pos += 24 + namlen
    return bytes(out)


# The tree both sides serve: an in-memory provider and the same files on disk.
TREE: dict[str, bytes | None] = {
    "/a.txt": b"hello, mount\n",
    "/b.txt": b"b\n",
    "/d": None,
    "/d/x.txt": b"x\n",
    "/e": None,
}


def write_tree(root: Path, tree: Mapping[str, bytes | None] = TREE) -> Path:
    for path, data in sorted(tree.items()):
        target = root / path.lstrip("/")
        if data is None:
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    return root


# Spec 058: rows of spec 034's v1.4 write parity (`WRITE_PARITY`) whose grant answer is the host
# system's, asserted exactly per system (keyed by `sys.platform`), and the mount's answer, the same
# on every host. Windows's values were seen on GitHub's `windows-2025-vs2026` runner image and
# depend on it: there a folder renamed onto an empty folder succeeded too (`g`, no `d`), which
# another image or file system may refuse. A Windows grant renames a folder over a file (release
# run 39135024458, EXECUTED;
# wasmtime renames by `std::fs::rename`, READ), where POSIX and the mount answer ENOTDIR (54); so
# `e` is gone, `a.txt` is a folder and `shutil.copyfile` of it makes no `copy.txt`. A Windows grant
# also opens every file without `FILE_SHARE_DELETE` (wasmtime 49's `maybe_dir`, READ), so a
# `TemporaryFile` cannot unlink its open file and a `NamedTemporaryFile` cannot be `os.replace`d
# inside its `with`: each leaves a `tmp…` name, and there is no `final.bin`. Those two rows'
# grant answers are the host's errno, left out on Windows as before.
TEMPORARY = "<a tempfile name>"  # a listing slot that takes a name `tempfile` makes
TEMPORARY_NAME = re.compile(r"tmp[a-z0-9_]{8}")  # tempfile's prefix and its 8 random characters
_POSIX_LISTING = ["a.txt", "b.txt", "copy.txt", "copy2.txt", "cr.txt", "e", "final.bin", "g", "h",
                  "save.txt", "x.txt"]  # fmt: skip
WRITE_MOUNT: dict[str, object] = {
    "rename a folder over a file": ["errno", 54],
    "sorted listing": _POSIX_LISTING,
}
WRITE_BY_SYSTEM: dict[str, dict[str, object]] = {
    "rename a folder over a file": {"linux": ["errno", 54], "darwin": ["errno", 54], "win32": None},
    "sorted listing": {
        "linux": _POSIX_LISTING,
        "darwin": _POSIX_LISTING,
        "win32": ["a.txt", "b.txt", "copy2.txt", "cr.txt", "g", "h", "save.txt", TEMPORARY,
                  TEMPORARY, "x.txt"],
    },
}  # fmt: skip


def write_by_system(row: str, system: str) -> object:
    """The grant's answer to `row` on `system` (a `sys.platform`): a KeyError for a system the
    table does not name, so an unknown host fails rather than passes."""
    return WRITE_BY_SYSTEM[row][system]


def answer_matches(want: object, got: object) -> bool:
    """`want == got`, except that a `TEMPORARY` slot in a listing matches one name `tempfile`
    makes, whole (so a listing with the same names in the same places, and nothing else)."""
    if isinstance(want, list) and TEMPORARY in want:
        if not isinstance(got, list) or len(got) != len(want):
            return False
        return all(
            w == g or (w == TEMPORARY and isinstance(g, str) and bool(TEMPORARY_NAME.fullmatch(g)))
            for w, g in zip(want, got, strict=True)
        )
    return want == got


METHODS = ("stat", "list", "read", "write", "mkdir", "remove", "rmdir", "rename")
_UNSET = object()


class MemoryProvider:
    """A provider over an in-memory tree that counts its own calls by method (all eight, spec 034)
    and records every path it was given, and every write-half call whole in `log`. It follows the
    protocol's contract: `read` answers EISDIR for a folder and ENOTDIR when a parent is a file;
    the write half answers as Decision 2 of spec 034 says. `answers` overrides one method on one
    path: an `Errno` is answered, an exception is raised, a callable is called with the method's
    arguments. Thread-safe: one provider may serve concurrent calls."""

    def __init__(self, tree: Mapping[str, bytes | None] = TREE) -> None:
        from wasi_python import Errno, Stat

        self.Errno, self.Stat = Errno, Stat
        self.tree = dict(tree)
        self.calls = dict.fromkeys(METHODS, 0)
        self.paths: list[tuple[str, str]] = []
        self.log: list[tuple[Any, ...]] = []
        self.answers: dict[tuple[str, str], Any] = {}
        self._lock = threading.RLock()

    def _count(self, method: str, path: str, *more: Any) -> Any:
        """Count one call, and give its override (or `_UNSET`)."""
        with self._lock:
            self.calls[method] += 1
            self.paths.append((method, path))
            if method in METHODS[3:]:
                self.log.append((method, path, *more))
                if method == "rename":
                    self.paths.append((method, more[0]))
            answer = self.answers.get((method, path), _UNSET)
        if isinstance(answer, BaseException):
            raise answer
        if callable(answer) and not isinstance(answer, self.Errno):
            return answer(path, *more)
        return answer

    def total(self) -> int:
        return sum(self.calls.values())

    def writes(self, path: str | None = None) -> list[bytes]:
        """The data of every `write` call, in order (to one path, when given)."""
        return [e[2] for e in self.log if e[0] == "write" and (path is None or e[1] == path)]

    def _missing(self, path: str) -> Any:
        """ENOTDIR when an ancestor is a file, else ENOENT."""
        parts = path.strip("/").split("/")
        for i in range(1, len(parts)):
            ancestor = "/" + "/".join(parts[:i])
            if self.tree.get(ancestor, None) is not None:
                return self.Errno.ENOTDIR
            if ancestor not in self.tree:
                return self.Errno.ENOENT
        return self.Errno.ENOENT

    def _parent(self, path: str) -> Any:
        """None when the parent is a folder, else ENOENT or ENOTDIR."""
        parent = path.rsplit("/", 1)[0] or "/"
        if self._is_dir(parent):
            return None
        return self.Errno.ENOTDIR if parent in self.tree else self._missing(parent)

    def _is_dir(self, path: str) -> bool:
        return path == "/" or (path in self.tree and self.tree[path] is None)

    def _children(self, path: str) -> list[str]:
        prefix = path.rstrip("/") + "/"
        return [p for p in self.tree if p.startswith(prefix)]

    def stat(self, path: str) -> Any:
        if (answer := self._count("stat", path)) is not _UNSET:
            return answer
        with self._lock:
            if self._is_dir(path):
                return self.Stat("dir")
            if path in self.tree:
                return self.Stat("file", size=len(self.tree[path] or b""))
            return self._missing(path)

    def list(self, path: str) -> Any:
        if (answer := self._count("list", path)) is not _UNSET:
            return answer
        with self._lock:
            if path in self.tree and self.tree[path] is not None:
                return self.Errno.ENOTDIR
            if not self._is_dir(path):
                return self._missing(path)
            prefix = path.rstrip("/") + "/"
            names = []
            for p, data in sorted(self.tree.items()):
                rest = p[len(prefix) :] if p.startswith(prefix) else None
                if rest and "/" not in rest:
                    names.append((rest, "dir" if data is None else "file"))
            return names

    def read(self, path: str) -> Any:
        if (answer := self._count("read", path)) is not _UNSET:
            return answer
        with self._lock:
            if self._is_dir(path):
                return self.Errno.EISDIR
            if path in self.tree:
                return self.tree[path]
            return self._missing(path)

    # The write half (spec 034, Decision 2).

    def write(self, path: str, data: bytes) -> Any:
        if (answer := self._count("write", path, data)) is not _UNSET:
            return answer
        with self._lock:
            if self._is_dir(path):
                return self.Errno.EISDIR
            if (refused := self._parent(path)) is not None:
                return refused
            self.tree[path] = bytes(data)
            return None

    def mkdir(self, path: str) -> Any:
        if (answer := self._count("mkdir", path)) is not _UNSET:
            return answer
        with self._lock:
            if self._is_dir(path) or path in self.tree:
                return self.Errno.EEXIST
            if (refused := self._parent(path)) is not None:
                return refused
            self.tree[path] = None
            return None

    def remove(self, path: str) -> Any:
        if (answer := self._count("remove", path)) is not _UNSET:
            return answer
        with self._lock:
            if self._is_dir(path):
                return self.Errno.EISDIR
            if path not in self.tree:
                return self._missing(path)
            del self.tree[path]
            return None

    def rmdir(self, path: str) -> Any:
        if (answer := self._count("rmdir", path)) is not _UNSET:
            return answer
        with self._lock:
            if path not in self.tree:
                return self._missing(path)
            if self.tree[path] is not None:
                return self.Errno.ENOTDIR
            if self._children(path):
                return self.Errno.ENOTEMPTY
            del self.tree[path]
            return None

    def rename(self, src: str, dst: str) -> Any:
        if (answer := self._count("rename", src, dst)) is not _UNSET:
            return answer
        with self._lock:
            if src not in self.tree:
                return self._missing(src)
            if (refused := self._parent(dst)) is not None:
                return refused
            folder = self.tree[src] is None
            if dst == src:
                return None
            if folder and dst.startswith(src + "/"):
                return self.Errno.EINVAL
            if dst in self.tree:
                if not folder and self.tree[dst] is None:
                    return self.Errno.EISDIR
                if folder and self.tree[dst] is not None:
                    return self.Errno.ENOTDIR
                if folder and self._children(dst):
                    return self.Errno.ENOTEMPTY
                del self.tree[dst]
            moved = {src: self.tree.pop(src)}
            for p in self._children(src):
                moved[dst + p[len(src) :]] = self.tree.pop(p)
            for p, data in moved.items():
                self.tree[p if p != src else dst] = data
            return None


def grant_raw(folders: list[tuple[Path, str, bool]], wat: str | None = None) -> Raw:
    """The raw module on plain wasmtime, with each (host folder, guest path, writable) preopened
    from 3 up: what a grant answers."""
    import wasmtime

    engine = wasmtime.Engine()
    store = wasmtime.Store(engine)
    config = wasmtime.WasiConfig()
    for host, guest, writable in folders:
        config.preopen_dir(str(host), guest, writable)
    store.set_wasi(config)
    linker = wasmtime.Linker(engine)
    linker.define_wasi()
    instance = linker.instantiate(store, wasmtime.Module(engine, wat or raw_wat()))
    return Raw(store, instance.exports(store))


class _OnStack:
    """A raw module whose every export runs with its call on this thread's stack."""

    call: Any
    store: Any

    @contextmanager
    def entered(self) -> Iterator[None]:
        """The call on this thread's stack for one export; a stop it recorded is raised as
        `Ends`, and the call is made live again for the next row."""
        from wasi_python import runner

        stack = runner._stack()
        stack.append(self.call)
        try:
            yield
        finally:
            stack.remove(self.call)
        stopped = self.call.stopped
        if stopped is not None:
            self.call.stopped = None
            self.store.set_epoch_deadline(2**40)
            raise Ends(str(stopped))


class Mounted(_OnStack):
    """The raw module on the runner's mount linker, with a call on the thread's stack around
    every export: a mount of `provider` at `guest` (preopen 3, on an empty placeholder folder;
    writable when `writable`), then each (host folder, guest path, writable) in `folders` from
    4 up."""

    def __init__(
        self,
        provider: Any,
        placeholder: Path,
        *,
        guest: str = "/m",
        folders: list[tuple[Path, str, bool]] = (),  # type: ignore[assignment]
        file_calls: int | None = None,
        staging: int = 1 << 30,
        fuel: int | None = None,
        wat: str | None = None,
        cancel: Any = None,
        stop_at: int | None = None,
        writable: bool = False,
    ) -> None:
        import wasmtime

        from wasi_python import Mount, runner
        from wasi_python.mounts import _Files

        config = wasmtime.Config()
        config.epoch_interruption = True
        config.consume_fuel = fuel is not None
        self.engine = engine = wasmtime.Engine(config)
        self.store = store = wasmtime.Store(engine)
        store.set_epoch_deadline(2**40)
        if fuel is not None:
            store.set_fuel(runner.UNMETERED)
        wasi = wasmtime.WasiConfig()
        wasi.preopen_dir(str(placeholder), guest, False)
        for host, path, rw in folders:
            wasi.preopen_dir(str(host), path, rw)
        store.set_wasi(wasi)
        others = [path for _, path, _ in folders]
        self.table = _Files(
            [(Mount(provider, guest, writable=writable), 3)],
            others,
            file_calls,
            staging,
            fuel is not None,
            engine,
        )
        self.call = runner._Call(store, None, _NoWaits(), 0, cancel, stop_at, self.table)
        self.linker = runner._mount_linker(wasmtime, engine)
        self.plain = runner._linker(wasmtime, engine)
        self.instance = self.linker.instantiate(store, wasmtime.Module(engine, wat or raw_wat()))
        stack = runner._stack()
        stack.append(self.call)
        try:
            self.table.bind(wasmtime, store, self.plain, self.instance)
        finally:
            stack.remove(self.call)
        if fuel is not None:
            store.set_fuel(fuel)
        self.raw = Raw(store, self.instance.exports(store), self.entered)


class Guarded(_OnStack):
    """The raw module on the runner's guard linker (spec 048), with its call on the thread's
    stack around every export: what a call without mounts answers. Each (host folder, guest
    path, writable) in `folders` is preopened from 3 up and served by wasmtime, but for the two
    calls the guard shadows (`fd_readdir`, `path_rename`), which a guard table (no mounts)
    forwards with the fixes of wasmtime 49.0.2 and 49.0.3."""

    def __init__(
        self,
        folders: list[tuple[Path, str, bool]],
        *,
        fuel: int | None = None,
        wat: str | None = None,
    ) -> None:
        import wasmtime

        from wasi_python import runner
        from wasi_python.mounts import _Files

        config = wasmtime.Config()
        config.epoch_interruption = True
        config.consume_fuel = fuel is not None
        self.engine = engine = wasmtime.Engine(config)
        self.store = store = wasmtime.Store(engine)
        store.set_epoch_deadline(2**40)
        if fuel is not None:
            store.set_fuel(runner.UNMETERED)
        wasi = wasmtime.WasiConfig()
        for host, path, writable in folders:
            wasi.preopen_dir(str(host), path, writable)
        store.set_wasi(wasi)
        others = [path for _, path, _ in folders]
        self.table = _Files([], others, None, 1 << 30, fuel is not None, engine)
        self.call = runner._Call(store, None, _NoWaits(), 0, None, None, self.table)
        self.linker = runner._guard_linker(wasmtime, engine)
        self.plain = runner._linker(wasmtime, engine)
        self.instance = self.linker.instantiate(store, wasmtime.Module(engine, wat or raw_wat()))
        stack = runner._stack()
        stack.append(self.call)
        try:
            self.table.bind(wasmtime, store, self.plain, self.instance)
        finally:
            stack.remove(self.call)
        if fuel is not None:
            store.set_fuel(fuel)
        self.raw = Raw(store, self.instance.exports(store), self.entered)


class _NoWaits:
    def wait(self, seconds: float) -> None:
        raise AssertionError("no wait expected")
