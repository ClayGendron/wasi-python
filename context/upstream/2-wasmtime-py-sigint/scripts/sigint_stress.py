"""Many SIGINTs at random moments while the main thread makes host-heavy wasm calls.

Every SIGINT must end as a KeyboardInterrupt in Python, the process must not
crash, and the SIGINT handler must be Python's default between calls.
"""
import os
import random
import signal
import sys
import threading
import time

import wasmtime

WAT = """(module
  (import "h" "f" (func $f (param i32) (result i32)))
  (func (export "run") (param $n i32) (result i32) (local $acc i32)
    (loop $l
      (local.set $acc (call $f (local.get $acc)))
      (local.set $n (i32.sub (local.get $n) (i32.const 1)))
      (br_if $l (local.get $n)))
    local.get $acc))"""

signal.signal(signal.SIGINT, signal.default_int_handler)
engine = wasmtime.Engine()
module = wasmtime.Module(engine, WAT)
linker = wasmtime.Linker(engine)
ty = wasmtime.FuncType([wasmtime.ValType.i32()], [wasmtime.ValType.i32()])
linker.define_func("h", "f", ty, lambda x: x + 1)

SIGNALS = int(sys.argv[1]) if len(sys.argv) > 1 else 200
sent = 0
done = threading.Event()


def sender():
    global sent
    rng = random.Random(1)
    while sent < SIGNALS:
        time.sleep(rng.uniform(0.0005, 0.005))
        os.kill(os.getpid(), signal.SIGINT)
        sent += 1
    done.set()


threading.Thread(target=sender, daemon=True).start()
caught = calls = wrong = 0
while True:
    try:
        store = wasmtime.Store(engine)
        run = linker.instantiate(store, module).exports(store)["run"]
        if run(store, 1000) != 1000:
            wrong += 1
        calls += 1
        if signal.getsignal(signal.SIGINT) is not signal.default_int_handler:
            wrong += 1
        if done.is_set():
            break
    except KeyboardInterrupt:
        caught += 1
# Let a last in-flight signal land.
try:
    time.sleep(0.05)
except KeyboardInterrupt:
    caught += 1
print(f"sent {sent} SIGINTs, caught {caught} KeyboardInterrupts, {calls} calls completed, {wrong} wrong")
