"""E3: fuel for start-up, import and one plot, on each scratch binary (fuel = guest instructions)."""
import hashlib, sys, tempfile
from pathlib import Path
sys.path.insert(0, "/Users/claygendron/Git/Repos/wasi_python/tests")
from harness import guest

S = Path(sys.argv[1]); L = S / "work/link"; A = Path("/Users/claygendron/Git/Repos/wasi_python/build/artifacts")
G = "/usr/local/lib/python315.zip/matplotlib/mpl-data"; DATA = S / "work/inst-mpl/matplotlib/mpl-data"
PLOT = (S / "scripts/milestone.py").read_text().replace('import matplotlib\n', 'import matplotlib\nmatplotlib.rcParams["svg.hashsalt"] = "wasi"\n', 1)
progs = {"pass": "pass", "import pyplot": "import matplotlib.pyplot", "plot": PLOT}
cases = [
    ("base plain", A / "python.wasm", A / "python-stdlib.zip", ["pass"]),
    ("base snapshot", A / "python-snapshot.wasm", A / "python-stdlib.zip", ["pass"]),
    ("mpl plain", L / "python-mplp-stripped.wasm", L / "python-stdlib-mpl.zip", ["pass", "import pyplot", "import pyplot", "plot"]),
    ("mpl snapshot, no pre-import", L / "python-mplp-snapshot-nopre.wasm", L / "python-stdlib-mpl.zip", ["pass", "import pyplot", "import pyplot", "plot"]),
    ("mpl snapshot, pyplot pre-imported", L / "python-mplp-snapshot.wasm", L / "python-stdlib-mpl.zip", ["pass", "import pyplot", "plot"]),
]
for label, wasm, zipf, names in cases:
    cfg = Path(tempfile.mkdtemp(dir=S / "e3", prefix="cfg-"))  # one config dir per binary: the second import reads the cache
    for name in names:
        out = Path(tempfile.mkdtemp(dir=S / "e3", prefix="out-"))
        r = guest.run(wasm, ["-c", progs[name]], workdir=Path(tempfile.mkdtemp(dir=S / "e3")), python_version="3.15.0",
                      stdlib=zipf, preopens=[(G, DATA, False), ("/out", out, True), ("/cfg", cfg, True)],
                      env={"MPLCONFIGDIR": "/cfg"}, fuel=10**12)
        print(f"{label:36s} {name:14s} exit={r.exit_code} trapped={r.trapped} fuel={r.fuel:,}", flush=True)
        if name == "plot":
            print("   ", r.text.replace("\n", " | ")[:400])
            p = out / "plot.svg"
            if p.exists(): print("    svg", hashlib.sha256(p.read_bytes()).hexdigest()[:16])
        if r.stderr.strip():
            print("    stderr:", r.stderr.decode()[-300:].replace("\n", " | "))
