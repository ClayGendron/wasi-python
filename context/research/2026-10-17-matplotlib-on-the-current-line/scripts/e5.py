import sys, tempfile
from pathlib import Path
sys.path.insert(0, "/Users/claygendron/Git/Repos/wasi_python/tests")
from harness import guest
S = Path(sys.argv[1]); L = S / "work/link"
G = "/usr/local/lib/python315.zip/matplotlib/mpl-data"; DATA = S / "work/inst-mpl/matplotlib/mpl-data"
cfg = Path(tempfile.mkdtemp(dir=S / "e3", prefix="cfg5-"))
for wasm, prog in [("python-mplp-snapshot-nopre.wasm", "import matplotlib.pyplot"),
                   ("python-mplp-snapshot-nopre.wasm", "import matplotlib"),
                   ("python-mplp-snapshot-nopre.wasm", "import matplotlib.font_manager"),
                   ("python-mplp-snapshot-nopre.wasm", "import matplotlib.pyplot"),
                   ("python-mplp-snapshot.wasm", "import os; os._exit(0)"),
                   ("python-mplp-snapshot-nopre.wasm", "import os; os._exit(0)")]:
    r = guest.run(L / wasm, ["-c", prog], workdir=Path(tempfile.mkdtemp(dir=S / "e3")), python_version="3.15.0",
                  stdlib=L / "python-stdlib-mpl.zip", preopens=[(G, DATA, False), ("/cfg", cfg, True)],
                  env={"MPLCONFIGDIR": "/cfg"}, fuel=10**12)
    print(f"{wasm:34s} {prog:32s} exit={r.exit_code} fuel={r.fuel:,}", r.stderr.decode()[-200:], flush=True)
