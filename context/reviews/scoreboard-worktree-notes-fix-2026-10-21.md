# Review of the scoreboard's folded worktree notes (judge fix at 5768d89)

- **Date:** 2026-10-21
- **Reviewer:** a fresh agent started by the lane; wrote none of this change
- **Reviewed:** `5768d89` on `2f53613` (`tests/harness/scoreboard.py`, `tests/unit/test_scoreboard.py`)
- **Run:** none dispatched (the lane asked for unit files and ruff only; a judge-only fix)
- **Box:** 25 minutes; finished inside it
- **Re-ran (EXECUTED):**
  - `uv run pytest tests/unit/test_scoreboard.py tests/unit/test_plugin.py tests/unit/test_landing_lane.py -q` → 136 passed, exit 0 (30 worktrees on this host at the time).
  - the new row by node id → 5 passed.
  - the new row with `folded_notes` patched to the identity (a scratch plugin, no file edited) → `[2]`, `[10]`, `[40]` fail, `[0]`, `[1]` pass: the row fails first as claimed.
  - `uv run ruff check src tests` → clean; `uv run ruff format --check src tests` → 151 files formatted.

## Criteria against evidence

1. Nothing the judge decides changes — met (READ): `folded_notes` is called only in `render`; verdicts, refusals, the ratchet and `meta["notes"]` (written at `tests/harness/plugin.py:716`) are untouched; `test_landing_lane.py:687` still holds `meta["notes"] == [NOTE]` and passes.
2. LOST/ABSENT/GREW and the "not machine-checked" lines print under every worktree count — met (EXECUTED for 0/1/2/10/40; READ for the tail: the "not machine-checked" lines are in `end`, never cut).
3. One note prints as before — met (EXECUTED, `[1]` asserts `shown == notes`).
4. Rule 4 — met (READ): the diff adds a check and edits no expectation, golden, allowance or progress file.
5. Citation rule — met (READ): the new docstring cites no document. The folded line reuses the existing note's suffix "(constitution §4.14 puts them outside)", text a user already read before this change, not a new comment.

## Findings, most severe first

1. **Low: other kinds of note would move below the folded line** (`tests/harness/scoreboard.py:336-343`). Today every note is a worktree note (`plugin.py:716` is the only producer), so nothing changes now. Should another kind appear, with two or more worktree notes it prints after the folded line rather than in its original place; with fewer than two, order is untouched. No fix needed; if order ever matters, put the folded line where the first worktree note stood.
2. **Low (note): the cap can still cut an example line for reasons other than worktrees** (`scoreboard.py:414`). Worst case today, READ: header, overrides, one note line, six areas, blocked, gaps, next and trap make 13 lines above the tail; the ratchet, RED and two "not machine-checked" lines make 4, plus one per FEWER line. That leaves 8 minus the FEWER count for LOST/ABSENT/GREW, which run in that order. All three LOST lines survive while there are at most five FEWER lines; the GREW lines go first. A new head-line kind or an unbounded note kind would shrink this again. Long goal lists cost width, not lines. No fix needed now; the next change that adds a head line should add a row like this one.
3. **Note: the failing check depended on the host.** `test_a_lost_pass_is_red_and_cannot_be_accepted`'s inner run reads the real repository's worktrees, so its scoreboard grew with the host's worktree count. After the fold it costs at most one line whatever the host holds, so the check no longer depends on that count.
4. **Note for the lane: running the unit files in the main tree rewrote `build/progress/latest.json`** (02:04, a 0-check record from the probe). It is a build file, not `context/progress/`. The next judge run writes it again.

## Verdict

Lands: the fix changes only how the scoreboard prints the notes, keeps every red and example line under 0 to 40 worktrees, and the new row was seen failing first.
