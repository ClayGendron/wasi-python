# Review of spec 063 before build: the release judges in parallel shards

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude Opus 5.5). It wrote none of the spec, the memo or
  questions 98 and 99. This is the pre-build review that §5.6 requires, because the spec
  changes the release workflow (build-class). It also checks the design's integrity: can the
  release publish while part of the judge went unrun, ran the wrong share, or was forged?
- **Reviewed:** `spec/063-the-release-judges-in-parallel-shards` at `50dc15a`, the diff
  `main...HEAD`. That covers the spec, the memo
  `research/2026-10-18-the-release-judges-in-parallel-shards.md` and its evidence folder,
  questions 98 and 99, and the roadmap lines. It also covers the raw evidence in the main
  tree's `build/reviews-evidence/063-spec/`.
- **Read:** `AGENTS.md` (rules 6a, 6b and 10); the constitution (§5, §7); `release.yml` on main
  and on spec 057's branch (`2e5f58c`); `tests/harness/scan.py` on 057's branch
  (`release_binding_errors`, rules 1 to 18, `release_attestation_errors`); and from `tests/harness/`:
  `plugin.py`, `scoreboard.py`, `needs.py`, `history.py`, `sameness.py`, `paths.py`
  (`judge_files`, `dirty_path`, `PACKAGES`), `pins.py` (`source_pair`) and `upstream.py`
  (`tie_errors`, `group_spec`). Also `tests/checks/test_v1_3_upstream_suites.py`,
  `tests/upstream/*.toml`, `scripts/steps/apply_patches.sh`, `.gitattributes` and
  `.gitignore`. And `actions/download-artifact@9000827…`'s `src/download-artifact.ts`, fetched
  as text into `src/` beside this file.
- **Executed** (all files are in `probes/` beside this file). Every run used a fresh
  `git clone` of the branch in this scratchpad, so neither git tree was touched. Every run used
  the frozen set `s-4eb5418a2b1bb553`, read-only. The machine's load average was 60 to 76, so
  runs were kept short.
  - Collection with and without artifacts (`collect-noart.txt`, `collect-art.txt`).
  - Goal markers per collected item (`goalprobe.py`, `goal-items.json`).
  - Decision 3's plan applied to the real collection (`plan_counts.py`, `plan_counts.txt`).
  - Shard simulation by pytest's own deselection (`-k`, which calls `pytest_deselected` as
    `--shard` will). One small shard (`shard-sim-zips.*`) and one empty shard
    (`shard-sim-empty.*`).
  - Unit skips without the build host's inputs (`unit-nobuild.*`).
  - The judge hash of HEAD against `accepted.json`.
  - Member names in the numpy and pandas tarballs.
  - Read-only `gh`. The 0.1.0a5 release's `SHA256SUMS`, and the a5 tag run's log
    (`a5/run-39152890225.log`).
- **Scoreboard:** not re-run. The diff holds only documents and evidence, and running the full
  judge on this loaded, shared machine would have bought nothing.

Labels: **EXECUTED** (I ran it), **READ** (code, a log or a document), **INFERRED** (reasoned,
not run).

## Summary

The core design is sound:

- Shards are pytest's own deselection.
- Records are handed on by id and SHA-256.
- One gather decides, and writes no history.

Three facts I measured hold it up:

- **Deselection through the hook leaves the record whole** (EXECUTED). All 397 goal checks
  stayed in `checks`, and the 377 outside the shard were `deselected`. The ratchet read "lost
  0 · absent 0 · unrun 0 · grew 0", and the exit code was 0.
- **The collection does not depend on artifacts** (EXECUTED). There were 1,594 items with the
  set and 1,594 without it, with identical node ids. The gather can collect on a runner that
  has no set.
- **The release's bytes have equalled the lane's newest acceptance** (READ). The newest history
  line's `python.wasm` was `1655014…`. The latest dry run built `1655014…`, and the a5 tag run
  built `42344e2…`, which matches a5's newest line.

Four things stop me calling it ready:

- The gather breaks spec 057's rule 16, and the spec does not say it widens that rule (F1).
- G3, as written, makes 8 of the 17 records red (F2).
- The first Linux and Windows runs will block every tag after the landing, and Decision 18's
  "skip with a platform reason" is not available for a goal check (F3).
- G7 claims more than the history can show (F4).

## Findings, most severe first

### F1. The gather breaks spec 057's rule 16, which Decision 16 does not widen. Medium (READ)

Rule 16 on 057's branch (`scan.py`, `release_binding_errors`) says a job that holds the build's
files downloads nothing else. Only `same-bytes` is exempt:

```python
if name in holders and name != "same-bytes" and len(downloads) > 1:
    errors.append(f"rule 16: {name} holds the build's files but downloads something else too")
```

Decision 9 has the gather download `release-assets` by id and check it. That makes it a holder
(rule 7). It then downloads 17 records. 063's own scan rule 7 requires those downloads. So
`release_binding_errors` and `release_shard_errors` cannot both pass on the designed workflow.
Decision 16 lists rules 4, 10 and 14 as widened, and "7 to 9 and 13 reach the new jobs as
written". Rule 16 is not mentioned.

Rule 16 matters. 057's build review (F1) added it so that no bytes arrive in a holder after its
check.

**Write in one of these:**

- (a) **Preferred: the gather holds no assets.** The build job hands on a third output,
  `wasm-sha256`. It is the SHA-256 of `build/artifacts/python.wasm`, computed on the build's
  runner before the upload, as `sums-sha256` is. The gather compares `meta.artifact` (G2) and
  the history line (G7) with that value. It never downloads `release-assets`, so rules 7, 8,
  9 and 16 do not apply to it, and 057's table gives it `contents: read` for the checkout
  alone. The trust is the same as `sums-sha256`: only the build job can set it.
- (b) **Exempt the gather, with its reason, as `same-bytes` is.** Every other download must
  land under `records/`, by guarded ids of the judge jobs and the build's `record-id`. Nothing
  under `records/` is executed, only parsed as JSON by `gather.py`. Add a unit variant: a
  gather that downloads into `release-assets/`, and one with a second `release-assets`
  download.

Either way, list rule 16 in Decision 16, and add the variant to acceptance 5.

### F2. G3's "both are non-empty" makes the build shard and all seven upstream shards red. Medium (EXECUTED)

G3 says a record's run checks equal its shard's goal checks, and its `suite.total` equals its
shard's count of unit tests, and that "both are non-empty". I applied Decision 3's plan to the
real collection (`plan_counts.txt`):

| shard | goal checks | unit tests |
|---|---|---|
| `build` | 27 | **0** |
| `own-embedding` | 151 | 0 |
| `own-guest` | 162 | 94 |
| `own-rest` | 26 | 1,103 |
| each `upstream-*` | 2 to 10 | **0** |

`own-embedding` also has no unit tests. So, read literally, G3 turns 11 of the 17 records red,
not 8. The `build` record, the three `own-embedding` records and all seven upstream records
fail. Acceptance 4's mutation, "a record whose run checks *and* unit tally are zero", shows
the intent: "not both zero". The plan otherwise holds. No item is in two shards on any system.
The union over all shards is the whole collection. Every upstream suite and class check maps
to a group.

**Write in:** "each count equals its share, which may be zero; the shard's selection (goal
checks plus unit tests) is not empty."

### F3. The first Linux and Windows runs block every tag after landing, and a goal check cannot be "skipped with a platform reason". Medium (READ, INFERRED)

What runs on Linux and Windows for the first time:

- `own-rest` holds 1,103 unit tests (EXECUTED count), with the whole tooling suite.
  `test_build_scripts`, `test_patches`, `test_landing_lane`, `test_build_progress`,
  `test_several_cores` and `test_clang_emulated` alone hold 231 items. They start shells, git
  and xdist workers. Only `test_runner_sweep`, `test_runner_grants` and `test_cli` have ever run
  on Windows.
- Every upstream leg runs `apply_patches.sh` for numpy's two patches. On Windows that means
  `git apply` under `env -i PATH=…` in Git Bash, with `GIT_CONFIG_GLOBAL=/dev/null` and
  `SYSTEMROOT` cleared.
- Three platform behaviours have never been shown here:
  - **Matrix outputs:** whether a leg's unwritten names, which arrive as empty values,
    overwrite the leg that wrote them.
  - **CI macOS fuel:** whether `upstream-macos` stays within 1e-4 of the lane on a CI runner.
  - **Windows unpacking:** the unpack and staging on Windows.

What holds, so the risk is in behaviour, not hashes:

- **The judge hash should match on Windows** (EXECUTED). `.gitattributes` sets
  `* text=auto eol=lf`. No symlink is tracked, and no two paths differ only in case.
- **The tarballs are Windows-safe** (EXECUTED). There are no links, no reserved names, no
  case clashes, and the longest member name is 165 characters.
- **No test module imports a POSIX-only module at module level** (READ). Collection will not
  break on Windows.

Two gaps in Decision 18:

1. **"Skipped there with a stated platform reason (`skipif(not POSIX, …)`)" works only for a
   unit test.** For a goal check, `plugin._judge` turns a skip whose reason names no need into
   a failure ("skipped without a known need"). A Windows-only failure in a goal check can only
   be fixed, given a new need (a vocabulary change), or have its system dropped from the plan
   with rule (e) amended. Say so.
2. **The block is unbounded.** After landing, main cannot be tagged until every Linux and
   Windows failure is fixed and landed (rule 6b). The roadmap says "0.1.0a6 waits on 057", not
   on 063.

**Write in:**

- State the order. Either a6 is tagged from main after 057 lands and before 063 lands, or
  063's landing waits on question 98's answer, so the branch's dry run finds these first.
- List the three platform behaviours above as unknowns that only a dry run settles. Each
  fails closed: an empty id fails the guard, and growth fails the shard.
- Note the goal-check rule from point 1.

### F4. G7 ties the release to the lane through `python.wasm` alone, but Decision 11 and the README claim all the release's bytes. Medium-Low (READ, EXECUTED)

A history line records one hash, `artifact`, which is `python.wasm` (`scoreboard.accept`). The
snapshot, the stdlib zip and MANIFEST are not in it. A change that alters only the zip leaves
`python.wasm` as it was. That includes a pure-Python file of pandas, or a stdlib recipe. Such a
change would meet G7 while the lane never judged that zip. 057's revision notes that MANIFEST
changes with the download script's line. The release's own shards do judge every file. So
nothing goes unjudged, but these claims overstate:

- "The release publishes only bytes the lane accepted" (Decision 11);
- "the lane's newest acceptance is on the same bytes" (README and CHANGELOG).

G7's commit clause is close to tautological. `accept()` writes `accepted.json`'s `commit` and
the line's `commit` from the same `meta["commit"]`.

One check is cheap and closes a real gap. Nothing makes the release run the judge the lane
accepted: `judge_changed` is never red in `compare`. Today HEAD's judge hash is `c7010af…`,
equal to `accepted.json`'s (EXECUTED).

**Write in:**

- Say "`python.wasm`, the lane's accepted artifact" wherever G7 is described, and that the
  other files are judged by the shards.
- Add to G7, for a pushed tag only: `meta.judge.hash` equals `accepted.json`'s `judge.hash`.
  A branch dry run under question 98 carries a changed judge, so the check must not apply
  there.

### F5. Decision 15's rule keys on `paths.PACKAGES`, which leaves out components compiled into the artifact. Low (READ)

- **qhull is left out.** It is pinned (`qhull-8.0.2.tar.gz` is in the set's MANIFEST),
  compiled into matplotlib, and listed in `needs.SOURCE_COMPONENTS`. It is not in
  `paths.PACKAGES` and has no `package` line, so the check never asks for its entry.
- **The linked runtimes are left out.** wasi-libc and libc++ are in every binary, with their
  licences in MANIFEST, and their place is not decided.
- **"A `via` naming nothing" is undefined.** Any non-empty string would pass.
- **A `later` closer can be any existing file**, so ten entries could all point at
  `roadmap.md`.

**Write in:**

- Key the rule on `paths.PACKAGES` ∪ `needs.SOURCE_COMPONENTS`, with the name map stated:
  `cpython`↔`python`, `sqlite`↔`sqlite-autoconf`.
- Give qhull `via matplotlib`, and decide wasi-libc and libc++ (`via python`, or out of scope
  with a reason).
- Require a `via` to name a `suite` entry, `python`, or a stdlib module from a fixed list in
  the file.
- Name each `later` closer in the spec.

### F6. The gather's completeness depends on `shards.select` alone. Unit tests are counted, not named. Low (READ, EXECUTED)

- **The plugin and the gather share one function.** Both apply `shards.select`. A bug that
  drops an item from every share passes G3 on every record. G5 catches it only for accepted
  passes. A new check, or any unit test, would run nowhere unseen.
- **G3 compares `suite.total`, a count.** Records carry no unit node ids.
- **One unit test leaves the release quietly.**
  `test_pins.py::test_the_real_zlib_tarball_round_trips_and_a_patch_is_caught` runs in today's
  build job and skips in `own-rest`, because no zlib tarball is there (EXECUTED,
  `unit-nobuild.log`). Unit skips are not ratcheted.
- **G1 should be a bijection.** If one job hands on the same hash for two shards, one file
  satisfies both. G2 then catches it, but only if the gather walks per shard. The pinned
  `download-artifact` only warns on an id it cannot find in a list (READ,
  `download-artifact.ts` lines 139 to 144), and puts a lone artifact directly in `path`
  (line 192). So G1 is the real closure, and the spec should say so.

**Write in:**

- The gather asserts that every collected goal check is run (not `deselected`) in at least one
  record.
- Under `--shard` only, the plugin writes a digest of the unit node ids it ran into `meta`.
  The lane's record is unchanged, and the gather compares the digest with the plan's.
- Move `tests/unit/test_pins.py` to the `build` shard, or accept the skip in writing.
- Make G1 one distinct hash per shard, one file each, with one download path per job
  (`records/<job>/`).

### F7. The scan does not pin the `sha` and `out` steps. Low (READ)

057 rule 1 pairs `assets-id` directly with the upload's `artifact-id`. In 063 the ids and
hashes pass through a `run:` step (`id: out`) that writes `"$SHARD-id"` to `GITHUB_OUTPUT`.
That indirection is needed: a matrix cannot name outputs per leg. But `release_shard_errors`
rule 4 only requires that the step exists.

**Write in:** rule 4 fixes these texts:

- **`out`:** its `env:` is exactly `SHARD: ${{ matrix.shard }}`,
  `RECORD_ID: ${{ steps.record.outputs.artifact-id }}` and
  `RECORD_SHA256: ${{ steps.sha.outputs.sha256 }}`, and its `run:` is the one fixed text.
- **`sha`:** it hashes `$RUNNER_TEMP/record/latest.json`, the same path the upload names.

### F8. Acceptance 3 and 8 compare things the spec does not define. Low (READ, EXECUTED)

- **Acceptance 3** compares a `--shard` record with "a run of the same items selected by node
  id". A node-id run never collects the other files, so their checks are missing from
  `checks`. The `--shard` record holds them as `deselected`. `sameness.differences` reports
  each as "only in the first record". My two probes show this: a unit-only run had 0 checks,
  while the shard simulation had 397.
- **Acceptance 8's merged record** leaves three things undefined:
  - its `suite`, which is compared, while the own shards run on three systems and skips
    differ by system (Windows 7 skips against 2 on the verify subset, READ);
  - the metrics of `numpy-lib` and `pandas-io-parser`, which each run twice;
  - the order behind "worst status". `deselected` must rank lowest, or every node is
    deselected somewhere.

**Write in:**

- Acceptance 3 compares the shard's run checks, plus `deselected` equal to the complement.
- Define the merged record: the status order, `suite` per system, and which record's metrics
  win (the darwin record's).

### F9. Notes; nothing to change unless the author agrees

- **Where the tarballs land.** Decision 5 should say they go to `downloads/<name>`.
  `pins.source_pair` finds a tree only beside `downloads/<name>`, which is ignored by git, so
  the tree stays clean (READ).
- **How the gather tells goal checks from unit tests.** `--collect-only -q` prints no markers.
  Today the folder tells them apart exactly: 397 goal checks under `tests/checks`, 1,197 unit
  tests elsewhere (EXECUTED). `gather.py` should read the `goal` marker, not guess from the
  path.
- **Re-runs.** GitHub's documentation says a re-run of failed jobs reuses the outputs of
  successful jobs (READ, *Re-running workflows and jobs*). It says nothing about single matrix
  legs. Either way the result fails closed: a lost id fails the gather's guard, and the
  recovery is "re-run all jobs". This is a cost risk, not an integrity risk. The diagnostic
  artifact's name should carry `${{ github.run_attempt }}`, so a second failure does not
  collide with the first.
- **Wall time.** 18 to 22 minutes is plausible on a normal runner day. The longest leg on the
  CI evidence is `own-embedding` (221 s measured). The unmeasured risk is `own-rest` on
  Windows: about 135 s of process- and git-heavy tooling tests on macOS could run two to three
  times slower there. On a slow day the runners differ two to one (a5's judge took 6.4 minutes
  against 11.7), so the build alone can reach 24 minutes. Acceptance 10 records the real
  numbers, which is right.
- **Limits.** 16 legs, 3 `verify` jobs, `same-bytes` and possibly the x86_64 rebuild come to
  19 to 21 jobs; macOS uses 5. That fits Free, at worst with a minute's queue, and costs
  nothing on a public repository.
- **The `three systems` check stays blocked forever.** It lives in `portable_and_sealed`,
  reads only the lane's darwin history, and the gather proves the claim instead. Decision 10
  is right that CI must not write history. A follow-up should decide how v1's goal counts
  this check.

## What I checked and found to hold

- **Deselection through the hook** (EXECUTED, `shard-sim-zips.log`, with `-k` standing in for
  `--shard`). All 397 goal checks were recorded and 377 were `deselected`; `collected_files`
  held all 48 files; the ratchet was green; the exit code was 0. "Upstream unrun 32" is
  reported but is never red (`Ratchet.red`). The plugin must record areas before it
  deselects. If it does not, the ratchet reports `absent`, which is loud. Acceptance 3's
  stand-in should add that variant.
- **A shard that selects nothing** exits 5 today, with no `RED` line (EXECUTED). Decision 1's
  red line adds the reason.
- **`own-rest` catches every unlisted file**, including `tests/test_api.py`, which is at the
  top level (EXECUTED). Rule (b) holds on today's tree.
- **The lane is unchanged without `--shard`.** The only change to the record is
  `meta.shard: null`, and `sameness` never compares `meta`.
- **Integrity of the gather.** Each case fails closed:
  - *A missing shard, a crashed shard or a timeout:* the gather's `needs` fail, and `attest`
    and `publish` are skipped (their `if:` implies `success()`).
  - *A partial record:* the pytest step fails first, and G4 rejects `unrun` anyway.
  - *A record from another run:* `NOT_BY_ID` forbids `run-id` and `github-token`, so ids
    resolve only in this run.
  - *A record of another commit, artifact or judge:* G2 rejects it.
  - *An upstream group that skipped for lack of its kit:* G4 rejects it. Note that this check
    rests on the gather alone, because `upstream kit` is not a protected need and the shard
    would stay green.
  - *A collection that differs on Windows:* G3 rejects it. I found no host-dependent
    parametrization (READ).
- **Three systems.** A system's record is the one its own job handed on by hash. A Linux leg
  cannot hand on a win32 record. So one host never votes for another, which keeps 057's
  Decision 4. The per-system matrix argument (Decision 7) holds: legs of one system share
  every host input.
- **G7 on real releases** (READ). The a5 tag run built `42344e2…`, equal to the newest line at
  the tag (`24b1d2c`). The latest dry run built `1655014…`, equal to line 63. No line in the
  history is partial, and the newest is clean.
- **057's other rules.** Rule 4 (one job's ids joined by commas) and rule 10 (each id guarded)
  are widened safely: the guard still refuses each empty or non-decimal id, and a comma list
  is still one job's. Rules 9, 11, 13, 15 and 17 fit as written. Rule 14 gains rows. Only
  rule 16 conflicts (F1).
- **GitHub's limits and costs** fit, as above.

## Constitution and AGENTS.md

- **§5.1:** a research memo with executed evidence stands behind every decision.
- **§5.2:** questions 98 and 99 each carry a stated "meanwhile". The spec decides every choice
  it needs without them.
- **§5.6:** this is the pre-build review. The memo is right that the next release's
  threat-model review should see the new jobs: they fetch the kit and two tarballs, all pinned,
  on runners that hold only `contents: read`.
- **§5.7 and decision 91:** the spec is build-class and takes one slot. It lands after 057.
- **§4 and §7:**
  - Every new input is pinned by hash.
  - Downloads unpack under `downloads/` and `build/` and run only in the guest, or as data for
    `git apply`.
  - Nothing is pushed: question 98 asks first.
- **AGENTS.md:**
  - *Rule 6a:* the gather accepts nothing.
  - *Rule 6b:* see F3 on what blocks a tag.
  - *Rule 10:* one merged scoreboard in the log.
  - The new AGENTS.md rule is in scope for a judge change.

## Verdict

**Ready once F1 to F4 are written in.**

- **F1 to F3 are Medium.** As written, the workflow cannot pass 057's rules (F1), G3 rejects
  good records (F2), and the landing silently becomes a release blocker (F3).
- **F4 is Medium-Low.** It is a claim to correct, plus one cheap check on tags.
- **F5 to F8 are Low.** Write them in or answer them in writing.
- **F9** needs nothing.

The design's integrity holds: every path I tried fails closed.
