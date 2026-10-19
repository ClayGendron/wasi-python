"""Section sizes, import list and function count of two wasm modules, side by side.

usage: wasm_sections.py OLD.wasm NEW.wasm
"""

import sys

NAMES = {0: "custom", 1: "type", 2: "import", 3: "function", 4: "table", 5: "memory", 6: "global",
         7: "export", 8: "start", 9: "element", 10: "code", 11: "data", 12: "datacount", 13: "tag"}


def leb(b, i):
    r = s = 0
    while True:
        x = b[i]
        i += 1
        r |= (x & 0x7F) << s
        s += 7
        if x < 0x80:
            return r, i


def name(b, i):
    n, i = leb(b, i)
    return b[i:i + n].decode("utf-8", "replace"), i + n


def read(path):
    b = open(path, "rb").read()
    assert b[:4] == b"\0asm"
    i, sizes, imports, nfunc = 8, {}, [], 0
    while i < len(b):
        sid = b[i]
        size, j = leb(b, i + 1)
        key = NAMES.get(sid, str(sid))
        if sid == 0:
            cname, _ = name(b, j)
            key = f"custom:{cname}"
        if sid == 2:
            n, k = leb(b, j)
            for _ in range(n):
                mod, k = name(b, k)
                fld, k = name(b, k)
                kind = b[k]
                k += 1
                imports.append(f"{mod}.{fld}:{kind}")
                if kind == 0:
                    _, k = leb(b, k)
                elif kind == 1:
                    k += 1
                    flags, k = leb(b, k)
                    _, k = leb(b, k)
                    if flags & 1:
                        _, k = leb(b, k)
                elif kind == 2:
                    flags, k = leb(b, k)
                    _, k = leb(b, k)
                    if flags & 1:
                        _, k = leb(b, k)
                elif kind == 3:
                    k += 2
                elif kind == 4:
                    k += 1
                    _, k = leb(b, k)
        if sid == 10:
            nfunc, _ = leb(b, j)
        sizes[key] = sizes.get(key, 0) + size
        i = j + size
    return len(b), sizes, imports, nfunc


a, b = read(sys.argv[1]), read(sys.argv[2])
print(f"total {a[0]:,} -> {b[0]:,} ({b[0] - a[0]:+,})")
print(f"functions with bodies {a[3]:,} -> {b[3]:,} ({b[3] - a[3]:+,})")
for k in sorted(set(a[1]) | set(b[1])):
    x, y = a[1].get(k, 0), b[1].get(k, 0)
    print(f"  {k:28} {x:>12,} -> {y:>12,} ({y - x:+,})")
print(f"imports {len(a[2])} -> {len(b[2])}; only old: {sorted(set(a[2]) - set(b[2]))}; "
      f"only new: {sorted(set(b[2]) - set(a[2]))}")
print("import modules:", sorted({s.split('.')[0] for s in b[2]}))
