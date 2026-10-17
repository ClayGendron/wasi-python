"""Run probe_lock.py's stages in order on one root through the product runner, wasi_python.run.

    WASI_PYTHON_ARTIFACTS=<artifacts> drive_lock.py <out file>
"""

import shutil
import sys
import tempfile
import time
from pathlib import Path

from wasi_python import run

HERE = Path(__file__).resolve().parent
out = Path(sys.argv[1])
src = (HERE / "probe_lock.py").read_text()
lines = []
for snapshot in (True, False):
    root = Path(tempfile.mkdtemp(prefix="lockroot-"))
    (root / "probe").mkdir()
    (root / "probe" / "probe_lock.py").write_text(src)
    (root / "tmpdir").mkdir()
    stages = [("die", {}), ("after", {}), ("clear", {}), ("spin", {}), ("after", {}), ("clear", {}),
              ("temp", {}), ("temp", {"SQLITE_TMPDIR": "/tmpdir"})]
    for stage, extra in stages:
        t0 = time.perf_counter()
        r = run(["/probe/probe_lock.py"], root=root, env={"WORK": "/work", "STAGE": stage, **extra},
                snapshot=snapshot, fuel=3 * 10**9 if stage == "spin" else 10**12, cache_dir=False)
        dt = time.perf_counter() - t0
        lines.append(f"== {'snapshot' if snapshot else 'plain'} {stage} {extra} exit={r.exit_code} "
                     f"trap={r.trapped} ({dt:.2f} s)")
        lines += r.stdout.decode(errors="replace").splitlines()
        err = r.stderr.decode(errors="replace").strip().splitlines()
        lines += [f"  stderr: {e}" for e in err[-2:]]
    host_view = sorted(str(p.relative_to(root)) for p in root.rglob("*") if "usr" not in p.parts)
    lines.append(f"host view of the root after: {host_view}")
    shutil.rmtree(root)
out.write_text("\n".join(lines) + "\n")
print("\n".join(lines))
