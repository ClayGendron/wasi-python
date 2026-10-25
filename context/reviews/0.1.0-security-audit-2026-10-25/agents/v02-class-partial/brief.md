# Candidate-verifier brief: v02-class-partial

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

## 2. The candidate (from hunter `h06-tools`; `proposed_verdict` is the hunter's proposal, not a decision)

```json
{
  "proposed_verdict": "confirmed",
  "fingerprint": "src/wasi_python/tools.py:_bound_keywords:class-construction-partial-unfixed",
  "title": "A guest can override a keyword a class tool's constructor binds with a partial or partialmethod",
  "description": "tool() promises that a keyword a functools.partial binds is fixed: it is left out of the schema, refused when a given schema names it, and refused in a frame. That holds wherever inspect.signature meets the partial, which is how _bound_keywords is documented. But for a class registered as a tool, _bound_keywords goes from the class to type(cls).__call__, which is type.__call__, a C slot, and stops with no fixed keywords. Meanwhile inspect.signature and the runtime both go into cls.__init__ (or __new__). So when __init__ is a functools.partialmethod, or on Python 3.14 a functools.partial (now a method descriptor), the bound keyword is not recorded. The result: tool() accepts a schema that names the keyword, and the per-frame check at _tool_host.py:1003-1009 never fires. Under an explicit schema that is open, has additionalProperties true, or lists the keyword, a guest frame naming it reaches the constructor. Because functools.partial lets the caller override keywords, the guest's value replaces the embedder's bound value. The gate's ToolCall.arguments also carries the keyword, though the docs say arguments never hold a partial-bound keyword.",
  "root_cause": "_bound_keywords (src/wasi_python/tools.py:439-474) treats a class like any other callable object: it reads type(target).__call__ and returns at the C-slot check (tools.py:466-470). It never walks the class's own __init__ or __new__, where inspect.signature and type.__call__ find the partial. So Tool._fixed is empty. The two checks that rely on it, _given (tools.py:418) and the frame check (_tool_host.py:1003-1009), then let the bound keyword through.",
  "intended_behavior": "A keyword bound by a partial or partialmethod anywhere inspect.signature meets it, a class's __init__ or __new__ included, is in Tool._fixed. tool() then refuses a given schema that names it, and a frame that names it is answered invalid_arguments without running the tool. Or tool() refuses such a class outright, as it already refuses an unbound partialmethod.",
  "trace": [
    {
      "kind": "entrypoint",
      "file": "src/wasi_python/_call.py",
      "line": 1263,
      "scope": "_door.frame",
      "description": "The guest's frame bytes are copied out of linear memory after admit and handed to the frame host."
    },
    {
      "kind": "propagation",
      "file": "src/wasi_python/_tool_host.py",
      "line": 1000,
      "scope": "_ToolHost._call_answer",
      "description": "The args are checked against the tool's explicit schema; an open schema, or one with additionalProperties true or listing the keyword, accepts role."
    },
    {
      "kind": "propagation",
      "file": "src/wasi_python/_tool_host.py",
      "line": 1004,
      "scope": "_ToolHost._call_answer",
      "description": "The bound-keyword refusal checks t._fixed, which is empty for the class, so role passes."
    },
    {
      "kind": "propagation",
      "file": "src/wasi_python/tools.py",
      "line": 469,
      "scope": "_bound_keywords",
      "description": "At registration the walk reached type.__call__ (a C slot) and returned with no fixed keywords, never reading cls.__init__."
    },
    {
      "kind": "propagation",
      "file": "src/wasi_python/_tool_host.py",
      "line": 232,
      "scope": "_Work.__call__",
      "description": "The gate gets a copy of the arguments with role in it, contrary to the documented contract."
    },
    {
      "kind": "sink",
      "file": "src/wasi_python/_tool_host.py",
      "line": 258,
      "scope": "_Work.__call__",
      "description": "t.fn(**args) calls the class; type.__call__ runs the partialmethod __init__, whose keyword merge lets the guest's role replace the embedder's bound role."
    }
  ],
  "evidence": [
    {
      "file": "src/wasi_python/tools.py",
      "line": 439,
      "description": "Docstring: keywords a partial binds are found 'wherever inspect.signature may meet one on its way to the function', including 'a class's __call__'; each is fixed and refused in a frame."
    },
    {
      "file": "src/wasi_python/tools.py",
      "line": 466,
      "description": "A class target goes to type(target).__call__ and stops at the C-slot check at line 469, so __init__/__new__ partials are never collected."
    },
    {
      "file": "src/wasi_python/tools.py",
      "line": 418,
      "description": "_given refuses a schema naming a fixed keyword only through the computed fixed set, so the class case is accepted."
    },
    {
      "file": "src/wasi_python/_tool_host.py",
      "line": 1004,
      "description": "The frame-time refusal relies on t._fixed alone."
    },
    {
      "file": "docs/how-to/tools.md",
      "line": 65,
      "description": "Promise: 'A keyword the partial binds is fixed. It is not in the schema, so the guest never sees its value, and a frame that names it is refused.'"
    },
    {
      "file": "tests/checks/test_v1_4_embedding.py",
      "line": 3517,
      "description": "The regression test covers nested partials, a __wrapped__ chain and a bound partialmethod, but no class whose constructor binds a keyword."
    }
  ],
  "conditions": [
    {
      "kind": "system_configuration",
      "description": "The embedder registers a class (a type object) as a tool, with __init__ or __new__ that is a functools.partialmethod, or on Python 3.14+ a functools.partial, binding the authority keyword (for example a role or user id)."
    },
    {
      "kind": "system_configuration",
      "description": "The tool's explicit input_schema lets the keyword through: no properties (open), additionalProperties not false, or a properties map that names it. tool() refuses the last for every other binding shape. A derived schema is not possible for a class tool: tool() refuses it for lack of hints."
    },
    {
      "kind": "authentication_level",
      "description": "The attacker is the untrusted guest code (or the model driving it), which can send any frame through the door."
    }
  ],
  "execution": {
    "attacker_perspective": "Untrusted guest code in run(tools=[...]) sends a raw tool-protocol frame through the door, naming a keyword the embedder bound in the tool class's constructor.",
    "payloads": [
      "class Account:\n    def _init(self, q, role=\"user\"): ...\n    __init__ = functools.partialmethod(_init, role=\"viewer\")\nacct = tool(Account, name=\"account\", input_schema={\"type\": \"object\"})",
      "import _host; _host.call(b'{\"v\":1,\"id\":1,\"op\":\"call\",\"tool\":\"account\",\"args\":{\"q\":\"x\",\"role\":\"admin\"}}')"
    ],
    "instructions": [
      "Bounded local check, run under ulimit -t 300 -f 4000000 -n 4096, env -i with HOME/TMPDIR/WASI_PYTHON_CACHE in the hunter's scratch, and sandbox-exec denying network. The target was not mounted read-only; no grant or root pointed at it.",
      "Host side: register the Account class above, a functools.partial(orders, user_id=42) tool and a derived tool, all in one wasi_python.run(['-c', prog], tools=[...], gate=gate) call, with a recording gate.",
      "Guest side: send the frame above through _host.call, then the same shape against the plain partial (user_id=1).",
      "Read the host-side log of what the gate and each handler received, and the ToolRecord."
    ],
    "observed_result": "The constructor ran with role='admin' (host log: ['Account handler', {'q': 'x', 'role': 'admin'}]), and the gate's arguments held role. The answer was tool_error only because the class returns a non-JSON instance, after the constructor's effect. In the same run the plain partial's user_id=1 was answered invalid_arguments ('unknown argument user_id') and its handler did not run. In-process, inspect.signature(Account) is '(q, *, role='viewer')' and Tool._fixed is []; tool() accepted a schema naming role. The same held for __init__ = functools.partial(...) on Python 3.14.2."
  },
  "remediation": {
    "strategy": "Make _bound_keywords walk a class's construction path as inspect.signature does. When the target is a type whose metaclass __call__ is type.__call__, inspect cls.__new__ and cls.__init__ (via inspect.getattr_static, unwrapping staticmethod and classmethod). Collect the keywords of a functools.partial or partialmethod found there, or refuse the class with the existing partialmethod TypeError. Add a regression case to test_bound_keywords_are_fixed_however_the_partial_is_reached: a class whose __init__ is a partialmethod, under an open schema and a schema naming the keyword. Expect refusal at tool() or invalid_arguments with no constructor call.",
    "code_changes": [
      {
        "file_name": "src/wasi_python/tools.py",
        "fixed_code": "        elif isinstance(target, type) and isinstance(type(target).__call__, _C_SLOTS):\n            # type.__call__ runs the class's own __new__ and __init__, as inspect.signature reads\n            # them: a partial bound there is fixed too, or the class is refused.\n            for attr in (\"__new__\", \"__init__\"):\n                member = inspect.getattr_static(target, attr, None)\n                member = getattr(member, \"__func__\", member)  # staticmethod, classmethod\n                if isinstance(member, functools.partialmethod):\n                    found.update(member.keywords)\n                elif isinstance(member, functools.partial):\n                    found.update(member.keywords)\n            return frozenset(found)"
      }
    ]
  },
  "severity": {
    "likelihood": {
      "score": "low",
      "reason": "It needs an uncommon registration shape: a class as a tool, with a partial or partialmethod constructor binding authority, and an explicit schema that leaves the keyword open."
    },
    "impact": {
      "score": "medium",
      "reason": "Where the shape is used, untrusted guest code replaces an authority value the embedder bound, such as a role or user id, and the constructor acts with it. That is a confused deputy inside the embedder's process, against an explicit documented guarantee."
    },
    "overall_severity": "low"
  },
  "confidence": {
    "score": "high",
    "reason": "Shown end to end through the real door and frame host in a sandboxed run, with the plain-partial control refused in the same run, and the source walk explains it exactly."
  }
}
```

## 3. The linked coverage unit(s) and the hunter's checks (artifact paths are relative to `context/reviews/0.1.0-security-audit-2026-10-25`)

```json
[
  {
    "coverage_id": "src%2Fwasi_python%2F_tool_host.py%23_ToolHost::src%2Fwasi_python%2F_tool_host.py%23admit::src%2Fwasi_python::AI-AND-LLM.md%23Tool-schema%20and%20dispatcher%20disagreement",
    "surface": "Tool frames over the door: admit (count, size, budget), bounded JSON parse, version/op/tool-name checks, schema validation, the gate, dispatch to t.fn(**args) on a bounded thread or the embedder's event loop, result serialization, the outcome record",
    "boundary": "admit, _parse, _Validator, the fail-closed gate, partial-bound keyword refusal, _Bounded and _ToolLoop",
    "agent_id": "h06-tools",
    "local_checks": [
      {
        "agent_id": "h06-tools",
        "reviewed_paths": [
          "src/wasi_python/_tool_host.py",
          "src/wasi_python/_call.py"
        ],
        "invariant": "A frame is admitted by length (count, 1 MiB cap, byte budget) before its bytes are read, copied out of guest memory once, then parsed strictly (UTF-8, nesting 64 counted outside strings, no NaN/Infinity, integer literals at most 64 characters, no repeated key including escaped duplicates, no lone surrogate, strict $bytes) before the version, op and exact tool-name lookup.",
        "method": "source",
        "result": "Holds. admit runs before memory.read (_call.py:1261-1263); the request is a bytes copy, so no double fetch; _parse and _unique_keys see JSON-decoded keys, so \"code\" and \"\\u0063ode\" collide and are refused; version must be type int in (1,); op must equal list or call; the tool is found by exact dict lookup, and the record name is only a 64-character cut used for display.",
        "artifact": null
      },
      {
        "agent_id": "h06-tools",
        "reviewed_paths": [
          "src/wasi_python/_tool_host.py",
          "src/wasi_python/_tool_schema.py",
          "src/wasi_python/tools.py"
        ],
        "invariant": "For every schema shape tool() accepts (derived, explicit closed, explicit open, with partials, bound method with self, dunder and keyword names, root $ref, additionalProperties true, bytes, async tool and gate), the handler receives exactly the validated object plus Python defaults and nothing a partial binds, and the gate's copy equals what the handler gets.",
        "method": "local",
        "result": "Holds for every shape except a class tool (below). Extra keys are refused by a closed schema (properties present, additionalProperties absent closes it); booleans and 1.0 are refused for integer; bytes only where base64 is declared; a plain or nested partial's keyword is refused under an open schema, a root $ref and additionalProperties true; self is refused for a bound method; a keyword property is refused at tool(); the gate's deep copy equals the handler's kwargs and a gate mutating its copy does not reach the handler; sync and async tools and gates give the same verdicts.",
        "artifact": "agents/h06-tools/artifacts/evidence/host_matrix.out.json"
      },
      {
        "agent_id": "h06-tools",
        "reviewed_paths": [
          "src/wasi_python/_tool_host.py",
          "src/wasi_python/runner.py"
        ],
        "invariant": "The gate fails closed: only None or True allow; False, any other value, any exception, a gate that is still deciding when the call is answered, or a failed tool loop refuse; the tool starts only after the gate and only while its call is unanswered.",
        "method": "local",
        "result": "Holds. Gates returning 0, 'yes', False or raising ValueError were answered denied and the handler did not run (host_matrix). Source: _Work.__call__ checks verdict identity after awaiting an async verdict (_tool_host.py:231-255), proceed() is taken under the bound's lock (_tool_host.py:716-721), and an awaitable is never started once the slot is abandoned (_Ops.post, _begin).",
        "artifact": "agents/h06-tools/artifacts/evidence/host_matrix.out.json"
      },
      {
        "agent_id": "h06-tools",
        "reviewed_paths": [
          "src/wasi_python/_tool_host.py",
          "src/wasi_python/_tool_schema.py",
          "src/wasi_python/_sessions.py"
        ],
        "invariant": "Result serialization and the outcome record are bounded and cannot be used to smuggle host text or hide abandoned calls; budgets bound delegated loops.",
        "method": "source",
        "result": "Holds. _to_json refuses non-JSON values, depth past 62 and a lone $bytes dict; answers are ASCII JSON capped at 16 MiB; non-ToolError exceptions cross only as '(internal error)'; the record lists 1,000 outcomes but counts every frame and every abandoned call; the frame and byte budgets are per call, per turn in a session (documented), with abandoned threads capped at 4 per call or session.",
        "artifact": null
      },
      {
        "agent_id": "h06-tools",
        "reviewed_paths": [
          "src/wasi_python/tools.py",
          "src/wasi_python/_tool_host.py",
          "src/wasi_python/_call.py",
          "recipes/guest/host/tools.py",
          "docs/how-to/tools.md",
          "docs/reference/tool-protocol.md",
          "tests/checks/test_v1_4_embedding.py"
        ],
        "invariant": "A keyword a functools.partial or partialmethod binds is fixed wherever inspect.signature meets it on the way to the function: left out of the schema, refused by tool() when a given schema names it, and refused in a frame.",
        "method": "local",
        "result": "Fails for a class used as a tool whose __init__ is a functools.partialmethod (or, on Python 3.14, a functools.partial, now a method descriptor). inspect.signature hides the keyword ('(q, *, role='viewer')'), but _bound_keywords stops at type.__call__ (a C slot) and returns no fixed keywords. tool() accepts a given schema that names role, and a guest frame through _host.call with role='admin' reached the constructor with role='admin' under run(tools=..., gate=...), while a plain partial's keyword was refused in the same run.",
        "artifact": "agents/h06-tools/artifacts/evidence/guest_frames.out.json"
      },
      {
        "agent_id": "h06-tools",
        "reviewed_paths": [
          "src/wasi_python/tools.py"
        ],
        "invariant": "The class-binding gap needs an explicit schema: a derived schema cannot reach it.",
        "method": "local",
        "result": "tool(A) with no input_schema is refused ('parameter q has no type hint'), because hints are read from type.__call__. So the gap needs an explicit schema that is open, has additionalProperties not false, or names the bound keyword.",
        "artifact": "agents/h06-tools/artifacts/evidence/class_derived_probe.out.json"
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

<!-- AI-AND-LLM.md#Core discipline -->
## Core discipline (include in every agent prompt for this domain)

```
- Prompt injection alone is not a finding. Require a code-level boundary failure: content reaches another principal's context, invokes authority the requester lacks, discloses data they cannot read, or drives a sink they cannot reach directly.
- Model output, memory, tool descriptions, and MCP responses are untrusted inputs. Point to the code that grants authority, trusts output, writes durable state, or feeds a sink.
- A guardrail prompt is not a security boundary. Count only deterministic checks, resource-scoped authorization, isolation, binding, and constrained credentials.
- State the attacker, affected principal, effective execution identity, resource, exact action, authority used, and observable impact. An intentional direct request to use the requester's existing authority is not a delegation defect merely because a model executes it.
- Authorization and action binding are separate controls. Attacker-controlled content that causes an action under an affected principal's valid authority is an action-binding failure when that principal did not intentionally request or approve the exact action.
- Classify every candidate as `confirmed` only after source evidence and bounded local validation establish the boundary and result. Use `needs_validation` when a required provider, deployment, model, renderer, or identity behavior is not observable locally.
```

<!-- AI-AND-LLM.md#Validation rules -->
## Validation rules (apply before reporting ANY finding here)

1. Name the crossed boundary and observable result: attacker, affected principal or shared resource, execution identity, target, and unauthorized or unrequested action or disclosure.
2. For confused-deputy authority claims, prove the tool lacks requester-and-resource authorization and that the attacker cannot perform the same action normally. For action-binding claims, instead prove attacker-controlled content caused an action under the affected principal's authority that the principal did not intentionally request or approve. Valid generic authorization does not establish that intent.
3. For memory or retrieval claims, cite both the attacker-controlled write and the later cross-principal read or privileged decision. A shared record without a reachable consumer is not enough.
4. For action binding, establish the intentional request or normalized approved object, if any, and compare it with the object the handler uses. Confirm a locally observable unrequested action, mutation, duplicate, or authority change without extending the test into harmful execution. For schema disagreement, compare the normalized validated object with the handler's object.
5. For MCP identity claims, verify the authenticated connection, request correlation, tool namespace, and effective credential. Mark `needs_validation` if external server identity or deployment routing is required.
6. Return `confirmed` findings only with a complete source trace and meaningful result. Return `needs_validation` for a specific unresolved boundary fact and state the bounded local or owner-observed check needed to resolve it.


## 6. Execution boundary, paths, allowlist

- Target root: `.` (all paths in your record are repository-relative to it). Never edit a file under it. Never run `uv sync`, plain `uv run`, `scripts/00_download.sh`, `scripts/build.sh` or `scripts/steps/*.sh`, `release/set_key.py`, `gh workflow run`, `git push`, `pytest --accept*`, or anything writing under `context/`. Never download from the internet; read-only `gh` GET calls against the project's own repository are allowed.
- Your scratch (the only place you write): `context/reviews/0.1.0-security-audit-2026-10-25/agents/v02-class-partial/scratch/`. Parent-owned artifacts (you never write): `context/reviews/0.1.0-security-audit-2026-10-25/agents/v02-class-partial/artifacts/`. Allowlist for promotion: regular files directly under `scratch/evidence/` named `*.txt`, `*.json`, `*.log` or `*.py`, at most 24 files, 512 KiB each, 8 MiB total; after you finish the parent promotes them to `artifacts/evidence/<name>`.
- Before any target-controlled execution confirm `./build/lane.lock` does not exist. Wrap every target-controlled run as: `ulimit -t 300 -f 4000000 -n 4096; /usr/bin/env -i PATH=/usr/bin:/bin HOME=context/reviews/0.1.0-security-audit-2026-10-25/agents/v02-class-partial/scratch/home TMPDIR=context/reviews/0.1.0-security-audit-2026-10-25/agents/v02-class-partial/scratch/tmp WASI_PYTHON_CACHE=context/reviews/0.1.0-security-audit-2026-10-25/agents/v02-class-partial/scratch/cache /usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' ./.venv/bin/python -I <script under scratch>` (make the three folders first; give each child a wall-clock bound with `subprocess.run(timeout=...)` from a trusted driver). This platform cannot enforce a read-only target mount or a memory rlimit; never point a writable grant or root at the target or at a real cache; say in the record's `execution.instructions` that the target was not read-only mounted. If a control you need cannot be enforced, do not execute; keep the exact blocker as `needs_validation`.
- You may read the hunter's evidence files under `context/reviews/0.1.0-security-audit-2026-10-25/agents/h06-tools/artifacts/evidence/` (read-only) and re-run its harness in your own scratch. A verifier-owned `local` check must cite a file you wrote under your own `scratch/evidence/`.
- Keep probes small and short (deadlines of a few seconds, small sizes).

## 7. Prior records with the same fingerprint

None (no prior run).

## 8. Result contract

Return exactly one JSON object and no surrounding prose: `{"decision": "confirmed|needs_validation|rejected", "record": { ... }}` where `record` exactly matches the decision's branch below (`additionalProperties: false`; do not carry `proposed_verdict`, `_hunter` or any other wrapper field; `verdict` must equal `decision`). Also write the same object to `context/reviews/0.1.0-security-audit-2026-10-25/agents/v02-class-partial/scratch/result.json`, writing it incrementally as you settle each part so a partial file exists if your final message is cut off. Use plain factual language.

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
