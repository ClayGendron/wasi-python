"""Spec 078's research: CPython test modules or single tests through the judge's guest driver (the
078 worktree's, read only), on main's set, on the runner's engine (fuel and epoch interruption)
with a chosen wasm stack, on a 64 MiB thread. Usage: cpy078.py STACK LABEL -- <regrtest args>"""
import ctypes, json, os, shutil, sys, threading
from pathlib import Path

WT = Path("/Users/claygendron/Git/Repos/wasi_python-078")
SET = Path(os.environ["SET"])
STAGE = Path("/Users/claygendron/Git/Repos/wasi_python/build/cpython-suite-research/stage")
sys.path.insert(0, str(WT / "tests"))
import wasmtime as wt  # noqa: E402
from wasmtime import _ffi  # noqa: E402
from harness import guest  # noqa: E402

stack, label = int(sys.argv[1]), sys.argv[2]
args = sys.argv[4:] if sys.argv[3:4] == ["--"] else sys.argv[3:]
cfg = wt.Config(); cfg.consume_fuel = True; cfg.epoch_interruption = True
cfg.max_wasm_stack = stack
f = _ffi.dll.wasmtime_config_async_stack_size_set
f.argtypes, f.restype = [ctypes.c_void_p, ctypes.c_size_t], None
f(cfg.ptr(), max(stack, 2 << 20))
guest._engine = wt.Engine(cfg)
wasm = SET / "python-snapshot.wasm"
cw = Path(os.environ["CWASM_DIR"]) / "snapshot-fuel-epoch.cwasm"
mod = wt.Module.deserialize_file(guest._engine, str(cw)) if cw.exists() else wt.Module.from_file(guest._engine, str(wasm))
if not cw.exists():
    cw.write_bytes(mod.serialize())
st = wasm.stat()
guest._modules[(str(wasm.resolve()), st.st_size, st.st_mtime_ns)] = mod
work = Path(os.environ["PROBE_TMP"]) / f"cpywork-{os.getpid()}"
work.mkdir(parents=True, exist_ok=True)
out = {}

def go():
    r = guest.run(wasm, ["-u", "/cpy/judge/drive.py", *args], workdir=work, python_version="3.15.0",
                  stdlib=SET / "python-stdlib.zip", env={"TMPDIR": "/tmp", "HOME": "/tmp"},
                  fuel=4 * 10**11, preopens=[("/cpy", STAGE, False)], mpl_data=True, measured=False)
    lines = r.stdout.decode(errors="replace").strip().splitlines()
    if os.environ.get("DUMP"):
        Path(os.environ["DUMP"]).write_text("\n".join(lines))
    keep = [l for l in lines if l.lstrip().startswith(("FAIL", "ERROR", "Total tests", "Result:", "RecursionError", "test_")) and ("FAIL" in l or "ERROR" in l or "Total" in l or "Result" in l)]
    out.update(label=label, stack=stack, exit=r.exit_code, trapped=r.trapped, cause=r.trap_cause,
               fuel=r.fuel, tail=keep[-6:])

threading.stack_size(64 << 20)
t = threading.Thread(target=go); t.start(); t.join()
shutil.rmtree(work, ignore_errors=True)
print(json.dumps(out), flush=True)
