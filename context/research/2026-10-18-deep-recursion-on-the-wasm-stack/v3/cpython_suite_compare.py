"""Spec 071 criterion 6: per-module passes on the built set against the CPython-suite memo's."""
import csv, json, sys
from pathlib import Path
MEMO = Path("context/research/2026-10-18-cpythons-own-tests-under-the-runtime/per-module-results.tsv")
RUNS = Path("build/cpy071/runs")
memo = {r["module"]: r for r in csv.DictReader(MEMO.open(), delimiter="\t")}
tot_memo = tot_now = 0
lost, gained, traps = [], [], []
for m, r in memo.items():
    p = RUNS / f"{m}.json"
    if not p.exists():
        lost.append((m, "not run")); continue
    rec = json.loads(p.read_text())
    now = rec.get("counts", {}).get("passed", 0)
    was = int(r["passed"])
    tot_memo += was; tot_now += now
    if rec.get("trapped") or rec.get("hang"):
        traps.append((m, rec.get("trapped") or "hang", was, now))
    if now < was:
        lost.append((m, f"{was} -> {now}", rec.get("trapped")))
    elif now > was:
        gained.append((m, f"{was} -> {now}"))
print("passes: memo", tot_memo, "built set", tot_now)
print("modules that lost passes:", len(lost)); [print("  LOST", *x) for x in lost]
print("modules that gained passes:", len(gained)); [print("  GAINED", *x) for x in gained]
print("modules that trapped or hung:", len(traps)); [print("  TRAP", *x) for x in traps]
