"""The embedder's tools, one function each (spec 031).

Importing this module sends one `list` frame through the door; each tool then has a function
here with its signature, its description as the docstring, and its descriptor as `.descriptor`.
A call checks its arguments against the signature, sends only the ones given, by keyword, and
returns the tool's value or raises the class for the kind of failure (see `host`). Nothing else
here is public, so `from host.tools import *` brings the tools alone.
"""

import binascii as _binascii
import inspect as _inspect
import json as _json
import keyword as _keyword
import re as _re

import _host as _door

from . import PROTOCOL as _PROTOCOL
from . import ToolArgumentError as _ToolArgumentError
from . import ToolBudgetExceeded as _ToolBudgetExceeded
from . import ToolCancelled as _ToolCancelled
from . import ToolDenied as _ToolDenied
from . import ToolError as _ToolError
from . import ToolProtocolError as _ToolProtocolError
from . import ToolTimeout as _ToolTimeout
from . import ToolTooLarge as _ToolTooLarge

_CLASS_OF_KIND = {
    "protocol": _ToolProtocolError,
    "unknown_tool": _ToolArgumentError,
    "invalid_arguments": _ToolArgumentError,
    "denied": _ToolDenied,
    "tool_error": _ToolError,
    "timeout": _ToolTimeout,
    "cancelled": _ToolCancelled,
    "too_large": _ToolTooLarge,
    "budget_exceeded": _ToolBudgetExceeded,
}
_NESTING = 62  # the most a call's arguments may nest: the frame, with its envelope, nests 64
_NAME = _re.compile(r"[A-Za-z][A-Za-z0-9_]{0,63}")
_next_id = [0]


class _NotProtocol(Exception):
    pass


def _encode(value, where, depth=0):
    """The protocol's JSON form of an argument (spec 031, Decision 6)."""
    if depth > _NESTING:
        raise _ToolArgumentError(f"{where} nests deeper than {_NESTING} levels")
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise _ToolArgumentError(f"{where} is {value!r}; only finite numbers cross")
        return float(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {"$bytes": _binascii.b2a_base64(bytes(value), newline=False).decode("ascii")}
    if isinstance(value, dict):
        if "$bytes" in value:
            raise _ToolArgumentError(f'{where}: a dict with the key "$bytes" would read as bytes')
        out = {}
        for k, v in value.items():
            if not isinstance(k, str):
                raise _ToolArgumentError(f"{where} has a key of type {type(k).__name__}, not str")
            out[k] = _encode(v, f"{where}[{k!r}]", depth + 1)
        return out
    if isinstance(value, (list, tuple)):
        return [_encode(v, f"{where}[{i}]", depth + 1) for i, v in enumerate(value)]
    import numbers as _numbers  # only here: numpy registers its scalars with it

    if isinstance(value, _numbers.Integral):
        return int(value)
    if isinstance(value, _numbers.Real):
        return _encode(float(value), where, depth)
    hint = ""
    if hasattr(value, "tolist"):
        hint = "; pass .tolist()"
    elif hasattr(value, "to_dict"):
        hint = '; pass .to_dict("records")'
    raise _ToolArgumentError(f"{where} is a {type(value).__name__}, which has no JSON form{hint}")


def _decode(value):
    """`{"$bytes": "<base64>"}` back into bytes, at every level of an answer."""
    if isinstance(value, list):
        return [_decode(v) for v in value]
    if isinstance(value, dict):
        if len(value) == 1 and "$bytes" in value and isinstance(value["$bytes"], str):
            try:
                return _binascii.a2b_base64(value["$bytes"].encode("ascii"), strict_mode=True)
            except (_binascii.Error, UnicodeEncodeError):
                raise _NotProtocol('a "$bytes" value is not strict base64') from None
        return {k: _decode(v) for k, v in value.items()}
    return value


def _exchange(request):
    """Send one frame and read its answer: (ok, the answer). ConnectionRefusedError passes
    through (no host); anything malformed is _NotProtocol."""
    _next_id[0] += 1
    frame_id = _next_id[0]
    frame = {"v": _PROTOCOL, "id": frame_id}
    frame.update(request)
    text = _json.dumps(frame, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    try:
        data = text.encode("utf-8")
    except UnicodeEncodeError:
        raise _ToolArgumentError("an argument holds a lone surrogate, which is not UTF-8") from None
    try:
        raw = _door.call(data)
    except ConnectionRefusedError:
        raise
    except OSError as e:
        raise _ToolProtocolError(f"the door failed: {e}") from None
    try:
        answer = _json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        raise _NotProtocol("the answer is not JSON") from None
    if not isinstance(answer, dict) or type(answer.get("v")) is not int:
        raise _NotProtocol("the answer is not a protocol 1 object")
    if answer["v"] != _PROTOCOL:
        raise _NotProtocol(f"the answer is protocol {answer['v']}, not {_PROTOCOL}")
    answer_id = answer.get("id")  # null when the host refused the frame unread
    if answer_id is not None and (type(answer_id) is not int or answer_id != frame_id):
        raise _NotProtocol("the answer's id does not match the call")
    ok = answer.get("ok")
    if ok is not True and ok is not False:
        raise _NotProtocol("the answer has no ok")
    return ok, answer


def _failure(answer):
    error = answer.get("error")
    error = error if isinstance(error, dict) else {}
    kind = error.get("kind")
    kind = kind if isinstance(kind, str) else "tool_error"
    message = error.get("message")
    e = _CLASS_OF_KIND.get(kind, _ToolError)(message if isinstance(message, str) else "")
    e.kind = kind
    return e


def _call(name, arguments):
    try:
        ok, answer = _exchange({"op": "call", "tool": name, "args": arguments})
    except ConnectionRefusedError:
        raise _ToolProtocolError("no host is bound to the door") from None
    except _NotProtocol as e:
        raise _ToolProtocolError(f"{name}: {e}") from None
    if not ok:
        raise _failure(answer)
    try:
        return _decode(answer.get("value"))
    except (_NotProtocol, RecursionError) as e:
        raise _ToolProtocolError(f"{name}: {e}") from None


# The signature and docstring rules match the host's `wasi_python.tools.stubs` exactly.


class _Hint:
    """An annotation shown as its text, the same on every Python version."""

    __slots__ = ("text",)

    def __init__(self, text):
        self.text = text

    def __repr__(self):
        return self.text

    def __eq__(self, other):
        return isinstance(other, _Hint) and other.text == self.text

    def __hash__(self):
        return hash(self.text)


class _Omitted:
    """The default shown for an optional argument whose schema gives none: it is not sent."""

    def __repr__(self):
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


def _scalar(value):
    if value is None or type(value) in (bool, int, str):
        return True
    return type(value) is float and value == value and abs(value) != float("inf")


def _hint_text(s, depth=0):
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
            texts = []
            for b in branches:
                text = _hint_text(b, depth + 1)
                if text not in texts:
                    texts.append(text)
            return " | ".join(texts)
    t = s.get("type")
    if isinstance(t, list) and t:
        return " | ".join(_hint_text(dict(s, type=one), depth + 1) for one in t)
    if t == "string" and s.get("contentEncoding") == "base64":
        return "bytes"
    if t == "array" and isinstance(s.get("items"), dict):
        return f"list[{_hint_text(s['items'], depth + 1)}]"
    extra = s.get("additionalProperties")
    if t == "object" and isinstance(extra, dict) and not s.get("properties"):
        return f"dict[str, {_hint_text(extra, depth + 1)}]"
    if isinstance(t, str) and t in _TYPE_TEXT:
        return _TYPE_TEXT[t]
    return "Any"


def _default(value):
    try:
        return _decode(value)
    except _NotProtocol:
        return value


def _signature(descriptor):
    """Required parameters first, each by position or keyword; `(**kwargs)` when the property
    names cannot make a signature."""
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
                default = _inspect.Parameter.empty
            elif isinstance(p, dict) and "default" in p:
                default = _default(p["default"])
            else:
                default = _OMITTED
            kind = _inspect.Parameter.POSITIONAL_OR_KEYWORD
            params.append(
                _inspect.Parameter(n, kind, default=default, annotation=_Hint(_hint_text(p)))
            )
        if "outputSchema" in descriptor:
            returns = _Hint(_hint_text(descriptor["outputSchema"]))
        else:
            returns = _inspect.Signature.empty
        return _inspect.Signature(params, return_annotation=returns)
    except (ValueError, TypeError):
        return _inspect.Signature([_inspect.Parameter("kwargs", _inspect.Parameter.VAR_KEYWORD)])


def _docstring(descriptor):
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


def _function(descriptor):
    name = descriptor["name"]
    signature = _signature(descriptor)
    by_keyword = [p for p in signature.parameters.values() if p.kind is p.VAR_KEYWORD]

    def call(*args, **kwargs):
        try:
            bound = signature.bind(*args, **kwargs)  # defaults are not applied, nor sent
        except TypeError as e:
            raise _ToolArgumentError(f"{name}(): {e}") from None
        given = dict(bound.arguments)
        if by_keyword:
            given = given.get(by_keyword[0].name, {})
        arguments = {k: _encode(v, f"{name}(): argument {k!r}") for k, v in given.items()}
        return _call(name, arguments)

    call.__name__ = call.__qualname__ = name
    call.__module__ = __name__
    call.__doc__ = _docstring(descriptor)
    call.__signature__ = signature
    call.descriptor = _json.loads(_json.dumps(descriptor))
    return call


def _discover():
    try:
        ok, answer = _exchange({"op": "list"})
    except ConnectionRefusedError:
        raise ImportError("this run has no tools: the embedder passed none") from None
    except (_NotProtocol, _ToolError) as e:
        raise ImportError(f"the host's answer is not protocol 1: {e}") from None
    if not ok:
        e = _failure(answer)
        raise ImportError(f"the host refused the tool list ({e.kind}): {e}")
    found = answer.get("tools")
    if not isinstance(found, list):
        raise ImportError("the host's answer is not protocol 1: it lists no tools")
    functions = {}
    for i, d in enumerate(found):
        name = d.get("name") if isinstance(d, dict) else None
        if not isinstance(name, str) or not _NAME.fullmatch(name) or _keyword.iskeyword(name):
            raise ImportError(f"the host's answer is not protocol 1: tool {i} has no valid name")
        if name in functions:
            raise ImportError(f"the host's answer is not protocol 1: two tools named {name!r}")
        functions[name] = _function(d)
    return functions


_functions = _discover()
globals().update(_functions)
__all__ = list(_functions)


def __getattr__(name):
    offered = ", ".join(__all__) or "none"
    raise AttributeError(f"module {__name__!r} has no tool {name!r}; this run offers: {offered}")
