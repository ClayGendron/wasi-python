# Prior art

Shallow clones of the projects this one learns from. They live here so
a study can grep them in place; git ignores everything in this
directory except this index. **Read-only. Study, cite, describe; never
copy code.** Building a dependency from its released tarball (the
`downloads/` pins) is a different thing from this directory.

Refresh a clone before studying it (`git fetch --depth 1 origin && git
reset --hard FETCH_HEAD` inside it), re-check its licence, and record
the commit in the memo that cites it.

| clone | what we study in it | licence | cloned 2026-10-16 at |
|---|---|---|---|
| `cpython` (branch 3.14) | `Tools/wasm/wasi`, `Modules/makesetup`, `Modules/getpath.py`, `Python/import.c` (`is_builtin`) | PSF-2.0 | 7c04882 |
| `cpython-wasi-build` | Brett Cannon's release recipe and the SDK pin per Python line | MIT | 7ce0aaf |
| `pyodide` | the Emscripten shape of the same problem; the numpy recipe and its cross-build files | MPL-2.0 | 6754c1f |
| `pyodide-recipes` | package recipes: matplotlib (C++ exceptions, five patches), scipy (f2c, OpenBLAS), pandas | MPL-2.0 | 01bd0af |
| `wasi-sdk` | the toolchain releases; `CppExceptions.md`; the SDK-33 exception sysroot | Apache-2.0 with LLVM exception | 2b65040 |
| `wasi-libc` | the preview1 libc: the preopen table, `-lc-printscan-long-double`, the emulated signal/clock/getpid | Apache-2.0 / MIT (see its LICENSE) | 165235b |
| `wizer` | snapshotting: init function, `--mapdir`, why a reactor is needed | Apache-2.0 with LLVM exception | 6130150 |
| `wasmtime` | the host: epoch interruption, fuel, store limits, `.cwasm` serialization | Apache-2.0 with LLVM exception | 2d9c19b |
| `wasmtime-v49` (tag `v49.0.3`, cloned 2026-10-17) | the release our runner uses: the module startup function, `memory_init_per_byte`, the copy-on-write memory image (`cow.rs`, `sys/*/vm.rs`) | Apache-2.0 with LLVM exception | f96eaba |
| `wasmtime-py` | the Python embedding our runner uses: `Linker.define_func`, `Module.deserialize_file` | Apache-2.0 with LLVM exception | 280ce73 |
| `componentize-py` | the link-time precedent for putting extension modules into one binary | Apache-2.0 with LLVM exception | 9ff99da |
| `webassembly-language-runtimes` | the WLR Python builds that embed the stdlib with wasi-vfs | Apache-2.0 | 5a40c30 |
| `numpy` | `meson.build`, `meson_cpu` (wasm32 family), `random/meson.build` (the double build of `distributions.c`) | BSD-3-Clause | ac61120 |
| `pandas` | `meson.build` (`_cyutility`), the unconditional `ctypes` and `mmap` imports | BSD-3-Clause | 3ce0a8c |
| `wasi-virt` | virtualizing a component's filesystem; the post-preview1 direction | Apache-2.0 with LLVM exception | 448f6df |
| `wasi-vfs` | a read-only file tree packed into a preview1 module: link-time override of wasi-libc's WASI imports, `pack` as a Wizer run | Apache-2.0 (`LICENSE`; `Cargo.toml` says Apache-2.0 WITH LLVM-exception) | 0f4db4b (v0.6.3) |
| `openblas` (`develop`, cloned 2026-10-17, deepened to 470 commits) | C LAPACK's one return convention (pull requests #6008 to #6082), `ctest.c`, `common.h`, `driver/others/memory.c` | BSD-3-Clause | 0fee0ebe |
| `ninja` (cloned 2026-10-17) | build progress: `src/line_printer.cc` (smart terminal, `NO_COLOR`), `src/status_printer.cc` (`NINJA_STATUS`, ETA from the previous run's `.ninja_log`) | Apache-2.0 (`COPYING`) | 48bfd165 |
| `cargo` (cloned 2026-10-17, sparse) | build progress: `src/util/progress.rs` (the `Building [==>  ] n/N` bar, its throttle, OSC 9;4), `crates/cargo-util-terminal/src/shell.rs` (`progress_supported`), `crates/cargo-util/src/lib.rs` (`is_ci`) | MIT OR Apache-2.0 | 3022244f |
| `uv` (cloned 2026-10-17, sparse) | build progress: `crates/uv-command-support/src/{printer,progress}.rs` (indicatif spinners and bars; plain lines when hidden), `crates/uv-install-operations/src/reporters.rs` | MIT OR Apache-2.0 | 968598af |
| `buildkit` (cloned 2026-10-17, sparse) | build progress: `util/progress/progressui/` (auto, tty, plain, rawjson, quiet; the rolling log tail; the error-log replay) | Apache-2.0 | 64aefaef |
| `brew` (cloned 2026-10-17, sparse) | build progress: `utils/output.rb` (`==>`), `utils/tty.rb` (colour, synchronized update), `download_queue.rb` (spinner, per-download bars), `env_config.rb` (`NO_EMOJI`, `INSTALL_BADGE`) | BSD-2-Clause | 013821de |
| `pnpm` (cloned 2026-10-17, sparse) | build progress: `pnpm/crates/cli/src/cli_args/reporter.rs` (default, append-only, ndjson, silent), `pnpm/crates/default-reporter/src/` (append-only off a terminal, ten-line lifecycle tail) | MIT | e7cfcbb2 |
| `langchain` (cloned 2026-10-17, sparse: `libs/core/langchain_core/{tools,messages,utils}`) | the tool API: `@tool`, `BaseTool`, `StructuredTool`, `args_schema`, `tool_call_schema`, `ToolException` and `handle_tool_error`, `ToolMessage`, sync and async tools | MIT | bd5b134d |
| `monty` (pydantic/monty, cloned 2026-10-17) | host functions in a sandboxed interpreter: `external_lookup`, `ExternalModule` with `.pyi` stubs, suspensions (`feed_start`), async futures, `max_suspensions`, the `monty-proto` wire (`crates/monty-proto/proto/monty/v1/monty.proto`) | MIT | d3286243 |
| `mcp-spec` (modelcontextprotocol/modelcontextprotocol, cloned 2026-10-17, sparse: `schema/2025-11-25`, `schema/2026-07-28`, `docs/specification/2025-11-25/{basic,server}`, `docs/specification/2026-07-28`) | the Tool object, `tools/list` and `tools/call`, `isError` against protocol errors, progress, cancellation, tool names | Apache-2.0 for new code and specification, MIT for earlier contributions, CC-BY-4.0 for other docs (`LICENSE`, in transition) | 86f6e0c6 |
| `cloudflare-agents` (cloudflare/agents, cloned 2026-10-17, sparse: `packages/codemode/src`, `docs/codemode`) | code mode: TypeScript types generated from tool schemas, the `ToolDispatcher` RPC back to the host, approval by replay | MIT | 7dd51c51 |
| `smolagents` (huggingface/smolagents, cloned 2026-10-17, sparse: `src/smolagents`) | `@tool` and `Tool`, how the code agent's tools reach generated code, the remote executors that ship tool source into the sandbox | Apache-2.0 | 96f33faa |
| `pydantic-ai` (pydantic/pydantic-ai, cloned 2026-10-17, sparse: `pydantic_ai_slim/pydantic_ai`, `src/pydantic_ai_harness/pydantic_ai_harness`) | schemas from type hints and docstrings, `ModelRetry`, approval and deferred tools, the harness's code mode on Monty | MIT | 1640d152 |
| `boomslang` (HubSpot/boomslang, cloned 2026-10-18) | lxml for `wasm32-wasip1`: `cpython/lxml-wasi/` (libxml2 and libxslt configured static with no threads, modules or zlib; the sdist's generated `etree.c` and `objectify.c` compiled directly; a libxml2 change for WASI's missing `dup()`), and how its builtins table names `lxml.etree` and `lxml.objectify` | Apache-2.0 (`LICENSE`) | f1de75a |

Removed: `bashkit` (everruns/bashkit; no licence file in the clone).
Its Wizer snapshot of CPython 3.14 and its HTTP door are studied
through its public README only.
