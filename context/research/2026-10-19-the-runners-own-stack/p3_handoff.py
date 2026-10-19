"""Probe 3 (a benchmark, for the memo only): what a thread of its own costs per call, and what
handing one host callback back to the caller's thread costs, in CPython on this host."""
import queue, sys, threading, time

N = 20000

def start_join(size: int, n: int) -> float:
    old = threading.stack_size(size)
    try:
        t0 = time.perf_counter()
        for _ in range(n):
            t = threading.Thread(target=lambda: None); t.start(); t.join()
        return (time.perf_counter() - t0) / n
    finally:
        threading.stack_size(old)

def roundtrip(n: int, timed: bool) -> float:
    inbox: queue.SimpleQueue = queue.SimpleQueue()
    done = object()
    def runner():
        reply = threading.Lock()
        for i in range(n):
            reply.acquire()
            box = [None]
            inbox.put((lambda x: x + 1, i, box, reply))
            reply.acquire()  # released by the caller once box is filled
            reply.release()
        inbox.put(done)
    t = threading.Thread(target=runner); t.start()
    t0 = time.perf_counter()
    while True:
        item = inbox.get(timeout=0.05) if timed else inbox.get()
        if item is done:
            break
        fn, arg, box, reply = item
        box[0] = fn(arg)
        reply.release()
    el = time.perf_counter() - t0
    t.join()
    return el / n

def direct(n: int) -> float:
    f = lambda x: x + 1
    t0 = time.perf_counter()
    for i in range(n):
        f(i)
    return (time.perf_counter() - t0) / n

print(sys.version.split()[0], sys.platform)
for size in (0, 9 << 20, 16 << 20):
    print(f"thread start+join, stack_size={size:>9}: {start_join(size, 2000) * 1e6:7.1f} us")
print(f"callback called directly:            {direct(N) * 1e6:7.2f} us")
print(f"callback handed to the caller (untimed wait): {roundtrip(N, False) * 1e6:7.1f} us")
print(f"callback handed to the caller (50 ms timed wait): {roundtrip(N, True) * 1e6:7.1f} us")
