"""Spec 083 probe: the lxml import's fuel when the zip's inode number answered is a chosen value
(times fixed). Usage: probe_ino.py <tests dir (pa)> <work> <program> <ino>..."""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from harness import guest  # noqa: E402
SET = Path("/Users/claygendron/Git/Repos/wasi_python/build/sets/s-c50ca51fae5eb55b-c9dcb5b8")
code = Path(sys.argv[3]).read_text()
work = Path(tempfile.mkdtemp(dir=sys.argv[2]))
for ino in map(lambda s: int(s, 0), sys.argv[4:]):
    guest.FileFacts.ino = lambda self, real, _i=ino: _i
    r = guest.run(SET / "python-snapshot.wasm", ["-c", code], workdir=work, python_version="3.15", stdlib=SET / "python-stdlib.zip")
    print(hex(ino), r.exit_code, r.fuel)
