"""Drive the prototype protocol through the real door of the built artifact set.

Run from the repository root: uv run python -I context/research/2026-10-17-a-tool-protocol-over-the-door/prototype_run.py
(add `--with langchain-core==1.6.12` for the LangChain scenario). Each scenario prints the
guest's output, the run's outcome, and the host's counts: frames, calls, and each frame's
outcome kind. Nothing here asserts on time; the timeouts only choose which outcome happens.
"""

import asyncio
import pathlib
import sys
import threading
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from tool_host import Denied, ToolError, ToolHost, allow_all, from_langchain, stubs, tool  # noqa: E402

from wasi_python import run  # noqa: E402

PRELUDE = (
    "import sys, types\n"
    "_m = types.ModuleType('tools')\n"
    f"exec(compile({(HERE / 'guest_tools.py').read_text()!r}, 'tools.py', 'exec'), _m.__dict__)\n"
    "sys.modules['tools'] = _m\n"
    "del _m\n"
)


@tool(read_only=True)
def lookup_region(code: str, year: int = 2026) -> dict:
    """Look up a sales region by its code.

    Args:
        code: The region code, such as "EMEA".
        year: The fiscal year.
    """
    return {"code": code, "year": year, "name": {"EMEA": "Europe"}.get(code, "?")}


@tool(read_only=True)
def sales(region: str) -> list:
    """Quarterly sales rows for a region."""
    return [{"region": region, "quarter": q, "revenue": r} for q, r in (("Q1", 10), ("Q2", 7), ("Q3", 12))]


@tool(destructive=True)
def delete_report(report_id: str) -> str:
    """Delete a saved report."""
    return "deleted"


@tool
def secret_fault(n: int) -> int:
    """A tool with a bug that would leak a host path."""
    raise KeyError("/Users/me/.ssh/id_rsa")


@tool
def refuse(n: int) -> int:
    """A tool that fails on purpose, with a message for the model."""
    raise ToolError(f"no record {n}; try a number below 100")


@tool(timeout_s=0.2)
def slow(n: int) -> int:
    """Blocks longer than its timeout."""
    time.sleep(5)
    return n


@tool
async def fetch(url: str) -> str:
    """Fetch a page (an async tool)."""
    await asyncio.sleep(0)
    return f"<html>{url}</html>"


@tool
def chart(n: int) -> bytes:
    """A PNG's first bytes."""
    return b"\x89PNG\r\n\x1a\n" + bytes([n])


@tool
def big(n: int) -> str:
    """A result larger than the response cap."""
    return "x" * n


@tool
def block(n: int) -> int:
    """Blocks until released (the cancel scenario)."""
    started.set()
    release.wait(30)
    return n


started, release = threading.Event(), threading.Event()
ALL = [lookup_region, sales, delete_report, secret_fault, refuse, slow, fetch, chart, big, block]


def policy(call):
    """The embedder's gate: read-only tools pass; anything destructive is refused."""
    if call.tool.annotations.get("destructive"):
        raise Denied(f"{call.tool.name} needs a person's approval")


def scenario(label, program, tools=ALL, gate=policy, **host_kw):
    run_kw = host_kw.pop("run_kw", {})
    host = ToolHost(tools, gate=gate, deadline_s=60, **host_kw) if tools is not None else None
    done = run(["-"], stdin=(PRELUDE + program).encode(), host=host, **{"deadline_s": 60, **run_kw})
    print(f"=== {label}")
    out = done.stdout.decode().rstrip()
    print(out if out else "(no stdout)")
    if done.exit_code != 0:
        print("stderr tail:", done.stderr.decode().strip().splitlines()[-1:] if done.stderr else "")
    if host is None:
        print(f"exit_code={done.exit_code} trapped={done.trapped!r} (no host bound)")
        return host, done
    print(f"exit_code={done.exit_code} trapped={done.trapped!r} frames={host.frames} calls={host.calls}")
    print("record:", host.record)
    if host.faults:
        print("faults kept for the embedder:", [repr(f) for f in host.faults])
    return host, done


scenario("discovery: one frame at import, real signatures and docstrings", """
import inspect, tools
print(tools.__all__)
print(inspect.signature(tools.lookup_region))
print(tools.lookup_region.__doc__)
print(tools.describe()[2]["annotations"])
""")

scenario("a call, and pandas on the result", """
import tools, pandas as pd
print(tools.lookup_region("EMEA"))
df = pd.DataFrame(tools.sales(region="EMEA"))
print(df.revenue.diff().idxmin(), df.loc[df.revenue.diff().idxmin(), "quarter"])
""")

scenario("arguments: the guest's binding, then the host's validation of a forged frame", """
import tools, _host, json
for bad in (lambda: tools.lookup_region(), lambda: tools.lookup_region(code=5),
            lambda: tools.call("lookup_region", code="EMEA", colour="red"),
            lambda: tools.call("lookup_region", code="EMEA", year="7")):
    try:
        bad()
    except tools.ToolArgumentError as e:
        print(type(e).__name__, "|", e)
raw = _host.call(json.dumps({"v": 1, "id": 99, "op": "call", "tool": "lookup_region",
                             "args": {"code": ["EMEA"]}}).encode())
print("forged:", raw.decode())
print("old protocol:", _host.call(b'{"v": 0, "id": 1, "op": "list"}').decode())
print("not JSON:", _host.call(b"\\xff\\x00").decode())
""")

scenario("the gate refuses; a tool error carries its message; a fault carries none", """
import tools
for f in (lambda: tools.delete_report("r1"), lambda: tools.refuse(7), lambda: tools.secret_fault(1)):
    try:
        f()
    except PermissionError as e:
        print("PermissionError:", type(e).__name__, "|", e)
    except tools.ToolError as e:
        print(type(e).__name__, e.kind, "|", e)
""")

scenario("timeout: a slow tool ends the call, not the run", """
import tools
try:
    tools.slow(1)
except TimeoutError as e:
    print(type(e).__name__, "|", e)
print("guest continues:", tools.lookup_region("EMEA")["name"])
""")

scenario("an async tool, and bytes both ways", """
import tools
print(tools.fetch("https://example.org"))
png = tools.chart(3)
print(type(png).__name__, png[:4], len(png))
""")

scenario("caps: calls per run and bytes per response", """
import tools
try:
    tools.big(2_000_000)
except tools.ToolResultTooLarge as e:
    print("too large |", e)
n = 0
try:
    while True:
        tools.lookup_region("EMEA"); n += 1
except tools.ToolBudgetExceeded as e:
    print("calls before the cap:", n, "|", e)
""", max_calls=4, response_bytes=1 << 20)

scenario("no tools passed: the import fails cleanly", """
try:
    import tools
except Exception as e:
    print(type(e).__name__, "|", e)
""", tools=None)

scenario("an empty tool list: the module imports with nothing in it", """
import tools
print(tools.__all__)
try:
    tools.anything
except AttributeError as e:
    print("AttributeError |", e)
""", tools=[], gate=allow_all)

# cancel while a tool blocks: the host sees the run's event, answers "cancelled", and the
# runner's own cancel (spec 015) ends the guest when the door returns.
ev = threading.Event()
threading.Thread(target=lambda: (started.wait(30), ev.set()), daemon=True).start()
host, done = scenario("cancel while a tool blocks", """
import tools
try:
    tools.block(1)
except tools.ToolError as e:
    print("guest saw:", e.kind)
while True:
    pass
""", cancel=ev, run_kw={"cancel": ev, "deadline_s": None})
release.set()

print("=== stubs for a prompt (host side)")
print(stubs([lookup_region, sales, fetch]))

try:
    from langchain_core.tools import ToolException
    from langchain_core.tools import tool as lc_tool
except ImportError:
    print("=== LangChain adapter: skipped (run with --with langchain-core)")
else:

    @lc_tool(parse_docstring=True)
    def weather(city: str, units: str = "c") -> dict:
        """Current weather for a city.

        Args:
            city: The city name.
            units: "c" or "f".
        """
        if city == "Atlantis":
            raise ToolException("no such city")
        return {"city": city, "temp": 21.5, "units": units}

    scenario("LangChain @tool through the adapter", """
import inspect, tools
print(inspect.signature(tools.weather))
print(tools.weather("Paris"))
try:
    tools.weather("Atlantis")
except tools.ToolError as e:
    print(type(e).__name__, "|", e)
""", tools=[from_langchain(weather)], gate=allow_all)
