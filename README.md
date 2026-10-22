# wasi-python

**A statically linked CPython for WebAssembly hosts, with numpy, pandas, scipy, scikit-learn,
statsmodels, matplotlib and lxml compiled in. No browser, no JavaScript.**

`wasi-python` runs Python code you did not write, such as code a model wrote, in a sandbox. It is
one `python.wasm` for `wasm32-wasip1`, with the scientific Python stack linked in as builtin
modules, and a small Python package that runs it under wasmtime. The guest sees only the folders
and functions you hand it: no host files, no network, no processes. It is for anyone who needs
to run untrusted data code from Python, Rust, Go or any other language with a WASI host.

[Documentation](https://claygendron.github.io/wasi_python/) ·
[Changelog](https://github.com/claygendron/wasi_python/blob/main/CHANGELOG.md) ·
[Security](https://github.com/claygendron/wasi_python/blob/main/SECURITY.md) ·
[Licence](https://github.com/claygendron/wasi_python/blob/main/LICENSE)

Status: **0.1.0**, CPython 3.15, wasi-sdk 34. Licence: Apache-2.0.

## What you get

| artifact | what it is |
|---|---|
| `python.wasm` | a WASI reactor: CPython with numpy, pandas, scipy, scikit-learn, statsmodels, matplotlib, lxml and regex compiled in |
| `python-snapshot.wasm` | the same binary with the interpreter already started, for a faster first call |
| `python-stdlib.zip` | the standard library and the packages' Python code, as bytecode in one read-only zip |
| `MANIFEST` | every pinned source, toolchain and recipe hash the build used |

They are published as release assets on GitHub and inside the `wasi-python` wheel on PyPI.
[More on the artifacts](https://claygendron.github.io/wasi_python/reference/artifacts/).

## Quickstart (5 minutes)

Install it (this brings wasmtime-py, which runs the guest):

```
pip install wasi-python        # or: uv add wasi-python
```

Run a program:

```python
from wasi_python import run

done = run(["-c", "import pandas as pd; print(pd.Series([1, 2, 3]).sum())"])
done.exit_code, done.stdout        # (0, b'6\n')
```

Hand it a folder, read-only unless you say otherwise:

```python
from wasi_python import Grant, run

done = run(["-c", "import os; print(os.listdir('/data'))"], grants=[Grant("data", "/data")])
```

Or call it from any language, as a command that prints one line of JSON:

```
$ wasi-python run -- -c "print(1)"
{"exit_code": 0, "fuel_used": null, "stderr": "", "stdout": "1\n", "trapped": null, "truncated": []}
```

A `Session` keeps one interpreter across several calls, like a notebook. `run_async` runs a call
on a worker thread, so an event loop never waits for a guest. `run(tools=[…])` offers the guest
your own Python functions, which it calls with `from host import tools`.
[The tutorial](https://claygendron.github.io/wasi_python/get-started/first-run/) walks through
each.

## Safe by default

A call that names no limit still has one. By default the guest has nothing writable: no `/`, no
`/tmp`, only the read-only standard library and the folders you grant. `root=True` gives a call
a fresh private `/`, writable, removed afterwards. The defaults are 1 GiB of memory, a 60 s
deadline, 16 MiB of output per stream and 1,024 open files; `fuel=` caps the instructions a call
may run. Pass `None` for no limit.

Some things are not protected, such as timing side channels or disk use inside a writable grant.
[The security model](https://claygendron.github.io/wasi_python/explanation/security-model/)
says what is and what is not.

## What runs, and what does not

numpy 2.5.2, pandas 3.0.6, scipy 1.18.1, scikit-learn 1.9.1, statsmodels 0.15.0,
matplotlib 3.11.2, lxml 6.1.3 and regex are compiled in. About 40 pure-Python packages ride in
the zip: Excel, PDF, HTML and XML, YAML, templates, graphs, sympy and more
([the full list](https://claygendron.github.io/wasi_python/reference/packages/)). Each package's
own test suite runs in the guest before a release.

`python.wasm -V` states the platform's facts after its version:

> (wasm32-wasip1: numpy's default integer is 32-bit; no threads; no ctypes, mmap, sockets, ssl, zstd or scipy.odr; compute about 1.3 to 2.3 times slower than native)

There are no processes and no network. [The limitations
page](https://claygendron.github.io/wasi_python/reference/limitations/) lists every difference
from native Python, each with its reason.

## Hosts

The binaries use WebAssembly's exception-handling proposal, so a host must support it. This
project runs wasmtime 49 itself; the rest of this list is read from each runtime's release notes
and source.

- **Runs by default:** wasmtime 47 or later (CLI, Rust, wasmtime-py); WasmEdge 0.16 or later.
- **Runs with a switch:** wasmer 6 or later on LLVM, V8 or Cranelift; wazero 1.12 or later;
  Node 24.15 or later.

To bring your own host, install the files without wasmtime-py,
`pip install --no-deps wasi-python`, and find them with `wasi_python.artifacts()`. Importing
`wasi_python` never loads wasmtime.
[Embedding from other languages](https://claygendron.github.io/wasi_python/how-to/embed-from-other-languages/)
shows how.

## API stability

The public API is what `wasi_python` and `wasi_python.tools` export (each module's `__all__`),
the `wasi-python` command, and the environment variables `WASI_PYTHON_ARTIFACTS` and
`WASI_PYTHON_CACHE`. Versions are `0.MINOR.PATCH`: a patch release changes no public name or
default, and a minor release removes something only after two minor releases of deprecation.
[The Python API](https://claygendron.github.io/wasi_python/reference/python-api/) and
[support and versioning](https://claygendron.github.io/wasi_python/reference/support-and-versioning/)
pages give the whole promise.

## Verifying a download

Every release asset carries build provenance signed by this repository's release workflow at
the release's tag:

```
gh attestation verify <asset> --repo ClayGendron/wasi_python \
  --signer-workflow ClayGendron/wasi_python/.github/workflows/release.yml@refs/tags/v<version> \
  --source-ref refs/tags/v<version> --deny-self-hosted-runners
```

`gh` must be logged in for this. Without `gh`, check the asset against the release's
`SHA256SUMS`.

## Building from source

The build is one command from pinned inputs: every source is fetched by URL and checked against
its SHA-256 before use.

```
scripts/00_download.sh   # fetch every pin and verify it against downloads/SHA256SUMS
scripts/build.sh         # build the artifact set; logs in build/logs/
```

The source trees are the released tarballs plus a few recorded patches, each offered upstream
and dropped once upstream releases the fix: upstream patches carried: 27. Every other adaptation is
a recipe file. [Building](https://claygendron.github.io/wasi_python/contributing/building/)
gives the details.

## Contributing, security, changelog

- [Contributing](https://claygendron.github.io/wasi_python/contributing/first-change/): start
  here. [AGENTS.md](https://github.com/claygendron/wasi_python/blob/main/AGENTS.md) is the rule
  book every change follows.
- [Security policy](https://github.com/claygendron/wasi_python/blob/main/SECURITY.md): report a
  way out of the sandbox privately.
- [Changelog](https://github.com/claygendron/wasi_python/blob/main/CHANGELOG.md): what each
  release changed.

## Licences

wasi-python is licensed under Apache-2.0. The artifact set, and the wheel with it, carries the
licence of every component it links, one file each in its `LICENSES` folder.

FreeType's licence asks every binary distribution to say this in its documentation, and this
README is the wheel's description:

> Portions of this software are copyright © 2026 The FreeType Project (https://freetype.org).
> All rights reserved.
