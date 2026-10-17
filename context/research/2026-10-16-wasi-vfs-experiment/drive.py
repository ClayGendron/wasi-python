"""Run a variant once, like the judge's driver (tests/harness/guest.py), but with the preopens chosen
by the caller: none, the root, or the root plus more. random_get and clock_time_get are answered by
the host exactly as the judge does, so fuel is exact and comparable with the judge's numbers.

Usage (as a library): run(wasm, ["-c", code], preopens=[(host_dir, guest_dir, mutable)], fuel=...)
"""

from __future__ import annotations

import hashlib
import itertools
import struct
from pathlib import Path

import wasmtime as wt

ARGV0 = "/usr/local/bin/python.wasm"
REALTIME_START_NS = 1_767_225_600_000_000_000
CLOCK_STEP_NS = 1_000

_engine = None
_modules: dict[str, wt.Module] = {}


def engine() -> wt.Engine:
    global _engine
    if _engine is None:
        cfg = wt.Config()
        cfg.consume_fuel = True
        _engine = wt.Engine(cfg)
    return _engine


def module(path: Path) -> wt.Module:
    key = str(path)
    if key not in _modules:
        _modules[key] = wt.Module.from_file(engine(), key)
    return _modules[key]


def run(wasm: Path, argv: list[str], *, preopens, io: Path, fuel: int = 2 * 10**11):
    mod = module(wasm)
    names = {e.name for e in mod.exports}
    io.mkdir(parents=True, exist_ok=True)
    store = wt.Store(engine())
    store.set_fuel(fuel)
    wasi = wt.WasiConfig()
    wasi.argv = [ARGV0, *argv]
    for host_dir, guest_dir, mutable in preopens:
        wasi.preopen_dir(str(host_dir), guest_dir, mutable)
    wasi.stdout_file = str(io / "stdout")
    wasi.stderr_file = str(io / "stderr")
    store.set_wasi(wasi)
    linker = wt.Linker(engine())
    linker.define_wasi()
    linker.allow_shadowing = True
    i32, i64 = wt.ValType.i32(), wt.ValType.i64()
    counter = itertools.count()
    ticks = itertools.count(1)

    def random_get(caller, buf, n):
        out = bytearray()
        while len(out) < n:
            out += hashlib.sha256(struct.pack("<Q", next(counter))).digest()
        caller.get("memory").write(caller, bytes(out[:n]), buf)
        return 0

    def clock_time_get(caller, clock_id, _precision, out):
        start = REALTIME_START_NS if clock_id == 0 else 0
        caller.get("memory").write(
            caller, struct.pack("<Q", start + next(ticks) * CLOCK_STEP_NS), out
        )
        return 0

    p1 = "wasi_snapshot_preview1"
    linker.define_func(p1, "random_get", wt.FuncType([i32, i32], [i32]), random_get, True)
    linker.define_func(
        p1, "clock_time_get", wt.FuncType([i32, i64, i32], [i32]), clock_time_get, True
    )
    linker.define_func("host", "call", wt.FuncType([i32] * 4, [i32]), lambda *a: -1, True)
    code, trapped = None, None
    try:
        inst = linker.instantiate(store, mod)
        ex = inst.exports(store)
        if "_initialize" in names:
            ex["_initialize"](store)
        code = ex["run"](store)
    except wt.ExitTrap as e:
        code = e.code
    except wt.Trap as e:
        trapped = (e.message or "trap").strip().splitlines()[0]
    except wt.WasmtimeError as e:
        trapped = str(e).strip().splitlines()[0]
    return {
        "exit": code,
        "trapped": trapped,
        "fuel": fuel - store.get_fuel(),
        "stdout": (io / "stdout").read_text(errors="replace"),
        "stderr": (io / "stderr").read_text(errors="replace"),
    }
