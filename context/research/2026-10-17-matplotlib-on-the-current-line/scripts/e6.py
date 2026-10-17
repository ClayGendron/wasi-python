"""Benchmark (wall clock, not a test): median of 3 calls after one warm-up, harness driver, M-series macOS."""
import statistics, sys, tempfile, time
from pathlib import Path
sys.path.insert(0, "/Users/claygendron/Git/Repos/wasi_python/tests")
from harness import guest
S = Path(sys.argv[1]); L = S / "work/link"; A = Path("/Users/claygendron/Git/Repos/wasi_python/build/artifacts")
G = "/usr/local/lib/python315.zip/matplotlib/mpl-data"; DATA = S / "work/inst-mpl/matplotlib/mpl-data"
PLOT = (S / "scripts/milestone.py").read_text()
cfg = Path(tempfile.mkdtemp(dir=S / "e3", prefix="cfg6-"))
for label, wasm, zipf, prog in [
    ("base snapshot pass", A / "python-snapshot.wasm", A / "python-stdlib.zip", "pass"),
    ("mpl snapshot (no pre-import) pass", L / "python-mplp-snapshot-nopre.wasm", L / "python-stdlib-mpl.zip", "pass"),
    ("mpl snapshot (pre-import) pass", L / "python-mplp-snapshot.wasm", L / "python-stdlib-mpl.zip", "pass"),
    ("mpl snapshot (no pre-import) plot", L / "python-mplp-snapshot-nopre.wasm", L / "python-stdlib-mpl.zip", PLOT),
    ("mpl snapshot (pre-import) plot", L / "python-mplp-snapshot.wasm", L / "python-stdlib-mpl.zip", PLOT)]:
    times = []
    for i in range(4):
        out = Path(tempfile.mkdtemp(dir=S / "e3", prefix="out6-"))
        t = time.perf_counter()
        r = guest.run(wasm, ["-c", prog], workdir=Path(tempfile.mkdtemp(dir=S / "e3")), python_version="3.15.0", stdlib=zipf,
                      preopens=[(G, DATA, False), ("/out", out, True), ("/cfg", cfg, True)], env={"MPLCONFIGDIR": "/cfg"}, fuel=10**12)
        if i: times.append(time.perf_counter() - t)
        assert r.exit_code == 0, r.describe()
    print(f"{label:38s} median {statistics.median(times)*1000:8.0f} ms  (3 runs)", flush=True)
