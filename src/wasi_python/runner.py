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

import atexit
import contextvars
import os
import threading
import weakref
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, NamedTuple

from . import _call, _engines, _limits, _places, _platform, _private_dirs, _sessions
from ._artifacts import Artifacts
from ._call import Completed as Completed  # re-exported: the public API names them here
from ._call import _CheckedCall
from ._limits import _UNSET
from ._places import Grant as Grant
from ._process import process
from ._sessions import _CLOSER, MAX_TURN_BYTES, _Event, _Phase, _State
from ._sessions import SessionEnded as SessionEnded
from .mounts import Mount

if TYPE_CHECKING:
    import asyncio
    import concurrent.futures

    from .tools import Tool, ToolCall


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

    The guest runs on a thread of the runner's own, with an 8 MiB wasm stack; your `host`,
    providers and tools' contexts are served on the calling thread, which waits. The guest sees
    no host folder but the read-only stdlib, and what `root`, `grants` and
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
            /tmp is writable, else an empty one the guest cannot write.
        stdin: The guest's standard input, whole; `None` is empty.
        host: The door's host function: called with each request's bytes, on the thread that
            made the call, it returns the response's. It must answer synchronously: an async one
            raises `TypeError`. Excludes `tools`.
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
        cache_dir: Where compiled modules are kept as .cwasm files, a folder only you and the
            runner write: never one a guest is granted, in this or another call. `None` or
            `True` uses `$WASI_PYTHON_CACHE`, else the user's cache folder; `False` keeps them
            in this process only, never on disk.
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
    return _run_checked_flushed(wt, checked, host, snapshot, cache_dir, artifacts, None)


def _run_checked_flushed(
    wt: Any,
    checked: _CheckedCall,
    host: Callable[[bytes], bytes | bytearray | memoryview] | None,
    snapshot: bool,
    cache_dir: str | os.PathLike[str] | None | bool,
    artifacts: Artifacts | None,
    loop: asyncio.AbstractEventLoop | None,
) -> Completed:
    """`_run_checked`, then the warnings its removals queued, outside every lock."""
    try:
        return _call._run_checked(wt, checked, host, snapshot, cache_dir, artifacts, loop)
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
            /tmp is writable, else an empty one the guest cannot write.
        stdin: The guest's standard input, whole; `None` is empty.
        host: The door's host function: called with each request's bytes, on the thread that
            made the call, it returns the response's. It must answer synchronously: an async one
            raises `TypeError`. Excludes `tools`.
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
        cache_dir: Where compiled modules are kept as .cwasm files, a folder only you and the
            runner write: never one a guest is granted, in this or another call. `None` or
            `True` uses `$WASI_PYTHON_CACHE`, else the user's cache folder; `False` keeps them
            in this process only, never on disk.
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
    import asyncio
    import contextvars

    _platform._refuse_forked()
    event = threading.Event()  # the call's cancel, set when the awaiting task is cancelled
    checked = _checked(
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
    )
    _check_executor(executor)
    loop = asyncio.get_running_loop()  # async tools await here
    wt = _engines._wasmtime()
    _register_exit_hook()
    p = process()
    with p.live_lock:  # the exit hook sets `exiting` before it reads `live`
        if p.exiting:
            raise RuntimeError("cannot schedule new futures after interpreter shutdown")
        p.live.add(event)
    try:
        work = contextvars.copy_context().run  # a door host sees the request's context
        args = (_run_checked_flushed, wt, checked, host, snapshot, cache_dir, artifacts, loop)
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
        with p.live_lock:
            p.live.discard(event)


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


def _submit(
    executor: concurrent.futures.Executor | None, fn: Callable[..., Any], *args: Any
) -> concurrent.futures.Future[Any]:
    """Submit to the caller's executor, or to the default pool, made anew when
    `async_workers` changed. The pool's size is process state, not a call's limit: it is read
    here, under the pool's lock, so the newest `set_defaults` always wins and a call that read
    its limits earlier never sizes the pool back. The lookup,
    any resize and the submit share one lock, so a resize on another thread never leaves a
    submit facing a pool that is shut down."""
    import concurrent.futures

    if executor is not None:
        return executor.submit(fn, *args)
    p = process()
    with p.pool_lock:
        if p.exiting:  # the exit hook has run: never start a pool's call again
            raise RuntimeError("cannot schedule new futures after interpreter shutdown")
        size = _current_defaults().async_workers
        if p.pool is None or p.pool_size != size:
            old = p.pool
            new = concurrent.futures.ThreadPoolExecutor(size, thread_name_prefix="wasi-python")
            p.pools.append(new)
            p.pool, p.pool_size = new, size
            if old is not None:
                old.shutdown(wait=False)  # its running calls finish
        return p.pool.submit(fn, *args)


def _register_exit_hook() -> None:
    """At exit, stop run_async's guests and drop its queued calls. threading runs its exit hooks
    in reverse order of registration, so this one, registered after concurrent.futures.thread is
    imported, runs before that module joins the pools' workers; registered before, exit would
    wait for every queued call (EXECUTED both ways)."""
    p = process()
    with p.pool_lock:
        if p.exit_hook_registered:
            return
        import concurrent.futures.thread  # noqa: F401  (its hook first, so ours runs before it)

        register = getattr(threading, "_register_atexit", None)
        if register is not None:
            register(_stop_async_calls)
        else:
            atexit.register(_stop_async_calls)
        p.exit_hook_registered = True


def _stop_async_calls() -> None:
    """Pools first, so no call can be submitted after its event was missed; then the events of the
    calls already running."""
    p = process()
    with p.pool_lock:
        p.exiting = True
        pools = list(p.pools)
    for pool in pools:
        pool.shutdown(wait=False, cancel_futures=True)
    with p.live_lock:
        events = list(p.live)
    for event in events:
        event.set()


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
) -> _CheckedCall:
    """Every argument a call's guest depends on, checked before any work, as one frozen record
    built from its typed parts, each field named. The defaults are read once, here, and every
    check that takes one takes it from this read, so a `set_defaults` on another thread never
    gives a call a mix of the old and new limits. `async_workers` is not a call's limit:
    `_submit` reads it under the pool's lock. A session passes the `limits` it read."""
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
    bounds = _limits._check_limits(fuel, deadline_s, memory_bytes, output_bytes)
    inputs = _limits._check_inputs(argv, env, stdin)
    places = _places._check_places(
        root,
        grants,
        mounts,
        max_file_calls,
        limits,
        import_path=import_path,
        max_open_files=max_open_files,
    )
    return _CheckedCall(
        fuel=bounds.fuel,
        deadline_s=bounds.deadline_s,
        memory_bytes=bounds.memory_bytes,
        output_bytes=bounds.output_bytes,
        argv=inputs.argv,
        env=inputs.env,
        stdin=inputs.stdin,
        cancel=cancel,
        tools=tool_args.tools,
        gate=tool_args.gate,
        tool_calls=tool_args.tool_calls,
        tool_request_bytes=tool_args.tool_request_bytes,
        root=places.root,
        grants=places.grants,
        mounts=places.mounts,
        import_path=places.import_path,
        import_serving=places.import_serving,
        file_calls=places.file_calls,
        open_files=places.open_files,
    )


def _is_async_callable(fn: Any) -> bool:
    """Whether calling `fn` makes a coroutine or an async generator, read through `partial`s and
    at an object's `__call__`, as `tool()` reads a tool. It does not
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


class _ToolArgs(NamedTuple):
    """A call's tool protocol arguments, checked: all `None` for a call without tools."""

    tools: tuple[Tool, ...] | None
    gate: Callable[[ToolCall], Any] | None
    tool_calls: int | None
    tool_request_bytes: int | None


def _check_tools(
    host: Any,
    tools: Any,
    gate: Any,
    max_tool_calls: Any,
    limits: Defaults | None = None,
    *,
    max_tool_request_bytes: Any = _UNSET,
) -> _ToolArgs:
    """tools=, gate= and max_tool_calls= as plain values: a tuple of
    `Tool`s with unique names, a gate that is not an async generator function, the frame limit,
    and the byte budget (with tools= only: a call without tools has every field None). A
    plain function goes through `tool()`. `wasi_python.tools` is imported only when tools are
    given, so `import wasi_python` still does not import it. An async `host=` is
    refused."""
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
        return _ToolArgs(None, None, None, None)
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
        read = limits if limits is not None else _current_defaults()  # one read, whichever is unset
        if max_tool_calls is _UNSET:
            max_tool_calls = read.tool_calls
        if max_tool_request_bytes is _UNSET:
            max_tool_request_bytes = read.tool_request_bytes
    return _ToolArgs(
        tuple(checked),
        gate,
        _limits._integer_limit("max_tool_calls", max_tool_calls),
        _limits._integer_limit("max_tool_request_bytes", max_tool_request_bytes),
    )


def stats() -> dict[str, int]:
    """Counts kept by this process, a diagnostic.

    `tool_threads_running` counts the tool threads alive in this process, abandoned ones
    included. `sessions_open` counts the `Session`s opened and not yet ended. `compiled`,
    `loaded` and `written` count how this process got its compiled modules: compiled from the
    binary, loaded from a .cwasm file, and .cwasm files written; what they count may change with
    the cache. A later release may add keys.
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
                where /tmp is writable, else an empty one the guest cannot write.
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
            cache_dir: Where compiled modules are kept as .cwasm files, a folder only you and
                the runner write: never one a guest is granted, in this or another call. `None`
                or `True` uses `$WASI_PYTHON_CACHE`, else the user's cache folder; `False` keeps
                them in this process only, never on disk.
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
        _platform._refuse_forked()
        wt = _engines._wasmtime()
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
        if not isinstance(snapshot, bool):
            raise TypeError(f"snapshot must be a bool; got {type(snapshot).__name__}")
        state.host = host
        state.context = contextvars.copy_context()
        self._state = state
        try:
            _sessions._open_session(wt, c, host, snapshot, cache_dir, artifacts, state)
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
        self._finalizer.atexit = False  # type: ignore[misc]
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
        if cancel is not None and not isinstance(cancel, threading.Event):
            raise TypeError(
                f"cancel must be a threading.Event, or None; got {type(cancel).__name__}"
            )
        return data, fuel, deadline, output

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

    def _release_claim(self) -> None:
        state = self._state
        with state.lock:
            _sessions._move(state, _Event.RELEASE)  # from TURN, or STOPPING after a close()
        _sessions._wake_reaper()

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
        self._claim(here=True)
        return _sessions._session_turn(self._state, data, fuel, deadline, output, cancel, None)

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

        _platform._refuse_forked()
        data, fuel, deadline, output = self._turn_args(code, fuel, deadline_s, output_bytes, None)
        _check_executor(executor)
        loop = asyncio.get_running_loop()
        _register_exit_hook()
        self._claim(here=False)
        event = threading.Event()
        state = self._state
        p = process()
        try:
            with p.live_lock:
                if p.exiting:
                    raise RuntimeError("cannot schedule new futures after interpreter shutdown")
                p.live.add(event)
            work = contextvars.copy_context().run
            args = (_sessions._session_turn, state, data, fuel, deadline, output, event, loop)
            future = _submit(executor, work, *args)
        except BaseException:
            with p.live_lock:
                p.live.discard(event)
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
            with p.live_lock:
                p.live.discard(event)

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
