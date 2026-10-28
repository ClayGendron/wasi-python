"""The package's version, its changelog and its release tag.

    uv run python release/version.py show
    uv run python release/version.py bump [--to 0.1.0a2]   # and the news files into CHANGELOG.md
    uv run python release/version.py check [--tag v0.1.0a1]
    uv run python release/version.py date [--day 2026-10-26]
    uv run python release/version.py release [--push]
    uv run python release/version.py notes 0.1.0a1 [--repository owner/name]
    uv run python release/version.py assets <artifact dir> <wheel> <out dir>

`__version__` in src/wasi_python/__init__.py is the only place the version is written;
pyproject.toml reads it through hatchling. A release is the annotated tag `v<version>` on a
pushed commit of main; pushing it starts .github/workflows/release.yml. Pushing a release tag is
cutting a release, which only the owner decides. The version's section is dated (`date`) on dev,
before the release pull request from dev to main, so the commit that pull request judges is the
commit main receives and the tag names (`release`), with nothing committed between.

A change's CHANGELOG lines and package rows are written in its news file (`CHANGES`), not into
CHANGELOG.md by hand. `bump` assembles them into the new version's section (joining an
unreleased section already written for it), puts each package row into the packages page's table,
and removes the news files; the reader of their shape is the judge's own, loaded by its path.

From 0.1.2 a version's section is its release's notes for an embedder who did not follow the
work: a summary paragraph, then the entries under the reader's six headings. The preparation
writes the summary into the section between `bump` and `date`; it and the rewrites the notes'
reader asks for are the only hand edits of the section. `date` refuses a section out of that
shape, and `check` reports one for every dated section.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
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
CHANGES = REPO / "context" / "changes"
PACKAGES = REPO / "docs" / "reference" / "packages.md"
# The release-tier claims ledger and its history by release, which `date` moves the blocks into.
LEDGER = REPO / "context" / "release-tier-claims.toml"
LEDGER_HISTORY = REPO / "context" / "release-tier-claims-history.md"
NEWS_READER = REPO / "tests" / "harness" / "news.py"
# The packages page's table the news files' rows belong to.
PACKAGE_HEADER = "| package | version | what works |"
PLACEHOLDER = "- (what changed)"
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


def add_section(changelog: str, version: Version, news: list | None = None) -> str:
    """The new version's `unreleased` section with the news files' lines under their headings:
    a new section above the newest one, or the unreleased one already written for it, joined.
    With no news, a new section with a placeholder line, never the one already written."""
    have = sections(changelog).get(str(version))
    if have is not None and (have != "unreleased" or not news):
        dated = f", dated {have}" if have != "unreleased" else " and no news file adds to it"
        raise ReleaseError(f"CHANGELOG.md already has a section for {version}{dated}")
    if have is None and not news:
        entry = f"## {version} — unreleased\n\n{PLACEHOLDER}\n\n"
        first = SECTION.search(changelog)
        if first is None:
            return changelog.rstrip("\n") + "\n\n" + entry
        return changelog[: first.start()] + entry + changelog[first.start() :]
    if have is None:
        entry = f"## {version} — unreleased\n\n"
        first = SECTION.search(changelog)
        changelog = (
            changelog.rstrip("\n") + "\n\n" + entry
            if first is None
            else changelog[: first.start()] + entry + changelog[first.start() :]
        )
    matches = list(SECTION.finditer(changelog))
    at = next(i for i, m in enumerate(matches) if m.group(1) == str(version))
    start = matches[at].end()
    end = matches[at + 1].start() if at + 1 < len(matches) else len(changelog)
    body = _joined(changelog[start:end], news or [])
    tail = "\n\n" if at + 1 < len(matches) else "\n"
    return changelog[:start] + "\n\n" + body + tail + changelog[end:]


def _joined(body: str, news: list) -> str:
    """A section's body with the news files' lines added under their headings: the text before
    the first heading kept (the placeholder dropped), the headings in the CHANGELOG's order, each
    heading's lines as written, then each news file's in name order."""
    preamble: list[str] = []
    blocks: dict[str, list[str]] = {}
    current = None
    for line in body.strip("\n").splitlines():
        if line.startswith("### "):
            current = line[4:].strip()
            blocks.setdefault(current, [])
        elif current is None:
            preamble.append(line)
        elif line.strip():
            blocks[current].append(line)
    preamble = [] if [x for x in preamble if x.strip()] == [PLACEHOLDER] else preamble
    for n in sorted(news, key=lambda n: n.name):
        for heading, lines in n.changelog.items():
            blocks.setdefault(heading, []).extend(lines)
    order = list(_reader().HEADINGS)
    headings = [h for h in order if h in blocks] + [h for h in blocks if h not in order]
    parts = ["\n".join(preamble).strip("\n")] if "".join(preamble).strip() else []
    parts += [f"### {h}\n\n" + "\n".join(blocks[h]) for h in headings]
    return "\n\n".join(parts)


def add_rows(page: str, rows: list[str]) -> str:
    """The packages page with each row in its table: replacing the row of the same package, or
    after the table's last row."""
    if not rows:
        return page
    lines = page.split("\n")
    try:
        head = lines.index(PACKAGE_HEADER)
    except ValueError:
        raise ReleaseError(f"the packages page has no table headed {PACKAGE_HEADER}") from None
    end = head + 2
    while end < len(lines) and lines[end].startswith("|"):
        end += 1

    def package(row: str) -> str:
        return row.split("|")[1].strip()

    for row in rows:
        same = [i for i in range(head + 2, end) if package(lines[i]) == package(row)]
        if same:
            lines[same[0]] = row
        else:
            lines.insert(end, row)
            end += 1
    return "\n".join(lines)


def _reader():
    """The judge's reader of news files and of the release-tier ledger, loaded by its path."""
    spec = importlib.util.spec_from_file_location("wasi_python_news", NEWS_READER)
    reader = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = reader  # dataclasses look their module up here
    spec.loader.exec_module(reader)
    return reader


def read_news(folder: Path) -> list:
    """Every news file in `folder`, by the judge's reader; a broken one stops the bump."""
    reader = _reader()
    try:
        return reader.folder(folder)
    except reader.NewsError as e:
        raise ReleaseError(f"a news file is broken: {e}") from None


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
    errors += reader_errors(changelog)
    if tag is not None:
        if tag != f"v{version}":
            errors.append(f"the tag {tag} is not v{version}, the version it points to")
        elif sections(changelog).get(version) == "unreleased":
            errors.append(f"CHANGELOG.md's section for {version} is still unreleased")
    return errors


def reader_errors(changelog: str) -> list[str]:
    """Each dated section written for the reader that is out of the reader's shape, one line per
    fault; an unreleased one waits for its summary, which comes between bump and date."""
    reader = _reader()
    return [
        f"CHANGELOG.md's section for {s.version}: {e}"
        for s in reader.reader_sections(changelog)
        if s.version and s.date != "unreleased"
        for e in reader.section_errors(s.body)
    ]


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
    date = sub.add_parser("date")
    date.add_argument("--day", help="YYYY-MM-DD; today in UTC by default")
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
    news = read_news(CHANGES)  # every edit below is made before any is written
    changelog = add_section(CHANGELOG.read_text(), new, news)
    rows = [row for n in sorted(news, key=lambda n: n.name) for row in n.rows]
    page = add_rows(PACKAGES.read_text(), rows) if rows else None
    INIT.write_text(init_text)
    CHANGELOG.write_text(changelog)
    if page is not None:
        PACKAGES.write_text(page)
    for n in news:
        (CHANGES / f"{n.name}.md").unlink()
    told = f"{len(news)} news file(s) assembled and removed" if news else "no news file"
    print(f"{current} -> {new}: {told}; read CHANGELOG.md's section, then commit")
    return 0


def _check(a: argparse.Namespace) -> int:
    errors = check_errors(INIT.read_text(), PYPROJECT.read_text(), CHANGELOG.read_text(), a.tag)
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)
    if not errors:
        print(f"ok {read_version(INIT.read_text())}" + (f" (tag {a.tag})" if a.tag else ""))
    return 1 if errors else 0


def _date(a: argparse.Namespace) -> int:
    """Date the version's section: a change for the pull request into dev that comes before the
    release pull request. A news file merged after bump is joined to the section first and
    removed, so its line reaches the notes; the release-tier ledger's blocks move under the
    version in the ledger's history, which the release pull request's acceptance reads. Every
    edit is made before any is written. It commits nothing."""
    version = Version.parse(read_version(INIT.read_text()))
    day = a.day or datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d")
    news = read_news(CHANGES)
    changelog = CHANGELOG.read_text()
    if news:
        changelog = add_section(changelog, version, news)
    reader = _reader()
    if reader.is_reader_version(str(version)) and str(version) in sections(changelog):
        faults = reader.section_errors(notes(changelog, str(version)))
        if faults:
            raise ReleaseError(
                f"{version}'s section is not the reader's notes: " + "; ".join(faults)
            )
    changelog = date_section(changelog, version, day)
    rows = [row for n in sorted(news, key=lambda n: n.name) for row in n.rows]
    page = add_rows(PACKAGES.read_text(), rows) if rows else None
    moved = None
    if LEDGER.is_file() and LEDGER_HISTORY.is_file():
        reader = _reader()
        try:
            moved = reader.move_ledger(
                LEDGER.read_text(), LEDGER_HISTORY.read_text(), str(version), day
            )
        except reader.NewsError as e:
            raise ReleaseError(f"the release-tier ledger: {e}") from None
    CHANGELOG.write_text(changelog)
    if page is not None:
        PACKAGES.write_text(page)
    for n in news:
        (CHANGES / f"{n.name}.md").unlink()
    if moved is not None:
        LEDGER.write_text(moved[0])
        LEDGER_HISTORY.write_text(moved[1])
    told = f"; {len(news)} news file(s) joined and removed" if news else ""
    print(f"dated {version} {day}{told}: commit through a pull request into dev")
    return 0


def _release(a: argparse.Namespace) -> int:
    """Tag main's tip, the commit the release pull request judged plus its acceptance, which the
    owner has pushed to main; nothing is committed, so the tag names exactly that commit."""
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
    errors = check_errors(INIT.read_text(), PYPROJECT.read_text(), CHANGELOG.read_text(), tag)
    if errors:  # an undated section is dated on dev, before the release pull request
        raise ReleaseError("; ".join(errors))
    message = f"wasi-python {version}\n\n{notes(CHANGELOG.read_text(), str(version))}"
    git("tag", "-a", tag, "-m", message)
    push = f"git push origin {tag}"
    if a.push:
        git("push", "origin", tag)
        print(f"pushed {tag}: the release workflow is running")
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
    "date": _date,
    "release": _release,
    "notes": _notes,
    "assets": _assets,
}

if __name__ == "__main__":
    os.environ.setdefault("SOURCE_DATE_EPOCH", str(EPOCH))
    raise SystemExit(main())
