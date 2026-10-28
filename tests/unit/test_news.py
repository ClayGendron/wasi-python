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
# The release-tier ledger: a pull request that moves a release-tier row appends its block; the
# date before the release moves the blocks under the version; the release's acceptance reads both

HEADER = "# The release-tier claims ledger.\n# Each block is appended by its pull request.\n"
BLOCK = (
    '[[claim]]\nspec = "140"\ngrows = ["tests/checks/test_v1_3_x.py::test_slow"]\n'
    'growth = "a pin moved"\n'
)
HISTORY = "# The release-tier claims, by release\n\nIntro.\n\n## 0.1.0\n\nMoved.\n\n```toml\n" + (
    '[[claim]]\nspec = "102"\nnew = ["tests/checks/test_v1_3_x.py::test_old"]\n```\n'
)


def _ledger_repo(tmp_path: Path, ledger: str, history: str) -> Path:
    (tmp_path / "src" / "wasi_python").mkdir(parents=True)
    (tmp_path / "src" / "wasi_python" / "__init__.py").write_text('__version__ = "0.1.1"\n')
    (tmp_path / "context").mkdir()
    (tmp_path / news.LEDGER).write_text(ledger)
    (tmp_path / news.LEDGER_HISTORY).write_text(history)
    return tmp_path


def test_the_release_reads_the_ledger_and_its_versions_moved_blocks(tmp_path: Path) -> None:
    moved = HISTORY.replace(
        "## 0.1.0",
        '## 0.1.1\n\nMoved.\n\n```toml\n[[claim]]\nspec = "139"\npasses = ["x"]\n'
        'fewer = "a group moved"\n```\n\n## 0.1.0',
    )
    repo = _ledger_repo(tmp_path, HEADER + "\n" + BLOCK, moved)
    claims = news.ledger_claims(repo)
    assert sorted(c.spec for c in claims) == ["139", "140"]  # not 0.1.0's
    assert (
        news.reason(claims, "grows", "tests/checks/test_v1_3_x.py::test_slow") == "140: a pin moved"
    )
    assert news.package_version(repo) == "0.1.1"


def test_date_moves_the_ledgers_blocks_under_the_version(tmp_path: Path) -> None:
    ledger, history = news.move_ledger(HEADER + "\n" + BLOCK, HISTORY, "0.1.1", "2026-10-26")
    assert ledger == HEADER
    assert history.index("## 0.1.1") < history.index("## 0.1.0")
    repo = _ledger_repo(tmp_path, ledger, history)
    assert [c.spec for c in news.ledger_claims(repo)] == ["140"]
    with pytest.raises(news.NewsError, match="already has a section for 0.1.1"):
        news.move_ledger(HEADER, history, "0.1.1", "2026-10-27")
    _, empty = news.move_ledger(HEADER, HISTORY, "0.1.1", "2026-10-26")
    assert "No block was in the ledger at the date." in empty.split("## 0.1.0")[0]


def test_a_broken_ledger_block_is_refused(tmp_path: Path) -> None:
    repo = _ledger_repo(tmp_path, HEADER + '[[claim]]\nspec = "140"\ngrows = ["x"]\n', HISTORY)
    with pytest.raises(news.NewsError, match="grows needs growth"):
        news.ledger_claims(repo)
