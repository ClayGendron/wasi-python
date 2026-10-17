"""Compare two Wizer snapshots' initial memory, from their active data segments, by data symbol.

    python -I memdiff.py a.wasm b.wasm python.map
"""

import bisect
import re
import sys


def leb(b, i):
    r = s = 0
    while True:
        x = b[i]; i += 1
        r |= (x & 0x7F) << s; s += 7
        if x < 0x80:
            return r, i


def sections(b):
    i = 8
    while i < len(b):
        sid = b[i]; size, i = leb(b, i + 1)
        yield sid, b[i:i + size]
        i += size


def memory(path):
    b = open(path, "rb").read()
    mem = bytearray()
    other = {}
    for sid, body in sections(b):
        if sid != 11:
            other.setdefault(sid, []).append(body)
            continue
        n, i = leb(body, 0)
        for _ in range(n):
            flag, i = leb(body, i)
            if flag == 1:  # passive: compared as bytes, not placed
                size, i = leb(body, i)
                other.setdefault("passive", []).append(body[i:i + size])
                i += size
                continue
            if flag == 2:
                _, i = leb(body, i)
            assert body[i] == 0x41
            off, i = leb(body, i + 1)  # i32.const (non-negative offsets assumed)
            assert body[i] == 0x0B
            size, i = leb(body, i + 1)
            if len(mem) < off + size:
                mem.extend(b"\0" * (off + size - len(mem)))
            mem[off:off + size] = body[i:i + size]
            i += size
    return mem, other


ma, oa = memory(sys.argv[1])
mb, ob = memory(sys.argv[2])
for sid in sorted(set(oa) | set(ob), key=str):
    if oa.get(sid) != ob.get(sid):
        print(f"section {sid} differs")
n = max(len(ma), len(mb))
ma.extend(b"\0" * (n - len(ma))); mb.extend(b"\0" * (n - len(mb)))
diffs = [k for k in range(n) if ma[k] != mb[k]]
print(f"memory image: {n} bytes; differing bytes: {len(diffs)}")
rows = []
for line in open(sys.argv[3]):
    m = re.match(r"\s*([0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)\s+(\S.*)$", line)
    if m and not m[4].startswith(("<internal>", "/")) and ":(" not in m[4]:
        rows.append((int(m[1], 16), int(m[3], 16), m[4].strip()))
rows.sort()
addrs = [r[0] for r in rows]
from collections import Counter
by = Counter()
for k in diffs:
    j = bisect.bisect_right(addrs, k) - 1
    name = rows[j][2] if j >= 0 and k < rows[j][0] + max(rows[j][1], 1) else f"(heap, outside any symbol)"
    by[name] += 1
for name, c in by.most_common(25):
    print(f"  {c:8d}  {name}")
if diffs:
    print(f"first differing address: {diffs[0]:#x}, last: {diffs[-1]:#x}")
