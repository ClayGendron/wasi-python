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
    monkeypatch.setitem(runner._sweep_state, "failed", {})  # spec 084: failed sweeps per name
    monkeypatch.setattr(runner, "_warned", set(), raising=False)
    monkeypatch.setattr(runner, "_pending_warnings", [], raising=False)
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
    locks it: the creator draws another name instead of raising (build review, finding 1). On
    Windows the race cannot happen: the creator holds the file open from its creation, and an
    open file cannot be deleted, by a sweeper or by this check; there the check shows that, and
    that the creator keeps its first name."""
    real = runner._try_lock
    removed, kept = [], []

    def swept_first(fd):
        if not removed:
            (lock,) = temp.glob("*.lock")
            try:
                lock.unlink()
                removed.append(lock.name)
            except PermissionError:  # Windows: open, so no one can delete it
                removed.append(None)
                kept.append(lock.name)
        return real(fd)

    monkeypatch.setattr(runner, "_try_lock", swept_first)
    private = runner._Private("wasi-python-root-")
    try:
        assert private.path.is_dir()
        if removed[0] is None:
            assert os.name == "nt", "only Windows refuses to delete an open file"
            assert Path(private.lock_path).name == kept[0]  # its first name: no redraw
        else:
            assert Path(private.lock_path).name != removed[0]
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
    """Otherwise what is left is never swept (build review, finding 5). Since spec 084 the
    removal is `_remove_tree`, and a folder it leaves is named in one warning."""
    private = runner._Private("wasi-python-root-")
    (private.path / "file").write_text("guest data")
    with monkeypatch.context() as m, pytest.warns(RuntimeWarning, match=private.name):
        m.setattr(runner, "_remove_tree", lambda *a, **k: False)
        private.remove()
        runner._flush_warnings()
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


# A private root never outlives its call (spec 084). `_remove_tree` walks a tree holding at most
# two descriptors, changes no mode, and never follows a link; a folder it leaves keeps its lock
# file, is named in one warning, and re-arms the sweep. Each case counts entries, descriptors or
# calls, and times nothing. On POSIX the deep cases run in a child with three free descriptors;
# Windows has no RLIMIT_NOFILE, and there the trees' paths pass 260 characters instead.

WINDOWS = os.name == "nt"
COUNTED = ("open", "scandir", "unlink", "rmdir")
FORBIDDEN = ("chmod", "fchmod", "mkdir", "rename")


def long_path(path) -> str:
    """An extended-length path on Windows (`\\\\?\\`), the absolute path elsewhere."""
    p = os.path.abspath(path)
    return "\\\\?\\" + p if WINDOWS and not p.startswith("\\\\?\\") else p


def deep_tree(top: Path, depth: int, *, name: str = "a", link_at: int = -1, link_to=None) -> int:
    """`top`, `depth` levels deep with a file at each level; returns its entries below `top`.
    One level at a time: through dir_fd on POSIX (macOS's PATH_MAX is 1,024 bytes), through
    extended-length paths on Windows."""
    entries = 0
    if not WINDOWS:
        os.mkdir(top)
        fd = os.open(top, os.O_RDONLY | os.O_DIRECTORY)
        try:
            for i in range(depth):
                os.close(os.open("f", os.O_CREAT | os.O_WRONLY, 0o644, dir_fd=fd))
                if i == link_at:
                    os.symlink(link_to, "link", dir_fd=fd)
                    entries += 1
                os.mkdir(name, dir_fd=fd)
                below = os.open(name, os.O_RDONLY | os.O_DIRECTORY, dir_fd=fd)
                os.close(fd)
                fd = below
                entries += 2
        finally:
            os.close(fd)
        return entries
    here = long_path(top)
    os.mkdir(here)
    for i in range(depth):
        open(here + "\\f", "w").close()
        if i == link_at:
            os.symlink(link_to, here + "\\link", target_is_directory=True)
            entries += 1
        here += "\\" + name
        os.mkdir(here)
        entries += 2
    return entries


def counting(monkeypatch) -> dict[str, int]:
    """Counts the calls `_remove_tree` makes, by name; `_dir_fd_ok` is fixed first, since it
    asks whether os.mkdir is in os.supports_dir_fd."""
    ok = runner._dir_fd_ok()
    monkeypatch.setattr(runner, "_dir_fd_ok", lambda: ok)
    counts = dict.fromkeys(COUNTED + FORBIDDEN, 0)
    for n in counts:
        real = getattr(os, n, None)
        if real is not None:

            def wrap(*a, _real=real, _n=n, **k):
                counts[_n] += 1
                return _real(*a, **k)

            monkeypatch.setattr(os, n, wrap)
    return counts


THREE_FREE = r"""
import os, resource, sys, tempfile
from wasi_python import runner

action, path = sys.argv[1:3]
if action == "sweep":
    tempfile.tempdir = path


def is_open(fd):
    try:
        os.fstat(fd)
        return True
    except OSError:
        return False


held = {int(n) for n in os.listdir("/dev/fd")}
held = {fd for fd in held if is_open(fd)}
limit = next(n for n in range(1, 1 << 16) if n - len([fd for fd in held if fd < n]) == 3)
resource.setrlimit(resource.RLIMIT_NOFILE, (limit, resource.getrlimit(resource.RLIMIT_NOFILE)[1]))
if action == "remove":
    print(runner._remove_tree(path))
else:
    runner._sweep_once()
    print(runner._sweep_state["swept"])
"""


def three_free(action: str, path) -> str:
    """Runs `_remove_tree(path)` or a sweep of `path` in a child left exactly three free
    descriptor numbers below its soft limit, counting the holes."""
    import subprocess

    out = subprocess.run(
        [sys.executable, "-c", THREE_FREE, action, str(path)],
        capture_output=True,
        text=True,
        timeout=120,  # a fail-safe, never a verdict
    )
    assert out.returncode == 0, out.stderr[-1500:]
    return out.stdout.strip()


def flushed(recwarn) -> list[str]:
    runner._flush_warnings()
    return [str(w.message) for w in recwarn if issubclass(w.category, RuntimeWarning)]


def test_a_tree_deeper_than_the_descriptor_limit_is_removed(tmp_path, monkeypatch) -> None:
    """Criterion 4: a tree deeper than the free descriptors is removed, in at most 5 counted
    calls per entry plus 5, with no chmod, mkdir or rename."""
    depth = 300 if WINDOWS else 1000
    if not WINDOWS:
        deep_tree(tmp_path / "limited", depth)
        assert three_free("remove", tmp_path / "limited") == "True"
        assert not os.path.lexists(tmp_path / "limited")
    entries = deep_tree(tmp_path / "counted", depth)
    counts = counting(monkeypatch)
    assert runner._remove_tree(tmp_path / "counted") is True
    assert not os.path.lexists(long_path(tmp_path / "counted"))
    assert sum(counts[n] for n in COUNTED) <= 5 * entries + 5, counts
    assert all(counts[n] == 0 for n in FORBIDDEN), counts


@pytest.mark.skipif(WINDOWS, reason="on Windows the path walk is the walk: the case above")
def test_the_path_walk_removes_a_deep_tree(tmp_path, monkeypatch) -> None:
    """Criterion 5: the Windows walk, forced on POSIX with plain absolute paths."""
    canary = tmp_path / "canary"
    canary.mkdir()
    (canary / "keep").write_text("keep")
    deep_tree(tmp_path / "tree", 300, link_at=150, link_to=str(canary))
    monkeypatch.setattr(runner, "_dir_fd_ok", lambda: False)
    assert runner._remove_tree(tmp_path / "tree") is True
    assert not os.path.lexists(tmp_path / "tree")
    assert (canary / "keep").read_text() == "keep"


def can_link(tmp_path) -> bool:
    try:
        os.symlink(tmp_path, tmp_path / "probe-link", target_is_directory=True)
    except (OSError, NotImplementedError):
        return False
    os.unlink(tmp_path / "probe-link")
    return True


def test_the_removal_never_follows_a_link(tmp_path) -> None:
    """Criterion 6, the static links: to the canary folder, to its file, `../..`, a link at
    depth 50, and the top itself replaced by a link."""
    if not can_link(tmp_path):
        pytest.skip("this user cannot make links")
    canary = tmp_path / "canary"
    canary.mkdir()
    (canary / "keep").write_text("keep")
    deep_tree(tmp_path / "tree", 60, link_at=50, link_to=str(canary))
    os.symlink(canary, tmp_path / "tree" / "to-folder", target_is_directory=True)
    os.symlink(canary / "keep", tmp_path / "tree" / "to-file")
    os.symlink(os.path.join("..", ".."), tmp_path / "tree" / "up", target_is_directory=True)
    assert runner._remove_tree(tmp_path / "tree") is True
    assert not os.path.lexists(tmp_path / "tree")
    os.symlink(canary, tmp_path / "top", target_is_directory=True)
    assert runner._remove_tree(tmp_path / "top") is True
    assert not os.path.lexists(tmp_path / "top")
    assert sorted(os.listdir(canary)) == ["keep"] and (canary / "keep").read_text() == "keep"


CHAIN = 8  # throwaway levels above the tree: more than the walk's deepest stack in these cases


def tree_with_canary(tmp_path) -> tuple[Path, Path]:
    """The review's shape: tree/ six levels deep, a file at each, and outside/keep beside it,
    both under CHAIN throwaway levels inside tmp_path, each holding a file `chain`. A walk that
    climbed out (the identity check missing) then fails `chain_intact` and stays inside tmp_path,
    never reaching the session's other folders (the build review, B1)."""
    base = tmp_path
    for i in range(CHAIN):
        base = base / f"c{i}"
        base.mkdir()
        (base / "chain").write_text("chain")
    (base / "outside").mkdir()
    (base / "outside" / "keep").write_text("keep")
    deep_tree(base / "tree", 6)
    return base / "tree", base / "outside"


def chain_intact(tmp_path) -> bool:
    """Every throwaway level and its `chain` file is still there."""
    base = tmp_path
    for i in range(CHAIN):
        base = base / f"c{i}"
        if not (base / "chain").is_file():
            return False
    return True


def hooked_open(monkeypatch, before=None, after=None) -> None:
    real = os.open

    def opener(path, flags, mode=0o777, *, dir_fd=None):
        if before is not None:
            before(path, dir_fd)
        fd = real(path, flags, mode, dir_fd=dir_fd)
        if after is not None:
            after(path, dir_fd)
        return fd

    monkeypatch.setattr(os, "open", opener)


def at_level(tree: Path, level: int):
    """A hook test: whether `dir_fd` is the tree's folder at `level` (0 is the top)."""
    folder = tree.joinpath(*["a"] * level)

    def test(path, dir_fd) -> bool:
        if path != "a" or dir_fd is None or not folder.is_dir():
            return False
        return os.path.samestat(os.fstat(dir_fd), os.stat(folder))

    return test


@pytest.mark.skipif(WINDOWS, reason="a hook on os.open with dir_fd: the POSIX walk")
def test_a_folder_swapped_for_a_link_mid_walk_is_left(tmp_path, monkeypatch) -> None:
    """Criterion 6, the swap (the review's attack B): level 3 moved aside and a link to the
    canary put in its place as the walk is about to open it. The link is left and the removal
    returns False; the canary is kept."""
    tree, outside = tree_with_canary(tmp_path)
    in_level_2, done = at_level(tree, 2), []

    def swap(path, dir_fd):
        if not done and in_level_2(path, dir_fd):
            level_3 = tree / "a" / "a" / "a"
            os.rename(level_3, tree.parent / "parked")
            os.symlink(outside, level_3)
            done.append(1)

    hooked_open(monkeypatch, before=swap)
    assert runner._remove_tree(tree) is False
    monkeypatch.undo()
    assert done and (tree / "a" / "a" / "a").is_symlink()
    assert sorted(os.listdir(outside)) == ["keep"] and chain_intact(tmp_path)


@pytest.mark.skipif(WINDOWS, reason="the climb by `..` and its identity check: the POSIX walk")
@pytest.mark.parametrize("attack", ["moved-out", "renamed-up", "parent-moved-out"])
def test_the_walk_never_climbs_out_of_a_moved_folder(tmp_path, monkeypatch, attack) -> None:
    """Criterion 7 (the review's F2): a folder moved during the walk, by a hook at an exact step.
    The climb's identity check stops the walk: it returns False and the canary is kept. Without
    the check the walk climbs out and empties it."""
    tree, outside = tree_with_canary(tmp_path)
    in_level_3, done = at_level(tree, 3), []
    level_3 = tree / "a" / "a" / "a"

    def move(path, dir_fd):
        if done or not in_level_3(path, dir_fd):
            return
        if attack == "moved-out":  # level 4, just after the walk opened it
            os.rename(level_3 / "a", outside / "moved")
        elif attack == "renamed-up":  # level 4 to the top, just after the walk opened it
            os.rename(level_3 / "a", tree / "up")
        else:  # level 3 out, while the walk is in level 4
            os.rename(level_3, outside / "lvl3")
        done.append(1)

    hooked_open(monkeypatch, after=move)
    assert runner._remove_tree(tree) is False
    monkeypatch.undo()
    assert done and chain_intact(tmp_path)
    assert (outside / "keep").read_text() == "keep"


@pytest.mark.skipif(POSIX and os.geteuid() == 0, reason="modes refuse nothing to root")
def test_read_only_content_is_left_and_named(temp, recwarn) -> None:
    """Criterion 8: the removal changes no mode or attribute. Read-only content is left with its
    modes, and the folder named; an empty folder it cannot open goes by rmdir (N1)."""
    private = runner._Private("wasi-python-root-")
    top = private.path
    if WINDOWS:
        (top / "ro").mkdir()
        (top / "ro" / "secret").write_text("x")
        os.chmod(top / "ro" / "secret", stat.S_IREAD)
        guarded = [top / "ro" / "secret"]
    else:
        for folder, mode in (("ro", 0o500), ("none", 0o000), ("empty", 0o000)):
            (top / folder).mkdir()
            if folder != "empty":
                (top / folder / "secret").write_text("x")
            os.chmod(top / folder, mode)
        guarded = [top / "ro", top / "none"]
    modes = [os.lstat(p).st_mode for p in guarded]
    try:
        assert runner._remove_tree(top) is False
        assert [os.lstat(p).st_mode for p in guarded] == modes
        assert not os.path.lexists(top / "empty")
        private.remove()
        assert names(temp) == sorted([private.name, f"{private.name}.lock"])
        seen = flushed(recwarn)
        assert len(seen) == 1 and str(top) in seen[0], seen
    finally:
        for p in guarded:
            os.chmod(p, stat.S_IWRITE | stat.S_IREAD if WINDOWS else 0o700)
        shutil.rmtree(top, ignore_errors=True)


def writer(monkeypatch, folder: Path, cap: int) -> list[int]:
    """A hook on os.unlink that adds a file to `folder` after each unlink, up to `cap` files."""
    real, added = os.unlink, [0]

    def unlink(path, *, dir_fd=None):
        real(path, dir_fd=dir_fd)
        if added[0] < cap:
            added[0] += 1
            (folder / f"w{added[0]}").write_bytes(b"")

    monkeypatch.setattr(os, "unlink", unlink)
    return added


def fresh_home(tmp_path: Path) -> tuple[str, Path, int | None]:
    tmp = tmp_path / "root" / "tmp"
    (tmp / ".home-0123" / "d").mkdir(parents=True)
    (tmp / ".home-0123" / "d" / "f0").write_bytes(b"")
    fd = None if WINDOWS else os.open(tmp, os.O_RDONLY | os.O_DIRECTORY)
    return ".home-0123", tmp, fd


def test_a_writer_cannot_keep_a_home_removal_going(temp, tmp_path, monkeypatch, recwarn) -> None:
    """Criterion 9 (the review's F3 and C1): a HOME's removal has a budget of calls, so a
    concurrent writer cannot keep it going; a private folder has none."""
    with monkeypatch.context() as m:
        m.setattr(runner, "_REMOVE_BUDGET", 10_000, raising=False)
        home = fresh_home(tmp_path)
        added = writer(m, home[1] / home[0] / "d", 50_000)
        counts = counting(m)
        runner._remove_home(home)
    assert os.path.lexists(home[1] / home[0]), added
    assert sum(counts[n] for n in COUNTED) <= 10_000, counts
    seen = flushed(recwarn)
    assert len(seen) == 1 and home[0] in seen[0], seen
    recwarn.clear()
    shutil.rmtree(tmp_path / "root")
    # the default budget, the writer stopped at 2,000 files: the HOME is gone
    with monkeypatch.context() as m:
        home = fresh_home(tmp_path)
        writer(m, home[1] / home[0] / "d", 2_000)
        runner._remove_home(home)
    assert not os.path.lexists(home[1] / home[0])
    # a private folder has no budget: 12,000 files, the budget patched to 10,000, no writer
    with monkeypatch.context() as m:
        m.setattr(runner, "_REMOVE_BUDGET", 10_000, raising=False)
        private = runner._Private("wasi-python-root-")
        for i in range(12_000):
            (private.path / f"f{i}").write_bytes(b"")
        counts = counting(m)
        private.remove()
    assert names(temp) == [] and sum(counts[n] for n in COUNTED) > 10_000, counts
    assert flushed(recwarn) == []


def failing_once(monkeypatch) -> list[str]:
    calls, real = [], runner._remove_tree

    def remove_tree(path, **k):
        calls.append(os.path.basename(os.fspath(path)))
        return False if len(calls) == 1 else real(path, **k)

    monkeypatch.setattr(runner, "_remove_tree", remove_tree)
    return calls


def test_what_a_removal_leaves_is_retried_by_the_next_calls_sweep(temp, monkeypatch, recwarn):
    """Criterion 10: a folder left keeps its lock file, is named once, and re-arms the sweep,
    after its name is dropped; the next sweep removes it."""
    failing_once(monkeypatch)
    monkeypatch.setitem(runner._sweep_state, "claimed", True)  # this process's first call is past
    private = runner._Private("wasi-python-root-")
    (private.path / "file").write_text("guest data")
    private.remove()
    assert names(temp) == sorted([private.name, f"{private.name}.lock"])
    assert private.name not in runner._held
    seen = flushed(recwarn)
    assert len(seen) == 1 and private.name in seen[0], seen
    assert runner._sweep_state["claimed"] is False
    assert sweep() == 1 and names(temp) == []


def test_the_name_is_dropped_before_the_sweep_is_re_armed(temp, monkeypatch) -> None:
    """Criterion 10 (the review's F6): a sweep that runs between the drop and the re-arm cannot
    spend the retry; one run just before the drop (another thread's, say) skips the held name,
    and the next sweep still removes the folder."""
    failing_once(monkeypatch)
    real_drop = runner._drop

    def drop(name):
        runner._sweep_once()  # sees the name still held
        real_drop(name)

    monkeypatch.setattr(runner, "_drop", drop)
    private = runner._Private("wasi-python-root-")
    (private.path / "file").write_text("guest data")
    private.remove()
    monkeypatch.setattr(runner, "_drop", real_drop)
    assert sweep() == 1 and names(temp) == []


def test_a_folder_is_retried_by_at_most_three_sweeps(temp, monkeypatch) -> None:
    """Criterion 10, the bound: its own removal and three sweeps, then left to the next process;
    and a sweep re-arms only after its loop."""
    calls, claimed = [], []

    def remove_tree(path, **k):
        calls.append(os.path.basename(os.fspath(path)))
        claimed.append(runner._sweep_state["claimed"])
        return False

    monkeypatch.setattr(runner, "_remove_tree", remove_tree)
    private = runner._Private("wasi-python-root-")
    other = dead(temp, "wasi-python-root-fedcba9876543210")
    private.remove()
    claimed.clear()
    for _ in range(6):
        runner._sweep_once()
    assert calls.count(private.name) == 4 and calls.count(other.name) == 3, calls
    assert runner._sweep_state["claimed"] is True
    assert all(claimed), claimed  # never re-armed from inside a sweep's loop


def test_a_deep_dead_root_is_swept(temp) -> None:
    """Criterion 11: the sweep removes a dead root deeper than its free descriptors."""
    folder = dead(temp)
    deep_tree(folder / "deep", 300 if WINDOWS else 1000)
    if WINDOWS:
        assert sweep() == 1
    else:
        assert three_free("sweep", temp) == "1"
    assert names(temp) == []


def test_a_removal_that_raises_still_lets_go(temp, monkeypatch) -> None:
    """Criterion 12: a removal that fails as no one foresaw (3.11's RecursionError was one)
    leaves the folder with its lock free and the name dropped, never held."""

    def remove_tree(*a, **k):
        raise RecursionError("maximum recursion depth exceeded")

    monkeypatch.setattr(runner, "_remove_tree", remove_tree)
    private = runner._Private("wasi-python-root-")
    private.remove()
    assert private.name not in runner._held
    assert names(temp) == sorted([private.name, f"{private.name}.lock"])
    fd = os.open(private.lock_path, os.O_RDWR | getattr(os, "O_BINARY", 0))
    try:
        assert runner._try_lock(fd) is True
    finally:
        runner._unlock_close(fd)


def test_a_warning_filter_never_makes_the_call_raise(temp, monkeypatch) -> None:
    """Criterion 13: under a filter that turns warnings into errors, neither the removal nor the
    flush raises; the folder is kept for the sweep."""
    import warnings

    monkeypatch.setattr(runner, "_remove_tree", lambda *a, **k: False)
    private = runner._Private("wasi-python-root-")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        private.remove()
        runner._flush_warnings()
    assert names(temp) == sorted([private.name, f"{private.name}.lock"])


def test_the_warning_is_given_outside_every_runner_lock(temp, monkeypatch) -> None:
    """Criterion 14 (the review's F6): a removal under the zip folder's lock queues its warning;
    the flush gives it with no runner lock held, so an embedder's handler may call stats()."""
    import warnings

    import wasi_python

    record = []

    def show(message, category, *a, **k):
        free = []
        for lock in (runner._lock, runner._zip_lock, runner._held_lock):
            free.append(lock.acquire(blocking=False))
            if free[-1]:
                lock.release()
        record.append((str(message), free, sorted(wasi_python.stats())))

    monkeypatch.setattr(runner, "_remove_tree", lambda *a, **k: False)
    private = runner._Private("wasi-python-zip-")
    with warnings.catch_warnings():
        warnings.simplefilter("always")
        warnings.showwarning = show
        with runner._zip_lock:  # as `_zip_folder` holds it when it makes a folder again
            private.remove()
        assert record == []
        runner._flush_warnings()
    assert len(record) == 1 and private.name in record[0][0], record
    assert record[0][1] == [True, True, True] and "compiled" in record[0][2]
