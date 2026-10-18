# 031 — A tool protocol over the door

- **Status:** drafted 2026-10-17; revised the same day against its pre-build review
  (`../reviews/031-a-tool-protocol-over-the-door-spec-2026-10-17.md`), whose split it adopts:
  this specification is the protocol, its host module and the guest package in the zip; **spec
  036** puts it in the runner (`run(tools=…)`, the door's cap before the copy, the bounds,
  `Completed.tools`). It changes the artifact set, so the revision was re-reviewed before build
  (constitution §5.6): **confirmed for build with conditions, written in** (the review's
  "Confirmation": C1 in Decisions 3 and 5 and criterion 4; C3 in Decision 4 and criterion
  5; C4 in criterion 8; C5 in Decision 5 and criterion 5).
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
      parser, validator or decoder recursion depends on the CPython version;
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
     its kind; an unknown kind raises `ToolError`.
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
14. `uv run pytest` green with `--accept-judge`; lost 0; the growth in bytes and in plain-start
    fuel (Decision 9) accepted with `--accept-growth` and that reason, and nothing else grows.
15. A release dry run passes every job (the artifact set changed).

## The owner's choices

None open here. Three of its choices, in Decisions 3 and 5, are the agent's where the owner's
decisions were silent: questions 50 to 52 in `../questions-for-the-owner.md`. Question 53 is
spec 036's. Nothing waits on them.

## Landing notes

Not built.
