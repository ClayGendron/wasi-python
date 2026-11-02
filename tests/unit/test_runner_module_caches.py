"""Every compiled-module cache the process could use is guarded, whatever one call's own
`cache_dir` says.

A `.cwasm` is native code that wasmtime runs as it finds it. A call with `cache_dir=False`, or
with a cache of its own, must still refuse a writable grant or root at, inside or above the
caches other calls and processes use: `$WASI_PYTHON_CACHE` and the platform's default folder.
Otherwise its guest writes a file named for the public snapshot digest there, and the next call
with the default cache loads it in the host.

The cache's own checks stand behind that rule: on POSIX a cache folder is used only when no one
but its owner may read, write or enter it, and a `.cwasm` is loaded only when no one but its
owner may read or write it, which is how the runner makes both and how a guest, under the usual
umask, makes neither. Nothing here measures time: each verdict is a refusal, a mode or a count
from `stats()`."""

from __future__ import annotations

import asyncio
import base64
import errno
import hashlib
import json
import os
import stat
import subprocess
import sys
import types
import warnings
from pathlib import Path

import pytest
import wasmtime as wt

import wasi_python
from harness import needs, paths
from wasi_python import Grant, _engines, _platform, _platform_posix, _platform_windows
from wasi_python import _wasmtime_ffi as ffi
from wasi_python._process import process

POSIX = os.name == "posix"
CALLERS = ("run", "run_async", "Session")
OWN = ("off", "elsewhere")
# Whose cache the guest aims at: the one `$WASI_PYTHON_CACHE` names (it exists); the platform's
# default under a home folder that holds nothing yet (the cache not made); or that default as a
# process without this one's `$XDG_CACHE_HOME` or `%LOCALAPPDATA%` computes it, while this
# process's own default is elsewhere.
VICTIMS = ("env", "default", "fallback")
# What a refusal names, so a row knows which cache refused it.
NAMED = {"env": "$WASI_PYTHON_CACHE", "default": "default folder", "fallback": "default folder"}

# Step 2 of the plant, in a fresh process (nothing compiled in memory): one call with every
# default, and how many modules it loaded from a cache.
LOADS = (
    "import json, sys\n"
    f"sys.path.insert(0, {str(paths.REPO / 'src')!r})\n"
    "import wasi_python\n"
    "try:\n"
    "    outcome = wasi_python.run(['-c', 'pass']).exit_code\n"
    "except Exception as e:\n"
    "    outcome = type(e).__name__\n"
    "print(json.dumps([outcome, wasi_python.stats()['loaded']]))\n"
)


@pytest.fixture(scope="module")
def compiled() -> None:
    """The snapshot compiled once in this process, kept in memory only, so no call below writes
    a compiled module to disk on its way to the judge."""
    needs.need("runner", "artifact dir")
    done = wasi_python.run(["-c", "pass"], cache_dir=False)
    assert done.exit_code == 0, done


def _snapshot_name() -> str:
    """The name the snapshot's unmetered `.cwasm` has: public, from the set's SHA256SUMS and
    the installed wasmtime-py."""
    directory = paths.artifact_dir()
    assert directory is not None
    sums = dict(
        reversed(line.split()) for line in (directory / "SHA256SUMS").read_text().splitlines()
    )
    return f"{sums['python-snapshot.wasm'][:32]}-wasmtime{ffi.version()}-plain.cwasm"


def _serialized() -> bytes:
    """A real compiled module this wasmtime loads with the runner's unmetered engine: what a
    guest would plant, small enough to carry in its source."""
    return wt.Module(_engines._engine(False), "(module)").serialize()


def _victim(work: Path, victim: str, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """The folder the guest is granted, writable, and the cache that lies in it."""
    if victim == "env":
        granted = work / "granted"
        cache = granted / "wasi_python"
        cache.mkdir(parents=True, mode=0o700)
        monkeypatch.setenv(_engines.CACHE_ENV, str(cache))
        return granted, cache
    home = work / "home"
    home.mkdir()
    monkeypatch.delenv(_engines.CACHE_ENV, raising=False)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    if victim == "default":
        monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
        monkeypatch.delenv("LOCALAPPDATA", raising=False)
        cache = _platform.PLATFORM.default_cache_dir(Path.home())
    else:
        # This process's default is elsewhere; the one without the overrides is under home.
        monkeypatch.setenv("XDG_CACHE_HOME", str(work / "xdg"))
        monkeypatch.setenv("LOCALAPPDATA", str(work / "local"))
        cache = _without_overrides(home)
    assert not cache.exists() and home in cache.parents, cache
    return home, cache


def _without_overrides(home: Path, system: str = sys.platform) -> Path:
    """The platform's default as a process of this user with no `$XDG_CACHE_HOME` or
    `%LOCALAPPDATA%` computes it."""
    if system == "win32":
        return home / "AppData" / "Local" / "wasi_python" / "cache"
    if system == "darwin":
        return home / "Library" / "Caches" / "wasi_python"
    return home / ".cache" / "wasi_python"


def _plant_code(target: str) -> str:
    data = base64.b64encode(_serialized()).decode()
    return (
        "import base64, os\n"
        f"os.makedirs({os.path.dirname(target)!r}, exist_ok=True)\n"
        f"with open({target!r}, 'wb') as f:\n"
        f"    f.write(base64.b64decode({data!r}))\n"
        "print('planted')\n"
    )


def _call(caller: str, code: str, grant: Grant, cache_dir: object) -> int | None:
    if caller == "run":
        return wasi_python.run(["-c", code], grants=[grant], cache_dir=cache_dir).exit_code
    if caller == "run_async":
        done = asyncio.run(wasi_python.run_async(["-c", code], grants=[grant], cache_dir=cache_dir))
        return done.exit_code
    with wasi_python.Session(grants=[grant], cache_dir=cache_dir) as session:
        return session.run(code).exit_code


def _fresh_process_loads() -> list:
    out = subprocess.run(
        [sys.executable, "-I", "-c", LOADS], capture_output=True, text=True, env={**os.environ}
    )
    assert out.returncode == 0, out.stderr[-1500:]
    return json.loads(out.stdout)


@pytest.mark.parametrize("victim", VICTIMS)
@pytest.mark.parametrize("own", OWN)
@pytest.mark.parametrize("caller", CALLERS)
def test_a_writable_grant_over_another_calls_cache_is_refused(
    compiled, work, monkeypatch, caller, own, victim
) -> None:
    """Step 1: a call whose own cache is off or elsewhere grants, writable, the folder that holds
    the cache another call uses. It is refused before the guest runs. Were it not, the guest
    would write a compiled module under the snapshot's public name, and step 2, a call with every
    default in a fresh process, would load it as native code: the count it reports is in the
    failure."""
    granted, cache = _victim(work, victim, monkeypatch)
    target = "/c/" + (cache / _snapshot_name()).relative_to(granted).as_posix()
    cache_dir: object = False if own == "off" else str(work / "own-cache")
    grant = Grant(str(granted), "/c", writable=True)
    try:
        exit_code = _call(caller, _plant_code(target), grant, cache_dir)
    except ValueError as e:
        assert "module cache" in str(e) and NAMED[victim] in str(e), e
        assert not (cache / _snapshot_name()).exists()
        if victim != "env":
            assert not cache.exists(), "a cache the call does not use was made"
        return
    outcome, loaded = _fresh_process_loads()
    pytest.fail(
        f"the writable grant over {cache} was not refused (the guest exited {exit_code}); "
        f"the next default call ({outcome}) then loaded {loaded} compiled module(s) the guest "
        "wrote"
    )


@pytest.mark.parametrize("where", ["at", "inside"])
def test_a_writable_grant_at_or_inside_another_calls_cache_is_refused(
    compiled, work, monkeypatch, where
) -> None:
    """The grant is the cache `$WASI_PYTHON_CACHE` names, or a folder inside it, in a call that
    keeps no cache: refused, naming that cache."""
    cache = work / "wasi_python"
    cache.mkdir(mode=0o700)
    granted = cache if where == "at" else cache / "sub"
    granted.mkdir(exist_ok=True)
    monkeypatch.setenv(_engines.CACHE_ENV, str(cache))
    with pytest.raises(ValueError, match="module cache") as refused:
        wasi_python.run(
            ["-c", "pass"], grants=[Grant(str(granted), "/c", writable=True)], cache_dir=False
        )
    assert "$WASI_PYTHON_CACHE" in str(refused.value), refused.value


@pytest.mark.parametrize("own", ["off", "own"])
def test_a_cache_reached_through_a_link_in_a_writable_grant_is_refused(
    compiled, work, monkeypatch, own
) -> None:
    """`$WASI_PYTHON_CACHE` names a path through a link that lies in a folder granted writable,
    while the folder the link resolves to is outside it. The guest could replace the link with a
    folder of its own, and the next call's cache would be the guest's: refused, whether the call
    keeps no cache or that cache is its own."""
    granted, safe = work / "data", work / "safe"
    granted.mkdir()
    (safe / "wasi_python").mkdir(parents=True, mode=0o700)
    try:
        (granted / "link").symlink_to(safe, target_is_directory=True)
    except OSError as e:
        pytest.skip(f"this host cannot make a symbolic link ({e.errno})")
    monkeypatch.setenv(_engines.CACHE_ENV, str(granted / "link" / "wasi_python"))
    with pytest.raises(ValueError, match="module cache"):
        wasi_python.run(
            ["-c", "pass"],
            grants=[Grant(str(granted), "/c", writable=True)],
            cache_dir=False if own == "off" else None,
        )


@pytest.mark.parametrize("climbs", [1, 2])
def test_a_cache_reached_through_a_link_then_dotdot_in_a_writable_grant_is_refused(
    compiled, work, monkeypatch, climbs
) -> None:
    """`$WASI_PYTHON_CACHE` names a path through a link in a folder granted writable, then
    climbs with `..`. The system walks the link and climbs from where it leads, not from the
    link's own folder, so the folder that holds the link must be judged as the path is walked:
    the guest could replace the link and choose where the cache resolves. Refused, with one `..`
    or two."""
    granted, target = work / "a", work / "x" / "y"
    granted.mkdir()
    target.mkdir(parents=True)
    reached = (target.parent if climbs == 1 else work) / "c"
    reached.mkdir(mode=0o700)
    try:
        (granted / "link").symlink_to(target, target_is_directory=True)
    except OSError as e:
        pytest.skip(f"this host cannot make a symbolic link ({e.errno})")
    spelled = os.path.join(str(granted / "link"), *([".."] * climbs), "c")
    monkeypatch.setenv(_engines.CACHE_ENV, spelled)
    with pytest.raises(ValueError, match="module cache"):
        wasi_python.run(
            ["-c", "pass"], grants=[Grant(str(granted), "/c", writable=True)], cache_dir=False
        )


@pytest.mark.parametrize("own", OWN)
def test_a_root_still_to_be_made_that_would_hold_a_cache_is_refused(
    compiled, work, monkeypatch, own
) -> None:
    """Neither the root nor `$WASI_PYTHON_CACHE` exists yet, and the cache would lie inside the
    root once it is made, or the root inside the cache: refused, and neither is made. A root
    beside it, under the same existing folder, is not refused, and a call that keeps no cache, or
    keeps its own elsewhere, makes neither `$WASI_PYTHON_CACHE` nor the platform's default."""
    cache = work / "new" / "wasi_python"
    home = work / "home"
    home.mkdir()
    monkeypatch.setenv(_engines.CACHE_ENV, str(cache))
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    cache_dir: object = False if own == "off" else str(work / "own-cache")
    for root in (work / "new", cache / "sub"):
        with pytest.raises(ValueError, match="module cache"):
            wasi_python.run(["-c", "pass"], root=str(root), cache_dir=cache_dir)
        assert not (work / "new").exists(), root
    done = wasi_python.run(["-c", "pass"], root=str(work / "other"), cache_dir=cache_dir)
    assert done.exit_code == 0, done
    assert not (work / "new").exists()
    assert not _platform.PLATFORM.default_cache_dir(Path.home()).exists()


def test_every_default_a_process_of_this_user_could_compute_is_listed(work, monkeypatch) -> None:
    """Each platform lists its default as this process computes it and as a process of the same
    user without `$XDG_CACHE_HOME` or `%LOCALAPPDATA%` computes it; on POSIX also under the home
    folder the password database gives this user, when `$HOME` says otherwise."""
    home = work / "home"
    monkeypatch.setenv("XDG_CACHE_HOME", str(work / "xdg"))
    monkeypatch.setenv("LOCALAPPDATA", str(work / "local"))
    linux = set(_platform_posix._Linux().default_cache_dirs(home))
    assert {work / "xdg" / "wasi_python", _without_overrides(home, "linux")} <= linux, linux
    darwin = set(_platform_posix._Darwin().default_cache_dirs(home))
    assert _without_overrides(home, "darwin") in darwin, darwin
    windows = set(_platform_windows._Windows().default_cache_dirs(home))
    want = {work / "local" / "wasi_python" / "cache", _without_overrides(home, "win32")}
    assert want <= windows, windows
    if POSIX:
        import pwd

        real = Path(pwd.getpwuid(os.getuid()).pw_dir)
        assert _without_overrides(real, "linux") in linux, linux
        assert _without_overrides(real, "darwin") in darwin, darwin


def test_a_process_with_no_home_folder_still_runs(compiled, monkeypatch) -> None:
    """Where no home folder can be found (a container with no `$HOME` and a uid the password
    database does not list), there is no default cache to judge, and a call that keeps no cache
    runs."""

    def no_home() -> Path:
        raise RuntimeError("Could not determine home directory.")

    monkeypatch.delenv(_engines.CACHE_ENV, raising=False)
    monkeypatch.setattr(Path, "home", staticmethod(no_home))
    if POSIX:
        import pwd

        def unlisted(uid: int) -> object:
            raise KeyError(f"getpwuid(): uid not found: {uid}")

        monkeypatch.setattr(pwd, "getpwuid", unlisted)
    done = wasi_python.run(["-c", "pass"], cache_dir=False)
    assert done.exit_code == 0, done


# The cache's own checks, on a module of a few bytes: no artifact set needed.


def _tiny(work: Path) -> tuple[Path, str]:
    binary = work / "tiny.wasm"
    binary.write_bytes(wt.wat2wasm("(module)"))
    return binary, hashlib.sha256(str(work).encode()).hexdigest()  # a digest of this test's own


def _miss(binary: Path, cache: Path, digest: str) -> tuple[dict[str, int], list[str]]:
    """One cache miss for the module named `digest`: the counts it moved, and its warnings."""
    before = dict(process().counts)
    with warnings.catch_warnings(record=True) as seen:
        warnings.simplefilter("always")
        _engines._module_miss(wt, _engines._engine(False), False, binary, cache, digest, held=None)
    counts = {k: process().counts[k] - before[k] for k in ("compiled", "loaded", "written")}
    return counts, [str(w.message) for w in seen]


def _name(digest: str) -> str:
    return f"{digest[:32]}-wasmtime{ffi.version()}-plain.cwasm"


def test_the_runner_makes_its_cache_folder_0700_and_its_files_0600(work) -> None:
    binary, digest = _tiny(work)
    cache = work / "a" / "cache"
    counts, _ = _miss(binary, cache, digest)
    assert counts == {"compiled": 1, "loaded": 0, "written": 1}, counts
    if POSIX:
        assert stat.S_IMODE(cache.stat().st_mode) == 0o700
        assert stat.S_IMODE((cache / _name(digest)).stat().st_mode) == 0o600


def test_a_cwasm_others_may_read_is_compiled_again_and_replaced_never_loaded(work) -> None:
    """A `.cwasm` at 0644, as a guest's `open` makes it under the usual umask, in a cache folder
    at 0700: on POSIX it is not loaded; the module is compiled and the runner's own file, at
    0600, takes its place. Windows has no such mode bits: there the file is loaded, which this
    check records."""
    binary, digest = _tiny(work)
    cache = work / "cache"
    cache.mkdir(mode=0o700)
    planted = cache / _name(digest)
    planted.write_bytes(_serialized())
    planted.chmod(0o644)
    counts, _ = _miss(binary, cache, digest)
    if POSIX:
        assert counts == {"compiled": 1, "loaded": 0, "written": 1}, counts
        assert stat.S_IMODE(planted.stat().st_mode) == 0o600
    else:
        assert counts == {"compiled": 0, "loaded": 1, "written": 0}, counts


def test_a_cache_folder_others_may_enter_is_not_used(work) -> None:
    """A cache folder at 0755, as a guest's `mkdir` makes it under the usual umask, holding a
    `.cwasm` at 0600: on POSIX neither is read nor written, the module is compiled in memory,
    and a warning names the folder. Windows has no such mode bits: there the file is loaded,
    which this check records."""
    binary, digest = _tiny(work)
    cache = work / "cache"
    cache.mkdir()
    cache.chmod(0o755)
    planted = cache / _name(digest)
    planted.write_bytes(_serialized())
    planted.chmod(0o600)
    counts, seen = _miss(binary, cache, digest)
    if POSIX:
        assert counts == {"compiled": 1, "loaded": 0, "written": 0}, counts
        assert any("not using the module cache" in m and str(cache) in m for m in seen), seen
        assert sorted(p.name for p in cache.iterdir()) == [planted.name]
    else:
        assert counts == {"compiled": 0, "loaded": 1, "written": 0}, counts


def test_a_cwasm_that_is_a_link_is_never_loaded(work) -> None:
    """A link in the cache, to a compiled module at 0600, is not loaded on any system: on
    Windows too, where the cache's only check is the kind of file it finds."""
    binary, digest = _tiny(work)
    cache = work / "cache"
    cache.mkdir(mode=0o700)
    real = work / "elsewhere.cwasm"
    real.write_bytes(_serialized())
    real.chmod(0o600)
    try:
        (cache / _name(digest)).symlink_to(real)
    except OSError as e:
        pytest.skip(f"this host cannot make a symbolic link ({e.errno})")
    counts, _ = _miss(binary, cache, digest)
    assert counts["loaded"] == 0 and counts["compiled"] == 1, counts
    assert real.read_bytes() == _serialized()  # never written through


def test_a_cwasm_with_a_second_name_is_never_loaded(work) -> None:
    """A hard link in the cache to a compiled module at 0600 elsewhere: a guest can make one
    (WASI's `path_link`) without writing a byte, and the file it names keeps its mode and owner.
    The runner's own files have one name; one with two is not loaded, on any system, and the
    file elsewhere is never written through."""
    binary, digest = _tiny(work)
    cache = work / "cache"
    cache.mkdir(mode=0o700)
    real = work / "elsewhere.cwasm"
    real.write_bytes(_serialized())
    real.chmod(0o600)
    os.link(real, cache / _name(digest))
    counts, _ = _miss(binary, cache, digest)
    assert counts["loaded"] == 0 and counts["compiled"] == 1, counts
    assert real.read_bytes() == _serialized()


@pytest.mark.skipif(
    not POSIX,
    reason="Windows holds the file open from its check to its load: "
    "test_on_windows_the_cwasm_is_held_open_from_its_check_to_its_load",
)
def test_a_cwasm_swapped_between_its_check_and_its_load_is_discarded(work) -> None:
    """Where wasmtime is given the path, because the system names no descriptor of the checked
    file that opens (no `/proc` in a sandbox, say), wasmtime-py opens the `.cwasm` by its path
    after the runner has checked the file there. A stand-in for wasmtime-py, handed to the cache
    miss as its own, puts another file at that path between the two (a compiled module at 0644,
    as a guest would make it) and then loads: the name's stamp checked again after the load
    discards the module loaded, the binary is compiled, and the runner's own file replaces the
    one swapped in."""
    binary, digest = _tiny(work)
    cache = work / "cache"
    cache.mkdir(mode=0o700)
    checked = cache / _name(digest)
    checked.write_bytes(_serialized())
    checked.chmod(0o600)
    swapped_in = work / "swapped-in.cwasm"
    swapped_in.write_bytes(_serialized())
    swapped_in.chmod(0o644)
    given: list[str] = []

    class Module(wt.Module):
        @classmethod
        def deserialize_file(cls, engine, path):
            given.append(path)
            os.replace(swapped_in, path)
            return wt.Module.deserialize_file(engine, path)

    def no_names(name: str, flags: int, *args: object, **kwargs: object) -> int:
        raise OSError(errno.ENOENT, "no descriptor names here", name)

    stand_in = types.SimpleNamespace(Module=Module, WasmtimeError=wt.WasmtimeError)
    before = dict(process().counts)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        _engines._module_miss(
            stand_in,
            _engines._engine(False),
            False,
            binary,
            cache,
            digest,
            held=None,
            reopen=no_names,
        )
    counts = {k: process().counts[k] - before[k] for k in ("compiled", "loaded", "written")}
    assert given == [str(checked)], given
    assert counts == {"compiled": 1, "loaded": 0, "written": 1}, counts
    assert stat.S_IMODE(checked.stat().st_mode) == 0o600


def test_a_folder_at_a_cwasm_name_is_skipped_not_raised(work) -> None:
    """A folder where a `.cwasm` would be, as a guest's `mkdir` could leave it: the module is
    compiled and kept in memory, the call goes on, and the folder is left as it is."""
    binary, digest = _tiny(work)
    cache = work / "cache"
    cache.mkdir(mode=0o700)
    (cache / _name(digest)).mkdir()
    counts, _ = _miss(binary, cache, digest)
    assert counts == {"compiled": 1, "loaded": 0, "written": 0}, counts
    assert (cache / _name(digest)).is_dir()


def test_a_cache_folder_that_is_a_link_is_not_used(work) -> None:
    """The cache folder is a link (a symbolic link on POSIX, a junction on Windows) to a folder
    at 0700 holding a `.cwasm` at 0600: not used on any system; on Windows the folder's kind is
    one of the two things the cache can check there."""
    binary, digest = _tiny(work)
    real = work / "real"
    real.mkdir(mode=0o700)
    planted = real / _name(digest)
    planted.write_bytes(_serialized())
    planted.chmod(0o600)
    cache = work / "cache"
    if POSIX:
        cache.symlink_to(real, target_is_directory=True)
    else:
        import _winapi

        _winapi.CreateJunction(str(real), str(cache))
    counts, _ = _miss(binary, cache, digest)
    assert counts == {"compiled": 1, "loaded": 0, "written": 0}, counts
    assert sorted(p.name for p in real.iterdir()) == [planted.name]


# `$WASI_PYTHON_CACHE` is read once, when the call is made, in the form the system reads it.


def test_a_relative_cache_variable_is_the_folder_it_named_at_the_call(work, monkeypatch) -> None:
    """A relative `$WASI_PYTHON_CACHE` names a folder under the working folder of the moment the
    call is made. The working folder then moves before the grants are judged: the other caches
    the call keeps from its guest still name the folder the variable named at the call, by an
    absolute path, and nothing under the new working folder."""
    first, then = work / "first", work / "then"
    first.mkdir()
    then.mkdir()
    monkeypatch.chdir(first)
    monkeypatch.setenv(_engines.CACHE_ENV, "rel")
    chosen = _engines._cache_given(str(work / "own"))
    monkeypatch.chdir(then)
    named = [path for _, path in _engines._caches(chosen)]
    assert all(path.is_absolute() for path in named), named
    real = [os.path.realpath(path) for path in named]
    assert os.path.realpath(first / "rel") in real, named
    assert not any(path.startswith(os.path.realpath(then)) for path in real), named


def test_a_cache_variable_set_after_the_call_is_not_read_by_it(work, monkeypatch) -> None:
    """`$WASI_PYTHON_CACHE` is unset when the call is made and set before its folders are
    resolved: the call keeps its module in the platform's default folder, and the folder the
    variable names later is not among the caches it judges."""
    home = work / "home"
    home.mkdir()
    for name in (_engines.CACHE_ENV, "XDG_CACHE_HOME", "LOCALAPPDATA"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    chosen = _engines._cache_given(None)
    late = work / "late"
    monkeypatch.setenv(_engines.CACHE_ENV, str(late))
    assert chosen.folder == _platform.PLATFORM.default_cache_dir(home), chosen
    named = [path for _, path in _engines._caches(chosen)]
    assert not any(late == path or late in path.parents for path in named), named


WIN_CWD = {"": "C:\\work", "C:": "C:\\work", "D:": "D:\\elsewhere"}


@pytest.mark.parametrize(
    ("spelled", "absolute"),
    [
        ("rel\\link\\..\\c", "C:\\work\\rel\\link\\..\\c"),
        ("D:rel\\..\\x", "D:\\elsewhere\\rel\\..\\x"),
        ("\\top\\..\\x", "C:\\top\\..\\x"),
        ("C:\\a\\link\\..\\b", "C:\\a\\link\\..\\b"),
        ("\\\\server\\share\\a\\..\\b", "\\\\server\\share\\a\\..\\b"),
    ],
    ids=["relative", "drive-relative", "rooted", "absolute", "share"],
)
def test_on_windows_a_cache_folder_is_made_absolute_keeping_every_dotdot(
    monkeypatch, spelled, absolute
) -> None:
    """On Windows a relative cache folder joins the current folder of its drive, a
    drive-relative one that drive's own, and a rooted one takes the current drive; every `..`
    is kept, so the judge's walk takes it after the link before it, as the guest's open would.
    The current folders are the observers' stand-ins, so the case runs on every system."""
    monkeypatch.setattr(process().observers, "drive_folder", lambda drive: WIN_CWD[drive.upper()])
    assert _platform_windows._Windows().absolute(spelled) == absolute


@pytest.mark.skipif(
    not POSIX,
    reason="a link on Windows needs the symbolic-link privilege; the Windows form is pinned by "
    "test_on_windows_a_cache_folder_is_made_absolute_keeping_every_dotdot",
)
def test_a_dotdot_after_a_link_in_cache_dir_means_what_the_system_means(work) -> None:
    """`cache_dir` climbs with `..` after a link: the system climbs from where the link leads,
    not from the link's own folder, so the folder made absolute keeps the `..`, and the module
    is cached where the system resolves the path."""
    granted, target = work / "granted", work / "x" / "y"
    granted.mkdir()
    target.mkdir(parents=True)
    (granted / "link").symlink_to(target, target_is_directory=True)
    spelled = os.path.join(str(granted / "link"), "..", "c")
    chosen = _engines._cache_given(spelled)
    assert chosen.folder is not None and ".." in chosen.folder.parts, chosen
    binary, digest = _tiny(work)
    counts, seen = _miss(binary, chosen.folder, digest)
    assert counts == {"compiled": 1, "loaded": 0, "written": 1}, (counts, seen)
    assert len(list((work / "x" / "c").glob("*.cwasm"))) == 1
    assert not (granted / "c").exists()
