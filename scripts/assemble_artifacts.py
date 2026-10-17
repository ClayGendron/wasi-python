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

LINE = line.read()
PYTHON = LINE["PYTHON_VERSION"]
PACKAGES = {
    "numpy": "2.5.2",
    "pandas": "3.0.6",
    "zlib": "1.3.1",
    "python-dateutil": "2.9.0.post0",
    "tzdata": "2026.5",
    "six": "1.17.0",
}
WHEELS = {
    "python-dateutil": "python_dateutil-2.9.0.post0-py2.py3-none-any.whl",
    "tzdata": "tzdata-2026.5-py2.py3-none-any.whl",
    "six": "six-1.17.0-py2.py3-none-any.whl",
}
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
PREIMPORT = "encodings, io, os, sys, json, csv, re, _colorize, numpy, pandas"
LICENCE_NAME = re.compile(r"(LICEN[CS]E|COPYING|NOTICE)[^/]*$", re.I)


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
    shutil.rmtree(new, ignore_errors=True)
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
            for p in sorted((pd_src / "LICENSES").iterdir())
        ],
        "zlib": [("zlib LICENSE", (b / "zlib-1.3.1" / "LICENSE").read_bytes())],
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
        f"x-wizer {wizer}",
        f"x-source-date-epoch {os.environ['SOURCE_DATE_EPOCH']}",
        f"x-preimport {PREIMPORT}",
        f"x-snapshot-zip {sha256(new / 'python-stdlib.zip')}",
    ]
    (new / "MANIFEST").write_text("\n".join(manifest) + "\n")

    files = sorted(p for p in new.rglob("*") if p.is_file())
    (new / "SHA256SUMS").write_text(
        "".join(f"{sha256(p)}  {p.relative_to(new).as_posix()}\n" for p in files)
    )
    shutil.rmtree(final, ignore_errors=True)
    new.rename(final)
    print(f"artifacts: {len(files) + 1} files in build/artifacts")


if __name__ == "__main__":
    main()
