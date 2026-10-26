"""The key of a finished artifact set, and the check that a set is this commit's.

    uv run --no-project python -I release/set_key.py key     # key=wasi-python-set-v1-<sha256>
    uv run --no-project python -I release/set_key.py verify <set> [--key <key>]

The key is the SHA-256 of one canonical text: a format line, the build's environment as the
workflow sets it (`ENV`), and `file <sha256> <path>` for every file of `closure()`: the pins, every
tracked file under `scripts/` and `recipes/`, this file, the build constraints an env value names,
and the gate step 60 runs with `tests/` on PYTHONPATH (`GATES`) with every local module it
imports. A cached set is judged on pull requests into dev and on dev without a rebuild. It is
rebuilt from the pins and compared byte for byte at the weekly run, at the release pull request
into main and at the tag, each of which builds its own set or rebuilds the cached one on two more
hosts and requires the same bytes. So a key that missed an input, or a planted cache entry, is
caught before any release and never published.

`verify` checks a set folder: every file against the set's own SHA256SUMS, no other file, and
MANIFEST's `pin` and `recipe` lines equal to what this checkout gives, by the selection
`scripts/assemble_artifacts.py` makes (its RESEARCH_PINS and sha256, imported; the `bench_` rule
of its `main`). With `--key`, the key this checkout gives must be that one. Standard library only.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FORMAT = "format 1"
PREFIX = "wasi-python-set-v1-"
# Every variable the build steps see from release.yml's top-level env (the rules check holds the
# list equal to it): step 10's `uv pip install` runs the uv UV_VERSION names.
ENV = ("SOURCE_DATE_EPOCH", "UV_BUILD_CONSTRAINT", "UV_LOCKED", "UV_PYTHON", "UV_VERSION")
TREES = ("scripts", "recipes")
FILES = ("downloads/SHA256SUMS", "release/set_key.py", "release/build-constraints.txt")
# The modules the build runs with PYTHONPATH="$HERE/<GATE_ROOT>" (scripts/steps/constructors.sh).
GATE_ROOT = "tests"
GATES = ("harness.constructors",)
SUMS = "SHA256SUMS"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tracked(repo: Path, *paths: str) -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "-z", "--", *paths],
        capture_output=True,
        check=True,
    ).stdout
    return sorted(p for p in out.decode().split("\0") if p)


def module_path(repo: Path, module: str) -> str | None:
    """The file a module name resolves to under GATE_ROOT (a package's `__init__.py`), if any."""
    base = repo / GATE_ROOT / Path(*module.split("."))
    for p in (base.with_suffix(".py"), base / "__init__.py"):
        if p.is_file():
            return p.relative_to(repo).as_posix()
    return None


def _imports(repo: Path, rel: str, module: str) -> set[str]:
    """The module names a file imports, absolute, relative ones resolved."""
    tree = ast.parse((repo / rel).read_text(encoding="utf-8"), rel)
    package = module if rel.endswith("__init__.py") else module.rpartition(".")[0]
    out: set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            if n.level:
                parts = package.split(".")
                base = ".".join(parts[: len(parts) - n.level + 1])
                stem = f"{base}.{n.module}" if n.module else base
            else:
                stem = n.module or ""
            out.add(stem)
            out |= {f"{stem}.{a.name}" for a in n.names}
    return out


def gate_files(repo: Path, gates: tuple[str, ...] = GATES) -> list[str]:
    """Every file under GATE_ROOT the gates import, directly or not, with each package's
    `__init__.py` on the way."""
    seen: set[str] = set()
    todo = list(gates)
    done: set[str] = set()
    while todo:
        module = todo.pop()
        if module in done:
            continue
        done.add(module)
        parts = module.split(".")
        for k in range(1, len(parts) + 1):  # the packages on the way, then the module
            rel = module_path(repo, ".".join(parts[:k]))
            if rel and rel not in seen:
                seen.add(rel)
                todo.extend(_imports(repo, rel, ".".join(parts[:k])))
    return sorted(seen)


def closure(repo: Path = REPO) -> list[str]:
    return sorted(set(tracked(repo, *TREES)) | set(FILES) | set(gate_files(repo)))


def canonical(repo: Path = REPO, environ=None) -> str:
    environ = os.environ if environ is None else environ
    missing = [n for n in ENV if n not in environ]
    if missing:
        raise SystemExit(f"set_key: the build's environment lacks {' '.join(missing)}")
    lines = [FORMAT]
    lines += [f"env {n}={environ[n]}" for n in ENV]
    for rel in closure(repo):
        p = repo / rel
        if not p.is_file():
            raise SystemExit(f"set_key: {rel} is in the closure and is not a file")
        lines.append(f"file {sha256(p)} {rel}")
    return "\n".join(lines) + "\n"


def key(repo: Path = REPO, environ=None) -> str:
    return PREFIX + hashlib.sha256(canonical(repo, environ).encode()).hexdigest()


def _assemble(repo: Path):
    """scripts/assemble_artifacts.py, imported, so verify makes MANIFEST's lines its way."""
    sys.path.insert(0, str(repo / "scripts"))
    try:
        spec = importlib.util.spec_from_file_location(
            "wasi_python_assemble", repo / "scripts" / "assemble_artifacts.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path.remove(str(repo / "scripts"))


def manifest_lines(repo: Path = REPO) -> tuple[list[str], list[str]]:
    """The `pin` and `recipe` lines this checkout gives, as assemble_artifacts.main makes them."""
    a = _assemble(repo)
    pins = [
        line.split()
        for line in (repo / "downloads" / "SHA256SUMS").read_text().splitlines()
        if line.strip() and line.split()[1] not in a.RESEARCH_PINS
    ]
    recipes = sorted(
        f for f in tracked(repo, "recipes", "scripts") if not Path(f).name.startswith("bench_")
    )
    return (
        [f"pin {sha} {name}" for sha, name in pins],
        [f"recipe {a.sha256(repo / f)} {f}" for f in recipes],
    )


def verify(folder: Path, repo: Path = REPO, want_key: str | None = None, environ=None) -> list[str]:
    """Why `folder` is not a whole set of this checkout's inputs: one line per reason."""
    errors: list[str] = []
    sums = folder / SUMS
    if not sums.is_file():
        return [f"{folder}: no {SUMS}"]
    listed: dict[str, str] = {}
    for n, line in enumerate(sums.read_text().splitlines(), 1):
        sha, sep, rel = line.partition("  ")
        if not sep or len(sha) != 64 or not rel:
            errors.append(f"{SUMS}:{n}: not '<sha256>  <path>'")
            continue
        listed[rel] = sha
    present = sorted(
        p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file() or p.is_symlink()
    )
    for rel in present:
        p = folder / rel
        if rel == SUMS:
            continue
        if rel not in listed:
            errors.append(f"{rel}: a file {SUMS} does not list")
        elif p.is_symlink() or sha256(p) != listed[rel]:
            errors.append(f"{rel}: not the bytes {SUMS} lists")
    errors += [f"{rel}: listed in {SUMS}, absent" for rel in sorted(set(listed) - set(present))]
    manifest = folder / "MANIFEST"
    if not manifest.is_file():
        errors.append("MANIFEST: absent")
    else:
        have = manifest.read_text().splitlines()
        pins, recipes = manifest_lines(repo)
        if [x for x in have if x.startswith("pin ")] != pins:
            errors.append("MANIFEST: its pin lines are not this checkout's downloads/SHA256SUMS")
        got = [x for x in have if x.startswith("recipe ")]
        if got != recipes:
            off = sorted(set(got) ^ set(recipes))
            errors.append(
                f"MANIFEST: its recipe lines are not this checkout's ({len(off)} differ, first: "
                f"{off[0] if off else 'the order'})"
            )
    if want_key is not None:
        mine = key(repo, environ)
        if mine != want_key:
            errors.append(f"key: this checkout gives {mine}, not {want_key}")
    return errors


def main(argv: list[str]) -> int:
    if argv[:1] == ["key"] and len(argv) == 1:
        text = canonical()
        sys.stderr.write(text)
        print(f"key={PREFIX}{hashlib.sha256(text.encode()).hexdigest()}")
        return 0
    if argv[:1] == ["verify"] and len(argv) in (2, 4) and (len(argv) == 2 or argv[2] == "--key"):
        errors = verify(Path(argv[1]), want_key=argv[3] if len(argv) == 4 else None)
        for line in errors:
            print(f"ERROR set: {line}")
        if not errors:
            print(f"set: {argv[1]} is whole and this commit's")
        return 1 if errors else 0
    print(__doc__.split("\n\n")[1], file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
