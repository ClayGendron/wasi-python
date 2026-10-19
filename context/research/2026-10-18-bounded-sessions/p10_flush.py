"""Why the snapshot does not flush an open file at a normal exit: variants. Counts only."""
import pathlib
import sys
import tempfile

from wasi_python import Grant, run

out = []
variants = {
    "global, left open": "f = open('/w/t.txt', 'w'); f.write('x' * 100)\n",
    "global, del f": "f = open('/w/t.txt', 'w'); f.write('x' * 100); del f\n",
    "gc.unfreeze first": "import gc; gc.unfreeze()\nf = open('/w/t.txt', 'w'); f.write('x' * 100)\n",
    "in a list global": "keep = [open('/w/t.txt', 'w')]; keep[0].write('x' * 100)\n",
    "binary, buffered": "f = open('/w/t.txt', 'wb'); f.write(b'x' * 100)\n",
    "in a cycle": "f = open('/w/t.txt', 'w'); f.write('x' * 100); f.me = f; del f\n",
}
for snap in (True, False):
    name = "snapshot" if snap else "plain"
    for label, code in variants.items():
        with tempfile.TemporaryDirectory() as d:
            r = run(["-c", code], snapshot=snap, grants=[Grant(d, "/w", writable=True)])
            size = (pathlib.Path(d) / "t.txt").stat().st_size
            line = f"{name} {label}: exit {r.exit_code}, file {size} bytes, stderr {r.stderr[-100:]!r}"
            print(line)
            out.append(line)
pathlib.Path(sys.argv[1]).write_text("\n".join(out) + "\n")
