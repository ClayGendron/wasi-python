"""numpy's and pandas' own tests, run inside the guest (spec 050).

The judge stages the tests of the artifact's own pinned source trees (tarball members, and files a
recorded patch creates, only) with the pinned test kit into one read-only grant, `/upstream`, and
runs pytest in the snapshot binary, one guest session per group. The guest writes an outcome
stream (`tests/upstream/drive.py`); this module reads it, sorts each failure into the class that
admits it, and names everything else as a finding. Each class and each trap is its own check and
an ordinary gap (spec 002); a group admits nothing by itself.
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

from harness import paths

HERE = paths.REPO / "tests" / "upstream"
KIT = HERE / "kit.txt"
EXPECTED = HERE / "expected"
WHEELS = paths.BUILD / "upstream" / "wheels"
CHECKS_FILE = "tests/checks/test_v1_3_upstream_suites.py"
PACKAGES = ("numpy", "pandas")
GRANT = "/upstream"
STREAM = "tmp/upstream/outcomes.txt"  # in the guest's root
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


@dataclass(frozen=True)
class NotSelected:
    files: tuple[str, ...]
    reason: str
    closes_with: str


@dataclass(frozen=True)
class Trap:
    id: str
    node: str  # a node id, a node-id prefix or a file
    reason: str
    closes_with: str

    @property
    def file(self) -> str:
        return self.node.split("::", 1)[0]


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

    def classes(self, group: str) -> list[Klass]:
        return [k for k in self.expected if k.group == group]


def load(package: str, directory: Path = HERE) -> Config:
    raw = tomllib.loads((directory / f"{package}.toml").read_text())
    return Config(
        package=raw["package"],
        marker=raw["marker"],
        args=list(raw.get("args", [])),
        path_packages=list(raw["path_packages"]),
        markers=list(raw.get("markers", [])),
        support=list(raw.get("support", [])),
        groups={
            name: Group(name, tuple(g["paths"]), int(g["fuel"]))
            for name, g in raw.get("groups", {}).items()
        },
        not_selected=[
            NotSelected(tuple(n["files"]), n["reason"], n["closes_with"])
            for n in raw.get("not_selected", [])
        ],
        traps=[
            Trap(t["id"], t["node"], t["reason"], t["closes_with"]) for t in raw.get("trap", [])
        ],
        expected=[
            Klass(e["id"], e["group"], e["outcome"], e["match"], e["reason"], e["closes_with"])
            for e in raw.get("expected", [])
        ],
    )


def load_all(directory: Path = HERE) -> dict[str, Config]:
    return {p: load(p, directory) for p in PACKAGES}


def suite_node(group: str) -> str:
    return f"{CHECKS_FILE}::test_upstream_suite[{group}]"


def class_node(group: str, klass: str) -> str:
    return f"{CHECKS_FILE}::test_upstream_class[{group}-{klass}]"


def trap_node(trap: str) -> str:
    return f"{CHECKS_FILE}::test_upstream_trap[{trap}]"


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
    """Unpack a wheel; refuse an absolute member name or any member with a `..` part (§4.8)."""
    with zipfile.ZipFile(wheel) as z:
        names = z.namelist()
        for name in names:
            parts = re.split(r"[\\/]", name)
            if name.startswith(("/", "\\")) or re.match(r"[A-Za-z]:", name) or ".." in parts:
                raise ValueError(f"{wheel.name}: member {name!r} refused (outside its folder)")
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
}


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
    top = tarball.name.removesuffix(".tar.gz")
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
            (wanted.add if rel in allowed else left_out.append)(rel)
        for anc in _ancestors(folder + "/x"):
            wanted |= {f"{anc}/__init__.py", f"{anc}/conftest.py"} & allowed
    for rel in sorted(wanted):
        if rel not in allowed or not (tree / rel).is_file():
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(tree / rel, target)
    return sorted(left_out)


def preopens(stage_root: Path) -> list[tuple[str, Path, bool]]:
    """The one grant every group and trap check gets: the stage, read-only, at /upstream."""
    return [(GRANT, stage_root, False)]


# ---------------------------------------------------------------------------------------------
# The argv (Decisions 5, 7, 8, 9)


def _abs(rel: str) -> str:
    return f"{GRANT}/tests/{rel}"


def group_spec(cfg: Config, group: Group) -> dict:
    inside = [p + "/" for p in group.paths]
    mine = lambda f: any(f.startswith(p) for p in inside)  # noqa: E731
    ignores = [f for n in cfg.not_selected for f in n.files if mine(f)]
    ignores += [t.node for t in cfg.traps if "::" not in t.node and mine(t.node)]
    deselects = [t.node for t in cfg.traps if "::" in t.node and mine(t.node)]
    return {
        "path_packages": cfg.path_packages,
        "markers": cfg.markers,
        "args": [
            "-m",
            cfg.marker,
            *cfg.args,
            *[_abs(p) for p in group.paths],
            *[f"--ignore={_abs(f)}" for f in dict.fromkeys(ignores)],
            *[f"--deselect={d}" for d in deselects],
        ],
    }


def trap_spec(cfg: Config, trap: Trap) -> dict:
    """The entry alone, with no marker: whatever it names runs."""
    return {
        "path_packages": cfg.path_packages,
        "markers": cfg.markers,
        "args": [*cfg.args, _abs(trap.node)],
    }


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


def parse_stream(text: str) -> Stream:
    s = Stream()
    current = None
    for line in text.splitlines():
        kind, _, rest = line.partition(" ")
        if kind == "C":
            s.open_node = rest
        elif kind == "S":
            s.open_node = current = rest
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


def trap_findings(stream: Stream, run: GuestRun) -> list[str]:
    """A trap check's findings: the trap (or fuel) that ended the entry's session, if any."""
    return _ended(stream, run) if run.trapped else []


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


def class_findings(actual: list[str], listed: list[str]) -> list[str]:
    """One finding per member, plus `+id` for each not in the list and `-id` for each listed but
    gone; none when the class is empty (its gap then says "remove the gap"; condition C1)."""
    if not actual:
        return []
    now, was = sorted(set(actual)), set(listed)
    return now + [f"+{n}" for n in now if n not in was] + [f"-{n}" for n in sorted(was - set(now))]


# ---------------------------------------------------------------------------------------------
# The rules (Decision 17)


def caps(configs: dict[str, Config]) -> int:
    return sum(g.fuel for c in configs.values() for g in c.groups.values()) + TRAP_FUEL * sum(
        len(c.traps) for c in configs.values()
    )


def rule_errors(
    configs: dict[str, Config],
    gap_checks: set[str],
    *,
    expected_dir: Path = EXPECTED,
    repo: Path = paths.REPO,
    members: dict[str, set[str]] | None = None,
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
        if members is not None and pkg in members:
            have = members[pkg]
            for g in cfg.groups.values():
                errors += [
                    f"{pkg}: group {g.name} path {p} is not a folder of the tarball"
                    for p in g.paths
                    if not any(m.startswith(p + "/") for m in have)
                ]
            files = [f for n in cfg.not_selected for f in n.files] + [t.file for t in cfg.traps]
            files += cfg.support
            errors += [f"{pkg}: {f} is not a tarball member" for f in files if f not in have]
    if expected_dir.is_dir():
        for f in sorted(expected_dir.rglob("*.txt")):
            if f not in lists:
                errors.append(f"expected/{f.relative_to(expected_dir).as_posix()} names no class")
    total = caps(configs)
    if total > CAP_BUDGET:
        errors.append(f"the fuel caps sum to {total:.3g}, over the {CAP_BUDGET:.0e} budget")
    return errors


# ---------------------------------------------------------------------------------------------
# The judge run: one stage per run, one guest session per group, cached for the class checks


@dataclass
class GroupRun:
    outcome: GroupOutcome
    fuel: int
    left_out: list[str]


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
            shutil.rmtree(self.root, ignore_errors=True)

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

            for p in self.configs:
                if pins.source_pair(p) is not None:
                    self.prepared[p] = self._prepare(p)
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
        for g in cfg.groups.values():
            (judge / f"{g.name}.json").write_text(json.dumps(group_spec(cfg, g), indent=1))
        for t in cfg.traps:
            (judge / f"{t.id}.json").write_text(json.dumps(trap_spec(cfg, t), indent=1))
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
        )
        stream_file = r.root / STREAM
        text = stream_file.read_text(errors="replace") if stream_file.is_file() else ""
        tail = r.stderr.decode(errors="replace").strip().splitlines()[-1:] or [""]
        run = GuestRun(r.exit_code, r.trapped, r.trap_cause, r.fuel, r.text, tail[0][:200])
        shutil.rmtree(r.root.parent, ignore_errors=True)  # the run's root: pytest's temp files
        return parse_stream(text), run

    def group(self, package: str, group: str) -> GroupRun:
        if group not in self.groups:
            left_out = self.prepare(package)
            cfg = self.configs[package]
            stream, run = self._run(package, group, cfg.groups[group].fuel)
            outcome = judge_group(stream, run, cfg.classes(group))
            self.groups[group] = GroupRun(outcome, run.fuel, left_out)
        return self.groups[group]

    def trap(self, package: str, trap_id: str) -> TrapRun:
        self.prepare(package)
        stream, run = self._run(package, trap_id, TRAP_FUEL)
        return TrapRun(trap_findings(stream, run), run.fuel)
