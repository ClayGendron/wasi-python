# Embed from other languages

This guide shows two ways to run sandboxed Python from a program that is not written in Python: call the `wasi-python` command as a subprocess, or load the artifacts in a WebAssembly engine of your own.

The subprocess is the short route. It needs a Python on the machine, with the wheel installed. The engine route needs no Python on the host, but you do four things the runner does for you.

## Call the command as a subprocess

`wasi-python run` runs one program and prints its result as one line of JSON:

```
$ wasi-python run -- -c "print(1)"
{"exit_code": 0, "fuel_used": null, "stderr": "", "stdout": "1\n", "trapped": null, "truncated": []}
```

From TypeScript on Node:

```typescript
import { spawn } from "node:child_process";

const child = spawn("wasi-python", ["run", "--deadline-s", "10", "--", "-c", code]);
let out = "";
child.stdout.on("data", (chunk) => (out += chunk));
child.on("error", (err) => console.error("wasi-python could not start:", err.message));
child.on("close", (status) => {
  if (status === 0) console.log(JSON.parse(out)); // how the program ended
  else if (status === 1) console.error(JSON.parse(out).error); // run() refused or failed
  else console.error(`wasi-python exited ${status}`); // 2: usage error; 130: interrupted
});
```

Any language that can start a process and parse JSON works the same way.

### Read the result

The command's own exit code says whether there is a result, not how the program ended:

| exit code | meaning |
|---|---|
| 0 | A result, on standard output. |
| 1 | `run` refused or failed: `{"error": …, "kind": …}` on standard output. |
| 2 | A usage error, on standard error. |
| 130 | Interrupted with Ctrl-C. |

On a result, the keys are `exit_code`, `trapped`, `fuel_used` and `truncated`, and `stdout` and `stderr` as text. A stream that is not valid UTF-8 comes as `stdout_base64` or `stderr_base64`. A program that exits with code 3 gives `"exit_code": 3` and the command's exit code 0. See [Results and errors](../reference/results-and-errors.md) for every value of `trapped`.

### Pass limits, folders and code

Each option is one of `run`'s arguments: `--deadline-s`, `--memory-bytes`, `--output-bytes`, `--fuel`, `--max-open-files`, `--env`, `--stdin`, `--no-snapshot`, `--grant`, `--grant-writable`, `--import-path`, `--root`, `--private-root` and `--no-root`. Everything after `--` is the program's arguments.

`--env KEY` with no value passes this command's own value for `KEY`, which keeps a secret off the command line.

The guest does not see the host's folders, so read a long program from the host with `--stdin`, and hand the guest its folders with grants:

```
$ wasi-python run --grant /data=./inputs --grant-writable /out=./results --stdin prog.py -- -
```

See the [command-line reference](../reference/cli.md) for every option.

### Two cautions

- The JSON line can be up to six times the program's output, because of JSON escaping. Collect standard output in full. Node's `exec`, for example, stops at 1 MiB by default.
- Put a long program in a file and pass `--stdin prog.py -- -`. A program in `-c` meets the system's limit on argument length.

## Load the artifacts in your own engine

The artifacts are plain `wasm32-wasip1` modules. Any engine that meets the requirements below can run them. Get the files from the wheel (`wasi_python.artifacts()` names them) or from a release; see [Artifacts](../reference/artifacts.md).

### Pick an engine

The binaries use WebAssembly's exception-handling proposal in its standard form (`exnref`, part of WebAssembly 3.0), so C++ exceptions work. They also need multi-value and reference types (WebAssembly 2.0). The project runs only wasmtime 50 itself. The rest of this table is read from each engine's release notes and source:

| status | engines |
|---|---|
| runs by default | wasmtime 47 or later (CLI, Rust, wasmtime-py), or 37 to 46 with `-W exceptions=y`; WasmEdge 0.16 or later (AOT 0.18 or later) |
| runs with a switch | wasmer 6 or later on LLVM or V8, or 7 or later on Cranelift (not Singlepass); wazero 1.12 or later with its experimental opt-in; Node 24.15 or later, or 25 |
| does not run | WAMR, wasmi, wasmer-python, wasmer-go, wasmtime's Winch, and wasmtime built without its `gc` feature |

The plain `wasmtime run` command cannot bind the custom import and refuses the binary. With `-W unknown-imports-default` it runs it, but the door then answers 0 with no response, which guest code reads as an empty answer.

### Do the four things the runner does

1. **Preopen the stdlib zip.** Preopen the folder that holds `python-stdlib.zip`, read-only, at `/usr/local/lib`, with nothing else in it, so the guest finds `/usr/local/lib/python315.zip`. Add whatever folders you grant, possibly none, a folder at `/` included. The snapshot runs only beside the zip it was built against. For matplotlib, extract the zip's member `matplotlib/mpl-data.zip` into a folder of its own and preopen it read-only at `/usr/local/lib/python315.zip/matplotlib/mpl-data`.
2. **Bind the one custom import, the door.** Its signature is `host::call(ptr, len, out_ptr_ptr, out_len_ptr) -> i32`. Answer −1 when there is no host. Otherwise read the request from guest memory, get space from the exported `host_alloc`, write the response, store its pointer and length at the two out-addresses, and answer 0. Answer −2 if the host fails. Frames are opaque bytes: their meaning is yours, or the [tool protocol](../reference/tool-protocol.md)'s.
3. **Call `_initialize`, then `run`.** Call `_initialize` on the plain reactor only. Then call `run` once per instance, with argv (`argv[0]` is `/usr/local/bin/python.wasm`) and the environment given through WASI. `run` returns the exit status.
4. **Give the guest 8 MiB of native stack**, on a thread with room for it. See the next section.

The guest's import path holds only the stdlib zip. If you add entries, add read-only ones only, after the zip.

### Give the guest enough stack

Set the engine's `max_wasm_stack` to 8 MiB. Above 2 MiB, wasmtime also needs `async_stack_size` at least as large, or it refuses the engine. wasmtime-py 50's `Config` has no property for it: call its declared binding first, or wasmtime-py's engine aborts the process on the refusal.

```python
wasmtime._ffi.wasmtime_config_async_stack_size_set(config.ptr(), size)
```

WebAssembly runs on the calling thread's own stack. So make every call into the guest on a thread with 8 MiB plus your own frames. The Python runner gives 10 MiB. A Linux main thread has 8 MiB and a Windows one 2 MB, which is too little: a guest that uses its stack then kills the process.

With wasmtime's default 512 KiB stack instead, recursion through Python code still raises `RecursionError`, but more kinds of deep nesting trap the guest, at much lower depths.

On Linux, install `faulthandler`, and any crash reporter or handler for `SIGSEGV`, `SIGILL` or `SIGFPE`, before your first engine, or not at all. Enabling or disabling one later makes any guest trap kill or hang your process.

### Keep an instance across turns

To keep Python's state between calls, as `wasi_python.Session` does, call the export `turn(ptr, len) -> i32` instead of `run`, once per turn:

- Write the turn's source as UTF-8 into a buffer from `host_alloc`, and pass its address and length. `turn` frees the buffer on every path.
- `turn` returns the exit status (0 to 255), 256 plus it when the turn called `exit()` or `quit()`, or −1 for a refusal, which runs no Python.
- Re-arm fuel and the deadline before each turn. Never call `turn` again after a trap or `proc_exit`. `run` and `turn` exclude each other in one instance.

To end the instance as Python ends, call `shutdown() -> i32` once, at rest, after a turn that returned, under a deadline. It runs `atexit` and finalizes, and returns 0, or 120 when finalization reported an error. Then never call the instance again.

### Start each call from a starting image

A starting image is the snapshot's memory after your own setup code ran: imports, data, functions. Make it once, then copy it into each new instance, so a call pays only for its own work.

1. **Run your setup with `prepare`.** In a fresh snapshot instance that has run nothing, write the code as UTF-8 into a buffer from `host_alloc` and call `prepare(ptr, len) -> i32`. It frees the buffer. It returns the code's exit status, or −1 for a refusal, which runs no Python: on the plain reactor, after `run` or `turn`, or a second time. The instance's argv entries after the first that begin with `/` are on `sys.path` while the setup runs, and are gone after it; a call that imports more from such a folder passes it in its own argv.
2. **Read the memory whole** when it returned 0. Those bytes are the image. Discard an instance whose `prepare` returned anything else: it refuses `prepare`, `run` and `turn`.
3. **Start each call from the image.** Instantiate the snapshot afresh, grow its memory to the image's size, copy the image in, then call `run` or `turn` as usual.

While the setup code runs, the clocks and entropy are pinned: `time.time()` reads 2026-01-01T00:00:00Z, `time.monotonic()` reads 0, and random bytes are zeros. So the code must not make a secret or wait for time to pass. File metadata is real. A call from the image gets its own grants, in any order, its own environment, and fresh randomness. The image works only with the snapshot binary and stdlib zip it was made with.

A call from an image ends without Python's teardown of the modules the image holds. `atexit` handlers run, what the program's own names held is finalized, and every file still open is flushed. An object a program hangs on an imported module is flushed, not finalized, so close what you open, or use `with`.

MANIFEST's `x-snapshot-package` lines name what to import to load every package the set ships, one line per distribution.

### Checkpoint a session

A session's state after its turns can be an image too, as `Session.checkpoint` makes one. In a snapshot instance whose last `turn` returned:

1. **Call `checkpoint(1) -> i32`.** It returns 0, or −1 for a refusal, which changes nothing: on the plain reactor, before a turn returned, after `run`, and while already entered.
2. **Read the memory whole.** Those bytes are the image. Refuse first if the guest holds a file or folder open: a start cannot reopen it.
3. **Call `checkpoint(0)`** on every path after a 0, so the live instance goes on as it was. While entered, `shutdown` and `prepare` refuse.

An instance the image is copied into resumes at its first `run` or `turn`: its import path is the stdlib zip's again, a first turn reads its own argv and environment and reseeds the generators, its monotonic clock never reads below the session's last reading, and it ends as a call from a starting image ends. The image holds every byte the session read.

### What you give up

The protections the Python runner adds are its own, not the artifacts'. An engine you drive yourself gets none of the runner's limits, folder checks or clean-up. The engine the runner pins, wasmtime 50, carries the fixes for a rename with a trailing `/` and for padding in directory listings in its own file calls. An embedder that drives the artifacts with its own wasmtime before 49.0.3 does not get them.

Do not pass a key that begins with `_PYTHON_` in the guest's environment: CPython's `sysconfig` reads these in isolated mode, and `_PYTHON_SYSCONFIGDATA_PATH` runs the module it names.

## In one line

Call `wasi-python run` and parse its one JSON line, or load the artifacts in an engine with exception handling, preopen the zip, bind the door, and give the guest 8 MiB of stack.
