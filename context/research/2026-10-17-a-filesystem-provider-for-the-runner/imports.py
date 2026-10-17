"""List each binary's imports, by module (memo finding 1).

uv run --no-sync python imports.py ART_DIR > imports.txt
"""

import sys
from pathlib import Path

import wasmtime as wt

art = Path(sys.argv[1])
engine = wt.Engine()
for name in ("python.wasm", "python-snapshot.wasm"):
    module = wt.Module.from_file(engine, str(art / name))
    by: dict[str, list[str]] = {}
    for imp in module.imports:
        by.setdefault(imp.module, []).append(imp.name)
    print(f"{name}: {sum(len(v) for v in by.values())} imports")
    for mod, names in by.items():
        print(f"  {mod} ({len(names)}): {' '.join(sorted(names))}")
