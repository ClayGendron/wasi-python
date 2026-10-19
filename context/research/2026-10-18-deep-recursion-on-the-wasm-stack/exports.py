"""List a wasm module's exports, globals' count and memory limits (a tiny section reader)."""
import sys

def leb(b, i):
    r = s = 0
    while True:
        x = b[i]; i += 1
        r |= (x & 0x7F) << s; s += 7
        if x < 0x80:
            return r, i

data = open(sys.argv[1], "rb").read()
i = 8
while i < len(data):
    sid = data[i]; i += 1
    size, i = leb(data, i)
    end = i + size
    if sid == 7:
        n, j = leb(data, i)
        for _ in range(n):
            ln, j = leb(data, j); name = data[j:j+ln].decode(); j += ln
            kind = data[j]; j += 1
            idx, j = leb(data, j)
            print("export", name, ["func","table","mem","global","tag"][kind], idx)
    if sid == 5:
        n, j = leb(data, i)
        flags = data[j]; j += 1
        mn, j = leb(data, j)
        print("memory min pages", mn, "flags", flags)
    if sid == 6:
        n, j = leb(data, i)
        print("globals", n)
        # first global: type, mut, init expr
        t = data[j]; mut = data[j+1]; op = data[j+2]
        v, _ = leb(data, j+3)
        print("global0 type", hex(t), "mut", mut, "op", hex(op), "init(uleb)", v)
    i = end
