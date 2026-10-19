"""Spec 073: script and -m run in a fresh, unfrozen __main__ (simulated from -c), as CPython's own
entry points run them in __main__, against today's runpy.run_path and runpy.run_module, which run
them in a temporary module. Bytes kept and fuel, per binary, through the judge's driver.

    WASI_PYTHON_ARTIFACTS=<set> PYTHONPATH=tests uv run python <this file>
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from harness import guest as driver
from harness import paths

GAP = "f = open('/out.txt', 'w')\nf.write('x' * 100)\ndef g():\n    pass\n"
ARGV0 = "/usr/local/bin/python.wasm"
FRESH = (
    "import sys\n"
    "old = sys.modules['__main__']\n"
    "new = type(old)('__main__')\n"
    "new.__dict__.update(old.__dict__)\n"
    "sys.modules['__main__'] = new\n"
)
SCRIPT_IN_MAIN = FRESH + (
    "import runpy\n"
    "sys.argv = ['/prog.py']\n"
    "runpy._run_code(runpy._get_code_from_file('/prog.py', '__main__'), new.__dict__, None,\n"
    "                '__main__', None, '', '/prog.py')\n"
)
M_IN_MAIN = FRESH + (
    "import runpy\n"
    "sys.path.append('/lib')\n"
    "sys.argv = ['prog']\n"
    "runpy._run_module_as_main('prog')\n"
)
M_TODAY = (
    "__import__('sys').path.extend(['/lib']) or __import__('sys').exit(__import__('_reactor')"
    f".run([{ARGV0!r}, '-m', 'prog'], dict(__import__('os').environ)))"
)


def private(src: str) -> str:
    return f"exec({src!r}, {{'__builtins__': __builtins__}})\n"


def main() -> None:
    d = paths.artifact_dir()
    m = paths.parse_manifest((d / "MANIFEST").read_text())
    work = Path(tempfile.mkdtemp(prefix="probe-073i-", dir=Path("build/073").resolve()))
    lib = work / "lib"
    lib.mkdir()
    (lib / "prog.py").write_text(GAP)
    ro = [("/lib", lib, False)]
    cases = {
        "script today (run_path)": (["/prog.py"], None),
        "script in a fresh main": (["-c", private(SCRIPT_IN_MAIN)], None),
        "-m today (run_module)": (["-c", M_TODAY], ro),
        "-m in a fresh main": (["-c", private(M_IN_MAIN)], ro),
    }
    for name, (argv, preopens) in cases.items():
        for which, wasm in (("plain", "python.wasm"), ("snapshot", "python-snapshot.wasm")):
            r = driver.run(
                d / wasm, argv, workdir=work, python_version=m.python,
                stdlib=d / "python-stdlib.zip", files={"/prog.py": GAP}, preopens=preopens,
            )
            out = r.root / "out.txt"
            kept = out.stat().st_size if out.exists() else "-"
            tail = r.stderr.decode(errors="replace").strip()[-70:]
            print(f"{name:24} {which:9} exit {r.exit_code} kept {kept!s:>4} fuel {r.fuel:>13,}  {tail}")


if __name__ == "__main__":
    main()
