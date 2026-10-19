"""Spec 078, criterion 16, on musl: the built runner from 256 KiB threads (a free, the __repr__
recursion, run_async on an executor of such threads) and a door callback at the deepest freeing
point; on CPython 3.14.0 every entry is refused."""
import asyncio, concurrent.futures, sys, threading
import wasi_python
print(sys.version.split()[0], flush=True)
FREE = "x = []\nfor i in range(20000): x = [x]\ndel x\nprint('ok')"
REPR = ("class A:\n    def __repr__(self): return repr(self)\n"
        "try:\n    repr(A())\nexcept RecursionError:\n    print('RecursionError')")
DOOR = ("import _host\nclass D:\n    __slots__ = ()\n    def __del__(self): _host.call(b'x' * 64)\n"
        "x = []\nfor _ in range(30000): x = [D(), x]\ndel x\nprint('freed')")
def show(d):
    return (d.exit_code, d.trapped, d.stdout.decode().strip()[-20:])
def guarded(f):
    try:
        return show(f())
    except RuntimeError as e:
        return ("RuntimeError", str(e)[:100])
threading.stack_size(256 * 1024)
out = {}
for name, code, kw in (("thread-free", FREE, {}), ("thread-repr", REPR, {}), ("door-at-depth", DOOR, {"host": lambda r: r})):
    t = threading.Thread(target=lambda: out.update(r=guarded(lambda: wasi_python.run(["-c", code], **kw))))
    t.start(); t.join()
    print(name, out["r"], flush=True)
for name, code in (("executor-free", FREE), ("executor-repr", REPR)):
    with concurrent.futures.ThreadPoolExecutor(1) as pool:
        print(name, guarded(lambda: asyncio.run(wasi_python.run_async(["-c", code], executor=pool))), flush=True)
