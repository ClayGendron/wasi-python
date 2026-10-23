# Set limits on a call

This guide shows you how to bound what one call may use: memory, wall-clock time, output, instructions and open files. It also shows how to cancel a call and how to read what a limit did.

Every call has limits even when you name none. A call that names no limit gets the defaults.

## Pass a limit

Each limit is a keyword argument of `run`, `run_async` and `Session`:

| argument | what it bounds | default |
|---|---|---|
| `memory_bytes` | the linear memory the guest may hold, in bytes | 1 GiB |
| `deadline_s` | wall-clock seconds for the call | 60 |
| `output_bytes` | bytes kept per stream (`stdout`, `stderr`) | 16 MiB |
| `fuel` | instructions the guest may execute | no cap |
| `max_open_files` | files and folders the guest holds open at once | 1,024 |

Calls with mounts or tools have more limits: `max_file_calls`, `max_tool_calls` and `max_tool_request_bytes`. See [Defaults and limits](../reference/defaults-and-limits.md) for each one.

In Python, pass each limit as a keyword argument to `run`:

```python
from wasi_python import run

code = "print(1)"
done = run(["-c", code], deadline_s=10, memory_bytes=256 << 20, fuel=5_000_000_000)
```

This call has a 10-second deadline, 256 MiB of memory and a cap of five billion instructions.

On the command line, the options are `--memory-bytes`, `--deadline-s`, `--output-bytes`, `--fuel` and `--max-open-files`. This is how a program in another language starts a call with a 10-second deadline:

```typescript
const child = spawn("wasi-python", ["run", "--deadline-s", "10", "--", "-c", code]);
```

## Remove a limit

Pass `None` for no limit. On the command line, every limit option (`--deadline-s`, `--memory-bytes`, `--output-bytes`, `--fuel`, `--max-open-files`) takes the word `none`.

No value can quietly remove a limit. A limit of the wrong type or out of range raises `TypeError` or `ValueError` before any work: a negative cap, `True`, or a deadline of 0. Integer limits take any integer type, numpy's included, from 0 to 2**63 - 1. A deadline is a positive number of seconds, counted in ticks of 10 ms, so any positive deadline is at least one tick.

## Change the defaults

`defaults()` returns the limits in force, as a `Defaults` value. `set_defaults()` replaces them and returns the previous ones. Change one field with `dataclasses.replace`, as here for the size of `run_async`'s worker pool:

```python
import dataclasses

from wasi_python import defaults, set_defaults

set_defaults(dataclasses.replace(defaults(), async_workers=4))
```

## Cap the instructions with fuel

*Fuel* is a count of the instructions the guest executes. Pass `fuel=` to cap it. Past the cap the call ends, `trapped` is `"out of fuel"` and `exit_code` is `None`. With a cap, `fuel_used` reports what the guest spent. Without one, `fuel_used` is `None`.

Fuel counts operations, not time, so a fuel cap does not depend on how fast the machine is or how busy it is. It also counts the interpreter's finalization, after the program's last line: tens of millions of instructions, more after large imports such as pandas. A cap that runs out there ends `"out of fuel"` after the program's own output was written. So size a metered call's `fuel` to cover its finalization too. See [Fuel](../explanation/fuel.md) for how to pick a budget.

## Cap the output

Output past `output_bytes` is dropped, and the stream's name is put in `truncated`. The guest runs on. A call with no truncated output reports an empty `truncated`, as in this command's result:

```
$ wasi-python run -- -c "print(1)"
{"exit_code": 0, "fuel_used": null, "stderr": "", "stdout": "1\n", "trapped": null, "truncated": []}
```

## Cap open files

`max_open_files` counts the files and folders the guest holds open at once, in grants, the root and mounts alike. Past it, an open answers `EMFILE` and the guest runs on. `0` refuses every open, the standard library's included.

A guest's descriptors share your process's descriptor table. So the cap protects your process only when your process's soft descriptor limit is above the cap plus what your process holds, for every call and session open at once. macOS starts a process at 256, and many Linux setups at 1,024. Raise the soft limit when your program starts:

```python
import resource  # Linux and macOS; Windows has no resource module

soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
resource.setrlimit(resource.RLIMIT_NOFILE, (hard, hard))
```

Or set `max_open_files` below your soft limit. The library never changes your process's limits. The `wasi-python run` command raises its own soft limit to its hard limit, since it owns its process.

## Cancel a call

Pass a `threading.Event` as `cancel=` to `run`. Once you set it and the guest runs, the guest stops within 5 ticks of 10 ms while it computes, and `trapped` is `"cancelled"`. From async code, cancel the `run_async` task instead; see [Run the guest from async code](async.md).

## Read what a limit did

`trapped` says why the call was stopped, or `None` when the program ended by itself:

| `trapped` | what stopped the call |
|---|---|
| `"out of fuel"` | the `fuel` cap |
| `"deadline"` | `deadline_s` |
| `"cancelled"` | your `cancel`, or the task's cancellation |
| `"out of file calls"` | `max_file_calls` |
| other text | a trap, such as `"stack overflow"`, or an error's first line |

When `trapped` is set, `exit_code` is `None`. The four fixed strings are promised; the other text is wasmtime's and may change.

`truncated` names the streams that passed `output_bytes`. `EMFILE` inside the guest means it hit `max_open_files`. See [Results and errors](../reference/results-and-errors.md) for every field.

In one line: every call has a memory cap, a deadline, an output cap and an open-file cap by default; add `fuel=` for an exact instruction budget, and `None` removes any of them.
