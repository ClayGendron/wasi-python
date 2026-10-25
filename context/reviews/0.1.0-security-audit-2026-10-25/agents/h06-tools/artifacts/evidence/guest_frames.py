"""End to end: a guest sends crafted frames through the door (`_host.call`) to tools offered by
wasi_python.run(tools=...), and the host records what the gate and each handler received."""
import functools, json, sys
import wasi_python
from wasi_python.tools import tool

seen = []

class Account:
    """A tool class whose construction binds role through a partialmethod."""
    def _init(self, q, role="user"):
        seen.append(("Account handler", {"q": q, "role": role}))
        self.result = {"q": q, "role": role}
    __init__ = functools.partialmethod(_init, role="viewer")

def account(**kw):  # not used: the class itself is the tool
    raise AssertionError

acct = tool(Account, name="account", input_schema={"type": "object"})

def orders(q, user_id=None):
    seen.append(("orders handler", {"q": q, "user_id": user_id}))
    return {"user_id": user_id}
part = tool(functools.partial(orders, user_id=42), name="orders", input_schema={"type": "object"})

@tool
def lookup(code: str, year: int = 2026) -> dict:
    """Look up."""
    seen.append(("lookup handler", {"code": code, "year": year}))
    return {"code": code, "year": year}

def gate(call):
    seen.append(("gate", call.tool.name, dict(call.arguments)))
    return None

prog = r'''
import _host, json
def send(raw):
    ans = json.loads(_host.call(raw))
    print(json.dumps({"sent": raw.decode(), "ok": ans.get("ok"), "error": ans.get("error"), "value": ans.get("value")}))
send(b'{"v":1,"id":1,"op":"call","tool":"account","args":{"q":"x","role":"admin"}}')
send(b'{"v":1,"id":2,"op":"call","tool":"orders","args":{"q":"x","user_id":1}}')
send(b'{"v":1,"id":3,"op":"call","tool":"orders","args":{"q":"x"}}')
send(b'{"v":1,"id":4,"op":"call","tool":"lookup","args":{"code":"E","admin":true}}')
send(b'{"v":1,"id":5,"op":"call","tool":"lookup","args":{"code":"a","code":"b"}}')
send(b'{"v":1,"id":6,"op":"call","tool":"lookup","args":{"code":"E","year":1.0}}')
send(b'{"v":1,"id":7,"op":"call","tool":"lookup","args":{"code":"E"}}')
'''
done = wasi_python.run(["-c", prog], tools=[acct, part, lookup], gate=gate, deadline_s=60)
print(json.dumps({
    "exit": done.exit_code if hasattr(done, "exit_code") else None,
    "guest_stdout": done.stdout.decode(errors="replace").splitlines(),
    "guest_stderr_tail": done.stderr.decode(errors="replace")[-600:],
    "host_seen": seen,
    "record": [(o.seq, o.tool, o.outcome, o.message, o.fault) for o in done.tools.outcomes],
}, indent=1, default=repr))
