"""Summarise the survey's runs: fuel and outcomes per label, collection errors, failures by
their one-line reason per family and tier, and any module loaded from the stage outside a test
folder. Writes build/095/survey/summary.md and failures.txt."""

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

SURVEY = Path.cwd() / "build/095/survey"
rows, fails, xerr, mods = [], defaultdict(Counter), [], []
members = defaultdict(list)
for res in sorted((SURVEY / "out").glob("*/result.json")):
    lab = res.parent.name
    # not tier rows: the stage's derived runs, collections, the start-cost probes, and the two
    # signal runs the timed test stopped (sci-n-signal-3 replaces them; sci-n-conv-method is
    # that test alone)
    if lab.startswith(("derived-", "kw-co", "sm-co", "sm-pp", "sci-pp")) or lab in (
        "sci-n-signal", "sci-n-signal-2", "sci-n-conv-method"):
        continue
    r = json.loads(res.read_text())
    rows.append(r)
    tier = "release" if lab.startswith("sci-r") else "normal"
    stream = res.parent / "stream.txt"
    if not stream.exists():
        continue
    for line in stream.read_text().splitlines():
        if line.startswith("R failed ") or line.startswith("R error "):
            _, outcome, node, *rest = line.split(" ", 3)
            reason = rest[0].removeprefix("-- ") if rest else ""
            key = re.sub(r"0x[0-9a-f]+|\d+(\.\d+)?", "#", reason)[:110]
            fails[(r["family"], tier)][key] += 1
            members[(r["family"], tier, key)].append(node)
        elif line.startswith("X "):
            xerr.append(f"{lab}: {line[2:][:230]}")
        elif (line.startswith("M ") and "/tests/" not in line
              and not line.split()[1].endswith(".conftest")):
            mods.append(f"{lab}: {line}")

out = ["| label | fuel G | exit | trap | passed | failed | error | skipped | xfailed | xpassed |",
       "|---|---|---|---|---|---|---|---|---|---|"]
tot = Counter()
for r in rows:
    c = r["counts"]
    tier = "release" if r["label"].startswith("sci-r") else "normal"
    tot[(r["family"], tier, "fuel")] += r["fuel"]
    for k in ("passed", "failed", "error", "skipped", "xfailed", "xpassed"):
        tot[(r["family"], tier, k)] += c.get(k, 0)
    out.append(f"| {r['label']} | {r['fuel'] / 1e9:.1f} | {r['exit']} | {r['trapped'] or ''} | "
               + " | ".join(str(c.get(k, 0)) for k in
                            ("passed", "failed", "error", "skipped", "xfailed", "xpassed")) + " |")
out += ["", "| family | tier | fuel T | passed | failed | error | skipped |", "|---|---|---|---|---|---|---|"]
for fam in ("scipy", "scikit-learn", "statsmodels"):
    for tier in ("normal", "release"):
        if tot[(fam, tier, "fuel")]:
            out.append(f"| {fam} | {tier} | {tot[(fam, tier, 'fuel')] / 1e12:.3f} | "
                       + " | ".join(str(tot[(fam, tier, k)]) for k in
                                    ("passed", "failed", "error", "skipped")) + " |")
out += ["", "## Collection errors", *xerr, "", "## Modules from the stage outside tests", *mods]
(SURVEY / "summary.md").write_text("\n".join(out) + "\n")
with (SURVEY / "failures.txt").open("w") as fh:
    for (fam, tier), cnt in sorted(fails.items()):
        fh.write(f"== {fam} {tier}: {sum(cnt.values())}\n")
        for k, v in cnt.most_common():
            fh.write(f"  {v:5d}  {k}\n")
            for n in members[(fam, tier, k)][:3]:
                fh.write(f"           {n[:160]}\n")
print("\n".join(out[-12:]))
