"""Spec 073: the gap's program through the product, wasi_python.run, in -c and script modes, on
both binaries (fuel unrecorded: run answers entropy and clocks from the host).

    WASI_PYTHON_ARTIFACTS=<set> uv run python <this file>
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import wasi_python

GAP = "f = open('/out.txt', 'w')\nf.write('x' * 100)\ndef g():\n    pass\n"

for snapshot in (False, True):
    for mode in ("-c", "script"):
        root = Path(tempfile.mkdtemp(prefix="probe-073r-", dir=Path("build/073").resolve()))
        if mode == "script":
            (root / "prog.py").write_text(GAP)
            argv = ["/prog.py"]
        else:
            argv = ["-c", GAP]
        done = wasi_python.run(argv, root=root, snapshot=snapshot)
        out = root / "out.txt"
        kept = out.stat().st_size if out.exists() else "-"
        which = "snapshot" if snapshot else "plain"
        print(f"{mode:7} {which:9} exit {done.exit_code} kept {kept}")

# stdin mode (argv empty, the program on stdin), and the -m mode through an import path.
from wasi_python import Grant  # noqa: E402

lib = Path(tempfile.mkdtemp(prefix="probe-073r-lib-", dir=Path("build/073").resolve()))
(lib / "prog.py").write_text(GAP)
for snapshot in (False, True):
    which = "snapshot" if snapshot else "plain"
    root = Path(tempfile.mkdtemp(prefix="probe-073r-", dir=Path("build/073").resolve()))
    done = wasi_python.run([], root=root, snapshot=snapshot, stdin=GAP.encode())
    out = root / "out.txt"
    print(f"stdin   {which:9} exit {done.exit_code} kept {out.stat().st_size if out.exists() else '-'}")
    root = Path(tempfile.mkdtemp(prefix="probe-073r-", dir=Path("build/073").resolve()))
    done = wasi_python.run(
        ["-m", "prog"], root=root, snapshot=snapshot, grants=[Grant(lib, "/code")],
        import_path=["/code"],
    )
    out = root / "out.txt"
    print(f"-m      {which:9} exit {done.exit_code} kept {out.stat().st_size if out.exists() else '-'}")
    done = wasi_python.run(["-c", "import sys; print(sys.executable)"], snapshot=snapshot)
    print(f"sys.executable {which}: {done.stdout.decode().strip()}")
