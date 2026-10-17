"""E0: a read-only grant nested under the stdlib grant, at the path matplotlib would compute."""
import sys
from pathlib import Path
sys.path.insert(0, "/Users/claygendron/Git/Repos/wasi_python/tests")
from harness import guest

S = Path(sys.argv[1])
A = Path("/Users/claygendron/Git/Repos/wasi_python/build/artifacts")
G = "/usr/local/lib/python315.zip/matplotlib/mpl-data"
prog = f"""
import os, decimal
p = "{G}"
print("decimal from", decimal.__file__)
print("rc", open(p + "/matplotlibrc").readline().strip(), os.path.isfile(p + "/matplotlibrc"))
print("listdir", sorted(os.listdir(p)), os.path.isdir(p + "/fonts/ttf"))
print("font bytes", len(open(p + "/fonts/ttf/DejaVuSans.ttf", "rb").read()))
for op in ("w", "a"):
    try:
        open(p + "/x", op); print("write", op, "ALLOWED")
    except OSError as e:
        print("write", op, type(e).__name__, e.errno)
try:
    os.listdir("/usr/local/lib/python315.zip/matplotlib"); print("parent listed")
except OSError as e:
    print("parent", type(e).__name__, e.errno)
print("HOME", os.environ.get("HOME"))
"""
for wasm in ("python.wasm", "python-snapshot.wasm"):
    for first in (False, True):
        r = guest.run(A / wasm, ["-c", prog], workdir=S / "e0/work", python_version="3.15.0",
                      stdlib=A / "python-stdlib.zip", preopens=[(G, S / "e0/data", False)],
                      preopens_first=first)
        print("==", wasm, "data-first" if first else "root-first", r.exit_code, r.trapped)
        print(r.text, r.stderr.decode()[-300:])
