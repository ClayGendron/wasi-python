"""Spec 073: what a fresh __main__ itself costs, apart from probe.py's wrapper. The control runs the
same wrapper (a private exec, then compile and exec of the program) in the frozen __main__; the
fresh case adds only the new module and the copy of its six names.

    WASI_PYTHON_ARTIFACTS=<set> PYTHONPATH=tests uv run python <this file>
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from harness import guest as driver
from harness import paths

CONTROL = (
    "import sys\n"
    "exec(compile(SRC, '<string>', 'exec'), sys.modules['__main__'].__dict__)\n"
)
FRESH = (
    "import sys\n"
    "old = sys.modules['__main__']\n"
    "new = type(old)('__main__')\n"
    "new.__dict__.update(old.__dict__)\n"
    "sys.modules['__main__'] = new\n"
    "exec(compile(SRC, '<string>', 'exec'), new.__dict__)\n"
)
GAP = "f = open('/out.txt', 'w')\nf.write('x' * 100)\ndef g():\n    pass\n"


def wrap(w: str, src: str) -> str:
    return f"exec({w!r}, {{'__builtins__': __builtins__, 'SRC': {src!r}}})\n"


def main() -> None:
    d = paths.artifact_dir()
    m = paths.parse_manifest((d / "MANIFEST").read_text())
    work = Path(tempfile.mkdtemp(prefix="probe-073c-", dir=Path("build/073").resolve()))
    for prog_name, src in (("bare", "pass"), ("gap", GAP), ("pandas", "import pandas")):
        fuels = {}
        for which, wasm in (("plain", "python.wasm"), ("snapshot", "python-snapshot.wasm")):
            for case, w in (("control", CONTROL), ("fresh", FRESH)):
                r = driver.run(
                    d / wasm, ["-c", wrap(w, src)], workdir=work, python_version=m.python,
                    stdlib=d / "python-stdlib.zip",
                )
                out = r.root / "out.txt"
                kept = out.stat().st_size if out.exists() else "-"
                fuels[(which, case)] = r.fuel
                print(f"{prog_name:7} {which:9} {case:8} exit {r.exit_code} kept {kept!s:>4} fuel {r.fuel:>15,}")
            print(f"{prog_name:7} {which:9} fresh - control = {fuels[(which, 'fresh')] - fuels[(which, 'control')]:+,}")


if __name__ == "__main__":
    main()
