"""Spec 083's growth list (F7): every fuel row, its accepted value (darwin-arm64), the times-only
value and the build's value, and the parts in ten thousand each moved it; rows that rise past the
tolerance (1e-4) first. The build's value must be one value over all its records.
Usage: uv run python -I growth.py <accepted.json> <times-only latest.json> <build latest.json>..."""
import json
import sys


def fuel(p):
    return {n: v["metrics"]["fuel"] for n, v in json.load(open(p))["checks"].items()
            if "fuel" in (v.get("metrics") or {})}


acc = {n: v["metrics"]["darwin-arm64"]["fuel"] for n, v in json.load(open(sys.argv[1]))["checks"].items()
       if "fuel" in v["metrics"].get("darwin-arm64", {})}
times = fuel(sys.argv[2])
builds = [fuel(p) for p in sys.argv[3:]]
rows = []
for n in sorted(set(acc) & set.intersection(*(set(b) for b in builds))):
    vals = {b[n] for b in builds}
    full = max(vals)
    t = times.get(n)
    rows.append(((full - acc[n]) / acc[n], n, acc[n], t, full, len(vals)))
grown = [r for r in rows if r[0] > 1e-4]
print(f"rows {len(rows)}; one value over {len(builds)} records: {sum(r[5] == 1 for r in rows)}; "
      f"rise past 1e-4: {len(grown)}; rise {sum(r[0] > 0 for r in rows)}; fall {sum(r[0] < 0 for r in rows)}")
print("| row | accepted | times only | full | times only, per 10^4 | full, per 10^4 |")
print("|---|---|---|---|---|---|")
for rel, n, a, t, f, k in sorted(grown, key=lambda r: -r[0]):
    ts = f"{t:,}" if t is not None else "n/a"
    tr = f"{(t - a) / a * 1e4:+.2f}" if t is not None else "n/a"
    print(f"| `{n.split('::')[-1]}` | {a:,} | {ts} | {f:,} | {tr} | {rel * 1e4:+.2f} |")
print()
print("all rows (per 10^4 against accepted: times only, full):")
for rel, n, a, t, f, k in sorted(rows, key=lambda r: -abs(r[0])):
    tr = f"{(t - a) / a * 1e4:+8.2f}" if t is not None else "     n/a"
    print(f"{tr} {rel * 1e4:+8.2f}  {n}{'' if k == 1 else f'  ({k} values!)'}")
