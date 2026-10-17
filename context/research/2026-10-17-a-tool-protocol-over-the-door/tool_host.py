"""Prototype of the host side: tools, a gate, and a `host=` callable that speaks protocol 1.

Research code for the memo, not the product. It shows that the whole protocol is a library on
top of the door: `ToolHost(...)` is a function from request bytes to response bytes, which is all
`wasi_python.run(host=...)` takes. The runner itself is unchanged.
"""

from __future__ import annotations

import asyncio
import base64
import concurrent.futures
import dataclasses
import inspect
import json
import re
import threading
import time
import typing
from collections.abc import Callable
from typing import Any

PROTOCOL = 1
NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,63}")


class ToolError(Exception):
    """Raised by a tool to fail with a message the guest may see. Any other exception is a fault:
    the guest sees only that the tool failed, and the embedder gets the exception."""


class Denied(Exception):
    """Raised (or returned) by a gate to refuse a call; the message reaches the guest."""


@dataclasses.dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_schema: dict
    fn: Callable[..., Any]
    is_async: bool = False
    output_schema: dict | None = None
    annotations: dict = dataclasses.field(default_factory=dict)  # MCP's hints: read_only, ...
    timeout_s: float | None = None
    errors: tuple[type[BaseException], ...] = (ToolError,)  # exceptions whose message may cross

    def descriptor(self) -> dict:
        d = {"name": self.name, "description": self.description, "input_schema": self.input_schema}
        if self.output_schema:
            d["output_schema"] = self.output_schema
        if self.annotations:
            d["annotations"] = self.annotations
        return d


@dataclasses.dataclass(frozen=True)
class ToolCall:
    """What the gate sees: decided by the host, never taken from the guest's frame."""

    seq: int  # the host's own count of calls in this run, from 1
    tool: Tool
    arguments: dict  # validated against tool.input_schema
    request_bytes: int
    calls_so_far: int
    bytes_so_far: int


# ---- schemas from Python signatures (a small subset; a real build would document it) ----

_PY_TO_JSON = {str: "string", int: "integer", float: "number", bool: "boolean", type(None): "null"}


def _schema_for(ann: Any) -> dict:
    if ann in _PY_TO_JSON:
        return {"type": _PY_TO_JSON[ann]}
    origin, args = typing.get_origin(ann), typing.get_args(ann)
    if origin is typing.Literal:
        return {"enum": list(args)}
    if origin in (typing.Union, getattr(__import__("types"), "UnionType", None)):
        return {"anyOf": [_schema_for(a) for a in args]}
    if origin is list:
        return {"type": "array", "items": _schema_for(args[0])} if args else {"type": "array"}
    if origin is dict or ann is dict:
        return {"type": "object", "additionalProperties": True}
    if ann is bytes:
        return {"type": "object", "properties": {"$bytes": {"type": "string"}},
                "required": ["$bytes"]}
    raise TypeError(f"no JSON Schema for {ann!r}; pass input_schema=")


def _arg_docs(doc: str) -> dict[str, str]:
    out, inside = {}, False
    for line in doc.splitlines():
        if line.strip() in ("Args:", "Arguments:"):
            inside = True
            continue
        if inside:
            m = re.match(r"\s+(\w+)(?:\s*\(.*?\))?:\s*(.+)", line)
            if m:
                out[m[1]] = m[2].strip()
            elif line.strip() and not line.startswith((" ", "\t")):
                inside = False
    return out


def tool(fn=None, *, name=None, description=None, input_schema=None, timeout_s=None,
         read_only=False, destructive=False):
    """Decorator: a function's signature and docstring become the tool's schema."""

    def wrap(f):
        doc = inspect.getdoc(f) or ""
        hints = typing.get_type_hints(f)
        if input_schema is None:
            props, required, docs = {}, [], _arg_docs(doc)
            for p in inspect.signature(f).parameters.values():
                s = _schema_for(hints.get(p.name, str))
                if p.name in docs:
                    s["description"] = docs[p.name]
                if p.default is inspect.Parameter.empty:
                    required.append(p.name)
                else:
                    s["default"] = p.default
                props[p.name] = s
            schema = {"type": "object", "properties": props, "required": required,
                      "additionalProperties": False}
        else:
            schema = input_schema
        n = name or f.__name__
        if not NAME.fullmatch(n):
            raise ValueError(f"tool name {n!r} must match {NAME.pattern}")
        ann = {k: True for k, v in (("read_only", read_only), ("destructive", destructive)) if v}
        return Tool(n, description or doc.split("\n\n")[0], schema, f,
                    inspect.iscoroutinefunction(f), annotations=ann, timeout_s=timeout_s)

    return wrap(fn) if fn is not None else wrap


def from_langchain(lc_tool) -> Tool:
    """A LangChain BaseTool as a Tool: its schema, its own pydantic validation, its ToolException."""
    from langchain_core.tools import ToolException

    schema = lc_tool.tool_call_schema.model_json_schema()
    schema.pop("title", None)
    schema.pop("description", None)
    is_async = getattr(lc_tool, "func", None) is None and getattr(lc_tool, "coroutine", None) is not None
    fn = (lambda **kw: lc_tool.ainvoke(kw)) if is_async else (lambda **kw: lc_tool.invoke(kw))
    name = re.sub(r"[^A-Za-z0-9_]", "_", lc_tool.name)
    return Tool(name, lc_tool.description, schema, fn, is_async, errors=(ToolError, ToolException))


# ---- validation: never trust the guest ----


def validate(value: Any, schema: dict, path: str = "$") -> None:
    """A strict subset of JSON Schema: type, enum, properties, required, additionalProperties
    (closed unless the schema opens it), items, anyOf. No coercion: "7" is not an integer."""
    if "anyOf" in schema:
        for alt in schema["anyOf"]:
            try:
                validate(value, alt, path)
                return
            except ValueError:
                pass
        raise ValueError(f"{path}: matches none of the allowed shapes")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{path}: must be one of {schema['enum']}")
    kinds = schema.get("type")
    if kinds is not None:
        kinds = kinds if isinstance(kinds, list) else [kinds]
        ok = {
            "string": isinstance(value, str), "boolean": isinstance(value, bool),
            "integer": isinstance(value, int) and not isinstance(value, bool),
            "number": isinstance(value, (int, float)) and not isinstance(value, bool),
            "null": value is None, "array": isinstance(value, list),
            "object": isinstance(value, dict),
        }
        if not any(ok.get(k, False) for k in kinds):
            raise ValueError(f"{path}: expected {' or '.join(kinds)}, got {type(value).__name__}")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for r in schema.get("required", ()):
            if r not in value:
                raise ValueError(f"{path}: missing required argument {r!r}")
        extra = schema.get("additionalProperties", False)
        for k, v in value.items():
            if k in props:
                validate(v, props[k], f"{path}.{k}")
            elif extra is False:
                raise ValueError(f"{path}: unexpected argument {k!r}")
            elif isinstance(extra, dict):
                validate(v, extra, f"{path}.{k}")
    if isinstance(value, list) and isinstance(schema.get("items"), dict):
        for i, v in enumerate(value):
            validate(v, schema["items"], f"{path}[{i}]")


def _decode(v):
    if isinstance(v, dict):
        if len(v) == 1 and "$bytes" in v and isinstance(v["$bytes"], str):
            return base64.b64decode(v["$bytes"], validate=True)
        return {k: _decode(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_decode(x) for x in v]
    return v


def _encode(v):
    if isinstance(v, (bytes, bytearray, memoryview)):
        return {"$bytes": base64.b64encode(bytes(v)).decode("ascii")}
    if isinstance(v, dict):
        return {str(k): _encode(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_encode(x) for x in v]
    if v is None or isinstance(v, (str, bool, int, float)):
        return v
    raise TypeError(f"a tool returned {type(v).__name__}, which has no JSON form")


# ---- the host callable ----


class _Fail(Exception):
    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind


class ToolHost:
    """`run(argv, host=ToolHost(tools, gate=...))`. One per run; it keeps that run's counts."""

    def __init__(self, tools, *, gate, max_calls=1000, request_bytes=1 << 20,
                 response_bytes=16 << 20, call_timeout_s=30.0, deadline_s=None, cancel=None):
        self.tools = {t.name: t for t in tools}
        if len(self.tools) != len(tools):
            raise ValueError("two tools share a name")
        self.gate, self.max_calls = gate, max_calls
        self.request_bytes, self.response_bytes = request_bytes, response_bytes
        self.call_timeout_s, self.cancel = call_timeout_s, cancel
        self.ends_at = None if deadline_s is None else time.monotonic() + deadline_s
        self.calls = 0
        self.bytes_in = self.bytes_out = 0
        self.frames = 0
        self.record: list[tuple[str, str, str]] = []  # (op, tool, outcome kind) per frame
        self.faults: list[BaseException] = []  # exceptions the guest saw only as "failed"
        self._pool = concurrent.futures.ThreadPoolExecutor(4, thread_name_prefix="tool")
        self._loop = asyncio.new_event_loop()
        threading.Thread(target=self._loop.run_forever, daemon=True).start()

    def __call__(self, frame: bytes) -> bytes:
        self.frames += 1
        self.bytes_in += len(frame)
        mark = len(self.record)
        rid = None
        try:
            if len(frame) > self.request_bytes:
                raise _Fail("too_large", f"the request is over {self.request_bytes} bytes")
            try:
                req = json.loads(frame)
            except (ValueError, RecursionError):
                raise _Fail("protocol", "the request is not JSON") from None
            if not isinstance(req, dict):
                raise _Fail("protocol", "the request is not an object")
            rid = req.get("id") if isinstance(req.get("id"), int) else None
            if req.get("v") != PROTOCOL:
                raise _Fail("protocol", f"protocol {req.get('v')!r} is not served; this host serves {PROTOCOL}")
            op = req.get("op")
            if op == "list":
                body = {"tools": [t.descriptor() for t in self.tools.values()]}
                self.record.append(("list", "", "ok"))
            elif op == "call":
                body = {"value": self._call(req, len(frame))}
            else:
                raise _Fail("protocol", f"unknown op {op!r}")
            out = self._frame(rid, True, body)
        except _Fail as f:
            if len(self.record) == mark:  # failed before any op recorded itself
                self.record.append(("?", "", f.kind))
            out = self._frame(rid, False, {"error": {"kind": f.kind, "message": str(f)}})
        if len(out) > self.response_bytes:
            op, name, _ = self.record[-1] if len(self.record) > mark else ("?", "", "")
            self.record[mark:] = [(op, name, "too_large")]
            out = json.dumps({"v": PROTOCOL, "id": rid, "ok": False, "error": {
                "kind": "too_large", "message": f"the result is over {self.response_bytes} bytes"}}).encode()
        self.bytes_out += len(out)
        return out

    def _frame(self, rid, ok, body) -> bytes:
        return json.dumps({"v": PROTOCOL, "id": rid, "ok": ok, **body}, separators=(",", ":"),
                          allow_nan=False).encode()

    def _call(self, req: dict, size: int):
        name, args = req.get("tool"), req.get("args", {})
        t = self.tools.get(name) if isinstance(name, str) else None
        if t is None:
            self.record.append(("call", str(name)[:64], "unknown_tool"))
            raise _Fail("unknown_tool", f"no tool named {str(name)[:64]!r}")
        if self.calls >= self.max_calls:
            self.record.append(("call", name, "budget_exceeded"))
            raise _Fail("budget_exceeded", f"this run may make {self.max_calls} tool calls")
        self.calls += 1
        try:
            validate(args, t.input_schema)
            args = _decode(args)
        except (ValueError, TypeError) as e:
            self.record.append(("call", name, "invalid_arguments"))
            raise _Fail("invalid_arguments", f"{name}: {e}") from None
        call = ToolCall(self.calls, t, args, size, self.calls, self.bytes_in)
        try:
            verdict = self.gate(call)
        except Denied as e:
            verdict = e
        if verdict is not None and verdict is not True:
            self.record.append(("call", name, "denied"))
            raise _Fail("denied", str(verdict) or f"{name} was refused")
        outcome = self._run(t, args)
        self.record.append(("call", name, "ok"))
        try:
            return _encode(outcome)
        except TypeError as e:
            self.faults.append(e)
            raise _Fail("tool_error", f"{name} failed (internal error)") from None

    def _run(self, t: Tool, args: dict):
        timeout = min(x for x in (t.timeout_s, self.call_timeout_s, self._left()) if x is not None)
        if t.is_async:
            fut = asyncio.run_coroutine_threadsafe(t.fn(**args), self._loop)
        else:
            fut = self._pool.submit(t.fn, **args)
        ends = time.monotonic() + timeout
        while True:  # wait in slices, so the run's cancel is seen while a tool blocks
            if self.cancel is not None and self.cancel.is_set():
                fut.cancel()
                self.record.append(("call", t.name, "cancelled"))
                raise _Fail("cancelled", "the run was cancelled")
            left = ends - time.monotonic()
            if left <= 0:
                fut.cancel()  # an async tool's task is cancelled; a thread runs on, unseen
                self.record.append(("call", t.name, "timeout"))
                raise _Fail("timeout", f"{t.name} took longer than {timeout:g} s")
            try:
                return fut.result(timeout=min(left, 0.05))
            except concurrent.futures.TimeoutError:
                continue
            except t.errors as e:
                self.record.append(("call", t.name, "tool_error"))
                raise _Fail("tool_error", str(e)[:4096]) from None
            except Exception as e:  # noqa: BLE001  a fault: the guest learns nothing from it
                self.faults.append(e)
                self.record.append(("call", t.name, "tool_error"))
                raise _Fail("tool_error", f"{t.name} failed (internal error)") from None

    def _left(self):
        return None if self.ends_at is None else max(0.0, self.ends_at - time.monotonic())


def allow_all(call: ToolCall) -> None:
    """The explicit gate that allows every call: passing it is the embedder's decision."""
    return None


def stubs(tools) -> str:
    """Python stubs for a prompt: the same signatures the guest's functions carry."""
    lines = ["# import tools", ""]
    for t in tools:
        props = t.input_schema.get("properties", {})
        req = set(t.input_schema.get("required", ()))
        names = {"string": "str", "integer": "int", "number": "float", "boolean": "bool",
                 "array": "list", "object": "dict", "null": "None"}
        params = []
        for p in sorted(props, key=lambda p: p not in req):
            ty = names.get(props[p].get("type"), "Any")
            params.append(p + ": " + ty + ("" if p in req else f" = {props[p].get('default')!r}"))
        lines.append(f"def {t.name}({', '.join(params)}):")
        lines.append(f'    """{t.description}"""')
        lines.append("")
    return "\n".join(lines)
