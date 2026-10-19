"""The source trees are their tarballs plus the recorded patches, mechanically (constitution §4.1,
spec 020).

A source tree under `build/` matches its pinned tarball when every file the tarball holds is
present and byte-identical in the tree (symlinks: same target). A tree with carried patches under
`recipes/patches/<top>/` must instead equal its tarball with exactly those applied, by the same
`scripts/steps/apply_patches.sh` the build runs; a path a patch deletes must be absent. Files the
build adds are not judged (spec 002, Decision 17).
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

from harness import paths

# Which pinned tarball is which source tree. CPython is matched case-sensitively, so a file named
# `python-…` (Brett's reference build) never counts as the CPython source.
SOURCE_PATTERNS = {
    "cpython": re.compile(r"Python-\d+\.\d+\.\d+\.tar\.xz"),
    "numpy": re.compile(r"numpy-[\w.]+\.tar\.gz"),
    "pandas": re.compile(r"pandas-[\w.]+\.tar\.gz"),
    "zlib": re.compile(r"zlib-[\w.]+\.tar\.gz"),
    "bzip2": re.compile(r"bzip2-[\w.]+\.tar\.gz"),
    "xz": re.compile(r"xz-[\w.]+\.tar\.gz"),
    "sqlite": re.compile(r"sqlite-autoconf-\d+\.tar\.gz"),
    "regex": re.compile(r"regex-[\w.]+\.tar\.gz"),  # spec 047
    # matplotlib (spec 023): its five C libraries and three packages
    "freetype": re.compile(r"freetype-[\w.]+\.tar\.xz"),
    "harfbuzz": re.compile(r"harfbuzz-[\w.]+\.tar\.xz"),
    "sheenbidi": re.compile(r"SheenBidi-[\w.]+\.tar\.gz"),
    "libraqm": re.compile(r"libraqm-[\w.]+\.tar\.gz"),
    "qhull": re.compile(r"qhull-[\w.]+\.tar\.gz"),
    "pillow": re.compile(r"pillow-[\w.]+\.tar\.gz"),
    "kiwisolver": re.compile(r"kiwisolver-[\w.]+\.tar\.gz"),
    "matplotlib": re.compile(r"matplotlib-[\w.]+\.tar\.gz"),
    "contourpy": re.compile(r"contourpy-[\w.]+\.tar\.gz"),  # spec 043
    # lxml (spec 046): its two C libraries and the package
    "libxml2": re.compile(r"libxml2-[\w.]+\.tar\.xz"),
    "libxslt": re.compile(r"libxslt-[\w.]+\.tar\.xz"),
    "lxml": re.compile(r"lxml-[\w.]+\.tar\.gz"),
    # tier A (spec 039): the two sdists whose pure package folders step 70 takes
    "pyyaml": re.compile(r"pyyaml-[\w.]+\.tar\.gz"),
    "markupsafe": re.compile(r"markupsafe-[\w.]+\.tar\.gz"),
    # spec 041, Decision 4: networkx from its sdist, so its carried patch has a tree
    "networkx": re.compile(r"networkx-[\w.]+\.tar\.gz"),
    # scipy (spec 037): OpenBLAS, whose C LAPACK is the LAPACK, and the package
    "openblas": re.compile(r"OpenBLAS-[\w.]+\.tar\.gz"),
    "scipy": re.compile(r"scipy-[\w.]+\.tar\.gz"),
}


def top_dir(tarball: Path) -> str:
    with tarfile.open(tarball) as t:
        for member in t:
            return member.name.split("/")[0]
    raise ValueError(f"{tarball.name} is empty")


def source_pair(
    component: str, downloads: Path | None = None, build: Path | None = None
) -> tuple[Path, Path] | None:
    """(tarball, tree) for a component when both are present, else None."""
    downloads = downloads or paths.DOWNLOADS
    build = build or paths.BUILD
    try:
        pinned = paths.read_pin_list(downloads / "SHA256SUMS")
    except (OSError, ValueError):
        return None
    for name in sorted(pinned):
        if SOURCE_PATTERNS[component].fullmatch(name) and (downloads / name).is_file():
            tarball = downloads / name
            tree = build / top_dir(tarball)
            if tree.is_dir():
                return tarball, tree
    return None


PATCHES = paths.REPO / "recipes" / "patches"
APPLIER = paths.REPO / "scripts" / "steps" / "apply_patches.sh"


def patch_files(top: str, patches: Path | None = None) -> list[Path]:
    """A tree's carried patches, in the order the applier takes them."""
    return sorted((patches or PATCHES).joinpath(top).glob("[0-9][0-9][0-9][0-9]-*.patch"))


# A pinned member the build's walks would skip without a word (spec 090, Decision 1's guard).
PINNED_LITTER = (
    "a pinned member with a name only an operating system leaves; the build skips it (spec 090)"
)


def tree_drift(tarball: Path, tree: Path, patches: Path | None = None) -> list[str]:
    """Every file that is missing or different in the tree, as 'path: why': against the tarball,
    or, when the tree has carried patches, against the tarball with them applied."""
    if patch_files(tree.name, patches):
        return _patched_drift(tarball, tree, (patches or PATCHES) / tree.name)
    return _tarball_drift(tarball, tree)


def _patched_drift(tarball: Path, tree: Path, patch_dir: Path) -> list[str]:
    # Under the project's own build/harness, never the system's temporary folder (§4.8): the
    # applier's ceiling keeps git from taking the outer repository for the tree's.
    paths.HARNESS_TMP.mkdir(parents=True, exist_ok=True)
    d = tempfile.mkdtemp(prefix="patched-", dir=paths.HARNESS_TMP)
    try:
        with tarfile.open(tarball) as t:
            members = [m.name.split("/", 1)[1] for m in t if "/" in m.name.strip("/")]
            t.extractall(d, filter="data")
        result = Path(d) / tree.name
        out = subprocess.run(
            ["sh", str(APPLIER), str(result), str(patch_dir)], capture_output=True, text=True
        )
        if out.returncode != 0:
            return [f"{tree.name}: the recorded patches do not apply: {out.stderr.strip()}"]
        drift = []
        held = set(members)
        for p in sorted(result.rglob("*")):
            rel = p.relative_to(result).as_posix()
            if paths.has_litter(rel) and rel not in held:
                continue  # Finder's or Explorer's, written into this extraction (specs 026, 090)
            if paths.has_litter(rel):
                drift.append(f"{rel}: {PINNED_LITTER}")
            target = tree / rel
            if p.is_symlink():
                if not target.is_symlink() or os.readlink(target) != os.readlink(p):
                    drift.append(f"{rel}: symlink changed or missing")
            elif p.is_dir():
                if not target.is_dir():
                    drift.append(f"{rel}: directory missing")
            elif not target.is_file() or target.is_symlink():
                drift.append(f"{rel}: missing")
            elif paths.sha256_file(target) != paths.sha256_file(p):
                drift.append(f"{rel}: modified")
        for rel in sorted(set(members)):
            if not os.path.lexists(result / rel) and os.path.lexists(tree / rel):
                drift.append(f"{rel}: a recorded patch deletes it")
        return drift
    finally:
        _remove_tree(Path(d))


def _remove_tree(d: Path) -> None:
    """Removed with spec 018's retries: a Finder window showing build/ can write litter into a
    folder while it is removed (spec 026). One that still will not go is left under build/harness,
    which git ignores, rather than failing the check."""
    for _ in range(3):
        shutil.rmtree(d, ignore_errors=True)
        if not d.exists():
            return


def _tarball_drift(tarball: Path, tree: Path) -> list[str]:
    drift = []
    with tarfile.open(tarball) as t:
        for member in t:
            parts = member.name.split("/", 1)
            if len(parts) < 2 or not parts[1]:
                continue
            rel = parts[1]
            target = tree / rel
            if paths.has_litter(rel.rstrip("/")):
                drift.append(f"{rel}: {PINNED_LITTER}")
            if member.isdir():
                if not target.is_dir():
                    drift.append(f"{rel}: directory missing")
            elif member.issym():
                if not target.is_symlink() or os.readlink(target) != member.linkname:
                    drift.append(f"{rel}: symlink changed or missing")
            elif member.isfile():
                if not target.is_file() or target.is_symlink():
                    drift.append(f"{rel}: missing")
                    continue
                f = t.extractfile(member)
                want = hashlib.sha256(f.read()).hexdigest() if f else ""
                if paths.sha256_file(target) != want:
                    drift.append(f"{rel}: modified")
    return drift
