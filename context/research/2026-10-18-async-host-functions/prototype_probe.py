"""Probe B: async tools through the real runner and a real guest, by a throwaway patch.

Run from the worktree, against a frozen artifact set that carries the guest package:
    WASI_PYTHON_ARTIFACTS=<set> uv run python -I <this file>

The patch (in this process only; `src/` is not changed) gives `tools._Work` the rule spec 053
proposes: call the gate and the tool on the work's own thread as today; when the tool's result
is awaitable, run it on a loop (a private loop on its own thread under `run`, the caller's loop
under `run_async`) and wait for the task's real end. It gives `tools._Bounded._abandon` one
more act: when a call is answered without its work, the in-flight task is asked to cancel.
`tool()` still refuses `async def`, so each tool here is a plain function returning a
coroutine, which the same rule covers.

Each scenario prints one line. Nothing measures time; waits are fail-safes.
"""

from __future__ import annotations

import asyncio
import threading

from wasi_python import run, run_async, runner
from wasi_python import tools as T

# ----------------------------------------------------------------------------------------------
# The throwaway patch

LOOP: dict[str, asyncio.AbstractEventLoop | None] = {"loop": None}
IN_FLIGHT: list = []  # (concurrent future, ended event) of the call now running
_original_work = T._Work.__call__
_original_abandon = T._Bounded._abandon


def _await_on_loop(awaitable):
    loop = LOOP["loop"]
    ended = threading.Event()
    box: dict = {}

    async def wrapper():
        try:
            box["value"] = await awaitable
        except BaseException as e:  # a CancelledError included: the call keeps it
            box["error"] = e
        finally:
            ended.set()

    cf = asyncio.run_coroutine_threadsafe(wrapper(), loop)
    IN_FLIGHT.append((cf, ended))
    while not ended.wait(runner.TICK_S):  # the task's real end, not the future's
        if loop.is_closed():
            raise RuntimeError("the tool loop closed")
    if "error" in box:
        raise box["error"]
    return box["value"]


def patched_work(self):
    fn = self.tool.fn

    def call(**args):
        value = fn(**args)
        if hasattr(value, "__await__"):
            return _await_on_loop(value)
        return value

    object.__setattr__(self.tool, "fn", call)
    try:
        return _original_work(self)
    finally:
        object.__setattr__(self.tool, "fn", fn)


def patched_abandon(self, slot):
    abandoned = _original_abandon(self, slot)
    if abandoned and IN_FLIGHT:
        cf, _ = IN_FLIGHT[-1]
        cf.cancel()  # asks the task to cancel; its thread waits for the real end
    return abandoned


T._Work.__call__ = patched_work
T._Bounded._abandon = patched_abandon


class PrivateLoop:
    def __enter__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(
            target=self.loop.run_forever, name="wasi-python-tool-loop", daemon=True
        )
        self.thread.start()
        LOOP["loop"] = self.loop
        return self

    def __exit__(self, *exc):
        async def shutdown():
            me = asyncio.current_task()
            tasks = [t for t in asyncio.all_tasks() if t is not me]
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            self.loop.stop()

        self.loop.call_soon_threadsafe(lambda: self.loop.create_task(shutdown()))
        self.thread.join(30)
        self.loop.close()
        LOOP["loop"] = None


# ----------------------------------------------------------------------------------------------
# Tools: plain functions returning coroutines

SEEN: dict = {}


def fetch(n: int) -> dict:
    """Fetch n things."""

    async def go():
        for _ in range(n):
            await asyncio.sleep(0)
        SEEN["loop"] = asyncio.get_running_loop()
        return {"n": n, "thread": threading.current_thread().name}

    return go()


def stall_coro():
    async def go():
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            SEEN.setdefault("cancelled", threading.Event()).set()
            raise

    return go()


def stall() -> dict:
    """Wait forever."""
    return stall_coro()


GUEST_FETCH = "from host import tools\nprint(tools.fetch(3))\n"
GUEST_STALL = (
    "from host import tools, ToolTimeout\n"
    "try:\n    tools.stall()\nexcept ToolTimeout as e:\n    print('ToolTimeout', e)\n"
)


def outcomes(done):
    return [(o.op, o.tool, o.outcome, o.abandoned) for o in done.tools.outcomes]


def joined():
    for t in threading.enumerate():
        if t.name.startswith("wasi-python-tool-") and t.name != "wasi-python-tool-loop":
            t.join(30)


def b1_run_on_a_private_loop():
    with PrivateLoop():
        done = run(["-c", GUEST_FETCH], tools=[fetch])
    print(f"B1 run: exit {done.exit_code}; stdout {done.stdout!r}; outcomes {outcomes(done)}")


def b2_run_async_on_the_callers_loop():
    async def main():
        loop = asyncio.get_running_loop()
        LOOP["loop"] = loop
        turns, stop = 0, False

        async def spin():
            nonlocal turns
            while not stop:
                turns += 1
                await asyncio.sleep(0)

        spinner = asyncio.ensure_future(spin())
        done = await run_async(["-c", GUEST_FETCH], tools=[fetch])
        stop = True
        await spinner
        return done, SEEN.get("loop") is loop, turns > 0

    done, same, turned = asyncio.run(main())
    LOOP["loop"] = None
    print(f"B2 run_async: exit {done.exit_code}; stdout {done.stdout!r}; the tool ran on the"
          f" caller's loop {same}; the loop turned meanwhile {turned}; outcomes {outcomes(done)}")


def b3_timeout_cancels_the_task():
    SEEN.pop("cancelled", None)
    SEEN["cancelled"] = threading.Event()
    before = runner.stats()["tool_threads_running"]
    slow = T.tool(stall, timeout_s=0.05)
    with PrivateLoop():
        done = run(["-c", GUEST_STALL], tools=[slow])
        saw = SEEN["cancelled"].wait(30)
        joined()
    after = runner.stats()["tool_threads_running"]
    print(f"B3 timeout_s: stdout {done.stdout!r}; outcomes {outcomes(done)}; the task saw"
          f" CancelledError {saw}; tool threads back to where they were {after == before}")


def b4_deadline_cancels_the_task():
    SEEN["cancelled"] = threading.Event()
    with PrivateLoop():
        done = run(["-c", GUEST_STALL], tools=[stall], deadline_s=1)
        saw = SEEN["cancelled"].wait(30)
        joined()
    print(f"B4 deadline_s=1, no timeout_s: stdout {done.stdout!r}; last outcome"
          f" {outcomes(done)[-1]}; message {done.tools.outcomes[-1].message!r}; the task saw"
          f" CancelledError {saw}")


def b5_cancelling_run_async_cancels_the_task():
    SEEN["cancelled"] = threading.Event()
    started = threading.Event()

    def stall_started() -> dict:
        """Wait forever, after saying so."""
        started.set()
        return stall_coro()

    async def main():
        LOOP["loop"] = asyncio.get_running_loop()
        task = asyncio.ensure_future(
            run_async(["-c", GUEST_STALL.replace("stall()", "stall_started()")],
                      tools=[stall_started], deadline_s=None)
        )
        await asyncio.to_thread(started.wait, 30)
        task.cancel()
        try:
            await task
            how = "returned"
        except asyncio.CancelledError:
            how = "CancelledError"
        saw = await asyncio.to_thread(SEEN["cancelled"].wait, 30)
        nxt = await run_async(["-c", GUEST_FETCH], tools=[fetch])
        return how, saw, nxt.stdout

    how, saw, nxt = asyncio.run(main())
    LOOP["loop"] = None
    print(f"B5 run_async cancelled during an async tool: the task raised {how}; the tool's task"
          f" saw CancelledError {saw}; the next call printed {nxt!r}")


if __name__ == "__main__":
    b1_run_on_a_private_loop()
    b2_run_async_on_the_callers_loop()
    b3_timeout_cancels_the_task()
    b4_deadline_cancels_the_task()
    b5_cancelling_run_async_cancels_the_task()
