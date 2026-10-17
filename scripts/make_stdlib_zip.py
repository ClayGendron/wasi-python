"""Build the stdlib zip: bytecode-only, deflated and deterministic (spec 003, Decision 7).

    make_stdlib_zip.py --lib <CPython Lib/> [--tree <dir whose children go to the zip root>]...
        [--wheel <pinned wheel>]... [--file <source>=<name in zip>]... [--skip <top-level name>]...
        [--replace <old>=<new>]... out.zip

Every .py becomes a .pyc compiled in process (the running interpreter's bytecode magic must be the
guest's: both are the line's version, scripts/line.conf; UNCHECKED_HASH, so no source mtime is consulted). Every member is deflated
at level 9 with the timestamp 1980-01-01 00:00 and mode 0644, in sorted order, so the same inputs
give the same bytes. Run it with PYTHONHASHSEED=0: set and frozenset constants are marshalled in
hash order.

_sysconfigdata and numpy's __config__.py say nothing about the build host, so the zip is the same
bytes from any host (spec 012, Decision 5). Their host keys are set to fixed values, whatever the
host wrote (HOST_KEYS, NUMPY_BUILD_KEYS); a key that is absent, or that does not read back as its
fixed value once rewritten, stops the build. Then each --replace rewrites its text in the two, in
the order given; an old text found in neither stops the build. Both run before compiling.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import os
import re
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
# build_time_vars keys that record the build host's tools, and the value each is given. The
# INSTALL* keys keep their own flags after `install -c`.
HOST_KEYS = {"BUILD_GNU_TYPE": "build", "GNULD": "no", "MKDIR_P": "mkdir -p"}
INSTALL_KEYS = ("INSTALL", "INSTALL_DATA", "INSTALL_PROGRAM", "INSTALL_SCRIPT", "INSTALL_SHARED")
INSTALL = re.compile(r"\S*install -c((?: \S+)*)")
# numpy's "Machine Information" -> "build" keys; its "endian" stays.
NUMPY_BUILD_KEYS = {"cpu": "build", "family": "build", "system": "build"}


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


def _str_items(node: ast.expr) -> dict[str, ast.expr]:
    """A dict display's string-keyed items, or nothing when the node is not a dict display."""
    if not isinstance(node, ast.Dict):
        return {}
    return {
        k.value: v
        for k, v in zip(node.keys, node.values, strict=True)
        if isinstance(k, ast.Constant) and isinstance(k.value, str)
    }


def _host_items(tree: ast.Module, name: str) -> dict[str, ast.expr]:
    """The dict whose keys record the build host: _sysconfigdata's build_time_vars, or numpy's
    CONFIG["Machine Information"]["build"]."""
    if "_sysconfigdata" in name:
        for node in tree.body:
            if (
                isinstance(node, ast.Assign)
                and [getattr(t, "id", None) for t in node.targets] == ["build_time_vars"]
                and isinstance(node.value, ast.Dict)
            ):
                return _str_items(node.value)
        raise SystemExit(f"{name}: no build_time_vars dict")
    for node in ast.walk(tree):
        machine = _str_items(_str_items(node).get("Machine Information"))
        if isinstance(machine.get("build"), ast.Dict):
            return _str_items(machine["build"])
    raise SystemExit(f"{name}: no Machine Information build dict")


def _fixed_values(items: dict[str, ast.expr], name: str) -> dict[str, str]:
    """Each host key's fixed value; one line and a stop for a key that is absent."""
    sysconfig = "_sysconfigdata" in name
    wanted = [*HOST_KEYS, *INSTALL_KEYS] if sysconfig else list(NUMPY_BUILD_KEYS)
    missing = [key for key in wanted if key not in items]
    if missing:
        raise SystemExit(f"{name}: no {', '.join(missing)} to make host-neutral")
    if not sysconfig:
        return dict(NUMPY_BUILD_KEYS)
    keys = dict(HOST_KEYS)
    for key in INSTALL_KEYS:
        old = ast.literal_eval(items[key])
        m = INSTALL.fullmatch(old) if isinstance(old, str) else None
        if m is None:
            raise SystemExit(f"{name}: {key} is {old!r}, not an `install -c` command")
        keys[key] = "install -c" + m[1]
    return keys


def host_neutral(text: str, name: str) -> str:
    """The member with its host keys set to their fixed values, read back to prove it."""
    data = text.encode()
    starts = [0]
    for row in data.splitlines(keepends=True):
        starts.append(starts[-1] + len(row))
    items = _host_items(ast.parse(data), name)
    fixed = _fixed_values(items, name)
    spans = []
    for key, value in fixed.items():
        node = items[key]  # col offsets are UTF-8 byte offsets, so the splice is on bytes
        start = starts[node.lineno - 1] + node.col_offset
        end = starts[node.end_lineno - 1] + node.end_col_offset
        spans.append((start, end, repr(value).encode()))
    for start, end, new in sorted(spans, reverse=True):
        data = data[:start] + new + data[end:]
    again = _host_items(ast.parse(data), name)
    wrong = sorted(k for k, v in fixed.items() if ast.literal_eval(again[k]) != v)
    if wrong:
        raise SystemExit(f"{name}: {', '.join(wrong)} did not read back as fixed")
    return data.decode()


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
    if any(not old for old, _ in replacements):
        raise SystemExit("--replace with an empty old text")  # before any rewrite runs
    found: set[str] = set()
    rewritten: set[str] = set()

    entries: dict[str, bytes] = {}

    def add(data: bytes, name: str, origin: str) -> None:
        if name.endswith(".py"):
            kind = next((key for key in REWRITE if key in name), None)
            if kind is not None:
                text = host_neutral(data.decode(), name)
                for old, new in replacements:
                    found.update([old] if old in text else [])
                    text = text.replace(old, new)
                data = text.encode()
                rewritten.add(kind)
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

    if rewritten != set(REWRITE):
        raise SystemExit(f"no member to make host-neutral for {sorted(set(REWRITE) - rewritten)}")
    for old, _ in replacements:
        if old not in found:
            raise SystemExit(f"--replace {old!r}: in neither _sysconfigdata nor numpy's __config__")

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
