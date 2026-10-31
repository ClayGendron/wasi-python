# Read output while the guest runs

This guide shows you how to see a guest's output while it runs, how to keep the end of a long output instead of its start, and how to give a session's turn its own standard input.

## Pass on_output

`run`, `run_async`, `Session.run` and `Session.run_async` take `on_output`. It is called with each `OutputChunk` of the guest's stdout and stderr while the guest runs:

```python
from wasi_python import run

def show(chunk):
    print(chunk.stream, chunk.data.decode(errors="replace"), end="")

done = run(["-u", "-c", "import time\nfor i in range(3): print(i); time.sleep(1)"], on_output=show)
```

A chunk has three fields. `stream` is `"stdout"` or `"stderr"`. `data` is the bytes. `cut` is true on the chunk that carries the stream past `output_bytes`.

- **Order.** Within a stream, chunks come in the order the guest wrote them. Across the two streams, they come in the order the runner read them.
- **A chunk is not a line.** Adjacent pieces of one stream are joined, and a line may span two chunks.
- **Every chunk arrives before the call returns.** Joined, a stream's chunks are its `Completed` field, under the default keep.
- **At most `output_bytes` of a stream are delivered.** The piece that passes the limit carries `cut=True`, and nothing more of that stream follows.

## Keep the callback short

Under `run` and `Session.run`, `on_output` runs on the thread that made the call. Your `host` function and your providers run there too. While the callback runs, they wait, and the call cannot return. So hand the bytes to a queue and return.

Under `run_async`, it runs on the event loop's thread, and the loop waits while it runs.

`on_output` must be synchronous. An `async def` raises `TypeError` before any work.

## Know what an exception does

An `Exception` from `on_output` is reported as a `RuntimeWarning` naming it. The callback is not called again for that call. The guest runs on, and the result is whole. So a guest's bytes cannot make `run` raise through a callback that chokes on them.

Any other `BaseException`, such as `KeyboardInterrupt`, stops the call, and the call raises it.

## Iterate with OutputFeed

From async code, an `OutputFeed` gives the chunks as an async iterator. Pass it as `on_output` and read it with `follow`, beside the call's task:

```python
import asyncio
from wasi_python import OutputFeed, run_async

async def main():
    feed = OutputFeed()
    task = asyncio.create_task(run_async(["-u", "script.py"], on_output=feed))
    async for chunk in feed.follow(task):
        print(chunk.stream, chunk.data)
    done = await task
```

`follow` ends once the task is done, whatever its outcome, after the chunks already delivered. A feed serves one call. `run` and `Session.run` refuse one.

## Make the guest write as it goes

CPython buffers stdout when it is not a terminal, so a program's prints may arrive together at its end. stderr is line-buffered already. To get each line as it is printed:

- for a call, pass `-u` in `argv`, or print with `flush=True`;
- in a session, run `sys.stdout.reconfigure(line_buffering=True)` in a turn.

## Keep the end of a long output

Past `output_bytes`, a stream keeps its first bytes by default. Pass `output_keep="tail"` to keep its last bytes instead, where a traceback is:

```python
done = run(["script.py"], output_bytes=4096, output_keep="tail")
```

When bytes were cut, the result starts with a line `[N bytes cut]`, and the rest is the tail, so `stdout` is never longer than `output_bytes`. N counts the bytes past `output_bytes`; the line itself takes the place of the tail's first bytes. Trust `truncated`, not the marker: a guest could print that line itself. The chunks `on_output` gets are still the start of the output. A reader who wants the traceback reads the result.

On the command line, `--output-keep tail` keeps the tail, and `--stream` prints one JSON line per chunk before the result line.

## Give a turn its standard input

`Session.run` and `Session.run_async` take `stdin`, the bytes of that turn's standard input. During the turn, `sys.stdin` reads them as text and `input()` reads their lines; at their end, `input()` raises `EOFError`. The next turn has its own, or none:

```python
from wasi_python import Session

with Session() as s:
    done = s.run("name = input()\nprint('hello', name)", stdin=b"Ada\n")
```

Without `stdin`, a turn reads end of file, as before. A turn's `stdin` is `sys.stdin` alone: `sys.stdin.fileno()` raises, and descriptor 0 stays empty.
