"""Where things are, and what the harness reads from the artifact directory (spec 002, Decision 12).

The artifact directory is `$WASI_PYTHON_ARTIFACTS` when it is set, and nothing else; otherwise
build/artifacts/ when it holds a MANIFEST (what scripts/build.sh writes: spec 003, Decision 10);
otherwise the wheel's `wasi_python._artifacts._ARTIFACT_DIR` when it holds one; otherwise there is
none.
"""

from __future__ import annotations

import hashlib
import io
import os
import re
import subprocess
import tarfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BUILD = REPO / "build"
DOWNLOADS = REPO / "downloads"
PIN_LIST = DOWNLOADS / "SHA256SUMS"
DIST = REPO / "dist"
CONTEXT = REPO / "context"
PRIOR_ART = CONTEXT / "prior_art"
PROGRESS = CONTEXT / "progress"
ACCEPTED = PROGRESS / "accepted.json"
HISTORY = PROGRESS / "history.jsonl"
LATEST = BUILD / "progress" / "latest.json"
HARNESS_TMP = BUILD / "harness"
REFERENCE_BUILD = BUILD / "brett-3.14.7"
EMBEDDERS = CONTEXT / "embedders.txt"
KNOWN_GAPS = REPO / "tests" / "known_gaps.toml"
README = REPO / "README.md"

ARTIFACTS_ENV = "WASI_PYTHON_ARTIFACTS"
ARTIFACT_FILES = (
    "python.wasm",
    "python-snapshot.wasm",
    "python-stdlib.zip",
    "MANIFEST",
    "SHA256SUMS",
)
LICENCE_COMPONENTS = (
    "cpython",
    "numpy",
    "pandas",
    "zlib",
    "bzip2",
    "xz",
    "sqlite",  # public domain: its tarball has no licence file, so its blessing is checked
    "python-dateutil",
    "tzdata",
    "six",
    "wasi-libc",
    "llvm-runtimes",
    "regex",  # spec 047, Decision 10
    # matplotlib (spec 023, Decision 9)
    "matplotlib",
    "pillow",
    "kiwisolver",
    "freetype",
    "harfbuzz",
    "sheenbidi",
    "libraqm",
    "pybind11",
    "cppy",
    "cycler",
    "pyparsing",
    "packaging",
    "fonttools",
    # matplotlib's second milestone (spec 043, Decision 11): contourpy, whose notice carries
    # LICENSE_YORICK for its GIST-derived code, and qhull, now linked
    "contourpy",
    "qhull",
    # lxml (spec 046, Decision 15)
    "libxml2",
    "libxslt",
    "lxml",
    # tier A (spec 039, Decision 8)
    "openpyxl",
    "et-xmlfile",
    "xlsxwriter",
    "xlrd",
    "pypdf",
    "beautifulsoup4",
    "soupsieve",
    "html5lib",
    "webencodings",
    "defusedxml",
    "xmltodict",
    "pyyaml",
    "tomli-w",
    "jinja2",
    "markupsafe",
    "tabulate",
    "charset-normalizer",
    "networkx",
    "patsy",
    "sympy",
    "mpmath",
    "attrs",
    "more-itertools",
    "toolz",
    "tqdm",
    "typing-extensions",
    "joblib",
    "cloudpickle",
    "threadpoolctl",
    "narwhals",
    # scipy (spec 037, Decision 13)
    "scipy",
    "openblas",
    # scikit-learn (spec 044, Decision 11)
    "scikit-learn",
    # seaborn and reportlab (spec 042, Decision 7): seaborn's notice carries its five vendored
    # licences, reportlab's its three third-party parts (their own checks hold both)
    "seaborn",
    "reportlab",
)
# SQLite's package line is named as its pin names it (sqlite-autoconf 3540100 is SQLite 3.54.1).
PACKAGES = (
    "numpy",
    "pandas",
    "zlib",
    "bzip2",
    "xz",
    "sqlite-autoconf",
    "python-dateutil",
    "tzdata",
    "six",
    "regex",
    "matplotlib",
    "pillow",
    "kiwisolver",
    "freetype",
    "harfbuzz",
    "sheenbidi",
    "libraqm",
    "pybind11",
    "cppy",
    "cycler",
    "pyparsing",
    "packaging",
    "fonttools",
    "contourpy",
    "qhull",
    "libxml2",
    "libxslt",
    "lxml",
    "openpyxl",
    "et-xmlfile",
    "xlsxwriter",
    "xlrd",
    "pypdf",
    "beautifulsoup4",
    "soupsieve",
    "html5lib",
    "webencodings",
    "defusedxml",
    "xmltodict",
    "pyyaml",
    "tomli-w",
    "jinja2",
    "markupsafe",
    "tabulate",
    "charset-normalizer",
    "networkx",
    "patsy",
    "sympy",
    "mpmath",
    "attrs",
    "more-itertools",
    "toolz",
    "tqdm",
    "typing-extensions",
    "joblib",
    "cloudpickle",
    "threadpoolctl",
    "narwhals",
    "scipy",
    "openblas",
    "scikit-learn",
    "seaborn",  # spec 042
    "reportlab",
)

# What the snapshot pre-imports (recipes/reactor_main.c, PREIMPORT): the stdlib's bootstrap, no
# package, for every package now and later (decision 34, spec 069). Changing it is a judge change.
PREIMPORT = ("encodings", "io", "os", "sys", "json", "csv", "re", "_colorize")
# The reactor's own top-level modules: the frozen recipe modules, the door, and the program.
REACTOR_MODULES = ("__main__", "_reactor", "_zip_directory", "_zip_resources", "_host")
# CPython's own modules outside sys.stdlib_module_names: two names (its frozen test modules) and
# one prefix (its generated build data, _sysconfigdata_<abi>_<platform>). Counted as stdlib.
CPYTHON_UNLISTED_NAMES = ("__hello__", "__phello__")
CPYTHON_UNLISTED_PREFIXES = ("_sysconfigdata_",)


def is_stdlib_or_reactor(name: str, stdlib: frozenset[str] | set[str]) -> bool:
    """A top-level module name is the stdlib's (in the guest's `sys.stdlib_module_names`, or one
    CPython ships outside it) or the reactor's own (spec 069, check a)."""
    return (
        name in stdlib
        or name in REACTOR_MODULES
        or name in CPYTHON_UNLISTED_NAMES
        or name.startswith(CPYTHON_UNLISTED_PREFIXES)
    )


# The judge: every file that decides a check's outcome or steers pytest (spec 002, Decision 14).
JUDGE_PATHS = (
    "tests",
    "context/embedders.txt",
    "pyproject.toml",
    "uv.lock",
    "pytest.ini",
    "tox.ini",
    "setup.cfg",
    "conftest.py",
    ".gitattributes",
)
# Directories never searched for a stray conftest.py: build output, downloads, clones, venvs.
NOT_SOURCE = {"build", "downloads", "prior_art", ".venv", ".venv-build", ".git", "__pycache__"}
# Files an operating system writes into any folder a person opens: never part of the judge, or a
# hash taken on a desktop could not be reproduced by CI (spec 011 concurrency-check review, F3).
# The build keeps the same set and rules in scripts/litter.py; a unit check holds the two equal
# (spec 090, Decision 1).
OS_LITTER = frozenset(
    {
        ".DS_Store",
        "Thumbs.db",
        "desktop.ini",
        "ehthumbs.db",
        "Icon\r",  # a folder's custom icon
        ".Spotlight-V100",  # the rest are a volume's root folders
        ".fseventsd",
        ".Trashes",
        ".TemporaryItems",
        ".DocumentRevisions-V100",
        ".apdisk",
    }
)


def is_litter(name: str) -> bool:
    """True for a name only an operating system leaves; AppleDouble `._x` files by their prefix."""
    return name in OS_LITTER or name.startswith("._")


def has_litter(rel: str) -> bool:
    """True when any part of a `/`-separated path is litter (a file inside a litter folder too)."""
    return any(is_litter(part) for part in rel.replace("\\", "/").split("/"))


def artifact_dir() -> Path | None:
    env = os.environ.get(ARTIFACTS_ENV)
    if env:  # set and not empty, as the runner reads it (spec 001, Decision 3)
        return Path(env).resolve()
    if (BUILD / "artifacts" / "MANIFEST").is_file():
        return (BUILD / "artifacts").resolve()
    from wasi_python import _artifacts

    d = _artifacts._ARTIFACT_DIR
    return d if (d / "MANIFEST").is_file() else None


def wasmtime_cli() -> Path | None:
    """The pinned wasmtime CLI step 10 unpacked under build/tools (spec 071, criterion 3)."""
    found = sorted((BUILD / "tools").glob("wasmtime-v*/wasmtime"))
    return found[0] if found else None


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tracked_files(*roots: str) -> list[str]:
    """Repository-relative paths git tracks under `roots`; the files on disk when git is absent."""
    try:
        r = subprocess.run(
            ["git", "-C", str(REPO), "ls-files", "-z", "--", *roots],
            capture_output=True,
            check=True,
        )
        return sorted(p for p in r.stdout.decode().split("\0") if p)
    except (OSError, subprocess.CalledProcessError):
        out = []
        for root in roots:
            out += [p.relative_to(REPO).as_posix() for p in (REPO / root).rglob("*") if p.is_file()]
        return sorted(out)


def judge_files() -> dict[str, str]:
    """Every judging file (Decision 14) with its SHA-256."""
    found: set[Path] = set()
    for rel in JUDGE_PATHS:
        p = REPO / rel
        found.update([p] if p.is_file() else p.rglob("*") if p.is_dir() else [])
    for dirpath, dirnames, filenames in os.walk(REPO):  # a stray conftest steers pytest too
        # Not into another checkout: a worktree or a repository below the root (spec 029,
        # Decision 5). Only this walk; one under JUDGE_PATHS stays in the hash.
        dirnames[:] = [
            d
            for d in dirnames
            if d not in NOT_SOURCE and not os.path.lexists(os.path.join(dirpath, d, ".git"))
        ]
        if "conftest.py" in filenames:
            found.add(Path(dirpath) / "conftest.py")
    return {
        f.relative_to(REPO).as_posix(): sha256_file(f)
        for f in sorted(found)
        if f.is_file()
        and not has_litter(f.relative_to(REPO).as_posix())
        and not NOT_SOURCE & set(f.relative_to(REPO).parts)
    }


def judge_hash(files: dict[str, str]) -> str:
    return sha256_bytes("".join(f"{k}\0{v}\n" for k, v in sorted(files.items())).encode())


# ---------------------------------------------------------------------------------------------
# Git: what the landing lane's rules read (spec 029)

# An untracked file makes the tree dirty when the judge could see it: under the judge's inputs, a
# judging file, a stray conftest.py anywhere (spec 029, Decision 2, condition D), or a document
# whose presence can turn a rules check green that the commit fails: a specification, a review,
# a patch's pull request draft (029's build review, finding 3).
DIRTY_UNTRACKED = (
    "src",
    "tests",
    "scripts",
    "recipes",
    "pyproject.toml",
    "uv.lock",
    "context/specifications",
    "context/reviews",
    "context/upstream",
    *JUDGE_PATHS,
)
WORKTREE_NOTE = "note: a worktree inside the repository: {} (constitution §4.14 puts them outside)"


def git(*args: str, repo: Path | None = None) -> str | None:
    """git's stdout, run in `repo` (this repository by default); None where git fails or is
    absent."""
    try:
        r = subprocess.run(
            ["git", "-C", str(repo or REPO), *args], capture_output=True, text=True, check=False
        )
    except OSError:
        return None
    return r.stdout if r.returncode == 0 else None


def linked_worktree(repo: Path | None = None) -> bool:
    """Whether `repo` is checked out in a linked worktree: its git directory is not the common
    one. A main tree, a plain clone and a submodule are not (spec 029, Decision 4)."""
    own = (git("rev-parse", "--absolute-git-dir", repo=repo) or "").strip()
    common = (
        git("rev-parse", "--path-format=absolute", "--git-common-dir", repo=repo) or ""
    ).strip()
    if not own or not common:
        return False
    try:
        return not os.path.samefile(own, common)
    except OSError:
        return own != common


def worktrees(repo: Path | None = None) -> list[Path]:
    """Every worktree of `repo`'s repository, the main tree's first, as `git worktree list`
    names them."""
    out = git("worktree", "list", "--porcelain", repo=repo) or ""
    return [
        Path(line[len("worktree ") :]) for line in out.splitlines() if line.startswith("worktree ")
    ]


def worktrees_inside(repo: Path | None = None) -> list[str]:
    """The worktrees below `repo`'s root, relative to it (spec 029, Decision 5)."""
    root = (repo or REPO).resolve()
    inside = []
    for w in worktrees(repo):
        w = w.resolve()
        if w != root and w.is_relative_to(root):
            inside.append(w.relative_to(root).as_posix())
    return sorted(inside)


def _judge_could_see(rel: str) -> bool:
    rel = rel.rstrip("/")
    return Path(rel).name == "conftest.py" or any(
        rel == p or rel.startswith(p + "/") for p in DIRTY_UNTRACKED
    )


def dirty_path(repo: Path | None = None) -> str | None:
    """The first change the judge could see, or None for a clean tree: any tracked change outside
    context/progress/, or an untracked file it could see; an untracked .idea/ or a research draft
    under context/research/ is clean (spec 029, Decision 2)."""
    out = git("status", "--porcelain", "-z", "--untracked-files=all", repo=repo)
    entries = (out or "").split("\0")
    i = 0
    while i < len(entries):
        entry, i = entries[i], i + 1
        if len(entry) < 4:
            continue
        code, names = entry[:2], [entry[3:]]
        if "R" in code or "C" in code:  # a rename or copy: its source follows
            names.append(entries[i])
            i += 1
        for name in names:
            if code == "??":
                if _judge_could_see(name):
                    return name
            elif not name.startswith("context/progress/"):
                return name
    return None


# ---------------------------------------------------------------------------------------------
# The pin list


def read_pin_list(path: Path = PIN_LIST) -> dict[str, str]:
    """`downloads/SHA256SUMS` as {file name: sha256}. Malformed lines raise ValueError."""
    pins: dict[str, str] = {}
    for n, line in enumerate(path.read_text().splitlines(), 1):
        m = re.fullmatch(r"([0-9a-f]{64})  (\S+)", line)
        if not m:
            raise ValueError(f"{path.name}:{n}: not '<64 hex>  <name>': {line!r}")
        if m[2] in pins:
            raise ValueError(f"{path.name}:{n}: {m[2]} is pinned twice")
        pins[m[2]] = m[1]
    return pins


def norm(name: str) -> str:
    return name.lower().replace("_", "-")


# ---------------------------------------------------------------------------------------------
# MANIFEST


@dataclass
class Manifest:
    python: str | None = None
    packages: dict[str, str] = field(default_factory=dict)
    pins: dict[str, str] = field(default_factory=dict)  # file -> sha256
    recipes: dict[str, str] = field(default_factory=dict)  # path -> sha256
    errors: list[str] = field(default_factory=list)


def parse_manifest(text: str) -> Manifest:
    m = Manifest()
    pythons = 0
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("x-"):
            continue
        word, *rest = line.split()
        where = f"MANIFEST:{n}"
        if word == "python" and len(rest) == 1 and re.fullmatch(r"3\.\d+\.\d+", rest[0]):
            pythons += 1
            m.python = rest[0]
        elif word == "package" and len(rest) == 2:
            if rest[0] in m.packages:
                m.errors.append(f"{where}: package {rest[0]} listed twice")
            m.packages[rest[0]] = rest[1]
        elif word == "pin" and len(rest) == 2 and re.fullmatch(r"[0-9a-f]{64}", rest[0]):
            m.pins[rest[1]] = rest[0]
        elif word == "recipe" and len(rest) == 2 and re.fullmatch(r"[0-9a-f]{64}", rest[0]):
            m.recipes[rest[1]] = rest[0]
        else:
            m.errors.append(f"{where}: not a python, package, pin or recipe line: {line!r}")
    if pythons != 1:
        m.errors.append(f"MANIFEST: {pythons} python lines; exactly one is required")
    for pkg in PACKAGES:
        if pkg not in m.packages:
            m.errors.append(f"MANIFEST: no package line for {pkg}")
    return m


def cpython_pin_name(version: str) -> str:
    return f"Python-{version}.tar.xz"


def is_version_of(file: str, pkg: str, version: str) -> bool:
    """Whether a pinned file name is exactly this package at this version (2.5.2 is not 2.5.20)."""
    prefix = norm(f"{pkg}-{version}")
    name = norm(file)
    if not name.startswith(prefix):
        return False
    rest = name[len(prefix) :]
    return rest == "" or rest.startswith(("-", ".tar", ".tgz", ".zip", ".whl"))


def _pin_for(pkg: str, pins: dict[str, str]) -> str | None:
    for f in sorted(pins):
        if norm(f).startswith(norm(pkg) + "-"):
            return f
    return None


def manifest_pin_errors(m: Manifest, pin_list: dict[str, str]) -> list[str]:
    errors = []
    for f, sha in sorted(m.pins.items()):
        if pin_list.get(f) != sha:
            errors.append(f"pin {f} is not the line in downloads/SHA256SUMS")
    if m.python and cpython_pin_name(m.python) not in m.pins:
        errors.append(f"no pin named {cpython_pin_name(m.python)} for python {m.python}")
    for pkg, version in sorted(m.packages.items()):
        f = _pin_for(pkg, m.pins)
        if f is None:
            errors.append(f"no pin for package {pkg}")
        elif not is_version_of(f, pkg, version):
            errors.append(f"package {pkg} {version} does not match its pin {f}")
    for tool in ("wasi-sdk", "wasmtime"):
        if not any(norm(f).startswith(tool + "-") for f in m.pins):
            errors.append(f"no pin for {tool}")
    return errors


def recipe_files() -> dict[str, str]:
    """The files `recipe` lines must cover: tracked under recipes/ and scripts/, not benchmarks."""
    return {
        f: sha256_file(REPO / f)
        for f in tracked_files("recipes", "scripts")
        if not Path(f).name.startswith("bench_") and (REPO / f).is_file()
    }


def manifest_recipe_errors(m: Manifest, tree: dict[str, str]) -> list[str]:
    errors = []
    for f in sorted(set(tree) - set(m.recipes)):
        errors.append(f"stale artifact: {f} is not in MANIFEST")
    for f in sorted(set(m.recipes) - set(tree)):
        errors.append(f"stale artifact: MANIFEST names {f}, which the tree does not have")
    for f in sorted(set(tree) & set(m.recipes)):
        if tree[f] != m.recipes[f]:
            errors.append(f"stale artifact: {f} changed since the build")
    return errors


# ---------------------------------------------------------------------------------------------
# Licences


def _top_level_licence(archive: Path) -> bytes | None:
    """The top-level LICENSE / LICENSE.txt / COPYING of a source tarball or wheel."""
    names = re.compile(r"(LICEN[CS]E(\.txt|\.rst|\.md)?|COPYING)", re.I)
    if archive.suffix == ".whl" or archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as z:
            for n in sorted(z.namelist()):
                parts = n.split("/")
                if ".dist-info" in parts[0] and names.fullmatch(parts[-1]):
                    return z.read(n)
        return None
    with tarfile.open(archive) as t:
        for member in t:
            parts = member.name.split("/")
            if len(parts) == 2 and member.isfile() and names.fullmatch(parts[1]):
                f = t.extractfile(member)
                return f.read() if f else None
    return None


# Licence text a notice must hold besides the top-level file, read from the same pinned archive
# (spec 007's build review, finding 7): xz's library is under 0BSD, and SQLite's notice is the
# blessing at the head of sqlite3.h. libxml2's and libxslt's terms are in a top-level file named
# `Copyright`, which the top-level search does not match (spec 046, Decision 15); qhull's in
# `COPYING.txt` (spec 043, Decision 11).
BLESSING = b"The author disclaims copyright to this source code."
MORE_LICENCE = {
    "xz": "COPYING.0BSD",
    "sqlite": "sqlite3.h",
    "libxml2": "Copyright",
    "libxslt": "Copyright",
    "qhull": "COPYING.txt",
}
# A notice a component's file must hold that ships in another component's pinned archive, named
# here so it stays if that component's own list changes (spec 043, Decision 11): contourpy's
# mpl2005 code came from GIST's gcntr.c, whose notice, the Regents of the University of
# California's, matplotlib ships as LICENSE/LICENSE_YORICK.
BORROWED_LICENCE = {"contourpy": ("matplotlib", "LICENSE/LICENSE_YORICK")}


def _more_licence(component: str, archive: Path) -> list[bytes]:
    if component not in MORE_LICENCE or archive.suffix in (".whl", ".zip"):
        return []
    want = MORE_LICENCE[component]
    with tarfile.open(archive) as t:
        for member in t:
            parts = member.name.split("/")
            if len(parts) == 2 and member.isfile() and parts[1] == want:
                f = t.extractfile(member)
                data = f.read() if f else b""
                if component != "sqlite":
                    return [data]
                return [BLESSING] if BLESSING in data else []
    return []


def _borrowed_licence(component: str, m: Manifest | None) -> list[bytes]:
    """The notice BORROWED_LICENCE names for a component, read from the other component's pinned
    archive; nothing when there is none, or when that archive is not here (presence only)."""
    if component not in BORROWED_LICENCE:
        return []
    other, member = BORROWED_LICENCE[component]
    archive = licence_source(other, m)
    if archive is None:
        return []
    with tarfile.open(archive) as t:
        for info in t:
            parts = info.name.split("/", 1)
            if len(parts) == 2 and parts[1] == member and info.isfile():
                f = t.extractfile(info)
                return [f.read() if f else b""]
    raise ValueError(f"{archive.name} holds no {member}")


def licence_source(component: str, m: Manifest | None) -> Path | None:
    """The pinned archive whose licence a component's notice must contain: the exact file the
    MANIFEST names, present in downloads/ and matching its pin. None means presence only."""
    if m is None or component in ("wasi-libc", "llvm-runtimes"):
        return None
    try:
        pinned = read_pin_list(DOWNLOADS / "SHA256SUMS")
    except (OSError, ValueError):
        return None
    if component == "cpython":
        names = [cpython_pin_name(m.python)] if m.python else []
    else:
        package = "sqlite-autoconf" if component == "sqlite" else component  # as its pin names it
        version = m.packages.get(package)
        # A source tarball before a wheel of the same version: numpy's host wheel (f2py's, spec
        # 037) is a build tool, and numpy's notices are its sdist's.
        names = sorted(
            (f for f in pinned if version and is_version_of(f, package, version)),
            key=lambda f: (".tar." not in f, f),
        )
    for name in names:
        f = DOWNLOADS / name
        if name in pinned and f.is_file():
            if sha256_file(f) != pinned[name]:
                raise ValueError(f"downloads/{name} does not match its pin")
            return f
    return None


def licence_errors(directory: Path, m: Manifest | None) -> tuple[list[str], list[str], list[str]]:
    """(errors, components checked for content, components checked for presence only)."""
    errors, content, presence = [], [], []
    for c in LICENCE_COMPONENTS:
        f = directory / "LICENSES" / f"{c}.txt"
        if not f.is_file() or f.stat().st_size == 0:
            errors.append(f"LICENSES/{c}.txt is missing or empty")
            continue
        try:
            src = licence_source(c, m)
        except ValueError as e:
            errors.append(f"LICENSES/{c}.txt: {e}")
            continue
        text = _top_level_licence(src) if src else None
        wanted = ([text] if text is not None else []) + (_more_licence(c, src) if src else [])
        try:
            borrowed = _borrowed_licence(c, m) if src else []
        except ValueError as e:
            errors.append(f"LICENSES/{c}.txt: {e}")
            continue
        if not wanted:
            presence.append(c)
            continue
        content.append(c)
        body = f.read_bytes()
        if not all(w in body for w in wanted):
            errors.append(f"LICENSES/{c}.txt does not contain the licence of {src.name}")
        if not all(w in body for w in borrowed):
            other, member = BORROWED_LICENCE[c]
            errors.append(f"LICENSES/{c}.txt does not contain {other}'s {member}")
    return errors, content, presence


def read_member(archive: Path, name: str) -> bytes:
    with zipfile.ZipFile(archive) as z:
        return z.read(name)


def zip_members(archive: Path) -> list[zipfile.ZipInfo]:
    with zipfile.ZipFile(io.BytesIO(archive.read_bytes())) as z:
        return z.infolist()
