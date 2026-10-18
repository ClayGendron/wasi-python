"""Probe harness for spec 055's addendum: one snapshot instance, driven by hand through wasmtime-py."""
import os, sys, time, threading
import wasmtime as wt
from pathlib import Path

S = Path(__file__).resolve().parent.parent
ART = S / "artifacts"
ZIPDIR = S / "probes" / "zipdir"

ENGINES = {}
def engine(metered=True):
    if metered not in ENGINES:
        cfg = wt.Config(); cfg.consume_fuel = metered; cfg.epoch_interruption = True
        ENGINES[metered] = wt.Engine(cfg)
    return ENGINES[metered]

MODS = {}
def module(metered=True, snapshot=True):
    k = (metered, snapshot)
    if k not in MODS:
        path = ART / ("python-snapshot.wasm" if snapshot else "python.wasm")
        cache = S / "cache" / f"{'snap' if snapshot else 'plain'}-{'fuel' if metered else 'nofuel'}.cwasm"
        if cache.exists():
            MODS[k] = wt.Module.deserialize_file(engine(metered), str(cache))
        else:
            m = wt.Module.from_file(engine(metered), str(path)); cache.write_bytes(m.serialize()); MODS[k] = m
    return MODS[k]

class Guest:
    def __init__(self, door=None, argv=("python",), metered=True, memory_bytes=None, stdout=None, snapshot=True):
        from wasi_python import runner as R
        self.R = R
        e = engine(metered)
        self.store = wt.Store(e)
        if metered:
            self.store.set_fuel(2**63 - 1)
        if memory_bytes is not None:
            self.store.set_limits(memory_size=memory_bytes)
        self.store.set_epoch_deadline(2**62)
        w = wt.WasiConfig()
        w.argv = list(argv)
        w.env = [("TMPDIR", "/tmp"), ("PYTHONTZPATH", "")]
        w.preopen_dir(str(ZIPDIR), "/usr/local/lib", wt.DirPerms.READ_ONLY, wt.FilePerms.READ_ONLY) if hasattr(wt, "DirPerms") else w.preopen_dir(str(ZIPDIR), "/usr/local/lib")
        self.out, self.err = R._Stream("stdout", None), R._Stream("stderr", None)
        self.keys = R._send_outputs(w, self.out, self.err)
        self.store.set_wasi(w)
        L = wt.Linker(e); L.define_wasi(); L.allow_shadowing = True
        i32 = wt.ValType.i32()
        ty = wt.FuncType([i32] * 4, [i32])
        self.door_fn = door
        def call(caller, ptr, ln, optr, olen):
            if self.door_fn is None:
                return -1
            mem = caller["memory"]; alloc = caller["host_alloc"]
            req = bytes(mem.read(caller, ptr, ptr + ln))
            resp = self.door_fn(caller, req)
            p = alloc(caller, len(resp)) if resp else 0
            if resp:
                mem.write(caller, resp, p)
            import struct
            mem.write(caller, struct.pack("<I", p), optr)
            mem.write(caller, struct.pack("<I", len(resp)), olen)
            return 0
        L.define_func("host", "call", ty, call, True)
        self.inst = L.instantiate(self.store, module(metered, snapshot))
        self.ex = self.inst.exports(self.store)

    def mem_bytes(self):
        return self.ex["memory"].data_len(self.store)

    def swap_streams(self):
        """Point the store's stdout/stderr keys at fresh streams; return the old ones."""
        R = self.R
        new_out, new_err = R._Stream("stdout", None), R._Stream("stderr", None)
        with R._outputs_lock:
            old = R._outputs[self.keys[0]], R._outputs[self.keys[1]]
            R._outputs[self.keys[0]], R._outputs[self.keys[1]] = new_out, new_err
        self.out, self.err = new_out, new_err
        return old

    def close(self):
        self.store.close()
