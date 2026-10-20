- **Project:** wasmtime-py (https://github.com/bytecodealliance/wasmtime-py)
- **Against:** 49.0.0 (the release `uv.lock` pins; EXECUTED, `importlib.metadata.version`)
- **Status:** drafted (spec 103, Design, "The debt is documented"; held in step with
  `src/wasi_python/_wasmtime_ffi.py` by the rules check `test_the_private_api_debt_is_documented`)
- **Title:** the public API the runner would use in place of the private bindings it calls
- **Files:** wasmtime/_store.py and _func.py (`Caller` methods, a store identity), _config.py
  (`async_stack_size`), _wasi.py (a locked custom-output table), _func.py (a reusable call, an
  epoch callback), the package's own `__init__` (what is public)
- **Why we need it:** the runner drives wasmtime through one module, the engine seam
  (`src/wasi_python/_wasmtime_ffi.py`, spec 103), which prefers a public form wherever the
  installed release has one and falls back to a private binding otherwise. Every private binding
  it still needs is a row of the table below. When a release makes one public, the adapter takes
  the public path, the name leaves its `NEEDED` or `OPTIONAL` tuple, and the row moves to
  "Landed" in the same change; the check keeps the two lists equal.

**This is a facts sheet, not an issue or a pull request** (question 80). wasmtime-py is a Bytecode
Alliance project, and the Bytecode Alliance AI Tool Use Policy keeps agents from opening pull
requests or commenting (as in `12-wasmtime-py-on-wasmtime-49-0-3/facts.md`). Whether to ask, and
the words, are the owner's. Nothing has been posted.

## The facts

1. **The runner reaches wasmtime-py's private surface in 25 lines of `src/` today** (EXECUTED,
   spec 103's regex over `src/wasi_python/*.py` at `a9064a2`: `runner.py` 14, `mounts.py` 11),
   for six things the public API cannot do: stop a guest from inside a host function without
   raising through the process-wide exception slot (spec 011), answer the epoch callback (spec
   015), own the output table without wasmtime-py's unlocked one (spec 011), forward a file call
   to wasmtime's own WASI fuel-neutrally (specs 032 and 048), set the async stack size (spec 078),
   and read wasmtime's load base for the trap-handler check (spec 071).
2. **What 49.0.0 has publicly** (EXECUTED, `dir()` and `inspect` in the venv): `Store` has
   `get_fuel`, `set_fuel`, `set_epoch_deadline` and `set_limits`; `Caller` has `get` only;
   `Config` has no `async_stack_size`; `WasiConfig.stdout_custom` and `stderr_custom` are setter
   properties; `Func.__call__(store, *params)` accepts a `Caller`; `Engine` has
   `increment_epoch` and no epoch callback; `Store` has no epoch callback; nothing public gives
   the library's path or a symbol's address; `Trap(message)` and `WasmtimeError(message)` build
   Python exceptions, not an owned C error.
3. **The public fuel and deadline methods make the same C calls** (READ, `_store.py:61-90` and
   `:109-115`):
   `Store.get_fuel` is `ffi.wasmtime_context_get_fuel(self._context(), byref(remaining))` and
   raises `WasmtimeError._from_ptr(err)`; `Store.set_fuel` is `ffi.wasmtime_context_set_fuel`
   the same way; `Store.set_epoch_deadline` is `ffi.wasmtime_context_set_epoch_deadline`. A
   `Caller` version of each would be three methods on `Caller` calling the same functions on
   `self._context()`, which `Caller._context()` already gives (READ, `_func.py:171`).
4. **The custom-output properties keep the callable in an unlocked table** (READ,
   `_wasi.py:120-126`: `CUSTOM_OUTPUTS.allocate(callback)`; `_slab.py`: a list and a free index,
   no lock; EXECUTED: no module of wasmtime-py imports `threading`). wasmtime calls the write and
   free callbacks on its own threads, so the runner keeps a locked table of its own (spec 011)
   and registers the two C callbacks itself.
5. **`Func.__call__` allocates per call and hides the trap** (READ, `_func.py:59-116`): it
   builds the `wasmtime_val_t` arrays on every call and turns the trap and error pointers into
   exceptions before the caller sees them. The forwarder (spec 032) calls one of 29 functions
   once per forwarded file call, the hottest path the runner has, and reads fuel before it
   raises; it keeps its own arrays and reads the pointers (`_ffi.wasmtime_func_call`).
6. **The epoch callback has no public form** (EXECUTED, fact 2): the runner registers
   `wasmtime_store_epoch_deadline_callback` with a C callback made from the binding's own
   `argtypes[1]`, and answers it with a `wasmtime_error_new` error it hands to wasmtime (spec
   015).

## The bindings

One row per entry of the adapter's `NEEDED` and `OPTIONAL` tuples; the first cell is the dotted
name as the adapter's holder table spells it. The last column names the sheet the row overlaps.

| binding | C API function | what the runner does with it | public wasmtime-py API that would replace it | in 49.0.0 | overlaps |
|---|---|---|---|---|---|
| `wasmtime._ffi.wasmtime_context_set_epoch_deadline` | `wasmtime_context_set_epoch_deadline` | stops the guest at its next function entry from inside a host function (spec 011, 015) | `Caller.set_epoch_deadline(ticks)` (`Store` has it) | `Store` only | — |
| `wasmtime._ffi.wasmtime_store_epoch_deadline_callback` | `wasmtime_store_epoch_deadline_callback` | registers the epoch callback that decides stop, cancel, deadline or continue (spec 015) | `Store.set_epoch_deadline_callback(fn)` with a Python callback | no | — |
| `wasmtime._ffi.wasmtime_error_new` | `wasmtime_error_new` | the error the epoch callback returns to stop the guest (spec 015) | the same public callback, returning a verdict instead of an owned error | no | — |
| `wasmtime._ffi.wasmtime_error_delete` | `wasmtime_error_delete` | frees an error the judge made and did not hand to wasmtime (one unit row) | the same | no | — |
| `wasmtime._ffi.wasmtime_error_t` | `wasmtime_error_t` (a struct) | the pointer type of an error's address, for freeing one the judge made (ctypes takes no untyped pointer for a typed argument) | the same | no | — |
| `wasmtime._ffi.wasi_config_set_stdout_custom` | `wasi_config_set_stdout_custom` | the guest's stdout, by a key into the runner's own locked table (spec 011) | `WasiConfig.stdout_custom = fn`, once its table is safe for several threads | property, unlocked table | — |
| `wasmtime._ffi.wasi_config_set_stderr_custom` | `wasi_config_set_stderr_custom` | the guest's stderr, the same way | `WasiConfig.stderr_custom = fn`, the same | property, unlocked table | — |
| `wasmtime._ffi.wasmtime_func_call` | `wasmtime_func_call` | forwards a file call to wasmtime's own WASI through the trampoline, fuel-neutrally (specs 032, 048) | a `Func` call that reuses its arrays and gives the trap and error back | `Func.__call__` allocates and raises | — |
| `wasmtime._ffi.wasmtime_context_get_fuel` | `wasmtime_context_get_fuel` | reads fuel before a forward, inside a host function | `Caller.get_fuel()` (`Store` has it) | `Store` only | — |
| `wasmtime._ffi.wasmtime_context_set_fuel` | `wasmtime_context_set_fuel` | grants a forward's allowance and sets it back | `Caller.set_fuel(n)` (`Store` has it) | `Store` only | — |
| `wasmtime._ffi.wasmtime_val_t` | `wasmtime_val_t` (a struct) | the forwarder's argument and result arrays | the same reusable public call | no | — |
| `wasmtime._ffi.WASMTIME_I32` | `WASMTIME_I32` (a kind constant) | marks an `i32` argument | the same | no | — |
| `wasmtime._ffi.WASMTIME_I64` | `WASMTIME_I64` (a kind constant) | marks an `i64` argument | the same | no | — |
| `wasmtime._ffi.wasm_trap_t` | `wasm_trap_t` (a struct) | the forward's trap out-pointer | the same | no | — |
| `wasmtime._ffi.wasmtime_context_t` | `wasmtime_context_t` (a struct) | the type of a store's context pointer, for the prepared call and the epoch callback's raw argument | none needed once the call and the callback are public | no | — |
| `wasmtime._ffi.dll` | the loaded `_libwasmtime` library (ctypes) | the address of one symbol, for the trap-handler check's load base (spec 071) | none needed: a public C symbol's address, read only by `dladdr` | no | — |
| `wasmtime._bindings._wasmtime_store_epoch_deadline_callback` | the binding record of `wasmtime_store_epoch_deadline_callback` | its `argtypes[1]` and `[3]`: the callback's and the finalizer's C types | the public epoch callback | no | — |
| `wasmtime._bindings._wasi_config_set_stdout_custom` | the binding record of `wasi_config_set_stdout_custom` | its `argtypes[1]` and `[3]`: the write's and the free's C types | the public properties with a locked table | no | — |
| `wasmtime._func.LAST_EXCEPTION` | none (wasmtime-py's own slot) | the judge asserts it is `None` after a clean call (spec 011) | none wanted; the slot per thread is sheet 1's ask | — | 1 |
| `wasmtime._func.FUNCTIONS` | none (wasmtime-py's own table) | the judge asserts a call defines no host function (spec 011) | none wanted | — | — |
| `wasmtime._wasi.CUSTOM_OUTPUTS` | none (wasmtime-py's own table) | the judge asserts a call takes no custom output of wasmtime-py's (spec 011) | none wanted; the locked table above | — | — |
| `wasmtime.Trap._from_ptr` | owns a `wasm_trap_t*` | raises the forward's trap as wasmtime-py's own `Trap` | the same public call | no | — |
| `wasmtime.WasmtimeError._from_ptr` | owns a `wasmtime_error_t*` | raises or frees the forward's and the fuel calls' errors | the same | no | — |
| `wasmtime.Caller._context` | `wasmtime_caller_context` | the store's context inside a host function: the identity guard (spec 011), fuel, the deadline, the forward | a public store identity on `Caller`, and the three `Caller` methods | no | — |
| `wasmtime.Store._context` | `wasmtime_store_context` | the call's context address at its opening, for the guard | a public store identity on `Store` | no | — |
| `wasmtime.Store.ptr` | the `wasmtime_store_t*` | registering the epoch callback | the public epoch callback | no | — |
| `wasmtime.Config.ptr` | the `wasm_config_t*` | setting the async stack size | `Config.async_stack_size` | no | 21 |
| `wasmtime.WasiConfig.ptr` | the `wasi_config_t*` | setting the two custom outputs | the public properties with a locked table | no | — |
| `wasmtime.Func._func` | the `wasmtime_func_t` handle | the trampoline's functions, for the forward | the same reusable public call | no | — |
| `wasmtime._ffi.dll.wasm_engine_new` | `wasm_engine_new` (a public C symbol) | the one symbol whose address the load-base read takes | none needed | — | — |
| `wasmtime._ffi.wasmtime_config_async_stack_size_set` (optional) | `wasmtime_config_async_stack_size_set` | the async stack size an 8 MiB wasm stack needs (spec 078); absent, a `RuntimeError` before any engine | `Config.async_stack_size` | no | 21 |

## Landed

None yet. A row moves here, with the release that made it public, when the adapter drops the
name (spec 103, Decision 6, step 6).

## The change, for the owner to write from

Three things, each small, in the order of their worth to the runner:

1. **`Caller.get_fuel`, `Caller.set_fuel`, `Caller.set_epoch_deadline`**, each the `Store`
   method's body on `self._context()` (fact 3). Then the runner's six host-function sites take
   the public path with no change of their own (spec 103, Decision 8).
2. **`Config.async_stack_size`**, as sheet 21 says.
3. **A locked `CUSTOM_OUTPUTS`** (fact 4), or a documented statement that the table is safe
   under wasmtime's output threads; then the two properties serve.

The epoch callback and a reusable `Func` call are larger designs; this sheet records the need,
not a shape.

## When it lands

For each row a release makes public: the adapter already prefers the public form, so the
operation changes little or nothing; the name leaves `NEEDED` or `OPTIONAL`; the row moves to
"Landed" above in the same change, or `test_the_private_api_debt_is_documented` is red; a new
major widens the pin by spec 103's Decision 6.
