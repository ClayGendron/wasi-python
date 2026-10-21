"""wasmtime-py's import and the two engines (the adapter import stays inside `_wasmtime`, so
importing this module loads no wasmtime-py), the compiled modules and the `.cwasm` cache, the
module lock and the counts, the epoch ticker, and the preopen check's WAT module."""

from __future__ import annotations

import hashlib
import os
import stat
import tempfile
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from . import _artifacts, _platform
from ._artifacts import ArtifactsMissing
from ._limits import TICK_S
from ._platform import _WASM_STACK
from ._process import process

if TYPE_CHECKING:
    import wasmtime
CACHE_ENV = "WASI_PYTHON_CACHE"


def _wasmtime() -> Any:
    """wasmtime-py, or one `ImportError` whatever stopped it loading: not
    installed (`ImportError`), installed on a platform it does not support (its pure wheel raises
    `RuntimeError` naming the architecture), or its native library not loading (`OSError`). The
    original is chained as the cause, so its text still names the platform."""
    try:
        import wasmtime as wt
    except (ImportError, RuntimeError, OSError) as e:
        raise ImportError(
            "wasi_python.run needs wasmtime-py (wasmtime>=49,<50), which installs with "
            "wasi-python; reinstall it or install wasmtime directly"
        ) from e
    from . import _wasmtime_ffi  # noqa: F401  (its own ImportError names what moved)

    return wt


# The identity check: wasmtime reports a preopen's `ino` as SipHash-1-3, zero keys,
# over the host folder's two identity numbers as 64-bit words (filesystem.rs:354-371; on Windows
# the volume serial and file index, windows.rs:85-91). A wasmtime that hashes otherwise refuses
# every grant, loudly; tests/unit/test_runner_grants.py pins it on every OS.
_CHECK_WAT = """(module
  (import "wasi_snapshot_preview1" "fd_prestat_get" (func $pg (param i32 i32) (result i32)))
  (import "wasi_snapshot_preview1" "fd_prestat_dir_name"
    (func $pn (param i32 i32 i32) (result i32)))
  (import "wasi_snapshot_preview1" "fd_filestat_get" (func $st (param i32 i32) (result i32)))
  (memory (export "memory") 1)
  (func (export "prestat") (param i32) (result i32) (call $pg (local.get 0) (i32.const 0)))
  (func (export "name") (param i32 i32) (result i32)
    (call $pn (local.get 0) (i32.const 1024) (local.get 1)))
  (func (export "stat") (param i32) (result i32) (call $st (local.get 0) (i32.const 64))))"""


def _check_module(wt: Any, engine: Any, metered: bool) -> Any:
    p = process()
    with p.cache_lock:
        if metered not in p.check_modules:
            p.check_modules[metered] = wt.Module(engine, _CHECK_WAT)
        return p.check_modules[metered]


def _home() -> Path | None:
    """The home folder, or None where none can be found (no `$HOME` and a uid the password
    database does not list): such a process has no default cache."""
    try:
        return Path.home()
    except (RuntimeError, KeyError, OSError):
        return None


def _cache_dir(given: str | os.PathLike[str] | None | bool) -> Path | None:
    if given is False:
        return None
    if given is not None and given is not True:
        return Path(given)
    if os.environ.get(CACHE_ENV):
        return Path(os.environ[CACHE_ENV])
    home = _home()
    return None if home is None else _platform.PLATFORM.default_cache_dir(home)


def _caches(own: Path | None) -> tuple[tuple[str, Path], ...]:
    """Every other module cache a call or process of this user could use, whatever this call's
    own: the folder `$WASI_PYTHON_CACHE` names and every platform default, each with the name
    the judge's refusal gives it. A call that keeps no cache, or its own elsewhere, must still
    give its guest no way to write where the next call loads native code from. Each name begins
    "the module cache"; `own` and repeats are left out."""
    found: list[tuple[str, Path]] = []
    if os.environ.get(CACHE_ENV):
        path = Path(os.environ[CACHE_ENV])
        found.append((f"the module cache ${CACHE_ENV} names ({path})", path))
    home = _home()
    for path in () if home is None else _platform.PLATFORM.default_cache_dirs(home):
        found.append((f"the module cache in the platform's default folder ({path})", path))
    seen = set() if own is None else {os.path.abspath(own)}
    caches = []
    for name, path in found:
        if os.path.abspath(path) not in seen:
            seen.add(os.path.abspath(path))
            caches.append((name, path))
    return tuple(caches)


def _engine(metered: bool) -> wasmtime.Engine:
    """Two engines per process: fuel metering changes the compiled code. The async stack size
    is set first, through the seam."""
    import wasmtime as wt

    from . import _wasmtime_ffi as ffi

    p = process()
    with p.cache_lock:
        if metered not in p.engines:
            p.fork_used = True  # before the engine exists: a fork from here on is refused
            cfg = wt.Config()
            cfg.consume_fuel = metered
            cfg.epoch_interruption = True
            ffi.set_async_stack(cfg, _WASM_STACK)  # first: an 8 MiB stack without it aborts
            cfg.max_wasm_stack = _WASM_STACK
            p.engines[metered] = wt.Engine(cfg)
        return p.engines[metered]


def _module(
    engine: wasmtime.Engine,
    metered: bool,
    binary: Path,
    cache: Path | None,
    want: str | None = None,
) -> wasmtime.Module:
    """The compiled module: from this process, else the .cwasm cache, else compiled and cached.

    A .cwasm is native code that wasmtime runs as it finds it, so the cache is used only as the
    runner makes it: on POSIX, a directory at 0700 and files at 0600 with one name, owned by this
    user; on Windows, no link or junction. Anything else is ignored, with a warning, and the
    module is compiled in this process; a refused file is replaced by the runner's own. That
    stops a file a guest makes, not one it rewrites in place: the guard is that the grant judge
    lets no guest reach any cache. `want` is a found set's checked digest:
    the module is then compiled from bytes read once and held to it, and the
    .cwasm under that digest is written only from them."""
    import wasmtime as wt

    digest = want if want is not None else _artifacts._digest(binary)
    p = process()
    with p.cache_lock:
        mod = p.modules.get((metered, digest))
        guard = p.compiling.setdefault((metered, digest), threading.Lock())
    if mod is not None:
        return mod
    # One thread compiles or loads; the others wait for it. Only this lock is held
    # while compiling: the epoch ticker takes the cache lock every round.
    with guard:
        with p.cache_lock:
            mod = p.modules.get((metered, digest))
        if mod is not None:
            return mod
        return _module_miss(wt, engine, metered, binary, cache, digest, want is not None)


def _module_miss(
    wt: Any,
    engine: wasmtime.Engine,
    metered: bool,
    binary: Path,
    cache: Path | None,
    digest: str,
    held: bool = False,
) -> wasmtime.Module:
    flavor = "fuel" if metered else "plain"
    cwasm = None
    try:
        if cache is not None and _platform.PLATFORM.private(cache, is_dir=True):
            from . import _wasmtime_ffi as ffi

            cwasm = cache / f"{digest[:32]}-wasmtime{ffi.version()}-{flavor}.cwasm"
    except OSError:
        cwasm = None  # unusable: compiled modules are kept in this process only
    mod: wasmtime.Module | None = None
    may_write = False
    if cwasm is not None:
        mod, may_write = _load(wt, engine, cwasm)
    if mod is None:
        if held:
            data = binary.read_bytes()
            if hashlib.sha256(data).hexdigest() != digest:
                raise ArtifactsMissing(
                    f"{binary} changed after it was checked against its set's SHA256SUMS; "
                    "it is not compiled"
                )
            mod = wt.Module(engine, data)
            del data
        else:
            mod = wt.Module.from_file(engine, str(binary))
        with process().cache_lock:
            process().counts["compiled"] += 1
        if cwasm is not None and cache is not None and may_write:
            _store(mod, cache, cwasm)
    with process().cache_lock:
        process().modules[(metered, digest)] = mod
    return mod


def _file_stamp(st: os.stat_result) -> tuple[int, int, int, int]:
    return st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns


def _load(wt: Any, engine: wasmtime.Engine, cwasm: Path) -> tuple[wasmtime.Module | None, bool]:
    """The module a `.cwasm` holds, if the file is as the runner makes it and is still the file
    checked once wasmtime has read it (wasmtime-py opens the path itself, so a file swapped in
    between is discarded); and whether the runner may put its own file at that name: when there
    is none, or the one there is refused, stale or swapped, but never over a folder."""
    try:
        before = os.lstat(cwasm)
    except FileNotFoundError:
        return None, True
    except OSError:
        return None, False
    if not _platform.PLATFORM.private(cwasm, is_dir=False):
        return None, not stat.S_ISDIR(before.st_mode)  # never loaded; replaced unless a folder
    try:
        mod = wt.Module.deserialize_file(engine, str(cwasm))
    except wt.WasmtimeError:
        return None, True  # stale or foreign: compiled again and replaced
    try:
        same = _file_stamp(os.lstat(cwasm)) == _file_stamp(before)
    except OSError:
        same = False
    if not same:
        return None, True
    with process().cache_lock:
        process().counts["loaded"] += 1
    return mod, False


def _store(mod: Any, cache: Path, cwasm: Path) -> None:
    """The runner's own `.cwasm`, made 0600 under another name and renamed into place, which
    replaces a refused file or link itself, never what a link names. A cache that cannot take it
    leaves the module in this process only, with a warning; it never fails the call."""
    import warnings

    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(prefix=".cwasm-", dir=cache)  # created 0600
        with os.fdopen(fd, "wb") as f:
            f.write(mod.serialize())
        os.replace(tmp, cwasm)
    except OSError as e:
        if tmp is not None:
            Path(tmp).unlink(missing_ok=True)
        warnings.warn(
            f"wasi_python: not writing the module cache at {cwasm}: {e.strerror or e}",
            RuntimeWarning,
            stacklevel=5,
        )
        return
    except BaseException:
        if tmp is not None:
            Path(tmp).unlink(missing_ok=True)
        raise
    with process().cache_lock:
        process().counts["written"] += 1


class _epoch_ticker:
    """While at least one call with a deadline runs, one thread per process advances every
    engine's epoch once per TICK_S of wall time elapsed, catching up when a sleep runs long, so a
    deadline of n ticks ends close to n * TICK_S. Its state (the thread, the active count, the
    epochs advanced and their condition) is the process's, read through `process()`."""

    def __init__(self, engine: wasmtime.Engine | None, wanted: bool) -> None:
        self.wanted = wanted

    @classmethod
    def count(cls) -> int:
        return process().ticker_count

    def __enter__(self) -> None:
        if not self.wanted:
            return
        p = process()
        with p.ticker_cond:
            p.ticker_active += 1
            if p.ticker_thread is None:
                p.ticker_thread = threading.Thread(target=self._tick, daemon=True)
                p.ticker_thread.start()
            p.ticker_cond.notify_all()

    def __exit__(self, *exc: object) -> None:
        if not self.wanted:
            return
        p = process()
        with p.ticker_cond:
            p.ticker_active -= 1

    @classmethod
    def _tick(cls) -> None:
        p = process()
        while True:
            with p.ticker_cond:
                while p.ticker_active == 0:
                    p.ticker_cond.wait()
            start, done = time.monotonic(), 0
            while True:
                with p.ticker_cond:
                    if p.ticker_active == 0:
                        break
                due = int((time.monotonic() - start) / TICK_S)
                with p.cache_lock:
                    engines = list(p.engines.values())
                for _ in range(due - done):
                    for engine in engines:
                        engine.increment_epoch()
                    p.ticker_count += 1
                done = due
                time.sleep(TICK_S / 4)
