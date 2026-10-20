import os, re, sys
root, pkg = sys.argv[1], sys.argv[2]
have = set(open(sys.argv[3]).read().split()) | set(sys.stdlib_module_names) | {"pytest","_pytest","pluggy","iniconfig","packaging","pygments","hypothesis","sortedcontainers","freezegun","pretend","numpy","pandas","matplotlib","PIL","kiwisolver","contourpy","lxml","regex","mpl_toolkits","tests","examples","test","Tests","conftest"}
base = os.path.join(root, pkg)
pat = re.compile(r"^(?:import|from)\s+([A-Za-z_]\w*)", re.M)
for dp, dn, fn in sorted(os.walk(base)):
    for f in sorted(fn):
        if not (f.endswith(".py") and (f.startswith(("test_", "tests_")) or f.endswith("_test.py") or f in ("tests.py",))): continue
        p = os.path.join(dp, f); t = open(p, encoding="utf-8", errors="replace").read()
        top = "\n".join(l for l in t.splitlines() if l and not l[0].isspace())
        miss = sorted({m for m in pat.findall(top) if m not in have and not m.startswith("_") and m != pkg.split("-")[0]})
        flags = [k for k, r in [("proc", r"subprocess|multiprocessing|Popen|ProcessPool"), ("thr", r"threading|Thread\("), ("sock", r"\bsocket\b")] if re.search(r, t)]
        if miss or flags: print(os.path.relpath(p, base), "missing:", miss, "uses:", flags)
