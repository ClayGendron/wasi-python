"""Fuel and probe runs on one artifact set, through the judge's own guest driver (fuel exact).

    measure.py <repo with tests/harness> <artifacts dir> <out dir> [--probes]

Writes <out dir>/fuel.txt (one line per program: binary, program, exit, fuel) and, with --probes,
<out dir>/<probe>.<binary>.out with each probe's stdout and stderr.
"""

import shutil
import sys
import tempfile
from pathlib import Path

repo, art, out = (Path(a) for a in sys.argv[1:4])
probes = "--probes" in sys.argv
sys.path.insert(0, str(repo / "tests"))
from harness import guest  # noqa: E402

HERE = Path(__file__).resolve().parent
PY = "3.15.0"
BIN = {"snapshot": art / "python-snapshot.wasm", "plain": art / "python.wasm"}
ZIP = art / "python-stdlib.zip"
out.mkdir(parents=True, exist_ok=True)
work = Path(tempfile.mkdtemp(prefix="measure-", dir=out))

PROGRAMS = [
    ("snapshot", "pass"),
    ("plain", "pass"),
    ("snapshot", "import bz2"),
    ("snapshot", "import lzma"),
    ("snapshot", "import sqlite3"),
    ("snapshot", "import sqlite3; sqlite3.connect(':memory:').execute('select 1').fetchone()"),
    ("plain", "import pandas"),
]
lines = []
for which, prog in PROGRAMS:
    r = guest.run(BIN[which], ["-c", prog], workdir=work, python_version=PY, stdlib=ZIP)
    tail = r.stderr.decode(errors="replace").strip().splitlines()[-1:] or [""]
    lines.append(f"{which}\t{prog}\texit={r.exit_code}\ttrap={r.trapped}\tfuel={r.fuel}\t{tail[0][:100]}")
    print(lines[-1], flush=True)
(out / "fuel.txt").write_text("\n".join(lines) + "\n")

if probes:
    for probe in ("probe_compress.py", "probe_sqlite.py"):
        src = (HERE / probe).read_text()
        for which in ("snapshot", "plain"):
            r = guest.run(BIN[which], [f"/probe/{probe}"], workdir=work, python_version=PY,
                          stdlib=ZIP, files={f"/probe/{probe}": src}, env={"WORK": "/work"})
            text = r.stdout.decode(errors="replace")
            text += f"--- exit={r.exit_code} trap={r.trapped} fuel={r.fuel}\n"
            text += r.stderr.decode(errors="replace")
            (out / f"{probe[:-3]}.{which}.out").write_text(text)
            print(probe, which, r.exit_code, r.trapped, r.fuel, flush=True)
shutil.rmtree(work)
