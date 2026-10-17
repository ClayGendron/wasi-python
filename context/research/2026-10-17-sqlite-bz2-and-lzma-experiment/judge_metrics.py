"""Compare the judge's per-check metrics (fuel, bytes) between two runs' build/progress/latest.json.

    judge_metrics.py <base latest.json> <new latest.json>
"""

import json
import sys

a, b = (json.load(open(p))["checks"] for p in sys.argv[1:3])
for k in sorted(set(a) & set(b)):
    ma, mb = a[k].get("metrics") or {}, b[k].get("metrics") or {}
    for m in sorted(set(ma) & set(mb)):
        if ma[m] != mb[m]:
            pct = 100 * (mb[m] - ma[m]) / ma[m] if ma[m] else float("nan")
            print(f"{k.split('::')[-1][:70]:70} {m:6} {ma[m]:>14,} -> {mb[m]:>14,}  {pct:+.2f}%")
