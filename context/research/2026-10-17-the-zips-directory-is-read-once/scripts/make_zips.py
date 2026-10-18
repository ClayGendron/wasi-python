"""Scratch zips of N members from today's stdlib zip, for counting fuel per member.

    uv run --no-sync python -I make_zips.py <today's python-stdlib.zip> <scratch dir>

Writes into the scratch dir (never into git):
  zip-1x.zip   today's members, unchanged (a copy)
  zip-2x.zip   today's members plus one copy of each under pad1/   (2 x 1,751)
  zip-3x.zip   ... plus pad2/                                        (3 x 1,751)
  zip-4x.zip   ... plus pad3/                                        (4 x 1,751)
  zip-4x-stored.zip  zip-4x's members, stored (no compression)
A copy keeps each member's name length, compression and bytes, so the padding looks like the real
members to zipimport and to zipfile. Nothing imports from pad*/: they only lengthen the directory.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

SRC, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(SRC) as z:
    members = [(i, z.read(i)) for i in z.infolist()]


def write(path: Path, copies: int, compress: int | None = None) -> None:
    with zipfile.ZipFile(path, "w") as out:
        for c in range(copies):
            prefix = "" if c == 0 else f"pad{c}/"
            for info, data in members:
                new = zipfile.ZipInfo(prefix + info.filename, info.date_time)
                new.compress_type = info.compress_type if compress is None else compress
                new.external_attr = info.external_attr
                out.writestr(new, data, compresslevel=9)
    with zipfile.ZipFile(path) as z:
        n = len(z.infolist())
    print(f"{path.name}\t{n}\t{path.stat().st_size}")


for k in (1, 2, 3, 4):
    write(OUT / f"zip-{k}x.zip", k)
write(OUT / "zip-4x-stored.zip", 4, zipfile.ZIP_STORED)
