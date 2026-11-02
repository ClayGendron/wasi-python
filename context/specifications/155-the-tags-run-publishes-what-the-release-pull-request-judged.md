# 155: The tag's run publishes what the release pull request judged

- **Status:** built 2026-10-30 on `spec/155-the-tags-run-publishes-what-the-release-pull-request-judged`, stacked on 159 (`dev` at `a1acec5c`), not landed. Drafted 2026-10-30 and reviewed before it was built (constitution §5.6: the release workflow), `../reviews/155-the-tags-run-publishes-what-the-release-pull-request-judged-spec-2026-10-30.md`, which signed it fit to build. Reserved on 2026-10-27 by specification 138's landing notes; the owner asked for it on 2026-10-30 ("can you implement all the recommendations") and agreed the same day to the amendment of constitution §5.5 it needs.
- **Date:** 2026-10-30
- **Owner:** Clay Gendron
- **Kind:** **build-class** (the release workflow, the plan script, the gather's prove-the-set mode), not structural, parallel-safe with 160 and 161; stacks on 159.
- **Depends on:** 159 (the build on arm64 Linux, the macOS rebuild, same-bytes off the gather's needs); the owner's decision of 2026-10-30 on §5.5.
- **Research it stands on:** `../research/2026-10-30-where-the-time-goes-since-0-1-1.md` (§2.3, §4 row 8); `../research/2026-10-25-a-development-process-that-runs-what-it-needs.md` §4.5 (the tag "promoted from the release pull request's run, as Wasmtime does"); specification 138's Decision 6.

## The problem

The 0.1.2 tag's run took 110 minutes and the 0.1.1 tag's 137 (EXECUTED, the memo §2.1). Each repeated, on the same tree plus one commit that holds the acceptance record, every job the release pull request's run had finished green two hours earlier: the compiles, both tiers on three systems, the gather. Constitution §5.5 asked for it ("the tag's own run judges both again"). The owner has decided the repetition goes.

## Decisions

### 1. What the tag's run does

On a pushed tag `v<version>` the plan sets `rebuild` true, `judge` false, `build` false, `tier` empty and every judge list `[]`, and a new output `publish` true (false on every other event). The `inputs` and `build` jobs run when `judge` or `rebuild` is true, so a tag still compiles; `select()` fills `verify` with the three runners when `rebuild` is true, not only when `judge` is. The run is: `plan`; `quick`; `inputs`; `build` (a compile from the pins on arm64 Linux, the version and tag check, the zero-patch check, the wheel, the assets, as today; no build shard, since no gather reads its record); `rebuild-linux-x86-64` and `rebuild-macos-arm64`; `same-bytes`; `verify` on three systems; a new job `judged` (Decision 2); `attest`; `publish`; `pypi`. No judge job and no gather run. `attest` and `publish` need `judged` beside `build`, `verify` and `same-bytes`, and `ci-status` needs `judged` as it needs every job; on a run whose plan says `publish`, `ci-status` is red when `publish` was skipped, so a tag that published nothing is never green. The tag's three jobs keep every guard they have (the artifact id handed on, the SHA-256 of `SHA256SUMS`, the files checked against it).

### 2. The bytes are the ones `main` accepted, and the tree is the one judged

`judged` runs on `ubuntu-24.04` after `build` and `same-bytes`, with the tagged commit checked out at `fetch-depth: 2`. It downloads the build's assets through the `verify-artifact` action, unpacks the set, and hashes the set's own `SHA256SUMS` and `python.wasm` itself. Then one command, `uv run python tests/harness/gather.py --prove-set <set-sums-sha256> <wasm-sha256>`, reads `context/progress/accepted.json` and the newest history line the way goal G7 does today and requires all of: the newest line's `source` is `ci` and its `tier` is `release`, the pair only a release pull request's acceptance writes (the post-merge acceptance writes the normal tier; the weekly run and a dispatch never accept); the line's `commit` is `HEAD^`, the commit the release pull request judged, whose child is the acceptance commit the tag sits on; the line is not partial and its tree was clean, as G7 asks today; the line's `set_sums` equals the first argument and its `artifact` the second; and `git diff --name-only HEAD^ HEAD` names exactly `context/progress/accepted.json` and one history volume, the rule `accept-release.yml` holds when it pushes, so the tagged tree is the judged tree plus the record and nothing else (the wheel carries `src/`, which no set hash covers). It exits non-zero with one line naming the first mismatch. Unit rows drive it against a scratch repository and accepted state in six cases: holds; a different set; the newest line not a release's (tier normal); the line's commit not the parent; a second file in the acceptance commit; a partial or dirty line. The event, parent and diff checks need no compile: the `build` job runs them as its first step on a tag (`gather.py --prove-set --tree-only`, the same command without the two hashes), so a wrong tag fails in a minute, and `judged` runs the whole check again against the bytes.

### 3. The constitution and the pages

§5.5's release rule changes from "the tag's own run judges both again" to: the tag's run rebuilds the set from the pins on three hosts, requires the same bytes as the release pull request's accepted record and the tagged tree to be the judged tree plus that record, installs the wheel fresh on three systems, attests and publishes; it judges nothing again, since the tree it builds is the one the release pull request judged plus the commit that recorded that judgement. The release pull request stays the dry run, whole, on the exact commit `main` receives. `docs/contributing/release-process.md` says the same in its words and its "Dry runs" section says the tag's run is not one; `context/progress/README.md`'s four sentences that say the tag judges, and the release workflow's header comment, follow.

### 4. What does not change

A tag never reuses a cached set (`inputs`'s trust rule). The weekly run, the release pull request and a dispatch keep both tiers. The attestation signs the build's assets as today. `release/version.py check --tag` and the ancestor check stay in the build job.

## Intent

A tag publishes within about 40 minutes of its push: the compile and the rebuilds in parallel, the same-bytes vote, the proof that these are the accepted bytes, the signature, the release.

## Design

Files: `.github/workflows/release.yml` (the plan's tag branch, the `inputs` and `build` gates, the `judged` job, the needs of `attest`, `publish` and `ci-status`, the header comment), `release/ci_plan.py` (`decide()`'s tag branch: `rebuild` true, `judge` false, `build` false, `publish` true; `select()`'s verify rule), `tests/harness/gather.py` (`--prove-set`), `tests/unit/test_gather.py` and `tests/unit/test_ci_plan.py` (the rows), `tests/checks/test_rules.py` (the needs, and `ci-status` red on a skipped publish), `context/constitution.md` §5.5 and its Status line, `docs/contributing/release-process.md`, `context/progress/README.md`, `context/changes/155-the-tags-run-publishes-what-the-release-pull-request-judged.md`.

## Scope

In: the four decisions. Out: promoting the release pull request's artifacts without a rebuild (Wasmtime's full pattern), which would skip the three-host vote at the tag; the owner keeps the vote.

## Acceptance criteria

1. On a tag the plan's `judge` and `build` outputs are false, `rebuild` and `publish` true, `tier` empty, every judge list `[]` and `verify` the three runners; on every other event `publish` is false. Unit rows.
2. `judged` exists, needs `build` and `same-bytes`, runs only on a tag, and is in the needs of `attest`, `publish` and `ci-status`; `inputs` and `build` run when `judge` or `rebuild` is true; `ci-status` is red when the plan said `publish` and `publish` was skipped. Rules rows.
3. `gather.py --prove-set` holds in the six cases of Decision 2. Unit rows.
4. The tag's run has no judge leg and no gather (READ from the next release's tag run, named in the landing notes, with its wall time EXECUTED).
5. Constitution §5.5, the release page, the progress README and the workflow's header say what Decision 3 says. READ.
6. The fast tier, `tests/lint` and the pull request's `ci-status` are green; the news file is present.

## Landing notes

Built 2026-10-30, before its pull request and review. What was built, beyond the Decisions' words:

- **The plan.** `Decision.publish` is true on a pushed tag alone; `judge` is false whenever `publish` is, `tier` is the empty string and `full` false on a tag, and `select()` gives `verify` the three runners on every run that rebuilds. 159's criterion-4 unit row (`test_the_build_shard_runs_exactly_where_the_rebuilds_compile`) drops its tag case, as Low 10 of the pre-build review asked: the tag's `build` output is now false, held by `test_a_tag_publishes_what_the_release_pull_request_judged` in `tests/unit/test_ci_plan.py`. 159's own text already said "until specification 155 changes that row", so it is left as written. Two other unit rows and the rules row `test_the_judge_matrices_are_the_shard_plan_on_every_release` lose their tag case (the whole selection and coverage rows read the weekly run instead); the rules row's `[a pushed tag]` id is retired in the news file's claim.
- **`--prove-set`** (`tests/harness/gather.py`, `prove_set`) also requires `accepted.json`'s `commit` to be the parent, and, where the history line carries 161's `event`, that it is `pull_request`; a line without one is read by `source` and `tier`, as `accept_from._is_release_line` reads it. Checked against the real `v0.1.2` tag in a scratch clone: the tree holds, and the bytes hold with line 115's `set_sums` and `artifact`.
- **The workflow.** The tree half runs as the build job's first step on a tag (`if:` the pushed-tag condition, the runner's own variables); the build shard's step, its SHA-256 and its record upload in `rebuild-linux-x86-64` carry `if: needs.plan.outputs.build == 'true'`; `judged` checks out with `fetch-depth: 2`, unpacks the set's tarball (one folder, or red), hashes its `SHA256SUMS` and `python.wasm` and runs the whole check. `ci-status` reads the plan's `publish` and is red when it is true and `publish` did not succeed. The scan's new `tag_run_errors` holds all of this, with fourteen mutants in `tests/unit/test_scan.py`; `jobs_that_run` models the tag's run as exactly plan, quick, inputs, build, the two rebuilds, same-bytes, verify, judged, attest, publish and ci-status.
- **Criterion 4 is the next tag's to prove.** A workflow change cannot run locally; the pull request's run proves the plan, the rules and the shape of every other event, and the next release's tag run proves that no judge leg and no gather runs, with its wall time.
