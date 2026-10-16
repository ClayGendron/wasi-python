"""The v1.1 rules as functions over an artifact directory, so a self-test can run each one on a
good and a bad synthetic set (spec 002, criterion 7). Each returns a list of findings."""

from __future__ import annotations

import zipfile
from pathlib import Path

from harness import paths, wasm

PLAIN_EXPORTS = {"memory", "_initialize", "wizer.initialize", "run", "host_alloc"}
SNAPSHOT_EXPORTS = {"memory", "run", "host_alloc"}
SNAPSHOT_FORBIDDEN = {"_initialize", "wizer.initialize"}


def complete_errors(d: Path) -> list[str]:
    errors = [f"{name} is missing" for name in paths.ARTIFACT_FILES if not (d / name).is_file()]
    errors += [
        f"LICENSES/{c}.txt is missing"
        for c in paths.LICENCE_COMPONENTS
        if not (d / "LICENSES" / f"{c}.txt").is_file()
    ]
    return errors


def sums_errors(d: Path) -> list[str]:
    sums = d / "SHA256SUMS"
    if not sums.is_file():
        return ["SHA256SUMS is missing"]
    try:
        listed = paths.read_pin_list(sums)
    except ValueError as e:
        return [str(e)]
    present = {
        p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file() and p.name != "SHA256SUMS"
    }
    errors = [f"{f} is not listed in SHA256SUMS" for f in sorted(present - set(listed))]
    errors += [f"SHA256SUMS lists {f}, which is absent" for f in sorted(set(listed) - present)]
    errors += [
        f"{f} does not match its SHA256SUMS line"
        for f in sorted(present & set(listed))
        if paths.sha256_file(d / f) != listed[f]
    ]
    return errors


def cwasm_errors(d: Path) -> list[str]:
    return [
        f"{p.relative_to(d).as_posix()} is a compiled module" for p in sorted(d.rglob("*.cwasm"))
    ]


def module_errors(binary: Path) -> list[str]:
    try:
        mod = wasm.parse_file(binary)
    except wasm.WasmError as e:
        return [f"{binary.name}: {e}"]
    return [f"{binary.name}: {e}" for e in wasm.wall_errors(mod)]


def is_core_module_errors(binary: Path) -> list[str]:
    head = binary.read_bytes()[:8]
    if head[:4] != wasm.MAGIC:
        return [f"{binary.name}: not a wasm binary"]
    if head[4:8] != wasm.CORE_VERSION:
        return [f"{binary.name}: not a core module (version {head[4:8].hex()})"]
    return []


def export_errors(binary: Path, required: set[str], forbidden: set[str] = frozenset()) -> list[str]:
    try:
        exports = set(wasm.parse_file(binary).exports)
    except wasm.WasmError as e:
        return [f"{binary.name}: {e}"]
    errors = [f"{binary.name}: no export {name}" for name in sorted(required - exports)]
    errors += [f"{binary.name}: exports {name}" for name in sorted(forbidden & exports)]
    return errors


def stdlib_zip_errors(z: Path) -> list[str]:
    errors = []
    with zipfile.ZipFile(z) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            if info.filename.endswith(".py"):
                errors.append(f"{info.filename}: source, not bytecode")
            if info.compress_type != zipfile.ZIP_DEFLATED:
                errors.append(f"{info.filename}: stored, not deflated")
    return errors[:20]


SHARED_SUFFIXES = (".so", ".dylib", ".pyd", ".dll")


def shared_library_errors(z: Path) -> list[str]:
    with zipfile.ZipFile(z) as archive:
        return [n for n in archive.namelist() if n.endswith(SHARED_SUFFIXES)]


def wheel_errors(wheel: Path, d: Path) -> list[str]:
    errors = []
    with zipfile.ZipFile(wheel) as w:
        names = set(w.namelist())
        for p in sorted(d.rglob("*")):
            if not p.is_file():
                continue
            member = f"wasi_python/artifacts/{p.relative_to(d).as_posix()}"
            if member not in names:
                errors.append(f"{wheel.name} lacks {member}")
            elif paths.sha256_bytes(w.read(member)) != paths.sha256_file(p):
                errors.append(f"{wheel.name}: {member} differs from the artifact set")
    return errors
