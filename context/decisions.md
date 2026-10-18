# The owner's decisions

Answers to the questions in `questions-for-the-owner.md`, moved here once answered, newest first.
Each keeps its question number, the date, the owner's answer, and what follows from it. A
decision that changes the constitution is also recorded there (`constitution.md`, its Status
line); this file is the record for the rest.

The owner went through every open question on 2026-10-17. Decisions that change the
constitution are recorded there (§3, §4.1, §4.4, §4.12, §4.15).

### 43–48. What else the default profile carries

- **Source:** `research/2026-10-17-what-else-the-default-profile-carries.md` (tiers A to D).
- **43, answered 2026-10-17:** tiers A and B approved, with their licences (constitution §4.12),
  tqdm's MPL-2.0 and regex's CNRI-Python included.
- **44, answered 2026-10-17:** cut the zip's per-member cost first: a research memo, then a
  specification ("the zip's directory is read once"), before tier A grows the zip.
- **45, answered 2026-10-17:** sympy (with mpmath) joins the default profile after that fix.
- **46, answered 2026-10-17:** nothing writable stays the default; the README documents that
  openpyxl needs a writable folder and that xlsxwriter (or pandas' `engine="xlsxwriter"`) writes
  in memory.
- **47, answered 2026-10-17:** pytz is left out; `zoneinfo` is the supported path.
- **48, answered 2026-10-17:** all of tier B is in 0.1.0: scikit-learn, statsmodels, lxml (with
  python-docx and python-pptx) and regex, after scipy.

### The roadmap, and 0.1.0's contents

- **Decided 2026-10-17:** "Matplotlib and scipy are v0.1.0 for sure, and we should probably
  consider what other libraries we should include for our v0.1.0 default profile." And: "Vfs
  shouldn't be a part of our 0.1.0 considerations, that is the main consumer of this package but
  not a part of its roadmap, and can we update the constitution to remove roadmap details from
  it? That will change over time."
- Done: the constitution's §2 is now the bar every release meets; the order of work and each
  release's contents live in `roadmap.md`. The candidates for the default profile are being
  researched.

### 41–42. The filesystem provider

- **Source:** `research/2026-10-17-a-filesystem-provider-for-the-runner.md`.
- **41, answered 2026-10-17:** a provider may be mounted at `/`, making the embedder the guest's
  whole filesystem; a `/` mount and `root=` are mutually exclusive; the zip stays at
  `/usr/local/lib`.
- **42, answered 2026-10-17:** provider calls have a default limit of 10,000 per run; at the
  limit the run stops, as at its fuel or deadline, and the result names it.

### 37. The tool protocol's gate, and 13. vfs on this runner

- **Studied:** vfs's authority model (read-only, 2026-10-17): every vfs verb takes an
  `Authority`; programs get an `Fs` curried with the caller's authority (vfs ADR 082); every call
  re-enters the router's gates; a denial is a `Result`, never an exception; "No `ask` inside
  vfs" (ADR 084); vfs needs to count calls (`VERB_CALL_BUDGET`) and record refused writes even on
  exit 0 (its specs 169 and 172); vfs planned its own host (spec 169b) and treated wasi_python as
  artifacts only.
- **37, answered 2026-10-17:** an optional `gate=`. Tools are capabilities, their authority bound
  by the embedder; wasi_python validates, routes, counts (`max_tool_calls`, with a default) and
  records each call's outcome in the result; `gate=` may refuse a validated call before the tool
  runs, and is absent by default.
- **13, answered 2026-10-17:** "converge on our runner, but do not edit vfs". vfs is to run its
  guests through `wasi_python.run`. That needs a filesystem provider in the runner (the guest's
  file calls served by embedder code, as vfs's 169b shim does), researched first. This project
  never edits vfs; vfs's own specifications are vfs's to change.

### Parallel work: build in parallel, land in series

- **Decided 2026-10-17:** adopted `research/2026-10-17-parallel-work-without-lowering-the-bar.md`
  (decisions A to D applied to constitution §4.14, §5.4, §5.7, §7 and `AGENTS.md`; F: commits on
  `spec/` branches are commits, so §4.14 applies as written). Decision E, the four judge rules
  (an acceptance sits on the commit it judged; main is linear; `--accept` refuses in a linked
  worktree; a worktree inside the repository is not judge input), is built as its own
  specification before parallel builders run.
- Disk: the old scratch clones of landed specifications were deleted (owner's approval).

### 38–40. The tool protocol (37 stays open)

- **38, answered 2026-10-17:** the guest's namespace is `host`: `from host import tools`.
- **39, answered 2026-10-17:** schemas are validated first. Errors follow `subprocess.run`'s
  precedent: `run()` never raises for what the guest or a tool does (it returns `exit_code`,
  `stdout`, `stderr`); it raises only for programming mistakes, before anything runs; inside the
  guest a failed tool call raises `ToolError`, as normal Python. No `run_safe`.
- **40, answered 2026-10-17:** no adapters ship (LangChain, MCP); the README may show recipes.

### Install as `pip install wasi-python`, without the `run` extra

- **Decided 2026-10-17**, after 0.1.0a3 shipped: "Could we change it to just pip install
  wasi-python and not with the run for the next release? That would be a better dev experience."
- wasmtime-py (`wasmtime>=49,<50`, about 8 to 10 MB per platform, with a wheel for every major
  platform) becomes a required dependency; `wasi-python[run]` stays as an empty alias so older
  instructions work. Built as spec 028 for 0.1.0a4 (§4.13 asks the specification for the reason).

### 12 and 14. A tool protocol over the door

- **Asked:** 2026-10-17 (12: `research/2026-10-17-market-research-use-cases.md`, proposal A;
  14: `research/2026-10-17-the-runtime-for-agent-code.md` §6).
- **Answered 2026-10-17:** yes. "wasm-python should be able to call tools/api/MCPs of the host
  program through a gated protocol that we design." And: "we should build our own convention.
  study langchain tools and monty for how it develops tools and how it passes to an embedded
  programs so we have a clean and familiar api." §4.4 amended: the raw door stays opaque; one
  optional tool protocol rides on it, used only when the embedder passes tools, gated per call.
- **Next:** a research memo on LangChain's tool API and Monty's embedding API, then a
  specification.

### 15. Async host functions

- **Answered 2026-10-17:** yes, as a later specification, with the tool protocol: an async host
  function awaited by the guest's door call, under the call's deadline.

### 16. Read-only code on the guest's import path

- **Answered 2026-10-17:** yes, as an explicit read-only typed grant the embedder asks for;
  never writable, never by default.

### 17. Per-access governance

- **Answered 2026-10-17:** left to embedders. The runner offers the hooks (grants, the gated
  tool protocol, a filesystem provider); policy and audit live outside.

### 18–22. State across agent turns

- **Source:** `research/2026-10-17-state-across-agent-turns.md`.
- **18, answered 2026-10-17:** yes, a second guest export that runs a turn without finalizing,
  after a pre-build review.
- **19, answered 2026-10-17:** a bounded session is in scope (§3 amended): one guest across
  several calls, not a shell.
- **20, answered 2026-10-17:** default bounds 15 minutes idle and 1 hour lifetime, both
  overridable.
- **21, answered 2026-10-17:** a trap ends the session in its first version; pause, resume and
  rollback come later.
- **22, answered 2026-10-17:** yes, the README shows the files-in-a-granted-folder pattern for
  state that outlives a process.

### 23. Publish the wheel on PyPI?

- **Answered 2026-10-17:** yes, from 0.1.0a3, under `wasi-python`. The owner created the project
  on pypi.org and configured this repository as its trusted publisher: "try publishing to it".
  The agent sets the Actions variable `PYPI_PUBLISH=true` (GitHub makes the `pypi` environment
  on first use) and tags v0.1.0a3 once its release work is clear: spec 024 (the security
  review's S1), its confirmation, and question 24's strict default.

### 24. A stricter default

- **Answered 2026-10-17:** "our wasi-python shouldn't be able to interact with a filesystem
  unless explicitly provided by the embedder." A call given no root and no grants has nothing
  writable: no folder, no `/tmp`, no `HOME` (§4.15 amended). `root=None` (a private scratch
  root) stays available when asked for. It ships in 0.1.0a3, before the first PyPI release, as
  its own specification with a README migration note.

### 25 and 28–31. scipy

- **Source:** `research/2026-10-17-what-scipy-needs.md`,
  `research/2026-10-17-openblas-one-return-convention.md`.
- **25, answered 2026-10-17:** all of scipy's licences approved (§4.12 amended).
- **26:** covered by question 32's scope ("any project, with a drafted pull request").
- **28, answered 2026-10-17:** `scipy.odr` may be absent, documented, with a clear
  `ImportError`.
- **29, answered 2026-10-17:** wasm SIMD is accepted as a host requirement, in the default build
  too (it follows from 30). The judge pins the feature list with `+simd128`.
- **30, answered 2026-10-17:** "in the default build for now, we can assess later how to divy
  things up once we get to profiles."
- **31, answered 2026-10-17:** without pythran at first.

### 33. §4.1's spent clause

- **Answered 2026-10-17:** reword it, without naming the owner. It now reads "(question 32;
  built by spec 020)".

### 35. Licences for matplotlib

- **Answered 2026-10-17:** the whole list approved (§4.12 amended). Spec 023 can be built.

### 36. Upstream for matplotlib's patches

- **Answered 2026-10-17:** yes. Patch 1's draft says it is merged upstream; patch 2's pull
  request (`_qhull` without a writable `/dev/null`) is drafted for the owner to send, with M2.

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

