# 180: A tag stops before it signs a wheel PyPI would refuse

- **Status:** built 2026-11-01 on `spec/180-a-tag-stops-before-it-signs-a-wheel-pypi-would-refuse`, from `dev` at `0d105cc1`, not landed. Asked for on 2026-11-01 by the orchestrating session, to close Medium M1 and Low L1 of the 0.1.3 release security review (`../reviews/0.1.3-security-review-2026-11-01.md`), which the release waits on.
- **Date:** 2026-11-01
- **Owner:** Clay Gendron
- **Kind:** **build-class** (the release workflow's tag path, one step in the `judged` job; its rules in `tests/harness/scan.py` and `tests/checks/test_rules.py`; the release page). Not structural: nothing under `src/` changes. No wasm build, and nothing the build makes changes.
- **Depends on:** 155 (the `judged` job, which only a pushed tag runs, before `attest` and `publish`); the owner's decision of 2026-11-01, "The wheel's check allows 256 MiB" (`../decisions.md`).
- **Research it stands on:** the security review's M1 and L1, which name this fix; specification 155's Decision 2; PyPI's file limit (https://pypi.org/help/#file-size-limit).

Labels: EXECUTED, run and seen; READ, read from a file, cited; INFERRED, reasoned.

## The problem

The owner's decision of 2026-11-01 raised the judge's wheel limit, `tests/harness/artifacts.py`'s `PYPI_FILE_LIMIT`, to 268,435,456 bytes (256 MiB, the limit asked of PyPI), and said the upload to PyPI waits for PyPI's approval (READ). The judge runs on a pull request, not on a tag. A tag's run signs every asset (`attest`, a signature permanent in Sigstore's public log), then makes the GitHub release (`publish`), then uploads the wheel to PyPI (`pypi`, only when the repository variable `PYPI_PUBLISH` is `true`) (READ, `.github/workflows/release.yml`). Nothing before `attest` compares the wheel with the limit PyPI has granted. The wheel measured 104,899,641 bytes at 174, past PyPI's default of 104,857,600 (READ, the review's M1).

So a tag pushed before PyPI's grant, or by a maintainer who read the wrong number, half-publishes: 0.1.3 is signed and on GitHub, PyPI refuses the file, and `pip install wasi-python==0.1.3` fails for every embedder. The only guard today is a sentence in the decision and a comparison by hand (`docs/contributing/release-process.md`, step 4).

The release page also says a failed PyPI upload cannot be helped by a re-run (L1). For a refusal for size, once PyPI has raised the limit, a re-run of the failed `pypi` job, within 30 days of the tag's run (GitHub's limit on re-runs), uploads the same wheel (INFERRED, the review).

## Decisions

### 1. The step sits in `judged`

A step in the `judged` job, after the build's files are downloaded and checked, and before the proof of the set. `judged` is the right place, for four reasons:

- It runs on a pushed tag alone (`needs.plan.outputs.publish == 'true'`), so it never runs on a pull request, the weekly run or a dispatch, where nothing uploads.
- `attest` and `publish` already need it, and the rules hold that they do (`tag_run_errors`). A red step there stops the signature and the release with no new job and no new `needs:`.
- It already has the build's files, through the `verify-artifact` action, checked against the SHA-256 of `SHA256SUMS` the build handed on, so the wheel it measures is the wheel `pypi` uploads.
- It is the job whose purpose is "nothing is signed or published unless this passes". A new job beside it would duplicate the download and the guards for one comparison.

Moving `pypi` before `attest` and `publish` (the review's other option) is not chosen: the upload would then be unsigned when it lands, and a PyPI failure would still leave the tag half-done the other way round.

### 2. When it applies

Only when the tag uploads to PyPI. The step's environment carries `TO_PYPI: ${{ vars.PYPI_PUBLISH == 'true' }}`, the `pypi` job's own condition, evaluated by the same expression, so the two agree unless the variable changes during the run, since each job reads it when it starts (GitHub compares the strings without regard to case, and the step reads the expression's result, not the variable). When it is not `true`, the step passes at any size: the GitHub release takes a wheel larger than PyPI's limit. The step has no `if:`, so it runs on every tag and says which way it went in its log.

### 3. The granted limit is a repository variable

`PYPI_FILE_LIMIT_GRANTED`, in bytes. Unset or empty, the limit is 104,857,600, PyPI's default, so a repository that never set it is safe. A value that is not a plain whole number (a letter, a sign, a leading zero, zero itself, or more than fifteen digits, which `[` could not compare) is refused, and the run stops: a typo never opens the gate.

A constant in a file that a recorded decision moves was the other choice. The variable is chosen because it keeps the owner's action to one place, beside `PYPI_PUBLISH`, the other setting that says what PyPI takes:

- PyPI's grant arrives by email, at a time of PyPI's choosing, possibly after the release pull request is green. A constant in the tree would need a pull request into `dev`, and then a new release pull request, since the tag's tree must be the judged tree plus its acceptance. The variable is one command, `gh variable set PYPI_FILE_LIMIT_GRANTED --body <bytes>`, run by the owner, at any time.
- A run the step stopped is re-run once the variable is set (Decision 4), with nothing signed in between.
- The judge's `PYPI_FILE_LIMIT` stays a constant: it bounds what a merge may grow to and is the owner's decision of 2026-11-01. The variable bounds what a tag may upload today. The two meet when PyPI grants 256 MiB.

Setting the variable is the owner's to do, as `PYPI_PUBLISH` is. No agent runs `gh variable set`.

### 4. A run it stopped, and a refusal at PyPI

When the step stops a tag's run, nothing is signed or published. Once PyPI has raised the limit and the variable holds it, the maintainer re-runs the failed jobs of the same run: `judged` reads the variable again (INFERRED: GitHub's documents do not say whether a re-run reads `vars` afresh), and `attest`, `publish` and `pypi` follow. If the maintainer chooses instead to release on GitHub alone, `PYPI_PUBLISH` off and a re-run do it (INFERRED, the same). The step's failure prints the first of these and the limit it read; if a re-run still shows the old limit, the tag is not pushed again and the wheel waits for the next patch release.

If PyPI still refuses the file for size (a grant recorded wrong), re-running the failed `pypi` job after PyPI raises the limit, within 30 days of the tag's run, uploads the same wheel. The release page says both (L1).

### 5. The checks

- **Behaviour** (`tests/checks/test_rules.py::test_a_tag_refuses_a_wheel_past_pypis_grant`): the step's own script, run in bash on a sparse wheel of each size, in twelve cases: no upload with a wheel past the default passes; the default with a wheel at it passes and one byte past refuses; 256 MiB granted with a wheel past the default passes and one byte past 256 MiB refuses; a grant that is not a number, zero, with a leading zero, thirty digits long or negative refuses; no wheel and two wheels refuse. Its absence fails every case (`workflow_step_script` raises).
- **Shape** (`tag_run_errors`, held by `test_a_tag_publishes_what_the_release_pull_request_judged`): `judged` runs the step exactly once, with no `if:`, and with exactly the environment of Decisions 2 and 3; the condition is the scan's `PYPI_CONDITION`, the same constant `pypi`'s rule 18 holds its `if:` to. The step carries no `continue-on-error:` either, which would let `judged` succeed past a refusal. Six mutants in `tests/unit/test_scan.py`: the condition without `== 'true'`, no condition, a literal limit, an `if:` on the step, the step renamed, `continue-on-error: true` on the step.

## Intent

No tag signs or publishes a wheel PyPI would refuse. A tag that would is stopped in `judged`, with nothing signed, and goes on by a re-run once PyPI's grant is in the repository variable.

## Design

Files: `.github/workflows/release.yml` (the step in `judged`, the comments of `judged` and `pypi`), `tests/harness/scan.py` (`PYPI_CONDITION`, `PYPI_LIMIT_STEP`, `PYPI_LIMIT_ENV`, and `tag_run_errors`'s rule), `tests/checks/test_rules.py` (the behaviour rows), `tests/unit/test_scan.py` (the six mutants), `docs/contributing/release-process.md`, `context/changes/180-a-tag-stops-before-it-signs-a-wheel-pypi-would-refuse.md`.

## Scope

In: the step, its two checks, the comments of `judged` and `pypi`, the release page's step 4, its stage 5 and its paragraph on a failed upload. Out: the release pull request's own run comparing the wheel with the grant, which would warn earlier but cannot stop a tag (the release pull request's run never uploads); L3's comparison of the published wheel with the judged one.

## Acceptance criteria

1. The step's twelve cases hold (Decision 5), each seen failing before the step existed. EXECUTED.
2. `tag_run_errors` holds the real workflow, names each of the six mutants, and was seen failing on the real workflow before the step existed. EXECUTED.
3. The release page says what the step does in step 4 and stage 5, and that a refusal for size is re-run once PyPI has raised the limit. READ.
4. The fast tier, `tests/lint` and the pull request's `ci-status` are green; the news file is present.
5. The next tag that uploads to PyPI logs the comparison in `judged` (READ from that run, named in the landing notes then).

## Landing notes

Built 2026-11-01, before its pull request and review.

- **Seen failing first.** With the checks written and the workflow unchanged, the twelve behaviour rows failed with "judged has no step named …", `test_a_tag_publishes_what_the_release_pull_request_judged` failed on the real workflow, and `tests/unit/test_scan.py` failed six rows: the real workflow and the five mutants (EXECUTED). With the step in place, all pass. Round 1's sixth mutant, `continue-on-error: true` on the step, failed against the scan before the scan refused it (EXECUTED).
- **A comment placement the scan reads.** `workflow_steps` ends a job's steps at a line indented six spaces that is not a step, so the step's comment sits inside it, below its name, as the `verify` job's comment does.
- **The re-run reads the variable again** (INFERRED). GitHub evaluates `vars` when a job starts, and a re-run of failed jobs starts them again; GitHub's documents say a re-run keeps the first run's actor, `GITHUB_SHA` and `GITHUB_REF`, within 30 days, and nothing of `vars`. If a re-run were to read the old value, a dispatch cannot help (a tag's publish needs the push event), so the next tag would be a patch release; the release page and the step's message say so. The first stopped run will say which.
- **Pre-build review.** The change does not touch the guest's imports or exports, the artifact set or the build recipe (constitution §5.6): it adds a comparison to the tag's path and changes nothing built. The design is the one the security review's M1 named as its closing; the pull request's review reads it.
