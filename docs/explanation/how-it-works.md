# How it works

This page follows a call from your program into the guest and back. It explains the pieces of the artifact set and why each one exists. It is for users who want a mental model, and for embedders who drive the binaries from their own host.

## The pieces

A release is an *artifact set* of four kinds of file:

| file | what it is |
|---|---|
| `python.wasm` | the *plain reactor*: CPython with every compiled package linked in |
| `python-snapshot.wasm` | the same binary after a snapshot: the interpreter already started |
| `python-stdlib.zip` | the standard library and the packages' Python code, as bytecode |
| `MANIFEST`, `SHA256SUMS` | every pinned source and recipe hash, and the hashes of the set |

The `wasi-python` wheel carries the same files, and `wasi_python.artifacts()` returns their paths. [Artifacts](../reference/artifacts.md) describes each file in detail.

## Packages are builtin modules

A normal CPython loads a package's C extension, such as numpy's core, from a shared library at import time. WASI cannot load shared libraries, so every compiled module is linked into the interpreter instead.

This works without changing the packages. CPython keeps a table of *builtin modules*, and it looks a module up there by its full dotted name, such as `numpy._core._multiarray_umath`. So when numpy's own Python code imports its C extension, CPython finds the builtin and never looks for a file. Inside the guest, `import numpy` reports `origin == 'built-in'`, and no `.so` is opened.

The build gets there through recipe files, not edits to each package's build:

- A compiler wrapper, `scripts/wasi-cc`, turns each extension module's shared-library link into a static archive. The packages' own `meson.build` files stay as they are.
- When two packages, or two copies of one C file, define the same symbol, the clash appears only in a static link. A small rename header, injected into one side, resolves it.

## The reactor and its exports

A WASI *command* is a binary with a `main` that runs once and exits. A WASI *reactor* has no `main`: the host calls `_initialize` once, then calls the functions the binary exports. (The snapshot has already run its initialization, so a host calls `_initialize` on the plain reactor only.) wasi-python's binaries are reactors, because a reactor can be snapshotted and kept alive across calls.

The exports that matter are:

- `run`: run one program, once per instance. It takes its arguments as CPython's command line does: `-c`, `-m`, a script, or `-` for stdin. It returns the exit status.
- `turn`: run one piece of code in an instance that stays alive, as a [session](sessions.md) does.
- `shutdown`: end such an instance as Python ends, running `atexit` handlers and finalizing.
- `prepare`: run code the host passes in a snapshot instance that has run nothing, then leave the instance ready to be imaged, with its preopen table cleared and its heap frozen. Each later instance starts from a copy of that memory.
- `host_alloc`: give the host space in guest memory, for a request's answer.

Every program runs in a fresh `__main__`, but a call from a starting image runs in the `__main__` its setup code ran in. Output is buffered as CPython buffers it without `-u`, so a program stopped early loses what it printed since its last flush.

## The host door

The guest has one import beyond WASI: `host::call`. Through it, guest code sends a request as bytes, and the host answers with bytes. The host writes its answer into memory it gets from `host_alloc`. The frames are opaque to wasi-python; their meaning is the embedder's.

From Python you bind the door with `run(host=...)`, a function from request bytes to response bytes. On top of the door, wasi-python ships one optional *tool protocol*: guest code writes `from host import tools` and calls the host's functions by name. See [tools](../how-to/tools.md) and the [tool protocol](../reference/tool-protocol.md).

## The snapshot

Starting CPython from nothing takes many instructions on every call. A *snapshot* does that work once, at build time. The build runs the reactor's initialization under Wizer (the pinned wasmtime's own `wasmtime wizer`), which saves the started interpreter's memory as a new binary. Each call to `python-snapshot.wasm` then starts from that saved state.

The snapshot has the interpreter started and the standard library's bootstrap modules imported: `encodings`, `io`, `os`, `sys`, `json`, `csv`, `re` and `_colorize`. It pre-imports no package. So numpy, pandas and every other package are imported in your call, with your environment, and a call pays only for what it imports. To pay for a large import once across several steps, put the steps in one call, or use a session.

Four facts follow from the snapshot:

- **Its string hash key is fixed.** Every snapshot instance hashes strings alike. The plain reactor draws a fresh key in every call. The [security model](security-model.md) says when that matters.
- **It is the same bytes on every build.** While the snapshot is made, the clocks, entropy and file metadata answer constants, so nothing about the build machine or the moment is saved. No program ever sees those constants; `run` restores the real answers before Python starts.
- **It runs only beside its own stdlib zip.** zipimport's file offsets are part of the saved state, so the snapshot's `MANIFEST` names the exact zip it was built against.
- **It finalizes as CPython does.** The bootstrap's heap starts frozen out of the garbage collector's way, and `run` undoes that freeze before finalizing, so files a program left open are flushed as in CPython.

`run(snapshot=False)` uses the plain reactor instead.

## The stdlib zip

The standard library and every package's Python code live in one deflated zip of bytecode only, built the same way on every build. The host grants it to the guest read-only, in a folder of its own at `/usr/local/lib`, so the guest finds `/usr/local/lib/python315.zip`. It is never in a writable place. matplotlib's data files travel inside the zip as one inner archive, which the runner extracts and grants read-only.

The reactor reads the zip's directory once per process and answers later imports and resource reads from that one read. The [guest filesystem](../reference/guest-filesystem.md) page lists everything the guest sees.

## The runner and the module cache

In Python, `run` and `Session` are the *runner*: they drive the binaries through wasmtime-py. For each call the runner:

1. finds the artifact set and checks it against its `SHA256SUMS`;
2. compiles the binary to native code, or loads it from the cache;
3. makes a fresh store, grants the stdlib zip and your folders, and arms the limits;
4. calls the guest on a thread of its own, with room for the guest's stack;
5. collects the output, releases the store, and removes the call's private folders.

Compiling a large wasm binary to native code is slow, so the runner keeps the compiled module as a `.cwasm` file in a cache: the user cache folder, or `$WASI_PYTHON_CACHE`. A `.cwasm` is native code tied to one wasmtime version and one CPU, so it is never published; each host compiles its own. The runner loads only files it made itself, in a folder at mode `0700` holding files at `0600`. On POSIX it reads one through the descriptor it checked, and only when every folder on the way to the cache is yours or root's and closed to other writers. `cache_dir=False` keeps the compiled module in memory only.

Fuel is counted from the end of instantiation, so a call spends the same fuel whether the module was compiled or loaded from the cache. See [fuel](fuel.md).

## In one line

One static reactor, optionally snapshotted, runs one program per instance beside a read-only zip, reaches the host only through WASI and one door, and is compiled once per host into a private cache.
