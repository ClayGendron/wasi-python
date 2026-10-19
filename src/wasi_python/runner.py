"""The runner: one program, one call (spec 001, Decision 3).

    from wasi_python import run

    done = run(["-c", "import pandas; print(pandas.__version__)"])
    done.exit_code, done.stdout

It does what any embedder does: preopen a directory at `/`, bind the one custom import
(`host::call`), and call the reactor's exports. wasmtime-py (a dependency of the package since
spec 028) is imported only here, when a call is made, so `import wasi_python` and `artifacts()`
still work where it cannot load.

It is safe by default (spec 006): a call that names no root has no `/` and nothing writable
(spec 025; `root=True` makes a fresh private one, removed afterwards); a call that names no
limit still has one for memory, time and output (`DEFAULTS`); and nothing a guest frame or a
host function does makes `run` raise.
"""

from __future__ import annotations

import atexit
import collections
import contextvars
import ctypes
import errno
import functools
import hashlib
import io
import itertools
import math
import ntpath
import numbers
import operator
import os
import queue
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
import weakref
import zipfile
import zlib
from collections.abc import Callable, Iterable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

from . import Artifacts
from . import artifacts as find_artifacts
from .mounts import METHODS, STAGING_CEILING, FileRecord, Mount

if TYPE_CHECKING:
    import concurrent.futures

    import wasmtime

    from .tools import Tool, ToolCall, ToolRecord, _ToolHost

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
    return _seconds_limit("deadline_s", value)


def _seconds_limit(name: str, value: Any) -> float | None:
    """`deadline_s`'s rule, named for its argument (spec 055, Decision 9: idle_s, lifetime_s)."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise TypeError(f"{name} must be a number of seconds, or None; got {value!r}")
    rule = f"{name} must be finite and above 0, and at most about 4.6e16 s, or None"
    try:
        seconds = float(value)
        ticks = math.ceil(seconds / TICK_S) if seconds > 0 else 0
    except (OverflowError, ValueError):
        raise ValueError(f"{rule}; got {_shown(value)}") from None
    if not math.isfinite(seconds) or seconds <= 0 or not 0 < ticks < NO_DEADLINE:
        raise ValueError(f"{rule}; got {_shown(value)}")
    return seconds


def _shutdown_limit(name: str, value: Any) -> float:
    """A session's shutdown budget in seconds: finite and at least 0; 0 skips the shutdown, and
    `None` is refused, since the runner itself starts endings and must bound them (spec 055,
    Decision 8)."""
    if value is None or isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise TypeError(f"{name} must be a number of seconds, 0 or more; got {value!r}")
    rule = f"{name} must be finite and 0 or more, and at most about 4.6e16 s"
    try:
        seconds = float(value)
        ticks = math.ceil(seconds / TICK_S) if seconds > 0 else 0
    except (OverflowError, ValueError):
        raise ValueError(f"{rule}; got {_shown(value)}") from None
    if not math.isfinite(seconds) or seconds < 0 or not 0 <= ticks < NO_DEADLINE:
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
    """The limits a call has when it names none: `defaults()` returns the ones in force, and
    `set_defaults()` replaces them.

    The values are checked here by `run`'s own rules, so an error from `run` always names what
    its caller passed. Each limit but `async_workers` takes `None` for no limit.

    Attributes:
        memory_bytes: The most linear memory a guest may hold, in bytes.
        deadline_s: The wall-clock seconds a call may run, enforced by epoch interruption,
            which costs nothing per instruction.
        output_bytes: The most bytes kept per stream; bytes past it are dropped and the stream
            is named in `truncated`.
        async_workers: How many guests `run_async`'s own pool runs at once; by default the CPU
            count, at most 8.
        file_calls: The most provider calls a call with mounts makes; then it ends "out of file
            calls".
        tool_calls: The most tool-protocol frames a call with tools answers; past it the guest
            gets `ToolBudgetExceeded`.
        tool_request_bytes: The most bytes of tool-protocol requests a call with tools reads,
            counted from each frame's length before it is read; a frame that would pass it is
            refused unread, and the guest gets `ToolBudgetExceeded`.
        open_files: The most files and folders a guest holds open at once, in grants, the root
            and mounts alike; past it an open answers `EMFILE` and the guest runs on.
        session_idle_s: The longest a `Session` may rest between turns before it ends "idle".
        session_lifetime_s: How long after its opening a `Session`'s turns may run; then it
            ends "lifetime".
        session_shutdown_s: The seconds a `Session`'s ending has to run Python's shutdown
            (`atexit` handlers, then finalization); past them the session is simply stopped.
            0 skips the shutdown; it cannot be `None`.
    """

    # Checked by run's rules (spec 013); async_workers sizes run_async's pool (spec 015).
    memory_bytes: int | None
    deadline_s: float | None
    output_bytes: int | None
    async_workers: int = field(default_factory=_default_workers)
    file_calls: int | None = 10_000
    tool_calls: int | None = 1000
    tool_request_bytes: int | None = 16 << 20  # spec 060
    open_files: int | None = 1024  # spec 068
    session_idle_s: float | None = 900.0  # spec 055, the owner's decision 20
    session_lifetime_s: float | None = 3600.0
    session_shutdown_s: float = 5.0  # jupyter_client's shutdown_wait_time (spec 055, Decision 8)

    def __post_init__(self) -> None:
        _check_limits(None, self.deadline_s, self.memory_bytes, self.output_bytes)
        _check_workers(self.async_workers)
        _integer_limit("file_calls", self.file_calls)
        _integer_limit("tool_calls", self.tool_calls)
        _integer_limit("tool_request_bytes", self.tool_request_bytes)
        _integer_limit("open_files", self.open_files)
        _seconds_limit("session_idle_s", self.session_idle_s)
        _seconds_limit("session_lifetime_s", self.session_lifetime_s)
        _shutdown_limit("session_shutdown_s", self.session_shutdown_s)


DEFAULTS = Defaults(memory_bytes=1 << 30, deadline_s=60.0, output_bytes=16 << 20)


def _current_defaults() -> Defaults:
    """The defaults a call reads, once, when it is made (spec 049, Decision 2). The binding stays
    this module's `DEFAULTS`, which `wasi_python.set_defaults` replaces under its lock."""
    return DEFAULTS


class _Unset:
    def __repr__(self) -> str:
        return "<default>"


_UNSET: Any = _Unset()


@dataclass(frozen=True)
class Completed:
    """How one program ended: what `run` returns.

    Attributes:
        exit_code: The program's exit status: its return value, or the code it passed to exit.
            `None` when it trapped.
        stdout: What the guest wrote to standard output, up to the output limit.
        stderr: What the guest wrote to standard error, up to the output limit.
        trapped: `None` when the program ended by itself. Otherwise one of four fixed strings,
            "out of fuel", "deadline", "cancelled" or "out of file calls", or wasmtime's words:
            a trap's plain name ("stack overflow"), or an error's first line. The four strings
            are promised; wasmtime's words are not.
        fuel_used: The guest's instructions spent, when a `fuel` cap was given and no deadline
            hit; else `None`.
        truncated: The streams ("stdout", "stderr") whose output passed the limit.
        files: For a call with mounts, its provider calls, faults and refused writes; else
            `None`.
        tools: For a call with tools, every frame counted and the first 1,000 listed; else
            `None`.
    """

    exit_code: int | None
    stdout: bytes
    stderr: bytes
    trapped: str | None
    fuel_used: int | None
    truncated: tuple[str, ...] = ()
    files: FileRecord | None = None  # spec 032
    tools: ToolRecord | None = None  # spec 036


@dataclass(frozen=True)
class Grant:
    """A host folder the guest sees at a guest path, read-only unless `writable=True`.

    A grant may be nested in another; `run` checks every grant before any work.

    Attributes:
        host: The host folder, a str or os.PathLike[str].
        guest: Where the guest sees it: an absolute guest path, not / and not the runtime's
            own /usr/local/lib.
        writable: Whether the guest may write there. Keyword-only.
    """

    # spec 017
    host: str | os.PathLike[str]
    guest: str
    writable: bool = field(default=False, kw_only=True)


def run(
    argv: Iterable[str],
    *,
    root: str | os.PathLike[str] | bool | None = False,
    grants: Iterable[Grant] = (),
    mounts: Iterable[Mount] = (),
    import_path: Iterable[str] = (),
    env: Mapping[str, str] | None = None,
    stdin: bytes | bytearray | memoryview | None = None,
    host: Callable[[bytes], bytes | bytearray | memoryview] | None = None,
    snapshot: bool = True,
    fuel: int | None = None,
    deadline_s: float | None = _UNSET,
    memory_bytes: int | None = _UNSET,
    output_bytes: int | None = _UNSET,
    cache_dir: str | os.PathLike[str] | None | bool = None,
    artifacts: Artifacts | None = None,
    cancel: threading.Event | None = None,
    max_file_calls: int | None = _UNSET,
    tools: Iterable[Tool | Callable[..., Any]] | None = None,
    gate: Callable[[ToolCall], Any] | None = None,
    max_tool_calls: int | None = _UNSET,
    max_tool_request_bytes: int | None = _UNSET,
    max_open_files: int | None = _UNSET,
) -> Completed:
    """Run one program in a fresh instance of the runtime and return how it ended.

    The guest sees no host folder but the read-only stdlib, and what `root`, `grants` and
    `mounts` give it. Every argument is checked before any work. A call that names no limit has
    the ones `defaults()` returns, read once, when the call is made. Nothing a guest does, and
    no `Exception` a provider, a tool or a gate raises, makes `run` raise: a provider's `OSError`
    may be its answer (the README's *Mounts*), and the rest are recorded in the result. A new
    failure is raised as one of the types below, or a subclass of one;
    messages may change.

    Args:
        argv: The guest's arguments after the program's name, as for `python`: `["-c", code]`,
            `["script.py"]` or `["-m", "module"]`.
        root: The host folder the guest sees as /, writable, made if missing. `False` or
            `None` (the default) gives no / and nothing writable; `True` gives a fresh private
            folder, removed after the call.
        grants: Host folders the guest sees at their guest paths, each a `Grant`, read-only
            unless it says `writable=True`. The stdlib zip is always granted, read-only, at
            /usr/local/lib.
        mounts: Providers whose files the guest sees at their guest paths, each a `Mount`,
            served from your code, read-only unless it says `writable=True`.
        import_path: Guest paths put on the guest's `sys.path` after the stdlib zip, in order:
            each a folder or a zip file inside a read-only grant. The root, a writable grant or
            a mount may not serve one, no writable grant or mount may lie under one, and no
            writable grant or root may lie inside the grant serving one.
        env: Environment variables laid over the guest's own: TMPDIR=/tmp, PYTHONTZPATH=
            empty (zoneinfo reads the zip's tzdata), and a HOME made fresh for the call where
            /tmp is writable.
        stdin: The guest's standard input, whole; `None` is empty.
        host: The door's host function: called with each request's bytes, it returns the
            response's. It must answer synchronously: an async one raises `TypeError`. Excludes
            `tools`.
        snapshot: `True` runs the snapshot binary, with the stdlib's bootstrap imported (no
            package); `False` the plain reactor.
        fuel: A cap on the guest's executed instructions; past it the call ends "out of
            fuel". `None` (the default) sets no cap.
        deadline_s: Wall-clock seconds; past them the call ends "deadline". Default:
            `defaults().deadline_s`, 60. `None` means no limit.
        memory_bytes: The most linear memory the guest may hold, in bytes. Default:
            `defaults().memory_bytes`, 1 GiB. `None` means no limit.
        output_bytes: The most bytes kept per stream; the rest are dropped and the stream
            named in `truncated`. Default: `defaults().output_bytes`, 16 MiB. `None` means no
            limit.
        cache_dir: Where compiled modules are kept as .cwasm files, a folder only you can
            write. `None` or `True` uses `$WASI_PYTHON_CACHE`, else the user's cache folder;
            `False` keeps them in this process only, never on disk.
        artifacts: The artifact set to run; `None` finds it with `artifacts()`.
        cancel: A `threading.Event`. Once it is set and the guest runs, the guest stops
            within 5 ticks of 10 ms while it computes, and the call ends "cancelled".
        max_file_calls: The most provider calls a call with mounts makes; then it ends "out
            of file calls". Default: `defaults().file_calls`, 10,000. `None` means no limit.
        tools: Host functions offered to the guest through the tool protocol (`from host
            import tools`), each a `wasi_python.tools.Tool` or a plain function, which goes
            through `tool()`. A tool may be async (an `async def`, or a function returning an
            awaitable): it is awaited on the event loop that awaits `run_async`, or, under
            `run`, on a loop of the call's own; it never starts once its call has been answered,
            and is cancelled when its call ends. Excludes `host`.
        gate: Called with a `ToolCall` before each tool runs. It allows by returning `None`
            or `True`, and refuses by returning `False` or raising `ToolDenied`. It may be
            async, as a tool may. Needs `tools`.
        max_tool_calls: The most tool-protocol frames a call answers; the guest gets
            `ToolBudgetExceeded` for the rest. Default: `defaults().tool_calls`, 1,000. `None`
            means no limit. Needs `tools`.
        max_tool_request_bytes: The most bytes of tool-protocol requests a call reads, counted
            from each frame's length before it is read, whatever its answer; a frame that would
            pass it is refused unread, and the guest gets `ToolBudgetExceeded` and runs on.
            Default: `defaults().tool_request_bytes`, 16 MiB. `None` means no limit. Needs
            `tools`.
        max_open_files: The most files and folders the guest holds open at once, in grants,
            the root and mounts alike; past it an open answers `EMFILE` and the guest runs on.
            0 refuses every open, the stdlib's included. It protects your process only within
            the process's own soft descriptor limit. Default: `defaults().open_files`, 1,024.
            `None` means no limit.

    Returns:
        How the program ended.

    Raises:
        TypeError: An argument has the wrong type; raised before any work.
        ValueError: An argument is out of range; raised before any work.
        ArtifactsMissing: There is no usable artifact set.
        ImportError: wasmtime-py cannot load; its own error is chained as the cause.
        OSError: A host filesystem call failed while the root, the private folders, the zip's
            copy or the cache was prepared (its subclasses, such as FileExistsError, included).
        RuntimeError: This process was forked after it ran a guest; a folder or the zip's
            copy changed between the runner's check and its use; or, on Linux, a handler
            installed or removed after the first run (faulthandler, `signal.signal`, a native
            crash reporter) replaced wasmtime's trap handlers, so a guest trap would end the
            process; raised before the guest runs.
        wasmtime.WasmtimeError: Today, for a folder removed between the runner's check and
            wasmtime's own open. The type is wasmtime-py's and is not promised.
        KeyboardInterrupt: Ctrl-C.
        BaseException: One that is not an `Exception`, raised by your own host, provider, tool
            or gate, propagates.
    """
    # Defaults: spec 013; roots: spec 025; grants: spec 017; mounts: specs 032 and 034;
    # cancel: spec 015; tools: spec 036; exceptions written down by spec 049, Decision 6.
    _refuse_forked()
    wt = _wasmtime()
    checked = _checked(
        argv,
        env,
        stdin,
        fuel,
        deadline_s,
        memory_bytes,
        output_bytes,
        cancel,
        host=host,
        tools=tools,
        gate=gate,
        max_tool_calls=max_tool_calls,
        max_tool_request_bytes=max_tool_request_bytes,
        root=root,
        grants=grants,
        mounts=mounts,
        max_file_calls=max_file_calls,
        import_path=import_path,
        max_open_files=max_open_files,
    )
    return _run_checked(wt, checked, host, snapshot, cache_dir, artifacts)


async def run_async(
    argv: Iterable[str],
    *,
    root: str | os.PathLike[str] | bool | None = False,
    grants: Iterable[Grant] = (),
    mounts: Iterable[Mount] = (),
    import_path: Iterable[str] = (),
    env: Mapping[str, str] | None = None,
    stdin: bytes | bytearray | memoryview | None = None,
    host: Callable[[bytes], bytes | bytearray | memoryview] | None = None,
    snapshot: bool = True,
    fuel: int | None = None,
    deadline_s: float | None = _UNSET,
    memory_bytes: int | None = _UNSET,
    output_bytes: int | None = _UNSET,
    cache_dir: str | os.PathLike[str] | None | bool = None,
    artifacts: Artifacts | None = None,
    executor: concurrent.futures.Executor | None = None,
    max_file_calls: int | None = _UNSET,
    tools: Iterable[Tool | Callable[..., Any]] | None = None,
    gate: Callable[[ToolCall], Any] | None = None,
    max_tool_calls: int | None = _UNSET,
    max_tool_request_bytes: int | None = _UNSET,
    max_open_files: int | None = _UNSET,
) -> Completed:
    """`run` from async code, on a worker thread, so the event loop is never blocked.

    The arguments are `run`'s, without `cancel`, plus `executor`; they are checked, and the
    defaults read, before anything is queued. If the awaiting task is cancelled, the guest is
    stopped and its worker freed before `asyncio.CancelledError` is raised; a call still queued
    never starts. A mount's provider runs on the worker thread, never the event loop's; a tool
    runs on a thread of its own.

    Args:
        argv: The guest's arguments after the program's name, as for `python`: `["-c", code]`,
            `["script.py"]` or `["-m", "module"]`.
        root: The host folder the guest sees as /, writable, made if missing. `False` or
            `None` (the default) gives no / and nothing writable; `True` gives a fresh private
            folder, removed after the call.
        grants: Host folders the guest sees at their guest paths, each a `Grant`, read-only
            unless it says `writable=True`. The stdlib zip is always granted, read-only, at
            /usr/local/lib.
        mounts: Providers whose files the guest sees at their guest paths, each a `Mount`,
            served from your code, read-only unless it says `writable=True`.
        import_path: Guest paths put on the guest's `sys.path` after the stdlib zip, in order:
            each a folder or a zip file inside a read-only grant. The root, a writable grant or
            a mount may not serve one, no writable grant or mount may lie under one, and no
            writable grant or root may lie inside the grant serving one.
        env: Environment variables laid over the guest's own: TMPDIR=/tmp, PYTHONTZPATH=
            empty (zoneinfo reads the zip's tzdata), and a HOME made fresh for the call where
            /tmp is writable.
        stdin: The guest's standard input, whole; `None` is empty.
        host: The door's host function: called with each request's bytes, it returns the
            response's. It must answer synchronously: an async one raises `TypeError`. Excludes
            `tools`.
        snapshot: `True` runs the snapshot binary, with the stdlib's bootstrap imported (no
            package); `False` the plain reactor.
        fuel: A cap on the guest's executed instructions; past it the call ends "out of
            fuel". `None` (the default) sets no cap.
        deadline_s: Wall-clock seconds; past them the call ends "deadline". Default:
            `defaults().deadline_s`, 60. `None` means no limit.
        memory_bytes: The most linear memory the guest may hold, in bytes. Default:
            `defaults().memory_bytes`, 1 GiB. `None` means no limit.
        output_bytes: The most bytes kept per stream; the rest are dropped and the stream
            named in `truncated`. Default: `defaults().output_bytes`, 16 MiB. `None` means no
            limit.
        cache_dir: Where compiled modules are kept as .cwasm files, a folder only you can
            write. `None` or `True` uses `$WASI_PYTHON_CACHE`, else the user's cache folder;
            `False` keeps them in this process only, never on disk.
        artifacts: The artifact set to run; `None` finds it with `artifacts()`.
        executor: Where the call runs: a `concurrent.futures.Executor` that runs callables
            on threads of this process (a process or interpreter pool is refused). `None` (the
            default) uses the runner's own pool of `defaults().async_workers` threads.
        max_file_calls: The most provider calls a call with mounts makes; then it ends "out
            of file calls". Default: `defaults().file_calls`, 10,000. `None` means no limit.
        tools: Host functions offered to the guest through the tool protocol (`from host
            import tools`), each a `wasi_python.tools.Tool` or a plain function, which goes
            through `tool()`. A tool may be async (an `async def`, or a function returning an
            awaitable): it is awaited on the event loop that awaits `run_async`, or, under
            `run`, on a loop of the call's own; it never starts once its call has been answered,
            and is cancelled when its call ends. Excludes `host`.
        gate: Called with a `ToolCall` before each tool runs. It allows by returning `None`
            or `True`, and refuses by returning `False` or raising `ToolDenied`. It may be
            async, as a tool may. Needs `tools`.
        max_tool_calls: The most tool-protocol frames a call answers; the guest gets
            `ToolBudgetExceeded` for the rest. Default: `defaults().tool_calls`, 1,000. `None`
            means no limit. Needs `tools`.
        max_tool_request_bytes: The most bytes of tool-protocol requests a call reads, counted
            from each frame's length before it is read, whatever its answer; a frame that would
            pass it is refused unread, and the guest gets `ToolBudgetExceeded` and runs on.
            Default: `defaults().tool_request_bytes`, 16 MiB. `None` means no limit. Needs
            `tools`.
        max_open_files: The most files and folders the guest holds open at once, in grants,
            the root and mounts alike; past it an open answers `EMFILE` and the guest runs on.
            0 refuses every open, the stdlib's included. It protects your process only within
            the process's own soft descriptor limit. Default: `defaults().open_files`, 1,024.
            `None` means no limit.

    Returns:
        How the program ended.

    Raises:
        TypeError: An argument has the wrong type; raised before any work.
        ValueError: An argument is out of range; raised before any work.
        ArtifactsMissing: There is no usable artifact set.
        ImportError: wasmtime-py cannot load; its own error is chained as the cause.
        OSError: A host filesystem call failed while the root, the private folders, the zip's
            copy or the cache was prepared (its subclasses, such as FileExistsError, included).
        RuntimeError: This process was forked after it ran a guest; the interpreter is shutting
            down; a folder or the zip's copy changed between the runner's check and its use; or,
            on Linux, a handler installed or removed after the first run replaced wasmtime's trap
            handlers (as `run`).
        wasmtime.WasmtimeError: Today, for a folder removed between the runner's check and
            wasmtime's own open. The type is wasmtime-py's and is not promised.
        asyncio.CancelledError: The awaiting task was cancelled; the guest was stopped and its
            worker freed first.
        BaseException: One that is not an `Exception`, raised by your own host, provider, tool
            or gate, propagates.
    """
    # spec 015
    import asyncio
    import contextvars

    _refuse_forked()
    checked = _checked(
        argv,
        env,
        stdin,
        fuel,
        deadline_s,
        memory_bytes,
        output_bytes,
        None,
        host=host,
        tools=tools,
        gate=gate,
        max_tool_calls=max_tool_calls,
        max_tool_request_bytes=max_tool_request_bytes,
        root=root,
        grants=grants,
        mounts=mounts,
        max_file_calls=max_file_calls,
        import_path=import_path,
        max_open_files=max_open_files,
    )
    _check_executor(executor)
    checked["tool_loop"] = asyncio.get_running_loop()  # async tools await here (spec 053)
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
        args = (_run_checked, wt, checked, host, snapshot, cache_dir, artifacts)
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
    """Submit to the caller's executor, or to the default pool, made anew when
    `async_workers` changed. The pool's size is process state, not a call's limit: it is read
    here, under the pool's lock, so the newest `set_defaults` always wins and a call that read
    its limits earlier never sizes the pool back (spec 049, the build review's F3). The lookup,
    any resize and the submit share one lock, so a resize on another thread never leaves a
    submit facing a pool that is shut down."""
    import concurrent.futures

    if executor is not None:
        return executor.submit(fn, *args)
    with _pool_lock:
        if _hook["exiting"]:  # the exit hook has run: never start a pool's call again
            raise RuntimeError("cannot schedule new futures after interpreter shutdown")
        size = _current_defaults().async_workers
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
_LOCK_NAME = re.compile(r"wasi-python-(root-|zip-)?[0-9a-f]{16}\.lock\Z")  # zip-: spec 017
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
    global _held_lock, _zip_lock, _zips, _tool_threads_lock
    global _sessions_lock, _sessions, _reaper_queue, _closers_lock
    _pool_lock, _live_lock, _held_lock = threading.Lock(), threading.Lock(), threading.Lock()
    # A child has none of its parent's tool threads (spec 036, Decision 8).
    _tool_threads_lock, _tool_threads["running"] = threading.Lock(), 0
    _zip_lock, _zips = threading.Lock(), {}  # the parent's zip folders stay the parent's
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
    # A child has no reaper, no sessions and none open (spec 055, Decision 13).
    _sessions_lock, _sessions = threading.Lock(), weakref.WeakSet()
    _reaper_queue, _closers_lock = queue.SimpleQueue(), threading.Lock()
    _closers.clear()
    _dropped.clear()
    _reaper.update(thread=None, stop=False, hooked=_reaper["hooked"])
    _counts["sessions_open"] = 0
    if _fork["used"]:
        _fork["forked"] = True


if hasattr(os, "register_at_fork"):  # not on Windows, which has no fork
    os.register_at_fork(after_in_child=_after_fork_in_child)


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
    *,
    host: Any = None,
    tools: Any = None,
    gate: Any = None,
    max_tool_calls: Any = _UNSET,
    max_tool_request_bytes: Any = _UNSET,
    root: Any = False,
    grants: Any = (),
    mounts: Any = (),
    max_file_calls: Any = _UNSET,
    import_path: Any = (),
    max_open_files: Any = _UNSET,
    limits: Defaults | None = None,
) -> dict[str, Any]:
    """Every argument a call's guest depends on, checked before any work (specs 013 to 015,
    and 036 for the tools). The defaults are read once, here, and every check that takes one
    takes it from this read, so a `set_defaults` on another thread never gives a call a mix of
    the old and new limits (spec 049, Decision 2). `async_workers` is not a call's limit:
    `_submit` reads it under the pool's lock. A session passes the `limits` it read (spec 055)."""
    limits = limits if limits is not None else _current_defaults()
    tool_args = _check_tools(
        host, tools, gate, max_tool_calls, limits, max_tool_request_bytes=max_tool_request_bytes
    )
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
    checked.update(tool_args)
    checked.update(
        _check_places(
            root,
            grants,
            mounts,
            max_file_calls,
            limits,
            import_path=import_path,
            max_open_files=max_open_files,
        )
    )
    return checked


def _is_async_callable(fn: Any) -> bool:
    """Whether calling `fn` makes a coroutine or an async generator, read through `partial`s and
    at an object's `__call__`, as `tool()` reads a tool (spec 053, Decision 9). It does not
    import `wasi_python.tools`."""
    import functools
    import inspect

    while isinstance(fn, functools.partial):
        fn = fn.func
    tests = (inspect.iscoroutinefunction, inspect.isasyncgenfunction)
    if any(test(fn) for test in tests):
        return True
    if not (inspect.isfunction(fn) or inspect.ismethod(fn)):
        if not callable(fn):
            return False
        call = type(fn).__call__
        return any(test(call) for test in tests)
    return False


def _check_tools(
    host: Any,
    tools: Any,
    gate: Any,
    max_tool_calls: Any,
    limits: Defaults | None = None,
    *,
    max_tool_request_bytes: Any = _UNSET,
) -> dict[str, Any]:
    """tools=, gate= and max_tool_calls= as plain values (spec 036, Decision 1): a tuple of
    `Tool`s with unique names, a gate that is not an async generator function, the frame limit,
    and spec 060's byte budget (with tools= only: a call without tools keeps its three keys). A
    plain function goes through `tool()`. `wasi_python.tools` is imported only when tools are
    given, so `import wasi_python` still does not import it. An async `host=` is
    refused (spec 053, Decision 9)."""
    if host is not None and _is_async_callable(host):
        raise TypeError(
            "host= must answer synchronously; serve an async host function as a tool (tools=)"
        )
    if tools is None:
        if gate is not None:
            raise TypeError(
                "gate= without tools= gates nothing: the raw door has no gate; pass tools="
            )
        if max_tool_calls is not _UNSET:
            raise TypeError(
                "max_tool_calls= without tools= limits nothing: the raw door has no limit; "
                "pass tools="
            )
        if max_tool_request_bytes is not _UNSET:
            raise TypeError(
                "max_tool_request_bytes= without tools= limits nothing: the raw door has no "
                "limit; pass tools="
            )
        return {"tools": None, "gate": None, "tool_calls": None}
    if host is not None:
        raise TypeError("pass host= for the raw door or tools= for the tool protocol, not both")
    from .tools import Tool, _is_async_generator, tool

    if (
        isinstance(tools, (str, bytes, bytearray, Mapping, Tool))
        or callable(tools)
        or not isinstance(tools, Iterable)
    ):
        raise TypeError(
            f"tools must be an iterable of Tool or functions, not {type(tools).__name__}"
        )
    checked: list[Tool] = []
    names: set[str] = set()
    for i, item in enumerate(tools):
        if not isinstance(item, Tool):
            if not callable(item):
                raise TypeError(
                    f"tools[{i}] must be a Tool or a function, not {type(item).__name__}"
                )
            item = tool(item)
        if item.name in names:
            raise ValueError(f"tools[{i}]: another tool is named {item.name!r}")
        names.add(item.name)
        checked.append(item)
    if gate is not None and not callable(gate):
        raise TypeError(f"gate must be a callable, or None; got {type(gate).__name__}")
    if gate is not None and _is_async_generator(gate):
        raise TypeError("gate is an async generator function; a gate answers each call once")
    if max_tool_calls is _UNSET or max_tool_request_bytes is _UNSET:
        limits = limits or _current_defaults()  # one read, whichever is unset
    if max_tool_calls is _UNSET:
        max_tool_calls = limits.tool_calls
    if max_tool_request_bytes is _UNSET:
        max_tool_request_bytes = limits.tool_request_bytes
    return {
        "tools": tuple(checked),
        "gate": gate,
        "tool_calls": _integer_limit("max_tool_calls", max_tool_calls),
        "tool_request_bytes": _integer_limit("max_tool_request_bytes", max_tool_request_bytes),
    }


# Grants (spec 017). A grant is a host folder the guest sees at a guest path, read-only unless it
# says `writable=True`. Every host path, `root` included, is walked one component at a time from
# `/`, judging each link on the way, and every rule compares identities (device and inode), never
# spellings: macOS folders are case-insensitive, and Windows spells one folder many ways. wasmtime
# then opens each path itself, so before the guest runs a check module of the runner's own reads
# back each preopen's identity and compares it with the walk's (Decision 5).
ZIP_GUEST = "/usr/local/lib"
MAX_LINKS = 40
_M64 = (1 << 64) - 1


def _host_path(where: str, value: Any) -> str:
    if isinstance(value, (bytes, bytearray)):
        raise TypeError(f"{where} must be a str or os.PathLike[str], not bytes")
    try:
        path = os.fspath(value)
    except TypeError:
        raise TypeError(
            f"{where} must be a str or os.PathLike[str], not {type(value).__name__}"
        ) from None
    if not isinstance(path, str):
        raise TypeError(f"{where} must be a str or os.PathLike[str], not a path of bytes")
    path = _text(where, path)
    if not path:
        raise ValueError(f"{where} is empty")
    return path


def _guest_path(where: str, value: Any) -> str:
    """An absolute guest path with no empty, `.` or `..` component and no trailing `/`, which
    wasi-libc would otherwise match by text alone (memo §7d); not `/` and not the runtime's."""
    if not isinstance(value, str):
        raise TypeError(f"{where}: the guest path must be a str, not {type(value).__name__}")
    path = _text(f"{where}: the guest path", value)
    if not path.startswith("/"):
        raise ValueError(f"{where}: the guest path must be absolute; got {path!r}")
    if path == "/":
        raise ValueError(f"{where}: the guest path / is the root; pass root= instead")
    if any(part in ("", ".", "..") for part in path.split("/")[1:]):
        raise ValueError(
            f"{where}: the guest path {path!r} has an empty, '.' or '..' part, or ends in '/'"
        )
    if path == ZIP_GUEST or path.startswith(ZIP_GUEST + "/"):
        raise ValueError(f"{where}: {path!r} is the runtime's own ({ZIP_GUEST})")
    return path


def _check_root(root: Any) -> str | bool | None:
    """The root as the runner keeps it: a host path; None for a private root (`root=True`); or
    False for none, the default (spec 025: nothing writable unless the embedder asks)."""
    if root is None or root is False:
        return False
    if root is True:
        return None
    return _host_path("root", root)


def _check_grants(grants: Any) -> tuple[Grant, ...]:
    """The grants as a tuple of plain `Grant`s, so `run_async` hands its worker no used iterator."""
    if isinstance(grants, (str, bytes, bytearray, Grant)) or not isinstance(grants, Iterable):
        raise TypeError(f"grants must be an iterable of Grant, not {type(grants).__name__}")
    checked: list[Grant] = []
    seen: set[str] = set()
    for i, grant in enumerate(grants):
        if not isinstance(grant, Grant):
            raise TypeError(f"grants[{i}] must be a Grant, not {type(grant).__name__}")
        guest = _guest_path(f"grants[{i}]", grant.guest)
        where = f"grants[{i}] at {guest}"
        if type(grant.writable) is not bool:
            raise TypeError(f"{where}: writable must be True or False, not {grant.writable!r}")
        if guest in seen:
            raise ValueError(f"{where}: another grant has the same guest path")
        seen.add(guest)
        checked.append(
            Grant(_host_path(f"{where}: host", grant.host), guest, writable=grant.writable)
        )
    return tuple(checked)


def _check_places(
    root: Any,
    grants: Any,
    mounts: Any,
    max_file_calls: Any,
    limits: Defaults,
    *,
    import_path: Any = (),
    max_open_files: Any = _UNSET,
) -> dict[str, Any]:
    """root, grants, mounts, the import path, the file-call limit and the cap on open files,
    checked together before any work: a mount may share no guest path with a grant, and a mount
    at / comes with no root (spec 032); each import-path entry is served by a read-only grant
    (spec 054); the cap applies to every call, with or without places (spec 068)."""
    checked_root = _check_root(root)
    checked_grants = _check_grants(grants)
    checked_mounts = _check_mounts(mounts, checked_grants, checked_root)
    entries, serving = _check_import_path(import_path, checked_grants, checked_mounts, checked_root)
    if max_file_calls is _UNSET:
        max_file_calls = limits.file_calls
    if max_open_files is _UNSET:
        max_open_files = limits.open_files
    return {
        "root": checked_root,
        "grants": checked_grants,
        "mounts": checked_mounts,
        "import_path": entries,
        "import_serving": serving,
        "file_calls": _integer_limit("max_file_calls", max_file_calls),
        "open_files": _integer_limit("max_open_files", max_open_files),
    }


def _under(path: str, place: str) -> bool:
    """`path` is at or below `place` by whole components, as wasi-libc matches a preopen; never
    by text alone (`/code2` is not under `/code`)."""
    return place == "/" or path == place or path.startswith(place + "/")


def _check_import_path(
    import_path: Any, grants: tuple[Grant, ...], mounts: tuple[Mount, ...], root: Any
) -> tuple[tuple[str, ...], tuple[int, ...]]:
    """The import path's entries, as the plain strings `_guest_path` returns (never the caller's
    objects, which the prelude is built from), and for each the index of the read-only grant that
    serves it; or TypeError for a type and ValueError for a value (spec 054, Decisions 2 to 4).
    The place serving an entry is the one with the longest guest prefix, as wasi-libc resolves
    it, and must be a read-only grant; no writable grant and no mount may lie under an entry."""
    if isinstance(import_path, (str, bytes, bytearray)) or not isinstance(import_path, Iterable):
        raise TypeError(f"import_path must be an iterable of str, not {type(import_path).__name__}")
    # Every place a path can resolve to: (guest path, what it is, its index, writable).
    places: list[tuple[str, str, int, bool]] = [
        (g.guest, "grants", i, g.writable) for i, g in enumerate(grants)
    ]
    places += [(m.guest, "mounts", i, m.writable) for i, m in enumerate(mounts)]
    if root is not False:  # a host path or a private root: always writable, at /
        places.append(("/", "root", -1, True))
    entries: list[str] = []
    serving: list[int] = []
    for i, entry in enumerate(import_path):
        where = f"import_path[{i}]"
        if isinstance(entry, str) and str.__str__(entry) == "/":
            raise ValueError(f"{where}: / cannot be on the import path; name a folder or a zip")
        path = _guest_path(where, entry)
        where = f"{where} {path!r}"
        if path in entries:
            raise ValueError(f"{where}: another entry is the same")
        found = [p for p in places if _under(path, p[0])]
        if not found:
            raise ValueError(f"{where}: no grant serves it; name a path inside a read-only grant")
        guest, kind, k, writable = max(found, key=lambda p: len(p[0]))
        named = "the root" if kind == "root" else f"{kind}[{k}] at {guest}"
        if kind == "mounts":
            raise ValueError(
                f"{where} is served by {named}, a mount; only a read-only grant may serve the "
                "import path (a provider may also be serving a writable store)"
            )
        if writable:
            raise ValueError(
                f"{where} is served by {named}, which is writable; only a read-only grant may "
                "serve the import path"
            )
        for other, okind, ok, owritable in places:
            if okind != "root" and (owritable or okind == "mounts") and _under(other, path):
                what = "a mount" if okind == "mounts" else "writable"
                raise ValueError(
                    f"{where}: {okind}[{ok}] at {other} is {what} and lies under it; nothing "
                    "writable, and no mount, may lie under an entry"
                )
        entries.append(path)
        serving.append(k)
    return tuple(entries), tuple(serving)


def _check_mounts(mounts: Any, grants: tuple[Grant, ...], root: Any) -> tuple[Mount, ...]:
    """The mounts as a tuple of plain `Mount`s, or TypeError for a type and ValueError for a
    value, each naming the mount's position and guest path (spec 032, Decision 2)."""
    import inspect

    if isinstance(mounts, (str, bytes, bytearray, Mount)) or not isinstance(mounts, Iterable):
        raise TypeError(f"mounts must be an iterable of Mount, not {type(mounts).__name__}")
    checked: list[Mount] = []
    seen = {grant.guest for grant in grants}
    for i, mount in enumerate(mounts):
        if not isinstance(mount, Mount):
            raise TypeError(f"mounts[{i}] must be a Mount, not {type(mount).__name__}")
        if not isinstance(mount.guest, str):
            raise TypeError(
                f"mounts[{i}]: the guest path must be a str, not {type(mount.guest).__name__}"
            )
        text = _text(f"mounts[{i}]: the guest path", mount.guest)
        guest = "/" if text == "/" else _guest_path(f"mounts[{i}]", text)
        where = f"mounts[{i}] at {guest}"
        if type(mount.writable) is not bool:
            raise TypeError(f"{where}: writable must be True or False, not {mount.writable!r}")
        # A writable mount's provider has the write half too (spec 034, Decision 1).
        methods = METHODS if mount.writable else METHODS[:3]
        for method in methods:
            function = getattr(mount.provider, method, None)
            if not callable(function):
                raise TypeError(f"{where}: the provider has no callable {method}()")
            if inspect.iscoroutinefunction(function):
                raise TypeError(
                    f"{where}: the provider's {method}() is a coroutine function; a provider "
                    "answers synchronously (async providers are a later specification)"
                )
        if guest in seen:
            raise ValueError(f"{where}: a grant or another mount has the same guest path")
        if guest == "/" and root is not False:
            raise ValueError(
                f"{where}: a mount at / is the guest's whole filesystem; it cannot be given "
                "with root="
            )
        seen.add(guest)
        checked.append(Mount(mount.provider, guest, writable=mount.writable))
    return tuple(checked)


Identity = tuple[int, int]


class _Walked:
    """A host folder walked component by component: the path wasmtime is given, the identities of
    the folder and each ancestor (the folder's first), and what keeps it from changing until the
    identity check: on POSIX the folder's descriptor, on Windows every component's handle. A root
    still to be made has `missing` components, and its chain is its deepest existing ancestor's."""

    def __init__(self, path: str, chain: tuple[Identity, ...], held: list[int]) -> None:
        self.path, self.chain, self.held = path, chain, held
        self.missing: tuple[str, ...] = ()

    @property
    def identity(self) -> Identity | None:
        return None if self.missing else self.chain[0]

    @property
    def fd(self) -> int | None:
        return self.held[-1] if self.held and os.name == "posix" else None

    def close(self) -> None:
        held, self.held = self.held, []
        for h in held:
            _close_held(h)


def _close_held(h: int) -> None:
    try:
        if os.name == "posix":
            os.close(h)
        else:
            _win().CloseHandle(h)
    except OSError:
        pass


def _walk(where: str, path: str, *, judge: bool, may_make: bool = False) -> _Walked:
    """Walk `path` from the top. With `judge`, a link in a folder this user can write (POSIX), or
    any link or junction (Windows), raises ValueError; without it (the runtime's own folders),
    every link is followed. With `may_make`, a missing tail is returned as `missing`."""
    try:
        if os.name == "posix":
            return _walk_posix(where, path, judge, may_make)
        return _walk_windows(where, path, judge, may_make)
    except ValueError:
        raise
    except OSError as e:
        if not judge:
            raise
        # A folder that cannot be searched, or vanished mid-walk: the caller's grant is refused.
        raise ValueError(f"{where}: {path!r} cannot be walked: {e.strerror or e}") from None


# Opened for search only where the system allows (Linux O_PATH, macOS O_SEARCH): wasmtime opens a
# grant below a folder this user may search but not list, so the walk must pass through it too.
_DIR = (_flags("O_PATH") or _flags("O_SEARCH") or os.O_RDONLY) | _flags(
    "O_DIRECTORY", "O_NOFOLLOW", "O_CLOEXEC"
)


def _walk_posix(where: str, path: str, judge: bool, may_make: bool) -> _Walked:
    # Joined to the working directory without normalising: `..` is taken on the walked folders,
    # as the kernel takes it, after any link before it is followed.
    todo = list(reversed(os.path.join(os.getcwd(), path).split("/")))
    top = os.open("/", _DIR)
    st = os.fstat(top)
    stack: list[tuple[int, Identity, str]] = [(top, (st.st_dev, st.st_ino), "")]
    links = 0
    try:
        while todo:
            name = todo.pop()
            if name in ("", "."):
                continue
            if name == "..":
                if len(stack) > 1:
                    os.close(stack.pop()[0])
                continue
            parent = stack[-1][0]
            try:
                st = os.lstat(name, dir_fd=parent)
            except FileNotFoundError:
                rest = [n for n in reversed(todo) if n not in ("", ".")]
                if not may_make or ".." in rest:
                    raise ValueError(f"{where}: {path!r} does not exist") from None
                walked = _walked_posix(stack)
                walked.missing = (name, *rest)
                return walked
            if stat.S_ISLNK(st.st_mode):
                if judge and _writable(parent, stack):
                    raise ValueError(
                        f"{where}: {path!r} passes through the link {name!r} in a folder this "
                        "user can write, which a guest could have made; name its target instead"
                    )
                links += 1
                if links > MAX_LINKS:
                    raise ValueError(
                        f"{where}: {path!r} passes through more than {MAX_LINKS} links"
                    )
                target = os.readlink(name, dir_fd=parent)
                if target.startswith("/"):
                    while len(stack) > 1:
                        os.close(stack.pop()[0])
                todo.extend(reversed(target.split("/")))
                continue
            if not stat.S_ISDIR(st.st_mode):
                raise ValueError(f"{where}: {path!r} is not a folder")
            fd = os.open(name, _DIR, dir_fd=parent)
            opened = os.fstat(fd)
            if (opened.st_dev, opened.st_ino) != (st.st_dev, st.st_ino):
                os.close(fd)
                raise ValueError(f"{where}: {path!r} changed while it was checked")
            stack.append((fd, (opened.st_dev, opened.st_ino), name))
        return _walked_posix(stack)
    except BaseException:
        for fd, _, _ in stack:
            os.close(fd)
        raise


def _walked_posix(stack: list[tuple[int, Identity, str]]) -> _Walked:
    """Keep the last folder's descriptor, close the rest."""
    for fd, _, _ in stack[:-1]:
        os.close(fd)
    text = "/" + "/".join(name for _, _, name in stack[1:])
    chain = tuple(identity for _, identity, _ in reversed(stack))
    last = stack[-1][0]
    stack[:] = []
    return _Walked(text, chain, [last])


def _writable(fd: int, stack: list[tuple[int, Identity, str]]) -> bool:
    """Whether this user can write the folder open at `fd`: only a link in such a folder could be
    a guest's, since a guest writes as this user (memo §7a)."""
    effective = os.access in os.supports_effective_ids
    if os.access in os.supports_dir_fd:
        return os.access(".", os.W_OK, dir_fd=fd, effective_ids=effective)
    text = "/" + "/".join(name for _, _, name in stack[1:])
    return os.access(text, os.W_OK, effective_ids=effective)


def _make_missing(where: str, walked: _Walked) -> _Walked:
    """Make a root's missing components, after the rules were decided on its existing chain, each
    inside the one before through its descriptor; then walk the made root as any other."""
    path = walked.path
    if os.name == "posix":
        fd = os.dup(walked.held[-1])
        try:
            for name in walked.missing:
                try:
                    os.mkdir(name, dir_fd=fd)
                except FileExistsError:  # a concurrent call made it
                    pass
                child = os.open(name, _DIR, dir_fd=fd)  # O_NOFOLLOW: a link put there fails
                os.close(fd)
                fd = child
                path = os.path.join(path, name)
        finally:
            os.close(fd)
    else:
        for name in walked.missing:
            path = os.path.join(path, name)
            Path(path).mkdir(exist_ok=True)
    walked.close()
    return _walk(where, path, judge=True)


# Windows (Decision 5): Python cannot open a folder with os.open, so the walk opens every
# component through CreateFileW, refuses a reparse point (a link or a junction), and holds each
# handle without FILE_SHARE_DELETE until the identity check, so no walked folder can be renamed,
# removed or replaced in between, and no path string is ever compared.
# Traverse access, not attributes alone: Windows runs share checks only for data, execute or
# delete access (MS-FSA 2.1.5.1.2.2), so an attribute-only handle held without FILE_SHARE_DELETE
# stops no rename. FILE_TRAVERSE is FILE_EXECUTE, which is checked, and needs only the permission
# to pass through a folder, as POSIX's search does, not to list it.
_WALK_ACCESS = 0x20 | 0x80  # FILE_TRAVERSE | FILE_READ_ATTRIBUTES
_STAT_ACCESS = 0x80  # FILE_READ_ATTRIBUTES: an identity read that holds nothing
_SHARE_READ_WRITE = 0x1 | 0x2
_OPEN_EXISTING = 3
_BACKUP_SEMANTICS = 0x02000000
_OPEN_REPARSE_POINT = 0x00200000
_ATTRIBUTE_DIRECTORY = 0x10
_ATTRIBUTE_REPARSE_POINT = 0x400
_win_api: dict[str, Any] = {}


def _win() -> Any:
    if "kernel32" not in _win_api:
        from ctypes import wintypes

        k = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
        k.CreateFileW.argtypes = [
            wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
            wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
        ]  # fmt: skip
        k.CreateFileW.restype = wintypes.HANDLE
        k.GetFileInformationByHandle.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
        k.GetFileInformationByHandle.restype = wintypes.BOOL
        k.CloseHandle.argtypes = [wintypes.HANDLE]
        k.CloseHandle.restype = wintypes.BOOL
        _win_api["kernel32"] = k
    return _win_api["kernel32"]


class _ByHandle(ctypes.Structure):
    _fields_ = [
        ("attributes", ctypes.c_uint32),
        ("times", ctypes.c_uint32 * 6),
        ("volume_serial", ctypes.c_uint32),
        ("size_high", ctypes.c_uint32),
        ("size_low", ctypes.c_uint32),
        ("links", ctypes.c_uint32),
        ("index_high", ctypes.c_uint32),
        ("index_low", ctypes.c_uint32),
    ]


def _win_open(path: str, follow: bool, access: int = _WALK_ACCESS) -> tuple[int, int, Identity]:
    """A held handle on `path`, its attributes and its identity, as wasmtime reads it."""
    k = _win()
    flags = _BACKUP_SEMANTICS | (0 if follow else _OPEN_REPARSE_POINT)
    h = k.CreateFileW(path, access, _SHARE_READ_WRITE, None, _OPEN_EXISTING, flags, None)
    if h is None or h == ctypes.c_void_p(-1).value:
        code = ctypes.get_last_error()  # type: ignore[attr-defined]
        raise ctypes.WinError(code)  # type: ignore[attr-defined]
    info = _ByHandle()
    if not k.GetFileInformationByHandle(h, ctypes.byref(info)):
        code = ctypes.get_last_error()  # type: ignore[attr-defined]
        k.CloseHandle(h)
        raise ctypes.WinError(code)  # type: ignore[attr-defined]
    index = (info.index_high << 32) | info.index_low
    return h, info.attributes, (info.volume_serial, index)


# Names a judged Windows walk refuses (spec 076, Decision 1): Win32 rewrites them, so the path
# opened and the chain of folders walked could disagree, and a rule that reads the chain could
# miss a true ancestor (the pre-build review's F1). A `:` is a drive letter (`C:\\b\\D:x` is
# drive D's current folder) or a stream; a trailing space or period is trimmed in some positions
# and not others; a reserved device name, with or without an extension, is the device, and a
# root still to be made through one would fail after the folders before it were made. The set is
# exactly Python's own `ntpath.isreserved` for one component (spec 077), which the runner cannot
# call on 3.11 and 3.12: Microsoft's reserved names ("Naming Files, Paths, and Namespaces"), with
# the superscript `COM¹` to `LPT³` it reserves "in every directory"; `CONIN$` and `CONOUT$`,
# which CPython refuses "on the side of caution"; and the characters Windows rejects in a name.
_WIN_DEVICES = frozenset(
    {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
    | {f"{p}{c}" for p in ("COM", "LPT") for c in "123456789\u00b9\u00b2\u00b3"}
)
_WIN_RESERVED_CHARS = frozenset('"*<>?|' + "".join(map(chr, range(32))))


def _rewritten(name: str) -> bool:
    """Whether Windows rewrites or rejects this one path component (never `.` or `..`): the same
    answer as `ntpath.isreserved` gives for it (spec 077, Decision 3)."""
    if name in (".", ".."):
        return False
    if ":" in name or _WIN_RESERVED_CHARS.intersection(name) or name.endswith((" ", ".")):
        return True
    return name.split(".", 1)[0].rstrip(" ").upper() in _WIN_DEVICES


def _drive_folder(drive: str) -> str:
    """The current folder of `drive` (the process's own drive when empty), holding no `..`: where
    a relative Windows path starts, and whose drive a rooted one takes (spec 076, Decision 1). A
    seam the tests replace."""
    return ntpath.abspath(drive or ".")


def _walk_windows(where: str, path: str, judge: bool, may_make: bool) -> _Walked:
    if judge:
        # Made absolute without dropping `..` (spec 076): only the start is ever normalised, and
        # `..` is taken on the folders walked, as `_walk_posix` takes it.
        drive, tail = ntpath.splitdrive(path)
        if tail[:1] in ("\\", "/") or drive[1:2] not in ("", ":"):  # rooted, or a share
            if not drive:  # rooted with no drive: the current folder's drive, fully qualified
                drive = ntpath.splitdrive(_drive_folder(""))[0]
            names = re.split(r"[\\/]", tail)
        else:
            drive, start = ntpath.splitdrive(_drive_folder(drive))
            names = re.split(r"[\\/]", start) + re.split(r"[\\/]", tail)
    else:
        drive, rest = ntpath.splitdrive(ntpath.realpath(path))
        names = re.split(r"[\\/]", rest)
    names = [n for n in names if n not in ("", ".")]
    if judge:
        for name in names:
            if _rewritten(name):
                raise ValueError(
                    f"{where}: {path!r} has a name Windows rewrites ({name!r}); name the folder "
                    "plainly"
                )
    held: list[int] = []
    chain: list[Identity] = []
    heres: list[str] = []

    def enter(here: str) -> None:
        h, attributes, identity = _win_open(here, follow=not judge)
        held.append(h)
        if judge and attributes & _ATTRIBUTE_REPARSE_POINT:
            raise ValueError(
                f"{where}: {path!r} passes through a link or junction; on Windows every one is "
                "refused"
            )
        if not attributes & _ATTRIBUTE_DIRECTORY:
            raise ValueError(f"{where}: {path!r} is not a folder")
        chain.append(identity)
        heres.append(here)

    try:
        try:
            enter(drive + "\\")  # a drive's root keeps its separator: `C:` alone is relative
        except FileNotFoundError:
            raise ValueError(f"{where}: {path!r} does not exist") from None
        for i, name in enumerate(names):
            if name == "..":
                if len(heres) > 1:  # at the drive's root `..` stays, as POSIX's does at `/`
                    _close_held(held.pop())
                    chain.pop()
                    heres.pop()
                continue
            try:
                enter(heres[-1].rstrip("\\") + "\\" + name)  # never ntpath.join (a drive resets it)
            except FileNotFoundError:
                rest = tuple(names[i + 1 :])
                if not may_make or ".." in rest:
                    raise ValueError(f"{where}: {path!r} does not exist") from None
                walked = _Walked(heres[-1], tuple(reversed(chain)), held)
                walked.missing = (name, *rest)
                return walked
        return _Walked(heres[-1], tuple(reversed(chain)), held)
    except BaseException:
        for h in held:
            _close_held(h)
        raise


def _chain(path: Path) -> tuple[Identity | None, tuple[Identity, ...]]:
    """A runtime folder's identity (None while it does not exist) and the identities of its
    deepest existing ancestor and that one's ancestors, every link followed; never refuses."""
    here = Path(os.path.realpath(path))
    exists = True
    while True:
        try:
            first = _identity_of(here)
            break
        except OSError:
            exists = False
            if here.parent == here:
                return None, ()
            here = here.parent
    chain = [first]
    for parent in here.parents:
        try:
            chain.append(_identity_of(parent))
        except OSError:
            break
    return (first if exists else None), tuple(chain)


def _identity_of(path: Path) -> Identity:
    if os.name == "posix":
        st = os.stat(path)
        if not stat.S_ISDIR(st.st_mode):
            raise NotADirectoryError(str(path))
        return (st.st_dev, st.st_ino)
    # Attributes only: a runtime folder's chain must not be cut short by a folder one may not
    # traverse, or by another handle's share mode (the follow-up review, F1).
    h, _, identity = _win_open(str(path), follow=True, access=_STAT_ACCESS)
    _close_held(h)
    return identity


def _judge(
    root: _Walked | None,
    grants: list[tuple[str, Grant, _Walked]],
    runtime: list,
    shared: list[tuple[str, tuple[Identity, ...]]] = [],  # noqa: B006 (read only)
) -> None:
    """Decision 4's rules, by identity. `runtime` is (name, identity or None, chain) for each of
    the runtime's own folders: a writable grant at, inside or above one is refused; a folder not
    made yet holds nothing, so only a grant above its deepest existing ancestor is. `shared` is
    (name, chain) for each folder no grant, read-only included, may be at or above."""
    judged = [("root", None, root)] if root is not None else []
    for where, _, w in [*judged, *grants]:  # root too: the temporary folder may have moved
        for name, chain in shared:
            if w.identity is not None and w.identity in chain:
                raise ValueError(f"{where} holds {name}; grant a folder apart from it")
    writable = [("root", root)] if root is not None else []
    writable += [(where, w) for where, g, w in grants if g.writable]
    for where, w in writable:
        for name, identity, chain in runtime:
            inside = identity is not None and identity in w.chain
            above = w.identity is not None and w.identity in chain
            if inside or above:
                how = "is inside" if inside else "holds"
                raise ValueError(
                    f"{where} is writable and {how} {name}, which later calls trust; grant a "
                    "folder apart from it"
                )
    for where, g, r in grants:
        if g.writable:
            continue
        for other, w in writable:
            if w.identity is not None and w.identity in r.chain:
                raise ValueError(
                    f"{where} is read-only but inside {other}, which is writable; a guest would "
                    "change it through that grant"
                )


# The zip (spec 017, Decision 2, amended by spec 023, Decision 5): one private folder per zip per
# process, beside a lock file. It holds `lib/python3XY.zip`, granted read-only at /usr/local/lib
# on every call (so the guest sees the zip there and nothing else), and `mpl-data/`, matplotlib's
# data extracted from the zip's inner archive, granted read-only at the path matplotlib computes.
# Its own lock, since the epoch ticker takes `_lock` every round.
_zip_lock = threading.Lock()
# the zip's SHA-256 -> [its _Private folder, the copy's stamp, the data's record or None]
_zips: dict[str, list[Any]] = {}
MPL_DATA_MEMBER = "matplotlib/mpl-data.zip"  # the inner archive in the stdlib zip (spec 023)
MPL_DATA_GUEST = "matplotlib/mpl-data"  # under the zip's guest path: Path(__file__) there


@dataclass(frozen=True)
class _ZipFolder:
    lib: Path  # granted at /usr/local/lib: the zip alone
    data: Path | None  # matplotlib's data, when the zip carries it
    name: str  # the zip's name, python3XY.zip


def _zip_folder(found: Artifacts) -> _ZipFolder:
    want = _digest(found.stdlib_zip)
    name = f"python{_version_tag(found.manifest)}.zip"
    with _zip_lock:
        entry = _zips.get(want)
        if entry is None:
            return _zip_folder_locked(found, want, name)
        private, stamp, record = entry
        if not os.path.isdir(private.path) or os.path.islink(private.path):
            # Removed on the host (a temporary-folder cleaner, say): made again, not trusted.
            private.remove()
            del _zips[want]
            return _zip_folder_locked(found, want, name)
        lib = private.path / "lib"
        dest = lib / name
        try:
            st = os.lstat(dest) if os.path.isdir(lib) and not os.path.islink(lib) else None
        except FileNotFoundError:
            st = None
        if st is None or not stat.S_ISREG(st.st_mode) or _stamp(st) != stamp:
            _real_folder(lib)
            entry[1] = _copy_zip(found, dest, want)  # changed on the host: copied again
        data = private.path / "mpl-data"
        if record is not None and not _data_intact(data, record):
            entry[2] = _extract_data(data, dest)  # changed on the host: extracted again
        return _ZipFolder(lib, None if entry[2] is None else data, name)


def _zip_folder_locked(found: Artifacts, want: str, name: str) -> _ZipFolder:
    private = _Private("wasi-python-zip-")
    try:
        lib = private.path / "lib"
        lib.mkdir(mode=0o700)
        stamp = _copy_zip(found, lib / name, want)
        record = _extract_data(private.path / "mpl-data", lib / name)
    except BaseException:
        private.remove()
        raise
    _zips[want] = [private, stamp, record]
    return _ZipFolder(lib, None if record is None else private.path / "mpl-data", name)


def _zip_known(found: Artifacts) -> Path | None:
    """This process's folder for this zip, if it has made one."""
    with _zip_lock:
        entry = _zips.get(_digest(found.stdlib_zip))
    return None if entry is None else entry[0].path


def _remove_entry(path: Path) -> None:
    """A real folder removed whole; a file or a link (to a folder too) unlinked, never followed."""
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path)
    else:
        os.unlink(path)


def _real_folder(path: Path) -> None:
    """A real folder at the path: a file or a link there is removed first, never followed."""
    if os.path.islink(path) or (os.path.lexists(path) and not os.path.isdir(path)):
        os.unlink(path)
    if not os.path.isdir(path):
        os.mkdir(path, 0o700)


def _member_parts(name: str) -> tuple[str, ...]:
    """A member's path, refused when it could leave the data folder (spec 023, Decision 5)."""
    parts = tuple(name.rstrip("/").split("/"))
    if (
        not name
        or name.startswith("/")
        or "\\" in name
        or ":" in name
        or any(p in ("", ".", "..") for p in parts)
    ):
        raise RuntimeError(f"the stdlib zip's matplotlib data holds the member {name!r}")
    return parts


def _extract_data(data: Path, zip_copy: Path) -> dict[str, tuple[int, ...] | None] | None:
    """matplotlib's data, made equal to the inner archive in the private copy of the zip (checked
    by its SHA-256 just before): the outer member is read into memory whole, each file written,
    read back once and compared with its CRC-32 and size, and every path recorded with its type
    and stamp. A member that is absolute, holds `..`, or is a link or anything but a regular file
    or folder is refused. What the folder holds and the archive does not is removed. None, and no
    folder, when the zip carries no data. Windows cannot replace a file a running guest has open:
    one already right is kept, as `_copy_zip` keeps the zip."""
    with zipfile.ZipFile(zip_copy) as outer:
        try:
            inner_bytes = outer.read(MPL_DATA_MEMBER)
        except KeyError:
            if os.path.lexists(data):
                shutil.rmtree(data) if os.path.isdir(data) and not os.path.islink(
                    data
                ) else os.unlink(data)
            return None
    files: dict[tuple[str, ...], zipfile.ZipInfo] = {}
    folders: set[tuple[str, ...]] = set()
    with zipfile.ZipFile(io.BytesIO(inner_bytes)) as inner:
        for info in inner.infolist():
            parts = _member_parts(info.filename)
            kind = stat.S_IFMT(info.external_attr >> 16)  # 0 when the zip records no type
            if info.is_dir():
                folders.add(parts)
            elif kind and kind != stat.S_IFREG:
                raise RuntimeError(
                    f"the stdlib zip's matplotlib data holds {info.filename!r}, not a regular file"
                )
            else:
                files[parts] = info
            folders.update(parts[:k] for k in range(1, len(parts)))
        clash = sorted("/".join(p) for p in folders & set(files))
        if clash:
            raise RuntimeError(f"the stdlib zip's matplotlib data holds {clash[0]!r} twice")
        _real_folder(data)
        for parts in sorted(folders, key=len):
            _real_folder(data.joinpath(*parts))
        for parts, info in sorted(files.items()):
            _write_member(inner, info, data.joinpath(*parts))
    _remove_extra(data, files, folders)
    return _record(data)


def _write_member(inner: zipfile.ZipFile, info: zipfile.ZipInfo, dest: Path) -> None:
    body = inner.read(info)  # zipfile checks the member's CRC-32 as it reads
    fd, tmp = tempfile.mkstemp(prefix=".mpl-data-", dir=dest.parent)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(body)
        os.chmod(tmp, 0o644)
        with open(tmp, "rb") as back:  # read back once: an accident on the way is caught here
            again = back.read()
        if len(again) != info.file_size or zlib.crc32(again) != info.CRC:
            raise RuntimeError(f"matplotlib's data file {dest} did not read back as written")
        if os.path.islink(dest) or os.path.isdir(dest):
            shutil.rmtree(dest) if os.path.isdir(dest) and not os.path.islink(dest) else os.unlink(
                dest
            )
        try:
            os.replace(tmp, dest)
        except PermissionError:
            if os.name != "nt" or not _holds(dest, info):
                raise
            Path(tmp).unlink(missing_ok=True)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _holds(path: Path, info: zipfile.ZipInfo) -> bool:
    try:
        with open(path, "rb") as f:
            body = f.read()
    except OSError:
        return False
    return len(body) == info.file_size and zlib.crc32(body) == info.CRC


def _remove_extra(data: Path, files: dict, folders: set) -> None:
    """Every entry of the folder that the archive does not hold, removed without following a
    link."""
    for dirpath, dirnames, filenames in os.walk(data, topdown=True, followlinks=False):
        here = Path(dirpath).relative_to(data).parts
        for d in list(dirnames):
            p = Path(dirpath, d)
            if (*here, d) not in folders or os.path.islink(p):
                dirnames.remove(d)
                _remove_entry(p)
        for f in filenames:
            if (*here, f) not in files:
                os.unlink(Path(dirpath, f))


def _record(data: Path) -> dict[str, tuple[int, ...] | None]:
    """Every path under the data folder: None for a folder, the stamp for a file."""
    record: dict[str, tuple[int, ...] | None] = {}
    for dirpath, dirnames, filenames in os.walk(data, followlinks=False):
        here = Path(dirpath).relative_to(data)
        for d in dirnames:
            record[(here / d).as_posix()] = None
        for f in filenames:
            record[(here / f).as_posix()] = _stamp(os.lstat(Path(dirpath, f)))
    return record


def _data_intact(data: Path, record: dict[str, tuple[int, ...] | None]) -> bool:
    """Per call, before granting: the whole tree against the record, the same names, each a real
    folder or a regular file as recorded, no link, each file's stamp equal."""
    if os.path.islink(data) or not os.path.isdir(data):
        return False
    seen: dict[str, tuple[int, ...] | None] = {}
    try:
        for dirpath, dirnames, filenames in os.walk(data, followlinks=False):
            here = Path(dirpath).relative_to(data)
            for name in [*dirnames, *filenames]:
                st = os.lstat(Path(dirpath, name))
                key = (here / name).as_posix()
                if stat.S_ISDIR(st.st_mode):
                    seen[key] = None
                elif stat.S_ISREG(st.st_mode):
                    seen[key] = _stamp(st)
                else:
                    return False  # a link, or anything else
    except OSError:
        return False
    return seen == record


def _copy_zip(found: Artifacts, dest: Path, want: str) -> tuple[int, ...]:
    fd, tmp = tempfile.mkstemp(prefix=".python-zip-", dir=dest.parent)
    try:
        with os.fdopen(fd, "wb") as out, found.stdlib_zip.open("rb") as src:
            for block in iter(lambda: src.read(1 << 20), b""):
                out.write(block)
        # 0644, not read-only: Windows could neither replace nor remove a read-only file, and
        # the guest's grant is read-only anyway, in a 0700 folder.
        os.chmod(tmp, 0o644)
        try:
            os.replace(tmp, dest)
        except PermissionError:
            # Windows cannot replace a file a running guest has open; when the file in place is
            # already the right zip, the copy is not needed.
            if os.name != "nt" or not (dest.is_file() and _hash_file(dest) == want):
                raise
            Path(tmp).unlink(missing_ok=True)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    if _hash_file(dest) != want:
        raise RuntimeError(f"the stdlib zip's copy at {dest} is not the artifact set's")
    return _stamp(os.lstat(dest))


def _remove_zips() -> None:
    with _zip_lock:
        entries = list(_zips.values())
        _zips.clear()
    for private, *_ in entries:
        private.remove()


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


def _rotl(x: int, b: int) -> int:
    return ((x << b) | (x >> (64 - b))) & _M64


def _siphash13(data: bytes) -> int:
    v0, v1 = 0x736F6D6570736575, 0x646F72616E646F6D
    v2, v3 = 0x6C7967656E657261, 0x7465646279746573

    def rounds(n: int) -> None:
        nonlocal v0, v1, v2, v3
        for _ in range(n):
            v0 = (v0 + v1) & _M64
            v1 = _rotl(v1, 13) ^ v0
            v0 = _rotl(v0, 32)
            v2 = (v2 + v3) & _M64
            v3 = _rotl(v3, 16) ^ v2
            v0 = (v0 + v3) & _M64
            v3 = _rotl(v3, 21) ^ v0
            v2 = (v2 + v1) & _M64
            v1 = _rotl(v1, 17) ^ v2
            v2 = _rotl(v2, 32)

    end = len(data) - len(data) % 8
    for i in range(0, end, 8):
        m = struct.unpack_from("<Q", data, i)[0]
        v3 ^= m
        rounds(1)
        v0 ^= m
    last = (len(data) & 0xFF) << 56
    for i, byte in enumerate(data[end:]):
        last |= byte << (8 * i)
    v3 ^= last
    rounds(1)
    v0 ^= last
    v2 ^= 0xFF
    rounds(3)
    return v0 ^ v1 ^ v2 ^ v3


def _wasi_ino(identity: Identity) -> int:
    """The `ino` wasmtime reports for a folder of this identity. Rust sign-extends a negative
    dev_t, hence the mask; the words are native-endian, as Rust's Hash writes them."""
    return _siphash13(struct.pack("=QQ", identity[0] & _M64, identity[1] & _M64))


class _Preopen(NamedTuple):
    label: str  # how an error names it: "grant 2 at /data", "root", "the stdlib folder"
    walked: _Walked
    guest: str
    writable: bool


def _check_module(wt: Any, engine: Any, metered: bool) -> Any:
    with _lock:
        if metered not in _check_modules:
            _check_modules[metered] = wt.Module(engine, _CHECK_WAT)
        return _check_modules[metered]


def _check_preopens(wt: Any, linker: Any, store: Any, check: Any, preopens: list[_Preopen]) -> None:
    """Before the guest: each preopen 3 + i is the folder the walk checked, by guest name and by
    identity. A mismatch raises before the guest runs; the walk's holds are released either way."""
    try:
        exports = linker.instantiate(store, check).exports(store)
        memory = exports["memory"]
        for i, p in enumerate(preopens):
            fd = 3 + i
            name = p.guest.encode()
            ok = exports["prestat"](store, fd) == 0
            if ok:
                head = bytes(memory.read(store, 0, 8))
                ok = head[0] == 0 and struct.unpack_from("<I", head, 4)[0] == len(name)
            ok = ok and exports["name"](store, fd, len(name)) == 0
            ok = ok and bytes(memory.read(store, 1024, 1024 + len(name))) == name
            ok = ok and exports["stat"](store, fd) == 0
            identity = p.walked.identity
            if ok and identity is not None:
                reported = struct.unpack("<Q", bytes(memory.read(store, 72, 80)))[0]
                ok = reported == _wasi_ino(identity)
            if not ok:
                raise RuntimeError(f"{p.label} changed between its check and the call")
    finally:
        for p in preopens:
            p.walked.close()


# A seam for the swap check (tests only): runs after every walk and before wasmtime opens anything.
_after_walk: Callable[[], None] | None = None


def _walk_grants(
    root: str | bool | None,
    grants: tuple[Grant, ...],
    found: Artifacts,
    cache: Path | None,
    import_path: tuple[str, ...] = (),
    serving: tuple[int, ...] = (),
) -> tuple[_Walked | None, list[tuple[str, Grant, _Walked]]]:
    """Every grant and `root`, walked and judged before any work (Decision 4); a missing root is
    made only once every rule has passed on its existing chain, the import path's included."""
    walked_root: _Walked | None = None
    walked: list[tuple[str, Grant, _Walked]] = []
    runtime = _runtime_folders(found, cache)  # first: it makes the module cache if it can
    try:
        if isinstance(root, str):
            walked_root = _walk("root", root, judge=True, may_make=True)
        for i, grant in enumerate(grants):
            where = f"grants[{i}] at {grant.guest}"
            walked.append((where, grant, _walk(where, os.fspath(grant.host), judge=True)))
        _judge(walked_root, walked, runtime, _shared_folders())
        _judge_import_path(walked_root, walked, import_path, serving)
        if walked_root is not None and walked_root.missing:
            try:
                walked_root = _make_missing("root", walked_root)
            except OSError as e:
                raise ValueError(f"root: {root!r} cannot be made: {e.strerror or e}") from None
        return walked_root, walked
    except BaseException:
        for w in [walked_root, *(w for _, _, w in walked)]:
            if w is not None:
                w.close()
        raise


def _judge_import_path(
    root: _Walked | None,
    grants: list[tuple[str, Grant, _Walked]],
    import_path: tuple[str, ...],
    serving: tuple[int, ...],
) -> None:
    """Spec 054, Decision 5, by identity: no writable grant, and no root, at or inside the whole
    folder of a read-only grant that serves an entry. The whole folder, not the entry's
    subfolder: a link inside a grant reaches any folder of it. A root still to be made carries
    its deepest existing ancestor's chain, so one to be made inside is refused before it is."""
    writable = [("root", root)] if root is not None else []
    writable += [(where, w) for where, g, w in grants if g.writable]
    for i, (entry, k) in enumerate(zip(import_path, serving, strict=True)):
        where, _, r = grants[k]
        for other, w in writable:
            if r.identity is not None and r.identity in w.chain:
                raise ValueError(
                    f"import_path[{i}] {entry!r} is served by {where}, whose folder holds "
                    f"{other}, which is writable; a guest would plant code there for the import "
                    "path"
                )


def _runtime_folders(found: Artifacts, cache: Path | None) -> list[tuple[str, Any, Any]]:
    """The folders later calls and processes trust: this zip's folder (or, before it is made, the
    temporary folder that will hold it), the artifact set's files, the module cache, and the
    runtime's own code (this package and wasmtime-py's, whose native library a guest must never
    replace). The module cache is made first, if it can be, so it is judged as it will be: a root
    still to be made above a cache still to be made would otherwise come to hold it (the build
    review, finding 1)."""
    import wasmtime

    if cache is not None:
        try:
            cache.mkdir(mode=0o700, parents=True, exist_ok=True)
        except OSError:
            pass  # unusable: `_module` then keeps compiled modules in memory
    zip_dir = _zip_known(found)
    if zip_dir is not None:
        folders = [("the runtime's stdlib folder", *_chain(zip_dir))]
    else:
        temp = Path(tempfile.gettempdir())
        folders = [
            ("the temporary folder, where the runtime's stdlib folder goes", None, _chain(temp)[1])
        ]
    parts = {found.manifest.parent, found.snapshot.parent, found.plain.parent}
    parts.add(found.stdlib_zip.parent)
    folders += [("the artifact set", *_chain(d)) for d in sorted(parts)]
    if cache is not None:
        folders.append(("the module cache", *_chain(cache)))
    folders.append(("wasi_python's own code", *_chain(Path(__file__).resolve().parent)))
    folders.append(("wasmtime-py's own code", *_chain(Path(wasmtime.__file__).resolve().parent)))
    # The host's own interpreter, which the next host process runs (spec 024, S2): its stdlib,
    # its site-packages and scripts, and the user's site-packages it imports at start-up.
    import site
    import sysconfig

    paths = sysconfig.get_paths()
    keys = ("stdlib", "platstdlib", "purelib", "platlib", "scripts")
    own = {Path(paths[k]).resolve() for k in keys if k in paths}
    if site.ENABLE_USER_SITE:
        own.add(Path(site.getusersitepackages()).resolve())
    folders += [("the host Python's own code", *_chain(d)) for d in sorted(own) if d.is_dir()]
    return folders


def _shared_folders() -> list[tuple[str, tuple[Identity, ...]]]:
    """Folders no grant may be at or above, read-only included: the temporary folder holds every
    call's private root and stdin (the build review, finding 2)."""
    temp = Path(tempfile.gettempdir())
    return [
        (
            "the temporary folder, which holds every call's private folders and stdin",
            _chain(temp)[1],
        )
    ]


def _run_checked(
    wt: Any,
    c: dict[str, Any],
    host: Host | None,
    snapshot: bool,
    cache_dir: str | os.PathLike[str] | None | bool,
    artifacts: Artifacts | None,
) -> Completed:
    found = artifacts if artifacts is not None else find_artifacts()
    if c.get("tools") is not None and not _has_guest_package(found.manifest):
        from . import ArtifactsMissing

        raise ArtifactsMissing(
            f"{found.manifest} has no `recipe … {GUEST_PACKAGE}` line: this artifact set "
            "predates the tool protocol (spec 031), so its guest cannot `from host import "
            "tools`; tools= needs a set built with the guest package"
        )
    cache = _cache_dir(cache_dir)
    root = c["root"]
    entries, serving = c.get("import_path", ()), c.get("import_serving", ())
    walked_root, walked = _walk_grants(root, c["grants"], found, cache, entries, serving)
    preopens: list[_Preopen] = []
    private = None
    try:
        if _after_walk is not None:
            _after_walk()
        binary = found.snapshot if snapshot else found.plain
        engine = _engine(c["fuel"] is not None)
        module = _module(engine, c["fuel"] is not None, binary, cache)
        root_path, private = _preopens(found, root, walked_root, walked, preopens)
        return _call(wt, engine, module, root_path, preopens, c, host)
    finally:
        # Windows holds every walked folder until here; a private root can be removed only after.
        for w in [walked_root, *(w for _, _, w in walked), *(p.walked for p in preopens)]:
            if w is not None:
                w.close()
        if private is not None:
            private.remove()


def _preopens(
    found: Artifacts,
    root: str | bool | None,
    walked_root: _Walked | None,
    walked: list[tuple[str, Grant, _Walked]],
    preopens: list[_Preopen],
) -> tuple[Path | None, _Private | None]:
    """The zip's folder, matplotlib's data, the root and the grants, appended to `preopens` in
    the order wasmtime opens them; (the root's path, a private root to remove or None). Shared by
    a call and a session's opening (spec 055)."""
    _sweep_once()
    folder = _zip_folder(found)
    preopens.append(
        _Preopen("the stdlib folder", _walk("", str(folder.lib), judge=False), ZIP_GUEST, False)
    )
    if folder.data is not None:  # after the zip's grant (spec 023, Decision 5)
        guest = f"{ZIP_GUEST}/{folder.name}/{MPL_DATA_GUEST}"
        walked_data = _walk("", str(folder.data), judge=False)
        preopens.append(_Preopen("matplotlib's data", walked_data, guest, False))
    root_path = None
    private = None
    if root is None:
        private = _Private("wasi-python-root-")  # 0700, this user's own, locked (spec 016)
        try:
            (private.path / "usr" / "local" / "lib").mkdir(parents=True)
            root_path = private.path
            walked_private = _walk("", str(root_path), judge=False)
        except BaseException:
            private.remove()
            raise
        preopens.append(_Preopen("the private root", walked_private, "/", True))
    elif walked_root is not None:
        root_path = Path(walked_root.path)
        # Real folders, never a guest's link: without them /usr would vanish from a fresh
        # root's listing, and the zip's path could resolve into a file a guest wrote. Made
        # through the walked folder, never its path, which another guest may have swapped
        # since the walk (spec 024).
        if walked_root.fd is not None and _dir_fd_ok():
            os.close(_real_dir_at(walked_root.fd, ("usr", "local", "lib")))
        else:
            _real_dir(root_path, ("usr", "local", "lib"))
        preopens.append(_Preopen("root", walked_root, "/", True))
    for where, grant, w in walked:
        preopens.append(_Preopen(where, w, grant.guest, grant.writable))
    return root_path, private


def _call(
    wt: Any,
    engine: wasmtime.Engine,
    module: wasmtime.Module,
    root: Path | None,
    preopens: list[_Preopen],
    c: dict[str, Any],
    host: Host | None,
) -> Completed:
    """One instance, one program. The store is closed before this returns, trapped or not, so the
    guest's memory and open files are released at once (a trapped store is otherwise kept alive by
    a reference cycle until Python's collector runs) and a private root can be removed afterwards
    (Windows refuses to remove an open directory). Ctrl-C is deferred while the guest runs."""
    with _deferred_ctrl_c():
        return _call_deferred(wt, engine, module, root, preopens, c, host)


def _call_deferred(
    wt: Any,
    engine: wasmtime.Engine,
    module: wasmtime.Module,
    root: Path | None,
    preopens: list[_Preopen],
    c: dict[str, Any],
    host: Host | None,
) -> Completed:
    tmp, tmp_fd = _home_folder(root, preopens, tuple(m.guest for m in c.get("mounts", ())))
    home = None
    if tmp is not None:
        # The fresh HOME is made, and removed, through a handle on /tmp opened without following a
        # link, so a guest running concurrently on the same folder cannot turn /tmp into a link
        # between the check and the mkdir (Windows has no dir_fd, and its guests cannot make links).
        name = f".home-{secrets.token_hex(16)}"
        try:
            if tmp_fd is not None:
                os.mkdir(name, dir_fd=tmp_fd)
            else:
                (tmp / name).mkdir()
        except BaseException:
            _close(tmp_fd)
            raise
        home = (name, f"/tmp/{name}")
    store = wt.Store(engine)
    try:
        guest_home = None if home is None else home[1]
        return _instance(wt, engine, module, store, preopens, guest_home, c, host)
    finally:
        store.close()
        if home is not None and tmp_fd is not None:
            shutil.rmtree(home[0], ignore_errors=True, dir_fd=tmp_fd)
        elif home is not None and tmp is not None:
            shutil.rmtree(tmp / home[0], ignore_errors=True)
        _close(tmp_fd)


def _home_folder(
    root: Path | None, preopens: list[_Preopen], mounted: tuple[str, ...] = ()
) -> tuple[Path | None, int | None]:
    """Where HOME is made (Decision 3): a writable grant at /tmp, else the root's tmp, else
    nowhere. A read-only grant at /tmp hides the root's tmp, so then there is no HOME either, and
    a mount at /tmp counts as one (spec 032): the runner makes nothing in a mount."""
    if "/tmp" in mounted:
        return None, None
    at_tmp = [p for p in preopens if p.guest == "/tmp"]
    if at_tmp:
        p = at_tmp[0]
        if not p.writable:
            return None, None
        fd = p.walked.fd
        return Path(p.walked.path), (os.dup(fd) if fd is not None and _dir_fd_ok() else None)
    if root is None:
        return None, None
    # TMPDIR, a real folder (a guest's link there is removed), made through the root's walked
    # folder, never its path (spec 024).
    fd = next(p.walked.fd for p in preopens if p.guest == "/")
    if fd is not None and _dir_fd_ok():
        return root / "tmp", _real_dir_at(fd, ("tmp",))
    return _real_dir(root, ("tmp",)), None


def _dir_fd_ok() -> bool:
    return os.mkdir in os.supports_dir_fd and shutil.rmtree.avoids_symlink_attacks is not False


def _open_dir(path: Path) -> int | None:
    """A handle on a directory, opened without following a link; None where the platform has no
    dir_fd support (Windows)."""
    if not _dir_fd_ok():
        return None
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    return os.open(path, flags)


def _close(fd: int | None) -> None:
    if fd is not None:
        os.close(fd)


def _import_prelude(entries: tuple[str, ...]) -> list[str]:
    """The `-c` prelude that puts the import path on `sys.path` (spec 054, Decision 7): one
    expression statement that binds no name in `__main__`. It drops the `linecache` entry the
    reactor registered for it, so no later `exec` or `eval` of a string shows its source; extends
    `sys.path` after the stdlib zip; and runs the caller's argv through the reactor's own
    argument handling, whose exit code it returns. `entries` are the plain strings
    `_check_import_path` kept, so `repr` is `str`'s own. No entries, no prelude: the argv is
    today's."""
    if not entries:
        return []
    plain = [str.__str__(e) for e in entries]
    line = (
        "__import__('linecache')._interactive_cache.clear() or "
        f"__import__('sys').path.extend({plain!r}) or "
        "__import__('sys').exit(__import__('_reactor').run("
        f"[{ARGV0!r}, *__import__('sys').argv[1:]], dict(__import__('os').environ)))"
    )
    return ["-c", line]


def _instance(
    wt: Any,
    engine: wasmtime.Engine,
    module: wasmtime.Module,
    store: wasmtime.Store,
    preopens: list[_Preopen],
    home: str | None,
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
    # Under tools=, the runner is the door's host: the frame host, bound by the same deadline,
    # cancel and Ctrl-C, and asked to admit each frame by its length before it is read (036).
    tool_host = _tool_host(c, stop_at, cancel)
    admit = None
    if tool_host is not None:
        host, admit = tool_host, tool_host.admit

    out, err = _Stream("stdout", output_bytes), _Stream("stderr", output_bytes)
    wasi = wt.WasiConfig()
    origin_ns = time.perf_counter_ns()  # wasmtime's monotonic clock counts from here (spec 010)
    wasi.argv = [ARGV0, *_import_prelude(c.get("import_path", ())), *argv]
    fresh = {} if home is None else {"HOME": home}  # no HOME where there is no /tmp to make it
    wasi.env = sorted({**BASE_ENV, **fresh, **(env or {})}.items())
    check = _check_module(wt, engine, fuel is not None)
    keys = _send_outputs(wasi, out, err)
    scratch = None
    mounts: tuple[Mount, ...] = c.get("mounts", ())
    mounted: list[_Preopen] = []  # each mount's preopen, on the call's empty placeholder
    table = None
    files = None
    try:
        # 0700, this user's own, locked (spec 016); made before the preopens, since it holds the
        # mounts' placeholder, which lies under the temporary folder no grant may reach (spec 032).
        scratch = _Private("wasi-python-")
        if mounts:
            placeholder = scratch.path / "mount"
            placeholder.mkdir()
            for i, mount in enumerate(mounts):
                walked = _walk("", str(placeholder), judge=False)
                mounted.append(
                    _Preopen(f"mounts[{i}] at {mount.guest}", walked, mount.guest, False)
                )
        every = [*preopens, *mounted]
        for p in every:  # the stdlib folder first; wasi-libc picks by the longest guest prefix
            wasi.preopen_dir(p.walked.path, p.guest, p.writable)
        stdin_path = scratch.path / "stdin"
        stdin_path.write_bytes(stdin or b"")
        wasi.stdin_file = str(stdin_path)
        store.set_wasi(wasi)
        linker = _linker(wt, engine)  # held for the whole call: clearing the cache cannot free it
        from .mounts import _Files

        staging = STAGING_CEILING if memory_bytes is None else memory_bytes
        others = [p.guest for p in preopens]
        if mounts:
            guest_linker = _mount_linker(wt, engine)
            first = 3 + len(preopens)  # the mounts' preopens come after every other
            numbers = [(mount, first + i) for i, mount in enumerate(mounts)]
        else:
            # A call without mounts: the guard linker, today's but for fd_readdir and
            # path_rename, served by a table with no mounts, which forwards both with wasmtime
            # 49.0.2's and 49.0.3's fixes (spec 048, Decision 7).
            guest_linker = _guard_linker(wt, engine)
            numbers = []
        table = _Files(
            numbers,
            others,
            c["file_calls"],
            staging,
            fuel is not None,
            engine,
            open_files=c["open_files"],  # spec 068: strict, as file_calls
        )
        call = _Call(store, host, waits, origin_ns, cancel, stop_at, table, admit)
        if cancel is not None:
            _watch(store)
        with _epoch_ticker(engine, deadline_s is not None or cancel is not None):
            done = _drive(wt, guest_linker, store, module, call, fuel, every, check, plain=linker)
        fuel_used = _fuel_used(fuel, done, call, store.get_fuel)
        # Spec 034, Decision 8: what the guest wrote is handed over at every ending that returns
        # a result, after the fuel is read; a call that raises never gets here. Every call has a
        # table since spec 048; a guard table's walk does nothing (no mount, nothing owed).
        table.walk()
    finally:
        if tool_host is not None:  # the call's tool loop, ended without waiting (spec 053)
            tool_host.close()
        # The store holds every descriptor the guest opened; a guest can open them until the
        # host refuses. Close it first, so the clean-up below has descriptors to work with, and
        # make that clean-up unable to raise (the 0.1.0a2 security review, F1).
        store.close()
        with _outputs_lock:  # the guest has ended; wasmtime frees the keys later, on its own thread
            for key in keys:
                _outputs.pop(key, None)
        if table is not None:  # the record kept, the rest dropped now (the build review, F3)
            # A guard table is never reported: `files` is None without mounts (spec 048).
            files = table.record() if mounts else None
            table.release()
        for p in mounted:
            p.walked.close()
        if scratch is not None:
            scratch.remove()
    truncated = tuple(s.name for s in (out, err) if s.dropped)
    record = None if tool_host is None else tool_host.record  # on every ending (C6)
    return Completed(
        done.exit_code,
        bytes(out.data),
        bytes(err.data),
        done.trapped,
        fuel_used,
        truncated,
        files,
        record,
    )


def _fuel_used(
    fuel: int | None, done: _Driven, call: _Call, remaining: Callable[[], int]
) -> int | None:
    """The instructions the guest ran, or None when the count is meaningless: after an epoch
    interrupt wasmtime's fuel counter is not brought up to date (spec 001 landing notes), and a
    stopped call ended on one (spec 011)."""
    if fuel is None or done.trapped == "deadline":
        return None
    table = getattr(call, "table", None)
    held = None if table is None else table.stop_fuel
    if held is not None and call.ended is None and call.stopped is held[0]:
        # A forward's own trap or error, or an ABI error a served call raised (spec 032): the
        # count read then is the guest's, as when wasmtime's WASI meets it directly.
        return fuel - held[1]
    if call.stopped is not None or call.ended is not None:
        return None
    return fuel - remaining() if done.metered else 0


class _Driven(NamedTuple):
    exit_code: int | None
    trapped: str | None
    metered: bool  # the cap is set only once instantiation has succeeded
    instance: Any


def _drive(
    wt: Any,
    linker: Any,
    store: Any,
    module: Any,
    call: _Call,
    fuel: int | None,
    preopens: list[_Preopen] = (),  # type: ignore[assignment]
    check: Any = None,
    plain: Any = None,
) -> _Driven:
    """Instantiate and run the guest with its call on this thread's stack. What a host function
    caught and recorded comes first: an exit or a trap is the call's result, and any other
    exception (Ctrl-C, a host's cancellation) is raised here, on the thread that made the call
    (spec 011). `plain` is today's linker when `linker` is the mount linker: the identity check
    reads wasmtime's own answers through it, and the trampoline takes wasmtime's calls from it
    (spec 032)."""
    not_ready = _trap_handlers_ready()  # spec 071, Decision 9: before every entry into the guest
    if not_ready is not None:
        raise RuntimeError(_TRAP_HANDLERS_REPLACED.format(signal=not_ready))
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
        own = linker if plain is None else plain
        if preopens:
            _check_preopens(wt, own, store, check, list(preopens))  # spec 017, Decision 5
        instance = linker.instantiate(store, module)
        if call.table is not None:  # after the guest, before the fuel cap and _initialize
            call.table.bind(wt, store, own, instance)
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
        e.__traceback__ = None  # its frames hold this call: freed now, not by the collector
    except wt.WasmtimeError as e:
        trapped = _first_line(str(e))
        e.__traceback__ = None
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
        cause.__traceback__ = None  # a reported stop's frames hold this call (spec 032, F3)
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
        table: Any = None,
        admit: Callable[[int], bytes | None] | None = None,
    ) -> None:
        self.context = _context_address(store)
        self.origin_ns = origin_ns  # its waits count from here (spec 055, the review's F6)
        self.door = _door(host, admit)  # admit: the frame host's, under tools= (spec 036)
        self.poll = _poll_oneoff(origin_ns, waits)
        self.stopped: BaseException | None = None
        self.cancel = cancel
        self.stop_at = stop_at
        # "cancelled" or "deadline", from the epoch callback; "out of file calls" (spec 032)
        self.ended: str | None = None
        self.table = table  # the call's mount table (spec 032), or its guard table (spec 048)
        if table is not None:
            table.call = self

    def files(self, caller: Any, name: str, *args: int) -> int:
        """One of the 29 shadowed calls, for a call with mounts (spec 032), or one of the two
        the guard shadows, for a call without (spec 048)."""
        if self.table is None:
            return EBADF
        return self.table(caller, name, *args)

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


def _shared(kind: str, refused: int, stopped: int, *bound: Any) -> Callable[..., int]:
    """A host function defined once per engine. It serves the call on top of this thread's
    stack, and only when the caller is that call's store; it never raises into wasmtime-py,
    whose exceptions travel by a process-wide slot (spec 011). `bound` goes before the guest's
    arguments: a file shadow's name (spec 032)."""

    import wasmtime as wt

    wasmtime_errors = (wt.Trap, wt.WasmtimeError)

    def function(caller: Any, *args: int) -> int:
        call = None
        try:
            stack = _stack()
            call = stack[-1] if stack else None
            if call is None or _context_address(caller) != call.context:
                return refused
            # Ctrl-C comes before the guard below: a pending Ctrl-C is recorded even for a call
            # the epoch callback has ended (spec 015's order).
            if call.stopped is None and _ctrl_c_watched() and _ctrl_c["pending"]:
                _ctrl_c["pending"] = False
                raise KeyboardInterrupt
            if call.stopped is not None or call.ended is not None:
                return stopped  # no host function runs for a stopped or ended call (spec 030)
            answer = getattr(call, kind)(caller, *bound, *args)
            if _ctrl_c_watched() and _ctrl_c["pending"]:  # Ctrl-C during a wait
                _ctrl_c["pending"] = False
                raise KeyboardInterrupt
            if call.cancel is not None and call.cancel.is_set():
                _epoch_now(caller)  # the epoch callback names it at the guest's next entry
            return answer
        except BaseException as cause:
            try:
                if (
                    call is not None
                    and call.ended is not None
                    and isinstance(cause, wasmtime_errors)
                ):
                    # The invariant (specs 030 and 032): while the guest runs, `call.ended` is
                    # set only where the runner also stops the guest by its own act in the same
                    # step: by the epoch callback, on a path that returns an error; or by the
                    # file-call limit's shadow (spec 032), which sets the epoch deadline to 0
                    # before it returns (`_drive` sets it only before any guest code runs). So a
                    # Trap or WasmtimeError caught here after `ended` is set is the runner's own
                    # stop surfacing: the callback's error, met in host_alloc after a door call
                    # outlived the callback's window, or at a forward's trampoline entry. The
                    # limit's shadow raises nothing, and once `ended` is set the guard above
                    # keeps every later host function, forwards included, from running. It is
                    # not a stop: `_drive` names the run from `ended`. ExitTrap is a
                    # WasmtimeError, and it cannot occur here, because the callback's error
                    # aborts host_alloc first. Keep this test this narrow: any other exception,
                    # or one caught before `ended`, is a stop.
                    _epoch_now(caller)  # the guest stops at its next function entry
                elif call is not None:
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
    recorded stop holds, a named end holds (spec 032: the first named end, such as "out of file
    calls", is kept under `cancel=` too), a deferred Ctrl-C becomes a stop, then a cancel, then
    the deadline; otherwise continue for up to CANCEL_TICKS ticks. 0 continues; an error (an int
    address) stops the guest (spec 015)."""
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
        if call.ended is not None:
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
_mount_linkers: dict[Any, Any] = {}
_guard_linkers: dict[Any, Any] = {}
_trampolines: dict[Any, Any] = {}
_stat_trampolines: dict[Any, Any] = {}


def _linker(wt: Any, engine: wasmtime.Engine) -> Any:
    """The engine's one linker: WASI, the shadowed poll_oneoff and the door, defined once, so a
    call adds nothing to wasmtime-py's process-wide table of host functions (spec 011)."""
    with _lock:
        linker = _linkers.get(engine)
        if linker is None:
            linker = _linkers[engine] = _runner_linker(wt, engine)
        return linker


def _runner_linker(wt: Any, engine: wasmtime.Engine) -> Any:
    linker = wt.Linker(engine)
    linker.define_wasi()
    linker.allow_shadowing = True
    i32 = wt.ValType.i32()
    ty = wt.FuncType([i32] * 4, [i32])
    poll = _shared("poll", EINVAL, EINVAL)
    linker.define_func("wasi_snapshot_preview1", "poll_oneoff", ty, poll, True)
    linker.define_func("host", "call", ty, _shared("door", NO_HOST, HOST_FAULT), True)
    return linker


def _mount_linker(wt: Any, engine: wasmtime.Engine) -> Any:
    """The engine's second linker, used only by calls with mounts (spec 032, Decision 1):
    today's, plus a shadow over each of the 29 calls in `mounts.SHADOWED`, each in the shared
    form, answering EBADF to a caller that is not its call's store and EIO once its call has
    stopped. Defined once per engine, like the first."""
    from .mounts import SIGNATURES

    with _lock:
        linker = _mount_linkers.get(engine)
        if linker is None:
            linker = _runner_linker(wt, engine)
            kinds = {"i32": wt.ValType.i32(), "i64": wt.ValType.i64()}
            for name, params in SIGNATURES.items():
                ty = wt.FuncType([kinds[p] for p in params], [kinds["i32"]])
                shadow = _shared("files", EBADF, EIO, name)
                linker.define_func("wasi_snapshot_preview1", name, ty, shadow, True)
            _mount_linkers[engine] = linker
        return linker


def _guard_linker(wt: Any, engine: wasmtime.Engine) -> Any:
    """The engine's third linker, used by every call without mounts (spec 048, Decision 7):
    today's, plus a shadow over the two calls in `mounts.GUARDED` (fd_readdir and path_rename)
    and the three in `mounts.COUNTED` (path_open, fd_close and fd_renumber, which the table
    forwards and counts against the call's cap on open files; spec 068), in the shared form, as
    the mount linker's. Every other call stays wasmtime's own. Defined once per engine, like the
    others."""
    from .mounts import COUNTED, GUARDED, SIGNATURES

    with _lock:
        linker = _guard_linkers.get(engine)
        if linker is None:
            linker = _runner_linker(wt, engine)
            kinds = {"i32": wt.ValType.i32(), "i64": wt.ValType.i64()}
            for name in GUARDED + COUNTED:
                ty = wt.FuncType([kinds[p] for p in SIGNATURES[name]], [kinds["i32"]])
                shadow = _shared("files", EBADF, EIO, name)
                linker.define_func("wasi_snapshot_preview1", name, ty, shadow, True)
            _guard_linkers[engine] = linker
        return linker


def _stat_trampoline_module(wt: Any, engine: wasmtime.Engine) -> Any:
    """The rename rule's stat trampoline, with its own one-page memory, compiled once per engine
    and instantiated per call (spec 048, Decision 2)."""
    from .mounts import stat_trampoline_wat

    with _lock:
        module = _stat_trampolines.get(engine)
        if module is None:
            module = _stat_trampolines[engine] = wt.Module(engine, stat_trampoline_wat())
        return module


def _trampoline_module(wt: Any, engine: wasmtime.Engine) -> Any:
    """The forwarders, compiled once per engine and instantiated per call (spec 032)."""
    from .mounts import trampoline_wat

    with _lock:
        module = _trampolines.get(engine)
        if module is None:
            module = _trampolines[engine] = wt.Module(engine, trampoline_wat())
        return module


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


EINVAL, ENOMEM, EBADF, EFAULT, EIO = 28, 48, 8, 21, 29  # WASI preview1 errno values
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


def _door(
    host: Host | None, admit: Callable[[int], bytes | None] | None = None
) -> Callable[..., int]:
    """host::call(ptr, len, out_ptr_ptr, out_len_ptr) -> 0, -1 or -2 (spec 003, Decision 5).

    With `admit` (the tool protocol's frame host, spec 036), each frame's length is offered to
    it once the addresses are checked and before the frame is read: bytes it returns are the
    answer, and the frame is never copied out of guest memory, so a refused frame costs the
    host the same whatever its length. The raw `host=` path passes no `admit`, as before."""

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
        response = None if admit is None else admit(length)
        if response is None:
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


def _stamp(st: os.stat_result) -> tuple[int, ...]:
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def _real_dir_at(fd: int, parts: tuple[str, ...]) -> int:
    """A descriptor on fd/parts…, each a real directory, each step taken from the folder before:
    a link or file a guest left in the way is removed, never followed (spec 024). The caller
    closes the result; `fd` stays open."""
    here = os.dup(fd)
    try:
        for part in parts:
            try:
                st = os.stat(part, dir_fd=here, follow_symlinks=False)
            except FileNotFoundError:
                st = None
            if st is not None and not stat.S_ISDIR(st.st_mode):
                os.unlink(part, dir_fd=here)  # a symbolic link or a file: removed, never followed
                st = None
            if st is None:
                try:
                    os.mkdir(part, dir_fd=here)
                except FileExistsError:  # a concurrent call made it
                    pass
            child = os.open(part, _DIR, dir_fd=here)  # O_NOFOLLOW: a link put there fails
            os.close(here)
            here = child
    except BaseException:
        os.close(here)
        raise
    return here


def _real_dir(root: Path, parts: tuple[str, ...]) -> Path:
    """root/parts…, each a real directory: a link or file a guest left in the way is removed.
    Windows only, where the walk holds every folder of the root's path (spec 017, Decision 5) and
    guests cannot make links; elsewhere `_real_dir_at`. The root is never made again here."""
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


GUEST_PACKAGE = "recipes/guest/host/tools.py"  # MANIFEST's recipe line for the guest package
_guest_packages: dict[str, tuple[tuple[int, ...], bool]] = {}  # path: (its stamp, the answer)


def _has_guest_package(manifest: Path) -> bool:
    """Whether MANIFEST names the tool protocol's guest package among its recipes (spec 036,
    Decision 1). Cached per path and stat stamp, with no lock: a race only reads it twice."""
    key = str(manifest)
    stamp = _stamp(os.stat(manifest))
    hit = _guest_packages.get(key)
    if hit is not None and hit[0] == stamp:
        return hit[1]
    found = False
    for line in Path(manifest).read_text().splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] == "recipe" and parts[-1] == GUEST_PACKAGE:
            found = True
            break
    _guest_packages[key] = (stamp, found)
    return found


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
_counts = {"compiled": 0, "loaded": 0, "written": 0, "sessions_open": 0}


def stats() -> dict[str, int]:
    """Counts kept by this process, a diagnostic.

    `tool_threads_running` counts the tool threads alive in this process, abandoned ones
    included. `sessions_open` counts the `Session`s opened and not yet ended. `compiled`,
    `loaded` and `written` count how this process got its compiled modules: compiled from the
    binary, loaded from a .cwasm file, and .cwasm files written; what they count may change with
    the cache. A later release may add keys.
    """
    # spec 036, Decision 5; the judge reads it.
    with _lock:
        counts = dict(_counts)
    with _tool_threads_lock:
        counts["tool_threads_running"] = _tool_threads["running"]
    return counts


# The tool threads alive in this process (spec 036, Decision 5): one per tool call, counted in
# as it starts and out as it ends, after its call returned or not.
_tool_threads_lock = threading.Lock()
_tool_threads = {"running": 0}


def _count_tool_threads(delta: int) -> None:
    with _tool_threads_lock:
        _tool_threads["running"] += delta


def _ctrl_c_now() -> bool:
    """A Ctrl-C is pending for the call on this (the main) thread: read, never cleared."""
    return _ctrl_c_watched() and _ctrl_c["pending"]


def _tool_host(c: dict[str, Any], stop_at: int | None, cancel: Any) -> _ToolHost | None:
    """The call's frame host, for a call with tools=, bound by the call's deadline, its cancel
    and Ctrl-C (spec 036, Decisions 2 to 5); None otherwise."""
    if c.get("tools") is None:
        return None
    from .tools import _Bounded, _ToolHost, _ToolLoop

    bound = _Bounded(
        tick_s=TICK_S,
        stop_at=stop_at,
        ticks=lambda: _epoch_ticker.count(),
        cancel=cancel,
        ctrl_c=_ctrl_c_now,
        count=_count_tool_threads,
    )
    # Under run_async, the caller's loop; otherwise a private loop of the call's own (spec 053).
    tool_loop = _ToolLoop(c.get("tool_loop"), count=_count_tool_threads)
    return _ToolHost(
        c["tools"],
        gate=c["gate"],
        max_calls=c["tool_calls"],
        invoke=bound,
        tool_loop=tool_loop,
        max_bytes=c.get("tool_request_bytes"),  # spec 060; a hand-built c without it: no limit
    )


@atexit.register
def _release() -> None:
    """Remove this process's zip folders, and free the cached linkers, modules and engines while
    wasmtime's bindings still exist."""
    _remove_zips()
    _check_modules.clear()
    _linkers.clear()
    _mount_linkers.clear()
    _guard_linkers.clear()
    _trampolines.clear()
    _stat_trampolines.clear()
    _modules.clear()
    _engines.clear()


# wasmtime's default wasm stack, stated (spec 071, Decision 3): the guest's C-stack window (128 KiB,
# recipes/reactor_main.c) is sized for it, and wasm runs on the calling thread's own stack, so a
# larger limit than the thread has would end the host process instead of trapping.
_WASM_STACK = 512 * 1024


def _engine(metered: bool) -> wasmtime.Engine:
    """Two engines per process: fuel metering changes the compiled code."""
    import wasmtime as wt

    with _lock:
        if metered not in _engines:
            _fork["used"] = True  # before the engine exists: a fork from here on is refused
            cfg = wt.Config()
            cfg.consume_fuel = metered
            cfg.epoch_interruption = True
            cfg.max_wasm_stack = _WASM_STACK
            _engines[metered] = wt.Engine(cfg)
        return _engines[metered]


# Linux: the fatal signals wasmtime 49 handles to turn a fault in wasm into a trap
# (crates/wasmtime/src/runtime/vm/sys/unix/signals.rs, foreach_handler): SIGSEGV and SIGILL, and
# SIGFPE on x86_64. Its handlers are installed when the first engine is made (spec 071, Decision 9).
_TRAP_SIGNALS = ("SIGSEGV", "SIGILL")
_TRAP_SIGNALS_X86_64 = ("SIGFPE",)
_TRAP_HANDLERS_REPLACED = (
    "wasmtime's handler for {signal} was replaced after the first run, by a handler installed or "
    "removed since (faulthandler, signal.signal, or a native crash reporter); a trap in the guest "
    "would end or hang this process, so the call was refused. If faulthandler.enable() was "
    "called after the first run, faulthandler.disable() undoes it; otherwise restart the "
    "process, and install faulthandler or any crash reporter before the first run"
)
_handlers: dict[str, Any] = {}  # the C library's sigaction and dladdr, and wasmtime's load base


class _DlInfo(ctypes.Structure):
    _fields_ = [
        ("dli_fname", ctypes.c_char_p),
        ("dli_fbase", ctypes.c_void_p),
        ("dli_sname", ctypes.c_char_p),
        ("dli_saddr", ctypes.c_void_p),
    ]


def _load_base(address: int | None) -> int | None:
    """The load base of the shared object that holds `address`, by dladdr; None if none does."""
    if not address or address in (1,):  # SIG_DFL (0) and SIG_IGN (1) are in no object
        return None
    info = _DlInfo()
    if not _handlers["dladdr"](ctypes.c_void_p(address), ctypes.byref(info)):
        return None
    return info.dli_fbase or None


def _handler_base(signum: int) -> int | None:
    """The load base of the object holding `signum`'s installed handler (the first word of
    `struct sigaction` in glibc and musl alike), or None."""
    buf = (ctypes.c_char * 1024)()  # larger than any struct sigaction
    if _handlers["sigaction"](signum, None, buf) != 0:
        return None
    return _load_base(ctypes.c_void_p.from_buffer(buf).value)


def _wasmtime_base() -> int | None:
    """The load base of wasmtime-py's own library, read once, from one of its symbols."""
    if "wasmtime" not in _handlers:
        from wasmtime import _ffi

        symbol = ctypes.cast(_ffi.dll.wasm_engine_new, ctypes.c_void_p).value
        _handlers["wasmtime"] = _load_base(symbol)
    return _handlers["wasmtime"]


def _trap_handlers_ready(
    platform: str | None = None,
    machine: str | None = None,
    handler_base: Callable[[int], int | None] | None = None,
    wasmtime_base: Callable[[], int | None] | None = None,
) -> str | None:
    """None when a trap in the guest would reach wasmtime; else the first signal whose handler is
    not wasmtime's (spec 071, Decision 9). Only on Linux, where wasmtime catches traps with signal
    handlers that a later faulthandler.enable() or disable(), a signal.signal or a native crash
    reporter can replace; macOS uses Mach ports and Windows a vectored handler. Exact for
    faulthandler, conservative for other handlers. Any failure counts as not ready."""
    import signal as signals

    if not (platform if platform is not None else sys.platform).startswith("linux"):
        return None
    names = _TRAP_SIGNALS
    if (machine if machine is not None else os.uname().machine) == "x86_64":
        names += _TRAP_SIGNALS_X86_64
    name = names[0]
    try:
        if handler_base is None or wasmtime_base is None:
            if "sigaction" not in _handlers:
                libc = ctypes.CDLL(None, use_errno=True)
                libc.sigaction.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p]
                libc.sigaction.restype = ctypes.c_int
                libc.dladdr.argtypes = [ctypes.c_void_p, ctypes.POINTER(_DlInfo)]
                libc.dladdr.restype = ctypes.c_int
                _handlers["dladdr"], _handlers["sigaction"] = libc.dladdr, libc.sigaction
            handler_base = handler_base or _handler_base
            wasmtime_base = wasmtime_base or _wasmtime_base
        ours = wasmtime_base()
        for name in names:
            if ours is None or handler_base(int(getattr(signals, name))) != ours:
                return name
    except Exception:
        return name
    return None


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


# ---------------------------------------------------------------------------------------------
# Sessions (spec 055): one instance of the guest kept across turns, with an idle bound and a
# lifetime, ended by Python's own shutdown inside a small budget, as a Jupyter kernel is.

MAX_TURN_BYTES = 0x7FFFFFFF  # the `turn` export's length is an i32
SESSION_EXPORTS = ("turn", "shutdown")

# Injected so the judge never sleeps (Decision 9): the one clock the bounds read.
_session_clock: Callable[[], float] = time.monotonic
# Test hooks: told each arming ("turn" or "ending", its epoch ticks); told each export called
# on a session's instance ("turn" or "shutdown", the thread's ident); called after a turn's
# export returned, before its ending is decided (criterion 42).
_on_arm: Callable[[str, int], None] | None = None
_on_export: Callable[[str, int], None] | None = None
_after_export: Callable[[], None] | None = None
_on_call: Callable[[str, Any], None] | None = None  # told each call built: (kind, its _Call)


class SessionEnded(RuntimeError):
    """A session has ended, so it runs no more turns.

    Attributes:
        reason: Why it ended, the value of `Session.ended`: "closed", "idle", "lifetime",
            "quit", "exit" or "error", one of `Completed.trapped`'s four fixed strings, or
            wasmtime's words for a trap.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(f"the session has ended: {reason}")
        self.reason = reason


class _Either:
    """A stop that is set when either event is: a turn's `cancel`, or its session's closing."""

    __slots__ = ("first", "second")

    def __init__(self, first: threading.Event | None, second: threading.Event) -> None:
        self.first, self.second = first, second

    def is_set(self) -> bool:
        return (self.first is not None and self.first.is_set()) or self.second.is_set()


class _State:
    """Everything a session holds: its store and folders, its limits and its flags. It never
    refers to its `Session`, so the collector can finalize a dropped one (Decision 13)."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.ended: str | None = None
        self.outcome: str | None = None
        self.busy = False
        self.closing = threading.Event()  # set with `ended`: stops a running turn
        self.done = threading.Event()  # the ending has finished; everything is released
        self.turn_thread: int | None = None
        self.ending_thread: int | None = None
        self.called = False  # a turn's export was called
        self.sound = False  # the last turn's export returned: the interpreter is safe to enter
        self.needs_initialize = False
        self.opened = 0.0
        self.last_end = 0.0
        self.idle_s: float | None = None
        self.lifetime_s: float | None = None
        self.shutdown_s = 0.0
        self.c: dict[str, Any] = {}
        self.wt: Any = None
        self.engine: Any = None
        self.store: Any = None
        self.exports: Any = None
        self.keys: tuple[int, int] = (0, 0)
        self.table: Any = None
        self.host: Host | None = None
        self.metered = False
        self.origin_ns = 0
        self.bounded: Any = None
        self.private_loop: Any = None
        self.scratch: _Private | None = None
        self.private: _Private | None = None
        self.walked: list[_Walked] = []
        self.home: tuple[str, Path | None, int | None] | None = None
        self.counted = False
        self.context: Any = None  # a copy taken at the opening, for a closer (the re-review's F7)


_sessions_lock = threading.Lock()
_sessions: weakref.WeakSet[_State] = weakref.WeakSet()
# enabled: the judge may open sessions without the thread; paused: it may drive `_reap` alone.
_reaper: dict[str, Any] = {
    "thread": None,
    "stop": False,
    "enabled": True,
    "paused": False,
    "hooked": False,
}
_reaper_queue: queue.SimpleQueue[Any] = queue.SimpleQueue()
_WAKE = object()
_dropped: collections.deque[_State] = collections.deque()  # taken from the queue, not yet ended
_closers_lock = threading.Lock()
_closers: set[threading.Thread] = set()


def _wake_reaper() -> None:
    _reaper_queue.put(_WAKE)


def _take_dropped() -> list[_State]:
    """Every dropped session the reaper has been told of and not yet ended, in order."""
    out = []
    while True:
        try:
            item = _reaper_queue.get_nowait()
        except queue.Empty:
            break
        if isinstance(item, _State):
            _dropped.append(item)
    while _dropped:
        out.append(_dropped.popleft())
    return out


def _collected(state: _State) -> None:
    """The collector's finalizer for a dropped session: no lock, nothing closed; the state goes
    to the reaper, which ends it on its own thread (the review's F9, the Confirmation's N2)."""
    if not _fork["forked"]:
        _reaper_queue.put(state)


def _due(state: _State) -> tuple[float, str] | None:
    """The first moment one of the session's bounds passes, and which; None for no bound."""
    due = []
    if state.idle_s is not None:
        due.append((state.last_end + state.idle_s, "idle"))
    if state.lifetime_s is not None:
        due.append((state.opened + state.lifetime_s, "lifetime"))
    return min(due) if due else None


def _mark(state: _State, reason: str) -> bool:
    """Under the state's lock: set `ended` once, by the first cause; True if this call set it."""
    if state.ended is not None:
        return False
    state.ended = reason
    state.closing.set()
    return True


def _start_closer(state: _State) -> None:
    """Run an ending the runner starts itself on a closer thread of its own (Decision 8)."""
    context = state.context.copy() if state.context is not None else None
    target = _end_quietly if context is None else functools.partial(context.run, _end_quietly)
    thread = threading.Thread(
        target=target, args=(state,), name="wasi-python-session-closer", daemon=True
    )
    with _closers_lock:
        _closers.add(thread)
    thread.start()


def _end_quietly(state: _State) -> None:
    try:
        _end_session(state, _CLOSER)
    except BaseException:
        pass  # a closer has no caller: the outcome records the stop
    finally:
        with _closers_lock:
            _closers.discard(threading.current_thread())


_start_ending: Callable[[_State], None] = _start_closer  # injected by the judge (criterion 7)


def _reap(now: float) -> float | None:
    """The reaper's one step: end every session whose bound has passed at `now` and that has no
    turn running, each ending handed to `_start_ending`; the seconds until the next is due, or
    None when none is (Decision 9)."""
    for item in _take_dropped():  # the collector's finalizer queued them (Decision 13)
        _end_dropped(item)
    with _sessions_lock:
        states = list(_sessions)
    wait: float | None = None
    for state in states:
        start = False
        with state.lock:
            due = _due(state)
            if state.ended is not None or state.busy or due is None:
                continue
            if now >= due[0]:
                start = _mark(state, due[1]) and _claim_ending(state, _CLOSER)
            else:
                left = due[0] - now
                wait = left if wait is None else min(wait, left)
        if start:
            _start_ending(state)
    return wait


def _reaper_loop(
    get: Callable[[float | None], Any] | None = None,
    clock: Callable[[], float] | None = None,
    rounds: int | None = None,
) -> None:
    """The reaper: wait on the queue until the next bound is due or a session is dropped or
    changes, then take one step. `get` and `clock` are injected by the judge, with a number of
    `rounds`, so it never sleeps (Decision 9)."""
    wait: float | None = None
    done = 0
    while rounds is None or done < rounds:
        done += 1
        try:
            item = (get or (lambda w: _reaper_queue.get(timeout=w)))(wait)
        except queue.Empty:
            item = _WAKE
        if _reaper["stop"]:
            if item is not _WAKE:
                _reaper_queue.put(item)  # for the exit hook to drain
            return
        if isinstance(item, _State):
            _dropped.append(item)  # `_reap` takes it, in order
        if _reaper["paused"]:
            wait = None
            continue
        try:
            wait = _reap((clock or _session_clock)())
        except BaseException:
            wait = TICK_S  # never dies: try again soon


def _end_dropped(state: _State) -> None:
    with state.lock:
        start = not state.busy and _mark(state, "closed") and _claim_ending(state, _CLOSER)
    if start:
        _start_ending(state)


def _ensure_reaper() -> None:
    """The reaper thread, a daemon started with the first session, and the exit hook."""
    with _sessions_lock:
        if not _reaper["hooked"]:
            atexit.register(_sessions_at_exit)  # after _release's: so it runs first
            _reaper["hooked"] = True
        if _reaper["enabled"] and _reaper["thread"] is None and not _reaper["stop"]:
            thread = threading.Thread(target=_reaper_loop, name="wasi-python-reaper", daemon=True)
            _reaper["thread"] = thread
            thread.start()


def _sessions_at_exit() -> None:
    """Stop the reaper and wait for its step; end the sessions on the collector's queue and
    every session at rest, each on its own closer, side by side; mark those whose turn still
    runs; then wait for every ending in progress (Decision 13; the re-review's F8)."""
    _reaper["stop"] = True
    thread = _reaper["thread"]
    _reaper_queue.put(_WAKE)
    if thread is not None and thread is not threading.current_thread():
        thread.join()
    states: list[_State] = _take_dropped()
    with _sessions_lock:
        states += [s for s in _sessions if s not in states]
    for state in states:
        with state.lock:
            _mark(state, "closed")
            start = not state.busy and _claim_ending(state, _CLOSER)
        if start:
            _start_closer(state)
    for state in states:
        state.done.wait()
    with _closers_lock:
        closers = list(_closers)
    for closer in closers:
        closer.join()


_CLOSER = -1  # `ending_thread` while a closer thread is being started for the ending


def _claim_ending(state: _State, owner: int) -> bool:
    """Under the state's lock: name who runs the ending, if no one does yet (Decision 8: a turn's
    thread, `close()`'s caller, or a closer)."""
    if state.ending_thread is not None or state.done.is_set():
        return False
    state.ending_thread = owner
    return True


def _end_session(state: _State, owner: int | None = None) -> BaseException | None:
    """The ending (Decision 8), on this thread, once: Python's shutdown if it applies, then
    everything released. `owner` is the claim the caller holds (`_claim_ending`); with none, it
    claims the ending if no one has. Returns what the embedder's code raised during it (a
    Ctrl-C, a `BaseException`), for a caller to raise; another's ending returns None at once."""
    me = threading.get_ident()
    with state.lock:
        if state.done.is_set():
            return None
        if state.ending_thread is None:
            state.ending_thread = me
        elif owner is not None and state.ending_thread == owner:
            state.ending_thread = me
        else:
            return None
    outcome, raised = "skipped", None
    try:
        try:
            if _shutdown_applies(state):
                outcome, raised = _shutdown(state)
        except BaseException as e:
            outcome, raised = "stopped", e
        finally:
            _release_session(state)
    finally:
        with state.lock:
            state.outcome = outcome
        state.done.set()
        _wake_reaper()
    return raised


def _shutdown_applies(state: _State) -> bool:
    return (
        state.called
        and state.sound
        and not state.busy
        and state.shutdown_s > 0
        and not _fork["forked"]
        and state.store is not None
    )


def _ending_seconds(state: _State, now: float) -> float:
    """The seconds the ending may run guest code: its budget, capped so it ends by the opening
    plus the lifetime plus the budget (the re-review's F2)."""
    end = now + state.shutdown_s
    if state.lifetime_s is not None:
        end = min(end, state.opened + state.lifetime_s + state.shutdown_s)
    return end - now


def _shutdown(state: _State) -> tuple[str, BaseException | None]:
    """Python's shutdown through the `shutdown` export, inside the budget: ("finished" or
    "stopped" or "skipped", what the embedder's code raised)."""
    left = _ending_seconds(state, _session_clock())
    if left <= 0:
        return "skipped", None
    if _trap_handlers_ready() is not None:  # a trap in the shutdown could end this process
        return "skipped", None  # (spec 071, Decision 9)
    ticks = max(1, math.ceil(left / TICK_S))
    fuel = state.c["fuel"] if state.metered else None
    call, _out, _err, tool_host = _arm(state, "ending", fuel, ticks, None, 0, None)
    wt, store = state.wt, state.store
    value = exited = None
    trapped: str | None = None
    stack = _stack()
    stack.append(call)
    _calls.lost = False
    try:
        with _epoch_ticker(state.engine, True):
            try:
                if _on_export is not None:
                    _on_export("shutdown", threading.get_ident())
                value = state.exports["shutdown"](store)
            except wt.ExitTrap as e:
                exited = e.code
            except wt.Trap as e:
                trapped = _trap_name(e)
                e.__traceback__ = None
            except wt.WasmtimeError as e:
                trapped = _first_line(str(e))
                e.__traceback__ = None
            finally:
                stack.pop()
                lost, _calls.lost = getattr(_calls, "lost", False), False
        raised: BaseException | None = None
        cause = call.stopped
        if lost:
            outcome = "stopped"
        elif cause is not None:
            outcome = "finished" if isinstance(cause, wt.ExitTrap) else "stopped"
            if not isinstance(cause, (wt.Trap, wt.WasmtimeError)):
                raised = cause  # a Ctrl-C, or the embedder's own BaseException
            cause.__traceback__ = None
        elif call.ended is not None or trapped is not None:
            outcome = "stopped"
        elif exited is not None or value in (0, 120):
            outcome = "finished"
        else:
            outcome = "stopped"  # a runner fault: quiet here (the re-review's N3)
        if raised is None and not lost:
            # spec 034's walk, its Ctrl-C check included (the re-review's F4), and made at exit
            # too, whatever run_async's exit hook set (the build review's F1)
            state.table.walk(ending=True)
        return outcome, raised
    finally:
        if tool_host is not None and state.private_loop is not None:
            state.private_loop.cancel_tasks()  # the loop itself closes with the session's release


def _release_session(state: _State) -> None:
    """Close the store and free everything the session held; never raises."""
    steps: list[Callable[[], Any]] = []
    if state.private_loop is not None:
        steps.append(state.private_loop.close)
    if state.store is not None:
        steps.append(state.store.close)
    steps.append(lambda: _drop_keys(state.keys))
    if state.table is not None:
        steps.append(state.table.release)
    for w in state.walked:
        steps.append(w.close)
    if state.scratch is not None:
        steps.append(state.scratch.remove)
    if state.home is not None:
        steps.append(lambda: _remove_home(state.home))
    if state.private is not None:
        steps.append(state.private.remove)
    for step in steps:
        try:
            step()
        except BaseException:
            pass
    state.store = state.exports = state.table = None
    with _lock:
        if state.counted:
            _counts["sessions_open"] -= 1
            state.counted = False
    with _sessions_lock:
        _sessions.discard(state)


def _drop_keys(keys: tuple[int, int]) -> None:
    with _outputs_lock:
        for key in keys:
            _outputs.pop(key, None)


def _remove_home(home: tuple[str, Path | None, int | None]) -> None:
    name, tmp, tmp_fd = home
    try:
        if tmp_fd is not None:
            shutil.rmtree(name, ignore_errors=True, dir_fd=tmp_fd)
        elif tmp is not None:
            shutil.rmtree(tmp / name, ignore_errors=True)
    finally:
        _close(tmp_fd)


def _arm(
    state: _State,
    kind: str,
    fuel: int | None,
    ticks: int,
    stop: Any,
    output_bytes: int | None,
    loop: Any,
) -> tuple[_Call, _Stream, _Stream, Any]:
    """One call into the session's instance: its fuel and epoch deadline re-armed, its waits on
    the session's clock base, fresh output streams, a frame host and mount counters of its own
    (Decision 7, step 2)."""
    store = state.store
    if state.metered:
        store.set_fuel(UNMETERED if fuel is None else fuel)
    store.set_epoch_deadline(min(CANCEL_TICKS, ticks))  # the session's callback checks the rest
    if _on_arm is not None:
        _on_arm(kind, ticks)
    stop_at = None if ticks >= NO_DEADLINE else _stop_at(_epoch_ticker.count(), ticks)
    checks: list[Callable[[], bool]] = []
    if stop_at is not None:
        checks.append(lambda: _epoch_ticker.count() >= stop_at)
    if stop is not None:
        checks.append(stop.is_set)
    if _ctrl_c_watched():
        checks.append(lambda: _ctrl_c["pending"])
    waits = _Waits(
        lambda: time.perf_counter(),
        time.sleep,
        (lambda: any(check() for check in checks)) if checks else None,
    )
    out, err = _Stream("stdout", output_bytes), _Stream("stderr", output_bytes)
    with _outputs_lock:
        _outputs[state.keys[0]], _outputs[state.keys[1]] = out, err
    host, admit, tool_host = state.host, None, None
    if state.c.get("tools") is not None:
        tool_host = _session_tool_host(state, stop_at, stop, loop)
        host, admit = tool_host, tool_host.admit
    state.table.new_turn()
    call = _Call(store, host, waits, state.origin_ns, stop, stop_at, state.table, admit)
    if _on_call is not None:
        _on_call(kind, call)
    return call, out, err, tool_host


def _session_tool_host(state: _State, stop_at: int | None, stop: Any, loop: Any) -> Any:
    """A frame host per turn; one bound per session, so abandoned tool threads are counted
    across its turns; one private tool loop per session for its synchronous turns, or the
    caller's loop for a turn by run_async (Decision 5, Decision 11)."""
    from .tools import _ToolHost, _ToolLoop

    c = state.c
    state.bounded.rearm(stop_at, stop)
    if loop is not None:
        tool_loop = _ToolLoop(loop, count=_count_tool_threads)
    else:
        if state.private_loop is None:
            state.private_loop = _ToolLoop(None, count=_count_tool_threads)
        tool_loop = state.private_loop
    return _ToolHost(
        c["tools"],
        gate=c["gate"],
        max_calls=c["tool_calls"],
        invoke=state.bounded,
        tool_loop=tool_loop,
        max_bytes=c.get("tool_request_bytes"),
    )


class _TurnDone(NamedTuple):
    completed: Completed
    cause: str | None  # what ends the session, if the turn does
    returned: bool  # the export returned a status: the interpreter is sound


def _drive_turn(
    state: _State, call: _Call, data: bytes
) -> tuple[int | None, int | None, str | None, bool]:
    """(the export's value, an exit code, a trap's name, whether guest code ran), on this
    thread's stack, by `_drive`'s rules (Decision 7, steps 3 and 4). Before any guest code, as in
    `_drive`, a turn is refused when wasmtime's trap handlers were replaced (spec 071, Decision
    9): the session then ends as on an error, without Python's shutdown."""
    not_ready = _trap_handlers_ready()
    if not_ready is not None:
        raise RuntimeError(_TRAP_HANDLERS_REPLACED.format(signal=not_ready))
    wt, store, exports = state.wt, state.store, state.exports
    value = exit_code = None
    trapped: str | None = None
    stack = _stack()
    stack.append(call)
    _calls.lost = False
    try:
        if call.cancel is not None and call.cancel.is_set():  # before any guest code
            return None, None, "cancelled", False
        state.called = True
        if state.needs_initialize:
            state.needs_initialize = False
            exports["_initialize"](store)
        p = 0
        if data:
            p = exports["host_alloc"](store, len(data)) & MASK32
            memory = exports["memory"]
            if p and p + len(data) <= memory.data_len(store):
                memory.write(store, data, p)
            else:
                p = 0  # the guest raises MemoryError for its code
        if _on_export is not None:
            _on_export("turn", threading.get_ident())
        value = exports["turn"](store, p, len(data))
    except wt.ExitTrap as e:
        exit_code = e.code
    except wt.Trap as e:
        trapped = _trap_name(e)
        e.__traceback__ = None
    except wt.WasmtimeError as e:
        trapped = _first_line(str(e))
        e.__traceback__ = None
    finally:
        stack.pop()
        lost, _calls.lost = getattr(_calls, "lost", False), False
    if lost:
        raise RuntimeError("wasi_python lost track of a call")
    cause = call.stopped
    if cause is not None:
        value = exit_code = trapped = None
        if isinstance(cause, wt.ExitTrap):
            exit_code = cause.code
        elif isinstance(cause, wt.Trap):
            trapped = _trap_name(cause)
        elif isinstance(cause, wt.WasmtimeError):
            trapped = _first_line(str(cause))
        else:
            raise cause
        cause.__traceback__ = None
    elif call.ended is not None:
        value, exit_code, trapped = None, None, call.ended
    return value, exit_code, trapped, True


def _turn_inside(
    state: _State,
    data: bytes,
    fuel: int | None,
    deadline_s: float | None,
    output_bytes: int | None,
    cancel: threading.Event | None,
    loop: Any,
) -> _TurnDone:
    own = NO_DEADLINE if deadline_s is None else max(1, math.ceil(deadline_s / TICK_S))
    ticks, capped = own, False
    if state.lifetime_s is not None:  # the lifetime caps the turn's deadline (the review's F4)
        left = state.opened + state.lifetime_s - _session_clock()
        cap = max(1, math.ceil(left / TICK_S))
        if cap < own:
            ticks, capped = cap, True
    stop = _Either(cancel, state.closing)
    call, out, err, tool_host = _arm(state, "turn", fuel, ticks, stop, output_bytes, loop)
    try:
        with _epoch_ticker(state.engine, True):
            value, exit_code, trapped, ran = _drive_turn(state, call, data)
        if _after_export is not None:
            _after_export()
        returned = value is not None
        cause: str | None = None
        if returned:
            if not -1 < value <= 511:  # the C side owns the range (Decision 2)
                raise RuntimeError("wasi_python lost track of a session")
            exit_code = value & 0xFF
            if value >= 256:
                cause = "quit"
        elif exit_code is not None:
            cause = "exit"
        elif trapped is not None and ran:
            cause = "lifetime" if trapped == "deadline" and capped else trapped
        fuel_used = None
        if ran and state.metered:
            budget = UNMETERED if fuel is None else fuel
            done = _Driven(exit_code, trapped, True, None)
            fuel_used = _fuel_used(budget, done, call, state.store.get_fuel)
        if ran:
            state.table.walk()  # spec 034, Decision 8, after the fuel is read
        files = state.table.record() if state.c.get("mounts") else None
        record = None if tool_host is None else tool_host.record
        truncated = tuple(s.name for s in (out, err) if s.dropped)
        completed = Completed(
            exit_code,
            bytes(out.data),
            bytes(err.data),
            trapped,
            fuel_used,
            truncated,
            files,
            record,
        )
        return _TurnDone(completed, cause, returned)
    finally:
        if tool_host is not None:
            if loop is not None:
                tool_host.close()  # the caller's loop: the runner's tasks asked to cancel
            elif state.private_loop is not None:
                state.private_loop.cancel_tasks()  # the session's loop lives on (spec 053)


def _session_turn(
    state: _State,
    data: bytes,
    fuel: int | None,
    deadline_s: float | None,
    output_bytes: int | None,
    cancel: threading.Event | None,
    loop: Any,
) -> Completed:
    """A claimed turn, on this thread: run it, decide whether it ended the session, and if the
    session has ended by its return, run the ending here (Decision 7, step 6)."""
    done: _TurnDone | None = None
    error: BaseException | None = None
    try:
        try:
            with _deferred_ctrl_c():
                done = _turn_inside(state, data, fuel, deadline_s, output_bytes, cancel, loop)
        except BaseException as e:
            error = e
        with state.lock:
            if error is not None:
                state.sound = False  # whatever the export returned: no shutdown (F3's error row)
                _mark(state, "error")
            elif done is not None:
                if done.returned:
                    state.sound = True  # the export returned: the interpreter is sound
                elif done.cause is not None:
                    state.sound = False  # a trap, an exit or a stop unwound it
                # else a cancel set before any guest code: the session is untouched
                if done.cause is not None:
                    _mark(state, done.cause)
                elif (
                    state.lifetime_s is not None
                    and _session_clock() >= state.opened + state.lifetime_s
                ):
                    _mark(state, "lifetime")
            state.busy = False
            state.turn_thread = None
            state.last_end = _session_clock()
            me = threading.get_ident()
            ended = state.ended is not None and _claim_ending(state, me)  # the turn's thread (F3)
        if ended:
            raised = _end_with_ctrl_c(state, me)
            if error is None and raised is not None:
                error = raised
    finally:
        _wake_reaper()
    if error is not None:
        raise error
    assert done is not None
    return done.completed


def _end_with_ctrl_c(state: _State, owner: int | None = None) -> BaseException | None:
    """The ending on this thread, with Ctrl-C deferred as for a turn; what it raised, if any."""
    try:
        with _deferred_ctrl_c():
            raised = _end_session(state, owner)
    except BaseException as e:
        return e
    return raised


def _open_session(
    wt: Any,
    c: dict[str, Any],
    host: Host | None,
    snapshot: bool,
    cache_dir: Any,
    artifacts: Artifacts | None,
    state: _State,
) -> None:
    """Decision 6: find the set and refuse one without the session exports, walk and judge the
    folders, make the store and instantiate it; no guest code runs."""
    found = artifacts if artifacts is not None else find_artifacts()
    from . import ArtifactsMissing

    if c.get("tools") is not None and not _has_guest_package(found.manifest):
        raise ArtifactsMissing(
            f"{found.manifest} has no `recipe … {GUEST_PACKAGE}` line: this artifact set "
            "predates the tool protocol (spec 031), so its guest cannot `from host import "
            "tools`; tools= needs a set built with the guest package"
        )
    cache = _cache_dir(cache_dir)
    binary = found.snapshot if snapshot else found.plain
    metered = c["fuel"] is not None
    engine = _engine(metered)
    module = _module(engine, metered, binary, cache)
    names = {e.name for e in module.exports}
    missing = [n for n in SESSION_EXPORTS if n not in names]
    if missing:
        raise ArtifactsMissing(
            f"{binary} does not export {' or '.join(missing)}: this artifact set predates "
            "sessions (spec 055); a Session needs a set built with them"
        )
    root = c["root"]
    entries, serving = c.get("import_path", ()), c.get("import_serving", ())
    walked_root, walked = _walk_grants(root, c["grants"], found, cache, entries, serving)
    state.walked = [w for w in [walked_root, *(w for _, _, w in walked)] if w is not None]
    preopens: list[_Preopen] = []
    try:
        root_path, state.private = _preopens(found, root, walked_root, walked, preopens)
        state.walked += [p.walked for p in preopens]
        mounts: tuple[Mount, ...] = c.get("mounts", ())
        tmp, tmp_fd = _home_folder(root_path, preopens, tuple(m.guest for m in mounts))
        home_guest = None
        if tmp is not None:
            name = f".home-{secrets.token_hex(16)}"
            try:
                if tmp_fd is not None:
                    os.mkdir(name, dir_fd=tmp_fd)
                else:
                    (tmp / name).mkdir()
            except BaseException:
                _close(tmp_fd)
                raise
            state.home = (name, tmp, tmp_fd)
            home_guest = f"/tmp/{name}"
        store = state.store = wt.Store(engine)
        if metered:
            store.set_fuel(UNMETERED)  # instantiation's own memory fill (spec 008)
        if c["memory_bytes"] is not None:
            store.set_limits(memory_size=c["memory_bytes"])
        wasi = wt.WasiConfig()
        state.origin_ns = time.perf_counter_ns()  # the session's clock base (the review's F6)
        wasi.argv = [ARGV0, *entries]
        fresh = {} if home_guest is None else {"HOME": home_guest}
        wasi.env = sorted({**BASE_ENV, **fresh, **(c["env"] or {})}.items())
        state.keys = _send_outputs(wasi, _Stream("stdout", 0), _Stream("stderr", 0))
        scratch = state.scratch = _Private("wasi-python-")
        mounted: list[_Preopen] = []
        if mounts:
            placeholder = scratch.path / "mount"
            placeholder.mkdir()
            for i, mount in enumerate(mounts):
                w = _walk("", str(placeholder), judge=False)
                state.walked.append(w)
                mounted.append(_Preopen(f"mounts[{i}] at {mount.guest}", w, mount.guest, False))
        every = [*preopens, *mounted]
        for p in every:
            wasi.preopen_dir(p.walked.path, p.guest, p.writable)
        stdin_path = scratch.path / "stdin"
        stdin_path.write_bytes(b"")
        wasi.stdin_file = str(stdin_path)
        store.set_wasi(wasi)
        linker = _linker(wt, engine)
        from .mounts import _Files

        staging = STAGING_CEILING if c["memory_bytes"] is None else c["memory_bytes"]
        others = [p.guest for p in preopens]
        if mounts:
            guest_linker = _mount_linker(wt, engine)
            first = 3 + len(preopens)
            numbers = [(mount, first + i) for i, mount in enumerate(mounts)]
        else:
            guest_linker = _guard_linker(wt, engine)
            numbers = []
        table = state.table = _Files(
            numbers,
            others,
            c["file_calls"],
            staging,
            metered,
            engine,
            open_files=c["open_files"],  # spec 068, per session: the store keeps them (Decision 5)
        )
        table.session = True
        store.set_epoch_deadline(NO_DEADLINE)  # no guest code runs before the first turn
        _watch(store)  # every turn can be stopped by a close (Decision 6)
        not_ready = _trap_handlers_ready()  # spec 071, Decision 9: before any wasm runs
        if not_ready is not None:
            raise RuntimeError(_TRAP_HANDLERS_REPLACED.format(signal=not_ready))
        check = _check_module(wt, engine, metered)
        _check_preopens(wt, linker, store, check, every)  # spec 017, Decision 5; once
        instance = guest_linker.instantiate(store, module)
        table.bind(wt, store, linker, instance)
        state.exports = instance.exports(store)
        state.needs_initialize = "_initialize" in state.exports
        state.wt, state.engine, state.metered = wt, engine, metered
        if c.get("tools") is not None:
            from .tools import _Bounded

            state.bounded = _Bounded(
                tick_s=TICK_S,
                ticks=lambda: _epoch_ticker.count(),
                ctrl_c=_ctrl_c_now,
                count=_count_tool_threads,
            )
    except BaseException:
        _release_session(state)
        raise


class Session:
    """One instance of the runtime kept across several calls, each a turn: variables, functions
    and imports made in one turn are there in the next.

    A session is opened by the constructor and ended by `close()`, by leaving a `with` block, by
    its idle bound or lifetime, by a turn that traps, calls `os._exit` or calls `exit()` or
    `quit()`, or by a turn the runner stops. A turn's exception, its `sys.exit()` and a full heap
    do not end it. When a session closed or expired at rest ends, it runs Python's shutdown, as a
    Jupyter kernel does: `atexit` handlers, then the interpreter's finalization, which flushes the
    files it closes, inside `shutdown_s` seconds and, in a metered session, its `fuel`; past
    them it is simply stopped. A session stopped mid-turn runs no shutdown. Either way its store
    and folders are released once its ending finishes.

    A session is one trust domain: a turn's output and exit status are only as trustworthy as
    the least trusted turn before it. Write and close files within a turn.

    Use it as a context manager::

        with Session(grants=[Grant("data", "/data")]) as session:
            session.run("import pandas as pd; df = pd.read_csv('/data/sales.csv')")
            done = session.run("df.groupby('region').total.sum()")
    """

    def __init__(
        self,
        *,
        root: str | os.PathLike[str] | bool | None = False,
        grants: Iterable[Grant] = (),
        mounts: Iterable[Mount] = (),
        import_path: Iterable[str] = (),
        env: Mapping[str, str] | None = None,
        host: Callable[[bytes], bytes | bytearray | memoryview] | None = None,
        snapshot: bool = True,
        fuel: int | None = None,
        deadline_s: float | None = _UNSET,
        memory_bytes: int | None = _UNSET,
        output_bytes: int | None = _UNSET,
        cache_dir: str | os.PathLike[str] | None | bool = None,
        artifacts: Artifacts | None = None,
        max_file_calls: int | None = _UNSET,
        tools: Iterable[Tool | Callable[..., Any]] | None = None,
        gate: Callable[[ToolCall], Any] | None = None,
        max_tool_calls: int | None = _UNSET,
        max_tool_request_bytes: int | None = _UNSET,
        max_open_files: int | None = _UNSET,
        idle_s: float | None = _UNSET,
        lifetime_s: float | None = _UNSET,
        shutdown_s: float = _UNSET,
    ) -> None:
        """Open a session: check every argument, find the artifact set, make the folders and
        the store, and instantiate the guest. No guest code runs until the first turn.

        Args:
            root: The host folder the guest sees as /, writable, made if missing. `False` or
                `None` (the default) gives no / and nothing writable; `True` gives a fresh
                private folder, removed when the session ends.
            grants: Host folders the guest sees at their guest paths, each a `Grant`, read-only
                unless it says `writable=True`. The stdlib zip is always granted, read-only, at
                /usr/local/lib.
            mounts: Providers whose files the guest sees at their guest paths, each a `Mount`,
                served from your code, read-only unless it says `writable=True`.
            import_path: Guest paths put on the guest's `sys.path` after the stdlib zip, in order:
                each a folder or a zip file inside a read-only grant. The root, a writable grant or
                a mount may not serve one, no writable grant or mount may lie under one, and no
                writable grant or root may lie inside the grant serving one.
            env: Environment variables laid over the guest's own: TMPDIR=/tmp, PYTHONTZPATH=
                empty (zoneinfo reads the zip's tzdata), and a HOME made fresh for the session
                where /tmp is writable.
            host: The door's host function: called with each request's bytes, it returns the
                response's. It must answer synchronously: an async one raises `TypeError`.
                Excludes `tools`.
            snapshot: `True` runs the snapshot binary, with the stdlib's bootstrap imported
                (no package); `False` the plain reactor.
            fuel: Each turn's cap on the guest's executed instructions, unless the turn passes
                its own; past it the turn ends "out of fuel", which ends the session. A session
                given a number is metered; `None` (the default) is unmetered, and its turns
                report no fuel.
            deadline_s: Each turn's wall-clock seconds, unless the turn passes its own; past
                them the turn ends "deadline". Default: `defaults().deadline_s`, 60. `None`
                means no limit but the lifetime's.
            memory_bytes: The most linear memory the guest may hold, in bytes, for the whole
                session. Default: `defaults().memory_bytes`, 1 GiB. `None` means no limit.
            output_bytes: The most bytes kept per stream in each turn, unless the turn passes
                its own; the rest are dropped and the stream named in `truncated`. Default:
                `defaults().output_bytes`, 16 MiB. `None` means no limit.
            cache_dir: Where compiled modules are kept as .cwasm files, a folder only you can
                write. `None` or `True` uses `$WASI_PYTHON_CACHE`, else the user's cache folder;
                `False` keeps them in this process only, never on disk.
            artifacts: The artifact set to run; `None` finds it with `artifacts()`.
            max_file_calls: The most provider calls each turn with mounts makes; then it ends
                "out of file calls". Default: `defaults().file_calls`, 10,000. `None` means no
                limit.
            tools: Host functions offered to the guest through the tool protocol (`from host
                import tools`), each a `wasi_python.tools.Tool` or a plain function, which goes
                through `tool()`. A tool may be async: under `run` it is awaited on one loop of
                the session's own for all its turns, under `run_async` on the event loop that
                awaits it. Fixed for the session. Excludes `host`.
            gate: Called with a `ToolCall` before each tool runs. It allows by returning `None`
                or `True`, and refuses by returning `False` or raising `ToolDenied`. It may be
                async, as a tool may. Needs `tools`.
            max_tool_calls: The most tool-protocol frames each turn answers; the guest gets
                `ToolBudgetExceeded` for the rest. Default: `defaults().tool_calls`, 1,000.
                `None` means no limit. Needs `tools`.
            max_tool_request_bytes: The most bytes of tool-protocol requests each turn reads,
                counted from each frame's length before it is read; a frame that would pass it
                is refused unread. Default: `defaults().tool_request_bytes`, 16 MiB. `None`
                means no limit. Needs `tools`.
            max_open_files: The most files and folders the guest holds open at once, in grants,
                the root and mounts alike, counted across the session's turns and its ending,
                since its store keeps them; past it an open answers `EMFILE` and the guest runs
                on. 0 refuses every open, the stdlib's included. It protects your process only
                within the process's own soft descriptor limit. Default:
                `defaults().open_files`, 1,024. `None` means no limit.
            idle_s: The longest the session may rest between turns; then it ends "idle".
                Default: `defaults().session_idle_s`, 900. `None` means no bound.
            lifetime_s: How long after the opening the session's turns may run: no turn starts
                at or after it, and each turn's deadline is capped at what is left; then it ends
                "lifetime". Default: `defaults().session_lifetime_s`, 3,600. `None` means no
                bound.
            shutdown_s: The seconds the session's ending has to run Python's shutdown, capped
                so it ends by the opening plus the lifetime plus this; past it the session is
                stopped. Default: `defaults().session_shutdown_s`, 5. 0 skips the shutdown;
                `None` is refused.

        Raises:
            TypeError: An argument has the wrong type; raised before any work.
            ValueError: An argument is out of range; raised before any work.
            ArtifactsMissing: There is no usable artifact set, or it predates sessions.
            ImportError: wasmtime-py cannot load; its own error is chained as the cause.
            OSError: A host filesystem call failed while the root, the private folders, the
                zip's copy or the cache was prepared.
            RuntimeError: This process was forked after it ran a guest; a folder or the zip's
                copy changed between the runner's check and its use; or, on Linux, wasmtime's
                trap handlers were replaced after the first run (as `run`).
            wasmtime.WasmtimeError: Today, for a folder removed between the runner's check and
                wasmtime's own open. The type is wasmtime-py's and is not promised.
        """
        _refuse_forked()
        wt = _wasmtime()
        limits = _current_defaults()
        c = _checked(
            [],
            env,
            None,
            fuel,
            deadline_s,
            memory_bytes,
            output_bytes,
            None,
            host=host,
            tools=tools,
            gate=gate,
            max_tool_calls=max_tool_calls,
            max_tool_request_bytes=max_tool_request_bytes,
            root=root,
            grants=grants,
            mounts=mounts,
            max_file_calls=max_file_calls,
            import_path=import_path,
            max_open_files=max_open_files,
            limits=limits,
        )
        state = _State()
        state.idle_s = _seconds_limit(
            "idle_s", limits.session_idle_s if idle_s is _UNSET else idle_s
        )
        state.lifetime_s = _seconds_limit(
            "lifetime_s", limits.session_lifetime_s if lifetime_s is _UNSET else lifetime_s
        )
        state.shutdown_s = _shutdown_limit(
            "shutdown_s", limits.session_shutdown_s if shutdown_s is _UNSET else shutdown_s
        )
        if not isinstance(snapshot, bool):
            raise TypeError(f"snapshot must be a bool; got {type(snapshot).__name__}")
        state.c, state.host = c, host
        state.context = contextvars.copy_context()
        self._state = state
        _open_session(wt, c, host, snapshot, cache_dir, artifacts, state)
        state.opened = state.last_end = _session_clock()
        with _lock:
            _counts["sessions_open"] += 1
            state.counted = True
        with _sessions_lock:
            _sessions.add(state)
        self._finalizer = weakref.finalize(self, _collected, state)
        self._finalizer.atexit = False  # the exit hook ends sessions (Decision 13)
        _ensure_reaper()
        _wake_reaper()

    def __enter__(self) -> Session:
        """Enter a `with` block; the session is closed when the block is left.

        Returns:
            This session.
        """
        return self

    def __exit__(self, *exc: object) -> None:
        """Close the session as the `with` block is left, however it is left.

        Args:
            exc: The exception leaving the block, if any; it is never suppressed.
        """
        self.close()

    @property
    def ended(self) -> str | None:
        """`None` while the session can run turns; once it cannot, why: "closed", "idle",
        "lifetime", "quit" (a turn called `exit()` or `quit()`), "exit" (a turn called
        `os._exit`), "error" (a turn raised in your process), or the stopped turn's `trapped`.
        Set once, and never changed."""
        return self._state.ended

    @property
    def shutdown_outcome(self) -> str | None:
        """`None` until the session's ending has finished; then "finished" (Python's shutdown
        ran to its end), "stopped" (its budget ran out, or it trapped), or "skipped" (no
        shutdown ran: the session was stopped mid-turn, no turn ever ran, `shutdown_s` was 0,
        or, on Linux, wasmtime's trap handlers were replaced after the first run). `close()`
        waits for the ending."""
        return self._state.outcome

    def _turn_args(
        self, code: Any, fuel: Any, deadline_s: Any, output_bytes: Any, cancel: Any
    ) -> tuple[bytes, int | None, float | None, int | None]:
        text = _text("code", code)
        data = str.encode(text, "utf-8")
        if len(data) > MAX_TURN_BYTES:
            raise ValueError(f"code must be at most {MAX_TURN_BYTES} bytes as UTF-8")
        c = self._state.c
        if fuel is _UNSET:
            fuel = c["fuel"]
        elif fuel is not None and c["fuel"] is None:
            _integer_limit("fuel", fuel)
            raise ValueError(
                "fuel= needs a metered session: open the Session with fuel= to cap its turns"
            )
        else:
            fuel = _integer_limit("fuel", fuel)
        deadline = c["deadline_s"] if deadline_s is _UNSET else _deadline_limit(deadline_s)
        output = (
            c["output_bytes"]
            if output_bytes is _UNSET
            else _integer_limit("output_bytes", output_bytes)
        )
        if cancel is not None and not isinstance(cancel, threading.Event):
            raise TypeError(
                f"cancel must be a threading.Event, or None; got {type(cancel).__name__}"
            )
        return data, fuel, deadline, output

    def _claim(self, *, here: bool) -> None:
        """Claim the session for one turn, or raise SessionEnded (a bound that has passed ends it
        first: its ending runs here, or on a closer thread) or RuntimeError (a turn running)."""
        state = self._state
        now = _session_clock()
        me = threading.get_ident()
        with state.lock:
            expired = False
            if state.ended is None:
                due = _due(state)
                if due is not None and now >= due[0] and not state.busy:
                    expired = _mark(state, due[1]) and _claim_ending(state, me if here else _CLOSER)
            ended = state.ended
            if ended is None:
                if state.busy:
                    raise RuntimeError("a turn is already running in this session")
                state.busy = True
                state.turn_thread = threading.get_ident()
                return
        if expired:
            if here:
                raised = _end_with_ctrl_c(state, me)
                if raised is not None:
                    raise raised
            else:
                _start_closer(state)
        raise SessionEnded(ended)

    def _release_claim(self) -> None:
        state = self._state
        with state.lock:
            state.busy = False
            state.turn_thread = None
        _wake_reaper()

    def run(
        self,
        code: str,
        *,
        fuel: int | None = _UNSET,
        deadline_s: float | None = _UNSET,
        output_bytes: int | None = _UNSET,
        cancel: threading.Event | None = None,
    ) -> Completed:
        """Run one turn of code in the session and return how it ended.

        The code runs in `__main__`, as the interactive interpreter runs it: a final expression's
        value is printed, `sys.exit()` is reported as the turn's exit status and the session
        goes on, and `exit()` or `quit()` make the turn return their status and then end the
        session. Nothing a guest does makes `run` raise.

        Args:
            code: The turn's source, a str.
            fuel: This turn's cap on executed instructions in a metered session; `None` sets no
                cap. Default: the session's.
            deadline_s: This turn's wall-clock seconds; `None` means no limit but the
                lifetime's. Default: the session's.
            output_bytes: The most bytes kept per stream in this turn. Default: the session's.
            cancel: A `threading.Event`. Once it is set and the guest runs, the turn stops
                within 5 ticks of 10 ms while it computes and ends "cancelled", which ends the
                session; set before the guest runs, the turn runs nothing and the session goes
                on.

        Returns:
            How the turn ended.

        Raises:
            TypeError: An argument has the wrong type; the session stays open.
            ValueError: An argument is out of range; the session stays open.
            SessionEnded: The session has ended, or its idle bound or lifetime has passed;
                in that case the session's ending runs here first, so `run` may block for up
                to `shutdown_s` (plus any call of your own code it makes) before it raises.
            RuntimeError: A turn is already running in this session; this process was forked
                after it ran a guest; the runner lost track of the turn; or, on Linux,
                wasmtime's trap handlers were replaced after the first run (as `run`; the turn
                runs no guest code and the session ends, without Python's shutdown).
            KeyboardInterrupt: Ctrl-C.
            BaseException: One that is not an `Exception`, raised by your own host, provider,
                tool or gate, propagates.
        """
        _refuse_forked()
        data, fuel, deadline, output = self._turn_args(code, fuel, deadline_s, output_bytes, cancel)
        self._claim(here=True)
        return _session_turn(self._state, data, fuel, deadline, output, cancel, None)

    async def run_async(
        self,
        code: str,
        *,
        fuel: int | None = _UNSET,
        deadline_s: float | None = _UNSET,
        output_bytes: int | None = _UNSET,
        executor: concurrent.futures.Executor | None = None,
    ) -> Completed:
        """`run` from async code, on a worker thread, so the event loop is never blocked.

        The turn is claimed before it is queued, so a second turn at once raises
        `RuntimeError`. If the awaiting task is cancelled while the turn runs, the turn is
        stopped, which ends the session, before `asyncio.CancelledError` is raised; a turn still
        queued never starts, and the session is untouched.

        Args:
            code: The turn's source, a str.
            fuel: This turn's cap on executed instructions in a metered session; `None` sets no
                cap. Default: the session's.
            deadline_s: This turn's wall-clock seconds; `None` means no limit but the
                lifetime's. Default: the session's.
            output_bytes: The most bytes kept per stream in this turn. Default: the session's.
            executor: Where the turn runs: a `concurrent.futures.Executor` that runs callables
                on threads of this process. `None` uses the runner's own pool.

        Returns:
            How the turn ended.

        Raises:
            TypeError: An argument has the wrong type; the session stays open.
            ValueError: An argument is out of range; the session stays open.
            SessionEnded: The session has ended, or its idle bound or lifetime has passed.
            RuntimeError: A turn is already running in this session; this process was forked
                after it ran a guest; the interpreter is shutting down; the runner lost track
                of the turn; or, on Linux, wasmtime's trap handlers were replaced (as `run`).
            asyncio.CancelledError: The awaiting task was cancelled.
            BaseException: One that is not an `Exception`, raised by your own host, provider,
                tool or gate, propagates.
        """
        import asyncio
        import contextvars

        _refuse_forked()
        data, fuel, deadline, output = self._turn_args(code, fuel, deadline_s, output_bytes, None)
        _check_executor(executor)
        loop = asyncio.get_running_loop()
        _register_exit_hook()
        self._claim(here=False)
        event = threading.Event()
        state = self._state
        try:
            with _live_lock:
                if _hook["exiting"]:
                    raise RuntimeError("cannot schedule new futures after interpreter shutdown")
                _live.add(event)
            work = contextvars.copy_context().run
            args = (_session_turn, state, data, fuel, deadline, output, event, loop)
            future = _submit(executor, work, *args)
        except BaseException:
            with _live_lock:
                _live.discard(event)
            self._release_claim()
            raise
        try:
            try:
                return await asyncio.wrap_future(future)
            except asyncio.CancelledError:
                if future.cancel():  # still queued: it never starts, the session is untouched
                    self._release_claim()
                    raise
                event.set()
                while not future.done():
                    try:
                        await asyncio.wrap_future(future)
                    except BaseException:
                        pass
                raise
        finally:
            with _live_lock:
                _live.discard(event)

    def close(self) -> None:
        """End the session, run its ending, and return once its store is closed.

        A turn running on another thread is stopped first, and `close()` waits for it, and for
        the ending, which runs Python's shutdown when the session was at rest (at most its
        `shutdown_s` of guest code, plus any call of your own code it makes). It blocks, so
        from a coroutine it blocks the event loop. Called from inside the session's own turn or
        ending (a host function or a provider), it marks the session and returns at once.
        Calling it again does nothing.

        Raises:
            KeyboardInterrupt: Ctrl-C during the ending, raised once the session is closed.
            BaseException: One that is not an `Exception`, raised by your own host, provider,
                tool or gate during the ending, raised once the session is closed.
        """
        state = self._state
        if _fork["forked"]:  # the store and folders are the parent's: touch nothing (lock-free)
            if state.ended is None:
                state.ended = "closed"
            if state.outcome is None:
                state.outcome = "skipped"
            return
        me = threading.get_ident()
        with state.lock:
            _mark(state, "closed")
            if state.turn_thread == me or state.ending_thread == me:
                return  # inside the session's own turn or ending: it ends as that returns
            here = not state.busy and _claim_ending(state, me)
        if here:
            self._finalizer.detach()
            raised = _end_with_ctrl_c(state, me)
            if raised is not None:
                raise raised
        state.done.wait()
