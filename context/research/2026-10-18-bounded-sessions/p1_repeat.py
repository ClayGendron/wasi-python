"""P1-P3: repeated export calls into one snapshot instance: fuel and the epoch deadline re-armed per
call, a call after a trap, and calls from several threads, closed from another."""
import sys, threading; sys.path.insert(0, sys.argv[1])
import h, wasmtime as wt

g = h.Guest()
alloc = g.ex["host_alloc"]
B = 10_000_000
used = []
for i in range(5):
    g.store.set_fuel(B)
    p = alloc(g.store, 64)
    used.append(B - g.store.get_fuel())
print("P1 fuel per host_alloc(64), budget re-set before each:", used)

# P1b: a call that runs out of fuel, then a call with a fresh budget
g.store.set_fuel(5)
try:
    alloc(g.store, 1 << 20)
    print("P1b: no trap")
except wt.Trap as e:
    print("P1b first call trapped:", e.trap_code)
g.store.set_fuel(B)
p = alloc(g.store, 64)
print("P1b next call after the trap returned", p, "fuel", B - g.store.get_fuel(), "(wasmtime lets a store be called again after a trap)")

# P2: the epoch deadline is relative to the engine's epoch when it is set
e = h.engine(True)
g.store.set_fuel(B)
g.store.set_epoch_deadline(1)
e.increment_epoch(); e.increment_epoch()
try:
    alloc(g.store, 64)
    print("P2: no trap")
except wt.Trap as ex:
    print("P2 call after the deadline passed trapped:", ex.trap_code)
g.store.set_fuel(B)
g.store.set_epoch_deadline(1000)
print("P2 next call with a re-armed deadline returned", alloc(g.store, 64) != 0)

# P3: one store, calls from three threads in turn, closed from a fourth
g2 = h.Guest()
res = []
def call(tag):
    g2.store.set_fuel(B)
    p = g2.ex["host_alloc"](g2.store, 128)
    res.append((tag, threading.get_ident() != main, p != 0, B - g2.store.get_fuel()))
main = threading.get_ident()
for tag in "ABC":
    t = threading.Thread(target=call, args=(tag,)); t.start(); t.join()
print("P3 calls on three threads (tag, other thread, ok, fuel):", res)
t = threading.Thread(target=g2.close); t.start(); t.join()
print("P3 closed from a fourth thread: ok")
# run once on g, then again: 70
g.store.set_fuel(10**10); g.store.set_epoch_deadline(2**62)
rc1 = g.ex["run"](g.store)
print("P1c run after five host_allocs and two traps: rc", rc1, "stdout", bytes(g.out.data)[-60:])
