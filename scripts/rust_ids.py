"""The rustc wrapper step 52 gives cargo, so a crate's identity does not depend on the build host.

    rust_ids.py <root> <rustc> <rustc's arguments>...

Cargo names every crate it compiles with `-C metadata=<hash>`, and rustc derives the crate's
identity from it: the disambiguator in every mangled symbol, and the hashes that order and name
what the crate defines. For a crate built for the guest, cargo leaves the host's triple out of
that hash, but it mixes in the hashes of the crate's dependencies, and a build script or a proc
macro is compiled for the host, with the host's `rustc -vV` (its `host:` line among it) in its
hash. orjson, the standard library and almost every crate between have a build script, so the
same sources gave a library of other bytes on each build host.

Here each compile's `-C metadata` is replaced by a hash of what the compile is: its arguments
with the build's root path made one word, cargo's own hashes and the output and search folders
left out, and each dependency named by its own replaced hash, read from the `.rustc-id` file
written beside it. A dependency built for the host (a proc macro) is named by its crate name
alone in a guest crate's hash, so nothing that varies with the host's own compile reaches the
guest's bytes. `-C extra-filename` stays cargo's, so cargo finds the files it expects. A call
that names no crate (cargo's `-vV` and `--print` queries) runs unchanged.
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

ROOT_WORD = "/wasi-python-root"
ID_SUFFIX = ".rustc-id"
# Arguments that change no byte rustc writes: how it reports, where it reads and writes.
QUIET_PREFIXES = ("--error-format=", "--json=", "--diagnostic-width=", "--color=")
PAIRED_DROPPED = frozenset(("--out-dir", "-L"))
CODEGEN_DROPPED = ("metadata=", "extra-filename=")
LIBRARY_SUFFIXES = (".rlib", ".rmeta", ".so", ".dylib", ".dll", ".a")


class IdError(Exception):
    pass


def _value(args: list[str], flag: str) -> str | None:
    """The value of a flag given as `flag value` or `flag=value`; the last one wins."""
    found = None
    for i, a in enumerate(args):
        if a == flag and i + 1 < len(args):
            found = args[i + 1]
        elif a.startswith(flag + "="):
            found = a[len(flag) + 1 :]
    return found


def _codegen(args: list[str], key: str) -> str | None:
    """The value of `-C key=value` (or `-Ckey=value`); the last one wins."""
    found = None
    for i, a in enumerate(args):
        if a == "-C" and i + 1 < len(args):
            opt = args[i + 1]
        elif a.startswith("-C") and len(a) > 2:
            opt = a[2:]
        else:
            continue
        if opt.startswith(key + "="):
            found = opt[len(key) + 1 :]
    return found


def id_file(path: Path) -> Path:
    """The `.rustc-id` file beside a library: its name less the library suffix."""
    name = path.name
    for suffix in LIBRARY_SUFFIXES:
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    return path.with_name(name + ID_SUFFIX)


def read_id(path: Path) -> tuple[str, str]:
    """A dependency's (kind, id), kind being `guest` or `host`."""
    f = id_file(path)
    try:
        kind, ident = f.read_text().split()
    except (OSError, ValueError) as e:
        raise IdError(
            f"no crate id beside {path} ({f.name}): was it compiled through this wrapper?"
        ) from e
    return kind, ident


def _extern(spec: str, guest: bool) -> str:
    """An `--extern [opts:]name[=path]` with the path replaced by what the dependency is."""
    if "=" not in spec:
        return spec
    head, path = spec.split("=", 1)
    kind, ident = read_id(Path(path))
    if guest and kind == "host":
        return f"{head}=host"
    return f"{head}={ident}"


def normalized(root: str, args: list[str]) -> list[str]:
    """The compile's arguments as they are on every host and in every checkout."""
    guest = _value(args, "--target") is not None
    out: list[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        nxt = args[i + 1] if i + 1 < len(args) else None
        if a.startswith("@"):
            raise IdError(f"an argument file ({a}) hides the compile's arguments")
        if a in PAIRED_DROPPED:
            i += 2
            continue
        if a == "-C" and nxt is not None and nxt.startswith(CODEGEN_DROPPED):
            i += 2
            continue
        if a.startswith("-C") and a[2:].startswith(CODEGEN_DROPPED):
            i += 1
            continue
        if a.startswith(("--out-dir=", "-L")) or a.startswith(QUIET_PREFIXES):
            i += 1
            continue
        if a == "--extern" and nxt is not None:
            out += [a, _extern(nxt, guest)]
            i += 2
            continue
        out.append(a.replace(root, ROOT_WORD))
        i += 1
    return out


def crate_id(root: str, args: list[str]) -> str:
    return hashlib.sha256("\0".join(normalized(root, args)).encode()).hexdigest()[:16]


def rewritten(root: str, args: list[str]) -> tuple[list[str], Path | None, str]:
    """The arguments with cargo's `-C metadata` replaced, the `.rustc-id` file to write (None
    when nothing is written), and its text."""
    crate = _value(args, "--crate-name")
    if crate is None or _codegen(args, "metadata") is None:
        return args, None, ""
    ident = crate_id(root, args)
    out: list[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "-C" and i + 1 < len(args) and args[i + 1].startswith("metadata="):
            out += ["-C", f"metadata={ident}"]
            i += 2
            continue
        if a.startswith("-Cmetadata="):
            out.append(f"-Cmetadata={ident}")
            i += 1
            continue
        out.append(a)
        i += 1
    out_dir = _value(args, "--out-dir")
    if out_dir is None:
        raise IdError(f"cargo's compile of {crate} names no --out-dir")
    extra = _codegen(args, "extra-filename") or ""
    kind = "guest" if _value(args, "--target") is not None else "host"
    return out, Path(out_dir) / f"lib{crate}{extra}{ID_SUFFIX}", f"{kind} {ident}\n"


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
        return 2
    root, rustc, *args = argv
    try:
        args, record, text = rewritten(root, args)
    except IdError as e:
        print(f"rust_ids: {e}", file=sys.stderr)
        return 1
    if record is not None:
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text(text)
    os.execv(rustc, [rustc, *args])
    return 1  # not reached


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
