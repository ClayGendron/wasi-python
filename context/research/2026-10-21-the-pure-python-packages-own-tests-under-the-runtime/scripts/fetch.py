"""Fetch spec 067's test sources into one empty folder each and check their SHA-256.

A scratch tool for the survey. Reads the drafting evidence's three lists; each archive goes to
<out>/<name>/<file>. Nothing is unpacked or run here.

    uv run --no-project python -I fetch.py <evidence folder> <out>
"""

import hashlib
import subprocess
import sys
from pathlib import Path

ev, out = Path(sys.argv[1]), Path(sys.argv[2])
TAGGED = {"cycler", "openpyxl", "et-xmlfile", "xlsxwriter", "xlrd", "tomli-w", "cloudpickle",
          "threadpoolctl"}
rows = []  # (name, sha, url, filename)
for line in (ev / "sdists.txt").read_text().splitlines():
    if line.startswith("#") or not line.strip():
        continue
    nv, sha, _size, url = line.split()[:4]
    name = nv.rsplit("-", 1)[0]
    if nv.startswith("python-dateutil"):
        name = "python-dateutil"
    if name in TAGGED:
        continue
    rows.append((name, sha, url, url.rsplit("/", 1)[1]))
for line in (ev / "sdists-067-revision.txt").read_text().splitlines():
    p = line.split()
    if line.startswith("#") or len(p) != 4 or p[0] == "seaborn":
        continue
    rows.append((p[0], p[2], p[3], p[1]))
for line in (ev / "tag-archives.txt").read_text().splitlines():
    p = line.split()
    if line.startswith("#") or len(p) != 3:
        continue
    sha, url = p[0], p[2]
    name = next(t for t in TAGGED if t.replace("-", "_").lower() in url.lower().replace("-", "_"))
    if "et_xmlfile" in url:
        name = "et-xmlfile"
    rows.append((name, sha, url, f"{name}-tag.tar.gz"))

bad = 0
for name, sha, url, fn in rows:
    d = out / name
    d.mkdir(parents=True, exist_ok=True)
    f = d / fn
    if not f.exists():
        subprocess.run(["curl", "-sSfL", "--retry", "3", "-o", str(f), url], check=True)
    got = hashlib.sha256(f.read_bytes()).hexdigest()
    ok = got == sha
    bad += not ok
    print(("OK  " if ok else "BAD ") + f"{name} {fn} {got[:12]}")
print(f"{len(rows)} sources, {bad} bad")
