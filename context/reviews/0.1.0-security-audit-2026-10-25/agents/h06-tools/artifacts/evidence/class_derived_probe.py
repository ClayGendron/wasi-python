"""Can a class with a partialmethod __init__ be described from its signature (no input_schema)?"""
import functools, json, sys
from wasi_python.tools import tool
class A:
    def _init(self, q: str, role: str = "user") -> None:
        pass
    __init__ = functools.partialmethod(_init, role="viewer")
try:
    t = tool(A, name="A")
    print(json.dumps({"derived": t.input_schema, "_fixed": sorted(t._fixed)}))
except Exception as e:
    print(json.dumps({"derived": "refused", "error": repr(e)[:300]}))
