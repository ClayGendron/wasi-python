"""What the run family's entry points share: the check of every argument a call's guest
depends on, the pool `run_async` runs on, the registry of its live calls and the exit hook that
stops them, and the one async wrapper that both `run_async`s await.

The defaults are read above, in the runner, where `set_defaults` replaces them, and passed
down: a call's limits as the one `Defaults` its entry point read, and the pool's size as the
reader itself, called under the pool's lock so that the newest `set_defaults` sizes the pool.
`asyncio` and `concurrent.futures` are imported inside the functions that use them, so
`import wasi_python` loads neither.
"""

from __future__ import annotations

import atexit
import contextlib
import contextvars
import functools
import queue
import threading
from collections.abc import Callable, Iterable, Iterator, Mapping
from typing import TYPE_CHECKING, Any, NamedTuple

from wasi_python import _limits, _outputs, _places, _results, _snapshot
from wasi_python._call import _CheckedCall
from wasi_python._limits import _UNSET
from wasi_python._process import process

if TYPE_CHECKING:
    import asyncio
    import concurrent.futures

    from wasi_python._call import Completed
    from wasi_python._outputs import OutputChunk
    from wasi_python.runner import Defaults
    from wasi_python.tools import Tool, ToolCall


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
    executor: concurrent.futures.Executor | None,
    defaults: Callable[[], Defaults],
    fn: Callable[..., Any],
    *args: Any,
) -> concurrent.futures.Future[Any]:
    """Submit to the caller's executor, or to the default pool, made anew when
    `async_workers` changed. The pool's size is process state, not a call's limit: it is read
    here, through `defaults`, under the pool's lock, so the newest `set_defaults` always wins
    and a call that read its limits earlier never sizes the pool back. The lookup,
    any resize and the submit share one lock, so a resize on another thread never leaves a
    submit facing a pool that is shut down."""
    import concurrent.futures

    if executor is not None:
        return executor.submit(fn, *args)
    p = process()
    with p.pool_lock:
        if p.exiting:  # the exit hook has run: never start a pool's call again
            raise RuntimeError("cannot schedule new futures after interpreter shutdown")
        while True:  # count what is done, and let go of a replaced pool with nothing left
            try:
                done = p.pool_done.get_nowait()
            except queue.Empty:
                break
            left = p.pools.get(done, 0) - 1
            if left > 0 or done is p.pool:
                p.pools[done] = max(left, 0)
            else:
                p.pools.pop(done, None)
        size = defaults().async_workers
        if p.pool is None or p.pool_size != size:
            old = p.pool
            new = concurrent.futures.ThreadPoolExecutor(size, thread_name_prefix="wasi-python")
            p.pools[new] = 0
            p.pool, p.pool_size = new, size
            if old is not None:
                old.shutdown(wait=False)  # its running calls finish
                if not p.pools.get(old):  # none of its futures left: nothing for exit to cancel
                    p.pools.pop(old, None)
        pool = p.pool
        future = pool.submit(fn, *args)
        p.pools[pool] = p.pools.get(pool, 0) + 1
    future.add_done_callback(functools.partial(_pool_future_done, pool))
    return future


def _pool_future_done(pool: concurrent.futures.ThreadPoolExecutor, future: Any) -> None:
    """One of a default pool's futures is done, told to the next submit, which counts it under
    the pool's lock: so a pool a resize replaced is let go once none of its futures is left, and
    the process keeps one pool, not one per resize. It takes no lock, since it may run on the
    worker, on the thread that cancelled the future, under the executor's own lock, or in
    `_submit` itself."""
    process().pool_done.put(pool)


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
    calls already running; then the claim of each session's turn whose queued future the pools'
    shutdown cancelled, since its coroutine may never resume to give the claim back, and the
    sessions' own exit hook would wait for a turn that never runs. A release is taken out of
    `live` under its lock, by this hook or by the coroutine's own cancel, so it runs once."""
    p = process()
    with p.pool_lock:
        p.exiting = True
        pools = list(p.pools)
    for pool in pools:
        pool.shutdown(wait=False, cancel_futures=True)
    releases = []
    with p.live_lock:
        events = list(p.live)
        for event, queued in list(p.live.items()):
            if queued is not None and queued[0].cancelled():  # it never starts
                releases.append(queued[1])
                del p.live[event]
    for event in events:
        event.set()
    for release in releases:
        try:
            release()
        except BaseException:
            pass  # an exit hook never raises: the sessions' own hook still ends the session


def _keep_release(
    event: threading.Event, future: concurrent.futures.Future[Any], release: Callable[[], None]
) -> None:
    """Keep, beside a session turn's event in `live`, its future and the release of its claim,
    for the exit hook to run if its shutdown of the pools cancels the turn before it starts.
    When the exit hook has already cancelled it, and so found nothing to run, the release runs
    here instead, after the lock."""
    p = process()
    with p.live_lock:
        if event not in p.live:
            return
        late = p.exiting and future.cancelled()
        if late:
            del p.live[event]
        else:
            p.live[event] = (future, release)
    if late:
        release()


def _take_live(event: threading.Event) -> Callable[[], None]:
    """Take a call's entry out of `live`, and return the release kept beside it, or one that
    does nothing when there is none or the exit hook has taken it: whoever takes a release runs
    it, so it runs once."""
    p = process()
    with p.live_lock:
        queued = p.live.pop(event, None)
    return (lambda: None) if queued is None else queued[1]


@contextlib.contextmanager
def _serving(on_output: object) -> Iterator[None]:
    """The feed `on_output` is, claimed for one call before any check, and ended whatever the
    outcome, so its follower ends."""
    feed = _outputs._claimed(on_output)  # a feed serves one call or turn
    try:
        yield
    finally:
        if feed is not None:
            feed._end()


async def _awaited(
    on_output: Callable[[OutputChunk], object] | None,
    event: threading.Event,
    executor: concurrent.futures.Executor | None,
    defaults: Callable[[], Defaults],
    build: Callable[[_outputs._Late | None, asyncio.AbstractEventLoop], tuple[Any, ...]],
    *,
    claim: Callable[[], None] | None = None,
    release: Callable[[], None] | None = None,
) -> Completed:
    """A checked call or turn, run on a worker and awaited. `on_output` is the checked delivery,
    `event` the cancel kept in `live` for the exit hook, `defaults` `_submit`'s reader of the
    pool's size, and `build` gives the function and its arguments, with the coroutine's own
    delivery and the running loop in place. A session's turn passes `claim`, run before it is
    queued, and `release`, which gives the claim back if the turn never starts. If the awaiting
    task is cancelled, a queued future never starts, and a running one is stopped and awaited
    to its end before `asyncio.CancelledError` is raised."""
    import asyncio

    loop = asyncio.get_running_loop()  # async tools await here
    _register_exit_hook()
    if claim is not None:
        claim()
    late = _outputs._Late.around(on_output)  # the coroutine's: raised after the await
    p = process()
    try:
        with p.live_lock:  # the exit hook sets `exiting` before it reads `live`
            if p.exiting:
                raise RuntimeError("cannot schedule new futures after interpreter shutdown")
            p.live[event] = None
        work = contextvars.copy_context().run  # a door host sees the request's context
        future = _submit(executor, defaults, work, *build(late, loop))
    except BaseException:
        _take_live(event)
        if release is not None:
            release()
        raise
    if release is not None:
        _keep_release(event, future, release)
    try:
        try:
            done: Completed = await asyncio.wrap_future(future)
            _outputs._Late.check(late)
            return done
        except asyncio.CancelledError:
            if future.cancel():  # still queued: it never starts, and a session is untouched
                _take_live(event)()  # a turn's claim released, unless the exit hook did it
                raise
            event.set()
            while not future.done():  # wait for the worker, whatever the call's outcome
                try:
                    await asyncio.wrap_future(future)
                except BaseException:
                    pass
            raise
    finally:
        _take_live(event)


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
    max_host_request_bytes: Any = _UNSET,
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
    limits: Defaults,
    snapshot: Any = True,
    on_output: Any = None,
    output_keep: Any = "head",
    results: Any = False,
    figures: Any = False,
    asynchronous: bool = False,
) -> _CheckedCall:
    """Every argument a call's guest depends on, checked before any work, as one frozen record
    built from its typed parts. Its entry point read the defaults once
    (`async_workers` is `_submit`'s, read under the pool's lock); `asynchronous` says an event
    loop awaits the call; `results` and `figures` set its mode."""
    tool_args = _check_tools(
        host, tools, gate, max_tool_calls, limits, max_tool_request_bytes=max_tool_request_bytes
    )
    memory_bytes = limits.memory_bytes if memory_bytes is _UNSET else memory_bytes
    deadline_s = limits.deadline_s if deadline_s is _UNSET else deadline_s
    output_bytes = limits.output_bytes if output_bytes is _UNSET else output_bytes
    cancel = _limits._check_cancel(cancel)
    bounds = _limits._check_limits(fuel, deadline_s, memory_bytes, output_bytes)
    binary, start = _snapshot._start(snapshot, bounds.memory_bytes)
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
        output_keep=_limits._check_output_keep(output_keep),
        on_output=_outputs._check_on_output(on_output, asynchronous=asynchronous),
        argv=inputs.argv,
        env=inputs.env,
        stdin=inputs.stdin,
        cancel=cancel,
        tools=tool_args.tools,
        gate=tool_args.gate,
        tool_calls=tool_args.tool_calls,
        tool_request_bytes=tool_args.tool_request_bytes,
        host_request_bytes=_raw_request_limit(host, max_host_request_bytes, limits),
        root=places.root,
        grants=places.grants,
        mounts=places.mounts,
        import_path=places.import_path,
        import_serving=places.import_serving,
        file_calls=places.file_calls,
        open_files=places.open_files,
        binary=binary,
        start=start,
        results=_results._check_results(results, figures, host, inputs.argv),
    )


def _raw_request_limit(host: Any, value: Any, limits: Defaults) -> int | None:
    if host is None:
        if value is not _UNSET:
            raise TypeError("max_host_request_bytes= requires host=")
        return None
    return _limits._integer_limit(
        "max_host_request_bytes", limits.host_request_bytes if value is _UNSET else value
    )


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
    limits: Defaults,
    *,
    max_tool_request_bytes: Any = _UNSET,
) -> _ToolArgs:
    """tools=, gate= and max_tool_calls= as plain values: a tuple of
    `Tool`s with unique names, a gate that is not an async generator function, the frame limit,
    and the byte budget (with tools= only: a call without tools has every field None). A
    plain function goes through `tool()`. `wasi_python.tools` is imported only when tools are
    given, so `import wasi_python` still does not import it. An async `host=` is
    refused."""
    if host is not None and _limits._is_async_callable(host):
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
                "max_tool_calls= without tools= limits nothing: the raw door has no frame count; "
                "pass tools="
            )
        if max_tool_request_bytes is not _UNSET:
            raise TypeError(
                "max_tool_request_bytes= without tools= limits nothing; pass tools= or use "
                "max_host_request_bytes= with host="
            )
        return _ToolArgs(None, None, None, None)
    if host is not None:
        raise TypeError("pass host= for the raw door or tools= for the tool protocol, not both")
    from wasi_python.tools import Tool, _is_async_generator, tool

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
    if max_tool_calls is _UNSET:
        max_tool_calls = limits.tool_calls
    if max_tool_request_bytes is _UNSET:
        max_tool_request_bytes = limits.tool_request_bytes
    return _ToolArgs(
        tuple(checked),
        gate,
        _limits._integer_limit("max_tool_calls", max_tool_calls),
        _limits._integer_limit("max_tool_request_bytes", max_tool_request_bytes),
    )
