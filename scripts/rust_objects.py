"""The gates on the one Rust static library step 52 builds, and on the link step 60 makes with it.

    rust_objects.py keep <llvm-ar> <staticlib> <out.a> <target dir> <umbrella> <module crate>...
    rust_objects.py inits <llvm-nm> <archive> <modules.txt>
    rust_objects.py foreign <llvm-nm> <archive> <runtime archive>...
    rust_objects.py imports <llvm-nm> <llvm-cxxfilt> <archive> <shim.c> <link input archive>...
    rust_objects.py link-map <python.map>

**keep.** The static library cargo writes holds more than the modules: Rust's `compiler_builtins`
(its own math, 128-bit helpers and, built from the shipped standard library, compiler-rt's C),
which LTO never merges. Linked as it is, its weak `round`, `sqrt`, `fma` and their kin would
replace wasi-libc's for the whole interpreter without a word. So the new archive holds only the
umbrella crate's object, the one LTO writes for all the Rust code, and each object found under a
module crate's own build-script folder (`build/<crate>-<hash>/out/` or `build/<crate>/<hash>/out/`:
the C a module compiles, orjson's yyjson). A member is matched to such an object by its bytes. Any
other member that is not `compiler_builtins`' stops the step, so nothing is dropped unnamed. The
umbrella's object is kept as `<umbrella>.o`: cargo's name for it carries cargo's hash of the
build, which mixes in the build host, and the archive must be the same bytes on every host. The
archive is written by `llvm-ar rcsD`, with no timestamps.

**inits.** The archive defines exactly the `PyInit_*` names `recipes/rust/modules.txt` lists.

**foreign.** The archive defines no global name that the SDK's runtime libraries also define,
weak or strong: a Rust object brings in nothing that should come from wasi-libc or compiler-rt.

**imports.** Each object's import entries are read as they are: any import outside `env` but
`wasi_snapshot_preview1.random_get` stops the step. Then the undefined names that no input of the
link defines (CPython's archive, the SDK's runtime libraries, the archive itself, and the few names
wasm-ld defines) are what would become imports of their own. Each one whose demangled form ends in
`::random_get` gets a definition in the shim, by its mangled name, calling `__wasi_random_get`,
which the reactor's link wraps: Rust's entropy is then pinned while a starting image is prepared,
as C's is. Their count must be the count of `random_get` import entries. Any other name left stops
the step, so a new direct clock or poll import is reviewed before it ships. This gate alone sees a
direct import that bypasses a wrap: wasm-ld merges imports of the same module, field and type, so
such an import adds no line to the binary's import list.

**link-map.** After the link, wasm-ld's map shows where each runtime name came from: the math
functions from wasi-libc's `libc.a`, the 128-bit and complex helpers from compiler-rt's
`libclang_rt.builtins.a`. A few must be named, so the check cannot pass on an empty map.

One line per finding; exit 1 on any.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
import tempfile
from pathlib import Path

TESTS = Path(__file__).resolve().parents[1] / "tests"
sys.path.insert(0, str(TESTS))
from harness import wasm  # noqa: E402

COMPILER_BUILTINS = "compiler_builtins"
# The names wasm-ld defines itself; an object's reference to one is never an import.
LINKER_NAMES = frozenset(
    ("__stack_pointer", "__indirect_function_table", "__memory_base", "__table_base", "__c_longjmp")
)
ENTROPY = ("wasi_snapshot_preview1", "random_get")
_MATH = "cbrt ceil copysign fabs floor fma fmax fmin fmod rint round sqrt trunc".split()
LIBC_NAMES = (*_MATH, *(f"{n}f" for n in _MATH))
BUILTINS_NAMES = tuple(
    "__addtf3 __multf3 __divtf3 __multi3 __udivti3 __modti3 __ashlti3 __lshrti3 __powidf2 "
    "__muldc3 __divdc3 __mulsc3 __divsc3".split()
)
MUST_BE_NAMED = ("round", "sqrt", "fma", "__multf3", "__multi3")


def ar_members(data: bytes) -> list[tuple[str, bytes]]:
    """(name, bytes) of each member of a System V or BSD `ar` archive, its index left out."""
    if not data.startswith(b"!<arch>\n"):
        raise ValueError("not an ar archive")
    pos, longnames, out = 8, b"", []
    while pos + 60 <= len(data):
        header = data[pos : pos + 60]
        name = header[:16].decode("ascii", "replace").rstrip()
        size = int(header[48:58].decode("ascii").strip())
        body = data[pos + 60 : pos + 60 + size]
        pos += 60 + size + (size & 1)
        if name in ("/", "/SYM64/", "__.SYMDEF", "__.SYMDEF SORTED"):
            continue
        if name == "//":
            longnames = body
            continue
        if name.startswith("#1/"):  # BSD: the name leads the body
            n = int(name[3:])
            name, body = body[:n].rstrip(b"\0").decode(), body[n:]
        elif name.startswith("/") and name[1:].isdigit():  # GNU: an offset into //
            start = int(name[1:])
            name = longnames[start : longnames.index(b"/\n", start)].decode()
        else:
            name = name.rstrip("/")
        out.append((name, body))
    return out


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _crate_of(build_dir: Path, path: Path) -> str:
    """The crate a file under cargo's `build/` folder belongs to: `<crate>-<hash>/out/...` or
    `<crate>/<hash>/out/...`."""
    first = path.relative_to(build_dir).parts[0]
    head, _, tail = first.rpartition("-")
    return head if head and re.fullmatch(r"[0-9a-f]{16}", tail) else first


def build_objects(target: Path, crates: set[str]) -> dict[str, str]:
    """SHA-256 -> crate, for each object under a build-script `out/` folder of the named crates:
    loose objects and the members of the archives beside them."""
    found: dict[str, str] = {}
    for build_dir in sorted(target.glob("*/release/build")) + sorted(target.glob("release/build")):
        for path in sorted(build_dir.rglob("*")):
            if "out" not in path.relative_to(build_dir).parts or not path.is_file():
                continue
            crate = _crate_of(build_dir, path)
            if crate not in crates:
                continue
            if path.suffix == ".o":
                found[_sha(path.read_bytes())] = crate
            elif path.suffix == ".a":
                for _, body in ar_members(path.read_bytes()):
                    found[_sha(body)] = crate
    return found


def keep(members: list[tuple[str, bytes]], umbrella: str, ours: dict[str, str], builtins: set[str]):
    """(kept members, dropped names, errors): the umbrella's object and the module crates' own C."""
    kept, dropped, errors = [], [], []
    umbrellas = [n for n, _ in members if n.startswith(f"{umbrella}-") and n.endswith(".o")]
    if len(umbrellas) > 1:
        errors.append(
            f"{len(umbrellas)} objects of the umbrella crate {umbrella}, where fat LTO writes one"
        )
    for name, body in members:
        if name.startswith(f"{umbrella}-") and name.endswith(".o"):
            kept.append((f"{umbrella}.o", body))
        elif _sha(body) in ours:
            kept.append((name, body))
        elif name.startswith(f"{COMPILER_BUILTINS}-") or _sha(body) in builtins:
            dropped.append(name)
        else:
            errors.append(f"a member that is neither a module's nor {COMPILER_BUILTINS}': {name}")
    if not umbrellas:
        errors.append(f"no object of the umbrella crate {umbrella}")
    return kept, dropped, errors


def keep_main(argv: list[str]) -> int:
    ar, staticlib, out, target, umbrella, *crates = argv
    members = ar_members(Path(staticlib).read_bytes())
    ours = build_objects(Path(target), set(crates))
    builtins = set(build_objects(Path(target), {COMPILER_BUILTINS}))
    kept, dropped, errors = keep(members, umbrella, ours, builtins)
    for e in errors:
        print(f"ERROR: {e}")
    if errors:
        return 1
    with tempfile.TemporaryDirectory() as tmp:
        files = []
        for n, (name, body) in enumerate(kept):
            f = Path(tmp) / f"{n:02d}" / name  # a folder each, so a member keeps its own name
            f.parent.mkdir()
            f.write_bytes(body)
            files.append(str(f))
        Path(out).unlink(missing_ok=True)
        subprocess.run([ar, "rcsD", out, *files], check=True)
    print(f"keep: {len(kept)} kept, {len(dropped)} dropped ({COMPILER_BUILTINS}')")
    return 0


def nm_names(nm: str, paths: list[str], *flags: str) -> set[str]:
    """The names llvm-nm prints for the paths with the flags, one name per symbol line."""
    if not paths:
        return set()
    text = subprocess.run(
        [nm, "-j", *flags, *paths], check=True, capture_output=True, text=True
    ).stdout
    return {line.strip() for line in text.splitlines() if line.strip() and not line.endswith(":")}


def read_modules(path: Path) -> list[tuple[str, str]]:
    """(dotted import name, init function) per line of modules.txt; # lines are comments."""
    out = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 2 or not parts[1].startswith("PyInit_"):
            raise ValueError(f"{path.name}:{number}: not `<dotted name> PyInit_<name>`: {line!r}")
        out.append((parts[0], parts[1]))
    return out


def inits_main(argv: list[str]) -> int:
    nm, archive, modules = argv
    want = {init for _, init in read_modules(Path(modules))}
    have = {n for n in nm_names(nm, [archive], "-g", "--defined-only") if n.startswith("PyInit_")}
    errors = [f"defines {n}, which modules.txt does not list" for n in sorted(have - want)]
    errors += [f"does not define {n}, which modules.txt lists" for n in sorted(want - have)]
    for e in errors:
        print(f"ERROR: the Rust archive {e}")
    if errors:
        return 1
    print(f"inits: the Rust archive defines exactly {', '.join(sorted(want))}")
    return 0


def foreign_main(argv: list[str]) -> int:
    nm, archive, *runtime = argv
    ours = nm_names(nm, [archive], "-g", "--defined-only")
    errors = []
    for lib in runtime:
        for name in sorted(ours & nm_names(nm, [lib], "-g", "--defined-only")):
            errors.append(f"the Rust archive defines {name}, which {Path(lib).name} defines too")
    for e in errors:
        print(f"ERROR: {e}")
    if errors:
        return 1
    print(f"foreign: the Rust archive defines none of the {len(runtime)} runtime libraries' names")
    return 0


def entropy_imports(objects: list[tuple[str, bytes]]) -> tuple[int, list[str]]:
    """(the count of random_get import entries, errors) over the objects' import entries."""
    count, errors = 0, []
    for name, body in objects:
        for imp in wasm.parse(body).imports:
            if imp.module == "env":
                continue
            if (imp.module, imp.name) != ENTROPY:
                errors.append(
                    f"{name}: a direct import the shim does not route: {imp.module}.{imp.name}"
                )
            elif imp.type is None or (imp.type.params, imp.type.results) != (
                ("i32", "i32"),
                ("i32",),
            ):
                errors.append(
                    f"{name}: random_get is imported as {imp.type}, not (i32, i32) -> (i32)"
                )
            else:
                count += 1
    return count, errors


def shim_source(names: list[tuple[str, str]]) -> str:
    """The C that defines each mangled `random_get` to call `__wasi_random_get`."""
    lines = [
        "/* Written by scripts/rust_objects.py: Rust's direct entropy imports, each defined",
        "   here to call __wasi_random_get, which the reactor's link wraps. Do not edit. */",
        "#include <stdint.h>",
        "#include <wasi/api.h>",
        "",
    ]
    for n, (mangled, demangled) in enumerate(names):
        lines += [
            f"/* {demangled} */",
            f'int32_t rust_random_get_{n}(uint8_t *buf, uint32_t len) __asm__("{mangled}");',
            f"int32_t rust_random_get_{n}(uint8_t *buf, uint32_t len) {{",
            "    return __wasi_random_get(buf, len);",
            "}",
            "",
        ]
    return "\n".join(lines)


def imports_main(argv: list[str]) -> int:
    nm, cxxfilt, archive, shim, *inputs = argv
    objects = ar_members(Path(archive).read_bytes())
    count, errors = entropy_imports(objects)
    undefined = nm_names(nm, [archive], "-u")
    defined = nm_names(nm, [archive], "--defined-only")
    for lib in inputs:
        defined |= nm_names(nm, [lib], "-g", "--defined-only")
    left = sorted(undefined - defined - LINKER_NAMES)
    demangled = {}
    if left:
        out = subprocess.run(
            [cxxfilt], input="\n".join(left), check=True, capture_output=True, text=True
        )
        demangled = dict(zip(left, out.stdout.splitlines(), strict=True))
    shimmed = []
    for name in left:
        d = demangled.get(name, name)
        if d.endswith("::random_get"):
            shimmed.append((name, d))
        else:
            errors.append(f"a direct WASI import the shim does not route: {name} ({d})")
    if len(shimmed) != count:
        errors.append(
            f"{len(shimmed)} random_get names to shim, but {count} random_get import entries"
        )
    for e in errors:
        print(f"ERROR: {e}")
    if errors:
        return 1
    Path(shim).write_text(shim_source(shimmed), encoding="utf-8")
    for mangled, d in shimmed:
        print(f"shimmed: {mangled} ({d})")
    print(f"imports: {count} entropy imports shimmed, nothing else imported")
    return 0


# A map line opens with wasm-ld's three columns, the address (`-` for a function), the offset and
# the size, then one space. After them an output section stands at no indent, an input chunk at 8
# (`archive.a(member.o):(name)` or `object.o:(name)`) and each of its symbols at 16.
MAP_COLUMNS = re.compile(r"\s*(?:-|[0-9a-f]+)\s+[0-9a-f]+\s+[0-9a-f]+ ")
MAP_CHUNK = re.compile(r"(?:(\S+?\.a)\([^)]*\)|(\S+?)):\(")


def map_sources(text: str) -> dict[str, set[str]]:
    """name -> the files (an archive's name, or an object's) whose chunks wasm-ld's map shows
    defining it."""
    sources: dict[str, set[str]] = {}
    current = None
    for line in text.splitlines():
        m = MAP_COLUMNS.match(line)
        if not m:
            continue
        rest = line[m.end() :]
        indent = len(rest) - len(rest.lstrip(" "))
        if indent < 8:
            current = None
        elif indent < 16:
            chunk = MAP_CHUNK.match(rest.strip())
            current = Path(chunk[1] or chunk[2]).name if chunk else None
        elif current is not None:
            sources.setdefault(rest.strip(), set()).add(current)
    return sources


def map_findings(text: str) -> list[str]:
    sources = map_sources(text)
    out = []
    for names, lib in ((LIBC_NAMES, "libc.a"), (BUILTINS_NAMES, "libclang_rt.builtins.a")):
        for name in names:
            if name in sources and sources[name] != {lib}:
                out.append(f"{name} comes from {', '.join(sorted(sources[name]))}, not {lib}")
    out += [f"the link map does not name {n}" for n in MUST_BE_NAMED if n not in sources]
    return out


def link_map_main(argv: list[str]) -> int:
    (path,) = argv
    found = map_findings(Path(path).read_text(encoding="utf-8", errors="replace"))
    for f in found:
        print(f"ERROR: {f}")
    if found:
        return 1
    print(
        "link map: the math names come from libc.a"
        " and the 128-bit helpers from libclang_rt.builtins.a"
    )
    return 0


MODES = {
    "keep": (keep_main, 6),
    "inits": (inits_main, 3),
    "foreign": (foreign_main, 3),
    "imports": (imports_main, 4),
    "link-map": (link_map_main, 1),
}


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in MODES or len(argv) - 1 < MODES[argv[0]][1]:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    return MODES[argv[0]][0](argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
