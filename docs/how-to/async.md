# Run the guest from async code

This guide shows you how to run the guest from asyncio code, such as a web endpoint, without
blocking the event loop, and how to cancel a call and size the worker pool.

## Await run_async

`run_async` takes `run`'s arguments except `cancel`, plus `executor`. It runs the call on a worker
thread, so the event loop never waits for a guest. wasmtime releases the GIL while WebAssembly
runs, so guests on different workers run in parallel.

This is an ASGI endpoint, shown with FastAPI:

```python
import asyncio
from wasi_python import run_async

@app.post("/run")
async def run_code(code: str):
    async with asyncio.timeout(30):  # also bounds the time spent waiting for a worker
        done = await run_async(["-c", code])
    return {"exit_code": done.exit_code, "stdout": done.stdout.decode()}
```

A `Session` has the same method for its turns: `await session.run_async(code)`.

## Cancel a call

To stop a guest, cancel its task. `run_async` has no `cancel` argument; the task's cancellation
is the cancel.

- **Cancelling the task stops its guest.** The runner checks for a cancel every 50 ms while the
  guest computes, and at once when the guest waits or calls the host. The check needs the GIL, so
  other busy Python threads delay it. The worker is freed and the private root removed before
  `CancelledError`, or the timeout's `TimeoutError`, reaches your code.
- **A call still waiting for a worker never starts.**
- **A guest inside a host function** stops only when that function returns. The runner cannot
  interrupt host code.
- **What cancels the task is your code**: a timeout, a task group, shutdown. Starlette does not
  cancel a plain endpoint's task when the client disconnects. So without a timeout, that guest
  runs to its `deadline_s`.

## Size the worker pool

With no `executor`, calls share one pool per process of `defaults().async_workers` threads. That
is the CPU count, at most 8. With CPU affinity, from Python 3.13, it is the CPUs this process may
use. Further calls wait for a worker.

At the defaults, each running guest may hold 1 GiB of memory, up to 32 MiB of output and a copy
of its `stdin`. So 8 workers bound one process at about 8.3 GiB, plus the disk a guest writes and
up to `max_open_files` file descriptors each. Four server worker processes have four pools: four
times that.

A container's CPU quota is not seen. Set the size yourself:

```python
set_defaults(dataclasses.replace(defaults(), async_workers=n))
```

A new size applies to calls submitted afterwards. Calls already running or queued on the old pool
still run there. The bound covers only `run_async` on its own pool. It does not cover `run`
called from your own threads, an `executor` you pass, or a framework's thread pool for
synchronous endpoints.

## Pass your own executor

`executor=` must run callables on threads of this process. A process pool or an interpreter pool
is refused. The guest itself runs on a thread of the runner's own, so the executor's thread stack
size does not matter.

A synchronous endpoint that calls `run` also keeps the loop free, since the framework runs it on a
thread. But it cannot be cancelled.

## Fork before the first guest

A process forked after it ran a guest refuses to run guests, with `RuntimeError`: wasmtime does not
support use across a fork. Warm the runner up after the fork, in gunicorn's `post_fork` for
example, never before.

## Know what happens at exit

At interpreter exit, `run_async`'s running guests are stopped together and its queued calls
dropped. So exit waits about as long as one cancel. It waits longer for a worker inside a host
function or still compiling.

## Await inside a tool, not a raw host function

A host function that must await is best served as an async tool. The runner awaits it on your
loop, bounds it by the call's deadline and cancel, and cancels it when its call ends:

```python
import asyncio
from wasi_python import run_async
from wasi_python.tools import tool

PRICES = {"EUR": 1.08, "GBP": 1.27}

@tool
async def rate(currency: str) -> float:
    """The US dollar price of one unit of a currency."""
    await asyncio.sleep(0)  # your async client's call goes here
    return PRICES[currency]

async def main():
    code = "from host import tools\nprint(tools.rate('EUR'))"
    done = await run_async(["-c", code], tools=[rate])
    return done.stdout                     # b'1.08\n'

asyncio.run(main())
```

Under `run_async`, an async tool runs on the event loop that awaits `run_async`, so objects bound
to that loop, such as your client sessions, work. See [Offer tools to the guest](tools.md) for
more.

A raw `host=` function must stay synchronous; an `async def` is refused. One that must await runs
the coroutine on its own loop with `asyncio.run_coroutine_threadsafe(coro, loop).result(timeout=...)`.
Without a timeout, a closing loop blocks it forever.

## Use trio or another framework

`run_async` is asyncio only. Under trio, call `run(cancel=event)` from a worker thread, and set the
`threading.Event` to stop the guest.

In one line: `await run_async(argv)` runs the guest on a worker thread, cancelling the task stops
the guest, and `async_workers` bounds how many run at once.
