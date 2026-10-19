# Records: gh run download 39255794160 -p 'record-*' -D <records dir> (the a7 tag run; 39265738300 for
# spec 065's dry run). Data only: parsed as JSON, never run. Spec 085's research, 2026-10-19.
# Read the a7 tag run's shard records (data only) against accepted.json at the tag commit.
import json, sys, subprocess
from pathlib import Path
d = Path(sys.argv[1]); repo = sys.argv[2]; commit = sys.argv[3]
acc = json.loads(subprocess.run(["git","-C",repo,"show",f"{commit}:context/progress/accepted.json"],capture_output=True,text=True).stdout)
blocked = []; miss = []; extra = []
for f in sorted(d.glob("record-*/latest.json")):
    r = json.loads(f.read_text()); m = r["meta"]; key = f.parent.name.removeprefix("record-")
    s = r.get("suite", {}); u = m.get("units", {})
    ran = sum(1 for c in r["checks"].values() if c["status"] != "deselected")
    print(f"{key:28} platform={m['platform']:16} suite={s} units.count={u.get('count')} goal-ran={ran} statuses={dict(sorted(__import__('collections').Counter(c['status'] for c in r['checks'].values()).items()))}")
    for n, c in r["checks"].items():
        if c["status"] == "blocked":
            blocked.append((key, n, c.get("need")))
        if c["status"] == "pass":
            a = acc["checks"].get(n, {}).get("metrics", {}).get("darwin-arm64", {})
            want = set(a) - {"wasmtime"}; have = set(c.get("metrics", {}))
            if want - have: miss.append((key, n, sorted(want-have)))
            if have - want: extra.append((key, n, sorted(have-want)))
print("\nblocked:"); [print(" ", *b) for b in blocked]
print("\npassing checks missing an accepted darwin-arm64 metric name:", len(miss)); [print(" ", *x) for x in miss[:30]]
print("\npassing checks with metric names accepted.json lacks:", len(extra)); [print(" ", *x) for x in extra[:15]]
