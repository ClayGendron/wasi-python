# Offer tools to the guest

This guide shows you how to offer your own Python functions to guest code as *tools*, how to keep their authority narrow, gate their calls, and read what happened. It ends with two recipes for LangChain and MCP tools.

A tool is a host function the guest calls as if it were its own. Guest code imports the tools with `from host import tools`. Between the two sides run JSON messages called *frames*, in a versioned protocol; see [The tool protocol](../reference/tool-protocol.md).

## Offer a tool

Decorate a function with `tool` and pass it in `tools=`:

```python
from wasi_python import run
from wasi_python.tools import ToolError, tool

REGIONS = {"EMEA": {"code": "EMEA", "manager": "Ada"}}

@tool(read_only=True)
def lookup_region(code: str) -> dict:
    """Look up a sales region by its code.

    Args:
        code: The region code, such as "EMEA".
    """
    if code not in REGIONS:
        raise ToolError(f"no region {code!r}")  # the guest reads this message
    return REGIONS[code]

program = """
from host import tools
print(tools.lookup_region("EMEA")["manager"])
"""
done = run(["-c", program], tools=[lookup_region])
done.stdout                                    # b'Ada\n'
[o.outcome for o in done.tools.outcomes]       # ['ok', 'ok']: the list, then the call
```

`tool()` takes the tool's name, description and *input schema* (the JSON Schema of its arguments) from the function: its type hints, its docstring up to the first heading, and its `Args:` section. `input_schema=` gives the schema instead, as a dict or a pydantic model. A plain function in `tools=` goes through `tool()` too.

The guest's function has the same signature and docstring, so `help(tools)` works in the guest. `wasi_python.tools.stubs(tools)` renders them as Python stubs for a prompt.

`read_only`, `destructive`, `idempotent` and `open_world` are labels shown to the guest as MCP's hints. They grant nothing.

## Keep a tool's authority narrow

A tool runs with your process's authority. A `read_file(path)` tool is a filesystem, and a `sql(query)` tool is your database: the guest may call it with any arguments its schema allows. So pass capabilities, not services. Make the tools per request, each closing over that caller's authority:

```python
def tools_for(user):
    @tool
    def my_orders(limit: int = 10) -> list[dict]:
        """This user's latest orders."""
        return orders.latest(user_id=user.id, limit=min(limit, 50))

    return [my_orders]

done = run(["-c", code], tools=tools_for(request.user))
```

A `functools.partial` binds authority too:

```python
tool(partial(orders_for, user_id=user.id, api_key=KEY), name="my_orders")
```

A keyword the partial binds is fixed. It is not in the schema, so the guest never sees its value, and a frame that names it is refused. So is a keyword a `partial` or `partialmethod` binds on the `__init__` or `__new__` of a class registered as a tool. A bound value need not be JSON: you can bind a database connection.

A parameter's own default is not fixed. It is published in the schema, and the guest may pass another value. So never put authority, such as a key or a user id, in a default.

## Gate each call

`gate=` is a function called before each tool runs. It gets a `ToolCall` with `seq`, `tool`, a copy of the validated `arguments`, and `request_bytes`. `arguments` holds only what the guest sent: no defaults, and no keyword a partial binds.

- The gate allows a call by returning `None` or `True`.
- It refuses by returning `False`, or by raising `ToolDenied(message)`, whose message the guest reads as a `PermissionError`.
- A gate that raises anything else refuses too, and the record keeps its fault.

With no gate, every valid call runs: your choice of tools is then the policy.

## Report errors to the guest

Nothing the guest, a gate or a tool does makes `run` raise.

- A `ToolError` you raise crosses to the guest with its message.
- A `ToolDenied` crosses with its message.
- Any other exception crosses only as "<name> failed (internal error)". The record's `fault` keeps its type and first line, so a path in an exception never reaches the guest.

A `ToolError`'s text crosses whole, up to 4,096 characters. The guest reads every word of it. So write its message for the guest, and never raise one with a host exception's text: `raise ToolError(str(e))` for an `OSError` hands the guest a host path. Let such an exception propagate instead. It then crosses as "(internal error)", and its type and first line stay in the record's `fault`.

A result must be JSON. numpy's integers and floats are, but numpy's `bool_` is not: return `bool(df["x"].any())`, not `df["x"].any()`.

## Read the record

`done.tools` is a `ToolRecord`, or `None` for a call without `tools=`. It holds:

- `frames`, every frame counted;
- `outcomes`, the first 1,000 frames, each with `seq`, `op`, `tool`, `outcome`, `message`, `request_bytes`, `response_bytes`, `fault` and `abandoned`;
- `unlisted`, the frames counted but not listed;
- `abandoned`, every call answered while its tool ran on.

It comes back on every ending: an exit, a trap, `"deadline"` and `"cancelled"`.

## Know the limits

- **Frames.** At most `max_tool_calls` frames per call, the guest's discovery frame, which lists the tools, included. The default is 1,000; `None` means no limit.
- **Request bytes.** At most `max_tool_request_bytes` bytes of requests read per call. The default is 16 MiB; `None` means no limit. A frame that would pass it is refused unread.
- Past either, the guest gets `ToolBudgetExceeded` and runs on.
- A single request over 1 MiB is refused from its length, and an answer over 16 MiB is refused as too large.

Parsing a frame costs host CPU in proportion to its bytes, so the request budget bounds that cost. Where many untrusted guests run at once, lower both limits, and the deadline. Send bulk data through a writable mount (see [Serve files from your own code](mounts.md)), not in tool arguments.

## Bound a tool's time

Each tool call runs its gate, its tool and the encoding of its result on a new thread, in a copy of the caller's `contextvars` context. So objects bound to one thread, such as a `sqlite3` connection made with its default `check_same_thread`, or a `threading.local`, do not work inside a tool. Context variables do.

A tool call ends at the first of:

- the tool's `timeout_s`, set with `tool(timeout_s=…)`;
- 20 ms before the run's deadline;
- the run's `cancel`, or the `run_async` task's cancellation;
- Ctrl-C.

A tool with no `timeout_s`, in a run with no deadline, still has an end. It waits at most the session's lifetime, or one hour (3,600 s) when there is none, as in a plain `run`.

A timeout raises `ToolTimeout`, also a `TimeoutError`, in the guest, which runs on. Fuel counts only the guest's instructions: time spent in a tool adds none.

A sync function cannot be stopped. A tool whose call timed out runs on to its end, unseen; its result is dropped, and its outcome says `abandoned=True`, because its effect may still land. So a call the guest retries after `ToolTimeout` may act twice. One run may hold 4 abandoned tool threads. While it does, its next tool call is answered `timeout` at once. The whole process may hold 64, across every run and session. A tool call already running then may still time out, so the count can pass 64 by the tool calls running at that moment. While the process holds 64, every run's next tool call is answered `timeout` at once, until one of them returns. A tool that can hang must bound itself, for example with a timeout on its own network call.

## Write an async tool

A tool or a gate may be an `async def`, or a function that returns an awaitable. The guest still calls it synchronously; only the host side awaits. Under `run_async`, it runs on the event loop that awaits `run_async`. Under `run`, it runs on a loop of the call's own. Once started, every end of the call cancels it at its next `await`. See [Run the guest from async code](async.md#await-inside-a-tool-not-a-raw-host-function) for an example.

## Know what run refuses

`run` refuses, before any work:

- `host=` together with `tools=`: the host has one channel to the guest, so pass `host=` for a raw host function or `tools=` for the protocol;
- `gate=`, `max_tool_calls=` or `max_tool_request_bytes=` without `tools=`;
- two tools with one name;
- an async generator function as a tool or a gate;
- an `async def` as `host=`: serve it as a tool instead;
- an artifact set from before the tool protocol, with `ArtifactsMissing`.

## Recipe: a LangChain tool

These two recipes are not part of the API: the project ships no adapter. Each was run once with the versions named.

A LangChain tool (`langchain-core==1.6.12`), its input checked by its own pydantic model:

```python
from langchain_core.tools import ToolException
from wasi_python.tools import ToolError, tool

def from_langchain(lc_tool):
    def call(**args):
        try:
            return lc_tool.invoke(args)
        except ToolException as e:
            raise ToolError(str(e)) from None  # its text is meant for the caller

    return tool(call, name=lc_tool.name, description=lc_tool.description,
                input_schema=lc_tool.args_schema, validates_input=True)
```

`validates_input=True` lets schema keywords outside the protocol's subset through, unchecked, for a tool that checks its own input.

## Recipe: an MCP server's tool

An MCP server's tool, through your own client session (`mcp==2.3.0`). The session lives on your event loop, and an async tool is awaited there. The result's structured content is the value, and an error result becomes a `ToolError` with the server's text:

```python
from wasi_python import run_async
from wasi_python.tools import ToolError, tool

def from_mcp(session, listed, timeout_s=30):
    async def call(**args):
        result = await session.call_tool(listed.name, args)
        text = " ".join(c.text for c in result.content if c.type == "text")
        if result.is_error:
            raise ToolError(text)
        return result.structured_content if result.structured_content is not None else text

    return tool(call, name=listed.name, description=listed.description or "",
                input_schema=listed.input_schema, validates_input=True, timeout_s=timeout_s)

async def answer(session, code):  # session: your open mcp.Client
    tools = [from_mcp(session, t) for t in (await session.list_tools()).tools]
    return await run_async(["-c", code], tools=tools)
```

An MCP tool whose name or property names are not Python identifiers needs `name=` and a renamed schema; see [The tool protocol](../reference/tool-protocol.md).

In one line: decorate a function with `@tool`, pass it in `tools=`, and the guest calls it from `host.tools`, with each call bounded, gated if you wish, and recorded.
