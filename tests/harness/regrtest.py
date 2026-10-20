"""CPython's own tests, run inside the guest by regrtest (spec 065).

The judge stages `Lib/test` from the pinned CPython tarball's members into its own read-only grant,
`/cpython`, and runs regrtest's own `main()` in the snapshot binary, one guest session per group.
The guest writes an outcome stream (`tests/upstream/regrtest_drive.py`); this module reads it,
sorts each failure into the class that admits it, each altered environment into the entry that
admits it, and names everything else as a finding. Classes, trap entries, the deselection, the
environment and host entries are each a check and an ordinary gap (spec 002); a group admits
nothing by itself. The configuration is `tests/upstream/python.toml`, loaded by `upstream.load`.
"""

from __future__ import annotations

import ast
import json
import re
import shutil
import sys
import tarfile
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from harness import litter, paths

GRANT = "/cpython"
STREAM = "judge/outcomes.txt"  # in the guest's root
DRIVER = "regrtest_drive.py"
CAP_BUDGET = 25 * 10**11
ENV = {"TMPDIR": "/tmp", "HOME": "/tmp"}
OUTCOMES = ("failed", "error")
FINE_STATES = ("PASSED", "FAILED", "SKIPPED", "RESOURCE_DENIED", "DID_NOT_RUN")
TEST_OUTCOMES = ("passed", "skipped", "failed", "error")
MODULE_RESULTS = (*FINE_STATES, "ENV_CHANGED", "load-error")
SYSTEMS = ("darwin", "linux", "win32")
STACK_TRAP = "call stack exhausted"


def system() -> str:
    """This host's system key, as 063's records name platforms."""
    return (
        "win32" if sys.platform == "win32" else ("darwin" if sys.platform == "darwin" else "linux")
    )


# ---------------------------------------------------------------------------------------------
# The configuration's own entries (Decision 21)


@dataclass(frozen=True)
class Deselected:
    id: str
    group: str
    tests: tuple[str, ...]
    reason: str
    closes_with: str


@dataclass(frozen=True)
class Environment:
    id: str
    group: str
    modules: tuple[str, ...]
    changes: tuple[str, ...]
    reason: str
    closes_with: str

    def admits(self, line: str) -> bool:
        """A recorded warning line is one of this entry's kinds: `<change> was modified by …`,
        the resource named exactly (the second confirmation's D1)."""
        return any(line.startswith(f"{c} was modified by ") for c in self.changes)


@dataclass(frozen=True)
class HostEntry:
    id: str
    group: str
    test: str  # a full test id, or ""
    module: str  # a module, or ""
    results: dict  # system -> outcome (test) or result (module)
    passes: dict  # system -> pass count (module entries)
    digests: dict  # system -> passed_digest (module entries)
    reason: str
    closes_with: str


def deselected_node(group: str, entry: str) -> str:
    return f"tests/checks/test_v1_3_upstream_suites.py::test_upstream_deselected[{group}-{entry}]"


def environment_node(group: str, entry: str) -> str:
    return f"tests/checks/test_v1_3_upstream_suites.py::test_upstream_environment[{group}-{entry}]"


def host_node(group: str, entry: str) -> str:
    return f"tests/checks/test_v1_3_upstream_suites.py::test_upstream_host[{group}-{entry}]"


def read_plan(directory: Path, rel: str) -> tuple[str, ...]:
    f = directory / rel
    if not f.is_file():
        return ()
    return tuple(line.strip() for line in f.read_text().splitlines() if line.strip())


def entries_from(raw: dict) -> tuple[list, list, list]:
    deselected = [
        Deselected(d["id"], d["group"], tuple(d["tests"]), d["reason"], d["closes_with"])
        for d in raw.get("deselected", [])
    ]
    environment = [
        Environment(
            e["id"],
            e["group"],
            tuple(e["modules"]),
            tuple(e["changes"]),
            e["reason"],
            e["closes_with"],
        )
        for e in raw.get("environment", [])
    ]
    hosts = []
    for h in raw.get("host_dependent", []):
        hosts.append(
            HostEntry(
                h["id"],
                h["group"],
                h.get("test", ""),
                h.get("module", ""),
                {s: h[s] for s in SYSTEMS if s in h},
                dict(h.get("passes", {})),
                dict(h.get("passed_digest", {})),
                h["reason"],
                h["closes_with"],
            )
        )
    return deselected, environment, hosts


def module_of_id(test_id: str, modules: set[str]) -> str | None:
    """The plan module a full test id lives in: the longest `test.<module>.` prefix."""
    best = None
    for m in modules:
        if test_id.startswith(f"test.{m}.") and (best is None or len(m) > len(best)):
            best = m
    return best


# ---------------------------------------------------------------------------------------------
# The argv: one JSON per group and trap entry (Decision 15)


def group_spec(cfg, group: str) -> dict:
    ignore = [t.test for t in cfg.traps if t.group == group and t.test]
    ignore += [i for d in cfg.deselected if d.group == group for i in d.tests]
    return {
        "modules": list(cfg.groups[group].modules),
        "ignore": ignore,
        "resources": cfg.resources,
        "options": list(cfg.options),
        "warnings": cfg.warnings,
    }


def trap_spec(cfg, trap) -> dict:
    """The entry alone: its module, matched to its one test (or the whole module)."""
    module = trap.module or module_of_id(trap.test, set(cfg.groups[trap.group].modules))
    return {
        "modules": [module],
        "match": [trap.test] if trap.test else [],
        "resources": cfg.resources,
        "options": list(cfg.options),
        "warnings": cfg.warnings,
    }


def guest_argv(name: str) -> list[str]:
    return ["-u", f"{GRANT}/judge/{DRIVER}", name]


def preopens(stage_root: Path) -> list[tuple[str, Path, bool]]:
    """A CPython group's one grant: its own stage, read-only, at /cpython (never /upstream)."""
    return [(GRANT, stage_root, False)]


# ---------------------------------------------------------------------------------------------
# The stage, from the verified tarball (Decision 15)

LIB_TEST = "Lib/test/"


def tarball_sources(tarball: Path) -> dict[str, str]:
    """Every regular file under `<top>/Lib/test/`, relative to `<top>/`: a `.py` file's text, any
    other file's empty string (the rules check: modules and test ids that exist)."""
    out: dict[str, str] = {}
    with tarfile.open(tarball) as t:
        for m in t:
            parts = m.name.split("/", 1)
            if len(parts) != 2 or not parts[1].startswith(LIB_TEST) or not m.isfile():
                continue
            text = ""
            if parts[1].endswith(".py"):
                src = t.extractfile(m)
                text = src.read().decode("utf-8", errors="replace") if src else ""
            out[parts[1]] = text
    return out


def stage(tarball: Path, tree: Path | None, dest: Path) -> list[str]:
    """Write every `Lib/test` member of `tarball`, read from the tarball itself, to
    `dest/lib/test/…`. Returns the tree's files under `Lib/test` that are not members (a warning:
    what a build left there, never staged), but for litter and bytecode (spec 090)."""
    names: set[str] = set()
    with tarfile.open(tarball) as t:
        for m in t:
            parts = m.name.split("/", 1)
            if len(parts) != 2 or not parts[1].startswith(LIB_TEST) or not m.isfile():
                continue
            rel = parts[1]
            if rel.startswith("/") or ".." in rel.split("/"):
                raise ValueError(f"{tarball.name}: member {m.name!r} refused (outside its folder)")
            src = t.extractfile(m)
            assert src is not None
            litter.refuse(rel, tarball.name)  # the seal's cleanup must never meet it (spec 089)
            target = dest / "lib" / rel[len("Lib/") :]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(src.read())
            names.add(rel)
    left_out: list[str] = []
    if tree is not None and (tree / LIB_TEST).is_dir():
        for p in sorted((tree / LIB_TEST).rglob("*")):
            if p.is_file():
                rel = p.relative_to(tree).as_posix()
                if rel not in names and not litter.unrecorded(rel):  # spec 090, Decision 5
                    left_out.append(rel)
    return left_out


# ---------------------------------------------------------------------------------------------
# The stream (Decision 13)


@dataclass
class Stream:
    listed: list[str] = field(default_factory=list)
    outcomes: list[tuple[str, str, str]] = field(default_factory=list)  # (outcome, id, reason)
    started: list[str] = field(default_factory=list)  # every S id, in order
    modules_started: list[str] = field(default_factory=list)
    load_errors: list[tuple[str, str]] = field(default_factory=list)
    ended: list[tuple[str, str, str, list[str]]] = field(default_factory=list)  # D lines
    guard: list[tuple[str, str, str]] = field(default_factory=list)  # M lines
    exit_code: int | None = None
    open_node: str | None = None  # the last S or C line
    module_of: dict[str, str] = field(default_factory=dict)  # test id -> its module


def parse_stream(text: str) -> Stream:
    s = Stream()
    module = None
    for line in text.splitlines():
        kind, _, rest = line.partition(" ")
        if kind == "L":
            s.listed.append(rest.strip())
        elif kind == "C":
            module = rest.strip()
            s.open_node = module
            s.modules_started.append(module)
        elif kind == "S":
            s.open_node = rest
            s.started.append(rest)
            if module is not None:
                s.module_of[rest] = module
        elif kind == "R":
            outcome, _, tail = rest.partition(" ")
            node, _, reason = tail.partition(" -- ")
            s.outcomes.append((outcome, node.strip(), reason.strip()))
            if module is not None:
                s.module_of.setdefault(node.strip(), module)
        elif kind == "X":
            name, _, reason = rest.partition(" -- ")
            s.load_errors.append((name.strip(), reason.strip()))
        elif kind == "D":
            parts = rest.split(" ", 3)
            name, state = parts[0], parts[1] if len(parts) > 1 else ""
            env = parts[2] if len(parts) > 2 else ""
            warns = parts[3].split("|") if len(parts) > 3 and parts[3] else []
            s.ended.append((name, state, env, warns))
        elif kind == "M":
            parts = rest.rsplit(" ", 2)
            if len(parts) == 3:
                s.guard.append((parts[0], parts[1], parts[2]))
        elif kind == "E":
            try:
                s.exit_code = int(rest)
            except ValueError:
                s.exit_code = -1
    return s


@dataclass(frozen=True)
class GuestRun:
    exit_code: int | None
    trapped: str | None
    cause: str | None
    fuel: int
    stderr_tail: str


@dataclass
class GroupOutcome:
    findings: list[str]
    members: dict[str, list[str]]  # class id -> ids
    environment: dict[str, list[str]]  # environment entry id -> modules that altered it
    deselected_ran: list[str]
    passes: int
    passed_digest: str
    counts: dict[str, int]
    states: dict[str, int]
    env_altered: list[str]
    host_seen: dict[str, dict]  # host entry id -> what this system did
    finished: bool


def passed_digest(nodes: list[str]) -> str:
    return paths.sha256_bytes("\n".join(sorted(nodes)).encode())[:12]


def ended_badly(stream: Stream, run: GuestRun) -> list[str]:
    """How the session ended, when it did not end normally. A trap names where it surfaced,
    not necessarily its cause."""
    where = stream.open_node if stream.open_node is not None else "start"
    if run.trapped == "out of fuel":
        return [f"out of fuel at or after {where}"]
    if run.trapped:
        return [f"trap: {run.cause or run.trapped} at or after {where}"]
    if stream.exit_code is None:
        return [f"no E line: the session did not finish (exit {run.exit_code}; {run.stderr_tail})"]
    return []


def universe(cfg) -> dict[str, str]:
    """Every module the plan places, and where: a group, not selected, or a whole-module trap."""
    where: dict[str, str] = {}
    for g in cfg.groups.values():
        for m in g.modules:
            where.setdefault(m, g.name)
    for n in cfg.not_selected:
        for m in n.modules:
            where.setdefault(m, "not selected")
    for t in cfg.traps:
        if t.module:
            where.setdefault(t.module, f"trap {t.id}")
    return where


def judge_group(stream: Stream, run: GuestRun, cfg, group: str, here: str) -> GroupOutcome:
    findings: list[str] = []
    classes = cfg.classes(group)
    members: dict[str, list[str]] = {k.id: [] for k in classes}
    compiled = [(k, re.compile(k.match)) for k in classes]
    hosts = [h for h in cfg.host_dependent if h.group == group]
    host_tests = {h.test: h for h in hosts if h.test}
    host_modules = {h.module: h for h in hosts if h.module}
    host_seen: dict[str, dict] = {h.id: {} for h in hosts}
    module_passes: dict[str, list[str]] = {m: [] for m in host_modules}

    passed: list[str] = []
    for outcome, node, reason in stream.outcomes:
        h = host_tests.get(node)
        if h is not None:
            host_seen[h.id]["result"] = outcome
            continue
        module = stream.module_of.get(node)
        if outcome == "passed":
            if module in host_modules:
                module_passes[module].append(node)
            else:
                passed.append(node)
            continue
        if outcome == "xpassed":
            outcome, reason = "failed", reason or "unexpected success"
        if outcome not in OUTCOMES:
            continue  # skipped, xfailed: upstream's own outcomes
        k = next((k for k, rx in compiled if k.outcome == outcome and rx.search(reason)), None)
        if k is not None:
            members[k.id].append(node)
        else:
            findings.append(f"unexpected {outcome} {node} — {reason}")
    for h in hosts:
        if h.test:
            want = h.results.get(here)
            got = host_seen[h.id].get("result", "absent")
            if want != got:
                findings.append(f"host entry {h.id}: {h.test} on {here} is {got}, recorded {want}")

    # each module's end: its state, and its environment
    environment: dict[str, list[str]] = {e.id: [] for e in cfg.environment if e.group == group}
    entry_of = {m: e for e in cfg.environment if e.group == group for m in e.modules}
    states: Counter = Counter()
    altered: list[str] = []
    for name, state, env, warns in stream.ended:
        states[state] += 1
        h = host_modules.get(name)
        if h is not None:
            host_seen[h.id]["result"] = state
        if state not in FINE_STATES and not (
            h is not None and state == h.results.get(here) == "ENV_CHANGED"
        ):
            findings.append(f"module {name} ended {state}")
        if env == "altered":
            altered.append(name)
            e = entry_of.get(name)
            if not warns:
                findings.append(f"module {name} altered the environment and printed no warning")
            elif e is None:
                findings.append(f"module {name} altered the environment: {' | '.join(warns)}")
            else:
                strangers = [w for w in warns if not e.admits(w)]
                if strangers:
                    findings.append(
                        f"module {name} altered the environment beyond {e.id}: "
                        f"{' | '.join(strangers)}"
                    )
                else:
                    environment[e.id].append(name)
    for name, reason in stream.load_errors:
        h = host_modules.get(name)
        if h is not None:
            host_seen[h.id]["result"] = "load-error"
            if h.results.get(here) == "load-error":
                continue
        findings.append(f"module {name} failed to load — {reason}")
    for h in hosts:
        if h.module:
            got = host_seen[h.id].get("result", "absent")
            if got != h.results.get(here):
                findings.append(f"host entry {h.id}: {h.module} on {here} is {got}")
            mine = module_passes[h.module]
            host_seen[h.id]["passes"] = len(mine)
            host_seen[h.id]["passed_digest"] = passed_digest(mine)
            if h.passes.get(here) is not None and h.passes.get(here) != len(mine):
                findings.append(f"host entry {h.id}: {len(mine)} passes on {here}")
            if h.digests.get(here) is not None and h.digests.get(here) != passed_digest(mine):
                findings.append(f"host entry {h.id}: passed digest {passed_digest(mine)} on {here}")

    bad = ended_badly(stream, run)
    findings += bad
    if not bad:
        if stream.exit_code not in (0, 2):
            findings.append(f"regrtest exit code {stream.exit_code}")
        if run.exit_code != 0:
            findings.append(f"guest exit {run.exit_code} after the E line")
        where = universe(cfg)
        listed = set(stream.listed)
        findings += [
            f"module {m} is in no group, not selected or trap" for m in sorted(listed - set(where))
        ]
        findings += [
            f"the plan names {m}, which regrtest does not list" for m in sorted(set(where) - listed)
        ]
    for name, f, kind in stream.guard:
        if kind == "product":
            findings.append(f"a product module came from the grant: {name} {f}")

    deselected = {i for d in cfg.deselected if d.group == group for i in d.tests}
    ran = sorted({n for n in stream.started if n in deselected})
    return GroupOutcome(
        findings=findings,
        members={k: sorted(set(v)) for k, v in members.items()},
        environment={k: sorted(set(v)) for k, v in environment.items()},
        deselected_ran=ran,
        passes=len(passed),
        passed_digest=passed_digest(passed),
        counts=dict(sorted(Counter(o for o, _, _ in stream.outcomes).items())),
        states=dict(sorted(states.items())),
        env_altered=sorted(altered),
        host_seen=host_seen,
        finished=not bad,
    )


def environment_findings(actual: list[str], listed: tuple[str, ...]) -> list[str]:
    """As a class: one finding per module that altered the environment, `+module` for one the
    entry does not name, `-module` for a named one that kept it; none when nothing altered."""
    if not actual:
        return []
    now, was = sorted(set(actual)), set(listed)
    return now + [f"+{m}" for m in now if m not in was] + [f"-{m}" for m in sorted(was - set(now))]


@dataclass
class TrapVerdict:
    findings: list[str]
    seen: str  # "trap at or after <id>", "no trap on this host", or how it ended otherwise
    counts: dict[str, int]
    fuel: int


def trap_verdict(stream: Stream, run: GuestRun, trap) -> TrapVerdict:
    """An open trap entry: one constant finding on every host, the named trap or no trap; red only
    for another cause, fuel, or a run that did not end as the entry allows (Decision 1)."""
    findings = [f"open trap entry: {trap.id}"]
    counts = dict(sorted(Counter(o for o, _, _ in stream.outcomes).items()))
    where = stream.open_node if stream.open_node is not None else "start"
    if run.trapped == "out of fuel":
        return TrapVerdict(
            findings + [f"out of fuel at or after {where}"], "out of fuel", counts, run.fuel
        )
    if run.trapped:
        cause = run.cause or run.trapped
        seen = f"trap at or after {where}"
        if STACK_TRAP not in cause:
            findings.append(f"trap by another cause: {cause} at or after {where}")
        return TrapVerdict(findings, seen, counts, run.fuel)
    seen = "no trap on this host"
    if stream.exit_code is None:
        findings.append(f"no E line: the session did not finish (exit {run.exit_code})")
    elif trap.module:
        if not any(name == trap.module for name, *_ in stream.ended):
            findings.append(f"no D line for {trap.module}: the module did not run to its end")
        if stream.exit_code not in (0, 2):
            findings.append(f"regrtest exit code {stream.exit_code}")
    else:
        mine = [o for o, n, _ in stream.outcomes if n == trap.test or n.startswith(trap.test + " ")]
        if stream.exit_code not in (0, 2) or not mine:
            findings.append(
                f"the entry ran nothing: {trap.test} (regrtest exit code {stream.exit_code})"
            )
        bad = [o for o in mine if o in OUTCOMES]
        if bad:
            findings.append(f"the entry's test {bad[0]} without a trap: {trap.test}")
    for name, reason in stream.load_errors:
        findings.append(f"module {name} failed to load — {reason}")
    return TrapVerdict(findings, seen, counts, run.fuel)


# ---------------------------------------------------------------------------------------------
# The rules (Decision 16)


def _class_methods(source: str) -> dict[str, tuple[list[str], set[str]]]:
    """Each class of a module: (its base names, the methods it defines)."""
    out = {}
    for node in ast.walk(ast.parse(source)):  # a class may sit under an `if` (test_tempfile)
        if isinstance(node, ast.ClassDef):
            bases = [b.id if isinstance(b, ast.Name) else ast.unparse(b) for b in node.bases]
            methods = {
                n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            out[node.name] = (bases, methods)
    return out


def _has_method(classes: dict, klass: str, method: str, seen: set | None = None) -> bool | None:
    """True or False when the module decides it; None when a base lies outside the module."""
    seen = seen or set()
    if klass in seen or klass not in classes:
        return None
    seen.add(klass)
    bases, methods = classes[klass]
    if method in methods:
        return True
    undecided = False
    for b in bases:
        if b in ("unittest.TestCase", "TestCase", "object"):
            continue
        got = _has_method(classes, b, method, seen)
        if got:
            return True
        if got is None:
            undecided = True
    return None if undecided else False


def id_exists(test_id: str, sources: dict[str, str]) -> bool:
    """Whether a full test id's class and method are in its module's source (`Lib/test/…`
    members' text), a method inherited from a base class in the same module included."""
    parts = test_id.split(".")
    if parts[:1] != ["test"]:
        return False
    for i in range(len(parts) - 2, 1, -1):
        rel = "Lib/" + "/".join(parts[:i]) + ".py"
        pkg = "Lib/" + "/".join(parts[:i]) + "/__init__.py"
        src = sources.get(rel) or (sources.get(pkg) if i == len(parts) - 2 else None)
        if src is not None and len(parts) - i == 2:
            classes = _class_methods(src)
            if parts[i] not in classes:  # the test's own class is defined in its module
                return False
            return _has_method(classes, parts[i], parts[i + 1]) is not False
    return False


def module_exists(module: str, members: set[str]) -> bool:
    base = "Lib/test/" + module.replace(".", "/")
    return f"{base}.py" in members or f"{base}/__init__.py" in members


def rule_errors(
    cfg,
    gap_checks: set[str],
    *,
    systems_of: dict[str, set[str]] | None = None,
    members: set[str] | None = None,
    sources: dict[str, str] | None = None,
) -> list[str]:
    pkg = cfg.package
    errors: list[str] = []
    placed: dict[str, str] = {}
    for g in cfg.groups.values():
        mods = list(g.modules)
        if not mods:
            errors.append(f"{pkg}: group {g.name}'s plan {g.list_file} is missing or empty")
            continue
        if len(set(mods)) != len(mods):
            errors.append(f"{pkg}: group {g.name}'s plan names a module twice")
        body = [m for m in mods if m != "test_monitoring"]
        if body != sorted(body):
            errors.append(f"{pkg}: group {g.name}'s plan is not sorted")
        if "test_monitoring" in mods:
            if mods[-1] != "test_monitoring":
                errors.append(f"{pkg}: test_monitoring is not last in {g.name}")
            if "test_profiling" in mods:
                errors.append(f"{pkg}: test_profiling is in test_monitoring's group {g.name}")
        for m in mods:
            if m in placed:
                errors.append(f"{pkg}: {m} is in {placed[m]} and {g.name}")
            placed[m] = g.name
    for n in cfg.not_selected:
        for m in n.modules:
            if m in placed:
                errors.append(f"{pkg}: {m} is in {placed[m]} and not selected")
            placed[m] = "not selected"
    for t in cfg.traps:
        if t.group not in cfg.groups:
            errors.append(f"{pkg}: trap {t.id} names no group: {t.group!r}")
            continue
        if t.module:
            if t.module in placed:
                errors.append(f"{pkg}: {t.module} is in {placed[t.module]} and trap {t.id}")
            placed[t.module] = f"trap {t.id}"
        elif module_of_id(t.test, set(cfg.groups[t.group].modules)) is None:
            errors.append(f"{pkg}: trap {t.id}'s test is in no module of {t.group}")
    for d in cfg.deselected:
        if d.group not in cfg.groups:
            errors.append(f"{pkg}: deselection {d.id} names no group: {d.group!r}")
            continue
        for i in d.tests:
            if module_of_id(i, set(cfg.groups[d.group].modules)) is None:
                errors.append(f"{pkg}: deselected {i} is in no module of {d.group}")
        if deselected_node(d.group, d.id) not in gap_checks:
            errors.append(f"{pkg}: deselection {d.id} has no gap in tests/known_gaps.toml")
    for e in cfg.environment:
        if e.group not in cfg.groups:
            errors.append(f"{pkg}: environment entry {e.id} names no group: {e.group!r}")
            continue
        errors += [
            f"{pkg}: environment entry {e.id}: {m} is not in {e.group}"
            for m in e.modules
            if m not in cfg.groups[e.group].modules
        ]
        if not e.changes:
            errors.append(f"{pkg}: environment entry {e.id} names no kind of change")
        if environment_node(e.group, e.id) not in gap_checks:
            errors.append(f"{pkg}: environment entry {e.id} has no gap in tests/known_gaps.toml")
    for h in cfg.host_dependent:
        if h.group not in cfg.groups:
            errors.append(f"{pkg}: host entry {h.id} names no group: {h.group!r}")
            continue
        mods = set(cfg.groups[h.group].modules)
        if bool(h.test) == bool(h.module):
            errors.append(f"{pkg}: host entry {h.id} names neither or both a test and a module")
        elif h.test and module_of_id(h.test, mods) is None:
            errors.append(f"{pkg}: host entry {h.id}'s test is in no module of {h.group}")
        elif h.module and h.module not in mods:
            errors.append(f"{pkg}: host entry {h.id}'s module is not in {h.group}")
        allowed = TEST_OUTCOMES if h.test else MODULE_RESULTS
        for s in sorted((systems_of or {}).get(h.group, set())):
            if s not in h.results:
                errors.append(f"{pkg}: host entry {h.id} records nothing for {s}")
        errors += [
            f"{pkg}: host entry {h.id}: {s} = {r!r}"
            for s, r in h.results.items()
            if r not in allowed
        ]
        if host_node(h.group, h.id) not in gap_checks:
            errors.append(f"{pkg}: host entry {h.id} has no gap in tests/known_gaps.toml")
    if members is not None:
        errors += [
            f"{pkg}: {m} names no test module of the tarball's Lib/test"
            for m in sorted(placed)
            if not module_exists(m, members)
        ]
    if sources is not None:
        ids = [i for d in cfg.deselected for i in d.tests] + [t.test for t in cfg.traps if t.test]
        ids += [h.test for h in cfg.host_dependent if h.test]
        errors += [
            f"{pkg}: {i} names no test of the tarball's source"
            for i in ids
            if not id_exists(i, sources)
        ]
    return errors


# ---------------------------------------------------------------------------------------------
# The judge run: one stage per run, one guest session per group, cached for the entry checks


@dataclass
class GroupRun:
    outcome: GroupOutcome
    fuel: int
    left_out: list[str]


class Session:
    """Stages `/cpython` once per judge run and runs each group once."""

    def __init__(self, workdir: Path, configs: dict) -> None:
        self.workdir = workdir
        self.configs = {p: c for p, c in configs.items() if c.runner == "regrtest"}
        self.root: Path | None = None
        self.prepared: dict[str, str | list[str]] = {}
        self.groups: dict[str, GroupRun] = {}

    def close(self) -> None:
        if self.root is not None:
            litter.remove(self.root)  # sealed: unsealed first (spec 089)

    def prepare(self, package: str) -> list[str]:
        if package not in self.prepared:
            self.prepared[package] = self._prepare(package)
        got = self.prepared[package]
        if isinstance(got, str):
            raise AssertionError(got)
        return got

    def _prepare(self, package: str) -> str | list[str]:
        from harness import pins, upstream

        cfg = self.configs[package]
        pair = pins.source_pair(cfg.component)
        assert pair is not None, f"no source tree for {cfg.component}"  # the need was met
        tarball, tree = pair
        manifest = paths.parse_manifest((paths.artifact_dir() / "MANIFEST").read_text())
        patches = upstream.repo_patches(upstream.tree_top(tarball))
        errors = upstream.tie_errors(package, manifest, tarball, patches)
        if errors:
            return "the tests are not the artifact's: " + "; ".join(errors)
        base = paths.HARNESS_TMP / "cpython"
        base.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix="run-", dir=base))
        left_out = stage(tarball, tree, self.root)
        judge = self.root / "judge"
        judge.mkdir()
        shutil.copyfile(upstream.HERE / DRIVER, judge / DRIVER)
        for g in cfg.groups:
            (judge / f"{g}.json").write_text(json.dumps(group_spec(cfg, g), indent=1))
        for t in cfg.traps:
            (judge / f"{t.id}.json").write_text(json.dumps(trap_spec(cfg, t), indent=1))
        litter.seal(self.root)  # no host process can add to the stage now (spec 089)
        return left_out

    def _run(self, name: str, fuel: int) -> tuple[Stream, GuestRun]:
        from harness import guest, upstream

        d = paths.artifact_dir()
        m = paths.parse_manifest((d / "MANIFEST").read_text())
        assert self.root is not None
        r = guest.run(
            d / "python-snapshot.wasm",
            guest_argv(name),
            workdir=self.workdir,
            python_version=m.python,
            stdlib=d / "python-stdlib.zip",
            env=ENV,
            fuel=fuel,
            preopens=preopens(self.root),
            mpl_data=upstream._has_mpl_data(d / "python-stdlib.zip"),
        )
        stream_file = r.root / STREAM
        text = stream_file.read_text(errors="replace") if stream_file.is_file() else ""
        tail = r.stderr.decode(errors="replace").strip().splitlines()[-1:] or [""]
        run = GuestRun(r.exit_code, r.trapped, r.trap_cause, r.fuel, tail[0][:200])
        litter.remove(r.root.parent)  # its stdlib folder is sealed (spec 089)
        return parse_stream(text), run

    def group(self, package: str, group: str) -> GroupRun:
        if group not in self.groups:
            left_out = self.prepare(package)
            cfg = self.configs[package]
            stream, run = self._run(group, cfg.groups[group].fuel)
            outcome = judge_group(stream, run, cfg, group, system())
            self.groups[group] = GroupRun(outcome, run.fuel, left_out)
        return self.groups[group]

    def trap(self, package: str, trap_id: str) -> TrapVerdict:
        from harness import upstream

        self.prepare(package)
        stream, run = self._run(trap_id, upstream.TRAP_FUEL)
        trap = next(t for t in self.configs[package].traps if t.id == trap_id)
        return trap_verdict(stream, run, trap)
