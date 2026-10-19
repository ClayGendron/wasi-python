"""Spec 071 v2: faulthandler and wasmtime's trap handlers on Linux. Each case in its own process.
Modes: when faulthandler changes (none / enable-before / enable-after / disable-after) x the engine's
signals_based_traps (on / off). Spectre flags left at their defaults. Guests: unreachable, call-stack exhaustion, out-of-bounds load."""
import subprocess, sys

CASE = r'''
import faulthandler, sys, wasmtime
fh, sig = sys.argv[1], sys.argv[2] == "on"
if fh in ("before", "disable-after"):
    faulthandler.enable()
cfg = wasmtime.Config()
cfg.consume_fuel = True
cfg.epoch_interruption = True
if not sig:
    cfg.signals_based_traps = False
try:
    engine = wasmtime.Engine(cfg)
except Exception as e:
    print("engine refused:", str(e).splitlines()[0]); sys.exit(0)
wat = """(module (memory 1)
  (func (export "u") unreachable)
  (func $r (export "r") call $r)
  (func (export "m") (drop (i32.load (i32.const 0x7ffffff0)))))"""
module = wasmtime.Module(engine, wat)
def call(name):
    store = wasmtime.Store(engine); store.set_fuel(10**9); store.set_epoch_deadline(1 << 40)
    f = wasmtime.Instance(store, module, []).exports(store)[name]
    try:
        f(store); return "no trap?!"
    except wasmtime.Trap as e:
        return str(e.trap_code)
print("first", call("u"), flush=True)
if fh == "after":
    faulthandler.enable()
elif fh == "disable-after":
    faulthandler.disable()
for n in ("u", "r", "m"):
    print(n, call(n), flush=True)
print("exit normally")
'''
for sig in ("on", "off"):
    for fh in ("none", "before", "after", "disable-after"):
        r = subprocess.run([sys.executable, "-c", CASE, fh, sig], capture_output=True, text=True)
        out = r.stdout.strip().replace("\n", " | ")
        err = r.stderr.strip().splitlines()[:1]
        print(f"signals {sig:3} faulthandler {fh:13}: exit {r.returncode:3} | {out} {err if r.returncode else ''}", flush=True)
