# 185: The wheel on PyPI carries its provenance

- **Status:** drafted 2026-11-05, not built. Asked for on 2026-11-05 by the owner: "The page is showing a warning about loss of provenance from 0.1.1 to 0.1.3. This is a very bad look, and must be resolved and ensured that we do not do this again." The owner's decisions of the same day are in `../decisions.md`, "PyPI provenance comes back".
- **Date:** 2026-11-05
- **Owner:** Clay Gendron
- **Kind:** **build-class** (the release workflow: the upload job signs before it uploads, a new read-back job after it, a new rehearsal job on the release shape; a read-back script under `release/`; their rules in `tests/harness/scan.py`; the release and verify pages; a project rule in `AGENTS.md`). Not structural: nothing under `src/` changes. No wasm build, and nothing the build makes changes. Reviewed before it is built, as 148 was, since it changes what holds `id-token` on a tag.
- **Depends on:** 148 (the upload by the pinned uv, rule 20), 155 (`judged`), 180 (the wheel's limit).
- **Research it stands on:** PyPI's Integrity API, read for every released wheel; the research brief of 2026-11-05 (*Is this the practice*, below); `astral-sh/attest-action` at `39b6ce43875c196a579e31635b11aa2a2036384a` (v0.0.7), read whole and run; pypi-attestations' and Warehouse's source, read for what PyPI checks.

Labels: EXECUTED, run and seen; READ, read from a file or a page, cited; INFERRED, reasoned.

## The problem

PyPI shows a provenance panel for a file that was uploaded with a PEP 740 attestation. That is a statement, signed through Sigstore by the workflow that published the file, naming the repository, the workflow and the commit. PyPI's Integrity API returns it at `/integrity/<project>/<version>/<file>/provenance` (EXECUTED, 2026-11-05):

| Version | Uploaded | PyPI provenance |
|---|---|---|
| 0.1.0 | 2026-10-23 | `ClayGendron/wasi_python`, `release.yml`, environment `pypi` |
| 0.1.1 | 2026-10-27 | `ClayGendron/wasi-python`, `release.yml`, environment `pypi` |
| 0.1.2 | 2026-10-29 | none ("No provenance available") |
| 0.1.3 | 2026-11-04 | none ("No provenance available") |

PyPI's project page now warns that provenance was lost after 0.1.1. A reader sees a project whose newest releases are less verifiable than its older ones. Whatever the cause, that looks like a supply-chain compromise.

### The cause

Specification 148 (Decision 6) replaced the upload step `pypa/gh-action-pypi-publish@dc37677b…` with `uv publish --no-config --trusted-publishing always dist/*.whl`. The action made a PEP 740 attestation for every file it uploaded, by default. `uv publish` uploads an attestation it finds beside a file, but makes none (READ, 148's research; EXECUTED, `uv publish --help` of uv 0.11.32 and 0.13.7 lists `--no-attestations` and nothing that signs). The swap landed in #49 (`37475488`) and first ran at the 0.1.2 tag. No upload since has carried an attestation.

The reason for the swap stands. The action runs a container named by a tag while the job holds `id-token: write`. The image is `docker://ghcr.io/pypa/gh-action-pypi-publish:<ref>`, named by a tag even when the action is pinned by commit, and a tag can be pushed again (READ, the research brief, `create-docker-action.py`). This specification keeps that fix and puts the attestation back.

### The process that was missing

Three gaps let a visible regression ship twice.

1. **The loss was decided on an inference, not on what the reader sees.** 148's pre-build review recommended accepting the loss because "PyPI still records that the file came through this repository's trusted publisher", and because no page of ours claimed PyPI's provenance (INFERRED, in that review's words). Nobody looked at PyPI's page for a file without provenance, or at what it says beside a file that has it. The owner accepted the loss on 2026-10-28, as it was described: a detail, reversible (`../decisions.md`). The owner was not told that PyPI would warn on the project's page.
2. **Nothing read PyPI back.** The release checks its own bytes thoroughly: the build, two rebuilds, `same-bytes`, `judged`, `attest` and a strict `gh attestation verify`. After `pypi` uploads, nothing reads what PyPI serves. The release page asks the maintainer to compare PyPI's digest by hand, and asks nothing about provenance (`docs/contributing/release-process.md`, "After a release"). So 0.1.2 and 0.1.3 shipped with both runs green, and nobody noticed until the owner read the page.
3. **No rule held a release to the proofs its predecessor carried.** The project's ratchet keeps an accepted test pass from being lost quietly. Nothing kept a public proof of origin from being lost: one Decision in one specification could drop a proof users rely on.

Files on PyPI cannot change, so 0.1.2 and 0.1.3 will never carry PyPI provenance. The owner's decision: leave them, and release 0.1.4 with it (`../decisions.md`).

## Is this the practice

The owner asked that a fresh agent confirm the design is the accepted way to get PEP 740 attestations with uv. The brief asked whether uv makes attestations, how the pypa action makes them, whether a separate signing job is a supported pattern, whether `actions/attest` can stand in, and how to verify after upload. It did not tell the agent the design. Its findings (READ unless marked; docs.astral.sh and docs.pypi.org were read through their sources on GitHub):

- uv does not make attestations. uv 0.9.12 added their *upload* (#16731). Astral's way to make them is its own action, **`astral-sh/attest-action`**, "a GitHub Action that generates PEP 740 publish attestations … primarily useful for directly publishing with uv publish". uv's GitHub guide runs it, pinned by commit (`39b6ce43…`, v0.0.7), as a step just before `uv publish` (`docs/guides/integration/github.md`).
- The pypa action signs inside its container, with pypi-attestations 0.0.30 and sigstore 4.5.1. The container is named by a tag. The concern of 148 is still accurate.
- PyPI's docs describe signing in a separate job (for GitLab, a `generate-pypi-attestations` job) and `pypi_attestations sign` with ambient `id-token: write` on GitHub (`docs/user/attestations/producing-attestations.md`). Warehouse verifies an attestation against the identity of the publisher that made the upload. For GitHub, pypi-attestations' policy, `_GitHubTrustedPublisherPolicy(repository, workflow)`, reads the repository and the workflow file, not the environment. A signature from a job outside the `pypi` environment verifies (READ by this author too: `pypi_attestations/_impl.py`, `GitHubPublisher._as_policy`; `warehouse/oidc/models/github.py`, `attestation_identity`).
- Pitfalls: the signature must come from the same top-level workflow file as the trusted publisher, not a reusable workflow (uv's own 0.9.15 release failed on this, astral-sh/uv#16944); the attestation's subject must be the uploaded file, untouched after signing; one attestation per predicate type; the upload must use trusted publishing; the file is `<dist>.publish.attestation` beside the distribution.
- `actions/attest` is not usable directly. Its Sigstore bundle would need converting to PyPI's attestation form.
- After the upload, the Integrity API answers 200 with the provenance, and `pypi-attestations verify pypi --repository <url> pypi:<file>` verifies it.

The owner first chose, from these findings, Astral's action in a job of its own. The owner then asked how other projects do it, and a second fresh agent read ten release workflows that publish with `uv publish` (READ, 2026-11-05): pyca/cryptography, pypa/abi3audit, PyO3/maturin, djlint/djLint, ormsgpack/ormsgpack, lmcinnes/umap, huggingface/hf-serve, astral-sh/trusted-publishing-examples, zizmorcore/zizmor and astral-sh/uv (with ruff and ty). Eight sign with `astral-sh/attest-action`, seven of them pinned by commit, **always as a step in the upload job**, just before `uv publish`. zizmor turned attestations off because it signs from a reusable workflow. uv, ruff and ty put none on PyPI and attest only their GitHub release files. **None reads PyPI back after the upload.** None signs in a separate job.

The owner's decision (2026-11-05, AskUserQuestion): **the common pattern**, the action as a step in `pypi` before `uv publish`. It is proven in the wild, it needs no hand-off of the attestation between jobs, and it is what Astral documents. This replaces the separate job of the first draft. That draft's pre-build review is answered on that basis below.

What this author then found by running the action's own command (EXECUTED, 2026-11-05, in a scratch clone at `39b6ce43`). These pitfalls the brief did not name, and each changes the design:

- **The pinned uv refuses the action's lock.** The action runs `uv run --locked --no-dev --project "$GITHUB_ACTION_PATH" action.py`. Its `pyproject.toml` sets a relative `exclude-newer = "P7D"`, recorded in `uv.lock` as `exclude-newer-span`. uv 0.9.22, 0.9.30, 0.10.0, 0.11.0, 0.11.32 and 0.12.5 refuse with "The lockfile at `uv.lock` needs to be updated, but `--locked` was provided". uv 0.13.0, 0.13.5 and 0.13.7 accept it. Had the action been dropped into `pypi` beside the workflow's uv 0.9.22, the 0.1.4 tag would have failed at the signature.
- **The action's own uv is a range.** When no uv is on the path, the action runs `astral-sh/setup-uv` with `version: ">=0.9.12"`: unpinned, and admitting the versions that refuse its lock. So the job installs its own exact uv first.
- **`--no-config` breaks the lock too.** `uv run --no-config --locked --project <action>` drops the action's `[tool.uv]` settings and refuses the same way. The action does not pass it, and nor does our read-back.
- From this repository's root, uv 0.13.7 runs the action's lock the same as from an empty folder, so our root `pyproject.toml` does not steer it.

An upstream issue for the second point (the fallback range admits uv versions that refuse the lock) is drafted under `../upstream/` for the owner to send. It is not ours to send.


## Decisions

### 1. `pypi` signs, then uploads

`pypi` keeps its `if:` (`PYPI_IF`), its `needs:` (`build`, `publish`), `environment: pypi` and its permissions (`contents: read`, `id-token: write`). Its steps become, in order:

1. `actions/checkout`, pinned by commit, at `HEAD_REF`, no credentials, sparse `.github/actions` and `release` (Decision 3).
2. `astral-sh/setup-uv`, pinned by commit, `version: "0.13.5"`, `checksum:` the archive's SHA-256, cache off (Decision 2).
3. The build's files, through `./.github/actions/verify-artifact`.
4. `mkdir dist && mv release-assets/*.whl dist/`.
5. `astral-sh/attest-action@39b6ce43875c196a579e31635b11aa2a2036384a # v0.0.7`, with `paths: dist/*.whl`. It finds uv on the path, so its own setup-uv is skipped. It takes the job's ambient OIDC token and writes `dist/<wheel>.publish.attestation`.
6. **Only the wheel and its attestation.** `dist/` holds exactly one `*.whl` and exactly `<that wheel>.publish.attestation`, or the step fails.
7. `uv publish --no-config --trusted-publishing always dist/*`.

**The upload names `dist/*`, not `dist/*.whl`.** uv 0.13.5 uploads an attestation only when it is among the files named. With `dist/*.whl` it uploads the wheel alone, with no error (EXECUTED, `uv publish --dry-run -vv` on a wheel with its `.publish.attestation` beside it: "Found attestation for distribution" with `dist/*`, nothing with `dist/*.whl`). That is how 0.1.2's loss would have come back unseen. Step 6 is what keeps `dist/*` from naming anything else.

**What it accepts.** The signer's code (the action and its locked wheels) runs in the job that can mint a PyPI upload token, as in every project surveyed. That is the residual the first draft's separate job removed, and the owner accepted it with the common pattern. What bounds it: the action is pinned by commit, its `uv.lock` holds every wheel by SHA-256, `uv run --locked` installs nothing else, and the job runs only on a pushed tag with `PYPI_PUBLISH` on. The signer can also mint Sigstore certificates for `release.yml` at the tag, as `attest` can. GitHub's attestation store needs `attestations: write`, which `pypi` lacks, so `gh attestation verify` without `--bundle` is unaffected (the review's Low 9).

### 2. The job's uv is 0.13.5, by checksum

uv 0.9.22 to 0.12.5 refuse the action's lock (*Is this the practice*). 0.13.5 accepts it, and is the oldest such release at least two weeks old (released 2026-10-22). `pypi` runs it for the signature and the upload alike: one uv per job. The workflow's `UV_VERSION` stays 0.9.22 for every other job. Moving the whole workflow to 0.13 would change every job's tool, for a reason only the jobs that touch PyPI have.

`setup-uv@1c37ad07` (v10.3.0) holds a checksum for 0.9.22 and none for 0.13.5 (READ, `src/download/checksum/known-checksums.json` at that commit). So the job passes `checksum: f68d291c75783122dad58ab77def0e13f3233f358731db5d6d7e8715603b928f`, the SHA-256 of `uv-x86_64-unknown-linux-gnu.tar.gz` at 0.13.5. It is the release's own `.sha256` file and the archive's hash, which agree (EXECUTED). The scan holds both as constants, `ATTEST_UV_VERSION` and `ATTEST_UV_SHA256` (the review's Low 5).

The action's licence is MIT OR Apache-2.0 (READ). It runs as a release tool on GitHub's runner and ships nothing in the wheel, so §4.12 does not apply. Moving its pin, or the uv pin, is a change to the release recipe, reviewed as one, and the rehearsal (Decision 4) runs it before any tag does.

### 3. The workflow's own settings reach the signer

Every job inherits the workflow's `env:`: `UV_LOCKED=1`, `UV_PYTHON=3.14.2` and `UV_BUILD_CONSTRAINT=release/build-constraints.txt`. uv reads the constraint file before it resolves anything, so a job that checks out `.github/actions` alone fails the action's `uv run` with "File not found: release/build-constraints.txt" (the review's High 1, EXECUTED by the reviewer). Every job here that runs the action's lock checks out the `release` folder too. With it present, the action's lock installs on uv's managed CPython 3.14.2 (EXECUTED by the reviewer: exit 0, pypi-attestations 0.0.30, sigstore 4.5.1). The top-level `env:` stays as it is; it is held to `release/set_key.py`'s `ENV`.

`uv publish --no-config` reads none of the three.

### 4. A rehearsal runs the path before the tag

Nothing before a tag ever reaches `pypi`, so a slip in it would only show after `publish` has made the GitHub release (the review's Medium 2). A new job, `pypi-rehearsal`, runs on every run of the release shape (`needs.plan.outputs.rebuild == 'true'`: the release pull request into `main`, a dispatch, the weekly run and the tag). It needs the plan and `build`. Its permissions are `contents: read` alone, and `timeout-minutes: 20`. It never signs and never uploads. **On a tag, `attest` needs it** (round two's N1). So a PyPI path that broke between the release pull request and the tag (Sigstore's trust root or signing config, the managed CPython, PyPI's APIs) stops the tag before anything is signed or published, and a re-run of the same run carries on once it passes.

It runs what `pypi` and `pypi-verify` run, as they run it: the same checkout (with `release`), the same uv by checksum, the workflow's own `env:`, and the action's tree at the same commit (checked out into `attest-action/`). Then:

1. `uv run --locked --no-dev --project attest-action python -I -c "import pypi_attestations, sigstore"`: the lock installs under the release's settings.
2. `python3 -I release/pypi_readback.py rehearse`: the read-back (Decision 5) on 0.1.1's wheel, whose provenance on PyPI names `ClayGendron/wasi-python`, `release.yml` and `pypi`, and whose SHA-256 is `191f22a3320a71e471ad202c7e98d60ed4c647f0ba3866a20d96dc29a1715547` (READ, 148's landing notes).
3. `uv run --locked --no-dev --project attest-action python -I -m pypi_attestations verify pypi --repository https://github.com/ClayGendron/wasi-python pypi:wasi_python-0.1.1-py3-none-any.whl`: the signature check, through Sigstore's trust root.
4. The build's files through the local action; `mkdir dist && mv release-assets/*.whl dist/`; a stand-in `dist/<wheel>.publish.attestation` holding `{}`; the staging check of Decision 1 exactly; and `uv publish --no-config --trusted-publishing never --dry-run -vv dist/*`, whose log must hold "Found attestation for distribution". A dry run reads the wheel's own metadata, so it runs on the build's real wheel, not a placeholder (EXECUTED: a renamed foreign wheel is refused, "does not start with the normalized package name"); with no token it exits 0 (EXECUTED, the author and round two).

That exercises everything but the signature and the token exchange. The release pull request of 0.1.4 runs it before the tag is pushed. A weekly run makes a handful of requests to PyPI and Sigstore, once.

### 5. `pypi-verify` reads PyPI back, and fails closed

A new job, `pypi-verify`, after `pypi`, needing `build` and `pypi` (it reads the build's outputs through the local action), with the same `if:`, `contents: read` alone, and `timeout-minutes: 15`. `pypi` itself gains `timeout-minutes: 20`, since it holds `id-token` while the action runs. It checks out as `pypi` does, checks out the action's tree into `attest-action/`, sets up uv as `pypi` does, and reads the build's files through the action. Then two steps, each `set -eu`, and neither holds `||` or `set +e`:

1. `python3 -I release/pypi_readback.py check --sums release-assets/SHA256SUMS --repository "$GITHUB_REPOSITORY"`, the version from `GITHUB_REF_NAME`. The script, standard library only, with a 30-second timeout on every request:
   - finds the one wheel in `SHA256SUMS`;
   - reads PyPI's JSON API for the version, and requires that file with that SHA-256;
   - reads the Integrity API's provenance for the file, and requires at least one attestation bundle whose publisher is `{kind: GitHub, repository: <repository>, workflow: release.yml, environment: pypi}` (the review's Low 7: the CLI prints OK on a provenance with no bundles, and does not check the workflow);
   - requires the Simple API (`/simple/wasi-python/`, JSON form) to list the file, since the signature check below finds the file there, behind its own cache (round two's N2);
   - tries up to six times, thirty seconds apart, while an answer says something is not there yet (a 404, a file not listed, no connection), and exits 1 with one line naming what is missing after the sixth. An answer that is there and wrong (a digest, a publisher, a matching bundle with no attestation) fails at once.
2. `uv run --locked --no-dev --project attest-action python -I -m pypi_attestations verify pypi --repository "https://github.com/$GITHUB_REPOSITORY" "pypi:$wheel"`: the signature over PyPI's own bytes, through Sigstore's trust root, the wheel's name read from `release-assets/`.

The six tries wait for PyPI to show our own upload, once per release. They are not retries against a host that is down, which the project's rule on third-party hosts forbids on a timer: they end after three minutes and the run is red (round two's N4).

A miss fails the job, and `ci-status` with it, so the tag's run is red (the review's Medium 3). The same script on 0.1.3 exits 1: no provenance (EXECUTED once built, criterion 2). That is how 0.1.2's loss would have been seen on its day.

`pypi-verify` uploads nothing, so a read that timed out is re-run alone.

### 6. The rules hold it

`tests/harness/scan.py`'s rule 20, `pypi_upload_errors`, becomes PyPI's signature and upload:

- `pypi` uses only checkout, setup-uv, the local action and `astral-sh/attest-action@ATTEST_ACTION_SHA`, the action exactly once with `paths: dist/*.whl` and no other input, after the local action and before the upload.
- setup-uv in `pypi` is `version: ATTEST_UV_VERSION` with `checksum: ATTEST_UV_SHA256` (in place of `${{ env.UV_VERSION }}`).
- The checkout's sparse list holds `release`.
- A step between the action and the upload holds `dist/` to the wheel and its attestation (the scan constant `PYPI_STAGE_CHECK`).
- The upload names `dist/*` and no other file; `--no-attestations` joins the flags it may not carry.
- Unchanged: no `env:`, no `$GITHUB_ENV` or `$GITHUB_PATH`, `--no-config`, `--trusted-publishing always`, no container or service anywhere.

A new rule 21, `pypi_readback_errors`:

- `pypi-verify` exists, its `if:` is `PYPI_IF`, it needs `pypi`, its permissions are `contents: read`, and it has a `timeout-minutes:`.
- It runs exactly the two commands of Decision 5, as scan constants, and no step of it holds `||` or `set +e`.
- `pypi-rehearsal` exists, needs the plan and `build`, its `if:` is `needs.plan.outputs.rebuild == 'true'`, its permissions are `contents: read`, it has a `timeout-minutes:`, and it runs exactly the commands of Decision 4, as scan constants. The attestation scan requires `attest` to need it.
- Both check out `astral-sh/attest-action` at `ATTEST_ACTION_SHA` into `attest-action` with `persist-credentials: false`, and set up uv as `pypi` does.

Changed elsewhere: `JOB_PERMISSIONS` gains the two jobs (rule 14). The checkout scan admits the action's checkout at `ATTEST_ACTION_SHA`, in those two jobs alone, as the one checkout not at `HEAD_REF`. `TAG_JOBS` gains `pypi-verify`, which only a pushed tag reaches. `ci-status` already needs every other job. `pypi-rehearsal` is not among the jobs `accept-record` may leave out, so `accept-record` needs it: the release pull request's acceptance waits on a green rehearsal, which is wanted, since a release whose PyPI path fails should not be accepted (round two's N5). On a merge into `dev` the rehearsal is skipped and holds nothing up. `test_rules.py`'s list of the jobs a tag runs gains it.

`tests/unit/test_scan.py`: the good fixture gains the new `pypi` and both jobs, plus one binding row per clause, each naming its rule. `tests/unit/test_pypi_readback.py`: the script's verdicts on recorded answers (a good wheel, a wrong digest, no file, no provenance, a provenance with no bundles, another repository, another workflow, another environment, a 404 that turns into a pass on the third try, six 404s), with the fetch replaced and no network. Each is seen failing first.

### 7. A release keeps every proof of origin its predecessor carried

A project rule in `AGENTS.md`, under "Rules that bind all work", in the words the review's Low 6 asked for:

> **A release keeps every proof of origin the last one carried** (the owner, 2026-11-05, after 0.1.2 and 0.1.3 reached PyPI without the provenance 0.1.1 had, and PyPI's page warned of it). The GitHub attestation of every asset, PyPI's provenance for the wheel and `SHA256SUMS` are public, and readers compare releases. A change that would drop or weaken one is asked of the owner with AskUserQuestion, and the question says what the reader will see where it shows (PyPI's page, the release page), read from that page, not inferred. The release verifies the GitHub attestations before it publishes and reads PyPI's digest and provenance back after it uploads, and it is red when one is missing.

Rules 20 and 21 hold the letter of it for PyPI. The `AGENTS.md` rule holds its spirit for anything new.

### 8. The pages

- `docs/how-to/verify-a-download.md`: "From 0.1.2 the wheel on PyPI carries no PyPI provenance…" becomes this. 0.1.2 and 0.1.3 on PyPI carry no PyPI provenance, and their GitHub attestation covers the same file. From 0.1.4 the wheel on PyPI carries PyPI provenance too, and one command checks it.
- `docs/contributing/release-process.md`: stage 7 says the wheel is signed for PyPI and uploaded with its signature, then read back. The release-shape runs rehearse it. "After a release" stops asking for PyPI's digest by hand and asks the maintainer to open PyPI's file page and see the provenance panel. Recovery, from the review's Low 8: `pypi-verify` uploads nothing and is re-run alone; a re-run of a failed `pypi` signs again, which is a new public signature and harmless; when PyPI refuses the attestation, the fix lands in `dev` and the wheel reaches PyPI with the next patch release.

### 9. PyPI's publishers

The owner reads the project's Publishing page on PyPI once, and removes any trusted publisher, or pending publisher, that is not this repository's `release.yml` in the environment `pypi`. 148's history records five attempts at 0.1.1's publisher. The review's Medium 4 asked for this when the signer was meant to run outside the environment. With the signer inside `pypi` it is no longer this design's premise, but a stray publisher with no environment would let any job of the workflow with `id-token` upload. The owner's reading goes in the landing notes.

## Design

Files: `.github/workflows/release.yml` (`pypi`, `pypi-verify`, `pypi-rehearsal`, `attest`'s needs, `accept-record`'s and `ci-status`'s needs); `release/pypi_readback.py` (new, standard library only); `tests/harness/scan.py` (`ATTEST_*`, `PYPI_STAGE_*`, `READBACK_*`, `REHEARSAL_*`; `pypi_upload_errors`, rule 20; `pypi_readback_errors`, rule 21; `JOB_PERMISSIONS`, `TAG_JOBS`, `checkout_ref_errors`, `release_attestation_errors`); `tests/unit/test_scan.py` (the fixtures and the rows); `tests/unit/test_pypi_readback.py` (new); `tests/checks/test_rules.py` (`TAG_RUN`); `docs/how-to/verify-a-download.md`; `docs/contributing/release-process.md`; `AGENTS.md`; `context/decisions.md`; `context/upstream/35-attest-action-uv-range/`.

## Intent

Every wheel this project puts on PyPI carries PyPI provenance that names this repository, `release.yml` and the `pypi` environment. The path is rehearsed on every release-shaped run before a tag. A tag whose wheel lands on PyPI without provenance that verifies is red the same day.

## Scope

In: `pypi`'s signature, staging and upload; `pypi-verify`; `pypi-rehearsal`; `release/pypi_readback.py` and its unit tests; rules 20 and 21 and the changed rules with their unit rows; the two pages; the `AGENTS.md` rule; the decision; the drafted upstream issue. Out: 0.1.2 and 0.1.3 on PyPI, which cannot change (the owner: leave them); the 0.1.4 release itself, its own release pull request; a PEP 740 attestation for the `.tar.xz` set, which does not go to PyPI; moving the workflow's `UV_VERSION`.

## Acceptance criteria

1. Rules 20 and 21 hold the real workflow and name each mutant, and `test_pypi_readback.py`'s rows hold; each was seen failing first. EXECUTED.
2. In this container: with uv 0.13.5 and the workflow's `env:`, the action's lock imports `pypi_attestations` and `sigstore`, and uv 0.9.22 refuses it; `pypi_readback.py check` on 0.1.3 exits 1 for lack of provenance, and `pypi_readback.py rehearse` passes on 0.1.1. EXECUTED. The signature checks need Sigstore's trust root, which this sandbox's network refuses; they are read from the release pull request's `pypi-rehearsal` (criterion 4).
3. The pages say what Decisions 7 and 8 say. READ.
4. The fast tier, `tests/lint` and the pull request's `ci-status` are green, and the news file is present. The 0.1.4 release pull request's `pypi-rehearsal` is green (READ from that run).
5. The 0.1.4 tag's run is green with `pypi` and `pypi-verify`, and PyPI's Integrity API returns provenance for the 0.1.4 wheel naming `ClayGendron/wasi-python`, `release.yml` and `pypi` (READ from that run and the API, named in the landing notes then).

## Landing notes

Built 2026-11-05 on `spec/185-the-wheel-on-pypi-carries-its-provenance`, from `dev` at `7ed71049`, after both pre-build rounds (`../reviews/185-the-wheel-on-pypi-carries-its-provenance-spec-2026-11-05.md`). Landed 2026-11-05 by squash merge of #100 as `10bc0c9d`, on the pull request's green run 42073893110 at `ea3e5e1b` and the review `../reviews/185-the-wheel-on-pypi-carries-its-provenance-pr-2026-11-05.md` ("Lands at 025971bf"); the post-merge run 42082118627 was green and accepted as `43d733fb`.

- **Base state.** The fast tier on `dev` at `7ed71049`, in this container: 4 failed, 3,764 passed, all four from running as root (`modes refuse nothing to root`, and `test_the_walk_judges_links`), which GitHub's runners do not. After the build: the same 4 failed, 3,811 passed; `tests/lint` 14 passed; `ruff check` and `ruff format --check` clean (EXECUTED).
- **Seen failing first.** `tests/unit/test_pypi_readback.py` errored on collection with no script (EXECUTED). `tests/unit/test_scan.py`, run in a copy of `dev`'s tree with only the new constants added to its `scan.py` (constants change no rule): 97 rows failed, the new good fixture among them, red on rules 14 and 20 (EXECUTED). The real workflow, before the scan changed, was red on rule 14 (two jobs), rule 20 (`pypi`'s setup-uv, `pypi uses astral-sh/attest-action@…`), the checkout scan (two jobs) and the plan gate (EXECUTED).
- **The read-back on the real PyPI** (criterion 2). `pypi_readback.py rehearse`: "ok: wasi_python-0.1.1-py3-none-any.whl on PyPI has the release's SHA-256 and provenance from ClayGendron/wasi-python", exit 0. `check` on 0.1.3's wheel with PyPI's own digest: "FAIL: after 6 tries, the Integrity API answered 404", exit 1 (EXECUTED). The lock with uv 0.13.5 imports `pypi_attestations` 0.0.30 and `sigstore` 4.5.1; uv 0.9.22 to 0.12.5 refuse it (EXECUTED). `verify pypi` on 0.1.3 from the lock exits 1, "Provenance for file … was not found" (EXECUTED).
- **The upload's files.** uv 0.13.5 `uv publish --dry-run -vv`: "Found attestation for distribution" with `dist/*`, nothing with `dist/*.whl`; with `--trusted-publishing never` and the build's kind of wheel it exits 0 offline; a foreign wheel renamed is refused for its metadata (EXECUTED).
- **The signer's pin** (the 0.1.4 security review's L2). `git ls-remote https://github.com/astral-sh/attest-action 'refs/tags/v0.0.7*'`, once by hand on 2026-11-05: `39b6ce43875c196a579e31635b11aa2a2036384a refs/tags/v0.0.7`, the commit the workflow pins; its `uv.lock` pins `pypi-attestations` 0.0.30 (EXECUTED).
- **PyPI's publishers** (Decision 9). The owner read PyPI's Publishing page on 2026-11-05 and pruned it to one trusted publisher: ClayGendron/wasi-python, `release.yml`, environment `pypi` (`../decisions.md`, "PyPI provenance comes back").
- **0.1.4 on the tag** (criteria 4 and 5). The release pull request #102's run on `a67c5585` was green, 145 jobs, `pypi-rehearsal` among them; its acceptance is `ad5dbdf7`, which `main` moved to and the owner tagged `v0.1.4` (annotated, `f5a06e6b`) on 2026-11-05. The tag's run 42110186903: `pypi` green, so the wheel went up with its attestation; the GitHub release published 21:45:30 UTC with `SHA256SUMS`, the `.tar.xz` and the wheel. In `pypi-verify`, `pypi_readback.py check` passed on its second try ("try 1 of 6: the Simple API lists no wasi_python-0.1.4-py3-none-any.whl yet", then "ok: … has the release's SHA-256 and provenance from ClayGendron/wasi-python"); the signature check that follows exited 1, "Could not find the artifact 'wasi_python-0.1.4-py3-none-any.whl' on PyPI", seconds later, a Simple API page that still lagged for the client it uses (EXECUTED, the job's log). Read by hand after the run, once each: the Integrity API holds one bundle, publisher `{kind: GitHub, repository: ClayGendron/wasi-python, workflow: release.yml, environment: pypi}`, one attestation; both Simple API forms list the wheel; the JSON API's SHA-256 `e34d6bf4c3c7ad6fbbcf3c81a6a418cfc24eb47129e715a23a7f8076a11da079` (112,146,034 bytes) is the release's `SHA256SUMS` line (EXECUTED). The signature itself could not be checked from the agent's sandbox, which cannot reach Sigstore's trust root (`TUFError`); PyPI verified the attestation when it accepted the upload. The re-run of `pypi-verify` alone was offered, and the owner chose to leave the run red (`../decisions.md`, "PyPI provenance comes back"). The signature check waiting for PyPI's index is a roadmap line before 0.1.5.
- **Still to read.** The provenance panel on PyPI's page for the 0.1.4 file, as a reader sees it (`docs/contributing/release-process.md`, "After publishing"), by the owner.
