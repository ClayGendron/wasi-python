# What the prior art does, and does not

- **Status:** research, 2026-10-22. Input for the README's headline. Commits the project to nothing; the owner's questions are in section 6.
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus). It wrote none of the code. Repository only: no web search (another agent does the market). Box: about 60 minutes.
- **The question:** what does wasi-python do that each studied alternative and ingredient does not, and the reverse, stated precisely enough that a README headline can be direct and true?

## Method and labels

- **READ** is a fact taken from a file. For this repository the path is given; for a clone, the clone's name under `context/prior_art/` and the path inside it. Clone commits as studied: pyodide `6754c1f`, cpython-wasi-build `7ce0aaf`, webassembly-language-runtimes (WLR) `5a40c30` (last commit 2024-01-24), componentize-py `9ff99da`, boomslang `f1de75a`, monty `d328624`, wasi-vfs `0f4db4b`, wizer `6130150`, smolagents `96f33fa`, pydantic-ai `1640d15`, cloudflare-agents `7dd51c5`, wasmtime `2d9c19b`.
- **INFERRED** is the researcher's reasoning from what was read.
- **EXECUTED** is only `uv run python -c` against the installed package, to confirm public signatures and `defaults()`. No build, judge or guest was run.
- "Not found" means a grep of the clone's docs and sources found nothing. It is weaker than "does not have". A clone is a snapshot; a project may have moved since.
- Two earlier memos already cover the market from the web: `2026-10-17-market-research-use-cases.md` (sections 1 and 2.3) and `2026-10-17-the-runtime-for-agent-code.md`. This memo does not repeat their web claims. It checks the same names against their source.

## 1. The alternatives

### 1.1 Pyodide

- **What it is.** "Pyodide is a Python distribution for the browser and Node.js based on WebAssembly" (READ, pyodide `README.md`). A port of CPython to Emscripten with a JS/Python foreign function interface.
- **What it gives.** Full CPython; numpy, pandas, scipy, matplotlib, scikit-learn and many more as wasm wheels loaded at run time with `micropip.install` or `pyodide.loadPackage` (READ, pyodide `docs/usage/loading-packages.md`); 335 recipes, Rust ones among them (cryptography, polars, pyarrow, pydantic_core) (READ, `ls pyodide-recipes/packages`). Python code can reach JavaScript: `import js` and then the DOM (READ, pyodide `docs/usage/quickstart.md`, line 187).
- **Sandbox.** None claimed. Its own CLI says "Execution is not sandboxed, this Pyodide Python has direct access to the native file system" (READ, pyodide `docs/usage/cli.md`, line 13). No fuel, no host-set memory or output default; interrupts are cooperative, through a SharedArrayBuffer (READ, pyodide `docs/usage/keyboard-interrupts.md`). A memory snapshot exists but is private and experimental (READ, pyodide `src/js/api.ts`, `makeMemorySnapshot`, `@private`).
- **What wasi-python does that it does not.** Needs no JavaScript engine: the guest imports WASI preview1 and one door, nothing else (READ, `docs/explanation/why-wasi.md`; judged by `tests/checks/test_v1_1_artifact_set.py::test_imports_are_wasi_and_the_door_only`). Has default limits, fuel, and nothing writable by default (READ, `docs/explanation/security-model.md`). Runs in-process from Python, Rust, Go or any WASI host, not only from JS.
- **What it does that wasi-python does not.** Runs in a browser. Installs packages at run time from PyPI. Carries far more packages, Rust ones included. Has network access through the browser (READ, pyodide `docs/usage/wasm-constraints.md`, "Synchronous HTTP requests").

### 1.2 cpython-wasi-build (Brett Cannon)

- **What it is.** A release workflow that builds upstream CPython for `wasm32-wasip1` with the SDK CPython pins (READ, cpython-wasi-build `.github/workflows/release.yml`). The clone has no README to quote, only `LICENSE` and the workflow.
- **What it gives.** `python.wasm` (a WASI *command*) and the stdlib as a plain folder tree, zipped for download, to be unpacked and preopened (`wasmtime --dir . python.wasm`); plus `libpython*.a` and build files for others to link. Its only test is `python.wasm -m sysconfig`. Releases are attested with `actions/attest` (READ, same file, jobs `build`, `test`, `release`). No packages, no runner, no snapshot.
- **What wasi-python does that it does not.** Compiled packages; a reactor with `run`, `turn`, `shutdown` exports; a snapshot; a bytecode stdlib zip read in place; a runner with limits; CPython's own test suite in the guest (28,108 passes in five groups, READ, `context/roadmap.md`, spec 065 line) and every package's suite.
- **What it does that wasi-python does not.** Builds upstream CPython with zero carried patches, and builds each new CPython micro release (READ, its `workflow_dispatch` inputs). Signed provenance is common to both.

### 1.3 webassembly-language-runtimes (WLR, VMware Labs)

- **What it is.** "WebAssembly Language Runtimes (or WLR for short) offers pre-built wasm32-wasi binaries for language runtimes and static builds of common open source libraries" (READ, WLR `README.md`). Latest Python release 3.12.0, December 2023; last commit January 2024.
- **What it gives.** `python.wasm` plus `python311.zip` at `/usr/local/lib`, an `aio` flavour that packs the stdlib into the binary with wasi-vfs, a WasmEdge flavour patched for sockets, and `wlr-libpy` to link the static libpython into your own module (READ, WLR `python/README.md`, `python/v3.12.0/wlr-build.sh`, `python/tools/wlr-libpy/README.md`). No numpy or pandas anywhere in the tree (READ, grep). Dependencies fetched by URL, no hash (READ, `python/v3.12.0/wlr-info.json`).
- **What wasi-python does that it does not.** Everything past the bare interpreter: packages, snapshot, runner, limits, tests, hashes. And it is maintained.
- **What it does that wasi-python does not.** A single-file build (`aio`) with the stdlib inside the binary. wasi-python chose a read-only folder instead, because wasi-vfs's output was not byte-reproducible (READ, `context/decisions.md`, question 2).

### 1.4 componentize-py (Bytecode Alliance)

- **What it is.** "A tool to convert a Python application to a WebAssembly component" from a WIT world (READ, componentize-py `README.md`).
- **What it gives.** One component per application, pre-initialized and snapshotted with that app's code (READ, componentize-py `src/lib.rs`, lines 453 to 458), linked from `.so` libraries at build time (READ, same file, around line 724). Native packages such as numpy work if you bring a WASI build of them: its `matrix-math` example downloads "an unofficial build of NumPy" (READ, `examples/matrix-math/README.md`). Its `sandbox` example shows a 20 s timeout and a 40 MB memory cap written in the example's host (READ, `examples/sandbox/README.md`).
- **What wasi-python does that it does not.** Ships the data stack already built and tested; runs arbitrary code strings in one prebuilt artifact, not a component compiled per app; ships the runner, with defaults.
- **What it does that wasi-python does not.** The component model and WIT: typed imports and exports, WASI preview 2 and 3 (`cli-p3`, `http-p3` examples). wasi-python is preview1 only.

### 1.5 boomslang (HubSpot)

- **What it is.** "Python, but Java." It "runs CPython 3.14 from a WASI build", embedded in Java through Endive, "sandboxed, with the stdlib plus NumPy, Pandas, Matplotlib, Pillow, Pydantic, ijson, and Jinja2 included", also as a Python wheel on wasmtime and from Rust (READ, boomslang `README.md`). Maven version 0.1.1; the Python wheel is on GitHub releases, not PyPI, version `0.0.0.dev0` in the tree (READ, `boomslang-py/README.md`, `_version.py`).
- **What it gives.** The closest thing to wasi-python. Statically linked numpy 2.4.4, pandas 3.0.2, matplotlib 3.9.3, Pillow, pydantic-core (a Rust extension), lxml and ijson (READ, `cpython/*/Dockerfile` `ARG *_TAG` lines; `docs/src/guide/supported-libraries.md`). A Wizer snapshot that pre-imports numpy, pandas, matplotlib, pydantic and lxml (READ, `python-host-core/src/lib.rs`, `prewarm_stdlib`). Persistent state across `execute()`, with `reset()` to the snapshot. JSON host functions through `boomslang_host.call`, and async host functions. Limits: timeout 120 s, output 10 MiB per stream, memory defaulting to the wasm32 4 GiB cap (READ, `boomslang-py/README.md`, "Resource limits"). The Python host stops CPU-bound code with epoch interruption (READ, `boomslang-py/src/boomslang/_engine.py`); the Java host does not: "timeouts do not hard-stop Python" (READ, `docs/src/guide/lifecycle.md`).
- **What wasi-python does that it does not.**
  - Nothing writable by default. boomslang mounts `/work`, `/lib` (on `sys.path`) and `/tmp` read-write by default, and "arbitrary additional mount points are not supported" (READ, `boomslang-py/README.md`, "Filesystem").
  - Fuel; an open-files cap; a memory default below 4 GiB (not found in boomslang).
  - scipy, scikit-learn, statsmodels, regex and about 40 pure-Python packages (READ, `docs/reference/packages.md`; scipy not found in boomslang).
  - Sources pinned by URL and SHA-256 and verified. boomslang clones by git tag and pipes WLR library tarballs through `curl | tar` with no hash (READ, `cpython/numpy-wasi/Dockerfile` lines 59 and 60, `cpython/matplotlib-wasi/Dockerfile` around line 125).
  - Recorded patches. boomslang edits sources with `patch.py` scripts per package and carries one `.patch` file (READ, `cpython/numpy-wasi/patch.py`, `find -name '*.patch'`).
  - Byte-identical rebuilds, signed provenance, each package's own test suite, a Windows judge: none found. Its CI runs on `ubuntu-24.04` only (READ, `.github/workflows/build.yml`).
  - A wheel on PyPI that works with current wasmtime-py. boomslang pins `wasmtime>=36,<46` because 47 aborts compiling its binary (READ, `boomslang-py/pyproject.toml`, lines 11 to 13).
  - One door import for every host function, and a tool layer with schemas, a gate and a record. boomslang's host ABI is a set of generated imports (`call`, `log`, async control calls) (READ, `docs/src/guide/other-hosts.md`).
- **What it does that wasi-python does not.** A JVM host. pydantic, a Rust package. Pillow with common formats beyond PNG. A snapshot with the data stack already imported, so a pandas call pays no import (wasi-python chose otherwise, decision 34). Needs no exception-handling proposal: it shims `setjmp` to run on Endive, which lacks it (READ, `cpython/matplotlib-wasi/Dockerfile`, around line 136), so it runs on hosts wasi-python cannot. Bytecode caching and `execute_function` (READ, `boomslang-py/README.md`).

### 1.6 Monty (Pydantic)

- **What it is.** "A secure Python sandbox, written in Rust, for code written by AI" (READ, monty `README.md`). Not CPython: a new interpreter for a subset of Python 3.14.
- **What it gives.** Sub-millisecond sandboxes from a pool, host functions (`external_lookup`), mounts (`read-only`, `overlay` by default), an `os` callback, async, a type checker, and snapshots that pause at a host call and serialize the interpreter to kilobytes (READ, `docs/alternatives.md`, `docs/filesystem.md`). Python, JS and Rust packages; Windows.
- **What it cannot run.** "No class inheritance, limited stdlib, no third-party libraries" (READ, `docs/alternatives.md`, "OSS Monty"); class inheritance, method decorators and generators are rejected at parse time (READ, `docs/limitations/index.md`). So no numpy or pandas.
- **Its limits.** Memory, execution time and recursion, "off unless you set them" (READ, `docs/alternatives.md`). Time counts execution time, not instructions; "there is no cumulative per-session budget" in OSS Monty (READ, `docs/resource-limits.md`, "Time"). Idle and session timeouts exist only in the commercial server (READ, `docs/server.md`, lines 149 to 151).
- **Its view of us.** Its table rates "WASI / wasmtime" "partial, almost full", security "strict", 16 ms, and notes "packages with C extensions need their own WASI build" and that `python.wasm` "is a WASI command module whose `_start` runs once" (READ, `docs/alternatives.md`, "WASI / wasmtime" and "Latency"). wasi-python answers both: the C extensions are built, and the reactor's `turn` export keeps a session (READ, `docs/explanation/how-it-works.md`) (INFERRED).
- **What it does that wasi-python does not.** Starts about 20 times faster from a pool; pauses mid-run and resumes elsewhere; type-checks code before it runs; ships to npm.

### 1.7 How the agent frameworks run generated code

- **smolagents.** Executors `local`, `blaxel`, `e2b`, `modal`, `docker` (READ, smolagents `src/smolagents/agents.py`, line 1516). The local one is an AST interpreter that "is not a security sandbox" (READ, `local_python_executor.py`, line 1693; `SECURITY.md`, line 80). The rest are remote services or containers. No wasm executor in this clone (READ, grep).
- **pydantic-ai.** Code mode runs on Monty (READ, pydantic-ai `src/pydantic_ai_harness/README.md`, line 222; `THREAT_MODEL.md`, line 156).
- **cloudflare-agents.** Code mode runs model-written TypeScript in a Worker isolate, or an iframe in the browser, with no network; tools are RPC "connectors" (READ, cloudflare-agents `docs/codemode/index.md`, lines 3, 33, 37). Not Python.
- **What follows (INFERRED).** None of the three has an in-process, sandboxed, full-CPython executor with the data stack. Each picks a service, a container, a Python subset or another language. That is the gap wasi-python fills.

## 2. The ingredients, and what the project adds

| ingredient | what it gives for free (READ) | what wasi-python adds (READ) |
|---|---|---|
| wasmtime | `Config::consume_fuel` ("By default this option is `false`"), `epoch_interruption`, `StoreLimitsBuilder::memory_size` ("By default, linear memory will not be limited") (wasmtime `crates/wasmtime/src/config.rs` line 627 on; `runtime/limits.rs` line 251) | the defaults (1 GiB, 60 s, 16 MiB per stream, 1,024 open files, 10,000 file calls, 1,000 tool calls; EXECUTED, `wasi_python.defaults()`), a deadline that also holds while the guest sleeps or waits in `select`, the recursion stack, refusal of bad limit types, cleanup, and two advisory fixes for 49.0.0 applied in the runner (`docs/explanation/security-model.md`) |
| wizer (now `wasmtime wizer`) | "The WebAssembly Pre-Initializer!"; moved into wasmtime (wizer `README.md`, line 34) | a snapshot that is the same bytes on every build (clocks, entropy and metadata held constant while it is made) and pre-imports no package (`docs/explanation/how-it-works.md`, "The snapshot") |
| wasi-vfs | "A virtual filesystem layer for WASI", read-only, embedded in the binary (wasi-vfs `README.md`) | not used: rejected for non-reproducible output and start-up cost (`context/decisions.md`, question 2); the zip is a read-only grant instead |
| wasi-sdk | the compiler, wasi-libc and the exception-handling sysroot (`context/prior_art/README.md`) | every compiled package and its C and C++ libraries linked as builtins through a compiler wrapper (`scripts/wasi-cc`); 27 recorded patches across 18 packages (`recipes/patches/`) |
| wasmtime-py | `Linker.define_func`, `Module.deserialize_file` | the whole runner: `run`, `run_async`, `Session`, grants, mounts, tools, the `.cwasm` cache at `0700`/`0600`, the CLI (`src/wasi_python/__init__.py`, `__all__`) |

The point for a headline (INFERRED): wasmtime gives the *mechanisms*; none is on by default. wasi-python's contribution on the host side is that every one is on by default, and that the guest it runs has the data stack in it.

## 3. The feature matrix

Cells: **yes**, **no**, **part** (partial), or **n/f** (not found). "—" means the column has no runner, so the row is the host's choice. Paths for wasi-python are in section 3.1; for the others they are in section 1.

| feature | wasi-python | Pyodide | cpython-wasi-build | WLR | boomslang | Monty |
|---|---|---|---|---|---|---|
| full CPython | yes, 3.15 | yes | yes, 3.15 | yes, 3.12 (2023) | yes, 3.14 | no, a subset |
| numpy and pandas | yes | yes, loaded | no | no | yes | no |
| scipy, scikit-learn, statsmodels | yes | yes, loaded | no | no | n/f | no |
| no JavaScript engine needed | yes | no | yes | yes | yes | yes |
| one static binary, packages builtin | yes | no (dynamic wheels) | stdlib only | stdlib only | yes | — |
| build-time snapshot | yes, no package imported | part, private | no | no | yes, packages imported | other kind (mid-run) |
| stdlib as a read-only bytecode zip | yes | no | no (a folder) | yes (or packed) | no (a folder) | — |
| limits on by default | yes: memory, deadline, output, open files | no | — | — | part: timeout, output | no, off unless set |
| fuel, an instruction count | yes | no | — | — | no (epoch) | no (execution time) |
| nothing writable by default | yes | no | — | — | no (`/work`, `/lib`, `/tmp`) | yes |
| grants, read-only or writable, any path | yes | part (NODEFS, JS) | — | — | part (fixed paths) | yes (MountDir) |
| one host import for all host calls | yes | no (`import js`) | — | — | no (several) | — |
| tool protocol: schemas, gate, record | yes | no | no | no | part (name + JSON) | part (host functions, stubs) |
| sessions with idle timeout and lifetime | yes | no | no | no | part (no bounds) | part (server only) |
| async host functions | yes | yes | no | no | yes | yes |
| filesystem provider in host code | yes | part (JS FS) | no | no | n/f | yes (`os` callback) |
| one-line JSON CLI | yes | no | no | no | no | part (CLI, not JSON) |
| byte-identical rebuilds across hosts | yes | n/f | n/f | n/f | n/f | — |
| signed provenance | yes | n/f | yes | n/f | n/f | n/f |
| each package's own tests in the guest | yes, 54 suites | part (CPython's) | no | n/f | no | — |
| inputs pinned by SHA-256 | yes | n/f | no (git ref) | no | no (git tag, curl) | n/f |
| carried-patch rule, release fails on drift | yes | part (patch dir) | n/a, no patches | part | no | — |
| hosts | wasmtime (judged); others read | browser, Node | WASI hosts | wasmtime, WasmEdge | JVM, wasmtime | native |
| Windows judged each release | yes | — | n/f | n/f | no (Linux CI) | yes (docs) |

**The rows only wasi-python has** among these six: fuel; limits on by default for all four of memory, deadline, output and open files; a tool protocol with schemas, a gate and a record over one import; sessions bounded by idle and lifetime in the open-source runner; byte-identical rebuilds; each package's own suite in the guest; the hashed-pin and recorded-patch rule; a Windows judge. scipy, scikit-learn and statsmodels compiled in, sandboxed and embeddable, are also unique to it (Pyodide has them, but without a sandbox and with a JS host).

### 3.1 The evidence for each wasi-python row

| feature | proof (READ) | explained in |
|---|---|---|
| one static binary | `tests/checks/test_v1_2_portable_and_sealed.py` (origins are `built-in`) | `docs/explanation/how-it-works.md` |
| the snapshot | `docs/reference/artifacts.md`; `MANIFEST`'s `x-preimport` line | `docs/explanation/how-it-works.md` |
| the stdlib zip | `docs/reference/artifacts.md` | `docs/reference/limitations.md`, "What the stdlib zip means" |
| default limits | `src/wasi_python/__init__.py` (`defaults()`); EXECUTED: `Defaults(memory_bytes=1073741824, deadline_s=60.0, output_bytes=16777216, …, open_files=1024, session_idle_s=900.0, session_lifetime_s=3600.0, …)` | `docs/explanation/security-model.md` |
| fuel | `run(..., fuel=)` signature (EXECUTED) | `docs/explanation/fuel.md` |
| grants, nothing writable | `Grant(host, guest, *, writable=False)` (EXECUTED); `run(root=False)` default | `docs/how-to/grants.md`, `docs/explanation/design-decisions.md` |
| one door import | `tests/checks/test_v1_1_artifact_set.py::test_imports_are_wasi_and_the_door_only` | `docs/explanation/why-wasi.md` |
| tools | `src/wasi_python/tools.py` `__all__` (`tool`, `ToolCall`, `ToolDenied`, `ToolRecord`, `stubs`) | `docs/how-to/tools.md`, `docs/reference/tool-protocol.md` |
| sessions | `Session(..., idle_s, lifetime_s, shutdown_s)` (EXECUTED) | `docs/explanation/sessions.md` |
| async host functions | `src/wasi_python/_tool_host.py` (awaitables on the tool loop), `_places.py` line 257 | `docs/how-to/async.md` |
| filesystem provider | `Mount`, `FileProvider`, `WritableFileProvider` in `__all__` | `docs/how-to/mounts.md` |
| JSON CLI | `src/wasi_python/cli.py` | `docs/how-to/embed-from-other-languages.md`, `docs/reference/cli.md` |
| same bytes, provenance | `.github/workflows/release.yml` jobs `same-bytes` (line 364) and `attest` (line 2333) | `docs/reference/artifacts.md`, `docs/how-to/verify-a-download.md` |
| own test suites | `tests/upstream/packages.toml`: 70 components, 54 `suite`, 14 `via`, 2 `build-only`, 0 `later` | `docs/explanation/pinned-releases-and-patches.md` |
| carried patches | `recipes/patches/`: 27 `.patch` files across 18 packages | `docs/explanation/pinned-releases-and-patches.md` |
| hosts | `docs/how-to/embed-from-other-languages.md`, "Pick an engine": only wasmtime 49 is run; the rest is read from release notes and source; no other host appears in `tests/` (grep) | same page |
| Windows | `.github/workflows/release.yml` `judge-windows` on `windows-2025`, six shards (line 1479) | `docs/reference/limitations.md`, "On Windows" |

## 4. The honest list: what the alternatives do that wasi-python does not

1. **Runs in a browser.** Pyodide does; wasi-python has no Emscripten build, by rule (constitution §3, §4.3).
2. **Installs packages at run time.** Pyodide's `micropip` installs any pure-Python wheel from PyPI. wasi-python has no pip in the guest; pure-Python code comes only from a read-only `import_path=` grant, and a compiled package means a new build (`docs/reference/packages.md`).
3. **Carries more packages, and Rust ones.** Pyodide: 335 recipes with pyarrow, polars, cryptography and pydantic. boomslang: pydantic. wasi-python: no Rust package, no pyarrow (so no Parquet), no cryptography (so no AES in pypdf) (`docs/reference/limitations.md`).
4. **Starts much faster.** Monty: under 1 ms from a pool. wasi-python: about 16 ms on the snapshot, and `import pandas` costs 4.66 billion instructions per call, because the snapshot pre-imports no package (`docs/explanation/performance-and-size.md`). boomslang pre-imports the stack, so its pandas call pays no import.
5. **Runs on hosts without exception handling.** boomslang shims C++ and `setjmp` to run on a JVM engine without it. wasi-python needs the exception-handling proposal: no WAMR, wasmi, wasmer-python, wasmer-go or Winch (`docs/how-to/embed-from-other-languages.md`).
6. **A JVM host.** boomslang's primary host is Java. wasi-python reaches Java only through the CLI subprocess or a JVM wasm engine with exception handling, and none is listed.
7. **Network.** Pyodide in a browser fetches through the browser; WLR has a WasmEdge sockets flavour. wasi-python has none, by design; data comes through grants, mounts, stdin or tools.
8. **Threads and native speed.** No column has threads; wasi-python is 1.3 to 2.3 times slower than native on compute, with 32-bit default integers (`docs/reference/limitations.md`). Monty is not comparable (no numpy).
9. **Pause and resume mid-run.** Monty serializes a paused interpreter to kilobytes and resumes it elsewhere. A wasi-python session ends with its process (`docs/explanation/sessions.md`).
10. **The component model and WASI preview 2.** componentize-py targets them; wasi-python is preview1 with one custom import.
11. **Size.** The wheel is 98.3 MB; Monty's download is about 4.5 MB (READ, monty `docs/alternatives.md`; `docs/explanation/performance-and-size.md`).
12. **Hosts judged.** wasi-python's other hosts (WasmEdge, wasmer, wazero, Node) are read from release notes, not run by the judge. A headline that names them should say "should run" or keep them out (INFERRED).
13. **Upstream as is, new micro releases.** cpython-wasi-build carries no patch and builds each CPython micro release; wasi-python carries 27 patches and builds a few pinned sets.

## 5. In one paragraph each

**What wasi-python is.** From the evidence: a CPython 3.15 interpreter compiled once for `wasm32-wasip1`, with numpy, pandas, scipy, scikit-learn, statsmodels, matplotlib, lxml and regex linked into the binary as builtin modules and about 40 pure-Python packages in a read-only bytecode zip; a build-time snapshot; and a small Python runner that executes it in-process under wasmtime with every limit on by default, nothing writable by default, fuel as a portable work cap, host tools over one import, and bounded sessions. Its artifacts are rebuilt to the same bytes on three build hosts, signed, and released only after CPython's and every package's own test suite pass inside the guest on Linux, macOS and Windows.

**Who it is for.** A developer who must run Python that nobody reviewed, typically code a model wrote, against data, inside their own process: an agent framework's code tool, a data product that lets users script, an evaluation harness that needs the same cost on every machine. They need pandas or scipy, cannot use a browser or a JS engine, do not want a container or a hosted sandbox per call, and want the guarantee to come from the build, not from their own wasmtime configuration (INFERRED from sections 1.7 and 3).

**The one thing nothing in the clones does.** Run the scientific Python stack, compiled in and tested by its own suites, inside a capability sandbox that is closed by default: no JavaScript host, no writable path, no channel but one import, and a limit on every resource before the caller names one. Pyodide has the stack without the sandbox. Monty has the sandbox without the stack. boomslang has the stack and a sandbox, but opens three writable folders by default, has no instruction cap, and no reproducible, signed, suite-tested release (INFERRED from section 3).

## 6. Questions for the owner

1. **The 16 ms figure.** Monty quotes 16 ms for "WASI / wasmtime" with a precompiled `.cwasm`; our own number is also 16 ms on the snapshot. Should the README state it beside Monty's 0.8 ms, or keep speed out of the headline (constitution §3: "Performant, not the fastest")?
2. **The hosts line.** Only wasmtime is judged. Should the headline say "any WASI host with exception handling" (true by reading) or "wasmtime, and others that support exception handling" (true by running)?
3. **Naming alternatives.** Is a comparison table naming Pyodide, boomslang and Monty wanted in the README, or only on a docs page? boomslang is a real company's project at 0.1.1; a table dated and sourced to its own README would be fair, but it ages.
4. **A pre-imported profile.** boomslang's snapshot pre-imports pandas, which makes its pandas call cheap. Decision 34 rejected that for the default set. Is a second artifact set with the data stack pre-imported worth a roadmap line, given that start cost is the honest list's item 4?
5. **The JVM.** boomslang's primary host is Java. Is a tested JVM path (a JVM wasm engine with exception handling) in scope after 0.1.0?

## One line

wasi-python is the only studied project that runs the full CPython data stack in a sandbox closed by default, metered by fuel, rebuilt to the same bytes and tested by every package's own suite; Pyodide has the stack without the sandbox, Monty the sandbox without the stack, and boomslang the stack with open defaults and no reproducible release.
