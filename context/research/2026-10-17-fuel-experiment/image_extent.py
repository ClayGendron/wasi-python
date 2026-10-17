"""Instantiation fuel by data extent: is it one per byte of the memory image?"""
import tempfile
import wasmtime as wt

def wat(pages, segs):
    s = " ".join(f'(data (i32.const {at}) "{"a" * n}")' for at, n in segs)
    return f'(module (memory (export "memory") {pages}) {s} (func (export "start")))'

def inst_fuel(eng, mod):
    s = wt.Store(eng); s.set_fuel(10**12); s.set_epoch_deadline(1 << 40)
    wt.Instance(s, mod, [])
    return 10**12 - s.get_fuel()

c = wt.Config(); c.consume_fuel = True; c.epoch_interruption = True
e = wt.Engine(c)
for pages, segs in [(1, [(16, 20000)]), (2, [(0, 1), (100000, 1)]), (100, [(0, 1), (6000000, 1)]), (100, [(0,1),(100000,1),(6000000,1)]), (10, [(16, 40000)])]:
    m = wt.Module(e, wt.wat2wasm(wat(pages, segs)))
    b = m.serialize()
    with tempfile.NamedTemporaryFile(suffix=".cwasm", delete=False) as f:
        f.write(b)
    print(pages, segs, "|", inst_fuel(e, m), inst_fuel(e, wt.Module.deserialize(e, b)), inst_fuel(e, wt.Module.deserialize_file(e, f.name)))
# Config.memory_init_cow off
c2 = wt.Config(); c2.consume_fuel = True; c2.epoch_interruption = True
try:
    c2.memory_init_cow = False
    e2 = wt.Engine(c2)
    m = wt.Module(e2, wt.wat2wasm(wat(1, [(16, 11)])))
    b = m.serialize()
    with tempfile.NamedTemporaryFile(suffix=".cwasm", delete=False) as f:
        f.write(b)
    print("cow off", inst_fuel(e2, m), inst_fuel(e2, wt.Module.deserialize(e2, b)), inst_fuel(e2, wt.Module.deserialize_file(e2, f.name)))
except Exception as ex:
    print("no memory_init_cow:", ex)
print([a for a in dir(wt.Config) if not a.startswith("_")])
