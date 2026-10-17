# Keep a host function's exception on the thread that raised it

<!-- Draft for the owner to review and post. Base: main at 280ce73. -->

When a host function raises, the trampoline stores the exception in the
module-global `LAST_EXCEPTION`, returns a trap, and `enter_wasm` re-raises
the stored exception once the call returns. The slot is shared by every
thread. If another thread's call traps in between, that thread raises the
first thread's exception, and the first thread gets a bare `Trap`.

This PR makes the slot thread-local, in `wasmtime/_func.py` and in
`wasmtime/component/_enter.py`. A host function always runs on the thread
that called into wasm, so a thread-local slot holds exactly the exception
its own call needs. Single-threaded behaviour does not change.

This is one piece of #254.

## Reproducer

The script in the linked issue: two threads, each with its own store.
Thread A's host function raises `ValueError`; thread B's module executes
`unreachable`.

On main (280ce73), macOS arm64, Python 3.14.2, libwasmtime 49.0.0, three
runs: 2738, 2636 and 2620 of 20000. With this PR, five runs: 0 each time.

## Tests

`test_host_exception_stays_on_its_thread`, in `tests/test_func.py` and in
`tests/component/test_func.py`. Each one stores an exception in the slot
from a second thread, then makes a trapping call on the main thread, and
checks that the call raises its own `Trap` (or `WasmtimeError`) and that
the second thread still gets its exception back.

The tests set the slot directly. The window between a host function
raising and its caller reading the slot cannot be held open from Python,
and a test that loops until the race happens would be slow and flaky. The
reproducer shows the race end to end.

`uv run pytest`: 228 passed, mypy clean (mypy 1.18.2 and pytest 9.0.1 from
`uv.lock`).

## Notes

- `LAST_EXCEPTION` keeps its name and becomes a `threading.local` with an
  `exn` attribute. It is private, but code outside the package that reads
  `wasmtime._func.LAST_EXCEPTION` directly will now see an object, not
  `None`.
- The annotation is now `Optional[BaseException]`, which is what the
  trampoline stores since #337.
- Free-threaded builds behave the same way: `threading.local` is per
  thread there too.
