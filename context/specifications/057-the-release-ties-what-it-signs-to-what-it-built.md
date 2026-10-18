# 057 — The release ties what it signs to what it built

- **Status:** drafted 2026-10-18; awaiting its pre-build review (required: build-class, the
  release workflow). Drafted on `spec/057-the-release-ties-what-it-signs-to-what-it-built`
  from main `d70690a`. It must land before the next release after 0.1.0a4 (0.1.0a5, any other
  alpha, or 0.1.0 final). The a4 security review's Confirmation set that bound.
- **Owner:** Clay Gendron
- **Kind:** build-class: the release workflow; a judge change. It changes
  `.github/workflows/release.yml` (every job), `scripts/00_download.sh` (the end of its verify
  block), `tests/harness/scan.py` (three new scans, and an amended `rebuild_gate_errors`),
  `tests/checks/test_rules.py`, `tests/checks/test_v1_5_rebuild_from_pins.py`,
  `tests/unit/test_scan.py`, `README.md` (*Releasing*), `CHANGELOG.md`, and a one-line
  amendment note in specs 009 (Decision 1) and 012 (Decision 7). It changes no artifact, no
  pin, no recipe that makes bytes, no `src/` file, and not the guest.
- **Depends on:** 056 (the a4 security review's findings; its Decision 6 names this
  follow-up, and its question 94 holds the owner's repository settings), landing now. Also
  on 004 (the release workflow), 009 (`attest` and its rules scan), 012 and 040 (`rebuild`
  and `same-bytes`, and their gate scan), and 028 (the `verify` job's install check). All are
  landed.
- **Research it stands on:** `../research/2026-10-18-the-release-ties-what-it-signs.md`. It
  holds what the pinned artifact actions do (READ at the pinned commits), the drafted workflow
  parsed (EXECUTED), the drafted check step run on tampered folders (EXECUTED), and N1 before
  and after on all three hosts (EXECUTED). It also stands on the 0.1.0a4 security review
  (`build/reviews-evidence/a4-security/0.1.0a4-security-review-2026-10-18.md` in the main tree,
  git-ignored): F4, N1, N3, and the Confirmation's "F4 and a4's PyPI publish".

## The problem

`same-bytes`, `verify`, `attest`, `publish` and `pypi` each fetch the build's files by the
name `release-assets`. Nothing ties those files to the build job. A pinned input that is
malicious and used only on a Linux rebuild host could steal the runner's token and replace the
artifact before `attest` runs. Then `same-bytes` would compare the attacker's files with
themselves, and `attest` would sign them (the review's F4, READ and INFERRED). F4 does not
block a4. It must close before the next release.

Two notes ride along:

- **N1.** The download step does not fail when a fetched file has no pin. It exits 0 at
  "34 of 35 verified" (EXECUTED, the memo). `pinned()` still refuses the file at use, so N1 is
  a missing early failure, not a way in.
- **N3, its workflow part.** `publish` has no environment. The `setup-uv` cache is left to its
  default. The repository's own settings (rulesets, an environment's reviewers) are the
  owner's: question 94.

## Decisions

1. **The build job hands on two values, and prints a third.** A job output is a value a job
   hands to the jobs that need it.
   - `assets-id` is the `artifact-id` output of the step that uploads `release-assets`. That
     step gets `id: assets`.
   - `sums-sha256` is the SHA-256 of `release-assets/SHA256SUMS`. A step `id: sums` computes
     it from the local file, before the upload: `shasum -a 256 release-assets/SHA256SUMS | cut
     -c1-64`, written to `$GITHUB_OUTPUT` as `sha256`.
   - A step after the upload prints the record for people:
     `release-assets: artifact <id>, digest <artifact-digest>`, then `SHA256SUMS: sha256 <hash>`,
     then `SHA256SUMS` itself. The values reach the script through `env:`.
   - **Why two values.** The id is the pointer. A download by id cannot pick up another
     artifact, and a deleted or replaced artifact fails the download. The SHA-256 is the
     content anchor. The build job's own runner computes it from the files it made, so it
     does not depend on the artifact service at all.
   - **Why the digest is printed, not handed on.** The download action checks the artifact's
     digest itself (Decision 2), against the service's record. No step on the reading side can
     see that digest: the action has no digest output (READ). The per-file check of Decision 3
     is the stronger proof anyway.
   - `SHA256SUMS` already lists the wheel and the `.tar.xz` (`release/version.py`,
     `write_assets`). So one hash covers both, the wheel's hash included.

2. **Every download is by id, and fails on a digest mismatch.** Every
   `actions/download-artifact` step in the workflow takes `artifact-ids:
   ${{ needs.<job>.outputs.<name> }}` with exactly one id. No step takes `name:` or `pattern:`.
   Every step says `digest-mismatch: error`.
   - The pinned v8.0.2 already defaults to `error` (READ). Saying it outright means an action
     bump cannot loosen it quietly, and the judge can see it.
   - One id per step, because the action only warns when some of several ids are missing
     (READ, `download-artifact.ts` lines 139-145). With one id, a missing artifact throws.
   - `pypi` gains `build` in its `needs` (`needs: [build, publish]`). A job can read only the
     outputs of the jobs it needs directly.

3. **One check step, the same in all five readers, right after the download.** In
   `same-bytes`, `verify`, `attest`, `publish` and `pypi`, the step after the `release-assets`
   download is "These are the bytes the build job made". Its text is this, exactly:

   ```yaml
         - name: These are the bytes the build job made
           # By id, the digest checked by the action; then SHA256SUMS against the hash the build job
           # handed on, every file against SHA256SUMS, and no other file (spec 057).
           env:
             SUMS_SHA256: ${{ needs.build.outputs.sums-sha256 }}
           run: |
             set -eu
             case "$SUMS_SHA256" in
               "" | *[!0-9a-f]*) echo "the build job handed on no SHA-256 of SHA256SUMS"; exit 1 ;;
             esac
             if [ "${#SUMS_SHA256}" -ne 64 ]; then
               echo "the build job handed on no SHA-256 of SHA256SUMS"
               exit 1
             fi
             if command -v sha256sum > /dev/null; then sum="sha256sum"; else sum="shasum -a 256"; fi
             printf '%s  SHA256SUMS\n' "$SUMS_SHA256" > SHA256SUMS.sha256
             ( cd release-assets && $sum -c ../SHA256SUMS.sha256 && $sum -c SHA256SUMS )
             want=$( { awk '{print $2}' release-assets/SHA256SUMS; echo SHA256SUMS; } | LC_ALL=C sort)
             have=$(cd release-assets && find . -mindepth 1 | sed 's#^\./##' | LC_ALL=C sort)
             if [ "$want" != "$have" ]; then
               echo "release-assets holds other files than the build job's"
               exit 1
             fi
   ```

   - **What it proves.** It proves four things, in order:
     1. the build job handed on a real hash;
     2. `SHA256SUMS` is the build's;
     3. every file it lists matches it;
     4. the folder holds nothing else.

     The last matters. `attest` signs `release-assets/*`, and `publish` uploads
     `release-assets/*`, so an extra file would be signed and published.
   - **It fails closed.** An empty output, another hash, a swapped wheel, a missing file, an
     extra file or a sub-folder each exit 1. The memo ran all eight cases, on both hash tools
     (EXECUTED).
   - **Where its scratch file goes.** `SHA256SUMS.sha256` is written beside `release-assets/`,
     never inside it. So the signed and published glob is unchanged.
   - **Why inline, not a script in the repository.** `attest` and `pypi` have no checkout. They
     should not gain one: spec 009 keeps the identity-token job free of the repository's code,
     setup-uv and uv. A composite action would need a checkout too. YAML anchors would make
     the judge resolve aliases, and it reads the workflow as text, with no YAML library (spec
     009, Decision 6). So the step is written out five times. The judge requires the five
     copies to be the same text, so they cannot drift.
   - **Values travel by `env:`, never as `${{ … }}` inside a `run:` script.** Our own job makes
     these outputs. Still, the rule costs nothing, and it removes script injection as a class.
   - **The hash tool.** It is `sha256sum` where the runner has it: GNU coreutils on Ubuntu and
     in Git for Windows's bash, and `/sbin/sha256sum` on recent macOS. Otherwise it is perl's
     `shasum -a 256`, which the recipe already uses. Both read the `<hash>  <name>` format with
     `-c` (EXECUTED on macOS for both; the dry run evidences Ubuntu and Windows).

4. **The rebuilds hand on their ids too.**
   - The `rebuild` matrix gains `key: linux-arm64` and `key: linux-x86-64` beside each
     runner's `timeout`. Its two uploads get `id: sums` and `id: wheel`.
   - A step `id: ids` writes `sums-<key>=<id>` and `wheel-<key>=<id>` to `$GITHUB_OUTPUT`,
     through `env:`.
   - The job's `outputs:` maps the four names `sums-linux-arm64`, `sums-linux-x86-64`,
     `wheel-linux-arm64` and `wheel-linux-x86-64` from `steps.ids.outputs`. That is the
     docs' pattern for a matrix: each leg writes only its own names (READ, the memo).
   - `same-bytes` downloads each by id into today's paths (`rebuilds/<runner>`,
     `rebuilt-wheels/<runner>`).
   - **Why.** These files are never signed. But they are the gate's two votes. Without ids, one
     compromised Linux leg could replace the other leg's `SHA256SUMS` and cast both votes.
   - **The fallback, decided now.** A real run might show one leg's output empty. The download
     would then fail ("No valid artifact IDs provided"), so the failure is closed. In that case
     only the four rebuild downloads go back to `name:`. The judge's rule 4 then exempts exactly
     those four, and the landing notes record the residual. The `release-assets` downloads
     never fall back.

5. **N1: the download step fails on a fetched name with no pin.** After its summary line,
   `scripts/00_download.sh` checks every name in `$NAMES` for a `<name>: OK` line in the
   verify file. If any name has none, it prints `ERROR: no pin in downloads/SHA256SUMS for:
   <names>` and exits 1 (`../research/2026-10-18-the-release-ties-what-it-signs/00_download.diff`).
   - It compares names, not counts. A repeated `get` of one name would make the counts differ
     with nothing wrong.
   - `--ignore-missing` stays. `SHA256SUMS` lists other hosts' files, and they are rightly
     absent.
   - `pinned()` is unchanged. It re-checks every file at use.
   - Fixed, the script exits 1 naming the file on all three hosts. With every pin present it
     exits 0, the research input included (EXECUTED, the memo).

6. **N3, the workflow's side.**
   - **`publish` names `environment: release`. `pypi` keeps `environment: pypi`.**
     - These are two environments, not one. PyPI's trusted publisher was set up against the
       `pypi` environment (`../decisions.md`, question 23), so renaming it would break
       publishing until the owner edits PyPI.
     - The two jobs also hold different powers: `contents: write` against `id-token: write`.
   - **Before the owner protects `release`.** A job that names a missing environment creates it,
     with no protection rules (READ, GitHub's docs).
     - So the first tag run after landing creates `release` unprotected. It behaves exactly as
       today.
     - Dry runs never reach `publish`, so they never create it.
     - Once the owner adds rules (question 94), `publish` waits for them before it gets a
       runner.
     - How those rules sit with the agent publishing alphas is the owner's choice
       (question 95). The workflow is the same either way.
   - **`enable-cache: false` on every `setup-uv` step** (four: `build`, `rebuild`, `verify`,
     `publish`).
     - Today's default, `auto`, already skips the cache on a tag push, and uses it on a manual
       dry run (READ).
     - With the cache off everywhere, the dry run takes the tag run's path, and nothing is
       restored from a cache that a branch's run could have written.
   - **Least privilege, stated per job.** The workflow-level `permissions:` becomes `{}`. Each
     job states its own:

     | job | permissions |
     |---|---|
     | `build`, `rebuild`, `verify` | `contents: read` (checkout) |
     | `same-bytes` | `{}`: no checkout and no API call. Its downloads use the runner's artifact service, not `GITHUB_TOKEN` (READ, the memo, INFERRED for the token) |
     | `attest` | `id-token: write`, `attestations: write`, `contents: read` (spec 009, unchanged) |
     | `publish` | `contents: write` |
     | `pypi` | `id-token: write` |

     If the dry run shows `same-bytes`' download refused under `{}`, its fallback is
     `contents: read`, recorded.

7. **Every action stays pinned by a full commit, and the judge now says so.** Every `uses:` in
   today's workflow is a 40-hex commit with its release in a comment (EXECUTED, the memo's
   probe). No check enforced that. A new scan covers every file in `.github/workflows/`. A
   `uses:` is either local (`./…`) or `owner/repo[/path]@<40 hex>`. This specification bumps
   no action. A bump is its own change.

8. **Recovery is unchanged.** The README says to re-run the failed jobs of the same run, never
   to push the tag again.
   - A re-run of failed jobs reuses the build job's outputs and the run's artifacts (INFERRED,
     not exercised).
   - If it did not, every reader fails closed, with "handed on no SHA-256" or "None of the
     provided artifact IDs were found". The recovery is then to re-run all jobs. The build is
     reproducible, so it makes the same bytes. A second attestation of the same bytes is
     harmless.
   - *Releasing* gains that sentence.

9. **The owner's hand check for a4 stops being a gate.** For a4, the review asked for one check
   by hand: the SHA-256 of every asset on PyPI and on the GitHub release must equal the
   `SHA256SUMS` in the build job's log.
   - Once this lands, every job that checks, signs or publishes proves its files equal the
     build's list before it acts. The build job's log prints the id, the digest, `SHA256SUMS`
     and its hash.
   - What remains is the upload after the last check: `gh release create` and PyPI's upload.
     That is the services' own integrity.
   - So the comparison becomes a release record, not a gate. Whoever cuts a release (the agent,
     for alphas) runs it after publishing and records it in that release's notes:
     - `gh release download v<version>`, then `shasum -a 256 -c` against the build log's
       `SHA256SUMS`;
     - PyPI's `digests.sha256` for the wheel (its JSON API) against the wheel's line.
   - A mismatch is a security incident: yank, and report under `SECURITY.md`.

10. **How it is evidenced.**
    - **The judge.** It reads the workflow as text, as specs 009 and 012 do. It also runs the
      check step itself, and the download script itself, on scratch folders (Design). Every new
      check is seen failing on `d70690a`'s tree, or is named as a guard that passes there.
    - **The dry run after landing** (a `workflow_dispatch`; the agent may dispatch dry runs,
      `../decisions.md`, 2026-10-18).
      - `same-bytes` and the three `verify` legs run the same check step, on that run's files,
        downloaded by id.
      - `attest`, `publish` and `pypi` are skipped, as every dry run skips them. Their copies of
        the step are the same text (rule 9 below). Their wiring to `needs.build` is checked
        statically (rule 6).
      - So the dry run exercises the exact text the publish path runs.
    - **The first tag run after landing.** Its `attest`, `publish` and `pypi` logs (the check's
      `OK` lines, "Downloading artifacts by ID") are recorded in that release's notes, beside
      Decision 9's comparison.

11. **Its place in the queue.** It is build-class (`scripts/`, the release workflow), so it
    builds as the only build-class change in flight (§5.7).
    - The next release after a4 waits on it. Its build and review are small (no artifact
      rebuild; the frozen set judges it). So it takes the next build-class slot.
    - A package specification that lands first and edits the workflow is rebased over. Any
      download it adds must be by id (rule 4).
    - The judge change is accepted with `--accept-judge`.

## Intent

Every job that checks, signs or publishes the release proves, before it acts, that its files
are the bytes the build job made. It does this by the artifact's id and by every file's
SHA-256, and it fails closed otherwise. The download step refuses a fetched file with no pin.
The publish jobs name their environments, run with no cache, and hold only the permissions
they use.

## Design

```
.github/workflows/release.yml
  permissions: {}                       workflow level; each job states its own (Decision 6)
  build      outputs assets-id, sums-sha256; steps sums, assets (upload), the printed record
  rebuild    matrix key per runner; uploads id sums, wheel; step ids; four outputs
  same-bytes downloads by id (release-assets, 2 sums, 2 wheels); the check step
  verify     download by id; the check step; cache off
  attest     download by id; the check step; then attest, then verify (spec 009 order kept)
  publish    environment: release; download by id; the check step; cache off
  pypi       needs [build, publish]; environment: pypi; download by id; the check step
scripts/00_download.sh                  the name check after the summary (Decision 5)
tests/harness/scan.py
  release_binding_errors(text)          rules 1-13 below, one line per breach
  action_pin_errors(text)               Decision 7
  unpinned_fetch_errors(script, pins)   every get/research name is in SHA256SUMS
  check_step_script(text)               the check step's run: block, from attest, as text
  rebuild_gate_errors                   amended: rebuild files by id, with keys (Decision 4)
tests/checks/test_rules.py              3 checks (one parametrized x7)
tests/checks/test_v1_5_rebuild_from_pins.py  2 checks (one parametrized x3)
tests/unit/test_scan.py                 a good workflow, and one bad variant per rule
README.md (Releasing), CHANGELOG.md     the next version's Security entry: F4, N1, N3
specs 009 and 012                       one amendment line each, pointing here
```

The drafted workflow is in the memo's evidence (`release.yml.diff`), as a sketch. It parses,
and the memo's probe finds nothing in it (EXECUTED).

**`release_binding_errors`.** It works on the workflow without comments, and gives one line
per breach. Its rules:

1. `build`'s `outputs:` maps `assets-id` from `steps.<id>.outputs.artifact-id`, where `<id>`
   is an upload step with `name: release-assets`.
2. `build`'s `outputs:` maps `sums-sha256` from a step whose `run:` hashes
   `release-assets/SHA256SUMS`. That step comes before the `release-assets` upload.
3. After that upload, a `build` step binds the upload's `artifact-id` and `artifact-digest` in
   `env:`, and `cat`s `release-assets/SHA256SUMS`.
4. Every `actions/download-artifact` step in the workflow has `artifact-ids:
   ${{ needs.<job>.outputs.<name> }}`, and no `name:` or `pattern:`.
5. Every `actions/download-artifact` step has `digest-mismatch: error`.
6. Every `needs.<job>.outputs.<name>` that a job reads names a job in its `needs:`, and an
   output that job's `outputs:` defines.
7. `same-bytes`, `verify`, `attest`, `publish` and `pypi` each download
   `needs.build.outputs.assets-id` into `path: release-assets`.
8. In each of those five, the step right after that download is the check step. It binds
   `SUMS_SHA256: ${{ needs.build.outputs.sums-sha256 }}`. Its `run:` checks `SHA256SUMS.sha256`
   and `-c SHA256SUMS`, and compares `find . -mindepth 1` with the listed names.
9. The five check steps are the same text.
10. No `run:` script contains `${{ needs.`.
11. `publish` has `environment: release`, and `pypi` has `environment: pypi`.
12. Every `astral-sh/setup-uv` step has `enable-cache: false`.
13. The workflow-level `permissions:` is `{}`, and each job's permissions are exactly its row
    in Decision 6's table.

`rebuild_gate_errors` keeps every rule it has, with three changes:

- Its "same-bytes does not name <runner>'s SHA256SUMS / rebuilt wheel" rules now want
  `artifact-ids: ${{ needs.rebuild.outputs.sums-<key> }}` (and `wheel-<key>`), with the
  runner's path.
- A new rule: each runner in the matrix carries its `key`, from a table in the scan
  (`ubuntu-24.04-arm` is `linux-arm64`, `ubuntu-24.04` is `linux-x86-64`).
- Another: `rebuild`'s `outputs:` maps all four names from `steps.ids.outputs`.

If Decision 4's fallback is taken, the three changes revert to the name rules, and the
landing notes say so.

**The behaviour checks.**

- `test_the_release_check_refuses_other_bytes[case]` takes `check_step_script` from
  `release.yml`. It runs that script in `bash`, in a temporary folder with a three-file
  `release-assets/` (a fake wheel, a fake `.tar.xz`, their `SHA256SUMS`).
  - The case `the build's own files` must exit 0.
  - Six cases must exit non-zero: `SUMS_SHA256` empty, `SUMS_SHA256` another hash, the wheel's
    bytes changed, the `.tar.xz` removed, an extra file, a sub-folder.
- `test_download_step_fails_on_a_fetched_file_with_no_pin[host]` copies
  `scripts/00_download.sh`, `line.sh` and `line.conf` to a temporary repository. There it
  writes one small fake file per fetched name, and a `SHA256SUMS` of those fakes. It puts a
  fake `uname` (one host key per case: `MACOS_ARM64`, `LINUX_AARCH64`, `LINUX_X86_64`) and a
  `curl` that exits 99 on `PATH`.
  - With every pin, the script exits 0 and prints `downloads: N pins, 0 fetched, N verified`.
  - With one name's line removed from `SHA256SUMS`, it exits 1, and stderr names the file.
  - Nothing is fetched. A call to the fake `curl` fails the case.

## Scope

**In:** the above.

**Out, each with its reason:**

- **The repository's settings** (rulesets on `main` and `v*`, the environments' reviewers and
  tag rules). They are the owner's account settings: questions 94 and 95. The judge cannot
  see them (N3).
- **A read-back after `gh release create` or PyPI's upload.** The bytes leave the last check
  for the services' own storage. Decision 9 records the comparison per release instead.
- **Rehearsing `attest`, `publish` or `pypi` in a dry run.** A signature is permanent in
  Sigstore's public log (spec 009, Decision 5). Their steps are the dry run's steps by text
  (rule 9).
- **Bumping any action**, or changing `attest`'s rules (spec 009). Decision 7.
- **Proving the build job itself honest.** That is what `same-bytes` and the two rebuilds are
  for (specs 012 and 040). This specification ties every later job to the build's output. It
  does not re-judge the build.

## Acceptance criteria

1. **Seen failing first, on `d70690a`'s tree**, before any change, each recorded with its
   output:
   - `test_the_release_signs_and_publishes_what_build_made` fails. Its report names at least
     rules 1, 2, 3, 4 (nine downloads by name), 5, 7, 8, 11, 12 and 13.
   - All seven `test_the_release_check_refuses_other_bytes` cases fail, because there is no
     check step.
   - All three `test_download_step_fails_on_a_fetched_file_with_no_pin` cases fail, because
     the script exits 0. The memo already shows this (EXECUTED).
   - Two new checks pass on that tree, and the landing notes say so:
     `test_every_action_is_pinned_by_commit` and `test_every_fetched_file_is_pinned`. They are
     guards on properties that already hold. Each is seen failing on its unit test's bad
     variant instead.
2. **13 new checks pass after the change:**
   - `test_rules.py`: 1 binding check, 1 pin check, 7 check-step cases;
   - `test_v1_5_rebuild_from_pins.py`: 3 download cases, 1 fetched-is-pinned check.

   `test_release_workflow_rebuilds_on_two_more_hosts` and
   `test_releases_attest_and_verify_their_assets` still pass, on their amended and unchanged
   scans.
3. **The unit tests.** `test_scan.py` feeds a good workflow to `release_binding_errors`, and it
   passes. Then 13 bad variants, one per rule, each yield exactly their own error.
   - `action_pin_errors` passes a good workflow. A tag (`@v4`) and a short commit each yield
     their error.
   - `unpinned_fetch_errors` passes a good script, and names an unpinned `get`.
   - The rebuild gate's four name-based variants become id-based, and one is added for a
     missing `key`. Each yields exactly its own error.
4. **The workflow parses** with PyYAML in a throwaway environment. The memo's
   `probe_workflow.py` reports 0 problems on it, against 13 on `d70690a`.
5. **The judge.**
   - The fast tier first, then the full `uv run pytest` once (AGENTS.md rule 3a), green.
   - The lane accepts with `--accept-judge "<reason>"`.
   - Lost 0. No fuel or byte growth: no artifact changes.
   - `ruff check` and `ruff format --check` are clean.
6. **The dry run after landing passes every job it runs.** The landing notes link it, and
   quote from its logs:
   - `build`'s printed record;
   - "Downloading artifacts by ID" and "Expected Digest" in `same-bytes` and in each
     `verify` leg (`ubuntu-24.04`, `windows-2025`, `macos-15`);
   - the check step's `OK` lines in those four jobs;
   - `same-bytes` downloading both rebuild legs by id.

   `attest`, `publish` and `pypi` are skipped. If Decision 4's or Decision 6's fallback is
   taken, the landing notes say which, and why.
7. **The first tag run after landing** records, in that release's notes (not this landing's):
   - `attest`'s, `publish`'s and `pypi`'s check steps passing;
   - their downloads by id;
   - Decision 9's comparison of the GitHub release's and PyPI's hashes with the build log's
     `SHA256SUMS`.

## Landing notes
