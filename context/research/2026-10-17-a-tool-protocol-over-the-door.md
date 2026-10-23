# A tool protocol over the door

- **Status:** research, 2026-10-17. It commits the project to nothing. It recommends a design for the specification that questions 12 and 14 call for.
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5), with one sub-agent for MCP, Cloudflare's code mode, smolagents and Pydantic AI. It wrote none of the code it studies. Box: one session.
- **Feeds:** the tool-protocol specification (constitution §4.4 as amended 2026-10-17), and the later async-host-function specification (question 15).
- **Stands on:**
  - the owner's words, `decisions.md` questions 12 and 14: "wasm-python should be able to call tools/api/MCPs of the host program through a gated protocol that we design", and "we should build our own convention. study langchain tools and monty for how it develops tools and how it passes to an embedded programs so we have a clean and familiar api";
  - constitution §4.4 (the raw door is opaque; one optional tool protocol rides on it, used only when the embedder passes tools, gated on every call), §4.5 (embedder-neutral), §4.7 (prior art studied, never copied) and §4.15 (safe by default);
  - `decisions.md` questions 15 (async host functions, later, with this protocol), 16 (read-only code on the import path), 17 (governance left to embedders);
  - `2026-10-17-the-runtime-for-agent-code.md` §3.2, the ten needs of a tool convention;
  - `2026-10-17-market-research-use-cases.md` proposal A ("tools appear inside the guest as ordinary Python functions");
  - specs 001 (the door and `host=`) and 015 (`cancel`, `run_async`, and what bounds a door host).

## Terms

- **The door:** the one custom import, `host::call`. The guest reaches it through the builtin module `_host` (`recipes/hostmodule.c`), as `_host.call(bytes) -> bytes`. The runner binds it to `host=`, a function from request bytes to response bytes (`src/wasi_python/runner.py:68`, `_door` at 2194-2229).
- **A frame:** the bytes of one door call, one way.
- **A tool:** a host function the embedder offers the guest, with a name, a description and an input schema.
- **A descriptor:** the data that describes a tool: name, description, input schema, and optionally an output schema and hints.
- **JSON Schema:** the standard way to describe the shape of JSON. MCP, OpenAI, Anthropic, LangChain and Pydantic AI all describe tool inputs with it.
- **The gate:** the embedder's function that allows or refuses each call, after the arguments are checked and before the tool runs.
- **A stub:** a Python `def` with a signature and a docstring but no body, shown to a model so it knows what it may call.
- **A suspension** (Monty's term): the interpreter stops at a host call and waits to be resumed with a value or an exception.

## Labels

**EXECUTED** means run here, with its script and output in `2026-10-17-a-tool-protocol-over-the-door/`. **READ** means read in a file or page, cited by path and line; paths under `context/prior_art/` are at the commits that `context/prior_art/README.md` records. **READ (sub-agent)** marks a citation that the sub-agent read and I did not re-read line by line. I spot-checked four of them: MCP `schema.ts` for the 2026-07-28 Tool and `isError`, and Cloudflare `executor.ts:161-188`. **INFERRED** means my reasoning.

Versions used: langchain-core 1.6.12 (pydantic 2.14.1); pydantic-monty 1.1.0 from PyPI (the clone is newer, see finding 2); smolagents 1.26.0; pydantic-ai-slim 2.57.0; this repository's `build/artifacts/` (Python 3.15.0, numpy 2.5.2, pandas 3.0.6) under wasmtime-py 49.

## Method

- **Cloned and read:** `langchain`, `monty`, `mcp-spec`, `cloudflare-agents`, `smolagents` and `pydantic-ai`. All six are under `context/prior_art/`. Licences were checked on cloning: MIT; MIT; Apache-2.0, MIT and CC-BY-4.0 in transition; MIT; Apache-2.0; and MIT. Rows were added to that README's table.
- **Probed each library in a throwaway environment** (`uv run --isolated --no-project --with …`):
  - `langchain_probe.py`, with output in `langchain_probe.txt`;
  - `monty_probe.py` and `monty_probe.txt`;
  - `smolagents_probe.py` and `smolagents_probe.txt`;
  - `pydantic_ai_probe.py` and `pydantic_ai_probe.txt`.
- **Built a prototype of the recommended protocol and ran it through the real door.** It is a pure-Python guest module, `guest_tools.py`, and a host library, `tool_host.py`. The prototype needed no change to the runner or the binary.
  - `prototype_run.py` runs the scenarios against `build/artifacts/`; its output is `prototype_run.txt`.
  - `door_timing_probe.py` isolates one runner defect the prototype found; its output is `door_timing_probe.txt`.
- **Nothing measures time.** The sleeps in the scripts only choose which outcome happens. What the scripts report is outcomes and counts.

## Findings

### 1. LangChain: the host-side shape developers know (READ, EXECUTED)

- **A decorator makes a tool from a function.** `@tool` takes `parse_docstring`, `args_schema`, `response_format` and `return_direct`. It returns a `StructuredTool` (`langchain_core/tools/convert.py:77-87`, `tools/structured.py:93`). The name is the function's name. The description is the docstring's first part.
  - With `parse_docstring=True`, a Google-style `Args:` section becomes the per-argument descriptions of a JSON Schema (EXECUTED, `langchain_probe.txt`, "tool_call_schema json").
- **Every tool is a name, a description and a schema** (`tools/base.py:473-493`). The schema is a pydantic model, or a JSON Schema dict. `tool_call_schema` drops the arguments the framework injects (`base.py:677-723`). Converting to the OpenAI shape gives `{type: "function", function: {name, description, parameters}}`. With `strict=True` it adds `additionalProperties: false` and makes every field required (EXECUTED; `utils/function_calling.py:825-840`).
- **Validation is pydantic's lax mode.** All EXECUTED:
  - `year="7"` is coerced to `7`;
  - an unknown argument (`colour`) is dropped silently;
  - a wrong type raises `ValidationError`.
- **Errors come in two kinds.**
  - A tool raises `ToolException` to fail with a message for the model. By default it propagates.
  - With `handle_tool_error=True`, the error becomes a `ToolMessage` with `status="error"` and the message as content (`base.py:527-545`, `1114-1131`; EXECUTED). `handle_validation_error=True` likewise gives the fixed text "Tool input validation error" (EXECUTED).
  - Any other exception always propagates, even when handling is on (EXECUTED, the `boom` probe). So LangChain's line is "a message the tool chose to show" against "a bug".
- **A call by a model is a `ToolCall`** `{type, id, name, args}`. Its answer is a `ToolMessage`: `content`, `tool_call_id`, `status`, and an `artifact` that is kept from the model (`messages/tool.py:26-81`, `206`; EXECUTED). `response_format="content_and_artifact"` splits a result into what the model reads and what the program keeps (EXECUTED).
- **Sync and async in one type.** `func` and `coroutine` are both optional. `ainvoke` of a sync tool runs it in an executor (`structured.py:121-123`). `invoke` of an async-only tool raises `NotImplementedError` (EXECUTED).
- **Names are not checked.** `"my tool"`, `"a.b"` and an 80-character name were all accepted (EXECUTED). The model provider refuses them later.

**What it means (INFERRED).** The familiar host side is this:
- a decorator over a plain function;
- the schema derived from type hints and a Google-style docstring;
- an explicit exception type for errors the model may see;
- sync or async tools alike.

LangChain, smolagents and Pydantic AI each do this their own way (finding 3). Developers expect it.

### 2. Monty: how a sandbox exposes host functions (READ, EXECUTED)

- **A call suspends; it never calls out.** "The interpreter never calls out; it stops and waits to be told what happened" (`monty/docs/host-functions.md:7-9`). The host answers through `external_lookup`, a dict from names to callables (`:50-52`). A name not offered raises `NameError` in the sandbox (`:77`; EXECUTED).
- **Modules, with stubs.** On the cloned main branch, `external_modules={'tools': ExternalModule({...}, stubs='...pyi...')}` makes `import tools` and `tools.add(1, 2)` work (`host-functions.md:300-382`). Missing attributes raise `AttributeError` and missing modules `ModuleNotFoundError`. The PyPI release 1.1.0 does not have `ExternalModule` yet (EXECUTED: it is absent from the package). So that part of this finding is READ only.
- **No schema, and no host-side check of arguments.** A host function receives the sandbox's values as written. An `int` reached a `str`-annotated host function unchanged (EXECUTED: the host saw `('int', 123)`). The defence is optional static checking of the model's code before it runs: Monty bundles the `ty` type checker, against stubs the host declares (`docs/type-checking.md:58-110`). The pattern Monty recommends is "the model sees the tool signatures, the checker enforces them" (`:181-183`). Its examples write those stubs by hand, with docstrings (`examples/expense_analysis/main.py:5-36`).
- **Errors cross as Python exceptions, by type name.** A host exception "behaves like an ordinary Python exception inside the sandbox", but only for the types Monty implements (`host-functions.md:177-234`). Both of these were EXECUTED:
  - A host class Monty does not know (`QuotaExceeded`) arrived as plain `Exception`.
  - **A host `KeyError('/Users/me/.ssh/id_rsa')` carried its message into the sandbox.** A careless tool leaks host detail.
- **Gating is the suspension API.** `feed_start` hands each call back as a `FunctionSnapshot` with `function_name`, `args`, `kwargs` and `call_id`. The docs say: "so you can log it, rate-limit it, require approval for it" (`host-functions.md:404-446`). Resuming with `{'exc_type': 'PermissionError', ...}` raised a catchable `PermissionError` in the sandbox, and the program ran on (EXECUTED).
- **Async and concurrency.** Under `AsyncMonty`, coroutine host functions are awaited on the host's loop. `asyncio.gather` in the sandbox runs several at once (`host-functions.md:236-298`). EXECUTED: `fetch('a')` waited on an event that only `fetch('b')` set, and both finished. A serial driver would have deadlocked. On the wire, a call may be answered with a future; the child later suspends with `ResolveFutures {pending_call_ids}`, and the parent answers with `ResumeFutures` (`crates/monty-proto/proto/monty/v1/monty.proto:681-712`, `851-869`, `1057-1063`).
- **Limits.** All READ unless marked.
  - `max_suspensions` caps host round trips per session. Its default is 1,000, and it "cannot be disabled" (`docs/resource-limits.md:56-62`). EXECUTED: with a cap of 5, ten calls failed with `RuntimeError: suspension limit 5 exceeded`.
  - Execution time is paused while the host answers, so "a host function that takes a minute costs nothing". A host that must bound its own waiting uses `request_timeout` (`:104-140`).
  - A value and its envelope must fit 256 MiB (`limitations/host-values.md:67-73`).
- **The wire is versioned, strict and framed.** It is protobuf in 4-byte length-prefixed frames, one request and one reply in strict alternation (`monty.proto:1-23`). There is a `protocol_version` with a supported range and no negotiation in-band. "A field the peer must act on" needs a version bump, even when the change is additive (`monty.proto:13-23`; `crates/monty-proto/README.md:41-47`). "Children are untrusted": every frame from the child is validated under a decode budget (`README.md:72-103`).
- **Its own safety advice** (`host-functions.md:448-462`): validate arguments "as untrusted input"; "`read_customer(id)` is a tool; `read_file(path)` is a filesystem".

**What it means (INFERRED).** Monty's guest side is the familiar one for code mode: tools are ordinary callables, in a module the code imports, described to the model by Python stubs with docstrings. Its gate is the suspension, which sees every call by name and arguments. What Monty does not do, and this project must: check arguments on the host, and keep a tool's internal errors from reaching the guest.

### 3. The others, briefly (READ (sub-agent) unless marked)

- **MCP**, the 2026-07-28 schema, which is the latest.
  - A `Tool` is `name`, `title?`, `description?`, `inputSchema` (JSON Schema whose root is `type: "object"`), `outputSchema?` and `annotations?` (`mcp-spec/schema/2026-07-28/schema.ts:1973-2009`; I re-read this). The annotations are `readOnlyHint`, `destructiveHint`, `idempotentHint` and `openWorldHint`. They are hints, and "untrusted unless the server is trusted" (`:1905-1954`).
  - `CallToolResult` is `content` blocks (text, image, audio, links, resources), plus `structuredContent?` and `isError?` (`:1809-1838`).
  - **There are two error channels.** A tool's own failure is a result with `isError: true`, "so the LLM can see it and self-correct". An unknown tool or a malformed request is a JSON-RPC error (`:1826-1836`; I re-read this).
  - Names SHOULD be 1 to 128 characters of `[A-Za-z0-9_.-]` (`docs/.../tools.mdx:309-332`).
  - Progress is opt-in notifications, and cancellation is a "hint" that races with completion.
  - The spec asks servers to validate inputs and clients to confirm sensitive operations, set timeouts and keep an audit log (`tools.mdx:787-800`).
- **Cloudflare code mode.**
  - Tools from MCP servers and other sources become a typed namespace in a Worker that has no network.
  - TypeScript types are generated from each tool's JSON Schema (`packages/codemode/src/tool-types.ts:221-284`). Names are sanitised to identifiers (`utils.ts:74-96`).
  - Each call crosses back to the host as `ToolDispatcher.call(name, argsJson)`. The host never throws across the boundary: it answers `{result}` or `{error}`, and the sandbox re-throws (`executor.ts:161-188`, which I re-read).
  - That `{error}` is the exception's own message, for any exception (`executor.ts:181-184`). It leaks as Monty's does.
  - Approval is `requiresApproval` per tool. A pending call aborts the run, and the code re-runs after approval, replaying finished calls from a log (`docs/codemode/approvals.md`).
- **smolagents.**
  - `@tool` derives `inputs` and `output_type` from hints and the `Args:` docstring. The model sees a Python `def` stub (`src/smolagents/tools.py:258-287`, `1061-1100`).
  - EXECUTED: a default (`units="c"`) became `nullable` and was lost, and the stub printed JSON type names (`city: string`), which is not valid Python.
  - Its remote executors (E2B, Docker, Modal) **ship each tool's source code into the sandbox** and run it there (`remote_executors.py:94-113`). So a tool that needs the host cannot work remotely (`agents.py:1609`).
- **Pydantic AI.**
  - The schema comes from hints, with griffe parsing the docstrings.
  - `ModelRetry` sends a message to the model; `requires_approval=True` makes the tool kind `unapproved`, and a deferred call goes back to the caller.
  - EXECUTED: `additionalProperties: false`, and the default `"c"` kept.
  - Its harness's code mode runs model code in Monty, renders tools as `async def` stubs, and sends every nested call through the normal tool manager (`code_mode/_toolset.py:642-673`, `1397-1412`). By default it allows 100 tool calls per snippet, reserved before they are scheduled (`code_mode/README.md:220`).
  - "The sandbox can't round-trip to the caller", so a call that needs approval becomes a retry (`_toolset.py:646-665`).
- **OpenAI and Anthropic.** Both describe a tool as name, description and JSON Schema. Both answer a call with a result that can be marked as an error: Anthropic's `is_error`, and OpenAI's output string. Anthropic tool names match `^[a-zA-Z0-9_-]{1,128}$` (the sub-agent, from the Anthropic docs; not re-read).
- **E2B and Daytona.** They expose the sandbox to the host. Neither documents a way for sandbox code to call host functions (INFERRED by the sub-agent).

**What it means (INFERRED).**
- **The industry agrees on the descriptor.** It is a name, a description, a JSON Schema for the input, and optionally an output schema and hints. MCP's field names are the common denominator.
- **It agrees on two error channels:** "the call could not be made", against "the tool ran and failed with a message for the model".
- **It agrees that tools stay on the host and calls are proxied,** as Cloudflare, Pydantic AI and Monty do, and smolagents' remote path does not.

### 4. The protocol works over today's door, with no runtime change (EXECUTED)

The prototype (`guest_tools.py`, `tool_host.py`) ran every scenario through `wasi_python.run(..., host=ToolHost(...))`. The output is in `prototype_run.txt`.
- **Discovery is one frame at import.** `import tools` sent one `list` frame (`frames=1 calls=0`). The module then held one Python function per tool, with a real signature, `(code: str, year: int = 2026)`, and the docstring with its `Args:` lines. A destructive tool's hint was visible through `tools.describe()`.
- **Calls return Python values.** `tools.lookup_region("EMEA")` returned a dict. `pd.DataFrame(tools.sales(region="EMEA"))` ran pandas on a tool's result, in three frames.
- **The host checks every argument, whatever the guest sends.**
  - A wrong type, an unknown key and the string `"7"` for an integer were each refused as `invalid_arguments`, with no coercion.
  - A frame forged with `_host.call`, bypassing the module, got the same refusal.
  - A frame with protocol version 0 got `protocol: "protocol 0 is not served; this host serves 1"`.
  - Bytes that are not JSON got a `protocol` error.
  - None of these raised in the runner.
- **The gate refused a destructive tool.** The guest saw `ToolDenied`, a subclass of `PermissionError`, carrying the gate's message.
- **Error text is split by intent.** A tool that raised `ToolError("no record 7; …")` passed its message to the guest. A tool with a bug (`KeyError('/Users/me/.ssh/id_rsa')`) passed only `secret_fault failed (internal error)`. The exception was kept for the embedder.
- **Timeout, async and bytes.**
  - A sync tool that blocked past its 0.2 s timeout gave the guest `ToolTimeout`, a `TimeoutError`, and the guest's next call succeeded.
  - An async tool ran on a host event loop.
  - Bytes crossed both ways as `{"$bytes": base64}`.
- **Caps.**
  - A 2 MB result against a 1 MiB response cap gave `ToolResultTooLarge`.
  - With `max_calls=4`, the fifth call gave `ToolBudgetExceeded`.
- **Without tools.**
  - With no host bound, `import tools` raised `ToolError: this run has no tools`.
  - With an empty tool list, the module imported empty, and any attribute raised `AttributeError` listing what is offered.
- **LangChain.** A LangChain `@tool` went through a twelve-line adapter (`from_langchain`):
  - its signature appeared in the guest;
  - its pydantic validation ran on the host;
  - its `ToolException` reached the guest as `ToolError: no such city`.
- **The prototype's simple stub renderer** gave the same signatures for a prompt (host side).

### 5. A cancel during a door call is misreported (EXECUTED; a runner defect)

The prototype's cancel scenario ended with `trapped='error while executing at wasm backtrace:'`, not `"cancelled"`. `door_timing_probe.py` repeats it with a plain `host` and no tool layer (`door_timing_probe.txt`):

| while the host blocks | answer | `trapped` |
|---|---|---|
| the deadline passes | 2 bytes, or 0 | `"deadline"` |
| `cancel` is set | 2 bytes, or 0 | `"error while executing at wasm backtrace:"` |
| control: `cancel` set while the guest computes | (no door call) | `"cancelled"` |

**Why (READ, then INFERRED).**
- After `host` returns, the door calls the guest's exported `host_alloc`, even for an empty answer (`runner.py:2224`). That is guest code, so the overdue epoch check fires there.
- Under `cancel=`, the epoch callback records `call.ended = "cancelled"` and returns an error (`runner.py:1875-1877`).
- The door re-raises that error from `host_alloc` (`2204-2205`). The shared host function then records it as the call's stop (`1833-1836`).
- `_drive` reads `call.stopped` before `call.ended` (`1746-1758`), so the run is named by the raw error.

In both rows the guest never sees the door's answer: the run ends inside the door. A tool protocol makes this common, because a blocked tool is the usual place to cancel. The fix is small: prefer `call.ended` when the recorded stop is the callback's own error. It belongs in the tool specification, or in a fix to spec 015 before it. It is a defect, not a design question.

## Answers to the brief

### (1) The familiar shape

- **Host side.**
  - A decorator over a plain function. The schema comes from the type hints and a Google-style `Args:` docstring. Sync and async functions work alike.
  - An explicit exception type for failures the model may read.
  - A JSON Schema descriptor in MCP's field names.
  - Adapters for existing LangChain tools and MCP servers.
  - This is LangChain's and Pydantic AI's shape (findings 1 and 3), and MCP's descriptor.
- **Guest side.**
  - `import tools`, then `tools.search(q="…")`: ordinary synchronous functions, with signatures and docstrings, so `help(tools)` and `inspect.signature` work. This is Monty's `ExternalModule` shape (finding 2) and proposal A's.
  - No `await`. This guest has no threads, and its `asyncio` cannot wait on the door: the selector waits in `poll_oneoff`, which knows only clocks and descriptors (the agent-runtime memo §3.2, item 5). Fan-out is a batch call instead.
  - The model is shown the same signatures as stubs, rendered on the host.

### (2) Errors, timeouts, cancellation, large results, streaming, gating

- **Errors.** There are two channels, as in MCP:
  - a protocol failure, where the frame is malformed, the version unknown or the tool unknown;
  - a call failure, with a closed set of kinds: `invalid_arguments`, `denied`, `tool_error`, `timeout`, `cancelled`, `too_large`, `budget_exceeded`.

  Each kind is a guest exception class that also subclasses the matching built-in: `PermissionError`, `TypeError` or `TimeoutError`. So model-written `except` clauses work.
- **Which text crosses.** Only text that a tool chose to show crosses: our `ToolError`, LangChain's `ToolException`, or MCP's `isError` text. Any other exception becomes "failed (internal error)" and is kept for the embedder. This is LangChain's line, and the reverse of Monty's and Cloudflare's behaviour, both of which leak (finding 2; finding 3).
- **Timeouts.** Each call is bounded by the smallest of three things:
  - the tool's own timeout;
  - a per-call default;
  - the run's remaining deadline, less a margin of two ticks, so the guest gets `ToolTimeout` before the run ends inside the door (finding 5).

  A timed-out async tool's task is cancelled. A timed-out sync tool's thread cannot be killed: it runs on, unseen, in a bounded pool, and the README must say so.
- **Cancellation.** The runner hands the call's cancel event to the tool host. The tool host waits in slices, sees the event, cancels the task and answers `cancelled`. The runner then stops the guest, as spec 015 does after any door call. That needs finding 5's fix.
- **Large results.** A per-response cap applies, and a result over it gives `too_large`, naming the cap. Bulk data belongs in files: a tool can write to a writable grant and return the path. Chunked handles (open, read, close) are left for later.
- **Streaming and progress.** Neither is in version 1. The guest is blocked during a call, so it has no use for progress. One request, one response.
- **Gating.** The gate runs on every call after validation and before the tool runs. It allows or refuses with a message. An approval that needs a person must answer within the call's timeout, or refuse with a message such as "asked for approval; try again later". Pausing and resuming a run is for the bounded sessions of question 19, later.

### (3) The wire format

See "The frame format" below. In short:
- one JSON object per door call, each way;
- a version and an id in every frame;
- three operations: `list`, `call` and `batch`;
- MCP's descriptor fields;
- `{"$bytes": base64}` for binary data;
- caps on request size, response size and calls per run.

An MCP tool maps one to one:
- its descriptor passes through, with the name made an identifier;
- `structuredContent` becomes the value;
- `isError` becomes `tool_error`, with the text;
- other content blocks become a list of `{type, text | data, mimeType}`.

### (4) Security

- **The gate sees what the host decided, never what the guest claimed.** That is:
  - the host's call number;
  - the tool's descriptor, including the embedder's own hints;
  - the arguments, already validated;
  - the request's size;
  - the calls and bytes so far.

  The guest's frame `id` is echoed and never trusted. An MCP server's hints are untrusted unless the embedder trusts the server.
- **Schema validation is on the host, always.** The guest module's own signature check is a convenience only. Finding 4 shows a forged frame refused. Validation is strict: no coercion, and objects closed unless their schema opens them.
- **Resource caps, each with a default (§4.15):**
  - calls per run;
  - request bytes and response bytes;
  - the per-call timeout;
  - the batch size.

  The host's JSON parser rejects NaN and Infinity, and catches deep nesting and huge integers. The prototype catches `RecursionError` and `ValueError`; CPython refuses integers over 4,300 digits.
- **No new import (§4.4).** The guest module is pure Python over `_host`. The prototype ran on the shipped binary unchanged.
- **Embedder-neutral (§4.5).** The protocol carries no embedder's names, verbs or identity. Identity stays in the embedder's closures, as with `host=` today (the agent-runtime memo §3.2, item 8).
- **Tools run with the host's authority.** This is Monty's warning (`host-functions.md:448-462`) and vfs's "one stated exception" (the agent-runtime memo §3.3). The README must say: a tool is a capability you built, and a `read_file(path)` tool is a filesystem.

## What it decides (recommended design)

These recommendations are for the specification to adopt or change. Each is labelled with the finding it rests on.

### The host API

```python
from wasi_python import run, run_async
from wasi_python.tools import tool, ToolError, Denied, from_langchain, from_mcp, stubs

@tool(read_only=True)
def lookup_region(code: str, year: int = 2026) -> dict:
    """Look up a sales region by its code.

    Args:
        code: The region code, such as "EMEA".
        year: The fiscal year.
    """
    if code not in REGIONS:
        raise ToolError(f"no region {code!r}; known: {sorted(REGIONS)}")  # the guest sees this
    return REGIONS[code]

@tool(destructive=True, timeout_s=10)
async def delete_report(report_id: str) -> str:
    """Delete a saved report."""
    await store.delete(report_id)
    return "deleted"

def gate(call):                               # every call, after validation, before the tool
    if call.tool.hints.get("destructive") and not user.may_delete:
        raise Denied("deleting needs the owner's approval")

my_tools = [lookup_region, delete_report, from_langchain(weather), *from_mcp(github, prefix="gh")]
prompt = SYSTEM + stubs(my_tools)             # the same signatures the guest's functions carry
done = run(["-c", model_code], tools=my_tools, gate=gate, deadline_s=30)
done = await run_async(["-c", model_code], tools=my_tools, gate=gate)  # async tools on this loop
done.tool_calls, done.tool_faults             # counts; faults are the exceptions kept from the guest
```

- **`tool`** derives the descriptor from hints and the docstring.
  - It covers a documented subset of types: `str`, `int`, `float`, `bool`, `None`, `bytes`, `list[T]`, `dict[str, T]`, `Literal`, unions, and `TypedDict`.
  - It also takes an explicit `input_schema=`, or any object with a `model_json_schema()` method (a pydantic model), so pydantic is never imported or required. Finding 1.
  - Names must be Python identifiers, at most 64 characters, not starting with `_`. The adapters sanitise other names and keep a map back to the originals, as Cloudflare and Pydantic AI do.
- **`from_langchain(t)`** is duck-typed, with no import of LangChain unless it is called. It uses `t.tool_call_schema`, `invoke` or `ainvoke`, and passes `ToolException` text through (finding 4).
- **`from_mcp(session, prefix=)`** lists the server's tools and calls them through the embedder's own MCP client session. It maps results as in answer (3), and cancels the MCP request on a timeout or a cancel. It is an adapter over the embedder's client, not an MCP client of ours.
- **`gate=` is required whenever `tools=` is given.** `wasi_python.tools.allow_all` is the explicit way to allow every call. This reads §4.4's "gated by the embedder on every call" and §4.15 literally. It is question 1 below.
  - A gate may be sync or async.
  - An exception from the gate is a refusal, and is counted as a fault.
- **`tools=` and `host=` exclude each other in version 1.** `tools=` is sugar for a host the runner builds and binds to the call's deadline and cancel event. The protocol host is also public (`ToolHost`), so an embedder can compose it with its own frames.
- **Async tools.**
  - Under `run_async`, async tools and gates are awaited on the caller's loop, through `run_coroutine_threadsafe` with a timeout. This is spec 015's README pattern, and question 15's "awaited by the guest's door call, under the call's deadline".
  - Under `run`, they run on one private loop thread per process.
  - Sync tools run in a bounded pool of their own.

### The guest API

```python
import tools                       # one `list` frame; ToolError if the run has no tools
help(tools.lookup_region)          # (code: str, year: int = 2026) and the docstring
r = tools.lookup_region("EMEA")    # a dict; JSON-like values in, Python values out
try:
    tools.delete_report("r1")
except PermissionError as e:       # tools.ToolDenied
    print("refused:", e)
a, b = tools.batch(tools.lookup_region.bind("EMEA"), tools.lookup_region.bind("APAC"))  # one frame
tools.call("lookup_region", code="EMEA")   # by name; tools.describe() gives the descriptors
```

- **`tools` ships in the stdlib zip** as a pure-Python module of about 150 lines. It is the project's code, so it is neutral. A non-Python embedder then only implements the host side of a published format.
  - The alternative is a module the runner generates per call into a read-only importable grant (question 16). It would make every embedder generate code, and it would wait on that specification.
  - Changing the zip changes the artifact set, so the specification needs its pre-build review (§5.6). The name is question 2.
- **The functions are synchronous.** `batch` is the one fan-out: up to N calls in one frame, each validated and gated, run concurrently on the host, with results in order. Its first error is raised, unless `return_exceptions=True`, as with `asyncio.gather`. INFERRED from the agent-runtime memo §3.2, item 5.
- **Exceptions:** `ToolError` with `.kind`; `ToolDenied` (also `PermissionError`), `ToolArgumentError` (also `TypeError`), `ToolTimeout` (also `TimeoutError`), `ToolCancelled`, `ToolResultTooLarge`, `ToolBudgetExceeded` and `ToolProtocolError`. An unknown tool raises `AttributeError`, listing what is offered.
- **Reserved names.** The module's own names (`call`, `batch`, `describe`, and the exception classes) cannot be tool names.

### The frame format (protocol 1)

Each frame is one UTF-8 JSON object per door call, each way. It is compact, with no NaN or Infinity.

```text
request   {"v": 1, "id": 7, "op": "list"}
          {"v": 1, "id": 8, "op": "call",  "tool": "lookup_region", "args": {"code": "EMEA"}}
          {"v": 1, "id": 9, "op": "batch", "calls": [{"tool": "...", "args": {...}}, ...]}

answer    {"v": 1, "id": 7, "ok": true, "tools": [descriptor, ...]}
          {"v": 1, "id": 8, "ok": true, "value": <JSON>}
          {"v": 1, "id": 9, "ok": true, "results": [{"ok": true, "value": ...},
                                                    {"ok": false, "error": {...}}]}
          {"v": 1, "id": 8, "ok": false, "error": {"kind": "denied", "message": "..."}}

descriptor {"name", "description", "inputSchema", "outputSchema"?, "annotations"?}   (MCP's names)
bytes      {"$bytes": "<base64>"}   (an object with exactly that one key is always bytes)
kinds      protocol, unknown_tool, invalid_arguments, denied, tool_error, timeout, cancelled,
           too_large, budget_exceeded
```

- **The id.** The guest numbers its frames, and the host echoes the number. Because the door is synchronous, ids match nothing today. They exist for the transcript, for `batch`, and for a later submit-and-collect, which Monty's `call_id` and futures show the use of (finding 2).
- **The version.**
  - `v` is in every frame. An unknown version is a `protocol` error naming the versions the host serves (EXECUTED).
  - New fields may be added within a version only if a peer may ignore them. A field the peer must act on bumps `v`, which is Monty's rule (`monty.proto:13-23`).
  - The wheel carries matching artifacts, so the two sides agree there. Other embedders read the published format.
- **Why JSON and not protobuf or CBOR** (INFERRED):
  - The guest has `json` with its C accelerator (EXECUTED: `_json` is builtin).
  - JSON is what every tool schema and MCP already speak.
  - It needs no new dependency on either side.
  - Base64 costs a third more on binary data, which the response cap bounds.
- **Why not MCP's JSON-RPC itself** (INFERRED):
  - MCP's results are content blocks written for a model to read. Agent code wants a value.
  - MCP also brings sessions, notifications and capabilities that a one-call door has no use for.
  - The descriptor uses MCP's names, so mapping a tool is one to one. Only the envelope is ours.
- **What the runner validates on every frame:**
  1. the size, against the request cap;
  2. that it is JSON, and an object;
  3. the version;
  4. the operation;
  5. the tool's name, against the offered set;
  6. the call count, against the cap;
  7. the arguments, against the tool's input schema;
  8. the gate;
  9. the result, which must be JSON-able and within the response cap.

  It does all of this with the host's own counters. The guest supplies nothing the host trusts.
- **What the schema check covers.**
  - The runner's validator implements a stated subset of JSON Schema: `type`, `enum`, `const`, `properties`, `required`, `additionalProperties`, `items`, `anyOf`, `oneOf`, local `$ref`, and the numeric and length bounds. There is no coercion.
  - A tool whose schema uses keywords outside that subset is refused at registration, unless the embedder states that the tool validates itself. LangChain's pydantic tools and MCP servers validate their own inputs. That is question 3.
- **Proposed defaults (§4.15)**, which the specification must justify:
  - 1,000 calls per run, as Monty's `max_suspensions`;
  - 1 MiB per request;
  - 16 MiB per response, as the output cap per stream;
  - 30 s per call, always less than the run's remaining deadline;
  - 16 calls per batch.

### Deadlines, fuel, cancel and async (question 15)

- **Host time is outside the epoch** (spec 015). So the tool host bounds every call itself, by the run's remaining deadline, and returns before the deadline passes (finding 5).
- **Fuel counts only guest instructions,** so tool time never changes `fuel_used`. A run's fuel stays exact, given the same tool answers.
- **The tool host's per-frame record** (operation, tool, outcome kind, bytes in and out; never times) is the door transcript that a replayable run needs (`2026-10-17-what-a-replayable-run-needs.md`).
- **Cancel** reaches a blocked tool through the call's event, then the guest through spec 015. That needs finding 5's fix.
- **Question 15's async host function** is this protocol's async tools and gates, awaited on the caller's loop under the call's deadline. The raw `host=` could gain the same later, through the same mechanism.

### Out of scope for version 1

- Streaming, progress, and chunked large results.
- Pausing a run for approval, and replaying it.
- Gates that rewrite arguments.
- Guest `async` tools and `asyncio.gather` over tools.
- Tool sets that change during a bounded session.
- Host objects and classes, as in Monty's `ClassInstance`.
- Bare global names: Monty's `external_lookup` (`from tools import *` gives them).
- Static type checking of the model's code before it runs: Monty's `ty`. An embedder can run a checker against `stubs()`.
- MCP resources, prompts and sampling.
- Passing raw MCP frames from the guest to a server.
- Combining `host=` and `tools=`.

## Questions for the owner

1. **Must `gate=` be given whenever `tools=` is?** *Recommended: yes*, with `allow_all` as the explicit "every call allowed". §4.4 says "gated by the embedder on every call", and §4.15 says no channel opens without an explicit argument. Passing `tools=` is explicit, but a forgotten gate is the likeliest mistake.
2. **The guest module's name: `tools`?** *Recommended: `tools`.* It is what Monty's docs and proposal A use, and what a model guesses. It goes in the stdlib zip, so an embedder's own `tools` package on an importable grant (question 16) would be shadowed.
3. **A tool whose schema the runner cannot fully check:** refuse it unless the embedder says the tool validates itself, or accept it and check only the subset? *Recommended: refuse unless stated*, which is safe by default.
4. **Ship `from_langchain` and `from_mcp` in the wheel, or as README recipes?** Both are duck-typed and add no dependency. Proposal A's item 7 put integrations outside this repository. These two are adapters of a format, not integrations with a framework. *Recommended: in the wheel.*

## Where it stopped

- `from_mcp` was not built or run. The mapping is READ from the schema only.
- The validator in the prototype covers less than the subset proposed above: it has no `$ref`, `oneOf`, bounds or `const`.
- `batch` was not prototyped.
- The prototype's descriptors use `input_schema`, not MCP's `inputSchema`.
- Finding 5's fix was not tried.
- Nothing was measured for speed. One door frame's cost is still unmeasured, as the agent-runtime memo §3.1 noted.

## One line

Give the embedder a `@tool` decorator, LangChain and MCP adapters, and a required gate. Give the model's code `import tools` with real signatures. Between them, carry versioned JSON frames that the host validates, gates, bounds and counts on every call. It runs on today's door unchanged, once the runner names a cancel that lands during a door call.
