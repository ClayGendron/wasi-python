"""Prototype of the guest side: the module agent code imports as `tools`.

Research code for the memo, not the product. In the recommended design this module ships in the
stdlib zip; here the driver loads it from the program's text, because nothing else can reach the
guest's import path yet. It speaks protocol 1 (the memo's "The frame format") through `_host`.

On import it asks the host for the tool list (one door call) and makes one Python function per
tool, with a real signature and docstring, so `help(tools)` and `inspect.signature` work.
"""

import base64
import inspect
import json
import typing

import _host

PROTOCOL = 1


class ToolError(Exception):
    """A tool call that did not return a value. `kind` names why; the message is the host's."""

    kind = "tool_error"


class ToolDenied(ToolError, PermissionError):
    kind = "denied"


class ToolArgumentError(ToolError, TypeError):
    kind = "invalid_arguments"


class ToolTimeout(ToolError, TimeoutError):
    kind = "timeout"


class ToolCancelled(ToolError):
    kind = "cancelled"


class ToolResultTooLarge(ToolError):
    kind = "too_large"


class ToolBudgetExceeded(ToolError):
    kind = "budget_exceeded"


class ToolProtocolError(ToolError):
    kind = "protocol"


_ERRORS = {c.kind: c for c in (ToolError, ToolDenied, ToolArgumentError, ToolTimeout,
                               ToolCancelled, ToolResultTooLarge, ToolBudgetExceeded,
                               ToolProtocolError)}
_ERRORS["unknown_tool"] = ToolArgumentError
_next_id = 0


def _encode(value):
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {"$bytes": base64.b64encode(bytes(value)).decode("ascii")}
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if not isinstance(k, str):
                raise TypeError(f"tool arguments need str keys, not {type(k).__name__}")
            out[k] = _encode(v)
        return out
    if isinstance(value, (list, tuple)):
        return [_encode(v) for v in value]
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise TypeError(f"a tool argument cannot be {type(value).__name__}; pass JSON-like values")


def _decode(value):
    if isinstance(value, dict):
        if len(value) == 1 and "$bytes" in value:
            return base64.b64decode(value["$bytes"])
        return {k: _decode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_decode(v) for v in value]
    return value


def _send(op, **fields):
    global _next_id
    _next_id += 1
    frame = {"v": PROTOCOL, "id": _next_id, "op": op, **fields}
    try:
        raw = _host.call(json.dumps(frame, separators=(",", ":"), allow_nan=False).encode())
    except ConnectionRefusedError:
        raise ToolError("this run has no tools: the embedder passed none") from None
    except OSError:
        raise ToolProtocolError("the host faulted while answering a tool call") from None
    try:
        answer = json.loads(raw)
    except ValueError:
        raise ToolProtocolError("the host's answer is not a protocol frame") from None
    if not isinstance(answer, dict) or answer.get("v") != PROTOCOL or answer.get("id") != _next_id:
        raise ToolProtocolError("the host's answer does not match the request")
    if answer.get("ok") is True:
        return answer
    error = answer.get("error") or {}
    cls = _ERRORS.get(error.get("kind"), ToolError)
    raise cls(str(error.get("message", "the tool call failed")))


def call(name, /, **arguments):
    """Call the tool `name` with keyword arguments; return its value."""
    return _decode(_send("call", tool=name, args=_encode(arguments))["value"])


_JSON_TYPES = {"string": str, "integer": int, "number": float, "boolean": bool,
               "array": list, "object": dict, "null": type(None)}


def _annotation(schema):
    if "enum" in schema:
        return typing.Literal[tuple(schema["enum"])]
    kind = schema.get("type")
    if isinstance(kind, list):
        parts = [_annotation({"type": k}) for k in kind]
        return typing.Union[tuple(parts)] if parts else typing.Any
    if kind == "array" and isinstance(schema.get("items"), dict):
        return list[_annotation(schema["items"])]
    if kind == "object":
        return dict[str, typing.Any]
    return _JSON_TYPES.get(kind, typing.Any)


def _make(desc):
    name, schema = desc["name"], desc.get("input_schema") or {}
    props, required = schema.get("properties", {}), set(schema.get("required", ()))
    params, arg_lines = [], []
    # required first, so the signature is valid Python; all are keyword-or-positional
    for pname in sorted(props, key=lambda p: p not in required):
        p = props[pname]
        default = inspect.Parameter.empty if pname in required else p.get("default")
        params.append(inspect.Parameter(pname, inspect.Parameter.POSITIONAL_OR_KEYWORD,
                                        default=default, annotation=_annotation(p)))
        if p.get("description"):
            arg_lines.append(f"    {pname}: {p['description']}")
    ret = _annotation(desc["output_schema"]) if desc.get("output_schema") else typing.Any
    sig = inspect.Signature(params, return_annotation=ret)

    def tool_function(*args, **kwargs):
        try:
            bound = sig.bind(*args, **kwargs)
        except TypeError as e:
            raise ToolArgumentError(f"{name}(): {e}") from None
        return call(name, **bound.arguments)

    tool_function.__name__ = tool_function.__qualname__ = name
    tool_function.__module__ = __name__
    tool_function.__signature__ = sig
    doc = desc.get("description", "").strip()
    if arg_lines:
        doc += "\n\nArgs:\n" + "\n".join(arg_lines)
    tool_function.__doc__ = doc
    return tool_function


_descriptors = _send("list")["tools"]
__all__ = []
for _d in _descriptors:
    globals()[_d["name"]] = _make(_d)
    __all__.append(_d["name"])


def describe():
    """The host's tool descriptors: name, description, input_schema, annotations."""
    return [dict(d) for d in _descriptors]


def __getattr__(name):
    raise AttributeError(f"the host offers no tool {name!r}; it offers: {', '.join(__all__) or 'none'}")
