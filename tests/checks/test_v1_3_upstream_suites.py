"""v1.3: numpy's and pandas' own tests pass inside the guest (spec 050).

One check per group runs upstream's fast selection in the snapshot binary, from the artifact's
own pinned source trees, and passes only when every failure falls in a known class. Each class
and each test that traps the guest is its own check, admitted as an ordinary gap with its closer.
The groups record `fuel` and `passes`, which must not fall.
"""

from __future__ import annotations

import pytest

from harness import needs, plugin, scan, upstream

pytestmark = pytest.mark.goal("v1.3")

CONFIGS = upstream.load_all()
GROUPS = [(c.package, g) for c in CONFIGS.values() for g in c.groups]
CLASSES = [(c.package, k) for c in CONFIGS.values() for k in c.expected]
TRAPS = [(c.package, t.id) for c in CONFIGS.values() for t in c.traps]


@pytest.fixture(scope="session")
def upstream_session(guest_workdir):
    s = upstream.Session(guest_workdir, CONFIGS)
    yield s
    s.close()


def _need(package: str) -> None:
    needs.need(
        "artifact dir",
        "snapshot binary",
        "stdlib zip",
        "manifest",
        "wasmtime-py",
        f"source tree {package}",
        "upstream kit",
    )


@pytest.mark.slow
@pytest.mark.parametrize(("package", "group"), GROUPS, ids=[g for _, g in GROUPS])
def test_upstream_suite(upstream_session, metric, fact, package, group) -> None:
    """Every failure or error falls in a class of the group; nothing traps, runs out of fuel,
    fails to collect or ends abnormally; the hypothesis profile is derandomized; no product
    module comes from the grant."""
    _need(package)
    run = upstream_session.group(package, group)
    fact("counts", run.outcome.counts)
    fact("passed_digest", run.outcome.passed_digest)
    fact("left_out", run.left_out)
    metric("fuel", run.fuel)
    metric("passes", run.outcome.passes)
    assert not run.outcome.findings, scan.report(run.outcome.findings, f"upstream {group}")


@pytest.mark.slow
@pytest.mark.parametrize(
    ("package", "klass"), CLASSES, ids=[f"{k.group}-{k.id}" for _, k in CLASSES]
)
def test_upstream_class(upstream_session, package, klass) -> None:
    """The class's members are exactly its list, by node id: one finding each while the class has
    members, and `+id`/`-id` for each test admitted or released without an edit to the list."""
    _need(package)
    run = upstream_session.group(package, klass.group)
    findings = upstream.class_findings(
        run.outcome.members[klass.id], upstream.read_list(upstream.list_path(klass))
    )
    if not run.outcome.finished:
        findings.append(f"group {klass.group} did not finish")
    assert not findings, scan.report(findings, f"class {klass.group}-{klass.id}")


@pytest.mark.slow
@pytest.mark.parametrize(("package", "trap"), TRAPS, ids=[t for _, t in TRAPS])
def test_upstream_trap(upstream_session, metric, package, trap) -> None:
    """The entry, run alone in its own session, completes without a trap."""
    _need(package)
    run = upstream_session.trap(package, trap)
    metric("fuel", run.fuel)
    assert not run.findings, scan.report(run.findings, f"trap {trap}")


@pytest.mark.goal("rules")
def test_upstream_files_are_well_formed() -> None:
    """The kit's lines; every closer exists; every class has a sorted list file, with exactly one
    gap while it has members and none when empty; every trap has its gap; names are unique; the
    groups' paths and the named files are tarball members (when the trees are here); the caps
    sum to at most 3×10¹²."""
    from harness import pins

    gaps, _ = plugin.load_gaps(upstream.paths.KNOWN_GAPS)
    members = {}
    for package in CONFIGS:
        pair = pins.source_pair(package)
        if pair is not None:
            members[package] = upstream.tarball_members(pair[0])
    errors = upstream.rule_errors(CONFIGS, set(gaps), members=members)
    assert not errors, scan.report(errors, "upstream files")
