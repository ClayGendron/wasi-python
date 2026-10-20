# 085 — `gather` checks what it trusts

- **Status:** **built 2026-10-19** on `spec/085-gather-checks-what-it-trusts` over main `9d89535`
  (the Landing notes), and **revised against its build review** the same day (in the lane's
  scratchpad, `085-review/085-gather-checks-what-it-trusts-build-2026-10-19.md`: "lands once B1
  is fixed"; B1 fixed, B2 and B3 taken, each seen failing first; *Revised against the build
  review*). The owner answered question 105 with (b), spec 086 before 037 and no same-bytes
  exception, and declined Decision 9's fuel band for now; both are written in. Built after the confirmation of its pre-build review (`6523595`, "confirmed for
  build", with builder notes c1 and c2, both taken). Before that: drafted 2026-10-19 from main `a6dfc17`
  (`31a8713`); **rebased onto main `9d89535`** (spec 065 landed, history line 79) and **revised
  the same day against its pre-build review** (in the lane's scratchpad,
  `085-review/085-gather-checks-what-it-trusts-spec-2026-10-19.md`, with its probes in `work/`;
  to be copied to `../reviews/` by the lane). Its verdict: "ready once F1 to F4 are written in;
  F5 to F8 written in or answered". All eight are written in (*Disposition of the pre-build
  review*). Not built. It changes neither the guest's imports nor its exports, the artifact set
  nor the build recipe, so §5.6 does not require a review before build; the lane held one anyway,
  since 085 changes what gates a release. A different agent reviews the build. Its branch dry
  run's gather is red on one expected G7 line until the lane accepts it (criterion 6). Spec 086
  lands before 037 (question 105, answered (b)), so G7 stays exact (*Coordination*).
- **Date:** 2026-10-19
- **Owner:** Clay Gendron
- **Kind:** **build-class** (§5.7; AGENTS.md rule 2): it changes `.github/workflows/release.yml`.
  It is also a judge change.
  - The workflow: the build job hands on one more hash, `set-sums-sha256`; the gather job guards
    and binds it; both rebuild jobs print `python3 --version` (N5).
  - The judge: `tests/harness/gather.py` (G1, G2 with `meta.wasmtime` bound, G4, G5, G7, the
    merged record and the hidden-needs scan),
    `tests/harness/plugin.py` (`run_meta` records `set_sums`), `tests/harness/scoreboard.py` (the
    history line carries `set_sums`), `tests/harness/scan.py` (release rules 6, 7 and 10, and the
    rebuild gate's printed facts), and their unit tests: `tests/unit/test_gather.py`,
    `test_scan.py`, `test_scoreboard.py`, `test_history.py`, `test_plugin.py`.
  - Docs: `README.md` (*Releasing*, one sentence), `context/progress/README.md` ("Before a
    release", one sentence), `CHANGELOG.md` (0.1.0a8), and one amendment line in spec 063.
  - It changes no `src/`, `scripts/`, `recipes/` or `downloads/SHA256SUMS`, no artifact, no pin,
    no golden output, no gap, no upstream allowance, and nothing under `context/progress/`.
- **Depends on:** 063 (the gather) and 057 (the release ties what it signs to what it built),
  both landed; and 065, landed on main `9d89535` (accepted as history line 79). 065 edited
  `gather.py`, `plugin.py`, `scoreboard.py`, `shards.py` and `tests/release_shards.toml`; this
  draft is rebased onto it. See *Coordination* for 037, 039 and 043.
- **Source:** the 0.1.0a7 security review
  (`../reviews/0.1.0a7-security-review-2026-10-19.md`): findings **F5**, **F6**, **F7** and note
  **N5**; the roadmap's 085 paragraph.
- **Research it stands on:** `../research/2026-10-19-gather-checks-what-it-trusts/` (all
  EXECUTED on 2026-10-19 in this worktree at `a6dfc17`; `forge_synthetic` and `hidden_wide` again
  at `9d89535` after the rebase):
  - `forge_synthetic.py` and `.out`: sixteen forged records and one control on the unit test's
    synthetic set. Fifteen forgeries leave today's gather green and one makes it raise; the
    control (ten times the fuel on macOS, with an honest `meta.wasmtime`) is red, as it should be.
  - `hidden_wide.py` and `.out`: a prototype of the widened hidden-needs scan (Decision 1, the
    review's F5). It finds nothing in the repository at `9d89535` and flags each of three planted
    spellings in a fake tree.
  - `forge_real.py` and `.out`: six forgeries on the a7 tag run's own 19 records (run
    `39255794160`), each re-hashed after the edit. Today's gather is green on the honest records
    and on all six forgeries.
  - `records.py`, `records_a7.out`, `records_065.out`: every `blocked` check, every `suite` count
    and every metric name in the 19 records of the a7 tag run and of spec 065's green dry run
    (`39265738300`).
  - `fuel_across_systems.py` and `.out`: each metric of each passing check on Linux and Windows
    against `accepted.json`'s darwin-arm64 value.
  - `prototype.py` and `.out`: a throwaway prototype of Decisions 1 to 3, applied to the honest
    records of both runs (no red line) and to every real forgery (red each time).
  - `set_sums_a7.out`: the hashes of the a7 release's two `SHA256SUMS` files and of the lane's
    frozen set.

## Why

Some words first. A **shard** is one named slice of the judge, run by one leg of a judge job.
Its **record** is the `latest.json` that leg writes. The **gather** is the job that reads the 19
records, by the id and SHA-256 each job handed on, and gives one verdict (spec 063, G1 to G7).
Nothing is signed or published unless the gather is green.

The gather checks that each record is the one its job made, ran exactly its share, and failed
nothing. But it believes three things a record says about itself. The security review found
each one, and this spec reproduced each one (EXECUTED).

1. **A `blocked` status (F6).** A blocked check is one that could not run, because a named
   prerequisite (a **need**) is missing. Four needs are missing in CI by nature: `oracle`,
   `prior-art clones`, `three systems` and `descriptor limit`. G4 accepts a block by any of the
   four, on any system, for any check. So a record may say any check is blocked by the oracle.
   - On the a7 tag run's real records, reporting `test_guest_has_no_network` blocked by `oracle`
     on all three systems leaves the gather green. So does the `numpy-core` suite blocked by
     `three systems`, and the descriptor check blocked on macOS and Linux, where the need is met
     (`forge_real.out`).
   - Today exactly five checks are blocked in CI, all by design: the goldens (`oracle`), the
     prior-art licence rule (`prior-art clones`), the same-bytes claim (`three systems`) and the
     descriptor check's two rows on Windows (`descriptor limit`) (`records_a7.out`,
     `records_065.out`). A sixth would pass silently.
2. **Its own counts (F7).** G4 computes failed unit tests as `total − passed − skipped`, with a
   missing key read as 0.
   - A record whose `suite` is `{}`, or all zeros, or one test short of its share, is green: on
     the real records, `linux/own-runner` with `suite: {}` and `windows/own-runner` with zeros,
     against 538 unit tests in each share (`forge_real.out`).
   - Counts that are not numbers make the gather raise (`TypeError`). It fails closed, but with
     no reason line.
3. **Its own metrics (F7).** The ratchet compares a check's metrics only with `accepted.json`'s
   values for the record's own platform. The lane accepts only on darwin-arm64. So a Linux or
   Windows record that drops a check's `fuel` is never compared, and the gather stays green
   (`forge_synthetic.out`; on the real records, one Windows check's fuel dropped).
   - Worse, in darwin records too (the pre-build review's F1, EXECUTED there and here): the
     ratchet compares fuel only when the record's `meta.wasmtime` equals the version
     `accepted.json` was measured on, and files the check under `fuel_not_compared` otherwise,
     which is never red. G2 does not check `meta.wasmtime`. So a macOS record with ten times the
     fuel and `meta.wasmtime` `"48.0.0"` or null is green (`forge_synthetic.out`).
4. **The lane's acceptance names only `python.wasm` (F5).** G7 requires the newest history line
   to be on the release's `python.wasm`. The snapshot, the stdlib zip, `MANIFEST` and the licences
   are outside that tie. They are still judged by the shards on the release's own bytes. But the
   lane may have accepted a different snapshot or zip with the same `python.wasm`, and G7 would
   not see it.
5. **N5.** The two rebuild jobs print each host tool's version, but not the runner's own
   `python3`. Step 10's shim (spec 079) keeps it out of the build; the log should still name it.

**And one thing the review's fix would get wrong.** F5 says "hand `sums-sha256` to `gather`". But
the build job's `sums-sha256` is the hash of the *release assets'* `SHA256SUMS`, which lists the
`.tar.xz` and the wheel, both named by version. For a7 that is `2c7e95ca…`. No acceptance can
know it. The set's *own* `SHA256SUMS`, inside the tarball, is `c9dcb5b8…`, and that is exactly
the lane's frozen set's (`set_sums_a7.out`). So 085 hands on a new hash, of the set's own file.

So the gather trusts each record on three points it can check, and ties the lane's acceptance to
one file where it could tie all of them.

## Decisions

1. **A check may be blocked in a release record only by a need its own body calls, and only on a
   system where CI lacks that need (F6).**
   - **The checks come from the code, not from a list.** The gather already collects the judge
     in process at its commit (`gather.collect`). For every goal check it now also reads the
     check function's own source (`inspect.getsource(item.function)`), parses it (`ast`), and
     notes every literal need named in a call `needs.need("…")` or `need("…")`. Of those, the CI
     needs are the ones the check may be blocked by. A parametrized check's rows share one body,
     so they share its needs.
   - **The systems come from the need.** `CI_NEEDS` in `gather.py` becomes a map from need to the
     systems that lack it, named as `expected_keys` names them:
     `oracle`, `prior-art clones` and `three systems` → `build`, `macos`, `linux` and `windows`
     (local tooling CI never has; G6 proves three systems instead); `descriptor limit` →
     `windows` only (Windows has no `RLIMIT_NOFILE`; macOS and Linux do). The build record's
     system is `build`, and G4 runs over it like the others. This map is the only hand-kept
     part. It is about four needs, not about checks, and it is hand-kept today as a set.
   - **G4** is red for a `blocked` check whose need its body does not name, or whose need does not
     block on that record's system: `G4 <system>/<shard> <node>: blocked by '<need>', which its
     check does not call` or `…, which does not block on <system>`. A block by any other need
     stays red as today.
   - **G5's exemption** ("every accepted pass or gap ran in at least one record, unless it is
     blocked by a CI need") uses the same rule.
   - **What the derivation finds today.** Exactly the five checks the CI blocks, each on the
     systems it is blocked on (`prototype.out`). No other check names a CI need.
   - **Where it fails closed** (red in the gather, nothing hidden): a need named through a helper
     or a fixture; through a variable, a lookup such as `NEED_OF[which]`, an f-string or `*args`;
     a direct `pytest.skip("needs: oracle")`, which the plugin also records as `blocked`; a source
     `inspect` cannot read.
   - **Found before a dry run.** A fast-tier unit test holds that `gather.hidden_ci_needs(repo)`
     returns nothing. It flags (the pre-build review's F5):
     - any string constant equal to a CI need under `tests/checks/` (conftest files included) and
       in `tests/conftest.py`, outside the statements of a `test_` function's body: a literal in
       its decorators (a `parametrize` list) or its default arguments is flagged (the build
       review's B2);
     - under `tests/harness/`, any such string used as a call argument, a container element (a
       dict, list, tuple or set member), a keyword value, or a constant set by plain assignment
       at module or class level, directly or through a conditional expression
       (`X = "three systems"`, `NEED = "oracle" if a else ""`; the confirmation's c1, the build
       review's B2), outside `needs.py` and
       `gather.py`, the two files that define the vocabulary, which the scan skips before parsing
       them (c2); a path piece such as `JOB_DIR / "oracle"` in `jobs.py` is not flagged;
     - any string beginning `"needs: "` anywhere in that scope, test bodies included, outside
       `needs.py`.
     Seven call sites today pass `need()` a non-literal (the review's count: `NEED_OF[which]`
     lookups and f-strings); none names a CI need, and the widened scan would flag one that
     came to (`hidden_wide.out`: nothing in the repository; each planted spelling flagged). Three
     spellings stay unseen until a dry run, where they are red: a need computed at run time from
     pieces; a CI need passed from inside a `test_` body to a helper that skips with it
     (`helper("descriptor limit")`; the confirmation's c1), since a string inside a check's body
     is not flagged and `needs_called` reads only `need(…)` calls; and a CI need held in a local
     variable of a harness function.
   - **Where it fails open** (narrow, and written down here; the review's F8):
     - the rows of a parametrized check share one body, so a row whose own path never calls the
       need may still be reported blocked by it (today only the descriptor check's two rows, both
       rightly blocked on Windows);
     - the rule asks whether the body *names* the need, not whether the call can be reached: a
       call in dead code or behind a condition allows the block on every system the map allows;
     - any call spelled `.need("…")` counts, whatever the object before the dot.
     Each of these needs a change to a check's own body, which is a judge change the review
     sees.
   - **Why not a pinned list.** The security review suggested pinning the pairs in `release_shards.toml`
     or `gather.py`. A list is a second copy of what the check's body says. It drifts unless it is
     checked against the body, and that check is the derivation itself. Adding a need to a check
     is already a judge change: the diff shows `needs.need("oracle")` added to a check, and the
     review sees it. A pinned list would add a line to that same diff and nothing else.
2. **A record's unit tally is its share (F7, counts).**
   - G4 requires `suite` to hold `passed`, `skipped` and `total`, each a whole number (an `int`,
     never a `bool`) at least 0, with `passed + skipped == total` and `total == meta.units.count`.
     G3 already ties `meta.units` to the plan's share, by count and by digest. So the tally, the
     record's own list and the plan agree.
   - The red line is `G4 <system>/<shard>: suite <value> is not its <n> unit tests`. When the
     shape and the total are right but `passed + skipped < total`, today's line stays: `N unit
     test(s) failed`.
   - **Why `total` must equal the count.** The plugin adds one to `total` for each unit test, at
     its call, or at a setup that failed or skipped (`plugin.py`, `_judge`). A complete serial run
     tallies each selected unit test once. A run cut short (`-x`, an interrupt) tallies fewer, and
     should be red. All 38 records of both runs meet the rule (`records_a7.out`,
     `records_065.out`).
3. **A passing check records every metric the lane accepted for it, on every system (F7,
   metrics).**
   - G5 is red when a record shows a check `pass` without a metric name that `accepted.json` holds
     for that check on darwin-arm64 (`wasmtime` aside): `G5 <system>/<shard>: <node> records no
     <metric> (accepted.json has it)`. It is red too when a passing check's metric value is not a
     finite number (an `int`, or a `float` that is neither `NaN` nor infinite; never a `bool`):
     `G5 <system>/<shard>: <node> metric <name> is not a number`. *Why finite* (the build
     review's B1): `json` reads `NaN` and `Infinity`, and the ratchet's `value > old × (1 +
     tolerance)` is false for `NaN`, so a darwin record whose fuel is all `NaN` was green. A
     check's `metrics` that is not a mapping is red the same way (`… metrics is not a mapping`),
     and a `need` that is not a string is G4's `blocked by …` line (B3): malformed shapes give a
     reason line, never a raise.
   - **Names on every system; values where they are compared today.** Fuel stays compared only in
     darwin records (the ratchet, to one part in ten thousand), and an upstream group's `passes`
     on every system (G5, as today). Fuel is not comparable across systems: on the a7 tag run,
     Linux fuel was up to 0.197% above the lane's darwin value and Windows up to 0.045%, far past
     the ratchet's 0.01% (`fuel_across_systems.out`). But the names agree: in the 19 records no
     passing check lacks a name `accepted.json` holds (`records_a7.out`).
   - A check that would record a metric on one system only is therefore red. Making a check do
     that is a judge change with its own reason; this spec adds no exception list.
   - A darwin record that drops a metric is already red through the ratchet ("is no longer
     recorded"). It may now be named twice. That is accepted.
   - **G2 binds `meta.wasmtime`** (the pre-build review's F1). Every record's `meta.wasmtime` must
     equal the `wasmtime` version locked in the gather's own `uv.lock` (`49.0.0` today), read with
     `tomllib` (`G2 <system>/<shard>: wasmtime <value> is not uv.lock's <version>`). Without it,
     one field in a darwin record turns off that record's fuel ratchet (*Why*, item 3). It also
     catches an honest fault: a leg that resolved another wasmtime. *Why not make
     `fuel_not_compared` red instead:* a branch that bumps wasmtime would then be red at every dry
     run until its acceptance, while the lock binds what that branch runs.
   - **What stays open.** Off darwin, metric values are still not compared: a Linux or Windows
     record may carry any number for fuel, as long as it is a number. Decision 9 says why 085 adds
     no band.
4. **The lane's acceptance names the whole set: its own `SHA256SUMS` (F5).**
   - **What is hashed.** The set's own `SHA256SUMS`: the file in the artifact folder that lists
     every other file of the set (`python.wasm`, the snapshot, the zip, `MANIFEST`, each licence).
     Not the release assets' `SHA256SUMS` (the *Why*). The set check `test_v1_1_artifact_set`'s
     `sums_errors` holds that every file matches it and none is missing or extra, and that check
     is an accepted pass. So one hash names every file of the artifact set a run judged. (The run
     judges other things too, each bound its own way: the wheel by `sums-sha256`, the runner's
     source by the commit through G2, the upstream kit and source trees by their pins.)
   - **The run records it.** `plugin.run_meta` adds `set_sums`: the SHA-256 of
     `artifact_dir()/SHA256SUMS`, or null when there is none.
   - **The lane's line carries it.** `scoreboard.accept` writes `set_sums` into the history line,
     beside `artifact`.
   - **The build hands it on.** A new step in the build job, before the `release-assets` upload,
     as the `python.wasm` step is:
     `echo "sha256=$(shasum -a 256 build/artifacts/SHA256SUMS | cut -c1-64)" >> "$GITHUB_OUTPUT"`,
     with id `set-sums`, handed on as the job output `set-sums-sha256`. It is a different file
     and a different name from `sums-sha256`, on purpose.
   - **The gather checks it.** `SET_SUMS_SHA256` is bound in the gather step's `env:` and guarded
     as 64 lower-case hex in its first step, with `WASM_SHA256`.
     - **G1:** red when it is not 64 hex (`G1 the build job handed on no set-sums-sha256`).
     - **G2:** each record's `meta.set_sums` equals it (`G2 <system>/<shard>: set_sums is not the
       build's SHA256SUMS`). Every shard unpacks the build's tarball, which holds the set's
       `SHA256SUMS`, so an honest record meets this.
     - **G7:** the newest history line's `set_sums` equals it (`G7 the newest acceptance is not on
       the release's set (SHA256SUMS)`). G7 keeps its `artifact` clause too: the `three systems`
       need and the history are keyed on `python.wasm`.
   - The merged record's `meta` gains `set_sums`, and the green line becomes
     `three systems: darwin linux win32 on <python.wasm> · set <set_sums>`.
   - **The a7 release would have met it.** Its set's `SHA256SUMS` is `c9dcb5b8…`, the same as the
     lane's frozen set `s-c50ca51fae5eb55b-c9dcb5b8` (`set_sums_a7.out`).
5. **No schema changes (how old lines are read).**
   - **The history line** stays format 2 (`"schema": 2`). `set_sums` is one more key. The replay
     (`history._step`) and the intact check (`history.errors`) read only `n`, `prev`, `schema`,
     the passed fields and `accepted`; they ignore other keys (READ). The chain hashes the line's
     whole text, so the new key is chained like every other. The sealed volume is untouched.
   - **Lines 1 to 79** have no `set_sums`. Every reader takes it with `.get`, so it reads as null.
     G7 treats null or missing as a mismatch. So the first release after 085 needs an acceptance
     made by 085's judge. 085's own landing writes one (`--accept-judge`), so a release of main
     after 085 meets G7 if its build makes the lane's set.
   - **`accepted.json`** does not change, and keeps `"schema": 1`. Its per-check `artifact` field
     has no reader (READ: no harness code reads it back). The set is a fact of one run, which the
     line holds; and the line hashes `accepted.json` (`accepted`), so the two are chained. A copy
     in `accepted.json` would sit where nothing reads it.
   - **`sameness.py`** does not compare `artifact` and need not compare `set_sums`.
6. **The rebuild jobs print `python3 --version` (N5).** Both rebuild jobs' step "The runner's own
   tools" gains the line `python3 --version`, after `uv --version`, with a comment: the runner's
   own interpreter, which step 10's shim keeps out of the build (spec 079), named so the job's log
   records what stood on `PATH`. `scan.rebuild_gate_errors` adds `python3 --version` to the facts
   each rebuild job must print, beside `nproc` and `binfmt_misc`. The two jobs stay alike in shape
   (its existing rule).
7. **Where the trust boundary is, and what 085 does not claim.**
   - **Who writes what.** The 19 records are written by the build job and by the legs of three
     judge jobs, in the same workflow run, from the same checkout. The gather checks them against
     values that only other jobs set: each record's id and hash (from its own job's outputs),
     `python.wasm`'s and now the set's hash (from the build job), and the collection, the plan,
     `accepted.json` and the history (from its own checkout).
   - **What a compromised judge leg can forge.** Everything in its own record. Also any record of
     its own system: the legs of one judge job share one output namespace (spec 063, Decision 7
     says so), so one leg can hand on another shard's id and hash. It also holds every input the
     gather compares against: the checkout (so the collection, the plan's shares and their
     digests) and the set it downloaded (so both hashes). **So a leg that knows the format can
     write records that pass every G rule, before 085 and after it.** It reports every check
     `pass`, with plausible metrics and exact counts. The gather cannot tell, because nothing in
     a record is attested by anyone but the job that wrote it.
   - **What such a leg cannot do.** Change the bytes that are signed or published. `attest`,
     `publish` and `pypi` re-download the assets by the build job's id and re-check them against
     the build job's `sums-sha256` (spec 057). A judge job holds `contents: read` only, and no
     job reads anything a judge job uploads except the gather, which reads records (READ,
     `release.yml`). A judge leg that uploads under another artifact's name gets a new id, and
     downloads by the old id then fail: at worst a stopped release (INFERRED from spec 057's
     download-by-id rule). So the worst a compromised leg does is make the verdict lie: a green
     gather on a set that would have failed.
   - **What 085 catches.** Honest faults and careless edits: a check that comes to name a CI need
     through a helper; a plugin or pytest change that miscounts or drops unit tests; a harness
     change that stops recording a metric on one system; a record from a run cut short; a shard
     that judged another set than the build's; a leg that resolved another wasmtime. It also
     closes some cheap lies: a one-field `blocked` that looks like an expected CI condition, a
     missing count, a dropped metric, and a darwin record's `meta.wasmtime` that turns off its own
     fuel ratchet. It leaves one cheap lie open: off darwin, a metric value may be any number
     (Decision 9). A forger must now write a consistent pass. That raises the bar a little and no
     more.
   - **What 085 does not change.** The history is an unsigned file in the repository, and its
     chain can be recomputed by anyone who can push. G7 ties the release to what the repository
     says the lane accepted, not to an authenticated acceptance. Today only the owner's account
     can push, the rulesets let it bypass, and no status check is required (spec 064 has not
     landed). Signing acceptances is out of scope.
   - In one line: **the gather checks consistency, not authenticity.**
8. **G7 stays exact: an exact `python.wasm` hash and an exact `SHA256SUMS` hash** (the
   pre-build review's F2; question 105, answered).
   - 085 compares both hashes exactly, as 057's rule asks.
   - The pinned clang (wasi-sdk 33) compiles one scipy file to different bytes on every run, so a
     set with scipy built on it would differ from the lane's on every build, in `python.wasm`'s
     and the snapshot's lines, and both G7 clauses would be red on every release.
   - **The owner answered question 105 with (b), 2026-10-19:** spec 086 (wasi-sdk 34, whose clang
     is fixed) lands before spec 037 (scipy), and 037's same-bytes exception is dropped. So every
     build of a set makes the same bytes, and both clauses stay exact hashes. No canonical digest
     and no exception enters the gather.
9. **No cross-system fuel band, declined by the owner for now** (the pre-build review's N1; the
   owner, 2026-10-19: "not now"). It may come back as a later specification.
   - A coarse band, say 1%, on Linux and Windows fuel against the lane's darwin value would catch
     two lies Decision 3 leaves open: fuel swapped between two checks (5.6% apart on the pair the
     review swapped) and a Linux-only fuel regression. The worst honest gap on the a7 tag run was
     0.197% (`fuel_across_systems.out`), so a 1% band has five times that margin today.
   - **Why it is left out.** The band would be a new rule about how fuel may differ by host, and
     a future host-dependent check (a file-system path, an encoding) could exceed it honestly; it
     catches forgeries that a compromised leg can avoid anyway (Decision 7).
   - **A later specification** would be small (one G5 clause, one constant, rows in the mutation
     table), and 085's data above is its evidence.

## Intent

A release record says only what its code allows. A check is blocked only where its own body asks
for a need CI lacks. A record's unit tally is its share. A passing check carries the metrics the
lane accepted for it, measured on the wasmtime the lock names. And the lane's acceptance names
the whole set, by its `SHA256SUMS`, not only `python.wasm`. These are consistency checks against honest faults; a compromised judge leg
can still forge a consistent record (Decision 7).

## Design

- **`gather.py`.**
  - `CI_NEEDS: dict[str, frozenset[str]]` (Decision 1) replaces the frozenset.
  - `needs_called(func) -> set[str]`: the literal needs a function's own source names in
    `need(…)` calls (an `ast.Call` whose function is the name `need` or an attribute `.need`,
    each `str` constant argument). Unreadable source gives the empty set.
  - `hidden_ci_needs(repo) -> list[str]`: Decision 1's scan, as `file:line: <string>`.
  - `locked_version(name, lock=paths.REPO / "uv.lock") -> str`: a package's version in `uv.lock`
    (`tomllib`); G2 compares each record's `meta.wasmtime` with `locked_version("wasmtime")`.
  - `collect()` returns a third value, `may_block: dict[str, frozenset[str]]`, for goal checks
    whose body names a CI need; `Inputs` gains `may_block`, `set_sums_sha256` and `wasmtime`;
    `main` reads `SET_SUMS_SHA256` and the locked wasmtime.
  - `allowed(node, need, system, may_block)`: `need in may_block.get(node, ()) and system in
    CI_NEEDS.get(need, ())`, used by G4 and G5.
  - G1, G2, G4, G5, G7 and `merge` as Decisions 1 to 4 say (G2's `meta.wasmtime`, Decision 3).
- **`plugin.py`.** `run_meta` adds `"set_sums"`.
- **`scoreboard.py`.** `accept` adds `"set_sums": meta.get("set_sums")` to the line.
- **`release.yml`.** The build job: the `set-sums` step and the `set-sums-sha256` output. The
  gather: `SET_SUMS_SHA256` in the guard step (with the same `case` and length test as
  `WASM_SHA256`) and in the gather step's `env:`. Both rebuild jobs: `python3 --version`.
- **`scan.py`.**
  - Rule 6: the build job's `set-sums-sha256` output names a step whose run hashes
    `build/artifacts/SHA256SUMS` with `shasum -a 256` or `sha256sum`, before the
    `release-assets` upload.
  - Rule 7: the gather step's `env:` is exactly today's plus
    `SET_SUMS_SHA256: ${{ needs.build.outputs.set-sums-sha256 }}`.
  - Rule 10: only `build` sets `set-sums-sha256`, and only `gather` reads it.
  - The rebuild gate: `python3 --version` among the printed facts.

## Scope

- **In:** F5, F6, F7 and N5 as decided above; their checks; the sentence in the README and the
  progress README that names what G7 ties; the CHANGELOG line; spec 063's amendment line.
- **Out:**
  - Signing acceptances, or requiring signed commits (Decision 7). The owner's to raise.
  - Comparing fuel values across systems, at the ratchet's tolerance or in a coarse band
    (Decisions 3 and 9).
  - The release environments' protection (the review's N1) and required status checks (spec 064).
  - Any change to what the shards run, to the plan, or to the judge's own run outside `--shard`.
  - Any canonical digest or same-bytes exception in the gather: none is needed, since spec 086
    lands before 037 (Decision 8).

## The checks first

Each check below is written, and **seen failing on main first**, before any code changes. "Fails
today" means the gather stays green (or raises) on the forgery, so the test that expects a red
line fails. `forge_synthetic.out` holds today's verdict on sixteen forgeries and a control; the
rest need inputs that do not exist yet (`set_sums_sha256`, `may_block`, `wasmtime`, `DESC`) and
fail today for that reason. The good set's records carry `meta.wasmtime` `"49.0.0"`, and
`Inputs.wasmtime` is `"49.0.0"`.

**The synthetic good set** (`tests/unit/test_gather.py`) gains, so that honest blocks stay green:
- a goal check `DESC = "tests/checks/test_v1_2_portable_and_sealed.py::test_descriptors"` in
  `own-a`'s file, accepted `pass`, reported `blocked` by `descriptor limit` in the Windows record
  only;
- `RULE_NODE` reported `blocked` by `prior-art clones` in both `own-rest` records, accepted `pass`;
- `Case.may_block = {RULE_NODE: {"prior-art clones"}, DESC: {"descriptor limit"}}`;
- `S = "5" * 64` as the set's hash: in every record's `meta.set_sums`, in the newest line's
  `set_sums`, and as `Inputs.set_sums_sha256`;
- `PROBE`'s fuel accepted on darwin-arm64 and recorded on every system.

`test_the_good_set_passes_and_names_three_systems` must still pass with these, and its line is
now `three systems: darwin linux win32 on <W> · set <S>`.

**New mutations, each red with the line it names** (`MUTATIONS`):

| finding | the forgery | red line starts with | today (`forge_synthetic.out`) |
|---|---|---|---|
| F6 | `CLASS` blocked by `oracle` in both upstream records | `G4 linux/up-l <CLASS>: blocked by 'oracle', which its check does not call` | green |
| F6 | `SUITE` blocked by `three systems` in both, metrics gone | `G4 linux/up-l <SUITE>: blocked by 'three systems'` | green |
| F6 | `DESC` blocked by `descriptor limit` on Linux | `G4 linux/own-a <DESC>: blocked by 'descriptor limit', which does not block on linux` | green (tried on `RULE_NODE`; the set has no `DESC` yet) |
| F6 | `CLASS` blocked by `oracle` everywhere, accepted `pass` | `G5 <CLASS>: accepted pass, ran in no record` | green |
| F7 | `macos/own-rest` `suite` is `{}` | `G4 macos/own-rest: suite {} is not its 2 unit tests` | green |
| F7 | `suite` all zeros | `G4 macos/own-rest: suite` | green |
| F7 | `suite` one short: `{1, 0, 1}` | `G4 macos/own-rest: suite` | green |
| F7 | `suite` counts are strings | `G4 macos/own-rest: suite` | raises `TypeError` |
| F7 | `suite` holds `true` for `passed` | `G4 macos/own-rest: suite` | green |
| F7 | Linux record drops `SUITE`'s `fuel` | `G5 linux/up-l: <SUITE> records no fuel` | green |
| F7 | Windows record drops `PROBE`'s `fuel` | `G5 windows/own-a: <PROBE> records no fuel` | green |
| F7 | Linux record's `PROBE` fuel is `"7"` | `G5 linux/own-a: <PROBE> metric fuel is not a number` | green |
| F7 | macOS record's `PROBE` fuel is `NaN` (the build review's B1) | `G5 macos/own-a: <PROBE> metric fuel is not a number` | green before B1's fix |
| F7 | macOS record's `PROBE` fuel is `Infinity` (B1) | `G5 macos/own-a: <PROBE> metric fuel is not a number` | red only through the ratchet before |
| F6 | a `need` given as a list (B3) | `G4 linux/own-a <DESC>: blocked by ['descriptor limit']` | raised `TypeError` |
| F7 | a check's `metrics` given as a list (B3) | `G5 linux/own-a: <PROBE> metrics is not a mapping` | raised |
| F7 | macOS record's `PROBE` fuel ×10, `meta.wasmtime` `"48.0.0"` | `G2 macos/own-a: wasmtime '48.0.0' is not uv.lock's 49.0.0` | green |
| F7 | the same, `meta.wasmtime` null | `G2 macos/own-a: wasmtime None is not uv.lock's 49.0.0` | green |
| F7 | `suite` `{passed: 4, skipped: -2, total: 2}` (a negative skip) | `G4 macos/own-rest: suite` | green (the review ran it on real records) |
| F7 | `suite.passed` is `2.0` | `G4 macos/own-rest: suite` | green (the review ran it on real records) |
| F5 | newest line's `set_sums` is another hash | `G7 the newest acceptance is not on the release's set` | green |
| F5 | newest line has no `set_sums` (a line from before 085) | `G7 the newest acceptance is not on the release's set` | green |
| F5 | `linux/own-a`'s `meta.set_sums` is another hash | `G2 linux/own-a: set_sums is not the build's SHA256SUMS` | green |
| F5 | no `set_sums_sha256` handed on | `G1 the build job handed on no set-sums-sha256` | (input absent) |

The existing mutation "blocked by the kit" (`upstream kit`) keeps its line. "a failed unit test"
(`passed` one lower, `total` unchanged) keeps `G4 macos/own-rest: 1 unit test(s) failed`.

**Other new unit tests:**
- `test_gather.py`: `needs_called` on small sources: one literal need; two in one call; a need in a
  nested block; a call through a helper (not seen); a variable argument (not seen); a function
  whose source cannot be read (empty).
- `test_gather.py`: `hidden_ci_needs` is empty on the real repository, and names `file:line` on a
  synthetic tree for each of: a conftest fixture calling `needs.need("oracle")`; a `NEED_OF` map
  in a conftest holding `"oracle"`; a harness dict holding `"descriptor limit"`; a direct
  `pytest.skip("needs: three systems")` inside a `test_` body; a CI need in `tests/conftest.py`.
  A path piece (`JOB_DIR / "oracle"`) in a harness file is not flagged. (Fast tier; the real-repo
  case fails today only because the function does not exist.)
- `test_gather.py`: `locked_version("wasmtime")` reads a synthetic `uv.lock`, and the real one
  gives the version the judge runs (`importlib.metadata.version("wasmtime")`).
- `test_plugin.py`: `run_meta` gives `set_sums` as the SHA-256 of the artifact folder's
  `SHA256SUMS`, and null without one.
- `test_scoreboard.py`: the line `accept` writes carries `set_sums` from the run's meta.
- `test_history.py`: a history of format-2 lines without `set_sums` followed by one with it is
  intact and replays; `last_passed` reads it.
- `test_scan.py`: one mutation each, each red with its rule's line: the build job without the
  `set-sums` step; its output naming another file; the step after the `release-assets` upload; the
  gather step without `SET_SUMS_SHA256`, or with it bound to another output; a judge job setting
  `set-sums-sha256`; a judge job reading it; a rebuild job without `python3 --version`.
- `test_rules.py`'s existing checks of the real workflow (release rules, rebuild gate) then pass
  on the edited workflow.

## Acceptance criteria

1. **Seen failing first.** Every check in *The checks first* is run on main before the code
   changes, and fails there. The landing notes cite the run (the builder's equivalent of
   `forge_synthetic.out`).
2. **Every forgery is red, each with its own line, on the branch dry run's own records** (the
   pre-build review's F4). The a7 and 065 records can no longer prove this: since 065 landed, the
   gather is red at G3 on the a7 records (their collection predates 065's), and 085's own unit
   tests and judge change move `own-rest`'s unit share and the judge hash. So the builder
   downloads the 19 records of the branch dry run (criterion 6) and runs `forge_real.py`'s six
   forgeries on them, plus the wasmtime forgery (a macOS record's fuel ×10 with `meta.wasmtime`
   `"48.0.0"`), against the built gather at the branch's commit:
   - the honest records are red on exactly one line, the expected G7 `set_sums` line;
   - each forgery adds exactly its own rule's line or lines to that one, and nothing else.
   The synthetic set's table holds the rest.
3. **Honest records stay green under the new rules.** The synthetic good set passes. Run as
   functions (G4's block and tally rules, G5's metric rules, G2's wasmtime rule) on the a7 tag
   run's 19 records and on spec 065's dry run's 19 records, the new rules give no red line (as
   `prototype.out` shows for the prototype). Only those rules, since the records' collection,
   judge and `set_sums` predate the branch.
4. **The derivation is the CI's reality.** On the real repository, `collect()`'s `may_block`
   names exactly the checks that the branch dry run reports `blocked`, each blocked only on the
   systems `CI_NEEDS` allows. The landing notes list them (today: five). `hidden_ci_needs` is
   empty.
5. **The set's hash is carried end to end.** In the branch dry run, every record's
   `meta.set_sums` equals the build job's `set-sums-sha256`; that hash equals the SHA-256 of the
   `SHA256SUMS` inside the release tarball; and it differs from `sums-sha256`.
6. **G7, before and after the acceptance.** On the branch, no history line carries `set_sums`
   yet: line 79, main's newest, predates the field. So the branch dry run's gather is red by
   design, on exactly one line, `G7 the newest acceptance is not on the release's set
   (SHA256SUMS)`. Every other job passes on all three systems, and the gather prints no other red
   line. The landing notes quote both facts. After the lane accepts 085, the newest line carries
   `set_sums`, and the lane's first dry run of main must pass every job, the gather included
   (AGENTS.md rule 6b's dry run before the next tag). If it does not, the lane stops there.
   *Why not soften G7 for a line without the key:* only 085's branch ever runs this gather with
   such a newest line, and a soft clause would stay in the judge for good.
   It holds whatever lands between 085 and 037, since 086 lands before 037 and no build varies
   (Decision 8). The pre-build review's F3 asked for the order or a second criterion; the owner's
   answer to question 105 settled it.
7. **N5.** Both rebuild jobs' logs in the dry run show the runner's `python3 --version` line.
8. **The judge.** The fast tier and the full judge (`-n 3`) are green in the worktree, with no
   lost pass and no growth. The lane accepts with `--accept-judge "<reason>"`. No golden output,
   gap, upstream allowance or progress file is edited by the builder.
9. **Docs.** The README's *Releasing* sentence and the progress README's "Before a release" say
   the lane's newest acceptance is on the same `python.wasm` **and the same set (its
   `SHA256SUMS`)**; the CHANGELOG's 0.1.0a8 section names F5, F6, F7 and N5; spec 063 gains one
   line under G4: "Amended by spec 085: G1, G2, G4, G5 and G7 check the set's `SHA256SUMS` hash,
   blocked checks against their bodies, unit tallies and metric names."

## Judge changes

This spec changes the judge, on purpose, and says so here so the review sees the judge-hash line.

- `tests/harness/gather.py`, `tests/harness/plugin.py`, `tests/harness/scoreboard.py` and
  `tests/harness/scan.py`, as the *Design* says.
- `tests/unit/test_gather.py`, `test_scan.py`, `test_scoreboard.py`, `test_history.py` and
  `test_plugin.py`, as *The checks first* says.
- **Nothing that turns a run green.** No check is weakened, and no golden output,
  `tests/known_gaps.toml`, `tests/upstream/*.toml`, `tests/upstream/expected/` or
  `context/progress/` file is edited (AGENTS.md rule 4). Every change makes the gather stricter.
- **The ratchet does not move.** No check is added to or removed from the goal set; the new tests
  are unit tests. Fuel, bytes and passes are unchanged. The lane's acceptance is `--accept-judge`
  alone.
- **Shards.** The new unit tests live in `tests/unit/test_gather.py`, `test_scan.py`,
  `test_scoreboard.py`, `test_history.py` and `test_plugin.py`, which run in `own-rest` (macOS and
  Linux) as today. `tests/release_shards.toml` does not change.

## Coordination

- **The order.** 065 has landed (`9d89535`, history line 79). 086 lands before 037 (question 105,
  answered (b)); 085 does not depend on either.
- **Spec 065** (landed) added `no_trap_anywhere` to `gather.py`, upstream check kinds to
  `plugin.py`, a scoreboard line to `scoreboard.py`, `group_systems` to `shards.py`, and CPython
  groups to the plan. Its `gather.py` change is additive and touches no G rule (the review, READ).
  This draft is rebased onto it. 065's own dry run's records meet the new G4 and G5 rules
  (`records_065.out`, `prototype.out`).
- **Spec 037** (scipy, built) rewrote the same-bytes job and `scan.rebuild_gate_errors` for its
  exception, which the owner's answer drops; whatever of that remains when 037 lands sits beside
  N5's line in that function's facts tuple. Whichever lands second merges the two by hand;
  neither changes the other's rule.
- **Spec 037, spec 086 and G7: question 105, answered (b).** The pinned clang compiles ducc0's FFT
  to a different object on every run, so a set with scipy built on wasi-sdk 33 would be a new
  variant at every build, and both G7 clauses would fail on every release. The owner chose (b):
  spec 086 (wasi-sdk 34) lands before 037, and 037's same-bytes exception is dropped. So the
  gather's G7 keeps exact hashes of `python.wasm` and of the set's `SHA256SUMS` (Decision 8).
- **Specs 039 and 043** change the build job's zero-patch step (its tree count, 19 to 20 or 21).
  085's new build step is a separate step below the build shard. Their hunks are near, not shared.
- **Spec 064** (required status checks) would make the rulesets enforce what Decision 7 says only
  the owner's account protects today. Not a dependency.

## Disposition of the pre-build review (2026-10-19)

The review: `085-review/085-gather-checks-what-it-trusts-spec-2026-10-19.md` in the lane's
scratchpad (probes in `work/`, records in `dl-a7/` and `dl-065/`), on `31a8713` over `a6dfc17`,
re-checked by its reviewer against `9d89535`. Verdict: "ready once F1 to F4 are written in; F5 to
F8 written in or answered". Every finding is written in; none changes the design.

- **F1 (Medium), one field switches off the darwin fuel ratchet.** Written in: G2 binds every
  record's `meta.wasmtime` to `uv.lock`'s locked version (Decision 3; *Why*, item 3; *Design*,
  `locked_version`). Reproduced here on the synthetic set, with a control (`forge_synthetic.out`:
  ×10 fuel is red with `49.0.0`, green with `48.0.0` and with null). Two rows added to the table.
  `fuel_not_compared` stays not red, for the review's reason.
- **F2 (Medium), question 105's option (a) does not cover the set clause.** Written in: Decision
  8 says the snapshot varies under 037 too, so option (a) must define a canonical set digest, or
  the set clause gives way while the exception holds, by the spec that builds the answer;
  *Coordination* points to it. The lane adds it to question 105's text. *Superseded the same
  day:* the owner answered question 105 with (b), so no canonical digest is needed (Decision 8).
- **F3 (Medium), criterion 6 assumed 085 before 037.** Written in: the order 065, 085, 037 is
  stated (status, criterion 6, *Coordination*); criterion 6b gives the other order its two
  expected G7 lines and holds tags until question 105 is built; line 78 is now line 79.
  *Superseded the same day:* with question 105 answered (b), 086 lands before 037, and criterion
  6b is gone.
- **F4 (Low-Medium), criteria 2 and 3 could pass with nothing proved.** Written in: criterion 2
  runs the honest baseline and every real forgery on the branch dry run's own records (red only on
  the expected G7 line; each forgery adds exactly its own line); criterion 3 keeps the a7 and 065
  records for the new rules alone, run as functions.
- **F5 (Low), `hidden_ci_needs` missed non-literal arguments.** Written in: the scan flags any CI
  need string in `tests/checks/` and `tests/conftest.py` outside a test body, CI need strings used
  as arguments or container members in `tests/harness/` (the vocabulary's two files aside), and
  any `"needs: "` literal (Decision 1). Prototyped (`hidden_wide.out`): nothing in the repository,
  each planted spelling flagged. Path pieces in `jobs.py` (`JOB_DIR / "oracle"`) are why harness
  strings count only as arguments or members.
- **F6 (Low), `CI_NEEDS` should name `build`.** Written in: the map names `build`, `macos`,
  `linux` and `windows` (Decision 1).
- **F7 (Low), two over-claims.** Written in: Decision 4 says one hash names every file of the
  artifact set, and how the rest a run judges is bound; Decision 7 names the cheap lie left open
  (off-darwin metric values) beside those closed (with F1's).
- **F8 (Low), the open edges of the derivation.** Written in: Decision 1 lists where it fails
  open (shared parametrized rows, unreachable or conditional calls, any `.need` attribute) beside
  where it fails closed.
- **N1 (owner's call), a coarse cross-system fuel band.** Written as Decision 9: left out, with
  the reasons and the recommendation (leave it out unless the owner asks; a small follow-up if
  asked).
- **N2 and N3.** No action: N5's line runs before step 10's shim and breaks no scan rule; no
  schema bump is needed (Decision 5).

## Landing notes

### What was built

- `tests/harness/gather.py`: `CI_NEEDS` as a map from need to systems (`build`, `macos`, `linux`,
  `windows`); `allowed`, `needs_called`, `hidden_ci_needs` (with `VOCABULARY_FILES` skipped before
  parsing, c2, and module constants flagged in `tests/harness/`, c1) and `locked_version`;
  `collect()` returns `may_block`; `Inputs` gains `set_sums_sha256`, `wasmtime` and `may_block`.
  G1 (`set-sums-sha256`), G2 (`set_sums`, `meta.wasmtime`), G4 (blocks against the body and the
  system; the tally as whole numbers equal to the share), G5 (accepted metric names on every
  system; metric values numbers; the exemption through `allowed`), G7 (`set_sums`), the merged
  record's `meta.set_sums`, and the green line `… on <wasm> · set <set_sums>`. `merge` adds only
  whole-number tallies, so a malformed one is a G4 line, not a crash.
- `tests/harness/plugin.py`: `run_meta` records `set_sums`. `tests/harness/scoreboard.py`: the
  line carries it.
- `tests/harness/scan.py`: rule 6 (the build's `set-sums-sha256`, from
  `build/artifacts/SHA256SUMS`, before the upload), rule 7 (`SET_SUMS_SHA256` in the gather's
  `env:`), rule 10 (only build sets `set-sums-sha256`, only the gather reads it), and the
  rebuild gate's `python3 --version`.
- `.github/workflows/release.yml`: the build job's `set-sums` step and output; the gather's guard
  (the same `case` and length test as `WASM_SHA256`) and `env:`; `python3 --version` in both
  rebuild jobs' tools step.
- Tests: 20 forgeries and a control in `tests/unit/test_gather.py`, with the derivation's, the
  scan's and the lock's unit tests; one each in `test_plugin.py`, `test_scoreboard.py` and
  `test_history.py`; nine in `test_scan.py`.
- Docs: the README's *Releasing* sentence, the progress README's "Before a release", the
  CHANGELOG under 0.1.0a8, and spec 063's amendment line under G4.

### Seen failing first (EXECUTED)

- `seen_failing_gather.out`: the new `test_gather.py` against today's gather (the three new
  `Inputs` fields dropped by `old_inputs.py`, since today's gather has none): all 20 forgeries
  fail, the good set fails only on its new green line, the 36 old mutations and the control pass.
- `seen_failing_others.out`: the new scan, plugin, scoreboard and history tests against today's
  code: 12 fail, the other 320 pass.

### Real records, against the built gather (EXECUTED, `built_on_real.out`)

Criterion 3, and the record-level part of criterion 2 that does not need the branch dry run. On
the a7 tag run's 19 records and on spec 065's dry run's 19 records, the honest baseline holds no
line of the new rules (G4's block and tally lines, G5's metric lines, G2's wasmtime line); its
G2 `set_sums`, G3 and G7 lines are the expected ones of records that predate this branch. Each
of seven forgeries adds exactly its own rule's lines to that baseline and nothing else, on both
runs: four for the no-network check blocked by `oracle` (three G4, one G5), two for `numpy-core`
blocked by `three systems`, two for the descriptor check on macOS and Linux, one each for the two
forged tallies, the dropped fuel, and ten times the fuel under `wasmtime` `48.0.0` (G2; the
ratchet stays silent there, which is why G2 binds it).

### The judge (no `--accept`; EXECUTED)

Against a private copy of main's set, `build/085/set` (a clone of
`build/sets/s-c50ca51fae5eb55b-c9dcb5b8`), through `WASI_PYTHON_ARTIFACTS`.

- **Full judge**, `uv run pytest -n 3` on `9128176`, a clean tree (`build/085/full-n3.log`; its
  record kept as `build/progress/latest.json`):
  `wasi_python v1: 495/623 pass · 3 gap · 125 blocked · 0 fail (unit suite 1622/1630, 8
  skipped)`; `ratchet vs b91e0eaa4e: lost 0 · absent 0 · unrun 0 · unrun locally 49 · gained 0 ·
  grew 0 · upstream unrun 99 · judge changed: tests/harness/gather.py, tests/harness/plugin.py,
  tests/harness/scan.py and 6 more`; `2117 passed, 133 skipped, 3 xfailed`. The blocked checks are
  the worktree's missing source trees, clones, oracle, wheel and wasmtime CLI, as in any worktree.
  The record's `meta.set_sums` is `c9dcb5b84ae2…`, the set's own `SHA256SUMS`, as Decision 4
  says.
- **Fast tier**, `uv run pytest -m "not slow" -n 3`, before the Landing notes existed
  (`build/085/fast-1.log`): one fail, `test_specifications_have_their_header_and_sections`, on
  this spec's missing `## Landing notes` section and header form; fixed in the spec, and the full
  judge above has 0 fail. `ruff check` and `ruff format --check` are green on `src/` and `tests/`.

### Amended at build, each with its reason

- **`merge` adds only whole-number tallies.** A tally of strings made the merged record raise
  before any red line was printed; it is now a G4 line (Decision 2) and left out of the sum.
- **The scan's unit test also checks the gather's guard step** (`SET_SUMS_SHA256` tested as 64
  hex), which no rule held; and the spec's header line takes the form the rules check reads
  (`- **Research it stands on:**`).
- **c1 and c2 taken** (the confirmation's builder notes): a module constant holding a bare CI need
  in `tests/harness/` is flagged; a need passed to a helper from inside a check's body is named
  in Decision 1 as found only at a dry run; `VOCABULARY_FILES` are skipped before parsing.

### Revised against the build review (2026-10-19)

The review: `085-review/085-gather-checks-what-it-trusts-build-2026-10-19.md` in the lane's
scratchpad, "lands once B1 is fixed". Each fix was seen failing first (`seen_failing_build_review.out`: the four new forgery rows and the scan's spellings test failed against the
built code; 74 others passed).

- **B1 (Medium), `NaN` fuel passed the darwin ratchet.** Fixed: `_number` accepts an `int` or a
  finite `float` (`math.isfinite`). Forgery rows for `NaN` and `Infinity` on a macOS record. On
  the real records, every fuel `NaN` in macos/own-guest now adds exactly its 124 G5 lines, on
  both runs (`built_on_real.out`).
- **B2 (Low), decorators and defaults counted as the body; harness class attributes and
  conditional expressions unseen.** Fixed: only a `test_` function's body statements are inside;
  in `tests/harness/`, a CI need assigned at module or class level, directly or through an `if …
  else`, is flagged. A local variable of a harness function stays unseen, and Decision 1 says
  so. Four new spellings in the scan's unit test.
- **B3 (Low), a list `need` or `metrics` raised.** Fixed: a `need` that is not a string is G4's
  `blocked by …` line (and `allowed` refuses it; the merged record carries its `repr`); `metrics`
  that is not a mapping is G5's `… metrics is not a mapping`, checked before the ratchet, whose
  `AttributeError` is now caught as "not comparable". Two forgery rows.
- **The owner's answers.** Question 105 (b): Decision 8, *Scope*, criterion 6 and *Coordination*
  now say spec 086 lands before 037 and the gather keeps exact hashes; criterion 6b is gone.
  Decision 9: declined for now, a possible later specification.
- **The judge after the fixes:** the affected unit tests and the rules (453 passed, 2 skipped),
  then the fast tier, `uv run pytest -m "not slow" -n 3` on `c378ba2`, a clean tree, against
  `build/085/set` (`build/085/fast-2.log`): `wasi_python v1: 478/623 pass · 1 gap · 25 blocked ·
  0 fail · 119 deselected (unit suite 1626/1634, 8 skipped)`; `ratchet vs b91e0eaa4e: lost 0 ·
  absent 0 · unrun 0 · unrun locally 23 · gained 0 · grew 0 · upstream unrun 99 · not selected 43
  · judge changed: …`; `2104 passed, 33 skipped, 1 xfailed`. The fixes touch only `gather.py`
  and its unit test, and no goal check, so the full judge was not run again.

### For the lane

- **Criterion 2's branch-dry-run part, criteria 4 to 7.** Push the branch and dispatch the
  release dry run. Expected: every job passes on all three systems except the gather, whose only
  red line is `G7 the newest acceptance is not on the release's set (SHA256SUMS)` (history line
  79 has no `set_sums`). Then run `built_on_real.py` on that run's own records, with
  `set_sums_sha256` set to the build's hash: the baseline red on that one line, each forgery adding
  only its own. Criterion 4: the run's `blocked` checks are the five `may_block` names, each on
  its allowed systems. Criterion 5: each record's `meta.set_sums` equals `set-sums-sha256`, the
  SHA-256 of the tarball's `SHA256SUMS`, and differs from `sums-sha256`. Criterion 7: both
  rebuild logs show `python3 --version`.
- **After acceptance** (`--accept-judge`), the first dry run of main must pass every job, the
  gather included (criterion 6).
- **Textual merges.** 037's branch edits the same-bytes job and `scan.rebuild_gate_errors` beside
  the `python3 --version` fact (its exception is dropped by question 105's answer, so those hunks
  may shrink); 039 and 043 change the zero-patch step's tree count, a few lines
  above the build job's new step. Each is near, none shared.

#### Claim list (wave 1)

Taken from the builder's full judge on `9128176` (`-n 3`, `build/085/full-n3.log`: `495/623 pass ·
3 gap · 125 blocked · 0 fail`, unit suite 1622/1630; `lost 0 · gained 0 · grew 0`), its fast tier
after the build review's fixes on `c378ba2` (`build/085/fast-2.log`: 0 fail, unit suite
1626/1634, `gained 0 · grew 0`), and the build review's full judge on `337ceb5` (`495/623 pass ·
0 fail`, unit suite 1626/1634, `lost 0 · gained 0 · grew 0`). Own base: main `9d89535`.

- **New checks:** none in the goal set. The unit suite gains its new rows in
  `tests/unit/test_gather.py`, `test_scan.py`, `test_scoreboard.py`, `test_history.py` and
  `test_plugin.py`; its total moves 1587 → 1634 (+47; 8 skipped) on the own base.
- **Retired checks:** none. No `--retire`.
- **Rows that grow:** none; nothing guest-side changes. No `--accept-growth`.
- **Passes that move:** none. No `--accept-fewer-passes`.
- **The judge hash changes**, in nine files: `tests/harness/gather.py`, `tests/harness/plugin.py`,
  `tests/harness/scan.py`, `tests/harness/scoreboard.py`, `tests/unit/test_gather.py`,
  `tests/unit/test_history.py`, `tests/unit/test_plugin.py`, `tests/unit/test_scan.py`,
  `tests/unit/test_scoreboard.py`. Not judged but changed: `.github/workflows/release.yml` (the
  build job's `set-sums-sha256` output and the rebuild logs' `python3 --version`), which makes
  this entry build-class.
- **What changes for the acceptance itself:** from this entry on, every run record carries
  `meta.set_sums` (the artifact set's own `SHA256SUMS` hash), and `--accept` writes it into the
  history line beside `artifact`. So the wave's acceptance line is the first with `set_sums`,
  and the wave's dry run's gather compares it (G7): it is green only if the lane's local set and
  the CI build job's set have the same `SHA256SUMS`, which the rebuild-from-pins compare already
  asks (criterion 6).
- **The flags** (paste-safe):
  - `--accept-judge "085: gather checks what it trusts; a blocked check only by a need its own body names, on a system that lacks it; each unit tally equal to its share; every accepted metric name on every system, each a finite number; meta.wasmtime bound to uv.lock; the set SHA256SUMS hash in every record and in the history line, compared in G1, G2 and G7; the rebuild jobs print python3 --version; the hidden-needs scan"`
  - no `--accept-growth`, no `--accept-fewer-passes`, no `--retire`.
- **Sameness:** the reviewer's record is `085-review/build-review/full-n3-337ceb5-latest.json` in
  the lane's scratchpad (on `337ceb5`, the tip before this list). The builder's
  `build/progress/latest.json` was later overwritten by a unit-only run (411 tests, no goal
  checks) and is not a comparison record. A difference against the reviewer's record is clean only
  when it is a check blocked in that worktree (125, the upstream groups and the rebuild checks) or
  a row another entry claims.
- **Not yet read:** this branch has no CI run (the wave's entry criterion 2; build-class, so rule
  2's "built" test asks for one). Criterion 2's branch dry run and criteria 4, 5 and 7 above are
  first seen in a dry run.

#### Rebased onto wave/01 (`70bb1a2`: main `7d0649d` plus 087; 2026-10-19)

`git rebase wave/01` replayed 085's seven commits, from main `9d89535`. One hunk conflicted, and
I resolved it as 085's builder; the rest merged cleanly (`README.md`,
`context/progress/README.md`, `tests/harness/plugin.py`). `git range-diff` shows six commits `=`
and the build commit `!`, by that hunk alone.

1. **The build commit, `CHANGELOG.md`, `## 0.1.0a8 — unreleased`:** both sides kept. 078's
   bullet first, as wave/01 has it, then 085's, then the bullets wave/01 already had after it
   (065, 083, 087's two). No wording changed.

**Semantic changes:** none in 085's code. I read what wave/01 changed in 085's areas since
`9d89535`:
- `tests/harness/plugin.py`: 089's litter warning in `pytest_configure`, apart from 085's
  `set_sums` in `run_meta`; both kept.
- New harness files `litter.py` (089) and `wat.py` (087), and 078's `guest.py`: the hidden-needs
  scan finds nothing on the merged tree (`test_gather.py`'s scan of the repository passes).
- `scripts/assemble_artifacts.py` (087's second carried patch) and the release workflow:
  untouched by 085's hunks.

**The fast tier on `b1c2364`** (`uv run pytest -m "not slow" -n 3`, against this worktree's copy of
main's set `s-c50ca51fae5eb55b-c9dcb5b8`, `build/085/fast-wave01.log`): `wasi_python v1:
523/663 pass · 1 gap · 25 blocked · 3 fail · 111 deselected (unit suite 1689/1697, 8 skipped)`;
`ratchet vs 9c6ba6db2d: lost 1 · gained 5 · grew 0`; `ruff check` and `ruff format --check` green.
The three fails and the lost pass are 087's rows, red only because no set with 087's patch exists
in this worktree: `test_manifest_recipes_match_the_tree` (main's MANIFEST does not list
`0002-timeout-ticks.patch`; the lost pass) and
`test_a_timeout_past_2_147_seconds_fires[plain]` and `[snapshot]` (main's regex binary). No unit
test and no 085 row is red.

**For the wave's rebuild and acceptance (set_sums and 087's set):**
- The acceptance must judge a set rebuilt from the wave tip, which carries 087's patch
  (`python.wasm` and the snapshot +202 bytes each), with `build/artifacts` that set, not
  `WASI_PYTHON_ARTIFACTS` pointing at an older one. From 085 on, `--accept` writes the hash of
  that set's own `SHA256SUMS` into the history line as `set_sums`. Main's frozen set
  `c9dcb5b8…` cannot be the accepted set: its MANIFEST loses `test_manifest_recipes_match_the_tree`.
- The wave's dry run's gather then requires the CI build job's `set-sums-sha256` to equal that
  `set_sums` (G7), and every record's `meta.set_sums` to equal it too (G2). Before 085, G7
  compared `python.wasm` only; now every file `SHA256SUMS` lists must match between the lane's
  rebuild and CI's Linux build: the snapshot, the zip, `MANIFEST` and the licences as well. The
  rebuild-from-pins compare the lane already makes against the CI build job's `SHA256SUMS` is
  exactly that check, so a difference there means the dry run's gather will be red on G7.
- Older history lines have no `set_sums`; G7 reads only the newest acceptance, the wave's.

## One line

The gather stops believing what a record says about itself on three points it can check (a
blocked check must be blocked by a need its own body calls, on a system that lacks it; a unit
tally must be its share; a passing check must carry the metrics the lane accepted, on the locked
wasmtime), and ties the
lane's acceptance to the whole set by its own `SHA256SUMS`, not only `python.wasm`; it checks
consistency, not authenticity.
