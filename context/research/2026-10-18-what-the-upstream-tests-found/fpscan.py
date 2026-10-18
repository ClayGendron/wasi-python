"""Find C callbacks whose wasm type differs from the type CPython calls them with.

Reads a linked wasm32 module: its types, functions, element segment (table index -> function)
and active data segments (the static memory image). Finds PyMethodDef and PyGetSetDef arrays in
the image (entries ending in an all-zero entry) and checks each callback's function type against
the type its flags (or slot) say CPython calls it with. Also reads the name section for names.
"""
import re
import struct
import sys

I = "i32"


class R:
    def __init__(self, b, p=0):
        self.b, self.p = b, p

    def u8(self):
        v = self.b[self.p]; self.p += 1; return v

    def uleb(self):
        r = s = 0
        while True:
            x = self.u8(); r |= (x & 0x7F) << s; s += 7
            if x < 0x80: return r

    def sleb(self):
        r = s = 0
        while True:
            x = self.u8(); r |= (x & 0x7F) << s; s += 7
            if x < 0x80:
                if x & 0x40: r -= 1 << s
                return r

    def bytes(self, n):
        v = self.b[self.p:self.p + n]; self.p += n; return v

    def name(self):
        return self.bytes(self.uleb()).decode()


VT = {0x7F: "i32", 0x7E: "i64", 0x7D: "f32", 0x7C: "f64", 0x7B: "v128", 0x70: "funcref", 0x6F: "externref"}


def const_expr(r):
    op = r.u8()
    if op == 0x41: v = r.sleb()
    elif op == 0x23: v = ("global", r.uleb())
    else: raise ValueError(hex(op))
    assert r.u8() == 0x0B
    return v


def parse(b):
    assert b[:4] == b"\0asm"
    r = R(b, 8)
    types, imported_funcs, funcs, elems, data, names = [], [], [], {}, [], {}
    while r.p < len(b):
        sid = r.u8(); size = r.uleb(); end = r.p + size
        if sid == 1:
            for _ in range(r.uleb()):
                assert r.u8() == 0x60
                ps = tuple(VT.get(r.u8(), "other") for _ in range(r.uleb()))
                rs = tuple(VT.get(r.u8(), "other") for _ in range(r.uleb()))
                types.append((ps, rs))
        elif sid == 2:
            for _ in range(r.uleb()):
                m, n, k = r.name(), r.name(), r.u8()
                if k == 0: imported_funcs.append(r.uleb())
                elif k == 1: r.u8(); fl = r.uleb(); r.uleb(); (fl & 1) and r.uleb()
                elif k == 2: fl = r.uleb(); r.uleb(); (fl & 1) and r.uleb()
                elif k == 3: r.u8(); r.u8()
                elif k == 4: r.u8(); r.uleb()
        elif sid == 3:
            funcs = [r.uleb() for _ in range(r.uleb())]
        elif sid == 9:
            for _ in range(r.uleb()):
                fl = r.uleb()
                assert fl in (0, 2), fl
                if fl == 2: r.uleb()
                off = const_expr(r)
                if fl == 2: assert r.u8() == 0
                idx = [r.uleb() for _ in range(r.uleb())]
                for i, f in enumerate(idx): elems[off + i] = f
        elif sid == 11:
            for _ in range(r.uleb()):
                fl = r.uleb()
                if fl == 1: r.bytes(r.uleb()); continue
                if fl == 2: r.uleb()
                off = const_expr(r)
                data.append((off, r.bytes(r.uleb())))
        elif sid == 0:
            nm = r.name()
            if nm == "name":
                while r.p < end:
                    sub = r.u8(); ssz = r.uleb(); send = r.p + ssz
                    if sub == 1:
                        for _ in range(r.uleb()):
                            i = r.uleb(); names[i] = r.name()
                    r.p = send
        r.p = end
    ftype = {i: types[t] for i, t in enumerate(imported_funcs)}
    ftype.update({len(imported_funcs) + i: types[t] for i, t in enumerate(funcs)})
    return ftype, elems, data, names


METH = {0x1: (I, I), 0x3: (I, I, I), 0x4: (I, I), 0x8: (I, I), 0x80: (I, I, I),
        0x82: (I, I, I, I), 0x282: (I, I, I, I, I)}
MODS = 0x10 | 0x20 | 0x40
IDENT = re.compile(rb"[A-Za-z_][A-Za-z0-9_]{0,80}\0")


def main(path):
    ftype, elems, data, names = parse(open(path, "rb").read())
    segs = sorted(data)
    base, mem = segs[0][0], bytearray()
    for off, d in segs:
        if off - base > len(mem): mem += bytes(off - base - len(mem))
        mem[off - base:off - base + len(d)] = d

    def at(addr, n=4):
        o = addr - base
        return mem[o:o + n] if 0 <= o <= len(mem) - n else None

    def cstr(addr):
        o = addr - base
        if not (0 <= o < len(mem)): return None
        m = IDENT.match(mem, o)
        return m.group()[:-1].decode() if m else None

    def word(o):
        return struct.unpack_from("<I", mem, o)[0]

    def fn(idx):
        f = elems.get(idx)
        return (f, ftype.get(f), names.get(f, f"func{f}")) if f is not None else None

    bad, checked = [], {"method": 0, "getset": 0, "member": 0}
    n = len(mem) - 20
    # PyMemberDef: 20-byte entries {name, type <= 20, offset, flags, doc}, ending in a zero entry.
    # Their bytes are skipped below, so a type code is never read as a function pointer.
    members = set()
    for o in range(0, n, 4):
        run, p = [], o
        while p < n - 20:
            nm, ty, off, fl, doc = struct.unpack_from("<IIIII", mem, p)
            if not (nm and cstr(nm) and ty <= 20 and fl <= 0xF and (not doc or at(doc, 1) is not None)):
                break
            run.append(p); p += 20
        if run and mem[p:p + 20] == bytes(20):
            for q in run:
                members.update(range(q, q + 20))
            checked["member"] += len(run)
    seen = set(members)
    # PyMethodDef: 16-byte entries, an array ends with an all-zero entry.
    for o in range(0, n, 4):
        if o in seen: continue
        run, p = [], o
        while p < n and p not in members:
            nm, meth, flags, doc = struct.unpack_from("<IIII", mem, p)
            name = cstr(nm) if nm else None
            if not name or meth not in elems or (flags & ~MODS) not in METH or (doc and at(doc, 1) is None):
                break
            run.append((p, name, meth, flags)); p += 16
        if run and mem[p:p + 16] == bytes(16):
            for q, name, meth, flags in run:
                seen.add(q)
                members.update(range(q, q + 16))
                f, (ps, rs), fname = fn(meth)
                checked["method"] += 1
                want = METH[flags & ~MODS]
                if ps != want or rs != (I,):
                    bad.append(f"method {name!r} -> {fname} {ps}->{rs}, flags {flags:#x} want {want}->('i32',)")
    # PyGetSetDef: 20-byte entries {name, get, set, doc, closure}, ending with an all-zero entry.
    seen2 = set(members)
    for o in range(0, n, 4):
        if o in seen2: continue
        run, p = [], o
        while p < n - 20 and p not in members:
            nm, get, set_, doc, clo = struct.unpack_from("<IIIII", mem, p)
            name = cstr(nm) if nm else None
            if not name or not (get or set_) or (get and get not in elems) or (set_ and set_ not in elems) or (doc and at(doc, 1) is None):
                break
            run.append((p, name, get, set_)); p += 20
        if run and mem[p:p + 20] == bytes(20):
            for q, name, get, set_ in run:
                seen2.add(q)
                checked["getset"] += 1
                if get:
                    f, (ps, rs), fname = fn(get)
                    if ps != (I, I) or rs != (I,):
                        bad.append(f"getter {name!r} -> {fname} {ps}->{rs} want (i32, i32)->i32")
                if set_:
                    f, (ps, rs), fname = fn(set_)
                    if ps != (I, I, I) or rs != (I,):
                        bad.append(f"setter {name!r} -> {fname} {ps}->{rs} want (i32, i32, i32)->i32")
    print("checked", checked, "elems", len(elems), "names", len(names))
    for b in sorted(set(bad)):
        print("MISMATCH", b)


if __name__ == "__main__":
    main(sys.argv[1])
