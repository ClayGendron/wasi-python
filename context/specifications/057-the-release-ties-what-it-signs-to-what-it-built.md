# 057 — The release ties what it signs to what it built

- **Status:** drafted 2026-10-18; revised against its pre-build review; awaiting the reviewer's
  confirmation. The review (`build/reviews-evidence/057-review/057-the-release-ties-what-it-signs-to-what-it-built-spec-2026-10-18.md`
  in the main tree, git-ignored; copied to `../reviews/` by the lane) said "ready once F1 to F5
  are written in". They are written in, and the Disposition below says where. Drafted on
  `spec/057-the-release-ties-what-it-signs-to-what-it-built` from main `d70690a`.
  - It must land before the next release after 0.1.0a4 (0.1.0a5, any other alpha, or 0.1.0
    final). The a4 security review's Confirmation set that bound.
  - It builds after spec 023 (matplotlib M1, in the build-class slot now) lands, and rebases
    onto main then.
- **Owner:** Clay Gendron
- **Kind:** build-class: the release workflow; a judge change.
  - It changes `.github/workflows/release.yml` in every job. The `rebuild` matrix becomes two
    jobs, `rebuild-linux-arm64` and `rebuild-linux-x86-64`.
  - It changes `scripts/00_download.sh`, at the end of its verify block.
  - It changes the judge: `tests/harness/scan.py` (three new scans; `rebuild_gate_errors`
    rewritten for two jobs), `tests/checks/test_rules.py`,
    `tests/checks/test_v1_5_rebuild_from_pins.py` and `tests/unit/test_scan.py`.
  - It changes `README.md` (*Releasing*) and `CHANGELOG.md`, and adds a one-line amendment
    note in specs 009 (Decision 1), 012 (Decision 7) and 040 (Decision 6).
  - It changes no artifact, no pin, no recipe that makes bytes, no `src/` file, and not the
    guest.
- **Depends on:** 056 (the a4 security review's findings; its Decision 6 names this
  follow-up, and its question 94 holds the owner's repository settings), landing now. Also
  on 004 (the release workflow), 009 (`attest` and its rules scan), 012 and 040 (the rebuilds
  and `same-bytes`, and their gate scan), and 028 (the `verify` job's install check). All are
  landed.
- **Research it stands on:** `../research/2026-10-18-the-release-ties-what-it-signs.md`. It
  holds what the pinned artifact actions do (READ at the pinned commits), the revised sketch
  of the workflow parsed (EXECUTED), the check step and the id guard run on tampered input
  (EXECUTED), and N1 before and after on all three hosts (EXECUTED). It also stands on the
  0.1.0a4 security review (`build/reviews-evidence/a4-security/0.1.0a4-security-review-2026-10-18.md`
  in the main tree, git-ignored): F4, N1, N3, and the Confirmation's "F4 and a4's PyPI
  publish".

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
  owner's: questions 94 and 95.

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
     is the stronger proof anyway. The review saw the upload's digest and each download's
     "Expected Digest" agree in the last dry run (EXECUTED there).
   - `SHA256SUMS` already lists the wheel and the `.tar.xz` (`release/version.py`,
     `write_assets`). So one hash covers both, the wheel's hash included.

2. **Every download is by one id, guarded, and fails on a digest mismatch.**
   - **The download.** Every `actions/download-artifact` step in the workflow takes
     `artifact-ids: ${{ needs.<job>.outputs.<name> }}`: one expression, and one id. Every
     step says `digest-mismatch: error`.
   - **What it never takes.** No download's `with:` holds `name`, `pattern`, `github-token`,
     `run-id`, `repository`, `merge-multiple` or `skip-decompress`. The middle three fetch
     from another run. The last two change where the bytes land, or whether they are
     unpacked.
   - **No other way to fetch an artifact.** The workflow never runs `gh run download`, never
     uses `actions/github-script`, and never calls the `/actions/artifacts` API.
   - **An empty id does not fail by itself (the review's F1, READ).** The action decides "by
     ids" with `!!inputs.artifactIds` (`download-artifact.ts`, line 61). An empty input is
     falsy. So the action falls through to its last branch and downloads every artifact in
     the run, each into `path/<name>/` (lines 166 and 194). "No valid artifact IDs provided"
     is thrown only for an input that is not empty but holds no id, such as `,`.
   - **So a guard step comes before every download.** It reads the id through `env:` and
     refuses anything but a non-empty decimal. In the five readers of `release-assets` it is
     this text, exactly:

     ```yaml
           - name: The build job handed on an artifact id
             # An empty artifact-ids makes download-artifact fetch every artifact of the run (spec 057).
             env:
               ASSETS_ID: ${{ needs.build.outputs.assets-id }}
             run: |
               case "$ASSETS_ID" in
                 "" | *[!0-9]*) echo "the build job handed on no artifact id"; exit 1 ;;
               esac
     ```

     `same-bytes` adds a second guard, "The rebuild jobs handed on artifact ids". It binds the
     four rebuild ids in `env:` and loops over them with the same `case`. The guard refuses
     an empty id, `12x` and `1,2`, and passes a decimal (EXECUTED, the memo).
   - **Why not `${{ … || 'missing' }}`.** That would make the action throw on a non-number.
     But it puts `||` in the job, which the existing "swallows a failure" rules of
     `release_attestation_errors` and `rebuild_gate_errors` refuse (READ, `scan.py`). The
     guard is plainer, and its message names the cause.
   - **Why one id per step.** The action only warns when some of several ids are missing
     (READ, lines 139-145). With one id, a missing artifact throws.
   - **Why `digest-mismatch` is written out.** The pinned v8.0.2 defaults to `error` (READ).
     Saying it means an action bump cannot loosen it quietly, and the judge can see it.
   - `pypi` gains `build` in its `needs` (`needs: [build, publish]`). A job can read only the
     outputs of the jobs it needs directly.

3. **One check step, the same in every reader, right after the download.** In `same-bytes`,
   `verify`, `attest`, `publish` and `pypi`, the step after the `release-assets` download is
   "These are the bytes the build job made". Its text is this, exactly:

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
     4. the folder holds nothing else, hidden files included.

     The last matters. `attest` signs `release-assets/*`, and `publish` uploads
     `release-assets/*`, so an extra file would be signed and published. A hidden file
     escapes that glob, and `find` still sees it.
   - **It fails closed.** It refuses each of these:
     - an empty or wrong hash;
     - a swapped wheel, also with `SHA256SUMS` rewritten to match it (F4's own move, caught
       at the anchor);
     - a missing file;
     - an extra file, or a hidden one;
     - a sub-folder.

     The memo and the review ran these cases on GNU, BSD and perl tools (EXECUTED).
   - **It also catches a download of everything.** If the guard were ever missing, a
     download of every artifact would fail here at `-c ../SHA256SUMS.sha256` (the review,
     EXECUTED). The guard is the first line, and this is the second.
   - **Where its scratch file goes.** `SHA256SUMS.sha256` is written beside `release-assets/`,
     never inside it. So the signed and published glob is unchanged.
   - **Why inline, not a script in the repository.** `attest` and `pypi` have no checkout. They
     should not gain one: spec 009 keeps the identity-token job free of the repository's code,
     setup-uv and uv. A composite action would need a checkout too. YAML anchors would make
     the judge resolve aliases, and it reads the workflow as text, with no YAML library (spec
     009, Decision 6). So the guard and the check are each written out once per reader. The
     judge requires the copies to be the same text, so they cannot drift.
   - **No `${{` in any `run:` script.** Values travel by `env:`. Our own jobs make these
     outputs. Still, the rule costs nothing, and it removes script injection as a class. The
     revised sketch has none (EXECUTED).
   - **The hash tool.** It is `sha256sum` where the runner has it: GNU coreutils on Ubuntu and
     in Git for Windows's bash, and `/sbin/sha256sum` on recent macOS. Otherwise it is perl's
     `shasum -a 256`, which the recipe already uses. Both read the `<hash>  <name>` format with
     `-c`. The memo ran macOS's two tools. The review added GNU coreutils 9.7 in Debian
     (EXECUTED). The `verify` job's Windows leg is evidenced by the dry run. It is not on the
     publish path.

4. **The two rebuilds become two jobs, each with its own outputs (the review's F2, the lane's
   ruling).**
   - **Why not a matrix.** A matrix shares one output namespace. Each leg's job reports
     whatever its steps write. A malicious input on one leg could start a background process
     that appends the other leg's output name to `GITHUB_OUTPUT`. The runner cleans up
     orphan processes only at job end (the review, EXECUTED in the dry run's log). The last
     leg to finish wins: "the last matrix job that runs will override the output value"
     (READ, GitHub's docs). In the last dry run, the x86_64 leg finished 1 h 48 min after the
     arm64 one (the review, EXECUTED). So one compromised leg could cast both votes of the
     same-bytes gate.
   - **The two jobs.** `rebuild-linux-arm64` runs on `ubuntu-24.04-arm` with
     `timeout-minutes: 120`. `rebuild-linux-x86-64` runs on `ubuntu-24.04` with 360.
     - Their steps are the same text, except the runner's name where the matrix put
       `${{ matrix.os }}`. That covers the display name and the upload names
       `rebuild-<runner>`, `rebuild-wheel-<runner>` and `rebuild-logs-<runner>`.
     - Each upload gets an id (`sums`, `wheel`). Each job's `outputs:` maps `sums-id` and
       `wheel-id` from them.
     - A job's outputs are its own: no other job can write them (INFERRED, as for `build`).
       So a compromised leg can at most delete or hide the other's artifact. That only fails
       the gate.
   - **`same-bytes`** needs `build`, `rebuild-linux-arm64` and `rebuild-linux-x86-64`. After
     its second guard, it downloads each job's `sums-id` into `rebuilds/<runner>` and each
     `wheel-id` into `rebuilt-wheels/<runner>`, by id. Its comparisons are unchanged.
   - **No fallback to downloads by name (the review's F3).** An empty rebuild output now
     fails at the guard, closed and with its cause named. The fix is to repair that job, not
     to go back to names.
   - **What two jobs cannot separate.** The x86_64 job compiles with the arm64 Linux
     wasi-sdk's clang under qemu (spec 040). So `wasi-sdk-33.0-arm64-linux.tar.gz` runs in
     both jobs. For that one input, a malicious tarball falls on both votes together, under
     any design. Every other host input is one job's alone. The pins (§4.2) are the defence
     for that tarball, as for every input. The README's *Releasing* says so.

5. **N1: the download step fails on a fetched name with no pin.** After its summary line,
   `scripts/00_download.sh` checks every name in `$NAMES` for a `<name>: OK` line in the
   verify file, with `set -f` around the loop. If any name has none, it prints
   `ERROR: no pin in downloads/SHA256SUMS for: <names>` and exits 1
   (`../research/2026-10-18-the-release-ties-what-it-signs/00_download.diff`).
   - It compares names, not counts. A repeated `get` of one name would make the counts differ
     with nothing wrong.
   - `set -f` keeps the unquoted loop from expanding a name as a pattern. No current name
     holds `*`, `?` or `[` (the review, READ), and `unpinned_fetch_errors` guards the same
     property.
   - `--ignore-missing` stays. `SHA256SUMS` lists other hosts' files, and they are rightly
     absent.
   - `pinned()` is unchanged. It re-checks every file at use.
   - Fixed, the script exits 1 naming the file on all three hosts. With every pin present it
     exits 0, the research input included (EXECUTED, the memo, with `set -f`).

6. **N3, the workflow's side.**
   - **`publish` names `environment: release`. `pypi` keeps `environment: pypi`.**
     - These are two environments, not one. PyPI's trusted publisher was set up against the
       `pypi` environment (`../decisions.md`, question 23), so renaming it would break
       publishing until the owner edits PyPI.
     - The two jobs also hold different powers: `contents: write` against `id-token: write`.
   - **What exists today (EXECUTED, `gh api repos/ClayGendron/wasi_python/environments`,
     2026-10-18).** `pypi` exists, with no protection rules and no deployment-branch policy.
     `release` does not exist.
   - **Before the owner protects `release`.** A job that names a missing environment creates it,
     with no protection rules (READ, GitHub's docs).
     - So the first tag run after landing creates `release` unprotected. It behaves exactly as
       today.
     - Dry runs never reach `publish`, so they never create it.
     - The owner can create `release` by hand before that tag, with one click. That removes
       the one unknown left before the tag (Decision 10).
     - Once the owner adds rules (questions 94 and 95), `publish` waits for them before it
       gets a runner. The workflow is the same either way.
   - **`enable-cache: false` on every `setup-uv` step** (five: `build`, both rebuild jobs,
     `verify`, `publish`).
     - Today's default, `auto`, already skips the cache on a tag push, and uses it on a manual
       dry run (READ).
     - With the cache off everywhere, the dry run takes the tag run's path, and nothing is
       restored from a cache that a branch's run could have written.
   - **Least privilege, stated per job.** The workflow-level `permissions:` becomes `{}`. Each
     job states its own:

     | job | permissions |
     |---|---|
     | `build`, `rebuild-linux-arm64`, `rebuild-linux-x86-64`, `verify` | `contents: read` (checkout) |
     | `same-bytes` | `{}`: no checkout and no API call. Its downloads use the runner's artifact service, not `GITHUB_TOKEN` (READ, the memo; INFERRED for the token) |
     | `attest` | `id-token: write`, `attestations: write`, `contents: read` (spec 009, unchanged) |
     | `publish` | `contents: write` |
     | `pypi` | `id-token: write` |

     If the dry run shows `same-bytes`' download refused under `{}`, its fallback is
     `contents: read`, recorded. That fallback grants a scope. It never changes how anything
     is fetched.

7. **Every action stays pinned by a full commit, and the judge now says so.**
   - Every `uses:` in today's workflow is a 40-hex commit with its release in a comment
     (EXECUTED, the memo's probe). No check enforced that.
   - A new scan covers every file in `.github/workflows/`. A `uses:` is either local (`./…`)
     or `owner/repo[/path]@<40 hex>`.
   - This specification bumps no action. A bump is its own change.
   - **What a text scan cannot see.** A 40-hex pin can name a commit that exists only in a
     fork (an "impostor commit"). So the README's *Releasing* gains one line for a later bump:
     check that the commit is the named release's tag
     (`gh api repos/<owner>/<repo>/git/ref/tags/<version>`).

8. **Recovery is unchanged.** The README says to re-run the failed jobs of the same run, never
   to push the tag again.
   - A re-run of failed jobs reuses the build job's outputs and the run's artifacts (INFERRED,
     not exercised).
   - If an output were lost, the reader stops at its guard ("the build job handed on no
     artifact id", or "a rebuild job handed on no artifact id"), or at the check ("handed on
     no SHA-256"). If an artifact were gone, the download throws ("None of the provided
     artifact IDs were found"). Each stops before signing or publishing.
   - The recovery is then to re-run all jobs. The build is reproducible, so it makes the same
     bytes. A second attestation of the same bytes is harmless.
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
      check step, the guard and the download script themselves, on scratch input (Design).
      Every new check is seen failing on `d70690a`'s tree, or is named as a guard that passes
      there.
    - **The dry run after landing** (a `workflow_dispatch`; the agent may dispatch dry runs,
      `../decisions.md`, 2026-10-18).
      - `same-bytes` and the three `verify` legs run the same guard and check steps, on that
        run's files, downloaded by id.
      - `attest`, `publish` and `pypi` are skipped, as every dry run skips them. Their copies of
        both steps are the same text (rules 9 and 10). Their wiring to `needs.build` is checked
        statically (rule 6).
      - **Why a pass in `same-bytes` carries over.** `same-bytes` runs with `permissions: {}`,
        which is a subset of every publish-path job's grants. The download uses the runner's
        runtime token, not `GITHUB_TOKEN`. So a by-id download that works in `same-bytes`
        works in `attest`, `publish` and `pypi` (INFERRED).
      - So the dry run exercises the exact text the publish path runs.
    - **The one unknown before the tag.** It is `environment: release` being created on first
      use. If that failed, `attest` would already have signed (permanent) with no release
      made, and the recovery is to re-run `publish`. That is acceptable. The owner can remove
      the unknown by creating `release` beforehand (Decision 6).
    - **The first tag run after landing.** Its `attest`, `publish` and `pypi` logs (the guard,
      "Downloading artifacts by ID", the check's `OK` lines) are recorded in that release's
      notes, beside Decision 9's comparison.

11. **Its place in the queue.** It is build-class (`scripts/`, the release workflow), so it
    builds as the only build-class change in flight (§5.7).
    - Spec 023 holds that slot now. This one builds after 023 lands, and rebases then. The
      next release after a4 waits on it. Its build and review are small (no artifact
      rebuild; the frozen set judges it).
    - If 023, or any later specification, edits the workflow first, this one rebases over it.
      Any download it adds must be by id and guarded (rules 4 and 10).
    - The judge change is accepted with `--accept-judge`.

## Intent

Every job that checks, signs or publishes the release proves, before it acts, that its files
are the bytes the build job made. It does this by the artifact's id, guarded against an empty
one, and by every file's SHA-256, and it fails closed otherwise. The two rebuild votes come
from two jobs, each speaking only for itself. The download step refuses a fetched file with
no pin. The publish jobs name their environments, run with no cache, and hold only the
permissions they use.

## Design

```
.github/workflows/release.yml
  permissions: {}            workflow level; each job states its own (Decision 6)
  build                      outputs assets-id, sums-sha256; steps sums, assets (upload), the printed record
  rebuild-linux-arm64        ubuntu-24.04-arm, 120 min; uploads id sums, wheel; outputs sums-id, wheel-id
  rebuild-linux-x86-64       ubuntu-24.04, 360 min; the same steps, its runner's names
  same-bytes                 guard; release-assets by id; check; rebuild guard; 4 downloads by id
  verify                     guard; download by id; check; cache off
  attest                     guard; download by id; check; then attest, then verify (spec 009 order kept)
  publish                    environment: release; guard; download by id; check; cache off
  pypi                       needs [build, publish]; environment: pypi; guard; download by id; check
scripts/00_download.sh       the name check after the summary, under set -f (Decision 5)
tests/harness/scan.py
  release_binding_errors(text)          rules 1-14 below, one line per breach
  action_pin_errors(text)               Decision 7
  unpinned_fetch_errors(script, pins)   every get/research name is in SHA256SUMS
  workflow_step_script(text, job, name) a step's run: block, as text; raises if it is absent
  rebuild_gate_errors                   rewritten for two jobs (below)
tests/checks/test_rules.py              4 checks (two of them parametrized: x9 and x4)
tests/checks/test_v1_5_rebuild_from_pins.py  2 checks (one parametrized x3)
tests/unit/test_scan.py                 a good workflow, and one bad variant per rule
README.md (Releasing), CHANGELOG.md     the next version's Security entry: F4, N1, N3
specs 009, 012 and 040                  one amendment line each, pointing here
```

The revised sketch of the workflow is in the memo's evidence (`release.yml.diff`). It is a
sketch, not applied. It parses, and the memo's probe finds nothing in it, against 23 problems
in today's workflow (EXECUTED). Three mutations of it are each caught: a guard removed, the
two rebuild jobs made different, and a `${{` put in a `run:` (EXECUTED).

**`release_binding_errors`.** It works on the workflow without comments, and gives one line
per breach. It reads a download's inputs from that step's `with:` block, never from the
step's display `- name:`. Its rules:

1. `build`'s `outputs:` maps `assets-id` from `steps.<id>.outputs.artifact-id`, where `<id>`
   is an upload step with `name: release-assets`.
2. `build`'s `outputs:` maps `sums-sha256` from a step whose `run:` hashes
   `release-assets/SHA256SUMS`. That step comes before the `release-assets` upload.
3. After that upload, a `build` step binds the upload's `artifact-id` and `artifact-digest` in
   `env:`, and `cat`s `release-assets/SHA256SUMS`.
4. Every `actions/download-artifact` step's `with:` has `artifact-ids:` with one
   `${{ needs.<job>.outputs.<name> }}`. It has none of `name`, `pattern`, `github-token`,
   `run-id`, `repository`, `merge-multiple` or `skip-decompress`. And the workflow holds no
   `gh run download`, no `actions/github-script`, and no `/actions/artifacts` call.
5. Every `actions/download-artifact` step has `digest-mismatch: error`.
6. Every `needs.<job>.outputs.<name>` that a job reads names a job in its `needs:`, and an
   output that job's `outputs:` defines.
7. Some jobs must download `needs.build.outputs.assets-id` into `path: release-assets`:
   every job that reads that output, and every job granted `contents: write` or
   `id-token: write`.
8. In each such job, the step right after that download is the check step. It binds
   `SUMS_SHA256: ${{ needs.build.outputs.sums-sha256 }}`. Its `run:` checks `SHA256SUMS.sha256`
   and `-c SHA256SUMS`, and compares `find . -mindepth 1` with the listed names.
9. The check steps are the same text.
10. Before every download, an earlier step in the same job binds that download's
    `artifact-ids` expression in `env:`. Its `run:` refuses `"" | *[!0-9]*)`. The guards
    before the `release-assets` downloads are the same text.
11. No `run:` script contains `${{`.
12. `publish` has `environment: release`, and `pypi` has `environment: pypi`.
13. Every `astral-sh/setup-uv` step has `enable-cache: false`.
14. The workflow-level `permissions:` is `{}`, and each job's permissions are exactly its row
    in Decision 6's table.

**`rebuild_gate_errors`, rewritten for two jobs.** It keeps the intent of specs 012 and 040.
It holds a table of the two jobs: `rebuild-linux-arm64` on `ubuntu-24.04-arm` for 120
minutes, and `rebuild-linux-x86-64` on `ubuntu-24.04` for 360. Its rules:

- Both jobs exist, with their table's `runs-on` and `timeout-minutes`.
- The two jobs are the same text once their runners' names are replaced by one placeholder,
  and their `name:`, `runs-on:` and `timeout-minutes:` lines are set aside. The longer name,
  `ubuntu-24.04-arm`, is replaced first.
- Each job prints `nproc` and the `binfmt_misc` entries, and runs `scripts/build.sh`.
- Each job uploads `build/artifacts/SHA256SUMS` as `rebuild-<runner>` (`id: sums`) and the
  wheel as `rebuild-wheel-<runner>` (`id: wheel`). Its `outputs:` maps `sums-id` and
  `wheel-id` from them.
- Neither rebuild job, nor `same-bytes`, has a job-level `if:` or `continue-on-error:`, or
  permissions beyond `contents: read`.
- `same-bytes` needs `build` and both rebuild jobs.
- `same-bytes` downloads each job's `sums-id` into `rebuilds/<runner>` and each job's
  `wheel-id` into `rebuilt-wheels/<runner>`.
- `same-bytes` keeps its `cmp` of a rebuild's `SHA256SUMS` with the set's, and both of its
  loops run over both runners.
- No step of `same-bytes` swallows a failure (`||` or `set +e`).
- `attest` and `publish` need `same-bytes`.

**The behaviour checks.**

- **`test_the_release_check_refuses_other_bytes[case]`.**
  - It takes the check step's script from `attest` with `workflow_step_script`. That helper
    raises when the step is absent, so every case fails on a workflow without it. An empty
    script would exit 0, and the "own files" case would pass falsely.
  - It runs the script in `bash`, in a temporary folder with a three-file `release-assets/`:
    a fake wheel, a fake `.tar.xz`, and their `SHA256SUMS`.
  - The case `the build's own files` must exit 0.
  - Eight cases must exit non-zero: `SUMS_SHA256` empty; `SUMS_SHA256` another hash; the
    wheel's bytes changed; the wheel swapped with `SHA256SUMS` rewritten to match; the
    `.tar.xz` removed; an extra file; a hidden file; a sub-folder.
- **`test_the_id_guard_refuses_a_missing_id[case]`.** It takes the guard's script from
  `attest`, again raising when it is absent. It runs it in `bash`. `ASSETS_ID` empty, `12x`
  and `1,2` must exit non-zero, and `123456789` must exit 0.
- **`test_download_step_fails_on_a_fetched_file_with_no_pin[host]`.** It copies
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
  see them (N3). §7 keeps the agent from changing them.
- **A read-back after `gh release create` or PyPI's upload.** The bytes leave the last check
  for the services' own storage. Decision 9 records the comparison per release instead.
- **Rehearsing `attest`, `publish` or `pypi` in a dry run.** A signature is permanent in
  Sigstore's public log (spec 009, Decision 5). Their steps are the dry run's steps by text
  (rules 9 and 10).
- **Bumping any action**, or changing `attest`'s rules (spec 009). Decision 7.
- **Proving the build job itself honest.** That is what `same-bytes` and the two rebuilds are
  for (specs 012 and 040). This specification ties every later job to the build's output,
  and keeps the two votes apart. It does not re-judge the build.
- **The arm64 Linux wasi-sdk shared by both rebuild jobs.** It is spec 040's design
  (Decision 4 above). The pins defend it.

## Acceptance criteria

1. **Seen failing first, on `d70690a`'s tree**, before any change, each recorded with its
   output:
   - `test_the_release_signs_and_publishes_what_build_made` fails. Its report names at least
     rules 1, 2, 3, 4 (nine downloads by name), 5, 7, 8, 10, 12, 13 and 14.
   - All nine `test_the_release_check_refuses_other_bytes` cases fail, and all four
     `test_the_id_guard_refuses_a_missing_id` cases fail. Each raises because its step is
     absent.
   - All three `test_download_step_fails_on_a_fetched_file_with_no_pin` cases fail, because
     the script exits 0. The memo already shows this (EXECUTED).
   - The rewritten `test_release_workflow_rebuilds_on_two_more_hosts` fails: "no
     rebuild-linux-arm64 job", "no rebuild-linux-x86-64 job".
   - Two new checks pass on that tree, and the landing notes say so:
     `test_every_action_is_pinned_by_commit` and `test_every_fetched_file_is_pinned`. They are
     guards on properties that already hold. Each is seen failing on its unit test's bad
     variant instead.
2. **19 new checks pass after the change:**
   - `test_rules.py`: 1 binding check, 1 pin check, 9 check-step cases, 4 guard cases;
   - `test_v1_5_rebuild_from_pins.py`: 3 download cases, 1 fetched-is-pinned check.

   The rewritten `test_release_workflow_rebuilds_on_two_more_hosts` passes, and so does the
   unchanged `test_releases_attest_and_verify_their_assets`.
3. **The unit tests.**
   - `test_scan.py` feeds a good workflow to `release_binding_errors`, and it passes. Then
     one bad variant per rule (14), each yielding exactly its own error.
   - Rule 4 also gets one variant per refused input (`name`, `pattern`, `github-token`,
     `run-id`, `repository`, `merge-multiple`, `skip-decompress`), and one each for
     `gh run download` and `actions/github-script`.
   - A further variant gives a step the display name `release-assets`, and rule 4 must still
     read `with:`.
   - `action_pin_errors` passes a good workflow. A tag (`@v4`) and a short commit each yield
     their error.
   - `unpinned_fetch_errors` passes a good script, and names an unpinned `get`.
   - The rewritten `rebuild_gate_errors` passes a good workflow, and each of its rules has a
     bad variant yielding exactly its own error.
4. **The workflow parses** with PyYAML in a throwaway environment. The memo's
   `probe_workflow.py` reports 0 problems on it, against 23 on `d70690a`.
5. **The judge.**
   - The fast tier first, then the full `uv run pytest` once (AGENTS.md rule 3a), green.
   - The lane accepts with `--accept-judge "<reason>"`.
   - Lost 0. No fuel or byte growth: no artifact changes.
   - `ruff check` and `ruff format --check` are clean.
6. **The dry run after landing passes every job it runs.** The landing notes link it, and
   quote from its logs:
   - `build`'s printed record;
   - the guards passing, then "Downloading artifacts by ID" and "Expected Digest", in
     `same-bytes` and in each `verify` leg (`ubuntu-24.04`, `windows-2025`, `macos-15`);
   - the check step's `OK` lines in those four jobs;
   - `same-bytes` downloading from both rebuild jobs by id.

   `attest`, `publish` and `pypi` are skipped. If Decision 6's `same-bytes` fallback is taken,
   the landing notes say so, and why.
7. **The first tag run after landing** records, in that release's notes (not this landing's):
   - `attest`'s, `publish`'s and `pypi`'s guard and check steps passing;
   - their downloads by id;
   - Decision 9's comparison of the GitHub release's and PyPI's hashes with the build log's
     `SHA256SUMS`.

## Disposition of the pre-build review (2026-10-18)

The review: `build/reviews-evidence/057-review/057-the-release-ties-what-it-signs-to-what-it-built-spec-2026-10-18.md`
(main tree, git-ignored). Its verdict was "ready once F1 to F5 are written in". The same
text is at `build/reviews-evidence/057-review/disposition.md`.

- **F1 (medium): written in.** An empty `artifact-ids` downloads every artifact of the run.
  The memo's account of an id lookup is corrected ("How it looks an id up"), and so are
  Decisions 4 and 8.
  - Decision 2 adds a guard step before every download, requiring a non-empty decimal. It is
    the same text in the five `release-assets` readers, and `same-bytes` has a second guard
    for the four rebuild ids.
  - It is not written as `|| 'missing'`.
  - Rule 10 makes it a judge rule, with a unit variant without the guard. Four behaviour
    cases run the guard itself.
- **F2 (medium): written in, option (a), the lane's ruling.** Decision 4: the matrix becomes
  `rebuild-linux-arm64` and `rebuild-linux-x86-64`, each with its own `sums-id` and
  `wheel-id`. The rewritten `rebuild_gate_errors` requires their steps to be the same text but
  for the runner. Decision 4 and Scope also say that the arm64 Linux wasi-sdk tarball runs on
  both legs.
- **F3 (low): written in.** The fallback to downloads by name is gone (Decision 4). An empty
  rebuild output fails at the guard.
- **F4 (low): written in.** Question 95 is restated as facts. The agent's `gh` is the owner's
  account, with the `repo` and `workflow` scopes, so the agent can approve deployments and
  edit environment rules as the owner. With "Prevent self-review" and the owner as sole
  reviewer, no run could be approved. `pypi` exists today with no protection and no branch
  policy (re-checked 2026-10-18, EXECUTED). The recommendation is still (a). It now says that
  a tag rule does not constrain the agent, which can push a `v*` tag, and what would make a
  reviewer a real gate.
- **F5 (low): written in.**
  - Rules 7 and 8 now cover every job that reads `assets-id`, or holds `contents: write` or
    `id-token: write`.
  - Rule 4 refuses `github-token`, `run-id`, `repository`, `merge-multiple` and
    `skip-decompress`, and any `gh run download`, `actions/github-script` or
    `/actions/artifacts` call. It reads `with:`, not the display name.
  - Rule 11 (was 10) is now "no `${{` in any `run:`".
  - The behaviour cases add "wheel swapped and `SHA256SUMS` rewritten" and "a hidden file"
    (EXECUTED, the memo).
  - Acceptance 1's cases fail when the step is absent, because `workflow_step_script` raises.
- **F6 (informational): answered in Decision 10.** A by-id download that works in
  `same-bytes` (`permissions: {}`) works in every publish-path job. The one unknown before the
  tag is `environment: release` being created on first use. Decision 6 says the owner can
  create it beforehand.
- **F7 (notes): taken.**
  - Decision 7 names impostor commits, and adds the README line for later bumps.
  - N1's loop runs under `set -f` (Decision 5; the memo re-ran it on three hosts).

The acceptance counts are restated: 19 new checks, against 13 before the review.

## Landing notes
