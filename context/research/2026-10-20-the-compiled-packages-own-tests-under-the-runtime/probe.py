import sys
from pathlib import Path
W = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(W / "tests"))
from harness import guest, paths
d = paths.artifact_dir(); m = paths.parse_manifest((d / "MANIFEST").read_text())
import tempfile; (W / "build/survey/out").mkdir(parents=True, exist_ok=True); out = Path(tempfile.mkdtemp(prefix="probe-", dir=W / "build/survey/out"))
for i, code in enumerate(sys.argv[1:]):
    r = guest.run(d / "python-snapshot.wasm", ["-c", code], workdir=out, python_version=m.python,
                  stdlib=d / "python-stdlib.zip", env={"TMPDIR": "/tmp", "HOME": "/tmp"},
                  fuel=50_000_000_000, mpl_data=True)
    print(i, r.exit_code, r.trapped, r.trap_cause, r.text.strip()[-200:], r.stderr.decode(errors="replace").strip()[-300:])
