"""r03: independent re-check of class-constructor partials as tools, plus the record's fix sketch."""
import functools, inspect, json, sys
import wasi_python
from wasi_python import tools as T
from wasi_python.tools import tool

seen = []
out = {"python": sys.version.split()[0]}

class PM(dict):
    def _init(self, q, role="user"):
        seen.append(("PM ctor", role)); dict.__init__(self, q=q, role=role)
    __init__ = functools.partialmethod(_init, role="viewer")

def _initp(self, q, role="user"):
    seen.append(("P ctor", role)); dict.__init__(self, q=q, role=role)
class P(dict):
    __init__ = functools.partial(_initp, role="viewer")

def _new(cls, q, role="user"):
    seen.append(("New ctor", role)); return {"q": q, "role": role}
class New:
    __new__ = staticmethod(functools.partial(_new, role="viewer"))

class Sub(PM):  # inherited partialmethod __init__
    pass

class Meta(type):
    def __call__(cls, *a, **k):
        return super().__call__(*a, **k)
class MetaPM(dict, metaclass=Meta):
    def _init(self, q, role="user"):
        seen.append(("MetaPM ctor", role)); dict.__init__(self, q=q, role=role)
    __init__ = functools.partialmethod(_init, role="viewer")

def ctrl(q, user_id=None):
    seen.append(("ctrl", user_id)); return {"user_id": user_id}

OPEN = {"type": "object"}
NAMING = {"type": "object", "properties": {"q": {"type": "string"}, "role": {"type": "string"}}}
reg, tools = {}, []
for nm, c in (("pm", PM), ("p", P), ("new", New), ("sub", Sub), ("meta", MetaPM)):
    t = tool(c, name=nm, input_schema=OPEN); tools.append(t)
    r = {"fixed": sorted(t._fixed)}
    try:
        r["sig"] = str(inspect.signature(c))
    except Exception as e:
        r["sig"] = repr(e)
    try:
        r["naming"] = "accepted fixed=%s" % sorted(tool(c, name=nm + "_n", input_schema=NAMING)._fixed)
    except Exception as e:
        r["naming"] = "refused " + type(e).__name__
    try:
        tool(c, name=nm + "_d"); r["derived"] = "accepted"
    except Exception as e:
        r["derived"] = "refused: " + str(e)[:80]
    reg[nm] = r
tools.append(tool(functools.partial(ctrl, user_id=42), name="ctrl", input_schema=OPEN))
try:
    tool(functools.partial(ctrl, user_id=42), name="ctrl_n", input_schema={"type": "object", "properties": {"user_id": {}}})
    reg["ctrl_naming"] = "accepted"
except Exception as e:
    reg["ctrl_naming"] = "refused " + type(e).__name__
out["registration"] = reg

# The record's fixed_code, applied as a wrapper in this process only.
orig = T._bound_keywords
def fixed_bk(name, fn):
    found = set()
    if isinstance(fn, type):
        for attr in ("__new__", "__init__"):
            member = inspect.getattr_static(fn, attr, None)
            member = getattr(member, "__func__", member)
            if isinstance(member, functools.partialmethod):
                found.update(member.keywords)
                member = member.func
            if isinstance(member, functools.partial) or getattr(member, "__wrapped__", None) is not None:
                found.update(orig(name, member))
    return frozenset(found | orig(name, fn))
class NestPM(dict):
    def _init(self, q, role="u", org="o"):
        dict.__init__(self)
    __init__ = functools.partialmethod(functools.partial(_init, org="acme"), role="viewer")
class CM(dict):
    __init__ = classmethod(functools.partial(lambda cls, q, role="u": None, role="viewer"))
out["fix_sketch"] = {n: sorted(fixed_bk(n, c)) for n, c in (("pm", PM), ("p", P), ("new", New), ("sub", Sub), ("meta", MetaPM), ("nestpm", NestPM), ("cm", CM))}

def gate(call):
    seen.append(("gate", call.tool.name, dict(call.arguments))); return None

prog = r'''
import _host, json
for i, (t, a) in enumerate([("pm", {"q":"x","role":"admin"}), ("p", {"q":"x","role":"admin"}), ("new", {"q":"x","role":"admin"}), ("sub", {"q":"x","role":"admin"}), ("meta", {"q":"x","role":"admin"}), ("pm", {"q":"x"}), ("ctrl", {"q":"x","user_id":1})]):
    ans = json.loads(_host.call(json.dumps({"v":1,"id":i+1,"op":"call","tool":t,"args":a}).encode()))
    print(json.dumps({"tool": t, "ok": ans.get("ok"), "error": ans.get("error"), "value": ans.get("value")}))
'''
done = wasi_python.run(["-c", prog], tools=tools, gate=gate, deadline_s=60)
out["guest"] = [json.loads(l) for l in done.stdout.decode(errors="replace").splitlines() if l.startswith("{")]
out["stderr_tail"] = done.stderr.decode(errors="replace")[-300:]
out["host_seen"] = seen
out["outcomes"] = [(o.tool, o.outcome) for o in done.tools.outcomes]
print(json.dumps(out, indent=1, default=repr))
