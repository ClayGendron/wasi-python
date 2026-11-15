"""The crates cargo reads offline, in the directory source step 52 points crates-io at.

    rust_vendor.py crates <Cargo.lock> <SHA256SUMS> <downloads> <vendor>
    rust_vendor.py std <rust-src's library/vendor> <vendor>

**crates.** Each package of the lock that comes from crates.io is a pinned `<name>-<version>.crate`
in downloads/. Its SHA-256 must be both its pin and the lock's checksum. It is unpacked into
`<vendor>/<name>-<version>/` with a `.cargo-checksum.json` as `cargo vendor` writes one: `package`
is the archive's SHA-256 and `files` holds every unpacked file's, read from the archive's
members (less the git files `cargo vendor` leaves out),
so cargo refuses a file changed after unpacking (an empty `files` would turn that check off). An
archive member that is not a plain file or folder under the crate's own folder stops the step.

**std.** Under `-Zbuild-std` cargo resolves the standard library's own dependencies through
crates-io too, so rust-src's vendored crates are copied beside the pinned ones; they are pinned by
rust-src's SHA-256 and carry their own `.cargo-checksum.json`. A name and version in both folders
must hold the same files with the same bytes, or the step stops.

One line per finding; exit 1 on any.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
import tarfile
from pathlib import Path

CRATES_IO = "registry+https://github.com/rust-lang/crates.io-index"
CHECKSUM = ".cargo-checksum.json"
PACKAGE = re.compile(r"^\[\[package\]\]\n((?:[a-z]+ = .*\n?)+)", re.M)
FIELD = re.compile(r'^([a-z]+) = "([^"]*)"$', re.M)
# The names `cargo vendor` leaves out at any depth, so a pinned crate unpacks to what rust-src's
# vendored copy of the same crate holds.
SKIPPED = frozenset((".gitattributes", ".gitignore", ".git"))


def lock_crates(text: str) -> list[tuple[str, str, str]]:
    """(name, version, checksum) of each crates.io package of a Cargo.lock, in its order."""
    out = []
    for block in PACKAGE.findall(text):
        fields = dict(FIELD.findall(block))
        if fields.get("source") == CRATES_IO:
            out.append((fields["name"], fields["version"], fields.get("checksum", "")))
    return out


def read_pins(text: str) -> dict[str, str]:
    """name -> SHA-256 of each `<sha>  <name>` line."""
    pins = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2:
            pins[parts[1]] = parts[0]
    return pins


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def unpack_crate(archive: Path, top: str, dest: Path) -> dict[str, str]:
    """Unpack the crate archive's `top/` folder into dest; relative path -> SHA-256 of each file."""
    files: dict[str, str] = {}
    with tarfile.open(archive, "r:gz") as tar:
        for info in tar:
            parts = info.name.split("/")
            if parts[0] != top or ".." in parts or info.name.startswith("/"):
                raise ValueError(f"{archive.name}: a member outside {top}/: {info.name}")
            rel = "/".join(p for p in parts[1:] if p)
            if SKIPPED & set(parts):
                continue
            if info.isdir():
                (dest / rel).mkdir(parents=True, exist_ok=True)
                continue
            if not info.isfile():
                raise ValueError(f"{archive.name}: a member that is not a plain file: {info.name}")
            if rel == CHECKSUM:
                raise ValueError(f"{archive.name}: carries its own {CHECKSUM}")
            data = tar.extractfile(info).read()
            (dest / rel).parent.mkdir(parents=True, exist_ok=True)
            (dest / rel).write_bytes(data)
            files[rel] = _sha(data)
    return files


def crates_main(argv: list[str]) -> int:
    lock, sums, downloads, vendor = (Path(a) for a in argv)
    pins = read_pins(sums.read_text(encoding="utf-8"))
    errors, n = [], 0
    for name, version, checksum in lock_crates(lock.read_text(encoding="utf-8")):
        file = f"{name}-{version}.crate"
        path = downloads / file
        if file not in pins:
            errors.append(f"{file} is not pinned")
            continue
        if not path.is_file():
            errors.append(f"downloads/{file} is missing: run scripts/00_download.sh")
            continue
        sha = _sha(path.read_bytes())
        if sha != pins[file]:
            errors.append(f"downloads/{file} does not match its pin")
            continue
        if sha != checksum:
            errors.append(f"{file}'s pin is not the lock's checksum {checksum or '(none)'}")
            continue
        dest = vendor / f"{name}-{version}"
        if dest.exists():
            shutil.rmtree(dest)
        files = unpack_crate(path, f"{name}-{version}", dest)
        if "Cargo.toml" not in files:
            errors.append(f"{file} holds no Cargo.toml")
            continue
        body = {"files": dict(sorted(files.items())), "package": sha}
        (dest / CHECKSUM).write_text(json.dumps(body, sort_keys=True), encoding="utf-8")
        n += 1
    for e in errors:
        print(f"ERROR: {e}")
    if errors:
        return 1
    print(f"crates: {n} pinned crates unpacked, each file's SHA-256 in its {CHECKSUM}")
    return 0


def tree(root: Path) -> dict[str, bytes]:
    """relative path -> bytes of every file under root but its checksum file."""
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file() and p.relative_to(root).as_posix() != CHECKSUM
    }


def std_main(argv: list[str]) -> int:
    source, vendor = (Path(a) for a in argv)
    errors, copied, same = [], 0, 0
    for crate in sorted(p for p in source.iterdir() if p.is_dir()):
        dest = vendor / crate.name
        if not (crate / CHECKSUM).is_file():
            errors.append(f"rust-src's {crate.name} has no {CHECKSUM}")
        elif dest.exists():
            if tree(crate) != tree(dest):
                errors.append(f"{crate.name} differs between rust-src and its crates.io pin")
            else:
                same += 1
        else:
            shutil.copytree(crate, dest)
            copied += 1
    for e in errors:
        print(f"ERROR: {e}")
    if errors:
        return 1
    print(f"std: {copied} of rust-src's vendored crates copied, {same} the same bytes as a pin")
    return 0


MODES = {"crates": (crates_main, 4), "std": (std_main, 2)}


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in MODES or len(argv) - 1 != MODES[argv[0]][1]:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    return MODES[argv[0]][0](argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
