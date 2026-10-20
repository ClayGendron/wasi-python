"""v1.3: numpy's, pandas' and CPython's own tests pass inside the guest (specs 050 and 065).

One check per group runs upstream's own selection in the snapshot binary, from the artifact's own
pinned sources, and passes only when every failure falls in a known class. Each class, each test
that traps the guest, and each of CPython's deselection, environment and host entries is its own
check, admitted as an ordinary gap with its closer. The groups record `fuel` and `passes`, which
must not fall. A fuel fact's test (spec 091) runs in a session of its own inside its group's
check: its outcomes count with the group's, and its fuel is a fact, not part of the group's
`fuel`.
"""

from __future__ import annotations

import pytest

from harness import needs, plugin, regrtest, scan, upstream

pytestmark = pytest.mark.goal("v1.3")

CONFIGS = upstream.load_all()
GROUPS = [(c.package, g) for c in CONFIGS.values() for g in c.groups]
CLASSES = [(c.package, k) for c in CONFIGS.values() for k in c.expected]
TRAPS = [(c.package, t.id) for c in CONFIGS.values() for t in c.traps]
DESELECTED = [(c.package, d) for c in CONFIGS.values() for d in c.deselected]
ENVIRONMENT = [(c.package, e) for c in CONFIGS.values() for e in c.environment]
HOSTS = [(c.package, h) for c in CONFIGS.values() for h in c.host_dependent]


@pytest.fixture(scope="session")
def upstream_session(guest_workdir):
    s = upstream.Session(guest_workdir, CONFIGS)
    yield s
    s.close()


@pytest.fixture(scope="session")
def regrtest_session(guest_workdir):
    s = regrtest.Session(guest_workdir, CONFIGS)
    yield s
    s.close()


def _need(package: str) -> None:
    cfg = CONFIGS[package]
    if cfg.runner == "regrtest":
        needs.need(
            "artifact dir",
            "snapshot binary",
            "stdlib zip",
            "manifest",
            "wasmtime-py",
            f"source tree {cfg.component}",
        )
        return
    needs.need(
        "artifact dir",
        "snapshot binary",
        "stdlib zip",
        "manifest",
        "wasmtime-py",
        f"source tree {package}",
        "upstream kit",
    )


def _session(package, upstream_session, regrtest_session):
    return regrtest_session if CONFIGS[package].runner == "regrtest" else upstream_session


@pytest.mark.slow
@pytest.mark.parametrize(("package", "group"), GROUPS, ids=[g for _, g in GROUPS])
def test_upstream_suite(upstream_session, regrtest_session, metric, fact, package, group) -> None:
    """Every failure or error falls in a class of the group; nothing traps, runs out of fuel,
    fails to collect or load, or ends abnormally; no product module comes from the grant. numpy's
    and pandas' hypothesis profile is derandomized; CPython's modules are exactly the plan's, and
    each environment change is one an entry names. A fuel fact's cases ran exactly once, in their
    own session, within its cap."""
    _need(package)
    run = _session(package, upstream_session, regrtest_session).group(package, group)
    fact("counts", run.outcome.counts)
    fact("passed_digest", run.outcome.passed_digest)
    fact("left_out", run.left_out)
    if CONFIGS[package].runner == "regrtest":
        fact("states", run.outcome.states)
        fact("env_altered", run.outcome.env_altered)
        if run.outcome.findings:  # every finding in the record, not only the message's first five
            fact("findings", run.outcome.findings)
    elif run.fuel_facts:  # recorded, never ratcheted (spec 091)
        fact("fuel_facts", run.fuel_facts)
    metric("fuel", run.fuel)
    metric("passes", run.outcome.passes)
    assert not run.outcome.findings, scan.report(run.outcome.findings, f"upstream {group}")


@pytest.mark.slow
@pytest.mark.parametrize(
    ("package", "klass"), CLASSES, ids=[f"{k.group}-{k.id}" for _, k in CLASSES]
)
def test_upstream_class(upstream_session, regrtest_session, package, klass) -> None:
    """The class's members are exactly its list, by node id: one finding each while the class has
    members, and `+id`/`-id` for each test admitted or released without an edit to the list."""
    _need(package)
    run = _session(package, upstream_session, regrtest_session).group(package, klass.group)
    findings = upstream.class_findings(
        run.outcome.members[klass.id], upstream.read_list(upstream.list_path(klass))
    )
    if not run.outcome.finished:
        findings.append(f"group {klass.group} did not finish")
    assert not findings, scan.report(findings, f"class {klass.group}-{klass.id}")


if TRAPS:  # an empty parametrization would be a skip that names no need, so a failure

    @pytest.mark.slow
    @pytest.mark.parametrize(("package", "trap"), TRAPS, ids=[t for _, t in TRAPS])
    def test_upstream_trap(upstream_session, regrtest_session, metric, fact, package, trap) -> None:
        """The entry, run alone in its own session, completes without a trap. A CPython entry,
        while open: the named trap, or no trap, on every host (spec 065, Decision 1)."""
        _need(package)
        if CONFIGS[package].runner == "regrtest":
            verdict = regrtest_session.trap(package, trap)
            metric("fuel", verdict.fuel)
            fact("trap", verdict.seen)
            fact("counts", verdict.counts)
            assert not verdict.findings, scan.report(verdict.findings, f"trap {trap}")
            return
        run = upstream_session.trap(package, trap)
        metric("fuel", run.fuel)
        assert not run.findings, scan.report(run.findings, f"trap {trap}")


if DESELECTED:

    @pytest.mark.slow
    @pytest.mark.parametrize(
        ("package", "entry"), DESELECTED, ids=[f"{d.group}-{d.id}" for _, d in DESELECTED]
    )
    def test_upstream_deselected(regrtest_session, package, entry) -> None:
        """The tests a deselection entry keeps from running, one finding each, on the scoreboard
        under its closer; red if one of them ran (spec 065, Decision 21)."""
        _need(package)
        run = regrtest_session.group(package, entry.group)
        findings = [f"deselected: {i}" for i in entry.tests]
        findings += [
            f"a deselected test ran: {i}" for i in run.outcome.deselected_ran if i in entry.tests
        ]
        if not run.outcome.finished:
            findings.append(f"group {entry.group} did not finish")
        assert not findings, scan.report(findings, f"deselected {entry.group}-{entry.id}")


if ENVIRONMENT:

    @pytest.mark.slow
    @pytest.mark.parametrize(
        ("package", "entry"), ENVIRONMENT, ids=[f"{e.group}-{e.id}" for _, e in ENVIRONMENT]
    )
    def test_upstream_environment(regrtest_session, package, entry) -> None:
        """The modules that altered the environment in only the entry's kinds of change, exactly
        its list: one finding each, `+module`/`-module` for a change (spec 065, Decision 21)."""
        _need(package)
        run = regrtest_session.group(package, entry.group)
        findings = regrtest.environment_findings(run.outcome.environment[entry.id], entry.modules)
        if not run.outcome.finished:
            findings.append(f"group {entry.group} did not finish")
        assert not findings, scan.report(findings, f"environment {entry.group}-{entry.id}")


if HOSTS:

    @pytest.mark.slow
    @pytest.mark.parametrize(
        ("package", "entry"), HOSTS, ids=[f"{h.group}-{h.id}" for _, h in HOSTS]
    )
    def test_upstream_host(regrtest_session, fact, package, entry) -> None:
        """A result recorded per system: one constant finding on the scoreboard, red if this
        system did otherwise (spec 065, Decision 21)."""
        _need(package)
        run = regrtest_session.group(package, entry.group)
        seen = run.outcome.host_seen.get(entry.id, {})
        fact("seen", seen)
        results = " ".join(f"{s}={entry.results.get(s, '-')}" for s in regrtest.SYSTEMS)
        findings = [f"host entry {entry.id}: {results}"]
        here = regrtest.system()
        if seen.get("result") != entry.results.get(here):
            findings.append(f"on {here}: {seen.get('result')}")
        assert not findings, scan.report(findings, f"host {entry.group}-{entry.id}")


@pytest.mark.goal("rules")
def test_upstream_files_are_well_formed() -> None:
    """The kit's lines; every closer exists; every class has a sorted list file, with exactly one
    gap while it has members and none when empty; every trap and entry has its gap; names are
    unique; the groups' paths and the named files are tarball members (when the tarballs are
    here); CPython's plan places every module once, in order, with its trap, deselected and host
    ids resolving in the tarball's source; each family's caps are within its budget."""
    from harness import pins, shards

    gaps, _ = plugin.load_gaps(upstream.paths.KNOWN_GAPS)
    members: dict[str, set[str]] = {}
    sources: dict[str, dict[str, str]] = {}
    for package, cfg in CONFIGS.items():
        pair = pins.source_pair(cfg.component or package)
        if pair is None:
            continue
        if cfg.runner == "regrtest":
            got = regrtest.tarball_sources(pair[0])
            members[package], sources[package] = set(got), got
        else:
            members[package] = upstream.tarball_members(pair[0])
    errors = upstream.rule_errors(
        CONFIGS, set(gaps), members=members, sources=sources, systems_of=shards.group_systems()
    )
    assert not errors, scan.report(errors, "upstream files")
