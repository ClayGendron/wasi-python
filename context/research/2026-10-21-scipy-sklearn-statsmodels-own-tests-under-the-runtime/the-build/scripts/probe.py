"""Run some node ids of a family in the guest the judge's way, with a long traceback, and print
the guest's output (a reading tool for single failures; never a measurement).

    uv run python probe.py <family> <fuel G> <node id> ...
"""

import sys
import tempfile
from dataclasses import replace
from pathlib import Path

W = Path("/Users/claygendron/Git/Repos/wasi_python/.claude/worktrees/agent-aab0b516adb4e5c06")
sys.path.insert(0, str(W / "tests"))
from harness import packages, paths, upstream  # noqa: E402

fam, fuel, nodes = sys.argv[1], int(float(sys.argv[2]) * 1e9), sys.argv[3:]
configs = upstream.load_all()
cfg = configs[fam]
first = next(iter(cfg.groups.values()))
probe = upstream.Group("probe", tuple(nodes), fuel)
cfg = replace(cfg, groups={**cfg.groups, "probe": probe}, args=[*cfg.args, "--tb=long", "-rf"])
import os  # noqa: E402

if os.environ.get("CLOCK"):
    cfg = replace(cfg, keys=replace(cfg.keys, clock_steps={"probe": (int(os.environ["CLOCK"]), "x")}))
paths.guest_tmp()
work = Path(tempfile.mkdtemp(dir=paths.guest_tmp()))
s = packages.Session(work, {fam: cfg})
orig = packages.group_args
packages.group_args = lambda c, g: (
    [*c.args, *(f"{packages.tree_root(c)}/{n}" for n in nodes)] if g.name == "probe" else orig(c, g)
)
try:
    s.prepare(fam)
    text, run = s._run(fam, "probe", fuel)
    print(run.stdout[-12000:])
    print("fuel", run.fuel, "exit", run.exit_code, run.trapped)
finally:
    s.close()
