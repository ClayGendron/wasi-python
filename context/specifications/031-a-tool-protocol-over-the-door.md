# 031 — A tool protocol over the door

- **Status:** drafted 2026-10-17. It changes the artifact set (the stdlib zip gains the guest's
  `host` package), so it needs its pre-build review before it is built (constitution §5.6).
- **Owner:** Clay Gendron
- **Kind:** build-class (constitution §5.7: it adds files under `recipes/` and changes
  `scripts/steps/70_zip.sh`). A new host module (`src/wasi_python/tools.py`); the runner
  (`src/wasi_python/runner.py`: `run`, `run_async`, `_checked`, `_instance`, `Completed`,
  `Defaults`, the fork hook); the guest package (`recipes/guest/host/`); `pyproject.toml`'s ruff
  paths; judge additions in `tests/`; `README.md`, `CHANGELOG.md`. It builds when no other
  build-class specification is in flight.
- **Depends on:** 001 and 003 (the door, `host=`, the zip step), 006 (safe by default), 011 (a
  call's recorded stop), 013 and 014 (arguments checked before any work), 015 (`cancel=`,
  `run_async`, the epoch callback, the fork hook), and **030** (a cancel during a door call is
  named `"cancelled"`), which lands first.
- **Research it stands on:**
  - `../research/2026-10-17-a-tool-protocol-over-the-door.md` (the design study; its prototype,
    `tool_host.py`, `guest_tools.py` and `prototype_run.py`, ran every scenario through today's
    door with no runner change: EXECUTED, `prototype_run.txt`);
  - the owner's decisions (`../decisions.md`): **12 and 14** (a gated tool protocol of our own,
    familiar from LangChain and Monty), **15** (async host functions, in a later specification),
    **17** (governance left to embedders), **37** (an optional `gate=`; tools are capabilities;
    the runner validates, routes, counts with `max_tool_calls` and records each call's outcome),
    **38 to 40** (`from host import tools`; schemas validated first; `subprocess.run`'s error
    rule; `ToolError` in the guest; no adapters shipped);
  - constitution §4.4 as amended 2026-10-17 (the raw door stays opaque; one optional tool
    protocol rides on it, used only when the embedder passes tools, gated per call), §4.5, §4.15.

## Terms

- **The door:** the one custom import, `host::call`, reached in the guest through the builtin
  module `_host` (`recipes/hostmodule.c`). The runner binds it to `host=`, a function from request
  bytes to response bytes (`runner.py`, `_door`).
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
  learns only that the call failed; the embedder gets the exception.

## The problem

The owner wants guest code to call the host's tools, APIs and MCP servers "through a gated
protocol that we design", with "a clean and familiar api" (decisions 12 and 14). Today the
door carries opaque bytes. Every embedder that wants tools must invent framing, schemas,
validation, error mapping, limits and a guest module, and must get each one right against a
hostile guest. The design study shows the whole protocol fits on today's door with no new
import, and that the familiar shape is a decorator on the host and ordinary functions in the
guest. It also found the one runner defect that a blocked tool exposes; spec 030 fixes it.

## Decisions

1. **One protocol, two halves, over the unchanged door.**
   - The host half is a new module, `wasi_python.tools`. The guest half is a pure-Python
     package, `host`, shipped in the stdlib zip. Between them run JSON frames, protocol 1
     (Decision 11), through `_host.call`.
   - The binary, its imports and its exports do not change. There is no third import (§4.4).
   - The protocol is used only when the embedder passes `tools=`. Without it, nothing of this
     specification runs on the host, and the door behaves exactly as today.
   - `import wasi_python` does not import `wasi_python.tools`; the runner imports it only when
     `tools=` is given, so the package's import cost is unchanged (spec 015's F6).

2. **The host API: a decorator, as LangChain's `@tool`.**
   - `wasi_python.tools.tool(fn=None, *, name=None, description=None, input_schema=None,
     validates_input=False, timeout_s=None, read_only=False, destructive=False,
     idempotent=False, open_world=False) -> Tool`. It works bare (`@tool`) and with arguments
     (`@tool(read_only=True)`).
   - **The name** is `name` or the function's `__name__`. It must match
     `[A-Za-z][A-Za-z0-9_]{0,63}` and must not be a Python keyword, so it is a guest identifier.
     A name that starts with `_` is refused by the same rule.
   - **The description** is `description`, or the docstring up to its first section heading
     (`Args:`, `Arguments:`, `Returns:`, `Raises:`), stripped.
   - **The input schema** comes from the signature and type hints. The root is `{"type":
     "object", "properties": …, "required": […], "additionalProperties": false}`. A Google-style
     `Args:` section gives each property its `description`. A parameter with a default is not
     required, and its default is the property's `default`.
   - **The hints it maps:** `str`, `int`, `float`, `bool`, `None`, `bytes`, `list[T]`,
     `dict[str, T]`, `Literal[…]` of JSON scalars, unions (`A | B`, `Optional[A]`) and `Any`.
     `bytes` maps to `{"type": "string", "contentEncoding": "base64"}` (Decision 6).
   - **It refuses**, with `TypeError` or `ValueError` naming the parameter, before anything
     runs: a parameter with no hint, a hint outside the list, `*args`, `**kwargs`, a
     positional-only parameter, a default with no JSON form, a bad name, an `async def`
     (Decision 15), and a given schema that uses a keyword outside the checked subset unless
     `validates_input=True` (Decision 6).
   - **`input_schema=`** replaces the derived schema. It is a dict whose root is `type:
     "object"`, or any object with a `model_json_schema()` method (a pydantic model class), so
     pydantic is never imported or required. The function is then called with the validated
     arguments as keywords, whatever its signature.
   - **The output schema** is derived from the return hint when the hint maps; otherwise it is
     absent. It is shown to the guest and in stubs, and never validated.
   - **The hints** `read_only`, `destructive`, `idempotent` and `open_world` are the embedder's
     labels, emitted as MCP's `readOnlyHint`, `destructiveHint`, `idempotentHint` and
     `openWorldHint` when true. A gate may read them. They grant nothing.
   - **`timeout_s`**, a positive number or `None`, bounds one call of this tool (Decision 9).
   - **`Tool`** is a frozen dataclass: `name`, `description`, `input_schema`, `output_schema`,
     `fn`, `timeout_s`, `validates_input` and the four hints. `Tool.descriptor()` returns the
     MCP-shaped dict. A `Tool` is callable on the host (`lookup_region(code="EMEA")` calls the
     function), so an embedder can test its tools without a guest.
   - **Tools are capabilities.** The decorator works on any function, closures and bound
     methods included. The README's first example makes tools per request inside a function
     that closes over the caller's authority. The runner adds no identity, user or policy to a
     call (decision 17, §4.5).

3. **The runner takes `tools=`, `gate=` and `max_tool_calls=`.**
   - `run(..., tools=None, gate=None, max_tool_calls=<default>)`, and `run_async` the same.
   - `tools` is an iterable of `Tool`s or plain functions. A plain function goes through `tool()`
     with no arguments. An empty iterable is allowed: the guest's `host.tools` then imports with
     nothing in it.
   - **Checked before anything runs**, in `_checked`, so `run_async` raises in the coroutine
     before queueing (specs 013 to 015): each item is a `Tool` or a function `tool()` accepts;
     names are unique; `gate` is `None` or a callable that is not a coroutine function;
     `max_tool_calls` is checked like `fuel` (an integer from 0 to 2**63 - 1, never `bool`, or
     `None` for no limit).
   - **`host=` and `tools=` exclude each other.** Passing both raises `TypeError` before
     anything runs: "pass host= for the raw door or tools= for the tool protocol, not both".
     Why: the door is one function. Under `tools=` the runner is that function, and it must see
     every frame to keep the count, the record and the rule that the guest supplies nothing the
     host trusts. Sharing the door would mean telling frames apart by their bytes, which would
     end the raw door's opacity (§4.4) and let a guest steer a frame to whichever side checks
     less. An embedder that wants both serves its own frames through `host=`, as today.
   - **`gate=` without `tools=`** raises `TypeError`: a gate the runner silently ignored would
     look like a gated raw door. An explicit `max_tool_calls` without `tools=` is checked and has
     no effect.
   - The command line (`wasi-python run`) gains nothing: tools are Python callables.

4. **Validated first, then gated, then run.** The runner's per-call host (`_ToolHost`, one per
   call, built in `_instance` beside the `_Call`) checks every frame in this order, with its own
   counters, and answers at the first failure:
   1. the frame count, against `max_tool_calls` (`budget_exceeded`);
   2. the frame's size, against the request cap (`too_large`);
   3. that it is JSON and an object (`protocol`);
   4. the version (`protocol`, naming the versions served);
   5. the operation (`protocol`);
   6. the tool's name, against the offered set (`unknown_tool`);
   7. the arguments, against the tool's input schema (`invalid_arguments`);
   8. the gate (`denied`);
   9. the tool, bounded (Decision 9) (`tool_error`, `denied`, `timeout`, `cancelled`);
   10. the result: it has a JSON form, and the answer fits the response cap (`tool_error`,
       `too_large`).

   No tool and no gate runs for a frame refused at steps 1 to 7.

5. **The gate is optional and absent by default (decision 37).**
   - Without a gate, every validated call of an offered tool runs. The embedder's gating is then
     its choice of which capabilities to pass. This is how this specification reads §4.4's
     "gated by the embedder on every call": the gate is the embedder's, it can see every call,
     and choosing tools is itself a gate.
   - `gate(call)` receives a `ToolCall`: `seq` (the host's frame number in this call, from 1),
     `tool` (the `Tool`), `arguments` (validated and decoded, the values the tool will get) and
     `request_bytes`. All of it is what the host decided; nothing is taken from the guest's frame
     unchecked. The frame's `id` is not shown.
   - It allows by returning `None` or `True`. It refuses by raising `ToolDenied(message)` (or
     `ToolError`); the message reaches the guest. A return of `False` refuses with the message
     "<name> was refused". Any other return, and any other exception, refuses with the same
     message and is recorded as a fault: a gate that breaks fails closed.
   - The gate and the tool run together on a tool worker under one bound (Decision 9), so a gate
     that asks a person must answer within the call's time or refuse.
   - A gate may not change the arguments. Pausing a run for approval is out of scope (bounded
     sessions, decision 19).

6. **The schema subset, checked strictly.**
   - **Checked keywords:** `type` (one or a list), `enum`, `const`, `properties`, `required`,
     `additionalProperties` (absent, it closes an object schema that lists `properties`, so an
     unknown argument is refused rather than passed to the function; this is stricter than JSON
     Schema's default, and the derived schemas say `false` anyway; an object schema with no
     `properties` stays open), `items` (one schema), `anyOf`, `oneOf`, local `$ref` into `$defs` or
     `definitions`, `minimum`, `maximum`, `exclusiveMinimum`, `exclusiveMaximum`, `minLength`,
     `maxLength`, `minItems`, `maxItems`, and `contentEncoding: "base64"` on a string.
   - **Ignored keywords** (annotations in JSON Schema): `title`, `description`, `default`,
     `examples`, `format`, `deprecated`, `readOnly`, `writeOnly`, `$schema`, `$id`, `$comment`.
   - **Any other keyword** makes `tool()` refuse the schema, unless `validates_input=True`
     states that the tool checks its own input. Then the runner checks the keywords it knows and
     skips the rest. So no schema is half-checked without the embedder saying so (the memo's
     question 3; see the owner's note at the end).
   - **No coercion.** `"7"` is not an integer; `true` is not an integer; an integer is a
     `number`. An unknown key is refused unless `additionalProperties` opens the object.
   - **Bytes.** A JSON object with exactly the one key `"$bytes"`, whose value is a string, is
     always bytes; it is decoded (strict base64) before validation. A value is bytes only where
     the schema says `{"type": "string", "contentEncoding": "base64"}`. A dict whose only key is
     `"$bytes"` cannot cross as a dict, either way.
   - **Parsing.** The host parses a frame with `json.loads` and a `parse_constant` that refuses
     `NaN` and `Infinity`; `RecursionError` and `ValueError` (deep nesting, an integer over
     CPython's 4,300 digits) are a `protocol` answer, never an exception from `run`.

7. **Errors follow `subprocess.run` (decision 39).**
   - `run()` never raises for what the guest, a frame, a tool or a gate does. Every one of those
     becomes an answer to the guest and a line in the record. A tool's or gate's
     `BaseException` (`SystemExit`, `KeyboardInterrupt` raised by the tool itself) is a fault
     too.
   - `run()` raises only for programming mistakes, before anything runs (Decision 3), and for
     what it raises today (a Ctrl-C on the calling thread, spec 011; `CancelledError` from a
     raw `host=`, spec 015).
   - **Which text crosses.** Only text a tool or gate chose to show: the message of `ToolError`
     or `ToolDenied`, truncated to 4,096 characters. Any other exception crosses as "<name>
     failed (internal error)" and is kept in the record as a fault. This is LangChain's line,
     and the reverse of what the memo saw in Monty and Cloudflare's code mode, where a host
     `KeyError('/Users/me/.ssh/id_rsa')` reached the sandbox (finding 2).
   - **On the host,** `ToolError(Exception)` and `ToolDenied(ToolError)`. A tool raising
     `ToolDenied` is a capability refusing (`denied`); a tool raising `ToolError` failed with a
     message (`tool_error`).

8. **Limits, each with a default (§4.15).**
   - **`max_tool_calls`**, default `DEFAULTS.max_tool_calls = 1000`, a new `Defaults` field with
     a default, so `Defaults` built from its first arguments still works. Every frame counts,
     the guest's discovery frame at import included: a frame is a host round trip, as Monty's
     `max_suspensions` counts them. Frames past the limit are answered `budget_exceeded` before
     they are parsed; the guest raises `ToolBudgetExceeded` and runs on. Only the first such
     frame is recorded, so the record holds at most `max_tool_calls + 1` entries. Why 1,000: it
     is Monty's default and ten times Pydantic AI's per-snippet default, ample for agent code,
     and it bounds the host's work and the record per call. `None` means no limit, as for the
     other limits.
   - **The request cap**, 1 MiB per frame (`TOOL_REQUEST_BYTES`): the host parses untrusted
     JSON, and the cap bounds that work and its memory. Bulk data goes through a granted folder.
   - **The response cap**, 16 MiB per answer (`TOOL_RESPONSE_BYTES`), the default output cap per
     stream. A result over it is answered `too_large`, naming the cap.
   - **Time** is Decision 9's.
   - The two caps are module constants, not arguments: an embedder that needs more data moves it
     through files.

9. **Deadlines, cancel, Ctrl-C and fuel hold across tool calls.**
   - **Tools run on tool workers.** A process-wide pool of at most `DEFAULTS.tool_workers`
     **daemon** threads (a new `Defaults` field, default 32, checked from 1 to 1024 like
     `async_workers`) runs the gate and the tool, inside a copy of the door thread's
     `contextvars` context. Daemon threads, not `ThreadPoolExecutor`'s workers, because
     interpreter exit joins those, and a hung tool would then hang exit. Why 32: the door is
     synchronous, so a guest has at most one call in flight; 32 is four times the default
     `async_workers`, with room for timed-out tools still running. A full pool makes a call
     wait, and the wait counts against that call's bound. The fork hook (spec 015) drops the
     pool in a child.
   - **The bound.** The door thread waits for the worker in slices of one tick (`TICK_S`). A call
     ends at the first of: the tool's `timeout_s`; the call's deadline less two ticks (from
     `stop_at` and the epoch ticker's count, as spec 010's waits read it), so the guest gets
     `ToolTimeout` before the run ends inside the door; the call's `cancel` event; and a pending
     Ctrl-C on the main thread (spec 011's flag). If the deadline leaves less than two ticks, the
     call is answered `timeout` at once and neither gate nor tool runs.
   - **After a timeout,** the guest gets `ToolTimeout` and runs on. A sync tool's thread cannot
     be stopped: it runs to its end, unseen, holding its worker, and its result is dropped. The
     README says so.
   - **After a cancel,** the host answers `cancelled`; the runner then stops the guest as spec
     015 does after any door call, and spec 030 names the run `"cancelled"`. Under `run_async`, a
     cancelled task therefore no longer waits on a blocked tool (spec 015's caveat for a blocked
     `host=` remains for the raw door).
   - **After a Ctrl-C,** the host answers `cancelled`, and the runner raises `KeyboardInterrupt`
     after the door returns, as today.
   - **Fuel** counts only guest instructions, so a tool's time never changes `fuel_used`. A call
     whose tools give the same answers spends the same fuel.

10. **Each call's outcome is in the result.**
    - `Completed` gains `tool_calls: tuple[ToolRecord, ...] = ()`, a last field with a default,
      so `Completed` built positionally still works. It is `()` for a call without `tools=`.
      The command line's JSON does not change.
    - `ToolRecord` (frozen): `seq`; `op` (`"list"`, `"call"`, or `None` when the frame could
      not be read); `tool` (the tool's name, or the guest's name cut to 64 characters, or
      `None`); `outcome` (`"ok"` or the failure's kind, Decision 11); `message` (what the guest
      was told on a failure, else `None`); `request_bytes`; `response_bytes`; `fault` (the
      exception kept from the guest, else `None`).
    - No record holds a time (§4.9). The record is the door transcript a replayable run needs
      (`../research/2026-10-17-what-a-replayable-run-needs.md`), apart from the values.
    - A refused call is recorded on an exit of 0 too, so an embedder can audit what the guest
      tried.

11. **The frame format: protocol 1.** One compact UTF-8 JSON object per door call, each way.
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
    - **The id.** The guest numbers its frames from 1; the host echoes the id when it can read
      one (an integer), else `null`. The host never trusts it.
    - **The version.** `v` is in every frame. An unknown version is a `protocol` answer naming
      the versions served. A field a peer may ignore may be added within a version; a field a
      peer must act on bumps `v` (Monty's rule). An operation may be added within a version,
      since an unknown operation is a clean `protocol` answer. `batch` is reserved for the later
      specification (Decision 15).
    - **Why JSON, and not MCP's JSON-RPC** (the memo): the guest has `json` with its C
      accelerator; every tool schema is JSON already; MCP's results are content blocks for a
      model and its sessions do not fit a one-call door. The descriptor uses MCP's names, so a
      tool maps one to one.
    - The README publishes this format, so an embedder in another language can serve it through
      its own door function.

12. **The guest side: `from host import tools` (decision 38).**
    - **`host`** (`host/__init__.py`) holds `PROTOCOL = 1` and the exceptions. Importing it sends
      no frame.
      | class | bases | kinds |
      |---|---|---|
      | `ToolError` | `Exception` | `tool_error`, and the base of all below; `.kind` names the kind |
      | `ToolDenied` | `ToolError`, `PermissionError` | `denied` |
      | `ToolArgumentError` | `ToolError`, `TypeError` | `invalid_arguments`, `unknown_tool` |
      | `ToolTimeout` | `ToolError`, `TimeoutError` | `timeout` |
      | `ToolCancelled` | `ToolError` | `cancelled` |
      | `ToolTooLarge` | `ToolError` | `too_large` (request or result; the memo's `ToolResultTooLarge` renamed for that reason) |
      | `ToolBudgetExceeded` | `ToolError` | `budget_exceeded` |
      | `ToolProtocolError` | `ToolError` | `protocol`, a door fault, an answer that does not match |

      The built-in bases make model-written `except PermissionError:` clauses work.
    - **`host.tools`** (`host/tools.py`) sends one `list` frame when it is imported. It then
      holds one plain synchronous function per tool, and nothing else public: no reserved names,
      so any valid tool name fits. Each function has a real `__signature__` built from the
      input schema (required parameters first), a docstring of the description and an `Args:`
      section, and a `descriptor` attribute (a copy of the host's descriptor). `help(tools)`,
      `inspect.signature` and `from host.tools import *` (through `__all__`) work.
    - **A call** binds its arguments to the signature (a binding error is `ToolArgumentError`,
      with no frame sent), passes every argument by keyword, and encodes values: `dict` with
      `str` keys, `list` and `tuple` as arrays, `str`, `bool`, `int` and finite `float`, `None`,
      `bytes`-like as `$bytes`, and any `numbers.Integral` or `numbers.Real` (numpy's scalars
      among them) as `int` or `float`. Anything else is `ToolArgumentError`, naming the type and,
      for an array or a frame, suggesting `.tolist()` or `.to_dict("records")`. It returns the
      decoded value. A failed answer raises the class for its kind; an unknown kind raises
      `ToolError`.
    - **An unknown attribute** of `host.tools` raises `AttributeError` listing the offered names.
    - **A run without tools.** Under no host, `from host import tools` raises `ImportError`:
      "this run has no tools: the embedder passed none". Under a raw `host=`, the discovery frame
      reaches that host like any other frame (its bytes are the embedder's to answer), and an
      answer that is not protocol 1 makes the import raise `ImportError` naming why. A failed
      protocol answer to the discovery frame (`budget_exceeded` under `max_tool_calls=0`, for
      one) also makes the import raise `ImportError`, naming its kind. So guest code can detect
      tools with `try: from host import tools except ImportError:`.
    - **Where it lives.** The source is `recipes/guest/host/__init__.py` and
      `recipes/guest/host/tools.py`, a build input hashed in `MANIFEST` like every recipe. Step 70
      adds them to the zip with two `--file` lines (`=host/__init__.py`, `=host/tools.py`),
      compiled like the rest. A pure-Python module in the zip needs no change to the binary and
      no new grant; the alternative, a module the runner writes into a read-only importable grant
      per call, waits on decision 16's specification and would make every embedder generate
      code. `ruff check` and `ruff format --check` cover `recipes/guest/` (`pyproject.toml`).
    - **The snapshot** does not pre-import `host` or `host.tools`. `host.tools` would call the
      door, and the snapshot's door stub traps; `host` alone saves too little to matter.

13. **Stubs for a prompt.** `wasi_python.tools.stubs(tools) -> str` renders each tool as a
    Python `def` line with the same signature the guest's function carries, and its docstring,
    with a first line `from host import tools`. A model is shown the same signatures its code
    will call (Monty's and Pydantic AI's pattern).

14. **No adapters ship (decision 40).** There is no LangChain or MCP adapter in the wheel. The
    README shows two short recipes built on `tool(fn, name=, description=, input_schema=,
    validates_input=True)`: a LangChain tool (its `tool_call_schema`, `invoke`, and its
    `ToolException` text re-raised as `ToolError`), and an MCP server's tool through the
    embedder's own client session (`structuredContent` as the value, `isError` as `ToolError`).
    Each recipe is run once by the builder in a throwaway environment (`uv run --isolated
    --no-project --with langchain-core …`, and `--with mcp` against the SDK's in-memory server),
    and the output is recorded in the landing notes (§4.10). The README labels them recipes,
    not API.

15. **Async tools are a later specification (decision 15).** This specification is
    synchronous end to end. `tool()` refuses an `async def`, and `run` refuses a coroutine
    gate, with `TypeError`: "async tools come with a later specification (decision 15)". The
    later specification adds async tools and gates, awaited on the caller's loop under
    `run_async` and on a private loop thread under `run`, within the same bound (Decision 9),
    and the guest's `batch` operation (several calls in one frame, run concurrently on the
    host). Why split: this one already adds a host module, a validator, a guest package in the
    zip and a build step; async adds a second execution path with its own cancellation, which
    one builder should not carry with the rest. Refusing now and accepting later breaks no
    caller.

16. **Docs.** The README gains "Tools": the decorator and the capability pattern (tools made per
    request, closing over authority); "a tool runs with your process's authority: a
    `read_file(path)` tool is a filesystem" (the memo's security finding); the gate; the record;
    the error rule; the limits and their reasons; timed-out tools that run on; the guest's API;
    the frame format; and the two recipes. The CHANGELOG gains a line.

## Intent

An embedder hands `run` a few decorated functions. The guest's code writes `from host import
tools` and calls them like Python. Every call is validated, optionally gated, bounded, counted
and recorded on the host. Nothing a guest or a tool does makes `run` raise.

## Design

```
src/wasi_python/tools.py              tool(), Tool, ToolCall, ToolRecord, ToolError, ToolDenied,
                                      stubs(); the hint mapper; the schema subset's validator;
                                      _ToolHost (protocol 1, one per call); the tool workers
src/wasi_python/runner.py             run/run_async(tools=, gate=, max_tool_calls=); _checked;
                                      _instance builds _ToolHost after stop_at and passes it as
                                      the _Call's host; Completed.tool_calls;
                                      Defaults.max_tool_calls and tool_workers; the fork hook
src/wasi_python/__init__.py           its docstring names wasi_python.tools
recipes/guest/host/__init__.py        PROTOCOL, the exceptions
recipes/guest/host/tools.py           discovery, one function per tool, encoding
scripts/steps/70_zip.sh               two --file lines
pyproject.toml                        ruff covers recipes/guest/
tests/unit/test_tools.py              the host half, with no guest
tests/unit/test_guest_tools.py        the guest package run natively against a fake _host
tests/checks/test_v1_4_embedding.py   end to end, against the built artifact set
README.md, CHANGELOG.md
```

## Scope

In: the above.

Out:
- async tools, async gates and `batch` (Decision 15's later specification);
- LangChain and MCP adapters in the wheel (decision 40: README recipes only);
- combining `host=` and `tools=` in one call;
- streaming, progress, and chunked large results;
- pausing a run for approval, and replay (bounded sessions, decisions 19 to 21);
- gates that rewrite arguments;
- tool sets that change during a call;
- host objects and classes (Monty's `ClassInstance`); bare global tool names;
- static type checking of the guest's code before it runs (an embedder can check against
  `stubs()`);
- MCP resources, prompts and sampling; raw MCP frames from the guest;
- tools on the command line.

## Acceptance criteria

Each new check is seen failing first: against today's code where the name is missing, and
against a stand-in that has the name but lacks the property where the property is the point
(listed per check). Nothing measures time. A tool that must block waits on a
`threading.Event` the check sets; a short `timeout_s` or `deadline_s` only chooses which outcome
happens, and the check asserts the outcome and the record, never a duration.

**Unit, the host half** (`tests/unit/test_tools.py`, no guest):
1. `test_a_tool_is_described_by_its_hints_and_docstring`: a sample tool's `descriptor()` equals
   an expected dict (properties, `required`, `additionalProperties: false`, the `Args:`
   descriptions, a default, a `Literal`, an optional, `bytes`, a hint).
2. `test_a_tool_that_cannot_be_described_is_refused`: each refusal of Decision 2 raises its
   error, with the parameter or keyword named; an `async def` names decision 15.
3. `test_the_validator_does_not_coerce`: a table of values against schemas, each keyword of the
   subset at least once (`"7"`, `true`, an unknown key, a missing key, a nested item, `anyOf`,
   `oneOf`, `$ref`, `const`, the bounds, `$bytes`), with the expected pass or `invalid_arguments`.
4. `test_frames_are_checked_in_order`: `_ToolHost` driven with raw frames (over the request cap,
   not JSON, `NaN`, nesting 100,000 deep, an integer of 5,000 digits, `v: 0`, an unknown `op`, an
   unknown tool, wrong arguments, past `max_tool_calls`) answers each with its kind, and the
   counters of a counting gate and tool stay at 0 for every one. Stand-in: a host that runs the
   gate before validating.
5. `test_the_gate_decides_after_validation`: allow by `None` and `True`; refuse by `False`, by
   `ToolDenied` (its message crosses), and by a stray exception and a stray return (generic
   message, recorded as faults). The tool's counter counts only allowed calls.
6. `test_only_chosen_text_crosses`: a `ToolError` message crosses; a `KeyError` naming a host
   path does not, its answer says "(internal error)", and the record keeps the exception. A
   result with no JSON form is the same. Stand-in: a host that sends `str(exception)`.
7. `test_run_refuses_mistakes_before_anything_runs`: `host=` with `tools=`, `gate=` without
   `tools=`, duplicate names, a non-callable gate, a coroutine gate and a bad `max_tool_calls`
   each raise from `run` and from `run_async` (before the executor is called), with a fake
   artifacts finder that counts zero lookups. `Defaults` built from three arguments still works;
   `max_tool_calls` and `tool_workers` are checked like the other limits.

**Unit, the guest half** (`tests/unit/test_guest_tools.py`, the recipe files loaded natively
with a fake `_host` that routes to a `_ToolHost`):
8. `test_the_guest_package_speaks_the_hosts_protocol`: `PROTOCOL` equals the host's; every kind
   the host can answer maps to the class of Decision 12; signatures, docstrings, `descriptor` and
   `__all__` match the tools; positional arguments go by keyword; numpy-like `numbers.Integral`
   values encode as `int`; bytes round-trip; a dict whose only key is `"$bytes"` is refused;
   `ImportError` when the fake raises `ConnectionRefusedError`, and when it answers bytes that
   are not protocol 1; `AttributeError` lists the offered names.
9. `test_stubs_match_the_guest_signatures`: for a set of tools covering every mapped hint, each
   `def` line of `stubs()` equals `def <name><inspect.signature(fn)>:` for the guest's function.

**End to end** (`tests/checks/test_v1_4_embedding.py`, the built artifact set, both binaries
where the check's existing peers run both):
10. `test_a_guest_calls_a_tool`: `from host import tools` and two calls, one result fed to
    `pandas.DataFrame`; stdout as expected; `tool_calls` is `list ok`, `call ok`, `call ok`, with
    byte counts above 0; `exit_code == 0`.
11. `test_a_forged_frame_is_validated_first`: the guest sends a frame through `_host.call` with a
    wrong-typed argument, and one with an unknown key; the tool's counter is 0; both records say
    `invalid_arguments`; the run exits 0.
12. `test_a_gate_refuses_before_the_tool_runs`: the guest catches `PermissionError` and prints
    the gate's message; the tool's counter is 0; the record says `denied` with that message.
13. `test_a_tool_fault_stays_on_the_host`: a tool raises `KeyError` naming a host path; the path
    is in neither stdout nor stderr; the record's `fault` is that exception; `run` did not raise.
14. `test_the_tool_call_limit_holds`: `max_tool_calls=3`, the guest makes six calls catching
    `ToolBudgetExceeded`; three frames are served (discovery and two calls), four are refused,
    and the record has four entries. Stand-in: a host that does not count the discovery frame.
15. `test_a_tool_timeout_ends_the_call_not_the_run`: a tool with `timeout_s=0.05` waits on an
    event; the guest catches `TimeoutError`, then calls another tool, which answers; exit 0; the
    record says `timeout`, then `ok`. The check sets the event afterwards so the worker ends.
16. `test_a_tool_blocking_past_the_deadline_is_answered`: a tool that waits on an event, under
    `deadline_s=0.3`, with no `timeout_s`; `run` returns, and the record's last entry says
    `timeout`. Stand-in: a host bound only by the tool's `timeout_s` (the check's child process
    reaches its 120 s fail-safe).
17. `test_a_cancel_during_a_tool_call_is_named`: in a child process like spec 015's, the tool
    sets a "started" event, the check sets `cancel`, and the run ends `trapped == "cancelled"`,
    `exit_code is None`, `fuel_used is None`, with the record's last entry `cancelled`.
18. `test_cancelling_an_async_call_during_a_tool_call`: `run_async` with a one-worker executor;
    the task is cancelled once the tool has started; it raises `CancelledError` while the tool
    still blocks, and then a new call on the same executor completes. Stand-in: a host that
    waits for the tool without watching `cancel`.
19. `test_fuel_is_exact_across_tool_calls`: the same program with two tool calls, run twice under
    a fuel cap, with tools that sleep different amounts each time; `fuel_used` is equal.
20. `test_a_large_result_is_refused`: a tool returning 17 MiB of bytes; the guest catches
    `ToolTooLarge` and runs on; the record says `too_large`.
21. `test_no_tools_no_protocol`: without `tools=`, `from host import tools` raises `ImportError`
    with the message of Decision 12; every existing `host=` check passes unchanged.
22. `test_the_zip_carries_the_host_package`: the zip holds `host/__init__.pyc` and
    `host/tools.pyc`; the existing check that `MANIFEST`'s recipe lines cover every tracked
    recipe passes with the two new files in it.

**The whole:**
23. The two README recipes ran once, as Decision 14 says, with their outputs in the landing
    notes.
24. `uv run pytest` green with `--accept-judge`; lost 0. The zip's growth (two small members) is
    accepted with `--accept-growth` and that reason; any fuel growth on existing checks is
    explained in the landing notes or fixed.
25. A release dry run passes every job (the artifact set changed).

## Questions for the owner

None open here. Four of these decisions (6, 8 and 9) are the agent's choice where the owner's
decisions were silent; they are recorded as questions 50 to 53 in `../questions-for-the-owner.md`,
and nothing waits on them.

## Landing notes

Not built.
