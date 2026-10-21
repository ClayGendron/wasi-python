"""The three families' shards in tests/release_shards.toml, and the release workflow's lists of
the Linux and release shards, from the TOMLs' measured fuel.

    uv run python gen_shards.py
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

W = Path("/Users/claygendron/Git/Repos/wasi_python/.claude/worktrees/agent-aab0b516adb4e5c06")
sys.path.insert(0, str(W / "tests"))
PLAN = W / "tests/release_shards.toml"
WF = W / ".github/workflows/release.yml"
BOUND = 725e9
DERIVED = 8.59e9  # scipy's derived run, once per shard that stages scipy
START = "# scipy's, scikit-learn's and statsmodels' own tests"
END = "# end of scipy's, scikit-learn's and statsmodels' shards"

measured: dict[str, int] = {}
tier: dict[str, str] = {}
family: dict[str, str] = {}
for fam in ("scipy", "scikit-learn", "statsmodels"):
    cfg = tomllib.loads((W / f"tests/upstream/{fam}.toml").read_text())
    for name, g in cfg["groups"].items():
        measured[name] = int(g["measured"])
        tier[name] = g.get("tier", "normal")
        family[name] = fam

normal = [
    ("upstream-sci-smoke-a", ["scipy-smoke-a", "scipy-smoke-b"]),
    ("upstream-sci-smoke-b", ["scikit-learn-smoke", "statsmodels-smoke"]),
]
release = [g for g in measured if tier[g] == "release"]


def cost(groups: list[str]) -> float:
    c = sum(measured[g] for g in groups)
    return c + (DERIVED if any(family[g] == "scipy" for g in groups) else 0)


bins: list[list[str]] = []
for g in sorted(release, key=lambda g: -measured[g]):
    for b in bins:
        if cost(b + [g]) <= BOUND:
            b.append(g)
            break
    else:
        bins.append([g])
bins.sort(key=lambda b: -cost(b))
rel = [(f"upstream-sci-release-{i + 1:02d}", b) for i, b in enumerate(bins)]

lines = [
    START,
    "# (the subpackage-folder families). Their normal tier, a smoke group per package, in two Linux",
    "# shards; their release tier, every other group, in release shards packed by the measured",
    "# darwin fuel to at most 725 G each (a group past it alone), scipy's derived test data counted",
    "# once in each shard that stages scipy.",
]
for name, groups in normal:
    lines += ["", f"[shard.{name}]", f"# {cost(groups) / 1e9:.1f} G measured", "groups = [" + ", ".join(f'"{g}"' for g in groups) + "]", 'systems = ["linux"]']
for name, groups in rel:
    lines += ["", f"[shard.{name}]", f"# {cost(groups) / 1e9:.1f} G measured", "groups = [" + ", ".join(f'"{g}"' for g in groups) + "]", 'systems = ["release"]']
lines += ["", END]
text = PLAN.read_text()
if START in text:
    text = text[: text.index(START)] + text[text.index(END) + len(END) + 1 :]
text = text.rstrip() + "\n\n" + "\n".join(lines) + "\n"
PLAN.write_text(text)

from harness import shards  # noqa: E402

plan = shards.load(PLAN)
linux, rels = shards.on(plan, "linux"), shards.on(plan, "release")
wf = WF.read_text()


def outputs(names: list[str]) -> str:
    return "".join(
        f"      {n}-id: ${{{{ steps.out.outputs.{n}-id }}}}\n      {n}-sha256: ${{{{ steps.out.outputs.{n}-sha256 }}}}\n"
        for n in names
    )


def job_block(wf: str, job: str, names: list[str]) -> str:
    start = wf.index(f"\n  {job}:\n")
    end = wf.index("\n  judge-", start + 10) if job != "judge-release" else wf.index("\n  gather:\n", start)
    body = wf[start:end]
    body = re.sub(r"(        shard: \[).*(\])", lambda m: m[1] + ", ".join(names) + m[2], body, count=1)
    body = re.sub(r"    outputs:\n(      [\w-]+: .*\n)+", "    outputs:\n" + outputs(names).replace("\\", "\\\\"), body, count=1)
    return wf[:start] + body + wf[end:]


wf = job_block(wf, "judge-linux", linux)
wf = job_block(wf, "judge-release", rels)


def env(sys_: str, n: str) -> str:
    return sys_ + "_" + n.upper().replace("-", "_")


job = {"LINUX": "judge-linux", "RELEASE": "judge-release"}
for sys_, names in (("LINUX", linux), ("RELEASE", rels)):
    j = job[sys_]
    pat = re.compile(rf"(          {sys_}_[A-Z0-9_]+_ID: \$\{{\{{ needs\.{j}\.outputs\.[\w-]+-id \}}\}}\n)+")
    new = "".join(f"          {env(sys_, n)}_ID: ${{{{ needs.{j}.outputs.{n}-id }}}}\n" for n in names)
    wf, k = pat.subn(new.replace("\\", "\\\\"), wf)
    assert k == 1, (sys_, "ids", k)
    pat = re.compile(rf"(          RECORD_{sys_}_[A-Z0-9_]+: \$\{{\{{ needs\.{j}\.outputs\.[\w-]+-sha256 \}}\}}\n)+")
    new = "".join(f"          RECORD_{env(sys_, n)}: ${{{{ needs.{j}.outputs.{n}-sha256 }}}}\n" for n in names)
    wf, k = pat.subn(new.replace("\\", "\\\\"), wf)
    assert k == 1, (sys_, "records", k)
    ids = ",".join(f"${{{{ needs.{j}.outputs.{n}-id }}}}" for n in names)
    wf, k = re.subn(rf"(          artifact-ids: )\$\{{\{{ needs\.{j}\.outputs\.[^\n]*", lambda m: m[1] + ids, wf)
    assert k == 1, (sys_, "artifact-ids", k)


def fix_for(m: re.Match) -> str:
    toks = m[2].split()
    lin = [f'"${env("LINUX", n)}_ID"' for n in linux]
    if not any(t.startswith(('"$LINUX_', '"$RELEASE_')) for t in toks):
        return m[0]
    if all(t.startswith('"$RELEASE_') for t in toks):
        toks = [f'"${env("RELEASE", n)}_ID"' for n in rels]
    else:
        first = next(i for i, t in enumerate(toks) if t.startswith('"$LINUX_'))
        last = max(i for i, t in enumerate(toks) if t.startswith('"$LINUX_'))
        toks = toks[:first] + lin + toks[last + 1 :]
    return m[1] + " ".join(toks) + m[3]


wf = re.sub(r"(          for id in )(.*?)(; do\n)", fix_for, wf)
WF.write_text(wf)
for n, b in normal + rel:
    print(n, f"{cost(b) / 1e9:.1f}", b)
print(len(rel), "release shards")
