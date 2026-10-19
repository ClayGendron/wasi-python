"""Spec 073: the gap's file when the program monkeypatches a pre-imported class with a function
from __main__ (json.JSONEncoder.default, a common idiom), so __main__'s namespace is reachable
from the snapshot's frozen heap. Today, with a fresh __main__, with the snapshot's modules kept
alive (probe_keep.py), and with gc.unfreeze() before finalizing (probe.py), per binary.

    WASI_PYTHON_ARTIFACTS=<set> PYTHONPATH=tests uv run python <this file>
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from harness import guest as driver
from harness import paths

PATCHED = (
    "import json\n"
    "f = open('/out.txt', 'w')\n"
    "f.write('x' * 100)\n"
    "def default(self, o):\n"
    "    return str(o)\n"
    "json.JSONEncoder.default = default\n"
)
FRESH = (
    "import sys\n"
    "old = sys.modules['__main__']\n"
    "new = type(old)('__main__')\n"
    "new.__dict__.update(old.__dict__)\n"
    "sys.modules['__main__'] = new\n"
    "exec(compile(SRC, '<string>', 'exec'), new.__dict__)\n"
)
KEEP = "\nimport sys as _s\n_s._wp073_keep = [m for m in _s.modules.values() if m is not _s.modules['__main__']]\n"
UNFREEZE = "\nimport gc\ngc.unfreeze()\n"


def fresh(src: str) -> str:
    return f"exec({FRESH!r}, {{'__builtins__': __builtins__, 'SRC': {src!r}}})\n"


def main() -> None:
    d = paths.artifact_dir()
    m = paths.parse_manifest((d / "MANIFEST").read_text())
    work = Path(tempfile.mkdtemp(prefix="probe-073p-", dir=Path("build/073").resolve()))
    cases = {
        "patched": PATCHED,
        "patched, fresh main": fresh(PATCHED),
        "patched, fresh main+keep": fresh(PATCHED + KEEP),
        "patched+unfreeze": PATCHED + UNFREEZE,
    }
    for name, prog in cases.items():
        for which, wasm in (("plain", "python.wasm"), ("snapshot", "python-snapshot.wasm")):
            r = driver.run(
                d / wasm, ["-c", prog], workdir=work, python_version=m.python,
                stdlib=d / "python-stdlib.zip",
            )
            out = r.root / "out.txt"
            kept = out.stat().st_size if out.exists() else "-"
            tail = r.stderr.decode(errors="replace").strip()[-60:]
            print(f"{name:26} {which:9} exit {r.exit_code} kept {kept!s:>4} fuel {r.fuel:>13,}  {tail}")


if __name__ == "__main__":
    main()
