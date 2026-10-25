# Hunter brief: h15-env-loaders

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

Agent id: `h15-env-loaders`. Target root: `.` (all paths in your result are repository-relative to it).

```json
[
  {
    "coverage_id": "build%2Fartifacts%2Fpython-stdlib.zip%23env-driven-loaders::src%2Fwasi_python%2F_limits.py%23_check_inputs::build%2Fartifacts::MEMORY-SAFETY-AND-BINARY.md%23Library%2C%20plugin%2C%20and%20executable%20search-order%20trust",
    "canonical_refs": {
      "surface": "build/artifacts/python-stdlib.zip#env-driven-loaders",
      "boundary": "src/wasi_python/_limits.py#_check_inputs",
      "subsystem": "build/artifacts",
      "attack_class": "MEMORY-SAFETY-AND-BINARY.md#Library, plugin, and executable search-order trust"
    },
    "surface": "build/artifacts/python-stdlib.zip#third-party packages' environment-driven loaders (numpy, scipy, pandas, sklearn, joblib, statsmodels, matplotlib, lxml, networkx, sympy, mpmath, reportlab, pypdf, pillow, fonttools, jinja2, tqdm, regex and the rest of the 60+ packages), plus a re-check of the stdlib list",
    "boundary": "src/wasi_python/_limits.py#_check_inputs (env keys pass unchecked apart from name syntax) and recipes/reactor_main.c#init_interpreter (isolated config: ignore_environment covers only CPython's documented PYTHON* variables)",
    "subsystem": "build/artifacts",
    "attack_class": "Chained trust and library search-order trust: an env= value naming a guest-writable folder (a reused root or writable grant) that a bundled package reads at import or first use to exec, spec_from_file_location, runpy, SourceFileLoader, or load entry points or plugins, outside the read-only import-path rule",
    "starting_paths": [
      "build/artifacts/python-stdlib.zip",
      "scripts/make_stdlib_zip.py",
      "scripts/steps/70_zip.sh",
      "src/wasi_python/_limits.py",
      "src/wasi_python/_call.py",
      "recipes/reactor_main.c",
      "recipes/reactor_bootstrap.py"
    ],
    "ordinary_attack_class_block": "ATTACK-CLASSES.md#Chained vulnerabilities and trust boundaries",
    "selected_companion_blocks": [
      "MEMORY-SAFETY-AND-BINARY.md#Core discipline",
      "MEMORY-SAFETY-AND-BINARY.md#Library, plugin, and executable search-order trust",
      "MEMORY-SAFETY-AND-BINARY.md#Universal moves",
      "MEMORY-SAFETY-AND-BINARY.md#Validation rules",
      "DATA-ISOLATION-AND-LIFECYCLE.md#Core discipline",
      "DATA-ISOLATION-AND-LIFECYCLE.md#Stale authorization and derived copy use",
      "DATA-ISOLATION-AND-LIFECYCLE.md#Restore reintroduces invalid state",
      "DATA-ISOLATION-AND-LIFECYCLE.md#Universal moves",
      "DATA-ISOLATION-AND-LIFECYCLE.md#Validation rules"
    ],
    "excluded_blocks": [
      {
        "block": "MEMORY-SAFETY-AND-BINARY.md#JIT and generated-code consistency",
        "reason": "only pure-Python and data loading paths in the zip are in question; the binaries' compiler properties are their own unit"
      }
    ]
  }
]
```

## 4. Selected attack-class blocks (verbatim)

<!-- ATTACK-CLASSES.md#Chained vulnerabilities and trust boundaries -->
**Chained vulnerabilities and trust boundaries** (subagent_type: `general`) Individually allowed or contained behavior can become a vulnerability when another component or lifecycle step relies on a stronger guarantee:
- **Multi-step boundary failures**: Map what a low-privilege principal may read, write, invoke, and retain, then connect only concrete outputs to later trust decisions. Confirm each prerequisite and do not assume a downstream effect.
- **Cross-component trust gaps**: Component A validates input and passes it to component B. Compare the exact guarantee A produces with what B assumes, including truncation, type coercion, normalization, tenant scope, and plugin/extension access.
- **Second-order use**: Data safe when stored may become dangerous in a later context. A field name becomes a JSON path, a slug becomes a file path, escaped text enters raw rendering, or a stored string becomes a URL, regex, template, or policy expression.
- **Scope and capability growth**: Token, API-key, plugin, OAuth, MCP, or AI capabilities become broader after delegation, refresh, caching, role change, or composition. Name the concrete operation the resulting principal should not have.
- **Timing and ordering**: Review setup, migration, soft-delete, revoke/cache expiry, check/use, and validate/consume windows. Confirm stale state is accepted before reporting.
- **Rollback and recovery**: Undelete, restore, revision rollback, and cancellation must apply current ownership, validation, and authorization. Confirm which invalid state is restored.

<!-- MEMORY-SAFETY-AND-BINARY.md#Core discipline -->
## Core discipline (include in every agent prompt for this domain)

```
- Re-derive every bound and lifetime from attacker-controlled inputs and all callers. Validate against the worst accepted case, not a typical test vector.
- A panic, sanitizer finding, or crash proves a defect only when a realistic untrusted input reaches it. Do not infer memory corruption, code execution, or shared availability impact from a label alone.
- Validate in a local harness with sanitizers, deterministic concurrency tests, existing fuzz targets, and debugger-assisted fault classification. Stop after proving the violated invariant and observable impact; do not develop post-corruption techniques.
- Assembly, JIT code, custom allocators, intra-object accesses, and foreign libraries can escape sanitizer coverage. Identify which relevant instructions are instrumented.
- Classify as `confirmed` only after source evidence and bounded local validation establish the defect and effect. Use `needs_validation` when ABI, allocator, architecture, feature, deployment, or reachability facts remain unknown.
```

<!-- MEMORY-SAFETY-AND-BINARY.md#Library, plugin, and executable search-order trust -->
**Library, plugin, and executable search-order trust** A privileged process loads a library, plugin, runtime image, or helper from a path writable by a less-trusted principal, or resolves a bare name through an attacker-influenceable working directory or environment. Compare intended installation ownership with each fallback and compatibility search path. A user loading their own plugin into their own process is not a boundary violation.

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

<!-- DATA-ISOLATION-AND-LIFECYCLE.md#Core discipline -->
## Core discipline (include in every agent prompt for this domain)

```
- A tenant or owner field on a record is not isolation. Find the query, key, path, policy, or row-level control that enforces it for each read and write path.
- Trace derived copies. Sanitized primary data can become unsafe in search, cache, analytics, export, previews, logs, replicas, and backups with different ACL and retention rules.
- Deletion and revocation are lifecycle contracts. Check current, historical, cached, indexed, exported, restored, and queued copies within the product's stated boundary.
- Privacy or retention preference is not automatically a security vulnerability. Require an explicit data-access boundary or deletion/revocation guarantee and an unauthorized reader or later operation.
- Use `confirmed` for complete source-visible lineage and bounded dummy-tenant tests. Use `needs_validation` when external storage policy, retention, CDN behavior, replica lag, or backup access is unavailable.
```

<!-- DATA-ISOLATION-AND-LIFECYCLE.md#Stale authorization and derived copy use -->
**Stale authorization and derived copy use** Membership removal, ACL update, consent withdrawal, secret revocation, or role downgrade does not invalidate sessions, caches, subscriptions, jobs, or materialized data that continue to authorize future operations.

<!-- DATA-ISOLATION-AND-LIFECYCLE.md#Restore reintroduces invalid state -->
**Restore reintroduces invalid state** Backup, undo, undelete, or replica recovery restores data, credentials, memberships, or permissions that current policy no longer allows. Re-authorize restored state and reapply lifecycle changes made after the snapshot.

<!-- DATA-ISOLATION-AND-LIFECYCLE.md#Universal moves -->
## Universal moves (apply across the above)

- Pick one protected record and draw primary write, query, cache, index, event, export, backup, deletion, and restore paths. Mark principal and tenant at every edge.
- Compare two dummy tenants through the same local service methods, then repeat after ACL change, deletion, account switch, and restore. Do not use real user data.
- Start at bypass clients, background jobs, migrations, global uniqueness, and cache keys. These paths commonly omit request-scoped identity that interactive endpoints carry.

<!-- DATA-ISOLATION-AND-LIFECYCLE.md#Validation rules -->
## Validation rules (apply before reporting ANY finding here)

1. Name attacker or lower-trust principal, protected data/state, affected owner/tenant, alternate copy or operation, and unauthorized disclosure or mutation.
2. Cite both intended source-of-truth policy and the path that omits or disagrees with it. Confirm another layer does not enforce the same tenant/lifecycle condition.
3. Use local dummy tenants and non-sensitive fixtures to prove cross-scope access or stale lifecycle behavior. Stop at the minimum observable record or operation.
4. If external cache, object storage, replicas, analytics, backup, or retention policy is required, classify `needs_validation` and state the owner-observed check.
5. Return `confirmed` only with complete lineage and concrete boundary impact. Return `needs_validation` with the exact unresolved storage, ACL, invalidation, retention, or restore fact.


## 5. Excluded blocks and reasons

- `MEMORY-SAFETY-AND-BINARY.md#JIT and generated-code consistency`: only pure-Python and data loading paths in the zip are in question; the binaries' compiler properties are their own unit

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
- `build%2Fartifacts%2Fpython.wasm%23try_table::src%2Fwasi_python%2F_engines.py%23_engine::build%2Fartifacts::MEMORY-SAFETY-AND-BINARY.md%23JIT%20and%20generated-code%20consistency`
- `github-release%2Fv0.1.0%23assets::.github%2Fworkflows%2Frelease.yml%23same-bytes::release::SUPPLY-CHAIN-AND-RELEASE.md%23Build-to-promotion%20substitution`
- `src%2Fwasi_python%2F_call.py%23_poll_oneoff::src%2Fwasi_python%2F_call.py%23_poll_plan::src%2Fwasi_python::MEMORY-SAFETY-AND-BINARY.md%23Out-of-bounds%20read%20or%20write`

## 9. Paths, sandbox, allowlist, and the result contract

- Your scratch directory (the only place you may write): `context/reviews/0.1.0-security-audit-2026-10-25/agents/h15-env-loaders/scratch/`
- Your retained artifacts directory (parent-owned; you never write it): `context/reviews/0.1.0-security-audit-2026-10-25/agents/h15-env-loaders/artifacts/`
- Promotion allowlist: regular files directly under `scratch/evidence/` named `*.txt`, `*.json`, `*.log` or `*.py`, at most 24 files, 512 KiB each, 8 MiB in total. After you finish, the parent promotes them to `artifacts/evidence/<name>`; a `local` check's `artifact` field must name `agents/h15-env-loaders/artifacts/evidence/<name>` for a file you wrote to `scratch/evidence/<name>`.
- Never edit any file under the target. Never run `uv sync`, plain `uv run`, `scripts/00_download.sh`, `scripts/build.sh` or any `scripts/steps/*.sh`, `release/set_key.py`, `gh workflow run`, `git push`, `pytest --accept*`, or anything writing under `context/`. Never download from the internet. Read-only `gh` GET calls against the project's own repository are allowed.
- Target-controlled execution (the runner through Python, a guest inside wasmtime, a pytest node id) is allowed only as a bounded local check, wrapped like this, with the three directories under your scratch: `ulimit -t 300 -f 4000000 -n 4096; /usr/bin/env -i PATH=/usr/bin:/bin HOME=context/reviews/0.1.0-security-audit-2026-10-25/agents/h15-env-loaders/scratch/home TMPDIR=context/reviews/0.1.0-security-audit-2026-10-25/agents/h15-env-loaders/scratch/tmp WASI_PYTHON_CACHE=context/reviews/0.1.0-security-audit-2026-10-25/agents/h15-env-loaders/scratch/cache /usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' ./.venv/bin/python -I <your script under scratch>` (create `scratch/home`, `scratch/tmp`, `scratch/cache` first). Use `subprocess.run(..., timeout=...)` from a trusted driver when a step needs a wall-clock bound. This platform cannot enforce a read-only target mount or a memory rlimit: the project's own memory cap bounds the guest, and you must not point any writable grant or root at the target. Record in each local check that the target was not read-only mounted. If a check needs a control you cannot enforce, do not run it: return `needs_validation` with that blocker.
- Pytest: use `./.venv/bin/python -I -m pytest <nodeid> -p no:cacheprovider --progress-latest context/reviews/0.1.0-security-audit-2026-10-25/agents/h15-env-loaders/scratch/latest.json` inside the same wrapper; never a whole tier.
- Keep disk use small; delete large files you create under scratch before finishing.

Also write your final JSON object to `context/reviews/0.1.0-security-audit-2026-10-25/agents/h15-env-loaders/scratch/result.json` (exact same content as you return), so the parent has a copy if the hand-back is truncated.

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
