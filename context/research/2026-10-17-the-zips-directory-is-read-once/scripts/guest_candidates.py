"""Fuel of each part of zipimport's directory read, and of the candidate fixes, by zip size.

    uv run --no-sync python guest_candidates.py <artifact copy dir> <scratch zips dir> <out.tsv>

Every case runs PRELUDE (candidates.py exec'd, so the compile is the same in every case) and then
one body. A body's cost is its fuel minus the 'base' case's fuel on the same binary and zip; the
cost per member is the slope of that difference between zip-1x (1,751) and zip-4x (7,004).
"""

from __future__ import annotations

import sys
from pathlib import Path

from wasi_python import Artifacts, run

ART, ZIPS, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
SRC = (Path(__file__).parent / "candidates.py").read_text()
PRELUDE = (
    f"_src = {SRC!r}\n"
    "C = {}\nexec(compile(_src, 'candidates.py', 'exec'), C)\n"
    "import zipimport as z, marshal, functools, types, hashlib\n"
    "P = '/usr/local/lib/python315.zip'\n"
    "D = z._zip_directory_cache[P]\n"
)
TZ = (
    "import zoneinfo, zoneinfo._common as zc, datetime\n"
    "KEYS = sorted(k[16:] for k, v in D.items() if v is not None and k.startswith('tzdata/zoneinfo/')"
    " and not k.endswith('.pyc') and k[16:] not in ('zones', 'tzdata.zi', 'leapseconds', 'zonenow.tab',"
    " 'iso3166.tab', 'zone.tab', 'zone1970.tab'))\n"
)
PARIS = (
    "t = zoneinfo.ZoneInfo('Europe/Paris'); "
    "print(t.utcoffset(datetime.datetime(2026, 7, 1)), len(KEYS))\n"
)
BODIES = {
    "base": "pass",
    # zipimport's own reader, as the start runs it, and with parts swapped for C calls.
    "zipimport x1": "z._read_directory(P)",
    "zipimport, unpack helpers as C calls": "f = functools.partial(int.from_bytes, byteorder='little')\n"
    "z._unpack_uint16 = z._unpack_uint32 = f\nz._read_directory(P)",
    "zipimport, _path_join as a C call": "z._bootstrap_external = types.SimpleNamespace(_path_join=str.__add__)\n"
    "z._read_directory(P)",
    "zipimport, both as C calls": "f = functools.partial(int.from_bytes, byteorder='little')\n"
    "z._unpack_uint16 = z._unpack_uint32 = f\n"
    "z._bootstrap_external = types.SimpleNamespace(_path_join=str.__add__)\nz._read_directory(P)",
    # Rewrites: one read of the directory, then a loop over a bytes object.
    "rewrite struct, no implied dirs": "C['read_directory_struct'](P, implied=False)",
    "rewrite struct": "d = C['read_directory_struct'](P); print(d == D, len(d))",
    "rewrite from_bytes": "d = C['read_directory_from_bytes'](P); print(d == D, len(d))",
    # A pre-parsed index: marshal.loads of zipimport's dict (the dumps is in both cases).
    "marshal dumps": "b = marshal.dumps(D); print(len(b))",
    "marshal dumps + loads": "b = marshal.dumps(D); d = marshal.loads(b); print(d == D, len(b))",
    # Resource reads: stock, ZipReader with a cached root, and the zipimport-backed reader.
    "tz base": TZ,
    "stock: Paris": TZ + PARIS,
    "stock: Paris + 4 more": TZ + PARIS + "for k in KEYS[:4]: zc.load_tzdata(k).close()",
    "cached root: Paris": TZ + "C['cache_zipreader_roots']()\n" + PARIS,
    "cached root: Paris + 4 more": TZ + "C['cache_zipreader_roots']()\n" + PARIS
    + "for k in KEYS[:4]: zc.load_tzdata(k).close()",
    "cached root: Paris + every zone": TZ + "C['cache_zipreader_roots']()\n" + PARIS
    + "for k in KEYS: zc.load_tzdata(k).close()",
    "index: Paris": TZ + "C['use_index_reader']()\n" + PARIS,
    "index: Paris + 4 more": TZ + "C['use_index_reader']()\n" + PARIS
    + "for k in KEYS[:4]: zc.load_tzdata(k).close()",
    "index: Paris + every zone": TZ + "C['use_index_reader']()\n" + PARIS
    + "for k in KEYS: zc.load_tzdata(k).close()",
    # The same bytes through both readers, and the reader's tree, compared.
    "index: equal to stock": TZ + "import importlib.resources as r\n"
    "a = {k: zc.load_tzdata(k).read() for k in KEYS[:40]}\n"
    "s = sorted(p.name for p in r.files('tzdata.zoneinfo').joinpath('Europe').iterdir())\n"
    "t = r.files('tzdata').joinpath('zoneinfo/tzdata.zi').read_text()\n"
    "C['use_index_reader']()\n"
    "b = {k: zc.load_tzdata(k).read() for k in KEYS[:40]}\n"
    "s2 = sorted(p.name for p in r.files('tzdata.zoneinfo').joinpath('Europe').iterdir())\n"
    "t2 = r.files('tzdata').joinpath('zoneinfo/tzdata.zi').read_text()\n"
    "print(a == b, s == s2, t == t2, len(s), len(t), r.files('tzdata').joinpath('nope').is_file())",
    # importlib.metadata parses the zip once per process (its own cache).
    "metadata miss x2": "import importlib.metadata as m\nfor _ in range(2):\n"
    "    try: m.version('nope')\n    except m.PackageNotFoundError: pass",
    "metadata import": "import importlib.metadata as m",
}
SNAPSHOT = ["base", "zipimport x1", "rewrite struct", "marshal dumps", "marshal dumps + loads", "tz base",
            "stock: Paris", "stock: Paris + 4 more", "cached root: Paris", "cached root: Paris + 4 more",
            "index: Paris", "index: Paris + 4 more", "index: Paris + every zone", "index: equal to stock",
            "metadata import", "metadata miss x2"]
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


for case in SNAPSHOT:
    one("snapshot", "zip-1x", 1751, case)
for zname, n in (("zip-1x", 1751), ("zip-4x", 7004)):
    for case in BODIES:
        if case == "cached root: Paris + every zone" and zname == "zip-4x":
            continue
        one("plain", zname, n, case)
OUT.write_text("\n".join(rows) + "\n")
