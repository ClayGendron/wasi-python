"""Where a class's construction path holds a partial or a partialmethod, inspect.signature
hides the bound keyword but tool()'s bound-keyword walk stops at type.__call__ and finds none:
compare signature, _fixed, the given-schema check, and a frame sent through the frame host."""
import functools, inspect, json, sys
from wasi_python.tools import tool
from wasi_python._tool_host import _ToolHost

log = []

class ViaPartialmethod:
    def _init(self, q, role="user"):
        log.append(("ViaPartialmethod", q, role))
    __init__ = functools.partialmethod(_init, role="viewer")

def _init2(self, q, role="user"):
    log.append(("ViaPartial", q, role))

class ViaPartial:  # functools.partial is a method descriptor from Python 3.14
    __init__ = functools.partial(_init2, role="viewer")

def impl(q, role="user"):
    log.append(("plain partial", q, role))
plain = functools.partial(impl, role="viewer")

out = {"python": sys.version.split()[0]}
for label, fn in [("ViaPartialmethod", ViaPartialmethod), ("ViaPartial", ViaPartial), ("plain partial", plain)]:
    r = {}
    try:
        r["signature"] = str(inspect.signature(fn))
    except Exception as e:
        r["signature"] = repr(e)
    # a given schema that names the bound keyword: tool() refuses it for a plain partial
    listed = {"type": "object", "properties": {"q": {"type": "string"}, "role": {"type": "string"}}}
    try:
        t = tool(fn, name="t", input_schema=listed)
        r["schema naming role"] = "accepted; _fixed=%s" % sorted(t._fixed)
    except Exception as e:
        r["schema naming role"] = "refused: " + repr(e)[:160]
    t = tool(fn, name="t", input_schema={"type": "object"})
    r["_fixed (open schema)"] = sorted(t._fixed)
    log.clear()
    host = _ToolHost([t])
    frame = {"v": 1, "id": 1, "op": "call", "tool": "t", "args": {"q": "x", "role": "admin"}}
    ans = json.loads(host(json.dumps(frame).encode()))
    r["frame role=admin answer"] = ans.get("error", ans.get("value"))
    r["handler saw"] = list(log)
    r["record fault"] = host.record.outcomes[-1].fault
    out[label] = r
json.dump(out, sys.stdout, indent=1)
print()
