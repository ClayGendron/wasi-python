"""Count the survey's skips by reason per family (normal tier), and the skips that name a mode's
variable, for the README's numbers."""

import re
from collections import Counter, defaultdict
from pathlib import Path

SURVEY = Path.cwd() / "build/095/survey"
FAM = {"sci-n": "scipy", "skl-n": "scikit-learn", "sm-n": "statsmodels"}
DROP = {"sci-n-signal", "sci-n-signal-2", "sci-n-conv-method"}
skips = defaultdict(Counter)
for s in sorted((SURVEY / "out").glob("*/stream.txt")):
    lab = s.parent.name
    fam = next((v for k, v in FAM.items() if lab.startswith(k + "-")), None)
    if fam is None or lab in DROP:
        continue
    for line in s.read_text().splitlines():
        if line.startswith("R skipped "):
            reason = line.split(" -- ", 1)[1] if " -- " in line else ""
            skips[fam][re.sub(r"\d+", "#", reason)[:100]] += 1
MODES = ("SCIPY_ARRAY_API", "SKLEARN_", "SM_", "SCIPY_XFAIL", "torch", "array_api_strict",
         "dpnp", "cupy", "jax")
for fam, c in skips.items():
    print(f"== {fam}: {sum(c.values())} skips")
    for k, v in c.most_common(12):
        print(f"  {v:6d}  {k}")
    mode = sum(v for k, v in c.items() if any(m in k for m in MODES))
    print(f"  mode or backend skips: {mode}")
