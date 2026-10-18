"""How a resource read's cost grows with the zip: zoneinfo and pytz on a small and a large zip.

    uv run --no-sync python guest_resources.py <profile dir> <out dir>

Small zip: today's stdlib zip plus pytz only. Large zip: guest/python-stdlib-ext.zip (today's
plus 5,609 members of candidates, pytz among them). Plain reactor, fuel metered.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

from wasi_python import Artifacts, artifacts, run

PROFILE, OUT = Path(sys.argv[1]), Path(sys.argv[2])
base = artifacts()
small = OUT / "python-stdlib-pytz.zip"
with zipfile.ZipFile(base.stdlib_zip) as z:
    have = {i.filename: (i, z.read(i)) for i in z.infolist()}
with zipfile.ZipFile(PROFILE / "zips" / "pytz.zip") as z:
    for i in z.infolist():
        have.setdefault(i.filename, (i, z.read(i)))
with zipfile.ZipFile(small, "w") as z:
    for name in sorted(have):
        z.writestr(have[name][0], have[name][1], compresslevel=9)
print("small zip members", len(have))
A = {
    "small": Artifacts(snapshot=base.snapshot, plain=base.plain, stdlib_zip=small, manifest=base.manifest),
    "large": Artifacts(snapshot=base.snapshot, plain=base.plain,
                       stdlib_zip=OUT / "guest" / "python-stdlib-ext.zip", manifest=base.manifest),
}
CASES = {
    "pass": "pass",
    "import zoneinfo": "import zoneinfo",
    "one ZoneInfo": "import zoneinfo; zoneinfo.ZoneInfo('Europe/Paris')",
    "two ZoneInfo": "import zoneinfo; zoneinfo.ZoneInfo('Europe/Paris'); zoneinfo.ZoneInfo('Asia/Tokyo')",
    "import pytz": "import pytz",
    "pytz.timezone": "import pytz; pytz.timezone('Europe/Paris')",
}
rows = ["zip\tcase\tfuel_used\texit"]
for zname, a in A.items():
    for cname, code in CASES.items():
        r = run(["-c", code], artifacts=a, snapshot=False, fuel=10**13, deadline_s=1800, cache_dir=False)
        rows.append(f"{zname}\t{cname}\t{r.fuel_used}\t{r.exit_code}")
        print(rows[-1], flush=True)
(OUT / "resources.tsv").write_text("\n".join(rows) + "\n")
