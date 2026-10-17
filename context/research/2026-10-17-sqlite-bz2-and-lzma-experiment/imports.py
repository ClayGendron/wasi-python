"""The imports of each binary (module, name), through the judge's own wasm parser, and the wall check.

    imports.py <repo> <binary>...
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]) / "tests"))
from harness import wasm  # noqa: E402

sets = {}
for p in sys.argv[2:]:
    m = wasm.parse_file(p)
    names = sorted((i.module, i.name) for i in m.imports)
    sets[p] = set(names)
    mods = sorted({i.module for i in m.imports})
    print(p.split("/")[-2] + "/" + p.split("/")[-1], len(names), "imports;", "modules", mods,
          "; wall errors:", wasm.wall_errors(m))
paths = list(sets)
for a, b in zip(paths, paths[1:]):
    print("added", sorted(sets[b] - sets[a]), "removed", sorted(sets[a] - sets[b]), f"({a.split('/')[-2]} -> {b.split('/')[-2]})")
