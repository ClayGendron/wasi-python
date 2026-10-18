"""Assemble the artifact directory (spec 003, Decision 9): the two binaries, the stdlib zip, the
licence notices of everything inside, MANIFEST and SHA256SUMS, written to build/artifacts.new/ and
renamed to build/artifacts/ only when complete.

    assemble_artifacts.py <repository root>
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

import line
from litter import OS_LITTER

LINE = line.read()
PYTHON = LINE["PYTHON_VERSION"]
PACKAGES = {
    "numpy": "2.5.2",
    "pandas": "3.0.6",
    "zlib": "1.3.1",
    "bzip2": "1.0.8",
    "xz": "5.8.4",
    "sqlite-autoconf": "3540100",  # SQLite 3.54.1, named as its pin names it (spec 007)
    "python-dateutil": "2.9.0.post0",
    "tzdata": "2026.5",
    "six": "1.17.0",
    "regex": "2026.9.29",  # spec 047
    # matplotlib (spec 023): the package, its compiled dependencies, the C libraries linked in, the
    # header-only C++ compiled in, and the pure packages in the zip. qhull is built, not linked.
    "matplotlib": "3.11.2",
    "pillow": "13.0.0",
    "kiwisolver": "1.5.1",
    "freetype": "2.14.3",
    "harfbuzz": "14.1.0",
    "sheenbidi": "3.0.0",
    "libraqm": "0.10.5",
    "pybind11": "3.1.0",
    "cppy": "1.3.1",
    "cycler": "0.12.1",
    "pyparsing": "3.3.3",
    "packaging": "26.3",
    "fonttools": "4.67.0",
    # lxml (spec 046): the package and its two C libraries, linked in.
    "libxml2": "2.15.4",
    "libxslt": "1.1.45",
    "lxml": "6.1.3",
}
WHEELS = {
    "python-dateutil": "python_dateutil-2.9.0.post0-py2.py3-none-any.whl",
    "tzdata": "tzdata-2026.5-py2.py3-none-any.whl",
    "six": "six-1.17.0-py2.py3-none-any.whl",
    "pybind11": "pybind11-3.1.0-py3-none-any.whl",
    "cppy": "cppy-1.3.1-py3-none-any.whl",
    "cycler": "cycler-0.12.1-py3-none-any.whl",
    "pyparsing": "pyparsing-3.3.3-py3-none-any.whl",
    "packaging": "packaging-26.3-py3-none-any.whl",
    "fonttools": "fonttools-4.67.0-py3-none-any.whl",
}
# The Unicode data terms of HarfBuzz's tables, pinned as a file (spec 023, Decision 9).
UNICODE_TERMS = "unicodetools-4fd8eca9-LICENSE"
# The licence notices of what the SDK links in, named by the line's wasi-libc and LLVM commits.
WASI_LIBC = [
    f"wasi-libc-{LINE['WASI_LIBC_COMMIT']}-{name}"
    for name in (
        "LICENSE",
        "LICENSE-APACHE",
        "LICENSE-APACHE-LLVM",
        "LICENSE-MIT",
        "musl-COPYRIGHT",
        "cloudlibc-LICENSE",
    )
]
LLVM = [
    f"llvm-{LINE['LLVM_COMMIT']}-{component}-LICENSE.TXT"
    for component in ("libcxx", "libcxxabi", "libunwind", "compiler-rt")
]
RESEARCH_PINS = {"python-3.14.7-wasi_sdk-24.zip"}
# matplotlib's notices beside its LICENSE/ folder: Agg's, compiled in, and the fonts' that travel
# with mpl-data (the AFM files' readme must go with them; spec 023, Decision 9).
MPL_NOTICES = (
    "extern/agg24-svn/src/copying",
    "lib/matplotlib/mpl-data/fonts/ttf/LICENSE_DEJAVU",
    "lib/matplotlib/mpl-data/fonts/ttf/LICENSE_STIX",
    "lib/matplotlib/mpl-data/fonts/pdfcorefonts/readme.txt",
)
# libxml2's own notices beside its Copyright file (spec 046, Decision 15): the two files Copyright
# names as its exceptions, each under an ISC-style grant of its own, and timsort.h's MIT notice.
# Each is the comment at the file's head that holds these words; a file missing, or a notice not
# where it was, stops the build.
LIBXML2_NOTICES = (
    ("dict.c", ("Copyright (C) 2003-2012 Daniel Veillard.", "Permission to use, copy, modify")),
    (
        "list.c",
        ("Copyright (C) 2000 Gary Pennington and Daniel Veillard.", "Permission to use, copy"),
    ),
    ("timsort.h", ("The MIT License (MIT)", "Copyright (c) 2010-2017 Christopher Swenson.")),
)
# lxml's terms (spec 046, Decision 15): its licence, its list of the licences in its wheels (which
# bundle GNU libiconv and zlib; this build links neither), and the BSD and ElementTree texts.
LXML_NOTICES = (
    "LICENSE.txt",
    "LICENSES.txt",
    "doc/licenses/BSD.txt",
    "doc/licenses/elementtree.txt",
)
# What each carried patch to an Apache-2.0 file changes, for the notice Apache-2.0 §4(b) asks of
# a modified file (spec 047, Decision 10): keyed by the patch's path, which the notice names, so a
# patch added or deleted without its line here stops the build.
MODIFIED = {
    "recipes/patches/regex-2026.9.29/0001-callback-signatures.patch": (
        "five callbacks gain the parameter CPython passes"
    ),
}
PREIMPORT = "encodings, io, os, sys, json, csv, re, _colorize, numpy, pandas"
LICENCE_NAME = re.compile(r"(LICEN[CS]E|COPYING|NOTICE)[^/]*$", re.I)


def _remove(path: Path) -> None:
    """Remove a folder, retrying as scripts/steps/remove.sh does: Finder can write into it while
    it is emptied (spec 018). A path already gone is success."""
    for _ in range(3):
        if os.path.islink(path) or os.path.isfile(path):
            try:
                os.unlink(path)
            except OSError:
                pass
        else:
            shutil.rmtree(path, ignore_errors=True)  # goes on past an entry, as rm -rf does
        if not os.path.lexists(path):
            return
    raise SystemExit(f"ERROR: cannot remove {path}")


def drop_litter(folder: Path) -> None:
    """Delete Finder and Explorer litter from a folder this script made, before it is listed."""
    for p in sorted(folder.rglob("*")):
        if p.name in OS_LITTER and p.is_file():
            p.unlink()


def listed_files(folder: Path) -> list[Path]:
    """The set's files for SHA256SUMS. Litter written after drop_litter is never listed, so the
    judge and the wheel rule see it as a file the set does not list (spec 018)."""
    return sorted(p for p in folder.rglob("*") if p.is_file() and p.name not in OS_LITTER)


def licence_files(folder: Path) -> list[Path]:
    """A licence folder's files, without litter: each is packed into a LICENSES file."""
    return sorted(p for p in folder.iterdir() if p.name not in OS_LITTER)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def notice(parts: list[tuple[str, bytes]]) -> bytes:
    """The parts joined unaltered, each after a one-line header naming it."""
    out = b""
    for label, data in parts:
        out += f"==== {label} ====\n".encode() + data
        if not data.endswith(b"\n"):
            out += b"\n"
        out += b"\n"
    return out


def wheel_licences(wheel: Path) -> list[tuple[str, bytes]]:
    with zipfile.ZipFile(wheel) as z:
        names = sorted(
            n
            for n in z.namelist()
            if ".dist-info/" in n and not n.endswith("/") and LICENCE_NAME.search(n)
        )
        return [(f"{wheel.name}: {n}", z.read(n)) for n in names]


def hacl_notice(cp: Path) -> bytes:
    """The MIT notice at the head of HACL*'s sources, as CPython ships them."""
    text = (cp / "Modules" / "_hacl" / "Hacl_Hash_SHA2.h").read_text()
    end = text.index("*/")
    if "MIT License" not in text[:end] or "Permission is hereby granted" not in text[:end]:
        raise SystemExit("HACL*'s header no longer carries its MIT notice")
    return (text[: end + 2] + "\n").encode()


def sqlite_notice(b: Path) -> bytes:
    """SQLite has no licence file: it is public domain, and its blessing heads each source file."""
    text = (b / "sqlite-autoconf-3540100" / "sqlite3.h").read_text()
    end = text.index("*/")
    if "disclaims copyright" not in text[:end] or "May you do good" not in text[:end]:
        raise SystemExit("sqlite3.h no longer opens with SQLite's blessing")
    return (text[: end + 2] + "\n").encode()


def head_notice(path: Path, words: tuple[str, ...]) -> bytes:
    """The first of a C file's two leading comments that holds every one of `words`."""
    if not path.is_file():
        raise SystemExit(f"{path.name} is missing: its licence notice cannot be read")
    text = path.read_text()
    start = 0
    for _ in range(2):
        begin = text.find("/*", start)
        end = text.find("*/", begin)
        if begin < 0 or end < 0:
            break
        comment = text[begin : end + 2]
        if all(w in comment for w in words):
            return (comment + "\n").encode()
        start = end + 2
    raise SystemExit(f"{path.name} no longer opens with the notice {words[0]!r}")
def modified_notice(root: Path, top: str) -> bytes:
    """One line per carried patch of a tree: the files it changes, read from the patch itself,
    the patch's path and what it does; then that the rest is compiled as released."""
    lines = []
    for patch in sorted((root / "recipes" / "patches" / top).glob("[0-9][0-9][0-9][0-9]-*.patch")):
        rel = patch.relative_to(root).as_posix()
        if rel not in MODIFIED:
            raise SystemExit(f"{rel}: no line in MODIFIED says what it changes")
        files = re.findall(r"^\+\+\+ b/(\S+)$", patch.read_text(), re.M)
        if not files:
            raise SystemExit(f"{rel}: changes no file")
        lines.append(
            f"This build modifies {', '.join(files)} with {rel} ({MODIFIED[rel]}); "
            "the module is otherwise compiled as released.\n"
        )
    if not lines:
        raise SystemExit(f"recipes/patches/{top}: no carried patch, so no modification notice")
    return "".join(lines).encode()


def main() -> None:
    root = Path(sys.argv[1]).resolve()
    b, d = root / "build", root / "downloads"
    untracked = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "ls-files",
            "--others",
            "--exclude-standard",
            "recipes",
            "scripts",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    if untracked:
        raise SystemExit(f"untracked recipe files (stage them first): {', '.join(untracked)}")

    new, final = b / "artifacts.new", b / "artifacts"
    _remove(new)
    (new / "LICENSES").mkdir(parents=True)
    for name in ("python.wasm", "python-snapshot.wasm", "python-stdlib.zip"):
        shutil.copyfile(b / "out" / name, new / name)

    cp, np_src, pd_src = b / f"Python-{PYTHON}", b / "numpy-2.5.2", b / "pandas-3.0.6"
    numpy_files = tomllib.loads((np_src / "pyproject.toml").read_text())["project"]["license-files"]
    licences = {
        "cpython": [
            ("CPython LICENSE", (cp / "LICENSE").read_bytes()),
            ("CPython Doc/license.rst", (cp / "Doc" / "license.rst").read_bytes()),
            # HACL* (hashlib's hashes) is compiled in and license.rst does not cover it; its MIT
            # notice is the header comment of each of its files.
            ("CPython Modules/_hacl (HACL*), the header of Hacl_Hash_SHA2.h", hacl_notice(cp)),
        ],
        "numpy": [(f"numpy {f}", (np_src / f).read_bytes()) for f in numpy_files],
        "pandas": [("pandas LICENSE", (pd_src / "LICENSE").read_bytes())]
        + [
            (f"pandas LICENSES/{p.name}", p.read_bytes())
            for p in licence_files(pd_src / "LICENSES")
        ],
        "zlib": [("zlib LICENSE", (b / "zlib-1.3.1" / "LICENSE").read_bytes())],
        "bzip2": [("bzip2 LICENSE", (b / "bzip2-1.0.8" / "LICENSE").read_bytes())],
        # Only liblzma is linked, and its files are 0BSD (COPYING says which parts are which).
        "xz": [
            (f"xz {n}", (b / "xz-5.8.4" / n).read_bytes()) for n in ("COPYING", "COPYING.0BSD")
        ],
        "sqlite": [("SQLite sqlite3.h, its header comment", sqlite_notice(b))],
        # spec 023, Decision 9: FreeType's BDF and PCF drivers are built, so their notices ship.
        "freetype": [
            (f"FreeType {n}", (b / "freetype-2.14.3" / n).read_bytes())
            for n in ("LICENSE.TXT", "docs/FTL.TXT", "src/bdf/README", "src/pcf/README")
        ],
        "harfbuzz": [
            (f"HarfBuzz {n}", (b / "harfbuzz-14.1.0" / n).read_bytes())
            for n in ("COPYING", "src/ms-use/COPYING")
        ]
        + [(f"Unicode's data terms ({UNICODE_TERMS})", (d / UNICODE_TERMS).read_bytes())],
        "sheenbidi": [("SheenBidi LICENSE", (b / "SheenBidi-3.0.0" / "LICENSE").read_bytes())],
        "libraqm": [("libraqm COPYING", (b / "libraqm-0.10.5" / "COPYING").read_bytes())],
        "matplotlib": [
            (f"matplotlib LICENSE/{p.name}", p.read_bytes())
            for p in licence_files(b / "matplotlib-3.11.2" / "LICENSE")
        ]
        + [(f"matplotlib {n}", (b / "matplotlib-3.11.2" / n).read_bytes()) for n in MPL_NOTICES],
        "pillow": [("Pillow LICENSE", (b / "pillow-13.0.0" / "LICENSE").read_bytes())],
        "kiwisolver": [("kiwisolver LICENSE", (b / "kiwisolver-1.5.1" / "LICENSE").read_bytes())],
        "libxml2": [("libxml2 Copyright", (b / "libxml2-2.15.4" / "Copyright").read_bytes())]
        + [
            (f"libxml2 {n}, its head comment", head_notice(b / "libxml2-2.15.4" / n, words))
            for n, words in LIBXML2_NOTICES
        ],
        "libxslt": [("libxslt Copyright", (b / "libxslt-1.1.45" / "Copyright").read_bytes())],
        "lxml": [(f"lxml {n}", (b / "lxml-6.1.3" / n).read_bytes()) for n in LXML_NOTICES],
        # spec 047, Decision 10: Apache-2.0 headed by its CNRI derivation, then the modified file
        "regex": [
            ("regex LICENSE.txt", (b / "regex-2026.9.29" / "LICENSE.txt").read_bytes()),
            ("regex, as this build compiles it", modified_notice(root, "regex-2026.9.29")),
        ],
        **{pkg: wheel_licences(d / wheel) for pkg, wheel in WHEELS.items()},
        "wasi-libc": [(name, (d / name).read_bytes()) for name in WASI_LIBC],
        "llvm-runtimes": [(name, (d / name).read_bytes()) for name in LLVM],
    }
    for component, parts in licences.items():
        if not parts:
            raise SystemExit(f"no licence text found for {component}")
        (new / "LICENSES" / f"{component}.txt").write_bytes(notice(parts))

    pins = [
        line.split()
        for line in (d / "SHA256SUMS").read_text().splitlines()
        if line.strip() and line.split()[1] not in RESEARCH_PINS
    ]
    tracked = subprocess.run(
        ["git", "-C", str(root), "ls-files", "recipes", "scripts"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    recipes = sorted(f for f in tracked if not Path(f).name.startswith("bench_"))
    wizer = (b / "out" / "wizer-command.txt").read_text().strip()
    manifest = [f"python {PYTHON}"]
    manifest += [f"package {name} {version}" for name, version in PACKAGES.items()]
    manifest += [f"pin {sha} {name}" for sha, name in pins]
    manifest += [f"recipe {sha256(root / f)} {f}" for f in recipes]
    manifest += [
        # The pin lines are every supported build host's inputs, not only this build's: each host
        # builds the same bytes, so MANIFEST is the same file from any of them (spec 012).
        "x-pins every-supported-build-host",
        f"x-wizer {wizer}",
        f"x-source-date-epoch {os.environ['SOURCE_DATE_EPOCH']}",
        f"x-preimport {PREIMPORT}",
        f"x-snapshot-zip {sha256(new / 'python-stdlib.zip')}",
    ]
    (new / "MANIFEST").write_text("\n".join(manifest) + "\n")

    drop_litter(new)
    files = listed_files(new)
    (new / "SHA256SUMS").write_text(
        "".join(f"{sha256(p)}  {p.relative_to(new).as_posix()}\n" for p in files)
    )
    _remove(final)
    new.rename(final)
    print(f"artifacts: {len(files) + 1} files in build/artifacts")


if __name__ == "__main__":
    main()
