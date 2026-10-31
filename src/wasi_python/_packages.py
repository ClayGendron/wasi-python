"""The Python packages an artifact set carries: `Package` and `packages()`, read from the stdlib
zip's `.dist-info` folders on the host, with no guest started and no wasmtime loaded."""

from __future__ import annotations

import importlib.metadata
import os
import re
import zipfile
from dataclasses import dataclass
from zipfile import ZipFile

from . import _artifacts
from ._artifacts import Artifacts, ArtifactsMissing
from ._process import process

# The most a member of a `.dist-info` folder may hold: the bound the guest's own zip reader
# keeps, so an unchecked set cannot make the host read without end.
MEMBER_BYTES = 1 << 20
# A character that would break or end a line of a prompt: the ASCII and Latin-1 controls,
# a newline among them, and Unicode's line and paragraph separators.
_LINE_BREAKER = re.compile(r"[\x00-\x1f\x7f-\x9f\u2028\u2029]")


@dataclass(frozen=True, slots=True)
class Package:
    """One Python package in the artifact set, as `packages()` lists it.

    `str()` of one is the line for a prompt, `scikit-learn 1.9.1 (import sklearn)`, or the name
    and version alone when it puts no name on the import path.

    Attributes:
        name: The distribution's name, as its metadata writes it (`scikit-learn`).
        version: The distribution's version (`1.9.1`).
        imports: The top-level names it puts on the import path, sorted (`("sklearn",)`).
    """

    name: str
    version: str
    imports: tuple[str, ...]

    def __str__(self) -> str:
        if not self.imports:
            return f"{self.name} {self.version}"
        return f"{self.name} {self.version} (import {', '.join(self.imports)})"


def packages(artifacts: Artifacts | None = None) -> tuple[Package, ...]:
    """The Python packages in the artifact set, each with its version and import names.

    One `Package` per distribution the guest's `importlib.metadata.distributions()` finds in the
    stdlib zip, sorted by normalized name. It reads the zip on the host: it starts no guest and
    loads no wasmtime. The C libraries and the interpreter's own modules are not listed, and
    neither is a package an `import_path=` adds. The answer is kept per zip file, so a second
    call on an unchanged zip reads nothing; a zip replaced in place is read again. Make the
    lines of a system prompt with `str`::

        "\\n".join(map(str, packages()))

    Args:
        artifacts: The set to read; `None` finds it with `artifacts()`.

    Raises:
        TypeError: `artifacts` is neither `None` nor an `Artifacts`.
        ArtifactsMissing: There is no set, its zip cannot be read, or a distribution in it has
            no name or version, a member over 1 MiB, or a control character in a name.
    """
    if artifacts is None:
        artifacts = _artifacts.artifacts()
    elif not isinstance(artifacts, Artifacts):
        raise TypeError(f"packages takes an Artifacts or None; got {type(artifacts).__name__}")
    path = artifacts.stdlib_zip
    try:
        resolved = str(path.resolve())
        named = os.stat(path)
    except OSError as e:
        raise ArtifactsMissing(f"{path} cannot be read ({e})") from None
    cache = process().packages
    found = cache.get((resolved, *_artifacts._stamp(named)))
    if found is not None:
        return found
    try:
        fd = os.open(path, _artifacts._OPEN_FLAGS)
        with os.fdopen(fd, "rb") as f:
            opened = os.fstat(fd)
            with ZipFile(f) as zf:
                found = _read_zip(zf, path)
        named = os.stat(path)
    except (OSError, zipfile.BadZipFile) as e:
        raise ArtifactsMissing(f"{path} cannot be read ({e})") from None
    if os.path.samestat(opened, named):  # what was read is the file the key names
        cache[(resolved, *_artifacts._stamp(named))] = found
    return found


def _read_zip(zf: ZipFile, path: os.PathLike[str]) -> tuple[Package, ...]:
    """Each top-level `.dist-info` folder of the zip as a `Package`, sorted by normalized name."""
    folders: set[str] = set()
    for info in zf.infolist():
        top, sep, _ = info.filename.partition("/")
        if sep and top.endswith(".dist-info"):
            folders.add(top)
            if info.file_size > MEMBER_BYTES:
                raise ArtifactsMissing(
                    f"{path}: {info.filename} holds {info.file_size} bytes, over 1 MiB"
                )
    found = [_package(zf, folder, path) for folder in sorted(folders)]
    return tuple(sorted(found, key=lambda p: (_normalized(p.name), p.name, p.version)))


def _package(zf: ZipFile, folder: str, path: os.PathLike[str]) -> Package:
    """One folder read as the guest's `importlib.metadata` reads it: the same METADATA bytes and
    the same email parser, through the zip's own path class on the host."""
    dist = importlib.metadata.PathDistribution(zipfile.Path(zf, folder + "/"))
    where = f"{path}: {folder}"
    try:
        meta = dist.metadata
        name = _header(meta, "Name")
        version = _header(meta, "Version")
        top_level = dist.read_text("top_level.txt")
    except (UnicodeDecodeError, ValueError) as e:
        raise ArtifactsMissing(f"{where} cannot be read ({e})") from None
    if not name or not version:
        raise ArtifactsMissing(f"{where} has no Name or no Version in its METADATA")
    imports = tuple(sorted(set((top_level or "").split())))
    for text in (name, version, *imports):
        if _LINE_BREAKER.search(text):
            raise ArtifactsMissing(f"{where}: {text!r} holds a control character")
    return Package(name, version, imports)


def _header(meta: importlib.metadata.PackageMetadata | None, key: str) -> str | None:
    """A header's first value, or None when it is absent: never `meta[key]`, whose answer to a
    missing key differs from one host Python to the next (None, a warning, or KeyError)."""
    values = meta.get_all(key) if meta is not None else None
    return str(values[0]) if values else None


def _normalized(name: str) -> str:
    """The name as packaging's rule compares it: runs of `-`, `_` and `.` are one `-`, lower."""
    return re.sub(r"[-_.]+", "-", name).lower()
