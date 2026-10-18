# 031 — A tool protocol over the door

- **Status:** drafted 2026-10-17; revised the same day against its pre-build review
  (`../reviews/031-a-tool-protocol-over-the-door-spec-2026-10-17.md`), whose split it adopts:
  this specification is the protocol, its host module and the guest package in the zip; **spec
  036** puts it in the runner (`run(tools=…)`, the door's cap before the copy, the bounds,
  `Completed.tools`). It changes the artifact set, so the revision was re-reviewed before build
  (constitution §5.6): **confirmed for build with conditions, written in** (the review's
  "Confirmation": C1 in Decisions 3 and 5 and criterion 4; C3 in Decision 4 and criterion
  5; C4 in criterion 8; C5 in Decision 5 and criterion 5). **Built 2026-10-18** on
  `spec/031-a-tool-protocol-over-the-door`; its build review
  (`../reviews/031-a-tool-protocol-over-the-door-2026-10-18.md`) said not yet (F1 and F2);
  **revised against it the same day** (Decisions 3, 4, 8 and 9 and criterion 14 amended; see
  Landing notes), awaiting the reviewer's confirmation.
- **Owner:** Clay Gendron
- **Kind:** build-class (constitution §5.7: it adds files under `recipes/` and changes
  `scripts/steps/70_zip.sh`). A new host module (`src/wasi_python/tools.py`), the guest package
  (`recipes/guest/host/`), `pyproject.toml`'s ruff paths, judge additions in `tests/`,
  `README.md` (the frame format), `CHANGELOG.md`. It does not change `runner.py`.
- **Depends on:** 001 and 003 (the door, `host=`, step 70), 012 (the zip's bytes from any host),
  018 (no litter in the zip). Spec 036 depends on this one.
- **Lane order:** it shares step 70 with 033 (the zip carries what packages need) and 035 (the
  zip's directory is read once), and the build recipe with 023 (matplotlib); none of them is in
  flight with it (§5.7). It does not wait on 035: its two members cost about 0.06% of a plain
  start (Decision 9), and decision 44 orders 035 before tier A, which this is not. If 035 lands
  first, the cost is smaller and the growth reason says so.
- **Research it stands on:**
  - `../research/2026-10-17-a-tool-protocol-over-the-door.md` (the design study; its prototype
    ran every scenario through today's door: EXECUTED, `prototype_run.txt`);
  - the pre-build review's probes (EXECUTED, `door_copy_probe`, `json_edges`,
    `schema_keywords`, `enum_equality`, `worker_affinity`, `pool_model`; paths in the review);
  - `../research/2026-10-17-what-else-the-default-profile-carries.md`, finding 5 (about 77,912
    instructions per zip member on a plain start; EXECUTED there);
  - the owner's decisions (`../decisions.md`): **12 and 14** (a gated tool protocol of our own,
    familiar from LangChain and Monty), **15** (async host functions, later), **17**
    (governance left to embedders), **37** (an optional `gate=`; tools are capabilities; the
    runner validates, routes, counts and records), **38 to 40** (`from host import tools`;
    validated first; `subprocess.run`'s error rule; `ToolError` in the guest; no adapters);
  - constitution §4.4 as amended 2026-10-17, §4.5, §4.15.

## Terms

- **The door:** the one custom import, `host::call`, reached in the guest through the builtin
  module `_host` (`recipes/hostmodule.c`). The runner binds it to `host=`, a function from request
  bytes to response bytes.
- **A frame:** the bytes of one door call, one way.
- **A tool:** a host function the embedder offers the guest, with a name, a description and an
  input schema (JSON Schema, the standard way to describe the shape of JSON).
- **A descriptor:** the data that describes a tool, in MCP's field names: `name`, `description`,
  `inputSchema`, and optionally `outputSchema` and `annotations`.
- **The gate:** an optional embedder function that sees each validated call and may refuse it
  before the tool runs.
- **A capability:** a tool whose authority the embedder bound when it made the tool (a closure
  or a bound method). The guest can use the authority only through the tool.
- **A fault:** an exception from a tool or gate that was not meant for the guest. The guest
  learns only that the call failed; the record names the exception's type and first line.
- **The frame host:** `_ToolHost`, the object that answers protocol frames for one call.

## The problem

The owner wants guest code to call the host's tools, APIs and MCP servers "through a gated
protocol that we design", with "a clean and familiar api" (decisions 12 and 14). Today the door
carries opaque bytes. Every embedder that wants tools must invent framing, schemas, validation,
error mapping, limits and a guest module, and get each right against a hostile guest. The design
study shows the protocol fits on today's door with no new import. The familiar shape is a
decorator on the host and ordinary functions in the guest. The review showed that the rules for
JSON, schemas and records must be the protocol's own, not whatever CPython does.

## Decisions

1. **One protocol, two halves, over the unchanged door; the runner part is 036.**
   - The host half is `wasi_python.tools`. The guest half is a pure-Python package, `host`, in
     the stdlib zip. Between them run JSON frames, protocol 1 (Decision 7), through
     `_host.call`. The binary, its imports and its exports do not change (§4.4).
   - This specification builds the frame host and its rules. Spec 036 binds it to the door
     (`run(tools=…)`), refuses frames by length before any copy, runs tools on their own threads
     under the call's bounds, and returns the record. Until 036 lands, the frame host is private
     and reached only by the checks, as a raw `host=` callable.
   - `import wasi_python` does not import `wasi_python.tools` (spec 015's F6).

2. **The host API: a decorator, as LangChain's `@tool`.**
   - `tool(fn=None, *, name=None, description=None, input_schema=None, validates_input=False,
     timeout_s=None, read_only=False, destructive=False, idempotent=False, open_world=False) ->
     Tool`, bare (`@tool`) or with arguments.
   - **The name** is `name` or `fn.__name__`; an object with no `__name__` (a
     `functools.partial`) needs `name=`. It must match `[A-Za-z][A-Za-z0-9_]{0,63}` and not be a
     Python keyword.
   - **The description** is `description`, or the docstring up to its first section heading
     (`Args:`, `Arguments:`, `Returns:`, `Raises:`), stripped.
   - **The derived schema.** The root is `{"type": "object", "properties": …, "required": […],
     "additionalProperties": false}`. A Google-style `Args:` section gives each property its
     `description`. A parameter with a default is not required, and its default is the property's
     `default` (description only; Decision 8 says the guest never sends it).
   - **Hints mapped:** `str`, `int`, `float`, `bool`, `None`, `bytes`, `list[T]`, `tuple[T,
     ...]` (an array), `dict[str, T]` (`additionalProperties: <T>`), `Literal[…]` of JSON
     scalars, unions (`A | B`, `Optional[A]`) and `Any` (`{}`). `bytes` maps to `{"type":
     "string", "contentEncoding": "base64"}`.
   - **Refused** with `TypeError` or `ValueError` naming the parameter: no hint; a hint outside
     the list; `*args`, `**kwargs`, a positional-only parameter; a default with no JSON form; a
     default of `None` on a hint that does not admit `None` (write `int | None = None`); a bad
     name; an `async def` (Decision 11); a `timeout_s` that is not a finite number above 0 (as
     `_deadline_limit` rules) or `None`.
   - **`input_schema=`** replaces the derived schema: a dict whose root is `type: "object"`, or
     any object with `model_json_schema()` (a pydantic model class; pydantic is never imported).
     The function is then called with the validated arguments as keywords. It is vetted as
     Decision 3 says.
   - **For every input schema,** derived or given, `tool()` refuses a root property name that is
     not a Python identifier or is a keyword (`from`, `class`, `max-results`), naming it: the
     guest builds a signature from these names. A README recipe renames such properties. A
     `required` name missing from `properties` is refused too.
   - **The output schema** comes from the return hint when it maps, else it is absent. It is
     shown, never validated.
   - **The hints** `read_only`, `destructive`, `idempotent`, `open_world` are the embedder's
     labels, emitted as MCP's `readOnlyHint` and so on when true. They grant nothing.
   - **`Tool` is immutable.** `tool()` vets a deep copy of the schema and keeps it private;
     `Tool.input_schema` and `Tool.descriptor()` return fresh copies, so a schema cannot be
     changed after it was vetted. `Tool` compares and hashes by identity (`eq=False`). It is
     callable on the host (`lookup_region(code="EMEA")` calls the function).
   - **Tools are capabilities.** `tool()` works on closures and bound methods. The runner adds no
     identity, user or policy to a call (decision 17, §4.5).

3. **The schema subset: what `tool()` accepts and what the validator checks.**
   - **Checked:** `type` (one or a list); `enum`, `const`; `properties`, `required`,
     `additionalProperties` (a boolean or a schema; absent, it closes an object schema that lists
     `properties`, stricter than JSON Schema's default, and leaves one without `properties`
     open); `minProperties`, `maxProperties`; `items` (one schema), `prefixItems` (with `items`
     for the rest), `minItems`, `maxItems`, `uniqueItems`; `anyOf`, `oneOf`; local `$ref` into
     `$defs` or `definitions`; `minimum`, `maximum`, `exclusiveMinimum`, `exclusiveMaximum`,
     `multipleOf` (a positive integer only; an `int` passes when it divides exactly, a `float`
     when `value % m == 0`); `minLength`, `maxLength` (in code points);
     `contentEncoding: "base64"` on a string.
   - **Ignored** (annotations): `title`, `description`, `default`, `examples`, `format`,
     `deprecated`, `readOnly`, `writeOnly`, `contentMediaType`, `discriminator` (OpenAPI's;
     `oneOf` is still checked), `$schema`, `$id`, `$comment`.
   - **Refused by `tool()`** unless `validates_input=True`: every other keyword. `pattern` is
     among them on purpose: an embedder's regular expression run on up to 1 MiB of guest text is
     a ReDoS risk (catastrophic backtracking) on the door's thread. The array form of `items`
     (draft 4's tuples), a `$ref` that is not local, and a `$ref` cycle that does not pass
     through a keyword that descends into the value (`properties`, `additionalProperties`,
     `items`, `prefixItems`) are refused even then.
   - With `validates_input=True` the validator checks the keywords it knows and skips the rest
     (owner question 50).
   - **Types, no coercion.** The validator sees the parsed JSON types: `bool`, `int`, `float`,
     `str`, `None`, `list`, `dict`. `integer` is an `int`, never a `bool` and never a `float`:
     `5.0` is refused, unlike JSON Schema, so an `int`-hinted tool never gets a float. `number` is
     an `int` or a `float`, never a `bool`.
   - **Equality** (`enum`, `const`, `uniqueItems`) is type-strict and recursive: two values are
     equal only when their parsed types and values are equal, so `true` never equals `1`, `1.0`
     never equals `1`, and `[true]` never equals `[1]`.
   - **`uniqueItems` in one pass.** Each item is turned into a canonical key, tagged by type at
     every level and hashable (a dict's key sorts its pairs), and the keys go in a set. The keys
     are equal exactly when the strict equality above says so. So an array costs one pass, never
     the pairwise comparisons of a naive check (137,438,691,328 for the 524,288 items a 1 MiB
     frame can carry; the review's C1).
   - **A validation budget per frame (the review's C1).** Validation runs on the door's thread,
     where neither the deadline, `cancel` nor Ctrl-C can stop host code. A recursive schema
     whose `anyOf` branches overlap (pydantic emits one for `Union[list[Node], list[Union[int,
     Node]]]`; EXECUTED, `recursive_union.txt`) makes a validator that tries every branch double
     its work at each level: 10,485,754 schema visits at depth 20, about 2^62 at the frame's
     62 levels (`validator_cost.txt`). So the validator counts every schema node it visits, and
     every item key it makes, against a fixed budget of **100,000 per frame**
     (`TOOL_VALIDATION_STEPS`). Past it, the call is answered `invalid_arguments`: "the
     arguments are too complex to check". The budget is a count, not a time, so the outcome is
     the same on every host. Why 100,000: an ordinary call's arguments need about one visit per
     JSON value, and a call with more than 100,000 values is either bulk data, which belongs in
     a granted folder as the request cap already says (a 1 MiB frame can hold about 524,288
     one-digit items, and is then refused here), or a branch explosion. The README says so.
   - **What a step is** (amended 2026-10-18 by the build review's F1 and F2). A value costs one
     step for each schema node it is checked against: its own, each `$ref`, `anyOf` or `oneOf`
     around it, and each `anyOf` branch tried. A node that only delegates (`$ref`, `anyOf`,
     `oneOf`, with no keyword that describes children) leaves the value's children to the schema
     it delegates to, so the cost per value does not grow with depth: pydantic's shapes cost
     about 1.4 to 2.3 steps per value. A key (`enum`, `const`, `uniqueItems`) costs one step for
     each value below the one it is made for, and a `uniqueItems` key one more for its item; each
     `enum` and `const` is a set of keys made once by `tool()`, so membership is one lookup. A
     message names a value by its kind and size, or by 64 characters of a string, never by
     formatting it whole.
   - **Bytes.** After parsing, an object with exactly the one key `"$bytes"` whose value is a
     string is decoded as strict base64 into `bytes`; any other `$bytes` object is a `protocol`
     answer. A value is accepted as bytes only where its schema says `{"type": "string",
     "contentEncoding": "base64"}`.

4. **The frame rules are the protocol's own, not the host Python's.** In this order, before any
   schema is consulted:
   1. the frame is at most `TOOL_REQUEST_BYTES` (1 MiB) long;
   2. it decodes as strict UTF-8 (`json.loads` never sees bytes, so no UTF-16 or UTF-32);
   3. a scan of the text counts nesting outside strings: **the frame's nesting, its envelope
      included, is at most 64** (so 62 levels inside the `args` value); 65 is refused. So no
      parser, validator or decoder recursion depends on the CPython version (with the bound on
      same-value chains, at most 8 schema nodes, that `tool()` checks: the build review's F5);
   4. `json.loads` with: `parse_constant` refusing `NaN` and `Infinity`; `parse_float` refusing a
      non-finite result (`1e400`); `parse_int` refusing a literal longer than 64 characters,
      whatever the process's integer-digit limit; `object_pairs_hook` refusing a duplicate key;
   5. no string, in a key or a value, holds a lone surrogate (`"\ud800"`); a valid surrogate
      pair is accepted;
   6. the top level is an object.

   Any failure is a `protocol` answer. Answers are encoded with `ensure_ascii=True`,
   `allow_nan=False` and compact separators, so encoding an answer never raises.

5. **The frame host answers a frame in a fixed order.** `_ToolHost(tools, *, gate=None,
   max_calls=1000, invoke=<inline>)` keeps one call's counters and record. It has two entry
   points:
   - **`admit(length) -> bytes | None`**, called with the frame's length before its bytes are
     read: it counts the frame and answers `budget_exceeded` past `max_calls`, or `too_large`
     over `TOOL_REQUEST_BYTES`; otherwise `None`. Spec 036's door calls it before any copy, so a
     refused frame costs the host constant work.
   - **The handshake (the review's C5).** When `admit` returns `None`, the frame host keeps the
     admitted length as pending. `__call__` consumes it and checks that it equals `len(frame)`;
     with none pending (a raw `host=`, as in this specification's checks), it calls `admit`
     itself. A pending length that differs from the frame's is a runner bug, answered
     `protocol` and recorded. So every frame is counted exactly once, on the door's path and on
     the raw one.
   - **`__call__(frame) -> bytes`** then answers at the first failure of: Decision 4's rules (`protocol`); the version
     (`protocol`, naming the versions served); the operation (`protocol`); the tool's name
     against the offered set (`unknown_tool`); the arguments against its schema,
     within the validation budget (`invalid_arguments`, Decision 3); then hands the work to
     `invoke`.
   - **Every frame counts** toward `max_calls`, the guest's discovery frame included: a frame is
     a host round trip, as Monty's `max_suspensions` counts them (owner question 51). Past the
     limit the guest gets `ToolBudgetExceeded` and runs on (question 52); since 036 answers it
     from the length alone, a guest looping on it spends only its own fuel and time.
   - **The work** is one callable that runs the gate, then the tool, then encodes the result
     (Decision 6's rules), so a result slow to encode counts against the call's time in 036.
     `invoke(work)` returns the answer, or one of `timeout` and `cancelled` with whether the work
     was left running. The default `invoke` runs the work inline; 036 supplies the bounded one.
   - **The gate** gets a `ToolCall`: `seq: int` (the frame's number in this call, from 1),
     `tool: Tool`, `arguments` (a deep copy of the validated, decoded values) and
     `request_bytes: int` (the frame's length). The tool gets its own copy, so a gate cannot
     change what the tool receives. The gate allows by returning `None` or `True`; it refuses by
     raising `ToolDenied(message)` or `ToolError(message)`, whose message crosses; a return of
     `False` refuses with "<name> was refused". Any other return or exception refuses with that
     message and is a fault: a broken gate fails closed. With no gate, every validated call runs:
     the embedder's gating is then its choice of capabilities (decision 37; how this reads §4.4's
     "gated by the embedder on every call").
   - No gate or tool runs for a frame refused before `invoke`.

6. **Errors follow `subprocess.run` (decision 39), and only chosen text crosses.**
   - Nothing a frame, a gate or a tool does raises out of the frame host. A tool's or gate's
     `BaseException` is a fault too.
   - `ToolError(Exception)` and `ToolDenied(ToolError)` on the host. A tool raising `ToolDenied`
     is a capability refusing (`denied`); raising `ToolError`, it failed with a message
     (`tool_error`). Any other exception crosses as "<name> failed (internal error)".
   - **Bounded text.** Every message is at most 4,096 characters; each guest value it echoes (a
     tool name, a key, a wrong value) is cut to 64 characters first.
   - **The result's JSON form** mirrors the guest's encoding (Decision 8): `dict` with `str` keys
     only (not stringified), `list` and `tuple` as arrays, `str`, `bool`, `int`, finite `float`,
     `None`, `bytes`-like as `$bytes`, any `numbers.Integral` as `int` and `numbers.Real` as
     `float` (numpy's scalars), and no dict whose only key is `"$bytes"`. Anything else is a
     fault. An answer over `TOOL_RESPONSE_BYTES` (16 MiB, the default output cap per stream) is
     `too_large`, naming the cap.

7. **The frame format: protocol 1.** One compact JSON object per door call, each way.
   ```text
   request  {"v": 1, "id": 7, "op": "list"}
            {"v": 1, "id": 8, "op": "call", "tool": "lookup_region", "args": {"code": "EMEA"}}
   answer   {"v": 1, "id": 7, "ok": true, "tools": [descriptor, ...]}
            {"v": 1, "id": 8, "ok": true, "value": <JSON>}
            {"v": 1, "id": 8, "ok": false, "error": {"kind": "denied", "message": "..."}}
   descriptor {"name", "description", "inputSchema", "outputSchema"?, "annotations"?}
   bytes    {"$bytes": "<base64>"}
   kinds    protocol, unknown_tool, invalid_arguments, denied, tool_error, timeout,
            cancelled, too_large, budget_exceeded
   ```
   - **The list** is in the order the embedder gave the tools, so the guest's module, stubs and
     fuel are the same from run to run.
   - **The id** is echoed when it is an `int` (not a `bool`) from 0 to 2**53 - 1, else `null`.
     The host never trusts it.
   - **The version.** `v` is in every frame; an unknown one is a `protocol` answer naming the
     versions served. A field a peer may ignore may be added within a version; a field a peer
     must act on bumps `v` (Monty's rule). An operation may be added within a version, since an
     unknown one is a clean `protocol` answer. `batch` is reserved (Decision 11).
   - **Why JSON, not MCP's JSON-RPC** (the memo): the guest has `json` with its C accelerator,
     every tool schema is JSON already, and MCP's sessions and content blocks do not fit a
     one-call door. The descriptor uses MCP's names, so a tool maps one to one.

8. **The guest side: `from host import tools` (decision 38).**
   - **`host`** (`host/__init__.py`) holds `PROTOCOL = 1` and the exceptions. Importing it sends
     no frame.

     | class | bases | kinds |
     |---|---|---|
     | `ToolError` | `Exception` | `tool_error`; the base of all below; `.kind` names the kind |
     | `ToolDenied` | `ToolError`, `PermissionError` | `denied` |
     | `ToolArgumentError` | `ToolError`, `TypeError` | `invalid_arguments`, `unknown_tool` |
     | `ToolTimeout` | `ToolError`, `TimeoutError` | `timeout` |
     | `ToolCancelled` | `ToolError` | `cancelled` |
     | `ToolTooLarge` | `ToolError` | `too_large` (request or result) |
     | `ToolBudgetExceeded` | `ToolError` | `budget_exceeded` |
     | `ToolProtocolError` | `ToolError` | `protocol`, a door fault, an answer that does not match |

     `ToolCancelled` rarely reaches guest code: after a cancel the runner stops the guest at its
     next function entry (specs 015, 030). The README says not to rely on `except
     ToolCancelled` for clean-up.
   - **`host.tools`** sends one `list` frame when imported, then holds one synchronous function
     per tool and nothing else public; it imports its own modules under private names (`import
     json as _json`), so a tool named `json` fits. Each function has a `__signature__` built from
     the input schema (required parameters first), a docstring of the description and an `Args:`
     section, and a `descriptor` attribute (a copy). A descriptor whose property names cannot
     make a signature (from a host that is not this runner) gets `(**kwargs)` instead of breaking
     the import. `help(tools)`, `inspect.signature` and `from host.tools import *` work.
   - **A call** binds its arguments to the signature without applying defaults, and sends only
     the arguments its caller gave, by keyword; the tool's own default applies to the rest. A
     binding error is `ToolArgumentError`, with no frame sent. Values are encoded by Decision
     6's rules; anything else is `ToolArgumentError` naming the type and, for an array or a
     frame, suggesting `.tolist()` or `.to_dict("records")`. A failed answer raises the class for
     its kind; an unknown kind raises `ToolError`. (Amended 2026-10-18 by the build review.) The
     guest refuses any dict holding a `"$bytes"` key, not only one whose only key it is (the
     host would answer a two-key one `protocol`), and, as `ToolArgumentError` with no frame
     sent, whatever Decision 4's rules would refuse: arguments nested past 62 levels (bytes
     count a level, as their `$bytes` object) and an integer over 64 characters.
   - **An unknown attribute** raises `AttributeError` listing the offered names.
   - **Without the protocol.** Under no host, `from host import tools` raises `ImportError`:
     "this run has no tools: the embedder passed none". Under a raw `host=`, the discovery frame
     reaches that host like any frame, and an answer that is not protocol 1 raises `ImportError`
     naming why. Any failed answer to discovery (`budget_exceeded` under `max_calls=0`) raises
     `ImportError` naming its kind.
   - **Where it lives.** `recipes/guest/host/__init__.py` and `recipes/guest/host/tools.py`, a
     build input hashed in `MANIFEST`'s recipe lines. It stays compatible with Python 3.11, since
     the unit checks load it on the host's Python. `pyproject.toml` lints and formats
     `recipes/guest/` explicitly (today `recipes` is excluded). The alternative, a module the
     runner writes into an importable grant per call, waits on decision 16 and would make every
     embedder generate code.

9. **The zip, the snapshot and their cost.**
   - Step 70 gains two `--file` lines (`=host/__init__.py`, `=host/tools.py`), compiled like the
     rest. `MANIFEST` gains two recipe lines; the zip, `SHA256SUMS` and the snapshot change (the
     snapshot runs only beside its exact zip, `80_snapshot.sh`).
   - The snapshot does not pre-import `host` or `host.tools`: `host.tools` would call the door,
     whose snapshot stub traps, and `host` alone saves too little.
   - **Cost:** about 77,912 fuel per zip member on a plain-binary start (the default-profile memo,
     finding 5), so about +156,000 per plain start, about +0.06% on `pass`. A snapshot start does
     not pay it. The judge accepts it with `--accept-growth` and that reason.
   - **Cost, as measured (amended 2026-10-18 by the build review, question 1).** A plain start
     pays about +0.16 M, as predicted. A snapshot's start and program pay nothing more (an
     `os._exit(0)` run differs by about −1,000 fuel), but its teardown, `Py_FinalizeEx` after the
     program, pays about +0.11 M: every new member shifts the frozen heap that teardown frees
     (INFERRED by the review; spec 033's 7 members cost +0.07 M the same way). The growth reason
     says so. Spec 035 may change it; this does not wait for it.
   - **Building it.** The builder develops end to end against today's artifacts first, with the
     guest package on a read-only `Grant` and `PYTHONPATH` set to it, and adds the two zip lines
     last, so the lane holds the build only for the final rebuild.

10. **Stubs for a prompt.** `stubs(tools) -> str` renders each tool as a `def` line with the
    signature the guest's function carries, and its docstring, under a first line `from host
    import tools`.

11. **Async tools are a later specification (decision 15).** `tool()` refuses an `async def`
    with `TypeError`: "async tools come with a later specification (decision 15)". That
    specification adds async tools and gates, and the guest's `batch` operation. Refusing now
    and accepting later breaks no caller.

12. **Docs.** The README gains "The tool protocol": protocol 1's frames, kinds, JSON rules and
    schema subset, for an embedder in another language that serves it through its own door
    function. The Python API's section ("Tools") comes with 036, when `run(tools=…)` exists. The
    CHANGELOG notes the guest package in the zip.

## Intent

The protocol, its rules and both of its halves exist, are checked, and ship in the artifact set,
so spec 036 only has to bind them to the runner.

## Design

```
src/wasi_python/tools.py              tool(), Tool, ToolCall, ToolError, ToolDenied, stubs();
                                      the hint mapper; the schema vetting and validator; the
                                      frame rules; _ToolHost (admit, __call__, the record)
recipes/guest/host/__init__.py        PROTOCOL, the exceptions
recipes/guest/host/tools.py           discovery, one function per tool, encoding
scripts/steps/70_zip.sh               two --file lines
pyproject.toml                        ruff covers recipes/guest/
tests/unit/test_tools.py              the host half, with no guest
tests/unit/test_guest_tools.py        the guest package on the host's Python, a fake _host
tests/checks/test_v1_4_embedding.py   the guest package against the built artifact set
README.md, CHANGELOG.md
```

The record's types (`ToolRecord`, `ToolOutcome`) are defined here, because the frame host keeps
them; 036 decides how the runner returns them.

- **`ToolRecord`** (frozen): `frames: int` (every frame counted, listed or not), `outcomes:
  tuple[ToolOutcome, ...]` (the first 1,000 frames, whatever `max_calls` is, as spec 032 keeps
  its first 1,000 faults), `unlisted: int` (`frames - len(outcomes)`).
- **`ToolOutcome`** (frozen): `seq`; `op` (`"list"`, `"call"`, or `None` when unread); `tool` (the
  tool's name, or the guest's cut to 64 characters, or `None`); `outcome` (`"ok"` or a kind);
  `message` (what the guest was told on a failure, else `None`); `request_bytes`;
  `response_bytes`; `fault` (the exception's type name and first line, at most 200 characters,
  as 032's `FileFault`, else `None`; no exception object is kept, so a result holds no frame of
  the call); `abandoned` (`True` when the tool was still running when the guest was answered, so
  its effect may still land).
- No time anywhere (§4.9). A refused call is listed on an exit of 0 too.

## Scope

In: the above. Out:
- the runner's arguments, the door's cap before the copy, tools on their own threads, deadlines,
  cancel and Ctrl-C across tool calls, `Completed`'s record, the README's Python API and the
  LangChain and MCP recipes (spec 036);
- async tools, async gates and `batch` (decision 15's later specification);
- adapters in the wheel (decision 40);
- streaming, progress, chunked results; pausing for approval; gates that rewrite arguments;
  tool sets that change during a call; host objects; bare global names; static checking of
  guest code; MCP resources, prompts and sampling; tools on the command line.

## Acceptance criteria

Each new check is seen failing first: against today's code where the name is missing, and
against the stand-in named where the property is the point. Nothing measures time.

**Unit, the host half** (`tests/unit/test_tools.py`):
1. `test_a_tool_is_described_by_its_hints_and_docstring`: a sample tool's `descriptor()` equals
   an expected dict (properties, `required`, `additionalProperties: false`, `Args:`
   descriptions, a default, a `Literal`, an optional, `bytes`, a `tuple`, a `dict[str, int]`, a
   hint). The tools' order in a `list` answer is the order given.
2. `test_a_tool_that_cannot_be_described_is_refused`: each refusal of Decision 2 (a `from`
   property, a `required` name not in `properties`, `x: int = None`, a NaN `timeout_s`, a
   `partial` without `name=`, an `async def` naming decision 15) and of Decision 3 (`pattern`,
   array `items`, a remote `$ref`, a `$ref` cycle that does not descend) raises, naming the
   parameter or keyword; `pattern` passes with `validates_input=True`, the cycle does not.
3. `test_a_vetted_schema_cannot_change`: changing the dict passed as `input_schema=`, or the one
   `Tool.input_schema` returned, changes neither what is validated nor the descriptor; a `Tool`
   goes in a set. Stand-in: a `Tool` holding the caller's dict.
4. `test_the_validator_does_not_coerce`: a table covering every checked keyword, with `"7"`,
   `true` and `5.0` for an integer, `true` against `enum: [1]`, `1.0` against `const: 1`,
   `[true]` against `[1]`, `uniqueItems` on `[1, true]` (passes) and `[1, 1]` (fails), an unknown
   key, a missing key, `additionalProperties` as a schema, `prefixItems`, `multipleOf`, `$ref`,
   and `$bytes` against a string schema. Stand-in: equality by `==`. And the budget (C1), with
   a validator that counts its steps, never a timing:
   - pydantic's recursive union (`Union[list[Node], list[Union[int, Node]]]`, its schema
     written into the check, so pydantic is not a dependency) against a value 62 levels deep
     that fails only at its deepest leaf is answered `invalid_arguments` ("too complex") after
     at most 100,000 counted steps;
   - under `uniqueItems`, 50,000 distinct items followed by a repeat of the first are refused
     after one pass (50,001 keys made, no pairwise comparison), and 100,001 distinct integers
     (about 600 KB) are answered "too complex" with at most 100,000 counted steps;
   - seen failing first against a naive validator (every branch tried, pairwise
     `uniqueItems`) given the same counter, which passes the budget on both.
5. `test_frames_follow_the_protocols_rules`: the frame host answers each with its kind, and a
   counting gate and tool stay at 0: over the cap (through `admit` alone, with no bytes), past
   `max_calls`, not UTF-8, UTF-16, a frame nested 65 levels in total (and one nested 64,
   which passes), `NaN`, `1e400`, a 65-character
   integer (also with `sys.set_int_max_str_digits(0)` in force), a duplicate key, a lone
   surrogate in a value and in an unknown key's name (the answer echoes it and encodes), a malformed `$bytes`, `v: 0`, an unknown `op`, an
   unknown tool, wrong arguments. Every answer encodes, and none raises. Frames are counted
   exactly once on both paths: `admit` then `__call__` (the door's), and `__call__` alone (a
   raw `host=`). Stand-in: a host that relies on `json.loads`'s defaults.
6. `test_the_gate_decides_after_validation`: allow by `None` and `True`; refuse by `False`, by
   `ToolDenied` (its message crosses), by a stray exception and a stray return (generic message,
   faults); a gate that mutates its `arguments` leaves the tool's unchanged; the tool's counter
   counts only allowed calls. Stand-in: a host that runs the gate before validating.
7. `test_only_chosen_text_crosses_and_is_bounded`: a `ToolError` message crosses, cut at 4,096;
   a `KeyError` naming a host path does not, its answer says "(internal error)" and the record's
   `fault` is `"KeyError: …"`; a result with a non-`str` key, a set, or `inf` is the same;
   numpy-like `numbers.Integral` results encode as `int`; a 17 MiB result is `too_large`.
   Stand-in: a host that sends `str(exception)`.
8. `test_the_record_is_bounded`: with `max_calls=None`, 1,500 frames each naming a
   10,000-character unknown key, and one naming a 1,000,000-character key (it fits the 1 MiB
   cap, so it reaches `invalid_arguments`), give `frames == 1501`, 1,000 outcomes,
   `unlisted == 501`, and no message over 4,096 characters; each echoed key is cut to 64.

**Unit, the guest half** (`tests/unit/test_guest_tools.py`, the recipe files loaded on the host's
Python with a fake `_host` that routes to a `_ToolHost`):
9. `test_the_guest_package_speaks_the_hosts_protocol`: `PROTOCOL` equals the host's; every kind
   maps to its class; signatures, docstrings, `descriptor` and `__all__` match; a tool named
   `json` works; positional arguments go by keyword; an omitted optional argument is absent from
   the frame; numpy-like scalars encode; bytes round-trip; a dict whose only key is `"$bytes"`
   is refused; a descriptor with a `from` property gets `(**kwargs)`; `ImportError` for no host,
   for a non-protocol answer and for `budget_exceeded` on discovery; `AttributeError` lists the
   offered names.
10. `test_stubs_match_the_guest_signatures`: each `def` line of `stubs()` equals `def
    <name><inspect.signature(fn)>:` for the guest's function, over tools covering every mapped
    hint.

**Against the built artifact set** (`tests/checks/test_v1_4_embedding.py`, the frame host passed
as a raw `host=`, its record read from the object):
11. `test_the_guest_package_round_trips_through_the_door`: `from host import tools`, two calls,
    one result fed to `pandas.DataFrame`, bytes both ways; stdout as expected; the record lists
    `list ok`, `call ok`, `call ok`; exit 0. Both binaries.
12. `test_a_forged_frame_is_validated_first`: the guest sends frames through `_host.call` with a
    wrong-typed argument and with an unknown key; the tool's counter is 0; both outcomes are
    `invalid_arguments`.
13. `test_the_zip_carries_the_host_package`: the zip holds `host/__init__.pyc` and
    `host/tools.pyc`; the existing check that `MANIFEST`'s recipe lines cover every tracked
    recipe passes with them.

**The whole:**
14. `uv run pytest` green with `--accept-judge`; lost 0; the growth in bytes, in plain-start
    fuel and in the snapshot's teardown (Decision 9, as amended) accepted with `--accept-growth`
    and that reason, and nothing else grows beyond heap-layout noise in the heavy jobs.
15. A release dry run passes every job (the artifact set changed).

## The owner's choices

None open here. Three of its choices, in Decisions 3 and 5, are the agent's where the owner's
decisions were silent: questions 50 to 52 in `../questions-for-the-owner.md`. Question 53 is
spec 036's. Nothing waits on them.

## Landing notes

Built 2026-10-18 by a builder agent (Claude Opus 5.5) in the worktree
`wasi_python-031`, on darwin-arm64, wasmtime 49.0.0. Every number below was EXECUTED there
unless it is labelled otherwise. The worktree's logs and scratch scripts go when it does, so the
numbers are written here. Not yet reviewed: the build review (`../reviews/`) is next, and the
lane's acceptance after it.

### What changed

- `src/wasi_python/tools.py` (new): `tool()`, `Tool`, `ToolCall`, `ToolOutcome`, `ToolRecord`,
  `ToolError`, `ToolDenied`, `stubs()`; the hint mapper; schema vetting (`_vet`, `_Vetting`); the
  validator (`_Validator`, with `steps`, `keys` and `exhausted`); the frame rules (`_parse`); and
  the frame host `_ToolHost` (`admit`, `__call__`, `record`). `_Work` is the callable `invoke`
  runs; `_Interrupted(kind, abandoned)` is what a bounded invoke (spec 036) gives back when it
  did not wait. `runner.py` and `__init__.py` are unchanged.
- `recipes/guest/host/__init__.py` and `recipes/guest/host/tools.py` (new), and two `--file`
  lines in `scripts/steps/70_zip.sh`.
- `pyproject.toml`: ruff lints and formats `recipes/guest/`. `extend-exclude` now names the
  other recipe files one by one, because ruff's `recipes/*.py` glob also matched files inside
  `recipes/guest/`. `src` gains `recipes/guest`, so `host` sorts as first-party.
- The judge: `tests/unit/test_tools.py` and `tests/unit/test_guest_tools.py` (new); three checks
  appended to `tests/checks/test_v1_4_embedding.py`; and `tests/checks/test_rules.py`'s ruff
  checks now also cover `recipes/guest`. That last one is a judge change.
- `README.md`: "The tool protocol" (Decision 12), the recipe that renames a property, and the
  zip's row in "What you get". `CHANGELOG.md`: one entry.

### The artifact set (the first build; superseded by the revision below)

The worktree's first build matched main's frozen set before any change (`diff` of
`build/artifacts/SHA256SUMS` against `build/sets/s-8d84b3b190fe9bce/SHA256SUMS`: no output).
The new set, from `scripts/build.sh --from 70`, is below. A full rebuild of all 11 steps
(`scripts/build.sh`, 5m17s) gave the same `SHA256SUMS` byte for byte (`cmp` exit 0):

```
5d3de5f6a195660225d9a0413633cddd8a3679efa0f929514daa6a5499f3d8ca  MANIFEST
f901330ae27b813ac44e0cdc85dd1d727bd1b57ab348812124e1319489caa4c9  python-snapshot.wasm
d3b21ac850f19bbd1f4cbc7fc3ce29e890ef6ac2f3fae1fc2059e50350330c31  python-stdlib.zip
4befe9de64edc783996ab006e6179b704a73a520b67431135df103db9db9625d  python.wasm
```

- Every `LICENSES/` line is unchanged, and so is `python.wasm`, as Decision 9 says.
- `MANIFEST` gains two recipe lines (`afa4ae76…` `recipes/guest/host/__init__.py`, `b3959ae3…`
  `recipes/guest/host/tools.py`). It also changes `70_zip.sh`'s hash and `x-snapshot-zip`.
- The zip: 1,100 to 1,102 `.pyc` (658 data files, as before); 11,162,065 to 11,174,678 bytes
  (+12,613). The snapshot: 65,505,752 to 65,509,922 bytes (+4,170).

### The cost (Decision 9), and where it differs

Method: `-c pass` through the judge's driver (a fixed clock and fixed entropy), on main's frozen
set and on the new set. Each was run under five heap perturbations: an environment variable of
0, 17, 300, 4,000 and 12,000 bytes.

| start | mean | min | max | of a start |
|---|---|---|---|---|
| plain | +157,362 | +146,573 | +168,898 | +0.065% of 242.0 M |
| snapshot | +110,800 | +87,167 | +122,141 | +0.135% of 82.0 M |

- **Plain start: as predicted.** Decision 9 said about +156,000.
- **Snapshot start: not as predicted.** Decision 9 said a snapshot start would not pay. It pays
  about +0.11 M.
  - It is a cost per member, not a one-off shift in the heap. A variant zip with only
    `host/__init__.py` (steps 70 to 90, then put back) cost +46,456 on the snapshot (min
    +44,304, max +50,644) and +81,182 on a plain start, over the same five perturbations.
  - The cause is not found. zipimport's parsed directory is frozen in the snapshot (spec 035
    says the same). Nothing in `recipes/reactor_bootstrap.py` or `reactor_main.c` calls
    `invalidate_caches` (READ).
  - Spec 033's acceptance also recorded +0.07 M per snapshot call, for 7 members.
  - That was two experiments on one question, so I stopped there (AGENTS.md, rule 7). It is
    left to the review and to spec 035.
- **The judge's growth list** (the full run, against `context/progress/accepted.json`): 2 byte
  metrics and 41 fuel metrics rose, 38 of them past the ratchet (its "grew 40"); 6 fell.
  - The two byte metrics are the zip (+12,613) and the snapshot (+4,170).
  - Light plain checks grew +150 k to +161 k (for example `test_guest_runs_here[plain]`
    +158,167).
  - Light snapshot checks grew +47 k to +115 k (`test_guest_runs_here[snapshot]` +101,353).
  - The heavy jobs moved both ways, by up to a few parts in ten thousand:
    `test_pandas_csv_job_matches_native` +2,190,579 (of 5.69 G),
    `test_sqlite_job_matches_native` +1,460,436, `test_npy_files_round_trip[snapshot]`
    +496,054, `test_default_integer_width_is_documented` +453,812, and
    `test_numpy_csv_job_matches_native` −447,228. These are inside the range spec 033's
    acceptance took as heap-layout noise (pandas_csv +2,499,701 there).
- **A growth reason for the lane:** "spec 031: 2 more zip members (+12,613 bytes; snapshot
  +4,170 bytes; python.wasm unchanged); about +0.16 M fuel per plain start, as predicted, and
  about +0.11 M per snapshot start, which Decision 9 did not predict (a cost per member, cause
  not found, see the landing notes); heavy jobs within ±2.2 M".
- **Criterion 14's "nothing else grows" does not hold as written**, because of the snapshot
  start. The review should decide whether that blocks this landing, or waits on spec 035.

### Each criterion

Seen failing first: criteria 1 to 10 failed at import or collection before the code existed
(`ModuleNotFoundError` for `wasi_python.tools`; `FileNotFoundError` for the recipe package).
Criteria 11 and 13 failed against the old set: `No module named 'host'`, and the zip without
`host/*.pyc`. The stand-ins below were run by a scratch script that patched one property out of
the built code and then ran the checks:

| stand-in | the check it breaks | result |
|---|---|---|
| a `Tool` holding the caller's dict | 3 | 1 failed |
| equality by `==` | 4, the table | 9 failed (`enum`, `const`, `uniqueItems` rows) |
| a naive validator: every branch, pairwise `uniqueItems`, the same counter, stopped at 10× the budget | 4, the budget | 2 failed: "stand-in passed the budget: 1000001 steps" on both |
| a host on `json.loads`'s defaults | 5 | 10 failed (NaN, Infinity, 1e400, a 65-character integer, both duplicate keys, the digit limit, …) |
| the gate run before validation | 6 | 1 failed |
| `str(exception)` sent to the guest | 7 | 1 failed: the secret path crossed |
| a frame host that skips the schema | 12 | 1 failed: the forged frames reached the tool |

The rest of the evidence, criterion by criterion:

1. `test_a_tool_is_described_by_its_hints_and_docstring` passes. It compares the whole
   descriptor (an `Args:` section, a continued description, a default, a `Literal`, an
   optional, `bytes`, `tuple[int, ...]`, `dict[str, int]`, `readOnlyHint`, the output schema)
   and the order of the `list` answer for two orderings. Added:
   `test_importing_the_package_does_not_load_the_tools` (Decision 1), in a subprocess.
2. `test_a_tool_that_cannot_be_described_is_refused` is 26 cases, each naming its parameter or
   keyword, and covers every refusal the criterion lists. With
   `test_validates_input_lets_unknown_keywords_through_but_never_a_cycle`, `pattern` passes under
   `validates_input=True` and the non-descending cycle does not.
3. `test_a_vetted_schema_cannot_change` passes. A `Tool` cannot be built except by `tool()`
   (`__post_init__` checks a private token), so no unvetted schema reaches a frame host.
4. The table is 85 rows (`test_the_validator_does_not_coerce`). On the budget:
   `test_a_recursive_union_is_checked_within_the_budget` gives "too complex" with
   `steps <= 100,000`, directly and through a frame. In `test_unique_items_take_one_pass`,
   50,000 distinct items and a repeat are refused with `keys == 50,001`, and 100,001 distinct
   integers are "too complex" with `steps <= 100,000`.
5. `test_frames_follow_the_protocols_rules` covers 21 bad frames. Every answer is ASCII JSON;
   the gate and the tool stay at 0; there is one frame and one `protocol` outcome each. The
   bounds pass: 64 levels in all, a 64-character integer, a surrogate pair, brackets inside a
   string. The digit limit holds under `sys.set_int_max_str_digits(0)`. The surrogate key is
   echoed as `\ud800` and encodes. Admission by length alone is checked. Each frame is counted
   once on both paths, and a mismatched admitted length is `protocol`, recorded with a fault.
   Added after the builder's own security reading (below):
   `test_the_nesting_scan_is_one_pass`, in four cases, counts the scan's tokens (at most one per
   character) on an unterminated string of 400,000 escaped quotes, on 800,000 quotes, and on
   two more.
6. `test_the_gate_decides_after_validation` passes: allow by `None` and `True`; refuse by
   `False`, `ToolDenied`, `ToolError`, `KeyError`, `SystemExit`, `"yes"` and `1`, with a fault
   only for the stray ones. A meddling gate leaves the tool's copy alone. An invalid frame
   never reaches the gate.
7. `test_only_chosen_text_crosses_and_is_bounded` passes: the 4,096 cut; a `KeyError` that
   names a path; an `int` key, a set, `inf` and a `$bytes`-only dict all fault; a fault is cut
   at 200 characters; numpy-like scalars, tuples and bytes encode; a 17 MiB result is
   `too_large`, naming `16777216`.
8. `test_the_record_is_bounded` passes: `frames == 1501`, 1,000 outcomes, `unlisted == 501`,
   every message ≤ 4,096, every echoed key ≤ 64. The 1,000,000-character key reaches
   `invalid_arguments` (C4).
9. `test_the_guest_package_speaks_the_hosts_protocol`, plus four more guest checks: every kind
   maps to its class and bases, and an unknown kind is a plain `ToolError`; a mismatched answer
   is `ToolProtocolError`; the `(**kwargs)` fallback; the three `ImportError`s; and an empty
   tool list.
10. `test_stubs_match_the_guest_signatures` passes: the `def` lines and the docstrings (through
    `ast`) equal the guest's, over every mapped hint. On the real guest, CPython 3.15 in wasm,
    the guest's `inspect.signature` lines equal the host's `stubs()` lines (host 3.14.2):
    `True`, with the package on a read-only grant before the zip lines existed.
11. `test_the_guest_package_round_trips_through_the_door` passes on both binaries. The output
    is `EMEA 60 ['month', 'sales']` and `b'\x00cba'`; the record is `list ok`, `call ok`,
    `call ok`, 3 frames. Fuel: snapshot 95,408,513; plain 5,005,322,033 (the plain binary
    imports pandas).
12. `test_a_forged_frame_is_validated_first` passes: both forged frames are `invalid_arguments`,
    and neither the tool nor the gate is called.
13. `test_the_zip_carries_the_host_package` passes, and so does
    `test_manifest_recipes_match_the_tree`.
14. The full judge, `uv run pytest`, run 2026-10-18 on the final tree (logs in the worktree):

    ```
    wasi_python v1: 204/208 pass · 0 gap · 4 blocked · 0 fail   (unit suite 750/757, 7 skipped)
      v1.1  artifact set        24/25  blocked 1
      v1.2  portable, sealed    40/41  blocked 1
      v1.3  data stack          20/21  blocked 1
      v1.4  embedding           81/81
      v1.5  rebuild from pins   18/18
      rules constitution rules  21/22  blocked 1
    blocked by: oracle 1 · prior-art clones 1 · three systems 1 · wheel 1
    ratchet vs 92df8325a4: lost 0 · absent 0 · unrun 0 · unrun locally 2 · gained 4 · grew 40 · judge changed: pyproject.toml, tests/checks/test_rules.py, tests/checks/test_v1_4_embedding.py and 2 more
    RED: 40 metric(s) grew
    954 passed, 11 skipped in 172.89s
    ```

    The run before the nesting fix below had the same scoreboard (746/753 units). The growth
    list matched it to within 34 fuel on three checks, and exactly on the rest.

    It is red only for the growth above. The lane needs `--accept-judge` (the new and changed
    check files, and ruff's paths) and `--accept-growth`. `ruff check` and
    `ruff format --check` are clean on `src`, `tests` and `recipes/guest`.
15. **Not done here: the release dry run** (`gh workflow run release.yml --ref <branch>`). It
    needs a push, which a builder does not do. It is the lane's, on the reviewed commit, as for
    spec 033.

### The builder's choices where the specification is silent

The review should confirm or reject each of these.

- **`PYTHONPATH` is not read by the runtime.** The reactor starts from
  `PyConfig_InitIsolatedConfig` (`recipes/reactor_main.c`). So the development run of
  Decision 9 put the read-only grant on `sys.path` in the program itself.
- **Bytes are checked at every schema node.** A `bytes` value is refused at any node with no
  `type`, `anyOf`, `oneOf` or `$ref`: `{}`, `true`, an open object's values, an array with no
  `items`. That is how Decision 3's "accepted as bytes only where its schema says so" is held.
  As a result every JSON value costs at least one validation step, which matches the budget's
  stated basis of one visit per value. A tool hinted `Any` therefore cannot receive bytes.
- **The guest refuses any dict with a `"$bytes"` key.** Decision 8 says "only key". The host
  would answer a two-key `$bytes` object `protocol` anyway, so the guest names it as a
  `ToolArgumentError` first.
- **A result nested deeper than 62 levels is a fault.** This is the same bound as the
  arguments, so the guest's parser meets a bounded answer.
- **A gate that raises `ToolError` refuses with kind `denied`.** A tool that raises it fails
  with `tool_error`.
- **Signatures render the same text on every Python version.** Annotations are shown through a
  private `_Hint` whose `repr` is the text (`Literal['a', None]`, `int | None`), so the host's
  `stubs()` and the guest's `help()` agree across 3.11 to 3.15. An optional property with no
  schema `default` shows `= ...`, and it is not sent. A `bytes` default is written in the
  schema as `{"$bytes": …}` and shown as bytes.
- **Over the cap, the budget answer comes first.** `admit` answers `budget_exceeded` before
  `too_large`, so a frame that is past `max_calls` and over the cap is `budget_exceeded`.

### A finding of the builder's own, fixed before review

- **The nesting scan was quadratic on a guest's frame.** The first version stripped strings
  with `re.sub` and a linear-per-match pattern (`"[^"\\]*(?:\\.[^"\\]*)*"`). On an
  unterminated string, that pattern is retried at every quote.
- A frame of `"` followed by `\"` repeated (1 MiB fits about 524,000 pairs) then costs about
  n²/2 steps on the door's thread, where no deadline or cancel can stop it. All of that comes
  before `json.loads`, which would refuse such a frame at once.
- Benchmark fact (EXECUTED, a scratch timing, not a check), for the old regex: 0.349 s at
  10,001 characters, 1.378 s at 20,001 and 5.412 s at 40,001. It quadruples each time the frame
  doubles, so about an hour at 1 MiB (INFERRED).
- The new scan, one `finditer` over escape pairs, quotes and brackets, takes 0.051 s at 800,001
  characters (EXECUTED, the same script).
- The check counts tokens, not time. It failed first because `_TOKEN` did not exist; the old
  code had no token pass to count.

### For the reviewer (security: guest-controlled frames)

- `_parse`: the nesting scan (one `_TOKEN` pass, fixed above), then strict UTF-8, the hooks,
  and the surrogate and `$bytes` walk. Is any frame of 1 MiB or less super-linear anywhere
  before the validator? Also check `_key` for `uniqueItems`: one counted step per item, but a
  nested item's key costs its size, which is linear in the frame.
- `_Validator`: is every path counted? Look at `$ref` and its siblings, `anyOf` short-circuit,
  `oneOf` trying every branch, and `uniqueItems` keys (made before `items` is visited).
- `_Vetting.no_cycle`: does any `$ref` chain that stays on one value escape it? For example
  through `prefixItems`, which counts as descending.
- `_Work` and the gate: every `BaseException` from a gate, a tool, `str(e)` or the encoder is
  caught; nothing but a `ToolError`'s own text reaches the guest.
- `__call__`'s catch-all answers `protocol` for a bug in the frame host. Check that it cannot
  hide a refusal.
- The guest package runs with the guest's privileges only. It trusts nothing from the answer
  beyond JSON types (`v`, `id` and `ok` are type-checked; `$bytes` is decoded strictly).

### Revision after the build review (2026-10-18)

The review (`../reviews/031-a-tool-protocol-over-the-door-2026-10-18.md`) said "not yet; fix F1
and F2 together". The branch was rebased onto main at `3b9c9c1` (spec 032 accepted). The
conflict in `tests/checks/test_v1_4_embedding.py` was mechanical: both sides had appended to
the end, and both blocks were kept. `README.md` and `CHANGELOG.md` merged on their own. Spec
032 changed no build input. Every number below is EXECUTED in the worktree unless labelled.

**F1 and F2, the validator.** The validator was rewritten as one piece (`_Validator`, `_key`,
`_keysets`, `_shown`, `_where`):
- A node that only delegates (`$ref`, `anyOf`, `oneOf`, with no keyword about children) no
  longer walks the value. The schema it delegates to does, so the bytes rule still holds (F2).
- Each `enum` and `const` is a set of keys, made once by `tool()` (`Tool._keysets`), so a check
  is one key and one lookup (F1).
- `_key` charges one step for each value below the one it keys; a `uniqueItems` key costs one
  more for its item.
- `_shown` and `_echo` name a non-string value by its kind and size, and never `json.dumps` it.
- A path is kept as links and rendered only for a message, so a visit no longer copies a
  string.

The new checks, each seen failing against the reviewed code (`2788f49`'s `tools.py`, loaded in
place of the new one by a scratch plugin):

| check | against the reviewed code |
|---|---|
| `test_valid_arguments_cost_about_one_step_per_value`, 4 cases | 4 failed |
| `test_an_enum_costs_one_key_per_value` | failed (the reviewer counted 60,093,990 key builds there; now at most 99,990 + 10) |
| `test_messages_never_format_a_whole_value` | failed |
| `test_unique_item_keys_are_charged` | passed: it kills the "item key uncounted" mutant (F6) |

The check is a stated bound, not "about one". Measured:

| arguments | JSON values | steps | per value | bound in the check |
|---|---|---|---|---|
| order, 5,000 lines | 35,002 | 50,002 | 1.43 | 1.5 |
| tree 20 deep, 5,000 leaves | 15,064 | 35,085 | 2.33 | 2.5 |
| tree 60 deep, 1,000 leaves | 3,184 | 7,245 | 2.28 | 2.5 |
| pydantic's recursive union, 60 deep | 1,062 | 2,189 | 2.06 | 2.5 |

- The tree's figure is 2.3, not 1.5, because its `Optional` parent tries `$ref` before `null`:
  three steps for a `null`.
- The cost per value no longer grows with depth. The review measured 41.76 per value at 40 deep
  before.
- A 10,000-line order (70,002 values, about 100,000 steps at 1.43) is still "too complex". So
  the README and Decision 3 now say a call of more than about 50,000 values is bulk data.
- The reviewer's 600-name `Literal` frame (99,990 names) now answers `ok`, with 99,990 key
  builds.

**F3.**
- `_fault` is `_described` (032's pattern and text), made total over `BaseException`.
- Both handlers that read a `ToolError`'s text now catch `BaseException`, and `_message_of` gives
  a plain `str`.
- `test_a_base_exception_never_escapes_the_frame_host`, 8 cases (`SystemExit`, Ctrl-C, a
  `__str__` raising either, each from a tool and from a gate). Against the reviewed code, two
  cases failed, and the Ctrl-C one escaped and aborted the pytest session.

**F4.** The guest now refuses, as `ToolArgumentError` and with no frame sent, two things the host
would refuse as `protocol`:
- a container, or bytes (which cross as an object), at a depth of 62 or more inside an argument;
- an integer whose literal would be over 64 characters (`-(10**63) < n < 10**64`, checked before
  `json.dumps`).

`test_the_guest_refuses_what_the_host_would_refuse_as_protocol` and
`test_a_loose_bytes_answer_is_a_protocol_error` failed against the old guest. `"QR=="` is left
out of the loose list: strict mode accepts it on both halves alike.

**F5.**
- `_Vetting.no_cycle` now also computes each node's longest same-value walk, and `tool()`
  refuses one over `SAME_VALUE_CHAIN` = 8 schema nodes. The validator's depth is then at most 62
  times 10 frames, under any CPython limit.
- `test_a_long_same_value_chain_is_refused` covers 1,500 nodes and 9, and accepts 7. It failed
  against the reviewed code.
- The catch-all point is spec 036's: 036's `invoke` should never raise, or its catch-all should
  keep `op`, `tool` and an unknown `abandoned`. The note is not written into 036's spec, since
  this branch carries one specification. It is left for 036's builder, in the disposition.

**F6.**
- I ran the reviewer's 21 mutants, adapted to the new code, plus 10 of my own, one for each new
  mechanism. All 31 are killed: `mutants.txt` in the worktree's scratch folder.
- My first run left two survivors: the key charge removed, and arrays walked at every delegating
  node. The `const` case and the recursive-union case in the checks above were sharpened until
  both were killed.
- `test_a_result_nested_too_deep_is_a_fault` covers the result bound.

**F7.**
- `Tool`'s guard is now a context variable that only `tool()` sets, so `dataclasses.replace`
  raises `TypeError` (`test_only_tool_makes_a_tool`; it failed against the reviewed code).
- numpy's `bool_` faults as "(internal error)", by Decision 6 as written; 036's README should
  say "return `bool(...)`".
- `max_calls=None` means no frame limit. It is private here, and 036 must not expose it
  unannounced (§4.15).

**Amended:**
- Decision 3: what a step is.
- Decision 4: the chain bound.
- Decision 8: the guest refuses any `"$bytes"` dict and what the frame rules would refuse.
- Decision 9 and criterion 14: the snapshot's growth is teardown.
- The README's budget paragraph, the CHANGELOG's costs, and a comment in `pyproject.toml`
  (review question 8).

**The artifact set after the revision.** The guest package changed, so steps 70 to 90 were
rebuilt (`scripts/build.sh --from 70`):

```
fbb1b1e2ac3f8b37bdf143c6e33e74dbafd62c1442826151b7fe80fb3e4fb531  MANIFEST
0cdc7b2bd78db6f5b73682b874ad94b4c23c47c6213c7d40ddfe49496299b725  python-snapshot.wasm
ee1acace2fc1fb2632067eef2abe24c2a9d5f83aa156b565d18ad9cb9c7bb4bc  python-stdlib.zip
4befe9de64edc783996ab006e6179b704a73a520b67431135df103db9db9625d  python.wasm
```

- `python.wasm` and every `LICENSES/` line are unchanged.
- The recipe line is now `bf592ac8…` for `recipes/guest/host/tools.py`.
- The zip: 1,102 `.pyc`, 11,175,028 bytes (+12,963 on main's frozen set).
- The snapshot: 65,509,949 bytes (+4,197).

**The cost, re-measured** on main's frozen set `s-8d84b3b190fe9bce` against the revised set,
under the same five heap perturbations:

| program | binary | mean | min | max |
|---|---|---|---|---|
| `-c pass` | snapshot | +110,800 | +87,167 | +122,141 |
| `-c pass` | plain | +155,809 | +145,020 | +167,345 |
| `-c "import os; os._exit(0)"` | snapshot | −989 | −1,163 | −838 |
| `-c "import os; os._exit(0)"` | plain | +151,746 | +145,927 | +160,073 |

So a snapshot's start and program cost nothing more, and its +0.11 M is teardown, as the review
found. A plain start pays for the two members it reads.

**The judge on the rebased, revised tree** (`uv run pytest`, no flags, its own artifacts):

```
wasi_python v1: 223/227 pass · 0 gap · 4 blocked · 0 fail   (unit suite 812/819, 7 skipped)
  v1.1  artifact set        24/25  blocked 1
  v1.2  portable, sealed    45/46  blocked 1
  v1.3  data stack          20/21  blocked 1
  v1.4  embedding           95/95
  v1.5  rebuild from pins   18/18
  rules constitution rules  21/22  blocked 1
blocked by: oracle 1 · prior-art clones 1 · three systems 1 · wheel 1
ratchet vs 789c841673: lost 0 · absent 0 · unrun 0 · unrun locally 2 · gained 4 · grew 40 · judge changed: pyproject.toml, tests/checks/test_rules.py, tests/checks/test_v1_4_embedding.py and 2 more
RED: 40 metric(s) grew
1035 passed, 11 skipped in 370.77s
```

- It is red only for growth.
- Against `context/progress/accepted.json`: 2 byte metrics (+12,963 zip, +4,197 snapshot) and
  41 fuel metrics rose, 38 past the ratchet; 6 fell.
  - `test_guest_runs_here`: +156,648 on plain, +101,353 on the snapshot.
  - The heavy jobs: from −447,659 (`numpy_csv`) to +2,190,148 (`pandas_csv`).
  - Criterion 11's fuel: snapshot 95,544,939; plain 5,005,055,535.
- `ruff check` and `ruff format --check` are clean on `src tests recipes/guest`.

**The growth reason for the lane:** "spec 031: the zip gains 2 members (+12,963 bytes) and the
snapshot +4,197 bytes; python.wasm unchanged; a plain start +~0.16 M fuel from reading 2 more zip
members, as Decision 9 predicted; a snapshot start +~0.11 M, all of it in Py_FinalizeEx after the
program (an os._exit(0) run differs by -989), not in the start or the program (Decision 9 and
criterion 14 as amended); heavy jobs move within +-2.2 M, heap-layout noise as in spec 033's
acceptance".

### The confirmation's N1 (2026-10-18)

The reviewer confirmed F1 to F7 and found one new bug, N1. Its fix is `src/` only, so the
artifact set does not change.

**The bug.**
- `Tool._keysets` was keyed by `(id(node), word)` alone.
- Pickle a `Tool`, free the original, and unpickle it in the same process: the new schema's
  nodes reuse the freed ids, and a node picks up another node's set.
- The reviewer saw 117 forbidden values accepted in 20 round trips.

**The fix.**
- Each entry now keeps its node, `(node, frozenset)`, and the validator uses it only when
  `entry[0] is s`.
- Otherwise the set is made again, charged, as for a schema no `tool()` vetted. A copied or
  unpickled `Tool` therefore pays its `enum` and `const` sizes once per frame.
- I chose this over keeping the sets out of the pickled and copied state: it is one test of
  identity, and it holds for any way a `Tool` is duplicated.

**The check.** `test_a_pickled_tool_checks_each_enum_against_its_own_set`:
- It makes a tool of 30 single-value `enum` properties and pickles it, then frees the original
  and unpickles the copy, five times over.
- Each property must accept its own value and refuse the 29 others.
- It failed against `7a587ad` (a valid value refused), and passes now.

**Evidence** (EXECUTED):
- The reviewer's `pickled3.py`, run on the fix: "0 wrong values accepted".
- The judge (`uv run pytest`, no flags, the worktree's own artifacts):
  `223/227 pass · 0 gap · 4 blocked · 0 fail (unit suite 813/820)`; `lost 0 · gained 4 ·
  grew 40`; red only for growth; 1036 passed.
- The growth list equals the revision's within 68 fuel on six checks, and exactly on the rest.
- `SHA256SUMS` is unchanged (zip `ee1acace…`, snapshot `0cdc7b2b…`, `python.wasm` `4befe9de…`).
- `ruff check` and `ruff format --check` are clean on `src tests recipes/guest`.

**Landed 2026-10-18** through the lane: rebased onto main (CHANGELOG conflicts kept both sides),
the main tree detached at `3059b71` rebuilt steps 70–90 and gave the worktree's `SHA256SUMS`
byte for byte (zip `ee1acace…`, snapshot `0cdc7b2b…`, `python.wasm` unchanged), spec 048's revised
documents committed on that HEAD (`c42410a`), accepted with `--accept-judge` and
`--accept-growth` (the confirmation's reason: two zip members, the snapshot's teardown) as
`64663de`, the rules tier passed, main fast-forwarded; the frozen set for builders became
`build/sets/s-0cdc7b2bd78db6f5`. Release dry run 39109451358 on `77bd08e`: every job passed.
