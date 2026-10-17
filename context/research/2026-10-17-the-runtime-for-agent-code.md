# The runtime for agent code

- **Status:** research, 2026-10-17. It commits the project to nothing. It feeds question 12 (a
  tool-call convention over the door), the typed-grants specification, spec 015 and the planned
  memo on state across agent turns.
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5). It wrote none of the code or documents it reads,
  here or in vfs. Box: 60 minutes; stopped at about 55. vfs was read, never edited.
- **The direction it answers,** the owner's words of 2026-10-17: "a safe runtime for agent code.
  The use case is much more powerful web agents that can access code and interact with their
  data and tools (either through a file system, tools in the host program, api calls, mcp, etc.)
  its main use case is to work with ~/Git/Repos/vfs and run on top of that where vfs manages the
  permissions and governance."
- **The rule it works under:** constitution §4.5. This memo may name vfs. Every recommendation
  for this repository is a general capability that any embedder could use. Nothing recommended
  here names vfs, carries vfs's wire format, or exists only for vfs.

## Terms

- **Embedder:** the host program that runs the guest. vfs would be one.
- **The door:** the one custom import, `host::call`. The guest calls it through the builtin
  module `_host` (`recipes/hostmodule.c`). A **frame** is the opaque bytes it carries.
- **Grant:** a host directory the embedder hands the guest under a guest path. WASI calls it a
  **preopen**. A **typed grant** is a grant marked read-only or writable.
- **Shim:** an embedder's own implementation of the WASI file calls (`path_open`, `fd_read` and
  the rest), answering them from something that is not a host directory. The principal
  engineer's memo calls this "3b".
- **Materialise:** copy the permitted files out of a store into a host directory, so a grant can
  hand them to the guest.
- **Authority:** vfs's term for who is acting. It is a set of subjects (whose rights apply), an
  actor (who does the work) and a narrowing (`src/vfs/authority.py:115-128`, ADR 062).

## Labels

READ means a claim read from a file, cited by path; paths under `vfs/` are in
`/Users/claygendron/Git/Repos/vfs`. EXECUTED means run here, in this box. INFERRED means the
researcher's reasoning. Nothing new was executed for this memo: every number below is quoted
from the document cited beside it, with that document's own label.

## Summary

1. **vfs is governed data access for agents.** It is an async Python library. It serves one
   namespace of rows in SQL databases and judges every verb against an authority. It keeps
   versions and a trash. Its MCP server, its shell and its tools are designed, not built (READ).
2. **vfs already plans to run this project's artifacts,** not this project's runner. Its spec
   169b is a WASI host of its own: a preview1 shim over vfs verbs, with whole-file staging, one
   verb per open, and one guest per process. Its spec 172 runs `python.wasm` under that host and
   adds a guest-side `vfs` package that calls verbs through the door (READ). These documents are
   drafts, not yet committed in vfs; none of it is code.
3. **So vfs has chosen file option (b), a shim, plus option (c), a door library.** Option (a),
   materialising into a grant, is not in its plans. It sees every file access under (b) and (c),
   and only the boundary under (a).
4. **Tools, API calls and MCP can reach a guest only through the door.** The guest has no
   network (judged, `test_guest_has_no_network`). So the embedder can govern every outside call.
   But vfs's own design today gives a program no way to call a tool: ADR 082 pin 2 says a
   program's capability has "no execution verb". The owner's direction and vfs's ADR disagree.
5. **What vfs needs from this project is mostly general.** In order: a stable embedder contract
   for a host that is not the runner; typed grants and a snapshot that honours them; a working
   directory per call; a way for an embedder to put its own read-only library on the import
   path; a deadline and cancellation that also bound time spent inside the door; door
   accounting. Later: a filesystem provider in the runner, a run record, streamed output, state
   across turns.
6. **Several vfs documents name things this project cannot ship:** a `vfs_run` export, a
   `vfsmodule.c`, artifacts named `vfs-python-…`, and a `vfs` package inside the stdlib zip.
   Each has a neutral equivalent that exists or can.

## 1. What vfs is (READ)

**A namespace over databases.** `VirtualFileSystem` routes paths to mounted storages
(`vfs/README.md`; `vfs/src/vfs/base.py:334-350`). The one storage that exists is
`DatabaseStorage`, over async SQLAlchemy, on SQLite, Postgres, MariaDB, SQL Server and Oracle.
There is no local-disk backend. Files are rows: text XOR bytes, with a MIME type and a version
(`vfs/context/research/studies/2026-10-15-agent-shell/04-filesystem-over-the-sandbox-boundary.md`,
summary).

**Verbs, not syscalls.** read, stat, ls, tree; glob, grep, glean (ranked search), graph (typed
edges); write, edit, delete, mkdir, move, copy, mkedge (`vfs/README.md`, "The verb surface";
`vfs/src/vfs/ops.py:36-62`). Every verb is a coroutine: `async def read(self, path=None, …,
authority=None) -> Result` (`base.py:879`). Failures are values: a `Result` carries classified
errors such as `vfs.not_found` or `vfs.permission_denied`, and "a raw exception always means a
bug" (`vfs/README.md`; ADR 008; ADR 076).

**Permissions in two layers.**
- A mount-level map, `read` or `read_write`, with per-prefix overrides; the most restrictive layer
  wins (`vfs/src/vfs/permissions.py:97-266`).
- Row grants on one ladder: `none < list < read < add < contribute < read_write`. `list` names a
  row, `read` reads it, `add` creates beneath a prefix, `contribute` also overwrites, and
  `read_write` trashes, moves and grants (`vfs/src/vfs/ops.py:110-114`; ADR 080). Every verb
  names its rung in one table (`VERB_RUNGS`, `ops.py:134-160`). Grants only widen; there is no
  deny row (`vfs/src/vfs/storage/grants.py`).

**Identity on every call.** Every verb takes `authority=`; rights are re-derived on every call
and never cached (ADR 063). Principals are `user`, `service` (an agent with its own identity),
`system` or `anonymous` (`authority.py:35`). There is no tenant object: tenants are subtrees
under grants (ADR 006). There are no quotas or rate limits in the code; quotas are a paid-tier
plan (`vfs/business/product-plan-2026-08.md`).

**Governance is history.** Version rows record the actor and subjects of a write (ADR 064). A
delete is a tombstone, restorable for 90 days by default (ADR 074, ADR 027). "The audit log … is
the storage engine's own history" (`vfs/business/product-plan-2026-08.md`). The claimed
differentiator is governed mutation with "no side door" (ADR 069).

**How an agent reaches it today.** Only as a Python library, in process. The MCP server
(spec 171), the bash-shaped shell (ADR 081, spec 167), programs and the `/.vfs/bin` index
(ADR 082, spec 169) and tools and MCP servers as views (spec 170) are drafts; none is built
(`vfs/context/specs/active/`; `ops.py:15-17`: the `cli` meta-verb "is deliberately absent").

## 2. How vfs intends to run agent code (READ)

The plan is written down in detail, but it is young. ADRs 081 to 086 and specs 166 to 173 are
untracked in vfs's working tree; its last commit is dated 2026-10-14 (`git status` in vfs, read
only). No shell, WASI host or wasmtime dependency exists in `vfs/src/` or `vfs/pyproject.toml`.
The only execution verb in code, `run`, routes to a `SupportsRun` protocol that no storage
implements, and ADR 082 retires it (`vfs/src/vfs/base.py:1548-1564`). vfs's roadmap puts
embedded code execution after its 0.1.0 (`vfs/ROADMAP-v0.1.0.md:125`). So everything below is
intent, open to change.

Its documents, in the order they depend on each other:

- **ADR 082, "one program ABI, six kinds".** A program gets `args`, `env`, `cwd`, `stdin`, `fs`
  and `budget`, and returns stdout, stderr and an exit code. `fs` is "the vfs verb set curried
  with the caller's `Authority`… no execution verb and no grant verbs". The six kinds are verb
  builtins, text programs, **programs** ("bytes stored in vfs, run in a sandbox as the caller"),
  **tools** (host Python functions, run with the host's authority), **MCP tools** and skills.
  "Programs spawn programs" was rejected: "a program holds no execution capability"
  (`vfs/context/decisions/082-…md`, pins 1-3 and "Options considered").
- **ADR 084, budgets.** Executing a program is `read` on its entry. A program never holds more
  than its caller. Budgets per run: `FUEL_BUDGET` 2 × 10⁹, `MEMORY_BYTE_BUDGET` 256 MiB,
  `VERB_CALL_BUDGET` 10,000, `STAGING_BYTE_BUDGET` 256 MiB, 10 s per command line. And, in its
  own words: "The epoch deadline does not cover time inside a verb, so the verb budget is part of
  the run budget" (`vfs/context/decisions/084-…md`, pin 5).
- **ADR 086, "Python in vfs is a statically linked WASI CPython".** The spike that seeded this
  repository; the decision that the build is "its own project, `wasi_python`"; vfs consumes the
  `wasi-python` wheel through an optional extra `vfs-py[python]`; it installs the binary and zip
  as rows at `/opt/bin/python3.wasm` and `/opt/lib/python3XY.zip`; "the verb door is
  `wasi_python`'s neutral host door … a pure-Python `vfs` package on top exposes the verb table
  bound to the caller's authority. No verb is reachable except through that door and the
  preview1 file calls, both gated" (`vfs/context/decisions/086-…md`, decisions 3-7).
- **Spec 169b, the WASI host.** A preview1 shim in Python, `shell/wasi/`, over vfs verbs
  (`vfs/context/specs/active/169-programs-the-index-and-the-vfs-views/spec.md:319-610`):
  - two preopens: fd 3 is `/`, fd 4 is `.` bound to the call's `cwd` (b3);
  - `path_open` issues at most one verb; a file is staged whole on open and written back whole
    on close (b4, b5); a refused write-back is "never silent": the close returns the errno and
    the run's `Result` carries the error even when the guest exits 0 (b5);
  - a table from each `ErrorKind` to a WASI errno; "the ladder reaches the guest as errno only"
    (b7);
  - **one guest at a time per process**, because of wasmtime-py's module-global trap slot; each
    verb is posted to the event loop with `run_coroutine_threadsafe` from the worker thread (b8);
  - exit 124 for a deadline, 137 for fuel or the verb budget, 134 for any other trap (b8);
  - a gated `read` of the program on every run, and a `.cwasm` cache keyed by content hash (b9).
- **Spec 172, the WASI Python runtime.** The `python` program kind (`python3 -c …`, `.py`
  scripts); a reactor entry named `vfs_run`; a staged-buffer cache so `zipimport` reads the zip
  row once; the door frames are "the `Result` wire of spec 171's adapter (verb name plus JSON
  arguments in, the `ResultPayload` out)"; "a pure-Python package `vfs` in the zip wraps it:
  `vfs.read(path)`, `vfs.write(path, content)`, `vfs.ls`, `vfs.glob`, `vfs.grep`"
  (`vfs/context/specs/active/172-the-wasi-python-runtime/spec.md`, §2-§4).
- **The evidence beneath them.** Study 04 ran real CPython 3.12 and QuickJS over a 250-line shim:
  one `read` is 5 SQL statements, one `write` 16, one `ls` 6; an 8 MiB row staged for a 1-byte
  read; 128 of 600 concurrent runs in one process got the other thread's exit code
  (`…/04-filesystem-over-the-sandbox-boundary.md`, findings 3 and 9, EXECUTED there). The spike
  ran the pandas CSV job on the snapshot over the shim in 120 ms with 15 verbs and 93 SQL
  statements, and `import numpy` through the zip row in 1,890 ms uncached, 338 ms with the cache
  (spec 172 §3 and criteria 2-3, from study 13, EXECUTED there).

**What this means (INFERRED).** vfs will not call `wasi_python.run()`. It plans to load
`python.wasm` itself under its own wasmtime-py host, as the README's "any other embedder" does.
So what vfs needs from this project is first **the embedder contract** (the exports, the door,
the zip's guest path, the snapshot's frozen preopens), and only second the runner's features.
That changes the order of the list in section 5.

## 3. Channel by channel

### 3.1 Files

The guest's data lives in vfs rows, not on a host disk. Three ways to reach it:

- **(a) Materialise into a grant.** The embedder copies the files the agent may read into a host
  directory, grants it read-only, grants a writable output directory, runs, then reads back what
  changed and writes it to the store under the agent's authority.
- **(b) A shim.** The embedder implements the WASI file calls itself over its store. The guest's
  `open()` goes, through wasi-libc and preview1, to the embedder's code. This is vfs's plan
  (spec 169b).
- **(c) A guest library over the door.** Guest code calls `lib.read(path)`; the library sends a
  frame; the embedder answers. This is vfs's plan for the verbs that have no POSIX form (spec
  172 §4).

| | (a) materialise | (b) shim | (c) door library |
|---|---|---|---|
| **Latency** | Copy-in before the run and diff after it, proportional to what is granted, not to what is read. This repo's own measure for a 9.9 MB tree: about 57 ms and 9.6 MB per root (`2026-10-16-where-package-data-lives.md`, C1, EXECUTED there). Inside the run, native-speed file calls through wasmtime. | One verb per open and one per dirty close: 5 and 16 SQL statements on vfs's dev engine. The pandas CSV job ran in 120 ms with 15 verbs (vfs study 13, EXECUTED there). A seek-heavy program pays for the whole file (8 MiB staged for 1 byte). | One door crossing per call: a copy of the frame each way, plus the embedder's encoding. Not measured in either repo. No staging. |
| **Consistency** | A snapshot taken at copy-in. Writes reach the store only at write-back, after the run. Changes made in the store during the run are invisible. A conflict shows up at write-back. | Live at each open: a later open sees other writers. Whole-file buffers: two opens of one path and last close wins (study 04, C3). A write is visible to the store at close, not at `write()`. | Live per call. Read-your-writes is whatever the store gives. |
| **Governance: does the store see every access?** | **No.** It judges `read` once per file at copy-in and `write` once per file at write-back. It never learns which granted files the program opened. | **Yes**, per open, per close, per listing, each under the caller's authority, with errno back to the guest. | **Yes**, per call, with a classified answer back to the guest. |
| **What this project must add** | Typed grants (several, read-only or writable, at any guest path, possibly none); a snapshot that honours them (`__wasilibc_reset_preopens`, package-data memo finding 2); `Completed.outputs`, the files created or changed in writable grants, found without following links; and the README's existing warning that write-back code must not follow a link a guest left. | Nothing in the guest. A published contract for a host that is not the runner: the exports, the zip's guest path, the preopen table the snapshot froze, the file calls CPython makes (a conformance job, as the principal engineer's memo asked). A per-call working directory. Optionally, a filesystem provider in the runner (section 5, item 8). | A way for the embedder to put its own guest library on the import path. Today the import path is only the stdlib zip, `site` does not run, and `PYTHONPATH` is ignored (`recipes/reactor_main.c:137-150`). |
| **Fits §4.4?** | Yes. Only preview1 file calls on real preopens. | Yes. The guest's imports do not change; the host answers the same preview1 calls differently. | Yes. It is the door. |

**What each option costs an agent's code (INFERRED).**
- (a) and (b) keep ordinary Python working: `pd.read_csv("/data/sales.csv")`, `open(...)`,
  `np.loadtxt`. A model writes that code without being told anything.
- (c) does not. `pandas.read_csv` wants a path or a file object, so the code becomes
  `pd.read_csv(io.BytesIO(lib.read(path)))`. A model must be taught the library. So (c) is the
  right home for what has no file form (grep, glean, graph, grants), and the wrong one for plain
  reads and writes.

**The trade (INFERRED).**
- (a) is cheapest to build and fastest per access, and its governance is coarse: the boundary,
  not the access. It suits a store that can name the inputs up front (a "files in, files out"
  job). It does not suit "here is the whole namespace; look around", because materialising the
  whole namespace is unbounded.
- (b) gives vfs what it sells: every access judged, versioned and attributed. It costs a shim of
  about 35 preview1 functions (spec 169b b2), security-critical, written once per embedder.
- (c) is the complement for verbs, not a replacement for files.
- vfs's plan, (b) plus (c), is consistent with its product. This project's typed grants serve (a)
  for every other embedder, and also serve vfs where it chooses to stage a working set.

### 3.2 Tools, API calls and MCP

**The door is the only path (READ, EXECUTED by the judge).** The guest has no socket, no `_ssl`,
no process (`README.md`, Safety; `test_guest_has_no_network`). Constitution §4.4 forbids a third
import. So a tool in the host, an HTTP API and an MCP server are all reached the same way: a
frame through `host::call`, answered by the embedder. That is exactly where vfs wants to judge
them: spec 170 makes a tool or MCP entry a row with a posture, and "who may call a tool is who
may read its entry" (READ).

**But vfs's own ABI gives a program no tool calls (READ).** ADR 082 pin 2: the program's `fs`
has "no execution verb"; "programs spawn programs" was rejected. Spec 172's door exposes the
verb table (read, write, ls, glob, grep), not `cli`. In vfs's design, an agent composes tools in
the shell (`python3 analyze.py | some_tool`), not inside a Python program. The owner's direction,
"agents that interact with their data and tools", reads as tools called from inside the code.
That is a vfs decision (question 2 below), and it does not change what this project builds: the
door carries the frames either way.

**What a tool-call convention over the door needs.** The owner deferred the convention
(question 12). These are the needs, not a decision:

1. **Naming and discovery.** A frame must name the tool and carry its arguments. The guest needs
   a way to list tools and their schemas (MCP's `tools/list`; vfs's `/.vfs/tools` entries whose
   content is a manifest). A convention could keep discovery as one more call, so nothing about
   the tool set is baked into the guest.
2. **Encoding.** Frames are bytes. JSON is what MCP, vfs's `Result` wire and every agent
   framework speak; bytes in a result (a PNG, a Parquet file) need a binary-safe form (base64 in
   JSON, or a length-prefixed binary envelope). The door's response limit is 2³¹ − 1 bytes and
   guest memory (`MAX_RESPONSE`, `runner.py:56`).
3. **Errors as values.** The door has two failure codes: −1 (no host: `ConnectionRefusedError`)
   and −2 (host fault: `OSError`). A tool's own failure, a refusal by policy and a timeout must be
   distinguishable by guest code without parsing prose. vfs's model, a closed set of classified
   kinds with a fixed phrase each (ADR 076), is a good shape; MCP's `isError` is the minimum.
4. **Streaming and large results.** The door is one request, one response. A result too large
   for guest memory, or a tool that reports progress, needs a handle: a first call returns an id,
   later calls fetch chunks, a last call closes. That is a convention over the door, needing no
   runtime change.
5. **Concurrency inside the guest.** The guest has no threads, and a door call blocks it. An
   agent that wants five API calls at once needs a batch frame (many requests, one response), or
   a submit-then-collect pair. Both are conventions. A guest `asyncio` loop cannot wait on the
   door: its selector waits in `poll_oneoff`, which knows only clocks and descriptors (INFERRED).
6. **Async hosts.** vfs verbs and MCP clients are coroutines; the door is synchronous. The
   bridge is the one both repos already name: run the guest on a worker thread and, inside the
   host function, post the coroutine to the event loop with `run_coroutine_threadsafe` and wait
   (spec 015, Scope; vfs spec 169b b8; vfs study 04 finding 8, EXECUTED there).
7. **Time inside the door.** The epoch deadline interrupts only wasm code. A host function that
   waits ten minutes on an API keeps the call alive past its deadline, and spec 015's `cancel`
   cannot stop it either: the callback fires only when the guest runs again (INFERRED from
   `runner.py:846-884`, which checks neither; vfs ADR 084 pin 5 states the same for its host).
   The host must be told how long it has, and when to give up.
8. **Identity and audit.** Who is calling is the embedder's to know. Today `host=` is a closure
   made per call, so an embedder binds the caller's authority into it; no runtime feature is
   needed for identity. Audit wants more: a per-call id, the fuel spent so far at each frame, and
   a record of frames in and out (section 5, item 9).
9. **Budgets.** The number of door calls and bytes through the door are unbounded today except by
   the deadline. vfs counts its own (`VERB_CALL_BUDGET`). Constitution §4.15 says every limit has
   a default; the door's count and bytes are not limits the runner sets today (INFERRED).
10. **The fault the embedder never sees.** The door turns any exception from `host` into −2 and
    drops it (`runner.py:858-859`), as spec 006 requires. The embedder that wrote the bug learns
    nothing from `Completed` (INFERRED). A count, or the first fault's type, would help.

### 3.3 Network

The guest has none, by construction (README, Safety, judged). `socket.socket` fails; `_ssl` and
`_socket` are absent; there is no WASI socket call it can use (the principal engineer's memo §2,
EXECUTED there). So every API or MCP call goes through the host, where the embedder can judge,
log, rate-limit and bill it (INFERRED). Two things follow:
- An `urllib` or `requests`-shaped client inside the guest would have to be a library that sends
  frames through the door. It would be embedder code or a convention library, never a socket
  import (§4.4).
- The guarantee holds only if the embedder's tool functions are themselves governed. vfs's ADR
  084 pin 3 names tools as "the one stated exception: a host-registered function runs with the
  host's own authority". A guest that can call such a tool reaches whatever the tool reaches.
  That is the embedder's design, and it is why vfs gates the call on `read` of the tool's entry.

## 4. What vfs needs, and conflicts with this repository

### 4.1 In vfs's order (READ, then INFERRED)

vfs lands spec 169b (its host) before spec 172 (Python). So vfs needs, in this order:

1. **The embedder contract, stable and written for a host that is not the runner:** the exports
   (`_initialize`, `run`, `host_alloc`, `memory`); the two imports; the stdlib zip's guest path
   (`/usr/local/lib/python315.zip`, fixed by `recipes/reactor_main.c:21-24`); the snapshot's
   frozen preopen table (`/` at fd 3 only); and which preview1 calls CPython makes.
2. **A per-call working directory.** vfs binds `.` to the shell's `cwd` as fd 4 (169b b3). The
   snapshot ignores any preopen it was not taken with (package-data memo, finding 2, EXECUTED
   there), so relative paths would resolve against `/`.
3. **Its own library on the import path, read-only.** Spec 172 puts a `vfs` package "in the zip".
   This project's zip cannot hold it (§4.5), and the snapshot runs only beside the exact zip it
   was built against. An embedder needs a general way to add a library.
4. **Deadline, cancellation and budgets that cover the door** (section 3.2, items 7 and 9).
5. **Concurrency.** vfs's host runs one guest per process because of wasmtime-py's trap slot.
   This project's runner already runs concurrent calls that share nothing (spec 011). vfs gets
   that only if it runs through the runner.
6. Later: a record of each run for its `/.vfs/run` view (169c), streamed stdout for its pipe
   (169b b10 names it the next step), and an answer on state across turns.

### 4.2 General, or vfs-specific?

| Need | General capability (in bounds) | vfs-specific (out of bounds here) |
|---|---|---|
| Files from a store | typed grants; `Completed.outputs`; a filesystem-provider protocol in the runner; a conformance job | whole-file staging into rows; the `ErrorKind`→errno table; text-vs-bytes write-back; hiding `/.vfs` |
| Guest library | read-only directories or zips an embedder puts on the import path | the `vfs` package itself and its verb table |
| Door frames | budgets, a host-time deadline, cancellation, a fault count, a transcript | the `Result` wire, `ResultPayload`, verb names |
| Identity | per-call `host=` (exists); a call id and fuel stamps for audit | `Authority`, subjects, actor, version rows |
| Exit status | `trapped` names a stable reason (exists) | 124, 137, 134 as shell statuses |
| Entry point | `run` (exists) | an export named `vfs_run` |
| Artifact names | `python.wasm`, `python-snapshot.wasm` (exist) | `vfs-python-<ver>-…wasm` |
| Install layout | the zip's fixed guest path (exists) | `/opt/bin`, `/opt/lib` as rows |
| Fuel per tenant | `fuel_used` per call (exists, with a cap) | summing per tenant, quotas |

### 4.3 Gaps and conflicts

1. **vfs names things that cannot exist here (READ).** Spec 172 still names a `vfs_run` entry,
   `vfsmodule.c` and `vfs_main.c`, artifacts named `vfs-python-…` and a `vfs` package in the zip.
   ADR 086 says `vfs_run` too, and spec 172's slice 172c still names a `vfs.call` import and a
   `_vfs` module, though its §4 and vfs's `context/specs/STATUS.md` (line 8) already say the door
   "is renamed neutral (`host::call`)". This repository ships `run`, `recipes/hostmodule.c` (module
   `_host`), `python.wasm` and `python-snapshot.wasm`, and a zip with nothing named for an
   embedder. The neutral contract already does everything those names were for. vfs's documents
   should follow it; that edit is vfs's.
2. **The install layout conflicts with the snapshot (INFERRED from READ).** vfs plans the zip at
   `/opt/lib/python3XY.zip`, found by "CPython's own landmark search … from the binary's path"
   (ADR 086 decision 4). This reactor does no landmark search: it sets the import path to the
   fixed `/usr/local/lib/python315.zip` and `argv[0]` to `/usr/local/bin/python.wasm`
   (`recipes/reactor_main.c:137-150`), and the snapshot froze both. A shim must serve the zip at
   that guest path, wherever the store keeps it, and must serve the exact bytes the `MANIFEST`
   names.
3. **Two preopens against a snapshot that froze one (EXECUTED in the package-data memo).** 169b's
   fd 4 `.` is ignored by today's snapshot. Typed grants need the same fix
   (`__wasilibc_reset_preopens` at the end of `wizer.initialize`, proven on a toy guest only).
4. **One guest per process against spec 011 (READ).** vfs's host serialises every guest, a 26 MB
   CPython run behind a 100 KB `cat`. This runner does not need to, because it routes traps and
   output per store, not through wasmtime-py's shared tables. vfs's host, written on wasmtime-py,
   would rediscover the races spec 011 closed.
5. **Programs cannot call tools (READ).** ADR 082 pin 2 against the owner's direction (question
   2).
6. **The zip from a writable store (INFERRED).** vfs plans to serve the stdlib zip from a row
   installed by the system actor at posture `read`. That is a read-only grant in effect, and it
   matches §4.15's rule that runtime files are never writable by the guest, as long as the shim
   never lets a guest write that path and the bytes are checked against `MANIFEST`.
7. **Memory budget (INFERRED).** vfs's 256 MiB default is a quarter of this runner's 1 GiB. The
   spike's pandas job peaked at 108 MiB (vfs spec 173, landing notes, EXECUTED there), so the
   golden-sized jobs fit. But the principal engineer's memo found one numpy test needed 560 MiB
   and suggested 512 MiB as the least safe default. A larger frame under 256 MiB ends in
   `MemoryError`; that is a vfs default, not a conflict, and is noted so it is chosen knowingly.
8. **Out of memory is not an abort here (READ).** vfs maps any non-fuel trap to 134 and says the
   host "cannot tell out-of-memory from a panic". With a store memory limit, this guest raises
   `MemoryError` and exits 1 (the principal engineer's memo §2, EXECUTED there).
9. **wasmtime-py versions in one process (INFERRED).** This runner pins `wasmtime>=49,<50` and
   uses its private `_ffi` binding (specs 011, 015). An embedder that also imports wasmtime-py
   must agree on that range.
10. **Reads are invisible under (a) (INFERRED).** If vfs ever stages a working set into a grant to
    get native speed, it loses per-access governance. That trade is vfs's, but the memo records
    it so the choice is made knowingly.

## 5. What to build here, ranked

Each item is a general capability, stated without reference to any embedder. Rank is by what it
unblocks for an embedder that governs data and tools, weighted by cost. "Exists" or "planned"
says where the project already stands.

1. **Typed grants, with a snapshot that honours them.** Several grants, each a host path, a guest
   path and read-only or writable; possibly none. The snapshot rebuilds its preopen table at run
   time, so a grant at any guest path works on both binaries. The stdlib zip moves to a
   read-only grant, which ends §4.15's alpha exception. *Planned* (owner's answers 1 and 2).
   Unblocks option (a), matplotlib's data, and item 4.
2. **A per-call working directory.** `cwd=` on `run`, and a documented way for any embedder to
   set it (an argument the bootstrap reads before the program starts). It must lie inside a
   grant or the embedder's served tree. *New, small.*
3. **The door bounded in time, and cancellable.** Spec 015's `cancel` and `run_async`, plus a
   rule for time spent inside the host function: the host is told the call's remaining deadline
   and its cancel event (a small context object passed to `host`, or an async `host` that
   `run_async` awaits on the caller's loop with the deadline as its timeout). Today a slow host
   outlives the deadline. *Spec 015 drafted; the door part is new and is the owner's to scope,
   since 015 left async host functions out.*
4. **`Completed.outputs` and `Completed.error`.** The files a program created or changed in its
   writable grants, found without following links; and the program's exception (type, message,
   line) as a value, not only a traceback. *Planned* (the principal engineer's direction 5).
   Makes option (a) governable at write-back.
5. **An embedder's read-only library on the import path.** A grant (a directory or a zip) the
   embedder marks importable; the bootstrap appends it to `sys.path` for that call. Only a
   read-only grant may be importable, so the spec-006 guarantee (code planted by one run never
   runs in another) still holds. Native isolated mode ignores `PYTHONPATH`; the mechanism should
   be an explicit argument, not the environment. *New.* It is what lets any embedder ship a
   guest-side helper (for files, tools or anything else) without touching the zip.
6. **Door accounting with defaults.** A cap on door calls and on bytes through the door per call,
   each with a default (§4.15), reported in `Completed` when hit; and a count of host faults the
   door swallowed. *New, small.*
7. **The embedder contract as a published, judged document, and a conformance job.** Everything
   a host that is not the runner must do: exports, imports, the zip's guest path and hash, the
   preopen table, the working directory, the preview1 calls CPython makes and what each must
   answer. The job is a guest program any embedder runs against its own filesystem shim (the
   principal engineer's memo, layer 3). *Partly exists* (README "Any other embedder"); the job is
   new.
8. **A filesystem provider in the runner (research first).** A Python protocol (open, read, write,
   stat, list, rename, remove) that `run` uses to answer the preview1 file calls, so a Python
   embedder can back the guest's files with any store and still get this runner's limits,
   concurrency, cancellation and input checks. It fits §4.4: the guest's imports do not change.
   It is large and security-critical (about 35 calls), and it is only worth building if the owner
   wants embedders to use the runner rather than write their own host. *New; needs a research
   memo with an experiment* (wasmtime-py's `Linker.allow_shadowing` already replaced `path_open`
   once, the principal engineer's memo, layer 3, EXECUTED there).
9. **A run record.** Hashes of the artifact, argv, env and stdin; the limits; the outcome; the
   door transcript, each frame stamped with the fuel spent so far. The base for deterministic
   replay. *Placeholder memo exists* (`2026-10-17-what-a-replayable-run-needs.md`).
10. **Streamed output.** A callback that receives stdout and stderr chunks as the guest writes
    them, within the output cap. For agent interfaces that show progress and for pipes. *New.*
11. **State across turns.** Whether a variable from one call can exist in the next. *A memo is
    planned* (`2026-10-17-state-across-agent-turns.md`, per `questions-for-the-owner.md`). vfs's
    own ABI is per run and stateless (ADR 082 pin 1), so vfs does not need it for its shell; a
    notebook-style agent would.
12. **A tool-call convention.** A guest helper and a runner argument that turn a tool call into a
    frame and back. *Question 12, deferred by the owner.* Section 3.2 lists what it must cover.
    Items 3, 5 and 6 are what any convention needs from the runtime, so they come first whatever
    the decision.

Not recommended: anything that names an embedder's verbs, error kinds or wire format; a socket
or HTTP import; a second custom import for files or tools (§4.4); a per-tenant fuel ledger (the
embedder sums `fuel_used`).

## 6. Questions for the owner

1. **Should vfs run guests through this project's runner, or through its own host?** vfs's spec
   169b plans its own wasmtime-py host with one guest per process. This runner already runs
   concurrent calls safely. If the runner is the way, item 8 (a filesystem provider) moves up
   and vfs's host shrinks to its shim. If not, item 7 (the contract and the conformance job)
   is what vfs needs most.
2. **May a guest program call tools?** vfs's ADR 082 says a program holds no execution
   capability; your direction says agent code reaches tools, API calls and MCP. If yes, vfs's
   guest door needs a tool verb under its own gates. This project's door carries it either way;
   the answer decides how soon question 12 matters.
3. **Is it in scope for the door to have a host-time deadline and an async host?** Spec 015 put
   async host functions out of scope. Agent tools are mostly network calls that wait. Item 3
   brings them back in.
4. **May an embedder add read-only code to the import path?** Item 5 changes the README's claim
   "only the stdlib zip is on the import path" to "only the stdlib zip and read-only grants the
   embedder names". That loosens a default only at the embedder's explicit request, but §4.15 says
   a change that loosens a default is yours.
5. **Should per-access governance be a goal of this project, or left to embedders?** Option (a)
   gives boundary governance with no new code here; option (b) gives per-access governance and
   needs either vfs's own shim or item 8.

## One line

vfs wants every file, tool and API call an agent's code makes to pass its gates, and the guest's
two channels already guarantee that nothing passes any other way; what this project owes it is a
written contract for its own host, typed grants, a working directory, a read-only import path,
and a door that the deadline and cancellation can reach, all stated so that any embedder could
use them.
