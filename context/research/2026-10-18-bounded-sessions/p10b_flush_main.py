"""The P2 difference: an open file beside a function defined in __main__. Counts only."""
import pathlib
import sys
import tempfile

from wasi_python import Grant, run

out = []
head = "f = open('/w/t.txt', 'w'); f.write('x' * 100)\n"
variants = {
    "P2 as run (atexit handler defined in __main__)": head + "import atexit\ndef h():\n    pass\natexit.register(h)\n",
    "a function defined, no atexit": head + "def h():\n    pass\n",
    "import atexit only": head + "import atexit\n",
    "atexit.register(print, 1)": head + "import atexit\natexit.register(print, 1)\n",
    "atexit handler that flushes f": head + "import atexit\natexit.register(f.flush)\n",
}
for snap in (True, False):
    name = "snapshot" if snap else "plain"
    for label, code in variants.items():
        sizes = []
        for _ in range(2):
            with tempfile.TemporaryDirectory() as d:
                r = run(["-c", code], snapshot=snap, grants=[Grant(d, "/w", writable=True)])
                sizes.append((pathlib.Path(d) / "t.txt").stat().st_size)
        line = f"{name} {label}: exit {r.exit_code}, file bytes over two runs {sizes}"
        print(line)
        out.append(line)
pathlib.Path(sys.argv[1]).write_text("\n".join(out) + "\n")
