"""Count `def test` lines and opt-in marks per subfolder of a tree (read as text).

    uv run --no-project python -I counts.py <tree root> <package dir> <depth> [mark regex]
"""

import re
import sys
from collections import Counter
from pathlib import Path

root, pkg, depth = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3])
mark = re.compile(sys.argv[4] if len(sys.argv) > 4 else r"^\s*@(slow|tooslow)\b", re.M)
tests, marks, files = Counter(), Counter(), Counter()
for f in sorted((root / pkg).rglob("*.py")):
    rel = f.relative_to(root)
    if not (f.name.startswith("test") or f.name.endswith("_test.py")):
        continue
    key = "/".join(rel.parts[:depth])
    t = f.read_text(errors="replace")
    tests[key] += len(re.findall(r"^\s*def test", t, re.M))
    marks[key] += len(mark.findall(t))
    files[key] += 1
for k in sorted(tests):
    print(f"{k} files={files[k]} tests={tests[k]} marked={marks[k]}")
print("total", sum(files.values()), sum(tests.values()), sum(marks.values()))
