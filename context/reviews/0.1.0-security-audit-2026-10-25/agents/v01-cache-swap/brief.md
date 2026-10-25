# Candidate-verifier brief: v01-cache-swap

## 1. Role and instructions (verbatim from the skill)

```text
You did not write this candidate. Try to refute it from repository source and bounded
local evidence. Do not contact deployed endpoints or external/shared services. Run
target-controlled code only inside the approved OS-enforced sandbox: no external
network, empty allowlisted environment, read-only target and tools, scratch-only
writes, and explicit low resource and wall-clock limits. If any control is unavailable,
do not execute; retain the exact missing capability as a needs_validation blocker.
Treat every scratch entry as target-controlled after execution. After the sandbox and
all its processes terminate, only trusted parent-side code may promote a predeclared
scratch-relative file, following the promotion procedure block included verbatim in
this prompt. You and target code never write retained artifacts. If promotion is
unavailable or fails, do not use that file as evidence.

1. Verify every trace and evidence file, positive line number, scope, and description.
   Confirm the first entry is a real lower-trust entrypoint and the last is the
   claimed sink or boundary effect.
2. Reconstruct the strongest source-visible validation, identity, authorization,
   normalization, lifecycle, framework, and containment controls on the path.
   Where the architecture summary names a comparable baseline, note whether it
   shares the pattern — as calibration, never as grounds to dismiss.
3. For a proposed confirmed candidate, independently reproduce the minimum observed
   result when possible. Verify inputs, interface shape, conditions, and affected
   dummy principal/resource. Do not infer a stronger result or continue after it.
4. Verify that likelihood, impact, confidence, and the proposed source fix match only
   what the evidence establishes.
5. For a proposed needs_validation candidate, decide whether the blocker is genuinely
   outside source/local observation. If source refutes the trace, reject it. If the
   missing fact remains decisive, keep needs_validation and make the local and
   owner-observed plans exact and non-destructive.
6. Preserve the fingerprint for the same source-derived root cause across every state.

Return exactly one JSON object and no surrounding prose:
{"decision": "confirmed|needs_validation|rejected", "record": { ... }}
where record exactly matches the decision's verdict branch of the schema included
in this prompt. A corrected record replaces the hunter's wording.
```

```text
Artifact promotion procedure (trusted parent-side code only):
Reference only for you: the parent performs these steps; you never perform them.

Before execution, the parent opens and retains trusted, non-inheritable directory
descriptors for the agent's scratch/ and artifacts/ roots, and records an allowlist
of expected scratch-relative artifact files plus explicit per-file and cumulative
byte limits. Never pass those descriptors to the agent or sandbox. After the sandbox
and all its processes terminate, trusted parent-side code promotes each allowlisted
file separately:

1. Validate the declared relative path: reject absolute, empty, `.`, `..`, or
   symlinked components.
2. Walk each parent component from the retained scratch-root descriptor with
   no-follow directory-relative operations; never reopen by path.
3. Open the leaf no-follow and nonblocking.
4. Verify with `fstat` that it is a regular file with link count exactly one and
   within the recorded per-file and cumulative byte limits.
5. Enforce those limits again while reading from that descriptor.
6. Copy exactly the verified size, repeat `fstat`, and reject a changed identity,
   type, link count, or size.
7. For the destination, walk every parent component from the retained
   artifacts-root descriptor with no-follow directory-relative operations; require
   each existing component to be a real directory, and create any missing directory
   exclusively before reopening and verifying it no-follow.
8. Create the leaf exclusively without following links, verify that the opened
   destination is a regular file with link count exactly one, and copy from the
   verified source descriptor without reopening either path.
9. Use equivalent race-safe APIs on non-POSIX systems.
10. Never recursively copy or glob scratch, extract an archive into artifacts, or
    open or promote a symlink, FIFO, socket, device, directory, hard-linked file,
    changing file, or file that exceeds its bound.
11. If any check is unavailable, cannot be enforced, or fails, discard the scratch
    entry; if it is decisive evidence, retain `needs_validation` with the exact
    promotion blocker.
```

## 2. The candidate (from hunter `h04-loader`; `proposed_verdict` is the hunter's proposal, not a decision)

```json
{
  "proposed_verdict": "needs_validation",
  "fingerprint": "src/wasi_python/_engines.py:_load:cwasm-checked-by-lstat-opened-by-path",
  "title": "Module cache: the .cwasm checked by lstat is not the file wasmtime deserializes when an ancestor folder belongs to a lower-trust user",
  "description": "The runner trusts a .cwasm (native code) only when private() finds it this user's, 0600, one link, in a 0700 folder of this user's. It checks only the leaf entries by path, then wasmtime-py reopens the file by its full path, following links in every ancestor, and the runner afterwards compares a fresh lstat stamp with the first. A principal that can rename entries in any ancestor of the cache folder can, during that open, rename the runner's folder aside and put a link to its own folder in its place, then restore it before the re-check. The planted image is then accepted and instantiated as python.wasm. The runner itself chooses such a path when a process runs with another user's $HOME (default_cache_dir is under $HOME; default_cache_dirs names sudo as a case it expects), e.g. root under a sudo that keeps HOME, where ~/.cache or ~/Library/Caches belongs to the invoking user. Under a deterministic schedule on one OS user the planted module was returned by _module with no warning; the cross-user race in a real sudo deployment was not observed.",
  "claimed_root_cause": "private() and the post-load stamp check bind the trust decision to path names (lstat of the leaf) while the load reopens by path; nothing checks that every ancestor of the cache folder is owned by this user (or root) and not writable by others, and the .cwasm is not opened once with no-follow and deserialized from that verified descriptor.",
  "trace": [
    {
      "kind": "entrypoint",
      "file": "src/wasi_python/runner.py",
      "line": 115,
      "scope": "run",
      "description": "Embedder call with cache_dir=None: the default module cache is used."
    },
    {
      "kind": "propagation",
      "file": "src/wasi_python/_call.py",
      "line": 146,
      "scope": "_run_checked",
      "description": "cache = _engines._cache_dir(cache_dir)."
    },
    {
      "kind": "propagation",
      "file": "src/wasi_python/_engines.py",
      "line": 85,
      "scope": "_cache_dir",
      "description": "Default cache derived from Path.home() ($HOME), which under a sudo that keeps HOME is the invoking user's home."
    },
    {
      "kind": "propagation",
      "file": "src/wasi_python/_platform.py",
      "line": 534,
      "scope": "_Posix.default_cache_dir",
      "description": "$XDG_CACHE_HOME or $HOME/.cache/wasi_python (Darwin line 1091: $HOME/Library/Caches/wasi_python); its parent belongs to whoever owns that home."
    },
    {
      "kind": "propagation",
      "file": "src/wasi_python/_engines.py",
      "line": 178,
      "scope": "_module_miss",
      "description": "private(cache, is_dir=True) lstats only the cache folder itself (owner, 0700); ancestors unchecked."
    },
    {
      "kind": "propagation",
      "file": "src/wasi_python/_engines.py",
      "line": 228,
      "scope": "_load",
      "description": "private(cwasm) lstats the leaf by path: this user's, 0600, one link."
    },
    {
      "kind": "sink",
      "file": "src/wasi_python/_engines.py",
      "line": 233,
      "scope": "_load",
      "description": "wt.Module.deserialize_file(engine, str(cwasm)) reopens the path, following any link swapped into an ancestor; the stamp re-check at line 237 passes once the folder is restored, and the module is cached and instantiated as the guest binary."
    }
  ],
  "evidence": [
    {
      "file": "src/wasi_python/_platform.py",
      "line": 556,
      "description": "POSIX private(): one lstat of the given path; no ancestor ownership or writability check."
    },
    {
      "file": "src/wasi_python/_engines.py",
      "line": 214,
      "description": "_load docstring: the post-load check 'narrows, not closes, the window between the check and the load'."
    },
    {
      "file": "src/wasi_python/_engines.py",
      "line": 237,
      "description": "Re-check compares lstat stamps by name, which an attacker restores before it runs."
    },
    {
      "file": "src/wasi_python/_platform.py",
      "line": 542,
      "description": "default_cache_dirs: the runner expects processes with another $HOME (sudo, a container, CI)."
    },
    {
      "file": "docs/explanation/security-model.md",
      "line": 89,
      "description": "Not-protected list covers caches 'if anything but the runner can write there' and names cache_dir/$WASI_PYTHON_CACHE as trusted input; the default derived from $HOME is not named there, and the runner's own private() owner check shows the default cache is meant to be refused when another user owns it."
    }
  ],
  "blockers": [
    "The cross-user part was not observed: this machine offers one OS user and no root, so a lower-trust owner of the cache folder's parent racing a second user's (or root's) runner could not be run.",
    "Whether a supported deployment runs the runner as another user with the invoking user's $HOME (macOS sudo keeping HOME, a sudo with env_keep HOME, a container or CI step with a mapped home) is a deployment fact outside source.",
    "Race feasibility without the deterministic hook (blind rename loop by the parent's owner against one deserialize per process) was not measured."
  ],
  "validation_plan": {
    "local": "On a disposable macOS or Linux VM with users alice and root: as alice, keep ~/Library/Caches (or ~/.cache) as is and prepare /Users/alice/planted/<digest32>-wasmtime49.0.0-plain.cwasm (a serialized module of another wasm). As root with HOME=/Users/alice (sudo on macOS keeps HOME), run wasi_python.run('print(1)', snapshot=False) once so root makes its 0700 cache and .cwasm. Then loop as alice: rename wasi_python -> wasi_python.aside, symlink wasi_python -> /Users/alice/planted, rename back; while root starts fresh processes that call run(). Record whether process().counts['loaded'] rises with the planted module's exports (or the call fails with the planted module's missing exports) without a RuntimeWarning. The deterministic one-user schedule is in agents/h04-loader/artifacts/evidence/swap_harness.py.",
    "deployment": "Owner states whether running the runner as root or another user with a different user's $HOME is supported; if so, confirm on the release platforms that sudo keeps HOME (macOS default) and that the default cache's parent is then owned by the invoking user."
  }
}
```

## 3. The linked coverage unit(s) and the hunter's checks (artifact paths are relative to `context/reviews/0.1.0-security-audit-2026-10-25`)

```json
[
  {
    "coverage_id": "src%2Fwasi_python%2F_engines.py%23deserialize_file::src%2Fwasi_python%2F_platform.py%23private::src%2Fwasi_python::MEMORY-SAFETY-AND-BINARY.md%23Library%2C%20plugin%2C%20and%20executable%20search-order%20trust",
    "surface": "The .cwasm module cache: default location from HOME/XDG_CACHE_HOME/LOCALAPPDATA/WASI_PYTHON_CACHE, cache_dir=, files named by digest and wasmtime version, loaded with deserialize_file",
    "boundary": "private(): owner, mode 0700/0600, link count, no reparse point; stamp re-check after load; mkstemp+replace writes; the judge refusing grants over every cache",
    "agent_id": "h04-loader",
    "local_checks": [
      {
        "agent_id": "h04-loader",
        "reviewed_paths": [
          "src/wasi_python/_engines.py",
          "src/wasi_python/_platform.py"
        ],
        "invariant": "Only a .cwasm the runner made (this user's, 0600, one link, in a 0700 folder of this user's) is deserialized, and the file deserialized is the file checked",
        "method": "source",
        "result": "POSIX private() (_platform.py:556-571) lstat-checks only the leaf (the cache folder, then the .cwasm) for owner, kind, link count and group/other mode bits; no ancestor of the cache folder is checked. _load (_engines.py:214-244) lstats, calls private(), then lets wasmtime-py reopen the file by its full path (deserialize_file, line 233) following any link in the ancestry, and afterwards compares only (dev, ino, size, mtime) of a fresh lstat with the first. The check and the open are not bound to one descriptor, so whoever can rename entries in an ancestor of the cache folder can redirect the open and restore the folder before the re-check. The docstring itself says the window is narrowed, not closed.",
        "artifact": null
      },
      {
        "agent_id": "h04-loader",
        "reviewed_paths": [
          "src/wasi_python/_places.py",
          "src/wasi_python/_engines.py",
          "src/wasi_python/_call.py",
          "src/wasi_python/_sessions.py",
          "src/wasi_python/_platform.py"
        ],
        "invariant": "No guest grant or root can write any module cache this process knows of",
        "method": "source",
        "result": "_walk_grants/_runtime_folders/_judge (_places.py:467-500, 527-575, 330-381) refuse a writable grant or root at, inside or above this call's cache, $WASI_PYTHON_CACHE and every platform default (including the password-database home's, _platform.py:542-554), by identity, with every link component of the written path in the chain (_cache_chain, 297-322) and not-yet-made caches judged from their deepest existing ancestor. Both run (_call.py:146-156) and Session (_sessions.py:961-979) pass others=_caches(cache). No guest path to a known cache found. A cache_dir= used by an earlier call is not remembered (embedder contract, runner.py:185-188 and security-model.md 'The module cache's contents').",
        "artifact": null
      },
      {
        "agent_id": "h04-loader",
        "reviewed_paths": [
          "src/wasi_python/_engines.py"
        ],
        "invariant": "The runner's own .cwasm writes cannot replace or follow a planted file or link",
        "method": "source",
        "result": "_store (_engines.py:254-275) writes via mkstemp(dir=cache) at 0600 and os.replace onto the name, which replaces a link itself; a refused folder at the name is never written over (_load line 229). Holds.",
        "artifact": null
      },
      {
        "agent_id": "h04-loader",
        "reviewed_paths": [
          "src/wasi_python/_engines.py",
          "src/wasi_python/_platform.py"
        ],
        "invariant": "The checked .cwasm identity equals the mapped identity under an ancestor swap",
        "method": "local",
        "result": "Deterministic schedule (one OS user plays both roles): the runner compiled a.wasm and wrote its 0600 .cwasm; a planted 0644 .cwasm of another module (export planted_image_loaded) is refused by private() when checked directly; with the cache folder renamed aside and replaced by a link to the planted folder only while wasmtime opens the path, and put back before the stamp re-check, _module(engine, False, a.wasm, cache) returned the planted module (exports ['planted_image_loaded'], counts loaded=2) with no warning. macOS arm64, wasmtime-py 49.0.0, sandbox-exec deny network, env -i, ulimit -t 300 -f 4000000 -n 4096; target not read-only mounted; writes under scratch only.",
        "artifact": "agents/h04-loader/artifacts/evidence/swap_run.log"
      },
      {
        "agent_id": "h04-loader",
        "reviewed_paths": [
          "src/wasi_python/_platform.py"
        ],
        "invariant": "private() refuses a cache another principal can write",
        "method": "local",
        "result": "On macOS an extended ACL 'everyone allow add_file,delete_child,...,file_inherit' on a 0700 cache folder is invisible to private(): private(dir) and private(file) both return True, and the mkstemp-made 0600 .cwasm inherits 'everyone allow read,write,append'. Reported as hardening: the ACL must be set by the folder's owner or an administrator, which the documented trusted-input rule for cache folders covers. Linux POSIX ACLs show in the group bits (mask) and are refused. Windows private() checks no owner or access list at all (_platform.py:1436-1448), as its docstring says.",
        "artifact": "agents/h04-loader/artifacts/evidence/acl_run.log"
      }
    ]
  }
]
```

## 4. Architecture facts (the run's architecture summary, verbatim)

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


## 5. Companion validation blocks (verbatim)

<!-- MEMORY-SAFETY-AND-BINARY.md#Core discipline -->
## Core discipline (include in every agent prompt for this domain)

```
- Re-derive every bound and lifetime from attacker-controlled inputs and all callers. Validate against the worst accepted case, not a typical test vector.
- A panic, sanitizer finding, or crash proves a defect only when a realistic untrusted input reaches it. Do not infer memory corruption, code execution, or shared availability impact from a label alone.
- Validate in a local harness with sanitizers, deterministic concurrency tests, existing fuzz targets, and debugger-assisted fault classification. Stop after proving the violated invariant and observable impact; do not develop post-corruption techniques.
- Assembly, JIT code, custom allocators, intra-object accesses, and foreign libraries can escape sanitizer coverage. Identify which relevant instructions are instrumented.
- Classify as `confirmed` only after source evidence and bounded local validation establish the defect and effect. Use `needs_validation` when ABI, allocator, architecture, feature, deployment, or reachability facts remain unknown.
```

<!-- MEMORY-SAFETY-AND-BINARY.md#Validation rules -->
## Validation rules (apply before reporting ANY finding here)

1. Establish a realistic untrusted entry and exact operation that violates a bounds, type, lifetime, ABI, concurrency, loader, or authority invariant.
2. Classify the observable effect: invalid read, invalid write, stale alias, wrong object, uninitialized output, unauthorized image load, deadlock, or safe process termination. Do not claim a stronger effect than observed.
3. Run the narrowest local harness, existing test, sanitizer, or fuzzer needed to reproduce the effect. Verify sanitizer coverage of the faulting operation and record architecture/build conditions.
4. For concurrency, use a deterministic schedule or sanitizer trace. For binary loading, prove the checked identity differs from the mapped identity and name the lower-trust writer.
5. Return `confirmed` findings only with exact input, source trace, and observed result. Return `needs_validation` for a specific unresolved reachability, ABI, build, deployment, or runtime fact and state the bounded check needed.


## 6. Execution boundary, paths, allowlist

- Target root: `.` (all paths in your record are repository-relative to it). Never edit a file under it. Never run `uv sync`, plain `uv run`, `scripts/00_download.sh`, `scripts/build.sh` or `scripts/steps/*.sh`, `release/set_key.py`, `gh workflow run`, `git push`, `pytest --accept*`, or anything writing under `context/`. Never download from the internet; read-only `gh` GET calls against the project's own repository are allowed.
- Your scratch (the only place you write): `context/reviews/0.1.0-security-audit-2026-10-25/agents/v01-cache-swap/scratch/`. Parent-owned artifacts (you never write): `context/reviews/0.1.0-security-audit-2026-10-25/agents/v01-cache-swap/artifacts/`. Allowlist for promotion: regular files directly under `scratch/evidence/` named `*.txt`, `*.json`, `*.log` or `*.py`, at most 24 files, 512 KiB each, 8 MiB total; after you finish the parent promotes them to `artifacts/evidence/<name>`.
- Before any target-controlled execution confirm `./build/lane.lock` does not exist. Wrap every target-controlled run as: `ulimit -t 300 -f 4000000 -n 4096; /usr/bin/env -i PATH=/usr/bin:/bin HOME=context/reviews/0.1.0-security-audit-2026-10-25/agents/v01-cache-swap/scratch/home TMPDIR=context/reviews/0.1.0-security-audit-2026-10-25/agents/v01-cache-swap/scratch/tmp WASI_PYTHON_CACHE=context/reviews/0.1.0-security-audit-2026-10-25/agents/v01-cache-swap/scratch/cache /usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' ./.venv/bin/python -I <script under scratch>` (make the three folders first; give each child a wall-clock bound with `subprocess.run(timeout=...)` from a trusted driver). This platform cannot enforce a read-only target mount or a memory rlimit; never point a writable grant or root at the target or at a real cache; say in the record's `execution.instructions` that the target was not read-only mounted. If a control you need cannot be enforced, do not execute; keep the exact blocker as `needs_validation`.
- You may read the hunter's evidence files under `context/reviews/0.1.0-security-audit-2026-10-25/agents/h04-loader/artifacts/evidence/` (read-only) and re-run its harness in your own scratch. A verifier-owned `local` check must cite a file you wrote under your own `scratch/evidence/`.
- Keep probes small and short (deadlines of a few seconds, small sizes).

## 7. Prior records with the same fingerprint

None (no prior run).

## 8. Result contract

Return exactly one JSON object and no surrounding prose: `{"decision": "confirmed|needs_validation|rejected", "record": { ... }}` where `record` exactly matches the decision's branch below (`additionalProperties: false`; do not carry `proposed_verdict`, `_hunter` or any other wrapper field; `verdict` must equal `decision`). Also write the same object to `context/reviews/0.1.0-security-audit-2026-10-25/agents/v01-cache-swap/scratch/result.json`, writing it incrementally as you settle each part so a partial file exists if your final message is cut off. Use plain factual language.

### `confirmed` branch (verbatim)
```json
{
  "type": "object",
  "description": "A source-grounded vulnerability that was independently demonstrated.",
  "properties": {
    "verdict": {
      "type": "string",
      "const": "confirmed"
    },
    "fingerprint": {
      "type": "string",
      "minLength": 1,
      "pattern": "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$",
      "description": "A stable source-derived identifier that does not change between validation states."
    },
    "title": {
      "type": "string",
      "minLength": 1,
      "visibleContent": true
    },
    "description": {
      "type": "string",
      "minLength": 1,
      "visibleContent": true
    },
    "root_cause": {
      "type": "string",
      "minLength": 1,
      "visibleContent": true
    },
    "intended_behavior": {
      "type": "string",
      "minLength": 1,
      "visibleContent": true
    },
    "trace": {
      "type": "array",
      "minItems": 1,
      "uniqueItems": true,
      "items": {
        "type": "object",
        "properties": {
          "kind": {
            "type": "string",
            "enum": [
              "entrypoint",
              "propagation",
              "sink"
            ]
          },
          "file": {
            "type": "string",
            "minLength": 1
          },
          "line": {
            "type": "integer",
            "minimum": 1
          },
          "scope": {
            "type": "string",
            "minLength": 1,
            "visibleContent": true
          },
          "description": {
            "type": "string",
            "minLength": 1,
            "visibleContent": true
          }
        },
        "required": [
          "kind",
          "file",
          "line",
          "scope",
          "description"
        ],
        "additionalProperties": false
      }
    },
    "evidence": {
      "type": "array",
      "minItems": 1,
      "uniqueItems": true,
      "items": {
        "type": "object",
        "properties": {
          "file": {
            "type": "string",
            "minLength": 1
          },
          "line": {
            "type": "integer",
            "minimum": 1
          },
          "description": {
            "type": "string",
            "minLength": 1,
            "visibleContent": true
          }
        },
        "required": [
          "file",
          "line",
          "description"
        ],
        "additionalProperties": false
      }
    },
    "conditions": {
      "type": "array",
      "uniqueItems": true,
      "items": {
        "type": "object",
        "properties": {
          "kind": {
            "type": "string",
            "enum": [
              "authentication_level",
              "authorization_role",
              "user_interaction",
              "system_configuration",
              "network_routing",
              "environmental_dependency",
              "data_state",
              "timing_dependency",
              "third_party_dependency"
            ]
          },
          "description": {
            "type": "string",
            "minLength": 1,
            "visibleContent": true
          }
        },
        "required": [
          "kind",
          "description"
        ],
        "additionalProperties": false
      }
    },
    "execution": {
      "type": "object",
      "description": "Target-neutral reproduction in the target's native interface.",
      "properties": {
        "attacker_perspective": {
          "type": "string",
          "minLength": 1,
          "visibleContent": true
        },
        "payloads": {
          "type": "array",
          "minItems": 1,
          "uniqueItems": true,
          "items": {
            "type": "string"
          }
        },
        "instructions": {
          "type": "array",
          "minItems": 1,
          "items": {
            "type": "string",
            "minLength": 1,
            "visibleContent": true
          }
        },
        "observed_result": {
          "type": "string",
          "minLength": 1,
          "visibleContent": true
        }
      },
      "required": [
        "attacker_perspective",
        "payloads",
        "instructions",
        "observed_result"
      ],
      "additionalProperties": false
    },
    "remediation": {
      "type": "object",
      "properties": {
        "strategy": {
          "type": "string",
          "minLength": 1,
          "visibleContent": true
        },
        "code_changes": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "file_name": {
                "type": "string",
                "minLength": 1
              },
              "fixed_code": {
                "type": "string"
              }
            },
            "required": [
              "file_name",
              "fixed_code"
            ],
            "additionalProperties": false
          }
        }
      },
      "required": [
        "strategy"
      ],
      "additionalProperties": false
    },
    "severity": {
      "type": "object",
      "properties": {
        "likelihood": {
          "type": "object",
          "properties": {
            "score": {
              "type": "string",
              "enum": [
                "informational",
                "low",
                "medium",
                "high",
                "critical"
              ]
            },
            "reason": {
              "type": "string",
              "minLength": 1,
              "visibleContent": true
            }
          },
          "required": [
            "score",
            "reason"
          ],
          "additionalProperties": false
        },
        "impact": {
          "type": "object",
          "properties": {
            "score": {
              "type": "string",
              "enum": [
                "informational",
                "low",
                "medium",
                "high",
                "critical"
              ]
            },
            "reason": {
              "type": "string",
              "minLength": 1,
              "visibleContent": true
            }
          },
          "required": [
            "score",
            "reason"
          ],
          "additionalProperties": false
        },
        "overall_severity": {
          "type": "string",
          "enum": [
            "informational",
            "low",
            "medium",
            "high",
            "critical"
          ]
        }
      },
      "required": [
        "likelihood",
        "impact",
        "overall_severity"
      ],
      "additionalProperties": false
    },
    "confidence": {
      "type": "object",
      "properties": {
        "score": {
          "type": "string",
          "enum": [
            "low",
            "medium",
            "high"
          ]
        },
        "reason": {
          "type": "string",
          "minLength": 1,
          "visibleContent": true
        }
      },
      "required": [
        "score",
        "reason"
      ],
      "additionalProperties": false
    }
  },
  "required": [
    "verdict",
    "fingerprint",
    "title",
    "description",
    "root_cause",
    "intended_behavior",
    "trace",
    "evidence",
    "conditions",
    "execution",
    "remediation",
    "severity",
    "confidence"
  ],
  "additionalProperties": false
}
```
### `needs_validation` branch (verbatim)
```json
{
  "type": "object",
  "description": "A source-grounded candidate whose decisive validation is blocked.",
  "properties": {
    "verdict": {
      "type": "string",
      "const": "needs_validation"
    },
    "fingerprint": {
      "type": "string",
      "minLength": 1,
      "pattern": "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
    },
    "title": {
      "type": "string",
      "minLength": 1,
      "visibleContent": true
    },
    "description": {
      "type": "string",
      "minLength": 1,
      "visibleContent": true
    },
    "claimed_root_cause": {
      "type": "string",
      "minLength": 1,
      "visibleContent": true
    },
    "trace": {
      "type": "array",
      "minItems": 1,
      "uniqueItems": true,
      "items": {
        "type": "object",
        "properties": {
          "kind": {
            "type": "string",
            "enum": [
              "entrypoint",
              "propagation",
              "sink"
            ]
          },
          "file": {
            "type": "string",
            "minLength": 1
          },
          "line": {
            "type": "integer",
            "minimum": 1
          },
          "scope": {
            "type": "string",
            "minLength": 1,
            "visibleContent": true
          },
          "description": {
            "type": "string",
            "minLength": 1,
            "visibleContent": true
          }
        },
        "required": [
          "kind",
          "file",
          "line",
          "scope",
          "description"
        ],
        "additionalProperties": false
      }
    },
    "evidence": {
      "type": "array",
      "minItems": 1,
      "uniqueItems": true,
      "items": {
        "type": "object",
        "properties": {
          "file": {
            "type": "string",
            "minLength": 1
          },
          "line": {
            "type": "integer",
            "minimum": 1
          },
          "description": {
            "type": "string",
            "minLength": 1,
            "visibleContent": true
          }
        },
        "required": [
          "file",
          "line",
          "description"
        ],
        "additionalProperties": false
      }
    },
    "blockers": {
      "type": "array",
      "minItems": 1,
      "uniqueItems": true,
      "items": {
        "type": "string",
        "minLength": 1,
        "visibleContent": true
      }
    },
    "validation_plan": {
      "type": "object",
      "properties": {
        "local": {
          "type": "string",
          "minLength": 1,
          "visibleContent": true
        },
        "deployment": {
          "type": "string",
          "minLength": 1,
          "visibleContent": true
        }
      },
      "additionalProperties": false
    }
  },
  "required": [
    "verdict",
    "fingerprint",
    "title",
    "description",
    "claimed_root_cause",
    "trace",
    "evidence",
    "blockers",
    "validation_plan"
  ],
  "additionalProperties": false
}
```
### `rejected` branch (verbatim)
```json
{
  "type": "object",
  "description": "A source-grounded candidate refuted during validation.",
  "properties": {
    "verdict": {
      "type": "string",
      "const": "rejected"
    },
    "fingerprint": {
      "type": "string",
      "minLength": 1,
      "pattern": "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
    },
    "title": {
      "type": "string",
      "minLength": 1,
      "visibleContent": true
    },
    "description": {
      "type": "string",
      "minLength": 1,
      "visibleContent": true
    },
    "claimed_root_cause": {
      "type": "string",
      "minLength": 1,
      "visibleContent": true
    },
    "trace": {
      "type": "array",
      "minItems": 1,
      "uniqueItems": true,
      "items": {
        "type": "object",
        "properties": {
          "kind": {
            "type": "string",
            "enum": [
              "entrypoint",
              "propagation",
              "sink"
            ]
          },
          "file": {
            "type": "string",
            "minLength": 1
          },
          "line": {
            "type": "integer",
            "minimum": 1
          },
          "scope": {
            "type": "string",
            "minLength": 1,
            "visibleContent": true
          },
          "description": {
            "type": "string",
            "minLength": 1,
            "visibleContent": true
          }
        },
        "required": [
          "kind",
          "file",
          "line",
          "scope",
          "description"
        ],
        "additionalProperties": false
      }
    },
    "evidence": {
      "type": "array",
      "minItems": 1,
      "uniqueItems": true,
      "items": {
        "type": "object",
        "properties": {
          "file": {
            "type": "string",
            "minLength": 1
          },
          "line": {
            "type": "integer",
            "minimum": 1
          },
          "description": {
            "type": "string",
            "minLength": 1,
            "visibleContent": true
          }
        },
        "required": [
          "file",
          "line",
          "description"
        ],
        "additionalProperties": false
      }
    },
    "reason": {
      "type": "string",
      "minLength": 1,
      "visibleContent": true
    }
  },
  "required": [
    "verdict",
    "fingerprint",
    "title",
    "description",
    "claimed_root_cause",
    "trace",
    "evidence",
    "reason"
  ],
  "additionalProperties": false
}
```
