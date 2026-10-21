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
import hashlib
import json
import os
import stat
import subprocess
import sys
import warnings
from pathlib import Path

import pytest
import wasmtime as wt

import wasi_python
from harness import needs, paths
from wasi_python import Grant, _engines, _platform
from wasi_python import _wasmtime_ffi as ffi
from wasi_python._process import process

POSIX = os.name == "posix"
CALLERS = ("run", "run_async", "Session")
OWN = ("off", "elsewhere")
# Whose cache the guest aims at: the one `$WASI_PYTHON_CACHE` names (it exists), or the
# platform's default under a home folder that holds nothing yet (the cache not made).
VICTIMS = ("env", "default")

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
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    cache = _platform.PLATFORM.default_cache_dir(Path.home())
    assert not cache.exists() and home in cache.parents, cache
    return home, cache


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
        assert "module cache" in str(e), e
        assert not (cache / _snapshot_name()).exists()
        return
    outcome, loaded = _fresh_process_loads()
    pytest.fail(
        f"the writable grant over {cache} was not refused (the guest exited {exit_code}); "
        f"the next default call ({outcome}) then loaded {loaded} compiled module(s) the guest "
        "wrote"
    )


def test_a_root_still_to_be_made_that_would_hold_a_cache_is_refused(
    compiled, work, monkeypatch
) -> None:
    """Neither the root nor `$WASI_PYTHON_CACHE` exists yet, and the cache would lie inside the
    root once it is made: refused, and neither is made. A root beside it, under the same
    existing folder, is not refused, and a call with `cache_dir=False` makes no cache."""
    cache = work / "new" / "wasi_python"
    monkeypatch.setenv(_engines.CACHE_ENV, str(cache))
    with pytest.raises(ValueError, match="module cache"):
        wasi_python.run(["-c", "pass"], root=str(work / "new"), cache_dir=False)
    assert not (work / "new").exists()
    done = wasi_python.run(["-c", "pass"], root=str(work / "other"), cache_dir=False)
    assert done.exit_code == 0, done
    assert not (work / "new").exists()


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
        _engines._module_miss(wt, _engines._engine(False), False, binary, cache, digest)
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
