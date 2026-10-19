"""Spec 078's research: what a wider C-stack window buys at an 8 MiB wasm stack, and what it costs
at 512 KiB. The research plain binary (main's recipe plus research_guard, relink/) reads its window
from RESEARCH_C_STACK at run(); absent, the recipe's 128 KiB. Runner's engine (fuel, epoch), 64 MiB
thread. Rows: spec 071's criterion-1 programs (imported from the 078 worktree's checks) and data
shapes. Usage: window078.py BINARY STACK WINDOW|none [ROW ...]"""
import ctypes, itertools, json, os, platform, shutil, struct, sys, tempfile, threading
from pathlib import Path
import wasmtime as wt
from wasmtime import _ffi

sys.path.insert(0, "/Users/claygendron/Git/Repos/wasi_python-078/tests")
from checks.test_v1_2_hostile_guest import COUNTED, RECURSIONS  # noqa: E402

BIN, STACK, WINDOW = Path(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
SET = Path(os.environ["SET"])
DATA = {
    "data-json-loads": "import json\nmark()\ndef go(): json.loads('[' * 400000 + ']' * 400000)",
    "data-eq-list": "x = []\nfor i in range(400000): x = [x]\ny = []\nfor i in range(400000): y = [y]\nmark()\ndef go(): x == y",
    "data-repr-list": "x = []\nfor i in range(400000): x = [x]\nmark()\ndef go(): repr(x)",
    "data-json-dumps": "import json\nx = []\nfor i in range(400000): x = [x]\nmark()\ndef go(): json.dumps(x)",
    "expat": ("import xml.parsers.expat as E\ndef h(name, attrs):\n    mark()\n"
              "    p = E.ParserCreate(); p.StartElementHandler = h; p.Parse('<a/>', True)\ndef go(): h(None, None)"),
    "sax": ("import xml.sax\nclass H(xml.sax.ContentHandler):\n    def startElement(self, n, a):\n"
            "        mark(); xml.sax.parseString(b'<a/>', H())\ndef go(): xml.sax.parseString(b'<a/>', H())"),
}
ROWS = sys.argv[4:] or ["repr", "getattr", "eq", "lru-cache", "heapq", "sorted-key", "map", "re-sub",
                        "pickle-reduce", "np-frompyfunc", "np-vectorize", "lxml-target", *DATA]
PROG = {**{k: v[0] for k, v in RECURSIONS.items()}, **DATA}
work = Path(tempfile.mkdtemp(prefix="w8-", dir=os.environ.get("PROBE_TMP")))
(work / "lib").mkdir(); shutil.copyfile(SET / "python-stdlib.zip", work / "lib" / "python315.zip")
cfg = wt.Config(); cfg.consume_fuel = True; cfg.epoch_interruption = True; cfg.max_wasm_stack = STACK
f = _ffi.dll.wasmtime_config_async_stack_size_set
f.argtypes, f.restype = [ctypes.c_void_p, ctypes.c_size_t], None
f(cfg.ptr(), max(STACK, 2 << 20))
engine = wt.Engine(cfg)
cw = Path(os.environ["CWASM_DIR"]) / f"{BIN.parent.name}-plain-fuel-epoch-{platform.machine()}.cwasm"
mod = wt.Module.deserialize_file(engine, str(cw)) if cw.exists() else wt.Module.from_file(engine, str(BIN))
if not cw.exists():
    cw.write_bytes(mod.serialize())

def run(code):
    root = work / "root"; shutil.rmtree(root, ignore_errors=True); (root / "tmp").mkdir(parents=True)
    store = wt.Store(engine); store.set_epoch_deadline(1 << 40); store.set_fuel(2 * 10**11)
    w = wt.WasiConfig(); w.argv = ["/usr/local/bin/python.wasm", "-c", code]
    env = [("HOME", "/tmp")] + ([] if WINDOW == "none" else [("RESEARCH_C_STACK", WINDOW)])
    w.env = env
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
        ex["_initialize"](store); ex["run"](store)
    except wt.ExitTrap:
        pass
    except wt.Trap as e:
        trapped = " | ".join(l.strip() for l in str(e).splitlines() if "wasm trap" in l)[:80] or "trap"
    except wt.WasmtimeError as e:
        trapped = "error: " + str(e).splitlines()[0][:60]
    out = (work / "out").read_text(errors="replace").strip().splitlines()
    return trapped, (out[-1] if out else "")

def main():
    for row in ROWS:
        code = COUNTED.format(body=PROG[row]) + "\nimport sys, os; sys.stdout.flush(); os._exit(0)\n"
        tr, out = run(code)
        print(json.dumps({"row": row, "stack": STACK, "window": WINDOW, "trapped": tr, "out": out[:100],
                          "arch": platform.machine()}), flush=True)

threading.stack_size(64 << 20); th = threading.Thread(target=main); th.start(); th.join()
shutil.rmtree(work, ignore_errors=True)
