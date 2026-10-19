"""Compare per-check fuel between two run records: uv run python compare.py A.json B.json"""
import json, sys
def fuel(p):
    c = json.load(open(p))["checks"]
    out = {}
    for n, v in c.items():
        m = v.get("metrics") or {}
        m = m.get(next(iter(m))) if m and isinstance(next(iter(m.values())), dict) else m
        if m and "fuel" in m:
            out[n] = (m["fuel"], v.get("status"))
    return out
a, b = fuel(sys.argv[1]), fuel(sys.argv[2])
same = diff = 0
for n in sorted(set(a) | set(b)):
    fa, fb = a.get(n, (None,))[0], b.get(n, (None,))[0]
    if fa is None or fb is None:
        print(f"ONLY-ONE {n} {fa} {fb}")
    elif fa != fb:
        diff += 1
        print(f"DIFF {fb - fa:+,} ({(fb - fa) / fa:+.6%}) {n} {fa:,} -> {fb:,}")
    else:
        same += 1
print(f"same {same} differ {diff} rows {len(set(a) | set(b))}")
