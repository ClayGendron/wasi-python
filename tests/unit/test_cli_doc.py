"""The command's reference page: rendered from its parser, one block, and no drift either way."""

from __future__ import annotations

import argparse

import pytest

from harness import cli_doc


def small() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tool run", usage="tool run [OPTIONS]", description="Runs.")
    p.add_argument(
        "--env", action="append", default=[], metavar="KEY=VALUE", help="a variable for the guest"
    )
    p.add_argument(
        "--fuel", type=int, metavar="N", default=argparse.SUPPRESS, help="a cap on instructions"
    )
    p.add_argument("--fast", action="store_true", help="skip the slow part")
    group = p.add_mutually_exclusive_group()
    group.add_argument("--root", metavar="HOST", help="the guest's /")
    group.add_argument("--no-root", action="store_true", help="no / at all")
    return p


def test_a_parser_renders_as_one_table() -> None:
    text = cli_doc.render(small())
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


def test_an_option_with_no_help_fails_the_render() -> None:
    """The page's sentence for an option is its help and nothing else, so an option the parser
    leaves bare cannot reach the page undescribed."""
    parser = small()
    next(a for a in parser._actions if "--fuel" in a.option_strings).help = None
    with pytest.raises(ValueError, match="--fuel: no help"):
        cli_doc.render(parser)


def test_a_page_holds_exactly_one_block() -> None:
    one = f"# Page\n\n{cli_doc.BEGIN}\nbody\n{cli_doc.END}\nafter\n"
    assert cli_doc.page_block(one) == (1, "body")
    assert cli_doc.page_block("# Page\n") == (0, None)
    assert cli_doc.page_block(one + one)[0] == 2
    assert cli_doc.page_block(f"```\n{cli_doc.BEGIN}\nx\n{cli_doc.END}\n```\n") == (0, None)
    assert cli_doc.replace_block(one, "new") == (
        f"# Page\n\n{cli_doc.BEGIN}\n\nnew\n\n{cli_doc.END}\nafter\n"
    )


def test_the_render_has_no_colour_whatever_the_terminal(monkeypatch) -> None:
    """argparse colours its usage line when asked to by the environment or a terminal; the page
    is the same text everywhere, so the render turns colour off."""
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.delenv("NO_COLOR", raising=False)
    text = cli_doc.live_block()
    assert "\x1b" not in text
    assert cli_doc.page_block(cli_doc.PAGE.read_text(encoding="utf-8")) == (1, text)


def test_every_option_of_the_command_is_described() -> None:
    text = cli_doc.render(cli_doc.live_parser())
    for option in ("--env", "--deadline-s", "--grant-writable", "--no-root"):
        assert f"| `{option}` |" in text
    assert "At most one of `--root`, `--private-root` and `--no-root`." in text


def test_every_option_of_the_command_carries_its_help() -> None:
    """Each command's `--help` describes every option, from the same text the page renders."""
    bare = [
        a.option_strings[-1]
        for parser in cli_doc.live_parsers()
        for a in parser._actions
        if a.option_strings and a.dest != "help" and a.help in (None, argparse.SUPPRESS)
    ]
    assert bare == [], f"options with no help=: {bare}"


def test_the_page_has_a_section_per_command() -> None:
    """`wasi-python packages` is on the page too, after `run`, with its one option."""
    text = cli_doc.live_block()
    assert text.index("### `wasi-python run`") < text.index("### `wasi-python packages`")
    assert "wasi-python packages [--json]" in text and "| `--json` |  | off |" in text
