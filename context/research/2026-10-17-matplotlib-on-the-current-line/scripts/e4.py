import sys, tempfile
from pathlib import Path
sys.path.insert(0, "/Users/claygendron/Git/Repos/wasi_python/tests")
from harness import guest
S = Path(sys.argv[1]); L = S / "work/link"
G = "/usr/local/lib/python315.zip/matplotlib/mpl-data"; DATA = S / "work/inst-mpl/matplotlib/mpl-data"
out = Path(tempfile.mkdtemp(dir=S / "e3", prefix="out4-"))
r = guest.run(L / "python-mplp-snapshot.wasm", ["-c", (S / "scripts/features_prog.py").read_text()],
              workdir=Path(tempfile.mkdtemp(dir=S / "e3")), python_version="3.15.0", stdlib=L / "python-stdlib-mpl.zip",
              preopens=[(G, DATA, False), ("/out", out, True)], fuel=10**12)
print("exit", r.exit_code, r.trapped, f"{r.fuel:,}"); print(r.text); print("STDERR", r.stderr.decode()[-800:])
