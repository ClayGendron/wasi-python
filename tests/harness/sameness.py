"""Whether two run records give the same answer (spec 052, Decision 12).

`differences(a, b)` lists every difference between two `latest.json` records in what a verdict is
made of: each check's `status`, `need`, `area`, `closer`, `facts`, the names of its metrics, its
`bytes` and `passes`; its `reason` where both records call it `gap` or `blocked` (there the
reason is deterministic: a gap's first line, a need); its `fuel` where the two differ
by more than the ratchet's tolerance, `abs(a - b) > FUEL_TOLERANCE * max(a, b)`, and so too each
value of its `fuel_facts` fact (spec 091: fuel recorded, never ratcheted); and the run's
`deselected`, `collected_files`, `suite` and `meta.foreign` (what steered the run from outside
the judge, which makes it red). A failure's reason is not compared: it may name a
temporary path, and the statuses already decide. A pass's reason, its note, is not compared
either: the plugin never compares a note, and one may print a fuel count, which carries the
residual serial runs show (spec 035's zone-load check: 17 instructions in 8.7 million between a
serial and a parallel run, the build's evidence). The rest of `meta` is never compared.

    uv run python tests/harness/sameness.py A.json B.json

prints the differences, one per line, and exits 1 when there are any.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ in (None, ""):  # run as a script: the harness package lives one folder up
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness.scoreboard import FUEL_TOLERANCE  # noqa: E402

FIELDS = ("status", "need", "area", "closer")
FUEL_FACTS = "fuel_facts"  # a fact of fuel values, compared as fuel is (spec 091)
EXACT_METRICS = ("bytes", "passes")
REASONED = ("gap", "blocked")
RUN_FIELDS = ("deselected", "collected_files", "suite")


def fuel_differs(a: int, b: int) -> bool:
    return abs(a - b) > FUEL_TOLERANCE * max(a, b)


def _facts(record: dict) -> tuple[object, dict]:
    """(the facts compared exactly, the fuel facts compared within the tolerance)."""
    facts = record.get("facts")
    if not isinstance(facts, dict) or FUEL_FACTS not in facts:
        return facts, {}
    return {k: v for k, v in facts.items() if k != FUEL_FACTS}, facts[FUEL_FACTS] or {}


def _check(node: str, a: dict, b: dict) -> list[str]:
    found = [
        f"{node}: {field} {a.get(field)!r} != {b.get(field)!r}"
        for field in FIELDS
        if a.get(field) != b.get(field)
    ]
    (fa, xa), (fb, xb) = _facts(a), _facts(b)
    if fa != fb:
        found.append(f"{node}: facts {fa!r} != {fb!r}")
    if set(xa) != set(xb):
        found.append(f"{node}: {FUEL_FACTS} {sorted(xa)} != {sorted(xb)}")
    for name in sorted(set(xa) & set(xb)):
        if fuel_differs(xa[name], xb[name]):
            found.append(
                f"{node}: {FUEL_FACTS} {name} {xa[name]} != {xb[name]} (beyond {FUEL_TOLERANCE})"
            )
    if a.get("status") == b.get("status") in REASONED and a.get("reason") != b.get("reason"):
        found.append(f"{node}: reason {a.get('reason')!r} != {b.get('reason')!r}")
    ma, mb = a.get("metrics") or {}, b.get("metrics") or {}
    if set(ma) != set(mb):
        found.append(f"{node}: metrics {sorted(ma)} != {sorted(mb)}")
    for name in EXACT_METRICS:
        if name in ma and name in mb and ma[name] != mb[name]:
            found.append(f"{node}: {name} {ma[name]} != {mb[name]}")
    if "fuel" in ma and "fuel" in mb and fuel_differs(ma["fuel"], mb["fuel"]):
        found.append(f"{node}: fuel {ma['fuel']} != {mb['fuel']} (beyond {FUEL_TOLERANCE})")
    return found


def differences(a: dict, b: dict) -> list[str]:
    """Every difference between two run records that could change a verdict."""
    found: list[str] = []
    ca, cb = a.get("checks", {}), b.get("checks", {})
    for node in sorted(set(ca) | set(cb)):
        if node not in cb:
            found.append(f"{node}: only in the first record")
        elif node not in ca:
            found.append(f"{node}: only in the second record")
        else:
            found += _check(node, ca[node], cb[node])
    for field in RUN_FIELDS:
        if a.get(field) != b.get(field):
            found.append(f"{field}: {a.get(field)!r} != {b.get(field)!r}")
    fa, fb = (r.get("meta", {}).get("foreign") or [] for r in (a, b))
    if sorted(fa) != sorted(fb):  # the one meta field that decides a verdict (build review, F2)
        found.append(f"meta.foreign: {fa!r} != {fb!r}")
    return found


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: sameness.py A.json B.json", file=sys.stderr)
        return 2
    a, b = (json.loads(Path(p).read_text()) for p in argv)
    found = differences(a, b)
    for line in found:
        print(line)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
