# /context/progress

The accepted state of the progress harness (`../specifications/002-the-progress-harness.md`). Written only by an acceptance, never by hand: after each green merge into `dev`, by the accept job's `uv run pytest --accept-from=<record.json> --claims=context/changes/` (*Acceptance from CI's record*, below); as the fallback, on a machine that must accept without CI, by a local `uv run pytest --accept "<reason>"` (*Local acceptance*).

- `accepted.json`: for each v1 check, its last accepted status, the commit and artifact it was seen on, and its metrics (fuel, bytes) per platform, plus the hash of every judging file.
- **The history**: one line per acceptance, append-only, in volumes (spec 062). Each line carries the hash of the line before it and of the `accepted.json` it wrote, so `test_progress_history_is_intact` notices a hand edit or a rewritten line.

## The history in volumes (spec 062)

The history is one hash-chained sequence of lines, kept in several files so that no tracked file passes the rules check's limit of `1 << 20` bytes.

- **Volume 1 is `history.jsonl`**: lines 1 to 59, sealed. Its SHA-256 is pinned in `tests/harness/history.py` (`SEALED`), and nothing is ever appended to it again.
- **Every later volume is named after its first line**: `history-00060.jsonl` begins with line 60. Line numbers are global, so a landing note cites "history line 61" as before, and may add the volume the `accepted:` line printed. To find line N, take the volume with the largest first line not above N.
- **A volume rolls only when full.** A new line goes to the newest volume while that volume stays within `BUDGET` (`1 << 19` bytes, half the limit); otherwise it begins a new volume. The intact check holds it both ways: no line past the budget, no volume begun early.
- **New lines record a change.** Lines 1 to 59 carry the full `passed` list. A line written since spec 062 has `"schema": 2`, the node ids that started passing (`passed_added`) and stopped passing (`passed_removed`) since the line before, and a digest of the whole passed set (`passed_digest`). A line's passed set is found by replay from line 1. The digest catches an inconsistent change, not a forgery: what catches a deliberate edit is the chain, the committed-prefix check and rule 1.
- **Only the intact check verifies every digest.** `--accept` checks the newest line's, and `three systems` none. On a history that does not replay, `three systems` is not met, and the intact check says why.

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
- **gap**: it fails exactly as `tests/known_gaps.toml` says, and that entry names the document that will fix it.
- **blocked**: a named prerequisite is missing (an artifact, the runner, a source tree). The `next:` line names the document that provides the most of them.
- **fail**: anything else. The run is red.

The ratchet compares the run with `accepted.json`. A pass that is lost, a check that disappears, or fuel or bytes that grow turns the run red. A pass that becomes blocked is red too, unless the run says `--partial "<why>"` (for example, a machine without artifacts).

### numpy's and pandas' own tests (spec 050)

`tests/checks/test_v1_3_upstream_suites.py` runs upstream's own tests in the guest, one check per group. Each group check records a third metric, **`passes`**: how many upstream tests passed.
- **It must not fall.** A lower value than the accepted one goes to its own list, `fewer`, printed `FEWER <node>: passes <old> -> <new>` before any `GREW` line and never cut. The run is red.
- **Its own flag.** Only `--accept-fewer-passes "<why>"` accepts a fall; the reason goes into the history line's `fewer_reason`. `--accept-growth` never does: an unrelated growth must not carry a lost pass.
- **A rise** is reported as `more`, not as `gained`. Without the flag, acceptance keeps the higher value.
- **A substitution** (one test from pass to skip, another the other way) keeps the count. Each group's `passed_digest` in `build/progress/latest.json` shows it; it is reported, not ratcheted.

Known failures are classes, each its own check and an ordinary gap. Their allowances are judge files, like `tests/known_gaps.toml`: `tests/upstream/*.toml` (the classes' expressions, the traps, the files not selected) and `tests/upstream/expected/<group>/<class>.txt` (each class's node ids). An edit to any of them is a judge change, and `git diff` names each test admitted or released. CPython's own tests (spec 065) are upstream checks like numpy's, with the same `passes` metric, flag and refusal; their plan, `tests/upstream/python/<group>.txt`, is judged too, and `tests/upstream/python.toml` adds three kinds of entry, each a gap: tests deselected by id, modules allowed one named kind of environment change, and results recorded per host. The compiled packages' own tests (spec 066) are upstream checks too, each package a family with its own grant (`/upstream-<package>`), stage and budget; a file too big for one group is split by a `[[split]]` of ordered `-k` expressions, each split group recording its file's collected count as the fact `collected`. The pure-Python packages' own tests (spec 067) are families of the same kind whose tests come from a pinned test source (`test_source = true`), tied to the package's pinned wheel file by file; each has one smoke group in the normal tier and its whole suite in the release tier, and a group may run docstring examples (`docstring_packages`, `docstring_modules`), doc files (`doctest_files`) or a module's own test functions (`module_functions`) as well as paths. A marker deselection is the fact `deselected`, with its reason.

A class or trap that is fixed: its check passes and its gap says "remove the gap". A fixed class stays, with an empty list file, as a passing check. A fixed trap's `[[trap]]` entry is removed in the same landing, its tests rejoin their group, and its now absent check is retired with `--retire` (an accepted gap whose check is absent is reported `absent`, as a pass is).

The checks need the source trees, the frozen artifacts and the test kit (`uv run python tests/upstream/fetch.py`). Without them they are blocked, which is local tooling and not red. But **`--accept` refuses** while any of them with an accepted pass or gap did not run here, unless `--partial "<why>"` is given.

A **fuel fact** (spec 091, `[[fuel_fact]]` in `tests/upstream/numpy.toml`) is a test whose fuel measures where a type object sits in memory, not the product: today one, numpy's `test_string_comparisons`, whose fuel moves with the `bool` type's address at every rebuild. Its cases leave their group's session and run in one of their own inside the group's check. Their outcomes still count: the group's `passes`, classes and `passed_digest` are what one session gives. Their fuel is not in the group's `fuel` metric: it is the fact `fuel_facts` in `latest.json`, red only at its cap (at least twice its fuel when measured), and compared between two runs of one commit by `sameness.py` to the ratchet's tolerance. A build-class landing's notes quote it in one clause. A move of more than 10% from the last quoted value gets one sentence of cause from the reviewer; when the quoted fact exceeds half its cap, that landing raises the cap or its reviewer says why not. The group's own fuel stays ratcheted and may still grow by a residual that needs its reason.

## Flags

| flag | what it does |
|---|---|
| `--accept "<reason>"` | record this run; refused unless green with no loss |
| `--accept-judge "<reason>"` | also accept a change to the judging files |
| `--accept-growth "<reason>"` | also accept fuel or bytes growth |
| `--accept-fewer-passes "<reason>"` | also accept a fall in an upstream group's `passes` (spec 050) |
| `--partial "<reason>"` | allow accepted passes to be blocked here |
| `--accept-from=<record.json>` | record a green CI run's merged record instead of this run; runs no check (the accept job; spec 138) |
| `--claims=context/changes/` | with `--accept-from`: take every reason from the news files changed since the last acceptance |
| `--retire <node id>` | with `--accept`: drop a check from the protected set |
| `--tier release` | judge both tiers; without it a run judges the normal tier (spec 102) |
| `--accept-tier-move "<reason>"` | also accept checks that moved between tiers (spec 102) |
| `-m "not slow"` | the fast tier: skip the golden jobs and the oracle |
| `-n 6` | run on six cores (spec 052): the same verdicts, about a third of the time |

The full record of the last run is `build/progress/latest.json`.

## Several cores (spec 052)

`uv run pytest -n 6` runs the judge on six cores with pytest-xdist (pinned in `uv.lock`). Its answer is the serial answer: every status, need, fact and `bytes` and `passes` value, the unit tally, the deselected list and the collected files are equal; fuel differs by no more than serial runs differ between themselves, far inside the ratchet's 0.01%. On darwin-arm64 (10 cores) the full judge took about 3 minutes against about 10 serially. Use `-n 3` when another agent's judge is running on the machine (a `-n 6` run peaks near 10 GiB), and `-n auto` on another machine. The plain `uv run pytest` stays serial.

- **How it stays the same.** The workers collect and run; each check's record is made on its worker exactly as in a serial run and rides to the controller on its report. Workers write nothing and run none of the acceptance's guards: the controller alone writes `latest.json`, judges the ratchet and accepts. An upstream group's check and its classes' checks always run in one worker (the judge's own scheduler; node ids are unchanged). A worker that dies is not replaced: the check it was running is `fail`, named "worker crashed", and the run ends; when no worker finishes at all, a red line says the record is incomplete. Each worker also reports what steered it from outside the judge (a conftest loaded only while collecting), so a parallel run is red exactly when a serial one is.
- **What the record says.** `meta.workers` is the number of workers started (`0` serially) and `meta.scheduler` the scheduler xdist used (`JudgeScheduling`; `null` serially). Neither is compared.
- **One way to run in parallel.** Allowed: `-n <number>`, `-n auto`, `--maxprocesses`, `--max-worker-restart 0` (the judge sets it), `--dist load`, `--loadscope-reorder`, `--testrunuid`. Refused before anything runs, exit 1 with one line: `-n logical`, any other `--dist`, any other `--max-worker-restart`, `-d`, `--no-loadscope-reorder`, `--maxschedchunk`, `--tx`, `--px`, `--rsyncdir`, `--rsyncignore`, `-f`/`--looponfail`. The ini keys `rsyncdirs`, `rsyncignore` and `looponfailroots` would come only from `pyproject.toml`, which is judged, and do nothing without the refused options.
- **Comparing two runs.** `uv run python tests/harness/sameness.py A.json B.json` prints every difference that could change a verdict (the fields above; a gap's or a blocked check's reason, not a pass's note, which may print a fuel count; fuel beyond the ratchet's tolerance; what steered the run from outside the judge, `meta.foreign`) and exits 1 when there is one. Fuel is compared between records of one platform only, as the ratchet keys it (spec 092).

### Comparing with a release record, and claim lists (spec 092)

- **A release record is either side.** The release workflow's gather job writes the merged record as the artifact `release-record-<attempt>`: `gh run download <id> -n release-record-1 -D build/<spec>/ci/`, then compare `build/<spec>/ci/record.json`. Sameness reads it as the darwin run it contains: each check as the darwin shard that ran it saw it (else Linux's, else Windows'), and the suite of the build and macOS shards together (against a local record, only its total and failing count: a unit test may skip on one host only). A check no shard ran (blocked by a need CI lacks, such as the oracle) is not compared, nor is fuel a Linux or Windows shard gave (G5 holds darwin fuel only, and Linux fuel moves between runs); stderr counts both. A check whose worst status on some system is not its darwin one is always a difference, which no claim explains (`<check>: status 'pass' on darwin-arm64, 'fail' on win32-amd64`), unless it is a block by a need CI lacks on a system that lacks it (the descriptor limit, on Windows). A record from a run before spec 092 (or before its build review) lacks the fields and is refused, exit 2, and so is a check with no source that some shard ran. **Compare only the record of a run whose every job, the gather included, is green.**
- **Where the set came from** (spec 101). A release record's `meta.set_source` is `built` (the build job compiled the set in this run) or `reused <key>` (a branch dispatch reused a set the cache held under its commit's key). A reuse run's verdict is the same verdict: the gather needs `same-bytes`, so the set judged equals two rebuilds from the pins made in the same run, and G2 holds every record, the build shard's included, to the build job's `python.wasm` and `SHA256SUMS`. The build shard runs on `build-shard`'s fresh arm64 Linux build on every run (its run is `build/build`, platform `linux-aarch64`); sameness still counts its unit tests on the darwin side. On a reuse run, the "release workflow's build" a local rebuild is compared with is `build-shard`'s; name its job id. A tag's set is always `built` (G7).
- **`--claims <toml>`** prints only the differences no claim explains, and exits 1 if any remain. A claim list is what the **second** record has that the **first** lacks, so put the record without the claimed changes first (a reviewer's or builder's record, then the acceptor's). Each specification writes its block in "For the lane"; a file for several specifications is their blocks one after another. `--except <spec>` drops a spec's claims (the entry whose record is the first: its changes are in both). stderr says how many differences each spec explained and which claimed entries matched nothing.

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

  An entry with `::` is a check; one without is a file and stands for its checks; a trailing `*` is a prefix (`"*"`: every row). A claim explains only its own kind: `grows` never explains a status, `new` never a check that went away. `meta.foreign` is never explained.

## The release tier (spec 102)

- **Two tiers.** The normal tier runs at every check: a pull request's run (the selection its paths need), every post-merge run on `dev` and its acceptance, a branch dispatch, a builder's or reviewer's local run. The release tier is the slow tests (upstream's `slow` markers, contourpy's `random_big` cases, CPython's `cpu`-gated tests and its four inline-`cpu` tests in full); it runs on a pushed tag, on the dry run on main before a tag, and in the release acceptance, and on a branch run dispatched with `release-tier: true`. Together the tiers are every test of every package built; nothing is left out of both. Which tests are release-tier is written in each family's TOML with its reason (`release_marker`, `[[release_select]]`, CPython's `cpython-release-*.txt`), and the rules prove each test lands in a tier.
- **A run record** says `meta.tier` and lists every release-tier check in `release_checks`. A normal run deselects each, reason `release tier`, even when named by node id; `--tier release` runs them.
- **The ratchet.** On a normal run an accepted release-tier row is `release tier not run <n>`: never red, never `--partial`; it keeps what was accepted, in `accepted.json` and in the history's passed set, and the line's counts take it at its accepted status. Each accepted entry records its tier (`"tier": "release"`; absent means normal). A check accepted in one tier and now in the other is `moved`, red on any run, until `--accept-tier-move "<NNN>: <reason>"` rewrites its tier; the reason is in the history line. A test that leaves a normal group for a release group lowers that group's `passes`: `fewer`, as ever.
- **The release acceptance**, before a tag, on main's tip, after the last merge and before the dry run on main: `uv run pytest -n 6 --tier release --accept "Release <version>: the release tier"` (`-n 6` only while nothing else runs on the machine, else `-n 3`; watch the workers' memory for the first ten minutes and restart at `-n 4` past 24 GiB). It may be the last merge's own acceptance, when the merged commit carries the version bump: first a normal-tier run without `--accept`, green, so a lost pass cannot cost the long run; then the one `--tier release --accept` run with every entry's reasons, which judges both tiers (`decisions.md`, 2026-10-22). Then compare the release-tier rows with the previous release acceptance's record, `uv run python tests/harness/sameness.py build/releases/<previous>/record.json build/progress/latest.json --tier-rows release --claims context/release-tier-claims.toml`. Every difference no claim explains is a release-tier regression and the tag waits. Keep the record under `build/releases/<version>/` and name its SHA-256 in the reason; if the previous one is gone, say so in the reason and rely on the ratchet, which compares every release-tier row with `accepted.json`. From step 4 of spec 138 this local acceptance goes: the release pull request from `dev` to `main` judges both tiers on the commit `main` will receive, and the accept job accepts its release-tier record onto `dev` as one acceptance commit (that specification's Decision 6).
- **The ledger**, `context/release-tier-claims.toml`: between two release acceptances, one `[[claim]]` block (the claim list's shape) per landed specification that changes a release-tier row or what one runs, appended by its pull request. At the release acceptance its blocks move under `## <version>` in `context/release-tier-claims-history.md` and the file starts empty.
- **The gather** expects the release shards' records only on a release run, and is red at G1 when a tag or a run on main did not judge the release tier, at G7 when the newest acceptance did not, at G3 when a normal run ran a release-tier check, and at G5 when an accepted entry's tier differs from the check's tier now.

## The verdict on a pull request (spec 138, Decision 3)

From step 2 of spec 138, a pull request into `dev` runs only what its changed paths need, and the gather's verdict is narrowed to what ran. The record says so: `meta.event` is `pull_request` and `meta.selected` lists the (system, shard) pairs that ran, which the decision job computes and the gather reads as `PLAN`.

- **G1** expects one record for each selected pair and no other file. **G2** holds every record to the set the set step restored and verified. **G3** holds each selected shard to its share. **G4** is unchanged. **G6** needs the probe on every system among the selected pairs.
- **G5**: a lost pass is red, and so is an absent check no news file retires. On a pull request a growth, a fall in a pass count or a tier move is listed, with its news file's reason or `unclaimed`; each shard's ratchet is red on an unclaimed one, as after the merge, where the gather is too; an absent check a news file's `retired` names is listed beside the `GROWTH` rows with its reason, on a pull request and after a merge alike, and so is it in each shard's ratchet and the quick job's rules step (amended 2026-10-25), since the accept job consumes the claim. "Ran in no record" is judged over the selected shards only. The rows an acceptance needs a reason for (growth, fewer passes, a tier move) are listed under a `GROWTH` heading, each with its news file's reason or the word `unclaimed`, and the gather is not red on them; one no news file explains is red, named, in the shard whose ratchet saw it (amended 2026-10-25).
- **G7 is not evaluated** on a pull request or after a merge: the post-merge run is the one that makes the acceptance G7 compares with. G7 holds at the release pull request and at the tag.
- On every other event `PLAN` is absent and G1 to G6 are whole. The gather's summary is the job summary, so a reviewer reads it without opening logs.

## Acceptance from CI's record (spec 138, Decisions 4 and 5)

Every merge into `dev` is accepted by CI, not on a laptop. The push to `dev` runs the full normal tier on three systems from `dev`'s cached set, then the gather with G1 to G6 whole, G7 not evaluated, and the rows an acceptance needs a reason for (growth, fewer passes, a tier move, an absent check) listed under `GROWTH` with the news file's reason when a claim gives one: the accept job consumes each claim. An unclaimed row is red there, named, as it is in the shard whose ratchet saw it. Two jobs follow, only when every job the run judges with is green, so `accepted.json` never records a red state.

A pull request into `dev` that changes `accepted.json` or a history volume is refused at `ci-status`: only the accept job writes accepted state. This README is a document; a pull request may edit it, and one that edits it alone is documentation only.

- **`accept-record`** (`contents: read`, no secret, no environment): in a fresh checkout of the judged commit, `uv run pytest -p no:cacheprovider --accept-from=build/ci/record.json --claims=context/changes/` writes `accepted.json` and the newest history volume and the commit's message, `build/progress/acceptance-message.txt`, and hands the three on as one artifact. Each option takes `=`: pytest finds the plugin's options in `tests/conftest.py`, which it loads only when no path is named, and a value after a space reads as a path.
- **`accept-push`** (the `accept` environment, whose deployment branch policy is `dev` alone): it checks the commit judged out with the deploy key (the environment's secret `ACCEPT_DEPLOY_KEY`, `dev`'s one bypass actor), runs no code of the repository, holds the change to `accepted.json` and one history volume, and, while `dev`'s tip is still the commit judged, commits them alone with the pathspec of step 4 below and pushes. The message is `Accepted: <the merge's subject, its pull request's title and number>`, then the reasons. It carries no skip word, since GitHub would also skip a release pull request whose head it is: the push's own run is the plan alone, quiet on a push of the accepted state, with nothing that judges. When `dev` has moved on, it pushes nothing, names the newer merge in one line, and succeeds: the newer merge's run accepts everything since the last acceptance.

`--accept-from` runs no check. It takes a gather's merged record from a push to `dev` or a pull request into `main` (`meta.event`, `meta.ref`, `meta.base_ref`), with `meta.set_source` `built` or `reused <key>`, for the commit checked out, and applies it as a local run's would. It is read as the darwin run it contains: each check as the record that ran it saw it, darwin first. A check darwin ran keeps darwin's metrics, keyed `darwin-arm64`, never the job's Linux host. A check only another system ran (the upstream groups run on Linux alone) keeps darwin's accepted fuel, since fuel elsewhere is not ratcheted, and takes the record's `passes` and `bytes`, which the gather holds equal on every system, under the same key. The history line names `source: "ci"`, the record's SHA-256 and the `platforms` whose probe passed, so the `three systems` need is met by the record.

Its reasons are the claim blocks of the news files added or changed between the commit the last acceptance judged and this one (`../changes/README.md`). Its refusals are the local acceptance's, in these forms, each a row of `tests/unit/test_accept_from.py`, and all named at once:

1. A linked worktree is no refusal: CI's checkout is a fresh clone, and the record, not the tree, carries what was judged.
2. A dirty tree is refused, as the record is read and as the acceptance is written.
3. "HEAD moved" becomes: the record's `meta.commit` and every shard's are the checkout's HEAD.
4. The judge's collection at the commit is not empty, and is the record's checks exactly.
5. `--shard` is refused, and so is every flag that gives a reason (`--accept`, `--partial`, `--retire`, `--accept-judge`, `--accept-growth`, `--accept-fewer-passes`, `--accept-tier-move`, `--tier`).
6. A run that is not green becomes: the gather's verdict (`meta.red`, which the gather writes into the record) has no red line, no shard was steered from outside the judge, and each shard's only override is `--progress-latest`.
7. A lost pass is refused; no claim clears it.
8. An absent check is retired only by a claim's `retired`; a `retired` entry that names no absent check refuses, as `--retire` does.
9. An accepted pass blocked, or an accepted upstream check not run, is always refused: a merge-grade run that blocks an accepted pass is a broken run, and no claim clears it.
10. A growth is cleared by `grows` with its `growth`.
11. A fall in a pass count is cleared by `passes` with its `fewer`.
12. A changed judge file is cleared by `judge`, which names each file with its reason. Until the verdict-bearing list of the judge's diet is built, that is every judge file the judge-hash line shows changed.
13. A check moved between tiers is cleared by `moved`.
14. A history that does not replay, or breaks its chain or its volume rule, is refused.

An unclaimed row refuses the acceptance with the row named, the run is red at `accept-record`, and the fix is a one-line news-file pull request whose merge runs the accept again.

## Local acceptance (spec 029)

The local `--accept` is the fallback for a machine that must accept without CI; it is not part of the normal flow. It is made in the main tree, on a clean tree, and on a detached HEAD, so `dev` moves only onto an acceptance already checked. The judge enforces three of these things:
- `--accept` is refused before collection in a linked worktree whose run would write a `context/progress` folder.
- It is refused on a tree with a change the judge could see: any tracked change outside `context/progress/`, or an untracked file under `src/`, `tests/`, `scripts/`, `recipes/`, `context/specifications/`, `context/reviews/` or `context/upstream/`, or a judging file.
- It is refused again when the acceptance is written, if the tree changed or HEAD moved during the run.

The steps, in order:

1. **Wait for a quiet tree.** Nothing else may be uncommitted in the main tree. Other agents' tracked edits block every acceptance, and they are never stashed (constitution §4.14). The acceptor waits for them to be committed, or for the work to move to a worktree.
2. **Detach.** Run `git switch --detach origin/dev` at the merged commit. It changes no working file that step 1 left. Commit the reviews here first, on the detached HEAD, and for a change built in the main tree, the change and its specification too.
3. **Accept.** Run `uv run pytest -n 3 --accept "<NNN>: <reason>"` (`-n 6` when nothing else runs on the machine; `decisions.md`, 2026-10-22), with `--accept-judge`, `--accept-growth`, `--accept-fewer-passes` and `--retire` as each specification's "For the lane" names them, every reason beginning with its specification's number. 3a. **Compare** (spec 052). The landing notes record `uv run python tests/harness/sameness.py <record> build/progress/latest.json` against the branch's CI record (`gh run download <id> -n release-record-1`), and its output. A difference is clean when it is a check blocked locally, or a row the specification's claim list names. Any other difference is a defect of a check (order, speed, a shared path) or of the harness, written in the landing notes and fixed by its own judge change. Nobody re-runs to make it go away.
4. **Commit the acceptance alone, at once** (spec 062). Run, in this order:

   ```
   git add -- context/progress/accepted.json ':(glob)context/progress/history*.jsonl'
   git commit -m "Accept …" -- context/progress/accepted.json ':(glob)context/progress/history*.jsonl'
   ```

   `git add` comes first because a new volume is untracked, and `git commit -- <path>` refuses a path git does not know. The pathspec leaves out anything else that is staged, and any change to this README. A stray file such as `history-70.jsonl` would match the glob too, but the intact check is red on it ("an unrecognised history file"), so `--accept` has already refused.
5. **Check it.** Run `uv run pytest tests/checks/test_rules.py`. `test_the_newest_acceptance_sits_on_the_commit_it_judged` reads this commit. Its first parent must be the commit its newest line judged, it must carry nothing else, and its line must say `dirty: false`. If that check fails, run `git reset --soft HEAD^` (a narrowed run can exit 1 only because other checks did not run; read the check's own line). HEAD is still detached and nothing has been pushed, so `dev` has not moved. Then redo step 4.
6. **Move `dev`.** Push the acceptance commit: `git push origin HEAD:dev`, once `git ls-remote origin refs/heads/dev` still names the commit it judged; otherwise accept again on the new tip. Its run is the plan alone: the plan is quiet on a push of the accepted state. `main` moves only by the owner (constitution §4.14).
7. **The run on `dev`.** The acceptance commit's run judges nothing (the decision job is quiet on a push of the accepted state alone, and `quick` waits on it); read the merge's own run, and keep its `release-record-1` under `build/`. A red line that is not growth is fixed forward: nothing on `dev` is reverted, and the next pull request carries the fix before anything else.

**The upstream suites in a local acceptance (spec 050).** The acceptor fetches the kit once (`uv run python tests/upstream/fetch.py`) and keeps the source trees under `build/`. The landing notes cite the scoreboard's ratchet line showing no `unrun locally` and no `upstream unrun` count: every upstream check ran on the commit accepted. `--accept` itself refuses otherwise, unless `--partial`.

**Before a release** (spec 063): the release workflow runs the upstream suites itself, in shards, and its `gather` job requires the newest acceptance to be on the release's `python.wasm` and its whole set (the set's own `SHA256SUMS`, the line's `set_sums`; spec 085), clean and not partial, and on a tag the release's judge to be the accepted one.

A red acceptance commit cannot be repaired by accepting again. A red rule makes the run red, and `--accept` refuses a red run. That is why step 5 runs before `dev` moves. What to do if a red acceptance reaches `dev` anyway is the owner's question (question 70); until it is answered, step 5 must not be skipped, and a red acceptance found on `dev` stops every merge into it: write it down under question 70 and change nothing.

The worktree check needs git 2.31 or later (`--path-format=absolute`). Older git fails closed: it takes the main tree for a linked worktree, and `--accept` is refused.
