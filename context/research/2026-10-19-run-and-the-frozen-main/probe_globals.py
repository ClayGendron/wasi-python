"""Spec 073: what a program sees of its own namespace in each of run's modes, today, per binary,
through wasi_python.run: whether its globals are in a collector generation (not frozen), whether
they are __main__'s, and the names runpy or the interpreter set.

    WASI_PYTHON_ARTIFACTS=<set> uv run python <this file>
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import wasi_python
from wasi_python import Grant

PROBE = (
    "import gc, sys\n"
    "g = globals()\n"
    "print('unfrozen', any(o is g for o in gc.get_objects()),\n"
    "      'is __main__', g is sys.modules['__main__'].__dict__,\n"
    "      'names', sorted(k for k in g if k.startswith('__')),\n"
    "      'values', (__name__, g.get('__file__'), __package__, getattr(__spec__, 'name', None),\n"
    "                 type(__loader__).__name__, type(__builtins__).__name__),\n"
    "      'argv0', sys.argv[0])\n"
)

lib = Path(tempfile.mkdtemp(prefix="probe-073g-lib-", dir=Path("build/073").resolve()))
(lib / "prog.py").write_text(PROBE)
for snapshot in (False, True):
    which = "snapshot" if snapshot else "plain"
    for mode in ("-c", "stdin", "script", "-m"):
        root = Path(tempfile.mkdtemp(prefix="probe-073g-", dir=Path("build/073").resolve()))
        kw = {}
        if mode == "-c":
            argv = ["-c", PROBE]
        elif mode == "stdin":
            argv, kw = [], {"stdin": PROBE.encode()}
        elif mode == "script":
            (root / "prog.py").write_text(PROBE)
            argv = ["/prog.py"]
        else:
            argv, kw = ["-m", "prog"], {"grants": [Grant(lib, "/code")], "import_path": ["/code"]}
        done = wasi_python.run(argv, root=root, snapshot=snapshot, **kw)
        text = (done.stdout or b"").decode().strip() or done.stderr.decode()[-200:]
        print(f"{mode:6} {which:9} exit {done.exit_code}: {text}")
