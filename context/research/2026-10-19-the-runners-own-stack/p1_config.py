"""Probe 1: how wasmtime-py 49 takes max_wasm_stack above 2 MiB. Each case in its own process:
wasmtime-py's Engine() unwraps the config's validation, so a bad one aborts the process."""
import ctypes, subprocess, sys

CASE = r'''
import ctypes, sys, wasmtime as wt
from wasmtime import _ffi
size, extra = int(sys.argv[1]), int(sys.argv[2])
cfg = wt.Config(); cfg.consume_fuel = True; cfg.epoch_interruption = True
cfg.max_wasm_stack = size
if extra >= 0:
    f = _ffi.dll.wasmtime_config_async_stack_size_set
    f.argtypes = [ctypes.c_void_p, ctypes.c_size_t]; f.restype = None
    f(cfg.ptr(), size + extra)
wt.Engine(cfg)
print("engine made", flush=True)
'''
if __name__ == "__main__":
    import wasmtime as wt
    from wasmtime import _ffi
    print("python setter for async_stack_size:", hasattr(wt.Config, "async_stack_size"))
    print("library exports wasmtime_config_async_stack_size_set:", hasattr(_ffi.dll, "wasmtime_config_async_stack_size_set"))
    for size in (512 << 10, 2 << 20, (2 << 20) + 4096, 8 << 20, 16 << 20):
        for extra in (-1, 0, 1 << 20):
            r = subprocess.run([sys.executable, "-c", CASE, str(size), str(extra)], capture_output=True, text=True)
            what = "plain config" if extra < 0 else f"async_stack_size = max_wasm_stack + {extra}"
            msg = (r.stdout.strip() or r.stderr.strip().splitlines()[1] if r.stderr.strip() else "")
            print(f"max_wasm_stack {size:>9}  {what:<40} exit {r.returncode:>4}  {msg}")
