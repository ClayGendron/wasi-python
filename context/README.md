# /context

The durable memory of this project: what we are building, why, and how
we build it, kept apart from the code. `constitution.md` sets the direction and the hard constraints;
every other document here obeys it. Code is a build artifact of this
context. When the two disagree, fix the code, unless the context is
demonstrably wrong, in which case fix the context first.

## The pipeline

We work **study → research → specify → build → review**. Each
directory is one stage; build is the code itself:

```
context/
  README.md            # this map
  constitution.md      # the mission, the goal, the hard constraints; everything else obeys it
  prior_art/           # STUDY — clones of the projects we learn from (git-ignored)
  research/            # RESEARCH — dated memos: executed experiments, study of precedent, placeholders for research still to do
  specifications/      # SPECIFY — numbered work packages to implement, retired on landing
  reviews/             # REVIEW — one record per review of a built change (or of a spec before build)
  progress/            # the harness's accepted state: accepted.json and an append-only history in volumes
  embedders.txt        # names no code may use (constitution §4.5); data the harness reads
  decisions.md         # the owner's decisions, newest first
  handoff.md           # the lane's state between sessions, replaced at each session's end
```

Progress is measured, not reported: `uv run pytest` prints the v1
scoreboard and compares it with `progress/accepted.json` (spec 002;
`progress/README.md` says how to read it).

Decisions are recorded in the specification that carries them, in a
**Decisions** section at its head, and in `research/` when they rest on
an experiment.

**There is no list of open questions.** A specification is written
without them: every choice it needs is made in it, with the reason.
Something we do not yet know enough to decide gets a research memo
marked *placeholder* that names the question, what would answer it and
what it blocks; the memo is filled in when the research is done, and
the specification that needs it waits until then.

A decision only the owner can make is asked through the owner's
channel and recorded, once answered, in `decisions.md`.

## Lifecycle rules

- **`prior_art/`** is a working set of other people's repositories,
  cloned shallow inside the repo and ignored by git. We study them:
  read, grep, cite, describe. **We never copy code from them.** Prior
  art is design input for our own original implementation. Check the
  licence of every clone right after cloning and record it in
  `prior_art/README.md`; a project with no licence is deleted and
  studied through its public docs instead. Refresh a clone to its
  upstream default branch before studying it, and record the commit
  in the memo that cites it. Building a dependency from its own
  released source is not copying; a patch we write for it is ours and
  lives in `recipes/`.
- **`research/`** is append-mostly, date-prefixed
  (`YYYY-MM-DD-slug.md`), never edited after the fact; supersede with
  a newer memo. A research memo is produced by actually gathering new
  findings: executed builds, measured runs, studied sources. Label
  every claim EXECUTED, READ or INFERRED. Count operations; report
  wall-clock as a benchmark fact, never as a test assertion. A memo
  commits us to nothing. A **placeholder** memo (status line says so)
  is the one exception to "never edited": it holds a question, the
  experiment that answers it and what it blocks, and is completed in
  place when the work is done. Evidence folders (a memo's outputs and
  logs) from before 2026-10-23 are in git history at `bb2235f2`; only
  `2026-10-18-wasmtime-49-advisories/`, which the judge reads, stays.
- **`specifications/`** are numbered (`NNN-slug.md`), born from
  research, small enough for one developer, and **retired on
  landing**. Each has a header (status, date, owner, kind, depends on,
  research it stands on), an intent paragraph, the design, scope in
  and out, counted acceptance criteria, and landing notes filled in
  when it lands. A landed spec is a historical record; its durable
  residue flows backward into `research/` and this README.
  A specification that changes anything `tests/public_api.txt` records
  says so in its Kind line ("changes the public API"), lists the
  snapshot lines it changes and the rule of spec 049, Decision 8, that
  allows each, and regenerates the snapshot and the README's reference
  with `tests/harness/api.py --write`.

- **`reviews/`** holds one record per review, named
  `NNN-<spec slug>-YYYY-MM-DD.md` after the specification it reviews.
  A review is done by someone who did not write the change, given the
  specification and the diff rather than the author's account. It
  records: what was re-run and the counts seen; each acceptance
  criterion with its evidence or its gap; findings ranked by
  severity, each with a failure scenario; constitution checks (§4
  and §7); and, after the author answers, the disposition of every
  finding (fixed, or not fixed and why). A landing cites its review
  in the specification's landing notes. A specification that
  changes the guest's imports or exports, the artifact set or the
  build recipe gets a review of the specification itself before it
  is built, recorded the same way. `reviews/README.md` holds the
  template.

## Conventions

- Plain Markdown, no proprietary formats.
- Each document opens with a frontmatter-free header: title, status,
  date, owner.
- Cross-reference with relative links; small, focused documents.
- Short sentences, one idea each, terms of art defined on first use.
