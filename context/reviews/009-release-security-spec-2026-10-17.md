# Review of 009 — Release security: provenance and a disclosure policy (the specification, before build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I read the constitution,
  `AGENTS.md`, the reviews README, the 008 pre-build review (for its format), the specification,
  the principal engineer's memo (section 2 "Supply chain", "Missing" 3 and 4, direction 7),
  spec 004, and the code and checks the specification touches or describes. I did not rely on
  the author's summary.
- **Reviewed:** `context/specifications/009-release-security.md` (draft, 82 lines, untracked),
  against the working tree at `f6b67ac`.
- **Ran (EXECUTED, darwin-arm64, gh 2.96.0, wasmtime-py 49, `build/artifacts/` read only).**
  - Scripts and outputs are under
    `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/review-009/`.
    Nothing under `build/` was written. No tracked file was edited.
  - `gh api` on `actions/attest-build-provenance` and `actions/attest`: tags, releases, the
    pinned commit, its `action.yml`, and `src/main.ts`, `src/attest.ts`, `src/subject.ts` of
    the inner action at the commit the wrapper pins.
  - `gh api` on this repository: visibility, private vulnerability reporting, artifact
    retention, the `v0.1.0a1` release and its tag run.
  - `gh attestation verify` on this project's `v0.1.0a1` `SHA256SUMS`, and on an attested
    public asset (`cli/cli` v2.96.0, `gh_2.96.0_linux_arm64.tar.gz`) under several policies,
    with and without a login.
  - `p1_sleep.py` and `p2_sleep.py`: `wasi_python.run` at HEAD, `cache_dir=False`, a fresh
    `mkdtemp` root, `deadline_s=1.0`.
  - `harness.scan.spec_shape_errors` and `open_question_hits` on the specification: both empty.
  - I did not run `uv run pytest`. It writes under `build/`, which this review must not touch.
    The scoreboard is the build review's job.

## What holds (the questions I was asked to look hard at)

- **The pin is the v4.2.2 commit.**
  - EXECUTED: `gh api repos/actions/attest-build-provenance/git/ref/tags/v4.2.2` gives a
    lightweight tag on commit `4d101475d8b20a2381f78447822ac1eab6504dd8`.
  - EXECUTED: the release was published 2026-08-06T19:59:04Z, and is not a pre-release. The
    commit's signature is verified. The moving `v4` tag points at the same commit.
  - READ: the commit's `action.yml` is a composite. Its one step is
    `actions/attest@508db95dd578ae2727ebd6217d5ba78e4fbda05d # v4.2.1`. EXECUTED: that is the
    `v4.2.1` tag of `actions/attest`, published 2026-07-29. So pinning the wrapper by commit
    pins the code that runs, transitively.
- **It runs on the publish job as it is.**
  - READ: the inner action is `using: node24`. The publish job runs on `ubuntu-24.04`, a
    GitHub-hosted image (EXECUTED: the `v0.1.0a1` tag run's publish job ran there).
  - READ (`subject.ts:119-151`): `subject-path` is expanded with `@actions/glob`. Only files
    become subjects. No match is an error ("Could not find subject"). Three files make one
    attestation with three subjects (README of `actions/attest`).
- **The two permissions are enough.**
  - READ (`main.ts`): the action fails at once without `id-token: write`
    ("missing \"id-token\" permission").
  - READ: `attestations: write` persists the attestation.
  - READ (`attest.ts:45-73`): `artifact-metadata: write` is needed only for a storage record.
    That path runs only with `push-to-registry: true` and one subject, and returns early for a
    repository owned by a user. So it is not needed here.
  - READ (`release.yml:149-150`): job-level `permissions` replace the workflow's. The job keeps
    `contents: write`, which includes the read that `actions/checkout` needs. Nothing else in
    the job needs another scope (EXECUTED: the `v0.1.0a1` publish succeeded with
    `contents: write` alone).
- **A public repository on a personal account can attest.**
  - EXECUTED: the repository is `public`, owner type `User`.
  - READ (README of `actions/attest`): "Artifact attestations are available in public
    repositories for all current GitHub plans."
- **A failed attestation stops the release, before it exists.**
  - READ (`main.ts:148-150`): any error calls `core.setFailed`. The step has no
    `continue-on-error`, so the job stops. `gh release create` comes after, so it never runs.
  - I think that is the right behaviour: a release whose README promises provenance should not
    ship without it. The specification should say it (finding 4).
- **`gh attestation verify` works on any file.**
  - READ (`gh attestation verify --help`): it takes a file path, hashes it, and looks up
    attestations for that digest. The asset's type does not matter.
  - EXECUTED: on `cli/cli`'s tarball, `--repo cli/cli` exits 0. Its one attestation lists 21
    subjects. So a wheel, a `.tar.xz` and `SHA256SUMS` in one attestation each verify alone.
  - EXECUTED: on this project's `v0.1.0a1` `SHA256SUMS` it exits 1 with HTTP 404. No asset of
    the current release is attested (finding 3).
- **The specification's shape is sound.** EXECUTED: `spec_shape_errors` and `open_question_hits`
  return `[]`.

## Acceptance criteria against evidence

1. *Two rules checks, a unit test that sees the scan fail, green with `--accept-judge`.*
   Checkable once the checks are pinned down (finding 5). As written, "the workflow scan" has no
   parser named, and the YAML library it would need is not a dependency.
2. *A dry run passes every job (it does not reach `publish`).* Checkable. It exercises none of
   the new step. That is the gap finding 4 closes.
3. *The landing notes say the attestation is first exercised by the next release.* Checkable.
   Decision 5's companion promise, that the next release's notes record the result, cannot be
   kept as worded (finding 10).

## Findings, most severe first

1. **Decision 3 calls a guest that hangs the embedder past its deadline a vulnerability. The
   runner has that hole today** (`009:29-32`; `runner.py` `_epoch_ticker`). High.
   - **What I saw (EXECUTED, `p2_sleep.py`, after a warm-up compile).** With `deadline_s=1.0`:

     | program | exit code | trapped | elapsed |
     |---|---|---|---|
     | `while True: pass` | None | deadline | 1.0 s |
     | `time.sleep(5)` | None | deadline | 5.0 s |
     | `time.sleep(15)` | None | deadline | 15.0 s |

     The elapsed column is a probe fact, not a check.
   - **Cause (INFERRED).** The deadline is epoch interruption. wasmtime checks the epoch in guest
     code only. A guest's `time.sleep` blocks inside the WASI `poll_oneoff` host call. The trap
     fires only when the call returns. So under the 60 s default, `time.sleep(10**9)` holds
     `run` for decades.
   - **Why it matters here.** Decision 3 lists both "a guest … hanging the embedder's process
     through … the runner" and "a defeat of a default limit". This is both. Publishing the
     policy while the current release fails its own first lines invites a report on day one,
     or worse, an embedder trusting the 60 s default.
   - **The judge does not see it.** READ: `test_a_run_has_a_default_deadline`
     (`test_v1_2_hostile_guest.py:183-190`) uses a busy loop only. The README's "Not protected"
     list says "timing (the clock is real…)", which is about side channels, not this.
   - **Fix.** Before `SECURITY.md` lands, do one of these, and say which:
     - (a) close it in its own specification (for example, the runner's `poll_oneoff` bounded
       by the time left), with a check that counts rather than times (§4.9). One way: shadow the
       call and assert the timeout the host was asked for;
     - (b) add it to the README's "Not protected" list with its reason, until (a) lands.
   - **A disclosure note.** This review is a file in a public repository once committed. The
     impact is a blocked call, not an escape, but the owner may want (a) or (b) to land first.

2. **The private reporting route does not exist yet, and the fallback has no private channel
   to hand over** (`009:36-38`). Medium-high.
   - EXECUTED: `gh api repos/ClayGendron/wasi_python/private-vulnerability-reporting` returns
     `{"enabled":false}`. So the "Report a vulnerability" button is not shown today. Question 10
     is still open.
   - The fallback is a public issue that "asks for a contact". GitHub has no direct messages.
     The specification does not say what contact the owner then gives. So a reporter waits on
     an answer nobody has decided.
   - The rules check cannot see a repository setting offline, so it would pass with a dead route.
   - **Fix (pick one, and say why):**
     - (a) make question 10's answer, with the setting on, a precondition of landing
       `SECURITY.md` (an acceptance criterion, checked by `gh api` and recorded);
     - (b) make the fallback concrete: the reporter opens an issue titled, say, "security
       contact" with no details; the maintainer opens a draft repository security advisory and
       adds the reporter to it. INFERRED from GitHub's documented advisory collaborators; it
       works without the setting;
     - (c) the owner names a private address. That is the owner's decision.

3. **The verification command is too loose, is in the wrong section, and needs a login. The
   current release cannot pass it** (`009:24-27`). Medium.
   - **Loose.** READ (`--help`): `--repo` accepts an attestation signed by any workflow of the
     repository, at any ref. So a future test workflow, or a dry-run attestation (finding 4),
     would satisfy it.
   - EXECUTED on `cli/cli`: a wrong `--signer-workflow` path exits 1. A wrong `--source-ref`
     exits 1 ("expected SourceRepositoryRef to be refs/tags/v2.96.0, got refs/heads/trunk").
     So both flags bind as documented.
   - **Suggested command:**
     `gh attestation verify <asset> --repo ClayGendron/wasi_python --signer-workflow
     ClayGendron/wasi_python/.github/workflows/release.yml --source-ref refs/tags/v<version>
     --deny-self-hosted-runners`. It proves the asset came from the release workflow, run for
     that tag.
   - **Login.** EXECUTED: with no token and an empty config, `gh attestation verify` exits 4
     ("please run: gh auth login"). So "a user without `gh`" is also a user without a GitHub
     account. Option: attach the action's `bundle-path` output as a fourth release asset.
     EXECUTED: `--bundle <file>` verifies with no login (exit 0 on `cli/cli`'s bundle).
   - **The current release.** EXECUTED: `v0.1.0a1`'s `SHA256SUMS` gives 404, exit 1. The
     README must say which version is the first attested, or users read a failure as tampering.
   - **Placement.** "Releasing" is the maintainer's section. A user reads the release page and
     "Running it". Put the command in the release notes (`release/version.py notes`, which adds
     that file to the Kind line) or a short "Verifying a download" section.
   - It works for all three asset types (see "What holds").

4. **Nothing checks the attestation before the release is created, and a failure's recovery is
   not written down** (`009:17-23`, `009:47-50`). Medium.
   - **The risk.** The first time the step runs is a real tag. A wrong permission or a Sigstore
     outage fails the job. READ: the tag is then pushed with no release.
   - **Recovery exists but is unwritten.** EXECUTED: the repository keeps artifacts 90 days. So
     "Re-run failed jobs" re-runs `publish` on the same bytes (INFERRED from GitHub's re-run
     behaviour). Say this in the README's "Releasing" section and in Decision 1, and say that
     blocking the release is intended.
   - **Fix: verify before creating.** Add a step after the attestation and before
     `gh release create`. For each file in `release-assets/`, run the command of finding 3,
     with `GH_TOKEN`, `--repo "$GITHUB_REPOSITORY"` and `--source-ref "$GITHUB_REF"`. This
     proves what a user will check, through the same API, before anything is public. `gh` is on
     the runner image (INFERRED from the existing `gh release create`).
   - **A dry-run exercise has a cost.** READ (`main.ts:59-66`): a public repository signs with
     the public-good Sigstore instance. Every attestation is a permanent entry in the public
     Rekor log, and in the repository's attestation list. A dry-run attestation would be a true
     statement about unreleased bytes signed at `refs/heads/main`. With finding 3's
     `--source-ref`, it never verifies as a release.
     - My advice: do not attest in dry runs by default. The static rules check, the
       verify-before-create step and the written recovery make the first real run fail safe.
     - If the owner wants one live rehearsal, a `workflow_dispatch`-only job that attests the
       dry run's assets is the honest form. It is the owner's call, because it writes to a
       public, permanent log (the spirit of §7 on publishing).

5. **The rules checks are not specified precisely enough to build or to see fail** (`009:41-46`).
   Medium.
   - **No parser.** READ: `pyproject.toml` has no YAML library, and §4.13 needs a written reason
     to add one. The scan must be text-based, like `test_release_workflow_runs_the_zero_patch_check`
     (`test_v1_5_rebuild_from_pins.py:72-81`). Say so.
   - **Name the scanner and its contract,** following `tests/harness/scan.py`: a pure function,
     for example `scan.release_attestation_errors(text: str) -> list[str]`, reported through
     `scan.report`.
   - **Say exactly what it asserts:**
     - the file is `.github/workflows/release.yml`;
     - the `publish` job's own `permissions:` block has `id-token: write` and
       `attestations: write` (job-level replaces workflow-level);
     - a step `uses: actions/attest-build-provenance@` (or `actions/attest@`, see finding 8)
       followed by 40 lower-case hex;
     - its `subject-path` is the same glob `gh release create` uploads (`release-assets/*`), so
       every uploaded file is attested;
     - the step has no `if:` and no `continue-on-error`;
     - it comes before the verify step (finding 4), which comes before `gh release create`.
   - **The unit test.** The pattern in `tests/unit/test_scan.py` is "firing on a bad input and
     quiet on a good one". Feed one good workflow, quiet, and one bad variant per rule: no step,
     `@v4`, after the create, a missing permission, `continue-on-error: true`.
   - **The security check.** Name the strings:
     - `SECURITY.md` at the repository root;
     - it contains "Report a vulnerability" and a link to `README.md#safety`;
     - `README.md` still has a `## Safety` heading, so the link is alive.
   - **The rules area.** Neither check is a constitution rule yet (question 5 is open). A
     sentence saying they guard a specification, as `test_the_version_is_released_by_the_book`
     does for spec 004, would keep the rules module's docstring true.
   - **Optional, cheap.** A general check that every `uses:` in every workflow is pinned by
     40-hex. Today only a comment says so (`release.yml:6`).

6. **Decision 3's "counts" list is a second copy of the README's "Enforced" list, and it is
   broader in places** (`009:29-35`). Low-medium.
   - "A guest's planted code running in a later call" is wider than the README's "never runs at
     start-up or on import" (`README.md:214`). The "Not protected" list keeps pdb's `.pdbrc`, a
     script the caller names from a reused root, and the plain reactor's `sys.prefix` after a
     planted `pyvenv.cfg` (`README.md:243-247`).
   - "Crashing … the embedder's process" collides with the host's file descriptors, which are
     not protected (`README.md:241-243`).
   - **Fix.** Define a vulnerability as "a breach of anything the README's 'Safety' section
     lists as enforced, with the defaults in force", plus the release-asset clause. Say the
     "Not protected" list wins on any conflict. Both lists then stay in one place, as Decision 3
     already intends for the second.
   - **"Does not match its pins"** has no meaning for a release asset. Assets are outputs.
     Either drop it, or say "differs from a rebuild of the tag on the build's host (arm64
     macOS)". The Linux rebuild is still a known gap.
   - **Missing routes.** Say where a hole in a component goes: CPython, numpy, pandas, zlib and
     wasmtime upstream, with this project shipping a new set. Say that the embedder's own host
     function is the embedder's. The runner's wall rests on wasmtime (`wasmtime>=49,<50`), so
     wasmtime's advisories apply to users.

7. **"Through GitHub's Sigstore instance" is wrong for this repository** (`009:21`). Low.
   - READ (`main.ts:59-66`): a public repository uses the public-good instance. Only private or
     internal repositories use GitHub's.
   - It matters for finding 4: every attestation becomes a permanent public log entry.
   - §4.10: the claim is unlabelled; it should carry READ and the source.

8. **The wrapper is the older form of the action** (`009:19`). Low.
   - READ (release notes of v4.0.0 to v4.2.2): "As of version 4, `actions/attest-build-provenance`
     is simply a wrapper on top of `actions/attest` … new implementations should use
     `actions/attest` instead."
   - EXECUTED: `actions/attest` `v4.2.2` is commit `1e69f48acb82d1966a394da916b4c1698aa569d6`,
     published 2026-08-04, older than two weeks. Its change from 4.2.1 is dependency bumps
     (`@sigstore/oci`, used only for registry pushes).
   - Either pin is correct. Pinning `actions/attest` directly removes one indirection and
     follows upstream's advice. Its default mode with no predicate is SLSA provenance (READ).
     Whichever is chosen, the rules check must match it.

9. **The job that mints the identity token also holds `contents: write` and runs uv** (`009:17-18`).
   Low.
   - READ (`release.yml:151-171`): `publish` runs `setup-uv`, a uv-managed Python, and
     `release/version.py notes`. With `id-token: write`, any of it can mint a token for this
     workflow.
   - INFERRED: such a token also satisfies a PyPI trusted publisher registered without the
     `pypi` environment.
   - **Fix (optional).** A separate `attest` job shaped like the `pypi` job: download, attest,
     verify, with `id-token: write`, `attestations: write`, `contents: read`. `publish` then
     `needs` it and keeps `contents: write` only. When the owner registers the PyPI publisher,
     name the `pypi` environment.

10. **"The next release's notes record its result" cannot happen as worded** (`009:48-50`). Low.
    - READ (`release.yml:166-171`): the notes are rendered by `version.py notes` before
      `gh release create`. They cannot hold a verification that runs after.
    - **Fix.** Record the result as an amendment to 009's landing notes, or in the release memo.
      The verify-before-create step of finding 4 logs it in the run as well. "A clean machine"
      needs a `gh` login, or the bundle (finding 3).

## Constitution checks

- **§4.2 (pins) holds.** The action is pinned by commit, like every other action. Its inner
  action is pinned by commit inside it. Sigstore's trust root, Fulcio and Rekor are services the
  step talks to. They are not build inputs and do not change a byte.
- **§4.4 and §4.5 hold.** Nothing touches the guest's imports. Nothing names an embedder.
- **§4.6 holds.** The artifact set is unchanged. A bundle as a fourth release asset (finding 3)
  would change the release's files, not the artifact set.
- **§4.9 holds as specified.** My timings are probe facts. A check for finding 1 must count,
  not time.
- **§4.10:** Decision 1's release date is right (EXECUTED). Its "GitHub's Sigstore instance" is
  wrong and unlabelled (finding 7).
- **§4.13:** the workflow scan must not pull in a YAML library without a written reason
  (finding 5).
- **§5.2 (no open questions):** the reporting route rests on question 10 (finding 2). The
  specification decides a fallback, but one that leads nowhere.
- **§5.6:** a change to the release workflow is reviewed before it is built. This is that review.
- **§7:** nothing tripped. A dry-run attestation, if ever added, writes to a public permanent
  log. Treat it as the owner's call (finding 4).

## Disposition (filled in by the author, then confirmed by the reviewer)

1. **Answered by moving `SECURITY.md` out.** It waits on spec 010 (which fixes the sleep defect
   the review found) so the policy it publishes is true. Meanwhile the README's "Not protected"
   list names the sleep gap (commit 47c9fdc).
2. **Answered by moving `SECURITY.md` out.** It waits on question 10 (private vulnerability
   reporting).
3. **Fixed.** Decision 2 uses `--signer-workflow`, `--source-ref` and
   `--deny-self-hosted-runners`; Decision 3 states the login, the bundle route, the first
   attested release, and puts the command in a user-facing README section and in every release's
   notes.
4. **Fixed.** The `attest` job verifies each asset before `publish` can run; Decision 4 writes
   the recovery down; Decision 5 keeps dry runs from signing to the public log.
5. **Fixed.** Decision 6 names the text scan, each rule, the check, and a unit test with one bad
   variant per rule.
6. **Answered by moving `SECURITY.md` out.**
7. **Fixed.** "the public-good Sigstore instance".
8. **Fixed.** The pin is `actions/attest@1e69f48acb82d1966a394da916b4c1698aa569d6` (v4.2.2,
   2026-08-04, EXECUTED by the author with `gh api`).
9. **Fixed.** A separate `attest` job with only `id-token: write`, `attestations: write`,
   `contents: read`.
10. **Fixed.** Decision 5 records the first real run's result in the landing notes of the
    specification that cuts that release, not in its notes.

## Verdict

**Does not build yet.** The attestation itself is right and cheap. The pin is the v4.2.2
commit. The two permissions are enough. It works for a public repository on a personal
account. A failure stops the release before it exists. Four things need changing first:
- the policy would publish a hole the runner has today, `time.sleep` past the deadline
  (finding 1);
- its reporting route is switched off, and its fallback leads nowhere (finding 2);
- the verification command should bind the workflow and the tag, live where users look, and
  say which release is the first attested (finding 3);
- a verify-before-create step and a written recovery should make the first real run fail
  safe (finding 4).

The rules checks then need their exact contract written (finding 5).

One line: attesting in `publish` with this pin is correct and fails safe, but close or declare
the sleep-past-deadline hole, turn on a real reporting route, tighten the verify command, and
verify before creating the release, before this is built.
