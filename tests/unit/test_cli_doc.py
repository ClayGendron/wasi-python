"""The command's reference page: rendered from its parser, one block, and no drift either way."""

from __future__ import annotations

import argparse

import pytest

from harness import cli_doc


def small() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tool run", usage="tool run [OPTIONS]", description="Runs.")
    p.add_argument("--env", action="append", default=[], metavar="KEY=VALUE")
    p.add_argument("--fuel", type=int, metavar="N", default=argparse.SUPPRESS)
    p.add_argument("--fast", action="store_true", help="skip the slow part")
    group = p.add_mutually_exclusive_group()
    group.add_argument("--root", metavar="HOST", help="the guest's /")
    group.add_argument("--no-root", action="store_true", help="no / at all")
    return p


DESCRIBED = {"--env": "a variable for the guest", "--fuel": "a cap on instructions"}


def test_a_parser_renders_as_one_table() -> None:
    text = cli_doc.render(small(), DESCRIBED)
    assert text.splitlines() == [
        "### `tool run`",
        "",
        "Runs.",
        "",
        "```",
        "tool run [OPTIONS]",
        "```",
        "",
        "| option | value | default | description |",
        "|---|---|---|---|",
        "| `--env` | `KEY=VALUE` | none | a variable for the guest (repeatable) |",
        "| `--fuel` | `N` | `run`'s default | a cap on instructions |",
        "| `--fast` |  | off | skip the slow part |",
        "| `--root` | `HOST` | none | the guest's / |",
        "| `--no-root` |  | off | no / at all |",
        "",
        "At most one of `--root` and `--no-root`.",
    ]


def test_an_option_with_no_description_fails_the_render() -> None:
    with pytest.raises(ValueError, match="--fuel: no description"):
        cli_doc.render(small(), {"--env": "a variable for the guest"})


def test_a_description_the_parser_no_longer_has_fails_the_render() -> None:
    with pytest.raises(ValueError, match="--gone: described, but the parser has no such option"):
        cli_doc.render(small(), {**DESCRIBED, "--gone": "removed"})


def test_an_option_described_twice_fails_the_render() -> None:
    """Once the parser carries an option's help, its entry in the mapping goes."""
    with pytest.raises(ValueError, match="--fast: described twice"):
        cli_doc.render(small(), {**DESCRIBED, "--fast": "again"})


def test_a_page_holds_exactly_one_block() -> None:
    one = f"# Page\n\n{cli_doc.BEGIN}\nbody\n{cli_doc.END}\nafter\n"
    assert cli_doc.page_block(one) == (1, "body")
    assert cli_doc.page_block("# Page\n") == (0, None)
    assert cli_doc.page_block(one + one)[0] == 2
    assert cli_doc.page_block(f"```\n{cli_doc.BEGIN}\nx\n{cli_doc.END}\n```\n") == (0, None)
    assert cli_doc.replace_block(one, "new") == (
        f"# Page\n\n{cli_doc.BEGIN}\n\nnew\n\n{cli_doc.END}\nafter\n"
    )


def test_every_option_of_the_command_is_described() -> None:
    text = cli_doc.render(cli_doc.live_parser())
    for option in ("--env", "--deadline-s", "--grant-writable", "--no-root"):
        assert f"| `{option}` |" in text
    assert "At most one of `--root`, `--private-root` and `--no-root`." in text
