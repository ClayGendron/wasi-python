# Questions for the owner

Questions the agent could not answer alone, written down so the work could go on (the owner's
instruction of 2026-10-16: "If you do have questions, please write them down in the repo and
continue working"). Each says what waits on it and what the agent did meanwhile. An answered
question moves to the bottom with the answer and the date.

## Open

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

### 3. A new hard constraint, "safe by default"

- **Asked:** 2026-10-16. **Source:** the principal engineer's memo.
- **The change:** a new §4 rule: every limit has a default; no channel to the host opens
  without an explicit argument; the runtime's files are never in a writable grant.
- **Meanwhile:** the agent gives `run()` safe defaults anyway (your direction: "no way (unless
  explicitly provided) to access the host file system or network"); the rule would make them
  binding on every later change.

### 4. Order of post-v1 work: sqlite3, bz2, lzma before matplotlib?

- **Asked:** 2026-10-16. **Source:** the principal engineer's memo, direction 8.
- **The question:** your order is matplotlib, then sqlite3/bz2/lzma, then scipy. matplotlib now
  waits on questions 1 and 2; sqlite3, bz2 and lzma need no C++ and no data folder. The agent
  works on them while matplotlib waits, and keeps your order for anything not blocked.

### 5. Security rules for releases

- **Asked:** 2026-10-16. **Source:** the principal engineer's memo, direction 7.
- **The change:** §5.5 gains "a security fix in a pinned component is a reason to release";
  §5.6 gains "a security review against the written threat model before each release".
- **Meanwhile:** the agent adds `SECURITY.md` and build-provenance attestations to the release
  workflow, which change no rule.

### 6. May the agent publish 0.1.0a2?

- **Asked:** 2026-10-16.
- **The question:** you authorised 0.1.0a1. Spec 005 names the 3.15 line's release `0.1.0a2`.
  The agent will prepare it (version bump, changelog, a green dry run of the release workflow)
  but will not push the tag until you say so (constitution §7).

### 7. A `wasi-python run` command line?

- **Asked:** 2026-10-16. **Source:** the principal engineer's memo.
- **The question:** §3 says the project "ships no shell". Is a thin command that runs a program
  and prints a JSON result part of the runner (allowed) or a shell (not)? The agent reads it as
  the runner but does not build it until you answer.

### 8. numpy's `.npy` files

- **Asked:** 2026-10-16. **Source:** `research/2026-10-16-what-data-folders-the-packages-need.md`.
- **The fact:** `np.save` and `np.load` of `.npy` files fail in 0.1.0a1 because numpy calls
  `os.dup`, which WASI preview1 does not have. Zero patches rules out a local fix.
- **The question:** may the agent file an upstream numpy issue (an outward-facing action)? The
  agent writes the issue text into the repository and records the failure as a known gap.

## Answered

(None yet.)
