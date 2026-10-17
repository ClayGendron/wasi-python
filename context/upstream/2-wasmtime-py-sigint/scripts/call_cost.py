"""Per-call cost of a trivial wasm export, on the main thread and on a worker."""
import threading
import timeit

import wasmtime

engine = wasmtime.Engine()
store = wasmtime.Store(engine)
module = wasmtime.Module(engine, '(module (func (export "nop")))')
nop = wasmtime.Instance(store, module, []).exports(store)["nop"]
N = 200000


def best(label):
    t = min(timeit.repeat(lambda: nop(store), number=N, repeat=5))
    print(f"{label}: {t / N * 1e6:.2f} us per call")


best("main thread")
t = threading.Thread(target=best, args=("worker thread",))
t.start()
t.join()
