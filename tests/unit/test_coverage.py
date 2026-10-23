"""The coverage measurer's reading of a run and the README's Codecov badge, without a run."""

from __future__ import annotations

import pytest

from harness import coverage

GOOD = f"# wasi-python\n\n{coverage.BADGE_TAG}\n"


@pytest.mark.parametrize("summary", ["1 failed, 899 passed", "899 passed, 2 errors", "1 error"])
def test_a_red_run_is_refused(summary: str) -> None:
    assert coverage.summary_names_failures(summary)


def test_a_green_summary_with_skips_and_xfails_is_not_red() -> None:
    assert not coverage.summary_names_failures("900 passed, 3 skipped, 2 xfailed, 1 deselected")


@pytest.mark.parametrize(
    ("line", "summary"),
    [
        ("900 passed, 3 skipped in 228.41s (0:03:48)", "900 passed, 3 skipped"),
        ("========= 1 failed, 899 passed in 230.00s =========", "1 failed, 899 passed"),
        ("12 passed in 0.50s", "12 passed"),
    ],
)
def test_summary_line_is_read_without_its_clock(line: str, summary: str) -> None:
    m = coverage.SUMMARY.match(line)
    assert m and m[1] == summary


def test_a_progress_line_is_not_a_summary() -> None:
    assert coverage.SUMMARY.match("....F.... [ 4%]") is None


def test_the_summary_is_the_last_one_in_the_log() -> None:
    log = "....F [ 50%]\n1 failed, 3 passed in 1.00s\nscoreboard\n4 passed in 2.00s\nratchet\n"
    assert coverage.summary_of(log) == "4 passed"
    assert coverage.summary_of("no summary here\n") == ""


def test_the_codecov_badge_is_found() -> None:
    assert coverage.badge_errors(GOOD) == []


def test_no_badge_is_an_error() -> None:
    assert coverage.badge_errors("# wasi-python\n") == [
        f"README.md: 0 Codecov badges, not one: {coverage.BADGE_TAG}"
    ]


def test_two_badges_are_an_error() -> None:
    assert coverage.badge_errors(GOOD + coverage.BADGE_TAG)[0].startswith("README.md: 2 Codecov")


def test_another_repositorys_badge_is_an_error() -> None:
    other = GOOD.replace("ClayGendron/wasi_python", "someone/else")
    assert coverage.badge_errors(other) == [
        f"README.md: the coverage badge is not {coverage.BADGE_TAG}"
    ]


def test_the_badge_links_to_the_repositorys_codecov_page() -> None:
    assert coverage.BADGE_TAG.startswith(f'<a href="{coverage.CODECOV}">')
    assert coverage.BADGE.findall(coverage.BADGE_TAG) == [f"{coverage.CODECOV}/graph/badge.svg"]


def test_a_red_ratchet_does_not_hide_the_summary() -> None:
    """The ratchet's RED line is the acceptance's; the numbers come from the tests that ran."""
    log = "RED: 1 accepted check(s) absent (retire them with --retire)\n3130 passed in 900.00s\n"
    assert coverage.summary_of(log) == "3130 passed"
    assert not coverage.summary_names_failures(coverage.summary_of(log))
