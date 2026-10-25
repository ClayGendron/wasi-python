# A Rust runner against wasmtime-py on speed

- **Status:** research, 2026-10-23; §4.1 and §4.2 added 2026-10-24 (the teardown's cause and fix). A time-boxed spike at the owner's request ("run a spike to see if a Rust core would be more performant than using wasmtime-py"). It changes nothing: no code in `src/`, no specification, no pin. Its evidence is the folder of the same name beside it. Every number here is wall-clock on one machine: a benchmark fact, never a check (AGENTS.md: tests count operations).
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Fable 5.1). Box: one session.
- **The question:** the guest's instructions are the same under any binding (the 2026-10-18 spike: fuel equal to the instruction). So where could a Rust core be faster at all? Only at the host boundary: starting a run, crossing the door, capturing output, serving file calls, running guests in parallel, and the process's own start and end. This memo measures each.
- **Stands on:** `2026-10-18-a-rust-core-with-js-and-python-wrappers.md` (the assessment) and `2026-10-18-a-rust-runner-spike-against-the-judge.md` (the spike whose Rust source this one extends); `src/wasi_python/{_call,_engines,_wasmtime_ffi}.py`; `tests/harness/guest.py`; the prior-art clone `wasmtime-py` (`_wasi.py`, `_store.py`, `_module.py`, `_ffi.py`), read only.
- **Machine:** darwin-arm64, Apple M1 Pro, 10 cores, 32 GiB, macOS 26.5.2; rustc 1.97.1; the main tree's uv environment (CPython 3.14.2, wasmtime-py 49.0.0); main at `2cd47507`, the 0.1.0 release.
- **Artifact set:** `build/artifacts`, the 0.1.0 set (python 3.15.0, numpy 2.5.2, pandas 3.0.6, scipy, matplotlib and the rest): `python.wasm` 99.4 MB, the snapshot 104.5 MB.

Labels: EXECUTED means run here; READ means read from a file, cited; INFERRED means the researcher's reasoning.

## The short version

1. **On compute, nothing.** A numpy sum takes the same time under Rust and under a bare wasmtime-py embedding (124 against 126 ms). The same Cranelift runs the same code.
2. **At the host boundary, a lot.** A door round trip costs about 1 µs in Rust and 37 µs through wasmtime-py's ctypes callback, 50 µs through the product runner: **35 to 47 times**. Capturing 32 MiB of stdout costs 18 ms in Rust, 33 ms in bare wasmtime-py and 140 ms in the product (its per-write ctypes callback). Eight guests at once on eight threads: bare wasmtime-py scales 4.2 times, Rust 3.0, the product 1.9.
3. **Most of the product's own gap is Python work a Rust core would not do, not wasmtime-py's.** The product spends about 8 ms more than bare wasmtime-py on every run (its scratch folder, HOME, preopen checks, the guest's own thread), 13 µs more per door call (the hand-off to the home thread) and 33 µs per file call under a mount (the Python shadow layer). Those are design costs of the Python runner. A Rust core removes them by construction; a leaner Python runner could remove part of them too.
4. **A finding outside the question: dropping the compiled module costs 4.4 to 5.0 s on this macOS**, in Rust and in wasmtime-py alike. A long-lived embedder pays it once at exit. **The shipped command line pays it on every invocation**: `wasi-python run -c "print(1)"` takes 4.9 s of which about 0.35 s is the run. The cause, found the next day by a stack sample (§4): wasmtime registers one native unwind entry per function with macOS's libunwind, 89,060 for this binary, and deregistering them one by one is quadratic. `Config::native_unwind_info(false)`, which wasmtime-py exposes, brings the drop to 2 to 12 ms, leaves fuel unchanged, and makes the `.cwasm` 10 MB smaller. That is a one-line change to the runner's engine config plus a cache-key change, for the owner to confirm as a specification.

**Answer:** a Rust core is not faster at running Python. It is much faster at everything around it that the embedder's code touches per call: tools, providers, output, and concurrency. For an agent framework that makes many short runs with tools, that is the part that matters.

## 1. What was measured, and how

### 1.1 Three arms on one wasmtime (EXECUTED)

All three embed **wasmtime 49.0.0**, the version wasmtime-py 49.0.0 carries, with the same Config: fuel on, epoch interruption on, the deferred reference-counting collector (so the Rust side's `.cwasm` is byte-identical to wasmtime-py's; the 2026-10-18 spike, §3.1). Each arm gives the guest the stdlib zip read-only at `/usr/local/lib`, no root, a 1 GiB memory cap, a 60 s deadline, a fuel budget of 10^12, and the same two environment variables.

| arm | what it is | its timer covers |
|---|---|---|
| **product** | `wasi_python.run`, the shipped runner on wasmtime-py, `.cwasm` cache warm | the call, from Python to Python |
| **bare** | a minimal wasmtime-py embedding written in the driver (`bench.py`), about 60 lines: Store, WasiConfig, Linker, one door function, stdout to a file | from `Store()` to the guest's return, on the calling thread |
| **rust** | the 2026-10-18 spike's binary, extended with an echo door and a threaded batch (`spike/src/main.rs`, 480 lines), driven over JSON in one process per batch | `run_ms`: instantiate and run; `batch/job`: the whole job, with its store, its WASI context, its ticker thread and the write of its stdout to a file, which is the fair column against the Python arms |

The bare arm is the control that separates **wasmtime-py's cost** (bare against rust) from **the product runner's own cost** (product against bare). The modules are loaded once per process in every arm before the timers start.

### 1.2 The programs (EXECUTED; `bench.py`)

- `hello`: `print('hello')`, on the snapshot and on the plain binary.
- `numpy-sum`: `import numpy as np; print(np.arange(10**6).sum())`, on the snapshot: compute, with a package import.
- `door-echo`: 20,000 calls of 64 bytes, and 500 calls of 1 MiB, through `_host.call`, a host that answers each frame with its own bytes. The product's host is `host=lambda b: b`; the bare arm's door is the judge driver's (`guest.py`'s `Turns`), a Python function on wasmtime-py's `Caller`; the Rust door reads the frame, calls the guest's `host_alloc` and writes the answer back.
- `stdout-32MiB`: 512 writes of 64 KiB to `sys.stdout.buffer`. The product's cap raised to 64 MiB.
- `files-grant`: 20,000 `os.stat` and 2,000 open-and-read of 4 KiB files in a read-only grant (a preopen in the other arms).
- `files-mount`: the same program under a `Mount` with an in-memory `FileProvider`, product only: the Python shadow layer's cost per call.
- `parallel-8`: eight hellos at once on eight threads (a `ThreadPoolExecutor` in the Python arms; `threads: 8` in the Rust batch), against eight in sequence.
- `cold-process`: a fresh process that runs one hello, caches warm.

## 2. The numbers

Per-run wall, **median** in ms (minimum in parentheses). Raw rows: `results/benchmarks.json`; the log of each run: `logs/`.

| program | runs | product | bare wasmtime-py | rust `batch/job` | rust `run_ms` |
|---|---|---|---|---|---|
| hello, snapshot | 20 | 20.2 (18.4) | 12.5 (12.4) | 14.5 | 10.3 (10.1) |
| hello, plain binary | 10 | 41.7 (40.7) | 34.0 (33.3) | 37.1 | 32.4 (32.1) |
| numpy sum, snapshot | 5 | 147.6 (146.3) | 126.0 (123.1) | 137.2 | 124.1 (121.9) |
| door echo, 20,000 × 64 B | 3 | 1,009.3 (1,007.1) | 735.0 (733.8) | 28.9 | 21.3 (21.2) |
| door echo, 500 × 1 MiB | 3 | 125.6 (125.2) | 106.8 (106.7) | 69.3 | 62.0 (61.3) |
| stdout, 32 MiB in 64 KiB writes | 3 | 140.4 (133.3) | 32.9 (32.7) | 33.2 | 18.3 (17.7) |
| files on a grant, 20,000 stat + 2,000 read | 3 | 504.8 (504.0) | 387.2 (383.6) | 425.9 | 418.3 (414.5) |
| files under a Python mount (product only) | 3 | 1,226.4 (1,209.7) | | | |

Eight hellos, snapshot, wall of all eight in ms (median of 3):

| arm | in sequence | on 8 threads | speedup |
|---|---|---|---|
| product | 140.8 | 73.3 | 1.92 |
| bare wasmtime-py | 92.2 | 22.1 | 4.18 |
| rust (`batch_ms`) | 112.7 | 37.8 | 2.99 |

A fresh process, one hello, caches warm (median of 5; `results/teardown-probes.txt` for the breakdown):

| | product (`uv run python`) | rust |
|---|---|---|
| process wall | 4,938 | 4,516 |
| of which, to the result | about 350 (interpreter and uv about 28; `import wasi_python` 31 to 49; the first run 310 to 723) | 57 with the drops skipped (module load 37 to 335; run 10 to 40) |
| of which, dropping the module at exit | about 4,400 (INFERRED from wall minus in-process) | 4,425 to 4,580 (EXECUTED, timed in the binary) |
| peak RSS | 288 MiB | 219 MiB |

## 3. What the numbers say

### 3.1 Compute: equal (EXECUTED)

numpy sum: bare 126.0, rust 124.1 (`run_ms`), 137.2 with the job's own setup. The 2026-10-18 spike showed fuel equal to the instruction; this shows the time equal too. Nothing about Rust makes the guest faster, and nothing about wasmtime-py makes it slower. The product's 147.6 is its own 8 ms of per-run work on top (§3.3) plus about 13 ms more the import pays under it (INFERRED: the gap grows from 8 ms on hello to 22 ms here; the likeliest cause is the product's guard linker on the stdlib zip's reads, not measured apart).

### 3.2 The host boundary: Rust by a wide margin (EXECUTED)

- **Door, small frames.** 20,000 round trips: rust 21.3 ms, so at most **1.1 µs** a call with the guest's own loop inside it; bare **36.8 µs**; product **50.5 µs**. wasmtime-py's cost is the ctypes path: a C-to-Python callback, `memory.read` and two `memory.write` calls, and a `host_alloc` call back into the guest, each a ctypes crossing with argument conversion. The product adds about 13.7 µs a call on top: spec 078's hand-off of the host function to the runner's home thread (its memo measured 7 to 8 µs) and the door frame's address checks.
- **Door, 1 MiB frames.** rust 62.0, bare 106.8, product 125.6 ms for 500 MiB in and 500 MiB out. The per-call overhead is amortized; the rest is copies. Python copies each frame at least twice (`bytes(memory.read(...))`, then `memory.write`), Rust once each way.
- **stdout.** 512 writes of 64 KiB: rust 18.3 (the `MemoryOutputPipe`, plus writing the 32 MiB to a file in `batch/job`, 33.2), bare 32.9 (wasmtime's own `stdout_file`), product 140.4. The product's output capture is a ctypes callback per write (`_output_write`, `_call.py:1038`) into a Python `_Stream` that enforces the cap: about **210 µs a write** over bare. For a guest that prints a lot this is the largest single cost the Python runner adds.
- **File calls on a grant.** bare 387, rust 418, product 505. Here both the bare arm and Rust run wasmtime's own WASI, and Rust is **8 percent slower**, not faster. Unexplained; within what two builds of the same crate behind different feature sets might do (INFERRED; not probed). The product's extra 118 ms is 5.4 µs a call: its guard linker, which shadows `fd_readdir` and `path_rename` and forwards the rest (spec 048).
- **File calls under a Python mount.** 1,226 ms against 505 on a grant: the Python shadow layer costs **33 µs a call** (22,000 calls). This is the ceiling of what a Rust mounts layer could save per call; a Rust core calling a Python `FileProvider` would still pay one Python call per operation, a few µs under PyO3 (INFERRED; not measured).

### 3.3 The product's own cost (EXECUTED, product minus bare)

| where | product over bare | what it is (READ, `_call.py`) |
|---|---|---|
| every run | about 8 ms | the private scratch folder and HOME folder, the preopen identity check through a WAT module, the import-path judge, a thread of its own with an 8 MiB stack, the epoch ticker, the `.cwasm` cache's stamp checks |
| every door call | about 14 µs | the hand-off to the home thread (spec 078), the frame's bounds checks |
| every 64 KiB write | about 210 µs | the output callback and the `_Stream` cap |
| every file call on a grant | about 5 µs | the guard linker's forwarders |
| every file call under a mount | about 33 µs | the Python shadow layer: descriptor table, path walk, provider bridge |

None of this is wasmtime-py's. It is what the Python runner does to be safe by default and to make its promises (spec 011's shared-nothing, 048's guard, 078's own stack). A Rust core would do the same work in Rust at a small fraction of these costs; part of it could also be trimmed in Python (the output callback could batch; the hand-off could be skipped when the caller is already on the home thread). That is a design choice, not a measurement.

### 3.4 Parallel runs (EXECUTED)

Bare wasmtime-py scales best (4.18 on 8 threads): wasmtime-py loads its library with `cdll.LoadLibrary` (READ, `_ffi.py:38`), so ctypes releases the GIL while the guest runs; eight guests run truly in parallel, and the GIL is taken back only for host callbacks. Rust reached 2.99 in this spike: each job spawns its own ticker thread and the eight stores instantiate their memory images at once, which contend in the kernel (INFERRED; the spike was not tuned). The product reached 1.92: it serializes more of its per-run work (its locks, its home thread, the stack-size lock around each thread start). For throughput of short runs, the Rust side's ceiling is higher than this spike shows and the product's is lower than wasmtime-py's; the reason is again the runner's design, not the binding.

### 3.5 The fresh process (EXECUTED)

To the result, Rust is about six times faster (57 ms against about 350): no interpreter, no 35 ms import, and the module's first load is 37 to 335 ms in both (the page cache decides). Peak RSS 219 against 288 MiB. Then both wait **about 4.4 s for the module to drop** (§4). That dwarfs everything else in a fresh process, and it is not the binding's.

## 4. The teardown finding (EXECUTED)

In the Rust binary, timed around the drops with `SPIKE_TIME_DROPS=1`:

- `drop(modules)`: **4,469 and 4,453 ms**; `drop(engine)`: 0 ms. The process then exits.
- `SPIKE_FAST_EXIT=1` (`std::process::exit(0)` after the result is printed): the whole process takes **57 ms**.
- Deserialized from bytes instead of the file (`Module::deserialize`): drop 4,445 and 4,433 ms. Not the file mapping.
- Compiled and loaded with `memory_init_cow(false)` (a second `.cwasm`, 291 MB): drop 4,580 and 4,491 ms. Not the copy-on-write memory image.
- The product in a fresh process: in-process 332 to 756 ms, wall 4,799 to 5,332 ms; `wasi-python run -c "print(1)"` with caches warm: 4,911 and 4,971 ms (and 14,133 ms the first time, which may be uv's own check or the page cache).

### 4.1 The cause (EXECUTED, 2026-10-24)

A stack sample of the unstripped binary during the drop (`sample <pid> 3`; `results/teardown-sample.txt`) puts **all 2,409 samples** in one frame chain: `drop(modules)` → `Arc<ModuleInner>::drop_slow` → `CodeMemory::drop` → **`__deregister_frame` in `libunwind.dylib`**.

- wasmtime emits native unwind information (`.eh_frame`) for the compiled code so a system unwinder or a profiler can walk through wasm frames. On macOS it hands libunwind **one frame description entry per function** (READ, `crates/wasmtime/src/runtime/vm/sys/unix/unwind.rs`: "For libunwind, `__register_frame` takes a pointer to a single FDE"; on glibc one call registers the whole section) and deregisters them one by one at drop.
- `python.wasm` and the snapshot each define **89,060 functions** (EXECUTED, the code section's count). libunwind keeps its registrations in a list, so 89,060 deregistrations walk it 89,060 times. wasmtime's own documentation names this: "Some platforms exhibit quadratic behavior when registering/unregistering unwinding information" (READ, `Config::native_unwind_info`).
- The option is `Config::native_unwind_info(false)`. Its doc says it "does not affect whether Wasmtime can capture Wasm backtraces": wasm backtraces come from wasmtime's own frame tables. It only loses native profilers and the system unwinder the ability to see through wasm frames, which nothing in the product uses. Windows ignores it (its ABI requires the information).
- **Measured** (`results/teardown-probes.txt`): Rust with the option off, snapshot recompiled: drop 7, 2 and 2 ms; the whole fresh process 69 ms (was 4,472 to 5,297). wasmtime-py with `cfg.native_unwind_info = False` (READ, `_config.py:483`, the C API's `wasmtime_config_native_unwind_info_set`): drop **12 ms** against **5,021 ms** with it on; hello's fuel **53,519,933 on both**; the `.cwasm` 288,425,040 B against 298,943,640 B.

### 4.2 What it means

- A long-lived embedder pays it once, at exit, if at all. **The shipped command line pays it on every invocation**, 4.9 s for 0.35 s of work; the README's "From any language" path spawns one per call. Every pytest process that loaded a module pays it once at exit.
- Registration is paid too, at every load: the same 89,060 calls into libunwind, inside the 37 to 335 ms module load. The option removes both.
- **The fix is one line in the runner's engine config**, `native_unwind_info = False`, with the `.cwasm` cache key changed so a cached module compiled with the old setting is not reused (the header would refuse it anyway, as the collector mismatch showed in the 2026-10-18 spike, but a fresh compile on first use of a release is what users would see). The judge's driver (`tests/harness/guest.py`) should carry the same setting so its fuel stays the product's; fuel does not move, so the ratchet does not. It is a parallel-safe specification touching `src/` and the judge, for the owner to confirm: drafted as `../specifications/126-native-unwind-information-is-left-out.md`, on its own memo, `2026-10-24-native-unwind-information-and-the-module-drop.md`. `os._exit` in the CLI is no longer the right fix: it would hide the cost at one call site and keep paying the registration at every load.

## 5. What this does and does not settle

- **Settled:** a Rust core gives no speed on the guest's own work; it gives 35 to 47 times on door round trips, 2 to 8 times on output capture, and a higher ceiling on concurrent short runs. These are the costs of the tool protocol, providers and output, the parts the agent-code use case touches most (`2026-10-17-the-runtime-for-agent-code.md`).
- **Settled:** about half of the product's gap to bare wasmtime-py is the Python runner's own design, not the binding. A Rust core would remove it by construction; the Python runner could trim part of it.
- **Not settled:** the 8 percent on file calls where Rust was slower; the Rust side's true parallel ceiling (untuned); Linux and Windows, where nothing here was run (glibc registers the unwind section in one call, so Linux likely never had the 4.4 s; Windows cannot turn the option off).
- **Not measured:** the tool protocol's full path (schema, gate, JSON frames) in either language; a PyO3 or napi-rs binding's own call cost; sessions.

## 6. What it changes in the recommendation on record

Nothing in the verdicts: the assessment's "adopt in part" and the 2026-10-18 spike's "fuel equal" stand. It adds one argument for the end state the owner named (question 96, one core shared by Python and JavaScript): **the Python runner's per-call costs at the host boundary are 35 to 47 times a Rust core's, and the parts of the product that pay them are the parts the agent use case leans on.** And it adds one item that is urgent regardless and independent of any Rust work: turn native unwind information off in the runner's engine config, which takes 4.4 s off every command-line invocation and 10 MB off every cached module.

## One line

A Rust core runs Python no faster than wasmtime-py (the same Cranelift, the same instructions), but it crosses the host boundary 35 to 47 times faster per door call and 2 to 8 times faster per output write, and wasmtime's per-function unwind registration with macOS's libunwind makes every `wasi-python run` invocation take 4.9 s for 0.35 s of work in either language, which `native_unwind_info = False` cuts to milliseconds with fuel unchanged.
