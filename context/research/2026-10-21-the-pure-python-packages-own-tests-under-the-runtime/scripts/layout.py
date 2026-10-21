"""Print each tree's top level and its test folders/files (read only).

    uv run --no-project python -I layout.py <trees>
"""

import sys
from pathlib import Path

trees = Path(sys.argv[1])
for d in sorted(trees.iterdir()):
    root = next(d.iterdir())
    top = sorted(p.name + ("/" if p.is_dir() else "") for p in root.iterdir())
    print(f"=== {d.name}: {' '.join(top)[:300]}")
    tdirs = sorted({str(p.parent.relative_to(root)) for p in root.rglob("test*.py")}
                   | {str(p.parent.relative_to(root)) for p in root.rglob("*_test.py")})
    n = len(list(root.rglob("test*.py"))) + len(list(root.rglob("*_test.py")))
    print(f"  {n} test files in {len(tdirs)} folders: {' '.join(tdirs)[:600]}")
