"""Fork after wasmtime was used in the parent by code other than wasi_python, then a guest
trap in the child. argv[1]: 'control' (parent only imports) or 'foreign' (parent makes an
Engine and runs a wasm function through wasmtime-py directly)."""
import json, os, sys
import wasmtime
import wasi_python
from wasi_python._process import process

mode = sys.argv[1]
if mode == "foreign":
    eng = wasmtime.Engine()
    store = wasmtime.Store(eng)
    mod = wasmtime.Module(eng, '(module (func (export "f") (result i32) i32.const 7))')
    inst = wasmtime.Instance(store, mod, [])
    print(json.dumps({"parent_foreign_wasm": inst.exports(store)["f"](store),
                      "fork_used": process().fork_used}), flush=True)
GUEST = ("import numpy as np\nfrom numpy.lib.stride_tricks import as_strided\n"
         "a = np.zeros(1, dtype=np.uint8)\n"
         "b = as_strided(a, shape=(2,), strides=(0x7ff00000,))\n"
         "print(int(b[1]))\n")
pid = os.fork()
if pid == 0:
    try:
        ok = wasi_python.run(["-c", "print('ok')"], deadline_s=60)
        print(json.dumps({"child_normal": [ok.exit_code, ok.trapped]}), flush=True)
        done = wasi_python.run(["-c", GUEST], deadline_s=60)
        print(json.dumps({"child_oob": [done.exit_code, done.trapped]}), flush=True)
    except BaseException as e:
        print(json.dumps({"child_raised": type(e).__name__ + ": " + str(e)[:120]}), flush=True)
    os._exit(0)
_, status = os.waitpid(pid, 0)
print(json.dumps({"mode": mode, "child_wait_status": status,
                  "signalled": os.WIFSIGNALED(status),
                  "signal": os.WTERMSIG(status) if os.WIFSIGNALED(status) else None,
                  "exit": os.WEXITSTATUS(status) if os.WIFEXITED(status) else None}), flush=True)
