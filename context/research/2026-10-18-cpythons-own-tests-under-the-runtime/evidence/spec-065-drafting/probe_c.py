"""Run one -c program in the frozen set's snapshot and plain binaries through the judge's driver."""
import sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tests"))
from harness import guest  # noqa: E402
SET = REPO / "build/sets/s-4eb5418a2b1bb553"
code = sys.argv[1]
for name in ("python-snapshot.wasm", "python.wasm"):
    import tempfile; w = Path(tempfile.mkdtemp(dir=REPO / "build/reviews-evidence/065-spec"))
    w.mkdir(parents=True, exist_ok=True)
    r = guest.run(SET / name, ["-c", code], workdir=w, python_version="3.15.0",
                  stdlib=SET / "python-stdlib.zip", env={"TMPDIR": "/tmp", "HOME": "/tmp"},
                  fuel=2 * 10**10, mpl_data=True)
    print(name, r.exit_code, r.stdout.decode().strip(), r.stderr.decode().strip()[-300:])
