<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/ClayGendron/wasi-python/main/docs/assets/wasi-python-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/ClayGendron/wasi-python/main/docs/assets/wasi-python-light.svg">
    <img alt="WASI-PYTHON" width="640" src="https://raw.githubusercontent.com/ClayGendron/wasi-python/main/docs/assets/wasi-python.svg">
  </picture>
</p>

<p align="center">
  <a href="https://pypi.org/project/wasi-python/"><img alt="PyPI" src="https://img.shields.io/pypi/v/wasi-python"></a>
  <a href="https://pypi.org/project/wasi-python/"><img alt="Python versions" src="https://img.shields.io/pypi/pyversions/wasi-python"></a>
  <a href="https://github.com/ClayGendron/wasi-python/actions/workflows/release.yml"><img alt="Release" src="https://github.com/ClayGendron/wasi-python/actions/workflows/release.yml/badge.svg"></a>
  <a href="https://github.com/ClayGendron/wasi-python/blob/main/LICENSE"><img alt="Licence" src="https://img.shields.io/github/license/ClayGendron/wasi-python"></a>
  <a href="https://codecov.io/gh/ClayGendron/wasi-python"><img alt="Coverage" src="https://codecov.io/gh/ClayGendron/wasi-python/graph/badge.svg"></a>
  <img alt="CPython 3.15" src="https://img.shields.io/badge/CPython-3.15-3776AB">
  <img alt="wasm32-wasip1" src="https://img.shields.io/badge/target-wasm32--wasip1-654FF0">
</p>

**A secure Python sandbox for agent-generated code with the scientific stack inside.**

```
pip install wasi-python
```

wasi-python is CPython 3.15 compiled to WebAssembly as one static binary. It includes numpy, pandas, scipy, scikit-learn, statsmodels, matplotlib, and forty plus other packages.

It is built to run code that AI agents generate, or any other code that is untrusted and must be kept apart from the host process. By default, the sandbox sees no host files and has no network access.

Run it from Python or load the same binary into any WebAssembly host that supports exception handling.

# Installation and Quick Start

```
$ pip install wasi-python
$ wasi-python run -- -c "print('hello, WebAssembly')"
{"exit_code": 0, "fuel_used": null, "stderr": "", "stdout": "hello, WebAssembly\n", "trapped": null, "truncated": []}
```

Requires Python 3.11 or later. The wheel carries the runtime, which unpacks to about 250 MB of WebAssembly and bytecode. Every release is tested on Linux (x86-64 and arm64), macOS (arm64) and Windows (x86-64). [Install](https://claygendron.github.io/wasi-python/get-started/install/) says more about what comes with the package and where it keeps its cache.

# Usage

### 1. The Scientific Stack in a Sandbox

Run numpy, scipy, scikit-learn and pandas inside a Python sandbox. The following recovers a frequency from a noisy signal with numpy, fits a curve with scipy, clusters points with scikit-learn and summarises them with pandas.

```python
from wasi_python import run

code = """
import numpy as np
import pandas as pd
from scipy import optimize
from sklearn.cluster import KMeans

rng = np.random.default_rng(7)

t = np.linspace(0, 5, 200)
signal = np.sin(2 * np.pi * 3 * t) + rng.normal(0, 0.3, t.size)
freqs = np.fft.rfftfreq(t.size, d=t[1] - t[0])
print(f"dominant frequency: {freqs[np.abs(np.fft.rfft(signal)).argmax()]:.1f} Hz")

(a, k), _ = optimize.curve_fit(lambda t, a, k: a * np.exp(-k * t), t, 3 * np.exp(-0.7 * t) + rng.normal(0, 0.1, t.size))
print(f"decay fit: a={a:.2f} k={k:.2f}")

points = np.vstack([c + rng.normal(0, 0.5, (100, 2)) for c in ([1, 1], [5, 5], [1, 5])])
labels = KMeans(n_clusters=3, n_init=10, random_state=0).fit_predict(points)
print(pd.DataFrame(points, columns=["x", "y"]).groupby(labels).mean().round(1))
"""

done = run(["-c", code])
print(done.stdout.decode())
```

```
dominant frequency: 3.0 Hz
decay fit: a=2.97 k=0.70
     x    y
0  5.0  5.0
1  1.0  0.8
2  1.1  5.0
```

`done` also carries `exit_code`, `stderr`, `fuel_used` and `trapped`, which names the limit that stopped a call, such as `"deadline"` or `"out of fuel"`. [Results and errors](https://claygendron.github.io/wasi-python/reference/results-and-errors/) describes every field, and [Packages](https://claygendron.github.io/wasi-python/reference/packages/) lists what each package can do inside the sandbox.

### 2. Safe and Secure by Design

The program inside the sandbox is the guest. Your program is the host. Make two folders on the host, each with a file. Grant the guest one of them, then watch it try the other, the parent folder and a write.

```python
import shutil
from pathlib import Path

from wasi_python import Grant, run

for name in ("wasi_python_shared", "wasi_python_private"):
    Path(name).mkdir(exist_ok=True)
    (Path(name) / "hello.txt").write_text(f"hello from {name}\n")

code = """
for path in ("/shared/hello.txt", "/private/hello.txt", "/shared/../private/hello.txt"):
    try:
        print(path, "->", open(path).read().strip())
    except OSError as e:
        print(path, "->", type(e).__name__)

try:
    open("/shared/notes.txt", "w")
except OSError as e:
    print("write to /shared ->", type(e).__name__)
"""

done = run(["-c", code], grants=[Grant("wasi_python_shared", "/shared")])
print(done.stdout.decode())

shutil.rmtree("wasi_python_shared")
shutil.rmtree("wasi_python_private")
```

```
/shared/hello.txt -> hello from wasi_python_shared
/private/hello.txt -> FileNotFoundError
/shared/../private/hello.txt -> PermissionError
write to /shared -> PermissionError
```

Now ask the guest to reach the network.

```python
from wasi_python import run

code = """
import urllib.request

try:
    urllib.request.urlopen("https://pypi.org")
except Exception as e:
    print("network ->", type(e).__name__)
"""

done = run(["-c", code])
print(done.stdout.decode())
```

```
network -> URLError
```

And every call runs under limits. Here each limit is set low so you can watch it stop a call.

```python
from wasi_python import run

spin = "while True: pass"

done = run(["-c", spin], deadline_s=1)
print("deadline ->", done.trapped)

done = run(["-c", spin], fuel=50_000_000)
print("fuel ->", done.trapped, done.fuel_used)

done = run(["-c", "x = bytearray(512 * 1024 * 1024)"], memory_bytes=128 * 1024 * 1024)
print("memory ->", done.exit_code, done.stderr.decode().strip().splitlines()[-1])

done = run(["-c", "print('x' * 10_000_000)"], output_bytes=1_000_000)
print("output ->", len(done.stdout), done.truncated)
```

```
deadline -> deadline
fuel -> out of fuel 50000000
memory -> 1 MemoryError
output -> 1000000 ('stdout',)
```

Everything the guest can reach is something you handed it. It starts with no files, no network and no way to start a process. A folder comes in through a `Grant` and a host function through `tools=`, and nothing else gets in. Instructions, time, memory, output and open files each have a default cap, and when a guest hits one the call ends and the result says which. The guest is a WebAssembly module with its own memory, so it holds no pointer into your process, and its only calls into the host are the WASI functions and the tools you pass. Each release is built reproducibly and signed by the workflow that built it. [Verify a download](https://claygendron.github.io/wasi-python/how-to/verify-a-download/) shows how to check one.

### 3. Bring Your Own Tools

The guest can call functions from your own program, as tools. Decorate a function, pass it in `tools=`, and guest code imports it with `from host import tools`. The guest sees the function's name, signature and docstring, so a model can read `help(tools)` and use it.

```python
from wasi_python import run
from wasi_python.tools import tool

PRICES = {"apple": 0.5, "pear": 0.8}

@tool(read_only=True)
def price(item: str) -> float:
    """Look up the unit price of an item.

    Args:
        item: The item's name, such as "apple".
    """
    return PRICES[item]

code = """
from host import tools

basket = {"apple": 6, "pear": 3}
print("total", sum(tools.price(name) * n for name, n in basket.items()))
try:
    tools.price("plum")
except Exception as e:
    print("plum ->", e)
"""

done = run(["-c", code], tools=[price])
print(done.stdout.decode())
```

```
total 5.4
plum -> price failed (internal error)
```

A tool runs with your program's authority, so hand the guest narrow functions rather than whole services. When a tool raises, the guest learns only that it failed. The traceback and its message stay on your side, in the call record at `done.tools`. A `gate=` function can look at every call before it runs and refuse it. [Tools](https://claygendron.github.io/wasi-python/how-to/tools/) covers schemas, gating, the record, and recipes for LangChain and MCP tools.

### 4. Maintains State Across Turns

A `Session` keeps one interpreter across several calls, like a notebook kernel. Imports and variables carry over, and a final expression is echoed.

```python
from wasi_python import Session

with Session() as session:
    session.run("import numpy as np; x = np.random.default_rng(1).normal(size=10_000)")
    print(session.run("print(round(float(x.mean()), 3), round(float(x.std()), 3))").stdout.decode())
    print(session.run("int((x > 2).sum())").stdout.decode())
```

```
-0.011 0.998
216
```

A session ends when you close it, when it rests longer than `idle_s`, or when `lifetime_s` passes. Each turn gets its own fuel and deadline. [Sessions](https://claygendron.github.io/wasi-python/how-to/sessions/) covers what carries over, how a session ends, and the shutdown.

### 5. And Async Of Course

`run_async` is the async version of `run`. The guest runs on a worker thread, and guests run in parallel. Here three guests each sleep for a second while a task on the event loop keeps ticking.

```python
import asyncio

from wasi_python import run_async

async def ticker():
    for i in range(3):
        await asyncio.sleep(0.3)
        print("event loop is free, tick", i)

async def main():
    guests = [run_async(["-c", f"import time; time.sleep(1); print('guest {n} done')"]) for n in range(3)]
    results, _ = await asyncio.gather(asyncio.gather(*guests), ticker())
    for done in results:
        print(done.stdout.decode().strip())

asyncio.run(main())
```

```
event loop is free, tick 0
event loop is free, tick 1
event loop is free, tick 2
guest 0 done
guest 1 done
guest 2 done
```

Cancel the task to stop the guest. `Session` has `run_async` too. [Async](https://claygendron.github.io/wasi-python/how-to/async/) covers cancellation, pool sizing and forking servers.

# What's Inside

| Artifact | What it is |
|---|---|
| `python.wasm` | a WASI reactor: CPython with numpy, pandas, scipy, scikit-learn, statsmodels, matplotlib, lxml and regex compiled in |
| `python-snapshot.wasm` | the same binary with the interpreter already started, for a faster first call |
| `python-stdlib.zip` | the standard library and the packages' Python code, as bytecode in one read-only zip |
| `MANIFEST` | every pinned source, toolchain and recipe hash the build used |

They are published as release assets on GitHub and inside the `wasi-python` wheel on PyPI. [More on the artifacts](https://claygendron.github.io/wasi-python/reference/artifacts/).

[Packages](https://claygendron.github.io/wasi-python/reference/packages/) lists every package with its version and what works. Each package's own test suite runs inside the sandbox before a release.

There are no processes, no network and no `pip` inside the guest. [Limitations](https://claygendron.github.io/wasi-python/reference/limitations/) lists every difference from native Python, each with its reason.

# Hosts

The binaries use WebAssembly's exception-handling proposal, so a host must support it. This project runs wasmtime 49 itself. The rest of this list is read from each runtime's release notes and source, not run here.

- **Runs by default:** wasmtime 47 or later (CLI, Rust, wasmtime-py); WasmEdge 0.16 or later.
- **Runs with a switch:** wasmer 6 or later on LLVM or V8, or 7 or later on Cranelift (not Singlepass); wazero 1.12 or later; Node 24.15 or later.

To bring your own host, install the files without wasmtime-py, `pip install --no-deps wasi-python`, and find them with `wasi_python.artifacts()`. Importing `wasi_python` never loads wasmtime. The `wasi_python` package enforces the limits in section 2. Another host sets its own. [Embedding from other languages](https://claygendron.github.io/wasi-python/how-to/embed-from-other-languages/) shows how.

# Build From Source

The build is one command from pinned inputs. Every source is fetched by URL and checked against its SHA-256 before use.

```
scripts/00_download.sh   # fetch every pin and verify it against downloads/SHA256SUMS
scripts/build.sh         # build the artifact set; logs in build/logs/
```

The source trees are the released tarballs plus a few recorded patches (upstream patches carried: 27), each offered upstream and dropped once upstream releases the fix. [Building](https://claygendron.github.io/wasi-python/contributing/building/) gives the full details.

# Contributing, Security, Changelog

- [Contributing](https://claygendron.github.io/wasi-python/contributing/first-change/): start here. [AGENTS.md](https://github.com/ClayGendron/wasi-python/blob/main/AGENTS.md) is the rule book every change follows.
- [Security policy](https://github.com/ClayGendron/wasi-python/blob/main/SECURITY.md): report a way out of the sandbox privately.
- [Changelog](https://github.com/ClayGendron/wasi-python/blob/main/CHANGELOG.md): what each release changed.

# Agentic Development

`v0.1.0` was built by Claude Opus and Fable agents in six days of near-continuous work from October 16th to the 22nd of 2026. The agents made 1,255 commits across 421 sessions, had up to 12 working at once, and read 500 million tokens and generated 9 million. Every change was specified first, built in its own worktree, reviewed by a fresh agent and judged by the test suite before it landed. [How it was built](https://claygendron.github.io/wasi-python/explanation/how-it-was-built/) has the full account, with charts. The rules are in [AGENTS.md](https://github.com/ClayGendron/wasi-python/blob/main/AGENTS.md) and [the contributing pages](https://claygendron.github.io/wasi-python/contributing/principles/).

# Licences

wasi-python is licensed under Apache-2.0. The artifact set carries the licence of every component it links, one file each in its `LICENSES` folder. The wheel's `LICENSE` file holds the Apache-2.0 text followed by each of those licences.
