"""Spec 078's research: per case, the largest depth that does not trap, on main's set (the snapshot,
its 128 KiB window built in), on the runner's engine (fuel, epoch interruption) at a given wasm
stack, on a 64 MiB thread. Usage: edges8.py SET STACK [CASE ...]"""
import ctypes, importlib.util, itertools, json, os, platform, shutil, struct, sys, tempfile, threading
from pathlib import Path
import wasmtime as wt
from wasmtime import _ffi

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("cases078", HERE / "cases078.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
SET, STACK = Path(sys.argv[1]), int(sys.argv[2])
NAMES = sys.argv[3:] or list(m.CASES)
work = Path(tempfile.mkdtemp(prefix="e8-", dir=os.environ.get("PROBE_TMP")))
(work / "lib").mkdir(); shutil.copyfile(SET / "python-stdlib.zip", work / "lib" / "python315.zip")
cfg = wt.Config(); cfg.consume_fuel = True; cfg.epoch_interruption = True; cfg.max_wasm_stack = STACK
f = _ffi.dll.wasmtime_config_async_stack_size_set
f.argtypes, f.restype = [ctypes.c_void_p, ctypes.c_size_t], None
f(cfg.ptr(), max(STACK, 2 << 20))
engine = wt.Engine(cfg)
cw = Path(os.environ["CWASM_DIR"]) / f"snapshot-fuel-epoch-{platform.machine()}.cwasm"
if cw.exists():
    mod = wt.Module.deserialize_file(engine, str(cw))
else:
    mod = wt.Module.from_file(engine, str(SET / "python-snapshot.wasm")); cw.write_bytes(mod.serialize())

def run(code):
    root = work / "root"; shutil.rmtree(root, ignore_errors=True); (root / "tmp").mkdir(parents=True)
    store = wt.Store(engine); store.set_epoch_deadline(1 << 40); store.set_fuel(10**11)
    w = wt.WasiConfig(); w.argv = ["/usr/local/bin/python.wasm", "-c", code]; w.env = [("HOME", "/tmp")]
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
    trapped = None
    try:
        ex["run"](store)
    except wt.ExitTrap:
        pass
    except wt.Trap as e:
        trapped = "trap: " + " | ".join(l for l in str(e).splitlines() if "wasm trap" in l or "unreachable" in l or "exhausted" in l)[:120]
    except wt.WasmtimeError as e:
        trapped = "error: " + str(e).splitlines()[0][:60]
    store.close() if hasattr(store, "close") else None
    out = (work / "out").read_text(errors="replace").strip().splitlines()
    return trapped, (out[-1] if out else "")

def main_old():
    for name in NAMES:
        make, hi = m.CASES[name]
        top_tr, top_out = run(make(hi))
        if not top_tr:
            res = {"case": name, "max_ok": hi, "unbounded_to": hi, "at_max": top_out[:90]}
        else:
            lo, last = 0, None
            h = hi - 1
            while lo < h:
                mid = (lo + h + 1) // 2
                tr, o = run(make(mid))
                if tr: h = mid - 1
                else: lo, last = mid, o
            res = {"case": name, "max_ok": lo, "at_max": (last or "")[:90], "above": top_tr}
        res.update(stack=STACK, arch=platform.machine())
        print(json.dumps(res), flush=True)


def main():
    for spec in NAMES:
        name, n = spec.split(":")
        make, hi = m.CASES[name]
        tr, out = run(make(int(n)))
        print(json.dumps({"case": name, "n": int(n), "trapped": tr, "out": out[:100], "stack": STACK}), flush=True)

threading.stack_size(64 << 20); th = threading.Thread(target=main); th.start(); th.join()
shutil.rmtree(work, ignore_errors=True)
