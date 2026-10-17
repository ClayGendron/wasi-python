"""Bytes of the reactor's code and data that come from each new library, from wasm-ld's link map
(build/link/python.map): the Size column of every input section, summed by where it came from.

    mapsizes.py <python.map>
"""

import re
import sys
from collections import Counter

GROUPS = {
    "libsqlite3.a": "SQLite (libsqlite3.a)",
    "liblzma.a": "liblzma (liblzma.a)",
    "libbz2.a": "bzip2 (libbz2.a)",
    "Modules/_sqlite/": "CPython _sqlite3 module",
    "_bz2module.o": "CPython _bz2 module",
    "_lzmamodule.o": "CPython _lzma module",
}
size = Counter()
section = None
for line in open(sys.argv[1]):
    parts = line.split(None, 4)
    if len(parts) >= 4 and parts[0] == "-" and re.fullmatch(r"[0-9a-f]+", parts[2]) and parts[3] in ("TYPE", "IMPORT", "FUNCTION", "TABLE", "MEMORY", "TAG", "GLOBAL", "EXPORT", "ELEM", "CODE", "DATA", "DATACOUNT") and len(parts) == 4:
        section = parts[3]
        continue
    if len(parts) < 4 or not re.fullmatch(r"[0-9a-f]+", parts[2]):
        continue
    src = parts[3]
    for key, name in GROUPS.items():
        if key in src and ":(" in src:
            size[(name, section)] += int(parts[2], 16)
for (name, sec), n in sorted(size.items()):
    print(f"{name:28} {sec:6} {n:>9,}")
totals = Counter()
for (name, _), n in size.items():
    totals[name] += n
print("total", f"{sum(totals.values()):,}")
for name, n in totals.most_common():
    print(f"  {name:28} {n:>9,}")
