"""Observe Monty's host functions: types, errors, gating, async, limits.

Run: uv run --isolated --no-project --with pydantic-monty==1.1.0 python -I monty_probe.py
Counts and outcomes only; nothing here measures time.
"""

import asyncio

from pydantic_monty import AsyncMonty, FunctionSnapshot, Monty, MontyComplete, MontyRuntimeError

seen = []


def get_temperature(city: str) -> float:
    seen.append((type(city).__name__, city))
    return 21.5


class QuotaExceeded(Exception):
    pass


def over_quota(n: int) -> int:
    raise QuotaExceeded("quota of 10 calls exceeded")


def leaky(n: int) -> int:
    raise KeyError("/Users/me/.ssh/id_rsa")


def returns_function(n: int):
    return print


def show(label, value):
    print(f"--- {label}\n{value}")


def outcome(session, code, **kw):
    try:
        return repr(session.feed_run(code, **kw))
    except MontyRuntimeError as e:
        return "MontyRuntimeError: " + e.display(format="type-msg")
    except Exception as e:  # noqa: BLE001
        return f"{type(e).__name__}: {e}"


with Monty() as pool:
    with pool.checkout() as s:
        # 1. no host-side type check: an int reaches a str-annotated host function
        show("int to a str parameter", outcome(s, "get_temperature(123)", external_lookup={"get_temperature": get_temperature}))
        show("what the host saw", seen)
        # 2. a host exception of a class Monty does not know
        show("custom host exception, uncaught", outcome(s, "over_quota(1)", external_lookup={"over_quota": over_quota}))
        show(
            "custom host exception, caught as Exception",
            outcome(s, "try:\n    over_quota(1)\nexcept Exception as e:\n    r = (type(e).__name__, str(e))\nr", external_lookup={"over_quota": over_quota}),
        )
        # 3. a host KeyError carries its message into the sandbox
        show("host KeyError message", outcome(s, "try:\n    leaky(1)\nexcept KeyError as e:\n    r = str(e)\nr", external_lookup={"leaky": leaky}))
        # 4. a host value that cannot cross
        show("host returns a builtin function", outcome(s, "f = returns_function(1)\n(type(f).__name__, repr(f))", external_lookup={"returns_function": returns_function}))
        # 5. a name the host did not offer
        show("unknown tool", outcome(s, "send_email('x')", external_lookup={"get_temperature": get_temperature}))
        # 6. what the sandbox can learn about a host function
        show("introspection", outcome(s, "(type(get_temperature).__name__, repr(get_temperature))", external_lookup={"get_temperature": get_temperature}))

    # 7. gating with feed_start: inspect each call, approve one, deny the next
    with pool.checkout() as s:
        code = (
            "a = get_temperature('London')\n"
            "try:\n    b = get_temperature(city='Paris')\n"
            "except PermissionError as e:\n    b = 'denied: ' + str(e)\n"
            "(a, b)"
        )
        snap = s.feed_start(code)
        calls = []
        while isinstance(snap, FunctionSnapshot):
            calls.append((snap.function_name, snap.args, snap.kwargs, snap.call_id))
            if snap.kwargs.get("city") == "Paris":
                snap = snap.resume({"exc_type": "PermissionError", "message": "denied by policy"})
            else:
                snap = snap.resume({"return_value": 20.0})
        show("gated calls (name, args, kwargs, call_id)", calls)
        show("gated outcome", repr(snap.output) if isinstance(snap, MontyComplete) else repr(snap))

    # 8. the suspension cap
    with pool.checkout(limits={"max_suspensions": 5}) as s:
        show(
            "max_suspensions=5, ten calls",
            outcome(s, "n = 0\nfor i in range(10):\n    get_temperature('x')\n    n += 1\nn", external_lookup={"get_temperature": get_temperature}),
        )


# 9. async host functions run concurrently under asyncio.gather in the sandbox:
# fetch('a') waits for an event that only fetch('b') sets, so a serial driver would deadlock.
async def main():
    ev = asyncio.Event()
    order = []

    async def fetch(name: str) -> str:
        order.append(f"start {name}")
        if name == "a":
            await asyncio.wait_for(ev.wait(), 30)
        else:
            ev.set()
        order.append(f"end {name}")
        return name

    async with AsyncMonty() as pool:
        async with pool.checkout() as s:
            r = await s.feed_run("import asyncio\nawait asyncio.gather(fetch('a'), fetch('b'))", external_lookup={"fetch": fetch})
    show("gather result", r)
    show("host order", order)


asyncio.run(main())
