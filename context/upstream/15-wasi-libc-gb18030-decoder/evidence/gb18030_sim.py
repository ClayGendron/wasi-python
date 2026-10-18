"""Model musl's GB18030 four-byte decoder in Python and compare it with CPython's codec.

Run: uv run --no-project python -I gb18030_sim.py GB18030_H GB18030UTF_H
  GB18030_H     wasi-libc 161b3195's libc-top-half/musl/src/locale/gb18030.h (the 2-byte table)
  GB18030UTF_H  musl 67219f0's src/locale/gb18030utf.h (the unmapped-range table of the fix)

"before" follows iconv.c at wasi-libc 161b3195 (lines 418-435) step by step, with the count of
table values v where `v - d <= c - d` in unsigned arithmetic (that is, d <= v <= c) done by
bisection instead of a 126x190 scan; the result is the same. "after" follows musl 67219f0.
Truth is CPython's own gb18030 codec. The repertoire is the one spec 046's whole-repertoire
check uses: U+00A0..U+FFFF without surrogates, private use U+E000..U+F8FF, U+FFFE, U+FFFF.
"""

import bisect
import re
import sys

nums = [int(x) for x in re.findall(r"\d+", open(sys.argv[1]).read())]
assert len(nums) == 126 * 190, len(nums)
table = sorted(nums)
pairs = [int(x, 0) for x in re.findall(r"0x[0-9a-fA-F]+|\d+", open(sys.argv[2]).read())]
ranges = list(zip(pairs[0::2], pairs[1::2]))


def count(lo, hi):  # how many table values v satisfy lo <= v <= hi
    return bisect.bisect_right(table, hi) - bisect.bisect_left(table, lo)


def linear(b):
    return (((b[0] - 0x81) * 10 + (b[1] - 0x30)) * 126 + (b[2] - 0x81)) * 10 + (b[3] - 0x30)


def before(b):
    c = linear(b) + 128
    d = 0
    while d <= c:
        k = count(d, c)
        d = c + 1
        c += k
    return c


def after(b):
    c = linear(b)
    if c >= 189000:
        return c - 189000 + 0x10000
    for start, length in ranges:
        if c < length:
            return c + start
        c -= length
    return None


print("2-byte table: %d entries, %d zero, %d distinct" % (len(nums), nums.count(0), len(set(nums))))
print("unmapped ranges in the fix: %d" % len(ranges))
rep = [
    cp
    for cp in range(0xA0, 0x10000)
    if not (0xD800 <= cp < 0xF900 or cp in (0xFFFE, 0xFFFF))
]
four = [(cp, chr(cp).encode("gb18030")) for cp in rep if len(chr(cp).encode("gb18030")) == 4]
print("repertoire %d characters, %d of them four-byte in CPython's codec" % (len(rep), len(four)))
bad_before = [(cp, b, before(b)) for cp, b in four if before(b) != cp]
bad_after = [(cp, b, after(b)) for cp, b in four if after(b) != cp]
print("before (wasi-libc 161b3195): %d decoded to another character" % len(bad_before))
print("  shifts seen: %s" % sorted({hex(cp - got) for cp, b, got in bad_before}))
print("  range of wrong ones: U+%04X..U+%04X" % (bad_before[0][0], bad_before[-1][0]))
for cp, b, got in bad_before[:3] + bad_before[-1:]:
    print("  U+%04X  %s -> U+%04X" % (cp, b.hex(" "), got))
print("after (musl 67219f0): %d decoded to another character" % len(bad_after))
for cp, b, got in bad_after[:5]:
    print("  U+%04X  %s -> %s" % (cp, b.hex(" "), "U+%04X" % got if got is not None else "ilseq"))
# Outside the BMP: CPython encodes U+10000 as 90 30 81 30.
for cp in (0x10000, 0x1F600, 0x10FFFF):
    b = chr(cp).encode("gb18030")
    print("U+%04X  %s -> before U+%04X, after U+%04X" % (cp, b.hex(" "), before(b), after(b)))
