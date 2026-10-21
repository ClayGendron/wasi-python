"""Which statsmodels test files load a dataset that spec 045 leaves out of the zip. Reads text only.

Usage: sm_datasets.py <statsmodels package folder>
"""

import os
import re
import sys

root = sys.argv[1]
LEFT_OUT = ["ccard", "committee", "copper", "cpunish", "fair", "scotland", "spector", "star98",
            "fertility", "china_smoking", "cancer", "heart", "interest_inflation"]
pats = {d: re.compile(rf"\b{d}\b\.load|datasets\.{d}\b|import[^\n]*\b{d}\b|load_{d}\b") for d in LEFT_OUT}
net = re.compile(r"get_rdataset|webuse\(")
files = {d: [] for d in LEFT_OUT}
netfiles = []
any_files = set()
for dp, dn, fn in os.walk(root):
    if "tests" not in dp.split(os.sep):
        continue
    for f in fn:
        if not f.endswith(".py"):
            continue
        p = os.path.join(dp, f)
        s = open(p, encoding="utf-8", errors="replace").read()
        r = os.path.relpath(p, root)
        for d, pat in pats.items():
            if pat.search(s):
                files[d].append(r)
                any_files.add(r)
        if net.search(s):
            netfiles.append(r)
for d in LEFT_OUT:
    print(d, len(files[d]), " ".join(sorted(files[d])[:6]))
print("files touching any left-out dataset:", len(any_files))
print("files naming get_rdataset or webuse:", len(netfiles), " ".join(sorted(netfiles)))
