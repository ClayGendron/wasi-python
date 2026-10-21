"""The three sdists' staged tests folders and test files, from the tarball members.

    uv run python inventory.py > inventory.json
"""

import json
import re
import sys
from pathlib import Path

W = Path("/Users/claygendron/Git/Repos/wasi_python/.claude/worktrees/agent-aab0b516adb4e5c06")
sys.path.insert(0, str(W / "tests"))
from harness import upstream  # noqa: E402

TEST_FILE = re.compile(r"(?:.*/)?(?:test_[^/]*|[^/]*_test)\.py")
FAMS = {
    "scipy": ("scipy-1.18.1.tar.gz", "scipy", ["scipy/odr/tests"]),
    "scikit-learn": ("scikit_learn-1.9.1.tar.gz", "sklearn", []),
    "statsmodels": ("statsmodels-0.15.0.tar.gz", "statsmodels", []),
}
out = {}
for fam, (tar, top, skip) in FAMS.items():
    members = upstream.tarball_members(W / "downloads" / tar)
    folders = set()
    for m in members:
        parts = m.split("/")
        if parts[0] != top or "tests" not in parts:
            continue
        i = parts.index("tests")
        folders.add("/".join(parts[: i + 1]))
    folders = sorted(f for f in folders if f not in skip)
    files = sorted(m for m in members if TEST_FILE.fullmatch(m) and any(m.startswith(f + "/") for f in folders))
    out[fam] = {"folders": folders, "files": files}
    print(fam, len(folders), len(files), file=sys.stderr)
print(json.dumps(out, indent=1))
