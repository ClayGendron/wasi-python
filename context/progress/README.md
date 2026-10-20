# /context/progress

The accepted state of the progress harness
(`../specifications/002-the-progress-harness.md`). Written only by
`uv run pytest --accept "<reason>"`, never by hand.

- `accepted.json`: for each v1 check, its last accepted status, the
  commit and artifact it was seen on, and its metrics (fuel, bytes)
  per platform, plus the hash of every judging file.
- **The history**: one line per acceptance, append-only, in volumes
  (spec 062). Each line carries the hash of the line before it and of
  the `accepted.json` it wrote, so `test_progress_history_is_intact`
  notices a hand edit or a rewritten line.

## The history in volumes (spec 062)

The history is one hash-chained sequence of lines, kept in several files so that no tracked file
passes the rules check's limit of `1 << 20` bytes.

- **Volume 1 is `history.jsonl`**: lines 1 to 59, sealed. Its SHA-256 is pinned in
  `tests/harness/history.py` (`SEALED`), and nothing is ever appended to it again.
- **Every later volume is named after its first line**: `history-00060.jsonl` begins with line 60.
  Line numbers are global, so a landing note cites "history line 61" as before, and may add the
  volume the `accepted:` line printed. To find line N, take the volume with the largest first line
  not above N.
- **A volume rolls only when full.** A new line goes to the newest volume while that volume stays
  within `BUDGET` (`1 << 19` bytes, half the limit); otherwise it begins a new volume. The intact
  check holds it both ways: no line past the budget, no volume begun early.
- **New lines record a change.** Lines 1 to 59 carry the full `passed` list. A line written since
  spec 062 has `"schema": 2`, the node ids that started passing (`passed_added`) and stopped
  passing (`passed_removed`) since the line before, and a digest of the whole passed set
  (`passed_digest`). A line's passed set is found by replay from line 1. The digest catches an
  inconsistent change, not a forgery: what catches a deliberate edit is the chain, the
  committed-prefix check and rule 1.
- **Only the intact check verifies every digest.** `--accept` checks the newest line's, and
  `three systems` none. On a history that does not replay, `three systems` is not met, and the
  intact check says why.

Line N's passed set:

```
uv run python -c "import sys; sys.path.insert(0, 'tests'); from harness import history, paths; print(sorted(list(history.passed_sets(history.lines(paths.PROGRESS)))[N - 1]))"
```

## How to read a run

`uv run pytest` ends with the scoreboard:

```
wasi_python v1: 14/67 pass · 8 gap · 45 blocked · 0 fail   (unit suite 115/115)
  v1.1  artifact set         0/15  blocked 15
  …
blocked by: artifact dir 37 · runner 3 · …
gaps close with: 2026-10-16-reproducible-builds-on-linux 5 · …
next: context/specifications/001-the-neutral-host-door-and-the-runner.md (unblocks 40, closes 1)
ratchet vs 2828f2cced: lost 0 · absent 0 · unrun 0 · gained 0 · grew 0
```

- **pass**: the check ran and held.
- **gap**: it fails exactly as `tests/known_gaps.toml` says, and that
  entry names the document that will fix it.
- **blocked**: a named prerequisite is missing (an artifact, the
  runner, a source tree). The `next:` line names the document that
  provides the most of them.
- **fail**: anything else. The run is red.

The ratchet compares the run with `accepted.json`. A pass that is
lost, a check that disappears, or fuel or bytes that grow turns the
run red. A pass that becomes blocked is red too, unless the run says
`--partial "<why>"` (for example, a machine without artifacts).

### numpy's and pandas' own tests (spec 050)

`tests/checks/test_v1_3_upstream_suites.py` runs upstream's own tests in the guest, one check
per group. Each group check records a third metric, **`passes`**: how many upstream tests
passed.
- **It must not fall.** A lower value than the accepted one goes to its own list, `fewer`,
  printed `FEWER <node>: passes <old> -> <new>` before any `GREW` line and never cut. The run is
  red.
- **Its own flag.** Only `--accept-fewer-passes "<why>"` accepts a fall; the reason goes into the
  history line's `fewer_reason`. `--accept-growth` never does: an unrelated growth must not carry a
  lost pass.
- **A rise** is reported as `more`, not as `gained`. Without the flag, acceptance keeps the
  higher value.
- **A substitution** (one test from pass to skip, another the other way) keeps the count. Each
  group's `passed_digest` in `build/progress/latest.json` shows it; it is reported, not ratcheted.

Known failures are classes, each its own check and an ordinary gap. Their allowances are judge
files, like `tests/known_gaps.toml`: `tests/upstream/*.toml` (the classes' expressions, the
traps, the files not selected) and `tests/upstream/expected/<group>/<class>.txt` (each class's
node ids). An edit to any of them is a judge change, and `git diff` names each test admitted or
released. CPython's own tests (spec 065) are upstream checks like numpy's, with the same
`passes` metric, flag and refusal; their plan, `tests/upstream/python/<group>.txt`, is judged too,
and `tests/upstream/python.toml` adds three kinds of entry, each a gap: tests deselected by id,
modules allowed one named kind of environment change, and results recorded per host. The
compiled packages' own tests (spec 066) are upstream checks too, each package a family with its
own grant (`/upstream-<package>`), stage and budget; a file too big for one group is split by a
`[[split]]` of ordered `-k` expressions, each split group recording its file's collected count as
the fact `collected`.

A class or trap that is fixed: its check passes and its gap says "remove the gap". A fixed class
stays, with an empty list file, as a passing check. A fixed trap's `[[trap]]` entry is removed in
the same landing, its tests rejoin their group, and its now absent check is retired with
`--retire` (an accepted gap whose check is absent is reported `absent`, as a pass is).

The checks need the source trees, the frozen artifacts and the test kit
(`uv run python tests/upstream/fetch.py`). Without them they are blocked, which is local tooling
and not red. But **`--accept` refuses** while any of them with an accepted pass or gap did not run
here, unless `--partial "<why>"` is given.

A **fuel fact** (spec 091, `[[fuel_fact]]` in `tests/upstream/numpy.toml`) is a test whose fuel
measures where a type object sits in memory, not the product: today one, numpy's
`test_string_comparisons`, whose fuel moves with the `bool` type's address at every rebuild. Its
cases leave their group's session and run in one of their own inside the group's check. Their
outcomes still count: the group's `passes`, classes and `passed_digest` are what one session
gives. Their fuel is not in the group's `fuel` metric: it is the fact `fuel_facts` in
`latest.json`, red only at its cap (at least twice its fuel when measured), and compared between
two runs of one commit by `sameness.py` to the ratchet's tolerance. A build-class landing's notes
quote it in one clause. A move of more than 10% from the last quoted value gets one sentence of
cause from the reviewer; when the quoted fact exceeds half its cap, that landing raises the cap or
its reviewer says why not. The group's own fuel stays ratcheted and may still grow by a residual
that needs its reason.

## Flags

| flag | what it does |
|---|---|
| `--accept "<reason>"` | record this run; refused unless green with no loss |
| `--accept-judge "<reason>"` | also accept a change to the judging files |
| `--accept-growth "<reason>"` | also accept fuel or bytes growth |
| `--accept-fewer-passes "<reason>"` | also accept a fall in an upstream group's `passes` (spec 050) |
| `--partial "<reason>"` | allow accepted passes to be blocked here |
| `--retire <node id>` | with `--accept`: drop a check from the protected set |
| `-m "not slow"` | the fast tier: skip the golden jobs and the oracle |
| `-n 6` | run on six cores (spec 052): the same verdicts, about a third of the time |

The full record of the last run is `build/progress/latest.json`.

## Several cores (spec 052)

`uv run pytest -n 6` runs the judge on six cores with pytest-xdist (pinned in `uv.lock`). Its
answer is the serial answer: every status, need, fact and `bytes` and `passes` value, the unit
tally, the deselected list and the collected files are equal; fuel differs by no more than serial
runs differ between themselves, far inside the ratchet's 0.01%. On darwin-arm64 (10 cores) the
full judge took about 3 minutes against about 10 serially. Use `-n 3` when another agent's judge
is running on the machine (a `-n 6` run peaks near 10 GiB), and `-n auto` on another machine.
The plain `uv run pytest` stays serial.

- **How it stays the same.** The workers collect and run; each check's record is made on its
  worker exactly as in a serial run and rides to the controller on its report. Workers write
  nothing and run none of the lane's guards: the controller alone writes `latest.json`, judges the
  ratchet and accepts. An upstream group's check and its classes' checks always run in one
  worker (the judge's own scheduler; node ids are unchanged). A worker that dies is not replaced:
  the check it was running is `fail`, named "worker crashed", and the run ends; when no worker
  finishes at all, a red line says the record is incomplete. Each worker also
  reports what steered it from outside the judge (a conftest loaded only while collecting), so a
  parallel run is red exactly when a serial one is.
- **What the record says.** `meta.workers` is the number of workers started (`0` serially) and
  `meta.scheduler` the scheduler xdist used (`JudgeScheduling`; `null` serially). Neither is
  compared.
- **One way to run in parallel.** Allowed: `-n <number>`, `-n auto`, `--maxprocesses`,
  `--max-worker-restart 0` (the judge sets it), `--dist load`, `--loadscope-reorder`,
  `--testrunuid`. Refused before anything runs, exit 1 with one line: `-n logical`, any other
  `--dist`, any other `--max-worker-restart`, `-d`,
  `--no-loadscope-reorder`, `--maxschedchunk`, `--tx`, `--px`, `--rsyncdir`, `--rsyncignore`,
  `-f`/`--looponfail`. The ini keys `rsyncdirs`, `rsyncignore` and `looponfailroots` would come
  only from `pyproject.toml`, which is judged, and do nothing without the refused options.
- **Comparing two runs.** `uv run python tests/harness/sameness.py A.json B.json` prints every
  difference that could change a verdict (the fields above; a gap's or a blocked check's reason,
  not a pass's note, which may print a fuel count; fuel beyond the ratchet's tolerance; what
  steered the run from outside the judge, `meta.foreign`) and exits 1 when there is one. Fuel is
  compared between records of one platform only, as the ratchet keys it (spec 092).

### Comparing with a release record, and claim lists (spec 092)

- **A release record is either side.** The release workflow's gather job writes the merged record
  as the artifact `release-record-<attempt>`: `gh run download <id> -n release-record-1 -D
  build/<spec>/ci/`, then compare `build/<spec>/ci/record.json`. Sameness reads it as the darwin
  run it contains: each check as the darwin shard that ran it saw it (else Linux's, else
  Windows'), and the suite of the build and macOS shards together (against a local record, only
  its total and failing count: a unit test may skip on one host only). A check no shard ran
  (blocked by a need CI lacks, such as the oracle) is not compared, nor is fuel a Linux or Windows
  shard gave (G5 holds darwin fuel only, and Linux fuel moves between runs); stderr counts both.
  A check whose worst status on some system is not its darwin one is always a difference, which no
  claim explains (`<check>: status 'pass' on darwin-arm64, 'fail' on win32-amd64`), unless it is a
  block by a need CI lacks on a system that lacks it (the descriptor limit, on Windows). A record
  from a run before spec 092 (or before its build review) lacks the fields and is refused, exit 2,
  and so is a check with no source that some shard ran. **Compare only the record of a run whose
  every job, the gather included, is green.**
- **`--claims <toml>`** prints only the differences no claim explains, and exits 1 if any remain.
  A claim list is what the **second** record has that the **first** lacks, so put the record
  without the claimed changes first (a reviewer's or builder's record, then the lane's). Each
  specification writes its block in "For the lane"; a wave's file is the blocks one after
  another. `--except <spec>` drops a spec's claims (the entry whose record is the first: its
  changes are in both). stderr says how many differences each spec explained and which claimed
  entries matched nothing.

  ```toml
  [[claim]]
  spec = "092"         # required
  new = []             # checks or files added: explains "only in the second record"
  retired = []         # checks or files removed: explains "only in the first record"
  changed = []         # checks whose status, need, reason, closer, area, facts or metric names move
  passes = []          # upstream checks whose passes (and passed_digest) move
  grows = []           # checks whose fuel or bytes move
  growth = ""          # required with grows: the reason
  units = 0            # unit tests added; the suite line is explained when the total moved by
                       # exactly the claims' sum and no more unit tests fail
  ```

  An entry with `::` is a check; one without is a file and stands for its checks; a trailing `*`
  is a prefix (`"*"`: every row). A claim explains only its own kind: `grows` never explains a
  status, `new` never a check that went away. `meta.foreign` is never explained.

## The landing lane (spec 029)

Only the lane accepts: in the main tree, on a clean tree, and on a detached HEAD, so main
moves only by fast-forward onto an acceptance already checked. The judge enforces three of
these things:
- `--accept` is refused before collection in a linked worktree whose run would write a
  `context/progress` folder.
- It is refused on a tree with a change the judge could see: any tracked change outside
  `context/progress/`, or an untracked file under `src/`, `tests/`, `scripts/`, `recipes/`,
  `context/specifications/`, `context/reviews/` or `context/upstream/`, or a judging file.
- It is refused again when the acceptance is written, if the tree changed or HEAD moved during
  the run.

The steps, in order:

1. **Wait for a quiet tree.** Nothing else may be uncommitted in the main tree. Other agents'
   tracked edits block every acceptance, and they are never stashed (constitution §4.14). The
   lane waits for them to be committed, or for the work to move to a worktree.
2. **Detach.** Run `git switch --detach <the wave's tip>` (constitution §5.7; a single
   specification is a wave of one). It changes no working file that step 1 left. Commit the
   reviews here first, on the detached HEAD, and for a change built in the main tree, the change
   and its specification too.
3. **Accept.** Create `build/lane.lock` (no other tier of the judge runs while it exists, the fast
   tier included, AGENTS.md rule 3a), run `uv run pytest -n 3 --accept "Wave NN: <specs>"`, with
   `--accept-judge`, `--accept-growth`, `--accept-fewer-passes` and `--retire` as each entry's
   "For the lane" names them, every reason beginning with its specification's number; then remove
   the lock. The serial confirmation spec 052's Decision 11 asks for is the wave's dry run (step
   7): its shards run serially and gather's G5 compares every row with this acceptance at 1e-4 on
   three systems (the owner, 2026-10-19; it replaces the local serial acceptance every fifth
   landing). The lane returns to serial local acceptance only after a dry run shows a G5 fuel line
   the `-n 3` acceptance did not, until ten waves are clean again.
3a. **Compare** (spec 052). The landing notes record `uv run python tests/harness/sameness.py
   <record> build/progress/latest.json` (the lane's record from step 3) and its output, for each
   entry's reviewer record. Until spec 092 (the judge reads a release record) lands, at least one
   reviewer per wave keeps a local `-n 3` record for this; once it lands, the wave's dry-run record
   is compared too, once downloaded. A difference is clean when it is a check blocked in that
   worktree, or a row in another entry's claim list (the rows its "For the lane" says it changes).
   Any other difference ejects that entry: it is a defect of a check (order, speed, a shared path)
   or of the harness, written in the landing notes and fixed by its own judge change. Nobody re-runs
   to make it go away. A wave is **counted** when every difference is clean and its dry run's G5
   is green; **not counted** when an entry has no comparison record or the dry run is red on a line
   that is not growth. "Not counted" never blocks a landing.
4. **Commit the acceptance alone, at once** (spec 062). Run, in this order:

   ```
   git add -- context/progress/accepted.json ':(glob)context/progress/history*.jsonl'
   git commit -m "Accept …" -- context/progress/accepted.json ':(glob)context/progress/history*.jsonl'
   ```

   `git add` comes first because a new volume is untracked, and `git commit -- <path>` refuses a
   path git does not know. The pathspec leaves out anything else that is staged, and any change to
   this README. A stray file such as `history-70.jsonl` would match the glob too, but the intact
   check is red on it ("an unrecognised history file"), so `--accept` has already refused.
5. **Check it.** Run `uv run pytest tests/checks/test_rules.py`.
   `test_the_newest_acceptance_sits_on_the_commit_it_judged` reads this commit. Its first
   parent must be the commit its newest line judged, it must carry nothing else, and its line
   must say `dirty: false`. If that check fails, run `git reset --soft HEAD^` (a narrowed run
   can exit 1 only because other checks did not run; read the check's own line). HEAD is still
   detached and nothing has been pushed, so main has not moved. Then redo step 4.
6. **Move main.** Run `git switch main && git merge --ff-only <the acceptance commit>`.
7. **Dry run, at the fast-forward.** Push the acceptance commit to `wave/NN` and dispatch the
   release workflow on it as main moves in step 6; do not wait for the run. Then delete `wave/NN`,
   local and remote (constitution §4.14); the run keeps its commit, and its record is fetched by
   run id. Download `release-record-1` into `build/wave-NN/` and keep it; it is the comparison
   record of record once spec 092 lands. A red line that is not growth is fixed forward: nothing
   on main is reverted, and the next wave carries the fix before anything else. A tag still needs
   a green run on main's exact commit (AGENTS.md rule 6b). At most three release workflow runs are
   live at once (AGENTS.md rule 3a).

**Ten clean waves** (spec 052, Decision 11, restated by the owner on 2026-10-19). Step 3 runs
on three cores from 2026-10-19, ahead of the count Decision 11 asked for: as first written, its bar
could not be met, since every recorded comparison (063, 065, 081) differed only by checks blocked
in the reviewer's worktree and run in the main tree. A comparison is now clean when every
difference is such a check, a row in another entry's claim list, or a defect since fixed by a
landed judge change. A difference of any other kind ejects its entry and is fixed. The lane
returns to serial local acceptance only after a dry run shows a G5 fuel line the `-n 3`
acceptance did not, until ten waves are clean again.

**The upstream suites on the lane (spec 050).** The lane fetches the kit once
(`uv run python tests/upstream/fetch.py`) and keeps the source trees under `build/`. The landing
notes cite the scoreboard's ratchet line showing no `unrun locally` and no `upstream unrun` count:
every upstream check ran on the commit accepted. `--accept` itself refuses otherwise, unless
`--partial`.

**Before a release** (spec 063): the release workflow runs the upstream suites itself, in shards,
and its `gather` job requires the newest acceptance to be on the release's `python.wasm` and its
whole set (the set's own `SHA256SUMS`, the line's `set_sums`; spec 085), clean and not partial,
and on a tag the release's judge to be the accepted one.

A red acceptance commit cannot be repaired by accepting again. A red rule makes the run red,
and `--accept` refuses a red run. That is why step 5 runs before main moves. What the lane does
if a red acceptance reaches main anyway is the owner's question (question 70); until it is
answered, step 5 must not be skipped, and a red acceptance found on main stops the lane: write it
down under question 70 and change nothing.

The worktree check needs git 2.31 or later (`--path-format=absolute`). Older git fails closed:
it takes the main tree for a linked worktree, and `--accept` is refused.
