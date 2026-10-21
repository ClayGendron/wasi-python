"""The tool protocol's guest half: the recipe package `recipes/guest/host/`, loaded on
the host's Python under a private name, with a fake `_host` whose `call` routes each frame to a
frame host (or to a stand-in that is not one). Nothing here measures time."""

from __future__ import annotations

import ast
import importlib.util
import inspect
import itertools
import json
import numbers
import pydoc
import sys
import types
from collections.abc import Callable
from typing import Any, Literal

import pytest

from harness import paths
from wasi_python import _tool_host as H
from wasi_python import tools as T
from wasi_python.tools import ToolDenied, ToolError, tool

PACKAGE = paths.REPO / "recipes" / "guest" / "host"
_names = itertools.count()


class Door:
    """A fake `_host`: each frame goes to `answer`, and is kept."""

    def __init__(self, answer: Callable[[bytes], bytes]) -> None:
        self.answer = answer
        self.frames: list[dict] = []

    def call(self, frame: bytes) -> bytes:
        assert isinstance(frame, bytes)
        self.frames.append(json.loads(frame))
        return self.answer(frame)


@pytest.fixture
def load(monkeypatch):
    """`load(door)` imports the package and its `tools` under a fresh private name, with `door`
    as `_host`; it returns (package, tools). A door of None stands for a run with no host."""
    loaded: list[str] = []

    def run(door: Any) -> tuple[types.ModuleType, types.ModuleType]:
        fake = types.ModuleType("_host")

        def call(frame: bytes) -> bytes:
            if door is None:
                raise ConnectionRefusedError("no host is bound to the door")
            return door.call(frame)

        fake.call = call
        monkeypatch.setitem(sys.modules, "_host", fake)
        name = f"_guest_host_{next(_names)}"
        spec = importlib.util.spec_from_file_location(
            name, PACKAGE / "__init__.py", submodule_search_locations=[str(PACKAGE)]
        )
        package = importlib.util.module_from_spec(spec)
        sys.modules[name] = package
        loaded.append(name)
        spec.loader.exec_module(package)
        return package, importlib.import_module(f"{name}.tools")

    yield run
    for name in loaded:
        for key in [k for k in sys.modules if k == name or k.startswith(name + ".")]:
            del sys.modules[key]


def lookup_region(
    code: str,
    level: Literal["country", "region"] = "region",
    year: int = 2026,
    note: str | None = None,
) -> dict[str, Any]:
    """Look up a sales region by its code.

    Args:
        code: The region code, such as "EMEA".
        year: The fiscal year.
    """
    return {"code": code, "level": level, "year": year, "note": note}


def reverse(data: bytes) -> bytes:
    """Reverse some bytes."""
    return data[::-1]


def json_(value: int) -> int:
    """A tool whose name is a module the package itself uses."""
    return value + 1


def describe(n: Any) -> str:
    """Name what arrived."""
    return type(n).__name__


def refuse(why: str) -> None:
    """Refuse."""
    raise ToolDenied(why)


def fail(why: str) -> None:
    """Fail."""
    raise ToolError(why)


def offered() -> list:
    return [
        tool(lookup_region, read_only=True),
        tool(reverse),
        tool(json_, name="json"),
        tool(describe),
        tool(refuse),
        tool(fail),
    ]


class Scalar:
    """A numpy-like integer: registered with numbers.Integral, not an int."""

    def __init__(self, n: int) -> None:
        self.n = n

    def __int__(self) -> int:
        return self.n

    __index__ = __int__


numbers.Integral.register(Scalar)


class Array:
    def tolist(self) -> list:
        return [1, 2]


class Frame:
    def to_dict(self, orient: str) -> list:
        return [{"a": 1}]


def test_the_guest_package_speaks_the_hosts_protocol(load) -> None:
    host = H._ToolHost(offered())
    door = Door(host)
    package, tools = load(door)
    assert package.PROTOCOL == T.PROTOCOL == 1
    assert door.frames == [{"v": 1, "id": 1, "op": "list"}]  # one discovery frame

    # Signatures, docstrings, descriptors and __all__.
    assert tools.__all__ == ["lookup_region", "reverse", "json", "describe", "refuse", "fail"]
    fn = tools.lookup_region
    assert str(inspect.signature(fn)) == (
        "(code: str, level: Literal['country', 'region'] = 'region', year: int = 2026, "
        "note: str | None = None) -> dict[str, Any]"
    )
    assert fn.__doc__ == (
        "Look up a sales region by its code.\n\nArgs:\n"
        '    code: The region code, such as "EMEA".\n    level\n    year: The fiscal year.\n'
        "    note"
    )
    assert fn.__name__ == "lookup_region" and fn.__module__ == tools.__name__
    assert fn.descriptor == offered()[0].descriptor()
    fn.descriptor["name"] = "changed"  # a copy: the call still goes by its own name
    assert fn("EMEA")["code"] == "EMEA"
    public = sorted(n for n in vars(tools) if not n.startswith("_"))
    assert public == sorted(tools.__all__)
    namespace: dict = {}
    exec(f"from {tools.__name__} import *", namespace)
    assert sorted(n for n in namespace if n != "__builtins__") == sorted(tools.__all__)
    assert "lookup_region" in pydoc.render_doc(tools)

    # Positional arguments go by keyword; an omitted optional argument is not sent.
    assert fn("EMEA", "country") == {
        "code": "EMEA",
        "level": "country",
        "year": 2026,
        "note": None,
    }
    assert door.frames[-1] == {
        "v": 1,
        "id": door.frames[-1]["id"],
        "op": "call",
        "tool": "lookup_region",
        "args": {"code": "EMEA", "level": "country"},
    }
    ids = [f["id"] for f in door.frames]
    assert ids == list(range(1, len(ids) + 1))

    # A tool named json works; numpy-like scalars encode; bytes round-trip.
    assert tools.json(41) == 42
    assert tools.describe(Scalar(3)) == "int"
    assert door.frames[-1]["args"] == {"n": 3}
    assert tools.describe([Scalar(1), (2, 3), {"k": 1.5}]) == "list"
    assert door.frames[-1]["args"] == {"n": [1, [2, 3], {"k": 1.5}]}
    with pytest.raises(package.ToolArgumentError, match="bytes are accepted only"):
        tools.describe({"k": b"\x00"})  # encoded as $bytes, refused by the host: the hint is Any
    assert door.frames[-1]["args"] == {"n": {"k": {"$bytes": "AA=="}}}
    assert tools.reverse(b"abc\x00\xff") == b"\xff\x00cba"
    assert tools.reverse(bytearray(b"ab")) == b"ba"

    # Refused before any frame: a dict that would read as bytes, a value with no JSON form, a
    # binding error.
    sent = len(door.frames)
    for bad, words in [
        ({"$bytes": "QQ=="}, "$bytes"),
        ({"$bytes": "QQ==", "x": 1}, "$bytes"),
        ({1: "a"}, "key"),
        ({1, 2}, "set"),
        (float("nan"), "finite"),
        (Array(), ".tolist()"),
        (Frame(), '.to_dict("records")'),
        ("\ud800", "surrogate"),
    ]:
        with pytest.raises(package.ToolArgumentError) as refused:
            tools.describe(bad)
        assert words in str(refused.value), (bad, str(refused.value))
        assert isinstance(refused.value, TypeError)
    for call in [lambda: fn(), lambda: fn("a", code="b"), lambda: fn("a", zone=1)]:
        with pytest.raises(package.ToolArgumentError):
            call()
    assert len(door.frames) == sent

    # Failed answers raise the class for their kind.
    with pytest.raises(package.ToolDenied, match="not today") as denied:
        tools.refuse("not today")
    assert isinstance(denied.value, PermissionError) and denied.value.kind == "denied"
    with pytest.raises(package.ToolError, match="broke") as failed:
        tools.fail("broke")
    assert type(failed.value) is package.ToolError and failed.value.kind == "tool_error"
    with pytest.raises(package.ToolArgumentError) as wrong:
        tools.lookup_region(5)
    assert wrong.value.kind == "invalid_arguments"

    # An unknown attribute lists the offered names.
    with pytest.raises(AttributeError, match="lookup_region"):
        tools.nope  # noqa: B018


CLASS_OF_KIND = {
    "protocol": "ToolProtocolError",
    "unknown_tool": "ToolArgumentError",
    "invalid_arguments": "ToolArgumentError",
    "denied": "ToolDenied",
    "tool_error": "ToolError",
    "timeout": "ToolTimeout",
    "cancelled": "ToolCancelled",
    "too_large": "ToolTooLarge",
    "budget_exceeded": "ToolBudgetExceeded",
}
BASES = {
    "ToolError": (Exception,),
    "ToolDenied": (PermissionError,),
    "ToolArgumentError": (TypeError,),
    "ToolTimeout": (TimeoutError,),
    "ToolCancelled": (),
    "ToolTooLarge": (),
    "ToolBudgetExceeded": (),
    "ToolProtocolError": (),
}


def test_every_kind_maps_to_its_class(load) -> None:
    host = H._ToolHost([tool(describe)])
    kinds = iter([*T._KINDS, "a_kind_from_later"])

    def answer(frame: bytes) -> bytes:
        request = json.loads(frame)
        if request["op"] == "list":
            return host(frame)
        error = {"kind": next(kinds), "message": "said"}
        return json.dumps({"v": 1, "id": request["id"], "ok": False, "error": error}).encode()

    package, tools = load(Door(answer))
    assert set(CLASS_OF_KIND) == set(T._KINDS)
    assert set(package.__all__) == {"PROTOCOL", *BASES}
    for name, bases in BASES.items():
        cls = getattr(package, name)
        assert issubclass(cls, package.ToolError) and all(issubclass(cls, b) for b in bases)
    for kind in T._KINDS:
        with pytest.raises(package.ToolError) as raised:
            tools.describe(1)
        assert type(raised.value).__name__ == CLASS_OF_KIND[kind], kind
        assert (raised.value.kind, str(raised.value)) == (kind, "said")
    with pytest.raises(package.ToolError) as raised:
        tools.describe(1)
    assert type(raised.value) is package.ToolError and raised.value.kind == "a_kind_from_later"


def test_an_answer_that_does_not_match_is_a_protocol_error(load) -> None:
    host = H._ToolHost([tool(describe)])
    replies: list[Any] = []

    def answer(frame: bytes) -> bytes:
        if json.loads(frame)["op"] == "list":
            return host(frame)
        return replies.pop(0)

    package, tools = load(Door(answer))
    for reply in [
        b"not json",
        b'{"v":2,"id":2,"ok":true,"value":1}',
        b'{"v":1,"id":999,"ok":true,"value":1}',
        b'{"v":1,"id":2,"ok":"yes"}',
        b'{"v":1,"id":2,"ok":true,"value":{"$bytes":"!!"}}',
        b"[1]",
    ]:
        replies.append(reply)
        with pytest.raises(package.ToolProtocolError):
            tools.describe(1)
    # A null id matches: an answer refused from the length alone has none.
    replies.append(b'{"v":1,"id":null,"ok":true,"value":{"$bytes":"QQ==","x":1}}')
    assert tools.describe(1) == {"$bytes": "QQ==", "x": 1}


def test_the_guest_refuses_what_the_host_would_refuse_as_protocol(load) -> None:
    """Arguments the frame rules would refuse (nested past 62 levels inside args, an
    integer literal over 64 characters) are a ToolArgumentError with no frame sent; at the bound
    they reach the tool."""
    host = H._ToolHost([tool(describe)])
    door = Door(host)
    package, tools = load(door)

    def nested(levels: int, leaf: Any = 0) -> Any:
        value: Any = leaf
        for _ in range(levels):
            value = [value]
        return value

    assert tools.describe(nested(62)) == "list"  # 64 levels in the frame: accepted
    assert tools.describe({"k": nested(61)}) == "dict"
    assert tools.describe(9 * 10**63) == "int"  # 64 digits
    assert tools.describe(-(9 * 10**62)) == "int"  # 64 characters with the sign
    sent = len(door.frames)
    too_deep = [nested(63), {"k": nested(62)}, nested(62, b"x")]  # bytes cross as an object
    too_long = [10**64, -(10**63), 10**5000, Scalar(10**70)]
    for bad in too_deep + too_long:
        with pytest.raises(package.ToolArgumentError):
            tools.describe(bad)
    assert len(door.frames) == sent


def test_a_loose_bytes_answer_is_a_protocol_error(load) -> None:
    """The guest decodes $bytes strictly, as the host does."""
    host = H._ToolHost([tool(describe)])
    replies: list[bytes] = []

    def answer(frame: bytes) -> bytes:
        request = json.loads(frame)
        if request["op"] == "list":
            return host(frame)
        return replies.pop(0) % request["id"]

    package, tools = load(Door(answer))
    for loose in [b'"QQ"', b'"Q Q=="', b'"QQ==QQ=="']:
        replies.append(b'{"v":1,"id":%d,"ok":true,"value":{"$bytes":' + loose + b"}}")
        with pytest.raises(package.ToolProtocolError):
            tools.describe(1)
    replies.append(b'{"v":1,"id":%d,"ok":true,"value":{"$bytes":"QQ=="}}')
    assert tools.describe(1) == b"A"


def test_a_descriptor_that_cannot_make_a_signature_takes_keywords(load) -> None:
    """From a host that is not this runner: a `from` property gets (**kwargs), never a broken
    import."""
    descriptor = {
        "name": "search",
        "description": "Search.",
        "inputSchema": {"type": "object", "properties": {"from": {"type": "string"}}},
    }

    def answer(frame: bytes) -> bytes:
        request = json.loads(frame)
        if request["op"] == "list":
            return json.dumps({"v": 1, "id": 1, "ok": True, "tools": [descriptor]}).encode()
        body = {"v": 1, "id": request["id"], "ok": True, "value": request["args"]}
        return json.dumps(body).encode()

    door = Door(answer)
    _, tools = load(door)
    assert str(inspect.signature(tools.search)) == "(**kwargs)"
    assert tools.search(**{"from": "x"}) == {"from": "x"}
    assert door.frames[-1]["args"] == {"from": "x"}


def test_without_the_protocol_the_import_says_why(load) -> None:
    with pytest.raises(ImportError, match="this run has no tools: the embedder passed none"):
        load(None)
    with pytest.raises(ImportError, match="not protocol 1"):
        load(Door(lambda frame: b"pong"))
    with pytest.raises(ImportError, match="budget_exceeded"):
        load(Door(H._ToolHost([], max_calls=0)))
    with pytest.raises(ImportError, match="not protocol 1"):
        bad = {"v": 1, "id": 1, "ok": True, "tools": [{"name": "_private"}]}
        load(Door(lambda frame: json.dumps(bad).encode()))
    package, tools = load(Door(H._ToolHost([])))  # no tools offered: an empty module
    assert tools.__all__ == []


# -------------------------------------------------------------------------------------------------
# 10. Stubs match the guest's signatures.


def every_hint(
    s: str,
    i: int,
    f: float,
    b: bool,
    n: None,
    data: bytes,
    many: list[int],
    pair: tuple[str, ...],
    table: dict[str, float],
    pick: Literal["a", 1, True, None],
    either: int | str,
    maybe: list[bytes] | None,
    anything: Any,
    nested: dict[str, list[dict[str, int | None]]],
    blob: bytes = b"\x00\x01",
    items: list[int] = [1, 2],  # noqa: B006
    mode: Literal["fast", "slow"] = "fast",
    ratio: float = 0.5,
    opt: str | None = None,
) -> list[dict[str, Any]]:
    """Every hint tool() maps.

    Args:
        s: A string.
        nested: Deep.
    """
    return []


def nothing() -> None:
    pass


def test_stubs_match_the_guest_signatures(load) -> None:
    given = [
        tool(every_hint),
        tool(nothing),
        tool(lookup_region),
        tool(
            describe,
            name="search",
            input_schema={
                "type": "object",
                "properties": {"q": {"type": "string"}, "limit": {"type": "integer"}},
                "required": ["q"],
            },
        ),
    ]
    _, tools = load(Door(H._ToolHost(given)))
    text = T.stubs(given)
    lines = text.splitlines()
    assert lines[0] == "from host import tools"
    defs = [line for line in lines if line.startswith("def ")]
    want = [f"def {t.name}{inspect.signature(getattr(tools, t.name))}:" for t in given]
    assert defs == want
    assert defs[3] == "def search(q: str, limit: int = ...) -> str:"
    assert "blob: bytes = b'\\x00\\x01'" in defs[0]
    module = ast.parse(text)  # the stubs are Python
    docs = {f.name: ast.get_docstring(f) for f in module.body if isinstance(f, ast.FunctionDef)}
    assert docs == {t.name: getattr(tools, t.name).__doc__ for t in given}
