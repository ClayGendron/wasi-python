"""Does gc.unfreeze(), run as the last atexit handler, give the snapshot CPython's own exit
behaviour (the plain reactor's), and at what cost? Counts only."""
import pathlib
import sys
import tempfile

from wasi_python import Grant, run

out = []
pre = "import atexit as _a, gc as _g\n_a.register(_g.unfreeze)\n"
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
    for label, code in (("without unfreeze", user), ("with gc.unfreeze run last", pre + user)):
        fuels = []
        for _ in range(3):
            with tempfile.TemporaryDirectory() as d:
                r = run(["-c", code], snapshot=snap, grants=[Grant(d, "/w", writable=True)], fuel=10**11)
                t = (pathlib.Path(d) / "t.txt").stat().st_size
                c = (pathlib.Path(d) / "c.txt").stat().st_size
            fuels.append(r.fuel_used)
        line = f"{name} {label}: exit {r.exit_code}, t.txt {t} bytes (110 written), c.txt {c} bytes (100 written, in a cycle), fuel min {min(fuels)}"
        print(line)
        out.append(line)
pathlib.Path(sys.argv[1]).write_text("\n".join(out) + "\n")
