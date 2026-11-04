# Review of 184 — The release honours a retirement its merges made

- **Date:** 2026-11-04
- **Reviewer:** an agent (Claude), a fresh sub-agent of https://claude.ai/code/session_01BD1pVFRgzAfigBamtZXRcj; not the author
- **Reviewed:** `origin/dev` (`0b6ce99c`) `..9ff0981e`, pull request #99; time box 25 minutes (a parallel-safe judge change)
- **Run:** the pull request's run, read by the author
- **Re-ran:** `uv run pytest tests/unit/test_accept_from.py -q` → 77 passed, exit 0; `uv run pytest tests/lint -q` → 14 passed, exit 0; ruff check and format on the two Python files → clean; `release/version.py check` → `ok 0.1.3`. The three new rows against `dev`'s `accept_from.py` in a scratch copy → the first fails on "retired names … which is not absent", the other two pass. Two mutants of the new module: `retired_since_release` without its stop at the release line → only `test_a_retirement_before_the_last_release_is_not_honoured_again` fails; `retired_before` passed on `dev` too → only `test_a_merge_still_refuses_a_retirement_of_a_check_that_is_not_absent` fails.

## Acceptance criteria against evidence
1. The first row fails before and passes after, and holds a file-wide entry and a refused entry naming a still-accepted check — met: EXECUTED (scratch copy with `dev`'s module; the row's asserts read).
2. The other two rows pass before and after and guard the edges — met: EXECUTED, and each one kills the mutant it is there for (above), so neither is vacuous.
3. Every `retired` entry of the release is honoured against the real history — met: EXECUTED with `history.lines(context/progress)` (134 lines, both volumes): 39 claims (38 plus 184's own news file, now in the folder), 12 checks retired since the last release line (`n` 115, commit `193c99961ed3`, the same anchor `since_release` returns), 15 `retired` entries, none left. None of the 12 is in today's `accepted.json`, so no retired check has come back.
4. Fast tier, `tests/lint` and `ci-status` green, news file present — `tests/lint` met (EXECUTED); news file present (READ); the fast tier and `ci-status` are the run's, read by the author.
5. The 0.1.3 release pull request's next run accepts its record — not yet testable; for the landing notes (READ when it runs).

Correctness, adversarially (READ and INFERRED, `tests/harness/accept_from.py`):
- **No new retirement.** `retired_before` enters only the stray-entry test. `c.retire` is still built from `ratchet.absent` alone, and the "absent, and no claim retires it" and lost-pass refusals are untouched. So the change can turn a refusal into a pass only for a `retired` entry. It cannot clear a lost pass, an absent check, a growth, a fall or a tier move.
- **The same span.** `retired_since_release` and `since_release` walk the same `history_lines` backwards and stop at the same `_is_release_line`, excluding that line. A release acceptance's own `retired` is not honoured again.
- **Release only.** `before` is empty unless `_release_pr(meta)`. The third row and its mutant hold this.
- **A retired check that reappears.** If it is accepted again and present at the release, the old entry is honoured and retires nothing: harmless. If it were absent again at the release, the re-read claim would retire it. But that path is `news.reason` over `ratchet.absent`, as it was before this change, so it is not widened. None of the 12 is accepted today.

Docs (READ): `context/progress/README.md` rule 8, `context/changes/README.md` and the module docstring say the rule. The code files name no specification or `context/` path; rule 8's "(spec 184)" is under `context/`, where that is allowed. The CHANGELOG summary is still one paragraph of four sentences and 105 words (EXECUTED, `wc -w`), inside 30 to 120. The new decision cites the earlier entry it replaces, by its title. Its limit, 268,435,456, matches `PYPI_FILE_LIMIT` in `tests/harness/artifacts.py`. Its steps (`PYPI_FILE_LIMIT_GRANTED`, `PYPI_PUBLISH` true) are those of `docs/contributing/release-process.md` step 4. The summary's hand edit outside the preparation pull request goes against that page's "in the preparation pull request alone". The specification's Design and the decision record why (the preparation had merged; the owner asked for one pull request), so this is answered.

## Findings, most severe first
1. **The self-check's Windows box is unticked** (pull request #99's description) — the box "The Windows legs of the newest run on this pull request's head were read" is empty, with the reason "not yet". Fix text: read the Windows legs of this head's run, then tick the box before the merge. Low.
2. **A stray entry in the release ledger now passes when it names a check a merge retired** (`tests/harness/accept_from.py:318`) — the test applies to every claim the release reads, not only the re-read news files. So a `context/release-claims/` entry that names a check retired at a merge since the last release (`retired = ["tests/checks/test_v1_3_the_zips_directory.py"]`, say) is no longer refused. It retires nothing, so no verdict moves. This is Decision 1's wording, so a written answer is enough. Low.
3. **The prose says "a merge's acceptance", the code reads any line since the release** (`tests/harness/accept_from.py:424`, `context/changes/README.md`) — a local `--accept --retire` line on `dev` is honoured too. That is a real retirement, so the behaviour is right, and rule 8's "a history line" is the exact one. A written answer, or "an acceptance" in the docstring at a later touch, is enough. Low.

## Constitution checks
- §4 constraints: §4.14 holds (a branch from `dev`'s tip, one specification, a news file with its `units` and `[claim.judge]`). The judge change is its own specification, with its reason and the judge-hash line; no check, golden, allowance or `context/progress/` file is edited to turn a run green. Nothing under `src/`, `.github/` or `release/` changes (READ, `git diff --stat`), so 4b has no file to read. Structure (4a): nothing under `src/`; the new function is 9 lines; no row moves.
- §7 never-do list: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)
1. —
2. —
3. —

## Verdict
Lands: the fix is correct and no wider than a no-op `retired` entry, its three rows hold the change and both edges, and the three Lows need only a ticked box or a written answer.
