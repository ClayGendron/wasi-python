# Review of 180 — a tag stops before it signs a wheel PyPI would refuse

- **Date:** 2026-11-01
- **Reviewer:** an agent (Claude), a fresh sub-agent of the orchestrating session; not the author
- **Reviewed:** `0d105cc1..75ad1592` (`5c3bf69d`, the change; `75ad1592`, round 1's fix commit): `.github/workflows/release.yml`, `tests/harness/scan.py`, `tests/checks/test_rules.py`, `tests/unit/test_scan.py`, `docs/contributing/release-process.md`, the specification and its news file; the description; the security review's M1 and L1; specification 155; the decision "The wheel's check allows 256 MiB"; constitution §5.5 and §5.6.
- **Run:** 41332993703 on `75ad1592`. Every job is green; only `review` and `ci-status` were red, and the plan's sole refusal is this missing file. That is the orchestrator's reading of the run: this reviewer's one `gh` call went to the description, so it is READ through the orchestrator.
- **Windows legs:** all 13 windows-2025 legs of run 41332993703 green (the orchestrator's reading, as above).
- **Re-ran:** at `5c3bf69d`: the twelve new rows, the tag-run rule and the scan's tag rows → 53 passed, exit 0; `uv run pytest -q tests/checks/test_rules.py tests/unit/test_scan.py tests/unit/test_ci_plan.py` → 931 passed, 2 skipped at `5c3bf69d`, 932 passed, 2 skipped at `75ad1592`, exit 0; `uv run pytest tests/lint -q` → 14 passed, exit 0; `ruff check` and `ruff format --check` on `src` and `tests` clean. Seen failing first: on `dev`'s `release.yml` (`0d105cc1`), `scan.tag_run_errors` names the missing step and `scan.workflow_step_script` raises `LookupError`, so every behaviour row fails (EXECUTED).
- **Box:** 45 minutes (build-class).

## Acceptance criteria against evidence

1. The twelve cases hold, each seen failing first — met: 12 passed, and on `dev`'s workflow the script lookup raises, so each row fails (EXECUTED).
2. `tag_run_errors` holds the real workflow, names the five mutants, and failed before the step — met: the scan rows pass and `tag_run_errors` on `dev`'s text returns the step's error (EXECUTED). It does not hold `continue-on-error:` on the step (finding 3).
3. The release page says what the step does in step 4 and stage 5, and that a refusal for size is re-run — met as text (READ), but two of its promises are not evidenced (findings 1 and 2).
4. Fast tier, `tests/lint`, `ci-status` green; news file present — lint and the rules rows green (EXECUTED); the news file's claim matches the diff (READ); `ci-status` pending.
5. The next uploading tag logs the comparison — not yet, by design.

The questions put to this review:

- **(a) Does a re-run read an updated repository variable?** Unknown. GitHub's re-run page says a re-run keeps the first actor's privileges, `GITHUB_SHA` and `GITHUB_REF`, within 30 days; neither it nor the variables reference says anything of `vars` (READ, docs.github.com; nothing else probed). The specification labels this INFERRED, which is right. The release page and the step's own failure message state it as fact (finding 1).
- **(b) Does 155's pre-build review precedent apply?** No; a note, nothing follows. §5.6 asks for one when a change touches the guest's imports or exports, the artifact set or the build recipe. 155 had one because it reshaped what a tag builds and publishes and amended §5.5. 160 changed a `release.yml` job and had none. 180 changes nothing built; it adds one refusal before `attest`, so a wrong design only stops a tag unsigned. Its design is M1's own closing, and the landing notes say so.
- **Bypass:** none found in the glob or the wheel. `judged`, `pypi` and every other reader fetch the same artifact by id, held to the same SHA-256 of `SHA256SUMS`, with no other file allowed (`verify-artifact`). Both glob `release-assets/*.whl`; the step requires exactly one regular file, and an unmatched glob stays literal, so `-f` refuses (EXECUTED). A malformed grant fails closed and arrives through `env:`. The one bypass is `continue-on-error:` (finding 3).
- **At the limit:** a wheel exactly at the limit passes (`-gt`; row "the default, a wheel at it", EXECUTED). Warehouse refuses only when the size is greater than the limit, and its default is 100 × 1,048,576 bytes (INFERRED, from Warehouse's upload code as I know it; not probed).
- **Every tag:** yes. `judged` runs on every pushed tag, the step has no `if:` (held by the scan), `attest` and `publish` need `judged`, and `pypi` needs `publish`.

## Findings, most severe first

1. **The docs and the step promise that a re-run reads the new limit, and GitHub does not document that** (`docs/contributing/release-process.md:50`; `.github/workflows/release.yml:869`) — Medium (a guarantee not evidenced). Failure: the owner sets `PYPI_FILE_LIMIT_GRANTED` and re-runs the failed jobs. If GitHub serves the attempt the first run's `vars`, the step stops again on the old number, and the page offers no next step. Nothing is signed, so this costs time, not integrity. Fix text for line 50's last sentence: "If the `judged` job stopped the run for the wheel's size, nothing was signed or published. Set `PYPI_FILE_LIMIT_GRANTED` to the new limit and re-run the failed jobs. The step's log prints the limit it read; if it still shows the old one, do not push the tag again: the wheel waits for the next patch release." The step's second echo becomes "once PyPI grants more, set PYPI_FILE_LIMIT_GRANTED to it and re-run the failed jobs; this line prints the limit read". Evidence that would close it instead: a GitHub document, or the first stopped run's log, recorded in the landing notes. Decision 4's "`judged` reads the variable again" should carry INFERRED as its landing note does, and so should its "`PYPI_PUBLISH` off and a re-run".
2. **"Kept 90 days" suggests a 90-day window, but a re-run is allowed for 30** (`docs/contributing/release-process.md:50`; spec lines 18 and 53) — Low. Failure: PyPI grants in week six, and the maintainer, reading "kept 90 days", expects to re-run the `pypi` job. GitHub allows a re-run only within 30 days of the first run (READ, docs.github.com). Fix text: "re-run the failed `pypi` job within 30 days of the tag's run (GitHub's limit on re-runs), which uploads the same wheel." Line 73's "kept for 90 days" predates this change and has the same issue; it may follow.
3. **`continue-on-error:` on the step is not refused** (`tests/harness/scan.py:2496`) — Low. Failure: someone adds `continue-on-error: true` under the step's name. A wheel past the grant then fails the step, `judged` still succeeds, and `attest` signs. That is M1 again, and every rule stays green. Fix text: `or {"if", "continue-on-error"} & set(limit[0])` in place of `or "if" in limit[0]`, with a sixth mutant in `BAD_TAG_RUN` that adds `continue-on-error: true` below the step's name. A job-level `continue-on-error:` on `judged` is held for the rebuild jobs but not for `judged`. That gap is 155's and may follow.
4. **"The two can never disagree" overstates it** (spec line 35) — Low, `context/` only. `judged` and `pypi` each read `vars.PYPI_PUBLISH` when they start, minutes apart. If the owner turns the switch on mid-run, the wheel goes up without the comparison and PyPI refuses it (L1's case). Fix text: "so the two agree unless the variable changes during the run."
5. **Self-check: the Windows box is unchecked** — Low, as the README ranks it. Fix: read the Windows legs of the head's run and tick the box.

Notes, no finding: PyPI's grant usually arrives in MiB, and the variable is in bytes, so step 4 might say "N MiB is N × 1,048,576 bytes". PyPI also caps a project's total size (10 GiB unless raised, INFERRED). At about 100 MiB a wheel, that is far off.

## Constitution checks

- §4 constraints: no source, recipe, pin or artifact changes (§4.1 holds). The judge changes only by adding checks, and the judge hash records them. No `src/` change, so not structural (4a). The writing rules hold (lint, EXECUTED). 4b, `.github/workflows/release.yml`: one step in `judged`, which runs on a pushed tag alone and holds `contents: read`. The step holds no token, and its two inputs come through `env:`. It refuses a wheel past the grant, a grant that is not a plain whole number, and anything but exactly one wheel, all only when `vars.PYPI_PUBLISH == 'true'`. `pypi` changes only a comment.
- §7 never-do list: nothing tripped. Nothing sets the variable; that stays the owner's.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. The re-run promise — fixed in `75ad1592`: line 50 and the step's echo follow the fix text, Decision 4 marks both re-run claims INFERRED, and the landing notes quote GitHub's re-run page. Confirmed (READ; lint, EXECUTED).
2. 30 days — fixed in `75ad1592` on line 50 and the specification's lines 18 and 53; line 73 left, as allowed. Confirmed (READ).
3. `continue-on-error:` — fixed in `75ad1592`, with a sixth mutant and units 6. Confirmed: with `5c3bf69d`'s `scan.py` in a scratch copy of `75ad1592`, the mutant's row fails (1 failed, 23 passed, EXECUTED); at `75ad1592` it passes.
4. "Never disagree" — fixed in `75ad1592`, Decision 2. Confirmed (READ).
5. The Windows box — ticked by the author with run 41332993703, whose 13 windows-2025 legs are green. Confirmed against the orchestrator's reading of the run.

## Verdict

Lands on 75ad1592: the step stops a tag before it signs a wheel past PyPI's grant, closing M1 and L1, and every finding of round 1 is closed.
