# Ctrl-C at a host function's entry: why wasmtime-py cannot fully fix it

Short memo for the owner. Labels: EXECUTED (run here), READ (source read here), INFERRED (reasoned, not run).

## What happens

1. The main thread is in wasm. SIGINT arrives. Python's C-level handler only sets a flag; Python runs the real handler at the next bytecode boundary on the main thread (READ: CPython 3.15 `RESUME` checks the eval breaker; the traceback below points at the `def` line, which is the function's `RESUME`).
2. The next bytecode is the entry of `trampoline`, the ctypes callback for a host function. `default_int_handler` raises `KeyboardInterrupt` there, before the `try` (EXECUTED: `evidence/sigint-before-full-stderr.txt`, `File "…/_func.py", line 188, in trampoline  @ffi.wasmtime_func_callback_t`).
3. ctypes catches it. In `_CallPythonObject` (READ: `Modules/_ctypes/callbacks.c`, 3.15), a `NULL` result goes to `PyErr_FormatUnraisable("Exception ignored while calling ctypes callback function …")`, and the return value is written only `if (restype != &ffi_type_void && result)`. So on an exception **the return slot is never written**.
4. The C caller gets whatever the slot held. EXECUTED (`evidence/ctypes-probe.txt`, 3.12, 3.13 and 3.14): a raising `CFUNCTYPE(c_size_t)` or `CFUNCTYPE(c_void_p)` callback returns the previous call's value, `0x1234`. The restype makes no difference.
5. Wasmtime reads that value as `Option<Box<wasm_trap_t>>` (READ: `crates/c-api/src/func.rs` at v49.0.0, `c_callback_to_rust_fn`: `if let Some(trap) = out { return Err(trap.error); }`). Non-zero garbage becomes a box it moves out of and frees. The process dies: exit 133 (SIGTRAP) in 10 of 10 runs of `sigint_posted.py` on main, and 133, 134 (SIGABRT) or 139 (SIGSEGV) in other runs (EXECUTED: `evidence/sigint-before.txt`, `evidence/sigint-stress-before.txt`, `evidence/new-tests-on-unmodified-main.txt`). A zero would be read as success, with the results never written and the `KeyboardInterrupt` lost (INFERRED).

## Can wasmtime-py fix it without touching signals? No.

- **A different callback restype.** No: ctypes never writes the slot when the callable raises, whatever the restype (READ, EXECUTED above). `void` is no better: Wasmtime still reads the register.
- **A `try` that covers the whole trampoline.** No: the exception is raised by the function's own entry check, before its first instruction. A Python function cannot catch an exception raised at its own entry, and a ctypes callback's outermost callable is always a Python call (INFERRED; I found no C-implemented stdlib callable that would call it and swallow every `BaseException`).
- **Checking for a pending exception in `enter_wasm`.** No: the crash happens inside Wasmtime, before control returns to `enter_wasm`.
- **`sys.unraisablehook`.** No: it could save the exception, but the return slot is still unwritten, so Wasmtime still crashes. It is also a process-wide hook a library should not take.
- **Blocking SIGINT with `pthread_sigmask` around calls.** Rejected: not on Windows, it defers Ctrl-C for the whole call even when host functions run, and children spawned by a host function inherit the blocked mask.

So the boundary that sees the `NULL` result is C code wasmtime-py does not own. Bindings that own that boundary do not have the bug (READ, studied only): pywasm3's host-call path checks `PyObject_CallObject`'s `NULL` result in C and returns a trap (`src/wasm3/_wasm3.c`, `if (!pRets) return raise_into_wasm(runtime);`); wasmer-python maps the `PyErr` from PyO3's `call` to `RuntimeError::user` (`packages/api/src/externals/function.rs`). Neither touches signal handlers. cffi callbacks take an `error=` return value and an `onerror` hook for exactly this case (INFERRED from cffi's documentation, not re-read here).

## The best in-library option, prototyped: a scoped SIGINT handler

`prototype-sigint-deferral.patch` (against main, includes `fix.patch`):

- In both `enter_wasm`s, on the main thread, and only while SIGINT has Python's `default_int_handler`, install a handler that only records the signal; restore the default afterwards if it is still ours.
- `trampoline` and the component `catch_exceptions` raise a recorded signal as `KeyboardInterrupt` as their first statement inside the `try`, so it becomes a trap and reaches the caller.
- If the call ends with the signal still recorded (a guest that never called a host function), `enter_wasm` raises `KeyboardInterrupt` then.
- A nested call, another thread, or an embedder's own handler: untouched.

Results (EXECUTED):

| check | main | prototype |
|---|---|---|
| `sigint_posted.py`, 10 runs | exit 133, 10 of 10 | `KeyboardInterrupt`, 10 of 10 |
| `sigint_stress.py`, 300 SIGINTs at random moments, 3 runs | crashed, 3 of 3 (134, 133, 134) | no crash; 297, 299, 298 caught; handler restored after every call; 0 wrong results |
| new test `test_sigint_at_host_function_entry` | crashes the test process, 3 of 3 | passes, 20 of 20 |
| full suite | 226 passed | 228 passed, mypy clean |
| trivial call, main thread | 5.35 µs | 7.95 µs (+2.6 µs, +49%) |
| trivial call, worker thread | 5.31 µs | 6.02 µs (+0.7 µs) |
| an embedder handler that raises (asyncio-style) | crashes | **still crashes**, 3 of 3 |

The stress runs lost 1–3 signals each: they landed in `Managed.__del__` and were printed as "Exception ignored while calling deallocator". That is ordinary CPython behaviour for a signal during `__del__`, not a crash.

## Why this is not offered as a ready fix

It is sound only for one case: SIGINT, Python's default handler, the main thread. It does not cover:

- an embedder's raising handler (asyncio's on a second Ctrl-C; EXECUTED still crashing);
- any other signal whose handler raises, such as a `SIGALRM` timeout or a `SIGTERM` handler that raises `SystemExit` (INFERRED: same path);
- `PyThreadState_SetAsyncExc` (INFERRED: same path).

And it costs every main-thread call about 2.6 µs, about half again the cost of a trivial call, for two `sigaction`s per call. A library that swaps process-wide signal handlers on its hot path is a design decision for the maintainers, not something to send unasked.

## What I recommend

1. Send `fix.patch` now (`pr.md`). It is unrelated to signals: a component host function that raises `KeyboardInterrupt`, `SystemExit` or any other `BaseException` aborts the process every time, because the component path still catches only `Exception`. #337 fixed the core path only.
2. File an issue for the entry-point case, with this memo's evidence, the two-line ctypes probe and the prototype as one option. Let the maintainers choose between: the scoped handler (opt-in or default); a documented limitation ("call wasm from a worker thread if you need Ctrl-C"); or a native shim.
3. Optionally, a CPython feature request: let a ctypes callback declare the value to return when it raises (as cffi's `error=` does), or zero the slot. Even then, Wasmtime's ownership of the returned trap means a static sentinel cannot be a trap pointer; zero would stop the crash but lose the interrupt (INFERRED).

Our runner keeps its own workaround (spec 011, Decision 3), which is the same idea as the prototype, applied around `run` only.

## One line

ctypes leaves a callback's return value unwritten when the callback raises at its own entry, and Wasmtime reads that garbage as a trap pointer; no code in wasmtime-py can catch that exception, so the only in-library mitigation is swapping the SIGINT handler around calls, which works for the default handler but costs ~2.6 µs per call and leaves other raising handlers crashing.
