"""Summarise the survey: per session fuel and outcomes; per family totals; failure reasons;
collection errors; per-file outcome counts (to choose smoke files).

    uv run --no-project python -I analyze.py <survey dir> [sessions|reasons|files <label>|errors]
"""

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

S = Path(sys.argv[1])
what = sys.argv[2] if len(sys.argv) > 2 else "sessions"
jobs = {}
for line in (S / "jobs.jsonl").read_text().splitlines():
    j = json.loads(line)
    jobs[j["label"]] = j  # the last run of a label wins


def stream(label):
    p = S / "out" / label / "stream.txt"
    return p.read_text(errors="replace").splitlines() if p.is_file() else []


def norm(reason: str) -> str:
    r = re.sub(r"0x[0-9a-f]+", "0x…", reason)
    r = re.sub(r"\d+", "#", r)
    return r[:110]


if what == "sessions":
    fam_tot = defaultdict(lambda: [0, Counter()])
    for lab, j in jobs.items():
        c = j["counts"]
        print(f"{lab:28} {j['fuel'] / 1e9:9.1f} G exit={j['exit']} trap={j['trap']} "
              + " ".join(f"{k}={v}" for k, v in sorted(c.items())))
        fam_tot[j["family"]][0] += j["fuel"]
        fam_tot[j["family"]][1].update(c)
    print()
    tot = 0
    for fam, (fuel, c) in sorted(fam_tot.items(), key=lambda x: -x[1][0]):
        tot += fuel
        print(f"{fam:20} {fuel / 1e9:9.1f} G passed={c['passed']} failed={c['failed']} "
              f"error={c['error']} skipped={c['skipped']} X={c['collect-error']}")
    print(f"TOTAL {tot / 1e12:.2f} T in {len(jobs)} sessions")
elif what == "reasons":
    for lab in jobs:
        reasons = Counter()
        for line in stream(lab):
            m = re.match(r"R (failed|error) (\S+) -- (.*)", line)
            if m:
                reasons[norm(m.group(3))] += 1
        if reasons:
            print(f"== {lab}")
            for r, n in reasons.most_common(12):
                print(f"   {n:5} {r}")
elif what == "errors":
    for lab in jobs:
        xs = [line for line in stream(lab) if line.startswith("X ")]
        if xs:
            print(f"== {lab} ({len(xs)})")
            for x in xs[:25]:
                print("  ", x[:220])
elif what == "files":
    for lab in sys.argv[3:]:
        print(f"== {lab}")
        per = defaultdict(Counter)
        for line in stream(lab):
            m = re.match(r"R (\w+) (\S+)", line)
            if m:
                per[m.group(2).split("::")[0]][m.group(1)] += 1
        for f, c in sorted(per.items()):
            print(f"  {f[:66]:66} " + " ".join(f"{k}={v}" for k, v in sorted(c.items())))
