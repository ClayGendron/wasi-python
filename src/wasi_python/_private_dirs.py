"""Private folders: `_Private` and its lock protocol, the sweep, the budgeted tree remover and
its two walks, the queued warnings, and the removal of a fresh home."""

from __future__ import annotations

import errno
import os
import re
import secrets
import stat
import tempfile
import warnings
from pathlib import Path

from . import _platform, _platform_common
from ._process import process

# Private folders and the sweep. Each private root and stdin folder has a
# lock file beside it in the temporary folder, locked for the folder's life and naming the kernel
# that made it. A process killed mid-call leaves both; the lock dies with it, so the next process
# on the same kernel can tell its folder is dead. A pid could not: pids repeat across namespaces,
# are reused, and a killed child is a zombie until reaped.
_LOCK_NAME = re.compile(r"wasi-python-(root-|zip-)?[0-9a-f]{16}\.lock\Z")  # zip-: the zip folders'


class _Taken(Exception):
    pass


class _Private:
    """A private folder in the temporary folder, with `<name>.lock` beside it, held locked until
    `remove`. The name is drawn here, as mkdtemp draws one, because the lock file must
    exist, locked, before the folder does."""

    def __init__(self, prefix: str) -> None:
        temp = tempfile.gettempdir()
        identity = _platform.PLATFORM.kernel_identity()
        create = _platform._flags(
            "O_RDWR", "O_CREAT", "O_EXCL", "O_NOFOLLOW", "O_CLOEXEC", "O_BINARY"
        )
        for _ in range(100):
            name = prefix + secrets.token_hex(8)
            lock_path, path = os.path.join(temp, name + ".lock"), os.path.join(temp, name)
            with process().held_lock:
                process().held.add(name)
            try:
                fd = os.open(lock_path, create, 0o600)
            except FileExistsError:
                _drop(name)
                continue
            except BaseException:
                _drop(name)
                raise
            owns = False  # the file at lock_path is the one this call made
            try:
                locked = _platform.PLATFORM.try_lock(fd)
                if locked is False:
                    raise _Taken
                owns = _platform._same_file(
                    fd, lock_path
                )  # a sweeper may have removed it, still empty
                if not owns:
                    raise _Taken
                if locked and identity is not None:  # unlocked: no identity, so never swept
                    os.lseek(fd, 0, 0)
                    os.write(fd, identity.encode("ascii") + b"\n")
                os.mkdir(path, 0o700)
            except (_Taken, FileExistsError):
                _abandon(fd, lock_path if owns else None, name)
                continue
            except BaseException:
                _abandon(fd, lock_path if owns else None, name)
                raise
            self.name, self.fd, self.lock_path, self.path = name, fd, lock_path, Path(path)
            return
        raise FileExistsError(errno.EEXIST, "no usable temporary folder name found")

    def remove(self) -> None:
        """Folder, then lock (close), then the lock file only if the folder is gone, then the
        name; never raises. A folder left keeps its lock file,
        is named in one warning, and re-arms the sweep, after its name is dropped."""
        errors: list[BaseException] = []
        gone = False
        try:
            try:
                _platform.PLATFORM.remove_tree(self.path, errors=errors)
            except Exception as e:  # a failure no one foresaw is a folder left, never a raise
                errors.append(e)
        finally:
            _platform.PLATFORM.unlock_close(self.fd)  # the lock file only once the folder is gone
            try:
                gone = not os.path.lexists(self.path)
                if gone:
                    _platform_common._unlink_quietly(self.lock_path)
            finally:
                _drop(self.name)
        if not gone:
            _warn_later(
                self.name,
                f"wasi_python: could not remove the private folder {self.path} "
                f"({_first_error(errors)}); it is kept with its lock file and retried at the "
                "next call",
            )
            # After the drop, so a sweep that runs first cannot spend the retry.
            with process().cache_lock:
                process().sweep_claimed = False


def _drop(name: str) -> None:
    p = process()
    with p.held_lock:
        p.held.discard(name)


def _abandon(fd: int, lock_path: str | None, name: str) -> None:
    _platform.PLATFORM.unlock_close(fd)
    if lock_path is not None:  # only a lock file this call made and still has at that name
        try:
            os.unlink(lock_path)
        except OSError:
            pass
    _drop(name)


def _sweep_once() -> None:
    """At a process's first call: remove the private folders of dead processes on this kernel.
    Claimed under the cache lock, run without it; it never raises into the call."""
    p = process()
    with p.cache_lock:
        if p.sweep_claimed:
            return
        p.sweep_claimed = True
    retry = False
    try:
        identity = _platform.PLATFORM.kernel_identity()
        if identity is None:
            return
        temp = tempfile.gettempdir()
        for entry in os.listdir(temp):
            try:
                retry = _sweep_entry(temp, entry, identity) or retry
            except Exception:
                continue
    except Exception:
        return
    finally:
        if retry:  # after the loop, so no second sweep starts while this one lists
            with p.cache_lock:
                p.sweep_claimed = False


def _owned(st: os.stat_result) -> bool:
    """This user's, by the platform's one owner test: on Windows, the user's own temporary
    folder is the owner check."""
    return _platform_common._this_users(st)


def _sweep_entry(temp: str, entry: str, identity: str) -> bool:
    """Removes one dead folder; True when it failed and may be retried by a re-armed sweep: a
    name fails at most `_SWEEP_TRIES` sweeps in this process, then waits for the next process."""
    if not _LOCK_NAME.match(entry):
        return False
    name = entry[: -len(".lock")]
    p = process()
    with p.held_lock:
        if name in p.held or p.sweep_failed.get(name, 0) >= _SWEEP_TRIES:
            return False
    lock_path, path = os.path.join(temp, entry), os.path.join(temp, name)
    named = os.lstat(lock_path)
    if not stat.S_ISREG(named.st_mode) or not _owned(named):
        return False  # not a lock of ours: nothing to sweep, nothing to retry
    fd = os.open(
        lock_path, _platform._flags("O_RDWR", "O_NOFOLLOW", "O_NONBLOCK", "O_CLOEXEC", "O_BINARY")
    )
    unlink = False
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode):
            return False
        if (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino):
            return False
        if not _platform.PLATFORM.try_lock(fd):
            return False  # a live call holds it
        os.lseek(fd, 0, 0)
        first = os.read(fd, 256).split(b"\n", 1)[0].decode("ascii", "replace")
        if not os.path.lexists(path):
            unlink = first in ("", identity)  # a lone lock file: nothing of a call's to lose
            return False
        if first != identity:
            return False  # another kernel's, or none
        folder = os.lstat(path)
        isjunction = getattr(os.path, "isjunction", lambda p: False)
        if not stat.S_ISDIR(folder.st_mode) or isjunction(path) or not _owned(folder):
            return False  # another user's folder at a dead lock's name is not ours to remove
        errors: list[BaseException] = []
        _platform.PLATFORM.remove_tree(path, errors=errors)
        if not os.path.lexists(path):
            with p.held_lock:
                p.sweep_swept += 1
            unlink = True
            return False
        with p.held_lock:
            tries = p.sweep_failed[name] = p.sweep_failed.get(name, 0) + 1
        _warn_later(
            name,
            f"wasi_python: the sweep could not remove {path} ({_first_error(errors)}); it is "
            "kept with its lock file",
        )
        return tries < _SWEEP_TRIES
    finally:
        # The platform orders the unlink and the lock's release: POSIX unlinks while still
        # holding the lock, so a creator that locks the file after this fails its same-file
        # check and draws again; Windows cannot delete an open file.
        _platform.PLATFORM.unlock_close(fd, unlink=lock_path if unlink else None)


_REMOVE_BUDGET = 2**20  # counted calls (open, listing, unlink, rmdir) for one HOME's removal
_SWEEP_TRIES = 3  # failed sweeps of one name in one process, then the next process tries


def _first_error(errors: list[BaseException]) -> str:
    return str(errors[0]) if errors else "unknown error"


def _warn_later(key: str, message: str) -> None:
    """Queue a warning, once per folder per process; `_flush_warnings` gives it."""
    p = process()
    with p.warnings_lock:
        if key in p.warned:
            return
        p.warned.add(key)
        p.pending_warnings.append(message)


def _flush_warnings() -> None:
    """Give the queued warnings, as RuntimeWarning, outside every runner lock: an embedder's
    `showwarning` may call `stats()` or `run`. A filter that turns them into errors loses them,
    never the call."""
    p = process()
    with p.warnings_lock:
        if not p.pending_warnings:
            return
        pending = list(p.pending_warnings)
        p.pending_warnings.clear()
    for message in pending:
        try:
            warnings.warn(message, RuntimeWarning, stacklevel=3)
        except Exception:
            pass


process().flush_warnings = _flush_warnings  # the exit release gives what the removals queued


def _remove_fresh_home(name: str, tmp: Path | None, tmp_fd: int | None) -> None:
    """A fresh HOME's removal: budgeted, since another call on the same root may be writing it;
    a HOME left is named, never retried (it has no lock file)."""
    errors: list[BaseException] = []
    if tmp_fd is not None:
        gone = _platform.PLATFORM.remove_tree(
            name, dir_fd=tmp_fd, budget=_REMOVE_BUDGET, errors=errors
        )
    elif tmp is not None:
        gone = _platform.PLATFORM.remove_tree(tmp / name, budget=_REMOVE_BUDGET, errors=errors)
    else:
        return
    if not gone:
        where = name if tmp is None else os.path.join(tmp, name)
        _warn_later(
            where,
            f"wasi_python: could not remove the call's fresh HOME {where} "
            f"({_first_error(errors)}); it is left in the caller's folder",
        )
