# Review of 009 — Release provenance: every asset attested and verified (the build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I read `AGENTS.md`, the
  constitution, `context/reviews/README.md`, the 008 build review (for its format),
  specification 009 with its landing notes, and its pre-build review with the dispositions, the
  confirmation (N1–N6) and the author's answers. Then I read the diff. I did not rely on the
  landing notes. Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** local commit `a0ba5fa` (9 files, not pushed): the `attest` job in
  `.github/workflows/release.yml`, `scan.release_attestation_errors` and its helpers in
  `tests/harness/scan.py`, the rules check, the unit tests, `verify_note` in
  `release/version.py`, and the README and CHANGELOG text.
- **Re-ran (EXECUTED, darwin-arm64, gh 2.96.0).** Probes and outputs are under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev009b/`
  (`probes/`, `break_scan.txt`, `tightened-*.txt`, `yaml_check.txt`, `actionlint-*.txt`,
  `notes-0.1.0a2.md`, `pytest-*.txt`, `probe-dl/`).
  - `uv run pytest -m "not slow"` → `116/123 pass · 1 gap · 2 blocked · 0 fail · 4 deselected`
    (unit suite 177/177); `293 passed, 2 skipped, 4 deselected, 1 xfailed`; ratchet `lost 0 ·
    gained 1 · grew 0 · judge changed: tests/checks/test_rules.py, tests/harness/scan.py,
    tests/unit/test_release_version.py and 1 more`; exit 0.
  - `uv run pytest` (full, the artifacts in `build/artifacts/` read only) → `120/123 pass · 1 gap ·
    2 blocked · 0 fail` (unit suite 177/177); `297 passed, 2 skipped, 1 xfailed`; the same ratchet
    line; exit 0.
  - The new tests alone: `-k "attestation or verify"` on `test_scan.py` and
    `test_release_version.py` → `14 passed` (the good workflow, the eleven bad variants, the
    verify note, and an older download-script test the filter also matches); `test_rules.py -k attest` → `1 passed`.
  - The scan on the workflow before the change (`git show a0ba5fa^:…release.yml`) →
    `['no attest job']`; on the workflow as built → `[]`.
  - `uv run ruff check src tests` → all checks passed; `uv run ruff format --check src tests` →
    38 files already formatted.
  - PyYAML 6.0.3 in a throwaway environment (`uv run --no-project --with pyyaml==6.0.3`) and
    actionlint 1.7.12 (darwin_arm64 tarball, SHA-256 `aba9ced2…6953f` equal to its release's
    checksums file, and its own build provenance verified with `gh attestation verify`), run on
    the workflow before and after the change: both exit 0, nothing reported. shellcheck is not
    installed, so actionlint did not lint the `run:` scripts.
  - 32 mutations of the real workflow through the scan (table below), and a sketch of tightened
    rules through the same mutations and the unit test's own good and bad workflows.
  - `gh attestation verify` on a real attested asset (`cli/cli` v2.96.0,
    `gh_2.96.0_linux_arm64.tar.gz`, never executed) to test the flag forms, and the attestations
    REST API with no token.
  - I did not push, commit, tag, dispatch a workflow, run `scripts/build.sh`, touch
    `build/artifacts/`, or edit a tracked file other than this review. My pytest runs rewrote
    `build/progress/latest.json` (untracked build state).

## Decisions 1–6 against the diff

- **Decision 1 (READ, EXECUTED).** The `attest` job is between `verify` and `publish`, with
  `if: github.event_name == 'push' && github.ref_type == 'tag'` (the same string as `publish`),
  `needs: [build, verify]`, `ubuntu-24.04`, and exactly `id-token: write`, `attestations: write`,
  `contents: read` (PyYAML agrees). Its steps are download, attest, verify, with no `if:` or
  `continue-on-error`. The verify step sets `GH_TOKEN: ${{ github.token }}` and uses
  `$GITHUB_REPOSITORY` and `$GITHUB_REF`. `publish` has `needs: [build, verify, attest]`. The
  identity token is not in a job with `contents: write`, setup-uv or uv.
  - **The pin (EXECUTED).** `gh api repos/actions/attest/git/ref/tags/v4.2.2` → commit
    `1e69f48acb82d1966a394da916b4c1698aa569d6`; the release was published 2026-08-04T20:36:29Z.
  - **SLSA provenance with only `subject-path` (READ).** The action's README at that commit,
    "Attestation Modes": provenance mode is used when there is no `sbom-path` and no predicate
    input, and it "auto-generates SLSA build provenance". It signs through the public-good
    Sigstore instance for a public repository (`gh repo view` → `PUBLIC`, EXECUTED).
  - **Permissions (READ).** The README's example also lists `artifact-metadata: write`. That is
    only for a storage record, which the action makes only with `push-to-registry: true`
    (README "Artifact Metadata Storage Records"; `src/main.ts` gates on `pushToRegistry`). So the
    three permissions are enough. `subject-path` is expanded with `@actions/glob` and filtered to
    files (`src/subject.ts`), so `release-assets/*` names every asset.
  - **The verify loop (EXECUTED on `cli/cli`'s attestation, INFERRED for a tag).**
    - `--source-ref` compares the full ref string exactly: `refs/heads/trunk` passes; `trunk`
      fails with "expected SourceRepositoryRef to be trunk, got refs/heads/trunk";
      `refs/tags/v2.96.0` fails the same way. For a tag push, `$GITHUB_REF` is `refs/tags/v<x>`
      and the certificate's source ref comes from the token's `ref` claim, which is the same
      string (INFERRED from GitHub's documented claims; no tag-pushed attestation was probed).
    - `--signer-workflow <owner>/<repo>/.github/workflows/<file>` is the right form: it passes,
      and so does `github.com/<owner>/<repo>/…`; another file name (`other.yml`) fails. It is a
      prefix match, though (finding 6).
    - `--deny-self-hosted-runners` passes on a GitHub-hosted attestation.
    - The runner image `ubuntu24/20261012.334` lists GitHub CLI 2.102.0 (READ, runner-images
      readme), newer than 2.96.0 where all four flags exist (EXECUTED `--help`).
    - The step runs under the default `bash -e`, so the first asset that fails verification
      fails the step (INFERRED from the documented default shell). An empty glob passes the
      literal `release-assets/*` to `gh`, which fails: closed.
  - **`publish` (READ, EXECUTED).** Its permissions and steps are unchanged; it downloads the
    same `release-assets` artifact (PyYAML: `name: release-assets`, `path: release-assets`).
    `needs: [build, verify, attest]` only adds an edge; on a dry run `attest` and `publish` are
    both skipped by their own `if:`. `pypi` still needs `publish`.
- **Decision 2 (READ).** The workflow's command has `--repo`, `--signer-workflow`,
  `--source-ref` and `--deny-self-hosted-runners`, and so do the README and the release notes,
  with the literal repository.
- **Decision 3 (READ, EXECUTED).** The README has "Verifying a download" with the command and
  the three facts. `_notes` appends `verify_note(version)`; `notes()` is unchanged (the diff
  touches only `_notes`; `test_release_version.py:70` still asserts `notes(…) == "- first\n"`,
  and passes). `release` still builds the tag message from `notes()` alone. A unit test shows
  the version in `--source-ref refs/tags/v0.1.0a2`. The bundle sentence is incomplete
  (finding 5).
- **Decision 4 (READ, EXECUTED).** The README's "Releasing" says nothing is published if
  `attest` fails, to re-run the failed jobs, and never to push the tag again. The 90 days hold:
  `gh api repos/ClayGendron/wasi_python/actions/permissions/artifact-and-log-retention` →
  `{"days":90,"maximum_allowed_days":90}`.
- **Decision 5 (READ).** Dry runs do not reach `attest` (its `if:`). The landing notes say the
  first real run is the next release and where its result is recorded.
- **Decision 6 (READ, EXECUTED).** The scan exists with each listed rule, the check is
  `test_releases_attest_and_verify_their_assets`, and the unit test feeds one good workflow and
  eleven bad variants, each naming exactly its own error. But the rules read comments as code
  and miss several natural ways to undo the job (findings 1–3).

## Acceptance criteria against evidence

1. *The rules check exists and its unit test shows each rule failing on its bad variant;
   `uv run pytest` is green with `--accept-judge`.* **Met for what it states** (EXECUTED: 11
   variants, each its own error; both runs green, with "judge changed"). It is not yet accepted;
   that is the landing step. The scan's misses (findings 1–3) are not in the criterion, but
   they are in Decision 1's promises the scan exists to keep.
2. *A dry run of the release workflow passes every job it runs.* **Not shown.** The commit is
   not pushed, so no dry run can include it. YAML and actionlint are clean (EXECUTED), and the
   change adds only a job that a dry run skips, so I expect it to pass (INFERRED). It must still
   be run after the push, before the landing is declared.
3. *The landing notes say the attestation is first exercised by the next release.* **Met**
   (READ: "Not yet exercised").

## Mutations of the real workflow through the scan (EXECUTED, `break_scan.txt`)

"Passes" means the scan reports nothing. "Closed" means the release would still fail before
publishing, because the strict verify step backstops it.

| # | mutation | scan | effect if shipped |
|---|---|---|---|
| 1 | the `actions/attest` step commented out | passes | **verify fails: closed**, but the judge is blind |
| 2 | the verify loop commented out (and `true` left) | passes | **publishes unverified** |
| 3 | a bare `gh attestation verify … --owner x`, the flags only in a following `echo` or `#` line | passes | weak verify; publishes |
| 4 | `… --deny-self-hosted-runners \|\| true` | passes | **publishes unverified** |
| 5 | `set +e` before the loop | passes | only the last asset's result counts |
| 6 | job-level `continue-on-error: true` on `attest` | passes | **publish runs after a failed attest** (INFERRED) |
| 7 | step `if:` / `continue-on-error:` at eight spaces | fails | — |
| 8 | workflow-level `permissions:` gains `id-token: write`, or becomes `write-all` | passes | `build` and `verify` (no own block) hold the token with setup-uv and the build |
| 9 | `publish`'s `permissions: write-all` | passes | `contents: write` and the token together |
| 10 | `id-token:   write` (extra spaces) in `publish` | passes | the same |
| 11 | `id-token: write` in the `verify` matrix job (flow mapping) | fails | — |
| 12 | both `attest`'s and `publish`'s `if:` set to `always()` | passes | **dry runs sign to the public log**, and publish |
| 13 | `publish`'s `if:` weakened alone | fails | — |
| 14 | `attest` `needs: [build] # not verify` | passes | signs before `verify` |
| 15 | `publish` `needs: [build, verify] # attest later` | passes | publishes without waiting |
| 16 | `astral-sh/setup-uv` step added to `attest` | passes | the token beside uv (Decision 1) |
| 17 | `predicate-type`/`predicate` inputs added to the attest step | passes | closed: verify's default `--predicate-type` is SLSA v1 (EXECUTED: "no attestations found with predicate type") |
| 18 | `--source-ref refs/heads/main`, or `--signer-workflow …/ci.yml` | passes | closed (verify fails) |
| 19 | the download names another artifact | passes | closed (download fails) |
| 20 | a duplicate `attest:` key later in the file | passes | not a real case: GitHub rejects duplicate keys (INFERRED) |
| 21 | `needs:` as a block list; a comment line or a trailing comment in `permissions:` | **fails** | false positives on valid YAML: friction, not a hole |

## Findings, most severe first

1. **The scan reads comments as code, so commenting out the verify step or the attest step
   passes** (`tests/harness/scan.py`, `release_attestation_errors`: the `ATTEST_USES` and
   `subject-path` searches over `body`, the `"gh attestation verify" in line` filter, and the
   `needs` word lists). Medium.
   - **Failure (EXECUTED, rows 1, 2, 14, 15).** Prefix each line of the verify loop with `# `:
     the scan returns `[]`, and `publish` would release assets nobody verified. The same for the
     attest step, and for `needs` names that appear only in a trailing comment.
   - Commenting out is the most natural way to switch a step off "for now". It is the case the
     check most needs to catch.
   - **Fix.** Drop full-line comments and trailing ` # …` comments from the text before every
     rule. The sketch in `probes/scan_tightened.py` does it in one function (`uncomment`), and
     it also clears the false positives of row 21. Add a bad variant: the verify loop commented
     out.

2. **A failure in `attest` can be swallowed, so `publish` runs anyway**
   (`release_attestation_errors`: the step rule matches six-space and deeper keys only; nothing
   looks at the verify command's shell). Medium.
   - **Failure (EXECUTED scan, INFERRED effect; rows 4–6).** `continue-on-error: true` at the
     job level, `|| true` after the verify command, or `set +e` before the loop: the scan returns
     `[]`. Decision 1 says "a release is created only for assets that verify" and "No step in the
     job has `if:` or `continue-on-error`"; Decision 4 says "if `attest` fails, nothing is
     published".
   - **Fix.** Reject `continue-on-error:` at the job level too (`^    continue-on-error:`), and
     reject `||` and `set +e` in the job. Each with its own bad variant.

3. **The scan misses the identity token granted outside a job's own block, and the shared `if:`
   can be weakened in both jobs at once** (`release_attestation_errors`: the `id-token: write`
   substring test over jobs only; the `if:` equality). Low-medium.
   - **Failure (EXECUTED; rows 8–10, 12).**
     - The workflow-level `permissions:` with `id-token: write` (or `write-all`) passes.
       `build` and `verify` have no block of their own, so both would hold the token while
       running setup-uv, uv's Python and the whole build. Decision 1: "never in the same job as
       `contents: write`, setup-uv or uv's Python".
     - `publish` with `permissions: write-all`, or `id-token:   write` with extra spaces, passes.
     - Both `if:` lines set to `always()` passes. Then a dry run signs into the public log,
       which Decision 5 exists to prevent. Nothing else in the judge checks `publish`'s `if:`
       either (READ: the only other workflow check is the zero-patch one).
   - **Fix.** Match `id-token:\s*write|write-all` in the text before `jobs:` and in every job
     but `attest` and `pypi`. Pin `attest`'s `if:` to the literal
     `github.event_name == 'push' && github.ref_type == 'tag'`, besides equality with
     `publish`'s. (The unit test's `GOOD_WORKFLOW` then needs that full `if:`.)

4. **A bare verify passes when the four flags appear anywhere after it**
   (`verify_text` joins every line from the first `gh attestation verify` to the end of the
   job). Low.
   - **Failure (EXECUTED, row 3).** `gh attestation verify "$a" --owner ClayGendron` followed by
     `echo "--repo --signer-workflow --source-ref --deny-self-hosted-runners"` passes. The real
     verify then binds neither workflow nor tag.
   - **Fix.** Join `\`-continued lines into logical commands, and require every logical command
     that runs `gh attestation verify` to carry all four flags. Rejecting `setup-uv` and
     `uv run` in the job (row 16, Decision 1) fits in the same change.
   - The sketch (`probes/scan_tightened.py`) with findings 1–4's changes fails every row of the
     table that should fail, passes the real workflow, and still names each of the unit test's
     eleven errors first (EXECUTED, `tightened-mutations.txt`, `tightened-unit.txt`). It is a
     sketch to measure the size of the change, not code for the repository.

5. **The README's bundle route is true but cannot be followed as written** (`README.md:172-173`).
   Low.
   - EXECUTED: `GET /repos/cli/cli/attestations/sha256:<digest>` with no token → HTTP 200, but
     each entry has `"bundle": null` and a `bundle_url` to a raw-snappy-compressed file. After
     fetching and decompressing it, `gh attestation verify --bundle … --repo … --signer-workflow
     … --source-ref … --deny-self-hosted-runners` with no token and an empty `GH_CONFIG_DIR`
     exits 0. So the route works.
   - "Verifies offline" is not shown: `gh` fetched Sigstore's trusted root over the network; a
     truly offline check needs `--custom-trusted-root` (INFERRED from `--help`).
   - The API also returns a second attestation, GitHub's own release attestation
     (`https://in-toto.io/attestation/release/v0.2`), which `gh` skips by predicate type.
   - **Fix.** Say: the API answers without a token with a link to a snappy-compressed bundle;
     decompressed, it verifies with `--bundle` and no login. Drop "offline", or name
     `--custom-trusted-root`.

6. **`--signer-workflow` is a prefix match** (Decision 2, `README.md:165-168`, the workflow, the
   notes). Low.
   - EXECUTED: against `cli/cli`'s `deployment.yml` attestation, `--signer-workflow
     cli/cli/.github/workflows/deploy` passes, and so does `…/deployment.yml@refs/heads/trun`.
     `--cert-identity https://github.com/cli/cli/.github/workflows/deployment.yml@refs/heads/trun`
     fails; only the exact identity passes.
   - So `…/release.yml` would also accept a workflow named `release.yml2.yml` in the same
     repository, run on the same tag. That needs write access to the repository, which could
     change `release.yml` itself, so the gain is small.
   - **Fix (optional, a Decision 2 change).** Either accept it in writing, or use
     `--signer-workflow ClayGendron/wasi_python/.github/workflows/release.yml@refs/tags/v<version>`
     (the `@` ends the path) or the exact `--cert-identity`. The scan's flag list would follow.

7. **No test shows the `notes` command appends the note** (`tests/unit/test_release_version.py`
   `test_the_release_notes_say_how_to_verify_this_version`). Low.
   - It tests `verify_note()` alone. Removing `+ verify_note(a.version)` from `_notes` would
     pass every test (READ; INFERRED that nothing else reaches `_notes`).
   - EXECUTED: `uv run --no-project python release/version.py notes 0.1.0a2` exits 0. Its body
     ends with a separate paragraph, "**Verify a download** …", and one fenced block, outside the
     bullet list (markdown-it-py 3.0.0 CommonMark parse: one `fence`, the list closed before it).
     So the output is well-formed today.
   - **Fix.** One test: `version.main(["notes", v])` on a temporary changelog (monkeypatch
     `version.CHANGELOG`, as `test_bump_writes_both_files_or_neither` does), asserting the output
     is `notes(…) + verify_note(v)`.

8. **The specification's Status line still says draft and "reviewed again before it is built"**
   (`009:3-8`). Low, for the landing.
   - **Fix.** On landing, set the status to landed and cite this review in the landing notes.

### Not findings (checked)

- The verify step runs straight after the attest step. If the attestations API lagged, the
  step would fail and nothing would publish; the documented re-run recovers (INFERRED; fails
  closed).
- A re-run of `attest` signs a second statement for the same digests. That is harmless.
- `notes()` and the tag message are unchanged (READ, EXECUTED as above).
- The README and CHANGELOG claims (signs every asset, verifies before publishing, nothing
  published on failure, re-run within 90 days, dry runs never sign, `0.1.0a1` has none) match
  the workflow as built (READ, and EXECUTED for the 90 days). The CHANGELOG bullet sits in the
  unreleased `0.1.0a2` section, the first release it will be true for.

## Constitution checks

- §4.2 pinned inputs: the new action is pinned by commit with its release named; the
  download-artifact pin is the one already used. Holds.
- §4.8 downloads untrusted: my probes kept every download in scratch and executed none but the
  hash-checked, attested actionlint. The change itself downloads nothing new into the build.
- §4.10 evidence: the landing notes label their claims EXECUTED; I reproduced the "seen failing
  first" result and the YAML parse. Holds.
- §4.13 tooling: ruff and pytest green; no dependency added to `pyproject.toml`. Holds.
- §4.14 and §7 git: the commit is local and not pushed; no tag, dispatch or release came with
  it. Nothing tripped that I can see.
- §5.6 review: this is the build review; the pre-build review and confirmation are cited in the
  specification.

## Disposition (filled in by the author)

1. **Fixed.** The scan strips whole-line and trailing comments before every rule
   (`scan.without_comments`); unit variants comment out the attest step and hide `verify` in a
   comment, and both fail.
2. **Fixed.** A job-level `continue-on-error:`, `||` and `set +e` in the job each fail; unit
   variants for the first two.
3. **Fixed.** The text before `jobs:` may not grant `id-token: write` or `write-all`; any job
   but `attest` and `pypi` is matched with `id-token:\s*write|write-all`; both `attest`'s and
   `publish`'s `if:` must be exactly the pushed-tag condition.
4. **Fixed.** `\`-continued lines are joined and every `gh attestation verify` must carry all
   four flags; the job may not use setup-uv or uv.
5. **Fixed.** The README no longer offers the REST bundle route.
6. **Fixed.** The author tested `--signer-workflow` on cli/cli's attested release (EXECUTED: it
   is a prefix match; `…/deployment.yml@refs/heads/trunk` passed, `…@refs/heads/other` failed).
   The workflow, the README and the release notes now pass `release.yml@refs/tags/v<version>`,
   which pins the file name exactly; `--source-ref` stays exact.
7. **Fixed.** `test_the_notes_command_prints_the_verify_note` runs the `notes` command.
8. **Fixed** at landing.

## Verdict

**Does not land yet.** The workflow change is right: the pin is v4.2.2, provenance is what
`subject-path` alone makes, the three permissions are enough, the verify flags have the right
forms, `publish` waits for `attest`, and a failure fails closed. The judge that guards it is
too easy to fool. Commenting out the verify step, `|| true`, a job-level `continue-on-error`, or
a workflow-level `id-token: write` all pass it (findings 1–3, Medium and Low-medium). They are a
few lines in one function and one bad variant each. Findings 4–8 are Low and can be fixed in the
same pass or answered in writing. Criterion 2's dry run waits on the push.

One line: the `attest` job is correct and fails closed, but make the scan ignore comments and
catch swallowed failures and a wider grant of the token before this lands.
