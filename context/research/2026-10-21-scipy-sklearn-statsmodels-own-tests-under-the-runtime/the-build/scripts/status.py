"""Where the build stands: groups per family and tier, measured fuel, unmeasured and over-bound
release groups (from the TOMLs and measured.json)."""

import json
import tomllib
from pathlib import Path

SP = Path(__file__).parent
W = Path("/Users/claygendron/Git/Repos/wasi_python/.claude/worktrees/agent-aab0b516adb4e5c06")
measured = json.loads((SP / "measured.json").read_text())
tot = {"normal": 0, "release": 0}
for fam in ("scipy", "scikit-learn", "statsmodels"):
    g = tomllib.loads((W / f"tests/upstream/{fam}.toml").read_text())["groups"]
    rel = [n for n, v in g.items() if v.get("tier") == "release"]
    norm = [n for n in g if n not in rel]
    m = sum(measured.get(n, 0) for n in rel)
    un = [n for n in rel if n not in measured]
    over = [(n, round(measured[n] / 1e9)) for n in rel if measured.get(n, 0) > 480e9]
    tot["release"] += m
    tot["normal"] += sum(measured.get(n, 0) for n in norm)
    print(f"{fam}: {len(norm)} normal, {len(rel)} release; measured release {m / 1e12:.2f} T; "
          f"unmeasured {len(un)}; over 480 G {len(over)}")
    print("   unmeasured:", " ".join(un))
    print("   over:", over)
print({k: round(v / 1e12, 2) for k, v in tot.items()})
