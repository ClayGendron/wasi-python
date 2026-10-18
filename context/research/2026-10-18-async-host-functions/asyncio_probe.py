"""Probe A: the asyncio facts spec 053's design rests on, with no guest.

Run: uv run --python 3.11 --isolated --no-project python -I asyncio_probe.py
     uv run python -I asyncio_probe.py            (the dev environment's 3.14)

Each case prints one line of counts and booleans. Waits that end a case use a generous timeout
only as a fail-safe; no line reports a time.
"""

from __future__ import annotations

import asyncio
import contextvars
import functools
import gc
import inspect
import sys
import threading

REQUEST = contextvars.ContextVar("request", default="unset")


def a1_worker_thread_to_a_free_loop() -> None:
    """A door thread (a worker) posts a coroutine to the loop that awaits the worker through
    wrap_future, as run_async does. The loop keeps turning while the worker waits."""

    async def main() -> tuple[object, int, bool]:
        loop = asyncio.get_running_loop()
        turns = 0
        stop = False

        async def spin() -> None:
            nonlocal turns
            while not stop:
                turns += 1
                await asyncio.sleep(0)

        async def tool() -> tuple[str, bool]:
            for _ in range(100):
                await asyncio.sleep(0)
            return threading.current_thread().name, asyncio.get_running_loop() is loop

        def door() -> tuple[str, bool]:
            return asyncio.run_coroutine_threadsafe(tool(), loop).result(timeout=30)

        spinner = asyncio.ensure_future(spin())
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(1) as pool:
            answer = await asyncio.wrap_future(pool.submit(door))
        stop = True
        await spinner
        return answer, turns, turns > 100

    answer, turns, free = asyncio.run(main())
    print(f"A1 tool ran on {answer[0]!r}, on the caller's loop {answer[1]}; loop turned while the"
          f" worker waited: {free}")


def a2_the_loops_own_thread_blocked() -> None:
    """`run` called inside a coroutine blocks the loop's thread. A coroutine posted to that loop
    from the door thread never starts while it is blocked."""

    async def main() -> tuple[bool, bool]:
        loop = asyncio.get_running_loop()
        started = threading.Event()

        async def tool() -> None:
            started.set()

        def door() -> None:
            asyncio.run_coroutine_threadsafe(tool(), loop)

        t = threading.Thread(target=door)
        t.start()
        t.join()
        # The loop's thread now blocks, as a sync run() inside a coroutine would.
        began_while_blocked = started.wait(1.0)
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        return began_while_blocked, started.is_set()

    blocked, later = asyncio.run(main())
    print(f"A2 a coroutine posted to a blocked loop started while it was blocked: {blocked};"
          f" started once the loop turned again: {later}")


def a3_context_reaches_the_task() -> None:
    """The task made by run_coroutine_threadsafe runs in a copy of the posting thread's context,
    including a value set inside `context.run` on that thread."""
    loop = asyncio.new_event_loop()
    t = threading.Thread(target=loop.run_forever, daemon=True)
    t.start()

    async def tool() -> str:
        return REQUEST.get()

    def door() -> str:
        REQUEST.set("from the request")
        ctx = contextvars.copy_context()

        def work() -> str:
            return asyncio.run_coroutine_threadsafe(tool(), loop).result(timeout=30)

        return ctx.run(work)

    seen = []
    w = threading.Thread(target=lambda: seen.append(door()))
    w.start()
    w.join()
    loop.call_soon_threadsafe(loop.stop)
    t.join()
    loop.close()
    print(f"A3 the task saw the posting thread's context: {seen == ['from the request']}"
          f" ({seen[0]!r}); the loop thread's own value: {REQUEST.get()!r}")


def a4_cancelling_the_concurrent_future() -> None:
    """cf.cancel() on run_coroutine_threadsafe's future succeeds at once and its waiter wakes,
    while the task itself only receives a cancel request; a task that suppresses it runs on. A
    wrapper's `finally` marks the task's real end."""
    loop = asyncio.new_event_loop()
    t = threading.Thread(target=loop.run_forever, daemon=True)
    t.start()
    for case in ("clean", "suppresses"):
        ended = threading.Event()
        release = threading.Event()
        steps = []
        saw_cancel = []

        async def tool() -> None:
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                saw_cancel.append(True)
                if case == "clean":
                    raise
            # suppressed: keep working until released
            while not release.is_set():
                steps.append(1)
                await asyncio.sleep(0.001)

        async def wrapper() -> None:
            try:
                await tool()
            finally:
                ended.set()

        cf = asyncio.run_coroutine_threadsafe(wrapper(), loop)
        while not cf.running() and not cf.done():  # the task exists once the loop has run it
            threading.Event().wait(0.001)
            break
        threading.Event().wait(0.05)  # let the task reach its await (fail-safe pacing only)
        cancelled = cf.cancel()
        try:
            cf.result(timeout=5)
            woke = "returned"
        except BaseException as e:  # concurrent.futures.CancelledError
            woke = type(e).__name__
        ended_at_wake = ended.is_set()
        ended_later = ended.wait(1.0)
        release.set()
        ended_after_release = ended.wait(5.0)
        print(f"A4 {case}: cf.cancel() -> {cancelled}; the waiter woke with {woke}; task ended"
              f" when the waiter woke: {ended_at_wake}; ended within the next second:"
              f" {ended_later}; saw CancelledError: {bool(saw_cancel)}; steps after the cancel:"
              f" {'>0' if steps else 0}; ended once released: {ended_after_release}")
    loop.call_soon_threadsafe(loop.stop)
    t.join()
    loop.close()


def a5_a_closed_loop() -> None:
    loop = asyncio.new_event_loop()
    loop.close()

    async def tool() -> None:
        pass

    coro = tool()
    try:
        asyncio.run_coroutine_threadsafe(coro, loop)
        what = "accepted"
    except RuntimeError as e:
        what = f"RuntimeError: {e}"
    finally:
        coro.close()
    print(f"A5 posting to a closed loop: {what}")


def a6_base_exceptions_in_a_task() -> None:
    """KeyboardInterrupt and SystemExit raised in a task leave the loop: the embedder's own
    asyncio.run would see them. A wrapper that catches BaseException keeps them in the call."""
    for exc in (KeyboardInterrupt, SystemExit):

        async def tool() -> None:
            raise exc()

        async def main() -> str:
            task = asyncio.ensure_future(tool())
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            return f"main returned, task.done()={task.done()}"

        try:
            out = asyncio.run(main())
        except BaseException as e:
            out = f"asyncio.run raised {type(e).__name__}"

        async def wrapped() -> str:
            try:
                await tool()
            except BaseException as e:
                return f"caught {type(e).__name__}"
            return "no exception"

        async def main2() -> str:
            return await asyncio.ensure_future(wrapped())

        print(f"A6 {exc.__name__} in a bare task: {out}; in a wrapper: {asyncio.run(main2())}")


def a7_made_on_one_thread_awaited_on_another() -> None:
    loop = asyncio.new_event_loop()
    t = threading.Thread(target=loop.run_forever, daemon=True, name="loop-thread")
    t.start()

    async def tool() -> str:
        await asyncio.sleep(0)
        return threading.current_thread().name

    async def awaiting(aw):
        return await aw

    coro = tool()  # made on the main thread: runs no code yet
    fut = asyncio.Future(loop=loop)
    loop.call_soon_threadsafe(fut.set_result, "a future of that loop")
    a = asyncio.run_coroutine_threadsafe(awaiting(coro), loop).result(timeout=30)
    b = asyncio.run_coroutine_threadsafe(awaiting(fut), loop).result(timeout=30)
    other = asyncio.new_event_loop()
    foreign = other.create_future()
    try:
        asyncio.run_coroutine_threadsafe(awaiting(foreign), loop).result(timeout=30)
        c = "awaited"
    except BaseException as e:
        c = f"{type(e).__name__}: {str(e).splitlines()[0][:60]}"
    other.close()
    loop.call_soon_threadsafe(loop.stop)
    t.join()
    loop.close()
    print(f"A7 a coroutine made on the main thread ran on {a!r}; a Future of that loop: {b!r};"
          f" a Future of another loop: {c}")


def a8_a_private_loop_shuts_down() -> None:
    """A per-call loop on its own thread: at the call's end, cancel every task, wait for them
    on the loop, stop, close. A task that suppresses the cancel keeps the thread alive."""
    for case in ("clean", "suppresses"):
        loop = asyncio.new_event_loop()
        release = threading.Event()

        def serve() -> None:
            loop.run_forever()
            loop.close()

        t = threading.Thread(target=serve, daemon=True)
        t.start()

        async def tool() -> None:
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                if case == "clean":
                    raise
            while not release.is_set():
                await asyncio.sleep(0.001)

        async def background() -> None:  # a task the tool itself spawned, never awaited
            await asyncio.Event().wait()

        asyncio.run_coroutine_threadsafe(tool(), loop)
        loop.call_soon_threadsafe(lambda: loop.create_task(background()))
        threading.Event().wait(0.05)

        async def shutdown() -> None:
            me = asyncio.current_task()
            tasks = [x for x in asyncio.all_tasks() if x is not me]
            for x in tasks:
                x.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            loop.stop()

        loop.call_soon_threadsafe(lambda: loop.create_task(shutdown()))
        t.join(1.0)
        alive = t.is_alive()
        release.set()
        t.join(5.0)
        print(f"A8 {case}: loop thread alive a second after the shutdown request: {alive};"
              f" ended once released: {not t.is_alive()}; loop closed: {loop.is_closed()}")


def a9_what_counts_as_async() -> None:
    async def coro_fn(x: int) -> int:
        return x

    async def agen_fn():
        yield 1

    class AsyncCall:
        async def __call__(self) -> None:
            pass

    def returns_coro():
        return coro_fn(1)

    c = returns_coro()
    loop = asyncio.new_event_loop()
    fut = loop.create_future()
    rows = {
        "async def": inspect.iscoroutinefunction(coro_fn),
        "partial(async def)": inspect.iscoroutinefunction(functools.partial(coro_fn, 1)),
        "async __call__ (the class's)": inspect.iscoroutinefunction(AsyncCall.__call__),
        "async generator fn is a coroutine fn": inspect.iscoroutinefunction(agen_fn),
        "def returning a coroutine": inspect.iscoroutinefunction(returns_coro),
        "isawaitable(its result)": inspect.isawaitable(c),
        "isawaitable(Future)": inspect.isawaitable(fut),
        "isawaitable(async generator)": inspect.isawaitable(agen_fn()),
    }
    c.close()
    loop.close()
    print("A9 " + "; ".join(f"{k}: {v}" for k, v in rows.items()))


if __name__ == "__main__":
    print(f"python {sys.version.split()[0]}")
    a1_worker_thread_to_a_free_loop()
    a2_the_loops_own_thread_blocked()
    a3_context_reaches_the_task()
    a4_cancelling_the_concurrent_future()
    a5_a_closed_loop()
    a6_base_exceptions_in_a_task()
    a7_made_on_one_thread_awaited_on_another()
    a8_a_private_loop_shuts_down()
    a9_what_counts_as_async()
    gc.collect()
