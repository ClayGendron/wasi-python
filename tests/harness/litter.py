"""Host litter: files a host process drops into a folder the guest sees (spec 089).

macOS writes `.DS_Store` files into folders it sizes (System Settings' storage scan and Finder,
through its folder-size cache), as the user, at any moment. A file that appears in a grant while a
guest runs changes what the guest lists, and the folder's times, and so its fuel
(`context/research/2026-10-19-ds-store-in-the-judges-stages.md`). Two defences, and neither ever
hides a file from the guest:

- A read-only stage is sealed: every folder in it loses its write bits once it is staged, so no
  process of the user's can add a file to it. It is unsealed only to be removed.
- Every guest run is watched: no grant may hold litter before or after the run, and a read-only
  grant must hold exactly the same entries after the run as before. A watched run that fails
  raises `HostLitter`, naming the file; it is never filtered out, retried or ignored.

A stage's writer refuses a member with a litter name (`refuse`), so the cleanup in `seal` can
never delete a real input. A judge killed before its teardown leaves sealed stages, which
`rm -rf` cannot empty; they are never read again (every stage has a fresh name), and
`chmod -R u+w build/harness` makes them removable (spec 089, F3).
"""

from __future__ import annotations

import os
import shutil
import stat
import sys
from collections.abc import Iterable
from pathlib import Path

from harness import paths

# What an operating system or its helpers leave in folders on their own, never a source file:
# spec 011's three, and the names spec 090 adds to the build's list (AppleDouble `._x` files are
# matched by their prefix).
LITTER_NAMES = frozenset(
    {
        *paths.OS_LITTER,  # .DS_Store, Thumbs.db, desktop.ini
        "ehthumbs.db",
        "Icon\r",  # a folder's custom icon
        ".Spotlight-V100",  # the rest are a volume's root folders
        ".fseventsd",
        ".Trashes",
        ".TemporaryItems",
        ".DocumentRevisions-V100",
        ".apdisk",
    }
)
SEAL_ROUNDS = 10  # scans for litter that landed while staging, before sealing gives up
REMOVE_TRIES = 5  # a writer can refill a folder between rmtree's unlinks (spec 018's race)


def is_litter(name: str) -> bool:
    """True for a name only an operating system leaves."""
    return name in LITTER_NAMES or name.startswith("._")


def refuse(member: str, source: str) -> None:
    """A stage's writer calls this for each member it stages: a member whose path has a litter
    name in it would be deleted by `seal`'s cleanup, so it is refused, by name, instead."""
    parts = member.replace("\\", "/").split("/")
    if any(is_litter(part) for part in parts):
        raise AssertionError(
            f"{source}: member {member!r} has a name only an operating system leaves; the judge"
            " would take it for host litter (spec 089, F6)"
        )


class HostLitter(AssertionError):
    """A file no check put there is in a folder the guest sees: the run proves nothing."""


def litter_in(root: Path) -> list[str]:
    """Every litter entry under `root`, relative to it, sorted; symlinks are not followed."""
    found: list[str] = []
    for d, dirs, files in os.walk(root):
        for name in (*dirs, *files):
            if is_litter(name):
                found.append(Path(d, name).relative_to(root).as_posix())
    return sorted(found)


def inventory(root: Path) -> frozenset[str]:
    """Every entry under `root`, relative to it (a folder with a trailing slash)."""
    out: set[str] = set()
    for d, dirs, files in os.walk(root):
        rel = Path(d).relative_to(root)
        out |= {(rel / n).as_posix() + "/" for n in dirs}
        out |= {(rel / n).as_posix() for n in files}
    return frozenset(out)


def _set_writable(root: Path, on: bool, *, deep: bool = True) -> list[str]:
    """Set or clear the write bits of `root`'s folders; on Windows, where a folder's mode does not
    stop a write, nothing (the watch alone holds there). Carries on past a folder it cannot
    change, and returns those."""
    if sys.platform == "win32":
        return []
    failed: list[str] = []
    if not deep:
        folders = [str(root)]
    elif on:  # top down, so each folder can be listed before its children are reached
        folders = []
        for d, _dirs, _files in os.walk(root, onerror=lambda e: failed.append(str(e.filename))):
            _chmod(d, True, failed)
        return failed
    else:
        folders = [d for d, _dirs, _files in os.walk(root)]
    for d in folders:
        _chmod(d, on, failed)
    return failed


def _chmod(d: str, on: bool, failed: list[str]) -> None:
    try:
        mode = stat.S_IMODE(os.lstat(d).st_mode)
        off = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH
        os.chmod(d, (mode | stat.S_IWUSR) if on else (mode & ~off))
    except OSError:
        failed.append(d)


def seal(root: Path) -> list[str]:
    """Take the write bits off every folder under `root`, `root` included, in place (never a move
    or a link), so no process of this user can add, remove or rename an entry. Then remove litter
    that landed while the stage was written (never staged; no guest has run): each file's folder
    is opened for its unlink alone, and the scan repeats until it finds none. Returns what was
    removed."""
    _set_writable(root, False)
    removed: list[str] = []
    found: list[str] = []
    for _ in range(SEAL_ROUNDS):
        found = litter_in(root)
        if not found:
            return removed
        for rel in reversed(found):
            p = root / rel
            _set_writable(p.parent, True, deep=False)
            try:
                if p.is_dir() and not p.is_symlink():
                    _set_writable(p, True)
                    shutil.rmtree(p)
                else:
                    p.unlink()
            finally:
                _set_writable(p.parent, False, deep=False)
        removed += found
    raise HostLitter(
        _message([f"{rel} keeps coming back while the stage is sealed" for rel in found])
    )


def unseal(root: Path) -> list[str]:
    """Give every folder under `root` its owner's write bit back, carrying on past any folder it
    cannot change; returns those."""
    return _set_writable(root, True) if root.exists() else []


def remove(root: Path) -> bool:
    """Unseal, then remove, a stage (a sealed folder cannot be emptied), trying again if a writer
    refilled a folder meanwhile. If anything is still there after the last try, it is left
    unsealed (so `rm -rf` can take it) and named on stderr, never left in silence; the stage is
    never read again, since every stage has a fresh name. True when it is gone."""
    for _ in range(REMOVE_TRIES):
        unseal(root)
        shutil.rmtree(root, ignore_errors=True)
        if not root.exists():
            return True
    stuck = unseal(root)
    sys.stderr.write(
        f"host litter: could not remove {root} after {REMOVE_TRIES} tries"
        + (f"; folders still sealed: {stuck[:3]}" if stuck else " (left unsealed)")
        + "; it is never read again; `chmod -R u+w build/harness` then `rm -rf` clears it"
        " (spec 089)\n"
    )
    return False


def sealed_leftovers(root: Path) -> list[str]:
    """Folders under `root` without their owner's write bit: what a killed judge left sealed.
    Only named, never unsealed here (no sweep: spec 089, Decision 3)."""
    if sys.platform == "win32" or not root.is_dir():
        return []
    return [d for d, _dirs, _files in os.walk(root) if not os.lstat(d).st_mode & stat.S_IWUSR]


class Watch:
    """One guest run's grants, looked at before and after the run. `grants` are (host folder,
    guest path, writable), as `guest.run` preopens them."""

    def __init__(self, grants: Iterable[tuple[str, str, bool]]) -> None:
        self.grants = [(Path(h), g, w) for h, g, w in grants]
        self.before: dict[str, frozenset[str]] = {}
        problems: list[str] = []
        for host, guest, writable in self.grants:
            problems += [f"{_join(guest, rel)} (before the run)" for rel in litter_in(host)]
            if not writable:
                self.before[guest] = inventory(host)
        if problems:
            raise HostLitter(_message(problems))

    def after(self) -> None:
        problems: list[str] = []
        for host, guest, writable in self.grants:
            problems += [f"{_join(guest, rel)} (after the run)" for rel in litter_in(host)]
            if not writable:
                now, old = inventory(host), self.before[guest]
                problems += [f"{_join(guest, rel)} appeared during the run" for rel in now - old]
                problems += [f"{_join(guest, rel)} vanished during the run" for rel in old - now]
        if problems:
            raise HostLitter(_message(sorted(set(problems))))


def _join(guest: str, rel: str) -> str:
    return guest.rstrip("/") + "/" + rel


def _message(problems: list[str]) -> str:
    shown = problems[:8] + ([f"and {len(problems) - 8} more"] if len(problems) > 8 else [])
    return (
        "a host process changed a folder the guest sees, so this run's outcome and fuel prove"
        " nothing: " + "; ".join(shown) + " (litter such as .DS_Store comes from macOS's"
        " folder-size cache: System Settings' storage scan, Finder; spec 089. A run it voids is"
        " run again once the writer is stopped; a stage a killed judge left sealed is cleared by"
        " `chmod -R u+w build/harness`)"
    )
