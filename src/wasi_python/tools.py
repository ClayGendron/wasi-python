"""Tools: host functions an embedder offers a guest, and the protocol that carries their calls.

A tool is a host function with a name, a description and an input schema (JSON Schema)::

    from wasi_python.tools import tool, ToolError

    @tool(read_only=True)
    def lookup_region(code: str, year: int = 2026) -> dict:
        \"\"\"Look up a sales region by its code.

        Args:
            code: The region code, such as "EMEA".
        \"\"\"
        if code not in REGIONS:
            raise ToolError(f"no region {code!r}")  # the guest reads this message
        return REGIONS[code]

The guest calls it as `from host import tools; tools.lookup_region("EMEA")`, and
`run(tools=[lookup_region])` offers it. Between the two run JSON frames through the door.
`import wasi_python` does not import this module.

`PROTOCOL` is the number of the protocol this host speaks. The rules for its frames, the schema
subset and the bounds are the protocol's own, not the host Python's, so an answer is the same
on every host; they change only with `PROTOCOL` (README.md, "The tool protocol").
"""

# The tool protocol in three modules, importing one way. `_tool_schema` holds the schema rules:
# what a tool's schema may say, how one is derived from a signature, and how a value is checked.
# This module holds the public surface, which imports them. `_tool_host` holds the host side of
# a call, the frames, the work, the tool loop, the bound and the frame host, which imports both.

from __future__ import annotations

import binascii
import contextvars
import copy
import functools
import inspect
import keyword
import math
import numbers
import re
import types
import typing
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from . import _tool_schema
from ._tool_schema import _Json, _KeySets

PROTOCOL = 1
_KINDS = (
    "protocol",
    "unknown_tool",
    "invalid_arguments",
    "denied",
    "tool_error",
    "timeout",
    "cancelled",
    "too_large",
    "budget_exceeded",
)

_WRAPPER_DEPTH = 64  # partials, methods and __wrapped__ links walked to find bound keywords
_PARTIALMETHOD = ("__partialmethod__", "_partialmethod")  # its mark: Python 3.13 on, and before
_C_SLOTS = (  # a type's __call__ written in C: the walk to bound keywords stops there
    types.WrapperDescriptorType,
    types.MethodWrapperType,
    types.MethodDescriptorType,
    types.BuiltinFunctionType,
    types.ClassMethodDescriptorType,
)

_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,63}")
_HEADINGS = ("Args:", "Arguments:", "Returns:", "Raises:")
_HINTS = (
    ("read_only", "readOnlyHint"),
    ("destructive", "destructiveHint"),
    ("idempotent", "idempotentHint"),
    ("open_world", "openWorldHint"),
)


class ToolError(Exception):
    """Raised by a tool to fail with a message the guest reads (`tool_error`), or by a gate to
    refuse with one (`denied`). Any other exception crosses only as "(internal error)"."""


class ToolDenied(ToolError):
    """Raised by a gate or a capability to refuse a call; its message crosses (`denied`)."""


# -------------------------------------------------------------------------------------------------
# Tools


_MAKING = contextvars.ContextVar("wasi_python_tools_making", default=False)


@dataclass(frozen=True, eq=False)
class Tool:
    """A host function offered to the guest, made only by `tool()`. Immutable; compared and
    hashed by identity. Calling it calls the function.

    Attributes:
        name: The name the guest calls it by.
        description: What the guest is told it does.
        fn: The function it calls.
        validates_input: Whether schema keywords outside the protocol's subset are let through,
            unchecked, for a tool that checks its own input.
        timeout_s: The longest one call may run, in seconds; `None` for no bound beyond the
            run's own.
        read_only: A label shown to the guest as MCP's readOnlyHint; it grants nothing.
        destructive: A label shown as MCP's destructiveHint; it grants nothing.
        idempotent: A label shown as MCP's idempotentHint; it grants nothing.
        open_world: A label shown as MCP's openWorldHint; it grants nothing.
    """

    name: str
    description: str
    fn: Callable[..., Any] = field(repr=False)
    _input_schema: _Json = field(repr=False)
    _output_schema: _Json | None = field(repr=False)
    validates_input: bool = False
    timeout_s: float | None = None
    read_only: bool = False
    destructive: bool = False
    idempotent: bool = False
    open_world: bool = False
    _keysets: _KeySets = field(default_factory=dict, repr=False)
    _fixed: frozenset[str] = field(default=frozenset(), repr=False)  # keywords a partial binds

    def __post_init__(self) -> None:
        # Only tool() makes one: not a direct call, and not dataclasses.replace.
        if not _MAKING.get():
            raise TypeError("a Tool is made by tool(), which describes and vets it")

    @property
    def input_schema(self) -> dict:  # type: ignore[type-arg]  # the public API text says `dict`
        """A copy of the vetted input schema."""
        return copy.deepcopy(self._input_schema)

    @property
    def output_schema(self) -> dict | None:  # type: ignore[type-arg]  # as the public API text
        """A copy of the output schema, or None. It is shown, never validated."""
        return copy.deepcopy(self._output_schema)

    def descriptor(self) -> dict:  # type: ignore[type-arg]  # as the public API text
        """The tool in MCP's field names: name, description, inputSchema, and outputSchema and
        annotations when there are any. A fresh copy each time."""
        d: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }
        if self._output_schema is not None:
            d["outputSchema"] = self.output_schema
        hints = {mcp: True for attr, mcp in _HINTS if getattr(self, attr)}
        if hints:
            d["annotations"] = hints
        return d

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Call the function with these arguments, on this thread, unchecked."""
        return self.fn(*args, **kwargs)


@dataclass(frozen=True)
class ToolCall:
    """What a gate sees of one tool call.

    Attributes:
        seq: The frame's number in this call, from 1.
        tool: The tool the guest called.
        arguments: A deep copy of the validated and decoded arguments; the tool gets its own.
        request_bytes: The frame's length in bytes.
    """

    seq: int
    tool: Tool
    arguments: dict[str, Any]
    request_bytes: int


@dataclass(frozen=True)
class ToolOutcome:
    """One frame, as the record lists it. Nothing in it measures time.

    Attributes:
        seq: The frame's number in this call, from 1.
        op: "list", "call", or `None` when the frame was not read.
        tool: The tool's name, or the name the guest gave, cut to 64 characters.
        outcome: "ok", or one of the protocol's kinds of failure (README.md, "The tool
            protocol").
        message: What the guest was told on a failure.
        request_bytes: The frame's length in bytes.
        response_bytes: The answer's length in bytes.
        fault: An exception not meant for the guest: its type and first line.
        abandoned: Whether the tool still ran when the guest was answered.
    """

    seq: int
    op: str | None
    tool: str | None
    outcome: str
    message: str | None
    request_bytes: int
    response_bytes: int
    fault: str | None = None
    abandoned: bool = False


@dataclass(frozen=True)
class ToolRecord:
    """Every frame of one call counted, the first 1,000 listed.

    Attributes:
        frames: Every frame the guest sent.
        outcomes: The first 1,000 frames, each a `ToolOutcome`.
        unlisted: How many frames are counted but not listed.
        abandoned: Every call answered while its tool ran on, listed or not, so a guest cannot
            hide a tool still running with your authority behind 1,000 cheap frames.
    """

    # abandoned: the tool calls left running past their answer

    frames: int
    outcomes: tuple[ToolOutcome, ...]
    unlisted: int
    abandoned: int = 0


# The two shapes a type checker sees: `fn` positionally, or none.
@typing.overload
def tool(
    fn: Callable[..., Any],
    /,
    *,
    name: str | None = None,
    description: str | None = None,
    input_schema: Any = None,
    validates_input: bool = False,
    timeout_s: float | None = None,
    read_only: bool = False,
    destructive: bool = False,
    idempotent: bool = False,
    open_world: bool = False,
) -> Tool: ...


@typing.overload
def tool(
    fn: None = None,
    /,
    *,
    name: str | None = None,
    description: str | None = None,
    input_schema: Any = None,
    validates_input: bool = False,
    timeout_s: float | None = None,
    read_only: bool = False,
    destructive: bool = False,
    idempotent: bool = False,
    open_world: bool = False,
) -> Callable[[Callable[..., Any]], Tool]: ...


def tool(
    fn: Callable[..., Any] | None = None,
    *,
    name: str | None = None,
    description: str | None = None,
    input_schema: Any = None,
    validates_input: bool = False,
    timeout_s: float | None = None,
    read_only: bool = False,
    destructive: bool = False,
    idempotent: bool = False,
    open_world: bool = False,
) -> Any:
    """Describe a function as a tool: `@tool`, `@tool(...)` with arguments, or `tool(fn, ...)`.

    The input schema is derived from the type hints and a Google-style `Args:` section, or
    given. Every schema is vetted against the protocol's subset. The four hints are your
    labels, shown to the guest as MCP's annotations; they grant nothing.

    The function may be an `async def`, or return an awaitable: the runner awaits it on the
    call's tool loop (the event loop that awaits `run_async`, or under `run` a loop of the
    call's own), never starts it once its call has been answered, and cancels it when its call
    ends. An async generator function is refused: a tool answers each call once. Calling the
    `Tool` on the host returns what the function returns, a coroutine for an `async def`.

    Args:
        fn: The function. Without it, `tool(...)` returns a decorator.
        name: The name the guest calls it by; by default the function's own.
        description: What the guest is told it does; by default the docstring up to its first
            section heading.
        input_schema: The input schema instead of the derived one: a dict whose root is an
            object, or anything with `model_json_schema()`.
        validates_input: Let schema keywords outside the protocol's subset through, unchecked,
            for a tool that checks its own input.
        timeout_s: The longest one call may run, in seconds; `None` for no bound beyond the
            run's own.
        read_only: Shown to the guest as MCP's readOnlyHint.
        destructive: Shown to the guest as MCP's destructiveHint.
        idempotent: Shown to the guest as MCP's idempotentHint.
        open_world: Shown to the guest as MCP's openWorldHint.

    Returns:
        The `Tool`, or, without `fn`, a decorator that makes one.

    Raises:
        TypeError: An argument has the wrong type, the function is an async generator
            function, or a type hint has no schema.
        ValueError: A name or a schema the protocol does not allow.
    """
    # timeout_s: the tool's own deadline, in seconds
    options = dict(
        name=name,
        description=description,
        input_schema=input_schema,
        validates_input=validates_input,
        timeout_s=timeout_s,
        read_only=read_only,
        destructive=destructive,
        idempotent=idempotent,
        open_world=open_world,
    )
    if fn is None:
        return lambda f: _make(f, **options)
    return _make(fn, **options)


def _make(
    fn: Any,
    *,
    name: Any,
    description: Any,
    input_schema: Any,
    validates_input: Any,
    timeout_s: Any,
    **hints: Any,
) -> Tool:
    if isinstance(fn, Tool) or not callable(fn):
        raise TypeError(f"tool() takes a function; got {type(fn).__name__}")
    for flag, value in [("validates_input", validates_input), *hints.items()]:
        if not isinstance(value, bool):
            raise TypeError(f"tool(): {flag} must be True or False; got {value!r}")
    if name is None:
        name = getattr(fn, "__name__", None)
        if name is None:
            raise TypeError(f"tool(): {type(fn).__name__} has no __name__; pass name=")
    if not isinstance(name, str):
        raise TypeError(f"tool(): name must be a str; got {name!r}")
    if not _NAME.fullmatch(name) or keyword.iskeyword(name):
        raise ValueError(
            f"tool(): the name {name!r} must be a letter, then up to 63 letters, digits or "
            "underscores, and not a Python keyword"
        )
    if _is_async_generator(fn):
        raise TypeError(f"{name}: an async generator streams; protocol 1 answers each call once")
    timeout = _timeout(name, timeout_s)
    fixed = _bound_keywords(name, fn)
    doc = _doc(fn)
    if description is None:
        description = _summary(doc)
    elif not isinstance(description, str):
        raise TypeError(f"{name}: description must be a str; got {description!r}")
    try:
        hints_of = _type_hints(name, fn)
    except TypeError:
        if input_schema is None:
            raise
        hints_of = {}  # the schema is given: the hints only add an output schema
    if input_schema is None:
        schema = _tool_schema._derived(name, fn, hints_of, _args_section(doc), fixed)
    else:
        schema = _given(name, input_schema, fixed)
    nodes = _tool_schema._vet(name, schema, validates_input)
    output = None
    if "return" in hints_of:
        try:
            output = _tool_schema._schema_of(hints_of["return"], "return")
        except (TypeError, ValueError):
            output = None  # a return hint that does not map: no output schema
    making = _MAKING.set(True)
    try:
        return Tool(
            name=name,
            description=description,
            fn=fn,
            _input_schema=schema,
            _output_schema=output,
            validates_input=validates_input,
            timeout_s=timeout,
            _keysets=_tool_schema._keysets(nodes),
            _fixed=fixed,
            **hints,
        )
    finally:
        _MAKING.reset(making)


def _given(name: str, input_schema: object, fixed: frozenset[str]) -> _Json:
    """A given input schema as plain JSON, before it is vetted: a model's `model_json_schema()`
    or the mapping itself, copied. It may not name a keyword a partial binds, which the guest
    could never set."""
    maker = getattr(input_schema, "model_json_schema", None)
    given = maker() if callable(maker) else input_schema
    if not isinstance(given, Mapping):
        raise TypeError(
            f"{name}: input_schema must be a dict, or have model_json_schema(); "
            f"got {type(input_schema).__name__}"
        )
    schema: _Json = _tool_schema._plain(given, f"{name}: input_schema", 0)
    named = sorted(fixed & _top_level_names(schema))
    if named:
        raise ValueError(
            f"{name}: input_schema names {', '.join(map(repr, named))}, which the partial "
            "binds; a bound keyword is fixed, so the guest cannot set it: leave it out"
        )
    return schema


def _top_level_names(schema: _Json) -> set[str]:
    """The names a frame could send at the arguments' top level: the root's `properties`, and
    those of each root `anyOf` and `oneOf` branch and of a branch's `$ref` target in the
    schema's own `$defs` or `definitions`, through branches of branches. A property's own
    schema, `items` and `additionalProperties` describe another object, whose key of the same
    name is its own, so none is entered. `allOf`, and what an unchecked schema adds, is left
    to the frame, which refuses a bound keyword among the top-level keys whatever the schema.
    Each `$ref` target is entered once, so a cycle, which vetting then refuses, ends."""
    names: set[str] = set()
    entered: set[str] = set()
    todo: list[Any] = [schema]
    while todo:
        node = todo.pop()
        if not isinstance(node, dict):
            continue
        props = node.get("properties")
        if isinstance(props, dict):
            names.update(props)
        for key in ("anyOf", "oneOf"):
            branches = node.get(key)
            if isinstance(branches, list):
                todo.extend(branches)
        ref = node.get("$ref")
        if isinstance(ref, str) and ref not in entered:
            entered.add(ref)
            todo.append(_tool_schema._resolve(schema, ref))
    return names


def _is_async_generator(fn: Any) -> bool:
    """Whether calling `fn` makes an async generator, read through `partial`s and at an
    object's `__call__`."""
    while isinstance(fn, functools.partial):
        fn = fn.func
    if inspect.isasyncgenfunction(fn):
        return True
    if not (inspect.isfunction(fn) or inspect.ismethod(fn)):
        return callable(fn) and inspect.isasyncgenfunction(type(fn).__call__)
    return False


def _bound_keywords(name: str, fn: Any) -> frozenset[str]:
    """The keywords a `functools.partial` binds, wherever `inspect.signature` or a call may
    meet one on its way to the function: the partial, nested partials, a bound method's
    function, a `__wrapped__` chain, a callable object's `__call__`, and a class's construction
    path (its metaclass's `__call__`, its `__new__` and its `__init__`), to any depth. Each is
    fixed: left out of the derived schema and refused in a frame, so the guest neither reads its
    value nor sets it. A `functools.partialmethod` met other than through an instance is
    refused."""
    found: set[str] = set()
    todo = [fn]  # one worklist, and one budget of steps across all its branches
    steps = 0
    while todo:
        steps += 1
        if steps > _WRAPPER_DEPTH:
            raise TypeError(
                f"{name}: its wrappers nest deeper than {_WRAPPER_DEPTH}; pass a function"
            )
        target = todo.pop()
        if isinstance(target, functools.partialmethod):
            # Met only as a class attribute read statically, on the construction path, which
            # the interpreter reaches through the instance it makes: read as it binds there.
            found.update(target.keywords)
            todo.append(target.func)
        elif any(getattr(target, a, None) is not None for a in _PARTIALMETHOD):
            raise TypeError(
                f"{name}: a functools.partialmethod is described only through an instance "
                "(obj.method); or bind its keywords with a closure or a functools.partial"
            )
        elif isinstance(target, functools.partial):
            found.update(target.keywords)
            todo.append(target.func)
        elif isinstance(target, (types.MethodType, staticmethod, classmethod)):
            todo.append(target.__func__)
        elif isinstance(target, type):
            # A class runs as type.__call__ does: its metaclass's __call__, then the __new__
            # and __init__ its MRO holds, read statically, whatever that __call__ says, since a
            # metaclass that delegates to type.__call__ still runs them with the guest's
            # keywords. C's slots hold no partial and end there.
            call = type(target).__call__
            todo.extend(
                part
                for part in (
                    call,
                    inspect.getattr_static(target, "__new__", None),
                    inspect.getattr_static(target, "__init__", None),
                )
                if part is not None and not isinstance(part, _C_SLOTS)
            )
        elif getattr(target, "__wrapped__", None) is not None:
            todo.append(target.__wrapped__)
        elif not (inspect.isfunction(target) or inspect.isbuiltin(target)):
            # Any other object: its type's __call__, as inspect.signature follows it, but not
            # into C's slots, which hold no partial and where inspect stops too. An object
            # with no __call__ is not callable: inspect.signature refuses it, as tool() does.
            try:
                call = type(target).__call__
            except AttributeError:
                continue
            if not isinstance(call, _C_SLOTS):
                todo.append(call)
    return frozenset(found)


def _timeout(name: str, value: Any) -> float | None:
    """As `_deadline_limit` rules: None, or a finite number of seconds above 0."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise TypeError(f"{name}: timeout_s must be a number of seconds, or None; got {value!r}")
    try:
        seconds = float(value)
    except (OverflowError, ValueError):
        seconds = math.nan
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError(f"{name}: timeout_s must be finite and above 0, or None; got {value!r}")
    return seconds


def _doc(fn: Any) -> str:
    target = fn
    while isinstance(target, functools.partial):
        target = target.func
    return inspect.getdoc(target) or ""


def _summary(doc: str) -> str:
    """The docstring up to its first section heading, stripped."""
    lines = []
    for line in doc.splitlines():
        if line.strip() in _HEADINGS:
            break
        lines.append(line)
    return "\n".join(lines).strip()


def _args_section(doc: str) -> dict[str, str]:
    """A Google-style `Args:` section: each `name: text` or `name (type): text`, continued on
    lines indented deeper, joined by single spaces."""
    found: dict[str, str] = {}
    lines = doc.splitlines()
    inside, indent, current = False, None, None
    for line in lines:
        stripped = line.strip()
        if not inside:
            inside = stripped in ("Args:", "Arguments:")
            continue
        if not stripped:
            continue
        depth = len(line) - len(line.lstrip())
        if depth == 0:
            break  # the next section, or the end of the section
        if indent is None:
            indent = depth
        if depth <= indent:
            m = re.match(r"\*{0,2}([A-Za-z_]\w*)\s*(?:\([^)]*\))?\s*:\s*(.*)$", stripped)
            if m is None:
                current = None
                continue
            current = m.group(1)
            found[current] = m.group(2).strip()
        elif current is not None:
            found[current] = f"{found[current]} {stripped}".strip()
    return found


def _type_hints(name: str, fn: Any) -> dict[str, Any]:
    target = fn
    while isinstance(target, functools.partial):
        target = target.func
    if not (inspect.isfunction(target) or inspect.ismethod(target)):
        target = type(target).__call__
    try:
        return typing.get_type_hints(target)
    except Exception as e:
        raise TypeError(f"{name}: its type hints cannot be read ({type(e).__name__}: {e})") from e


# -------------------------------------------------------------------------------------------------
# Stubs for a prompt. The guest package renders its signatures by the same rules.


class _Hint:
    """An annotation shown as its text, the same on every Python version."""

    __slots__ = ("text",)

    def __init__(self, text: str) -> None:
        self.text = text

    def __repr__(self) -> str:
        return self.text

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Hint) and other.text == self.text

    def __hash__(self) -> int:
        return hash(self.text)


class _Omitted:
    """The default shown for an optional argument whose schema gives none: it is not sent."""

    def __repr__(self) -> str:
        return "..."


_OMITTED = _Omitted()
_TYPE_TEXT = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
    "null": "None",
    "array": "list",
    "object": "dict",
}


def _hint_text(s: Any, depth: int = 0) -> str:
    if not isinstance(s, dict) or depth > 8:
        return "Any"
    enum = s.get("enum")
    if isinstance(enum, list) and enum and all(_tool_schema._scalar(v) for v in enum):
        return "Literal[" + ", ".join(repr(v) for v in enum) + "]"
    if "const" in s and _tool_schema._scalar(s["const"]):
        return f"Literal[{s['const']!r}]"
    for key in ("anyOf", "oneOf"):
        branches = s.get(key)
        if isinstance(branches, list) and branches:
            texts: list[str] = []
            for b in branches:
                text = _hint_text(b, depth + 1)
                if text not in texts:
                    texts.append(text)
            return " | ".join(texts)
    t = s.get("type")
    if isinstance(t, list) and t:
        return " | ".join(_hint_text({**s, "type": one}, depth + 1) for one in t)
    if t == "string" and s.get("contentEncoding") == "base64":
        return "bytes"
    if t == "array" and isinstance(s.get("items"), dict):
        return f"list[{_hint_text(s['items'], depth + 1)}]"
    if (
        t == "object"
        and isinstance(s.get("additionalProperties"), dict)
        and not s.get("properties")
    ):
        return f"dict[str, {_hint_text(s['additionalProperties'], depth + 1)}]"
    if isinstance(t, str) and t in _TYPE_TEXT:
        return _TYPE_TEXT[t]
    return "Any"


def _default(value: Any) -> Any:
    if isinstance(value, dict):
        if len(value) == 1 and isinstance(value.get("$bytes"), str):
            try:
                return binascii.a2b_base64(value["$bytes"].encode("ascii"), strict_mode=True)
            except (binascii.Error, UnicodeEncodeError):
                return value
        return {k: _default(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_default(v) for v in value]
    return value


def _signature(descriptor: _Json) -> inspect.Signature:
    """The signature the guest's function carries: required parameters first, each by
    position or keyword; `(**kwargs)` when the property names cannot make one."""
    try:
        s = descriptor.get("inputSchema")
        props = s.get("properties", {}) if isinstance(s, dict) else None
        required = s.get("required", []) if isinstance(s, dict) else None
        if not isinstance(props, dict) or not isinstance(required, list):
            raise ValueError("no properties")
        names = [n for n in props if n in required] + [n for n in props if n not in required]
        params = []
        for n in names:
            p = props[n]
            if n in required:
                default: Any = inspect.Parameter.empty
            elif isinstance(p, dict) and "default" in p:
                default = _default(p["default"])
            else:
                default = _OMITTED
            params.append(
                inspect.Parameter(
                    n, inspect.Parameter.POSITIONAL_OR_KEYWORD, default=default,
                    annotation=_Hint(_hint_text(p)),
                )
            )  # fmt: skip
        if "outputSchema" in descriptor:
            returns: Any = _Hint(_hint_text(descriptor["outputSchema"]))
        else:
            returns = inspect.Signature.empty
        return inspect.Signature(params, return_annotation=returns)
    except (ValueError, TypeError):
        return inspect.Signature([inspect.Parameter("kwargs", inspect.Parameter.VAR_KEYWORD)])


def _docstring(descriptor: _Json) -> str:
    """The description, then an `Args:` section naming each property."""
    description = descriptor.get("description")
    text = description.strip() if isinstance(description, str) else ""
    s = descriptor.get("inputSchema")
    props = s.get("properties") if isinstance(s, dict) else None
    if isinstance(props, dict) and props:
        lines = []
        for n, p in props.items():
            said = p.get("description") if isinstance(p, dict) else None
            lines.append(f"    {n}: {said}" if isinstance(said, str) and said else f"    {n}")
        text = (text + "\n\n" if text else "") + "Args:\n" + "\n".join(lines)
    return text


def stubs(tools: Iterable[Tool | Callable[..., Any]]) -> str:
    """Python stubs for a prompt: each tool as a `def` with the signature and docstring the
    guest's function carries, under a first line `from host import tools`.

    Args:
        tools: The tools, each a `Tool` or a plain function, which goes through `tool()`.

    Raises:
        TypeError: A plain function `tool()` refuses.
        ValueError: A plain function `tool()` refuses.
    """
    out = ["from host import tools", ""]
    for t in tools:
        t = t if isinstance(t, Tool) else tool(t)
        d = t.descriptor()
        out.append(f"def {t.name}{_signature(d)}:")
        doc = _docstring(d).replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
        lines = doc.splitlines() or [""]
        body = ['    """' + lines[0]] + [f"    {line}" if line else "" for line in lines[1:]]
        if len(lines) > 1:
            body.append('    """')
        else:
            body[0] += '"""'
        out += body
        out.append("")
    return "\n".join(out)


__all__ = [
    "PROTOCOL",
    "Tool",
    "ToolCall",
    "ToolDenied",
    "ToolError",
    "ToolOutcome",
    "ToolRecord",
    "stubs",
    "tool",
]
