"""Read llvm-objdump -d lines on stdin; for each br_table, decode the LEB128
target count from the encoded bytes (the count excludes the default label)."""
import sys
n = 0; mx = 0; mxaddr = None; hist = {}
for line in sys.stdin:
    if 'br_table' not in line: continue
    addr, rest = line.split(':', 1)
    hexpart = rest.split('\t')[0].split()
    bs = [int(h, 16) for h in hexpart]
    assert bs[0] == 0x0e
    r = s = 0; i = 1
    while True:
        x = bs[i]; i += 1; r |= (x & 0x7f) << s; s += 7
        if not x & 0x80: break
    n += 1
    if r > mx: mx, mxaddr = r, addr.strip()
    b = 1 << max(r, 1).bit_length()
    hist[b] = hist.get(b, 0) + 1
print(f'file={sys.argv[1]} br_table_count={n} max_targets_excl_default={mx} max_at=0x{mxaddr} pow2_hist={sorted(hist.items())}')
