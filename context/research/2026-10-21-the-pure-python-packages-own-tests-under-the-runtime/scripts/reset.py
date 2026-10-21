"""Remove stages (all, or the named families) and the named sessions' outputs, so they are
staged and run again.  uv run --no-project python -I reset.py <survey> stages=a,b|all out=x,y"""

import os
import shutil
import stat
import sys
from pathlib import Path

S = Path(sys.argv[1])


def rm(p: Path) -> None:
    if not p.exists():
        return
    for d, dirs, files in os.walk(p):
        os.chmod(d, stat.S_IRWXU)
        for f in files:
            fp = Path(d) / f
            if not fp.is_symlink():
                os.chmod(fp, stat.S_IRUSR | stat.S_IWUSR)
    shutil.rmtree(p)


for arg in sys.argv[2:]:
    key, _, val = arg.partition("=")
    names = [v for v in val.split(",") if v]
    if key == "stages":
        targets = sorted((S / "stage").iterdir()) if names == ["all"] else [S / "stage" / n for n in names]
    else:
        targets = [S / "out" / n for n in names]
    for t in targets:
        rm(t)
        print("removed", t.name)
