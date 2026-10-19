"""Spec 071 v2: can the runner see, exactly, that a guest trap would no longer reach wasmtime on
Linux? For each fatal signal wasmtime handles, read the installed handler with sigaction and ask
dladdr which shared object holds it. Each faulthandler order in its own process, then a trap."""
import subprocess, sys

CASE = r'''
import ctypes, ctypes.util, faulthandler, signal, sys, wasmtime
from wasmtime import _ffi
libc = ctypes.CDLL(None, use_errno=True)
class Dl_info(ctypes.Structure):
    _fields_ = [("dli_fname", ctypes.c_char_p), ("dli_fbase", ctypes.c_void_p),
                ("dli_sname", ctypes.c_char_p), ("dli_saddr", ctypes.c_void_p)]
libc.dladdr.argtypes = [ctypes.c_void_p, ctypes.POINTER(Dl_info)]
buf = (ctypes.c_char * 1024)()            # larger than any struct sigaction; the handler is first
libc.sigaction.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p]
WASMTIME = ctypes.c_void_p.in_dll  # placeholder to keep names short
def owner(sig):
    if libc.sigaction(sig, None, buf) != 0:
        return "sigaction failed"
    addr = ctypes.c_void_p.from_buffer(buf).value or 0
    if addr in (0, 1):
        return {0: "SIG_DFL", 1: "SIG_IGN"}[addr]
    info = Dl_info()
    if not libc.dladdr(addr, ctypes.byref(info)):
        return hex(addr)
    name = (info.dli_fname or b"?").decode()
    return "wasmtime" if "libwasmtime" in name else name.rsplit("/", 1)[-1]
SIGS = [signal.SIGSEGV, signal.SIGILL, signal.SIGBUS, signal.SIGFPE]
fh = sys.argv[1]
if fh in ("before", "disable-after", "disable-restore"):
    faulthandler.enable()
engine = wasmtime.Engine()
module = wasmtime.Module(engine, '(module (func (export "u") unreachable))')
if fh == "after":
    faulthandler.enable()
elif fh in ("disable-after",):
    faulthandler.disable()
elif fh == "after-then-disable":
    faulthandler.enable(); faulthandler.disable()
print("handlers:", ",".join(owner(s) for s in SIGS), flush=True)
store = wasmtime.Store(engine)
f = wasmtime.Instance(store, module, []).exports(store)["u"]
try:
    f(store)
except wasmtime.Trap as e:
    print("trap returned", e.trap_code, flush=True)
'''
for fh in ("none", "before", "after", "disable-after", "after-then-disable"):
    r = subprocess.run([sys.executable, "-c", CASE, fh], capture_output=True, text=True)
    print(f"faulthandler {fh:18}: exit {r.returncode:3} | " + r.stdout.strip().replace("\n", " | "), flush=True)
