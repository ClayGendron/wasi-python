"""Bounded local checks for h08-process: traps, door at depth, host BaseExceptions, fork."""
import os, sys, time, json

import wasi_python
from wasi_python import run
from wasi_python import _wasmtime_ffi as ffi, _call
from wasi_python._process import process

mode = sys.argv[1]
OK = ["-c", "print('ok')"]

def show(label, done):
    print(json.dumps({"check": label, "exit_code": done.exit_code, "trapped": done.trapped,
                      "stdout_tail": done.stdout[-120:].decode("utf-8", "replace"),
                      "stderr_tail": done.stderr[-300:].decode("utf-8", "replace"),
                      "last_exception_none": ffi.last_exception() is None,
                      "host_functions": ffi.host_function_count()}), flush=True)

def normal(label):
    show(label, run(OK, deadline_s=60))

t0 = time.monotonic()
normal("baseline")
if mode == "traps":
    code = "import sys\nsys.setrecursionlimit(10**8)\ndef f(n): return f(n + 1)\nf(0)"
    show("stack_overflow", run(["-c", code], deadline_s=60))
    normal("after_stack_overflow")
    show("out_of_fuel", run(["-c", "while True: pass"], fuel=10**8, deadline_s=60))
    normal("after_fuel")
    show("deadline", run(["-c", "while True: pass"], deadline_s=0.5))
    normal("after_deadline")
elif mode == "door_depth":
    calls = [0]
    def host(b):
        calls[0] += 1
        return b"ok" * 8
    code = ("import sys, _host\nsys.setrecursionlimit(10**8)\n"
            "def f(n):\n    _host.call(b'x' * 64)\n    return f(n + 1)\nf(0)")
    done = run(["-c", code], host=host, deadline_s=240)
    show("door_at_every_depth", done)
    print(json.dumps({"host_calls": calls[0]}), flush=True)
    normal("after_door_depth")
elif mode == "tools_depth":
    from wasi_python.tools import tool
    def add(a: int, b: int) -> int:
        return a + b
    frame = ('{"a":' * 62 + '1' + '}' * 62).encode()
    code = ("import sys, _host\nsys.setrecursionlimit(10**8)\nF = " + repr(frame) + "\n"
            "def f(n):\n    _host.call(F)\n    return f(n + 1)\nf(0)")
    done = run(["-c", code], tools=[tool(add)], max_tool_calls=None,
               max_tool_request_bytes=None, deadline_s=240)
    show("tool_frame_at_every_depth", done)
    print(json.dumps({"tool_frames": None if done.tools is None else done.tools.frames
                      if hasattr(done.tools, "frames") else str(done.tools)[:200]}), flush=True)
    normal("after_tools_depth")
elif mode == "host_raises":
    for exc in (KeyboardInterrupt, SystemExit):
        def host(b, exc=exc):
            raise exc()
        try:
            done = run(["-c", "import _host\n_host.call(b'x')\nprint('after')"], host=host,
                       deadline_s=60)
            print(json.dumps({"check": "host_raises_" + exc.__name__, "returned": True,
                              "trapped": done.trapped}), flush=True)
        except BaseException as e:
            print(json.dumps({"check": "host_raises_" + exc.__name__, "raised": type(e).__name__,
                              "last_exception_none": ffi.last_exception() is None,
                              "host_functions": ffi.host_function_count()}), flush=True)
        normal("after_host_raises_" + exc.__name__)
elif mode == "fork":
    zips = {k: str(v[0].path) for k, v in process().zips.items()}
    pid = os.fork()
    if pid == 0:
        try:
            run(OK, deadline_s=10)
            msg = "child_ran"
        except RuntimeError as e:
            msg = "child_refused: " + str(e)[:90]
        except BaseException as e:
            msg = "child_other: " + type(e).__name__
        print(json.dumps({"check": "fork_child", "result": msg, "forked": process().forked}),
              flush=True)
        sys.exit(0)  # a normal exit: the child's atexit hooks run
    _, status = os.waitpid(pid, 0)
    print(json.dumps({"check": "fork_parent", "child_status": status,
                      "zip_folders_still_there": all(os.path.isdir(p) for p in zips.values())}),
          flush=True)
    normal("parent_after_fork")
elif mode == "late_output":
    import ctypes
    buf = (ctypes.c_ubyte * 5).from_buffer_copy(b"hello")
    unknown = 10**9  # a key never handed out: a write after its stream was dropped
    n = _call._write_output(unknown, ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte)), 5)
    _call._free_output(unknown)
    print(json.dumps({"check": "late_write_unknown_key", "returned": n,
                      "outputs_left": len(process().outputs)}), flush=True)
print(json.dumps({"mode": mode, "seconds": round(time.monotonic() - t0, 1)}), flush=True)
