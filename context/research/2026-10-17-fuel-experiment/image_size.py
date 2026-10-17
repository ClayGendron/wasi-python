"""Fuel spent during instantiation, by memory size and data segment, three ways to get the module."""
import tempfile
import wasmtime as wt

def wat(pages, data_at, data_len):
    seg = f'(data (i32.const {data_at}) "{"a" * data_len}")' if data_len else ""
    return f'(module (memory (export "memory") {pages}) {seg} (func (export "start")))'

def inst_fuel(eng, mod):
    s = wt.Store(eng); s.set_fuel(10**12); s.set_epoch_deadline(1 << 40)
    wt.Instance(s, mod, [])
    return 10**12 - s.get_fuel()

c = wt.Config(); c.consume_fuel = True; c.epoch_interruption = True
e = wt.Engine(c)
print("pages data_at data_len | compiled deser_bytes deser_file")
for pages, at, n in [(1,0,0),(1,16,1),(1,16,11),(1,16,100),(1,60000,100),(2,16,11),(2,70000,11),(10,16,11),(10,600000,11),(10,16,5000),(100,6000000,11)]:
    m = wt.Module(e, wt.wat2wasm(wat(pages, at, n)))
    b = m.serialize()
    with tempfile.NamedTemporaryFile(suffix=".cwasm", delete=False) as f:
        f.write(b)
    print(pages, at, n, "|", inst_fuel(e, m), inst_fuel(e, wt.Module.deserialize(e, b)), inst_fuel(e, wt.Module.deserialize_file(e, f.name)))
