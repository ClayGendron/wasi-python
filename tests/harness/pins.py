"""The source trees are their tarballs plus the recorded patches, mechanically.

A source tree under `build/` matches its pinned tarball when every file the tarball holds is
present and byte-identical in the tree (symlinks: same target). A tree with carried patches under
`recipes/patches/<top>/` must instead equal its tarball with exactly those applied, by the same
`scripts/steps/apply_patches.sh` the build runs; a path a patch deletes must be absent. Files the
build adds are not judged, but for one shape: a folder under any `subprojects/` that the tarball
did not ship, which is what a meson fallback leaves when it fetches a subproject and builds it in.
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
    "zstd": re.compile(r"zstd-[\w.]+\.tar\.gz"),
    "regex": re.compile(r"regex-[\w.]+\.tar\.gz"),
    # matplotlib: its five C libraries and three packages
    "freetype": re.compile(r"freetype-[\w.]+\.tar\.xz"),
    "harfbuzz": re.compile(r"harfbuzz-[\w.]+\.tar\.xz"),
    "sheenbidi": re.compile(r"SheenBidi-[\w.]+\.tar\.gz"),
    "libraqm": re.compile(r"libraqm-[\w.]+\.tar\.gz"),
    "qhull": re.compile(r"qhull-[\w.]+\.tar\.gz"),
    # Pillow's JPEG codec
    "libjpeg-turbo": re.compile(r"libjpeg-turbo-[\w.]+\.tar\.gz"),
    "pillow": re.compile(r"pillow-[\w.]+\.tar\.gz"),
    "kiwisolver": re.compile(r"kiwisolver-[\w.]+\.tar\.gz"),
    "matplotlib": re.compile(r"matplotlib-[\w.]+\.tar\.gz"),
    "contourpy": re.compile(r"contourpy-[\w.]+\.tar\.gz"),
    # lxml: its two C libraries and the package
    "libxml2": re.compile(r"libxml2-[\w.]+\.tar\.xz"),
    "libxslt": re.compile(r"libxslt-[\w.]+\.tar\.xz"),
    "lxml": re.compile(r"lxml-[\w.]+\.tar\.gz"),
    # tier A: the two sdists whose pure package folders step 70 takes
    "pyyaml": re.compile(r"pyyaml-[\w.]+\.tar\.gz"),
    "markupsafe": re.compile(r"markupsafe-[\w.]+\.tar\.gz"),
    # networkx from its sdist, so its carried patch has a tree
    "networkx": re.compile(r"networkx-[\w.]+\.tar\.gz"),
    # scipy: OpenBLAS, whose C LAPACK is the LAPACK, and the package
    "openblas": re.compile(r"OpenBLAS-[\w.]+\.tar\.gz"),
    "scipy": re.compile(r"scipy-[\w.]+\.tar\.gz"),
    # scikit-learn
    "scikit_learn": re.compile(r"scikit_learn-[\w.]+\.tar\.gz"),
    # seaborn from its sdist, whose package step 70 takes
    "seaborn": re.compile(r"seaborn-[\w.]+\.tar\.gz"),
    # statsmodels
    "statsmodels": re.compile(r"statsmodels-[\w.]+\.tar\.gz"),
    # python-docx and python-pptx from their sdists, so each carried patch has a tree
    "python-docx": re.compile(r"python_docx-[\w.]+\.tar\.gz"),
    "python-pptx": re.compile(r"python_pptx-[\w.]+\.tar\.gz"),
    # pdfminer.six from its sdist, so its carried patch has a tree; xarray from its sdist, for the
    # notices its wheel lacks
    "pdfminer-six": re.compile(r"pdfminer_six-[\w.]+\.tar\.gz"),
    "xarray": re.compile(r"xarray-[\w.]+\.tar\.gz"),
    # SVG to PNG through cairo: its three C libraries, cffi's C backend, and cairocffi and CairoSVG
    # from their sdists (CairoSVG's carried patch has a tree)
    "pixman": re.compile(r"pixman-[\w.]+\.tar\.xz"),
    "libpng": re.compile(r"libpng-[\w.]+\.tar\.xz"),
    "cairo": re.compile(r"cairo-[\w.]+\.tar\.xz"),
    "cffi": re.compile(r"cffi-[\w.]+\.tar\.gz"),
    "cairocffi": re.compile(r"cairocffi-[\w.]+\.tar\.gz"),
    "cairosvg": re.compile(r"cairosvg-[\w.]+\.tar\.gz"),
    # The pure-Python packages' test sources: each package's sdist, or, where the sdist carries no
    # tests, its release tag's archive (named `-tag.tar.gz`, so no pattern meets an sdist), and
    # pypdf's sample files at the commit its release tag records. They are data the judge stages,
    # never built.
    "attrs": re.compile(r"attrs-[\w.]+\.tar\.gz"),
    "beautifulsoup4": re.compile(r"beautifulsoup4-[\w.]+\.tar\.gz"),
    "charset-normalizer": re.compile(r"charset_normalizer-[\w.]+\.tar\.gz"),
    "cloudpickle": re.compile(r"cloudpickle-[\w.]+-tag\.tar\.gz"),
    "cycler": re.compile(r"cycler-[\w.]+-tag\.tar\.gz"),
    "defusedxml": re.compile(r"defusedxml-[\w.]+\.tar\.gz"),
    "et-xmlfile": re.compile(r"et_xmlfile-[\w.]+-tag\.tar\.gz"),
    "fonttools": re.compile(r"fonttools-[\w.]+\.tar\.gz"),
    "formulaic": re.compile(r"formulaic-[\w.]+\.tar\.gz"),
    "html5lib": re.compile(r"html5lib-[\w.]+\.tar\.gz"),
    "interface-meta": re.compile(r"interface_meta-[\w.]+\.tar\.gz"),
    "jinja2": re.compile(r"jinja2-[\w.]+\.tar\.gz"),
    "joblib": re.compile(r"joblib-[\w.]+\.tar\.gz"),
    "more-itertools": re.compile(r"more_itertools-[\w.]+\.tar\.gz"),
    "mpmath": re.compile(r"mpmath-[\w.]+\.tar\.gz"),
    "narwhals": re.compile(r"narwhals-[\w.]+\.tar\.gz"),
    "openpyxl": re.compile(r"openpyxl-[\w.]+-tag\.tar\.gz"),
    "packaging": re.compile(r"packaging-[\w.]+\.tar\.gz"),
    "patsy": re.compile(r"patsy-[\w.]+\.tar\.gz"),
    "pyparsing": re.compile(r"pyparsing-[\w.]+\.tar\.gz"),
    "pypdf": re.compile(r"pypdf-[\w.]+\.tar\.gz"),
    "pypdf-samples": re.compile(r"pypdf-[\w.]+-sample-files-tag\.tar\.gz"),
    # pdfplumber's and pdfminer.six's release tags: their sdists hold no PDF file the tests read
    "pdfplumber": re.compile(r"pdfplumber-[\w.]+-tag\.tar\.gz"),
    "pdfminer-six-tests": re.compile(r"pdfminer_six-[\w.]+-tag\.tar\.gz"),
    # The tests of the packages that draw through cairo: tinycss2's, cssselect2's and imageio's
    # sdists, and imageio's test images at one commit
    "tinycss2": re.compile(r"tinycss2-[\w.]+\.tar\.gz"),
    "cssselect2": re.compile(r"cssselect2-[\w.]+\.tar\.gz"),
    "imageio": re.compile(r"imageio-[\w.]+\.tar\.gz"),
    "imageio-test-images": re.compile(r"imageio-test-images-[0-9a-f]+-tag\.tar\.gz"),
    "python-dateutil": re.compile(r"python\-dateutil-[\w.]+\.tar\.gz"),
    "reportlab": re.compile(r"reportlab-[\w.]+\.tar\.gz"),
    "six": re.compile(r"six-[\w.]+\.tar\.gz"),
    "soupsieve": re.compile(r"soupsieve-[\w.]+\.tar\.gz"),
    "sympy": re.compile(r"sympy-[\w.]+\.tar\.gz"),
    "tabulate": re.compile(r"tabulate-[\w.]+\.tar\.gz"),
    "threadpoolctl": re.compile(r"threadpoolctl-[\w.]+-tag\.tar\.gz"),
    "tomli-w": re.compile(r"tomli_w-[\w.]+-tag\.tar\.gz"),
    "toolz": re.compile(r"toolz-[\w.]+\.tar\.gz"),
    "tqdm": re.compile(r"tqdm-[\w.]+\.tar\.gz"),
    "typing-extensions": re.compile(r"typing_extensions-[\w.]+\.tar\.gz"),
    "tzdata": re.compile(r"tzdata-[\w.]+\.tar\.gz"),
    "webencodings": re.compile(r"webencodings-[\w.]+\.tar\.gz"),
    "wrapt": re.compile(r"wrapt-[\w.]+\.tar\.gz"),
    "xlrd": re.compile(r"xlrd-[\w.]+-tag\.tar\.gz"),
    "xlsxwriter": re.compile(r"xlsxwriter-[\w.]+-tag\.tar\.gz"),
    "xmltodict": re.compile(r"xmltodict-[\w.]+\.tar\.gz"),
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


# A pinned member the build's walks would skip without a word.
PINNED_LITTER = "a pinned member with a name only an operating system leaves; the build skips it"


def tree_drift(tarball: Path, tree: Path, patches: Path | None = None) -> list[str]:
    """Every file that is missing or different in the tree, as 'path: why': against the tarball,
    or, when the tree has carried patches, against the tarball with them applied; and every
    subproject folder the tarball did not ship."""
    if patch_files(tree.name, patches):
        drift = _patched_drift(tarball, tree, (patches or PATCHES) / tree.name)
    else:
        drift = _tarball_drift(tarball, tree)
    return drift + added_subprojects(tarball, tree)


# A subproject folder in the tree that the tarball did not ship: a meson wrap fetched it.
ADDED_SUBPROJECT = "a subproject folder the tarball did not ship (a meson fallback fetched it)"


def added_subprojects(tarball: Path, tree: Path) -> list[str]:
    """Every folder directly under a `subprojects/` folder of the tree, at any depth, that is no
    member of the tarball and holds none, as 'path/: why'."""
    shipped = set()
    with tarfile.open(tarball) as t:
        for member in t:
            parts = member.name.strip("/").split("/")[1:]
            shipped.update("/".join(parts[:i]) for i in range(1, len(parts) + 1))
    found = []
    for folder, dirs, _ in os.walk(tree):
        if os.path.basename(folder) != "subprojects":
            continue
        base = Path(folder).relative_to(tree).as_posix()
        for name in sorted(dirs):
            rel = f"{base}/{name}"
            if rel not in shipped and not paths.has_litter(name):
                found.append(f"{rel}/: {ADDED_SUBPROJECT}")
    return sorted(found)


def _patched_drift(tarball: Path, tree: Path, patch_dir: Path) -> list[str]:
    # Under the project's own build/harness, never the system's temporary folder: the
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
                continue  # Finder's or Explorer's, written into this extraction
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
    """Removed with retries: a Finder window showing build/ can write litter into a
    folder while it is removed. One that still will not go is left under build/harness,
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
