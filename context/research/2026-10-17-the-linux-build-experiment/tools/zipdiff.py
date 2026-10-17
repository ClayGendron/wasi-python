"""Compare two zips member by member: names and order, then each differing member's bytes.

    python -I zipdiff.py a.zip b.zip [--show]
"""

import sys
import zipfile
import difflib

a, b = zipfile.ZipFile(sys.argv[1]), zipfile.ZipFile(sys.argv[2])
na, nb = a.namelist(), b.namelist()
print(f"members: {len(na)} vs {len(nb)}; same names: {set(na) == set(nb)}; same order: {na == nb}")
for n in sorted(set(na) ^ set(nb)):
    print(f"only in {'a' if n in na else 'b'}: {n}")
diff = [n for n in na if n in nb and a.read(n) != b.read(n)]
print(f"differing members: {len(diff)}")
for n in diff:
    da, db = a.read(n), b.read(n)
    print(f"  {n}: {len(da)} vs {len(db)} bytes")
    if "--show" in sys.argv and n.endswith(".pyc"):
        import marshal
        ca, cb = marshal.loads(da[16:]), marshal.loads(db[16:])
        ka = [c for c in ca.co_consts if isinstance(c, (str, dict, tuple))]
        kb = [c for c in cb.co_consts if isinstance(c, (str, dict, tuple))]
        for line in difflib.unified_diff(repr(ka).split(", "), repr(kb).split(", "), lineterm="", n=0):
            print("     ", line[:220])
