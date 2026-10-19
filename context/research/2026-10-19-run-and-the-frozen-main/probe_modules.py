"""Spec 073: the hole a fresh __main__ would leave. For every module in sys.modules at a snapshot
program's start, a program stores an open file as that module's attribute, writes 100 bytes and
exits without closing it (no function in __main__). Bytes kept, per binary; plus the same with a
fresh, unfrozen __main__ simulated (as probe.py's fresh_main), which cannot help this case.

    WASI_PYTHON_ARTIFACTS=<set> PYTHONPATH=tests uv run python <this file>
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from harness import guest as driver
from harness import paths


def main() -> None:
    d = paths.artifact_dir()
    m = paths.parse_manifest((d / "MANIFEST").read_text())
    work = Path(tempfile.mkdtemp(prefix="probe-073mod-", dir=Path("build/073").resolve()))
    kw = dict(workdir=work, python_version=m.python, stdlib=d / "python-stdlib.zip")
    snap, plain = d / "python-snapshot.wasm", d / "python.wasm"
    r = driver.run(snap, ["-c", "import sys; print(' '.join(sorted(sys.modules)))"], **kw)
    names = r.text.split()
    print(f"{len(names)} modules at a snapshot program's start")
    lost: list[str] = []
    for name in names:
        prog = (
            f"import {name} as _m\n"
            "_m._wp073 = open('/out.txt', 'w')\n"
            "_m._wp073.write('x' * 100)\n"
        )
        row = []
        for wasm in (plain, snap):
            res = driver.run(wasm, ["-c", prog], **kw)
            out = res.root / "out.txt"
            kept = out.stat().st_size if out.exists() else -1
            row.append(kept if res.exit_code == 0 else f"exit {res.exit_code}")
        print(f"{name:32} plain {row[0]!s:>7}  snapshot {row[1]!s:>7}")
        if row[0] == 100 and row[1] != 100:
            lost.append(name)
    print(f"lost on the snapshot only: {len(lost)}: {' '.join(lost)}")


if __name__ == "__main__":
    main()
