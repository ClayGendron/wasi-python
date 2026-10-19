"""Run guest cases on the frozen set with a chosen wasm stack, and report how each ended.

uv run python probe.py --binary snapshot|plain [--stack BYTES] [--async BYTES] [--wasm PATH]
                       [--cwasm PATH] CASEFILE [CASE ...]

Each case runs in a fresh instance, as the runner's engine is configured (fuel and epoch
interruption), with the stdlib zip read-only at /usr/local/lib and an empty writable root at /.
After the run, the lowest written byte of the linear-memory stack region [0, 16 MiB) is reported:
the C stack's low-water mark. One JSON line per case.
"""

import argparse
import ctypes
import importlib.util
import itertools
import json
import os
import shutil
import struct
import sys
import tempfile
from pathlib import Path

import wasmtime as wt

SET = Path("/Users/claygendron/Git/Repos/wasi_python/build/sets/s-4eb5418a2b1bb553-c353b1d9")
STACK_TOP = 16 * 1024 * 1024
ARGV0 = "/usr/local/bin/python.wasm"

ap = argparse.ArgumentParser()
ap.add_argument("--binary", default="snapshot")
ap.add_argument("--stack", type=int, default=0)
ap.add_argument("--async-stack", dest="async_stack", type=int, default=0)
ap.add_argument("--wasm")
ap.add_argument("--cwasm")
ap.add_argument("--fuel", type=int, default=4 * 10**10)
ap.add_argument("--env", action="append", default=[])
ap.add_argument("--mpl", action="store_true")
ap.add_argument("--main-thread", action="store_true", help="run on the main thread's own stack")
ap.add_argument("--engine", default="runner", help="runner (fuel, epoch) or bare (wasmtime's defaults)")
ap.add_argument("casefile")
ap.add_argument("cases", nargs="*")
a = ap.parse_args()

spec = importlib.util.spec_from_file_location("cases", a.casefile)
cases_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cases_mod)
CASES = cases_mod.CASES

cfg = wt.Config()
BARE = a.engine == "bare"
cfg.consume_fuel = not BARE
cfg.epoch_interruption = not BARE
if a.async_stack:
    from wasmtime import _ffi

    _ffi.dll.wasmtime_config_async_stack_size_set.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    _ffi.dll.wasmtime_config_async_stack_size_set.restype = None
    _ffi.dll.wasmtime_config_async_stack_size_set(ctypes.cast(cfg.ptr(), ctypes.c_void_p), a.async_stack)
if a.stack:
    cfg.max_wasm_stack = a.stack
engine = wt.Engine(cfg)
wasm = Path(a.wasm) if a.wasm else SET / ("python-snapshot.wasm" if a.binary == "snapshot" else "python.wasm")
if a.cwasm and Path(a.cwasm).exists():
    mod = wt.Module.deserialize_file(engine, a.cwasm)
else:
    mod = wt.Module.from_file(engine, str(wasm))
    if a.cwasm:
        Path(a.cwasm).write_bytes(mod.serialize())
names = {e.name for e in mod.exports}
reactor = "_initialize" in names

work = Path(tempfile.mkdtemp(prefix="probe-", dir=os.environ.get("PROBE_TMP")))
lib = work / "lib"
lib.mkdir()
shutil.copyfile(SET / "python-stdlib.zip", lib / "python315.zip")


def low_water(store, memory) -> int:
    data = memory.read(store, 0, STACK_TOP)
    for i in range(0, STACK_TOP, 4096):
        if any(data[i : i + 4096]):
            j = i
            while not data[j]:
                j += 1
            return j
    return STACK_TOP


def run_case(name: str, code: str) -> dict:
    root = work / f"root-{name}"
    (root / "usr/local/lib").mkdir(parents=True)
    (root / "tmp").mkdir()
    out, err = work / f"{name}.out", work / f"{name}.err"
    store = wt.Store(engine)
    if not BARE:
        store.set_epoch_deadline(1 << 40)
        store.set_fuel(2**63 - 1)
    wasi = wt.WasiConfig()
    wasi.argv = [ARGV0, "-c", code]
    wasi.env = [("HOME", "/tmp"), ("TMPDIR", "/tmp")] + [tuple(e.split("=", 1)) for e in a.env]
    wasi.preopen_dir(str(lib), "/usr/local/lib", False)
    if a.mpl:
        sys.path.insert(0, "/Users/claygendron/Git/Repos/wasi_python-071/tests")
        from harness import guest as _g
        wasi.preopen_dir(str(_g.mpl_data_dir(SET / "python-stdlib.zip", work)), "/usr/local/lib/python315.zip/matplotlib/mpl-data", False)
    wasi.preopen_dir(str(root), "/")
    wasi.stdout_file = str(out)
    wasi.stderr_file = str(err)
    store.set_wasi(wasi)
    linker = wt.Linker(engine)
    linker.define_wasi()
    linker.allow_shadowing = True
    i32, i64 = wt.ValType.i32(), wt.ValType.i64()
    ticks = itertools.count(1)
    rnd = itertools.count()

    def random_get(caller, buf, n):
        caller.get("memory").write(caller, bytes((next(rnd) * 7919) & 255 for _ in range(n)), buf)
        return 0

    def clock_time_get(caller, clock_id, _p, o):
        v = (1_767_225_600_000_000_000 if clock_id == 0 else 0) + next(ticks) * 1000
        caller.get("memory").write(caller, struct.pack("<Q", v), o)
        return 0

    def door(caller, *args):
        return -1

    p1 = "wasi_snapshot_preview1"
    linker.define_func(p1, "random_get", wt.FuncType([i32, i32], [i32]), random_get, True)
    linker.define_func(p1, "clock_time_get", wt.FuncType([i32, i64, i32], [i32]), clock_time_get, True)
    linker.define_func("host", "call", wt.FuncType([i32] * 4, [i32]), door, True)
    inst = linker.instantiate(store, mod)
    ex = inst.exports(store)
    memory = ex["memory"]
    base_low = low_water(store, memory)
    if not BARE:
        store.set_fuel(a.fuel)
    res = {"case": name, "binary": a.binary, "stack": a.stack or "default", "env": a.env, "start_low": base_low}
    try:
        if reactor:
            ex["_initialize"](store)
        res["exit"] = ex["run"](store)
    except wt.ExitTrap as e:
        res["exit"] = e.code
    except wt.Trap as e:
        lines = e.message.strip().splitlines()
        cause = [l for l in lines if "wasm trap" in l or "stack" in l.lower()]
        res["trap"] = "out of fuel" if e.trap_code == wt.TrapCode.OUT_OF_FUEL else (cause[-1].strip() if cause else lines[0])
    except wt.WasmtimeError as e:
        res["trap"] = str(e).strip().splitlines()[0]
    res["fuel"] = 0 if BARE else a.fuel - store.get_fuel()
    res["low"] = low_water(store, memory)
    if "__sp" in names:
        res["sp_used"] = STACK_TOP - ex["__sp"].value(store)
    res["c_stack_used"] = STACK_TOP - res["low"]
    o = out.read_text(errors="replace").strip().splitlines()
    e = err.read_text(errors="replace").strip().splitlines()
    res["stdout"] = o[-1] if o else ""
    res["stderr_last"] = e[-1] if e else ""
    res["stderr_lines"] = len(e)
    shutil.rmtree(root, ignore_errors=True)
    return res


import threading


def bisect(name, make, hi):
    """The largest N in [1, hi] whose run does not trap, and how the run at N + 1 ended."""
    lo, best, seen = 0, None, {}
    top = hi
    while lo < hi:
        mid = (lo + hi + 1) // 2
        r = run_case(f"{name}-{mid}", make(mid))
        seen[mid] = r
        if "trap" in r:
            hi = mid - 1
        else:
            lo, best = mid, r
    nxt = seen.get(lo + 1) or (run_case(f"{name}-{lo + 1}", make(lo + 1)) if lo < top else None)
    return {"case": name, "binary": a.binary, "stack": a.stack or "default", "max_ok": lo,
            "at_max": best and {k: best.get(k) for k in ("stdout", "fuel", "c_stack_used")},
            "above": nxt and {k: nxt.get(k) for k in ("trap", "stdout", "c_stack_used", "sp_used", "stderr_last")}}


def main():
    for name in a.cases or list(CASES):
        v = CASES[name]
        if isinstance(v, tuple):
            print(json.dumps(bisect(name, v[0], v[1])), flush=True)
        else:
            print(json.dumps(run_case(name, v)), flush=True)


try:
    # The wasm runs on this thread's own native stack: give it room beyond max_wasm_stack.
    if a.main_thread:
        main()
    else:
        threading.stack_size(max(64 << 20, 2 * (a.stack or 0)))
        t = threading.Thread(target=main)
        t.start()
        t.join()
finally:
    shutil.rmtree(work, ignore_errors=True)
