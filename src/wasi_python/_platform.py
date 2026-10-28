"""What the operating system decides, behind one interface chosen once at import.

`PLATFORM` is the one platform object: a `_Linux`, a `_Darwin`, a `_Windows`, or a `_Posix` for
any other POSIX host, bound by `_select`, the only place in the package that asks the
interpreter which system this is. Every caller writes `from . import _platform` and reads
`_platform.PLATFORM` at the call, so a check that binds another platform for its duration is
seen by every caller. The Windows class lives in `_platform_windows.py`, and what both families
run in `_platform_common.py`, below both.

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
  reads; on POSIX the owner, the mode, the number of names and any access list are checked,
  through the descriptor wasmtime is then given, and every folder on the way must be this
  user's, root's or, on `/`'s own device, the owner of `/`'s, and closed to other writers;
  Windows, which has no mode bits and no name for a descriptor, checks the kind of file and
  that it is no link, and holds the file open from its check to its load.
- A file a running guest holds open cannot be replaced on Windows, so a copy of the zip or a
  data file that is already right is left in place there.
- The guest's output: on POSIX wasmtime writes each stream into a pipe it opens by a `/dev/fd`
  path and the runner reads; Windows has no path to an anonymous pipe and `poll` takes no
  Windows pipe, so there the output stays on wasmtime's custom-output callback.

Fork is not a platform difference and stays a module function: a child of a process that made an
engine is refused everywhere."""

from __future__ import annotations

import ctypes
import errno
import os
import shutil
import stat
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from . import _platform_common
from ._platform_common import _REMOVE_BATCH, _Opened, _Removal
from ._platform_common import Identity as Identity
from ._platform_common import _Walked as _Walked
from ._platform_windows import _Windows
from ._process import process


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


# The guest's stack. Every entry into wasm runs on a guest thread the runner makes for
# it, with _THREAD_STACK bytes of stack, _WASM_STACK of them for wasm. The C-stack
# window (128 KiB, recipes/reactor_main.c) is unchanged. _HOST_ROOM holds what runs below
# the guest's frames: the runner's own callbacks (measured at most 48 KiB), and the collector's
# finalizers, audit hooks and trace functions that can run inside them.
_WASM_STACK = 8 << 20
_HOST_ROOM = 2 << 20
_THREAD_STACK = _WASM_STACK + _HOST_ROOM

# Opened for search only where the system allows (Linux O_PATH, macOS O_SEARCH): wasmtime opens a
# grant below a folder this user may search but not list, so the walk must pass through it too.
_DIR = (_flags("O_PATH") or _flags("O_SEARCH") or os.O_RDONLY) | _flags(
    "O_DIRECTORY", "O_NOFOLLOW", "O_CLOEXEC"
)
_DIR_OPEN = _flags("O_RDONLY", "O_DIRECTORY", "O_NOFOLLOW", "O_CLOEXEC", "O_NONBLOCK")
MAX_LINKS = 40

# The module cache. Its folder and a `.cwasm` are opened without following a link, and the file
# without waiting, should a pipe stand at its name. wasmtime opens a compiled module by name, so
# it is given a name of the descriptor the runner checked: `/dev/fd/N`, or `/proc/self/fd/N`
# where Linux has no `/dev/fd`. macOS's `ACL_TYPE_EXTENDED` (sys/acl.h) is the one kind of
# access list it keeps.
_CACHE_DIR_OPEN = _flags("O_RDONLY", "O_DIRECTORY", "O_NOFOLLOW", "O_CLOEXEC")
_CACHE_FILE_OPEN = _flags("O_RDONLY", "O_NOFOLLOW", "O_CLOEXEC", "O_NONBLOCK")
_FD_NAMES = ("/dev/fd", "/proc/self/fd")
_ACL_TYPE_EXTENDED = 0x100
# Under a user namespace a file whose owner the namespace does not map shows the kernel's overflow
# uid, 65534 by default, the same number as the namespace's own `nobody`. On `/` it is trusted as
# any owner of `/` is; below `/` the number could be either owner, so it is not.
_OVERFLOW_UID = 65534
# Every cache folder is below `/`, so when `/` fails no other folder can help.
_ROOT_ADVICE = (
    "no folder can hold the cache while it is, so have its owner run chmod go-w /, or pass "
    "cache_dir=False to compile in memory without this warning"
)

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
    def absolute(self, path: str) -> str: ...
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
    def cache_folder(
        self, cache: Path, *, lstat: Callable[[str], os.stat_result] = os.lstat
    ) -> Path | None: ...
    def open_cached(
        self, cwasm: Path, *, reopen: Callable[..., int] = os.open
    ) -> _Opened | None: ...
    def output_channel(self) -> tuple[str, int, int] | None: ...


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
        # The C library's stack calls, resolved once and published whole: a reader sees None
        # or every key, never some, so no lock is needed while two threads fill it at once.
        self.stack_api: dict[str, Any] | None = None

    # The walk.

    def walk(self, where: str, path: str, *, judge: bool, may_make: bool = False) -> _Walked:
        """Walk `path` from the top. With `judge`, a link in a folder this user can write raises
        ValueError; without it (the runtime's own folders), every link is followed. With
        `may_make`, a missing tail is returned as `missing`."""
        return _platform_common._refused(
            where, path, judge, lambda: self._walk(where, path, judge, may_make)
        )

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
        """Make a root's missing components at 0700, after the rules were decided on its existing
        chain, each inside the one before through its descriptor where the system has them, else by
        path; a component another user made first is refused. Then walk the made root as any
        other, and refuse it if the walk by name reached another folder than the one made."""
        path, made = walked.path, None
        if self.has_dir_fd and walked.fd is not None:
            fd = os.dup(walked.fd)
            try:
                for name in walked.missing:
                    try:
                        os.mkdir(name, 0o700, dir_fd=fd)
                    except FileExistsError:  # a concurrent call made it, if it is this user's
                        pass
                    child = os.open(name, _DIR, dir_fd=fd)  # O_NOFOLLOW: a link put there fails
                    os.close(fd)
                    fd = child
                    path = os.path.join(path, name)
                    # The folder open is the one judged: its owner, not the name's.
                    st = os.fstat(fd)
                    _platform_common._refuse_another_users(where, path, st)
                    made = (st.st_dev, st.st_ino)
            finally:
                os.close(fd)
        else:
            path = _platform_common._make_by_path(where, path, walked.missing)
        walked.close()
        again = self.walk(where, path, judge=True)
        if made is not None and again.chain[0] != made:  # renamed away, another put at its name
            again.close()
            raise ValueError(f"{where}: {path!r} changed after it was made")
        return again

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
        return _platform_common._real_dir_by_path(root, parts), None

    def long_path(self, path: str) -> str:
        return os.path.abspath(path)

    def absolute(self, path: str) -> str:
        """`path` against the working folder, joined without normalising: the kernel takes a
        `..` after it follows the link before it, so collapsing `link/..` by its spelling would
        name another folder."""
        return os.path.join(os.getcwd(), path)

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
            _platform_common._unlink_quietly(unlink)
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
            return _platform_common._removing(lambda r: _remove_at(name, dir_fd, r), budget, errors)
        if dir_fd is not None:
            raise NotImplementedError("dir_fd unavailable on this platform")
        return _platform_common._removing(
            lambda r: _platform_common._remove_by_path(self.long_path(name), r), budget, errors
        )

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
        `$XDG_CACHE_HOME`, under `home` and under the homes the password database gives this
        user, which a process with another `$HOME` (sudo, a container, CI) still reaches: the
        effective uid's, which owns what this process makes, and the real uid's, under which a
        process with no `$HOME` finds its own."""
        homes = [home]
        try:
            import pwd

            for uid in (os.geteuid(), os.getuid()):
                try:
                    homes.append(Path(pwd.getpwuid(uid).pw_dir))
                except KeyError:
                    pass  # no entry for this uid
        except (ImportError, AttributeError):
            pass  # no password database: `home` alone
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
        return self._as_made(path, os.lstat(path), is_dir=is_dir, listed=False)

    def private_fd(self, fd: int, *, is_dir: bool, path: Path) -> bool:
        """`private` of the file open at `fd`, which no rename can change, and no access list:
        the mode bits do not show one, and a list on the folder that its new files inherit would
        give every `.cwasm` the runner writes there a list. `path` names it in the warning."""
        listed = self._access_list(fd, is_dir=is_dir)
        return self._as_made(path, os.fstat(fd), is_dir=is_dir, listed=listed)

    def _as_made(self, path: Path, st: os.stat_result, *, is_dir: bool, listed: bool) -> bool:
        kind_ok = stat.S_ISDIR(st.st_mode) if is_dir else _platform_common._one_file(st)
        mine = _platform_common._this_users(st)
        if kind_ok and mine and not st.st_mode & 0o077 and not listed:
            return True
        how = "owned by this user that no one else may read, write or enter"
        must = f"a directory {how} (mode 0700)" if is_dir else f"a file {how} (mode 0600), one name"
        _platform_common._not_used(path, f"{must}, with no access list")
        return False

    def _access_list(self, fd: int, *, is_dir: bool) -> bool:
        """Whether the file open at `fd` has an access list; a host the runner does not know by
        name has no way it reads."""
        return False

    def cache_folder(
        self, cache: Path, *, lstat: Callable[[str], os.stat_result] = os.lstat
    ) -> Path | None:
        """The cache folder to use, its missing folders made at 0700, or None when it is not as
        the runner makes it (with a warning). The way to it, its links resolved, must hold no
        folder another user could change: each is this user's, root's or, on `/`'s own device,
        the owner of `/`'s, and no one else may write it unless it is sticky, as `/tmp` is,
        where no one else may rename what is in it. Else whoever could would put another folder
        at the cache's name between the check and the load. OSError names the folder that
        fails. `lstat` is the walk's."""
        folder = Path(os.path.realpath(cache.parent)) / cache.name
        for missing in _way(folder.parent, lstat):
            try:
                os.mkdir(missing, 0o700)
            except FileExistsError:  # a concurrent call made it, or another user: judged below
                pass
        # Walked once more, so a folder another user made between the walk and the `mkdir` is
        # judged as one found there is, and one that went away in between is not passed over.
        gone = _way(folder.parent, lstat)
        if gone:
            raise FileNotFoundError(
                errno.ENOENT, f"{gone[0]}, on the way to it, went away while it was made"
            )
        if not self.private(folder, is_dir=True):
            return None
        fd = os.open(folder, _CACHE_DIR_OPEN)
        try:
            return folder if self.private_fd(fd, is_dir=True, path=folder) else None
        finally:
            os.close(fd)

    def open_cached(self, cwasm: Path, *, reopen: Callable[..., int] = os.open) -> _Opened | None:
        """The `.cwasm` open, checked through its descriptor, with the name wasmtime is to open it
        by; None when it is not as the runner makes it (with a warning). The file is opened inside
        its folder's descriptor, each without following a link and each checked as opened, so
        what was checked is what is open whatever the names say after. wasmtime is given the
        descriptor's own name, which on macOS duplicates it and on Linux reopens the same file;
        where no such name opens (no `/proc` in a sandbox), the path, by `by_path`. `reopen` is
        the open that tries the name."""
        if not self.private(cwasm, is_dir=False):
            return None
        folder = os.open(cwasm.parent, _CACHE_DIR_OPEN)
        try:
            if not self.private_fd(folder, is_dir=True, path=cwasm.parent):
                raise OSError(errno.EPERM, "the cache folder changed", str(cwasm.parent))
            at = os.open in os.supports_dir_fd  # else by path, below a folder just checked
            fd = os.open(
                cwasm.name if at else cwasm, _CACHE_FILE_OPEN, dir_fd=folder if at else None
            )
        finally:
            os.close(folder)
        try:
            ok = self.private_fd(fd, is_dir=False, path=cwasm)
            name = _fd_name(fd, reopen) if ok else None
        except BaseException:
            os.close(fd)
            raise
        if not ok:
            os.close(fd)
            return None
        return _Opened(fd, name or str(cwasm), by_path=name is None)

    # The guest's output.

    def output_channel(self) -> tuple[str, int, int] | None:
        """A pipe wasmtime can open by a path and write as a file: (the path, the end the runner
        reads, the end the runner closes once wasmtime has opened the path). `/dev/fd` is the
        descriptor file system on macOS and a link to `/proc/self/fd` on Linux, through which a
        pipe opens anew."""
        r, w = os.pipe()
        return f"/dev/fd/{w}", r, w


def _way(folder: Path, lstat: Callable[[str], os.stat_result]) -> list[Path]:
    """The folders from `/` down to `folder` that do not exist yet, for the caller to make; each
    one that exists is a folder that no one else may write, or that is sticky, and is this
    user's, root's, or, on `/`'s own device, the owner of `/`'s. Whoever owns `/` can already
    rename every folder on its file system, so trusting it there adds no one; past a mount
    point it cannot rename the way, and the overflow uid could stand for another owner below
    `/`. PermissionError names the first folder that fails."""
    missing = []
    top: os.stat_result | None = None
    for here in [*reversed(folder.parents), folder]:
        try:
            st = lstat(str(here))
        except FileNotFoundError:
            missing.append(here)
            continue
        root = here == here.parent
        if root:
            top = st
        why = None
        if not stat.S_ISDIR(st.st_mode):
            why = "is not a folder"
        elif not root and not _owner_trusted(st, top):
            why = f"is another user's (uid {_platform_common._owner(st)})"
        elif st.st_mode & 0o022 and not st.st_mode & stat.S_ISVTX:
            why = f"may be written by others (mode {stat.S_IMODE(st.st_mode):o}) and is not sticky"
        if why is not None:
            advice = _ROOT_ADVICE if root else "set $WASI_PYTHON_CACHE to a folder of yours"
            raise PermissionError(errno.EACCES, f"{here}, on the way to it, {why}; {advice}")
    return missing


def _owner_trusted(st: os.stat_result, top: os.stat_result | None) -> bool:
    """Whether a folder below `/` belongs to this user, to root, or to the owner of `/` on `/`'s
    own device. The device is read only once the owner matched `/`'s."""
    if _platform_common._this_users(st):
        return True
    owner = _platform_common._owner(st)
    if owner == 0:
        return True
    if top is None:
        return False
    root_owner = _platform_common._owner(top)
    return owner == root_owner != _OVERFLOW_UID and st.st_dev == top.st_dev


def _fd_name(fd: int, reopen: Callable[..., int]) -> str | None:
    """A name that opens the file open at `fd`, found by opening it, or None where none does."""
    for base in _FD_NAMES:
        name = f"{base}/{fd}"
        try:
            os.close(reopen(name, os.O_RDONLY | _flags("O_CLOEXEC")))
        except OSError:
            continue
        return name
    return None


def _writable(fd: int, stack: list[tuple[int, Identity, str]]) -> bool:
    """Whether this user can write the folder open at `fd`: only a link in such a folder could be
    a guest's, since a guest writes as this user."""
    effective = os.access in os.supports_effective_ids
    if os.access in os.supports_dir_fd:
        return os.access(".", os.W_OK, dir_fd=fd, effective_ids=effective)
    text = "/" + "/".join(name for _, _, name in stack[1:])
    return os.access(text, os.W_OK, effective_ids=effective)


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
            entries = _platform_common._listing(cur, failed, removal)
            down, removed = None, False
            for entry in entries:
                if _platform_common._is_folder(entry):
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
    its stack where CPython guesses it, wasmtime's signal handlers checked, and its access
    lists."""

    name = "linux"

    def _kernel_identity(self) -> str | None:
        return Path("/proc/sys/kernel/random/boot_id").read_text().strip()

    def _access_list(self, fd: int, *, is_dir: bool) -> bool:
        """Whether the file open at `fd` has a POSIX access list, or, on a folder, a default one
        that what is made inside inherits; a file system without extended attributes has
        none."""
        try:
            names = os.listxattr(fd)
        except OSError as e:
            if e.errno in (errno.ENOTSUP, errno.EOPNOTSUPP):
                return False
            raise
        return "system.posix_acl_access" in names or (
            is_dir and "system.posix_acl_default" in names
        )

    # The guest thread's own stack. Each C function is a private prototype, resolved
    # once; no argtypes are set on a shared ctypes attribute. What is measured is the thread's
    # whole stack as the C library reports it (glibc's static TLS and thread descriptor lie
    # inside it, and the frames above the entry count too), not the room left at the entry: the
    # 1 MiB between the refusal line and the thread's size, and the host room, absorb both.

    def _stack_bounds(self) -> tuple[int, int] | None:
        api = self.stack_api
        if api is None:
            libc = ctypes.CDLL(None)
            vp, sz = ctypes.c_void_p, ctypes.c_size_t
            api = {
                "self": ctypes.CFUNCTYPE(ctypes.c_ulong)(("pthread_self", libc)),
                "getattr": ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_ulong, vp)(
                    ("pthread_getattr_np", libc)
                ),
                "getstack": ctypes.CFUNCTYPE(
                    ctypes.c_int, vp, ctypes.POINTER(vp), ctypes.POINTER(sz)
                )(("pthread_attr_getstack", libc)),
                "guard": ctypes.CFUNCTYPE(ctypes.c_int, vp, ctypes.POINTER(sz))(
                    ("pthread_attr_getguardsize", libc)
                ),
                "destroy": ctypes.CFUNCTYPE(ctypes.c_int, vp)(("pthread_attr_destroy", libc)),
            }
            self.stack_api = api
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
    """macOS: the boot session uuid, the Mach stack probe, the Caches folder, and its access
    lists."""

    name = "darwin"

    def __init__(self) -> None:
        super().__init__()
        # The C library's access-list calls, resolved once and published whole, as `stack_api`.
        self.acl_api: dict[str, Any] | None = None

    def _access_list(self, fd: int, *, is_dir: bool) -> bool:
        """Whether the file open at `fd` has an extended access list, any entry, allow or deny,
        read by `acl_get_fd_np`: macOS's `listxattr` lists none. No list is NULL with ENOENT;
        NULL with another errno is an OSError, so the cache is not used."""
        import ctypes.util

        api = self.acl_api
        if api is None:
            libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
            vp, i = ctypes.c_void_p, ctypes.c_int
            api = {
                "get": ctypes.CFUNCTYPE(vp, i, i, use_errno=True)(("acl_get_fd_np", libc)),
                "free": ctypes.CFUNCTYPE(i, vp)(("acl_free", libc)),
            }
            self.acl_api = api
        ctypes.set_errno(0)
        found = api["get"](fd, _ACL_TYPE_EXTENDED)
        if found:
            api["free"](found)
            return True
        err = ctypes.get_errno()
        if err == errno.ENOENT:
            return False
        raise OSError(err, os.strerror(err))

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
        if api is None:
            libc = ctypes.CDLL(None)
            vp = ctypes.c_void_p
            api = {
                "self": ctypes.CFUNCTYPE(vp)(("pthread_self", libc)),
                "top": ctypes.CFUNCTYPE(vp, vp)(("pthread_get_stackaddr_np", libc)),
                "size": ctypes.CFUNCTYPE(ctypes.c_size_t, vp)(("pthread_get_stacksize_np", libc)),
            }
            self.stack_api = api
        me = api["self"]()
        top, size = api["top"](me), api["size"](me)
        if not top or not size or size >= top:
            return None
        return top - size, size

    def default_cache_dir(self, home: Path) -> Path:
        return home / "Library" / "Caches" / "wasi_python"

    def _unset_default(self, home: Path) -> Path:
        return self.default_cache_dir(home)  # macOS reads no override


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
