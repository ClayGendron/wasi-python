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

from . import _platform
from ._process import process

# Private folders and the sweep (spec 016, Decision 2). Each private root and stdin folder has a
# lock file beside it in the temporary folder, locked for the folder's life and naming the kernel
# that made it. A process killed mid-call leaves both; the lock dies with it, so the next process
# on the same kernel can tell its folder is dead. A pid could not: pids repeat across namespaces,
# are reused, and a killed child is a zombie until reaped.
_LOCK_NAME = re.compile(r"wasi-python-(root-|zip-)?[0-9a-f]{16}\.lock\Z")  # zip-: spec 017


class _Taken(Exception):
    pass


class _Private:
    """A private folder in the temporary folder, with `<name>.lock` beside it, held locked until
    `remove` (spec 016). The name is drawn here, as mkdtemp draws one, because the lock file must
    exist, locked, before the folder does."""

    def __init__(self, prefix: str) -> None:
        temp = tempfile.gettempdir()
        identity = _platform._kernel_identity()
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
                locked = _platform._try_lock(fd)
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
        name; never raises (the 0.1.0a2 security review, F1). A folder left keeps its lock file,
        is named in one warning, and re-arms the sweep, after its name is dropped (spec 084)."""
        errors: list[BaseException] = []
        gone = False
        try:
            try:
                _remove_tree(self.path, errors=errors)
            except Exception as e:  # a failure no one foresaw is a folder left, never a raise
                errors.append(e)
        finally:
            _platform._unlock_close(self.fd)  # Windows cannot delete an open file
            try:
                gone = not os.path.lexists(self.path)
                if gone:
                    _unlink_quietly(self.lock_path)
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
    _platform._unlock_close(fd)
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
        identity = _platform._kernel_identity()
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
        if retry:  # after the loop, so no second sweep starts while this one lists (spec 084)
            with p.cache_lock:
                p.sweep_claimed = False


def _owned(st: os.stat_result) -> bool:
    getuid = getattr(os, "getuid", None)
    return getuid is None or st.st_uid == getuid()  # Windows: the user's own temporary folder


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
        if not _platform._try_lock(fd):
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
        if not stat.S_ISDIR(folder.st_mode) or isjunction(path):
            return False
        errors: list[BaseException] = []
        _remove_tree(path, errors=errors)
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
        # POSIX unlinks while still holding the lock, so a creator that locks the file after
        # this fails its same-file check and draws again; Windows cannot delete an open file.
        if unlink and os.name == "posix":
            _unlink_quietly(lock_path)
        _platform._unlock_close(fd)
        if unlink and os.name != "posix":
            _unlink_quietly(lock_path)


def _unlink_quietly(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


# The removal (spec 084). A guest can build a tree one level at a time through dir_fd, deeper
# than the process's free descriptors, and shutil.rmtree holds one descriptor per level (and on
# 3.11 one Python frame per level). `_remove_tree` holds at most two: on POSIX it goes down by
# name with O_NOFOLLOW and up by "..", checking each parent against the identity it recorded on
# the way down; elsewhere (Windows) it walks extended-length paths. It creates, renames and
# chmods nothing: what it may not delete, it leaves (spec 084, Decision 4). Only a fresh HOME,
# which another call on the same root may be writing, gets a budget of calls (Decision 12).
_REMOVE_BUDGET = 2**20  # counted calls (open, listing, unlink, rmdir) for one HOME's removal
_REMOVE_BATCH = 1024  # entries a listing reads before it acts
_SWEEP_TRIES = 3  # failed sweeps of one name in one process, then the next process tries
_DIR_OPEN = _platform._flags("O_RDONLY", "O_DIRECTORY", "O_NOFOLLOW", "O_CLOEXEC", "O_NONBLOCK")


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


def _remove_tree(
    path: str | os.PathLike[str],
    *,
    dir_fd: int | None = None,
    budget: int | None = None,
    errors: list[BaseException] | None = None,
) -> bool:
    """Remove the tree at `path` (a name in `dir_fd` when given); True when nothing is left at
    that name. Never raises an `Exception`; the first error it met is appended to `errors`."""
    removal = _Removal(budget)
    try:
        if _platform._dir_fd_ok():
            gone = _remove_at(os.fspath(path), dir_fd, removal)
        elif dir_fd is None:
            gone = _remove_by_path(_long_path(os.fspath(path)), removal)
        else:
            raise NotImplementedError("dir_fd unavailable on this platform")
    except Exception as e:  # _Spent included
        removal.fail(e)
        gone = False
    if not gone and errors is not None and removal.error is not None:
        errors.append(removal.error)
    return gone


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
    except PermissionError as e:  # mode 0000, say: an empty one goes by rmdir (the review's N1)
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


def _long_path(path: str) -> str:
    """An extended-length path on Windows, so no path is limited to 260 characters."""
    path = os.path.abspath(path)
    if os.name != "nt" or path.startswith("\\\\?\\"):
        return path
    if path.startswith("\\\\"):
        return "\\\\?\\UNC\\" + path[2:]
    return "\\\\?\\" + path


def _remove_by_path(top: str, removal: _Removal) -> bool:
    """Windows (and POSIX when a test forces it): the same walk on paths, down by joining a name
    and up by dropping it. Links and junctions are removed, never entered."""
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


def _first_error(errors: list[BaseException]) -> str:
    return str(errors[0]) if errors else "unknown error"


def _warn_later(key: str, message: str) -> None:
    """Queue a warning, once per folder per process; `_flush_warnings` gives it (spec 084)."""
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
    a HOME left is named, never retried (it has no lock file) (spec 084, Decision 12)."""
    errors: list[BaseException] = []
    if tmp_fd is not None:
        gone = _remove_tree(name, dir_fd=tmp_fd, budget=_REMOVE_BUDGET, errors=errors)
    elif tmp is not None:
        gone = _remove_tree(tmp / name, budget=_REMOVE_BUDGET, errors=errors)
    else:
        return
    if not gone:
        where = name if tmp is None else os.path.join(tmp, name)
        _warn_later(
            where,
            f"wasi_python: could not remove the call's fresh HOME {where} "
            f"({_first_error(errors)}); it is left in the caller's folder",
        )
