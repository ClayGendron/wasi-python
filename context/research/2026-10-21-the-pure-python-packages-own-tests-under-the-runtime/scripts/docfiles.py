"""Print the doc files under a tree folder whose text holds a doctest prompt (read as text).

    uv run --no-project python -I docfiles.py <tree root> <folder> <suffix>...
"""

import sys
from pathlib import Path

root, folder, suffixes = Path(sys.argv[1]), sys.argv[2], tuple(sys.argv[3:])
out = [str(p.relative_to(root)) for p in sorted((root / folder).rglob("*"))
       if p.is_file() and p.suffix in suffixes and ">>> " in p.read_text(errors="replace")]
print(" ".join(out))
print(len(out), file=sys.stderr)
