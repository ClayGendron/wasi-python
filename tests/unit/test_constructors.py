"""The constructor check compares the reviewed list whole (spec 023's build review, F2): one more
constructor with a name already reviewed, a missing one, or another order each fails; the real
list passes."""

from __future__ import annotations

import pytest

from harness import constructors

REVIEWED = list(constructors.REVIEWED_CONSTRUCTORS)


def test_the_reviewed_list_passes() -> None:
    assert constructors.list_errors(REVIEWED, REVIEWED) == []


@pytest.mark.parametrize("name", ["__cxx_global_var_init", "_GLOBAL__I_000100"])
def test_one_more_constructor_with_a_reviewed_name_fails(name) -> None:
    found = [*REVIEWED, name]
    assert constructors.list_errors(found, REVIEWED) == [
        f"{name}: a static constructor no review has read (1 more than reviewed)"
    ]


def test_a_new_name_and_a_missing_one_fail() -> None:
    found = [*REVIEWED[:-1], "_GLOBAL__sub_I_ft2font_wrapper.cpp"]
    assert constructors.list_errors(found, REVIEWED) == [
        "_GLOBAL__sub_I_ft2font_wrapper.cpp: a static constructor no review has read",
        f"{REVIEWED[-1]}: reviewed, but no longer linked",
    ]


def test_another_order_fails() -> None:
    found = [REVIEWED[1], REVIEWED[0], *REVIEWED[2:]]
    (error,) = constructors.list_errors(found, REVIEWED)
    assert error.startswith("the constructors run in another order than reviewed")
