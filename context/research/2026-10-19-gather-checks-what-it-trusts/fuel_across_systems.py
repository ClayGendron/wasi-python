# Records: gh run download 39255794160 -p 'record-*' -D <records dir> (the a7 tag run; 39265738300 for
# spec 065's dry run). Data only: parsed as JSON, never run. Spec 085's research, 2026-10-19.
# Each metric of each passing check, per record, against accepted.json's darwin-arm64 value.
import json, sys, subprocess
from collections import defaultdict
from pathlib import Path
d = Path(sys.argv[1]); repo = sys.argv[2]; commit = sys.argv[3]
acc = json.loads(subprocess.run(["git","-C",repo,"show",f"{commit}:context/progress/accepted.json"],capture_output=True,text=True).stdout)
stats = defaultdict(lambda: [0,0,0,0])  # same, above, below, n
worst = defaultdict(float)
nmetric = defaultdict(int)
for f in sorted(d.glob("record-*/latest.json")):
    r = json.loads(f.read_text()); plat = r["meta"]["platform"].split("-")[0]
    for n, c in r["checks"].items():
        if c["status"] != "pass": continue
        a = acc["checks"].get(n, {}).get("metrics", {}).get("darwin-arm64", {})
        for k, v in c.get("metrics", {}).items():
            nmetric[(plat,k)] += 1
            if k not in a: continue
            s = stats[(plat,k)]; s[3] += 1
            if v == a[k]: s[0] += 1
            elif v > a[k]: s[1] += 1; worst[(plat,k)] = max(worst[(plat,k)], (v-a[k])/max(a[k],1))
            else: s[2] += 1
for key in sorted(stats): print(key, "same/above/below/n =", stats[key], "worst rel above = %.3g" % worst[key])
print(dict(nmetric))
