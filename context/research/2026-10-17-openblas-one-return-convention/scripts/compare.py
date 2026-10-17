"""Compare the probe's wasm output with its native output, key by key.

Integer results (info, ipiv, sdim, exit codes, the residual and callback flags) must be equal.
A floating vector (all keys sharing a prefix, like dgesdd.s[*]) passes when
max |wasm - native| <= TOL * max |native| over the vector.
usage: uv run python -I compare.py <wasm.txt> <native.txt> [TOL]
"""
import collections
import re
import sys

TOL = float(sys.argv[3]) if len(sys.argv) > 3 else 1e-10


def load(p):
    d = {}
    for line in open(p):
        k, v = line.split(None, 1)
        d[k] = v.strip()
    return d


w, n = load(sys.argv[1]), load(sys.argv[2])
ok = True
if set(w) != set(n):
    print("key sets differ:", sorted(set(w) ^ set(n))[:10])
    ok = False
groups = collections.defaultdict(list)
for k in n:
    groups[re.sub(r"\[.*\]$", "", k)].append(k)
for g, keys in groups.items():
    ints = all(re.fullmatch(r"-?\d+", n[k]) for k in keys) and (len(keys) == 1 or "ipiv" in g)
    if ints:
        same = all(w.get(k) == n[k] for k in keys)
        print(f"{g:22s} {'equal' if same else 'DIFFERENT'} ({len(keys)} integer{'s' if len(keys) > 1 else ''})")
        ok &= same
        continue
    nv = [float(n[k]) for k in keys]
    wv = [float(w[k]) for k in keys]
    scale = max(abs(x) for x in nv) or 1.0
    diff = max(abs(a - b) for a, b in zip(wv, nv))
    rel = diff / scale
    passed = rel <= TOL
    ok &= passed
    print(f"{g:22s} {'pass' if passed else 'FAIL'}  n={len(keys):3d}  max|d|/max|x| = {rel:.2e}")
print(f"ALL {'PASS' if ok else 'FAIL'} (tolerance {TOL:g} relative)")
sys.exit(0 if ok else 1)
