"""E1: the first milestone on the scratch binary: import, Agg, plot, savefig PNG and SVG."""
import hashlib, sys
from pathlib import Path
sys.path.insert(0, "/Users/claygendron/Git/Repos/wasi_python/tests")
from harness import guest

S = Path(sys.argv[1]); wasm = Path(sys.argv[2]); zipf = Path(sys.argv[3]); prog = Path(sys.argv[4]).read_text()
env = dict(arg.split("=", 1) for arg in sys.argv[5:])
G = "/usr/local/lib/python315.zip/matplotlib/mpl-data"
out = Path(__import__("tempfile").mkdtemp(dir=S / "e1", prefix="out-")); print("out", out)
r = guest.run(wasm, ["-c", prog], workdir=Path(__import__("tempfile").mkdtemp(dir=S / "e1")), python_version="3.15.0", stdlib=zipf,
              preopens=[(G, S / "work/inst-mpl/matplotlib/mpl-data", False), ("/out", out, True)],
              env=env, fuel=10**12)
print("exit", r.exit_code, "trapped", r.trapped, "fuel", f"{r.fuel:,}")
print(r.text[-3000:])
print("STDERR", r.stderr.decode()[-3000:])
