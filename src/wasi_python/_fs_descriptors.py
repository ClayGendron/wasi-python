"""The descriptor calls (`fd_*`) over a call's mount table, one function per call, each taking the
table as `files`. A number not in the table is wasmtime's: forwarded. A mount's own preopen is an
empty, read-only folder of the runner's, so a call wasmtime answers alike for every read-only
preopen is forwarded too; its listing, its stat and the paths under it are the provider's. A
function reads the table's fields and changes its state only through the table's methods.
"""

from __future__ import annotations

import struct
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from ._fs_memory import (
    APPEND,
    ATIM,
    ATIM_NOW,
    DIR_RIGHTS,
    DIRECTORY,
    DSYNC,
    EBADF,
    EFAULT,
    EFBIG,
    EINVAL,
    EIO,
    ENOTSUP,
    EPERM,
    FD_READ,
    FD_READDIR,
    FD_WRITE,
    FDSTAT,
    MASK32,
    MASK64,
    MTIM,
    MTIM_NOW,
    NONBLOCK,
    OFFSET_TOP,
    PREAD_CHUNK,
    PROVIDER_BASE,
    REGULAR_FILE,
    RIGHTS,
    RSYNC,
    SYNC,
    ZEROS,
    _enum,
    _filestat,
    _flags,
    _iovecs,
    _Memory,
    _result,
    _rights,
)
from .mounts import _Open

if TYPE_CHECKING:
    from ._fs_table import _Files


def _fd_advise(files: _Files, caller: Any, fd: int, offset: int, length: int, advice: int) -> int:
    entry = files._entry(fd)
    if entry is None or entry.preopen:
        return files.forward(caller, "fd_advise", (fd, offset, length, advice))
    _enum(advice, 5, "Advice")
    return 0 if entry.kind == "file" else EBADF


def _fd_allocate(files: _Files, caller: Any, fd: int, offset: int, length: int) -> int:
    entry = files._entry(fd)
    if entry is None or entry.preopen:
        return files.forward(caller, "fd_allocate", (fd, offset, length))
    return ENOTSUP if entry.kind == "file" else EBADF


def _fd_close(files: _Files, caller: Any, fd: int) -> int:
    entry = files._entry(fd)
    if entry is None:
        errno = files.forward(caller, "fd_close", (fd,))
        if errno == 0:
            files._unhold(fd & MASK32)  # a number the guest held frees its slot
        return errno
    number = fd & MASK32
    if entry.preopen:
        errno = files.forward(caller, "fd_close", (fd,))
        if errno == 0:
            files._drop(number)  # wasmtime freed the number: it is no longer the mount's
        return errno
    if not (entry.dirty and not entry.unlinked):
        files._drop(number)
        return 0
    # A dirty buffer: one write-back, then the number is freed whatever the answer, as
    # POSIX's close frees the descriptor even when it fails.
    errno, made = files._write_back(caller, entry, "close")
    if made:
        files._drop(number)
    else:
        # Not made (cancel, deadline, limit): owed. Closed for the guest, but the number
        # stays reserved, counted in `opened` and its bytes in `staged`, until the ending.
        files._owe(number, entry)
    return errno


def _fd_datasync(files: _Files, caller: Any, fd: int) -> int:
    entry = files._entry(fd)
    if entry is None or entry.preopen:
        return files.forward(caller, "fd_datasync", (fd,))
    return _sync(files, caller, entry)


def _fd_sync(files: _Files, caller: Any, fd: int) -> int:
    entry = files._entry(fd)
    if entry is None or entry.preopen:
        return files.forward(caller, "fd_sync", (fd,))
    return _sync(files, caller, entry)


def _sync(files: _Files, caller: Any, entry: _Open) -> int:
    """A dirty buffer's write-back, its answer the guest's; a clean one, an unlinked one or
    one that may not write needs no call. A folder is EBADF."""
    if entry.kind != "file":
        return EBADF
    if entry.dirty and not entry.unlinked:
        return files._write_back(caller, entry, "sync")[0]
    return 0


def _fd_fdstat_get(files: _Files, caller: Any, fd: int, ptr: int) -> int:
    entry = files._entry(fd)
    if entry is None or entry.preopen:
        return files.forward(caller, "fd_fdstat_get", (fd, ptr))
    memory = _Memory(caller)
    if errno := _result(memory, ptr, 24, 8):
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


def _fd_fdstat_set_flags(files: _Files, caller: Any, fd: int, flags: int) -> int:
    entry = files._entry(fd)
    if entry is None or entry.preopen:
        return files.forward(caller, "fd_fdstat_set_flags", (fd, flags))
    flags = _flags(flags, 0x1F, 0xFFFF, "Fdflags")
    if entry.kind != "file":
        return EBADF
    if flags & (DSYNC | RSYNC | SYNC):
        return EINVAL
    entry.append, entry.nonblock = bool(flags & APPEND), bool(flags & NONBLOCK)
    return 0


def _fd_fdstat_set_rights(files: _Files, caller: Any, fd: int, base: int, inheriting: int) -> int:
    entry = files._entry(fd)
    if entry is None or entry.preopen:
        return files.forward(caller, "fd_fdstat_set_rights", (fd, base, inheriting))
    _rights(base)
    _rights(inheriting)
    return ENOTSUP


def _fd_filestat_get(files: _Files, caller: Any, fd: int, ptr: int) -> int:
    entry = files._entry(fd)
    if entry is None:
        return files.forward(caller, "fd_filestat_get", (fd, ptr))
    memory = _Memory(caller)
    if errno := _result(memory, ptr, 64, 8):
        return errno
    # No provider call: the kind and size are the staged bytes', and the times are 0.
    links = 0 if entry.unlinked else 1  # an unlinked file has no name left
    ino = files.context.ino_of(entry.path)
    stat = _filestat(entry.mount.dev, ino, entry.kind, len(entry.data), 0, links)
    memory.write(ptr & MASK32, stat)
    return 0


def _fd_filestat_set_size(files: _Files, caller: Any, fd: int, size: int) -> int:
    entry = files._entry(fd)
    if entry is None or entry.preopen:
        return files.forward(caller, "fd_filestat_set_size", (fd, size))
    if entry.kind != "file":
        return EBADF
    if not entry.mount.writable:
        return EPERM  # a read-only grant's answer
    size &= MASK64
    if size >= OFFSET_TOP or not entry.writable:
        return EINVAL  # the host's ftruncate: past i64, or a descriptor not open to write
    if not files._fits(entry, size):
        return EFBIG
    data = entry.data
    assert isinstance(data, bytearray)
    if size < len(data):
        del data[size:]
    else:
        _grow(data, size)
    files._changed(entry)
    return 0


def _fd_filestat_set_times(
    files: _Files, caller: Any, fd: int, atim: int, mtim: int, flags: int
) -> int:
    entry = files._entry(fd)
    if entry is None or (entry.preopen and not entry.mount.writable):
        return files.forward(caller, "fd_filestat_set_times", (fd, atim, mtim, flags))
    flags = _flags(flags, 0xF, 0xFFFF, "Fstflags")
    if (flags & ATIM and flags & ATIM_NOW) or (flags & MTIM and flags & MTIM_NOW):
        return EINVAL
    # Times are the provider's: a writable mount accepts and ignores
    # them, its own preopen included, as a writable grant accepts the call.
    return 0 if entry.mount.writable else EPERM


def _fd_read(files: _Files, caller: Any, fd: int, iovs: int, count: int, nread: int) -> int:
    entry = files._entry(fd)
    if entry is None or entry.preopen:
        return files.forward(caller, "fd_read", (fd, iovs, count, nread))
    return _reads(files, caller, entry, iovs, count, None, nread)


def _fd_pread(
    files: _Files, caller: Any, fd: int, iovs: int, count: int, offset: int, nread: int
) -> int:
    entry = files._entry(fd)
    if entry is None or entry.preopen:
        return files.forward(caller, "fd_pread", (fd, iovs, count, offset, nread))
    return _reads(files, caller, entry, iovs, count, offset & MASK64, nread)


def _reads(
    files: _Files, caller: Any, entry: _Open, iovs: int, count: int, offset: int | None, nread: int
) -> int:
    memory = _Memory(caller)
    chosen = _iovecs(memory, iovs, count)
    if isinstance(chosen, int):
        return chosen
    if errno := _result(memory, nread, 4, 4):
        return errno
    if entry.kind != "file" or not entry.readable:
        return EBADF  # a folder, or a file opened only to write
    at = entry.position if offset is None else offset
    buf, size = chosen
    # As Linux answers a grant (the reference): an offset past i64, or a read
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


def _fd_write(files: _Files, caller: Any, fd: int, iovs: int, count: int, nwritten: int) -> int:
    entry = files._entry(fd)
    if entry is None or entry.preopen:
        return files.forward(caller, "fd_write", (fd, iovs, count, nwritten))
    return _writes(files, caller, entry, iovs, count, None, nwritten)


def _fd_pwrite(
    files: _Files, caller: Any, fd: int, iovs: int, count: int, offset: int, nwritten: int
) -> int:
    entry = files._entry(fd)
    if entry is None or entry.preopen:
        return files.forward(caller, "fd_pwrite", (fd, iovs, count, offset, nwritten))
    return _writes(files, caller, entry, iovs, count, offset & MASK64, nwritten)


def _writes(
    files: _Files,
    caller: Any,
    entry: _Open,
    iovs: int,
    count: int,
    offset: int | None,
    nwritten: int,
) -> int:
    """A write into a buffer, as wasmtime writes a writable grant's file: the first
    non-empty ciovec; on an append descriptor at the end, `fd_pwrite`'s offset
    ignored; past the end, zeros in the gap. No provider call. A descriptor that may not
    write, or a folder, is the host's EBADF."""
    memory = _Memory(caller)
    chosen = _iovecs(memory, iovs, count)
    if isinstance(chosen, int):
        return chosen
    if errno := _result(memory, nwritten, 4, 4):
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
        if not files._fits(entry, at + size):
            return EFBIG
        data = entry.data
        assert isinstance(data, bytearray)
        _grow(data, at)
        data[at : at + size] = memory.read(buf, size)
        files._changed(entry)
    if offset is None:
        entry.position = len(entry.data) if entry.append else at + size
    memory.write(nwritten & MASK32, struct.pack("<I", size))
    return 0


def _fd_seek(files: _Files, caller: Any, fd: int, offset: int, whence: int, ptr: int) -> int:
    entry = files._entry(fd)
    if entry is None or entry.preopen:
        return files.forward(caller, "fd_seek", (fd, offset, whence, ptr))
    whence = _enum(whence, 2, "Whence")
    memory = _Memory(caller)
    if errno := _result(memory, ptr, 8, 8):
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


def _fd_tell(files: _Files, caller: Any, fd: int, ptr: int) -> int:
    entry = files._entry(fd)
    if entry is None or entry.preopen:
        return files.forward(caller, "fd_tell", (fd, ptr))
    memory = _Memory(caller)
    if errno := _result(memory, ptr, 8, 8):
        return errno
    if entry.kind != "file":
        return EBADF
    memory.write(ptr & MASK32, struct.pack("<Q", entry.position))
    return 0


def _fd_readdir(
    files: _Files, caller: Any, fd: int, buf: int, length: int, cookie: int, used: int
) -> int:
    entry = files._entry(fd)
    if entry is None:
        errno = files.forward(caller, "fd_readdir", (fd, buf, length, cookie, used))
        if errno == 0:
            errno = _zeroed(files, caller, fd, buf & MASK32, length & MASK32, cookie, used & MASK32)
        return errno
    memory = _Memory(caller)
    buf, length, cookie = buf & MASK32, length & MASK32, cookie & MASK64
    if not memory.fits(buf, length):
        return EFAULT
    if errno := _result(memory, used, 4, 4):
        return errno
    if entry.kind != "dir":
        return EBADF
    if entry.unlinked:
        pass  # only its dots, kept since it was unlinked, with no provider call
    elif entry.listing is None or (cookie == 0 and not entry.fresh):
        # The listing made at open serves the first pass; from cookie 0 after that, the
        # folder is listed again, as rewinddir expects.
        ino = files.context.ino_of(entry.path)
        errno, listing, held = files._list(caller, entry.mount, entry.path, ino, entry.held)
        if errno:
            return errno
        files._relist(entry, listing, held)
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


def _zeroed(
    files: _Files, caller: Any, fd: int, buf: int, length: int, cookie: int, used: int
) -> int:
    """After a forwarded fd_readdir that answered 0: every entry's three padding bytes
    zero, as wasmtime 49.0.2 writes them (GHSA-96f6-r43r-8c24). The
    walk reads each d_namlen from the guest's buffer, which only wasmtime has written,
    unless the guest's `used` pointer lies over the listing: wasmtime writes the count there
    last, over whatever field it lands on (a d_namlen the walk would follow included).
    Then the folder is listed again on the guard's own page, for no more
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
    forwards = files.forwards
    assert forwards is not None and forwards.page is not None  # it just forwarded
    # No more than the guest's memory can hold from `buf`, so the
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
        errno = files.forward(caller, "fd_readdir", (fd, 0, length, cookie, at), stat=True)
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


def _fd_renumber(files: _Files, caller: Any, fd: int, to: int) -> int:
    """With mounts, never onto or from a number in the table, or at or above 2**30: wasmtime
    would silently replace the target (as wasmtime 49 was seen to answer). A guard table has no
    provider numbers, so it forwards whatever the numbers. A renumber
    wasmtime makes closes `to` and moves `from` there; the held set follows it, and a number
    renumbered onto itself stays held."""
    a, b = fd & MASK32, to & MASK32
    if files.mounts and (
        a in files.table or b in files.table or a >= PROVIDER_BASE or b >= PROVIDER_BASE
    ):
        return ENOTSUP
    errno = files.forward(caller, "fd_renumber", (fd, to))
    if errno == 0 and a != b:
        files._renumbered(a, b)
    return errno


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


def _grow(data: bytearray, size: int) -> None:
    """Zeros appended to `data` up to `size` bytes, from one shared 64 KiB block, so a growth
    makes no temporary of the gap's size."""
    block = memoryview(ZEROS)
    while len(data) < size:
        data += block[: size - len(data)]


HANDLERS: dict[str, Callable[..., int]] = {
    "fd_advise": _fd_advise,
    "fd_allocate": _fd_allocate,
    "fd_close": _fd_close,
    "fd_datasync": _fd_datasync,
    "fd_fdstat_get": _fd_fdstat_get,
    "fd_fdstat_set_flags": _fd_fdstat_set_flags,
    "fd_fdstat_set_rights": _fd_fdstat_set_rights,
    "fd_filestat_get": _fd_filestat_get,
    "fd_filestat_set_size": _fd_filestat_set_size,
    "fd_filestat_set_times": _fd_filestat_set_times,
    "fd_pread": _fd_pread,
    "fd_pwrite": _fd_pwrite,
    "fd_read": _fd_read,
    "fd_readdir": _fd_readdir,
    "fd_renumber": _fd_renumber,
    "fd_seek": _fd_seek,
    "fd_sync": _fd_sync,
    "fd_tell": _fd_tell,
    "fd_write": _fd_write,
}
