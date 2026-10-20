"""Spec 086: a branch dry run's shard records (macOS first, then the others) against the accepted
record's darwin-arm64 values: fuel and bytes per row, per kind, and the upstream groups.
usage: ci_vs_accepted.py ACCEPTED.json RECORD_DIR..."""
import json, statistics, sys
acc = json.load(open(sys.argv[1]))["checks"]
rows, src = {}, {}
for d in sys.argv[2:]:
    for node, rec in json.load(open(f"{d}/latest.json"))["checks"].items():
        if rec.get("status") != "pass" or node in rows:
            continue
        rows[node] = rec.get("metrics") or {}
        src[node] = d.rsplit("/", 1)[-1]
def old(node, kind):
    m = (acc.get(node) or {}).get("metrics") or {}
    m = m.get("darwin-arm64", m)
    v = m.get(kind)
    return v.get("value") if isinstance(v, dict) else v
for kind in ("fuel", "bytes"):
    t = [(n, old(n, kind), m[kind]) for n, m in rows.items() if isinstance(m.get(kind), (int, float)) and old(n, kind)]
    pct = [(b - a) / a * 100 for _, a, b in t]
    sa, sb = sum(a for _, a, _ in t), sum(b for _, _, b in t)
    print(f"{kind}: {len(t)} rows, {sum(p > 0.01 for p in pct)} up and {sum(p < -0.01 for p in pct)} down by >0.01%, "
          f"median {statistics.median(pct):+.3f}%, min {min(pct):+.3f}%, max {max(pct):+.3f}%, sum {sa:,} -> {sb:,} ({(sb - sa) / sa * 100:+.3f}%)")
    for p, (n, a, b) in sorted(zip(pct, t), key=lambda x: -abs(x[0]))[:15]:
        print(f"  {p:+.3f}%  {a:,} -> {b:,}  {n}  [{src[n]}]")
print("upstream groups:")
for n, m in sorted(rows.items()):
    if "upstream_suite[" in n:
        a = old(n, "fuel")
        print(f"  {n.split('[')[1][:-1]:22} {a:,} -> {m['fuel']:,} ({(m['fuel'] - a) / a * 100:+.3f}%), passes {old(n, 'passes')} -> {m.get('passes')}  [{src[n]}]")
