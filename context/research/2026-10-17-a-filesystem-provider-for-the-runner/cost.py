"""What one crossing costs: a tiny guest calls fd_fdstat_get(1) N times, five ways.

uv run --no-sync python cost.py SCRATCH > cost.txt

  real       wasmtime's own WASI, nothing shadowed (the runner today)
  empty      a Python shadow that answers 0 at once: the cost of entering Python
  provider   a Python shadow that writes a 24-byte fdstat, as a provider's fd would
  forward    a Python shadow that forwards to wasmtime's WASI through the trampoline (Func.__call__)
  fast       as forward, through a cached ctypes call (wasmtime_func_call), no per-call type lookup

Fuel per call is exact (a count); seconds per call are a benchmark fact on this machine only.
"""

from __future__ import annotations

import ctypes
import struct
import sys
import time
from pathlib import Path

import wasmtime as wt
from wasmtime import _ffi as ffi

SCRATCH = Path(sys.argv[1])
N = 100_000
P1 = "wasi_snapshot_preview1"

GUEST = f"""(module
 (import "{P1}" "fd_fdstat_get" (func $get (param i32 i32) (result i32)))
 (memory (export "memory") 1)
 (func (export "loop") (param $n i32) (result i32) (local $e i32)
  (block $out (loop $l
   (br_if $out (i32.eqz (local.get $n)))
   (local.set $e (i32.or (local.get $e) (call $get (i32.const 1) (i32.const 64))))
   (local.set $n (i32.sub (local.get $n) (i32.const 1)))
   (br $l)))
  (local.get $e)))"""

TRAMP = f"""(module
 (import "{P1}" "fd_fdstat_get" (func $get (param i32 i32) (result i32)))
 (import "env" "memory" (memory 0))
 (export "memory" (memory 0))
 (func (export "fd_fdstat_get") (param i32 i32) (result i32) local.get 0 local.get 1 call $get))"""


def run(how: str) -> tuple[int, float, int]:
    cfg = wt.Config()
    cfg.consume_fuel = True
    engine = wt.Engine(cfg)
    store = wt.Store(engine)
    store.set_fuel(10**12)
    w = wt.WasiConfig()
    w.stdout_file = str(SCRATCH / "cost.out")
    store.set_wasi(w)
    plain = wt.Linker(engine)
    plain.define_wasi()
    linker = plain
    i32 = wt.ValType.i32()
    ft = wt.FuncType([i32, i32], [i32])
    box: dict = {}
    if how != "real":
        linker = wt.Linker(engine)
        linker.define_wasi()
        linker.allow_shadowing = True
        rec = struct.pack("<BxHxxxxQQ", 2, 0, 0, 0)

        def empty(c, fd, out):
            return 0

        def provider(c, fd, out):
            c.get("memory").write(c, rec, out & 0xFFFFFFFF)
            return 0

        def forward(c, fd, out):
            return box["fwd"](c, fd, out)

        def fast(c, fd, out):
            p = box["params"]
            p[0].of.i32, p[1].of.i32 = fd, out
            err = ffi.wasmtime_func_call(c._context(), box["func"], p, 2, box["results"], 1, box["trapref"])
            if err or box["trap"]:
                raise RuntimeError("forward failed")  # a model only: the runner would record a stop
            return box["results"][0].of.i32

        fn = {"empty": empty, "provider": provider, "forward": forward, "fast": fast}[how]
        linker.define_func(P1, "fd_fdstat_get", ft, fn, True)
    ex = linker.instantiate(store, wt.Module(engine, GUEST)).exports(store)
    if how in ("forward", "fast"):
        t = wt.Instance(store, wt.Module(engine, TRAMP), [plain.get(store, P1, "fd_fdstat_get"), ex["memory"]])
        box["fwd"] = t.exports(store)["fd_fdstat_get"]
        box["func"] = ctypes.byref(box["fwd"]._func)
        params = (ffi.wasmtime_val_t * 2)()
        for v in params:
            v.kind = ffi.WASMTIME_I32.value
        box["params"], box["results"] = params, (ffi.wasmtime_val_t * 1)()
        box["trap"] = ctypes.POINTER(ffi.wasm_trap_t)()
        box["trapref"] = ctypes.byref(box["trap"])
    ex["loop"](store, 10)  # warm
    f0 = store.get_fuel()
    t0 = time.perf_counter()
    err = ex["loop"](store, N)
    secs = time.perf_counter() - t0
    return f0 - store.get_fuel(), secs, err


print(f"N = {N:,} calls of fd_fdstat_get(1) from a wasm loop")
print("how       | errno | fuel/call | µs/call (benchmark fact)")
for how in ("real", "empty", "provider", "forward", "fast"):
    best = None
    for _ in range(3):
        fuel, secs, err = run(how)
        best = secs if best is None else min(best, secs)
    print(f"{how:9} | {err:5} | {fuel / N:9.1f} | {best / N * 1e6:7.2f}")
