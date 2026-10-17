"""Two effects of the startup charge and the remedy: meter from after instantiation.

1. A cap smaller than the memory image traps at instantiation for a compiled module, not for a
   loaded one.
2. Giving instantiation its own budget, then setting the caller's fuel, makes fuel_used and the
   cap the same however the module was obtained.
"""
import tempfile
from pathlib import Path
import wasmtime as wt

WAT = """(module (memory 1) (data (i32.const 16) "hello")
  (func (export "f") (result i32) (local i32)
    (loop $l local.get 0 i32.const 1 i32.add local.tee 0 i32.const 100 i32.lt_u br_if $l)
    local.get 0))"""
c = wt.Config(); c.consume_fuel = True; c.epoch_interruption = True
e = wt.Engine(c)
m = wt.Module(e, wt.wat2wasm(WAT))
p = Path(tempfile.mkdtemp()) / "m.cwasm"; p.write_bytes(m.serialize())
ways = {"compiled": m, "deserialize_file": wt.Module.deserialize_file(e, str(p))}

def today(mod, cap):
    s = wt.Store(e); s.set_fuel(cap); s.set_epoch_deadline(1 << 40)
    try:
        r = wt.Instance(s, mod, []).exports(s)["f"](s)
    except wt.Trap as t:
        return f"trap {t.trap_code}", cap - s.get_fuel()
    return r, cap - s.get_fuel()

INSTANTIATE = 2**63 - 1
def remedy(mod, cap):
    s = wt.Store(e); s.set_fuel(INSTANTIATE); s.set_epoch_deadline(1 << 40)
    inst = wt.Instance(s, mod, [])
    s.set_fuel(cap)  # the caller's cap starts here: only the guest's own calls spend it
    try:
        r = inst.exports(s)["f"](s)
    except wt.Trap as t:
        return f"trap {t.trap_code}", cap - s.get_fuel()
    return r, cap - s.get_fuel()

for cap in (1000, 10**6):
    for name, mod in ways.items():
        print(f"cap={cap:>7} {name:17} today={today(mod, cap)} remedy={remedy(mod, cap)}")
