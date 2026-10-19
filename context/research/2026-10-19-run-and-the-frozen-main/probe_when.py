"""Spec 073: when __main__'s module object dies, and when what its dict holds is finalized, on each
binary, through the judge's driver. The callbacks print len(sys.modules) and whether `os` still
has its dict: finalize_remove_modules leaves sys.modules full (values None); after it the dict is
empty; finalize_modules_clear_weaklist then wipes surviving modules (os among them).

    WASI_PYTHON_ARTIFACTS=<set> PYTHONPATH=tests uv run python <this file>
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from harness import guest as driver
from harness import paths

PROGRAM = (
    "import os, sys, weakref\n"
    "def say(what, w=os.write, s=sys, o=os):\n"
    "    w(2, f'{what}: sys.modules {len(s.modules)}, os wiped {o.__dict__.get(\"sep\") is None}\\n'.encode())\n"
    "class R:\n"
    "    def __del__(self, say=say):\n"
    "        say('a value in __main__ finalized')\n"
    "r = R()\n"
    "wr = weakref.ref(sys.modules['__main__'], lambda _, say=say: say('__main__ module died'))\n"
    "say('program ends')\n"
)


def main() -> None:
    d = paths.artifact_dir()
    m = paths.parse_manifest((d / "MANIFEST").read_text())
    work = Path(tempfile.mkdtemp(prefix="probe-073w-", dir=Path("build/073").resolve()))
    for which, wasm in (("plain", "python.wasm"), ("snapshot", "python-snapshot.wasm")):
        r = driver.run(
            d / wasm, ["-c", PROGRAM], workdir=work, python_version=m.python,
            stdlib=d / "python-stdlib.zip",
        )
        print(f"== {which}: exit {r.exit_code}, fuel {r.fuel:,}")
        print(r.stderr.decode(errors="replace").rstrip())


if __name__ == "__main__":
    main()
