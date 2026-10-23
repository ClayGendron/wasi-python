"""Markdown paragraphs on one line each: what the fix joins, what it never joins, and the check
and the command line that report and rewrite files."""

from __future__ import annotations

import shutil
import subprocess

import pytest

from harness import wrap

# name -> (the text, the text with every paragraph on one line)
CASES = {
    "a paragraph": (
        "One paragraph written\nover three\nlines.\n",
        "One paragraph written over three lines.\n",
    ),
    "surrounding whitespace is trimmed": (
        "First line \n   second line\t\n",
        "First line second line\n",
    ),
    "two paragraphs stay two": (
        "One\ntwo.\n\nThree\nfour.\n",
        "One two.\n\nThree four.\n",
    ),
    "a one-line file": ("Just one line.\n", "Just one line.\n"),
    "an empty file": ("", ""),
    "no trailing newline": ("one\ntwo", "one two"),
    "two trailing newlines": ("one\ntwo\n\n", "one two\n\n"),
    "a list item's continuation": (
        "- **Status:** landed on main, after\n  its review.\n- **Kind:** parallel-safe\n",
        "- **Status:** landed on main, after its review.\n- **Kind:** parallel-safe\n",
    ),
    "nested items": (
        "- outer item\n  continues\n  - inner item\n    continues\n  - second inner\n- second\n",
        "- outer item continues\n  - inner item continues\n  - second inner\n- second\n",
    ),
    "a lazy continuation joins its item": (
        "1. a numbered item that\nwraps without indent\n2. the next\n",
        "1. a numbered item that wraps without indent\n2. the next\n",
    ),
    "a later paragraph in an item": (
        "- item\n\n  its second paragraph\n  wraps here\n",
        "- item\n\n  its second paragraph wraps here\n",
    ),
    "a year and a dot mid-paragraph is text": (
        "The owner decided on\n2026. The next sentence\ncontinues.\n",
        "The owner decided on 2026. The next sentence continues.\n",
    ),
    "a date and a dot mid-paragraph is text": (
        "It landed\n2026-10-22. The next\nsentence.\n",
        "It landed 2026-10-22. The next sentence.\n",
    ),
    "a 1. mid-paragraph starts a list": (
        "Steps:\n1. first\n2. second\n",
        "Steps:\n1. first\n2. second\n",
    ),
    "a number after an item is an item": (
        "1. first item\n   continues\n3) third item\n   continues\n",
        "1. first item continues\n3) third item continues\n",
    ),
    "a bullet mid-paragraph starts a list": (
        "Text before\n- an item\n  continues\n",
        "Text before\n- an item continues\n",
    ),
    "a blockquote paragraph": (
        "> One quoted\n> paragraph\n>\n> and another\n>  here\n",
        "> One quoted paragraph\n>\n> and another here\n",
    ),
    "a blockquote with a nested list": (
        "> Intro\n> text:\n> - item one\n>   continues\n> - item two\n",
        "> Intro text:\n> - item one continues\n> - item two\n",
    ),
    "a nested blockquote": ("> > deep\n> > quote\n", "> > deep quote\n"),
    "a quote after a paragraph is its own block": (
        "Before\n> quoted\n> text\nafter\nthat\n",
        "Before\n> quoted text\nafter that\n",
    ),
    "a backtick fence": (
        "Before\n```python\nx = 1\ny = 2\n```\nafter\nit\n",
        "Before\n```python\nx = 1\ny = 2\n```\nafter it\n",
    ),
    "a tilde fence and its closing fence": (
        "~~~~\na\nb\n~~~\nstill\ncode\n~~~~\nc\nd\n",
        "~~~~\na\nb\n~~~\nstill\ncode\n~~~~\nc d\n",
    ),
    "an indented fence": ("    ```\n    a\n    b\n    ```\n", "    ```\n    a\n    b\n    ```\n"),
    "a fence inside a list item": (
        "- run\n  this:\n  ```\n  one\n  two\n  ```\n  then\n  that\n",
        "- run this:\n  ```\n  one\n  two\n  ```\n  then that\n",
    ),
    "a fence opening an item": (
        "1. ```bash\n   one\n   two\n   ```\n",
        "1. ```bash\n   one\n   two\n   ```\n",
    ),
    "indented code after a blank line": (
        "Text\nhere\n\n    code one\n    code two\n\nmore\ntext\n",
        "Text here\n\n    code one\n    code two\n\nmore text\n",
    ),
    "tab-indented code": ("\tcode one\n\tcode two\n", "\tcode one\n\tcode two\n"),
    "four spaces mid-paragraph continue it": ("Text\n    more text\n", "Text more text\n"),
    "indented code inside an item": (
        "- item\n\n      code one\n      code two\n",
        "- item\n\n      code one\n      code two\n",
    ),
    "a table": (
        "Before\nit\n\n| a | b |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n\nafter\nit\n",
        "Before it\n\n| a | b |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n\nafter it\n",
    ),
    "a table without outer pipes": (
        "Lead\na | b\n--|--\n1 | 2\nrow\n",
        "Lead\na | b\n--|--\n1 | 2\nrow\n",
    ),
    "a table inside a list": (
        "- item\n  text:\n\n  | a | b |\n  |---|---|\n  | 1 | 2 |\n- next\n  item\n",
        "- item text:\n\n  | a | b |\n  |---|---|\n  | 1 | 2 |\n- next item\n",
    ),
    "a pipe in prose is not a table": (
        "Use `a | b` to\njoin them.\n",
        "Use `a | b` to join them.\n",
    ),
    "headings": (
        "# Title\nText\nhere\n## Section\nmore\ntext\n",
        "# Title\nText here\n## Section\nmore text\n",
    ),
    "a setext heading": ("A heading\nin two lines\n===\n", "A heading\nin two lines\n===\n"),
    "a setext heading with dashes": ("Heading\ntext\n---\n", "Heading\ntext\n---\n"),
    "a horizontal rule": ("one\ntwo\n\n***\nthree\nfour\n", "one two\n\n***\nthree four\n"),
    "an HTML block": (
        '<p align="center">\n  <picture>\n    <img src="x">\n  </picture>\n</p>\n\nText\nhere\n',
        '<p align="center">\n  <picture>\n    <img src="x">\n  </picture>\n</p>\n\nText here\n',
    ),
    "an HTML comment over lines": (
        "<!-- a comment\n\nover lines\n-->\nText\nhere\n",
        "<!-- a comment\n\nover lines\n-->\nText here\n",
    ),
    "a block tag interrupts a paragraph": (
        "Text\n<div>\ninside\n</div>\n",
        "Text\n<div>\ninside\n</div>\n",
    ),
    "an inline tag mid-paragraph is text": (
        "Press\n<kbd>Ctrl</kbd> and\nC.\n",
        "Press <kbd>Ctrl</kbd> and C.\n",
    ),
    "an autolink starts a paragraph": (
        "<https://example.org> is\nthe site.\n",
        "<https://example.org> is the site.\n",
    ),
    "front matter": (
        "---\ntitle: A page\ntags: one\n---\nText\nhere\n",
        "---\ntitle: A page\ntags: one\n---\nText here\n",
    ),
    "a hard break of two spaces": (
        "one  \ntwo\nthree\n",
        "one  \ntwo three\n",
    ),
    "a hard break of a backslash": ("one\\\ntwo\nthree\n", "one\\\ntwo three\n"),
    "an escaped backslash is no break": ("one\\\\\ntwo\n", "one\\\\ two\n"),
    "a hard break ends a group": ("one\ntwo  \nthree\n", "one two  \nthree\n"),
    "link reference definitions": (
        "[one]: https://example.org/one\n[two]: https://example.org/two\n",
        "[one]: https://example.org/one\n[two]: https://example.org/two\n",
    ),
    "an admonition's body": (
        '!!! note "Dated"\n    These figures were\n    recorded once.\n\nAfter\nit.\n',
        '!!! note "Dated"\n    These figures were recorded once.\n\nAfter it.\n',
    ),
    "a tab's body": (
        '=== "Python"\n\n    Text in\n    the tab.\n',
        '=== "Python"\n\n    Text in the tab.\n',
    ),
}


@pytest.mark.parametrize("case", CASES)
def test_the_fix_joins_exactly_one_paragraph_per_line(case) -> None:
    text, want = CASES[case]
    assert wrap.unwrap(text) == want


@pytest.mark.parametrize("case", CASES)
def test_the_fix_is_idempotent(case) -> None:
    once = wrap.unwrap(CASES[case][0])
    assert wrap.unwrap(once) == once
    assert wrap.offending_lines(once) == []


def test_the_check_names_each_paragraphs_first_line() -> None:
    text = "# T\n\nOne\ntwo\n\n- item\n  more\n- single\n\n> q\n> r\n"
    assert wrap.offending_lines(text) == [3, 6, 10]
    assert wrap.offending_lines(wrap.unwrap(text)) == []


def test_a_crlf_text_is_never_changed() -> None:
    text = "one\r\ntwo\r\n"
    assert wrap.is_crlf(text)
    assert wrap.unwrap(text) == text
    assert wrap.offending_lines(text) == []


def test_files_are_checked_and_fixed_in_place(work) -> None:
    wrapped = work / "wrapped.md"
    wrapped.write_bytes(b"one\ntwo")
    clean = work / "clean.md"
    clean.write_bytes(b"one line\n")
    crlf = work / "crlf.md"
    crlf.write_bytes(b"one\r\ntwo\r\n")
    (work / "notes.txt").write_bytes(b"not\nmarkdown\n")
    shown = {wrapped: "wrapped.md", clean: "clean.md", crlf: "crlf.md"}.__getitem__
    assert wrap.findings([work], shown) == [
        "crlf.md: CRLF line endings, not read",
        "wrapped.md:1",
    ]
    before = clean.stat().st_mtime_ns
    changed, left = wrap.fix([work])
    assert [c.rsplit("/", 1)[-1] for c in changed] == ["wrapped.md"]
    assert [c.rsplit("/", 1)[-1] for c in left] == ["crlf.md"]
    assert wrapped.read_bytes() == b"one two"
    assert crlf.read_bytes() == b"one\r\ntwo\r\n"
    assert clean.stat().st_mtime_ns == before
    assert wrap.fix([work]) == ([], left)


def test_a_search_skips_the_trees_that_are_not_ours(work) -> None:
    for d in ("docs", "build", "downloads", ".claude", "test_app", "site", "context/prior_art"):
        (work / d).mkdir(parents=True)
        (work / d / "page.md").write_text("one\ntwo\n")
    (work / "context" / "kept.md").write_text("one\ntwo\n")
    found = sorted(p.relative_to(work).as_posix() for p in wrap.markdown_files([work]))
    assert found == ["context/kept.md", "docs/page.md"]
    # a file named on the command line is read wherever it is
    assert wrap.markdown_files([work / "build" / "page.md"]) == [work / "build" / "page.md"]


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_a_search_skips_what_git_ignores(work) -> None:
    subprocess.run(["git", "init", "-q", str(work)], check=True)
    (work / ".gitignore").write_text("ignored/\n")
    for d in ("ignored", "kept"):
        (work / d).mkdir()
        (work / d / "page.md").write_text("one\ntwo\n")
    found = sorted(p.relative_to(work).as_posix() for p in wrap.markdown_files([work]))
    assert found == ["kept/page.md"]
    # a directory that is itself ignored was asked for by name, so it is read
    assert wrap.markdown_files([work / "ignored"]) == [work / "ignored" / "page.md"]


def test_the_command_line_checks_then_fixes(work, monkeypatch, capsys) -> None:
    monkeypatch.chdir(work)
    (work / "a.md").write_text("one\ntwo\n\nthree\nfour\n")
    assert wrap.main(["--check", "a.md"]) == 1
    assert capsys.readouterr().out.splitlines() == ["a.md:1", "a.md:4"]
    assert wrap.main(["--fix", "a.md"]) == 0
    assert capsys.readouterr().out.splitlines() == ["a.md"]
    assert (work / "a.md").read_text() == "one two\n\nthree four\n"
    assert wrap.main(["--check", "a.md"]) == 0
    assert wrap.main(["--fix", "a.md"]) == 0
    assert capsys.readouterr().out == ""
