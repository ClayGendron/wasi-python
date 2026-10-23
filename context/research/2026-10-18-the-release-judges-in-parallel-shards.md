# The release judges in parallel shards

- **Status:** executed, 2026-10-18 (time box: one session; judge time on the shared machine about 11 minutes, one group at a time). Nothing in the repository's code changed. The evidence is in `2026-10-18-the-release-judges-in-parallel-shards/` beside this memo; the raw logs are in the main tree's git-ignored `build/reviews-evidence/063-spec/`.
- **Revised:** 2026-10-18, after spec 063's pre-build review. Its findings changed the design in places this memo describes; the specification is the record of the design, and the paragraphs below that changed say so in brackets. The measurements are unchanged.
- **Owner:** Clay Gendron
- **Researcher:** the drafting agent (Claude Opus 5.5) of spec 063.
- **Asked by:** the owner, 2026-10-18 (paraphrased closely): the release rebuilds from the pins on three hosts, then verifies with the judge on Ubuntu, Windows and macOS. Split the judge so its pieces run in parallel. Run every pulled-in package's own test suite (numpy, pandas, scipy and the rest) as separate parallel jobs beside our own judge. The goal is a release that moves quicker without giving up the suite's reliability. The lane shaped it into five points, which this memo tests one by one.
- **Feeds:** `../specifications/063-the-release-judges-in-parallel-shards.md`.
- **Stands on:** spec 004 (the release workflow), 050 and 051 (the upstream suites), 052 (the judge on several cores; its census and its sameness function), 057 (the release ties what it signs to what it built; in build review, lands first), 059 (native rebuilds), 062 (the history in volumes; `systems_that_passed`), and `context/progress/README.md`, "Before a release".

Labels: **EXECUTED** (run here, output in the evidence folder or the named log), **READ** (read in a file, a log or a document, cited), **INFERRED** (reasoned from those, not run).

## 1. What the release does today

**The timeline (EXECUTED, `gh run view 39171852747 --json jobs`; `timeline.txt`).** The newest dry run, on main after spec 059, took **33.4 minutes**:

| job | starts at | takes | what takes the time |
|---|---|---|---|
| build and judge (macos-15) | 0.1 | 26.7 | build 12.3, zero-patch 0.5, **the judge 11.7**, assets 1.4 |
| rebuild ubuntu-24.04-arm | 0.0 | 10.0 | build 9.3 |
| rebuild ubuntu-24.04 | 0.0 | 15.8 | build 15.1 |
| verify ×3 | 26.8 | 4.2 to 6.5 | a subset of the judge, 3.5 to 5.8 |
| same-bytes | 26.8 | 0.3 | |

The critical path is build, then the whole judge serially on the same macOS runner, then verify. The 0.1.0a5 tag run (`39152890225`) took 89.0 minutes, all of it the emulated x86_64 rebuild that spec 059 removed; its build job's judge took 6.4 minutes on another macOS runner. Runner speed varies by about two to one between runs (READ, both timelines).

**What "the judge" means in the release today (READ, `.github/workflows/release.yml`; the build log).** Only the build job runs `uv run pytest`. Its scoreboard on run 39171852747:

```
wasi_python v1: 361/397 pass · 2 gap · 34 blocked · 0 fail   (unit suite 1190/1197, 7 skipped)
blocked by: upstream kit 31 · oracle 1 · prior-art clones 1 · three systems 1
ratchet vs fdb06c26f1: lost 0 · absent 0 · unrun 0 · unrun locally 21 · gained 1 · grew 0 · upstream unrun 31
1551 passed, 41 skipped, 2 xfailed in 621.78s (0:10:21)
```

So:

- **The upstream suites never run in the release.** Their 31 checks are blocked by `upstream kit`, a need that is not protected, so the run stays green. That is spec 050's recorded-not-rule gap.
- **The verify jobs on Linux, Windows and macOS do not run `uv run pytest`.** They run a named subset: the four v1.1 to v1.4 check files and three unit files, against an empty baseline, and assert that nothing is blocked but `oracle`, `three systems` and `wheel`. The owner's description ("running `uv run pytest` on each") is the intent, not today's state.
- **Every accepted run in the history is darwin-arm64** (EXECUTED: 63 lines, one platform). The full judge has never run, accepted, on Linux or Windows. Nothing measures today whether the judge's own tooling tests (the plugin, the scoreboard, the landing lane, the build scripts) pass there.

**Where the judge's time goes on a CI macOS runner (EXECUTED, `perfile.py` over the build log; `build-judge-per-file.txt`, `collect-per-file.txt`).** 1,594 items collected in 48 files. The time up to each progress line is charged to its file, so small files can be under-charged; the shape is clear:

| file | seconds | items |
|---|---|---|
| tests/checks/test_v1_4_embedding.py | 220.7 | 151 |
| tests/checks/test_v1_2_hostile_guest.py | 54.0 | 60 |
| tests/unit/test_build_progress.py | 46.7 | 83 |
| tests/checks/test_v1_5_rebuild_from_pins.py | 46.0 | 27 |
| tests/unit/test_landing_lane.py | 44.8 | 42 |
| tests/checks/test_v1_3_data_stack.py | 41.1 | 27 |
| tests/unit/test_runner_mounts.py | 26.1 | 69 |
| tests/unit/test_several_cores.py | 25.9 | 34 |
| tests/checks/test_v1_1_artifact_set.py | 19.3 | 28 |
| tests/checks/test_rules.py | 16.9 | 25 |
| everything else (38 files) | 78.3 | 1,048 |

One file, the embedding checks, is 36% of the judge. It is the floor of any split by file.

**CI hosts compared (EXECUTED, the three verify logs of run 39171852747; `verify-per-file.txt`).** On the same subset, ubuntu-24.04 took 300 s and macos-15 295 s in the test step; per file they agree within 15% (embedding 214.6 s against 209.0 s). windows-2025 took 213 s for the step (its log lines carry a byte-order mark the parser did not read, so no per-file split). In the a5 tag run the same step took 196 s, 259 s and 288 s. INFERRED: the three systems run the guest at about the same speed, within the runners' own spread.

**Per-job overhead (EXECUTED, the verify jobs' steps).** Checkout, setup-uv, the download and the unpack take 13 to 31 s together; the first `uv run` syncs the environment inside the test step. INFERRED: a shard job costs about 45 s before its first check, and about a minute more when it must fetch the upstream kit and two source tarballs (section 3).

## 2. The upstream groups, each run alone (EXECUTED)

Each of the eleven groups ran in its own pytest process, one after another, on the frozen set `s-4eb5418a2b1bb553` in the 063 worktree, with links to the main tree's numpy and pandas trees and the kit (`groups.sh`; `groups-table.txt`). The machine was shared with the lane and two builders: load average 45 to 105 on 10 cores. So the wall times below are inflated; fuel and passes are not.

| group | fuel | passes | wall (loaded) | wall (quiet, spec 052's memo, READ) |
|---|---|---|---|---|
| pandas-groupby | 474.7 G | 22,227 | 137.6 s | 79.7 s |
| pandas-frame | 338.1 G | 10,852 | 143.7 s | 57.6 s |
| numpy-core | 202.2 G | 9,519 | 34.1 s | 31.1 s |
| numpy-others | 175.3 G | 7,269 | 29.2 s | 26.2 s |
| numpy-lib | 131.2 G | 4,825 | 24.6 s | 22.1 s |
| pandas-reshape | 98.0 G | 2,664 | 35.6 s | |
| pandas-io-parser | 88.7 G | 3,474 | 46.4 s | |
| pandas-io-formats | 53.8 G | 977 | 15.6 s | |
| pandas-tslibs | 33.4 G | 590 | 16.2 s | |
| pandas-libs | 22.0 G | 1,063 | 13.1 s | |
| pandas-internals | 16.4 G | 258 | 13.2 s | |
| **all eleven** | **1,633.8 G** | **63,718** | 509 s | about 266 s |

- **Alone gives the same answer as the lane's whole run.** Every group passed. Every `passes` equals `accepted.json`'s darwin-arm64 value exactly, and every fuel is within **7.3e-8** of it (the ratchet's tolerance is 1e-4). The lane accepted those values inside one serial run of the whole judge. So a group needs nothing an earlier check left in the process: it can be its own job.
- **The stage must hold every package's tree.** `numpy-lib` run with only numpy's tree present (pandas' tree moved aside) still passed with 4,825 passes, but its fuel moved by **3.9e-5**, about 500 times the residual, and within a factor of three of the tolerance. The harness already says why (`upstream.Session.prepare`: "the guest's fuel depends on the whole grant"). INFERRED: a shard that fetched only its own package's tree would sit close to a false growth on macOS, where its fuel is compared with the lane's. Every upstream shard fetches every tree.
- **Fuel predicts the time.** In the quiet runs, groupby, frame, numpy-core, numpy-others and numpy-lib cost 0.154 to 0.170 s per G of fuel. INFERRED for CI: about 1.5 to 2.5 times the quiet Mac (the CI macOS judge took 622 s; spec 052's quiet serial judge, then smaller, took 580 s with the upstream suites, about 314 s without). So groupby needs about 2 to 3.3 minutes of guest time on a CI runner, frame 1.4 to 2.4, and the six small pandas groups together 1.3 to 2.2.

**Our own judge's parts, locally.** The fast tier took 3 min 48 s on this machine (READ, AGENTS.md, 2026-10-18); not re-run, to keep within the box. The slow checks outside the upstream file (the guest jobs in data stack and matplotlib) took **31.4 s**, the oracle check blocked there (EXECUTED, `groups-table.txt`, last line); spec 052 measured the oracle at 21.9 s (READ).

## 3. What a shard must fetch, and verify (READ, the harness; INFERRED where said)

An upstream check runs only when every need is met: `artifact dir`, `snapshot binary`, `stdlib zip`, `manifest`, `wasmtime-py`, `source tree <package>` and `upstream kit` (`tests/checks/test_v1_3_upstream_suites.py::_need`). In a shard that means:

| input | where it comes from | verified by |
|---|---|---|
| the artifact set | the build job's `release-assets`, by id | spec 057's check step (SHA256SUMS against the handed-on hash, every file, nothing else) |
| the kit (7 wheels) | `uv run python tests/upstream/fetch.py`, the URLs of `tests/upstream/kit.txt` | `fetch.py` (SHA-256 per line, rename only after the match); `kit_met` again at use; unpacked by `safe_unzip`, run only in the guest |
| `numpy-2.5.2.tar.gz`, `pandas-3.0.6.tar.gz` | their `get` lines in `scripts/00_download.sh` | `downloads/SHA256SUMS`; then `upstream.tie_errors`: the tarball's hash equals the artifact's MANIFEST pin |
| the trees `build/numpy-2.5.2`, `build/pandas-3.0.6` | the tarballs unpacked, then `scripts/steps/apply_patches.sh` (numpy carries two patches, pandas none) | `tie_errors` (every patch's hash equals MANIFEST's), the stage copies tarball members and patch-created files only; `test_source_tree_matches_its_tarball[numpy]` and `[pandas]` can run in the same shard |

- **Not `scripts/00_download.sh`.** It fetches the 35 pins of the running host's key and has no key for Windows (READ, its `case "$HOST_KEY"`). A shard needs two of them. INFERRED: a small `--trees` mode in `tests/upstream/fetch.py` that reads the two URLs from the `get` lines (one source of URLs, spec 003, Decision 1), the hashes from `downloads/SHA256SUMS`, unpacks with `tarfile`'s `data` filter, and runs the same `apply_patches.sh` the build runs.
- **Windows needs `sh` and `git` for the patches.** `apply_patches.sh` uses `git apply` in a cleared environment, `mktemp`, `find` and `touch -r`. Git for Windows provides them under the bash shell the verify job already uses (INFERRED; never run on Windows: the first dry run is the measurement).
- **The other needs in a shard.** `wheel`: the shard copies the wheel from `release-assets/` into `dist/`, so `test_wheel_carries_the_artifact_set` runs everywhere (today it is blocked on verify). `git history`: a checkout with `fetch-depth: 0`. `compile records` and `source tree <c>` for the other thirteen components exist only on the build host: those checks stay in the build job. `oracle` and `prior-art clones` are local tooling; they stay blocked in CI, as today, and are not protected needs.

## 4. GitHub's limits (READ, GitHub's documentation, 2026-10-18)

- **Cost.** The repository is public (EXECUTED: `gh repo view` → `"visibility":"PUBLIC"`, owner type `User`). "GitHub Actions usage is free for self-hosted runners and for public repositories that use standard GitHub-hosted runners"; larger runners "are always charged for, even when used by public repositories" (docs.github.com, *GitHub Actions billing*). Every runner here is standard: minutes cost nothing.
- **Concurrency** (docs.github.com, *Actions limits*): standard runners, per account, Free **20 jobs at once, 5 of them macOS**; Pro 40 and 5; Team 60 and 5; Enterprise 500 and 50. The account's plan is not visible to the agent's token (`gh api user` → `"plan": null`), so the plan must fit Free.
- **Runner sizes** (docs.github.com, *GitHub-hosted runners*): ubuntu-24.04, ubuntu-24.04-arm and windows-2025: 4 CPUs, 16 GB; macos-15 (arm64): 3 CPUs (M1), 7 GB.
- **Other limits** (*Actions limits*; *Workflow syntax*): a job may run 6 hours; a matrix may hold 256 jobs; job outputs at most 1 MB per job and 50 MB per run. "When using a matrix, job outputs will be combined from all jobs inside the matrix … Ensure that the output name is unique, otherwise the last matrix job that runs will override the output value", with an example in which each leg writes `output_<version>` and the next job reads all three. So a matrix can hand on one id per leg, under per-leg names.
- **Artifacts.** `actions/download-artifact` at the pinned commit takes `artifact-ids` "comma-separated"; several ids land in one folder per artifact name unless `merge-multiple` (READ, its `action.yml` at `9000827`). The documented artifact quota (500 MB on Free) is stated for private repositories' billing; for public ones the page says nothing (READ). A shard's record is about 150 KB (INFERRED from `build/progress/latest.json`'s size).

## 5. The shard plan

**Which shards (INFERRED from sections 1 and 2; CI seconds from the build log).**

| shard | selection | systems | CI guest time (est.) |
|---|---|---|---|
| `build` | `tests/checks/test_v1_5_rebuild_from_pins.py` (needs the build tree, its compile records and every component's tree) | the build job (macOS) | 46 s, measured |
| `own-embedding` | `tests/checks/test_v1_4_embedding.py` | macOS, Linux, Windows | 221 s, measured |
| `own-guest` | the other guest check files and the runner's unit files that start guests (hostile guest, data stack, artifact set, the zips folder, matplotlib, portable and sealed, public API, runner mounts, runner grants) | macOS, Linux, Windows | about 175 s |
| `own-rest` | every collected item no other shard of the plan takes: the rules, the harness's and the build tooling's unit tests, and new files by default | macOS, Linux, Windows | about 180 s |
| `upstream-groupby` | pandas-groupby | Linux | 120 to 200 s |
| `upstream-frame` | pandas-frame | Linux | 85 to 145 s |
| `upstream-numpy-a` | numpy-core, numpy-lib | Linux | 80 to 135 s |
| `upstream-numpy-b` | numpy-others, pandas-reshape | Linux | 60 to 105 s |
| `upstream-pandas-small` | pandas-io-parser, -io-formats, -tslibs, -libs, -internals | Linux | 50 to 80 s |
| `upstream-macos` | numpy-lib | macOS | 35 to 55 s |
| `upstream-windows` | pandas-io-parser | Windows | 30 to 45 s |

- **Our own judge on all three systems, split in three.** The embedding file alone is the floor (221 s). The other two are balanced against it. `own-rest` is the catch-all, so a new test file is never outside the release.
- **The package suites in full on Linux, in five shards.** Eleven jobs would cost eleven times the fixed minute and eleven of the twenty slots; five shards keep every shard under the embedding floor. A group is the unit: a shard holds whole groups, with their classes.
- **One representative group on macOS and on Windows.** macOS is the platform the lane accepts on, so its fuel is compared with the lane's to 1e-4: `numpy-lib`, cheap and full of file I/O (`npyio`). Windows is where the host's file system differs most (spec 058): `pandas-io-parser` reads files, compressed files and encodings through the guest's WASI calls. Every group already runs on darwin-arm64 at each landing; section 6's acceptance rule ties the release to that run.

**Concurrency at the fan-out (INFERRED).** macOS: three own shards, `upstream-macos` and `verify` = 5, the macOS limit. Windows: 5. Linux: three own, five upstream, `verify` = 9, plus `same-bytes` and possibly the x86_64 rebuild still running. Total 19 to 21 against Free's 20: at most a job or two waits about a minute for a `verify` job (about 1 minute) to free its slot. On Pro nothing waits.

**Expected wall time (INFERRED; today 33.4 minutes for a dry run).**

| stage | minutes |
|---|---|
| build: build 9.8 to 12.3, zero-patch 0.5, the `build` shard about 1, assets 0.8 to 1.4 | 12 to 15.5 |
| the shards in parallel: the longest is `own-embedding` (221 s and about 45 s of setup) or `upstream-groupby` | 4.5 to 5.5 |
| gather: checkout, sync, downloads, one collection, the merge | about 1.5 |
| attest, publish (a tag only) | about 1 |

A dry run: **about 18 to 22 minutes**; a tag run about 19 to 23. That is a third faster than today, while adding the eleven upstream groups (1.6 T fuel) and our own judge on Linux and Windows. The x86_64 rebuild (15.8) and `same-bytes` run beside the shards, off the critical path.

## 6. The gather

One job after every shard. It is spec 052's controller merge, across machines: each shard is a serial run that writes its own `latest.json`; the gather reads them all and decides.

- **Integrity, as spec 057 does for assets.** Each shard job hashes its record and hands on two outputs, the record's artifact id and its SHA-256. The gather guards each id, downloads by id with `digest-mismatch: error`, and accepts a file only if its SHA-256 is one a shard job handed on; an extra file is red. A matrix shares one output namespace (spec 057, Decision 4). Here the legs of one system's job share every host-side input as well: the same runner image, the same `uv.lock` wheels for that platform, the same code. The upstream legs add only data (the kit runs in the guest; the tarballs are unpacked, not run). INFERRED: a leg that could forge another leg's output of the same system could forge its own record in place too, so per-leg names inside one system's job give nothing away. What 057 protects, one host's inputs casting another host's vote, stays protected: macOS, Linux and Windows are three jobs, each with its own outputs.
- **Each record says what it is.** `meta.commit` is the gather's own commit; `meta.artifact` is the SHA-256 of the release's `python.wasm` [as revised: handed on by the build job as `wasm-sha256`, so the gather holds no assets and spec 057's rule 16 stands]; `meta.judge.hash` is the judge hash the gather computes from its own checkout; `meta.platform` names the shard's system; `meta.shard` names the shard the output name said; `dirty` false; no `foreign`; no `partial`; serial (`workers` 0); no override but `--progress-latest`. Any difference is red.
- **No shard selects nothing, and none selects less than its share.** The gather collects the judge once at its own commit (`pytest --collect-only`, no artifacts needed) and applies the plan to it. Each record's run checks must be exactly its shard's goal checks, and its unit tally exactly the shard's count of unit tests [as revised: each count may be zero, the selection as a whole not; the unit tests are compared by a digest of their node ids, and every collected item must be in some share]. An empty selection is red twice: in the plan's own rule check, and in the plugin, which refuses a `--shard` that selects nothing.
- **Against the lane's acceptance.** Each shard already runs the ratchet against the checkout's `accepted.json`, as the build job's judge does today ("lost 0 · absent 0 · … · grew 0" above). The gather re-runs `scoreboard.compare` on every record, then checks the union: every accepted pass and gap ran somewhere (only `oracle`, `prior-art clones` and `three systems` may block), and an upstream group's `passes` and `passed_digest` agree on every system that ran it.
- **The release's `python.wasm` is the lane's accepted artifact** [as revised: a history line records only `python.wasm`'s hash, so this ties that file alone; the other files are judged by the release's shards; on a tag the release's judge hash must also equal `accepted.json`'s]. The newest history line's `artifact` equals the release's `python.wasm` SHA-256, and it is clean and not a `--partial` acceptance. Since every landing that changes the set is accepted, and the build reproduces the set from the pins on any host (specs 012, 040, 059), a release of main's commit meets this (INFERRED). This is the confirmation "Before a release" asks someone to make by hand.
- **Three systems.** The gather requires the probe check (`history.PROBE`) to have passed on the release's artifact in a darwin, a linux and a win32 record. That is the `three systems` claim, proven inside the release run.
- **CI writes no history.** The gather writes nothing under `context/progress/` and accepts nothing. Its merged record and scoreboard are a workflow artifact (`release-record`) and a summary in the log. Only the lane accepts (constitution §5.7; AGENTS.md rule 6a). The need `three systems` stays what it is locally.

## 7. Risks

- **Shard flakiness.** A shard is a new grouping of checks in one process. Spec 052 found three checks that depended on an earlier check in the same process and fixed them; its census ran every goal check alone (READ, its memo, sections 7 and 8). Section 2 shows the groups alone give the lane's answer. INFERRED: the files are kept whole and run serially, so the remaining risk is small. A flaky failure stops the release; the recovery is GitHub's re-run of the failed jobs (spec 057, Decision 8), and the release notes name the shard and the check. No automatic retry: a check that fails once is a defect to fix.
- **A shard that silently selects nothing.** Red three times: the plan rule, the plugin's refusal, and the gather's comparison with its own collection. A missing shard is red at the gather's id guard and again in its plan check.
- **The gather trusting a record.** Covered by the ids, the hashes and the meta rules (section 6). The remaining trust is in the shard's own code, as it is in today's build job: a compromised host input on one system can lie about that system's shards. Three systems and the lane's acceptance on the same bytes are the cross-checks.
- **A first run on Linux and Windows.** The judge's tooling tests have never run there (section 1). INFERRED: the first dry run may find checks that cannot hold on one system. [As revised: the owner answered question 98 yes, so the builder dry-runs the release on the spec's branch before landing and fixes what it finds there. A goal check that fails on one system is fixed or given a real need; only a unit test may take the `skipif(not POSIX, reason=…)` pattern, since the plugin fails a goal check's skip that names no need.]
- **Collection differs by system.** The gather assumes the same node ids everywhere. A parametrization that depends on the host would show up as a red "selected other checks". That is a property worth holding, not a false alarm.
- **Queueing.** On Free, a slot or two may wait about a minute (section 5).
- **New inputs on CI runners.** Shards fetch seven kit wheels and two tarballs, all hash-pinned, on runners with `contents: read`. Nothing a shard makes reaches the assets: it produces a record, which only the gather reads. The next release's threat-model review (constitution §5.6) should see these jobs.

## 8. The rule for every package from now on

The artifact holds 22 packages and CPython (READ, the frozen set's MANIFEST). Two run their own suites. The others fall in four kinds:

- **compiled libraries reached through a package or a stdlib module:** zlib, bzip2, xz, sqlite, freetype, harfbuzz, SheenBidi, libraqm [as revised: also qhull, a source component compiled into matplotlib, and the linked runtimes wasi-libc and libc++, reached through every run]. Their own suites are C programs against a native build; here they are exercised through CPython's `zlib`, `bz2`, `lzma`, `sqlite3` and through matplotlib and pillow.
- **build-time only:** pybind11 and cppy (headers for compiling kiwisolver and matplotlib).
- **suites not yet run:** matplotlib, pillow, kiwisolver, fonttools, pyparsing, cycler, packaging, python-dateutil, six, tzdata. The pure-Python ones are pinned as wheels, which carry no tests: a later spec pins each one's sdist as data for its tests.
- **CPython itself.** Its own test suite (`python -m test`) supports WASI and is large; whether it gates a release was a scope decision [the owner answered question 99: "Gate 0.1.0 regardless"; a specification of its own, 065, carries it].

A judge check over the MANIFEST's packages, reading one file (`tests/upstream/packages.toml`) that names each package's kind, makes the rule mechanical: a new package fails the judge until its spec adds its suite or says why not. AGENTS.md says it in one line. A spec template line would not be checked.

## One line

Split the release's judge into eleven named shards in seventeen jobs (three of our own on each system, five package shards on Linux, one package group each on macOS and Windows, and the build host's own checks), merge their hashed records in one gather that ties them to the release's bytes, the lane's acceptance and three systems, and the release takes about 20 minutes instead of 33 while running every package suite it never ran before.
