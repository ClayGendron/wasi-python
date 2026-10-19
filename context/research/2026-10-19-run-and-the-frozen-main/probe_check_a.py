"""Spec 073: check A's logic, run today, per binary, through wasi_python.run: the gap's program
and a zip left open beside a def, in each of run's modes (a directory target too); its findings as scan.report gives
them.

    WASI_PYTHON_ARTIFACTS=<set> PYTHONPATH=tests uv run python <this file>
"""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

import wasi_python
from harness import scan
from wasi_python import Grant

UNCLOSED = "f = open('/out.txt', 'w')\nf.write('x' * 100)\ndef g():\n    pass\n"
ZIPPED = (
    "import zipfile\n"
    "z = zipfile.ZipFile('/out.zip', 'w')\n"
    "z.writestr('a.txt', 'x' * 100)\n"
    "def g():\n    pass\n"
)
BASE = Path("build/073").resolve()


def one(mode: str, program: str, snapshot: bool) -> Path:
    root = Path(tempfile.mkdtemp(prefix="probe-073a-", dir=BASE))
    kw: dict = {}
    if mode == "-c":
        argv = ["-c", program]
    elif mode == "stdin":
        argv, kw = [], {"stdin": program.encode()}
    elif mode == "script":
        (root / "prog.py").write_text(program)
        argv = ["/prog.py"]
    elif mode == "directory":
        (root / "app").mkdir()
        (root / "app" / "__main__.py").write_text(program)
        argv = ["/app"]
    else:
        lib = Path(tempfile.mkdtemp(prefix="probe-073a-lib-", dir=BASE))
        (lib / "prog.py").write_text(program)
        argv, kw = ["-m", "prog"], {"grants": [Grant(lib, "/code")], "import_path": ["/code"]}
    done = wasi_python.run(argv, root=root, snapshot=snapshot, **kw)
    assert done.exit_code == 0, done
    return root


for snapshot in (False, True):
    findings = []
    for mode in ("-c", "stdin", "script", "directory", "-m"):
        out = one(mode, UNCLOSED, snapshot) / "out.txt"
        kept = out.stat().st_size if out.exists() else 0
        if kept != 100:
            findings.append(f"{mode}: a file left open kept {kept} of 100 bytes")
        z = one(mode, ZIPPED, snapshot) / "out.zip"
        try:
            with zipfile.ZipFile(z) as f:
                ok = f.read("a.txt") == b"x" * 100
        except (OSError, zipfile.BadZipFile):
            ok = False
        if not ok:
            findings.append(f"{mode}: a zip left open is unreadable")
    which = "snapshot" if snapshot else "plain"
    print(which, scan.report(findings, "unclosed file"))
    for f in findings:
        print("   ", f)
