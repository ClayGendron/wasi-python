# Review of spec 062 before build: the progress history stays small

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude Opus 5.5). It wrote neither the specification nor the memo.
- **Reviewed:** `context/specifications/062-the-progress-history-stays-small.md` and `context/research/2026-10-18-the-progress-history-stays-small.md` at `3b81107`, on branch `spec/062-the-progress-history-stays-small` (`git diff f6b3f75..HEAD`: those two files only). The lane asked for this pre-build review: the change guards the record that every other change lands on. It was reviewed as a judge change. The bar: lines 1 to 59 stay byte for byte, no tamper that today's check catches goes unseen, every reader of the history gives the answer it gives today, and no lane guard (spec 029) gets weaker.
- **Read:** `AGENTS.md` (rules 4 to 6a, 9); the constitution (§4.9, §4.10, §5.2, §5.6, §5.7, §7); `context/progress/README.md` (the files, the lane's steps 1 to 6, "Before a release"); `tests/harness/scoreboard.py` (`accept`, `history_errors`, `systems_that_passed`), `plugin.py` (`accept_refusal`, the writing block of `pytest_sessionfinish`, the skip re-evaluation), `needs.py` (`_three_systems`, `need`), `paths.py` (`HISTORY`, `dirty_path`, `DIRTY_UNTRACKED`), `scan.py` (`acceptance_errors`); `tests/checks/test_rules.py` (`test_no_artifact_or_large_file_is_tracked`, `test_progress_history_is_intact`, `_committed`, rule 1's check); `tests/unit/test_several_cores.py` (`_history`); `.gitattributes`; the house format, `context/reviews/052-the-judge-on-several-cores-spec-2026-10-18.md`; the author's logs `build/062-fast-tier.log` and `build/062-fast-tier-set.log` in the worktree.
- **Executed** (scripts and outputs beside this file; no tree of the repository written):
  - `proto.py`: a prototype of the spec's rules written from the spec's text alone (volumes, names, `target`, replay with digests, `errors`), counting bytes hashed and set operations. It is the reviewer's, not the builder's.
  - `probes.py` (output `probes.out`): P1 main's 59 lines replayed and extended by three format-2 lines; P2 four tampers; P3 two scale runs; P4 one line's budget.
  - `p5_quadratic.py` (`p5.out`): what criterion 2 costs when `accept` replays from line 1.
  - `p6_move59.py` (`p6.out`): an old-format line moved into a later volume.
  - A scratch git repository (git 2.51.0): Decision 12's two commands, step 5's `reset --soft` and redo, and `rev-list` on a commit that deletes a volume.
  - `uv run pytest tests/checks/test_v1_3_matplotlib.py -m "not slow"` without `WASI_PYTHON_ARTIFACTS` (`noart.out`), for the author's side note.
- **Not re-run:** the scoreboard. There is no build to judge yet.

## The design against the questions asked

- **Lines 1 to 59 and the boundary (EXECUTED, P1).** Replaying main's 59 lines gives exactly their `passed` lists. Line 60 lands in `history-00060.jsonl` (1,337 bytes), lines 61 and 62 follow it (2,694 and 4,107 bytes), `history.jsonl`'s bytes are unchanged, and the prototype's `errors` is empty: the chain verifies across the boundary. Volume 1's SHA-256 at `f6b3f75` is `0a99162aefbb4d997b80b2012e73a39364aba108defe56781611cb1623ed1120`.
- **Tamper-evidence (EXECUTED on the prototype, P2 and P6).** Editing, deleting, reordering or renaming within or across volumes is caught by the chain, `n`, the name rule or the begun-early rule, as the spec says. A non-canonical name (`history-000060.jsonl`) is caught only if "name" means the exact canonical spelling (F4). Three things are not caught by the intact check alone:
  - the newest volume deleted, with `accepted.json` put back to the line before (P2 ii, silent);
  - the last line's `passed_added` and `passed_digest` rewritten together (P2 iii, silent);
  - line 59 and volume 2 rewritten into `history-00059.jsonl` (P6, silent). The first two are exactly as today: truncating `history.jsonl`, or editing its last line's `passed`, is silent to today's check too. The committed-volume check catches all three before a commit, and rule 1 catches the first after one (F7). The third is new and cheap to close (F3).
- **Replay for every reader (READ, INFERRED).** A format-2 line's replayed set is, by construction, that run's passes. So it is the same set as an old line's `passed`, including on a `--partial` line (its unrun checks are simply absent, then return in the next line's `passed_added`). `three systems` asks the same question of the same set. The ratchet, fewer-passes and growth logic read `accepted.json` only (`scoreboard.compare`, `accept`'s metric merge); they never read the history and are untouched. An added or removed list that disagrees with the digest is reported by `passed_sets` at that line, and an edit to any line but the last also breaks the next line's `prev` and every later digest.
- **Budget (INFERRED from line 59, P4; EXECUTED, P3).** A format-2 line with no change is 1,336 bytes; an id costs 87 bytes; one line passes `BUDGET` at about 6,008 changed ids. Decision 9's refusal plus Decision 4's roll mean no volume can ever exceed `BUDGET`, so any budget below `1 << 20` would hold the rule; half is sound. The realistic trigger for the refusal is a `--partial` acceptance on a machine without artifacts (it removes nearly every id, and the next line adds them back), not "thousands of checks changing". With partials every 50th line, criterion 2's own model gives lines up to 117,397 bytes at 1,500 checks and 266,079 at 3,500. `accepted.json` reaches the limit near 3,500 checks first, so the refusal is not the binding wall (F9).
- **The lane's commands (EXECUTED).** Decision 12's `git add` then `git commit -- <pathspec>` committed exactly `accepted.json` and the new volume, and left a changed `README.md` in the same folder and an unrelated staged file out. After `git reset --soft HEAD^` the same commit command redoes it. `git rev-list -1 HEAD -- ':(glob)context/progress/history*.jsonl'` finds a commit that only deletes a volume. The glob also sweeps a stray `history-70.jsonl` into the commit (F8). Nothing else in spec 029's guards assumes one file: `dirty_path` treats all of `context/progress/` as clean, and the size rule is per file.
- **Scale (EXECUTED, counted, P3 and P5).** See F2: per-line digest verification makes replay O(lines x checks), and `accept` replaying from line 1 makes criterion 2 quadratic.

## Findings, most severe first

1. **Medium. Criterion 3 cannot pass as written.** It requires `git diff f6b3f75 -- context/progress/` to be empty on the built branch. The same build edits `context/progress/README.md` ("Documents, in the build"). That diff is therefore never empty. *Fix:* `git diff f6b3f75 -- context/progress/history.jsonl context/progress/accepted.json` is empty, plus no file matching `history-*.jsonl` exists on the built branch (READ).

2. **Medium. Replay is not "a few set operations" a line, and `accept` makes criterion 2 quadratic (EXECUTED, counted).** Decision 7 makes `passed_sets` check every line's digest. Each check sorts, serialises and hashes the whole passed set, so it costs O(checks), not O(change). Counted on the prototype:
   - one verified replay of 500 acceptances growing to 1,500 checks hashes **36,924,332** bytes;
   - one verified replay of 3,000 acceptances growing to 3,500 checks hashes **441,570,727** bytes, against 305,325 set operations without digests;
   - criterion 2 calls `accept` 500 times. If `accept` replays from line 1 with digests, the calls hash **7,540,480,222** bytes in all and parse **1,045,123,016** bytes of JSON (P5). Half of that parse is volume 1, read 500 times. A judge run replays up to three times (the intact check, `accept`, `three systems`). *Fix:*
   - `passed_sets(lines, verify=True)`. Only `errors` verifies every digest.
   - `accept` replays with `verify=False` and checks only the last line's digest (one hash). It still refuses a history that does not apply (an added id already present, a removed id absent, a list unsorted).
   - `systems_that_passed` replays with `verify=False`. The intact check is where tampering is reported.
   - Criterion 2 records two counts in the landing notes: bytes hashed and JSON bytes parsed by the whole test. If the parse count is too large for the fast tier, the builder may cache the replayed set by the last line's hash inside `history`; a count, not a time, decides.
   - Correct Decision 7's reason ("a few set operations each").

3. **Low-Medium. An old-format line can live in a later volume (EXECUTED, P6).** Decision 10 forbids an old-format line after a format-2 line, but not one at the head of a later volume. P6 moved line 59 into `history-00059.jsonl` with lines 60 to 62 after it. The chain, `n`, the name and the begun-early rule all hold (volume 1, at 1,003,766 bytes, could not take line 59), so the prototype reported nothing. Only the committed-prefix check catches it, and only until the rewrite is committed. That contradicts Decision 1's "lines 1 to 59 stay in `history.jsonl`". *Fix:* in Decision 10, "an old-format line in any volume but `history.jsonl`" is an error. Add it as criterion 4(l). Optional and cheap: a constant `SEALED = {"history.jsonl": "0a99162a…1120"}` in `history.py`, checked by `errors`. Then lines 1 to 59 are pinned byte for byte even against a committed rewrite, which neither today's check nor the spec's catches.

4. **Low. Say exactly what a valid name, order and line are.** Decision 1 leaves these open:
   - **Canonical names.** "A volume whose name is not its first line's `n`" must mean `name == volume_name(n)`. Otherwise `history-000060.jsonl` and `history-00001.jsonl` are second names for a line.
   - **Numeric order.** `volumes()` and rule 1's "newest volume" must sort by the number. Sorted by name, `history-100000.jsonl` comes before `history-99999.jsonl` (EXECUTED).
   - **Unknown `schema`.** A line whose `schema` is not 2 (`3`, `"2"`) is an error, not "old format".
   - **Blank lines.** Today's reader skips them. Say whether a format-2 volume may hold one (it shifts offsets).
   - **An unreplayable history.** `systems_that_passed` on a history that does not replay raises inside the `three systems` predicate, so `test_same_bytes_passed_on_three_systems` errors loudly. That is acceptable. Say so. *Fix:* one sentence each in Decisions 1, 7 and 10. Add the two names to criterion 4(d).

5. **Low. Count bytes, and write bytes (READ).** The plugin appends with `.open("a")`, text mode, which writes `\r\n` on win32. `target` measures `st_size`, which is bytes. A check that reads text measures characters. After a win32 acceptance the two disagree. The roll comes early, and a text-measuring `errors` could then report "begun early". `three systems` needs linux and win32 acceptances someday. *Fix:* the plugin writes with `newline="\n"` (or bytes). `target` and `errors` both measure with `read_bytes`. Say so in Decisions 4 and 8.

6. **Low. Criteria 2 and 9 can be sharper.**
   - Criterion 2 should also assert that, at every line, the replayed set equals the simulated run's passes. It is direct and cheap.
   - It should require at least one artifact whose expected systems are a strict subset: a system's runs on that artifact all fail the probe, after the probe passed on an earlier line. Without that, stand-in (d) (a replay that ignores `passed_removed`) may be caught only by the digest, not by the `three systems` assertion it names.
   - "At least 3 volumes" holds: the prototype makes 6 with criterion 2's parameters (P3).
   - Criterion 9 should add (e): the newest commit touching a volume deletes one. Rule 1 must report it, since it changes a volume that is not the newest.
   - The stand-ins are real when applied to a scratch copy of the module the test imports, as the spec says.

7. **Info. The tamper-evidence limits are today's, and the digest is a consistency check, not a seal (EXECUTED, P2).**
   - Deleting the newest volume and putting `accepted.json` back is silent to the intact check once committed. The committed-volume check catches it before the commit. After it, rule 1 catches it: `rev-list` finds the deleting commit, which changes a volume that is not its newest and whose newest line names an older commit. That holds only if Decision 11 compares against the newest volume in the commit's tree, as written.
   - A last line rewritten with a recomputed digest is silent, as editing the last line's `passed` is today. *Fix:* one sentence in Decision 6, so that no later reader leans on `passed_digest` as protection against a deliberate edit. Criterion 4(h) tests the accidental case.

8. **Info. The glob commits a stray `history-70.jsonl` (EXECUTED).** It does no harm. An untracked file under `context/progress/` is not "dirty" (`dirty_path`), so step 3's run goes ahead, and the intact check makes it red ("unrecognised history file"), so `--accept` refuses. A `.orig` file does not match the glob. No change is needed. One line in the README's step 4 would help a person.

9. **Info. The author's two side notes do not belong in 062.**
   - *The four spec-023 checks.* `test_matplotlib_data_is_granted_read_only[plain|snapshot]` and `test_usr_local_lib_holds_only_the_zip[plain|snapshot]` (`test_v1_2_hostile_guest.py`) fail without artifacts (READ, `build/062-fast-tier.log`: 4 fail). With the set they pass (`062-fast-tier-set.log`: 326 pass, 0 fail). The matplotlib file's own fast checks block correctly (EXECUTED, `noart.out`: 3 blocked by `artifact dir`). It is a missing need in 023's checks, so it is its own judge change, owned by 023's follow-up. 062's builder judges with the artifact set, as instructed.
   - *`accepted.json`.* 288 bytes a check (EXECUTED: 111,711 bytes of checks for 388). The history went from 14 to 374 passing checks between lines 1 and 59 (2026-10-16 17:50 to 2026-10-18 19:27). At that pace, 3,500 checks is weeks away, not years (INFERRED). Per-platform metrics will make each entry larger once linux and win32 accept. It is a different file and a different design, and folding it in would delay an urgent fix. The lane should open its research memo now, so it is not the next emergency.

10. **Info. Documents.**
    - The README's "Before a release" paragraph names `history.jsonl`. Make it "the history".
    - A person can no longer read line N's passed set off the line. The README should give the one-liner (`history.passed_sets(history.lines(paths.PROGRESS))`).
    - `tests/unit/test_several_cores.py` reads `history.jsonl` directly. It stays right, since an empty folder starts there, and needs no edit.

## Constitution checks

- §4.9: holds. No criterion times anything. F2's numbers are counts.
- §4.10: the memo's and the spec's numbers carry their labels. The one claim that is not a count (Decision 7's "a few set operations each") is corrected by F2.
- §5.2: holds once F4 is written in. The later "split such a line" and `accepted.json` are scoped out with reasons, not left open.
- §5.6: this is the pre-build review the lane asked for. The build is reviewed again.
- §5.7: holds. Parallel-safe and not build-class, accepted with `--accept-judge`. Lane step 4 changes by a fixed, tested command (criterion 10).
- §7: nothing tripped. No line is rewritten, no limit is raised and no file is exempted.

## Verdict

**Ready to build once F1 to F3 are written in.** F1 is a wording fix. F2 changes Decision 7 and criterion 2. F3 is one line in Decision 10 and one case in criterion 4. F4 to F6 are carried as conditions for the build, and the build review checks them. F7 to F10 need no change to the design.

One line: volumes plus change-lines are the right design and they verify across the boundary with lines 1 to 59 untouched. Before building, fix criterion 3's diff, verify digests only in the intact check so replay stays linear, and forbid old-format lines outside `history.jsonl`.
