- **Project:** wasmtime-py (https://github.com/bytecodealliance/wasmtime-py)
- **Against:** 49.0.0 (the release `uv.lock` pins), and its `main` at `280ce73` (READ)
- **Status:** drafted
- **Title:** `Config.async_stack_size`, so a `max_wasm_stack` above 2 MiB can be set from Python
- **Files:** wasmtime/_config.py (one setter property; the `max_wasm_stack` docstring's default)
- **Why we need it:** spec 078 gives the guest an 8 MiB wasm stack. wasmtime refuses a
  `max_wasm_stack` above `async_stack_size` (2 MiB by default), and wasmtime-py's `Engine()`
  unwraps that refusal, so the process aborts. The runner sets the async size through
  `wasmtime._ffi.wasmtime_config_async_stack_size_set`, a private module, until a release has the
  property; it prefers the property when present.

**This is a facts sheet, not an issue or a pull request** (question 80). wasmtime-py is a Bytecode
Alliance project, and the Bytecode Alliance AI Tool Use Policy keeps agents from opening pull
requests or commenting (as in `12-wasmtime-py-on-wasmtime-49-0-3/facts.md`). Whether to ask, and
the words, are the owner's. Nothing has been posted.

## The facts

1. **wasmtime refuses the config, and wasmtime-py aborts.** `Config::validate` bails with
   "max_wasm_stack size cannot exceed the async_stack_size" (READ, wasmtime 49.0.3,
   `crates/wasmtime/src/config.rs:2632–2633`). The C API's engine constructor unwraps it (READ,
   `crates/c-api/src/engine.rs:37`), so `wasmtime.Engine(cfg)` ends the Python process with
   SIGABRT, no exception (EXECUTED, `../../research/2026-10-19-the-runners-own-stack/evidence/p1_config.out`:
   exit −6 at 2 MiB + 4 KiB, 8 MiB and 16 MiB).
2. **The C function is already bound.** `wasmtime/_bindings.py` declares
   `wasmtime_config_async_stack_size_set` with `[POINTER(wasm_config_t), c_size_t]` (READ,
   `_bindings.py:3729–3733` at 49.0.0); `Config` has no property that calls it (READ,
   `_config.py`, where `max_wasm_stack` is at 392–408). Calling the binding first makes the engine
   at 8 MiB (EXECUTED, `…/evidence/p1b_binding.out`).
3. **The docstring of `max_wasm_stack` says "This defaults to 2MB".** wasmtime's own default is
   512 KiB (READ, `config.rs:851`; EXECUTED, the same trap depth and fuel with 524,288 set as
   unset, `../../research/2026-10-18-deep-recursion-on-the-wasm-stack.md`, section 1).

## The change, for the owner to write from

A setter property beside `max_wasm_stack`, in the file's own style:

```python
@setter_property
def async_stack_size(self, size: int) -> None:
    """
    Configures the size of the stacks used for asynchronous execution, in bytes. It cannot be
    less than `max_wasm_stack`; raise it first to set `max_wasm_stack` above its 2 MiB default.
    """
    if not isinstance(size, int):
        raise TypeError('expected an int')
    ffi.wasmtime_config_async_stack_size_set(self.ptr(), size)
```

and "This defaults to 512 KiB" in `max_wasm_stack`'s docstring, which might also say that a value
above `async_stack_size` makes `Engine` abort the process. A test: a `Config` with
`async_stack_size = 8 << 20` and `max_wasm_stack = 8 << 20` makes an `Engine`.

## When it lands

When a wasmtime-py release the project pins has the property, spec 078's runner uses it (it
already prefers it), and the fallback to `_ffi` can be removed by a change that says so.
