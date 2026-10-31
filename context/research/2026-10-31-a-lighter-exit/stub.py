"""Write a copy of a wasm module whose named functions return at once (a spike tool: void
functions get `return`; i32 functions get `i32.const VALUE; return`).
usage: stub.py <in.wasm> <out.wasm> name[=i32value] ..."""
import sys
def leb(b, i):
    r = s = 0
    while True:
        x = b[i]; i += 1; r |= (x & 0x7F) << s; s += 7
        if x < 0x80: return r, i
def enc(n):
    out = bytearray()
    while True:
        x = n & 0x7F; n >>= 7
        if n: out.append(x | 0x80)
        else: out.append(x); return bytes(out)
def sleb(v):
    out = bytearray()
    while True:
        x = v & 0x7F; v >>= 7
        if (v == 0 and not x & 0x40) or (v == -1 and x & 0x40): out.append(x); return bytes(out)
        out.append(x | 0x80)
src, dst, *want = sys.argv[1:]
want = dict((w.split("=") + [None])[:2] for w in want)
data = open(src, "rb").read()
secs = []; i = 8
while i < len(data):
    sid = data[i]; n, j = leb(data, i + 1); secs.append((sid, j, j + n, i)); i = j + n
nimp = 0; names = {}
for sid, a, b, _ in secs:
    if sid == 2:
        cnt, k = leb(data, a)
        for _ in range(cnt):
            l, k = leb(data, k); k += l; l, k = leb(data, k); k += l
            kind = data[k]; k += 1
            if kind == 0: _, k = leb(data, k); nimp += 1
            elif kind == 1: k += 1; f = data[k]; k += 1; _, k = leb(data, k); k = leb(data, k)[1] if f & 1 else k
            elif kind == 2: f = data[k]; k += 1; _, k = leb(data, k); k = leb(data, k)[1] if f & 1 else k
            elif kind == 3: k += 2
            elif kind == 4: k += 1; _, k = leb(data, k)
    if sid == 0:
        l, k = leb(data, a)
        if data[k:k + l] == b"name":
            k += l
            while k < b:
                sub = data[k]; sl, k2 = leb(data, k + 1)
                if sub == 1:
                    cnt, m = leb(data, k2)
                    for _ in range(cnt):
                        idx, m = leb(data, m); l2, m = leb(data, m); names[data[m:m + l2].decode()] = idx; m += l2
                k = k2 + sl
targets = {}
for nm, v in want.items():
    targets[names[nm] - nimp] = v
out = bytearray(data[:8])
for sid, a, b, start in secs:
    if sid != 10:
        out += data[start:b]; continue
    cnt, k = leb(data, a); body = bytearray(enc(cnt))
    for idx in range(cnt):
        sz, k = leb(data, k); fb = data[k:k + sz]; k += sz
        if idx in targets:
            nl, m = leb(fb, 0)
            for _ in range(nl): _, m = leb(fb, m); m += 1
            ins = b"\x0f" if targets[idx] is None else b"\x41" + sleb(int(targets[idx])) + b"\x0f"
            fb = fb[:m] + ins + fb[m:]
        body += enc(len(fb)) + fb
    out += bytes([10]) + enc(len(body)) + body
open(dst, "wb").write(out)
print("stubbed", {n: names[n] for n in want}, "imports", nimp)
