"""Spec 078, criterion 16, on musl: the built runner from a 256 KiB calling thread, and a door
callback at the deepest freeing point, survive; on CPython 3.14.0 every entry is refused."""
import sys, threading
import wasi_python
print(sys.version.split()[0], flush=True)
FREE = "x = []\nfor i in range(20000): x = [x]\ndel x\nprint('ok')"
DOOR = ("import _host\nclass D:\n    __slots__ = ()\n    def __del__(self): _host.call(b'x' * 64)\n"
        "x = []\nfor _ in range(30000): x = [D(), x]\ndel x\nprint('freed')")
out = {}
def go(code, **kw):
    try:
        d = wasi_python.run(["-c", code], **kw)
        out["r"] = (d.exit_code, d.trapped, d.stdout.decode().strip()[-20:])
    except RuntimeError as e:
        out["r"] = ("RuntimeError", str(e)[:120])
threading.stack_size(256 * 1024)
for name, code, kw in (("small-thread-free", FREE, {}), ("door-at-depth", DOOR, {"host": lambda r: r})):
    t = threading.Thread(target=go, args=(code,), kwargs=kw); t.start(); t.join()
    print(name, out["r"], flush=True)
