
import faulthandler, signal, sys
import wasi_python
order = sys.argv[1]
if order in ("before", "before-then-disable"):
    faulthandler.enable()
warm = wasi_python.run(["-c", "print(1)"])
assert warm.exit_code == 0, warm
if order == "after":
    faulthandler.enable()
elif order == "before-then-disable":
    faulthandler.disable()
elif order == "after-then-disable":
    faulthandler.enable()
    faulthandler.disable()
elif order == "signal-after":
    signal.signal(signal.SIGILL, lambda *a: None)
deep = "import json\njson.loads('[' * 200000 + ']' * 200000)"
try:
    done = wasi_python.run(["-c", deep])
    print("trapped", done.trapped, flush=True)
except RuntimeError as e:
    print("refused", e, flush=True)

