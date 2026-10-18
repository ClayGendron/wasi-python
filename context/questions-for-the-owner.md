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

### 91. Build the next build-class specification stacked on the one in review?

- **Asked:** 2026-10-18. **Source:** the owner's question that day, "Is there a way to speed up
  the verification part of this process", and the agent's answer in that session.
- **The fact:** about ten build-class specifications stand between main and 0.1.0 (the roadmap's
  queue: 023, 046, 047, 037, 038, 043, 039, 041, 042, 044, 045, 055). Constitution §5.7 lets only
  one change to the build recipe be in flight, so each waits for the previous one's build,
  review, answers, confirmation and landing. A landing's machine time is small: a full build
  from pins about 5 min 15 s and the full judge about 9 to 10 min on darwin-arm64 (EXECUTED,
  this session's lane logs); the waits are the review round trips.
- **The question:** may the next build-class specification be built on a branch made from the
  current one's reviewed branch, while that one is in review, and landed strictly after it?
- **What it costs:** if the lower specification changes after its review, the stacked one
  rebases, rebuilds and re-measures its numbers, and its review covers that delta (as spec 050
  did after 051). Still one landing at a time; the lane's rules do not change.
- **The agent's recommendation:** yes, at most two deep (one in review, one building on it),
  written into §5.7 and AGENTS.md rule 2. It is the one change that shortens the road to 0.1.0
  noticeably (INFERRED).
- **Meanwhile:** the queue stays serial, as §5.7 says.
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
### 91. Four choices in bounded sessions where your decisions are silent

- **Asked:** 2026-10-18. **Source:** `specifications/055-bounded-sessions.md` (Decisions 3, 4,
  8 and 9); `research/2026-10-18-bounded-sessions.md`. Nothing waits on it: spec 055 decides
  each as written below, so its pre-build review and its build go ahead. An answer that differs
  changes one decision and its checks before 055 is built, or in a follow-up after.
- **The facts.** Your decisions 18 to 22 set the export, the scope, the bounds (15 minutes idle,
  1 hour), "a trap ends the session" and the README's files pattern. Four behaviours they do not
  cover had to be chosen:
  1. **`sys.exit()` in a turn keeps the session** (Decision 4). The turn reports the exit status,
     as `run` would, and the next turn still has every variable. Model code ends scripts with
     `sys.exit(main())` by habit; Jupyter keeps its kernel the same way. `os._exit()` still ends
     the session, because it unwinds the guest like a trap. The first research memo had leaned
     the other way ("a trap or an exit ends the session").
  2. **Closing is a stop, not a shutdown** (Decision 8). No guest code runs at close or expiry:
     no `atexit` handlers, no flush of files a program left open. What a turn wrote to its
     folders or mounts is already delivered at the end of that turn.
  3. **A running turn is never cut by the lifetime** (Decision 9). A turn's own deadline bounds
     it. If the hour passes during a turn, the turn returns its result and the session ends
     then. So a session lives at most 1 hour plus one turn's deadline (60 s by default).
  4. **A turn's last expression is echoed** (Decision 3), as in a notebook: `df.head()` as the
     last line prints the frame. It costs about 0.58 M instructions for a four-line turn, under
     1% of a fresh run.
- **The question:** keep these four as decided, or change any?
- **The agent's recommendation:** keep all four. Each follows the interactive interpreters
  agents are trained on, keeps a turn's limits fixed when it starts, and keeps the export's C
  small (no finalize path).

## The owner's direction for the product (2026-10-17)

"I am thinking of this more as a safe runtime for agent code. The use case is much more
powerful web agents that can access code and interact with their data and tools (either through
a file system, tools in the host program, api calls, mcp, etc.) its main use case is to work with
~/Git/repos/vfs and run on top of that where vfs manages the permissions and governance."

The code stays embedder-neutral (§4.5). The capabilities that agent use needs are built as
general features; `research/2026-10-17-the-runtime-for-agent-code.md` studies which. State
across turns is researched before any specification (`research/2026-10-17-state-across-agent-turns.md`).
