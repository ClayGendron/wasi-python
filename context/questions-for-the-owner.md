# Questions for the owner

Questions the agent could not answer alone, written down so the work could go on (the owner's
instruction of 2026-10-16: "If you do have questions, please write them down in the repo and
continue working"). Each says what waits on it and what the agent did meanwhile. An answered
question moves to another document (research, spec, review, etc.) and is deleted from this
document.

## Open

### 13. Should vfs run guests through this runner, or through its own host?

- **Asked:** 2026-10-17. **Source:** `research/2026-10-17-the-runtime-for-agent-code.md` §6.
- vfs's spec 169b plans its own wasmtime-py host, one guest per process. The agent recommended
  this runner (it already runs concurrent calls safely; vfs keeps only its shim, and a
  filesystem provider moves up).
- **The owner, 2026-10-17:** "This will require further research later, so leave this as an open
  question for owner." Nothing waits on it: the tool protocol, sessions and the strict default
  are general features either way.

### 34. Pre-import matplotlib in the default snapshot?

- **Asked:** 2026-10-17. **Source:** `research/2026-10-17-matplotlib-on-the-current-line.md`.
- Pre-importing makes a plotting call 4.6 times cheaper (5.81 G to 1.25 G fuel) but costs every
  call +23.4 M fuel (+28% on `pass`), grows the snapshot 17.5 MB and each instance's starting
  memory 18 MiB.
- **The owner, 2026-10-17:** decide after matplotlib's first milestone (spec 023) is built,
  from the real set's measurements. The agent brings the numbers back then.

### 37. Does the tool protocol need a gate, or are the tools the authority?

- **Asked:** 2026-10-17. **Source:** `research/2026-10-17-a-tool-protocol-over-the-door.md`.
- **The owner, 2026-10-17:** "My thinking is that wasi_python would call the public api for
  something like read, and when it calls read VFS would inject its Authority into the read call,
  so wasi_python would not know anything about permissions" ... "I'd like to position wasi_python
  without a gate, or at least an optional one, I want to spend time on this design and think
  through it with you."
- **The agent's reading:** that is the capability model, as grants already are: holding a tool is
  the permission, and the tool (bound by the embedder to its authority) enforces it. A gate would
  then be optional, a hook for embedders whose tools do not carry their own policy. Being worked
  through with the owner, starting from a study of vfs's authority model.

## The owner's direction for the product (2026-10-17)

"I am thinking of this more as a safe runtime for agent code. The use case is much more
powerful web agents that can access code and interact with their data and tools (either through
a file system, tools in the host program, api calls, mcp, etc.) its main use case is to work with
~/Git/repos/vfs and run on top of that where vfs manages the permissions and governance."

The code stays embedder-neutral (§4.5). The capabilities that agent use needs are built as
general features; `research/2026-10-17-the-runtime-for-agent-code.md` studies which. State
across turns is researched before any specification (`research/2026-10-17-state-across-agent-turns.md`).
