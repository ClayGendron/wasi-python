"""Windows: the platform interface answered through handles, `msvcrt` locks and the registry.

What Windows does differently, and why: Python cannot open a folder as a descriptor there, so
a walk opens every component as a handle, refuses a link or a junction, and holds each handle
without letting it be deleted until the identity check; a name Win32 rewrites is refused, since
the path opened and the folders walked could disagree; a lock is `msvcrt.locking`, which
reports a held range by its own errnos, and a lock file is unlinked only after it is closed,
since an open file cannot be deleted; the kernel's identity is the machine guid; the guest
thread's stack is read from the thread information block; the cache folders are the profile's
local application data; and a file a running guest holds open is never replaced. The full list
of what differs between the platforms stays in the platform module's docstring.

This module is imported on every system, since the platform module imports the Windows class
for its one chooser and the judge builds a Windows platform on any host to model it. So its
top level defines classes, constants and functions only, and a Windows-only import goes inside
the method that uses it.
"""

from __future__ import annotations

import ctypes
import os
import re
import stat
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import _platform_common
from ._platform_common import Identity, _Opened, _Walked
from ._process import process

# Windows: Python cannot open a folder with os.open, so the walk opens every
# component through CreateFileW, refuses a reparse point (a link or a junction), and holds each
# handle without FILE_SHARE_DELETE until the identity check, so no walked folder can be renamed,
# removed or replaced in between, and no path string is ever compared.
# Traverse access, not attributes alone: Windows runs share checks only for data, execute or
# delete access (MS-FSA 2.1.5.1.2.2), so an attribute-only handle held without FILE_SHARE_DELETE
# stops no rename. FILE_TRAVERSE is FILE_EXECUTE, which is checked, and needs only the permission
# to pass through a folder, as POSIX's search does, not to list it.
_WALK_ACCESS = 0x20 | 0x80  # FILE_TRAVERSE | FILE_READ_ATTRIBUTES
_STAT_ACCESS = 0x80  # FILE_READ_ATTRIBUTES: an identity read that holds nothing
_SHARE_READ_WRITE = 0x1 | 0x2
_OPEN_EXISTING = 3
_BACKUP_SEMANTICS = 0x02000000
_OPEN_REPARSE_POINT = 0x00200000
_ATTRIBUTE_DIRECTORY = 0x10
_ATTRIBUTE_REPARSE_POINT = 0x400

# Names a judged Windows walk refuses: Win32 rewrites them, so the path
# opened and the chain of folders walked could disagree, and a rule that reads the chain could
# miss a true ancestor. A `:` is a drive letter (`C:\\b\\D:x` is
# drive D's current folder) or a stream; a trailing space or period is trimmed in some positions
# and not others; a reserved device name, with or without an extension, is the device, and a
# root still to be made through one would fail after the folders before it were made. The set is
# exactly Python's own `ntpath.isreserved` for one component, which the runner cannot
# call on 3.11 and 3.12: Microsoft's reserved names ("Naming Files, Paths, and Namespaces"), with
# the superscript `COM¹` to `LPT³` it reserves "in every directory"; `CONIN$` and `CONOUT$`,
# which CPython refuses "on the side of caution"; and the characters Windows rejects in a name.
_WIN_DEVICES = frozenset(
    {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
    | {f"{p}{c}" for p in ("COM", "LPT") for c in "123456789\u00b9\u00b2\u00b3"}
)
_WIN_RESERVED_CHARS = frozenset('"*<>?|' + "".join(map(chr, range(32))))


class _ByHandle(ctypes.Structure):
    _fields_ = [
        ("attributes", ctypes.c_uint32),
        ("times", ctypes.c_uint32 * 6),
        ("volume_serial", ctypes.c_uint32),
        ("size_high", ctypes.c_uint32),
        ("size_low", ctypes.c_uint32),
        ("links", ctypes.c_uint32),
        ("index_high", ctypes.c_uint32),
        ("index_low", ctypes.c_uint32),
    ]


def _rewritten(name: str) -> bool:
    """Whether Windows rewrites or rejects this one path component (never `.` or `..`): the same
    answer as `ntpath.isreserved` gives for it."""
    if name in (".", ".."):
        return False
    if ":" in name or _WIN_RESERVED_CHARS.intersection(name) or name.endswith((" ", ".")):
        return True
    return name.split(".", 1)[0].rstrip(" ").upper() in _WIN_DEVICES


def _default_drive_folder(drive: str) -> str:
    """The current folder of `drive` (the process's own drive when empty), holding no `..`: where
    a relative Windows path starts, and whose drive a rooted one takes. The
    observers' `drive_folder` stands in for it when set."""
    import ntpath

    return ntpath.abspath(drive or ".")


def _windows_usable(
    low: int, high: int, guarantee: int, page: int = 4096
) -> tuple[int, int] | None:
    size = high - low - guarantee - page
    return (low + guarantee + page, size) if size > 0 else None


class _Windows:
    """Windows: handles in place of descriptors, `msvcrt` locks, the machine guid, the thread
    information block's stack limits, the profile's cache folder, and no file replaced while a
    guest holds it open."""

    name = "windows"
    has_dir_fd = False
    holds_open_files = True

    def __init__(self) -> None:
        self.identity: dict[str, str | None] = {}  # the kernel's, read once
        self.stack_api: dict[str, Any] = {}  # kernel32's stack calls, resolved once
        self.win_api: dict[str, Any] = {}  # kernel32's file calls, resolved once

    def kernel32(self) -> Any:
        api = self.win_api
        if "kernel32" not in api:
            from ctypes import wintypes

            k = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
            k.CreateFileW.argtypes = [
                wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
            ]  # fmt: skip
            k.CreateFileW.restype = wintypes.HANDLE
            k.GetFileInformationByHandle.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
            k.GetFileInformationByHandle.restype = wintypes.BOOL
            k.CloseHandle.argtypes = [wintypes.HANDLE]
            k.CloseHandle.restype = wintypes.BOOL
            api["kernel32"] = k
        return api["kernel32"]

    def open_handle(
        self, path: str, follow: bool, access: int = _WALK_ACCESS
    ) -> tuple[int, int, Identity]:
        """A held handle on `path`, its attributes and its identity, as wasmtime reads it."""
        k = self.kernel32()
        flags = _BACKUP_SEMANTICS | (0 if follow else _OPEN_REPARSE_POINT)
        h = k.CreateFileW(path, access, _SHARE_READ_WRITE, None, _OPEN_EXISTING, flags, None)
        if h is None or h == ctypes.c_void_p(-1).value:
            code = ctypes.get_last_error()  # type: ignore[attr-defined]
            raise ctypes.WinError(code)  # type: ignore[attr-defined]
        info = _ByHandle()
        if not k.GetFileInformationByHandle(h, ctypes.byref(info)):
            code = ctypes.get_last_error()  # type: ignore[attr-defined]
            k.CloseHandle(h)
            raise ctypes.WinError(code)  # type: ignore[attr-defined]
        index = (info.index_high << 32) | info.index_low
        return h, info.attributes, (info.volume_serial, index)

    # The walk.

    def walk(self, where: str, path: str, *, judge: bool, may_make: bool = False) -> _Walked:
        """Walk `path` from the top through handles. With `judge`, any link or junction raises
        ValueError; without it (the runtime's own folders), every link is followed. With
        `may_make`, a missing tail is returned as `missing`."""
        return _platform_common._refused(
            where, path, judge, lambda: self._walk(where, path, judge, may_make)
        )

    def _walk(self, where: str, path: str, judge: bool, may_make: bool) -> _Walked:
        import ntpath

        if judge:
            # Made absolute without dropping `..`: only the start is ever normalised,
            # and `..` is taken on the folders walked, as the POSIX walk takes it.
            drive, tail = ntpath.splitdrive(path)
            drive_folder = process().observers.drive_folder or _default_drive_folder
            if tail[:1] in ("\\", "/") or drive[1:2] not in ("", ":"):  # rooted, or a share
                if not drive:  # rooted with no drive: the current folder's drive, fully qualified
                    drive = ntpath.splitdrive(drive_folder(""))[0]
                names = re.split(r"[\\/]", tail)
            else:
                drive, start = ntpath.splitdrive(drive_folder(drive))
                names = re.split(r"[\\/]", start) + re.split(r"[\\/]", tail)
        else:
            drive, rest = ntpath.splitdrive(ntpath.realpath(path))
            names = re.split(r"[\\/]", rest)
        names = [n for n in names if n not in ("", ".")]
        if judge:
            for name in names:
                if _rewritten(name):
                    raise ValueError(
                        f"{where}: {path!r} has a name Windows rewrites ({name!r}); name the "
                        "folder plainly"
                    )
        held: list[int] = []
        chain: list[Identity] = []
        heres: list[str] = []

        def enter(here: str) -> None:
            h, attributes, identity = self.open_handle(here, follow=not judge)
            held.append(h)
            if judge and attributes & _ATTRIBUTE_REPARSE_POINT:
                raise ValueError(
                    f"{where}: {path!r} passes through a link or junction; on Windows every one "
                    "is refused"
                )
            if not attributes & _ATTRIBUTE_DIRECTORY:
                raise ValueError(f"{where}: {path!r} is not a folder")
            chain.append(identity)
            heres.append(here)

        def walked(missing: tuple[str, ...]) -> _Walked:
            w = _Walked(heres[-1], tuple(reversed(chain)), held, closer=self.close_held)
            w.missing = missing
            return w

        try:
            try:
                enter(drive + "\\")  # a drive's root keeps its separator: `C:` alone is relative
            except FileNotFoundError:
                raise ValueError(f"{where}: {path!r} does not exist") from None
            for i, name in enumerate(names):
                if name == "..":
                    if len(heres) > 1:  # at the drive's root `..` stays, as POSIX's does at `/`
                        self.close_held(held.pop())
                        chain.pop()
                        heres.pop()
                    continue
                try:
                    enter(
                        heres[-1].rstrip("\\") + "\\" + name
                    )  # never ntpath.join: a drive resets it
                except FileNotFoundError:
                    left = tuple(names[i + 1 :])
                    if not may_make or ".." in left:
                        raise ValueError(f"{where}: {path!r} does not exist") from None
                    return walked((name, *left))
            return walked(())
        except BaseException:
            for h in held:
                self.close_held(h)
            raise

    def make_missing(self, where: str, walked: _Walked) -> _Walked:
        """Make a root's missing components by path, after the rules were decided on its
        existing chain; then walk the made root as any other."""
        path = _platform_common._make_by_path(walked.path, walked.missing)
        walked.close()
        return self.walk(where, path, judge=True)

    def close_held(self, h: int) -> None:
        try:
            self.kernel32().CloseHandle(h)
        except OSError:
            pass

    def identity_of(self, path: Path) -> Identity:
        # Attributes only: a runtime folder's chain must not be cut short by a folder one may not
        # traverse, or by another handle's share mode.
        h, _, identity = self.open_handle(str(path), follow=True, access=_STAT_ACCESS)
        self.close_held(h)
        return identity

    def real_dir(
        self, root: Path, fd: int | None, parts: tuple[str, ...]
    ) -> tuple[Path, int | None]:
        """root/parts…, each a real directory, by path: the walk holds every folder of the root's
        path, and guests make links only where the user holds the symbolic-link privilege."""
        return _platform_common._real_dir_by_path(root, parts), None

    def long_path(self, path: str) -> str:
        """An extended-length path, so no path is limited to 260 characters."""
        path = os.path.abspath(path)
        if path.startswith("\\\\?\\"):
            return path
        if path.startswith("\\\\"):
            return "\\\\?\\UNC\\" + path[2:]
        return "\\\\?\\" + path

    # Locks.

    def try_lock(self, fd: int) -> bool | None:
        """Lock the open file without waiting: True when locked, False when another holder has
        it (`msvcrt.locking` reports a held range by its own errnos), None when this filesystem
        gives no lock."""
        import msvcrt

        try:
            os.lseek(fd, 0, 0)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)  # type: ignore[attr-defined]
            return True
        except BlockingIOError:
            return False
        except OSError as e:
            return False if e.errno in _platform_common._BUSY else None

    def unlock_close(self, fd: int, *, unlink: str | None = None) -> None:
        """Unlock (a closed handle's lock is freed only after a delay), close, then unlink the
        lock file at `unlink`, if given: an open file cannot be deleted; quiet."""
        import msvcrt

        try:
            os.lseek(fd, 0, 0)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)  # type: ignore[attr-defined]
        except OSError:
            pass
        try:
            os.close(fd)
        except OSError:
            pass
        if unlink is not None:
            _platform_common._unlink_quietly(unlink)

    def kernel_identity(self) -> str | None:
        """The machine guid from the registry, read once; None when it cannot be read."""
        if "value" not in self.identity:
            value = None
            try:
                import winreg

                access = winreg.KEY_READ | winreg.KEY_WOW64_64KEY  # type: ignore[attr-defined]
                where = r"SOFTWARE\Microsoft\Cryptography"
                with winreg.OpenKey(  # type: ignore[attr-defined]
                    winreg.HKEY_LOCAL_MACHINE,  # type: ignore[attr-defined]
                    where,
                    0,
                    access,
                ) as key:
                    value = str(winreg.QueryValueEx(key, "MachineGuid")[0])  # type: ignore[attr-defined]
            except Exception:
                value = None
            self.identity["value"] = value if value and "\n" not in value else None
        return self.identity["value"]

    # The remover.

    def remove_tree(
        self,
        path: str | os.PathLike[str],
        *,
        dir_fd: int | None = None,
        budget: int | None = None,
        errors: list[BaseException] | None = None,
    ) -> bool:
        """Remove the tree at `path` by extended-length paths, links and junctions never entered;
        True when nothing is left there. Never raises an `Exception`; the first error it met is
        appended to `errors`."""
        if dir_fd is not None:
            raise NotImplementedError("dir_fd unavailable on this platform")
        top = self.long_path(os.fspath(path))
        return _platform_common._removing(
            lambda r: _platform_common._remove_by_path(top, r), budget, errors
        )

    # The guest thread.

    def stack_bounds(self) -> tuple[int, int] | None:
        """(the usable bottom, the usable size) of this thread's stack, or None if unreadable.
        Counted conservatively: high - low - the thread's stack guarantee - one page."""
        try:
            api = self.stack_api
            if "limits" not in api:
                kernel32 = ctypes.WinDLL("kernel32")  # type: ignore[attr-defined]
                up = ctypes.POINTER(ctypes.c_size_t)
                api["limits"] = ctypes.WINFUNCTYPE(None, up, up)(  # type: ignore[attr-defined]
                    ("GetCurrentThreadStackLimits", kernel32)
                )
                api["guarantee"] = ctypes.WINFUNCTYPE(  # type: ignore[attr-defined]
                    ctypes.c_int, ctypes.POINTER(ctypes.c_ulong)
                )(("SetThreadStackGuarantee", kernel32))
            low, high = ctypes.c_size_t(), ctypes.c_size_t()
            api["limits"](ctypes.byref(low), ctypes.byref(high))
            guarantee = ctypes.c_ulong(0)
            if not api["guarantee"](ctypes.byref(guarantee)):  # 0 asks; it changes nothing
                return None
            return _windows_usable(low.value, high.value, guarantee.value)
        except Exception:
            return None

    def tell_interpreter(
        self,
        bottom: int,
        size: int,
        *,
        implementation: str | None = None,
        version: tuple[int, ...] | None = None,
        libc: str | None = None,
        resolve: Callable[..., Any] | None = None,
    ) -> bool:
        return False  # CPython reads the thread's real stack from the thread information block

    def trap_handlers_ready(
        self,
        machine: str | None = None,
        handler_base: Callable[[int], int | None] | None = None,
        wasmtime_base: Callable[[], int | None] | None = None,
    ) -> str | None:
        return None  # wasmtime catches traps with a vectored exception handler

    # The cache.

    def default_cache_dir(self, home: Path) -> Path:
        base = os.environ.get("LOCALAPPDATA")
        return (Path(base) if base else home / "AppData" / "Local") / "wasi_python" / "cache"

    def default_cache_dirs(self, home: Path) -> tuple[Path, ...]:
        """This process's default and the one a process without `%LOCALAPPDATA%` computes.
        `home` is `%USERPROFILE%`, which Windows sets at logon from the profile."""
        unset = home / "AppData" / "Local" / "wasi_python" / "cache"
        return tuple(dict.fromkeys([self.default_cache_dir(home), unset]))

    def private(self, path: Path, *, is_dir: bool) -> bool:
        """Whether a cache path is of the kind the runner makes: a directory, or a file with one
        name, and no link or junction. Windows has no mode bits, and a guest's file inherits the
        folder's access list as the runner's own does, so who wrote a file cannot be told here.
        A directory is made if absent."""
        if is_dir:
            path.mkdir(mode=0o700, parents=True, exist_ok=True)
        st = os.lstat(path)
        link = getattr(st, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
        kind_ok = stat.S_ISDIR(st.st_mode) if is_dir else _platform_common._one_file(st)
        if kind_ok and not link:
            return True
        _platform_common._not_used(
            path, "a directory, no link or junction" if is_dir else "a file with one name"
        )
        return False

    def private_fd(self, fd: int, *, is_dir: bool, path: Path) -> bool:
        """`private` of the file open at `fd`: its kind and its one name. The open followed any
        link, so the caller compares what is open with what `private` checked by name."""
        st = os.fstat(fd)
        if stat.S_ISDIR(st.st_mode) if is_dir else _platform_common._one_file(st):
            return True
        _platform_common._not_used(path, "a directory" if is_dir else "a file with one name")
        return False

    def cache_folder(
        self, cache: Path, *, lstat: Callable[[str], os.stat_result] = os.lstat
    ) -> Path | None:
        """The cache folder, made if absent, or None when it is not of the kind the runner makes
        (with a warning). No folder on the way is judged: Windows has no mode bits, and the
        grant rule is the guard. `lstat` is the POSIX walk's, unused here."""
        return cache if self.private(cache, is_dir=True) else None

    def open_cached(self, cwasm: Path, *, reopen: Callable[..., int] = os.open) -> _Opened | None:
        """The `.cwasm` open, or None when it is not of the kind the runner makes (with a
        warning). There is no name for a descriptor that wasmtime could open, so it is given the
        path; the read descriptor held until the caller closes it shares reading and writing but
        not deletion, so the name cannot be renamed, replaced or removed from the check until
        wasmtime has the file, and wasmtime's own open, which reads and shares reading, is
        compatible with it. `reopen` is the POSIX one's, unused here."""
        if not self.private(cwasm, is_dir=False):
            return None
        flags = os.O_RDONLY | getattr(os, "O_NOINHERIT", 0) | getattr(os, "O_BINARY", 0)
        fd = os.open(cwasm, flags)
        try:
            ok = self.private_fd(fd, is_dir=False, path=cwasm)
        except BaseException:
            os.close(fd)
            raise
        if not ok:
            os.close(fd)
            return None
        return _Opened(fd, str(cwasm), by_path=True)
