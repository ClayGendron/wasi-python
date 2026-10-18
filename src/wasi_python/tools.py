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
`run(tools=[lookup_region])` offers it. Between the two run JSON frames through the door, in
the protocol whose number is `PROTOCOL` (README.md, "The tool protocol"). The rules for those
frames, the schema subset and the bounds are the protocol's own, not the host Python's, so an
answer is the same on every host; they change only with `PROTOCOL`. `import wasi_python` does
not import this module.
"""

# The tool protocol's host half (spec 031): the tools, and the frame host that answers the
# guest's frames through the door.

from __future__ import annotations

import binascii
import contextvars
import copy
import functools
import inspect
import json
import keyword
import math
import numbers
import re
import threading
import time
import types
import typing
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, NamedTuple

PROTOCOL = 1
_PROTOCOLS = (1,)  # the versions this host serves
_TOOL_REQUEST_BYTES = 1 << 20  # a request frame's cap
_TOOL_RESPONSE_BYTES = 16 << 20  # an answer's cap: the default output cap per stream
_TOOL_VALIDATION_STEPS = 100_000  # schema nodes visited and item keys made, per frame
_TOOL_NESTING = 64  # a frame's nesting, its envelope included
_VALUE_NESTING = _TOOL_NESTING - 2  # inside a call's args, or a result's value
_INT_CHARS = 64  # the longest integer literal a frame may hold
_MESSAGE_CHARS = 4096  # the longest message the guest is told
_ECHO_CHARS = 64  # the longest piece of guest text a message repeats
_FAULT_CHARS = 200  # a fault's type and first line, as spec 032's FileFault
_RECORD_OUTCOMES = 1000  # the frames a record lists, whatever max_calls is
_MAX_ID = 2**53 - 1
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
_TOO_COMPLEX = "the arguments are too complex to check"
_SAME_VALUE_CHAIN = 8  # the most schema nodes a $ref, anyOf or oneOf chain passes on one value
_MAX_ABANDONED = 4  # tool threads one call may leave running before its next call is refused
_DEADLINE_MARGIN_TICKS = 2  # a tool call ends this many ticks before the run's deadline

_WRAPPER_DEPTH = 64  # partials, methods and __wrapped__ links walked to find bound keywords
_PARTIALMETHOD = ("__partialmethod__", "_partialmethod")  # its mark: Python 3.13 on, and before

_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,63}")
_HEADINGS = ("Args:", "Arguments:", "Returns:", "Raises:")
_HINTS = (
    ("read_only", "readOnlyHint"),
    ("destructive", "destructiveHint"),
    ("idempotent", "idempotentHint"),
    ("open_world", "openWorldHint"),
)
_JSON_TYPES = ("string", "integer", "number", "boolean", "null", "array", "object")
# Decision 3: what the validator checks, what it ignores, and what descends into the value.
_CHECKED = frozenset(
    (
        "type", "enum", "const", "properties", "required", "additionalProperties",
        "minProperties", "maxProperties", "items", "prefixItems", "minItems", "maxItems",
        "uniqueItems", "anyOf", "oneOf", "$ref", "$defs", "definitions", "minimum", "maximum",
        "exclusiveMinimum", "exclusiveMaximum", "multipleOf", "minLength", "maxLength",
        "contentEncoding",
    )
)  # fmt: skip
_IGNORED = frozenset(
    (
        "title", "description", "default", "examples", "format", "deprecated", "readOnly",
        "writeOnly", "contentMediaType", "discriminator", "$schema", "$id", "$comment",
    )
)  # fmt: skip
_SURROGATE = re.compile("[\ud800-\udfff]")
# One token per match, never retried: an escape pair, a quote or a bracket (Decision 4, rule 3).
_TOKEN = re.compile(r'\\.|["\[\]{}]', re.S)


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
    _input_schema: dict = field(repr=False)
    _output_schema: dict | None = field(repr=False)
    validates_input: bool = False
    timeout_s: float | None = None
    read_only: bool = False
    destructive: bool = False
    idempotent: bool = False
    open_world: bool = False
    _keysets: dict = field(default_factory=dict, repr=False)
    _fixed: frozenset = field(default=frozenset(), repr=False)  # keywords a partial binds

    def __post_init__(self) -> None:
        # Only tool() makes one: not a direct call, and not dataclasses.replace (review F7).
        if not _MAKING.get():
            raise TypeError("a Tool is made by tool(), which describes and vets it")

    @property
    def input_schema(self) -> dict:
        """A copy of the vetted input schema."""
        return copy.deepcopy(self._input_schema)

    @property
    def output_schema(self) -> dict | None:
        """A copy of the output schema, or None. It is shown, never validated."""
        return copy.deepcopy(self._output_schema)

    def descriptor(self) -> dict:
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

    # abandoned: spec 036, the build review's F2

    frames: int
    outcomes: tuple[ToolOutcome, ...]
    unlisted: int
    abandoned: int = 0


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
        TypeError: An argument has the wrong type, the function is async, or a type hint has
            no schema.
        ValueError: A name or a schema the protocol does not allow.
    """
    # timeout_s: spec 036
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
    if _is_async(fn):
        raise TypeError(f"{name}: async tools come with a later specification (decision 15)")
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
        schema = _derived(name, fn, hints_of, _args_section(doc), fixed)
    else:
        maker = getattr(input_schema, "model_json_schema", None)
        given = maker() if callable(maker) else input_schema
        if not isinstance(given, Mapping):
            raise TypeError(
                f"{name}: input_schema must be a dict, or have model_json_schema(); "
                f"got {type(input_schema).__name__}"
            )
        schema = _plain(given, f"{name}: input_schema", 0)
        props = schema.get("properties")
        named = sorted(fixed & set(props)) if isinstance(props, dict) else []
        if named:
            raise ValueError(
                f"{name}: input_schema names {', '.join(map(repr, named))}, which the partial "
                "binds; a bound keyword is fixed, so the guest cannot set it: leave it out"
            )
    nodes = _vet(name, schema, validates_input)
    output = None
    if "return" in hints_of:
        try:
            output = _schema_of(hints_of["return"], "return")
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
            _keysets=_keysets(nodes),
            _fixed=fixed,
            **hints,
        )
    finally:
        _MAKING.reset(making)


def _is_async(fn: Any) -> bool:
    while isinstance(fn, functools.partial):
        fn = fn.func
    if inspect.iscoroutinefunction(fn) or inspect.isasyncgenfunction(fn):
        return True
    if not (inspect.isfunction(fn) or inspect.ismethod(fn)):
        call = type(fn).__call__
        return inspect.iscoroutinefunction(call) or inspect.isasyncgenfunction(call)
    return False


def _bound_keywords(name: str, fn: Any) -> frozenset[str]:
    """The keywords a `functools.partial` binds, wherever `inspect.signature` may meet one on
    its way to the function: the partial, nested partials, a bound method's function, a
    `__wrapped__` chain, a callable object's `__call__` (spec 056, Decision 1). Each is fixed:
    left out of the derived schema and refused in a frame, so the guest neither reads its value
    nor sets it. A `functools.partialmethod` met other than through an instance is refused."""
    found: set[str] = set()
    target, called = fn, False
    for _ in range(_WRAPPER_DEPTH):
        if any(getattr(target, a, None) is not None for a in _PARTIALMETHOD):
            raise TypeError(
                f"{name}: a functools.partialmethod is described only through an instance "
                "(obj.method); or bind its keywords with a closure or a functools.partial"
            )
        if isinstance(target, functools.partial):
            found.update(target.keywords)
            target = target.func
        elif isinstance(target, types.MethodType):
            target = target.__func__
        elif not isinstance(target, type) and getattr(target, "__wrapped__", None) is not None:
            target = target.__wrapped__
        elif not called and not (
            inspect.isfunction(target) or inspect.isbuiltin(target) or isinstance(target, type)
        ):
            called = True
            try:
                target = type(target).__call__
            except AttributeError:  # not callable: inspect.signature refuses it, as tool() does
                return frozenset(found)
        else:
            return frozenset(found)
    raise TypeError(f"{name}: its wrappers nest deeper than {_WRAPPER_DEPTH}; pass a function")


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


def _derived(
    name: str,
    fn: Any,
    hints: dict[str, Any],
    args_doc: dict[str, str],
    fixed: frozenset = frozenset(),
) -> dict:
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError) as e:
        raise TypeError(f"{name}: its signature cannot be read ({e})") from e
    properties: dict[str, Any] = {}
    required: list[str] = []
    for p in sig.parameters.values():
        if p.name in fixed:
            continue  # bound by a partial: not the guest's to read or set (spec 056)
        where = f"{name}: parameter {p.name!r}"
        if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            raise TypeError(f"{where}: *args and **kwargs cannot be described; name each one")
        if p.kind is p.POSITIONAL_ONLY:
            raise TypeError(f"{where} is positional-only; the guest passes arguments by keyword")
        if p.name not in hints:
            raise TypeError(f"{where} has no type hint")
        s = _schema_of(hints[p.name], where)
        if p.name in args_doc and args_doc[p.name]:
            s["description"] = args_doc[p.name]
        if p.default is p.empty:
            required.append(p.name)
        else:
            if p.default is None and not _admits_none(s):
                shown = inspect.formatannotation(hints[p.name])
                raise ValueError(
                    f"{where}: a default of None needs a hint that admits None "
                    f"(write `{p.name}: {shown} | None = None`)"
                )
            try:
                s["default"] = _to_json(p.default, 0)
            except _NotJSON as e:
                raise ValueError(f"{where}: its default has no JSON form ({e})") from None
        properties[p.name] = s
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def _schema_of(hint: Any, where: str) -> dict:
    """Decision 2's hints, mapped to JSON Schema."""
    if hint is Any:
        return {}
    if hint is None or hint is type(None):
        return {"type": "null"}
    simple = {bool: "boolean", int: "integer", float: "number", str: "string"}
    for py, json_type in simple.items():
        if hint is py:
            return {"type": json_type}
    if hint is bytes:
        return {"type": "string", "contentEncoding": "base64"}
    origin, args = typing.get_origin(hint), typing.get_args(hint)
    if origin is list and len(args) == 1:
        return {"type": "array", "items": _schema_of(args[0], where)}
    if origin is tuple and len(args) == 2 and args[1] is Ellipsis:
        return {"type": "array", "items": _schema_of(args[0], where)}
    if origin is dict and len(args) == 2 and args[0] is str:
        return {"type": "object", "additionalProperties": _schema_of(args[1], where)}
    if origin is typing.Literal and args and all(_scalar(a) for a in args):
        return {"enum": list(args)}
    if origin is typing.Union or origin is types.UnionType:
        return {"anyOf": [_schema_of(a, where) for a in args]}
    raise TypeError(
        f"{where}: the hint {inspect.formatannotation(hint)} is not one tool() maps (str, int, "
        "float, bool, None, bytes, list[T], tuple[T, ...], dict[str, T], Literal of JSON "
        "scalars, unions, Any); pass input_schema= instead"
    )


def _scalar(value: Any) -> bool:
    if value is None or isinstance(value, (bool, int, str)):
        return type(value) in (type(None), bool, int, str)
    return type(value) is float and math.isfinite(value)


def _admits_none(s: Any) -> bool:
    if s is True or (isinstance(s, dict) and not (set(s) - _IGNORED)):
        return True
    if not isinstance(s, dict):
        return False
    t = s.get("type")
    if t == "null" or (isinstance(t, list) and "null" in t):
        return True
    if None in s.get("enum", ()):
        return True
    return any(_admits_none(b) for b in s.get("anyOf", []) + s.get("oneOf", []))


def _plain(value: Any, where: str, depth: int) -> Any:
    """A deep copy of a schema made only of JSON values (a tuple becomes a list)."""
    if depth > 256:
        raise ValueError(f"{where} nests deeper than 256 levels")
    if value is None or type(value) in (bool, int, str):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"{where} holds {value!r}, which JSON does not allow")
        return value
    if isinstance(value, Mapping):
        out = {}
        for k, v in value.items():
            if not isinstance(k, str):
                raise ValueError(f"{where} has a key that is not a str: {k!r}")
            out[str(k)] = _plain(v, where, depth + 1)
        return out
    if isinstance(value, (list, tuple)):
        return [_plain(v, where, depth + 1) for v in value]
    raise ValueError(f"{where} holds a {type(value).__name__}, which is not JSON")


# -------------------------------------------------------------------------------------------------
# Vetting a schema (Decision 3)


def _vet(name: str, root: dict, validates_input: bool) -> list[Any]:
    where = f"{name}: input schema"
    if root.get("type") != "object":
        raise ValueError(f'{where}: its root must be {{"type": "object", ...}}')
    properties = root.get("properties", {})
    if not isinstance(properties, dict):
        raise ValueError(f"{where}: properties must be an object")
    for prop in properties:
        if not prop.isidentifier() or keyword.iskeyword(prop):
            raise ValueError(
                f"{where}: the property {prop!r} is not a Python identifier, or is a keyword; "
                "the guest calls the tool with it as a keyword argument (rename it, as the "
                "README shows)"
            )
    required = root.get("required", [])
    if isinstance(required, list):
        for r in required:
            if r not in properties:
                raise ValueError(f"{where}: required names {r!r}, which is not in properties")
    return _Vetting(where, root, validates_input).run()


class _Vetting:
    """Every schema node reachable from the root, and every definition, uses only keywords the
    validator knows (unless the tool validates its own input), with well-formed values; every
    `$ref` is local and resolves; and no `$ref` cycle stays on one value."""

    def __init__(self, where: str, root: dict, validates_input: bool) -> None:
        self.where, self.root, self.lax = where, root, validates_input

    def fail(self, path: str, what: str) -> None:
        raise ValueError(f"{self.where}: {path}: {what}")

    def run(self) -> list[Any]:
        todo: list[tuple[str, Any]] = [("#", self.root)]
        for container in ("$defs", "definitions"):
            defs = self.root.get(container)
            if isinstance(defs, dict):
                todo += [(f"#/{container}/{k}", v) for k, v in defs.items()]
        nodes: dict[int, Any] = {}
        while todo:
            path, node = todo.pop()
            if id(node) in nodes:
                continue
            nodes[id(node)] = node
            todo += self.node(path, node)
        self.no_cycle(list(nodes.values()))
        return list(nodes.values())

    def node(self, path: str, s: Any) -> list[tuple[str, Any]]:
        """Vet one node; give the subschemas the validator visits from it."""
        if isinstance(s, bool):
            return []
        if not isinstance(s, dict):
            self.fail(path, "a schema must be an object or a boolean")
        for key, value in s.items():
            if key in _IGNORED:
                continue
            if key not in _CHECKED:
                if not self.lax:
                    why = ""
                    if key == "pattern":
                        why = (
                            " (pattern stays refused: a regular expression run on guest text can "
                            "backtrack without end)"
                        )
                    self.fail(
                        path,
                        f"the keyword {key!r} is outside the subset the runner checks; pass "
                        f"validates_input=True if the tool checks its own input{why}",
                    )
                continue
            problem = _malformed(key, value)
            if problem is not None:
                if key in ("multipleOf", "contentEncoding"):
                    if self.lax:
                        continue  # outside what the validator checks: the tool's own
                    problem += "; pass validates_input=True if the tool checks it"
                self.fail(path, f"{key} {problem}")
            if key == "$ref" and _resolve(self.root, value) is None:
                self.fail(
                    path,
                    f"$ref {value!r} is not a local reference into $defs or definitions that "
                    "resolves",
                )
        out = [(f"{path}/{k}", child) for k, child, _ in _children(s)]
        if "$ref" in s:
            out.append((s["$ref"], _resolve(self.root, s["$ref"])))
        return out

    def no_cycle(self, nodes: list[Any]) -> None:
        """No walk along anyOf, oneOf and $ref alone, which stay on one value, comes back to
        where it began: a depth-first search over those edges finds no node on its own path.
        And none is longer than _SAME_VALUE_CHAIN nodes, so the validator's recursion is bounded
        by the value's depth times that, never by the host Python's limit (review F5)."""
        done: set[int] = set()
        longest: dict[int, int] = {}  # the most nodes a same-value walk from a node passes
        for start in nodes:
            if id(start) in done:
                continue
            on_path = {id(start)}
            stack = [(start, iter(self.same_value(start)))]
            while stack:
                node, children = stack[-1]
                child = next(children, None)
                if child is None:
                    stack.pop()
                    on_path.discard(id(node))
                    done.add(id(node))
                    below = [longest.get(id(c), 0) for c in self.same_value(node)]
                    longest[id(node)] = 1 + max(below, default=0)
                    if longest[id(node)] > _SAME_VALUE_CHAIN:
                        raise ValueError(
                            f"{self.where}: a chain of more than {_SAME_VALUE_CHAIN} $ref, anyOf "
                            "or oneOf steps on one value; shorten it"
                        )
                elif id(child) in on_path:
                    raise ValueError(
                        f"{self.where}: a $ref cycle that does not descend into the value "
                        "(through properties, additionalProperties, items or prefixItems) "
                        "would never end"
                    )
                elif id(child) not in done:
                    on_path.add(id(child))
                    stack.append((child, iter(self.same_value(child))))

    def same_value(self, s: Any) -> list[Any]:
        if not isinstance(s, dict):
            return []
        out = [child for _, child, descends in _children(s) if not descends]
        if "$ref" in s:
            target = _resolve(self.root, s["$ref"])
            if isinstance(target, dict):
                out.append(target)
        return out


def _children(s: dict) -> list[tuple[str, Any, bool]]:
    """(keyword, subschema, whether it descends into the value) for each subschema the
    validator visits."""
    out: list[tuple[str, Any, bool]] = []
    props = s.get("properties")
    if isinstance(props, dict):
        out += [(f"properties/{k}", v, True) for k, v in props.items()]
    extra = s.get("additionalProperties")
    if isinstance(extra, dict):
        out.append(("additionalProperties", extra, True))
    items = s.get("items")
    if isinstance(items, dict):
        out.append(("items", items, True))
    prefix = s.get("prefixItems")
    if isinstance(prefix, list):
        out += [(f"prefixItems/{i}", v, True) for i, v in enumerate(prefix) if isinstance(v, dict)]
    for key in ("anyOf", "oneOf"):
        branches = s.get(key)
        if isinstance(branches, list):
            out += [(f"{key}/{i}", v, False) for i, v in enumerate(branches) if isinstance(v, dict)]
    return out


def _resolve(root: dict, ref: Any) -> Any:
    """A local `$ref` into $defs or definitions, or None."""
    if not isinstance(ref, str) or not ref.startswith(("#/$defs/", "#/definitions/")):
        return None
    node: Any = root
    for part in ref[2:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node if isinstance(node, (dict, bool)) else None


def _count(value: Any) -> bool:
    return type(value) is int and value >= 0


def _number(value: Any) -> bool:
    return type(value) in (int, float)


def _malformed(key: str, value: Any) -> str | None:
    """Why a checked keyword's value is not one the validator can check, or None."""
    if key == "type":
        names = value if isinstance(value, list) else [value]
        if not names or not all(isinstance(n, str) and n in _JSON_TYPES for n in names):
            return f"must name JSON types ({', '.join(_JSON_TYPES)}); got {value!r}"
    elif key == "enum":
        if not isinstance(value, list):
            return "must be a list"
    elif key in ("properties", "$defs", "definitions"):
        if not isinstance(value, dict):
            return "must be an object"
    elif key == "required":
        if not isinstance(value, list) or not all(isinstance(r, str) for r in value):
            return "must be a list of names"
    elif key in ("additionalProperties", "items"):
        if not isinstance(value, (dict, bool)):
            return (
                "must be one schema (the array form of items is draft 4's tuple: use prefixItems)"
                if key == "items"
                else "must be a schema or a boolean"
            )
    elif key == "prefixItems":
        if not isinstance(value, list) or not all(isinstance(v, (dict, bool)) for v in value):
            return "must be a list of schemas"
    elif key in ("anyOf", "oneOf"):
        if not isinstance(value, list) or not value:
            return "must be a list of schemas"
        if not all(isinstance(v, (dict, bool)) for v in value):
            return "must be a list of schemas"
    elif key == "$ref":
        if not isinstance(value, str):
            return "must be a string"
    elif key in ("minProperties", "maxProperties", "minItems", "maxItems"):
        if not _count(value):
            return "must be an integer from 0"
    elif key in ("minLength", "maxLength"):
        if not _count(value):
            return "must be an integer from 0"
    elif key == "uniqueItems":
        if not isinstance(value, bool):
            return "must be true or false"
    elif key in ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum"):
        if not _number(value):
            return "must be a number"
    elif key == "multipleOf":
        if type(value) is not int or value <= 0:
            return "must be a positive integer for the runner to check it"
    elif key == "contentEncoding":
        if value != "base64":
            return "must be base64 for the runner to check it"
    return None


# -------------------------------------------------------------------------------------------------
# The validator (Decision 3)


class _TooComplex(Exception):
    pass


class _Invalid(Exception):
    pass


_EMPTY: dict = {}
_DELEGATES = ("$ref", "anyOf", "oneOf")
_OBJECT_WORDS = frozenset(
    ("properties", "additionalProperties", "required", "minProperties", "maxProperties")
)
_ARRAY_WORDS = frozenset(("items", "prefixItems", "minItems", "maxItems", "uniqueItems"))


_KeySets = dict[tuple[int, str], tuple[dict, frozenset]]


def _keysets(nodes: Iterable[Any]) -> _KeySets:
    """Each `enum` and `const` as a set of keys, made once when the tool is made, so checking a
    value against them is one key and one lookup (review F1). Each entry keeps its node, and is
    used only for that same object: an id alone can be reused by another node once a Tool is
    copied or unpickled and the original freed (the confirmation's N1)."""
    out: _KeySets = {}
    for s in nodes:
        if not isinstance(s, dict):
            continue
        if isinstance(s.get("enum"), list):
            out[(id(s), "enum")] = (s, frozenset(_key(e) for e in s["enum"]))
        if "const" in s:
            out[(id(s), "const")] = (s, frozenset((_key(s["const"]),)))
    return out


class _Validator:
    """Checks a decoded value against a vetted schema, with no coercion and type-strict
    equality, counting its work against a budget (Decision 3, and the build review's F1 and F2).

    - One step for each schema node a value is checked against. A node that only delegates
      (`$ref`, `anyOf`, `oneOf`) leaves the value's children to the schema it delegates to, so a
      value costs one step for each schema that describes it, never a walk per wrapper.
    - A key (for `enum`, `const` and `uniqueItems`) costs one step for each value below the one
      it is made for, and a `uniqueItems` key one more for its item; an `enum` or a `const` is a
      set of keys made once, so membership is one lookup.
    - A message names a value by its kind and size, or by 64 characters of a string.

    A value is accepted as bytes only where its schema says so. `check` gives None, or what is
    wrong."""

    def __init__(
        self,
        root: Any,
        budget: int = _TOOL_VALIDATION_STEPS,
        keysets: _KeySets | None = None,
    ) -> None:
        self.root, self.budget = root, budget
        self.keysets = dict(keysets or {})
        self.steps = 0  # schema nodes visited, plus the values below each key made
        self.keys = 0  # item keys made (uniqueItems)
        self.exhausted = False

    def check(self, value: Any) -> str | None:
        try:
            self.visit(self.root, value, None)
        except _TooComplex:
            self.exhausted = True
            return _TOO_COMPLEX
        except _Invalid as e:
            return str(e)
        return None

    def step(self) -> None:
        if self.steps >= self.budget:
            raise _TooComplex
        self.steps += 1

    def keyset(self, s: dict, word: str) -> frozenset:
        entry = self.keysets.get((id(s), word))
        if entry is not None and entry[0] is s:
            return entry[1]
        # A schema no tool() vetted (the unit checks), or a Tool copied or unpickled, whose
        # entries name nodes that are gone: made now, and charged.
        allowed = s["enum"] if word == "enum" else [s["const"]]
        keys = []
        for e in allowed:
            self.step()
            keys.append(_key(e, self.step))
        found = frozenset(keys)
        self.keysets[(id(s), word)] = (s, found)
        return found

    def visit(self, s: Any, value: Any, at: Any) -> None:
        self.step()
        if s is False:
            raise _Invalid(f"{_where(at)}: no value is allowed here")
        if s is True:
            s = _EMPTY
        delegates = any(k in s for k in _DELEGATES)
        if isinstance(value, bytes) and "type" not in s and not delegates:
            raise _Invalid(
                f'{_where(at)}: bytes are accepted only where the schema says {{"type": '
                '"string", "contentEncoding": "base64"}'
            )
        if "$ref" in s:
            self.visit(_resolve(self.root, s["$ref"]), value, at)
        if "type" in s:
            t = s["type"]
            names = t if isinstance(t, list) else [t]
            if not any(_is_type(n, value, s) for n in names):
                want = " or ".join(_type_name(n, s) for n in names)
                raise _Invalid(f"{_where(at)}: expected {want}, got {_kind_of(value)}")
        if "enum" in s or "const" in s:
            k = _key(value, self.step)
            if "enum" in s and k not in self.keyset(s, "enum"):
                raise _Invalid(f"{_where(at)}: {_shown(value)} is not one of the allowed values")
            if "const" in s and k not in self.keyset(s, "const"):
                raise _Invalid(f"{_where(at)}: {_shown(value)} is not the allowed value")
        if isinstance(value, dict):
            if not delegates or not _OBJECT_WORDS.isdisjoint(s):
                self.object(s, value, at)
        elif isinstance(value, list):
            if not delegates or not _ARRAY_WORDS.isdisjoint(s):
                self.array(s, value, at)
        elif isinstance(value, str):
            self.length(s, len(value), at, "characters")
        elif isinstance(value, bytes):
            self.length(s, len(value), at, "bytes")
        elif _number(value):
            self.number(s, value, at)
        if "anyOf" in s:
            first = None
            for branch in s["anyOf"]:
                try:
                    self.visit(branch, value, at)
                    break
                except _Invalid as e:
                    first = first or str(e)
            else:
                raise _Invalid(f"{_where(at)}: matches none of anyOf ({first})")
        if "oneOf" in s:
            matched = 0
            first = ""
            for branch in s["oneOf"]:
                try:
                    self.visit(branch, value, at)
                    matched += 1
                except _Invalid as e:
                    first = first or str(e)
            if matched != 1:
                why = f"none ({first})" if matched == 0 else f"{matched}"
                raise _Invalid(f"{_where(at)}: must match exactly one of oneOf; it matches {why}")

    def object(self, s: dict, value: dict, at: Any) -> None:
        props = s.get("properties", _EMPTY)
        for name in s.get("required", ()):
            if name not in value:
                raise _Invalid(f"{_where(at)}: missing the required argument {_echo(name)}")
        n = len(value)
        if "minProperties" in s and n < s["minProperties"]:
            raise _Invalid(f"{_where(at)}: at least {s['minProperties']} keys, got {n}")
        if "maxProperties" in s and n > s["maxProperties"]:
            raise _Invalid(f"{_where(at)}: at most {s['maxProperties']} keys, got {n}")
        extra = s.get("additionalProperties", False if "properties" in s else True)
        for k, v in value.items():
            if k in props:
                self.visit(props[k], v, (at, "." + k))
            elif extra is False:
                raise _Invalid(f"{_where(at)}: unknown argument {_echo(k)}")
            else:
                self.visit(extra, v, (at, "." + _echo(k)))

    def array(self, s: dict, value: list, at: Any) -> None:
        n = len(value)
        if "minItems" in s and n < s["minItems"]:
            raise _Invalid(f"{_where(at)}: at least {s['minItems']} items, got {n}")
        if "maxItems" in s and n > s["maxItems"]:
            raise _Invalid(f"{_where(at)}: at most {s['maxItems']} items, got {n}")
        if s.get("uniqueItems"):
            seen: set = set()
            for i, item in enumerate(value):
                k = self.item_key(item)
                if k in seen:
                    raise _Invalid(f"{_where(at)}: the items must be unique; item {i} repeats one")
                seen.add(k)
        prefix = s.get("prefixItems", ())
        rest = s.get("items", True)
        for i, item in enumerate(value):
            self.visit(prefix[i] if i < len(prefix) else rest, item, (at, f"[{i}]"))

    def item_key(self, item: Any) -> Any:
        self.step()
        self.keys += 1
        return _key(item, self.step)

    def length(self, s: dict, n: int, at: Any, unit: str) -> None:
        if "minLength" in s and n < s["minLength"]:
            raise _Invalid(f"{_where(at)}: at least {s['minLength']} {unit}, got {n}")
        if "maxLength" in s and n > s["maxLength"]:
            raise _Invalid(f"{_where(at)}: at most {s['maxLength']} {unit}, got {n}")

    def number(self, s: dict, x: int | float, at: Any) -> None:
        for key, ok, says in (
            ("minimum", lambda b: x >= b, "at least"),
            ("maximum", lambda b: x <= b, "at most"),
            ("exclusiveMinimum", lambda b: x > b, "above"),
            ("exclusiveMaximum", lambda b: x < b, "below"),
        ):
            if key in s and _number(s[key]) and not ok(s[key]):
                raise _Invalid(f"{_where(at)}: must be {says} {s[key]}, got {_shown(x)}")
        m = s.get("multipleOf")
        if type(m) is int and m > 0 and x % m != 0:
            raise _Invalid(f"{_where(at)}: must be a multiple of {m}, got {_shown(x)}")


def _where(at: Any) -> str:
    """A path kept as (parent, segment) links, rendered only for a message."""
    parts = []
    while at is not None:
        at, segment = at
        parts.append(segment)
    path = "".join(reversed(parts)).lstrip(".")
    return f"argument {path}" if path else "the arguments"


def _is_type(name: str, value: Any, s: dict) -> bool:
    if name == "string":
        if s.get("contentEncoding") == "base64":
            return isinstance(value, bytes)
        return isinstance(value, str)
    if name == "integer":
        return type(value) is int
    if name == "number":
        return type(value) in (int, float)
    if name == "boolean":
        return type(value) is bool
    if name == "null":
        return value is None
    if name == "array":
        return isinstance(value, list)
    return isinstance(value, dict)  # "object"


def _type_name(name: str, s: dict) -> str:
    if name == "string" and s.get("contentEncoding") == "base64":
        return "bytes"
    return name


def _kind_of(value: Any) -> str:
    if value is None:
        return "null"
    return {
        bool: "boolean",
        int: "integer",
        float: "number",
        str: "string",
        bytes: "bytes",
        list: "array",
        dict: "object",
    }.get(type(value), type(value).__name__)


def _key(value: Any, charge: Callable[[], None] | None = None) -> Any:
    """A hashable key, tagged by type at every level: two values have equal keys exactly when
    they are equal as JSON with no coercion (true is never 1, 1.0 is never 1). `charge` is
    called once for each value below `value`, before its key is made."""
    if value is None:
        return ("n",)
    t = type(value)
    if t is bool:
        return ("b", value)
    if t is int:
        return ("i", value)
    if t is float:
        return ("f", value)
    if t is str:
        return ("s", value)
    if t is bytes:
        return ("y", value)
    if t is list:
        keys = []
        for v in value:
            if charge is not None:
                charge()
            keys.append(_key(v, charge))
        return ("l", tuple(keys))
    if t is dict:
        pairs = []
        for k, v in value.items():
            if charge is not None:
                charge()
            pairs.append((k, _key(v, charge)))
        return ("d", tuple(sorted(pairs)))
    return ("?", id(value))


# -------------------------------------------------------------------------------------------------
# Frames (Decisions 4 and 7)


class _Refused(Exception):
    """A frame that breaks the protocol's rules: a `protocol` answer."""


def _echo(value: Any) -> str:
    """A piece of guest text for a message: a string cut to 64 characters first; any other
    value named by its kind and size (`_shown`), never formatted whole."""
    if not isinstance(value, str):
        return _shown(value)
    cut = value[:_ECHO_CHARS]
    return f"'{cut}'" + ("..." if len(value) > _ECHO_CHARS else "")


def _shown(value: Any) -> str:
    """A value for a message, at a cost bounded whatever its size (review F1)."""
    if isinstance(value, str):
        return _echo(value)
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if type(value) is int:
        text = str(value) if -(10**_ECHO_CHARS) < value < 10**_ECHO_CHARS else "a long integer"
        return text
    if type(value) is float:
        return repr(value)
    if isinstance(value, list):
        return f"an array of {len(value)} items"
    if isinstance(value, dict):
        return f"an object of {len(value)} keys"
    if isinstance(value, bytes):
        return f"{len(value)} bytes"
    return f"a {type(value).__name__}"


def _nesting(text: str) -> int:
    """The deepest nesting of arrays and objects outside strings, in one pass over the text: a
    regular expression that skips whole strings would be retried at every quote of an
    unterminated one, which is quadratic on a guest's megabyte."""
    depth = deepest = 0
    inside = False
    for m in _TOKEN.finditer(text):
        token = m.group()
        if inside:
            inside = token != '"'  # an escape pair or a bracket stays inside the string
        elif token == '"':
            inside = True
        elif token in "[{":
            depth += 1
            if depth > deepest:
                deepest = depth
                if deepest > _TOOL_NESTING:
                    break
        elif token in "]}":
            depth -= 1
    return deepest


def _no_constant(name: str) -> Any:
    raise _Refused(f"the frame holds {name}, which JSON does not allow")


def _finite(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise _Refused(f"the number {_echo(text)} is out of range")
    return value


def _bounded_int(text: str) -> int:
    if len(text) > _INT_CHARS:
        raise _Refused(f"an integer of {len(text)} characters; at most {_INT_CHARS}")
    return int(text)


def _unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out = dict(pairs)
    if len(out) != len(pairs):
        seen: set[str] = set()
        for k, _ in pairs:
            if k in seen:
                raise _Refused(f"the frame repeats the key {_echo(k)}")
            seen.add(k)
    return out


def _parse(frame: bytes) -> dict:
    """Decision 4's rules 2 to 6, then the `$bytes` objects decoded."""
    try:
        text = frame.decode("utf-8")
    except UnicodeDecodeError:
        raise _Refused("the frame is not UTF-8") from None
    depth = _nesting(text)
    if depth > _TOOL_NESTING:
        raise _Refused(f"the frame nests deeper than {_TOOL_NESTING} levels")
    try:
        value = json.loads(
            text,
            parse_constant=_no_constant,
            parse_float=_finite,
            parse_int=_bounded_int,
            object_pairs_hook=_unique_keys,
        )
    except _Refused:
        raise
    except (ValueError, RecursionError) as e:
        first = (str(e).splitlines() or [""])[0][:200]
        raise _Refused(f"the frame is not JSON ({first})") from None
    value = _decoded(value)
    if not isinstance(value, dict):
        raise _Refused("the frame is not a JSON object")
    return value


def _decoded(value: Any) -> Any:
    """Strings checked for lone surrogates, and each `{"$bytes": "<base64>"}` made bytes."""
    if isinstance(value, str):
        if _SURROGATE.search(value):
            raise _Refused(f"a string holds a lone surrogate: {_echo(value)}")
        return value
    if isinstance(value, list):
        return [_decoded(v) for v in value]
    if isinstance(value, dict):
        for k in value:
            if _SURROGATE.search(k):
                raise _Refused(f"a key holds a lone surrogate: {_echo(k)}")
        if "$bytes" in value:
            data = value["$bytes"]
            if len(value) != 1 or not isinstance(data, str):
                raise _Refused('a "$bytes" object must have that one key, holding a string')
            try:
                return binascii.a2b_base64(data.encode("ascii"), strict_mode=True)
            except (binascii.Error, UnicodeEncodeError):
                raise _Refused('a "$bytes" value is not strict base64') from None
        return {k: _decoded(v) for k, v in value.items()}
    return value


class _NotJSON(Exception):
    pass


def _to_json(value: Any, depth: int) -> Any:
    """Decision 6's JSON form, which mirrors the guest's encoding."""
    if depth > _VALUE_NESTING:
        raise _NotJSON(f"the value nests deeper than {_VALUE_NESTING} levels")
    if value is None or isinstance(value, bool):
        return None if value is None else bool(value)
    if isinstance(value, str):
        return str.__str__(value)
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise _NotJSON(f"{value!r} is not a finite number")
        return float(value)
    if isinstance(value, dict):
        if len(value) == 1 and "$bytes" in value:
            raise _NotJSON('a dict whose only key is "$bytes" would read as bytes')
        out = {}
        for k, v in value.items():
            if not isinstance(k, str):
                raise _NotJSON(f"a dict key of type {type(k).__name__}, not str")
            out[str.__str__(k)] = _to_json(v, depth + 1)
        return out
    if isinstance(value, (list, tuple)):
        return [_to_json(v, depth + 1) for v in value]
    if isinstance(value, (bytes, bytearray, memoryview)):
        data = binascii.b2a_base64(bytes(value), newline=False).decode("ascii")
        return {"$bytes": data}
    if isinstance(value, numbers.Integral):
        return int(value)
    if isinstance(value, numbers.Real):
        x = float(value)
        if not math.isfinite(x):
            raise _NotJSON(f"{x!r} is not a finite number")
        return x
    raise _NotJSON(f"a {type(value).__name__} has no JSON form")


def _encode(answer: dict) -> bytes:
    return json.dumps(answer, ensure_ascii=True, allow_nan=False, separators=(",", ":")).encode(
        "ascii"
    )


def _bounded(message: str) -> str:
    return message[:_MESSAGE_CHARS]


def _described(e: BaseException) -> str:
    """An exception's type name and the first line of its text, as spec 032's `_described`
    (so `fault` reads as 032's `FileFault`), but total over `BaseException`: a `__str__` that
    raises `SystemExit` gives the name alone (review F3)."""
    try:
        name = type.__dict__["__name__"].__get__(type(e))  # the type's own name
        if type(name) is not str:
            name = "an exception"
    except BaseException:
        name = "an exception"
    try:
        text = str(e)
        if type(text) is not str:
            return name
        lines = str.splitlines(str.strip(text))
    except BaseException:
        return name
    return f"{name}: {lines[0]}" if lines else name


def _fault(e: BaseException) -> str:
    return _described(e)[:_FAULT_CHARS]


def _message_of(e: BaseException) -> str:
    """A ToolError's own text, bounded, as a plain str; raises whatever its __str__ raises."""
    text = str(e)
    return _bounded(text if type(text) is str else str.__str__(text))


class _Done(NamedTuple):
    """What the work gives: the answer's bytes and how it ended."""

    answer: bytes
    outcome: str  # "ok" or a kind
    message: str | None
    fault: str | None


class _Interrupted(NamedTuple):
    """What a bounded invoke gives when it did not wait for the work (spec 036)."""

    kind: str  # "timeout" or "cancelled"; "tool_error" when the bound itself failed
    abandoned: bool  # the work was left running
    message: str | None = None  # what the guest is told; by default "<name> timed out" and so on
    fault: str | None = None  # the bound's own exception, when it failed after the work started


class _Work:
    """The gate, then the tool, then the result's encoding, as one callable: what `invoke`
    runs. It touches no state of the frame host, so it may run, or finish late, elsewhere."""

    def __init__(self, host: _ToolHost, seq: int, frame_id: Any, tool: Tool, args: dict) -> None:
        self.tool, self.seq, self.frame_id = tool, seq, frame_id
        self._gate, self._args, self._size = host._gate, args, host._size

    def __call__(self, proceed: Callable[[], bool] | None = None) -> _Done:
        """`proceed`, from the bound, is asked once the gate has allowed and before the tool
        starts: False when the call was already answered, so the tool never runs (spec 056)."""
        t = self.tool
        args = self._args
        if self._gate is not None:
            call = ToolCall(self.seq, t, copy.deepcopy(args), self._size)
            refused = f"{t.name} was refused"
            try:
                verdict = self._gate(call)
            except ToolError as e:
                try:
                    return self.failed("denied", _message_of(e))
                except BaseException as inner:
                    return self.failed("denied", refused, _fault(inner))
            except BaseException as e:  # a broken gate fails closed
                return self.failed("denied", refused, _fault(e))
            if verdict is False:
                return self.failed("denied", refused)
            if verdict is not None and verdict is not True:
                why = f"TypeError: the gate returned {type(verdict).__name__}, not None or a bool"
                return self.failed("denied", refused, why[:_FAULT_CHARS])
        if proceed is not None and not proceed():
            return self.failed("cancelled", f"{t.name} was not run: its call had ended")
        internal = f"{t.name} failed (internal error)"
        try:
            value = t.fn(**args)
        except ToolError as e:
            how = "denied" if isinstance(e, ToolDenied) else "tool_error"
            try:
                return self.failed(how, _message_of(e))
            except BaseException as inner:
                return self.failed(how, internal, _fault(inner))
        except BaseException as e:
            return self.failed("tool_error", internal, _fault(e))
        try:
            body = _to_json(value, 0)
            encoded = _encode({"v": PROTOCOL, "id": self.frame_id, "ok": True, "value": body})
        except BaseException as e:
            return self.failed("tool_error", internal, _fault(e))
        if len(encoded) > _TOOL_RESPONSE_BYTES:
            return self.failed(
                "too_large",
                f"the result of {t.name} is {len(encoded)} bytes encoded, over the "
                f"{_TOOL_RESPONSE_BYTES}-byte (16 MiB) cap",
            )
        return _Done(encoded, "ok", None, None)

    def failed(self, kind: str, message: str, fault: str | None = None) -> _Done:
        return _Done(_error(self.frame_id, kind, message), kind, message, fault)


def _error(frame_id: Any, kind: str, message: str) -> bytes:
    error = {"kind": kind, "message": _bounded(message)}
    return _encode({"v": PROTOCOL, "id": frame_id, "ok": False, "error": error})


def _inline(work: _Work) -> _Done | _Interrupted:
    return work()


class _Slot:
    """One tool call's result: filled by its own thread, read by its own call only, so a late
    result of an abandoned call is dropped, never delivered to a later one (spec 036, D4)."""

    __slots__ = ("abandoned", "done", "fault", "filled", "finished", "started")

    def __init__(self) -> None:
        self.filled = threading.Event()
        self.done: _Done | None = None
        self.fault: str | None = None  # the work raised past its own catch-all, or never started
        self.started = False  # its thread was started
        self.finished = False  # set under the bound's lock, as its thread ends
        self.abandoned = False  # set under the bound's lock, when the call was answered without it


class _Bounded:
    """The invoke of spec 036 (Decisions 3 to 5): the work of one tool call runs on a new daemon
    thread, in a copy of the door thread's context, while the door thread waits beside it in
    slices of one tick. The call ends at the first of: the work's answer; a pending Ctrl-C or
    the call's `cancel` (`cancelled`); the call's deadline less two ticks, read from the ticker
    as spec 010's waits read it, or the tool's `timeout_s` (`timeout`). A call left running is
    abandoned: its thread runs to its end unseen, and its result is dropped. One call may hold
    `_MAX_ABANDONED` of them; while it does, its next tool call is answered `timeout` at once.

    Everything it needs is injected, so the judge drives it with fakes: `ticks` (the epoch
    ticker's count), `ctrl_c` (whether a Ctrl-C is pending; read, never cleared), `count` (told
    +1 and -1 as tool threads start and end), `start` (starts a thread) and `clock` (for
    `timeout_s`). It never raises an `Exception`: a thread that cannot start, or a fault of its
    own, is a `tool_error` answer that keeps the call and its tool in the record (the 031 build
    review's F5)."""

    def __init__(
        self,
        *,
        tick_s: float,
        stop_at: int | None = None,
        ticks: Callable[[], int] | None = None,
        cancel: threading.Event | None = None,
        ctrl_c: Callable[[], bool] | None = None,
        count: Callable[[int], Any] = lambda delta: None,
        start: Callable[[threading.Thread], Any] = threading.Thread.start,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._tick, self._stop_at, self._ticks = tick_s, stop_at, ticks
        self._cancel, self._ctrl_c, self._count = cancel, ctrl_c, count
        self._start, self._clock = start, clock
        self._lock = threading.Lock()
        self._abandoned = 0  # this call's threads still running after their call was answered

    def _ended(self) -> str | None:
        """'cancelled' or 'deadline' when the run is ending, else None."""
        if self._ctrl_c is not None and self._ctrl_c():
            return "cancelled"
        if self._cancel is not None and self._cancel.is_set():
            return "cancelled"
        if self._stop_at is not None and self._ticks is not None:
            if self._ticks() >= self._stop_at - _DEADLINE_MARGIN_TICKS:
                return "deadline"
        return None

    def __call__(self, work: _Work) -> _Done | _Interrupted:
        name = work.tool.name
        internal = f"{name} failed (internal error)"
        slot: _Slot | None = None
        try:
            ended = self._ended()
            if ended == "cancelled":
                return _Interrupted("cancelled", False, f"{name} was cancelled")
            if ended == "deadline":
                too_near = f"{name} timed out: the run's deadline is too near to start it"
                return _Interrupted("timeout", False, too_near)
            with self._lock:
                full = self._abandoned >= _MAX_ABANDONED
            if full:
                busy = f"{name} timed out: {_MAX_ABANDONED} earlier tool calls are still running"
                return _Interrupted("timeout", False, busy)
            slot = _Slot()
            if not self._started(work, slot):
                return work.failed("tool_error", internal, slot.fault)
            return self._wait(work, slot)
        except Exception as e:
            fault = _fault(e)
            if slot is None or not slot.started:
                return work.failed("tool_error", internal, fault)
            if not self._abandon(slot):  # the work had finished: its answer stands
                return self._delivered(work, slot)
            return _Interrupted("tool_error", True, internal, fault)

    def _started(self, work: _Work, slot: _Slot) -> bool:
        """Start the work's thread; False, with the fault in the slot, if it cannot start."""
        context = contextvars.copy_context()

        def target() -> None:
            try:
                try:
                    slot.done = context.run(work, functools.partial(self._proceed, slot))
                except BaseException as e:  # _Work catches its own; this is a last resort
                    slot.fault = _fault(e)
                slot.filled.set()
            finally:
                with self._lock:
                    slot.finished = True
                    if slot.abandoned:
                        self._abandoned -= 1
                self._count(-1)

        self._count(1)
        try:
            thread = threading.Thread(
                target=target, name=f"wasi-python-tool-{work.tool.name}", daemon=True
            )
            self._start(thread)
        except Exception as e:  # the operating system's thread limit (spec 036, D5)
            self._count(-1)
            slot.fault = _fault(e)
            return False
        slot.started = True
        return True

    def _proceed(self, slot: _Slot) -> bool:
        """Whether the tool may start: False once the call was answered without it. Taken under
        the lock `_abandon` takes, so a call is either answered before its tool starts (the tool
        never runs) or after (it runs on, abandoned): the a4 security review's F2, spec 056."""
        with self._lock:
            return not slot.abandoned

    def _abandon(self, slot: _Slot) -> bool:
        """Mark the call answered without its work; False if the work had already finished or
        filled its slot (its thread may not have reached its `finally` yet: the build review's
        F3), so its answer stands and nothing is counted."""
        with self._lock:
            if slot.finished or slot.filled.is_set():
                return False
            slot.abandoned = True
            self._abandoned += 1
            return True

    def _wait(self, work: _Work, slot: _Slot) -> _Done | _Interrupted:
        name, timeout = work.tool.name, work.tool.timeout_s
        until = None if timeout is None else self._clock() + timeout
        while True:
            pause = self._tick
            if until is not None:
                pause = max(0.0, min(pause, until - self._clock()))
            if slot.filled.wait(pause):
                return self._delivered(work, slot)
            ended = self._ended()
            if ended is None and until is not None and self._clock() >= until:
                ended = "timeout"
            if ended is None:
                continue
            if not self._abandon(slot):  # it finished just now: its answer stands
                return self._delivered(work, slot)
            if ended == "cancelled":
                return _Interrupted("cancelled", True, f"{name} was cancelled")
            if ended == "deadline":
                return _Interrupted("timeout", True, f"{name} timed out at the run's deadline")
            return _Interrupted("timeout", True, f"{name} timed out after {timeout:g} s")

    @staticmethod
    def _delivered(work: _Work, slot: _Slot) -> _Done:
        if slot.done is not None:
            return slot.done
        return work.failed("tool_error", f"{work.tool.name} failed (internal error)", slot.fault)


class _ToolHost:
    """The frame host: answers one call's protocol frames and keeps its counters and record.

    `admit(length)` is called with a frame's length before its bytes are read (spec 036's door
    does); `__call__(frame)` answers the frame. A raw `host=` calls only `__call__`, which then
    admits the frame itself, so every frame is counted exactly once. Nothing a frame, a gate or
    a tool does raises out of either."""

    def __init__(
        self,
        tools: Iterable[Tool],
        *,
        gate: Callable[[ToolCall], Any] | None = None,
        max_calls: int | None = 1000,
        invoke: Callable[[_Work], _Done | _Interrupted] = _inline,
    ) -> None:
        self._tools = tuple(tools)
        for t in self._tools:
            if not isinstance(t, Tool):
                raise TypeError(f"a frame host serves Tools; got {type(t).__name__}")
        self._by_name = {t.name: t for t in self._tools}
        if len(self._by_name) != len(self._tools):
            raise ValueError("two tools share a name")
        self._descriptors = [t.descriptor() for t in self._tools]
        self._gate, self._max_calls, self._invoke = gate, max_calls, invoke
        self._frames = 0
        self._abandoned = 0  # calls answered while their tool ran on, listed or not
        self._outcomes: list[ToolOutcome] = []
        self._pending: tuple[int, int] | None = None  # (seq, length) admitted, not yet read
        self._size = 0

    @property
    def record(self) -> ToolRecord:
        return ToolRecord(
            frames=self._frames,
            outcomes=tuple(self._outcomes),
            unlisted=self._frames - len(self._outcomes),
            abandoned=self._abandoned,
        )

    def _note(self, outcome: ToolOutcome) -> None:
        if outcome.abandoned:
            self._abandoned += 1
        if len(self._outcomes) < _RECORD_OUTCOMES:
            self._outcomes.append(outcome)

    def admit(self, length: int) -> bytes | None:
        """Count a frame from its length alone: an answer for one past `max_calls` or over
        the cap, else None, and the length is kept for `__call__` to check."""
        self._frames += 1
        seq = self._frames
        self._pending = None
        answer = None
        if self._max_calls is not None and seq > self._max_calls:
            kind = "budget_exceeded"
            message = f"this run allows {self._max_calls} tool frames; this was frame {seq}"
        elif length > _TOOL_REQUEST_BYTES:
            kind = "too_large"
            message = f"the frame is {length} bytes; at most {_TOOL_REQUEST_BYTES} (1 MiB)"
        else:
            self._pending = (seq, length)
            return None
        answer = _error(None, kind, message)
        self._note(ToolOutcome(seq, None, None, kind, message, length, len(answer)))
        return answer

    def __call__(self, frame: bytes) -> bytes:
        if not isinstance(frame, (bytes, bytearray, memoryview)):
            frame = b""  # a runner bug: answered as an empty frame, never raised
        frame = bytes(frame)
        if self._pending is None:
            early = self.admit(len(frame))
            if early is not None:
                return early
        assert self._pending is not None
        seq, admitted = self._pending
        self._pending = None
        self._size = len(frame)
        if admitted != len(frame):
            message = f"the door admitted {admitted} bytes but passed {len(frame)}"
            answer = _error(None, "protocol", message)
            fault = f"RuntimeError: {message}"
            self._note(
                ToolOutcome(seq, None, None, "protocol", message, len(frame), len(answer), fault)
            )
            return answer
        try:
            return self._answer(seq, frame)
        except Exception as e:  # a bug here must not reach the guest's door as a fault
            message = "the host could not answer this frame (internal error)"
            answer = _error(None, "protocol", message)
            self._note(
                ToolOutcome(
                    seq, None, None, "protocol", message, len(frame), len(answer), _fault(e)
                )
            )
            return answer

    def _answer(self, seq: int, frame: bytes) -> bytes:
        size = len(frame)
        op = name = None

        def failed(kind: str, message: str, frame_id: Any = None) -> bytes:
            answer = _error(frame_id, kind, message)
            self._note(ToolOutcome(seq, op, name, kind, _bounded(message), size, len(answer), None))
            return answer

        try:
            request = _parse(frame)
        except _Refused as e:
            return failed("protocol", str(e))
        frame_id = request.get("id")
        if type(frame_id) is not int or not 0 <= frame_id <= _MAX_ID:
            frame_id = None
        version = request.get("v")
        if type(version) is not int or version not in _PROTOCOLS:
            served = ", ".join(str(v) for v in _PROTOCOLS)
            return failed(
                "protocol",
                f"this host serves protocol version {served}; the frame asks for "
                f"{_echo(version) if 'v' in request else 'none'}",
                frame_id,
            )
        raw_op = request.get("op")
        if raw_op == "list":
            op = "list"
            body = {"v": PROTOCOL, "id": frame_id, "ok": True, "tools": self._descriptors}
            answer = _encode(body)
            if len(answer) > _TOOL_RESPONSE_BYTES:
                return failed("too_large", "the tool list is over the 16 MiB cap", frame_id)
            self._note(ToolOutcome(seq, op, None, "ok", None, size, len(answer)))
            return answer
        if raw_op != "call":
            reserved = " (batch is reserved for a later version)" if raw_op == "batch" else ""
            return failed(
                "protocol",
                f"unknown operation {_echo(raw_op)}; this host serves list and call{reserved}",
                frame_id,
            )
        op = "call"
        raw_name = request.get("tool")
        if not isinstance(raw_name, str):
            return failed("protocol", "a call names its tool with a string", frame_id)
        name = raw_name[:_ECHO_CHARS]
        t = self._by_name.get(raw_name)
        if t is None:
            offered = ", ".join(self._by_name) or "none"
            return failed(
                "unknown_tool",
                f"no tool named {_echo(raw_name)}; this run offers: {offered}",
                frame_id,
            )
        args = request.get("args", {})
        if not isinstance(args, dict):
            return failed(
                "invalid_arguments", f"{t.name}: the arguments must be an object", frame_id
            )
        error = _Validator(t._input_schema, keysets=t._keysets).check(args)
        if error is not None:
            return failed("invalid_arguments", f"{t.name}: {error}", frame_id)
        for k in args:
            if k in t._fixed:  # an open schema let a bound keyword through: as unknown (056)
                message = f"{t.name}: {_where(None)}: unknown argument {_echo(k)}"
                return failed("invalid_arguments", message, frame_id)
        work = _Work(self, seq, frame_id, t, args)
        done = self._invoke(work)
        if isinstance(done, _Interrupted):
            what = "timed out" if done.kind == "timeout" else "was cancelled"
            message = _bounded(done.message or f"{t.name} {what}")
            answer = _error(frame_id, done.kind, message)
            self._note(
                ToolOutcome(
                    seq, op, name, done.kind, message, size, len(answer), done.fault, done.abandoned
                )
            )
            return answer
        self._note(
            ToolOutcome(
                seq, op, name, done.outcome, done.message, size, len(done.answer), done.fault
            )
        )
        return done.answer


# -------------------------------------------------------------------------------------------------
# Stubs for a prompt (Decision 10). The guest package renders its signatures by the same rules.


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
    if isinstance(enum, list) and enum and all(_scalar(v) for v in enum):
        return "Literal[" + ", ".join(repr(v) for v in enum) + "]"
    if "const" in s and _scalar(s["const"]):
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


def _signature(descriptor: dict) -> inspect.Signature:
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


def _docstring(descriptor: dict) -> str:
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
