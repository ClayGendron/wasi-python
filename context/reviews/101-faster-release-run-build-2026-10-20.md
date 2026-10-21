# Review of 101 — a faster release run (build)

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent (Claude), not the author. It reviewed none of 101 before this: not
  the draft, not the pre-build review.
- **Reviewed:** `git diff faa9c93..8174bc0` on `spec/101-faster-release-run` (the code at
  `6992fc0`; `8174bc0` adds only `context/`), against the specification as revised and its
  pre-build review (`101-faster-release-run-prebuild-2026-10-20.md`).
- **Run:** the builder's run **39488829008** on `6992fc0`, which is the reviewed code (constitution
  §5.6, the owner, 2026-10-20). No run of the reviewer's own. Read back with `gh run view
  39488829008 --json jobs` and `gh run download 39488829008 -n release-record-1`. Also read:
  39468404589 (source), 39475482749 and 39481889333 (reuse), and wave 08's dry run 39488145764
  on `faa9c93` (the base, for comparison).
- **Re-ran (EXECUTED):**
  - Single node ids and four unit files: `uv run pytest -p no:cacheprovider -q` on the three new
    rules checks, `test_release_shards_cover_the_judge`, `test_release_judges_in_shards`,
    `tests/unit/test_{set_key,sameness,shards}.py` → 142 passed, exit 0
    (`build/101-review/probes.txt`).
  - `uv run ruff check src tests release` and `ruff format --check` → both exit 0.
  - The fast tier: **not run**. `build/lane.lock` existed in the main tree for the whole review
    (22:18 onward).
- **Time box:** 60 minutes (build-class, as the lane set it). Kept.

## The run, read back (EXECUTED)

- **Run 39488829008.** `success`, `workflow_dispatch` on `6992fc0`. 52 jobs: 49 passed;
  `attest` and both `publish` jobs skipped (not a tag). Created 20:04:14Z, updated 21:09:55Z:
  65.7 minutes.
- **The decision.** The `inputs` log: `from-source 'true', cached '': reuse=false`. The key was
  `wasi-python-set-v1-4e9c54d5…`, and the cache had no entry for it.
- **The set.** The build ran on macOS for 30.4 minutes. It logged `set: build/artifacts is whole
  and this commit's`. `same-bytes` started at +30.9 and passed.
- **The save.** `save-set` started at +34.2. It logged `wasi-python-set is whole and this
  commit's` and `Cache saved with key: wasi-python-set-v1-4e9c54d5…`.
- **The record.** `meta.set_source` is `built`. `set_sums` is `b5a66245…` and `artifact` is
  `ee45b241…`; wave 08's dry run 39488145764 on `faa9c93` has the same two hashes. There are 39
  records. `runs["build/build"]` is `linux-aarch64`, 10 of 10 units.
- **The scoreboard.** 767/859 pass, 85 gap, 7 blocked, 0 fail. The base had 758/850, so 9
  checks are new: 1 for check 1, 1 for check 2, and 7 cases of check 3. That is the claim list's
  `new`. The unit suite has 1926 per system on darwin and Linux, against 1875 on the base: +51,
  the claim's `units = 51`. Windows has 688, unchanged.
- **The macOS queue.** The macOS legs started between +32.9 (`own-embedding-a`) and +55.4
  (`upstream-macos`), while every Linux and Windows leg had ended by +45.1. The 65.7 minutes come
  from that queue. `own-embedding`'s job took 15.2 minutes, with a tail of 5.6 by the notes.
- **Earlier runs.** 39481889333 (reuse, `25fcd1a`): its `inputs` ran on `ubuntu-24.04`, and the
  build job on `ubuntu-24.04` logged `Cache restored from key: wasi-python-set-v1-ad003ce1…`. Its
  only red legs are the five macOS judge legs, which the notes call growth. 39475482749 has the
  same five plus Linux `own-guest` `cancelled`, as the notes say.

## Acceptance criteria against evidence

1. **The checks exist, seen failing first** — met, with one departure (L3). READ: the notes give
   the failures and mutants. EXECUTED: the checks pass here, and the reviewer's own mutants were
   each named. Those were: `save-set` on a tag (R5); the gather without `same-bytes` (R6 and rule
   7); `WASI_PYTHON_ARTIFACTS` in `build-shard` (R4); an `if:` on the set check (R3); a
   job-level or step-level `env:` on a build job in `release.yml` (K4); `set-cache.yml` saving
   without its verify (C8), or with a `pull_request` trigger (C1). Dropping the decision's
   `refs/heads/main` test is caught by check 3, which runs the step's own text in bash; the text
   rules do not catch it.
2. **The set does not change** — met. EXECUTED: there is no diff under `scripts/`, `recipes/`,
   `downloads/` or `src/`. `set_sums` is `b5a66245…`, equal to the base's dry run.
3. **The key is whole (traced build)** — not met yet. It needs the container slot. My ruling is
   below.
4. **A source run** — met. READ for 39468404589. EXECUTED for 39488829008: every job passed on
   all three systems, `save-set` saved, and its log names the key. The stored size (85,926,949
   bytes) is READ from the notes.
5. **A reuse run** — met in CI but for the gather. EXECUTED: 39481889333 had `reuse=true`, a
   build on `ubuntu-24.04` with the restore, and `same-bytes` passed. The gather was skipped,
   because the macOS legs were red on 042's growth. The builder ran the gather offline on that
   run's records (READ: no G1 to G4 or G6 line, and `meta.set_source` `reused …`). Note N1 covers
   the gap.
6. **The numbers** — met. READ for the table. EXECUTED for 39488829008's job times. The 65.7
   minutes and the 15.2-minute `own-embedding` job are each named with a cause: the queue and the
   tail.
7. **The seed** — after landing, as written. See L5.
8. **The judge** — not yet. The fast tier is not recorded after the rebase (L1). Acceptance and
   the sameness line belong to the lane.
9. **The tail** — met. READ: one reading, nothing found, and the follow-up is left to the lane
   (L6).

## Findings, most severe first

1. **Medium — M1. Decision 5's no-vacuous-pass comparison (the pre-build review's L6) is not
   evidenced** (self-check, unchecked). On a tag, the seven build-record checks now read only
   `build-shard`'s Linux tree in CI. A loop that matches nothing on Linux would pass quietly.
   CI would then stop checking how the published set was made. Only the lane's darwin run would
   still check it.
   Failure: on Linux, a meson-log glob or a compile-record path matches no file, and
   `test_every_build_python_is_pinned` passes with zero logs read. No record shows it, because a
   passing check keeps no output.
   Evidence that closes it: use the same container slot as criterion 3 (below), after its
   build. Run `uv run pytest -s -p no:cacheprovider` on `test_every_compile_contracts_nothing`
   and `test_every_build_python_is_pinned`; both print their `read:` lines. Add the other five
   record checks by node id. Save the output in `build/101/`. Put the counts in the landing notes
   beside the lane's darwin lines from the same command: compile records, commands, meson logs,
   `config.log`s and SDKs probed. Equal counts, or every difference explained, close it.

2. **Medium — M2. After the 103–109 chain lands, the rebased branch fails a rule the chain
   adds.** The chain (`claude/gallant-ride-9nxxmn`, tip `dbecd2d`) adds
   `test_code_outside_src_names_no_context_document` (spec 108). It holds that no comment or
   docstring under `tests/`, `scripts/`, `release/` or the workflows names a specification, a
   decision, a review finding or a path under `context/`. 101's own new lines do this throughout:
   "spec 101", "Decision 5", "the review's H1", "context/specifications/…".
   Failure (EXECUTED): I ran the chain's `scan.context_citation_hits` on 101's files at
   `8174bc0` and kept only the lines 101 adds. That gives **84 hits in 14 files**:
   - `release.yml` 18, `scan.py` 13, `test_rules.py` 10, `release_shards.toml` 8;
   - `shards.py` 7, `gather.py` 6, `test_shards.py` 5;
   - `sameness.py` 3, `test_gather.py` 3, `test_set_key.py` 3;
   - `set-cache.yml` 2, `release/set_key.py` 2, `test_sameness.py` 2, `test_scan.py` 2.

   The rule is red on the rebased tip until each hit says its reason in words.
   Fix: at the rebase, the builder rewords those comments and docstrings, as the chain did for
   the base's. Code, error strings and step names stay as they are. 101's text rules strip
   comments (`without_comments`) and match step names, not comments, so the rewording cannot
   change a verdict. The lane reads the reword as comment-only and runs the fast tier on the
   rebased tip. Evidence that closes it: that tier green, including
   `test_code_outside_src_names_no_context_document`.

   **The files 101 shares with the chain** (EXECUTED, `git merge-tree --write-tree dbecd2d
   8174bc0`):
   - Content conflicts:
     - `release.yml`, four hunks: the header comment; the build job's `outputs:` comment, where
       101 removes `record-id` and the chain rewords it; the zero-patch step's comment, where
       101 adds the `if:`; and the old build-shard steps, which 101 removes and the chain
       rewords.
     - `tests/checks/test_rules.py`, one hunk near line 832: both add checks at the same place.
       Keep both.
     - `tests/harness/scan.py`, two hunks: rule 6's `sha_step` line with its comment, and the end
       of the file, where both append. Keep both.
     - `tests/harness/shards.py`, one hunk: rule (h)'s comment.
     - `tests/release_shards.toml`, one hunk: the build shard's comment.
   - Merged cleanly: `CHANGELOG.md`, `tests/harness/gather.py`, `tests/harness/sameness.py`, and
     `tests/unit/test_{gather,sameness,scan,shards}.py`.
   - Not shared: the chain does not touch `release/set_key.py`, `set-cache.yml` or
     `tests/unit/test_set_key.py`.

   Every hunk is comment against code. None changes the logic of either side.

3. **Low — L1. The fast tier after the rebase onto `faa9c93` is not recorded** (self-check,
   unchecked; AGENTS.md rule 2). CI 39488829008 judged `6992fc0` in full on three systems and
   passed, and that covers the code. The rule still asks for the tier.
   Fix: the tier on the rebased tip (M2's) goes in `build/101/`, or the lane's integration fast
   tier covers it. The notes name which.

4. **Low — L2. Decision 9's 20% rule was not applied, and is not answered in the specification.**
   Decision 9 says a boundary that leaves the halves more than 20% apart "moves". The halves
   were 25% apart in three runs of four, and the notes leave the choice to this review.
   My ruling: do not move the boundary. The four large macOS jobs in 39488829008 took 14.4
   (`own-hostile`), 14.5 (`own-guest`), 15.2 (`own-embedding`) and 10.7 (`own-embedding-a`)
   minutes. Evening the halves would save under a minute, and a move costs a run.
   Fix text for Decision 9, in place of "a boundary that leaves the halves more than 20% apart
   moves": "The halves came out 25% apart in three runs of four (the *Landing notes*). The
   boundary stays, because the longest macOS job is within a minute of `own-hostile` and
   `own-guest`, and a move would gain less than a run costs."

5. **Low — L3. Check 4 is a unit row, not a rules check.** *The checks* list it as "(rules)",
   and Decision 8 says the set check's script "is run in bash by a rules check". It is
   `tests/unit/test_set_key.py::test_the_set_check_refuses_other_bytes`, and it calls `verify()`
   in Python. The workflow step's text is held by R3. The claim list is right: the row is among
   the 33 units, not under `new`.
   Fix (context): in *What was built*, add "check 4 is a unit row of `test_set_key.py`, calling
   `verify()` directly; the step's text is held by `release_reuse_errors` (R3)".

6. **Low — L4. K4 holds the build's `env:` in `release.yml` only, not in `set-cache.yml`'s
   `seed`** (`tests/harness/scan.py`, `set_key_errors` and `release_reuse_errors`). EXECUTED: a
   job-level `env: {CC: gcc}` on `seed` gives no error from either rule. The same mutant on
   `build-shard` gives K4.
   Failure: `seed` builds under a variable the key does not hold, and saves the result under
   main's key. Every reader then rebuilds three times and goes red. So it costs speed, never a
   false pass (layer 3).
   Fix: a C rule saying `seed`'s job and its build steps set no `env:`, with that mutant seen
   failing. The lane reads it as a code fix.

7. **Low — L5. Criterion 7 should show a reader hitting the seeded entry, not only the save.**
   `seed` saves on `ubuntu-24.04-arm`. Readers look up and restore on `ubuntu-24.04` (x86-64).
   The cache action puts the compression method into an entry's version (INFERRED from its
   documentation). If the arm64 image's `zstd` differs, main's entry is never hit and every
   branch builds from source. Nothing turns red when that happens.
   Fix (criterion 7's text): add "and the next branch dispatch on main's key logs `cached 'true'`
   in `inputs` and `Cache restored` in `build`; the lane records that run's id too."

8. **Low — L6. The roadmap lines the specification leaves to the lane are not written yet.**
   These are the macOS exit tail's follow-up (Decision 10; choice 4) and the width count
   (choice 5, about 38 jobs a run).
   Fix: the lane writes both before the fast-forward. At landing, the landing notes cite this
   review (`landed_review_errors`).

9. **Note — N1.** No reuse run's gather has run in CI: the macOS legs were red on growth on the
   unaccepted set. The `SET_SOURCE` wiring is proven on a source run (`set: built` on the
   scoreboard). `reused <key>` is proven by unit rows and by the builder's offline gather. The
   lane names the first CI reuse run whose gather passes, which is likely a parallel-safe
   entry's run in wave 10.

10. **Note — N2.** On a reuse run, the judge legs run on the restored set from about +2 minutes,
    before `same-bytes` has matched it. This is within §4.2: `python.wasm` runs only under
    wasmtime, the legs hold `contents: read`, and no record or publish exists without
    `same-bytes` (gather `needs`, rule 7, R6). It is stated here so a later change keeps the
    gather's `needs`.

11. **Note — N3.** The pre-build review file's own *Disposition* section is still empty. The
    disposition is written in the specification (*Disposition of the pre-build review*), and I
    checked each item against the diff: H1 in `sameness.py` and check 7; M2 in the C rules; L3 in
    `set-source` and check 3; L4 in R3; L6 in R4 and rule 8's regex. The lane may leave the
    section empty or point it at the specification.

## My ruling on criterion 3 (the traced build)

**I agree it may follow this review.** The key decides speed, never the verdict. I checked this
against the code. A reused set reaches a release record only through `same-bytes` (two fresh
rebuilds) and G2 on `build-shard`'s third fresh build, because the gather needs both (rule 7,
R6). A tag or a dispatch on main never reuses: the decision step is held by check 3, and G7 is
held by `set-source` from `steps.compile.outcome`. So a key that misses an input can make a run
red. It cannot make a stale set pass.

It must come **before the lane accepts 101**, in the same container slot as M1's evidence. It
must show:

- **The command.** Decision 3's exact `strace -f -y -e trace=%file,%process,chdir,fchdir -o
  build/101/trace.txt scripts/build.sh`. Run it on arm64 Linux, on the tip being landed, after
  `scripts/00_download.sh`.
- **Every path touched.** Resolve each relative path against its process's working folder. List
  every path under the checkout, outside `build/` and `downloads/`, that the build opens, stats,
  accesses or reads as a link. Include **failed lookups** (`ENOENT`): a file that appears later
  changes what the build reads.
- **Each path answered.** Each listed path is either in `set_key.closure()`, or answered in
  writing. For a real input, the answer is a closure change (code, which the lane reads) or a
  K rule. These are likely to need an answer (INFERRED, not traced):
  - `pyproject.toml` and `uv.toml`, which `uv pip install` in step 10 reads for configuration
    when its working folder is inside the checkout. Today `pyproject.toml` has no `[tool.uv]`
    table. The answer is either a rules row that it has none, or the file in the closure.
  - The `tests/` lookups for `sitecustomize` and `usercustomize` that `PYTHONPATH=tests` causes.
    L5a's rule covers these.
  - Any bytecode written under `tests/`. That is an output, but it should be named.
- **The record.** The list, its count, and the command go in the landing notes, labelled
  EXECUTED.

## Constitution checks

- **§4.1 (patches):** nothing under `recipes/patches/` changes. The zero-patch step runs on every
  run in `build-shard`, and on source runs in `build`. It holds.
- **§4.2 (pins, untrusted downloads):** no new download. `actions/cache/restore` and
  `actions/cache/save` are pinned by commit (`55cc8345…`, v6.1.0). A restored set is checked
  against its own `SHA256SUMS` and this checkout's `MANIFEST` lines. It runs only under
  wasmtime, and nothing is published without three fresh builds' bytes (N2). It holds.
- **§4.14 and §5.7:** one specification on its branch. The lane's wave rules are unchanged. On a
  reuse wave, §5.7's comparison is with `build-shard`'s build (Decision 4, the pre-build review's
  L7). It holds.
- **Artifacts never in git:** none are added. It holds.
- **§5.6:** the pre-build review was required (the release workflow) and is on file. This build
  review reads the builder's run on the exact code reviewed.
- **§7:** nothing tripped. There is no unpinned fetch and no number reported that was not
  executed. The four self-check items left open are named as open (M1, L1, L2, criterion 3).

## Disposition (filled in by the author, then confirmed by the reviewer)

1. M1 — open. It needs the container session criterion 3 needs, and Docker did not answer on
   2026-10-20 at night (`docker info` and `docker version` hung over four minutes; stopped, the
   slot never taken). The session, its command and where its output goes are in the
   specification's *Disposition of the build review*.
2. M2 — closed on the rebased tip. The citation rule failed with 74 findings after the rebase
   onto `dbecd2d` and passes after a comment-and-docstring-only reword, its own commit; the
   reword is checked as such by AST (Python) and comment-stripped lines (YAML, TOML). Every
   rebase hunk is named in the specification's *Landing notes*. The fast tier on `2190443`: 0
   fail. Run 39537732021 on `2190443`: one red line, the base's own Windows no-fork check (the
   chain's run 39530569266, fixed at `727bd4c`), not 101's.
3. L1 closed (the fast tier on `2190443`: 0 fail); L2, L3 and L5 written in with the review's
   text; L4 fixed as rule C10, its two mutants seen failing first, its own commit; L6 left to the
   lane, as the review asks; N1 to N3 acknowledged. Each in the specification's *Disposition of
   the build review*.

## Verdict

Lands once M1 is evidenced (the build-record checks' `read:` counts from a Linux tree beside the
lane's darwin counts), M2 is closed on the rebased tip (101's comments reworded, the fast tier
green), and criterion 3's trace is in the landing notes as ruled above; the Lows are write-ins
with their fix text.

One line: the design holds and its run is green on all three systems; what is left is evidence
(a traced build and a Linux-tree read count, in one container slot) and a comment-only reword
after the 103–109 chain.
