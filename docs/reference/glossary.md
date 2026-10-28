# Glossary

The terms these pages use, in alphabetical order. Each entry links to the page that explains it in full.

**Artifact set.** The files a release ships: `python.wasm`, `python-snapshot.wasm`, `python-stdlib.zip`, `MANIFEST` and `SHA256SUMS`. See [Artifacts](artifacts.md).

**Door.** The guest's one way to call the host: a single host function, bound to the guest's `host` module, that takes request bytes and returns response bytes. You pass it to `run` as `host=`, or let the tool protocol use it through `tools=`. See [Tool protocol](tool-protocol.md).

**Fuel.** A count of the guest's executed instructions. A `fuel` cap stops a run after that many instructions, and `fuel_used` reports how many ran. Because fuel counts operations and not time, a limit is the same on every machine. See [Fuel](../explanation/fuel.md).

**Grant.** A host folder you hand to the guest at a guest path, with `Grant(host, guest)`. A grant is read-only unless you pass `writable=True`. See [Grants](../how-to/grants.md).

**Guest.** The Python program running inside `python.wasm`, in the sandbox. The *host* is the program that runs it, such as your Python process through `run`.

**Mount.** A folder in the guest whose files your own code serves. The guest uses ordinary calls such as `open` and `os.listdir`, and your provider answers each one. See [Mounts](../how-to/mounts.md).

**Preopen.** A host directory handed to a WASI guest at a guest path when it starts. WASI gives a guest no file access except through preopens. The stdlib zip, every grant and every mount reach the guest as preopens.

**Provider.** The object you write to serve a mount. It answers calls such as `stat`, `list` and `read` for paths inside the mount. See [Mounts](../how-to/mounts.md).

**Reactor.** A WASI module that the host initializes once and then calls into, instead of one that runs a single `main`. `python.wasm` is a reactor: the host calls `_initialize`, then one `run` per instance. See [How it works](../explanation/how-it-works.md).

**Root.** The guest's `/`. By default the guest has no writable `/`. `root=True` gives a call a fresh private folder as its `/`, removed afterwards; `root=` a path gives it that host folder. See [Grants](../how-to/grants.md).

**Session.** One instance of the runtime kept across several calls, each a *turn*. Variables, functions and imports made in one turn are there in the next. See [Sessions](../how-to/sessions.md).

**Snapshot.** Two things share the word. The set's snapshot binary, `python-snapshot.wasm`, is `python.wasm` after the interpreter has started and the stdlib's bootstrap modules are imported, saved with Wizer at build time; it pre-imports no package, and a call on it skips the interpreter's start-up. See [How it works](../explanation/how-it-works.md). A `Snapshot` you make with `make_snapshot` or `make_package_snapshot` is the guest's memory after your own code ran once in that binary; a call given it starts from a private copy of it. See [Start every call from a snapshot](../how-to/snapshots.md).

**Stdlib zip.** `python-stdlib.zip`: the standard library and the Python code of every package in the set, as bytecode in one zip. Every call sees it read-only at `/usr/local/lib`. See [Guest filesystem](guest-filesystem.md).

**The judge.** The project's test suite, run with `uv run pytest`. It judges every check and prints a scoreboard of passes, known gaps, blocked checks and failures. See [Your first change](../contributing/first-change.md).

**Turn.** One call to a session's `run`. See [Sessions](../how-to/sessions.md).

**WASI.** The WebAssembly System Interface: the operating-system interface a WebAssembly module uses for files, the clock, arguments and standard output. See [Why WASI](../explanation/why-wasi.md).
