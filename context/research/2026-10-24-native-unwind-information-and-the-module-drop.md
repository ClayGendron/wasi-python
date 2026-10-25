# Native unwind information and the module drop

- **Status:** research, 2026-10-24. The cause and the fix of one finding from `2026-10-23-a-rust-runner-against-wasmtime-py-on-speed.md` (its §4): dropping the compiled module costs about 4.4 s on macOS. It changes nothing: no code in `src/`, no pin. Its specification is `../specifications/126-native-unwind-information-is-left-out.md`. Every number is wall-clock on one machine: a benchmark fact, never a check.
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Fable 5.1). Box: one session, the morning after the speed spike.
- **Evidence:** in the speed memo's folder, `2026-10-23-a-rust-runner-against-wasmtime-py-on-speed/results/`: `teardown-probes.txt` (every timing below), `teardown-sample.txt` (the stack sample), `cold-job.json` (the probe's job); its `spike/src/main.rs` carries the probe switches (`SPIKE_TIME_DROPS`, `SPIKE_FAST_EXIT`, `SPIKE_DESER_BYTES`, `SPIKE_NO_COW`, `SPIKE_NO_UNWIND`).
- **Stands on:** the prior-art clone `wasmtime-v49` (tag v49.0.3): `crates/wasmtime/src/runtime/vm/sys/unix/unwind.rs`, `crates/wasmtime/src/config.rs`, `crates/c-api/src/config.rs`; the clone `wasmtime-py` (280ce73): `wasmtime/_config.py`; `src/wasi_python/_engines.py`; `tests/harness/guest.py`. Read only; nothing copied.
- **Machine:** darwin-arm64, Apple M1 Pro, 10 cores, 32 GiB, macOS 26.5.2; wasmtime 49.0.0 under wasmtime-py 49.0.0 and under the `wasmtime` crate; the 0.1.0 artifact set (`build/artifacts`), main `2cd47507`.

Labels: EXECUTED means run here; READ means read from a file, cited; INFERRED means the researcher's reasoning.

## The short version

1. **What happens.** Dropping a compiled module of this size costs 4.4 to 5.0 s on macOS, in Rust and in wasmtime-py alike. Every `wasi-python run` pays it at exit: 4.9 s for 0.35 s of work. Every pytest process that compiled or loaded a module pays it at exit, once per module.
2. **Why.** wasmtime emits native unwind information for the compiled code and, on macOS, registers it with the system's libunwind **one entry per function**. `python.wasm` defines **89,060 functions**. libunwind keeps a list, so 89,060 deregistrations walk it 89,060 times. A stack sample during the drop puts every sample in that one libunwind call.
3. **The fix.** `Config::native_unwind_info(false)`, which wasmtime-py exposes as `Config.native_unwind_info`. The drop falls to **2 to 12 ms**. Fuel is **unchanged to the instruction**. The `.cwasm` loses its 10.5 MB `.eh_frame` section and nothing else.
4. **The catch.** A `.cwasm` compiled with the information still carries it and still costs 4.5 s when loaded under an engine that has the option off (EXECUTED, §3). So the module cache's file name must change with the setting, or every existing cache keeps the cost.
5. **The cost.** A native profiler (Instruments, `sample`, `perf`) can no longer attribute time inside wasm frames. wasmtime's own backtraces, trap words and `fuel_used` are untouched. Windows ignores the option (its ABI requires the information).

6. **Overtaken the same day.** The research for the pin move to wasmtime 50 (`2026-10-24-moving-to-wasmtime-50.md`) found the drop at 19.6 ms under wasmtime-py 50.0.1 with the information left on; the lane re-measured 22 ms (EXECUTED). wasmtime 50 fixed the registration upstream. So the pin move removes the cost on its own, and spec 126's remaining value is the 10 MB smaller `.cwasm` and a drop of 2 to 12 ms instead of 22.

## 1. The finding, as the speed memo left it (EXECUTED, 2026-10-23)

The speed spike's fresh-process row: one hello on the snapshot, caches warm, took 4,938 ms in the product and 4,516 ms in the Rust spike, while the work itself took 350 and 57 ms. Timed inside the Rust binary: `drop(modules)` 4,469 and 4,453 ms, `drop(engine)` 0 ms; with `std::process::exit(0)` before the drops, the whole process took 57 ms. Two probes did not find the cause: deserializing from bytes instead of the file (drop 4,445 ms) and compiling with `memory_init_cow(false)` (drop 4,580 ms). The product in a fresh process showed the same gap (in-process 332 to 756 ms, wall 4,799 to 5,332 ms), and so did `wasi-python run -c "print(1)"` (4,911 and 4,971 ms).

## 2. The cause (EXECUTED)

### 2.1 The stack sample

The spike rebuilt unstripped with line tables and sampled during the drop (`sample <pid> 3`): **all 2,409 samples** on the main thread share one chain.

```
main (main.rs:472)
  drop(HashMap<PathBuf, Module>)
    Arc<ModuleInner>::drop_slow
      Arc<MemoryImage>::drop_slow (the Arc chain; not the image itself)
        drop_glue<CodeMemory>
          CodeMemory::drop
            __deregister_frame  (libunwind.dylib)
```

The other threads (wasmtime's trap-handler mach port thread, tokio's two blocking workers) sit in `mach_msg` and `pthread_cond_wait`: idle.

### 2.2 What wasmtime does (READ)

- `unwind.rs` lines 85 to 107: "For libunwind, `__register_frame` takes a pointer to a single FDE." The code walks the module's `.eh_frame` section and calls `__register_frame` once per frame description entry, pushing each pointer on a list; `Drop` (lines 121 to 135) calls `__deregister_frame` once per entry, in reverse. On macOS libunwind is always the unwinder (line 58). On glibc one call registers the whole section (lines 109 to 113).
- Cranelift emits one frame description entry per compiled function (INFERRED from the one-to-one form of `.eh_frame`; not counted here). `python.wasm` and the snapshot each define **89,060 functions** (EXECUTED: the code section's count, read from the binary).
- libunwind's dynamic registrations are a linked list searched on each call, so each deregistration is linear in the entries still registered, and the whole drop is quadratic (INFERRED from the shape; wasmtime's own words, `config.rs` lines 616 to 619, READ: "Some platforms exhibit quadratic behavior when registering/unregistering unwinding information which can greatly slow down the module loading/unloading process").
- The option: `Config::native_unwind_info(bool)`, default on (READ, `config.rs:596-625`). Its doc: it "only exists to help third-party stack capturing mechanisms, such as the system's unwinder or the `backtrace` crate" and "does not affect whether Wasmtime can capture Wasm backtraces". The C API exposes it (`wasmtime_config_native_unwind_info_set`, `c-api/src/config.rs:297`) and wasmtime-py as a property setter (`_config.py:483`, `Config.native_unwind_info = False`).

### 2.3 Why both bindings show it

The registration and the drop happen inside wasmtime's `CodeMemory`, below the C API. wasmtime-py's `Module` and the crate's `Module` hold the same object. So the Python process pays the same 89,060 calls, and the measured gap (about 4.4 s) is the same.

## 3. The fix, measured (EXECUTED)

| | native unwind information on | off |
|---|---|---|
| Rust: `drop(modules)` | 4,453 to 4,580 ms | 7, 2, 2 ms |
| Rust: whole fresh process, one hello | 4,472 to 5,297 ms | 69 ms |
| wasmtime-py: module drop (`del`, `gc.collect()`) | 5,021 ms | 12 ms |
| wasmtime-py: hello's `fuel_used` | 53,519,933 | 53,519,933 |
| `.cwasm` size, snapshot | 298,943,640 B | 288,425,040 B |
| `.cwasm` sections (ELF, EXECUTED) | 14, with `.eh_frame` 10,521,060 B | 13, no `.eh_frame`; every other section the same size (`.text` 190,267,392 B both) |
| compile time, snapshot (one run each, noisy) | 14.6 s | 16.9 s |

**The catch:** the snapshot's `.cwasm` compiled **with** the information, loaded under an engine with the option **off**: it loads (wasmtime's header does not record this setting), load 370 ms, **drop 4,516 ms**. The information lives in the file, and the registration follows the file, not the engine. The runner's cache name is `{digest}-wasmtime{version}-{flavor}.cwasm` (READ, `_engines.py:181`), so without a name change every existing cache keeps the cost until its files are replaced by hand.

Load time with the option off was not measured apart from noise (Rust 33 to 45 ms against 37 to 335 ms; the page cache decides). The registration side costs the same 89,060 calls at every load (INFERRED from the code: `UnwindRegistration::new` runs at publish), so a saving there is expected but unmeasured.

## 4. What it changes

- **For the command line:** `wasi-python run` falls from about 4.9 s to about 0.5 s on macOS for a hello (INFERRED: the run's 0.35 s plus the interpreter's start; the exit then costs milliseconds). The README's "From any language" path, which spawns one per call, becomes usable at that rate.
- **For the judge:** each pytest process compiles or loads up to two modules and drops them at exit; with `-n 6` each worker does. About 9 s per worker process at exit on macOS goes away (INFERRED from two drops of 4.5 s; not measured on a judge run).
- **For embedders:** a long-lived process pays it once at exit today, and nothing after. Memory: the 10.5 MB section is no longer mapped.
- **For Linux and Windows:** glibc registers the section in one call, so Linux likely never had the quadratic drop (INFERRED, untested). Windows requires the information and ignores the option (READ, the doc); its cache name still changes with everyone's, which costs one recompile there for nothing.
- **What is lost:** a native profiler's view inside wasm frames. The product does not use one; the research memos' fuel measurements come from wasmtime's own counters.
- **What is not changed:** `fuel_used`, trap words, wasm backtraces, the artifact set (no guest byte changes), the public API.

## 5. Where it stopped

- Not measured: the registration side's cost at load; a judge run's wall before and after; Linux.
- Not counted: the frame description entries themselves (89,060 functions is the proxy).
- `os._exit` in the command line, suggested on 2026-10-23 before the cause was known, is withdrawn: it would hide the cost at one call site and leave the load-side registrations and every other process's exit as they are.

## One line

wasmtime registers one unwind entry per function with macOS's libunwind and takes them back one by one, 89,060 times for this binary, which is the 4.4 s at every module drop; `native_unwind_info = False` removes it with fuel unchanged, and the module cache's name must change with it, since a cached file keeps the information it was compiled with.
