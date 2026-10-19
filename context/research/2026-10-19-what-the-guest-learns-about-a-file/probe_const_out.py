"""Spec 083 probe: a program's output when every time answered is one constant (the 'constant'
design), against the prototype's own answers. Usage: probe_const_out.py <tests dir (pa)> <work> <program>"""
import atexit, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from harness import guest  # noqa: E402
SET = Path("/Users/claygendron/Git/Repos/wasi_python/build/sets/s-c50ca51fae5eb55b-c9dcb5b8")
code = Path(sys.argv[3]).read_text()
work = Path(tempfile.mkdtemp(dir=sys.argv[2]))
atexit.register(shutil.rmtree, work, True)  # its run folders hold links to the set's zip
for label in ("the clock's next value on a change", "one constant"):
    if label == "one constant":
        guest.FileFacts.stamp = lambda self, ino, real: (guest.REALTIME_START_NS - 10**9,) * 3
    r = guest.run(SET / "python-snapshot.wasm", ["-c", code], workdir=work, python_version="3.15", stdlib=SET / "python-stdlib.zip")
    print(f"{label}: exit {r.exit_code}; stdout {r.text.strip()!r}; stderr tail {r.stderr.decode().strip().splitlines()[-1:]}")
