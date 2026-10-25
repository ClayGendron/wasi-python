# Architecture summary: wasi_python (run-1, 2026-10-24)

## 1. Product, principals, authority, protected resources

wasi_python is a sandbox for running untrusted Python: a statically linked CPython 3.15 for `wasm32-wasip1` with numpy, pandas, scipy, scikit-learn, statsmodels, matplotlib and lxml compiled in. It ships an artifact set (`python.wasm`, `python-snapshot.wasm`, `python-stdlib.zip`, `MANIFEST`, `SHA256SUMS`) and a Python wheel `wasi-python` whose runner (`src/wasi_python/`) drives the set under wasmtime-py 49.0.0. Embedders call `run`, `run_async` or `Session`, or the `wasi-python` CLI. Releases are built, attested and published by GitHub Actions.

Principals, lowest trust first:
- **The guest**: untrusted Python inside the wasm. By design it has WASI preview1 on its preopens, one imported door `host::call`, no network, no processes, no threads, nothing writable unless granted.
- **A previous call's leftovers** on a reused root or writable grant (data may persist; code must never run at start-up or on import).
- **The tool-calling model** driving a Session: each turn is untrusted; one session is one trust domain.
- **Another OS user** sharing the temp folder or the machine; **another process of the same user** is trusted for the module cache.
- **A fork PR author**: only `docs.yml` runs on pull requests, read-only.
- **The embedder**: trusted, but its arguments (`argv`, `env`, `stdin`, `root`, grants, mounts, `host=`, `tools=`, limits, `cache_dir`, `artifacts=`) are checked so none silently removes a limit or changes what the guest sees.

Protected resources: the host filesystem outside root/grants; host memory and the host process; the embedder's other calls' results and state; the module cache (native code loaded into the process); the artifact set's integrity; the release's signing and publishing authority; the limits (deadline, fuel, memory, output, open files, tool budget).

## 2. Comparable baseline

Pyodide (Emscripten) is the explicit contrast (`docs/explanation/why-wasi.md`); hosted microVM sandboxes are in `context/research/2026-10-17-market-research-use-cases.md`. The shared defect pattern that has mattered is a guest reaching host authority through a host-provided bridge (the Pyodide `ctypes` escape), which puts the door, mount providers and module cache first.

## 3. Stack, deployment paths, offline limits

Host runner: Python >= 3.11, `wasmtime>=49,<50` (uv.lock: 49.0.0, which lacks the 49.0.2/49.0.3 fixes, so the runner carries them). Build: POSIX sh steps, wasi-sdk 34, meson/ninja/Cython, a pinned host CPython; every input pinned in `downloads/SHA256SUMS`. Packaging: hatchling, uv. Deployments: PyPI wheel (CLI `wasi-python`), GitHub release assets, bring-your-own-host. CI: Linux x86-64/arm64, macOS arm64, Windows.

Locally: `.venv` holds wasmtime-py 49.0.0 and an editable install; `build/artifacts/` holds the set; wasi-sdk 34 (`llvm-objdump`, `llvm-nm`) and wasmtime CLI 49.0.3 are under `build/tools/`; no `wasm-tools`. Prohibited: `uv sync`/plain `uv run`, `scripts/00_download.sh`, `scripts/build.sh` and steps, `release/set_key.py`, `gh workflow run`, tag pushes, `pytest --accept*`, writes under `context/`. Use `.venv/bin/python -I`; redirect `WASI_PYTHON_CACHE` and `TMPDIR` to scratch. macOS enforces `env -i`, `sandbox-exec (deny network*)`, scratch-only writes, CPU/file/descriptor rlimits; not memory rlimits or disk quotas; wall-clock via `subprocess.run(timeout=)`.

## 4. Entry surfaces and source-to-sink paths

- **WASI calls** (`src/wasi_python/_call.py:937-990`): without mounts, the guard linker shadows `fd_readdir`, `path_rename` (GHSA fixes, `_fs_paths.py:543-598`, `_fs_descriptors.py:360-482`) and `path_open`/`fd_close`/`fd_renumber` (open-file cap); with mounts, all 29 calls (`_fs_memory.py:20-50`) go through the runner's VFS and a trampoline (`_fs_table.py:212-264`, `_wasmtime_ffi.py:363-400`). `path_link`, `path_symlink`, `path_readlink`, `args_get`, `environ_get`, `random_get`, `clock_*`, `sock_*` are wasmtime's own. `poll_oneoff` is sliced to the deadline (`_call.py:1082-1174`); stdout/stderr go through a ctypes callback into capped buffers (`_call.py:1023-1041, 1177-1190`).
- **The door** (`_call.py:1226-1282`): guest supplies `ptr,len,out_ptr_ptr,out_len_ptr`; bounds `ptr+len > size`; answer buffer from the guest's exported `host_alloc` (re-entrant guest code inside a host function); answer capped at `MAX_RESPONSE`; a raw `host=` runs on the home thread with no gate or budget; exceptions become `HOST_FAULT` with no text. Guest side: `recipes/hostmodule.c`.
- **Tool frames** (`_tool_host.py`): `admit` (count, 1 MiB frame, byte budget) before read; bounded JSON parse; schema validation (`_tool_schema.py:449-627`); gate (fail-closed) on a deep copy; sink `t.fn(**args)` on a `_Bounded` thread or `_ToolLoop`; explicit schemas without `properties` are open.
- **Embedder arguments** (`runner.py:540-611`, `_limits.py:29-154`, `_places.py:72-271`): type/range checks; `env=` may override `HOME`/`TMPDIR`; `artifacts=` skips the SHA256SUMS check.
- **Sessions** (`_sessions.py`): turn code via `host_alloc` + `turn` export; memory and file table persist across turns; reaper for idle/lifetime.
- **Grant judge and preopens** (`_places.py:330-500`, `_platform.py:312-375`): no-follow component walk, links in user-writable folders refused, refused places (temp folder at-or-above, runtime folders, module caches), post-open inode identity check (skipped when identity is None); `/usr/local/lib` and `/tmp` made under the root with `real_dir`.
- **Private folders** (`_private_dirs.py`, `_zip.py`, `_call.py:292-371`): roots, stdin, zip copy and fresh HOME under `tempfile.gettempdir()`, 0700, lock files with kernel identity, a sweep that removes dead ones, `remove_tree` that never follows links.
- **Module cache** (`_engines.py:130-275`, `_platform.py:556-579`): `.cwasm` native code; owner/mode/nlink checks; load then stamp re-check (window narrowed, not closed); mkstemp + replace writes.
- **Artifact set** (`_artifacts.py:62-84, 181-220`): `$WASI_PYTHON_ARTIFACTS` > checkout `build/artifacts` > wheel copy; integrity against the folder's own SHA256SUMS.
- **CLI** (`cli.py`): grants split at first `=`, `--env KEY` copies from the host env, stdin read whole, raises `RLIMIT_NOFILE`.
- **Build** (`scripts/00_download.sh`, `scripts/steps/common.sh#pinned`, `apply_patches.sh`, `tar -xf`, `zipfile.extractall`, `uv pip install --require-hashes`).
- **Release** (`.github/workflows/release.yml`, 2,602 lines; `set-cache.yml`; `docs.yml`): tag push or dispatch; `permissions: {}` top level; artifact handoff by id with `digest-mismatch: error`; branch dispatch may restore a cached set verified by `release/set_key.py verify` against its own SHA256SUMS; `attest` (id-token) on tag push without an environment gate; `publish` in environment `release`; `pypi` behind `vars.PYPI_PUBLISH`; `docs.yml` deploys on any dispatch from any ref.

## 5. Trust boundaries and strongest controls

| Boundary | Strongest source-visible control |
|---|---|
| Guest to host filesystem | wasmtime preopens + guard linker; grant judge walk (`_platform.py:312-375`); `_judge` (`_places.py:330-381`) |
| Guest to host memory/process | wasm linear memory; pointer checks in `_door`, `poll_oneoff`, `_fs_memory`; `_shared` stack-top check (`_call.py:711-772`) |
| Guest to embedder authority | tool admission, schema, gate (`_tool_host.py:836-1027`); raw door has none by design |
| Call to call | per-call store, output keys, private folders; judge refuses runtime folders; `site` off; import path read-only (`_places.py:176-227, 503-523`) |
| Same-user process to native code | cache `private()` checks (`_platform.py:556-579`), 0600 files |
| Build inputs to artifact | `downloads/SHA256SUMS` + `pinned()`; `apply_patches.sh` |
| Build to publish | artifact id + digest handoff; tag-on-main check; environments |

## 6. Starting paths

`src/wasi_python/{_call,_fs_paths,_fs_table,_fs_descriptors,_fs_memory,_places,_platform,_private_dirs,_home,_zip,_engines,_artifacts,_wasmtime_ffi,_process,_tool_host,_tool_schema,tools,_sessions,_limits,runner,cli,mounts}.py`; `recipes/hostmodule.c`, `recipes/reactor_main.c`; `scripts/00_download.sh`, `scripts/steps/{common,apply_patches,10_tools,20_cpython,60_link,70_zip,80_snapshot,90_artifacts}.sh`, `scripts/make_stdlib_zip.py`, `scripts/assemble_artifacts.py`; `release/{set_key,version,licences}.py`, `release/build-constraints.txt`; `.github/workflows/{release,set-cache,docs}.yml`; `build/artifacts/*`.

## 7. Prior coverage

No compatible prior ledger. The project's own review `context/reviews/0.1.0-security-review-2026-10-21.md` (two Highs, since fixed by specs 113 and 114) is background only; nothing is carried or excluded from hunting on its account. Documented "not protected" items (`docs/explanation/security-model.md:67-109`) are intended behaviour, not findings, unless a hunter shows a stronger effect than documented.

## 8. Companion selection

- `MEMORY-SAFETY-AND-BINARY.md`: the runner reads and writes guest memory through wasmtime-py's private API and ctypes; loads native `.cwasm`; the artifacts are a binary under a JIT.
- `SUPPLY-CHAIN-AND-RELEASE.md`: pinned downloads, patches, CI, attestation, publishing, cache reuse.
- `DATA-ISOLATION-AND-LIFECYCLE.md`: per-call and per-session state, reused roots, derived copies (zip copy, cache, output buffers).
- `RESOURCE-EXHAUSTION-AND-AVAILABILITY.md`: the limits are an explicit promise (SECURITY.md "The limits"); the embedder's process is the shared service.
- `AI-AND-LLM.md`: the tool protocol is a model-to-tool dispatch with a gate and schema.
- `DESKTOP-MOBILE-AND-LOCAL-IPC.md`: temp-folder, lock-file and cache-folder ownership against another OS user; the CLI.
- Excluded: `WEB-PROTOCOL-AND-AUTH.md`, `CLIENT-SIDE.md`, `PROTOCOLS-RPC-AND-MESSAGING.md`, `CLOUD-AND-DEPLOYMENT.md` (no HTTP, browser, RPC transport or cloud workload in the repository).
