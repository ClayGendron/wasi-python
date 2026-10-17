"""Classify wasm-ld signature-mismatch warnings: result-only (int vs void) or parameter difference.
usage: uv run python -I classify.py <link log>"""
import re, sys
lines = open(sys.argv[1]).read().splitlines()
out = []
i = 0
while i < len(lines):
    m = re.search(r"function signature mismatch: (\S+)", lines[i])
    if m:
        a = re.match(r">>> defined as \((.*?)\) -> (\S+) in .*\((.*?)\)$", lines[i + 1])
        b = re.match(r">>> defined as \((.*?)\) -> (\S+) in .*\((.*?)\)$", lines[i + 2])
        pa, ra, oa = a.groups(); pb, rb, ob = b.groups()
        kind = "result-only" if pa == pb else f"params({len(pa.split(','))} vs {len(pb.split(','))})"
        out.append((m.group(1), kind, f"{oa}:{ra}", f"{ob}:{rb}"))
        i += 3
    else:
        i += 1
from collections import Counter
print(Counter(k for _, k, _, _ in out))
for r in out:
    print(*r, sep="\t")
