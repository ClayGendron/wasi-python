"""The compiled packages' own tests, each package its own family.

A `driver = "package"` configuration (`tests/upstream/<package>.toml`) has its own grant
(`/upstream-<package>`), its own stage, its own copy of the kit and its own fuel budget, so no
package's tests can move another's fuel. Its groups run through
`tests/upstream/package_drive.py`, which keeps `drive.py`'s stream and adds three lines: `R skipped
<collector>` for a file that skips itself whole, `D <node id>` for an item lxml's own runner would
not run, and `K <n>`, the file's collected count before a split's `-k` deselects.

numpy's and pandas' configurations, `drive.py` and their guard are untouched: this module reads
only `driver = "package"` configurations.
"""

from __future__ import annotations

import ast
import json
import shutil
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from harness import litter, paths, upstream

DRIVER = "package_drive.py"
# numpy's and pandas' keys, with their meaning there: never in a package TOML (Decision 14)
REFUSED = ("path_packages", "support")
WORK = "/tmp/work"  # the writable working folder, in the guest's root


@dataclass(frozen=True)
class Split:
    """One file too big for one group, split by construction: group i runs
    `-k "(e_i) and not (e_1 or ... or e_{i-1})"`, the last `-k "not (e_1 or ... or e_{n-1})"`."""

    file: str
    groups: tuple[str, ...]
    keywords: tuple[str, ...]

    def keyword(self, group: str) -> str:
        i = self.groups.index(group)
        earlier = " or ".join(f"({k})" for k in self.keywords[:i])
        if i == len(self.groups) - 1:
            return f"not ({earlier})"
        mine = f"({self.keywords[i]})"
        return f"{mine} and not ({earlier})" if earlier else mine


@dataclass(frozen=True)
class PackageKeys:
    budget: int
    stage_folders: tuple[str, ...]
    support_files: tuple[str, ...] = ()
    package_paths: dict[str, str] = field(default_factory=dict)
    extra_sys_path: tuple[str, ...] = ()
    support_packages: tuple[str, ...] = ()
    cwd: str = WORK
    cwd_files: tuple[str, ...] = ()
    splits: tuple[Split, ...] = ()
    keep_from_test_suite: bool = False  # lxml: run only what each module's test_suite() runs
    doctest_files: tuple[tuple[str, int], ...] = ()
    doctest_preimport: tuple[str, ...] = ()
    docstring_modules: tuple[str, ...] = ()
    docstring_not_selected: tuple[str, ...] = ()  # e.g. lxml.cssselect: cssselect is not shipped
    measured: dict[str, int] = field(default_factory=dict)  # each group's recorded fuel
    refused: tuple[str, ...] = ()  # keys a package TOML may not carry (path_packages, support)

    def split_of(self, group: str) -> Split | None:
        return next((s for s in self.splits if group in s.groups), None)


def load(raw: dict) -> upstream.Config:
    keys = PackageKeys(
        budget=int(raw["budget"]),
        stage_folders=tuple(raw["stage_folders"]),
        support_files=tuple(raw.get("support_files", [])),
        package_paths=dict(raw.get("package_paths", {})),
        extra_sys_path=tuple(raw.get("extra_sys_path", [])),
        support_packages=tuple(raw.get("support_packages", [])),
        cwd=raw.get("cwd", WORK),
        cwd_files=tuple(raw.get("cwd_files", [])),
        splits=tuple(
            Split(s["file"], tuple(s["groups"]), tuple(s["keywords"])) for s in raw.get("split", [])
        ),
        keep_from_test_suite=bool(raw.get("keep_from_test_suite", False)),
        doctest_files=tuple((f, int(flags)) for f, flags in raw.get("doctest_files", [])),
        doctest_preimport=tuple(raw.get("doctest_preimport", [])),
        docstring_modules=tuple(raw.get("docstring_modules", [])),
        docstring_not_selected=tuple(raw.get("docstring_not_selected", [])),
        measured={
            n: int(g["measured"]) for n, g in raw.get("groups", {}).items() if "measured" in g
        },
        refused=tuple(k for k in REFUSED if k in raw),
    )
    return upstream.Config(
        package=raw["package"],
        marker=raw.get("marker", ""),
        args=list(raw.get("args", [])),
        path_packages=[],
        markers=list(raw.get("markers", [])),
        support=[],
        groups={
            name: upstream.Group(
                name, tuple(g["paths"]), int(g["fuel"]), tier=g.get("tier", upstream.TIER)
            )
            for name, g in raw.get("groups", {}).items()
        },
        not_selected=[
            upstream.NotSelected(tuple(n["files"]), n["reason"], n["closes_with"])
            for n in raw.get("not_selected", [])
        ],
        traps=[
            upstream.Trap(t["id"], t["node"], t["reason"], t["closes_with"])
            for t in raw.get("trap", [])
        ],
        expected=[
            upstream.Klass(
                e["id"], e["group"], e["outcome"], e["match"], e["reason"], e["closes_with"]
            )
            for e in raw.get("expected", [])
        ],
        grant=raw["grant"],
        driver="package",
        keys=keys,
    )


def tree_root(cfg: upstream.Config) -> str:
    return f"{cfg.grant}/tree"


def guest_cwd(cfg: upstream.Config) -> str:
    """`/tmp/work`, or the stage's tree root when the TOML says `cwd = "tree"`."""
    return tree_root(cfg) if cfg.keys.cwd == "tree" else cfg.keys.cwd


# ---------------------------------------------------------------------------------------------
# lxml: what each module's test_suite() runs

LOADERS = ("loadTestsFromTestCase", "makeSuite")


def test_suite_classes(source: str) -> list[str] | str | None:
    """The TestCase classes a module's test_suite() adds: their names, "*" when it loads the whole
    module (`loadTestsFromModule`), None when it has no test_suite()."""
    mod = ast.parse(source)
    fn = next(
        (n for n in mod.body if isinstance(n, ast.FunctionDef) and n.name == "test_suite"), None
    )
    if fn is None:
        return None
    names: set[str] = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in LOADERS and node.args and isinstance(node.args[0], ast.Name):
                names.add(node.args[0].id)
            elif node.func.attr == "loadTestsFromModule":
                return "*"
    return sorted(names)


def test_suite_doctests(source: str) -> tuple[list[str], int]:
    """The doctest files (basenames) a module's test_suite() names, and how many docstring suites
    (`DocTestSuite`) it adds."""
    mod = ast.parse(source)
    fn = next(
        (n for n in mod.body if isinstance(n, ast.FunctionDef) and n.name == "test_suite"), None
    )
    files: list[str] = []
    docstrings = 0
    for node in ast.walk(fn) if fn else []:
        if not isinstance(node, ast.Call):
            continue
        name = (
            node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
        )
        first = node.args[0] if node.args else None
        if name in ("make_doctest", "DocFileSuite") and isinstance(first, ast.Constant):
            files.append(PurePosixPath(str(first.value)).name)
        elif name == "DocTestSuite":
            docstrings += 1
    return files, docstrings


def keep_classes(cfg: upstream.Config, tree: Path) -> dict[str, list[str] | str]:
    """For each staged test module the groups run, the classes its test_suite() adds."""
    if not cfg.keys.keep_from_test_suite:
        return {}
    out: dict[str, list[str] | str] = {}
    out_files = {f for n in cfg.not_selected for f in n.files}
    for folder in cfg.keys.stage_folders:
        for p in sorted((tree / folder).glob("test_*.py")):
            rel = p.relative_to(tree).as_posix()
            if rel in out_files:
                continue
            got = test_suite_classes(p.read_text(encoding="utf-8"))
            if got is not None:
                out[rel] = got
    return out


# ---------------------------------------------------------------------------------------------
# Staging and the argv


def stage(cfg: upstream.Config, tree: Path, allowed: set[str], dest: Path) -> list[str]:
    """Copy the stage folders and the support files from `tree` to `dest/tree`, members (and
    files a recorded patch creates) only. Returns what was left out."""
    wanted: set[str] = set(cfg.keys.support_files) | {f for f, _ in cfg.keys.doctest_files}
    left_out: list[str] = []
    for folder in cfg.keys.stage_folders:
        for p in sorted((tree / folder).rglob("*")):
            if p.is_dir():
                continue
            rel = p.relative_to(tree).as_posix()
            if rel in allowed:
                wanted.add(rel)
            elif not litter.unrecorded(rel):  # no fact holds litter or bytecode
                left_out.append(rel)
    for rel in sorted(wanted):
        if rel not in allowed or not (tree / rel).is_file():
            continue
        litter.refuse(rel, tree.name)  # the seal's cleanup must never meet it
        target = dest / "tree" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(tree / rel, target)
    return sorted(left_out)


def group_args(cfg: upstream.Config, group: upstream.Group) -> list[str]:
    """pytest's selection for one group. The host makes every path absolute under the grant's tree
    and leaves every other argument as it is: a marker or an option's value is never a path.
    `--deselect` takes a node id, relative to the rootdir (the tree)."""
    root = tree_root(cfg) + "/"
    inside = [p if p.endswith(".py") else p + "/" for p in group.paths]
    mine = lambda f: any(f == p or f.startswith(p) for p in inside)  # noqa: E731
    out = [f for n in cfg.not_selected for f in n.files if mine(f.split("::", 1)[0])]
    ignores = [f for f in out if "::" not in f]  # a file
    deselects = [f for f in out if "::" in f]  # one test by node id (regex's test_main)
    deselects += [t.node for t in cfg.traps if "::" in t.node and mine(t.node)]
    args = ["-m", cfg.marker] if cfg.marker else []
    args += [*cfg.args, *(root + p for p in group.paths)]
    args += [f"--ignore={root}{f}" for f in dict.fromkeys(ignores)]
    args += [f"--deselect={d}" for d in deselects]
    split = cfg.keys.split_of(group.name)
    if split is not None:
        args.append(f"-k{split.keyword(group.name)}")
    return args


def group_spec(
    cfg: upstream.Config, group: upstream.Group, keep: dict, top_names: list[str]
) -> dict:
    k = cfg.keys
    return {
        "markers": cfg.markers,
        "args": group_args(cfg, group),
        "package_paths": k.package_paths,
        "extra_sys_path": list(k.extra_sys_path),
        "cwd": guest_cwd(cfg),
        "keep_classes": keep or None,
        "doctest_files": [[f, flags] for f, flags in k.doctest_files],
        "doctest_preimport": list(k.doctest_preimport),
        "docstring_modules": list(k.docstring_modules),
        "top_names": top_names,
        "split": cfg.keys.split_of(group.name) is not None,
    }


def zip_top_names(stdlib: Path) -> list[str]:
    with zipfile.ZipFile(stdlib) as z:
        return sorted({n.split("/")[0].removesuffix(".pyc") for n in z.namelist() if n.strip("/")})


# ---------------------------------------------------------------------------------------------
# The verdict: the shared judge, then this driver's guard and lines


@dataclass
class Extra:
    deselected: list[str] = field(default_factory=list)  # D lines
    collected: int | None = None  # K line


def parse_extra(text: str) -> Extra:
    e = Extra()
    for line in text.splitlines():
        kind, _, rest = line.partition(" ")
        if kind == "D":
            e.deselected.append(rest)
        elif kind == "K":
            try:
                e.collected = int(rest)
            except ValueError:
                e.collected = -1
    return e


def guard_findings(cfg: upstream.Config, modules: list[tuple[str, str]]) -> list[str]:
    """Path-based: a module loaded from the tree must lie under a staged
    folder; a module of the product's names reported from outside the zip is a finding."""
    root = tree_root(cfg) + "/"
    folders = [root + f.rstrip("/") + "/" for f in cfg.keys.stage_folders]
    files = {
        root + f for f in cfg.keys.support_files
    }  # e.g. Pillow's selftest.py, run by docstring
    findings = []
    for name, f in modules:
        if f.startswith(root):
            if not any(f.startswith(d) for d in folders) and f not in files:
                findings.append(f"a module came from outside the staged folders: {name} {f}")
        else:
            findings.append(f"a product module came from outside the zip: {name} {f}")
    return findings


def _added(listed, node: str) -> bool:
    """Whether a node of a module with a test_suite() is one it adds: a test of a class it names,
    or of any class when it loads the whole module ("*"); never a module-level function."""
    parts = node.split("::")
    if len(parts) < 3:
        return False
    return listed == "*" or parts[1] in listed


def keep_findings(extra: Extra, stream: upstream.Stream, keep: dict) -> list[str]:
    """lxml, exactly test_suite()'s tests: every class
    it names ran at least one test; every test that ran is one it adds; every item deselected is
    one it does not add (its own `test_suite` builder among them)."""
    if not keep:
        return []
    findings = []
    ran = list(stream.started)
    for f, classes in keep.items():
        if classes == "*":
            continue
        for c in classes:
            if not any(n.startswith(f"{f}::{c}::") for n in ran):
                findings.append(f"a class lxml's test_suite() runs ran nothing: {f}::{c}")
    for node in dict.fromkeys(n for _, n, _ in stream.outcomes):  # tests, not collectors
        listed = keep.get(node.split("::", 1)[0])
        if listed is not None and "::" in node and not _added(listed, node):
            findings.append(f"ran a test lxml's test_suite() does not add: {node}")
    for node in extra.deselected:
        listed = keep.get(node.split("::", 1)[0])
        if listed is not None and _added(listed, node):
            findings.append(f"deselected a test lxml's test_suite() runs: {node}")
    return findings


def judge(
    cfg: upstream.Config, group: str, text: str, run: upstream.GuestRun, keep: dict
) -> tuple[upstream.GroupOutcome, Extra]:
    stream = upstream.parse_stream(text)
    extra = parse_extra(text)
    modules, stream.modules = stream.modules, []  # this driver's guard, not drive.py's
    outcome = upstream.judge_group(stream, run, cfg.classes(group))
    outcome.findings += guard_findings(cfg, modules)
    outcome.findings += keep_findings(extra, stream, keep)
    if cfg.keys.split_of(group) is not None and extra.collected is None:
        outcome.findings.append("no K line: the split group's file was not collected")
    return outcome, extra


# ---------------------------------------------------------------------------------------------
# The session: one stage per family, one guest session per group


@dataclass
class PackageRun:
    outcome: upstream.GroupOutcome
    fuel: int
    left_out: list[str]
    collected: int | None


class Session:
    """Stages each family once per judge run, on first use, and runs each group once."""

    def __init__(self, workdir: Path, configs: dict[str, upstream.Config]) -> None:
        self.workdir = workdir
        self.configs = {p: c for p, c in configs.items() if c.driver == "package"}
        self.roots: dict[str, Path] = {}
        self.prepared: dict[str, str | tuple[list[str], dict]] = {}
        self.groups: dict[str, PackageRun] = {}

    def close(self) -> None:
        for root in self.roots.values():
            litter.remove(root)

    def prepare(self, package: str) -> tuple[list[str], dict]:
        if package not in self.prepared:
            self.prepared[package] = self._prepare(package)
        got = self.prepared[package]
        if isinstance(got, str):
            raise AssertionError(got)
        return got

    def _prepare(self, package: str) -> str | tuple[list[str], dict]:
        from harness import pins

        cfg = self.configs[package]
        pair = pins.source_pair(package)
        if pair is None:
            return f"no source tree for {package}"
        tarball, tree = pair
        d = paths.artifact_dir()
        manifest = paths.parse_manifest((d / "MANIFEST").read_text())
        patches = upstream.repo_patches(tree.name)
        errors = upstream.tie_errors(package, manifest, tarball, patches)
        if errors:
            return "the tests are not the artifact's: " + "; ".join(errors)
        allowed = upstream.tarball_members(tarball)
        for p in patches:
            allowed |= upstream.patch_created((paths.REPO / p).read_text())
        base = paths.HARNESS_TMP / f"upstream-{package}"
        base.mkdir(parents=True, exist_ok=True)
        root = Path(tempfile.mkdtemp(prefix="run-", dir=base))
        self.roots[package] = root
        for _, _, name in upstream.kit_entries(upstream.KIT.read_text()):
            upstream.safe_unzip(upstream.WHEELS / name, root / "kit")
        judge_dir = root / "judge"
        judge_dir.mkdir()
        shutil.copyfile(upstream.HERE / DRIVER, judge_dir / DRIVER)
        shutil.copyfile(upstream.HERE / f"{package}.ini", judge_dir / f"{package}.ini")
        left_out = stage(cfg, tree, allowed, root)
        keep = keep_classes(cfg, root / "tree")
        top = zip_top_names(d / "python-stdlib.zip")
        for g in cfg.groups.values():
            spec = group_spec(cfg, g, keep, top)
            (judge_dir / f"{g.name}.json").write_text(json.dumps(spec, indent=1))
        for t in cfg.traps:
            spec = {**group_spec(cfg, cfg.groups[next(iter(cfg.groups))], keep, top)}
            spec["args"], spec["split"] = [*cfg.args, t.node], False
            (judge_dir / f"{t.id}.json").write_text(json.dumps(spec, indent=1))
        litter.seal(root)  # read-only, once staged
        return left_out, keep

    def _files(self, package: str) -> dict[str, bytes] | None:
        from harness import pins

        cfg = self.configs[package]
        if not cfg.keys.cwd_files:
            return None
        pair = pins.source_pair(package)
        assert pair is not None
        tree = pair[1]
        return {f"{WORK}/{rel}": (tree / rel).read_bytes() for rel in cfg.keys.cwd_files}

    def _run(self, package: str, name: str, fuel: int) -> tuple[str, upstream.GuestRun]:
        from harness import guest

        cfg = self.configs[package]
        d = paths.artifact_dir()
        m = paths.parse_manifest((d / "MANIFEST").read_text())
        r = guest.run(
            d / "python-snapshot.wasm",
            ["-u", f"{cfg.grant}/judge/{DRIVER}", package, name],
            workdir=self.workdir,
            python_version=m.python,
            stdlib=d / "python-stdlib.zip",
            files=self._files(package),
            env=upstream.ENV,
            fuel=fuel,
            preopens=[(cfg.grant, self.roots[package], False)],
            mpl_data=upstream._has_mpl_data(d / "python-stdlib.zip"),
        )
        stream_file = r.root / upstream.STREAM
        text = stream_file.read_text(errors="replace") if stream_file.is_file() else ""
        kept = paths.HARNESS_TMP / "streams"  # the whole stream, for reading a failure in full
        kept.mkdir(parents=True, exist_ok=True)
        (kept / f"{package}-{name}.txt").write_text(text)
        tail = r.stderr.decode(errors="replace").strip().splitlines()[-1:] or [""]
        run = upstream.GuestRun(r.exit_code, r.trapped, r.trap_cause, r.fuel, r.text, tail[0][:200])
        litter.remove(r.root.parent)  # the run's root and its sealed stdlib folder
        return text, run

    def group(self, package: str, group: str) -> PackageRun:
        if group not in self.groups:
            left_out, keep = self.prepare(package)
            cfg = self.configs[package]
            text, run = self._run(package, group, cfg.groups[group].fuel)
            outcome, extra = judge(cfg, group, text, run, keep)
            outcome.findings += self._split_findings(cfg, group, extra.collected)
            self.groups[group] = PackageRun(outcome, run.fuel, left_out, extra.collected)
        return self.groups[group]

    def _split_findings(self, cfg: upstream.Config, group: str, collected: int | None) -> list[str]:
        """Every group of a split collected the same file: a count unequal to an earlier group's
        of the same split in this judge run is red."""
        split = cfg.keys.split_of(group)
        if split is None or collected is None:
            return []
        for other in split.groups:
            seen = self.groups.get(other)
            if seen is not None and seen.collected is not None and seen.collected != collected:
                return [
                    f"{split.file}: collected {collected} tests here, {seen.collected} in {other}"
                ]
        return []

    def trap(self, package: str, trap_id: str) -> upstream.TrapRun:
        self.prepare(package)
        text, run = self._run(package, trap_id, upstream.TRAP_FUEL)
        node = next(t.node for t in self.configs[package].traps if t.id == trap_id)
        return upstream.TrapRun(
            upstream.trap_findings(upstream.parse_stream(text), run, node), run.fuel
        )


# ---------------------------------------------------------------------------------------------
# The rules


def _keyword_errors(expr: str) -> str | None:
    """Why pytest's own parser refuses a -k expression, or None."""
    try:
        from _pytest.mark.expression import Expression

        Expression.compile(expr)
    except Exception as e:  # noqa: BLE001 (pytest's ParseError, whatever its module)
        return str(e).splitlines()[0]
    return None


def split_errors(pkg: str, cfg: upstream.Config) -> list[str]:
    errors = []
    seen: set[str] = set()
    for s in cfg.keys.splits:
        where = f"{pkg}: split of {s.file}"
        if len(s.groups) < 2:
            errors.append(f"{where}: fewer than two groups")
        if len(s.keywords) != len(s.groups) - 1:
            errors.append(f"{where}: {len(s.keywords)} expressions for {len(s.groups)} groups")
        for k in s.keywords:
            if not k.strip():
                errors.append(f"{where}: an empty expression")
            elif (why := _keyword_errors(k)) is not None:
                errors.append(f"{where}: expression {k!r} does not parse: {why}")
        for g in s.groups:
            if g in seen:
                errors.append(f"{where}: group {g} is in two splits")
            seen.add(g)
            if g not in cfg.groups:
                errors.append(f"{where}: names no group of its package: {g}")
            elif cfg.groups[g].paths != (s.file,):
                errors.append(f"{where}: group {g}'s paths are not exactly its file")
    return errors


def rule_cap(measured: int) -> int:
    """1.5 times a group's recorded fuel, rounded up to two significant figures: the owner's rule
    (decisions.md, "Every test of every package we build", 2026-10-20)."""
    x = 3 * measured // 2 + (3 * measured % 2 > 0)
    step = 10 ** max(len(str(x)) - 2, 0)
    return -(-x // step) * step


def rule_errors(pkg: str, cfg: upstream.Config, members: set[str] | None) -> list[str]:
    k = cfg.keys
    errors = [f"{pkg}: a package TOML may not carry {key} (Decision 14)" for key in k.refused]
    for g in cfg.groups.values():
        m = k.measured.get(g.name)
        if m is None:
            errors.append(f"{pkg}: group {g.name} records no measured fuel")
        elif g.fuel > rule_cap(m):
            errors.append(
                f"{pkg}: group {g.name}'s cap {g.fuel:,} is above 1.5 times its measured "
                f"{m:,} ({rule_cap(m):,})"
            )
    if cfg.grant != f"/upstream-{pkg}":
        errors.append(f"{pkg}: grant {cfg.grant} is not /upstream-{pkg}")
    if k.cwd not in (WORK, "tree"):
        errors.append(f"{pkg}: cwd {k.cwd!r} is neither {WORK} nor the tree root")
    if k.cwd_files and k.cwd != WORK:
        errors.append(f"{pkg}: cwd_files need cwd = {WORK!r}")
    for folder in k.support_packages:
        if folder not in k.stage_folders:
            errors.append(f"{pkg}: support package {folder} is not a stage folder")
    for g in cfg.groups.values():
        for p in g.paths:
            if not any(p == f or p.startswith(f.rstrip("/") + "/") for f in k.stage_folders):
                errors.append(f"{pkg}: group {g.name} path {p} is not under a stage folder")
    errors += split_errors(pkg, cfg)
    caps = sum(g.fuel for g in cfg.groups.values()) + upstream.TRAP_FUEL * len(cfg.traps)
    if caps > k.budget:
        errors.append(f"{pkg}: caps {caps:.3g} over the family's budget {k.budget:.3g}")
    if members is not None:

        def folder_ok(f: str) -> bool:
            return any(m.startswith(f.rstrip("/") + "/") for m in members)

        for f in [*k.stage_folders, *k.extra_sys_path, *k.package_paths.values()]:
            if f != "." and not folder_ok(f):
                errors.append(f"{pkg}: {f} is not a folder of the tarball")
        files = [*k.support_files, *k.cwd_files, *(f for f, _ in k.doctest_files)]
        files += [f.split("::", 1)[0] for n in cfg.not_selected for f in n.files]
        files += [p for g in cfg.groups.values() for p in g.paths if p.endswith(".py")]
        errors += [f"{pkg}: {f} is not a tarball member" for f in files if f not in members]
    return errors


def lxml_errors(configs: dict[str, upstream.Config], members: set[str] | None) -> list[str]:
    """lxml's selection is its own runner's, read statically from the
    tarball: the doctest files the selected modules' test_suite() functions name are exactly the
    configuration's, and their docstring suites are as many as it runs or names as left out."""
    from harness import pins

    cfg = configs.get("lxml")
    pair = pins.source_pair("lxml")
    if cfg is None or cfg.driver != "package" or pair is None or members is None:
        return []
    import tarfile

    k = cfg.keys
    out_files = {f for n in cfg.not_selected for f in n.files}
    named: set[str] = set()
    suites = 0
    with tarfile.open(pair[0]) as tar:
        top = tar.getmembers()[0].name.split("/")[0]
        for folder in k.stage_folders:
            for rel in sorted(m for m in members if m.startswith(folder + "/test_")):
                if not rel.endswith(".py") or "/" in rel[len(folder) + 1 :] or rel in out_files:
                    continue
                source = tar.extractfile(f"{top}/{rel}").read().decode("utf-8")
                files, docstrings = test_suite_doctests(source)
                named |= set(files)
                suites += docstrings
    declared = {PurePosixPath(f).name for f, _ in k.doctest_files}
    errors = [
        f"lxml: test_suite() names doctest file {f}, not configured"
        for f in sorted(named - declared)
    ]
    errors += [
        f"lxml: doctest file {f} is named by no selected test_suite()"
        for f in sorted(declared - named)
    ]
    want = len(k.docstring_modules) + len(k.docstring_not_selected)
    if suites != want:
        errors.append(
            f"lxml: the selected test_suite() functions add {suites} docstring suites; the "
            f"configuration runs or leaves out {want}"
        )
    return errors
