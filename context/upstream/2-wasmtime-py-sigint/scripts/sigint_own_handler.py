import signal
import threading

import wasmtime

WAT = """(module
  (import "h" "f" (func $f))
  (func (export "run") (local $i i32)
    (loop $l
      (local.set $i (i32.add (local.get $i) (i32.const 1)))
      (br_if $l (i32.lt_u (local.get $i) (i32.const 2000000000))))
    call $f))"""

def own_handler(signum, frame):
    raise KeyboardInterrupt  # an embedder handler that raises, as asyncio's does


signal.signal(signal.SIGINT, own_handler)
engine = wasmtime.Engine()
store = wasmtime.Store(engine)
linker = wasmtime.Linker(engine)
linker.define_func("h", "f", wasmtime.FuncType([], []), lambda: None)
run = linker.instantiate(store, wasmtime.Module(engine, WAT)).exports(store)["run"]

# Ctrl-C while the loop runs, before the call to the host function
threading.Timer(0.2, signal.raise_signal, (signal.SIGINT,)).start()
try:
    run(store)
except KeyboardInterrupt:
    print("KeyboardInterrupt, as expected")
