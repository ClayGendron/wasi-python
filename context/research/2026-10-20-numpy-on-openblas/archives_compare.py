"""Criterion 5: step 50's and step 57's extension archives (and their .deps) in two build trees,
compared by SHA-256. Usage: archives_compare.py <base build/> <new build/>"""

import hashlib
import sys
from pathlib import Path

base, new = Path(sys.argv[1]), Path(sys.argv[2])
for folder in ("pandas-build", "scipy-modules", "scipy-shims"):
    files = sorted(
        p.relative_to(new / folder)
        for p in (new / folder).rglob("*")
        if p.is_file() and (p.suffix in (".so", ".a") or p.name.endswith(".so.deps"))
    )
    differ = []
    for rel in files:
        a, b = base / folder / rel, new / folder / rel
        if not a.is_file():
            differ.append(str(rel))
            continue
        x, y = a.read_bytes(), b.read_bytes()
        if rel.name.endswith(".deps"):  # absolute paths name each tree's own checkout
            x = x.replace(bytes(base.resolve().parent), b"<tree>")
            y = y.replace(bytes(new.resolve().parent), b"<tree>")
        if hashlib.sha256(x).digest() != hashlib.sha256(y).digest():
            differ.append(str(rel))
    print(f"{folder}: {len(files)} archives and .deps files, {len(differ)} differ", *differ[:10])
