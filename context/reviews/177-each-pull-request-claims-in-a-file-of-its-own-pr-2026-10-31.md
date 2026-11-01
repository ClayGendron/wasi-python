# Review of 177 — Each pull request claims in a file of its own

- **Date:** 2026-10-31
- **Reviewer:** an agent (Claude), a fresh sub-agent of Claude Code session 0672b924-ca3c-4b6c-91ca-f834537cb1bc; not the author
- **Reviewed:** `7185f04c` on `bedf8f30` (#87, rebased from `9058d01f`; same code, plus #71's sixth block)
- **Run:** 41257413015 on `7185f04c`: `gather` and every Windows leg green; `ci-status` red only for this file's absence
- **Re-ran:** touched unit files and rules → 696 passed, 2 skipped; the new rules check over `dev`'s ledger → failed; base's and head's `news.py` and `sameness`, each over its tree; `ledger_refusals` and `ledger_move_refusal` against twelve hostile edits; fast tier on `7185f04c` with 166's set, read-only → 4,464 passed, 0 failed; `tests/lint` → 14 passed.
- **Box:** 45 minutes (a judge change); used about 50.

## Acceptance criteria against evidence

1. The blocks moved byte for byte; the single file is gone — met. EXECUTED: `bedf8f30`'s file from its first `[[claim]]` equals 166's first block, 165, 159, 167, 171 and 166's second (#71), cut from the five files in that order, `diff` empty; each file is named after its news file; `ledger_refusals` of `bedf8f30` against `7185f04c` is `[]`.
2. Every reader takes the folder in file-name order; `date` moves and removes each file — met. READ; EXECUTED: `ledger_move_refusal` admits `date`'s move of the real files and an added file, and refuses an edited, dropped or prepended-to one.
3. The same claims — met. The unit row rebuilds the old form, so I ran `bedf8f30`'s `news.py` against head's: at 0.1.2, 7 claims equal and all 96 probes quote alike; at 0.1.3, 6 equal, every verdict alike, 35 of 93 quote another block (finding 4). `sameness` alike.
4. `ci-status` refuses another's block added, edited or dropped, and the single file back — met for the plain header, not others (finding 1); a same-number rename admitted (finding 2).
5. The rules check refuses the single file and a misnamed file, seen failing first — met (EXECUTED above).
6. The documents say Decisions 1 to 5 — met (READ); the docs page names no specification.
7. Lint, fast tier, `ci-status` — met but for this file: `ci-status`'s one refusal is its absence. A fast-tier run I began on `9058d01f` was voided by the rebase in the worktree mid-run; its eight failures did not recur.

Structure (4a): not structural; nothing under `src/`; no function past 80 lines (`ledger_refusals` about 45); `ci_plan.py` 1,206 → 1,299 lines.

Code under `release/` (4b): `ci_plan.py` adds `ledger_refusals` for a pull request into `dev` that changes a ledger path (more refused, nothing less), and the preparation check reads the folder by `git`; no token. `version.py`'s `date` unlinks each moved file after every check passes.

## Findings, most severe first

1. **A claim block written in another TOML spelling escapes `ledger_refusals`** (`release/ci_plan.py` `claim_blocks`; `tests/harness/news.py` `ledger_file_claims`) — `claim_blocks` splits at a literal `[[claim]]` line and drops the text before the first one, while TOML also reads `[[ claim ]]`, `[["claim"]]` and an indented header as the same table. Failure: prepend `[[ claim ]]\nspec = "165"\ngrows = ["tests/checks/test_rules.py::*"]\ngrowth = "injected"` to `165-python-docx-and-python-pptx.toml` → `ledger_refusals` returns `[]`, `ledger_file_claims` reads two claims, and both rules checks pass (EXECUTED); a pull request has added a reason under another change's name, which Decision 4 says is refused. (Appending it after a block is caught, as an edit of that block.) Medium: a guarantee of a judge change not held. Fix: `ledger_file_claims` refuses a file whose `[[claim]]` tables do not number its lines matching `^\[\[claim\]\]$`, so each block begins with the literal header and nothing but comments comes before the first; a unit row with `[[ claim ]]` prepended, seen failing first, closes it.
2. **A rename within one number is admitted** (`ci_plan.ledger_refusals`; the rules check) — `165-python-docx-and-python-pptx.toml` renamed to `165-renamed.toml` is neither added nor dropped, and its name passes `LEDGER_NAME`. Failure: the file then names no news file, and file-name order, which picks the quoted reason, can move. No claim changes. Low: answer in writing, or refuse a path the base held that the head lacks, outside the pull request's own files, when its blocks reappear under another name.
3. **The folder's README is a verdict-bearing judge file** (`tests/harness/paths.py` `VERDICT_BEARING`, `JUDGE_PATHS`; `release/ci_plan.py` `HARNESS_DIRS`) — `context/release-claims/**` takes in `README.md`, so a wording fix to it alone needs a `[claim.judge]` reason and runs as a harness change, where `ci_plan` already treats `context/progress/README.md` as a document. Low: narrow the three to the folder's `.toml` files, or say in the specification that the README is judged with the folder.
4. **Which reason a row two blocks name is quoted with** (Decision 3, the author's open point) — see the ruling below. Low, answered: reserve the rule for its own specification.

### Ruling on the quoted reason

It is not a correctness bug. Every reason quoted, before and after, is a true reason for the row, written by a change that moved it: 165's growth says every guest's zip directory grew, and 166, 167 and 171 each grew every release group too. Neither append order nor file-name order picks "the" cause; four changes moved `numpy-slow-*`, and the verdict is the same in every probe. What changes is precision: 166's measured `numpy-slow-*` line is more useful than 165's blanket `::*`, and file-name order happens to get `sympy-*` more precise (159) and the numpy groups less (165).

The better rule is the most specific match: an exact name over a prefix, a longer prefix over a shorter, ties by file name. It is order-free, needs nothing git knows, and picks 166 for the numpy groups and 159 for `sympy-*`. "The block from the change that moved the row" is not knowable from the claims when several moved it, and merge order is what the folder gives up. Better still, the gather could show every matching reason. Either is its own judge change, since the news files share `news.reason`'s first-match rule (Scope: Out), and the only effect before then is the wording of 0.1.3's acceptance line. Not in this pull request; a roadmap line before 0.1.3's release acceptance would hold it.

## Constitution checks

- §4 constraints: no upstream patch, pin, artifact or `src/` file moves; uv only; no code file names a specification (`tests/lint` green); the judge changes with its reason under `[claim.judge]`, and no check, golden output, allowance or `context/progress/` file is edited to turn a run green.
- §7 never-do list: nothing tripped. The verdict-bearing list moves from the file to the folder with the claim the news file gives.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Header spellings — fixed in `f356bf93`: claims compared as `tomllib` reads them; any header but `[[claim]]` at column 0 refused. Confirmed.
2. Rename — fixed in `f356bf93`: renaming or removing another's file is refused. Confirmed.
3. README — answered in Decision 4: a `*.toml` pattern would match no file after `date`, which the verdict-bearing check forbids. Accepted.
4. Quoted reason — written under Scope, the most specific match reserved. Accepted.

## Round 2

- **Reviewed:** `7185f04c..f356bf93`, one fix commit.
- **Re-ran** (EXECUTED): touched unit files and rules → 703 passed, 2 skipped; `tests/lint` → 14 passed. `[[ claim ]]`, `[["claim"]]` and an indented header, prepended or appended to 165's file → refused by `ledger_refusals` and the rules check; a rename (same number, `.txt`, subfolder) or a removal → refused; the round-1 refusals hold; an own file with a plain header, and this pull request's move → admitted.
- **Read:** comments no longer count as a change; `header_errors` could refuse an array line beginning `[[`, which no claim's shape writes. Seen failing first is noted. Nothing structural.
- **Run:** on `f356bf93` not finished when signed; the merge waits on its `ci-status`.

## Verdict

Lands on f356bf93: the Medium and the rename Low are fixed and seen refused, the other Lows answered, and the release reads the claims the single file gave.
