"""lint: the writing conventions, run by the quick job's lint step and by
`uv run pytest tests/lint`.

These hold how the documents and the code's prose are written: the specifications' shape, the one-
line paragraphs, the labels of an executed write-up, the README's badge, the rule that code
names no document of the knowledge tree, and the same rule for the release's notes. They gate a
change but are not goal checks: no area, no ratchet, no acceptance, and the fast tier does not
collect them (`norecursedirs`), so a document being written never colours the product's verdict.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from harness import budget, paths, scan

SPECS = paths.CONTEXT / "specifications"
RESEARCH = paths.CONTEXT / "research"


def test_specifications_have_their_header_and_sections() -> None:
    errors = [e for s in sorted(SPECS.glob("*.md")) for e in scan.spec_shape_errors(s)]
    assert not errors, scan.report(errors)


def test_a_long_specification_is_named_never_failed(capsys) -> None:
    """A specification says its decisions in about 1,500 words and its landing notes in ten lines.
    One past 2,000 words, or whose landing notes run past 15 lines, is named as a warning, an
    annotation and a line of the job's summary on a run, a plain line elsewhere; it never fails,
    since a document already written is not rewritten to fit."""
    named = os.environ.get("GITHUB_STEP_SUMMARY")
    summary = Path(named) if named else None
    lines = budget.length_warnings(sorted(SPECS.glob("[0-9][0-9][0-9]-*.md")), summary)
    with capsys.disabled():
        for line in lines:
            print("\n" + (line if summary else line.removeprefix(budget.LENGTH_WARNING)), end="")
        if lines:
            print()


def test_specifications_have_no_open_question() -> None:
    docs = sorted(SPECS.glob("*.md")) + [paths.README, paths.REPO / "AGENTS.md"]
    hits = [h for d in docs for h in scan.open_question_hits(d)]
    assert not hits, scan.report(hits)


# (path, the exact phrase, why it stays). Each entry admits that phrase in that file's comments
# and docstrings; an entry that admits nothing fails, so the tuple only ever shrinks.
JUDGE_FILE = (
    "the known gaps and the upstream suites' allowances change only by a judge change of their "
    "own, which clears these comments then; a cleanup of comments never edits them"
)
GUEST_INPUT = (
    "a source the guest runs: its bytes are the guest's input, and a shorter docstring moved the "
    "regex job's fuel past the ratchet's tolerance, so it changes with a judge change that "
    "re-measures its fuel"
)
SHAPE_SHOWN = (
    "the src/ citation check documents its regexes by showing the shapes they match and refuse; "
    "the token is the rule's own vocabulary, not a citation of a document"
)
CONTEXT_CITATION_ALLOWED: tuple[tuple[str, str, str], ...] = (
    ("tests/lint/test_writing_conventions.py", "C6", SHAPE_SHOWN),
    ("tests/lint/test_writing_conventions.py", "C99", SHAPE_SHOWN),
    ("tests/lint/test_writing_conventions.py", "D3", SHAPE_SHOWN),
    ("tests/lint/test_writing_conventions.py", "F1", SHAPE_SHOWN),
    ("tests/lint/test_writing_conventions.py", "F3", SHAPE_SHOWN),
    ("tests/lint/test_writing_conventions.py", "F4.2", SHAPE_SHOWN),
    ("tests/lint/test_writing_conventions.py", "L1", SHAPE_SHOWN),
    ("tests/lint/test_writing_conventions.py", "N12", SHAPE_SHOWN),
    ("tests/lint/test_writing_conventions.py", "S3", SHAPE_SHOWN),
    ("tests/lint/test_writing_conventions.py", "memo", SHAPE_SHOWN),
    ("tests/jobs/callbacks.py", "spec 051", GUEST_INPUT),
    ("tests/jobs/compress.py", "spec 007", GUEST_INPUT),
    ("tests/jobs/excel.py", "spec 039", GUEST_INPUT),
    ("tests/jobs/files_from_the_zip.py", "041's", GUEST_INPUT),
    ("tests/jobs/files_from_the_zip.py", "spec 041", GUEST_INPUT),
    ("tests/jobs/lxml_xml.py", "spec 046", GUEST_INPUT),
    ("tests/jobs/machine_learning.py", "037's", GUEST_INPUT),
    ("tests/jobs/machine_learning.py", "spec 044", GUEST_INPUT),
    ("tests/jobs/markup.py", "spec 039", GUEST_INPUT),
    ("tests/jobs/markup.py", "spec 046", GUEST_INPUT),
    ("tests/jobs/modelling.py", "spec 037", GUEST_INPUT),
    ("tests/jobs/modelling.py", "spec 039", GUEST_INPUT),
    ("tests/jobs/pandas_tz.py", "spec 035", GUEST_INPUT),
    ("tests/jobs/pdf_reports.py", "spec 042", GUEST_INPUT),
    ("tests/jobs/pdf.py", "spec 039", GUEST_INPUT),
    ("tests/jobs/plot_callbacks.py", "023's", GUEST_INPUT),
    ("tests/jobs/plot_callbacks.py", "spec 023", GUEST_INPUT),
    ("tests/jobs/plot_contour.py", "spec 043", GUEST_INPUT),
    ("tests/jobs/plot_line.py", "spec 023", GUEST_INPUT),
    ("tests/jobs/regex_features.py", "spec 047", GUEST_INPUT),
    ("tests/jobs/scipy_edges.py", "spec 038", GUEST_INPUT),
    ("tests/jobs/scipy_lapack.py", "spec 037", GUEST_INPUT),
    ("tests/jobs/scipy_numeric.py", "spec 037", GUEST_INPUT),
    ("tests/jobs/scipy_solvers.py", "spec 037", GUEST_INPUT),
    ("tests/jobs/sqlite.py", "spec 007", GUEST_INPUT),
    ("tests/jobs/statistical_plots.py", "037's", GUEST_INPUT),
    ("tests/jobs/statistical_plots.py", "spec 037", GUEST_INPUT),
    ("tests/jobs/statistical_plots.py", "spec 042", GUEST_INPUT),
    ("tests/jobs/symbolic.py", "spec 037", GUEST_INPUT),
    ("tests/jobs/symbolic.py", "spec 039", GUEST_INPUT),
    ("tests/jobs/text_formats.py", "spec 039", GUEST_INPUT),
    ("tests/jobs/utilities.py", "spec 039", GUEST_INPUT),
    ("tests/known_gaps.toml", "C1", JUDGE_FILE),
    ("tests/known_gaps.toml", "Spec 066", JUDGE_FILE),
    ("tests/known_gaps.toml", "spec 002", JUDGE_FILE),
    ("tests/known_gaps.toml", "spec 050", JUDGE_FILE),
    ("tests/known_gaps.toml", "spec 065", JUDGE_FILE),
    ("tests/upstream/drive.py", "spec 050", GUEST_INPUT),
    ("tests/upstream/kiwisolver.toml", "spec 066", JUDGE_FILE),
    ("tests/upstream/lxml.toml", "spec 066", JUDGE_FILE),
    ("tests/upstream/matplotlib.toml", "spec 066", JUDGE_FILE),
    ("tests/upstream/package_drive.py", "066's", GUEST_INPUT),
    ("tests/upstream/package_drive.py", "build review", GUEST_INPUT),
    ("tests/upstream/package_drive.py", "review, M2", GUEST_INPUT),
    ("tests/upstream/package_drive.py", "spec 050", GUEST_INPUT),
    ("tests/upstream/package_drive.py", "spec 066", GUEST_INPUT),
    ("tests/upstream/packages.toml", "context/roadmap", JUDGE_FILE),
    ("tests/upstream/packages.toml", "spec 037", JUDGE_FILE),
    ("tests/upstream/packages.toml", "spec 063", JUDGE_FILE),
    ("tests/upstream/packages.toml", "spec 065", JUDGE_FILE),
    ("tests/upstream/packages.toml", "spec 066", JUDGE_FILE),
    ("tests/upstream/pillow.toml", "review, H2", JUDGE_FILE),
    ("tests/upstream/pillow.toml", "spec 066", JUDGE_FILE),
    ("tests/upstream/regex.toml", "spec 066", JUDGE_FILE),
    ("tests/upstream/regrtest_drive.py", "C1", GUEST_INPUT),
    ("tests/upstream/regrtest_drive.py", "confirmation's", GUEST_INPUT),
    ("tests/upstream/regrtest_drive.py", "spec 065", GUEST_INPUT),
)


def test_code_outside_src_names_no_context_document() -> None:
    """Code speaks for itself: no comment or docstring under `tests/`, `scripts/`, `release/` or
    the workflows names a specification, the constitution's sections, a research write-up, a
    review, an owner's numbered question, a path under the knowledge tree or a review finding's
    identifier. The reason is written in words, and the documents cite the code, not
    the other way round. The judge's reads of those documents are code, not prose, so they are
    not held here."""
    allowed = {(path, phrase) for path, phrase, _ in CONTEXT_CITATION_ALLOWED}
    used: set[tuple[str, str]] = set()
    hits = []
    for p in scan.context_citation_files(paths.REPO):
        where = scan.rel(p, paths.REPO)
        for line, rule, phrase in scan.context_citation_hits(p):
            if (where, phrase) in allowed:
                used.add((where, phrase))
            else:
                hits.append(f"{where}:{line}: {rule}: {phrase}")
    hits += [f"{path}: allowed '{phrase}' is no longer there" for path, phrase in allowed - used]
    assert not hits, scan.report(hits)


# The string rule leaves the judge's allowance files to a judge change of their own: a known
# gap's `closes_with` names its closer by number in the judge's own format, and their reasons
# are reworded with the comments of those files, by the change that clears them.
STRING_RULE_LATER = ("tests/known_gaps.toml", "tests/upstream/*.toml")
# (path, the exact phrase, why it stays), as for comments: each entry admits that phrase in that
# file's strings; an entry that admits nothing fails, so the tuple only ever shrinks.
RULE_NAME = "the name a rule table gives the form it refuses, the rule's own vocabulary"
FIXTURE = (
    "a scanner's input in a unit row: the text is what the scanner reads, so rewording it would "
    "change the row"
)
GAP_DATA = (
    "a known gap's closes_with names the specification that closes it by number, the format the "
    "judge parses"
)
GUEST_FUEL = (
    "a guest program in a check that records fuel: its bytes are the guest's input, so it changes "
    "with the change that re-measures the guest's fuel"
)
STRING_CITATION_ALLOWED: tuple[tuple[str, str, str], ...] = (
    ("tests/lint/test_writing_conventions.py", "memo", RULE_NAME),
    ("tests/harness/scan.py", "memo", RULE_NAME),
    ("tests/unit/test_scan.py", "constitution §", FIXTURE),
    ("tests/unit/test_scan.py", "memo", FIXTURE),
    ("tests/unit/test_scan.py", "review 2026-10-19", FIXTURE),
    ("tests/unit/test_scan.py", "question 95", FIXTURE),
    ("tests/unit/test_scan.py", "review's F4.2", FIXTURE),
    ("tests/unit/test_scan.py", "build review", FIXTURE),
    ("tests/unit/test_scan.py", "Confirmation's M5", FIXTURE),
    ("tests/unit/test_scan.py", "Confirmation's", FIXTURE),
    ("tests/unit/test_scan.py", "spec 131", FIXTURE),
    ("tests/unit/test_scan.py", "spec 144", FIXTURE),
    ("tests/unit/test_scan.py", "spec 999", FIXTURE),
    ("tests/unit/test_landing_lane.py", "memo", FIXTURE),
    ("tests/unit/test_shards.py", "spec 001", GAP_DATA),
    ("tests/unit/test_shards.py", "spec 065", GAP_DATA),
    ("tests/unit/test_shards.py", "spec 099", GAP_DATA),
    ("tests/checks/test_v1_3_data_stack.py", "review 033", GUEST_FUEL),
)


def test_no_string_names_a_context_document() -> None:
    """Strings speak for themselves: no string literal under `tests/`, `scripts/`, `release/`,
    the workflows or `src/`, nor in `pyproject.toml`, names a specification, the constitution's
    sections, a research write-up, a dated, numbered or named review, an owner's numbered
    question or a finding a review names. A message, a help text, a title, a step's name and a
    program a check holds give their reasons in words. A path and a bare label are data in a
    string, so they are not held here."""
    allowed = {(path, phrase) for path, phrase, _ in STRING_CITATION_ALLOWED}
    used: set[tuple[str, str]] = set()
    hits = []
    for p in scan.string_citation_files(paths.REPO, STRING_RULE_LATER):
        where = scan.rel(p, paths.REPO)
        for line, rule, phrase in scan.string_citation_hits(p):
            if (where, phrase) in allowed:
                used.add((where, phrase))
            else:
                hits.append(f"{where}:{line}: {rule}: {phrase}")
    hits += [f"{path}: allowed '{phrase}' is no longer there" for path, phrase in allowed - used]
    assert not hits, scan.report(hits)


def test_release_notes_name_no_context_document() -> None:
    """The release's notes are a public page, on GitHub, on the site and behind PyPI's link, so
    they meet the public pages' rule: every news file's entries, the changelog's header and its
    sections written for the reader name no specification, constitution section, write-up,
    review, numbered question, path under the knowledge tree or finding, by the same regexes the
    README and the site are read with, and no reserved embedder name. The sections published
    before the reader's notes began are not read."""
    hits = scan.release_note_hits(paths.REPO)
    assert not hits, scan.report(hits)


def test_markdown_paragraphs_are_one_line_each() -> None:
    """A Markdown paragraph is written on one line: a renderer joins a paragraph's lines with
    spaces anyway, so a hard wrap at a column changes nothing a reader sees while every edit
    re-flows its neighbours and every diff is noisier. The root's Markdown files, the public
    pages and every document under the knowledge tree are held, the prior-art clones excepted
    (they are not ours); code, tables, headings and HTML are never joined, and a CRLF file is
    reported. `uv run python tests/harness/wrap.py --fix PATH` joins what this finds."""
    from harness import wrap

    roots = [*sorted(paths.REPO.glob("*.md")), paths.REPO / "docs", paths.CONTEXT]
    hits = wrap.findings(roots, lambda p: scan.rel(p, paths.REPO))
    assert not hits, scan.report(hits)


def test_readme_carries_the_codecov_badge() -> None:
    """The README carries one coverage badge, this repository's on Codecov, which the release
    workflow feeds from the Linux judge legs its plan names, run under coverage.py. The number
    lives at Codecov, so no file in the tree can drift from it."""
    from harness import coverage

    errors = coverage.badge_errors(paths.README.read_text(encoding="utf-8"))
    assert not errors, scan.report(errors)


def test_executed_memos_label_their_claims() -> None:
    errors = [e for m in sorted(RESEARCH.glob("*.md")) for e in scan.memo_label_errors(m)]
    assert not errors, scan.report(errors)


# Code speaks for itself: a code file names no specification, memo, review, finding ID or
# `context/` path; its comments and docstrings give the reason in words, and the number lives in
# the document that cites the file. `src/` is held here, over every comment token and every
# docstring (through `tokenize`, so an identifier or a literal never trips it). Eight regexes:
# a specification number in any form, a decision number with or without one (case-sensitive:
# every citation writes "Decision 8", and "a decision" in prose stays free), the constitution,
# the memo, any form of the word "review", a numbered question, a `context/` path, and a one-
# or two-digit finding ID (`F3`, `N12`, `F4.2`, `S3`, `D3`, `C6`, `L1`; the look-arounds keep
# `F401` in a `noqa` and a word like `MD5` out). The regexes refuse more than citations: `C99`,
# `L1` as a cache level, `F1` as a key, and the words "memo" and "review" in any use; a comment
# that needs such a word writes around it. Where words will not do, CITATION_ALLOWED carries the
# exact token with a one-line reason; a citation of a `context/` document is never added.
CITATION_KINDS = {
    "specification number": re.compile(r"\bspec(?:ification)?s?\s+\d{3}\b", re.I),
    "decision number": re.compile(r"\bDecisions?\s+\d+\b"),
    "constitution": re.compile(r"\bconstitution\b", re.I),
    "memo": re.compile(r"\bmemo\b", re.I),
    "review": re.compile(r"\breviews?\b|\bre-review|\bconfirmation's\b", re.I),
    "question": re.compile(r"\bquestion\s+\d+\b", re.I),
    "context path": re.compile(r"\bcontext/"),
    "finding ID": re.compile(r"(?<![A-Za-z0-9_])[CDFLNS]\d{1,2}(?:\.\d+)?(?![A-Za-z0-9_])"),
}
CITATION_ALLOWED: tuple[tuple[str, str], ...] = ()  # (exact token, why words would not do)


def _prose(path: Path) -> list[tuple[int, str]]:
    """(line, text) for every comment token and every line of every docstring: a string that is
    the first token of a module, a class or a function body, or stands alone as a statement."""
    import io
    import tokenize

    out: list[tuple[int, str]] = []
    last: int | None = None
    opening = (None, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.NL)
    for tok in tokenize.generate_tokens(io.StringIO(path.read_text(encoding="utf-8")).readline):
        if tok.type == tokenize.COMMENT:
            out.append((tok.start[0], tok.string))
        elif tok.type == tokenize.STRING and last in opening:
            out += [(tok.start[0] + i, line) for i, line in enumerate(tok.string.splitlines())]
        if tok.type not in (tokenize.NL, tokenize.COMMENT):
            last = tok.type
    return out


def _citation_hits(root: Path) -> list[str]:
    allowed = {token for token, _ in CITATION_ALLOWED}
    hits = []
    for path in sorted(p for p in scan.files_under(root, ".") if p.suffix == ".py"):
        for line, text in _prose(path):
            for kind, pattern in CITATION_KINDS.items():
                for m in pattern.finditer(text):
                    if m.group(0) not in allowed:
                        hits.append(f"{scan.rel(path, paths.REPO)}:{line}: {kind} {m.group(0)!r}")
    return hits


def test_src_names_no_context_document() -> None:
    """No specification number, decision number, constitution, memo, review, numbered question,
    `context/` path or finding ID in any comment or docstring of any `.py` under `src/`."""
    hits = _citation_hits(paths.REPO / "src")
    assert not hits, scan.report(hits)


# The documentation site's address, as `mkdocs.yml` names it. A pointer from the code or from a
# page read outside the site is a full URL, since the wheel carries no `docs/` folder.
SITE = "https://claygendron.github.io/wasi-python/"
SITE_LINK = re.compile(re.escape(SITE) + r"([A-Za-z0-9_./-]*)")


def _src_text(path: Path) -> list[tuple[int, str]]:
    """(line, text) of every comment and every string literal's text in one Python file."""
    import io
    import tokenize

    kinds = {tokenize.COMMENT, tokenize.STRING}
    kinds |= {getattr(tokenize, "FSTRING_MIDDLE", tokenize.STRING)}
    kinds |= {getattr(tokenize, "TSTRING_MIDDLE", tokenize.STRING)}
    source = io.StringIO(path.read_text(encoding="utf-8")).readline
    return [(t.start[0], t.string) for t in tokenize.generate_tokens(source) if t.type in kinds]


def _page_of(link: str) -> Path:
    """The Markdown file under `docs/` that a path on the site is built from; a full stop that
    ends the sentence the link closes is not part of the path."""
    rel = link.split("#", 1)[0].rstrip(".").strip("/")
    if not rel:
        return paths.REPO / "docs" / "index.md"
    page = paths.REPO / "docs" / f"{rel}.md"
    return page if page.is_file() else paths.REPO / "docs" / rel / "index.md"


def test_src_points_at_the_site_not_the_readme() -> None:
    """The runner's comments, docstrings and messages point a reader at the documentation site,
    not at a section of the README, which is short and keeps no reference sections; and every
    link to the site from `src/`, the README or the security policy names a page the site has, so
    a page that moves or goes turns this red before a reader meets the dead link."""
    site_url = re.search(r"^site_url:\s*(\S+)", (paths.REPO / "mkdocs.yml").read_text(), re.M)
    hits = [] if site_url and site_url[1] == SITE else [f"mkdocs.yml: site_url is not {SITE}"]
    sources = sorted(p for p in scan.files_under(paths.REPO / "src", ".") if p.suffix == ".py")
    texts = [(p, line, text) for p in sources for line, text in _src_text(p)]
    for page in (paths.README, paths.REPO / "SECURITY.md"):
        texts += [(page, n, text) for n, text in enumerate(page.read_text().splitlines(), 1)]
    for path, line, text in texts:
        name = scan.rel(path, paths.REPO)
        if path.suffix == ".py":
            for m in re.finditer("README", text):
                at = line + text[: m.start()].count("\n")
                hits.append(f"{name}:{at}: names the README; name the site's page instead")
        for m in SITE_LINK.finditer(text):
            if not _page_of(m[1]).is_file():
                at = line + text[: m.start()].count("\n")
                hits.append(f"{name}:{at}: {m[0]} is no page under docs/")
    assert not hits, scan.report(hits)


def test_a_site_link_that_ends_a_sentence_names_its_page() -> None:
    """A link written at the end of a sentence carries the full stop into the match; the page it
    names is the one before the stop."""
    building = paths.REPO / "docs" / "contributing" / "building.md"
    assert _page_of("contributing/building/.") == building
    assert _page_of("contributing/building/#build-the-artifacts") == building
