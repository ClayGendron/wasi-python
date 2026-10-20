"""The artifact set: `Artifacts`, `ArtifactsMissing`, `artifact_dir` and `artifacts()`, and the
facts about the set's files the runner reads: its digests, stamps, version tag and guest
packages."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

from ._process import process

_ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
_ARTIFACTS_ENV = "WASI_PYTHON_ARTIFACTS"


def _checkout_artifact_dir() -> Path | None:
    """A source checkout's build/artifacts/: only when this package is <repo>/src/wasi_python/
    and <repo>/pyproject.toml names wasi-python. A copy installed with `pip install --target`,
    or vendored, inside some project never takes that project's build/ (spec 087, Decision 10)."""
    package = Path(__file__).resolve().parent
    if package.parent.name != "src":
        return None
    repo = package.parent.parent
    try:
        import tomllib

        name = tomllib.loads((repo / "pyproject.toml").read_text()).get("project", {}).get("name")
    except (OSError, ValueError, UnicodeDecodeError, AttributeError):
        return None
    return repo / "build" / "artifacts" if name == "wasi-python" else None


_CHECKOUT_ARTIFACT_DIR = _checkout_artifact_dir()


class ArtifactsMissing(RuntimeError):
    """Raised when there is no usable artifact set; the message says how to get one."""


@dataclass(frozen=True)
class Artifacts:
    """The artifact set's four files, made by `artifacts()`, or by you for `run(artifacts=…)`.

    Attributes:
        snapshot: The snapshot binary, python-snapshot.wasm: the reactor with the stdlib's
            bootstrap imported (no package).
        plain: The plain reactor, python.wasm, without the snapshot.
        stdlib_zip: The stdlib zip, python-stdlib.zip, which every guest sees read-only at
            /usr/local/lib.
        manifest: The MANIFEST: every pinned source and recipe hash the build used.
    """

    snapshot: Path
    plain: Path
    stdlib_zip: Path
    manifest: Path


def artifact_dir() -> Path:
    """The folder holding the artifact set.

    It is `$WASI_PYTHON_ARTIFACTS` when that is set and not empty; else, when this package runs
    from a source checkout of wasi-python (`<repo>/src/wasi_python/`), its build/artifacts/ when
    that holds a MANIFEST; else the wheel's own artifacts/ when it holds one. `run` and `Session`
    check the set they find against its SHA256SUMS before using it.

    Raises:
        ArtifactsMissing: None of the three is there.
    """
    # The harness's order (spec 001, Decision 3; spec 003, Decision 10).
    env = os.environ.get(_ARTIFACTS_ENV)
    if env:  # set and not empty
        return Path(env).resolve()
    for d in (_CHECKOUT_ARTIFACT_DIR, _ARTIFACT_DIR):
        if d is not None and (d / "MANIFEST").is_file():
            return d
    raise ArtifactsMissing(
        f"no runtime artifacts: ${_ARTIFACTS_ENV} is unset, and neither "
        f"{_CHECKOUT_ARTIFACT_DIR} nor {_ARTIFACT_DIR} has a MANIFEST. Install the released "
        "wheel, or build with scripts/build.sh (see README.md)."
    )


def artifacts() -> Artifacts:
    """The artifact set's paths, in the folder `artifact_dir()` names.

    Raises:
        ArtifactsMissing: There is no artifact set, or its folder has no MANIFEST; the message
            says how to get one.
    """
    d = artifact_dir()
    manifest = d / "MANIFEST"
    if not manifest.is_file():
        raise ArtifactsMissing(f"{d} has no MANIFEST (from ${_ARTIFACTS_ENV})")
    return Artifacts(
        snapshot=d / "python-snapshot.wasm",
        plain=d / "python.wasm",
        stdlib_zip=d / "python-stdlib.zip",
        manifest=manifest,
    )


find_artifacts = artifacts


def _stamp(st: os.stat_result) -> tuple[int, ...]:
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def _hash_file(path: Path) -> str:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    h = hashlib.sha256()
    with os.fdopen(os.open(path, flags), "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _version_tag(manifest: Path) -> str:
    """'315' from MANIFEST's `python 3.15.0` line: the stdlib zip's guest name is python315.zip.
    Cached per path in `process().versions`."""
    versions = process().versions
    if manifest not in versions:
        for line in manifest.read_text().splitlines():
            if line.startswith("python "):
                major, minor = line.split()[1].split(".")[:2]
                versions[manifest] = f"{major}{minor}"
                break
        else:
            raise ValueError(f"{manifest} has no python line")
    return versions[manifest]


GUEST_PACKAGE = "recipes/guest/host/tools.py"  # MANIFEST's recipe line for the guest package


def _has_guest_package(manifest: Path) -> bool:
    """Whether MANIFEST names the tool protocol's guest package among its recipes (spec 036,
    Decision 1). Cached per path and stat stamp in `process().guest_packages`, with no lock: a
    race only reads it twice."""
    key = str(manifest)
    stamp = _stamp(os.stat(manifest))
    cache = process().guest_packages
    hit = cache.get(key)
    if hit is not None and hit[0] == stamp:
        return hit[1]
    found = False
    for line in Path(manifest).read_text().splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] == "recipe" and parts[-1] == GUEST_PACKAGE:
            found = True
            break
    cache[key] = (stamp, found)
    return found


SET_SUMS = "SHA256SUMS"  # beside MANIFEST in every set the build writes (spec 003, step 90)


class _Checked(NamedTuple):
    """The digests a found set's check took, which the call then holds its bytes to."""

    binary: str
    zip: str


def _found_and_checked(snapshot: bool) -> tuple[Artifacts, _Checked]:
    """The set `artifacts()` finds, its MANIFEST, the binary this call runs and the stdlib zip
    each checked against the set's own SHA256SUMS before any is used (spec 087, Decision 10, the
    0.1.0 security review's S3). A changed or half-written file is refused, not compiled. The
    digests are kept per file stamp, so a later call reads only the two small files again. They
    are handed on: `_module` compiles only bytes with the checked digest, and `_zip_folder` holds
    the guest's private copy of the zip to it, so a file changed after the check is refused too,
    and never reaches the guest or the .cwasm cache. A set the caller passes is the caller's own."""

    found = find_artifacts()
    sums_path = found.manifest.parent / SET_SUMS
    try:
        text = sums_path.read_text()
    except (OSError, UnicodeDecodeError) as e:
        raise ArtifactsMissing(
            f"{sums_path} cannot be read ({e}): an artifact set the runner finds is checked "
            "against its SHA256SUMS before use"
        ) from None
    sums = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2:
            sums[parts[1].lstrip("*")] = parts[0].lower()
    binary = found.snapshot if snapshot else found.plain
    got_of: dict[Path, str] = {}
    for path in (found.manifest, binary, found.stdlib_zip):
        want = sums.get(path.name)
        if want is None or path.parent != found.manifest.parent:
            raise ArtifactsMissing(f"{path} is not listed in {sums_path}")
        try:
            got = _digest(path)
        except OSError as e:
            raise ArtifactsMissing(f"{path} cannot be read ({e})") from None
        if got != want:
            raise ArtifactsMissing(
                f"{path} does not match {sums_path} (SHA-256 {got[:16]}…, listed {want[:16]}…): "
                "the set changed after it was built; rebuild or reinstall it"
            )
        got_of[path] = got
    return found, _Checked(got_of[binary], got_of[found.stdlib_zip])


def _digest(path: Path) -> str:
    st = path.stat()
    key = (str(path.resolve()), st.st_size, st.st_mtime_ns)
    digests = process().digests  # per path, size and mtime
    if key not in digests:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for block in iter(lambda: f.read(1 << 20), b""):
                h.update(block)
        digests[key] = h.hexdigest()
    return digests[key]
