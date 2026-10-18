# 062 — The progress history stays small

- **Status:** built 2026-10-18; awaiting its build review. Built on
  `spec/062-the-progress-history-stays-small` (the Landing notes). Before that it was revised
  against its pre-build review, with F1 to F3 written in and F4 to F6 as build conditions, now
  built and evidenced in the Landing notes, and the lane confirmed it for build. The review is
  `build/reviews-evidence/062-spec/062-the-progress-history-stays-small-spec-2026-10-18.md` in
  the main tree, which the lane copies to `context/reviews/` ("ready to build once F1 to F3 are
  written in"), and every finding is answered in the Disposition. Drafted 2026-10-18 from main
  `f6b3f75`. It is urgent: every landing is blocked until it lands (Intent).
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
   consecutive lines. A valid name is exactly what `volume_name(n)` makes for its first line's
   `n`: `history-000060.jsonl` and `history-00001.jsonl` are not second names for a line (the
   review, F4). Volumes are ordered by that number, never by name (sorted by name,
   `history-100000.jsonl` would come before `history-99999.jsonl`). Old-format lines (Decision 6)
   live only in `history.jsonl`, and its bytes are pinned: `history.SEALED = {"history.jsonl":
   "0a99162aefbb4d997b80b2012e73a39364aba108defe56781611cb1623ed1120"}`, its SHA-256 at
   `f6b3f75` (EXECUTED, `shasum -a 256`), which the intact check compares (the review, F3).
   *Reason:* `history.jsonl` cannot change (lines 1 to 59 must stay verifiable,
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
   bytes, half the rule's limit). Every size here is in bytes: `target` and `errors` measure a
   volume with `read_bytes()`, a line by its UTF-8 encoding, and the plugin writes with
   `newline="\n"`, so a win32 acceptance writes the same bytes as any other (the review, F5).
   An acceptance appends its line to the newest volume when that
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
   replays to its digest. **The digest catches inconsistency, not forgery** (the review, F7): a
   person who rewrites the last line's `passed_added` and its `passed_digest` together is not
   caught by it, exactly as an edit of the last line's `passed` is not caught today. What catches
   a deliberate edit is the chain (for every line but the last), the committed-prefix check
   (before a commit) and rule 1 (after one). No reader may lean on `passed_digest` as a seal.
   Volumes alone would work but make a new file every 6 to 15 acceptances;
   smaller lines alone cannot work, since volume 1 is full.
7. **Readers replay; one module owns the format.** A new module `tests/harness/history.py` (it
   imports only `paths`) holds the volume rules, the replay, the check and the reader of `three
   systems`:
   - `BUDGET`; `volume_name(n)`; `volumes(folder) -> list[Path]` in line order; `lines(folder) ->
     list[str]` (every line of every volume, in order); `target(folder, line) -> Path`
     (Decision 4);
   - `passed_sets(lines, verify=True)`, which yields each line's replayed set and raises
     `ValueError` naming the line when a line does not apply: not JSON, a `schema` other than the
     integer `2` on a line that has one, an `added` id already in the set, a `removed` id not in
     it, a list not sorted, or (only with `verify=True`) a digest that does not match;
   - `last_passed(lines) -> set[str]`: the newest line's replayed set, for `accept`. It replays
     with `verify=False` and then checks the newest line's digest alone (one digest). A
     module-level cache of one entry, keyed by the SHA-256 of the newest line, which `accept`
     fills with the set of the line it makes, lets the next call skip the replay; on a miss it
     replays. The key is a line whose `prev` chains to every line before it, so a hit is the set
     a full replay would give on an intact history;
   - `errors(found, accepted_text, committed, sealed=None) -> list[str]` (Decision 10): the one
     caller that verifies every digest;
   - `systems_that_passed(folder, artifact) -> set[str]`: the systems of every line whose
     `artifact` is the hash and whose replayed set holds the probe
     `tests/checks/test_v1_2_portable_and_sealed.py::test_guest_runs_here[plain]`. It replays
     with `verify=False`. **On a history that does not replay it returns the empty set**: `three
     systems` is then not met, and the intact check is what reports the broken history (the
     lane's ruling on the review's F4);
   - `OPS`, a counter of the digests computed, the bytes hashed for them and the JSON bytes
     parsed, which the unit tests read (criterion 12).

   `scoreboard.history_errors` and `scoreboard.systems_that_passed` move there; their callers
   (`needs._three_systems`, the two checks, the unit tests) follow. *Reason:* the format is read in
   four places (the intact check, three systems, rule 1, `accept`); one module keeps them from
   drifting. A digest sorts, serialises and hashes the whole passed set, so it costs as much as
   the set is large, not as the change is (the review, F2, counted on its prototype: one verified
   replay of 500 acceptances growing to 1,500 checks hashes 36,924,332 bytes; `accept` verifying
   every line at each of criterion 2's 500 acceptances would hash 7,540,480,222 bytes and parse
   1,045,123,016 bytes of JSON). So a judge run verifies every digest once, in the intact check;
   `accept` verifies one; `three systems` none. Without digests a replay is a set operation per
   id changed: 40,599 for the same 500 acceptances.
8. **`accept` builds a format-2 line; the plugin writes it where `target` says.**
   `scoreboard.accept` takes `history_lines: list[str]` (from `history.lines`) instead of
   `history_text`. `n` is their count plus one; `prev` hashes the last of them; the changes come
   from `history.last_passed` and the digest from the run's passes. A history that does not
   replay refuses the acceptance (`AcceptRefused`, naming the line). The plugin appends the line
   to `history.target(pdir, line)`, opened with `newline="\n"` (Decision 4), and prints
   `accepted: <that path> line <n>`. *Reason:* the line is still made in one place and
   written once, by the controller (spec 052, Decision 3); only where it goes is new.
9. **An oversize line is refused, not written.** When a line's UTF-8 length plus one exceeds
   `BUDGET`, `accept` raises `AcceptRefused("the history line would be <k> bytes, over the volume
   budget of 524288 (spec 062)")` and nothing is written. *Reason:* a file over the budget must
   never be written, even once. This happens only when more than about 6,000 checks change in one
   acceptance (the memo, finding 5: 15 times today's number of checks); a red line is the right
   answer then, and a later spec can split such a line.
10. **The intact check covers every volume.** `history.errors(found, accepted_text, committed,
    sealed=None)`. `found` maps the name of every file in the progress folder whose name starts
    with `history` to its bytes; `committed` maps the name of every volume in HEAD's tree to its
    committed bytes, or is `None` without git; `sealed` maps a volume's name to the SHA-256 its
    bytes must have (the intact check passes `history.SEALED`; unit tests pass their own or none).
    It reports, each as its own line:
    - a file starting with `history` whose name is not exactly `volume_name(n)` for some `n`
      (`history-60.jsonl`, `history-000060.jsonl`, `history-00001.jsonl`,
      `history-00060.jsonl.orig`): "unrecognised history file";
    - an empty volume, a missing `history.jsonl` while later volumes exist, and a volume whose name
      is not `volume_name` of its first line's `n`;
    - a blank line anywhere, and a volume that does not end with a newline (today's reader skips
      blank lines; from now on one is an error, since it shifts the byte offsets Decision 4
      measures; main's 59 lines hold none, EXECUTED);
    - a line with a `schema` key whose value is not the integer `2` (`3`, `"2"`);
    - an old-format line in any volume but `history.jsonl` (the review, F3: line 59 moved into a
      `history-00059.jsonl` ahead of volume 2 passed every other rule);
    - a volume named in `sealed` whose SHA-256 differs (so lines 1 to 59 are pinned byte for byte
      even against a committed rewrite);
    - everything today's check reports (a line not JSON, `prev` not hashing the line before, `n`
      not its place, the last line's `accepted` not the hash of `accepted.json`, `accepted.json`
      without a history or a history without it), across volumes;
    - a line that does not replay (Decision 7), a format-2 line that carries `passed`, and an
      old-format line after a format-2 line;
    - a format-2 line that ends past `BUDGET` in its volume, and a volume begun early (Decision 4);
    - a committed volume missing from the folder, and a committed volume whose text is not a prefix
      of the file's.

    `test_progress_history_is_intact` keeps its name and calls it with the real folder, every
    committed volume (from `git ls-tree --name-only HEAD -- context/progress/` and `git show`) and
    `history.SEALED`. It verifies every digest (Decision 7).
    *Reason:* today's check reads `history.jsonl` alone; an edit in a later volume would pass it.
11. **Rule 1 reads the newest volume.** `scan.acceptance_errors` finds the newest acceptance with
    `git rev-list -1 HEAD -- ':(glob)context/progress/history*.jsonl'`, takes the volumes in that
    commit's tree (`git ls-tree`), and reads the newest line from the newest volume, newest by
    number (Decision 1). An acceptance
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
    staged (EXECUTED in a scratch repository, finding 7). The glob also takes a stray
    `history-70.jsonl` into the commit (the review, F8); that does no harm, since the intact check
    is red on it ("unrecognised history file") and `--accept` refuses a red run first. The README
    says so in one line beside step 4.
13. **Nothing is migrated.** Lines 1 to 59 are not edited, moved or re-encoded. Spec 060's held
    line 60 (`24b16f8`) is not carried over: it was written by the old writer into
    `history.jsonl`. The lane re-makes that acceptance after 062 lands (How the lane lands it).
    *Reason:* the chain and the committed-prefix check exist so that no line is ever rewritten.

## Design

**`tests/harness/history.py`** (new; a judging file under `tests/`). Decisions 1, 4, 6, 7, 9 (the
size test is shared with `accept`), 10 and 12. Constants: `BUDGET = 1 << 19`, `FIRST =
"history.jsonl"`, `SEALED`, `PROBE` (the guest probe's node id, moved from `scoreboard`),
`ACCEPT_PATHSPEC`; the counter `OPS`.

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
  step 4 with Decision 12's two commands and the line on a stray volume name (F8); step 5
  unchanged. "Before a release" says "the history" for `history.jsonl`. A person can no longer
  read line N's passed set off the line, so the README gives the one-liner: `uv run python -c
  "import sys; sys.path.insert(0, 'tests'); from harness import history, paths; print(sorted(list(
  history.passed_sets(history.lines(paths.PROGRESS)))[N - 1]))"` (the review, F10).
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
  checks (INFERRED). The review counts 288 bytes a check (111,711 bytes of checks for 388) and,
  at the pace of lines 1 to 59 (14 to 374 passing checks in two days), puts 3,500 checks weeks
  away, not years (F9, INFERRED). The size rule will say so first. That is a later spec's
  question, and its research memo should be opened now; this spec does not change
  `accepted.json`.
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
   `passed_removed`, then a large `passed_added`); on some runs the probe fails; and at least one
   artifact's expected systems are a strict subset of the three: one system's every run on it
   fails the probe, after the probe passed on an earlier line (the review, F6). It asserts:
   - volume 1's bytes are unchanged;
   - every file in the folder is at most `1 << 20` bytes, and every format-2 line ends at an offset
     of at most `BUDGET` in its volume;
   - there are at least 3 volumes, each named after its first line, and `n` runs from 1 to the last
     line without a gap;
   - `history.errors(…)` is empty, with `committed` set to the folder as it stood halfway through
     (every committed volume a prefix);
   - at every line, the replayed set (`history.passed_sets`) equals that simulated run's passes;
   - for every artifact hash, `history.systems_that_passed` equals the systems computed directly
     from the simulated runs, and for the strict-subset artifact that answer lacks the failing
     system.

   It records in the landing notes `history.OPS` for the whole test: digests computed, bytes
   hashed for them and JSON bytes parsed (a count decides whether it fits the fast tier, never a
   time).

   *Stand-ins:* (a) today's writer (one file, full lists: `history.jsonl` passes `1 << 20` at the
   first ten new lines); (b) a roll decided after writing (a volume ends past `BUDGET`); (c) volumes
   numbered by count (`history-00002.jsonl`) instead of first line; (d) a replay that ignores
   `passed_removed` (credits the strict-subset artifact's failing system; the per-line set
   assertion fails too).
3. **Main's 59 lines stay valid as they are.** `test_progress_history_is_intact` passes on the
   real folder at the built commit (lines 1 to 59, old format, `history.jsonl` alone, with
   `accepted.json`), and `history.passed_sets` replays them to the same sets as their `passed`
   lists. On the built branch, `git diff f6b3f75 -- context/progress/history.jsonl
   context/progress/accepted.json` prints nothing, and no file matching
   `context/progress/history-*.jsonl` exists (the review, F1: the README in the same folder is
   edited by this build, so the folder's diff is not empty). *Stand-ins:* an `errors` that
   requires format-2 keys on every line fails on the real file; so does one whose `SEALED` hash
   is off by one hex digit.
4. **Tampering is caught in every volume.** `tests/unit/test_history.py`, from a valid synthetic
   history of three volumes, one case per change, each giving its named error and no error on the
   untouched history: (a) one byte changed in a middle line of volume 2; (b) volume 2 deleted; (c)
   volume 3 renamed one number higher; (d) stray files `history-00070.jsonl.orig`,
   `history-70.jsonl`, and the non-canonical `history-000060.jsonl` and `history-00001.jsonl`
   (each "unrecognised history file"); (e) a line appended to volume 1 after volume 2 exists; (f) volume 3 begun
   early (its first line would have fitted in volume 2); (g) a format-2 line pushing its volume past
   `BUDGET`; (h) the last line's `passed_added` edited so it no longer replays to its digest (no
   later line chains to it, so only the digest catches it); (i) an old-format line after a format-2
   line; (j) a format-2 line that also carries `passed`; (k) `accepted.json` edited; (l) the last
   old-format line moved out of volume 1 into a volume of its own named after it, ahead of the
   format-2 volumes, with the chain, `n` and names all still holding (the review's P6: only
   "an old-format line outside history.jsonl" reports it, and `sealed` reports volume 1's new
   hash); (m) a blank line in volume 2, and volume 3 without its final newline; (n) a line with
   `"schema": 3` and one with `"schema": "2"`; (o) volume 1 changed while `sealed` names its old
   hash. The volumes are found in numeric order: a history whose volumes include
   `history-99999.jsonl` and `history-100000.jsonl` replays in that order. *Stand-ins:* today's
   `history_errors` on `history.jsonl` alone reports none of (a) to (d), (f) to (j) and (l) to
   (n); an `errors` without the old-format rule misses (l) when `sealed` is not given; a
   `volumes` sorted by name fails the numeric-order case.
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
   (e) the newest commit touching a volume deletes one (the newest volume removed, `accepted.json`
   put back): reported, as a change to a volume that is not its newest and as a line that judged
   an older commit. *Stand-in:* today's `acceptance_errors` (it follows `history.jsonl`, keeps
   judging line 59's commit, and reports neither (b), (d) nor (e)).
10. **The lane's commit command does what the README says.** `tests/unit/test_landing_lane.py`:
    in a scratch repository with a committed `history.jsonl`, a new volume, a changed
    `accepted.json`, a changed `context/progress/README.md` and another staged file, the two
    commands of Decision 12 (built from `history.ACCEPT_PATHSPEC`) make a commit holding exactly
    `accepted.json` and the new volume, and leave the other two changes uncommitted; and
    `context/progress/README.md` contains both commands verbatim. *Stand-in:* today's step 4
    (`git commit -- …accepted.json …history.jsonl`) exits non-zero on the untracked volume, or,
    once added, leaves it out.
11. **Each caller verifies only what it must (the review, F2).** `tests/unit/test_history.py`, on
    criterion 2's history (or one of at least 200 format-2 lines), reads `history.OPS` around each
    caller: `history.errors` computes exactly one digest per format-2 line; `scoreboard.accept`
    computes at most 2 (the newest line's check and the new line's own), with a cold cache and
    with a warm one, and with a warm cache parses no JSON of earlier lines; `systems_that_passed`
    computes 0. The landing notes record the counts. *Stand-ins:* (a) an `accept` that verifies
    every line's digest (its count equals the format-2 line count); (b) a `systems_that_passed`
    that replays with `verify=True`; (c) `errors` with `verify=False` (0 digests: criterion 4(h)
    fails too).
12. **`three systems` on a broken history is not met; the intact check says why.**
    `tests/unit/test_history.py`: on criterion 6's folder with one line made not to apply (an
    `added` id already in the set), `systems_that_passed` returns the empty set without raising,
    and `history.errors` names that line. *Stand-in:* a `systems_that_passed` that lets the
    `ValueError` out.
13. **Green.** `ruff check`, `ruff format --check`, `uv run pytest -m "not slow" -n 3` and the full
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

## Disposition of the pre-build review

The review (`062-the-progress-history-stays-small-spec-2026-10-18.md`, by a fresh agent, at
`3b81107`): "ready to build once F1 to F3 are written in". The lane checks this write-in itself;
there is no second spec review.

- **F1 (Medium), criterion 3's diff could never be empty.** Written in: criterion 3 now diffs
  `history.jsonl` and `accepted.json` only, and requires that no `history-*.jsonl` exists on the
  built branch.
- **F2 (Medium), replay verified every digest, and `accept` made criterion 2 quadratic.** Written
  in: `passed_sets(lines, verify=True)`; only `errors` verifies every digest; `accept` goes through
  `history.last_passed`, which checks the newest line's digest alone and keeps a one-entry cache
  keyed by the newest line's hash; `systems_that_passed` verifies none (Decision 7, whose reason
  is corrected with the review's counts). New criterion 11 counts the digests per caller, and its
  stand-in "accept verifies every line" fails it. Criterion 2 records `history.OPS`.
- **F3 (Low-Medium), an old-format line could live in a later volume.** Written in: Decision 1
  (old-format lines only in `history.jsonl`; `SEALED` pins its SHA-256,
  `0a99162a…1120`, as confirmed by `shasum -a 256` on `f6b3f75`), Decision 10 (both reported),
  criterion 4(l) and 4(o).
- **F4 (Low), names, order, schema, blank lines, a broken history.** Build conditions, written into
  Decisions 1, 7 and 10 and criteria 4(d), 4(m), 4(n), the numeric-order case and criterion 12.
  The lane's ruling: `systems_that_passed` on a history that does not replay returns the empty
  set, and the intact check is what reports it.
- **F5 (Low), bytes, not characters.** Build condition, written into Decisions 4 and 8: the plugin
  writes with `newline="\n"`; `target` and `errors` measure with `read_bytes()`.
- **F6 (Low), sharper criteria.** Build condition, written in: criterion 2 compares the replayed set
  with that run's passes at every line and includes an artifact that passed on fewer than three
  systems; criterion 9(e) is a commit that deletes a volume.
- **F7 (Info), the digest is a consistency check.** Written into Decision 6.
- **F8 (Info), the glob takes a stray `history-70.jsonl`.** No design change; one line in the
  README's step 4 (Decision 12).
- **F9 (Info), the two side notes.** Agreed: the four spec-023 checks are 023's follow-up, and the
  builder judges with the artifact set; `accepted.json` is scoped out, with the review's numbers
  (Scope).
- **F10 (Info), documents.** Written into Design: "Before a release" says "the history", and the
  README gives the one-liner for line N's passed set. `tests/unit/test_several_cores.py` needs no
  edit.

## Landing notes

**Built 2026-10-18** on `spec/062-the-progress-history-stays-small`, from the confirmed spec
(`6fdd1fd`), by the drafting agent. Not accepted and not pushed: only the lane accepts. Every
judge run used the frozen set `build/sets/s-8eb9e35734deeb21` of the main tree
(`WASI_PYTHON_ARTIFACTS`). Logs are in the worktree's git-ignored `build/` (`062-*.log`).

**What was built.** `tests/harness/history.py` (new): the volume rules, `passed_sets(lines,
verify=True)`, `last_passed` with its one-entry cache, `target`, `errors`, `systems_that_passed`,
`SEALED`, `ACCEPT_PATHSPEC` and `ACCEPT_COMMANDS`, and the counter `OPS`. `scoreboard.accept`
takes `history_lines`, writes format 2, and refuses an oversize line or a history that does not
replay. The plugin writes to `history.target` with `newline="\n"` and prints the volume's path.
`needs._three_systems`, `test_same_bytes_passed_on_three_systems`,
`test_progress_history_is_intact` (every volume, every committed volume, `SEALED`) and rule 1
(`scan.acceptance_errors`) read every volume. The checks are `tests/unit/test_history.py` (30)
and new cases in `test_plugin.py` (2) and `test_landing_lane.py` (7); the old tests of the moved
functions in `test_scoreboard.py` and `test_plugin.py` now call `history`. Documents:
`context/progress/README.md` (the history in volumes; the line-N one-liner, run once on line 59;
step 4's two commands and the stray-name line; "Before a release" says "the history"),
`context/README.md`, and one amendment each in specs 002 and 029.

**The checks came first.** On main's harness, `tests/unit/test_history.py` fails at import
(`ImportError: cannot import name 'history' from 'harness'`), and so do the new cases in
`test_plugin.py` and `test_landing_lane.py`, which import it.

**Each criterion's evidence.**
1. `test_a_line_records_what_changed_not_every_pass`: a line after 5,000 unchanged passes is
   under 4,096 bytes. It has no `passed`, and it names exactly the 10 ids added and the 3 removed.
2. `test_many_more_acceptances_*`: volume 1 is a 1,020,789-byte look-alike, followed by 500
   acceptances as the checks grow to 1,500. Volume 1's bytes are unchanged. Every file is at most
   `1 << 20` bytes, and every format-2 line ends within `BUDGET`. There are at least 4 volumes,
   each named after its first line. `errors` is empty against the halfway commit and the seal. The
   replayed set equals the run's passes at every line. `systems_that_passed` equals the direct
   answer for every artifact, and for `art5` it is `{darwin, win32}`, because linux failed the
   probe on every run.
3. `test_progress_history_is_intact` passes on main's 59 lines (`history.jsonl` alone), and
   `test_mains_lines_replay_to_their_passed_lists` passes. On the built branch, `git diff f6b3f75
   -- context/progress/history.jsonl context/progress/accepted.json` prints nothing (0 bytes), and
   `context/progress/` holds no `history-*.jsonl`. The judge runs below left both files' SHA-256
   unchanged (`build/062-progress-before.txt`).
4. Cases (a) to (o) and the numeric-order case each give their named error, starting from a
   history that is clean. Also added: a volume's first line whose `n` is not a number is reported,
   not raised. Without the fix, that check failed with `ValueError: Unknown format code 'd'`.
5. `test_committed_volumes_only_grow`.
6. `test_three_systems_reads_every_volume`: `{darwin, linux, win32}` for A, and nothing for B.
7. `test_accept_starts_a_volume_when_the_newest_is_full_and_says_where`: lines 61 and 62 go to
   `history-00061.jsonl`. The run prints the path, `history.jsonl` keeps its bytes, and the volume
   holds no `\r`.
8. `test_an_oversize_line_is_refused_*`, both through `accept` and through the plugin: the run is
   red and nothing is written.
9. Cases (a) to (e) in `test_landing_lane.py`.
10. `test_the_lanes_commit_takes_exactly_the_acceptance` and
    `test_the_readme_quotes_the_lanes_commit_commands`.
11. `test_each_caller_computes_only_the_digests_it_must` (counts below).
12. `test_three_systems_on_a_broken_history_is_not_met`.

**The stand-ins** were applied as scratch copies of the module, swapped into the live module by a
small pytest plugin kept in the session's scratchpad. They were never committed. Each run is
logged in `build/062-standins.log`, and every one fails its checks:
- C1a, today's `accept`: the line is 435,570 bytes. C1b, a change taken against `accepted.json`:
  435,696 bytes.
- C2a, today's writer: volume 1's bytes change. C2b, a roll decided after writing: line 210 ends
  at byte 576,044 of `history-00060.jsonl`. C2c, volumes numbered by count: the volume is named
  `history-00002.jsonl` where `history-00060.jsonl` was expected. C2d, a replay that ignores
  `passed_removed`: the three-systems answer is wrong (it fails at artifact `art` with the empty
  set, because a later `passed_added` no longer applies).
- C3a, format-2 keys required on every line: "history line 1: no schema" from the real intact
  check. C3b, `SEALED` off by one digit: "history.jsonl is not the sealed volume".
- C4a, today's check on `history.jsonl` alone: 15 cases error in their fixture, because it calls
  the untouched three-volume history red, and the old-format move fails. C4b, no old-format rule:
  `[]` for case (l). C4c, volumes sorted by name: `history-100000` comes before `history-99999`.
- C5, a committed check on `history.jsonl` alone: volume 2's loss is missed.
- C6a and C6b: `{'darwin'}`. C6c: `{'darwin', 'win32'}`.
- C7, today's plugin: no `accepted: …history-00061.jsonl line 61` line is printed.
- C8: "DID NOT RAISE AcceptRefused", twice.
- C9, today's `acceptance_errors`: (b), (c), (d) and (e) fail ("DID NOT RAISE"); (a) holds, as it
  should.
- C10, today's pathspec: the commit holds only `accepted.json`, and the README check fails.
- C11a, an `accept` that verifies every line: 502 digests. C11b, a three-systems read that
  verifies: 500 digests. C11c, `errors` without verifying: 0 digests where 500 were expected, and
  4(h) fails.
- C12: the `ValueError` gets out.

**F2's operation counts** (from `history.OPS`, printed by the checks):
- Criterion 2's 500 acceptances, while writing:
  - 999 digests: each acceptance's new line, plus the check of the newest line's digest, which the
    first acceptance skips because volume 1's newest line is old-format;
  - 81,137,136 bytes hashed;
  - 3,350,033 JSON bytes parsed.
  The review projected 7,540,480,222 bytes hashed and 1,045,123,016 parsed if `accept` verified
  every line on every call.
- One intact check of that history: 500 digests (one per format-2 line), 40,569,438 bytes hashed,
  3,479,741 bytes parsed.
- `accept` with a cold cache: 2 digests and 10,440 bytes hashed. It parses the whole history once
  (3,479,741 bytes) and checks no earlier digest.
- `accept` with a warm cache: 2 digests. It parses only the newest line, 7,656 bytes.
- `systems_that_passed`: 0 digests, 3,479,741 bytes parsed.

**The volume rotation, shown in a scratch copy.** `context/progress/` was copied to the
scratchpad. Then `uv run pytest -m "not slow" -n 3 --progress-dir=<copy>
--progress-latest=<copy>/latest.json --accept=… --accept-judge=… --partial=…` was run against
the set. It is allowed in a worktree because the folder is not the repository's (spec 029). It
ended with `accepted: <copy>/history-00060.jsonl line 60`:
- `history.jsonl` is still 1,037,524 bytes, and its SHA-256 equals `SEALED`;
- `history-00060.jsonl` is 5,450 bytes, and line 60's `prev` hashes line 59;
- `history.errors` over the copy, with `f6b3f75`'s `history.jsonl` as committed and `SEALED`,
  returns `[]` (`build/062-rotation-verify.txt`).

Line 60 removed 48 ids: the slow checks that the fast tier deselected. The lane's serial,
unnarrowed acceptance will remove none of them. That line is larger than 2 KB mostly because its
`judge_changed` names 11 files.

**The judge lines.**
- The fast tier, `uv run pytest -m "not slow" -n 3` (`build/062-build-fast-2.log`): exit 0, 1500
  passed, 26 skipped. `wasi_python v1: 326/390 pass · 0 gap · 18 blocked · 0 fail · 46
  deselected (unit suite 1174/1182, 8 skipped)`; rules 25/26, blocked 1.
- The full judge, `uv run pytest`, serial, without `--accept` (`build/062-full-judge.log`): exit 0,
  1512 passed, 58 skipped, 2 xfailed:
  `wasi_python v1: 338/390 pass · 2 gap · 50 blocked · 0 fail (unit suite 1174/1182, 8 skipped)`
  `ratchet vs 7c3d606d09: lost 0 · absent 0 · unrun 0 · unrun locally 36 · gained 0 · grew 0 ·
  upstream unrun 31 · judge changed: tests/checks/test_rules.py,
  tests/checks/test_v1_2_portable_and_sealed.py, tests/harness/history.py and 8 more`.
  The only blocks are local tooling this worktree lacks: the source trees, the upstream kit, the
  oracle, the prior-art clones, `wheel`, and `three systems` (which main's history has never met).
  The run is red only by `judge changed`, which the lane accepts with `--accept-judge`.
  `history.jsonl` and `accepted.json` kept their SHA-256 (`shasum -a 256 -c
  build/062-progress-before.txt`: both OK), and no volume was created.
- `ruff check` and `ruff format --check` on `src`, `tests` and `recipes/guest` are clean.

One line: new history lines store only what changed in the passed set, and the history continues
in files named by their first line, each under half the limit, chained as one, with lines 1 to 59
untouched.
