"""Function body sizes by name (code section + name section) of a wasm module; print those that differ between two."""
import sys
def leb(b, i):
    r = s = 0
    while True:
        x = b[i]; i += 1; r |= (x & 0x7F) << s; s += 7
        if x < 0x80: return r, i
def load(p):
    d = open(p, "rb").read(); i = 8; nimp = 0; sizes = []; names = {}
    while i < len(d):
        sid = d[i]; size, j = leb(d, i + 1); end = j + size
        if sid == 2:
            n, k = leb(d, j)
            for _ in range(n):
                l, k = leb(d, k); k += l; l, k = leb(d, k); k += l
                kind = d[k]; k += 1
                if kind == 0: _, k = leb(d, k); nimp += 1
                elif kind == 1: k += 1; f = d[k]; k += 1; _, k = leb(d, k); k = leb(d, k)[1] if f & 1 else k
                elif kind == 2: f = d[k]; k += 1; _, k = leb(d, k); k = leb(d, k)[1] if f & 1 else k
                elif kind == 3: k += 2
                elif kind == 4: k += 1; _, k = leb(d, k)
        elif sid == 10:
            n, k = leb(d, j)
            for _ in range(n):
                s, k = leb(d, k); sizes.append(s); k += s
        elif sid == 0:
            l, k = leb(d, j); nm = d[k:k+l]; k += l
            if nm == b"name":
                while k < end:
                    sub = d[k]; ss, k2 = leb(d, k + 1)
                    if sub == 1:
                        n, q = leb(d, k2)
                        for _ in range(n):
                            idx, q = leb(d, q); l, q = leb(d, q); names[idx] = d[q:q+l].decode(errors="replace"); q += l
                    k = k2 + ss
        i = end
    return {names.get(nimp + i, str(nimp + i)): s for i, s in enumerate(sizes)}
a, b = load(sys.argv[1]), load(sys.argv[2])
for k in sorted(set(a) | set(b)):
    if a.get(k) != b.get(k): print(k, a.get(k), b.get(k))
