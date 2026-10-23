# Defaults and limits

This page lists every limit a call has, its default, its unit, and where you set it. A call that names no limit still has one: each limit below applies unless you change it.

A *limit* here is a bound the runner enforces on one guest: memory, time, output, files and tool traffic. The *defaults* are the values a call reads for each limit it does not name.

## The limits

| limit | default | unit | `run()` and `run_async()` | `Session` | command option |
|---|---|---|---|---|---|
| memory | 1 GiB | bytes of linear memory | `memory_bytes=` | `memory_bytes=` (whole session) | `--memory-bytes` |
| deadline | 60 | seconds of wall-clock time | `deadline_s=` | `deadline_s=` (each turn), or per turn | `--deadline-s` |
| output | 16 MiB | bytes kept per stream | `output_bytes=` | `output_bytes=` (each turn), or per turn | `--output-bytes` |
| fuel | none | guest instructions | `fuel=` | `fuel=` (each turn), or per turn | `--fuel` |
| open files | 1,024 | files and folders open at once | `max_open_files=` | `max_open_files=` | `--max-open-files` |
| provider calls | 10,000 | calls to a mount's provider | `max_file_calls=` | `max_file_calls=` (each turn) | not offered |
| tool frames | 1,000 | tool-protocol frames answered | `max_tool_calls=` | `max_tool_calls=` (each turn) | not offered |
| tool request bytes | 16 MiB | bytes of tool requests read | `max_tool_request_bytes=` | `max_tool_request_bytes=` (each turn) | not offered |
| session idle time | 900 | seconds between turns | not offered | `idle_s=` | not offered |
| session lifetime | 3,600 | seconds from the opening | not offered | `lifetime_s=` | not offered |
| session shutdown | 5 | seconds for Python's shutdown | not offered | `shutdown_s=` | not offered |
| `run_async` workers | the CPU count, at most 8 | guests run at once on the runner's pool | not offered (see below) | not offered | not offered |

"Per turn" means `Session.run()` and `Session.run_async()` take `fuel=`, `deadline_s=` and `output_bytes=` of their own, which override the session's for that turn.

## What `None` means

Pass `None` for no limit. For the deadline in a session, `None` means no limit but the session's lifetime. On the command line, every limit option (`--deadline-s`, `--memory-bytes`, `--output-bytes`, `--fuel`, `--max-open-files`) takes the word `none`.

Two exceptions:

- `fuel` has no cap by default. Its default is `None`, and `fuel_used` is then `None` too. A session given a number is *metered*: every turn reports its fuel.
- `shutdown_s` cannot be `None`. Use `0` to skip the shutdown.

`max_open_files=0` refuses every open, the stdlib's included.

## How each limit ends a call

| limit | what happens when it is reached |
|---|---|
| memory | The guest cannot grow its linear memory past it; an allocation that needs more fails inside the guest. |
| deadline | The call ends with `trapped == "deadline"`. The deadline holds while the guest sleeps or waits. |
| output | Bytes past the limit are dropped, and the stream is named in `truncated`. |
| fuel | The call ends with `trapped == "out of fuel"`. |
| open files | The next open answers `EMFILE`, and the guest runs on. |
| provider calls | The call that would pass the limit is not made; the run ends with `trapped == "out of file calls"`. |
| tool frames, tool request bytes | The guest gets `ToolBudgetExceeded` and runs on. |
| session idle time | The session ends `"idle"`. |
| session lifetime | No turn starts at or after it, and each turn's deadline is capped at what is left; then the session ends `"lifetime"`. |
| session shutdown | Past it, the session is simply stopped, and `shutdown_outcome` is `"stopped"`. |

## Rules for the values

The runner checks every limit before any work. A value of the wrong type or out of range raises `TypeError` or `ValueError`, so no value can quietly remove a limit. A negative cap, `True`, or a deadline of 0 are all refused.

- Integer limits take any integer type, numpy's included, from 0 to 2\*\*63 - 1.
- A deadline is a positive real number of seconds. It is counted in ticks of 10 ms, so any positive deadline is at least one tick.
- A cancel stops a computing guest within 5 ticks of 10 ms.

## Limits a mount adds

A call with mounts has three more bounds. Each has a default.

- **Provider calls:** `max_file_calls=`, 10,000 by default. Every provider call counts, whatever it answers.
- **Open files in mounts:** counted with those in grants and the root under `max_open_files`, and at most 1,024 in mounts whatever the cap. The next open answers `EMFILE` without calling the provider. They cost no host file descriptor.
- **Staged bytes:** the bytes of every open file plus every kept listing are at most `memory_bytes` (4 GiB with `memory_bytes=None`). A read that would pass it answers `EFBIG`. A provider should refuse a large file before it reads it: check `stat`'s size first.

See [Mounts](../how-to/mounts.md).

## Limits the tool protocol fixes

These belong to the protocol, not to your settings, and do not change:

- a request is at most 1 MiB, and an answer at most 16 MiB;
- a request nests at most 64 levels;
- checking one frame's arguments takes at most 100,000 steps.

See the [tool protocol](tool-protocol.md).

## Read and change the defaults

`wasi_python.defaults()` returns the `Defaults` in force. `wasi_python.set_defaults(new)` replaces them for calls made afterwards, and returns the previous ones. To change one field, replace it on a copy, as for the size of the `run_async` pool:

```python
import dataclasses

from wasi_python import defaults, set_defaults

set_defaults(dataclasses.replace(defaults(), async_workers=4))
```

The `Defaults` fields are `memory_bytes`, `deadline_s`, `output_bytes`, `async_workers`, `file_calls`, `tool_calls`, `tool_request_bytes`, `open_files`, `session_idle_s`, `session_lifetime_s` and `session_shutdown_s`.

## Your process's own limits

A guest's file descriptors share your process's table. The `max_open_files` cap protects your process only when the process's soft descriptor limit is above the cap plus what the process already holds, for every call and session open at once. macOS starts a process at 256, and many Linux setups at 1,024. Raise the soft limit at start, or set `max_open_files` below it:

```python
import resource  # Linux and macOS; Windows has no resource module

soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
resource.setrlimit(resource.RLIMIT_NOFILE, (hard, hard))
```

The library never changes your process's limits. The `wasi-python run` command raises its own soft limit to its hard limit, since it owns its process.

At the defaults, each running guest may hold 1 GiB of memory, up to 32 MiB of output and a copy of its standard input. So the eight workers of a full `run_async` pool bound one process at about 8.3 GiB, plus the disk a guest writes.

## Hard bounds of the platform

- A guest can use at most 4 GiB of memory, even with `memory_bytes=None`: wasm32's 65,536 pages of linear memory bound every allocation. A request past it raises `MemoryError` or `OSError`.
- The guest runs with 8 MiB of WebAssembly stack, on a thread with 10 MiB. Deep recursion raises `RecursionError`. See the [limitations page](limitations.md).

See [Set limits](../how-to/limits.md) for recipes, and [Fuel](../explanation/fuel.md) for why fuel counts operations rather than time.

## In one line

Every call has a memory, deadline, output and open-file limit by default, plus mount, tool and session bounds where they apply; pass `None` for no limit, and `set_defaults()` to change them all.
