# Candidate-verifier brief: v03-sysconfigdata

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

## 2. The candidate (from hunter `h03-private-dirs`; `proposed_verdict` is the hunter's proposal, not a decision)

```json
{
  "proposed_verdict": "confirmed",
  "fingerprint": "runner-env.sysconfig-PYTHON-SYSCONFIGDATA-PATH.loads-code-outside-import-path-rules",
  "title": "env= _PYTHON_SYSCONFIGDATA_PATH makes a module planted in a reused root run on `import pandas` in a later call",
  "description": "The runner promises that code planted in a root never runs at start-up or on import in a later call, and enforces it by an isolated interpreter (PYTHON* variables ignored, site off) and by allowing import_path entries only from read-only grants with nothing writable under them. CPython 3.15's sysconfig honours the private variable _PYTHON_SYSCONFIGDATA_PATH without checking sys.flags.ignore_environment and execs `_sysconfigdata_<abi>_<platform>_<multiarch>` from that folder. The runner lays env= over the guest's environment without any key policy, so an embedder that passes this variable (for instance copied from a cross-build host environment with the CLI's --env KEY, or by forwarding its environment) pointing at a folder in a reused root or writable grant turns a file an earlier guest left there into code run in the later call on a plain `import pandas` (also scipy, sklearn, joblib, statsmodels), on both binaries. The security model lists only HOME and PYTHONTZPATH overrides as unprotected.",
  "root_cause": "sysconfig._get_sysconfigdata reads os.environ['_PYTHON_SYSCONFIGDATA_PATH'] regardless of isolated mode and loads a module from that directory with PathFinder + exec_module; the runner's env check (_limits._check_inputs) rejects only empty keys and '=', and nothing applies the import_path rules (read-only grant, nothing writable under it) to this code-loading variable.",
  "intended_behavior": "Every folder the guest's interpreter loads code from is subject to the import_path rules: a read-only grant with no writable root, grant or mount under or inside it; an env= entry that would load code from elsewhere is refused before any work (or ignored, as isolated mode ignores PYTHONPATH).",
  "trace": [
    {
      "kind": "entrypoint",
      "file": "src/wasi_python/_limits.py",
      "line": 139,
      "scope": "_check_inputs",
      "description": "env keys are checked only for emptiness and '='; _PYTHON_SYSCONFIGDATA_PATH passes."
    },
    {
      "kind": "propagation",
      "file": "src/wasi_python/_call.py",
      "line": 452,
      "scope": "_instance",
      "description": "wasi.env = BASE_ENV + HOME + env= laid over them, unfiltered (the session's opening does the same at _sessions.py:999)."
    },
    {
      "kind": "propagation",
      "file": "recipes/reactor_bootstrap.py",
      "line": 143,
      "scope": "run",
      "description": "The reactor copies the WASI environment into os.environ for the program."
    },
    {
      "kind": "propagation",
      "file": "build/pandas-3.0.6/pandas/compat/_constants.py",
      "line": 21,
      "scope": "module level",
      "description": "`import pandas` calls sysconfig.get_config_var('HOST_GNU_TYPE') at import."
    },
    {
      "kind": "propagation",
      "file": "build/Python-3.15.0/Lib/sysconfig/__init__.py",
      "line": 360,
      "scope": "_get_sysconfigdata",
      "description": "Reads _PYTHON_SYSCONFIGDATA_PATH from os.environ with no ignore_environment check."
    },
    {
      "kind": "sink",
      "file": "build/Python-3.15.0/Lib/sysconfig/__init__.py",
      "line": 343,
      "scope": "_import_from_directory",
      "description": "PathFinder.find_spec(name, [path]) then spec.loader.exec_module(module): the planted file in the reused root runs."
    }
  ],
  "evidence": [
    {
      "file": "docs/explanation/security-model.md",
      "line": 9,
      "description": "Policy: code planted in a root never runs at start-up or on import in a later call, on either binary."
    },
    {
      "file": "docs/explanation/security-model.md",
      "line": 82,
      "description": "Only env= overrides of HOME or PYTHONTZPATH are listed as not protected."
    },
    {
      "file": "recipes/reactor_main.c",
      "line": 179,
      "description": "Isolated config: the design relies on the interpreter ignoring environment-driven code paths."
    },
    {
      "file": "src/wasi_python/_places.py",
      "line": 176,
      "description": "_check_import_path: the control that confines code-loading folders to read-only grants, which this variable bypasses."
    },
    {
      "file": "build/Python-3.15.0/Lib/sysconfig/__init__.py",
      "line": 361,
      "description": "_import_from_directory(path, name) used whenever the variable is set."
    }
  ],
  "conditions": [
    {
      "kind": "system_configuration",
      "description": "The embedder passes env containing _PYTHON_SYSCONFIGDATA_PATH naming a guest folder that a previous call could write (a reused root, a writable grant, or a writable mount), e.g. by forwarding a cross-build host environment or with the CLI's --env _PYTHON_SYSCONFIGDATA_PATH."
    },
    {
      "kind": "data_state",
      "description": "An earlier, less trusted call on the same root or writable folder left `_sysconfigdata__wasi_wasm32-wasi.py` (or .pyc) there."
    },
    {
      "kind": "user_interaction",
      "description": "The later program imports pandas, scipy, sklearn, joblib or statsmodels, or calls sysconfig.get_config_var(s)."
    }
  ],
  "execution": {
    "attacker_perspective": "A guest in call 1 with a writable root writes one file; the embedder's later call on the same root, with the env entry, runs a program that only imports pandas.",
    "payloads": [
      "call 1: wasi_python.run(['-c', \"import os; os.makedirs('/data', exist_ok=True); open('/data/_sysconfigdata__wasi_wasm32-wasi.py','w').write(\\\"import sys\\\\nsys.stderr.write('PLANTED\\\\\\\\n')\\\\nbuild_time_vars={'installed_base':'/usr/local'}\\\\n\\\")\"], root=R)",
      "call 2: wasi_python.run(['-c', 'import pandas'], root=R, env={'_PYTHON_SYSCONFIGDATA_PATH': '/data'})"
    ],
    "instructions": [
      "Under env -i, sandbox-exec (deny network*), ulimit -t 300 -f 4000000 -n 4096, run .venv/bin/python -I sysconfigdata_path_check.py <scratch> with R under scratch.",
      "Compare each `import <pkg>` call with and without the env entry for 'PLANTED' on stderr."
    ],
    "observed_result": "Without the entry no planted code ran. With it, PLANTED was written to stderr in the later call on import of pandas, scipy, sklearn, joblib and statsmodels.api (snapshot) and pandas (plain binary); numpy and matplotlib imports did not trigger it."
  },
  "remediation": {
    "strategy": "Refuse (or drop) env keys that make the guest interpreter load code from a folder, at least _PYTHON_SYSCONFIGDATA_PATH, in the runner's argument check, with the message pointing to import_path; add a regression check that plants the module in call 1 and asserts call 2 raises ValueError before any work. Alternatively apply the import_path rules to its value (a read-only grant with nothing writable under it). Name the variable in the security model either way.",
    "code_changes": [
      {
        "file_name": "src/wasi_python/_limits.py",
        "fixed_code": "_CODE_FOLDER_ENV = frozenset({\"_PYTHON_SYSCONFIGDATA_PATH\"})  # sysconfig execs a module from it\n...\n            if not name or \"=\" in name:\n                raise ValueError(\"env key: illegal environment variable name\")  # never quoted\n            if name in _CODE_FOLDER_ENV:\n                raise ValueError(\n                    \"env key: _PYTHON_SYSCONFIGDATA_PATH loads code from a folder; \"\n                    \"name a read-only grant in import_path instead\"\n                )"
      }
    ]
  },
  "severity": {
    "likelihood": {
      "score": "low",
      "reason": "Requires a trusted embedder to pass a private, underscore-prefixed CPython variable naming a guest-writable folder; plausible only when forwarding a cross-build host environment or by explicit choice."
    },
    "impact": {
      "score": "medium",
      "reason": "Crosses the call-to-call boundary the policy promises: an earlier guest's code runs in a later call with that call's grants, tools, door and stdin; it stays inside the wasm sandbox and does not reach the host."
    },
    "overall_severity": "low"
  },
  "confidence": {
    "score": "high",
    "reason": "Source path is complete and the effect was observed in bounded local runs on both binaries, with controls that never ran the planted file."
  }
}
```

## 3. The linked coverage unit(s) and the hunter's checks (artifact paths are relative to `context/reviews/0.1.0-security-audit-2026-10-25`)

```json
[
  {
    "coverage_id": "src%2Fwasi_python%2F_call.py%23_preopens::src%2Fwasi_python%2F_places.py%23_judge_import_path::src%2Fwasi_python::ATTACK-CLASSES.md%23Chained%20vulnerabilities%20and%20trust%20boundaries::reused-root",
    "surface": "A root, writable grant or mount reused across calls: what an earlier guest leaves (modules, .pth, config files read by packages, HOME contents, /etc/xml/catalog, matplotlibrc, .cwasm) and what a later call does with it; env= overriding HOME, TMPDIR or PYTHON* variables",
    "boundary": "site off and -I semantics in the reactor, read-only import path with nothing writable under it, the fresh or read-only HOME, the judge's refusal of caches",
    "agent_id": "h03-private-dirs",
    "local_checks": [
      {
        "agent_id": "h03-private-dirs",
        "reviewed_paths": [
          "recipes/reactor_main.c",
          "recipes/reactor_bootstrap.py",
          "recipes/reportlab_start_up_stand_in.py"
        ],
        "invariant": "The reactor starts isolated: no site, no sys.path[0] for -c, a script or -m, PYTHON* variables ignored, only the zip on sys.path; reportlab's home-folder start-up files are pre-empted by stand-ins.",
        "method": "source",
        "result": "init_interpreter uses PyConfig_InitIsolatedConfig (reactor_main.c:179) with module_search_paths_set and site_import=0 (191-197); _reactor.run (reactor_bootstrap.py:140-226) runs a script file without inserting its folder (only a named directory or zip is inserted, documented); the session setup appends only the runner's checked import_path entries (234-245, _sessions.py:976-998). reportlab_mods/reportlab_settings stand-ins are packed in the zip.",
        "artifact": null
      },
      {
        "agent_id": "h03-private-dirs",
        "reviewed_paths": [
          "src/wasi_python/_places.py",
          "src/wasi_python/_call.py"
        ],
        "invariant": "An import_path entry is served only by a read-only grant, with no writable grant, mount or root under it or inside its grant, by guest path and by host identity.",
        "method": "source",
        "result": "_check_import_path (_places.py:176-227) and _judge_import_path (503-523) with _judge's read-only-inside-writable rule (374-381) hold this; the fresh HOME is a new 128-bit name under the root's /tmp made through a no-follow descriptor (_call.py:292-325, 348-371), so no earlier call can pre-populate it.",
        "artifact": null
      },
      {
        "agent_id": "h03-private-dirs",
        "reviewed_paths": [
          "src/wasi_python/_call.py",
          "src/wasi_python/_places.py",
          "recipes/reactor_main.c",
          "recipes/reactor_bootstrap.py",
          "docs/explanation/security-model.md"
        ],
        "invariant": "Two consecutive run calls on one writable root: nothing call 1 plants runs at start-up or on import in call 2, with defaults, with env= overrides of HOME, TMPDIR and PYTHON* variables, and with import_path entries, on both binaries.",
        "method": "local",
        "result": "reused_root_result.json: 34 planted files (site hooks, .pth, pyvenv.cfg at three levels, files under the root's own usr/local/lib/python3.15 written through the root descriptor, stdlib-name shadows, _sysconfigdata modules, reportlab hooks, matplotlibrc, .pdbrc). Defaults on snapshot and plain: none ran; sys.path is the zip only. HOME/TMPDIR/PYTHONPATH/PYTHONSTARTUP/PYTHONHOME/PYTHONUSERBASE/PYTHONBREAKPOINT/PYTHONINSPECT/MPLCONFIGDIR/MPLBACKEND overrides: only .pdbrc ran, when the program called breakpoint() (documented). import_path served by the root is refused. env _PYTHON_SYSCONFIGDATA_PATH=/ ran the planted /_sysconfigdata__wasi_wasm32-wasi.py (candidate).",
        "artifact": "agents/h03-private-dirs/artifacts/evidence/reused_root_result.json"
      },
      {
        "agent_id": "h03-private-dirs",
        "reviewed_paths": [
          "src/wasi_python/_call.py",
          "src/wasi_python/_limits.py",
          "src/wasi_python/_sessions.py",
          "build/Python-3.15.0/Lib/sysconfig/__init__.py",
          "build/pandas-3.0.6/pandas/compat/_constants.py"
        ],
        "invariant": "No env= entry turns a file planted in a reused root into code that runs on a plain import in a later call (the import path's read-only-grant rule cannot be bypassed through the environment).",
        "method": "local",
        "result": "sysconfigdata_path_result.json: with env={'_PYTHON_SYSCONFIGDATA_PATH': '/data'} a module planted by call 1 at /data/_sysconfigdata__wasi_wasm32-wasi.py runs on `import pandas`, `import scipy`, `import sklearn`, `import joblib`, `import statsmodels.api` (snapshot) and `import pandas` (plain); control calls without the entry never run it. sysconfig reads the variable without consulting sys.flags.ignore_environment and execs the module from that folder; the runner passes env keys through unchecked.",
        "artifact": "agents/h03-private-dirs/artifacts/evidence/sysconfigdata_path_result.json"
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

<!-- DATA-ISOLATION-AND-LIFECYCLE.md#Core discipline -->
## Core discipline (include in every agent prompt for this domain)

```
- A tenant or owner field on a record is not isolation. Find the query, key, path, policy, or row-level control that enforces it for each read and write path.
- Trace derived copies. Sanitized primary data can become unsafe in search, cache, analytics, export, previews, logs, replicas, and backups with different ACL and retention rules.
- Deletion and revocation are lifecycle contracts. Check current, historical, cached, indexed, exported, restored, and queued copies within the product's stated boundary.
- Privacy or retention preference is not automatically a security vulnerability. Require an explicit data-access boundary or deletion/revocation guarantee and an unauthorized reader or later operation.
- Use `confirmed` for complete source-visible lineage and bounded dummy-tenant tests. Use `needs_validation` when external storage policy, retention, CDN behavior, replica lag, or backup access is unavailable.
```

<!-- DATA-ISOLATION-AND-LIFECYCLE.md#Validation rules -->
## Validation rules (apply before reporting ANY finding here)

1. Name attacker or lower-trust principal, protected data/state, affected owner/tenant, alternate copy or operation, and unauthorized disclosure or mutation.
2. Cite both intended source-of-truth policy and the path that omits or disagrees with it. Confirm another layer does not enforce the same tenant/lifecycle condition.
3. Use local dummy tenants and non-sensitive fixtures to prove cross-scope access or stale lifecycle behavior. Stop at the minimum observable record or operation.
4. If external cache, object storage, replicas, analytics, backup, or retention policy is required, classify `needs_validation` and state the owner-observed check.
5. Return `confirmed` only with complete lineage and concrete boundary impact. Return `needs_validation` with the exact unresolved storage, ACL, invalidation, retention, or restore fact.


## 6. Execution boundary, paths, allowlist

- Target root: `.` (all paths in your record are repository-relative to it). Never edit a file under it. Never run `uv sync`, plain `uv run`, `scripts/00_download.sh`, `scripts/build.sh` or `scripts/steps/*.sh`, `release/set_key.py`, `gh workflow run`, `git push`, `pytest --accept*`, or anything writing under `context/`. Never download from the internet; read-only `gh` GET calls against the project's own repository are allowed.
- Your scratch (the only place you write): `context/reviews/0.1.0-security-audit-2026-10-25/agents/v03-sysconfigdata/scratch/`. Parent-owned artifacts (you never write): `context/reviews/0.1.0-security-audit-2026-10-25/agents/v03-sysconfigdata/artifacts/`. Allowlist for promotion: regular files directly under `scratch/evidence/` named `*.txt`, `*.json`, `*.log` or `*.py`, at most 24 files, 512 KiB each, 8 MiB total; after you finish the parent promotes them to `artifacts/evidence/<name>`.
- Before any target-controlled execution confirm `./build/lane.lock` does not exist. Wrap every target-controlled run as: `ulimit -t 300 -f 4000000 -n 4096; /usr/bin/env -i PATH=/usr/bin:/bin HOME=context/reviews/0.1.0-security-audit-2026-10-25/agents/v03-sysconfigdata/scratch/home TMPDIR=context/reviews/0.1.0-security-audit-2026-10-25/agents/v03-sysconfigdata/scratch/tmp WASI_PYTHON_CACHE=context/reviews/0.1.0-security-audit-2026-10-25/agents/v03-sysconfigdata/scratch/cache /usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' ./.venv/bin/python -I <script under scratch>` (make the three folders first; give each child a wall-clock bound with `subprocess.run(timeout=...)` from a trusted driver). This platform cannot enforce a read-only target mount or a memory rlimit; never point a writable grant or root at the target or at a real cache; say in the record's `execution.instructions` that the target was not read-only mounted. If a control you need cannot be enforced, do not execute; keep the exact blocker as `needs_validation`.
- You may read the hunter's evidence files under `context/reviews/0.1.0-security-audit-2026-10-25/agents/h03-private-dirs/artifacts/evidence/` (read-only) and re-run its harness in your own scratch. A verifier-owned `local` check must cite a file you wrote under your own `scratch/evidence/`.
- Keep probes small and short (deadlines of a few seconds, small sizes).

## 7. Prior records with the same fingerprint

None (no prior run).

## 8. Result contract

Return exactly one JSON object and no surrounding prose: `{"decision": "confirmed|needs_validation|rejected", "record": { ... }}` where `record` exactly matches the decision's branch below (`additionalProperties: false`; do not carry `proposed_verdict`, `_hunter` or any other wrapper field; `verdict` must equal `decision`). Also write the same object to `context/reviews/0.1.0-security-audit-2026-10-25/agents/v03-sysconfigdata/scratch/result.json`, writing it incrementally as you settle each part so a partial file exists if your final message is cut off. Use plain factual language.

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
