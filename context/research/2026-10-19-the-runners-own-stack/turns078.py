"""Spec 078's research: a session's store driven from a different thread each turn (opened on the
main thread, turns on fresh threads with 9 MiB stacks at an 8 MiB wasm stack): state persists and
fuel matches the same turns on one thread. Through the 078 worktree's judge driver."""
import ctypes, json, os, sys, threading
from pathlib import Path
sys.path.insert(0, "/Users/claygendron/Git/Repos/wasi_python-078/tests")
import wasmtime as wt
from wasmtime import _ffi
from harness import guest

SET = Path(os.environ["SET"]); work = Path(os.environ["PROBE_TMP"]) / "turns078"; work.mkdir(exist_ok=True)
cfg = wt.Config(); cfg.consume_fuel = True; cfg.epoch_interruption = True; cfg.max_wasm_stack = 8 << 20
f = _ffi.dll.wasmtime_config_async_stack_size_set
f.argtypes, f.restype = [ctypes.c_void_p, ctypes.c_size_t], None
f(cfg.ptr(), 8 << 20); guest._engine = wt.Engine(cfg)
CODE = ["x = 41", "import numpy as np; y = np.arange(5)", "x += 1; print(x, y.sum())",
        "z = []\nfor i in range(20000): z = [z]\ndel z\nprint('freed 20000')"]
def drive(hop):
    t = guest.turns(SET / "python-snapshot.wasm", workdir=work, python_version="3.15.0", stdlib=SET / "python-stdlib.zip")
    out = []
    for code in CODE:
        box = {}
        def go(): box["r"] = t.turn(code)
        if hop:
            old = threading.stack_size(9 << 20); th = threading.Thread(target=go); th.start(); threading.stack_size(old); th.join()
        else:
            go()
        r = box["r"]; out.append((r.value, r.trapped, (10**11 - t.store.get_fuel()) if False else t.store.get_fuel(), r.stdout.decode().strip()))
    return out
a, b = drive(False), drive(True)
for (x, y) in zip(a, b):
    print(json.dumps({"one_thread": x, "thread_per_turn": y, "same": x == y}))
