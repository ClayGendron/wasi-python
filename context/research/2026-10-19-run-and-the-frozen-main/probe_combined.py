"""Spec 073, amended (question 103 answered: unfreeze before finalizing): the combined design, a
fresh __main__ per program and, on the snapshot only, gc.unfreeze() after the program and before
Py_FinalizeEx. Like for like: both sides run the same private wrapper, which compiles and execs
the program; the control runs it in the frozen __main__ with no unfreeze (today), the combined
case in a fresh __main__ and then unfreezes (on the snapshot; the plain binary has nothing frozen
and the design does not unfreeze there). Bytes kept and fuel, per binary, through the driver.

    WASI_PYTHON_ARTIFACTS=<set> PYTHONPATH=tests uv run python <this file>
"""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

from harness import guest as driver
from harness import paths

CONTROL = "import sys\nexec(compile(SRC, '<string>', 'exec'), sys.modules['__main__'].__dict__)\n"
FRESH = (
    "import sys\n"
    "old = sys.modules['__main__']\n"
    "new = type(old)('__main__')\n"
    "new.__dict__.update(old.__dict__)\n"
    "sys.modules['__main__'] = new\n"
    "exec(compile(SRC, '<string>', 'exec'), new.__dict__)\n"
)
UNFREEZE = "sys.modules['gc'].unfreeze()\n"  # gc is in a snapshot program's sys.modules at start
GAP = "f = open('/out.txt', 'w')\nf.write('x' * 100)\ndef g():\n    pass\n"
PATCHED = (
    "import json\nf = open('/out.txt', 'w')\nf.write('x' * 100)\n"
    "def default(self, o):\n    return str(o)\njson.JSONEncoder.default = default\n"
)
STASH = "import json\njson.log = open('/out.txt', 'w')\njson.log.write('x' * 100)\n"
ZIPPED = (
    "import zipfile\nz = zipfile.ZipFile('/out.zip', 'w')\nz.writestr('a.txt', 'x' * 100)\n"
    "def g():\n    pass\n"
)
PROGRAMS = {
    "bare": "pass",
    "gap": GAP,
    "patched class": PATCHED,
    "module attribute": STASH,
    "zip": ZIPPED,
    "import pandas": "import pandas",
}


def wrap(w: str, src: str) -> str:
    return f"exec({w!r}, {{'__builtins__': __builtins__, 'SRC': {src!r}}})\n"


def kept(root: Path) -> str:
    z, out = root / "out.zip", root / "out.txt"
    if z.exists():
        try:
            with zipfile.ZipFile(z) as f:
                return "zip ok" if f.read("a.txt") == b"x" * 100 else "zip short"
        except zipfile.BadZipFile:
            return "zip BAD"
    return str(out.stat().st_size) if out.exists() else "-"


def main() -> None:
    d = paths.artifact_dir()
    m = paths.parse_manifest((d / "MANIFEST").read_text())
    work = Path(tempfile.mkdtemp(prefix="probe-073x-", dir=Path("build/073").resolve()))
    for name, src in PROGRAMS.items():
        for which, wasm in (("plain", "python.wasm"), ("snapshot", "python-snapshot.wasm")):
            combined = FRESH + (UNFREEZE if which == "snapshot" else "")
            fuel = {}
            for case, w in (("control", CONTROL), ("combined", combined)):
                r = driver.run(
                    d / wasm, ["-c", wrap(w, src)], workdir=work, python_version=m.python,
                    stdlib=d / "python-stdlib.zip",
                )
                fuel[case] = r.fuel
                print(f"{name:16} {which:9} {case:9} exit {r.exit_code} kept {kept(r.root):>7} "
                      f"fuel {r.fuel:>15,}")
            print(f"{name:16} {which:9} combined - control = {fuel['combined'] - fuel['control']:+,}")


if __name__ == "__main__":
    main()
