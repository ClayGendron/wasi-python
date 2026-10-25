"""The inputs are checked: `run` refuses an argv, env or stdin that the guest would see
differently, with TypeError for a wrong type and ValueError for a wrong value, naming the argument
but never quoting a value, and passes on plain values."""

from __future__ import annotations

import array
import pathlib
from types import MappingProxyType

import pytest

from wasi_python import _limits

SECRET = "s3cr3t-value"


def check(argv=("-c", "pass"), env=None, stdin=None):
    return _limits._check_inputs(argv, env, stdin)


class Sneaky(str):
    """A str subclass whose own __str__ and encode lie: the runner must pass on the real text."""

    def __str__(self) -> str:
        return "evil"

    def encode(self, *args, **kwargs):
        return b"evil"


@pytest.mark.parametrize(
    "argv",
    [("-c", "pass"), ["-c", "pass"], (x for x in ["-c", "pass"]), {"-c": 1, "pass": 2}.keys()],
    ids=["tuple", "list", "generator", "dict_keys"],
)
def test_argv_is_any_iterable_of_str(argv) -> None:
    assert check(argv=argv).argv == ("-c", "pass")


def test_argv_items_are_passed_on_as_plain_str() -> None:
    (item,) = check(argv=[Sneaky("ok")]).argv
    assert (type(item), item) == (str, "ok")


def test_an_empty_argv_is_allowed() -> None:
    assert check(argv=[]).argv == ()


@pytest.mark.parametrize(
    "argv",
    ["-c", b"-c", bytearray(b"-c"), 5, ["-c", 5], ["-c", b"x"], [pathlib.PurePosixPath("/x")]],
    ids=["str", "bytes", "bytearray", "int", "an int item", "a bytes item", "a path item"],
)
def test_argv_of_another_type_is_refused(argv) -> None:
    with pytest.raises(TypeError, match="argv"):
        check(argv=argv)


@pytest.mark.parametrize("item", ["a\0b", "\udcff"], ids=["NUL", "lone surrogate"])
def test_an_argv_item_the_guest_would_see_differently_is_refused(item) -> None:
    with pytest.raises(ValueError, match=r"argv\[1\]"):
        check(argv=["-c", item])


@pytest.mark.parametrize(
    "env",
    [{"K": "v"}, MappingProxyType({"K": "v"}), {"KÉ": "v"}, {"1K": "v"}, {"A B": "v"}],
    ids=["dict", "mapping proxy", "non-ascii key", "leading digit", "space"],
)
def test_env_takes_a_mapping_of_odd_but_valid_keys(env) -> None:
    assert check(env=env).env == dict(env)


def test_env_is_passed_on_as_a_dict_of_plain_str() -> None:
    env = check(env={Sneaky("K"): Sneaky("v")}).env
    assert [(type(k), k, type(v), v) for k, v in env.items()] == [(str, "K", str, "v")]


@pytest.mark.parametrize(
    "env",
    [[("K", "v")], {"K": 5}, {5: "v"}, {"K": b"v"}],
    ids=["a list of pairs", "an int value", "an int key", "a bytes value"],
)
def test_env_of_another_type_is_refused(env) -> None:
    with pytest.raises(TypeError, match="env"):
        check(env=env)


@pytest.mark.parametrize(
    ("env", "words"),
    [
        ({"K": "a\0" + SECRET}, "embedded null byte"),
        ({"HOME\0x": "/shared"}, "embedded null byte"),
        ({"K=X": SECRET}, "illegal environment variable name"),
        ({"=K": SECRET}, "illegal environment variable name"),
        ({"": SECRET}, "illegal environment variable name"),
        ({"K": "\udcff" + SECRET}, "UTF-8"),
        ({"\udcff": SECRET}, "UTF-8"),
        ({"_PYTHON_SYSCONFIGDATA_PATH": SECRET}, "private build settings"),
        ({"_PYTHON_PROJECT_BASE": SECRET}, "private build settings"),
    ],
    ids=[
        "NUL in a value",
        "NUL in a key",
        "= in a key",
        "leading =",
        "empty key",
        "surrogate in a value",
        "surrogate in a key",
        "the sysconfig data folder",
        "a private build setting that loads no code",
    ],
)
def test_an_env_entry_the_guest_would_see_differently_is_refused(env, words) -> None:
    with pytest.raises(ValueError, match=words) as refused:
        check(env=env)
    assert SECRET not in str(refused.value), "the message quotes a value"


def test_a_refused_key_is_never_quoted_and_a_long_key_is_cut() -> None:
    with pytest.raises(ValueError) as refused:
        check(env={"TOKEN=" + SECRET: "v"})
    assert SECRET not in str(refused.value)
    with pytest.raises(ValueError) as refused:
        check(env={"K" * 100_000: "a\0b"})
    assert len(str(refused.value)) < 100


@pytest.mark.parametrize(
    "stdin",
    [b"hi", bytearray(b"hi"), memoryview(b"hi"), memoryview(b"h_i_")[::2], array.array("b", b"hi")],
    ids=["bytes", "bytearray", "memoryview", "non-contiguous", "array"],
)
def test_stdin_is_any_bytes_like_object(stdin) -> None:
    passed = check(stdin=stdin).stdin
    assert (type(passed), passed) == (bytes, b"hi")


def test_exact_bytes_stdin_is_not_copied() -> None:
    data = b"x" * 1000
    assert check(stdin=data).stdin is data


@pytest.mark.parametrize("stdin", ["", "hi", 0, False, [], 5], ids=repr)
def test_stdin_that_is_not_bytes_like_is_refused(stdin) -> None:
    with pytest.raises(TypeError, match="stdin"):
        check(stdin=stdin)


def test_none_is_no_env_and_no_stdin() -> None:
    assert check() == _limits._Inputs(("-c", "pass"), None, None)
