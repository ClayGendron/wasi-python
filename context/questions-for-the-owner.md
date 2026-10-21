# Questions for the owner

Questions the agent could not answer alone, written down so the work could go on (the owner's
instruction of 2026-10-16: "If you do have questions, please write them down in the repo and
continue working"). Each says what waits on it and what the agent did meanwhile. An answered
question moves to another document (research, spec, review, etc.) and is deleted from this
document.

## Open

### 108. Amend §5.6: a structural change is reviewed before build, and a structural review of `src/` precedes each release

- **Asked:** 2026-10-20. **Source:** `specifications/108-a-structural-review-is-a-stage.md`,
  Decisions 1 and 2; `research/2026-10-20-a-design-review-of-the-runner.md`, section 5. Your ask
  of 2026-10-20: "this PR should include changes so that this refactor/review process is more a
  part of the normal workflow".
- **The fact:** §5.6 names three kinds of change that are reviewed before they are built, and
  one review before each release, the security review. The review stage has checked behaviour,
  not structure: 89 landed specifications and 187 reviews left `runner.py` at 6,241 lines with 60
  mutable module globals and 27 locks (the memo, section 2, READ). Specs 103 to 108 fix that
  once, and their rules checks hold the letter of the fix. Nothing in the constitution asks a
  reviewer to look at the structure again.
- **The question:** may §5.6 be amended with the two sentences below, and its Status line with
  the entry below? AGENTS.md's rule "Structure is reviewed, not only behaviour" (spec 108) binds
  agents from the wave that lands it, as rule 8's "the runner's code" did on 2026-10-19; the
  constitution is yours to change.
- **The amendment, §5.6.** After "so a wrong design is caught before it is code.": "A
  specification that is structural (AGENTS.md: it adds a module-level mutable or lock outside the
  process object's module, a use of the engine's private API outside the engine seam, a platform
  branch outside the platform module, a test seam not on the process object, or takes a module
  or a function past its ceiling) is reviewed before it is built in the same way, against the
  structural rubric in `reviews/README.md` (owner, 2026-10-20, question 108)." After the last
  sentence, on the security review: "Before each release a fresh reviewer also writes a
  structural review of `src/` against that rubric, recorded under `reviews/` beside the security
  review; the release waits on its High findings (owner, 2026-10-20, question 108)."
- **The Status line entry:** "Amended 2026-10-20 by the owner's answer to question 108: a
  structural change is reviewed before it is built, and a structural review of `src/` precedes
  each release beside the security review (§5.6)."
- **The agent's recommendation:** yes, as written. The cost is one 45-minute review per release
  and one "Structure" section per structural specification; the alternative is the file the memo
  describes, grown again.
- **Meanwhile:** AGENTS.md carries the rule and the judge holds it
  (`test_a_release_has_its_structural_review`,
  `test_built_structural_specifications_cite_their_pre_build_review`). A "no" removes the release
  half (the rule's last sentence and the first check) in one context-and-judge commit by the lane,
  recorded in `decisions.md`; the rubric stays as guidance and the pre-build half stays, since
  AGENTS.md rule 8 already requires a pre-build review of the runner's code.

## The owner's direction for the product (2026-10-17)

"I am thinking of this more as a safe runtime for agent code. The use case is much more
powerful web agents that can access code and interact with their data and tools (either through
a file system, tools in the host program, api calls, mcp, etc.) its main use case is to work with
~/Git/repos/vfs and run on top of that where vfs manages the permissions and governance."

The code stays embedder-neutral (§4.5). The capabilities that agent use needs are built as
general features; `research/2026-10-17-the-runtime-for-agent-code.md` studies which. State
across turns is researched before any specification (`research/2026-10-17-state-across-agent-turns.md`).
