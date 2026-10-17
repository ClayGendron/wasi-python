# 009 — Release provenance: every asset attested and verified

- **Status:** landed, 2026-10-17. Reviewed before build
  (`../reviews/009-release-security-spec-2026-10-17.md`) and after
  (`../reviews/009-release-security-2026-10-17.md`). `SECURITY.md`, the first draft's other
  half, waits on the owner (question 10) and on spec 010.
- **Owner:** Clay Gendron
- **Kind:** `.github/workflows/release.yml`, `release/version.py`, judge additions in
  `tests/checks/test_rules.py`, `tests/harness/scan.py`, `tests/unit/test_scan.py` and
  `tests/unit/test_release_version.py`, `README.md`, `CHANGELOG.md`.
- **Depends on:** 004 (the release workflow).
- **Research it stands on:** `../research/2026-10-16-a-principal-engineers-direction.md`
  (section 2, "Supply chain": "no signature or provenance attestation on the release assets";
  direction 7), and the review's probes (EXECUTED: `gh attestation verify` on another project's
  release assets, with and without login, and on `v0.1.0a1`'s assets). The constitution changes
  direction 7 also proposes are the owner's (question 5) and are not made here.

## Decisions

1. **A separate `attest` job.** Between `verify` and `publish`, a new job, `attest`, runs only
   for a pushed tag (the same `if:` as `publish`), with `needs: [build, verify]` (so it never
   signs a set that then fails on another system: a signature is permanent, Decision 5), on
   `ubuntu-24.04`, with job-level permissions
   `id-token: write`, `attestations: write` and `contents: read` and nothing else. Its steps:
   download the `release-assets` artifact; `actions/attest@1e69f48acb82d1966a394da916b4c1698aa569d6
   # v4.2.2` (published 2026-08-04, more than two weeks old; upstream recommends it over the older
   `attest-build-provenance` wrapper) with `subject-path: release-assets/*`, the same glob
   `publish` uploads, and no other input, which makes a SLSA build-provenance statement signed
   through the public-good Sigstore instance (the repository is public); then, for each asset,
   `gh attestation verify` with the strict flags of Decision 2, so a release is created only for
   assets that verify. The verify step sets `GH_TOKEN: ${{ github.token }}` (without it `gh`
   exits 4) and names the repository and ref from `$GITHUB_REPOSITORY` and `$GITHUB_REF`, not typed
   literals. No step in the job has `if:` or `continue-on-error`. `publish` gains
   `needs: [build, verify, attest]`. The identity token is never in the same job as
   `contents: write`, setup-uv or uv's Python.
2. **The strict verification.** `gh attestation verify <asset> --repo ClayGendron/wasi_python
   --signer-workflow ClayGendron/wasi_python/.github/workflows/release.yml@refs/tags/v<version>
   --source-ref refs/tags/v<version> --deny-self-hosted-runners`. `--repo` alone would accept a
   statement from any workflow in the repository at any ref; the two extra flags fail on a
   mismatch (the review, EXECUTED). `--signer-workflow` is a prefix match, so it carries
   `@refs/tags/v<version>`, which pins the workflow's file name exactly (the build review's
   finding 6; EXECUTED by the author on cli/cli's release).
3. **Where users read it.** The README gains a section, "Verifying a download", with that command,
   and three facts: `gh` must be logged in for the command as written (`gh attestation
   download` needs a login too, but GitHub's attestations REST API answers without a token, so a
   bundle fetched from it verifies offline with `--bundle`: the review, EXECUTED); `SHA256SUMS` remains
   the check for a user without `gh`; and the first attested release is the first one published
   after this specification lands (`v0.1.0a1` has none; verifying its assets fails with a 404:
   the review, EXECUTED). The `notes` command of `release/version.py` (`_notes`, which prints the
   release body) appends the command with the version filled in; `notes()`, which also builds the
   annotated tag's message, does not change. A unit test shows the command with the version.
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
   uploads (`release-assets/*`); an `attest` job that does not need both `build` and `verify`;
   no `gh attestation verify` line carrying `--repo`, `--signer-workflow`, `--source-ref` and
   `--deny-self-hosted-runners`; steps out of order (download, then attest, then verify); any
   `if:` or `continue-on-error` on a step of the job; `id-token: write` in any job other than
   `attest` and `pypi`; a `publish` job that does not need `attest`. The check is
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

Built 2026-10-17 by the author agent (local commit `a0ba5fa`); reviewed in
`../reviews/009-release-security-2026-10-17.md`. Its fixes: the scan reads the workflow without
comments and refuses swallowed failures, workflow-level or stray identity tokens, and weakened
`if:` lines; every verify command carries all four flags, and `--signer-workflow` carries
`@refs/tags/v<version>` (a prefix match otherwise, EXECUTED on cli/cli).

**Seen failing first** (EXECUTED): `test_releases_attest_and_verify_their_assets` on the
workflow before the change: "no attest job". The unit tests: the good workflow passes, and each
of the eleven bad variants yields exactly its own error.

**The workflow** parses as YAML (EXECUTED: PyYAML 6.0.3 in a throwaway environment): jobs
`build`, `verify`, `attest`, `publish`, `pypi`; `attest` needs `[build, verify]` with exactly the
three permissions; `publish` needs `[build, verify, attest]`.

**Not yet exercised:** the `attest` job runs only for a pushed tag, so its first run is the next
release (Decision 5); that release's landing notes record `gh attestation verify` on each asset
from a clean machine.
