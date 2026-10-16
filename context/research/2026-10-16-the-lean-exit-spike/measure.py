"""SPIKE: what each exit mode costs and what it keeps.

    uv run python context/research/2026-10-16-the-lean-exit-spike/measure.py

Runs the lean-exit variant (build/spike-lean-exit/, from build.sh beside this file) through the
judge's own driver, so fuel (instructions executed) is exact and repeatable. Each program checks
one guarantee a native Python exit gives; a mode keeps it when the expected bytes are where they
should be after the run.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tests"))

from harness import guest, jobs  # noqa: E402

SPIKE = REPO / "build" / "spike-lean-exit"
MODES = {
    0: "full finalize (today)",
    1: "flush stdio",
    2: "+ atexit",
    3: "+ clear __main__, gc",
    4: "+ clear new modules, gc",
    5: "+ close open files, gc",
    6: "5 + freeze at start",
}
HELPER = "log = open('/w/helper.txt', 'w')\nlog.write('helper')\n"

# name -> (argv, files, (path in root, expected bytes) or None for stdout)
CASES = {
    "pass": (["-c", "pass"], {}, None),
    "print, no newline": (["-c", "print('kept', end='')"], {}, ("stdout", b"kept")),
    "unclosed file in __main__": (
        ["-c", "f = open('/w/a.txt', 'w'); f.write('main')"],
        {},
        ("w/a.txt", b"main"),
    ),
    "atexit handler": (
        ["-c", "import atexit\natexit.register(lambda: open('/w/b.txt', 'w').write('bye'))"],
        {},
        ("w/b.txt", b"bye"),
    ),
    "file held by an imported module": (
        ["/w/main.py"],
        {
            "/w/main.py": "import sys\nsys.path.insert(0, '/w')\nimport helper\n",
            "/w/helper.py": HELPER,
        },
        ("w/helper.txt", b"helper"),
    ),
    "file in a reference cycle (native loses it too)": (
        [
            "-c",
            "class A: pass\na = A(); a.me = a; a.f = open('/w/c.txt', 'w'); a.f.write('cycle'); del a",
        ],
        {},
        ("w/c.txt", b"cycle"),
    ),
    "__del__ of an object in __main__": (
        ["-c", "class D:\n    def __del__(self): open('/w/e.txt', 'w').write('del')\nd = D()"],
        {},
        ("w/e.txt", b"del"),
    ),
    "__del__ of an object a module holds": (
        ["/w/main.py"],
        {
            "/w/main.py": "import sys\nsys.path.insert(0, '/w')\nimport holder\n",
            "/w/holder.py": "class D:\n    def __del__(self): open('/w/f.txt', 'w').write('del')\nd = D()\n",
        },
        ("w/f.txt", b"del"),
    ),
    "logging to a file": (
        ["-c", "import logging\nlogging.basicConfig(filename='/w/d.log')\nlogging.warning('hi')"],
        {},
        ("w/d.log", b"WARNING:root:hi\n"),
    ),
}


def pandas_job_files() -> dict[str, bytes]:
    files = {"/jobs/pandas_csv.py": jobs.script("pandas_csv").read_bytes(), "/out/.keep": b""}
    files.update({f"/data/{n}": src.read_bytes() for n, src in jobs.DATA.items()})
    return files


def main() -> int:
    manifest = (SPIKE / "MANIFEST").read_text().split("\n", 1)[0].split()[1]
    zip_path = SPIKE / "python-stdlib.zip"
    with tempfile.TemporaryDirectory() as d:
        work = Path(d)
        for binary in ("python-snapshot.wasm", "python.wasm"):
            print(f"== {binary}")
            header = f"{'program':34}" + "".join(f"{m:>16}" for m in MODES)
            print(header)
            cases = dict(CASES)
            cases["pandas csv job"] = (
                ["/jobs/pandas_csv.py", "/data", "/out"],
                pandas_job_files(),
                None,
            )
            for name, (argv, files, expect) in cases.items():
                cells = []
                for mode in MODES:
                    r = guest.run(
                        SPIKE / binary,
                        argv,
                        workdir=work,
                        python_version=manifest,
                        stdlib=zip_path,
                        files={"/w/.keep": b"", **files},
                        env={"WASI_PYTHON_EXIT_MODE": str(mode)},
                    )
                    kept = "ok"
                    if r.exit_code != 0:
                        kept = f"exit {r.exit_code}"
                    elif expect is not None:
                        where, want = expect
                        got = r.stdout if where == "stdout" else _read(r.root / where)
                        kept = "kept" if got == want else "LOST"
                    noise = "!" if r.stderr.strip() else ""
                    cells.append(f"{r.fuel / 1e6:9.1f}M {kept:>4}{noise}")
                print(f"{name:34}" + "".join(f"{c:>16}" for c in cells))
    print("M = million instructions (fuel); ! = the run wrote to stderr")
    return 0


def _read(path: Path) -> bytes | None:
    return path.read_bytes() if path.is_file() else None


if __name__ == "__main__":
    raise SystemExit(main())
