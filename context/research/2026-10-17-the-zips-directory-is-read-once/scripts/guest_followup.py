"""Follow-ups: importlib.metadata on a zip with a dist-info, and pandas time zones on the snapshot.

    uv run --no-sync python guest_followup.py <artifact copy dir> <scratch zips dir> <out.tsv>

Writes zip-1x-meta.zip and zip-4x-meta.zip (zip-1x / zip-4x plus one made-up
tabulate-0.9.0.dist-info/METADATA) into the scratch dir. Same PRELUDE as guest_candidates.py.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

from wasi_python import Artifacts, run

ART, ZIPS, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
for k in ("1x", "4x"):
    src, dst = ZIPS / f"zip-{k}.zip", ZIPS / f"zip-{k}-meta.zip"
    if not dst.exists():
        dst.write_bytes(src.read_bytes())
        with zipfile.ZipFile(dst, "a") as z:
            z.writestr("tabulate-0.9.0.dist-info/METADATA",
                       "Metadata-Version: 2.1\nName: tabulate\nVersion: 0.9.0\n")
SRC = (Path(__file__).parent / "candidates.py").read_text()
PRELUDE = (
    f"_src = {SRC!r}\n"
    "C = {}\nexec(compile(_src, 'candidates.py', 'exec'), C)\n"
    "import zipimport as z, importlib.metadata as m\n"
)
MISS = "try: m.version('nope')\nexcept m.PackageNotFoundError: print('miss')\n"
TZ = "import pandas as pd\n"
TS = ("print(pd.Timestamp('2026-07-01 12:00', tz='Europe/Paris').utcoffset(), "
      "list(pd.date_range('2026-01-01', periods=2, freq='D', tz='Asia/Tokyo').strftime('%z')))\n")
BODIES = {
    "base": "pass",
    "metadata version, stock": "print(m.version('tabulate'))",
    "metadata version, index": "C['use_index_metadata']()\nprint(m.version('tabulate'))",
    "metadata miss, stock": MISS,
    "metadata miss, index": "C['use_index_metadata']()\n" + MISS,
    "pandas base": TZ,
    "pandas tz, stock": TZ + TS,
    "pandas tz, index": TZ + "C['use_index_reader']()\n" + TS,
}
rows = ["binary\tzip\tmembers\tcase\tfuel_used\texit\tstdout"]


def one(binary: str, zname: str, n: int, case: str) -> None:
    a = Artifacts(snapshot=ART / "python-snapshot.wasm", plain=ART / "python.wasm",
                  stdlib_zip=ZIPS / f"{zname}.zip", manifest=ART / "MANIFEST")
    r = run(["-c", PRELUDE + BODIES[case]], artifacts=a, snapshot=binary == "snapshot",
            fuel=10**13, deadline_s=7200, cache_dir=False)
    out = r.stdout.decode().strip().replace("\t", " ").replace("\n", " | ")[:300]
    if r.exit_code:
        out += " ERR " + r.stderr.decode().strip().splitlines()[-1][:200]
    rows.append(f"{binary}\t{zname}\t{n}\t{case}\t{r.fuel_used}\t{r.exit_code}\t{out}")
    print(rows[-1], flush=True)


for case in ("base", "metadata miss, stock", "metadata miss, index", "pandas base", "pandas tz, stock",
             "pandas tz, index"):
    one("snapshot", "zip-1x", 1751, case)
for zname, n in (("zip-1x-meta", 1752), ("zip-4x-meta", 7005)):
    for case in BODIES:
        if not case.startswith("pandas"):
            one("plain", zname, n, case)
for case in ("pandas base", "pandas tz, stock", "pandas tz, index"):
    one("plain", "zip-1x", 1751, case)
OUT.write_text("\n".join(rows) + "\n")
