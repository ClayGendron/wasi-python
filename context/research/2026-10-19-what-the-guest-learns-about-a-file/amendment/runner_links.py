"""Spec 083 amendment probe: can a guest make a hard link through the product runner? A writable
grant, `os.link` inside it, and both names' link counts. The grant folder is removed at the end.
Usage: WASI_PYTHON_ARTIFACTS=<set> uv run python -I runner_links.py <work dir>"""
import shutil, sys, tempfile
from pathlib import Path
from wasi_python import Grant, run
work = Path(tempfile.mkdtemp(prefix="rlink-", dir=sys.argv[1]))
try:
    code = ("import os\nopen('/w/a', 'w').write('x')\nos.link('/w/a', '/w/b')\n"
            "print(os.stat('/w/a').st_nlink, os.stat('/w/b').st_nlink, os.path.samefile('/w/a', '/w/b'))")
    done = run(["-c", code], root=False, grants=[Grant(work, "/w", writable=True)])
    print("guest:", done.stdout.decode().strip() or done, "| host nlink of a:", (work / "a").stat().st_nlink)
finally:
    shutil.rmtree(work, ignore_errors=True)
