"""Concurrent calls share nothing (spec 011): the runner's host functions are defined once per
engine and find their call through a stack checked against the caller's store; whatever they
catch is recorded on that call, the guest is stopped through its epoch deadline, and the call
reports or re-raises it on its own thread. Nothing here measures time."""

from __future__ import annotations

import asyncio
import struct

import pytest
import wasmtime as wt

from wasi_python import _call, _engines, _home, _platform, _wasmtime_ffi
from wasi_python._process import process


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
    call = _call._Call(owner, host, NoWaits(), 0)
    linker = Keeping(_call._linker(wt, engine))
    try:
        done = _call._drive(wt, linker, store, wt.Module(engine, guest(mode)), call, None)
        result = (done.exit_code, done.trapped)
    except BaseException as e:
        if raises is None or not isinstance(e, raises):
            raise
        result = ("raised", type(e))
    assert _home._stack() == [], "the call was left on the thread's stack"
    memory = linker.instance.exports(store)["memory"]
    answer, ran_on = struct.unpack("<ii", bytes(memory.read(store, 64, 72)))
    return (*result, answer, ran_on)


def test_a_buffer_from_host_alloc_reaches_the_guest() -> None:
    assert drive(0, lambda frame: b"ok") == (0, None, 0, 1)


def test_an_exit_in_host_alloc_is_the_calls_exit() -> None:
    """The door answers -2 and the guest stops at its next function entry; the call reports the
    exit, not what followed."""
    assert drive(1, lambda frame: b"ok") == (7, None, _call.HOST_FAULT, 0)


@pytest.mark.parametrize("mode", [2, 3], ids=["unreachable", "stack overflow"])
def test_a_trap_in_host_alloc_is_the_calls_trap(mode) -> None:
    """The call reports the trap host_alloc hit (as the runner names any trap, by the first line
    of its message), not the interrupt that stopped the guest afterwards."""
    exit_code, trapped, answer, ran_on = drive(mode, lambda frame: b"ok")
    assert (exit_code, answer, ran_on) == (None, _call.HOST_FAULT, 0)
    assert trapped and trapped != "deadline", trapped


@pytest.mark.parametrize("raised", [asyncio.CancelledError, KeyboardInterrupt, SystemExit])
def test_a_hosts_base_exception_comes_back_to_its_own_call(raised) -> None:
    """Nothing crosses wasmtime-py's process-wide exception slot: the door itself answers -2
    (an exception through the slot would unwind the guest before it stored the answer), the
    guest stops, and the call raises what its host raised."""

    def host(frame: bytes) -> bytes:
        raise raised()

    assert drive(0, host, raises=raised) == ("raised", raised, _call.HOST_FAULT, 0)
    assert _wasmtime_ffi.last_exception() is None


def test_a_caller_from_another_store_gets_no_host() -> None:
    """A stack entry belongs to one store: a guest in another store is answered as if no host
    were bound, never with this call's host."""
    assert drive(0, lambda frame: b"ok", other_store=True)[2] == _call.NO_HOST


def test_a_stopped_call_reports_no_fuel() -> None:
    """After the stop's interrupt the fuel counter is stale, so a stopped call reports None,
    even when its recorded cause is an exit (spec 011)."""
    from types import SimpleNamespace

    done = _call._Driven(7, None, True, None)
    plain = SimpleNamespace(stopped=None, ended=None)
    assert _call._fuel_used(1000, done, plain, lambda: 400) == 600
    stopped = SimpleNamespace(stopped=SystemExit(), ended=None)
    assert _call._fuel_used(1000, done, stopped, lambda: 400) is None
    ended = SimpleNamespace(stopped=None, ended="cancelled")  # spec 015's epoch callback
    assert _call._fuel_used(1000, done, ended, lambda: 400) is None


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
        with _home._deferred_ctrl_c():
            assert signal.getsignal(signal.SIGINT) is _home._note_ctrl_c
            _home._note_ctrl_c(signal.SIGINT, None)  # what the handler does on Ctrl-C
            drive(0, lambda frame: seen.append(frame) or b"ok")
    assert seen == [] and process().ctrl_c_pending is False
    assert signal.getsignal(signal.SIGINT) is signal.default_int_handler


def test_ctrl_c_no_host_function_saw_is_raised_when_the_call_ends(default_ctrl_c) -> None:
    import signal

    with pytest.raises(KeyboardInterrupt):
        with _home._deferred_ctrl_c():
            _home._note_ctrl_c(signal.SIGINT, None)
    assert signal.getsignal(signal.SIGINT) is signal.default_int_handler


def test_ctrl_c_is_left_alone_under_an_embedders_handler() -> None:
    import signal

    def mine(signum, frame) -> None:
        pass

    before = signal.signal(signal.SIGINT, mine)
    try:
        with _home._deferred_ctrl_c():
            assert signal.getsignal(signal.SIGINT) is mine
    finally:
        signal.signal(signal.SIGINT, before)


def test_a_handler_a_host_sets_during_a_call_is_kept(default_ctrl_c) -> None:
    """The default handler comes back only if the runner's own is still installed (spec 011)."""
    import signal

    def hosts(signum, frame) -> None:
        pass

    with _home._deferred_ctrl_c():
        signal.signal(signal.SIGINT, hosts)
    assert signal.getsignal(signal.SIGINT) is hosts


class RecordingConfig:
    """A wasmtime.Config stand-in that keeps what is set on it, in order."""

    def __init__(self) -> None:
        self.set: dict[str, object] = {}

    def __setattr__(self, name: str, value: object) -> None:
        if name == "set":
            object.__setattr__(self, name, value)
        else:
            self.set[name] = value

    def ptr(self) -> RecordingConfig:
        return self


def _record_async_stack(monkeypatch) -> None:
    """The seam's binding for the async stack size, recording into the stand-in (spec 102)."""
    monkeypatch.setattr(
        _wasmtime_ffi,
        "ASYNC_STACK_SETTER",
        lambda cfg, size: cfg.set.__setitem__("async_stack_size (binding)", size),
    )


STATED = 8 * 1024 * 1024


def test_the_runner_states_its_wasm_stack(monkeypatch) -> None:
    """Spec 078, criterion 2 (restating spec 071's criterion 5): the runner's engines are made
    with an 8 MiB wasm stack, stated, beside fuel (for the metered one) and epoch interruption;
    wasmtime's async stack size is raised to it first, through wasmtime-py's own binding."""
    made: list[RecordingConfig] = []
    monkeypatch.setattr(wt, "Config", RecordingConfig)
    monkeypatch.setattr(wt, "Engine", lambda cfg: made.append(cfg) or object())
    monkeypatch.setattr(process(), "engines", {})
    monkeypatch.setattr(process(), "fork_used", process().fork_used)
    _record_async_stack(monkeypatch)
    _engines._engine(True)
    _engines._engine(False)
    assert _platform._WASM_STACK == STATED
    assert _platform._THREAD_STACK == STATED + 2 * 1024 * 1024
    assert [list(c.set.items()) for c in made] == [
        [
            ("consume_fuel", True),
            ("epoch_interruption", True),
            ("async_stack_size (binding)", STATED),
            ("max_wasm_stack", STATED),
        ],
        [
            ("consume_fuel", False),
            ("epoch_interruption", True),
            ("async_stack_size (binding)", STATED),
            ("max_wasm_stack", STATED),
        ],
    ]


def test_the_async_stack_size_property_is_preferred(monkeypatch) -> None:
    """Spec 078, criterion 2: a wasmtime-py whose Config has an async_stack_size property is set
    through it, and the binding is not called."""

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

    monkeypatch.setattr(_wasmtime_ffi, "ASYNC_STACK_SETTER", None)
    cfg = WithProperty()
    _wasmtime_ffi.set_async_stack(cfg, STATED)
    assert cfg.set == {"async_stack_size (property)": STATED}


def test_no_engine_is_made_without_the_async_stack_size(monkeypatch) -> None:
    """Spec 078, criterion 2 (the review's F5): with neither the property nor the binding, the
    engine is refused with RuntimeError naming wasmtime-py's version, before max_wasm_stack is set
    and before an Engine is made (wasmtime's refusal would abort the process)."""
    made: list[RecordingConfig] = []
    monkeypatch.setattr(wt, "Config", RecordingConfig)
    monkeypatch.setattr(wt, "Engine", lambda cfg: made.append(cfg) or object())
    monkeypatch.setattr(process(), "engines", {})
    monkeypatch.setattr(process(), "fork_used", process().fork_used)
    monkeypatch.setattr(_wasmtime_ffi, "ASYNC_STACK_SETTER", None)
    with pytest.raises(RuntimeError, match=r"wasmtime-py .* cannot set async_stack_size"):
        _engines._engine(True)
    assert made == []


def test_the_guest_driver_makes_the_runners_engine(monkeypatch) -> None:
    """Spec 078, criterion 2 (restating spec 071's criterion 5, Decision 3): the judge's driver
    makes the runner's engine: fuel, epoch interruption and the same 8 MiB stack, the async stack
    size first, so checks see the frames `run` gives."""
    from harness import guest

    made: list[RecordingConfig] = []
    monkeypatch.setattr(wt, "Config", RecordingConfig)
    monkeypatch.setattr(wt, "Engine", lambda cfg: made.append(cfg) or object())
    monkeypatch.setattr(guest, "_engine", None)
    _record_async_stack(monkeypatch)
    guest.engine()
    assert list(made[0].set.items()) == [
        ("consume_fuel", True),
        ("epoch_interruption", True),
        ("async_stack_size (binding)", STATED),
        ("max_wasm_stack", STATED),
    ]
    assert guest.THREAD_STACK == _platform._THREAD_STACK


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
        return _platform._trap_handlers_ready(platform, machine, handler_base, wasmtime_base)

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
