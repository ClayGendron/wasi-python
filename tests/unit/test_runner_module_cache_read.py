"""The compiled module wasmtime loads is the file the runner checked, and a cache on a way
another user could change is not used.

A `.cwasm` is native code that wasmtime runs as it finds it. On POSIX the runner opens the
cache folder and the file by descriptor, checks what it opened, and hands wasmtime that
descriptor's name, so a file swapped in at the path after the check is never what is loaded.
Every folder on the way to the cache must be this user's or root's and closed to other
writers (a sticky folder such as `/tmp` aside), as `sshd` asks of the way to a key, or the
cache is not used, with a warning, and the call still runs. A folder or file with an access
list is not used either. On Windows the file is held open from its check to its load. A
module is compiled from the bytes it was hashed from, so a `.cwasm` under a digest holds that
digest's code. An empty `cache_dir` is refused, and a relative one is the folder it names when
the call is made.

Each verdict is a count from `stats()`, a module's exports, a warning or a refusal; the stand-ins
are parameters of the functions they stand in for."""

from __future__ import annotations

import asyncio
import errno
import hashlib
import os
import shutil
import stat
import subprocess
import sys
import types
import warnings
import zipfile
from pathlib import Path

import pytest
import wasmtime as wt

import wasi_python
from harness import wat
from wasi_python import ArtifactsMissing, _artifacts, _engines, runner
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
        mod = _engines._module_miss(stand_in, engine, False, binary, cache, digest, **seams)
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
