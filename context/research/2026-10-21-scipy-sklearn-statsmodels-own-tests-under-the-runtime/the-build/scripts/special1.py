"""scipy-special-1 stopped in test_support_alternative_backends.py's hyp1f1 hypothesis case
(killed at about 10 T): split at the file where it stopped, by sdist order."""
import json
import sys
sys.argv = sys.argv[:1]
import pass3

g = pass3.groups["scipy"]
i = next(k for k, x in enumerate(g) if x["name"] == "scipy-special-1")
old = g[i]
ps = old["paths"]
v = pass3.ff["scipy-special-1"]
pg = "scipy/special/tests/test_precompute_gammainc.py"
sab = "scipy/special/tests/test_support_alternative_backends.py"
a = ps[: ps.index(pg)]
b = ps[ps.index(pg) + 1 : ps.index(sab)]
rest = ps[ps.index(sab) + 1 :]
base = {k: y for k, y in old.items() if k not in ("name", "paths", "est", "cap", "comment")}
fe = lambda fs: sum(v["files"].get(f, 0.0) for f in fs)  # noqa: E731
new = [
    {**base, "name": "scipy-special-1", "paths": a, "est": round(fe(a) + 66.6, 1), "cap": 1_000_000_000_000},
]
s = {"file": pg, "groups": ["scipy-special-precompute-gammainc-1"], "keywords": []}
new += pass3.rebuild_split("scipy", s, 0, old)
pass3.splits["scipy"].append(s)
new += [
    {**base, "name": "scipy-special-2", "paths": b, "est": round(fe(b) + 20, 1), "cap": 600_000_000_000},
    {**base, "name": "scipy-special-3", "paths": [sab], "est": round(fe([sab]) + 20, 1), "cap": 2_000_000_000_000},
    {**base, "name": "scipy-special-4", "paths": rest, "est": 300.0, "cap": 5_000_000_000_000},
]
g[i : i + 1] = new
for x in new:
    print(x["name"], x["est"], x["paths"][:2], len(x["paths"]))
(pass3.SP / "groups.json").write_text(json.dumps(pass3.groups, indent=1))
(pass3.SP / "splits.json").write_text(json.dumps(pass3.splits, indent=1))
