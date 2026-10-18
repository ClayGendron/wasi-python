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
- **The owner, 2026-10-18:** "make it true for all packages whatever the decision is … if
  we can leave them all as not pre imported then that makes the most sense … but if we must
  pre import some, we should import all." A Fable agent is measuring the uniform options
  (stdlib only, today's numpy and pandas, every package) for the owner's decision.

## The owner's direction for the product (2026-10-17)

"I am thinking of this more as a safe runtime for agent code. The use case is much more
powerful web agents that can access code and interact with their data and tools (either through
a file system, tools in the host program, api calls, mcp, etc.) its main use case is to work with
~/Git/repos/vfs and run on top of that where vfs manages the permissions and governance."

The code stays embedder-neutral (§4.5). The capabilities that agent use needs are built as
general features; `research/2026-10-17-the-runtime-for-agent-code.md` studies which. State
across turns is researched before any specification (`research/2026-10-17-state-across-agent-turns.md`).
