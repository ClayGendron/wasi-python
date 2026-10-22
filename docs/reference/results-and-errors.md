# Results and errors

This page lists what a call gives back: the fields of its result, the exceptions it can raise,
and the JSON line and exit codes of the `wasi-python run` command. Use it to read how a program
ended and to decide what your code should handle.

Two ideas run through the page. A program that fails *inside* the guest still gives you a
result: its exit code, its output and, if it was stopped, why. Only a problem on the host side,
such as a bad argument or a missing artifact set, raises an exception from `run`.

## The result of a call

`run()`, `run_async()` and `Session.run()` each return a `Completed`, a frozen dataclass.

| field | type | what it holds |
|---|---|---|
| `exit_code` | `int` or `None` | The program's exit status: its return value, or the code it passed to `exit`. It is masked to 0 to 255, as a POSIX process's is. `None` when the program was stopped (see `trapped`). |
| `stdout` | `bytes` | What the guest wrote to standard output, up to the output limit. |
| `stderr` | `bytes` | What the guest wrote to standard error, up to the output limit. |
| `trapped` | `str` or `None` | `None` when the program ended by itself. Otherwise why it was stopped (see below). |
| `fuel_used` | `int` or `None` | The guest's instructions spent, when you gave a `fuel` cap and no deadline hit; else `None`. |
| `truncated` | `tuple[str, ...]` | The streams, `"stdout"` and `"stderr"`, whose output passed the limit. Empty when nothing was cut. |
| `files` | `FileRecord` or `None` | For a call with mounts: its provider calls, faults and refused writes. Else `None`. |
| `tools` | `ToolRecord` or `None` | For a call with tools: every tool-protocol frame counted and the first 1,000 listed. Else `None`. |

For example, the pandas call from the README returns exit code 0 and the sum on standard output:

```python
from wasi_python import run

done = run(["-c", "import pandas as pd; print(pd.Series([1, 2, 3]).sum())"])
done.exit_code, done.stdout        # (0, b'6\n')
```

### `trapped`: why a program was stopped

A *trap* is WebAssembly's word for an error that stops the guest at once. `trapped` names the
reason. Four values are fixed strings, and they are promised:

| value | what stopped the program |
|---|---|
| `"out of fuel"` | It used the `fuel` cap you gave. |
| `"deadline"` | It ran past `deadline_s` seconds of wall-clock time. |
| `"cancelled"` | You set the `cancel` event, or cancelled the `run_async` task. |
| `"out of file calls"` | A call with mounts made more provider calls than `max_file_calls`. |

Any other value comes from wasmtime, the WebAssembly engine that runs the guest. It is a trap's
plain name, such as `"stack overflow"`, `"unreachable"` or `"memory out of bounds"`, or, for an
error with no trap code, the error's first line. These words are not promised: match only the
four fixed strings.

When `trapped` is set, `exit_code` is `None`. Output buffered inside the guest and not yet
flushed is lost, as it is when a native process is killed. Run the program with `-u`, or flush,
if you need every line up to the stop.

`fuel_used` is `None` when a call ran out of file calls. A cap that runs out during the
interpreter's own finalization, after the program's last line, still ends `"out of fuel"`, after
the program's own output was written. See [Fuel](../explanation/fuel.md) for how to size a cap.

### `truncated`: cut output

Each stream keeps at most `output_bytes` bytes (16 MiB by default). The bytes past the limit are
dropped, and the stream's name is added to `truncated`.

### `files`: what a mount's provider did

A `FileRecord` counts a call's provider calls. It holds no times and no exception objects.

| field | what it holds |
|---|---|
| `calls` | Each provider method's count: all eight methods, zeros included. |
| `faults` | The first 1,000 `FileFault`s: provider calls that raised an exception that is not an answer, or answered outside the protocol. Each has `method`, `path` and `error` (the exception's type and first line, or `"bad answer: <type>"`). |
| `refused` | The first 1,000 `RefusedWrite`s: write calls the provider did not accept, or write-backs the runner owed and did not make. |
| `refused_total` | How many writes were refused in all, so you can tell when the list was cut. |

A `RefusedWrite` has `mount` (the mount's guest path), `method`, `paths` (the path, or
`(src, dst)` for a rename), `errno`, `at` (`"open"`, `"call"`, `"close"`, `"sync"` or `"exit"`)
and `cause` (`"refused"`, `"fault"` or `"limit"`).

### `tools`: what the guest asked of your tools

A `ToolRecord` counts every tool-protocol frame of one call. Nothing in it measures time. It comes
back on every ending: an exit, a trap, a deadline or a cancel.

| field | what it holds |
|---|---|
| `frames` | Every frame the guest sent. |
| `outcomes` | The first 1,000 frames, each a `ToolOutcome`. |
| `unlisted` | How many frames are counted but not listed. |
| `abandoned` | Every call answered while its tool still ran, listed or not. |

A `ToolOutcome` has `seq` (from 1), `op` (`"list"`, `"call"`, or `None` when the frame was not
read), `tool`, `outcome` (`"ok"` or one of the protocol's kinds of failure), `message`,
`request_bytes`, `response_bytes`, `fault` (an exception not meant for the guest: its type and
first line) and `abandoned`. The kinds of failure are listed on the
[tool protocol](tool-protocol.md) page.

## Exceptions `run` raises

`run` raises only for problems on the host side. Nothing the guest does, and nothing your own
`host` function, provider, tool or gate returns or raises as an `Exception`, makes `run` raise.
Exceptions are promised by type, never by message.

| exception | when |
|---|---|
| `TypeError` | An argument has the wrong type. Raised before any work. |
| `ValueError` | An argument is out of range, or the guest would see it differently (a NUL, text that is not UTF-8, an `=` or nothing as an environment key). Raised before any work. No message quotes a value. |
| `ArtifactsMissing` | There is no usable artifact set. A subclass of `RuntimeError`; the message says how to get one. |
| `ImportError` | wasmtime-py cannot load. Its own error is chained as the cause. |
| `OSError` | A host file-system call failed while the runner prepared the root, the private folders, the copy of the stdlib zip or the cache. Its subclasses, such as `FileExistsError`, are included. |
| `RuntimeError` | Raised before the guest runs, for one of these: the process was forked after it ran a guest; a folder or the zip's copy changed between the runner's check and its use; on Linux, a signal handler installed or removed after the first call replaced wasmtime's trap handlers; the guest's thread could not start, has too little stack, or its stack cannot be read on this platform; the host is CPython 3.14.0 on a C library other than glibc; or wasmtime-py cannot set its async stack size. |
| `wasmtime.WasmtimeError` | Today, for a folder removed between the runner's check and wasmtime's own open. The type is wasmtime-py's and is not promised. |
| `KeyboardInterrupt` | Ctrl-C. |
| any `BaseException` that is not an `Exception` | Raised by your own host function, provider, tool or gate; it propagates. |

`run_async` raises the same, plus `asyncio.CancelledError` when the awaiting task is cancelled
(the guest is stopped and its worker freed first), and `RuntimeError` when the interpreter is
shutting down.

### Session exceptions

`SessionEnded`, a subclass of `RuntimeError`, means a `Session` has ended and runs no more turns.
`Session.ended` tells you why: `"closed"`, `"idle"`, `"lifetime"`, `"quit"` (a turn called
`exit()` or `quit()`), `"exit"` (a turn called `os._exit`), `"error"` (a turn raised in your
process), or the stopped turn's `trapped`. See [Sessions](../how-to/sessions.md).

### Tool exceptions

On the host side, `wasi_python.tools.ToolError` is what a tool raises to fail with a message the
guest reads, and `ToolDenied` (a subclass) is what a gate raises to refuse a call. Any other
exception reaches the guest only as "(internal error)". On the guest side, each kind of failure
is a subclass of `host.ToolError`; the [tool protocol](tool-protocol.md) page lists them.

## `Errno`: a provider's answers

`Errno` is an `IntEnum` of WASI preview1's error numbers. A mount's provider returns one instead
of a value, and the guest sees it unchanged, as the `OSError` of that errno.

| member | value | member | value | member | value |
|---|---|---|---|---|---|
| `EACCES` | 2 | `EIO` | 29 | `ENOTEMPTY` | 55 |
| `EBUSY` | 10 | `EISDIR` | 31 | `ENOTSUP` | 58 |
| `ECANCELED` | 11 | `ENAMETOOLONG` | 37 | `EPERM` | 63 |
| `EDQUOT` | 19 | `ENOENT` | 44 | `EROFS` | 69 |
| `EEXIST` | 20 | `ENOSPC` | 51 | `ESTALE` | 72 |
| `EFBIG` | 22 | `ENOSYS` | 52 | `ETIMEDOUT` | 73 |
| `EINVAL` | 28 | `ENOTDIR` | 54 | `EXDEV` | 75 |

The set is closed. It holds no success value, nothing that makes the guest's C library retry,
and nothing that describes the guest's own arguments.

The numbers are WASI's, not Linux's. Inside the guest a missing path is `[Errno 44]`, where Linux
says `[Errno 2]`. Compare with `errno.ENOENT` or catch `FileNotFoundError` rather than test a
number.

## The command's JSON line and exit codes

`wasi-python run` prints one line of JSON and sets its own exit code.

```
$ wasi-python run -- -c "print(1)"
{"exit_code": 0, "fuel_used": null, "stderr": "", "stdout": "1\n", "trapped": null, "truncated": []}
```

On a result, the line's keys are `exit_code`, `trapped`, `fuel_used` and `truncated`, as `run`
returns them, and `stdout` and `stderr` as text. A stream that is not valid UTF-8 comes instead
as `stdout_base64` or `stderr_base64`. Output cut at `--output-bytes` in the middle of a
character is not valid UTF-8.

The command's exit code says whether there is a result, not how the program ended:

| exit code | meaning | what is printed |
|---|---|---|
| 0 | A result. | The result line on standard output. |
| 1 | `run` refused or failed. | `{"error": …, "kind": …}` on standard output. |
| 2 | A usage error. | A message on standard error. |
| 130 | Interrupted with Ctrl-C. | |

So a program that exits with code 3 gives `"exit_code": 3` and the command's own exit code 0.

The line can be up to six times the program's output, because of JSON escaping. Read standard
output in full. See [Embed from other languages](../how-to/embed-from-other-languages.md) for an
example, and the [command-line reference](cli.md) for every option.

## In one line

A call returns a `Completed` whose `trapped` says if and why the guest was stopped; it raises only
for host-side problems, and the command reports the same result as one JSON line.
