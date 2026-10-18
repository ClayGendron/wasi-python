"""Mounts (specs 032 and 034): a provider's files at a guest path, served from embedder code.

    from wasi_python import Mount, run

    done = run(argv, mounts=[Mount(files, "/work")])
    done = run(argv, mounts=[Mount(store, "/work", writable=True)])

A provider answers three methods on normalized, absolute paths (`/` is the mount itself): `stat`,
`list` and `read`, each returning a value or an `Errno`, or raising an `OSError` whose errno (by
name) or, with no errno, whose class names one (spec 061). A writable mount's provider also
answers the write half (`write`, `mkdir`, `remove`, `rmdir`, `rename`), each `None` or an
`Errno`, raised the same way; a file's bytes are staged in the runner and handed over whole at
open (a create or truncation), at close, at sync and at the call's ending. The runner owns every
descriptor, offset, flag, cookie and pointer; the provider sees only normalized paths.

How it works: on a call with mounts, the guest's 29 preview1 calls that act on a descriptor and
are not forward-safe are shadowed (`SHADOWED`). Each finds its call on the thread's stack (spec
011). A call that names a number in the call's mount table is served here; any other is forwarded
to wasmtime's own WASI through a small trampoline instantiated on the guest's memory, by
`wasmtime_func_call` on the caller's context, fuel-neutral. Each mount is preopened on an empty,
read-only placeholder folder the runner owns, so wasi-libc's preopen scan finds it; a file or
folder opened in a mount gets a number from 2**30 up, which wasmtime never reaches.

A call without mounts shadows only the two calls in `GUARDED` (spec 048), through a table with no
mounts, so both are forwarded, and every forward of them carries wasmtime 49.0.2's and 49.0.3's
fixes, which wasmtime 49.0.0, the newest wasmtime-py, lacks.

wasmtime-py is imported only inside functions, so the package imports without the `run` extra.
"""

from __future__ import annotations

import ctypes
import enum
import errno as _host_errno
import heapq
import struct
import sys
import types
from array import array
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from .runner import _Call


class Errno(enum.IntEnum):
    """An answer a provider gives instead of a value: WASI preview1's numbers, which the guest
    sees unchanged, each as the `OSError` of that errno. The set is closed: no success, nothing
    that makes the guest's C library retry, and nothing that describes the guest's own
    arguments."""

    # The numbers: READ, wasi-libc's wasip1.h (spec 032).

    EACCES = 2
    EBUSY = 10
    ECANCELED = 11
    EDQUOT = 19
    EEXIST = 20
    EFBIG = 22
    EINVAL = 28
    EIO = 29
    EISDIR = 31
    ENAMETOOLONG = 37
    ENOENT = 44
    ENOSPC = 51
    ENOSYS = 52
    ENOTDIR = 54
    ENOTEMPTY = 55
    ENOTSUP = 58
    EPERM = 63
    EROFS = 69
    ESTALE = 72
    ETIMEDOUT = 73
    EXDEV = 75


@dataclass(frozen=True)
class Stat:
    """What a provider's `stat` answers for a path.

    Attributes:
        kind: "file" or "dir".
        size: The size in bytes, 0 to 2**63 - 1. A bool is refused.
        mtime_ns: The modification time in nanoseconds, 0 to 2**64 - 1. A bool is refused.
    """

    kind: str
    size: int = 0
    mtime_ns: int = 0


class FileProvider(Protocol):
    """What a mount's provider answers, for type checkers: a read-only mount's three methods.

    Paths are absolute within the mount (/ is the mount itself) and normalized by the runner.
    A provider answers each call with a value or an `Errno`, or raises an `OSError`: its errno,
    matched by name on this host, or with no errno its class (`FileNotFoundError`,
    `FileExistsError`, `IsADirectoryError`, `NotADirectoryError`, `PermissionError`,
    `TimeoutError`), is then the answer, as the `Errno` of that name would be. Any other
    exception, an errno outside `Errno`, or an answer outside the protocol gives the guest EIO
    and adds a `FileFault` to the result; one that is not an `Exception` stops the call and is
    raised from `run`.
    """

    def stat(self, path: str) -> Stat | Errno:
        """What the path is: a `Stat`, whose kind for / must be "dir", or an `Errno`.

        Args:
            path: An absolute path within the mount.
        """

    def list(self, path: str) -> Iterable[tuple[str, str]] | Errno:
        """A folder's entries, as (name, kind) pairs, or an `Errno`.

        A name is one path component: not empty, . or .., no / or NUL, at most 255 bytes of
        UTF-8, and no repeats. A kind is "file" or "dir".

        Args:
            path: An absolute path within the mount.
        """

    def read(self, path: str) -> bytes | bytearray | memoryview | Errno:
        """A file's whole content, or an `Errno`: EISDIR when the path itself is a folder, and
        ENOTDIR when a parent is a file.

        Args:
            path: An absolute path within the mount.
        """


class WritableFileProvider(FileProvider, Protocol):
    """What a writable mount's provider answers, for type checkers: the read half and the
    write half.

    Each method of the write half answers `None` for success or an `Errno`: POSIX's contract,
    in preview1's numbering. An `OSError` it raises is a refusal when it names a member, as for
    the read half. A file's bytes are staged by the runner and handed over whole at
    open (a create or a truncation), at close, at sync and at the call's ending.
    """

    # spec 034
    def write(self, path: str, data: bytes) -> None | Errno:
        """Replace a file's whole content, creating the file if it is missing.

        A create or a truncation at open reaches the provider as `write(path, b"")`.

        Args:
            path: An absolute path within the mount.
            data: The file's new content, a copy the provider may keep.
        """

    def mkdir(self, path: str) -> None | Errno:
        """Make a folder.

        Args:
            path: An absolute path within the mount.
        """

    def remove(self, path: str) -> None | Errno:
        """Remove a file; EISDIR for a folder.

        Args:
            path: An absolute path within the mount.
        """

    def rmdir(self, path: str) -> None | Errno:
        """Remove a folder; ENOTEMPTY for one that holds anything.

        Args:
            path: An absolute path within the mount.
        """

    def rename(self, src: str, dst: str) -> None | Errno:
        """Move a file or folder within the mount, by POSIX's rule for replacing `dst`.

        Args:
            src: The absolute path, within the mount, of what moves.
            dst: The absolute path, within the mount, it moves to.
        """


@dataclass(frozen=True)
class Mount:
    """A provider whose files the guest sees at a guest path, read-only unless
    `writable=True`.

    `run` checks every mount before any work.

    Attributes:
        provider: The provider: a `FileProvider`, or a `WritableFileProvider` for a writable
            mount.
        guest: Where the guest sees it: an absolute guest path, or / for the guest's whole
            filesystem (not with `root=`).
        writable: Whether the guest may write there; it needs the provider's write half.
            Keyword-only.
    """

    # spec 032; writable: spec 034

    provider: FileProvider
    guest: str
    writable: bool = field(default=False, kw_only=True)


@dataclass(frozen=True)
class FileFault:
    """One provider call that raised an exception that is not an answer, or answered outside its
    protocol.

    Attributes:
        method: The provider's method, such as "read".
        path: The path it was given; a rename's source.
        error: The exception's type and first line, or "bad answer: <type>".
    """

    method: str
    path: str
    error: str


@dataclass(frozen=True)
class RefusedWrite:
    """One write-half call the provider did not accept, or a write-back the runner owed and did
    not make.

    Attributes:
        mount: The mount's guest path.
        method: The provider's method, such as "write".
        paths: The provider path, or (src, dst) for a rename.
        errno: The provider's answer, or EIO for a fault or the limit.
        at: When: "open", "call", "close", "sync" or "exit".
        cause: Why: "refused", "fault" or "limit".
    """

    # spec 034, Decision 11

    mount: str
    method: str
    paths: tuple[str, ...]
    errno: Errno
    at: str
    cause: str


@dataclass(frozen=True)
class FileRecord:
    """A call's provider calls, counted. No times, and no exception objects, so a result holds
    no frame of the call.

    Attributes:
        calls: Each method's count, all eight methods, zeros included.
        faults: The first 1,000 faults.
        refused: The first 1,000 refused writes.
        refused_total: How many writes were refused in all, so a cut list says so.
    """

    calls: Mapping[str, int]
    faults: tuple[FileFault, ...] = ()
    refused: tuple[RefusedWrite, ...] = ()
    refused_total: int = 0


# A provider's OSError (spec 061): the answer of its errno, matched by name, never by number,
# which differs by host (ENOENT is 2 on every host and 2 is preview1's EACCES). One code path for
# every host: the table is the host's own errno module, read by the guest's names.

# A host name the guest's C library spells as a member (wasi-libc: EOPNOTSUPP is ENOTSUP).
_ERRNO_ALIASES = {"EOPNOTSUPP": "ENOTSUP"}


def _errno_table(names: Mapping[str, object]) -> dict[int, Errno]:
    """Each host errno number, from an `errno`-like namespace, to the member of the same name.
    A name the host lacks is skipped; only plain ints count; the first member keeps a number."""
    table: dict[int, Errno] = {}
    pairs = [(member.name, member) for member in Errno]
    pairs += [(alias, Errno[name]) for alias, name in _ERRNO_ALIASES.items()]
    for name, member in pairs:
        number = names.get(name)
        if type(number) is int:
            table.setdefault(number, member)
    return table


_HOST_ERRNO = _errno_table(vars(_host_errno))
# With no errno at all: the class, PEP 3151's name for exactly one member, first match in order.
_RAISED = (
    (FileNotFoundError, Errno.ENOENT),
    (FileExistsError, Errno.EEXIST),
    (IsADirectoryError, Errno.EISDIR),
    (NotADirectoryError, Errno.ENOTDIR),
    (PermissionError, Errno.EACCES),
    (TimeoutError, Errno.ETIMEDOUT),
)
_ERRNO_SLOT = OSError.__dict__["errno"]  # the slot itself, past any subclass's property


def _raised(e: BaseException) -> Errno | None:
    """The member a provider's exception stands for, or None (a fault). Total, and it runs no
    provider code: the type by `type()`, the errno through `OSError`'s own slot, an exact int,
    a lookup in a dict of ints; the class only when the slot is None, by `issubclass` against
    built-in classes. A present errno that names no member is a fault, whatever the class."""
    try:
        kind = type(e)
        if not issubclass(kind, OSError):
            return None
        number = _ERRNO_SLOT.__get__(e, kind)
        if number is None:
            for base, member in _RAISED:
                if issubclass(kind, base):
                    return member
            return None
        if type(number) is int:
            return _HOST_ERRNO.get(number)
        return None
    except Exception:
        return None


# The 29 preview1 calls that act on a descriptor and are not forward-safe, with their raw
# parameters (the result is one i32): every call the guest's file traffic can name a provider
# number in. fd_renumber, fd_allocate and fd_fdstat_set_rights are not imported by today's
# binaries; they are shadowed so a later binary cannot reach a provider number unseen.
SIGNATURES: dict[str, tuple[str, ...]] = {
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
}
SHADOWED = tuple(SIGNATURES)
# Reviewed: on a provider number each answers EBADF (the number is not in wasmtime's table), or,
# for poll_oneoff (the runner's own), as for any descriptor; on a mount's preopen wasmtime answers
# as for a grant's (spec 032, Decision 1).
FORWARD_SAFE = (
    "fd_prestat_get",
    "fd_prestat_dir_name",
    "sock_accept",
    "sock_recv",
    "sock_send",
    "sock_shutdown",
    "poll_oneoff",
)

# The guard (spec 048). wasmtime 49.0.0 carries two advisories that reach a guest, and no
# wasmtime-py on PyPI carries a wasmtime with their fixes yet:
# - GHSA-96f6-r43r-8c24 (fixed in wasmtime 49.0.2): fd_readdir copies up to three bytes of
#   uninitialized host memory into each entry's padding. A forwarded listing is zeroed there.
# - GHSA-m9f7-9w4p-gv38 (fixed in wasmtime 49.0.3): path_rename puts a source's trailing slash
#   back before renameat, and macOS and FreeBSD then follow a symbolic link out of the sandbox.
#   A forwarded rename with a trailing slash on either path needs a source that is a folder,
#   judged without following its own link, and is forwarded by the plain names.
# A call without mounts shadows these two only; a call with mounts forwards them the same way.
# Each guard goes when the published floor admits only patched versions (tests/checks/
# test_rules.py, test_the_rename_and_readdir_guard_match_the_floor).
GUARDED = ("fd_readdir", "path_rename")
# What the guard asks wasmtime on its own page, never in the guest's memory: the rename's source
# type, and a listing again when the guest's `used` pointer lies over its own listing.
PRIVATE = ("path_filestat_get", "fd_readdir")
STAT_PATH = 64  # the source path's offset in the stat trampoline's page; the filestat is at 0

PROVIDER_BASE = 2**30  # provider numbers start here; wasmtime's own never reach it
MAX_MOUNT_FILES = 1024  # open provider numbers per call
MAX_PATH = 4096  # bytes; a longer path is ENAMETOOLONG, unread
MAX_NAME = 255  # bytes in one path component, and in one listed name
MAX_IOVECS = 1024
PREAD_CHUNK = 64 * 1024  # wasmtime 49's MAX_READ_SIZE_ALLOC, which fd_pread reads by
FAULTS_KEPT = 1000
REFUSED_KEPT = 1000
STAGING_CEILING = 4 << 30  # wasm32's own ceiling, when memory_bytes is None
FUEL_ALLOWANCE = 1000  # covers the trampoline's few instructions; set back after each forward
FUEL_MAX = 2**63 - 1
METHODS = ("stat", "list", "read", "write", "mkdir", "remove", "rmdir", "rename")
WRITE_HALF = METHODS[3:]  # a writable mount's provider has each of these (spec 034)

MASK32, MASK64 = 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF
# preview1 errno values the runner answers itself
EBADF, EBUSY, ECANCELED, EEXIST, EFAULT, EFBIG, EILSEQ, EINVAL, EIO = (
    8,
    10,
    11,
    20,
    21,
    22,
    25,
    28,
    29,
)
EISDIR, EMFILE, ENAMETOOLONG, ENOENT, ENOTDIR, ENOTSUP, EPERM, ETIMEDOUT, EXDEV = (
    31,
    33,
    37,
    44,
    54,
    58,
    63,
    73,
    75,
)
DIRECTORY, REGULAR_FILE = 3, 4  # filetypes
O_CREAT, O_DIRECTORY, O_EXCL, O_TRUNC = 1, 2, 4, 8
APPEND, DSYNC, NONBLOCK, RSYNC, SYNC = 1, 2, 4, 8, 16
ATIM, ATIM_NOW, MTIM, MTIM_NOW = 1, 2, 4, 8
FD_READ, FD_SEEK, FD_WRITE, FD_READDIR = 1 << 1, 1 << 2, 1 << 6, 1 << 14
PATH_FILESTAT_SET_SIZE, FD_FILESTAT_SET_SIZE = 1 << 19, 1 << 22
RIGHTS = (1 << 30) - 1  # wasmtime 49's Rights::all()
FILE_RIGHTS = RIGHTS & ~FD_WRITE  # a file opened read-only, as wasmtime reports it
OFFSET_TOP = 2**63  # an offset, a position or a size from here on: the host's EINVAL
# Which trailing `/` makes a rename served in a writable mount need a folder source: (the
# source's, the destination's). Either path's counts, as wasmtime 49.0.3's rule, which spec 048
# carries for a grant's rename (GHSA-m9f7-9w4p-gv38): the parity's reference is a guarded grant
# (spec 034, the build review, F3). The source is judged by one `stat`, after the runner's own
# answers (the path rules, EBUSY, EINVAL) and before the provider's `rename`: for a slash-named
# rename that is the guard's order, the stat's errno or ENOTDIR before anything is renamed.
RENAME_SLASH_NEEDS_FOLDER = (True, True)
ZEROS = bytes(1 << 16)  # the block a buffer grows from (the build review, F4)
DIR_RIGHTS = RIGHTS & ~(FD_SEEK | FD_WRITE | PATH_FILESTAT_SET_SIZE | FD_FILESTAT_SET_SIZE)
FILESTAT = "<QQB7xQQQQQ"  # dev, ino, filetype, nlink, size, atim, mtim, ctim: 64 bytes
FDSTAT = "<BxH4xQQ"  # filetype, flags, rights base and inheriting: 24 bytes
DIRENT = "<QQIB3x"  # d_next, d_ino, d_namlen, d_type: 24 bytes


def trampoline_wat() -> str:
    """The forwarders: each imports one of wasmtime's own calls and exports a function that calls
    it, beside the guest's memory re-exported as `memory`, which wasmtime's WASI reads through
    the calling instance (memo finding 3)."""
    lines = ["(module"]
    for name, params in SIGNATURES.items():
        sig = f"(param {' '.join(params)}) (result i32)"
        lines.append(f'  (import "wasi_snapshot_preview1" "{name}" (func ${name} {sig}))')
    lines.append('  (import "env" "memory" (memory 0))')
    lines.append('  (export "memory" (memory 0))')
    for name, params in SIGNATURES.items():
        sig = f"(param {' '.join(params)}) (result i32)"
        gets = " ".join(f"(local.get {i})" for i in range(len(params)))
        lines.append(f'  (func (export "{name}") {sig} (call ${name} {gets}))')
    lines.append(")")
    return "\n".join(lines)


def stat_trampoline_wat() -> str:
    """The guard's own trampoline (spec 048, Decision 2): it imports wasmtime's calls in
    `PRIVATE` and defines and exports its own memory, one page that the host grows when a
    listing needs it, which wasmtime's WASI reads and writes through, so what the guard asks
    never touches a byte of the guest's."""
    lines = ["(module"]
    for name in PRIVATE:
        sig = f"(param {' '.join(SIGNATURES[name])}) (result i32)"
        lines.append(f'  (import "wasi_snapshot_preview1" "{name}" (func ${name} {sig}))')
    lines.append('  (memory (export "memory") 1)')
    for name in PRIVATE:
        params = SIGNATURES[name]
        sig = f"(param {' '.join(params)}) (result i32)"
        gets = " ".join(f"(local.get {i})" for i in range(len(params)))
        lines.append(f'  (func (export "{name}") {sig} (call ${name} {gets}))')
    lines.append(")")
    return "\n".join(lines)


def _ends(message: str) -> BaseException:
    """What wasmtime gives a guest that passes an argument its ABI cannot carry (a flag or enum
    value it does not define, an integer out of its type's range, a misaligned pointer): an
    error that ends the run. Raised to the shared function, which records it as the stop."""
    import wasmtime

    error = wasmtime.WasmtimeError(message)
    error.abi = True  # type: ignore[attr-defined]
    return error


def _unsigned(value: int, top: int, name: str) -> int:
    """A raw argument as wiggle converts it: the i32 or i64 taken as signed, which must fit the
    WASI type, or the run ends."""
    if not 0 <= value <= top:
        raise _ends("out of range integral type conversion attempted")
    return value


def _flags(value: int, bits: int, top: int, name: str) -> int:
    value = _unsigned(value, top, name)
    if value & ~bits:
        raise _ends(f"Invalid flag value {name}")
    return value


def _enum(value: int, last: int, name: str) -> int:
    value = _unsigned(value, 0xFF, name)
    if value > last:
        raise _ends(f"Invalid enum value {name}")
    return value


def _lookup(value: int) -> int:
    return _flags(value, 1, 0x7FFFFFFF, "Lookupflags")


def _rights(value: int) -> int:
    return _flags(value, RIGHTS, 2**63 - 1, "Rights")


_Listing = tuple[bytearray, array]  # a folder's encoded preview1 entries and their offsets


@dataclass
class _Mounted:
    """One mount as a call holds it."""

    provider: Any
    guest: str
    dev: int  # _siphash13 of the guest path
    nested: tuple[str, ...]  # more specific preopens, as paths within this mount
    writable: bool = False  # the embedder said so (spec 034); else no write-half call is made


@dataclass
class _Open:
    """A descriptor in the mount table: a mount's own preopen, or a provider file or folder."""

    mount: _Mounted
    path: str  # within the mount, normalized
    kind: str  # "file" or "dir"
    preopen: bool = False
    data: bytes | bytearray = b""  # a file's staged bytes; its buffer, if it may write
    position: int = 0
    append: bool = False
    nonblock: bool = False
    listing: _Listing | None = None  # the encoded entries and where each starts, dots first
    fresh: bool = False  # the listing has not yet served a pass from cookie 0
    held: int = 0  # staged bytes this descriptor holds
    readable: bool = True  # wasmtime's open mode: FD_READ asked for, or not opened to write
    writable: bool = False  # it may write (spec 034): CREAT or TRUNC, or FD_WRITE asked for
    dirty: bool = False  # the provider has not been given these bytes
    unlinked: bool = False  # the guest removed or replaced its path in this call (Decision 7)


@dataclass
class _Forwards:
    """The trampoline's function handles and argument arrays, for one call's store only: a
    handle of one store used with another store's context aborts the process. `stat` and
    `page` are the guard's own trampoline's calls (`PRIVATE`) and its memory (spec 048)."""

    funcs: dict[str, Any]
    stat: dict[str, Any] = field(default_factory=dict)
    page: Any = None
    slots: dict[str, tuple[Any, Any, Any]] = field(default_factory=dict)


class _Memory:
    """The guest's memory for one host call: every pointer and length is checked against its
    size before a byte is read or written (Decision 7)."""

    def __init__(self, caller: Any) -> None:
        import wasmtime

        self.caller = caller
        memory = caller.get("memory")
        self.memory = memory if isinstance(memory, wasmtime.Memory) else None
        self.size = 0 if self.memory is None else self.memory.data_len(caller)

    def fits(self, ptr: int, length: int) -> bool:
        return self.memory is not None and ptr + length <= self.size

    def read(self, ptr: int, length: int) -> bytes:
        return bytes(self.memory.read(self.caller, ptr, ptr + length)) if length else b""

    def write(self, ptr: int, data: bytes) -> None:
        if data:
            self.memory.write(self.caller, data, ptr)


def _aligned(ptr: int, align: int) -> None:
    if ptr % align:
        raise _ends(f"Pointer not aligned to {align}")


class _Files:
    """One call's mount table and provider calls (spec 032). Called by the 29 shadows through
    the shared function with the shadowed call's name; it answers an errno, or raises a
    wasmtime error that ends the run (a forward's, or an ABI error as wasmtime gives it), or a
    provider's BaseException, which the shared function records as the call's stop."""

    def __init__(
        self,
        mounts: list[tuple[Mount, int]],
        others: list[str],
        file_calls: int | None,
        staging: int,
        metered: bool,
        engine: Any = None,
    ) -> None:
        from . import runner

        self._runner = runner
        self.mounts: list[_Mounted] = []
        self.table: dict[int, _Open] = {}
        for mount, number in mounts:
            nested = tuple(
                g if mount.guest == "/" else g[len(mount.guest) :]
                for g in others + [m.guest for m, _ in mounts]
                if g != mount.guest
                and (g.startswith(mount.guest + "/") or (mount.guest == "/" and g != "/"))
            )
            mounted = _Mounted(
                mount.provider,
                mount.guest,
                runner._siphash13(mount.guest.encode()),
                nested,
                mount.writable is True,
            )
            self.mounts.append(mounted)
            self.table[number] = _Open(mounted, "/", "dir", preopen=True)
        self.limit, self.staging, self.metered = file_calls, staging, metered
        self.engine = engine
        self.calls = dict.fromkeys(METHODS, 0)
        self.total = 0
        self.faults: list[FileFault] = []
        self.refused: list[RefusedWrite] = []
        self.refused_total = 0
        self.staged = 0
        self.opened = 0  # provider numbers in use, owed ones included
        self.free: list[int] = []
        # Closed for the guest, written back at the ending (spec 034, Decision 5): out of `table`
        # (so no call finds them; N2) and out of `free` (so no open reuses the number).
        self.owed: dict[int, _Open] = {}
        self.next = PROVIDER_BASE
        self.forwards: _Forwards | None = None
        # a forward's own error, or an ABI error the runner raised, and the guest's fuel then
        self.stop_fuel: tuple[BaseException, int] | None = None
        self.call: _Call | None = None

    def record(self) -> FileRecord:
        return FileRecord(
            types.MappingProxyType(dict(self.calls)),
            tuple(self.faults),
            tuple(self.refused),
            self.refused_total,
        )

    def walk(self) -> None:
        """The ending's write-backs (spec 034, Decision 8), made after the guest has stopped by
        any ending that returns a result, on the call's thread, outside every host function:
        one `write` for each dirty buffer of a writable mount that is not unlinked, owed buffers
        included, in ascending provider number. Its own counted call path, never `_ask`: no
        cancel or deadline check (the guest is gone), never `call.ended` or the epoch or the
        fuel. Bounded by construction: at most MAX_MOUNT_FILES buffers, the staging bound in
        bytes, and the file calls left; a write-back past the limit is recorded, not made. It
        makes no call once the interpreter is exiting or a Ctrl-C is pending: no result will
        carry a record then, and provider code must not run."""
        r = self._runner
        for number in sorted([*self.table, *self.owed]):
            entry = self.table[number] if number in self.table else self.owed[number]
            if entry.kind != "file" or not entry.dirty or entry.unlinked:
                continue
            if r._hook["exiting"] or (r._ctrl_c_watched() and r._ctrl_c["pending"]):
                return
            paths = (entry.path,)
            if self.limit is not None and self.total >= self.limit:
                self._refuse(entry.mount, "write", paths, Errno.EIO, "exit", "limit")
            else:
                self._made(entry.mount, "write", "exit", paths, (bytes(entry.data),))
            entry.dirty = False

    def release(self) -> None:
        """Drop what the call held once it has ended (the build review, F3): the staged files
        and listings, the trampoline's handles and the link back to the call, so nothing waits
        for the cyclic collector."""
        self.table.clear()
        self.owed.clear()
        self.mounts.clear()
        self.forwards = None
        self.stop_fuel = None
        self.call = None
        self.staged = 0

    # The trampoline (Decision 1).

    def bind(self, wt: Any, store: Any, plain: Any, instance: Any) -> None:
        """Instantiate the trampoline on the guest's memory with wasmtime's own calls from
        `plain` (today's linker), and the stat trampoline on its own page (spec 048). After
        the guest, before the fuel cap and `_initialize`."""
        module = self._runner._trampoline_module(wt, self.engine)
        imports = [plain.get(store, "wasi_snapshot_preview1", name) for name in SIGNATURES]
        imports.append(instance.exports(store)["memory"])
        exports = wt.Instance(store, module, imports).exports(store)
        stat_module = self._runner._stat_trampoline_module(wt, self.engine)
        stat_imports = [plain.get(store, "wasi_snapshot_preview1", name) for name in PRIVATE]
        stat = wt.Instance(store, stat_module, stat_imports).exports(store)
        self.forwards = _Forwards(
            {name: exports[name]._func for name in SIGNATURES},
            {name: stat[name]._func for name in PRIVATE},
            stat["memory"],
        )

    def forward(self, caller: Any, name: str, args: tuple[int, ...], stat: bool = False) -> int:
        """wasmtime's own answer, on the caller's context, never through `Func.__call__` (whose
        exception slot is process-wide). Fuel-neutral on a metered call: read, raised by the
        allowance, and set back in a `finally` before any trap or error is raised. `stat`
        forwards one of `PRIVATE` through the guard's own trampoline, on its page (spec 048)."""
        from wasmtime import Trap, WasmtimeError, _ffi

        if self.forwards is None:
            return EBADF  # no trampoline yet: nothing of wasmtime's can be reached
        key = "stat:" + name if stat else name  # the guard trampoline's own slots (N2)
        slot = self.forwards.slots.get(key)
        if slot is None:
            types = SIGNATURES[name]
            params = (_ffi.wasmtime_val_t * len(types))()
            for i, kind in enumerate(types):
                kinds = _ffi.WASMTIME_I32 if kind == "i32" else _ffi.WASMTIME_I64
                params[i].kind = kinds.value
            func = self.forwards.stat[name] if stat else self.forwards.funcs[name]
            slot = (func, params, (_ffi.wasmtime_val_t * 1)())
            self.forwards.slots[key] = slot
        func, params, results = slot
        for i, (kind, value) in enumerate(zip(SIGNATURES[name], args, strict=True)):
            if kind == "i32":
                params[i].of.i32 = value
            else:
                params[i].of.i64 = value
        context = caller._context()
        before = _get_fuel(context) if self.metered else None
        trap = ctypes.POINTER(_ffi.wasm_trap_t)()
        try:
            if before is not None:
                _set_fuel(context, min(before + FUEL_ALLOWANCE, FUEL_MAX))
            error = _ffi.wasmtime_func_call(
                context, ctypes.byref(func), params, len(args), results, 1, ctypes.byref(trap)
            )
        finally:
            if before is not None:
                _set_fuel(context, before)
        if trap or error:
            raised = WasmtimeError._from_ptr(error) if error else None
            if trap:
                raised = Trap._from_ptr(trap)  # owns and frees it; an error beside it is freed
            assert raised is not None
            if before is not None:
                self.stop_fuel = (raised, before)
            raise raised
        return results[0].of.i32

    # Dispatch.

    def __call__(self, caller: Any, name: str, *args: int) -> int:
        try:
            return getattr(self, "_" + name)(caller, *args)
        except BaseException as e:
            if self.metered and getattr(e, "abi", False):
                # An ABI error ends the run where a grant's does, with the fuel then (served
                # code spends none), as a forward's error keeps it (the build review, F4.2).
                self.stop_fuel = (e, _get_fuel(caller._context()))
            raise

    def _entry(self, fd: int) -> _Open | None:
        return self.table.get(fd & MASK32)

    # The provider (Decisions 3, 4, 8 and 10).

    def _ask(self, caller: Any, mount: _Mounted, method: str, *args: Any) -> tuple[int, Any]:
        """One provider call, counted, or the errno that stops it first: the call's cancel, its
        deadline, then the file-call limit. (0, answer) when the provider answered."""
        if errno := self._gate(caller):
            return errno, None
        return self._invoke(mount, method, args)

    def _gate(self, caller: Any) -> int:
        """0, or the errno that stops a provider call while the guest runs (Decision 10 of spec
        032): the call's cancel, its deadline, then the file-call limit, which names the end."""
        r, call = self._runner, self.call
        if call is not None and call.cancel is not None and call.cancel.is_set():
            r._epoch_now(caller)  # named "cancelled" by the epoch callback at the next entry
            return ECANCELED
        if call is not None and call.stop_at is not None:
            if r._epoch_ticker.count() >= call.stop_at:
                r._epoch_now(caller)  # an interrupt at the next entry: "deadline"
                return ETIMEDOUT
        if self.limit is not None and self.total >= self.limit:
            if call is not None and call.ended is None:
                call.ended = "out of file calls"
            r._epoch_now(caller)  # in the same step: the guest stops at its next entry
            return EIO
        return 0

    def _invoke(self, mount: _Mounted, method: str, args: tuple[Any, ...]) -> tuple[int, Any]:
        """The provider call itself, counted, inside the fault boundary: (0, answer), or EIO with
        the fault recorded. An OSError that names a member is that answer, as if returned (spec
        061); nothing of it is kept. A BaseException that is not an Exception is let through: it
        is the call's stop (spec 032, Decision 4)."""
        self.total += 1
        self.calls[method] += 1
        try:
            return 0, getattr(mount.provider, method)(*args)
        except Exception as e:
            if (member := _raised(e)) is not None:
                return 0, member
            self._fault(method, args[0], _described(e))
            return EIO, None

    # The write half (spec 034, Decisions 2, 5 and 11).

    def _change(
        self, caller: Any, mount: _Mounted, method: str, at: str, paths: tuple[str, ...], *data: Any
    ) -> tuple[int, bool]:
        """One write-half call: (errno, made). Not made (cancel, deadline, limit) means the
        provider never saw it: nothing is recorded here, since the guest gets the errno and a
        write-back owed by a close or sync is recorded once, by the ending (N3, Decision 5)."""
        if errno := self._gate(caller):
            return errno, False
        return self._made(mount, method, at, paths, data), True

    def _made(
        self, mount: _Mounted, method: str, at: str, paths: tuple[str, ...], data: tuple[Any, ...]
    ) -> int:
        """Call the provider and judge its answer by its real type: None is success, an exact
        Errno is a refusal, anything else (an awaitable included) a fault, answered EIO. Every
        refusal and fault is recorded."""
        errno, answer = self._invoke(mount, method, (*paths, *data))
        if errno:
            self._refuse(mount, method, paths, Errno.EIO, at, "fault")
            return EIO
        try:
            if answer is None:
                return 0
            if type(answer) is Errno:  # exact: an enum with members has no subclass
                self._refuse(mount, method, paths, answer, at, "refused")
                return int(answer)
            self._bad(method, paths[0], answer)
        except Exception as e:
            self._fault(method, paths[0], _described(e))
        self._refuse(mount, method, paths, Errno.EIO, at, "fault")
        return EIO

    def _refuse(
        self,
        mount: _Mounted,
        method: str,
        paths: tuple[str, ...],
        errno: Errno,
        at: str,
        cause: str,
    ) -> None:
        self.refused_total += 1
        if len(self.refused) < REFUSED_KEPT:
            self.refused.append(RefusedWrite(mount.guest, method, paths, errno, at, cause))

    def _fault(self, method: str, path: str, error: str) -> None:
        if len(self.faults) < FAULTS_KEPT:
            self.faults.append(FileFault(method, path, error[:200]))

    def _bad(self, method: str, path: str, answer: Any) -> int:
        if type(answer) is types.CoroutineType:
            try:
                answer.close()  # never awaited, never warned about
            except Exception:
                pass
        self._fault(method, path, f"bad answer: {type(answer).__name__}")
        return EIO

    def _stat(self, caller: Any, mount: _Mounted, path: str) -> tuple[int, str, int, int]:
        """(0, kind, size, mtime_ns), or (errno, "", 0, 0). Every answer is judged by its real
        type, which runs no provider code; what is left to look at runs inside the boundary."""
        errno, answer = self._ask(caller, mount, "stat", path)
        if errno:
            return errno, "", 0, 0
        try:
            if type(answer) is Errno:  # exact: an enum with members has no subclass
                return int(answer), "", 0, 0
            if issubclass(type(answer), Stat):
                kind, size, mtime = answer.kind, answer.size, answer.mtime_ns
                if (
                    _kind(kind)
                    and _number(size, 2**63 - 1)
                    and _number(mtime, MASK64)
                    and (path != "/" or kind == "dir")
                ):
                    return 0, kind, int.__index__(size), int.__index__(mtime)
            return self._bad("stat", path, answer), "", 0, 0
        except Exception as e:
            self._fault("stat", path, _described(e))
            return EIO, "", 0, 0

    def _read(
        self, caller: Any, mount: _Mounted, path: str, buffer: bool = False
    ) -> tuple[int, bytes | bytearray | None]:
        """(0, bytes) for a file (a bytearray when `buffer`, for a descriptor that may write),
        (0, None) for a folder (EISDIR), or (errno, None)."""
        errno, answer = self._ask(caller, mount, "read", path)
        if errno:
            return errno, None
        try:
            if type(answer) is Errno:
                return (0, None) if answer is Errno.EISDIR else (int(answer), None)
            if not issubclass(type(answer), (bytes, bytearray, memoryview)):
                return self._bad("read", path, answer), None
            with memoryview(answer) as view:  # judged in bytes before any copy (Decision 8)
                if self.staged + view.nbytes > self.staging:
                    return EFBIG, None
                return 0, (bytearray(view) if buffer else view.tobytes())
        except Exception as e:
            self._fault("read", path, _described(e))
            return EIO, None

    def _list(
        self, caller: Any, mount: _Mounted, path: str, ino: int, released: int = 0
    ) -> tuple[int, _Listing | None, int]:
        """(0, listing, bytes held), the dots first, or (errno, None, 0). A listing is kept as
        what the guest is served: one buffer of encoded preview1 entries (each its 24-byte
        header, `d_next` included, then its name) and an array of where each starts. It is
        judged against the staging bound as it is gathered, counting the bytes allocated for
        the buffer, the array and the set of names that finds a repeat; once gathered, it holds
        the buffer and the array. Every name is checked before the guest sees it."""
        errno, answer = self._ask(caller, mount, "list", path)
        if errno:
            return errno, None, 0
        iterator = None
        try:
            if type(answer) is Errno:
                return int(answer), None, 0
            kind_of = type(answer)
            if not issubclass(kind_of, Iterable) or issubclass(
                kind_of, (str, bytes, bytearray, memoryview)
            ):
                return self._bad("list", path, answer), None, 0
            data, offsets = _dots(ino)
            seen: set[bytes] = set()
            names = 0  # the bytes of the name objects the set holds
            prefix = path.rstrip("/") + "/"
            # iter() and each next() run the listing's own code, a generator method's body
            # included: an OSError there is the answer of its errno too (spec 061, Decision 5).
            try:
                iterator = iter(answer)
            except Exception as e:
                return self._listing_raised(path, e), None, 0
            while True:
                try:
                    item = next(iterator)
                except StopIteration:
                    break
                except Exception as e:
                    return self._listing_raised(path, e), None, 0
                listed = _listed(item)
                if listed is None or listed[1] in seen:
                    return self._bad("list", path, answer), None, 0
                text, encoded, kind = listed
                seen.add(encoded)
                names += sys.getsizeof(encoded)
                child = self._runner._siphash13((prefix + text).encode())
                d_type = DIRECTORY if kind == "dir" else REGULAR_FILE
                offsets.append(len(data))
                data += struct.pack(DIRENT, len(offsets), child, len(encoded), d_type) + encoded
                gathering = sys.getsizeof(data) + sys.getsizeof(offsets)
                gathering += sys.getsizeof(seen) + names
                if self.staged - released + gathering > self.staging:
                    return EFBIG, None, 0
            return 0, (data, offsets), sys.getsizeof(data) + sys.getsizeof(offsets)
        except Exception as e:
            self._fault("list", path, _described(e))
            return EIO, None, 0
        finally:
            _close(iterator)

    def _listing_raised(self, path: str, e: Exception) -> int:
        """The errno for an exception the listing raised: its member's (spec 061), or EIO with
        the fault recorded."""
        if (member := _raised(e)) is not None:
            return int(member)
        self._fault("list", path, _described(e))
        return EIO

    # Numbers and staging (Decisions 1 and 8).

    def _take(self, entry: _Open) -> int:
        number = heapq.heappop(self.free) if self.free else self.next
        if number == self.next:
            self.next += 1
        self.table[number] = entry
        self.opened += 1
        self.staged += entry.held
        return number

    def _drop(self, number: int) -> None:
        entry = self.table.pop(number)
        if not entry.preopen:
            self.opened -= 1
            heapq.heappush(self.free, number)
        self.staged -= entry.held

    # Paths (Decision 5).

    def _path(self, memory: _Memory, ptr: int, length: int) -> bytes | int:
        """The guest's path bytes, after its pointer and length are checked."""
        ptr, length = ptr & MASK32, length & MASK32
        if not memory.fits(ptr, length):
            return EFAULT
        if length > MAX_PATH:
            return ENAMETOOLONG
        return memory.read(ptr, length)

    def _text(self, raw: bytes) -> str | int:
        """UTF-8, as wasmtime decodes a path when it reads it."""
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return EILSEQ

    def _resolve(self, base: _Open, text: str) -> tuple[str, bool] | int:
        """The path within the mount and whether it must name a folder, or the errno."""
        if not text:
            return ENOENT
        if text.startswith("/"):
            return EPERM
        if "\0" in text:
            return EINVAL
        parts = text.split("/")
        if any(len(part.encode()) > MAX_NAME for part in parts):
            return ENAMETOOLONG
        if base.unlinked:
            return ENOENT  # an open, removed folder holds nothing (spec 034, Decision 7)
        stack = [p for p in base.path.split("/") if p]
        floor = len(stack)
        for part in parts:
            if part in ("", "."):
                continue
            if part == "..":
                if len(stack) <= floor:
                    return EPERM  # it climbs above the descriptor's folder, even for a moment
                stack.pop()
            else:
                stack.append(part)
        path = "/" + "/".join(stack)
        for nested in base.mount.nested:
            if path == nested or path.startswith(nested + "/"):
                return EPERM  # a more specific preopen's: the guest spelled it past wasi-libc
        return path, parts[-1] in ("", ".", "..")

    def _iovecs(self, memory: _Memory, ptr: int, count: int) -> tuple[int, int] | int:
        """The first non-empty buffer (pointer, length) of an iovec array, as wasmtime reads
        it, after the array and every buffer in it are checked."""
        ptr, count = ptr & MASK32, count & MASK32
        if count > MAX_IOVECS:
            return EINVAL
        if not memory.fits(ptr, 8 * count):
            return EFAULT
        if count:
            _aligned(ptr, 4)
        chosen = (0, 0)
        for buf, size in struct.iter_unpack("<II", memory.read(ptr, 8 * count)):
            if not memory.fits(buf, size):
                return EFAULT
            if size and chosen == (0, 0):
                chosen = (buf, size)
        return chosen

    def _result(self, memory: _Memory, ptr: int, size: int, align: int) -> int:
        """0 when a result of `size` bytes fits at `ptr`; EFAULT when it does not."""
        ptr &= MASK32
        if not memory.fits(ptr, size):
            return EFAULT
        _aligned(ptr, align)
        return 0

    def _filestat(
        self, entry: _Open, kind: str, size: int, mtime: int, path: str, links: int = 1
    ) -> bytes:
        filetype = DIRECTORY if kind == "dir" else REGULAR_FILE
        ino = self._runner._siphash13(path.encode())
        return struct.pack(
            FILESTAT,
            entry.mount.dev,
            ino,
            filetype,
            links,
            size if kind == "file" else 0,
            mtime,
            mtime,
            mtime,
        )

    # The descriptor calls. A number not in the table is wasmtime's: forwarded. A mount's own
    # preopen is an empty, read-only folder of the runner's, so a call wasmtime answers alike
    # for every read-only preopen is forwarded too; its listing, its stat and the paths under it
    # are the provider's.

    def _fd_advise(self, caller: Any, fd: int, offset: int, length: int, advice: int) -> int:
        entry = self._entry(fd)
        if entry is None or entry.preopen:
            return self.forward(caller, "fd_advise", (fd, offset, length, advice))
        _enum(advice, 5, "Advice")
        return 0 if entry.kind == "file" else EBADF

    def _fd_allocate(self, caller: Any, fd: int, offset: int, length: int) -> int:
        entry = self._entry(fd)
        if entry is None or entry.preopen:
            return self.forward(caller, "fd_allocate", (fd, offset, length))
        return ENOTSUP if entry.kind == "file" else EBADF

    def _fd_close(self, caller: Any, fd: int) -> int:
        entry = self._entry(fd)
        if entry is None:
            return self.forward(caller, "fd_close", (fd,))
        number = fd & MASK32
        if entry.preopen:
            errno = self.forward(caller, "fd_close", (fd,))
            if errno == 0:
                self._drop(number)  # wasmtime freed the number: it is no longer the mount's
            return errno
        if not (entry.dirty and not entry.unlinked):
            self._drop(number)
            return 0
        # A dirty buffer: one write-back, then the number is freed whatever the answer, as
        # POSIX's close frees the descriptor even when it fails (spec 034, Decision 5).
        errno, made = self._write_back(caller, entry, "close")
        if made:
            self._drop(number)
        else:
            # Not made (cancel, deadline, limit): owed. Closed for the guest, but the number
            # stays reserved, counted in `opened` and its bytes in `staged`, until the ending.
            del self.table[number]
            self.owed[number] = entry
        return errno

    def _write_back(self, caller: Any, entry: _Open, at: str) -> tuple[int, bool]:
        """A dirty buffer's whole content handed to the provider, at close or sync: (errno,
        made). On success the buffer is clean; on a refusal it stays dirty."""
        if errno := self._gate(caller):
            return errno, False  # not made: owed at a close, still dirty at a sync
        data = bytes(entry.data)  # a copy the provider may keep, made only for a call that is made
        if (errno := self._made(entry.mount, "write", at, (entry.path,), (data,))) == 0:
            entry.dirty = False
        return errno, True

    def _fd_datasync(self, caller: Any, fd: int) -> int:
        entry = self._entry(fd)
        if entry is None or entry.preopen:
            return self.forward(caller, "fd_datasync", (fd,))
        return self._sync(caller, entry)

    def _fd_sync(self, caller: Any, fd: int) -> int:
        entry = self._entry(fd)
        if entry is None or entry.preopen:
            return self.forward(caller, "fd_sync", (fd,))
        return self._sync(caller, entry)

    def _sync(self, caller: Any, entry: _Open) -> int:
        """A dirty buffer's write-back, its answer the guest's; a clean one, an unlinked one or
        one that may not write needs no call (spec 034, Decision 5). A folder is EBADF."""
        if entry.kind != "file":
            return EBADF
        if entry.dirty and not entry.unlinked:
            return self._write_back(caller, entry, "sync")[0]
        return 0

    def _fd_fdstat_get(self, caller: Any, fd: int, ptr: int) -> int:
        entry = self._entry(fd)
        if entry is None or entry.preopen:
            return self.forward(caller, "fd_fdstat_get", (fd, ptr))
        memory = _Memory(caller)
        if errno := self._result(memory, ptr, 24, 8):
            return errno
        if entry.kind == "file":
            flags = (APPEND if entry.append else 0) | (NONBLOCK if entry.nonblock else 0)
            rights = RIGHTS  # as wasmtime reports a file by its open mode
            if not entry.readable:
                rights &= ~(FD_READ | FD_READDIR)
            if not entry.writable:
                rights &= ~FD_WRITE
            data = struct.pack(FDSTAT, REGULAR_FILE, flags, rights, rights)
        else:
            data = struct.pack(FDSTAT, DIRECTORY, 0, DIR_RIGHTS, DIR_RIGHTS)
        memory.write(ptr & MASK32, data)
        return 0

    def _fd_fdstat_set_flags(self, caller: Any, fd: int, flags: int) -> int:
        entry = self._entry(fd)
        if entry is None or entry.preopen:
            return self.forward(caller, "fd_fdstat_set_flags", (fd, flags))
        flags = _flags(flags, 0x1F, 0xFFFF, "Fdflags")
        if entry.kind != "file":
            return EBADF
        if flags & (DSYNC | RSYNC | SYNC):
            return EINVAL
        entry.append, entry.nonblock = bool(flags & APPEND), bool(flags & NONBLOCK)
        return 0

    def _fd_fdstat_set_rights(self, caller: Any, fd: int, base: int, inheriting: int) -> int:
        entry = self._entry(fd)
        if entry is None or entry.preopen:
            return self.forward(caller, "fd_fdstat_set_rights", (fd, base, inheriting))
        _rights(base)
        _rights(inheriting)
        return ENOTSUP

    def _fd_filestat_get(self, caller: Any, fd: int, ptr: int) -> int:
        entry = self._entry(fd)
        if entry is None:
            return self.forward(caller, "fd_filestat_get", (fd, ptr))
        memory = _Memory(caller)
        if errno := self._result(memory, ptr, 64, 8):
            return errno
        # No provider call: the kind and size are the staged bytes', and the times are 0.
        links = 0 if entry.unlinked else 1  # an unlinked file has no name left (spec 034)
        stat = self._filestat(entry, entry.kind, len(entry.data), 0, entry.path, links)
        memory.write(ptr & MASK32, stat)
        return 0

    def _fd_filestat_set_size(self, caller: Any, fd: int, size: int) -> int:
        entry = self._entry(fd)
        if entry is None or entry.preopen:
            return self.forward(caller, "fd_filestat_set_size", (fd, size))
        if entry.kind != "file":
            return EBADF
        if not entry.mount.writable:
            return EPERM  # a read-only grant's answer
        size &= MASK64
        if size >= OFFSET_TOP or not entry.writable:
            return EINVAL  # the host's ftruncate: past i64, or a descriptor not open to write
        if not self._fits(entry, size):
            return EFBIG
        data = entry.data
        assert isinstance(data, bytearray)
        if size < len(data):
            del data[size:]
        else:
            _grow(data, size)
        self._changed(entry)
        return 0

    def _fits(self, entry: _Open, size: int) -> bool:
        """Whether a buffer may become `size` bytes: judged against the staging bound on the new
        size, before a byte is allocated (spec 034, Decision 4)."""
        return size <= len(entry.data) or self.staged - entry.held + size <= self.staging

    def _changed(self, entry: _Open) -> None:
        """A buffer was written or resized: counted at its size, and dirty, even when its bytes
        are the same, as a grant's file has its mtime touched."""
        self.staged += len(entry.data) - entry.held
        entry.held = len(entry.data)
        entry.dirty = True

    def _fd_filestat_set_times(self, caller: Any, fd: int, atim: int, mtim: int, flags: int) -> int:
        entry = self._entry(fd)
        if entry is None or (entry.preopen and not entry.mount.writable):
            return self.forward(caller, "fd_filestat_set_times", (fd, atim, mtim, flags))
        flags = _flags(flags, 0xF, 0xFFFF, "Fstflags")
        if (flags & ATIM and flags & ATIM_NOW) or (flags & MTIM and flags & MTIM_NOW):
            return EINVAL
        # Times are the provider's (spec 034, Decision 9): a writable mount accepts and ignores
        # them, its own preopen included, as a writable grant accepts the call.
        return 0 if entry.mount.writable else EPERM

    def _fd_read(self, caller: Any, fd: int, iovs: int, count: int, nread: int) -> int:
        entry = self._entry(fd)
        if entry is None or entry.preopen:
            return self.forward(caller, "fd_read", (fd, iovs, count, nread))
        return self._reads(caller, entry, iovs, count, None, nread)

    def _fd_pread(
        self, caller: Any, fd: int, iovs: int, count: int, offset: int, nread: int
    ) -> int:
        entry = self._entry(fd)
        if entry is None or entry.preopen:
            return self.forward(caller, "fd_pread", (fd, iovs, count, offset, nread))
        return self._reads(caller, entry, iovs, count, offset & MASK64, nread)

    def _reads(
        self, caller: Any, entry: _Open, iovs: int, count: int, offset: int | None, nread: int
    ) -> int:
        memory = _Memory(caller)
        chosen = self._iovecs(memory, iovs, count)
        if isinstance(chosen, int):
            return chosen
        if errno := self._result(memory, nread, 4, 4):
            return errno
        if entry.kind != "file" or not entry.readable:
            return EBADF  # a folder, or a file opened only to write (spec 034)
        at = entry.position if offset is None else offset
        buf, size = chosen
        # As Linux answers a grant (the reference, Decision 6): an offset past i64, or a read
        # whose end would pass it, is EINVAL (the kernel's rw_verify_area). fd_pread reads
        # through wasmtime's stream, which asks for at most MAX_READ_SIZE_ALLOC (64 KiB) at a
        # time (crates/wasi/src/lib.rs:31), so only that much counts there.
        count = size if offset is None else min(size, PREAD_CHUNK)
        if at >= 2**63 or at + count > 2**63 - 1:
            return EINVAL
        data = entry.data[at : at + size]
        memory.write(buf, data)
        if offset is None:
            entry.position = at + len(data)
        memory.write(nread & MASK32, struct.pack("<I", len(data)))
        return 0

    def _fd_write(self, caller: Any, fd: int, iovs: int, count: int, nwritten: int) -> int:
        entry = self._entry(fd)
        if entry is None or entry.preopen:
            return self.forward(caller, "fd_write", (fd, iovs, count, nwritten))
        return self._writes(caller, entry, iovs, count, None, nwritten)

    def _fd_pwrite(
        self, caller: Any, fd: int, iovs: int, count: int, offset: int, nwritten: int
    ) -> int:
        entry = self._entry(fd)
        if entry is None or entry.preopen:
            return self.forward(caller, "fd_pwrite", (fd, iovs, count, offset, nwritten))
        return self._writes(caller, entry, iovs, count, offset & MASK64, nwritten)

    def _writes(
        self, caller: Any, entry: _Open, iovs: int, count: int, offset: int | None, nwritten: int
    ) -> int:
        """A write into a buffer, as wasmtime writes a writable grant's file (spec 034, Decision
        4): the first non-empty ciovec; on an append descriptor at the end, `fd_pwrite`'s offset
        ignored; past the end, zeros in the gap. No provider call. A descriptor that may not
        write, or a folder, is the host's EBADF."""
        memory = _Memory(caller)
        chosen = self._iovecs(memory, iovs, count)
        if isinstance(chosen, int):
            return chosen
        if errno := self._result(memory, nwritten, 4, 4):
            return errno
        if entry.kind != "file":
            return EBADF
        at = entry.position if offset is None else offset
        if at >= OFFSET_TOP and not entry.append:
            return EINVAL  # the host's pwrite past i64, judged before the descriptor's mode
        if not entry.writable:
            return EBADF
        if entry.append:
            at = len(entry.data)
        buf, size = chosen
        if size:  # an empty write changes nothing, as on a grant
            if not self._fits(entry, at + size):
                return EFBIG
            data = entry.data
            assert isinstance(data, bytearray)
            _grow(data, at)
            data[at : at + size] = memory.read(buf, size)
            self._changed(entry)
        if offset is None:
            entry.position = len(entry.data) if entry.append else at + size
        memory.write(nwritten & MASK32, struct.pack("<I", size))
        return 0

    def _fd_seek(self, caller: Any, fd: int, offset: int, whence: int, ptr: int) -> int:
        entry = self._entry(fd)
        if entry is None or entry.preopen:
            return self.forward(caller, "fd_seek", (fd, offset, whence, ptr))
        whence = _enum(whence, 2, "Whence")
        memory = _Memory(caller)
        if errno := self._result(memory, ptr, 8, 8):
            return errno
        if entry.kind != "file":
            return EBADF
        if whence == 0:
            target = offset if offset >= 0 else -1
        elif whence == 1:
            target = entry.position + offset
        else:
            target = len(entry.data) + offset
        if not 0 <= target <= MASK64:
            return EINVAL
        entry.position = target
        memory.write(ptr & MASK32, struct.pack("<Q", target))
        return 0

    def _fd_tell(self, caller: Any, fd: int, ptr: int) -> int:
        entry = self._entry(fd)
        if entry is None or entry.preopen:
            return self.forward(caller, "fd_tell", (fd, ptr))
        memory = _Memory(caller)
        if errno := self._result(memory, ptr, 8, 8):
            return errno
        if entry.kind != "file":
            return EBADF
        memory.write(ptr & MASK32, struct.pack("<Q", entry.position))
        return 0

    def _fd_readdir(
        self, caller: Any, fd: int, buf: int, length: int, cookie: int, used: int
    ) -> int:
        entry = self._entry(fd)
        if entry is None:
            errno = self.forward(caller, "fd_readdir", (fd, buf, length, cookie, used))
            if errno == 0:
                errno = self._zeroed(
                    caller, fd, buf & MASK32, length & MASK32, cookie, used & MASK32
                )
            return errno
        memory = _Memory(caller)
        buf, length, cookie = buf & MASK32, length & MASK32, cookie & MASK64
        if not memory.fits(buf, length):
            return EFAULT
        if errno := self._result(memory, used, 4, 4):
            return errno
        if entry.kind != "dir":
            return EBADF
        if entry.unlinked:
            pass  # only its dots, kept since it was unlinked, with no provider call
        elif entry.listing is None or (cookie == 0 and not entry.fresh):
            # The listing made at open serves the first pass; from cookie 0 after that, the
            # folder is listed again, as rewinddir expects.
            ino = self._runner._siphash13(entry.path.encode())
            errno, listing, held = self._list(caller, entry.mount, entry.path, ino, entry.held)
            if errno:
                return errno
            self.staged += held - entry.held
            entry.listing, entry.held, entry.fresh = listing, held, True
        if cookie == 0:
            entry.fresh = False
        if entry.listing is None:
            return EIO  # never kept: a listing that could not be had is an errno, not a value
        # wasmtime writes the entries from the cookie on, one after another, each cut where
        # the buffer ends: the same bytes as one slice of the encoded listing.
        data, offsets = entry.listing
        out = data[offsets[cookie] : offsets[cookie] + length] if cookie < len(offsets) else b""
        memory.write(buf, bytes(out))
        memory.write(used & MASK32, struct.pack("<I", len(out)))
        return 0

    def _zeroed(self, caller: Any, fd: int, buf: int, length: int, cookie: int, used: int) -> int:
        """After a forwarded fd_readdir that answered 0: every entry's three padding bytes
        zero, as wasmtime 49.0.2 writes them (spec 048, Decision 4; GHSA-96f6-r43r-8c24). The
        walk reads each d_namlen from the guest's buffer, which only wasmtime has written,
        unless the guest's `used` pointer lies over the listing: wasmtime writes the count there
        last, over whatever field it lands on (a d_namlen the walk would follow included; the
        build review, F1). Then the folder is listed again on the guard's own page, for no more
        than the guest's memory holds from `buf`, its padding zeroed there, and written out as
        wasmtime writes a listing, the entries and then the count at `used`; bytes the first
        listing wrote past the second are zeroed. If the folder
        cannot be listed again, the first listing is zeroed whole, the count is 0, and the
        answer is EIO. Answers the errno the guest gets."""
        memory = _Memory(caller)
        if not memory.fits(used, 4):
            return 0
        count = struct.unpack("<I", memory.read(used, 4))[0]
        if not memory.fits(buf, count) or not count:
            return 0
        if used + 4 <= buf or used >= buf + count:
            data = bytearray(memory.read(buf, count))
            if _zero_pads(data):
                memory.write(buf, bytes(data))
            return 0
        forwards = self.forwards
        assert forwards is not None and forwards.page is not None  # it just forwarded
        # No more than the guest's memory can hold from `buf` (the confirmation, C2), so the
        # page, the listing and its count after it, never grows past the guest's own memory.
        length = min(length, memory.size - max(buf, 8))
        page, at = forwards.page, (length + 3) & ~3  # the listing at 0, its count after it
        errno = 0
        short = at + 4 - page.data_len(caller)
        if short > 0:
            try:
                page.grow(caller, (short + 65535) // 65536)
            except Exception:
                errno = EIO  # a page that cannot grow (the memory limit): not served, below
        if not errno:
            errno = self.forward(caller, "fd_readdir", (fd, 0, length, cookie, at), stat=True)
        again = 0 if errno else struct.unpack("<I", page.read(caller, at, at + 4))[0]
        if errno or not memory.fits(buf, again):  # not listed again: none of the first is left
            memory.write(buf, bytes(count))
            memory.write(used, bytes(4))
            return EIO
        data = bytearray(page.read(caller, 0, again))
        _zero_pads(data)
        memory.write(buf, bytes(data) + bytes(max(0, count - again)))
        memory.write(used, struct.pack("<I", again))
        return 0

    def _fd_renumber(self, caller: Any, fd: int, to: int) -> int:
        """Never onto or from a number in the table, or at or above 2**30: wasmtime would
        silently replace the target (the review's raw_answers.txt)."""
        a, b = fd & MASK32, to & MASK32
        if a in self.table or b in self.table or a >= PROVIDER_BASE or b >= PROVIDER_BASE:
            return ENOTSUP
        return self.forward(caller, "fd_renumber", (fd, to))

    # The path calls.

    def _path_open(
        self,
        caller: Any,
        fd: int,
        dirflags: int,
        ptr: int,
        length: int,
        oflags: int,
        base_rights: int,
        inheriting: int,
        fdflags: int,
        out: int,
    ) -> int:
        entry = self._entry(fd)
        args = (fd, dirflags, ptr, length, oflags, base_rights, inheriting, fdflags, out)
        if entry is None:
            return self.forward(caller, "path_open", args)
        _lookup(dirflags)
        oflags = _flags(oflags, 0xF, 0xFFFF, "Oflags")
        base_rights = _rights(base_rights)
        _rights(inheriting)
        fdflags = _flags(fdflags, 0x1F, 0xFFFF, "Fdflags")
        memory = _Memory(caller)
        raw = self._path(memory, ptr, length)
        if isinstance(raw, int):
            return raw
        if errno := self._result(memory, out, 4, 4):
            return errno
        text = self._text(raw)
        if isinstance(text, int):
            return text
        if entry.kind != "dir":
            return ENOTDIR
        if fdflags & (SYNC | DSYNC | RSYNC):
            return ENOTSUP
        if oflags & O_DIRECTORY and oflags & (O_CREAT | O_EXCL | O_TRUNC):
            return EINVAL
        mount = entry.mount
        writes = bool(oflags & (O_CREAT | O_TRUNC) or base_rights & FD_WRITE)  # "may write"
        if writes and not mount.writable:
            return EPERM  # a read-only grant's answer, before any provider call (Decision 6)
        resolved = self._resolve(entry, text)
        if isinstance(resolved, int):
            return resolved
        path, folder_only = resolved
        if self.opened >= MAX_MOUNT_FILES:
            return EMFILE  # before the provider: no call, none counted
        if writes:
            opened = self._open_writing(caller, mount, path, folder_only, oflags, base_rights)
            if isinstance(opened, int):
                return opened
            opened.append, opened.nonblock = bool(fdflags & APPEND), bool(fdflags & NONBLOCK)
        elif oflags & O_DIRECTORY:
            ino = self._runner._siphash13(path.encode())
            errno, listing, held = self._list(caller, mount, path, ino)
            if errno:
                return errno
            opened = _Open(mount, path, "dir", listing=listing, fresh=True, held=held)
        else:
            errno, data = self._read(caller, mount, path)
            if errno:
                return errno
            if data is None:
                opened = _Open(mount, path, "dir")
            elif folder_only:
                return ENOTDIR
            else:
                opened = _Open(mount, path, "file", data=data, held=len(data))
                opened.append, opened.nonblock = bool(fdflags & APPEND), bool(fdflags & NONBLOCK)
        number = self._take(opened)
        memory.write(out & MASK32, struct.pack("<I", number))
        return 0

    def _open_writing(
        self, caller: Any, mount: _Mounted, path: str, folder_only: bool, oflags: int, rights: int
    ) -> _Open | int:
        """An open that may write, on a writable mount (spec 034, Decision 3): the table read
        top to bottom, at most two provider calls, a create or a truncation made at open by
        `write(path, b"")`. The buffer starts clean. A call the gate stops owes nothing: no
        buffer exists yet, so the open answers that errno and nothing is recorded (N3)."""
        creat, trunc = oflags & O_CREAT, oflags & O_TRUNC
        if oflags & O_DIRECTORY or folder_only:
            # A folder is never opened to write; a name that must be a folder is not a file.
            # Linux's answers, wasmtime's reference: the mount itself exists (EEXIST for "x"),
            # a create there is EISDIR, else as found.
            if path == "/":
                return EEXIST if creat and oflags & O_EXCL else EISDIR
            if creat and folder_only:
                return EISDIR
            errno, kind, _, _ = self._stat(caller, mount, path)
            return errno or (EISDIR if kind == "dir" else ENOTDIR)
        data: bytes | bytearray = bytearray()
        if creat and oflags & O_EXCL:  # "x": a name no one holds, exact within the call
            errno, kind, _, _ = self._stat(caller, mount, path)
            if errno == 0:
                return EEXIST
            if errno != ENOENT or (errno := self._create(caller, mount, path)):
                return errno
        elif creat and trunc:  # "w": one call creates or truncates
            if errno := self._create(caller, mount, path):
                return errno
        elif trunc:
            errno, kind, _, _ = self._stat(caller, mount, path)
            if errno:
                return errno
            if kind == "dir":
                return EISDIR
            if errno := self._create(caller, mount, path):
                return errno
        else:  # "a", O_CREAT | O_WRONLY, "r+": the bytes, or a create when missing
            errno, got = self._read(caller, mount, path, buffer=True)
            if errno == ENOENT and creat:
                if errno := self._create(caller, mount, path):
                    return errno
            elif errno:
                return errno
            elif got is None:
                return EISDIR
            else:
                data = got
        return _Open(
            mount,
            path,
            "file",
            data=data,
            held=len(data),
            readable=bool(rights & FD_READ),
            writable=True,
        )

    def _create(self, caller: Any, mount: _Mounted, path: str) -> int:
        """A create or a truncation at open: one `write(path, b"")`, recorded at "open" when it
        is refused."""
        return self._change(caller, mount, "write", "open", (path,), b"")[0]

    def _path_filestat_get(
        self, caller: Any, fd: int, flags: int, ptr: int, length: int, out: int
    ) -> int:
        entry = self._entry(fd)
        if entry is None:
            return self.forward(caller, "path_filestat_get", (fd, flags, ptr, length, out))
        _lookup(flags)
        memory = _Memory(caller)
        raw = self._path(memory, ptr, length)
        if isinstance(raw, int):
            return raw
        if errno := self._result(memory, out, 64, 8):
            return errno
        if entry.kind != "dir":
            return EBADF
        text = self._text(raw)
        if isinstance(text, int):
            return text
        resolved = self._resolve(entry, text)
        if isinstance(resolved, int):
            return resolved
        path, folder_only = resolved
        errno, kind, size, mtime = self._stat(caller, entry.mount, path)
        if errno:
            return errno
        if folder_only and kind != "dir":
            return ENOTDIR
        memory.write(out & MASK32, self._filestat(entry, kind, size, mtime, path))
        return 0

    def _path_readlink(
        self, caller: Any, fd: int, ptr: int, length: int, buf: int, size: int, used: int
    ) -> int:
        entry = self._entry(fd)
        if entry is None:
            return self.forward(caller, "path_readlink", (fd, ptr, length, buf, size, used))
        memory = _Memory(caller)
        raw = self._path(memory, ptr, length)
        if isinstance(raw, int):
            return raw
        if not memory.fits(buf & MASK32, size & MASK32):
            return EFAULT
        if errno := self._result(memory, used, 4, 4):
            return errno
        if entry.kind != "dir":
            return EBADF
        text = self._text(raw)
        if isinstance(text, int):
            return text
        resolved = self._resolve(entry, text)
        if isinstance(resolved, int):
            return resolved
        path, folder_only = resolved
        errno, kind, _, _ = self._stat(caller, entry.mount, path)
        if errno:
            return errno
        if folder_only and kind != "dir":
            return ENOTDIR
        return EINVAL  # a file or a folder: not a link (a mount has no links)

    def _refused(self, caller: Any, entry: _Open, *paths: tuple[int, int]) -> int:
        """A write-shaped path call on a read-only folder of the table: EPERM once its paths
        are read, as wasmtime answers on a read-only grant, before any provider call."""
        if entry.kind != "dir":
            return EBADF
        return self._read_paths(caller, paths) or EPERM

    def _read_paths(self, caller: Any, paths: tuple[tuple[int, int], ...]) -> int:
        """0 when every path can be read as wasmtime reads it, else the errno."""
        texts = self._texts(caller, paths)
        return texts if isinstance(texts, int) else 0

    def _texts(self, caller: Any, paths: tuple[tuple[int, int], ...]) -> list[str] | int:
        """Every path read and decoded as wasmtime reads it, or the first errno."""
        memory, texts = _Memory(caller), []
        for ptr, length in paths:
            raw = self._path(memory, ptr, length)
            if isinstance(raw, int):
                return raw
            text = self._text(raw)
            if isinstance(text, int):
                return text
            texts.append(text)
        return texts

    # The namespace calls of a writable mount (spec 034, Decisions 6 and 7). The answers the
    # runner gives itself, with no provider call, are Linux's on a writable grant (wasmtime's
    # reference, EXECUTED in the build's probe); macOS differs on some, which the parity table
    # asserts per system.

    def _path_create_directory(self, caller: Any, fd: int, ptr: int, length: int) -> int:
        entry = self._entry(fd)
        if entry is None:
            return self.forward(caller, "path_create_directory", (fd, ptr, length))
        return self._namespace(caller, entry, ptr, length, "mkdir")

    def _path_remove_directory(self, caller: Any, fd: int, ptr: int, length: int) -> int:
        entry = self._entry(fd)
        if entry is None:
            return self.forward(caller, "path_remove_directory", (fd, ptr, length))
        return self._namespace(caller, entry, ptr, length, "rmdir")

    def _path_unlink_file(self, caller: Any, fd: int, ptr: int, length: int) -> int:
        entry = self._entry(fd)
        if entry is None:
            return self.forward(caller, "path_unlink_file", (fd, ptr, length))
        return self._namespace(caller, entry, ptr, length, "remove")

    def _namespace(self, caller: Any, entry: _Open, ptr: int, length: int, method: str) -> int:
        """`mkdir`, `remove` or `rmdir`: one provider call after the path rules, or the answer
        the runner gives itself: the mount itself, a name ending in `/`, `.` or `..` (one `stat`
        decides it), and an `rmdir` strictly above a more specific preopen (EBUSY)."""
        if entry.kind != "dir":
            return EBADF
        texts = self._texts(caller, ((ptr, length),))
        if isinstance(texts, int):
            return texts
        if not entry.mount.writable:
            return EPERM  # a read-only grant's answer, before any provider call
        resolved = self._resolve(entry, texts[0])
        if isinstance(resolved, int):
            return resolved
        path, folder_only = resolved
        last, mount = texts[0].rsplit("/", 1)[-1], entry.mount
        if path == "/":  # the mount itself, as a grant's own preopen answers
            return {"mkdir": EEXIST, "remove": EISDIR, "rmdir": EINVAL}[method]
        if folder_only and (method != "mkdir" or last in (".", "..")):
            errno, kind, _, _ = self._stat(caller, mount, path)
            if errno:
                return errno
            if kind != "dir":
                return ENOTDIR
            return {"mkdir": EEXIST, "remove": EISDIR, "rmdir": EINVAL}[method]
        if method == "rmdir" and self._above(mount, path):
            return EBUSY  # the guest's view of other preopens stays where it was put
        errno, _ = self._change(caller, mount, method, "call", (path,))
        if errno == 0 and method != "mkdir":
            self._follow(mount, path)
        return errno

    def _above(self, mount: _Mounted, path: str) -> bool:
        """Whether `path` is strictly above a more specific preopen's guest path."""
        prefix = "/" if path == "/" else path + "/"
        return any(nested.startswith(prefix) for nested in mount.nested)

    def _follow(self, mount: _Mounted, src: str, dst: str | None = None) -> None:
        """After `remove(src)` or `rmdir(src)` (no `dst`), or `rename(src, dst)`, succeeded,
        this call's descriptors follow it, as POSIX's follow the file (Decision 7): those at the
        removed path, or at or under the rename's `dst`, are unlinked; then those at or under its
        `src` take the same path under `dst`. Owed buffers follow too: their bytes are the
        file's."""
        entries = [e for e in (*self.table.values(), *self.owed.values()) if e.mount is mount]
        live = [e for e in entries if not e.preopen and not e.unlinked]
        for e in live:
            if dst is None and e.path == src:
                self._unlink(e)
            elif dst is not None and (e.path == dst or e.path.startswith(dst + "/")):
                self._unlink(e)
        if dst is not None:
            for e in live:
                if not e.unlinked and (e.path == src or e.path.startswith(src + "/")):
                    e.path = dst + e.path[len(src) :]

    def _unlink(self, entry: _Open) -> None:
        """A descriptor whose path the guest removed or replaced: a file keeps its buffer for
        reads and writes and is never written back; a folder holds nothing from now on, its
        kept listing replaced by the dots."""
        entry.unlinked = True
        if entry.kind == "dir":
            listing = _dots(self._runner._siphash13(entry.path.encode()))
            held = sys.getsizeof(listing[0]) + sys.getsizeof(listing[1])
            self.staged += held - entry.held
            entry.listing, entry.held, entry.fresh = listing, held, True

    def _path_filestat_set_times(
        self,
        caller: Any,
        fd: int,
        flags: int,
        ptr: int,
        length: int,
        atim: int,
        mtim: int,
        fst: int,
    ) -> int:
        entry = self._entry(fd)
        if entry is None:
            args = (fd, flags, ptr, length, atim, mtim, fst)
            return self.forward(caller, "path_filestat_set_times", args)
        _lookup(flags)
        fst = _flags(fst, 0xF, 0xFFFF, "Fstflags")
        if (fst & ATIM and fst & ATIM_NOW) or (fst & MTIM and fst & MTIM_NOW):
            return EINVAL
        if not entry.mount.writable:
            return self._refused(caller, entry, (ptr, length))
        if entry.kind != "dir":
            return EBADF
        texts = self._texts(caller, ((ptr, length),))
        if isinstance(texts, int):
            return texts
        resolved = self._resolve(entry, texts[0])
        # Times are the provider's (Decision 9): accepted and ignored, with no provider call.
        return resolved if isinstance(resolved, int) else 0

    def _path_symlink(
        self, caller: Any, old: int, old_length: int, fd: int, new: int, new_length: int
    ) -> int:
        entry = self._entry(fd)
        if entry is None:
            return self.forward(caller, "path_symlink", (old, old_length, fd, new, new_length))
        refused = self._refused(caller, entry, (old, old_length), (new, new_length))
        if refused != EPERM or not entry.mount.writable:
            return refused
        return ENOTSUP  # the protocol has no link (Decision 9)

    def _across(
        self, caller: Any, a: int, b: int, paths: tuple[tuple[int, int], ...], follow: bool = False
    ) -> int:
        """A rename or link between two descriptors that are not one mount's, at least one of
        them a number of the table: each side must be a folder (a number of wasmtime's is asked
        of wasmtime, with no side effect), then the paths are read; a read-only side refuses
        (EPERM), as across a writable and a read-only grant; two sides that may both be written
        are two filesystems (EXDEV), so `shutil.move` copies (Decision 6)."""
        for fd in (a, b):
            entry = self._entry(fd)
            if entry is not None:
                if entry.kind != "dir":
                    return EBADF
            elif not self._wasmtime_folder(caller, fd):
                return EBADF
        if errno := self._read_paths(caller, paths):
            return errno
        for fd in (a, b):
            entry = self._entry(fd)
            if entry is not None and not entry.mount.writable:
                return EPERM
        for fd in (a, b):
            if self._entry(fd) is None and not self._wasmtime_writable(caller, fd):
                return EPERM
        if follow:
            return EINVAL  # a link that follows links, as wasmtime answers between writable sides
        return EXDEV

    def _wasmtime_folder(self, caller: Any, fd: int) -> bool:
        """Whether wasmtime's number is a folder: fd_fdstat_set_rights answers ENOTSUP on any
        open file or folder and fd_allocate EBADF on anything but a file; neither changes it."""
        rights = self.forward(caller, "fd_fdstat_set_rights", (fd, 0, 0))
        return rights == ENOTSUP and self.forward(caller, "fd_allocate", (fd, 0, 0)) == EBADF

    def _wasmtime_writable(self, caller: Any, fd: int) -> bool:
        """Whether wasmtime's folder may be written: `path_create_directory` of the empty path
        answers EPERM on a read-only one, before the path is looked at, and ENOENT on a writable
        one; it makes nothing (EXECUTED on Linux and macOS in the build's probe)."""
        return self.forward(caller, "path_create_directory", (fd, 0, 0)) != EPERM

    def _path_rename(
        self, caller: Any, fd: int, old: int, old_length: int, to: int, new: int, new_length: int
    ) -> int:
        a, b = self._entry(fd), self._entry(to)
        if a is None and b is None:  # two of wasmtime's numbers: spec 048's rule
            return self._rename(caller, fd, old, old_length, to, new, new_length)
        paths = ((old, old_length), (new, new_length))
        if a is None or b is None or a.mount is not b.mount or not a.mount.writable:
            return self._across(caller, fd, to, paths)
        if a.kind != "dir" or b.kind != "dir":
            return EBADF
        texts = self._texts(caller, paths)
        if isinstance(texts, int):
            return texts
        resolved = [self._resolve(base, text) for base, text in ((a, texts[0]), (b, texts[1]))]
        for one in resolved:
            if isinstance(one, int):
                return one
        (src, _), (dst, _) = resolved  # type: ignore[misc]
        mount, lasts = a.mount, [text.rsplit("/", 1)[-1] for text in texts]
        needs_folder = any(
            counts and text.endswith("/")
            for counts, text in zip(RENAME_SLASH_NEEDS_FOLDER, texts, strict=True)
        )
        if "/" in (src, dst) or {".", ".."} & set(lasts):
            return EBUSY  # the mount itself, or a name ending in `.` or `..` (Linux's answer)
        if self._above(mount, src) or self._above(mount, dst):
            return EBUSY  # the guest's view of other preopens stays where it was put
        if dst.startswith(src + "/"):
            return EINVAL  # into its own subfolder
        if src == dst or needs_folder:
            # onto itself, or a source that must be a folder: one `stat` decides it
            errno, kind, _, _ = self._stat(caller, mount, src)
            if errno:
                return errno
            if needs_folder and kind != "dir":
                return ENOTDIR
            if src == dst:
                return 0
        errno, _ = self._change(caller, mount, "rename", "call", (src, dst))
        if errno == 0:
            self._follow(mount, src, dst)
        return errno

    def _rename(
        self, caller: Any, fd: int, old: int, old_length: int, to: int, new: int, new_length: int
    ) -> int:
        """wasmtime 49.0.3's rule (spec 048, Decisions 1 to 3; GHSA-m9f7-9w4p-gv38). With no
        trailing slash on either path, or a path wasmtime could not read either, the rename is
        forwarded unchanged. Otherwise the source must be a folder, judged without following its
        own link: the stat's errno, or ENOTDIR for anything else; and a folder is renamed by the
        plain names, every trailing slash trimmed from both paths (the same pointers, shorter
        lengths), so the kernel is never handed a slash-named link to follow. Once a slash is
        seen, the rename is never forwarded with it (condition C2): a path the guard cannot
        read whole answers its errno instead."""
        memory = _Memory(caller)
        spans = ((old & MASK32, old_length & MASK32), (new & MASK32, new_length & MASK32))
        readable = all(memory.fits(ptr, length) for ptr, length in spans)
        if not readable or not any(
            length and memory.read(ptr + length - 1, 1) == b"/" for ptr, length in spans
        ):
            return self.forward(caller, "path_rename", (fd, old, old_length, to, new, new_length))
        # Either path past MAX_PATH is ENAMETOOLONG, never forwarded, so the host's work stays
        # bounded; the text is decoded as wasmtime reads both paths before anything else.
        paths = []
        for ptr, length in ((old, old_length), (new, new_length)):
            raw = self._path(memory, ptr, length)
            if isinstance(raw, int):
                return raw
            if isinstance(text := self._text(raw), int):
                return text
            paths.append(raw)
        source, target = _plain(paths[0]), _plain(paths[1])
        if errno := self._source_type(caller, fd, source):
            return errno
        return self.forward(caller, "path_rename", (fd, old, len(source), to, new, len(target)))

    def _source_type(self, caller: Any, fd: int, source: bytes) -> int:
        """0 when `source` names a folder under `fd`, judged by wasmtime's own path_filestat_get
        with the follow flag clear, on the stat trampoline's page: the path at STAT_PATH, the
        64-byte filestat at 0, its filetype at byte 16 (Decision 2). Else the stat's errno, or
        ENOTDIR for a file or a link (Decision 3)."""
        forwards = self.forwards
        if forwards is None or forwards.page is None:
            return EBADF  # no trampoline yet: nothing of wasmtime's can be reached
        if STAT_PATH + len(source) > forwards.page.data_len(caller):
            return ENAMETOOLONG
        forwards.page.write(caller, source, STAT_PATH)
        args = (fd, 0, STAT_PATH, len(source), 0)
        if errno := self.forward(caller, "path_filestat_get", args, stat=True):
            return errno
        return 0 if forwards.page.read(caller, 16, 17)[0] == DIRECTORY else ENOTDIR

    def _path_link(
        self,
        caller: Any,
        fd: int,
        flags: int,
        old: int,
        old_length: int,
        to: int,
        new: int,
        new_length: int,
    ) -> int:
        a, b = self._entry(fd), self._entry(to)
        if a is None and b is None:
            args = (fd, flags, old, old_length, to, new, new_length)
            return self.forward(caller, "path_link", args)
        flags = _lookup(flags)
        paths = ((old, old_length), (new, new_length))
        if a is None or b is None or a.mount is not b.mount or not a.mount.writable:
            return self._across(caller, fd, to, paths, follow=bool(flags & 1))
        if a.kind != "dir" or b.kind != "dir":
            return EBADF
        if errno := self._read_paths(caller, paths):
            return errno
        return EINVAL if flags & 1 else ENOTSUP  # the protocol has no link (Decision 9)


def _plain(path: bytes) -> bytes:
    """A path with its trailing slashes trimmed, but never below one byte, as wasmtime's own
    `strip_dir_suffix` keeps `/` itself."""
    return path.rstrip(b"/") or path[:1]


def _zero_pads(data: bytearray) -> bool:
    """Zero the three padding bytes after each entry's d_type in a listing as wasmtime wrote
    it, walking by 24 + d_namlen (d_next is a cookie, not an offset), a header the listing cut
    short as far as it reaches. True when a byte changed."""
    changed, pos, count = False, 0, len(data)
    while pos < count:
        for at in (pos + 21, pos + 22, pos + 23):
            if at < count and data[at]:
                data[at] = 0
                changed = True
        if pos + 24 > count:
            break
        pos += 24 + struct.unpack_from("<I", data, pos + 16)[0]
    return changed


def _described(e: BaseException) -> str:
    """An exception's type name and the first line of its text; total: it runs no provider
    code it cannot survive (a metaclass's `__name__`, a `__str__` returning a str subclass) and
    formats nothing but plain str."""
    try:
        name = type.__dict__["__name__"].__get__(type(e))  # the type's own name, not a property's
        if type(name) is not str:
            name = "an exception"
    except Exception:
        name = "an exception"
    try:
        text = str(e)
        if type(text) is not str:
            return name
        lines = str.splitlines(str.strip(text))
    except Exception:
        return name
    return f"{name}: {lines[0]}" if lines else name


def _grow(data: bytearray, size: int) -> None:
    """Zeros appended to `data` up to `size` bytes, from one shared 64 KiB block, so a growth
    makes no temporary of the gap's size (the build review, F4)."""
    block = memoryview(ZEROS)
    while len(data) < size:
        data += block[: size - len(data)]


def _dots(ino: int) -> _Listing:
    """A listing's first two entries, `.` and `..`, encoded as wasmtime writes them."""
    data, offsets = bytearray(), array("I")
    for index, name in enumerate((b".", b"..")):
        offsets.append(len(data))
        data += struct.pack(DIRENT, index + 1, ino, len(name), DIRECTORY) + name
    return data, offsets


def _kind(value: Any) -> bool:
    return type(value) is str and value in ("file", "dir")


def _number(value: Any, top: int) -> bool:
    kind = type(value)
    if issubclass(kind, bool) or not issubclass(kind, int):
        return False
    return 0 <= int.__index__(value) <= top


def _listed(item: Any) -> tuple[str, bytes, str] | None:
    """A listing entry as (name, its UTF-8, kind), or None when it is outside the protocol: a
    plain tuple of two plain str (so no provider code runs to take it apart)."""
    if type(item) is not tuple or len(item) != 2:
        return None
    name, kind = item
    if type(name) is not str or not _kind(kind):
        return None
    if name in ("", ".", "..") or "/" in name or "\0" in name:
        return None
    try:
        encoded = name.encode("utf-8")
    except UnicodeEncodeError:
        return None  # a lone surrogate
    if len(encoded) > MAX_NAME:
        return None
    return name, encoded, kind


def _close(iterator: Any) -> None:
    """Close a provider's iterator, as a for loop left early would not; never raising."""
    if iterator is None:
        return
    try:
        close = getattr(iterator, "close", None)
        if close is not None:
            close()
    except Exception:
        pass


def _get_fuel(context: Any) -> int:
    from wasmtime import WasmtimeError, _ffi

    fuel = ctypes.c_uint64()
    error = _ffi.wasmtime_context_get_fuel(context, ctypes.byref(fuel))
    if error:
        raise WasmtimeError._from_ptr(error)
    return fuel.value


def _set_fuel(context: Any, fuel: int) -> None:
    from wasmtime import WasmtimeError, _ffi

    error = _ffi.wasmtime_context_set_fuel(context, fuel)
    if error:
        WasmtimeError._from_ptr(error)  # owned, so freed; a metered store never refuses


__all__ = [
    "Errno",
    "FileFault",
    "FileProvider",
    "FileRecord",
    "Mount",
    "RefusedWrite",
    "Stat",
    "WritableFileProvider",
]
