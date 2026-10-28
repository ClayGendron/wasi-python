"""lint: the fast tier's fuel budget, read from the acceptance.

Each normal-tier goal check's accepted fuel is held to its family's cap in `tests/lint/budget.toml`.
The gather holds each pull request's own fuel and the acceptance from CI's record refuses a check
past its cap, so this is the backstop for a cap or an `[[over]]` entry edited by hand. A check over
budget fails here until the file lists the specification that will move it to the slow normal tier
or the release tier; a listed one is reported as a warning naming it. The quick job's times are
reported by `tests/harness/budget.py --times`, as warnings only: a duration depends on its host.
"""

from __future__ import annotations

import json
import warnings

from harness import budget, paths, scan


def test_no_normal_tier_check_is_past_its_familys_fuel_cap() -> None:
    plan = budget.load()
    accepted = json.loads((paths.PROGRESS / "accepted.json").read_text(encoding="utf-8"))
    upstream = budget.upstream_families()

    def family(node: str) -> str:
        return budget.family_of(node, upstream)

    over = budget.fuel_over(accepted, plan.caps, family)
    files = [f"{budget.GOAL_DIR}{p.name}" for p in (paths.REPO / budget.GOAL_DIR).glob("test_*.py")]
    stale = budget.stale_caps(accepted, plan.caps, family, budget.new_families(accepted, files))
    assert not stale, scan.report(stale)
    specs = budget.spec_status(paths.CONTEXT / "specifications")
    bad, reported = budget.findings(over, plan, specs)
    for line in reported:
        warnings.warn(f"budget: {line}", stacklevel=1)
    assert not bad, scan.report(bad)
