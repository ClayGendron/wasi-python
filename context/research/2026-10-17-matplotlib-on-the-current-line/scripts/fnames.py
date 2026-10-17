import sys
def leb(b, i):
    r = s = 0
    while True:
        x = b[i]; i += 1; r |= (x & 0x7F) << s; s += 7
        if x < 0x80: return r, i
d = open(sys.argv[1], "rb").read(); want = {int(x) for x in sys.argv[2:]}; i = 8
while i < len(d):
    sid = d[i]; i += 1; size, i = leb(d, i); end = i + size
    if sid == 0:
        n, j = leb(d, i)
        if d[j:j + n] == b"name":
            k = j + n
            while k < end:
                sub = d[k]; k += 1; ln, k = leb(d, k); se = k + ln
                if sub == 1:
                    cnt, k = leb(d, k)
                    for _ in range(cnt):
                        idx, k = leb(d, k); nl, k = leb(d, k)
                        if idx in want: print(idx, d[k:k + nl].decode())
                        k += nl
                k = se
    i = end
