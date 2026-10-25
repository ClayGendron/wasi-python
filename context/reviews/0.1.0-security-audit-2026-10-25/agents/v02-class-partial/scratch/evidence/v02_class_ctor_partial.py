"""Verifier v02: a class tool whose constructor binds a keyword with partial/partialmethod,
against the plain-partial control, end to end through run(tools=..., gate=...)."""
import functools, inspect, json, sys
import wasi_python
from wasi_python.tools import tool

seen = []
out = {"python": sys.version.split()[0]}

class AccountPM(dict):
    """__init__ is a partialmethod binding role."""
    def _init(self, q, role="user"):
        seen.append(("AccountPM ctor", {"q": q, "role": role}))
        dict.__init__(self, q=q, role=role)
    __init__ = functools.partialmethod(_init, role="viewer")

def _initp(self, q, role="user"):
    seen.append(("AccountP ctor", {"q": q, "role": role}))
    dict.__init__(self, q=q, role=role)

class AccountP(dict):
    """__init__ is a plain functools.partial (a method descriptor on 3.14)."""
    __init__ = functools.partial(_initp, role="viewer")

def _new(cls, q, role="user"):
    seen.append(("AccountNew ctor", {"q": q, "role": role}))
    return {"q": q, "role": role}

class AccountNew:
    """__new__ is a staticmethod over a partial binding role; returns a plain dict."""
    __new__ = staticmethod(functools.partial(_new, role="viewer"))

def orders(q, user_id=None):
    seen.append(("orders handler", {"q": q, "user_id": user_id}))
    return {"user_id": user_id}

OPEN = {"type": "object"}
NAMING = {"type": "object", "properties": {"q": {"type": "string"}, "role": {"type": "string"}}, "required": ["q"]}

tools = []
reg = {}
for nm, target in (("acct_pm", AccountPM), ("acct_p", AccountP), ("acct_new", AccountNew)):
    t = tool(target, name=nm, input_schema=OPEN)
    tools.append(t)
    reg[nm] = {"signature": str(inspect.signature(target)), "fixed": sorted(t._fixed)}
    try:
        t2 = tool(target, name=nm + "_named", input_schema=NAMING)
        reg[nm]["schema_naming_role"] = "accepted, fixed=%s" % sorted(t2._fixed)
    except Exception as e:
        reg[nm]["schema_naming_role"] = "refused: %s: %s" % (type(e).__name__, e)
part = tool(functools.partial(orders, user_id=42), name="orders", input_schema=OPEN)
tools.append(part)
reg["orders"] = {"signature": str(inspect.signature(part.fn)), "fixed": sorted(part._fixed)}
try:
    tool(functools.partial(orders, user_id=42), name="orders_named",
         input_schema={"type": "object", "properties": {"q": {"type": "string"}, "user_id": {"type": "integer"}}})
    reg["orders"]["schema_naming_user_id"] = "accepted"
except Exception as e:
    reg["orders"]["schema_naming_user_id"] = "refused: %s: %s" % (type(e).__name__, e)

# Side probes: callable instance with __call__ = partialmethod, and a Python metaclass __call__.
class CallPM:
    def _c(self, q, role="user"):
        return {"q": q, "role": role}
    __call__ = functools.partialmethod(_c, role="viewer")
try:
    reg["callable_instance_call_partialmethod"] = "accepted, fixed=%s" % sorted(tool(CallPM(), name="cpm", input_schema=OPEN)._fixed)
except Exception as e:
    reg["callable_instance_call_partialmethod"] = "refused: %s: %s" % (type(e).__name__, e)

class Meta(type):
    def __call__(cls, *a, **k):
        return super().__call__(*a, **k)
class AccountMeta(dict, metaclass=Meta):
    def _init(self, q, role="user"):
        dict.__init__(self, q=q, role=role)
    __init__ = functools.partialmethod(_init, role="viewer")
try:
    tm = tool(AccountMeta, name="acct_meta", input_schema=OPEN)
    reg["metaclass_python_call"] = {"signature": str(inspect.signature(AccountMeta)), "fixed": sorted(tm._fixed)}
except Exception as e:
    reg["metaclass_python_call"] = "refused: %s: %s" % (type(e).__name__, e)

# The hunter's proposed fix, evaluated in this script only (the target is not edited).
_C_SLOTS = (type(type.__call__), type(object().__str__), type(str.join), type(len), type(dict.__dict__["fromkeys"]))
def proposed(target):
    found = set()
    if isinstance(target, type) and isinstance(type(target).__call__, _C_SLOTS):
        for attr in ("__new__", "__init__"):
            member = inspect.getattr_static(target, attr, None)
            member = getattr(member, "__func__", member)
            if isinstance(member, functools.partialmethod):
                found.update(member.keywords)
            elif isinstance(member, functools.partial):
                found.update(member.keywords)
    return sorted(found)
out["proposed_fix_fixed"] = {n: proposed(c) for n, c in (("AccountPM", AccountPM), ("AccountP", AccountP), ("AccountNew", AccountNew), ("AccountMeta", AccountMeta))}
out["registration"] = reg

def gate(call):
    seen.append(("gate", call.tool.name, dict(call.arguments)))
    return None

prog = r'''
import _host, json
def send(raw):
    ans = json.loads(_host.call(raw))
    print(json.dumps({"tool": json.loads(raw)["tool"], "ok": ans.get("ok"), "error": ans.get("error"), "value": ans.get("value")}))
send(b'{"v":1,"id":1,"op":"call","tool":"acct_pm","args":{"q":"x","role":"admin"}}')
send(b'{"v":1,"id":2,"op":"call","tool":"acct_p","args":{"q":"x","role":"admin"}}')
send(b'{"v":1,"id":3,"op":"call","tool":"acct_new","args":{"q":"x","role":"admin"}}')
send(b'{"v":1,"id":4,"op":"call","tool":"acct_pm","args":{"q":"x"}}')
send(b'{"v":1,"id":5,"op":"call","tool":"orders","args":{"q":"x","user_id":1}}')
send(b'{"v":1,"id":6,"op":"call","tool":"orders","args":{"q":"x"}}')
'''
done = wasi_python.run(["-c", prog], tools=tools, gate=gate, deadline_s=60)
out["guest_answers"] = [json.loads(l) for l in done.stdout.decode(errors="replace").splitlines() if l.startswith("{")]
out["guest_stderr_tail"] = done.stderr.decode(errors="replace")[-400:]
out["host_seen"] = seen
out["record"] = [(o.seq, o.tool, o.outcome, o.message, o.fault) for o in done.tools.outcomes]
print(json.dumps(out, indent=1, default=repr))
