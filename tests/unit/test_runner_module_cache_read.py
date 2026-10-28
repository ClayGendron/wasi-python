"""The compiled module wasmtime loads is the file the runner checked, and a cache on a way
another user could change is not used.

A `.cwasm` is native code that wasmtime runs as it finds it. On POSIX the runner opens the
cache folder and the file by descriptor, checks what it opened, and hands wasmtime that
descriptor's name, so a file swapped in at the path after the check is never what is loaded.
Every folder on the way to the cache must be this user's, root's or, on `/`'s own device, the
owner of `/`'s, and closed to other writers (a sticky folder such as `/tmp` aside), as `sshd`
asks of the way to a key, or the cache is not used, with a warning, and the call still runs.
A folder or file with an access list is not used either, nor, on macOS, a cache whose way
holds a folder with an access list that lets anyone else change it. On Windows the file is held
open from its check to its load. A module is compiled from the bytes it was hashed from, so a
`.cwasm` under a digest holds that digest's code. An empty `cache_dir` is refused, and a
relative one is the folder it names when the call is made.

Each verdict is a count from `stats()`, a module's exports, a warning or a refusal; the stand-ins
are parameters of the functions they stand in for, the process object's observers, or the
platform object's own methods."""

from __future__ import annotations

import asyncio
import errno
import hashlib
import inspect
import os
import shutil
import stat
import subprocess
import sys
import types
import warnings
import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest
import wasmtime as wt

import wasi_python
from harness import wat
from wasi_python import ArtifactsMissing, _artifacts, _engines, _platform, runner
from wasi_python import _wasmtime_ffi as ffi
from wasi_python._process import process

POSIX = os.name == "posix"
NOT_POSIX = "a POSIX descriptor rule; Windows holds the file open instead"
PLANTED = '(module (func (export "planted")))'


def _tiny(work: Path) -> tuple[Path, str]:
    binary = work / "tiny.wasm"
    binary.write_bytes(wt.wat2wasm("(module)"))
    return binary, hashlib.sha256(str(work).encode()).hexdigest()  # a digest of this test's own


def _name(digest: str) -> str:
    return f"{digest[:32]}-wasmtime{ffi.version()}-plain.cwasm"


def _serialized(text: str = "(module)") -> bytes:
    return wt.Module(_engines._engine(False), text).serialize()


def _cached(cache: Path, digest: str, text: str = "(module)") -> Path:
    """A cache folder at 0700 holding the runner's own kind of `.cwasm`, at 0600."""
    cache.mkdir(mode=0o700, exist_ok=True)
    cwasm = cache / _name(digest)
    cwasm.write_bytes(_serialized(text))
    cwasm.chmod(0o600)
    return cwasm


def _miss(
    binary: Path, cache: Path, digest: str, stand_in: object = wt, **seams: object
) -> tuple[dict[str, int], list[str], wt.Module]:
    """One cache miss for the module named `digest`: the counts it moved, its warnings and the
    module it returned."""
    before = dict(process().counts)
    with warnings.catch_warnings(record=True) as seen:
        warnings.simplefilter("always")
        engine = _engines._engine(False)
        mod = _engines._module_miss(
            stand_in, engine, False, binary, cache, digest, held=None, **seams
        )
    counts = {k: process().counts[k] - before[k] for k in ("compiled", "loaded", "written")}
    return counts, [str(w.message) for w in seen], mod


def _exports(mod: wt.Module) -> list[str]:
    return [e.name for e in mod.exports]


# Row 1: the swap inside the load.


@pytest.mark.skipif(not POSIX, reason=NOT_POSIX)
def test_a_swap_inside_the_load_cannot_reach_wasmtime(work) -> None:
    """A stand-in for wasmtime-py, inside its load, moves the checked file aside, puts a 0644
    module that exports `planted` at its name, loads, and puts the original back, so the name's
    stamp after the load is the one checked. By path that loads the planted module and the
    stamp re-check passes; through the checked descriptor's name the checked file is loaded."""
    binary, digest = _tiny(work)
    cwasm = _cached(work / "cache", digest)
    planted, aside = work / "planted.cwasm", work / "aside.cwasm"
    planted.write_bytes(_serialized(PLANTED))
    planted.chmod(0o644)
    given: list[str] = []

    class Module(wt.Module):
        @classmethod
        def deserialize_file(cls, engine, path):
            given.append(path)
            os.rename(cwasm, aside)
            os.rename(planted, cwasm)
            try:
                return wt.Module.deserialize_file(engine, path)
            finally:
                os.rename(cwasm, planted)
                os.rename(aside, cwasm)

    stand_in = types.SimpleNamespace(Module=Module, WasmtimeError=wt.WasmtimeError)
    counts, _, mod = _miss(binary, work / "cache", digest, stand_in)
    assert _exports(mod) == [], f"the module swapped in was loaded, through {given}"
    assert given and given[0].startswith(("/dev/fd/", "/proc/self/fd/")), given
    assert counts == {"compiled": 0, "loaded": 1, "written": 0}, counts


@pytest.mark.skipif(not POSIX, reason=NOT_POSIX)
def test_where_a_descriptor_has_no_name_the_cache_still_loads_by_path(work) -> None:
    """Where the system cannot open `/dev/fd/N` (no `/proc` in a sandbox or chroot), the
    runner's own open of that name fails first: an existing `.cwasm` loads by path, with the
    stamp re-check, and is never compiled again or rewritten for that reason."""
    binary, digest = _tiny(work)
    cwasm = _cached(work / "cache", digest)
    inode = cwasm.stat().st_ino
    tried: list[str] = []

    def no_names(name: str, flags: int, *args: object, **kwargs: object) -> int:
        tried.append(name)
        raise OSError(errno.ENOENT, "no descriptor names here", name)

    counts, seen, mod = _miss(binary, work / "cache", digest, reopen=no_names)
    assert counts == {"compiled": 0, "loaded": 1, "written": 0}, (counts, seen)
    assert tried and _exports(mod) == []
    assert cwasm.stat().st_ino == inode, "the .cwasm was rewritten"


@pytest.mark.skipif(POSIX, reason="the held handle is Windows's; POSIX loads by descriptor")
def test_on_windows_the_cwasm_is_held_open_from_its_check_to_its_load(work) -> None:
    """Windows has no descriptor name wasmtime can open, so the runner holds a read handle of
    the `.cwasm` from its check until the load returns: a replacement of that name inside the
    load is refused, and the checked file is the one loaded."""
    binary, digest = _tiny(work)
    cwasm = _cached(work / "cache", digest)
    planted = work / "planted.cwasm"
    planted.write_bytes(_serialized(PLANTED))
    refused: list[OSError] = []

    class Module(wt.Module):
        @classmethod
        def deserialize_file(cls, engine, path):
            try:
                os.replace(planted, cwasm)
            except PermissionError as e:
                refused.append(e)
            return wt.Module.deserialize_file(engine, path)

    stand_in = types.SimpleNamespace(Module=Module, WasmtimeError=wt.WasmtimeError)
    counts, _, mod = _miss(binary, work / "cache", digest, stand_in)
    assert refused, "the .cwasm was replaced while the runner held it"
    assert _exports(mod) == []
    assert counts == {"compiled": 0, "loaded": 1, "written": 0}, counts


# Row 2: the way to the cache.


@pytest.mark.skipif(not POSIX, reason="Windows has no ancestor rule; the grant rule guards it")
@pytest.mark.parametrize(
    ("mode", "owner", "used"),
    [
        (0o777, "this user", False),
        (0o755, "another user", False),
        (0o1777, "this user", True),
        (0o1777, "another user", False),
    ],
)
def test_an_ancestor_another_user_owns_or_can_write_is_not_used(work, mode, owner, used) -> None:
    """The folder above the cache is a real folder at `mode`. World-writable without the sticky
    bit, whoever owns it, anyone could rename the cache folder away; a sticky folder of this
    user's, like root's `/tmp`, lets no one else rename an entry; one another user owns, sticky
    or not, its owner can. Only the owner is a stand-in, through the walk's `lstat`. `/`, root's
    at 0755, is on the way of every case. A cache not used compiles in memory and writes
    nothing, with one warning that names the folder."""
    binary, digest = _tiny(work)
    above = work / "above"
    above.mkdir()
    above.chmod(mode)
    other = os.getuid() + 1
    real_above = os.path.realpath(above)

    def lstat(path: str) -> object:
        st = os.lstat(path)
        if owner == "another user" and os.path.realpath(path) == real_above:
            return types.SimpleNamespace(st_mode=st.st_mode, st_uid=other)
        return st

    seams = {"lstat": lstat} if owner == "another user" else {}
    try:
        counts, seen, _ = _miss(binary, above / "cache", digest, **seams)
    finally:
        above.chmod(0o755)
    if used:
        assert counts == {"compiled": 1, "loaded": 0, "written": 1}, (counts, seen)
        assert seen == []
        return
    assert counts == {"compiled": 1, "loaded": 0, "written": 0}, (counts, seen)
    assert len(seen) == 1 and real_above in seen[0], seen
    assert not (above / "cache").exists() or list((above / "cache").iterdir()) == []


# The way's owners: root, this user, and the owner of `/` on its own file system.

WALK_SKIP = "Windows has no ancestor rule; the grant rule guards it"
ROOT_ADVICE = (
    "no folder can hold the cache while it is, so have its owner run chmod go-w /, or pass "
    "cache_dir=False to compile in memory without this warning"
)
FOLDER_ADVICE = "set $WASI_PYTHON_CACHE to a folder of yours"
OVERFLOW = 65534  # the kernel's default overflow uid: an owner a user namespace does not map


def _other() -> int:
    """A uid that is not this process's, nor root's, nor the overflow uid, and whose successor
    is none of them either: the owner of `/` on a container host that maps its own ids."""
    uid = 2346
    while os.geteuid() in (uid, uid + 1):
        uid += 2
    return uid


def _seen_as(changes: dict[Path | str, dict[str, int]]) -> Callable[[str], object]:
    """The walk's `lstat`, reporting the named folders with some fields changed (an owner, a
    mode, a device) and every other folder as it is."""
    changed = {os.path.realpath(k): v for k, v in changes.items()}

    def lstat(path: str) -> object:
        st = os.lstat(path)
        fields = {"st_mode": st.st_mode, "st_uid": st.st_uid, "st_dev": st.st_dev}
        fields.update(changed.get(path, {}))
        return types.SimpleNamespace(**fields)

    return lstat


def _above(work: Path, mode: int = 0o755) -> Path:
    """The folder that holds the cache, a real folder at `mode` (set after the `mkdir`, whose
    mode the umask masks)."""
    above = work / "above"
    above.mkdir()
    above.chmod(mode)
    return above


def _not_used(counts: dict[str, int], seen: list[str], where: Path | str, why: str) -> str:
    """The cache was not used: compiled in memory, nothing written, one warning that names the
    folder that failed and why. The warning, for the caller to read further."""
    assert counts == {"compiled": 1, "loaded": 0, "written": 0}, (counts, seen)
    assert len(seen) == 1, seen
    assert f"{os.path.realpath(where)}, on the way to it, {why}" in seen[0], seen
    return seen[0]


def _used(counts: dict[str, int], seen: list[str]) -> None:
    assert counts == {"compiled": 1, "loaded": 0, "written": 1}, (counts, seen)
    assert seen == []


@pytest.mark.skipif(not POSIX, reason=WALK_SKIP)
@pytest.mark.parametrize("case", ["root", "root-and-above", "above-another", "above-elsewhere"])
def test_the_owner_of_root_is_trusted_on_the_way_as_root_is(work, case) -> None:
    """`/` belongs to a uid of its own, as on a container host that maps ids. Whoever owns `/`
    can already rename every folder on its file system, so the cache under `/` is used, and so
    is one under a folder of that owner's on `/`'s device. A folder another uid owns is refused
    as before, and so is a folder of `/`'s owner on another device: past a mount point that
    owner cannot rename the way, so owning a folder there is owning it, nothing more."""
    binary, digest = _tiny(work)
    above = _above(work)
    owner, device = _other(), os.lstat("/").st_dev
    changes: dict[Path | str, dict[str, int]] = {"/": {"st_uid": owner}}
    if case == "root-and-above":
        changes[above] = {"st_uid": owner, "st_dev": device}
    elif case == "above-another":
        changes[above] = {"st_uid": owner + 1, "st_dev": device}
    elif case == "above-elsewhere":
        changes[above] = {"st_uid": owner, "st_dev": device + 1}
    counts, seen, _ = _miss(binary, above / "cache", digest, lstat=_seen_as(changes))
    if case in ("root", "root-and-above"):
        _used(counts, seen)
        return
    uid = owner + 1 if case == "above-another" else owner
    _not_used(counts, seen, above, f"is another user's (uid {uid})")


@pytest.mark.skipif(not POSIX, reason=WALK_SKIP)
@pytest.mark.parametrize(
    ("mode", "owner", "used"),
    [
        (0o777, "other", False),
        (0o775, "other", False),
        (0o1777, "other", True),
        (0o777, "root", False),
    ],
    ids=["0777-other", "0775-other", "1777-other", "0777-root"],
)
def test_a_root_others_may_write_still_refuses(work, mode, owner, used) -> None:
    """The mode rule holds for `/` as for every folder, whoever owns it: one its group or anyone
    may write, without the sticky bit, is refused for its mode; a sticky one passes, as `/tmp`
    does, since no one else may rename what is in it."""
    binary, digest = _tiny(work)
    uid = _other() if owner == "other" else 0
    changes = {"/": {"st_mode": stat.S_IFDIR | mode, "st_uid": uid}}
    counts, seen, _ = _miss(binary, work / "cache", digest, lstat=_seen_as(changes))
    if used:
        _used(counts, seen)
        return
    _not_used(counts, seen, "/", f"may be written by others (mode {mode:o}) and is not sticky")


@pytest.mark.skipif(not POSIX, reason=WALK_SKIP)
@pytest.mark.parametrize("failing", ["root", "above"])
def test_when_root_fails_the_warning_says_no_folder_can_hold_the_cache(work, failing) -> None:
    """Every cache folder is below `/`, so when `/` is what fails, another folder cannot help:
    the warning says to close `/` or to keep no cache. A folder below `/` that fails still says
    to choose a folder of yours."""
    binary, digest = _tiny(work)
    above = _above(work, 0o755 if failing == "root" else 0o777)
    try:
        if failing == "root":
            changes = {"/": {"st_mode": stat.S_IFDIR | 0o777, "st_uid": 0}}
            counts, seen, _ = _miss(binary, above / "cache", digest, lstat=_seen_as(changes))
        else:
            counts, seen, _ = _miss(binary, above / "cache", digest)
    finally:
        above.chmod(0o755)
    where = "/" if failing == "root" else above
    warned = _not_used(counts, seen, where, "may be written by others (mode 777)")
    if failing == "root":
        assert warned.endswith(ROOT_ADVICE), warned
        assert "$WASI_PYTHON_CACHE" not in warned, warned
    else:
        assert warned.endswith(FOLDER_ADVICE), warned


@pytest.mark.skipif(not POSIX, reason=WALK_SKIP)
@pytest.mark.parametrize("above_too", [False, True])
def test_an_overflow_owner_of_root_is_trusted_on_root_alone(work, above_too) -> None:
    """A `/` whose owner a user namespace does not map shows the overflow uid. No one in the
    namespace has its owner's rights, so `/` passes; but below `/` the same number is also the
    namespace's own `nobody`, so a folder showing it is another user's, as before."""
    if os.geteuid() == OVERFLOW:
        pytest.skip("this process runs as the overflow uid")
    binary, digest = _tiny(work)
    above = _above(work)
    changes: dict[Path | str, dict[str, int]] = {"/": {"st_uid": OVERFLOW}}
    if above_too:
        changes[above] = {"st_uid": OVERFLOW, "st_dev": os.lstat("/").st_dev}
    counts, seen, _ = _miss(binary, above / "cache", digest, lstat=_seen_as(changes))
    if not above_too:
        _used(counts, seen)
        return
    _not_used(counts, seen, above, f"is another user's (uid {OVERFLOW})")


def _owned_by_another(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    """The observers' owner for `path`'s inode is another uid; every other file keeps its own."""
    st = os.lstat(path)
    mine = (st.st_dev, st.st_ino)
    monkeypatch.setattr(
        process().observers,
        "owner_of",
        lambda s: os.geteuid() + 1 if (s.st_dev, s.st_ino) == mine else s.st_uid,
    )


@pytest.mark.skipif(not POSIX, reason=WALK_SKIP)
@pytest.mark.parametrize("whose", ["above", "folder", "cwasm"])
def test_the_cache_asks_the_one_owner_test(work, monkeypatch, whose) -> None:
    """The cache's owner test is the one the runner's other folders pass: the effective uid,
    the one a made file is owned by, compared with the owner the observers may stand in for.
    A folder on the way that another uid owns is refused; a cache folder or a `.cwasm` that
    another uid owns is not used, and the `.cwasm` is compiled around and replaced."""
    binary, digest = _tiny(work)
    above = _above(work)
    cache = above / "cache"
    cwasm = _cached(cache, digest) if whose == "cwasm" else None
    if whose == "folder":
        cache.mkdir(mode=0o700)
    _owned_by_another(monkeypatch, {"above": above, "folder": cache, "cwasm": cwasm}[whose])
    counts, seen, _ = _miss(binary, cache, digest)
    if whose == "above":
        _not_used(counts, seen, above, f"is another user's (uid {os.geteuid() + 1})")
    elif whose == "folder":
        assert counts == {"compiled": 1, "loaded": 0, "written": 0}, (counts, seen)
        assert len(seen) == 1 and "must be a directory owned by this user" in seen[0], seen
    else:
        assert counts == {"compiled": 1, "loaded": 0, "written": 1}, (counts, seen)
        assert len(seen) == 1 and "must be a file owned by this user" in seen[0], seen


@pytest.mark.skipif(not POSIX, reason=WALK_SKIP)
def test_a_folder_made_on_the_way_after_the_walk_is_judged(work) -> None:
    """The folder that would hold the cache is missing when the way is walked; another user
    makes it, open to all, before the runner's `mkdir`, which finds it there. It is judged as a
    folder found on the way is: refused for its mode, and the cache not used."""
    binary, digest = _tiny(work)
    made = work / "made"
    target = os.path.realpath(made)
    looked: list[str] = []

    def lstat(path: str) -> os.stat_result:
        if path == target and not looked:
            looked.append(path)
            made.mkdir()
            made.chmod(0o777)  # a `mkdir`'s mode is masked by the umask
            raise FileNotFoundError(errno.ENOENT, "not there yet", path)
        return os.lstat(path)

    try:
        counts, seen, _ = _miss(binary, made / "cache", digest, lstat=lstat)
    finally:
        if made.exists():
            made.chmod(0o755)
    assert looked, "the walk never looked at the missing folder"
    _not_used(counts, seen, made, "may be written by others (mode 777) and is not sticky")


def test_module_miss_requires_held() -> None:
    """What the digest of a module is (the set's checked digest, the binary's hash, or a key the
    caller names) is said at every call: a caller that forgot it would compile what it reads
    without comparing it with the digest it files the module under."""
    held = inspect.signature(_engines._module_miss).parameters["held"]
    assert held.default is inspect.Parameter.empty, held


# Row 3: access lists.


def _access_list(path: Path, kind: str) -> None:
    """An access list on `path`: on macOS by `chmod +a`, on Linux by `setfacl`, each leaving the
    mode bits as they were; the check is skipped, with its reason, where neither can."""
    if sys.platform == "darwin":
        entry = {
            "grants": "everyone allow write",
            "inherits": "everyone allow read,file_inherit,directory_inherit,only_inherit",
        }[kind]
        command = ["chmod", "+a", entry, str(path)]
    elif sys.platform.startswith("linux"):
        if shutil.which("setfacl") is None:
            pytest.skip("setfacl is not installed on this host")
        command = ["setfacl", *({"grants": ["-m"], "inherits": ["-d", "-m"]}[kind])]
        command += ["u:nobody:---", str(path)]
    else:
        pytest.skip("access lists are read on macOS and Linux")
    done = subprocess.run(command, capture_output=True, text=True)
    if done.returncode != 0:
        pytest.skip(f"this file system takes no access list: {done.stderr.strip()}")


@pytest.mark.skipif(not POSIX, reason="Windows access lists are not read")
def test_a_cache_folder_with_an_access_list_is_not_used(work) -> None:
    binary, digest = _tiny(work)
    cache = work / "cache"
    _cached(cache, digest)
    _access_list(cache, "grants")
    assert stat.S_IMODE(cache.stat().st_mode) == 0o700  # the mode bits alone pass
    counts, seen, _ = _miss(binary, cache, digest)
    assert counts == {"compiled": 1, "loaded": 0, "written": 0}, (counts, seen)
    assert any("not using the module cache" in m and str(cache) in m for m in seen), seen


@pytest.mark.skipif(not POSIX, reason="Windows access lists are not read")
def test_a_cwasm_with_an_access_list_is_compiled_around_and_replaced(work) -> None:
    binary, digest = _tiny(work)
    cache = work / "cache"
    cwasm = _cached(cache, digest)
    _access_list(cwasm, "grants")
    assert stat.S_IMODE(cwasm.stat().st_mode) == 0o600
    counts, seen, _ = _miss(binary, cache, digest)
    assert counts == {"compiled": 1, "loaded": 0, "written": 1}, (counts, seen)
    counts, seen, _ = _miss(binary, cache, digest)  # the runner's own file, with no list
    assert counts == {"compiled": 0, "loaded": 1, "written": 0}, (counts, seen)


@pytest.mark.skipif(not POSIX, reason="Windows access lists are not read")
def test_a_cache_folder_whose_list_only_inherits_is_not_used_and_not_written(work) -> None:
    """A list that applies only to what is made inside would give every new `.cwasm` a list the
    next process refuses: the folder is not used, so nothing is written into it."""
    binary, digest = _tiny(work)
    cache = work / "cache"
    cache.mkdir(mode=0o700)
    _access_list(cache, "inherits")
    counts, seen, _ = _miss(binary, cache, digest)
    assert counts == {"compiled": 1, "loaded": 0, "written": 0}, (counts, seen)
    assert list(cache.iterdir()) == []


# The access lists on the way: what the mode bits do not show.

MACOS = sys.platform == "darwin"
MACOS_ONLY = "macOS keeps access lists the mode bits do not show"
LINUX_ONLY = "the mask rule is Linux's"
# macOS's rights (sys/acl.h), by the names `chmod +a` takes for a folder.
RIGHTS = {
    "add_file": 1 << 2,
    "add_subdirectory": 1 << 5,
    "delete_child": 1 << 6,
    "delete": 1 << 4,
    "writesecurity": 1 << 12,
    "chown": 1 << 13,
}
ALL_SIX = sum(RIGHTS.values())
# The kernel's generic write bit (sys/kauth.h), which grants every right above but chown.
GENERIC_WRITE = 1 << 23
# list, search, readattr, writeattr, readextattr, writeextattr, readsecurity, synchronize.
CHANGE_NOTHING = (1 << 1) | (1 << 3) | (1 << 7) | (1 << 8) | (1 << 9) | (1 << 10) | (1 << 11)
CHANGE_NOTHING |= 1 << 20
EVERYONE = 12  # macOS's gid for the group everyone
ROOT_LIST_ADVICE = (
    "no folder can hold the cache while it is, so pass cache_dir=False to compile in memory "
    "without this warning"
)
ENTRY_ADVICE = "remove that entry with chmod -a, or set $WASI_PYTHON_CACHE to a folder of yours"


def _listed(
    monkeypatch: pytest.MonkeyPatch,
    folder: Path | str,
    *entries: tuple[bool, str, int, int, bool],
    raises: OSError | None = None,
) -> None:
    """The platform's reader of access lists answers `entries`, or raises `raises`, for
    `folder`, and defers every other path to the reader it replaces (none on a platform without
    one), so the real lists on the way are still read where there is a reader."""
    real = os.path.realpath(folder)
    default = getattr(_platform.PLATFORM, "access_entries", lambda path: ())

    def fake(path: str) -> tuple[object, ...]:
        if path != real:
            return default(path)
        if raises is not None:
            raise raises
        return tuple(_platform._Entry(*e) for e in entries)

    monkeypatch.setattr(_platform.PLATFORM, "access_entries", fake, raising=False)


def _user_words(uid: int) -> str:
    import pwd

    try:
        return f"the user {pwd.getpwuid(uid).pw_name} (uid {uid})"
    except KeyError:
        return f"the user uid {uid}"


def _group_words(gid: int) -> str:
    import grp

    try:
        return f"the group {grp.getgrgid(gid).gr_name} (gid {gid})"
    except KeyError:
        return f"the group gid {gid}"


@pytest.mark.skipif(not POSIX, reason=WALK_SKIP)
@pytest.mark.parametrize(
    ("kind", "rights", "mask"),
    [*(("user", [name], None) for name in RIGHTS), ("group", ["add_file", "delete_child"], None)]
    + [("", ["delete_child"], None), ("user", [*RIGHTS][:5], GENERIC_WRITE)],
    ids=[*RIGHTS, "group-everyone", "unnamed", "generic-write"],
)
def test_an_entry_that_lets_another_change_a_folder_on_the_way_is_not_used(
    work, monkeypatch, kind, rights, mask
) -> None:
    """The folder above the cache is a real 0755 folder whose access list holds one allow
    entry: for another user, each right that adds, removes or renames what the folder holds,
    removes or renames the folder, or changes who may; for the group everyone; for a principal
    the system cannot name, whose id is never read as root's; for another user, the kernel's
    generic write bit alone, which a list a network file system translates can carry and which
    grants five of those rights. Each lets someone other than this user or root change the
    folder, so the cache is not used, and the warning names the folder, the principal and the
    rights."""
    binary, digest = _tiny(work)
    above = _above(work)
    cache = above / "cache"
    who = {"user": _other(), "group": EVERYONE, "": 0}[kind]
    mask = sum(RIGHTS[name] for name in rights) if mask is None else mask
    _listed(monkeypatch, above, (True, kind, who, mask, False))
    counts, seen, _ = _miss(binary, cache, digest)
    principal = {
        "user": _user_words(who),
        "group": _group_words(who),
        "": "a user or group the system cannot name",
    }[kind]
    why = f"has an access list that lets {principal} {', '.join(rights)}"
    warned = _not_used(counts, seen, above, why)
    assert warned.endswith(f"; {ENTRY_ADVICE}"), warned
    if kind == "group":
        assert warned == (
            f"wasi_python: not using the module cache at {cache}: {os.path.realpath(above)}, on "
            f"the way to it, {why}; {ENTRY_ADVICE}"
        ), warned


@pytest.mark.skipif(not POSIX, reason=WALK_SKIP)
@pytest.mark.parametrize(
    "entry",
    [
        (False, "group", EVERYONE, RIGHTS["delete"], False),
        (True, "user", "me", ALL_SIX, False),
        (True, "user", 0, ALL_SIX, False),
        (True, "user", "other", CHANGE_NOTHING, False),
        (True, "group", EVERYONE, ALL_SIX, True),
    ],
    ids=["deny", "this-user", "root", "changes-nothing", "only-inherit"],
)
def test_an_entry_that_changes_nothing_or_names_no_one_new_passes(work, monkeypatch, entry) -> None:
    """A deny entry, as every macOS home carries; an allow for this user or root, whom the walk
    already trusts; an allow of rights that change nothing in the folder; an entry that only
    what is made inside inherits. None lets another change the folder: the cache is used."""
    binary, digest = _tiny(work)
    above = _above(work)
    allow, kind, who, mask, inherit_only = entry
    uid = {"me": os.geteuid(), "other": _other()}.get(who, who)
    _listed(monkeypatch, above, (allow, kind, uid, mask, inherit_only))
    counts, seen, _ = _miss(binary, above / "cache", digest)
    _used(counts, seen)


@pytest.mark.skipif(not POSIX, reason=WALK_SKIP)
@pytest.mark.parametrize("code", [errno.EACCES, errno.EIO], ids=["EACCES", "EIO"])
def test_a_list_that_cannot_be_read_means_the_cache_is_not_used(work, monkeypatch, code) -> None:
    """The check cannot vouch for a folder whose list it cannot read: the cache is not used,
    and the warning gives the system's reason."""
    binary, digest = _tiny(work)
    above = _above(work)
    _listed(monkeypatch, above, raises=OSError(code, os.strerror(code)))
    counts, seen, _ = _miss(binary, above / "cache", digest)
    why = f"has an access list the runner cannot read ({os.strerror(code)})"
    warned = _not_used(counts, seen, above, why)
    assert warned.endswith(f"; {FOLDER_ADVICE}"), warned


@pytest.mark.skipif(not POSIX, reason=WALK_SKIP)
def test_when_roots_list_fails_the_warning_says_no_folder_can_hold_the_cache(
    work, monkeypatch
) -> None:
    """Every cache folder is below `/`, and on macOS `/` is the sealed system volume no one
    changes from a running system, so an entry there is not one to take back: the warning says
    to keep no cache."""
    binary, digest = _tiny(work)
    _listed(monkeypatch, "/", (True, "user", _other(), RIGHTS["delete_child"], False))
    counts, seen, _ = _miss(binary, work / "cache", digest)
    why = f"has an access list that lets {_user_words(_other())} delete_child"
    warned = _not_used(counts, seen, "/", why)
    assert warned.endswith(f"; {ROOT_LIST_ADVICE}"), warned
    assert "$WASI_PYTHON_CACHE" not in warned and "chmod -a" not in warned, warned


def _chmod(*args: str) -> None:
    subprocess.run(["chmod", *args], check=True, capture_output=True)


@pytest.mark.skipif(not MACOS, reason=MACOS_ONLY)
def test_on_macos_an_allow_entry_on_the_way_is_not_used(work) -> None:
    """A real entry, set on a folder this row made: everyone may add to it and remove from it
    while its mode reads 0755."""
    binary, digest = _tiny(work)
    above = _above(work)
    _chmod("+a", "group:everyone allow add_file,delete_child", str(above))
    try:
        counts, seen, _ = _miss(binary, above / "cache", digest)
    finally:
        _chmod("-N", str(above))
    why = "has an access list that lets the group everyone (gid 12) add_file, delete_child"
    _not_used(counts, seen, above, why)


@pytest.mark.skipif(not MACOS, reason=MACOS_ONLY)
def test_on_macos_the_homes_deny_entry_passes(work) -> None:
    """The entry every macOS home and its Library carry, set on a folder this row made."""
    binary, digest = _tiny(work)
    above = _above(work)
    _chmod("+a", "group:everyone deny delete", str(above))
    try:
        counts, seen, _ = _miss(binary, above / "cache", digest)
    finally:
        _chmod("-N", str(above))
    _used(counts, seen)


@pytest.mark.skipif(not MACOS, reason=MACOS_ONLY)
@pytest.mark.parametrize("limit", [True, False], ids=["limit_inherit", "inherit"])
def test_on_macos_a_folder_made_below_an_inheriting_entry_is_not_used(work, limit) -> None:
    """The folder above carries an entry that only what is made inside inherits, so it passes.
    The runner makes the missing folder below it, which inherits the entry as one that applies:
    everyone may then empty and refill it. The walk after the `mkdir` refuses it, before the
    cache folder is made. With `limit_inherit` the cache folder itself would inherit nothing,
    so this walk is the only check that sees it."""
    binary, digest = _tiny(work)
    above = _above(work)
    made, cache = above / "made", above / "made" / "cache"
    flags = "directory_inherit,only_inherit" + (",limit_inherit" if limit else "")
    _chmod("+a", f"group:everyone allow add_file,delete_child,{flags}", str(above))
    try:
        counts, seen, _ = _miss(binary, cache, digest)
    finally:
        _chmod("-R", "-N", str(above))
    why = "has an access list that lets the group everyone (gid 12) add_file, delete_child"
    _not_used(counts, seen, made, why)
    assert made.is_dir() and not cache.exists()


@pytest.mark.skipif(not MACOS, reason=MACOS_ONLY)
def test_on_macos_each_entry_is_read_as_it_is_written(work) -> None:
    """The reader answers each entry of a real list in its order: whether it allows, whose it
    is, its rights and whether it only inherits; a folder with no list answers none."""
    import pwd

    listed, bare = work / "listed", work / "bare"
    listed.mkdir()
    bare.mkdir()
    entries = [
        "user:nobody allow delete,writesecurity",
        "group:everyone deny delete",
        "group:everyone allow add_file,only_inherit,directory_inherit",
    ]
    for at, entry in enumerate(entries):
        _chmod("+a#", str(at), entry, str(listed))
    try:
        got = _platform.PLATFORM.access_entries(str(listed))
        none = _platform.PLATFORM.access_entries(str(bare))
    finally:
        _chmod("-N", str(listed))
    nobody = pwd.getpwnam("nobody").pw_uid
    assert [tuple(e) for e in got] == [
        (True, "user", nobody, RIGHTS["delete"] | RIGHTS["writesecurity"], False),
        (False, "group", EVERYONE, RIGHTS["delete"], False),
        (True, "group", EVERYONE, RIGHTS["add_file"], True),
    ], got
    assert none == ()


def _posix_acl(other: int, mask: int) -> bytes:
    """A Linux access list in the kernel's format: a 32-bit version word, 2, then one record per
    entry (tag, rights, id) in tag order: the owner, the named user `other`, the owning group,
    the mask and everyone else; an unnamed entry's id is all ones."""
    import struct

    unnamed = 0xFFFFFFFF
    records = [(0x01, 7, unnamed), (0x02, 7, other), (0x04, 5, unnamed)]
    records += [(0x10, mask, unnamed), (0x20, 5, unnamed)]
    return struct.pack("<I", 2) + b"".join(struct.pack("<HHI", *r) for r in records)


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason=LINUX_ONLY)
@pytest.mark.parametrize("mask", [7, 5], ids=["rwx", "r-x"])
def test_on_linux_a_named_entry_shows_in_the_group_bits(work, mask) -> None:
    """A Linux list that names another user with `rwx` must hold a mask, no named entry has a
    right the mask lacks, and the mode's group bits are the mask. So an entry that lets another
    user write shows as a group-writable folder, which the walk refuses for its mode, and one
    the mask cuts to `r-x` grants no write: the walk reads no list on Linux and misses none."""
    binary, digest = _tiny(work)
    above = _above(work)
    name = "system.posix_acl_access"
    try:
        os.setxattr(above, name, _posix_acl(_other(), mask))
    except OSError as e:
        if e.errno in (errno.ENOTSUP, errno.EOPNOTSUPP, errno.EINVAL):
            pytest.skip(
                f"this file system or namespace takes no such list ({errno.errorcode[e.errno]})"
            )
        raise
    try:
        assert stat.S_IMODE(os.lstat(above).st_mode) == (0o775 if mask == 7 else 0o755)
        counts, seen, _ = _miss(binary, above / "cache", digest)
    finally:
        os.removexattr(above, name)
    if mask == 5:
        _used(counts, seen)
        return
    _not_used(counts, seen, above, "may be written by others (mode 775) and is not sticky")


# Row 4: one read for every compile.


@pytest.fixture
def fresh(monkeypatch) -> None:
    """No module this process already holds, so each case compiles anew."""
    monkeypatch.setattr(process(), "modules", {})


def test_a_binary_changed_while_it_was_read_is_never_compiled_or_cached(work, fresh) -> None:
    """A set given through `artifacts=` is keyed by the digest of its binary as the call found
    it. The file is then changed, before the compile reads it: the bytes read do not hash to the
    key, so nothing is compiled and no `.cwasm` under that digest holds other code."""
    binary = work / "given.wasm"
    binary.write_bytes(wt.wat2wasm("(module)"))
    digest = hashlib.sha256(binary.read_bytes()).hexdigest()
    binary.write_bytes(wt.wat2wasm(PLANTED))
    cache = work / "cache"
    cache.mkdir(mode=0o700)
    before = process().counts["compiled"]
    with pytest.raises(ArtifactsMissing, match="changed while it was read"):
        _engines._module_miss(wt, _engines._engine(False), False, binary, cache, digest, False)
    assert process().counts["compiled"] == before
    assert list(cache.glob("*.cwasm")) == []


# Row 5: the empty and the relative `cache_dir`.


def test_an_empty_cache_dir_is_refused_before_any_work(work, monkeypatch) -> None:
    """`cache_dir=""` names no folder (an unset variable read as empty, say): each entry point
    refuses it before it looks for an artifact set, which here does not exist."""
    monkeypatch.setenv(_artifacts._ARTIFACTS_ENV, str(work / "no-set"))
    match = "an empty string names none"
    with pytest.raises(ValueError, match=match):
        wasi_python.run(["-c", "pass"], cache_dir="")
    with pytest.raises(ValueError, match=match):
        asyncio.run(wasi_python.run_async(["-c", "pass"], cache_dir=""))
    with pytest.raises(ValueError, match=match):
        wasi_python.Session(cache_dir="")


@pytest.fixture
def found(work, monkeypatch) -> Path:
    """A small set at $WASI_PYTHON_ARTIFACTS: a door-probing snapshot, an empty zip, its sums."""
    folder = work / "set"
    wat.build(folder, "python-snapshot.wasm", wat.SNAPSHOT)
    wat.build(folder, "python.wasm", wat.PLAIN_REACTOR)
    (folder / "MANIFEST").write_text("python 3.15.0\n")
    with zipfile.ZipFile(folder / "python-stdlib.zip", "w"):
        pass
    names = ["MANIFEST", "python-snapshot.wasm", "python-stdlib.zip", "python.wasm"]
    sums = [f"{hashlib.sha256((folder / n).read_bytes()).hexdigest()}  {n}\n" for n in names]
    (folder / "SHA256SUMS").write_text("".join(sums))
    monkeypatch.setenv(_artifacts._ARTIFACTS_ENV, str(folder))
    return folder


@pytest.mark.parametrize("given", ["argument", "variable"])
def test_a_relative_cache_dir_is_the_folder_it_names_at_the_call(
    found, fresh, work, monkeypatch, given
) -> None:
    """A relative `cache_dir`, or `$WASI_PYTHON_CACHE`, names a folder under the working folder
    of the moment the call is made. The working folder then moves, after the folders are
    judged and before the module is cached: the `.cwasm` is written where the name pointed at
    the call, so the folder judged is the folder used."""
    monkeypatch.chdir(work)
    elsewhere = work / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.setattr(process().observers, "after_walk", lambda: os.chdir(elsewhere))
    if given == "argument":
        done = runner.run([], cache_dir="rel")
    else:
        monkeypatch.setenv(_engines.CACHE_ENV, "rel")
        done = runner.run([])
    assert done.exit_code == 101, done
    assert len(list((work / "rel").glob("*.cwasm"))) == 1
    assert not (elsewhere / "rel").exists()
