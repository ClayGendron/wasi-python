"""News files: what one change says it moved, read where the change is judged and released.

A news file is `NNN-<slug>.md` in the changes folder (`CHANGES`), one per specification (or per
pull request that carries none), in three sections:

    # NNN: <title>

    ## Changelog

    ### Fixed              (New, Faster, Security, Fixed, Upgrading or For contributors)

    - **<what the reader gets>** <the one fact that changed>. [<page>](<SITE><path>/)

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

The changelog's lines are the release's notes, written for an embedder who did not follow the
work: each entry is one line, a bold lead of two to twelve words that says what the reader gets,
the fact that changed, and a link to the documentation site's page that explains it, last; at
most sixty words, not counting the links' addresses. The detail an agent needs stays with the
specification the title names.

The release's changelog assembly (`release/version.py bump`) takes the first two sections; the
gather lists a growth with the reason a claim gives; the acceptance from CI's record takes every
reason from the claims of the news files merged since the last acceptance. A changelog section of
a version above 0.1.1 is the reader's notes whole: a summary paragraph, then the entries under the
six headings in their order (`section_errors`); the sections before it were published in an older
shape and are left as they are. Standard library only, so the release's own script can load this
file by its path.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

CHANGES = "context/changes"
NAME = re.compile(r"(\d{3})-[a-z0-9]+(?:-[a-z0-9]+)*\.md")
PATH = re.compile(re.escape(CHANGES) + r"/" + NAME.pattern)
# The changelog's headings, in the order a reader scans them.
HEADINGS = ("New", "Faster", "Security", "Fixed", "Upgrading", "For contributors")
# The documentation site, which every entry links last; mkdocs.yml's site_url.
SITE = "https://claygendron.github.io/wasi-python/"
LEAD = re.compile(r"^- \*\*(?P<lead>.+?)\*\*\s+\S")
LINK = re.compile(r"\[[^\]\n]*\]\((?P<url>[^)\s]+)\)")
LEAD_WORDS = (2, 12)
ENTRY_WORDS = 60
SUMMARY_WORDS = (30, 120)
# The placeholder `bump` writes into a section no news file fills.
PLACEHOLDER = "- (what changed)"
# A changelog section's heading: `## <version> — <date or unreleased>`.
VERSION_HEADING = re.compile(r"^## (\S+) — (unreleased|\d{4}-\d{2}-\d{2})$", re.M)
# The last version whose notes were published in the older shape.
LAST_OLD_SHAPE = (0, 1, 1)
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
                raise NewsError(f"{name}: {_heading_error(heading)}")
            if heading in out:
                raise NewsError(f"{name}: the changelog heading {heading!r} twice")
            out[heading] = []
        elif not line.strip():
            continue
        elif heading is None or not line.startswith("- "):
            raise NewsError(f"{name}: a line of the changelog is not a `- ` line under a heading")
        else:
            faults = entry_errors(line)
            if faults:
                raise NewsError(f"{name}: {'; '.join(faults)}: {line[:60]!r}")
            out[heading].append(line)
    if not out:
        raise NewsError(f"{name}: the changelog has no heading")
    for heading, kept in out.items():
        if not kept:
            raise NewsError(f"{name}: the changelog heading {heading!r} has no line")
    return out


def _heading_error(heading: str) -> str:
    return f"the changelog heading {heading!r} is not one of " + ", ".join(HEADINGS)


def _words(text: str) -> int:
    """Whitespace-separated tokens, every link's address dropped and its text kept."""
    return len(LINK.sub(lambda m: m[0][: m[0].index("](")] + "]", text).split())


def entry_errors(line: str) -> list[str]:
    """What keeps one `- ` line from being a reader's entry: a bold lead of two to twelve words
    first, at most sixty words, and a link to a page of the documentation site last."""
    errors = []
    lead = LEAD.match(line)
    if lead is None:
        errors.append("the entry does not open with a bold lead and the fact after it")
    elif not LEAD_WORDS[0] <= len(lead["lead"].split()) <= LEAD_WORDS[1]:
        errors.append(
            f"a lead of {len(lead['lead'].split())} words; "
            f"{LEAD_WORDS[0]} to {LEAD_WORDS[1]} say the value"
        )
    if _words(line) > ENTRY_WORDS:
        errors.append(f"the entry is {_words(line)} words; at most {ENTRY_WORDS}")
    links = list(LINK.finditer(line.rstrip()))
    last = links[-1] if links else None
    if last is None or last.end() != len(line.rstrip()) or not last["url"].startswith(SITE):
        errors.append(f"the entry does not end with a link to a page of {SITE}")
    return errors


def summary_errors(text: str) -> list[str]:
    """What keeps a section's text before its first heading from being its summary: one
    paragraph, neither a list line nor a heading, of thirty to one hundred and twenty words."""
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines or [line.strip() for line in lines] == [PLACEHOLDER]:
        return ["no summary before the first heading"]
    if len(lines) > 1:
        return ["the summary is more than one paragraph on one line"]
    if lines[0].startswith(("- ", "#", "|")):
        return ["the summary is a list line, a heading or a table, not a paragraph"]
    words = _words(lines[0])
    if not SUMMARY_WORDS[0] <= words <= SUMMARY_WORDS[1]:
        return [f"the summary is {words} words; {SUMMARY_WORDS[0]} to {SUMMARY_WORDS[1]}"]
    return []


def section_errors(body: str) -> list[str]:
    """What keeps a changelog section's body from being the reader's notes: its summary, its
    headings among the six, each once, in their order, each with at least one entry, and each
    entry's shape."""
    preamble: list[str] = []
    blocks: dict[str, list[str]] = {}
    errors = []
    current = None
    for line in body.splitlines():
        if line.startswith("### "):
            current = line[4:].strip()
            if current in blocks:
                errors.append(f"the heading {current!r} twice")
            blocks.setdefault(current, [])
        elif current is None:
            preamble.append(line)
        elif line.strip():
            blocks[current].append(line)
    errors = summary_errors("\n".join(preamble)) + errors
    known = [h for h in blocks if h in HEADINGS]
    errors += [_heading_error(h) for h in blocks if h not in HEADINGS]
    if known != sorted(known, key=HEADINGS.index):
        errors.append("the headings are not in the order " + ", ".join(HEADINGS))
    if not blocks:
        errors.append("no heading and no entry")
    for heading, lines in blocks.items():
        if not lines:
            errors.append(f"the heading {heading!r} has no entry")
        for line in lines:
            if not line.startswith("- "):
                errors.append(f"under {heading!r}, a line that is not an entry: {line[:60]!r}")
                continue
            errors += [f"{e}: {line[:60]!r}" for e in entry_errors(line)]
    return errors


def link_errors(entries: list[str], docs: Path) -> list[str]:
    """Each link to the documentation site in the entries whose page is missing under `docs`:
    `<path>/` is `docs/<path>.md` or `docs/<path>/index.md`, the site's root `docs/index.md`; an
    anchor is not read."""
    errors = []
    for line in entries:
        for m in LINK.finditer(line):
            url = m["url"]
            if not url.startswith(SITE):
                continue
            path = url[len(SITE) :].split("#", 1)[0].strip("/")
            pages = [f"{path}.md", f"{path}/index.md"] if path else ["index.md"]
            if not any((docs / page).is_file() for page in pages):
                errors.append(f"{url}: no page " + " or ".join(f"docs/{p}" for p in pages))
    return errors


def is_reader_version(version: str) -> bool:
    """Whether a version's changelog section is the reader's notes: its `X.Y.Z` is above 0.1.1,
    so a pre-release of the next version counts."""
    m = re.match(r"(\d+)\.(\d+)\.(\d+)", version)
    return m is not None and tuple(int(x) for x in m.groups()) > LAST_OLD_SHAPE


@dataclass
class Section:
    version: str  # empty for the header above the first section
    date: str  # a date, "unreleased", or empty for the header
    body: str  # the text after the heading line, up to the next section
    line: int  # the body's first line in the file, counted from 1


def reader_sections(changelog: str) -> list[Section]:
    """The changelog's header (the text before its first version section) and every section
    whose version `is_reader_version` accepts, whatever other sections the file holds."""
    matches = list(VERSION_HEADING.finditer(changelog))
    head_end = matches[0].start() if matches else len(changelog)
    out = [Section("", "", changelog[:head_end], 1)]
    for i, m in enumerate(matches):
        if not is_reader_version(m[1]):
            continue
        start = m.end() + 1
        end = matches[i + 1].start() if i + 1 < len(matches) else len(changelog)
        out.append(Section(m[1], m[2], changelog[start:end], changelog[:start].count("\n") + 1))
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
    the tables are the release ledger's (`spec` None)."""
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


def claims_only(filename: str, text: str) -> list[Claim]:
    """A news file's claims alone, or NewsError for a broken claim block. For a file read back
    from git after bump removed it: its changelog was assembled and checked when it was merged,
    and an older file's changelog may be in a shape since retired, so only `## Claims` is read."""
    m = NAME.fullmatch(filename)
    if m is None:
        raise NewsError(f"{filename}: a news file is named NNN-<slug>.md")
    found = re.search(r"^## Claims\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    if found is None:
        return []
    return _claims(filename, m[1], found[1].splitlines())


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
# The release ledger

# Any claim the release must see whose news file will not be there: a pull request that changes a
# release-tier row, or what one runs, writes its [[claim]] blocks into a file of its own in the
# ledger's folder, named after its news file, since the run after its merge judges the normal
# tier alone; and the release's preparation writes the reason for a row an acceptance on dev
# recorded unclaimed into the file of the change it explains. One file per pull request, as the
# news files are, so two open pull requests never write the same file. The date before the
# release pull request (`release/version.py date`) moves each file under `## <version>` in the
# history and removes it, and the release pull request's gather and acceptance read both: what
# the date moved and any file written since. The folder's README stays, so the folder does.
LEDGER = "context/release-claims"
LEDGER_HISTORY = "context/release-claims-history.md"
# The single file the ledger was until every pull request had a file of its own: every pull
# request appended to its end, so each merge made every other open one conflict.
OLD_LEDGER = "context/release-claims.toml"
LEDGER_NAME = re.compile(r"(\d{3})-[a-z0-9]+(?:-[a-z0-9]+)*\.toml")
# A file the date moved, in the history: its name in backticks, then its blocks in a fence.
MOVED_FILE = re.compile(r"^`(" + LEDGER_NAME.pattern + r")`:\n\n```toml\n(.*?)^```$", re.M | re.S)
VERSION_FILE = "src/wasi_python/__init__.py"


def package_version(repo: Path) -> str:
    """`__version__` as the package's one version line writes it; empty when there is none."""
    try:
        text = (repo / VERSION_FILE).read_text(encoding="utf-8")
    except OSError:
        return ""
    m = re.search(r'^__version__ = "([^"]+)"$', text, re.M)
    return m[1] if m else ""


def ledger_tables(name: str, text: str, spec: str | None = None) -> list[Claim]:
    """The claims of ledger text, or NewsError naming what is wrong: [[claim]] tables alone, each
    in a news file's claim shape, its spec `spec` or, when None, any specification's number."""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        raise NewsError(f"{name}: not TOML ({e})") from e
    if set(data) - {"claim"} or not isinstance(data.get("claim", []), list):
        raise NewsError(f"{name}: the ledger holds only [[claim]] tables")
    return _claim_tables(name, data.get("claim", []), spec)


def ledger_file_claims(name: str, text: str) -> list[Claim]:
    """The claims of one ledger file, `name` its file name: named NNN-<slug>.toml after its news
    file, at least one [[claim]] table, each of spec NNN."""
    m = LEDGER_NAME.fullmatch(name)
    if m is None:
        raise NewsError(f"{LEDGER}/{name}: a ledger file is named NNN-<slug>.toml, as news files")
    found = ledger_tables(f"{LEDGER}/{name}", text, m[1])
    if not found:
        raise NewsError(f"{LEDGER}/{name}: a ledger file holds at least one [[claim]] table")
    errors = header_errors(text, len(found))
    if errors:
        raise NewsError(f"{LEDGER}/{name}: {errors[0]}")
    return found


def header_errors(text: str, tables: int) -> list[str]:
    """Why a ledger file's array-of-tables headers are not each `[[claim]]` alone at the start of
    a line, one for each of its `tables` claims. TOML reads `[[ claim ]]`, `[["claim"]]` and an
    indented header as the same table, and a reader of the text, a person or a check that cuts
    the file into blocks, would miss a block so written."""
    out = [
        f"line {k}: an array-of-tables header is written [[claim]], at the start of the line, "
        f"not {line.strip()!r}"
        for k, line in enumerate(text.splitlines(), 1)
        if re.match(r"\s*\[\[", line) and line.rstrip() != "[[claim]]"
    ]
    literal = sum(1 for line in text.splitlines() if line.rstrip() == "[[claim]]")
    if not out and literal != tables:
        out.append(f"{tables} [[claim]] tables, but {literal} lines read [[claim]]")
    return out


def ledger_files(folder: Path) -> dict[str, str]:
    """Each .toml file in the ledger's folder, by name, in name order; none without the folder."""
    if not folder.is_dir():
        return {}
    return {
        p.name: p.read_text(encoding="utf-8")
        for p in sorted(folder.iterdir())
        if p.is_file() and p.suffix == ".toml"
    }


def _section(text: str, version: str) -> str | None:
    """The body of `## <version>` in the history, up to the next `## ` heading; None without one."""
    m = re.search(rf"^## {re.escape(version)}\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m[1] if m else None


def ledger_claims(repo: Path) -> list[Claim]:
    """The release ledger's claims: the blocks the date moved under this version in the history,
    then those of each file still in the folder, by file name."""
    out = []
    history = repo / LEDGER_HISTORY
    body = (
        _section(history.read_text(encoding="utf-8"), package_version(repo))
        if history.is_file()
        else None
    )
    for n, block in enumerate(FENCE.findall(body or ""), 1):
        out += ledger_tables(f"{LEDGER_HISTORY} block {n}", block)
    for name, text in ledger_files(repo / LEDGER).items():
        out += ledger_file_claims(name, text)
    return out


def moved_files(history: str, version: str) -> dict[str, str]:
    """Each ledger file the date moved under `## <version>` in the history, by name, its blocks
    stripped; empty when the section moved none or there is no section."""
    return {m[1]: m[3].strip() for m in MOVED_FILE.finditer(_section(history, version) or "")}


def move_ledger(files: dict[str, str], history: str, version: str, day: str) -> str:
    """The history with the ledger's files (`files`, name to text) moved under `## <version>`,
    newest section first, each under its name in file-name order. Each file is checked for its
    shape first; a history that already has the version's section refuses."""
    if _section(history, version) is not None:
        raise NewsError(f"{LEDGER_HISTORY} already has a section for {version}")
    for name, text in files.items():
        ledger_file_claims(name, text)
    said = f"Moved by `release/version.py date` on {day}, before the release pull request."
    moved = [f"`{name}`:\n\n```toml\n{files[name].strip()}\n```" for name in sorted(files)]
    body = "\n\n".join(moved) if moved else "No block was in the ledger at the date."
    section = f"## {version}\n\n{said}\n\n{body}\n\n"
    first = re.search(r"^## ", history, re.M)
    if first is None:
        return history.rstrip("\n") + "\n\n" + section.rstrip("\n") + "\n"
    return history[: first.start()] + section + history[first.start() :]
