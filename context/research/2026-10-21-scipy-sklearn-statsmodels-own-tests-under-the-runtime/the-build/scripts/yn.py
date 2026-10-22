import sys
import tempfile
from pathlib import Path

W = Path("/Users/claygendron/Git/Repos/wasi_python/.claude/worktrees/agent-aab0b516adb4e5c06")
sys.path.insert(0, str(W / "tests"))
from harness import guest, paths, upstream  # noqa: E402

code = """
import scipy.special as sc, numpy as np
print('yn', sc.yn(3, 1e-105), sc.yn(3, 1e-10), sc.yv(3, 1e-105))
with sc.errstate(all='raise'):
    for f, a in ((sc.yn, (3, 1e-105)), (sc.yv, (3, 1e-105)), (sc.gamma, (1000.0,)), (sc.kv, (3, 1e-310))):
        try:
            print(f.__name__, f(*a))
        except Exception as e:
            print(f.__name__, 'raised', type(e).__name__, e)
"""
d = paths.artifact_dir()
m = paths.parse_manifest((d / "MANIFEST").read_text())
r = guest.run(
    d / "python-snapshot.wasm", ["-c", code], workdir=Path(tempfile.mkdtemp(dir=paths.guest_tmp())),
    python_version=m.python, stdlib=d / "python-stdlib.zip", env=upstream.ENV, measured=False, fuel=50 * 10**9,
)
print(r.stdout.decode(), r.stderr.decode()[-800:])
