"""Run the snapshot once with plain python arguments, through the judge's guest driver.

uv run python probe.py [--stack <bytes>] [--ro <guest path>=<host dir>] -- <python args...>
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
args = sys.argv[1:]
if args[:1] == ["--stack"]:
    os.environ["CPY_STACK"] = args[1]
    args = args[2:]
import run_one  # noqa: E402
from harness import guest  # noqa: E402

pre = []
while args[0] == "--ro":
    g, h = args[1].split("=", 1)
    pre.append((g, run_one.Path(h), False))
    args = args[2:]
args = args[args.index("--") + 1 :]
wasm = run_one.SET / "python-snapshot.wasm"
run_one.preload(wasm)
w = run_one.WORK / "tmp"
w.mkdir(parents=True, exist_ok=True)
r = guest.run(wasm, args, workdir=w, python_version="3.15.0", stdlib=run_one.SET / "python-stdlib.zip",
              env=run_one.ENV, fuel=10**11, preopens=pre or None)
print("exit", r.exit_code, "trapped", r.trapped, "cause", r.trap_cause, "fuel", r.fuel)
print(r.stdout.decode(errors="replace")[-1500:])
print(r.stderr.decode(errors="replace")[-1500:])
import shutil; shutil.rmtree(r.root.parent, ignore_errors=True)
