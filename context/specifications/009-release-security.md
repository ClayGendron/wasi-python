# 009 — Release security: provenance and a disclosure policy

- **Status:** draft, 2026-10-17. It changes the release workflow, so it is reviewed before it
  is built.
- **Owner:** Clay Gendron
- **Kind:** `.github/workflows/release.yml`, a new `SECURITY.md`, judge additions in
  `tests/checks/test_rules.py` and `tests/harness/scan.py`, `README.md`, `CHANGELOG.md`.
- **Depends on:** 004 (the release workflow).
- **Research it stands on:** `../research/2026-10-16-a-principal-engineers-direction.md`
  (section 2, "Supply chain": "no signature or provenance attestation on the release assets …
  no `SECURITY.md`"; direction 7). The constitution changes that direction also proposes
  (§5.5, a security fix as a reason to release; §5.6, a security review before each release)
  are the owner's (`../questions-for-the-owner.md`, question 5) and are not made here.

## Decisions

1. **Build provenance for every release asset.** The `publish` job, which runs only for a pushed
   tag, gains `id-token: write` and `attestations: write` and, before `gh release create`, one
   step: `actions/attest-build-provenance@4d101475d8b20a2381f78447822ac1eab6504dd8 # v4.2.2`
   (published 2026-08-06, more than two weeks old; pinned by commit like every other action) with
   `subject-path: release-assets/*`. It signs, through GitHub's Sigstore instance, a SLSA
   provenance statement that each asset (the wheel, the artifact `.tar.xz`, `SHA256SUMS`) was
   made by this workflow at this commit. Dry runs do not publish, so they do not attest.
2. **How a user verifies.** The README's "Releasing" section gains: `gh attestation verify
   <asset> --repo ClayGendron/wasi_python`, which checks the signature and that the asset's
   digest is the one the workflow recorded. The existing `SHA256SUMS` stays: it is what a user
   without `gh` checks.
3. **`SECURITY.md`.** It says:
   - what counts as a vulnerability here: a guest reaching the host's files, network or
     processes beyond what the embedder granted; a guest crashing or hanging the embedder's
     process through the door or the runner; a guest's planted code running in a later call;
     a defeat of a default limit; a release asset that does not match its pins, its
     `SHA256SUMS` or its attestation;
   - what does not: everything the README's "Safety" section lists as not protected (that list
     is the policy, kept in one place);
   - how to report: privately, through the repository's "Report a vulnerability" button
     (GitHub's private vulnerability reporting), never in a public issue; if that is not
     available, a public issue that asks for a contact and says nothing else;
   - supported versions: the newest alpha only, while the project is alpha;
   - what happens next: a fix is a new alpha with the advisory, and the release notes name it.
4. **Two rules checks** (`tests/checks/test_rules.py`, the rules area):
   `test_releases_attest_their_assets` (the workflow's `publish` job has the attestation step,
   pinned by a 40-hex commit, with the two permissions, before the release is created) and
   `test_a_security_policy_is_published` (`SECURITY.md` exists and names the private reporting
   route and the README's "Safety" section). A unit test feeds the workflow scan a workflow
   without the step and sees it fail.
5. **What is not verified before a release.** The attestation step runs only when a tag is
   pushed, so the first time it runs is the next release. The landing notes say so, and the
   next release's notes record its result (`gh attestation verify` on each asset, run from a
   clean machine).

## Intent

A user can prove a downloaded asset came from this repository's workflow at a given commit, and
knows how to report a hole in the sandbox without publishing it first.

## Design

```
.github/workflows/release.yml   publish: permissions; the attestation step
SECURITY.md                     the policy
tests/checks/test_rules.py      two rules checks
tests/harness/scan.py           the workflow scan
README.md, CHANGELOG.md         how to verify
```

## Scope

In: the above. Out: signing the wheel for PyPI (PyPI's own attestations come with trusted
publishing, which waits on the owner); the constitution's release rules (question 5); enabling
GitHub's private vulnerability reporting, a repository setting (question 10).

## Acceptance criteria

1. The two rules checks exist, the unit test shows the scan failing on a workflow without the
   step, and `uv run pytest` is green with `--accept-judge`.
2. A dry run of the release workflow passes every job (it does not reach `publish`).
3. The landing notes say the attestation is first exercised by the next release.

## Landing notes

(Filled in on landing.)
