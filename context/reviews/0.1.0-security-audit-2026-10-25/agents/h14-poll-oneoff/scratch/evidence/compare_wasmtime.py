"""Bounded local check (h14-poll-oneoff): the same raw poll_oneoff calls answered by wasmtime-py
49.0.0's own WASI poll_oneoff (no shadow) and by the runner's shadow (_call._poll_oneoff on a
linker that shadows only poll_oneoff, as in the project's own unit test), to record where the
shadow's answers differ from wasmtime's. Only memory-relevant outcome: whether anything outside
the event and nevents regions changed. A scratch folder is preopened at fd 3."""
import json, struct, sys
from pathlib import Path
import wasmtime as wt
sys.path.insert(0, "./src")
from wasi_python import _call

S = Path(sys.argv[1]); d = S / "work" / "pre3"; d.mkdir(parents=True, exist_ok=True)
WAT = """(module
  (import "wasi_snapshot_preview1" "poll_oneoff" (func $p (param i32 i32 i32 i32) (result i32)))
  (memory (export "memory") 1)
  (func (export "poll") (param i32 i32 i32 i32) (result i32)
    (call $p (local.get 0) (local.get 1) (local.get 2) (local.get 3))))"""
def clock(ud, cid, t, flags=0): return struct.pack("<QB7xIxxxxQQH6x", ud, 0, cid, t, 0, flags)
def fdsub(ud, tag, fd): return struct.pack("<QB7xI28x", ud, tag, fd)
CASES = [("aligned clock", clock(1,1,0), 1024, 8192, 64), ("misaligned in_ptr", clock(1,1,0), 1025, 8192, 64),
         ("misaligned out_ptr", clock(1,1,0), 1024, 8193, 64), ("misaligned nevents_ptr", clock(1,1,0), 1024, 8192, 65),
         ("unknown tag 3", struct.pack("<QB39x",1,3), 1024, 8192, 64), ("clock id 2", clock(1,2,0), 1024, 8192, 64),
         ("clock id 9", clock(1,9,0), 1024, 8192, 64), ("flags 0xFFFE", clock(1,1,0,0xFFFE), 1024, 8192, 64),
         ("fd_read 3 (preopened dir)", fdsub(1,1,3), 1024, 8192, 64), ("fd_read 99 (no such fd)", fdsub(1,1,99), 1024, 8192, 64),
         ("fd_read stdin", fdsub(1,1,0), 1024, 8192, 64), ("out_ptr 65535-31 (no room)", clock(1,1,0), 1024, 65536-31, 64)]
def one(shadow, sub, i, o, nv):
    engine = wt.Engine(); store = wt.Store(engine); linker = wt.Linker(engine); linker.define_wasi()
    w = wt.WasiConfig(); w.preopen_dir(str(d), "/d"); store.set_wasi(w)
    if shadow:
        linker.allow_shadowing = True
        f = _call._poll_oneoff(0, _call._Waits(lambda: 0.0, lambda s: None, None))
        linker.define_func("wasi_snapshot_preview1", "poll_oneoff", wt.FuncType([wt.ValType.i32()]*4, [wt.ValType.i32()]), f, True)
    ex = linker.instantiate(store, wt.Module(engine, WAT)).exports(store); m = ex["memory"]
    m.write(store, b"\xaa" * 65536, 0); m.write(store, sub, i); before = bytes(m.read(store, 0, 65536))
    try: r = ex["poll"](store, i, o, 1, nv)
    except (wt.Trap, wt.WasmtimeError) as e: r = "ends run: " + str(e).strip().splitlines()[0][:120]
    after = bytes(m.read(store, 0, 65536)); ch = [k for k in range(65536) if before[k] != after[k]]
    ok = set(range(o, o+32)) | set(range(nv, nv+4))
    return {"answer": r, "changed": len(ch), "changed_outside": len([k for k in ch if k not in ok])}
rows = [{"case": c, "wasmtime": one(False, *a), "shadow": one(True, *a)} for c, *a in CASES]
for r in rows: print(json.dumps(r))
json.dump(rows, open(S / "evidence" / "compare_wasmtime.json", "w"), indent=1)
