# Review of 142 — The 80-line allowance is judged by length (pull request)

- **Date:** 2026-10-28
- **Reviewer:** an agent (Claude Opus 5.5), a fresh sub-agent of the orchestrating session; not the author
- **Reviewed:** pull request #37, `spec/142-the-80-line-allowance-is-judged-by-length`, `dev` at `0b67fe1b` to head `b0b75dde` (`4303db3c`, `b521fe1e`, `b0b75dde` and the specification's commits), with the specification, the 0.1.1 structural review's M-a and L6, the 0.1.0 structural review's M-a and M1(c), the news file, `tests/harness/paths.py`'s `VERDICT_BEARING`, `tests/harness/accept_from.py`'s claim reading, `context/changes/README.md`, the roadmap's 142 lines and the pull request's description (READ, `gh pr view 37`, once).
- **Run:** 40642434118, the pull request's run on `b0b75dde`, **still running when this review was written**: `plan` and `build the site strictly` passed; `quick` and the set's key pending; the Pages deploy and the rebuilds skipped (READ, `gh pr checks 37`, once). `ci-status`, the gather's summary and the Windows legs are not read yet; the orchestrator says when the run ends, and this line and the Verdict are then written again.
- **Re-ran:** (on the head, arm64 macOS, `uv run`; logs under the worktree's `build/142-review/`)
  - The scan with an empty allowance, the landing notes' command → seven lines: `_instance` 155, `_Process.__init__` 83, `_open_session` 138, `Session.run_async` 81, `run` 156, `run_async` 181, `Session.__init__` 178; equal, key by key, to `LONG_FUNCTIONS` on the head (EXECUTED).
  - The seven listed functions measured by the same `ast` count on `src/` at `ee72523e`, `86fab037`, `658a6213`, `2a13298b`, `0b67fe1b` and the head (`git show` of each file) → no move through 145; at 146 `_open_session` 136 to 138 and `_Process.__init__` 81 to 82; at 144 `_Process.__init__` 82 to 83 and `Session.run_async` 82 to 81; the head equal to `0b67fe1b` (EXECUTED). The `_process.py` diffs: 146 adds `self.tool_threads_abandoned`, 144 adds `self.pool_done` (EXECUTED, `git diff`).
  - `uv run pytest -q -p no:cacheprovider` on `test_scan.py::test_a_listed_function_past_its_length_is_a_hit`, `::test_a_listed_function_shorter_than_its_length_is_a_stale_allowance`, `::test_a_function_over_the_ceiling_is_a_hit`, `test_rules.py::test_no_function_is_over_eighty_lines` and `::test_the_news_files_have_their_shape` → 5 passed, exit 0 (EXECUTED, `probes.log`).
  - `git diff --stat origin/dev...HEAD -- src/` → empty (EXECUTED).
  - A walk of `src/` for a `<file>:<qualname>` key defined more than once → one, `tools.py:tool` (three overloads, each short, unlisted); no file name repeats under `src/` (EXECUTED).
  - `uv run pytest tests/lint -q -p no:cacheprovider` after this file (EXECUTED, below the box).
- **Time box:** 25 minutes (parallel-safe, a judge change), held; the wait for the run lies outside it.

Labels: EXECUTED means I ran it; READ means I read the file or log cited; INFERRED means my reasoning.

## The author's self-check

The pull request's description (READ): `Author:` names a builder sub-agent of the orchestrating session; `Specifications:` names 142; the new checks seen failing first, checked, with the two unit rows' `assert [] == [...]` outputs and the rules check's `6 finding(s), digest 3092c2796d92` with the old values; no gap added, checked; the news file present, checked. The Windows legs box is unchecked ("not yet read"), since the run had not ended (finding 2). The description states the one difference from the Design (the grown-function branch inside the walk), which the landing notes give with its reason.

## Acceptance criteria against evidence

1. The two new unit rows exist and were seen failing; the old row is unchanged and green — **met**: both rows are in `tests/unit/test_scan.py` beside `test_a_function_over_the_ceiling_is_a_hit`, use its `_function` helper, and pass with it (EXECUTED); the old row is not in the diff (READ); their red outputs on the base are in the description and the landing notes (READ, not re-run: on the base's scan both calls return `[]` because the base never reads a listed length, INFERRED from the base's code in the diff).
2. The rules check failed with six findings on the old values and passes with the reset — **met** for the pass (EXECUTED); the failure is READ from the description and landing notes, and agrees with the lengths I measured at `ee72523e` against the old listing: three past (156/151, 181/176, 178/173) and three short (136/150, 155/159, 81/82), six (EXECUTED, the per-merge walk).
3. `LONG_FUNCTIONS` holds the same seven keys at the head's lengths, with the command in the landing notes — **met**: same seven keys, each equal to the empty-allowance scan on the head (EXECUTED); the command and lengths are in the landing notes, labelled EXECUTED (READ).
4. No file under `src/` changes — **met** (EXECUTED).
5. The news file with its Changed line and claim block; the shape check passes — **met** (READ; EXECUTED, `test_the_news_files_have_their_shape`).
6. The pull request's run: `quick` with `lint` green, no accepted pass lost, `ci-status` green — **not yet evidenced**: run 40642434118 had not ended (READ). Locally the rules check, the scan rows and `tests/lint` pass (EXECUTED); `quick` runs `tests/checks/test_rules.py` on every push (`.github/workflows/release.yml:165`, READ), so the equality is judged on the head that merges.

The rule itself, against the code (`tests/harness/scan.py:2870-2907`, READ, and the rows, EXECUTED):

- **At its listed length, green.** The walk's second branch fires only on `n > allowed[key]`, and the closing loop only on `n <= 80` or `n < allowed[key]`; equality passes both (the first row's second assertion holds it).
- **Longer, a hit naming both numbers**, `file:line: qualname (n lines, listed m)`, in the walk's sorted part, so it reads as the unlisted form does with the bound added.
- **Shorter but past 80, a stale allowance naming both**, `stale allowance: key (n lines, listed m)`; at or under 80, and gone, unchanged from 108. A listed function at or under 80 is reported once, as stale, never also as grown, because the walk's branch requires `n > FUNCTION_CEILING` (READ).
- **Unlisted past 80, a hit, unchanged**, and an unlisted function is never compared with the dict (the `key not in allowed` branch comes first, so `allowed[key]` cannot raise) (READ).
- **The message says what to do.** `LONG_FUNCTIONS_FIX` is passed as `scan.report`'s `what`: shorten the function, or list the length it has, lower when it shrank, higher only with the claim (READ).
- **The check keeps its name**, `test_no_function_is_over_eighty_lines`, so no accepted check goes absent (READ, the diff).
- **The count** is unchanged, `end_lineno - lineno + 1`, docstrings in. Decision 2 settles the 0.1.0 review's M1(c) on the measure with its reason (a reader scrolls a docstring; a measure without them would drop `run`, `run_async` and `Session.run_async` from the list with no code changed), and leaves the shared argument list, M1(c)'s other half and the fold-in the 0.1.1 review's M-a suggested, to 115, as Scope says. I agree: changing the measure in the same change that makes it bind would hide the debt the reset is meant to show (INFERRED).
- **The list only shrinks unless a rise is claimed.** The lower bound being red makes each number exactly the tree's, so a rise is a one-number diff. `tests/checks/test_rules.py` is not verdict-bearing (`tests/harness/paths.py:296-304`, READ), and the accept job reads `[claim.judge]` for verdict-bearing files alone and passes on no other (`tests/harness/accept_from.py:286-295`, READ), so the accept job will not refuse a missing claim; Decision 5 puts that on the review. I find that acceptable: every judge change is seen by its review and recorded by the judge's hash, and making the file verdict-bearing would ask a claim of every lowered length too, against the rule's direction (INFERRED). But the checklist did not say so: its item 4's "a row changed and not claimed" speaks of the gather's `GROWTH` rows, which a listed length is not, and `context/changes/README.md:22` describes `[claim.judge]` as for verdict-bearing files. Finding 1, applied.

## The claim block against the diff

The diff raises four values and lowers three (READ). The `[claim.judge]` reason names all four rises with a cause and the three falls with their numbers (READ). The causes hold:

- `run`, `run_async`, `Session.__init__` +5 each: already 156, 181 and 178 at `ee72523e` and unmoved since (EXECUTED); the cause, the `env` and `cache_dir` sentences and the `_cache_given` line in each of the three copies of the argument list, is the 0.1.1 review's (READ there, from `git diff 855c7530`).
- `_Process.__init__` 82 to 83, **higher than the draft's table**, which lowered it to 81: explained. 146 added `tool_threads_abandoned` (81 to 82) and 144 added `pool_done` (82 to 83) (EXECUTED), so only 144's merge took it past its old listing, as the claim, the landing notes and the Changelog line say. Neither 146 nor 144 needed a claim, since nothing judged a length then (INFERRED).
- `Session.run_async` 82 to 81 (144), `_open_session` 150 to 138 (136 before 146's two arguments), `_instance` 159 to 155: lowered, unclaimed as Decision 4 allows (EXECUTED, the lengths).

The Changelog line names the four that grew unseen, and its `(spec 142)` follows the form of the news files landed before it (READ, 144's and 146's). No `GROWTH` row is expected: no fuel, bytes or upstream counts move, and no check changes tier (INFERRED, the diff touches `tests/` judge code only); the gather will say.

## Structure

Judge only: no file under `src/` changes, so no row of the rubric moves (EXECUTED). The change gives row R7's measurement its teeth; it adds no concern, flag, mutable, seam, platform branch or private-API use. **Not structural**, as the Kind line says.

## Findings, most severe first

1. **Low L1: the reviewer's checklist did not say that a raised listed length must be claimed** (`context/reviews/README.md:27`; `context/changes/README.md:22`) — Decision 5 rests the claim on the review, but item 4 speaks of the gather's `GROWTH` rows and the changes README of verdict-bearing files only. Failure: a later change raises `_instance` to 160 with no `[claim.judge]` line; the accept job passes it, and a reviewer reading item 4 as written finds no row to call unclaimed. Fix, **applied** in `536bab78`, appended to item 4: "A raised length in the long-function allowance, `LONG_FUNCTIONS` in `tests/checks/test_rules.py`, is claimed under the news file's `[claim.judge]` with the reason the function grew, though that file is not verdict-bearing and the accept job does not ask for the claim: the review is what holds it, and a raise not claimed is Medium (`../specifications/142-the-80-line-allowance-is-judged-by-length.md`, Decision 5)." The changes README's comment line is left as is: it describes what the accept job reads, which stays true.
2. **Low L2: the Windows legs box is unchecked** (the pull request's description) — the run had not ended. Fix: once `ci-status` concludes, read the Windows legs of run 40642434118 (or of the head's run, if the branch is rebased), check the box and say what they showed.
3. **Low L3: a key defined twice keeps only its last length** (`tests/harness/scan.py:2891`, `lengths[key] = n`) — the walk compares each definition with the listing, but the stale check reads the last one. Failure: a listed key with two definitions (an overload pair, or `if`/`else` defs) of 90 and 85 lines, listed 90, is reported as `stale allowance: ... (85 lines, listed 90)`, and lowering it to 85 turns the 90-line one into a hit, so no listing passes. No listed key has two definitions today; the only repeated key is `tools.py:tool`, three short overloads (EXECUTED). Fix, the author's (code): `lengths[key] = max(n, lengths.get(key, 0))`, or answer in the pull request that it stays latent until a listed function is overloaded.

## Constitution checks

- §4 constraints: §4.9 holds, the check counts lines, never time (READ); §4.10 holds, the landing notes label the lengths EXECUTED with the command and I reproduced them (EXECUTED); §4.13 holds locally (ruff and the checks green per the description, the rules check and lint re-run here, EXECUTED) and awaits the run; §4.14 holds, one specification on a branch from `dev`'s tip, no `src/` change. §4.1 to §4.8, §4.11, §4.12 and §4.15 are not touched (no recipe, pin, import, artifact, licence or default changes, READ the diff).
- §7 never-do list: nothing tripped. The judge changes with its reason in the specification and a claim in the news file; no check, golden output, gap or `context/progress/` file is edited to turn a run green, and the new bound makes the rules check stricter, not looser (READ).

**For the landing: the list must equal the lengths on the head that merges.** 147 and 143 merge ahead of this pull request and may move a listed function. After each, the author rebases, re-runs the scan, lists the head's numbers, claims any new rise with its cause in the news file and updates the landing notes, and the reviewer reads that commit and signs again. The rules check runs in `quick` on every push, and a mismatch in either direction is red, so the run on the rebased head is the evidence; a merge of a head not rebased past a change that moved a listed length would be red on `dev`'s post-merge run. Every pull request merged after this one that lengthens a listed function now carries its claim (finding 1).

## Disposition (filled in by the author, then confirmed by the reviewer)

1. L1 —
2. L2 —
3. L3 —

## Verdict

Lands once run 40642434118's `ci-status` is green and its Windows legs are read: the scan holds each listed function at exactly its length, red on a rise and on a fall, the list equals the head's lengths, every raise is claimed with a cause that holds against 144 and 146, and nothing under `src/` moves; the run had not ended when this was written, so this line is written again when it has, and again after any rebase past 147 or 143 that moves a listed length.
