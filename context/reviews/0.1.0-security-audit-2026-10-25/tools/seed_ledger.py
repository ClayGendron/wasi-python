import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from ledger import make_unit, write

AC = "ATTACK-CLASSES.md#"
MS = "MEMORY-SAFETY-AND-BINARY.md#"
SC = "SUPPLY-CHAIN-AND-RELEASE.md#"
DI = "DATA-ISOLATION-AND-LIFECYCLE.md#"
RE_ = "RESOURCE-EXHAUSTION-AND-AVAILABILITY.md#"
AI = "AI-AND-LLM.md#"
DT = "DESKTOP-MOBILE-AND-LOCAL-IPC.md#"

def comp(prefix, *classes):
    return [prefix + "Core discipline"] + [prefix + c for c in classes] + [prefix + "Universal moves", prefix + "Validation rules"]

SRC = "src/wasi_python"
units = []

# 1. Guest -> host filesystem through grants (forwarded WASI calls and the guard)
units.append(make_unit(
    {"surface": "src/wasi_python/_call.py#_guard_linker", "boundary": "src/wasi_python/_places.py#_judge", "subsystem": SRC, "attack_class": AC + "Resource and file handling"},
    "Guest WASI path calls on grants and the root (guard linker: path_open, path_rename, fd_readdir shadowed; path_link, path_symlink, path_readlink forwarded to wasmtime 49.0.0)",
    "Grant judge and preopen identity check; the rename guard for GHSA-m9f7-9w4p-gv38", SRC, "Resource and file handling: path traversal, symlink and rename races, TOCTOU between judge and preopen",
    ["src/wasi_python/_call.py", "src/wasi_python/_places.py", "src/wasi_python/_platform.py", "src/wasi_python/_fs_paths.py", "src/wasi_python/_fs_descriptors.py"],
    AC + "Resource and file handling",
    comp(DT, "Local file ownership and TOCTOU"),
    [{"block": MS + "Out-of-bounds read or write", "reason": "guest memory bounds of the runner-served calls are a separate unit"},
     {"block": DT + "IPC peer-authentication gaps", "reason": "no IPC channel; the guest reaches the host only through WASI and the door"}]))

# 2. Runner-served WASI calls: guest memory bounds and the trampolines
units.append(make_unit(
    {"surface": "src/wasi_python/_fs_memory.py#SIGNATURES", "boundary": "src/wasi_python/_fs_memory.py#bounds", "subsystem": SRC, "attack_class": MS + "Out-of-bounds read or write"},
    "The 29 WASI calls the runner serves itself (mount linker) and the five it shadows (guard linker): pointers, lengths, iovecs, dirent buffers, path buffers read from and written to guest linear memory; the trampolines and ffi.PreparedCall",
    "Guest-memory bounds checks in _fs_memory/_fs_descriptors/_fs_paths and the raw memory access in _wasmtime_ffi", SRC, "Out-of-bounds read or write, integer and unit confusion in guest pointer arithmetic",
    ["src/wasi_python/_fs_memory.py", "src/wasi_python/_fs_descriptors.py", "src/wasi_python/_fs_paths.py", "src/wasi_python/_fs_table.py", "src/wasi_python/_wasmtime_ffi.py"],
    AC + "Resource and file handling",
    comp(MS, "Out-of-bounds read or write", "Integer overflow, underflow, truncation, and signedness", "Unit and pointer-depth confusion", "Uninitialized or partially initialized data", "Pointer-length and ownership contract mismatch"),
    [{"block": MS + "JIT and generated-code consistency", "reason": "wasmtime's compiler is an upstream component; only the two shipped binaries are compiled"},
     {"block": MS + "Kernel and privileged-interface attack classes", "reason": "no kernel or privileged interface in the repository"}]))

# 3. Mounts: provider-backed virtual filesystem
units.append(make_unit(
    {"surface": "src/wasi_python/mounts.py#FileProvider", "boundary": "src/wasi_python/_fs_paths.py#_resolve", "subsystem": SRC, "attack_class": AC + "Resource and file handling"},
    "Mounts: guest path calls resolved by the runner against an embedder FileProvider; provider answers (stat, list, read, write-back) typed and staged",
    "_resolve (absolute, NUL, .., component length, nested preopens), _flags/_rights, _listed names, staging caps, the home-thread gate", SRC, "Resource and file handling: traversal inside and out of a mount, provider-answer trust, write-back ordering",
    ["src/wasi_python/mounts.py", "src/wasi_python/_fs_paths.py", "src/wasi_python/_fs_table.py", "src/wasi_python/_fs_descriptors.py"],
    AC + "Resource and file handling",
    comp(DI, "Composite-key and namespace collision", "Stale authorization and derived copy use"),
    [{"block": DI + "Export and backup scope expansion", "reason": "no export or backup feature"}]))

# 4. Private folders in the temp folder against another OS user and another call
units.append(make_unit(
    {"surface": "src/wasi_python/_private_dirs.py#_Private", "boundary": "src/wasi_python/_private_dirs.py#_sweep_once", "subsystem": SRC, "attack_class": DT + "Local file ownership and TOCTOU"},
    "Private root, stdin folder, stdlib-zip copy and fresh HOME made under tempfile.gettempdir(); lock files; the sweep of dead folders; remove_tree; real_dir making /usr/local/lib and /tmp under a root",
    "O_EXCL|O_NOFOLLOW lock creation, flock, kernel identity, owner checks in the sweep, the no-follow removal walk, the judge's refusal of the temp folder at-or-above", SRC, "Local file ownership and TOCTOU: another OS user or another call's guest swapping, pre-creating or linking into the runner's private folders",
    ["src/wasi_python/_private_dirs.py", "src/wasi_python/_platform.py", "src/wasi_python/_zip.py", "src/wasi_python/_call.py", "src/wasi_python/_places.py"],
    AC + "Resource and file handling",
    comp(DT, "Local file ownership and TOCTOU", "IPC lifecycle and correlation confusion"),
    [{"block": DT + "Privileged helper as confused deputy", "reason": "no privileged helper; the runner runs as the embedder"}]))

# 5. Module cache: native code loaded from a folder
units.append(make_unit(
    {"surface": "src/wasi_python/_engines.py#deserialize_file", "boundary": "src/wasi_python/_platform.py#private", "subsystem": SRC, "attack_class": MS + "Library, plugin, and executable search-order trust"},
    "The .cwasm module cache: default location from HOME/XDG_CACHE_HOME/LOCALAPPDATA/WASI_PYTHON_CACHE, cache_dir=, files named by digest and wasmtime version, loaded with deserialize_file",
    "private(): owner, mode 0700/0600, link count, no reparse point; stamp re-check after load; mkstemp+replace writes; the judge refusing grants over every cache", SRC, "Library and executable search-order trust: who can place native code where the runner loads it",
    ["src/wasi_python/_engines.py", "src/wasi_python/_platform.py", "src/wasi_python/_places.py"],
    AC + "Chained vulnerabilities and trust boundaries",
    comp(MS, "Library, plugin, and executable search-order trust", "Missing artifact identity or signature binding", "Shared-state races and TOCTOU"),
    [{"block": MS + "Malformed binary metadata and relocation handling", "reason": "the .cwasm parser is wasmtime's, an upstream component"}]))

# 6. Artifact set discovery and integrity
units.append(make_unit(
    {"surface": "src/wasi_python/_artifacts.py#find", "boundary": "src/wasi_python/_artifacts.py#_found_and_checked", "subsystem": SRC, "attack_class": MS + "Missing artifact identity or signature binding"},
    "Artifact set discovery: WASI_PYTHON_ARTIFACTS, the checkout's build/artifacts (pyproject.toml detection), the wheel's copy, artifacts= passed by the caller; MANIFEST parsing; the zip copy and mpl-data extraction",
    "SHA256SUMS integrity check before compile, re-hash before compile, zip copy held to digest, _member_parts for zip entries", SRC, "Missing artifact identity binding: the set checked vs the set mapped; what artifacts= and env bypass",
    ["src/wasi_python/_artifacts.py", "src/wasi_python/_engines.py", "src/wasi_python/_zip.py", "src/wasi_python/_call.py"],
    AC + "Chained vulnerabilities and trust boundaries",
    comp(MS, "Missing artifact identity or signature binding", "Library, plugin, and executable search-order trust"),
    [{"block": SC + "Update metadata and rollback confusion", "reason": "no updater; the wheel carries its set"}]))

# 7. The door host::call
units.append(make_unit(
    {"surface": "src/wasi_python/_call.py#_door", "boundary": "src/wasi_python/_call.py#_shared", "subsystem": SRC, "attack_class": MS + "Pointer-length and ownership contract mismatch"},
    "The door host::call: guest pointers and lengths, admit before read, the answer buffer from the guest's exported host_alloc (re-entrant guest code inside a host function), MAX_RESPONSE, HOST_FAULT; the raw host= path on the home thread; recipes/hostmodule.c",
    "Pointer bounds before read and after host_alloc, _shared's stack-top check, exception conversion, the home thread handoff", SRC, "Pointer-length contract and stale-view: memory growth between check and use, re-entrancy, exceptions crossing the ffi",
    ["src/wasi_python/_call.py", "src/wasi_python/_wasmtime_ffi.py", "src/wasi_python/_home.py", "recipes/hostmodule.c", "recipes/guest/host"],
    AC + "Chained vulnerabilities and trust boundaries",
    comp(MS, "Pointer-length and ownership contract mismatch", "Use-after-free, stale view, and double free", "Unwind, exception, and thread-affinity violations"),
    [{"block": AI + "Tool-schema and dispatcher disagreement", "reason": "the tool protocol on top of the door is its own unit"}]))

# 8. Tool protocol
units.append(make_unit(
    {"surface": "src/wasi_python/_tool_host.py#_ToolHost", "boundary": "src/wasi_python/_tool_host.py#admit", "subsystem": SRC, "attack_class": AI + "Tool-schema and dispatcher disagreement"},
    "Tool frames over the door: admit (count, size, budget), bounded JSON parse, version/op/tool-name checks, schema validation, the gate, dispatch to t.fn(**args) on a bounded thread or the embedder's event loop, result serialization, the outcome record",
    "admit, _parse, _Validator, the fail-closed gate, partial-bound keyword refusal, _Bounded and _ToolLoop", SRC, "Tool-schema and dispatcher disagreement; tool-argument injection; confused-deputy through the embedder's authority",
    ["src/wasi_python/_tool_host.py", "src/wasi_python/_tool_schema.py", "src/wasi_python/tools.py", "src/wasi_python/_call.py"],
    AC + "Injection",
    comp(AI, "Tool-schema and dispatcher disagreement", "Tool-argument injection into a downstream sink", "Excessive agency and confused-deputy authority", "Unbounded delegated action loops"),
    [{"block": AI + "Indirect injection through retrieved or ingested content", "reason": "no retrieval or memory store; the model's context is the embedder's"},
     {"block": AI + "MCP server and tool identity confusion", "reason": "no MCP transport in the repository"}]))

# 9. Sessions and call-to-call isolation
units.append(make_unit(
    {"surface": "src/wasi_python/_sessions.py#Session", "boundary": "src/wasi_python/_process.py#_Process", "subsystem": SRC, "attack_class": AC + "Business logic"},
    "Sessions (turns, idle/lifetime reaper, shutdown, cancel) and concurrent run() calls sharing one process: stores, output buffers keyed per call, the thread stack, locks, fork handling",
    "Session state machine, per-call output keys, _shared's stack-top check, the process object's locks and fork hook", SRC, "Business logic and isolation: one call's result, output or state reaching another; state-machine skips; concurrency races with security effect",
    ["src/wasi_python/_sessions.py", "src/wasi_python/_process.py", "src/wasi_python/_call.py", "src/wasi_python/_home.py", "src/wasi_python/runner.py"],
    AC + "Business logic",
    comp(DI, "Composite-key and namespace collision", "Stale authorization and derived copy use", "Soft-delete and tombstone bypass"),
    [{"block": DI + "Migration default and ownership confusion", "reason": "no schema or migration"}]))

# 10. Limits
units.append(make_unit(
    {"surface": "src/wasi_python/runner.py#run", "boundary": "src/wasi_python/_limits.py#_check_limits", "subsystem": SRC, "attack_class": RE_ + "Detached work after cancellation"},
    "The limits an embedder relies on: deadline (epoch ticks, poll_oneoff slicing, host-function and provider waits), fuel, memory cap, output cap, open-file cap, tool budget, session idle/lifetime; their argument validation and defaults",
    "_check_limits and _integer_limit, _Waits, the epoch ticker, the open-file cap, output _Stream caps, admit", SRC, "Limit bypass: work that outlives or escapes a limit, caps counted in the wrong unit, arguments that remove a limit silently",
    ["src/wasi_python/_limits.py", "src/wasi_python/runner.py", "src/wasi_python/_call.py", "src/wasi_python/_engines.py", "src/wasi_python/_fs_table.py", "src/wasi_python/_sessions.py"],
    AC + "Business logic",
    comp(RE_, "Detached work after cancellation", "Unbounded buffering and cardinality", "File descriptor, handle, and temporary-resource leaks", "Reachable fatal error or deadlock", "Quota-accounting scope and reset gaps"),
    [{"block": RE_ + "Database and downstream query amplification", "reason": "no database"},
     {"block": RE_ + "Pre-authentication work imbalance", "reason": "no authentication step; every guest is untrusted by design"}]))

# 11. Process integrity: private wasmtime-py API, ctypes callbacks, threads, traps
units.append(make_unit(
    {"surface": "src/wasi_python/_wasmtime_ffi.py#ffi", "boundary": "src/wasi_python/_home.py#home", "subsystem": SRC, "attack_class": MS + "Unwind, exception, and thread-affinity violations"},
    "The runner's use of wasmtime-py's private API and ctypes: raw memory pointers, PreparedCall, the output callback, trap and signal handling (Linux handler check), guest threads on runner stacks, store close on every path, the fork hook",
    "_wasmtime_ffi as the only private-API user, the home thread protocol, store lifecycle in _call, the signal-handler check", SRC, "Unwind, exception and thread-affinity violations; stale pointers after memory growth or store close; teardown safety",
    ["src/wasi_python/_wasmtime_ffi.py", "src/wasi_python/_home.py", "src/wasi_python/_call.py", "src/wasi_python/_process.py", "src/wasi_python/_platform.py", "src/wasi_python/_engines.py"],
    AC + "Wildcard",
    comp(MS, "Unwind, exception, and thread-affinity violations", "Use-after-free, stale view, and double free", "Shared-state races and TOCTOU", "Unload, reload, and teardown safety"),
    [{"block": MS + "Type confusion and invalid downcast", "reason": "Python-side code; wasmtime's own type checks are upstream"}]))

# 12. CLI and the obvious things across the package
units.append(make_unit(
    {"surface": "src/wasi_python/cli.py#main", "boundary": "src/wasi_python/runner.py#_checked", "subsystem": SRC, "attack_class": AC + "Obvious things"},
    "The wasi-python CLI (grant parsing at the first '=', --env KEY copying from the host env, --root creation, --stdin, JSON output) and the package as a whole: secrets, eval/exec with dynamic input, debug toggles, TODOs that name security",
    "_checked argument validation in runner.py; the CLI's own parsing", SRC, "Obvious things and injection in the CLI",
    ["src/wasi_python/cli.py", "src/wasi_python/runner.py", "src/wasi_python/__init__.py", "src/wasi_python/_limits.py"],
    AC + "Obvious things",
    comp(DT, "File-open and intent authority confusion"),
    [{"block": DT + "Custom-scheme and deep-link ambiguity", "reason": "no URI scheme or deep link"}]))

# 13. Release workflow and CI
units.append(make_unit(
    {"surface": ".github/workflows/release.yml#on", "boundary": ".github/workflows/release.yml#permissions", "subsystem": ".github/workflows", "attack_class": SC + "Cache, artifact, and workspace trust mixing"},
    "release.yml (tag push, workflow_dispatch; build, rebuilds, same-bytes, judge legs, gather, attest, publish, pypi; branch-run cache reuse), set-cache.yml (push to main) and docs.yml (pull_request build, dispatch deploy)",
    "permissions: {} and per-job grants, persist-credentials: false, artifact id + digest handoff, tag-on-main check, environments release/pypi/github-pages, set_key verify", ".github/workflows", "Cache and artifact trust mixing; untrusted code in a privileged workflow; expression injection; build-to-promotion substitution; signing-policy gaps",
    [".github/workflows/release.yml", ".github/workflows/set-cache.yml", ".github/workflows/docs.yml", "release/set_key.py", "release/version.py"],
    AC + "Access control",
    comp(SC, "Cache, artifact, and workspace trust mixing", "Untrusted code in a privileged workflow", "Workflow command and expression confusion", "Automation identity overreach", "Build-to-promotion substitution", "Release authorization and signing-policy gaps"),
    [{"block": SC + "Plugin and extension trust expansion", "reason": "no plugin system"},
     {"block": SC + "Update metadata and rollback confusion", "reason": "no updater"}]))

# 14. Build inputs: downloads, pins, extraction, patches
units.append(make_unit(
    {"surface": "scripts/00_download.sh#download", "boundary": "downloads/SHA256SUMS", "subsystem": "scripts", "attack_class": SC + "Mutable and unbound build inputs"},
    "Pinned downloads (curl to .part, shasum -c), pinned() in common.sh, tar -xf and zipfile.extractall of pinned archives, apply_patches.sh and recipes/patches, uv pip install --require-hashes, upstream build systems (meson, cmake, setuptools) that may fetch",
    "downloads/SHA256SUMS verification before use; apply_patches.sh's refusal of unrecorded differences; hash-required installs", "scripts", "Mutable and unbound build inputs; archive extraction; generated-source provenance; build-context inclusion",
    ["scripts/00_download.sh", "scripts/steps/common.sh", "scripts/steps/apply_patches.sh", "scripts/steps/10_tools.sh", "scripts/steps/20_cpython.sh", "scripts/steps/70_zip.sh", "scripts/steps/90_artifacts.sh", "scripts/make_stdlib_zip.py", "scripts/assemble_artifacts.py", "recipes/patches", "downloads/SHA256SUMS", "scripts/line.conf"],
    AC + "Resource and file handling",
    comp(SC, "Mutable and unbound build inputs", "Dependency source and namespace confusion", "Generated-source and codegen provenance gaps", "Build-context inclusion"),
    [{"block": SC + "Untrusted code in a privileged workflow", "reason": "CI triggers and permissions are the release.yml unit"}]))

# 15. Wheel dependencies and the wheel build
units.append(make_unit(
    {"surface": "pyproject.toml#dependencies", "boundary": "release/set_key.py#verify", "subsystem": "release", "attack_class": SC + "Dependency source and namespace confusion"},
    "The wheel's runtime dependency bound wasmtime>=49,<50 and uv.lock; the wheel build (hatchling, release/build-backend.in, build-constraints.txt, licences.py append/restore, version.py); set_key.py as the cache key and verifier",
    "uv.lock hashes, build-constraints, set_key's coverage of inputs, version.py's tag check", "release", "Dependency source and namespace confusion; what the cache key leaves out; what the wheel includes",
    ["pyproject.toml", "uv.lock", "release/build-backend.in", "release/build-constraints.txt", "release/licences.py", "release/set_key.py", "release/version.py"],
    AC + "Obvious things",
    comp(SC, "Dependency source and namespace confusion", "Build-context inclusion", "Build-to-promotion substitution"),
    [{"block": SC + "Workflow command and expression confusion", "reason": "workflow expressions are the release.yml unit"}]))

# 16. The shipped binaries
units.append(make_unit(
    {"surface": "build/artifacts/python.wasm#imports", "boundary": "scripts/steps/60_link.sh#link", "subsystem": "build/artifacts", "attack_class": AC + "Obvious things"},
    "python.wasm and python-snapshot.wasm: import and export sections, custom sections and embedded host paths, target features (threads, shared memory), memory limits, br_table sizes (GHSA-mghf-wjfp-p5xm), integrity against SHA256SUMS and the published 0.1.0 release, the snapshot's fixed hash secret and sys.flags/sys.path",
    "What the link step and reactor recipe put in the binary; the runner compiling only these two modules", "build/artifacts", "Binary inventory: imports beyond WASI preview1 and host::call, leaked paths or secrets, features the model says are absent",
    ["build/artifacts/python.wasm", "build/artifacts/python-snapshot.wasm", "build/artifacts/SHA256SUMS", "build/artifacts/MANIFEST", "scripts/steps/60_link.sh", "scripts/steps/80_snapshot.sh", "recipes/reactor_main.c", "recipes/hostmodule.c"],
    AC + "Obvious things",
    comp(MS, "JIT and generated-code consistency", "Library, plugin, and executable search-order trust"),
    [{"block": MS + "Malformed binary metadata and relocation handling", "reason": "the binary is the project's own output, parsed by wasmtime upstream; a malformed-input defect there is not this repository's"}]))

# 17. The stdlib zip and the import path
units.append(make_unit(
    {"surface": "build/artifacts/python-stdlib.zip#entries", "boundary": "scripts/make_stdlib_zip.py#members", "subsystem": "build/artifacts", "attack_class": MS + "Library, plugin, and executable search-order trust"},
    "python-stdlib.zip entries (symlinks, absolute or .. names, duplicates, .pth/sitecustomize/pyvenv.cfg, pip/ensurepip, credentials or fixtures, reportlab_mods/settings), sys.path and sys.flags inside the guest, site disabled, planted modules on a reused root, the mpl-data extraction",
    "make_stdlib_zip.py's member selection; the runner's import-path judge and site-off start; _zip._member_parts", "build/artifacts", "Library search-order trust: code planted where the guest imports from; zip-slip in the runner's extraction",
    ["build/artifacts/python-stdlib.zip", "scripts/make_stdlib_zip.py", "scripts/steps/70_zip.sh", "src/wasi_python/_zip.py", "src/wasi_python/_places.py", "src/wasi_python/_call.py", "recipes/reactor_main.c"],
    AC + "Resource and file handling",
    comp(MS, "Library, plugin, and executable search-order trust"),
    [{"block": MS + "JIT and generated-code consistency", "reason": "the binaries' unit covers compiler-facing properties"}]))

# 18. Reused roots and cross-call code execution (lifecycle)
units.append(make_unit(
    {"surface": "src/wasi_python/_call.py#_preopens", "boundary": "src/wasi_python/_places.py#_judge_import_path", "subsystem": SRC, "attack_class": AC + "Chained vulnerabilities and trust boundaries", "lifecycle": "reused-root"},
    "A root, writable grant or mount reused across calls: what an earlier guest leaves (modules, .pth, config files read by packages, HOME contents, /etc/xml/catalog, matplotlibrc, .cwasm) and what a later call does with it; env= overriding HOME, TMPDIR or PYTHON* variables",
    "site off and -I semantics in the reactor, read-only import path with nothing writable under it, the fresh or read-only HOME, the judge's refusal of caches", SRC, "Chained trust: planted code or configuration becoming execution in a later call, beyond what the security model documents",
    ["src/wasi_python/_call.py", "src/wasi_python/_home.py", "src/wasi_python/_places.py", "recipes/reactor_main.c", "docs/explanation/security-model.md"],
    AC + "Chained vulnerabilities and trust boundaries",
    comp(DI, "Stale authorization and derived copy use", "Restore reintroduces invalid state"),
    [{"block": DI + "Backup and replication boundary drift", "reason": "no backup or replication"}],
    lifecycle="reused root across calls"))

write(units, sys.argv[1])
