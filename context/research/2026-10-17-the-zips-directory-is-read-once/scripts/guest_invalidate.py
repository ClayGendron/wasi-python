"""importlib.invalidate_caches() drops zipimport's directory: the next import reads it again.

    uv run --no-sync python guest_invalidate.py <artifact copy dir> <scratch zips dir> <out.tsv>
"""

from __future__ import annotations

import sys
from pathlib import Path

from wasi_python import Artifacts, run

ART, ZIPS, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
CASES = {
    "import importlib": "import importlib",
    "import json.tool": "import importlib, json.tool",
    "invalidate_caches + import json.tool": "import importlib; importlib.invalidate_caches(); import json.tool\n"
    "import zipimport; print(len(zipimport._zip_directory_cache))",
}
rows = ["binary\tzip\tcase\tfuel_used\texit\tstdout"]
for binary, zname in (("snapshot", "zip-1x"), ("plain", "zip-1x"), ("plain", "zip-4x")):
    a = Artifacts(snapshot=ART / "python-snapshot.wasm", plain=ART / "python.wasm",
                  stdlib_zip=ZIPS / f"{zname}.zip", manifest=ART / "MANIFEST")
    for case, code in CASES.items():
        r = run(["-c", code], artifacts=a, snapshot=binary == "snapshot", fuel=10**13, cache_dir=False)
        rows.append(f"{binary}\t{zname}\t{case}\t{r.fuel_used}\t{r.exit_code}\t{r.stdout.decode().strip()}")
        print(rows[-1], flush=True)
OUT.write_text("\n".join(rows) + "\n")
