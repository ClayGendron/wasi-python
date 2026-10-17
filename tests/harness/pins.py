"""Zero upstream patches, mechanically (constitution §4.1).

A source tree under `build/` matches its pinned tarball when every file the tarball holds is
present and byte-identical in the tree (symlinks: same target). Files the build adds are not
judged (spec 002, Decision 17).
"""

from __future__ import annotations

import hashlib
import os
import re
import tarfile
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


def tree_drift(tarball: Path, tree: Path) -> list[str]:
    """Every tarball file that is missing or different in the tree, as 'path: why'."""
    drift = []
    with tarfile.open(tarball) as t:
        for member in t:
            parts = member.name.split("/", 1)
            if len(parts) < 2 or not parts[1]:
                continue
            rel = parts[1]
            target = tree / rel
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
