"""The package's version, its changelog and its release tag.

    uv run python release/version.py show
    uv run python release/version.py bump [--to 0.1.0a2]
    uv run python release/version.py check [--tag v0.1.0a1]
    uv run python release/version.py release [--push]
    uv run python release/version.py notes 0.1.0a1 [--repository owner/name]
    uv run python release/version.py assets <artifact dir> <wheel> <out dir>

`__version__` in src/wasi_python/__init__.py is the only place the version is written;
pyproject.toml reads it through hatchling. A release is the annotated tag `v<version>` on a
pushed commit of main; pushing it starts .github/workflows/release.yml. Pushing a release tag is
cutting a release, which only the owner decides.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import io
import lzma
import os
import re
import subprocess
import sys
import tarfile
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INIT = REPO / "src" / "wasi_python" / "__init__.py"
PYPROJECT = REPO / "pyproject.toml"
CHANGELOG = REPO / "CHANGELOG.md"
VERSION_LINE = re.compile(r'^__version__ = "([^"]+)"$', re.M)
FORM = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:(a|b|rc)([1-9]\d*))?$")
STAGES = {"a": 0, "b": 1, "rc": 2, None: 3}
SECTION = re.compile(r"^## (\S+) — (unreleased|\d{4}-\d{2}-\d{2})$", re.M)
EPOCH = 1767225600  # SOURCE_DATE_EPOCH, as the build
# The repository a local run names; the release workflow passes the one it runs in, which is the
# one its attestations are signed in.
REPOSITORY = "ClayGendron/wasi-python"


class ReleaseError(Exception):
    """One line saying what is wrong."""


@dataclass(frozen=True, order=True)
class Version:
    major: int
    minor: int
    patch: int
    stage: int  # 0 a, 1 b, 2 rc, 3 final
    number: int

    @classmethod
    def parse(cls, text: str) -> Version:
        m = FORM.match(text)
        if m is None:
            raise ReleaseError(f"{text!r} is not a version of the form X.Y.Z, X.Y.ZaN, bN or rcN")
        major, minor, patch, stage, number = m.groups()
        return cls(int(major), int(minor), int(patch), STAGES[stage], int(number or 0))

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.stage == 3:
            return base
        return base + {0: "a", 1: "b", 2: "rc"}[self.stage] + str(self.number)

    @property
    def is_prerelease(self) -> bool:
        return self.stage != 3

    def next_alpha(self) -> Version:
        """0.0.0 -> 0.1.0a1; X.Y.ZaN -> X.Y.Za(N+1); anything else -> the next minor's a1."""
        if (self.major, self.minor, self.patch) == (0, 0, 0):
            return Version(0, 1, 0, 0, 1)
        if self.stage == 0:
            return Version(self.major, self.minor, self.patch, 0, self.number + 1)
        return Version(self.major, self.minor + 1, 0, 0, 1)


def read_version(init_text: str) -> str:
    m = VERSION_LINE.search(init_text)
    if m is None:
        raise ReleaseError(f"{INIT.relative_to(REPO)} has no __version__ line")
    return m.group(1)


def write_version(init_text: str, version: Version) -> str:
    return VERSION_LINE.sub(f'__version__ = "{version}"', init_text, count=1)


def sections(changelog: str) -> dict[str, str]:
    """version -> its date, or 'unreleased'."""
    return {m.group(1): m.group(2) for m in SECTION.finditer(changelog)}


def add_section(changelog: str, version: Version) -> str:
    """A new `unreleased` section above the newest one."""
    if str(version) in sections(changelog):
        raise ReleaseError(f"CHANGELOG.md already has a section for {version}")
    entry = f"## {version} — unreleased\n\n- (what changed)\n\n"
    first = SECTION.search(changelog)
    if first is None:
        return changelog.rstrip("\n") + "\n\n" + entry
    return changelog[: first.start()] + entry + changelog[first.start() :]


def date_section(changelog: str, version: Version, day: str) -> str:
    old = f"## {version} — unreleased"
    if old not in changelog:
        raise ReleaseError(f"CHANGELOG.md has no unreleased section for {version}")
    return changelog.replace(old, f"## {version} — {day}", 1)


def notes(changelog: str, version: str) -> str:
    matches = list(SECTION.finditer(changelog))
    for i, m in enumerate(matches):
        if m.group(1) == version:
            end = matches[i + 1].start() if i + 1 < len(matches) else len(changelog)
            return changelog[m.end() : end].strip() + "\n"
    raise ReleaseError(f"CHANGELOG.md has no section for {version}")


def check_errors(
    init_text: str, pyproject_text: str, changelog: str, tag: str | None = None
) -> list[str]:
    errors = []
    try:
        version = str(Version.parse(read_version(init_text)))
    except ReleaseError as e:
        return [str(e)]
    if not re.search(r'^dynamic = \["version"\]$', pyproject_text, re.M):
        errors.append('pyproject.toml must declare dynamic = ["version"]')
    if re.search(r"^version = ", pyproject_text, re.M):
        errors.append("pyproject.toml writes a static version; __init__.py is the only place")
    if 'path = "src/wasi_python/__init__.py"' not in pyproject_text:
        errors.append("pyproject.toml's [tool.hatch.version] does not read src/wasi_python")
    if version != "0.0.0" and version not in sections(changelog):
        errors.append(f"CHANGELOG.md has no section for {version}")
    if tag is not None:
        if tag != f"v{version}":
            errors.append(f"the tag {tag} is not v{version}, the version it points to")
        elif sections(changelog).get(version) == "unreleased":
            errors.append(f"CHANGELOG.md's section for {version} is still unreleased")
    return errors


def git(*args: str, strip: bool = True) -> str:
    out = subprocess.run(
        ["git", "-C", str(REPO), *args], capture_output=True, text=True, check=True
    ).stdout
    return out.strip() if strip else out


def set_files(artifacts: Path) -> list[Path]:
    """The set's files, as its SHA256SUMS names them, and SHA256SUMS, sorted as the folder's walk
    once sorted them; a listed file that is missing stops the release."""
    sums = artifacts / "SHA256SUMS"
    if not sums.is_file():
        raise SystemExit(f"{sums} is missing: the artifact set has no list")
    listed = [line.split(None, 1)[1].strip() for line in sums.read_text().splitlines() if line]
    outside = [rel for rel in listed if rel.startswith("/") or ".." in rel.split("/")]
    if outside:
        raise SystemExit(f"SHA256SUMS lists paths outside the set: {', '.join(outside)}")
    files = [artifacts / rel for rel in listed] + [sums]
    missing = [p.relative_to(artifacts).as_posix() for p in files if not p.is_file()]
    if missing:
        raise SystemExit(f"SHA256SUMS lists files that are missing: {', '.join(missing)}")
    return sorted(set(files))


def write_assets(artifacts: Path, wheel: Path, out: Path, version: str) -> list[Path]:
    """The wheel, the artifact set as a deterministic .tar.xz, and SHA256SUMS of both. The tarball
    packs the files the set's own SHA256SUMS lists, and SHA256SUMS: never the folder, where a
    desktop may have written litter."""
    files = set_files(artifacts)
    out.mkdir(parents=True, exist_ok=True)
    top = f"wasi-python-{version}"
    tar_path = out / f"{top}-wasm32-wasip1.tar.xz"
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as tar:
        dirs = sorted({p.parent for p in files if p.parent != artifacts})
        for d in [artifacts, *dirs]:
            name = top if d == artifacts else f"{top}/{d.relative_to(artifacts).as_posix()}"
            tar.addfile(_info(name, tarfile.DIRTYPE, 0o755, 0))
        for p in files:
            data = p.read_bytes()
            info = _info(f"{top}/{p.relative_to(artifacts).as_posix()}", tarfile.REGTYPE, 0o644)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    tar_path.write_bytes(lzma.compress(raw.getvalue(), preset=9))
    wheel_out = out / wheel.name
    wheel_out.write_bytes(wheel.read_bytes())
    sums = out / "SHA256SUMS"
    sums.write_text(
        "".join(
            f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n"
            for p in sorted((tar_path, wheel_out))
        )
    )
    return [wheel_out, tar_path, sums]


def _info(name: str, kind: bytes, mode: int, size: int = 0) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.type, info.mode, info.size = kind, mode, size
    info.mtime, info.uid, info.gid, info.uname, info.gname = EPOCH, 0, 0, "", ""
    return info


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="release/version.py")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("show")
    bump = sub.add_parser("bump")
    bump.add_argument("--to")
    check = sub.add_parser("check")
    check.add_argument("--tag")
    release = sub.add_parser("release")
    release.add_argument("--push", action="store_true")
    notes_cmd = sub.add_parser("notes")
    notes_cmd.add_argument("version")
    notes_cmd.add_argument("--repository", default=REPOSITORY)
    assets = sub.add_parser("assets")
    assets.add_argument("artifacts", type=Path)
    assets.add_argument("wheel", type=Path)
    assets.add_argument("out", type=Path)
    a = parser.parse_args(argv)
    try:
        return COMMANDS[a.command](a)
    except ReleaseError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def _show(a: argparse.Namespace) -> int:
    print(read_version(INIT.read_text()))
    return 0


def _bump(a: argparse.Namespace) -> int:
    current = Version.parse(read_version(INIT.read_text()))
    new = Version.parse(a.to) if a.to else current.next_alpha()
    if new <= current:
        raise ReleaseError(f"{new} is not greater than {current}")
    init_text = write_version(INIT.read_text(), new)
    changelog = add_section(CHANGELOG.read_text(), new)  # raises before anything is written
    INIT.write_text(init_text)
    CHANGELOG.write_text(changelog)
    print(f"{current} -> {new}: edit CHANGELOG.md's section, then commit")
    return 0


def _check(a: argparse.Namespace) -> int:
    errors = check_errors(INIT.read_text(), PYPROJECT.read_text(), CHANGELOG.read_text(), a.tag)
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)
    if not errors:
        print(f"ok {read_version(INIT.read_text())}" + (f" (tag {a.tag})" if a.tag else ""))
    return 1 if errors else 0


def _release(a: argparse.Namespace) -> int:
    version = Version.parse(read_version(INIT.read_text()))
    tag = f"v{version}"
    changed = git("status", "--porcelain", "--untracked-files=no", strip=False).rstrip("\n")
    if changed:
        names = ", ".join(line[3:] for line in changed.splitlines()[:5])
        raise ReleaseError(f"tracked files have uncommitted changes: {names}")
    if git("rev-parse", "--abbrev-ref", "HEAD") != "main":
        raise ReleaseError("releases are cut from main")
    git("fetch", "origin", "main", "--tags")
    if git("rev-parse", "HEAD") != git("rev-parse", "origin/main"):
        raise ReleaseError("main is not level with origin/main: push or pull first")
    if git("tag", "--list", tag):
        raise ReleaseError(f"the tag {tag} exists already")
    day = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d")
    before = CHANGELOG.read_text()
    CHANGELOG.write_text(date_section(before, version, day))
    errors = check_errors(INIT.read_text(), PYPROJECT.read_text(), CHANGELOG.read_text(), tag)
    if errors:
        CHANGELOG.write_text(before)  # undo this command's own edit
        raise ReleaseError("; ".join(errors))
    git("commit", "-q", "-m", f"Release {version}", "--", str(CHANGELOG))
    message = f"wasi-python {version}\n\n{notes(CHANGELOG.read_text(), str(version))}"
    git("tag", "-a", tag, "-m", message)
    push = f"git push origin main {tag}"
    if a.push:
        subprocess.run(["git", "-C", str(REPO), "push", "origin", "main", tag], check=True)
        print(f"pushed main and {tag}: the release workflow is running")
    else:
        print(f"tagged {tag}. To cut the release: {push}")
    return 0


def verify_note(version: str, repository: str = REPOSITORY) -> str:
    """How a user checks this release's assets: appended to the release's notes, not to the tag's
    message. The command is the one the release's attest job runs before it publishes."""
    return (
        "\n**Verify a download** (`gh` logged in; see the README's *Verifying a download*):\n\n"
        "```\n"
        f"gh attestation verify <asset> --repo {repository} \\\n"
        "  --signer-workflow "
        f"{repository}/.github/workflows/release.yml@refs/tags/v{version} \\\n"
        f"  --source-ref refs/tags/v{version} --deny-self-hosted-runners\n"
        "```\n"
    )


def _notes(a: argparse.Namespace) -> int:
    print(notes(CHANGELOG.read_text(), a.version) + verify_note(a.version, a.repository), end="")
    return 0


def _assets(a: argparse.Namespace) -> int:
    version = read_version(INIT.read_text())
    for p in write_assets(a.artifacts, a.wheel, a.out, version):
        print(f"{p.name}: {p.stat().st_size} bytes")
    return 0


COMMANDS = {
    "show": _show,
    "bump": _bump,
    "check": _check,
    "release": _release,
    "notes": _notes,
    "assets": _assets,
}

if __name__ == "__main__":
    os.environ.setdefault("SOURCE_DATE_EPOCH", str(EPOCH))
    raise SystemExit(main())
