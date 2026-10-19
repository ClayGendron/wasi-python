"""Spec 083 probe: correlate fuel with each filestat answer's fields (prototype driver)."""
import struct, sys, tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from harness import guest  # noqa: E402
SET = Path("/Users/claygendron/Git/Repos/wasi_python/build/sets/s-c50ca51fae5eb55b-c9dcb5b8")
seen = []
orig = guest._Stats._rewrite
def rewrite(self, caller, memory, at):
    r = orig(self, caller, memory, at)
    raw = bytes(memory.read(caller, at, at + 64))
    seen.append(struct.unpack("<QQB7xQQQQQ", raw))
    return r
guest._Stats._rewrite = rewrite
code = "import os\nopen('/f', 'w').write('x')\nos.stat('/f')"
work = Path(tempfile.mkdtemp(dir=sys.argv[2]))
rows = []
for _ in range(int(sys.argv[3])):
    seen.clear()
    r = guest.run(SET / "python-snapshot.wasm", ["-c", code], workdir=work, python_version="3.15", stdlib=SET / "python-stdlib.zip")
    rows.append((r.fuel, [s for s in seen]))
lo = min(f for f, _ in rows)
for f, s in rows:
    print(f - lo, [(x[1], hex(x[1]), x[2], x[3], x[4]) for x in s][:1], [x[5:] == s[0][5:] for x in s])
