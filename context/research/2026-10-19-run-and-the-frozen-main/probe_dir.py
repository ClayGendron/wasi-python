"""Spec 073: a directory target (`run(["/app"])`, `/app/__main__.py`), today, per binary, through
wasi_python.run: the gap's bytes, and the namespace probe_globals.py prints.

    WASI_PYTHON_ARTIFACTS=<set> uv run python <this file>
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import wasi_python

GAP = "f = open('/out.txt', 'w')\nf.write('x' * 100)\ndef g():\n    pass\n"
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
for snapshot in (False, True):
    which = "snapshot" if snapshot else "plain"
    for name, prog in (("gap", GAP), ("globals", PROBE)):
        root = Path(tempfile.mkdtemp(prefix="probe-073d-", dir=Path("build/073").resolve()))
        (root / "app").mkdir()
        (root / "app" / "__main__.py").write_text(prog)
        done = wasi_python.run(["/app"], root=root, snapshot=snapshot)
        out = root / "out.txt"
        kept = out.stat().st_size if out.exists() else "-"
        text = done.stdout.decode().strip() or done.stderr.decode()[-200:]
        print(f"dir {name:8} {which:9} exit {done.exit_code} kept {kept}: {text}")
