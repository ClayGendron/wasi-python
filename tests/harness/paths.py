"""Where things are, and what the harness reads from the artifact directory (spec 002, Decision 12).

The artifact directory is `$WASI_PYTHON_ARTIFACTS` when it is set, and nothing else; otherwise
build/artifacts/ when it holds a MANIFEST (what scripts/build.sh writes: spec 003, Decision 10);
otherwise the wheel's `wasi_python.ARTIFACT_DIR` when it holds one; otherwise there is none.
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
OS_LITTER = {".DS_Store", "Thumbs.db", "desktop.ini"}


def artifact_dir() -> Path | None:
    env = os.environ.get(ARTIFACTS_ENV)
    if env:  # set and not empty, as the runner reads it (spec 001, Decision 3)
        return Path(env).resolve()
    if (BUILD / "artifacts" / "MANIFEST").is_file():
        return (BUILD / "artifacts").resolve()
    import wasi_python

    d = wasi_python.ARTIFACT_DIR
    return d if (d / "MANIFEST").is_file() else None


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
        dirnames[:] = [d for d in dirnames if d not in NOT_SOURCE]
        if "conftest.py" in filenames:
            found.add(Path(dirpath) / "conftest.py")
    return {
        f.relative_to(REPO).as_posix(): sha256_file(f)
        for f in sorted(found)
        if f.is_file()
        and f.name not in OS_LITTER
        and not NOT_SOURCE & set(f.relative_to(REPO).parts)
    }


def judge_hash(files: dict[str, str]) -> str:
    return sha256_bytes("".join(f"{k}\0{v}\n" for k, v in sorted(files.items())).encode())


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
# blessing at the head of sqlite3.h.
BLESSING = b"The author disclaims copyright to this source code."


def _more_licence(component: str, archive: Path) -> list[bytes]:
    if component not in ("xz", "sqlite") or archive.suffix in (".whl", ".zip"):
        return []
    want = "COPYING.0BSD" if component == "xz" else "sqlite3.h"
    with tarfile.open(archive) as t:
        for member in t:
            parts = member.name.split("/")
            if len(parts) == 2 and member.isfile() and parts[1] == want:
                f = t.extractfile(member)
                data = f.read() if f else b""
                if component == "xz":
                    return [data]
                return [BLESSING] if BLESSING in data else []
    return []


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
        names = [f for f in sorted(pinned) if version and is_version_of(f, package, version)]
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
        if not wanted:
            presence.append(c)
            continue
        content.append(c)
        body = f.read_bytes()
        if not all(w in body for w in wanted):
            errors.append(f"LICENSES/{c}.txt does not contain the licence of {src.name}")
    return errors, content, presence


def read_member(archive: Path, name: str) -> bytes:
    with zipfile.ZipFile(archive) as z:
        return z.read(name)


def zip_members(archive: Path) -> list[zipfile.ZipInfo]:
    with zipfile.ZipFile(io.BytesIO(archive.read_bytes())) as z:
        return z.infolist()
