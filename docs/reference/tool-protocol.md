# Tool protocol

This page is the wire format through which guest code calls the host's tools. Read it if you
serve tools from a host of your own, in any language. If you use `run(tools=...)` from Python,
the runner speaks it for you: see [Tools](../how-to/tools.md).

## The door and the protocol

`python.wasm` has one custom import, the *door*. Through it, the guest hands the host a request
as bytes and gets a response as bytes. The door gives those bytes no meaning of its own.

The tool protocol is one meaning for them. Guest code writes `from host import tools`, then calls
a tool such as `tools.lookup_region("EMEA")`. The guest's half is the pure-Python package `host`,
in the stdlib zip. The host's half in Python is `wasi_python.tools`. Another host serves the
protocol from its own door function, by the rules below.

The protocol is optional. If the door never answers it, `from host import tools` raises
`ImportError`.

## Version

`wasi_python.tools.PROTOCOL` is the version this host speaks: `1`. The rules on this page belong
to the protocol, not to the host's Python or its settings, so an answer is the same on every
host. They change only with the version.

- A field a peer may ignore can be added within a version.
- A field a peer must act on bumps `v`.
- An unknown version or operation gets a `protocol` answer naming what the host serves.
- The operation `batch` is reserved.

## Frames

A *frame* is one compact UTF-8 JSON object, sent as one door call, each way.

- `v` is the protocol version, `1`.
- `id` is the guest's number for the frame. The host echoes it when it is an integer from 0 to
  2\*\*53 - 1, and answers `null` otherwise. The host never trusts it.

```text
request    {"v": 1, "id": 7, "op": "list"}
           {"v": 1, "id": 8, "op": "call", "tool": "lookup_region", "args": {"code": "EMEA"}}
answer     {"v": 1, "id": 7, "ok": true, "tools": [descriptor, ...]}
           {"v": 1, "id": 8, "ok": true, "value": <JSON>}
           {"v": 1, "id": 8, "ok": false, "error": {"kind": "denied", "message": "..."}}
descriptor {"name", "description", "inputSchema", "outputSchema"?, "annotations"?}
bytes      {"$bytes": "<base64>"}
```

There are two operations:

- `list` asks for the tools. The answer's `tools` holds one *descriptor* per tool, in the order
  the embedder gave them. A descriptor uses the Model Context Protocol's (MCP's) field names.
- `call` calls one tool by name with its arguments in `args`. The answer holds the tool's result
  in `value`, or an `error` with a `kind` and a `message`.

Bytes travel as an object with exactly one key, `$bytes`, holding strict base64.

## Kinds of failure

Each failure has a kind. On the guest's side, each kind is raised as a subclass of
`host.ToolError`, with the kind in its `.kind` attribute.

| kind | guest class | when |
|---|---|---|
| `protocol` | `ToolProtocolError` | The frame breaks a rule below, or the answer does not match. |
| `unknown_tool` | `ToolArgumentError` (also `TypeError`) | No tool has that name. |
| `invalid_arguments` | `ToolArgumentError` | The arguments do not fit the input schema. |
| `denied` | `ToolDenied` (also `PermissionError`) | The gate or the tool refused. |
| `tool_error` | `ToolError` | The tool failed; only a message it chose crosses. |
| `timeout` | `ToolTimeout` (also `TimeoutError`) | The call ran out of time. |
| `cancelled` | `ToolCancelled` | The run was cancelled during the call. |
| `too_large` | `ToolTooLarge` | A request over 1 MiB, or an answer over 16 MiB. |
| `budget_exceeded` | `ToolBudgetExceeded` | The run's frames are used up (1,000 by default), or its request bytes (16 MiB by default). |

A cancelled run is stopped at the guest's next function entry, so do not rely on
`except ToolCancelled` for clean-up.

## The rules for a request

The host checks a request in this order, before it reads any schema. Each failure is a
`protocol` answer.

1. At most 1 MiB, judged from the length before the bytes are read.
2. Strict UTF-8, never UTF-16 or UTF-32.
3. Nested at most 64 levels, the envelope included, counted outside strings. That leaves 62
   levels inside `args`.
4. JSON with no `NaN` or `Infinity`, no number that overflows a double (`1e400`), no integer
   literal over 64 characters, and no repeated key.
5. No lone surrogate (`"\ud800"`) in a key or a value. A surrogate pair is fine.
6. An object at the top.

Then, in order:

- a `{"$bytes": "<base64>"}` object becomes bytes; any other `$bytes` object is a `protocol`
  answer;
- the version and the operation are checked;
- the tool's name is looked up (`unknown_tool`);
- the arguments are checked against the tool's input schema (`invalid_arguments`).

Every frame counts toward the run's budget, including the discovery frame that
`from host import tools` sends. Past the budget, the guest gets `ToolBudgetExceeded` and runs on.
If the discovery frame itself is refused, `from host import tools` raises `ImportError`.

Answers are encoded as ASCII JSON, so an echoed lone surrogate still encodes. A message is at
most 4,096 characters, and each piece of guest text it repeats is cut to 64 characters first.

## The schema subset

A tool's input schema is a subset of JSON Schema. The validator checks these keywords:

- `type`, `enum`, `const`;
- `properties`, `required`, `additionalProperties`, `minProperties`, `maxProperties`;
- `items` (one schema), `prefixItems`, `minItems`, `maxItems`, `uniqueItems`;
- `anyOf`, `oneOf`, and a local `$ref` into `$defs` or `definitions`;
- the four numeric bounds, and `multipleOf` (a positive integer);
- `minLength` and `maxLength`, in code points;
- `contentEncoding: "base64"`.

When `additionalProperties` is absent, it closes an object schema that lists `properties`. That
is stricter than JSON Schema.

The validator ignores the annotations: `title`, `description`, `default`, `examples`, `format`,
`deprecated`, `readOnly`, `writeOnly`, `contentMediaType`, `discriminator`, `$schema`, `$id` and
`$comment`.

`tool()` refuses any other keyword, unless the tool checks its own input
(`validates_input=True`); those keywords are then skipped. `pattern` is refused on purpose: a
regular expression run on a megabyte of guest text can backtrack without end. The array form of
`items`, a `$ref` that is not local, and a `$ref` cycle that never descends into the value are
refused even then.

Three more rules:

- **No coercion.** `integer` is an integer, never `true` and never `5.0`. `number` is never a
  boolean. `enum`, `const` and `uniqueItems` compare by JSON type and value: `true` never equals
  `1`, and `1.0` never equals `1`.
- **Bytes** are accepted only where the schema says
  `{"type": "string", "contentEncoding": "base64"}`.
- **A budget of 100,000 steps per frame.** Past it, the call is `invalid_arguments`, "the
  arguments are too complex to check". A value costs one step for each schema node it is checked
  against. Ordinary arguments cost one to two and a half steps per JSON value, whatever their
  depth. A chain of `$ref`, `anyOf` and `oneOf` on one value is at most 8 schema nodes. A call
  with more than about 50,000 values is bulk data, which belongs in a granted folder or a
  writable mount.

## Results

Results cross as JSON: a dict with `str` keys, a list or tuple, `str`, `bool`, `int`, a finite
`float`, `None`, bytes as `$bytes`, and numpy's scalars as `int` or `float`. numpy's `bool_` is
not JSON: return `bool(...)`.

Anything else reaches the guest only as `"<name> failed (internal error)"` or
`"<name> was refused"`: a result that is not JSON, an exception that is not a `ToolError`, or a
gate that raises anything but `ToolDenied` or `ToolError`. The host's record keeps the
exception's type and first line. So a path inside an exception never reaches the guest.

## Names

A tool's name is a letter, then up to 63 letters, digits or underscores, and not a Python
keyword.

The guest calls a tool with its properties as keyword arguments. So `tool()` refuses a property
that is not a Python identifier, or that is a keyword (`from`, `class`, `max-results`). Rename
the property, and map it back in the function:

```python
from wasi_python.tools import tool

schema = {"type": "object", "properties": {"sender": {"type": "string"}},
          "required": ["sender"]}

@tool(name="search_mail", input_schema=schema)
def search_mail(**args):
    return mail.search(**{"from": args["sender"]})
```

`stubs(tools)` renders each tool as the `def` line and docstring the guest's function carries,
under `from host import tools`, for a prompt.

## Serving the door from another host

A host that is not the Python runner binds the door itself. The import is
`host::call(ptr, len, out_ptr_ptr, out_len_ptr) -> i32`:

- answer −1 when there is no host function;
- otherwise read the request from guest memory, get space for the response from the guest's
  exported `host_alloc`, write the response there, store its pointer and length at the two
  out-addresses, and answer 0;
- answer −2 if the host fails.

Frames are opaque bytes to the door. To serve tools, read and write them by the rules on this
page. See [Embed from other languages](../how-to/embed-from-other-languages.md).

## In one line

One compact JSON object per door call each way, `v` 1, two operations (`list` and `call`), nine
kinds of failure, strict request rules and a small JSON Schema subset, all fixed by `PROTOCOL`.
