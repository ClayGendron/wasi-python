"""Host-side matrix: for each schema shape the registry accepts, send crafted frames to the
frame host (admit, then the frame) under the real bound (_Bounded), and compare the gate's
copy of the arguments with what the handler receives. Sync and async tools and gates."""
import asyncio, functools, json, sys, threading
from wasi_python.tools import tool
from wasi_python import _tool_host as th

seen = {}

def rec(label):
    def handler(**kw):
        seen.setdefault(label, []).append(("handler", dict(kw)))
        return {"got": sorted(kw)}
    return handler

def frame(name, args, fid=1):
    return json.dumps({"v": 1, "id": fid, "op": "call", "tool": name, "args": args}).encode()

def gate(call):
    seen.setdefault(call.tool.name, []).append(("gate", dict(call.arguments)))
    return None

async def agate(call):
    await asyncio.sleep(0)
    seen.setdefault(call.tool.name, []).append(("gate", dict(call.arguments)))
    return True

def host(tools, g):
    bound = th._Bounded(tick_s=0.01)
    return th._ToolHost(tools, gate=g, invoke=bound, max_calls=None)

def send(h, raw):
    early = h.admit(len(raw))
    if early is not None:
        return json.loads(early)
    return json.loads(h(raw))

out = []
def case(label, tools, name, args, raw=None, g=gate):
    seen.clear()
    h = host(tools, g)
    ans = send(h, raw if raw is not None else frame(name, args))
    out.append({"case": label, "sent": args if raw is None else raw.decode(),
                "answer": {k: ans[k] for k in ("ok", "value", "error") if k in ans},
                "seen": seen.get(name, [])})
    h.close()

# 1 derived
@tool
def derived(code: str, year: int = 2026) -> dict:
    return rec("derived")(code=code, year=year)
case("derived: valid", [derived], "derived", {"code": "E"})
case("derived: extra key refused", [derived], "derived", {"code": "E", "admin": True})
case("derived: bool for int refused", [derived], "derived", {"code": "E", "year": True})

# 2 explicit closed (properties, no additionalProperties)
closed = tool(rec("closed"), name="closed", input_schema={"type": "object", "properties": {"q": {"type": "string"}}})
case("explicit closed: extra refused", [closed], "closed", {"q": "x", "role": "admin"})

# 3 explicit open (no properties) with **kwargs
opn = tool(rec("opn"), name="opn", input_schema={"type": "object"})
case("explicit open: any key passes", [opn], "opn", {"anything": 1, "__class__": 2})

# 4 partial with fixed keyword, open schema
def impl(q, user_id=None, **kw):
    seen.setdefault("part", []).append(("handler", {"q": q, "user_id": user_id, **kw}))
    return {"user_id": user_id}
part = tool(functools.partial(impl, user_id=42), name="part", input_schema={"type": "object"})
case("partial+open: fixed keyword refused", [part], "part", {"q": "x", "user_id": 1})
case("partial+open: allowed", [part], "part", {"q": "x"})

# 5 partial with fixed keyword, root $ref into $defs naming the fixed keyword
schema_ref = {"type": "object", "$ref": "#/$defs/A",
              "$defs": {"A": {"type": "object", "properties": {"q": {"type": "string"}, "user_id": {"type": "integer"}}}}}
part_ref = tool(functools.partial(impl, user_id=42), name="part_ref", input_schema=schema_ref)
case("partial+$ref naming fixed: refused at frame", [part_ref], "part_ref", {"q": "x", "user_id": 1})

# 6 additionalProperties true with fixed
part_ap = tool(functools.partial(impl, user_id=42), name="part_ap", input_schema={"type": "object", "properties": {"q": {"type": "string"}}, "additionalProperties": True})
case("partial+additionalProperties true: fixed refused", [part_ap], "part_ap", {"q": "x", "user_id": 1})

# 7 bound method (self)
class Svc:
    def __init__(self): self.owner = "embedder"
    def m(self, q: str) -> dict:
        seen.setdefault("m", []).append(("handler", {"q": q, "self.owner": self.owner}))
        return {"q": q}
s = Svc()
bm = tool(s.m)
case("bound method: self not in schema", [bm], "m", {"q": "x"})
case("bound method: self refused", [bm], "m", {"q": "x", "self": "guest"})
print("bound method schema:", json.dumps(bm.input_schema), file=sys.stderr)

# 8 bound method with open schema, guest sends self
bmo = tool(s.m, name="mo", input_schema={"type": "object"})
case("bound method + open: self -> TypeError, internal error", [bmo], "mo", {"q": "x", "self": "guest"})

# 9 class whose __init__ is a partialmethod binding a keyword, open schema
class Acct:
    def _init(self, q, role="user"):
        seen.setdefault("Acct", []).append(("handler", {"q": q, "role": role}))
    __init__ = functools.partialmethod(_init, role="viewer")
try:
    acct = tool(Acct, name="Acct", input_schema={"type": "object"})
    print("Acct _fixed:", sorted(acct._fixed), file=sys.stderr)
    def acct_fn(**kw):
        Acct(**kw)
        return None
    case("class with partialmethod __init__ + open schema: role override", [acct], "Acct", {"q": "x", "role": "admin"})
    case("class with partialmethod __init__ + open schema: no role", [acct], "Acct", {"q": "x"})
except Exception as e:
    out.append({"case": "class partialmethod", "tool() raised": repr(e)})

# 10 dunder / reserved names
try:
    tool(rec("kw"), name="kw", input_schema={"type": "object", "properties": {"from": {}}})
    out.append({"case": "keyword property", "result": "accepted"})
except Exception as e:
    out.append({"case": "keyword property", "result": repr(e)})
dund = tool(rec("dund"), name="dund", input_schema={"type": "object", "properties": {"__dict__": {"type": "integer"}}})
case("dunder property passes as a kwarg", [dund], "dund", {"__dict__": 1})

# 11 duplicate keys
case("duplicate key refused", [derived], "derived", None, raw=b'{"v":1,"id":1,"op":"call","tool":"derived","args":{"code":"a","code":"b"}}')
case("escaped duplicate key refused", [derived], "derived", None, raw=b'{"v":1,"id":1,"op":"call","tool":"derived","args":{"code":"a","\\u0063ode":"b"}}')

# 12 async tool and async gate, same shapes
@tool
async def aderived(code: str, year: int = 2026) -> dict:
    await asyncio.sleep(0)
    seen.setdefault("aderived", []).append(("handler", {"code": code, "year": year}))
    return {"code": code}
case("async tool + async gate: valid", [aderived], "aderived", {"code": "E"}, g=agate)
case("async tool + async gate: extra refused", [aderived], "aderived", {"code": "E", "x": 1}, g=agate)
case("sync tool + async gate: valid", [derived], "derived", {"code": "E"}, g=agate)

# 13 gate verdicts: fail closed
for label, g in [("gate returns 0", lambda c: 0), ("gate returns 'yes'", lambda c: "yes"),
                 ("gate raises ValueError", lambda c: (_ for _ in ()).throw(ValueError("x"))),
                 ("gate returns False", lambda c: False)]:
    case(label, [derived], "derived", {"code": "E"}, g=g)

# 14 gate mutates its copy; handler unaffected
def mut(call):
    call.arguments["code"] = "MUTATED"
    call.arguments["admin"] = True
case("gate mutates its copy", [derived], "derived", {"code": "E"}, g=mut)

# 15 bytes
@tool
def b(data: bytes) -> int:
    seen.setdefault("b", []).append(("handler", {"type": type(data).__name__, "len": len(data)}))
    return len(data)
case("bytes accepted where declared", [b], "b", {"data": {"$bytes": "AAEC"}})
case("str refused where bytes declared", [b], "b", {"data": "AAEC"})
case("bytes refused into an Any (open) schema", [opn], "opn", {"x": {"$bytes": "AAEC"}})

json.dump(out, sys.stdout, indent=1, default=repr)
print()
print("threads alive at end:", threading.active_count(), file=sys.stderr)
