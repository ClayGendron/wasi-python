"""Tabulate the runs: one row per module, the totals, and the failures by reason.

uv run python analyze.py <modules file> <out dir>

Writes <out>/per-module.tsv, <out>/failures.tsv (every failed or errored test with its reason),
<out>/module-outcomes.tsv (modules that did not end OK, with regrtest's own verdict line) and
prints the totals.
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

RUNS = Path("/Users/claygendron/Git/Repos/wasi_python/build/cpython-suite-research/runs")
KINDS = ("passed", "skipped", "failed", "error", "xfailed", "xpassed")


def verdict(label: str) -> str:
    """regrtest's per-module line: passed, failed, skipped, crashed, env changed, ..."""
    out = RUNS / f"{label}.out"
    if not out.exists():
        return ""
    for line in out.read_text(errors="replace").splitlines():
        m = re.match(r"^\d+:\d\d:\d\d \[1/1(?:/1)?\] \S+ (.*)$", line)
        if m:
            return m.group(1).strip()
    return ""


def status(rec: dict, v: str) -> str:
    if rec.get("hang"):
        return "hang"
    if rec.get("host_crash") is not None:
        return "host-crash"
    if rec.get("trapped") == "out of fuel":
        return "out-of-fuel"
    if rec.get("trapped"):
        return "trap"
    if "uncaught exception" in v or "crashed" in v:
        return "module-error"
    if v.startswith("skipped") or "skipped" in v and not rec.get("counts"):
        return "module-skipped"
    if "env changed" in v:
        return "env-changed"
    if v.startswith("failed") or rec.get("exit") not in (0, None):
        return "failed"
    if not rec.get("counts"):
        return "no-tests"
    return "ok"


def main() -> None:
    mods = [m.strip() for m in Path(sys.argv[1]).read_text().split() if m.strip()]
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    rows, fails, odd = [], [], []
    tot = Counter()
    st = Counter()
    fuel_all = 0
    wall_all = 0.0
    for m in mods:
        p = RUNS / f"{m}.json"
        if not p.exists():
            continue
        rec = json.loads(p.read_text())
        v = verdict(m)
        s = status(rec, v)
        st[s] += 1
        c = rec.get("counts") or {}
        for k in KINDS:
            tot[k] += c.get(k, 0)
        fuel = rec.get("fuel", 0)
        fuel_all += fuel
        wall_all += rec.get("wall_s") or 0
        rows.append(
            [m, s, *[str(c.get(k, 0)) for k in KINDS], f"{fuel / 1e9:.2f}", str(rec.get("wall_s", "")), v]
        )
        for o, name, reason in rec.get("cases", []):
            if o in ("failed", "error"):
                fails.append([m, o, name, " ".join(reason.split())[:300]])
        if s != "ok":
            tail = " | ".join(rec.get("stderr_tail") or [])
            odd.append([m, s, v, (rec.get("trap_cause") or rec.get("trapped") or ""), tail[:300]])
    head = ["module", "status", *KINDS, "fuel_G", "wall_s", "regrtest"]
    (out / "per-module.tsv").write_text(
        "\n".join("\t".join(r) for r in [head, *rows]) + "\n"
    )
    (out / "failures.tsv").write_text(
        "\n".join("\t".join(r) for r in [["module", "outcome", "test", "reason"], *fails]) + "\n"
    )
    (out / "module-outcomes.tsv").write_text(
        "\n".join("\t".join(r) for r in [["module", "status", "regrtest", "trap", "stderr"], *odd]) + "\n"
    )
    print(f"modules recorded: {len(rows)} of {len(mods)}")
    print("module status:", dict(st))
    print("tests:", dict(tot))
    print(f"fuel: {fuel_all / 1e9:.1f} G; wall (sum of sessions): {wall_all:.0f} s")


if __name__ == "__main__":
    main()
