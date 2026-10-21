"""scipy's two time-limited mpmath tests that pass the bound at the judge's clock: each its own
split group of test_mpmath.py, with a 100 us clock step, before the split's remainder."""

import json
from pathlib import Path

SP = Path(__file__).parent
groups = json.loads((SP / "groups.json").read_text())
splits = json.loads((SP / "splits.json").read_text())
F = "scipy/special/tests/test_mpmath.py"
s = next(x for x in splits["scipy"] if x["file"] == F)
if "scipy-special-mpmath-betainc" not in s["groups"]:
    last = s["groups"][-1]
    s["groups"][-1:-1] = ["scipy-special-mpmath-betainc", "scipy-special-mpmath-betaincc"]
    s["keywords"] += ["test_betainc and not test_betaincc", "test_betaincc"]
    gs = groups["scipy"]
    i = next(k for k, g in enumerate(gs) if g["name"] == last)
    gs[i:i] = [
        {"name": "scipy-special-mpmath-betainc", "paths": [F], "est": 63.3, "cap": 200_000_000_000, "clock": 100_000},
        {"name": "scipy-special-mpmath-betaincc", "paths": [F], "est": 26.8, "cap": 200_000_000_000, "clock": 100_000},
    ]
    gs[i + 2]["cap"] = 20 * 10**12
(SP / "groups.json").write_text(json.dumps(groups, indent=1))
(SP / "splits.json").write_text(json.dumps(splits, indent=1))
print(s)
