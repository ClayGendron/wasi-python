"""The preview1 ABI as bytes: the calls a call's table shadows and their raw parameters, the
numbers wasi-libc and wasmtime agree on (errnos, flags, rights, limits, struct formats), the
trampoline's WAT, the argument checks wasmtime's ABI makes, and the readers of the guest's memory,
each of which checks a pointer and a length before a byte is read.

wasmtime-py is imported only inside functions, so the package imports without the `run` extra.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any, Protocol, cast

# The 29 preview1 calls that act on a descriptor and are not forward-safe, with their raw
# parameters (the result is one i32): every call the guest's file traffic can name a provider
# number in. fd_renumber, fd_allocate and fd_fdstat_set_rights are not imported by today's
# binaries (the reactor refuses qhull's freopen, fd_renumber's one user); they are
# shadowed so a later binary cannot reach a provider number unseen.
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
# as for a grant's.
FORWARD_SAFE = (
    "fd_prestat_get",
    "fd_prestat_dir_name",
    "sock_accept",
    "sock_recv",
    "sock_send",
    "sock_shutdown",
    "poll_oneoff",
)

# The calls that make or free a descriptor the guest holds: in wasmtime's preview1 only
# path_open adds one, fd_close frees one, and fd_renumber frees `to` and moves `from` there.
# Shadowed on calls without mounts too, permanently, so the table counts against the call's cap.
COUNTED = ("path_open", "fd_close", "fd_renumber")

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
WRITE_HALF = METHODS[3:]  # a writable mount's provider has each of these

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
ENXIO = 60  # a special file: no such device or address, as a sealed host answers its open
DIRECTORY, REGULAR_FILE, SYMBOLIC_LINK = 3, 4, 7  # filetypes
O_CREAT, O_DIRECTORY, O_EXCL, O_TRUNC = 1, 2, 4, 8
APPEND, DSYNC, NONBLOCK, RSYNC, SYNC = 1, 2, 4, 8, 16
ATIM, ATIM_NOW, MTIM, MTIM_NOW = 1, 2, 4, 8
FD_READ, FD_SEEK, FD_WRITE, FD_READDIR = 1 << 1, 1 << 2, 1 << 6, 1 << 14
PATH_FILESTAT_SET_SIZE, FD_FILESTAT_SET_SIZE = 1 << 19, 1 << 22
RIGHTS = (1 << 30) - 1  # wasmtime 49's Rights::all()
FILE_RIGHTS = RIGHTS & ~FD_WRITE  # a file opened read-only, as wasmtime reports it
OFFSET_TOP = 2**63  # an offset, a position or a size from here on: the host's EINVAL
# Which trailing `/` makes a rename served in a writable mount need a folder source: (the
# source's, the destination's). Either path's counts, as in wasmtime's own rename on a grant,
# which the parity holds the mount to: the source is a folder, judged without following its own
# link, or the rename is ENOTDIR. The source is judged by one `stat`, after the runner's own
# answers (the path rules, EBUSY, EINVAL) and before the provider's `rename`, so nothing is
# renamed before the stat's errno or ENOTDIR.
RENAME_SLASH_NEEDS_FOLDER = (True, True)
ZEROS = bytes(1 << 16)  # the block a buffer grows from
DIR_RIGHTS = RIGHTS & ~(FD_SEEK | FD_WRITE | PATH_FILESTAT_SET_SIZE | FD_FILESTAT_SET_SIZE)
FILESTAT = "<QQB7xQQQQQ"  # dev, ino, filetype, nlink, size, atim, mtim, ctim: 64 bytes
FILESTAT_SIZE, FILETYPE_AT = 64, 16  # a filestat's size, and where its filetype lies
FDSTAT = "<BxH4xQQ"  # filetype, flags, rights base and inheriting: 24 bytes
DIRENT = "<QQIB3x"  # d_next, d_ino, d_namlen, d_type: 24 bytes


def trampoline_wat() -> str:
    """The forwarders: each imports one of wasmtime's own calls and exports a function that calls
    it, beside the guest's memory re-exported as `memory`, which wasmtime's WASI reads through
    the calling instance."""
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


class _AbiMarked(Protocol):
    """An error marked as an ABI refusal, the mark the handler reads back."""

    abi: bool


def _ends(message: str) -> BaseException:
    """What wasmtime gives a guest that passes an argument its ABI cannot carry (a flag or enum
    value it does not define, an integer out of its type's range, a misaligned pointer): an
    error that ends the run. Raised to the shared function, which records it as the stop."""
    import wasmtime

    error = wasmtime.WasmtimeError(message)
    cast(_AbiMarked, error).abi = True
    return error


def _unsigned(value: int, top: int, name: str) -> int:
    """A raw argument as wiggle converts it: the i32 or i64 taken as signed, which must fit the
    WASI type, or the run ends, in wasmtime's words, which name the direction: a mount answers
    as a grant does."""
    if value < 0:
        raise _ends("number too small to fit in target type")
    if value > top:
        raise _ends("number too large to fit in target type")
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


@dataclass
class _Forwards:
    """The trampoline's function handles and argument arrays, for one call's store only: a
    handle of one store used with another store's context aborts the process."""

    funcs: dict[str, Any]
    slots: dict[str, Any] = field(default_factory=dict)  # the seam's prepared calls


class _Memory:
    """The guest's memory for one host call: every pointer and length is checked against its
    size before a byte is read or written."""

    def __init__(self, caller: Any) -> None:
        import wasmtime

        self.caller = caller
        memory = caller.get("memory")
        self.memory = memory if isinstance(memory, wasmtime.Memory) else None
        self.size = 0 if self.memory is None else self.memory.data_len(caller)

    def fits(self, ptr: int, length: int) -> bool:
        return self.memory is not None and ptr + length <= self.size

    def read(self, ptr: int, length: int) -> bytes:  # after `fits`, so the memory is there
        memory = self.memory
        return bytes(memory.read(self.caller, ptr, ptr + length)) if length and memory else b""

    def write(self, ptr: int, data: bytes | bytearray) -> None:
        if data and self.memory:
            self.memory.write(self.caller, data, ptr)


def _aligned(ptr: int, align: int) -> None:
    if ptr % align:
        raise _ends(f"Pointer not aligned to {align}")


def _path(memory: _Memory, ptr: int, length: int) -> bytes | int:
    """The guest's path bytes, after its pointer and length are checked."""
    ptr, length = ptr & MASK32, length & MASK32
    if not memory.fits(ptr, length):
        return EFAULT
    if length > MAX_PATH:
        return ENAMETOOLONG
    return memory.read(ptr, length)


def _text(raw: bytes) -> str | int:
    """UTF-8, as wasmtime decodes a path when it reads it."""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return EILSEQ


def _iovecs(memory: _Memory, ptr: int, count: int) -> tuple[int, int] | int:
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


def _result(memory: _Memory, ptr: int, size: int, align: int) -> int:
    """0 when a result of `size` bytes fits at `ptr`; EFAULT when it does not."""
    ptr &= MASK32
    if not memory.fits(ptr, size):
        return EFAULT
    _aligned(ptr, align)
    return 0


def _filestat(dev: int, ino: int, kind: str, size: int, mtime: int, links: int = 1) -> bytes:
    """A filestat as wasmtime packs one: a file's size, a folder's 0, and one time for all three."""
    filetype = DIRECTORY if kind == "dir" else REGULAR_FILE
    size = size if kind == "file" else 0
    return struct.pack(FILESTAT, dev, ino, filetype, links, size, mtime, mtime, mtime)
