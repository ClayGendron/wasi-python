# Review of 195 — A review that waits fails no run

- **Date:** 2026-11-15
- **Reviewer:** an agent (Claude), a fresh sub-agent of https://claude.ai/code/session_01BD1pVJ3SruxSESqPMy9sAx; not the author
- **Reviewed:** `origin/dev...89eb0e88`: the first read was through `62db4b7e`; round 1 adds the fix commit `e50571bd` (code) and `89eb0e88` (landing notes, `context/` only), both read
- **Run:** 43668754606 on `e50571bd`, with no review file yet: concluded `success`, with check runs `review` failure and `ci-status` failure; every other job succeeded or was skipped (READ, the Actions API, 2026-11-15)
- **Re-ran:** `uv run pytest -q -p no:cacheprovider tests/unit/test_ci_plan.py tests/unit/test_scan.py tests/unit/test_precheck.py -n 4` → 841 passed, exit 0; `uv run pytest -q -p no:cacheprovider tests/lint` → 14 passed, exit 0; `uv run pytest -q -p no:cacheprovider tests/checks/test_rules.py -k "news_files or ruff" --partial local` → 3 passed, exit 0; `release/precheck.py --plan-only` on `89eb0e88` → one wait printed, exit 0, no worktree left; a probe of `only_waiting` before and after the fix.

Box: 45 minutes (build-class), and a second pass on round 1. The self-check: all four boxes ticked, with the failing-first counts and the Windows legs named.

## Acceptance criteria against evidence
1. The plan's waits are tested. No review yet, a review left behind by code and a verdict that does not land each wait. A review signed by the author or by no one does not. A missing news file leaves the review job waiting and fails ci-status. A run refused nothing and a push never wait. Round 1 adds a refusal that only quotes a waiting phrase. Met. EXECUTED; failing first on `dev` is INFERRED and claimed in the self-check.
2. The rule 17 rows are tested: the real workflow passes, and each mutant is named. Met. EXECUTED. A step-level copy of the review expression is still refused (probe), since `replace(..., 1)` removes one line per matching job. READ.
3. The precheck tests cover quick's scripted steps in order, the hook that leaves someone else's hook alone, and (round 1) the runner's shell and quick's env. Met. EXECUTED.
4. The first run with no review file ends with `review` and `ci-status` red and the run's conclusion success. Met: run 43668754606 (READ, the Actions API: run `conclusion: success`; check runs `review` 132674036354 and `ci-status` 132678645666 both `failure`; the pull request's `mergeable_state` is `blocked`). The run after the review file is green: still to come, after this file is committed.

Diff, §4b, file by file (READ):
- `.github/workflows/release.yml`: unchanged since the first read. `review` and `ci-status` (`permissions: {}`, no token) gain job-level `continue-on-error`; their steps are unchanged, and no job `needs` either.
- `release/ci_plan.py`: round 1 matches each wait whole with `fullmatch`, so the wait has to be the entire message. Each pattern is the fixed text with only a review path, a stem or a sha in it, no wider than `REVIEW` and `NEWS`; anything else fails closed, which is stricter. EXECUTED: the quoted-phrase refusal of the first round now returns False, and the three real waits return True. The plan job's token is unchanged (`contents: read`, `actions: read`).
- `release/precheck.py`: local only, and it holds no token. Round 1 calls `ci_plan.from_runner` with a pull request's variables and no `GH_TOKEN`. `_gh` then reads nothing, so the precheck re-uses no run, and the release's preparation and the ledger are read as CI reads them. It runs quick in the runner's shell with quick's plain `env:` values.

No reader of a run's conclusion sees a new success: `accept-release.yml` acts only into `main`; the re-use reads job conclusions and skips these two; `red-run-issue` and the README badge read pushes, where nothing waits.

## Findings, most severe first
1. **The merge guard rested on a forum quote** (`.github/workflows/release.yml:207`, `:1890`). Medium, closed. The specification's only evidence that a job failed under job-level `continue-on-error` reports a failed check run was community discussion 15452. Run 43668754606 now shows it on this repository: the run concluded `success`, the `review` and `ci-status` check runs concluded `failure`, and the pull request reads `blocked` (READ, the API). That no mail went out is INFERRED from the success conclusion. Only the owner's inbox confirms it, and the landing notes say so.
2. **Waits were matched by substring** (`release/ci_plan.py:826`). Low, fixed in `e50571bd`. The waits are now anchored `fullmatch` patterns, with a test row for a reviewer's name that quotes a waiting phrase. EXECUTED.
3. **The docstring promised a skip-word check the plan does not make** (`release/precheck.py:11`). Low, fixed in `e50571bd`: the claim is gone.
4. **The plan half was a copy of part of `from_runner`** (`release/precheck.py:82-97`). Low, fixed in `e50571bd`: it calls `ci_plan.from_runner` with no token.
5. **The precheck's shell was not the runner's** (`release/precheck.py:68`). Low, fixed in `e50571bd`: it uses the runner's shell and quick's env, with a test.
6. **The new rule could not be met as root** (`AGENTS.md:51`). Low, fixed in `e50571bd`. The rule now accepts a failure seen the same way on `origin/dev`, said in the pull request, and this pull request's description says so for `test_the_walk_judges_links`.

## Constitution checks
- §4 constraints: nothing under `src/`, no input, no artifact and no patch changes. "uv only" holds: the hook and the docs run `uv run python release/precheck.py`. The code-writing rule holds: the new comments and docstrings name no specification number and no `context/` path (lint passes, EXECUTED). Rule 17's narrowing is a judge change, and the news file claims it under `[claim.judge]`.
- §7 never-do list: nothing tripped. The judge is narrowed, not weakened, to let only two exact lines through: a refused check stays red, and only the run's conclusion moves. All three commits carry `Co-Authored-By: Claude Opus 5.5` and the author's session trailer.

## Disposition (filled in by the author, then confirmed by the reviewer)
1. Finding 1 — closed by run 43668754606 and the landing notes in `89eb0e88`; confirmed against the API.
2. Finding 2 — fixed in `e50571bd`; confirmed.
3. Finding 3 — fixed in `e50571bd`; confirmed.
4. Finding 4 — fixed in `e50571bd`; confirmed.
5. Finding 5 — fixed in `e50571bd`; confirmed.
6. Finding 6 — fixed in `e50571bd`; confirmed.

## Verdict
Lands: run 43668754606 shows a waiting review leaves both required checks red and the pull request blocked while the run concludes success, and round 1's fix commit closes every Low.
