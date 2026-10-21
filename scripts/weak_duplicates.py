"""Two checks on python.wasm's static link that wasm-ld's own warnings cannot make.
Step 60 runs the first before the link and the second after it.

    weak_duplicates.py archives <llvm-nm> <llvm-cxxfilt> <allowed list> <archive>...
    weak_duplicates.py link-map <python.map> --require <name>... --forbid <name>...

**archives.** wasm-ld stops on two strong definitions of one name (step 60's `clashes()` reads
its `duplicate symbol` lines), but where one definition is weak it keeps one and says nothing.
That is right for the C++ inline functions and templates a header defines in every file that uses
it, and wrong when two copies differ: scikit-learn's `bounded_rand_int` is `inline` inside
`extern "C"`, so each module that includes svm/src/newrand/newrand.h defines it weakly, and each
copy calls its own file's `mt_rand`; a missed rename would make one module draw from another's
generator, silently. So this lists, with the SDK's llvm-nm, every global weak definition in the
link's archives whose name another archive also defines, weak or strong, and stops on each one no
review has allowed. Allowed by rule, not listed: the C++ standard library (a mangled name whose
outermost scope is `std::`: its vtables, type information, guard variables and the lambdas inside
its functions included), the C++ runtime's
`__cxa_*` and `__cxxabiv1::`, and clang's `__clang_call_terminate`. Allowed by review: the list
recipes/weak-duplicates-allowed.txt, one fnmatch pattern per line, matched against the name and
its demangled form, or, written `scope:<pattern>`, against a C++ name's outermost scope (its
namespace or class); each with `# <reason>` on its line, or the build stops. A pattern that
matches nothing is named too, so the list never outlives what it allows. One line per finding;
exit 1 on any.

**link-map.** After the link, wasm-ld's map (`-Wl,--Map`, build/link/python.map) must name each
`--require` name and none of the `--forbid` names, each as a whole symbol name (a name inside a
longer identifier does not count): scikit-learn's renamed generators are in the binary, and the
original names are not. One line per finding; exit 1 on any.
"""

from __future__ import annotations

import fnmatch
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

# `llvm-nm -A -P -g --defined-only` prints `archive[member]: name type value size`, or `file: name
# type ...` for an object outside an archive.
NM_LINE = re.compile(
    r"^(?P<file>.+?)(?:\[(?P<member>[^\]]+)\])?: (?P<name>\S+) (?P<type>\S)(?: |$)"
)
WEAK_TYPES = frozenset("WV")
# The outermost scope of a mangled name: `_Z`, an optional special name (vtable TV, VTT TT, type
# information TI, its name TS, a guard variable GV), then any of a local entity's Z, a nested
# name's N, cv- and ref-qualifiers (r V K R O), a pointer P, a function type F or void v, and then
# St (::std) or the first source name, <length><identifier>.
SCOPE = re.compile(r"^_Z(?:TV|TT|TI|TS|GV)?[ZPFNKVrROv]*(?:(St)|(\d+))")
RUNTIME_NAMES = ("__clang_call_terminate",)
RUNTIME_PREFIXES = ("__cxa_", "_ZN10__cxxabiv1", "_ZTIN10__cxxabiv1", "_ZTVN10__cxxabiv1")


def parse_nm(text: str) -> list[tuple[str, str, str]]:
    """(archive, name, type) for each line llvm-nm printed; a line it cannot read stops it."""
    out = []
    for line in text.splitlines():
        if not line.strip():
            continue
        m = NM_LINE.match(line)
        if m is None:
            raise SystemExit(f"weak_duplicates: cannot read llvm-nm's line {line!r}")
        out.append((m["file"], m["name"], m["type"]))
    return out


def scope(name: str) -> str | None:
    """The outermost scope of a mangled C++ name (`std`, `pybind11`, `HighsLp`), or None for a
    C name or one this cannot read."""
    m = SCOPE.match(name)
    if m is None:
        return None
    if m[1]:
        return "std"
    n = int(m[2])
    ident = name[m.end() : m.end() + n]
    return ident if len(ident) == n else None


def allowed_by_rule(name: str) -> bool:
    return (
        scope(name) == "std"
        or name in RUNTIME_NAMES
        or any(name.startswith(p) for p in RUNTIME_PREFIXES)
    )


def allows(pattern: str, name: str, demangled: str) -> bool:
    """`scope:<pattern>` matches a mangled name's outermost scope; any other pattern matches the
    name or its demangled form; fnmatch either way."""
    if pattern.startswith("scope:"):
        s = scope(name)
        return s is not None and fnmatch.fnmatchcase(s, pattern[len("scope:") :])
    return fnmatch.fnmatchcase(name, pattern) or fnmatch.fnmatchcase(demangled, pattern)


def read_allowed(path: Path) -> list[str]:
    """The reviewed patterns: one per line, each followed on its line by `# <its reason>`; a line
    that starts with `#` is a comment, and blank lines are ignored. A pattern with no reason stops
    the build."""
    out = []
    for n, line in enumerate(path.read_text().splitlines(), 1):
        pattern, _, reason = line.partition("#")
        pattern = pattern.strip()
        if not pattern:
            continue
        if not reason.strip():
            raise SystemExit(f"{path.name}:{n}: {pattern!r} has no `# reason` on its line")
        out.append(pattern)
    return out


def findings(
    defs: list[tuple[str, str, str]], demangled: dict[str, str], allowed: list[str]
) -> tuple[list[str], list[str]]:
    """(one line per weak definition shared across archives that nothing allows, the allowed
    patterns that matched no such name)."""
    by_name: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for archive, name, kind in defs:
        by_name[name][archive].add("weak" if kind in WEAK_TYPES else "strong")
    used: set[str] = set()
    bad = []
    for name in sorted(by_name):
        archives = by_name[name]
        if len(archives) < 2 or not any("weak" in kinds for kinds in archives.values()):
            continue
        if allowed_by_rule(name):
            continue
        hits = [p for p in allowed if allows(p, name, demangled.get(name, name))]
        if hits:
            used.update(hits)
            continue
        where = ", ".join(
            f"{Path(a).name} ({'/'.join(sorted(k))})" for a, k in sorted(archives.items())
        )
        shown = demangled.get(name, name)
        label = name if shown == name else f"{name} ({shown})"
        bad.append(f"weak definition shared by {len(archives)} archives: {label}: {where}")
    stale = [p for p in allowed if p not in used]
    return bad, stale


def demangle(cxxfilt: str, names: list[str]) -> dict[str, str]:
    if not names:
        return {}
    r = subprocess.run(
        [cxxfilt], input="\n".join(names) + "\n", capture_output=True, text=True, check=True
    )
    return dict(zip(names, r.stdout.splitlines(), strict=True))


def archives_main(argv: list[str]) -> int:
    nm, cxxfilt, allowed_file, *archives = argv
    if not archives:
        raise SystemExit("weak_duplicates: no archive given")
    defs = []
    for archive in archives:
        r = subprocess.run(
            [nm, "-A", "-P", "-g", "--defined-only", archive],
            capture_output=True,
            text=True,
            check=True,
        )
        # Each archive is named as the caller gave it, so two members of one archive never count
        # as two archives.
        defs += [(archive, n, t) for _, n, t in parse_nm(r.stdout)]
    weak = sorted({n for _, n, t in defs if t in WEAK_TYPES})
    bad, stale = findings(defs, demangle(cxxfilt, weak), read_allowed(Path(allowed_file)))
    for line in bad:
        print(f"ERROR: {line}")
    for pattern in stale:
        print(f"ERROR: {allowed_file}: {pattern!r} allows no weak definition of this link")
    n_shared = len(bad)
    print(
        f"weak duplicates: {len(archives)} archives, {len(weak)} weak names, "
        f"{n_shared} unreviewed, {len(stale)} stale patterns"
    )
    return 1 if bad or stale else 0


def map_findings(text: str, require: list[str], forbid: list[str]) -> list[str]:
    def present(name: str) -> bool:
        return re.search(rf"(?<![A-Za-z0-9_$]){re.escape(name)}(?![A-Za-z0-9_$])", text) is not None

    out = [f"the link map does not name {n}" for n in require if not present(n)]
    out += [f"the link map names {n}" for n in forbid if present(n)]
    return out


def link_map_main(argv: list[str]) -> int:
    if not argv or "--require" not in argv or "--forbid" not in argv:
        raise SystemExit(
            "usage: weak_duplicates.py link-map MAP --require NAME... --forbid NAME..."
        )
    path, rest = Path(argv[0]), argv[1:]
    i, j = rest.index("--require"), rest.index("--forbid")
    require = rest[i + 1 : j] if i < j else rest[i + 1 :]
    forbid = rest[j + 1 :] if j > i else rest[j + 1 : i]
    bad = map_findings(path.read_text(errors="replace"), require, forbid)
    for line in bad:
        print(f"ERROR: {line}")
    print(f"link map: {len(require)} names required, {len(forbid)} forbidden, {len(bad)} findings")
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    if argv[:1] == ["archives"] and len(argv) >= 5:
        return archives_main(argv[1:])
    if argv[:1] == ["link-map"]:
        return link_map_main(argv[1:])
    print(__doc__.split("\n\n")[1], file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
