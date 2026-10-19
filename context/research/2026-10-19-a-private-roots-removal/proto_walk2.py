"""Revised after the pre-build review (F1, F3): no permission repair, and a budget of counted
calls. A prototype of spec 084's POSIX removal: a walk that holds two descriptors (the folder it is in,
and the one it opens next), descends by name and climbs by "..", checking each parent against
the identity it recorded on the way down. It renames nothing and makes nothing, so it needs no
disk space. Not the product's code."""

from __future__ import annotations

import os
import stat

DIR = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC | getattr(os, "O_NONBLOCK", 0)
BATCH = 1024
BUDGET = [2**20]  # counted calls (open, listing, unlink, rmdir) per removal; past it, False


class _Spent(Exception):
    pass


def _spend():
    if ops["open"] + ops["scandir"] + ops["unlink"] + ops["rmdir"] >= BUDGET[0]:
        raise _Spent


ops = {"open": 0, "close": 0, "scandir": 0, "unlink": 0, "rmdir": 0, "fchmod": 0,
       "open_now": 0, "open_peak": 0}


def _open(name, dir_fd):
    _spend()
    fd = os.open(name, DIR, dir_fd=dir_fd)
    ops["open"] += 1
    ops["open_now"] += 1
    ops["open_peak"] = max(ops["open_peak"], ops["open_now"])
    return fd


def _close(fd):
    os.close(fd)
    ops["close"] += 1
    ops["open_now"] -= 1


def _batch(fd, skip):
    _spend()
    ops["scandir"] += 1
    ops["open_peak"] = max(ops["open_peak"], ops["open_now"] + 1)  # scandir(fd) dups fd
    out = []
    with os.scandir(fd) as it:
        for e in it:
            if e.name not in skip:
                out.append(e)
                if len(out) == BATCH:
                    break
    return out


def _is_dir(e):
    try:
        return e.is_dir(follow_symlinks=False)
    except OSError:
        return False


def remove_tree(name: str, parent_fd: int) -> bool:
    """Remove `name` under `parent_fd`; True when it is gone. Never raises OSError."""
    try:
        st = os.lstat(name, dir_fd=parent_fd)
    except FileNotFoundError:
        return True
    except OSError:
        return False
    if not stat.S_ISDIR(st.st_mode):  # a link or a file where the folder was: the name is ours
        try:
            os.unlink(name, dir_fd=parent_fd)
            ops["unlink"] += 1
            return True
        except OSError:
            return False
    try:
        cur = _open(name, parent_fd)
    except OSError:
        return False
    here = os.fstat(cur)
    if (here.st_dev, here.st_ino) != (st.st_dev, st.st_ino):
        _close(cur)
        return False
    dev = here.st_dev
    # one frame per level below the top: (its name in its parent, the parent's identity, the
    # names in it that could not be removed)
    stack: list[tuple[str, tuple[int, int], set]] = []
    skip: set = set()
    ident = (here.st_dev, here.st_ino)
    fixed = False
    try:
        while True:
            entries = _batch(cur, skip)
            down = None
            progress = False
            for e in entries:
                if _is_dir(e):
                    try:
                        if e.stat(follow_symlinks=False).st_dev != dev:
                            skip.add(e.name)  # another filesystem: never entered
                            continue
                    except OSError:
                        skip.add(e.name)
                        continue
                    down = e.name
                    break
                try:
                    _spend()
                    os.unlink(e.name, dir_fd=cur)
                    ops["unlink"] += 1
                    progress = True
                except FileNotFoundError:
                    progress = True
                except OSError:
                    skip.add(e.name)
            if down is not None:
                try:
                    child = _open(down, cur)
                except _Spent:
                    raise
                except OSError:
                    skip.add(down)
                    continue
                cst = os.fstat(child)
                if cst.st_dev != dev:
                    _close(child)
                    skip.add(down)
                    continue
                stack.append((down, ident, skip))
                _close(cur)
                cur, ident, skip, fixed = child, (cst.st_dev, cst.st_ino), set(), False
                continue
            if entries and progress:
                continue  # more of this folder to list
            # this folder holds nothing it can remove: climb
            if not stack:
                break
            child_name, parent_ident, parent_skip = stack.pop()
            parent = _open("..", cur)
            pst = os.fstat(parent)
            if (pst.st_dev, pst.st_ino) != parent_ident:  # moved under us: never walk out
                _close(parent)
                return False
            _close(cur)
            cur, ident, skip, fixed = parent, parent_ident, parent_skip, False
            try:
                _spend()
                os.rmdir(child_name, dir_fd=cur)
                ops["rmdir"] += 1
            except FileNotFoundError:
                pass
            except OSError:
                skip.add(child_name)
    except _Spent:
        return False
    finally:
        _close(cur)
    try:
        os.rmdir(name, dir_fd=parent_fd)
        ops["rmdir"] += 1
        return True
    except FileNotFoundError:
        return True
    except OSError:
        return False
