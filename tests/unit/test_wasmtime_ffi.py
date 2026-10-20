"""The engine seam (spec 102): the one test file that may import wasmtime-py's private modules.
Rows U1 to U10 and U18 need no wasm module; U11 to U16 drive wasmtime-py with a WAT module and
need no python.wasm. Nothing here measures time."""

from __future__ import annotations

import ctypes
import gc
import importlib.metadata
import re
import subprocess
import sys
import tomllib
from types import SimpleNamespace

import pytest
import wasmtime as wt
from wasmtime import _bindings, _ffi, _func, _wasi

from harness import paths
from wasi_python import _wasmtime_ffi as ffi
from wasi_python import runner

# Decision 1's table: every name the adapter exposes, in the table's order.
TABLE = (
    "PIN",
    "version",
    "Context",
    "context_of",
    "context_address",
    "set_epoch_deadline",
    "get_fuel",
    "set_fuel",
    "new_error",
    "delete_error",
    "EPOCH_CALLBACK",
    "watch_epochs",
    "OUTPUT_WRITE",
    "OUTPUT_FREE",
    "set_custom_outputs",
    "ASYNC_STACK_SETTER",
    "set_async_stack",
    "engine_symbol_address",
    "raw_func",
    "PreparedCall",
    "last_exception",
    "host_function_count",
    "custom_output_table",
    "Storelike",
    "NEEDED",
    "OPTIONAL",
    "missing",
    "check",
)


def real_holders() -> dict[str, object]:
    """Decision 2's holder table, built from the installed wasmtime-py."""
    return {
        "wasmtime._ffi": _ffi,
        "wasmtime._bindings": _bindings,
        "wasmtime._func": _func,
        "wasmtime._wasi": _wasi,
        "wasmtime.Trap": wt.Trap,
        "wasmtime.WasmtimeError": wt.WasmtimeError,
        "wasmtime.Caller": wt.Caller,
        "wasmtime.Store": wt.Store,
        "wasmtime.Config": wt.Config,
        "wasmtime.WasiConfig": wt.WasiConfig,
        "wasmtime.Func": wt.Func,
        "wasmtime._ffi.dll": getattr(_ffi, "dll", None),
    }


def dotted(pairs: tuple[tuple[str, str], ...]) -> list[str]:
    return [holder + "." + name for holder, name in pairs]


# U1


def test_missing_names_each_absent_name_in_order_and_all_lists_the_table() -> None:
    assert ffi.missing(real_holders()) == []
    assert isinstance(ffi.NEEDED, tuple) and isinstance(ffi.OPTIONAL, tuple)
    assert len(ffi.NEEDED) >= 30 and len(ffi.OPTIONAL) == 1
    assert len(set(dotted(ffi.NEEDED) + dotted(ffi.OPTIONAL))) == len(ffi.NEEDED) + 1
    # An empty stand-in for every holder: every name is absent, in NEEDED's order.
    empty = {holder: SimpleNamespace() for holder in real_holders()}
    assert ffi.missing(empty) == dotted(ffi.NEEDED)
    # A holder that is None reports its names (the pre-build review's L6), nothing more.
    partial = real_holders()
    partial["wasmtime._ffi.dll"] = None
    assert ffi.missing(partial) == ["wasmtime._ffi.dll.wasm_engine_new"]
    # A binding record whose argtypes are not four long is missing; Func's handle is read from
    # the class annotations (an instance attribute, so hasattr on the class is False).
    partial = real_holders()
    partial["wasmtime._bindings"] = SimpleNamespace(
        _wasmtime_store_epoch_deadline_callback=SimpleNamespace(argtypes=[1, 2, 3]),
        _wasi_config_set_stdout_custom=_bindings._wasi_config_set_stdout_custom,
    )
    partial["wasmtime.Func"] = type("F", (), {"__annotations__": {}})
    assert ffi.missing(partial) == [
        "wasmtime._bindings._wasmtime_store_epoch_deadline_callback",
        "wasmtime.Func._func",
    ]
    assert ffi.missing({}) == dotted(ffi.NEEDED)
    assert sorted(ffi.__all__) == sorted(TABLE)
    assert len(ffi.__all__) == len(TABLE)


# U2


def test_check_raises_one_import_error_naming_the_version_the_names_and_the_pin() -> None:
    holders = real_holders()
    holders["wasmtime.Trap"] = SimpleNamespace()
    holders["wasmtime._wasi"] = SimpleNamespace()
    with pytest.raises(ImportError) as info:
        ffi.check(holders)
    text = str(info.value)
    assert f"wasmtime-py {ffi.version()} lacks" in text
    assert "wasmtime._wasi.CUSTOM_OUTPUTS, wasmtime.Trap._from_ptr" in text
    assert ffi.PIN in text and "install a wasmtime-py inside that range" in text
    ffi.check(real_holders())  # nothing missing: nothing raised


# U3


def test_the_runner_lets_the_adapters_import_error_through(monkeypatch) -> None:
    """A moved symbol is seen at the first run(), before any engine exists, naming the version
    and the names; with no wasmtime-py at all, the "needs wasmtime-py" error, its cause chained."""
    import wasi_python

    monkeypatch.delattr(_ffi, "wasmtime_error_new")
    monkeypatch.delitem(sys.modules, "wasi_python._wasmtime_ffi")
    monkeypatch.delattr(wasi_python, "_wasmtime_ffi")  # else `from . import` finds the old one
    version = re.escape(importlib.metadata.version("wasmtime"))
    with pytest.raises(ImportError, match=rf"wasmtime-py {version} .*wasmtime_error_new"):
        runner._wasmtime()
    assert "wasi_python._wasmtime_ffi" not in sys.modules
    monkeypatch.undo()
    assert sys.modules["wasi_python._wasmtime_ffi"] is ffi
    assert runner._wasmtime() is wt
    monkeypatch.setitem(sys.modules, "wasmtime", None)
    with pytest.raises(ImportError, match=r"needs wasmtime-py") as info:
        runner._wasmtime()
    assert isinstance(info.value.__cause__, ImportError)


# U4


def test_the_pin_is_written_the_same_in_three_places(monkeypatch) -> None:
    project = tomllib.loads((paths.REPO / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["dependencies"] == [ffi.PIN]
    monkeypatch.setitem(sys.modules, "wasmtime", None)
    with pytest.raises(ImportError) as info:
        runner._wasmtime()
    assert f"({ffi.PIN})" in str(info.value)


# U5


def test_the_bindings_the_runner_calls_exist() -> None:
    """The shapes of the bindings the seam reads its C types from, pinned since a release could
    move them; the runner's two output callbacks are declared with the seam's types (ctypes
    caches a CFUNCTYPE by its signature, so the identity holds)."""
    assert type(runner._output_write) is ffi.OUTPUT_WRITE
    assert type(runner._output_free) is ffi.OUTPUT_FREE
    for name in ("wasi_config_set_stdout_custom", "wasi_config_set_stderr_custom"):
        assert callable(getattr(_ffi, name)), name
        argtypes = getattr(_bindings, "_" + name).argtypes
        assert len(argtypes) == 4, name
        assert argtypes[0] is ctypes.POINTER(_ffi.wasi_config_t), name
        assert argtypes[1] is ffi.OUTPUT_WRITE, name
        assert argtypes[2] is ctypes.c_void_p, name
        assert argtypes[3] is ffi.OUTPUT_FREE, name
    assert ffi.OUTPUT_WRITE._restype_ is ctypes.c_ssize_t
    assert ffi.OUTPUT_WRITE._argtypes_ == (
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_ubyte),
        ctypes.c_size_t,
    )
    assert ffi.OUTPUT_FREE._argtypes_ == (ctypes.c_void_p,)
    assert callable(_ffi.wasmtime_context_set_epoch_deadline)
    assert _bindings._wasmtime_context_set_epoch_deadline.argtypes == [
        ctypes.POINTER(_ffi.wasmtime_context_t),
        ctypes.c_uint64,
    ]
    # spec 015: the epoch callback, and the error it answers with
    assert callable(_ffi.wasmtime_store_epoch_deadline_callback)
    argtypes = _bindings._wasmtime_store_epoch_deadline_callback.argtypes
    assert len(argtypes) == 4
    assert argtypes[0] is ctypes.POINTER(_ffi.wasmtime_store_t)
    assert argtypes[1] is ffi.EPOCH_CALLBACK
    assert ffi.EPOCH_CALLBACK._restype_ is ctypes.c_size_t
    assert ffi.EPOCH_CALLBACK._argtypes_ == (
        ffi.Context,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_uint64),
        ctypes.POINTER(ctypes.c_uint8),
    )
    assert ffi.Context is ctypes.POINTER(_ffi.wasmtime_context_t)
    assert argtypes[2] is ctypes.c_void_p
    assert argtypes[3]._argtypes_ == (ctypes.c_void_p,)
    assert callable(_ffi.wasmtime_error_new)


# U6


def test_the_stop_error_is_real_and_never_leaves_a_zero_delta(monkeypatch) -> None:
    """Spec 015's build review, F2: an error wasmtime can own, or, when none can be made, a
    continue by one tick, never by 0."""
    address = ffi.new_error(b"x")
    assert isinstance(address, int) and address
    ffi.delete_error(address)
    delta = (ctypes.c_uint64 * 1)()
    address = runner._stop_error(delta)
    assert address and delta[0] == 0
    ffi.delete_error(address)

    def broken(message):
        raise MemoryError

    monkeypatch.setattr(ffi, "new_error", broken)
    assert runner._stop_error(delta) == 0 and delta[0] == 1
    delta[0] = 0
    monkeypatch.setattr(ffi, "new_error", lambda message: 0)
    assert runner._stop_error(delta) == 0 and delta[0] == 1


# U7


class RecordingConfig:
    """A stand-in Config recording what is set on it; `ptr()` is itself, so a recorder in the
    binding's place sees the object."""

    def __init__(self) -> None:
        object.__setattr__(self, "set", {})

    def __setattr__(self, name: str, value: object) -> None:
        self.set[name] = value

    def ptr(self) -> RecordingConfig:
        return self


class WithProperty(RecordingConfig):
    @property
    def async_stack_size(self) -> int:
        return 0

    @async_stack_size.setter
    def async_stack_size(self, size: int) -> None:
        self.set["async_stack_size (property)"] = size

    def __setattr__(self, name: str, value: object) -> None:
        if name == "async_stack_size":
            object.__setattr__(self, name, value)
        else:
            super().__setattr__(name, value)


def test_set_async_stack_takes_the_property_then_the_binding_then_refuses(monkeypatch) -> None:
    calls: list[tuple[object, int]] = []
    monkeypatch.setattr(ffi, "ASYNC_STACK_SETTER", lambda cfg, size: calls.append((cfg, size)))
    cfg = WithProperty()
    ffi.set_async_stack(cfg, 8 << 20)
    assert cfg.set == {"async_stack_size (property)": 8 << 20} and calls == []
    cfg = RecordingConfig()
    ffi.set_async_stack(cfg, 8 << 20)
    assert cfg.set == {} and calls == [(cfg, 8 << 20)]
    monkeypatch.setattr(ffi, "ASYNC_STACK_SETTER", None)
    with pytest.raises(RuntimeError, match=r"wasmtime-py .* cannot set async_stack_size"):
        ffi.set_async_stack(RecordingConfig(), 8 << 20)


# U8


def test_engine_symbol_address_is_a_real_address() -> None:
    address = ffi.engine_symbol_address()
    assert isinstance(address, int) and address > 0


# The WAT modules of U9 to U16.

ADD = """(module
  (func (export "add") (param i32 i64) (result i32)
    (i32.add (local.get 0) (i32.wrap_i64 (local.get 1)))))"""
BOOM = '(module (func (export "boom") (param i32) (result i32) unreachable))'
ONE = '(module (func (export "one") (result i32) i32.const 1))'
LOOP = '(module (func (export "loop") (loop br 0)))'
CALLS_HOST = """(module
  (import "host" "f" (func $f))
  (func (export "run") call $f))"""
WRITES = """(module
  (import "wasi_snapshot_preview1" "fd_write"
    (func $fd_write (param i32 i32 i32 i32) (result i32)))
  (memory (export "memory") 1)
  (data (i32.const 100) "out\\n")
  (data (i32.const 108) "err\\n")
  (func (export "_start")
    (i32.store (i32.const 0) (i32.const 100))
    (i32.store (i32.const 4) (i32.const 4))
    (drop (call $fd_write (i32.const 1) (i32.const 0) (i32.const 1) (i32.const 8)))
    (i32.store (i32.const 0) (i32.const 108))
    (i32.store (i32.const 4) (i32.const 4))
    (drop (call $fd_write (i32.const 2) (i32.const 0) (i32.const 1) (i32.const 8)))))"""


def engine(*, fuel: bool = False, epochs: bool = False) -> wt.Engine:
    config = wt.Config()
    config.consume_fuel = fuel
    config.epoch_interruption = epochs
    return wt.Engine(config)


def export(store: wt.Store, wat: str, name: str) -> wt.Func:
    instance = wt.Instance(store, wt.Module(store.engine, wat), [])
    return instance.exports(store)[name]


# U9


def test_the_judges_three_reads_of_wasmtime_pys_own_tables() -> None:
    store = wt.Store(engine())
    assert export(store, ONE, "one")(store) == 1
    assert ffi.last_exception() is None
    before = ffi.host_function_count()
    assert isinstance(before, int)
    # The count is the table's high-water mark: a definition takes a freed slot first (earlier
    # rows of this worker freed some), and grows the table once none is free.
    linker = wt.Linker(store.engine)
    for n in range(before + 1):
        linker.define_func("host", f"f{n}", wt.FuncType([], []), lambda: None)
        assert ffi.host_function_count() in (before, before + 1)
        if ffi.host_function_count() == before + 1:
            break
    assert ffi.host_function_count() == before + 1
    assert callable(ffi.custom_output_table().allocate)


# U10


def test_the_package_imports_without_the_adapter() -> None:
    code = (
        "import sys\n"
        f"sys.path.insert(0, {str(paths.REPO / 'src')!r})\n"
        "import wasi_python\n"
        "print('wasi_python._wasmtime_ffi' in sys.modules, callable(wasi_python.run))\n"
    )
    out = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.split() == ["False", "True"], out.stdout


# U11


def test_a_prepared_call_reuses_its_arrays_and_raises_the_trap() -> None:
    store = wt.Store(engine())
    context = ffi.context_of(store)
    assert isinstance(context, ffi.Context)
    add = ffi.PreparedCall(ffi.raw_func(export(store, ADD, "add")), ("i32", "i64"))
    assert add.call(context, (3, 4)) == 7
    assert add.call(context, (10, (1 << 32) + 5)) == 15  # the same arrays, a second answer
    assert add.call(context, (-1, 1)) == 0
    boom = ffi.PreparedCall(ffi.raw_func(export(store, BOOM, "boom")), ("i32",))
    with pytest.raises(wt.Trap, match="unreachable"):
        boom.call(context, (1,))
    with pytest.raises(wt.Trap):
        boom.call(context, (2,))  # the trap out-pointer is made per call: no stale trap
    assert add.call(context, (1, 1)) == 2


# U12


def test_fuel_round_trips_on_a_metered_store_and_an_unmetered_one_refuses_reads() -> None:
    store = wt.Store(engine(fuel=True))
    store.set_fuel(1000)
    assert ffi.get_fuel(store) == 1000
    ffi.set_fuel(store, 5)
    assert ffi.get_fuel(store) == 5 == store.get_fuel()
    private = SimpleNamespace(_context=store._context)  # a Caller's shape: no public methods
    assert ffi.get_fuel(private) == 5
    ffi.set_fuel(private, 9)
    assert ffi.get_fuel(store) == 9
    plain = wt.Store(engine())
    with pytest.raises(wt.WasmtimeError):
        ffi.get_fuel(plain)
    with pytest.raises(wt.WasmtimeError):
        ffi.get_fuel(SimpleNamespace(_context=plain._context))
    ffi.set_fuel(plain, 5)  # raises nothing on either path
    ffi.set_fuel(SimpleNamespace(_context=plain._context), 5)


# U13


def test_watch_epochs_registers_a_callback_whose_error_ends_the_call() -> None:
    store = wt.Store(engine(epochs=True))
    seen: list[int] = []

    @ffi.EPOCH_CALLBACK
    def callback(context, data, delta, kind):
        seen.append(ctypes.addressof(context.contents))
        return ffi.new_error(b"stopped by a unit row")

    ffi.watch_epochs(store, callback)
    store.set_epoch_deadline(1)
    store.engine.increment_epoch()
    loop = export(store, LOOP, "loop")
    with pytest.raises(wt.WasmtimeError) as info:
        loop(store)
    assert "stopped by a unit row" in str(info.value)
    assert seen == [ffi.context_address(store)]


# U14


def test_a_deadline_of_zero_traps_the_next_call() -> None:
    store = wt.Store(engine(epochs=True))
    one = export(store, ONE, "one")
    store.set_epoch_deadline(1 << 20)
    assert one(store) == 1
    ffi.set_epoch_deadline(store, 0)
    with pytest.raises(wt.Trap):
        one(store)
    other = wt.Store(engine(epochs=True))
    one = export(other, ONE, "one")
    other.set_epoch_deadline(1 << 20)
    assert one(other) == 1
    ffi.set_epoch_deadline(SimpleNamespace(_context=other._context), 0)  # the private path
    with pytest.raises(wt.Trap):
        one(other)


# U15


def test_a_callers_context_is_its_stores() -> None:
    store = wt.Store(engine())
    seen: list[int] = []
    linker = wt.Linker(store.engine)

    def host(caller: wt.Caller) -> None:
        seen.append(ffi.context_address(caller))
        assert ctypes.addressof(ffi.context_of(caller).contents) == seen[-1]

    linker.define_func("host", "f", wt.FuncType([], []), host, access_caller=True)
    instance = linker.instantiate(store, wt.Module(store.engine, CALLS_HOST))
    instance.exports(store)["run"](store)
    assert seen == [ffi.context_address(store)]
    assert ctypes.addressof(ffi.context_of(store).contents) == seen[0]


# U16


def test_custom_outputs_reach_the_write_callback_and_are_freed_once_per_key() -> None:
    writes: list[tuple[int | None, bytes]] = []
    frees: list[int | None] = []

    @ffi.OUTPUT_WRITE
    def write(key, data, size):
        writes.append((key, ctypes.string_at(data, size)))
        return size

    @ffi.OUTPUT_FREE
    def free(key):
        frees.append(key)

    store = wt.Store(engine())
    wasi = wt.WasiConfig()
    ffi.set_custom_outputs(wasi, write, free, 11, 22)
    store.set_wasi(wasi)
    linker = wt.Linker(store.engine)
    linker.define_wasi()
    instance = linker.instantiate(store, wt.Module(store.engine, WRITES))
    instance.exports(store)["_start"](store)
    for _ in range(200):  # wasmtime writes on its own threads: a fail-safe that counts rounds
        if len(writes) == 2:
            break
        gc.collect()
    assert sorted(writes) == [(11, b"out\n"), (22, b"err\n")]
    del instance, linker, store, wasi
    for _ in range(200):
        gc.collect()
        if len(frees) == 2:
            break
    assert sorted(frees) == [11, 22]


# U18


class PublicStore:
    """A store-like with the public methods, recording their arguments; its private context is
    never asked for."""

    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def get_fuel(self) -> int:
        self.calls.append(("get_fuel",))
        return 42

    def set_fuel(self, fuel: int) -> None:
        self.calls.append(("set_fuel", fuel))

    def set_epoch_deadline(self, ticks: int) -> None:
        self.calls.append(("set_epoch_deadline", ticks))

    def _context(self):
        raise AssertionError("the private path was taken on an object with the public method")


class RefusingStore(PublicStore):
    def set_fuel(self, fuel: int) -> None:
        raise wt.WasmtimeError("not metered")


def test_the_public_api_is_preferred_where_the_object_has_it(monkeypatch) -> None:
    public = {"get_fuel", "set_fuel", "set_epoch_deadline"}
    assert public <= {n for n in dir(wt.Store) if callable(getattr(wt.Store, n))}
    assert not public & set(dir(wt.Caller))  # on 49.0.0 a Caller takes the private path
    bindings: list[tuple[str, object]] = []

    def record(name):
        return lambda context, *rest: bindings.append((name, context)) or None

    monkeypatch.setattr(_ffi, "wasmtime_context_get_fuel", record("get"))
    monkeypatch.setattr(_ffi, "wasmtime_context_set_fuel", record("set"))
    monkeypatch.setattr(_ffi, "wasmtime_context_set_epoch_deadline", record("deadline"))
    store = PublicStore()
    assert ffi.get_fuel(store) == 42
    ffi.set_fuel(store, 7)
    ffi.set_epoch_deadline(store, 0)
    assert store.calls == [("get_fuel",), ("set_fuel", 7), ("set_epoch_deadline", 0)]
    ffi.set_fuel(RefusingStore(), 7)  # the public path's refusal is dropped: never raises
    assert bindings == []
    context = object()
    private = SimpleNamespace(_context=lambda: context)
    assert ffi.get_fuel(private) == 0  # the recorder wrote nothing into the out-parameter
    ffi.set_fuel(private, 7)
    ffi.set_epoch_deadline(private, 0)
    assert bindings == [("get", context), ("set", context), ("deadline", context)]
    setter: list[object] = []
    monkeypatch.setattr(ffi, "ASYNC_STACK_SETTER", lambda cfg, size: setter.append(cfg))
    cfg = WithProperty()
    ffi.set_async_stack(cfg, 1 << 20)
    assert cfg.set == {"async_stack_size (property)": 1 << 20} and setter == []
    cfg = RecordingConfig()
    ffi.set_async_stack(cfg, 1 << 20)
    assert setter == [cfg]
