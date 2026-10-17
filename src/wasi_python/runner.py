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
import ctypes
import errno
import hashlib
import itertools
import math
import numbers
import operator
import os
import re
import secrets
import shutil
import stat
import struct
import sys
import tempfile
import threading
import time
import warnings
from collections.abc import Callable, Iterable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

from . import Artifacts
from . import artifacts as find_artifacts

if TYPE_CHECKING:
    import concurrent.futures

    import wasmtime

ARGV0 = "/usr/local/bin/python.wasm"
NO_HOST = -1
HOST_FAULT = -2
CACHE_ENV = "WASI_PYTHON_CACHE"
TICK_S = 0.01
NO_DEADLINE = 2**62
CANCEL_TICKS = 5  # a call with `cancel` is checked every 5 ticks while it computes (spec 015)
MAX_WORKERS = 1024
MASK32 = 0xFFFFFFFF
UNMETERED = 2**63 - 1  # the budget instantiation runs on, before the cap is set (spec 008)
MAX_RESPONSE = 0x7FFFFFFF  # the largest door response: its length must fit a signed i32
# The guest's environment before the caller's `env`. HOME is added per call: a fresh, empty
# directory under /tmp that the runner removes afterwards, so nothing a call leaves in its HOME
# (pdb's .pdbrc, for one) is read by the next (spec 006, Decision 2).
BASE_ENV = {"TMPDIR": "/tmp", "PYTHONTZPATH": ""}

Host = Callable[[bytes], bytes]


LIMIT_MAX = 2**63 - 1  # wasmtime reads a memory limit as signed: 2**63 and above mean none


def _shown(value: Any) -> str:
    """A value for an error message: an integer too long to print is named by its size."""
    if isinstance(value, int) and value.bit_length() > 128:
        return f"an integer of {value.bit_length()} bits"
    return repr(value)


def _integer_limit(name: str, value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise TypeError(f"{name} must be an integer, or None; got {value!r}")
    try:
        number = operator.index(value)
    except TypeError:
        raise TypeError(f"{name} must be an integer, or None; got {value!r}") from None
    if not 0 <= number <= LIMIT_MAX:
        raise ValueError(f"{name} must be from 0 to 2**63 - 1, or None; got {_shown(number)}")
    return number


def _deadline_limit(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise TypeError(f"deadline_s must be a number of seconds, or None; got {value!r}")
    rule = "deadline_s must be finite and above 0, and at most about 4.6e16 s, or None"
    try:
        seconds = float(value)
        ticks = math.ceil(seconds / TICK_S) if seconds > 0 else 0
    except (OverflowError, ValueError):
        raise ValueError(f"{rule}; got {_shown(value)}") from None
    if not math.isfinite(seconds) or seconds <= 0 or not 0 < ticks < NO_DEADLINE:
        raise ValueError(f"{rule}; got {_shown(value)}")
    return seconds


def _check_limits(
    fuel: Any, deadline_s: Any, memory_bytes: Any, output_bytes: Any
) -> dict[str, Any]:
    """The four limits as plain values, or TypeError for a wrong type and ValueError for a value
    out of range. A negative fuel or memory cap, or a memory cap of 2**63 or more, would mean no
    limit to wasmtime, and `True` would mean 1, so none of them reaches it (spec 013)."""
    return {
        "fuel": _integer_limit("fuel", fuel),
        "deadline_s": _deadline_limit(deadline_s),
        "memory_bytes": _integer_limit("memory_bytes", memory_bytes),
        "output_bytes": _integer_limit("output_bytes", output_bytes),
    }


def _text(where: str, value: Any) -> str:
    """A plain str the guest will see exactly: no NUL, and valid UTF-8, which WASI carries.
    `str.__str__` and `str.encode` are called directly, so a subclass's overrides are ignored.
    Messages name `where`, never the value: environment values are often secrets."""
    if not isinstance(value, str):
        raise TypeError(f"{where} must be a str, not {type(value).__name__}")
    text = str.__str__(value)
    if "\0" in text:
        raise ValueError(f"{where}: embedded null byte")
    try:
        str.encode(text, "utf-8")
    except UnicodeEncodeError:
        raise ValueError(f"{where}: not valid UTF-8 (a lone surrogate)") from None
    return text


def _check_inputs(argv: Any, env: Any, stdin: Any) -> dict[str, Any]:
    """argv, env and stdin as plain values, or TypeError for a wrong type and ValueError for a
    value the guest would see differently: a NUL cut an argument or key short, and an = split a
    key, so {"HOME\\0x": ...} set HOME (spec 014)."""
    if isinstance(argv, (str, bytes, bytearray)) or not isinstance(argv, Iterable):
        raise TypeError(f"argv must be an iterable of str, not {type(argv).__name__}")
    args = [_text(f"argv[{i}]", item) for i, item in enumerate(argv)]
    plain_env = None
    if env is not None:
        if not isinstance(env, Mapping):
            raise TypeError(f"env must be a mapping of str to str, not {type(env).__name__}")
        plain_env = {}
        for key, value in env.items():
            name = _text("env key", key)
            if not name or "=" in name:
                raise ValueError("env key: illegal environment variable name")  # never quoted
            shown = name if len(name) <= 40 else name[:40] + "…"
            plain_env[name] = _text(f"env value for {shown!r}", value)
    data = None
    if stdin is not None:
        if type(stdin) is bytes:
            data = stdin  # not copied again
        else:
            try:
                data = memoryview(stdin).tobytes()
            except TypeError:
                raise TypeError(
                    f"stdin must be bytes-like, or None; got {type(stdin).__name__}"
                ) from None
    return {"argv": args, "env": plain_env, "stdin": data}


def _cpus() -> int:
    count = getattr(os, "process_cpu_count", os.cpu_count)()  # 3.13 honours CPU affinity
    return count or 1


def _default_workers() -> int:
    """At most 8: at the defaults a worker holds up to 1 GiB of guest memory and 32 MiB of output,
    so 8 bound a process at about 8.3 GiB, and past 8 the measured speedup flattens (spec 015)."""
    return min(_cpus(), 8)


def _check_workers(value: Any) -> int:
    if isinstance(value, bool):
        raise TypeError(f"async_workers must be an integer; got {value!r}")
    try:
        number = operator.index(value)
    except TypeError:
        raise TypeError(f"async_workers must be an integer; got {value!r}") from None
    if not 1 <= number <= MAX_WORKERS:
        raise ValueError(f"async_workers must be from 1 to {MAX_WORKERS}; got {_shown(number)}")
    return number


@dataclass(frozen=True)
class Defaults:
    """The limits a call has when it names none. `run` reads `DEFAULTS` at call time; the values
    are checked here, by `run`'s rules, so an error from `run` always names what its caller
    passed (spec 013). `async_workers` sizes `run_async`'s default pool (spec 015)."""

    memory_bytes: int  # the guest's linear memory
    deadline_s: float  # wall-clock time, by epoch interruption (costs nothing per instruction)
    output_bytes: int  # per stream; bytes past it are dropped and the stream named in `truncated`
    async_workers: int = field(default_factory=_default_workers)  # guests run_async runs at once

    def __post_init__(self) -> None:
        _check_limits(None, self.deadline_s, self.memory_bytes, self.output_bytes)
        _check_workers(self.async_workers)


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
    trapped: str | None  # None, "out of fuel", "deadline", "cancelled", the trap code's plain
    # name ("stack overflow"), or, for a trap without a code, its message's first line
    fuel_used: int | None  # instructions spent, when a fuel cap was given and no deadline hit
    truncated: tuple[str, ...] = ()  # the streams ("stdout", "stderr") whose output was capped


def run(
    argv: Iterable[str],
    *,
    root: str | os.PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
    stdin: bytes | bytearray | memoryview | None = None,
    host: Host | None = None,
    snapshot: bool = True,
    fuel: int | None = None,
    deadline_s: float | None = _UNSET,
    memory_bytes: int | None = _UNSET,
    output_bytes: int | None = _UNSET,
    cache_dir: str | os.PathLike[str] | None | bool = None,
    artifacts: Artifacts | None = None,
    cancel: threading.Event | None = None,
) -> Completed:
    """Run one program in a fresh instance of the runtime and return how it ended.

    `root` is the host directory the guest sees as `/`; without one, a fresh private directory is
    made and removed after the call. `memory_bytes`, `deadline_s` and `output_bytes` default to
    `DEFAULTS`; `None` means no limit. The guest's environment starts from `BASE_ENV` (`/tmp` for
    temporary files, `zoneinfo` on the zip's tzdata) and a `HOME` made fresh for the call, with
    `env` laid over it.
    `cache_dir=False` keeps compiled modules in this process only, never on disk.
    `cancel`, a `threading.Event`: once it is set and the guest runs, the guest stops within
    `CANCEL_TICKS` ticks and the call returns `trapped == "cancelled"` (spec 015)."""
    _refuse_forked()
    wt = _wasmtime()
    checked = _checked(argv, env, stdin, fuel, deadline_s, memory_bytes, output_bytes, cancel)
    return _run_checked(wt, checked, root, host, snapshot, cache_dir, artifacts)


async def run_async(
    argv: Iterable[str],
    *,
    root: str | os.PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
    stdin: bytes | bytearray | memoryview | None = None,
    host: Host | None = None,
    snapshot: bool = True,
    fuel: int | None = None,
    deadline_s: float | None = _UNSET,
    memory_bytes: int | None = _UNSET,
    output_bytes: int | None = _UNSET,
    cache_dir: str | os.PathLike[str] | None | bool = None,
    artifacts: Artifacts | None = None,
    executor: concurrent.futures.Executor | None = None,
) -> Completed:
    """`run` from async code, on a worker thread, so the event loop is never blocked (spec 015).

    The arguments are `run`'s, checked here before anything is queued. The call runs on
    `executor`, which must run callables on threads of this process, or on the runner's default
    pool of `DEFAULTS.async_workers` threads. If the awaiting task is cancelled, the guest is
    stopped and its worker freed before `CancelledError` is raised; a call still queued never
    starts."""
    import asyncio
    import contextvars

    _refuse_forked()
    checked = _checked(argv, env, stdin, fuel, deadline_s, memory_bytes, output_bytes, None)
    _check_executor(executor)
    wt = _wasmtime()
    _register_exit_hook()
    event = threading.Event()
    checked["cancel"] = event
    with _live_lock:  # the exit hook sets `exiting` before it reads `_live` (the build review, N1)
        if _hook["exiting"]:
            raise RuntimeError("cannot schedule new futures after interpreter shutdown")
        _live.add(event)
    try:
        work = contextvars.copy_context().run  # a door host sees the request's context
        args = (_run_checked, wt, checked, root, host, snapshot, cache_dir, artifacts)
        future = _submit(executor, work, *args)
        try:
            return await asyncio.wrap_future(future)
        except asyncio.CancelledError:
            if future.cancel():  # still queued: it never starts
                raise
            event.set()
            while not future.done():  # wait for the worker, whatever the call's outcome
                try:
                    await asyncio.wrap_future(future)
                except BaseException:
                    pass
            raise
    finally:
        with _live_lock:
            _live.discard(event)


def _check_executor(executor: Any) -> None:
    import concurrent.futures

    if executor is None:
        return
    interpreters = getattr(concurrent.futures, "InterpreterPoolExecutor", None)  # 3.14
    if interpreters is not None and isinstance(executor, interpreters):
        raise TypeError("executor must run on threads of this process, not an interpreter pool")
    if isinstance(executor, concurrent.futures.ProcessPoolExecutor):
        raise TypeError("executor must run on threads of this process, not a process pool")
    if not isinstance(executor, concurrent.futures.Executor):
        raise TypeError(f"executor must be a concurrent.futures.Executor; got {executor!r}")


# run_async's default pool, its live calls and its exit hook (spec 015, Decisions 4 and 6).
_pool_lock = threading.Lock()
_pool: dict[str, Any] = {"pool": None, "size": 0}
_pools: list[concurrent.futures.ThreadPoolExecutor] = []  # every default pool made, for exit
_live_lock = threading.Lock()
_live: set[threading.Event] = set()
_hook = {"registered": False, "exiting": False}


def _submit(executor: Any, fn: Callable[..., Any], *args: Any) -> concurrent.futures.Future[Any]:
    """Submit to the caller's executor, or to the default pool, resized when `DEFAULTS` changed.
    The lookup, any resize and the submit share one lock, so a resize on another thread never
    leaves a submit facing a pool that is shut down."""
    import concurrent.futures

    if executor is not None:
        return executor.submit(fn, *args)
    with _pool_lock:
        if _hook["exiting"]:  # the exit hook has run: never start a pool's call again
            raise RuntimeError("cannot schedule new futures after interpreter shutdown")
        size = DEFAULTS.async_workers
        if _pool["pool"] is None or _pool["size"] != size:
            old = _pool["pool"]
            new = concurrent.futures.ThreadPoolExecutor(size, thread_name_prefix="wasi-python")
            _pools.append(new)
            _pool.update(pool=new, size=size)
            if old is not None:
                old.shutdown(wait=False)  # its running calls finish
        return _pool["pool"].submit(fn, *args)


def _register_exit_hook() -> None:
    """At exit, stop run_async's guests and drop its queued calls. threading runs its exit hooks
    in reverse order of registration, so this one, registered after concurrent.futures.thread is
    imported, runs before that module joins the pools' workers; registered before, exit would
    wait for every queued call (spec 015's confirmation, EXECUTED both ways)."""
    with _pool_lock:
        if _hook["registered"]:
            return
        import concurrent.futures.thread  # noqa: F401  (its hook first, so ours runs before it)

        register = getattr(threading, "_register_atexit", None)
        if register is not None:
            register(_stop_async_calls)
        else:
            atexit.register(_stop_async_calls)
        _hook["registered"] = True


def _stop_async_calls() -> None:
    """Pools first, so no call can be submitted after its event was missed; then the events of the
    calls already running (spec 015's build review, F3)."""
    with _pool_lock:
        _hook["exiting"] = True
        pools = list(_pools)
    for pool in pools:
        pool.shutdown(wait=False, cancel_futures=True)
    with _live_lock:
        events = list(_live)
    for event in events:
        event.set()


# Private folders and the sweep (spec 016, Decision 2). Each private root and stdin folder has a
# lock file beside it in the temporary folder, locked for the folder's life and naming the kernel
# that made it. A process killed mid-call leaves both; the lock dies with it, so the next process
# on the same kernel can tell its folder is dead. A pid could not: pids repeat across namespaces,
# are reused, and a killed child is a zombie until reaped.
_LOCK_NAME = re.compile(r"wasi-python-(root-)?[0-9a-f]{16}\.lock\Z")
_held_lock = threading.Lock()
_held: set[str] = set()  # the names this process holds: NFS may treat flock as per-process
_sweep_state = {"claimed": False, "swept": 0}
_identity: dict[str, str | None] = {}


def _flags(*names: str) -> int:
    flags = 0
    for name in names:
        flags |= getattr(os, name, 0)
    return flags


def _kernel_identity() -> str | None:
    """Which kernel this process runs on, or None: a lock taken on one kernel is invisible to
    another that shares the folder (a VM and its host), so a sweep touches only its own."""
    if "value" not in _identity:
        value = None
        try:
            if sys.platform.startswith("linux"):
                value = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
            elif sys.platform == "darwin":
                import ctypes.util

                libc = ctypes.CDLL(ctypes.util.find_library("c"))
                size_p, void_p = ctypes.POINTER(ctypes.c_size_t), ctypes.c_void_p
                libc.sysctlbyname.argtypes = [
                    ctypes.c_char_p,
                    void_p,
                    size_p,
                    void_p,
                    ctypes.c_size_t,
                ]
                libc.sysctlbyname.restype = ctypes.c_int
                buf, size = ctypes.create_string_buffer(64), ctypes.c_size_t(64)
                name = b"kern.bootsessionuuid"
                if libc.sysctlbyname(name, buf, ctypes.byref(size), None, 0) == 0:
                    value = buf.value.decode("ascii")
            elif sys.platform == "win32":
                import winreg

                access = winreg.KEY_READ | winreg.KEY_WOW64_64KEY
                where = r"SOFTWARE\Microsoft\Cryptography"
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, where, 0, access) as key:
                    value = str(winreg.QueryValueEx(key, "MachineGuid")[0])
        except Exception:
            value = None
        _identity["value"] = value if value and "\n" not in value else None
    return _identity["value"]


_BUSY = {errno.EACCES, errno.EDEADLK, getattr(errno, "EDEADLOCK", errno.EDEADLK)}


def _try_lock(fd: int) -> bool | None:
    """Lock the open file without waiting: True when locked, False when another holder has it,
    None when this filesystem gives no lock (`ENOLCK` on NFS without a lock daemon, say)."""
    try:
        if sys.platform == "win32":
            import msvcrt

            os.lseek(fd, 0, 0)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except BlockingIOError:
        return False
    except OSError as e:
        return False if sys.platform == "win32" and e.errno in _BUSY else None


def _unlock_close(fd: int) -> None:
    """Unlock (Windows frees a closed handle's lock only after a delay), then close; quiet."""
    if sys.platform == "win32":
        try:
            import msvcrt

            os.lseek(fd, 0, 0)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
    try:
        os.close(fd)
    except OSError:
        pass


def _same_file(fd: int, path: str) -> bool:
    """Whether the open file is still the file at `path`; False when the path is gone."""
    try:
        opened, named = os.fstat(fd), os.lstat(path)
    except OSError:
        return False
    return (opened.st_dev, opened.st_ino) == (named.st_dev, named.st_ino)


class _Taken(Exception):
    pass


class _Private:
    """A private folder in the temporary folder, with `<name>.lock` beside it, held locked until
    `remove` (spec 016). The name is drawn here, as mkdtemp draws one, because the lock file must
    exist, locked, before the folder does."""

    def __init__(self, prefix: str) -> None:
        temp = tempfile.gettempdir()
        identity = _kernel_identity()
        create = _flags("O_RDWR", "O_CREAT", "O_EXCL", "O_NOFOLLOW", "O_CLOEXEC", "O_BINARY")
        for _ in range(100):
            name = prefix + secrets.token_hex(8)
            lock_path, path = os.path.join(temp, name + ".lock"), os.path.join(temp, name)
            with _held_lock:
                _held.add(name)
            try:
                fd = os.open(lock_path, create, 0o600)
            except FileExistsError:
                _drop(name)
                continue
            except BaseException:
                _drop(name)
                raise
            owns = False  # the file at lock_path is the one this call made
            try:
                locked = _try_lock(fd)
                if locked is False:
                    raise _Taken
                owns = _same_file(fd, lock_path)  # a sweeper may have removed it, still empty
                if not owns:
                    raise _Taken
                if locked and identity is not None:  # unlocked: no identity, so never swept
                    os.lseek(fd, 0, 0)
                    os.write(fd, identity.encode("ascii") + b"\n")
                os.mkdir(path, 0o700)
            except (_Taken, FileExistsError):
                _abandon(fd, lock_path if owns else None, name)
                continue
            except BaseException:
                _abandon(fd, lock_path if owns else None, name)
                raise
            self.name, self.fd, self.lock_path, self.path = name, fd, lock_path, Path(path)
            return
        raise FileExistsError(errno.EEXIST, "no usable temporary folder name found")

    def remove(self) -> None:
        """Folder, then lock (close), then the lock file only if the folder is gone, then the
        name; never raises (the 0.1.0a2 security review, F1)."""
        shutil.rmtree(self.path, ignore_errors=True)
        _unlock_close(self.fd)  # Windows cannot delete an open file
        if not os.path.lexists(self.path):
            try:
                os.unlink(self.lock_path)
            except OSError:
                pass
        _drop(self.name)


def _drop(name: str) -> None:
    with _held_lock:
        _held.discard(name)


def _abandon(fd: int, lock_path: str | None, name: str) -> None:
    _unlock_close(fd)
    if lock_path is not None:  # only a lock file this call made and still has at that name
        try:
            os.unlink(lock_path)
        except OSError:
            pass
    _drop(name)


def _sweep_once() -> None:
    """At a process's first call: remove the private folders of dead processes on this kernel.
    Claimed under `_lock`, run without it; it never raises into the call."""
    with _lock:
        if _sweep_state["claimed"]:
            return
        _sweep_state["claimed"] = True
    try:
        identity = _kernel_identity()
        if identity is None:
            return
        temp = tempfile.gettempdir()
        for entry in os.listdir(temp):
            try:
                _sweep_entry(temp, entry, identity)
            except Exception:
                continue
    except Exception:
        return


def _owned(st: os.stat_result) -> bool:
    getuid = getattr(os, "getuid", None)
    return getuid is None or st.st_uid == getuid()  # Windows: the user's own temporary folder


def _sweep_entry(temp: str, entry: str, identity: str) -> None:
    if not _LOCK_NAME.match(entry):
        return
    name = entry[: -len(".lock")]
    with _held_lock:
        if name in _held:
            return
    lock_path, path = os.path.join(temp, entry), os.path.join(temp, name)
    named = os.lstat(lock_path)
    if not stat.S_ISREG(named.st_mode) or not _owned(named):
        return
    fd = os.open(lock_path, _flags("O_RDWR", "O_NOFOLLOW", "O_NONBLOCK", "O_CLOEXEC", "O_BINARY"))
    unlink = False
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode):
            return
        if (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino):
            return
        if not _try_lock(fd):
            return  # a live call holds it
        os.lseek(fd, 0, 0)
        first = os.read(fd, 256).split(b"\n", 1)[0].decode("ascii", "replace")
        if not os.path.lexists(path):
            unlink = first in ("", identity)  # a lone lock file: nothing of a call's to lose
            return
        if first != identity:
            return  # another kernel's, or none
        folder = os.lstat(path)
        isjunction = getattr(os.path, "isjunction", lambda p: False)
        if not stat.S_ISDIR(folder.st_mode) or isjunction(path):
            return
        shutil.rmtree(path, ignore_errors=True)
        if not os.path.lexists(path):
            with _held_lock:
                _sweep_state["swept"] += 1
            unlink = True
    finally:
        # POSIX unlinks while still holding the lock, so a creator that locks the file after
        # this fails its same-file check and draws again; Windows cannot delete an open file.
        if unlink and os.name == "posix":
            _unlink_quietly(lock_path)
        _unlock_close(fd)
        if unlink and os.name != "posix":
            _unlink_quietly(lock_path)


def _unlink_quietly(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


# Fork (spec 015, Decision 5). A child of a process that made an engine inherits state from
# threads that no longer exist, and wasmtime does not support use across a fork (on macOS it
# aborts), so such a child is refused. A child of a parent that only imported this runs normally.
_fork = {"used": False, "forked": False}


def _refuse_forked() -> None:
    if _fork["forked"]:
        raise RuntimeError(
            "wasi_python was used before this process was forked; use it in the child only, or "
            "start processes with 'spawn' or 'forkserver'"
        )


def _after_fork_in_child() -> None:
    """Only assignments, and no lock: a lock may have been held by a thread the fork left out, so
    every lock the runner takes is made anew (spec 015's build review, F8)."""
    global _pool_lock, _live_lock, _lock, _epoch_callback_lock, _outputs_lock, _compiling
    global _held_lock
    _pool_lock, _live_lock, _held_lock = threading.Lock(), threading.Lock(), threading.Lock()
    _lock, _epoch_callback_lock, _outputs_lock = (
        threading.Lock(),
        threading.Lock(),
        threading.RLock(),
    )
    _compiling = {}
    _pool.update(pool=None, size=0)
    _pools.clear()
    _live.clear()
    _epoch_ticker._thread, _epoch_ticker._active = None, 0
    _epoch_ticker._cond = threading.Condition()
    if _fork["used"]:
        _fork["forked"] = True


if hasattr(os, "register_at_fork"):  # not on Windows, which has no fork
    os.register_at_fork(after_in_child=_after_fork_in_child)


def _wasmtime() -> Any:
    try:
        import wasmtime as wt
    except ImportError as e:
        raise ImportError(
            'wasi_python.run needs wasmtime-py: pip install "wasi-python[run]"'
        ) from e
    return wt


def _checked(
    argv: Any,
    env: Any,
    stdin: Any,
    fuel: Any,
    deadline_s: Any,
    memory_bytes: Any,
    output_bytes: Any,
    cancel: Any,
) -> dict[str, Any]:
    """Every argument a call's guest depends on, checked before any work (specs 013 to 015)."""
    limits = DEFAULTS
    if memory_bytes is _UNSET:
        memory_bytes = limits.memory_bytes
    if deadline_s is _UNSET:
        deadline_s = limits.deadline_s
    if output_bytes is _UNSET:
        output_bytes = limits.output_bytes
    if cancel is not None and not isinstance(cancel, threading.Event):
        raise TypeError(f"cancel must be a threading.Event, or None; got {type(cancel).__name__}")
    checked = _check_limits(fuel, deadline_s, memory_bytes, output_bytes)
    checked.update(_check_inputs(argv, env, stdin))
    checked["cancel"] = cancel
    return checked


def _run_checked(
    wt: Any,
    c: dict[str, Any],
    root: str | os.PathLike[str] | None,
    host: Host | None,
    snapshot: bool,
    cache_dir: str | os.PathLike[str] | None | bool,
    artifacts: Artifacts | None,
) -> Completed:
    found = artifacts if artifacts is not None else find_artifacts()
    binary = found.snapshot if snapshot else found.plain
    engine = _engine(c["fuel"] is not None)
    module = _module(engine, c["fuel"] is not None, binary, _cache_dir(cache_dir))
    _sweep_once()
    if root is not None:
        guest_root = Path(root)
        _place_stdlib(found, guest_root)
        return _call(wt, engine, module, found, guest_root, c, host)
    private = _Private("wasi-python-root-")  # 0700, this user's own, locked (spec 016)
    try:
        _place_private(found, private.path)
        return _call(wt, engine, module, found, private.path, c, host)
    finally:
        private.remove()


def _call(
    wt: Any,
    engine: wasmtime.Engine,
    module: wasmtime.Module,
    found: Artifacts,
    guest_root: Path,
    c: dict[str, Any],
    host: Host | None,
) -> Completed:
    """One instance, one program. The store is closed before this returns, trapped or not, so the
    guest's memory and open files are released at once (a trapped store is otherwise kept alive by
    a reference cycle until Python's collector runs) and a private root can be removed afterwards
    (Windows refuses to remove an open directory). Ctrl-C is deferred while the guest runs."""
    with _deferred_ctrl_c():
        return _call_deferred(wt, engine, module, found, guest_root, c, host)


def _call_deferred(
    wt: Any,
    engine: wasmtime.Engine,
    module: wasmtime.Module,
    found: Artifacts,
    guest_root: Path,
    c: dict[str, Any],
    host: Host | None,
) -> Completed:
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
        return _instance(wt, engine, module, store, guest_root, f"/tmp/{home}", c, host)
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
    c: dict[str, Any],
    host: Host | None,
) -> Completed:
    argv, env, stdin, cancel = c["argv"], c["env"], c["stdin"], c["cancel"]
    fuel, deadline_s = c["fuel"], c["deadline_s"]
    memory_bytes, output_bytes = c["memory_bytes"], c["output_bytes"]
    if fuel is not None:
        # Fuel is metered from the end of instantiation (spec 008): instantiation runs only
        # wasmtime's own memory fill, which it charges per byte when it cannot map the image
        # (macOS when compiled in the process, Windows always); the guest's work starts after.
        store.set_fuel(UNMETERED)
    if memory_bytes is not None:
        store.set_limits(memory_size=memory_bytes)
    ticks = NO_DEADLINE if deadline_s is None else max(1, math.ceil(deadline_s / TICK_S))
    # A call with `cancel` is first checked within CANCEL_TICKS ticks, whatever its deadline; its
    # callback then enforces the deadline too (spec 015).
    store.set_epoch_deadline(ticks if cancel is None else min(CANCEL_TICKS, ticks))
    # The ticker's count at which this store's deadline has passed, read after the deadline is set
    # (spec 010): a wait in poll_oneoff stops there, so it never outlives the deadline.
    stop_at = None if deadline_s is None else _stop_at(_epoch_ticker.count(), ticks)
    checks = [] if stop_at is None else [lambda: _epoch_ticker.count() >= stop_at]
    if cancel is not None:
        checks.append(cancel.is_set)  # a wait ends at a cancel, deadline or not
    if _ctrl_c_watched():
        checks.append(lambda: _ctrl_c["pending"])  # a wait on the main thread ends at Ctrl-C
    waits = _Waits(
        lambda: time.perf_counter(),
        time.sleep,
        (lambda: any(check() for check in checks)) if checks else None,
    )

    out, err = _Stream("stdout", output_bytes), _Stream("stderr", output_bytes)
    wasi = wt.WasiConfig()
    origin_ns = time.perf_counter_ns()  # wasmtime's monotonic clock counts from here (spec 010)
    wasi.argv = [ARGV0, *argv]
    wasi.env = sorted({**BASE_ENV, "HOME": home, **(env or {})}.items())
    wasi.preopen_dir(str(guest_root), "/")
    keys = _send_outputs(wasi, out, err)
    scratch = None
    try:
        scratch = _Private("wasi-python-")  # 0700, this user's own, locked (spec 016)
        stdin_path = scratch.path / "stdin"
        stdin_path.write_bytes(stdin or b"")
        wasi.stdin_file = str(stdin_path)
        store.set_wasi(wasi)
        linker = _linker(wt, engine)  # held for the whole call: clearing the cache cannot free it
        call = _Call(store, host, waits, origin_ns, cancel, stop_at)
        if cancel is not None:
            _watch(store)
        with _epoch_ticker(engine, deadline_s is not None or cancel is not None):
            done = _drive(wt, linker, store, module, call, fuel)
        fuel_used = _fuel_used(fuel, done, call, store.get_fuel)
    finally:
        # The store holds every descriptor the guest opened; a guest can open them until the
        # host refuses. Close it first, so the clean-up below has descriptors to work with, and
        # make that clean-up unable to raise (the 0.1.0a2 security review, F1).
        store.close()
        with _outputs_lock:  # the guest has ended; wasmtime frees the keys later, on its own thread
            for key in keys:
                _outputs.pop(key, None)
        if scratch is not None:
            scratch.remove()
    truncated = tuple(s.name for s in (out, err) if s.dropped)
    return Completed(
        done.exit_code, bytes(out.data), bytes(err.data), done.trapped, fuel_used, truncated
    )


def _fuel_used(
    fuel: int | None, done: _Driven, call: _Call, remaining: Callable[[], int]
) -> int | None:
    """The instructions the guest ran, or None when the count is meaningless: after an epoch
    interrupt wasmtime's fuel counter is not brought up to date (spec 001 landing notes), and a
    stopped call ended on one (spec 011)."""
    if fuel is None or done.trapped == "deadline":
        return None
    if call.stopped is not None or call.ended is not None:
        return None
    return fuel - remaining() if done.metered else 0


class _Driven(NamedTuple):
    exit_code: int | None
    trapped: str | None
    metered: bool  # the cap is set only once instantiation has succeeded
    instance: Any


def _drive(wt: Any, linker: Any, store: Any, module: Any, call: _Call, fuel: int | None) -> _Driven:
    """Instantiate and run the guest with its call on this thread's stack. What a host function
    caught and recorded comes first: an exit or a trap is the call's result, and any other
    exception (Ctrl-C, a host's cancellation) is raised here, on the thread that made the call
    (spec 011)."""
    exit_code: int | None = None
    trapped: str | None = None
    metered = False
    instance = None
    stack = _stack()
    stack.append(call)
    _calls.lost = False
    try:
        if call.cancel is not None and call.cancel.is_set():  # cancelled before the guest ran
            call.ended = "cancelled"
            return _Driven(None, "cancelled", False, None)
        instance = linker.instantiate(store, module)
        if fuel is not None:
            store.set_fuel(fuel)
            metered = True
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
    finally:
        stack.pop()
        lost, _calls.lost = getattr(_calls, "lost", False), False
    if lost:
        raise RuntimeError("wasi_python lost track of a call")
    cause = call.stopped
    if cause is not None:
        exit_code, trapped = None, None
        if isinstance(cause, wt.ExitTrap):
            exit_code = cause.code
        elif isinstance(cause, wt.Trap):
            trapped = _trap_name(cause)
        elif isinstance(cause, wt.WasmtimeError):
            trapped = _first_line(str(cause))
        else:
            raise cause
    elif call.ended is not None:  # the epoch callback stopped it (spec 015)
        exit_code, trapped = None, call.ended
    return _Driven(exit_code, trapped, metered, instance)


class _Call:
    """One call's state, which the shared host functions find on the calling thread's stack: its
    door, its poll_oneoff, its store's context address, and the first exception they caught; for
    a call with `cancel`, the event, the ticker count its deadline passes at, and the outcome the
    epoch callback recorded (spec 015)."""

    def __init__(
        self,
        store: Any,
        host: Host | None,
        waits: Any,
        origin_ns: int,
        cancel: threading.Event | None = None,
        stop_at: int | None = None,
    ) -> None:
        self.context = _context_address(store)
        self.door = _door(host)
        self.poll = _poll_oneoff(origin_ns, waits)
        self.stopped: BaseException | None = None
        self.cancel = cancel
        self.stop_at = stop_at
        self.ended: str | None = None  # "cancelled" or "deadline", from the epoch callback

    def stop(self, caller: Any, cause: BaseException) -> None:
        """Record the cause and stop the guest: an epoch deadline of 0, set through the caller's
        context, traps it at its next function entry, with nothing raised through wasmtime-py."""
        if self.stopped is None:
            self.stopped = cause
        from wasmtime import _ffi

        _ffi.wasmtime_context_set_epoch_deadline(caller._context(), 0)


_calls = threading.local()


def _stack() -> list[_Call]:
    stack = getattr(_calls, "stack", None)
    if stack is None:
        stack = _calls.stack = []
    return stack


def _context_address(storelike: Any) -> int:
    return ctypes.addressof(storelike._context().contents)


def _shared(kind: str, refused: int, stopped: int) -> Callable[..., int]:
    """A host function defined once per engine. It serves the call on top of this thread's
    stack, and only when the caller is that call's store; it never raises into wasmtime-py,
    whose exceptions travel by a process-wide slot (spec 011)."""

    def function(caller: Any, *args: int) -> int:
        call = None
        try:
            stack = _stack()
            call = stack[-1] if stack else None
            if call is None or _context_address(caller) != call.context:
                return refused
            if call.stopped is None and _ctrl_c_watched() and _ctrl_c["pending"]:
                _ctrl_c["pending"] = False
                raise KeyboardInterrupt
            if call.stopped is not None:
                return stopped
            answer = getattr(call, kind)(caller, *args)
            if _ctrl_c_watched() and _ctrl_c["pending"]:  # Ctrl-C during a wait
                _ctrl_c["pending"] = False
                raise KeyboardInterrupt
            if call.cancel is not None and call.cancel.is_set():
                _epoch_now(caller)  # the epoch callback names it at the guest's next entry
            return answer
        except BaseException as cause:
            try:
                if call is not None:
                    call.stop(caller, cause)
            except BaseException:
                pass
            return stopped

    return function


def _epoch_now(caller: Any) -> None:
    """An epoch deadline of 0 for the caller's store: its guest stops, or meets its epoch
    callback, at its next function entry."""
    from wasmtime import _ffi

    _ffi.wasmtime_context_set_epoch_deadline(caller._context(), 0)


def _epoch_answer(context: Any, delta: Any) -> int:
    """The epoch callback's decision for the call on top of this thread's stack, in order: a
    recorded stop holds, a deferred Ctrl-C becomes a stop, then a cancel, then the deadline;
    otherwise continue for up to CANCEL_TICKS ticks. 0 continues; an error (an int address) stops
    the guest (spec 015)."""
    call = None
    try:
        try:
            stack = _stack()
            call = stack[-1] if stack else None
            if call is not None and ctypes.addressof(context.contents) != call.context:
                call = None
        except BaseException:
            call = None
        if call is None:
            _calls.lost = True
            return _stop_error(delta)
        if call.stopped is not None:
            return _stop_error(delta)
        if _ctrl_c_watched() and _ctrl_c["pending"]:
            _ctrl_c["pending"] = False
            call.stopped = KeyboardInterrupt()
            return _stop_error(delta)
        if call.cancel is not None and call.cancel.is_set():
            call.ended = "cancelled"
            return _stop_error(delta)
        count = _epoch_ticker.count()
        if call.stop_at is not None and count >= call.stop_at:
            call.ended = "deadline"
            return _stop_error(delta)
        left = CANCEL_TICKS if call.stop_at is None else call.stop_at - count
        delta[0] = max(1, min(CANCEL_TICKS, left))
        return 0
    except BaseException as cause:
        try:
            if call is None:
                _calls.lost = True
            elif call.stopped is None:
                call.stopped = cause
        except BaseException:
            pass
        return _stop_error(delta)


def _stop_error(delta: Any) -> int:
    """A new wasmtime error, which wasmtime owns once returned. If none can be made, continue for
    one tick, never 0, so the next callback tries again (spec 015's build review, F2)."""
    try:
        from wasmtime import _ffi

        error = ctypes.cast(_ffi.wasmtime_error_new(b"stopped by wasi_python"), ctypes.c_void_p)
        if error.value:
            return error.value
    except BaseException:
        pass
    try:
        delta[0] = 1
    except BaseException:
        pass
    return 0


def _on_epoch(context: Any, data: Any, delta: Any, kind: Any) -> int:
    return _epoch_answer(context, delta)  # never writes `kind`: wasmtime panics on a bad value


_epoch_callback: Any = None  # the one C callback, made on first use
_epoch_callback_lock = threading.Lock()


def _watch(store: Any) -> None:
    """Give a store the epoch callback, with a NULL finalizer: no per-call ctypes object exists,
    and the callback finds its call through the thread's stack (spec 015)."""
    global _epoch_callback
    from wasmtime import _bindings, _ffi

    argtypes = _bindings._wasmtime_store_epoch_deadline_callback.argtypes
    with _epoch_callback_lock:  # one object for the process: a store must never outlive its own
        if _epoch_callback is None:
            _epoch_callback = argtypes[1](_on_epoch)
        callback = _epoch_callback
    _ffi.wasmtime_store_epoch_deadline_callback(store.ptr(), callback, None, argtypes[3]())


_linkers: dict[Any, Any] = {}


def _linker(wt: Any, engine: wasmtime.Engine) -> Any:
    """The engine's one linker: WASI, the shadowed poll_oneoff and the door, defined once, so a
    call adds nothing to wasmtime-py's process-wide table of host functions (spec 011)."""
    with _lock:
        linker = _linkers.get(engine)
        if linker is None:
            linker = wt.Linker(engine)
            linker.define_wasi()
            linker.allow_shadowing = True
            i32 = wt.ValType.i32()
            ty = wt.FuncType([i32] * 4, [i32])
            poll = _shared("poll", EINVAL, EINVAL)
            linker.define_func("wasi_snapshot_preview1", "poll_oneoff", ty, poll, True)
            linker.define_func("host", "call", ty, _shared("door", NO_HOST, HOST_FAULT), True)
            _linkers[engine] = linker
        return linker


# The guest's stdout and stderr, by a key that is never reused. wasmtime calls the two functions
# below on its own threads, and frees a key when it drops the stream; wasmtime-py's own table for
# custom outputs is not used, since it has no lock (spec 011).
_outputs: dict[int, _Stream] = {}
_outputs_lock = threading.RLock()  # a finalizer the collector runs inside a locked block
_output_keys = itertools.count(1)


@ctypes.CFUNCTYPE(
    ctypes.c_ssize_t, ctypes.c_void_p, ctypes.POINTER(ctypes.c_ubyte), ctypes.c_size_t
)
def _output_write(key: int | None, data: Any, size: int) -> int:
    try:
        with _outputs_lock:
            stream = _outputs.get(key or 0)
        return size if stream is None else stream.write(ctypes.string_at(data, size))
    except BaseException:
        return size  # never raises, never prints: the bytes are dropped and the write succeeds


@ctypes.CFUNCTYPE(None, ctypes.c_void_p)
def _output_free(key: int | None) -> None:
    with _outputs_lock:
        _outputs.pop(key or 0, None)


def _send_outputs(wasi: Any, out: _Stream, err: _Stream) -> tuple[int, int]:
    from wasmtime import _ffi

    with _outputs_lock:
        keys = next(_output_keys), next(_output_keys)
        _outputs[keys[0]], _outputs[keys[1]] = out, err
    _ffi.wasi_config_set_stdout_custom(wasi.ptr(), _output_write, keys[0], _output_free)
    _ffi.wasi_config_set_stderr_custom(wasi.ptr(), _output_write, keys[1], _output_free)
    return keys


# Ctrl-C while a guest runs on the main thread. Python's default handler raises KeyboardInterrupt
# wherever the main thread next runs Python, and when that is the first line of wasmtime-py's
# trampoline the exception cannot be caught and the process aborts (spec 011's review, EXECUTED:
# exit 134). So while run() holds the main thread under the default handler, Ctrl-C only sets a
# flag: the shared host functions turn it into a recorded stop, a wait ends at it, and a flag no
# host function saw is raised once the call has ended.
_ctrl_c = {"pending": False}


def _note_ctrl_c(signum: int, frame: Any) -> None:
    _ctrl_c["pending"] = True


def _ctrl_c_watched() -> bool:
    import signal

    main = threading.current_thread() is threading.main_thread()
    return main and signal.getsignal(signal.SIGINT) is _note_ctrl_c


@contextmanager
def _deferred_ctrl_c() -> Iterator[None]:
    import signal

    main = threading.current_thread() is threading.main_thread()
    if not main or signal.getsignal(signal.SIGINT) is not signal.default_int_handler:
        yield  # another thread, an embedder's own handler, or a nested call: nothing to defer
        return
    _ctrl_c["pending"] = False
    signal.signal(signal.SIGINT, _note_ctrl_c)
    try:
        yield
    finally:
        if signal.getsignal(signal.SIGINT) is _note_ctrl_c:  # a host may have set its own
            signal.signal(signal.SIGINT, signal.default_int_handler)
        pending, _ctrl_c["pending"] = _ctrl_c["pending"], False
    if pending:
        raise KeyboardInterrupt


EINVAL, ENOMEM, EBADF, EFAULT = 28, 48, 8, 21  # WASI preview1 errno values
MAX_SUBSCRIPTIONS = 4096  # one poll_oneoff's host work is bounded (spec 010)
SUBSCRIPTION = (
    "<QB7xIxxxxQQH6x"  # userdata, tag, clock id or fd, timeout, precision, flags: 48 bytes
)
EVENT = "<QHB5xQH6x"  # userdata, error, type, nbytes, flags: 32 bytes
CLOCK, FD_READ, FD_WRITE = 0, 1, 2
REALTIME, MONOTONIC = 0, 1
ABSTIME = 1


@dataclass(frozen=True)
class _Plan:
    """What one poll_oneoff answers: an errno, or the events to write after waiting wait_ns."""

    errno: int | None
    events: tuple[tuple[int, int, int, int, int], ...] = ()
    wait_ns: int = 0


def _stop_at(count: int, ticks: int) -> int:
    """The ticker's count at which a deadline of `ticks`, set when the count was `count`, has
    passed. The engine's epoch can be one round ahead of the count (the ticker advances the engines
    first), hence the + 1: a wait never ends before the epoch reaches the deadline (spec 010)."""
    return count + ticks + 1


def _poll_plan(raw: bytes, n: int, realtime_ns: int, monotonic_ns: int) -> _Plan:
    """poll_oneoff as wasmtime 49 answers it (crates/wasi/src/p1.rs), for the guest's files and
    stdio: a descriptor subscription is ready at once (stdin for writing, stdout and stderr for
    reading and the preopened root answer EBADF); otherwise the shortest clock wins, and every
    clock due by then is reported, with nbytes 0 as wasmtime writes it (spec 010)."""
    if n == 0:
        return _Plan(EINVAL)
    if n > MAX_SUBSCRIPTIONS:
        return _Plan(ENOMEM)
    ready, clocks = [], []
    for userdata, tag, which, timeout, _precision, flags in struct.iter_unpack(SUBSCRIPTION, raw):
        if tag == CLOCK:
            if which not in (REALTIME, MONOTONIC):
                return _Plan(EINVAL)
            if flags & ABSTIME:
                timeout -= realtime_ns if which == REALTIME else monotonic_ns
            clocks.append((max(0, timeout), userdata))
        elif tag in (FD_READ, FD_WRITE):
            if (
                which == 3
                or (tag == FD_READ and which in (1, 2))
                or (tag == FD_WRITE and which == 0)
            ):
                return _Plan(EBADF)
            ready.append((userdata, 0, tag, 1, 0))
        else:
            return _Plan(EINVAL)
    if ready:
        return _Plan(None, tuple(ready))
    wait_ns = min(timeout for timeout, _ in clocks)
    due = tuple((userdata, 0, CLOCK, 0, 0) for timeout, userdata in clocks if timeout <= wait_ns)
    return _Plan(None, due, wait_ns)


class _Waits:
    """A wait that the call's deadline ends: in slices of at most TICK_S while a deadline is set,
    one sleep otherwise. `now`, `sleep` and `deadline_passed` are injected so the judge counts the
    slices without measuring time (spec 010)."""

    def __init__(
        self,
        now: Callable[[], float],
        sleep: Callable[[float], None],
        deadline_passed: Callable[[], bool] | None,
    ) -> None:
        self.now, self.sleep, self.deadline_passed = now, sleep, deadline_passed

    def wait(self, seconds: float) -> None:
        if self.deadline_passed is None:
            if seconds > 0:
                self.sleep(seconds)
            return
        until = self.now() + seconds
        while (left := until - self.now()) > 0 and not self.deadline_passed():
            self.sleep(min(left, TICK_S))


def _poll_oneoff(
    origin_ns: int,
    waits: _Waits,
    realtime_ns: Callable[[], int] = time.time_ns,
    monotonic_ns: Callable[[], int] = time.perf_counter_ns,
) -> Callable[..., int]:
    """The shadowed poll_oneoff. It never raises into wasmtime-py (an exception there travels by a
    process-wide slot another call can take): a wait ended by the deadline answers normally, and
    the guest traps at its next epoch check. A BaseException goes to the shared function, which
    records it and stops the guest (spec 011). The clocks are injectable for the judge."""

    def call(caller, in_ptr: int, out_ptr: int, n: int, nevents_ptr: int) -> int:
        try:
            memory = caller.get("memory")
            in_ptr, out_ptr, n, nevents_ptr = (
                v & MASK32 for v in (in_ptr, out_ptr, n, nevents_ptr)
            )
            if n == 0 or n > MAX_SUBSCRIPTIONS:
                return EINVAL if n == 0 else ENOMEM
            size = memory.data_len(caller)
            if in_ptr + 48 * n > size or out_ptr + 32 * n > size or nevents_ptr + 4 > size:
                return EFAULT
            raw = bytes(memory.read(caller, in_ptr, in_ptr + 48 * n))
            plan = _poll_plan(raw, n, realtime_ns(), monotonic_ns() - origin_ns)
            if plan.errno is not None:
                return plan.errno
            if plan.wait_ns:
                waits.wait(plan.wait_ns / 1e9)
            events = b"".join(struct.pack(EVENT, *e) for e in plan.events)
            memory.write(caller, events, out_ptr)
            memory.write(caller, struct.pack("<I", len(plan.events)), nevents_ptr)
            return 0
        except Exception:
            return EINVAL  # anything else is recorded by the shared function (spec 011)

    return call


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
    if e.trap_code is not None:  # by its kind, not wasmtime's heading (spec 016, Decision 3)
        return _trap_code_name(e.trap_code)
    return _first_line(e.message)


def _trap_code_name(code: Any) -> str:
    """`TrapCode.STACK_OVERFLOW` is "stack overflow"."""
    return code.name.lower().replace("_", " ")


def _door(host: Host | None) -> Callable[..., int]:
    """host::call(ptr, len, out_ptr_ptr, out_len_ptr) -> 0, -1 or -2 (spec 003, Decision 5)."""

    import wasmtime as wt

    def call(caller, ptr: int, length: int, out_ptr_ptr: int, out_len_ptr: int) -> int:
        if host is None:
            return NO_HOST
        try:
            return frame(caller, ptr, length, out_ptr_ptr, out_len_ptr)
        except (wt.Trap, wt.WasmtimeError):
            raise  # a trap or exit inside host_alloc: the shared function records it (spec 011)
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
    """Free the cached linkers, modules and engines while wasmtime's bindings still exist."""
    _linkers.clear()
    _modules.clear()
    _engines.clear()


def _engine(metered: bool) -> wasmtime.Engine:
    """Two engines per process: fuel metering changes the compiled code."""
    import wasmtime as wt

    with _lock:
        if metered not in _engines:
            _fork["used"] = True  # before the engine exists: a fork from here on is refused
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
        return _module_miss(wt, engine, metered, binary, cache, digest)


_compiling: dict[tuple[bool, str], threading.Lock] = {}


def _module_miss(
    wt: Any, engine: wasmtime.Engine, metered: bool, binary: Path, cache: Path | None, digest: str
) -> wasmtime.Module:
    flavor = "fuel" if metered else "plain"
    mod = None
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
        stacklevel=5,
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
    _count = 0  # epochs advanced so far, updated after the engines are (spec 010)
    _thread: threading.Thread | None = None
    _cond = threading.Condition()

    def __init__(self, engine: wasmtime.Engine, wanted: bool) -> None:
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
