"""Sort every failed or errored test, and every module that did not run, into a class.

uv run python classify.py <pass dir with failures.tsv and module-outcomes.tsv> <out tsv>

The classes are the memo's (section 4). A failure no class takes is printed as UNCLASSIFIED.
Order matters: the first class whose module and reason patterns fit takes the test.
"""

import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# (class, kind, module regex, reason regex)
CLASSES = [
    ("c-stack-exhausted", "defect", r".", r"call stack exhausted"),
    ("no-test-modules", "build choice", r".", r"_testcapi|_testinternalcapi|_testlimitedcapi|get_stack_pointer"),
    ("no-test-modules", "build choice", r"^test_monitoring$", r"TestCApiEventGeneration"),
    ("ctypes-stand-in", "product stand-in", r".", r"ctypes is unavailable|module 'ctypes' has no attribute|cannot import name .* from 'ctypes'"),
    ("ctypes-stand-in", "product stand-in", r"^test_ctypes$", r"errors while loading tests"),
    ("mmap-stand-in", "product stand-in", r"^test_mmap$", r"."),
    ("no-executable-file", "product contract", r".", r"No such file or directory: '/usr/local/bin/python.wasm'"),
    ("not-in-zip", "product choice", r".", r"Standard library module '(ensurepip|venv)' was not found"),
    ("read-only-eperm", "sandbox", r".", r"\[Errno 63\] Operation not permitted: '/usr/local/lib/python315.zip/"),
    ("read-only-eperm", "sandbox", r"^test_bdb$", r"subtest failure|PermissionError"),
    ("bytecode-only-zip", "product choice", r".", r"Not a directory: '/usr/local/lib/python315.zip|could not get source code|c_resources"),
    ("bytecode-only-zip", "product choice", r"^test_ast$", r"errors while loading tests"),
    ("bytecode-only-zip", "product choice", r"^(test_contextlib|test_contextlib_async|test_linecache|test_module|test_unittest|test_pdb|test_pydoc\.test_pydoc)$", r"."),
    ("bytecode-only-zip", "product choice", r"^test_inspect\.test_inspect$", r"Items in the first set|lineno"),
    ("bytecode-only-zip", "product choice", r"^test_sys$", r"_path_normpath"),
    ("stepped-clock", "judge environment", r"^(test_os\.test_os|test_time|test_logging)$", r"within 0\.05 delta|0\.450 <= dt|False is not true|No rotated files"),
    ("sqlite-lock", "documented (README)", r"^(test_sqlite3|test_dbm_sqlite3)$", r"database is locked|error not raised"),
    # the verbose rerun names these subtests' error: "ctypes is unavailable" (runs-verbose)
    ("ctypes-stand-in", "product stand-in", r"^test_io\.", r"subtest failure"),
    ("wasi-path-errno", "sandbox", r".", r"\[Errno 28\] Invalid argument: .*/'|\[Errno 22\] File too large"),
]


def classify(module: str, reason: str) -> tuple[str, str]:
    for name, kind, mod_re, why_re in CLASSES:
        if re.search(mod_re, module) and re.search(why_re, reason):
            return name, kind
    return "UNCLASSIFIED", "?"


def main() -> None:
    d = Path(sys.argv[1])
    out = []
    per = defaultdict(Counter)
    mods = defaultdict(set)
    kinds = {}
    for r in csv.DictReader(open(d / "failures.tsv"), delimiter="\t"):
        c, k = classify(r["module"], r["reason"])
        per[c][r["outcome"]] += 1
        mods[c].add(r["module"])
        kinds[c] = k
        out.append([c, r["module"], r["outcome"], r["test"], r["reason"][:200]])
    for r in csv.DictReader(open(d / "module-outcomes.tsv"), delimiter="\t"):
        if r["status"] not in ("module-error", "trap"):
            continue
        stderr_path = Path("/Users/claygendron/Git/Repos/wasi_python/build/cpython-suite-research/runs") / f"{r['module']}.err"
        why = r["trap"] + " " + (stderr_path.read_text(errors="replace")[-3000:] if stderr_path.exists() else "")
        c, k = classify(r["module"], why)
        per[c][r["status"]] += 1
        mods[c].add(r["module"])
        kinds[c] = k
        out.append([c, r["module"], r["status"], "(whole module)", " ".join(why.split())[-200:]])
    Path(sys.argv[2]).write_text(
        "\n".join("\t".join(x) for x in [["class", "module", "outcome", "test", "reason"], *sorted(out)]) + "\n"
    )
    for c in sorted(per, key=lambda c: -sum(per[c].values())):
        print(f"{c}\t{kinds[c]}\t{dict(per[c])}\t{len(mods[c])} modules: {', '.join(sorted(mods[c]))}")


if __name__ == "__main__":
    main()
