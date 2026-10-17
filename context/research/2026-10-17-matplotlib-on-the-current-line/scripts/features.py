"""Print a wasm module's target_features custom section and count atomic (0xFE) opcode prefixes roughly."""
import sys
def leb(b, i):
    r = s = 0
    while True:
        x = b[i]; i += 1; r |= (x & 0x7F) << s; s += 7
        if x < 0x80: return r, i
for path in sys.argv[1:]:
    d = open(path, "rb").read(); i = 8; feats = None
    while i < len(d):
        sid = d[i]; i += 1; size, i = leb(d, i); end = i + size
        if sid == 0:
            n, j = leb(d, i); name = d[j:j + n].decode()
            if name == "target_features":
                k = j + n; cnt, k = leb(d, k); feats = []
                for _ in range(cnt):
                    pre = chr(d[k]); k += 1; ln, k = leb(d, k); feats.append(pre + d[k:k + ln].decode()); k += ln
        i = end
    print(path.split("/")[-1], feats)
