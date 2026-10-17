"""Trap on the first poll_oneoff, to see which code sleeps during start-up."""
import sys, wasmtime as wt
eng = wt.Engine(wt.Config())
mod = wt.Module.from_file(eng, sys.argv[1])
store = wt.Store(eng); w = wt.WasiConfig(); w.argv = ["python.wasm", "-c", "print(1)"]; store.set_wasi(w)
lk = wt.Linker(eng); lk.define_wasi(); lk.allow_shadowing = True
i32 = wt.ValType.i32()
def poll(caller, a, b, c, d):
    raise wt.Trap("poll_oneoff called")
lk.define_func("wasi_snapshot_preview1", "poll_oneoff", wt.FuncType([i32]*4, [i32]), poll, True)
lk.define_func("host", "call", wt.FuncType([i32]*4, [i32]), lambda *a: -1, True)
inst = lk.instantiate(store, mod)
try:
    inst.exports(store)["_initialize"](store)
    print("_initialize returned")
except Exception as e:
    print(type(e), str(e)[:200]); [print(f.func_name, f.func_index) for f in (getattr(e, "frames", None) or [])]
