# Review of 149 — the runner's structure Lows are closed: the news file retires no row

- **Date:** 2026-10-28
- **Reviewer:** an agent (Claude Opus 5.5), a fresh sub-agent of https://claude.ai/code/session_01ThzDEU6oHaVS4VRYYiC1im; not the author
- **Reviewed:** a300b655 on dev bd8dcaee (pull request #47)
- **Run:** 40723388657
- **Re-ran:** `uv run pytest tests/lint tests/unit/test_news.py -q -p no:cacheprovider` → 35 passed, exit 0
- **Box:** 25 minutes; done inside it.

## What the change is

Dev's post-merge run 40715047964 on bd8dcaee refused its acceptance with one line: `149: retired names tests/unit/test_runner_waits.py::test_with_no_table_every_number_above_2_is_ready, which is not absent`. The commit removes the `retired` list, its one entry, from `context/changes/149-the-runners-structure-lows-are-closed.md`. Nothing else changes.

## Acceptance criteria against evidence

1. The row was never accepted by name — met. EXECUTED: `grep test_with_no_table_every_number_above_2_is_ready context/progress/accepted.json` finds nothing; `grep test_runner_waits` finds one line, the file's hash in the judge's hash table (line 18463), not a row; no `tests/unit/…::` node id appears in the record at all.
2. Unit rows are kept only as a tally — met. READ: `tests/harness/plugin.py` `area_of` returns a goal only for a `goal`-marked item, and `_carry` sends a unit test's pass and skip as a suite tally, with no per-id record, when it has none.
3. The `retired` rule refuses an entry that matches no absent row — met. READ: `tests/harness/accept_from.py` `claimed` (lines 274 to 277) appends `retired names …, which is not absent` for each retired entry that `news.names` matches against no row of `ratchet.absent`. A row never held by name cannot be absent, so the claim could only refuse.
4. No accepted pass is lost — met. READ: the removed test is gone from `tests/unit/` (no `def test_with_no_table…` remains); the record held it only inside the tally, and `units` is parsed but not judged at acceptance. INFERRED: the post-merge run's only refusal was this line, so the tally's change refused nothing.
5. The pull request's run is green but for the review — met. EXECUTED: `gh run view 40723388657` shows `plan`, `quick`, `verify`, every Linux and Windows judge shard and the gather green, the rest skipped, and `ci-status` the one red job. INFERRED: its refusal is the missing review file, since every other job is green and this file is not yet on the branch.
6. Self-check — met. READ: the `Author:` line names the orchestrating session; the boxes say documentation only, no new check or gap, the news file the one changed.

## Findings, most severe first

None.

## Constitution checks

- §4 constraints: the judge is not weakened; a claim that could only refuse is dropped, and no check, golden output, gap, allowance or `context/progress/` file is touched.
- §7 never-do list: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

No findings.

## Verdict

Lands: dropping a retire claim for a unit row the record never held by name loses no accepted pass and clears the post-merge run's only refusal.
