# How the large autonomous ports were run, and what this project takes from them

- **Status:** executed (a study of precedent), 2026-10-16
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5), in one session, box: half a day.
- **Feeds:** `../specifications/002-the-progress-harness.md`; the
  "Working autonomously" section of `../../AGENTS.md`.
- **Evidence labels:** READ (a source was read; cited below), INFERRED
  (this memo's reasoning from what was read), EXECUTED (run here).

## Why this study

The owner asked that wasi_python be developed by an agent working on
its own. Three projects have done that at scale in 2026. Each one
published how it worked. The question: what made them converge, what
made them stall, and what does that change here?

A **harness** here means the code that judges the work: the tests,
the scoreboard of what passes, and the rules for when a change may
land. A **ratchet** is a record of what passed before, used so that
nothing that passed may quietly stop passing.

## The precedents

### 1. Bun: 535,000 lines of Zig ported to Rust (May 2026)

READ (InfoQ; Pragmatic Engineer; PR #30412):

- Jarred Sumner spent about three hours writing `PORTING.md` first.
  It mapped every recurring Zig pattern to its Rust form. A second
  artifact, `LIFETIMES.tsv`, classified the lifetime of every struct
  field, with two adversarial reviewers voting on each choice.
- About fifty Claude Code workflows ran over roughly eleven days, at
  peak four worktrees of sixteen agents each. The workflows are
  checked in as `.claude/workflows/phase-*.workflow.js`: port, fill,
  fix-bugs, test-bringup, test-swarm, audits.
- Each unit had one implementer, two adversarial reviewers in fresh
  contexts that saw only the diff, and a fixer. "The implementer
  doesn't review. The reviewer doesn't implement."
- The arbiter was Bun's existing test suite. It is written in
  TypeScript, so it does not depend on the language being ported.
  `scripts/test-scoreboard.sh` ran every test file and the swarms
  reported `passing` against `total`.
- When the agents went wrong, the team changed the workflow, not the
  output. Agents running `git stash`, `stash pop` and `reset --hard`
  in one tree destroyed each other's work; the fix was a rule (commit
  single files; no stash, no reset) and sharding.
- What the suite missed: nineteen subtle semantic regressions that
  came from Zig and Rust looking alike. Security review and fuzzing
  after the merge found them, not the tests.
- Cost, as reported: about $165,000 of tokens. Line and commit counts
  differ between sources (535k vs 960k lines; 6,502 vs 6,755
  commits); this memo does not reconcile them.

### 2. ts-rust: the TypeScript compiler ported to Rust (June–October 2026)

READ (the repository's README, `AGENTS.md`,
`docs/typechecker-accountability.md`, `docs/history.md`; press):

- A first attempt with another vendor's models produced 1.3 million
  lines and stalled at about 84% compatibility, at a reported
  $400,000 of tokens. Its own history file says why: breadth.
  "Hundreds of commits across many compiler subsystems" landed
  **before the parity harness became authoritative**; a later audit
  found 70 failing tests.
- The recovery narrowed the claim to one measurable path: a
  five-file contract, `minimal-working-v0`, with an oracle gate, a
  runtime gate and a benchmark gate. That goal completed.
- The Claude attempt restarted from scratch, had a working v0 in ten
  hours, and reported all 184,773 ported Go tests passing in about
  two weeks, at about $24,000. The oracle is the Go compiler at a
  pinned upstream commit (`UPSTREAM.md`).
- The accountability rules are the most precise in the set:
  - A **protected set**: every test name, every gate item, every
    oracle battery. A candidate is compared with the last accepted
    revision **by name**: retained, recovered, lost, absent, unrun.
    "New passes do not offset lost ones." Lost, absent or unrun is a
    STOP.
  - **Allowances** for known failures must name the exact case, and
    resource caps (editor memory growth per edit) "can only go down".
  - **The judge is protected.** "Do not change a runner, baseline,
    or expectation to bypass a STOP." The gate records the hash of
    every judging tool; changing one needs an explicit, reviewed
    entry.
  - **State lives in two files**: a small `current.json` and an
    append-only `history.jsonl`. "Do not edit or remove committed
    lines." Every measured revision is recorded before the next one,
    failed ones included.
  - Roles: one implementer, one independent reviewer, one regression
    auditor. Reviewers and auditors never edit code or expectations.
  - After two measured attempts without progress on one hypothesis,
    stop and reassess.

### 3. Anthropic's C compiler, built by sixteen parallel Claudes (February 2026)

READ (Nicholas Carlini, "Building a C compiler with a team of
parallel Claudes", Anthropic engineering blog):

- The loop was a bash `while true` that restarted Claude Code with a
  prompt file. Agents claimed tasks by writing lock files into
  `current_tasks/` and synchronized through git. No orchestrator.
- "The task verifier is nearly perfect" was the precondition: an
  agent will solve whatever problem the verifier poses, so a weak
  verifier gets the wrong problem solved. Tests were added each time
  a new failure mode was seen.
- GCC was the **oracle**. When the Linux kernel was one giant failing
  task, the harness compiled a random subset of files with GCC and
  the rest with the new compiler, so different agents could find
  different bugs.
- Written for the model, not for a person: print a few lines, log the
  rest to files, put `ERROR` and the reason on one line so `grep`
  finds it, precompute aggregate statistics.
- **Time blindness**: "Claude can't tell time" and will spend hours
  running tests. The harness had a `--fast` mode running a
  deterministic 1% or 10% sample.
- Fresh contexts need orientation: READMEs and progress files,
  updated often.
- Late in the project new features kept breaking old ones; a CI gate
  that refused regressions fixed it.
- The warning: "it is easy to see tests pass and assume the job is
  done."
- Cost: about 2,000 sessions, about $20,000.

### 4. Cursor's long-running agents (January 2026)

READ (secondary summaries; the original post could not be opened):
equal agents sharing a lock file slowed twenty agents to the
throughput of two or three; planners that do not code plus workers
that do not plan worked better; a judge agent ends each cycle;
periodic fresh starts were needed against drift and tunnel vision;
"the prompts matter more" than the harness.

## Lessons, each with what this repository does about it

| # | lesson | label | what this repo does |
|---|---|---|---|
| 1 | The verifier is built first and must be close to perfect; an agent solves the problem the verifier poses. | READ (C compiler, Bun, ts-rust) | The v1 goal (constitution §2) is written as checks before the work they judge: spec 002. |
| 2 | Judge with an oracle that does not share code with the thing judged. | READ (GCC; pinned Go; Bun's TypeScript suite) | Native CPython with the pinned numpy and pandas produces golden outputs. The harness drives the guest through its own minimal wasmtime driver, not through the runner it is judging. |
| 3 | Progress is counted by name against the last accepted state; new passes never offset a lost one. | READ (ts-rust) | `context/progress/accepted.json` records each check's last accepted state; a lost pass turns the run red. |
| 4 | Resources ratchet too, and a cap only moves down. | READ (ts-rust) | Guest cost is wasmtime **fuel** (an instruction count, deterministic: see the fuel memo) and artifact bytes; growth past a tolerance is red until accepted with a stated reason. This is constitution §3's "slower without a stated reason is a regression", made countable. |
| 5 | A known failure is an allowance that names its case and its fix. | READ (ts-rust) | `tests/known_gaps.toml`: each entry names one check and the document that will close it; a gap that starts passing fails the run until its entry is removed. |
| 6 | Nobody edits the judge to get a pass. | READ (ts-rust) | The scoreboard hashes the judging files; a changed judge is reported and must be accepted with a reason, and the review sees it. |
| 7 | State in a small current file plus an append-only history. | READ (ts-rust) | `accepted.json` plus `history.jsonl`; the history is never rewritten. |
| 8 | Output for the model: few lines, one-line errors, details in files. | READ (C compiler) | The scoreboard prints about twenty lines; every failure is one `FAIL <check> — <reason>` line; the full record is `build/progress/latest.json`. |
| 9 | Agents are time-blind; give them a fast tier. | READ (C compiler) | Checks that run a large guest job are marked `slow`; `-m "not slow"` is the fast tier. The constitution's time boxes stay. |
| 10 | Each blocked check says what it waits for, so the next task is obvious. | INFERRED from 1 and from Cursor's planners | Every skipped check names one prerequisite; the scoreboard's `next:` line names the one that unblocks the most checks. |
| 11 | The implementer does not review; reviewers see the diff and the spec, in a fresh context. | READ (Bun, ts-rust) | Already constitution §5.6. Added: the reviewer re-runs the scoreboard and reads the ratchet report, not the author's summary. |
| 12 | Breadth before an authoritative harness is how a port stalls; recover by narrowing to one measurable path. | READ (ts-rust history) | No build work before spec 002 lands. One specification at a time, each moving named checks from blocked to pass. Two failed attempts on one hypothesis: stop and write down why (ts-rust's rule, and the constitution's time boxes). |
| 13 | Fix the process, not the output; each new failure mode becomes a check. | READ (Bun, C compiler) | The spike's three silent failures (the `strtold` abort, the `numpy.random` signature clash, the 32-bit default integer) are guest checks from day one. |
| 14 | A passing suite does not prove semantics. | READ (Bun's nineteen regressions; ts-rust's 120 real repositories) | Several independent oracles: golden jobs, the spike's probes, and later numpy's and pandas' own test subsets, whose pass counts ratchet. |
| 15 | Parallel agents collide on shared git state; locks throttle them. | READ (Bun, Cursor, C compiler) | Not adopted now. One artifact is built in sequence and a swarm has nothing independent to share. Revisit when the upstream test subsets yield many independent failures. AGENTS.md already bans `stash` and `restore` on uncommitted work. |
| 16 | A planning artifact before any agent writes code. | READ (Bun's `PORTING.md`) | The constitution, the recipe table in the spike memo, and one specification per piece of work. |
| 17 | Verification quality, not token volume, decided the outcomes. | INFERRED (ts-rust's stalled attempt cost about seventeen times its successful one; both figures are the author's) | Spend on the harness first. |

## What this study does not show

- None of these projects is a cross-compiled interpreter. Their
  oracles were whole programs in the same domain. Ours is native
  CPython at the same pinned versions, which differs from the guest
  by documented platform facts (the 32-bit default integer, no
  threads). INFERRED: the differential checks must state those facts
  rather than paper over them.
- The cost figures are the authors' own or come from press coverage.
  None was checked here.
- Cursor's original post was not read; its row rests on summaries.

## Sources

- Anthropic engineering, "Building a C compiler with a team of
  parallel Claudes": <https://www.anthropic.com/engineering/building-c-compiler>
  (read 2026-10-16).
- oven-sh/bun PR #30412, "Rewrite Bun in Rust":
  <https://github.com/oven-sh/bun/pull/30412> (read 2026-10-16, first
  100,000 characters).
- InfoQ, "Bun Rewrites 535K Lines of Zig into Rust":
  <https://www.infoq.com/news/2026/09/bun-AI-rewrite-zig-rust-4-months/>.
- The Pragmatic Engineer, "What can we learn from Bun's rapid Rust
  rewrite with AI?":
  <https://newsletter.pragmaticengineer.com/p/the-pulse-what-can-we-learn-from-07f>.
- pingdotgg/ts-rust: <https://github.com/pingdotgg/ts-rust>, with
  `AGENTS.md`, `docs/typechecker-accountability.md`, `docs/history.md`
  on `main` (read 2026-10-16).
- The Register, "$24,000 AI experiment ports TypeScript compiler to
  Rust" (2026-10-15):
  <https://www.theregister.com/devops/2026/10/15/24000-ai-experiment-ports-typescript-compiler-to-rust/5303409>.
- Cursor, "Scaling long-running autonomous coding":
  <https://cursor.com/blog/scaling-agents> (through
  <https://simonwillison.net/b/9250> and other summaries).

## One line

The projects that converged built a near-perfect judge first,
counted progress by name against the last accepted state, and never
let a pass quietly disappear; this project does the same before it
builds anything else.
