"""Spec 073: the gap's program in each of run's modes (-c, a script, -m), on each binary, through
the judge's driver. -m reaches a read-only folder on the import path the way the runner's
prelude does (src/wasi_python/runner.py, _import_prelude).

    WASI_PYTHON_ARTIFACTS=<set> PYTHONPATH=tests uv run python <this file>
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from harness import guest as driver
from harness import paths

GAP = "f = open('/out.txt', 'w')\nf.write('x' * 100)\ndef g():\n    pass\n"
ARGV0 = "/usr/local/bin/python.wasm"
PRELUDE = (
    "__import__('sys').path.extend(['/lib']) or __import__('sys').exit(__import__('_reactor')"
    f".run([{ARGV0!r}, '-m', 'prog'], dict(__import__('os').environ)))"
)


def main() -> None:
    d = paths.artifact_dir()
    m = paths.parse_manifest((d / "MANIFEST").read_text())
    work = Path(tempfile.mkdtemp(prefix="probe-073m-", dir=Path("build/073").resolve()))
    lib = work / "lib"
    lib.mkdir()
    (lib / "prog.py").write_text(GAP)
    modes = {
        "-c": (["-c", GAP], {}, None),
        "script": (["/prog.py"], {"/prog.py": GAP}, None),
        "-m (prelude)": (["-c", PRELUDE], {}, [("/lib", lib, False)]),
    }
    for mode, (argv, files, preopens) in modes.items():
        for which, wasm in (("plain", "python.wasm"), ("snapshot", "python-snapshot.wasm")):
            r = driver.run(
                d / wasm, argv, workdir=work, python_version=m.python,
                stdlib=d / "python-stdlib.zip", files=files, preopens=preopens,
            )
            out = r.root / "out.txt"
            kept = out.stat().st_size if out.exists() else "-"
            tail = r.stderr.decode(errors="replace").strip()[-80:]
            print(f"{mode:14} {which:9} exit {r.exit_code} kept {kept:>4}  {tail}")


if __name__ == "__main__":
    main()
