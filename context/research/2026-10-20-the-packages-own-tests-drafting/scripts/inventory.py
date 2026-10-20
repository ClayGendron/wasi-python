import os, re, sys
from collections import Counter
root = sys.argv[1]
STD = set(sys.stdlib_module_names)
pat_test = re.compile(r"(^test_.*\.py$|.*_test\.py$|^tests?\.py$|^tests_.*\.py$)")
for pkg in sorted(os.listdir(root)):
    base = os.path.join(root, pkg)
    files = []
    for dp, dn, fn in os.walk(base):
        for f in fn:
            rel = os.path.relpath(os.path.join(dp, f), base)
            if f.endswith(".py") and (pat_test.match(f) or "/tests/" in "/" + rel or "/test/" in "/" + rel or "Tests/" in rel) and not rel.startswith(("doc", "docs", "examples", "benchmarks", "tools", "galleries")):
                files.append(rel)
    tf = [f for f in files if pat_test.match(os.path.basename(f))]
    nt = 0; feats = Counter(); imps = Counter(); skips = Counter()
    for f in files:
        try: t = open(os.path.join(base, f), encoding="utf-8", errors="replace").read()
        except Exception: continue
        nt += len(re.findall(r"^\s*(?:async\s+)?def test", t, re.M))
        for k, r in [("subprocess", r"\bsubprocess\b|\bPopen\b"), ("threading", r"\bthreading\b|\bThread\("), ("multiprocessing", r"\bmultiprocessing\b|ProcessPool"), ("socket", r"\bsocket\b"), ("signal", r"\bsignal\."), ("mmap", r"\bmmap\b"), ("getsource", r"getsource|getsourcelines|inspect\.getfile"), ("network", r"urlopen|requests\.|http://|https://"), ("hypothesis", r"\bhypothesis\b"), ("os.fork", r"os\.fork"), ("sys.executable", r"sys\.executable")]:
            if re.search(r, t): feats[k] += 1
        for m in re.finditer(r"^\s*(?:import|from)\s+([A-Za-z_][\w]*)", t, re.M):
            n = m.group(1)
            if n not in STD: imps[n] += 1
        for m in re.finditer(r"importorskip\(\s*['\"]([\w.]+)", t): skips[m.group(1)] += 1
    conf = [f for f in files if os.path.basename(f) == "conftest.py"]
    print(f"== {pkg}: {len(tf)} test files, {nt} test defs, conftest {len(conf)}")
    print("   features:", dict(feats))
    print("   imports:", ", ".join(f"{k}:{v}" for k, v in imps.most_common(14)))
    if skips: print("   importorskip:", dict(skips))
