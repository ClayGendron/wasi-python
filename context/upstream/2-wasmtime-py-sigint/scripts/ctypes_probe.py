"""What does a ctypes callback return to C when the Python callable raises?

Each thunk is called through its C function pointer, as Wasmtime calls
wasmtime-py's trampoline. A good call returns 0x1234 first, so a later
raising call shows whatever its return slot already held.
"""
import ctypes
import sys

sys.unraisablehook = lambda u: None  # keep the output short
for restype in (ctypes.c_size_t, ctypes.c_void_p):
    proto = ctypes.CFUNCTYPE(restype)
    good = proto(lambda: 0x1234)

    def bad():
        raise KeyboardInterrupt

    bad = proto(bad)
    call_good = proto(ctypes.cast(good, ctypes.c_void_p).value)
    call_bad = proto(ctypes.cast(bad, ctypes.c_void_p).value)
    seen = set()
    for i in range(5):
        seen.add(f"ok -> {call_good()!r}")
        seen.add(f"raised -> {call_bad()!r}")
    print(sys.version.split()[0], restype.__name__, sorted(seen))
