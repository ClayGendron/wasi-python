# Hunter brief: h08-process

## 1. Role
You are a security hunter. Your goal is to find source-grounded security invariant failures in your assigned coverage units of the target repository at `.`, and you must return exactly one JSON object matching the structured-result contract at the end of this brief (section 9).

## 2. Architecture summary (verbatim)

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


## 3. Your assigned coverage units

Agent id: `h08-process`. Target root: `.` (all paths in your result are repository-relative to it).

```json
[
  {
    "coverage_id": "src%2Fwasi_python%2F_wasmtime_ffi.py%23ffi::src%2Fwasi_python%2F_home.py%23home::src%2Fwasi_python::MEMORY-SAFETY-AND-BINARY.md%23Unwind%2C%20exception%2C%20and%20thread-affinity%20violations",
    "canonical_refs": {
      "surface": "src/wasi_python/_wasmtime_ffi.py#ffi",
      "boundary": "src/wasi_python/_home.py#home",
      "subsystem": "src/wasi_python",
      "attack_class": "MEMORY-SAFETY-AND-BINARY.md#Unwind, exception, and thread-affinity violations"
    },
    "surface": "The runner's use of wasmtime-py's private API and ctypes: raw memory pointers, PreparedCall, the output callback, trap and signal handling (Linux handler check), guest threads on runner stacks, store close on every path, the fork hook",
    "boundary": "_wasmtime_ffi as the only private-API user, the home thread protocol, store lifecycle in _call, the signal-handler check",
    "subsystem": "src/wasi_python",
    "attack_class": "Unwind, exception and thread-affinity violations; stale pointers after memory growth or store close; teardown safety",
    "starting_paths": [
      "src/wasi_python/_wasmtime_ffi.py",
      "src/wasi_python/_home.py",
      "src/wasi_python/_call.py",
      "src/wasi_python/_process.py",
      "src/wasi_python/_platform.py",
      "src/wasi_python/_engines.py"
    ],
    "ordinary_attack_class_block": "ATTACK-CLASSES.md#Wildcard",
    "selected_companion_blocks": [
      "MEMORY-SAFETY-AND-BINARY.md#Core discipline",
      "MEMORY-SAFETY-AND-BINARY.md#Unwind, exception, and thread-affinity violations",
      "MEMORY-SAFETY-AND-BINARY.md#Use-after-free, stale view, and double free",
      "MEMORY-SAFETY-AND-BINARY.md#Shared-state races and TOCTOU",
      "MEMORY-SAFETY-AND-BINARY.md#Unload, reload, and teardown safety",
      "MEMORY-SAFETY-AND-BINARY.md#Universal moves",
      "MEMORY-SAFETY-AND-BINARY.md#Validation rules"
    ],
    "excluded_blocks": [
      {
        "block": "MEMORY-SAFETY-AND-BINARY.md#Type confusion and invalid downcast",
        "reason": "Python-side code; wasmtime's own type checks are upstream"
      }
    ]
  }
]
```

## 4. Selected attack-class blocks (verbatim)

<!-- ATTACK-CLASSES.md#Wildcard -->
**Wildcard** (subagent_type: `general`) You are not given a category. Find vulnerabilities outside the standard classes already assigned.

Read code that looks boring or disconnected from security. Follow incomplete, experimental, compatibility, and fallback features, but retain the same concrete boundary and validation requirements as every other class.

Use these starting points, but do not limit yourself to them:
- What is the strangest code in the codebase? Why does it exist? What happens if it is abused?
- Are there any features that feel half-finished, experimental, or bolted on? Those have the weakest security because they got the least review.
- What happens if you use the API in a way the frontend never would? The UI constrains users, but the API does not. What API calls are possible but never made by the client?
- Are there any hidden or undocumented endpoints, parameters, headers, or features? Look at route registrations, middleware, and config for things that are not in the docs.
- What happens when you mix features that were not designed to work together? Localization + preview + caching. Import + plugins + webhooks. OAuth + impersonation + API keys.
- Is there anything interesting in the git history? Reverted security fixes, commented-out auth checks, secrets that were committed then removed (still in history).
- Which valid-account actions affect other users, shared integrity, availability, or operator-owned cost? Verify containment, quotas, authorization, and recovery around those actions.
- Which operations are irreversible or require elevated confirmation? Bind authorization and approval to the final principal, action, and resource.
- What assumptions does the code make about the environment? That the database is local, that the clock is accurate, that DNS is trustworthy, that the filesystem is case-sensitive?
- Look at the test files — what are they **not** testing? Compare the edge cases the developer thought about (tests exist) with the ones they did not (no tests).

Pursue anomalies inside your assigned scope until the invariant is settled. If something looks strange, read it until you can state whether it is safe. If a function has a comment explaining why it is safe, verify the explanation. If a variable is named `temp` or `hack` or `legacy`, read it closely.

<!-- MEMORY-SAFETY-AND-BINARY.md#Core discipline -->
## Core discipline (include in every agent prompt for this domain)

```
- Re-derive every bound and lifetime from attacker-controlled inputs and all callers. Validate against the worst accepted case, not a typical test vector.
- A panic, sanitizer finding, or crash proves a defect only when a realistic untrusted input reaches it. Do not infer memory corruption, code execution, or shared availability impact from a label alone.
- Validate in a local harness with sanitizers, deterministic concurrency tests, existing fuzz targets, and debugger-assisted fault classification. Stop after proving the violated invariant and observable impact; do not develop post-corruption techniques.
- Assembly, JIT code, custom allocators, intra-object accesses, and foreign libraries can escape sanitizer coverage. Identify which relevant instructions are instrumented.
- Classify as `confirmed` only after source evidence and bounded local validation establish the defect and effect. Use `needs_validation` when ABI, allocator, architecture, feature, deployment, or reachability facts remain unknown.
```

<!-- MEMORY-SAFETY-AND-BINARY.md#Unwind, exception, and thread-affinity violations -->
**Unwind, exception, and thread-affinity violations** Exceptions or panics cross an ABI that forbids unwinding, callbacks run after teardown, or APIs requiring one runtime thread are invoked elsewhere. Review error conversion and cancellation. Confirm whether the process aborts or state is corrupted before assigning impact.

<!-- MEMORY-SAFETY-AND-BINARY.md#Use-after-free, stale view, and double free -->
**Use-after-free, stale view, and double free** Owners are released while callbacks, wait queues, timers, iterators, borrowed slices, or cached raw pointers can still use them. Review every error, cancellation, close, and realloc path. For embedded notification anchors, each free path must drain or detach all observers.

<!-- MEMORY-SAFETY-AND-BINARY.md#Shared-state races and TOCTOU -->
**Shared-state races and TOCTOU** Concurrent parser streams, global caches, lazy initialization, signal handlers, and resource teardown can invalidate bounds, policy, or pointers established earlier. Verify the race with a repeatable local schedule, barrier, or thread sanitizer; a hypothetical interleaving without a security-relevant state transition remains `needs_validation`.

<!-- MEMORY-SAFETY-AND-BINARY.md#Unload, reload, and teardown safety -->
**Unload, reload, and teardown safety** Live function pointers, callbacks, worker threads, or data views survive module unload or runtime reset. Review shutdown and failed-load cleanup as closely as startup.

<!-- MEMORY-SAFETY-AND-BINARY.md#Universal moves -->
## Universal moves (apply across the above)

- Audit fixes and duplicated paths for the same source-to-sink shape. A check in one caller, architecture, protocol role, feature flag, or compatibility path does not protect its siblings.
- Build a table for every parser or FFI boundary: accepted length/type, checked representation, allocation owner, consumer, thread, and teardown. Most native findings are one disagreement in that table.
- Use existing corpora and small locally generated boundary fixtures. Save exact sanitizer/runtime output and the input property that triggers it; avoid large resource consumption and any live target.

<!-- MEMORY-SAFETY-AND-BINARY.md#Validation rules -->
## Validation rules (apply before reporting ANY finding here)

1. Establish a realistic untrusted entry and exact operation that violates a bounds, type, lifetime, ABI, concurrency, loader, or authority invariant.
2. Classify the observable effect: invalid read, invalid write, stale alias, wrong object, uninitialized output, unauthorized image load, deadlock, or safe process termination. Do not claim a stronger effect than observed.
3. Run the narrowest local harness, existing test, sanitizer, or fuzzer needed to reproduce the effect. Verify sanitizer coverage of the faulting operation and record architecture/build conditions.
4. For concurrency, use a deterministic schedule or sanitizer trace. For binary loading, prove the checked identity differs from the mapped identity and name the lower-trust writer.
5. Return `confirmed` findings only with exact input, source trace, and observed result. Return `needs_validation` for a specific unresolved reachability, ABI, build, deployment, or runtime fact and state the bounded check needed.


## 5. Excluded blocks and reasons

- `MEMORY-SAFETY-AND-BINARY.md#Type confusion and invalid downcast`: Python-side code; wasmtime's own type checks are upstream

## 6. Core hunting method and promotion procedure

```text
## Defensive vulnerability-finding method

Your goal is to find source-grounded security invariant failures and the smallest fix,
not to expand harm beyond the boundary result. Stay within source review and bounded local execution.
Do not contact deployed endpoints, provider APIs, registries, identity systems,
message brokers, shared services, or other users. Use local dummy data only.

READ THE CODE AT DEPTH. Follow each assigned input through parsing, identity,
authorization, normalization, state, derived copies, and the final sink. Read sibling,
legacy, batch, retry, cancellation, migration, and error paths that produce the same
effect. Compare sibling controls for equivalence, not only presence, and compare what
one component guarantees with what the next component assumes.

WORK FROM A CONCRETE INVARIANT:
1. Name the lower-trust principal and starting capability.
2. Name the accepted value, action, state transition, or resource selector.
3. Locate the control that should reject, bind, isolate, limit, or revoke it.
4. Trace the exact source path after that decision.
5. Stop at the smallest affected dummy record, wrong return value, process-integrity
   effect, or locally observable shared-resource effect.
6. State a source-level change and regression case that enforce the invariant.

DEPTH BOUND: trace only paths that can reach your assigned boundary or whose
guarantees that boundary relies on. Stop a line of investigation as soon as the
invariant is settled either way, and record the result in your structured output —
a covered, candidate, or blocked disposition, or an `uncovered` entry — instead of
continuing to search.

TEST SAD PATHS AND DISAGREEMENTS. Check absent, empty, zero, negative, maximum,
over-limit, duplicate, mixed encoding, stale, revoked, reordered, concurrent,
partially migrated, failed dependency, and rollback state only where the interface
accepts them. Compare canonicalization and units at every parser or policy handoff.
For multi-step issues, treat each output as a prerequisite and do not assume a later
boundary. If any prerequisite is not established, record a blocker.

When a proposed high or critical candidate reveals a reusable root cause, search paths
owned by the assigned coverage IDs for lexical, structural, and logical variants.
Consolidate the same root cause, but establish each variant's conditions and impact
independently. Do not investigate peer-owned units. Return a variant with no current
coverage unit as `uncovered`.

USE THE NARROWEST LOCAL CHECK THAT SETTLES THE CLAIM. Target-controlled builds,
tests, processes, browsers, emulators, fuzzers, and fixture processing may run only
inside the parent-approved OS-enforced sandbox. It must disable external networking,
start from an empty allowlisted environment, expose target and tools read-only, permit
writes only to your scratch directory, and apply low CPU, memory, process, file-size,
disk, and wall-clock limits. Isolated loopback is allowed only for a local fixture.
If any control is unavailable, do not execute: return needs_validation with that exact
blocker. Prefer an existing unit test, minimal function harness, dummy-tenant service
call, small malformed fixture, deterministic race schedule, or locally rendered policy.
Do not install or fetch tools.

Record the exact input, command, limits, and minimum result. For the environment,
record only allowlisted variable names and safe non-secret values needed to reproduce
the check. Never capture the ambient environment, inherited variables, credentials,
authentication state, or unrelated host paths. The target-controlled process writes
only in scratch. After the sandbox and all its processes terminate, only trusted
parent-side code may promote predeclared scratch-relative files, following the
promotion procedure block included verbatim in this prompt. You and target code never
write retained artifacts. If promotion is unavailable or fails for decisive evidence,
return needs_validation with the exact promotion blocker.
Never stress availability, invoke a live target, use a real credential, publish an
artifact, or continue past the minimum observed effect.

A deployment, browser, provider, broker, OS, proxy, package, secret, or identity fact
outside source is not proof either way. If one such fact is decisive, return a
needs_validation record with the exact missing observation and safe owner-observed check.
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

## 7. Core validation rules

```text
## Candidate gate

1. A candidate needs a complete repository-relative source trace and evidence for the
   claimed root cause, including the strongest source-visible control.
2. A proposed confirmed record needs a bounded local observed result, meaningful impact
   across a stated boundary, complete conditions, and no visible preventing layer.
3. Do not strengthen a crash into code execution, ordinary work into shared availability,
   or a same-principal action into privilege gain.
4. If a required fact is not source-visible or locally observable, use
   needs_validation. Name exact blockers; do not give it severity or speculative completion.
5. A missing best practice with no affected principal/resource is excluded or hardening,
   not a finding. A candidate disproved by source is not needs_validation.
6. Use the same source-derived fingerprint for the same root cause in every state.
   It must match `^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$` and must not include a line,
   wave, agent, severity, or verdict.
7. Return an empty candidate array when nothing survives these gates.
```

## 8. Exclusions and peers

No prior-run confirmed records are carried, so nothing is excluded on that account. Documented "not protected" behaviour in `docs/explanation/security-model.md:67-109` is intended behaviour: report it only if you show an effect stronger than documented. The project's own earlier review `context/reviews/0.1.0-security-review-2026-10-21.md` is background you may read; do not re-report its closed findings (its H1 and H2 were fixed by specs 113 and 114).

Peer-owned coverage IDs you must not duplicate (return an unexpected boundary under `uncovered` instead):
- `.github%2Fworkflows%2Frelease.yml%23on::.github%2Fworkflows%2Frelease.yml%23permissions::.github%2Fworkflows::SUPPLY-CHAIN-AND-RELEASE.md%23Cache%2C%20artifact%2C%20and%20workspace%20trust%20mixing`
- `build%2Fartifacts%2Fpython-stdlib.zip%23entries::scripts%2Fmake_stdlib_zip.py%23members::build%2Fartifacts::MEMORY-SAFETY-AND-BINARY.md%23Library%2C%20plugin%2C%20and%20executable%20search-order%20trust`
- `build%2Fartifacts%2Fpython.wasm%23imports::scripts%2Fsteps%2F60_link.sh%23link::build%2Fartifacts::ATTACK-CLASSES.md%23Obvious%20things`
- `pyproject.toml%23dependencies::release%2Fset_key.py%23verify::release::SUPPLY-CHAIN-AND-RELEASE.md%23Dependency%20source%20and%20namespace%20confusion`
- `scripts%2F00_download.sh%23download::downloads%2FSHA256SUMS::scripts::SUPPLY-CHAIN-AND-RELEASE.md%23Mutable%20and%20unbound%20build%20inputs`
- `src%2Fwasi_python%2F_artifacts.py%23find::src%2Fwasi_python%2F_artifacts.py%23_found_and_checked::src%2Fwasi_python::MEMORY-SAFETY-AND-BINARY.md%23Missing%20artifact%20identity%20or%20signature%20binding`
- `src%2Fwasi_python%2F_call.py%23_door::src%2Fwasi_python%2F_call.py%23_shared::src%2Fwasi_python::MEMORY-SAFETY-AND-BINARY.md%23Pointer-length%20and%20ownership%20contract%20mismatch`
- `src%2Fwasi_python%2F_call.py%23_guard_linker::src%2Fwasi_python%2F_places.py%23_judge::src%2Fwasi_python::ATTACK-CLASSES.md%23Resource%20and%20file%20handling`
- `src%2Fwasi_python%2F_call.py%23_preopens::src%2Fwasi_python%2F_places.py%23_judge_import_path::src%2Fwasi_python::ATTACK-CLASSES.md%23Chained%20vulnerabilities%20and%20trust%20boundaries::reused-root`
- `src%2Fwasi_python%2F_engines.py%23deserialize_file::src%2Fwasi_python%2F_platform.py%23private::src%2Fwasi_python::MEMORY-SAFETY-AND-BINARY.md%23Library%2C%20plugin%2C%20and%20executable%20search-order%20trust`
- `src%2Fwasi_python%2F_fs_memory.py%23SIGNATURES::src%2Fwasi_python%2F_fs_memory.py%23bounds::src%2Fwasi_python::MEMORY-SAFETY-AND-BINARY.md%23Out-of-bounds%20read%20or%20write`
- `src%2Fwasi_python%2F_private_dirs.py%23_Private::src%2Fwasi_python%2F_private_dirs.py%23_sweep_once::src%2Fwasi_python::DESKTOP-MOBILE-AND-LOCAL-IPC.md%23Local%20file%20ownership%20and%20TOCTOU`
- `src%2Fwasi_python%2F_sessions.py%23Session::src%2Fwasi_python%2F_process.py%23_Process::src%2Fwasi_python::ATTACK-CLASSES.md%23Business%20logic`
- `src%2Fwasi_python%2F_tool_host.py%23_ToolHost::src%2Fwasi_python%2F_tool_host.py%23admit::src%2Fwasi_python::AI-AND-LLM.md%23Tool-schema%20and%20dispatcher%20disagreement`
- `src%2Fwasi_python%2Fcli.py%23main::src%2Fwasi_python%2Frunner.py%23_checked::src%2Fwasi_python::ATTACK-CLASSES.md%23Obvious%20things`
- `src%2Fwasi_python%2Fmounts.py%23FileProvider::src%2Fwasi_python%2F_fs_paths.py%23_resolve::src%2Fwasi_python::ATTACK-CLASSES.md%23Resource%20and%20file%20handling`
- `src%2Fwasi_python%2Frunner.py%23run::src%2Fwasi_python%2F_limits.py%23_check_limits::src%2Fwasi_python::RESOURCE-EXHAUSTION-AND-AVAILABILITY.md%23Detached%20work%20after%20cancellation`

## 9. Paths, sandbox, allowlist, and the result contract

- Your scratch directory (the only place you may write): `context/reviews/0.1.0-security-audit-2026-10-25/agents/h08-process/scratch/`
- Your retained artifacts directory (parent-owned; you never write it): `context/reviews/0.1.0-security-audit-2026-10-25/agents/h08-process/artifacts/`
- Promotion allowlist: regular files directly under `scratch/evidence/` named `*.txt`, `*.json`, `*.log` or `*.py`, at most 24 files, 512 KiB each, 8 MiB in total. After you finish, the parent promotes them to `artifacts/evidence/<name>`; a `local` check's `artifact` field must name `agents/h08-process/artifacts/evidence/<name>` for a file you wrote to `scratch/evidence/<name>`.
- Never edit any file under the target. Never run `uv sync`, plain `uv run`, `scripts/00_download.sh`, `scripts/build.sh` or any `scripts/steps/*.sh`, `release/set_key.py`, `gh workflow run`, `git push`, `pytest --accept*`, or anything writing under `context/`. Never download from the internet. Read-only `gh` GET calls against the project's own repository are allowed.
- Target-controlled execution (the runner through Python, a guest inside wasmtime, a pytest node id) is allowed only as a bounded local check, wrapped like this, with the three directories under your scratch: `ulimit -t 300 -f 4000000 -n 4096; /usr/bin/env -i PATH=/usr/bin:/bin HOME=context/reviews/0.1.0-security-audit-2026-10-25/agents/h08-process/scratch/home TMPDIR=context/reviews/0.1.0-security-audit-2026-10-25/agents/h08-process/scratch/tmp WASI_PYTHON_CACHE=context/reviews/0.1.0-security-audit-2026-10-25/agents/h08-process/scratch/cache /usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' ./.venv/bin/python -I <your script under scratch>` (create `scratch/home`, `scratch/tmp`, `scratch/cache` first). Use `subprocess.run(..., timeout=...)` from a trusted driver when a step needs a wall-clock bound. This platform cannot enforce a read-only target mount or a memory rlimit: the project's own memory cap bounds the guest, and you must not point any writable grant or root at the target. Record in each local check that the target was not read-only mounted. If a check needs a control you cannot enforce, do not run it: return `needs_validation` with that blocker.
- Pytest: use `./.venv/bin/python -I -m pytest <nodeid> -p no:cacheprovider --progress-latest context/reviews/0.1.0-security-audit-2026-10-25/agents/h08-process/scratch/latest.json` inside the same wrapper; never a whole tier.
- Keep disk use small; delete large files you create under scratch before finishing.

Also write your final JSON object to `context/reviews/0.1.0-security-audit-2026-10-25/agents/h08-process/scratch/result.json` (exact same content as you return), so the parent has a copy if the hand-back is truncated.

## Structured hunter result

Return exactly one JSON object, with no surrounding prose:

```json
{
  "units": [
    {
      "coverage_id": "one assigned ID",
      "disposition": "covered|candidate|blocked",
      "reviewed_paths": ["repo/relative/path"],
      "checks": [
        {
          "agent_id": "canonical owner of this check",
          "reviewed_paths": ["repo/relative/path owned by this check"],
          "invariant": "specific control checked for this unit",
          "method": "source|local",
          "result": "what source or the bounded check established",
          "artifact": "agents/<agent-id>/artifacts/file for local, null for source"
        }
      ],
      "candidate_fingerprints": [],
      "unresolved": []
    }
  ],
  "candidates": [],
  "hardening": ["concrete non-finding note"],
  "uncovered": [
    {
      "surface": "...",
      "boundary": "...",
      "subsystem": "...",
      "attack_class": "...",
      "starting_paths": ["repo/relative/path"],
      "reason": "why this needs its own deterministic coverage unit"
    }
  ]
}
```

Each `candidates` entry is schema-shaped except that it uses `proposed_verdict` in place of `verdict`:

- `proposed_verdict: "confirmed"`: include every field required by the `confirmed` branch of `report-schema.json` other than `verdict`: `fingerprint`, title, description, `root_cause`, `intended_behavior`, ordered `trace`, `evidence`, `conditions`, target-neutral `execution`, `remediation`, `severity`, and `confidence`. The execution instructions describe only the bounded local check already performed. `payloads` holds the minimum test input, fixture, or native invocation. `observed_result` records actual local output. Overall severity must not exceed observed impact.
- `proposed_verdict: "needs_validation"`: include every field required by that schema branch other than `verdict`: `fingerprint`, title, description, `claimed_root_cause`, ordered `trace`, `evidence`, nonempty `blockers`, and `validation_plan` with at least one applicable `local` or `deployment` step. Do not invent an inapplicable context. Do not include severity, execution, remediation, reason, or a confirmed `root_cause`. `deployment` is an owner-observed check, not a request to probe a live target.

Every assigned coverage ID appears exactly once in `units`. A `covered` unit needs an owner, nonempty `reviewed_paths` and `checks`, no unresolved fact, and no candidate. A `candidate` unit has the same owned evidence and is the only state that carries linked fingerprints. A `blocked` unit is an owned partial review with nonempty paths, checks, and unresolved facts but no fingerprint. All source paths are repository-relative, never absolute or traversal paths. A trace with several entries begins at `entrypoint`, ends at `sink`, and labels intermediate steps `propagation`. Every check has its own canonical lowercase `agent_id` and nonempty `reviewed_paths`; the unit-level list is exactly the union of those owned paths. A `source` check uses `artifact: null`. A `local` check uses one successfully parent-promoted regular file beneath `agents/<check.agent_id>/artifacts/`; this permits a verifier to add independently owned evidence without taking ownership from the hunter. Never link scratch, an output-root file, or another check owner's artifact.

### `confirmed` branch of report-schema.json (verbatim)

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

### `needs_validation` branch of report-schema.json (verbatim)

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
