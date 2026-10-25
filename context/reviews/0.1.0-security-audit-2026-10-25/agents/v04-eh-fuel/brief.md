# Candidate-verifier brief: v04-eh-fuel

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

## 2. The candidate (from hunter `h17-eh-advisories`; `proposed_verdict` is the hunter's proposal, not a decision)

```json
{
  "proposed_verdict": "needs_validation",
  "fingerprint": "wasmtime-49.0.0:GHSA-m63x-6p34-q65x:try_table-catch-fuel:src/wasi_python/_engines.py:_engine",
  "title": "Shipped binaries carry 44,791 try_table sites run on a metered wasmtime 49.0.0 engine affected by GHSA-m63x-6p34-q65x (fuel dropped on the catch path)",
  "description": "A metered call compiles python.wasm (or the snapshot) on an engine with consume_fuel and wasmtime's default exception support, under the wasmtime 49.0.0 the pin resolves to. GHSA-m63x-6p34-q65x (fixed 49.0.1) says Cranelift's fuel accounting on the catch path of a call inside a try_table can drop the fuel the callee used, resetting to the fuel left before the call. The shipped code has 44,791 try_table instructions in 7,905 functions, from C++ exceptions and setjmp/longjmp built with the new exception-handling proposal, and guest Python reaches them through the compiled-in packages. So the advisory's preconditions are met, and a guest may spend more instructions than its fuel cap counts. SECURITY.md counts running past the fuel cap as in scope. How much fuel a Python-reachable catch path drops, and whether it compounds, was not measured. The default deadline still bounds wall-clock time; a call with fuel and deadline_s=None relies on fuel alone.",
  "claimed_root_cause": "The runner's dependency pin (pyproject.toml wasmtime>=49,<50, resolved to 49.0.0 in uv.lock) admits a wasmtime whose Cranelift fuel accounting is wrong on try_table catch paths, while the build's -fwasm-exceptions flags put try_table on every caught C++ exception and longjmp path, and _engine leaves exceptions enabled on the metered engine. The runner carries no mitigation for this advisory, unlike its shadows for the filesystem advisories.",
  "trace": [
    {
      "kind": "entrypoint",
      "file": "recipes/wasi-scipy.cross",
      "line": 44,
      "scope": "C++ and sjlj build flags",
      "description": "Compiled-in C++ is built with -fwasm-exceptions -fexceptions and -wasm-use-legacy-eh=false (C with -wasm-enable-sjlj at line 39), so guest Python calls that throw and catch in C++, or longjmp, run try_table catch paths."
    },
    {
      "kind": "propagation",
      "file": "scripts/steps/60_link.sh",
      "line": 129,
      "scope": "link",
      "description": "python.wasm is linked with -fwasm-exceptions; the shipped module has 44,791 try_table, 26,569 throw_ref and 2 throw instructions, and +exception-handling in target_features."
    },
    {
      "kind": "propagation",
      "file": "uv.lock",
      "line": 1049,
      "scope": "wasmtime pin",
      "description": "wasmtime-py resolves to 49.0.0, inside GHSA-m63x's affected range (fixed in 49.0.1)."
    },
    {
      "kind": "propagation",
      "file": "src/wasi_python/_engines.py",
      "line": 122,
      "scope": "_engine",
      "description": "The metered engine sets consume_fuel and leaves wasm exceptions and the Cranelift compiler at their defaults, which is the advisory's configuration."
    },
    {
      "kind": "sink",
      "file": "src/wasi_python/_call.py",
      "line": 416,
      "scope": "metered call",
      "description": "The store's fuel is the instruction cap the runner promises; per the advisory, fuel spent in a callee that unwinds to a try_table catch can be lost, so the cap and fuel_used (line 511) can under-count."
    }
  ],
  "evidence": [
    {
      "file": "context/research/2026-10-18-wasmtime-49-advisories/advisories/GHSA-m63x-6p34-q65x.json",
      "line": 1,
      "description": "Advisory: Cranelift drops fuel on try_table catch and call_ref; affects 49.0.0, fixed 49.0.1; only guests with try_table or call_ref are affected; needs consume_fuel."
    },
    {
      "file": "src/wasi_python/_engines.py",
      "line": 122,
      "description": "cfg.consume_fuel = metered; no wasm_exceptions(False) or other override."
    },
    {
      "file": "pyproject.toml",
      "line": 18,
      "description": "dependencies = [\"wasmtime>=49,<50\"]."
    },
    {
      "file": "recipes/wasi-numpy.cross",
      "line": 37,
      "description": "numpy C++ built with -fwasm-exceptions -fexceptions on the new EH encoding."
    },
    {
      "file": "scripts/steps/80_snapshot.sh",
      "line": 18,
      "description": "The snapshot is made with -W exceptions=y; its code section has the same try_table count."
    },
    {
      "file": "SECURITY.md",
      "line": 18,
      "description": "In scope: a guest that runs past its deadline, fuel, memory or output cap."
    }
  ],
  "blockers": [
    "Not measured: how much fuel one Python-reachable try_table catch path loses under 49.0.0, and whether any compiled-in path nests catches so the loss compounds. I stopped at the binary and configuration preconditions and built no guest program to exercise the defect.",
    "No wasmtime-py at 49.0.1 or later is installed to diff fuel counts against; only the wasmtime CLI 49.0.3 is under build/tools."
  ],
  "validation_plan": {
    "local": "The owner runs a differential fuel count. Take one fixed guest script that triggers a C++ exception caught inside a compiled-in package N times, for small N (1, 10, 100). Read fuel_used from run(..., fuel=<large>, deadline_s=<short>) under wasmtime-py 49.0.0. Run the same module with the same fuel through the pinned wasmtime CLI 49.0.3 (-W fuel=...), or a wasmtime-py on 49.0.1 or later, and compare. If 49.0.0 reports less fuel per N than the fixed engine, the cap under-counts. Keep N and the deadline small.",
    "deployment": "The owner confirms whether PyPI now has a wasmtime-py on wasmtime 49.0.1 or later (or 50.x, see the moving-to-wasmtime-50 memo) and moves the pin's floor past the fix. Until then, document that the fuel cap is advisory on 49.0.0 for code paths that throw and catch, and keep a finite deadline_s beside fuel."
  }
}
```

## 3. The linked coverage unit(s) and the hunter's checks (artifact paths are relative to `context/reviews/0.1.0-security-audit-2026-10-25`)

```json
[
  {
    "coverage_id": "build%2Fartifacts%2Fpython.wasm%23try_table::src%2Fwasi_python%2F_engines.py%23_engine::build%2Fartifacts::MEMORY-SAFETY-AND-BINARY.md%23JIT%20and%20generated-code%20consistency",
    "surface": "build/artifacts/python.wasm#try_table, call_ref and tag section (and python-snapshot.wasm), compiled by src/wasi_python/_engines.py#_engine",
    "boundary": "src/wasi_python/_engines.py#_engine (consume_fuel on the metered engine; exceptions and function references left at wasmtime 49.0.0's defaults, which enable them) and the wasmtime>=49,<50 pin resolving to 49.0.0",
    "agent_id": "h17-eh-advisories",
    "local_checks": [
      {
        "agent_id": "h17-eh-advisories",
        "reviewed_paths": [
          "build/artifacts/python.wasm",
          "build/artifacts/python-snapshot.wasm"
        ],
        "invariant": "GHSA-p79w-pv2r-29qp precondition: the module declares an odd number of exception tags (defined plus imported)",
        "method": "local",
        "result": "Read-only section parse of both shipped binaries: the tag section (id 13, 5 bytes) defines exactly 2 tags, both type 6, and no tag is imported (all 43 imports are functions). 2 is even, so the VMContext misalignment precondition is not met by the current artifacts under wasmtime 49.0.0. Target not read-only mounted; the parse ran with the system python3 -I on the files, executing no target code.",
        "artifact": "agents/h17-eh-advisories/artifacts/evidence/eh_sections.json"
      },
      {
        "agent_id": "h17-eh-advisories",
        "reviewed_paths": [
          "build/artifacts/python.wasm",
          "build/artifacts/python-snapshot.wasm",
          "src/wasi_python/_engines.py"
        ],
        "invariant": "GHSA-wjc8-633q-pwxr precondition: a module (guest-supplied or shipped) registers a long chain of recursive types whose drop recurses in the host type registry",
        "method": "local",
        "result": "Both binaries' type sections hold 858 entries, all plain func types: no explicit rec group, no sub/sub-final declaration, supertype chain depth 0, and no typed reference (0x63/0x64) in any signature (only one exnref, 0x69), so no type refers to another and no chain exists. The guest is Python inside python.wasm and has no API to compile or instantiate a wasm module; the only other module the runner compiles is the fixed _CHECK_WAT (src/wasi_python/_engines.py:47-56), three func types. Precondition not met.",
        "artifact": "agents/h17-eh-advisories/artifacts/evidence/eh_sections.json"
      },
      {
        "agent_id": "h17-eh-advisories",
        "reviewed_paths": [
          "build/artifacts/python.wasm"
        ],
        "invariant": "GHSA-m63x-6p34-q65x precondition: the guest bytecode contains try_table or call_ref",
        "method": "local",
        "result": "llvm-objdump -d (wasi-sdk 34) over python.wasm counted 31,968,592 instructions in 89,061 functions: try_table 44,791 (in 7,905 functions), throw_ref 26,569, throw 2 (one in __wasm_longjmp, one in _Unwind_RaiseException), call_ref 0, return_call_ref 0. target_features includes +exception-handling. The try_table precondition is met; call_ref is absent.",
        "artifact": "agents/h17-eh-advisories/artifacts/evidence/eh_opcount_python.txt"
      },
      {
        "agent_id": "h17-eh-advisories",
        "reviewed_paths": [
          "build/artifacts/python-snapshot.wasm"
        ],
        "invariant": "GHSA-m63x-6p34-q65x precondition holds for the snapshot too",
        "method": "local",
        "result": "Same counts in python-snapshot.wasm: try_table 44,791 in 7,905 functions, throw_ref 26,569, throw 2, call_ref 0; +exception-handling in target_features. The Wizer snapshot keeps the code section unchanged.",
        "artifact": "agents/h17-eh-advisories/artifacts/evidence/eh_opcount_python-snapshot.txt"
      },
      {
        "agent_id": "h17-eh-advisories",
        "reviewed_paths": [
          "src/wasi_python/_engines.py",
          "uv.lock",
          "pyproject.toml",
          "src/wasi_python/_call.py",
          "src/wasi_python/runner.py",
          "src/wasi_python/_limits.py",
          "context/research/2026-10-18-wasmtime-49-advisories/advisories/GHSA-m63x-6p34-q65x.json",
          "context/research/2026-10-18-wasmtime-49-advisories/advisories/GHSA-p79w-pv2r-29qp.json",
          "context/research/2026-10-18-wasmtime-49-advisories/advisories/GHSA-wjc8-633q-pwxr.json"
        ],
        "invariant": "The metered engine under the resolved wasmtime is outside GHSA-m63x's affected range, or fuel is not the only bound on a metered call",
        "method": "source",
        "result": "_engine sets only consume_fuel=metered, epoch_interruption, the async stack and max_wasm_stack (_engines.py:110-127), so exceptions stay at wasmtime's default (on since 47.0.0) and the compiler is the default Cranelift: the advisory's configuration. pyproject.toml:18 pins wasmtime>=49,<50 and uv.lock:1048-1049 resolves 49.0.0, inside the affected range (fixed 49.0.1). A metered call sets fuel at _call.py:412-416 and reports fuel_used at :511. The deadline defaults from limits (runner.py:574-575) and epoch interruption is not affected by the advisory, so a call with a deadline stays wall-clock bounded; an embedder that passes fuel with deadline_s=None has fuel as its only instruction bound.",
        "artifact": null
      },
      {
        "agent_id": "h17-eh-advisories",
        "reviewed_paths": [
          "recipes/wasi-numpy.cross",
          "recipes/wasi-pandas.cross",
          "recipes/wasi-scipy.cross",
          "recipes/wasi-matplotlib.cross",
          "scripts/steps/60_link.sh",
          "scripts/steps/80_snapshot.sh"
        ],
        "invariant": "Where the try_table code comes from and whether ordinary guest Python can reach it",
        "method": "source",
        "result": "The cross files compile C++ with -fwasm-exceptions -fexceptions and -wasm-use-legacy-eh=false (wasi-numpy.cross:37, wasi-pandas.cross:31, wasi-scipy.cross:44, wasi-matplotlib.cross:39), and C with -wasm-enable-sjlj (wasi-scipy.cross:39, wasi-matplotlib.cross:37); 60_link.sh:129 links with -fwasm-exceptions; 80_snapshot.sh:18 runs Wizer with -W exceptions=y. So every caught C++ exception and every setjmp/longjmp return in the compiled-in packages goes through a try_table catch, and guest Python reaches those paths through ordinary package calls. Python's own exceptions do not use try_table (CPython signals them by return value). The 2026-10-18 advisories memo's statement that the module enables no exception proposal predates these flags and is out of date.",
        "artifact": null
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

<!-- RESOURCE-EXHAUSTION-AND-AVAILABILITY.md#Core discipline -->
## Core discipline (include in every agent prompt for this domain)

```
- Require an input-to-cost path, a missing effective bound, and impact on another user, shared service, safety function, or operator-owned spend. Self-limiting work in the requester's own process is not a service vulnerability.
- A missing rate limit is not enough. Check body/message/file caps, concurrency, queues, deadlines, database constraints, upstream gateways, and per-tenant quotas before calling a path unbounded.
- Do not run stress, saturation, or production tests. Use asymptotic analysis, small boundary fixtures, mocked paid calls, strict local resource limits, and deterministic cancellation tests.
- State attacker cost, service work, persistence, scope, and recovery. One bounded input with superlinear or persistent shared effect is materially different from sustained volume.
- Use `confirmed` for source-visible bounds failures demonstrated safely. Use `needs_validation` when upstream caps, deployed topology, autoscaling, paid quota, or recovery behavior is outside the repository.
```

<!-- RESOURCE-EXHAUSTION-AND-AVAILABILITY.md#Validation rules -->
## Validation rules (apply before reporting ANY finding here)

1. Name untrusted input, requester work, service amplification or retained resource, shared blast radius, and recovery. Missing limits without concrete shared impact are hardening.
2. Confirm no source-visible upstream, parser, queue, tenant, or framework bound prevents the path. Unknown deployed controls require `needs_validation`.
3. For superlinear behavior, establish the accepted complexity and bounded local growth. For leaks, show repeatable retention after cleanup should occur. For fatal paths, identify process/supervisor isolation.
4. Prioritize by low requester work, unauthenticated reachability, cross-tenant scope, persistence, and poor recovery; do not validate with availability impact.
5. Return `confirmed` only with safe local proof and meaningful shared effect. Return `needs_validation` with the exact upstream limit, topology, quota, or recovery observation an owner must check.


## 6. Execution boundary, paths, allowlist

- Target root: `.` (all paths in your record are repository-relative to it). Never edit a file under it. Never run `uv sync`, plain `uv run`, `scripts/00_download.sh`, `scripts/build.sh` or `scripts/steps/*.sh`, `release/set_key.py`, `gh workflow run`, `git push`, `pytest --accept*`, or anything writing under `context/`. Never download from the internet; read-only `gh` GET calls against the project's own repository are allowed.
- Your scratch (the only place you write): `context/reviews/0.1.0-security-audit-2026-10-25/agents/v04-eh-fuel/scratch/`. Parent-owned artifacts (you never write): `context/reviews/0.1.0-security-audit-2026-10-25/agents/v04-eh-fuel/artifacts/`. Allowlist for promotion: regular files directly under `scratch/evidence/` named `*.txt`, `*.json`, `*.log` or `*.py`, at most 24 files, 512 KiB each, 8 MiB total; after you finish the parent promotes them to `artifacts/evidence/<name>`.
- Before any target-controlled execution confirm `./build/lane.lock` does not exist. Wrap every target-controlled run as: `ulimit -t 300 -f 4000000 -n 4096; /usr/bin/env -i PATH=/usr/bin:/bin HOME=context/reviews/0.1.0-security-audit-2026-10-25/agents/v04-eh-fuel/scratch/home TMPDIR=context/reviews/0.1.0-security-audit-2026-10-25/agents/v04-eh-fuel/scratch/tmp WASI_PYTHON_CACHE=context/reviews/0.1.0-security-audit-2026-10-25/agents/v04-eh-fuel/scratch/cache /usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' ./.venv/bin/python -I <script under scratch>` (make the three folders first; give each child a wall-clock bound with `subprocess.run(timeout=...)` from a trusted driver). This platform cannot enforce a read-only target mount or a memory rlimit; never point a writable grant or root at the target or at a real cache; say in the record's `execution.instructions` that the target was not read-only mounted. If a control you need cannot be enforced, do not execute; keep the exact blocker as `needs_validation`.
- You may read the hunter's evidence files under `context/reviews/0.1.0-security-audit-2026-10-25/agents/h17-eh-advisories/artifacts/evidence/` (read-only) and re-run its harness in your own scratch. A verifier-owned `local` check must cite a file you wrote under your own `scratch/evidence/`.
- Keep probes small and short (deadlines of a few seconds, small sizes).

## 7. Prior records with the same fingerprint

None (no prior run).

## 8. Result contract

Return exactly one JSON object and no surrounding prose: `{"decision": "confirmed|needs_validation|rejected", "record": { ... }}` where `record` exactly matches the decision's branch below (`additionalProperties: false`; do not carry `proposed_verdict`, `_hunter` or any other wrapper field; `verdict` must equal `decision`). Also write the same object to `context/reviews/0.1.0-security-audit-2026-10-25/agents/v04-eh-fuel/scratch/result.json`, writing it incrementally as you settle each part so a partial file exists if your final message is cut off. Use plain factual language.

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
