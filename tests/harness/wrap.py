"""Markdown paragraphs on one line each: the rule's reading, its check and its fix.

    uv run python tests/harness/wrap.py --check PATH...   # path:line per wrapped paragraph; exit 1
    uv run python tests/harness/wrap.py --fix PATH...     # rewrite in place; print each changed

A renderer joins the lines of one paragraph with spaces, so a paragraph hard-wrapped at a column
renders as it would on one line, while every edit to it re-flows its neighbours and every diff of
it is noisier. The fix joins what a renderer joins and nothing else: the lines of one paragraph,
a list item's continuation lines (nested items too), and the lines of one blockquote paragraph
(the first line's `>` prefix kept, the others' dropped). It never joins fenced or indented code,
a table, a heading, a horizontal rule, an HTML block, front matter, a link reference definition,
an admonition's or a tab's opening line, two list items, or a line ending in a hard break (two
spaces or a backslash) to the next. When in doubt it leaves the lines as they are, so the check
reports only what the fix would join.

A path may be a file or a directory; a directory is searched for `*.md`, never into the build
and download trees, the agents' settings, the test app, the built site, the prior-art clones or a
path git ignores (unless the directory asked for is itself ignored). A file with CRLF line
endings is reported and never rewritten. The fix keeps the file's final newline, or its lack of
one, and is idempotent: a second fix changes nothing, and a file with no offence is not written.
Self-contained: it imports no other harness module, so it runs as a script.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

# Directory names a search never enters, wherever they are, and the clones' folder by its parents.
SKIP_DIRS = frozenset(
    {"build", "downloads", ".claude", "test_app", "site", ".git", ".venv", ".venv-build"}
    | {"__pycache__", "node_modules"}
    # Build inputs: the manifest hashes every file under recipes/, so a rewrap makes the set stale.
    | {"recipes"}
)
SKIP_NESTED = (("context", "prior_art"),)

FENCE = re.compile(r"^[ \t]*(`{3,}|~{3,})(.*)$")
ATX = re.compile(r"^#{1,6}(?:[ \t]|$)")
RULE = re.compile(r"^(?:(?:\*[ \t]*){3,}|(?:-[ \t]*){3,}|(?:_[ \t]*){3,})$")
SETEXT = re.compile(r"^(?:=+|-+)[ \t]*$")
BULLET = re.compile(r"^([-*+])(?:([ \t]+)(.*))?$")
ORDERED = re.compile(r"^(\d{1,9})([.)])(?:([ \t]+)(.*))?$")
REFERENCE = re.compile(r"^\[(?!\^)[^\]]+\]:")
# MkDocs' admonitions (`!!! note`, `??? tip`, `???+ tip`) and pymdownx's tabs (`=== "Tab"`):
# a line that opens a block whose body is indented four columns under it.
OPENER = re.compile(r"^(?:!!!|\?\?\?\+?|===)[ \t]+\S")
DELIMITER = re.compile(r"^\|?[ \t]*:?-+:?[ \t]*(?:\|[ \t]*:?-+:?[ \t]*)*\|?[ \t]*$")
QUOTE = re.compile(r"^[ \t]*> ?")
# HTML blocks, as CommonMark reads them: the first five kinds end at their closing text, the
# sixth (block-level tags) and seventh (any other tag alone on its line) at a blank line. Only
# the first six may interrupt a paragraph.
HTML_ENDS = (
    (re.compile(r"^<(script|pre|style|textarea)(?:[\s>]|$)", re.I), None),
    (re.compile(r"^<!--"), "-->"),
    (re.compile(r"^<\?"), "?>"),
    (re.compile(r"^<!\[CDATA\["), "]]>"),
    (re.compile(r"^<![A-Za-z]"), ">"),
)
BLOCK_TAGS = (
    "address|article|aside|base|basefont|blockquote|body|caption|center|col|colgroup|dd|details|"
    "dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|form|frame|frameset|h[1-6]|head|"
    "header|hr|html|iframe|legend|li|link|main|menu|menuitem|nav|noframes|ol|optgroup|option|p|"
    "param|picture|search|section|source|summary|table|tbody|td|tfoot|th|thead|title|tr|track|ul"
)
HTML_BLOCK = re.compile(rf"^</?(?:{BLOCK_TAGS})(?:[\s/>]|$)", re.I)
HTML_START = re.compile(r"^<[A-Za-z/!?]")
AUTOLINK = re.compile(r"^<(?:[A-Za-z][A-Za-z0-9+.-]{1,31}:[^\s<>]*|[^\s<>@]+@[^\s<>]+)>")


def _indent(text: str) -> int:
    """The leading whitespace's width in columns, a tab reaching the next multiple of four."""
    col = 0
    for ch in text:
        if ch == " ":
            col += 1
        elif ch == "\t":
            col += 4 - col % 4
        else:
            break
    return col


def hard_break(line: str) -> bool:
    """The line ends in a hard break: two or more spaces, or an odd run of backslashes."""
    if line.endswith("  "):
        return True
    body = line.rstrip()
    return body == line and (len(body) - len(body.rstrip("\\"))) % 2 == 1


def _fence(stripped: str) -> tuple[str, int] | None:
    """(the fence's character, its length) when the line opens a fenced code block."""
    m = FENCE.match(stripped)
    if m is None or (m[1][0] == "`" and "`" in m[2]):
        return None
    return m[1][0], len(m[1])


def _closes(text: str, fence: tuple[str, int]) -> bool:
    m = FENCE.match(text)
    return bool(m and m[1][0] == fence[0] and len(m[1]) >= fence[1] and not m[2].strip())


def _html(stripped: str, at_start: bool) -> str | None:
    """How the HTML block the line opens ends: its closing text, "" for a blank line, or None
    when the line opens none. At a block's start any tag opens one; inside a paragraph only
    the kinds that may interrupt it do."""
    if not HTML_START.match(stripped) or AUTOLINK.match(stripped):
        return None
    for pattern, end in HTML_ENDS:
        m = pattern.match(stripped)
        if m:
            close = end if end is not None else f"</{m[1].lower()}>"
            rest = stripped[m.end() :]
            done = close in (rest.lower() if end is None else rest)
            return "" if done and close != "" else close
    if HTML_BLOCK.match(stripped) or at_start:
        return "\n"  # a blank line ends it
    return None


def _table_starts(stripped: str, following: str | None) -> bool:
    if stripped.startswith("|"):
        return True
    return (
        "|" in stripped
        and following is not None
        and "|" in following
        and bool(DELIMITER.match(following.strip()))
    )


def _item(stripped: str, indent: int, interrupting: bool, in_list: bool) -> tuple[int, str] | None:
    """(the item's content column, its content) when the line is a list item. Inside a
    paragraph an empty item is text, and a numbered one is an item only when its number is 1
    or a list is open, so a sentence wrapped before "2026. The" stays one paragraph."""
    m = BULLET.match(stripped)
    if m is None:
        m = ORDERED.match(stripped)
        if m is None:
            return None
        if interrupting and int(m[1]) != 1 and not in_list:
            return None
        marker, gap, content = len(m[1]) + 1, m[3], m[4]
    else:
        marker, gap, content = 1, m[2], m[3]
    if interrupting and not (content or "").strip():
        return None
    width = _indent(gap or " ")
    width = width if 1 <= width <= 4 and (content or "").strip() else 1
    return indent + marker + width, content or ""


class _Reader:
    """One container's lines (the file, or a blockquote's lines with one `>` removed), read
    into groups of line indexes a renderer joins into one paragraph."""

    def __init__(self, items: list[tuple[int, str]], groups: list[list[int]], inner: dict) -> None:
        self.items, self.groups, self.inner = items, groups, inner
        self.lists: list[int] = []
        self.cur: list[int] | None = None
        self.broken = False  # the open paragraph's last line ends in a hard break
        self.mode: tuple | None = None
        for idx, text in items:
            inner[idx] = text

    def close(self, keep: bool = True) -> None:
        if self.cur is not None and len(self.cur) > 1 and keep:
            self.groups.append(self.cur)
        self.cur, self.broken = None, False

    def open(self, idx: int, text: str) -> None:
        self.close()
        self.cur, self.broken = [idx], hard_break(text)

    def pop_lists(self, indent: int) -> None:
        while self.lists and self.lists[-1] > indent:
            self.lists.pop()

    def run(self, start: int = 0) -> None:
        i = start
        while i < len(self.items):
            i = self.step(i)
        self.close()

    def step(self, i: int) -> int:
        idx, text = self.items[i]
        if self.mode is not None and not self.in_mode(text):
            return i + 1
        if not text.strip():
            self.close()
            return i + 1
        stripped, indent = text.lstrip(), _indent(text)
        following = self.items[i + 1][1] if i + 1 < len(self.items) else None
        at_start = self.cur is None
        fence = _fence(stripped)
        if fence is not None:
            self.close()
            self.mode = ("fence", fence)
            return i + 1
        if at_start and indent >= (self.lists[-1] if self.lists else 0) + 4:
            return i + 1  # indented code: a line of its own
        if stripped.startswith(">"):
            return self.quote(i)
        if ATX.match(stripped) or REFERENCE.match(stripped):
            self.close()
            return i + 1
        if not at_start and SETEXT.match(stripped):
            self.close(keep=False)  # the paragraph is a heading's text
            return i + 1
        if RULE.match(stripped):
            self.close()
            return i + 1
        end = _html(stripped, at_start)
        if end is not None:
            self.close()
            self.mode = ("html", end) if end else None
            return i + 1
        if _table_starts(stripped, following):
            self.close()
            self.mode = ("table",)
            return i + 1
        if OPENER.match(stripped):
            self.close()
            self.pop_lists(indent)
            self.lists.append(indent + 4)
            return i + 1
        item = _item(stripped, indent, not at_start, bool(self.lists))
        if item is not None:
            return self.item(i, indent, item)
        if self.cur is not None and not self.broken:
            self.cur.append(idx)
            self.broken = hard_break(text)
            return i + 1
        if at_start:
            self.pop_lists(indent)
        self.open(idx, text)
        return i + 1

    def in_mode(self, text: str) -> bool:
        """Whether the line is read normally: False while a fence, an HTML block or a table
        holds it (the line it ends on included, for a fence or an HTML block)."""
        assert self.mode is not None
        kind = self.mode[0]
        if kind == "fence":
            if _closes(text, self.mode[1]):
                self.mode = None
            return False
        if kind == "html":
            end = self.mode[1]
            if end == "\n":
                if text.strip():
                    return False
                self.mode = None
                return True
            if end.lower() in text.lower():
                self.mode = None
            return False
        if not text.strip():
            self.mode = None
            return True
        stripped = text.lstrip()
        starts = (
            _fence(stripped)
            or ATX.match(stripped)
            or stripped.startswith(">")
            or RULE.match(stripped)
            or _html(stripped, False) is not None
            or _item(stripped, _indent(text), True, bool(self.lists))
        )
        if starts:
            self.mode = None
            return True
        return False

    def quote(self, i: int) -> int:
        """A run of blockquote lines, read as a container of its own."""
        self.close()
        j = i
        run = []
        while j < len(self.items):
            idx, text = self.items[j]
            if not text.strip() or not text.lstrip().startswith(">"):
                break
            run.append((idx, QUOTE.sub("", text, count=1)))
            j += 1
        _Reader(run, self.groups, self.inner).run()
        return j

    def item(self, i: int, indent: int, item: tuple[int, str]) -> int:
        idx, text = self.items[i]
        self.close()
        self.pop_lists(indent)
        column, content = item
        self.lists.append(column)
        content = content.lstrip()
        if not content.strip():
            return i + 1
        fence = _fence(content)
        if fence is not None:
            self.mode = ("fence", fence)
            return i + 1
        if (
            ATX.match(content)
            or RULE.match(content)
            or content.startswith((">", "|"))
            or _html(content, True) is not None
        ):
            return i + 1
        self.open(idx, text)
        return i + 1


def _front_matter_end(lines: list[str]) -> int:
    """The index of the first line after front matter, 0 when the text has none."""
    if not lines or lines[0].lstrip("﻿").rstrip() != "---":
        return 0
    for k in range(1, len(lines)):
        if lines[k].rstrip() in ("---", "..."):
            return k + 1
    return 0


def paragraphs(text: str) -> tuple[list[list[int]], dict[int, str]]:
    """(each group of two or more line indexes a renderer joins into one paragraph, every
    line's text with its blockquote prefixes removed)."""
    lines = text.split("\n")
    groups: list[list[int]] = []
    inner: dict[int, str] = {}
    start = _front_matter_end(lines)
    reader = _Reader(list(enumerate(lines)), groups, inner)
    reader.run(start)
    return sorted(groups), inner


def is_crlf(text: str) -> bool:
    return "\r\n" in text


def offending_lines(text: str) -> list[int]:
    """The 1-based first line of every paragraph written on more than one line; none for a
    CRLF text, which the fix never touches (`is_crlf` reports it)."""
    if is_crlf(text):
        return []
    return [g[0] + 1 for g in paragraphs(text)[0]]


def unwrap(text: str) -> str:
    """The text with every paragraph on one line: a group's first line keeps its indentation
    and prefixes, each line after it joins with one space, its own prefixes and surrounding
    whitespace dropped (a hard break at the group's end is kept). A CRLF text is returned as it
    is."""
    if is_crlf(text):
        return text
    lines = text.split("\n")
    groups, inner = paragraphs(text)
    if not groups:
        return text
    first = {g[0]: g for g in groups}
    out: list[str] = []
    i = 0
    while i < len(lines):
        g = first.get(i)
        if g is None:
            out.append(lines[i])
            i += 1
            continue
        parts = [lines[g[0]].rstrip()] + [inner[k].strip() for k in g[1:-1]]
        last = inner[g[-1]].lstrip()
        parts.append(last if hard_break(last) else last.rstrip())
        out.append(" ".join(parts))
        i = g[-1] + 1
    return "\n".join(out)


def _ignored(root: Path, files: list[Path]) -> set[Path]:
    """The files git ignores under `root`; none when git is missing, `root` is outside a
    repository, or `root` is itself ignored (it was asked for by name)."""
    try:
        here = subprocess.run(
            ["git", "-C", str(root), "check-ignore", "-q", "."], capture_output=True, check=False
        )
        if here.returncode != 1 or not files:
            return set()
        r = subprocess.run(
            ["git", "-C", str(root), "check-ignore", "--stdin", "-z"],
            input="\0".join(str(f.absolute()) for f in files).encode(),
            capture_output=True,
            check=False,
        )
    except OSError:
        return set()
    return {Path(p) for p in r.stdout.decode().split("\0") if p}


def _skipped(parts: tuple[str, ...]) -> bool:
    if parts and parts[-1] in SKIP_DIRS:
        return True
    return any(parts[-len(n) :] == n for n in SKIP_NESTED if len(parts) >= len(n))


def markdown_files(paths: Iterable[Path]) -> list[Path]:
    """Each path given as a file, and every `*.md` under each directory given, in order."""
    out: list[Path] = []
    for path in paths:
        path = Path(path)
        if path.is_file():
            out.append(path)
            continue
        found: list[Path] = []
        for here, dirs, files in os.walk(path):
            base = Path(here)
            dirs[:] = sorted(d for d in dirs if not _skipped((base / d).absolute().parts))
            found += [base / f for f in sorted(files) if f.endswith(".md")]
        ignored = _ignored(path, found)
        out += [f for f in found if f.absolute() not in ignored]
    return out


def _shown(path: Path) -> str:
    try:
        return path.absolute().relative_to(Path.cwd()).as_posix()
    except ValueError:
        return path.as_posix()


def findings(paths: Iterable[Path], shown=_shown) -> list[str]:
    """`path:line` for every wrapped paragraph, and a line for every CRLF file."""
    out = []
    for f in markdown_files(paths):
        try:
            text = f.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            out.append(f"{shown(f)}: not UTF-8, not read")
            continue
        if is_crlf(text):
            out.append(f"{shown(f)}: CRLF line endings, not read")
        else:
            out += [f"{shown(f)}:{n}" for n in offending_lines(text)]
    return out


def fix(paths: Iterable[Path]) -> tuple[list[str], list[str]]:
    """(the files rewritten, the CRLF files left as they are)."""
    changed, crlf = [], []
    for f in markdown_files(paths):
        try:
            text = f.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            continue  # the check reports it; the fix never guesses an encoding
        if is_crlf(text):
            crlf.append(_shown(f))
            continue
        new = unwrap(text)
        if new != text:
            f.write_bytes(new.encode("utf-8"))
            changed.append(_shown(f))
    return changed, crlf


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="report each wrapped paragraph")
    mode.add_argument("--fix", action="store_true", help="join each wrapped paragraph in place")
    p.add_argument("paths", nargs="+", type=Path, help="Markdown files or directories")
    ns = p.parse_args(argv)
    if ns.check:
        hits = findings(ns.paths)
        for h in hits:
            print(h)
        return 1 if hits else 0
    changed, crlf = fix(ns.paths)
    for c in changed:
        print(c)
    for c in crlf:
        print(f"{c}: CRLF line endings, left as they are")
    return 1 if crlf else 0


if __name__ == "__main__":
    sys.exit(main())
