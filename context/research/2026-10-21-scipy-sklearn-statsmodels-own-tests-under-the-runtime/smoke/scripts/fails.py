"""Failure and error reasons, counted, for the probes named (label prefixes).

    uv run python build/095b/survey/fails.py <prefix>...
"""

import collections
import sys
from pathlib import Path

S = Path.cwd() / "build/095b/survey/out"
for d in sorted(S.iterdir()):
    if not any(d.name.startswith(p) for p in sys.argv[1:]) or not (d / "stream.txt").exists():
        continue
    c = collections.Counter()
    for line in (d / "stream.txt").read_text().splitlines():
        parts = line.split(" ", 2)
        if parts[0] == "R" and parts[1] in ("failed", "error"):
            reason = parts[2].split(" -- ", 1)[-1][:100]
            c[(parts[1], reason)] += 1
        elif parts[0] == "X":
            c[("collect", parts[-1][:100])] += 1
    if c:
        print("==", d.name)
        for (k, r), n in c.most_common():
            print(f"  {n:4} {k} {r}")
