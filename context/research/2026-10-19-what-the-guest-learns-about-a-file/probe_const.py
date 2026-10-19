"""Spec 083 probe: the lxml import's fuel when every time answered is one constant.
Usage: probe_const.py <tests dir (pa)> <work> <program> <ns>..."""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from harness import guest  # noqa: E402
SET = Path("/Users/claygendron/Git/Repos/wasi_python/build/sets/s-c50ca51fae5eb55b-c9dcb5b8")
code = Path(sys.argv[3]).read_text()
work = Path(tempfile.mkdtemp(dir=sys.argv[2]))
for ns in map(int, sys.argv[4:]):
    guest.FileFacts.stamp = lambda self, ino, real, _ns=ns: (_ns, _ns, _ns)
    r = guest.run(SET / "python-snapshot.wasm", ["-c", code], workdir=work, python_version="3.15", stdlib=SET / "python-stdlib.zip")
    print(ns, r.exit_code, r.fuel)
