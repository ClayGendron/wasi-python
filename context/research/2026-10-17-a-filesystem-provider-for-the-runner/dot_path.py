"""Does wasi-libc normalize "." before it picks a preopen? (memo finding 7)

uv run --no-sync python dot_path.py ART_DIR > dot_path.txt
"""

import sys
from pathlib import Path

from wasi_python import Artifacts, run

art = Path(sys.argv[1])
found = Artifacts(art / "python-snapshot.wasm", art / "python.wasm", art / "python-stdlib.zip", art / "MANIFEST")
prog = """
import os
for p in ("/usr/local/lib/python315.zip", "/usr/local/./lib/python315.zip", "/usr/./local/lib/python315.zip", "/usr/local/lib/../lib/python315.zip"):
    try:
        print(p, "->", os.stat(p).st_size)
    except OSError as e:
        print(p, "->", e.errno, e.strerror)
"""
c = run(["-c", prog], root=True, cache_dir=False, artifacts=found)
print(c.exit_code, c.stdout.decode(), c.stderr.decode()[-500:])
