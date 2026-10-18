# 062 — The progress history stays small

- **Status:** drafted 2026-10-18; awaiting its pre-build review. Drafted on
  `spec/062-the-progress-history-stays-small` from main `f6b3f75`. Urgent: every landing is
  blocked until it lands (Intent).
- **Date:** 2026-10-18
- **Owner:** Clay Gendron
- **Kind:** a judge change; parallel-safe, not build-class (§5.7). It adds one harness module
  (`tests/harness/history.py`) and its unit tests (`tests/unit/test_history.py`), and edits
  `tests/harness/scoreboard.py`, `plugin.py`, `needs.py`, `scan.py`, the checks
  `test_progress_history_is_intact` (`tests/checks/test_rules.py`) and
  `test_same_bytes_passed_on_three_systems` (`tests/checks/test_v1_2_portable_and_sealed.py`),
  the unit tests that call the changed functions (`tests/unit/test_scoreboard.py`,
  `test_plugin.py`, `test_landing_lane.py`), and documents (`context/progress/README.md`,
  `context/README.md`, one amendment line each in specs 002 and 029). It touches no `src/`,
  `scripts/`, `recipes/`, `downloads/SHA256SUMS` or workflow; it changes neither the guest nor the
  artifact set. Every judging file it edits changes the judge hash: **the lane accepts it with
  `--accept-judge`.** Its pre-build review is asked for by the lane (the change guards the record
  every other change lands on).
- **Depends on:** 002 (the progress harness: the history, its chain, the need `three systems`),
  029 (the lane's guards: rule 1 reads the newest history line; the commit command of step 4), 052
  (the controller alone writes an acceptance); all landed.
- **Research it stands on:** `../research/2026-10-18-the-progress-history-stays-small.md` (called
  "the memo" below; findings 1 to 7).

## Intent

`context/progress/history.jsonl` holds one line per acceptance, append-only and hash-chained. At
main `f6b3f75` it is 1,037,524 bytes and 59 lines. The rules check
`test_no_artifact_or_large_file_is_tracked` refuses a tracked file over `1 << 20` bytes
(1,048,576). Spec 060's acceptance (`24b16f8`, held off main) adds a 33,770-byte line 60 and
makes the file 1,071,294 bytes, so its rules tier is red, and a red acceptance never reaches main.
Every later acceptance would do the same. So no change can land.

After this spec:
- **The history continues in volumes.** Lines 1 to 59 stay in `history.jsonl`, byte for byte.
  New lines go to further files in the same folder, each named after its first line and each kept
  under half the limit. The hash chain runs across them as one chain.
- **New lines are small.** A new line records which checks started or stopped passing since the
  line before, and a digest of the whole passed set, instead of the whole list. A line is about
  2 KB, not 34 KB, and it no longer grows with the number of checks (the memo, findings 2 and 4).
- **Every reader keeps working.** `three systems`, the ratchet, the intact check, rule 1 and the
  `accepted: … line N` message. A landing note still cites "history line 60"; the line number is
  global.

The size rule is not touched. It keeps every tracked file small, this one included.

## Decisions

1. **Volumes, named by their first line.** The history is the ordered sequence of its volumes in
   `context/progress/`. Volume 1 is `history.jsonl` and starts at line 1. Every later volume is
   `history-<n>.jsonl`, where `<n>` is the number of its first line, zero-padded to five digits
   (`history-00060.jsonl`; a number past 99,999 simply has more digits). A volume holds
   consecutive lines. *Reason:* `history.jsonl` cannot change (lines 1 to 59 must stay verifiable,
   and editing them is not allowed), and it has 11,052 bytes left (the memo, finding 1), so any fix
   starts a new file. Naming a volume by its first line lets a person find "history line 75"
   from a directory listing (the volume with the largest first line not above 75), and gives the
   intact check one more thing to hold: a name must equal its first line's `n`.
2. **`n` stays global.** Line numbers continue across volumes: the first line of
   `history-00060.jsonl` has `n: 60`. *Reason:* landing notes cite "history line 56"; those
   citations, and every later one, keep their meaning. The plugin prints `accepted:
   <volume path> line <n>`, so the note can name the volume too.
3. **One chain across volumes.** The first line of a volume carries in `prev` the hash of the last
   line of the volume before, exactly as any line carries the hash of the line before it.
   *Reason:* the tamper-evidence is one chain from line 1 to the newest line. Deleting, reordering
   or editing a volume breaks it like editing a line does.
4. **A volume rolls only when the next line would not fit.** `history.BUDGET = 1 << 19` (524,288
   bytes, half the rule's limit). An acceptance appends its line to the newest volume when that
   volume's size in bytes plus the line's UTF-8 length plus one (its newline) is at most `BUDGET`;
   otherwise it starts a new volume named after the line. An empty folder starts at
   `history.jsonl`. The intact check holds the rule both ways: every line written under this spec
   (Decision 6's format) ends at a byte offset of at most `BUDGET` in its volume, and every volume
   after the first begins with a line that would not have fitted in the volume before it.
   *Reason:* the roll is decided by one deterministic rule, so a volume can be neither overfull nor
   started early by hand. Half the limit leaves room for one unusually large line (a run in which
   thousands of checks change at once) and means the size rule is never what stops a landing.
   Volume 1 (1,037,524 bytes, all lines of the old format) is over the budget, so the first line
   written under this spec, line 60, starts `history-00060.jsonl`.
5. **The size rule stays as it is.** `test_no_artifact_or_large_file_is_tracked` and its
   `1 << 20` are not edited, and no file is exempted. *Reason:* the rule exists so that tracked
   files stay small; an exemption would let this one grow without bound.
6. **New lines carry the passed set as a change (format 2).** A line written under this spec has
   every key a line has today except `passed`, and four more:
   - `schema`: `2`;
   - `passed_added`: the sorted node ids that pass in this run and were not in the line before's
     passed set;
   - `passed_removed`: the sorted node ids that were in the line before's set and do not pass in
     this run;
   - `passed_digest`: `paths.sha256_bytes(json.dumps(sorted(S)).encode())`, where `S` is this
     run's full passed set.

   Lines 1 to 59 (no `schema` key) keep their full `passed` list and are never rewritten. A line's
   passed set is found by replay: an old-format line's set is its `passed`; a format-2 line's set is
   the set before it, minus `passed_removed`, plus `passed_added`. *Reason:* `passed` is 96% of a
   line and grows by about 87 bytes per passing check (the memo, finding 2); between acceptances
   the set changes by 0 to 24 ids (finding 4). Replayed over lines 1 to 59, the change form makes
   lines of 994 to 5,193 bytes, 9.4 times less in all. A 512 KiB volume then holds about 270
   acceptances; in the memo's model, 500 acceptances with checks growing to 1,390 make 2 volumes,
   against 83 with full lists (finding 5). The digest pins the replayed set at every line, so the
   change form keeps the same tamper-evidence as the full list: a wrong or edited change no longer
   replays to its digest. Volumes alone would work but make a new file every 6 to 15 acceptances;
   smaller lines alone cannot work, since volume 1 is full.
7. **Readers replay; one module owns the format.** A new module `tests/harness/history.py` (it
   imports only `paths`) holds the volume rules, the replay, the check and the reader of `three
   systems`:
   - `BUDGET`; `volume_name(n)`; `volumes(folder) -> list[Path]` in line order; `lines(folder) ->
     list[str]` (every line of every volume, in order); `target(folder, line) -> Path`
     (Decision 4);
   - `passed_sets(lines)`, which yields each line's replayed set and raises `ValueError` naming the
     line when a line does not replay (not JSON, an `added` id already in the set, a `removed` id
     not in it, a list not sorted, or a digest that does not match);
   - `errors(found, accepted_text, committed) -> list[str]` (Decision 9);
   - `systems_that_passed(folder, artifact) -> set[str]`: the systems of every line whose
     `artifact` is the hash and whose replayed set holds the probe
     `tests/checks/test_v1_2_portable_and_sealed.py::test_guest_runs_here[plain]`.

   `scoreboard.history_errors` and `scoreboard.systems_that_passed` move there; their callers
   (`needs._three_systems`, the two checks, the unit tests) follow. *Reason:* the format is read in
   four places (the intact check, three systems, rule 1, `accept`); one module keeps them from
   drifting. Replay is one pass over every line: thousands of lines, a few set operations each.
8. **`accept` builds a format-2 line; the plugin writes it where `target` says.**
   `scoreboard.accept` takes `history_lines: list[str]` (from `history.lines`) instead of
   `history_text`. `n` is their count plus one; `prev` hashes the last of them; the changes and the
   digest come from replaying them. A history that does not replay refuses the acceptance
   (`AcceptRefused`, naming the line). The plugin appends the line to `history.target(pdir, line)`
   and prints `accepted: <that path> line <n>`. *Reason:* the line is still made in one place and
   written once, by the controller (spec 052, Decision 3); only where it goes is new.
9. **An oversize line is refused, not written.** When a line's UTF-8 length plus one exceeds
   `BUDGET`, `accept` raises `AcceptRefused("the history line would be <k> bytes, over the volume
   budget of 524288 (spec 062)")` and nothing is written. *Reason:* a file over the budget must
   never be written, even once. This happens only when more than about 6,000 checks change in one
   acceptance (the memo, finding 5: 15 times today's number of checks); a red line is the right
   answer then, and a later spec can split such a line.
10. **The intact check covers every volume.** `history.errors(found, accepted_text, committed)`.
    `found` maps the name of every file in the progress folder whose name starts with `history`
    to its text; `committed` maps the name of every volume in HEAD's tree to its committed text, or
    is `None` without git. It reports, each as its own line:
    - a file starting with `history` that is not a volume name (`history-60.jsonl`,
      `history-00060.jsonl.orig`): "unrecognised history file";
    - an empty volume, a missing `history.jsonl` while later volumes exist, and a volume whose name
      is not its first line's `n`;
    - everything today's check reports (a line not JSON, `prev` not hashing the line before, `n`
      not its place, the last line's `accepted` not the hash of `accepted.json`, `accepted.json`
      without a history or a history without it), across volumes;
    - a line that does not replay (Decision 7), a format-2 line that carries `passed`, and an
      old-format line after a format-2 line;
    - a format-2 line that ends past `BUDGET` in its volume, and a volume begun early (Decision 4);
    - a committed volume missing from the folder, and a committed volume whose text is not a prefix
      of the file's.

    `test_progress_history_is_intact` keeps its name and calls it with the real folder and, from
    `git ls-tree --name-only HEAD -- context/progress/` and `git show`, every committed volume.
    *Reason:* today's check reads `history.jsonl` alone; an edit in a later volume would pass it.
11. **Rule 1 reads the newest volume.** `scan.acceptance_errors` finds the newest acceptance with
    `git rev-list -1 HEAD -- ':(glob)context/progress/history*.jsonl'`, takes the volumes in that
    commit's tree (`git ls-tree`), and reads the newest line from the newest volume. An acceptance
    commit carries `accepted.json` and its newest volume, and nothing else; any other change,
    another volume included, is reported ("an acceptance commit carries only accepted.json and its
    newest history volume"). The `dirty: false` rule is unchanged. *Reason:* today's rule follows
    `history.jsonl` only; once line 60 lives in volume 2, it would keep judging line 59's commit
    and miss an acceptance carried across a rebase.
12. **The lane commits with a fixed command.** Step 4 of the lane becomes:

    ```
    git add -- context/progress/accepted.json ':(glob)context/progress/history*.jsonl'
    git commit -m "Accept …" -- context/progress/accepted.json ':(glob)context/progress/history*.jsonl'
    ```

    The pathspec is one constant, `history.ACCEPT_PATHSPEC`, which the README quotes. *Reason:*
    `git commit -- <path>` refuses a path git does not know yet, and a new volume is untracked when
    it is written (the memo, finding 7). After `git add`, the same pathspec commits exactly the
    acceptance and still leaves out a change to `README.md` in the same folder and anything else
    staged (EXECUTED in a scratch repository, finding 7).
13. **Nothing is migrated.** Lines 1 to 59 are not edited, moved or re-encoded. Spec 060's held
    line 60 (`24b16f8`) is not carried over: it was written by the old writer into
    `history.jsonl`. The lane re-makes that acceptance after 062 lands (How the lane lands it).
    *Reason:* the chain and the committed-prefix check exist so that no line is ever rewritten.

## Design

**`tests/harness/history.py`** (new; a judging file under `tests/`). Decisions 1, 4, 6, 7, 9 (the
size test is shared with `accept`), 10 and 12. Constants: `BUDGET = 1 << 19`, `FIRST =
"history.jsonl"`, `PROBE` (the guest probe's node id, moved from `scoreboard`), `ACCEPT_PATHSPEC`.

**`tests/harness/scoreboard.py`.** `accept` takes `history_lines`, writes format 2 and refuses an
oversize line (Decisions 8 and 9). `last_history_line`, `history_errors` and
`systems_that_passed` are removed; `dumps` and everything else stay.

**`tests/harness/plugin.py`.** In `pytest_sessionfinish`: `history.lines(pdir)` in, `history.target`
out, the `accepted:` line with the volume's path. The `--progress-dir` help says "where
accepted.json and the history volumes live".

**`tests/harness/needs.py`.** `_three_systems` calls `history.systems_that_passed(paths.PROGRESS,
…)`. **`tests/harness/paths.py`** is unchanged: `paths.HISTORY` stays the path of volume 1.

**`tests/harness/scan.py`.** `acceptance_errors` per Decision 11; `PROGRESS_FILES` and
`HISTORY_FILE` give way to the volume rule from `history`.

**The two checks.** `test_progress_history_is_intact` (Decision 10) and
`test_same_bytes_passed_on_three_systems` (`history.systems_that_passed(paths.PROGRESS, …)`).

**Documents, in the build:**
- `context/progress/README.md`: "Three kinds of file" in place of "Two files": `accepted.json`,
  the history volumes and their names, format 2 and its replay, the budget; how to find line N;
  step 4 with Decision 12's two commands; step 5 unchanged.
- `context/README.md`: the folder line names "an append-only history in volumes".
- Spec 002 (the need table's `three systems` row and the history decision) and spec 029 (rule 1's
  "accepted.json and history.jsonl"): one line each, "Amended 2026-10-18 by spec 062: …", in the
  style of 002's amendment by 029.

## Scope

**In:** Decisions 1 to 13; the checks below; the documents above.

**Out:**
- Any edit of lines 1 to 59, of `test_no_artifact_or_large_file_is_tracked`, or of `1 << 20`.
- Splitting one line over several volumes (Decision 9 refuses instead).
- A full-set "keyframe" at the start of each volume, so a volume could be read alone. Replay from
  line 1 is cheap, and every volume is in the repository.
- **`accepted.json` reaching the limit.** It is 128,029 bytes for 388 checks and 125 judging
  files at `f6b3f75` (EXECUTED), about 300 bytes a check, so it reaches `1 << 20` near 3,500
  checks (INFERRED). The size rule will say so first. That is a later spec's question; this spec
  does not change `accepted.json`.
- Re-making spec 060's acceptance (the lane's work, below).

## Acceptance criteria

Each is counted; none times anything. Each check is written first, run against today's harness
(or the stand-in named) to see it fail, then the code is written. The builder records each
stand-in's failing assertion in the landing notes; a stand-in is applied in a scratch copy of the
module, never committed.

1. **Lines stop growing with the checks.** `tests/unit/test_history.py`: after a line whose passed
   set is 5,000 synthetic node ids of 83 bytes, `scoreboard.accept` on a run where the same 5,000
   pass makes a line under 4,096 bytes, with `passed_added == passed_removed == []` and no
   `passed` key; on a run where 10 more pass and 3 stop passing, exactly those 10 and 3, sorted; in
   both, the replayed set equals the run's passes and `passed_digest` is its digest. *Stand-ins:*
   (a) today's `accept` (a line over 430,000 bytes, and `passed` present); (b) a delta taken
   against `accepted.json`'s statuses instead of the line before (the 3 removed are missed when
   `accepted.json` keeps their old pass).
2. **Many more acceptances; the limit holds (the central criterion).** `tests/unit/test_history.py`
   writes a synthetic history in a temporary folder. Volume 1 is a look-alike of main's: 59
   old-format lines with full `passed` lists, a valid chain, at least 1,000,000 bytes. Then at least
   **500** acceptances through `scoreboard.accept`, `history.target` and an append (the code path
   the plugin uses), while the checks grow from 392 to at least 1,500; the system rotates
   `darwin`, `linux`, `win32`, each with checks that pass only on it; the artifact hash changes
   every 30 acceptances; every 50th acceptance is a partial run that passes only 20 checks (a large
   `passed_removed`, then a large `passed_added`); and on some runs the probe fails. It asserts:
   - volume 1's bytes are unchanged;
   - every file in the folder is at most `1 << 20` bytes, and every format-2 line ends at an offset
     of at most `BUDGET` in its volume;
   - there are at least 3 volumes, each named after its first line, and `n` runs from 1 to the last
     line without a gap;
   - `history.errors(…)` is empty, with `committed` set to the folder as it stood halfway through
     (every committed volume a prefix);
   - for every artifact hash, `history.systems_that_passed` equals the systems computed directly
     from the simulated runs.

   *Stand-ins:* (a) today's writer (one file, full lists: `history.jsonl` passes `1 << 20` at the
   first ten new lines); (b) a roll decided after writing (a volume ends past `BUDGET`); (c) volumes
   numbered by count (`history-00002.jsonl`) instead of first line; (d) a replay that ignores
   `passed_removed` (credits a system whose run failed the probe).
3. **Main's 59 lines stay valid as they are.** `test_progress_history_is_intact` passes on the
   real folder at the built commit (lines 1 to 59, old format, `history.jsonl` alone, with
   `accepted.json`), and `history.passed_sets` replays them to the same sets as their `passed`
   lists. `git diff f6b3f75 -- context/progress/` is empty on the built branch. *Stand-in:* an
   `errors` that requires format-2 keys on every line fails on the real file.
4. **Tampering is caught in every volume.** `tests/unit/test_history.py`, from a valid synthetic
   history of three volumes, one case per change, each giving its named error and no error on the
   untouched history: (a) one byte changed in a middle line of volume 2; (b) volume 2 deleted; (c)
   volume 3 renamed one number higher; (d) a stray `history-00070.jsonl.orig` and a
   `history-70.jsonl`; (e) a line appended to volume 1 after volume 2 exists; (f) volume 3 begun
   early (its first line would have fitted in volume 2); (g) a format-2 line pushing its volume past
   `BUDGET`; (h) the last line's `passed_added` edited so it no longer replays to its digest (no
   later line chains to it, so only the digest catches it); (i) an old-format line after a format-2
   line; (j) a format-2 line that also carries `passed`; (k) `accepted.json` edited. *Stand-in:*
   today's `history_errors` on `history.jsonl` alone reports none of (a) to (d) and (f) to (j).
5. **Committed volumes only grow.** `tests/unit/test_history.py`: with `committed` holding volumes
   1 and 2, a folder where volume 2 lost its last line, a folder without volume 2, and a folder
   where volume 1 changed are each reported; a folder that adds volume 3 and lines to volume 2 is
   not. *Stand-in:* a committed check on `history.jsonl` alone misses the first two.
6. **`three systems` reads every volume.** `tests/unit/test_history.py`: artifact `A`'s probe
   passes on `darwin` at line 59 (old format, volume 1); on `linux` at line 60 (volume 2; not in
   `passed_added`, since it was in line 59's set); fails on `win32` at line 61 (in
   `passed_removed`); passes on `win32` at line 62 (in `passed_added`); line 63 is artifact `B` on
   `linux` without the probe. `systems_that_passed(folder, A) == {"darwin", "linux", "win32"}`;
   for `B`, empty. *Stand-ins:* (a) today's reader, on `history.jsonl` alone (`{"darwin"}`); (b) a
   reader of `passed` only (the same); (c) a reader that takes `passed_added` as the set (misses
   `linux`).
7. **The plugin writes where `target` says, and says so.** `tests/unit/test_plugin.py`, the
   `inner` fixture: a progress folder whose `history.jsonl` holds old-format filler lines (each
   with a `passed` list, so they replay) over `BUDGET`; a green `--accept` writes line `N+1` to `history-<N+1>.jsonl`, prints `accepted:
   …/history-<N+1>.jsonl line <N+1>`, and leaves `history.jsonl`'s bytes unchanged; a second
   `--accept` appends line `N+2` to the same volume. *Stand-in:* today's plugin (appends to
   `history.jsonl`).
8. **An oversize line is refused.** `tests/unit/test_history.py`: `accept` on a run whose change
   from the line before is 7,000 ids of 83 bytes raises `AcceptRefused` naming the byte count and
   the budget; through the plugin (criterion 7's fixture), the same refusal is red and the folder's
   files are unchanged. *Stand-in:* an `accept` without the refusal (a line over `BUDGET` is
   written, and criterion 2's offset assertion would fail on it).
9. **Rule 1 across volumes.** `tests/unit/test_landing_lane.py` (its git fixtures): (a) an
   acceptance commit that adds `history-00060.jsonl` and changes `accepted.json`, sitting on the
   commit its line 60 judged: no error; (b) the same acceptance moved onto another parent: "sits on
   …, but its history line 60 judged …"; (c) an acceptance commit that also changes
   `history.jsonl`: "also changes context/progress/history.jsonl"; (d) line 60 saying
   `dirty: true` under a judge holding `tests/unit/test_landing_lane.py`: reported. *Stand-in:*
   today's `acceptance_errors` (it follows `history.jsonl`, keeps judging line 59's commit, and reports neither (b) nor (d)).
10. **The lane's commit command does what the README says.** `tests/unit/test_landing_lane.py`:
    in a scratch repository with a committed `history.jsonl`, a new volume, a changed
    `accepted.json`, a changed `context/progress/README.md` and another staged file, the two
    commands of Decision 12 (built from `history.ACCEPT_PATHSPEC`) make a commit holding exactly
    `accepted.json` and the new volume, and leave the other two changes uncommitted; and
    `context/progress/README.md` contains both commands verbatim. *Stand-in:* today's step 4
    (`git commit -- …accepted.json …history.jsonl`) exits non-zero on the untracked volume, or,
    once added, leaves it out.
11. **Green.** `ruff check`, `ruff format --check`, `uv run pytest -m "not slow" -n 3` and the full
    judge pass on the built commit; the run is red only by `judge changed`, which the lane accepts
    with `--accept-judge`. The fast-tier and unit counts are recorded in the landing notes.

## How the lane lands it

The next acceptance is 062's own. It writes line 60 with the new code.

1. **Land 062 first.** Rebase its reviewed commit onto main (`f6b3f75`, or whatever main is). Run
   the lane's steps 1 to 3a, serially:
   `uv run pytest --accept "Spec 062: the progress history stays small (…)" --accept-judge "the
   history continues in volumes and new lines store the passed set as a change (spec 062)"`.
   Volume 1 is over `BUDGET`, so line 60 starts `context/progress/history-00060.jsonl`; the run
   prints `accepted: …/history-00060.jsonl line 60`.
2. **Commit with the new step 4** (Decision 12's two commands), then step 5. The rules tier is
   green: `history.jsonl` is still 1,037,524 bytes, the new volume about 2 KB, rule 1 reads line
   60 from volume 2.
3. **Record in the landing notes:** `git diff f6b3f75 <acceptance commit> --
   context/progress/history.jsonl` prints nothing; `wc -c` of both volumes; the `accepted:` line.
4. **Then re-make spec 060's acceptance.** `24b16f8` is never used: its line 60 was written into
   `history.jsonl` by the old writer. Rebase 060's reviewed commit onto the new main, taking main's
   progress files (AGENTS.md rule 6a), and accept again: line 61, in `history-00060.jsonl`. 060's
   landing notes cite "history line 61", not 60. Every later landing goes the same way.

A landing note cites a line as before, by its global number, and may add the volume the
`accepted:` line printed: "history line 61 (`context/progress/history-00060.jsonl`)".

## Landing notes

None yet: the spec awaits its pre-build review.

One line: new history lines store only what changed in the passed set, and the history continues
in files named by their first line, each under half the limit, chained as one, with lines 1 to 59
untouched.
