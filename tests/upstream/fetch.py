"""Fetch the upstream test kit into build/upstream/wheels/, and, for a
release shard, the upstream packages' source trees.

Run by hand, `uv run python tests/upstream/fetch.py`; the judge never fetches. Each wheel is
downloaded to a temporary name and renamed only after its SHA-256 equals its `kit.txt` line. A
mismatch deletes the download and exits non-zero. Nothing is unpacked or run here.

`uv run python tests/upstream/fetch.py --shard NAME` does nothing for a shard without upstream
groups. For one with groups it fetches the kit, then every upstream package's source tarball to
`downloads/<name>`: the URL from its `get` line in `scripts/00_download.sh`, the hash from
`downloads/SHA256SUMS`, renamed only after the match. It unpacks each into `build/` with tarfile's
`data` filter and applies the tree's carried patches with `scripts/steps/apply_patches.sh`, the
applier the build runs. Every tree of each family whose group the shard runs, not only the
group's own: the guest's fuel depends on the whole stage. numpy and pandas
share the `/upstream` stage, so a shard with either fetches both and the kit; CPython's tests have
their own stage, so a shard with a CPython group fetches the CPython tarball.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
KIT = HERE / "kit.txt"
WHEELS = REPO / "build" / "upstream" / "wheels"
DOWNLOADS = REPO / "downloads"
BUILD = REPO / "build"
DOWNLOAD_SCRIPT = REPO / "scripts" / "00_download.sh"
APPLIER = REPO / "scripts" / "steps" / "apply_patches.sh"
PATCHES = REPO / "recipes" / "patches"
GET_LINE = re.compile(r"^\s*get (https://\S+) (\S+)\s*$", re.M)


def kit_lines(text: str) -> list[tuple[str, str]]:
    """(sha256, url) per non-empty line."""
    out = []
    for line in text.splitlines():
        if line.strip():
            sha, url = line.split("  ", 1)
            out.append((sha, url.strip()))
    return out


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(sha: str, url: str, wheels: Path) -> str | None:
    """Download one wheel; None when it is in place with its hash, else why it is not."""
    dest = wheels / url.rsplit("/", 1)[1]
    if dest.is_file() and sha256_file(dest) == sha:
        return None
    part = dest.with_name(dest.name + ".part")
    with urllib.request.urlopen(url, timeout=120) as r, part.open("wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    got = sha256_file(part)
    if got != sha:
        part.unlink()
        return f"{dest.name}: SHA-256 {got}, kit.txt says {sha}"
    part.replace(dest)
    return None


def fetch_kit() -> list[str]:
    WHEELS.mkdir(parents=True, exist_ok=True)
    return [e for sha, url in kit_lines(KIT.read_text()) if (e := fetch(sha, url, WHEELS))]


def get_urls(script_text: str) -> dict[str, str]:
    """{file name: URL} from the download script's `get <url> <name>` lines."""
    return {m[2]: m[1] for m in GET_LINE.finditer(script_text)}


def pins(text: str) -> dict[str, str]:
    """{file name: sha256} from downloads/SHA256SUMS."""
    out = {}
    for line in text.splitlines():
        if line.strip():
            sha, name = line.split(None, 1)
            out[name.strip().lstrip("*")] = sha
    return out


def tarball_names(packages: list[str], pinned: dict[str, str]) -> tuple[list[str], list[str]]:
    """Each upstream package's pinned tarball name, and an error per package with none."""
    from harness import pins as harness_pins

    names, errors = [], []
    for package in packages:
        found = sorted(n for n in pinned if harness_pins.SOURCE_PATTERNS[package].fullmatch(n))
        if len(found) == 1:
            names.append(found[0])
        else:
            errors.append(
                f"{package}: {len(found)} pinned tarballs in downloads/SHA256SUMS, not one"
            )
    return names, errors


def unpack(tarball: Path, build: Path) -> Path:
    """Unpack into `build/` with tarfile's `data` filter; refuse a tree already there."""
    with tarfile.open(tarball) as t:
        members = t.getmembers()
        for m in members:  # within its own tree, not only within build/ (the data filter's bound)
            parts = m.name.replace("\\", "/").split("/")
            if m.name.startswith(("/", "\\")) or ".." in parts:
                raise ValueError(f"member {m.name!r} refused (outside its tree)")
        tops = {m.name.split("/", 1)[0] for m in members}
        if len(tops) != 1:
            raise ValueError(f"{tarball.name}: not one top folder: {sorted(tops)[:3]}")
        tree = build / tops.pop()
        if tree.exists():
            raise FileExistsError(f"{tree} is already there; a shard starts from no tree")
        build.mkdir(parents=True, exist_ok=True)
        t.extractall(build, members=members, filter="data")
    return tree


def fetch_trees(
    packages: list[str],
    *,
    downloads: Path = DOWNLOADS,
    build: Path = BUILD,
    script: Path = DOWNLOAD_SCRIPT,
    applier: Path = APPLIER,
    patches: Path = PATCHES,
    run=subprocess.run,
) -> list[str]:
    """Fetch, verify, unpack and patch every upstream package's tree; the errors, or none."""
    pinned = pins((downloads / "SHA256SUMS").read_text())
    urls = get_urls(script.read_text())
    names, errors = tarball_names(packages, pinned)
    errors += [f"{n}: no get line in {script.name}" for n in names if n not in urls]
    if errors:
        return errors
    for name in names:
        e = fetch(pinned[name], urls[name], downloads)
        if e:
            return [e]
    for name in names:
        try:
            tree = unpack(downloads / name, build)
        except (OSError, ValueError, tarfile.TarError) as e:
            return [f"{name}: {e}"]
        r = run(["sh", str(applier), str(tree), str(patches / tree.name)], check=False)
        if r.returncode != 0:
            return [f"{tree.name}: the carried patches did not apply (exit {r.returncode})"]
        print(f"the tree {tree.name} is in {build}")
    return []


def shard_packages(name: str) -> list[str] | None:
    """The source components a shard needs, [] when it runs no upstream group, None when the plan
    holds no such shard: every package of each grant family whose group the shard runs (numpy and
    pandas together; CPython alone), named as `harness.pins.SOURCE_PATTERNS` names them."""
    sys.path.insert(0, str(HERE.parent))  # the harness package, when run as a script
    from harness import shards, upstream

    plan = shards.load()
    if name not in plan:
        return None
    configs = upstream.load_all()
    wanted = set(plan[name].groups)
    families = {c.grant for c in configs.values() if wanted & set(c.groups)}
    return [c.component or p for p, c in configs.items() if c.grant in families]


def needs_kit(packages: list[str]) -> bool:
    """The pytest kit serves numpy's and pandas' groups only; CPython's regrtest is in Lib/test."""
    return any(p != "cpython" for p in packages)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    packages: list[str] = []
    if argv:
        if len(argv) != 2 or argv[0] != "--shard":
            print("usage: fetch.py [--shard NAME]", file=sys.stderr)
            return 2
        got = shard_packages(argv[1])
        if got is None:
            print(f"the plan holds no shard {argv[1]}", file=sys.stderr)
            return 2
        if not got:
            print(f"nothing to fetch: shard {argv[1]} runs no upstream group")
            return 0
        packages = got
    errors: list[str] = []
    if not packages or needs_kit(packages):
        errors = fetch_kit()
        if not errors:
            print(f"the kit is in {WHEELS}")
    if not errors and packages:
        errors = fetch_trees(packages)
    for e in errors:
        print(e, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
