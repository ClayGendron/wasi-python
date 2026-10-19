"""Concurrent calls share nothing (spec 011): the runner's host functions are defined once per
engine and find their call through a stack checked against the caller's store; whatever they
catch is recorded on that call, the guest is stopped through its epoch deadline, and the call
reports or re-raises it on its own thread. Nothing here measures time."""

from __future__ import annotations

import asyncio
import ctypes
import struct

import pytest
import wasmtime as wt
from wasmtime import _bindings, _ffi, _func

from wasi_python import runner


def guest(mode: int) -> str:
    """A guest whose door call makes the host allocate; host_alloc then exits (1), hits
    unreachable (2), overflows the stack (3) or returns a buffer (0). Straight-line code stores
    the door's answer at 64, before the next function entry; a 1 at 68 means the guest ran on
    past that entry."""
    return f"""
(module
  (import "host" "call" (func $call (param i32 i32 i32 i32) (result i32)))
  (import "wasi_snapshot_preview1" "proc_exit" (func $exit (param i32)))
  (memory (export "memory") 1)
  (func $deep (param i32) (result i32) (call $deep (i32.add (local.get 0) (i32.const 1))))
  (func $empty)
  (func (export "host_alloc") (param i32) (result i32)
    (if (i32.eq (i32.const {mode}) (i32.const 1)) (then (call $exit (i32.const 7))))
    (if (i32.eq (i32.const {mode}) (i32.const 2)) (then unreachable))
    (if (i32.eq (i32.const {mode}) (i32.const 3)) (then (drop (call $deep (i32.const 0)))))
    (i32.const 1024))
  (func (export "run") (result i32) (local $r i32)
    (local.set $r (call $call (i32.const 0) (i32.const 3) (i32.const 16) (i32.const 20)))
    (i32.store (i32.const 64) (local.get $r))
    (call $empty)
    (i32.store (i32.const 68) (i32.const 1))
    (local.get $r)))
"""


class NoWaits:
    def wait(self, seconds: float) -> None:
        raise AssertionError("no wait expected")


class Keeping:
    """The runner's shared linker, keeping the instance so a test can read the guest's memory
    after the call, raised or not."""

    def __init__(self, linker) -> None:
        self.linker, self.instance = linker, None

    def instantiate(self, store, module):
        self.instance = self.linker.instantiate(store, module)
        return self.instance


def drive(mode: int, host, *, other_store: bool = False, raises=None):
    """Run the guest through the runner's shared linker. Returns (exit code, trap) or ("raised",
    the exception's type), then the door's answer and whether the guest ran past the stop."""
    config = wt.Config()
    config.epoch_interruption = True
    engine = wt.Engine(config)
    store = wt.Store(engine)
    store.set_epoch_deadline(2**40)
    store.set_wasi(wt.WasiConfig())
    owner = wt.Store(engine) if other_store else store
    call = runner._Call(owner, host, NoWaits(), 0)
    linker = Keeping(runner._linker(wt, engine))
    try:
        done = runner._drive(wt, linker, store, wt.Module(engine, guest(mode)), call, None)
        result = (done.exit_code, done.trapped)
    except BaseException as e:
        if raises is None or not isinstance(e, raises):
            raise
        result = ("raised", type(e))
    assert runner._stack() == [], "the call was left on the thread's stack"
    memory = linker.instance.exports(store)["memory"]
    answer, ran_on = struct.unpack("<ii", bytes(memory.read(store, 64, 72)))
    return (*result, answer, ran_on)


def test_a_buffer_from_host_alloc_reaches_the_guest() -> None:
    assert drive(0, lambda frame: b"ok") == (0, None, 0, 1)


def test_an_exit_in_host_alloc_is_the_calls_exit() -> None:
    """The door answers -2 and the guest stops at its next function entry; the call reports the
    exit, not what followed."""
    assert drive(1, lambda frame: b"ok") == (7, None, runner.HOST_FAULT, 0)


@pytest.mark.parametrize("mode", [2, 3], ids=["unreachable", "stack overflow"])
def test_a_trap_in_host_alloc_is_the_calls_trap(mode) -> None:
    """The call reports the trap host_alloc hit (as the runner names any trap, by the first line
    of its message), not the interrupt that stopped the guest afterwards."""
    exit_code, trapped, answer, ran_on = drive(mode, lambda frame: b"ok")
    assert (exit_code, answer, ran_on) == (None, runner.HOST_FAULT, 0)
    assert trapped and trapped != "deadline", trapped


@pytest.mark.parametrize("raised", [asyncio.CancelledError, KeyboardInterrupt, SystemExit])
def test_a_hosts_base_exception_comes_back_to_its_own_call(raised) -> None:
    """Nothing crosses wasmtime-py's process-wide exception slot: the door itself answers -2
    (an exception through the slot would unwind the guest before it stored the answer), the
    guest stops, and the call raises what its host raised."""

    def host(frame: bytes) -> bytes:
        raise raised()

    assert drive(0, host, raises=raised) == ("raised", raised, runner.HOST_FAULT, 0)
    assert _func.LAST_EXCEPTION is None


def test_a_caller_from_another_store_gets_no_host() -> None:
    """A stack entry belongs to one store: a guest in another store is answered as if no host
    were bound, never with this call's host."""
    assert drive(0, lambda frame: b"ok", other_store=True)[2] == runner.NO_HOST


def test_a_stopped_call_reports_no_fuel() -> None:
    """After the stop's interrupt the fuel counter is stale, so a stopped call reports None,
    even when its recorded cause is an exit (spec 011)."""
    from types import SimpleNamespace

    done = runner._Driven(7, None, True, None)
    plain = SimpleNamespace(stopped=None, ended=None)
    assert runner._fuel_used(1000, done, plain, lambda: 400) == 600
    stopped = SimpleNamespace(stopped=SystemExit(), ended=None)
    assert runner._fuel_used(1000, done, stopped, lambda: 400) is None
    ended = SimpleNamespace(stopped=None, ended="cancelled")  # spec 015's epoch callback
    assert runner._fuel_used(1000, done, ended, lambda: 400) is None


def test_the_bindings_the_runner_calls_exist() -> None:
    """The runner calls three C functions through wasmtime-py's private binding module
    (`_ffi`, which re-exports `_bindings`); pin their shape, since a release could move them."""
    for name in ("wasi_config_set_stdout_custom", "wasi_config_set_stderr_custom"):
        assert callable(getattr(_ffi, name)), name
        argtypes = getattr(_bindings, "_" + name).argtypes
        assert len(argtypes) == 4, name
        assert argtypes[0] is ctypes.POINTER(_ffi.wasi_config_t), name
        assert argtypes[2] is ctypes.c_void_p, name
        assert argtypes[1] is type(runner._output_write), name  # ctypes caches by signature
        assert argtypes[3] is type(runner._output_free), name
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
    assert argtypes[1]._restype_ is ctypes.c_size_t
    assert argtypes[1]._argtypes_ == (
        ctypes.POINTER(_ffi.wasmtime_context_t),
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_uint64),
        ctypes.POINTER(ctypes.c_uint8),
    )
    assert argtypes[2] is ctypes.c_void_p
    assert argtypes[3]._argtypes_ == (ctypes.c_void_p,)
    assert callable(_ffi.wasmtime_error_new)


@pytest.fixture
def default_ctrl_c():
    """Python's default SIGINT handler on the main thread, as in a plain script."""
    import signal

    before = signal.signal(signal.SIGINT, signal.default_int_handler)
    yield
    signal.signal(signal.SIGINT, before)


def test_ctrl_c_during_a_call_stops_it_and_is_raised_by_it(default_ctrl_c) -> None:
    """Ctrl-C only sets a flag while a call holds the main thread (the default handler would
    raise inside wasmtime-py's trampoline, where it aborts the process); the next host function
    turns it into a stop, and the call raises KeyboardInterrupt. The host is never called."""
    import signal

    seen = []
    with pytest.raises(KeyboardInterrupt):
        with runner._deferred_ctrl_c():
            assert signal.getsignal(signal.SIGINT) is runner._note_ctrl_c
            runner._note_ctrl_c(signal.SIGINT, None)  # what the handler does on Ctrl-C
            drive(0, lambda frame: seen.append(frame) or b"ok")
    assert seen == [] and runner._ctrl_c["pending"] is False
    assert signal.getsignal(signal.SIGINT) is signal.default_int_handler


def test_ctrl_c_no_host_function_saw_is_raised_when_the_call_ends(default_ctrl_c) -> None:
    import signal

    with pytest.raises(KeyboardInterrupt):
        with runner._deferred_ctrl_c():
            runner._note_ctrl_c(signal.SIGINT, None)
    assert signal.getsignal(signal.SIGINT) is signal.default_int_handler


def test_ctrl_c_is_left_alone_under_an_embedders_handler() -> None:
    import signal

    def mine(signum, frame) -> None:
        pass

    before = signal.signal(signal.SIGINT, mine)
    try:
        with runner._deferred_ctrl_c():
            assert signal.getsignal(signal.SIGINT) is mine
    finally:
        signal.signal(signal.SIGINT, before)


def test_a_handler_a_host_sets_during_a_call_is_kept(default_ctrl_c) -> None:
    """The default handler comes back only if the runner's own is still installed (spec 011)."""
    import signal

    def hosts(signum, frame) -> None:
        pass

    with runner._deferred_ctrl_c():
        signal.signal(signal.SIGINT, hosts)
    assert signal.getsignal(signal.SIGINT) is hosts


class RecordingConfig:
    """A wasmtime.Config stand-in that keeps what is set on it."""

    def __init__(self) -> None:
        self.set: dict[str, object] = {}

    def __setattr__(self, name: str, value: object) -> None:
        if name == "set":
            object.__setattr__(self, name, value)
        else:
            self.set[name] = value


def test_the_runner_states_its_wasm_stack(monkeypatch) -> None:
    """Spec 071, criterion 5: the runner's engines are made with a 512 KiB wasm stack, stated,
    beside fuel (for the metered one) and epoch interruption."""
    made: list[RecordingConfig] = []
    monkeypatch.setattr(wt, "Config", RecordingConfig)
    monkeypatch.setattr(wt, "Engine", lambda cfg: made.append(cfg) or object())
    monkeypatch.setattr(runner, "_engines", {})
    monkeypatch.setitem(runner._fork, "used", runner._fork["used"])
    runner._engine(True)
    runner._engine(False)
    assert runner._WASM_STACK == 512 * 1024
    assert [c.set for c in made] == [
        {"consume_fuel": True, "epoch_interruption": True, "max_wasm_stack": 512 * 1024},
        {"consume_fuel": False, "epoch_interruption": True, "max_wasm_stack": 512 * 1024},
    ]


def test_the_guest_driver_makes_the_runners_engine(monkeypatch) -> None:
    """Spec 071, criterion 5 (Decision 3): the judge's driver makes the runner's engine: fuel,
    epoch interruption and the same 512 KiB stack, so checks see the frames `run` gives."""
    from harness import guest

    made: list[RecordingConfig] = []
    monkeypatch.setattr(wt, "Config", RecordingConfig)
    monkeypatch.setattr(wt, "Engine", lambda cfg: made.append(cfg) or object())
    monkeypatch.setattr(guest, "_engine", None)
    guest.engine()
    assert made[0].set == {
        "consume_fuel": True,
        "epoch_interruption": True,
        "max_wasm_stack": 512 * 1024,
    }


def test_trap_handlers_ready_reads_each_signal_by_load_base() -> None:
    """Spec 071, criterion 11's unit: on Linux the check names the first signal whose handler
    lies outside wasmtime's library (compared by load base), counts SIGFPE on x86_64 only, treats
    any failure as not ready, and reads nothing on macOS or Windows."""
    import signal

    ours = 0x7000

    def bases(**by_name: int | None):
        table = {int(getattr(signal, k)): v for k, v in by_name.items()}
        return lambda signum: table.get(signum, ours)

    def ready(machine="x86_64", platform="linux", handler_base=None, wasmtime_base=lambda: ours):
        return runner._trap_handlers_ready(platform, machine, handler_base, wasmtime_base)

    assert ready(handler_base=bases()) is None
    assert ready(handler_base=bases(SIGILL=0x9000)) == "SIGILL"
    assert ready(handler_base=bases(SIGSEGV=None, SIGILL=0x9000)) == "SIGSEGV"
    assert ready(handler_base=bases(SIGFPE=None)) == "SIGFPE"
    assert ready("aarch64", handler_base=bases(SIGFPE=None)) is None
    assert ready(handler_base=bases(), wasmtime_base=lambda: None) == "SIGSEGV"

    def broken(signum: int) -> int | None:
        raise OSError("dladdr failed")

    assert ready(handler_base=broken) == "SIGSEGV"
    for platform in ("darwin", "win32"):
        assert ready(platform=platform, handler_base=broken) is None
