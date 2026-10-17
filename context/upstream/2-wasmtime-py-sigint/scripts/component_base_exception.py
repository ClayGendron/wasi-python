"""A component host function that raises KeyboardInterrupt (no signals involved)."""
from wasmtime import Engine, Store
from wasmtime.component import Component, Linker

engine = Engine()
store = Store(engine)
component = Component(engine, """
    (component
        (import "f" (func $f))
        (core func $f (canon lower (func $f)))
        (core module $m (import "" "f" (func $f)) (func (export "run") call $f))
        (core instance $i (instantiate $m (with "" (instance (export "f" (func $f))))))
        (func (export "run") (canon lift (core func $i "run")))
    )
""")
linker = Linker(engine)
with linker.root() as root:
    def f(store):
        raise KeyboardInterrupt
    root.add_func("f", f)
run = linker.instantiate(store, component).get_func(store, "run")
try:
    run(store)
except KeyboardInterrupt:
    print("KeyboardInterrupt, as expected")
