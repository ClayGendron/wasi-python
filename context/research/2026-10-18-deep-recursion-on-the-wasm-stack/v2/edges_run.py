"""Depth edges at one stack (spec 071 v2): per case, the largest depth that does not trap, with
the research snapshot's window (RESEARCH_C_STACK); runner-like engine (fuel, epoch) unless --bare.
Adapted from the pre-build review's fixed512.py. Usage: edges_run.py WASM CASEFILE [CASE ...] --hi KIB"""
import argparse, importlib.util, itertools, json, os, platform, shutil, struct, sys, tempfile, threading
from pathlib import Path
import wasmtime as wt

ap = argparse.ArgumentParser()
ap.add_argument("wasm"); ap.add_argument("casefile"); ap.add_argument("cases", nargs="*")
ap.add_argument("--zip", default="/Users/claygendron/Git/Repos/wasi_python/build/sets/s-4eb5418a2b1bb553-c353b1d9/python-stdlib.zip")
ap.add_argument("--window", type=int, default=131072)
ap.add_argument("--bare", action="store_true")
ap.add_argument("--nosig", action="store_true")
ap.add_argument("--lo", type=int, default=96); ap.add_argument("--hi", type=int, default=1024)  # KiB
a = ap.parse_args()
spec = importlib.util.spec_from_file_location("cases", a.casefile)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
CASES = m.CASES
work = Path(tempfile.mkdtemp(prefix="sm-"))
(work / "lib").mkdir(); shutil.copyfile(a.zip, work / "lib" / "python315.zip")
engines, mods = {}, {}

def module(stack):
    if stack not in engines:
        cfg = wt.Config(); cfg.consume_fuel = not a.bare; cfg.epoch_interruption = not a.bare
        cfg.max_wasm_stack = stack
        if a.nosig: cfg.signals_based_traps = False
        e = wt.Engine(cfg); engines[stack] = e
        cw = work / f"m-{int(a.bare)}-{int(a.nosig)}.cwasm"
        if cw.exists():
            mods[stack] = wt.Module.deserialize_file(e, str(cw))
        else:
            mod = wt.Module.from_file(e, a.wasm); cw.write_bytes(mod.serialize()); mods[stack] = mod
    return engines[stack], mods[stack]

def run(code, stack):
    engine, mod = module(stack)
    root = work / "root"; shutil.rmtree(root, ignore_errors=True); (root / "tmp").mkdir(parents=True)
    store = wt.Store(engine)
    if not a.bare:
        store.set_epoch_deadline(1 << 40); store.set_fuel(4 * 10**10)
    w = wt.WasiConfig(); w.argv = ["/usr/local/bin/python.wasm", "-c", code]
    w.env = [("HOME", "/tmp"), ("RESEARCH_C_STACK", str(a.window))] if a.window else [("HOME", "/tmp")]
    w.preopen_dir(str(work / "lib"), "/usr/local/lib", False); w.preopen_dir(str(root), "/")
    w.stdout_file = str(work / "out"); w.stderr_file = str(work / "err")
    store.set_wasi(w)
    lk = wt.Linker(engine); lk.define_wasi(); lk.allow_shadowing = True
    i32, i64 = wt.ValType.i32(), wt.ValType.i64(); t = itertools.count(1)
    def rg(c, b, n): c.get("memory").write(c, bytes((i * 7919) & 255 for i in range(n)), b); return 0
    def ct(c, cid, _p, o): c.get("memory").write(c, struct.pack("<Q", 1767225600000000000 + next(t) * 1000), o); return 0
    p1 = "wasi_snapshot_preview1"
    lk.define_func(p1, "random_get", wt.FuncType([i32, i32], [i32]), rg, True)
    lk.define_func(p1, "clock_time_get", wt.FuncType([i32, i64, i32], [i32]), ct, True)
    lk.define_func("host", "call", wt.FuncType([i32] * 4, [i32]), lambda c, *x: -1, True)
    ex = lk.instantiate(store, mod).exports(store)
    try:
        if "_initialize" in [e.name for e in mod.exports]: ex["_initialize"](store)
        ex["run"](store); trapped = None
    except wt.ExitTrap: trapped = None
    except wt.Trap as e: trapped = "trap"
    except wt.WasmtimeError as e: trapped = "error"
    out = (work / "out").read_text(errors="replace").strip().splitlines()
    return trapped, (out[-1] if out else "")

def main():
    """Bisect, per case, the largest depth N in [1, hi] whose run does not trap (runs are fresh
    instances; a trap at N means any deeper N traps too for these monotone shapes)."""
    for name in a.cases or list(CASES):
        make, hi = CASES[name]
        lo, top, last = 0, hi, None
        while lo < hi:
            mid = (lo + hi + 1) // 2
            tr, o = run(make(mid), a.hi * 1024)
            if tr:
                hi = mid - 1
            else:
                lo, last = mid, o
        above = run(make(lo + 1), a.hi * 1024) if lo < top else (None, "")
        print(json.dumps({"case": name, "stack_kib": a.hi, "max_ok": lo, "at_max": (last or "")[:70],
                          "above": ["trap" if above[0] else "ok", above[1][:70]],
                          "arch": platform.machine(), "window": a.window}), flush=True)

threading.stack_size(64 << 20); th = threading.Thread(target=main); th.start(); th.join()
shutil.rmtree(work, ignore_errors=True)
