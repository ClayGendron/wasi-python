# Review of spec 057 before build: the release ties what it signs to what it built

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude Opus 5.5). It wrote none of the specification, the memo, the sketch or question 95. This is the pre-build review §5.6 requires: the spec changes the release workflow (build-class). It is also a supply-chain security review of the design.
- **Reviewed:** `spec/057-the-release-ties-what-it-signs-to-what-it-built` at `2be03f1`, the diff `d70690a...HEAD`. That is the spec, `research/2026-10-18-the-release-ties-what-it-signs.md` and its evidence folder (`release.yml.diff`, `00_download.diff`, the probe, the logs), question 95, and the roadmap line.
- **Read:** `AGENTS.md`; the constitution (§4.2, §4.6, §4.8, §5.5, §5.6, §7); `context/reviews/README.md`; the 0.1.0a4 security review (F4, N1, N3, "F4 and a4's PyPI publish"); `.github/workflows/release.yml` at `d70690a`; `release/version.py` (`write_assets`); `scripts/00_download.sh`; `tests/harness/scan.py` (`without_comments`, `workflow_jobs`, `release_attestation_errors`, `rebuild_gate_errors`). I also read the pinned `actions/download-artifact@9000827…` `action.yml` and `src/download-artifact.ts`, and the pinned `actions/upload-artifact@cf430e0…` `action.yml`. I fetched them as text into `src/` beside this file.
- **Executed.** The scripts and logs are beside this file. Nothing was written in any tree.
  - The sketch was applied to a scratch copy of `release.yml` (`wf/release.yml`). The five check steps were pulled out of it: there are 5 copies, and 1 distinct text (`extract.py`, run with `uv run --no-project python -I`).
  - The check step ran on 14 cases, each on three hash tools (`cases.sh`; `cases-macos.log`, `cases-debian.log`). The tools were macOS `/sbin/sha256sum`, perl `shasum` (PATH without `/sbin`), and GNU coreutils 9.7 `sha256sum` in the local `debian:trixie-slim` image, run with `--network none`. All 42 runs gave the expected result.
  - The judge's two existing workflow scans ran on scratch copies of today's workflow and of the sketch (`scans.py`, `scans.log`). The results match the memo's `existing_scans.log`.
  - Read-only `gh`. The last dry run's log (`gh run view 39122955064 --log`, saved as `dryrun-39122955064.log`) and its job timings. `gh auth status`. The repository's environments (`gh api repos/ClayGendron/wasi_python/environments`). The a4 tag run (39135024458) was still in its first jobs, so I used the dry run instead.
- **Scoreboard:** not re-run. The diff holds documents and evidence only. Running the judge would write into a tree I may not write to.

Labels: **EXECUTED** (I ran it), **READ** (code or document), **INFERRED** (reasoned, not run).

## Summary

The core design is sound. Under it, `attest`, `publish` and `pypi` act only on the bytes the build job made, even against an attacker who controls one rebuild job and its runtime token.

- The download is by id, and an id is assigned by the server. It cannot be forged, and it cannot be re-pointed by deleting and uploading again under the same name.
- The anchor is the SHA-256 of `SHA256SUMS`, computed on the build's own runner, and handed on as a job output. Only the build job can set that output.
- Every file is checked against that list. The folder must hold exactly those files, so nothing extra is signed or published.

I re-ran the check on GNU coreutils, the tool the publish path actually uses (EXECUTED). It fails closed in every case.

Two claims in the spec are wrong, though, and the rebuild votes do not get the isolation the spec says they do:

- An empty `artifact-ids` does not fail. The pinned action falls through to downloading every artifact in the run (F1).
- A matrix shares one output namespace. A compromised leg can claim the other leg's output name (F2).

Neither one reopens F4's signing gap. Both must be written in.

## Findings, most severe first

### F1. An empty `artifact-ids` downloads every artifact in the run; it does not fail. Medium (READ, EXECUTED)

`download-artifact.ts` sets `isDownloadByIds = !!inputs.artifactIds` (line 61). An empty input is falsy, so it never reaches the by-id branch. The action then takes the last branch, "No input name, artifact-ids or pattern filtered specified, downloading all artifacts" (line 166). With several artifacts, each one lands in `path/<artifact name>/` (line 194). The error "No valid artifact IDs provided" (line 111) is thrown only for an input that is not empty but holds no ids, such as `,`. `core.getInput` trims, so `${{ '' }}` arrives as `''`.

So two statements in the spec are false:

- Decision 4: "The download would then fail ('No valid artifact IDs provided'), so the failure is closed."
- Decision 8: "every reader fails closed, with 'handed on no SHA-256' or 'None of the provided artifact IDs were found'."

The memo's "It parses each id as a number, and throws on anything else, or on an empty list" is true only for a list that is not empty.

**Failure scenario.** A rebuild leg's output arrives empty. Decision 4 expects exactly this case, and so does a re-run that loses outputs (Decision 8). `same-bytes` then downloads every artifact of the run into `rebuilds/<runner>/<name>/`. That includes `release-assets`, both legs' files, the logs, and anything an attacker uploaded. The step fails only because `cmp "$sums" rebuilds/<runner>/SHA256SUMS` finds no such file. That failure is closed by accident, and its log points the wrong way. Someone following the spec's text would diagnose "no valid ids" when the real cause is different.

For `release-assets` the check step does catch it. I simulated the download-all layout, and the check fails on all three tools at `sha256sum -c ../SHA256SUMS.sha256` (EXECUTED, case "download-all layout (empty id)"). So the signing path holds, but only because of the check step, not because of the action.

**Write in:**

1. Correct Decisions 4 and 8, and the memo's "How it looks an id up".
2. Add a guard before every download. It reads each id through `env:` and requires a non-empty decimal, for example `case "$ID" in "" | *[!0-9]*) exit 1 ;; esac`. Write it as one step per reading job, the same text in the five `release-assets` readers. `same-bytes`' copy also covers the four rebuild ids.
3. Make the guard a judge rule: the step before each download binds that download's id and refuses an empty one. Add a unit variant without the guard.

Do not use `${{ needs.x.outputs.y || 'missing' }}`. It would make the action throw ("Invalid artifact ID"), but it trips the existing `\|\|` "swallows a failure" rules in both `release_attestation_errors` and `rebuild_gate_errors` (READ, `scan.py`).

### F2. One compromised rebuild leg can still cast both votes, because a matrix shares one output namespace. Medium (READ, EXECUTED, INFERRED)

Decision 4 gives each leg its own output names. It states the purpose: "Without ids, one compromised Linux leg could replace the other leg's `SHA256SUMS` and cast both votes." The design does not achieve that against the spec's own attacker, who has code running on one leg.

- That leg's job reports whatever its steps output. The job's `outputs:` map `sums-linux-x86-64: ${{ steps.ids.outputs.sums-linux-x86-64 }}` in **both** legs.
- A background process started by the malicious input can append `sums-linux-x86-64=<its own id>` to the `ids` step's `GITHUB_OUTPUT` file. Processes survive from step to step: the runner cleans up orphans only at job end. The dry run's log shows "Cleaning up orphan processes" only in each job's final phase (EXECUTED, lines 535, 991, 1435). Hosted runners also grant passwordless sudo, so the leg can report anything it likes (INFERRED).
- GitHub's docs (quoted in the memo, READ): "the last matrix job that runs will override the output value."
- In the last dry run the x86-64 leg finished 1 h 48 min after the arm64 leg, and 1 h 38 min after `release-assets` was uploaded (EXECUTED, job timings of 39122955064). So a malicious input on the x86-64 leg wins the collision without trying. One on the arm64 leg can sleep inside its 120-minute limit, and the repository is public, so it can watch the other leg's status.

**Failure scenario.** A macOS-only malicious input makes evil bytes in `build`. A Linux-x86-64-only malicious input (the qemu `.deb`, or the x86-64 wasmtime, CPython, Cython or Ninja) uploads a copy of the evil `SHA256SUMS` and the evil wheel. It then reports its ids under both legs' names. `same-bytes` compares the evil set with two copies of itself, and the gate passes.

This does not touch F4's signing core: `release-assets` stays bound to the build. But the two-host gate of specs 012 and 040 is reduced to one host. That is the very property Decision 4 claims to protect.

Note also that the arm64 Linux wasi-sdk tarball runs on **both** legs (spec 040: the x86-64 leg runs the arm64 clang under qemu). For that one input, the two votes fall together under any design. The spec should say so.

**Write in one of two options:**

- **(a) Two jobs instead of a matrix.** Use `rebuild-linux-arm64` and `rebuild-linux-x86-64`, each with its own `outputs:` (`sums-id`, `wheel-id`). The judge requires their steps to be the same text except the runner, the timeout and the key. A job's outputs are then its own namespace, and deleting the other job's artifact only fails the gate. This is the recommendation. It also removes the need for Decision 4's fallback (F3).
- **(b) Keep the matrix, and narrow the claim.** Ids stop a leg replacing the other's artifact by name, but a leg can still claim the other's output name. Record that residual in the spec, the memo and the CHANGELOG.

### F3. Decision 4's fallback to `name:` reopens vote replacement, though not F4's signing. Low (READ, INFERRED)

The question was whether the fallback reopens F4. It does not, for what is signed: `release-assets` never falls back, and the check step still binds it. It does reopen the rebuild votes to a plain delete-and-reupload by name. Upload-artifact's own `overwrite` documents the delete; the runtime token suffices (READ, `ul-action.yml`). That is simpler than F2's output trick.

**Write in:** with F2(a), drop the fallback. Without it, a leg's empty output fails closed (once F1's guard is in), and the fix is to repair the job, not to go back to names. If (b) is chosen, keep the fallback but name its residual as above.

### F4. Question 95 should state as facts what it frames as conditions. Low (EXECUTED)

- "If the agent's `gh` is logged in as you": it is. `gh auth status` shows the account `ClayGendron`, with the scopes `repo` and `workflow`. So the agent can approve pending deployments, and it can edit environment rules, as the owner. The point the question makes is right: a reviewer gate the agent can pass as the owner is not a human gate. It should say so as fact, and add that the agent can also change the rule itself.
- "Prevent self-review … would also stop you from approving a tag you pushed yourself": this understates it. Every run the agent starts has the owner as its actor. With the owner as the only reviewer and self-review prevented, **no** run could ever be approved.
- The `pypi` environment exists today with no protection rules and no deployment-branch policy (EXECUTED, `gh api …/environments`: `"protection_rules":[]`, `"deployment_branch_policy":null`). That is why option (a)'s tag rule has value now: it stops a branch's run from minting a token through `pypi`. The question should state that fact.
- The recommendation, (a), is sound. Say once that a tag rule does not constrain the agent, which can push a `v*` tag. It constrains other paths.

### F5. Gaps in the judge's new rules. Low (READ, EXECUTED)

1. **Rules 7 and 8 name five jobs.** A sixth job added later, such as another publisher, could download `assets-id` by id and skip the check, and still pass rule 4. Make it general: every job that downloads `needs.build.outputs.assets-id`, and every job granted `contents: write` or `id-token: write`, has the check step right after its download.
2. **Rule 4 should also refuse the inputs that change what "by id" means.** These are `github-token`, `run-id` and `repository` (a download from another run), `merge-multiple`, and `skip-decompress`. It should also refuse any other way to fetch an artifact (`gh run download`, `actions/github-script`). And it must look at `with: name:`, not at a step's display `- name:`.
3. **Rule 10 can be stronger at no cost.** The sketch has no `${{` inside any `run:` script (EXECUTED, grep of `wf/release.yml`). So the rule can be "no `${{` in any `run:`", not only `${{ needs.`.
4. **The behaviour cases.**
   - Add "the wheel swapped and `SHA256SUMS` rewritten to match". It is the actual F4 move, and it fails at the anchor (EXECUTED, all three tools).
   - Add "a hidden file". It fails (EXECUTED), and `attest`'s glob would not see it, which is why the check's `find` matters.
   - Acceptance 1 says all seven cases fail on `d70690a` "because there is no check step". That holds only if `check_step_script` raises when no step is found. An empty script run in bash exits 0, so the "own files" case would pass there. Say that the test fails when no step is found.

### F6. Evidence before a tag: state the argument, and the one unknown left. Low, informational (INFERRED)

The dry run cannot run `attest`, `publish` or `pypi`. The spec's argument is that the text is the same (rule 9) and the wiring is checked statically (rule 6). That is fair, and it can be made stronger:

- `same-bytes` runs with `permissions: {}`, which is a subset of every publish-path job's grants.
- The artifact download uses the runner's runtime token, not `GITHUB_TOKEN`.
- So a by-id download that works in `same-bytes` works in `attest`, `publish` and `pypi`.

What stays unexercised until the tag is `environment: release` being created on first use. If that failed, `attest` would already have signed (permanent), with no release made, and the recovery is to re-run `publish`. That is acceptable. The owner could also create `release` by hand beforehand (one click, under question 94) to remove the unknown. The spec should say this in Decision 10.

### F7. Notes, nothing to change

- **Decision 7.** A commit pin of 40 hex characters can still name a commit that exists only in a fork (an "impostor commit"), and a text scan cannot see that. No action is bumped here. For a later bump, the README's *Releasing* could say: check that the commit is the named release's tag (`gh api repos/<o>/<r>/git/ref/tags/<v>`).
- **N1's loop.** `for name in $NAMES` is unquoted, so the names are subject to pathname expansion. No current name has `*`, `?` or `[` (READ), and the static `unpinned_fetch_errors` guard covers the same property. A `set -f` around the loop would close it.

## What I checked and found to hold

- **The anchor cannot be swapped before it is hashed** (READ). Only the build job writes `release-assets/` (`version.py write_assets`, `hash  name` with two spaces, LF). The `sums` step hashes it in the same job, before the upload. No other job can set `build`'s outputs (INFERRED: a job reports only its own outputs, and no API writes another job's).
- **Ids and digests** (READ, EXECUTED).
  - Artifact ids are assigned by the server. A deleted or replaced artifact is gone from the `latest: true` listing, so its id is not found and the download throws.
  - An attacker in a re-run can upload a newer artifact named `release-assets`. That hides the build's id: the result is a denial of service, not a swap.
  - The upload's digest is the zip's. The dry run's "SHA256 digest of uploaded artifact is 56659eaf…" equals each download's "Expected Digest: sha256:56659eaf…". So the per-file check against the build's own hash is rightly the real proof, and the digest is rightly only printed.
  - The strings "Downloading artifacts by ID" and "Expected Digest" exist in the pinned source, so Acceptance 6's quotes are valid.
  - Several ids only warn, which is why one id per step is right. A comma list handed on by a compromised leg lands in sub-folders and fails `cmp`.
- **The check step** (EXECUTED).
  - The five copies are byte-identical in the sketch. `without_comments` leaves `sed 's#^\./##'` intact, because its regex needs whitespace before the `#`.
  - All 14 cases behave as expected on GNU, BSD and perl tools: good, empty, non-hex, uppercase, 63 hex, a swapped wheel, the tar missing, an extra file, a hidden file, an extra file with a space, a sub-folder, sums rewritten, the download-all layout, and a symlink with the same bytes (passes).
  - A symlink cannot reach the check through the build's zip, and CRLF cannot either (the download is binary and the build writes LF).
  - A name with a space fails closed.
- **Windows** is not on the publish path. Its leg is evidenced by the dry run, as the spec says. If Git Bash ever found Windows' own `find` or `sort` first, the check would fail closed (`have` empty).
- **N1** (READ). The fix compares names, not counts. It keeps `--ignore-missing`, and it leaves `pinned()` alone. The harness test exercises the real script with a fake `uname` and a `curl` that fails if called. That is the right stand-in, and it fails on `d70690a`.
- **N3** (READ, EXECUTED).
  - `publish` gets `environment: release`. `pypi` keeps `pypi`, which matters because the trusted publisher is bound to it.
  - `enable-cache: false` is on all four `setup-uv` steps.
  - The workflow-level `permissions: {}`, with each job's grant stated, is least privilege. No job uses a scope it lacks: `build` needs checkout and `setup-uv`'s release download.
  - `same-bytes` at `{}` still satisfies `rebuild_gate_errors`' "no more than contents: read".
- **The existing scans** (EXECUTED). On the sketch, `release_attestation_errors` passes, and `rebuild_gate_errors` reports exactly the four by-name rules the spec says it will amend.
- **Queue and constitution.** There is no open question in the spec (§5.2, §7), nothing is timed (§4.9), and no pin is added (§4.2). It is build-class, so it takes one slot, as §5.7 says. The owner's settings are left to questions 94 and 95. That is right: §7 forbids the agent changing them.

## Acceptance criteria against the design

1. **Seen failing first.** Met once F5.4's "fails when no step is found" is written in.
2. **13 new checks.** Consistent: 9 in `test_rules.py` and 4 in `test_v1_5`. F1's guard rule and F2(a) would change the count and the rebuild-gate amendments, so the builder restates them.
3. **Unit tests, one bad variant per rule.** Add F1's guard variant and F5's rule-4 variants.
4. **The probe gives 0 problems on the draft.** EXECUTED by the memo, and I reproduced the extraction. The probe should also learn F1's guard.
5. **The judge.** Standard. `--accept-judge`.
6. **The dry run.** Sound. The evidence lines exist (READ). With F2(a), `same-bytes` downloading "both rebuild legs by id" becomes "both rebuild jobs".
7. **The first tag run.** Sound. F6's sentence belongs in Decision 10.

## Verdict

**Ready once F1 to F5 are written in.**

- F1 and F2 are Medium. The spec's fail-closed explanation for an empty id is false, and the matrix does not isolate the two votes as claimed.
- F3 to F5 are Low.
- F6 and F7 can be answered in writing.

The binding of what is signed and published to the build's bytes is correct as designed.

## Disposition

The author's disposition is the spec's own section "Disposition of the pre-build review (2026-10-18)", at `bec7597`, and the same text is in `disposition.md` beside this file. In short:

- F1 is written in: a guard step before every download, and rule 10.
- F2 is written in as option (a), the lane's ruling: two rebuild jobs.
- F3 is written in: the fallback to names is dropped.
- F4 is written in: question 95 is restated as facts.
- F5 is written in: rules 4, 7, 8 and 11, the new behaviour cases, and `workflow_step_script` raising when the step is absent.
- F6 is answered in Decision 10, and F7 in Decisions 5 and 7.

## Confirmation (2026-10-18)

- **Reviewed:** `bec7597`, the diff `git diff 2be03f1 bec7597`. That covers the spec, the memo, the evidence folder (the revised `release.yml.diff`, `probe_workflow.py` and its log, `check_step_cases.log`, `existing_scans.log`, `00_download.diff`, `n1_download_runs.log`), question 95 and the roadmap.
- **Executed.** Scripts and logs are in `confirmation/` beside this file. Nothing was written in any tracked file.
  - The revised sketch was applied to a scratch copy of `release.yml` at `d70690a`. `extract2.py` (run with `uv run --no-project python -I`) found 5 check steps with 1 distinct text, and 5 `release-assets` guards with 1 distinct text. The check step's `run:` is byte-identical to the one I tested before.
  - My 14 check-step cases ran again on all three tools: macOS `/sbin/sha256sum`, perl `shasum`, and GNU coreutils 9.7 in `debian:trixie-slim` with `--network none`. All 42 gave the expected result (`cases-macos.log`, `cases-debian.log`).
  - The guard ran on 8 ids on macOS and on Debian. These exit 1: `''`, `12x`, `1,2`, `' 12'`, `-1` and `0x1f`. These exit 0: `123456789`, and `12138231122` (a real id from the dry run).
  - The memo's `probe_workflow.py` (PyYAML 6.0.3, in a throwaway uv environment) gave 23 problems on today's workflow and 0 on the revised sketch, matching the memo (`probe-review.log`). The existing scans on the sketch give the expected results: `release_attestation_errors` passes, and `rebuild_gate_errors` reports "no rebuild job", which is the scan the spec rewrites (`scans.log`).
  - Six fresh mutations, beyond the memo's three. The probe is the author's tool, not the judge, so each is also judged against the spec's rules as written:

    | mutation | probe | the spec's rules |
    |---|---|---|
    | M1: `same-bytes`' rebuild guard still binds `X86_64_WHEEL_ID` in `env:`, but its loop no longer tests it | passes | **passes** (rule 10 asks only that the expression is bound and the `case` exists) |
    | M2: `continue-on-error: true` on that rebuild guard | passes | **passes** (no rule forbids it; that guard has no twin to compare with) |
    | M3: `publish`'s guard tests `$ASSETS_IDX` | passes | caught (rule 10: the `release-assets` guards are the same text) |
    | M4: the x86_64 job uploads under the arm64 job's name | caught | caught (rebuild-gate identity rule) |
    | M5: `same-bytes` downloads the x86_64 job's `sums-id` into `rebuilds/ubuntu-24.04-arm` | passes | caught, if the rewritten rule pairs each job's id with its own runner's path, as today's name rule pairs `name:` with `path:` |
    | M6: `continue-on-error: true` on `publish`'s check step | — | caught **only if** "the same text" compares whole steps: whole blocks give 2 distinct copies, `run:` alone gives 1 (`m6-check.sh`) |

    In M1 and M2 an empty id still fails closed later. The download fetches everything, and `cmp` finds no `rebuilds/<runner>/SHA256SUMS`. But that is exactly the accidental failure F1 replaced with a guard. In M6, `publish` would go on to upload bytes that were never verified, and that is the regression the judge exists to stop.

**Each finding against its answer:**

- **F1: closed.**
  - Decision 2 states the fact, with the right lines, and so does the memo.
  - Decision 8's messages are now true.
  - A guard comes before every download, and it is not written with `||`.
  - The judge runs four behaviour cases on the guard itself.
  - A small remaining inaccuracy, which needs no change: the memo says the action "throws on anything else". In fact `parseInt("12x")` is 12. The guard refuses `12x` (EXECUTED), so nothing depends on it.
- **F2: closed.**
  - The sketch has `rebuild-linux-arm64` and `rebuild-linux-x86-64`, each with its own `sums-id` and `wheel-id`.
  - `same-bytes` needs both jobs and reads each one's outputs. The identity rule set aside `name`, `runs-on` and `timeout-minutes`, and caught M4.
  - The shared arm64 wasi-sdk tarball is stated in Decision 4 and in Scope.
- **F3: closed.** No fallback remains.
- **F4: closed.**
  - Question 95 now states the account, the scopes, the deadlock under self-review, `pypi`'s open state today, and what a tag rule does not constrain.
  - It adds what would make a reviewer a real gate: a separate identity for the agent.
- **F5: closed for 5.1 to 5.4, with one gap left (N1 below).**
  - Rules 7 and 8 are general.
  - Rule 4 lists every refused input and every other fetch path, and it reads `with:`.
  - Rule 11 refuses any `${{` in a `run:`.
  - The two new cases are in.
  - `workflow_step_script` raises when the step is absent.
- **F6: answered.** Decision 10 states the subset-of-grants argument, and names the one unknown and its recovery.
- **F7: taken.**
  - Decision 7 names impostor commits, with the README line for later bumps.
  - `set -f` is in, and the memo re-ran N1 with it on all three hosts.
  - The acceptance counts add up: 15 in `test_rules.py` (1 + 1 + 9 + 4) and 4 in `test_v1_5`, so 19.

**What remains: N1, Low, one rule's wording.** M1, M2 and M6 show that the guard and check rules can be met while the step is made inert. Write into the Design's rules:

1. Rules 9 and 10 compare **whole steps**, every key, not only their `run:` blocks.
2. No guard step, check step or `actions/download-artifact` step carries `if:` or `continue-on-error:`. This covers the `same-bytes` rebuild guard, which has no twin.
3. Rule 10's guard must test the variable that holds that download's expression. A variable bound in `env:` but not named in the `case`, or in the loop's list, does not count.

Add one unit variant for each of M1, M2 and M6. Also state that the rewritten `rebuild_gate_errors` pairs each `artifact-ids` with its own runner's `path:` (M5).

**Verdict:** ready to build once N1 is written in. N1 is a few lines in the Design and 3 unit variants, and needs no fresh review: the lane can check it against this text. Everything else is closed.
