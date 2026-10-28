"""The path calls (`path_*`) over a call's mount table, one function per call, each taking the
table as `files`: the path rules, the opens and the namespace calls of a writable mount. A
function reads the table's fields and changes its
state only through the table's methods.
"""

from __future__ import annotations

import struct
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from ._fs_memory import (
    APPEND,
    ATIM,
    ATIM_NOW,
    DIRECTORY,
    DSYNC,
    EBADF,
    EBUSY,
    EEXIST,
    EFAULT,
    EINVAL,
    EISDIR,
    EMFILE,
    ENAMETOOLONG,
    ENOENT,
    ENOTDIR,
    ENOTSUP,
    ENXIO,
    EPERM,
    EXDEV,
    FD_READ,
    FD_WRITE,
    FILESTAT_SIZE,
    FILETYPE_AT,
    MASK32,
    MAX_MOUNT_FILES,
    MAX_NAME,
    MTIM,
    MTIM_NOW,
    NONBLOCK,
    O_CREAT,
    O_DIRECTORY,
    O_EXCL,
    O_TRUNC,
    REGULAR_FILE,
    RENAME_SLASH_NEEDS_FOLDER,
    RIGHTS,
    RSYNC,
    SYMBOLIC_LINK,
    SYNC,
    _filestat,
    _flags,
    _lookup,
    _Memory,
    _path,
    _result,
    _rights,
    _text,
)
from .mounts import _Mounted, _Open

if TYPE_CHECKING:
    from ._fs_table import _Files


def _resolve(base: _Open, text: str) -> tuple[str, bool] | int:
    """The path within the mount and whether it must name a folder, or the errno."""
    if not text:
        return ENOENT
    if text.startswith("/"):
        return EPERM
    if "\0" in text or "\\" in text or ":" in text:
        # A backslash or a colon is a separator or a drive to some host's path logic: refused
        # on every host, so a provider never sees a name a host could read another way.
        return EINVAL
    parts = text.split("/")
    if any(len(part.encode()) > MAX_NAME for part in parts):
        return ENAMETOOLONG
    if base.unlinked:
        return ENOENT  # an open, removed folder holds nothing
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


def _path_open(
    files: _Files,
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
    entry = files._entry(fd)
    args = (fd, dirflags, ptr, length, oflags, base_rights, inheriting, fdflags, out)
    if entry is None:
        return _forwarded_open(files, caller, args)
    _lookup(dirflags)
    oflags = _flags(oflags, 0xF, 0xFFFF, "Oflags")
    base_rights = _rights(base_rights)
    _rights(inheriting)
    fdflags = _flags(fdflags, 0x1F, 0xFFFF, "Fdflags")
    memory = _Memory(caller)
    raw = _path(memory, ptr, length)
    if isinstance(raw, int):
        return raw
    if errno := _result(memory, out, 4, 4):
        return errno
    text = _text(raw)
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
        return EPERM  # a read-only grant's answer, before any provider call
    resolved = _resolve(entry, text)
    if isinstance(resolved, int):
        return resolved
    path, folder_only = resolved
    if files.opened >= MAX_MOUNT_FILES or files._at_cap():
        return EMFILE  # before the provider: no call, none counted
    if writes:
        opened = _open_writing(files, caller, mount, path, folder_only, oflags, base_rights)
        if isinstance(opened, int):
            return opened
        opened.append, opened.nonblock = bool(fdflags & APPEND), bool(fdflags & NONBLOCK)
    elif oflags & O_DIRECTORY:
        opened = _open_folder(files, caller, mount, path)
        if isinstance(opened, int):
            return opened
    else:
        errno, data = files._read(caller, mount, path)
        if errno:
            return errno
        if data is None:
            opened = _Open(mount, path, "dir")
        elif folder_only:
            return ENOTDIR
        else:
            opened = _Open(mount, path, "file", data=data, held=len(data))
            opened.append, opened.nonblock = bool(fdflags & APPEND), bool(fdflags & NONBLOCK)
    number = files._take(opened)
    memory.write(out & MASK32, struct.pack("<I", number))
    return 0


def _open_folder(files: _Files, caller: Any, mount: _Mounted, path: str) -> _Open | int:
    """An `O_DIRECTORY` open to read: the path is asked `stat` first, so a file answers ENOTDIR
    as on a grant and a lenient provider is never asked to list it; then the listing is made.
    The mount itself is a folder, and is listed with no `stat`."""
    if path != "/":
        errno, kind, _, _ = files._stat(caller, mount, path)
        if errno or kind != "dir":
            return errno or ENOTDIR
    errno, listing, held = files._list(caller, mount, path, files.context.ino_of(path))
    if errno:
        return errno
    return _Open(mount, path, "dir", listing=listing, fresh=True, held=held)


def _forwarded_open(files: _Files, caller: Any, args: tuple[int, ...]) -> int:
    """A path_open on a descriptor of wasmtime's: the cap, the look, then wasmtime's own open,
    whose new number the table holds. One answer differs from wasmtime's: an open that asks to
    write a special file on a read-only grant is refused by the look, ENXIO, or ENOTDIR with
    O_DIRECTORY, where wasmtime answers EPERM from its permission check before its host open;
    the table does not record which grant a held folder came from, and both refuse with nothing
    opened."""
    if files._at_cap():
        return EMFILE  # at the cap: nothing looked at, nothing forwarded, nothing opened
    if errno := _look(files, caller, args):
        return errno
    errno = files.forward(caller, "path_open", args)
    if errno == 0:  # wasmtime wrote the new number at `out`, so it is in memory
        (number,) = struct.unpack("<I", _Memory(caller).read(args[8] & MASK32, 4))
        files._hold(number)
    return errno


def _look(files: _Files, caller: Any, args: tuple[int, ...]) -> int:
    """0 to forward an open to wasmtime, or the errno that refuses it. A host's open of a FIFO
    waits in the kernel for the other end, and the deadline, a cancel and Ctrl-C stop wasm code
    only, so what the open would reach is looked at first, and anything that is not a folder, a
    regular file or a link the open will not follow is refused (`_refusal`).

    The look is wasmtime's own path_filestat_get on the open's descriptor, lookup flags and
    path: the name resolves as the open will resolve it, inside wasmtime's sandbox, following
    links exactly when the open follows them, so a link the guest made to a FIFO is refused as
    the FIFO is. Its 64-byte answer is written over the guest's bytes 0 to 63, which are put
    back before the open; wasmtime copies the path before it writes the answer, so a path lying
    there is read whole, and the guest, inside its own host call on its one thread, cannot see
    them change.

    No look is made for an open wasmtime refuses before its host open (`_looked_at`), or for a
    path or window the memory does not hold, so those answers stay wasmtime's. `out` is not
    looked at: a special file is refused whatever `out` holds, where wasmtime would open it and
    then end the run on a bad `out`, since forwarding it would reach the open that waits. A look
    that ends in a wasmtime error refuses with ENXIO and records no stop: a later wasmtime ends
    the call on a socket, and the runner's own epoch stop, met there, has recorded the end.

    What a look cannot close: a host process, or another call writing the same grant, that
    swaps the name between the look and the open."""
    fd, dirflags, ptr, length, oflags, base, inheriting, fdflags, _ = args
    memory = _Memory(caller)
    ptr, length = ptr & MASK32, length & MASK32
    if not _looked_at(dirflags, oflags, fdflags, base, inheriting):
        return 0
    if not (memory.fits(ptr, length) and memory.fits(0, FILESTAT_SIZE)):
        return 0
    saved = memory.read(0, FILESTAT_SIZE)
    try:
        look = (fd, dirflags, ptr, length, 0)
        errno = files.forward(caller, "path_filestat_get", look, ends=False)
        filetype = memory.read(FILETYPE_AT, 1)[0]
    finally:
        memory.write(0, saved)
    if errno is None:
        return ENXIO
    return 0 if errno else _refusal(filetype, oflags)


def _looked_at(dirflags: int, oflags: int, fdflags: int, base: int, inheriting: int) -> bool:
    """Whether wasmtime takes an open with these arguments to its host open, where a special
    file could make it wait: not one with a lookup flag, an open flag, a descriptor flag or a
    right wasmtime does not define (it ends the run at their conversion), a sync flag,
    O_DIRECTORY with a create, or O_CREAT with O_EXCL, which the host refuses for an existing
    name before it opens anything."""
    if dirflags & ~1 or oflags & ~0xF or fdflags & ~0x1F:
        return False
    if base & ~RIGHTS or inheriting & ~RIGHTS:
        return False
    if fdflags & (SYNC | DSYNC | RSYNC) or (oflags & O_CREAT and oflags & O_EXCL):
        return False
    return not (oflags & O_DIRECTORY and oflags & (O_CREAT | O_EXCL | O_TRUNC))


def _refusal(filetype: int, oflags: int) -> int:
    """0 for a folder, a regular file or a link (seen only by a look that does not follow);
    for anything else, ENOTDIR under O_DIRECTORY, wasmtime's own answer for a non-folder, and
    ENXIO otherwise, the answer a sealed host gives for a device or a socket."""
    if filetype in (DIRECTORY, REGULAR_FILE, SYMBOLIC_LINK):
        return 0
    return ENOTDIR if oflags & O_DIRECTORY else ENXIO


def _open_writing(
    files: _Files,
    caller: Any,
    mount: _Mounted,
    path: str,
    folder_only: bool,
    oflags: int,
    rights: int,
) -> _Open | int:
    """An open that may write, on a writable mount: the table read
    top to bottom, at most two provider calls, a create or a truncation made at open by
    `write(path, b"")`. The buffer starts clean. A call the gate stops owes nothing: no
    buffer exists yet, so the open answers that errno and nothing is recorded."""
    creat, trunc = oflags & O_CREAT, oflags & O_TRUNC
    if oflags & O_DIRECTORY or folder_only:
        # A folder is never opened to write; a name that must be a folder is not a file.
        # Linux's answers, wasmtime's reference: the mount itself exists (EEXIST for "x"),
        # a create there is EISDIR, else as found.
        if path == "/":
            return EEXIST if creat and oflags & O_EXCL else EISDIR
        if creat and folder_only:
            return EISDIR
        errno, kind, _, _ = files._stat(caller, mount, path)
        return errno or (EISDIR if kind == "dir" else ENOTDIR)
    data: bytes | bytearray = bytearray()
    if creat and oflags & O_EXCL:  # "x": a name no one holds, exact within the call
        errno, kind, _, _ = files._stat(caller, mount, path)
        if errno == 0:
            return EEXIST
        if errno != ENOENT or (errno := _create(files, caller, mount, path)):
            return errno
    elif creat and trunc:  # "w": one call creates or truncates
        if errno := _create(files, caller, mount, path):
            return errno
    elif trunc:
        errno, kind, _, _ = files._stat(caller, mount, path)
        if errno:
            return errno
        if kind == "dir":
            return EISDIR
        if errno := _create(files, caller, mount, path):
            return errno
    else:  # "a", O_CREAT | O_WRONLY, "r+": the bytes, or a create when missing
        errno, got = files._read(caller, mount, path, buffer=True)
        if errno == ENOENT and creat:
            if errno := _create(files, caller, mount, path):
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


def _create(files: _Files, caller: Any, mount: _Mounted, path: str) -> int:
    """A create or a truncation at open: one `write(path, b"")`, recorded at "open" when it
    is refused."""
    return files._change(caller, mount, "write", "open", (path,), b"")[0]


def _path_filestat_get(
    files: _Files, caller: Any, fd: int, flags: int, ptr: int, length: int, out: int
) -> int:
    entry = files._entry(fd)
    if entry is None:
        return files.forward(caller, "path_filestat_get", (fd, flags, ptr, length, out))
    _lookup(flags)
    memory = _Memory(caller)
    raw = _path(memory, ptr, length)
    if isinstance(raw, int):
        return raw
    if errno := _result(memory, out, 64, 8):
        return errno
    if entry.kind != "dir":
        return EBADF
    text = _text(raw)
    if isinstance(text, int):
        return text
    resolved = _resolve(entry, text)
    if isinstance(resolved, int):
        return resolved
    path, folder_only = resolved
    errno, kind, size, mtime = files._stat(caller, entry.mount, path)
    if errno:
        return errno
    if folder_only and kind != "dir":
        return ENOTDIR
    ino = files.context.ino_of(path)
    memory.write(out & MASK32, _filestat(entry.mount.dev, ino, kind, size, mtime))
    return 0


def _path_readlink(
    files: _Files, caller: Any, fd: int, ptr: int, length: int, buf: int, size: int, used: int
) -> int:
    entry = files._entry(fd)
    if entry is None:
        return files.forward(caller, "path_readlink", (fd, ptr, length, buf, size, used))
    memory = _Memory(caller)
    raw = _path(memory, ptr, length)
    if isinstance(raw, int):
        return raw
    if not memory.fits(buf & MASK32, size & MASK32):
        return EFAULT
    if errno := _result(memory, used, 4, 4):
        return errno
    if entry.kind != "dir":
        return EBADF
    text = _text(raw)
    if isinstance(text, int):
        return text
    resolved = _resolve(entry, text)
    if isinstance(resolved, int):
        return resolved
    path, folder_only = resolved
    errno, kind, _, _ = files._stat(caller, entry.mount, path)
    if errno:
        return errno
    if folder_only and kind != "dir":
        return ENOTDIR
    return EINVAL  # a file or a folder: not a link (a mount has no links)


def _refused(files: _Files, caller: Any, entry: _Open, *paths: tuple[int, int]) -> int:
    """A write-shaped path call on a read-only folder of the table: EPERM once its paths
    are read, as wasmtime answers on a read-only grant, before any provider call."""
    if entry.kind != "dir":
        return EBADF
    return _read_paths(files, caller, paths) or EPERM


def _read_paths(files: _Files, caller: Any, paths: tuple[tuple[int, int], ...]) -> int:
    """0 when every path can be read as wasmtime reads it, else the errno."""
    texts = _texts(files, caller, paths)
    return texts if isinstance(texts, int) else 0


def _texts(files: _Files, caller: Any, paths: tuple[tuple[int, int], ...]) -> list[str] | int:
    """Every path read and decoded as wasmtime reads it, or the first errno."""
    memory, texts = _Memory(caller), []
    for ptr, length in paths:
        raw = _path(memory, ptr, length)
        if isinstance(raw, int):
            return raw
        text = _text(raw)
        if isinstance(text, int):
            return text
        texts.append(text)
    return texts


# The namespace calls of a writable mount. The answers the runner gives itself, with no provider
# call, are Linux's on a writable grant (wasmtime's reference, EXECUTED in the build's probe);
# macOS differs on some, which the parity table asserts per system.


def _path_create_directory(files: _Files, caller: Any, fd: int, ptr: int, length: int) -> int:
    entry = files._entry(fd)
    if entry is None:
        return files.forward(caller, "path_create_directory", (fd, ptr, length))
    return _namespace(files, caller, entry, ptr, length, "mkdir")


def _path_remove_directory(files: _Files, caller: Any, fd: int, ptr: int, length: int) -> int:
    entry = files._entry(fd)
    if entry is None:
        return files.forward(caller, "path_remove_directory", (fd, ptr, length))
    return _namespace(files, caller, entry, ptr, length, "rmdir")


def _path_unlink_file(files: _Files, caller: Any, fd: int, ptr: int, length: int) -> int:
    entry = files._entry(fd)
    if entry is None:
        return files.forward(caller, "path_unlink_file", (fd, ptr, length))
    return _namespace(files, caller, entry, ptr, length, "remove")


def _namespace(files: _Files, caller: Any, entry: _Open, ptr: int, length: int, method: str) -> int:
    """`mkdir`, `remove` or `rmdir`: one provider call after the path rules, or the answer
    the runner gives itself: the mount itself, a name ending in `/`, `.` or `..` (one `stat`
    decides it), and an `rmdir` strictly above a more specific preopen (EBUSY)."""
    if entry.kind != "dir":
        return EBADF
    texts = _texts(files, caller, ((ptr, length),))
    if isinstance(texts, int):
        return texts
    if not entry.mount.writable:
        return EPERM  # a read-only grant's answer, before any provider call
    resolved = _resolve(entry, texts[0])
    if isinstance(resolved, int):
        return resolved
    path, folder_only = resolved
    last, mount = texts[0].rsplit("/", 1)[-1], entry.mount
    if path == "/":  # the mount itself, as a grant's own preopen answers
        return {"mkdir": EEXIST, "remove": EISDIR, "rmdir": EINVAL}[method]
    if folder_only and (method != "mkdir" or last in (".", "..")):
        errno, kind, _, _ = files._stat(caller, mount, path)
        if errno:
            return errno
        if kind != "dir":
            return ENOTDIR
        return {"mkdir": EEXIST, "remove": EISDIR, "rmdir": EINVAL}[method]
    if method == "rmdir" and _above(mount, path):
        return EBUSY  # the guest's view of other preopens stays where it was put
    errno, _ = files._change(caller, mount, method, "call", (path,))
    if errno == 0 and method != "mkdir":
        files._follow(mount, path)
    return errno


def _above(mount: _Mounted, path: str) -> bool:
    """Whether `path` is strictly above a more specific preopen's guest path."""
    prefix = "/" if path == "/" else path + "/"
    return any(nested.startswith(prefix) for nested in mount.nested)


def _path_filestat_set_times(
    files: _Files,
    caller: Any,
    fd: int,
    flags: int,
    ptr: int,
    length: int,
    atim: int,
    mtim: int,
    fst: int,
) -> int:
    entry = files._entry(fd)
    if entry is None:
        args = (fd, flags, ptr, length, atim, mtim, fst)
        return files.forward(caller, "path_filestat_set_times", args)
    _lookup(flags)
    fst = _flags(fst, 0xF, 0xFFFF, "Fstflags")
    if (fst & ATIM and fst & ATIM_NOW) or (fst & MTIM and fst & MTIM_NOW):
        return EINVAL
    if not entry.mount.writable:
        return _refused(files, caller, entry, (ptr, length))
    if entry.kind != "dir":
        return EBADF
    texts = _texts(files, caller, ((ptr, length),))
    if isinstance(texts, int):
        return texts
    resolved = _resolve(entry, texts[0])
    if isinstance(resolved, int):
        return resolved
    if not fst or resolved[0] == "/":
        # No time to set is nothing to do: Linux's utimensat answers 0 before it looks the path
        # up, and the reference grant with it. The mount itself is always there.
        return 0
    # Times are the provider's: accepted and ignored once the path is found, as a grant answers;
    # a file named as a folder is not found.
    errno, kind, _, _ = files._stat(caller, entry.mount, resolved[0])
    return errno or (ENOTDIR if resolved[1] and kind != "dir" else 0)


def _path_symlink(
    files: _Files, caller: Any, old: int, old_length: int, fd: int, new: int, new_length: int
) -> int:
    entry = files._entry(fd)
    if entry is None:
        return files.forward(caller, "path_symlink", (old, old_length, fd, new, new_length))
    refused = _refused(files, caller, entry, (old, old_length), (new, new_length))
    if refused != EPERM or not entry.mount.writable:
        return refused
    return ENOTSUP  # the protocol has no link


def _across(
    files: _Files,
    caller: Any,
    a: int,
    b: int,
    paths: tuple[tuple[int, int], ...],
    follow: bool = False,
) -> int:
    """A rename or link between two descriptors that are not one mount's, at least one of
    them a number of the table: each side must be a folder (a number of wasmtime's is asked
    of wasmtime, with no side effect), then the paths are read; a read-only side refuses
    (EPERM), as across a writable and a read-only grant; two sides that may both be written
    are two filesystems (EXDEV), so `shutil.move` copies."""
    for fd in (a, b):
        entry = files._entry(fd)
        if entry is not None:
            if entry.kind != "dir":
                return EBADF
        elif not _wasmtime_folder(files, caller, fd):
            return EBADF
    if errno := _read_paths(files, caller, paths):
        return errno
    for fd in (a, b):
        entry = files._entry(fd)
        if entry is not None and not entry.mount.writable:
            return EPERM
    for fd in (a, b):
        if files._entry(fd) is None and not _wasmtime_writable(files, caller, fd):
            return EPERM
    if follow:
        return EINVAL  # a link that follows links, as wasmtime answers between writable sides
    return EXDEV


def _wasmtime_folder(files: _Files, caller: Any, fd: int) -> bool:
    """Whether wasmtime's number is a folder: fd_fdstat_set_rights answers ENOTSUP on any
    open file or folder and fd_allocate EBADF on anything but a file; neither changes it."""
    rights = files.forward(caller, "fd_fdstat_set_rights", (fd, 0, 0))
    return rights == ENOTSUP and files.forward(caller, "fd_allocate", (fd, 0, 0)) == EBADF


def _wasmtime_writable(files: _Files, caller: Any, fd: int) -> bool:
    """Whether wasmtime's folder may be written: `path_create_directory` of the empty path
    answers EPERM on a read-only one, before the path is looked at, and ENOENT on a writable
    one; it makes nothing (EXECUTED on Linux and macOS in the build's probe)."""
    return files.forward(caller, "path_create_directory", (fd, 0, 0)) != EPERM


def _path_rename(
    files: _Files,
    caller: Any,
    fd: int,
    old: int,
    old_length: int,
    to: int,
    new: int,
    new_length: int,
) -> int:
    a, b = files._entry(fd), files._entry(to)
    if a is None and b is None:  # two of wasmtime's numbers: wasmtime's own rename
        return files.forward(caller, "path_rename", (fd, old, old_length, to, new, new_length))
    paths = ((old, old_length), (new, new_length))
    if a is None or b is None or a.mount is not b.mount or not a.mount.writable:
        return _across(files, caller, fd, to, paths)
    if a.kind != "dir" or b.kind != "dir":
        return EBADF
    texts = _texts(files, caller, paths)
    if isinstance(texts, int):
        return texts
    first, second = _resolve(a, texts[0]), _resolve(b, texts[1])
    if isinstance(first, int):
        return first
    if isinstance(second, int):
        return second
    (src, _), (dst, _) = first, second
    mount, lasts = a.mount, [text.rsplit("/", 1)[-1] for text in texts]
    needs_folder = any(
        counts and text.endswith("/")
        for counts, text in zip(RENAME_SLASH_NEEDS_FOLDER, texts, strict=True)
    )
    if "/" in (src, dst) or {".", ".."} & set(lasts):
        return EBUSY  # the mount itself, or a name ending in `.` or `..` (Linux's answer)
    if _above(mount, src) or _above(mount, dst):
        return EBUSY  # the guest's view of other preopens stays where it was put
    if dst.startswith(src + "/"):
        return EINVAL  # into its own subfolder
    if src == dst or needs_folder:
        # onto itself, or a source that must be a folder: one `stat` decides it
        errno, kind, _, _ = files._stat(caller, mount, src)
        if errno:
            return errno
        if needs_folder and kind != "dir":
            return ENOTDIR
        if src == dst:
            return 0
    errno, _ = files._change(caller, mount, "rename", "call", (src, dst))
    if errno == 0:
        files._follow(mount, src, dst)
    return errno


def _path_link(
    files: _Files,
    caller: Any,
    fd: int,
    flags: int,
    old: int,
    old_length: int,
    to: int,
    new: int,
    new_length: int,
) -> int:
    a, b = files._entry(fd), files._entry(to)
    if a is None and b is None:
        args = (fd, flags, old, old_length, to, new, new_length)
        return files.forward(caller, "path_link", args)
    flags = _lookup(flags)
    paths = ((old, old_length), (new, new_length))
    if a is None or b is None or a.mount is not b.mount or not a.mount.writable:
        return _across(files, caller, fd, to, paths, follow=bool(flags & 1))
    if a.kind != "dir" or b.kind != "dir":
        return EBADF
    if errno := _read_paths(files, caller, paths):
        return errno
    return EINVAL if flags & 1 else ENOTSUP  # the protocol has no link


HANDLERS: dict[str, Callable[..., int]] = {
    "path_create_directory": _path_create_directory,
    "path_filestat_get": _path_filestat_get,
    "path_filestat_set_times": _path_filestat_set_times,
    "path_link": _path_link,
    "path_open": _path_open,
    "path_readlink": _path_readlink,
    "path_remove_directory": _path_remove_directory,
    "path_rename": _path_rename,
    "path_symlink": _path_symlink,
    "path_unlink_file": _path_unlink_file,
}
