# Issue 2: SIGINT at the trampoline's entry aborts the process

Status:
- **The SIGINT case: no sound in-library fix.** See `memo.md`. A prototype (`prototype-sigint-deferral.patch`) works for the default handler on the main thread and is offered as an option for an issue, not as a PR.
- **Found on the way, ready:** component host functions still catch only `Exception`, so any `BaseException` aborts the process deterministically. `fix.patch` and `pr.md`.

Nothing was posted. Base: wasmtime-py main at `280ce73`.

## Files

| file | what |
|---|---|
| `memo.md` | why the SIGINT case cannot be fully fixed in wasmtime-py; options; recommendation |
| `fix.patch` | component `catch_exceptions` catches `BaseException`; test. Applies to main |
| `fix-on-top-of-issue-1.patch` | the same, for a tree that already has issue 1's patch (they touch adjacent lines in `component/_enter.py`, so they conflict otherwise) |
| `pr.md` | PR draft for `fix.patch` |
| `prototype-sigint-deferral.patch` | the scoped SIGINT handler, plus `fix.patch`, plus a deterministic test. Applies to main |
| `scripts/` | probes and stress scripts |
| `evidence/` | outputs |

## Why the process aborts (summary of `memo.md`)

1. SIGINT lands while the main thread is in wasm; Python handles it at the next bytecode boundary, the `RESUME` at `trampoline`'s entry (READ; EXECUTED traceback).
2. `KeyboardInterrupt` escapes the callback; ctypes prints it as unraisable and **never writes the return slot** (READ `callbacks.c`; EXECUTED `scripts/ctypes_probe.py`: a raising callback returns the previous call's value, for both `c_size_t` and `c_void_p`, on 3.12, 3.13 and 3.14).
3. Wasmtime treats the stale non-zero value as a `Box<wasm_trap_t>` and frees it (READ `crates/c-api/src/func.rs`, v49.0.0). The process dies with SIGTRAP, SIGABRT or SIGSEGV (EXECUTED: 133 in 10 of 10 `sigint_posted.py` runs on main; 134/133/134 under the stress script).

## What I tried, and why rejected (detail in `memo.md`)

| idea | verdict | evidence |
|---|---|---|
| a restype whose "unwritten" value is safe | impossible: the slot is never written | READ, EXECUTED |
| widen the `try` | impossible: the raise is at the function's own entry | READ, INFERRED |
| check for a pending exception in `enter_wasm` | too late: the crash is inside Wasmtime | EXECUTED (crash before return) |
| `sys.unraisablehook` | saves the exception, not the return value; process-wide | INFERRED |
| `pthread_sigmask` around calls | no Windows; defers Ctrl-C for the whole call; children inherit the mask | INFERRED |
| scoped SIGINT handler (prototyped) | works for the default handler; +2.6 µs per main-thread call; other raising handlers still crash | EXECUTED |

Prior art (READ only, MIT-licensed, nothing copied): pywasm3 checks the Python call's `NULL` result in C; wasmer-python maps the PyO3 `PyErr` to a Wasmer `RuntimeError`. Neither swaps signal handlers; both own the native boundary that ctypes hides from wasmtime-py.

## Evidence (EXECUTED, macOS arm64, Python 3.14.2, libwasmtime 49.0.0)

- `evidence/sigint-before.txt`: `sigint_posted.py` × 10 on main: exit 133 × 10.
- `evidence/sigint-before-full-stderr.txt`: one run's full stderr.
- `evidence/sigint-prototype.txt`: × 10 on the prototype: `KeyboardInterrupt` × 10, exit 0.
- `evidence/sigint-stress-before.txt`, `evidence/sigint-stress-prototype.txt`, `evidence/stress-run*.log`: 300 random SIGINTs per run.
- `evidence/sigint-own-handler-prototype.txt`: the prototype still crashes under a raising embedder handler (3 of 3).
- `evidence/sigint-test-20-runs-prototype.txt`: the new deterministic test, 20 of 20.
- `evidence/call-cost.txt`: per-call cost, main against the prototype (benchmark fact, best of 5 × 200,000 calls).
- `evidence/ctypes-probe.txt`: the ctypes return-slot probe.
- `evidence/component-base-exception-before.txt`: the component bug on main, exit 134 × 3.
- `evidence/new-tests-on-unmodified-main.txt`: both new tests crash the test process on main.
- `evidence/tests-after-fix.txt`: 227 passed with `fix.patch`.
- `evidence/tests-after-prototype.txt`: 228 passed with the prototype.
- `evidence/tests-issue1-plus-fix.txt`: 229 passed with issue 1's patch plus `fix-on-top-of-issue-1.patch`.

The deterministic test (`test_sigint_at_host_function_entry`, in the prototype): the guest sets a flag in memory and spins; a second thread waits for the flag, calls `signal.raise_signal(SIGINT)` (which trips Python's C-level flag before it returns), then writes the word that lets the guest leave its loop and call the host function. So Python handles the signal exactly at the host function's entry. No timing is involved. INFERRED: on Windows, `raise_signal` from a non-main thread also runs the C handler in that thread, so the test should hold there too; not run.

## Other observations

- One stress run printed `mach_msg failed with 268451845 (10004005)` once (EXECUTED, 1 of 6 runs, no crash). 0x10004005 is `MACH_RCV_INTERRUPTED`; INFERRED to come from Wasmtime's macOS Mach-port trap handler thread receiving the process-directed SIGINT. Not investigated further.
- `test_host_base_exception` uses a fresh `Store` per case: after a trap a component instance cannot be re-entered ("cannot enter component instance"), EXECUTED.

## Licence and process (READ)

Same as issue 1: Apache-2.0 WITH LLVM-exception, no CLA, no DCO, no PR template, no written AI policy. The owner should state in the PR and the issue that an AI agent prepared the patch and the analysis.

## Open risks

- `fix.patch` and issue 1's patch conflict textually; send one, then rebase the other (or use `fix-on-top-of-issue-1.patch`).
- The SIGINT issue stays open upstream; our runner's workaround stays.
- Only macOS was run.

## One line

The Ctrl-C crash comes from ctypes leaving the return value unwritten, so wasmtime-py can only mitigate it (prototype, default handler only, +2.6 µs per call) and the maintainers should choose; meanwhile a deterministic `BaseException` crash in component host functions has a one-line fix ready.
