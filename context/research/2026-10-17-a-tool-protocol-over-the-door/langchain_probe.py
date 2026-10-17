"""Observe LangChain's tool API: the schema it derives, how it is called, how it fails.

Run: uv run --isolated --no-project --with langchain-core python -I langchain_probe.py
Prints one labelled line or block per probe; the output is saved beside this file.
"""

import asyncio
import json

from langchain_core.tools import StructuredTool, ToolException, tool
from langchain_core.utils.function_calling import convert_to_openai_tool


@tool(parse_docstring=True)
def lookup_region(code: str, year: int = 2026) -> dict:
    """Look up a sales region by its code.

    Args:
        code: The region code, such as "EMEA".
        year: The fiscal year.
    """
    if code == "XX":
        raise ToolException(f"no region {code!r}")
    return {"code": code, "year": year, "name": "Europe"}


@tool
async def fetch_page(url: str) -> str:
    """Fetch a page (async)."""
    await asyncio.sleep(0)
    return f"<html>{url}</html>"


def show(label, value):
    print(f"--- {label}")
    print(value if isinstance(value, str) else json.dumps(value, indent=1, default=repr))


show("type and name", f"{type(lookup_region).__name__} {lookup_region.name!r}")
show("description", lookup_region.description)
show("tool_call_schema json", lookup_region.tool_call_schema.model_json_schema())
show("openai tool", convert_to_openai_tool(lookup_region))
show("openai tool strict", convert_to_openai_tool(lookup_region, strict=True))

# 1. plain dict input returns the raw value
show("invoke(dict)", lookup_region.invoke({"code": "EMEA"}))
# 2. a ToolCall input returns a ToolMessage
msg = lookup_region.invoke({"type": "tool_call", "id": "c1", "name": "lookup_region", "args": {"code": "EMEA"}})
show("invoke(ToolCall) type", type(msg).__name__)
show("invoke(ToolCall) message", msg.model_dump(include={"content", "tool_call_id", "status", "name", "artifact"}))
# 3. coercion: a string "7" for an int
show("coercion year='7'", lookup_region.invoke({"code": "EMEA", "year": "7"}))
# 4. a wrong type, default handle_validation_error=False
try:
    lookup_region.invoke({"code": "EMEA", "year": "seven"})
except Exception as e:  # noqa: BLE001
    show("bad arg raises", f"{type(e).__name__}: {str(e).splitlines()[0]}")
# 5. an unknown argument
show("extra arg", lookup_region.invoke({"code": "EMEA", "colour": "red"}))
# 6. ToolException with default handle_tool_error=False
try:
    lookup_region.invoke({"code": "XX"})
except ToolException as e:
    show("ToolException raises by default", repr(e))
# 7. handled: becomes a ToolMessage with status=error
lookup_region.handle_tool_error = True
msg = lookup_region.invoke({"type": "tool_call", "id": "c2", "name": "lookup_region", "args": {"code": "XX"}})
show("handled ToolException", msg.model_dump(include={"content", "status"}))
lookup_region.handle_validation_error = True
msg = lookup_region.invoke({"type": "tool_call", "id": "c3", "name": "lookup_region", "args": {"year": "x"}})
show("handled validation error", msg.model_dump(include={"content", "status"}))
# 8. a plain exception is never handled
@tool
def boom(x: int) -> int:
    """Always fails."""
    raise RuntimeError("secret host path /Users/me/key")


boom.handle_tool_error = True
try:
    boom.invoke({"x": 1})
except RuntimeError as e:
    show("plain exception propagates even when handled", repr(e))
# 9. async: ainvoke of async tool; invoke of an async-only tool; ainvoke of a sync tool
show("ainvoke async tool", asyncio.run(fetch_page.ainvoke({"url": "u"})))
try:
    fetch_page.invoke({"url": "u"})
except Exception as e:  # noqa: BLE001
    show("invoke of async-only tool", f"{type(e).__name__}: {e}")
show("ainvoke of sync tool", asyncio.run(lookup_region.ainvoke({"code": "EMEA"})))
# 10. content_and_artifact
@tool(response_format="content_and_artifact")
def chart(n: int) -> tuple[str, bytes]:
    """Draw a chart."""
    return f"a chart of {n} points", b"\x89PNG..."


m = chart.invoke({"type": "tool_call", "id": "c4", "name": "chart", "args": {"n": 3}})
show("content_and_artifact", {"content": m.content, "artifact": repr(m.artifact)})
# 11. StructuredTool.from_function with both sync and async
st = StructuredTool.from_function(func=lambda q: q.upper(), coroutine=None, name="up", description="Upper.")
show("from_function lambda schema", st.tool_call_schema.model_json_schema())
# 12. names LangChain allows
for bad in ["my tool", "a.b", "x" * 80]:
    t = StructuredTool.from_function(func=lambda q: q, name=bad, description="d")
    show(f"name accepted {bad[:12]!r}", t.name == bad)
