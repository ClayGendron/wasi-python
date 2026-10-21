"""numpy's and pandas' own tests, run inside the guest, and the configuration of every
upstream suite, CPython's included (its runner is `harness.regrtest`), and the compiled
packages' (`driver = "package"`, a family each, run by `harness.packages`).

The judge stages the tests of the artifact's own pinned source trees (tarball members, and files a
recorded patch creates, only) with the pinned test kit into one read-only grant, `/upstream`, and
runs pytest in the snapshot binary, one guest session per group. The guest writes an outcome
stream (`tests/upstream/drive.py`); this module reads it, sorts each failure into the class that
admits it, and names everything else as a finding. Each class and each trap is its own check and
an ordinary gap; a group admits nothing by itself.

A fuel fact is a test whose fuel measures where a type object sits in memory, not the
product. It is deselected from its group and run alone in a second session inside the group's
check: its outcomes count with the group's, its fuel is recorded and never ratcheted, and its cap
is the only bound on it.
"""

from __future__ import annotations

import json
import re
import shutil
import tarfile
import tempfile
import tomllib
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from harness import litter, paths

HERE = paths.REPO / "tests" / "upstream"
KIT = HERE / "kit.txt"
EXPECTED = HERE / "expected"
WHEELS = paths.BUILD / "upstream" / "wheels"
CHECKS_FILE = "tests/checks/test_v1_3_upstream_suites.py"
PACKAGES = ("numpy", "pandas", "python")
# The compiled packages' own suites, one family (grant, stage, budget) each.
PACKAGE_SUITES = ("matplotlib", "contourpy", "pillow", "kiwisolver", "lxml", "regex")
GRANT = "/upstream"
STREAM = "tmp/upstream/outcomes.txt"  # in the guest's root
TIER = "normal"  # a group without `tier` is in the normal tier
TIERS = ("normal", "release")
TRAP_FUEL = 5 * 10**10
CAP_BUDGET = 3 * 10**12
ENV = {"TMPDIR": "/tmp", "HOME": "/tmp"}
OUTCOMES = ("failed", "error")


# ---------------------------------------------------------------------------------------------
# The configuration: tests/upstream/<package>.toml


@dataclass(frozen=True)
class Group:
    name: str
    paths: tuple[str, ...]
    fuel: int
    modules: tuple[str, ...] = ()  # a regrtest group's plan, in run order
    list_file: str = ""
    tier: str = "normal"  # "release": run only before a publication, never left out
    release_by: str = ""  # a pytest release group's kind, "marker" or "keyword"
    measured: int | None = None  # the fuel a judge run recorded, which bounds the cap
    selects_nothing: str = ""  # a marker release group kept as a guard: why it may run no test
    smoke: str | None = None  # a smoke family's normal group: why it is the package's smoke


@dataclass(frozen=True)
class ReleaseSelect:
    """Tests the project runs in the release tier: within `files`, those matching `keyword` that
    the family's normal marker selects."""

    files: tuple[str, ...]
    keyword: str
    reason: str


@dataclass(frozen=True)
class NotSelected:
    files: tuple[str, ...]
    reason: str
    closes_with: str
    modules: tuple[str, ...] = ()  # regrtest modules listed nowhere


@dataclass(frozen=True)
class Trap:
    id: str
    node: str  # a node id, a node-id prefix or a file
    reason: str
    closes_with: str
    group: str = ""  # its group: a regrtest trap's, and any in a family with release groups
    test: str = ""  # a regrtest trap's full test id, or
    module: str = ""  # its whole module

    @property
    def file(self) -> str:
        return self.node.split("::", 1)[0]


@dataclass(frozen=True)
class FuelFact:
    """A test whose fuel is a fact, not a metric. `node` is `file::function` (or
    `file::Class::function`), a parametrized test: the group deselects `node[`, and the fact's own
    session runs `node`. `fuel` is that session's cap, at least twice its fuel when measured."""

    id: str
    group: str
    node: str
    fuel: int
    reason: str
    evidence: tuple[str, ...]

    @property
    def file(self) -> str:
        return self.node.split("::", 1)[0]

    def owns(self, node: str) -> bool:
        """Whether a test's node id is one of the entry's cases."""
        return node.startswith(self.node + "[")


@dataclass(frozen=True)
class Klass:
    id: str
    group: str
    outcome: str
    match: str
    reason: str
    closes_with: str


@dataclass(frozen=True)
class Config:
    package: str
    marker: str
    args: list[str]
    path_packages: list[str]
    markers: list[str]
    support: list[str]
    groups: dict[str, Group]
    not_selected: list[NotSelected]
    traps: list[Trap]
    expected: list[Klass]
    runner: str = "pytest"
    component: str = ""
    grant: str = GRANT
    resources: str = ""
    options: tuple[str, ...] = ()
    warnings: str = ""
    deselected: list = field(default_factory=list)
    environment: list = field(default_factory=list)
    host_dependent: list = field(default_factory=list)
    fuel_facts: list[FuelFact] = field(default_factory=list)  # recorded, never ratcheted
    driver: str = "upstream"  # "package": the compiled packages' families, read by harness.packages
    keys: object = None  # harness.packages.PackageKeys when driver == "package"
    release_marker: str = ""  # the -m its marker release groups run
    excluded_marker: str = ""  # what no tier runs, for a capability the guest lacks
    excluded_reason: str = ""
    excluded_closes_with: str = ""
    release_select: list[ReleaseSelect] = field(default_factory=list)
    release_resources: str = ""  # regrtest: the resources its release groups enable
    release_entries: list = field(default_factory=list)  # regrtest: the release lists' ids

    def classes(self, group: str) -> list[Klass]:
        return [k for k in self.expected if k.group == group]

    def facts(self, group: str) -> list[FuelFact]:
        return [f for f in self.fuel_facts if f.group == group]


def _fuel_facts(raw: dict) -> list[FuelFact]:
    return [
        FuelFact(
            f["id"],
            f["group"],
            f["node"],
            int(f["fuel"]),
            f.get("reason", ""),
            tuple(f.get("evidence", [])),
        )
        for f in raw.get("fuel_fact", [])
    ]


def load(package: str, directory: Path = HERE) -> Config:
    raw = tomllib.loads((directory / f"{package}.toml").read_text())
    if raw.get("runner", "pytest") == "regrtest":
        return _load_regrtest(raw, directory)
    if raw.get("driver") == "package":
        from harness import packages

        return packages.load(raw)
    return from_raw(raw, directory)


def group_of(name: str, g: dict) -> Group:
    """A pytest family's group, its tier fields read as the TOML gives them."""
    measured = g.get("measured")
    return Group(
        name,
        tuple(g["paths"]),
        int(g["fuel"]),
        tier=g.get("tier", TIER),
        release_by=g.get("release_by", ""),
        measured=None if measured is None else int(measured),
        selects_nothing=g.get("selects_nothing", ""),
        smoke=g.get("smoke"),
    )


def tier_fields(raw: dict) -> dict:
    """The family's release-tier keys, as Config takes them."""
    return {
        "release_marker": raw.get("release_marker", ""),
        "excluded_marker": raw.get("excluded_marker", ""),
        "excluded_reason": raw.get("excluded_reason", ""),
        "excluded_closes_with": raw.get("excluded_closes_with", ""),
        "release_select": [
            ReleaseSelect(tuple(e.get("files", [])), e.get("keyword", ""), e.get("reason", ""))
            for e in raw.get("release_select", [])
        ],
    }


def from_raw(raw: dict, directory: Path = HERE) -> Config:
    """numpy's and pandas' kind of family, from its parsed TOML."""
    return Config(
        package=raw["package"],
        marker=raw["marker"],
        args=list(raw.get("args", [])),
        path_packages=list(raw["path_packages"]),
        markers=list(raw.get("markers", [])),
        support=list(raw.get("support", [])),
        groups={name: group_of(name, g) for name, g in raw.get("groups", {}).items()},
        not_selected=[
            NotSelected(tuple(n["files"]), n["reason"], n["closes_with"])
            for n in raw.get("not_selected", [])
        ],
        traps=[
            Trap(t["id"], t["node"], t["reason"], t["closes_with"], t.get("group", ""))
            for t in raw.get("trap", [])
        ],
        expected=[
            Klass(e["id"], e["group"], e["outcome"], e["match"], e["reason"], e["closes_with"])
            for e in raw.get("expected", [])
        ],
        fuel_facts=_fuel_facts(raw),
        **tier_fields(raw),
    )


def _load_regrtest(raw: dict, directory: Path) -> Config:
    from harness import regrtest

    deselected, environment, hosts = regrtest.entries_from(raw)
    groups, entries = regrtest.groups_from(raw, directory)
    return Config(
        package=raw["package"],
        marker="",
        args=[],
        path_packages=[],
        markers=[],
        support=[],
        groups=groups,
        not_selected=[
            NotSelected((), n["reason"], n["closes_with"], tuple(n["modules"]))
            for n in raw.get("not_selected", [])
        ],
        traps=[
            Trap(
                t["id"],
                "",
                t["reason"],
                t["closes_with"],
                t["group"],
                t.get("test", ""),
                t.get("module", ""),
            )
            for t in raw.get("trap", [])
        ],
        expected=[
            Klass(e["id"], e["group"], e["outcome"], e["match"], e["reason"], e["closes_with"])
            for e in raw.get("expected", [])
        ],
        runner="regrtest",
        component=raw["component"],
        grant=raw["grant"],
        resources=raw["resources"],
        options=tuple(raw.get("options", [])),
        warnings=raw.get("warnings", ""),
        deselected=deselected,
        environment=environment,
        host_dependent=hosts,
        fuel_facts=_fuel_facts(raw),  # refused by the rules: a regrtest suite has none
        release_resources=raw.get("release_resources", ""),
        release_entries=entries,
    )


def load_all(directory: Path = HERE) -> dict[str, Config]:
    names = PACKAGES + tuple(p for p in PACKAGE_SUITES if (directory / f"{p}.toml").is_file())
    return {p: load(p, directory) for p in names}


def suite_node(group: str) -> str:
    return f"{CHECKS_FILE}::test_upstream_suite[{group}]"


def class_node(group: str, klass: str) -> str:
    return f"{CHECKS_FILE}::test_upstream_class[{group}-{klass}]"


def trap_node(trap: str) -> str:
    return f"{CHECKS_FILE}::test_upstream_trap[{trap}]"


def entry_node(kind: str, group: str, entry: str) -> str:
    """A CPython deselection, environment or host entry's check."""
    return f"{CHECKS_FILE}::test_upstream_{kind}[{group}-{entry}]"


def release_checks(configs: dict[str, Config]) -> set[str]:
    """Every check of a release-tier group: its suite, its classes, the traps and entries that
    name it. A check takes its group's tier, so a group's checks never run in two tiers."""
    out: set[str] = set()
    for cfg in configs.values():
        mine = {g.name for g in cfg.groups.values() if g.tier == "release"}
        out |= {suite_node(g) for g in mine}
        out |= {class_node(k.group, k.id) for k in cfg.expected if k.group in mine}
        out |= {trap_node(t.id) for t in cfg.traps if t.group in mine}
        for kind, entries in (
            ("deselected", cfg.deselected),
            ("environment", cfg.environment),
            ("host", cfg.host_dependent),
        ):
            out |= {entry_node(kind, e.group, e.id) for e in entries if e.group in mine}
    return out


def list_path(klass: Klass, expected_dir: Path = EXPECTED) -> Path:
    return expected_dir / klass.group / f"{klass.id}.txt"


def read_list(path: Path) -> list[str]:
    """A class's node ids, one per line; a missing file is an empty list."""
    if not path.is_file():
        return []
    return [line for line in path.read_text().splitlines() if line.strip()]


# ---------------------------------------------------------------------------------------------
# The test kit (Decision 2)

KIT_LINE = re.compile(r"([0-9a-f]{64})  (https://\S+)")
WHEEL_NAME = re.compile(r"[A-Za-z0-9_.]+-[A-Za-z0-9_.!+]+-(py3|py2\.py3)-none-any\.whl")


def kit_entries(text: str) -> list[tuple[str, str, str]]:
    """(sha256, url, file name) per line."""
    out = []
    for line in text.splitlines():
        m = KIT_LINE.fullmatch(line.strip())
        if m:
            out.append((m[1], m[2], m[2].rsplit("/", 1)[1]))
    return out


def kit_errors(text: str) -> list[str]:
    errors = []
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        m = KIT_LINE.fullmatch(line)
        if not m:
            errors.append(f"kit.txt:{n}: not '<64 hex>  <url>': {line[:80]!r}")
            continue
        url = m[2]
        if not url.startswith("https://files.pythonhosted.org/"):
            errors.append(f"kit.txt:{n}: not a files.pythonhosted.org URL: {url}")
        elif not WHEEL_NAME.fullmatch(url.rsplit("/", 1)[1]):
            errors.append(f"kit.txt:{n}: not a py3-none-any wheel: {url.rsplit('/', 1)[1]}")
    return errors


def kit_met(kit: Path = KIT, wheels: Path = WHEELS) -> bool:
    """Every wheel of kit.txt is in `wheels` with its SHA-256 (the need `upstream kit`)."""
    try:
        entries = kit_entries(kit.read_text())
    except OSError:
        return False
    return bool(entries) and all(
        (wheels / name).is_file() and paths.sha256_file(wheels / name) == sha
        for sha, _, name in entries
    )


def safe_unzip(wheel: Path, dest: Path) -> None:
    """Unpack a wheel; refuse an absolute member name or any member with a `..` part."""
    with zipfile.ZipFile(wheel) as z:
        names = z.namelist()
        for name in names:
            parts = re.split(r"[\\/]", name)
            if name.startswith(("/", "\\")) or re.match(r"[A-Za-z]:", name) or ".." in parts:
                raise ValueError(f"{wheel.name}: member {name!r} refused (outside its folder)")
            litter.refuse(name, wheel.name)  # the seal's cleanup must never meet it
        dest.mkdir(parents=True, exist_ok=True)
        for info in z.infolist():
            target = dest / info.filename
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(info))


# ---------------------------------------------------------------------------------------------
# The tie to the artifact and the member filter (Decision 3)

TARBALL = {
    "numpy": re.compile(r"numpy-[\w.]+\.tar\.gz"),
    "pandas": re.compile(r"pandas-[\w.]+\.tar\.gz"),
    "python": re.compile(r"Python-\d+\.\d+\.\d+\.tar\.xz"),
    # the compiled packages' pinned sdists
    "matplotlib": re.compile(r"matplotlib-[\w.]+\.tar\.gz"),
    "contourpy": re.compile(r"contourpy-[\w.]+\.tar\.gz"),
    "pillow": re.compile(r"pillow-[\w.]+\.tar\.gz"),
    "kiwisolver": re.compile(r"kiwisolver-[\w.]+\.tar\.gz"),
    "lxml": re.compile(r"lxml-[\w.]+\.tar\.gz"),
    "regex": re.compile(r"regex-[\w.]+\.tar\.gz"),
}


def tree_top(tarball: Path) -> str:
    """The folder a source tarball unpacks to: its name less `.tar.gz` or `.tar.xz`."""
    return tarball.name.removesuffix(".tar.gz").removesuffix(".tar.xz")


def repo_patches(top: str, repo: Path = paths.REPO) -> dict[str, str]:
    """The repository's patches for a tree, as MANIFEST names them: {path: sha256}."""
    folder = repo / "recipes" / "patches" / top
    return {
        p.relative_to(repo).as_posix(): paths.sha256_file(p)
        for p in sorted(folder.glob("[0-9][0-9][0-9][0-9]-*.patch"))
    }


def tie_errors(
    package: str,
    manifest: paths.Manifest,
    tarball: Path,
    patches: dict[str, str],
    tarball_sha: str | None = None,
) -> list[str]:
    """Why the tests (from `tarball` and `patches`) are not the artifact's; empty when they are."""
    errors = []
    built = {n: s for n, s in manifest.pins.items() if TARBALL[package].fullmatch(n)}
    sha = tarball_sha or paths.sha256_file(tarball)
    if tarball.name not in built:
        names = ", ".join(sorted(built)) or f"no {package} tarball"
        errors.append(f"tests from {tarball.name}, artifact built from {names}")
    elif built[tarball.name] != sha:
        errors.append(
            f"tests from {tarball.name} SHA-256 {sha[:12]}, artifact built from "
            f"{tarball.name} SHA-256 {built[tarball.name][:12]}"
        )
    top = tree_top(tarball)
    prefix = f"recipes/patches/{top}/"
    recorded = {
        p: s for p, s in manifest.recipes.items() if p.startswith(prefix) and p.endswith(".patch")
    }
    for p in sorted(set(recorded) | set(patches)):
        if recorded.get(p) != patches.get(p):
            mine = (patches.get(p) or "absent")[:12]
            theirs = (recorded.get(p) or "absent")[:12]
            errors.append(f"tests carry patch {p} {mine}, artifact built with {theirs}")
    return errors


def tarball_members(tarball: Path) -> set[str]:
    """Every regular file the tarball holds, relative to its top folder."""
    out = set()
    with tarfile.open(tarball) as t:
        for m in t:
            parts = m.name.split("/", 1)
            if m.isfile() and len(parts) == 2 and parts[1]:
                out.add(parts[1])
    return out


def patch_created(text: str) -> set[str]:
    """Files a patch creates: its `+++ b/<path>` lines whose `---` side is /dev/null."""
    out, prev = set(), ""
    for line in text.splitlines():
        if line.startswith("+++ ") and prev.strip() == "--- /dev/null":
            name = line[4:].split("\t", 1)[0].strip()
            out.add(name[2:] if name.startswith("b/") else name)
        prev = line
    return out


def _ancestors(rel: str) -> list[str]:
    """The folders from the first `tests` folder above `rel` down to `rel`'s parent."""
    parts = PurePosixPath(rel).parts
    if "tests" not in parts:
        return []
    start = parts.index("tests")
    return ["/".join(parts[: i + 1]) for i in range(start, len(parts) - 1)]


def staged_folders(cfg: Config) -> list[str]:
    folders = {p for g in cfg.groups.values() for p in g.paths}
    folders |= {str(PurePosixPath(t.file).parent) for t in cfg.traps}
    return sorted(f for f in folders if not any(f.startswith(o + "/") for o in folders))


def stage(cfg: Config, tree: Path, allowed: set[str], dest: Path) -> list[str]:
    """Copy the groups' and traps' folders, their `tests` ancestors' __init__.py and conftest.py,
    and the support files from `tree` to `dest`, members only. Returns what was left out."""
    wanted: set[str] = set(cfg.support)
    left_out: list[str] = []
    for folder in staged_folders(cfg):
        root = tree / folder
        for p in sorted(root.rglob("*")):
            if p.is_dir():
                continue
            rel = p.relative_to(tree).as_posix()
            if rel in allowed:
                wanted.add(rel)
            elif not litter.unrecorded(rel):  # no fact holds litter or bytecode
                left_out.append(rel)
        for anc in _ancestors(folder + "/x"):
            wanted |= {f"{anc}/__init__.py", f"{anc}/conftest.py"} & allowed
    for rel in sorted(wanted):
        if rel not in allowed or not (tree / rel).is_file():
            continue
        litter.refuse(rel, tree.name)  # the seal's cleanup must never meet it
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(tree / rel, target)
    return sorted(left_out)


def _has_mpl_data(stdlib: Path) -> bool:
    import zipfile

    from harness import guest

    with zipfile.ZipFile(stdlib) as z:
        return guest.MPL_DATA_MEMBER in z.NameToInfo


def preopens(stage_root: Path) -> list[tuple[str, Path, bool]]:
    """The one grant every group and trap check gets: the stage, read-only, at /upstream."""
    return [(GRANT, stage_root, False)]


# ---------------------------------------------------------------------------------------------
# The argv (Decisions 5, 7, 8, 9)


def _abs(rel: str) -> str:
    return f"{GRANT}/tests/{rel}"


def group_spec(cfg: Config, group: Group) -> dict:
    from harness import tiers

    inside = [p + "/" for p in group.paths]
    mine = lambda f: any(f.startswith(p) for p in inside)  # noqa: E731
    ignores = [f for n in cfg.not_selected for f in n.files if mine(f)]
    ignores += [t.node for t in cfg.traps if "::" not in t.node and mine(t.node)]
    ignores += tiers.smoke_ignores(cfg, group)  # a path release group leaves the smoke files
    deselects = [t.node for t in cfg.traps if "::" in t.node and mine(t.node)]
    deselects += [f.node + "[" for f in cfg.facts(group.name)]  # its cases only
    return {
        "path_packages": cfg.path_packages,
        "markers": cfg.markers,
        "args": [
            *(["-m", m] if (m := tiers.marker_of(cfg, group)) or group.tier == "normal" else []),
            *cfg.args,
            *[_abs(p) for p in group.paths],
            *[f"--ignore={_abs(f)}" for f in dict.fromkeys(ignores)],
            *[f"--deselect={d}" for d in deselects],
            *[f"-k{k}" for k in [tiers.keyword_arg(cfg, group, None)] if k is not None],
        ],
    }


def trap_spec(cfg: Config, trap: Trap) -> dict:
    """The entry alone, with no marker: whatever it names runs."""
    return {
        "path_packages": cfg.path_packages,
        "markers": cfg.markers,
        "args": [*cfg.args, _abs(trap.node)],
    }


def fact_spec(cfg: Config, fact: FuelFact) -> dict:
    """The entry alone, under its group's marker and tier filter, so it runs exactly the cases
    its group would have run."""
    from harness import tiers

    group = cfg.groups[fact.group]
    k = tiers.keyword_arg(cfg, group, None)
    return {
        "path_packages": cfg.path_packages,
        "markers": cfg.markers,
        "args": [
            "-m",
            tiers.marker_of(cfg, group),
            *cfg.args,
            _abs(fact.node),
            *([f"-k{k}"] if k is not None else []),
        ],
    }


def judge_specs(cfg: Config) -> dict[str, dict]:
    """Every JSON a family's stage holds, by name: each group's, both tiers', each trap's and
    each fuel fact's. The tier a run judges never changes what is staged, so a normal row's fuel
    is the same in a normal run and a release run."""
    out = {g.name: group_spec(cfg, g) for g in cfg.groups.values()}
    out |= {t.id: trap_spec(cfg, t) for t in cfg.traps}
    out |= {f.id: fact_spec(cfg, f) for f in cfg.fuel_facts}
    return out


def guest_argv(package: str, name: str) -> list[str]:
    return ["-u", f"{GRANT}/judge/drive.py", package, name]


# ---------------------------------------------------------------------------------------------
# The stream (Decision 11) and what a group's run means (Decision 10)


@dataclass
class Stream:
    outcomes: list[tuple[str, str, str]] = field(default_factory=list)  # (outcome, node, reason)
    collect_errors: list[tuple[str, str]] = field(default_factory=list)
    profile: str | None = None
    modules: list[tuple[str, str]] = field(default_factory=list)
    exit_code: int | None = None
    open_node: str | None = None  # the last S or C line: what ran when the stream ended
    started: list[str] = field(default_factory=list)  # every S and C node, in order


def parse_stream(text: str) -> Stream:
    s = Stream()
    current = None
    for line in text.splitlines():
        kind, _, rest = line.partition(" ")
        if kind == "C":
            s.open_node = rest
            s.started.append(rest)
        elif kind == "S":
            s.open_node = current = rest
            s.started.append(rest)
        elif kind == "R":
            outcome, _, tail = rest.partition(" ")
            if current is not None and (
                tail.startswith(current + " -- ") or tail.rstrip() == current + " --"
            ):
                node, reason = current, tail[len(current) + 4 :]
            else:
                node, _, reason = tail.partition(" -- ")
            s.outcomes.append((outcome, node, reason.strip()))
        elif kind == "X":
            node, _, reason = rest.partition(" -- ")
            s.collect_errors.append((node, reason.strip()))
        elif kind == "P":
            s.profile = rest
        elif kind == "M":
            name, _, f = rest.partition(" ")
            s.modules.append((name, f))
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
    stdout: str
    stderr_tail: str


@dataclass
class GroupOutcome:
    findings: list[str]
    members: dict[str, list[str]]
    passes: int
    passed_digest: str
    counts: dict[str, int]
    finished: bool


def passed_digest(nodes: list[str]) -> str:
    return paths.sha256_bytes("\n".join(sorted(nodes)).encode())[:12]


def _ended(stream: Stream, run: GuestRun) -> list[str]:
    """How the session ended, when it did not end normally."""
    if run.trapped:
        where = stream.open_node if stream.open_node is not None else "start"
        if run.trapped == "out of fuel":
            return [f"out of fuel at {where}"]
        return [f"trap: {run.cause or run.trapped} at {where}"]
    if stream.exit_code is None:
        return [f"no E line: the session did not finish (exit {run.exit_code}; {run.stderr_tail})"]
    return []


def trap_findings(stream: Stream, run: GuestRun, entry: str) -> list[str]:
    """A trap check's findings: the trap (or fuel) that ended the entry's session; or, when it
    did not trap, a session that did not finish or never started anything under the entry's
    node id (a renamed test, nothing collected, a usage error), which guards nothing.
    The entry is a node id, a node-id prefix or a file, as `--deselect` reads it."""
    if run.trapped:
        return _ended(stream, run)
    if stream.exit_code is None:
        return _ended(stream, run)
    if not any(node.startswith(entry) for node in stream.started):
        return [f"the entry ran nothing: {entry} (pytest exit code {stream.exit_code})"]
    return []


def _profile_ok(profile: str) -> bool:
    fields = dict(p.partition("=")[::2] for p in profile.split())
    return fields.get("derandomize") == "True" and fields.get("database") == "None"


def judge_group(stream: Stream, run: GuestRun, classes: list[Klass]) -> GroupOutcome:
    findings: list[str] = []
    members: dict[str, list[str]] = {k.id: [] for k in classes}
    compiled = [(k, re.compile(k.match)) for k in classes]
    for outcome, node, reason in stream.outcomes:
        if outcome not in OUTCOMES:
            continue  # pass, skip, xfail, non-strict xpass: upstream's own outcomes
        k = next((k for k, rx in compiled if k.outcome == outcome and rx.search(reason)), None)
        if k is not None:
            members[k.id].append(node)
        else:
            findings.append(f"unexpected {outcome} {node} — {reason}")
    findings += [f"collection error {node} — {why}" for node, why in stream.collect_errors]
    ended = _ended(stream, run)
    findings += ended
    if not ended:
        code = stream.exit_code
        if code == 3 or "INTERNALERROR" in run.stdout:
            findings.append(f"INTERNALERROR (pytest exit code {code})")
        elif code not in (0, 1):
            findings.append(f"pytest exit code {code}")
        if run.exit_code != 0:
            findings.append(f"guest exit {run.exit_code} after the E line")
        if stream.profile is None:
            findings.append("no P line: collection did not finish")
        elif not _profile_ok(stream.profile):
            findings.append(
                f"hypothesis profile not derandomized or with a database: {stream.profile}"
            )
    for name, f in stream.modules:
        if "tests" not in name.split(".") and name != "pandas.conftest":
            findings.append(f"a product module came from the grant: {name} {f}")
    passed = [n for o, n, _ in stream.outcomes if o == "passed"]
    return GroupOutcome(
        findings=findings,
        members={k: sorted(set(v)) for k, v in members.items()},
        passes=len(passed),
        passed_digest=passed_digest(passed),
        counts=dict(sorted(Counter(o for o, _, _ in stream.outcomes).items())),
        finished=not ended,
    )


def _tests(stream: Stream) -> list[str]:
    return list(dict.fromkeys(n for _, n, _ in stream.outcomes))


def fact_findings(group: Stream, alone: Stream, fact: FuelFact) -> list[str]:
    """Whether the entry's cases ran exactly once: none in the group's session, and in
    its own session at least one of them and nothing else."""
    where = f"fuel fact {fact.id}"
    found = [f"{where}: {n} also ran in the group" for n in _tests(group) if fact.owns(n)]
    mine = _tests(alone)
    if not any(fact.owns(n) for n in mine):
        found.append(f"{where}: its session ran nothing of {fact.node}")
    found += [f"{where}: its session ran {n}, outside the entry" for n in mine if not fact.owns(n)]
    return found


def combine(parts: list[tuple[Stream, GroupOutcome, str]], extra: list[str]) -> GroupOutcome:
    """One group's outcome from its sessions, the group's own and each fuel fact's:
    findings keep their session's prefix; members, counts and passes add up; the digest is of every
    passed id, so it is the one a single session gives when nothing else changed."""
    passed = [n for s, _, _ in parts for o, n, _ in s.outcomes if o == "passed"]
    members: dict[str, set[str]] = {}
    counts: Counter[str] = Counter()
    findings: list[str] = []
    for _, outcome, prefix in parts:
        findings += [prefix + f for f in outcome.findings]
        for k, v in outcome.members.items():
            members.setdefault(k, set()).update(v)
        counts.update(outcome.counts)
    return GroupOutcome(
        findings=findings + extra,
        members={k: sorted(v) for k, v in members.items()},
        passes=len(passed),
        passed_digest=passed_digest(passed),
        counts=dict(sorted(counts.items())),
        finished=all(outcome.finished for _, outcome, _ in parts),
    )


def class_findings(actual: list[str], listed: list[str]) -> list[str]:
    """One finding per member, plus `+id` for each not in the list and `-id` for each listed but
    gone; none when the class is empty (its gap then says "remove the gap")."""
    if not actual:
        return []
    now, was = sorted(set(actual)), set(listed)
    return now + [f"+{n}" for n in now if n not in was] + [f"-{n}" for n in sorted(was - set(now))]


# ---------------------------------------------------------------------------------------------
# The rules (Decision 17)


def caps(configs: dict[str, Config], tier: str | None = None) -> int:
    """The family's fuel caps: its groups', its traps' and its fuel facts', of one tier or of
    both. A trap or a fact takes its group's tier."""

    def mine(c: Config, group: str) -> bool:
        g = c.groups.get(group)
        return tier is None or (g.tier if g is not None else TIER) == tier

    return (
        sum(g.fuel for c in configs.values() for g in c.groups.values() if mine(c, g.name))
        + TRAP_FUEL * sum(1 for c in configs.values() for t in c.traps if mine(c, t.group))
        + sum(f.fuel for c in configs.values() for f in c.fuel_facts if mine(c, f.group))
    )


# A fuel fact's node: `file::function` or `file::Class::function`, with no parameters.
FACT_NODE = re.compile(r"[\w./-]+\.py::\w+(::\w+)?")
# Where a fuel fact's evidence lives: the reviewed trace that measured the dependence.
EVIDENCE_DIRS = ("context/reviews/", "context/research/", "context/specifications/")


def fact_errors(pkg: str, cfg: Config, repo: Path) -> list[str]:
    """A fuel fact names its group, a parametrized test under that group's paths that no other
    entry already takes out, a reason, and evidence in the repository."""
    errors = []
    # A not_selected path becomes `--ignore`, so a folder takes out every file under it.
    taken = [x.rstrip("/") for n in cfg.not_selected for x in n.files]
    for f in cfg.fuel_facts:
        where = f"{pkg}: fuel fact {f.id}"
        if cfg.runner != "pytest":
            errors.append(f"{where}: only a pytest suite has fuel facts")
            continue
        if f.group not in cfg.groups:
            errors.append(f"{where} names no group of its package: {f.group}")
        elif not any(f.file.startswith(p + "/") for p in cfg.groups[f.group].paths):
            errors.append(f"{where}: {f.file} is not under its group's paths")
        if not FACT_NODE.fullmatch(f.node):
            errors.append(f"{where}: node {f.node!r} is not file::function with no parameters")
        cases = f.node + "["  # what the group deselects: a trap on a sibling name does not overlap
        if any(f.file == x or f.file.startswith(x + "/") for x in taken) or any(
            t.node.startswith(cases) or cases.startswith(t.node) for t in cfg.traps
        ):
            errors.append(f"{where}: {f.node} is also left out by a not_selected or trap entry")
        if not f.reason.strip():
            errors.append(f"{where} has no reason")
        if not f.evidence:
            errors.append(f"{where} names no evidence")
        for e in f.evidence:
            if not e.startswith(EVIDENCE_DIRS) or not (repo / e).is_file():
                errors.append(
                    f"{where}: evidence {e} is not a file under context/reviews, "
                    "context/research or context/specifications"
                )
        if f.fuel <= 0:
            errors.append(f"{where}: fuel cap {f.fuel} is not positive")
    return errors


def families(configs: dict[str, Config]) -> dict[str, dict[str, Config]]:
    """The configs by grant: each family shares one stage, one grant and one fuel budget."""
    out: dict[str, dict[str, Config]] = {}
    for p, c in configs.items():
        out.setdefault(c.grant, {})[p] = c
    return out


def rule_errors(
    configs: dict[str, Config],
    gap_checks: set[str],
    *,
    expected_dir: Path = EXPECTED,
    repo: Path = paths.REPO,
    members: dict[str, set[str]] | None = None,
    sources: dict[str, dict[str, str]] | None = None,
    systems_of: dict[str, set[str]] | None = None,
) -> list[str]:
    errors = kit_errors(KIT.read_text()) if KIT.is_file() else ["tests/upstream/kit.txt is missing"]
    groups: set[str] = set()
    names: set[str] = set()
    lists: set[Path] = set()
    for pkg, cfg in configs.items():
        closers = [n.closes_with for n in cfg.not_selected]
        closers += [t.closes_with for t in cfg.traps] + [k.closes_with for k in cfg.expected]
        errors += [
            f"{pkg}: closes_with {c} does not exist" for c in closers if not (repo / c).is_file()
        ]
        for g in cfg.groups:
            if g in names:
                errors.append(f"{pkg}: the name {g} is used twice")
            names.add(g)
            groups.add(g)
        for t in cfg.traps:
            if t.id in names:
                errors.append(f"{pkg}: the name {t.id} is used twice")
            names.add(t.id)
            if trap_node(t.id) not in gap_checks:
                errors.append(f"{pkg}: trap {t.id} has no gap in tests/known_gaps.toml")
        for f in cfg.fuel_facts:
            if f.id in names:
                errors.append(f"{pkg}: the name {f.id} is used twice")
            names.add(f.id)
        errors += fact_errors(pkg, cfg, repo)
        from harness import tiers

        errors += tiers.rule_errors(pkg, cfg, (members or {}).get(pkg))
        seen: set[tuple[str, str]] = set()
        for k in cfg.expected:
            if (k.group, k.id) in seen:
                errors.append(f"{pkg}: class {k.group}-{k.id} is listed twice")
            seen.add((k.group, k.id))
            if k.group not in cfg.groups:
                errors.append(f"{pkg}: class {k.id} names no group of its package: {k.group}")
            if k.outcome not in OUTCOMES:
                errors.append(f"{pkg}: class {k.group}-{k.id}: outcome {k.outcome!r}")
            try:
                re.compile(k.match)
            except re.error as e:
                errors.append(f"{pkg}: class {k.group}-{k.id}: match does not compile: {e}")
            f = list_path(k, expected_dir)
            lists.add(f)
            if not f.is_file():
                errors.append(f"{pkg}: class {k.group}-{k.id} has no list file {f.name}")
                continue
            listed = read_list(f)
            if listed != sorted(set(listed)):
                errors.append(f"{pkg}: {k.group}/{k.id}.txt is not sorted and unique")
            has_gap = class_node(k.group, k.id) in gap_checks
            if listed and not has_gap:
                errors.append(f"{pkg}: class {k.group}-{k.id} has members but no gap")
            if not listed and has_gap:
                errors.append(f"{pkg}: class {k.group}-{k.id} is empty but still has a gap")
        if cfg.driver == "package":
            from harness import packages

            errors += packages.rule_errors(pkg, cfg, (members or {}).get(pkg))
            continue
        if cfg.runner == "regrtest":
            from harness import regrtest

            errors += regrtest.rule_errors(
                cfg,
                gap_checks,
                systems_of=systems_of,
                members=(members or {}).get(pkg),
                sources=(sources or {}).get(pkg),
            )
            continue
        if members is not None and pkg in members:
            have = members[pkg]
            for g in cfg.groups.values():
                errors += [
                    f"{pkg}: group {g.name} path {p} is not a folder of the tarball"
                    for p in g.paths
                    if not any(m.startswith(p + "/") for m in have)
                ]
            files = [f for n in cfg.not_selected for f in n.files] + [t.file for t in cfg.traps]
            files += cfg.support + [f.file for f in cfg.fuel_facts]
            errors += [f"{pkg}: {f} is not a tarball member" for f in files if f not in have]
    if expected_dir.is_dir():
        for f in sorted(expected_dir.rglob("*.txt")):
            if f not in lists:
                errors.append(f"expected/{f.relative_to(expected_dir).as_posix()} names no class")
    from harness import regrtest

    budgets = {GRANT: CAP_BUDGET, regrtest.GRANT: regrtest.CAP_BUDGET}
    # each package family's budget is its own TOML's `budget`, the sum of its caps by
    # the owner's rule (decisions.md, "Every test of every package we build", 2026-10-20)
    budgets |= {c.grant: c.keys.budget for c in configs.values() if c.driver == "package"}
    # numpy's, pandas' and CPython's budgets bound each tier: what every check pays, and what a
    # release run adds; a package family's is the sum of all its caps, both tiers.
    release_budgets = {regrtest.GRANT: regrtest.RELEASE_CAP_BUDGET}
    for grant, family in sorted(families(configs).items()):
        package = any(c.driver == "package" for c in family.values())
        for tier in (None,) if package else TIERS:
            budget = budgets.get(grant, CAP_BUDGET)
            if tier == "release":
                budget = release_budgets.get(grant, budget)
            total = caps(family, tier)
            if total > budget:
                what = f"{tier}-tier " if tier else ""
                errors.append(
                    f"the {grant} family's {what}fuel caps sum to {total:.3g}, over the "
                    f"{budget:.2g} budget"
                )
    return errors


# ---------------------------------------------------------------------------------------------
# The judge run: one stage per run, one guest session per group, cached for the class checks


@dataclass
class GroupRun:
    outcome: GroupOutcome
    fuel: int  # the group's own session: the metric
    left_out: list[str]
    fuel_facts: dict[str, int] = field(default_factory=dict)  # each fact's session


@dataclass
class TrapRun:
    findings: list[str]
    fuel: int


class Session:
    """Stages `/upstream` once per judge run and runs each group once."""

    def __init__(self, workdir: Path, configs: dict[str, Config]) -> None:
        self.workdir = workdir
        self.configs = configs
        self.root: Path | None = None
        self.prepared: dict[str, str | list[str]] = {}  # package -> tie error, or left out
        self.groups: dict[str, GroupRun] = {}

    def close(self) -> None:
        if self.root is not None:
            litter.remove(self.root)  # sealed: unsealed first

    def _stage_root(self) -> Path:
        if self.root is None:
            base = paths.HARNESS_TMP / "upstream"
            base.mkdir(parents=True, exist_ok=True)
            self.root = Path(tempfile.mkdtemp(prefix="run-", dir=base))
            for _, _, name in kit_entries(KIT.read_text()):
                safe_unzip(WHEELS / name, self.root / "kit")
            judge = self.root / "judge"
            judge.mkdir()
            for f in ("drive.py", "numpy.ini", "pandas.ini"):
                shutil.copyfile(HERE / f, judge / f)
        return self.root

    def prepare(self, package: str) -> list[str]:
        """Tie, then stage, one package's tests; an AssertionError when the tie fails."""
        if not self.prepared:
            # Every package with a source tree, in a fixed order, whichever check asks first:
            # the guest's fuel depends on the whole grant (pytest lists its root folder, and the
            # allocations move the collector's timing), so the stage is the same in every run.
            from harness import pins

            for p, c in self.configs.items():
                # the compiled packages' families have stages of their own, never staged into
                # /upstream
                if c.runner == "pytest" and c.driver != "package" and pins.source_pair(p):
                    self.prepared[p] = self._prepare(p)
            if self.root is not None:
                litter.seal(self.root)  # the whole stage, once every package is in
        got = self.prepared.get(package, f"no source tree for {package}")
        if isinstance(got, str):
            raise AssertionError(got)
        return got

    def _prepare(self, package: str) -> str | list[str]:
        from harness import pins

        cfg = self.configs[package]
        pair = pins.source_pair(package)
        assert pair is not None, f"no source tree for {package}"  # the need was met
        tarball, tree = pair
        manifest = paths.parse_manifest((paths.artifact_dir() / "MANIFEST").read_text())
        patches = repo_patches(tree.name)
        errors = tie_errors(package, manifest, tarball, patches)
        if errors:
            return "the tests are not the artifact's: " + "; ".join(errors)
        allowed = tarball_members(tarball)
        for p in patches:
            allowed |= patch_created((paths.REPO / p).read_text())
        root = self._stage_root()
        left_out = stage(cfg, tree, allowed, root / "tests")
        judge = root / "judge"
        for name, spec in judge_specs(cfg).items():
            (judge / f"{name}.json").write_text(json.dumps(spec, indent=1))
        return left_out

    def _run(self, package: str, name: str, fuel: int) -> tuple[Stream, GuestRun]:
        from harness import guest

        d = paths.artifact_dir()
        m = paths.parse_manifest((d / "MANIFEST").read_text())
        r = guest.run(
            d / "python-snapshot.wasm",
            guest_argv(package, name),
            workdir=self.workdir,
            python_version=m.python,
            stdlib=d / "python-stdlib.zip",
            env=ENV,
            fuel=fuel,
            preopens=preopens(self._stage_root()),
            # matplotlib's data, as the runner grants it on every call:
            # without it `import matplotlib` raises NotADirectoryError, which pandas' own
            # `importorskip("matplotlib")` does not catch, so a group would fail to collect.
            mpl_data=_has_mpl_data(d / "python-stdlib.zip"),
        )
        stream_file = r.root / STREAM
        text = stream_file.read_text(errors="replace") if stream_file.is_file() else ""
        tail = r.stderr.decode(errors="replace").strip().splitlines()[-1:] or [""]
        run = GuestRun(r.exit_code, r.trapped, r.trap_cause, r.fuel, r.text, tail[0][:200])
        litter.remove(r.root.parent)  # the run's root and its sealed stdlib folder
        return parse_stream(text), run

    def group(self, package: str, group: str) -> GroupRun:
        """The group's session, then each of its fuel facts', judged as one."""
        if group not in self.groups:
            left_out = self.prepare(package)
            cfg = self.configs[package]
            classes = cfg.classes(group)
            stream, run = self._run(package, group, cfg.groups[group].fuel)
            parts = [(stream, judge_group(stream, run, classes), "")]
            extra: list[str] = []
            facts: dict[str, int] = {}
            for f in cfg.facts(group):
                alone, f_run = self._run(package, f.id, f.fuel)
                parts.append((alone, judge_group(alone, f_run, classes), f"fuel fact {f.id}: "))
                extra += fact_findings(stream, alone, f)
                facts[f.id] = f_run.fuel
            self.groups[group] = GroupRun(combine(parts, extra), run.fuel, left_out, facts)
        return self.groups[group]

    def trap(self, package: str, trap_id: str) -> TrapRun:
        self.prepare(package)
        stream, run = self._run(package, trap_id, TRAP_FUEL)
        node = next(t.node for t in self.configs[package].traps if t.id == trap_id)
        return TrapRun(trap_findings(stream, run, node), run.fuel)
