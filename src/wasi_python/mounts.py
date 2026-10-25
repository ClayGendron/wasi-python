"""Mounts: a provider's files at a guest path, served from embedder code.

    from wasi_python import Mount, run

    done = run(argv, mounts=[Mount(files, "/work")])
    done = run(argv, mounts=[Mount(store, "/work", writable=True)])

A provider answers three methods on normalized, absolute paths (`/` is the mount itself): `stat`,
`list` and `read`, each returning a value or an `Errno`, or raising an `OSError` whose errno (by
name) or, with no errno, whose class names one. A writable mount's provider also
answers the write half (`write`, `mkdir`, `remove`, `rmdir`, `rename`), each `None` or an
`Errno`, raised the same way; a file's bytes are staged in the runner and handed over whole at
open (a create or truncation), at close, at sync and at the call's ending. The runner owns every
descriptor, offset, flag, cookie and pointer; the provider sees only normalized paths.

How a call is served is the four modules beside this one: the bytes that cross the WASI
boundary (`_fs_memory`), the table a call holds and its provider calls (`_fs_table`), and the
descriptor and path calls over it (`_fs_descriptors`, `_fs_paths`). This module is what they
and the runner speak: the public types, the two private rows a call keeps of them, the
protocol the table asks its host through, and how a provider's `OSError` is read.
"""

from __future__ import annotations

import enum
import errno as _host_errno
from array import array
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol


class Errno(enum.IntEnum):
    """An answer a provider gives instead of a value: WASI preview1's numbers, which the guest
    sees unchanged, each as the `OSError` of that errno. The set is closed: no success, nothing
    that makes the guest's C library retry, and nothing that describes the guest's own
    arguments."""

    # The numbers: READ, wasi-libc's wasip1.h.

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
    in preview1's numbering. An `OSError` it raises is a refusal when its errno (by name) or,
    with no errno, its class names a member, as for the read half. A file's bytes are staged by
    the runner and handed over whole at open (a create or a truncation), at close, at sync and
    at the call's ending.
    """

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


# A provider's OSError: the answer of its errno, matched by name, never by number,
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


_Listing = tuple[bytearray, "array[int]"]  # a folder's encoded preview1 entries and their offsets


@dataclass
class _Mounted:
    """One mount as a call holds it."""

    provider: Any
    guest: str
    dev: int  # _siphash13 of the guest path
    nested: tuple[str, ...]  # more specific preopens, as paths within this mount
    writable: bool = False  # the embedder said so; else no write-half call is made


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
    writable: bool = False  # it may write: CREAT or TRUNC, or FD_WRITE asked for
    dirty: bool = False  # the provider has not been given these bytes
    unlinked: bool = False  # the guest removed or replaced its path in this call


class _CallContext(Protocol):
    """What the mount table asks of its host: four process-wide answers and five of the call it
    serves, one object for all nine, so the table imports nothing of the runner."""

    def ino_of(self, path: str) -> int: ...  # SipHash-1-3 of a guest path, 64 bits
    def trampoline(self, wt: Any, engine: Any) -> Any: ...  # the forwarders' module
    def exiting(self) -> bool: ...  # the interpreter is exiting: no provider code may run
    def ctrl_c_pending(self) -> bool: ...  # a deferred Ctrl-C waits for this call
    def stop_now(self, caller: Any) -> None: ...  # stop, or the epoch callback, at the next entry
    def cancelled(self) -> bool: ...  # the call's cancel is set
    def deadline_passed(self) -> bool: ...  # the call's deadline tick has been reached
    def name_end(self, reason: str) -> None: ...  # names the call's end once; a first name holds
    def on_home(self, fn: Callable[..., Any], *args: Any) -> Any: ...  # the embedder's thread


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
