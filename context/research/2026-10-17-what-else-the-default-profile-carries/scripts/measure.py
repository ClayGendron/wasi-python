"""Measure each installed candidate as step 70 would pack it.

    measure.py <pkgs dir> <out.tsv> <zips dir>

For every pkgs/<name>/ (one distribution, installed with --no-deps): the version, the licence
metadata, the runtime requirements, whether it carries native code, and the members and deflated
bytes it would add to the stdlib zip under step 70's rules (scripts/make_stdlib_zip.py: .py
compiled to .pyc, tests/sources/caches skipped, dist-info and .data skipped). Also writes
<zips dir>/<name>.zip, the members as step 70 would write them, for the guest experiment.
Run with the line's host Python 3.15 so the .pyc are the guest's bytecode.
"""

from __future__ import annotations

import email.parser
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath

# step 70's rules, as scripts/make_stdlib_zip.py states them
SKIP_DIRS = {"__pycache__", "test", "tests", "idlelib", "tkinter", "turtledemo", "ensurepip",
             "venv", "site-packages"}
SKIP_SUFFIXES = {".pyi", ".pxd", ".pyx", ".pxi", ".h", ".c", ".cpp", ".so", ".deps", ".a"}
SKIP_NAMES = {"conftest.py", "meson.build", ".DS_Store"}
NATIVE = {".so", ".pyd", ".dylib"}
EPOCH = (1980, 1, 1, 0, 0, 0)

IMPORT_RE = {
    "metadata": re.compile(rb"importlib[._]metadata|importlib_metadata|pkg_resources"),
    "threading": re.compile(rb"^\s*(?:import|from)\s+(?:threading|concurrent|multiprocessing)\b", re.M),
    "network": re.compile(rb"^\s*(?:import|from)\s+(?:socket|ssl|http\.client|urllib\.request|urllib3|requests|httpx)\b", re.M),
    "subprocess": re.compile(rb"^\s*(?:import|from)\s+subprocess\b", re.M),
    "ctypes": re.compile(rb"^\s*(?:import|from)\s+(?:ctypes|cffi)\b", re.M),
}


def meta(d: Path):
    infos = list(d.glob("*.dist-info/METADATA"))
    if not infos:
        return {}
    m = email.parser.Parser().parsestr(infos[0].read_text(errors="replace"))
    return m


def licence(m) -> str:
    expr = m.get("License-Expression")
    if expr:
        return expr
    lic = (m.get("License") or "").strip().splitlines()
    lic = lic[0][:40] if lic else ""
    cls = [c.split("::")[-1].strip() for c in m.get_all("Classifier") or [] if c.startswith("License ::")]
    return "; ".join(x for x in [lic] + cls if x) or "?"


def requires(m) -> str:
    out = []
    for r in m.get_all("Requires-Dist") or []:
        if "extra ==" in r:
            continue
        out.append(re.split(r"[\s;<>=!~\[(]", r.strip())[0])
    return ",".join(out)


def members(d: Path):
    for p in sorted(d.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(d)
        top = rel.parts[0]
        if top.endswith(".dist-info") or top.endswith(".data") or top in {"bin", "share", "include"}:
            continue
        if top.endswith(".libs") or ".dylibs" in rel.parts:
            continue
        if set(rel.parts[:-1]) & SKIP_DIRS or rel.name in SKIP_NAMES:
            continue
        if p.suffix in SKIP_SUFFIXES or p.suffix in NATIVE or p.suffix == ".pyc":
            continue
        yield p, rel


def main() -> None:
    pkgs, out, zips = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    zips.mkdir(parents=True, exist_ok=True)
    rows = ["name\tversion\tlicence\trequires\tnative_files\tnative_bytes\tmembers\tpy_members\tdeflated_bytes\tunpacked_bytes\tmetadata\tthreading\tnetwork\tsubprocess\tctypes\ttops"]
    for d in sorted(pkgs.iterdir()):
        if not d.is_dir():
            continue
        m = meta(d)
        native = [p for p in d.rglob("*") if p.is_file() and (p.suffix in NATIVE or ".so" in p.suffixes)]
        nbytes = sum(p.stat().st_size for p in native)
        n = npy = unpacked = 0
        hits = {k: 0 for k in IMPORT_RE}
        tops = set()
        zpath = zips / f"{d.name}.zip"
        with zipfile.ZipFile(zpath, "w") as z:
            for p, rel in members(d):
                data = p.read_bytes()
                name = PurePosixPath(*rel.parts)
                tops.add(rel.parts[0].removesuffix(".py"))
                if p.suffix == ".py":
                    for k, rx in IMPORT_RE.items():
                        if rx.search(data):
                            hits[k] += 1
                    try:
                        code = compile(data, str(name), "exec", dont_inherit=True, optimize=0)
                    except SyntaxError:
                        continue
                    from importlib._bootstrap_external import _code_to_hash_pyc
                    import importlib.util
                    data = bytes(_code_to_hash_pyc(code, importlib.util.source_hash(data), checked=False))
                    name = name.with_suffix(".pyc")
                    npy += 1
                info = zipfile.ZipInfo(str(name), EPOCH)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                z.writestr(info, data, compresslevel=9)
                n += 1
                unpacked += len(data)
        deflated = sum(i.compress_size for i in zipfile.ZipFile(zpath).infolist())
        rows.append("\t".join(map(str, [
            d.name, m.get("Version", "?"), licence(m), requires(m), len(native), nbytes, n, npy,
            deflated, unpacked, *hits.values(), ",".join(sorted(tops))])))
    out.write_text("\n".join(rows) + "\n")


if __name__ == "__main__":
    main()
