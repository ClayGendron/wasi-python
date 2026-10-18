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

### 43 to 48. What else the default profile carries

- **Asked:** 2026-10-17. **Source:** `research/2026-10-17-what-else-the-default-profile-carries.md`
  ("Questions for the owner"; tiers A to D). Waits on them: `roadmap.md`'s "others" row and the
  specifications the memo orders. Meanwhile the agent lands specs 027, 029 and 028.
- **43.** Tier A (about thirty pure-Python packages) and tier B (scikit-learn, statsmodels, lxml,
  regex) as listed, with their licences? Two families are new: tqdm (MPL-2.0 AND MIT) and regex
  (CNRI-Python). The memo recommends yes.
- **44.** A plain start grows from about 242 M to about 620 M fuel with matplotlib, scipy, A and B
  (snapshot calls do not pay it). Accept, or first build "the zip's directory is read once"? The
  memo recommends cutting the per-member cost before the zip triples.
- **45.** sympy (and mpmath): 936 members, 9.3 MB, +73 M fuel on a plain start; on every hosted
  list, rare in benchmarks. In the default profile?
- **46.** openpyxl writes only with a writable `/tmp`; xlsxwriter writes in memory. Document the
  limit and keep nothing writable by default? The memo recommends yes.
- **47.** Leave pytz out (`zoneinfo` works; one `pytz.timezone()` costs 155 G fuel from the zip)?
  The memo recommends yes.
- **48.** scikit-learn, statsmodels and lxml in 0.1.0 (after scipy), or the release after?

## The owner's direction for the product (2026-10-17)

"I am thinking of this more as a safe runtime for agent code. The use case is much more
powerful web agents that can access code and interact with their data and tools (either through
a file system, tools in the host program, api calls, mcp, etc.) its main use case is to work with
~/Git/repos/vfs and run on top of that where vfs manages the permissions and governance."

The code stays embedder-neutral (§4.5). The capabilities that agent use needs are built as
general features; `research/2026-10-17-the-runtime-for-agent-code.md` studies which. State
across turns is researched before any specification (`research/2026-10-17-state-across-agent-turns.md`).
