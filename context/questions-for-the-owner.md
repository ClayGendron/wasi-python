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

### 41–42. The filesystem provider

- **Asked:** 2026-10-17. **Source:** `research/2026-10-17-a-filesystem-provider-for-the-runner.md`
  (the guest's 26 file calls shadowed on a second linker used only when mounts are given; a
  provider serves `stat`, `list`, `read`, and on a writable mount `write`, `mkdir`, `remove`,
  `rmdir`, `rename`; `Mount(provider, "/work", writable=False)`; EXECUTED on both binaries).
- **41. May a provider be mounted at `/`?** It would let an embedder like vfs be the guest's
  whole filesystem; the zip stays at `/usr/local/lib` either way.
- **42. The provider-call limit:** the memo suggests a default of 10,000 calls per run, after
  which the run stops (vfs's own `VERB_CALL_BUDGET` is 10,000).

## The owner's direction for the product (2026-10-17)

"I am thinking of this more as a safe runtime for agent code. The use case is much more
powerful web agents that can access code and interact with their data and tools (either through
a file system, tools in the host program, api calls, mcp, etc.) its main use case is to work with
~/Git/repos/vfs and run on top of that where vfs manages the permissions and governance."

The code stays embedder-neutral (§4.5). The capabilities that agent use needs are built as
general features; `research/2026-10-17-the-runtime-for-agent-code.md` studies which. State
across turns is researched before any specification (`research/2026-10-17-state-across-agent-turns.md`).
