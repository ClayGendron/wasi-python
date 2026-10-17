"""The limits are checked (spec 013): `run` refuses a limit of the wrong type with TypeError and
one out of range with ValueError, before any work, and passes on plain values."""

from __future__ import annotations

import math
from fractions import Fraction

import pytest

from wasi_python import runner

TOP = 2**63 - 1


class Index:
    """An integer that is not an int, as a numpy integer is: it has __index__."""

    def __init__(self, value: int) -> None:
        self.value = value

    def __index__(self) -> int:
        return self.value


def check(**given):
    limits = {"fuel": None, "deadline_s": None, "memory_bytes": None, "output_bytes": None}
    return runner._check_limits(**{**limits, **given})


@pytest.mark.parametrize("name", ["fuel", "memory_bytes", "output_bytes"])
def test_an_integer_limit_takes_0_to_2_63_minus_1(name) -> None:
    assert check(**{name: 0})[name] == 0
    assert check(**{name: TOP})[name] == TOP
    for wrong in (-1, TOP + 1, 2**64, 2**64 - 1):
        with pytest.raises(ValueError, match=name):
            check(**{name: wrong})


@pytest.mark.parametrize("name", ["fuel", "memory_bytes", "output_bytes"])
def test_an_integer_limit_refuses_other_types(name) -> None:
    for wrong in (True, False, 1.5, 1.0, "1", b"1", Fraction(1)):
        with pytest.raises(TypeError, match=name):
            check(**{name: wrong})


@pytest.mark.parametrize("name", ["fuel", "memory_bytes", "output_bytes"])
def test_an_integer_limit_passes_on_a_plain_int(name) -> None:
    value = check(**{name: Index(7)})[name]
    assert (type(value), value) == (int, 7)


def test_a_deadline_is_a_positive_finite_real() -> None:
    assert check(deadline_s=60)["deadline_s"] == 60.0
    assert type(check(deadline_s=Fraction(1, 2))["deadline_s"]) is float
    assert check(deadline_s=1e-300)["deadline_s"] == 1e-300  # rounds up to one tick, as before
    for wrong in (0, 0.0, -1, -1e-9, math.nan, math.inf, -math.inf, 1.7e308, 10**400):
        with pytest.raises(ValueError, match="deadline_s"):
            check(deadline_s=wrong)
    top = 4.611686018427387e16  # the largest float whose ticks stay below NO_DEADLINE
    assert check(deadline_s=top)["deadline_s"] == top
    with pytest.raises(ValueError, match="deadline_s"):
        check(deadline_s=math.nextafter(top, math.inf))


def test_a_huge_integer_is_named_in_the_message() -> None:
    with pytest.raises(ValueError, match="fuel .* an integer of 16610 bits"):
        check(fuel=10**5000)
    with pytest.raises(ValueError, match="deadline_s .* an integer of 16610 bits"):
        check(deadline_s=10**5000)


def test_a_deadline_refuses_other_types() -> None:
    for wrong in (True, False, "1", b"1", 1j, Index(1)):
        with pytest.raises(TypeError, match="deadline_s"):
            check(deadline_s=wrong)


def test_none_means_no_limit() -> None:
    assert check() == {"fuel": None, "deadline_s": None, "memory_bytes": None, "output_bytes": None}


def test_the_defaults_pass_and_a_bad_default_is_refused() -> None:
    d = runner.DEFAULTS
    check(deadline_s=d.deadline_s, memory_bytes=d.memory_bytes, output_bytes=d.output_bytes)
    with pytest.raises(ValueError, match="memory_bytes"):
        runner.Defaults(memory_bytes=-1, deadline_s=60.0, output_bytes=1)
    with pytest.raises(TypeError, match="deadline_s"):
        runner.Defaults(memory_bytes=1, deadline_s=True, output_bytes=1)
