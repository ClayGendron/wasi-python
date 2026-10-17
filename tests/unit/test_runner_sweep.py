"""A dead process's private folders are swept, by lock and kernel, and a trap is named by its
code (spec 016). Each case sweeps an empty temporary folder of its own; nothing here measures
time. The `verify` job runs this file on Linux, macOS and Windows."""

from __future__ import annotations

import errno
import os
import secrets
import shutil
import stat
import sys
import tempfile
from pathlib import Path

import pytest

from wasi_python import runner

IDENTITY = runner._kernel_identity()
POSIX = os.name == "posix"


@pytest.fixture
def temp(tmp_path, monkeypatch):
    """An empty temporary folder, and a sweep not yet claimed in this process."""
    if IDENTITY is None:
        pytest.skip("this host's kernel identity cannot be read, so nothing is swept")
    folder = tmp_path / "temp"
    folder.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(folder))
    monkeypatch.setitem(runner._sweep_state, "claimed", False)
    monkeypatch.setitem(runner._sweep_state, "swept", 0)
    return folder


def dead(temp: Path, name: str = "wasi-python-root-0123456789abcdef", first: str | None = None):
    """A folder and its lock file, as a killed process leaves them: unlocked, naming a kernel."""
    (temp / name).mkdir()
    (temp / name / "file").write_text("guest data")
    line = IDENTITY if first is None else first
    (temp / f"{name}.lock").write_bytes(line.encode() + (b"\n" if line else b""))
    return temp / name


def sweep() -> int:
    runner._sweep_once()
    return runner._sweep_state["swept"]


def names(temp: Path) -> list[str]:
    return sorted(p.name for p in temp.iterdir())


def test_a_dead_folder_is_removed_with_its_lock_file(temp) -> None:
    dead(temp)
    dead(temp, "wasi-python-0123456789abcdef")
    assert sweep() == 2
    assert names(temp) == []


def test_the_sweep_runs_once_per_process(temp) -> None:
    sweep()
    dead(temp)
    assert sweep() == 0 and len(names(temp)) == 2


def test_a_held_lock_keeps_its_folder(temp) -> None:
    folder = dead(temp)
    fd = os.open(f"{folder}.lock", os.O_RDWR | getattr(os, "O_BINARY", 0))
    try:
        assert runner._try_lock(fd)  # a live call's lock, through another open file
        assert sweep() == 0
        assert (folder / "file").exists()
    finally:
        os.close(fd)


def test_a_name_this_process_holds_is_never_swept(temp, monkeypatch) -> None:
    folder = dead(temp)
    monkeypatch.setattr(runner, "_held", {folder.name})
    assert sweep() == 0 and (folder / "file").exists()


@pytest.mark.parametrize("first", ["another-kernel", ""])
def test_another_kernels_folder_and_an_unnamed_one_stay(temp, first) -> None:
    folder = dead(temp, first=first)
    assert sweep() == 0 and (folder / "file").exists()


def test_a_folder_without_a_lock_file_stays(temp) -> None:
    (temp / "wasi-python-root-0123456789abcdef").mkdir()
    (temp / "wasi-python-root-x1y2z3").mkdir()  # a release before 0.1.0a3: no lock file
    assert sweep() == 0 and len(names(temp)) == 2


@pytest.mark.parametrize(("first", "removed"), [(None, True), ("", True), ("another", False)])
def test_a_lone_lock_file(temp, first, removed) -> None:
    folder = dead(temp, first=first)
    for p in folder.iterdir():
        p.unlink()
    folder.rmdir()
    assert sweep() == 0  # a lone lock file is no folder
    assert names(temp) == ([] if removed else [f"{folder.name}.lock"])


@pytest.mark.skipif(not POSIX, reason="Windows: the user's own temporary folder is the owner check")
def test_another_owner_is_refused(temp, monkeypatch) -> None:
    folder = dead(temp)
    lock, real_lstat = f"{folder}.lock", os.lstat

    def lstat(p, **k):
        st = real_lstat(p, **k)
        if str(p) != lock:
            return st
        fields = list(st[:10])
        fields[stat.ST_UID] = os.getuid() + 1  # another user's lock file
        return os.stat_result(fields)

    with monkeypatch.context() as m:
        m.setattr(os, "lstat", lstat)
        assert sweep() == 0
    assert (folder / "file").exists()


@pytest.mark.skipif(not POSIX, reason="Windows: the user's own temporary folder is the owner check")
def test_owned_means_this_users() -> None:
    mine = os.lstat(".")
    fields = list(mine[:10])
    fields[stat.ST_UID] = os.getuid() + 1
    assert runner._owned(mine) and not runner._owned(os.stat_result(fields))


@pytest.mark.skipif(not POSIX, reason="making a link needs privileges on Windows")
def test_links_are_never_followed(temp, tmp_path) -> None:
    canary = tmp_path / "canary"
    canary.mkdir()
    (canary / "keep").write_text("keep")
    # a link named like a lock file, and a link named like a root beside a dead lock file
    (temp / "wasi-python-1111111111111111.lock").symlink_to(canary / "keep")
    (temp / "wasi-python-root-2222222222222222").symlink_to(canary)
    (temp / "wasi-python-root-2222222222222222.lock").write_text(IDENTITY + "\n")
    # a dead folder holding a link to the canary
    folder = dead(temp, "wasi-python-root-3333333333333333")
    (folder / "out").symlink_to(canary)
    assert sweep() == 1
    assert (canary / "keep").read_text() == "keep"
    assert "wasi-python-root-3333333333333333" not in names(temp)
    assert (temp / "wasi-python-root-2222222222222222").is_symlink()


@pytest.mark.skipif(not POSIX, reason="no FIFOs on Windows")
def test_a_fifo_swapped_in_is_skipped(temp, monkeypatch) -> None:
    folder = dead(temp)
    lock = Path(f"{folder}.lock")
    regular = os.lstat(lock)
    lock.unlink()
    os.mkfifo(lock)
    real_lstat = os.lstat
    # the swap happens between the sweep's lstat and its open: lstat still sees the file
    with monkeypatch.context() as m:
        m.setattr(
            os, "lstat", lambda p, **k: regular if str(p) == str(lock) else real_lstat(p, **k)
        )
        assert sweep() == 0
    assert stat.S_ISFIFO(os.lstat(lock).st_mode) and (folder / "file").exists()


def test_a_failing_listing_leaves_the_call_alone(temp, monkeypatch) -> None:
    def broken(path):
        raise PermissionError(13, "denied")

    with monkeypatch.context() as m:
        m.setattr(os, "listdir", broken)
        assert sweep() == 0  # returned quietly
    private = runner._Private("wasi-python-root-")  # and the call goes on to make its folder
    private.remove()


def test_a_busy_name_is_drawn_again(temp, monkeypatch) -> None:
    """A sweeper holding a new lock file at the instant its creator tries it: the creator draws
    another name instead of raising (spec 016's confirmation, C4)."""
    real = runner._try_lock
    calls = []

    def once_busy(fd):
        calls.append(fd)
        return False if len(calls) == 1 else real(fd)

    monkeypatch.setattr(runner, "_try_lock", once_busy)
    private = runner._Private("wasi-python-")
    try:
        assert private.path.is_dir() and len(calls) == 2
    finally:
        private.remove()


def test_a_private_folder_goes_before_its_lock_file(temp, monkeypatch) -> None:
    private = runner._Private("wasi-python-root-")
    lock = Path(private.lock_path)
    os.lseek(private.fd, 0, 0)  # through the holder: Windows refuses a locked byte to any other
    assert lock.exists() and os.read(private.fd, 256).decode().strip() == IDENTITY
    seen = []
    real_unlink = os.unlink

    def unlink(p, *a, **k):
        seen.append((str(p), os.path.lexists(private.path)))
        return real_unlink(p, *a, **k)

    monkeypatch.setattr(os, "unlink", unlink)
    private.remove()
    assert seen == [(str(lock), False)]
    assert names(temp) == [] and private.name not in runner._held


def test_a_lock_file_swept_before_its_lock_makes_the_creator_draw_again(temp, monkeypatch) -> None:
    """A sweeper removes a new, still-empty lock file (the lone-lock rule) before its creator
    locks it: the creator draws another name instead of raising (build review, finding 1)."""
    real = runner._try_lock
    removed = []

    def swept_first(fd):
        if not removed:
            (lock,) = temp.glob("*.lock")
            removed.append(lock.name)
            lock.unlink()
        return real(fd)

    monkeypatch.setattr(runner, "_try_lock", swept_first)
    private = runner._Private("wasi-python-root-")
    try:
        assert private.path.is_dir() and Path(private.lock_path).name != removed[0]
    finally:
        private.remove()
    assert names(temp) == []


def test_a_filesystem_without_locks_still_makes_a_folder_that_is_never_swept(
    temp, monkeypatch
) -> None:
    """ENOLCK (NFS without a lock daemon): no lock and no identity, so the folder is only ever
    leaked, never swept; the call goes on (build review, finding 2)."""
    if POSIX:
        import fcntl

        monkeypatch.setattr(fcntl, "flock", lambda fd, op: _raise(OSError(errno.ENOLCK, "no")))
    else:
        import msvcrt

        monkeypatch.setattr(msvcrt, "locking", lambda *a: _raise(OSError(errno.ENOLCK, "no")))
    private = runner._Private("wasi-python-root-")
    try:
        assert private.path.is_dir() and Path(private.lock_path).read_bytes() == b""
        assert len(names(temp)) == 2  # one name drawn, nothing abandoned
        runner._held.discard(private.name)  # as another process would see it
        assert sweep() == 0 and private.path.is_dir()
    finally:
        private.remove()
    assert names(temp) == []


def test_a_lock_that_errors_keeps_its_folder(temp, monkeypatch) -> None:
    """A lock file naming this kernel whose lock attempt errors (a lock daemon gone away) stays
    with its folder: only a lock taken may lead to a removal (build review confirmation, N1)."""
    folder = dead(temp)
    no_lock = lambda *a: _raise(OSError(errno.ENOLCK, "no locks"))  # noqa: E731
    if POSIX:
        import fcntl

        monkeypatch.setattr(fcntl, "flock", no_lock)
    else:
        import msvcrt

        monkeypatch.setattr(msvcrt, "locking", no_lock)
    assert sweep() == 0 and (folder / "file").exists()


def _raise(e: BaseException):
    raise e


def test_only_contention_is_busy(monkeypatch) -> None:
    fd = os.open(os.devnull, os.O_RDONLY)
    try:
        if POSIX:
            import fcntl

            target, name = fcntl, "flock"
        else:
            import msvcrt

            target, name = msvcrt, "locking"
        monkeypatch.setattr(target, name, lambda *a: _raise(BlockingIOError(errno.EAGAIN, "busy")))
        busy = runner._try_lock(fd)
        if not POSIX:  # msvcrt.locking reports a held range as EACCES
            monkeypatch.setattr(target, name, lambda *a: _raise(OSError(errno.EACCES, "held")))
            assert runner._try_lock(fd) is False
        monkeypatch.setattr(target, name, lambda *a: _raise(OSError(errno.ENOLCK, "no locks")))
        assert busy is False and runner._try_lock(fd) is None
    finally:
        os.close(fd)


def test_an_existing_lock_file_is_never_opened_again(temp, monkeypatch) -> None:
    """O_EXCL: a drawn name whose lock file exists is left untouched and another is drawn."""
    taken = temp / "wasi-python-root-0000000000000000.lock"
    taken.write_bytes(b"someone else's\n")
    draws = iter(["0000000000000000", "1111111111111111"])
    monkeypatch.setattr(secrets, "token_hex", lambda n: next(draws))
    private = runner._Private("wasi-python-root-")
    try:
        assert private.name == "wasi-python-root-1111111111111111"
        assert taken.read_bytes() == b"someone else's\n"
    finally:
        private.remove()


def test_a_folder_rmtree_could_not_remove_keeps_its_lock_file(temp, monkeypatch) -> None:
    """Otherwise what is left is never swept (build review, finding 5)."""
    private = runner._Private("wasi-python-root-")
    (private.path / "file").write_text("guest data")
    with monkeypatch.context() as m:
        m.setattr(shutil, "rmtree", lambda *a, **k: None)
        private.remove()
    assert names(temp) == sorted([private.name, f"{private.name}.lock"])
    monkeypatch.setitem(runner._sweep_state, "claimed", False)
    monkeypatch.setitem(runner._sweep_state, "swept", 0)
    assert sweep() == 1 and names(temp) == []


@pytest.mark.skipif(not POSIX, reason="Windows cannot delete an open file")
def test_the_sweep_unlinks_before_it_lets_the_lock_go(temp, monkeypatch) -> None:
    """A creator that locks the file after the sweep fails its same-file check and draws again,
    instead of keeping a folder whose lock file is gone (build review, finding 6)."""
    folder = dead(temp)
    lock, real = f"{folder}.lock", runner._unlock_close
    seen = []

    def release(fd):
        seen.append(os.path.lexists(lock))
        real(fd)

    monkeypatch.setattr(runner, "_unlock_close", release)
    assert sweep() == 1 and seen == [False]


class FakeTrap:
    def __init__(self, code, message="first line\nmore"):
        self.trap_code, self.message = code, message


def test_a_trap_is_named_by_its_code() -> None:
    """The 0.1.0a2 security review, F7: a stack overflow read "error while executing at wasm
    backtrace:", wasmtime's heading, not its cause."""
    import wasmtime as wt

    assert runner._trap_name(FakeTrap(wt.TrapCode.OUT_OF_FUEL)) == "out of fuel"
    assert runner._trap_name(FakeTrap(wt.TrapCode.INTERRUPT)) == "deadline"
    assert runner._trap_name(FakeTrap(wt.TrapCode.STACK_OVERFLOW)) == "stack overflow"
    assert runner._trap_name(FakeTrap(wt.TrapCode.UNREACHABLE)) == "unreachable"
    assert runner._trap_name(FakeTrap(None)) == "first line"


def test_every_trap_code_has_a_plain_name() -> None:
    """A wasmtime release that renames or adds a code fails here first."""
    import wasmtime as wt

    names = {runner._trap_code_name(code) for code in wt.TrapCode}
    assert all(n and n == n.lower() and set(n) <= set("abcdefghijklmnopqrstuvwxyz ") for n in names)
    assert {"stack overflow", "memory out of bounds", "integer division by zero"} <= names


def test_the_kernel_identity_is_one_line() -> None:
    if IDENTITY is None:
        assert sys.platform not in ("linux", "darwin", "win32")
        return
    assert IDENTITY and "\n" not in IDENTITY and IDENTITY == IDENTITY.strip()
