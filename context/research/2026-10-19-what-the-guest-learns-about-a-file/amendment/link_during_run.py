"""Spec 083 amendment probe: another run links the shared stdlib zip while this guest runs.

The guest stats the zip, calls the door (the host links the set's zip once more, as a concurrent
run's driver does), and stats it again. With `copy`, the driver's `_place` copies files instead of
linking them. The run folder is removed at the end, whatever happens.
Usage: uv run python -I link_during_run.py <tests dir> <work dir> [copy]"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, sys.argv[1])
from harness import guest  # noqa: E402

SET = Path(os.environ.get("P083_SET") or sys.exit("P083_SET: a private copy of the set (cp -c -Rp)"))
work = Path(tempfile.mkdtemp(prefix="link-", dir=sys.argv[2]))
extra = work / "extra-link.zip"

if sys.argv[3:] == ["copy"]:

    def place(src: Path, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)

    guest._place = place


def host(frame: bytes) -> bytes:
    os.link(SET / "python-stdlib.zip", extra)
    return b""


PROG = (
    "import os, _host\n"
    "z = '/usr/local/lib/python315.zip'\n"
    "a = os.stat(z)\n"
    "_host.call(b'link')\n"
    "b = os.stat(z)\n"
    "print('nlink', a.st_nlink, b.st_nlink, 'ctime same', a.st_ctime_ns == b.st_ctime_ns,"
    " 'mtime same', a.st_mtime_ns == b.st_mtime_ns)\n"
)
try:
    r = guest.run(
        SET / "python-snapshot.wasm",
        ["-c", PROG],
        workdir=work,
        python_version="3.15",
        stdlib=SET / "python-stdlib.zip",
        host=host,
    )
    print(r.text.strip() or r.describe(), "| fuel", r.fuel)
finally:
    shutil.rmtree(work, ignore_errors=True)
