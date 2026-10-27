"""The engine seam: the one module of wasi_python that touches wasmtime-py's private
API.

wasmtime-py's private API is every name of its that begins with an underscore or is not in its
documented surface: the binding modules, the store context, the raw function handle, the
from-pointer constructors and the pointer methods. The runner and the mounts drive the engine
through this module's named operations and name none of that themselves; a rules check holds it
(`tests/checks/test_rules.py::test_only_the_engine_seam_touches_wasmtimes_private_api`). Each
operation calls wasmtime-py's public API when the installed release has it and falls back to the
private binding otherwise. This module holds no mutable state: constants, functions
and one class; nothing here is reset at fork or released at exit.

At import, `check` asserts that every private name in `NEEDED` exists, and raises one
`ImportError` naming the wasmtime-py version, the names it lacks and the pin when one does not.
`runner._wasmtime()` imports this module after wasmtime-py itself, so a moved symbol is seen at
the first `run()`, before any engine, store or instance exists.

The debt, one line per private binding, with the public name wanted in its place (the rules
check `test_the_private_api_debt_is_documented` holds this list, the tuples and the debt sheet
equal):

- `wasmtime._ffi.wasmtime_context_set_epoch_deadline` -> `Caller.set_epoch_deadline(ticks)`
- `wasmtime._ffi.wasmtime_store_epoch_deadline_callback` -> a public epoch callback on `Store`
- `wasmtime._ffi.wasmtime_error_new` -> the same callback, returning a verdict, not an error
- `wasmtime._ffi.wasmtime_error_delete` -> the same
- `wasmtime._ffi.wasmtime_error_t` -> the same
- `wasmtime._ffi.wasi_config_set_stdout_custom` -> `WasiConfig.stdout_custom` on a locked table
- `wasmtime._ffi.wasi_config_set_stderr_custom` -> `WasiConfig.stderr_custom` on a locked table
- `wasmtime._ffi.wasmtime_func_call` -> a `Func` call that reuses its arrays and gives back the
  trap and the error
- `wasmtime._ffi.wasmtime_context_get_fuel` -> `Caller.get_fuel()`
- `wasmtime._ffi.wasmtime_context_set_fuel` -> `Caller.set_fuel(fuel)`
- `wasmtime._ffi.wasmtime_val_t` -> the same reusable call
- `wasmtime._ffi.WASMTIME_I32` -> the same
- `wasmtime._ffi.WASMTIME_I64` -> the same
- `wasmtime._ffi.wasm_trap_t` -> the same
- `wasmtime._ffi.wasmtime_context_t` -> none once the call and the callback are public
- `wasmtime._ffi.dll` -> none: a public C symbol's address, read only by `dladdr`
- `wasmtime._bindings._wasmtime_store_epoch_deadline_callback` -> the public epoch callback
- `wasmtime._bindings._wasi_config_set_stdout_custom` -> the public properties on a locked table
- `wasmtime._func.LAST_EXCEPTION` -> none wanted (the judge reads it; sheet 1 asks for the slot
  per thread)
- `wasmtime._func.FUNCTIONS` -> none wanted (the judge reads it)
- `wasmtime._func.FUNCTIONS.handles` -> none wanted (the judge reads it)
- `wasmtime._wasi.CUSTOM_OUTPUTS` -> none wanted (the judge reads it)
- `wasmtime.Trap._from_ptr` -> the same reusable call
- `wasmtime.WasmtimeError._from_ptr` -> the same
- `wasmtime.Caller._context` -> a public store identity on `Caller`, and its three methods
- `wasmtime.Store._context` -> a public store identity on `Store`
- `wasmtime.Store.ptr` -> the public epoch callback
- `wasmtime.Config.ptr` -> `Config.async_stack_size` (sheet 21)
- `wasmtime.WasiConfig.ptr` -> the public properties on a locked table
- `wasmtime.Func._func` -> the same reusable call
- `wasmtime._ffi.dll.wasm_engine_new` -> none needed
- `wasmtime._ffi.wasmtime_config_async_stack_size_set` (optional) -> `Config.async_stack_size`
  (sheet 21)

A wasmtime-py major bump is done here, in one place:

1. Change the range in `pyproject.toml` and `PIN`; `uv sync` (a unit row holds the two equal).
2. `uv run python -c "import wasi_python._wasmtime_ffi"`: the import check names every name that
   moved. Nothing else in the package fails to import, because nothing else names the private
   API.
3. Fix each named operation here. Each operation's docstring says what it must do;
   `tests/unit/test_wasmtime_ffi.py` says what each must do observably.
4. `uv run pytest tests/unit/test_wasmtime_ffi.py tests/checks/test_rules.py`, then the fast tier
   on the frozen set with `tests/harness/sameness.py` against the last accepted record: the same
   verdicts, or the differences named.
5. The bump is its own specification.
6. When a release makes an operation public, the preference order is already public first, so
   often nothing changes in the operation; the private name leaves `NEEDED` or `OPTIONAL`, and
   its row moves from the sheet's table to its "Landed" list in the same change.
7. Re-read one fact no row names: a session's turn gathers its output from a pipe by reading
   what the pipe holds once the guest has returned, which is every byte only because wasmtime
   writes a file output on the guest's own thread (`OutputFile`, `write_all`, in wasmtime-wasi's
   `cli/file.rs`). A release that moved file output onto a worker, as it does a custom output,
   would let a turn's bytes reach the next turn.
"""

from __future__ import annotations

import ctypes
from importlib.metadata import version as _installed
from typing import Any, Protocol, cast

from wasmtime import (
    Caller,
    Config,
    Func,
    Store,
    Trap,
    WasiConfig,
    WasmtimeError,
    _bindings,
    _ffi,
    _func,
    _wasi,
)

__all__ = [
    "ASYNC_STACK_SETTER",
    "Context",
    "EPOCH_CALLBACK",
    "NEEDED",
    "OPTIONAL",
    "OUTPUT_FREE",
    "OUTPUT_WRITE",
    "PIN",
    "PreparedCall",
    "Storelike",
    "check",
    "context_address",
    "context_of",
    "custom_output_table",
    "delete_error",
    "engine_symbol_address",
    "get_fuel",
    "host_function_count",
    "last_exception",
    "missing",
    "new_error",
    "raw_func",
    "set_async_stack",
    "set_custom_outputs",
    "set_epoch_deadline",
    "set_fuel",
    "version",
    "watch_epochs",
]

PIN = "wasmtime>=50,<51"

# The private names this module reads, as (holder, name) pairs: the holder is the dotted name of
# the module or class, as the table given to `check` spells it. `OPTIONAL` is not checked.
NEEDED: tuple[tuple[str, str], ...] = (
    ("wasmtime._ffi", "wasmtime_context_set_epoch_deadline"),
    ("wasmtime._ffi", "wasmtime_store_epoch_deadline_callback"),
    ("wasmtime._ffi", "wasmtime_error_new"),
    ("wasmtime._ffi", "wasmtime_error_delete"),
    ("wasmtime._ffi", "wasmtime_error_t"),
    ("wasmtime._ffi", "wasi_config_set_stdout_custom"),
    ("wasmtime._ffi", "wasi_config_set_stderr_custom"),
    ("wasmtime._ffi", "wasmtime_func_call"),
    ("wasmtime._ffi", "wasmtime_context_get_fuel"),
    ("wasmtime._ffi", "wasmtime_context_set_fuel"),
    ("wasmtime._ffi", "wasmtime_val_t"),
    ("wasmtime._ffi", "WASMTIME_I32"),
    ("wasmtime._ffi", "WASMTIME_I64"),
    ("wasmtime._ffi", "wasm_trap_t"),
    ("wasmtime._ffi", "wasmtime_context_t"),
    ("wasmtime._ffi", "dll"),
    ("wasmtime._bindings", "_wasmtime_store_epoch_deadline_callback"),
    ("wasmtime._bindings", "_wasi_config_set_stdout_custom"),
    ("wasmtime._func", "LAST_EXCEPTION"),
    ("wasmtime._func", "FUNCTIONS"),
    ("wasmtime._func.FUNCTIONS", "handles"),
    ("wasmtime._wasi", "CUSTOM_OUTPUTS"),
    ("wasmtime.Trap", "_from_ptr"),
    ("wasmtime.WasmtimeError", "_from_ptr"),
    ("wasmtime.Caller", "_context"),
    ("wasmtime.Store", "_context"),
    ("wasmtime.Store", "ptr"),
    ("wasmtime.Config", "ptr"),
    ("wasmtime.WasiConfig", "ptr"),
    ("wasmtime.Func", "_func"),
    ("wasmtime._ffi.dll", "wasm_engine_new"),
)
OPTIONAL: tuple[tuple[str, str], ...] = (("wasmtime._ffi", "wasmtime_config_async_stack_size_set"),)

_RECORDS = "wasmtime._bindings"  # its names are binding records, read for their argtypes
_HANDLE = ("wasmtime.Func", "_func")  # an instance attribute, read as a class annotation


def version() -> str:
    """The installed wasmtime-py's version, from its metadata."""
    return _installed("wasmtime")


def _has(holder: object, name: str, where: str) -> bool:
    if (where, name) == _HANDLE:
        return name in getattr(holder, "__annotations__", {})
    if not hasattr(holder, name):
        return False
    if where == _RECORDS:
        return len(getattr(getattr(holder, name), "argtypes", None) or ()) == 4
    return True


def missing(holders: dict[str, object]) -> list[str]:
    """The dotted names of `NEEDED` absent from `holders`, in `NEEDED`'s order; every name of a
    holder that is `None` or not in the table is absent. Pure: reads, never raises."""
    absent = []
    for where, name in NEEDED:
        holder = holders.get(where)
        if holder is None or not _has(holder, name, where):
            absent.append(where + "." + name)
    return absent


def check(holders: dict[str, object]) -> None:
    """One `ImportError` naming the version, every missing name and the pin; else nothing."""
    absent = missing(holders)
    if absent:
        raise ImportError(
            "wasi_python drives wasmtime-py through its private API, and wasmtime-py "
            f"{version()} lacks: {', '.join(absent)}. wasi_python was written against {PIN}; "
            "install a wasmtime-py inside that range, or update wasi_python"
        )


check(
    {
        "wasmtime._ffi": _ffi,
        "wasmtime._bindings": _bindings,
        "wasmtime._func": _func,
        "wasmtime._wasi": _wasi,
        "wasmtime.Trap": Trap,
        "wasmtime.WasmtimeError": WasmtimeError,
        "wasmtime.Caller": Caller,
        "wasmtime.Store": Store,
        "wasmtime.Config": Config,
        "wasmtime.WasiConfig": WasiConfig,
        "wasmtime.Func": Func,
        "wasmtime._ffi.dll": getattr(_ffi, "dll", None),
        "wasmtime._func.FUNCTIONS": getattr(_func, "FUNCTIONS", None),
    }
)

# A store's context pointer: what the C API takes for the store's state.
Context = ctypes.POINTER(_ffi.wasmtime_context_t)


class Storelike(Protocol):
    """What a `Store` and a `Caller` have in common: the store's context."""

    def _context(self) -> Any: ...


def context_of(storelike: Storelike) -> Context:  # type: ignore[valid-type]
    """The store's context pointer, from a `Store` or from the `Caller` of a host function."""
    context: Context = storelike._context()  # type: ignore[valid-type]
    return context


def context_address(storelike: Storelike) -> int:
    """The context's address: the store's identity, which the host functions compare."""
    return ctypes.addressof(storelike._context().contents)


def set_epoch_deadline(storelike: Storelike, ticks: int) -> None:
    """The store's epoch deadline, `ticks` after the engine's current epoch; 0 stops the guest
    at its next function entry. Public on a `Store`; the binding on a `Caller`."""
    public = getattr(storelike, "set_epoch_deadline", None)
    if public is not None:
        public(ticks)
        return
    _ffi.wasmtime_context_set_epoch_deadline(storelike._context(), ticks)


def get_fuel(storelike: Storelike) -> int:
    """The store's fuel; raises `WasmtimeError` on a store that does not meter."""
    public = getattr(storelike, "get_fuel", None)
    if public is not None:
        return cast(int, public())
    fuel = ctypes.c_uint64()
    error = _ffi.wasmtime_context_get_fuel(storelike._context(), ctypes.byref(fuel))
    if error:
        raise WasmtimeError._from_ptr(error)
    return fuel.value


def set_fuel(storelike: Storelike, fuel: int) -> None:
    """Set the store's fuel; never raises (a metered store never refuses, and an unmetered one's
    refusal is dropped, the error freed)."""
    public = getattr(storelike, "set_fuel", None)
    if public is not None:
        try:
            public(fuel)
        except WasmtimeError:
            pass
        return
    error = _ffi.wasmtime_context_set_fuel(storelike._context(), fuel)
    if error:
        WasmtimeError._from_ptr(error)  # owned, so freed


def new_error(text: bytes) -> int:
    """A new error wasmtime owns once it is returned to it (the epoch callback's stop), as its
    address; 0 when none was made. Plain: may raise."""
    error = ctypes.cast(_ffi.wasmtime_error_new(text), ctypes.c_void_p)
    return error.value or 0


def delete_error(address: int) -> None:
    """Free an error from `new_error` that was not handed to wasmtime."""
    _ffi.wasmtime_error_delete(ctypes.cast(address, ctypes.POINTER(_ffi.wasmtime_error_t)))


# The epoch callback's C type (context, data, delta out-pointer, kind out-pointer -> an error's
# address or 0) and its finalizer's, read from the binding's own record.
EPOCH_CALLBACK = _bindings._wasmtime_store_epoch_deadline_callback.argtypes[1]
_EPOCH_FINALIZER = _bindings._wasmtime_store_epoch_deadline_callback.argtypes[3]


def watch_epochs(store: Store, callback: Any) -> None:
    """Give `store` the epoch callback, an `EPOCH_CALLBACK` object the caller keeps alive, with
    no data and a NULL finalizer."""
    _ffi.wasmtime_store_epoch_deadline_callback(store.ptr(), callback, None, _EPOCH_FINALIZER())


# A custom output's write (key, bytes, size -> written) and free (key) C types, from the record.
OUTPUT_WRITE = _bindings._wasi_config_set_stdout_custom.argtypes[1]
OUTPUT_FREE = _bindings._wasi_config_set_stdout_custom.argtypes[3]


def set_custom_outputs(wasi: WasiConfig, write: Any, free: Any, out_key: int, err_key: int) -> None:
    """The guest's stdout and stderr as `write` under `out_key` and `err_key`, freed through
    `free` with the key; the two are `OUTPUT_WRITE` and `OUTPUT_FREE` objects the caller keeps."""
    _ffi.wasi_config_set_stdout_custom(wasi.ptr(), write, out_key, free)
    _ffi.wasi_config_set_stderr_custom(wasi.ptr(), write, err_key, free)


# The binding for the async stack size, or None when wasmtime-py lacks it; looked up here at call
# time, so a test patches this name.
ASYNC_STACK_SETTER = getattr(_ffi, "wasmtime_config_async_stack_size_set", None)


def set_async_stack(cfg: Config, size: int) -> None:
    """wasmtime's async stack size, which must be at least `max_wasm_stack` above 2 MiB, or
    wasmtime refuses the config and wasmtime-py's engine aborts the process.
    Through `Config.async_stack_size` when wasmtime-py has it, else the binding; with neither, a
    RuntimeError before any engine is made."""
    if isinstance(getattr(type(cfg), "async_stack_size", None), property):
        cfg.async_stack_size = size  # type: ignore[attr-defined]  # the stubs lack the property
        return
    if not callable(ASYNC_STACK_SETTER):
        raise RuntimeError(
            f"wasmtime-py {version()} cannot set async_stack_size, which the runner's "
            f"{size >> 20} MiB wasm stack needs"
        )
    ASYNC_STACK_SETTER(cfg.ptr(), size)


def engine_symbol_address() -> int:
    """The address of one public symbol of wasmtime's library, for the load-base read."""
    return ctypes.cast(_ffi.dll.wasm_engine_new, ctypes.c_void_p).value or 0


def raw_func(func: Func) -> Any:
    """The C handle of a `Func`, for a prepared call."""
    return func._func


def last_exception() -> BaseException | None:
    """wasmtime-py's process-wide exception slot (the judge asserts it is None after a call)."""
    return _func.LAST_EXCEPTION


def host_function_count() -> int:
    """How many host functions wasmtime-py's own table holds (the judge asserts a call adds
    none)."""
    return len(_func.FUNCTIONS.handles)


def custom_output_table() -> Any:
    """wasmtime-py's own table of custom outputs, which the runner never uses; the
    judge counts its allocations."""
    return _wasi.CUSTOM_OUTPUTS


class PreparedCall:
    """One function of the trampoline, with its argument array (its kinds set once) and its
    one-slot result array made once and reused per call (one forwarded file call is
    the hottest path the runner has). The trap out-pointer is made per call, since the `Trap`
    takes ownership of what it points to."""

    __slots__ = ("func", "kinds", "params", "results")

    def __init__(self, func: Any, kinds: tuple[str, ...]) -> None:
        self.func = func
        self.kinds = kinds
        self.params = (_ffi.wasmtime_val_t * len(kinds))()
        for i, kind in enumerate(kinds):
            tag = _ffi.WASMTIME_I32 if kind == "i32" else _ffi.WASMTIME_I64
            self.params[i].kind = ctypes.c_ubyte(tag.value)
        self.results = (_ffi.wasmtime_val_t * 1)()

    def call(self, context: Context, args: tuple[int, ...]) -> int:  # type: ignore[valid-type]
        """The function's `i32` answer on `context`; raises its `Trap`, else its `WasmtimeError`
        (when both come back the trap is raised and the error is wrapped so that it is freed).
        Touches no fuel."""
        params = self.params
        for i, (kind, value) in enumerate(zip(self.kinds, args, strict=True)):
            if kind == "i32":
                params[i].of.i32 = value
            else:
                params[i].of.i64 = value
        trap = ctypes.POINTER(_ffi.wasm_trap_t)()
        error = _ffi.wasmtime_func_call(
            context, ctypes.byref(self.func), params, len(args), self.results, 1, ctypes.byref(trap)
        )
        if trap or error:
            raised: BaseException | None = WasmtimeError._from_ptr(error) if error else None
            if trap:
                raised = Trap._from_ptr(trap)  # owns and frees it; an error beside it is freed
            assert raised is not None
            raise raised
        return self.results[0].of.i32
