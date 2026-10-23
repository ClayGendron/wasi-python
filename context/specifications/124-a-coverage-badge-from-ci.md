# 124: A coverage badge from CI

- **Status:** **built 2026-10-23 on `wave/13`**; drafted and built the night before the 0.1.0 tag on the owner's instruction (2026-10-22, "lets make it CI based please"; Codecov chosen by the owner the same night). Reviewed with 125 by one fresh agent (Landing notes).
- **Date:** 2026-10-22
- **Owner:** Clay Gendron
- **Kind:** **build-class** (it adds a job to the release workflow) and a **judge change** (`tests/`, `pyproject.toml`, `uv.lock`). Not structural: `src/` is unchanged.
- **Depends on:** 122 (the short README, whose badge row this adds to; the limitations page the `-V` checks now read). Landed and unchanged: 002 (the judge), 052 (the fast tier's parallel runs), 102 (the release tier).
- **Research it stands on:** none written; the facts are below, each labelled. The owner's decisions of 2026-10-22, given in the session: a coverage badge, measured in CI, served by Codecov; no downloads badge (an earlier decision).

## Decisions

1. **Measured in CI, served by Codecov** (the owner). A first design kept a record in `context/` that a rules check held equal to a static badge; the owner asked for CI to own the number and chose Codecov over a badges branch or the docs site. So nothing in the tree holds the percent and nothing can drift from it.
2. **The fast tier is what is measured.** `uv run pytest -m "not slow"` serially under coverage.py, `--source=src/wasi_python`. The slow tier's guest jobs exercise the guest, not the runner's lines, and the packages' own suites run in the sandbox; neither is the runner's coverage.
3. **coverage.py 7.17.0, pinned exactly** in the `dev` group, as pytest-xdist and mypy are: a coverage release can change which lines count.
4. **`COVERAGE_CORE=sysmon` on Python 3.12 and later.** The default tracer ran the fast tier about ten times slower (EXECUTED: 18% of the tests after 35 minutes on darwin-arm64, killed); with sysmon the serial run took 23 min 35 s (EXECUTED, 2026-10-22, 3,196 passed).
5. **A token, not OIDC.** The owner added `CODECOV_TOKEN` to the repository's secrets (READ, `gh secret list`), so the job keeps `contents: read` alone and needs no `id-token: write`.
6. **Nothing needs the job.** A Codecov outage or a failed upload shows red in the run and never holds up `attest`, `publish` or `pypi`. A red coverage job is still a red run, which rule 6b's "every job passes" reads.
7. **The `-V` sentence and numpy's integer width move to the limitations page.** 122's README dropped the `-V` blockquote; `test_version_states_the_platform_semantics` and `test_default_integer_width_is_documented` now read `docs/reference/limitations.md`, which states both.

## Intent

The README shows how much of the runner the fast tier runs, the number comes from the release workflow on every run, and no person or agent writes it.

## Design

- `tests/harness/coverage.py --measure`: runs the fast tier under coverage.py into `build/coverage/` (`.coverage`, `pytest.log`, `coverage.json`, `coverage.xml`), prints the percent, and exits non-zero when the pytest summary names a failure or an error. `--check`: the README carries exactly one Codecov badge and it is `BADGE_TAG`, this repository's.
- `.github/workflows/release.yml`, job `coverage` (needs `build`): checks out, verifies and unpacks the set the build job handed on exactly as `judge-linux` does, runs `--measure`, uploads `build/coverage/` as `coverage-<attempt>` whatever happens, then `codecov/codecov-action` v7.1.1 pinned by commit `303a32d7a59b442fa8d48b6a1cc6825c09c847a5` (READ, `gh api` on the annotated tag) with `files: build/coverage/coverage.xml`, `disable_search: true`, the token, `fail_ci_if_error: true`. `tests/harness/scan.py`'s `JOB_PERMISSIONS` gains its row, `contents: read`.
- `README.md`: Codecov's badge after the licence badge, linking to the repository's Codecov page.
- `tests/checks/test_rules.py::test_readme_carries_the_codecov_badge` holds the badge.
- `AGENTS.md` rule 6b names no local measurement; `docs/contributing/first-change.md` says where the number comes from.

## Scope

In: the above. Out: a coverage threshold that fails a run (the number is reported, not gated); per-line reports in the README; coverage of the guest.

## Acceptance criteria

1. `tests/unit/test_coverage.py` passes (14 rows: the summary reader, a red run refused, the badge found once and only this repository's).
2. `test_readme_carries_the_codecov_badge` and `test_the_release_signs_and_publishes_what_build_made` pass; `tests/unit/test_scan.py::test_the_real_workflow_passes_every_release_scan` passes.
3. The release workflow's `coverage` job is green on the branch run and on the dry run, and Codecov shows the commit.

## Landing notes

- Fast tier, darwin-arm64, before the job's permission row: 2 failed (the permission row, as expected), 3,174 passed (EXECUTED, `build/fast-tier-wave13.log`); both rows pass by node id after it.
- The first local measurement found four failures, none in the runner: a docstring line over 100 columns, a `context/` path in a code docstring, the old record check judging its own run, and `recipes/patches/README.md` rewrapped by the paragraph rule though `MANIFEST` hashes it (the artifact set read stale). The last was restored to its committed text and `tests/harness/wrap.py` skips `recipes/`.
- The review, the branch run and the dry run are recorded with 125's.
