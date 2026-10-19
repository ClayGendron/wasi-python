"""Stage CPython's own test package for the guest, members of the pinned tarball only.

uv run python stage.py

Reads the member names of downloads/Python-3.15.0.tar.xz (its SHA-256 checked against
downloads/SHA256SUMS first; nothing is extracted from it) and copies each `Lib/test/` member
from the source tree build/Python-3.15.0 into build/cpython-suite-research/stage/lib/test.
A file the build left in the tree (a __pycache__) is not a member and is left out. The guest
driver goes to stage/judge/drive.py. The stage is granted read-only at /cpy.
"""

import hashlib
import shutil
import tarfile
from pathlib import Path

REPO = Path("/Users/claygendron/Git/Repos/wasi_python")
TARBALL = REPO / "downloads/Python-3.15.0.tar.xz"
TREE = REPO / "build/Python-3.15.0"
OUT = REPO / "build/cpython-suite-research/stage"
HERE = Path(__file__).resolve().parent


def main() -> None:
    want = next(
        line.split()[0]
        for line in (REPO / "downloads/SHA256SUMS").read_text().splitlines()
        if line.endswith("  Python-3.15.0.tar.xz")
    )
    got = hashlib.sha256(TARBALL.read_bytes()).hexdigest()
    assert got == want, f"tarball hash {got} != pinned {want}"
    prefix = "Python-3.15.0/Lib/test/"
    with tarfile.open(TARBALL) as t:
        members = [m.name[len("Python-3.15.0/") :] for m in t if m.isfile() and m.name.startswith(prefix)]
    if OUT.exists():
        shutil.rmtree(OUT)
    n = 0
    missing = []
    for rel in members:
        assert ".." not in Path(rel).parts and not rel.startswith("/")
        src = TREE / rel
        if not src.is_file():
            missing.append(rel)
            continue
        dest = OUT / "lib" / rel[len("Lib/") :]
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        n += 1
    left = [
        p for p in (TREE / "Lib/test").rglob("*")
        if p.is_file() and str(p.relative_to(TREE)) not in set(members)
    ]
    (OUT / "judge").mkdir(parents=True)
    shutil.copyfile(HERE / "drive.py", OUT / "judge/drive.py")
    print(f"staged {n} members; {len(missing)} missing from the tree; {len(left)} non-members left out")
    for p in missing[:10]:
        print("missing", p)


if __name__ == "__main__":
    main()
