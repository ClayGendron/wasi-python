"""Spec 065's allowances: every failing id of the verbose reruns, plus the trap hunt's one error,
sorted into the plan's groups and spec 065's classes.

uv run --no-project python allowances.py  ->  allowances.tsv (group, class, outcome, id, reason)
and a count per (group, class, outcome).
"""
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
group_of = {}
for f in (HERE / "plan").glob("cpython-*.txt"):
    for m in f.read_text().split():
        group_of[m] = f.stem
NOT_SELECTED = set((HERE / "plan/not-selected.txt").read_text().split())

RULES = [  # (module regex, reason regex, class)
    (r".", r"ctypes is unavailable", "no-ctypes"),
    (r".", r"module 'ctypes' has no attribute 'pythonapi'", "ctypes-stand-in-surface"),
    (r"^test_mmap$", r"mmap is unavailable|cannot access local variable 'm'", "no-mmap"),
    (r"^test_mmap$", r"module 'mmap' has no attribute|object\.__new__\(\) takes exactly one", "mmap-stand-in-surface"),
    (r".", r"PermissionError: \[Errno 63\]", "read-only-eperm"),
    (r".", r"database is locked", "sqlite-lock"),
    (r"^test_dbm_sqlite3$", r"error not raised", "no-file-modes"),
    (r"^test_monitoring$", r"", "monitoring-tool-left"),
    (r".", r"_testcapi|_testinternalcapi|get_stack_pointer", "no-test-modules"),
    (r"^test_(logging|os\.test_os)$", r".", "stepped-clock"),
    (r"^test_shutil$", r"\[Errno 28\]", "trailing-slash-einval"),
    (r"^test_platform$", r"python\.wasm", "no-executable-file"),
]


def klass(module, outcome, reason, tid=""):
    if tid.endswith("test_mmap_closed_by_int_scenarios"):
        return "mmap-stand-in-surface"  # module 'mmap' has no attribute 'ACCESS_DEFAULT' (classes.tsv)
    for mod, why, k in RULES:
        if re.search(mod, module) and re.search(why, reason):
            return k
    return "stdlib-zip" if outcome == "failed" else "stdlib-zip-error"


rows = [l.split("\t") for l in (HERE / "verbose-ids.tsv").read_text().splitlines()]
rows.append(["test_doctest", "error",
             "test.test_doctest.test_doctest.TestDocTestFinder.test_empty_namespace_package",
             "PermissionError: [Errno 63] Operation not permitted: '/usr/local/lib/python315.zip/doctest_empty_pkg.pyc'"])
out, counts = [], Counter()
for module, outcome, tid, reason in rows:
    if module in NOT_SELECTED:
        continue
    g = group_of[module]
    k = klass(module, outcome, reason, tid)
    out.append("\t".join([g, k, outcome, tid, reason]))
    counts[(g, k, outcome)] += 1
(HERE / "allowances.tsv").write_text("\n".join(sorted(out)) + "\n")
for key in sorted(counts):
    print(*key, counts[key], sep="\t")
print("total", sum(counts.values()))
