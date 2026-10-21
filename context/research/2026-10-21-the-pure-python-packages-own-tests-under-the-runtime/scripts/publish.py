"""Copy the survey's evidence (text outputs, job lists, scripts) into the research folder.

    uv run --no-project python -I publish.py <scratch 067> <research folder> <survey dir>
"""

import shutil
import subprocess
import sys
from pathlib import Path

scratch, research, survey = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
(research / "scripts").mkdir(parents=True, exist_ok=True)
py = [sys.executable, "-I"]
for what, name in [("sessions", "sessions.txt"), ("reasons", "reasons.txt"),
                   ("errors", "collection-errors.txt")]:
    out = subprocess.run([*py, str(scratch / "scripts/analyze.py"), survey, what],
                         capture_output=True, text=True, check=True).stdout
    (research / name).write_text(out)
out = subprocess.run([*py, str(scratch / "scripts/price.py"), survey],
                     capture_output=True, text=True, check=True).stdout
(research / "price.txt").write_text(out)
for s in ["survey.py", "families.py", "runjobs.py", "analyze.py", "price.py", "patsy_inline.py",
          "fetch.py", "unpack.py", "extras.py", "reset.py", "configs.py", "counts.py",
          "docfiles.py", "layout.py", "publish.py"]:
    shutil.copyfile(scratch / "scripts" / s, research / "scripts" / s)
jobs = []
for n in ["jobs-1.txt", "jobs-2b.txt", "jobs-2.txt", "jobs-5.txt", "jobs-6.txt", "jobs-7.txt",
          "jobs-8.txt"]:
    jobs.append(f"# ---- {n}\n" + (scratch / n).read_text())
(research / "jobs.txt").write_text("".join(jobs))
for n in ["sympy-docfiles.txt", "joblib-docfiles.txt", "configs.txt"]:
    shutil.copyfile(scratch / n, research / n)
print(sorted(p.name for p in research.rglob("*") if p.is_file()))
