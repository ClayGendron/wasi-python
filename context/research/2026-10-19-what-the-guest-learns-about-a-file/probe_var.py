"""Spec 083 probe: one program, N runs, through the driver in <tests dir>, with a variant
patched in (none, norewrite, norestore). Usage: probe_var.py <tests dir> <N> <work> <variant>"""
import os
import atexit, collections, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from harness import guest  # noqa: E402
SET = Path(os.environ.get("P083_SET") or sys.exit("P083_SET: a private copy of the set (cp -c -Rp)"))
N, variant = int(sys.argv[2]), sys.argv[4]
calls = getattr(guest, "_FileCalls", None) or getattr(guest, "_Stats", None)
if variant == "norewrite":  # forward wasmtime's answers unchanged
    calls._answer = lambda self, caller, at: None
    calls.fd_readdir = lambda self, caller, *a: self.call(caller, self.funcs["fd_readdir"], *a)
if variant == "norestore":  # let the trampoline's instructions count
    calls.call = lambda self, caller, func, *args: func(caller, *args)
code = sys.argv[5] if len(sys.argv) > 5 else "import os, time\nopen('/f', 'w').write('x')\nprint(time.localtime(os.stat('/f').st_mtime).tm_year)"
work = Path(tempfile.mkdtemp(dir=sys.argv[3]))
atexit.register(shutil.rmtree, work, True)  # its run folders hold links to the set's zip
fuels = []
for _ in range(N):
    r = guest.run(SET / "python-snapshot.wasm", ["-c", code], workdir=work, python_version="3.15", stdlib=SET / "python-stdlib.zip")
    assert r.exit_code == 0, r.describe()
    fuels.append(r.fuel)
lo = min(fuels)
print(variant, lo, dict(sorted(collections.Counter(f - lo for f in fuels).items())))
