"""Spec 073's probes: why `run` on the snapshot loses an unclosed file's bytes, and what each fix
costs. Each case runs once per binary through the judge's own driver (seeded entropy, stepped
clock), so fuel repeats; it prints the bytes `/out.txt` kept, the fuel, and stderr's last line.

    WASI_PYTHON_ARTIFACTS=<set> PYTHONPATH=tests uv run python <this file> [case ...]
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from harness import guest as driver
from harness import paths

OPEN = "f = open('/out.txt', 'w')\nf.write('x' * 100)\n"
GAP = OPEN + "def g():\n    pass\n"  # check (h)'s program, tests/checks/test_v1_4_embedding.py
REPORTER = (
    "import os\n"
    "class R:\n"
    "    def __del__(self, w=os.write):\n"
    "        w(2, b'R finalized\\n')\n"
    "r = R()\n"
)
# Fix simulations, appended to the program: they run inside _reactor.run, before Py_FinalizeEx.
UNFREEZE = "\nimport gc\ngc.unfreeze()\n"
IMPORT_GC = "\nimport gc\n"
WALK = (
    "\nimport gc as _gc, io as _io\n"
    "for _o in _gc.get_objects():\n"
    "    if isinstance(_o, _io.IOBase):\n"
    "        try:\n"
    "            _o.flush()\n"
    "        except Exception:\n"
    "            pass\n"
)


def fresh_main(source: str) -> str:
    """The program run in a new, unfrozen __main__ made at run time, as _reactor.run would make
    it; the wrapper runs in a private namespace, so the frozen __main__ keeps nothing of it."""
    wrap = (
        "import sys\n"
        "old = sys.modules['__main__']\n"
        "new = type(old)('__main__')\n"
        "new.__dict__.update(old.__dict__)\n"
        "sys.modules['__main__'] = new\n"
        "exec(compile(SRC, '<string>', 'exec'), new.__dict__)\n"
    )
    return f"exec({wrap!r}, {{'__builtins__': __builtins__, 'SRC': {source!r}}})\n"


ZIPPED = (
    "import zipfile\n"
    "z = zipfile.ZipFile('/out.zip', 'w')\n"
    "z.writestr('a.txt', 'x' * 100)\n"
    "def g():\n    pass\n"
)

CASES: dict[str, tuple[list[str], dict[str, str]]] = {
    # the cause
    "gap": (["-c", GAP], {}),
    "no-def": (["-c", OPEN], {}),
    "class": (["-c", OPEN + "class C:\n    pass\n"], {}),
    "lambda": (["-c", OPEN + "h = lambda: 0\n"], {}),
    "main-kept-alive": (["-c", GAP + "import sys\nsys.kept = sys.modules['__main__']\n"], {}),
    "reporter": (["-c", REPORTER + "def g():\n    pass\n"], {}),
    "reporter-no-def": (["-c", REPORTER], {}),
    "script": (["/prog.py"], {"/prog.py": GAP}),
    "zip-left-open": (["-c", ZIPPED], {}),
    # the fixes, simulated in the program
    "bare": (["-c", "pass"], {}),
    "bare+import-gc": (["-c", "pass" + IMPORT_GC], {}),
    "bare+unfreeze": (["-c", "pass" + UNFREEZE], {}),
    "bare+walk": (["-c", "pass" + WALK], {}),
    "bare+fresh-main": (["-c", fresh_main("pass")], {}),
    "gap+import-gc": (["-c", GAP + IMPORT_GC], {}),
    "gap+unfreeze": (["-c", GAP + UNFREEZE], {}),
    "gap+walk": (["-c", GAP + WALK], {}),
    "gap+fresh-main": (["-c", fresh_main(GAP)], {}),
    "zip+unfreeze": (["-c", ZIPPED + UNFREEZE], {}),
    "zip+walk": (["-c", ZIPPED + WALK], {}),
    "zip+fresh-main": (["-c", fresh_main(ZIPPED)], {}),
    "pandas": (["-c", "import pandas"], {}),
    "pandas+import-gc": (["-c", "import pandas" + IMPORT_GC], {}),
    "pandas+unfreeze": (["-c", "import pandas" + UNFREEZE], {}),
    "pandas+walk": (["-c", "import pandas" + WALK], {}),
    "pandas+fresh-main": (["-c", fresh_main("import pandas")], {}),
}


def kept(root: Path) -> str:
    out, z = root / "out.txt", root / "out.zip"
    if z.exists():
        import zipfile

        try:
            with zipfile.ZipFile(z) as f:
                return f"zip ok {len(f.read('a.txt'))}"
        except zipfile.BadZipFile:
            return f"zip BAD ({z.stat().st_size} bytes)"
    return str(out.stat().st_size) if out.exists() else "-"


def main(names: list[str]) -> None:
    d = paths.artifact_dir()
    m = paths.parse_manifest((d / "MANIFEST").read_text())
    work = Path(tempfile.mkdtemp(prefix="probe-073-", dir=Path("build/073").resolve()))
    print(f"{'case':22} {'binary':9} {'kept':>14} {'fuel':>15}  stderr")
    for name in names or list(CASES):
        argv, files = CASES[name]
        for which, wasm in (("plain", "python.wasm"), ("snapshot", "python-snapshot.wasm")):
            r = driver.run(
                d / wasm,
                argv,
                workdir=work,
                python_version=m.python,
                stdlib=d / "python-stdlib.zip",
                files=files,
            )
            err = r.stderr.decode(errors="replace").strip().replace("\n", " | ")[-60:]
            status = "" if r.exit_code == 0 else f" exit={r.exit_code} trap={r.trapped}"
            print(f"{name:22} {which:9} {kept(r.root):>14} {r.fuel:>15,}  {err}{status}")


if __name__ == "__main__":
    main(sys.argv[1:])
