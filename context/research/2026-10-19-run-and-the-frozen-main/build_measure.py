"""Spec 073's build: criterion 4 and the amendment's rows, measured on two sets through the judge's
driver: main's (a fresh `cp -Rp` copy) and the built one. Bare `-c pass`, the gap, and `import
pandas`, on both binaries; check (b)'s factor on each set.

    PYTHONPATH=tests uv run python <this file> <main set> <built set>
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from harness import guest as driver
from harness import paths

GAP = "f = open('/out.txt', 'w')\nf.write('x' * 100)\ndef g():\n    pass\n"
PROGRAMS = {"bare": "pass", "gap": GAP, "import pandas": "import pandas"}


def fuel(d: Path, which: str, src: str, work: Path) -> tuple[int, str]:
    m = paths.parse_manifest((d / "MANIFEST").read_text())
    wasm = d / ("python-snapshot.wasm" if which == "snapshot" else "python.wasm")
    r = driver.run(wasm, ["-c", src], workdir=work, python_version=m.python,
                   stdlib=d / "python-stdlib.zip")
    assert r.exit_code == 0, r.describe()
    out = r.root / "out.txt"
    return r.fuel, (str(out.stat().st_size) if out.exists() else "-")


def main(main_set: Path, built: Path) -> None:
    work = Path(tempfile.mkdtemp(prefix="measure-073-", dir=Path("build/073").resolve()))
    got: dict = {}
    for name, src in PROGRAMS.items():
        for which in ("snapshot", "plain"):
            a, ka = fuel(main_set, which, src, work)
            b, kb = fuel(built, which, src, work)
            got[(name, which)] = (a, b)
            print(f"{name:14} {which:9} main {a:>15,} (kept {ka:>3})  built {b:>15,} (kept {kb:>3})"
                  f"  rise {b - a:+,} ({(b - a) / a:+.2%})")
    for label, i in (("main", 0), ("built", 1)):
        p, s = got[("bare", "plain")][i], got[("bare", "snapshot")][i]
        print(f"check (b) on {label}: plain {p:,} / snapshot {s:,} = {p / s:.3f}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
