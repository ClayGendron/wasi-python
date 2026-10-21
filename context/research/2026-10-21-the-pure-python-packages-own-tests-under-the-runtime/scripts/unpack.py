"""Copy the four sdists 039, 041 and 042 pin, check them against downloads/SHA256SUMS, and unpack
every test source into <scratch>/trees/<name>/ with tarfile's data filter (archives are data:
nothing is run). networkx's tree gets the carried patch, as the build applies it.

    uv run --no-project python -I unpack.py <worktree> <scratch>
"""

import hashlib
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

wt, scratch = Path(sys.argv[1]), Path(sys.argv[2])
main_downloads = Path("/Users/claygendron/Git/Repos/wasi_python/downloads")
sums = {}
for line in (wt / "downloads/SHA256SUMS").read_text().splitlines():
    if line.strip():
        h, n = line.split()
        sums[n.lstrip("*")] = h
for n in ["pyyaml-6.0.3.tar.gz", "markupsafe-3.0.4.tar.gz", "networkx-3.7.tar.gz",
          "seaborn-0.13.2.tar.gz"]:
    d = scratch / "src" / n.split("-")[0]
    d.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(main_downloads / n, d / n)
    got = hashlib.sha256((d / n).read_bytes()).hexdigest()
    print(("OK  " if got == sums[n] else "BAD ") + n)

trees = scratch / "trees"
for d in sorted((scratch / "src").iterdir()):
    for a in sorted(d.glob("*.tar.gz")):
        dest = trees / d.name
        if dest.exists():
            continue
        dest.mkdir(parents=True)
        with tarfile.open(a) as t:
            t.extractall(dest, filter="data")
        tops = list(dest.iterdir())
        print(d.name, "->", [p.name for p in tops])

nx = next((trees / "networkx").iterdir())
patch = wt / "recipes/patches/networkx-3.7/0001-graph-atlas-from-a-zip.patch"
if not (nx / ".patched").exists():
    subprocess.run(["patch", "-p1", "-i", str(patch)], cwd=nx, check=True)
    (nx / ".patched").write_text("")
