"""Run CPython test modules (or single tests) through the judge's guest driver on a chosen binary,
wasm stack and C-stack guard window. Research only.

uv run python cpy071.py --wasm W --cwasm C [--stack B] [--guard B] LABEL -- <regrtest args>
"""
import argparse, ctypes, json, os, shutil, sys, threading
from pathlib import Path

REPO = Path("/Users/claygendron/Git/Repos/wasi_python")
SET = REPO / "build/sets/s-4eb5418a2b1bb553-c353b1d9"
STAGE = REPO / "build/cpython-suite-research/stage"
sys.path.insert(0, "/Users/claygendron/Git/Repos/wasi_python-071/tests")
import wasmtime as wt  # noqa: E402
from harness import guest  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--wasm", required=True)
ap.add_argument("--cwasm", required=True)
ap.add_argument("--stack", type=int, default=0)
ap.add_argument("--guard", type=int, default=0)
ap.add_argument("label")
ap.add_argument("rest", nargs=argparse.REMAINDER)
a = ap.parse_args()
args = a.rest[1:] if a.rest[:1] == ["--"] else a.rest

cfg = wt.Config()
cfg.consume_fuel = True
if a.stack:
    from wasmtime import _ffi
    f = _ffi.dll.wasmtime_config_async_stack_size_set
    f.argtypes, f.restype = [ctypes.c_void_p, ctypes.c_size_t], None
    f(ctypes.cast(cfg.ptr(), ctypes.c_void_p), a.stack)
    cfg.max_wasm_stack = a.stack
guest._engine = wt.Engine(cfg)
wasm = Path(a.wasm)
if Path(a.cwasm).exists():
    mod = wt.Module.deserialize_file(guest._engine, a.cwasm)
else:
    mod = wt.Module.from_file(guest._engine, str(wasm))
    Path(a.cwasm).write_bytes(mod.serialize())
st = wasm.stat()
guest._modules[(str(wasm.resolve()), st.st_size, st.st_mtime_ns)] = mod
env = {"TMPDIR": "/tmp", "HOME": "/tmp"}
if a.guard:
    env["RESEARCH_C_STACK"] = str(a.guard)
work = Path(os.environ["PROBE_TMP"]) / "cpywork"
work.mkdir(parents=True, exist_ok=True)
out = {}

def go():
    r = guest.run(wasm, ["-u", "/cpy/judge/drive.py", *args], workdir=work, python_version="3.15.0",
                  stdlib=SET / "python-stdlib.zip", env=env, fuel=4 * 10**11,
                  preopens=[("/cpy", STAGE, False)], mpl_data=True)
    lines = r.stdout.decode(errors="replace").strip().splitlines(); tail = [l for l in lines if l.startswith(("FAIL:", "ERROR:", "AssertionError", "RecursionError"))][:12] + lines[-4:]
    out.update(label=a.label, stack=a.stack or "default", guard=a.guard or "none", exit=r.exit_code,
               trapped=r.trapped, cause=r.trap_cause, fuel=r.fuel, tail=tail)
    shutil.rmtree(r.root.parent, ignore_errors=True)

threading.stack_size(max(64 << 20, 2 * a.stack))
t = threading.Thread(target=go); t.start(); t.join()
print(json.dumps(out))
