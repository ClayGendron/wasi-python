# 009 — Release provenance: every asset attested and verified

- **Status:** draft, 2026-10-17; revised the same day to answer its review
  (`../reviews/009-release-security-spec-2026-10-17.md`). The review's findings 1, 2 and 6 were
  about `SECURITY.md`, which moved out of this specification: it waits on the owner turning on
  private vulnerability reporting (`../questions-for-the-owner.md`, question 10; the setting is
  off today, EXECUTED by the review) and on spec 010 (a sleeping guest keeps its deadline), so
  that the policy it publishes is true when it is published. It changes the release workflow,
  so it is reviewed again before it is built.
- **Owner:** Clay Gendron
- **Kind:** `.github/workflows/release.yml`, judge additions in `tests/checks/test_rules.py`,
  `tests/harness/scan.py` and `tests/unit/test_scan.py`, `README.md`, `CHANGELOG.md`.
- **Depends on:** 004 (the release workflow).
- **Research it stands on:** `../research/2026-10-16-a-principal-engineers-direction.md`
  (section 2, "Supply chain": "no signature or provenance attestation on the release assets";
  direction 7), and the review's probes (EXECUTED: `gh attestation verify` on another project's
  release assets, with and without login, and on `v0.1.0a1`'s assets). The constitution changes
  direction 7 also proposes are the owner's (question 5) and are not made here.

## Decisions

1. **A separate `attest` job.** Between `verify` and `publish`, a new job, `attest`, runs only
   for a pushed tag (the same `if:` as `publish`), on `ubuntu-24.04`, with job-level permissions
   `id-token: write`, `attestations: write` and `contents: read` and nothing else. Its steps:
   download the `release-assets` artifact; `actions/attest@1e69f48acb82d1966a394da916b4c1698aa569d6
   # v4.2.2` (published 2026-08-04, more than two weeks old; upstream recommends it over the older
   `attest-build-provenance` wrapper) with `subject-path: release-assets/*`, the same glob
   `publish` uploads, and no other input, which makes a SLSA build-provenance statement signed
   through the public-good Sigstore instance (the repository is public); then, for each asset,
   `gh attestation verify` with the strict flags of Decision 2, so a release is created only for
   assets that verify. No step in the job has `if:` or `continue-on-error`. `publish` gains
   `needs: [build, verify, attest]`. The identity token is never in the same job as
   `contents: write`, setup-uv or uv's Python.
2. **The strict verification.** `gh attestation verify <asset> --repo ClayGendron/wasi_python
   --signer-workflow ClayGendron/wasi_python/.github/workflows/release.yml --source-ref
   refs/tags/v<version> --deny-self-hosted-runners`. `--repo` alone would accept a statement from
   any workflow in the repository at any ref; the two extra flags fail on a mismatch (the review,
   EXECUTED).
3. **Where users read it.** The README gains a section, "Verifying a download", with that command,
   and three facts: `gh` must be logged in for the command as written (a downloaded bundle,
   `gh attestation download`, verifies without one: the review, EXECUTED); `SHA256SUMS` remains
   the check for a user without `gh`; and the first attested release is the first one published
   after this specification lands (`v0.1.0a1` has none; verifying its assets fails with a 404:
   the review, EXECUTED). `release/version.py notes` appends the command, with the version filled
   in, to every release's notes.
4. **Recovery.** If `attest` fails, nothing is published. The README's "Releasing" section says
   so, and that the fix is to re-run the failed jobs of the same workflow run (its artifacts are
   kept 90 days), never to push the tag again.
5. **No rehearsal in a dry run.** Dry runs do not reach `attest`: a statement signed for this
   public repository goes to Sigstore's public transparency log, which is permanent, so it is made
   only for a real release. The first real run of `attest` is the next release; its result
   (`gh attestation verify` on each asset from a clean machine) is recorded in that release's
   landing notes, under the specification that cuts it.
6. **The rules check, text-based.** The judge has no YAML library, so
   `scan.release_attestation_errors(workflow_text)` reads the workflow as text and reports: no
   `attest:` job; an `attest` job whose `if:` is not the `publish` job's; job permissions other
   than exactly `id-token: write`, `attestations: write`, `contents: read`; no `uses:
   actions/attest@` pinned by a 40-hex commit; a `subject-path` other than the glob `publish`
   uploads (`release-assets/*`); no `gh attestation verify` line carrying both
   `--signer-workflow` and `--source-ref`; any `if:` or `continue-on-error` on a step of the job;
   a `publish` job that does not need `attest`. The check is
   `test_releases_attest_and_verify_their_assets`. Its unit test feeds one good workflow and one
   bad variant per rule, each naming exactly its own error.

## Intent

A user can prove that a downloaded asset came from this repository's release workflow at the
tag it claims, and the workflow refuses to publish an asset it cannot prove.

## Design

```
.github/workflows/release.yml   the attest job; publish needs it
release/version.py              notes: the verify command appended
tests/harness/scan.py           release_attestation_errors
tests/checks/test_rules.py      test_releases_attest_and_verify_their_assets
tests/unit/test_scan.py         one good, one bad per rule
README.md, CHANGELOG.md         "Verifying a download"; recovery in "Releasing"
```

## Scope

In: the above. Out: `SECURITY.md` (waits on question 10 and spec 010); PyPI's own attestations,
which come with trusted publishing (the owner's, later); the constitution's release rules
(question 5).

## Acceptance criteria

1. The rules check exists and its unit test shows each rule failing on its bad variant;
   `uv run pytest` is green with `--accept-judge`.
2. A dry run of the release workflow passes every job it runs (`attest` and `publish` are
   skipped, as for every dry run).
3. The landing notes say the attestation is first exercised by the next release.

## Landing notes

(Filled in on landing.)
