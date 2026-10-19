# Review of 077 — The grant follow-ups (the build)

- **Date:** 2026-10-19
- **Reviewer:** a fresh agent (Claude Opus 5.5). I wrote spec 077's pre-build review and its
  confirmation, and none of the code.
- **Reviewed:** `spec/077-the-grant-follow-ups`, rebased onto main `23f1c4f`: the confirmed spec
  `aaac75e` (`cba597e` before the rebase), the build `42795d4`, and the notes `fd94262`
  (`git diff aaac75e..fd94262`; READ whole: `runner.py`, `test_runner_grants.py`, `README.md`,
  `CHANGELOG.md`, the landing notes). The builder's `build/077/` logs were read.
- **Ran:** EXECUTED on darwin-arm64, CPython 3.14.2. No tracked file of any tree was written.
  The fast tier rewrote the worktree's git-ignored `build/progress/latest.json`; the builder's
  copy was saved first, as `builder-latest.json` here. Stand-ins ran on a scratch copy (`tree/`,
  from `git archive fd94262`). Beside this file:
  - `probe_built_walk.py` → `.out`: the **built** `_walk_windows` and `_rewritten`, through
    their seams, over the Win32 model of 076's build review. The model is updated for 077: its
    reserved names now include the superscripts and console names, and a segment holding a
    reserved character names nothing. Named rows, roots to be made, and a fuzz of 95,515
    spellings whose alphabet holds `COM¹`, `conin$`, `com0` and `a*b`.
  - `probe_oracle_wide.py` → `.out`: the built `_rewritten` against `ntpath.isreserved("x\\" +
    name)` over 6,673,008 names. These are every code point alone (except `/` and `\`), and
    beside `nul`, `x`, `com` and `lpt`. They also include every one-letter case variant of every
    reserved name, with extensions and trailing spaces.
  - `standins.py` → `.out`: S1 to S6 re-made independently.
  - `fast-n3.log`, `fast-n3-latest.json`: the fast tier against `s-c50ca51fae5eb55b`.

## What holds

1. **The code is the confirmed design** (READ).
   - `_WIN_DEVICES` holds upper-case names: CPython's six, and `COM`/`LPT` with `1`–`9` and
     `\u00b9\u00b2\u00b3`.
   - `_WIN_RESERVED_CHARS` is `"*<>?|` plus the characters 0–31.
   - `_rewritten` is false for `.`/`..`. It is true for a `:`, a reserved character, a trailing
     space or period, or an upper-cased stem in the set. Nothing else in `_walk_windows` moved.
   - The `RAW` read export now uses the iovec at 200 and the count at 208.
   - The control zeroes 208 and 300, opens `f.txt` to read, and asserts errno 0, count 2 and
     `b"or"`.
   - The model mirrors the runner with its own sets, and the oracle case is as Decision 4 says.
   - The README and CHANGELOG lines are as the Design says.
2. **The model fuzz agrees with the built walk** (EXECUTED, `probe_built_walk.out`).
   - Over 95,515 spellings: 1,020 accepted, **0 with a wrong chain, 0 leaking a handle, 0
     errors other than a refusal**.
   - `C:\b\COM0` is walked to itself with a true chain.
   - `C:\b\conın$`, `a*b` and `a|b` are refused.
   - The roots to be made `C:\b\new\COM¹`, `…\CONIN$`, `…\a*b`, `…\a?b` and `…\a\x01b` are all
     refused before anything is made: the corner both reviews named is closed.
   - Every row from 076's build review behaves as before.
3. **The oracle holds far beyond the unit case** (EXECUTED, `probe_oracle_wide.out`). The built
   `_rewritten` equals `ntpath.isreserved` on all 6,673,008 names, with 0 differences, so the
   README's "exactly those Python's `ntpath.isreserved` refuses" is true. The unit case's 18,275
   names are a fair, fast sample of that. It counts names, not time, and asserts both answers
   occur. It skips below 3.13 only, and the judge and release run 3.14.2.
4. **The stand-ins bite.** The builder's log records S1 to S6 CAUGHT, and "seen failing first":
   three nodes failed before the code (READ). Re-made independently on the scratch copy, all six
   are CAUGHT with the expected messages (EXECUTED, `standins.out`):
   - S1 (no superscripts): the walk's "DID NOT RAISE" and the oracle's `LPT³…` differences;
   - S2 (no console names): the same, on `CONOUT$`/`conin$`;
   - S3 (export at 400/408): `assert 0 == 2`;
   - S4 (the write-only descriptor opened `READ|WRITE`): `assert 0 == 8`;
   - S5 (no reserved characters): "DID NOT RAISE" and the oracle on `x*y`, `?`, `|`;
   - S6 (stem lower-cased): the oracle on `conın$`.

   The unchanged copy passes all four cases.
5. **The judge is not weakened** (READ). It only gains rows, a control row and one case, and
   every changed value is stricter. The judge change named is `tests/unit/test_runner_grants.py`
   alone.
6. **The growth is not 077's** (READ and EXECUTED).
   - 077 changes `_rewritten`, which runs only in a judged walk on Windows, plus one unit file.
     No guest run on macOS reaches either.
   - Three runs grew on three **different** rows of spec 071's `test_recursion_through_python_raises`:
     - the builder's full judge on `[lru-cache-plain]`;
     - the CI macOS judge of dry run 39210847037 on `[lru-cache-plain]` and `[pickle-partial-plain]`;
     - my fast tier on `[heapq-plain]` (`177337468 -> 177442609`).
   - That pattern is run-to-run variation on main, not a change made here. It is spec 080's, as
     the coordinator says.
   - Fast tier, `-n 3`, against `s-c50ca51fae5eb55b`: `474/550 pass · 1 gap · 24 blocked · 0
     fail · 51 deselected (unit suite 1268/1276, 8 skipped)`; `lost 0 · absent 0 · unrun 0 ·
     gained 0 · grew 1` (that row); `1742 passed, 32 skipped, 1 xfailed`. Exit 1, from the growth
     alone.
7. **The dry run so far is honest** (EXECUTED with `gh`).
   - Run 39210847037 is `workflow_dispatch` on `spec/077-verify`, with head `70bdf25`. Its only
     parent is `42795d4`, the build; `42795d4..fd94262` touches only the spec.
   - Its one file is `release.yml`, +1 −1 (`-rA`), matching `build/077/verify-commit.diff`.
   - Jobs: both rebuilds succeeded, `build and judge (arm64 macOS)` failed on `RED: 2 metric(s)
     grew` (the two 071 rows above), and `verify` and everything after it was skipped.
   - `git ls-remote` shows no `spec/077-verify` left.
   - The landing notes say all this and keep criterion 6 open.

## Findings

None that block.

- **N1 (no action, cosmetic).** The README and CHANGELOG hunks leave one over-long line each
  ("folder so named cannot be granted on Windows. A path rooted with no drive (`\data`) takes";
  "…before any folder is made. A path rooted with no drive takes the current folder's drive.
  The"). Markdown renders them the same; rewrap if the lane cares.
- **N2 (no action).** The refusal message for `a*b` stays "a name Windows rewrites", though
  Windows rejects it; Decision 3 keeps 076's wording on purpose, and the README explains it.

## What the Windows run must show (criterion 6)

Once spec 080 lands, 077 is rebased onto it. The rebase will most likely change files under
`tests/` (080 fixes 071's rows), so by the freshness rule the dry run is made **on the rebased
tip**, not on `42795d4`. It must show:

1. **The temporary commit.** It comes from `git commit-tree` on the rebased tip, its only parent
   is that tip, and its only change is `-rA` in the verify step (+1 −1). It is pushed to
   `spec/077-verify` and deleted after the run. The landing notes record the run id, its
   `headSha` and parent, and the diff.
2. **The jobs.** Every job passes on all three systems: both rebuilds, `build and judge (arm64
   macOS)` with no lost pass and nothing grown, `the same bytes from every host`, and `verify`
   on `ubuntu-24.04`, `macos-15` and `windows-2025`. Attest and publish are skipped, as on any
   dry run.
3. **The PASSED lines.** In `verify (windows-2025)`, the landing notes quote one `PASSED` line
   each for:
   - `test_the_windows_walk_takes_dot_dot_on_walked_folders`;
   - `test_the_windows_walk_records_the_true_chain`;
   - `test_a_rewritten_name_is_one_ntpath_refuses`. It must be PASSED, **not SKIPPED**: the job
     runs 3.14.2, so a skip there would mean the wrong Python;
   - `test_a_read_only_grant_refuses_raw_writes`. This is the first Windows observation of a
     two-byte read through a write-only descriptor, answering `EACCES` (2), and of the control
     read returning `b"or"` on Windows.
4. **Nothing else red or blocked.** The step's blocked needs are only `oracle`, `three systems`
   and `wheel`, as the next step asserts.

A node that is missing, `SKIPPED`, blocked or deselected fails criterion 6, as a `FAILED` one
does.

## Verdict

**It lands once criterion 6's Windows run passes.** Everything that can be judged without it
holds: the code is the confirmed design, the model fuzz and a 6.7-million-name oracle agree with
it, S1 to S6 bite, the judge is stricter, and the one red metric is spec 071's run-to-run
variation, seen on three different rows in three runs.

## One line

077 is right on macOS and in the model, `_rewritten` equals `ntpath.isreserved` on every name
tried, and only the Windows dry run on the post-080 tip remains.
