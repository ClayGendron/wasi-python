"""What both platform families run: the Windows class and the POSIX classes alike.

The result of a walk (`_Walked`) and the refusal of a walk that cannot be taken, the steps a
walk takes by path (making a missing tail, making a real folder below a root, a quiet unlink),
the owner test a made folder must pass, the cache's kind checks, their warning and a checked
`.cwasm` held open, and the remover's budget and its walk by path. They sit below both platform
modules, so the Windows module and the POSIX module each import this one and neither imports
the other: the package's imports point one way, with no cycle. Of the package this module
imports only the process state, whose observers may stand in for a file's owner, and it reads
no platform: each name here runs the same on every system, and the choice of platform stays in
the platform module's one chooser.
"""

from __future__ import annotations

import errno
import os
import stat
from collections.abc import Callable
from pathlib import Path

from ._process import process

Identity = tuple[int, int]


class _Walked:
    """A host folder walked component by component: the path wasmtime is given, the identities of
    the folder and each ancestor (the folder's first), and what keeps it from changing until the
    identity check: on POSIX the folder's descriptor, on Windows every component's handle. A root
    still to be made has `missing` components, and its chain is its deepest existing ancestor's.
    `close` releases the holds through the closer of the walk that made it, and `fd` is the
    folder's descriptor on a walk by descriptors, else None."""

    def __init__(
        self,
        path: str,
        chain: tuple[Identity, ...],
        held: list[int],
        *,
        descriptors: bool = False,
        closer: Callable[[int], None],
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
        for h in held:
            self.closer(h)


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


def _unlink_quietly(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


_BUSY = {errno.EACCES, errno.EDEADLK, getattr(errno, "EDEADLOCK", errno.EDEADLK)}
_REMOVE_BATCH = 1024  # entries a listing reads before it acts


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


def _one_file(st: os.stat_result) -> bool:
    """A regular file with one name, as `mkstemp` and a rename leave the runner's own: a second
    name is a hard link a guest could make to a file elsewhere without writing a byte."""
    return stat.S_ISREG(st.st_mode) and st.st_nlink == 1


class _Opened:
    """A checked `.cwasm`, open: `fd` is the file the runner checked, and `name` the name wasmtime
    is given to open it by, the descriptor's own where the system has one. Where it is the path
    instead, `by_path` asks the caller to check the name's stamp again after the load. `close`
    closes the descriptor once wasmtime has the file."""

    def __init__(self, fd: int, name: str, *, by_path: bool) -> None:
        self.fd, self.name, self.by_path = fd, name, by_path

    def close(self) -> None:
        os.close(self.fd)


def _not_used(path: Path, must_be: str) -> None:
    import warnings

    warnings.warn(
        f"wasi_python: not using the module cache at {path}: it must be {must_be}",
        RuntimeWarning,
        stacklevel=6,
    )


def _this_users(st: os.stat_result) -> bool:
    """Whether the file `st` describes is this user's: owned by the effective uid, the one a file
    or folder this process makes is owned by. Windows has no uid, so there every file is, and no
    owner is compared. The observers' `owner_of`, when set, stands in for the owner."""
    geteuid: Callable[[], int] | None = getattr(os, "geteuid", None)
    if geteuid is None:
        return True
    owner_of = process().observers.owner_of
    return (st.st_uid if owner_of is None else owner_of(st)) == geteuid()


def _refuse_another_users(where: str, path: str, st: os.stat_result) -> None:
    """A folder on the way to a root, made here or found made, must be this user's: another user
    who made it first could read and seed every file the guest keeps below it."""
    if not _this_users(st):
        raise ValueError(
            f"{where}: {path!r}: a folder on the way to the root was made by another user"
        )


def _make_by_path(where: str, path: str, missing: tuple[str, ...]) -> str:
    """Make a root's missing components by path, each for this user alone, and refuse one
    another user made first, judged by `lstat` so a link put at the name is judged as itself and
    never followed. Windows applies a mode of exactly 0700 as an access list for this user,
    SYSTEM and the administrators from Python 3.13, and ignores the mode before."""
    for name in missing:
        path = os.path.join(path, name)
        Path(path).mkdir(mode=0o700, exist_ok=True)
        _refuse_another_users(where, path, os.lstat(path))
    return path


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
