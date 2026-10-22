"""Stage a family once and run each case of one parametrized test alone in the guest at a fuel
cap, printing how each ended (a reading tool: which cases do not finish). Each case is its own
probe group, since the stage writes every group's arguments before it is sealed.

    uv run python probe_many.py <family> <fuel G> <file>::<function> --names a,b,c [--prefix numpy-]
"""

import sys
import tempfile
from dataclasses import replace
from pathlib import Path

W = Path("/Users/claygendron/Git/Repos/wasi_python/.claude/worktrees/agent-aab0b516adb4e5c06")
sys.path.insert(0, str(W / "tests"))
from harness import packages, paths, upstream  # noqa: E402

fam, fuel, target = sys.argv[1], int(float(sys.argv[2]) * 1e9), sys.argv[3]
names = sys.argv[sys.argv.index("--names") + 1].split(",")
prefix = sys.argv[sys.argv.index("--prefix") + 1] if "--prefix" in sys.argv else "numpy-"
file, func = target.split("::", 1)
cfg = upstream.load_all()[fam]
probes = {f"probe-{i}": f"{func}[{prefix}{x}]" for i, x in enumerate(names)}
extra = {g: upstream.Group(g, (file,), fuel) for g in probes}
cfg = replace(cfg, groups={**cfg.groups, **extra}, args=[*cfg.args, "-rf"])
paths.guest_tmp()
work = Path(tempfile.mkdtemp(dir=paths.guest_tmp()))
s = packages.Session(work, {fam: cfg})
orig = packages.group_args
packages.group_args = lambda c, g: (
    [*c.args, f"{packages.tree_root(c)}/{file}", f"-k{probes[g.name]}"] if g.name in probes else orig(c, g)
)
try:
    s.prepare(fam)
    for g, k in probes.items():
        text, run = s._run(fam, g, fuel)
        ends = [ln[:120] for ln in text.splitlines() if ln[:2] in ("R ", "E ")][-2:]
        print(f"{run.fuel / 1e9:7.1f} G  {run.trapped or 'ended'}  {k}  {ends}", flush=True)
finally:
    s.close()
