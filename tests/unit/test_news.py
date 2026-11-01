"""News files: one per change, its release-note entries, its package rows and its claim block,
read by the release's changelog assembly, the gather's growth listing and the acceptance from CI."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from harness import news, paths

GOOD = """# 999: a change

## Changelog

### New

- **A thing you can do now.** It is new. [Install](https://claygendron.github.io/wasi-python/get-started/install/)

### Fixed

- **A thing that broke works again.** It is fixed. [Sessions](https://claygendron.github.io/wasi-python/how-to/sessions/#know-how-a-session-ends)

## Package rows

| numpy | 2.5.2 | Built in. |

## Claims

```toml
[[claim]]
spec = "999"
new = ["tests/checks/test_rules.py::test_new"]
grows = ["tests/checks/test_v1_4_x.py::*"]
growth = "the tool table is larger"
passes = ["tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[g1]"]
fewer = "two tests moved to the release tier"
units = 3

[claim.judge]
"tests/harness/plugin.py" = "it reads the record"

[claim.moved]
"tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[g2]" = "slow"
```
"""


NEW_ENTRY = next(line for line in GOOD.splitlines() if line.startswith("- **A thing you can"))
FIXED_ENTRY = next(line for line in GOOD.splitlines() if line.startswith("- **A thing that"))
# Forty words of fact and a link whose text is twenty-five words: sixty-nine words in all.
LONG_LINK_TEXT = (
    "- **A long link.** "
    + " ".join(["word"] * 40)
    + " ["
    + " ".join(["page"] * 25)
    + "](https://claygendron.github.io/wasi-python/get-started/install/)"
)
SIXTY_ONE = (
    "- **A long one.** "
    + " ".join(["word"] * 56)
    + " [Install](https://claygendron.github.io/wasi-python/get-started/install/)"
)


def test_a_news_file_reads_its_three_sections() -> None:
    n = news.parse("999-a-change.md", GOOD)
    assert n.name == "999-a-change" and n.spec == "999"
    assert n.changelog == {"New": [NEW_ENTRY], "Fixed": [FIXED_ENTRY]}
    assert n.rows == ["| numpy | 2.5.2 | Built in. |"]
    (c,) = n.claims
    assert c.spec == "999" and c.units == 3 and c.growth == "the tool table is larger"
    assert c.judge == {"tests/harness/plugin.py": "it reads the record"}
    assert c.moved == {"tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[g2]": "slow"}


def test_no_package_rows_and_an_empty_claim_are_allowed() -> None:
    text = GOOD.split("## Package rows")[0] + (
        '## Package rows\n\nNone.\n\n## Claims\n\n```toml\n[[claim]]\nspec = "999"\n```\n'
    )
    n = news.parse("999-a-change.md", text)
    assert n.rows == [] and n.claims[0].grows == [] and n.claims[0].judge == {}


BROKEN = {
    "a name that is not NNN-slug": ("999_a_change.md", GOOD, "NNN-<slug>"),
    "a title of another number": ("998-a-change.md", GOOD, "998"),
    "no changelog": ("999-a-change.md", GOOD.replace("## Changelog", "## Notes"), "Notes"),
    "a heading the changelog does not use": (
        "999-a-change.md",
        GOOD.replace("### Fixed", "### Improved"),
        "Improved",
    ),
    "a heading with no line": (
        "999-a-change.md",
        GOOD.replace(FIXED_ENTRY + "\n", ""),
        "Fixed",
    ),
    "prose under a heading": (
        "999-a-change.md",
        GOOD.replace(NEW_ENTRY, "It moved."),
        "a line",
    ),
    "a row of two cells": (
        "999-a-change.md",
        GOOD.replace("| numpy | 2.5.2 | Built in. |", "| numpy | 2.5.2 |"),
        "three cells",
    ),
    "no claim block": (
        "999-a-change.md",
        GOOD.split("```toml")[0],
        "toml",
    ),
    "a claim block that is not TOML": (
        "999-a-change.md",
        GOOD.replace('spec = "999"', "spec = "),
        "TOML",
    ),
    "a key the shape does not name": (
        "999-a-change.md",
        GOOD.replace("units = 3", "units = 3\nwhy = 1"),
        "why",
    ),
    "grows with no growth": (
        "999-a-change.md",
        GOOD.replace('growth = "the tool table is larger"\n', ""),
        "growth",
    ),
    "a judge file with no reason": (
        "999-a-change.md",
        GOOD.replace('= "it reads the record"', '= ""'),
        "judge",
    ),
    "a claim for another specification": (
        "999-a-change.md",
        GOOD.replace('spec = "999"', 'spec = "998"'),
        "998",
    ),
    "a heading of the old four": (
        "999-a-change.md",
        GOOD.replace("### Fixed", "### Changed"),
        "New, Faster, Security, Fixed, Upgrading, For contributors",
    ),
    "an entry with no bold lead": (
        "999-a-change.md",
        GOOD.replace("- **A thing that broke works again.**", "- A thing that broke works again."),
        "bold lead",
    ),
    "a lead of thirteen words": (
        "999-a-change.md",
        GOOD.replace("**A thing that broke works again.**", "**" + " ".join(["word"] * 13) + ".**"),
        "lead of 13 words",
    ),
    "an entry of sixty-one words": (
        "999-a-change.md",
        GOOD.replace(FIXED_ENTRY, SIXTY_ONE),
        "61 words",
    ),
    "an entry past sixty words only through its link's text": (
        "999-a-change.md",
        GOOD.replace(FIXED_ENTRY, LONG_LINK_TEXT),
        "69 words",
    ),
    "an entry that does not end with a link to the site": (
        "999-a-change.md",
        GOOD.replace(
            "[Sessions](https://claygendron.github.io/wasi-python/how-to/sessions/#know-how-a-session-ends)",
            "[Elsewhere](https://example.org/)",
        ),
        "end with a link",
    ),
}


@pytest.mark.parametrize("case", BROKEN)
def test_each_broken_news_file_is_refused_with_its_reason(case) -> None:
    name, text, words = BROKEN[case]
    with pytest.raises(news.NewsError, match=words.replace("[", r"\[").replace("*", r"\*")):
        news.parse(name, text)


def test_sixty_words_is_the_bound() -> None:
    """The word count drops every link's address; sixty words pass and sixty-one do not."""
    sixty = SIXTY_ONE.replace("word word ", "word ", 1)
    assert news.entry_errors(sixty) == []
    assert news.entry_errors(SIXTY_ONE) == ["the entry is 61 words; at most 60"]


def test_the_site_is_the_documentations_own_address() -> None:
    mkdocs = (paths.REPO / "mkdocs.yml").read_text(encoding="utf-8")
    site_url = re.search(r"^site_url:\s*(\S+)\s*$", mkdocs, re.M)
    assert site_url is not None and news.SITE == site_url[1]


def test_each_site_link_leads_to_a_page(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    (docs / "how-to").mkdir(parents=True)
    (docs / "reference" / "deep").mkdir(parents=True)
    (docs / "index.md").write_text("# Home\n")
    (docs / "how-to" / "sessions.md").write_text("# Sessions\n")
    (docs / "reference" / "deep" / "index.md").write_text("# Deep\n")
    entries = [
        FIXED_ENTRY,
        f"- **Home.** It is home. [Home]({news.SITE})",
        f"- **Deep.** It is deep. [Deep]({news.SITE}reference/deep/)",
        f"- **Gone.** It moved away. [Gone]({news.SITE}reference/gone/#where)",
        "- **Elsewhere.** It is elsewhere. [Advisory](https://example.org/x)",
    ]
    assert news.link_errors(entries, docs) == [
        f"{news.SITE}reference/gone/#where: no page docs/reference/gone.md or "
        "docs/reference/gone/index.md"
    ]


@pytest.mark.parametrize(
    "text, want",
    [("0.1.2a1", True), ("0.1.2", True), ("0.2.0", True), ("1.0.0rc1", True),
     ("0.1.1", False), ("0.1.0a7", False), ("0.1.0", False), ("", False)],
)  # fmt: skip
def test_which_versions_carry_the_readers_notes(text, want) -> None:
    assert news.is_reader_version(text) is want


LOG = """# Changelog

The header.

## 0.1.2 — unreleased

A summary.

## 0.1.2a1 — 2026-11-01

Another.

## 0.1.1 — 2026-10-27

### Changed

- an old line
"""


def test_the_reader_sections_are_the_header_and_the_versions_above_0_1_1() -> None:
    got = [(s.version, s.date, s.body.strip(), s.line) for s in news.reader_sections(LOG)]
    assert got == [
        ("", "", "# Changelog\n\nThe header.", 1),
        ("0.1.2", "unreleased", "A summary.", 6),
        ("0.1.2a1", "2026-11-01", "Another.", 10),
    ]
    only_old = "# Changelog\n\n## 0.1.0a1 — unreleased\n\n- first\n"
    assert [s.version for s in news.reader_sections(only_old)] == [""]


def test_a_folder_holds_news_files_and_its_readme(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# the folder\n")
    (tmp_path / "999-a-change.md").write_text(GOOD)
    (tmp_path / "001-first.md").write_text(GOOD.replace("999", "001"))
    assert [n.name for n in news.folder(tmp_path)] == ["001-first", "999-a-change"]
    assert news.folder(tmp_path / "missing") == []


@pytest.mark.parametrize(
    "rel, want",
    [
        ("context/changes/138-pull-requests-into-dev.md", True),
        ("context/changes/README.md", False),
        ("context/changes/notes.txt", False),
        ("context/changes/sub/138-x.md", False),
        ("context/reviews/138-x-pr-2026-10-25.md", False),
    ],
)
def test_which_paths_are_news_files(rel, want) -> None:
    assert news.is_news_path(rel) is want


def test_a_claim_names_a_check_by_id_by_file_or_by_prefix() -> None:
    node = "tests/checks/test_v1_4_x.py::test_tools[a]"
    assert news.names(node, node)
    assert news.names("tests/checks/test_v1_4_x.py", node)
    assert news.names("tests/checks/test_v1_4_*", node)
    assert not news.names("tests/checks/test_v1_4_x.py::test_tools[b]", node)
    assert not news.names("tests/checks/test_v1_4", node)


def test_the_reason_a_claim_gives_for_each_kind_of_row() -> None:
    claims = news.parse("999-a-change.md", GOOD).claims
    tools = "tests/checks/test_v1_4_x.py::test_tools"
    group = "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[g1]"
    moved = "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[g2]"
    assert news.reason(claims, "grows", tools) == "999: the tool table is larger"
    assert news.reason(claims, "passes", group) == "999: two tests moved to the release tier"
    assert news.reason(claims, "moved", moved) == "999: slow"
    assert news.reason(claims, "judge", "tests/harness/plugin.py") == "999: it reads the record"
    assert news.reason(claims, "grows", group) is None
    assert news.reason(claims, "judge", "tests/harness/gather.py") is None


# ---------------------------------------------------------------------------------------------
# The release ledger: a folder of one file per pull request, named after its news file; the date
# before the release moves each file under the version; the release's acceptance reads both

BLOCK = (
    '[[claim]]\nspec = "140"\ngrows = ["tests/checks/test_v1_3_x.py::test_slow"]\n'
    'growth = "a pin moved"\n'
)
HISTORY = "# The release claims, by release\n\nIntro.\n\n## 0.1.0\n\nMoved.\n\n```toml\n" + (
    '[[claim]]\nspec = "102"\nnew = ["tests/checks/test_v1_3_x.py::test_old"]\n```\n'
)
FILE = "140-a-pin-moved.toml"


def _ledger_repo(tmp_path: Path, files: dict[str, str], history: str) -> Path:
    (tmp_path / "src" / "wasi_python").mkdir(parents=True)
    (tmp_path / "src" / "wasi_python" / "__init__.py").write_text('__version__ = "0.1.1"\n')
    (tmp_path / news.LEDGER).mkdir(parents=True)
    (tmp_path / news.LEDGER / "README.md").write_text("# The ledger\n")
    for name, text in files.items():
        (tmp_path / news.LEDGER / name).write_text(text)
    (tmp_path / news.LEDGER_HISTORY).write_text(history)
    return tmp_path


def test_the_release_reads_the_ledger_and_its_versions_moved_blocks(tmp_path: Path) -> None:
    moved = HISTORY.replace(
        "## 0.1.0",
        '## 0.1.1\n\nMoved.\n\n```toml\n[[claim]]\nspec = "139"\npasses = ["x"]\n'
        'fewer = "a group moved"\n```\n\n## 0.1.0',
    )
    repo = _ledger_repo(tmp_path, {FILE: BLOCK}, moved)
    claims = news.ledger_claims(repo)
    assert [c.spec for c in claims] == ["139", "140"]  # not 0.1.0's
    assert (
        news.reason(claims, "grows", "tests/checks/test_v1_3_x.py::test_slow") == "140: a pin moved"
    )
    assert news.package_version(repo) == "0.1.1"


def test_the_ledgers_files_are_read_in_file_name_order(tmp_path: Path) -> None:
    """One file per pull request, read by name, whatever order they were written in; the
    folder's README and anything not .toml are not ledger files."""
    later = '[[claim]]\nspec = "171"\ngrows = ["x"]\ngrowth = "the zip grew"\n'
    repo = _ledger_repo(tmp_path, {"171-later.toml": later, FILE: BLOCK}, "# history\n")
    (repo / news.LEDGER / "notes.txt").write_text("not a ledger file\n")
    assert list(news.ledger_files(repo / news.LEDGER)) == [FILE, "171-later.toml"]
    assert [c.spec for c in news.ledger_claims(repo)] == ["140", "171"]
    assert news.ledger_files(tmp_path / "absent") == {}


def test_a_ledger_file_is_named_after_its_news_file_and_holds_its_own_blocks() -> None:
    assert [c.spec for c in news.ledger_file_claims(FILE, BLOCK)] == ["140"]
    with pytest.raises(news.NewsError, match="named NNN-<slug>.toml"):
        news.ledger_file_claims("release-claims.toml", BLOCK)
    with pytest.raises(news.NewsError, match="not the file's 141"):
        news.ledger_file_claims("141-another.toml", BLOCK)
    with pytest.raises(news.NewsError, match="at least one"):
        news.ledger_file_claims(FILE, "# nothing yet\n")


def test_date_moves_the_ledgers_files_under_the_version(tmp_path: Path) -> None:
    later = '[[claim]]\nspec = "171"\ngrows = ["x"]\ngrowth = "the zip grew"\n'
    history = news.move_ledger(
        {"171-later.toml": later, FILE: BLOCK}, HISTORY, "0.1.1", "2026-10-26"
    )
    assert history.index("## 0.1.1") < history.index("## 0.1.0")
    assert history.index(f"`{FILE}`:") < history.index("`171-later.toml`:")
    repo = _ledger_repo(tmp_path, {}, history)
    assert [c.spec for c in news.ledger_claims(repo)] == ["140", "171"]
    with pytest.raises(news.NewsError, match="already has a section for 0.1.1"):
        news.move_ledger({}, history, "0.1.1", "2026-10-27")
    empty = news.move_ledger({}, HISTORY, "0.1.1", "2026-10-26")
    assert "No block was in the ledger at the date." in empty.split("## 0.1.0")[0]
    with pytest.raises(news.NewsError, match="named NNN-<slug>.toml"):
        news.move_ledger({"stray.toml": BLOCK}, HISTORY, "0.1.1", "2026-10-26")


def test_a_broken_ledger_block_is_refused(tmp_path: Path) -> None:
    repo = _ledger_repo(tmp_path, {FILE: '[[claim]]\nspec = "140"\ngrows = ["x"]\n'}, HISTORY)
    with pytest.raises(news.NewsError, match="grows needs growth"):
        news.ledger_claims(repo)


def test_a_removed_news_files_claims_are_read_whatever_its_changelog(tmp_path: Path) -> None:
    """The release reads back the news files bump removed, whose changelog was assembled and
    checked then; an older file's changelog may be in a shape since retired, so only its claims
    are read, and a broken claim block is still refused."""
    old = (
        "# 120: an older change\n\n## Changelog\n\n### Changed\n\n- It changed.\n\n"
        '## README rows\n\nNone.\n\n## Claims\n\n```toml\n[[claim]]\nspec = "120"\n'
        'grows = ["x"]\ngrowth = "it grew"\n```\n'
    )
    assert [c.growth for c in news.claims_only("120-an-older-change.md", old)] == ["it grew"]
    assert news.claims_only("121-none.md", "# 121: none\n\n## Changelog\n") == []
    with pytest.raises(news.NewsError, match="growth"):
        news.claims_only("120-broken.md", old.replace('growth = "it grew"\n', ""))
    with pytest.raises(news.NewsError, match="not the file's 123"):
        news.claims_only("123-other.md", old)


def test_the_files_date_moved_under_a_version_are_read_back() -> None:
    moved = news.move_ledger({FILE: BLOCK}, HISTORY, "0.1.1", "2026-10-30")
    assert news.moved_files(moved, "0.1.1") == {FILE: BLOCK.strip()}
    assert news.moved_files(moved, "0.1.0") == {}  # moved as one block, before a file each
    assert news.moved_files(moved, "0.0.9") == {}
    empty = news.move_ledger({}, HISTORY, "0.1.1", "2026-10-30")
    assert news.moved_files(empty, "0.1.1") == {}


# The five blocks the single ledger held when it became a folder, cut to the keys that matter
# here, in the order they were appended. Two name rows a third names too, so the order decides
# which reason a row is quoted with, and nothing else.
OLD_ORDER = (
    ("166-the-pins-move.toml", '[[claim]]\nspec = "166"\npasses = ["S::t[pypdf-r]"]\n'
     'grows = ["S::t[numpy-slow-*", "S::t[scipy-*"]\ngrowth = "the pins move"\n'),
    ("165-docx-and-pptx.toml", '[[claim]]\nspec = "165"\nnew = ["S::t[python-docx-r]"]\n'
     'grows = ["S::*"]\ngrowth = "two packages join the zip"\n'),
    ("159-the-runs-take-shape.toml", '[[claim]]\nspec = "159"\nnew = ["S::trap[sympy-P]"]\n'
     'retired = ["S::t[sympy-r-2]"]\ngrows = ["S::t[sympy-*"]\ngrowth = "sympy grew"\n'),
    ("167-pdfplumber-and-xarray.toml", '[[claim]]\nspec = "167"\nnew = ["S::t[xarray-r-plot]"]\n'
     'grows = ["S::*"]\ngrowth = "three packages join the zip"\n'
     '[claim.judge]\n"tests/known_gaps.toml" = "a gap"\n'),
    ("171-the-packages-a-set-carries.toml", '[[claim]]\nspec = "171"\ngrows = ["S::*"]\n'
     'growth = "the zip grows its top_level.txt"\n'),
)  # fmt: skip
ROWS = ("S::t[pypdf-r]", "S::t[numpy-slow-a]", "S::t[scipy-1]", "S::t[sympy-r-1]",
        "S::t[sympy-r-2]", "S::t[python-docx-r]", "S::trap[sympy-P]", "S::t[other]",
        "tests/known_gaps.toml", "tests/upstream/numpy.toml", "T::t[x]")  # fmt: skip
KINDS = ("new", "retired", "changed", "passes", "grows", "judge", "moved")


def _old_ledger(tmp_path: Path, blocks) -> list[news.Claim]:
    """What the single ledger file gave the release: the version's moved blocks, then the file's
    blocks read as one, in the order they were appended."""
    old = tmp_path / "old"
    repo = _ledger_repo(old, {}, HISTORY)
    text = "# The release claims ledger.\n\n" + "\n".join(b for _, b in blocks)
    return news.ledger_claims(repo) + news.ledger_tables("context/release-claims.toml", text)


def test_the_folder_gives_the_release_the_claims_the_single_file_gave(tmp_path: Path) -> None:
    """The same blocks give the same claims, whether in the single file or a file each. Read in
    file-name order the two lists are equal, entry for entry, so every reason quoted is the same;
    against the order they were appended, the claims are the same set, and every row is claimed
    or unclaimed alike under every kind: what the acceptance and the release's reconciliation
    decide does not move. Only a row two blocks name may be quoted with the other's reason."""
    new = news.ledger_claims(_ledger_repo(tmp_path / "new", dict(OLD_ORDER), HISTORY))
    assert new == _old_ledger(tmp_path / "by-name", sorted(OLD_ORDER))
    old = _old_ledger(tmp_path / "appended", OLD_ORDER)
    assert sorted(new, key=lambda c: c.spec) == sorted(old, key=lambda c: c.spec)
    for kind in KINDS:
        for row in ROWS:
            assert (news.reason(new, kind, row) is None) == (news.reason(old, kind, row) is None)
    assert news.reason(old, "grows", "S::t[sympy-r-1]") == "165: two packages join the zip"
    assert news.reason(new, "grows", "S::t[sympy-r-1]") == "159: sympy grew"
