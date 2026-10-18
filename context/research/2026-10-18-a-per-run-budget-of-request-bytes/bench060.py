"""Spec 060's benchmark facts (research only; nothing here is a check).

A: host CPU per admitted frame, by shape, the frame host alone (no guest).
B: the cost of a frame refused from its length (admit only).
C: a guest that floods 1 MiB frames through run(), at today's defaults and under a prototype
   per-run budget of request bytes (a wrapper around admit), with fuel and host CPU.
"""

import json
import statistics
import sys
import time
from typing import Any

from wasi_python import run
from wasi_python import tools as T
from wasi_python.tools import tool

CAP = T._TOOL_REQUEST_BYTES


@tool
def t_any(x: Any) -> int:
    """any"""
    return 0


@tool
def t_ints(x: list[int]) -> int:
    """ints"""
    return 0


@tool
def t_str(x: str) -> int:
    """str"""
    return 0


def filled(name: str, unit: str) -> bytes:
    head = '{"v":1,"id":1,"op":"call","tool":"%s","args":{"x":[' % name
    tail = "]}}"
    n = (CAP - len(head) - len(tail)) // (len(unit) + 1)
    return (head + ",".join([unit] * n) + tail).encode()


def escaped() -> bytes:
    head = '{"v":1,"id":1,"op":"call","tool":"t_str","args":{"x":"'
    tail = '"}}'
    n = (CAP - len(head) - len(tail)) // 6
    return (head + "\\u00e9" * n + tail).encode()


SHAPES = {
    "empty objects, Any": filled("t_any", "{}"),
    "empty lists, Any": filled("t_any", "[]"),
    "ints, list[int]": filled("t_ints", "0"),
    "ints, unknown tool": filled("nope", "0"),
    "escaped string, str": escaped(),
    "a typical call (63 B)": b'{"v":1,"id":7,"op":"call","tool":"t_str","args":{"x":"EMEA"}}',
}


def part_a() -> None:
    print("A. host CPU per admitted frame (thread CPU, median of 5)")
    for label, frame in SHAPES.items():
        cpu = []
        for _ in range(5):
            host = T._ToolHost([t_any, t_ints, t_str], max_calls=None)
            c0 = time.thread_time()
            answer = host(frame)
            cpu.append(time.thread_time() - c0)
        kind = json.loads(answer)
        kind = "ok" if kind["ok"] else kind["error"]["kind"]
        med = statistics.median(cpu)
        per_mib = med * (1 << 20) / len(frame)
        print(f"  {label:24s} {len(frame):8d} B  {med * 1000:8.2f} ms  {per_mib:6.3f} s/MiB  {kind}")


def part_b() -> None:
    print("B. a frame refused from its length (admit alone, 100,000 frames)")
    host = T._ToolHost([t_any], max_calls=0)
    c0 = time.thread_time()
    for _ in range(100_000):
        host.admit(CAP)
    dt = time.thread_time() - c0
    print(f"  budget_exceeded (calls): {dt / 100_000 * 1e6:.2f} us per frame")


def prototype(budget: int | None) -> None:
    """Wrap admit with a per-run budget of admitted request bytes, as spec 060 would."""
    original = T._ToolHost._060_original = getattr(T._ToolHost, "_060_original", T._ToolHost.admit)
    if budget is None:
        T._ToolHost.admit = original
        return

    def admit(self: Any, length: int) -> bytes | None:
        spent = getattr(self, "_060_spent", 0)
        answer = original(self, length)
        if answer is not None:
            return answer
        if spent + length > budget:
            self._pending = None
            seq = self._frames
            message = f"this run allows {budget} bytes of tool requests; {spent} are used"
            answer = T._error(None, "budget_exceeded", message)
            self._note(T.ToolOutcome(seq, None, None, "budget_exceeded", message, length, len(answer)))
            return answer
        self._060_spent = spent + length
        return None

    T._ToolHost.admit = admit


FLOOD = r"""
import _host, time
head = '{"v":1,"id":1,"op":"call","tool":"t_any","args":{"x":['
tail = ']}}'
n = (1048576 - len(head) - len(tail)) // 3
frame = (head + ",".join(["{}"] * n) + tail).encode()
t0 = time.monotonic()
for i in range(FRAMES):
    _host.call(frame)
print(round(time.monotonic() - t0, 2))
"""


def part_c(frames: int) -> None:
    print(f"C. a guest sends {frames} worst-shape 1 MiB frames through run()")
    spent: list[float] = []
    original_call = T._ToolHost.__call__

    def timed(self: Any, frame: bytes) -> bytes:
        c0 = time.thread_time()
        try:
            return original_call(self, frame)
        finally:
            spent.append(time.thread_time() - c0)

    T._ToolHost.__call__ = timed
    try:
        for label, budget in (("no byte budget (today)", None), ("prototype 16 MiB", 16 << 20)):
            prototype(budget)
            for fuel in (None, 10**13):
                spent.clear()
                w0, c0 = time.perf_counter(), time.process_time()
                done = run(
                    ["-c", FLOOD.replace("FRAMES", str(frames))],
                    tools=[t_any],
                    fuel=fuel,
                    deadline_s=120,
                )
                wall, cpu = time.perf_counter() - w0, time.process_time() - c0
                kinds: dict[str, int] = {}
                for o in done.tools.outcomes:
                    kinds[o.outcome] = kinds.get(o.outcome, 0) + 1
                print(
                    f"  {label:24s} fuel={'on ' if fuel else 'off'} frames read={len(spent):3d} "
                    f"frame-host CPU {sum(spent):6.2f} s  run wall {wall:6.2f} s  "
                    f"process CPU {cpu:6.2f} s  fuel_used {done.fuel_used}  {kinds}  "
                    f"exit {done.exit_code} {done.trapped}"
                )
    finally:
        T._ToolHost.__call__ = original_call
        prototype(None)


def part_c0() -> None:
    """Fuel for the guest's loop alone: the same program with 0 and with 2 frames."""
    print("C0. guest fuel to build a frame and to re-send one (fuel on, defaults, no budget)")
    used = []
    for k in (0, 1, 21):
        done = run(["-c", FLOOD.replace("FRAMES", str(k))], tools=[t_any], fuel=10**13)
        used.append(done.fuel_used)
        print(f"  {k:2d} frames: fuel_used {done.fuel_used}")
    print(f"  per re-sent frame: {(used[2] - used[1]) / 20:.0f} fuel")


if __name__ == "__main__":
    print(sys.version.split()[0], sys.platform)
    part_a()
    part_b()
    part_c0()
    part_c(int(sys.argv[1]) if len(sys.argv) > 1 else 40)
