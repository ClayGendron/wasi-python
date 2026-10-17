"""Host side: what open_memmap does with a file object on WASI, before and after."""
from wasi_python import run

prog = r'''
import sys, numpy as np
from numpy.lib import _format_impl, format
try:
    import mmap; print("mmap module: present")
except ImportError as e:
    print("mmap module:", e)
def probe(label):
    with open("/tmp/m.npy", "wb") as f:
        try:
            format.open_memmap(f, mode="w+", dtype=np.float64, shape=(3,))
            print(label, "ok")
        except Exception as e:
            print(label, type(e).__name__, e)
    try:
        np.save("/tmp/p.npy", np.arange(3))
        np.load("/tmp/p.npy", mmap_mode="r")
        print(label, "np.load(mmap_mode='r') ok")
    except Exception as e:
        print(label, "np.load(mmap_mode='r'):", type(e).__name__, e)
probe("stock:")
_format_impl.sys = sys
_orig = _format_impl.isfileobj
def isfileobj(f):
    return False if sys.platform == "wasi" else _orig(f)
_format_impl.isfileobj = isfileobj
probe("patched:")
'''
done = run(["-c", prog])
print(done.stdout.decode(), done.stderr.decode()[-1500:], "exit", done.exit_code)
