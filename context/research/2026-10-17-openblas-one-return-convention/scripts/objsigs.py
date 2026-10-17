"""Every function signature in a wasm32 static archive, per object, from the objects themselves.

wasm-ld warns once per symbol, so after the first clash on a name it hides the rest. This reads each
object's type, import, function and linking sections and lists, for every global function name, each
distinct wasm type it is declared (imported) or defined with, and in which objects. A name with more than
one type is a clash, whatever wasm-ld chose to print.
usage: uv run python -I objsigs.py <archive> <out.txt>
"""
import collections, subprocess, sys, tempfile, pathlib

VT = {0x7F: "i32", 0x7E: "i64", 0x7D: "f32", 0x7C: "f64", 0x7B: "v128", 0x70: "funcref", 0x6F: "externref"}


class R:
    def __init__(s, b, p=0):
        s.b, s.p = b, p

    def u8(s):
        s.p += 1
        return s.b[s.p - 1]

    def u(s):
        r = sh = 0
        while True:
            x = s.u8(); r |= (x & 0x7F) << sh; sh += 7
            if x < 0x80:
                return r

    def name(s):
        n = s.u(); s.p += n
        return s.b[s.p - n:s.p].decode()


def parse(data):
    assert data[:4] == b"\0asm"
    r = R(data, 8); types = []; fimports = []; ftypes = []; syms = []
    while r.p < len(data):
        sid = r.u8(); size = r.u(); end = r.p + size
        if sid == 1:
            for _ in range(r.u()):
                assert r.u8() == 0x60
                ps = [VT[r.u8()] for _ in range(r.u())]; rs = [VT[r.u8()] for _ in range(r.u())]
                types.append(f"({', '.join(ps)}) -> {', '.join(rs) or 'void'}")
        elif sid == 2:
            for _ in range(r.u()):
                mod = r.name(); fld = r.name(); k = r.u8()
                if k == 0: fimports.append((fld, r.u()))
                elif k == 1: r.u8(); fl = r.u(); r.u(); r.u() if fl & 1 else None
                elif k == 2:  # memory: limits
                    fl = r.u(); r.u(); r.u() if fl & 1 else None
                elif k == 3: r.u8(); r.u8()  # global: valtype, mutability
                elif k == 4: r.u8(); r.u()
        elif sid == 3:
            ftypes = [r.u() for _ in range(r.u())]
        elif sid == 0:
            nm = r.name()
            if nm == "linking":
                r.u()
                while r.p < end:
                    st = r.u8(); ln = r.u(); se = r.p
                    if st == 8:
                        for _ in range(r.u()):
                            kind = r.u8(); flags = r.u()
                            if kind in (0, 2, 4, 5):
                                idx = r.u()
                                if not (flags & 0x10) or (flags & 0x40): nm2 = r.name()
                                else: nm2 = None
                                if kind == 0: syms.append((flags, idx, nm2))
                            elif kind == 1:
                                r.name()
                                if not flags & 0x10: r.u(); r.u(); r.u()
                            elif kind == 3: r.u()
                    r.p = se + ln
        r.p = end
    out = []
    nimp = len(fimports)
    for flags, idx, nm in syms:
        if flags & 0x02:  # local
            continue
        if flags & 0x10:  # undefined: an import
            fld, t = fimports[idx]
            out.append(("U", nm or fld, types[t]))
        else:
            out.append(("D", nm, types[ftypes[idx - nimp]]))
    return out


def read_ar(b):
    """GNU-format archive (what llvm-ar writes): '!<arch>', 60-byte headers, '//' long-name table."""
    assert b[:8] == b"!<arch>\n"
    p = 8; longnames = b""; out = []
    while p + 60 <= len(b):
        h = b[p:p + 60]; name = h[:16].decode().strip(); size = int(h[48:58]); p += 60
        data = b[p:p + size]; p += size + (size & 1)
        if name == "//": longnames = data; continue
        if name in ("/", "/SYM64/"): continue
        if name.startswith("/") and name[1:].isdigit():
            o = int(name[1:]); name = longnames[o:longnames.index(b"\n", o)].decode()
        out.append((name.rstrip("/"), data))
    return out


def main():
    ar, outp = sys.argv[1], sys.argv[2]
    seen = collections.defaultdict(lambda: collections.defaultdict(list))
    members = read_ar(pathlib.Path(ar).read_bytes())
    names = collections.Counter(m for m, _ in members)
    counts = collections.Counter()
    for m, data in members:
        counts[m] += 1
        tag = f"{m}#{counts[m]}" if names[m] > 1 else m
        for ud, nm, t in parse(data):
            seen[nm][t].append(f"{tag}:{ud}")
    clashes = {n: v for n, v in seen.items() if len(v) > 1}
    with open(outp, "w") as f:
        f.write(f"objects: {len(members)}  function names: {len(seen)}  names with more than one type: {len(clashes)}\n")
        for n in sorted(clashes):
            f.write(f"\n{n}\n")
            for t, objs in clashes[n].items():
                defs = [o for o in objs if o.endswith(":D")]
                f.write(f"  {t}  [{len(objs)} objects; defined in {', '.join(defs) or 'none'}]  e.g. {', '.join(objs[:4])}\n")
    print(open(outp).readline().strip())


main()
