# Performance and size

This page gives the measured size and speed of wasi-python, and says how the numbers were taken.
Use it to set expectations, not as a promise.

!!! note "Dated: 2026-10-22"
    These figures were recorded on the CPython 3.15 line, on one arm64 Mac running macOS, with
    wasmtime 49. Times are facts of that one machine. Instruction counts are wasmtime's fuel
    counts, which repeat on any machine with the same wasmtime version.

## Size

| file | size |
|---|---|
| `python.wasm` (the plain reactor) | 99.4 MB |
| `python-snapshot.wasm` | 104.5 MB |
| `python-stdlib.zip` | 53.9 MB |
| the `wasi-python` wheel | 98.3 MB |
| each release asset, compressed with xz | 6 to 22 MB |

The binaries hold CPython and every compiled package: numpy and scipy on one OpenBLAS, pandas,
scikit-learn, statsmodels, matplotlib, lxml, regex and the rest. The zip holds the standard
library and every package's Python code as bytecode.

## Starting a call

| what | time | guest instructions |
|---|---|---|
| one call on the snapshot, `-c pass` | 16 ms | 43.8 million |
| one call on the plain reactor, `-c pass` | 21 ms | 218 million |
| `import numpy` on the snapshot | | 0.81 billion |
| `import pandas` on the snapshot | about 0.8 s | 4.66 billion |
| `import pandas` on the plain reactor | 620 ms | 4.92 billion |

Most of a bare snapshot call is the interpreter finalizing after the program ends.

The snapshot pre-imports no package, so a call pays for what it imports, when it imports it.
Some more imports on the snapshot:

| import | guest instructions |
|---|---|
| `yaml`, `jinja2`, `tabulate` | 1.07 billion |
| `pypdf` | 1.42 billion |
| `openpyxl`, `xlsxwriter` | 2.24 billion |
| `sympy` | 4.11 billion |

A line plot saved as PNG costs about 8.78 billion instructions with a fresh font cache, and 6.79
billion when `MPLCONFIGDIR` points at a kept folder.

The first call in a process compiles the binary to native code, which took about 3 seconds when
first measured, on an earlier and smaller build. A first call that loads the compiled module
from the `.cwasm` cache took about 0.1 seconds.

To pay a large import less often, do several steps in one call, or use a
[session](sessions.md), whose later turns keep what an earlier turn imported.

## Compute

Measured against native CPython on the same machine:

| work | wasi-python against native |
|---|---|
| numpy kernels | 1.6 to 2.3 times slower |
| pandas `groupby` over a million rows | 1.3 to 1.4 times slower |

So compute runs about 1.3 to 2.3 times slower than native. The guest has no SIMD in numpy's own
loops and no threads. The numpy figure was taken before numpy's `dot`, `matmul` and `linalg`
moved onto OpenBLAS, so it describes numpy's own loops, not its linear algebra.

Results match native: numpy, pandas, `bz2`, `lzma` and `sqlite3` give byte-identical output to
native Python on the same pins, on six reference jobs.

## Building

A full build from pinned sources, with the downloads already present, took 8 minutes 35
seconds on a 10-core arm64 Mac.

## How the numbers were taken

- **Instruction counts** come from wasmtime's fuel meter, which counts every wasm instruction
  the guest executes. They are the project's measure of work. Its tests assert counts and never
  time a run. See [fuel](fuel.md).
- **Times** are benchmark facts, recorded on the machine above as each feature was built.
  Another machine, another load or another wasmtime version gives other times.
- **Sizes** are the files as built, on the date above, and grow as packages are added.

## In one line

On one arm64 Mac, a wasi-python call starts in about 16 ms on the snapshot, computes about 1.3 to
2.3 times slower than native, and gives the same results.
