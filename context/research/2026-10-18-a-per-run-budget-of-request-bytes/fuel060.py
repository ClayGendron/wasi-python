"""Fuel per re-sent 1 MiB frame: 1 and 101 frames to an unknown tool, three times each."""
from wasi_python import run
from wasi_python.tools import tool

@tool
def t(x: int) -> int:
    """t"""
    return 0

PROG = r"""
import _host
head = '{"v":1,"id":1,"op":"call","tool":"nope","args":{"x":['
tail = ']}}'
n = (1048576 - len(head) - len(tail)) // 2
frame = (head + ",".join(["0"] * n) + tail).encode()
for i in range(FRAMES):
    _host.call(frame)
"""
for rep in range(3):
    u = [run(["-c", PROG.replace("FRAMES", str(k))], tools=[t], fuel=10**13).fuel_used for k in (1, 101)]
    print(f"rep {rep}: 1 frame {u[0]}, 101 frames {u[1]}, per re-sent frame {(u[1]-u[0])/100:.0f}")
