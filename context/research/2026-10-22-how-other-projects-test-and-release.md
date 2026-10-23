# How other projects test, gate merges and release

- **Status:** research, 2026-10-22 (written the night of 2026-10-21). A study of precedent and a measurement of this repository's own run history. Nothing in `src/`, `tests/`, `scripts/`, CI, `AGENTS.md` or the constitution changed. No judge, pytest or build was run.
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5), one session. Box: one session.
- **Stands on:** the owner's remark that development is "significantly limited by code running to test our code"; `2026-10-16-how-autonomous-ports-were-run.md` (which studied how agent ports judged their work, not how projects budget CI); AGENTS.md rules 2 to 8; constitution §5.5 to §5.7; `context/progress/README.md`.
- **Feeds:** a separate advisor's recommendation. This memo lists options; it recommends none.
- **Evidence labels:** EXECUTED (measured here, read-only: `gh run list`, `gh run view`, the history files, `git log`), READ (a file in a clone or a URL, cited), INFERRED (reasoning).

## Terms

- A **branch run** is a dispatch of `.github/workflows/release.yml` on a `spec/NNN` branch.
- A **merge queue** tests each approved change merged onto the latest main, and merges only what passed. **bors** is Rust's merge-queue bot. A **rollup** is several small PRs tested as one merge commit. A **try build** is an on-demand run of chosen CI jobs on a PR.
- **Test selection** means running only the tests a change could affect. **Result caching** means reusing a test's earlier result when none of its inputs changed.

## 1. Our pattern in numbers

### The stages a specification passes through

READ (AGENTS.md rules 2, 3a, 6a, 8; constitution §5.6, §5.7; `context/progress/README.md`): draft (checks first) → pre-build review and its confirmation (for build-class, runner or structural specs) → build, looping on the local fast tier → one or more branch runs, each a full three-system judge → self-check and landing notes → build review (reads the run, or dispatches its own) and its confirmation → rebase onto the wave's tip, fast tier after each entry → the lane's main-tree rebuild and local `-n 3` normal-tier judge and acceptance → a fresh integration review → fast-forward → the wave's dry run on CI (three systems, serial). Before a tag: a local release acceptance with the release tier, a dry run on main, then the tag's own run.

### Measured cost

All EXECUTED unless marked.

- **The release workflow, 100 runs** (2026-10-19 05:15 to 2026-10-21 21:20 UTC, 64 hours): 31 green, 62 red, 7 cancelled. Every one was a `workflow_dispatch` except the `v0.1.0a7` tag; the workflow has no `pull_request` trigger.
- **Width and length.** A run was 29 jobs and a median of 24 minutes wall before 2026-10-20 05:00; since 2026-10-20 09:00 it is 43 to 59 jobs and a median of 55 minutes (60 for the green ones). Median runner time 186 minutes a run; 283 runner-hours over the 100.
- **Branch runs per specification.** 32 specifications had 78 branch runs: mean 2.4 (one run: 9 specs; two: 11; three: 8; four or five: 2; seven: 2, specs 101 and 102). They took 54 wall-hours. 16 wave runs took 12.2.
- **Why runs were red.** Of the 62 red runs, 29 were red only on `GREW` lines (fuel or bytes past 1e-4, the judge's design until the lane accepts the growth), 7 only at the gather's G7 (a branch set is never the accepted one), 2 on both. So **38 of 62 red runs (61%) were red by design**, and a reader had to open logs to know. 24 showed a real failure: 14 on Windows alone, 4 on Linux alone, 4 in the arm64 build shard, 2 on several systems.
- **What the Windows reds were.** About five distinct defects, each seen on several branches because it sat on the shared base: the read-only removal rows (six branches, wave/01 and wave/02 included), `test_a_forked_child_is_refused` (five branches), the abandoned-turn session (two), the stylesheet grants (one). CHANGELOG READ: 0.1.0a4's tag run failed on Windows only.
- **Acceptances.** 93 history lines. Per day: 5, 29, 30, 15, 10, 4 (2026-10-16 to 10-21). The later days carry waves: 11 waves and the structural chain landed about 39 specifications on 2026-10-20 and 10-21. 32 of the 93 lines carry a growth reason.
- **Local judge.** The lane's `-n 3` normal tier took 19 min 51 s at wave 11 (READ, `context/reviews/wave-11-integration-2026-10-21.md`); the fast tier about 3 min 48 s (AGENTS.md).
- **The release tier** is about 117 T of fuel measured so far (READ, `context/handoff.md`). Spec 102 equates 4.4 to 9 T with 12 to 25 minutes at `-n 3`; INFERRED, the whole release tier is about 5 hours locally at that rate.
- **Reviews.** 215 review files for 106 specifications (77 with two, 11 with three, three with four or more), 11 wave integration reviews, seven release security reviews. `context/reviews/` holds about 925,000 words and `context/specifications/` about 833,000 (`wc -w`).
- **Rebase friction.** Since 2026-10-19, 38 commit subjects name conflicts, most in README (14) and CHANGELOG (11). Spec 045 named 22, 13, then 6 hunks over three rebases.

### Where a specification's hours go

Method (INFERRED from EXECUTED data): commit times from `git log` on each spec's files, joined with run start and end times from `gh run view`, for two small specs of wave 11 and one package spec, 100. Time between commits is not all agent work: an agent may think or wait unseen. It is an estimate.

| spec | draft to landed | runs on the critical path | code (commit gaps of building) | other |
|---|---|---|---|---|
| 113 | 8.0 h | 4.1 h: run 92 min (two attempts) + run 61 + lane judge 20 + dry run 72 | ~0.6 h | spec, two reviews, notes, wave wait |
| 114 | 8.0 h | 2.7 h: run 68 + lane 20 + dry run 72, plus 0.7 h waiting for the wave | ~1.4 h | same |
| 100 | 20 h | three runs, three restacks each rebuilt from empty | two build phases ~1 h | restacks onto wave 08, the chain, wave 09 |

For a small specification, about **35 to 50% of elapsed time is waiting on runs** and **10 to 20% is writing code**. For a package specification the larger cost is re-basing and rebuilding onto moving bases, each followed by more runs. INFERRED.

**How many times the same suite runs per change.** The full normal tier on three systems runs about 2.4 times per spec on its branch, once more in the wave's dry run (shared by about 3.5 entries), once locally at the lane, and again in the pre-tag dry run and the tag run (shared by the release). The local fast tier runs after every rebase. INFERRED: about **three full three-system judges per specification**, plus a local one per wave.

## 2. What each studied project does

Clones are shallow, read-only, at the commits in `context/prior_art/README.md`.

### Pyodide (CPython on wasm, browser and Node)

- **Selection.** READ `pyodide/.github/workflows/main.yml`: PRs and pushes build only `tag:core`, the test packages and numpy. SciPy's suite runs on push, or on a PR with a `[scipy]` commit tag or `scipy` label, with `-m 'not slow'` (`test-scipy-trigger`, `test-scipy`). `concurrency: cancel-in-progress: true`.
- **Packages** (READ `pyodide-recipes/.github/workflows/build.yml`, `tools/calc_diff.py`): a PR builds the recipes changed against its base plus `tag:core`; the whole set of 335 builds on push to main, a `full build` label, or a cron twice a week.
- **What tests mean.** Each recipe has a small test file (`packages/numpy/test_numpy.py`, 14 tests; `packages/pandas/test_pandas.py`, 2). The packages' own upstream suites do not run in CI, scipy's fast part apart.
- **Caching.** ccache and conda environments by key (`main.yml` line 145; `build.yml` line 170).
- **Release.** Push a tag, wait for CI (READ `docs/development/maintainers.md`).
- **Performance.** `make benchmark` exists (`Makefile` line 293); no workflow runs it.

### emscripten-forge recipes

READ `.github/workflows/build_recipes.yaml`, `emci/find_recipes_with_changes.py`, `emci/rattler_build.py`: the workflow runs only when `recipes/**` changes, builds only recipes whose files changed, and passes `--skip-existing` so a package already on the channel is not rebuilt. The channel is the cache.

### CPython

- **Selection.** READ `Tools/build/compute-changes.py`, `.github/workflows/reusable-context.yml`: the changed files decide which jobs run. Docs-only changes skip tests; a change under `Tools/wasm/` runs the WASI job; platform-specific files run that platform only; Windows tests run unless a change is Unix-build-only; fuzzing runs only for C changes.
- **Tiers.** READ `Lib/test/libregrtest/cmdline.py` lines 495 to 510, `Makefile.pre.in` line 2291: PR CI runs `make ci`, `--fast-ci` (`-u all,-cpu`, 10-minute timeout). Buildbots run `--slow-ci` (`-u all`, 20 minutes) after merge. READ devguide.python.org/testing/buildbots: buildbots run on each push to a branch, on a PR only with a `test-with-buildbots` label or a `!buildbot` comment; core developers must "fix or revert" what breaks a stable buildbot.
- **WASI.** One job, about 60-minute timeout, caches the WASI SDK (`.github/workflows/reusable-wasi.yml`).

### numpy and scipy

- **Selection.** READ `numpy/.github/workflows/linux.yml`: a cheap `smoke_test` job gates about ten others (`needs: [smoke_test]`); `paths-ignore` skips docs-only changes; superseded runs are cancelled.
- **Slow tests.** `spin test` defaults to `-m "not slow"` (`numpy/.spin/cmds.py` line 137); a few jobs pass `-m full` (`linux.yml` line 194, `macos.yml` line 102). scipy does the same (`scipy/.github/workflows/windows.yml` line 97, `--mode full` on one job).
- **A budget on the fast tier.** READ `scipy/pixi.toml` lines 400 to 403 and `scipy/.github/workflows/linux.yml` line 711: one aarch64 job runs the fast suite with `--fail-slow=1.0`, so a test not marked slow that takes over a second fails CI.
- **Performance.** numpy's `benchmark` job runs `spin bench --quick` on PRs (`linux.yml` lines 197 to 228): it proves the benchmarks still run and compares nothing.

### Wasmtime

- **Selection.** READ `.github/workflows/main.yml` lines 167 to 270, `ci/build-test-matrix.js` lines 399 to 437, `docs/contributing-ci.md`: a PR to main runs "a sample of the full CI test suite", by default on x86_64 Linux. Changed paths add configurations (a Cranelift ISA, `crates/c-api`, fuzz, GC). A commit containing `prtest:full` (or `prtest:<filter>`) asks for more.
- **Merge queue.** The full suite on all platforms runs once, in GitHub's merge queue (`merge_group`). Main itself never runs CI: "CI doesn't run on pushes to `main`".
- **Out of band.** Fuzzing runs on OSS-Fuzz; CI only samples the corpus. A daily cron runs full CI on main, weekly on release branches (`.github/workflows/ci-cron-trigger.yml`).
- **Release.** Monthly by automation: a release branch on the 5th, published on the 20th (`docs/contributing-release-process.md`).

### Rust

READ `src/ci/github-actions/jobs.yml`, `src/doc/rustc-dev-guide/src/tests/ci.md`, `perf.md`, `crater.md`:

- **Three kinds of run.** `pr` (11 jobs, all Linux, about 40 minutes, "relatively short and lightweight"), `auto` (82 jobs, all platforms, "several hours"), and `try` (chosen jobs on demand, `@bors try jobs=<pattern>`, at most 20).
- **One full test per merge.** bors tests one merge commit at a time against main and fast-forwards on green. The guide states the price: about 10 merges a day.
- **Rollups.** A team member batches trivial PRs into one merge commit "using their judgment to decide if a PR is risky or not". PRs marked `rollup=never` go alone.
- **Caching.** Docker images keyed by a hash of the Dockerfiles and scripts.
- **Performance.** Perf runs on request (`@rust-timer queue`), and after merge. READ github.com/rust-lang/rustc-perf `triage/README.md`: regressions in instruction counts are triaged weekly after merge; the author is asked to respond; a big one may be reverted. Not a merge gate.
- **Ecosystem.** Crater runs every crate's tests, on request, for risky changes.

### Result caching, merge queues and perf gates elsewhere

- **Bazel** (READ bazel.build/docs/user-manual): with `--cache_test_results=auto`, a test reruns only if "Bazel detects changes in the test or its dependencies", it is `external`, several runs were asked for, or it failed. bazel.build/remote/caching warns that tools outside the workspace are not tracked, so two hosts can share a wrong hit.
- **pytest-testmon** (READ testmon.org): selects tests from per-test coverage; it does not track data files or external services.
- **GitHub merge queue** (READ docs.github.com, "Managing a merge queue"): groups queued PRs with the base, up to a maximum group size; a failing PR is removed and the rest re-tested.
- **CodSpeed** (READ codspeed.io/docs): measures by simulation, so results are stable across hardware; a regression blocks only if the project makes the check required.

## 3. Comparison

| dimension | us | Pyodide | CPython | numpy / scipy | Wasmtime | Rust |
|---|---|---|---|---|---|---|
| per-change selection | none: every branch run runs every shard | changed recipes + core; scipy by label | by changed paths and platform | paths-ignore; cheap job first | sample, plus by path and `prtest:` | fixed light `pr` set |
| full suite runs | ~2.4 per spec + wave + lane | on push to main, label, cron | buildbots after merge | every PR (fast mode) | once, in merge queue | once per merge (`auto`) |
| platforms per change | macOS, Linux, Windows always | Linux, macOS core | as paths say | all, fast mode | Linux by default | Linux on PR |
| slow tier | release tier: tag, pre-tag dry run, lane | `not slow` only | `--slow-ci` on buildbots | `-m full` on a few jobs; fail-slow budget | full in queue; fuzz out of band | `auto`; crater on request |
| result caching | set reuse by key on branches (spec 101) | ccache, conda, channel | SDK, ccache | ccache | none found | Docker images by hash |
| batching | waves of up to 5, manual rebases | none | none | none | merge queue | bors queue + rollups |
| perf policy | gate: any fuel or byte growth >1e-4 red | none in CI | none in CI | benchmarks run, not compared | none in CI found | weekly triage, may revert |
| review layers | pre-build, confirm, build, confirm, integration, release security and structural | one approval | one core dev | one or two | one approval | one reviewer |
| release gate | release tier + dry run + tag run + two reviews | tag CI | release manager, stable buildbots | wheels CI | monthly automation | nightly promotion |

## 4. Where we are heavier, and why

1. **No selection.** Every project studied runs a lighter set on a change and the full set at one later point. We run the full three-system set, upstream suites included, on every branch run, for a context-only edit as much as a recipe change. INFERRED: this is the largest single cost.
2. **The full suite runs several times per change.** Rust and Wasmtime run it once per merge. We run it on the branch (2.4 times), at the lane locally, at the wave's dry run, and before and at the tag.
3. **CI's colour carries little.** 61% of our red runs were red by design. Elsewhere red means broken, and a merge queue acts on the colour alone. Here every run needs an agent to read it.
4. **Performance is a hard gate at 1e-4.** No project studied gates merges on a performance number by default; Rust triages instruction counts weekly. Our fuel is exact enough to gate on (`2026-10-16-fuel-as-the-operation-count.md`), so the gate is cheap per check; what costs is the red runs and the claim-list bookkeeping on 32 of 93 acceptances.
5. **Review layers.** Up to five reviews per landed specification, against one approval elsewhere, and nearly two million words in reviews and specifications in six days.
6. **Manual batching.** Waves resemble rollups, but each builder rebases by hand and conflicts recur in README and CHANGELOG. CPython and numpy keep one news file per change (`cpython/Misc/NEWS.d/next/`, `numpy/doc/release/upcoming_changes/`), so those files never conflict.

**What buys real safety here.**

- **Windows on CI.** 14 of 24 real red runs were Windows alone, and 0.1.0a4's tag failed only on Windows. A wasm runtime fails in platform ways (read-only files, process spawning, path rules). Running Windows only at release time would have moved those finds to the tag.
- **A full run at one integration point.** Three wave dry runs were red on a real failure (wave/01 and wave/02 on Windows, wave/10 in the build shard), so the integration point catches what branches and the local acceptance miss.
- **An exact ratchet.** The code is written by agents, who solve what the verifier asks (`2026-10-16-how-autonomous-ports-were-run.md`, lesson 1). A ratchet that counts by name and refuses lost passes is the precedent that converged.
- **Fresh review.** Bun's and ts-rust's rule ("the implementer doesn't review") came from agents.
- **Costs that are mostly repetition.** The second and later branch runs of a spec, a local full judge when a CI record of the same commit exists, upstream suites rerun on an unchanged set, and red-by-design runs that must be read. INFERRED.

## 5. Candidate changes

Each with what, who does it, saving (INFERRED), risk, and what in our rules changes.

**A. Path-based shard selection on branch runs.** A first job maps changed paths to shards: a change outside `scripts/`, `recipes/`, `downloads/` and the upstream TOMLs keeps the set and its upstream suites' inputs, so those shards are skipped; a `context/`-only change skips the guest. Windows `own-*` shards stay for any `src/` or `tests/` change. *Who:* CPython `compute-changes.py`, Wasmtime `build-test-matrix.js`, pyodide-recipes `calc_diff.py`. *Saving:* the upstream shards are most of a run's 43 to 59 jobs; perhaps 40 to 60% of runner time and 15 to 30 minutes of wall time for most specs. *Risk:* a missed dependency (a harness file that changes upstream behaviour). *Changes:* AGENTS.md rule 2 ("built" means a full run), §5.6's "re-runs the counted tests".

**B. A light branch run, the full run once at the wave.** Builders' runs use a fixed light set (Linux plus Windows `own-*`, no upstream); the wave's dry run, already three-system and serial, is the full test of each entry. *Who:* Rust `pr` vs `auto`; Wasmtime PR vs merge queue. *Saving:* about 1.4 of 2.4 full runs per spec, ~35 runner-hours a day at the recent pace. *Risk:* failures surface at the wave, ejecting an entry later; Rust's ~10 merges a day is the price of one full run per merge. *Changes:* rules 2, 3a, 8 (the reviewer's run), §5.6, §5.7.

**C. One acceptance record from CI.** The lane accepts from the wave's dry-run record (spec 092 already reads one) instead of a local `-n 3` full judge. *Who:* every project studied judges merges on CI only. *Saving:* ~20 minutes of lane time and the machine's judge slot per wave. *Risk:* `accepted.json` holds darwin-arm64 fuel measured locally; CI's macOS runner may differ; an `--accept` from a downloaded record is new judge code. *Changes:* §5.7, rule 6a, progress README steps 3 and 3a.

**D. Growth that is claimed is green.** The gather reads the branch's claim block and passes when every `GREW` row is claimed, so a run's colour means something. Or make growth advisory on branch runs and gate only at acceptance. *Who:* Rust (instruction counts, triaged after merge); CodSpeed (blocking only when made required). *Saving:* reading time for ~29 in 100 runs; automation could act on colour. *Risk:* growth with a wrong reason passes; the claim must be written before the run. *Changes:* rule 5, progress README's ratchet, the gather.

**E. Result reuse by input hash.** A guest check whose inputs (the set's `SHA256SUMS`, the judging files, the runner's sources, `uv.lock`, the host image) are unchanged since an accepted run reuses that result. Fuel is deterministic, so a reuse is honest where inputs are complete. *Who:* Bazel `--cache_test_results=auto`; our own spec 101 for the set. *Saving:* for a `context/`-only or docs spec, nearly the whole run. *Risk:* an undeclared input (Bazel's own warning); Windows image updates; hides flakiness. *Changes:* the ratchet's `unrun`, §5.6, rule 3a.

**F. Rollups for context-only and judge-only work.** Specs that touch only `context/`, README, CHANGELOG or judge prose go in a batch with no branch run of their own. *Who:* Rust rollups; rule 6b already lets such commits follow a dry run. *Saving:* one or more runs per such spec (112 and 110 had one or two). *Risk:* the "who decides it is trivial" judgment; a prose change to a judging file still moves the judge hash. *Changes:* rule 2, §5.4.

**G. A cheap gate first, and cancel superseded runs.** A short job (ruff, units, rules) must pass before the native build and 40 shards start; `cancel-in-progress: true` for a branch's newer push. *Who:* numpy `smoke_test`; Pyodide, numpy, Wasmtime concurrency. *Saving:* a run that dies on a rules check (spec 093's header check) costs minutes, not ~250 runner-minutes. *Risk:* small; cancelling a run someone meant to read. *Changes:* the workflow only.

**H. News fragments instead of one CHANGELOG and shared README rows.** One file per spec under a directory, assembled at release. *Who:* CPython `Misc/NEWS.d/next/`, numpy `doc/release/upcoming_changes/`. *Saving:* about half the named conflicts since 2026-10-19 and the re-runs they cause. *Risk:* README size rows still conflict. *Changes:* rule 2's CHANGELOG sentence.

**I. Fewer review rounds for low-risk kinds.** One review after build for parallel-safe specs, merged with the integration review; pre-build review kept for §5.6's classes. The owner's compressed path (decisions, 2026-10-21) already overlaps review with the run. *Who:* every project here uses one approval. *Saving:* agent time and prose; not CI. *Risk:* the reviews have caught real defects (113's M1); agents' code needs a fresh reader. *Changes:* §5.6, rule 8.

**J. A scheduled release-tier run.** The release tier runs nightly on main instead of only before a tag, so a slow-test regression is found within a day. *Who:* Wasmtime daily cron; CPython buildbots; pyodide-recipes twice weekly. *Saving:* none per spec; it removes a five-hour surprise at the tag. *Risk:* runner cost; it conflicts with the owner's standing rule that slow tests run only to publish (decisions, 2026-10-21), so it needs the owner. *Changes:* §5.5's release rule.

**K. A fuel budget on the normal tier.** A normal-tier check past a fuel cap fails, as scipy's `--fail-slow=1.0` does, so the fast tier stays fast without re-asking where each test goes. *Who:* scipy. *Saving:* keeps the normal tier from growing; no immediate saving. *Risk:* small. *Changes:* the tier rules in each family's TOML.

## What this study does not show

- Run times mix load: three builders and the lane shared a five-macOS-job account limit, so wall time includes queueing.
- The hour split in part 1 comes from commit times; an agent's unseen work between commits is counted as gaps, not measured.
- "Real" failures were classified by grepping `FAIL`, `LOST` and the ratchet's counts from the failed jobs' logs; a red with no such line was counted by its job.
- Wasmtime's and CPython's out-of-band benchmarking (Sightglass, speed.python.org) were not read.

## Sources

Clones under `context/prior_art/` (commits in its README): `pyodide` (6754c1f), `pyodide-recipes` (01bd0af), `cpython` (7c04882), `numpy` (ac61120), `wasmtime` (2d9c19b), and, cloned for this memo, `rust` (1a2c479, sparse: `.github`, `src/ci`, two dev-guide folders), `scipy` (3f3cfc3, sparse), `emscripten-forge-recipes` (2c44545, sparse). URLs, read 2026-10-21: <https://github.com/rust-lang/rustc-perf/blob/master/triage/README.md>, <https://devguide.python.org/testing/buildbots/>, <https://bazel.build/docs/user-manual>, <https://bazel.build/remote/caching>, <https://testmon.org/>, <https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue>, <https://codspeed.io/docs/instruments/cpu>, <https://codspeed.io/docs/features/performance-checks>. Our data: `gh run list --workflow release.yml --limit 100`, `gh run view <id> --json jobs` and `--log-failed` for every failed job (scratch only), `context/progress/history*.jsonl`, `git log`.

## One line

Other projects run a light set on each change and the full set once, at merge; we run the full three-system set about three times per specification and gate on growth that is red by design, and Windows CI and one full integration run are the parts that have caught real defects.
