"""The tool protocol's schema rules, which know nothing of frames, threads or the guest.

The subset of JSON Schema the protocol admits, how a Python signature maps into it, and how a
value is checked against a schema within a budget of steps, so that an answer is the same on
every host. A tool's schema is derived and vetted here when the tool is made; each call's
arguments are checked here before its tool runs. The JSON-value helpers live here too, below
both of their readers: a value's JSON form, and a value as a message shows it.
"""

from __future__ import annotations

import binascii
import inspect
import keyword
import math
import numbers
import types
import typing
from collections.abc import Callable, Iterable, Mapping
from typing import Any

_TOOL_VALIDATION_STEPS = 100_000  # schema nodes visited and item keys made, per frame
_TOOL_NESTING = 64  # a frame's nesting, its envelope included
_VALUE_NESTING = _TOOL_NESTING - 2  # inside a call's args, or a result's value
_ECHO_CHARS = 64  # the longest piece of guest text a message repeats
_Json = dict[str, Any]  # a JSON object as json.loads gives it: a schema, a descriptor, a frame
_TOO_COMPLEX = "the arguments are too complex to check"
_SAME_VALUE_CHAIN = 8  # the most schema nodes a $ref, anyOf or oneOf chain passes on one value
_JSON_TYPES = ("string", "integer", "number", "boolean", "null", "array", "object")
# What the validator checks, what it ignores, and what descends into the value.
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


# -------------------------------------------------------------------------------------------------
# A schema from a signature


def _derived(
    name: str,
    fn: Any,
    hints: dict[str, Any],
    args_doc: dict[str, str],
    fixed: frozenset[str] = frozenset(),
) -> _Json:
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError) as e:
        raise TypeError(f"{name}: its signature cannot be read ({e})") from e
    properties: dict[str, Any] = {}
    required: list[str] = []
    for p in sig.parameters.values():
        if p.name in fixed:
            continue  # bound by a partial: not the guest's to read or set
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


def _schema_of(hint: Any, where: str) -> _Json:
    """The hints a tool's signature may carry, mapped to JSON Schema."""
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
# Vetting a schema


def _vet(name: str, root: _Json, validates_input: bool) -> list[Any]:
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
                "the guest calls the tool with it as a keyword argument (rename it and map it "
                "back, as https://claygendron.github.io/wasi-python/reference/tool-protocol/ "
                "shows under Names)"
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

    def __init__(self, where: str, root: _Json, validates_input: bool) -> None:
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
        by the value's depth times that, never by the host Python's limit."""
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


def _children(s: _Json) -> list[tuple[str, Any, bool]]:
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


def _resolve(root: _Json, ref: Any) -> Any:
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


def _number(value: Any) -> typing.TypeGuard[int | float]:
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
# The validator


class _TooComplex(Exception):
    pass


class _Invalid(Exception):
    pass


_EMPTY: _Json = {}
_DELEGATES = ("$ref", "anyOf", "oneOf")
_OBJECT_WORDS = frozenset(
    ("properties", "additionalProperties", "required", "minProperties", "maxProperties")
)
_ARRAY_WORDS = frozenset(("items", "prefixItems", "minItems", "maxItems", "uniqueItems"))


_KeySets = dict[tuple[int, str], tuple[_Json, frozenset[Any]]]


def _keysets(nodes: Iterable[Any]) -> _KeySets:
    """Each `enum` and `const` as a set of keys, made once when the tool is made, so checking a
    value against them is one key and one lookup. Each entry keeps its node, and is
    used only for that same object: an id alone can be reused by another node once a Tool is
    copied or unpickled and the original freed."""
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
    equality, counting its work against a budget.

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

    def keyset(self, s: _Json, word: str) -> frozenset[Any]:
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

    def object(self, s: _Json, value: _Json, at: Any) -> None:
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

    def array(self, s: _Json, value: list[Any], at: Any) -> None:
        n = len(value)
        if "minItems" in s and n < s["minItems"]:
            raise _Invalid(f"{_where(at)}: at least {s['minItems']} items, got {n}")
        if "maxItems" in s and n > s["maxItems"]:
            raise _Invalid(f"{_where(at)}: at most {s['maxItems']} items, got {n}")
        if s.get("uniqueItems"):
            seen: set[Any] = set()
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

    def length(self, s: _Json, n: int, at: Any, unit: str) -> None:
        if "minLength" in s and n < s["minLength"]:
            raise _Invalid(f"{_where(at)}: at least {s['minLength']} {unit}, got {n}")
        if "maxLength" in s and n > s["maxLength"]:
            raise _Invalid(f"{_where(at)}: at most {s['maxLength']} {unit}, got {n}")

    def number(self, s: _Json, x: int | float, at: Any) -> None:
        if _number(b := s.get("minimum")) and not x >= b:
            raise _Invalid(f"{_where(at)}: must be at least {b}, got {_shown(x)}")
        if _number(b := s.get("maximum")) and not x <= b:
            raise _Invalid(f"{_where(at)}: must be at most {b}, got {_shown(x)}")
        if _number(b := s.get("exclusiveMinimum")) and not x > b:
            raise _Invalid(f"{_where(at)}: must be above {b}, got {_shown(x)}")
        if _number(b := s.get("exclusiveMaximum")) and not x < b:
            raise _Invalid(f"{_where(at)}: must be below {b}, got {_shown(x)}")
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


def _is_type(name: str, value: Any, s: _Json) -> bool:
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


def _type_name(name: str, s: _Json) -> str:
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
# JSON values: as a message shows them, and as an answer carries them


def _echo(value: Any) -> str:
    """A piece of guest text for a message: a string cut to 64 characters first; any other
    value named by its kind and size (`_shown`), never formatted whole."""
    if not isinstance(value, str):
        return _shown(value)
    cut = value[:_ECHO_CHARS]
    return f"'{cut}'" + ("..." if len(value) > _ECHO_CHARS else "")


def _shown(value: Any) -> str:
    """A value for a message, at a cost bounded whatever its size."""
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


class _NotJSON(Exception):
    pass


def _to_json(value: Any, depth: int) -> Any:
    """A value's JSON form, which mirrors the guest's encoding."""
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
