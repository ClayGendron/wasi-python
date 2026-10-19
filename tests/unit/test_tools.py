"""The tool protocol's host half (spec 031), with no guest: `tool()` describes and vets, the
validator checks without coercion inside a counted budget, and the frame host answers raw frames
in a fixed order, as a raw `host=` would see them. Nothing here measures time."""

from __future__ import annotations

import functools
import json
import numbers
import subprocess
import sys
from typing import Any, Literal

import pytest

from wasi_python import tools as T
from wasi_python.tools import Tool, ToolDenied, ToolError, tool


def frame(op: str = "call", *, v: Any = 1, id: Any = 1, **fields: Any) -> bytes:
    return json.dumps({"v": v, "id": id, "op": op, **fields}).encode()


def call_frame(name: str, args: Any, **fields: Any) -> bytes:
    return frame("call", tool=name, args=args, **fields)


def answer(raw: bytes) -> dict:
    assert isinstance(raw, bytes), type(raw)
    text = raw.decode("ascii")  # every answer is ASCII JSON (ensure_ascii)
    return json.loads(text)


def kind(raw: bytes) -> str | None:
    a = answer(raw)
    return None if a["ok"] else a["error"]["kind"]


class Counter:
    """A gate and a tool that count their calls."""

    def __init__(self) -> None:
        self.gate_calls = 0
        self.tool_calls = 0

    def gate(self, call: T.ToolCall) -> None:
        self.gate_calls += 1


def counting_tools(counter: Counter) -> list[Tool]:
    @tool
    def echo(x: Any) -> Any:
        """Give back what it was given."""
        counter.tool_calls += 1
        return x

    @tool
    def count(n: int) -> int:
        """Count to n."""
        counter.tool_calls += 1
        return n

    return [echo, count]


# -------------------------------------------------------------------------------------------------
# 1. A tool is described by its hints and docstring.


def lookup_region(
    code: str,
    level: Literal["country", "region"],
    data: bytes,
    pair: tuple[int, ...],
    counts: dict[str, int],
    year: int = 2026,
    note: str | None = None,
) -> dict[str, int]:
    """Look up a sales region by its code.

    Args:
        code: The region code, such as "EMEA".
        level: How fine the answer is.
        year: The fiscal year,
            from 2000 on.

    Returns:
        The region's numbers.
    """
    return {"code": len(code)}


LOOKUP_REGION = {
    "name": "lookup_region",
    "description": "Look up a sales region by its code.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": 'The region code, such as "EMEA".'},
            "level": {"enum": ["country", "region"], "description": "How fine the answer is."},
            "data": {"type": "string", "contentEncoding": "base64"},
            "pair": {"type": "array", "items": {"type": "integer"}},
            "counts": {"type": "object", "additionalProperties": {"type": "integer"}},
            "year": {
                "type": "integer",
                "description": "The fiscal year, from 2000 on.",
                "default": 2026,
            },
            "note": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": None},
        },
        "required": ["code", "level", "data", "pair", "counts"],
        "additionalProperties": False,
    },
    "outputSchema": {"type": "object", "additionalProperties": {"type": "integer"}},
    "annotations": {"readOnlyHint": True},
}


def test_a_tool_is_described_by_its_hints_and_docstring() -> None:
    t = tool(read_only=True)(lookup_region)
    assert isinstance(t, Tool)
    assert t.descriptor() == LOOKUP_REGION
    assert (t.name, t.description) == ("lookup_region", "Look up a sales region by its code.")
    assert t("EMEA", "region", b"", (), {}) == {"code": 4}  # callable on the host

    def plain(flag: bool, scale: float, nothing: None, anything: Any, items: list[str]) -> None:
        pass

    p = tool(plain)
    assert p.descriptor() == {
        "name": "plain",
        "description": "",
        "inputSchema": {
            "type": "object",
            "properties": {
                "flag": {"type": "boolean"},
                "scale": {"type": "number"},
                "nothing": {"type": "null"},
                "anything": {},
                "items": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["flag", "scale", "nothing", "anything", "items"],
            "additionalProperties": False,
        },
        "outputSchema": {"type": "null"},
    }
    named = tool(name="other", description="Said here.", destructive=True, open_world=True)(plain)
    assert named.descriptor()["name"] == "other"
    assert named.descriptor()["description"] == "Said here."
    assert named.descriptor()["annotations"] == {"destructiveHint": True, "openWorldHint": True}

    # The list answer keeps the order the embedder gave.
    host = T._ToolHost([t, p, named])
    a = answer(host(frame("list", id=7)))
    assert a == {"v": 1, "id": 7, "ok": True, "tools": [LOOKUP_REGION, *a["tools"][1:]]}
    assert [d["name"] for d in a["tools"]] == ["lookup_region", "plain", "other"]
    host = T._ToolHost([named, t, p])
    assert [d["name"] for d in answer(host(frame("list")))["tools"]] == [
        "other",
        "lookup_region",
        "plain",
    ]


def test_importing_the_package_does_not_load_the_tools() -> None:
    """Decision 1: `import wasi_python` leaves `wasi_python.tools` unloaded (spec 015's F6)."""
    probe = "import sys, wasi_python; print('wasi_python.tools' in sys.modules)"
    r = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, check=True)
    assert r.stdout.strip() == "False", r.stdout + r.stderr


# -------------------------------------------------------------------------------------------------
# 2. A tool that cannot be described is refused.


def schema(properties: dict, **more: Any) -> dict:
    return {"type": "object", "properties": properties, **more}


async def fetch(url: str):
    yield url  # an async generator: protocol 1 answers once (spec 053)


def _cycle() -> dict:
    return schema(
        {"x": {"$ref": "#/$defs/A"}},
        **{"$defs": {"A": {"anyOf": [{"$ref": "#/$defs/B"}]}, "B": {"$ref": "#/$defs/A"}}},
    )


def no_hint(x) -> None:  # noqa: ANN001
    pass


def star(*xs: int) -> None:
    pass


def stars(**kw: int) -> None:
    pass


def positional(x: int, /) -> None:
    pass


def bad_default(x: int = None) -> None:  # type: ignore[assignment]
    pass


def set_default(x: list[int] = {1}) -> None:  # type: ignore[assignment]  # noqa: B006
    pass


def set_hint(x: set[int]) -> None:
    pass


def fixed_tuple(x: tuple[int, str]) -> None:
    pass


def int_keys(x: dict[int, str]) -> None:
    pass


def square(x: int) -> int:
    return x


REFUSED = [
    # (what, the call, the exception, words its message must hold)
    (
        "a from property",
        lambda: tool(square, input_schema=schema({"from": {}})),
        ValueError,
        "'from'",
    ),
    (
        "a max-results property",
        lambda: tool(square, input_schema=schema({"max-results": {}})),
        ValueError,
        "'max-results'",
    ),
    (
        "a required name not in properties",
        lambda: tool(square, input_schema=schema({"x": {}}, required=["x", "y"])),
        ValueError,
        "'y'",
    ),
    ("x: int = None", lambda: tool(bad_default), ValueError, "int | None = None"),
    ("a NaN timeout_s", lambda: tool(square, timeout_s=float("nan")), ValueError, "timeout_s"),
    (
        "an infinite timeout_s",
        lambda: tool(square, timeout_s=float("inf")),
        ValueError,
        "timeout_s",
    ),
    ("a zero timeout_s", lambda: tool(square, timeout_s=0), ValueError, "timeout_s"),
    ("a bool timeout_s", lambda: tool(square, timeout_s=True), TypeError, "timeout_s"),
    ("a partial without name=", lambda: tool(functools.partial(square, 1)), TypeError, "name="),
    ("an async generator function", lambda: tool(fetch), TypeError, "async generator"),
    ("no hint", lambda: tool(no_hint), TypeError, "'x'"),
    ("*args", lambda: tool(star), TypeError, "'xs'"),
    ("**kwargs", lambda: tool(stars), TypeError, "'kw'"),
    ("a positional-only parameter", lambda: tool(positional), TypeError, "'x'"),
    ("a default with no JSON form", lambda: tool(set_default), ValueError, "'x'"),
    ("a hint outside the list", lambda: tool(set_hint), TypeError, "'x'"),
    ("a fixed tuple", lambda: tool(fixed_tuple), TypeError, "'x'"),
    ("a dict with int keys", lambda: tool(int_keys), TypeError, "'x'"),
    ("a bad name", lambda: tool(square, name="2fast"), ValueError, "'2fast'"),
    ("a keyword as a name", lambda: tool(square, name="class"), ValueError, "'class'"),
    ("a lambda", lambda: tool(lambda x: x), ValueError, "<lambda>"),
    (
        "a root that is not an object",
        lambda: tool(square, input_schema={"type": "array"}),
        ValueError,
        "object",
    ),
    (
        "pattern",
        lambda: tool(square, input_schema=schema({"x": {"type": "string", "pattern": "^a+$"}})),
        ValueError,
        "pattern",
    ),
    (
        "array items",
        lambda: tool(
            square,
            input_schema=schema({"x": {"type": "array", "items": [{"type": "string"}]}}),
            validates_input=True,
        ),
        ValueError,
        "items",
    ),
    (
        "a remote $ref",
        lambda: tool(
            square,
            input_schema=schema({"x": {"$ref": "https://example.org/s.json"}}),
            validates_input=True,
        ),
        ValueError,
        "$ref",
    ),
    (
        "a $ref cycle that does not descend",
        lambda: tool(square, input_schema=_cycle(), validates_input=True),
        ValueError,
        "$ref",
    ),
]


@pytest.mark.parametrize("what, make, error, words", REFUSED, ids=[r[0] for r in REFUSED])
def test_a_tool_that_cannot_be_described_is_refused(what, make, error, words) -> None:
    with pytest.raises(error) as refused:
        make()
    assert words in str(refused.value), str(refused.value)


def test_bound_keywords_are_found_through_any_wrapper() -> None:
    """Spec 056, Decision 1: a callable object whose `__call__` is a partial's target, and a
    `__wrapped__` cycle (refused, not walked forever)."""

    class Orders:
        def __call__(self, user_id: int, api_key: str = "default") -> int:
            return user_id

    assert T._bound_keywords("t", Orders()) == frozenset()
    assert T._bound_keywords("t", functools.partial(Orders(), api_key="k")) == {"api_key"}
    made = tool(functools.partial(Orders(), api_key="k"), name="t")
    assert made.input_schema["properties"] == {"user_id": {"type": "integer"}}
    assert made._fixed == {"api_key"}

    def loop(x: int) -> int:
        return x

    loop.__wrapped__ = loop
    with pytest.raises(TypeError, match="nest deeper"):
        tool(loop)


class _SlotCall:
    """Callable objects whose type's `__call__` is each kind of C slot in `_C_SLOTS`."""

    class Method:
        __call__ = str.upper  # a method descriptor

    class MethodWrapper:
        __call__ = (1).__add__  # a method-wrapper

    class Builtin:
        __call__ = len  # a builtin function

    class ClassMethod:
        __call__ = staticmethod(dict.__dict__["fromkeys"])  # a class-method descriptor


C_SLOT_ENDS = {
    "wrapper_descriptor": _SlotCall,  # a class: its type's __call__ is type.__call__
    "method-wrapper": _SlotCall.MethodWrapper(),
    "method_descriptor": _SlotCall.Method(),
    "builtin_function_or_method": _SlotCall.Builtin(),
    "classmethod_descriptor": _SlotCall.ClassMethod(),
}


def _wrapped_chain(end: Any, links: int) -> Any:
    """`links` functions, each `__wrapped__` round the next, the last round `end`."""
    target = end
    for _ in range(links):

        def link() -> None:
            pass

        link.__wrapped__ = target
        target = link
    return target


@pytest.mark.parametrize("slot", list(C_SLOT_ENDS))
def test_the_bound_keyword_walk_stops_at_each_c_slot(slot) -> None:
    """Spec 070, Decision 4 (spec 060's build review, N3): the walk stops at a C `__call__` itself,
    in the hop that meets it, as at a function. A function at the end of 63 links is the deepest
    chain the walk reads (64 hops); one link more is refused. Each slot kind at the same depth is
    read too, so no kind of `_C_SLOTS` can go without a hop more and the refusal."""
    assert type(type(C_SLOT_ENDS[slot]).__call__).__name__ == slot

    def plain() -> None:
        pass

    deepest = T._WRAPPER_DEPTH - 1
    assert T._bound_keywords("t", _wrapped_chain(plain, deepest)) == frozenset()
    with pytest.raises(TypeError, match="nest deeper"):
        T._bound_keywords("t", _wrapped_chain(plain, deepest + 1))
    assert T._bound_keywords("t", _wrapped_chain(C_SLOT_ENDS[slot], deepest)) == frozenset()


def test_validates_input_lets_unknown_keywords_through_but_never_a_cycle() -> None:
    s = schema({"x": {"type": "string", "pattern": "^a+$"}})
    t = tool(square, input_schema=s, validates_input=True)
    assert t.descriptor()["inputSchema"] == s
    # The pattern is the tool's to check: the validator skips it.
    host = T._ToolHost([t])
    assert kind(host(call_frame("square", {"x": "bbb"}))) is None
    with pytest.raises(ValueError, match=r"\$ref"):
        tool(square, input_schema=_cycle(), validates_input=True)
    # A cycle that descends into the value is how a recursive schema is written: allowed.
    tree = schema(
        {"t": {"$ref": "#/$defs/T"}},
        **{"$defs": {"T": {"type": "array", "items": {"$ref": "#/$defs/T"}}}},
    )
    tool(square, input_schema=tree)


class Model:
    """Anything with model_json_schema() (a pydantic model class), never imported."""

    @classmethod
    def model_json_schema(cls) -> dict:
        return schema({"code": {"type": "string", "title": "Code"}}, required=["code"])


def test_a_schema_may_come_from_a_model() -> None:
    seen = []

    def lookup(**kw: Any) -> str:
        seen.append(kw)
        return "ok"

    t = tool(lookup, input_schema=Model)
    assert t.input_schema == Model.model_json_schema()
    host = T._ToolHost([t])
    assert answer(host(call_frame("lookup", {"code": "EMEA"})))["value"] == "ok"
    assert seen == [{"code": "EMEA"}]
    assert kind(host(call_frame("lookup", {"code": "EMEA", "x": 1}))) == "invalid_arguments"


# -------------------------------------------------------------------------------------------------
# 3. A vetted schema cannot change.


def take(n: Any = None) -> Any:
    return n


def test_a_vetted_schema_cannot_change() -> None:
    given = schema({"n": {"type": "integer"}}, required=["n"])
    t = tool(take, input_schema=given)
    before = t.descriptor()
    given["properties"]["n"]["type"] = "string"
    given["properties"]["n"]["pattern"] = "^x$"
    given["required"].append("m")
    handed = t.input_schema
    handed["properties"]["n"]["type"] = "string"
    t.descriptor()["inputSchema"]["properties"].clear()
    assert t.descriptor() == before
    assert t.input_schema == before["inputSchema"]
    host = T._ToolHost([t])
    assert answer(host(call_frame("take", {"n": 3})))["value"] == 3
    assert kind(host(call_frame("take", {"n": "3"}))) == "invalid_arguments"
    # Compared and hashed by identity.
    u = tool(take, input_schema=schema({"n": {"type": "integer"}}, required=["n"]))
    assert t != u and t == t
    assert len({t, u, t}) == 2
    with pytest.raises(AttributeError):
        t.name = "other"  # type: ignore[misc]
    with pytest.raises(TypeError, match="tool()"):
        Tool("x", "", square, {"type": "object"}, None)


# -------------------------------------------------------------------------------------------------
# 4. The validator does not coerce, and it works inside a counted budget.

DEFS = {"$defs": {"Pos": {"type": "integer", "minimum": 1}}}

TABLE = [
    # (schema, value, passes)
    ({"type": "integer"}, 7, True),
    ({"type": "integer"}, "7", False),
    ({"type": "integer"}, True, False),
    ({"type": "integer"}, 5.0, False),
    ({"type": "number"}, 5, True),
    ({"type": "number"}, 5.5, True),
    ({"type": "number"}, True, False),
    ({"type": "boolean"}, True, True),
    ({"type": "boolean"}, 1, False),
    ({"type": "null"}, None, True),
    ({"type": "null"}, 0, False),
    ({"type": "string"}, "a", True),
    ({"type": "string"}, b"a", False),  # $bytes against a string schema
    ({"type": ["string", "null"]}, None, True),
    ({"type": ["string", "null"]}, 1, False),
    ({"type": "array"}, [1], True),
    ({"type": "array"}, {"a": 1}, False),
    ({"type": "object"}, {"a": 1}, True),  # no properties: open
    ({"type": "object"}, [1], False),
    ({"enum": [1]}, 1, True),
    ({"enum": [1]}, True, False),
    ({"enum": [1]}, 1.0, False),
    ({"enum": [{"a": 1}]}, {"a": True}, False),
    ({"enum": [{"a": 1}]}, {"a": 1}, True),
    ({"const": 1}, 1.0, False),
    ({"const": 1}, 1, True),
    ({"const": [1]}, [True], False),
    ({"const": [1]}, [1], True),
    ({"const": None}, None, True),
    ({"type": "array", "uniqueItems": True}, [1, True], True),
    ({"type": "array", "uniqueItems": True}, [1, 1.0], True),
    ({"type": "array", "uniqueItems": True}, [1, 1], False),
    ({"type": "array", "uniqueItems": True}, [{"a": [1]}, {"a": [1]}], False),
    ({"type": "array", "uniqueItems": True}, [{"a": [1]}, {"a": [True]}], True),
    ({"properties": {"a": {"type": "integer"}}, "required": ["a"]}, {"a": 1}, True),
    ({"properties": {"a": {"type": "integer"}}, "required": ["a"]}, {"a": 1, "b": 2}, False),
    ({"properties": {"a": {"type": "integer"}}, "required": ["a"]}, {}, False),
    ({"properties": {"a": {}}, "additionalProperties": True}, {"a": 1, "b": 2}, True),
    ({"properties": {"a": {}}, "additionalProperties": False}, {"b": 2}, False),
    ({"type": "object", "additionalProperties": {"type": "integer"}}, {"x": 1}, True),
    ({"type": "object", "additionalProperties": {"type": "integer"}}, {"x": "1"}, False),
    ({"type": "object", "minProperties": 1}, {}, False),
    ({"type": "object", "maxProperties": 1}, {"a": 1, "b": 2}, False),
    ({"type": "object", "maxProperties": 2}, {"a": 1, "b": 2}, True),
    ({"type": "array", "items": {"type": "integer"}}, [1, 2], True),
    ({"type": "array", "items": {"type": "integer"}}, [1, "2"], False),
    ({"prefixItems": [{"type": "string"}], "items": {"type": "integer"}}, ["a", 1, 2], True),
    ({"prefixItems": [{"type": "string"}], "items": {"type": "integer"}}, ["a", "b"], False),
    ({"prefixItems": [{"type": "string"}], "items": {"type": "integer"}}, [1], False),
    ({"prefixItems": [{"type": "string"}], "items": False}, ["a", 1], False),
    ({"prefixItems": [{"type": "string"}]}, ["a", 1], True),
    ({"type": "array", "minItems": 2}, [1], False),
    ({"type": "array", "maxItems": 1}, [1, 2], False),
    ({"anyOf": [{"type": "integer"}, {"type": "string"}]}, "a", True),
    ({"anyOf": [{"type": "integer"}, {"type": "string"}]}, None, False),
    ({"oneOf": [{"type": "integer"}, {"type": "number"}]}, 1, False),  # both match
    ({"oneOf": [{"type": "integer"}, {"type": "number"}]}, 1.5, True),
    ({"$ref": "#/$defs/Pos", **DEFS}, 1, True),
    ({"$ref": "#/$defs/Pos", **DEFS}, 0, False),
    ({"$ref": "#/$defs/Pos", **DEFS}, 1.0, False),
    ({"type": "number", "minimum": 1}, 0.5, False),
    ({"type": "number", "maximum": 1}, 1, True),
    ({"type": "number", "exclusiveMinimum": 1}, 1, False),
    ({"type": "number", "exclusiveMaximum": 1}, 0.999, True),
    ({"type": "number", "exclusiveMaximum": 1}, 1.0, False),
    ({"multipleOf": 3}, 9, True),
    ({"multipleOf": 3}, 10, False),
    ({"multipleOf": 3}, 9.0, True),
    ({"multipleOf": 3}, 9.5, False),
    ({"type": "string", "maxLength": 1}, "é", True),  # code points, not bytes
    ({"type": "string", "maxLength": 1}, "\U0001f600", True),
    ({"type": "string", "maxLength": 1}, "ab", False),
    ({"type": "string", "minLength": 2}, "a", False),
    ({"type": "string", "contentEncoding": "base64"}, b"x", True),
    ({"type": "string", "contentEncoding": "base64"}, "eA==", False),
    # Bytes are accepted only where the schema says so, never where it says nothing.
    ({}, b"x", False),
    (True, b"x", False),
    ({"type": "object"}, {"a": b"x"}, False),
    ({"type": "array"}, [[b"x"]], False),
    ({"prefixItems": [{"type": "string"}]}, ["a", b"x"], False),
    ({"anyOf": [{"type": "string", "contentEncoding": "base64"}, {"type": "null"}]}, b"x", True),
    (
        {"$ref": "#/$defs/B", "$defs": {"B": {"type": "string", "contentEncoding": "base64"}}},
        b"",
        True,
    ),
    ({"title": "T", "description": "d", "format": "date", "examples": [1]}, "anything", True),
    (True, 1, True),
    (False, 1, False),
]


@pytest.mark.parametrize("s, value, passes", TABLE)
def test_the_validator_does_not_coerce(s, value, passes) -> None:
    v = T._Validator(s)
    error = v.check(value)
    assert (error is None) == passes, error
    assert not v.exhausted


def test_bytes_cross_only_where_the_schema_says_so() -> None:
    @tool
    def text(s: str) -> str:
        return s

    @tool
    def blob(b: bytes) -> int:
        return len(b)

    @tool
    def anything(x: Any) -> Any:
        return x

    host = T._ToolHost([text, blob, anything])
    assert kind(host(call_frame("text", {"s": {"$bytes": "eA=="}}))) == "invalid_arguments"
    assert kind(host(call_frame("anything", {"x": {"$bytes": "eA=="}}))) == "invalid_arguments"
    assert kind(host(call_frame("anything", {"x": [{"y": {"$bytes": ""}}]}))) == "invalid_arguments"
    assert answer(host(call_frame("blob", {"b": {"$bytes": "eHl6"}})))["value"] == 3
    assert kind(host(call_frame("blob", {"b": "eHl6"}))) == "invalid_arguments"


# pydantic 2.14.1's schema for Node = RootModel[Union[list[Node], list[Union[int, Node]]]]
# (EXECUTED in the pre-build review, recursive_union.txt), written here so pydantic is not a
# dependency.
NODE = {
    "anyOf": [
        {"items": {"$ref": "#/$defs/Node"}, "type": "array"},
        {"items": {"anyOf": [{"type": "integer"}, {"$ref": "#/$defs/Node"}]}, "type": "array"},
    ],
    "title": "Node",
}
TREE = schema({"tree": {"$ref": "#/$defs/Node"}}, required=["tree"], **{"$defs": {"Node": NODE}})


def deep(levels: int, leaf: Any) -> Any:
    value = leaf
    for _ in range(levels):
        value = [value]
    return value


def test_a_recursive_union_is_checked_within_the_budget() -> None:
    v = T._Validator(TREE)
    assert v.check({"tree": deep(3, 1)}) is None  # an ordinary value passes
    v = T._Validator(TREE)
    error = v.check({"tree": deep(62, "leaf")})  # fails only at its deepest leaf
    assert error == "the arguments are too complex to check", error
    assert v.exhausted and v.steps <= T._TOOL_VALIDATION_STEPS == 100_000
    # And through a frame: 62 levels inside args is the most a frame may carry.
    t = tool(square, name="walk", input_schema=TREE)
    host = T._ToolHost([t])
    a = answer(host(call_frame("walk", {"tree": deep(62, "leaf")})))
    assert a["error"] == {
        "kind": "invalid_arguments",
        "message": "walk: the arguments are too complex to check",
    }


def test_unique_items_take_one_pass() -> None:
    s = {"type": "array", "uniqueItems": True}
    v = T._Validator(s)
    items = [*range(50_000), 0]
    error = v.check(items)
    assert error is not None and "unique" in error, error
    assert not v.exhausted
    assert v.keys == 50_001  # one key per item, then the repeat is found: no pairwise comparison
    assert v.steps <= 50_001 + 1
    v = T._Validator(s)
    error = v.check(list(range(100_001)))  # about 600 KB as a frame
    assert error == "the arguments are too complex to check", error
    assert v.exhausted and v.steps <= T._TOOL_VALIDATION_STEPS


def test_unique_item_keys_are_charged() -> None:
    """Review F6: each uniqueItems key is a counted step, made before the items are visited, so
    100,001 distinct strings exhaust the budget before the first one fails its type."""
    v = T._Validator({"type": "array", "uniqueItems": True, "items": {"type": "integer"}})
    assert v.check([f"s{i}" for i in range(100_001)]) == "the arguments are too complex to check"
    assert v.exhausted and v.steps <= T._TOOL_VALIDATION_STEPS


def values(x: Any) -> int:
    """The JSON values in x, containers included."""
    if isinstance(x, dict):
        return 1 + sum(values(v) for v in x.values())
    if isinstance(x, list):
        return 1 + sum(values(v) for v in x)
    return 1


# pydantic's shapes (review F2): an order whose lines are a $ref, and a recursive tree with an
# Optional parent (anyOf of a $ref and null).
ORDER = {
    "type": "object",
    "properties": {"lines": {"type": "array", "items": {"$ref": "#/$defs/Line"}}},
    "required": ["lines"],
    "additionalProperties": False,
    "$defs": {
        "Line": {
            "type": "object",
            "properties": {
                "sku": {"type": "string"},
                "qty": {"type": "integer"},
                "note": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": None},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["sku", "qty"],
        }
    },
}
NODE_TREE = {
    "type": "object",
    "properties": {"root": {"$ref": "#/$defs/Node"}},
    "required": ["root"],
    "$defs": {
        "Node": {
            "type": "object",
            "properties": {
                "value": {"type": "integer"},
                "children": {"type": "array", "items": {"$ref": "#/$defs/Node"}},
                "parent": {"anyOf": [{"$ref": "#/$defs/Node"}, {"type": "null"}], "default": None},
            },
            "required": ["value"],
        }
    },
}


def chain(depth: int, leaves: int) -> dict:
    node: dict = {"value": 0, "children": [{"value": i, "parent": None} for i in range(leaves)]}
    for _ in range(depth):
        node = {"value": 1, "children": [node]}
    return node


@pytest.mark.parametrize(
    "schema_, args, per_value",
    [
        (
            ORDER,
            {"lines": [{"sku": "A1", "qty": 2, "note": None, "tags": ["x", "y"]}] * 5_000},
            1.5,
        ),
        (NODE_TREE, {"root": chain(20, 5_000)}, 2.5),
        (NODE_TREE, {"root": chain(60, 1_000)}, 2.5),
        (TREE, {"tree": deep(60, list(range(1_000)))}, 2.5),
    ],
    ids=[
        "an order of 5,000 lines",
        "a tree 20 deep, 5,000 leaves",
        "a tree 60 deep",
        "pydantic's recursive union, 60 deep",
    ],
)
def test_valid_arguments_cost_about_one_step_per_value(schema_, args, per_value) -> None:
    """Decision 3's basis, as the README states it (review F2): a value costs one step for each
    schema node it is checked against: its own, each $ref, anyOf or oneOf around it, and each
    anyOf branch tried. A node that only delegates never walks the value again, so the cost per
    value does not grow with depth. pydantic's shapes: an order at most 1.5 steps per value; a
    tree whose Optional parent tries a $ref before null at most 2.5."""
    v = T._Validator(schema_)
    assert v.check(args) is None
    assert v.steps <= per_value * values(args), (v.steps, values(args))


def test_an_enum_costs_one_key_per_value(monkeypatch) -> None:
    """Review F1: `names: list[Literal[<600 names>]]` with 99,990 names in one frame. Each name's
    key is built once and looked up in the enum's key set, made once when the tool is made; a
    container's key is charged one step per value below it."""
    names = tuple(f"z{i:04d}" for i in range(600))

    def zones(places: list[str]) -> int:
        return len(places)

    zones.__annotations__["places"] = list[Literal[names]]
    t = tool(zones)
    built = {"keys": 0}
    real = T._key

    def counting(value: Any, *more: Any) -> Any:
        built["keys"] += 1
        return real(value, *more)

    monkeypatch.setattr(T, "_key", counting)
    host = T._ToolHost([t])
    raw = host(call_frame("zones", {"places": [names[-1]] * 99_990}))
    assert answer(raw)["value"] == 99_990
    assert built["keys"] <= 99_990 + 10, built  # one per name: never the enum's 600 per name
    # A const or an enum compared with a container charges the values below it: 100,000 of
    # them exhaust the budget before the comparison could fail.
    v = T._Validator({"const": [1]})
    assert v.check(list(range(100_000))) == "the arguments are too complex to check"
    assert v.exhausted and v.steps <= T._TOOL_VALIDATION_STEPS


def many(**kw: Any) -> dict:
    """Give back the arguments (module level, so a Tool of it pickles)."""
    return kw


def test_a_pickled_tool_checks_each_enum_against_its_own_set() -> None:
    """Confirmation N1: the key sets are found by node identity. A Tool pickled, the original
    freed, then unpickled, reuses the freed ids; each node still checks only its own set."""
    import gc
    import pickle

    n = 30
    allow = schema({f"p{i}": {"enum": [f"v{i}"]} for i in range(n)})
    wrong = 0
    for _ in range(5):
        t = tool(many, input_schema=allow)
        data = pickle.dumps(t)
        del t
        gc.collect()
        host = T._ToolHost([pickle.loads(data)], max_calls=None)
        for i in range(n):
            assert answer(host(call_frame("many", {f"p{i}": f"v{i}"})))["ok"] is True
            for j in range(n):
                if i != j:
                    wrong += answer(host(call_frame("many", {f"p{i}": f"v{j}"})))["ok"]
    assert wrong == 0


def test_messages_never_format_a_whole_value() -> None:
    """Review F1: a failing enum, const or bound names the value by its kind and size, never by
    dumping it, so a message costs what it says."""
    v = T._Validator({"type": "object", "properties": {"x": {"const": 1}}})
    big = list(range(50_000))
    error = v.check({"x": big})
    assert error is not None and "array of 50000 items" in error and len(error) < 200, error
    assert T._shown({"k" * 100: 1}) == "an object of 1 keys"
    assert T._shown("y" * 100) == "'" + "y" * 64 + "'..."


# -------------------------------------------------------------------------------------------------
# 5. Frames follow the protocol's rules.


def nested(total: int) -> bytes:
    """A call frame nested `total` levels, its envelope (the frame and args) included."""
    return call_frame("echo", {"x": deep(total - 2, 0)})


def raw_call(args_text: str, name: str = "echo") -> bytes:
    head = json.dumps({"v": 1, "id": 1, "op": "call", "tool": name}, separators=(",", ":"))
    return (head[:-1] + ',"args":' + args_text + "}").encode()


BAD_FRAMES = [
    ("not UTF-8", b'{"v":1,"id":1,"op":"list","x":"\xff"}'),
    ("UTF-16", frame("list").decode().encode("utf-16")),
    ("UTF-32", frame("list").decode().encode("utf-32")),
    ("nested 65 levels", nested(65)),
    ("NaN", raw_call('{"x":NaN}')),
    ("Infinity", raw_call('{"x":-Infinity}')),
    ("1e400", raw_call('{"x":1e400}')),
    ("a 65-character integer", raw_call('{"x":' + "9" * 65 + "}")),
    ("a duplicate key", b'{"v":1,"v":1,"id":1,"op":"list"}'),
    ("a duplicate key, escaped", b'{"v":1,"\\u0076":1,"id":1,"op":"list"}'),
    ("a lone surrogate in a value", raw_call('{"x":"\\ud800"}')),
    ("a $bytes that is not a string", raw_call('{"x":{"$bytes":5}}')),
    ("a $bytes that is not base64", raw_call('{"x":{"$bytes":"!!"}}')),
    ("a $bytes with another key", raw_call('{"x":{"$bytes":"QQ==","y":1}}')),
    ("a top-level array", b'[{"v":1,"id":1,"op":"list"}]'),
    ("v: 0", frame("list", v=0)),
    ("no v", b'{"id":1,"op":"list"}'),
    ("v: true", frame("list", v=True)),
    ("an unknown op", frame("batch")),
    ("a tool that is not a string", frame("call", tool=5, args={})),
    ("not JSON", b'{"v":1,'),
]


@pytest.mark.parametrize("what, raw", BAD_FRAMES, ids=[b[0] for b in BAD_FRAMES])
def test_frames_follow_the_protocols_rules(what, raw) -> None:
    c = Counter()
    host = T._ToolHost(counting_tools(c), gate=c.gate)
    a = answer(host(raw))
    assert a["v"] == 1 and a["ok"] is False, a
    assert a["error"]["kind"] == "protocol", a
    assert len(a["error"]["message"]) <= 4096
    assert (c.gate_calls, c.tool_calls) == (0, 0)
    assert host.record.frames == 1
    assert [o.outcome for o in host.record.outcomes] == ["protocol"]


def test_the_frame_rules_name_versions_ops_tools_and_arguments() -> None:
    c = Counter()
    host = T._ToolHost(counting_tools(c), gate=c.gate)
    a = answer(host(frame("list", v=0, id=3)))
    assert a["id"] == 3 and "version 1" in a["error"]["message"], a
    a = answer(host(frame("fly")))
    assert "list" in a["error"]["message"] and "call" in a["error"]["message"], a
    a = answer(host(call_frame("nope", {})))
    assert a["error"]["kind"] == "unknown_tool" and "echo" in a["error"]["message"], a
    a = answer(host(call_frame("count", {"n": "7"})))
    assert a["error"]["kind"] == "invalid_arguments", a
    assert (c.gate_calls, c.tool_calls) == (0, 0)
    # Echoed only when it is an int from 0 to 2**53 - 1.
    for sent, echoed in [(5, 5), (0, 0), (2**53 - 1, 2**53 - 1), (2**53, None), (-1, None)]:
        assert answer(host(frame("list", id=sent)))["id"] == echoed
    for sent in [True, "5", 1.0, None, [1]]:
        assert answer(host(frame("list", id=sent)))["id"] is None


def test_the_frame_limits_pass_at_their_bounds() -> None:
    c = Counter()
    host = T._ToolHost(counting_tools(c), gate=c.gate)
    assert kind(host(nested(64))) is None  # 64 levels in all: 62 inside args
    assert kind(host(raw_call('{"x":' + "9" * 64 + "}"))) is None
    assert answer(host(raw_call('{"x":"\\ud83d\\ude00"}')))["value"] == "\U0001f600"  # a pair
    assert answer(host(raw_call('{"x":"[{\\"]"}')))["value"] == '[{"]'  # brackets in a string
    assert (c.gate_calls, c.tool_calls) == (4, 4)


class CountingPattern:
    """A compiled pattern whose finditer counts the matches it yields."""

    def __init__(self, pattern) -> None:
        self.pattern, self.matches = pattern, 0

    def finditer(self, text: str):
        for m in self.pattern.finditer(text):
            self.matches += 1
            yield m


@pytest.mark.parametrize(
    "text",
    [
        '"' + '\\"' * 400_000,  # an unterminated string of escaped quotes: n**2 for a regex
        '"' * 800_000,  # quotes alone
        "[" * 65 + '"' + "]" * 65,
        '{"a":"\\\\"}',
    ],
    ids=["escaped quotes", "quotes", "brackets", "escaped backslash"],
)
def test_the_nesting_scan_is_one_pass(monkeypatch, text) -> None:
    """Decision 4, rule 3, on a guest's frame of up to 1 MiB: one token per match, each character
    seen once, whatever the frame (a regular expression retried at every quote is quadratic)."""
    counter = CountingPattern(T._TOKEN)
    monkeypatch.setattr(T, "_TOKEN", counter)
    T._nesting(text)
    assert counter.matches <= len(text)
    c = Counter()
    host = T._ToolHost(counting_tools(c), gate=c.gate)
    assert kind(host(text.encode())) == "protocol"


def test_a_long_integer_is_refused_whatever_the_process_allows() -> None:
    before = sys.get_int_max_str_digits()
    sys.set_int_max_str_digits(0)
    try:
        c = Counter()
        host = T._ToolHost(counting_tools(c), gate=c.gate)
        assert kind(host(raw_call('{"x":' + "9" * 65 + "}"))) == "protocol"
        assert kind(host(raw_call('{"x":' + "9" * 5000 + "}"))) == "protocol"
        assert c.tool_calls == 0
    finally:
        sys.set_int_max_str_digits(before)


def test_a_lone_surrogate_in_a_key_is_echoed_and_encodes() -> None:
    c = Counter()
    host = T._ToolHost(counting_tools(c), gate=c.gate)
    raw = host(raw_call('{"\\ud800":1}', "count"))
    assert b"\\ud800" in raw  # echoed, as an escape: the answer is ASCII
    assert kind(raw) == "protocol"
    assert answer(raw)["error"]["message"].count("\ud800") == 1


def test_the_cap_and_the_budget_answer_from_the_length_alone() -> None:
    c = Counter()
    host = T._ToolHost(counting_tools(c), gate=c.gate, max_calls=2)
    over = host.admit(T._TOOL_REQUEST_BYTES + 1)  # no bytes at all
    assert kind(over) == "too_large" and answer(over)["id"] is None
    assert host.admit(T._TOOL_REQUEST_BYTES) is None  # at the cap: admitted
    f = frame("list")
    assert kind(host(f[:0] + b" " * (T._TOOL_REQUEST_BYTES - len(f)) + f)) is None
    past = host.admit(10)
    assert kind(past) == "budget_exceeded"
    assert kind(host(frame("list"))) == "budget_exceeded"  # the raw path counts it too
    assert host.record.frames == 4
    assert [o.outcome for o in host.record.outcomes] == [
        "too_large",
        "ok",
        "budget_exceeded",
        "budget_exceeded",
    ]
    assert (c.gate_calls, c.tool_calls) == (0, 0)
    # max_calls=0 refuses the first frame, the guest's discovery.
    assert kind(T._ToolHost([], max_calls=0)(frame("list"))) == "budget_exceeded"


def test_every_frame_is_counted_once_on_both_paths() -> None:
    c = Counter()
    host = T._ToolHost(counting_tools(c), gate=c.gate)
    f = call_frame("count", {"n": 2})
    assert host.admit(len(f)) is None  # the door's path: admit, then the bytes
    assert answer(host(f))["value"] == 2
    assert host.record.frames == 1
    assert answer(host(f))["value"] == 2  # the raw path: the frame host admits it itself
    assert host.record.frames == 2
    assert host.admit(len(f) + 1) is None  # a runner that admits one length and sends another
    a = answer(host(f))
    assert a["error"]["kind"] == "protocol", a
    assert host.record.frames == 3
    assert [o.seq for o in host.record.outcomes] == [1, 2, 3]
    assert [o.outcome for o in host.record.outcomes] == ["ok", "ok", "protocol"]
    assert host.record.outcomes[2].fault is not None
    assert c.tool_calls == 2


# -------------------------------------------------------------------------------------------------
# 6. The gate decides after validation.


def test_the_gate_decides_after_validation() -> None:
    received = []

    @tool
    def count(n: int, tags: list[str] = ()) -> int:  # type: ignore[assignment]
        received.append((n, list(tags)))
        return n

    def run(gate) -> dict:
        host = T._ToolHost([count], gate=gate)
        a = answer(host(call_frame("count", {"n": 1, "tags": ["a"]})))
        return {"answer": a, "outcome": host.record.outcomes[-1]}

    seen = []

    def watch(verdict):
        def gate(call: T.ToolCall):
            seen.append(call)
            if isinstance(verdict, BaseException):
                raise verdict
            return verdict

        return gate

    assert run(watch(None))["answer"]["value"] == 1
    assert run(watch(True))["answer"]["value"] == 1
    assert len(received) == 2
    call = seen[0]
    assert (call.seq, call.tool, call.arguments, call.request_bytes) == (
        1,
        count,
        {"n": 1, "tags": ["a"]},
        len(call_frame("count", {"n": 1, "tags": ["a"]})),
    )

    for verdict, message, faulted in [
        (False, "count was refused", False),
        (ToolDenied("not on a Sunday"), "not on a Sunday", False),
        (ToolError("ask the owner"), "ask the owner", False),
        (KeyError("/etc/secret"), "count was refused", True),
        (SystemExit(3), "count was refused", True),
        ("yes", "count was refused", True),
        (1, "count was refused", True),
    ]:
        r = run(watch(verdict))
        assert r["answer"]["error"] == {"kind": "denied", "message": message}, (verdict, r)
        assert (r["outcome"].fault is not None) == faulted, (verdict, r["outcome"])
    assert len(received) == 2  # no refused call reached the tool
    assert run(watch(KeyError("x")))["outcome"].fault == "KeyError: 'x'"

    def meddle(call: T.ToolCall) -> None:
        call.arguments["n"] = 99
        call.arguments["tags"].append("b")

    assert run(meddle)["answer"]["value"] == 1
    assert received[-1] == (1, ["a"])  # the tool's copy is its own

    # Invalid arguments never reach the gate.
    seen.clear()
    host = T._ToolHost([count], gate=watch(None))
    assert kind(host(call_frame("count", {"n": "1"}))) == "invalid_arguments"
    assert seen == []


# -------------------------------------------------------------------------------------------------
# 7. Only chosen text crosses, and it is bounded.


class Big:
    """A numpy-like integer: registered with numbers.Integral, not an int."""

    def __init__(self, n: int) -> None:
        self.n = n

    def __int__(self) -> int:
        return self.n

    __index__ = __int__


numbers.Integral.register(Big)


class Real:
    """A numpy-like float: registered with numbers.Real, not a float."""

    def __init__(self, x: float) -> None:
        self.x = x

    def __float__(self) -> float:
        return self.x


numbers.Real.register(Real)


def test_only_chosen_text_crosses_and_is_bounded() -> None:
    results: dict[str, Any] = {}

    @tool
    def give(what: str) -> Any:
        r = results[what]
        if isinstance(r, BaseException):
            raise r
        return r

    host = T._ToolHost([give])

    def ask(what: str, value: Any) -> tuple[dict, T.ToolOutcome]:
        results[what] = value
        a = answer(host(call_frame("give", {"what": what})))
        return a, host.record.outcomes[-1]

    a, o = ask("long", ToolError("x" * 5000))
    assert a["error"]["kind"] == "tool_error" and a["error"]["message"] == "x" * 4096
    assert o.fault is None and o.message == "x" * 4096
    a, o = ask("denied", ToolDenied("no"))
    assert a["error"] == {"kind": "denied", "message": "no"}
    a, o = ask("leak", KeyError("/home/owner/secret.txt"))
    assert a["error"] == {"kind": "tool_error", "message": "give failed (internal error)"}
    assert "secret" not in json.dumps(a)
    assert o.fault == "KeyError: '/home/owner/secret.txt'"
    for what, value in [("int key", {1: "a"}), ("set", {1, 2}), ("inf", float("inf"))]:
        a, o = ask(what, value)
        assert a["error"] == {"kind": "tool_error", "message": "give failed (internal error)"}, a
        assert o.fault is not None and len(o.fault) <= 200, (what, o)
    a, o = ask("only $bytes", {"$bytes": "QQ=="})
    assert a["error"]["message"] == "give failed (internal error)"
    a, o = ask("long fault", ValueError("y" * 1000 + "\nsecond line"))
    assert o.fault == ("ValueError: " + "y" * 1000)[:200]
    a, _ = ask("numpy-like", {"n": Big(7), "x": Real(0.5), "t": (1, 2), "b": b"\x00"})
    assert a["value"] == {"n": 7, "x": 0.5, "t": [1, 2], "b": {"$bytes": "AA=="}}
    a, o = ask("huge", "x" * (17 << 20))
    assert a["error"]["kind"] == "too_large" and "16777216" in a["error"]["message"], a
    assert o.outcome == "too_large"


class LoudText(ToolError):
    """A ToolError whose text raises SystemExit."""

    def __str__(self) -> str:
        raise SystemExit(9)


class LoudKey(KeyError):
    """An exception whose text raises KeyboardInterrupt."""

    def __str__(self) -> str:
        raise KeyboardInterrupt


@pytest.mark.parametrize("where", ["tool", "gate"])
@pytest.mark.parametrize(
    "raised",
    [SystemExit(3), KeyboardInterrupt(), LoudText(), LoudKey()],
    ids=[
        "SystemExit",
        "KeyboardInterrupt",
        "a __str__ raising SystemExit",
        "a __str__ raising Ctrl-C",
    ],
)
def test_a_base_exception_never_escapes_the_frame_host(where, raised) -> None:
    """Decision 6 and review F3: a BaseException from a tool or a gate, or from an exception's
    own __str__, is a fault, answered and recorded; nothing raises out of the frame host."""

    def boom(*_: Any) -> None:
        raise raised

    @tool
    def act(n: int) -> int:
        if where == "tool":
            boom()
        return n

    host = T._ToolHost([act], gate=boom if where == "gate" else None)
    a = answer(host(call_frame("act", {"n": 1})))
    assert a["ok"] is False and a["error"]["kind"] in ("denied", "tool_error"), a
    o = host.record.outcomes[-1]
    # A ToolError whose text cannot be read faults with what its __str__ raised.
    named = "SystemExit" if isinstance(raised, LoudText) else type(raised).__name__
    assert o.fault is not None and o.fault.split(":")[0] == named, o
    assert a["error"]["message"] in ("act failed (internal error)", "act was refused"), a


def test_a_result_nested_too_deep_is_a_fault() -> None:
    """The builder's bound, checked (review F6): a result nested deeper than 62 levels faults."""

    @tool
    def nest(levels: int) -> Any:
        return deep(levels, 0)

    host = T._ToolHost([nest])
    assert answer(host(call_frame("nest", {"levels": 62})))["ok"] is True
    a = answer(host(call_frame("nest", {"levels": 64})))
    assert a["error"] == {"kind": "tool_error", "message": "nest failed (internal error)"}, a
    assert "nests deeper" in host.record.outcomes[-1].fault


def test_a_long_same_value_chain_is_refused() -> None:
    """Review F5: a $ref chain that stays on one value is at most _SAME_VALUE_CHAIN nodes, so the
    validator's recursion never depends on the host Python's limit."""

    def chained(n: int) -> dict:
        defs = {f"D{i}": {"$ref": f"#/$defs/D{i + 1}"} for i in range(n)}
        defs[f"D{n}"] = {"type": "integer"}
        return schema({"x": {"$ref": "#/$defs/D0"}}, **{"$defs": defs})

    tool(square, input_schema=chained(T._SAME_VALUE_CHAIN - 2))
    with pytest.raises(ValueError, match="chain of more than 8"):
        tool(square, input_schema=chained(1_500))
    with pytest.raises(ValueError, match="chain of more than 8"):
        tool(square, input_schema=chained(T._SAME_VALUE_CHAIN))


def test_only_tool_makes_a_tool() -> None:
    """Review F7: dataclasses.replace cannot make a Tool that tool() never vetted."""
    import dataclasses

    t = tool(square)
    with pytest.raises(TypeError, match="tool()"):
        dataclasses.replace(t, _input_schema=schema({"x": {"type": "string", "pattern": "a"}}))


# -------------------------------------------------------------------------------------------------
# 8. The record is bounded.


def test_the_record_is_bounded() -> None:
    @tool
    def f(a: int) -> int:
        return a

    host = T._ToolHost([f], max_calls=None)
    for _ in range(1500):
        raw = host(call_frame("f", {"a": 1, "k" * 10_000: 1}))
        assert kind(raw) == "invalid_arguments"
    big = call_frame("f", {"a": 1, "k" * 1_000_000: 1})
    assert len(big) <= T._TOOL_REQUEST_BYTES  # it fits the cap, so it reaches the validator
    a = answer(host(big))
    assert a["error"]["kind"] == "invalid_arguments", a
    assert "k" * 64 in a["error"]["message"] and "k" * 65 not in a["error"]["message"]
    r = host.record
    assert (r.frames, len(r.outcomes), r.unlisted) == (1501, 1000, 501)
    assert all(o.message is None or len(o.message) <= 4096 for o in r.outcomes)
    assert all("k" * 65 not in (o.message or "") for o in r.outcomes)
    assert r.outcomes[0].request_bytes == len(call_frame("f", {"a": 1, "k" * 10_000: 1}))
    assert r.outcomes[0].tool == "f" and r.outcomes[0].op == "call"
    assert not any(o.abandoned for o in r.outcomes)


# -------------------------------------------------------------------------------------------------
# 9. A per-run budget of request bytes, and the tool list encoded once (spec 060).


def padded(raw: bytes, size: int) -> bytes:
    """`raw` with leading spaces, `size` bytes long: JSON allows them, so it parses the same."""
    assert len(raw) <= size
    return b" " * (size - len(raw)) + raw


def test_the_request_byte_budget_counts_admitted_bytes(monkeypatch) -> None:
    """Spec 060, criterion 1: the bytes `admit` lets through are counted from their length, before
    a frame is read, whatever its answer; a frame that would pass the budget is refused unread,
    `budget_exceeded`, and spends nothing. Parses are counted, never timed."""
    parses: list[int] = []
    real = T._parse

    def counting(raw: bytes) -> dict:
        parses.append(len(raw))
        return real(raw)

    monkeypatch.setattr(T, "_parse", counting)
    c = Counter()
    host = T._ToolHost(counting_tools(c), gate=c.gate, max_bytes=1000)
    assert host.admit(600) is None
    assert kind(host(b"x" * 600)) == "protocol"  # not JSON: it still spent its bytes
    assert len(parses) == 1
    refused = host.admit(401)
    assert kind(refused) == "budget_exceeded", refused
    assert "bytes" in answer(refused)["error"]["message"]
    assert host._pending is None
    last = host.record.outcomes[-1]
    assert (last.op, last.tool, last.outcome, last.request_bytes) == (
        None,
        None,
        "budget_exceeded",
        401,
    )
    assert len(parses) == 1
    assert host.admit(400) is None  # exactly reaches 1000: admitted
    assert answer(host(padded(call_frame("count", {"n": 1}), 400)))["value"] == 1
    assert len(parses) == 2
    assert kind(host.admit(1)) == "budget_exceeded"
    assert len(parses) == 2
    assert c.tool_calls == 1

    # The 1 MiB cap comes first, and a frame over it spends nothing.
    host = T._ToolHost([], max_bytes=T._TOOL_REQUEST_BYTES)
    assert kind(host.admit(T._TOOL_REQUEST_BYTES + 1)) == "too_large"
    assert host.admit(T._TOOL_REQUEST_BYTES) is None
    assert kind(host(padded(frame("list"), T._TOOL_REQUEST_BYTES))) is None
    assert len(parses) == 3

    # The raw path admits in __call__ and counts the same way.
    host = T._ToolHost([], max_bytes=100)
    assert kind(host(padded(frame("list"), 60))) is None
    assert kind(host(padded(frame("list"), 60))) == "budget_exceeded"
    assert len(parses) == 4

    # The frame limit comes first; 0 refuses every non-empty frame.
    host = T._ToolHost([], max_calls=1, max_bytes=0)
    first, second = host.admit(26), host.admit(26)
    assert kind(first) == kind(second) == "budget_exceeded"
    assert "bytes" in answer(first)["error"]["message"]
    assert "tool frames" in answer(second)["error"]["message"]
    host = T._ToolHost([], max_bytes=0)
    assert kind(host(b"")) == "protocol"  # an empty frame is admitted, and spends nothing
    assert kind(host(frame("list"))) == "budget_exceeded"
    assert len(parses) == 5

    # None, the private default, is no limit.
    host = T._ToolHost([], max_calls=None)
    one = padded(frame("list"), 1000)
    for _ in range(2000):
        assert kind(host(one)) is None
    assert len(parses) == 2005


def test_the_tool_list_is_encoded_once(monkeypatch) -> None:
    """Spec 060, criterion 5 (its pre-build review, F1): the descriptors are encoded at the first
    `list` frame and the frame's id spliced in, byte for byte what encoding the whole answer
    gives; a list over the answer cap is `too_large` on every `list` frame."""
    encodes: list[int] = []
    real = T._encode

    def counting(body: dict) -> bytes:
        encodes.append(1)
        return real(body)

    monkeypatch.setattr(T, "_encode", counting)
    tools = [*counting_tools(Counter()), tool(square)]
    host = T._ToolHost(tools, max_calls=None)
    ids = [1, 2, 3, 4, None]
    raws = [host(frame("list", id=i)) for i in ids[:4]]
    raws.append(host(json.dumps({"v": 1, "op": "list"}).encode()))
    assert len(encodes) == 1, len(encodes)
    descriptors = [t.descriptor() for t in tools]
    for raw, i in zip(raws, ids, strict=True):
        assert raw == real({"v": 1, "id": i, "ok": True, "tools": descriptors}), i
    monkeypatch.setattr(T, "_TOOL_RESPONSE_BYTES", 100)
    small = T._ToolHost(tools, max_calls=None)
    assert [kind(small(frame("list", id=i))) for i in (1, 2)] == ["too_large", "too_large"]


def _list_tools() -> list[Tool]:
    return [*counting_tools(Counter()), tool(square)]


def _list_frame(i: int | None) -> bytes:
    return frame("list", id=i) if i is not None else json.dumps({"v": 1, "op": "list"}).encode()


def test_an_oversized_tool_list_is_refused_before_it_is_built(monkeypatch) -> None:
    """Spec 075, criterion 4 (spec 060's build review, N1): a list over the answer cap is
    refused from its length, on every `list` frame, and its answer is never built."""
    builds: list = []
    real = T._ToolHost._list_answer

    def counting(self: Any, frame_id: Any) -> bytes:
        builds.append(frame_id)
        return real(self, frame_id)

    monkeypatch.setattr(T._ToolHost, "_list_answer", counting)
    monkeypatch.setattr(T, "_TOOL_RESPONSE_BYTES", 100)
    host = T._ToolHost(_list_tools(), max_calls=None)
    for i in (1, 2, None):
        a = answer(host(_list_frame(i)))
        refused = {"kind": "too_large", "message": "the tool list is over the 16 MiB cap"}
        assert (a["id"], a["ok"], a["error"]) == (i, False, refused), i
    outcomes = [(o.op, o.tool, o.outcome) for o in host.record.outcomes]
    assert outcomes == [("list", None, "too_large")] * 3
    assert builds == []
    monkeypatch.setattr(T, "_TOOL_RESPONSE_BYTES", 16 << 20)
    host = T._ToolHost(_list_tools(), max_calls=None)
    assert [kind(host(_list_frame(i))) for i in (1, 2)] == [None, None]
    assert builds == [1, 2]


def test_the_tool_list_cap_is_exact_for_each_id(monkeypatch) -> None:
    """Spec 075, criterion 5: the refusal from the length keeps the cap to the byte, for each
    frame's own id (`null` is 4 bytes, an id 1 to 16 digits)."""
    tools = _list_tools()
    descriptors = [t.descriptor() for t in tools]

    def length(i: int | None) -> int:
        return len(T._encode({"v": 1, "id": i, "ok": True, "tools": descriptors}))

    monkeypatch.setattr(T, "_TOOL_RESPONSE_BYTES", length(9))
    host = T._ToolHost(tools, max_calls=None)
    nine = host(_list_frame(9))
    assert (kind(nine), len(nine)) == (None, length(9))
    assert kind(host(_list_frame(10))) == "too_large"
    assert kind(host(_list_frame(None))) == "too_large"
    assert kind(host(_list_frame(0))) is None
    monkeypatch.setattr(T, "_TOOL_RESPONSE_BYTES", length(9) - 1)
    host = T._ToolHost(tools, max_calls=None)
    assert [kind(host(_list_frame(i))) for i in (9, 0)] == ["too_large", "too_large"]
    # The length the refusal reads is the length of the answer that would be built (last, so
    # that on main, which has no `_list_length`, the boundary rows above are seen to pass).
    monkeypatch.setattr(T, "_TOOL_RESPONSE_BYTES", 16 << 20)
    host = T._ToolHost(tools, max_calls=None)
    for i in (None, 0, 9, 10, 2**53 - 1):
        assert host._list_length(i) == len(host._list_answer(i)) == length(i), i
