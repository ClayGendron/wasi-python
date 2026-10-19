"""Spec 078's research: is the guest's fuel the same at a 512 KiB and an 8 MiB wasm stack, and on
the caller's thread and a thread of its own? Through the 078 worktree's judge driver (seeded
random, stepped clock), on main's set, each program once per configuration."""
import ctypes, json, os, sys, threading
from pathlib import Path
sys.path.insert(0, "/Users/claygendron/Git/Repos/wasi_python-078/tests")
import wasmtime as wt
from wasmtime import _ffi
from harness import guest
from checks.test_v1_2_hostile_guest import COUNTED, RECURSIONS

SET = Path(os.environ["SET"]); work = Path(os.environ["PROBE_TMP"]) / "fuel078"; work.mkdir(exist_ok=True)
PROGRAMS = {
    "hello": "print('hello')",
    "numpy": "import numpy as np; print(np.arange(10).sum())",
    "pandas-groupby": "import pandas as pd; print(pd.DataFrame({'a':[1,2,1],'b':[3,4,5]}).groupby('a').b.sum())",
    "repr-recursion": COUNTED.format(body=RECURSIONS["repr"][0]),
    "free-2000": "x = []\nfor i in range(2000): x = [x]\ndel x\nprint('ok')",
}
def engine(stack):
    cfg = wt.Config(); cfg.consume_fuel = True; cfg.epoch_interruption = True; cfg.max_wasm_stack = stack
    f = _ffi.dll.wasmtime_config_async_stack_size_set
    f.argtypes, f.restype = [ctypes.c_void_p, ctypes.c_size_t], None
    f(cfg.ptr(), max(stack, 2 << 20)); return wt.Engine(cfg)
res = {}
for stack in (524288, 8388608):
    guest._engine = engine(stack); guest._modules.clear()
    for where in ("caller", "own-thread"):
        for name, code in PROGRAMS.items():
            box = {}
            def go():
                r = guest.run(SET / "python-snapshot.wasm", ["-c", code], workdir=work, python_version="3.15.0",
                              stdlib=SET / "python-stdlib.zip", measured=False)
                box.update(fuel=r.fuel, out=r.stdout.decode()[-40:], trapped=r.trapped)
            if where == "caller":
                go()
            else:
                old = threading.stack_size(stack + (1 << 20)); t = threading.Thread(target=go); t.start(); threading.stack_size(old); t.join()
            res.setdefault(name, {})[f"{stack//1024}K/{where}"] = box["fuel"]
            assert box["trapped"] is None, box
for name, v in res.items():
    print(name.ljust(16), json.dumps(v), "same" if len(set(v.values())) == 1 else "DIFFERENT")
