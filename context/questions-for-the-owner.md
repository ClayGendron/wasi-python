# Questions for the owner

Questions the agent could not answer alone, written down so the work could go on (the owner's
instruction of 2026-10-16: "If you do have questions, please write them down in the repo and
continue working"). Each says what waits on it and what the agent did meanwhile. An answered
question moves to the bottom with the answer and the date.

## Open

### 12. A tool-call convention over the door

- **Asked:** 2026-10-17. **Source:** `research/2026-10-17-market-research-use-cases.md`,
  proposal A.
- **The question:** may the project ship an optional convention, such as a guest helper plus
  `tools={name: fn}` on the runner, that turns `tools.lookup(x)` into a JSON frame through the
  door? Constitution §4.4 says the door's frames are opaque to the project.
- **The owner, 2026-10-17:** "Let's come back to this." It waits on the study of what the agent
  runtime needs (`research/2026-10-17-the-runtime-for-agent-code.md`).

### 13–17. The agent runtime

- **Asked:** 2026-10-17. **Source:** `research/2026-10-17-the-runtime-for-agent-code.md` §6.
- **13. Should vfs run guests through this runner, or through its own host?** vfs's spec 169b
  plans its own wasmtime-py host, one guest per process. *Recommended: this runner.* It already
  runs concurrent calls safely; vfs keeps only its shim, and a filesystem provider (memo item 8)
  moves up. If not, the written embedder contract (item 7) comes first.
- **14. May a guest program call tools?** vfs's ADR 082 says a program holds no execution
  capability; the owner's direction says agent code reaches tools, APIs and MCP. *Recommended:
  yes, through the door, under the embedder's gates.* It decides how soon question 12 matters.
- **15. Is a door bounded by host time, and an async host, in scope?** Spec 015 put async host
  functions out. Agent tools mostly wait on the network. *Recommended: yes, as a spec after 015.*
- **16. May an embedder add read-only code to the import path?** It loosens a default only at the
  embedder's explicit request; §4.15 makes that the owner's call. *Recommended: yes, as a
  read-only typed grant.*
- **17. Is per-access governance a goal here, or left to embedders?** *Recommended: left to
  embedders,* with the runner offering the hooks (grants, the door, a provider) they need.

### 18–22. State across agent turns

- **Asked:** 2026-10-17. **Source:** `research/2026-10-17-state-across-agent-turns.md`.
- **18. May the guest gain a second export that runs a turn without finalizing?** It changes the
  recipe and the exports, not the imports (§4.4). *Recommended: yes, after a pre-build review.*
- **19. Is a session in scope?** §3 says the project is "not a development environment".
  *Recommended: yes, bounded,* as a run that spans calls, not a shell.
- **20. The default bounds.** *Recommended: 15 minutes idle, 1 hour lifetime,* in line with the
  market's 15 to 20 minutes.
- **21. Is "a trap ends the session" acceptable for v1?** *Recommended: yes;* pause, resume and
  rollback wait for a later spec.
- **22. Should the README show the files-in-a-root pattern** for state that must outlive a
  process? *Recommended: yes;* it costs a paragraph and no code.

### 23. Publish the wheel on PyPI?

- **Asked:** 2026-10-17, after 0.1.0a2 shipped to GitHub only. **Source:**
  `.github/workflows/release.yml`, job `pypi`.
- **The question:** the release workflow can publish the wheel on PyPI, but the job stays off
  until the owner does two things only the owner can do: register this workflow as a trusted
  publisher for `wasi-python` on pypi.org (owner `ClayGendron`, repository `wasi_python`,
  workflow `release.yml`, environment `pypi`), and set the repository variable `PYPI_PUBLISH` to
  `true`. The name `wasi-python` is free on PyPI today (404).
- *Recommended: yes, from 0.1.0a3.* `pip install wasi-python` is how most users would try it.
  0.1.0a2 stays GitHub-only; re-running its tag would rebuild, not republish.
- **In progress (2026-10-17):** the owner is setting it up, under the name `wasi-python` (PyPI
  treats `wasi_python` as the same name; the import stays `import wasi_python`). The settings:
  on pypi.org, a pending GitHub publisher with project `wasi-python`, owner `ClayGendron`,
  repository `wasi_python`, workflow `release.yml`, environment `pypi`; on GitHub, an environment
  named `pypi` (optionally with the owner as required reviewer) and the Actions variable
  `PYPI_PUBLISH=true`. Nothing publishes before the next tagged release, which still needs the
  §5.6 security review and the owner's word (§7). *Open until the owner says it is done.*

### 24. Should a call with no root and no grants become stricter?

- **Asked:** 2026-10-17. **Source:** `research/2026-10-17-typed-grants.md`, question 1.
- **The question:** typed grants (spec 017) keep today's default: `run(argv)` gets a fresh,
  private, writable `/`. A stricter default, a private `/tmp` only or nothing writable, is safer
  but breaks callers that write a file. `root=False` gives the stricter run to anyone who asks.
- *Recommended: keep the default for now;* revisit before 1.0. Nothing waits on this answer:
  spec 017 changes no default.

### 25–31. scipy

- **Asked:** 2026-10-17. **Source:** `research/2026-10-17-what-scipy-needs.md`. scipy is last on
  §2's list, after matplotlib; nothing is built until these are answered, and none blocks
  current work.
- **The facts:** scipy 1.18.1 builds without Fortran except BLAS/LAPACK. OpenBLAS 0.3.34's C
  LAPACK builds for WASI with zero patches, but declares functions with return types that clash
  with their definitions, which wasm turns into traps at run time (the SVD traps today). The fix
  belongs upstream.
- **25. Licences (§4.12):** may BSL-1.0 (Boost.Math, ryu), the Qhull licence,
  BSD-3-Clause-LBNL (xsf), BSD-2-Clause (fast_matrix_market) and the BSD/MIT set (scipy,
  OpenBLAS, LAPACK, HiGHS, ducc0, pybind11 and others) be linked? *Recommended: yes;* without
  Boost there is no `scipy.special` or `scipy.stats`.
- **26. Upstream:** may the agent draft an OpenBLAS issue and pull request (one return
  convention, plus four WASI portability fixes) and a small scipy one, for you to read and send?
  *Recommended: yes,* as with numpy and wasmtime-py: you approve before anything is posted.
- **27. Wait or shim:** answered by question 32: neither; carried patches.
- **28. `scipy.odr`:** accept its absence (scipy has deprecated it)? *Recommended: yes.*
- **29. SIMD:** OpenBLAS's wasm target needs wasm SIMD. Accept it as a host requirement, as
  exception handling already is? *Recommended: yes;* every wasmtime since 2021 has it.
- **30. A profile:** scipy adds about 20–25 MB to `python.wasm` (INFERRED from Pyodide's
  wheels). Ship it only in a separate scipy build? *Recommended: yes,* which makes build profiles
  a prerequisite.
- **31. pythran:** build without it first (5 modules fall back to slower code), or pin it and
  its three dependencies as build tools? *Recommended: without, at first.*

### 33. Reword §4.1's clause that spec 020 has now fulfilled?

- **Asked:** 2026-10-17. **Source:** spec 020's build review, confirmation C3.
- **The fact:** §4.1 ends "(owner, 2026-10-17, question 32; until the specification that builds
  this lands, no patch is applied and the old zero-diff check stands)". Spec 020 has landed, so
  the clause has expired by its own words, and reads as history. The agent edited it to "built by
  spec 020" and then reverted that, because only the owner changes the constitution.
- **The question:** may the agent replace the clause with "(owner, 2026-10-17, question 32;
  built by spec 020)"? *Recommended: yes;* it changes no rule. Nothing waits on it.

## The owner's direction for the product (2026-10-17)

"I am thinking of this more as a safe runtime for agent code. The use case is much more
powerful web agents that can access code and interact with their data and tools (either through
a file system, tools in the host program, api calls, mcp, etc.) its main use case is to work with
~/Git/repos/vfs and run on top of that where vfs manages the permissions and governance."

The code stays embedder-neutral (§4.5). The capabilities that agent use needs are built as
general features; `research/2026-10-17-the-runtime-for-agent-code.md` studies which. State
across turns is researched before any specification (`research/2026-10-17-state-across-agent-turns.md`).

## Answered

### 32. Carry our own fixes to other projects, or wait for upstream?

- **Asked:** 2026-10-17. **Source:** `research/2026-10-17-what-scipy-needs.md` (OpenBLAS's C
  LAPACK traps under wasm until a type fix lands upstream), and question 27.
- **The question:** keep §4.1's zero patches (wait, or carry a generated shim layer), or carry
  patch files that mirror drafted upstream pull requests; and for which projects.
- **Answered 2026-10-17:** Carried patches, for any pinned project, each with an upstream PR
  drafted in the repository: "I do not want to wait for upstream. I want to build fixes
  ourselves but document the upstream fixes (PRs) we should submit to other projects." §4.1 is
  amended; a specification builds the mechanism (patch layout, apply step, `MANIFEST` lines, the
  release check) before any patch is applied. This also answers question 27 (no waiting) and
  reopens numpy's `.npy` fix (question 8) as a carried patch.

### 1. Constitution: "only the grants the embedder gives, which may be none"

- **Asked:** 2026-10-16. **Source:** `research/2026-10-16-a-principal-engineers-direction.md`
  (direction 4, "Constitution changes proposed"), `research/2026-10-16-where-package-data-lives.md`
  ("The owner's direction").
- **The change:** §2.2 and §2.4 say the guest sees "the one directory the embedder preopens".
  They would say: only the grants the embedder gives (read-only or writable folders), which may
  be none. The embedder contract becomes "bind one function, call one export; preopen what you
  grant".
- **What waits:** matplotlib's data (a second, read-only folder), several folders per run
  (typed grants), and a run with no folder at all.
- **Meanwhile:** the agent builds what the current text allows (spec 005, the hostile-guest
  checks, safe defaults with one folder).
- **Answered 2026-10-17:** Yes: typed grants, read-only or writable, which may be none. The constitution's §2.2 and §2.4 are amended.

### 2. matplotlib's data: a read-only folder (C2) or packed inside the binary (C3, wasi-vfs)

- **Asked:** 2026-10-16. **Source:** `research/2026-10-16-where-package-data-lives.md`,
  `research/2026-10-16-wasi-vfs-for-package-data.md`.
- **The agent's recommendation:** C2, a read-only folder mounted at the path matplotlib already
  looks in. wasi-vfs works on the real build and allows zero folders, but its packed output is
  not byte-reproducible (uninitialised padding), it adds about one instruction of start-up per
  packed byte for a reason not found, it brings Rust runtime code whose licences would ship, and
  it has one maintainer who has said he has little time. C3 is worth it only if a run with no
  folder at all, and the stdlib zip inside the binary, become goals.
- **What waits:** the matplotlib specification.
- **Answered 2026-10-17:** C2: a read-only folder where matplotlib already looks, built on typed grants. The constitution's §2 records it.

### 3. A new hard constraint, "safe by default"

- **Asked:** 2026-10-16. **Source:** the principal engineer's memo.
- **The change:** a new §4 rule: every limit has a default; no channel to the host opens
  without an explicit argument; the runtime's files are never in a writable grant.
- **Meanwhile:** the agent gives `run()` safe defaults anyway (your direction: "no way (unless
  explicitly provided) to access the host file system or network"); the rule would make them
  binding on every later change.
- **Answered 2026-10-17:** Yes, binding: §4.15 "Safe by default". A change that loosens a default needs the owner's decision.

### 4. Order of post-v1 work: sqlite3, bz2, lzma before matplotlib?

- **Asked:** 2026-10-16. **Source:** the principal engineer's memo, direction 8.
- **The question:** your order is matplotlib, then sqlite3/bz2/lzma, then scipy. matplotlib now
  waits on questions 1 and 2; sqlite3, bz2 and lzma need no C++ and no data folder. The agent
  works on them while matplotlib waits, and keeps your order for anything not blocked.
- **Answered 2026-10-17:** sqlite3, bz2 and lzma first (spec 007), then typed grants and matplotlib. The constitution's §2 records it.

### 5. Security rules for releases

- **Asked:** 2026-10-16. **Source:** the principal engineer's memo, direction 7.
- **The change:** §5.5 gains "a security fix in a pinned component is a reason to release";
  §5.6 gains "a security review against the written threat model before each release".
- **Meanwhile:** the agent adds `SECURITY.md` and build-provenance attestations to the release
  workflow, which change no rule.
- **Answered 2026-10-17:** Both: §5.5 (a security fix in a pinned component is a reason to release; the agent prepares one and asks) and §5.6 (a security review against the threat model before each release).

### 6. May the agent publish 0.1.0a2?

- **Asked:** 2026-10-16.
- **The question:** you authorised 0.1.0a1. Spec 005 names the 3.15 line's release `0.1.0a2`.
  The agent will prepare it (version bump, changelog, a green dry run of the release workflow)
  but will not push the tag until you say so (constitution §7).
- **Status, 2026-10-17:** ready. `__version__` is `0.1.0a2`, and the CHANGELOG's unreleased
  section covers specs 005 to 014. The dry run of `1f21dd0` passed every job, including the arm64
  Linux rebuild with byte-identical `SHA256SUMS`. Before tagging, the agent will run one security
  review of the release against the threat model, by a fresh agent. Releasing is one command
  (`release/version.py release`) once you say yes.
- **Answered 2026-10-17:** Yes, after a security review of the release against the threat model by a fresh agent; then the agent tags v0.1.0a2.

### 7. A `wasi-python run` command line?

- **Asked:** 2026-10-16. **Source:** the principal engineer's memo.
- **The question:** §3 says the project "ships no shell". Is a thin command that runs a program
  and prints a JSON result part of the runner (allowed) or a shell (not)? The agent reads it as
  the runner but does not build it until you answer.
- **Answered 2026-10-17:** Yes, as part of the runner: `wasi-python run` prints one program's result as JSON. The constitution's §3 records it.

### 8. numpy's `.npy` files

- **Asked:** 2026-10-16. **Source:** `research/2026-10-16-what-data-folders-the-packages-need.md`.
- **The fact:** `np.save` and `np.load` of `.npy` files fail in 0.1.0a1 because numpy calls
  `os.dup`, which WASI preview1 does not have. Zero patches rules out a local fix.
- **The question:** may the agent file an upstream numpy issue (an outward-facing action)? The
  agent writes the issue text into the repository and records the failure as a known gap.
- **Answered 2026-10-17:** File it, after the owner reads and approves the text (drafted as an artifact).

### 9. Licences for sqlite3, bz2 and lzma

- **Asked:** 2026-10-17. **Source:** `research/2026-10-17-sqlite-bz2-and-lzma.md`.
- **The question:** constitution §4.12: "Nothing with a licence the owner has not approved is
  linked in." Building these three modules in links: SQLite 3.54.1 (public domain: its
  header's blessing, no licence file), bzip2 1.0.8 (its own BSD-style licence), and liblzma from
  xz 5.8.4 (0BSD). Do you approve them?
- **What waits:** spec 007 (sqlite3, bz2 and lzma) is written and reviewed, but not built, until
  you answer. The experiment shows all three build with no patch; bz2 and lzma match native
  byte for byte; sqlite3 works with one limit (one connection writes at a time, through a lock
  directory beside the database).
- **Answered 2026-10-17:** Approved: SQLite (public domain), bzip2 (BSD-style), liblzma from xz (0BSD). The constitution's §4.12 records it; spec 007 is unblocked.

### 10. Turn on private vulnerability reporting?

- **Asked:** 2026-10-17. **Source:** spec 009 (`specifications/009-release-security.md`).
- **The question:** `SECURITY.md` asks reporters to use GitHub's "Report a vulnerability"
  button, which works only when private vulnerability reporting is on in the repository's
  settings (Settings → Code security). May the agent turn it on (`gh api -X PUT
  repos/ClayGendron/wasi_python/private-vulnerability-reporting`), or will you?
- **Meanwhile:** `SECURITY.md` is not written yet; it waits on this answer (spec 010, the other
  thing it waited on, landed 2026-10-17), so that its reporting route works.
- **Answered 2026-10-17:** Yes, the agent turns it on (`gh api`), then writes `SECURITY.md`.

### 11. File a wasmtime-py issue about its shared callback tables?

- **Asked:** 2026-10-17. **Source:** spec 010's build review, finding 1, and spec 011
  (`specifications/011-concurrent-calls-share-nothing.md`).
- **The fact:** wasmtime-py keeps the Python callbacks of `define_func` and of custom WASI
  output in two process-wide tables with no lock. Threads that define or free them at once
  corrupt the tables (EXECUTED: after a few hundred concurrent calls every later call raised).
  Spec 011 works around it in the runner, without patching wasmtime-py.
- **The question:** may the agent file the issue (an outward-facing action)? The agent writes
  its text into spec 011's landing notes either way.
- **Answered 2026-10-17:** File it, after the owner reads and approves the text (drafted as an artifact).

