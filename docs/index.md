# wasi-python

wasi-python is CPython 3.15 built for `wasm32-wasip1`, with numpy, pandas, scipy, scikit-learn, statsmodels, matplotlib and lxml compiled in. It is one static WebAssembly binary. It needs no browser and no JavaScript. It runs on a WASI host, and the `wasi-python` wheel brings one, so you can run it from your own Python program. It is built to run code you did not write, including code a model writes: the guest sees only the folders and host functions you hand it.

```python
from wasi_python import run

done = run(["-c", "import pandas as pd; print(pd.Series([1, 2, 3]).sum())"])
done.exit_code, done.stdout        # (0, b'6\n')
```

The packages are linked in as builtin modules. That means the guest opens no shared library and installs nothing at run time.

## Where to start

- **Use it.** `pip install wasi-python`, then run your first sandboxed program. Start with [Your first run](get-started/first-run.md).
- **Embed it.** Run `python.wasm` from another language or another WASI host. Start with [Embed from other languages](how-to/embed-from-other-languages.md).
- **Build it.** Build the artifacts from pinned sources and make a change. Start with [Building from source](contributing/building.md).

New to a term on these pages? See the [glossary](reference/glossary.md).

## Why WASI and not a browser build

WebAssembly is the machine: an instruction set and a file format. WASI is the operating-system interface the binary talks to: files, the clock, arguments and standard output. Most "Python in WebAssembly" means Pyodide, which needs a browser or Node and Emscripten's JavaScript glue. This binary needs a WASI host and nothing else, and its sandbox is WASI's capability model. Read more in [Why WASI](explanation/why-wasi.md).

## Licence

wasi-python is licensed under Apache-2.0. Each release carries the licence notices of everything it builds in.

In short: one sandboxed CPython with the scientific stack built in, which you run from your own program.
