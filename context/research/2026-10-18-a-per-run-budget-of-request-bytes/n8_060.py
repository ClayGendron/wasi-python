"""N8 of the 0.1.0a4 security review: a __call__ chain two deep, with hand-copied annotations,
publishes a partial's bound keywords. Reproduce it on main, then try a prototype walk."""

import functools
import json
import sys
import types
import warnings

from wasi_python import tools as T
from wasi_python.tools import tool

warnings.simplefilter("ignore", FutureWarning)  # 3.13: partial as a class attribute


def orders(user_id: int, api_key: str, limit: int = 10) -> list[str]:
    """Orders."""
    return [f"{user_id}:{api_key[:6]}:{limit}"]


SECRET = "sk-live-N8"


def depth(n: int):
    """A callable object whose __call__ chain is n objects deep, ending at a partial."""

    class Last:
        __call__ = staticmethod(functools.partial(orders, user_id=42, api_key=SECRET))

    obj = Last()
    obj.__annotations__ = dict(orders.__annotations__)
    for _ in range(n - 1):
        cls = type("Hop", (), {"__call__": obj})
        obj = cls()
        obj.__annotations__ = dict(orders.__annotations__)  # hand-copied, so hints read
    return obj


def show(label: str) -> None:
    for n in (1, 2, 3):
        try:
            t = tool(depth(n), name="my_orders")
        except TypeError as e:
            print(f"  {label} depth {n}: refused: {e}")
            continue
        props = t.descriptor()["inputSchema"]["properties"]
        leak = SECRET in json.dumps(t.descriptor())
        print(f"  {label} depth {n}: properties {sorted(props)}  secret in descriptor: {leak}")


print(sys.version.split()[0])
show("main")

_SLOTS = (
    types.WrapperDescriptorType,
    types.MethodWrapperType,
    types.MethodDescriptorType,
    types.BuiltinFunctionType,
    types.ClassMethodDescriptorType,
)


def walk(name, fn):
    """The prototype: follow type(obj).__call__ on every hop, as inspect.signature does, and stop
    where inspect stops (a C slot wrapper), within the same 64 links."""
    found = set()
    target = fn
    for _ in range(T._WRAPPER_DEPTH):
        if any(getattr(target, a, None) is not None for a in T._PARTIALMETHOD):
            raise TypeError(f"{name}: partialmethod")
        if isinstance(target, functools.partial):
            found.update(target.keywords)
            target = target.func
        elif isinstance(target, types.MethodType):
            target = target.__func__
        elif not isinstance(target, type) and getattr(target, "__wrapped__", None) is not None:
            target = target.__wrapped__
        elif not (
            T.inspect.isfunction(target) or T.inspect.isbuiltin(target) or isinstance(target, type)
        ):
            call = getattr(type(target), "__call__", None)
            if call is None or isinstance(call, _SLOTS):
                return frozenset(found)
            target = call
        else:
            return frozenset(found)
    raise TypeError(f"{name}: its wrappers nest deeper than {T._WRAPPER_DEPTH}; pass a function")


T._bound_keywords = walk
show("prototype")

# The prototype must not refuse what main accepts: ordinary callables still describe.


class Plain:
    def __call__(self, a: int) -> int:
        """Plain."""
        return a


for label, fn in (
    ("a function", orders),
    ("a callable object", Plain()),
    ("a bound method", Plain().__call__),
    ("a partial", functools.partial(orders, user_id=1, api_key="k")),
):
    t = tool(fn, name="x")
    print(f"  prototype, {label}: properties {sorted(t.descriptor()['inputSchema']['properties'])}")
for label, fn in (("operator.itemgetter(0)", __import__("operator").itemgetter(0)),):
    try:
        walk("x", fn)
        print(f"  prototype walk, {label}: no loop, ends")
    except TypeError as e:
        print(f"  prototype walk, {label}: {e}")
