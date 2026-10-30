# 155: The tag's run publishes what the release pull request judged

- **Status:** drafted 2026-10-30, to be reviewed before it is built (constitution §5.6: the release workflow). Reserved on 2026-10-27 by specification 138's landing notes; the owner asked for it on 2026-10-30 ("can you implement all the recommendations") and agreed the same day to the amendment of constitution §5.5 it needs.
- **Date:** 2026-10-30
- **Owner:** Clay Gendron
- **Kind:** **build-class** (the release workflow, the plan script, the gather's prove-the-set mode), not structural, parallel-safe with 160 and 161; stacks on 159.
- **Depends on:** 159 (the build on arm64 Linux, the macOS rebuild, same-bytes off the gather's needs); the owner's decision of 2026-10-30 on §5.5.
- **Research it stands on:** `../research/2026-10-30-where-the-time-goes-since-0-1-1.md` (§2.3, §4 row 8); `../research/2026-10-25-a-development-process-that-runs-what-it-needs.md` §4.5 (the tag "promoted from the release pull request's run, as Wasmtime does"); specification 138's Decision 6.

## The problem

The 0.1.2 tag's run took 110 minutes and the 0.1.1 tag's 137 (EXECUTED, the memo §2.1). Each repeated, on the same tree plus one commit that holds the acceptance record, every job the release pull request's run had finished green two hours earlier: the compiles, both tiers on three systems, the gather. Constitution §5.5 asked for it ("the tag's own run judges both again"). The owner has decided the repetition goes.

## Decisions

### 1. What the tag's run does

On a pushed tag `v<version>` the plan sets `rebuild` true, `judge` false, `tier` none and `selected` empty. The run is: `plan`; `quick`; `build` (a compile from the pins on arm64 Linux, the version and tag check, the zero-patch check, the wheel, the assets, as today); `rebuild-linux-x86-64` and `rebuild-macos-arm64`; `same-bytes`; `verify` on three systems; a new job `judged` (Decision 2); `attest`; `publish`; `pypi`. No judge job and no gather run. `attest` and `publish` need `judged` beside `build`, `verify` and `same-bytes`; the tag's three jobs keep every guard they have (the artifact id handed on, the SHA-256 of `SHA256SUMS`, the files checked against it).

### 2. The bytes are the ones `main` accepted

`judged` runs on `ubuntu-24.04` after `build` and `same-bytes`. It checks out the tagged commit, reads `context/progress/accepted.json` and the newest history line, and requires that the newest acceptance was a release pull request's (its `meta.event`, as 138's Decision 5 records it), that its commit is the tagged commit's parent or the tagged commit itself, and that the set it accepted is the set this run built: the SHA-256 of the build's `SHA256SUMS` equals the one the record carries, and the SHA-256 of `python.wasm` equals the record's artifact hash. The check is one command, `uv run python tests/harness/gather.py --prove-set <sums-sha256> <wasm-sha256>`, which reads the accepted state the way goal G7 does today and exits non-zero with one line naming the mismatch. A unit row drives it against a scratch accepted state in its four cases (holds; a different set; the newest acceptance not a release's; the acceptance not on the tagged tree).

### 3. The constitution and the release page

§5.5's release rule changes from "the tag's own run judges both again" to: the tag's run rebuilds the set from the pins on three hosts, requires the same bytes as the release pull request's accepted record, installs the wheel fresh on three systems, attests and publishes; it judges nothing again, since the tree it builds is the one the release pull request judged plus the commit that recorded that judgement. The release pull request stays the dry run, whole, on the exact commit `main` receives. `docs/contributing/release-process.md` says the same in its words, and its "Dry runs" section says the tag's run is not one.

### 4. What does not change

A tag never reuses a cached set (`inputs`'s trust rule). The weekly run, the release pull request and a dispatch keep both tiers. The attestation signs the build's assets as today. `release/version.py check --tag` and the ancestor check stay in the build job.

## Intent

A tag publishes within about 40 minutes of its push: the compile and the rebuilds in parallel, the same-bytes vote, the proof that these are the accepted bytes, the signature, the release.

## Design

Files: `.github/workflows/release.yml` (the plan's tag branch, the `judged` job, the needs of `attest` and `publish`), `release/ci_plan.py` (`decide()`'s tag branch: `rebuild` true, `judge` false), `tests/harness/gather.py` (`--prove-set`), `tests/unit/test_gather.py` and `tests/unit/test_ci_plan.py` (the rows), `tests/checks/test_rules.py` (the needs), `context/constitution.md` §5.5 and its Status line, `docs/contributing/release-process.md`, `context/changes/155-the-tags-run-publishes-what-the-release-pull-request-judged.md`.

## Scope

In: the four decisions. Out: promoting the release pull request's artifacts without a rebuild (Wasmtime's full pattern), which would skip the three-host vote at the tag; the owner keeps the vote.

## Acceptance criteria

1. On a tag the plan's `judge` output is false, `rebuild` true, `tier` empty and every judge list `[]`. Unit rows.
2. `judged` exists, needs `build` and `same-bytes`, runs only on a tag, and is in the needs of `attest` and `publish`. A rules row.
3. `gather.py --prove-set` holds in the four cases of Decision 2. Unit rows.
4. The tag's run has no judge leg and no gather (READ from the next release's tag run, named in the landing notes, with its wall time EXECUTED).
5. Constitution §5.5 and the release page say what Decision 3 says. READ.
6. The fast tier, `tests/lint` and the pull request's `ci-status` are green; the news file is present.

## Landing notes

To be written at the landing.
