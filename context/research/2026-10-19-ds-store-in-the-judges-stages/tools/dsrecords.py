"""List (name, code, type) records in .DS_Store files by scanning for record headers."""
import re, struct, sys, collections
TYPES = {b"long":4, b"shor":4, b"bool":1, b"comp":8, b"dutc":8, b"type":4, b"blob":None, b"ustr":None}
def records(data):
    data = data + bytes(16)
    out = []
    i = 0
    n = len(data)
    while i + 4 < n:
        (ln,) = struct.unpack(">I", data[i:i+4])
        if 0 < ln < 256 and i + 4 + 2*ln + 8 <= n:
            try:
                name = data[i+4:i+4+2*ln].decode("utf-16-be")
            except UnicodeDecodeError:
                i += 1; continue
            code = data[i+4+2*ln:i+8+2*ln]; typ = data[i+8+2*ln:i+12+2*ln]
            if typ in TYPES and re.fullmatch(rb"[A-Za-z0-9 ]{4}", code) and name.isprintable():
                j = i + 12 + 2*ln
                if typ == b"comp" or typ == b"dutc":
                    val = struct.unpack(">Q", data[j:j+8])[0]; j += 8
                elif typ in (b"long", b"shor", b"type"):
                    val = data[j:j+4].hex(); j += 4
                elif typ == b"bool":
                    val = data[j]; j += 1
                elif typ == b"blob":
                    (bl,) = struct.unpack(">I", data[j:j+4]); val = f"blob[{bl}]"; j += 4 + bl
                else:
                    (ul,) = struct.unpack(">I", data[j:j+4]); val = data[j+4:j+4+2*ul].decode("utf-16-be", "replace"); j += 4 + 2*ul
                out.append((name, code.decode(), typ.decode(), val)); i = j; continue
        i += 1
    return out
codes = collections.Counter()
for p in sys.argv[1:]:
    try:
        rs = records(open(p, "rb").read())
    except OSError as e:
        print(p, e); continue
    for r in rs: codes[r[1]] += 1
    if len(sys.argv) <= 6:
        print("==", p)
        for r in rs[:12]: print("  ", r)
        if len(rs) > 12: print("   ...", len(rs), "records")
print("codes:", dict(codes))
