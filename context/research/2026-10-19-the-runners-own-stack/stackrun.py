"""One guest through wasi_python.run, with the runner's wasm stack set to W, on a thread of T bytes
(or the main thread). Prints one JSON line. Used by the probes of spec 078's research; it patches
the runner in this process only (research, not a design)."""
import ctypes, json, os, sys, threading

def thread_stack_bytes() -> int | None:
    """The calling thread's real stack size, from the C library."""
    try:
        if sys.platform == "darwin":
            libc = ctypes.CDLL(None)
            libc.pthread_self.restype = ctypes.c_void_p
            libc.pthread_get_stacksize_np.restype = ctypes.c_size_t
            libc.pthread_get_stacksize_np.argtypes = [ctypes.c_void_p]
            return libc.pthread_get_stacksize_np(libc.pthread_self())
        if sys.platform.startswith("linux"):
            libc = ctypes.CDLL(None)
            libc.pthread_self.restype = ctypes.c_void_p
            attr = (ctypes.c_char * 256)()
            if libc.pthread_getattr_np(ctypes.c_void_p(libc.pthread_self()), attr) != 0:
                return None
            size = ctypes.c_size_t(); addr = ctypes.c_void_p()
            libc.pthread_attr_getstack(attr, ctypes.byref(addr), ctypes.byref(size))
            libc.pthread_attr_destroy(attr)
            return size.value
    except Exception:
        return None
    return None

def stack_bounds():
    """(low, high) of the calling thread's usable stack, from the C library (Linux, macOS)."""
    libc = ctypes.CDLL(None)
    libc.pthread_self.restype = ctypes.c_void_p
    if sys.platform == "darwin":
        libc.pthread_get_stackaddr_np.restype = ctypes.c_void_p
        libc.pthread_get_stackaddr_np.argtypes = [ctypes.c_void_p]
        libc.pthread_get_stacksize_np.restype = ctypes.c_size_t
        libc.pthread_get_stacksize_np.argtypes = [ctypes.c_void_p]
        high = libc.pthread_get_stackaddr_np(libc.pthread_self())
        return high - libc.pthread_get_stacksize_np(libc.pthread_self()), high
    attr = (ctypes.c_char * 256)()
    assert libc.pthread_getattr_np(ctypes.c_void_p(libc.pthread_self()), attr) == 0
    size = ctypes.c_size_t(); addr = ctypes.c_void_p(); guard = ctypes.c_size_t()
    libc.pthread_attr_getstack(attr, ctypes.byref(addr), ctypes.byref(size))
    libc.pthread_attr_getguardsize(attr, ctypes.byref(guard))
    libc.pthread_attr_destroy(attr)
    return addr.value + guard.value, addr.value + size.value

def protect():
    """Tell the host interpreter this thread's real stack (CPython 3.14+)."""
    f = getattr(ctypes.pythonapi, "PyUnstable_ThreadState_SetStackProtection", None)
    if f is None:
        return "absent"
    low, high = stack_bounds()
    ctypes.pythonapi.PyThreadState_Get.restype = ctypes.c_void_p
    f.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]; f.restype = ctypes.c_int
    return f(ctypes.pythonapi.PyThreadState_Get(), low, high - low)

PROGRAMS = {
    # freeing a 100,000-deep list: native stack only, traps even at 8 MiB (the memo, section 4)
    "free100k": "x = []\nfor _ in range(100000): x = [x]\ndel x\nprint('freed')",
    # a chain of frees whose finalizer calls the door at every level, so host frames sit below
    # the deepest wasm frames when the limit is met
    "free-door": (
        "import _host\nclass N:\n    __slots__ = ('n',)\n    def __del__(self): _host.call(b'x' * 64)\n"
        "x = None\nfor _ in range(100000):\n    y = N(); y.n = x; x = y\ndel x, y\nprint('freed')"
    ),
    "free-provider": (
        "import os\nclass N:\n    __slots__ = ('n',)\n    def __del__(self): os.stat('/m/a')\n"
        "x = None\nfor _ in range(100000):\n    y = N(); y.n = x; x = y\ndel x, y\nprint('freed')"
    ),
    "pass": "print('ok')",
    "named": "import sys\nsys.setrecursionlimit(10**8)\ndef f(n): return f(n + 1)\nf(0)",
    # a list chain whose every level also holds an object with a finalizer that calls the door
    # (or a provider); list_dealloc frees the inner list first, so each finalizer runs at its
    # level's depth on the way back, the innermost at the deepest point
    "list-door": (
        "import _host\nclass D:\n    __slots__ = ()\n    def __del__(self): _host.call(b'x' * 64)\n"
        "x = []\nfor _ in range(N_DEPTH): x = [D(), x]\ndel x\nprint('freed')"
    ),
    "list-provider": (
        "import os\nclass D:\n    __slots__ = ()\n    def __del__(self): os.stat('/m/a')\n"
        "x = []\nfor _ in range(N_DEPTH): x = [D(), x]\ndel x\nprint('freed')"
    ),
    "list": "x = []\nfor _ in range(N_DEPTH): x = [x]\ndel x\nprint('freed')",
}

def main() -> None:
    wasm_stack, where, shape = int(sys.argv[1]), sys.argv[2], sys.argv[3]
    metered = len(sys.argv) > 4 and sys.argv[4] == "metered"
    sys.path.insert(0, os.environ["SRC"])
    from wasi_python import runner, run, Mount
    from wasi_python.mounts import Stat
    import wasmtime as wt
    from wasmtime import _ffi

    def engine(metered_: bool):
        with runner._lock:
            if metered_ not in runner._engines:
                runner._fork["used"] = True
                cfg = wt.Config(); cfg.consume_fuel = metered_; cfg.epoch_interruption = True
                cfg.max_wasm_stack = wasm_stack
                f = _ffi.dll.wasmtime_config_async_stack_size_set
                f.argtypes = [ctypes.c_void_p, ctypes.c_size_t]; f.restype = None
                f(cfg.ptr(), max(wasm_stack, 2 << 20))
                runner._engines[metered_] = wt.Engine(cfg)
            return runner._engines[metered_]
    runner._engine = engine

    class P:
        def stat(self, path): return Stat("dir") if path == "/" else Stat("file", size=3)
        def list(self, path): return [("a", "file")]
        def read(self, path): return b"abc"

    out = {}
    def go():
        out["thread_stack"] = thread_stack_bytes()
        if os.environ.get("PROTECT"):
            out["protect"] = protect()
        name, _, n = shape.partition(":")
        code = PROGRAMS[name].replace("N_DEPTH", n or "0")
        d = run(["-c", code], cache_dir=os.environ.get("CACHE") or False,
                host=lambda r: r, mounts=[Mount(P(), "/m")], deadline_s=None, max_file_calls=None,
                fuel=10**13 if metered else None)
        out.update(exit=d.exit_code, trapped=d.trapped, fuel=d.fuel_used, stdout=d.stdout.decode()[-60:],
                   stderr=d.stderr.decode()[-200:])
    if where == "main":
        go()
    else:
        old = threading.stack_size(int(where))
        t = threading.Thread(target=go); t.start(); threading.stack_size(old); t.join()
    out.update(wasm_stack=wasm_stack, where=where, shape=shape, metered=metered)
    print(json.dumps(out), flush=True)

if __name__ == "__main__":
    main()
