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
from collections.abc import Callable
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
            "wasi_python.run needs wasmtime-py (wasmtime>=50,<51), which installs with "
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


def _cache_given(given: str | os.PathLike[str] | None | bool) -> str | bool | None:
    """`cache_dir` as the call names it, checked when the call is made. An empty string names
    no folder (an unset variable read as empty, say) and is refused. A folder, and the one
    `$WASI_PYTHON_CACHE` names when `None` or `True` defers to it, is made absolute against the
    working folder of this moment, so the folder judged is the folder used whatever a later
    `chdir` does."""
    if given is None or given is True:
        named = os.environ.get(CACHE_ENV)
        return os.path.abspath(named) if named else given
    if given is False:
        return False
    path = os.fspath(given)
    if path == "":
        raise ValueError(
            "cache_dir must be a folder, True, False or None; an empty string names none"
        )
    return os.path.abspath(path)


def _cache_dir(given: str | os.PathLike[str] | None | bool) -> Path | None:
    if given is False:
        return None
    if given is not None and given is not True:
        return Path(given)
    if os.environ.get(CACHE_ENV):
        return Path(os.path.abspath(os.environ[CACHE_ENV]))
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
    runner makes it: on POSIX, a directory at 0700 and files at 0600 with one name and no access
    list, owned by this user, on a way of folders no other user can change, and read through
    the descriptor that was checked; on Windows, no link or junction, held open from its check
    to its load. Anything else is ignored, with a warning, and the module is compiled in this
    process; a refused file is replaced by the runner's own. That stops a file a guest makes,
    not one it rewrites in place: the guard is that the grant judge lets no guest reach any
    cache. `want` is a found set's checked digest; else the digest is the binary's as hashed
    now. Either way the module is compiled from bytes read once and held to it, so the .cwasm
    under that digest is written only from them."""
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
    held: bool | None,
    *,
    lstat: Callable[[str], os.stat_result] = os.lstat,
    reopen: Callable[..., int] = os.open,
) -> wasmtime.Module:
    """The module loaded from the cache, else compiled, cached and counted. `held` says what
    `digest` is: True, the set's checked digest; False, the binary's hash taken for this call;
    None, a key the caller names itself, for which what is read is compiled as it is. `lstat`
    is the walk of the way to the cache, `reopen` the open that tries a descriptor's name."""
    flavor = "fuel" if metered else "plain"
    cwasm = None
    try:
        folder = None if cache is None else _platform.PLATFORM.cache_folder(cache, lstat=lstat)
        if folder is not None:
            from . import _wasmtime_ffi as ffi

            cwasm = folder / f"{digest[:32]}-wasmtime{ffi.version()}-{flavor}.cwasm"
    except OSError as e:
        cwasm = None  # unusable: compiled modules are kept in this process only
        _cache_warning(f"not using the module cache at {cache}", e)
    mod: wasmtime.Module | None = None
    may_write = False
    if cwasm is not None:
        mod, may_write = _load(wt, engine, cwasm, reopen)
    if mod is None:
        mod = _compile(wt, engine, binary, digest, held)
        with process().cache_lock:
            process().counts["compiled"] += 1
        if cwasm is not None and may_write:
            _store(mod, cwasm.parent, cwasm)
    with process().cache_lock:
        process().modules[(metered, digest)] = mod
    return mod


def _compile(
    wt: Any, engine: wasmtime.Engine, binary: Path, digest: str, held: bool | None
) -> wasmtime.Module:
    """The module compiled from one read of `binary`, whose bytes must hash to `digest` unless
    `held` is None, a key the caller names itself, never the binary's: a file changed between
    its hash and its compile is never compiled, so it is never cached under a digest it does not
    have. wasmtime-py's own `from_file` reads the whole
    file too; the hash is one pass over bytes already in memory."""
    data = binary.read_bytes()
    if held is not None and hashlib.sha256(data).hexdigest() != digest:
        what = (
            "changed after it was checked against its set's SHA256SUMS"
            if held
            else "changed while it was read"
        )
        raise ArtifactsMissing(f"{binary} {what}; it is not compiled")
    mod: wasmtime.Module = wt.Module(engine, data)
    return mod


def _file_stamp(st: os.stat_result) -> tuple[int, int, int, int]:
    return st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns


def _load(
    wt: Any, engine: wasmtime.Engine, cwasm: Path, reopen: Callable[..., int] = os.open
) -> tuple[wasmtime.Module | None, bool]:
    """The module a `.cwasm` holds, if the file is as the runner makes it, read through the open
    file the runner checked: wasmtime opens the name of the checked descriptor, so a file put at
    the path after the check is not the file loaded. Where wasmtime is given the path instead
    (Windows, which holds the file open meanwhile, or a system with no name for a descriptor),
    the name's stamp is checked again after the load. And whether the runner may put its own
    file at that name: when there is none, or the one there is refused, stale or swapped, but
    never over a folder. A file that goes away meanwhile is a miss, never a failure."""
    try:
        before = os.lstat(cwasm)
    except FileNotFoundError:
        return None, True
    except OSError:
        return None, False
    try:
        opened = _platform.PLATFORM.open_cached(cwasm, reopen=reopen)
    except OSError:
        return None, False
    if opened is None:
        return None, not stat.S_ISDIR(before.st_mode)  # never loaded; replaced unless a folder
    try:
        if _file_stamp(os.fstat(opened.fd)) != _file_stamp(before):
            return None, True  # another file since its name was read
        try:
            mod = wt.Module.deserialize_file(engine, opened.name)
        except (wt.WasmtimeError, OSError):
            return None, True  # stale or foreign: compiled again and replaced
        if opened.by_path and not _same_stamp(cwasm, before):
            return None, True
    finally:
        opened.close()
    with process().cache_lock:
        process().counts["loaded"] += 1
    return mod, False


def _same_stamp(path: Path, before: os.stat_result) -> bool:
    try:
        return _file_stamp(os.lstat(path)) == _file_stamp(before)
    except OSError:
        return False


def _cache_warning(what: str, error: OSError) -> None:
    """The embedder's one sign that a module stays in memory because its cache is unusable."""
    import warnings

    warnings.warn(f"wasi_python: {what}: {error.strerror or error}", RuntimeWarning, stacklevel=6)


def _store(mod: Any, cache: Path, cwasm: Path) -> None:
    """The runner's own `.cwasm`, made 0600 under another name and renamed into place, which
    replaces a refused file or link itself, never what a link names. A cache that cannot take it
    leaves the module in this process only, with a warning; it never fails the call."""

    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(prefix=".cwasm-", dir=cache)  # created 0600
        with os.fdopen(fd, "wb") as f:
            f.write(mod.serialize())
        os.replace(tmp, cwasm)
    except OSError as e:
        if tmp is not None:
            Path(tmp).unlink(missing_ok=True)
        _cache_warning(f"not writing the module cache at {cwasm}", e)
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
