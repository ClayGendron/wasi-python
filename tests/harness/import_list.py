"""What the guest asks of its host: a binary's imports, compared with the reviewed list.

`recipes/guest-imports.txt` lists every import of `python.wasm` and of the snapshot, one
`module field` per line. A binary passes only when its imports, module and field, are exactly that
list: one more fails (a new call into the host no review has read), and so does one fewer (the
list would otherwise outlive the binary it describes). wasm-ld merges imports with the same module,
field and type, so a second object importing `random_get` adds no line here; the build's own gate
on each Rust object's import entries sees that case.

Steps 60 and 80 run this module on the binary each makes:

    python -m harness.import_list build/out/python.wasm      (with tests/ on PYTHONPATH)
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from harness import wasm

LIST = Path(__file__).resolve().parents[2] / "recipes" / "guest-imports.txt"


def listed(path: Path = LIST) -> Counter[tuple[str, str]]:
    """The reviewed imports: each `module field` line, comments and blank lines skipped."""
    out: Counter[tuple[str, str]] = Counter()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 2:
            raise ValueError(f"{path.name}:{number}: not `module field`: {line!r}")
        out[(parts[0], parts[1])] += 1
    return out


def errors(mod: wasm.Module, want: Counter[tuple[str, str]]) -> list[str]:
    """One line per import the binary has and the list lacks, and per listed one it lacks."""
    have = Counter((i.module, i.name) for i in mod.imports)
    out = [f"a new import: {m} {n}" for (m, n) in sorted((have - want).elements())]
    out += [
        f"a listed import the binary lacks: {m} {n}" for (m, n) in sorted((want - have).elements())
    ]
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: python -m harness.import_list <binary.wasm>", file=sys.stderr)
        return 2
    binary = Path(argv[0])
    mod = wasm.parse_file(binary)
    found = errors(mod, listed())
    for line in found:
        print(f"ERROR: {binary.name}: {line}")
    if found:
        return 1
    print(f"imports: {binary.name} has the {len(mod.imports)} reviewed imports of {LIST.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
