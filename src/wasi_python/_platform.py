"""What the operating system decides, behind one interface chosen once at import.

`PLATFORM` is the one platform object: a `_Linux`, a `_Darwin`, a `_Windows`, or a `_Posix` for
any other POSIX host, bound by `_select`, the only place in the package that asks the
interpreter which system this is. Every caller writes `from . import _platform` and reads
`_platform.PLATFORM` at the call, so a check that binds another platform for its duration is
seen by every caller.

What differs, and why each difference exists:

- Directory descriptors. POSIX walks a host folder, makes a root's missing tail and removes a
  tree through descriptors opened without following a link, so a guest's link planted between
  two steps leads nowhere; a POSIX host without `dir_fd` support, and Windows, which has none,
  take the same steps by path. Windows walks through handles instead, held without
  `FILE_SHARE_DELETE` so no walked folder can be renamed or replaced before the identity check.
- Locks. POSIX takes `flock`; Windows `msvcrt.locking`, which reports a held range with its own
  errnos. POSIX unlinks a lock file while still holding the lock, so a creator that locks the
  file after finds it gone and draws again; Windows cannot delete an open file, so it unlocks,
  closes and then unlinks.
- The kernel's identity, so a sweep touches only the folders of its own kernel: Linux's boot id,
  macOS's boot session uuid, Windows's machine guid; an unknown POSIX host has none, so it
  never sweeps.
- The guest thread's stack: read through `pthread_getattr_np` on Linux, the Mach calls on
  macOS, the thread information block on Windows; an unknown host cannot read it, and the
  runner then refuses to start a guest. CPython 3.14 and later on Linux without glibc guess a
  thread's stack, so Linux alone tells the interpreter the real one.
- wasmtime's trap handlers: on Linux they are signal handlers that a later `faulthandler`,
  `signal.signal` or crash reporter can replace, so Linux alone checks them before a guest runs;
  macOS uses Mach ports and Windows a vectored handler.
- The default cache folders, and whether a cache path is as the runner makes it: every default a
  process of this user could compute, with or without the override variable each platform
  reads; on POSIX the owner, the mode and the number of names are checked, while on Windows,
  which has no mode bits, only the kind of file and that it is no link.
- A file a running guest holds open cannot be replaced on Windows, so a copy of the zip or a
  data file that is already right is left in place there.

Fork is not a platform difference and stays a module function: a child of a process that made an
engine is refused everywhere."""

from __future__ import annotations

import ctypes
import errno
import os
import re
import shutil
import stat
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from ._process import process

Identity = tuple[int, int]


class _Walked:
    """A host folder walked component by component: the path wasmtime is given, the identities of
    the folder and each ancestor (the folder's first), and what keeps it from changing until the
    identity check: on POSIX the folder's descriptor, on Windows every component's handle. A root
    still to be made has `missing` components, and its chain is its deepest existing ancestor's.
    `close` releases the holds through the closer of the walk that made it (the platform's by
    default), and `fd` is the folder's descriptor on a walk by descriptors, else None."""

    def __init__(
        self,
        path: str,
        chain: tuple[Identity, ...],
        held: list[int],
        *,
        descriptors: bool = False,
        closer: Callable[[int], None] | None = None,
    ) -> None:
        self.path, self.chain, self.held = path, chain, held
        self.missing: tuple[str, ...] = ()
        self.descriptors, self.closer = descriptors, closer

    @property
    def identity(self) -> Identity | None:
        return None if self.missing else self.chain[0]

    @property
    def fd(self) -> int | None:
        return self.held[-1] if self.held and self.descriptors else None

    def close(self) -> None:
        held, self.held = self.held, []
        closer = PLATFORM.close_held if self.closer is None else self.closer
        for h in held:
            closer(h)


class _Spent(Exception):
    """The removal's budget of calls is spent."""


class _Removal:
    """One removal's count of calls, its budget, and the first error it met."""

    def __init__(self, budget: int | None) -> None:
        self.calls, self.budget = 0, budget
        self.error: BaseException | None = None

    def spend(self) -> None:
        if self.budget is not None and self.calls >= self.budget:
            raise _Spent(f"the removal's budget of {self.budget} calls is spent")
        self.calls += 1

    def fail(self, error: BaseException) -> None:
        if self.error is None:
            self.error = error


def _flags(*names: str) -> int:
    flags = 0
    for name in names:
        flags |= getattr(os, name, 0)
    return flags


def _same_file(fd: int, path: str) -> bool:
    """Whether the open file is still the file at `path`; False when the path is gone."""
    try:
        opened, named = os.fstat(fd), os.lstat(path)
    except OSError:
        return False
    return (opened.st_dev, opened.st_ino) == (named.st_dev, named.st_ino)


# Fork. A child of a process that made an engine inherits state from
# threads that no longer exist, and wasmtime does not support use across a fork (on macOS it
# aborts), so such a child is refused. A child of a parent that only imported this runs normally.


def _refuse_forked() -> None:
    if process().forked:
        raise RuntimeError(
            "wasi_python was used before this process was forked; use it in the child only, or "
            "start processes with 'spawn' or 'forkserver'"
        )


def _close(fd: int | None) -> None:
    if fd is not None:
        os.close(fd)


def _unlink_quietly(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


# The guest's stack. Every entry into wasm runs on a guest thread the runner makes for
# it, with _THREAD_STACK bytes of stack, _WASM_STACK of them for wasm. The C-stack
# window (128 KiB, recipes/reactor_main.c) is unchanged. _HOST_ROOM holds what runs below
# the guest's frames: the runner's own callbacks (measured at most 48 KiB), and the collector's
# finalizers, audit hooks and trace functions that can run inside them.
_WASM_STACK = 8 << 20
_HOST_ROOM = 2 << 20
_THREAD_STACK = _WASM_STACK + _HOST_ROOM

_BUSY = {errno.EACCES, errno.EDEADLK, getattr(errno, "EDEADLOCK", errno.EDEADLK)}

# Opened for search only where the system allows (Linux O_PATH, macOS O_SEARCH): wasmtime opens a
# grant below a folder this user may search but not list, so the walk must pass through it too.
_DIR = (_flags("O_PATH") or _flags("O_SEARCH") or os.O_RDONLY) | _flags(
    "O_DIRECTORY", "O_NOFOLLOW", "O_CLOEXEC"
)
_DIR_OPEN = _flags("O_RDONLY", "O_DIRECTORY", "O_NOFOLLOW", "O_CLOEXEC", "O_NONBLOCK")
_REMOVE_BATCH = 1024  # entries a listing reads before it acts
MAX_LINKS = 40

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

# Linux: the fatal signals wasmtime 49 handles to turn a fault in wasm into a trap
# (crates/wasmtime/src/runtime/vm/sys/unix/signals.rs, foreach_handler): SIGSEGV and SIGILL, and
# SIGFPE on x86_64. Its handlers are installed when the first engine is made.
_TRAP_SIGNALS = ("SIGSEGV", "SIGILL")
_TRAP_SIGNALS_X86_64 = ("SIGFPE",)
_TRAP_HANDLERS_REPLACED = (
    "wasmtime's handler for {signal} was replaced after the first run, by a handler installed or "
    "removed since (faulthandler, signal.signal, or a native crash reporter); a trap in the guest "
    "would end or hang this process, so the call was refused. If faulthandler.enable() was "
    "called after the first run, faulthandler.disable() undoes it; otherwise restart the "
    "process, and install faulthandler or any crash reporter before the first run"
)


class _Platform(Protocol):
    """The questions the runner asks of its host. `_Posix` answers them for any POSIX host,
    `_Linux` and `_Darwin` for the two it knows by name, `_Windows` for Windows."""

    name: str  # the one name a message may print
    has_dir_fd: bool  # folders are made, walked and removed through descriptors
    holds_open_files: bool  # a file a running guest holds open cannot be replaced

    def walk(self, where: str, path: str, *, judge: bool, may_make: bool = False) -> _Walked: ...
    def make_missing(self, where: str, walked: _Walked) -> _Walked: ...
    def close_held(self, h: int) -> None: ...
    def identity_of(self, path: Path) -> Identity: ...
    def real_dir(
        self, root: Path, fd: int | None, parts: tuple[str, ...]
    ) -> tuple[Path, int | None]: ...
    def long_path(self, path: str) -> str: ...
    def try_lock(self, fd: int) -> bool | None: ...
    def unlock_close(self, fd: int, *, unlink: str | None = None) -> None: ...
    def kernel_identity(self) -> str | None: ...
    def remove_tree(
        self,
        path: str | os.PathLike[str],
        *,
        dir_fd: int | None = None,
        budget: int | None = None,
        errors: list[BaseException] | None = None,
    ) -> bool: ...
    def stack_bounds(self) -> tuple[int, int] | None: ...
    def tell_interpreter(
        self,
        bottom: int,
        size: int,
        *,
        implementation: str | None = None,
        version: tuple[int, ...] | None = None,
        libc: str | None = None,
        resolve: Callable[..., Any] | None = None,
    ) -> bool: ...
    def trap_handlers_ready(self, machine: str | None = None) -> str | None: ...
    def default_cache_dir(self, home: Path) -> Path: ...
    def default_cache_dirs(self, home: Path) -> tuple[Path, ...]: ...
    def private(self, path: Path, *, is_dir: bool) -> bool: ...


def _refused(where: str, path: str, judge: bool, walk: Callable[[], _Walked]) -> _Walked:
    """The walk, with a folder that cannot be searched, or vanished mid-walk, refused as the
    caller's grant when judged; the runtime's own folders raise as they are."""
    try:
        return walk()
    except ValueError:
        raise
    except OSError as e:
        if not judge:
            raise
        raise ValueError(f"{where}: {path!r} cannot be walked: {e.strerror or e}") from None


def _removing(
    walk: Callable[[_Removal], bool], budget: int | None, errors: list[BaseException] | None
) -> bool:
    """One walk of the remover, budgeted and never raising an `Exception`: True when nothing is
    left at the name; the first error met is appended to `errors`."""
    removal = _Removal(budget)
    try:
        gone = walk(removal)
    except Exception as e:  # _Spent included
        removal.fail(e)
        gone = False
    if not gone and errors is not None and removal.error is not None:
        errors.append(removal.error)
    return gone


class _Posix:
    """Any POSIX host the runner does not know by name: descriptors where the system has them,
    `flock`, no kernel identity, no stack probe, no interpreter hint, no trap-handler check."""

    name = "posix"
    holds_open_files = False

    def __init__(self) -> None:
        self.has_dir_fd = (
            os.mkdir in os.supports_dir_fd and shutil.rmtree.avoids_symlink_attacks is not False
        )
        self.identity: dict[str, str | None] = {}  # the kernel's, read once
        self.stack_api: dict[str, Any] = {}  # the C library's stack calls, resolved once

    # The walk.

    def walk(self, where: str, path: str, *, judge: bool, may_make: bool = False) -> _Walked:
        """Walk `path` from the top. With `judge`, a link in a folder this user can write raises
        ValueError; without it (the runtime's own folders), every link is followed. With
        `may_make`, a missing tail is returned as `missing`."""
        return _refused(where, path, judge, lambda: self._walk(where, path, judge, may_make))

    def _walk(self, where: str, path: str, judge: bool, may_make: bool) -> _Walked:
        # Joined to the working directory without normalising: `..` is taken on the walked
        # folders, as the kernel takes it, after any link before it is followed.
        todo = list(reversed(os.path.join(os.getcwd(), path).split("/")))
        top = os.open("/", _DIR)
        st = os.fstat(top)
        stack: list[tuple[int, Identity, str]] = [(top, (st.st_dev, st.st_ino), "")]
        links = 0
        try:
            while todo:
                name = todo.pop()
                if name in ("", "."):
                    continue
                if name == "..":
                    if len(stack) > 1:
                        os.close(stack.pop()[0])
                    continue
                parent = stack[-1][0]
                try:
                    st = os.lstat(name, dir_fd=parent)
                except FileNotFoundError:
                    rest = [n for n in reversed(todo) if n not in ("", ".")]
                    if not may_make or ".." in rest:
                        raise ValueError(f"{where}: {path!r} does not exist") from None
                    walked = self._walked(stack)
                    walked.missing = (name, *rest)
                    return walked
                if stat.S_ISLNK(st.st_mode):
                    if judge and _writable(parent, stack):
                        raise ValueError(
                            f"{where}: {path!r} passes through the link {name!r} in a folder "
                            "this user can write, which a guest could have made; name its "
                            "target instead"
                        )
                    links += 1
                    if links > MAX_LINKS:
                        raise ValueError(
                            f"{where}: {path!r} passes through more than {MAX_LINKS} links"
                        )
                    target = os.readlink(name, dir_fd=parent)
                    if target.startswith("/"):
                        while len(stack) > 1:
                            os.close(stack.pop()[0])
                    todo.extend(reversed(target.split("/")))
                    continue
                if not stat.S_ISDIR(st.st_mode):
                    raise ValueError(f"{where}: {path!r} is not a folder")
                fd = os.open(name, _DIR, dir_fd=parent)
                opened = os.fstat(fd)
                if (opened.st_dev, opened.st_ino) != (st.st_dev, st.st_ino):
                    os.close(fd)
                    raise ValueError(f"{where}: {path!r} changed while it was checked")
                stack.append((fd, (opened.st_dev, opened.st_ino), name))
            return self._walked(stack)
        except BaseException:
            for fd, _, _ in stack:
                os.close(fd)
            raise

    def _walked(self, stack: list[tuple[int, Identity, str]]) -> _Walked:
        """Keep the last folder's descriptor, close the rest."""
        for fd, _, _ in stack[:-1]:
            os.close(fd)
        text = "/" + "/".join(name for _, _, name in stack[1:])
        chain = tuple(identity for _, identity, _ in reversed(stack))
        last = stack[-1][0]
        stack[:] = []
        return _Walked(text, chain, [last], descriptors=True, closer=self.close_held)

    def make_missing(self, where: str, walked: _Walked) -> _Walked:
        """Make a root's missing components, after the rules were decided on its existing chain,
        each inside the one before through its descriptor where the system has them, else by
        path; then walk the made root as any other."""
        path = walked.path
        if self.has_dir_fd and walked.fd is not None:
            fd = os.dup(walked.fd)
            try:
                for name in walked.missing:
                    try:
                        os.mkdir(name, dir_fd=fd)
                    except FileExistsError:  # a concurrent call made it
                        pass
                    child = os.open(name, _DIR, dir_fd=fd)  # O_NOFOLLOW: a link put there fails
                    os.close(fd)
                    fd = child
                    path = os.path.join(path, name)
            finally:
                os.close(fd)
        else:
            path = _make_by_path(path, walked.missing)
        walked.close()
        return self.walk(where, path, judge=True)

    def close_held(self, h: int) -> None:
        try:
            os.close(h)
        except OSError:
            pass

    def identity_of(self, path: Path) -> Identity:
        st = os.stat(path)
        if not stat.S_ISDIR(st.st_mode):
            raise NotADirectoryError(str(path))
        return (st.st_dev, st.st_ino)

    def real_dir(
        self, root: Path, fd: int | None, parts: tuple[str, ...]
    ) -> tuple[Path, int | None]:
        """root/parts…, each a real directory: a link or file a guest left in the way is removed,
        never followed. Through `fd`, the root's walked descriptor, where the system has them,
        with a descriptor on the result for the caller to close; else by path, with None."""
        if fd is not None and self.has_dir_fd:
            return root.joinpath(*parts), _real_dir_at(fd, parts)
        return _real_dir_by_path(root, parts), None

    def long_path(self, path: str) -> str:
        return os.path.abspath(path)

    # Locks.

    def try_lock(self, fd: int) -> bool | None:
        """Lock the open file without waiting: True when locked, False when another holder has
        it, None when this filesystem gives no lock (`ENOLCK` on NFS without a lock daemon,
        say)."""
        import fcntl

        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except BlockingIOError:
            return False
        except OSError:
            return None

    def unlock_close(self, fd: int, *, unlink: str | None = None) -> None:
        """Unlink the lock file at `unlink`, if given, while the lock is still held, so a creator
        that locks the file after fails its same-file check and draws again; then close, which
        releases the lock; quiet."""
        if unlink is not None:
            _unlink_quietly(unlink)
        try:
            os.close(fd)
        except OSError:
            pass

    def kernel_identity(self) -> str | None:
        """Which kernel this process runs on, or None: a lock taken on one kernel is invisible to
        another that shares the folder (a VM and its host), so a sweep touches only its own."""
        if "value" not in self.identity:
            try:
                value = self._kernel_identity()
            except Exception:
                value = None
            self.identity["value"] = value if value and "\n" not in value else None
        return self.identity["value"]

    def _kernel_identity(self) -> str | None:
        return None

    # The remover.

    def remove_tree(
        self,
        path: str | os.PathLike[str],
        *,
        dir_fd: int | None = None,
        budget: int | None = None,
        errors: list[BaseException] | None = None,
    ) -> bool:
        """Remove the tree at `path` (a name in `dir_fd` when given); True when nothing is left at
        that name. By descriptors where the system has them, at most two held; else by paths.
        Never raises an `Exception`; the first error it met is appended to `errors`."""
        name = os.fspath(path)
        if self.has_dir_fd:
            return _removing(lambda r: _remove_at(name, dir_fd, r), budget, errors)
        if dir_fd is not None:
            raise NotImplementedError("dir_fd unavailable on this platform")
        return _removing(lambda r: _remove_by_path(self.long_path(name), r), budget, errors)

    # The guest thread.

    def stack_bounds(self) -> tuple[int, int] | None:
        """(the usable bottom, the usable size) of this thread's stack, or None if unreadable."""
        try:
            return self._stack_bounds()
        except Exception:
            return None

    def _stack_bounds(self) -> tuple[int, int] | None:
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
        """Whether the interpreter was told this thread's real stack: only where it guesses."""
        return False

    def trap_handlers_ready(
        self,
        machine: str | None = None,
        handler_base: Callable[[int], int | None] | None = None,
        wasmtime_base: Callable[[], int | None] | None = None,
    ) -> str | None:
        """None when a trap in the guest would reach wasmtime; else the first signal whose
        handler is not wasmtime's. Only Linux catches traps with signal handlers."""
        return None

    # The cache.

    def default_cache_dir(self, home: Path) -> Path:
        base = os.environ.get("XDG_CACHE_HOME")
        return (Path(base) if base else home / ".cache") / "wasi_python"

    def _unset_default(self, home: Path) -> Path:
        """The default a process without the override variable computes."""
        return home / ".cache" / "wasi_python"

    def default_cache_dirs(self, home: Path) -> tuple[Path, ...]:
        """Every default a process of this user could compute: this one's, and the one without
        `$XDG_CACHE_HOME`, under `home` and under the home the password database gives this
        user, which a process with another `$HOME` (sudo, a container, CI) still reaches."""
        homes = [home]
        try:
            import pwd

            homes.append(Path(pwd.getpwuid(os.getuid()).pw_dir))
        except (ImportError, AttributeError, KeyError):
            pass  # no password database, or no entry for this uid: `home` alone
        found = [self.default_cache_dir(home), *(self._unset_default(h) for h in homes)]
        return tuple(dict.fromkeys(found))

    def private(self, path: Path, *, is_dir: bool) -> bool:
        """Whether a cache path is as the runner makes it: this user's, no link, and no bit for
        group or other (a directory 0700, a file 0600 with one name). A guest's `mkdir` and
        `open` give 0755 and 0644 under the usual umask, so its new folder or file fails here; a
        file the runner made and a guest rewrote in place does not. A directory is made if
        absent."""
        if is_dir:
            path.mkdir(mode=0o700, parents=True, exist_ok=True)
        st = os.lstat(path)
        kind_ok = stat.S_ISDIR(st.st_mode) if is_dir else _one_file(st)
        if kind_ok and st.st_uid == os.getuid() and not st.st_mode & 0o077:
            return True
        how = "owned by this user that no one else may read, write or enter"
        _not_used(
            path,
            f"a directory {how} (mode 0700)" if is_dir else f"a file {how} (mode 0600), one name",
        )
        return False


def _one_file(st: os.stat_result) -> bool:
    """A regular file with one name, as `mkstemp` and a rename leave the runner's own: a second
    name is a hard link a guest could make to a file elsewhere without writing a byte."""
    return stat.S_ISREG(st.st_mode) and st.st_nlink == 1


def _not_used(path: Path, must_be: str) -> None:
    import warnings

    warnings.warn(
        f"wasi_python: not using the module cache at {path}: it must be {must_be}",
        RuntimeWarning,
        stacklevel=6,
    )


def _writable(fd: int, stack: list[tuple[int, Identity, str]]) -> bool:
    """Whether this user can write the folder open at `fd`: only a link in such a folder could be
    a guest's, since a guest writes as this user."""
    effective = os.access in os.supports_effective_ids
    if os.access in os.supports_dir_fd:
        return os.access(".", os.W_OK, dir_fd=fd, effective_ids=effective)
    text = "/" + "/".join(name for _, _, name in stack[1:])
    return os.access(text, os.W_OK, effective_ids=effective)


def _make_by_path(path: str, missing: tuple[str, ...]) -> str:
    for name in missing:
        path = os.path.join(path, name)
        Path(path).mkdir(exist_ok=True)
    return path


def _real_dir_at(fd: int, parts: tuple[str, ...]) -> int:
    """A descriptor on fd/parts…, each a real directory, each step taken from the folder before:
    a link or file a guest left in the way is removed, never followed. The caller
    closes the result; `fd` stays open."""
    here = os.dup(fd)
    try:
        for part in parts:
            try:
                st = os.stat(part, dir_fd=here, follow_symlinks=False)
            except FileNotFoundError:
                st = None
            if st is not None and not stat.S_ISDIR(st.st_mode):
                os.unlink(part, dir_fd=here)  # a symbolic link or a file: removed, never followed
                st = None
            if st is None:
                try:
                    os.mkdir(part, dir_fd=here)
                except FileExistsError:  # a concurrent call made it
                    pass
            child = os.open(part, _DIR, dir_fd=here)  # O_NOFOLLOW: a link put there fails
            os.close(here)
            here = child
    except BaseException:
        os.close(here)
        raise
    return here


def _real_dir_by_path(root: Path, parts: tuple[str, ...]) -> Path:
    """root/parts…, each a real directory: a link or file a guest left in the way is removed.
    Windows, where the walk holds every folder of the root's path and
    guests can make links only where the user holds the symbolic-link privilege, and
    a POSIX host without directory descriptors. The root is never made again here."""
    here = root
    for part in parts:
        here = here / part
        try:
            st = os.lstat(here)
        except FileNotFoundError:
            st = None
        if st is not None and not stat.S_ISDIR(st.st_mode):
            here.unlink()  # a symbolic link or a file: removed, never followed
            st = None
        if st is None:
            try:
                here.mkdir()
            except FileExistsError:  # a concurrent call made it
                if not stat.S_ISDIR(os.lstat(here).st_mode):
                    raise
    return here


# The removal. A guest can build a tree one level at a time through dir_fd, deeper
# than the process's free descriptors, and shutil.rmtree holds one descriptor per level (and on
# 3.11 one Python frame per level). The remover holds at most two: on POSIX it goes down by
# name with O_NOFOLLOW and up by "..", checking each parent against the identity it recorded on
# the way down; elsewhere (Windows) it walks extended-length paths. It creates, renames and
# chmods nothing: what it may not delete, it leaves. Only a fresh HOME,
# which another call on the same root may be writing, gets a budget of calls.


def _is_folder(entry: os.DirEntry[str]) -> bool:
    """A folder to enter: never a link, and never a junction (as shutil's `_rmtree_islink`)."""
    try:
        if not entry.is_dir(follow_symlinks=False):
            return False
        if hasattr(entry, "is_junction"):
            return not entry.is_junction()
        tag = getattr(entry.stat(follow_symlinks=False), "st_reparse_tag", 0)
        return not (tag and tag == getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", None))
    except OSError:
        return False


def _listing(where: int | str, failed: set[str], removal: _Removal) -> list[os.DirEntry[str]]:
    """Up to `_REMOVE_BATCH` entries not yet failed, read and closed before anything is done."""
    removal.spend()
    found: list[os.DirEntry[str]] = []
    with os.scandir(where) as entries:
        for entry in entries:
            if entry.name not in failed:
                found.append(entry)
                if len(found) == _REMOVE_BATCH:
                    break
    return found


def _remove_at(name: str, parent: int | None, removal: _Removal) -> bool:
    """POSIX: the walk by descriptors, at most two held at once."""
    try:
        st = os.lstat(name, dir_fd=parent)
    except FileNotFoundError:
        return True
    if not stat.S_ISDIR(st.st_mode):  # a link or a file in the folder's place: never followed
        removal.spend()
        try:
            os.unlink(name, dir_fd=parent)
        except FileNotFoundError:
            pass
        return True
    removal.spend()
    cur = os.open(name, _DIR_OPEN, dir_fd=parent)
    try:
        here = os.fstat(cur)
        if (here.st_dev, here.st_ino) != (st.st_dev, st.st_ino):
            raise OSError(errno.EBUSY, "the folder changed before its removal", name)
        dev, ident = here.st_dev, (here.st_dev, here.st_ino)
        stack: list[tuple[str, tuple[int, int], set[str]]] = []  # name, parent, parent's failed
        failed: set[str] = set()
        while True:
            entries = _listing(cur, failed, removal)
            down, removed = None, False
            for entry in entries:
                if _is_folder(entry):
                    down = entry
                    break
                removal.spend()
                try:
                    os.unlink(entry.name, dir_fd=cur)
                    removed = True
                except FileNotFoundError:
                    removed = True
                except OSError as e:
                    removal.fail(e)
                    failed.add(entry.name)
            if down is not None:
                child = _enter(down, cur, dev, failed, removal)
                if child is None:
                    continue
                inside = os.fstat(child)
                stack.append((down.name, ident, failed))
                os.close(cur)
                cur, ident, failed = child, (inside.st_dev, inside.st_ino), set()
                continue
            if removed or len(entries) == _REMOVE_BATCH:
                continue
            if not stack:
                break
            child_name, parent_ident, parent_failed = stack.pop()
            removal.spend()
            up = os.open("..", _DIR_OPEN, dir_fd=cur)
            above = os.fstat(up)
            if (above.st_dev, above.st_ino) != parent_ident:  # moved: never walk out of the tree
                os.close(up)
                raise OSError(errno.EBUSY, "a folder moved during its removal", child_name)
            os.close(cur)
            cur, ident, failed = up, parent_ident, parent_failed
            removal.spend()
            try:
                os.rmdir(child_name, dir_fd=cur)
            except FileNotFoundError:
                pass
            except OSError as e:
                removal.fail(e)
                failed.add(child_name)
    finally:
        os.close(cur)
    removal.spend()
    try:
        os.rmdir(name, dir_fd=parent)
    except FileNotFoundError:
        pass
    return True


def _enter(
    entry: os.DirEntry[str], cur: int, dev: int, failed: set[str], removal: _Removal
) -> int | None:
    """The folder below, opened without following a link; None when it is gone, removed (an
    empty folder it may not open), or recorded as failed."""
    try:
        if entry.stat(follow_symlinks=False).st_dev != dev:  # another device: never entered
            raise OSError(errno.EXDEV, "another device", entry.name)
        removal.spend()
        child = os.open(entry.name, _DIR_OPEN, dir_fd=cur)
    except FileNotFoundError:
        return None
    except PermissionError as e:  # mode 0000, say: an empty one goes by rmdir
        removal.spend()
        try:
            os.rmdir(entry.name, dir_fd=cur)
        except FileNotFoundError:
            pass
        except OSError:
            removal.fail(e)
            failed.add(entry.name)
        return None
    except OSError as e:  # a link swapped in (ELOOP, ENOTDIR): left, never followed
        removal.fail(e)
        failed.add(entry.name)
        return None
    if os.fstat(child).st_dev != dev:
        os.close(child)
        removal.fail(OSError(errno.EXDEV, "another device", entry.name))
        failed.add(entry.name)
        return None
    return child


def _remove_by_path(top: str, removal: _Removal) -> bool:
    """Windows (and a POSIX host without directory descriptors, or a check that forces it): the
    same walk on paths, down by joining a name and up by dropping it. Links and junctions are
    removed, never entered."""
    try:
        st = os.lstat(top)
    except FileNotFoundError:
        return True
    attributes = getattr(st, "st_file_attributes", 0)
    reparse = attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    if not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode) or reparse:
        removal.spend()
        try:
            os.unlink(top)
        except FileNotFoundError:
            pass
        return True
    dev, here = st.st_dev, top
    stack: list[tuple[str, set[str]]] = []  # name, parent's failed
    failed: set[str] = set()
    while True:
        try:
            entries = _listing(here, failed, removal)
        except _Spent:
            raise
        except OSError as e:  # a folder it may not list: climb, and its rmdir decides
            removal.fail(e)
            entries = []
        down, removed = None, False
        for entry in entries:
            if _is_folder(entry):
                down = entry
                break
            removal.spend()
            try:
                os.unlink(os.path.join(here, entry.name))
                removed = True
            except FileNotFoundError:
                removed = True
            except OSError as e:
                removal.fail(e)
                failed.add(entry.name)
        if down is not None:
            below = os.path.join(here, down.name)
            try:
                if os.lstat(below).st_dev != dev:
                    raise OSError(errno.EXDEV, "another device", below)
            except FileNotFoundError:
                continue
            except OSError as e:
                removal.fail(e)
                failed.add(down.name)
                continue
            stack.append((down.name, failed))
            here, failed = below, set()
            continue
        if removed or len(entries) == _REMOVE_BATCH:
            continue
        if not stack:
            break
        child_name, failed = stack.pop()
        child, here = here, here[: -(len(child_name) + 1)]
        removal.spend()
        try:
            os.rmdir(child)
        except FileNotFoundError:
            pass
        except OSError as e:
            removal.fail(e)
            failed.add(child_name)
    removal.spend()
    try:
        os.rmdir(top)
    except FileNotFoundError:
        pass
    return True


def _pyapi(name: str, restype: Any, *argtypes: Any) -> Any:
    """A private prototype of a C API function: no restype or argtypes is set on
    `ctypes.pythonapi`'s shared attributes. AttributeError if absent."""
    return ctypes.PYFUNCTYPE(restype, *argtypes)((name, ctypes.pythonapi))


class _DlInfo(ctypes.Structure):
    _fields_ = [
        ("dli_fname", ctypes.c_char_p),
        ("dli_fbase", ctypes.c_void_p),
        ("dli_sname", ctypes.c_char_p),
        ("dli_saddr", ctypes.c_void_p),
    ]


def _load_base(address: int | None) -> int | None:
    """The load base of the shared object that holds `address`, by dladdr; None if none does."""
    if not address or address in (1,):  # SIG_DFL (0) and SIG_IGN (1) are in no object
        return None
    info = _DlInfo()
    if not process().handlers["dladdr"](ctypes.c_void_p(address), ctypes.byref(info)):
        return None
    return info.dli_fbase or None


def _handler_base(signum: int) -> int | None:
    """The load base of the object holding `signum`'s installed handler (the first word of
    `struct sigaction` in glibc and musl alike), or None."""
    buf = (ctypes.c_char * 1024)()  # larger than any struct sigaction
    if process().handlers["sigaction"](signum, None, buf) != 0:
        return None
    return _load_base(ctypes.c_void_p.from_buffer(buf).value)


def _wasmtime_base() -> int | None:
    """The load base of wasmtime-py's own library, read once, from one of its symbols."""
    handlers = process().handlers
    if "wasmtime" not in handlers:
        from . import _wasmtime_ffi as ffi

        handlers["wasmtime"] = _load_base(ffi.engine_symbol_address())
    base: int | None = handlers["wasmtime"]
    return base


class _Linux(_Posix):
    """Linux: the kernel's boot id, the `pthread_getattr_np` stack probe, the interpreter told
    its stack where CPython guesses it, and wasmtime's signal handlers checked."""

    name = "linux"

    def _kernel_identity(self) -> str | None:
        return Path("/proc/sys/kernel/random/boot_id").read_text().strip()

    # The guest thread's own stack. Each C function is a private prototype, resolved
    # once; no argtypes are set on a shared ctypes attribute. What is measured is the thread's
    # whole stack as the C library reports it (glibc's static TLS and thread descriptor lie
    # inside it, and the frames above the entry count too), not the room left at the entry: the
    # 1 MiB between the refusal line and the thread's size, and the host room, absorb both.

    def _stack_bounds(self) -> tuple[int, int] | None:
        api = self.stack_api
        if "getattr" not in api:
            libc = ctypes.CDLL(None)
            vp, sz = ctypes.c_void_p, ctypes.c_size_t
            api["self"] = ctypes.CFUNCTYPE(ctypes.c_ulong)(("pthread_self", libc))
            api["getattr"] = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_ulong, vp)(
                ("pthread_getattr_np", libc)
            )
            api["getstack"] = ctypes.CFUNCTYPE(
                ctypes.c_int, vp, ctypes.POINTER(vp), ctypes.POINTER(sz)
            )(("pthread_attr_getstack", libc))
            api["guard"] = ctypes.CFUNCTYPE(ctypes.c_int, vp, ctypes.POINTER(sz))(
                ("pthread_attr_getguardsize", libc)
            )
            api["destroy"] = ctypes.CFUNCTYPE(ctypes.c_int, vp)(("pthread_attr_destroy", libc))
        attr = (ctypes.c_char * 1024)()  # larger than any pthread_attr_t
        if api["getattr"](api["self"](), attr) != 0:
            return None
        try:
            addr, size, guard = ctypes.c_void_p(), ctypes.c_size_t(), ctypes.c_size_t()
            if api["getstack"](attr, ctypes.byref(addr), ctypes.byref(size)) != 0:
                return None
            if api["guard"](attr, ctypes.byref(guard)) != 0:
                return None
        finally:
            api["destroy"](attr)
        if not addr.value or size.value <= guard.value:
            return None
        return addr.value + guard.value, size.value - guard.value

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
        """Where CPython 3.14 and later guess their thread's stack (Linux without glibc), tell
        the interpreter this thread's real one, or a callback from deep in the guest ends the
        process. True when told. CPython 3.14.0 there has no such call:
        RuntimeError."""
        import platform as platform_module

        name = implementation if implementation is not None else sys.implementation.name
        ver = version if version is not None else tuple(sys.version_info[:3])
        if name != "cpython" or ver[:2] < (3, 14):
            return False
        lib = libc if libc is not None else platform_module.libc_ver()[0]
        if lib == "glibc":
            return False
        find = resolve if resolve is not None else _pyapi
        try:
            get = find("PyThreadState_Get", ctypes.c_void_p)
            protect = find(
                "PyUnstable_ThreadState_SetStackProtection",
                ctypes.c_int,
                ctypes.c_void_p,
                ctypes.c_void_p,
                ctypes.c_size_t,
            )
        except AttributeError:
            raise RuntimeError(
                f"CPython {'.'.join(map(str, ver))} on this C library guesses its thread's stack "
                "and cannot be told the guest thread's; use CPython 3.14.1 or later"
            ) from None
        try:
            protect(get(), bottom, size)
        except Exception as e:
            raise RuntimeError(f"the interpreter refused the guest thread's stack: {e}") from None
        return True

    def trap_handlers_ready(
        self,
        machine: str | None = None,
        handler_base: Callable[[int], int | None] | None = None,
        wasmtime_base: Callable[[], int | None] | None = None,
    ) -> str | None:
        """None when a trap in the guest would reach wasmtime; else the first signal whose
        handler is not wasmtime's: wasmtime catches traps with signal
        handlers that a later faulthandler.enable() or disable(), a signal.signal or a native
        crash reporter can replace. Exact for faulthandler, conservative for other handlers.
        Any failure counts as not ready."""
        import signal as signals

        names: tuple[str, ...] = _TRAP_SIGNALS
        if (machine if machine is not None else os.uname().machine) == "x86_64":
            names += _TRAP_SIGNALS_X86_64
        name = names[0]
        try:
            if handler_base is None or wasmtime_base is None:
                handlers = process().handlers
                if "sigaction" not in handlers:
                    libc = ctypes.CDLL(None, use_errno=True)
                    libc.sigaction.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p]
                    libc.sigaction.restype = ctypes.c_int
                    libc.dladdr.argtypes = [ctypes.c_void_p, ctypes.POINTER(_DlInfo)]
                    libc.dladdr.restype = ctypes.c_int
                    handlers["dladdr"], handlers["sigaction"] = libc.dladdr, libc.sigaction
                handler_base = handler_base or _handler_base
                wasmtime_base = wasmtime_base or _wasmtime_base
            ours = wasmtime_base()
            for name in names:
                if ours is None or handler_base(int(getattr(signals, name))) != ours:
                    return name
        except Exception:
            return name
        return None


class _Darwin(_Posix):
    """macOS: the boot session uuid, the Mach stack probe, and the Caches folder."""

    name = "darwin"

    def _kernel_identity(self) -> str | None:
        import ctypes.util

        libc = ctypes.CDLL(ctypes.util.find_library("c"))
        size_p, void_p = ctypes.POINTER(ctypes.c_size_t), ctypes.c_void_p
        libc.sysctlbyname.argtypes = [ctypes.c_char_p, void_p, size_p, void_p, ctypes.c_size_t]
        libc.sysctlbyname.restype = ctypes.c_int
        buf, size = ctypes.create_string_buffer(64), ctypes.c_size_t(64)
        name = b"kern.bootsessionuuid"
        if libc.sysctlbyname(name, buf, ctypes.byref(size), None, 0) == 0:
            return buf.value.decode("ascii")
        return None

    def _stack_bounds(self) -> tuple[int, int] | None:
        api = self.stack_api
        if "top" not in api:
            libc = ctypes.CDLL(None)
            vp = ctypes.c_void_p
            api["self"] = ctypes.CFUNCTYPE(vp)(("pthread_self", libc))
            api["top"] = ctypes.CFUNCTYPE(vp, vp)(("pthread_get_stackaddr_np", libc))
            api["size"] = ctypes.CFUNCTYPE(ctypes.c_size_t, vp)(("pthread_get_stacksize_np", libc))
        me = api["self"]()
        top, size = api["top"](me), api["size"](me)
        if not top or not size or size >= top:
            return None
        return top - size, size

    def default_cache_dir(self, home: Path) -> Path:
        return home / "Library" / "Caches" / "wasi_python"

    def _unset_default(self, home: Path) -> Path:
        return self.default_cache_dir(home)  # macOS reads no override


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
        return _refused(where, path, judge, lambda: self._walk(where, path, judge, may_make))

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
        path = _make_by_path(walked.path, walked.missing)
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
        return _real_dir_by_path(root, parts), None

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
            return False if e.errno in _BUSY else None

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
            _unlink_quietly(unlink)

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
        return _removing(lambda r: _remove_by_path(top, r), budget, errors)

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
        kind_ok = stat.S_ISDIR(st.st_mode) if is_dir else _one_file(st)
        if kind_ok and not link:
            return True
        _not_used(path, "a directory, no link or junction" if is_dir else "a file with one name")
        return False


def _select() -> _Platform:
    """The one platform of this process. Android is a POSIX host the runner does not know by
    name: no boot id, no stack probe, no trap-handler check, so no guest runs there."""
    if sys.platform == "win32":
        return _Windows()
    if sys.platform == "darwin":
        return _Darwin()
    if sys.platform.startswith("linux"):
        return _Linux()
    return _Posix()


PLATFORM: _Platform = _select()
