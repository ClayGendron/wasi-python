"""Run the probes natively under the clone's oracle (the line's pinned host Python 3.15.0 with the
guest's package pins), each in a fresh WORK directory.

    native.py <repo> <out dir>
"""

import subprocess
import sys
import tempfile
from pathlib import Path

repo, out = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(repo / "tests"))
from harness import jobs  # noqa: E402

HERE = Path(__file__).resolve().parent
out.mkdir(parents=True, exist_ok=True)
for probe in ("probe_compress.py", "probe_sqlite.py"):
    with tempfile.TemporaryDirectory() as work:
        env = jobs.oracle_env(0) | {"WORK": work}
        r = subprocess.run(jobs.oracle_command("-I", str(HERE / probe)), env=env, capture_output=True)
        text = r.stdout.decode() + f"--- exit={r.returncode}\n" + r.stderr.decode()
        (out / f"{probe[:-3]}.native.out").write_text(text)
        print(probe, r.returncode)
