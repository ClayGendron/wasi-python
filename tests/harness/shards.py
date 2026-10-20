"""The release's shards and every package's own suite (spec 063).

A shard is a named selection of the judge's own checks, read from `tests/release_shards.toml`:
`uv run pytest --shard=<name>` deselects everything outside it through pytest's own hook, so node
ids, records and the ratchet are the judge's (Decision 1). The plugin and the gather both select
with `select`, and the plan's rules (`plan_errors`) need no artifacts (Decision 2). The file
`tests/upstream/packages.toml` names, for every component of the artifact, its own suite or why
not yet (`package_errors`, Decision 15).
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from harness import paths

PLAN = paths.REPO / "tests" / "release_shards.toml"
PACKAGES_FILE = paths.REPO / "tests" / "upstream" / "packages.toml"
UPSTREAM_FILE = "tests/checks/test_v1_3_upstream_suites.py"
OWN_SYSTEMS = ("macos", "linux", "windows")
SYSTEMS = (*OWN_SYSTEMS, "build")
# Each system's platform, as a run record's `meta.platform` begins (sys.platform).
PLATFORM = {"macos": "darwin", "linux": "linux", "windows": "win32", "build": "darwin"}


@dataclass(frozen=True)
class Shard:
    name: str
    systems: tuple[str, ...]
    files: tuple[str, ...] = ()
    groups: tuple[str, ...] = ()
    rest: bool = False
    nodes: tuple[str, ...] = ()  # the build shard only: single checks that need the build host


def load(path: Path = PLAN) -> dict[str, Shard]:
    """The plan, in the file's order. A malformed file raises (KeyError, TypeError, ValueError)."""
    raw = tomllib.loads(path.read_text())
    plan: dict[str, Shard] = {}
    for name, s in raw.get("shard", {}).items():
        plan[name] = Shard(
            name=name,
            systems=tuple(s.get("systems", ())),
            files=tuple(s.get("files", ())),
            groups=tuple(s.get("groups", ())),
            rest=bool(s.get("rest", False)),
            nodes=tuple(s.get("nodes", ())),
        )
    return plan


def on(plan: dict[str, Shard], system: str) -> list[str]:
    """The shards a system runs, in the plan's order."""
    return [name for name, s in plan.items() if system in s.systems]


def group_of(configs: dict | None = None) -> dict[str, str]:
    """Every upstream check's group: a group's suite check, its classes' checks (the map spec 052's
    scheduler keeps) and each trap whose file lies under one of the group's paths (the rule
    `upstream.group_spec` uses for its ignores)."""
    from harness import plugin, upstream

    configs = upstream.load_all() if configs is None else configs
    out = {
        node: scope.removeprefix("upstream ")
        for node, scope in plugin.upstream_scopes(configs).items()
    }
    for cfg in configs.values():
        for t in cfg.traps:
            if t.group:  # a regrtest trap names its group (spec 065)
                out[upstream.trap_node(t.id)] = t.group
                continue
            for g in cfg.groups.values():
                if any(t.file.startswith(p + "/") for p in g.paths):
                    out[upstream.trap_node(t.id)] = g.name
                    break
    return out


def group_systems(plan: dict[str, Shard] | None = None) -> dict[str, set[str]]:
    """Each upstream group's systems in the release: the union of its shards' (spec 065: what a
    host entry must record a result for)."""
    plan = load() if plan is None else plan
    out: dict[str, set[str]] = {}
    for s in plan.values():
        for g in s.groups:
            out.setdefault(g, set()).update(x for x in s.systems if x != "build")
    names = {"macos": "darwin", "linux": "linux", "windows": "win32"}
    return {g: {names[x] for x in xs} | {"darwin"} for g, xs in out.items()}


def select(
    nodeids: list[str], plan: dict[str, Shard], groups: dict[str, str]
) -> dict[str, list[str]]:
    """Each shard's items, in collection order (Decision 2). A group's checks go to every shard
    that names the group; another item goes to the shard whose `files` names its file, exactly
    (never by prefix); every item that no shard of the whole plan takes goes to `rest`."""
    out: dict[str, list[str]] = {name: [] for name in plan}
    by_node = {n: name for name, s in plan.items() for n in s.nodes}
    by_file = {f: name for name, s in plan.items() for f in s.files}
    rest = [name for name, s in plan.items() if s.rest]
    for node in nodeids:
        group = groups.get(node)
        if node in by_node:  # named by node id: that shard alone, whatever its file's shard
            takers = [by_node[node]]
        elif group is not None:
            takers = [name for name, s in plan.items() if group in s.groups]
        else:
            file = node.split("::", 1)[0]
            takers = [by_file[file]] if file in by_file else rest
        for name in takers:
            out[name].append(node)
    return out


def units_digest(nodeids: list[str]) -> str:
    """The digest of a set of unit tests' node ids (Decision 1, `meta.units`)."""
    return paths.sha256_bytes("\n".join(sorted(nodeids)).encode())


def test_files(tracked: list[str]) -> list[str]:
    """The test modules among tracked files: `test_*.py` under tests/, not the guest jobs."""
    return sorted(
        f
        for f in tracked
        if f.startswith("tests/")
        and not f.startswith("tests/jobs/")
        and re.fullmatch(r"test_[^/]*\.py", PurePosixPath(f).name)
    )


# The checks of the rules and the upstream file are not product checks; the runner's own unit files
# are (they test src/wasi_python on the host).
NOT_PRODUCT_CHECKS = ("tests/checks/test_rules.py", UPSTREAM_FILE)
PRODUCT_UNITS = re.compile(
    r"tests/test_api\.py|tests/unit/test_(runner_[^/]*|cli|tools|async_tools|guest_tools)\.py"
)


def product_files(files: list[str]) -> list[str]:
    """The product's test files among `files`: every goal-check file under tests/checks/ but the
    rules and the upstream file, and every runner unit file (rule (g))."""
    return [
        f
        for f in files
        if (f.startswith("tests/checks/") and f not in NOT_PRODUCT_CHECKS)
        or PRODUCT_UNITS.fullmatch(f)
    ]


def plan_errors(plan: dict[str, Shard], files: list[str], groups: list[str]) -> list[str]:
    """Rules (a) to (g) of Decision 2: `files` are the tracked test modules, `groups` every upstream
    group's name."""
    errors: list[str] = []
    if not plan:
        return ["the plan names no shard"]
    seen: dict[str, str] = {}
    for name, s in plan.items():
        kinds = [bool(s.files), bool(s.groups), s.rest]
        if sum(kinds) != 1:
            errors.append(f"(a) {name} selects by not exactly one of files, groups and rest")
        for f in s.files:
            if f not in files:
                errors.append(f"(a) {name}: {f} is not a tracked test file")
            if f == UPSTREAM_FILE:
                errors.append(f"(a) {name}: the upstream file is selected by groups and rest")
            if f in seen:
                errors.append(f"(a) {f} is in two shards: {seen[f]} and {name}")
            seen[f] = name
        for g in s.groups:
            if g not in groups:
                errors.append(f"(c) {name}: {g} is not an upstream group")
        for system in s.systems:
            if system not in SYSTEMS:
                errors.append(f"(d) {name}: unknown system {system}")
        if not s.systems:
            errors.append(f"(d) {name} runs on no system")
    rests = [name for name, s in plan.items() if s.rest]
    if len(rests) != 1:
        errors.append(f"(b) {len(rests)} shards are rest, not one")
    if not [f for f in files if f not in seen]:
        errors.append("(b) every test file is listed, so rest selects nothing")
    for g in groups:
        linux = [name for name, s in plan.items() if g in s.groups and "linux" in s.systems]
        if len(linux) != 1:
            errors.append(f"(c) upstream group {g} is in {len(linux)} Linux shards, not one")
    for name, s in plan.items():
        if "build" in s.systems and (name != "build" or s.systems != ("build",) or not s.files):
            errors.append(f"(d) {name}: only the shard build runs on build, alone, by files")
    if "build" not in plan:
        errors.append("(d) no shard named build")
    for name, s in plan.items():
        if s.files and name != "build" and set(s.systems) != set(OWN_SYSTEMS):
            errors.append(f"(e) {name} does not run on all of macos, linux and windows")
        # The rest shard holds the rules and the judge's own tooling (the build scripts, the
        # landing lane, the harness's self-tests): they run where the lane and the rebuild hosts
        # run, macOS and Linux (spec 063's first Windows run: 112 failures, none a product check).
        if s.rest and not {"macos", "linux"} <= set(s.systems):
            errors.append(f"(e) {name} does not run on macos and linux")
    # (h) Single checks by node id: only the build shard names them, each once, each a check of a
    # tracked test file (the confirmation's D1).
    named: set[str] = set()
    for name, s in plan.items():
        for n in s.nodes:
            file, _, test = n.partition("::")
            func = test.split("[", 1)[0]
            if name != "build":
                errors.append(f"(h) {name}: only the build shard names checks by node id")
            if n in named:
                errors.append(f"(h) {n} is named twice")
            named.add(n)
            if file not in files or not func:
                errors.append(f"(h) {n}: not a check of a tracked test file")
            elif (paths.REPO / file).is_file() and f"def {func}(" not in (
                paths.REPO / file
            ).read_text():
                errors.append(f"(h) {n}: {file} defines no {func}")
    # (g) Every product check file and every runner unit file is in a files shard that runs on all
    # three systems, so rest holds only the rules and the judge's own tooling, and a new product
    # file cannot fall off Windows by default (spec 063's build review, F1).
    on_all = {f for s in plan.values() if set(OWN_SYSTEMS) <= set(s.systems) for f in s.files}
    build_files = set(plan["build"].files) if "build" in plan else set()
    for f in product_files(files):
        if f not in on_all and f not in build_files:
            errors.append(f"(g) {f} is a product file in no files shard on all three systems")
    for system in SYSTEMS:
        taken: dict[str, str] = {}
        for name in on(plan, system):
            for g in plan[name].groups:
                if g in taken:
                    errors.append(f"(f) on {system}, {g} is in {taken[g]} and {name}")
                taken[g] = name
    return errors


# ---------------------------------------------------------------------------------------------
# Every package names its own suite (Decision 15)

KINDS = ("suite", "via", "build-only", "later")
# The runtimes linked into every binary, which neither list names (the pre-build review, F5).
LINKED_RUNTIMES = ("wasi-libc", "llvm-runtimes")
# needs.SOURCE_COMPONENTS names three components otherwise than paths.PACKAGES and the file do
# (scikit-learn's tree is named as its tarball names it; spec 044).
COMPONENT_NAMES = {"cpython": "python", "sqlite": "sqlite-autoconf", "scikit_learn": "scikit-learn"}
SPEC_NUMBER = re.compile(r"spec (\d{3})\b")


def components() -> list[str]:
    """Every component of the artifact that needs an entry: paths.PACKAGES, the source
    components (named as the file names them) and the linked runtimes."""
    from harness import needs

    names = set(paths.PACKAGES) | {COMPONENT_NAMES.get(c, c) for c in needs.SOURCE_COMPONENTS}
    return sorted(names | {"python"} | set(LINKED_RUNTIMES))


def reserved_numbers(roadmap_text: str) -> set[str]:
    """The specification numbers `context/roadmap.md` reserves on lines beginning `Reserved:`."""
    out: set[str] = set()
    for line in roadmap_text.split("\n\n"):
        if line.lstrip().startswith("Reserved:"):
            out |= set(re.findall(r"\b(\d{3}) \(", line))
    return out


def package_errors(
    raw: dict,
    names: list[str],
    suites: dict[str, int],
    repo: Path = paths.REPO,
) -> list[str]:
    """Why `packages.toml` (parsed as `raw`) does not name every component's suite; `suites`
    maps each package with an upstream config to its number of groups."""
    errors: list[str] = []
    entries = raw.get("package", {})
    modules = set(raw.get("stdlib_modules", []))
    roadmap = repo / "context" / "roadmap.md"
    reserved = reserved_numbers(roadmap.read_text()) if roadmap.is_file() else set()
    specs = {p.name[:3] for p in (repo / "context" / "specifications").glob("[0-9][0-9][0-9]-*.md")}
    for name in names:
        if name not in entries:
            errors.append(f"{name}: no entry in tests/upstream/packages.toml")
    for name, e in entries.items():
        kind = e.get("kind")
        if name not in names:
            errors.append(f"{name}: an entry for no component of the artifact")
        if kind not in KINDS:
            errors.append(f"{name}: unknown kind {kind!r}")
        elif kind == "suite":
            if not suites.get(name):
                errors.append(f"{name}: kind suite, but no tests/upstream/{name}.toml with a group")
        elif kind == "via":
            via = e.get("via", "")
            target = entries.get(via, {})
            # What reaches it: a package whose suite runs or is named to run (suite, later),
            # CPython, or a listed stdlib module; never a via or build-only entry, or nothing.
            if not (via == "python" or target.get("kind") in ("suite", "later") or via in modules):
                errors.append(
                    f"{name}: via {via!r} is not a suite or later entry, python or a listed "
                    "stdlib module"
                )
        elif kind == "build-only":
            if not str(e.get("reason", "")).strip():
                errors.append(f"{name}: build-only without a reason")
        elif kind == "later":
            if not str(e.get("reason", "")).strip():
                errors.append(f"{name}: later without a reason")
            m = SPEC_NUMBER.fullmatch(str(e.get("closes_with", "")).split(",")[0].strip())
            if not m or (m[1] not in specs and m[1] not in reserved):
                errors.append(
                    f"{name}: closes_with {e.get('closes_with')!r} names no specification, "
                    "written or reserved"
                )
    return errors
