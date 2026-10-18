# The owner's decisions

Answers to the questions in `questions-for-the-owner.md`, moved here once answered, newest first.
Each keeps its question number, the date, the owner's answer, and what follows from it. A
decision that changes the constitution is also recorded there (`constitution.md`, its Status
line); this file is the record for the rest.

The owner went through every open question on 2026-10-17. Decisions that change the
constitution are recorded there (§3, §4.1, §4.4, §4.12, §4.15).

### The owner's answers of 2026-10-18, evening (questions 64, 90, 92 to 97, and pull requests)

Asked one by one, with the agent's recommendation in each question.

- **64 (the wheel and PyPI's limit):** "wait on a decision until we cross the 100MB threshold".
  The wheel is about 54.3 MB with lxml (spec 046). Each landing records its size; the agent
  brings the question back when a landing would cross 100 MB.
- **90 (`batch` in the tool protocol):** after 0.1.0, as recommended.
- **92 (bounded sessions, spec 055):** keep its three choices where they follow precedent,
  "especially that of Jupyter". `sys.exit()` keeps the session and the last expression is echoed,
  as in Jupyter, so both stand. Closing did not follow Jupyter, which lets Python exit normally;
  the owner chose to follow Jupyter: at close and at expiry the session runs Python's shutdown
  (`atexit`, flushes) inside a small fuel and time budget, and is stopped if the budget runs out.
  Spec 055's Decision 8 changes before it is built. **The descriptor cap comes before 0.1.0**: a
  per-sandbox limit on files open at once, set by the embedder like the other limits, default
  1,024, `EMFILE` past it, for `run` and sessions alike. The owner's principle, kept: "if an
  embedder provides it access to an OS and file system, it should be able to use that file system
  until time, fuel, memory, etc of that individual session run out"; the cap guards the host
  process, not what the guest may use. A specification of its own.
- **93 (a read-only mount on the import path):** no. "Agents will not be importing code, and
  wasi python should not design for this use case. The dev building an app with wasi python
  would define all of the imports and code and libraries upfront." Mounts stay refused there.
- **94 (rulesets):** yes, the agent sets them. Done 2026-10-18 with the owner's `gh`: ruleset
  25363090 on the default branch (no deletion, no force push, updates only by the admin role)
  and 25363091 on `refs/tags/v*` (creation, deletion, moves and updates only by the admin role).
  The agent's pushes pass as the admin's ("Bypassed rule violations" is printed on each push).
- **95 (docs commits after a dry run):** allowed, written into AGENTS.md rule 6b.
- **96 (a Rust core):** "I want to move over to a rust core after 0.1.0, but I do not think that
  mean we replace wasmtime-py, but this can be decided later. The main thing is a rust code that
  can be shared by python and js, at least partially, so there is less to maintain." After 0.1.0;
  the research and the spike are on record.
- **97 (the release environments):** "nothing for now, later we can state the main is the only
  branch that can do the release and enforce a human review step."
- **Pull requests (asked with question 98):** "We should push changes as a branch, create a PR to
  main that runs the tests, and once completed and approved, merge the changes." Asked who
  approves (a pull request's author cannot approve it, and the agent works as the owner's
  account), the owner chose "My account, checks only": pull requests must pass their checks; no
  approval is required. Spec 064 specifies it, after spec 063, whose shards become the checks.

### 91, answered: up to three build changes built at once (2026-10-18)

- **Asked:** 2026-10-18 (question 91: build the next build-class specification stacked on the one
  in review?). The owner asked that day what limited parallel work; the agent named constitution
  §5.7's own rule ("a change to the build recipe overlaps no other change to the build recipe",
  the owner, 2026-10-17) and offered two shapes: build in parallel and land one at a time, or ship
  several as one landing.
- **The owner, 2026-10-18:** option A, "up to 3, land one by one".
- **What follows:** constitution §5.7 and AGENTS.md rule 2 are amended. Up to three build-class
  specifications are built and reviewed at once, each in its own worktree. Each lands alone: the
  lane rebases it, rebuilds the set from the pins in the main tree, compares it with the builder's
  set rebuilt on the same base, judges and re-measures it; a delta review follows when the rebase
  altered its recipe hunks or its numbers moved beyond what its review saw. Shipping several as one
  landing was declined: one landing stays one specification (§5.4). Chains stay in order (scipy
  before scikit-learn and statsmodels; 041 before 039).

### The x86_64 rebuild without emulation (2026-10-18)

The owner, 2026-10-18: "I don't see the value in the hour long build under emulation", then, on
`research/2026-10-18-byte-identical-wasm-builds-prior-art.md` (the flag `-ffp-contract=off`
makes the pinned x86_64 and aarch64 clangs emit the same numpy object; no project studied
emulates a compiler or normalizes compiler output): "I agree, please make these changes."

- `-ffp-contract=off` goes on **every** compile in the recipe (one rule, not numpy only), as a
  recipe item under constitution §4.1's first kind.
- The x86_64 rebuild runs natively. The emulated compiler (spec 040's `clang-emulated` and its
  pins) stays in the tree, switched off, for one release as the same-day fallback, then is
  deleted.
- "The same bytes" keeps one meaning: `SHA256SUMS` equal, byte for byte. No per-function
  exception list.
- Specification 059 carries it, build-class, after spec 023 and before spec 057. It changes
  specs 012 and 040's decisions; its evidence is a dry run with emulation off.

### Work on while the owner is away; the agent may publish alphas (2026-10-18)

The owner, before stepping away on 2026-10-18: "please continue working and do not pause to wait
for me. If you run into issues like git worktree, find a resolution for them that is safe. If
you have questions, please document them in questions for owner. Do not stop working unless
0.1.0 is fully implemented and ready to publish. You may publish alpha releases but not the
0.1.0 release."

- This is the owner's explicit instruction under constitution §7 for these actions: pushing
  `main` and alpha tags (`v0.1.0aN`), dispatching the release workflow's dry runs, and
  publishing alpha releases to GitHub and PyPI. Every other §7 rule stands: no 0.1.0 tag, no
  final release, nothing else outward-facing.
- Each alpha still waits on its pre-release security review (§5.6).
- Two working changes the owner asked for the same day: builders and reviewers loop on the
  judge's fast tier and run the full judge once per stage (`AGENTS.md`, rule 3a); and the judge
  on several cores, researched and specified first (spec 052).

### 49–89. The overnight questions (answered 2026-10-18)

The owner went through every question written overnight on 2026-10-18, in rounds, with the
agent's recommendation beside each. The full questions, with their facts, are in git history
(`questions-for-the-owner.md` before this change) and in the specifications they cite.

- **49, answered:** nothing is cut from 0.1.0. The owner: "we need to have the tool protocol, a
  byo file system for embedders, async host functions, sessions, so basically cancel nothing for
  0.1.0". So 0.1.0 carries the cancel fix (030), the tool protocol (031, 036), the filesystem
  provider (032) and writable mounts (034), and also async host functions, read-only code on the
  import path and bounded sessions (state across agent turns). The three new ones need
  specifications; sessions need their research first (`research/2026-10-17-state-across-agent-turns.md`).
- **50–53, answered:** keep the tool protocol's defaults as built.
- **54, answered:** a provider may also raise `OSError`; its errno is then the guest's answer
  (any other exception stays a fault, `EIO`). A follow-up change to spec 032's provider.
- **55, 56 and 72, answered:** keep as built (staging bounded by `memory_bytes`, the
  `max_file_calls` names, one buffer per open).
- **57–63, answered:** keep all as decided: 033 landed first; the `-V` banner keeps "no ctypes";
  spec 035's reader replaces `zipfile.Path` for the zip's packages, and its three run-time
  replacements are a recipe under §4.1, not a carried patch; scipy is not pre-imported until
  measured (with question 34's numbers); OpenBLAS's backport is carried in git until 0.3.35;
  x86_64 compiles with the emulated aarch64 clang.
- **64:** still open (wait, then assess from the measured wheel).
- **70, answered:** yes, unpushed only. If a bad acceptance commit reaches `main` unpushed, the
  lane may `git reset --soft` that one commit (constitution §4.14); a pushed one stops the lane
  and comes to the owner.
- **71, answered:** the POSIX rule: unclosed files are handed to the provider at every ending
  that returns a result, a cancel and a deadline included. Spec 034 lands as built.
- **73, answered:** (a) reportlab's fonts stay out for good; (b) the agent drafts a facts sheet
  on the `zipimporter._files` bug for the owner to send; (c) the four-clause BSD of Tyler C.
  Sarna's barcode modules is approved with its advertising clause (§4.12): a later change ships
  `reportlab/graphics/barcode/`, adds a QR code and a Code 128 barcode to the PDF golden, and
  puts "This product includes software developed by Tyler C. Sarna." in the README's barcode
  line, the CHANGELOG, and any later material that mentions barcodes.
- **80, answered:** for projects that restrict AI-written contributions, the upstream draft is a
  facts sheet (spec 020's six header lines) from which the owner writes and files in their own
  words.
- **81, answered:** contourpy (BSD-3-Clause) approved, with `LICENSE_YORICK` covering its
  GIST-derived code (§4.12). Spec 043 is unblocked.
- **82, answered:** (a) lxml (046) and regex (047) may take a free build-class slot before
  scipy (037, 038); (b) `lxml.isoschematron` stays out for 0.1.0; (c) lxml's ElementTree and
  difflib-derived files are read as inside the approved CPython family; (d) the agent drafts a
  wasi-libc and musl facts sheet on GB18030.
- **83, answered:** all as decided in specs 044 and 045: scikit-learn's and statsmodels'
  bundled code approved; CC BY 4.0 approved for scikit-learn's digits, breast cancer and wine
  data (§4.12), all six datasets ship with an attribution part; the two sample photographs and
  statsmodels' fourteen datasets without public-domain terms stay out. Specs 044 and 045 are
  unblocked.
- **84:** settled by events: spec 048's mitigation landed before any release.
- **85, answered:** the exact 49.0.3 rule (as landed); symlinks are not refused.
- **86, answered:** facts sheet 12 stays the standing ask; the shadow is removed with the pin
  that moves past wasmtime 49.0.3.
- **87, answered:** both, after 0.1.0a4 (with the fix) is on PyPI: the owner yanks 0.1.0a3 and
  publishes a GitHub security advisory for wasi-python; the agent drafts the advisory text.
- **88, answered:** the stricter promise: a deprecated thing survives at least **two** final
  minor releases (as CPython's PEP 387), the rest as spec 049 writes it. Spec 049 is revised to
  say so before it is built.
- **89, answered:** (a), a judge-only binary linked with numpy's test modules, never shipped:
  a later build-class specification.

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

