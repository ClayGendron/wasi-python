"""scikit-learn's draft-group files one per session, to pick within the budget.

    uv run python build/095b/survey/mkjobs3.py
"""

import importlib.util
from pathlib import Path

S = Path.cwd() / "build/095b/survey"
spec = importlib.util.spec_from_file_location("mk", S / "mkjobs.py")
src = (S / "mkjobs.py").read_text()
ns: dict = {}
exec(compile(src.split("for path in SK_ALONE")[0].replace(
    'for path in (S / "files-scipy.txt").read_text().split():\n'
    '    lines.append("\\t".join(["scipy", label("sc", path), "150e9", M, path]))\n', ""),
    "mk", "exec"), ns)
lines = ["\t".join(["scikit-learn", ns["label"]("sk", p), "150e9", p])
         for p in ns["SK_A"] + ns["SK_B"]]
(S / "jobs-3.tsv").write_text("\n".join(lines) + "\n")
print(len(lines), "jobs")
