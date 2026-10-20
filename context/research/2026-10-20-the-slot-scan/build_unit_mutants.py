"""Spec 096, check 4's daggers: each rule's mutant makes its unit row fail. Copies tests/ into a
scratch folder, applies one textual mutation to harness/callbacks.py, runs the slot rows."""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

repo = Path(sys.argv[1])
MUTANTS = [
    (
        "C string allows a space",
        'STRING = re.compile(rb"[\\x20-\\x7e]{1,256}\\0")',
        'STRING = re.compile(rb"[\\x21-\\x7e]{1,256}\\0")',
    ),
    ("metatype by tp_basicsize", "and (w[4] >= TYPE_SIZE or w[32] in meta)", "and (w[32] in meta)"),
    (
        "a function field must be a table index",
        "if w[off // 4] and w[off // 4] not in mod.elements\n",
        "if False\n",
    ),
    ("exactly one `type`", "if len(selfref) != 1:", "if False:"),
    ("unreadable tp_name is a finding", "if w[3] and not names[addr]:", "if False:"),
    ("a record typed by a nameless type is a finding", "if typ in nameless:", "if False:"),
    (
        "unreferenced candidates counted",
        'cov["unreferenced type candidates"] += 1\n            continue',
        "pass",
    ),
    (
        "a spec must be referenced",
        "        if addr not in refs:\n            continue\n        name_ptr",
        "        name_ptr",
    ),
    (
        "a broken run is a finding",
        'report.findings.append(f"spec {name}: slot entry {len(entries)} unreadable {entry}")',
        "pass",
    ),
    ("old ids read", '4: ("mp_length", UNARY),', ""),
    ("NULL function slot readable", "entry[1] == 0 or ", ""),
    (
        "named records",
        "        for n in sorted(names - report.seen.get(kind, set()))\n",
        "        for n in sorted(set())\n",
    ),
    (
        "bounds",
        "for k, cap in maximums.items() if c[k] > cap]",
        "for k, cap in maximums.items() if False]",
    ),
]
src = (repo / "tests" / "harness" / "callbacks.py").read_text()
for label, old, new in MUTANTS:
    if src.count(old) != 1:
        print(f"{label}: mutation text found {src.count(old)} times")
        continue
    with tempfile.TemporaryDirectory() as d:
        t = Path(d) / "tests"
        shutil.copytree(repo / "tests", t, ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy(repo / "pyproject.toml", Path(d) / "pyproject.toml")
        (t / "harness" / "callbacks.py").write_text(src.replace(old, new))
        r = subprocess.run(
            [
                "uv",
                "run",
                "--project",
                str(repo),
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                str(t / "unit" / "test_callbacks.py"),
                "-k",
                "slots",
            ],
            capture_output=True,
            text=True,
            cwd=d,
        )
        failed = sorted(
            {
                l.split("::")[1].split(" ")[0]
                for l in r.stdout.splitlines()
                if l.startswith("FAILED")
            }
        )
        print(f"{label}: {len(failed)} failed: {', '.join(failed) or 'NONE'}")
