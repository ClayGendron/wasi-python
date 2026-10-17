"""Build the stdlib zip: bytecode-only, deflated and deterministic (spec 003, Decision 7).

    make_stdlib_zip.py --lib <CPython Lib/> [--tree <dir whose children go to the zip root>]...
        [--wheel <pinned wheel>]... [--file <source>=<name in zip>]... [--skip <top-level name>]...
        [--replace <old>=<new>]... out.zip

Every .py becomes a .pyc compiled in process (the running interpreter's bytecode magic must be the
guest's: both are the line's version, scripts/line.conf; UNCHECKED_HASH, so no source mtime is consulted). Every member is deflated
at level 9 with the timestamp 1980-01-01 00:00 and mode 0644, in sorted order, so the same inputs
give the same bytes. Run it with PYTHONHASHSEED=0: set and frozenset constants are marshalled in
hash order. --replace rewrites text in _sysconfigdata and numpy's __config__.py before compiling,
so the zip carries no builder's path.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
import zipfile
from importlib._bootstrap_external import _code_to_hash_pyc
from pathlib import Path, PurePosixPath

import line

TARGET = line.target()
SKIP_DIRS = {
    "__pycache__",
    "test",
    "tests",
    "idlelib",
    "tkinter",
    "turtledemo",
    "ensurepip",
    "venv",
    "site-packages",
}
SKIP_SUFFIXES = {".pyi", ".pxd", ".pyx", ".pxi", ".h", ".c", ".cpp", ".so", ".deps", ".a"}
SKIP_NAMES = {"conftest.py", "meson.build"}
REWRITE = ("_sysconfigdata", "numpy/__config__.py")
EPOCH = (1980, 1, 1, 0, 0, 0)


def walk(root: Path, skip_top: frozenset[str] = frozenset()):
    """(file, name in zip) for every member of a tree, skipping tests, sources and caches."""
    for dirpath, dirnames, filenames in os.walk(root):
        here = Path(dirpath)
        rel = here.relative_to(root)
        dirnames[:] = sorted(
            d
            for d in dirnames
            if d not in SKIP_DIRS
            and not d.endswith(".dist-info")
            and not (rel == Path(".") and d in skip_top)
        )
        for f in sorted(filenames):
            p = here / f
            if p.suffix in SKIP_SUFFIXES or f in SKIP_NAMES or f.endswith((".so", ".so.deps")):
                continue
            if rel == Path(".") and Path(f).stem in skip_top:
                continue
            yield p.read_bytes(), str(PurePosixPath(*rel.parts, f))


def wheel_members(wheel: Path):
    with zipfile.ZipFile(wheel) as z:
        for info in sorted(z.infolist(), key=lambda i: i.filename):
            name = info.filename
            top = name.split("/", 1)[0]
            if info.is_dir() or top.endswith(".dist-info") or top.endswith(".data"):
                continue
            parts = set(name.split("/"))
            if parts & SKIP_DIRS or PurePosixPath(name).suffix in SKIP_SUFFIXES:
                continue
            yield z.read(name), name


def pyc(source: bytes, name: str) -> bytes:
    code = compile(source, name, "exec", dont_inherit=True, optimize=0)
    return bytes(_code_to_hash_pyc(code, importlib.util.source_hash(source), checked=False))


def member(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=EPOCH)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    info.create_system = 3  # unix, so the mode is read the same way everywhere
    return info


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lib", required=True, type=Path)
    ap.add_argument("--tree", action="append", default=[], type=Path)
    ap.add_argument("--wheel", action="append", default=[], type=Path)
    ap.add_argument("--file", action="append", default=[])
    ap.add_argument("--skip", action="append", default=[])
    ap.add_argument("--replace", action="append", default=[])
    ap.add_argument("out", type=Path)
    a = ap.parse_args()
    if sys.version_info[:2] != TARGET:
        raise SystemExit(
            f"compile with Python {TARGET[0]}.{TARGET[1]}, not {sys.version.split()[0]}"
        )
    if os.environ.get("PYTHONHASHSEED") != "0":
        raise SystemExit("run with PYTHONHASHSEED=0: sets are marshalled in hash order")
    replacements = [tuple(r.split("=", 1)) for r in a.replace]

    entries: dict[str, bytes] = {}

    def add(data: bytes, name: str, origin: str) -> None:
        if name.endswith(".py"):
            if any(key in name for key in REWRITE):
                text = data.decode()
                for old, new in replacements:
                    text = text.replace(old, new)
                data = text.encode()
            data, name = pyc(data, name), name + "c"
        if name in entries:
            raise SystemExit(f"{name} comes from two inputs (the second: {origin})")
        entries[name] = data

    for data, name in walk(a.lib, frozenset(a.skip)):
        add(data, name, str(a.lib))
    for tree in a.tree:
        for data, name in walk(tree):
            add(data, name, str(tree))
    for wheel in a.wheel:
        for data, name in wheel_members(wheel):
            add(data, name, wheel.name)
    for spec in a.file:
        src, _, name = spec.partition("=")
        add(Path(src).read_bytes(), name, src)

    a.out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(a.out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name in sorted(entries):
            z.writestr(
                member(name), entries[name], compress_type=zipfile.ZIP_DEFLATED, compresslevel=9
            )
    n_pyc = sum(name.endswith(".pyc") for name in entries)
    print(
        f"{a.out.name}: {n_pyc} pyc, {len(entries) - n_pyc} data files, "
        f"{a.out.stat().st_size} bytes"
    )


if __name__ == "__main__":
    main()
