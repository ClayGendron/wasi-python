"""Spec 073: keeping the snapshot's own modules alive through finalize_modules' removal step, so
its wipe of surviving modules (finalize_modules_clear_weaklist) clears their frozen dicts, as a
way to close the hole a fresh __main__ leaves (probe_modules.out). Simulated from the program:
`sys` is wiped last, so a list on it keeps every module alive through the wipe.

    WASI_PYTHON_ARTIFACTS=<set> PYTHONPATH=tests uv run python <this file>
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from harness import guest as driver
from harness import paths

KEEP = "\nimport sys as _s\n_s._wp073_keep = [m for m in _s.modules.values() if m is not _s.modules['__main__']]\n"
STASH = "import json\njson._wp073 = open('/out.txt', 'w')\njson._wp073.write('x' * 100)\n"
GAP = "f = open('/out.txt', 'w')\nf.write('x' * 100)\ndef g():\n    pass\n"


def main() -> None:
    d = paths.artifact_dir()
    m = paths.parse_manifest((d / "MANIFEST").read_text())
    work = Path(tempfile.mkdtemp(prefix="probe-073k-", dir=Path("build/073").resolve()))
    cases = {
        "bare": "pass",
        "bare+keep": "pass" + KEEP,
        "json-stash": STASH,
        "json-stash+keep": STASH + KEEP,
        "gap+keep (main not kept)": GAP + KEEP,
        "pandas": "import pandas",
        "pandas+keep": "import pandas" + KEEP,
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
            print(f"{name:26} {which:9} exit {r.exit_code} kept {kept!s:>4} fuel {r.fuel:>15,}  {tail}")


if __name__ == "__main__":
    main()
