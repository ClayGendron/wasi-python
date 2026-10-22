# Install wasi-python

This page shows you how to install the `wasi-python` package, what it brings with it, and where it
keeps the compiled module between runs.

## Install the package

You need Python 3.11 or later on the host. Install the package from PyPI with pip:

```
pip install wasi-python
```

Or add it to a uv project:

```
uv add wasi-python
```

That is all. The command `wasi-python` and the Python function `wasi_python.run` are now ready.
Go on to [Your first run](first-run.md).

## What comes with it

The wheel carries the whole *artifact set*: the files that make up the runtime.

| file | what it is |
|---|---|
| `python.wasm` | CPython with numpy, pandas and the other compiled packages built in, as one WebAssembly module |
| `python-snapshot.wasm` | the same module, with the interpreter already started |
| `python-stdlib.zip` | the standard library and the pure-Python packages |
| `MANIFEST` and `SHA256SUMS` | every pinned source and recipe hash, and the files' checksums |

Installing the package also installs wasmtime-py (`wasmtime>=49,<50`). wasmtime-py is the
WebAssembly runtime that runs the guest. The *guest* is the Python program that runs inside the
sandbox; the *host* is your own Python process.

You can still write `pip install "wasi-python[run]"`. The `run` extra is empty and is kept so
that older instructions keep working.

## Install without wasmtime-py

An *embedder* is a program that runs the artifact set itself. Perhaps it brings its own wasmtime
binding, in another version or another language. An embedder installs the package without its
dependencies:

```
pip install --no-deps wasi-python
```

It then calls `wasi_python.artifacts()` for the files. The function returns an `Artifacts` value
with four paths: `snapshot`, `plain`, `stdlib_zip` and `manifest`. Importing `wasi_python` never
loads wasmtime; only `run` does.

`artifacts()` finds the set in this order:

1. the folder that `$WASI_PYTHON_ARTIFACTS` names;
2. when the package runs from a source checkout of wasi-python, that checkout's
   `build/artifacts/`;
3. the wheel's own copy.

A copy installed with `pip install --target`, or vendored into another project, never takes a
neighbouring `build/` folder. `run` and `Session` check the set they find against its
`SHA256SUMS` before they use it. That check catches a file changed or half-written since the
build. It does not catch a set rewritten whole, with a new `SHA256SUMS`. So keep any folder you
name with `$WASI_PYTHON_ARTIFACTS`, or pass as `artifacts=`, where only you can write.

## Where the compiled module is kept

The first call compiles the WebAssembly module to native code. The runner keeps the result as a
`.cwasm` file, so later calls skip the compile. The file lives in your user cache folder, or in
`$WASI_PYTHON_CACHE` if you set it. Give `$WASI_PYTHON_CACHE` as an absolute path: a relative one
names a different folder in each working folder.

A `.cwasm` file is native code, so the runner is strict about it. It loads one only from a folder
at mode `0700` holding files at mode `0600`, as the runner itself makes them. A file made any
other way is compiled around and never loaded. Pass `cache_dir=False` to keep the compiled module
in memory only. A process with no home folder and no `$WASI_PYTHON_CACHE` does the same.

On Windows the runner can check only that the cache folder and its files are not links. It
cannot check who wrote them. So `cache_dir` and `$WASI_PYTHON_CACHE` must name a folder only you
can write. The default, in your own profile, is one.

Never grant a guest the cache folder. See [Grant folders to the guest](../how-to/grants.md) for
the folders the runner refuses to grant.

In one line: `pip install wasi-python` gives you the runtime, its artifact set and wasmtime-py,
and the first call caches a compiled module where only you can write.
