"""What the operating system decides, behind one interface chosen once at import.

`PLATFORM` is the one platform object: a `_Linux`, a `_Darwin`, a `_Windows`, or a `_Posix` for
any other POSIX host, bound by `_select`, the only place in the package that asks the
interpreter which system this is. Every caller writes `from . import _platform` and reads
`_platform.PLATFORM` at the call, so a check that binds another platform for its duration is
seen by every caller. The POSIX classes live in `_platform_posix.py`, the Windows class in
`_platform_windows.py`, and what both families run in `_platform_common.py`, below both; no other
module imports any of the three, and what a caller needs of the shared half has a delegate here.
This module keeps the interface, the one choice and the names callers read.

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
  user's, root's or, on `/`'s own device, the owner of `/`'s, and closed to other writers, on
  macOS by its access list too, which the mode bits do not show;
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

import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from . import _platform_common
from ._platform_common import Identity as Identity
from ._platform_common import _Opened
from ._platform_common import _Walked as _Walked
from ._platform_posix import _Darwin, _Linux, _Posix
from ._platform_windows import _Windows
from ._process import process


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

# The refusal a call raises when Linux's check finds one of wasmtime's trap handlers replaced.
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
    def open_owned(
        self, path: Path, *, lstat: Callable[[str], os.stat_result] = os.lstat
    ) -> int: ...
    def output_channel(self) -> tuple[str, int, int] | None: ...


# What callers outside the platform modules need of the shared half, reached through this door.
# Each delegates at the call, so a stand-in set on `_platform_common` is seen; each has a name of
# its own, since a runner name is defined in one module.


def _rewritten_on_windows(name: str) -> bool:
    """Whether Windows rewrites or rejects this one path component."""
    return _platform_common._rewritten(name)


def _owned_by_this_user(st: os.stat_result) -> bool:
    """Whether the file `st` describes is this user's."""
    return _platform_common._this_users(st)


def _remove_file_quietly(path: str) -> None:
    """Remove `path`, if it can be removed."""
    _platform_common._unlink_quietly(path)


def _open_flags(*names: str) -> int:
    """The open flags of these names that this system has, or'd together; one it lacks adds none."""
    return _platform_common._flags(*names)


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


if TYPE_CHECKING:
    # The checker reads `_select` as Linux's and skips the other branches, so the macOS and plain
    # POSIX classes are held to the protocol here: a member the protocol gains and one of them
    # lacks is an error. Never called. The Windows class is held in its own module's pass.
    def _conforms(darwin: _Darwin, posix: _Posix) -> tuple[_Platform, _Platform]:
        return darwin, posix
