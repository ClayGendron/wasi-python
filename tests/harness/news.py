"""News files: what one change says it moved, read where the change is judged and released.

A news file is `NNN-<slug>.md` in the changes folder (`CHANGES`), one per specification (or per
pull request that carries none), in three sections:

    # NNN: <title>

    ## Changelog

    ### Changed            (Added, Changed, Fixed or Security, as CHANGELOG.md uses them)

    - **<what>**: <the line, one paragraph>

    ## Package rows       (optional: rows of the packages page's table, or "None.")

    | <package> | <version> | <what works> |

    ## Claims

    ```toml
    [[claim]]
    spec = "NNN"
    new = []             # checks or files added
    retired = []         # checks removed: an acceptance retires the absent ones they name
    changed = []         # checks whose status, need, reason or facts move
    passes = []          # upstream checks whose pass count moves
    fewer = ""           # the reason, when a count in `passes` falls
    grows = []           # checks whose fuel or bytes grow
    growth = ""          # the reason, required with grows
    units = 0            # unit tests added
    [claim.judge]        # each judge file changed, with its reason
    [claim.moved]        # each check moved between tiers, with its reason
    ```

The release's changelog assembly (`release/version.py bump`) takes the first two sections; the
gather lists a growth with the reason a claim gives; the acceptance from CI's record takes every
reason from the claims of the news files merged since the last acceptance. Standard library only,
so the release's own script can load this file by its path.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

CHANGES = "context/changes"
NAME = re.compile(r"(\d{3})-[a-z0-9]+(?:-[a-z0-9]+)*\.md")
PATH = re.compile(re.escape(CHANGES) + r"/" + NAME.pattern)
HEADINGS = ("Added", "Changed", "Fixed", "Security")  # in the CHANGELOG's order
SECTIONS = ("Changelog", "Package rows", "Claims")
LISTS = ("new", "retired", "changed", "passes", "grows")
REASONS = ("growth", "fewer")
TABLES = ("judge", "moved")
KEYS = frozenset({"spec", "units", *LISTS, *REASONS, *TABLES})
FENCE = re.compile(r"^```toml\n(.*?)^```$", re.M | re.S)


class NewsError(ValueError):
    """A news file that does not have the shape; the message names the file and what is wrong."""


@dataclass
class Claim:
    spec: str
    new: list[str] = field(default_factory=list)
    retired: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    passes: list[str] = field(default_factory=list)
    fewer: str = ""
    grows: list[str] = field(default_factory=list)
    growth: str = ""
    units: int = 0
    judge: dict[str, str] = field(default_factory=dict)
    moved: dict[str, str] = field(default_factory=dict)


@dataclass
class News:
    name: str  # NNN-<slug>, the file's name without .md
    spec: str  # NNN
    changelog: dict[str, list[str]]  # heading -> its lines, in the file's order
    rows: list[str]  # the package rows, each a table row
    claims: list[Claim]


def is_news_path(rel: str) -> bool:
    """Whether a repository path is a news file (the folder's README is not)."""
    return bool(PATH.fullmatch(rel))


def _sections(name: str, text: str) -> tuple[str, dict[str, list[str]]]:
    """The title line and each `## ` section's lines."""
    title, out, current = "", {}, None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            if current not in SECTIONS:
                raise NewsError(f"{name}: a section the shape does not name: {current!r}")
            if current in out:
                raise NewsError(f"{name}: the section {current!r} twice")
            out[current] = []
        elif current is not None:
            out[current].append(line)
        elif line.startswith("# ") and not title:
            title = line[2:].strip()
        elif line.strip():
            raise NewsError(f"{name}: text before the first section: {line[:60]!r}")
    return title, out


def _changelog(name: str, lines: list[str]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    heading = None
    for line in lines:
        if line.startswith("### "):
            heading = line[4:].strip()
            if heading not in HEADINGS:
                raise NewsError(
                    f"{name}: the changelog heading {heading!r} is not one of "
                    + ", ".join(HEADINGS)
                )
            if heading in out:
                raise NewsError(f"{name}: the changelog heading {heading!r} twice")
            out[heading] = []
        elif not line.strip():
            continue
        elif heading is None or not line.startswith("- "):
            raise NewsError(f"{name}: a line of the changelog is not a `- ` line under a heading")
        else:
            out[heading].append(line)
    if not out:
        raise NewsError(f"{name}: the changelog has no heading")
    for heading, kept in out.items():
        if not kept:
            raise NewsError(f"{name}: the changelog heading {heading!r} has no line")
    return out


def _rows(name: str, lines: list[str]) -> list[str]:
    kept = [line.strip() for line in lines if line.strip()]
    if kept == ["None."]:
        return []
    for line in kept:
        cells = line.split("|")
        if not (line.startswith("|") and line.endswith("|") and len(cells) == 5):
            raise NewsError(f"{name}: a package row is not a table row of three cells: {line!r}")
    return kept


def _claims(name: str, spec: str, lines: list[str]) -> list[Claim]:
    blocks = FENCE.findall("\n".join(lines) + "\n")
    if len(blocks) != 1:
        raise NewsError(f"{name}: the claims are not one ```toml block")
    try:
        data = tomllib.loads(blocks[0])
    except tomllib.TOMLDecodeError as e:
        raise NewsError(f"{name}: the claim block is not TOML ({e})") from e
    if set(data) != {"claim"} or not isinstance(data["claim"], list):
        raise NewsError(f"{name}: the claim block holds only [[claim]] tables")
    return _claim_tables(name, data["claim"], spec)


def _claim_tables(name: str, tables: list, spec: str | None) -> list[Claim]:
    """Each [[claim]] table in the shape, its spec the news file's (`spec`), or any number when
    the tables are the release-tier ledger's (`spec` None)."""
    out = []
    for n, c in enumerate(tables, 1):
        where = f"{name}: claim {n}"
        unknown = sorted(set(c) - KEYS)
        if unknown:
            raise NewsError(f"{where}: keys the shape does not name: {', '.join(unknown)}")
        if spec is not None and c.get("spec") != spec:
            raise NewsError(f"{where}: spec is {c.get('spec')!r}, not the file's {spec}")
        if spec is None and not re.fullmatch(r"\d{3}", str(c.get("spec", ""))):
            raise NewsError(f"{where}: spec is {c.get('spec')!r}, not a specification's number")
        for k in LISTS:
            v = c.get(k, [])
            if not isinstance(v, list) or not all(isinstance(x, str) and x for x in v):
                raise NewsError(f"{where}: {k} is a list of strings")
        for k in REASONS:
            if not isinstance(c.get(k, ""), str):
                raise NewsError(f"{where}: {k} is a string")
        for k in TABLES:
            v = c.get(k, {})
            if not isinstance(v, dict) or not all(
                isinstance(r, str) and r.strip() for r in v.values()
            ):
                raise NewsError(f"{where}: {k} names each entry with its reason, a string")
        if c.get("grows") and not c.get("growth"):
            raise NewsError(f"{where}: grows needs growth, its reason")
        if type(c.get("units", 0)) is not int:
            raise NewsError(f"{where}: units is a whole number")
        out.append(Claim(**c))
    return out


def parse(filename: str, text: str) -> News:
    """A news file's content, or NewsError naming what is wrong."""
    m = NAME.fullmatch(filename)
    if m is None:
        raise NewsError(f"{filename}: a news file is named NNN-<slug>.md")
    spec = m[1]
    title, sections = _sections(filename, text)
    if not title.startswith(f"{spec}: "):
        raise NewsError(f"{filename}: the title does not begin with {spec}: ({title!r})")
    for want in ("Changelog", "Claims"):
        if want not in sections:
            raise NewsError(f"{filename}: no ## {want} section")
    return News(
        name=filename[: -len(".md")],
        spec=spec,
        changelog=_changelog(filename, sections["Changelog"]),
        rows=_rows(filename, sections.get("Package rows", [])),
        claims=_claims(filename, spec, sections["Claims"]),
    )


def load(path: Path) -> News:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise NewsError(f"{path.name}: not a readable file ({e})") from e
    return parse(path.name, text)


def folder(path: Path) -> list[News]:
    """Every news file in a folder, by name; its README and anything else are not news files."""
    if not path.is_dir():
        return []
    return [load(p) for p in sorted(path.iterdir()) if p.is_file() and NAME.fullmatch(p.name)]


def names(entry: str, key: str) -> bool:
    """Whether a claimed entry names a check or a file: exactly, as the check's file, or by a
    trailing `*` prefix."""
    if entry.endswith("*"):
        return key.startswith(entry[:-1])
    return key == entry or ("::" not in entry and key.split("::", 1)[0] == entry)


def reason(claims: list[Claim], kind: str, key: str) -> str | None:
    """The reason the first claim that names `key` under `kind` gives, as `NNN: <reason>`: grows
    with its growth, passes with its fewer, judge and moved with their own; retired with the
    claim's spec alone. None when no claim names it, or when the claim gives no reason."""
    for c in claims:
        if kind in TABLES:
            hit = next((r for e, r in getattr(c, kind).items() if names(e, key)), None)
        elif any(names(e, key) for e in getattr(c, kind)):
            hit = {"grows": c.growth, "passes": c.fewer, "retired": "retired"}.get(kind, "")
        else:
            continue
        if hit:
            return f"{c.spec}: {hit}"
    return None


# ---------------------------------------------------------------------------------------------
# The release-tier ledger

# A pull request that changes a release-tier row, or what one runs, appends its [[claim]] block to
# the ledger, since the run after its merge judges the normal tier alone and bump removes its
# news file before the release. The date before the release pull request (`release/version.py
# date`) moves the blocks under `## <version>` in the history, and the release pull request's
# gather and acceptance read both: what the date moved and anything appended since.
LEDGER = "context/release-tier-claims.toml"
LEDGER_HISTORY = "context/release-tier-claims-history.md"
VERSION_FILE = "src/wasi_python/__init__.py"


def package_version(repo: Path) -> str:
    """`__version__` as the package's one version line writes it; empty when there is none."""
    try:
        text = (repo / VERSION_FILE).read_text(encoding="utf-8")
    except OSError:
        return ""
    m = re.search(r'^__version__ = "([^"]+)"$', text, re.M)
    return m[1] if m else ""


def _ledger_tables(name: str, text: str) -> list[Claim]:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        raise NewsError(f"{name}: not TOML ({e})") from e
    if set(data) - {"claim"} or not isinstance(data.get("claim", []), list):
        raise NewsError(f"{name}: the ledger holds only [[claim]] tables")
    return _claim_tables(name, data.get("claim", []), None)


def _section(text: str, version: str) -> str | None:
    """The body of `## <version>` in the history, up to the next `## ` heading; None without one."""
    m = re.search(rf"^## {re.escape(version)}\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m[1] if m else None


def ledger_claims(repo: Path) -> list[Claim]:
    """The release's release-tier claims: the blocks the date moved under this version in the
    history, then any still in the ledger."""
    out = []
    history = repo / LEDGER_HISTORY
    body = (
        _section(history.read_text(encoding="utf-8"), package_version(repo))
        if history.is_file()
        else None
    )
    for n, block in enumerate(FENCE.findall(body or ""), 1):
        out += _ledger_tables(f"{LEDGER_HISTORY} block {n}", block)
    ledger = repo / LEDGER
    if ledger.is_file():
        out += _ledger_tables(LEDGER, ledger.read_text(encoding="utf-8"))
    return out


def move_ledger(ledger: str, history: str, version: str, day: str) -> tuple[str, str]:
    """The ledger with its blocks moved under `## <version>` in the history, newest first: (the
    ledger's header comments alone, the history with the new section). The blocks are checked
    for their shape first; a history that already has the version's section refuses."""
    if _section(history, version) is not None:
        raise NewsError(f"{LEDGER_HISTORY} already has a section for {version}")
    lines = ledger.splitlines(keepends=True)
    at = next((k for k, line in enumerate(lines) if not line.startswith("#")), len(lines))
    header, blocks = "".join(lines[:at]), "".join(lines[at:]).strip()
    _ledger_tables(LEDGER, blocks)
    said = f"Moved by `release/version.py date` on {day}, before the release pull request."
    body = f"```toml\n{blocks}\n```" if blocks else "No block was in the ledger at the date."
    section = f"## {version}\n\n{said}\n\n{body}\n\n"
    first = re.search(r"^## ", history, re.M)
    if first is None:
        new = history.rstrip("\n") + "\n\n" + section.rstrip("\n") + "\n"
    else:
        new = history[: first.start()] + section + history[first.start() :]
    return header, new
