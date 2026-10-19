"""Spec 083 amendment probe: does a guest's fuel move with the host link count of its stdlib zip?

A private copy of the set's zip is granted as the stdlib (the `guest` fixture's `stdlib=`), first
with no other link, then with 1,100 more links to it, made in the work folder. Each program runs
once at each count. With `copy`, the driver's `_place` copies files instead of linking them. The
work folder, links included, is removed at the end, whatever happens.
Usage: uv run python -I nlink_fuel.py <tests dir> <work dir> [copy]"""

import atexit
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, sys.argv[1])
from harness import guest  # noqa: E402

SET = Path(os.environ.get("P083_SET") or sys.exit("P083_SET: a private copy of the set (cp -c -Rp)"))
work = Path(tempfile.mkdtemp(prefix="nlink-", dir=sys.argv[2]))
atexit.register(shutil.rmtree, work, True)  # its run folders and links hold the zip copy's links
mine = work / "stdlib.zip"
shutil.copyfile(SET / "python-stdlib.zip", mine)

if sys.argv[3:] == ["copy"]:

    def place(src: Path, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)

    guest._place = place

PROGRAMS = {
    "stat the zip": "import os\nprint(os.stat('/usr/local/lib/python315.zip').st_nlink)",
    "import json and stat the zip": (
        "import json, os\nprint(json.dumps(os.stat('/usr/local/lib/python315.zip').st_nlink))"
    ),
}


def go(code: str) -> tuple[str, int]:
    r = guest.run(
        SET / "python-snapshot.wasm",
        ["-c", code],
        workdir=work,
        python_version="3.15",
        stdlib=mine,
    )
    return (r.text.strip() or r.describe()), r.fuel


before = {label: go(code) for label, code in PROGRAMS.items()}
links = work / "links"
links.mkdir()
for i in range(1100):
    os.link(mine, links / f"{i}.zip")
after = {label: go(code) for label, code in PROGRAMS.items()}
for label in PROGRAMS:
    (o1, f1), (o2, f2) = before[label], after[label]
    print(f"{label:30} host links {1}+run: guest nlink {o1}, fuel {f1:,} | "
          f"1,101+run: guest nlink {o2}, fuel {f2:,} | difference {f2 - f1:+,}")
