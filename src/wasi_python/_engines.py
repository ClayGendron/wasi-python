"""wasmtime-py's import and the two engines (spec 102 keeps the adapter import inside
`_wasmtime`), the compiled modules and the `.cwasm` cache, the module lock and the counts, the
epoch ticker (spec 015), and the preopen check's WAT module (spec 017)."""

from __future__ import annotations

import hashlib
import os
import stat
import sys
import tempfile
import threading
import time
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Any

from . import _artifacts, _platform
from ._artifacts import ArtifactsMissing
from ._limits import TICK_S
from ._platform import _WASM_STACK

if TYPE_CHECKING:
    import wasmtime
CACHE_ENV = "WASI_PYTHON_CACHE"


def _wasmtime() -> Any:
    """wasmtime-py, or one `ImportError` whatever stopped it loading (spec 028, Decision 3): not
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
    from . import _wasmtime_ffi  # noqa: F401  (spec 102: its own ImportError names what moved)

    return wt


# The identity check (Decision 5): wasmtime reports a preopen's `ino` as SipHash-1-3, zero keys,
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
_check_modules: dict[bool, Any] = {}


def _check_module(wt: Any, engine: Any, metered: bool) -> Any:
    with _lock:
        if metered not in _check_modules:
            _check_modules[metered] = wt.Module(engine, _CHECK_WAT)
        return _check_modules[metered]


def _cache_dir(given: str | os.PathLike[str] | None | bool) -> Path | None:
    if given is False:
        return None
    if given is not None and given is not True:
        return Path(given)
    if os.environ.get(CACHE_ENV):
        return Path(os.environ[CACHE_ENV])
    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Caches" / "wasi_python"
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        return (Path(base) if base else home / "AppData" / "Local") / "wasi_python" / "cache"
    base = os.environ.get("XDG_CACHE_HOME")
    return (Path(base) if base else home / ".cache") / "wasi_python"


_lock = threading.Lock()
_engines: dict[bool, wasmtime.Engine] = {}
_modules: dict[tuple[bool, str], wasmtime.Module] = {}
_counts = {"compiled": 0, "loaded": 0, "written": 0, "sessions_open": 0}


def _engine(metered: bool) -> wasmtime.Engine:
    """Two engines per process: fuel metering changes the compiled code. The async stack size
    is set first, through the seam (spec 078, Decision 1; spec 102)."""
    import wasmtime as wt

    from . import _wasmtime_ffi as ffi

    with _lock:
        if metered not in _engines:
            _platform._fork["used"] = (
                True  # before the engine exists: a fork from here on is refused
            )
            cfg = wt.Config()
            cfg.consume_fuel = metered
            cfg.epoch_interruption = True
            ffi.set_async_stack(cfg, _WASM_STACK)  # first: an 8 MiB stack without it aborts
            cfg.max_wasm_stack = _WASM_STACK
            _engines[metered] = wt.Engine(cfg)
        return _engines[metered]


def _module(
    engine: wasmtime.Engine,
    metered: bool,
    binary: Path,
    cache: Path | None,
    want: str | None = None,
) -> wasmtime.Module:
    """The compiled module: from this process, else the .cwasm cache, else compiled and cached.

    A .cwasm is native code that wasmtime runs as it finds it, so the cache is used only where no
    one else can write: on POSIX, a directory and files owned by this user and writable by no one
    else (the directory is made 0700, the files 0600). Anything else is ignored, with a warning,
    and the module is compiled in this process. `want` is a found set's checked digest (spec 087,
    Decision 10): the module is then compiled from bytes read once and held to it, and the
    .cwasm under that digest is written only from them."""
    import wasmtime as wt

    digest = want if want is not None else _artifacts._digest(binary)
    with _lock:
        mod = _modules.get((metered, digest))
        guard = _compiling.setdefault((metered, digest), threading.Lock())
    if mod is not None:
        return mod
    # One thread compiles or loads; the others wait for it (spec 011). Only this lock is held
    # while compiling: the epoch ticker takes _lock every round.
    with guard:
        with _lock:
            mod = _modules.get((metered, digest))
        if mod is not None:
            return mod
        return _module_miss(wt, engine, metered, binary, cache, digest, want is not None)


_compiling: dict[tuple[bool, str], threading.Lock] = {}


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
    mod = None
    cwasm = None
    if cache is not None and _private(cache, is_dir=True):
        from . import _wasmtime_ffi as ffi

        cwasm = cache / f"{digest[:32]}-wasmtime{ffi.version()}-{flavor}.cwasm"
    if cwasm is not None and cwasm.exists() and _private(cwasm, is_dir=False):
        try:
            mod = wt.Module.deserialize_file(engine, str(cwasm))
            with _lock:
                _counts["loaded"] += 1
        except wt.WasmtimeError:
            mod = None  # stale or foreign: compiled again below and replaced
            cwasm.unlink(missing_ok=True)
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
        with _lock:
            _counts["compiled"] += 1
        if cwasm is not None and not cwasm.exists():
            fd, tmp = tempfile.mkstemp(prefix=".cwasm-", dir=cache)  # created 0600
            try:
                with os.fdopen(fd, "wb") as f:
                    f.write(mod.serialize())
                os.replace(tmp, cwasm)
                with _lock:
                    _counts["written"] += 1
            except BaseException:
                Path(tmp).unlink(missing_ok=True)
                raise
    with _lock:
        _modules[(metered, digest)] = mod
    return mod


def _private(path: Path, *, is_dir: bool) -> bool:
    """Whether a cache path is this user's alone (POSIX); a directory is made if absent."""
    if is_dir:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name != "posix":
        return True  # the default cache is under the user's own profile
    st = os.lstat(path)
    kind_ok = stat.S_ISDIR(st.st_mode) if is_dir else stat.S_ISREG(st.st_mode)
    if kind_ok and st.st_uid == os.getuid() and not st.st_mode & 0o022:
        return True
    warnings.warn(
        f"wasi_python: not using the module cache at {path}: it must be a "
        f"{'directory' if is_dir else 'file'} owned by this user and writable by no one else",
        RuntimeWarning,
        stacklevel=5,
    )
    return False


class _epoch_ticker:
    """While at least one call with a deadline runs, one thread per process advances every
    engine's epoch once per TICK_S of wall time elapsed, catching up when a sleep runs long, so a
    deadline of n ticks ends close to n * TICK_S."""

    _active = 0
    _count = 0  # epochs advanced so far, updated after the engines are (spec 010)
    _thread: threading.Thread | None = None
    _cond = threading.Condition()

    def __init__(self, engine: wasmtime.Engine | None, wanted: bool) -> None:
        self.wanted = wanted

    @classmethod
    def count(cls) -> int:
        return cls._count

    def __enter__(self) -> None:
        if not self.wanted:
            return
        cls = type(self)
        with cls._cond:
            cls._active += 1
            if cls._thread is None:
                cls._thread = threading.Thread(target=cls._tick, daemon=True)
                cls._thread.start()
            cls._cond.notify_all()

    def __exit__(self, *exc: object) -> None:
        if not self.wanted:
            return
        with type(self)._cond:
            type(self)._active -= 1

    @classmethod
    def _tick(cls) -> None:
        while True:
            with cls._cond:
                while cls._active == 0:
                    cls._cond.wait()
            start, done = time.monotonic(), 0
            while True:
                with cls._cond:
                    if cls._active == 0:
                        break
                due = int((time.monotonic() - start) / TICK_S)
                with _lock:
                    engines = list(_engines.values())
                for _ in range(due - done):
                    for engine in engines:
                        engine.increment_epoch()
                    cls._count += 1
                done = due
                time.sleep(TICK_S / 4)
