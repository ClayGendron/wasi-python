"""Where a plain start's per-member fuel goes, and what a resource read costs, by zip size.

    uv run --no-sync python guest_start.py <artifact copy dir> <scratch zips dir> <out.tsv>

Every case is one call on the plain reactor (snapshot=False) with fuel metered, on zips of
1,751 / 3,502 / 5,253 / 7,004 members (make_zips.py). The snapshot cases run on today's zip only:
the snapshot runs beside the exact zip it was built with. Differences between cases on one zip, and
slopes across zips, give the cost per member of each step.
"""

from __future__ import annotations

import sys
from pathlib import Path

from wasi_python import Artifacts, run

ART, ZIPS, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
P = "'/usr/local/lib/python315.zip'"

CASES = {
    "pass": "pass",
    # One more parse of the whole central directory by zipimport, after the start's own.
    "zipimport._read_directory x1": f"import zipimport as z; z._read_directory({P})",
    "zipimport._read_directory x3": f"import zipimport as z\nfor _ in range(3): z._read_directory({P})",
    # What the start left cached: which archives, and how many names (members + implied dirs).
    "cache after start": "import zipimport as z, io, os\n"
    "print({k: len(v) for k, v in z._zip_directory_cache.items()}, "
    f"os.stat({P}).st_blksize, io.DEFAULT_BUFFER_SIZE)",
    # zipfile's own parse, as importlib.resources' ZipReader does it on every files() call.
    "import zipfile": "import zipfile",
    "zipfile.ZipFile x1": f"import zipfile; zipfile.ZipFile({P}).close()",
    "zipfile.Path + name set x1": f"import zipfile; zipfile.Path({P}).root._name_set()",
    # importlib.resources on a package inside the zip.
    "import importlib.resources": "import importlib.resources as r",
    "resources.files x1": "import importlib.resources as r; r.files('tzdata.zoneinfo')",
    "resources read x1": "import importlib.resources as r\n"
    "r.files('tzdata.zoneinfo').joinpath('UTC').read_bytes()",
    "resources read x5": "import importlib.resources as r\n"
    "for k in ('UTC', 'GMT', 'EST', 'MST', 'HST'): r.files('tzdata.zoneinfo').joinpath(k).read_bytes()",
    "import zoneinfo": "import zoneinfo",
    "ZoneInfo Europe/Paris": "import zoneinfo; zoneinfo.ZoneInfo('Europe/Paris')",
    "ZoneInfo Paris+Tokyo": "import zoneinfo; zoneinfo.ZoneInfo('Europe/Paris'); "
    "zoneinfo.ZoneInfo('Asia/Tokyo')",
}
SNAPSHOT_CASES = [
    "pass",
    "zipimport._read_directory x1",
    "cache after start",
    "import importlib.resources",
    "resources read x1",
    "resources read x5",
    "import zoneinfo",
    "ZoneInfo Europe/Paris",
    "ZoneInfo Paris+Tokyo",
]

ZIP_SET = [("zip-1x", 1751), ("zip-2x", 3502), ("zip-3x", 5253), ("zip-4x", 7004), ("zip-4x-stored", 7004)]
rows = ["binary\tzip\tmembers\tcase\tfuel_used\texit\tstdout"]


def one(binary: str, zname: str, n: int, case: str) -> None:
    a = Artifacts(
        snapshot=ART / "python-snapshot.wasm",
        plain=ART / "python.wasm",
        stdlib_zip=ZIPS / f"{zname}.zip",
        manifest=ART / "MANIFEST",
    )
    r = run(["-c", CASES[case]], artifacts=a, snapshot=binary == "snapshot", fuel=10**13,
            deadline_s=3600, cache_dir=False)
    out = r.stdout.decode().strip().replace("\t", " ").replace("\n", " | ")[:300]
    if r.exit_code:
        out += " ERR " + r.stderr.decode().strip().splitlines()[-1][:200]
    rows.append(f"{binary}\t{zname}\t{n}\t{case}\t{r.fuel_used}\t{r.exit_code}\t{out}")
    print(rows[-1], flush=True)


for case in SNAPSHOT_CASES:
    one("snapshot", "zip-1x", 1751, case)
cases = sys.argv[4].split(",") if len(sys.argv) > 4 else list(CASES)
for zname, n in ZIP_SET:
    for case in cases:
        if zname == "zip-4x-stored" and case not in ("pass", "resources read x1"):
            continue
        one("plain", zname, n, case)
OUT.write_text("\n".join(rows) + "\n")
