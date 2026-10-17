# Catch `BaseException` in component host functions, as #337 did for core

<!-- Draft for the owner to review and post. Base: main at 280ce73.
     If the LAST_EXCEPTION PR lands first, use fix-on-top-of-issue-1.patch. -->

#337 fixed #336 for core host functions: the trampoline now catches
`BaseException`, so `KeyboardInterrupt`, `SystemExit` and custom
`BaseException` subclasses reach the caller. The component path was not
changed. `catch_exceptions` in `wasmtime/component/_enter.py` still catches
only `Exception`, so a component host function that raises
`KeyboardInterrupt` lets it escape the ctypes callback. ctypes then returns
to Wasmtime without writing the return value, Wasmtime reads a stale value
as a `wasmtime_error_t *`, and the process dies.

```python
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
run(store)  # main: "Exception ignored while calling ctypes callback function", then SIGABRT
```

On main (280ce73), macOS arm64, Python 3.14.2, libwasmtime 49.0.0: exit 134
in 3 of 3 runs. With this PR it raises `KeyboardInterrupt`.

The change is `except Exception` → `except BaseException` in
`catch_exceptions`, and the slot's annotation widened to match (mypy flags
the assignment otherwise). The test, `test_host_base_exception` in
`tests/component/test_linker.py`, mirrors the core one from #337:
`KeyboardInterrupt`, `SystemExit` and a custom subclass, each must reach
the caller. On main it aborts the test process (exit 134, 139, 134 in
three runs).

`uv run pytest`: 227 passed, mypy clean.

## Related, not fixed here

A real Ctrl-C can still crash the process when Python handles it at the
very entry of a host function's callback, before the `try`. No code inside
the callback can catch that, because ctypes discards the exception and
leaves the return value unwritten. I will open a separate issue with the
details and some options.
