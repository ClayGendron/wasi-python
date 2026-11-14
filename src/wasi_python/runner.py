"""The runner: one program, one call.

    from wasi_python import run

    done = run(["-c", "import pandas; print(pandas.__version__)"])
    done.exit_code, done.stdout

It does what any embedder does: preopen a directory at `/`, bind the one custom import
(`host::call`), and call the reactor's exports. wasmtime-py (a dependency of the package) is
imported only here, when a call is made, so `import wasi_python` and `artifacts()` still work
where it cannot load.

It is safe by default: a call that names no root has no `/` and nothing writable
(`root=True` makes a fresh private one, removed afterwards); a call that names no
limit still has one for memory, time and output (`DEFAULTS`); and nothing a guest frame or a
host function does makes `run` raise.
"""

from __future__ import annotations

import contextvars
import os
import threading
import weakref
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any, Literal, Protocol, cast

from . import _call, _engines, _entry, _limits, _outputs, _platform, _private_dirs, _sessions
from ._artifacts import Artifacts, ArtifactsMissing
from ._call import Completed as Completed  # re-exported: the public API names them here
from ._call import _CheckedCall
from ._limits import _UNSET
from ._outputs import OutputChunk as OutputChunk  # re-exported: the public API names them here
from ._outputs import OutputFeed as OutputFeed
from ._places import Grant as Grant
from ._process import process
from ._sessions import _CLOSER, MAX_TURN_BYTES, _Event, _Phase, _State
from ._sessions import SessionEnded as SessionEnded
from ._snapshot import Snapshot
from .mounts import Mount

if TYPE_CHECKING:
    import asyncio
    import concurrent.futures

    from .tools import Tool, ToolCall


class _ExitFlag(Protocol):
    """A finalizer's exit flag, which the stubs give no setter."""

    atexit: bool


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

    # Checked by run's rules; async_workers sizes run_async's pool.
    memory_bytes: int | None
    deadline_s: float | None
    output_bytes: int | None
    async_workers: int = field(default_factory=_limits._default_workers)
    file_calls: int | None = 10_000
    tool_calls: int | None = 1000
    tool_request_bytes: int | None = 16 << 20  # the byte budget of a call's frames
    open_files: int | None = 1024  # the cap on files open at once
    session_idle_s: float | None = 900.0  # 15 minutes, the owner's number
    session_lifetime_s: float | None = 3600.0
    session_shutdown_s: float = 5.0  # jupyter_client's shutdown_wait_time

    def __post_init__(self) -> None:
        _limits._check_limits(None, self.deadline_s, self.memory_bytes, self.output_bytes)
        _limits._check_workers(self.async_workers)
        _limits._integer_limit("file_calls", self.file_calls)
        _limits._integer_limit("tool_calls", self.tool_calls)
        _limits._integer_limit("tool_request_bytes", self.tool_request_bytes)
        _limits._integer_limit("open_files", self.open_files)
        _limits._seconds_limit("session_idle_s", self.session_idle_s)
        _limits._seconds_limit("session_lifetime_s", self.session_lifetime_s)
        _limits._shutdown_limit("session_shutdown_s", self.session_shutdown_s)


DEFAULTS = Defaults(memory_bytes=1 << 30, deadline_s=60.0, output_bytes=16 << 20)


def _current_defaults() -> Defaults:
    """The defaults a call reads, once, when it is made. The binding stays
    this module's `DEFAULTS`, which `wasi_python.set_defaults` replaces under its lock."""
    return DEFAULTS


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
    snapshot: bool | Snapshot = True,
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
    on_output: Callable[[OutputChunk], object] | None = None,
    output_keep: Literal["head", "tail"] = "head",
    results: bool = False,
    figures: bool = False,
) -> Completed:
    """Run one program in a fresh instance of the runtime and return how it ended.

    The guest runs on a thread of the runner's own, with an 8 MiB wasm stack; your `host`,
    providers and tools' contexts are served on the calling thread, which waits. The guest sees
    no host folder but the read-only stdlib, and what `root`, `grants` and `mounts` give it.
    Every argument is checked before any work. A call that names no limit has the ones
    `defaults()` returns, read once, when the call is made. Nothing a guest does, and no
    `Exception` a provider, a tool or a gate raises, makes `run` raise: a provider's `OSError`
    may be its answer (the documentation's *Serve files from your own code*, under *Raise an
    OSError instead*), and the rest are recorded in the result. A new failure is raised as one
    of the types below, or a subclass of one; messages may change.

    Args:
        argv: The guest's arguments after the program's name, as for `python`: `["-c", code]`,
            `["script.py"]` or `["-m", "module"]`.
        root: The host folder the guest sees as /, writable, made if missing. `False` or
            `None` (the default) gives no / and nothing writable; `True` gives a fresh private
            folder, removed after the call.
        grants: Host folders the guest sees at their guest paths, each a `Grant`, read-only unless
            it says `writable=True`. The stdlib zip is always granted, read-only, at /usr/local/lib.
        mounts: Providers whose files the guest sees at their guest paths, each a `Mount`,
            served from your code, read-only unless it says `writable=True`.
        import_path: Guest paths put on the guest's `sys.path` after the stdlib zip, in order:
            each a folder or a zip file inside a read-only grant. The root, a writable grant or
            a mount may not serve one, no writable grant or mount may lie under one, and no
            writable grant or root may lie inside the grant serving one.
        env: Environment variables laid over the guest's own: TMPDIR=/tmp, PYTHONTZPATH=
            empty (zoneinfo reads the zip's tzdata), and a HOME made fresh for the call where
            /tmp is writable, else an empty one the guest cannot write. A key that begins with
            `_PYTHON_`, which CPython reads past isolated mode (`_PYTHON_SYSCONFIGDATA_PATH`
            loads code), raises `ValueError`.
        stdin: The guest's standard input, whole; `None` is empty.
        host: The door's host function: called with each request's bytes, on the thread that
            made the call, it returns the response's. It must answer synchronously: an async one
            raises `TypeError`. Excludes `tools`.
        snapshot: `True` runs the snapshot binary, with the stdlib's bootstrap imported (no
            package); `False` the plain reactor; a `Snapshot` starts the call from its image.
        fuel: A cap on the guest's executed instructions; past it the call ends "out of
            fuel". `None` (the default) sets no cap.
        deadline_s: Wall-clock seconds; past them the call ends "deadline". Default:
            `defaults().deadline_s`, 60. `None` means no limit.
        memory_bytes: The most linear memory the guest may hold, in bytes. Default:
            `defaults().memory_bytes`, 1 GiB. `None` means no limit.
        output_bytes: The most bytes kept per stream; the rest are dropped and the stream
            named in `truncated`. Default: `defaults().output_bytes`, 16 MiB. `None` means no
            limit.
        cache_dir: Where compiled modules are kept as .cwasm files, a folder only you and the
            runner write: never one a guest is granted, in this or another call. `None` or
            `True` uses `$WASI_PYTHON_CACHE`, else the user's cache folder; `False` keeps them
            in this process only, never on disk. A relative folder is made absolute when the
            call is made; an empty string is refused.
        artifacts: The artifact set to run; `None` finds it with `artifacts()` and checks it
            against its SHA256SUMS first. A set you pass is used as you give it.
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
        on_output: Called with each `OutputChunk` of the guest's stdout and stderr while it
            runs: under `run`, on the thread that made the call, in turn with your `host` and
            providers, which wait while it runs; under `run_async`, on the event loop's thread.
            Keep it short. At most `output_bytes` of each stream are delivered, every chunk
            before the call returns. An `Exception` from it is warned as a `RuntimeWarning` and
            ends delivery for the call, which goes on; any other `BaseException` stops the call
            and is raised. It must be synchronous: an async one raises `TypeError`. An
            `OutputFeed` iterates the chunks under `run_async`, beside the call's task; `run`
            refuses one, and a feed serves one call.
        output_keep: What a stream past `output_bytes` keeps: "head" (the default) its first
            bytes, "tail" its last, after a first line `[N bytes cut]`, where N counts the bytes
            past `output_bytes` and the line takes the place of the tail's first bytes. Anything
            else raises `ValueError`.
        results: `True` returns a `-c` program's last expression as `Completed.value`, not
            printed, and what it passes to `display()` as `Completed.displays`; they share one
            more `output_bytes`. Excludes `host`.
        figures: `True` adds each matplotlib figure the program shows or leaves open, as a PNG
            display. Needs `results`.

    Returns:
        How the program ended.

    Raises:
        TypeError: An argument has the wrong type; raised before any work.
        ValueError: An argument is out of range (`SnapshotMismatch` too); raised before any work.
        ArtifactsMissing: There is no usable artifact set.
        ImportError: wasmtime-py cannot load; its own error is chained as the cause.
        OSError: A host filesystem call failed while the root, the private folders, the zip's
            copy or the cache was prepared (its subclasses, such as FileExistsError, included).
        RuntimeError: This process was forked after it ran a guest; a folder or the zip's
            copy changed between the runner's check and its use; on Linux, a handler installed
            or removed after the first run (faulthandler, `signal.signal`, a native crash
            reporter) replaced wasmtime's trap handlers, so a guest trap would end the process;
            the guest's thread could not start, or has less stack than its 8 MiB wasm stack
            needs, or its stack cannot be read on this platform; this is CPython 3.14.0 on a
            C library other than glibc; or wasmtime-py cannot set its async stack size; raised
            before the guest runs.
        wasmtime.WasmtimeError: Today, for a folder removed between the runner's check and
            wasmtime's own open. The type is wasmtime-py's and is not promised.
        KeyboardInterrupt: Ctrl-C.
        BaseException: One that is not an `Exception`, raised by your own host, provider, tool
            or gate, propagates.
    """
    # Every argument is checked before any work; the exceptions are the ones the docstring names.
    _platform._refuse_forked()
    wt = _engines._wasmtime()
    checked = _entry._checked(
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
        limits=_current_defaults(),
        snapshot=snapshot,
        on_output=on_output,
        output_keep=output_keep,
        results=results,
        figures=figures,
    )
    cache = _engines._cache_given(cache_dir)
    return _run_checked_flushed(wt, checked, host, cache, artifacts, None)


def _run_checked_flushed(
    wt: Any,
    checked: _CheckedCall,
    host: Callable[[bytes], bytes | bytearray | memoryview] | None,
    cache: _engines._Cache,
    artifacts: Artifacts | None,
    loop: asyncio.AbstractEventLoop | None,
) -> Completed:
    """`_run_checked`, then the warnings its removals queued, outside every lock."""
    try:
        return _call._run_checked(wt, checked, host, cache, artifacts, loop)
    finally:
        _private_dirs._flush_warnings()


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
    snapshot: bool | Snapshot = True,
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
    on_output: Callable[[OutputChunk], object] | None = None,
    output_keep: Literal["head", "tail"] = "head",
    results: bool = False,
    figures: bool = False,
) -> Completed:
    """`run` from async code, on a worker thread, so the event loop is never blocked.

    The arguments are `run`'s, without `cancel`, plus `executor`; they are checked, and the
    defaults read, before anything is queued. The worker serves your `host` and providers while
    the guest runs on a thread of the runner's own, so the worker's own stack size does not
    matter. If the awaiting task is cancelled, the guest is
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
            /tmp is writable, else an empty one the guest cannot write. A key that begins with
            `_PYTHON_`, which CPython reads past isolated mode (`_PYTHON_SYSCONFIGDATA_PATH`
            loads code), raises `ValueError`.
        stdin: The guest's standard input, whole; `None` is empty.
        host: The door's host function: called with each request's bytes, on the thread that
            made the call, it returns the response's. It must answer synchronously: an async one
            raises `TypeError`. Excludes `tools`.
        snapshot: `True` runs the snapshot binary, with the stdlib's bootstrap imported (no
            package); `False` the plain reactor; a `Snapshot` starts the call from its image.
        fuel: A cap on the guest's executed instructions; past it the call ends "out of
            fuel". `None` (the default) sets no cap.
        deadline_s: Wall-clock seconds; past them the call ends "deadline". Default:
            `defaults().deadline_s`, 60. `None` means no limit.
        memory_bytes: The most linear memory the guest may hold, in bytes. Default:
            `defaults().memory_bytes`, 1 GiB. `None` means no limit.
        output_bytes: The most bytes kept per stream; the rest are dropped and the stream
            named in `truncated`. Default: `defaults().output_bytes`, 16 MiB. `None` means no
            limit.
        cache_dir: Where compiled modules are kept as .cwasm files, a folder only you and the
            runner write: never one a guest is granted, in this or another call. `None` or
            `True` uses `$WASI_PYTHON_CACHE`, else the user's cache folder; `False` keeps them
            in this process only, never on disk. A relative folder is made absolute when the
            call is made; an empty string is refused.
        artifacts: The artifact set to run; `None` finds it with `artifacts()` and checks it
            against its SHA256SUMS first. A set you pass is used as you give it.
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
        on_output: Called with each `OutputChunk` of the guest's stdout and stderr while it
            runs: under `run`, on the thread that made the call, in turn with your `host` and
            providers, which wait while it runs; under `run_async`, on the event loop's thread.
            Keep it short. At most `output_bytes` of each stream are delivered, every chunk
            before the call returns. An `Exception` from it is warned as a `RuntimeWarning` and
            ends delivery for the call, which goes on; any other `BaseException` stops the call
            and is raised. It must be synchronous: an async one raises `TypeError`. An
            `OutputFeed` iterates the chunks under `run_async`, beside the call's task; `run`
            refuses one, and a feed serves one call.
        output_keep: What a stream past `output_bytes` keeps: "head" (the default) its first
            bytes, "tail" its last, after a first line `[N bytes cut]`, where N counts the bytes
            past `output_bytes` and the line takes the place of the tail's first bytes. Anything
            else raises `ValueError`.
        results: `True` returns a `-c` program's last expression as `Completed.value`, not
            printed, and what it passes to `display()` as `Completed.displays`; they share one
            more `output_bytes`. Excludes `host`.
        figures: `True` adds each matplotlib figure the program shows or leaves open, as a PNG
            display. Needs `results`.

    Returns:
        How the program ended.

    Raises:
        TypeError: An argument has the wrong type; raised before any work.
        ValueError: An argument is out of range (`SnapshotMismatch` too); raised before any work.
        ArtifactsMissing: There is no usable artifact set.
        ImportError: wasmtime-py cannot load; its own error is chained as the cause.
        OSError: A host filesystem call failed while the root, the private folders, the zip's
            copy or the cache was prepared (its subclasses, such as FileExistsError, included).
        RuntimeError: This process was forked after it ran a guest; the interpreter is shutting
            down; a folder or the zip's copy changed between the runner's check and its use; on
            Linux, a handler installed or removed after the first run replaced wasmtime's trap
            handlers; or the guest's thread is refused (as `run`).
        wasmtime.WasmtimeError: Today, for a folder removed between the runner's check and
            wasmtime's own open. The type is wasmtime-py's and is not promised.
        asyncio.CancelledError: The awaiting task was cancelled; the guest was stopped and its
            worker freed first.
        BaseException: One that is not an `Exception`, raised by your own host, provider, tool
            or gate, propagates.
    """
    with _entry._serving(on_output):  # a feed serves one call
        _platform._refuse_forked()
        event = threading.Event()  # the call's cancel, set when the awaiting task is cancelled
        checked = _entry._checked(
            argv,
            env,
            stdin,
            fuel,
            deadline_s,
            memory_bytes,
            output_bytes,
            event,
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
            limits=_current_defaults(),
            snapshot=snapshot,
            on_output=on_output,
            output_keep=output_keep,
            results=results,
            figures=figures,
            asynchronous=True,
        )
        cache = _engines._cache_given(cache_dir)
        _entry._check_executor(executor)
        wt = _engines._wasmtime()
        return await _entry._awaited(
            checked.on_output,
            event,
            executor,
            _current_defaults,
            lambda late, loop: (
                _run_checked_flushed,
                wt,
                replace(checked, on_output=late),
                host,
                cache,
                artifacts,
                loop,
            ),
        )


def stats() -> dict[str, int]:
    """Counts kept by this process, a diagnostic.

    `tool_threads_running` counts the tool threads alive in this process, abandoned ones
    included. `sessions_open` counts the `Session`s opened and not yet ended. `compiled`,
    `loaded` and `written` count how this process got its compiled modules: compiled from the
    binary, loaded from a .cwasm file, and .cwasm files written; what they count may change with
    the cache. `snapshots_made` counts the snapshots this process made, and `snapshots_restored`
    the calls and sessions it started from one. A later release may add keys.
    """
    # the judge reads it.
    p = process()
    with p.cache_lock:
        counts = dict(p.counts)
    with p.tool_threads_lock:
        counts["tool_threads_running"] = p.tool_threads_running
    return counts


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
        snapshot: bool | Snapshot = True,
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
        results: bool = False,
        figures: bool = False,
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
                where /tmp is writable, else an empty one the guest cannot write. A key that
                begins with `_PYTHON_`, which CPython reads past isolated mode
                (`_PYTHON_SYSCONFIGDATA_PATH` loads code), raises `ValueError`.
            host: The door's host function: called with each request's bytes, it returns the
                response's. It must answer synchronously: an async one raises `TypeError`.
                Excludes `tools`.
            snapshot: `True` runs the snapshot binary, with the stdlib's bootstrap imported
                (no package); `False` the plain reactor; a `Snapshot` opens it from its image.
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
            cache_dir: Where compiled modules are kept as .cwasm files, a folder only you and
                the runner write: never one a guest is granted, in this or another call. `None`
                or `True` uses `$WASI_PYTHON_CACHE`, else the user's cache folder; `False` keeps
                them in this process only, never on disk. A relative folder is made absolute
                when the call is made; an empty string is refused.
            artifacts: The artifact set to run; `None` finds it with `artifacts()` and checks
                it against its SHA256SUMS first. A set you pass is used as you give it.
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
            results: `True` returns each turn's last expression as `Completed.value`, not
                printed, and what it passes to `display()` as `Completed.displays`; they share
                one more `output_bytes`. Fixed for the session. Excludes `host`.
            figures: `True` adds each matplotlib figure a turn shows or leaves open, as a PNG
                display. Needs `results`.

        Raises:
            TypeError: An argument has the wrong type; raised before any work.
            ValueError: An argument is out of range (`SnapshotMismatch` too); raised before
                any work.
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
        _platform._refuse_forked()
        wt = _engines._wasmtime()
        limits = _current_defaults()
        c = _entry._checked(
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
            snapshot=snapshot,
            results=results,
            figures=figures,
        )
        cache = _engines._cache_given(cache_dir)
        state = _State(c, wt)
        state.idle_s = _limits._seconds_limit(
            "idle_s", limits.session_idle_s if idle_s is _UNSET else idle_s
        )
        state.lifetime_s = _limits._seconds_limit(
            "lifetime_s", limits.session_lifetime_s if lifetime_s is _UNSET else lifetime_s
        )
        state.shutdown_s = _limits._shutdown_limit(
            "shutdown_s", limits.session_shutdown_s if shutdown_s is _UNSET else shutdown_s
        )
        state.host = host
        state.context = contextvars.copy_context()
        self._state = state
        try:
            _sessions._open_session(wt, c, host, cache, artifacts, state)
        finally:
            _private_dirs._flush_warnings()  # the sweep's, or a failed opening's
        p = process()
        state.opened = state.last_end = p.observers.clock()
        with p.cache_lock:
            p.counts["sessions_open"] += 1
        with state.lock:
            _sessions._move(state, _Event.OPENED)  # counted from here until its release
        with p.sessions_lock:
            p.sessions.add(state)
        self._finalizer = weakref.finalize(self, _sessions._collected, state)
        # The exit hook ends sessions; `atexit` is a property on a slotted class, so
        # the write works where the checker sees only the slots.
        cast(_ExitFlag, self._finalizer).atexit = False
        _sessions._ensure_reaper()
        _sessions._wake_reaper()

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
        text = _limits._text("code", code)
        data = str.encode(text, "utf-8")
        if len(data) > MAX_TURN_BYTES:
            raise ValueError(f"code must be at most {MAX_TURN_BYTES} bytes as UTF-8")
        c = self._state.checked
        if fuel is _UNSET:
            fuel = c.fuel
        elif fuel is not None and c.fuel is None:
            _limits._integer_limit("fuel", fuel)
            raise ValueError(
                "fuel= needs a metered session: open the Session with fuel= to cap its turns"
            )
        else:
            fuel = _limits._integer_limit("fuel", fuel)
        deadline = c.deadline_s if deadline_s is _UNSET else _limits._deadline_limit(deadline_s)
        output = (
            c.output_bytes
            if output_bytes is _UNSET
            else _limits._integer_limit("output_bytes", output_bytes)
        )
        _limits._check_cancel(cancel)
        return data, fuel, deadline, output

    def _turn_io(
        self, stdin: Any, on_output: Any, output_keep: Any, *, asynchronous: bool
    ) -> _sessions._TurnIO:
        """A turn's stdin, delivery and keep, checked before the claim: a turn's stdin as
        `run`'s, at most `MAX_TURN_BYTES`, and only on a set whose binary takes one."""
        data = _limits._check_inputs((), None, stdin).stdin
        if data is not None and len(data) > MAX_TURN_BYTES:
            raise ValueError(f"stdin must be at most {MAX_TURN_BYTES} bytes")
        keep = _limits._check_output_keep(output_keep)
        callback = _outputs._check_on_output(on_output, asynchronous=asynchronous)
        if data is not None and not self._state.takes_stdin:
            raise ArtifactsMissing(
                "this artifact set's binary does not export turn_input, so a turn cannot be "
                "given stdin; it needs a set built with it"
            )
        return _sessions._TurnIO(data, callback, keep)

    def _claim(self, *, here: bool) -> None:
        """Claim the session for one turn, or raise SessionEnded (a bound that has passed ends it
        first: its ending runs here, or on a closer thread) or RuntimeError (a turn running)."""
        state = self._state
        now = process().observers.clock()
        me = threading.get_ident()
        with state.lock:
            expired = False
            if state.phase is _Phase.OPEN:
                due = _sessions._due(state)
                if due is not None and now >= due[0]:
                    expired = _sessions._mark(state, due[1]) and _sessions._claim_ending(
                        state, me if here else _CLOSER
                    )
            ended = state.ended
            if ended is None:
                if state.phase is _Phase.TURN:
                    raise RuntimeError("a turn is already running in this session")
                _sessions._move(state, _Event.CLAIM, me)
                return
        if expired:
            if here:
                raised = _sessions._end_with_ctrl_c(state, me)
                if raised is not None:
                    raise raised
            else:
                _sessions._start_closer(state)
        raise SessionEnded(ended)

    def _prepare(
        self, data: bytes, fuel: int | None, deadline_s: float | None, output_bytes: int | None
    ) -> tuple[Completed, tuple[bytes, int] | None, Any]:
        """A making's one turn, through the `prepare` export: how it ended; when its code
        returned 0, the image and the count of files left open, read on this thread before the
        claim is released; and the set's digests as the opening checked them."""
        _platform._refuse_forked()
        self._claim(here=True)
        state = self._state
        args = (state, data, fuel, deadline_s, output_bytes, None, None, "prepare")
        done = _sessions._session_turn(*args)
        return done, state.captured, state.set_digests

    def checkpoint(self) -> Snapshot:
        """Keep the session's state as a snapshot, and go on.

        Once a turn has returned, the guest's memory is read whole, between two calls into the
        guest, and kept as a `Snapshot`: every name, import and object the turns made. Pass it
        as `snapshot=` to `Session`, `run` or `run_async`; each starts from a private copy with
        its own grants, mounts, environment, import path, tools, clocks and randomness, and this
        session goes on unchanged. A start reseeds `random`'s, numpy's and the other module
        generators, even after the session's own seed; a generator held in a name draws the
        same in every start. The checkpoint holds every byte the session's memory holds, what
        its turns read from grants, mounts and tools included: start it only where its code may
        read everything the session read. It binds to this session's artifact set.

        Returns:
            The snapshot. Its origin's `kind` is "checkpoint", and its `parent_sha256` is the
            image this session started from, if any.

        Raises:
            RuntimeError: This process was forked after it ran a guest; a turn is running; no
                turn has returned yet; or the runner lost track of the call, which ends the
                session.
            ValueError: The session runs the plain binary (`snapshot=False`).
            ArtifactsMissing: The artifact set predates checkpoints.
            SessionEnded: The session has ended, or its idle bound or lifetime has passed.
            SnapshotFailed: A turn left a file or folder open (reason "open file", with
                `completed` `None`; the session goes on), or the guest trapped (reason
                "trapped"), which ends the session.
            MemoryError: This process had no memory for the image; the session goes on.
        """
        _platform._refuse_forked()
        state = self._state
        if state.checked.binary != "snapshot":
            raise ValueError(
                "a checkpoint needs the snapshot binary: this session runs the plain one "
                "(snapshot=False)"
            )
        if not state.checkpointable:
            raise ArtifactsMissing(
                "this artifact set's snapshot binary does not export checkpoint: it predates "
                "checkpoints; use a set built with them"
            )
        self._claim(here=True)
        refusal = _sessions._checkpoint_refusal(state)
        if refusal is not None:
            self._release_claim()
            raise refusal
        done = _sessions._session_turn(state, b"", None, None, None, None, None, "checkpoint")
        return _sessions._checkpointed(state, done)

    def _release_claim(self) -> None:
        """A claimed turn that never started gives its claim back. When a `close()` came between
        the claim and the release, the session is marked and nobody holds it: its ending goes to
        a closer, and the `close()` waiting for it returns."""
        state = self._state
        with state.lock:
            after = _sessions._move(state, _Event.RELEASE)  # from TURN, or STOPPING after a close()
            start = after is _Phase.MARKED and _sessions._claim_ending(state, _CLOSER)
        if start:
            _sessions._start_closer(state)
        _sessions._wake_reaper()

    def run(
        self,
        code: str,
        *,
        fuel: int | None = _UNSET,
        deadline_s: float | None = _UNSET,
        output_bytes: int | None = _UNSET,
        cancel: threading.Event | None = None,
        stdin: bytes | bytearray | memoryview | None = None,
        on_output: Callable[[OutputChunk], object] | None = None,
        output_keep: Literal["head", "tail"] = "head",
    ) -> Completed:
        """Run one turn of code in the session and return how it ended.

        The code runs in `__main__`, as the interactive interpreter runs it: a final expression's
        value is printed (in a session with `results=True`, returned as `Completed.value`
        instead), `sys.exit()` is reported as the turn's exit status and the session goes on,
        and `exit()` or `quit()` make the turn return their status and then end the session.
        Nothing a guest does makes `run` raise.

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
            stdin: This turn's standard input: `sys.stdin` reads these bytes, as text, during
                the turn, and `input()` reads its lines; the session's own stdin comes back
                after it. `None` (the default) leaves the session's, which reads end of file.
            on_output: Called with each `OutputChunk` of the turn's output while it runs, on
                the thread that made the call, as `run` calls it. Default: none.
            output_keep: What a stream past this turn's `output_bytes` keeps, "head" or
                "tail", as for `run`. Default: "head".

        Returns:
            How the turn ended.

        Raises:
            TypeError: An argument has the wrong type; the session stays open.
            ValueError: An argument is out of range; the session stays open.
            ArtifactsMissing: `stdin` was given and the artifact set predates a turn's stdin;
                the session stays open.
            SessionEnded: The session has ended, or its idle bound or lifetime has passed;
                in that case the session's ending runs here first, so `run` may block for up
                to `shutdown_s` (plus any call of your own code it makes) before it raises.
            RuntimeError: A turn is already running in this session; this process was forked
                after it ran a guest; the runner lost track of the turn; on Linux, wasmtime's
                trap handlers were replaced after the first run (as `run`; the turn runs no
                guest code and the session ends, without Python's shutdown); or the guest's
                thread is refused (as `run`).
            KeyboardInterrupt: Ctrl-C.
            BaseException: One that is not an `Exception`, raised by your own host, provider,
                tool or gate, propagates.
        """
        _platform._refuse_forked()
        data, fuel, deadline, output = self._turn_args(code, fuel, deadline_s, output_bytes, cancel)
        io = self._turn_io(stdin, on_output, output_keep, asynchronous=False)
        self._claim(here=True)
        args = (self._state, data, fuel, deadline, output, cancel, None, "turn", io)
        return _sessions._session_turn(*args)

    async def run_async(
        self,
        code: str,
        *,
        fuel: int | None = _UNSET,
        deadline_s: float | None = _UNSET,
        output_bytes: int | None = _UNSET,
        executor: concurrent.futures.Executor | None = None,
        stdin: bytes | bytearray | memoryview | None = None,
        on_output: Callable[[OutputChunk], object] | None = None,
        output_keep: Literal["head", "tail"] = "head",
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
            stdin: This turn's standard input, as for `run`.
            on_output: Called with each `OutputChunk` of the turn's output while it runs, on
                the event loop's thread, as `run_async` calls it; an `OutputFeed` too.
            output_keep: What a stream past this turn's `output_bytes` keeps, as for `run`.

        Returns:
            How the turn ended.

        Raises:
            TypeError: An argument has the wrong type; the session stays open.
            ValueError: An argument is out of range; the session stays open.
            ArtifactsMissing: `stdin` was given and the artifact set predates a turn's stdin.
            SessionEnded: The session has ended, or its idle bound or lifetime has passed.
            RuntimeError: A turn is already running in this session; this process was forked
                after it ran a guest; the interpreter is shutting down; the runner lost track
                of the turn; or, on Linux, wasmtime's trap handlers were replaced (as `run`).
            asyncio.CancelledError: The awaiting task was cancelled.
            BaseException: One that is not an `Exception`, raised by your own host, provider,
                tool or gate, propagates.
        """
        with _entry._serving(on_output):  # a feed serves one turn
            _platform._refuse_forked()
            data, fuel, deadline, output = self._turn_args(
                code, fuel, deadline_s, output_bytes, None
            )
            io = self._turn_io(stdin, on_output, output_keep, asynchronous=True)
            _entry._check_executor(executor)
            event = threading.Event()  # the turn's cancel, set when the awaiting task is cancelled
            state = self._state
            return await _entry._awaited(
                io.on_output,
                event,
                executor,
                _current_defaults,
                lambda late, loop: (
                    _sessions._session_turn,
                    state,
                    data,
                    fuel,
                    deadline,
                    output,
                    event,
                    loop,
                    "turn",
                    io._replace(on_output=late),
                ),
                claim=lambda: self._claim(here=False),
                release=self._release_claim,
            )

    def close(self) -> None:
        """End the session, run its ending, and return once its store is closed.

        A turn running on another thread is stopped first, and `close()` waits for it, and for
        the ending, which runs Python's shutdown when the session was at rest (at most its
        `shutdown_s` of guest code, plus any call of your own code it makes). It blocks, so
        from a coroutine it blocks the event loop. Called from inside the session's own turn or
        ending, on the thread that runs it (a host function or a provider, under `run` or
        `run_async` alike), it marks the session and returns at once, and the session ends as
        the turn returns. From any other thread, the event loop's that awaits a `run_async`
        turn and a tool's own thread among them, it waits for the ending. One exception: from
        the event loop's thread before a `run_async` turn has started (still queued for a
        worker), it marks the session and returns at once; the turn then stops as it starts, or,
        if it is cancelled first, the session is ended on a closer, so `shutdown_outcome` may
        still be `None` when that `close()` returns. Calling it again does nothing.

        Raises:
            KeyboardInterrupt: Ctrl-C during the ending, raised once the session is closed.
            BaseException: One that is not an `Exception`, raised by your own host, provider,
                tool or gate during the ending, raised once the session is closed.
        """
        state = self._state
        if process().forked:  # the store and folders are the parent's: touch nothing (lock-free)
            if state.ended is None:
                state.ended = "closed"
            if state.outcome is None:
                state.outcome = "skipped"
            return
        me = threading.get_ident()
        with state.lock:
            _sessions._mark(state, "closed")
            if state.holder == me:
                return  # inside the session's own turn or ending: it ends as that returns
            here = state.phase is _Phase.MARKED and _sessions._claim_ending(state, me)
        if here:
            self._finalizer.detach()
            raised = _sessions._end_with_ctrl_c(state, me)
            if raised is not None:
                raise raised
        state.done.wait()
