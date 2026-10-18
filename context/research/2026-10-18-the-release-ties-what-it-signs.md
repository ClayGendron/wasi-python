# The release ties what it signs to what it built: the facts spec 057 stands on

- **Status:** research, 2026-10-18. Box: one session, done. No workflow, script or check in the
  repository was changed; every experiment ran on scratch copies.
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5), the author of spec 057.
- **Stands on:** the 0.1.0a4 security review (`build/reviews-evidence/a4-security/0.1.0a4-security-review-2026-10-18.md`
  in the main tree, git-ignored): F4, N1, N3 and the Confirmation's "F4 and a4's PyPI publish";
  spec 056, Decision 6 and question 94; specs 004, 009, 012, 028 and 040;
  `.github/workflows/release.yml`, `scripts/00_download.sh`, `scripts/steps/common.sh`,
  `release/version.py` and `tests/harness/scan.py` at main `d70690a`.
- **Evidence:** `2026-10-18-the-release-ties-what-it-signs/` beside this memo:
  - `release.yml.diff`: the drafted workflow, as a diff against `d70690a`. It is a sketch for
    the builder, not applied.
  - `probe_workflow.py` and `probe_workflow.log`: both workflows parsed with PyYAML.
  - `existing_scans.log`: the judge's two workflow scans run on both workflows.
  - `run_check_case.sh` and `check_step_cases.log`: the drafted check step run on good and
    tampered folders.
  - `00_download.diff`, `n1_harness.txt` and `n1_download_runs.log`: N1, before and after.

One idea per sentence. A term of art is defined where it first appears.

## The short version

- Five jobs fetch the build's assets by the name `release-assets`. Nothing ties those bytes to
  the build job (READ, `release.yml`). That is the gap F4 names.
- The two pinned artifact actions can close it. The upload action outputs the artifact's id
  and its SHA-256. The download action fetches by id, and by default fails when the
  artifact's digest does not match (READ, both `action.yml` files at the pinned commits).
- A job output can carry one more anchor: the SHA-256 of the build's `SHA256SUMS`. A job
  output is a value that a job hands to the jobs that need it. Each reader then checks every
  file against that list. A drafted check step refused every tampered folder and passed the
  build's own (EXECUTED, eight cases on two hash tools).
- N1 is real on all three build hosts. With one fetched name missing from `SHA256SUMS`, the
  download step exits 0 (EXECUTED). A ten-line change makes it exit 1 and name the file
  (EXECUTED).
- `setup-uv`'s cache is already off for a tag push by default. It is on for a manual dry run
  (READ). Turning it off explicitly makes the dry run take the tag run's path.
- A job that names an environment that does not exist creates it, with no protection rules
  (READ, GitHub's docs). So the workflow can name `release` before the owner protects it.

## What the pinned actions do (READ)

The sources were fetched from `raw.githubusercontent.com` at the commits `release.yml` pins.

- **`actions/upload-artifact@cf430e0…` (v7.0.2).** Its `action.yml` lists three outputs:
  `artifact-id` ("A unique identifier for the artifact that was just uploaded"),
  `artifact-url`, and `artifact-digest` ("SHA-256 digest for the artifact that was just
  uploaded"). Each is empty if the upload failed.
- **`actions/download-artifact@9000827…` (v8.0.2).** Its `action.yml` takes `artifact-ids`
  ("IDs of the artifacts to download, comma-separated. Either inputs `artifact-ids` or `name`
  can be used, but not both"). It also takes `digest-mismatch`, with options `ignore`, `info`,
  `warn` and `error`. The default is `error`, "which will fail the action".
- **How it looks an id up** (`src/download-artifact.ts`, lines 101-145):
  - It parses each id as a number, and throws on anything else, or on an empty list.
  - It lists the current run's artifacts (`latest: true`) and keeps those with a listed id.
  - It throws when none is found. A partly found list is only a warning, so a job should
    pass exactly one id per download.
  - With no `github-token` input, it sets no `findBy` (lines 65-80), so it reads the current
    run through the runner's own artifact service. A job needs no `GITHUB_TOKEN` scope to
    download its own run's artifacts (INFERRED from that code path).
- **The digest it checks** is `artifact.digest` from that listing (line 195). That is the
  service's record of the upload. So the action proves "the bytes uploaded under this id". It
  does not prove "the bytes the build job made". The build job's own output is what proves
  that.
- **With one artifact**, the files land in `path` itself, with no folder per artifact name
  (line 189-193). So a by-id download leaves the same layout as today's by-name download.
- **`astral-sh/setup-uv@1c37ad0…` (v10.3.0).** `enable-cache` defaults to `auto`: "enables
  caching on GitHub-hosted runners except for release, tag push, pull_request_target, and
  workflow_run events." The review guessed the cache was on (INFERRED there). It is off for a
  tag push and on for `workflow_dispatch`, the dry run.

## What GitHub says about outputs and environments (READ)

From `docs.github.com`, workflow syntax and "Managing environments", read 2026-10-18:

- "Outputs can be a maximum of 1 MB per job." "Outputs containing secrets are redacted on
  the runner and not sent to GitHub Actions."
- "When using a matrix, job outputs will be combined from all jobs inside the matrix. …
  Ensure that the output name is unique, otherwise the last matrix job that runs will override
  the output value."
- The page's matrix example has each leg write only its own output name (`output_1` to
  `output_3`). A later job then reads all three. So a matrix job can hand on one id per leg,
  each under its own name (INFERRED from the example).
- "Running a workflow that references an environment that does not exist will create an
  environment with the referenced name." Such an environment has no protection rules or
  secrets.
- An environment's protection rules "must pass before a job referencing the environment is
  sent to a runner". "Prevent self-review" stops the person who started a run from approving
  it.

## The workflow, parsed (EXECUTED)

`probe_workflow.py` parses a workflow with PyYAML 6.0.3, in a throwaway uv environment. It
reports four things:

- a download that is not by id, or lacks `digest-mismatch: error`;
- a `setup-uv` step whose cache is not off;
- an unpinned `uses:`;
- a `needs.J.outputs.O` that names a job the reader does not need, or an output J does not
  define.

| workflow | problems | what |
|---|---|---|
| today's (`d70690a`) | 13 | nine downloads by name (five of `release-assets`, four of the rebuilds' files), four `setup-uv` steps with the cache left to `auto` |
| the draft (`release.yml.diff`) | 0 | every download by id, every cache off, every reference defined |

- Every `uses:` in today's workflow is pinned by a 40-hex commit, as the review said. No
  check in the judge enforces that yet (READ, `tests/harness/scan.py`).
- Today the workflow-level permissions are `contents: read`. Only `attest`, `publish` and
  `pypi` declare their own permissions.

The judge's two workflow scans ran on both files (`existing_scans.log`, EXECUTED):

- `release_attestation_errors` passes both.
- `rebuild_gate_errors` passes today's file. On the draft it reports four errors, "same-bytes
  does not name …'s SHA256SUMS / rebuilt wheel". Its rules look for `name: rebuild-<runner>`.
  A download by id has no `name:`. So spec 057 has to change that scan, which is a judge
  change.

## The check step (EXECUTED)

The draft adds one step after each read of `release-assets`. The step is the same in all five
jobs. In order, it does four things:

1. It refuses an empty or non-hex `sums-sha256`.
2. It checks `SHA256SUMS` against `sums-sha256`.
3. It checks each file against `SHA256SUMS`.
4. It requires the folder to hold exactly the names `SHA256SUMS` lists, plus `SHA256SUMS`.

It uses `sha256sum` where the runner has it, and `shasum -a 256` otherwise.

`check_step_cases.log`: the step was pulled out of the draft with PyYAML (all five copies are
identical). It ran in bash on arm64 macOS 26.5.2, both with `/sbin/sha256sum` on PATH and
without it (then perl's `shasum`).

| case | either tool |
|---|---|
| the build's own three files | exit 0 |
| `sums-sha256` empty | exit 1, "handed on no SHA-256" |
| `sums-sha256` another hash | exit 1, `SHA256SUMS: FAILED` |
| `sums-sha256` in capitals | exit 1 |
| an extra `evil.whl` | exit 1, "other files than the build job's" |
| the wheel's bytes swapped | exit 1 |
| the `.tar.xz` missing | exit 1 |
| a sub-folder | exit 1 |

Not run here: Git for Windows's bash (the `verify` job's Windows leg) and GNU `sha256sum` on
Ubuntu. The dry run after landing is their evidence. Both are GNU coreutils, whose `-c` reads
this format (INFERRED).

## N1 (EXECUTED)

`n1_harness.txt` describes the setup:

- a scratch copy of the download script, `line.sh` and `line.conf`;
- a fake file for every pinned name, with a `SHA256SUMS` made from those fakes;
- a fake `uname` for each build host;
- a `curl` that fails if it is ever called. It never was.

| script | host | `zlib-1.3.1.tar.gz` unpinned | all pinned |
|---|---|---|---|
| today | x86_64 Linux | exit 0, "35 pins, 0 fetched, 34 verified" | exit 0 |
| today | aarch64 Linux | exit 0, "29 pins, 0 fetched, 28 verified" | exit 0 |
| today | arm64 macOS | exit 0, "29 pins, 0 fetched, 28 verified" | exit 0 |
| `00_download.diff` | all three | exit 1, `ERROR: no pin in downloads/SHA256SUMS for: zlib-1.3.1.tar.gz` | exit 0, N of N verified |

- With `--all` (the research input), the fixed script also exits 0, at "36 pins, 0 fetched,
  36 verified".
- `pinned()` in `steps/common.sh` still refuses an unpinned name at use (READ). So N1 was
  never a way in. It was a missing early failure.
- The fix compares names, not counts. A name with no `<name>: OK` line fails, and is named.
  This works even if a later `get` line repeats a name, which a count would not.

## Where it stopped

All in the box. These are not known until a real run:

- Git for Windows's tools under the `verify` job.
- A matrix leg's empty output name not overriding the other leg's value (the docs' example
  says it does not).
- The first tag run's `attest`, `publish` and `pypi` steps.

Spec 057 says how each is evidenced, and what happens when one fails.

## One line

The pinned artifact actions can fetch by id and check a digest, and a hash the build job hands
on ties every reader to the build's own files. N1 exits 0 today on every host, and a ten-line
name check fixes it.
