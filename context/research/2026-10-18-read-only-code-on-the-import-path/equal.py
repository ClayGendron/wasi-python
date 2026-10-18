"""Byte equality of exit code, stdout and stderr with and without the prelude (memo §2).

    WASI_PYTHON_ARTIFACTS=<set> uv run python <this file> <scratch dir>
"""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from probe import prelude  # noqa: E402

from wasi_python import Grant, run  # noqa: E402

code = Path(sys.argv[1]).resolve()
shutil.rmtree(code, ignore_errors=True)
code.mkdir(parents=True)
(code / "boom.py").write_text("def f():\n    return 1 / 0\nf()\n")
g = [Grant(str(code), "/code")]
cases = [
    ["-V"],
    ["-u", "-c", "print(1)"],
    ["-c", "import sys; sys.exit(7)"],
    ["-c", "raise SystemExit('bye')"],
    ["-c", "1/0"],
    ["/code/boom.py"],
    ["/code/nope.py"],
    ["-c", "import sys; print(sys.orig_argv, sorted(k for k in dir() if not k.startswith('__')))"],
]
for snap in (True, False):
    for a in cases:
        x = run(a, grants=g, snapshot=snap)
        y = run(prelude(["/code"]) + a, grants=g, snapshot=snap)
        same = (x.exit_code, x.stdout, x.stderr) == (y.exit_code, y.stdout, y.stderr)
        print("snapshot" if snap else "plain", a, "equal" if same else "DIFFERENT")
