# The progress history stays small

- **Status:** executed, 2026-10-18 (time box: under an hour). Nothing in the repository was changed by it. The two scratch scripts lived in the session's scratchpad and are described below; their numbers are reproducible from `context/progress/history.jsonl` at main `f6b3f75`.
- **Owner:** Clay Gendron
- **Researcher:** the drafting agent (Claude Opus 5.5) of spec 062.
- **Asked by:** the lane, 2026-10-18: spec 060's acceptance (`24b16f8`, held off main) made `history.jsonl` larger than the tracked-file limit, so every landing is blocked.
- **Feeds:** `../specifications/062-the-progress-history-stays-small.md`.
- **Stands on:** spec 002 (the progress harness: the history, its chain, `three systems`), spec 029 (the lane's guards; rule 1 reads the newest history line), spec 052 (the controller alone writes the acceptance).

## The question

`context/progress/history.jsonl` gets one line per acceptance. It is append-only and hash-chained. The rules check `test_no_artifact_or_large_file_is_tracked` refuses any tracked file over `1 << 20` bytes (1,048,576). The history has just crossed it. How does the history keep every reader working, keep its tamper-evidence, keep lines 1 to 59 verifiable, and stay under the limit however many acceptances and checks come?

## What was found

1. **The numbers (EXECUTED).** At main `f6b3f75` the file is 1,037,524 bytes and 59 lines (`wc -c`, `wc -l`). That leaves 11,052 bytes. The held acceptance `24b16f8` makes it 1,071,294 bytes (`git cat-file -s 24b16f8:context/progress/history.jsonl`); its line 60 is 33,770 bytes. `git merge-base --is-ancestor 24b16f8 main` says it is not on main.

2. **What makes a line big (EXECUTED).** One field: `passed`, the sorted node ids of every check that passed in that run. Line 1 is 1,579 bytes, of which `passed` is 1,030 (14 ids). Line 31 is 16,362 bytes, `passed` 15,410 (182 ids). Line 59 is 33,757 bytes, `passed` 32,549 (374 ids). Without `passed`, line 59 is 1,196 bytes. A node id averages 83 bytes. So a line grows by about 87 bytes per passing check, and the file grows by the whole list at every acceptance. Nothing else in a line is over 250 bytes (`growth_reason` at 247 on line 59).

3. **Who reads `passed` (READ).** Only `scoreboard.systems_that_passed`, for the need and the check `three systems` (`needs._three_systems`, `test_same_bytes_passed_on_three_systems`). It asks whether the guest probe `test_guest_runs_here[plain]` passed on one artifact hash, per system. The other readers of the history use other fields: the chain check (`history_errors`: `prev`, `n`, the last line's `accepted`, the committed prefix), rule 1 (`scan.acceptance_errors`: the newest line's `n`, `commit`, `dirty`), `accept` (the last line, for `prev`, and the line count, for `n`), and the plugin's `accepted: … line N`. The ratchet reads `accepted.json` only. Nothing under `scripts/`, `src/` or `.github/` reads the history (`grep -rln`).

4. **The passed set changes little between acceptances (EXECUTED).** Replaying lines 1 to 59 and taking each line's set difference from the line before: most acceptances add 0 to 24 ids and remove 0 or 1. Every line so far was accepted on `darwin-arm64`. A line that kept every field except `passed`, and added the ids gained, the ids lost and a SHA-256 of the full sorted set, would have been 994 to 5,193 bytes; the 59 lines would total 110,218 bytes against 1,037,524 (9.4 times less).

5. **Projection (EXECUTED, a model).** A scratch model appended 500 more acceptances while the checks grew from 392 to 1,390 (two per acceptance), rolling to a new file whenever the next line would push the current one past 512 KiB. With full `passed` lists it made 83 files. With the gained-and-lost form it made 2. A single line can list about 6,010 ids before it alone would pass 512 KiB (`(524,288 − 1,196 − 200) / 87`): the worst case is one run in which that many checks change at once.

6. **Compression (EXECUTED).** `gzip -9` of the 59 lines is 42,240 bytes. The lists compress well because each repeats the one before.

7. **git and a new file (EXECUTED, git 2.51.0, in a scratch repository).** `git commit -m x -- <path>` refuses a path git does not know yet ("did not match any file(s) known to git"). After `git add -- context/progress/accepted.json ':(glob)context/progress/history*.jsonl'`, the command `git commit -m acc -- context/progress/accepted.json ':(glob)context/progress/history*.jsonl'` committed exactly those two changes and left out a modified `README.md` in the same folder and an unrelated staged file. `git rev-list -1 HEAD -- ':(glob)context/progress/history*.jsonl'` found that commit.

## The options

- **(a) Volumes.** Lines 1 to 59 stay in `history.jsonl`, unchanged and sealed. Later lines go to further files in the same folder, each under a budget, the chain continuing across them. Line numbers stay global. *Needed whatever else is done*: volume 1 has 11,052 bytes left and cannot be edited, so any fix starts a new file. Alone, it keeps each file small but makes a new file every 15 acceptances today and every 6 at 1,000 checks (finding 5's 83 files).
- **(b) Smaller lines.** New lines record the passed set as what changed since the line before, plus a digest of the whole set. A reader replays from line 1. Same information, same tamper-evidence (the digest pins the replayed set at every line). Alone, it does not work: volume 1 has room for only about five more such lines.
- **(c) Others considered.**
  - *Raise or exempt the limit for this file.* Refused by the brief and by the reason for the rule: the file would grow without bound.
  - *Compress the history* (finding 6). A binary file in git, unreadable in a diff, not greppable for "history line 56", and the committed-prefix check would have to decompress.
  - *A file per acceptance* (`runs/0060.json`). Unbounded file count, and a rename or deletion is harder to see than a broken chain.
  - *Drop or archive old lines behind a checkpoint digest.* Lines 1 to 59 must stay verifiable as they are.
  - *Keep the history outside the tree* (git notes, a release asset). The committed-prefix check and rule 1 read committed files; notes are not pushed by default.
  - *Record only the probe's result* instead of the passed set. Smaller still, but it throws away what the history is for: which checks held at each acceptance.

## Recommendation (INFERRED)

Take (a) and (b) together. Volumes give the bound per file and leave lines 1 to 59 byte for byte as they are. Smaller lines keep the number of volumes small as checks grow (finding 5: 2 files instead of 83). Keep `n` global, so a landing note still cites "history line 60". Name each volume after its first line, so a reader finds line N without opening files. Keep the size rule as it is. Spec 062 writes the details.

One line: the passed list is 96% of a history line, so new lines store only what changed, and the history continues in numbered files, each under half the limit, chained as one.
