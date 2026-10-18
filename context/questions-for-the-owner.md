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

## The owner's direction for the product (2026-10-17)

"I am thinking of this more as a safe runtime for agent code. The use case is much more
powerful web agents that can access code and interact with their data and tools (either through
a file system, tools in the host program, api calls, mcp, etc.) its main use case is to work with
~/Git/repos/vfs and run on top of that where vfs manages the permissions and governance."

The code stays embedder-neutral (§4.5). The capabilities that agent use needs are built as
general features; `research/2026-10-17-the-runtime-for-agent-code.md` studies which. State
across turns is researched before any specification (`research/2026-10-17-state-across-agent-turns.md`).
