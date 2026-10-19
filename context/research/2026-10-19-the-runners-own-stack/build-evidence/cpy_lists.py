import json, sys
from pathlib import Path
sys.path.insert(0, "tests")
from harness import regrtest, upstream, scan
configs = upstream.load_all()
s = regrtest.Session(Path("build/harness/cpyrun"), configs)
group = sys.argv[1]
o = s.group("python", group).outcome
for kid in sys.argv[2:]:
    k = next(k for k in configs["python"].expected if k.group == group and k.id == kid)
    upstream.list_path(k).write_text("\n".join(sorted(set(o.members[kid]))) + "\n")
for k in configs["python"].expected:
    if k.group == group:
        f = upstream.class_findings(o.members.get(k.id, []), upstream.read_list(upstream.list_path(k)))
        print(k.id, f"{len(f)} finding(s), digest {scan.digest(f)}" if f else "empty")
print("findings", o.findings[:3])
s.close()
