"""Is _struct builtin, is zipimport frozen, and who loaded encodings (plain reactor, today's zip).

    uv run --no-sync python guest_builtins.py <artifact copy dir>   (prints outputs/builtins.txt)
"""

import sys
from pathlib import Path

from wasi_python import Artifacts, run

A = Path(sys.argv[1])
a = Artifacts(snapshot=A / "python-snapshot.wasm", plain=A / "python.wasm",
              stdlib_zip=A / "python-stdlib.zip", manifest=A / "MANIFEST")
code = ('import sys, zipimport; print("_struct" in sys.builtin_module_names, '
        '"zlib" in sys.builtin_module_names, zipimport.__spec__.origin, '
        'sys.modules["encodings"].__spec__.loader)')
r = run(["-c", code], artifacts=a, snapshot=False, cache_dir=False)
print(r.stdout.decode().strip())
