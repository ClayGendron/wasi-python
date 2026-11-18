"""wasmtime-py (the wheel's engine) running the copy-on-write pandas module, to see whether the
wheel can get the copy-on-write start without moving onto the Rust core."""
import os, sys, time, json, statistics, tempfile, threading, wasmtime as w
def main():
    wasm, cwasm, lib, root, code, n = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], int(sys.argv[6])
    from wasi_python import _wasmtime_ffi as ffi
    c = w.Config(); c.epoch_interruption = True; ffi.set_async_stack(c, 8 << 20); c.max_wasm_stack = 8 << 20; c.memory_init_cow = True
    e = w.Engine(c)
    t = time.perf_counter()
    if not os.path.exists(cwasm):
        m = w.Module.from_file(e, wasm); open(cwasm, "wb").write(m.serialize()); comp = (time.perf_counter() - t) * 1e3
    else:
        comp = None
    t = time.perf_counter(); m = w.Module.deserialize_file(e, cwasm); load = (time.perf_counter() - t) * 1e3
    link = w.Linker(e); link.define_wasi()
    link.define_func("host", "call", w.FuncType([w.ValType.i32()] * 4, [w.ValType.i32()]), lambda a, b, c_, d: -1)
    xs, out = [], ""
    for i in range(n):
        fd, of = tempfile.mkstemp(dir=os.environ.get("TMPOUT")); os.close(fd)
        t0 = time.perf_counter()
        s = w.Store(e); s.set_epoch_deadline(1 << 40)
        wc = w.WasiConfig(); wc.argv = ["python", "-c", code]
        wc.env = [("TMPDIR", "/tmp"), ("PYTHONTZPATH", ""), ("HOME", "/tmp/.home-snapshot")]
        wc.preopen_dir(lib, "/usr/local/lib", False); wc.preopen_dir(root, "/", True)
        wc.stdout_file = of; wc.stderr_file = of
        s.set_wasi(wc)
        inst = link.instantiate(s, m)
        try:
            inst.exports(s)["run"](s)
        except w.ExitTrap:
            pass
        del inst, s
        xs.append((time.perf_counter() - t0) * 1e3)
        out = open(of).read(); os.unlink(of)
    print(json.dumps({"compile_ms": comp, "load_ms": round(load, 1), "total_med_ms": round(statistics.median(xs), 2), "total_first_ms": round(xs[0], 2), "out": out[:120]}))

threading.stack_size(64 << 20); t_=threading.Thread(target=main); t_.start(); t_.join()
