"""Record each other family's stage digests with a given tree's harness.

    uv run --project <worktree> python gen_stages.py <repo root> <out json>

The repo root's tests/ is put first on sys.path, so its harness (the base's or the build's)
computes the digests; its downloads/ and build/ are links to the worktree's tarballs and trees.
"""

import json
import sys
import tempfile
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root / "tests"))
src = (Path(__file__).parent / "unit_stages_add.py").read_text()
ns: dict = {}
exec(  # noqa: S102 (a scratch tool, run on our own text)
    "import json\nfrom harness import packages, upstream\n" + src, ns
)
from harness import paths  # noqa: E402

assert paths.REPO == root, paths.REPO
with tempfile.TemporaryDirectory() as d:
    out = ns["stage_digests"](Path(d))
Path(sys.argv[2]).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
print(json.dumps(out, indent=1))
