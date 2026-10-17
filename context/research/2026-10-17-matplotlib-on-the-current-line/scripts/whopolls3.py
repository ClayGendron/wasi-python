"""Decode the first poll_oneoff subscription during start-up; return 'no event' a few times."""
import struct, sys, wasmtime as wt
eng = wt.Engine(wt.Config())
mod = wt.Module.from_file(eng, sys.argv[1])
store = wt.Store(eng); w = wt.WasiConfig(); w.argv = ["python.wasm", "-c", "print(1)"]; store.set_wasi(w)
lk = wt.Linker(eng); lk.define_wasi(); lk.allow_shadowing = True
i32 = wt.ValType.i32(); n = [0]
def poll(caller, inp, out, nsub, nevents):
    mem = caller.get("memory"); raw = bytes(mem.read(caller, inp, inp + 48 * nsub))
    for k in range(nsub):
        s = raw[48 * k: 48 * (k + 1)]
        ud, tag = struct.unpack_from("<QB", s)
        cid, timeout, prec, flags = struct.unpack_from("<IQQH", s, 16)
        print("sub", k, "userdata", ud, "tag", tag, "clock", cid, "timeout", timeout, "flags", flags, flush=True)
    n[0] += 1
    if n[0] > 50:
        raise wt.Trap("stop")
    mem.write(caller, struct.pack("<I", 0), nevents)
    return 58
lk.define_func("wasi_snapshot_preview1", "poll_oneoff", wt.FuncType([i32]*4, [i32]), poll, True)
lk.define_func("host", "call", wt.FuncType([i32]*4, [i32]), lambda *a: -1, True)
inst = lk.instantiate(store, mod)
try:
    inst.exports(store)["_initialize"](store); print("_initialize returned")
except Exception as e:
    print(type(e).__name__, str(e)[:6000])
