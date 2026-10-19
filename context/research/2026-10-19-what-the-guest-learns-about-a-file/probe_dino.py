"""Spec 083 probe: does fd_readdir's d_ino equal fd_filestat's ino (main's driver)?"""
import os
import atexit, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from harness import guest  # noqa: E402
SET = Path(os.environ.get("P083_SET") or sys.exit("P083_SET: a private copy of the set (cp -c -Rp)"))
code = """import os
os.mkdir('/d'); open('/d/a', 'w').close(); os.mkdir('/d/s')
for e in os.scandir('/d'):
    print(e.name, e.inode() == os.stat(e.path).st_ino, e.inode() == e.stat(follow_symlinks=False).st_ino, hex(e.inode()))
print('dev', os.stat('/d').st_dev, os.stat('/d/a').st_dev)
"""
work = Path(tempfile.mkdtemp(dir=sys.argv[2]))
atexit.register(shutil.rmtree, work, True)  # its run folders hold links to the set's zip
r = guest.run(SET / "python-snapshot.wasm", ["-c", code], workdir=work, python_version="3.15", stdlib=SET / "python-stdlib.zip")
print(r.text, r.describe())
