# What output capture costs

- **Status:** research, 2026-10-24. The attribution of one finding from `2026-10-23-a-rust-runner-against-wasmtime-py-on-speed.md` (§3.2 "stdout"): the product spends about 210 µs more than bare wasmtime-py on each 64 KiB the guest writes to stdout. It changes nothing: no code in `src/`, no pin. Its specification is `../specifications/129-output-is-read-from-a-pipe.md`. Every number is wall-clock on one machine shared with two other agents' work: a benchmark fact, never a check.
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Fable 5.1). Box: one session, the evening after the speed spike.
- **Evidence:** the folder of the same name beside this memo: `driver.py` (every arm, every prototype, monkeypatched from the driver; nothing under `src/` edited), `summarize.py`, `results/*.json` (every run), `results/summary.txt` (the tables below, with every run listed).
- **Stands on:** `src/wasi_python/_call.py` (`_write_output`, `_free_output`, `_send_outputs`, `_Stream`), `src/wasi_python/_wasmtime_ffi.py` (`set_custom_outputs`, `OUTPUT_WRITE`), `src/wasi_python/_process.py` (`outputs`, `outputs_lock`); the prior-art clones, read only: `wasmtime-py` (280ce73, `wasmtime/_wasi.py`, `_bindings.py`) and `wasmtime-v49` (v49.0.3: `crates/c-api/src/wasi.rs`, `crates/wasi/src/p1.rs`, `crates/wasi/src/cli.rs`, `crates/wasi/src/cli/file.rs`, `crates/wasi/src/p2/write_stream.rs`, `crates/wasi-io/src/impls.rs`); spec 011 (the callback tables, which already saw the frees run on wasmtime's tokio threads); spec 006 (the cap).
- **Machine:** darwin-arm64, Apple M1 Pro, 10 cores, 32 GiB, macOS 26.5.2; CPython 3.14.2, wasmtime-py 49.0.0 (wasmtime 49.0.0); the 0.1.0 artifact set (`build/artifacts`), main `2cd47507`. Two other research agents ran builds and benchmarks on the machine throughout, so absolute numbers move between windows by up to 1.6 times; every comparison below is between arms run in one window, one after another.

Labels: EXECUTED means run here; READ means read from a file, cited; INFERRED means the researcher's reasoning.

## The short version

1. **The 210 µs is not one callback. It is sixteen.** wasmtime's preview1 `fd_write` hands a stream its bytes in pieces of at most 4,096 bytes (READ, `p1.rs:306`: "blocking_write_and_flush takes at most one 4k buffer"). 512 guest writes of 64 KiB became **8,192 callbacks of 4,096 bytes** in every run (EXECUTED). A 1 MiB write becomes 256 callbacks. The cost is per 4 KiB, about 14 µs, whatever the guest's write size.
2. **Three parts, none of them the copy.** Per 4 KiB piece, in one window: about **3.4 µs** is wasmtime's own stream worker, paid even when the callback is a C function with no Python in it; about **4.7 µs** is the ctypes crossing onto a thread that has no Python thread state, which Python makes and destroys on every callback; about **2.8 µs** is the Python callback's body (the lock, the lookup, `string_at`, `_Stream.write`). The copies are a fraction of the last part. Together they explain about three quarters of the gap; the rest is the hand-offs between the three threads involved.
3. **Why a foreign thread.** The C API wraps a custom stdout in wasmtime-wasi's `AsyncWriteStream` (READ, `cli.rs:186`), which spawns a worker task on wasmtime-wasi's tokio runtime. The guest thread queues each 4 KiB piece, blocks, and the worker thread calls our Python function. Every callback ran on one of two tokio threads, never on the guest thread, and each one got a fresh Python thread state (EXECUTED: `threading.current_thread()` named a new `Dummy-N` on every callback).
4. **A cheaper Python callback cannot fix it.** Five prototypes (one copy instead of two, a preallocated buffer, the lock dropped) moved the 32 MiB program from 161 to 149 ms at best (EXECUTED). They can touch only the third part.
5. **A pipe fixes it.** wasmtime writes each stream into a pipe the runner opened, through the public `stdout_file` setter with a `/dev/fd/N` path, and one runner thread reads the pipe into the capped stream. No callback, no worker, no foreign thread: the 32 MiB program ran in **36 to 48 ms against 156 to 242 ms** for the product and 35 to 42 ms for the product writing to a plain file, in the same windows; 10,000 writes of 100 bytes ran in **35 ms against 305 ms** (EXECUTED). The cap held exactly at the byte, truncation was named, stdout and stderr interleaved 1,000 times stayed apart, and the host held at most the cap plus the pipe's 64 KiB kernel buffer (EXECUTED, §5). The one platform question is Windows (§6).

## 1. What the product does today (READ)

`_instance` makes two `_Stream` objects and calls `_send_outputs`, which registers them under two fresh keys in `process().outputs` and gives wasmtime one C callback for both streams through the seam (`_wasmtime_ffi.set_custom_outputs`, over `wasi_config_set_stdout_custom` and `wasi_config_set_stderr_custom`). The callback `_write_output(key, data, size)` takes `process().outputs_lock`, looks the key up, copies the bytes once with `ctypes.string_at`, and calls `_Stream.write`, which slices to the room left under the cap (a second copy when truncating), marks `dropped`, extends a `bytearray` (a third copy) and returns `size`, so the guest's write succeeds whatever was kept. At the call's end `Completed.stdout` is `bytes(out.data)` (one more copy of the whole), and `truncated` names each stream whose `dropped` is set. wasmtime calls `_free_output` for each key when it drops the stream; `_instance`'s release pops the keys itself first.

## 2. How wasmtime delivers a write (READ)

- `wasi_config_set_stdout_custom` (`crates/c-api/src/wasi.rs:264`) builds a `CustomOutputStream` that implements `AsyncWrite` by calling the C callback (`raw_write`, `:175`) and gives it to the WASI builder as the stdout `StdoutStream`. It implements only `async_stream`, so it takes the trait's default `p2_stream` (`crates/wasi/src/cli.rs:186`): `AsyncWriteStream::new(8192, ...)`, which spawns a worker task on wasmtime-wasi's runtime (`crates/wasi/src/p2/write_stream.rs:147`, `crate::runtime::spawn`) and hands it each write over a mutex and a `Notify`.
- preview1's `fd_write` on stdout or stderr (`crates/wasi/src/p1.rs:695`) writes through `BlockingMode::Blocking.write` (`:296`), which splits the guest's buffer into pieces of at most 4,096 bytes and awaits `blocking_write_and_flush` for each; `wasi-io` refuses a larger piece (`crates/wasi-io/src/impls.rs:145`). Each piece is a `Vec::from(chunk)` copy, a hand-off to the worker thread, the callback there, a flush, and the wake-up of the guest thread.
- `wasi_config_set_stdout_file` builds an `OutputFile` (`crates/wasi/src/cli/file.rs:16`), which implements `p2_stream` itself, writing with `write_all` on the calling thread. The same 4 KiB loop runs, but each piece is one `write(2)` on the guest thread: no worker, no second thread.
- Spec 011 saw the same worker from the other side: "the custom outputs' frees run on wasmtime's tokio worker threads, because the WASI stdio stream is cloned into an `AsyncWriteStream` task" (its upstream note).

## 3. The reproduction (EXECUTED)

The spike's program (512 writes of 64 KiB through `sys.stdout.buffer`, the cap at 64 MiB), three repeats, medians: product **201.1 ms**, bare wasmtime-py writing stdout to a file **36.0 ms**, bare wasmtime-py with its own public `stdout_custom` callback (`bytes(array)` and `bytearray.extend`) **179.2 ms**. The spike saw 140.4 and 32.9 on a quiet machine; this window was loud. The third arm is the finding in one line: wasmtime-py's own custom callback, with none of the product's bookkeeping, costs almost what the product costs.

## 4. The attribution (EXECUTED)

The program for the rest is `os.write(1, chunk)` in a loop, one `fd_write` per call and no `BufferedWriter` between. Every arm embeds the same wasmtime with the same Config, fuel and epochs on, the module loaded before the timer.

| arm | what it is |
|---|---|
| product | `wasi_python.run`, `output_bytes=64 << 20` |
| product-stamped | the product, its callback replaced from the driver by one that stamps `perf_counter_ns` around the real `_write_output` and records size and thread |
| product-file | the product, `_send_outputs` replaced so wasmtime writes both streams to files in the driver's folder: the product with no callback |
| product-pipe | the product, `_send_outputs` replaced by the pipe design of §5 |
| bare-file | a minimal wasmtime-py embedding, `stdout_file` |
| bare-pipe | the same, `stdout_file = "/dev/fd/N"` on a pipe the driver reads on a thread |
| bare-custom-libc | the same, the custom stdout callback is libc's `write` cast to the callback type, the key the fd of `/dev/null`: wasmtime's custom stream path with no Python in the callback |
| bare-custom-raw | a Python callback that returns `size` and nothing else |
| bare-custom-copy | the same, plus `ctypes.string_at` |
| bare-custom-product-like | the product's callback body, re-made in the driver: lock, lookup, `string_at`, `_Stream.write` |
| bare-custom-pub | wasmtime-py's public `stdout_custom` (its own `Slab`, `bytes(array)`) into a `bytearray` |

### 4.1 The write size does not matter; the number of 4 KiB pieces does

32 MiB in three shapes, the quiet window (`results/sizes.json`, 3 repeats, median ms):

| program | callbacks | product | product-file | bare-file | bare-custom-libc | bare-custom-raw | product-pipe |
|---|---|---|---|---|---|---|---|
| 4 KiB × 8,192 | 8,192 | 178.5 | 47.2 | 39.7 | 69.3 | 110.7 | 40.2 |
| 64 KiB × 512 | 8,192 | 155.6 | 39.9 | 34.9 | 62.4 | 100.5 | 35.9 |
| 1 MiB × 32 | 8,192 | 176.5 | 42.2 | 47.9 | 82.1 | 151.1 | 40.3 |

Every shape made 8,192 callbacks of exactly 4,096 bytes (the stamps' `sizes: [4096]`). The product's time is the same within noise for 8,192 writes and for 32: the cost is per piece, not per guest write, and not per byte beyond the piece. The spike's "210 µs per 64 KiB write" is sixteen pieces at about 13 to 14 µs.

### 4.2 The three parts, per 4 KiB piece

From the 64 KiB × 512 row of the quiet window, and the 5-repeat window of `results/attribute.json` (the machine louder: product 241.8, product-file 41.9, bare-file 35.9):

| part | measured as | quiet window | loud window |
|---|---|---|---|
| wasmtime's stream worker: the `Vec` copy, the mutex and `Notify` hand-off to the tokio thread and back, the flush | bare-custom-libc minus bare-file, over 8,192 | 27.5 ms, **3.4 µs** | 38.2 ms, **4.7 µs** |
| the ctypes crossing onto a thread with no Python thread state | bare-custom-raw minus bare-custom-libc | 38.1 ms, **4.7 µs** | 38.0 ms, **4.6 µs** |
| the Python body: the lock, the lookup, `string_at`, `_Stream.write` | the stamps inside `_write_output` | 23.2 ms, **2.8 µs** | 31.1 ms, **3.8 µs** |
| sum | | 88.8 ms of a 115.7 ms gap (77%) | 107.3 ms of a 199.9 ms gap (54%) |

The gap is product minus product-file (the same runner, the callback the only difference). What the sum leaves is the thread hand-offs the stamps cannot see: the guest thread blocked on a `Notify` while two tokio threads take turns (INFERRED; the stamps saw two OS thread idents in the quiet window and three in the loud one, each holding about half the callbacks), and the ctypes argument conversion outside the stamped body. The loud window inflates exactly those parts, which is what contention would do.

The ctypes floor: a callback of the same type called from a thread that already holds a Python thread state costs **0.61 µs** (EXECUTED, `crossing-floor`: Python calling the C thunk, which calls back). On a thread without one it costs about 4.7 µs: `PyGILState_Ensure` makes a thread state, the body runs, `PyGILState_Release` destroys it. The `Dummy-N` names, a new one on each of the first four callbacks in every run, show the state is fresh each time.

The body's parts, from the loud window's bare arms: `string_at` of 4 KiB, 2.2 µs (custom-copy minus custom-raw: 17.8 ms over 8,192); the lock, the lookup and `_Stream.write`, 3.5 µs more (custom-product-like minus custom-copy: 29.0 ms); wasmtime-py's own public callback, 0.9 µs more again (custom-pub). The copies are two or three microseconds of a 14 to 24 µs piece.

### 4.3 stderr is the same path (EXECUTED)

`os.write(2, 64 KiB)` × 512 (`results/stderr.json`): product 138.1, product-file 39.1, product-pipe 39.2, the one-copy prototype 162.0; 8,192 callbacks of 4,096 bytes, each on a fresh thread state.

### 4.4 Small writes, the common case (EXECUTED)

10,000 writes of 100 bytes, as `print` makes them (`results/small.json`, medians): product **304.5**, product-file 48.5, product-pipe **35.3**, bare-file 40.6, bare-pipe 25.7, bare-custom-libc 96.5, bare-custom-raw 236.6. Per guest write the product pays about 25.6 µs over the file; wasmtime's worker about 5.6 µs of it and the Python crossing and body the rest. The spike's hello (`print('hello')`) pays this once; a program that prints a line per row pays it per line.

### 4.5 The empty call (EXECUTED)

`pass`: product 18.1 ms, product-pipe 18.1 ms, bare-file 10.8 ms. The product's own per-call work is the spike's 7 to 8 ms, and the pipe design adds nothing visible to it: two `os.pipe()` calls and one thread.

## 5. The designs (EXECUTED unless marked)

Each design was a prototype in the driver that replaced `_call._output_write`, `_call._Stream` or `_call._send_outputs` for one run, on the real runner. `results/protos.json`, `results/cap.json`.

### 5.1 A cheaper callback (design a): about 10 ms of 120

64 KiB × 512, one window, medians: product 161.4; one copy into a growing `bytearray` by a ctypes array over the C buffer 148.9; one copy into a `bytearray` preallocated to the cap, by `memmove` 153.8; one copy and the lock dropped 150.9; `memmove` into a zero-grown `bytearray` 159.0; today's two copies with the lock dropped 160.8. The best saves 12 ms, 1.5 µs a piece, out of a gap of about 120 ms. The lock costs nothing measurable. Every one kept the cap exact at the byte and `truncated` named (§5.4), after one bug the first run showed: a prototype that copies the room under the cap rather than `min(room, size)` reads host memory past the buffer into the stream (the cap check must count against the write's own size). Design (a) keeps every promise and gains a tenth of the gap. Rejected on the gain.

A note on the preallocated buffer: the default cap is 16 MiB a stream, so preallocating costs 32 MiB per call, 256 MiB for eight guests at once, for output most calls never write. The growing `bytearray` holds what was written. Rejected on memory as well.

### 5.2 A file wasmtime writes (design b): fast, and the cap is not live

The product with `stdout_file` into the driver's folder: 39.9 ms for 32 MiB, the floor. But with `output_bytes=4096` a guest that wrote 1 MiB left a **1,048,576-byte file** on disk and `truncated` empty (`results/cap.json`, "product-file"). A file cannot stop the guest; the host holds whatever the guest writes until the call ends and the runner reads the file back. It breaks the live cap. Rejected.

### 5.3 A pipe wasmtime writes and the runner reads (design b2): the floor, every promise kept

- `_send_outputs` replaced: `r, w = os.pipe()` for each stream; `wasi.stdout_file = f"/dev/fd/{w}"` (the public setter; wasmtime opens the path at once, `wasi_config_set_stdout_file` calls `create_file` before it returns, READ `wasi.rs:150`); the runner closes its own `w`, so the only write end is wasmtime's; one thread reads both read ends with `select` into the two `_Stream` objects by their unchanged `write`, until each returns EOF. EOF comes when the store closes, which `_instance`'s release does explicitly (`store.close()`), and the stream's `data` and `dropped` wait for the reader before the result is built.
- 32 MiB in 64 KiB writes: **35.9 and 48.3 ms** against the product's 155.6 and 241.8 and product-file's 39.9 and 41.9 in the same windows; the three shapes of §4.1 within 1 ms of product-file each; stderr 39.2 against 138.1; 10,000 small writes 35.3 against 304.5, faster than product-file (a pipe write stays in the kernel's memory; a file write reaches the file system). The empty call unchanged (§4.5).
- Why it is at the floor (INFERRED from §2): `OutputFile` writes on the guest thread, one `write(2)` per 4 KiB piece, about 2 µs; no worker, no second thread, no Python per piece. The reader thread wakes when the pipe has bytes and takes them 64 KiB at a time (the pipe's buffer), about 512 wake-ups for 32 MiB rather than 8,192 callbacks, each on a thread that keeps its Python state.

### 5.4 The promises, on each design (EXECUTED, `results/cap.json`)

A guest writes 1 MiB to stdout then `done\n` to stderr, `output_bytes=4096`:

| design | `stdout` | `stderr` | `truncated` |
|---|---|---|---|
| product today | 4,096 bytes, all `x` | `done\n` | `("stdout",)` |
| each of the five callback prototypes (after the fix of §5.1) | the same | the same | the same |
| pipe (b2) | the same | the same | the same |
| file (b) | 1,048,576 bytes on disk | | `()` |

Interleaved: 1,000 rounds of 7 bytes to stdout and 5 to stderr under the pipe design gave exactly 7,000 and 5,000 bytes, nothing crossed, `truncated` empty.

What the host holds under the pipe design: the stream's `bytearray`, at most the cap, plus the pipe's kernel buffer, 64 KiB on macOS and Linux (INFERRED from the platforms' documented pipe sizes; the reader keeps draining past the cap and drops, so the guest never blocks for long, and a guest past the cap costs the host a `read` per 64 KiB and nothing kept). Today the host holds at most the cap plus one 4 KiB piece in wasmtime's hands. The promise an embedder sees, `len(stdout) <= output_bytes`, is unchanged.

### 5.5 What wasmtime-py's API offers (READ, `_wasi.py`)

`stdout_file`, `stdout_custom`, `inherit_stdout`, and the three for stderr. Nothing else in 49.0.x; the clone is at 280ce73 (2026-09-24). `inherit_stdout` is the process's own fd 1: shared by every call, not an option. `stdout_custom` is the path measured here. `stdout_file` with a pipe's path is the way to a pipe through the public API without a new binding.

### 5.6 Rejected without a prototype (INFERRED)

- **A Python `fd_write` shadow on fds 1 and 2** through the guard linker, as the product shadows `path_open` today: the cap exact, no thread, no platform code. But every `fd_write` of every fd would pass through a Python host function, about 37 to 50 µs a call by the spike's door numbers (§3.2 there): 512 × 64 KiB would cost about 20 ms over the floor, better than today; 10,000 prints would cost about 400 ms, worse than today's 305; and a guest writing files through a grant would pay it on every write it makes. Rejected on the small writes and the files.
- **Running the callback on the guest thread.** It is wasmtime's `AsyncWriteStream` that moves it, below the C API. Nothing in wasmtime-py reaches it.
- **Keeping a Python thread state on the tokio threads.** They are wasmtime's; ctypes makes and destroys the state per callback and offers no hook to keep one.

## 6. Where it stopped

- **Windows.** The pipe design was prototyped on macOS only. `/dev/fd/N` exists on macOS and Linux (Linux's is `/proc/self/fd/N`, which a pipe may be reopened through; INFERRED, not run here). Windows has no path to an anonymous pipe; a named pipe (`\\.\pipe\...`, made with `_winapi.CreateNamedPipe`, as `multiprocessing` makes one) has a path, but whether wasmtime's `File::create` (`CREATE_ALWAYS`, `GENERIC_WRITE`) opens a named pipe's client end is not established here. The specification makes this the builder's first probe and says what Windows does if it fails (it keeps today's callback behind the same seam).
- **Linux** was not run: no Linux host in this session. CI's Linux runners are the check.
- **The unattributed quarter** of the gap (§4.2) is reasoned, not measured: a sample of the three threads during the loop would settle it. It does not change the design, since the pipe removes the threads it would have attributed to.
- **The spawned-thread effect.** `bare-file-on-thread` (the bare arm on a spawned 8 MiB thread, as the product runs its guest) was slower than `bare-file` in both windows (56 against 49; 78 against 36), but the loud windows make it unreliable. Possibly macOS's scheduling of a secondary thread. Not established; a separate question, outside this memo.
- **The prototype's `select.select`** (`_drain` in `driver.py`) refuses a descriptor at or above `FD_SETSIZE`, 1,024 (the pre-build review of the specification, EXECUTED there: a pipe end at descriptor 1,100 raised `ValueError`; `select.poll` took it). The prototype ran in a process with few descriptors; the specification's reader uses `poll`. The driver's own run instructions are in its docstring: from the repository root, with its folders under `build/output-capture-costs/`.
- **One rule slip to record:** the first patch of the driver was applied with a bare `python3` heredoc before the rule was remembered; every later edit and every run went through `uv run --no-sync python`.

## One line

The 210 µs a 64 KiB write costs the product is sixteen 4 KiB pieces, each a hand-off to wasmtime's tokio worker thread plus a ctypes callback that builds and destroys a Python thread state, with the copy a tenth of it; a pipe wasmtime writes through the public `stdout_file` and the runner reads on one thread keeps the cap, the names and the two streams and runs at the file floor, 36 to 48 ms for 32 MiB against 156 to 242.
