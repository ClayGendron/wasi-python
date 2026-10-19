"""A prototype of spec 084's removal (POSIX only), to test the design, not the product's code.

The tree is made wide, not deep: every folder below the top is renamed up into one holding folder
the removal makes inside the top, under a sequential name, and each piece is then emptied at depth
two. It holds at most four descriptors (the top, the holding folder, one piece, the listing's dup),
never follows a link, and never crosses a device."""

from __future__ import annotations

import os
import secrets
import stat

DIR = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC | getattr(os, "O_NONBLOCK", 0)
BATCH = 1024
ops = {"open": 0, "close": 0, "scandir": 0, "rename": 0, "unlink": 0, "rmdir": 0, "fchmod": 0,
       "mkdir": 0, "open_now": 0, "open_peak": 0}


def _open(name, dir_fd):
    fd = os.open(name, DIR, dir_fd=dir_fd)
    ops["open"] += 1
    ops["open_now"] += 1
    ops["open_peak"] = max(ops["open_peak"], ops["open_now"])
    return fd


def _close(fd):
    os.close(fd)
    ops["close"] += 1
    ops["open_now"] -= 1


def _listing(fd):
    ops["scandir"] += 1
    ops["open_peak"] = max(ops["open_peak"], ops["open_now"] + 1)  # scandir(fd) dups fd
    out = []
    with os.scandir(fd) as it:
        for e in it:
            out.append(e)
            if len(out) == BATCH:
                break
    return out


def _is_dir(entry) -> bool:
    try:
        return entry.is_dir(follow_symlinks=False)
    except OSError:
        return False


def _writable(fd) -> None:
    """A folder the user made unwritable or unsearchable: made 0700 once, through its descriptor."""
    os.fchmod(fd, 0o700)
    ops["fchmod"] += 1


def _fix(fd, entry, is_dir) -> None:
    """Once per entry: a folder the user made unwritable or unsearchable becomes 0700 (through its
    own descriptor, or lchmod where the platform has it); a file's folder becomes 0700."""
    if not is_dir:
        _writable(fd)
        return
    try:
        cfd = _open(entry.name, fd)
    except PermissionError:  # 0o000: no descriptor to be had
        if os.chmod in os.supports_follow_symlinks:
            os.chmod(entry.name, 0o700, dir_fd=fd, follow_symlinks=False)
        else:  # Linux: lstat said folder; nothing live writes a dead root
            os.chmod(entry.name, 0o700, dir_fd=fd)
        ops["fchmod"] += 1
        return
    try:
        _writable(cfd)
    finally:
        _close(cfd)


def _empty(fd, dev, hold_fd, counter, failures, skip=None) -> None:
    """Move every subfolder of the open folder into the holding folder, unlink everything else."""
    fixed: set = set()
    folder_fixed = False
    while True:
        entries = [e for e in _listing(fd) if e.name != skip]
        if not entries:
            return
        progress = False
        for e in entries:
            d = _is_dir(e)
            try:
                if d:
                    if e.stat(follow_symlinks=False).st_dev != dev:
                        failures.append(("device", e.name))
                        continue
                    counter[0] += 1
                    os.rename(e.name, str(counter[0]), src_dir_fd=fd, dst_dir_fd=hold_fd)
                    ops["rename"] += 1
                else:
                    os.unlink(e.name, dir_fd=fd)
                    ops["unlink"] += 1
                progress = True
            except FileNotFoundError:
                progress = True
            except PermissionError:
                if d:
                    counter[0] -= 1
                key = e.name if d else None
                if (d and e.name not in fixed) or (not d and not folder_fixed):
                    try:
                        if not folder_fixed:
                            _writable(fd)
                            folder_fixed = True
                        if d:
                            _fix(fd, e, True)
                            fixed.add(e.name)
                    except OSError as err:
                        failures.append((err.errno, e.name))
                        continue
                    progress = True
                    continue
                failures.append(("permission", e.name))
            except OSError as err:
                if d:
                    counter[0] -= 1
                failures.append((err.errno, e.name))
        if not progress:
            return


def remove_tree(name: str, parent_fd: int) -> bool:
    """Remove the folder `name` under `parent_fd`; True when it is gone. Never raises OSError."""
    failures: list = []
    try:
        top = _open(name, parent_fd)
    except FileNotFoundError:
        return True
    except OSError:
        return False
    try:
        st = os.fstat(top)
        if not stat.S_ISDIR(st.st_mode):
            return False
        dev = st.st_dev
        try:
            _writable(top) if not (st.st_mode & 0o700) == 0o700 else None
        except OSError:
            pass
        while True:  # a holding folder of our own, under a fresh name
            hold = ".wasi-python-rm-" + secrets.token_hex(8)
            try:
                os.mkdir(hold, 0o700, dir_fd=top)
                ops["mkdir"] += 1
                break
            except FileExistsError:
                continue
        hold_fd = _open(hold, top)
        counter = [0]
        try:
            # the top's own entries first (the holding folder is skipped by name)
            _empty(top, dev, hold_fd, counter, failures, skip=hold)
            done = 0
            while done < counter[0]:  # each piece, in the order it arrived
                done += 1
                piece = str(done)
                try:
                    pfd = _open(piece, hold_fd)
                except OSError as err:
                    failures.append((err.errno, piece))
                    continue
                try:
                    _empty(pfd, dev, hold_fd, counter, failures)
                finally:
                    _close(pfd)
                try:
                    os.rmdir(piece, dir_fd=hold_fd)
                    ops["rmdir"] += 1
                except OSError as err:
                    failures.append((err.errno, piece))
        finally:
            _close(hold_fd)
        try:
            os.rmdir(hold, dir_fd=top)
            ops["rmdir"] += 1
        except OSError as err:
            failures.append((err.errno, hold))
    finally:
        _close(top)
    try:
        os.rmdir(name, dir_fd=parent_fd)
        ops["rmdir"] += 1
    except FileNotFoundError:
        pass
    except OSError as err:
        failures.append((err.errno, name))
        return False
    return not failures or not _exists(name, parent_fd)


def _exists(name, parent_fd) -> bool:
    try:
        os.lstat(name, dir_fd=parent_fd)
        return True
    except FileNotFoundError:
        return False
