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

### 49. Which agent-runtime features are in 0.1.0?

- **Asked:** 2026-10-17 (overnight; the owner asked the agent to keep working to 0.1.0 and write
  questions down). **Source:** `roadmap.md`, "Agent runtime features (placement in 0.1.0 to be
  decided)".
- Decided as features, not yet placed: the cancel fix (spec 030, a defect), the tool protocol
  (spec 031), async host functions, read-only code on the import path, the filesystem provider
  (spec 032), bounded sessions.
- **The agent's recommendation:** in 0.1.0: the cancel fix, the tool protocol and the
  filesystem provider (the first two are what an agent's code calls most; the provider lets
  vfs run on this runner). After 0.1.0: async host functions (unless the tool spec needs
  them), read-only code on the import path, bounded sessions.
- **Meanwhile:** the agent specifies and builds 030, 031 and 032 as 0.1.0 work, and leaves the
  rest unspecified. Answering otherwise moves them out; nothing built is lost.

### 50 to 53. The tool protocol's defaults (spec 031)

- **Asked:** 2026-10-17 (overnight). **Source:** spec 031, Decisions 6, 8 and 9. Each is
  decided in the spec as written below, so nothing waits; the owner may change any of them before
  or after it is built.
- **50. A schema keyword the runner does not check** (the tool memo's question 3): refused
  unless the tool says `validates_input=True`, reading decision 39's "validated first" strictly.
  The alternative checks the subset and skips the rest silently.
- **51. The discovery frame counts toward `max_tool_calls`,** so `max_tool_calls=4` allows three
  tool calls. The alternative counts only `call` frames.
- **52. At the limit the guest gets `ToolBudgetExceeded` and runs on,** so its code can handle
  it. Decision 42 stops the run at the filesystem provider's limit instead; the two could be made
  the same.
- **53. No per-call default timeout beyond the run's deadline.** The memo proposed 30 s per
  call. With `deadline_s=None` a hung tool holds the run until `cancel`, which is the embedder's
  explicit choice of no limit.

### 54 to 56. The filesystem provider's choices (spec 032)

- **Asked:** 2026-10-17 (overnight). **Source:** spec 032, Decisions 3 and 8. Each is decided
  in the spec as written below, so nothing waits.
- **54. Answers or exceptions.** The provider memo proposed that a provider raise `OSError`.
  Spec 032 has it return an `Errno` and treats any exception as a fault (the guest gets `EIO`),
  following vfs's "a denial is a result" (decision 37). Keep it, or also accept a raised
  `OSError` as its errno?
- **55. The staging bound.** Bytes a provider stages are bounded by the call's `memory_bytes`,
  with no knob of their own. Keep it, or add `max_staged_bytes`?
- **56. Names.** `max_file_calls`, `Defaults.file_calls` and `trapped == "out of file calls"`
  (after `"out of fuel"`), beside the tool protocol's `max_tool_calls`.

## The owner's direction for the product (2026-10-17)

"I am thinking of this more as a safe runtime for agent code. The use case is much more
powerful web agents that can access code and interact with their data and tools (either through
a file system, tools in the host program, api calls, mcp, etc.) its main use case is to work with
~/Git/repos/vfs and run on top of that where vfs manages the permissions and governance."

The code stays embedder-neutral (§4.5). The capabilities that agent use needs are built as
general features; `research/2026-10-17-the-runtime-for-agent-code.md` studies which. State
across turns is researched before any specification (`research/2026-10-17-state-across-agent-turns.md`).
