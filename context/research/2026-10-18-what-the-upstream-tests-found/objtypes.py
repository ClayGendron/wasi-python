import sys
sys.path.insert(0, sys.argv[1])
from fpscan import R, VT
WANT = {"array_descr_set", "gentype___copy__", "_get_castingimpl", "sfloat___reduce__",
        "array_converter_get_scalar_input", "boundarraymethod__supports_unaligned"}
for path in sys.argv[2:]:
    b = open(path, "rb").read(); r = R(b, 8)
    types, nimp, funcs, syms = [], 0, [], {}
    while r.p < len(b):
        sid = r.u8(); size = r.uleb(); end = r.p + size
        if sid == 1:
            for _ in range(r.uleb()):
                r.u8(); ps = tuple(VT.get(r.u8(), "o") for _ in range(r.uleb())); rs = tuple(VT.get(r.u8(), "o") for _ in range(r.uleb())); types.append((ps, rs))
        elif sid == 2:
            for _ in range(r.uleb()):
                r.name(); r.name(); k = r.u8()
                if k == 0: r.uleb(); nimp += 1
                elif k == 1: r.u8(); fl = r.uleb(); r.uleb(); (fl & 1) and r.uleb()
                elif k == 2: fl = r.uleb(); r.uleb(); (fl & 1) and r.uleb()
                elif k == 3: r.u8(); r.u8()
                elif k == 4: r.u8(); r.uleb()
        elif sid == 3:
            funcs = [r.uleb() for _ in range(r.uleb())]
        elif sid == 0 and r.name() == "linking":
            r.uleb()
            while r.p < end:
                sub = r.u8(); ssz = r.uleb(); send = r.p + ssz
                if sub == 8:
                    for _ in range(r.uleb()):
                        kind = r.u8(); flags = r.uleb()
                        if kind in (0, 2, 4, 5):
                            idx = r.uleb()
                            if not (flags & 0x10) or (flags & 0x40):
                                nm = r.name()
                                if kind == 0: syms[nm] = idx
                        elif kind == 1:
                            nm = r.name()
                            if not (flags & 0x10): r.uleb(); r.uleb(); r.uleb()
                        elif kind == 3: r.uleb()
                r.p = send
        r.p = end
    for nm, idx in syms.items():
        if nm in WANT and idx >= nimp:
            print(path.split("/")[-2], nm, types[funcs[idx - nimp]])
