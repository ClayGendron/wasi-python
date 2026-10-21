"""Read a package's unpacked sdist as text and count what its own tests ask of the platform.

Usage: survey.py <package root folder> <name> <out folder>
Reads only; imports nothing from the tree.
"""

import ast
import os
import re
import sys
from collections import Counter, defaultdict

root, name, out = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(out, exist_ok=True)

RISKS = {
    "subprocess": r"\bsubprocess\b|sys\.executable|os\.system\(|os\.popen\(",
    "multiprocessing": r"\bmultiprocessing\b|ProcessPoolExecutor|\bPool\(",
    "threads": r"\bthreading\b|ThreadPoolExecutor|concurrent\.futures|Thread\(",
    "network": r"urlopen|\brequests\b|\bpooch\b|socket\.|http://|https://|download_if_missing|webuse|get_rdataset",
    "ctypes": r"\bctypes\b",
    "mmap": r"\bmmap\b|mmap_mode",
    "importorskip": r"importorskip\(",
    "signal": r"\bsignal\.(alarm|signal|SIG)",
    "fork": r"os\.fork\(",
    "tmp_path": r"\btmp_path\b|\btmpdir\b|tempfile\.",
    "hypothesis": r"\bhypothesis\b",
    "slow_mark": r"mark\.slow\b",
    "xslow_mark": r"mark\.xslow\b",
    "thread_unsafe": r"thread_unsafe|parallel_threads",
    "timeout": r"mark\.timeout|fail_slow",
    "xfail_32bit": r"xfail_on_32bit|_32BIT|IS_32BIT|maxsize\s*[<>]",
    "network_mark": r"mark\.network|SKLEARN_SKIP_NETWORK_TESTS|skip_network",
    "matplotlib": r"\bmatplotlib\b",
}

TEST_EXT = re.compile(
    r"_test_ccallback|_test_deprecation_call|_test_deprecation_def|_test_multivariate|"
    r"ndimage\._ctest|ndimage\._cytest|_ctest\b|_cytest\b|_test_internal|_test_odeint_banded"
)

test_files = []
data_bytes = 0
data_files = 0
conftests = []
for dirpath, dirnames, filenames in os.walk(root):
    rel = os.path.relpath(dirpath, root)
    parts = rel.split(os.sep)
    in_tests = "tests" in parts or "testing" in parts
    for f in filenames:
        p = os.path.join(dirpath, f)
        r = os.path.relpath(p, root)
        if f == "conftest.py":
            conftests.append(r)
        if in_tests:
            if f.startswith("test_") and f.endswith(".py"):
                test_files.append(r)
            elif not f.endswith(".py"):
                data_files += 1
                data_bytes += os.path.getsize(p)

test_files.sort()
risk_files = defaultdict(list)
defs = Counter()
ext_files = []
imports_by_file = {}
for r in test_files:
    src = open(os.path.join(root, r), encoding="utf-8", errors="replace").read()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        defs[r] = -1
        continue
    n = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            n += 1
    defs[r] = n
    for k, pat in RISKS.items():
        hits = len(re.findall(pat, src))
        if hits:
            risk_files[k].append((r, hits))
    if TEST_EXT.search(src):
        ext_files.append((r, sorted(set(TEST_EXT.findall(src)))))
    tops = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                tops.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            tops.add(node.module.split(".")[0])
    imports_by_file[r] = tops

# top-level folders of the test files
by_sub = Counter()
defs_by_sub = Counter()
for r in test_files:
    parts = r.split(os.sep)
    key = "/".join(parts[:2]) if len(parts) > 2 else parts[0]
    by_sub[key] += 1
    defs_by_sub[key] += max(defs[r], 0)

all_imports = Counter()
for s in imports_by_file.values():
    all_imports.update(s)

with open(os.path.join(out, f"{name}-inventory.txt"), "w") as fh:
    fh.write(f"{name}: {len(test_files)} test files, {sum(max(v, 0) for v in defs.values())} test functions (def test*, before parametrization)\n")
    fh.write(f"non-.py files under tests/ or testing/: {data_files}, {data_bytes} bytes\n")
    fh.write(f"conftest.py files: {len(conftests)}\n")
    for c in sorted(conftests):
        fh.write(f"  {c}\n")
    fh.write("\nby subpackage: files, test functions\n")
    for k in sorted(by_sub):
        fh.write(f"  {k}: {by_sub[k]} files, {defs_by_sub[k]} defs\n")
    fh.write("\ntop-level imports across test files (count of files)\n")
    for k, v in all_imports.most_common():
        fh.write(f"  {k}: {v}\n")

with open(os.path.join(out, f"{name}-risks.txt"), "w") as fh:
    for k in RISKS:
        lst = risk_files.get(k, [])
        fh.write(f"== {k}: {len(lst)} files, {sum(h for _, h in lst)} hits\n")
        for r, h in lst:
            fh.write(f"  {r} {h}\n")
    fh.write(f"== compiled test extensions: {len(ext_files)} files\n")
    for r, names in ext_files:
        fh.write(f"  {r} {' '.join(names)}\n")

print(open(os.path.join(out, f"{name}-inventory.txt")).read().split("\ntop-level")[0])
for k in RISKS:
    lst = risk_files.get(k, [])
    print(f"{k}: {len(lst)} files, {sum(h for _, h in lst)} hits")
print(f"compiled test extensions: {len(ext_files)} files")
