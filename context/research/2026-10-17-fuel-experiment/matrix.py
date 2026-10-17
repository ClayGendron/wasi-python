"""Instantiate fuel of a one-segment module across engine configs and ways to obtain the module."""
import sys, tempfile
from pathlib import Path
import wasmtime as wt

WAT = '(module (memory 1) (data (i32.const 16) "hello") (func (export "f")))'
d = Path(tempfile.mkdtemp())
(d / "m.wat").write_text(WAT)

def inst(e, m):
    s = wt.Store(e); s.set_fuel(10**9); s.set_epoch_deadline(1 << 40); wt.Instance(s, m, []); return 10**9 - s.get_fuel()

def cfg(**kw):
    c = wt.Config(); c.consume_fuel = True; c.epoch_interruption = True
    for k, v in kw.items(): setattr(c, k, v)
    return c

rows = [("default", {}), ("epoch off", {"epoch_interruption": False}),
        ("opt none", {"cranelift_opt_level": "none"}), ("opt speed_and_size", {"cranelift_opt_level": "speed_and_size"}),
        ("parallel off", {"parallel_compilation": False}), ("exceptions on", {"wasm_exceptions": True})]
for name, kw in rows:
    e = wt.Engine(cfg(**kw))
    m = wt.Module(e, wt.wat2wasm(WAT)); b = m.serialize(); (d / "m.cwasm").write_bytes(b)
    other = wt.Engine(cfg(**kw))
    print(f"{name:20} compiled={inst(e, m)} from_file={inst(e, wt.Module.from_file(e, str(d / 'm.wat')))} "
          f"deser_bytes={inst(e, wt.Module.deserialize(e, b))} deser_file={inst(e, wt.Module.deserialize_file(e, str(d / 'm.cwasm')))} "
          f"other_engine_file={inst(other, wt.Module.deserialize_file(other, str(d / 'm.cwasm')))}")
# wasmtime's own cache (Config.cache): first compile, then a cache hit in a fresh engine
cache_toml = d / "cache.toml"
cache_toml.write_text(f'[cache]\ndirectory = "{d / "wtcache"}"\n')
for i in range(2):
    c = cfg(); c.cache = str(cache_toml); e = wt.Engine(c)
    print(f"Config.cache pass {i}: compiled={inst(e, wt.Module(e, wt.wat2wasm(WAT)))}")
