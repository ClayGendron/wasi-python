"""An explicit flush of every open file object, run as the last atexit handler: does it make
the snapshot's shutdown flush what P2 lost, and what does it cost? Counts only."""
import pathlib
import sys
import tempfile

from wasi_python import Grant, run

out = []
flusher = (
    "import atexit as _a, gc as _g, io as _io\n"
    "def _flush_open_files():\n"
    "    for o in _g.get_objects():\n"
    "        if isinstance(o, _io.IOBase):\n"
    "            try:\n"
    "                if not o.closed: o.flush()\n"
    "            except Exception: pass\n"
    "_a.register(_flush_open_files)\n"
)
user = (
    "f = open('/w/t.txt', 'w'); f.write('x' * 100)\n"
    "g = open('/w/c.txt', 'w'); g.write('y' * 100); g.me = g; del g\n"
    "import atexit\n"
    "def h():\n"
    "    f.write('z' * 10)\n"
    "atexit.register(h)\n"
)
for snap in (True, False):
    name = "snapshot" if snap else "plain"
    for label, code in (("without the flusher", user), ("with the flusher registered first", flusher + user)):
        with tempfile.TemporaryDirectory() as d:
            r = run(["-c", code], snapshot=snap, grants=[Grant(d, "/w", writable=True)], fuel=10**11)
            t = (pathlib.Path(d) / "t.txt").stat().st_size
            c = (pathlib.Path(d) / "c.txt").stat().st_size
        line = f"{name} {label}: exit {r.exit_code}, t.txt {t} bytes (110 written), c.txt {c} bytes (100 written, in a cycle), fuel {r.fuel_used}"
        print(line)
        out.append(line)
    # The flusher's own cost: once with pandas imported, measured inside the guest by the
    # difference of two runs that end by os._exit (no finalization).
    base = "import pandas, numpy as np\na = [np.zeros(3) for _ in range(1000)]\n"
    cut = "\nimport os; os._exit(0)\n"
    counts = []
    for extra in ("", flusher + "_flush_open_files()\n"):
        best = min(run(["-c", base + extra + cut], snapshot=snap, fuel=10**11, deadline_s=None).fuel_used for _ in range(3))
        counts.append(best)
    line = f"{name} flusher cost after importing pandas: {counts[1] - counts[0]} fuel (min of 3 each)"
    print(line)
    out.append(line)
pathlib.Path(sys.argv[1]).write_text("\n".join(out) + "\n")
