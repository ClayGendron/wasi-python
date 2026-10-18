"""Read-only mounts (spec 032): a provider's files at a guest path, served from embedder code.

    from wasi_python import Mount, run

    done = run(argv, mounts=[Mount(files, "/work")])

A provider answers three methods on normalized, absolute paths (`/` is the mount itself): `stat`,
`list` and `read`, each returning a value or an `Errno`, never raising. The runner owns every
descriptor, offset, flag, cookie and pointer; the provider sees only normalized paths.

How it works: on a call with mounts, the guest's 29 preview1 calls that act on a descriptor and
are not forward-safe are shadowed (`SHADOWED`). Each finds its call on the thread's stack (spec
011). A call that names a number in the call's mount table is served here; any other is forwarded
to wasmtime's own WASI through a small trampoline instantiated on the guest's memory, by
`wasmtime_func_call` on the caller's context, fuel-neutral. Each mount is preopened on an empty,
read-only placeholder folder the runner owns, so wasi-libc's preopen scan finds it; a file or
folder opened in a mount gets a number from 2**30 up, which wasmtime never reaches.

wasmtime-py is imported only inside functions, so the package imports without the `run` extra.
"""

from __future__ import annotations

import ctypes
import enum
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
    sees unchanged (READ, wasi-libc's wasip1.h). The set is closed: no success, nothing that
    makes the guest's C library retry, and nothing that describes the guest's own arguments."""

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
    """What `stat` answers: "file" or "dir", the size in bytes (0 to 2**63 - 1) and the
    modification time in nanoseconds (0 to 2**64 - 1). A bool is refused for either number."""

    kind: str
    size: int = 0
    mtime_ns: int = 0


class FileProvider(Protocol):
    """The protocol a mount's provider follows (for type checkers). Paths are absolute within
    the mount and normalized by the runner. `read` answers EISDIR when the path itself is a
    folder and ENOTDIR when a parent is a file. A provider answers; it does not raise."""

    def stat(self, path: str) -> Stat | Errno: ...

    def list(self, path: str) -> Iterable[tuple[str, str]] | Errno: ...

    def read(self, path: str) -> bytes | bytearray | memoryview | Errno: ...


@dataclass(frozen=True)
class Mount:
    """A provider the guest sees at `guest`, read-only: an absolute guest path, or `/` for the
    guest's whole filesystem (not with `root=`). `run` checks every mount before any work."""

    provider: Any
    guest: str


@dataclass(frozen=True)
class FileFault:
    """One provider call that raised or answered outside its protocol: the method, the path it
    was given, and the exception's type and first line (or "bad answer: <type>")."""

    method: str
    path: str
    error: str


@dataclass(frozen=True)
class FileRecord:
    """A call's provider calls: each method's count (zeros included) and the first 1,000 faults.
    No times, and no exception objects, so a result holds no frame of the call."""

    calls: Mapping[str, int]
    faults: tuple[FileFault, ...] = ()


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

PROVIDER_BASE = 2**30  # provider numbers start here; wasmtime's own never reach it
MAX_MOUNT_FILES = 1024  # open provider numbers per call
MAX_PATH = 4096  # bytes; a longer path is ENAMETOOLONG, unread
MAX_NAME = 255  # bytes in one path component, and in one listed name
MAX_IOVECS = 1024
FAULTS_KEPT = 1000
STAGING_CEILING = 4 << 30  # wasm32's own ceiling, when memory_bytes is None
FUEL_ALLOWANCE = 1000  # covers the trampoline's few instructions; set back after each forward
FUEL_MAX = 2**63 - 1
METHODS = ("stat", "list", "read")

MASK32, MASK64 = 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF
# preview1 errno values the runner answers itself
EBADF, ECANCELED, EFAULT, EFBIG, EILSEQ, EINVAL, EIO = 8, 11, 21, 22, 25, 28, 29
EISDIR, EMFILE, ENAMETOOLONG, ENOENT, ENOTDIR, ENOTSUP, EPERM, ETIMEDOUT = (
    31,
    33,
    37,
    44,
    54,
    58,
    63,
    73,
)
DIRECTORY, REGULAR_FILE = 3, 4  # filetypes
O_CREAT, O_DIRECTORY, O_EXCL, O_TRUNC = 1, 2, 4, 8
APPEND, DSYNC, NONBLOCK, RSYNC, SYNC = 1, 2, 4, 8, 16
ATIM, ATIM_NOW, MTIM, MTIM_NOW = 1, 2, 4, 8
FD_SEEK, FD_WRITE, PATH_FILESTAT_SET_SIZE, FD_FILESTAT_SET_SIZE = 1 << 2, 1 << 6, 1 << 19, 1 << 22
RIGHTS = (1 << 30) - 1  # wasmtime 49's Rights::all()
FILE_RIGHTS = RIGHTS & ~FD_WRITE  # a file opened read-only, as wasmtime reports it
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


@dataclass
class _Open:
    """A descriptor in the mount table: a mount's own preopen, or a provider file or folder."""

    mount: _Mounted
    path: str  # within the mount, normalized
    kind: str  # "file" or "dir"
    preopen: bool = False
    data: bytes = b""  # a file's staged bytes
    position: int = 0
    append: bool = False
    nonblock: bool = False
    listing: _Listing | None = None  # the encoded entries and where each starts, dots first
    fresh: bool = False  # the listing has not yet served a pass from cookie 0
    held: int = 0  # staged bytes this descriptor holds


@dataclass
class _Forwards:
    """The trampoline's function handles and argument arrays, for one call's store only: a
    handle of one store used with another store's context aborts the process."""

    funcs: dict[str, Any]
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
                mount.provider, mount.guest, runner._siphash13(mount.guest.encode()), nested
            )
            self.mounts.append(mounted)
            self.table[number] = _Open(mounted, "/", "dir", preopen=True)
        self.limit, self.staging, self.metered = file_calls, staging, metered
        self.engine = engine
        self.calls = dict.fromkeys(METHODS, 0)
        self.total = 0
        self.faults: list[FileFault] = []
        self.staged = 0
        self.opened = 0  # provider numbers in use
        self.free: list[int] = []
        self.next = PROVIDER_BASE
        self.forwards: _Forwards | None = None
        # a forward's own error, or an ABI error the runner raised, and the guest's fuel then
        self.stop_fuel: tuple[BaseException, int] | None = None
        self.call: _Call | None = None

    def record(self) -> FileRecord:
        return FileRecord(types.MappingProxyType(dict(self.calls)), tuple(self.faults))

    def release(self) -> None:
        """Drop what the call held once it has ended (the build review, F3): the staged files
        and listings, the trampoline's handles and the link back to the call, so nothing waits
        for the cyclic collector."""
        self.table.clear()
        self.mounts.clear()
        self.forwards = None
        self.stop_fuel = None
        self.call = None
        self.staged = 0

    # The trampoline (Decision 1).

    def bind(self, wt: Any, store: Any, plain: Any, instance: Any) -> None:
        """Instantiate the trampoline on the guest's memory with wasmtime's own calls from
        `plain` (today's linker). After the guest, before the fuel cap and `_initialize`."""
        module = self._runner._trampoline_module(wt, self.engine)
        imports = [plain.get(store, "wasi_snapshot_preview1", name) for name in SIGNATURES]
        imports.append(instance.exports(store)["memory"])
        exports = wt.Instance(store, module, imports).exports(store)
        self.forwards = _Forwards({name: exports[name]._func for name in SIGNATURES})

    def forward(self, caller: Any, name: str, args: tuple[int, ...]) -> int:
        """wasmtime's own answer, on the caller's context, never through `Func.__call__` (whose
        exception slot is process-wide). Fuel-neutral on a metered call: read, raised by the
        allowance, and set back in a `finally` before any trap or error is raised."""
        from wasmtime import Trap, WasmtimeError, _ffi

        if self.forwards is None:
            return EBADF  # no trampoline yet: nothing of wasmtime's can be reached
        slot = self.forwards.slots.get(name)
        if slot is None:
            types = SIGNATURES[name]
            params = (_ffi.wasmtime_val_t * len(types))()
            for i, kind in enumerate(types):
                kinds = _ffi.WASMTIME_I32 if kind == "i32" else _ffi.WASMTIME_I64
                params[i].kind = kinds.value
            slot = (self.forwards.funcs[name], params, (_ffi.wasmtime_val_t * 1)())
            self.forwards.slots[name] = slot
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

    def _ask(self, caller: Any, mount: _Mounted, method: str, path: str) -> tuple[int, Any]:
        """One provider call, counted, or the errno that stops it first: the call's cancel, its
        deadline, then the file-call limit. (0, answer) when the provider answered."""
        r, call = self._runner, self.call
        if call is not None and call.cancel is not None and call.cancel.is_set():
            r._epoch_now(caller)  # named "cancelled" by the epoch callback at the next entry
            return ECANCELED, None
        if call is not None and call.stop_at is not None:
            if r._epoch_ticker.count() >= call.stop_at:
                r._epoch_now(caller)  # an interrupt at the next entry: "deadline"
                return ETIMEDOUT, None
        if self.limit is not None and self.total >= self.limit:
            if call is not None and call.ended is None:
                call.ended = "out of file calls"
            r._epoch_now(caller)  # in the same step: the guest stops at its next entry
            return EIO, None
        self.total += 1
        self.calls[method] += 1
        try:
            return 0, getattr(mount.provider, method)(path)
        except Exception as e:
            self._fault(method, path, _described(e))
            return EIO, None

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

    def _read(self, caller: Any, mount: _Mounted, path: str) -> tuple[int, bytes | None]:
        """(0, bytes) for a file, (0, None) for a folder (EISDIR), or (errno, None)."""
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
                return 0, view.tobytes()
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
            data, offsets = bytearray(), array("I")
            for index, name in enumerate((b".", b"..")):
                offsets.append(len(data))
                data += struct.pack(DIRENT, index + 1, ino, len(name), DIRECTORY) + name
            seen: set[bytes] = set()
            names = 0  # the bytes of the name objects the set holds
            prefix = path.rstrip("/") + "/"
            iterator = iter(answer)
            for item in iterator:
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

    def _filestat(self, entry: _Open, kind: str, size: int, mtime: int, path: str) -> bytes:
        filetype = DIRECTORY if kind == "dir" else REGULAR_FILE
        ino = self._runner._siphash13(path.encode())
        return struct.pack(
            FILESTAT,
            entry.mount.dev,
            ino,
            filetype,
            1,
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
        if entry.preopen:
            errno = self.forward(caller, "fd_close", (fd,))
            if errno == 0:
                self._drop(fd & MASK32)  # wasmtime freed the number: it is no longer the mount's
            return errno
        self._drop(fd & MASK32)
        return 0

    def _fd_datasync(self, caller: Any, fd: int) -> int:
        entry = self._entry(fd)
        if entry is None or entry.preopen:
            return self.forward(caller, "fd_datasync", (fd,))
        return 0 if entry.kind == "file" else EBADF

    def _fd_sync(self, caller: Any, fd: int) -> int:
        entry = self._entry(fd)
        if entry is None or entry.preopen:
            return self.forward(caller, "fd_sync", (fd,))
        return 0 if entry.kind == "file" else EBADF

    def _fd_fdstat_get(self, caller: Any, fd: int, ptr: int) -> int:
        entry = self._entry(fd)
        if entry is None or entry.preopen:
            return self.forward(caller, "fd_fdstat_get", (fd, ptr))
        memory = _Memory(caller)
        if errno := self._result(memory, ptr, 24, 8):
            return errno
        if entry.kind == "file":
            flags = (APPEND if entry.append else 0) | (NONBLOCK if entry.nonblock else 0)
            data = struct.pack(FDSTAT, REGULAR_FILE, flags, FILE_RIGHTS, FILE_RIGHTS)
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
        stat = self._filestat(entry, entry.kind, len(entry.data), 0, entry.path)
        memory.write(ptr & MASK32, stat)
        return 0

    def _fd_filestat_set_size(self, caller: Any, fd: int, size: int) -> int:
        entry = self._entry(fd)
        if entry is None or entry.preopen:
            return self.forward(caller, "fd_filestat_set_size", (fd, size))
        return EPERM if entry.kind == "file" else EBADF

    def _fd_filestat_set_times(self, caller: Any, fd: int, atim: int, mtim: int, flags: int) -> int:
        entry = self._entry(fd)
        if entry is None or entry.preopen:
            return self.forward(caller, "fd_filestat_set_times", (fd, atim, mtim, flags))
        flags = _flags(flags, 0xF, 0xFFFF, "Fstflags")
        if (flags & ATIM and flags & ATIM_NOW) or (flags & MTIM and flags & MTIM_NOW):
            return EINVAL
        return EPERM

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
        if entry.kind != "file":
            return EBADF
        at = entry.position if offset is None else offset
        if at >= 2**63:
            return EINVAL  # the host refuses an offset past i64, as wasmtime's read does
        buf, size = chosen
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
        return self._writes(caller, iovs, count, nwritten)

    def _fd_pwrite(
        self, caller: Any, fd: int, iovs: int, count: int, offset: int, nwritten: int
    ) -> int:
        entry = self._entry(fd)
        if entry is None or entry.preopen:
            return self.forward(caller, "fd_pwrite", (fd, iovs, count, offset, nwritten))
        return self._writes(caller, iovs, count, nwritten)

    def _writes(self, caller: Any, iovs: int, count: int, nwritten: int) -> int:
        """A write on a descriptor opened read-only: the host refuses it with EBADF."""
        memory = _Memory(caller)
        chosen = self._iovecs(memory, iovs, count)
        if isinstance(chosen, int):
            return chosen
        if errno := self._result(memory, nwritten, 4, 4):
            return errno
        return EBADF

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
            return self.forward(caller, "fd_readdir", (fd, buf, length, cookie, used))
        memory = _Memory(caller)
        buf, length, cookie = buf & MASK32, length & MASK32, cookie & MASK64
        if not memory.fits(buf, length):
            return EFAULT
        if errno := self._result(memory, used, 4, 4):
            return errno
        if entry.kind != "dir":
            return EBADF
        if entry.listing is None or (cookie == 0 and not entry.fresh):
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
        if oflags & (O_CREAT | O_TRUNC) or base_rights & FD_WRITE:
            return EPERM  # a read-only grant's answer, before any provider call (Decision 6)
        resolved = self._resolve(entry, text)
        if isinstance(resolved, int):
            return resolved
        path, folder_only = resolved
        if self.opened >= MAX_MOUNT_FILES:
            return EMFILE  # before the provider: no call, none counted
        mount = entry.mount
        if oflags & O_DIRECTORY:
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
        memory = _Memory(caller)
        for ptr, length in paths:
            raw = self._path(memory, ptr, length)
            if isinstance(raw, int):
                return raw
            text = self._text(raw)
            if isinstance(text, int):
                return text
        return 0

    def _path_create_directory(self, caller: Any, fd: int, ptr: int, length: int) -> int:
        entry = self._entry(fd)
        if entry is None:
            return self.forward(caller, "path_create_directory", (fd, ptr, length))
        return self._refused(caller, entry, (ptr, length))

    def _path_remove_directory(self, caller: Any, fd: int, ptr: int, length: int) -> int:
        entry = self._entry(fd)
        if entry is None:
            return self.forward(caller, "path_remove_directory", (fd, ptr, length))
        return self._refused(caller, entry, (ptr, length))

    def _path_unlink_file(self, caller: Any, fd: int, ptr: int, length: int) -> int:
        entry = self._entry(fd)
        if entry is None:
            return self.forward(caller, "path_unlink_file", (fd, ptr, length))
        return self._refused(caller, entry, (ptr, length))

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
        return self._refused(caller, entry, (ptr, length))

    def _path_symlink(
        self, caller: Any, old: int, old_length: int, fd: int, new: int, new_length: int
    ) -> int:
        entry = self._entry(fd)
        if entry is None:
            return self.forward(caller, "path_symlink", (old, old_length, fd, new, new_length))
        return self._refused(caller, entry, (old, old_length), (new, new_length))

    def _across(self, caller: Any, a: int, b: int, *paths: tuple[int, int]) -> int:
        """A rename or link that names a number of the table: each side must be a folder (a
        number of wasmtime's is asked of wasmtime, with no side effect), then the paths are
        read; a read-only side refuses, as across two read-only grants."""
        for fd in (a, b):
            entry = self._entry(fd)
            if entry is not None:
                if entry.kind != "dir":
                    return EBADF
            elif not self._wasmtime_folder(caller, fd):
                return EBADF
        return self._read_paths(caller, paths) or EPERM

    def _wasmtime_folder(self, caller: Any, fd: int) -> bool:
        """Whether wasmtime's number is a folder: fd_fdstat_set_rights answers ENOTSUP on any
        open file or folder and fd_allocate EBADF on anything but a file; neither changes it."""
        rights = self.forward(caller, "fd_fdstat_set_rights", (fd, 0, 0))
        return rights == ENOTSUP and self.forward(caller, "fd_allocate", (fd, 0, 0)) == EBADF

    def _path_rename(
        self, caller: Any, fd: int, old: int, old_length: int, to: int, new: int, new_length: int
    ) -> int:
        if self._entry(fd) is None and self._entry(to) is None:
            args = (fd, old, old_length, to, new, new_length)
            return self.forward(caller, "path_rename", args)
        return self._across(caller, fd, to, (old, old_length), (new, new_length))

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
        if self._entry(fd) is None and self._entry(to) is None:
            args = (fd, flags, old, old_length, to, new, new_length)
            return self.forward(caller, "path_link", args)
        _lookup(flags)
        return self._across(caller, fd, to, (old, old_length), (new, new_length))


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


__all__ = ["Errno", "FileFault", "FileProvider", "FileRecord", "Mount", "Stat"]
