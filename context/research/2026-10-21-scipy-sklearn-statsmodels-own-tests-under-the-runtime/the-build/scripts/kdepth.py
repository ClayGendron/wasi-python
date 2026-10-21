"""How long a -k expression the guest's pytest compiles: N terms joined by `or`, and the split's
form `(e) and not ((e1) or (e2) ...)`."""

import sys
import tempfile
import zipfile
from pathlib import Path

W = Path("/Users/claygendron/Git/Repos/wasi_python/.claude/worktrees/agent-aab0b516adb4e5c06")
sys.path.insert(0, str(W / "tests"))
from harness import guest, paths, upstream  # noqa: E402

kit = Path(tempfile.mkdtemp())
for _, _, name in upstream.kit_entries(upstream.KIT.read_text()):
    with zipfile.ZipFile(upstream.WHEELS / name) as z:
        z.extractall(kit)
code = """
import sys
sys.path.append('/kit')
from _pytest.mark.expression import Expression
for n in (50, 100, 200, 300, 400, 600):
    e = ' or '.join(f'test_x[a-{i}]' for i in range(n))
    try:
        Expression.compile('not (' + e + ')')
        print(n, 'ok')
    except BaseException as x:
        print(n, 'bad', type(x).__name__)
"""
d = paths.artifact_dir()
m = paths.parse_manifest((d / "MANIFEST").read_text())
r = guest.run(
    d / "python-snapshot.wasm", ["-c", code], workdir=Path(tempfile.mkdtemp(dir=paths.guest_tmp())),
    python_version=m.python, stdlib=d / "python-stdlib.zip", env=upstream.ENV,
    preopens=[("/kit", kit, False)], measured=False, fuel=50 * 10**9,
)
print(r.stdout.decode(), r.stderr.decode()[-500:])
