"""The runner: one program, one call (spec 001, Decision 3).

    from wasi_python import run

    done = run(["-c", "import pandas; print(pandas.__version__)"])
    done.exit_code, done.stdout

It does what any embedder does: preopen a directory at `/`, bind the one custom import
(`host::call`), and call the reactor's exports. wasmtime-py (the `run` extra) is imported only
here, when a call is made.

It is safe by default (spec 006): a call that names no root gets a fresh private one, removed
afterwards; a call that names no limit still has one for memory, time and output (`DEFAULTS`);
and nothing a guest frame or a host function does makes `run` raise.
"""

from __future__ import annotations

import atexit
import hashlib
import math
import os
import secrets
import shutil
import stat
import struct
import sys
import tempfile
import threading
import time
import warnings
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from . import Artifacts
from . import artifacts as find_artifacts

if TYPE_CHECKING:
    import wasmtime

ARGV0 = "/usr/local/bin/python.wasm"
NO_HOST = -1
HOST_FAULT = -2
CACHE_ENV = "WASI_PYTHON_CACHE"
TICK_S = 0.01
NO_DEADLINE = 2**62
MASK32 = 0xFFFFFFFF
UNMETERED = 2**63 - 1  # the most fuel a store takes: instantiation runs on it (spec 008)
MAX_RESPONSE = 0x7FFFFFFF  # the largest door response: its length must fit a signed i32
# The guest's environment before the caller's `env`. HOME is added per call: a fresh, empty
# directory under /tmp that the runner removes afterwards, so nothing a call leaves in its HOME
# (pdb's .pdbrc, for one) is read by the next (spec 006, Decision 2).
BASE_ENV = {"TMPDIR": "/tmp", "PYTHONTZPATH": ""}

Host = Callable[[bytes], bytes]


@dataclass(frozen=True)
class Defaults:
    """The limits a call has when it names none. `run` reads `DEFAULTS` at call time."""

    memory_bytes: int  # the guest's linear memory
    deadline_s: float  # wall-clock time, by epoch interruption (costs nothing per instruction)
    output_bytes: int  # per stream; bytes past it are dropped and the stream named in `truncated`


DEFAULTS = Defaults(memory_bytes=1 << 30, deadline_s=60.0, output_bytes=16 << 20)


class _Unset:
    def __repr__(self) -> str:
        return "<default>"


_UNSET: Any = _Unset()


@dataclass(frozen=True)
class Completed:
    """How one program ended."""

    exit_code: int | None  # run's return value or proc_exit's code; None when it trapped
    stdout: bytes
    stderr: bytes
    trapped: str | None  # None, "out of fuel", "deadline", or the trap's first line
    fuel_used: int | None  # instructions spent, when a fuel cap was given and no deadline hit
    truncated: tuple[str, ...] = ()  # the streams ("stdout", "stderr") whose output was capped


def run(
    argv: list[str],
    *,
    root: str | os.PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
    stdin: bytes | None = None,
    host: Host | None = None,
    snapshot: bool = True,
    fuel: int | None = None,
    deadline_s: float | None = _UNSET,
    memory_bytes: int | None = _UNSET,
    output_bytes: int | None = _UNSET,
    cache_dir: str | os.PathLike[str] | None | bool = None,
    artifacts: Artifacts | None = None,
) -> Completed:
    """Run one program in a fresh instance of the runtime and return how it ended.

    `root` is the host directory the guest sees as `/`; without one, a fresh private directory is
    made and removed after the call. `memory_bytes`, `deadline_s` and `output_bytes` default to
    `DEFAULTS`; `None` means no limit. The guest's environment starts from `BASE_ENV` (`/tmp` for
    temporary files, `zoneinfo` on the zip's tzdata) and a `HOME` made fresh for the call, with
    `env` laid over it.
    `cache_dir=False` keeps compiled modules in this process only, never on disk."""
    try:
        import wasmtime as wt
    except ImportError as e:
        raise ImportError(
            'wasi_python.run needs wasmtime-py: pip install "wasi-python[run]"'
        ) from e

    limits = DEFAULTS
    if memory_bytes is _UNSET:
        memory_bytes = limits.memory_bytes
    if deadline_s is _UNSET:
        deadline_s = limits.deadline_s
    if output_bytes is _UNSET:
        output_bytes = limits.output_bytes

    found = artifacts if artifacts is not None else find_artifacts()
    binary = found.snapshot if snapshot else found.plain
    engine = _engine(fuel is not None)
    module = _module(engine, fuel is not None, binary, _cache_dir(cache_dir))
    if root is not None:
        guest_root = Path(root)
        _place_stdlib(found, guest_root)
        return _call(
            wt,
            engine,
            module,
            found,
            guest_root,
            argv,
            env,
            stdin,
            host,
            fuel,
            deadline_s,
            memory_bytes,
            output_bytes,
        )
    guest_root = Path(tempfile.mkdtemp(prefix="wasi-python-root-"))  # 0700, this user's own
    try:
        _place_private(found, guest_root)
        return _call(
            wt,
            engine,
            module,
            found,
            guest_root,
            argv,
            env,
            stdin,
            host,
            fuel,
            deadline_s,
            memory_bytes,
            output_bytes,
        )
    finally:
        shutil.rmtree(guest_root, ignore_errors=True)


def _call(
    wt: Any,
    engine: wasmtime.Engine,
    module: wasmtime.Module,
    found: Artifacts,
    guest_root: Path,
    argv: list[str],
    env: Mapping[str, str] | None,
    stdin: bytes | None,
    host: Host | None,
    fuel: int | None,
    deadline_s: float | None,
    memory_bytes: int | None,
    output_bytes: int | None,
) -> Completed:
    """One instance, one program. The store is closed before this returns, trapped or not, so the
    guest's memory and open files are released at once (a trapped store is otherwise kept alive by
    a reference cycle until Python's collector runs) and a private root can be removed afterwards
    (Windows refuses to remove an open directory)."""
    tmp = _real_dir(guest_root, ("tmp",))  # TMPDIR; a guest's link there is removed
    home = f".home-{secrets.token_hex(16)}"
    # The fresh HOME is made, and removed, through a handle on /tmp opened without following a
    # link, so a guest running concurrently on the same root cannot turn /tmp into a link between
    # the check and the mkdir (Windows has no dir_fd, and its guests cannot make links).
    tmp_fd = _open_dir(tmp)
    try:
        if tmp_fd is not None:
            os.mkdir(home, dir_fd=tmp_fd)
        else:
            (tmp / home).mkdir()
    except BaseException:
        _close(tmp_fd)
        raise
    store = wt.Store(engine)
    try:
        return _instance(
            wt,
            engine,
            module,
            store,
            guest_root,
            f"/tmp/{home}",
            argv,
            env,
            stdin,
            host,
            fuel,
            deadline_s,
            memory_bytes,
            output_bytes,
        )
    finally:
        store.close()
        if tmp_fd is not None:
            shutil.rmtree(home, ignore_errors=True, dir_fd=tmp_fd)
        else:
            shutil.rmtree(tmp / home, ignore_errors=True)
        _close(tmp_fd)


def _open_dir(path: Path) -> int | None:
    """A handle on a directory, opened without following a link; None where the platform has no
    dir_fd support (Windows)."""
    if os.mkdir not in os.supports_dir_fd or shutil.rmtree.avoids_symlink_attacks is False:
        return None
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    return os.open(path, flags)


def _close(fd: int | None) -> None:
    if fd is not None:
        os.close(fd)


def _instance(
    wt: Any,
    engine: wasmtime.Engine,
    module: wasmtime.Module,
    store: wasmtime.Store,
    guest_root: Path,
    home: str,
    argv: list[str],
    env: Mapping[str, str] | None,
    stdin: bytes | None,
    host: Host | None,
    fuel: int | None,
    deadline_s: float | None,
    memory_bytes: int | None,
    output_bytes: int | None,
) -> Completed:
    if fuel is not None:
        # Fuel is metered from the end of instantiation (spec 008): instantiation runs only
        # wasmtime's own memory fill, which it charges per byte when it cannot map the image
        # (macOS when compiled in the process, Windows always); the guest's work starts after.
        store.set_fuel(UNMETERED)
    if memory_bytes is not None:
        store.set_limits(memory_size=memory_bytes)
    ticks = NO_DEADLINE if deadline_s is None else max(1, math.ceil(deadline_s / TICK_S))
    store.set_epoch_deadline(ticks)

    out, err = _Stream("stdout", output_bytes), _Stream("stderr", output_bytes)
    wasi = wt.WasiConfig()
    wasi.argv = [ARGV0, *argv]
    wasi.env = sorted({**BASE_ENV, "HOME": home, **(env or {})}.items())
    wasi.preopen_dir(str(guest_root), "/")
    wasi.stdout_custom = out.write
    wasi.stderr_custom = err.write
    with tempfile.TemporaryDirectory(prefix="wasi-python-") as scratch:
        stdin_path = Path(scratch) / "stdin"
        stdin_path.write_bytes(stdin or b"")
        wasi.stdin_file = str(stdin_path)
        store.set_wasi(wasi)
        linker = wt.Linker(engine)
        linker.define_wasi()
        i32 = wt.ValType.i32()
        door = _door(host)
        linker.define_func("host", "call", wt.FuncType([i32] * 4, [i32]), door, True)

        exit_code: int | None = None
        trapped: str | None = None
        with _epoch_ticker(engine, deadline_s is not None):
            try:
                instance = linker.instantiate(store, module)
                if fuel is not None:
                    store.set_fuel(fuel)
                exports = instance.exports(store)
                if "_initialize" in exports:
                    exports["_initialize"](store)
                exit_code = exports["run"](store)
            except wt.ExitTrap as e:
                exit_code = e.code
            except wt.Trap as e:
                trapped = _trap_name(e)
            except wt.WasmtimeError as e:
                trapped = _first_line(str(e))
    # After an epoch interrupt wasmtime's fuel counter is not brought up to date, so the count is
    # meaningless then (spec 001 landing notes).
    counted = fuel is not None and trapped != "deadline"
    fuel_used = fuel - store.get_fuel() if counted else None
    truncated = tuple(s.name for s in (out, err) if s.dropped)
    return Completed(exit_code, bytes(out.data), bytes(err.data), trapped, fuel_used, truncated)


class _Stream:
    """A guest's stdout or stderr, kept up to a cap. Bytes past it are dropped, never buffered,
    and still reported as written, so the guest's write succeeds and is not retried (wasmtime-py
    takes the callback's return value as the count written)."""

    def __init__(self, name: str, cap: int | None) -> None:
        self.name, self.cap, self.data, self.dropped = name, cap, bytearray(), False

    def write(self, data: bytes) -> int:
        room = len(data) if self.cap is None else max(0, self.cap - len(self.data))
        if room < len(data):
            self.dropped = True
        self.data.extend(data[:room])
        return len(data)


def _first_line(text: str) -> str:
    lines = text.strip().splitlines()
    return lines[0] if lines else "trap"


def _trap_name(e: wasmtime.Trap) -> str:
    import wasmtime as wt

    if e.trap_code == wt.TrapCode.OUT_OF_FUEL:
        return "out of fuel"
    if e.trap_code == wt.TrapCode.INTERRUPT:
        return "deadline"
    return _first_line(e.message)


def _door(host: Host | None) -> Callable[..., int]:
    """host::call(ptr, len, out_ptr_ptr, out_len_ptr) -> 0, -1 or -2 (spec 003, Decision 5)."""

    import wasmtime as wt

    def call(caller, ptr: int, length: int, out_ptr_ptr: int, out_len_ptr: int) -> int:
        if host is None:
            return NO_HOST
        try:
            return frame(caller, ptr, length, out_ptr_ptr, out_len_ptr)
        except (wt.Trap, wt.WasmtimeError):
            raise  # a deadline or fuel running out inside host_alloc ends the run as anywhere
        except Exception:
            return HOST_FAULT  # nothing a frame or a host does escapes run() (spec 006)

    def frame(caller, ptr: int, length: int, out_ptr_ptr: int, out_len_ptr: int) -> int:
        memory, alloc = caller.get("memory"), caller.get("host_alloc")
        if memory is None or alloc is None:
            return HOST_FAULT
        ptr, length = ptr & MASK32, length & MASK32  # i32 values: addresses are unsigned
        out_ptr_ptr, out_len_ptr = out_ptr_ptr & MASK32, out_len_ptr & MASK32
        size = memory.data_len(caller)
        if ptr + length > size or out_ptr_ptr + 4 > size or out_len_ptr + 4 > size:
            return HOST_FAULT  # memory.read would clamp a frame that runs past memory
        response = host(bytes(memory.read(caller, ptr, ptr + length)))
        if not isinstance(response, (bytes, bytearray, memoryview)):
            return HOST_FAULT
        if memoryview(response).nbytes > MAX_RESPONSE:
            return HOST_FAULT  # checked in bytes, before the copy
        response = bytes(response)
        p = alloc(caller, len(response)) & MASK32
        if not p or p + len(response) > memory.data_len(caller):
            return HOST_FAULT
        memory.write(caller, response, p)
        memory.write(caller, struct.pack("<I", p), out_ptr_ptr)
        memory.write(caller, struct.pack("<I", len(response)), out_len_ptr)
        return 0

    return call


def _place_stdlib(found: Artifacts, root: Path) -> None:
    """The artifact set's own zip at /usr/local/lib/python3XY.zip: the snapshot runs only beside
    the zip it was built against.

    The root is the guest's to write, so nothing in it is trusted: the zip is a copy (never a link
    to the artifact itself), no symbolic link the guest left on the way to it is followed, and a
    file that is not byte for byte the artifact's zip is replaced, by renaming a fresh copy over
    it. On POSIX a copy this process placed is recognised by its inode and change time, which a
    guest cannot set back, when the filesystem keeps sub-second times; otherwise the file is
    hashed."""
    lib = _real_dir(root, ("usr", "local", "lib"))
    dest = lib / f"python{_version_tag(found.manifest)}.zip"
    want = _digest(found.stdlib_zip)
    # Calls in this process place one root's zip one at a time: on Windows a file being renamed
    # over cannot be opened, so a second call checking it mid-rename would fail.
    with _lock:
        guard = _placing.setdefault(str(dest), threading.Lock())
    with guard:
        _place_checked(found, dest, want)


_placing: dict[str, threading.Lock] = {}


def _place_private(found: Artifacts, root: Path) -> None:
    """The zip in a private root this call made: a plain copy, recorded in no cache, so a process
    making many calls without a root does not grow `_placed` or `_placing`."""
    lib = root / "usr" / "local" / "lib"
    lib.mkdir(parents=True)
    shutil.copyfile(found.stdlib_zip, lib / f"python{_version_tag(found.manifest)}.zip")


def _place_checked(found: Artifacts, dest: Path, want: str) -> None:
    lib = dest.parent
    try:
        st = os.lstat(dest)
    except FileNotFoundError:
        st = None
    if st is not None and stat.S_ISDIR(st.st_mode):
        shutil.rmtree(dest)  # a guest's directory in the zip's place; links inside are not followed
        st = None
    if st is not None and stat.S_ISREG(st.st_mode):
        # A filesystem with whole-second times cannot show a write within the same second.
        fine_times = st.st_ctime_ns % 1_000_000_000 != 0
        if os.name == "posix" and fine_times and _placed.get(str(dest)) == _stamp(st):
            return
        if _hash_file(dest) == want:
            _placed[str(dest)] = _stamp(st)
            return
    fd, tmp = tempfile.mkstemp(prefix=".python-zip-", dir=lib)
    try:
        with os.fdopen(fd, "wb") as out, found.stdlib_zip.open("rb") as src:
            for block in iter(lambda: src.read(1 << 20), b""):
                out.write(block)
        os.chmod(tmp, 0o644)
        try:
            os.replace(tmp, dest)  # replaces a link at dest itself, never what it points to
        except PermissionError:
            # Windows cannot rename over a file another call's guest has open; when that file
            # is already the right zip (a concurrent call placed it), this copy is not needed.
            if os.name != "nt":
                raise
            st = os.lstat(dest)
            if not (stat.S_ISREG(st.st_mode) and _hash_file(dest) == want):
                raise
            Path(tmp).unlink(missing_ok=True)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    _placed[str(dest)] = _stamp(os.lstat(dest))


_placed: dict[str, tuple[int, ...]] = {}


def _stamp(st: os.stat_result) -> tuple[int, ...]:
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def _real_dir(root: Path, parts: tuple[str, ...]) -> Path:
    """root/parts…, each a real directory: a link or file a guest left in the way is removed."""
    root.mkdir(parents=True, exist_ok=True)
    here = root
    for part in parts:
        here = here / part
        try:
            st = os.lstat(here)
        except FileNotFoundError:
            st = None
        if st is not None and not stat.S_ISDIR(st.st_mode):
            here.unlink()  # a symbolic link or a file: removed, never followed
            st = None
        if st is None:
            try:
                here.mkdir()
            except FileExistsError:  # a concurrent call made it
                if not stat.S_ISDIR(os.lstat(here).st_mode):
                    raise
    return here


def _hash_file(path: Path) -> str:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    h = hashlib.sha256()
    with os.fdopen(os.open(path, flags), "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


_versions: dict[Path, str] = {}


def _version_tag(manifest: Path) -> str:
    """'315' from MANIFEST's `python 3.15.0` line: the stdlib zip's guest name is python315.zip."""
    if manifest not in _versions:
        for line in manifest.read_text().splitlines():
            if line.startswith("python "):
                major, minor = line.split()[1].split(".")[:2]
                _versions[manifest] = f"{major}{minor}"
                break
        else:
            raise ValueError(f"{manifest} has no python line")
    return _versions[manifest]


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
_digests: dict[tuple[str, int, int], str] = {}
_counts = {"compiled": 0, "loaded": 0, "written": 0}


def stats() -> dict[str, int]:
    """How this process got its compiled modules: compiled from the binary, loaded from a .cwasm,
    and .cwasm files written. A diagnostic; the judge's cache check reads it."""
    with _lock:
        return dict(_counts)


@atexit.register
def _release() -> None:
    """Free the cached modules and engines while wasmtime's bindings still exist."""
    _modules.clear()
    _engines.clear()


def _engine(metered: bool) -> wasmtime.Engine:
    """Two engines per process: fuel metering changes the compiled code."""
    import wasmtime as wt

    with _lock:
        if metered not in _engines:
            cfg = wt.Config()
            cfg.consume_fuel = metered
            cfg.epoch_interruption = True
            _engines[metered] = wt.Engine(cfg)
        return _engines[metered]


def _digest(path: Path) -> str:
    st = path.stat()
    key = (str(path.resolve()), st.st_size, st.st_mtime_ns)
    if key not in _digests:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for block in iter(lambda: f.read(1 << 20), b""):
                h.update(block)
        _digests[key] = h.hexdigest()
    return _digests[key]


def _module(
    engine: wasmtime.Engine, metered: bool, binary: Path, cache: Path | None
) -> wasmtime.Module:
    """The compiled module: from this process, else the .cwasm cache, else compiled and cached.

    A .cwasm is native code that wasmtime runs as it finds it, so the cache is used only where no
    one else can write: on POSIX, a directory and files owned by this user and writable by no one
    else (the directory is made 0700, the files 0600). Anything else is ignored, with a warning,
    and the module is compiled in this process."""
    import wasmtime as wt

    digest = _digest(binary)
    with _lock:
        mod = _modules.get((metered, digest))
    if mod is not None:
        return mod
    flavor = "fuel" if metered else "plain"
    cwasm = None
    if cache is not None and _private(cache, is_dir=True):
        cwasm = cache / f"{digest[:32]}-wasmtime{_wasmtime_version()}-{flavor}.cwasm"
    if cwasm is not None and cwasm.exists() and _private(cwasm, is_dir=False):
        try:
            mod = wt.Module.deserialize_file(engine, str(cwasm))
            with _lock:
                _counts["loaded"] += 1
        except wt.WasmtimeError:
            mod = None  # stale or foreign: compiled again below and replaced
            cwasm.unlink(missing_ok=True)
    if mod is None:
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
        stacklevel=4,
    )
    return False


def _wasmtime_version() -> str:
    from importlib.metadata import version

    return version("wasmtime")


class _epoch_ticker:
    """While at least one call with a deadline runs, one thread per process advances every
    engine's epoch once per TICK_S of wall time elapsed, catching up when a sleep runs long, so a
    deadline of n ticks ends close to n * TICK_S."""

    _active = 0
    _thread: threading.Thread | None = None
    _cond = threading.Condition()

    def __init__(self, engine: wasmtime.Engine, wanted: bool) -> None:
        self.wanted = wanted

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
                done = due
                time.sleep(TICK_S / 4)
