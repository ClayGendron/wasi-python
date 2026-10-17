"""Fuel for one guest, three ways to obtain the module, read after instantiate and after run.

usage: uv run python real.py <python.wasm or python-snapshot.wasm> <stdlib.zip> <scratch dir> [cow=0|1] [prog]

One engine (consume_fuel, epoch_interruption). The clock and random are answered by this script
(a fixed start and a step; a counter hashed with SHA-256), so every run sees the same inputs.
"""
import hashlib, itertools, mmap, shutil, struct, sys, time
from pathlib import Path
import wasmtime as wt

wasm, stdlib, scratch = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
cow = (sys.argv[4] if len(sys.argv) > 4 else "1") == "1"
prog = sys.argv[5] if len(sys.argv) > 5 else "pass"
scratch.mkdir(parents=True, exist_ok=True)
FUEL = 10**12

def leb(b, i):
    r = s = 0
    while True:
        x = b[i]; i += 1; r |= (x & 0x7F) << s; s += 7
        if x < 0x80: return r, i

def sleb(b, i):
    r = s = 0
    while True:
        x = b[i]; i += 1; r |= (x & 0x7F) << s; s += 7
        if x < 0x80:
            if x & 0x40: r -= 1 << s
            return r, i

def data_extent(b):
    """Active data segments of memory 0 with an i32.const offset: count, bytes, [lo, hi)."""
    i, n, lo, hi, total = 8, 0, None, 0, 0
    while i < len(b):
        sid = b[i]; size, i = leb(b, i + 1); end = i + size
        if sid == 11:
            cnt, j = leb(b, i)
            for _ in range(cnt):
                flags, j = leb(b, j)
                if flags == 1:  # passive
                    ln, j = leb(b, j); j += ln; continue
                if flags == 2: _, j = leb(b, j)
                assert b[j] == 0x41, "offset is not i32.const"
                off, j = sleb(b, j + 1); assert b[j] == 0x0B; j += 1
                ln, j = leb(b, j); j += ln
                n += 1; total += ln; lo = off if lo is None else min(lo, off); hi = max(hi, off + ln)
        i = end
    return n, total, lo, hi

def instance_fuel(engine, mod):
    root = scratch / "root"; shutil.rmtree(root, ignore_errors=True)
    (root / "usr/local/lib").mkdir(parents=True); (root / "tmp").mkdir()
    shutil.copyfile(stdlib, root / "usr/local/lib/python315.zip")
    store = wt.Store(engine); store.set_fuel(FUEL); store.set_epoch_deadline(2**62)
    w = wt.WasiConfig(); w.argv = ["/usr/local/bin/python.wasm", "-c", prog]
    w.env = [("HOME", "/tmp"), ("PYTHONTZPATH", ""), ("TMPDIR", "/tmp")]
    w.preopen_dir(str(root), "/"); w.stdout_file = str(scratch / "out"); w.stderr_file = str(scratch / "err")
    store.set_wasi(w)
    linker = wt.Linker(engine); linker.define_wasi(); linker.allow_shadowing = True
    i32, i64 = wt.ValType.i32(), wt.ValType.i64()
    ctr, ticks = itertools.count(), itertools.count(1)
    def rnd(c, buf, n):
        out = bytearray()
        while len(out) < n: out += hashlib.sha256(struct.pack("<Q", next(ctr))).digest()
        c.get("memory").write(c, bytes(out[:n]), buf); return 0
    def clk(c, cid, _p, out):
        v = (1_767_225_600_000_000_000 if cid == 0 else 0) + next(ticks) * 1000
        c.get("memory").write(c, struct.pack("<Q", v), out); return 0
    p1 = "wasi_snapshot_preview1"
    linker.define_func(p1, "random_get", wt.FuncType([i32, i32], [i32]), rnd, True)
    linker.define_func(p1, "clock_time_get", wt.FuncType([i32, i64, i32], [i32]), clk, True)
    linker.define_func("host", "call", wt.FuncType([i32] * 4, [i32]), lambda c, a, b, d, e: -1, True)
    t = time.perf_counter()
    ex = linker.instantiate(store, mod).exports(store)
    t_inst = time.perf_counter() - t
    after_inst = FUEL - store.get_fuel()
    try:
        if "_initialize" in ex: ex["_initialize"](store)
        code = ex["run"](store)
    except wt.ExitTrap as e:
        code = e.code
    total = FUEL - store.get_fuel()
    return after_inst, total - after_inst, total, code, (scratch / "out").read_bytes()[:40], t_inst

b = wasm.read_bytes()
n, total, lo, hi = data_extent(b)
page = mmap.PAGESIZE
img = ((hi + page - 1) // page) * page - (lo // page) * page
print(f"{wasm.name}: {n} active data segments, {total} bytes; extent [{lo}, {hi}); image at host page {page}: {img} bytes")
cfg = wt.Config(); cfg.consume_fuel = True; cfg.epoch_interruption = True; cfg.memory_init_cow = cow
engine = wt.Engine(cfg)
mod = wt.Module(engine, b)
ser = mod.serialize()
cw = scratch / "m.cwasm"; cw.write_bytes(ser)
print(f"memory_init_cow={cow} prog={prog!r}")
print("how                  | instantiate | after instantiate | total | exit | stdout | inst s")
for how, m in [("compiled", mod), ("deserialize(bytes)", wt.Module.deserialize(engine, ser)),
               ("deserialize_file", wt.Module.deserialize_file(engine, str(cw))), ("compiled again", mod)]:
    a, r, t, code, out, ti = instance_fuel(engine, m)
    print(f"{how:20} | {a:,} | {r:,} | {t:,} | {code} | {out!r} | {ti:.3f}")
