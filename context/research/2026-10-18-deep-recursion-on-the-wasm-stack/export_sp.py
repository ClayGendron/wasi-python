"""Copy a wasm module, adding one export: global 0 (the C stack pointer) as "__sp". Research only."""
import sys

def leb(b, i):
    r = s = 0
    while True:
        x = b[i]; i += 1
        r |= (x & 0x7F) << s; s += 7
        if x < 0x80:
            return r, i

def uleb(n):
    out = bytearray()
    while True:
        x = n & 0x7F; n >>= 7
        out.append(x | (0x80 if n else 0))
        if not n:
            return bytes(out)

src, dst = sys.argv[1:]
data = open(src, "rb").read()
out = bytearray(data[:8])
i = 8
while i < len(data):
    sid = data[i]; i += 1
    size, j = leb(data, i)
    body = data[j:j + size]
    if sid == 7:
        n, k = leb(body, 0)
        name = b"__sp"
        body = uleb(n + 1) + body[k:] + uleb(len(name)) + name + bytes([3]) + uleb(0)
    out += bytes([sid]) + uleb(len(body)) + body
    i = j + size
open(dst, "wb").write(out)
