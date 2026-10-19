"""Spec 083 probe: the lxml import's fuel when every time answered is one constant.
Usage: probe_const.py <tests dir (pa)> <work> <program> <ns>..."""
import os
import atexit, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from harness import guest  # noqa: E402
SET = Path(os.environ.get("P083_SET") or sys.exit("P083_SET: a private copy of the set (cp -c -Rp)"))
code = Path(sys.argv[3]).read_text()
work = Path(tempfile.mkdtemp(dir=sys.argv[2]))
atexit.register(shutil.rmtree, work, True)  # its run folders hold links to the set's zip
for ns in map(int, sys.argv[4:]):
    guest.FileFacts.stamp = lambda self, ino, real, _ns=ns: (_ns, _ns, _ns)
    r = guest.run(SET / "python-snapshot.wasm", ["-c", code], workdir=work, python_version="3.15", stdlib=SET / "python-stdlib.zip")
    print(ns, r.exit_code, r.fuel)
