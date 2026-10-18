# Questions for the owner

Questions the agent could not answer alone, written down so the work could go on (the owner's
instruction of 2026-10-16: "If you do have questions, please write them down in the repo and
continue working"). Each says what waits on it and what the agent did meanwhile. An answered
question moves to another document (research, spec, review, etc.) and is deleted from this
document.

## Open

### 34. Pre-import matplotlib in the default snapshot?

- **Asked:** 2026-10-17. **Source:** `research/2026-10-17-matplotlib-on-the-current-line.md`.
- Pre-importing makes a plotting call 4.6 times cheaper (5.81 G to 1.25 G fuel) but costs every
  call +23.4 M fuel (+28% on `pass`), grows the snapshot 17.5 MB and each instance's starting
  memory 18 MiB.
- **The owner, 2026-10-17:** decide after matplotlib's first milestone (spec 023) is built,
  from the real set's measurements. The agent brings the numbers back then.
- **The numbers, 2026-10-18** (EXECUTED by spec 023's builder on its built set, a scratch
  snapshot with matplotlib pre-imported; nothing of it lands; spec 023's landing notes, in its
  build review now):

  | | no pre-import | pre-imported |
  |---|---|---|
  | a plot job with its PNG save (fuel) | 7.56 G fresh cache, 5.57 G kept cache | 1.02 G (7.4 and 5.5 times less) |
  | `-c pass` (fuel) | 83.37 M | 106.64 M (+27.9%) |
  | the snapshot | 70.90 MB | 88.39 MB (+24.7%) |
  | starting memory per instance | 57.3 MiB | 74.0 MiB (+16.75 MiB) |
  | the wheel | 52.1 MB | about 58.5 MB |

- **The agent's recommendation:** do not pre-import for 0.1.0. Every call, plotting or not, would
  pay +28% fuel and +16.75 MiB of starting memory, while a plotting call already works and only
  costs more fuel the first time in a process. A profile that pre-imports matplotlib is the
  constitution's answer for plotting-heavy embedders (§2, "a profile is its own artifact set").
  Meanwhile: not pre-imported; nothing waits on the answer.

### 64. The wheel and PyPI's file-size limit

- **Asked:** 2026-10-17 (overnight). **Source:** `specifications/039-tier-a-packages.md`,
  Decision 13. Nothing in spec 039 waits on it; 0.1.0's PyPI upload does.
- **The fact:** PyPI refuses a file over 100.0 MiB unless the project's own limit is raised
  ("100.0 MiB by default; individual projects may differ … we can sometimes increase your
  limit", READ: `https://pypi.org/help/`, 2026-10-17). The `wasi-python` wheel carries the
  whole artifact set. Its three large files deflate to about 38.7 MB today (EXECUTED while
  drafting 039: `python.wasm` 7.6 MB, the snapshot 20.1 MB, the zip 10.9 MB, which is already
  deflated). Tier A adds about 16.5 MB of zip. With matplotlib M1, scipy and tier B as their
  documents estimate, the wheel reaches about 95 to 110 MB before 0.1.0 (INFERRED).
- **The question:** before 0.1.0, will you ask PyPI to raise `wasi-python`'s limit (an action on
  your account), or should the agent plan another route? The other routes each cost something
  the project has chosen against: publishing the snapshot binary as a second wheel makes one
  install two packages; a smaller default profile undoes decisions 43 and 48.
- **The agent's recommendation:** ask for the raise once spec 023 has landed, citing the
  measured wheel. Each landing until then records the wheel's size (039's landing notes do), so
  the request carries real numbers.
- **The owner, 2026-10-18:** wait; measure the wheel as packages land, then assess the route
  from the real size. Each landing records the wheel's size; the agent brings the number back.
- **Measured, 2026-10-18** (EXECUTED by spec 023's builder, the wheel built as spec 028 builds
  it): main's set (035) gives a 38.9 MB wheel; with matplotlib M1 it is 52,070,134 bytes
  (49.7 MiB): the stdlib zip deflates to 21.6 MB, the snapshot to 21.4 MB, `python.wasm` to
  8.8 MB. So M1 added about 13 MB, less than the documents estimated (spec 035's reader does not
  change size; the zip's 631 new members do). Still to come: scipy (037, 038), tier A (039) and
  tier B (044 to 047); the estimate of 95 to 110 MB at 0.1.0 is revised when scipy lands.

### 94. The release path's repository settings

- **Asked:** 2026-10-18. **Source:** the 0.1.0a4 security review's note N3
  (`build/reviews-evidence/a4-security/0.1.0a4-security-review-2026-10-18.md`, git-ignored),
  `specifications/056-the-a4-security-reviews-findings.md`, Decision 6. Nothing in 0.1.0a4
  waits on it: the review does not block on N3.
- **The fact:** the release path's human controls cannot be seen from the repository. The
  `publish` job (`contents: write`) has no protected environment, and branch and tag protection
  cannot be verified from a checkout (READ, the review). Spec 029's landing-lane guards are a
  process aid on the agent's side, not a control.
- **The question:** will you add rulesets on `main` and on `v*` tags (no force push, no deletion,
  pushes by you only) and a protected environment, with you as the required reviewer, for the
  `publish` and `pypi` jobs? These are settings on your GitHub account; the agent cannot set
  them. The workflow side (naming the environment in `release.yml`, `enable-cache: false`) goes
  in the follow-up build-class specification that 056 names.
- **The agent's recommendation:** yes, before 0.1.0 final. Then the follow-up names the
  environment in the workflow.
### 96. A Rust core with JavaScript and Python wrappers?

- **Asked:** 2026-10-18. **Source:** the owner's proposal that day (a Rust core runner on the
  `wasmtime` crate, napi-rs for Node, Bun and Deno, PyO3 replacing wasmtime-py, the artifacts
  downloaded on first use), assessed at the owner's request in
  `research/2026-10-18-a-rust-core-with-js-and-python-wrappers.md`.
- **The facts (the memo):** the constitution's "no JavaScript" rule is about the guest, and §2.4
  already expects embedders in other languages, so a JavaScript binding fits. wasmtime-py has
  shipped every wasmtime major release on the same day for twelve months, never a patch release,
  and wasmtime 50 is due within days; nothing is patched into wasmtime-py (spec 048 shadows two
  calls in Python). The port is far larger than mounts.py: the door's threading, async tools,
  cancel, sessions, the frozen API of spec 049, and a judge that drives the artifacts with its
  own wasmtime-py driver. napi-rs promises Node; Bun is best effort and Deno is not promised.
  Download on first use contradicts the mission's "without … a package install step" and opens a
  network channel in the embedder's process.
- **The question:** which of the three parts, if any, should go on the roadmap, and when?
- **The agent's recommendation (the memo's verdict):** adopt in part, after 0.1.0.
  - Now: a time-boxed research spike, a Rust `run()` checked against the judge, to settle
    whether fuel counts match across runners. It commits to nothing.
  - After 0.1.0 and the wasmtime 50 pin: a separate Node package on that core.
  - Keep the Python wheel on wasmtime-py, and keep bundling the artifacts in it, asking PyPI
    for the size raise (question 64).
- **The owner, 2026-10-18 (in part):** "have an opus agent run the rust spike". **The spike
  (`research/2026-10-18-a-rust-runner-spike-against-the-judge.md`):** with the same wasmtime and
  Config, a Rust `run()` gives the same outputs on 16 of 16 judge jobs and the same fuel to the
  instruction; the only steady gap (3e-5, matplotlib) comes from the wasmtime patch version, not
  Rust against Python. A Rust core is 376 lines here, an 8.7 to 13.9 MB binary, about 190 crates,
  all permissive. It also found that wasmtime-py 49.0.0 embeds wasmtime 49.0.0 (only the CLI is
  49.0.3). The memo leaves the verdict as it was: adopt in part, after 0.1.0. The rest of the
  question stays yours.
- **Meanwhile:** nothing else changes.

### 95. Documentation commits between a release's dry run and its tag

- **Asked:** 2026-10-18. **Source:** the 0.1.0a5 cut; AGENTS.md rule 6b ("dispatch the release
  workflow on main's exact commit").
- **The fact:** the dry run that passed every job (run 39143362471, the emulated x86_64 rebuild
  and `same-bytes` included) ran on `8f1ba40`. Seven commits followed it before the tag, all
  under `context/` and `CHANGELOG.md` (EXECUTED: `git diff --name-only 8f1ba40 d8afce3` names no
  file under `src/`, `tests/`, `scripts/`, `recipes/`, `.github/`, `downloads/`, `pyproject.toml`
  or `uv.lock`). The judge's rules checks read `context/`, so the agent ran the fast tier on
  `d8afce3` (exit 0, `rules 25/25`, ratchet lost 0) and tagged `0463d02` ("Release 0.1.0a5",
  which dates the CHANGELOG) without a second dry run. A second one would have cost about two
  hours, most of it the emulated rebuild. The a5 security addendum already reads the same way
  ("a5 may be released from 8f1ba40 (09ceb18 docs only)").
- **The question:** is that the rule? The agent's reading is: commits that touch only
  `context/`, `CHANGELOG.md` and `README.md` may follow the dry run if the fast tier passes on
  the commit to be tagged; any other file means a new dry run.
- **The agent's recommendation:** yes, and write that sentence into rule 6b. After spec 059 a dry
  run takes about 22 minutes, so the exception matters less from 0.1.0a6 on.
- **Meanwhile:** 0.1.0a5 was tagged this way. A different answer changes the next release only.

### 92. Bounded sessions: three choices where your decisions are silent, and one placement

- **Asked:** 2026-10-18. **Source:** `specifications/055-bounded-sessions.md` (Decisions 3, 4,
  8, 11 and 22) and its pre-build review (`reviews/055-bounded-sessions-spec-2026-10-18.md`,
  F2); `research/2026-10-18-bounded-sessions.md`. Nothing waits on it: spec 055 decides each
  as written below, so its confirmation and its build go ahead. An answer that differs changes
  one decision and its checks before 055 is built, or in a follow-up after.
- **The facts.** Your decisions 18 to 22 set the export, the scope, the bounds (15 minutes idle,
  1 hour), "a trap ends the session" and the README's files pattern. Three behaviours they do
  not cover had to be chosen:
  1. **`sys.exit()` in a turn keeps the session** (Decision 4). The turn reports the exit status,
     as `run` would, and the next turn still has every variable. Model code ends scripts with
     `sys.exit(main())` by habit; Jupyter keeps its kernel the same way. `os._exit()` still ends
     the session, because it unwinds the guest like a trap. The first research memo had leaned
     the other way ("a trap or an exit ends the session").
  2. **Closing is a stop, not a shutdown** (Decision 8). No guest code runs at close or expiry:
     no `atexit` handlers, no flush of files a program left open. What a turn wrote to its
     folders or mounts is already delivered at the end of that turn.
  3. **A turn's last expression is echoed** (Decision 3), as in a notebook: `df.head()` as the
     last line prints the frame. It costs about 0.58 M instructions for a four-line turn, under
     1% of a fresh run.

  The one-hour lifetime is not among them: a turn's deadline is capped at the lifetime left, so
  no guest code runs past the hour (Decision 9; the landing lane's ruling on the review's F4).
- **The placement.** A guest can open every host file descriptor the process has (the review
  measured 122,870 on macOS, after which the host's own `open()` failed). For `run` that lasts
  one call; a session holds them until it ends, up to its idle bound or the hour. No limit on
  descriptors exists today, for `run` or sessions. Spec 055 documents it, advises a short
  `idle_s` for untrusted code, and records a cap per store as a later specification.
- **The questions:** (a) keep the three choices as decided, or change any? (b) Should the
  descriptor cap come before 0.1.0, or after?
- **The agent's recommendation:** (a) keep all three: each follows the interactive interpreters
  agents are trained on, and keeps the export's C small. (b) After 0.1.0, unless an embedder
  runs untrusted sessions in a shared process before then: the gap already exists for `run`,
  the README states it, and a cap is its own design (shadowing `path_open` per store).

### 93. May a read-only mount serve an import-path entry?

- **Asked:** 2026-10-18. **Source:** `specifications/054-read-only-code-on-the-import-path.md`
  (Decision 9) and its pre-build review, finding F1
  (`reviews/054-read-only-code-on-the-import-path-spec-2026-10-18.md`).
- **The facts:**
  - Decision 16 approved read-only code on the import path "as an explicit read-only typed
    grant". Spec 032 left mounts out on purpose ("stays a typed grant … A mount … may import; it
    is not claimed").
  - A read-only mount can serve imports today, mechanically: with an in-memory provider at `/m`
    on the import path, `import json` made 0 provider calls and a module and a package in the
    mount made 14 `stat`, 1 `list` and 4 `read` calls (EXECUTED, the 054 memo §7, both binaries).
  - **The hazard (F1, EXECUTED by the reviewer, both binaries):** one provider object mounted
    read-only at `/lib` and writable at `/work`. Call 1 writes `/work/lib/evil.py`. Call 2, with
    the same layout and `/lib/lib` on the import path, runs `import evil`: "planted code ran".
    Every rule 054 has for grants allows that layout, because a mount has no host identity.
  - Within one call the runner can see the plainest form of it: the same provider object given
    twice, once writable. It cannot see two different objects backed by one store, nor a store
    written in another call or by another route. For grants, the cross-call case is already
    documented as the embedder's (054, Decision 5).
- **The question:** may a read-only mount serve an import-path entry? If yes, is the refusal of
  a read-only mount whose provider object is also mounted writable in the same call enough, with
  the README making every other route (other objects, other calls) the embedder's
  responsibility, as for grants across calls? Or should the runner refuse something across calls
  too (it keeps no state between calls today)?
- **The agent's recommendation:** yes, in a small follow-up specification after 054 lands: a
  read-only mount may serve an entry; a mount whose provider `is` the provider of a writable
  mount in the same call is refused; the README states the cross-call rule in the same words as
  for grants. The agent runtime's files often live in a store (decision 13), and copying a
  library to a folder first is the only route until then. No cross-call refusal: the runner
  keeps no state between calls, and adding some is a larger change than this one.
- **Meanwhile:** refused. Spec 054 serves import-path entries from read-only grants only; a
  mount serving an entry is a `ValueError`. Nothing waits on this answer.
### 90. The tool protocol's `batch`: in 0.1.0, or after?

- **Asked:** 2026-10-18. **Source:** `specifications/053-async-host-functions.md`, Decision 11;
  `research/2026-10-18-async-host-functions.md`, "Not studied". Nothing in spec 053 waits on it.
- **The fact:** spec 031's Decision 11 planned "async tools and gates, and the guest's `batch`
  operation" for decision 15's specification. Spec 053 carries async tools and gates and leaves
  `batch` out. `batch` would let one guest frame carry several tool calls, answered together,
  so a guest (which has no threads, and blocks on each door call) gets concurrency: five API
  calls at once instead of one after another. It helps sync tools on their threads as much as
  async ones. It changes the guest package and so the zip: build-class, one slot at a time
  (§5.7), behind 0.1.0's long build-class queue (the roadmap). Protocol 1 already reserves the
  name, and an unknown operation is a clean `protocol` answer (spec 031, Decision 7), so adding
  it in a later minor release breaks no guest and no embedder.
- **The question:** should `batch` be specified for 0.1.0 (after spec 053, as its own
  build-class specification), or after 0.1.0?
- **The agent's recommendation:** after 0.1.0. Decision 49 named the features 0.1.0 carries,
  and `batch` is not among them; it can be added without breaking anyone; and 0.1.0's
  build-class slot is spoken for by the scipy line and tier B.
- **Meanwhile:** spec 053 is drafted without `batch`; a guest calls tools one at a time.

## The owner's direction for the product (2026-10-17)

"I am thinking of this more as a safe runtime for agent code. The use case is much more
powerful web agents that can access code and interact with their data and tools (either through
a file system, tools in the host program, api calls, mcp, etc.) its main use case is to work with
~/Git/repos/vfs and run on top of that where vfs manages the permissions and governance."

The code stays embedder-neutral (§4.5). The capabilities that agent use needs are built as
general features; `research/2026-10-17-the-runtime-for-agent-code.md` studies which. State
across turns is researched before any specification (`research/2026-10-17-state-across-agent-turns.md`).
