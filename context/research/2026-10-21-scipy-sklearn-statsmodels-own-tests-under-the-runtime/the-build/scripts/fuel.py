"""Each upstream suite check's fuel, passes and outcome from judge records; optionally merged
into measured.json.

    uv run python fuel.py [--merge] record.json ...
"""

import json
import sys
from pathlib import Path

SP = Path(__file__).parent
merge = "--merge" in sys.argv
files = [a for a in sys.argv[1:] if a != "--merge"]
measured = json.loads((SP / "measured.json").read_text()) if (SP / "measured.json").exists() else {}
for f in files:
    rec = json.loads(Path(f).read_text())
    results = rec.get("results") or rec.get("checks") or {}
    items = results.items() if isinstance(results, dict) else ((r.get("nodeid"), r) for r in results)
    for node, r in items:
        if "test_upstream_suite[" not in str(node):
            continue
        group = node.split("[", 1)[1].rstrip("]")
        m = r.get("metrics", {})
        fuel = m.get("fuel")
        print(f"{group}\t{r.get('status', r.get('outcome'))}\t{fuel / 1e9 if fuel else None:.1f} G\tpasses {m.get('passes')}" if fuel else f"{group}\t{r.get('status', r.get('outcome'))}\tno fuel")
        if merge and fuel:
            measured[group] = int(fuel)
if merge:
    (SP / "measured.json").write_text(json.dumps(measured, indent=1, sort_keys=True))
