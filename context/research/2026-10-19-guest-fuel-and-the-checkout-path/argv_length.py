"""Fuel of the lxml SAFETY program against the length of its host-path argument alone."""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, "tests"); sys.path.insert(0, "tests/checks")
from harness import guest, paths
import test_v1_3_lxml as t
A = Path("/Users/claygendron/Git/Repos/wasi_python/build/sets/s-c50ca51fae5eb55b")
m = paths.parse_manifest((A / "MANIFEST").read_text())
paths.HARNESS_TMP.mkdir(parents=True, exist_ok=True)
work = Path(tempfile.mkdtemp(prefix="probe081-", dir=paths.HARNESS_TMP))
ro, rw, pre = t._grants(work)
which = sys.argv[1]; CH = __import__("os").environ.get("CH", "a")
for n in [int(x) for x in sys.argv[2:]]:
    arg = "/" + CH * (n - len("/secret.txt") - 1) + "/secret.txt"
    r = guest.run(A / ("python-snapshot.wasm" if which == "snapshot" else "python.wasm"),
                  ["-c", t.SAFETY, arg], workdir=work, python_version=m.python,
                  stdlib=A / "python-stdlib.zip", preopens=pre)
    assert r.exit_code == 0, r.describe()
    print(which, len(arg), r.fuel, flush=True)
