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

### 37–40. The tool protocol

- **Asked:** 2026-10-17. **Source:** `research/2026-10-17-a-tool-protocol-over-the-door.md`
  (LangChain, Monty, MCP, Cloudflare's code mode and others studied; a prototype ran through
  today's door with no change to the runner or the binary).
- **37. Is `gate=` required whenever `tools=` is given?** The gate sees every call after the
  runner validates it and before the tool runs. *Recommended: yes;* an embedder that wants no
  policy passes `gate=allow_all` and says so in its code (§4.15).
- **38. The guest module's name: `tools`, shipped in the stdlib zip?** Agent code would write
  `import tools; tools.lookup_region("EMEA")`. *Recommended: yes;* it is short and what agent
  code expects, and it does nothing unless the embedder passed tools.
- **39. Refuse a tool whose schema the runner can only partly check,** unless the embedder marks
  that the tool validates its own arguments? *Recommended: yes* (never trust the guest).
- **40. The LangChain and MCP adapters: in the wheel, or as README recipes?** *Recommended: in
  the wheel as small optional modules that import their library lazily,* so no dependency is
  added.

## The owner's direction for the product (2026-10-17)

"I am thinking of this more as a safe runtime for agent code. The use case is much more
powerful web agents that can access code and interact with their data and tools (either through
a file system, tools in the host program, api calls, mcp, etc.) its main use case is to work with
~/Git/repos/vfs and run on top of that where vfs manages the permissions and governance."

The code stays embedder-neutral (§4.5). The capabilities that agent use needs are built as
general features; `research/2026-10-17-the-runtime-for-agent-code.md` studies which. State
across turns is researched before any specification (`research/2026-10-17-state-across-agent-turns.md`).
